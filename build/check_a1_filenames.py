"""Golden check for A1 — self-describing output filenames (v0.12.0).

Consolidations stamp the run's provenance (the run-folder name = date + src-env)
into the consolidated workbook's filename; the two comparison families append a
generated-on date to their suggested filename; TSN Highway Log is exempt (no
src/env, undated input). The legacy flat layout (day=None) keeps its fixed name.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_a1_filenames.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import paths
import consolidate_ramp_summary as crs
import consolidate_ramp_detail as crd
import consolidate_highway_sequence as chs
import consolidate_highway_log as chl
import consolidate_tsn_highway_log as ctsn
import compare_env
import compare_highway_log

RUN = "2026-06-16 ssor-prod"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_stamp_helper():
    print("paths.stamped_consolidated_filename:")
    f = paths.stamped_consolidated_filename
    check("real run folder stamps date+src-env",
          f("highway_log_consolidated.xlsx", RUN)
          == f"highway_log_consolidated {RUN}.xlsx")
    check("legacy bare-date folder still stamps (parses as ssor-prod)",
          f("x.xlsx", "2026-06-11") == "x 2026-06-11.xlsx")
    check("day=None -> unchanged", f("x.xlsx", None) == "x.xlsx")
    check("non-run-folder string -> unchanged",
          f("x.xlsx", "Downloads") == "x.xlsx")
    check("extensionless name stamps whole name",
          f("noext", RUN) == f"noext {RUN}")


def test_consolidator_out_paths():
    print("consolidator out_path_for(day) stamps; day=None keeps legacy:")
    for mod in (crs, crd, chs, chl):
        stamped = paths.stamped_consolidated_filename(mod.FILENAME, RUN)
        expect = paths.output_day_dir(RUN) / "consolidated" / stamped
        got = mod.out_path_for(RUN)
        check(f"{mod.SUBDIR}: dated run -> stamped name", got == expect)
        check(f"{mod.SUBDIR}: stamped name carries the run folder",
              RUN in got.name and got.name != mod.FILENAME)
        check(f"{mod.SUBDIR}: day=None -> legacy fixed path",
              mod.out_path_for(None) == mod.OUT_PATH
              and mod.out_path_for(None).name == mod.FILENAME)


def test_tsn_exempt():
    print("TSN Highway Log is exempt (fixed name, ignores day):")
    p_none = ctsn.out_path_for(None)
    p_day = ctsn.out_path_for(RUN)
    check("TSN out_path_for ignores day (same path)", p_none == p_day)
    check("TSN keeps its unstamped fixed name", RUN not in p_day.name)


def test_compare_suggest_names_carry_date():
    print("comparison suggest_name carries a generated-on date:")
    today = paths.today_str()
    env_name = compare_env.HIGHWAY_LOG.suggest_name(
        "output/2026-06-16 ssor-prod", "output/2026-06-16 ars-prod")
    check("cross-env name ends .xlsx and has the side pair",
          env_name.endswith(".xlsx") and "_vs_" in env_name)
    check("cross-env name stamps today's date",
          today in env_name and bool(DATE_RE.search(env_name)))
    hl_name = compare_highway_log.suggest_name("tsmis_route_1.xlsx")
    check("TSMIS-vs-TSN name ends .xlsx and tags the route",
          hl_name.endswith(".xlsx") and "Route1" in hl_name)
    check("TSMIS-vs-TSN name stamps today's date", today in hl_name)


def main():
    test_stamp_helper()
    test_consolidator_out_paths()
    test_tsn_exempt()
    test_compare_suggest_names_carry_date()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL A1 FILENAME CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
