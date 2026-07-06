"""Guard: every check on disk is actually RUN by checks.yml (and vice versa).

checks.yml enumerates the blocking suite by hand (direct `python build/...`
lines, a bash for-loop of extension-less names, and `node build/...` lines).
Nothing previously failed when a new build/check_*.py never got wired in — a
check could exist, pass locally, and silently never run in CI. This tripwire
closes that: it globs the checks on disk, extracts every check name referenced
in checks.yml, and fails on any difference, either direction.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_ci_manifest.py
"""
import re
import sys
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent
WORKFLOW = ROOT / ".github" / "workflows" / "checks.yml"

_fail = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


def main():
    on_disk = {p.stem for p in BUILD_DIR.glob("check_*.py")}
    on_disk |= {p.stem for p in BUILD_DIR.glob("check_*.js")}

    check("checks.yml exists", WORKFLOW.is_file(), str(WORKFLOW))
    if not WORKFLOW.is_file():
        return

    text = WORKFLOW.read_text(encoding="utf-8")
    # Every check reference, however invoked: `python build/check_x.py`,
    # the bash `for c in check_a check_b ...` loop, `node build/check_y.js`.
    # Comments count as references only if they name a real file — a stale
    # comment naming a DELETED check is caught by the reverse direction below.
    referenced = set(re.findall(r"\bcheck_[a-z0-9_]+\b", text))

    never_run = sorted(on_disk - referenced)
    check("every check on disk is referenced by checks.yml", not never_run,
          "not wired into CI: " + ", ".join(never_run))

    ghosts = sorted(referenced - on_disk)
    check("every check checks.yml references exists on disk", not ghosts,
          "referenced but missing: " + ", ".join(ghosts))

    # The suite must stay non-trivial — a glob typo that empties either side
    # would otherwise make both assertions vacuously green.
    check(f"sanity: a real suite was compared ({len(on_disk)} on disk)",
          len(on_disk) >= 70)


if __name__ == "__main__":
    print("CI check-manifest guard (build/check_* vs checks.yml):")
    main()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        sys.exit(1)
    print("\nall good")
