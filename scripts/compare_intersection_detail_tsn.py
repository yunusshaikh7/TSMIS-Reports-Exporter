"""Build the TSMIS-vs-TSN Intersection Detail discrepancy workbook (FLAT, route+PM).

The Ramp Detail FLAT recipe applied to Intersection Detail: both sides are XLSX in
different shapes, each with its own loader projecting onto ONE shared PM-keyed
header. Reconciled by hand on route 1 (1,265 PMs aligned):

  * TSMIS side — the CONSOLIDATED Intersection Detail workbook (leading Route
    column + the 36 source columns). Its header is column-shifted (the "INT Type"
    label sits over the eff-date value, etc.), so columns are read BY POSITION.
  * TSN side — the statewide raw `Sheet 1` (36 named DB columns); route from
    `LOCATION` ("12 ORA 001" -> "001").

Both store attribute values in (eff_date, type) order (the planning-phase
"pair-order reversal" was a misread of the shifted TSMIS labels).

Every field present in both systems is COMPARED and COUNTED — a mechanical diff; the
reader adds commentary, the tool never hides a column. Columns are ordered to mirror the
source report and every column is compared BY REPORT POSITION — each report column to the
same column in the other report (user decision 2026-06-24); nothing is suppressed. The
eight date columns split two ways: Date of Record and the mainline / cross-street eff-dates
(first AND second) are a STRUCTURAL refresh-vs-original difference — TSMIS stores a recent
refresh date or a "2024" bulk stamp where TSN keeps the original/recent geometry date — so
they differ on nearly every row; the INT / Control / Lighting eff-dates are geometry-vs-
geometry and sit a systematic ~1 day apart. Main Line Length and the intersecting-route
block are compared too. Some columns differ on nearly every row by their nature (see below);
they are still flagged, and the Notes sheet COMMENTS on why rather than suppressing them. A
second "Report View" sheet replicates the printed two-line record and shows every difference
in red (date offsets included, but kept out of its per-record "Major" count). Normalizations
make some raw-different
values compare equal; each is documented in the Notes sheet so a match is read as "equal
after the stated normalization", not raw equality:
  1. **Boolean encoding** — mastarm / right-channelization / lighting are Y/N on
     TSN but 1/0 on TSMIS. NORMALIZED here as Y≡1 / N≡0 so only genuine changes flag
     (a TSMIS cell shown as "Y" was stored "1"); the Notes sheet states this.
  2. **Control-type crosswalk** — TSN records signalized under the legacy signal
     sub-types J/K/L/M/N/P, which TSNR/TSMIS collapses into the single category TSMIS
     stores as the code "S". Per the TSNR/MIRE reference, both sides' signalized codes
     are normalized to that one code "S" (the Signalized category) so the sub-type
     split stops flagging; the Notes sheet documents it. (Geometry/INT Type needs no
     crosswalk — both systems share the F/M/S/T/Y/Z/R codes.)
  3. **Date of Record** is a TSMIS refresh date (not the historical record date), so
     the whole column differs from TSN — it is compared and counted like everything
     else, and the Notes sheet comments on why the column differs wholesale.
  4. **Cross-street (CS*) attributes** — TSMIS leaves them blank for ~37% of
     intersections while TSN defaults them, so that column shows many blank-vs-value
     differences; compared and counted, with the completeness gap noted.

Console-free; engine in compare_core.
"""
import dataclasses
import re
from datetime import date
from pathlib import Path

try:
    from openpyxl import load_workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.cell_range import CellRange
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_tsn_common as ctc
from compare_core import (CompareSchema, normalize_value, keys_for,
                          pair_occurrences_by_similarity, union_keys)
from paths import today_str

REPORT_NAME = "Intersection Detail"
TSMIS_SHEET = "Intersection Detail"      # consolidated sheet (Route prepended)
TSN_SHEET = "Sheet 1"                     # raw statewide DB dump
NORMALIZED_SHEET = "Intersection Detail (TSN)"

KEY = "PM"
# Column order mirrors the source report (each effective-date next to its type, the
# mainline block, then the cross-street block, then the intersecting route). Every
# field present in both systems is compared and counted — nothing is suppressed
# (CONTEXT_FIELDS is empty, below; the position-aligned policy compares every column).
SHARED_HEADER = [
    "PR", "Route Suffix", "PM", "Date of Record", "HG", "City Code", "R/U",
    "INT Type Eff-Date", "INT Type",
    "Control Type Eff-Date", "Control Type",
    "Lighting Eff-Date", "Lighting",
    "ML Eff-Date", "ML Mastarm", "ML Left Chan", "ML Right Chan",
    "ML Traffic Flow", "ML Num Lanes", "ML 2nd Eff-Date",
    "Description", "Main Line Length",
    "CS Eff-Date", "CS Mastarm", "CS Left Chan", "CS Right Chan",
    "CS Traffic Flow", "CS Num Lanes", "Int St Eff-Date",
    "Intrte Route", "Intrte PM Prefix", "Intrte Postmile", "Intrte PM Suffix",
]
KEY_FIELD = SHARED_HEADER.index(KEY)      # 2 (after PR + the derived Route Suffix column)
# Position-aligned comparison (user decision 2026-06-24): every report column is compared
# to the same column in the other report — nothing is suppressed. The mainline/cross
# eff-date columns differ structurally (TSMIS stores a refresh date where TSN stores the
# original) and so flag on nearly every row; the Notes sheet documents it. INT/Control/
# Lighting are geometry-vs-geometry (the systematic ~1-day offset).
CONTEXT_FIELDS = ()
DATE_FIELDS = ("Date of Record", "INT Type Eff-Date", "Control Type Eff-Date",
               "Lighting Eff-Date", "ML Eff-Date", "ML 2nd Eff-Date", "CS Eff-Date",
               "Int St Eff-Date")
