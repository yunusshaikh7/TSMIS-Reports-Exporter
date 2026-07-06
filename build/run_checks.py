"""Run the FULL offline check suite locally with one command.

The blocking gate lives in .github/workflows/checks.yml; before it existed as a
single local command, a dev had to copy the check list out of the workflow by
hand, and a subset run let a red suite ship (v0.17.3). This runner is the local
equivalent of the whole gate: it globs every build/check_*.py and check_*.js,
runs each with the SAME interpreter it was invoked with (so the build venv is
used when invoked as `build\.venv\Scripts\python.exe build\run_checks.py`), and
exits non-zero if anything fails. check_ci_manifest.py separately guards that
checks.yml runs this same globbed set, so the list can never silently drift.

Usage (from the repo root or build\):
    build\.venv\Scripts\python.exe build\run_checks.py           # stop on first failure
    build\.venv\Scripts\python.exe build\run_checks.py -k        # keep going, summarize
    build\.venv\Scripts\python.exe build\run_checks.py -j 4      # 4 checks in parallel
    build\.venv\Scripts\python.exe build\run_checks.py --skip-js # no node on this box

Stdlib only; no third-party deps (the CHECKS need the runtime deps, not the
runner). Each check's output is buffered and printed as one block so parallel
runs stay readable.
"""
import argparse
import concurrent.futures
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
ROOT = BUILD_DIR.parent

# Byte-compile + the product-name guard run as extra "checks" so this one
# command reproduces every blocking step of checks.yml, not just the check_*
# scripts. (Advisory lint — ruff/bandit/pip-audit — is deliberately NOT here:
# those never block in CI either.)
_COMPILEALL = [sys.executable, "-m", "compileall", "-q",
               str(ROOT / "scripts"), str(ROOT / "build"), str(ROOT / "version.py")]


def _discover(skip_js):
    """The full ordered check list as (name, argv) pairs."""
    checks = [("compileall", _COMPILEALL)]
    for p in sorted(BUILD_DIR.glob("check_*.py")):
        checks.append((p.stem, [sys.executable, str(p)]))
    js = sorted(BUILD_DIR.glob("check_*.js"))
    if skip_js:
        print(f"note: skipping {len(js)} JS check(s) (--skip-js)")
    else:
        node = shutil.which("node")
        if node is None:
            print("ERROR: node is not on PATH but JS checks exist "
                  "(pass --skip-js to run without them)", file=sys.stderr)
            sys.exit(2)
        for p in js:
            checks.append((p.stem, [node, str(p)]))
    return checks


def _run_one(name, argv):
    """Run one check; returns (name, ok, seconds, combined output)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")   # the " ≠ " marker vs cp1252
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=str(ROOT), env=env,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        ok, out = proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    except OSError as e:
        ok, out = False, f"could not launch: {type(e).__name__}: {e}"
    return name, ok, time.monotonic() - t0, out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the full offline check suite.")
    ap.add_argument("-k", "--keep-going", action="store_true",
                    help="run everything even after a failure")
    ap.add_argument("-j", "--jobs", type=int, default=1, metavar="N",
                    help="run N checks in parallel (default 1)")
    ap.add_argument("--skip-js", action="store_true",
                    help="skip the node-based check_*.js scripts")
    ap.add_argument("--only", metavar="SUBSTR",
                    help="run only checks whose name contains SUBSTR")
    args = ap.parse_args(argv)

    checks = _discover(args.skip_js)
    if args.only:
        checks = [c for c in checks if args.only in c[0]]
        if not checks:
            print(f"no checks match {args.only!r}", file=sys.stderr)
            return 2

    failed, passed = [], 0
    t0 = time.monotonic()

    def report(name, ok, secs, out):
        nonlocal passed
        status = "ok" if ok else "FAIL"
        print(f"[{status:>4}] {name}  ({secs:.1f}s)")
        if not ok:
            print(out.rstrip() or "(no output)")
            failed.append(name)
        else:
            passed += 1

    if args.jobs > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futures = {ex.submit(_run_one, n, a): n for n, a in checks}
            for fut in concurrent.futures.as_completed(futures):
                report(*fut.result())
                if failed and not args.keep_going:
                    for f in futures:
                        f.cancel()
                    break
    else:
        for name, a in checks:
            report(*_run_one(name, a))
            if failed and not args.keep_going:
                break

    total = time.monotonic() - t0
    print(f"\n{passed} passed, {len(failed)} failed of {len(checks)} "
          f"({total:.0f}s)")
    if failed:
        print("failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
