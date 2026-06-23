"""Golden check for A2 — the cross-env compare dropdowns only offer run folders
that actually contain the chosen report (v0.12.0).

Covers paths.list_output_days_for_report, the GuiApi.get_compare_folders bridge
method (folders-kind filters; files-kind / bad index fall back to all folders),
and the start_compare_env server-side preflight that rejects a picked run folder
lacking the report's export.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_a2_compare_filter.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import paths
import gui_api
import reports

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _mk(tmp, run, subdir, with_file=True):
    d = tmp / run / subdir
    d.mkdir(parents=True, exist_ok=True)
    if with_file:
        (d / "x.xlsx").write_bytes(b"PK")


def _folders_idx(subdir):
    for i, row in enumerate(reports.COMPARE_REPORTS):
        _l, m, k, _g = row[:4]
        if k == "folders" and getattr(m, "subdir", None) == subdir:
            return i
    return None


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_a2_"))
    orig = paths.OUTPUT_ROOT
    paths.OUTPUT_ROOT = tmp
    gui_api.OUTPUT_ROOT = tmp            # gui_api imported it by value
    try:
        _mk(tmp, "2026-06-16 ssor-prod", "highway_log")
        _mk(tmp, "2026-06-16 ars-prod", "ramp_detail")
        _mk(tmp, "2026-06-15 ssor-prod", "highway_log", with_file=False)  # empty

        print("paths.list_output_days_for_report:")
        check("only the NON-EMPTY highway_log run is offered",
              paths.list_output_days_for_report("highway_log")
              == ["2026-06-16 ssor-prod"])
        check("ramp_detail filter picks its own run",
              paths.list_output_days_for_report("ramp_detail")
              == ["2026-06-16 ars-prod"])
        check("unknown subdir -> empty",
              paths.list_output_days_for_report("nope") == [])
        check("list_output_days still returns all three, newest-first",
              paths.list_output_days() == ["2026-06-16 ssor-prod",
                                           "2026-06-16 ars-prod",
                                           "2026-06-15 ssor-prod"])

        print("GuiApi.get_compare_folders:")
        api = gui_api.GuiApi()
        hl_idx = _folders_idx("highway_log")
        check("a folders-kind highway_log comparison exists", hl_idx is not None)
        hl_key = reports.COMPARE_KEYS[hl_idx]
        check("folders-kind filters to runs with the report",
              api.get_compare_folders(hl_key).get("folders")
              == ["2026-06-16 ssor-prod"])
        files_key = next((reports.COMPARE_KEYS[i]
                          for i, r in enumerate(reports.COMPARE_REPORTS)
                          if r[2] == "files"), None)
        check("files-kind returns ALL folders (no dropdown filter)",
              set(api.get_compare_folders(files_key).get("folders"))
              == set(paths.list_output_days()))
        check("bad key falls back to all folders (never empty by mistake)",
              set(api.get_compare_folders("__nope__").get("folders"))
              == set(paths.list_output_days()))

        print("start_compare_env preflight:")
        res = api.start_compare_env(hl_key, "2026-06-16 ssor-prod",
                                    "2026-06-16 ars-prod", True, False)
        check("rejects a side lacking the report's export",
              isinstance(res, dict) and bool(res.get("error")))
        check("the rejection names the offending folder",
              "ars-prod" in (res.get("error") or ""))
        check("a rejected preflight left the task slot free",
              api._try_claim_task("x") is True)
        api._release_task()
    finally:
        paths.OUTPUT_ROOT = orig
        gui_api.OUTPUT_ROOT = orig
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL A2 COMPARE-FILTER CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
