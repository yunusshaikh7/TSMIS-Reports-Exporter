"""Build the TSMIS-vs-TSN Highway Log discrepancy workbook.

Takes a TSMIS Highway Log and a TSN Highway Log — either BOTH per-route
workbooks (31 columns, one route each) or BOTH consolidated workbooks (a
leading "Route" column, every route) — and writes one four-sheet comparison
workbook (the format approved from the Route-1 sample):

  Summary      row counts, match status, per-field difference counts, live
               SELF-CHECK rows (cross-totals that prove the formulas line up),
               notes
  Spot Check   one location under a microscope: type a Comparison row number
               (or find one by route+location) and every field shows the raw
               values from both data sheets plus an INDEPENDENTLY recomputed
               verdict with an Agree? column — the audit surface for anyone
               who doubts the formulas
  Comparison   one row per (Route,) Location + occurrence in EITHER file, in
               document order; per-field cells show the matched value, or
               "tsmis ≠ tsn" in red when the systems disagree (TSMIS first);
               the TSMIS/TSN Row numbers are clickable jumps to the source
               row, and each data-sheet row links back
  Only in TSMIS / Only in TSN
               every one-sided row pulled out where it can't be missed — the
               rows of routes the other system lacks entirely (consolidated
               mode flags those as "entire route" and tints them) plus the
               locations missing from the other side within shared routes
  TSMIS / TSN  the two inputs, plus a "Key (helper)" lookup column

In the default "formulas" flavor EVERYTHING in the workbook is a live Excel
formula (lookup keys, statuses, diff counts, summary): edit a value on the
TSMIS or TSN sheet and the whole report recalculates. The Python side only
decides the row universe (the union of location keys, aligned in document
order) and writes the formulas. Note for the consolidated case: the live
keys/lookups make Excel's FIRST recalc of a 50k-row comparison take a while —
that's the price of a fully live workbook.

compare(..., mode=) also offers a "values" flavor (and "both"): the same
sheets, colors and links, but the bulk written as plain computed RESULTS via
the same Python mirror that powers the run summary — opens instantly, no
manual-calculation mode, roughly a third the size; only the Spot Check sheet
and the Summary's SELF-CHECK rows stay live (they recount the literal
sheets, so internal consistency remains provable in Excel).

Comparison semantics (mirrored in _count_diffs for the run summary):
  * Rows are keyed on (Route +) Location plus occurrence number (duplicates
    like a postmile listed twice pair up by order of appearance).
  * The union is a diff-style document-order merge per route with
    first-position dedupe — postmiles can legitimately run backwards at
    realignments (TSMIS prints some out of order), so sorting would lie.
  * Values compare after Excel TRIM (the TSMIS export pads Description).
  * Med Wid first normalizes zero-padding in the numeric part (TSMIS '0Z' =
    TSN '00Z'); every other field compares exactly.

The per-route output is verified cell-for-cell against the approved sample
(same union order, same counts, same formulas modulo the matched-value
display); the consolidated layout is the same design with a Route key column.

Console-free like the other report modules: progress via events.on_log,
overwrite via the confirm_overwrite callback, cancel honored between phases,
ConsolidateResult returned.
"""
import difflib
import re
from datetime import date
from pathlib import Path

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.formatting.rule import CellIsRule, FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from events import ConsolidateResult, Events

REPORT_NAME = "Highway Log"          # registry label (comparison type)
SHEET_NAME = "Highway Log"           # required sheet in both inputs

# The per-route Highway Log layout (TSMIS export == converted TSN file).
# Consolidated workbooks carry ["Route"] + this.
EXPECTED_HEADER = [
    "Location", "MI", "N/A", "Cnty Odom", "City", "R/U", "SPD", "TER", "H/G",
    "A/C", "LB T", "LB Lns", "LB F", "LB OT", "LB TR", "LB T-W", "LB IN",
    "LB SH", "Med TCB", "Med Wid", "RB T", "RB Lns", "RB F", "RB IN", "RB SH",
    "RB T-W", "RB OT", "RB SH", "Description", "Date of Rec", "Sig Chg. Date",
]
N_FIELDS = len(EXPECTED_HEADER) - 1      # data fields (everything but Location)

# Styling shared by all sheets (colors taken from the approved sample; the
# Only-in tab colors echo the Comparison sheet's yellow/blue row tints).
_DARK = "1F3864"            # header band / banners
_TAB = {"Summary": "808080", "Spot Check": "7030A0", "Comparison": "C00000",
        "Routes": "ED7D31", "Only in TSMIS": "BF8F00", "Only in TSN": "2E75B6",
        "TSMIS": "4472C4", "TSN": "70AD47"}
_DIFF_MARK = " ≠ "          # appears ONLY in differing cells; counts key on it

_PROGRESS_EVERY = 10_000    # log + cancel-check cadence on big workbooks


def suggest_name(tsmis_path):
    """Output filename suggestion: 'TSMIS_vs_TSN_Route<id>_Comparison.xlsx'
    when the picked file carries a route token, consolidated-aware otherwise."""
    stem = Path(tsmis_path).stem
    m = re.search(r"route[ _-]*([0-9]+[A-Za-z]?)", stem, re.IGNORECASE)
    if m:
        tag = f"Route{m.group(1).lstrip('0') or '0'}"
    elif "consolidated" in stem.lower():
        tag = "Consolidated"
    else:
        tag = "Highway_Log"
    return f"TSMIS_vs_TSN_{tag}_Comparison.xlsx"


# =============================================================================
# Input loading
# =============================================================================

def _load_input(path):
    """Load one Highway Log workbook -> (rows, has_route).

    Accepts the per-route layout (31 columns) and the consolidated layout
    ("Route" + 31). Raises ValueError with a user-safe message otherwise."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if SHEET_NAME not in wb.sheetnames:
            raise ValueError(
                f"{name} has no '{SHEET_NAME}' sheet — pick a Highway Log "
                f"workbook (a TSMIS export or consolidation, or a TSN file "
                f"made by the TSN Highway Log consolidation).")
        rows_iter = wb[SHEET_NAME].iter_rows(values_only=True)
        header = [v for v in next(rows_iter, [])]
        while header and header[-1] in (None, ""):
            header.pop()
        if header == EXPECTED_HEADER:
            has_route = False
        elif header == ["Route"] + EXPECTED_HEADER:
            has_route = True
        else:
            raise ValueError(
                f"{name} doesn't have the Highway Log column layout this "
                f"comparison expects — re-create it with this app, then retry.")
        n = len(header)
        rows = []
        for r in rows_iter:
            r = list(r)[:n] + [None] * max(0, n - len(r))
            if any(v is not None and str(v).strip() != "" for v in r):
                rows.append(r)
        return rows, has_route
    finally:
        wb.close()


def _keys(rows, has_route):
    """[(route, location, occurrence), ...] in file order (route "" for the
    per-route layout). Occurrence repeats of the same (route, location) are
    numbered 1.., exactly like the sheets' live helper column."""
    seen = {}
    out = []
    for r in rows:
        if has_route:
            route = "" if r[0] is None else str(r[0])
            loc = "" if r[1] is None else str(r[1])
        else:
            route, loc = "", ("" if r[0] is None else str(r[0]))
        k = (route, loc)
        seen[k] = seen.get(k, 0) + 1
        out.append((route, loc, seen[k]))
    return out


def _union_keys(keys_t, keys_n):
    """The union of the two key sequences in DOCUMENT order, grouped by route:
    TSMIS's routes in TSMIS order (TSN-only routes appended in TSN order),
    and within each route a diff-style alignment of the two row sequences.

    Common keys appear exactly once (first position wins — a key can fall
    outside the aligner's 'equal' blocks when one file lists it out of
    sequence; seen in the field: TSMIS printed 059.739 after 059.759 while
    TSN kept it in order). The Excel MATCH lookups pair each union row with
    both files regardless of where it sits. Aligning per route keeps the
    matcher fast on consolidated inputs (50k+ rows)."""
    by_route_t, by_route_n = {}, {}
    for k in keys_t:
        by_route_t.setdefault(k[0], []).append(k)
    for k in keys_n:
        by_route_n.setdefault(k[0], []).append(k)

    out = []
    seen = set()

    def emit(keys):
        for k in keys:
            if k not in seen:
                seen.add(k)
                out.append(k)

    routes = list(by_route_t) + [r for r in by_route_n if r not in by_route_t]
    for route in routes:
        seq_t = by_route_t.get(route, [])
        seq_n = by_route_n.get(route, [])
        if not seq_t or not seq_n:
            emit(seq_t or seq_n)
            continue
        sm = difflib.SequenceMatcher(None, seq_t, seq_n, autojunk=False)
        for op, a0, a1, b0, b1 in sm.get_opcodes():
            if op == "equal" or op == "delete":
                emit(seq_t[a0:a1])
            elif op == "insert":
                emit(seq_n[b0:b1])
            else:                       # replace: TSMIS block, then TSN block
                emit(seq_t[a0:a1])
                emit(seq_n[b0:b1])
    return out


