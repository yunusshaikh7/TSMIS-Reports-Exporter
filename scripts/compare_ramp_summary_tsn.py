"""Build the TSMIS-vs-TSN Ramp Summary discrepancy workbook (the AGGREGATE recipe).

Unlike the FLAT comparators (Ramp Detail etc.) that match per-postmile rows, the
two SUMMARY reports compare ONE statewide category-count table per side:

  * TSN side — the statewide "Ramp Summary Statewide" PDF: a single page of
    category counts (Highway Groups / On/Off / Population / Ramp Types) parsed with
    the same geometry helpers the per-route consolidator uses.
  * TSMIS side — the CONSOLIDATED Ramp Summary workbook: its per-route "TSAR Ramps
    Summary" sheet is SUMMED column-by-column into the same statewide totals (this
    is exactly what the workbook's live "Combined" sheet shows).

Each side reduces to {category-slug -> count}; the comparison key is the category
(has_route=False), the single data field is the count. The canonical category list
(the TSN 16-ramp-type superset, incl. the TSN-only P/V "Dummy" classes) lives in
summary_layout, shared with the familiar-layout sheet appended via extra_sheet_writer.

Reconciled on the 6.19 ground truth: TSN total 15410 vs TSMIS 15215; P (Dummy
Paired)=122 and V (Dummy, Volume only)=81 are TSN-only classifications, so they
compare as 0 (TSMIS) vs the TSN count. Console-free; engine in compare_core.
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
import consolidate_ramp_summary as rs
import summary_layout
from compare_core import CompareSchema
from paths import today_str

REPORT_NAME = "Ramp Summary"
TSMIS_SHEET = rs.SUMMARY_SHEET_NAME          # "TSAR Ramps Summary" (per-route rows)
NORMALIZED_SHEET = "Ramp Summary (TSN)"      # the library's normalized 2-col workbook

_SPEC = summary_layout.RAMP_SUMMARY_SPEC
# (key, slug) for every compared category, in familiar display order.
_CATEGORIES = _SPEC.categories()

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

# slug -> the consolidated workbook's row-2 display header (authoritative, from the
# consolidator's own GROUPS), so the TSMIS sum maps columns to the same slugs.
_SLUG_TO_DISPLAY = {slug: disp for _grp, cols in rs.GROUPS for slug, disp in cols}


# --------------------------------------------------------------------------- #
# TSN side: parse the statewide PDF -> {slug: count}
# --------------------------------------------------------------------------- #
def _tsn_data_page(pdf):
    """The page carrying the category table (the statewide PDF leads with cover /
    parameter pages); fall back to the last page."""
    for pg in pdf.pages:
        txt = pg.extract_text() or ""
        if re.search(r"Total number of Ramps", txt, re.I) or \
           ("Highway Groups" in txt and "Ramp Types" in txt):
            return pg
    return pdf.pages[-1]


def parse_tsn_pdf(path):
    """The statewide TSN Ramp Summary PDF -> {slug: count} over the full schema."""
    with pdfplumber.open(path) as pdf:
        page = _tsn_data_page(pdf)
        words = page.extract_words()
        left = rs.stitch_wrapped_rows(rs.get_rows_for_column(words, left=True))
        right = rs.stitch_wrapped_rows(rs.get_rows_for_column(words, left=False))
        rec, used = {}, set()
        rec.update(rs.match_schema(left, rs.HIGHWAY_GROUPS, used))
        rec.update(rs.match_schema(left, rs.ONOFF, used))
        rec.update(rs.match_schema(left, rs.POP_GROUPS, used))
        rec.update(rs.match_schema(right, rs.RAMP_TYPES))
        m = re.search(r"Total number of Ramps:\s*([\d,]+)", page.extract_text() or "", re.I)
        rec["total_ramps"] = int(m.group(1).replace(",", "")) if m else None
    return rec


def _load_tsn(path):
    """TSN side -> {slug: count}. Reads the raw statewide PDF, or the library's
    normalized 2-column workbook (Category | Count) if that was supplied."""
    path = Path(path)
    name = path.name
    if path.suffix.lower() == ".pdf":
        return parse_tsn_pdf(path)
    # normalized library workbook: a Category|Count sheet keyed on the compare key.
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        sn = NORMALIZED_SHEET if NORMALIZED_SHEET in wb.sheetnames else wb.sheetnames[0]
        key_to_slug = {k: s for k, s in _CATEGORIES}
        rec = {}
        it = wb[sn].iter_rows(values_only=True)
        next(it, None)                                   # header
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
# TSMIS side: SUM the consolidated workbook's per-route sheet -> {slug: count}
# --------------------------------------------------------------------------- #
def _load_tsmis(path):
    """TSMIS side -> {slug: count}. Sums each category column of the consolidated
    Ramp Summary workbook's per-route 'TSAR Ramps Summary' sheet (== its Combined
    sheet's live totals). Categories the workbook lacks (e.g. an older export with
    no P/V columns) total 0, so they still compare against the TSN count."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if TSMIS_SHEET not in wb.sheetnames:
            raise ValueError(f"{name} has no '{TSMIS_SHEET}' sheet — pick the "
                             "consolidated TSMIS Ramp Summary workbook.")
        it = wb[TSMIS_SHEET].iter_rows(values_only=True)
        next(it, None)                                   # row 1: group headers
        header = next(it, None) or ()                    # row 2: display headers
        disp_to_col = {str(h).strip(): i for i, h in enumerate(header) if h is not None}
        if "Route" not in disp_to_col:
            raise ValueError(f"{name} isn't a consolidated Ramp Summary workbook "
                             "(no 'Route' column) — consolidate the per-route "
                             "exports first.")
        sums = {slug: 0 for slug in _SLUG_TO_DISPLAY}
        for row in it:
            if not row or all(c is None for c in row):
                continue
            for slug, disp in _SLUG_TO_DISPLAY.items():
                ci = disp_to_col.get(disp)
                if ci is not None and ci < len(row) and isinstance(row[ci], (int, float)):
                    sums[slug] += int(row[ci])
        return sums
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# rows over the canonical category list
# --------------------------------------------------------------------------- #
def _rows(counts, with_footnotes=False):
    """[[category_key, count], ...] over every canonical category, in display
    order. A category absent from `counts` is emitted as 0 so both sides align on
    the full set (rather than becoming a one-sided row). `with_footnotes` appends
    the TSMIS-only metrics (e.g. Ramp Points w/out linework) — emitted on the TSMIS
    side ONLY, so they land in 'Only in TSMIS' and on the familiar sheet's footer."""
    out = [[key, int(counts.get(slug, 0) or 0)] for key, slug in _CATEGORIES]
    if with_footnotes:
        for f in _SPEC.footnotes:
            v = counts.get(f.slug)
            if v is not None:
                out.append([f.key, int(v)])
    return out


