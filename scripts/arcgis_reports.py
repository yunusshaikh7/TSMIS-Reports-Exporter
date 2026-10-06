"""The ArcGIS report registry — every TSMIS report the ArcGIS layer library
renders (or will), what each one is wired to, and the export editions that are
compared against it.

One row per report FAMILY, in the site's own report order. The rows are the
whole report set on purpose: the ArcGIS ▸ ArcGIS reports tab lists every
report, and a row whose build has not landed yet still appears (greyed, saying
so) instead of the tab quietly showing only what happens to work. Adding a
report's build is this table plus its build and comparator modules; the two
sub-tabs, the GUI endpoints, the `#mock` preview and `check_arcgis_matrix` all
derive from here, so none of them needs editing to learn about a new one.

Kept out of `gui_arcgis_api` on purpose: the checks import this to derive what
must exist, and they must not have to import GUI code to do it.

`build` renders the report from the layers (None = not rendered yet); `compare`
diffs that build against the app's own consolidated export (None = no
comparison yet). Modules are named rather than imported so this table stays
import-cheap — the layer builds pull openpyxl and the whole clean-road
substrate behind them.

Each report has ONE ArcGIS build (an Excel workbook), refreshed in place on the
ArcGIS reports tab. Its EDITIONS are every export the site offers for that
report — the Excel export and the print (PDF) edition — and each one is its own
row on the Reports vs ArcGIS matrix, compared against that same build. Editions
are DERIVED from `report_catalog.EXPORT` (a print edition's key is its family's
plus `_pdf`; Ramp Summary's Excel sibling is `_excel`), and an edition can be
compared only when the app consolidates it. Both editions consolidate to the
SAME shape — that is what each report's PDF-vs-Excel self-check proves — so one
comparator per report serves both.

The three Clean Road files are rows too (owner decision 2026-09-02): the site
now exports them, so "our layer build vs the site's export" is TSMIS vs TSMIS
exactly like the report rows. Clean Road Highway already has its build (the
CA HIGHWAYS workbook), and the site's export of every Clean Road file
consolidates since v0.48.0; the comparator between the two is not written yet.
"""
from collections import OrderedDict, namedtuple
from functools import lru_cache
from importlib import import_module

Spec = namedtuple("Spec", "key label code build compare exports subdirs why")
Edition = namedtuple("Edition",
                     "key family label code subdir consolidator comparable why")

_NO_BUILD = "no ArcGIS build of this report yet"
_NO_COMPARE = "no comparison of the ArcGIS build against the site's export yet"
_NO_EDITION = "this edition is not consolidated yet, so it cannot be compared"

# key -> (build module, compare module)
_REPORTS = OrderedDict((
    ("ramp_summary", (None, None)),
    ("ramp_detail", (None, None)),
    ("highway_sequence", (None, None)),
    ("highway_log", (None, None)),
    ("intersection_summary", (None, None)),
    ("intersection_detail", ("arcgis_report_intersection_detail",
                             "compare_intersection_detail_arcgis")),
    ("highway_detail", ("arcgis_report_highway_detail",
                        "compare_highway_detail_arcgis")),
    ("highway_summary", (None, None)),
    ("clean_highway", ("consolidate_clean_highway", None)),
    ("clean_intersection", (None, None)),
    ("clean_ramp", (None, None)),
))

KEYS = tuple(_REPORTS)

# An export key names its family directly or by one of these suffixes.
_EDITION_SUFFIXES = ("_pdf", "_excel")


def is_report(key):
    return key in _REPORTS


def family_of(export_key):
    """The registry family an export key belongs to (`highway_detail_pdf` ->
    'highway_detail'), or None for an export with no family here."""
    if export_key in _REPORTS:
        return export_key
    for suffix in _EDITION_SUFFIXES:
        base = export_key[:-len(suffix)]
        if export_key.endswith(suffix) and base in _REPORTS:
            return base
    return None


def _why(build, compare, has_editions):
    if build is None:
        return _NO_BUILD
    if compare is None or not has_editions:
        return _NO_COMPARE
    return ""


