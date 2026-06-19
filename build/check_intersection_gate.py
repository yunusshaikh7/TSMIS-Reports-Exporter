"""Golden check for the app-wide intersection disable gate
(reports.DISABLED_EXPORT_SUBDIRS / enabled_export_reports + the GUI wiring).

Intersection Summary/Detail are export-only and not ready for users, so they're
disabled across the Export tab, the Everything tab, the Saved-reports library
and the matrix — through ONE gate — while keeping EXPORT_REPORTS indices stable
(manifests / env-scan / start_* index into the full list). Flip back by emptying
DISABLED_EXPORT_SUBDIRS.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_intersection_gate.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import reports
import gui_api

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_enabled_export_reports():
    print("reports.enabled_export_reports (gate + stable indices):")
    enabled = reports.enabled_export_reports()
    subdirs = {spec.subdir for _i, _l, _f, spec in enabled}
    check("intersection_summary dropped", "intersection_summary" not in subdirs)
    check("intersection_detail dropped", "intersection_detail" not in subdirs)
    check("five reports remain", len(enabled) == 5)
    check("the non-intersection reports are kept",
          {"ramp_summary", "ramp_detail", "highway_sequence",
           "highway_log", "highway_log_pdf"} <= subdirs)
    # idx must be the TRUE position in EXPORT_REPORTS (so callers stay aligned).
    check("each idx maps back to its own EXPORT_REPORTS row",
          all(reports.EXPORT_REPORTS[i] == (label, fmt, spec)
              for i, label, fmt, spec in enabled))
    check("intersection indices (5,6) are excluded",
          all(i not in (5, 6) for i, *_ in enabled))


def test_gui_initial_state():
    print("gui_api.get_initial_state reports list:")
    a = gui_api.GuiApi()
    a._started = True            # skip the one-time check/update worker launch
    init = a.get_initial_state()
    labels = [r["label"] for r in init["reports"]]
    check("no Intersection in the Export/Everything report list",
          not any("Intersection" in l for l in labels))
    check("five reports offered", len(init["reports"]) == 5)
    check("every report item carries a stable idx",
          all(isinstance(r.get("idx"), int) for r in init["reports"]))
    check("idx values match EXPORT_REPORTS labels",
          all(reports.EXPORT_REPORTS[r["idx"]][0] == r["label"]
              for r in init["reports"]))


def test_report_library_info():
    print("gui_api.report_library_info excludes Intersection:")
    a = gui_api.GuiApi()
    info = a.report_library_info()
    labels = [r["label"] for r in info["reports"]]
    check("no Intersection rows in Saved reports",
          not any("Intersection" in l for l in labels))
    check("five report rows", len(info["reports"]) == 5)


def test_start_rejects_disabled():
    print("start_export rejects a disabled-only selection:")
    a = gui_api.GuiApi()
    # 5,6 are Intersection Summary/Detail -> all disabled -> nothing to export.
    res = a.start_export([5, 6], "", False, 1)
    check("intersection-only export rejected", bool(res.get("error")))
    check("no task was claimed", a._task is None)


def test_toggle_back_on():
    print("flipping the gate off re-includes Intersection:")
    saved = reports.DISABLED_EXPORT_SUBDIRS
    try:
        reports.DISABLED_EXPORT_SUBDIRS = set()
        enabled = reports.enabled_export_reports()
        check("all seven reports enabled when the set is empty", len(enabled) == 7)
    finally:
        reports.DISABLED_EXPORT_SUBDIRS = saved
    check("restored to two disabled", len(reports.enabled_export_reports()) == 5)


def main():
    test_enabled_export_reports()
    test_gui_initial_state()
    test_report_library_info()
    test_start_rejects_disabled()
    test_toggle_back_on()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL INTERSECTION-GATE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
