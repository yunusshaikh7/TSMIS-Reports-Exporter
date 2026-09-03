"""The "Reports vs layers" registry — every TSMIS report the ArcGIS layer
library renders (or will), and what each one is wired to.

One row per report FAMILY, in the site's own report order. The rows are the
whole report set on purpose: the ArcGIS tab's matrix lists every report, and a
row whose build has not landed yet still appears — greyed, saying so — instead
of the tab quietly showing only what happens to work. Adding a report's build is
this table plus its build and comparator modules; the matrix, the GUI endpoints,
the `#mock` preview and `check_arcgis_matrix` all derive from here, so none of
them needs editing to learn about a new one.

Kept out of `gui_arcgis_api` on purpose: the checks import this to derive what
must exist, and they must not have to import GUI code to do it.

`build` renders the report from the layers (None = not rendered yet); `compare`
diffs that build against the app's own consolidated export (None = no
comparison yet); `exports` are the consolidators that can produce the TSMIS
side, in PREFERENCE order. There is more than one export consolidator per
report because both editions consolidate to the SAME shape — the PDF
consolidator exists precisely so its output lines up column-for-column with the
Excel one, and each report's PDF-vs-Excel self-check is what proves it. So a day
that was exported in either edition can be compared; Excel is preferred where a
day has both. Modules are named rather than imported so this table stays
import-cheap — the layer builds pull openpyxl and the whole clean-road
substrate behind them.

The three Clean Road files are rows too (owner decision 2026-09-02): the site
now exports them, so "our layer build vs the site's export" is TSMIS vs TSMIS
exactly like the report rows. Clean Road Highway already has its build (the
Clean Road sub-tab's CA HIGHWAYS workbook); its comparison waits on a
consolidator for the site's export, which waits on real per-route files.
"""
from collections import OrderedDict, namedtuple
from importlib import import_module

Spec = namedtuple("Spec", "key label code build compare exports subdirs why")

_NO_BUILD = "not rendered from the layers yet"
_NO_COMPARE = ("no comparison yet — the site's export has no consolidator "
               "until real per-route files are censused")

# key -> (build module, compare module, (export consolidators, preferred first))
_REPORTS = OrderedDict((
    ("ramp_summary", (None, None, ("consolidate_ramp_summary",))),
    ("ramp_detail", (None, None,
                     ("consolidate_ramp_detail",
                      "consolidate_tsmis_ramp_detail_pdf"))),
    ("highway_sequence", (None, None,
                          ("consolidate_highway_sequence",
                           "consolidate_tsmis_highway_sequence_pdf"))),
    ("highway_log", (None, None,
                     ("consolidate_highway_log",
                      "consolidate_tsmis_highway_log_pdf"))),
    ("intersection_summary", (None, None, ("consolidate_intersection_summary",))),
    ("intersection_detail", ("arcgis_report_intersection_detail",
                             "compare_intersection_detail_arcgis",
                             ("consolidate_intersection_detail",
                              "consolidate_tsmis_intersection_detail_pdf"))),
    ("highway_detail", ("arcgis_report_highway_detail",
                        "compare_highway_detail_arcgis",
                        ("consolidate_highway_detail",
                         "consolidate_tsmis_highway_detail_pdf"))),
    ("highway_summary", (None, None, ("consolidate_highway_summary",))),
    ("clean_highway", ("consolidate_clean_highway", None, ())),
    ("clean_intersection", (None, None, ())),
    ("clean_ramp", (None, None, ())),
))

KEYS = tuple(_REPORTS)


def is_report(key):
    return key in _REPORTS


def _why(build, compare, exports):
    if build is None:
        return _NO_BUILD
    if compare is None or not exports:
        return _NO_COMPARE
    return ""


def _catalog_row(key):
    """(label, short code) from the report-metadata source of truth. Imported
    lazily so this registry stays cheap to import."""
    import report_catalog
    labels = {e.key: e.label for e in report_catalog.EXPORT}
    return labels.get(key, key), report_catalog.short_code(key)


def spec(key):
    """The resolved row: label/code from the catalog, the build and compare
    MODULES (None where the lane has not rendered the report yet), the export
    consolidators (preferred first) and their subdirs, and `why` — the one-line
    reason the row cannot be compared yet ("" when it can).

    Raises KeyError for an unknown key — every caller reaches this only after
    `is_report`, so an unknown key here is a wiring bug, not user input."""
    build, compare, exports = _REPORTS[key]
    label, code = _catalog_row(key)
    build_mod = import_module(build) if build else None
    cmp_mod = import_module(compare) if compare else None
    export_mods = tuple(import_module(m) for m in exports)
    return Spec(key, label, code, build_mod, cmp_mod, export_mods,
                tuple(m.SUBDIR for m in export_mods),
                _why(build, compare, exports))


def resolve(key):
    """`(label, build, compare, exports)` with the modules imported — `build` /
    `compare` are None for a row the lane has not rendered yet."""
    s = spec(key)
    return s.label, s.build, s.compare, s.exports


def can_build(key):
    return _REPORTS[key][0] is not None


def can_compare(key):
    build, compare, exports = _REPORTS[key]
    return build is not None and compare is not None and bool(exports)


def labels():
    """The matrix's rows: `[{key, label, code, buildable, comparable, why}, …]`
    in registry order."""
    out = []
    for k in KEYS:
        build, compare, exports = _REPORTS[k]
        label, code = _catalog_row(k)
        out.append({"key": k, "label": label, "code": code,
                    "buildable": build is not None,
                    "comparable": can_compare(k),
                    "why": _why(build, compare, exports)})
    return out


def label_of(key):
    return _catalog_row(key)[0] if key in _REPORTS else key


DEFAULT_KEY = next(k for k in KEYS if can_compare(k))
