"""Build the TSMIS-vs-TSN Highway Log discrepancy workbook.

Takes a TSMIS Highway Log and a TSN Highway Log — either BOTH per-route
workbooks (31 columns, one route each) or BOTH consolidated workbooks (a
leading "Route" column, every route) — and writes one four-sheet comparison
workbook (the format approved from the Route-1 sample):

  Summary      row counts, match status, per-field difference counts, notes
  Comparison   one row per (Route,) Location + occurrence in EITHER file, in
               document order; per-field cells show the matched value, or
               "tsmis ≠ tsn" in red when the systems disagree
  TSMIS / TSN  the two inputs, plus a "Key (helper)" lookup column

EVERYTHING in the workbook is a live Excel formula (lookup keys, statuses,
diff counts, summary): edit a value on the TSMIS or TSN sheet and the whole
report recalculates. The Python side only decides the row universe (the union
of location keys, aligned in document order) and writes the formulas. Note for
the consolidated case: the live keys/lookups make Excel's FIRST recalc of a
50k-row comparison take a while — that's the price of a fully live workbook.

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

# Styling shared by all sheets (colors taken from the approved sample).
_DARK = "1F3864"            # header band / banners
_TAB = {"Summary": "808080", "Comparison": "C00000", "Routes": "ED7D31",
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
    """Counts matching what the workbook's formulas will compute."""
    off = 1 if has_route else 0          # data fields start after Route
    by_t = {k: rows_t[i] for i, k in enumerate(keys_t)}
    by_n = {k: rows_n[i] for i, k in enumerate(keys_n)}
    both = t_only = n_only = diff_rows = identical = diff_cells = 0
    for k in union:
        rt, rn = by_t.get(k), by_n.get(k)
        if rt is None:
            n_only += 1
            continue
        if rn is None:
            t_only += 1
            continue
        both += 1
        row_diffs = 0
        for f in range(1, len(EXPECTED_HEADER)):     # every field but Location
            va, vb = _xl_trim(rt[f + off]), _xl_trim(rn[f + off])
            if EXPECTED_HEADER[f] == "Med Wid":
                va, vb = _medwid_norm(va), _medwid_norm(vb)
            if va != vb:
                row_diffs += 1
        diff_cells += row_diffs
        if row_diffs:
            diff_rows += 1
        else:
            identical += 1
    return {"both": both, "t_only": t_only, "n_only": n_only,
            "diff_rows": diff_rows, "identical": identical,
            "diff_cells": diff_cells}


# =============================================================================
# Layout: column geometry for the two input shapes
# =============================================================================

class _Layout:
    """Column letters for both workbook shapes.

    per-route:    data sheets  Location=A, fields B..AE, key helper AF
                  comparison   Location,#,TSMIS Row,TSN Row,Status,Diffs,fields G..AJ
    consolidated: data sheets  Route=A, Location=B, fields C..AF, key helper AG
                  comparison   Route,Location,#,...,fields H..AK
    """

    def __init__(self, has_route):
        self.has_route = has_route
        self.off = 1 if has_route else 0
        # data sheets
        self.data_header = (["Route"] if has_route else []) + EXPECTED_HEADER
        self.key_col = get_column_letter(len(self.data_header) + 1)   # AF / AG
        self.data_last_col = get_column_letter(len(self.data_header))  # AE / AF
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
        """Data-sheet column letter for EXPECTED_HEADER[field_idx]."""
        return get_column_letter(field_idx + 1 + self.off)

    def field_col(self, field_idx):
        """Comparison-sheet column letter for EXPECTED_HEADER[field_idx]."""
        return get_column_letter(self.f0 + field_idx - 1)

    def key_expr(self, r):
        """The lookup key for Comparison row r (matches the helper column)."""
        if self.has_route:
            return f"${self.c_route}{r}&\"|\"&${self.c_loc}{r}&\"|\"&${self.c_occ}{r}"
        return f"${self.c_loc}{r}&\"|\"&${self.c_occ}{r}"

    def helper_formula(self, r):
        """The data sheets' live key column (occurrence via COUNTIF[S])."""
        if self.has_route:
            return (f'=A{r}&"|"&B{r}&"|"&COUNTIFS($A$2:$A{r},$A{r},'
                    f'$B$2:$B{r},$B{r})')
        return f'=A{r}&"|"&COUNTIF($A$2:$A{r},$A{r})'


# =============================================================================
# Workbook writing
# =============================================================================

def _trim_ref(sheet, col, row_ref):
    return f'TRIM(INDEX({sheet}!{col}:{col},{row_ref}))'


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


