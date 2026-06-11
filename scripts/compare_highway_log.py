"""Build the TSMIS-vs-TSN Highway Log discrepancy workbook.

Takes TWO per-route Highway Log workbooks -- the TSMIS export and the TSN
file produced by the TSN Highway Log consolidation -- and writes one
four-sheet comparison workbook (the format approved from the Route-1 sample):

  Summary      row counts, match status, per-field difference counts, notes
  Comparison   one row per (Location, occurrence) in EITHER file, in document
               order; per-field cells show the matched value, or
               "tsmis ≠ tsn" in red when the systems disagree
  TSMIS / TSN  the two inputs, plus a "Key (helper)" lookup column

EVERYTHING in the workbook is a live Excel formula (lookups, statuses, diff
counts, summary): edit a value on the TSMIS or TSN sheet and the whole report
recalculates. The Python side only decides the row universe (the union of
location keys, aligned in document order) and writes the formulas.

Comparison semantics (mirrored in _count_diffs for the run summary):
  * Rows are keyed on Location plus occurrence number (duplicates like a
    postmile listed twice pair up by order of appearance).
  * Values compare after Excel TRIM (the TSMIS export pads Description).
  * Med Wid first normalizes zero-padding in the numeric part (TSMIS '0Z' =
    TSN '00Z'); every other field compares exactly.

Console-free like the other report modules: progress via events.on_log,
overwrite via the confirm_overwrite callback, ConsolidateResult returned.
"""
import re
from datetime import date
from pathlib import Path

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.formatting.rule import CellIsRule, FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from events import ConsolidateResult, Events

REPORT_NAME = "Highway Log Comparison"
SHEET_NAME = "Highway Log"          # required sheet in both inputs

# The per-route Highway Log layout (TSMIS export == converted TSN file).
EXPECTED_HEADER = [
    "Location", "MI", "N/A", "Cnty Odom", "City", "R/U", "SPD", "TER", "H/G",
    "A/C", "LB T", "LB Lns", "LB F", "LB OT", "LB TR", "LB T-W", "LB IN",
    "LB SH", "Med TCB", "Med Wid", "RB T", "RB Lns", "RB F", "RB IN", "RB SH",
    "RB T-W", "RB OT", "RB SH", "Description", "Date of Rec", "Sig Chg. Date",
]
N_FIELDS = len(EXPECTED_HEADER) - 1      # data fields (everything but Location)

# Styling shared by all sheets (colors taken from the approved sample).
_DARK = "1F3864"            # header band / banners
_TAB = {"Summary": "808080", "Comparison": "C00000",
        "TSMIS": "4472C4", "TSN": "70AD47"}
_DIFF_MARK = " ≠ "          # appears ONLY in differing cells; counts key on it


# =============================================================================
# Input loading
# =============================================================================

