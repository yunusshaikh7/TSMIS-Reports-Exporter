"""Guard: a missing Playwright must never silently kill the GUI at import.

The export_*.py stubs fail-early when Playwright is absent. They used to
`print(...); sys.exit(1)` at MODULE IMPORT time — and report_catalog (the
metadata SoT the whole GUI imports) imports their SPECs, so a damaged/pruned
bundle killed the windowed exe with exit 1 and no dialog. The guard now
branches: run as a console script -> the friendly ".bat" message + exit 1
(unchanged UX); imported -> a real ImportError the caller's fatal path can show.

Both branches are exercised in SUBPROCESSES with playwright masked out
(sys.modules[...] = None makes `import playwright...` raise ImportError).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_export_stub_guard.py
"""
import os
import subprocess
import sys
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent

_fail = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


_MASK = ("import sys; "
         "sys.modules['playwright'] = None; "
         "sys.modules['playwright.sync_api'] = None; "
         "sys.path.insert(0, 'scripts'); ")


def _run(code):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-c", code], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


def main():
    # ---- imported (the GUI path): ImportError, NEVER SystemExit -------------
    probe = _MASK + (
        "out = 'NO-RAISE'\n"
        "try:\n"
        "    import report_catalog\n"
        "except SystemExit:\n"
        "    out = 'SYSTEMEXIT'\n"
        "except ImportError:\n"
        "    out = 'IMPORTERROR'\n"
        "print(out)")
    r = _run(probe)
    check("importing report_catalog without playwright raises ImportError "
          "(not SystemExit, not silence)",
          "IMPORTERROR" in r.stdout,
          f"stdout={r.stdout!r} stderr-tail={r.stderr[-200:]!r}")
    check("...and the probe subprocess itself exits 0 (the error was catchable)",
          r.returncode == 0, f"returncode={r.returncode}")

    # ---- run as a console script: the friendly message + exit 1 (unchanged) -
    stub = "scripts/export_ramp_summary.py"
    code = _MASK + f"exec(compile(open(r'{stub}', encoding='utf-8').read(), r'{stub}', 'exec'))"
    r = _run(code)
    check("running a stub as a script without playwright exits 1",
          r.returncode == 1, f"returncode={r.returncode}")
    check("...with the friendly .bat guidance on stdout",
          "Playwright is not installed" in r.stdout, f"stdout={r.stdout!r}")


if __name__ == "__main__":
    print("export-stub ImportError guard (GUI import vs console run):")
    main()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        sys.exit(1)
    print("\nall good")
