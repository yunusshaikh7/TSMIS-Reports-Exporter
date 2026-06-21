"""Diagnostic check: the SOURCE ARCHIVE's console flow imports + dispatches.

The ``*-batch-source.zip`` release variant is the ``.bat`` console flow (the
target runs ``1. setup.bat`` to fetch the libraries). This is the offline half of
that variant's gate (R1-M02). It builds a real source archive, extracts it into a
disposable clean dir, and runs the console smoke in a FRESH interpreter rooted at
the EXTRACTED tree -- so it can only see what actually shipped in the archive.

TWO modes, because the artifact under review differs by caller (PA-B03):

  * **worktree candidate** (default, pre-commit) -- archives the COMPLETE intended
    product worktree: tracked modifications + untracked product files, ``.gitignore``
    respected, ``docs/planning/`` excluded, built via a THROWAWAY git index so the
    real index is never touched. This is what gates a phase BEFORE it is committed
    (Claude's per-phase review is pre-commit), and what protects later phases (e.g.
    P4 console/report dispatch) from a worktree change a plain ``git archive HEAD``
    would miss.
  * **supplied archive** (``--zip PATH``) -- gates an EXACT caller-built zip. The
    release workflow builds the upload zip first and passes it here, so the gate
    runs against the same archive that is published.

It asserts archive membership + prefix, that the candidate archive reflects the
WORKTREE (not HEAD), the clean-extract console menu->module dispatch, and (the
negative characterization) that a required member missing from the archive FAILS.

No live browser / auth-file write / network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_source_zip_smoke.py
    build\\.venv\\Scripts\\python.exe build\\check_source_zip_smoke.py --zip dist.zip
"""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "TSMIS-Exporter-batch/"          # MUST match release.yml's git archive --prefix
_SELF_REL = "build/check_source_zip_smoke.py"   # this file -- the worktree-provenance probe

# Console-flow members that MUST be present in the source archive. A representative
# subset proves membership/prefix; the smoke's `import reports` then transitively
# requires every export_/consolidate_/compare_ module too.
_REQUIRED_MEMBERS = [
    "scripts/reports.py", "scripts/cli.py", "scripts/export_multi.py",
    "scripts/run_report.py", "scripts/consolidate_ramp_detail.py",
    "scripts/compare_env.py",
]

# The console smoke, run in a FRESH interpreter with the EXTRACTED archive root as
# cwd + import root -- so it imports ONLY what shipped in the archive (a clean
# extract test, never the checkout). Exits 0 on success, nonzero on any failure.
_SMOKE_SRC = r'''
import io, os, sys
from pathlib import Path
sys.stdin = io.StringIO("")                     # any stray prompt -> EOF, never blocks
sys.path.insert(0, str(Path.cwd() / "scripts"))
import cli, run_report, reports, export_multi    # noqa: F401  (import == archive proof)

fail = []
def ck(name, cond):
    print(("  [OK ] " if cond else "  [FAIL] ") + name)
    if not cond:
        fail.append(name)

menu = export_multi.REPORTS
ck("export menu derives from EXPORT_REPORTS (menu order)",
   len(menu) == len(reports.EXPORT_REPORTS)
   and [m[0] for m in menu] == [r[0] for r in reports.EXPORT_REPORTS])

os.environ["TSMIS_REPORTS"] = "1,3"; p13 = cli._select_reports_console(menu)
os.environ["TSMIS_REPORTS"] = "2";   p2 = cli._select_reports_console(menu)
os.environ["TSMIS_REPORTS"] = "all"; pall = cli._select_reports_console(menu)
os.environ.pop("TSMIS_REPORTS", None)
ck("selection '1,3' dispatches to menu items 1 and 3", p13 == [menu[0], menu[2]])
ck("selection '2' dispatches to a DIFFERENT module", p2 == [menu[1]] and p2 != p13)
ck("selection 'all' dispatches to every report", pall == list(menu))
ck("every dispatched report exposes a ReportSpec subdir",
   all(getattr(s, "subdir", None) for _l, s in menu))

bad = [l for l, m in reports.CONSOLIDATE_REPORTS
       if not callable(getattr(m, "consolidate", None))]
ck("every Consolidate row resolves to a consolidate() entry", not bad)

bad_cmp = []
for l, ad, kind, _g in reports.COMPARE_REPORTS:
    fn = "compare" if kind == "files" else "compare_folders"
    if not (callable(getattr(ad, fn, None)) and callable(getattr(ad, "suggest_name", None))):
        bad_cmp.append((l, kind))
ck("every Compare row resolves to its entry + suggest_name", not bad_cmp)

print(f"SMOKE {'FAIL' if fail else 'OK'}: {len(fail)} failure(s)")
sys.exit(1 if fail else 0)
'''

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _candidate_archive(dest_zip):
    """Archive the CURRENT worktree -- tracked modifications + untracked product
    files, .gitignore respected -- MINUS docs/planning/, using a THROWAWAY index
    file so the developer's real staging area is never altered. This is the
    pre-commit (phase-review) artifact: it reflects the worktree, not HEAD."""
    tmp_index = dest_zip.parent / "candidate.index"
    env = dict(os.environ, GIT_INDEX_FILE=str(tmp_index))

    def g(*args, **kw):
        # autocrlf=false: archive the worktree bytes as-is (no eol conversion, no
        # noisy "LF will be replaced by CRLF" warnings, and the provenance content
        # match below is exact).
        return subprocess.run(["git", "-c", "core.autocrlf=false", *args],
                              cwd=str(ROOT), env=env, check=True, **kw)

    try:
        g("read-tree", "HEAD")                       # seed the temp index from HEAD
        g("add", "-A")                               # stage all worktree changes (incl. untracked)
        g("rm", "-r", "--cached", "--ignore-unmatch", "docs/planning",
          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   # never ship planning
        tree = g("write-tree", capture_output=True, text=True).stdout.strip()
        g("archive", "--format=zip", "--prefix", PREFIX, "-o", str(dest_zip), tree)
    finally:
        if tmp_index.exists():
            tmp_index.unlink()


def _extract(zip_path, dest_dir):
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest_dir)
    root = dest_dir / PREFIX.rstrip("/")
    if root.is_dir():
        return root
    tops = [p for p in dest_dir.iterdir() if p.is_dir()]   # tolerate a different prefix
    return tops[0] if len(tops) == 1 else dest_dir


