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
reader adds commentary, the tool never hides a column — EXCEPT two columns that are
SHOWN BUT NOT COUNTED (greyed): the second mainline eff-date and the int-street
eff-date are a uniform "2024" bulk-load stamp on the TSMIS side with no comparable TSN
date, so they appear for reference but never flag. Columns ordered to mirror the source
report. The five real effective dates (INT / Control / Lighting / Mainline / Cross-street),
Main Line Length, and the intersecting-route block ARE compared (previously omitted); the
eff-dates are a systematic ~1 day apart and flag on that offset. Some columns differ on
nearly every row by their nature (see below); they are still flagged, and the Notes sheet
COMMENTS on why rather than suppressing them. Normalizations make some raw-different
values compare equal; each is documented in the Notes sheet so a match is read as "equal
after the stated normalization", not raw equality:
  1. **Boolean encoding** — mastarm / right-channelization / lighting are Y/N on
     TSN but 1/0 on TSMIS. NORMALIZED here as Y≡1 / N≡0 so only genuine changes flag
     (a TSMIS cell shown as "Y" was stored "1"); the Notes sheet states this.
  2. **Control-type crosswalk** — TSN records signalized under the legacy signal
     sub-types J/K/L/M/N/P, which TSNR/TSMIS collapses into the single category "S".
     Per the TSNR/MIRE reference, both sides' signalized codes are normalized to one
     readable "Signalized" category so the sub-type split stops flagging — and the
     word "Signalized" (vs the raw letter codes) makes the merge visible on the page;
     the Notes sheet documents it. (Geometry/INT Type needs no crosswalk — both
     systems share the F/M/S/T/Y/Z/R codes.)
  3. **Date of Record** is a TSMIS refresh date (not the historical record date), so
     the whole column differs from TSN — it is compared and counted like everything
     else, and the Notes sheet comments on why the column differs wholesale.
  4. **Cross-street (CS*) attributes** — TSMIS leaves them blank for ~37% of
     intersections while TSN defaults them, so that column shows many blank-vs-value
     differences; compared and counted, with the completeness gap noted.