# =============================================================================
# Python mirror of the workbook's comparison semantics (for the run summary;
# the workbook itself recomputes everything with live formulas)
# =============================================================================

def _xl_trim(v):
    """Excel TRIM: text form, edge spaces stripped, internal runs collapsed."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(" +", " ", str(v)).strip(" ")


def _medwid_norm(t):
    """Mirror the Med Wid formula: VALUE() the whole code, else VALUE() all but
    the last character and keep that suffix, else the raw text — so '0Z',
    '00Z' and '06V'/'6V' compare as equals."""
    def num(s):
        if re.fullmatch(r"\d+(\.\d+)?", s):
            f = float(s)
            return str(int(f)) if f.is_integer() else str(f)
        return None
    n = num(t)
    if n is not None:
        return n
    if t:
        n = num(t[:-1])
        if n is not None:
            return n + t[-1]
    return t


def _count_diffs(rows_t, rows_n, keys_t, keys_n, union, has_route):
    """Counts matching what the workbook's formulas will compute: overall
    totals, per-field difference counts, per-route aggregates (consolidated),
    and the FIRST matched-with-differences Comparison row (the Spot Check
    sheet's default). The same numbers back the run summary AND become the
    literal cells of the values workbook, so the two output flavors can
    never disagree."""
    off = 1 if has_route else 0          # data fields start after Route
    by_t = {k: rows_t[i] for i, k in enumerate(keys_t)}
    by_n = {k: rows_n[i] for i, k in enumerate(keys_n)}
    both = t_only = n_only = diff_rows = identical = diff_cells = 0
    first_diff_row = None
    field_diffs = {f: 0 for f in range(1, len(EXPECTED_HEADER))}
    route = {}                           # consolidated: per-route aggregates

    def rstat(rid):
        return route.setdefault(rid, {"t_rows": 0, "n_rows": 0, "locs": 0,
                                      "matched": 0, "withdiffs": 0, "cells": 0})
    if has_route:
        for k in keys_t:
            rstat(k[0])["t_rows"] += 1
        for k in keys_n:
            rstat(k[0])["n_rows"] += 1
    for i, k in enumerate(union):
        rt, rn = by_t.get(k), by_n.get(k)
        rs = rstat(k[0]) if has_route else None
        if rs is not None:
            rs["locs"] += 1
        if rt is None:
            n_only += 1
            continue
        if rn is None:
            t_only += 1
            continue
        both += 1
        if rs is not None:
            rs["matched"] += 1
        row_diffs = 0
        for f in range(1, len(EXPECTED_HEADER)):     # every field but Location
            va, vb = _xl_trim(rt[f + off]), _xl_trim(rn[f + off])
            if EXPECTED_HEADER[f] == "Med Wid":
                va, vb = _medwid_norm(va), _medwid_norm(vb)
            if va != vb:
                row_diffs += 1
                field_diffs[f] += 1
        diff_cells += row_diffs
        if rs is not None:
            rs["cells"] += row_diffs
            if row_diffs:
                rs["withdiffs"] += 1
        if row_diffs:
            diff_rows += 1
            if first_diff_row is None:
                first_diff_row = i + 2
        else:
            identical += 1
    return {"both": both, "t_only": t_only, "n_only": n_only,
            "diff_rows": diff_rows, "identical": identical,
            "diff_cells": diff_cells, "first_diff_row": first_diff_row,
            "field_diffs": field_diffs, "route": route}


# =============================================================================
# Layout: column geometry for the two input shapes
# =============================================================================

class _Layout:
    """Column letters for both workbook shapes.

    per-route:    data sheets  Comparison row=A (back-link), Location=B,
                  fields C..AF, key helper AG
                  comparison   Location,#,TSMIS Row,TSN Row,Status,Diffs,fields G..AJ
    consolidated: data sheets  Comparison row=A (back-link), Route=B,
                  Location=C, fields D..AG, key helper AH
                  comparison   Route,Location,#,...,fields H..AK
    """

    def __init__(self, has_route):
        self.has_route = has_route
        self.off = 1 if has_route else 0
        # data sheets: a leading "Comparison row" back-link column, then the
        # input's columns, then the live key helper
        self.data_header = (["Route"] if has_route else []) + EXPECTED_HEADER
        self.back_col = "A"                                  # back-link column
        self.route_data_col = "B" if has_route else None     # Route on data sheets
        self.key_col = get_column_letter(len(self.data_header) + 2)   # AG / AH
        self.data_last_col = get_column_letter(len(self.data_header) + 1)  # AF / AG
        # comparison sheet
        self.id_headers = ((["Route"] if has_route else [])
                           + ["Location", "#", "TSMIS Row", "TSN Row", "Status", "Diffs"])
        self.f0 = len(self.id_headers) + 1            # first field column index (G / H)
        self.last_field_col = get_column_letter(self.f0 + N_FIELDS - 1)  # AJ / AK
        c = [get_column_letter(i + 1) for i in range(len(self.id_headers))]
        if has_route:
            (self.c_route, self.c_loc, self.c_occ, self.c_trow, self.c_nrow,
             self.c_status, self.c_diffs) = c
        else:
            self.c_route = None
            (self.c_loc, self.c_occ, self.c_trow, self.c_nrow,
             self.c_status, self.c_diffs) = c

    def data_col(self, field_idx):
        """Data-sheet column letter for EXPECTED_HEADER[field_idx] (the data
        sheets carry a leading "Comparison row" link column)."""
        return get_column_letter(field_idx + 2 + self.off)

    def field_col(self, field_idx):
        """Comparison-sheet column letter for EXPECTED_HEADER[field_idx]."""
        return get_column_letter(self.f0 + field_idx - 1)

    def key_expr(self, r):
        """The lookup key for Comparison row r (matches the helper column)."""
        if self.has_route:
            return f"${self.c_route}{r}&\"|\"&${self.c_loc}{r}&\"|\"&${self.c_occ}{r}"
        return f"${self.c_loc}{r}&\"|\"&${self.c_occ}{r}"

    def helper_formula(self, r):
        """The data sheets' live key column (occurrence via COUNTIF[S]).
        Route/Location sit in B/C (B alone per-route) — column A is the
        "Comparison row" back-link."""
        if self.has_route:
            return (f'=B{r}&"|"&C{r}&"|"&COUNTIFS($B$2:$B{r},$B{r},'
                    f'$C$2:$C{r},$C{r})')
        return f'=B{r}&"|"&COUNTIF($B$2:$B{r},$B{r})'


# =============================================================================
# Workbook writing
# =============================================================================

def _trim_ref(sheet, col, row_ref):
    return f'TRIM(INDEX({sheet}!{col}:{col},{row_ref}))'


def _row_link(side, key, lay):
    """The 'TSMIS Row' / 'TSN Row' cell: the matched data-sheet row number as
    a CLICKABLE link, so a doubter can eyeball the source values instead of
    trusting the lookup. The link targets the ENTIRE ROW ("57:57"), so Excel
    selects the whole row on arrival — a temporary highlight that clears on
    the next click — while the view stays at the frozen left columns.
    (A bounded range like A57:AH57 made Excel scroll to the range's RIGHT
    edge when it didn't fit the window — measured via COM on real Excel;
    row-only references keep scrollColumn at home.) HYPERLINK's friendly
    value is the MATCH number itself, so the cell still counts as a number
    (the Summary SELF-CHECK relies on COUNT) — the MATCH is computed three
    times (range start, range end, display)."""
    m = f'MATCH({key},{side}!${lay.key_col}:${lay.key_col},0)'
    return f'=IFERROR(HYPERLINK("#{side}!"&{m}&":"&{m},{m}),"")'


def _row_link_value(side, row_num, lay):
    """_row_link with the row number known at build time (values workbook):
    same whole-row jump-and-select, no MATCH."""
    return f'=HYPERLINK("#{side}!{row_num}:{row_num}",{row_num})'


def _link_font():
    return Font(name="Arial", size=10, color="0563C1", underline="single")


def _medwid_ref(sheet, col, row_ref):
    """The zero-padding-normalized form of a Med Wid cell (see _medwid_norm)."""
    t = _trim_ref(sheet, col, row_ref)
    return (f'IFERROR(VALUE({t})&"",'
            f'IFERROR(VALUE(LEFT({t},LEN({t})-1))&RIGHT({t},1),{t}))')


def _field_formula(lay, r, field_idx):
    """Comparison cell formula for data field `field_idx` (1-based into
    EXPECTED_HEADER) on Comparison row `r`: the matched value when the two
    systems agree, 'tsmis ≠ tsn' when they differ, and on single-side rows
    (TSMIS only / TSN only — tinted yellow/blue) that system's own value, so
    the row's data is still readable instead of blank. Excel's IF evaluates
    only the taken branch, so the absent side's INDEX (whose row ref is "")
    is never computed on single-side rows."""
    col = lay.data_col(field_idx)
    ct, cs = f"${lay.c_trow}{r}", f"${lay.c_nrow}{r}"
    t, n = _trim_ref("TSMIS", col, ct), _trim_ref("TSN", col, cs)
    if EXPECTED_HEADER[field_idx] == "Med Wid":
        eq = f'{_medwid_ref("TSMIS", col, ct)}={_medwid_ref("TSN", col, cs)}'
    else:
        eq = f"{t}={n}"
    show_t = f'IF({t}="","(blank)",{t})'
    show_n = f'IF({n}="","(blank)",{n})'
    st = f"${lay.c_status}{r}"
    return (f'=IF({st}="TSMIS only",{t},IF({st}="TSN only",{n},IF({eq},{t},'
            f'{show_t}&"{_DIFF_MARK}"&{show_n})))')


def _field_value(rt, rn, off, f):
    """What _field_formula DISPLAYS, computed in Python — the values
    workbook's cell for EXPECTED_HEADER[f]. `rt`/`rn` are the raw input rows
    (None when that side lacks the key); returns "" for an empty result."""
    if rt is None:                       # TSN-only row: that side's own value
        return _xl_trim(rn[f + off])
    if rn is None:                       # TSMIS-only row
        return _xl_trim(rt[f + off])
    va, vb = _xl_trim(rt[f + off]), _xl_trim(rn[f + off])
    ca, cb = va, vb
    if EXPECTED_HEADER[f] == "Med Wid":
        ca, cb = _medwid_norm(va), _medwid_norm(vb)
    if ca == cb:
        return va
    return f"{va or '(blank)'}{_DIFF_MARK}{vb or '(blank)'}"


# The workbook is written in openpyxl's STREAMING (write_only) mode: the
# consolidated comparison carries ~2 million formula cells, which the normal
# in-memory mode cannot save in reasonable time or RAM (the consolidators use
# the same mode for the same reason). Streaming rules: sheets are created in
# display order, freeze/widths/filter/CF are set before rows are appended,
# and styled cells are WriteOnlyCells.

def _styled(ws, value, font, fill=None, align=None):
    c = WriteOnlyCell(ws, value=value)
    c.font = font
    if fill:
        c.fill = fill
    if align:
        c.alignment = align
    return c


def _header_row(ws, values):
    font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill = PatternFill("solid", start_color=_DARK)
    align = Alignment(horizontal="center", vertical="bottom", wrap_text=True)
    return [_styled(ws, v, font, fill, align) for v in values]


def _write_data_sheet(wb, name, rows, lay, events, cmp_rows, helper_keys=None):
    """One input copied to its sheet, with a leading 'Comparison row' LINK
    back to where each row appears on the Comparison sheet (column A — so a
    reviewer who jumped here from a row link has a one-click way back, right
    where they land) and the live 'Key (helper)' column at the end. The link
    target is a literal (cmp_rows[i]), consistent with the workbook's
    design: the comparison's row universe is fixed at build time, only the
    VALUES are live."""
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = _TAB[name]
    body_font = Font(name="Arial", size=10)
    link_font = _link_font()

    # Keep the back-link + Route + Location in view while scrolling fields.
    ws.freeze_panes = "D2" if lay.has_route else "C2"
    ws.auto_filter.ref = f"A1:{lay.data_last_col}{len(rows) + 1}"
    ws.column_dimensions[lay.key_col].width = 14
    ws.column_dimensions[lay.back_col].width = 13
    if lay.has_route:
        ws.column_dimensions[lay.route_data_col].width = 8
    ws.column_dimensions[lay.data_col(0)].width = 12          # Location
    ws.column_dimensions[lay.data_col(1)].width = 11          # MI
    ws.column_dimensions[lay.data_col(28)].width = 26         # Description
    ws.column_dimensions[lay.data_col(29)].width = 11         # Date of Rec

    ws.append(_header_row(ws, ["Comparison row"] + lay.data_header + ["Key (helper)"]))
    for r, row in enumerate(rows, start=2):
        u = cmp_rows[r - 2]
        # Whole-row target: the jump selects the entire Comparison row
        # (temporary highlight until the next click) WITHOUT scrolling
        # right, same as the forward row links.
        cells = [_styled(ws, f'=HYPERLINK("#Comparison!{u}:{u}",{u})', link_font)]
        cells += [_styled(ws, v, body_font) for v in row]
        # values workbook: the key is a literal string instead of the formula
        cells.append(_styled(ws, helper_keys[r - 2] if helper_keys is not None
                             else lay.helper_formula(r), body_font))
        ws.append(cells)
        if (r - 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  {name} sheet: {r - 1:,} rows…")
            if events.is_cancelled():
                return None
    return ws


def _write_comparison(wb, union, lay, events, vals=None):
    """The big sheet. `vals` None = live formulas (the default workbook);
    else the values model (compare() builds it) and every cell is the
    computed RESULT — identical text, no formulas, links kept."""
    ws = wb.create_sheet("Comparison")
    ws.sheet_properties.tabColor = _TAB["Comparison"]
    body_font = Font(name="Arial", size=10)

    last = len(union) + 1
    ws.row_dimensions[1].height = 45.75
    ws.freeze_panes = f"{lay.field_col(1)}2"
    ws.auto_filter.ref = f"A1:{lay.last_field_col}{last}"
    if lay.has_route:
        ws.column_dimensions["A"].width = 8
    ws.column_dimensions[lay.c_loc].width = 12
    ws.column_dimensions[lay.c_occ].width = 4
    ws.column_dimensions[lay.c_trow].width = 7
    ws.column_dimensions[lay.c_status].width = 11
    ws.column_dimensions[lay.c_diffs].width = 6
    ws.column_dimensions[lay.field_col(1)].width = 12
    ws.column_dimensions[lay.field_col(28)].width = 30        # Description
    ws.column_dimensions[lay.field_col(29)].width = 12        # Date of Rec

    # Conditional formatting (same look as the sample, diff detection keyed on
    # the ≠ marker): red diff cells, yellow TSMIS-only rows, blue TSN-only
    # rows, bold red Diffs count when > 0.
    f1 = lay.field_col(1)
    full = f"A2:{lay.last_field_col}{last}"
    fields = f"{f1}2:{lay.last_field_col}{last}"
    ws.conditional_formatting.add(fields, FormulaRule(
        formula=[f'ISNUMBER(SEARCH("{_DIFF_MARK}",{f1}2))'],
        fill=PatternFill(bgColor="FFC7CE"),
        font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(full, FormulaRule(
        formula=[f'${lay.c_status}2="TSMIS only"'], fill=PatternFill(bgColor="FFE699")))
    ws.conditional_formatting.add(full, FormulaRule(
        formula=[f'${lay.c_status}2="TSN only"'], fill=PatternFill(bgColor="BDD7EE")))
    ws.conditional_formatting.add(f"{lay.c_diffs}2:{lay.c_diffs}{last}", CellIsRule(
        operator="greaterThan", formula=["0"],
        font=Font(color="C00000", bold=True)))

    link_font = _link_font()
    link_cols = {3, 4} if lay.has_route else {2, 3}   # trow / nrow positions
    ws.append(_header_row(ws, lay.id_headers + EXPECTED_HEADER[1:]))
    for i, (route, loc, occ) in enumerate(union):
        r = i + 2
        if vals is None:
            key = lay.key_expr(r)
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link("TSMIS", key, lay),
                _row_link("TSN", key, lay),
                f'=IF(AND({lay.c_trow}{r}<>"",{lay.c_nrow}{r}<>""),"Both",'
                f'IF({lay.c_trow}{r}<>"","TSMIS only","TSN only"))',
                # Diffs counts cells carrying the ≠ marker (matched cells show
                # the value, so "non-blank" no longer means "different").
                f'=IF({lay.c_status}{r}<>"Both","",SUMPRODUCT(--ISNUMBER(SEARCH('
                f'"{_DIFF_MARK}",{lay.field_col(1)}{r}:{lay.last_field_col}{r}))))',
            ]
            row += [_field_formula(lay, r, f)
                    for f in range(1, len(EXPECTED_HEADER))]
        else:
            k = (route, loc, occ)
            rt, rn = vals["by_t"].get(k), vals["by_n"].get(k)
            tr, nr = vals["row_t"].get(k), vals["row_n"].get(k)
            status = ("Both" if rt is not None and rn is not None
                      else "TSMIS only" if rt is not None else "TSN only")
            fields, ndiff = [], 0
            for f in range(1, len(EXPECTED_HEADER)):
                v = _field_value(rt, rn, vals["off"], f)
                if _DIFF_MARK in v:
                    ndiff += 1
                fields.append(v if v != "" else None)
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link_value("TSMIS", tr, lay) if tr else None,
                _row_link_value("TSN", nr, lay) if nr else None,
                status,
                ndiff if status == "Both" else None,
            ] + fields
        ws.append([_styled(ws, v, link_font if j in link_cols else body_font)
                   for j, v in enumerate(row)])
        if (i + 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  Comparison sheet: {i + 1:,} of {len(union):,} rows…")
            if events.is_cancelled():
                return None
    return ws


def _write_spot_check(wb, lay, n_union, default_row, default_key,
                      manual_calc=False):
    """'Spot Check': one location under a microscope, for reviewers who doubt
    the formulas. Type any Comparison row number (or find one by route +
    location) and the sheet lays that row out field by field — the RAW values
    from both data sheets next to an INDEPENDENTLY recomputed verdict (same
    TRIM / Med Wid rules, computed straight from the data sheets, never
    reading the Comparison sheet's answer) and an Agree? column that flags
    any disagreement with what the Comparison sheet displays. On one-sided
    rows the verdict column carries the status itself (tinted) plus a loud
    callout line — the Status cell alone is easy to miss — and Agree? still
    verifies the displayed value against that system's data sheet. Opens
    pre-set to `default_row`, the first matched row with differences."""
    ws = wb.create_sheet("Spot Check")
    ws.sheet_properties.tabColor = _TAB["Spot Check"]
    ws.sheet_view.showGridLines = False

    title_font = Font(name="Arial", size=14, bold=True, color=_DARK)
    note_font = Font(name="Arial", size=10, color="595959")
    banner_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    banner_fill = PatternFill("solid", start_color=_DARK)
    body_font = Font(name="Arial", size=10)
    bold_font = Font(name="Arial", size=10, bold=True)
    alert_font = Font(name="Arial", size=11, bold=True, color="C00000")
    input_font = Font(name="Arial", size=11, bold=True)
    input_fill = PatternFill("solid", start_color="FFF2CC")
    link_font = _link_font()
    center = Alignment(horizontal="center")
    right = Alignment(horizontal="right")

    last = n_union + 1
    inp = "$C$6"                                   # the row-number input cell
    trow_cell, nrow_cell = "$C$12", "$F$12"        # matched data-sheet rows
    status = "$C$11"                               # the row's status cell
    F_FIRST = 16                                   # first field row
    F_LAST = F_FIRST + N_FIELDS - 1

    for col, w in (("A", 2), ("B", 19), ("C", 24), ("D", 24), ("E", 17),
                   ("F", 30), ("G", 9), ("H", 16), ("I", 16), ("J", 16)):
        ws.column_dimensions[col].width = w
    # Verdict / agreement colors. One-sided verdicts tint like the
    # Comparison sheet's yellow/blue rows so the situation is unmissable.
    ws.conditional_formatting.add(f"E{F_FIRST}:E{F_LAST}", CellIsRule(
        operator="equal", formula=['"DIFFERENT"'],
        font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(f"E{F_FIRST}:E{F_LAST}", CellIsRule(
        operator="equal", formula=['"TSMIS only"'],
        fill=PatternFill(bgColor="FFE699")))
    ws.conditional_formatting.add(f"E{F_FIRST}:E{F_LAST}", CellIsRule(
        operator="equal", formula=['"TSN only"'],
        fill=PatternFill(bgColor="BDD7EE")))
    ws.conditional_formatting.add(f"G{F_FIRST}:G{F_LAST}", CellIsRule(
        operator="equal", formula=['"CHECK"'],
        fill=PatternFill(bgColor="FFC7CE"), font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(f"G{F_FIRST}:G{F_LAST}", CellIsRule(
        operator="equal", formula=['"OK"'], font=Font(color="2E7D32", bold=True)))

    grid = {}

    def put(rc, value, font=body_font, fill=None, align=None, fmt=None):
        grid[rc] = (value, font, fill, align, fmt)

    def banner(row, text):
        put((row, 2), text, banner_font, banner_fill)
        for c in range(3, 11):                     # extend the band to col J
            put((row, c), "", banner_font, banner_fill)

    # --- intro + inputs --------------------------------------------------
    put((2, 2), "Spot Check — audit any single location", title_font)
    put((3, 2), "Every value below recomputes for the row you pick. The "
                "'Independent verdict' column re-compares the two data sheets "
                "directly (TRIM + the Med Wid rule) WITHOUT reading the "
                "Comparison sheet — Agree? = OK means both computations "
                "reached the same answer.", note_font)
    put((4, 2), f"In difference cells the order is always:   "
                f"TSMIS value{_DIFF_MARK}TSN value   (TSMIS first, TSN second).",
        bold_font)
    if manual_calc:
        put((5, 2), "▶ PRESS F9 AFTER EVERY CHANGE — this workbook calculates "
                    "manually, so nothing updates until you do.", alert_font)
    put((6, 2), f"Comparison row # to check (2–{last}):", bold_font)
    put((6, 3), default_row, input_font, input_fill, center)
    put((6, 4), "← type a row number" + (", then press F9" if manual_calc
                                         else " (updates instantly)"), note_font)
    d_route, d_loc, d_occ = default_key
    if lay.has_route:
        put((7, 2), "…or find one:", note_font)
        put((7, 3), "Route:", bold_font, None, right)
        put((7, 4), d_route, body_font, input_fill, center, "@")
        put((7, 5), "Location:", bold_font, None, right)
        put((7, 6), d_loc, body_font, input_fill, center, "@")
        put((7, 7), "Occ #:", bold_font, None, right)
        put((7, 8), d_occ, body_font, input_fill, center)
        find = (f"SUMPRODUCT((Comparison!$A$2:$A${last}=$D$7)"
                f"*(Comparison!${lay.c_loc}$2:${lay.c_loc}${last}=$F$7)"
                f"*(Comparison!${lay.c_occ}$2:${lay.c_occ}${last}=$H$7)"
                f"*ROW(Comparison!$A$2:$A${last}))")
        put((7, 9), "→ Comparison row:", bold_font, None, right)
        put((7, 10), f'=IF({find}=0,"not found",{find})', bold_font, None, center)
    else:
        put((7, 2), "…or find one:", note_font)
        put((7, 3), "Location:", bold_font, None, right)
        put((7, 4), d_loc, body_font, input_fill, center, "@")
        put((7, 5), "Occ #:", bold_font, None, right)
        put((7, 6), d_occ, body_font, input_fill, center)
        find = (f"SUMPRODUCT((Comparison!$A$2:$A${last}=$D$7)"
                f"*(Comparison!$B$2:$B${last}=$F$7)"
                f"*ROW(Comparison!$A$2:$A${last}))")
        put((7, 7), "→ Comparison row:", bold_font, None, right)
        put((7, 8), f'=IF({find}=0,"not found",{find})', bold_font, None, center)

    # --- what the Comparison sheet says ----------------------------------
    def cmp_idx(col):
        return f"INDEX(Comparison!${col}:${col},{inp})"

    banner(9, "WHAT THE COMPARISON SHEET SHOWS FOR THAT ROW")
    if lay.has_route:
        put((10, 2), "Route:", bold_font)
        put((10, 3), f'=IFERROR({cmp_idx(lay.c_route)},"")', body_font)
    put((10, 5), "Location:", bold_font)
    put((10, 6), f'=IFERROR({cmp_idx(lay.c_loc)},"")', body_font)
    put((10, 8), "Occurrence #:", bold_font)
    put((10, 9), f'=IFERROR({cmp_idx(lay.c_occ)},"")', body_font)
    put((11, 2), "Status:", bold_font)
    put((11, 3), f'=IFERROR({cmp_idx(lay.c_status)},"")', bold_font)
    put((11, 5), "Diffs counted:", bold_font)
    put((11, 6), f'=IFERROR({cmp_idx(lay.c_diffs)},"")', bold_font)
    put((12, 2), "TSMIS sheet row:", bold_font)
    put((12, 3), f'=IFERROR(IF({cmp_idx(lay.c_trow)}="","",'
                 f'HYPERLINK("#TSMIS!"&{cmp_idx(lay.c_trow)}&'
                 f'":"&{cmp_idx(lay.c_trow)},'
                 f'{cmp_idx(lay.c_trow)})),"")', link_font)
    put((12, 5), "TSN sheet row:", bold_font)
    put((12, 6), f'=IFERROR(IF({cmp_idx(lay.c_nrow)}="","",'
                 f'HYPERLINK("#TSN!"&{cmp_idx(lay.c_nrow)}&'
                 f'":"&{cmp_idx(lay.c_nrow)},'
                 f'{cmp_idx(lay.c_nrow)})),"")', link_font)
    # Loud one-sided callout: the Status cell alone is easy to miss.
    put((13, 2), f'=IF({status}="TSMIS only","⚠ THIS LOCATION EXISTS ONLY IN '
                 f'TSMIS — there is no TSN row to compare; TSN values below '
                 f'are blank.",IF({status}="TSN only","⚠ THIS LOCATION EXISTS '
                 f'ONLY IN TSN — there is no TSMIS row to compare; TSMIS '
                 f'values below are blank.",""))', alert_font)

    # --- field-by-field ---------------------------------------------------
    banner(15, "FIELD BY FIELD — RECOMPUTED FROM THE DATA SHEETS "
               "(independent of the Comparison sheet)")
    headers = ["Field", "TSMIS value (as stored)", "TSN value (as stored)",
               "Independent verdict", f"Comparison sheet shows "
               f"(TSMIS{_DIFF_MARK}TSN)", "Agree?",
               "TSMIS Med-Wid normalized", "TSN Med-Wid normalized"]
    for j, h in enumerate(headers):
        put((F_FIRST - 1, 2 + j), h,
            Font(name="Arial", size=10, bold=True, color="FFFFFF"),
            banner_fill, Alignment(horizontal="center", wrap_text=True))

    def raw(side, col, row_ref):
        idx = f"INDEX({side}!{col}:{col},{row_ref})"
        return (f'=IF({row_ref}="","",IFERROR(IF(ISBLANK({idx}),"",{idx}),""))')

    for f in range(1, len(EXPECTED_HEADER)):
        r = F_FIRST + f - 1
        col = lay.data_col(f)
        fcol = lay.field_col(f)
        is_date = EXPECTED_HEADER[f] in ("Date of Rec", "Sig Chg. Date")
        fmt = "mm/dd/yyyy" if is_date else None
        trim_t = _trim_ref("TSMIS", col, trow_cell)
        trim_n = _trim_ref("TSN", col, nrow_cell)
        if EXPECTED_HEADER[f] == "Med Wid":
            eq = (f'{_medwid_ref("TSMIS", col, trow_cell)}='
                  f'{_medwid_ref("TSN", col, nrow_cell)}')
            put((r, 8), f'=IF({trow_cell}="","",'
                        f'{_medwid_ref("TSMIS", col, trow_cell)})', body_font,
                None, center)
            put((r, 9), f'=IF({nrow_cell}="","",'
                        f'{_medwid_ref("TSN", col, nrow_cell)})', body_font,
                None, center)
        else:
            eq = f"{trim_t}={trim_n}"
        put((r, 2), EXPECTED_HEADER[f], bold_font)
        put((r, 3), raw("TSMIS", col, trow_cell), body_font, None, None, fmt)
        put((r, 4), raw("TSN", col, nrow_cell), body_font, None, None, fmt)
        # One-sided rows: the verdict carries the status itself (tinted via
        # CF) so the situation shows in every field row, not just up top.
        put((r, 5), f'=IF({status}="","",IF({status}<>"Both",{status},'
                    f'IF({eq},"match","DIFFERENT")))', body_font, None, center)
        put((r, 6), f'=IFERROR(INDEX(Comparison!{fcol}:{fcol},{inp}),"")',
            body_font)
        # Agree?: matched rows — recomputed verdict vs the ≠ marker;
        # one-sided rows — the displayed value must equal that system's own
        # (trimmed) value, so the column stays meaningful there too.
        put((r, 7), f'=IF({status}="","",IF({status}="Both",'
                    f'IF((E{r}="DIFFERENT")=ISNUMBER(SEARCH("{_DIFF_MARK}",'
                    f'F{r})),"OK","CHECK"),IF({status}="TSMIS only",'
                    f'IF({trim_t}=F{r},"OK","CHECK"),'
                    f'IF({trim_n}=F{r},"OK","CHECK"))))', body_font, None, center)

    put((F_LAST + 2, 2),
        "• On rows that exist in only one system the verdict column shows "
        "'TSMIS only' / 'TSN only' on every field; Agree? then verifies the "
        "displayed value against that system's data sheet.", note_font)
    put((F_LAST + 3, 2),
        "• The blue row numbers jump to the source row on the data sheets "
        "and select the whole row so it stands out — it un-highlights when "
        "you click elsewhere. Each data-sheet row links back to its "
        "Comparison row. Values are shown exactly as stored (before TRIM).",
        note_font)

    # Emit the sparse grid (append-only streaming sheet).
    n_rows = max(r for r, _c in grid)
    n_cols = max(c for _r, c in grid)
    for r in range(1, n_rows + 1):
        cells = []
        for c in range(1, n_cols + 1):
            if (r, c) in grid:
                value, font, fill, align, fmt = grid[(r, c)]
                cell = _styled(ws, value, font, fill, align)
                if fmt:
                    cell.number_format = fmt
                cells.append(cell)
            else:
                cells.append(None)
        ws.append(cells)
    return ws


def _write_only_sheet(wb, side, keys, lay, events, vals=None):
    """'Only in TSMIS' / 'Only in TSN': every one-sided union row, in union
    order, with the full field data pulled LIVE from that system's data sheet
    (same MATCH-on-helper-key + INDEX pattern as the Comparison sheet, so the
    tab recalculates with edits). Consolidated mode adds a "Missing from
    <other>" column — "entire route" (tinted: the other system lacks the whole
    route) vs "this location only" — so wholly-missing routes can't be
    overlooked. `side` is "TSMIS" or "TSN"; `keys` its one-sided union keys."""
    other = "TSN" if side == "TSMIS" else "TSMIS"
    name = f"Only in {side}"
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = _TAB[name]
    body_font = Font(name="Arial", size=10)

    id_headers = ((["Route"] if lay.has_route else [])
                  + ["Location", "#", f"{side} Row"]
                  + ([f"Missing from {other}"] if lay.has_route else []))
    n_id = len(id_headers)
    fcol = lambda f: get_column_letter(n_id + f)      # comparison-field -> letter
    last_field = fcol(N_FIELDS)
    last = len(keys) + 1
    c = [get_column_letter(i + 1) for i in range(n_id)]
    if lay.has_route:
        c_route, c_loc, c_occ, c_row, c_why = c
    else:
        c_route = c_why = None
        c_loc, c_occ, c_row = c

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = f"{fcol(1)}2"
    ws.auto_filter.ref = f"A1:{last_field}{last}"
    if lay.has_route:
        ws.column_dimensions[c_route].width = 8
        ws.column_dimensions[c_why].width = 18
    ws.column_dimensions[c_loc].width = 12
    ws.column_dimensions[c_occ].width = 4
    ws.column_dimensions[c_row].width = 9
    ws.column_dimensions[fcol(1)].width = 12
    ws.column_dimensions[fcol(28)].width = 30         # Description
    ws.column_dimensions[fcol(29)].width = 12         # Date of Rec
    if lay.has_route:
        # Whole-route gaps stand out; single-location gaps stay plain. Colors
        # mirror the Comparison sheet's TSMIS-only / TSN-only row tints.
        tint = "FFE699" if side == "TSMIS" else "BDD7EE"
        ws.conditional_formatting.add(f"A2:{last_field}{last}", FormulaRule(
            formula=[f'${c_why}2="entire route"'], fill=PatternFill(bgColor=tint)))

    link_font = _link_font()
    link_col = 3 if lay.has_route else 2              # the "<side> Row" position
    if vals is not None:
        own_rows = vals["row_t"] if side == "TSMIS" else vals["row_n"]
        own_by = vals["by_t"] if side == "TSMIS" else vals["by_n"]
        other_routes = vals["routes_n"] if side == "TSMIS" else vals["routes_t"]
    ws.append(_header_row(ws, id_headers + EXPECTED_HEADER[1:]))
    for i, (route, loc, occ) in enumerate(keys):
        r = i + 2
        if vals is None:
            if lay.has_route:
                key = f'${c_route}{r}&"|"&${c_loc}{r}&"|"&${c_occ}{r}'
            else:
                key = f'${c_loc}{r}&"|"&${c_occ}{r}'
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link(side, key, lay),
            ]
            if lay.has_route:
                rc = lay.route_data_col      # Route on the data sheets (B)
                row.append(f'=IF(COUNTIF({other}!${rc}:${rc},$A{r})=0,'
                           f'"entire route","this location only")')
            rr = f"${c_row}{r}"
            row += [f'=IF({rr}="","",{_trim_ref(side, lay.data_col(f), rr)})'
                    for f in range(1, len(EXPECTED_HEADER))]
        else:
            k = (route, loc, occ)
            own = own_by[k]
            row = ([route] if lay.has_route else []) + [
                loc, occ,
                _row_link_value(side, own_rows[k], lay),
            ]
            if lay.has_route:
                row.append("entire route" if route not in other_routes
                           else "this location only")
            row += [(_xl_trim(own[f + vals["off"]]) or None)
                    for f in range(1, len(EXPECTED_HEADER))]
        ws.append([_styled(ws, v, link_font if j == link_col else body_font)
                   for j, v in enumerate(row)])
        if (i + 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  {name} sheet: {i + 1:,} of {len(keys):,} rows…")
            if events.is_cancelled():
                return None
    return ws


def _route_coverage(keys_t, keys_n):
    """Route lists, ordered as the union orders them: TSMIS's route order,
    then TSN-only routes in TSN order. Returns (all_routes, both, t_only,
    n_only) — each a list of route ids."""
    rt = list(dict.fromkeys(k[0] for k in keys_t))
    rn = list(dict.fromkeys(k[0] for k in keys_n))
    set_t, set_n = set(rt), set(rn)
    all_routes = rt + [r for r in rn if r not in set_t]
    return (all_routes,
            [r for r in all_routes if r in set_t and r in set_n],
            [r for r in rt if r not in set_n],
            [r for r in rn if r not in set_t])


def _write_routes(wb, all_routes, lay, vals=None):
    """Consolidated mode only: one row per route with LIVE coverage stats —
    which system has it, how many rows each side carries, and how much of it
    differs. The route ids are the row universe (literals, like the
    Comparison sheet's keys); every count is a formula."""
    ws = wb.create_sheet("Routes")
    ws.sheet_properties.tabColor = _TAB["Routes"]
    body_font = Font(name="Arial", size=10)
    last = len(all_routes) + 1
    st, df = lay.c_status, lay.c_diffs

    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:H{last}"
    for col, w in (("A", 8), ("B", 12), ("C", 12), ("D", 12),
                   ("E", 16), ("F", 16), ("G", 18), ("H", 14)):
        ws.column_dimensions[col].width = w
    ws.row_dimensions[1].height = 30
    # Status colors match the Comparison sheet; red counts where differences exist.
    ws.conditional_formatting.add(f"A2:H{last}", FormulaRule(
        formula=['$B2="TSMIS only"'], fill=PatternFill(bgColor="FFE699")))
    ws.conditional_formatting.add(f"A2:H{last}", FormulaRule(
        formula=['$B2="TSN only"'], fill=PatternFill(bgColor="BDD7EE")))
    ws.conditional_formatting.add(f"G2:H{last}", CellIsRule(
        operator="greaterThan", formula=["0"],
        font=Font(color="C00000", bold=True)))

    ws.append(_header_row(ws, [
        "Route", "Status", "TSMIS rows", "TSN rows", "Locations compared",
        "Matched locations", "Locations w/ differences", "Differing cells"]))
    rc = lay.route_data_col                  # Route on the data sheets (B)
    for i, route in enumerate(all_routes):
        r = i + 2
        if vals is None:
            cells = (
                route,
                f'=IF(AND(C{r}>0,D{r}>0),"Both",IF(C{r}>0,"TSMIS only","TSN only"))',
                f'=COUNTIF(TSMIS!${rc}:${rc},$A{r})',
                f'=COUNTIF(TSN!${rc}:${rc},$A{r})',
                f'=COUNTIF(Comparison!$A:$A,$A{r})',
                f'=COUNTIFS(Comparison!$A:$A,$A{r},Comparison!${st}:${st},"Both")',
                f'=COUNTIFS(Comparison!$A:$A,$A{r},Comparison!${st}:${st},"Both",'
                f'Comparison!${df}:${df},">0")',
                f'=SUMIF(Comparison!$A:$A,$A{r},Comparison!${df}:${df})',
            )
        else:
            rs = vals["counts"]["route"][route]
            cells = (
                route,
                ("Both" if rs["t_rows"] and rs["n_rows"]
                 else "TSMIS only" if rs["t_rows"] else "TSN only"),
                rs["t_rows"], rs["n_rows"], rs["locs"], rs["matched"],
                rs["withdiffs"], rs["cells"],
            )
        ws.append([_styled(ws, v, body_font) for v in cells])
    return ws


def _write_summary(wb, tsmis_name, tsn_name, n_union, lay, vals=None):
    """`vals` None = live-formula stats; else the values model and every
    stat is its literal number. The SELF-CHECK rows stay LIVE in both
    flavors — in the values workbook they recount the literal sheets, so
    they still prove the written numbers are internally consistent."""
    ws = wb.create_sheet("Summary")
    ws.sheet_properties.tabColor = _TAB["Summary"]
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["B"].width = 46
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 20

    title_font = Font(name="Arial", size=14, bold=True, color=_DARK)
    note_font = Font(name="Arial", size=10, color="595959")
    banner_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    banner_fill = PatternFill("solid", start_color=_DARK)
    body_font = Font(name="Arial", size=10)
    bold_font = Font(name="Arial", size=10, bold=True)
    center = Alignment(horizontal="center")
    last = n_union + 1                              # Comparison data end row
    loc_col = lay.data_col(0)              # Location on the data sheets
    st, df = lay.c_status, lay.c_diffs

    # Streaming sheets are append-only: build a sparse (row, col) grid first,
    # emit it row by row at the end.
    grid = {}
    row = [1]                                       # 1-slot mutable cursor

    def put(col, value, font=body_font, fill=None, align=None):
        grid[(row[0], col)] = (value, font, fill, align)

    def line(*cells, advance=1):
        for col, value, *style in cells:
            put(col, value, *style)
        row[0] += advance

    def banner(text):
        line((2, text, banner_font, banner_fill))

    def stat(label, formula, value=None):
        line((2, label),
             (3, formula if vals is None else value, bold_font, None, center))

    c = None if vals is None else vals["counts"]
    scope = ("Consolidated (all routes)" if lay.has_route else "Per-route") \
        + ("" if vals is None else " — VALUES copy")
    row[0] = 2
    line((2, f"TSMIS vs TSN — Highway Log — Discrepancy Report ({scope})", title_font))
    if lay.has_route and vals is None:
        # The big formulas workbook ships UNCALCULATED (manual mode): every
        # cell shows blank/0 until F9. Without a loud banner that reads as
        # broken data. (The values copy calculates nothing — no banner.)
        line((2, "▶ PRESS F9 TO CALCULATE — this workbook opens uncalculated "
                 "(blank/0 cells). The first F9 takes a few minutes; let it "
                 "finish, then save.",
              Font(name="Arial", size=11, bold=True, color="C00000")))
    line((2, "Cell-by-cell comparison keyed on "
             + ("Route + Location" if lay.has_route else "Location")
             + " (+ occurrence for duplicates). "
             + ("All formulas are live: edits on the TSMIS / TSN sheets "
                "recalculate everything." if vals is None else
                "This copy holds plain VALUES — it opens instantly and "
                "nothing needs calculating, but edits do NOT recalculate "
                "(the live-formulas copy does that). The Spot Check sheet "
                "and the SELF-CHECK rows below stay live."), note_font))
    line((2, f"TSMIS: {tsmis_name}      TSN: {tsn_name}      "
             f"created {date.today().isoformat()}", note_font), advance=2)

    banner("ROW COUNTS")
    stat("TSMIS data rows", f"=COUNTA(TSMIS!{loc_col}:{loc_col})-1",
         None if vals is None else vals["n_t"])
    stat("TSN data rows", f"=COUNTA(TSN!{loc_col}:{loc_col})-1",
         None if vals is None else vals["n_n"])
    stat("Union of locations compared",
         f"=COUNTA(Comparison!{lay.c_loc}:{lay.c_loc})-1", n_union)
    banner("MATCH STATUS")
    stat("Locations in both systems", f'=COUNTIF(Comparison!{st}:{st},"Both")',
         c and c["both"])
    stat("In TSMIS only (missing from TSN) — listed on the 'Only in TSMIS' sheet",
         f'=COUNTIF(Comparison!{st}:{st},"TSMIS only")', c and c["t_only"])
    stat("In TSN only (missing from TSMIS) — listed on the 'Only in TSN' sheet",
         f'=COUNTIF(Comparison!{st}:{st},"TSN only")', c and c["n_only"])
    if lay.has_route:
        banner("ROUTE COVERAGE (see the Routes sheet for the per-route breakdown)")
        stat("Routes covered by both systems", '=COUNTIF(Routes!B:B,"Both")',
             None if vals is None else vals["r_both"])
        stat("Routes only in TSMIS (missing from TSN)",
             '=COUNTIF(Routes!B:B,"TSMIS only")',
             None if vals is None else vals["r_t_only"])
        stat("Routes only in TSN (missing from TSMIS)",
             '=COUNTIF(Routes!B:B,"TSN only")',
             None if vals is None else vals["r_n_only"])
    banner("FIELD-LEVEL DISCREPANCIES (matched rows)")
    stat("Matched rows with ≥ 1 field difference",
         f'=COUNTIFS(Comparison!{st}2:{st}{last},"Both",'
         f'Comparison!{df}2:{df}{last},">0")', c and c["diff_rows"])
    stat("Matched rows fully identical",
         f'=COUNTIFS(Comparison!{st}2:{st}{last},"Both",'
         f'Comparison!{df}2:{df}{last},0)', c and c["identical"])
    stat("Total differing cells", f"=SUM(Comparison!{df}2:{df}{last})",
         c and c["diff_cells"])
    row[0] += 1

    banner("DIFFERENCES BY FIELD")
    line((2, "Field", bold_font), (3, "Comparison col", bold_font),
         (4, "# of cells differing", bold_font))
    f_start = row[0]
    for f in range(1, len(EXPECTED_HEADER)):
        col = lay.field_col(f)
        line((2, EXPECTED_HEADER[f]), (3, col),
             (4, f'=COUNTIF(Comparison!{col}2:{col}{last},"*{_DIFF_MARK.strip()}*")'
              if vals is None else c["field_diffs"][f],
              bold_font, None, center))
    f_end = row[0] - 1
    row[0] += 1

    # Live cross-checks: each headline number recomputed a second, independent
    # way. Any row reading CHECK means a formula no longer points where it
    # should (the classic cause: rows inserted/deleted on a data sheet).
    banner("SELF-CHECK (every row should read OK after calculation)")
    only_loc = "B" if lay.has_route else "A"          # Location col on Only-in tabs

    def check(label, cond):
        line((2, label), (3, f'=IF({cond},"OK","CHECK")', bold_font, None, center))

    union_count = f"COUNTA(Comparison!{lay.c_loc}:{lay.c_loc})-1"
    check("Every Comparison row has a status (Both + TSMIS only + TSN only)",
          f'COUNTIF(Comparison!{st}:{st},"Both")'
          f'+COUNTIF(Comparison!{st}:{st},"TSMIS only")'
          f'+COUNTIF(Comparison!{st}:{st},"TSN only")={union_count}')
    check("Every row with TSMIS data found its TSMIS sheet row",
          f'COUNT(Comparison!{lay.c_trow}:{lay.c_trow})='
          f'COUNTIF(Comparison!{st}:{st},"Both")'
          f'+COUNTIF(Comparison!{st}:{st},"TSMIS only")')
    check("Every row with TSN data found its TSN sheet row",
          f'COUNT(Comparison!{lay.c_nrow}:{lay.c_nrow})='
          f'COUNTIF(Comparison!{st}:{st},"Both")'
          f'+COUNTIF(Comparison!{st}:{st},"TSN only")')
    check("'Only in TSMIS' sheet rows = TSMIS-only rows in the Comparison",
          f"COUNTA('Only in TSMIS'!{only_loc}:{only_loc})-1="
          f'COUNTIF(Comparison!{st}:{st},"TSMIS only")')
    check("'Only in TSN' sheet rows = TSN-only rows in the Comparison",
          f"COUNTA('Only in TSN'!{only_loc}:{only_loc})-1="
          f'COUNTIF(Comparison!{st}:{st},"TSN only")')
    check("Per-field difference counts add up to the total differing cells",
          f'SUM(D{f_start}:D{f_end})=SUM(Comparison!{df}2:{df}{last})')
    if lay.has_route:
        check("Routes sheet TSMIS row counts add up to the TSMIS sheet",
              f"SUM(Routes!C:C)=COUNTA(TSMIS!{loc_col}:{loc_col})-1")
        check("Routes sheet TSN row counts add up to the TSN sheet",
              f"SUM(Routes!D:D)=COUNTA(TSN!{loc_col}:{loc_col})-1")
        check("Routes sheet 'Locations compared' adds up to the Comparison",
              f"SUM(Routes!E:E)={union_count}")
    row[0] += 1

    banner("HOW TO READ / NOTES")
    notes = [
        "• Comparison sheet: matching values are shown in plain text; a red "
        f"cell shows  TSMIS value{_DIFF_MARK}TSN value  where the two systems "
        "disagree for that Location and field.",
        '• "(blank)" means the cell is empty in that system. Filter the Diffs '
        "column (>0) to isolate rows needing review.",
        "• Yellow rows exist only in TSMIS; blue rows exist only in TSN "
        "(mostly TSN segment splits and TSMIS realignment markers). Their "
        "field cells show that system's own values.",
        "• The 'Only in TSMIS' and 'Only in TSN' sheets repeat every "
        "one-sided row in one place — including the rows of routes the other "
        "system doesn't carry at all"
        + (" (flagged 'entire route' and tinted; filter the 'Missing from …' "
           "column to separate whole-route gaps from single locations)"
           if lay.has_route else "")
        + ". The Comparison sheet still contains the same rows in document "
        "order.",
        "• Rows pair on " + ("Route plus " if lay.has_route else "")
        + "Location plus occurrence number (a postmile listed twice pairs "
        "first-with-first, second-with-second).",
        "• Leading/trailing spaces are ignored (TRIM) — the TSMIS export pads "
        "Description with trailing blanks.",
        f'• Lookups use the "Key (helper)" column ({lay.key_col}) on each '
        'data sheet: ' + ("Route, " if lay.has_route else "")
        + 'Location & "|" & occurrence #.',
        "• Med Wid is compared after normalizing zero-padding in the numeric "
        "part (TSMIS 0Z = TSN 00Z, 6V = 06V, etc.), since the two systems "
        "format this code differently. All other fields compare exactly.",
    ]
    notes.append(
        "• Doubting a value? The blue row numbers in the 'TSMIS Row' / "
        "'TSN Row' columns are clickable — they jump to the data sheet and "
        "SELECT that whole row (it stays highlighted until you click "
        "elsewhere), and each data-sheet row links back to its Comparison "
        "row the same way. The Spot Check sheet audits any single location "
        "end to end: raw values from both systems and an independently "
        "recomputed verdict for every field.")
    if vals is not None:
        notes.append(
            "• This is the VALUES copy: every number and comparison cell is "
            "a computed result, not a formula (only the Spot Check sheet and "
            "the SELF-CHECK rows stay live). If the data changes, re-create "
            "the comparison — or use the live-formulas copy, which "
            "recalculates.")
    notes.append(
        "• SELF-CHECK recomputes the headline numbers a second, independent "
        "way; a CHECK there means the sheets no longer agree (e.g. rows were "
        "inserted or deleted on a data sheet) — re-create the report rather "
        "than trust the numbers.")
    if lay.has_route:
        notes.append(
            "• The Routes sheet lists every route either system carries — "
            "which side covers it, row counts, and how much of it differs.")
        if vals is None:
            notes.append(
                "• CALCULATION IS SET TO MANUAL (large workbook): cells show "
                "blank/0 until you press F9. The first F9 takes a few minutes — "
                "let it finish, then save to keep the results; edits afterwards "
                "only recalculate when you press F9 again. (Excel keeps the "
                "manual setting for other workbooks opened in the same session — "
                "Formulas → Calculation Options switches it back.)")
    for note in notes:
        line((2, note, note_font))

    # Emit the grid (append-only streaming sheet).
    n_rows = max(r for r, _c in grid)
    n_cols = max(c for _r, c in grid)
    for r in range(1, n_rows + 1):
        cells = []
        for c in range(1, n_cols + 1):
            if (r, c) in grid:
                value, font, fill, align = grid[(r, c)]
                cells.append(_styled(ws, value, font, fill, align))
            else:
                cells.append(None)
        ws.append(cells)


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas"):
    """Build the comparison workbook(s). Returns a ConsolidateResult (same
    contract as the consolidators, so the GUI/console drive it identically).

    `mode`: "formulas" (the live workbook — every cell recalculates),
    "values" (same sheets and look, but the bulk is plain computed RESULTS —
    opens instantly, no F9; links, conditional formatting, the Spot Check
    sheet and the SELF-CHECK rows are kept), or "both" (two files: the picked
    name for the formulas copy and '<name> (values).xlsx' next to it)."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (openpyxl).")
    confirm = confirm_overwrite or (lambda _p: True)
    tsmis_path, tsn_path, out = Path(tsmis_path), Path(tsn_path), Path(out_path)

    modes = {"formulas": ("formulas",), "values": ("values",),
             "both": ("formulas", "values")}.get(mode)
    if modes is None:
        return ConsolidateResult(status="error",
                                 message=f"Unknown comparison mode: {mode}")
    out_paths = {m: out for m in modes}
    if len(modes) > 1:                  # the values twin sits next to the pick
        out_paths["values"] = out.with_name(f"{out.stem} (values){out.suffix}")

    for p, side in ((tsmis_path, "TSMIS"), (tsn_path, "TSN")):
        if not p.is_file():
            return ConsolidateResult(
                status="error",
                message=f"The {side} file doesn't exist:\n{p}")
    for m in modes:
        if out_paths[m].exists() and not confirm(out_paths[m]):
            return ConsolidateResult(status="cancelled",
                                     message="Cancelled. Existing file kept.")

    events.on_log("=" * 60)
    events.on_log("Highway Log Comparison — TSMIS vs TSN")
    events.on_log("=" * 60)
    events.on_log(f"TSMIS: {tsmis_path.name}")
    events.on_log(f"TSN:   {tsn_path.name}")
    events.on_log("")

    try:
        rows_t, route_t = _load_input(tsmis_path)
        rows_n, route_n = _load_input(tsn_path)
    except ValueError as e:
        return ConsolidateResult(status="error", message=str(e))
    if route_t != route_n:
        per, con = ((tsn_path, tsmis_path) if route_t else (tsmis_path, tsn_path))
        return ConsolidateResult(
            status="error",
            message=(f"The two files have different shapes: {con.name} is a "
                     f"consolidated workbook (has a Route column) but "
                     f"{per.name} is per-route. Pick two per-route files or "
                     f"two consolidated files."))
    if not rows_t or not rows_n:
        return ConsolidateResult(
            status="error",
            message="One of the files has no data rows — nothing to compare.")
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")

    has_route = route_t
    lay = _Layout(has_route)
    keys_t, keys_n = _keys(rows_t, has_route), _keys(rows_n, has_route)
    union = _union_keys(keys_t, keys_n)
    counts = _count_diffs(rows_t, rows_n, keys_t, keys_n, union, has_route)
    events.on_log(f"TSMIS rows: {len(rows_t):,}   TSN rows: {len(rows_n):,}   "
                  f"union: {len(union):,} locations"
                  + (f" across {len({k[0] for k in union})} routes" if has_route else ""))
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")

    # Shared model for every output flavor (parsed/aligned/counted ONCE).
    spot_row = counts.get("first_diff_row") or 2
    all_routes = r_both = r_t_only = r_n_only = None
    if has_route:
        all_routes, r_both, r_t_only, r_n_only = _route_coverage(keys_t, keys_n)
    set_t, set_n = set(keys_t), set(keys_n)
    only_t = [k for k in union if k not in set_n]
    only_n = [k for k in union if k not in set_t]
    union_row = {k: i + 2 for i, k in enumerate(union)}   # data row -> Comparison row
    cmp_rows_t = [union_row[k] for k in keys_t]
    cmp_rows_n = [union_row[k] for k in keys_n]

    cancelled = ConsolidateResult(status="cancelled", message="Cancelled by user.")
    for m in modes:
        path = out_paths[m]
        if m == "values":
            # Everything the formulas would display, precomputed: the writers
            # emit literal results instead of formulas (links/CF/Spot Check/
            # SELF-CHECK stay live). Same _xl_trim/_medwid_norm mirror as the
            # run summary, so the two flavors can never disagree.
            vals = {
                "off": 1 if has_route else 0,
                "by_t": {k: rows_t[i] for i, k in enumerate(keys_t)},
                "by_n": {k: rows_n[i] for i, k in enumerate(keys_n)},
                "row_t": {k: i + 2 for i, k in enumerate(keys_t)},
                "row_n": {k: i + 2 for i, k in enumerate(keys_n)},
                "routes_t": {k[0] for k in keys_t},
                "routes_n": {k[0] for k in keys_n},
                "counts": counts,
                "n_t": len(rows_t), "n_n": len(rows_n),
                "r_both": len(r_both) if has_route else 0,
                "r_t_only": len(r_t_only) if has_route else 0,
                "r_n_only": len(r_n_only) if has_route else 0,
            }
            hk_t = [f"{k[0]}|{k[1]}|{k[2]}" if has_route else f"{k[1]}|{k[2]}"
                    for k in keys_t]
            hk_n = [f"{k[0]}|{k[1]}|{k[2]}" if has_route else f"{k[1]}|{k[2]}"
                    for k in keys_n]
            events.on_log(f"Writing the VALUES workbook: {path.name}")
        else:
            vals, hk_t, hk_n = None, None, None
            events.on_log(f"Writing the live-formulas workbook: {path.name}")

        # Streaming workbook (see the note above _styled): sheets are created
        # in display order; Summary first so it's the active sheet on open.
        wb = Workbook(write_only=True)
        if has_route and m == "formulas":
            # ~2M live formulas: in automatic mode Excel would recalculate
            # for minutes on open AND after every edit. Ship the workbook in
            # MANUAL calculation mode instead — it opens instantly showing
            # blanks/zeros, the user presses F9 once (the one unavoidable big
            # calc), saves, and from then on opens are instant and edits
            # don't hang. calcOnSave off so saving doesn't sneak the big calc
            # back in. (Per-route files and the VALUES copy stay automatic.)
            wb.calculation.calcMode = "manual"
            wb.calculation.calcOnSave = False
            wb.calculation.fullCalcOnLoad = False
        _write_summary(wb, tsmis_path.name, tsn_path.name, len(union), lay,
                       vals=vals)
        _write_spot_check(wb, lay, len(union), spot_row, union[spot_row - 2],
                          manual_calc=(has_route and m == "formulas"))
        if _write_comparison(wb, union, lay, events, vals=vals) is None:
            return cancelled
        if has_route:
            _write_routes(wb, all_routes, lay, vals=vals)
        # The one-sided rows again, on their own tabs (union order): the rows
        # of routes the other system lacks entirely plus the locations missing
        # from the other side within shared routes.
        if _write_only_sheet(wb, "TSMIS", only_t, lay, events, vals=vals) is None:
            return cancelled
        if _write_only_sheet(wb, "TSN", only_n, lay, events, vals=vals) is None:
            return cancelled
        if _write_data_sheet(wb, "TSMIS", rows_t, lay, events, cmp_rows_t,
                             helper_keys=hk_t) is None:
            return cancelled
        if _write_data_sheet(wb, "TSN", rows_n, lay, events, cmp_rows_n,
                             helper_keys=hk_n) is None:
            return cancelled
        events.on_log("Saving…")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            wb.save(path)
        except PermissionError:
            return ConsolidateResult(
                status="error",
                message=(f"Could not save {path.name}.\n\n"
                         "The file is probably open in Excel. Close it and try again."))

    def _route_list(label, routes):
        shown = ", ".join(routes[:15]) + (", …" if len(routes) > 15 else "")
        return f"{label} ({len(routes)}): {shown}" if routes else f"{label}: none"

    lines = [
        f"Locations in both systems:   {counts['both']:,}",
        f"In TSMIS only / in TSN only: {counts['t_only']:,} / {counts['n_only']:,} "
        "(each listed on its own 'Only in …' sheet)",
        f"Matched rows with differences: {counts['diff_rows']:,} "
        f"({counts['diff_cells']:,} differing cells); "
        f"{counts['identical']:,} fully identical",
    ]
    if has_route:
        lines += [
            f"Routes covered by both systems: {len(r_both)}",
            _route_list("Routes only in TSMIS (missing from TSN)", r_t_only),
            _route_list("Routes only in TSN (missing from TSMIS)", r_n_only),
            "Those routes' rows are included — tinted 'entire route' on the "
            "'Only in …' sheets; per-route breakdown on the Routes sheet.",
        ]
        if "formulas" in modes:
            lines.append(
                "Note: the live-formulas workbook opens in MANUAL calculation "
                "— press F9 in Excel to calculate (first time takes a few "
                "minutes), then save. The Summary's SELF-CHECK rows should "
                "all read OK." + ("  The values copy opens ready — nothing "
                                  "to calculate." if "values" in modes else ""))
    if "formulas" in modes:
        lines.append(f"Live-formulas file: {out_paths['formulas']}")
    if "values" in modes:
        lines.append(f"Values file: {out_paths['values']}")
    primary = out_paths["formulas" if "formulas" in modes else "values"]
    return ConsolidateResult(status="ok", output_path=str(primary),
                             summary_lines=lines)