# Y/N (TSN) vs 1/0 (TSMIS) booleans — normalized to Y/N so only real changes flag.
BOOLEAN_FIELDS = ("Lighting", "ML Mastarm", "ML Right Chan", "CS Mastarm", "CS Right Chan")
# Numeric fields where the two systems differ only in zero-padding — Main Line Length
# (TSMIS '58' vs TSN '058'), the intersecting-route number, and its postmile (TSMIS
# '9.560' vs TSN '9.56'). Normalized to a canonical number so the padding doesn't flag.
NUMERIC_FIELDS = ("Main Line Length", "Intrte Route", "Intrte Postmile")
# Control-type crosswalk (per the TSNR/MIRE reference "TSNR - Intersection Control
# and Geometry Type"): TSN spreads the signalized category across the legacy signal
# sub-types J–P (J/K/L/M/N/P), which TSNR/TSMIS collapses into the single code TSMIS
# stores as "S". Both sides' signalized codes normalize to that one code "S" (the
# Signalized category) — so the compared Control Type cell shows "S" wherever the
# crosswalk applied, and the sub-type split stops flagging as a difference. The Notes
# sheet documents the crosswalk. Geometry (INT Type) needs NO crosswalk — both systems
# share F/M/S/T/Y/Z/R.
_SIGNALIZED_CODES = {"J", "K", "L", "M", "N", "P", "S"}
_SIGNALIZED_LABEL = "S"          # TSN J–P + TSMIS S all fold to TSMIS's code "S"

# TSN raw column name for each shared field (key + fields).
_TSN_COL = {
    "PR": "PP", "PM": "POST_MILE", "HG": "HG", "City Code": "CITY_CODE", "R/U": "RU",
    "INT Type": "TY_INT", "Control Type": "TY_CT", "Lighting": "LT_TY",
    "ML Mastarm": "MAIN_SM", "ML Left Chan": "MAIN_LC", "ML Right Chan": "MAIN_RC",
    "ML Traffic Flow": "MAIN_TF", "ML Num Lanes": "MAIN_NL", "Description": "DESCRIPTION",
    "CS Mastarm": "CS_SM", "CS Left Chan": "CS_LC", "CS Right Chan": "CS_RC",
    "CS Traffic Flow": "CS_TF", "CS Num Lanes": "CS_NL", "Date of Record": "DATE_REC",
    # added columns — mapped BY REPORT POSITION (each report column compared to the same
    # column in the other report; user decision 2026-06-24). So the FIRST mainline/cross
    # eff-date (next to the attrs) maps to TSN's first date — the historical/geometry
    # EFF_DATE_ML / CROSS_BEGIN_DATE — and the SECOND eff-date maps to TSN's recent
    # MAIN_EFF_DATE / EFF_DATE. TSMIS stores a refresh date in the first slot, so these
    # read as structural refresh-vs-original differences (like Date of Record), not a
    # 1-day offset. INT/Control/Lighting are geometry-vs-geometry (the 1-day offset).
    "INT Type Eff-Date": "EFF_DATE_INT", "Control Type Eff-Date": "EFF_DATE_CT",
    "Lighting Eff-Date": "EFF_DATE_LT", "ML Eff-Date": "EFF_DATE_ML",
    "CS Eff-Date": "CROSS_BEGIN_DATE", "Main Line Length": "MAIN_OVERRIDE",
    "ML 2nd Eff-Date": "MAIN_EFF_DATE", "Int St Eff-Date": "EFF_DATE",
    "Intrte Route": "CROSS_ROUTE_NAME", "Intrte PM Prefix": "CROSS_PM_PREFIX",
    "Intrte Postmile": "CROSS_POSTMILE", "Intrte PM Suffix": "CROSS_PM_SUFFIX",
}
# Consolidated-TSMIS VALUE position for each shared field (Route at 0; header is
# column-shifted so position — not label — is authoritative; verified on route 1).
_TSMIS_POS = {
    "PR": 1, "PM": 2, "HG": 6, "City Code": 7, "R/U": 8, "INT Type": 10,
    "Control Type": 12, "Lighting": 14, "ML Mastarm": 16, "ML Left Chan": 17,
    "ML Right Chan": 18, "ML Traffic Flow": 19, "ML Num Lanes": 20, "Description": 22,
    "CS Mastarm": 25, "CS Left Chan": 26, "CS Right Chan": 27, "CS Traffic Flow": 28,
    "CS Num Lanes": 29, "Date of Record": 5,
    # added columns — the consolidated VALUE position (header labels are shifted; the
    # eff-date sits one column LEFT of its type value). Verified across 16k paired rows.
    # NB the intersecting-route PM suffix is at pos 35 (the 'Xing Rte' label), not 31.
    "INT Type Eff-Date": 9, "Control Type Eff-Date": 11, "Lighting Eff-Date": 13,
    "ML Eff-Date": 15, "ML 2nd Eff-Date": 21, "Main Line Length": 23, "CS Eff-Date": 24,
    "Int St Eff-Date": 30, "Intrte Route": 32, "Intrte PM Prefix": 33,
    "Intrte Postmile": 34, "Intrte PM Suffix": 35,
}
_TSMIS_ROUTE_POS = 4                       # consolidated "Location" column ("12 ORA 001")


# --------------------------------------------------------------------------- #
# normalization
# --------------------------------------------------------------------------- #
def _split_route(tok):
    """Split a LOCATION token into (base_route, route_suffix):
    '12 ORA 210U' -> ('210', 'U'); '12 ORA. 210' -> ('210', '').

    A California route name can carry an alpha route SUFFIX (e.g. S/U — the printed
    report's "S" column) that TSN keeps but TSMIS often omits. Keying on the BASE
    route lets the same intersection still pair across that label difference, while
    the suffix is surfaced as the compared 'Route Suffix' column — so a suffix-only
    difference is flagged there (TSN 'U' vs TSMIS blank) rather than the rows being
    dropped to one-sided OR silently merged."""
    t = str(tok or "").strip().upper().replace("-", " ")
    parts = t.split()
    last = parts[-1] if parts else ""
    m = re.fullmatch(r"(\d+)([A-Z]?)", last)
    return (f"{int(m.group(1)):03d}", m.group(2)) if m else (last, "")


