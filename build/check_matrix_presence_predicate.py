"""Golden check for the shared accepted-data-file predicate (CMP-AUD-083).

Matrix PRESENCE, newest-data MTIME, FINGERPRINTING, and adapter DISCOVERY must
share ONE predicate: a file counts as report data iff it is a ``.xlsx`` / ``.pdf``
that is NOT an Excel lock (``~$``), an in-flight temp, a comparison payload, the
publication lock, or one of our sidecars. Before this, a folder holding only a
lock / ``notes.txt`` / ``README`` / ``.fingerprint.json`` read as an EXPORT, and a
newer lock or sidecar could make an otherwise-current comparison look stale.

Covers the predicate itself, the four real call sites (report_library.newest_mtime
+ _newest_in, day_matrix + baseline_matrix _folder_newest_mtime), and the
fingerprint extension-allowlist behavior, over empty / lock-only / metadata-only /
mixed / real-xlsx / real-pdf folders.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_matrix_presence_predicate.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import artifact_store
import baseline_matrix
import day_matrix
import report_library

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _touch(folder, name, mtime=None, content=b"x"):
    p = Path(folder) / name
    p.write_bytes(content)
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def test_predicate():
    print("is_report_data_file: extension allowlist + lock/temp/sidecar exclusion:")
    rd = artifact_store.is_report_data_file
    cases = [
        ("tsmis_highway_log_route 001.xlsx", True),
        ("ramp_summary_route 005.pdf", True),
        ("REPORT.XLSX", True),                                # case-insensitive
        ("~$tsmis_highway_log_route 001.xlsx", False),        # Excel lock
        ("notes.txt", False),
        ("README", False),
        ("data.csv", False),
        (".fingerprint.json", False),
        (".outcome.json", False),
        (".provenance.json", False),
        (".tsmis-owned.json", False),                         # ownership marker
        (".gitkeep", False),
        ("route.xlsx.tmp-abc123def456", False),               # in-flight temp
        ("x.staging", False),
        (artifact_store._COMPARISON_PUBLICATION_LOCK_NAME, False),
    ]
    ok = all(rd(n) is exp for n, exp in cases)
    check("every predicate case matches its expected verdict", ok)
    if not ok:
        for n, exp in cases:
            if rd(n) is not exp:
                print(f"      MISMATCH {n!r}: got {rd(n)} want {exp}")


def _all_scanners(folder):
    """(report_library.newest_mtime, _newest_in, day, baseline) presence for one
    leaf folder. newest_mtime scans <dest>/<env>/<subdir>, so nest the folder."""
    return {
        "_newest_in": report_library._newest_in(folder),
        "day": day_matrix._folder_newest_mtime(folder),
        "baseline": baseline_matrix._folder_newest_mtime(folder),
    }


def test_call_sites():
    print("all four scanners agree on presence (CMP-AUD-083 defect scenarios):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_083_"))
    # empty
    empty = tmp / "empty"; empty.mkdir()
    # lock-only (~$)  — the finding's "appears exported"
    locks = tmp / "locks"; locks.mkdir()
    _touch(locks, "~$route.xlsx")
    # metadata-only (notes / README / sidecar)
    meta = tmp / "meta"; meta.mkdir()
    _touch(meta, "notes.txt"); _touch(meta, "README"); _touch(meta, ".fingerprint.json")
    _touch(meta, ".tsmis-owned.json")
    # a real export
    real = tmp / "real"; real.mkdir()
    _touch(real, "tsmis_highway_log_route 001.xlsx", mtime=1000)
    realpdf = tmp / "realpdf"; realpdf.mkdir()
    _touch(realpdf, "ramp_summary_route 005.pdf", mtime=1000)
    # mixed: a real export + a NEWER lock + a NEWER sidecar (must not inflate freshness)
    mixed = tmp / "mixed"; mixed.mkdir()
    _touch(mixed, "tsmis_highway_log_route 001.xlsx", mtime=1000)
    _touch(mixed, "~$route.xlsx", mtime=9000)
    _touch(mixed, ".fingerprint.json", mtime=9000)
    _touch(mixed, "notes.txt", mtime=9000)

    for label, folder, present in [
        ("empty -> absent", empty, False),
        ("lock-only -> absent", locks, False),
        ("metadata-only -> absent", meta, False),
        ("real .xlsx -> present", real, True),
        ("real .pdf -> present", realpdf, True),
        ("mixed -> present", mixed, True),
    ]:
        scans = _all_scanners(folder)
        agree = all((v is not None) == present for v in scans.values())
        check(f"{label}: all scanners agree", agree)
        if not agree:
            print(f"      {scans}")

    # newest_mtime (the <dest>/<env>/<subdir> variant): a lock/notes-only subdir is
    # absent, a real one is present.
    dest = tmp / "dest"; (dest / "ssor-prod" / "highway_log").mkdir(parents=True)
    (dest / "ssor-prod" / "ramp_summary").mkdir(parents=True)
    _touch(dest / "ssor-prod" / "highway_log", "tsmis_highway_log_route 001.xlsx", mtime=1000)
    _touch(dest / "ssor-prod" / "ramp_summary", "~$lock.xlsx")     # lock-only
    check("newest_mtime present for a real-xlsx subdir",
          report_library.newest_mtime(dest, "highway_log") is not None)
    check("newest_mtime absent for a lock-only subdir",
          report_library.newest_mtime(dest, "ramp_summary") is None)

    # the finding's "newer lock/sidecar makes stale": the mixed folder's newest is
    # the real .xlsx (1000), NOT the 9000 lock/sidecar/notes.
    for name, fn in [("day", day_matrix._folder_newest_mtime),
                     ("baseline", baseline_matrix._folder_newest_mtime),
                     ("report_library", report_library._newest_in)]:
        m = fn(mixed)
        check(f"{name}: a newer lock/sidecar does NOT inflate the mixed folder's mtime",
              m is not None and m < 5000)


def test_fingerprint_stays_conservative():
    """The DELIBERATE asymmetry: fingerprint (change-detection) is conservative-
    INCLUSION — a stray file DOES bust freshness so nothing hides — while presence
    (is-this-an-export?) uses the CMP-AUD-083 allowlist and ignores it. Pinning
    both directions stops a future 'just unify them' refactor from reintroducing
    the hiding bug (guarded harder by check_artifact_store's near-match .zlib)."""
    print("fingerprint stays conservative; presence uses the allowlist (the asymmetry):")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_083fp_"))
    a = tmp / "a"; a.mkdir()
    _touch(a, "route 001.xlsx", mtime=1000, content=b"realdata")
    fp1 = artifact_store.fingerprint(a)
    _touch(a, "notes.txt", mtime=1000)             # a stray non-report file
    fp2 = artifact_store.fingerprint(a)
    check("a stray notes.txt DOES change the fingerprint (conservative inclusion)",
          fp1 != fp2)
    # ...but the SAME stray file never makes the folder read as an export.
    check("the stray notes.txt does NOT mark the folder present (allowlist)",
          report_library._newest_in(a) is not None                # the real .xlsx is present
          and day_matrix._folder_newest_mtime(a) is not None)
    # our own strict-format artifacts (locks/temps/sidecars) stay excluded BOTH ways:
    # adding a lock to {route, notes} leaves the fingerprint at its notes-inclusive fp2.
    _touch(a, "~$route 001.xlsx", mtime=9000)       # an Excel lock
    fp3 = artifact_store.fingerprint(a)
    check("an Excel lock does NOT change the fingerprint (our own artifact)", fp2 == fp3)


def main():
    test_predicate()
    test_call_sites()
    test_fingerprint_stays_conservative()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL MATRIX-PRESENCE-PREDICATE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
