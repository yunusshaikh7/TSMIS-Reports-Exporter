"""Golden check for the always-current destination plumbing (v0.12.0):
settings.batch_dest (default / set / reset) and report_library freshness
(presence + newest-file age per report type under the destination).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_report_library.py
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import settings
import report_library

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_batch_dest_setting():
    print("settings.get/set_batch_dest:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_cfg_"))
    orig = settings.CONFIG_FILE
    settings.CONFIG_FILE = tmp / "config.json"
    settings._cache, settings._cache_mtime = None, None
    try:
        check("unset -> default", settings.get_batch_dest() == settings.default_batch_dest())
        settings.set_batch_dest(r"D:\My Reports")
        check("set persists", settings.get_batch_dest() == r"D:\My Reports")
        check("survives a fresh read", settings.get_batch_dest() == r"D:\My Reports")
        settings.set_batch_dest("")
        check("empty -> back to default",
              settings.get_batch_dest() == settings.default_batch_dest())
    finally:
        settings.CONFIG_FILE = orig
        settings._cache, settings._cache_mtime = None, None
        shutil.rmtree(tmp, ignore_errors=True)


def test_report_ages():
    print("report_library.report_ages:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_dest_"))
    try:
        (dest / "ssor-prod" / "highway_log").mkdir(parents=True)
        (dest / "ssor-prod" / "highway_log" / "r1.xlsx").write_bytes(b"PK")
        (dest / "ars-prod" / "ramp_summary").mkdir(parents=True)
        old = dest / "ars-prod" / "ramp_summary" / "r1.pdf"
        old.write_bytes(b"%PDF")
        old_t = time.time() - 6 * 86400
        os.utime(old, (old_t, old_t))

        rows = report_library.report_ages(dest, [
            ("Highway Log", "highway_log"),
            ("Ramp Summary", "ramp_summary"),
            ("Intersection Detail", "intersection_detail"),
        ])
        by = {r["label"]: r for r in rows}
        check("highway log present + fresh (< 1h)",
              by["Highway Log"]["present"] and by["Highway Log"]["age_seconds"] < 3600)
        check("ramp summary present + ~6 days old",
              by["Ramp Summary"]["present"]
              and 5 * 86400 < by["Ramp Summary"]["age_seconds"] < 7 * 86400)
        check("intersection detail absent (no age)",
              not by["Intersection Detail"]["present"]
              and by["Intersection Detail"]["age_seconds"] is None)
        check("newest_mtime None for a missing subdir",
              report_library.newest_mtime(dest, "nope") is None)
        check("newest_mtime None for a missing destination",
              report_library.newest_mtime(dest / "does-not-exist", "highway_log") is None)
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def main():
    test_batch_dest_setting()
    test_report_ages()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL REPORT-LIBRARY / BATCH-DEST CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