def _run_smoke(root):
    """Run the console smoke in a fresh interpreter rooted at `root`. Returns
    (exit_code, combined_output)."""
    r = subprocess.run([sys.executable, "-c", _SMOKE_SRC], cwd=str(root),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def _norm(b):
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _check_archive(archive_root, *, candidate):
    check(f"archive uses the release prefix {PREFIX!r}", archive_root.is_dir())
    missing = [m for m in _REQUIRED_MEMBERS if not (archive_root / m).is_file()]
    check("every required console member is IN the archive", not missing)
    if missing:
        print("   missing from archive:", missing)

    if candidate:
        # Worktree provenance: the candidate archive must carry THIS file's CURRENT
        # (uncommitted) content. The check itself is an untracked PA addition absent
        # from HEAD, so a content match proves the archive is the worktree revision,
        # NOT a silent fallback to HEAD (PA-B03 demo #1/#3).
        a = archive_root / _SELF_REL
        prov = a.is_file() and _norm(a.read_bytes()) == _norm(Path(__file__).read_bytes())
        check("candidate archive reflects the WORKTREE (this file's current content), not HEAD",
              prov)

    code, out = _run_smoke(archive_root)
    for line in out.splitlines():
        print("   |", line)
    check("clean-extract console smoke passes against the archive", code == 0)


def main(argv):
    zip_arg = None
    if "--zip" in argv:
        zip_arg = argv[argv.index("--zip") + 1]

    tmp = Path(tempfile.mkdtemp(prefix="tsmis_srczip_"))
    try:
        if zip_arg:
            print(f"mode: supplied archive  ({zip_arg})")
            check("supplied archive exists", Path(zip_arg).is_file())
            archive_root = _extract(Path(zip_arg), tmp / "x")
            _check_archive(archive_root, candidate=False)
        else:
            print("mode: worktree candidate (pre-commit; real git index untouched)")
            zip_path = tmp / "candidate.zip"
            _candidate_archive(zip_path)
            check("candidate archive built from the worktree",
                  zip_path.exists() and zip_path.stat().st_size > 0)
            archive_root = _extract(zip_path, tmp / "x")
            _check_archive(archive_root, candidate=True)

            # NEGATIVE: drop a required member from a COPY of the archive -> the
            # smoke MUST fail, proving the gate detects a member missing from the
            # archive (not just a happy checkout).
            neg = tmp / "neg"
            shutil.copytree(archive_root, neg)
            (neg / "scripts" / "export_multi.py").unlink()
            ncode, _ = _run_smoke(neg)
            check("a member missing from the archive FAILS the smoke (negative test)",
                  ncode != 0)

        print()
        if _failures:
            print(f"FAILED: {len(_failures)} check(s): {_failures}")
            return 1
        print("ALL SOURCE-ZIP CONSOLE-FLOW CHECKS PASSED (real archive + clean extract)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
