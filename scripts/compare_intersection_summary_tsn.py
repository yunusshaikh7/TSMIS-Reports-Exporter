"""Build the TSMIS-vs-TSN Intersection Summary discrepancy workbook (AGGREGATE).

The Ramp Summary recipe applied to the intersection category taxonomy: each side
reduces to ONE statewide {category: count} table, compared with has_route=False
(key = category, field = count). The category schema (the UNION of both systems'
11 blocks — incl. the diverged CONTROL TYPES / INTERSECTION TYPE codes that show
one-sided) + the block-walk mapper + the familiar-layout sheet all live in
summary_layout (INTERSECTION_SUMMARY_SPEC), shared with the consolidator.

  * TSMIS side — the CONSOLIDATED Intersection Summary workbook (one row per route,
    one column per category key); summed column-by-column.
  * TSN side — the statewide PDF: a 3-COLUMN page (left/middle/right bands), each
    band block-walked with the SAME summary_layout.counts_from_rows the TSMIS
    consolidator uses, so the two sides can't drift.

Reconciled on the 6.19 ground truth: TSMIS 16473 vs TSN 16626; CONTROL TYPES
(TSN J-P signals vs TSMIS S/O/Q/R) and INTERSECTION TYPE (TSMIS R/C/P) diverge →
those codes compare one-sided (no crosswalk; user decision). Console-free.
"""
import re
from pathlib import Path

try:
    import pdfplumber
    from openpyxl import load_workbook
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_tsn_common as ctc
import summary_layout
from compare_core import CompareSchema
from paths import today_str

REPORT_NAME = "Intersection Summary"
TSMIS_SHEET = "Intersection Summary"            # consolidated per-route sheet
NORMALIZED_SHEET = "Intersection Summary (TSN)"  # library normalized 2-col workbook

_SPEC = summary_layout.INTERSECTION_SUMMARY_SPEC
_CATEGORIES = _SPEC.categories()                 # [(key, slug), ...] incl. Total
# Column-header (compare key) -> slug for reading the consolidated workbook.
_KEY_TO_SLUG = {c.key: c.slug for sec in _SPEC.sections for c in sec.cats}
_KEY_TO_SLUG[_SPEC.total.key] = _SPEC.total.slug

# 3-column band boundaries on the statewide page (calibrated to the raw geometry).
_BAND_LEFT, _BAND_RIGHT = 190, 495
_TOTAL_RE = re.compile(r"Total Intersections\s*=\s*([\d,]+)", re.IGNORECASE)

_SCHEMA = CompareSchema(
    report_name=REPORT_NAME,
    header=["Category", "Count"],
    side_a="TSMIS",
    side_b="TSN",
    id_noun="category",
    id_noun_plural="categories",
    sides_noun="systems",
    cmp_widths={"Count": 12},
    data_widths={"Count": 12},
    scope_flat="Statewide category totals",
    one_sided_note_extra=" (a category one system classifies and the other doesn't)",
    extra_sheet_writer=summary_layout.make_extra_sheet_writer(_SPEC),
)


# --------------------------------------------------------------------------- #
# TSN side: 3-column statewide PDF -> {slug: count}
# --------------------------------------------------------------------------- #
def _cluster(words):
    """A band's words -> [(count_or_None, code-text)] rows (top-clustered, x-sorted)."""
    if not words:
        return []
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows, cur, ct = [], [], None
    for w in words:
        if ct is None or abs(w["top"] - ct) <= 3:
            cur.append(w)
            ct = ct if ct is not None else w["top"]
        else:
            rows.append(cur)
            cur, ct = [w], w["top"]
    if cur:
        rows.append(cur)
    out = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        ts = [w["text"] for w in row]
        if ts and re.fullmatch(r"-?[\d,]+", ts[0]) and any(c.isdigit() for c in ts[0]):
            out.append((int(ts[0].replace(",", "")), " ".join(ts[1:])))
        else:
            out.append((None, " ".join(ts)))
    return out


def _data_page(pdf):
    for pg in pdf.pages:
        if _TOTAL_RE.search(pg.extract_text() or ""):
            return pg
    return pdf.pages[-1]


