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
"pair-order reversal" was a misread of the shifted TSMIS labels). Three real
reconciliations:
  1. **Boolean encoding** — mastarm / right-channelization / lighting are Y/N on
     TSN but 1/0 on TSMIS. NORMALIZED here as Y≡1 / N≡0 (user decision) so only
     genuine changes flag; a Notes sheet + header note INDICATE this is applied.
  2. **Control-type taxonomy divergence** — TSN legacy codes (e.g. P) vs TSMIS new
     (S = signalized). No crosswalk (user decision) -> shows as genuine diffs.
  3. **Date of Record** is a TSMIS refresh date (not the record date) -> a CONTEXT
     field (shown, never counted), alongside the roadbed PR indicator.

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
SHARED_HEADER = [
    "PR", "PM", "HG", "City Code", "R/U", "INT Type", "Control Type", "Lighting",
    "ML Mastarm", "ML Left Chan", "ML Right Chan", "ML Traffic Flow", "ML Num Lanes",
    "Description", "CS Mastarm", "CS Left Chan", "CS Right Chan", "CS Traffic Flow",
    "CS Num Lanes", "Date of Record",
]
KEY_FIELD = SHARED_HEADER.index(KEY)      # 1
# Shown but never counted: the roadbed indicator, the TSMIS refresh date, and the
# CROSS-STREET attributes — TSMIS leaves cross-street detail blank for ~37% of
# intersections while TSN defaults them (so a raw compare floods 30k blank-vs-N
# cells that bury the substantive mainline differences). The mainline attributes +
# types ARE compared; the cross-street values stay visible (context) so a reviewer
# still sees the completeness gap without it dominating the diff count.
CONTEXT_FIELDS = ("PR", "Date of Record", "CS Mastarm", "CS Left Chan",
                  "CS Right Chan", "CS Traffic Flow", "CS Num Lanes")
DATE_FIELDS = ("Date of Record",)
# Y/N (TSN) vs 1/0 (TSMIS) booleans — normalized to Y/N so only real changes flag.
BOOLEAN_FIELDS = ("Lighting", "ML Mastarm", "ML Right Chan", "CS Mastarm", "CS Right Chan")

# TSN raw column name for each shared field (key + fields).
_TSN_COL = {
    "PR": "PP", "PM": "POST_MILE", "HG": "HG", "City Code": "CITY_CODE", "R/U": "RU",
    "INT Type": "TY_INT", "Control Type": "TY_CT", "Lighting": "LT_TY",
    "ML Mastarm": "MAIN_SM", "ML Left Chan": "MAIN_LC", "ML Right Chan": "MAIN_RC",
    "ML Traffic Flow": "MAIN_TF", "ML Num Lanes": "MAIN_NL", "Description": "DESCRIPTION",
    "CS Mastarm": "CS_SM", "CS Left Chan": "CS_LC", "CS Right Chan": "CS_RC",
    "CS Traffic Flow": "CS_TF", "CS Num Lanes": "CS_NL", "Date of Record": "DATE_REC",
}
# Consolidated-TSMIS VALUE position for each shared field (Route at 0; header is
# column-shifted so position — not label — is authoritative; verified on route 1).
_TSMIS_POS = {
    "PR": 1, "PM": 2, "HG": 6, "City Code": 7, "R/U": 8, "INT Type": 10,
    "Control Type": 12, "Lighting": 14, "ML Mastarm": 16, "ML Left Chan": 17,
    "ML Right Chan": 18, "ML Traffic Flow": 19, "ML Num Lanes": 20, "Description": 22,
    "CS Mastarm": 25, "CS Left Chan": 26, "CS Right Chan": 27, "CS Traffic Flow": 28,
    "CS Num Lanes": 29, "Date of Record": 5,
}
_TSMIS_ROUTE_POS = 4                       # consolidated "Location" column ("12 ORA 001")


# --------------------------------------------------------------------------- #
# normalization
# --------------------------------------------------------------------------- #
def _norm_route(tok):
    t = str(tok or "").strip().upper().replace("-", " ")
    parts = t.split()
    last = parts[-1] if parts else ""
    m = re.fullmatch(r"(\d+)([A-Z]?)", last)
    return f"{int(m.group(1)):03d}{m.group(2)}" if m else last


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


def _v(x):
    return normalize_value(x)


def _project(field, raw):
    """Normalize one raw cell for `field` into the shared, comparable form."""
    if field in BOOLEAN_FIELDS:
        return _norm_bool(raw)
    if field == "PM":
        return _norm_pm(raw)
    if field == "Date of Record":
        return _iso_date(raw)
    return _v(raw)


# --------------------------------------------------------------------------- #
# loaders -> consolidated-shape rows ([route, *SHARED_HEADER])
# --------------------------------------------------------------------------- #
def _tsn_row(r, h):
    def g(name):
        i = h.get(name)
        return r[i] if i is not None and i < len(r) else None
    route = _norm_route(g("LOCATION"))
    return [route] + [_project(f, g(_TSN_COL[f])) for f in SHARED_HEADER]


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
            rows = [[_v(c) for c in list(r)[:len(SHARED_HEADER) + 1]]
                    for r in it if r and any(c not in (None, "") for c in r)]
            return rows, True
    finally:
        wb.close()
    return tsn_rows_from_raw(path), True


def _tsmis_row(r):
    def at(i):
        return r[i] if i < len(r) else None
    route = _norm_route(at(_TSMIS_ROUTE_POS))
    return [route] + [_project(f, at(_TSMIS_POS[f])) for f in SHARED_HEADER]


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
# Notes sheet — the INDICATOR that boolean normalization is applied
# --------------------------------------------------------------------------- #
def _write_notes_sheet(wb):
    ws = wb.create_sheet("Notes")
    ws.sheet_properties.tabColor = "ED7D31"
    write_only = getattr(wb, "write_only", False)
    title = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    fill = PatternFill("solid", start_color="1F3864")
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

    ws.column_dimensions["A"].width = 110
    ws.append([cell("Intersection Detail — TSMIS vs TSN: comparison notes", title, fill)])
    for line in (
        "Boolean attributes (Lighting, ML Mastarm, ML Right Chan, CS Mastarm, CS Right "
        "Chan) are encoded Y/N on TSN but 1/0 on TSMIS. They are NORMALIZED as Y≡1 / "
        "N≡0 so only genuine changes are flagged (not the encoding); cells are shown as Y/N.",
        "Control Type uses different code sets between the systems (TSN legacy signal codes "
        "vs TSMIS S=Signalized etc.) — NO crosswalk is applied, so a code change reads as a "
        "genuine difference.",
        "CONTEXT columns (shown for reference, never counted as a difference): the PR "
        "roadbed indicator; Date of Record (a TSMIS refresh date, not the record date); and "
        "the five CROSS-STREET attributes (CS Mastarm / Left Chan / Right Chan / Traffic Flow "
        "/ Num Lanes) — TSMIS leaves cross-street detail blank for ~37% of intersections while "
        "TSN defaults it, so counting them would bury the substantive mainline differences. The "
        "cross-street values are still shown so the completeness gap is visible.",
        "Rows are keyed on Route + Postmile (PM); attribute effective-dates are not compared.",
    ):
        ws.append([cell(line, body, align=wrap)])
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
