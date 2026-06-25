"""Dependency-integrity guard for the reproducible build (P10 / R1-R10 / RR1-C2).

Static assertions (default run): version.py <-> requirements.txt <-> the hash-pinned
lock all agree on the Playwright pin; the `cryptography` transitive is explicitly
pinned; the lock is hash-pinned and covers every direct runtime + build dep at the
SAME version.

`--verify-installed`: FAIL when the installed env does not match the lock exactly
(unexpected / missing / version-mismatched packages), ignoring the bootstrap tools
pip freeze omits, so a polluted or drifted build venv can't ship. The freeze is taken
from THIS interpreter (`sys.executable -m pip freeze`) so build.ps1 runs it inside the
build venv with no fragile native pipe; `--freeze-file PATH` overrides for tests.

Pure stdlib, offline, no network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_build_env.py
    build\\.venv\\Scripts\\python.exe build\\check_build_env.py --verify-installed
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQ = ROOT / "requirements.txt"
REQ_BUILD = ROOT / "requirements-build.txt"
LOCK = ROOT / "requirements-build.lock.txt"

# pip freeze omits these bootstrap tools; the lock pins setuptools (required under
# --require-hashes) -- drop them from BOTH sides of the installed-env comparison.
_BOOTSTRAP = {"pip", "setuptools", "wheel", "distribute"}

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _norm(name):
    """PEP 503 normalize: lowercase, runs of -_. collapse to a single '-'."""
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def _req_pins(text):
    """{normalized_name: version} for the `name==version` lines in a requirements
    file (skipping comments, blanks, -r/-c includes, and markers)."""
    pins = {}
    for raw in text.splitlines():
        line = raw.lstrip("﻿").strip()   # tolerate a stray UTF-8 BOM
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = re.match(r"([A-Za-z0-9_.\-]+)\s*==\s*([^\s;]+)", line)
        if m:
            pins[_norm(m.group(1))] = m.group(2)
    return pins


def _lock_pins(text):
    """{normalized_name: version} for the `name==version \\` lines in the hash lock
    (the indented `--hash=` lines and comments are skipped)."""
    pins = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("--hash"):
            continue
        m = re.match(r"([A-Za-z0-9_.\-]+)==([^\s;\\]+)", line)
        if m:
            pins[_norm(m.group(1))] = m.group(2)
    return pins


def _playwright_from_version_py():
    text = (ROOT / "version.py").read_text(encoding="utf-8")
    m = re.search(r'PLAYWRIGHT_VERSION\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def test_static():
    print("dependency-integrity (version.py <-> requirements <-> lock):")
    req = _req_pins(REQ.read_text(encoding="utf-8"))
    reqb = _req_pins(REQ_BUILD.read_text(encoding="utf-8"))
    lock_text = LOCK.read_text(encoding="utf-8")
    lock = _lock_pins(lock_text)
    pw = _playwright_from_version_py()

    check("requirements.txt pins playwright", "playwright" in req)
    check("version.py PLAYWRIGHT_VERSION == requirements.txt playwright pin",
          pw is not None and req.get("playwright") == pw)
    check("the lock pins the SAME playwright as version.py",
          lock.get("playwright") == pw)
    check("the cryptography transitive is explicitly pinned in requirements.txt",
          "cryptography" in req)
    check("the lock is hash-pinned (carries --hash=sha256 lines)",
          "--hash=sha256:" in lock_text)
    # Every direct runtime + build dep must appear in the lock at the SAME version.
    for name, ver in sorted({**req, **reqb}.items()):
        check(f"lock covers direct dep {name}=={ver}", lock.get(name) == ver)


def _diff_env(lock, freeze):
    """(missing, unexpected, mismatched) comparing an installed freeze to the lock,
    ignoring the bootstrap tools pip freeze omits."""
    lk = {n: v for n, v in lock.items() if n not in _BOOTSTRAP}
    fz = {n: v for n, v in freeze.items() if n not in _BOOTSTRAP}
    missing = sorted(n for n in lk if n not in fz)
    unexpected = sorted(n for n in fz if n not in lk)
    mismatched = sorted(f"{n} (lock {lk[n]} != installed {fz[n]})"
                        for n in lk if n in fz and lk[n] != fz[n])
    return missing, unexpected, mismatched


def verify_installed(freeze_text):
    """True when the installed freeze matches the lock exactly; prints any diffs."""
    lock = _lock_pins(LOCK.read_text(encoding="utf-8"))
    freeze = _req_pins(freeze_text)            # freeze lines are name==version too
    missing, unexpected, mismatched = _diff_env(lock, freeze)
    if missing:
        print(f"  [FAIL] missing from the installed env: {missing}")
    if unexpected:
        print(f"  [FAIL] UNEXPECTED package(s) not in the lock: {unexpected}")
    if mismatched:
        print(f"  [FAIL] version mismatch(es): {mismatched}")
    ok = not (missing or unexpected or mismatched)
    if ok:
        print("  [OK ] installed env matches the lock exactly")
    return ok


def test_diff_env_selftests():
    print("env-verification self-tests (synthetic):")
    lock = {"playwright": "1.60.0", "openpyxl": "3.1.5", "setuptools": "82.0.1"}
    m, u, x = _diff_env(lock, {"playwright": "1.60.0", "openpyxl": "3.1.5"})
    check("exact match (minus bootstrap) -> no diffs", not (m or u or x))
    m, u, x = _diff_env(lock, {"playwright": "1.60.0", "openpyxl": "3.1.5", "requests": "2.0"})
    check("an UNEXPECTED extra package is detected", u == ["requests"])
    m, u, x = _diff_env(lock, {"playwright": "1.60.0"})
    check("a MISSING package is detected", "openpyxl" in m)
    m, u, x = _diff_env(lock, {"playwright": "1.59.0", "openpyxl": "3.1.5"})
    check("a VERSION MISMATCH is detected", any("playwright" in s for s in x))


def _installed_freeze(argv):
    """The `pip freeze` text to verify: an explicit `--freeze-file PATH` (tests),
    else THIS interpreter's own freeze (so build.ps1 runs it inside the build venv
    with no fragile native pipe — a PowerShell native-to-native pipe can corrupt the
    first line with a BOM)."""
    if "--freeze-file" in argv:
        return Path(argv[argv.index("--freeze-file") + 1]).read_text(encoding="utf-8")
    import subprocess
    out = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                         capture_output=True, text=True)
    return out.stdout


def main():
    if "--verify-installed" in sys.argv:
        return 0 if verify_installed(_installed_freeze(sys.argv)) else 1
    test_static()
    test_diff_env_selftests()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL BUILD-ENV CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
