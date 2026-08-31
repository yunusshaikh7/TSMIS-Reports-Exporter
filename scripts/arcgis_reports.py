"""The "Reports vs layers" registry — which TSMIS reports we can render from
the ArcGIS layer library, and what each one is wired to.

One row per report. Adding the next report is this table plus its build and
comparator modules; the GUI endpoints, the sub-tab's picker and
`check_arcgis_report` all derive from here, so none of them needs editing to
learn about a new one.

Kept out of `gui_arcgis_api` on purpose: the checks import this to derive what
must exist, and they must not have to import GUI code to do it.

`build` renders the report from the layers; `compare` diffs that build against
the app's own consolidated export; `exports` are the consolidators that can
produce the TSMIS side, in PREFERENCE order, and they supply the export-day
picker its run days.

There is more than one export consolidator per report because both editions
consolidate to the SAME shape — the PDF consolidator exists precisely so its
output lines up column-for-column with the Excel one, and each report's
PDF-vs-Excel self-check is what proves it. So a day that was exported in either
edition can be compared; Excel is preferred where a day has both. Modules are
named rather than imported so this table stays import-cheap — the layer builds
pull openpyxl and the whole clean-road substrate behind them.
"""
from collections import OrderedDict
from importlib import import_module
from pathlib import Path

# key -> (label, build module, compare module, (export consolidators, preferred first))
_REPORTS = OrderedDict((
    ("highway_detail", ("Highway Detail",
                        "arcgis_report_highway_detail",
                        "compare_highway_detail_arcgis",
                        ("consolidate_highway_detail",
                         "consolidate_tsmis_highway_detail_pdf"))),
    ("intersection_detail", ("Intersection Detail",
                             "arcgis_report_intersection_detail",
                             "compare_intersection_detail_arcgis",
                             ("consolidate_intersection_detail",
                              "consolidate_tsmis_intersection_detail_pdf"))),
))

KEYS = tuple(_REPORTS)
DEFAULT_KEY = KEYS[0]


def labels():
    """The picker's rows: `[{key, label}, …]` in registry order."""
    return [{"key": k, "label": _REPORTS[k][0]} for k in KEYS]


def label_of(key):
    spec = _REPORTS.get(key)
    return spec[0] if spec else key


def is_report(key):
    return key in _REPORTS


def resolve(key):
    """`(label, build, compare, exports)` with the modules imported; `exports`
    is the tuple of export consolidators, preferred first.

    Raises KeyError for an unknown key — every caller reaches this only after
    `is_report`, so an unknown key here is a wiring bug, not user input."""
    label, build, compare, exports = _REPORTS[key]
    return (label, import_module(build), import_module(compare),
            tuple(import_module(m) for m in exports))


def export_days(key):
    """`[{day, path, subdir}, …]` — every run day that has a consolidated
    export this report can be compared against, newest first, one row per day.

    A day exported in both editions appears ONCE, as the preferred edition, so
    the picker never offers the same day twice."""
    import paths

    _label, _build, _compare, exports = resolve(key)
    seen, days = set(), []
    for mod in exports:
        for day in paths.list_output_days_for_report(mod.SUBDIR):
            if day in seen:
                continue
            p = mod.out_path_for(day)
            if p and Path(p).is_file():
                seen.add(day)
                days.append({"day": day, "path": str(p), "subdir": mod.SUBDIR})
    days.sort(key=lambda d: d["day"], reverse=True)
    return days


def export_path(key, day):
    """The consolidated export to compare against for `day`, or None."""
    for row in export_days(key):
        if row["day"] == day:
            return Path(row["path"])
    return None