@lru_cache(maxsize=1)
def _catalog():
    """(labels, codes, consolidator module names by subdir, export keys in
    catalog order) from the report-metadata source of truth. Imported lazily —
    the catalog pulls every export/consolidate module — and read once."""
    import report_catalog
    labels = {e.key: e.label for e in report_catalog.EXPORT}
    codes = {e.key: report_catalog.short_code(e.key) for e in report_catalog.EXPORT}
    consolidators = {sub: m.__name__ for sub, m in
                     report_catalog.consolidator_by_export_subdir().items()}
    subdirs = {e.key: e.spec.subdir for e in report_catalog.EXPORT}
    return labels, codes, consolidators, subdirs, tuple(labels)


def _catalog_row(key):
    labels, codes, _cons, _subs, _order = _catalog()
    return labels.get(key, key), codes.get(key, key)


@lru_cache(maxsize=1)
def editions():
    """Every export edition, family by family in registry order — the family's
    own key first (its established row), then its siblings in catalog order.
    These are the Reports vs ArcGIS matrix rows."""
    labels, codes, consolidators, subdirs, order = _catalog()
    out = []
    for family in KEYS:
        build, compare = _REPORTS[family]
        keys = [k for k in order if family_of(k) == family]
        keys.sort(key=lambda k: k != family)       # stable: the family first
        for key in keys:
            sub = subdirs[key]
            cons = consolidators.get(sub)
            comparable = bool(build and compare and cons)
            if build is None:
                why = _NO_BUILD
            elif compare is None:
                why = _NO_COMPARE
            elif cons is None:
                why = _NO_EDITION
            else:
                why = ""
            out.append(Edition(key, family, labels[key], codes[key], sub,
                               cons, comparable, why))
    return tuple(out)


def edition_keys():
    return tuple(e.key for e in editions())


def is_edition(key):
    return key in edition_keys()


def edition(key):
    """The resolved edition row. Raises KeyError for an unknown key — callers
    reach this only after `is_edition`, so an unknown key is a wiring bug."""
    for e in editions():
        if e.key == key:
            return e
    raise KeyError(key)


def editions_of(family):
    return tuple(e for e in editions() if e.family == family)


def spec(key):
    """The resolved family row: label/code from the catalog, the build and
    compare MODULES (None where the lane has not rendered the report yet), the
    consolidators of its comparable-shaped editions (the family's own edition
    first) and their subdirs, and `why` — the one-line reason the report cannot
    be compared yet ("" when it can).

    Raises KeyError for an unknown key — every caller reaches this only after
    `is_report`, so an unknown key here is a wiring bug, not user input."""
    build, compare = _REPORTS[key]
    label, code = _catalog_row(key)
    build_mod = import_module(build) if build else None
    cmp_mod = import_module(compare) if compare else None
    eds = [e for e in editions_of(key) if e.consolidator]
    export_mods = tuple(import_module(e.consolidator) for e in eds)
    return Spec(key, label, code, build_mod, cmp_mod, export_mods,
                tuple(e.subdir for e in eds), _why(build, compare, bool(eds)))


def resolve(key):
    """`(label, build, compare, exports)` with the modules imported — `build` /
    `compare` are None for a row the lane has not rendered yet."""
    s = spec(key)
    return s.label, s.build, s.compare, s.exports


def can_build(key):
    return _REPORTS[key][0] is not None


def can_compare(key):
    return any(e.comparable for e in editions_of(key))


def labels():
    """The ArcGIS reports tab's rows: `[{key, label, code, buildable,
    comparable, why, editions}, …]` in registry order; `editions` are the
    family's export edition keys."""
    out = []
    for k in KEYS:
        build, compare = _REPORTS[k]
        label, code = _catalog_row(k)
        eds = editions_of(k)
        out.append({"key": k, "label": label, "code": code,
                    "buildable": build is not None,
                    "comparable": can_compare(k),
                    "why": _why(build, compare, any(e.consolidator for e in eds)),
                    "editions": [e.key for e in eds]})
    return out


def label_of(key):
    """A family's or an edition's display label."""
    if key in _REPORTS or is_edition(key):
        return _catalog_row(key)[0]
    return key


DEFAULT_KEY = next(k for k in KEYS
                   if _REPORTS[k][0] is not None and _REPORTS[k][1] is not None)