def _norm_route(tok):
    """The base route number (route suffix stripped) — the row key. See _split_route."""
    return _split_route(tok)[0]


# PM + date canon shared with Ramp Detail, homed in compare_tsn_common (P5b/S04);
# iso_date also handles this report's 2-digit TSN year. Names kept so the loaders, the
# Report View, and the golden canary still resolve idt._norm_pm / idt._iso_date.
_norm_pm = ctc.norm_pm
_iso_date = ctc.iso_date


_BOOL = {"Y": "Y", "N": "N", "1": "Y", "0": "N"}


def _norm_bool(v):
    return _BOOL.get(str(v or "").strip().upper(), str(v or "").strip())


def _norm_num(v):
    """Canonicalize a zero-padded number: '058'->'58', '9.560'->'9.56', '0.000'->'0'.
    Non-numeric values are returned unchanged (so e.g. a route name with letters is safe)."""
    s = str(v or "").strip()
    if not s or not re.fullmatch(r"-?\d+(\.\d+)?", s):
        return s
    neg, s = s.startswith("-"), s.lstrip("-")
    if "." in s:
        ip, fp = s.split("."); ip = ip.lstrip("0") or "0"; fp = fp.rstrip("0")
        s = ip + ("." + fp if fp else "")
    else:
        s = s.lstrip("0") or "0"
    return ("-" + s) if neg else s


def _norm_control_type(v):
    """Apply the TSN→TSNR control-type crosswalk: the legacy signal sub-types J–P
    (TSN) and TSMIS's combined "S" all fold into the single code "S" (the Signalized
    category TSMIS stores), so the sub-type split no longer reads as a difference. The
    compared cell therefore shows "S" wherever the crosswalk applied. Every other code
    is left as-is (both systems share A/B/C/D/E/F/G/H/I/R/Z)."""
    s = str(v or "").strip().upper()
    return _SIGNALIZED_LABEL if s in _SIGNALIZED_CODES else _v(v)


def _v(x):
    return normalize_value(x)


def _project(field, raw):
    """Normalize one raw cell for `field` into the shared, comparable form."""
    if field in BOOLEAN_FIELDS:
        return _norm_bool(raw)
    if field == "Control Type":
        return _norm_control_type(raw)
    if field == "PM":
        return _norm_pm(raw)
    if field in DATE_FIELDS:
        return _iso_date(raw)
    if field in NUMERIC_FIELDS:
        return _norm_num(raw)
    return _v(raw)


# --------------------------------------------------------------------------- #
# loaders -> consolidated-shape rows ([route, *SHARED_HEADER])
# --------------------------------------------------------------------------- #
def _tsn_row(r, h):
    def g(name):
        i = h.get(name)
        return r[i] if i is not None and i < len(r) else None
    base, route_suffix = _split_route(g("LOCATION"))
    return [base] + [route_suffix if f == "Route Suffix" else _project(f, g(_TSN_COL[f]))
                     for f in SHARED_HEADER]