Console-free; engine in compare_core.
"""
import re
from pathlib import Path

try:
    from openpyxl import load_workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from compare_core import CompareSchema, normalize_value, run_compare
from events import ConsolidateResult, Events
from paths import today_str

REPORT_NAME = "Intersection Detail"
TSMIS_SHEET = "Intersection Detail"      # consolidated sheet (Route prepended)
TSN_SHEET = "Sheet 1"                     # raw statewide DB dump
NORMALIZED_SHEET = "Intersection Detail (TSN)"

KEY = "PM"
# Column order mirrors the source report (each effective-date next to its type, the
# mainline block, then the cross-street block, then the intersecting route). Every
# field present in both systems is compared EXCEPT the two CONTEXT_FIELDS below.
SHARED_HEADER = [
    "PR", "Roadbed", "PM", "Date of Record", "HG", "City Code", "R/U",
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
KEY_FIELD = SHARED_HEADER.index(KEY)      # 2 (after PR + the derived Roadbed column)
# Two columns are SHOWN BUT NOT COUNTED (context): the second mainline eff-date and the
# int-street eff-date are a uniform "2024" bulk-load stamp on the TSMIS side with no
# comparable TSN counterpart — they appear (greyed) for reference but never flag. The
# five real eff-dates (INT/Control/Lighting/Mainline/Cross-street) ARE compared: each is
# systematically ~1 day apart (TSMIS Dec 31 vs TSN Jan 1) and flags on that offset (raw,
# user decision); the Notes sheet documents it. Everything else present in both systems
# is compared and counted (a mechanical diff).
CONTEXT_FIELDS = ("ML 2nd Eff-Date", "Int St Eff-Date")
DATE_FIELDS = ("Date of Record", "INT Type Eff-Date", "Control Type Eff-Date",
               "Lighting Eff-Date", "ML Eff-Date", "ML 2nd Eff-Date", "CS Eff-Date",
               "Int St Eff-Date")
# Y/N (TSN) vs 1/0 (TSMIS) booleans — normalized to Y/N so only real changes flag.
BOOLEAN_FIELDS = ("Lighting", "ML Mastarm", "ML Right Chan", "CS Mastarm", "CS Right Chan")
# Control-type crosswalk (per the TSNR/MIRE reference "TSNR - Intersection Control
# and Geometry Type"): TSN spreads "Signalized" across the legacy signal sub-types
# J–P (J/K/L/M/N/P), which TSNR/TSMIS collapses into the single category TSMIS stores
# as "S". Both sides' signalized codes normalize to the readable category label
# below — so the compared Control Type shows the word "Signalized" (visibly a merged
# category, distinct from the raw single-letter codes) wherever the crosswalk applied,
# and the sub-type split stops flagging as a difference. The Notes sheet documents the
# crosswalk. Geometry (INT Type) needs NO crosswalk — both systems share F/M/S/T/Y/Z/R.
_SIGNALIZED_CODES = {"J", "K", "L", "M", "N", "P", "S"}
_SIGNALIZED_LABEL = "Signalized"

# TSN raw column name for each shared field (key + fields).
_TSN_COL = {
    "PR": "PP", "PM": "POST_MILE", "HG": "HG", "City Code": "CITY_CODE", "R/U": "RU",
    "INT Type": "TY_INT", "Control Type": "TY_CT", "Lighting": "LT_TY",
    "ML Mastarm": "MAIN_SM", "ML Left Chan": "MAIN_LC", "ML Right Chan": "MAIN_RC",
    "ML Traffic Flow": "MAIN_TF", "ML Num Lanes": "MAIN_NL", "Description": "DESCRIPTION",
    "CS Mastarm": "CS_SM", "CS Left Chan": "CS_LC", "CS Right Chan": "CS_RC",
    "CS Traffic Flow": "CS_TF", "CS Num Lanes": "CS_NL", "Date of Record": "DATE_REC",
    # added columns (TSN counterpart verified across 16k paired rows). The eff-dates map
    # to the RECENT TSN dates (98% a clean 1-day offset); the two context columns map to
    # the leftover historical TSN dates (shown, not counted).
    "INT Type Eff-Date": "EFF_DATE_INT", "Control Type Eff-Date": "EFF_DATE_CT",
    "Lighting Eff-Date": "EFF_DATE_LT", "ML Eff-Date": "MAIN_EFF_DATE",
    "CS Eff-Date": "EFF_DATE", "Main Line Length": "MAIN_OVERRIDE",
    "ML 2nd Eff-Date": "EFF_DATE_ML", "Int St Eff-Date": "CROSS_BEGIN_DATE",
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
    """Split a LOCATION token into (base_route, roadbed_suffix):
    '12 ORA 210U' -> ('210', 'U'); '12 ORA. 210' -> ('210', '').

    California divided highways carry a roadbed letter (S/U) on the route name that
    TSN keeps but TSMIS often omits. Keying on the BASE route lets the same
    intersection still pair across that label difference, while the suffix is
    surfaced as the compared 'Roadbed' column — so a suffix-only difference is
    flagged there (TSN 'U' vs TSMIS blank) rather than the rows being dropped to
    one-sided OR silently merged."""
    t = str(tok or "").strip().upper().replace("-", " ")
    parts = t.split()
    last = parts[-1] if parts else ""
    m = re.fullmatch(r"(\d+)([A-Z]?)", last)
    return (f"{int(m.group(1)):03d}", m.group(2)) if m else (last, "")


def _norm_route(tok):
    """The base route number (roadbed suffix stripped) — the row key. See _split_route."""
    return _split_route(tok)[0]


def _norm_pm(pm):
    s = str(pm or "").strip()
    if not s:
        return ""
    neg = s.startswith("-")
    s = s.lstrip("-").lstrip("0") or "0"
    if s.startswith("."):
        s = "0" + s
    return ("-" + s) if neg else s


def _iso_date(d):
    s = str(d or "").strip()
    if not s:
        return ""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{2})-(\d{2})-(\d{2})$", s)        # TSN '73-10-19' (YY-MM-DD)
    if m:
        yy = int(m.group(1))
        cc = 1900 if yy >= 30 else 2000                # 2-digit-year window
        return f"{cc + yy}-{m.group(2)}-{m.group(3)}"
    return s


_BOOL = {"Y": "Y", "N": "N", "1": "Y", "0": "N"}


def _norm_bool(v):
    return _BOOL.get(str(v or "").strip().upper(), str(v or "").strip())


def _norm_control_type(v):
    """Apply the TSN→TSNR control-type crosswalk: the legacy signal sub-types J–P
    (TSN) and TSMIS's combined "S" all fold into the single readable category
    "Signalized", so the sub-type split no longer reads as a difference and the
    merge is visible on the page (the word "Signalized" vs the raw letter codes).
    Every other code is left as-is (both systems share A/B/C/D/E/F/G/H/I/R/Z)."""
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
    return _v(raw)


# --------------------------------------------------------------------------- #
# loaders -> consolidated-shape rows ([route, *SHARED_HEADER])
# --------------------------------------------------------------------------- #
def _tsn_row(r, h):
    def g(name):
        i = h.get(name)
        return r[i] if i is not None and i < len(r) else None
    base, roadbed = _split_route(g("LOCATION"))
    return [base] + [roadbed if f == "Roadbed" else _project(f, g(_TSN_COL[f]))
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
    workbook built before a normalization change (e.g. before the J–P→Signalized
    crosswalk) would otherwise feed raw codes straight through `_v` and flag a
    phantom 'Signalized ≠ P'. Normalizing at COMPARE time means a normalization
    change takes effect immediately, without rebuilding the library."""
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
    base, roadbed = _split_route(at(_TSMIS_ROUTE_POS))
    return [base] + [roadbed if f == "Roadbed" else _project(f, at(_TSMIS_POS[f]))
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
         "TSNR/TSMIS collapses them into ONE category stored as 'S'. Both sides' signalized "
         "codes are normalized to the single readable category 'Signalized'. HOW TO SEE IT: "
         "wherever the Control Type cell reads the word 'Signalized' (not a raw letter code), "
         "the crosswalk was applied and a TSN J–P matched a TSMIS S. Every other control code "
         "(A/B/C/D/E/F/G/H/I/R/Z) is shared and compared unchanged. INT Type needs no "
         "crosswalk — both systems share the F/M/S/T/Y/Z/R codes.")
    note("• Boolean encoding — Lighting, ML Mastarm, ML Right Chan, CS Mastarm, CS Right "
         "Chan are stored Y/N on TSN but 1/0 on TSMIS. Normalized as Y≡1 / N≡0, so only a "
         "genuine change flags (not the encoding). HOW TO SEE IT: a cell shown as 'Y' on the "
         "TSMIS side was stored '1' (and 'N' was '0').")
    note("• Postmile (PM) — leading zeros and spaces are stripped so the same postmile pairs "
         "across formatting (TSN ' 004.901' ≡ TSMIS '4.901'). PM is the row key.")
    note("• Roadbed suffix — California divided highways carry an S/U suffix on the route name "
         "that TSN keeps but TSMIS often omits (TSN '210U' vs TSMIS '210'). Rows are matched on "
         "the BASE route number so the same intersection still pairs; the suffix is compared in "
         "the 'Roadbed' column (TSN 'U' vs TSMIS blank flags there) rather than dropping the row.")

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
    note("• Effective-date columns (INT Type / Control Type / Lighting / Mainline / Cross-street "
         "Eff-Date) — COMPARED. All five sit a SYSTEMATIC ~1 day apart (TSMIS stores Dec 31, TSN "
         "stores Jan 1: '1973-10-18' vs '1973-10-19', or '2021-12-31' vs '2022-01-01') — an "
         "encoding convention, not per-intersection edits. They flag on that 1-day offset by "
         "design (raw comparison); read the count as the convention, not thousands of changes. "
         "Mainline maps to TSN MAIN_EFF_DATE, cross-street to EFF_DATE (the recent dates).")
    note("• Intersecting-route block (Intrte Route / PM Prefix / Postmile / PM Suffix) + Main "
         "Line Length — also compared. The intersecting route is mostly blank on both (only ~10 "
         "intersections cross another state route); differences are genuine where present.")

    section("SHOWN BUT NOT COUNTED  (greyed columns — present for reference, never flagged)")
    note("• ML 2nd Eff-Date and Int St Eff-Date are a uniform '2024' bulk-load stamp on the "
         "TSMIS side with no comparable TSN date, so they are shown (greyed) but never count as a "
         "difference. TSMIS's roadbed 'S' / second 'Xing' route stubs are blank and omitted; TSN's "
         "ADT columns (MAIN_ADT / CROSS_ADT) have no TSMIS counterpart and are not shown.")
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
    context_fields=CONTEXT_FIELDS,
    context_fill="D9D9D9",          # grey the 2 shown-but-not-counted columns
    legend_writer=_write_notes_sheet,
)


