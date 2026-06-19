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


def test_cell_ages():
    print("report_library.cell_ages (per (env, report) freshness for the matrix):")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_cell_"))
    try:
        # ssor-prod has a fresh ramp_detail; ars-prod has an OLD ramp_detail and
        # a fresh ramp_summary; ars-test is empty.
        (dest / "ssor-prod" / "ramp_detail").mkdir(parents=True)
        (dest / "ssor-prod" / "ramp_detail" / "r1.xlsx").write_bytes(b"PK")
        (dest / "ars-prod" / "ramp_detail").mkdir(parents=True)
        oldf = dest / "ars-prod" / "ramp_detail" / "r1.xlsx"
        oldf.write_bytes(b"PK")
        old_t = time.time() - 4 * 86400
        os.utime(oldf, (old_t, old_t))
        (dest / "ars-prod" / "ramp_summary").mkdir(parents=True)
        (dest / "ars-prod" / "ramp_summary" / "r1.pdf").write_bytes(b"%PDF")

        reports = [("Ramp Detail", "ramp_detail"), ("Ramp Summary", "ramp_summary")]
        envs = ["ssor-prod", "ars-prod", "ars-test"]
        cells = report_library.cell_ages(dest, reports, envs)

        check("ssor-prod ramp_detail present + fresh",
              cells["ssor-prod"]["ramp_detail"]["present"]
              and cells["ssor-prod"]["ramp_detail"]["age_seconds"] < 3600)
        check("ssor-prod ramp_summary absent",
              not cells["ssor-prod"]["ramp_summary"]["present"])
        check("ars-prod ramp_detail present + ~4 days old",
              cells["ars-prod"]["ramp_detail"]["present"]
              and 3 * 86400 < cells["ars-prod"]["ramp_detail"]["age_seconds"] < 5 * 86400)
        check("ars-prod ramp_summary present + fresh",
              cells["ars-prod"]["ramp_summary"]["present"])
        check("ars-test all absent (empty env folder)",
              not cells["ars-test"]["ramp_detail"]["present"]
              and not cells["ars-test"]["ramp_summary"]["present"])
        check("missing dest -> all absent, no raise",
              all(not v["present"]
                  for env in report_library.cell_ages(dest / "nope", reports, envs).values()
                  for v in env.values()))
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_matrix_baseline_setting():
    print("settings.get/set_matrix_baseline:")
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_mxb_"))
    orig = settings.CONFIG_FILE
    settings.CONFIG_FILE = tmp / "config.json"
    settings._cache, settings._cache_mtime = None, None
    try:
        check("unset -> ssor-prod default", settings.get_matrix_baseline() == "ssor-prod")
        settings.set_matrix_baseline("ars-test")
        check("set persists", settings.get_matrix_baseline() == "ars-test")
        settings.set_matrix_baseline("")
        check("empty -> back to default", settings.get_matrix_baseline() == "ssor-prod")
    finally:
        settings.CONFIG_FILE = orig
        settings._cache, settings._cache_mtime = None, None
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    test_batch_dest_setting()
    test_report_ages()
    test_cell_ages()
    test_matrix_baseline_setting()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL REPORT-LIBRARY / BATCH-DEST CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