def _load_per_route(path):
    """Load one per-route Highway Log workbook -> list of row tuples.
    Raises ValueError with a user-safe message when the shape is wrong."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if SHEET_NAME not in wb.sheetnames:
            raise ValueError(
                f"{name} has no '{SHEET_NAME}' sheet — pick a per-route "
                f"Highway Log workbook (a TSMIS export, or a TSN file made by "
                f"the TSN Highway Log consolidation).")
        rows_iter = wb[SHEET_NAME].iter_rows(values_only=True)
        header = [v for v in next(rows_iter, [])]
        # Trim trailing blanks some writers append to the header row.
        while header and header[-1] in (None, ""):
            header.pop()
        if header[:1] == ["Route"] and header[1:] == EXPECTED_HEADER:
            raise ValueError(
                f"{name} looks like a CONSOLIDATED multi-route workbook. "
                f"Pick the per-route file instead (one route per workbook).")
        if header != EXPECTED_HEADER:
            raise ValueError(
                f"{name} doesn't have the Highway Log column layout this "
                f"comparison expects — re-create it with this app, then retry.")
        n = len(EXPECTED_HEADER)
        rows = []
        for r in rows_iter:
            r = list(r)[:n] + [None] * max(0, n - len(r))
            if any(v is not None and str(v).strip() != "" for v in r):
                rows.append(r)
        return rows
    finally:
        wb.close()


def _keys(rows):
    """[(location, occurrence), ...] in file order. Occurrence numbers repeat
    visits to the same Location (1-based), exactly like the sheets' helper
    column =A&"|"&COUNTIF($A$2:$A,$A)."""
    seen = {}
    out = []
    for r in rows:
        loc = "" if r[0] is None else str(r[0])
        seen[loc] = seen.get(loc, 0) + 1
        out.append((loc, seen[loc]))
    return out


def _union_keys(keys_t, keys_n):
    """The union of the two key sequences in DOCUMENT order: common keys appear
    exactly once, file-only keys are interleaved at the position their file
    gives them (a diff-style alignment, not a sort — postmiles can legitimately
    run backwards at realignments, so sorting would lie).

    The dedupe matters: a key present in BOTH files can fall outside the
    aligner's 'equal' blocks when one file lists it out of sequence (seen in
    the field: TSMIS printed 059.739 after 059.759 while TSN kept it in
    order). It would then be emitted by both its TSMIS block and its TSN
    block; each key keeps its FIRST position only. The Excel MATCH lookups
    pair the row with both files regardless of where the union places it."""
    import difflib
    sm = difflib.SequenceMatcher(None, keys_t, keys_n, autojunk=False)
    out = []
    seen = set()

    def emit(keys):
        for k in keys:
            if k not in seen:
                seen.add(k)
                out.append(k)

    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            emit(keys_t[a0:a1])
        elif op == "delete":
            emit(keys_t[a0:a1])
        elif op == "insert":
            emit(keys_n[b0:b1])
        else:                               # replace: TSMIS block, then TSN block
            emit(keys_t[a0:a1])
            emit(keys_n[b0:b1])
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


def _count_diffs(rows_t, rows_n, keys_t, keys_n, union):
    """Counts matching what the workbook's formulas will compute."""
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
            va, vb = _xl_trim(rt[f]), _xl_trim(rn[f])
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
# Workbook writing
# =============================================================================

def _trim_ref(sheet, col, row_ref):
    return f'TRIM(INDEX({sheet}!{col}:{col},{row_ref}))'


def _medwid_ref(sheet, col, row_ref):
    """The zero-padding-normalized form of a Med Wid cell (see _medwid_norm)."""
    t = _trim_ref(sheet, col, row_ref)
    return (f'IFERROR(VALUE({t})&"",'
            f'IFERROR(VALUE(LEFT({t},LEN({t})-1))&RIGHT({t},1),{t}))')


def _field_formula(r, field_idx):
    """Comparison cell formula for data field `field_idx` (1-based into
    EXPECTED_HEADER) on Comparison row `r`: the matched value when the two
    systems agree, 'tsmis ≠ tsn' when they differ, blank when the row isn't
    in both files."""
    col = get_column_letter(field_idx + 1)          # sheet col: B..AE
    t, n = _trim_ref("TSMIS", col, f"$C{r}"), _trim_ref("TSN", col, f"$D{r}")
    if EXPECTED_HEADER[field_idx] == "Med Wid":
        eq = f'{_medwid_ref("TSMIS", col, f"$C{r}")}={_medwid_ref("TSN", col, f"$D{r}")}'
    else:
        eq = f"{t}={n}"
    show_t = f'IF({t}="","(blank)",{t})'
    show_n = f'IF({n}="","(blank)",{n})'
    return (f'=IF($E{r}<>"Both","",IF({eq},{t},'
            f'{show_t}&"{_DIFF_MARK}"&{show_n}))')


def _write_data_sheet(wb, name, rows):
    """One input copied to its sheet + the live 'Key (helper)' column."""
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = _TAB[name]
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", start_color=_DARK)
    body_font = Font(name="Arial", size=10)

    ws.append(EXPECTED_HEADER + ["Key (helper)"])
    for c in ws[1]:
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="bottom", wrap_text=True)
    for r, row in enumerate(rows, start=2):
        ws.append(list(row) + [f'=A{r}&"|"&COUNTIF($A$2:$A{r},$A{r})'])
        for c in ws[r]:
            c.font = body_font
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:AE{len(rows) + 1}"
    for col, w in (("A", 12), ("B", 11), ("AC", 26), ("AD", 11), ("AF", 14)):
        ws.column_dimensions[col].width = w
    return ws