def _write_data_sheet(wb, name, rows, lay, events):
    """One input copied to its sheet + the live 'Key (helper)' column."""
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = _TAB[name]
    body_font = Font(name="Arial", size=10)

    ws.freeze_panes = "C2" if lay.has_route else "B2"
    ws.auto_filter.ref = f"A1:{lay.data_last_col}{len(rows) + 1}"
    ws.column_dimensions[lay.key_col].width = 14
    if lay.has_route:
        ws.column_dimensions["A"].width = 8
    ws.column_dimensions[lay.data_col(0)].width = 12          # Location
    ws.column_dimensions[lay.data_col(1)].width = 11          # MI
    ws.column_dimensions[lay.data_col(28)].width = 26         # Description
    ws.column_dimensions[lay.data_col(29)].width = 11         # Date of Rec

    ws.append(_header_row(ws, lay.data_header + ["Key (helper)"]))
    for r, row in enumerate(rows, start=2):
        cells = [_styled(ws, v, body_font) for v in row]
        cells.append(_styled(ws, lay.helper_formula(r), body_font))
        ws.append(cells)
        if (r - 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  {name} sheet: {r - 1:,} rows…")
            if events.is_cancelled():
                return None
    return ws


def _write_comparison(wb, union, lay, events):
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

    ws.append(_header_row(ws, lay.id_headers + EXPECTED_HEADER[1:]))
    for i, (route, loc, occ) in enumerate(union):
        r = i + 2
        key = lay.key_expr(r)
        row = ([route] if lay.has_route else []) + [
            loc, occ,
            f'=IFERROR(MATCH({key},TSMIS!${lay.key_col}:${lay.key_col},0),"")',
            f'=IFERROR(MATCH({key},TSN!${lay.key_col}:${lay.key_col},0),"")',
            f'=IF(AND({lay.c_trow}{r}<>"",{lay.c_nrow}{r}<>""),"Both",'
            f'IF({lay.c_trow}{r}<>"","TSMIS only","TSN only"))',
            # Diffs counts cells carrying the ≠ marker (matched cells show the
            # value now, so "non-blank" no longer means "different").
            f'=IF({lay.c_status}{r}<>"Both","",SUMPRODUCT(--ISNUMBER(SEARCH('
            f'"{_DIFF_MARK}",{lay.field_col(1)}{r}:{lay.last_field_col}{r}))))',
        ]
        row += [_field_formula(lay, r, f) for f in range(1, len(EXPECTED_HEADER))]
        ws.append([_styled(ws, v, body_font) for v in row])
        if (i + 1) % _PROGRESS_EVERY == 0:
            events.on_log(f"  Comparison sheet: {i + 1:,} of {len(union):,} rows…")
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


def _write_routes(wb, all_routes, lay):
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
    for i, route in enumerate(all_routes):
        r = i + 2
        ws.append([_styled(ws, v, body_font) for v in (
            route,
            f'=IF(AND(C{r}>0,D{r}>0),"Both",IF(C{r}>0,"TSMIS only","TSN only"))',
            f'=COUNTIF(TSMIS!$A:$A,$A{r})',
            f'=COUNTIF(TSN!$A:$A,$A{r})',
            f'=COUNTIF(Comparison!$A:$A,$A{r})',
            f'=COUNTIFS(Comparison!$A:$A,$A{r},Comparison!${st}:${st},"Both")',
            f'=COUNTIFS(Comparison!$A:$A,$A{r},Comparison!${st}:${st},"Both",'
            f'Comparison!${df}:${df},">0")',
            f'=SUMIF(Comparison!$A:$A,$A{r},Comparison!${df}:${df})',
        )])
    return ws


def _write_summary(wb, tsmis_name, tsn_name, n_union, lay):
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
    loc_col = lay.data_col(0) if lay.has_route else "A"   # Location on data sheets
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

    def stat(label, formula):
        line((2, label), (3, formula, bold_font, None, center))

    scope = "Consolidated (all routes)" if lay.has_route else "Per-route"
    row[0] = 2
    line((2, f"TSMIS vs TSN — Highway Log — Discrepancy Report ({scope})", title_font))
    if lay.has_route:
        # The big workbook ships UNCALCULATED (manual mode): every cell shows
        # blank/0 until F9. Without a loud banner that reads as broken data.
        line((2, "▶ PRESS F9 TO CALCULATE — this workbook opens uncalculated "
                 "(blank/0 cells). The first F9 takes a few minutes; let it "
                 "finish, then save.",
              Font(name="Arial", size=11, bold=True, color="C00000")))
    line((2, "Cell-by-cell comparison keyed on "
             + ("Route + Location" if lay.has_route else "Location")
             + " (+ occurrence for duplicates). All formulas are live: edits "
             "on the TSMIS / TSN sheets recalculate everything.", note_font))
    line((2, f"TSMIS: {tsmis_name}      TSN: {tsn_name}      "
             f"created {date.today().isoformat()}", note_font), advance=2)

    banner("ROW COUNTS")
    stat("TSMIS data rows", f"=COUNTA(TSMIS!{loc_col}:{loc_col})-1")
    stat("TSN data rows", f"=COUNTA(TSN!{loc_col}:{loc_col})-1")
    stat("Union of locations compared", f"=COUNTA(Comparison!{lay.c_loc}:{lay.c_loc})-1")
    banner("MATCH STATUS")
    stat("Locations in both systems", f'=COUNTIF(Comparison!{st}:{st},"Both")')
    stat("In TSMIS only (missing from TSN)", f'=COUNTIF(Comparison!{st}:{st},"TSMIS only")')
    stat("In TSN only (missing from TSMIS)", f'=COUNTIF(Comparison!{st}:{st},"TSN only")')
    if lay.has_route:
        banner("ROUTE COVERAGE (see the Routes sheet for the per-route breakdown)")
        stat("Routes covered by both systems", '=COUNTIF(Routes!B:B,"Both")')
        stat("Routes only in TSMIS (missing from TSN)", '=COUNTIF(Routes!B:B,"TSMIS only")')
        stat("Routes only in TSN (missing from TSMIS)", '=COUNTIF(Routes!B:B,"TSN only")')
    banner("FIELD-LEVEL DISCREPANCIES (matched rows)")
    stat("Matched rows with ≥ 1 field difference",
         f'=COUNTIFS(Comparison!{st}2:{st}{last},"Both",'
         f'Comparison!{df}2:{df}{last},">0")')
    stat("Matched rows fully identical",
         f'=COUNTIFS(Comparison!{st}2:{st}{last},"Both",'
         f'Comparison!{df}2:{df}{last},0)')
    stat("Total differing cells", f"=SUM(Comparison!{df}2:{df}{last})")
    row[0] += 1

    banner("DIFFERENCES BY FIELD")
    line((2, "Field", bold_font), (3, "Comparison col", bold_font),
         (4, "# of cells differing", bold_font))
    for f in range(1, len(EXPECTED_HEADER)):
        col = lay.field_col(f)
        line((2, EXPECTED_HEADER[f]), (3, col),
             (4, f'=COUNTIF(Comparison!{col}2:{col}{last},"*{_DIFF_MARK.strip()}*")',
              bold_font, None, center))
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
    if lay.has_route:
        notes.append(
            "• The Routes sheet lists every route either system carries — "
            "which side covers it, row counts, and how much of it differs.")
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


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None):
    """Build the comparison workbook. Returns a ConsolidateResult (same
    contract as the consolidators, so the GUI/console drive it identically)."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (openpyxl).")
    confirm = confirm_overwrite or (lambda _p: True)
    tsmis_path, tsn_path, out = Path(tsmis_path), Path(tsn_path), Path(out_path)

    for p, side in ((tsmis_path, "TSMIS"), (tsn_path, "TSN")):
        if not p.is_file():
            return ConsolidateResult(
                status="error",
                message=f"The {side} file doesn't exist:\n{p}")
    if out.exists() and not confirm(out):
        return ConsolidateResult(status="cancelled", message="Cancelled. Existing file kept.")

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
    events.on_log("Writing comparison workbook (live formulas)…")
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")

    # Streaming workbook (see the note above _styled): sheets are created in
    # display order; Summary first so it's the active sheet on open.
    wb = Workbook(write_only=True)
    if has_route:
        # ~2M live formulas: in automatic mode Excel would recalculate for
        # minutes on open AND after every edit. Ship the workbook in MANUAL
        # calculation mode instead — it opens instantly showing blanks/zeros,
        # the user presses F9 once (the one unavoidable big calc), saves, and
        # from then on opens are instant and edits don't hang. calcOnSave off
        # so saving doesn't sneak the big calc back in. (Per-route files stay
        # automatic: they calculate instantly and users expect live updates.)
        wb.calculation.calcMode = "manual"
        wb.calculation.calcOnSave = False
        wb.calculation.fullCalcOnLoad = False
    _write_summary(wb, tsmis_path.name, tsn_path.name, len(union), lay)
    if _write_comparison(wb, union, lay, events) is None:
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")
    if has_route:
        all_routes, r_both, r_t_only, r_n_only = _route_coverage(keys_t, keys_n)
        _write_routes(wb, all_routes, lay)
    if _write_data_sheet(wb, "TSMIS", rows_t, lay, events) is None:
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")
    if _write_data_sheet(wb, "TSN", rows_n, lay, events) is None:
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")
    events.on_log("Saving…")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(out)
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))

    def _route_list(label, routes):
        shown = ", ".join(routes[:15]) + (", …" if len(routes) > 15 else "")
        return f"{label} ({len(routes)}): {shown}" if routes else f"{label}: none"

    lines = [
        f"Locations in both systems:   {counts['both']:,}",
        f"In TSMIS only / in TSN only: {counts['t_only']:,} / {counts['n_only']:,}",
        f"Matched rows with differences: {counts['diff_rows']:,} "
        f"({counts['diff_cells']:,} differing cells); "
        f"{counts['identical']:,} fully identical",
    ]
    if has_route:
        lines += [
            f"Routes covered by both systems: {len(r_both)}",
            _route_list("Routes only in TSMIS (missing from TSN)", r_t_only),
            _route_list("Routes only in TSN (missing from TSMIS)", r_n_only),
            "Per-route breakdown: see the Routes sheet.",
            "Note: the workbook opens in MANUAL calculation — press F9 in "
            "Excel to calculate (first time takes a few minutes), then save.",
        ]
    lines.append(f"Output file: {out}")
    return ConsolidateResult(status="ok", output_path=str(out),
                             summary_lines=lines)