def tsn_rows_from_raw(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        sn = TSN_SHEET if TSN_SHEET in wb.sheetnames else wb.sheetnames[0]
        it = wb[sn].iter_rows(values_only=True)
        header = list(next(it, []) or [])
        h = {str(n).strip(): i for i, n in enumerate(header) if n is not None}
        if "LOCATION" not in h or "POST_MILE" not in h:
            raise ValueError("the TSN Intersection Detail workbook is missing "
                             "LOCATION/POST_MILE — pick the raw 'TSAR - INTERSECTION DETAIL' export.")
        return [_tsn_row(list(r), h) for r in it
                if r and any(c is not None and str(c).strip() != "" for c in r)]
    finally:
        wb.close()


def _normalized_row(r):
    """Re-project one row from the normalized TSN-library sheet onto the shared
    shape, RE-APPLYING the field normalizations (control-type crosswalk, booleans,
    PM, date). The projections are idempotent on already-normalized values, so this
    is a no-op for a freshly-built library BUT repairs a STALE one — a library
    workbook built before a normalization change (e.g. before the J–P→`S` signal
    crosswalk) would otherwise feed raw codes straight through `_v` and flag a phantom
    'S ≠ P' (a fresh library shows the crosswalked code 'S', a stale one the raw 'P').
    Normalizing at COMPARE time means a normalization change takes effect immediately,
    without rebuilding the library."""
    vals = list(r)[:len(SHARED_HEADER) + 1]
    vals += [None] * (len(SHARED_HEADER) + 1 - len(vals))
    return [_v(vals[0])] + [_project(f, vals[i + 1]) for i, f in enumerate(SHARED_HEADER)]


def _load_tsn(path):
    path = Path(path)
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {path.name}: {type(e).__name__}: {e}")
    try:
        if NORMALIZED_SHEET in wb.sheetnames:
            it = wb[NORMALIZED_SHEET].iter_rows(values_only=True)
            next(it, None)
            rows = [_normalized_row(r)
                    for r in it if r and any(c not in (None, "") for c in r)]
            return rows, True
    finally:
        wb.close()
    return tsn_rows_from_raw(path), True


def _tsmis_row(r):
    def at(i):
        return r[i] if i < len(r) else None
    base, route_suffix = _split_route(at(_TSMIS_ROUTE_POS))
    return [base] + [route_suffix if f == "Route Suffix" else _project(f, at(_TSMIS_POS[f]))
                     for f in SHARED_HEADER]


def _load_tsmis(path):
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if TSMIS_SHEET not in wb.sheetnames:
            raise ValueError(f"{name} has no '{TSMIS_SHEET}' sheet — pick the "
                             "consolidated TSMIS Intersection Detail workbook.")
        it = wb[TSMIS_SHEET].iter_rows(values_only=True)
        header = [str(c).strip() if c is not None else "" for c in (next(it, []) or [])]
        if not header or header[0] != "Route":
            raise ValueError(f"{name} isn't a CONSOLIDATED Intersection Detail workbook "
                             "(expected a leading 'Route' column) — consolidate first.")
        return [_tsmis_row(list(r)) for r in it
                if r and any(c is not None and str(c).strip() != "" for c in r)], True
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# Notes sheet — documents every normalization applied (so a match is read as
# "equal after the stated normalization", not raw equality) and comments on the
# columns that differ wholesale. Nothing is suppressed: all shared fields are
# compared and counted.
# --------------------------------------------------------------------------- #
def _write_notes_sheet(wb):
    ws = wb.create_sheet("Notes")
    ws.sheet_properties.tabColor = "ED7D31"
    write_only = getattr(wb, "write_only", False)
    title = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    head = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill = PatternFill("solid", start_color="1F3864")
    sec_fill = PatternFill("solid", start_color="0070C0")
    body = Font(name="Arial", size=10)
    wrap = Alignment(vertical="top", wrap_text=True)

    def cell(value, font=body, f=None, align=None):
        if not write_only:
            return value
        c = WriteOnlyCell(ws, value=value)
        c.font = font
        if f:
            c.fill = f
        if align:
            c.alignment = align
        return c

    def section(text):
        ws.append([cell(text, head, f=sec_fill)])

    def note(text):
        ws.append([cell(text, body, align=wrap)])

    ws.column_dimensions["A"].width = 110
    ws.append([cell("Intersection Detail — TSMIS vs TSN: comparison notes", title, fill)])
    note("This is a MECHANICAL field-by-field diff. EVERY column present in both systems "
         "is compared and counted — nothing is hidden. Some columns differ on nearly every "
         "row by their nature; they are still flagged, and the reasons are noted below "
         "(commentary belongs to the reader, not to suppressing a column).")

    section("NORMALIZATIONS APPLIED  (these can make raw-different values compare EQUAL — "
            "a match means 'equal after the normalization named here', not that the source "
            "cells were byte-identical)")
    note("• Control Type — CROSSWALK (per the TSNR/MIRE reference 'TSNR - Intersection "
         "Control and Geometry Type'): TSN records signalized intersections under the legacy "
         "signal sub-types J/K/L/M/N/P (pretimed / semi- / full-actuated, 2- vs multi-phase); "
         "TSNR/TSMIS collapses them into ONE category stored as the code 'S'. Both sides' "
         "signalized codes are normalized to that single code 'S' (the Signalized category). "
         "HOW TO SEE IT: wherever the Control Type cell reads 'S' (a single code that may be "
         "a folded TSN J–P), the crosswalk was applied — a TSN J–P matched a TSMIS S. Every other control code "
         "(A/B/C/D/E/F/G/H/I/R/Z) is shared and compared unchanged. INT Type needs no "
         "crosswalk — both systems share the F/M/S/T/Y/Z/R codes.")
    note("• Boolean encoding — Lighting, ML Mastarm, ML Right Chan, CS Mastarm, CS Right "
         "Chan are stored Y/N on TSN but 1/0 on TSMIS. Normalized as Y≡1 / N≡0, so only a "
         "genuine change flags (not the encoding). HOW TO SEE IT: a cell shown as 'Y' on the "
         "TSMIS side was stored '1' (and 'N' was '0').")
    note("• Postmile (PM) — leading zeros and spaces are stripped so the same postmile pairs "
         "across formatting (TSN ' 004.901' ≡ TSMIS '4.901'). PM is the row key.")
    note("• Route suffix — a California route name can carry an alpha suffix (e.g. S/U — the "
         "printed report's 'S' column) that TSN keeps but TSMIS often omits (TSN '210U' vs TSMIS "
         "'210'). Rows are matched on the BASE route number so the same intersection still pairs; "
         "the suffix is compared in the 'Route Suffix' column (TSN 'U' vs TSMIS blank flags there) "
         "rather than dropping the row.")

    section("COLUMNS THAT DIFFER WHOLESALE  (compared and counted like any other — the "
            "difference is structural, explained here, NOT a per-intersection data error)")
    note("• Date of Record — TSMIS stores a data-REFRESH date (typically 2019–2023) while TSN "
         "stores the historical RECORD date (often 1964/1970/1977). The two therefore differ on "
         "almost every matched row. The column is compared and counted; treat the count as 'the "
         "field means different things in the two systems', not as thousands of corrections.")
    note("• Cross-street attributes (CS Mastarm / Left Chan / Right Chan / Traffic Flow / Num "
         "Lanes) — TSMIS leaves cross-street detail blank for ~37% of intersections while TSN "
         "defaults it, so this group shows many blank-vs-value differences. They are compared "
         "and counted; most differences here are a TSMIS completeness gap rather than a "
         "value conflict.")
    note("• Effective-date columns — all COMPARED BY REPORT POSITION (each report column to the "
         "same column in the other report, user decision 2026-06-24). They split two ways. "
         "(a) STRUCTURAL refresh-vs-original — Date of Record and the mainline / cross-street "
         "eff-dates (first AND second): TSMIS stores a recent refresh date or a uniform '2024' "
         "bulk stamp where TSN keeps the original/recent geometry date (e.g. '2021-12-31' vs "
         "'1964-01-01', or '2024' vs '2022-01-01'), so they differ on nearly every matched row. "
         "(b) The INT Type / Control / Lighting eff-dates are geometry-vs-geometry and sit a "
         "SYSTEMATIC ~1 day apart ('1973-10-18' vs '1973-10-19') — an encoding convention. Read "
         "the counts as the convention/structure, not as per-intersection edits.")
    note("• Intersecting-route block (Intrte Route / PM Prefix / Postmile / PM Suffix) + Main "
         "Line Length — also compared. The intersecting route is mostly blank on both (only ~10 "
         "intersections cross another state route); differences are genuine where present.")
    note("• Nothing is greyed-out or shown-but-not-counted — under position alignment every shared "
         "column is compared and counted. (TSMIS's blank route-suffix 'S' / second 'Xing' route stubs "
         "are omitted; TSN's ADT columns MAIN_ADT / CROSS_ADT have no TSMIS counterpart and aren't "
         "compared — they appear, for reference, only on the Report View.)")

    section("REPORT VIEW  (a second sheet — the printed two-line record, for visual inspection)")
    note("• The 'Report View' tab replicates the printed Intersection Detail record (two physical "
         "lines per intersection) and renders EVERY difference in red — the structural date offsets "
         "included — so the page can be eyeballed straight against the source PDF. Per record it "
         "shows two counts: 'Major' = genuine NON-date attribute conflicts (the date offsets are "
         "excluded so they don't drown out the real conflicts); 'Diffs' = every difference. TSN-only "
         "geometry/ADT columns appear there in blue for reference.")
    note("Rows are keyed on Route + Postmile (PM).")
    return ws


_SCHEMA = CompareSchema(
    report_name=REPORT_NAME,
    header=SHARED_HEADER,
    side_a="TSMIS",
    side_b="TSN",
    id_noun="intersection",
    id_noun_plural="intersections",
    pair_noun="postmile",
    sides_noun="systems",
    date_fields=DATE_FIELDS,
    data_widths={"Description": 26, "Date of Record": 11},
    cmp_widths={"Description": 30, "Date of Record": 12},
    one_sided_note_extra=" (intersections one system lists at a postmile the other doesn't)",
    key_field=KEY_FIELD,
    context_fields=CONTEXT_FIELDS,  # () — position-aligned, nothing suppressed or greyed
    legend_writer=_write_notes_sheet,
)


# --------------------------------------------------------------------------- #
# Report View — a two-line replica of the printed report, comparison-coloured
# --------------------------------------------------------------------------- #
# The printed Intersection Detail record is TWO physical lines; this sheet mirrors
# that (row 1 = MAINLINE side, row 2 = CROSS-STREET side) so the comparison reads
# like the report. Mainline and intersecting blocks are PARALLEL (same attributes)
# so they share the middle columns; line-1-only fields sit on the mainline row,
# line-2-only on the cross row. Colour: RED = any difference — a genuine ("Major")
# discrepancy AND a structural date offset (Date of Record / the position-aligned
# eff-dates) both read red (user request 2026-06-24: all date discrepancies are red);
# BLUE = TSN-only column; AMBER = TSMIS-only column. Two per-record counts head each
# record: Major = genuine NON-date conflicts (so the reader can filter to the real
# attribute differences past the ubiquitous date offsets), Diffs = every difference
# (the dates included). Identity is repeated on both physical rows so a filter keeps
# the 2-row records together — the streaming workbook can't vertically merge cells.
_RV_ONE = {"LOC": "LOCATION", "XOVR": "X_CROSS_OVERRIDE",
           "ADT": "MAIN_ADT", "CADT": "CROSS_ADT"}
_RV_DATEONE = ()         # no date-valued TSN-only columns (geometry dates are compared)
# Structural date columns (refresh-vs-original or ADT-year) -> always yellow. The
# geometry-vs-geometry INT/Control/Lighting eff-dates -> yellow only within the 1-day offset.
_RV_SOFT_ALWAYS = ("Date of Record", "ML Eff-Date", "CS Eff-Date",
                   "ML 2nd Eff-Date", "Int St Eff-Date")
_RV_EFFDATES = ("INT Type Eff-Date", "Control Type Eff-Date", "Lighting Eff-Date")
_RV_AUX = ("Major", "Diffs", "Route")       # frozen-left aux columns
# Report grid — column SHARING matches the printed report: DESCRIPTION spans under
# LOCATION, LINE LGTH under R/U, the INTERSECTING block under INT/CONTROL/LIGHTING,
# INT ST + INTERSECTING ROUTE + XING under MAINLINE. Each entry is
# (g1, l1, s1, g2, l2, s2): line-1 group/label/spec stacked over line-2's. spec=(kind,ref).
_RV_GRID = [
    ("", "P", ("cmp", "PR"), "", "", ("blank", None)),
    ("", "POST MILE", ("pm", None), "", "", ("blank", None)),
    ("", "S", ("blank", None), "", "", ("blank", None)),
    ("", "LOCATION", ("loc", None), "", "DESCRIPTION", ("cmp", "Description")),
    ("", "DATE OF REC", ("cmp", "Date of Record"), "", "", ("blank", None)),
    ("", "H/G", ("cmp", "HG"), "", "", ("blank", None)),
    ("", "CITY", ("cmp", "City Code"), "", "", ("blank", None)),
    ("", "R/U", ("cmp", "R/U"), "*MAIN*", "LINE LGTH", ("cmp", "Main Line Length")),
    ("* INT *", "EFF-DATE", ("cmp", "INT Type Eff-Date"), "* INTERSECTING *", "EFF-DATE", ("cmp", "CS Eff-Date")),
    ("* INT *", "T/Y", ("cmp", "INT Type"), "* INTERSECTING *", "S/M", ("cmp", "CS Mastarm")),
    ("* CONTROL *", "EFF-DATE", ("cmp", "Control Type Eff-Date"), "* INTERSECTING *", "L/C", ("cmp", "CS Left Chan")),
    ("* CONTROL *", "T/Y", ("cmp", "Control Type"), "* INTERSECTING *", "R/C", ("cmp", "CS Right Chan")),
    ("* LIGHTING *", "EFF-DATE", ("cmp", "Lighting Eff-Date"), "* INTERSECTING *", "T/F", ("cmp", "CS Traffic Flow")),
    ("* LIGHTING *", "T/Y", ("cmp", "Lighting"), "* INTERSECTING *", "N/L", ("cmp", "CS Num Lanes")),
    ("* MAINLINE *", "EFF-DATE", ("cmp", "ML Eff-Date"), "* INT ST *", "EFF-DATE", ("cmp", "Int St Eff-Date")),
    ("* MAINLINE *", "S/M", ("cmp", "ML Mastarm"), "*INT ROUTE*", "RTE NO", ("cmp", "Intrte Route")),
    ("* MAINLINE *", "L/C", ("cmp", "ML Left Chan"), "*INT ROUTE*", "P", ("cmp", "Intrte PM Prefix")),
    ("* MAINLINE *", "R/C", ("cmp", "ML Right Chan"), "*INT ROUTE*", "POST MI", ("cmp", "Intrte Postmile")),
    ("* MAINLINE *", "T/F", ("cmp", "ML Traffic Flow"), "*XING*", "RTE", ("cmp", "Intrte PM Suffix")),
    ("* MAINLINE *", "N/L", ("cmp", "ML Num Lanes"), "*XING*", "S", ("blank", None)),
    ("* MAINLINE *", "EFF-DATE", ("cmp", "ML 2nd Eff-Date"), "", "", ("blank", None)),
    ("TSN only", "X-Ovr", ("tn", "XOVR"), "TSN only", "", ("blank", None)),
    ("TSN only", "ML ADT", ("tn", "ADT"), "TSN only", "CS ADT", ("tn", "CADT")),
]
# (normal, ALT) fill hex pairs — whole-record alternation across every cell type. A record's
# neutral cells are uniformly WHITE (normal) or GREY (alt) so each record reads as one solid
# zebra band: white is applied to EVERY neutral cell of the record (blanks included), never
# mixed with grey within a record (the patchy-white-gap bug). 'soft' (date differences)
# shares the hard RED palette — every date discrepancy renders red (user request 2026-06-24)
# — while staying out of the Major count (see _rv_classify).
_RV_FILLS = {"hard": ("F8D4D4", "E8B6B6"), "soft": ("F8D4D4", "E8B6B6"),
             "tn": ("DCE5F3", "B7CCE7"), "tm": ("F8E4CF", "E3C9A2"),
             "id": ("FFFFFF", "CFD6DE"), "count": ("FFFFFF", "CFD6DE"), "eq": ("FFFFFF", "CFD6DE")}
_RV_FONTCOL = {"hard": "9C0006", "soft": "9C0006", "tn": "163A63", "tm": "7A431A"}
# Hover-comments on the normalized headers (so a match reads as "equal after this rule").
_RV_COMMENTS = {
    "Control Type": "NORMALIZED: TSN's signal sub-types J-P and TSMIS's 'S' all fold to 'S' "
                    "(signalized) per the TSNR crosswalk, so the sub-type split doesn't flag.",
    "Lighting": "NORMALIZED: boolean 1/0 (TSMIS) compared as 1=Y, 0=N (TSN).",
    "ML Mastarm": "NORMALIZED: boolean 1/0 (TSMIS) = Y/N (TSN).",
    "ML Right Chan": "NORMALIZED: boolean 1/0 (TSMIS) = Y/N (TSN).",
    "CS Mastarm": "NORMALIZED: boolean 1/0 (TSMIS) = Y/N (TSN).",
    "CS Right Chan": "NORMALIZED: boolean 1/0 (TSMIS) = Y/N (TSN).",
    "Main Line Length": "NORMALIZED: zero-padding ignored (TSMIS '58' = TSN '058').",
    "Intrte Postmile": "NORMALIZED: trailing zeros ignored (TSMIS '9.560' = TSN '9.56').",
    "Date of Record": "TSMIS stores a data-REFRESH date; TSN the historical RECORD date - a "
                      "structural difference. Shown RED, but kept OUT of the Major count "
                      "(it isn't a per-row data error).",
    "ML Eff-Date": "Compared BY REPORT POSITION: TSMIS shows its refresh date, TSN the "
                   "original/geometry date - structural. Shown RED, not counted as Major.",
    "CS Eff-Date": "Compared BY REPORT POSITION: TSMIS shows its refresh date, TSN the "
                   "original/geometry date - structural. Shown RED, not counted as Major.",
}


def _rv_pdate(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", str(s or ""))
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except (ValueError, AttributeError):
        return None


def _rv_classify(field, tm, tn):
    """Classify a DIFFERING cell. 'soft' = a structural DATE difference (Date of Record,
    a position-aligned eff-date, or an INT/Control/Lighting geometry date within the
    systematic 1-day offset): it renders RED like a genuine conflict but is kept OUT of
    the per-record Major count. 'hard' = a genuine 'Major' discrepancy. Everything that
    isn't one of those date cases is hard. (Both soft and hard count toward Diffs.)"""
    if field in _RV_SOFT_ALWAYS:
        return "soft"
    if field in _RV_EFFDATES:
        da, db = _rv_pdate(tm), _rv_pdate(tn)
        if da and db and abs((da - db).days) <= 1:
            return "soft"
    return "hard"


def _tsn_onesided(path):
    """Raw TSN one-sided columns (geometry eff-dates, ADT counts, X-cross override) +
    Location, aligned to the rows `tsn_rows_from_raw` yields. Returns None for a
    normalized-library workbook (those columns aren't stored there) — the replica then
    shows the TSN-only cells blank."""
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return None
    try:
        if NORMALIZED_SHEET in wb.sheetnames:
            return None
        sn = TSN_SHEET if TSN_SHEET in wb.sheetnames else wb.sheetnames[0]
        it = wb[sn].iter_rows(values_only=True)
        hdr = next(it, None) or []
        h = {str(n).strip(): i for i, n in enumerate(hdr) if n is not None}
        out = []
        for r in it:
            if not (r and any(c is not None and str(c).strip() != "" for c in r)):
                continue
            out.append({k: ("" if h.get(col) is None or h[col] >= len(r) or r[h[col]] is None
                            else str(r[h[col]]).strip())
                        for k, col in _RV_ONE.items()})
        return out
    finally:
        wb.close()


def _tsmis_locations(path):
    """Consolidated TSMIS 'Location' (pos 4), aligned to the rows `_load_tsmis` yields."""
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return []
    try:
        if TSMIS_SHEET not in wb.sheetnames:
            return []
        it = wb[TSMIS_SHEET].iter_rows(values_only=True)
        next(it, None)
        out = []
        for r in it:
            if not (r and any(c is not None and str(c).strip() != "" for c in r)):
                continue
            out.append("" if len(r) <= 4 or r[4] is None else str(r[4]).strip())
        return out
    finally:
        wb.close()


def _write_report_view(wb, ctx, tsn_one, tm_loc):
    """Append the two-line 'Report View' — a faithful replica of the printed
    Intersection Detail record (two physical lines per intersection) — to the
    streaming comparison workbook. Column SHARING mirrors the report: DESCRIPTION
    spans under LOCATION, LINE LGTH under R/U, the INTERSECTING block under
    INT/CONTROL/LIGHTING, INT ST + INTERSECTING ROUTE + XING under MAINLINE. The
    4-row header is the report's two stacked header blocks (line-1 group/label over
    line-2 group/label). Identity (Major/Diffs/Route + P/PostMile/S/Location) repeats
    on both physical rows so a filter keeps the 2-row records intact — the streaming
    workbook can't vertically merge the data cells (header cells it can, below)."""
    sc = ctx["sc"]
    rows_a, rows_b = ctx["rows_a"], ctx["rows_b"]
    ka = keys_for(rows_a, True, key_field=sc.key_field)
    kb = keys_for(rows_b, True, key_field=sc.key_field)
    ka, kb = pair_occurrences_by_similarity(sc, rows_a, rows_b, ka, kb, True)
    union = union_keys(ka, kb)
    amap = {k: i for i, k in enumerate(ka)}
    bmap = {k: j for j, k in enumerate(kb)}
    fi = {name: 1 + i for i, name in enumerate(sc.header)}      # +1 for leading route col
    NA, NG = len(_RV_AUX), len(_RV_GRID)
    NC = NA + NG

    def aval(row, name):
        if row is None:
            return ""
        v = row[fi[name]]
        return "" if v is None else str(v).strip()

    Fn = lambda **k: Font(name="Consolas", **{"size": 8.5, **k})
    fill = lambda c: PatternFill("solid", fgColor=c)
    HEAD, GRP = fill("21344F"), fill("3A5688")
    thin = Side(style="thin", color="D2D2D2")
    med = Side(style="medium", color="51607A")        # strong between-record divider
    bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    ctrW = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ctr = Alignment(horizontal="center", vertical="center")
    lft = Alignment(horizontal="left", vertical="center")
    _FONTS = {"hard": dict(color=_RV_FONTCOL["hard"], bold=True),
              "soft": dict(color=_RV_FONTCOL["soft"], bold=True),
              "tn": dict(color=_RV_FONTCOL["tn"]), "tm": dict(color=_RV_FONTCOL["tm"]),
              "id": dict(bold=True), "count": dict(bold=True)}

    ws = wb.create_sheet("Report View")
    ws.sheet_properties.tabColor = "21344F"
    ws.freeze_panes = "H5"      # MUST precede the streamed rows in write-only mode; keeps
                                # Major/Diffs/Route + P/PostMile/S/Location + the 4 header rows

    def value(spec, ra, rb, one):
        """Resolve a grid spec to (text, status). 'cmp' compares the normalized TSMIS
        and TSN cells (eq / soft / hard); 'tn' is a TSN-only column; everything else
        (blank / pm / loc handled in the row loop) is non-counting."""
        kind, ref = spec
        if kind == "tn":
            v = one.get(ref, "") if one else ""
            return (_iso_date(v) if ref in _RV_DATEONE else v, "tn")
        if kind == "tm":
            return (aval(ra, ref), "tm")
        if kind == "cmp":
            tm, tn = aval(ra, ref), aval(rb, ref)
            if tm == tn:
                return (tm, "eq")
            return (f"{tm or '·'} ≠ {tn or '·'}", _rv_classify(ref, tm, tn))
        return ("", "blank")

    def woc(val, status, alt, *, bottom=False, align=None):
        """A streamed data cell. Every status carries a (normal, ALT) band pair so a whole
        record alternates as one solid zebra band (white record vs grey record); an unknown
        status falls to 'eq' so a blank cell takes its record's band, not a stray shade."""
        c = WriteOnlyCell(ws, value=val)
        c.alignment = align or (lft if status == "id" else ctr)
        c.border = Border(left=thin, right=thin, bottom=(med if bottom else None))
        c.fill = fill(_RV_FILLS.get(status, _RV_FILLS["eq"])[1 if alt else 0])
        c.font = Fn(**_FONTS.get(status, {}))
        return c

    def hcell(val, fillc, font, align, comment_ref=None):
        """A streamed header cell, optionally carrying the normalization hover-comment."""
        c = WriteOnlyCell(ws, value=val)
        c.fill = fillc; c.font = font; c.alignment = align; c.border = bd
        t = _RV_COMMENTS.get(comment_ref) if comment_ref else None
        if t:
            cm = Comment(t, "TSMIS vs TSN"); cm.width = 250; cm.height = 130
            c.comment = cm
        return c

    # ---- 4-row header (the report's two stacked header blocks) ----
    g1 = [col[0] for col in _RV_GRID]
    g2 = [col[3] for col in _RV_GRID]

    def group_row(groups):
        """One header row of GROUP cells: the leftmost of each run carries the label and
        every cell in a non-empty run shares the GRP fill; empty groups stay plain."""
        cells, i = [], 0
        while i < NG:
            g, j = groups[i], i
            while j < NG and groups[j] == g:
                j += 1
            for k in range(i, j):
                if g:
                    cells.append(hcell(g if k == i else "", GRP,
                                       Fn(bold=True, color="FFFFFF", size=7.5), ctr))
                else:
                    cells.append(hcell("", PatternFill(), Fn(), ctr))
            i = j
        return cells

    aux_white = Fn(bold=True, color="FFFFFF", size=8)
    blank_dark = Fn()
    ws.append([hcell(lab, HEAD, aux_white, ctrW) for lab in _RV_AUX] + group_row(g1))
    ws.append([hcell("", HEAD, blank_dark, ctrW) for _ in _RV_AUX] +
              [hcell(col[1], HEAD, Fn(bold=True, color="FFFFFF", size=7.5), ctrW, col[2][1])
               for col in _RV_GRID])
    ws.append([hcell("", HEAD, blank_dark, ctrW) for _ in _RV_AUX] + group_row(g2))
    ws.append([hcell("", HEAD, blank_dark, ctrW) for _ in _RV_AUX] +
              [hcell(col[4], HEAD, Fn(color="BBD0EC", size=7.5), ctrW, col[5][1])
               for col in _RV_GRID])

    # ---- data: two physical rows per record, whole-record alternating band ----
    for n, key in enumerate(union):
        ra = rows_a[amap[key]] if key in amap else None
        rb = rows_b[bmap[key]] if key in bmap else None
        one = (tsn_one[bmap[key]] if (tsn_one and key in bmap and bmap[key] < len(tsn_one)) else {})
        location = ""
        if key in amap and amap[key] < len(tm_loc) and tm_loc[amap[key]]:
            location = tm_loc[amap[key]]
        elif one:
            location = one.get("LOC", "")
        pmval = aval(ra, "PM") or aval(rb, "PM") or (key[1] if len(key) > 1 else "")
        alt = (n % 2 == 1)
        # pass 1 — Major (genuine conflicts) + Diffs (every difference) counts
        maj = dif = 0
        for li in (0, 1):
            for col in _RV_GRID:
                _, st = value(col[2] if li == 0 else col[5], ra, rb, one)
                if st in ("soft", "hard"):
                    dif += 1
                    maj += (st == "hard")
        # pass 2 — assemble + append both physical rows
        for li in (0, 1):
            bottom = (li == 1)
            row = [woc(maj, "hard" if maj else "count", alt, bottom=bottom),
                   woc(dif, "count", alt, bottom=bottom),
                   woc(key[0], "count", alt, bottom=bottom)]
            for col in _RV_GRID:
                spec = col[2] if li == 0 else col[5]
                kind = spec[0]
                if kind == "loc":
                    text, st = location, "id"
                elif kind == "pm":
                    text, st = pmval, "id"
                else:
                    text, st = value(spec, ra, rb, one)
                align = lft if (li == 1 and col[4] == "DESCRIPTION") else None
                row.append(woc(text, st, alt, bottom=bottom, align=align))
            ws.append(row)

    # ---- header merges (aux labels down rows 1-4; group runs across) ----
    for i in range(1, NA + 1):
        ws.merged_cells.ranges.add(CellRange(min_col=i, max_col=i, min_row=1, max_row=4))

    def merge_groups(groups, hdr_row):
        i = 0
        while i < NG:
            g, j = groups[i], i
            while j < NG and groups[j] == g:
                j += 1
            if g and j - i > 1:
                ws.merged_cells.ranges.add(CellRange(
                    min_col=NA + i + 1, max_col=NA + j, min_row=hdr_row, max_row=hdr_row))
            i = j
    merge_groups(g1, 1)
    merge_groups(g2, 3)

    ws.auto_filter.ref = f"A4:{get_column_letter(NC)}{4 + 2 * len(union)}"
    for h, ht in {1: 13, 2: 22, 3: 13, 4: 14}.items():
        ws.row_dimensions[h].height = ht
    WG = {"P": 3.5, "POST MILE": 8, "S": 3, "LOCATION": 13, "DATE OF REC": 9.5,
          "H/G": 4, "CITY": 6, "R/U": 5}
    for ci, w in {1: 5.5, 2: 5.5, 3: 8}.items():
        ws.column_dimensions[get_column_letter(ci)].width = w
    for gi, col in enumerate(_RV_GRID):
        lab = col[1]
        w = (10.5 if lab == "EFF-DATE" else WG[lab] if lab in WG
             else 9 if lab in ("X-Ovr", "ML ADT") else 4.2)
        ws.column_dimensions[get_column_letter(NA + gi + 1)].width = w
    return ws


# --------------------------------------------------------------------------- #
# adapter surface
# --------------------------------------------------------------------------- #
def suggest_name(tsmis_path):
    stem = Path(tsmis_path).stem
    m = re.search(r"route[ _-]*([0-9]+[A-Za-z]?)", stem, re.IGNORECASE)
    tag = (f"Route{m.group(1).lstrip('0') or '0'}" if m
           else "Consolidated" if "consolidated" in stem.lower() else "Intersection_Detail")
    return f"TSMIS_vs_TSN_IntersectionDetail_{tag}_Comparison {today_str()}.xlsx"


def _load_pair(tsmis_path, tsn_path):
    """(rows_t, rows_n, warnings) for the shared driver — no input warnings on this
    FLAT detail pair, so run_compare uses its () default."""
    rows_t, _ = _load_tsmis(tsmis_path)
    rows_n, _ = _load_tsn(tsn_path)
    return rows_t, rows_n, None


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas"):
    """Build the Intersection Detail TSMIS-vs-TSN comparison workbook(s). `tsmis_path`
    is the consolidated TSMIS Intersection Detail workbook; `tsn_path` the TSN
    statewide (raw or normalized) workbook.

    A per-call schema adds the two-line 'Report View' replica via the EXISTING
    extra_sheet_writer opt-in (the flat Comparison sheet is untouched; compare_core
    stays unmodified). The TSN-only columns come from the raw TSN file (None for a
    normalized library) and the locations from the consolidated TSMIS — both read
    lazily inside the writer, so they only open the workbooks when a sheet is actually
    built (after a successful load)."""
    schema = dataclasses.replace(
        _SCHEMA, extra_sheet_writer=lambda wb, ctx: _write_report_view(
            wb, ctx, _tsn_onesided(Path(tsn_path)), _tsmis_locations(Path(tsmis_path))))
    return ctc.run_files_compare(
        schema, tsmis_path, tsn_path, out_path,
        banner="Intersection Detail Comparison — TSMIS vs TSN", has_route=True,
        loader=_load_pair, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        events=events, confirm_overwrite=confirm_overwrite, mode=mode)
