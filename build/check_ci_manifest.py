"""Guard: the CI workflows actually run the FULL check suite via the runner.

U1 (v0.19.0): checks.yml no longer enumerates checks by hand — the list lives
ONLY in build/run_checks.py's glob (every build/check_*.py + check_*.js), so a
new check file is picked up automatically and can never be silently skipped
(the v0.17.3 mechanism this family of guards exists for). What CAN still
regress is the workflows dropping the runner call itself, or the runner's
discovery going quietly narrow — this tripwire pins both:

  * checks.yml AND release.yml each invoke `python build/run_checks.py` in a
    step WITHOUT `continue-on-error` (a soft-failing suite is no gate at all);
  * the runner's discovery still globs BOTH check families, and a suite-sized
    set exists on disk (a glob typo can't quietly shrink the gate).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_ci_manifest.py
"""
import re
import sys
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent
CHECKS_YML = ROOT / ".github" / "workflows" / "checks.yml"
RELEASE_YML = ROOT / ".github" / "workflows" / "release.yml"

# The suite is ~88 today; a discovery bug that quietly halves it must trip this.
MIN_SUITE_SIZE = 80

_fail = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok: {name}")
    else:
        print(f"FAIL: {name}" + (f"\n      {detail}" if detail else ""))
        _fail.append(name)


def _runner_step_blocking(text, wf_name):
    """True when the workflow calls run_checks.py in a step WITHOUT
    continue-on-error."""
    for m in re.finditer(r"^( *)- name:.*$", text, re.M):
        indent = m.group(1)
        start = m.end()
        nxt = re.search(rf"^{indent}- name:", text[start:], re.M)
        body = text[start:start + nxt.start()] if nxt else text[start:]
        if "run_checks.py" in body:
            if "continue-on-error: true" in body:
                print(f"      {wf_name}: the runner step is continue-on-error")
                return False
            return True
    return False


def main():
    on_disk = ({p.stem for p in BUILD_DIR.glob("check_*.py")}
               | {p.stem for p in BUILD_DIR.glob("check_*.js")})
    check(f"a suite-sized check set exists on disk ({len(on_disk)})",
          len(on_disk) >= MIN_SUITE_SIZE)

    for wf in (CHECKS_YML, RELEASE_YML):
        check(f"{wf.name} exists", wf.is_file(), str(wf))
        if wf.is_file():
            text = wf.read_text(encoding="utf-8")
            check(f"{wf.name} runs the full suite via run_checks.py (blocking)",
                  _runner_step_blocking(text, wf.name))

    # the runner's discovery must still glob BOTH families — a narrowed glob
    # would silently shrink every gate that trusts it.
    runner = (BUILD_DIR / "run_checks.py").read_text(encoding="utf-8")
    check("run_checks.py discovers check_*.py by glob", 'glob("check_*.py")' in runner)
    check("run_checks.py discovers check_*.js by glob", 'glob("check_*.js")' in runner)


if __name__ == "__main__":
    print("CI runner-gate guard (run_checks.py wired + discovery intact):")
    main()
    if _fail:
        print(f"\n{len(_fail)} check(s) FAILED")
        sys.exit(1)
    print("all good")