# --------------------------------------------------------------------------- #
# adapter surface
# --------------------------------------------------------------------------- #
def suggest_name(tsmis_path):
    stem = Path(tsmis_path).stem
    m = re.search(r"route[ _-]*([0-9]+[A-Za-z]?)", stem, re.IGNORECASE)
    tag = (f"Route{m.group(1).lstrip('0') or '0'}" if m
           else "Consolidated" if "consolidated" in stem.lower() else "Intersection_Detail")
    return f"TSMIS_vs_TSN_IntersectionDetail_{tag}_Comparison {today_str()}.xlsx"


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas"):
    """Build the Intersection Detail TSMIS-vs-TSN comparison workbook(s). `tsmis_path`
    is the consolidated TSMIS Intersection Detail workbook; `tsn_path` the TSN
    statewide (raw or normalized) workbook."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (openpyxl).")
    tsmis_path, tsn_path = Path(tsmis_path), Path(tsn_path)
    for p, side in ((tsmis_path, "TSMIS"), (tsn_path, "TSN")):
        if not p.is_file():
            return ConsolidateResult(status="error",
                                     message=f"The {side} file doesn't exist:\n{p}")

    events.on_log("=" * 60)
    events.on_log("Intersection Detail Comparison — TSMIS vs TSN")
    events.on_log("=" * 60)
    events.on_log(f"TSMIS: {tsmis_path.name}")
    events.on_log(f"TSN:   {tsn_path.name}")
    events.on_log("")

    try:
        rows_t, route_t = _load_tsmis(tsmis_path)
        rows_n, route_n = _load_tsn(tsn_path)
    except ValueError as e:
        return ConsolidateResult(status="error", message=str(e))

    return run_compare(_SCHEMA, rows_t, rows_n, True, out_path,
                       events=events, confirm_overwrite=confirm_overwrite,
                       mode=mode, name_a=tsmis_path.name, name_b=tsn_path.name)
