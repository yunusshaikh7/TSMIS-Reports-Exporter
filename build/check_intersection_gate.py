"""Golden check for the app-wide export disable GATE
(reports.DISABLED_EXPORT_SUBDIRS / is_export_disabled / enabled_export_reports /
export_reports_status + the GUI wiring).

As of v0.16.x the gate is EMPTY — every export report, INCLUDING Intersection
Summary/Detail (and, as of CR-002, Intersection Detail (PDF)), is enabled (they
live on the development site; users switch via Settings ▸ "Use development site").
This check locks (a) the default all-enabled state and (b) that the gate MECHANISM
still works: a subdir added back to the set is SHOWN GREYED (not hidden), excluded
from the saved-reports library, and rejected by the start_* guards server-side —
with EXPORT_REPORTS indices kept stable (manifests / env-scan / start_* index into
the full list).

The expected count is DERIVED from the registry (`len(reports.EXPORT_REPORTS)`), not
hard-coded, so adding a report (CR-002's Int-Detail-PDF) doesn't require bumping a
literal here — the gate behavior is what's under test, not the count.

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

# DERIVED counts — adding a report flows through here without a literal edit.
# The gate is EMPTY again as of v0.19.1 (the v0.18.1 reserved Highway pair's
# export is now enabled); a future re-disable goes back into _RESERVED.
N_REPORTS = len(reports.EXPORT_REPORTS)
_RESERVED = set()
N_ENABLED = N_REPORTS - len(_RESERVED)


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_default_all_enabled():
    print(f"default gate = empty; all {N_ENABLED} reports enabled:")
    check("DISABLED_EXPORT_SUBDIRS is empty (every report enabled)",
          reports.DISABLED_EXPORT_SUBDIRS == _RESERVED)
    enabled = reports.enabled_export_reports()
    check(f"{N_ENABLED} export reports enabled (all of them)",
          len(enabled) == N_ENABLED)
    subdirs = {spec.subdir for _i, _l, _f, spec in enabled}
    check("Intersection Summary + Detail (+ the PDF variant) are enabled",
          {"intersection_summary", "intersection_detail", "intersection_detail_pdf"} <= subdirs)
    check("the Highway Detail/Summary pair is enabled (v0.19.1)",
          {"highway_detail", "highway_summary"} <= subdirs)
    status = reports.export_reports_status()
    disabled = {label for _i, label, _f, _s, d in status if d}
    check(f"all {N_REPORTS} present; none flagged disabled",
          len(status) == N_REPORTS and disabled == set())
    check("each report's row maps back to its own EXPORT_REPORTS entry",
          all(reports.EXPORT_REPORTS[i] == (label, fmt, spec)
              for i, label, fmt, spec, _d in status))


def test_gui_initial_state_all_enabled():
    print(f"gui_api.get_initial_state (all {N_REPORTS} offered; none greyed):")
    a = gui_api.GuiApi()
    a._started = True            # skip the one-time check/update worker launch
    init = a.get_initial_state()
    check(f"{N_REPORTS} reports offered", len(init["reports"]) == N_REPORTS)
    check("no report greyed (the Highway pair enabled in v0.19.1)",
          {r["label"] for r in init["reports"] if r["disabled"]} == set())
    check("Highway Detail/Summary shown AND pickable",
          all(any(r["label"] == lbl and not r["disabled"] for r in init["reports"])
              for lbl in ("Highway Detail", "Highway Summary")))
    check("Intersection shown AND pickable",
          any("Intersection" in r["label"] and not r["disabled"]
              for r in init["reports"]))
    # Each payload report's label matches its stable KEY's registry row. The list is
    # in PICKER display order now, so idx is NOT a registry index — verify by key.
    _label_by_key = {spec.subdir: label for label, _f, spec in reports.EXPORT_REPORTS}
    check("each report's label matches its stable key's registry row",
          all(_label_by_key.get(r["key"]) == r["label"] for r in init["reports"]))
    check("idx is the display position (0..N-1 in list order)",
          [r["idx"] for r in init["reports"]] == list(range(N_REPORTS)))


def test_report_library_includes_all():
    print(f"gui_api.report_library_info lists all {N_ENABLED} enabled reports:")
    a = gui_api.GuiApi()
    info = a.report_library_info()
    check(f"saved-reports library lists the {N_ENABLED} enabled reports",
          len(info["reports"]) == N_ENABLED)


def test_gate_mechanism_still_works():
    print("the disable gate still greys + rejects a RE-disabled subdir:")
    saved = reports.DISABLED_EXPORT_SUBDIRS
    try:
        reports.DISABLED_EXPORT_SUBDIRS = {"intersection_summary"}
        enabled = reports.enabled_export_reports()
        ensub = {spec.subdir for _i, _l, _f, spec in enabled}
        check("re-disabled subdir dropped from enabled",
              "intersection_summary" not in ensub and len(enabled) == N_REPORTS - 1)
        status = reports.export_reports_status()
        disabled = {label for _i, label, _f, _s, d in status if d}
        check("exactly the re-disabled report flagged disabled",
              disabled == {"Intersection Summary"})
        a = gui_api.GuiApi()
        # intersection_summary is the family key == export-op key (P3); when it's
        # app-wide-disabled, the start guard must reject it server-side.
        res = a.start_export(["intersection_summary"], "", False, 1)
        check("a disabled-only export is rejected (no worker launched)",
              bool(res.get("error")))
        check("no task was claimed", a._task is None)
        a2 = gui_api.GuiApi()
        a2._started = True
        init = a2.get_initial_state()
        check("re-disabled report is SHOWN greyed (not hidden)",
              any(r["label"] == "Intersection Summary" and r["disabled"]
                  for r in init["reports"])
              and len(init["reports"]) == N_REPORTS)
    finally:
        reports.DISABLED_EXPORT_SUBDIRS = saved
    check("restored to the default gate (empty — every report enabled)",
          len(reports.enabled_export_reports()) == N_ENABLED)


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
