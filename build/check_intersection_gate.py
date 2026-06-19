"""Golden check for the app-wide export disable GATE
(reports.DISABLED_EXPORT_SUBDIRS / is_export_disabled / enabled_export_reports /
export_reports_status + the GUI wiring).

As of v0.16.x the gate is EMPTY — all seven export reports, INCLUDING Intersection
Summary/Detail, are enabled (they live on the development site; users switch via
Settings ▸ "Use development site"). This check locks (a) the default all-enabled
state and (b) that the gate MECHANISM still works: a subdir added back to the set
is SHOWN GREYED (not hidden), excluded from the saved-reports library, and
rejected by the start_* guards server-side — with EXPORT_REPORTS indices kept
stable (manifests / env-scan / start_* index into the full list).

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


def test_default_all_enabled():
    print("default gate is empty — all seven reports enabled (incl. Intersection):")
    check("DISABLED_EXPORT_SUBDIRS is empty by default",
          reports.DISABLED_EXPORT_SUBDIRS == set())
    enabled = reports.enabled_export_reports()
    check("all seven export reports enabled", len(enabled) == 7)
    subdirs = {spec.subdir for _i, _l, _f, spec in enabled}
    check("Intersection Summary + Detail are now included",
          {"intersection_summary", "intersection_detail"} <= subdirs)
    status = reports.export_reports_status()
    check("all seven present, none flagged disabled",
          len(status) == 7 and not any(d for *_rest, d in status))
    check("each idx maps back to its own EXPORT_REPORTS row",
          all(reports.EXPORT_REPORTS[i] == (label, fmt, spec)
              for i, label, fmt, spec, _d in status))


def test_gui_initial_state_all_enabled():
    print("gui_api.get_initial_state (all seven offered, none greyed):")
    a = gui_api.GuiApi()
    a._started = True            # skip the one-time check/update worker launch
    init = a.get_initial_state()
    check("seven reports offered", len(init["reports"]) == 7)
    check("none greyed by default", not any(r["disabled"] for r in init["reports"]))
    check("Intersection shown AND pickable",
          any("Intersection" in r["label"] and not r["disabled"]
              for r in init["reports"]))
    check("idx values match EXPORT_REPORTS labels",
          all(reports.EXPORT_REPORTS[r["idx"]][0] == r["label"]
              for r in init["reports"]))


def test_report_library_includes_all():
    print("gui_api.report_library_info now includes Intersection:")
    a = gui_api.GuiApi()
    info = a.report_library_info()
    check("saved-reports library lists all seven", len(info["reports"]) == 7)


def test_gate_mechanism_still_works():
    print("the disable gate still greys + rejects a RE-disabled subdir:")
    saved = reports.DISABLED_EXPORT_SUBDIRS
    try:
        reports.DISABLED_EXPORT_SUBDIRS = {"intersection_summary"}
        enabled = reports.enabled_export_reports()
        ensub = {spec.subdir for _i, _l, _f, spec in enabled}
        check("re-disabled subdir dropped from enabled",
              "intersection_summary" not in ensub and len(enabled) == 6)
        status = reports.export_reports_status()
        disabled = {label for _i, label, _f, _s, d in status if d}
        check("exactly the re-disabled report flagged disabled",
              disabled == {"Intersection Summary"})
        idx = next(i for i, (_l, _f, s) in enumerate(reports.EXPORT_REPORTS)
                   if s.subdir == "intersection_summary")
        a = gui_api.GuiApi()
        res = a.start_export([idx], "", False, 1)
        check("a disabled-only export is rejected (no worker launched)",
              bool(res.get("error")))
        check("no task was claimed", a._task is None)
        a2 = gui_api.GuiApi()
        a2._started = True
        init = a2.get_initial_state()
        check("re-disabled report is SHOWN greyed (not hidden)",
              any(r["label"] == "Intersection Summary" and r["disabled"]
                  for r in init["reports"])
              and len(init["reports"]) == 7)
    finally:
        reports.DISABLED_EXPORT_SUBDIRS = saved
    check("restored to all seven enabled",
          len(reports.enabled_export_reports()) == 7)


def main():
    test_default_all_enabled()
    test_gui_initial_state_all_enabled()
    test_report_library_includes_all()
    test_gate_mechanism_still_works()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL EXPORT-GATE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