# --------------------------------------------------------------------------- #
# adapter surface (registry "files" kind)
# --------------------------------------------------------------------------- #
def suggest_name(tsmis_path):
    return f"TSMIS_vs_TSN_RampSummary_Comparison {today_str()}.xlsx"


def _load_pair(tsmis_path, tsn_path):
    """(rows_t, rows_n, warnings) for the shared driver. A statewide TSN page should
    fill every category; flag any the parser missed so an incomplete parse can't
    masquerade as a clean comparison. The TSMIS-only footnote metrics ride the TSMIS side."""
    tsmis_counts = _load_tsmis(tsmis_path)
    tsn_counts = _load_tsn(tsn_path)
    warnings = []
    missing = [key for key, slug in _CATEGORIES if tsn_counts.get(slug) is None]
    if missing:
        warnings.append(f"TSN parse did not find {len(missing)} categor"
                        f"{'y' if len(missing) == 1 else 'ies'}: "
                        + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
    return _rows(tsmis_counts, with_footnotes=True), _rows(tsn_counts), warnings


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas"):
    """Build the Ramp Summary TSMIS-vs-TSN AGGREGATE comparison workbook(s).
    `tsmis_path` is the consolidated TSMIS Ramp Summary workbook; `tsn_path` the
    TSN statewide PDF (or the library's normalized workbook)."""
    return ctc.run_files_compare(
        _SCHEMA, tsmis_path, tsn_path, out_path,
        banner="Ramp Summary Comparison — TSMIS vs TSN (statewide category counts)",
        has_route=False, loader=_load_pair, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (pdfplumber, openpyxl).",
        events=events, confirm_overwrite=confirm_overwrite, mode=mode)