def parse_tsn_pdf(path):
    """The statewide TSN Intersection Summary PDF -> {slug: count}. Splits the page
    into 3 column bands and block-walks each independently (so each column's
    count+label rows pair correctly), merging the per-band counts."""
    with pdfplumber.open(path) as pdf:
        page = _data_page(pdf)
        bands = [[], [], []]
        for w in page.extract_words():
            x = w["x0"]
            bands[0 if x < _BAND_LEFT else (1 if x < _BAND_RIGHT else 2)].append(w)
        counts = {}
        for band in bands:
            for slug, v in summary_layout.counts_from_rows(_SPEC, _cluster(band)).items():
                counts[slug] = counts.get(slug, 0) + v
        m = _TOTAL_RE.search(page.extract_text() or "")
        counts["total_intersections"] = int(m.group(1).replace(",", "")) if m else None
    return counts


def _load_tsn(path):
    """TSN side -> {slug: count}. Raw statewide PDF, or the library's normalized
    Category|Count workbook."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return parse_tsn_pdf(path)
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {path.name}: {type(e).__name__}: {e}")
    try:
        sn = NORMALIZED_SHEET if NORMALIZED_SHEET in wb.sheetnames else wb.sheetnames[0]
        key_to_slug = {k: s for k, s in _CATEGORIES}
        rec = {}
        it = wb[sn].iter_rows(values_only=True)
        next(it, None)
        for r in it:
            if not r or r[0] is None:
                continue
            slug = key_to_slug.get(str(r[0]).strip())
            if slug is not None and len(r) > 1 and isinstance(r[1], (int, float)):
                rec[slug] = int(r[1])
        return rec
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# TSMIS side: SUM the consolidated workbook's per-route columns -> {slug: count}
# --------------------------------------------------------------------------- #
def _load_tsmis(path):
    """TSMIS side -> {slug: count}. Sums each category column of the consolidated
    Intersection Summary workbook's per-route sheet."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if TSMIS_SHEET not in wb.sheetnames:
            raise ValueError(f"{name} has no '{TSMIS_SHEET}' sheet — pick the "
                             "consolidated TSMIS Intersection Summary workbook.")
        it = wb[TSMIS_SHEET].iter_rows(values_only=True)
        header = next(it, None) or ()
        col_slug = {i: _KEY_TO_SLUG[str(h).strip()]
                    for i, h in enumerate(header)
                    if h is not None and str(h).strip() in _KEY_TO_SLUG}
        if "Route" not in [str(h).strip() for h in header if h is not None]:
            raise ValueError(f"{name} isn't a consolidated Intersection Summary "
                             "workbook (no 'Route' column) — consolidate first.")
        sums = {}
        for row in it:
            if not row or all(c is None for c in row):
                continue
            for i, slug in col_slug.items():
                if i < len(row) and isinstance(row[i], (int, float)):
                    sums[slug] = sums.get(slug, 0) + int(row[i])
        return sums
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# rows + adapter surface
# --------------------------------------------------------------------------- #
def _rows(counts, side):
    """Rows for `side` ('tsmis'|'tsn'): the side's applicable categories only, so a
    category the other system doesn't classify stays ONE-SIDED (Only in …)."""
    return [[key, int(counts.get(slug, 0) or 0)]
            for key, slug in _SPEC.categories_for(side)]


def suggest_name(tsmis_path):
    return f"TSMIS_vs_TSN_IntersectionSummary_Comparison {today_str()}.xlsx"


def _load_pair(tsmis_path, tsn_path):
    """(rows_t, rows_n, warnings) for the shared driver. The parse-integrity warning is
    scoped to the categories TSN ACTUALLY classifies (the TSN-applicable set) — the
    TSMIS-only codes are legitimately absent from the TSN PDF and must NOT be flagged."""
    tsmis_counts = _load_tsmis(tsmis_path)
    tsn_counts = _load_tsn(tsn_path)
    warnings = []
    if tsn_counts.get("total_intersections") is None:
        warnings.append("TSN parse did not find the 'Total Intersections' figure — "
                        "the statewide page may not have parsed; verify the TSN PDF.")
    missing = [key for key, slug in _SPEC.categories_for("tsn")
               if tsn_counts.get(slug) is None]
    if missing:
        warnings.append(f"TSN parse did not find {len(missing)} expected categor"
                        f"{'y' if len(missing) == 1 else 'ies'}: "
                        + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
    return _rows(tsmis_counts, "tsmis"), _rows(tsn_counts, "tsn"), warnings


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas"):
    """Build the Intersection Summary TSMIS-vs-TSN AGGREGATE comparison workbook(s)."""
    return ctc.run_files_compare(
        _SCHEMA, tsmis_path, tsn_path, out_path,
        banner="Intersection Summary Comparison — TSMIS vs TSN (statewide category counts)",
        has_route=False, loader=_load_pair, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (pdfplumber, openpyxl).",
        events=events, confirm_overwrite=confirm_overwrite, mode=mode)