def _write_comparison(wb, union):
    ws = wb.create_sheet("Comparison")
    ws.sheet_properties.tabColor = _TAB["Comparison"]
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", start_color=_DARK)
    body_font = Font(name="Arial", size=10)

    ws.append(["Location", "#", "TSMIS Row", "TSN Row", "Status", "Diffs"]
              + EXPECTED_HEADER[1:])
    for c in ws[1]:
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="bottom", wrap_text=True)
    ws.row_dimensions[1].height = 45.75

    last_field_col = get_column_letter(6 + N_FIELDS)            # AJ
    for i, (loc, occ) in enumerate(union):
        r = i + 2
        row = [
            loc, occ,
            f'=IFERROR(MATCH($A{r}&"|"&$B{r},TSMIS!$AF:$AF,0),"")',
            f'=IFERROR(MATCH($A{r}&"|"&$B{r},TSN!$AF:$AF,0),"")',
            f'=IF(AND(C{r}<>"",D{r}<>""),"Both",IF(C{r}<>"","TSMIS only","TSN only"))',
            # Diffs counts cells carrying the ≠ marker (matched cells show the
            # value now, so "non-blank" no longer means "different").
            f'=IF(E{r}<>"Both","",SUMPRODUCT(--ISNUMBER(SEARCH("{_DIFF_MARK}",'
            f'G{r}:{last_field_col}{r}))))',
        ]
        row += [_field_formula(r, f) for f in range(1, len(EXPECTED_HEADER))]
        ws.append(row)
        for c in ws[r]:
            c.font = body_font

    last = len(union) + 1
    ws.freeze_panes = "G2"
    ws.auto_filter.ref = f"A1:{last_field_col}{last}"
    for col, w in (("A", 12), ("B", 4), ("C", 7), ("E", 11), ("F", 6),
                   ("G", 12), ("AH", 30), ("AI", 12)):
        ws.column_dimensions[col].width = w

    # Conditional formatting (same look as the sample, diff detection keyed on
    # the ≠ marker): red diff cells, yellow TSMIS-only rows, blue TSN-only
    # rows, bold red Diffs count when > 0.
    full = f"A2:{last_field_col}{last}"
    fields = f"G2:{last_field_col}{last}"
    ws.conditional_formatting.add(fields, FormulaRule(
        formula=[f'ISNUMBER(SEARCH("{_DIFF_MARK}",G2))'],
        fill=PatternFill(bgColor="FFC7CE"),
        font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(full, FormulaRule(
        formula=['$E2="TSMIS only"'], fill=PatternFill(bgColor="FFE699")))
    ws.conditional_formatting.add(full, FormulaRule(
        formula=['$E2="TSN only"'], fill=PatternFill(bgColor="BDD7EE")))
    ws.conditional_formatting.add(f"F2:F{last}", CellIsRule(
        operator="greaterThan", formula=["0"],
        font=Font(color="C00000", bold=True)))
    return ws


def _write_summary(wb, tsmis_name, tsn_name, n_union):
    ws = wb.active
    ws.title = "Summary"
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

    row = [1]                                       # 1-slot mutable cursor

    def put(col, value, font=body_font, fill=None, align=None):
        c = ws.cell(row=row[0], column=col, value=value)
        c.font = font
        if fill:
            c.fill = fill
        if align:
            c.alignment = align
        return c

    def line(*cells, advance=1):
        for col, value, *style in cells:
            put(col, value, *style)
        row[0] += advance

    def banner(text):
        line((2, text, banner_font, banner_fill))

    def stat(label, formula):
        line((2, label), (3, formula, bold_font, None, center))

    row[0] = 2
    line((2, "TSMIS vs TSN — Highway Log — Discrepancy Report", title_font))
    line((2, "Cell-by-cell comparison keyed on Location (+ occurrence for "
             "duplicates). All formulas are live: edits on the TSMIS / TSN "
             "sheets recalculate everything.", note_font))
    line((2, f"TSMIS: {tsmis_name}      TSN: {tsn_name}      "
             f"created {date.today().isoformat()}", note_font), advance=2)

    banner("ROW COUNTS")
    stat("TSMIS data rows", "=COUNTA(TSMIS!A:A)-1")
    stat("TSN data rows", "=COUNTA(TSN!A:A)-1")
    stat("Union of locations compared", "=COUNTA(Comparison!A:A)-1")
    banner("MATCH STATUS")
    stat("Locations in both systems", '=COUNTIF(Comparison!E:E,"Both")')
    stat("In TSMIS only (missing from TSN)", '=COUNTIF(Comparison!E:E,"TSMIS only")')
    stat("In TSN only (missing from TSMIS)", '=COUNTIF(Comparison!E:E,"TSN only")')
    banner("FIELD-LEVEL DISCREPANCIES (matched rows)")
    stat("Matched rows with ≥ 1 field difference",
         f'=COUNTIFS(Comparison!E2:E{last},"Both",Comparison!F2:F{last},">0")')
    stat("Matched rows fully identical",
         f'=COUNTIFS(Comparison!E2:E{last},"Both",Comparison!F2:F{last},0)')
    stat("Total differing cells", f"=SUM(Comparison!F2:F{last})")
    row[0] += 1

    banner("DIFFERENCES BY FIELD")
    line((2, "Field", bold_font), (3, "Comparison col", bold_font),
         (4, "# of cells differing", bold_font))
    for f in range(1, len(EXPECTED_HEADER)):
        col = get_column_letter(6 + f)              # Comparison column G..AJ
        line((2, EXPECTED_HEADER[f]), (3, col),
             (4, f'=COUNTIF(Comparison!{col}2:{col}{last},"*{_DIFF_MARK.strip()}*")',
              bold_font, None, center))
    row[0] += 1

    banner("HOW TO READ / NOTES")
    for note in (
        "• Comparison sheet: matching values are shown in plain text; a red "
        f"cell shows  TSMIS value{_DIFF_MARK}TSN value  where the two systems "
        "disagree for that Location and field.",
        '• "(blank)" means the cell is empty in that system. Filter the Diffs '
        "column (>0) to isolate rows needing review.",
        "• Yellow rows exist only in TSMIS; blue rows exist only in TSN "
        "(mostly TSN segment splits and TSMIS realignment markers).",
        "• Rows pair on Location plus occurrence number (a postmile listed "
        "twice pairs first-with-first, second-with-second).",
        "• Leading/trailing spaces are ignored (TRIM) — the TSMIS export pads "
        "Description with trailing blanks.",
        '• Lookups use the "Key (helper)" column (AF) on each data sheet: '
        'Location & "|" & occurrence #.',
        "• Med Wid is compared after normalizing zero-padding in the numeric "
        "part (TSMIS 0Z = TSN 00Z, 6V = 06V, etc.), since the two systems "
        "format this code differently. All other fields compare exactly.",
    ):
        line((2, note, note_font))


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
        rows_t = _load_per_route(tsmis_path)
        rows_n = _load_per_route(tsn_path)
    except ValueError as e:
        return ConsolidateResult(status="error", message=str(e))
    if not rows_t or not rows_n:
        return ConsolidateResult(
            status="error",
            message="One of the files has no data rows — nothing to compare.")
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")

    keys_t, keys_n = _keys(rows_t), _keys(rows_n)
    union = _union_keys(keys_t, keys_n)
    counts = _count_diffs(rows_t, rows_n, keys_t, keys_n, union)
    events.on_log(f"TSMIS rows: {len(rows_t)}   TSN rows: {len(rows_n)}   "
                  f"union: {len(union)} locations")
    events.on_log("Writing comparison workbook (live formulas)…")
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")

    wb = Workbook()
    _write_summary(wb, tsmis_path.name, tsn_path.name, len(union))
    _write_comparison(wb, union)
    _write_data_sheet(wb, "TSMIS", rows_t)
    _write_data_sheet(wb, "TSN", rows_n)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(out)
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))

    return ConsolidateResult(
        status="ok",
        output_path=str(out),
        summary_lines=[
            f"Locations in both systems:   {counts['both']}",
            f"In TSMIS only / in TSN only: {counts['t_only']} / {counts['n_only']}",
            f"Matched rows with differences: {counts['diff_rows']} "
            f"({counts['diff_cells']} differing cells); "
            f"{counts['identical']} fully identical",
            f"Output file: {out}",
        ],
    )
