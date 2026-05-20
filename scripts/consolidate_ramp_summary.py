"""Consolidate TSAR: Ramp Summary PDFs into a single Excel workbook.

Reads every PDF in   output/ramp_summary/
Writes one workbook in output/consolidated/tsar_ramp_summary_consolidated.xlsx
with one row per route plus audit columns that verify the parsed numbers
sum to the reported total.

This script is self-contained on purpose: the parsing logic is specific
to the TSAR Ramp Summary PDF layout (two columns, wrapped descriptions,
orphan numbers) and is not reused by the other consolidators. Each
report's consolidator gets its own file under scripts/ so a layout
change in one report cannot break another.
"""
import logging
import re
import sys
from pathlib import Path

# pdfplumber wraps pdfminer.six, which logs a "Could not get FontBBox from
# font descriptor" warning for every font with a malformed bbox — these
# PDFs hit it on nearly every page. Parsing is unaffected; just silence it.
logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import pdfplumber
except ImportError:
    print('ERROR: pdfplumber is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.formatting.rule import CellIsRule
except ImportError:
    print('ERROR: openpyxl is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from common import OUTPUT_ROOT

INPUT_DIR = OUTPUT_ROOT / "ramp_summary"
OUT_DIR = OUTPUT_ROOT / "consolidated"
OUT_PATH = OUT_DIR / "tsar_ramp_summary_consolidated.xlsx"


# =============================================================================
# Schema — (column_name, label_match_regex), in report order
# =============================================================================

HIGHWAY_GROUPS = [
    ("hwy_right",         r"^R\s*-\s*Right$"),
    ("hwy_divided",       r"^D\s*-\s*Divided$"),
    ("hwy_undivided",     r"^U\s*-\s*Undivided$"),
    ("hwy_unconstructed", r"^X\s*-\s*Unconstructed$"),
    ("hwy_left",          r"^L\s*-\s*Left$"),
    ("hwy_others",        r"^Others$"),
]
ONOFF = [
    ("onoff_on",    r"^ON\s*-\s*On$"),
    ("onoff_off",   r"^OFF\s*-\s*Off$"),
    ("onoff_other", r"^OTH\s*-\s*Other$"),
]
POP_GROUPS = [
    ("pop_rural_inside",  r"^R-RURAL\s*-I\s*INSIDE CITY$"),
    ("pop_rural_outside", r"^-O\s*OUTSIDE CITY$"),     # 1st occurrence
    ("pop_urban_inside",  r"^U-URBAN\s*-I\s*INSIDE CITY$"),
    ("pop_urban_outside", r"^-O\s*OUTSIDE CITY$"),     # 2nd occurrence
    ("pop_invalid",       r"^-INVALID DATA$"),
]
RAMP_TYPES = [
    ("ramp_A_frontage",     r"^A\s*-\s*Frontage Road$"),
    ("ramp_B_collector",    r"^B\s*-\s*Collector Road$"),
    ("ramp_C_connector_L",  r"^C\s*-\s*Direct or Semi-direct Connector \(Left\)$"),
    ("ramp_D_diamond",      r"^D\s*-\s*Diamond Type Ramp$"),
    ("ramp_E_slip",         r"^E\s*-\s*Slip Ramp$"),
    ("ramp_F_connector_R",  r"^F\s*-\s*Direct or Semi-direct Connector \(Right\)$"),
    ("ramp_G_loop_left",    r"^G\s*-\s*Loop \(w/Left turn\)$"),
    ("ramp_H_buttonhook",   r"^H\s*-\s*Buttonhook Ramp$"),
    ("ramp_J_scissors",     r"^J\s*-\s*Scissors$"),
    ("ramp_K_split",        r"^K\s*-\s*Split Ramp$"),
    ("ramp_L_loop_noleft",  r"^L\s*-\s*Loop without Left Turn$"),
    ("ramp_M_two_way",      r"^M\s*-\s*Two way Ramp Segment$"),
    ("ramp_R_rest_area",    r"^R\s*-\s*Rest Area, Vista Point, Truck Scale$"),
    ("ramp_Z_other",        r"^Z\s*-\s*Other$"),
]

COLUMN_SPLIT_X = 300  # left column < this, right column >= this
Y_TOLERANCE = 3       # words within this y-distance are same row


# =============================================================================
# PDF -> rows
# =============================================================================

def get_rows_for_column(words, left=True):
    """Group words into (number_or_None, label_text) tuples for one column."""
    col_words = [w for w in words if (w["x0"] < COLUMN_SPLIT_X) == left]
    if not col_words:
        return []
    col_words.sort(key=lambda w: (w["top"], w["x0"]))

    rows = []
    current_top = None
    current = []
    for w in col_words:
        if current_top is None or abs(w["top"] - current_top) <= Y_TOLERANCE:
            current.append(w)
            current_top = w["top"] if current_top is None else current_top
        else:
            rows.append(current)
            current = [w]
            current_top = w["top"]
    if current:
        rows.append(current)

    parsed = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        texts = [w["text"] for w in row]
        # Accept thousands separators like "1,918"
        if texts and re.fullmatch(r"-?[\d,]+", texts[0]) and any(c.isdigit() for c in texts[0]):
            num = int(texts[0].replace(",", ""))
            label = " ".join(texts[1:])
        else:
            num = None
            label = " ".join(texts)
        parsed.append((num, label.strip()))
    return parsed


# Noise tokens that get merged into data rows by pdfplumber's row clustering.
NOISE_PATTERNS = [
    r"\bHighway Groups\b",
    r"\bOn/Off Indicator\b",
    r"\bPopulation Groups\b",
    r"\bRamp Types\b",
    r"\bNUMBER\s+CODE\b",
    r"\bNUMB\b",
    r"\bCODE\b",
    r"\bER\b",
    r"\bTotal Number of Ramps:\s*[\d,]+\b",
    r"\bRamp Points w/out linework:\s*[\d,]+\b",
]


def clean_label(label):
    """Strip section-header / totals noise that got merged into a data row."""
    out = label
    for pat in NOISE_PATTERNS:
        out = re.sub(pat, "", out)
    return re.sub(r"\s+", " ", out).strip()


def is_new_label(text):
    """Heuristic: does this text start a new schema row, or continue a wrapped one?"""
    if not text:
        return False
    return bool(
        re.match(r"^[A-Z]\s*-\s", text)        # ramp types: "A - ", "D - "
        or re.match(r"^[A-Z]{2,}\s*-\s", text) # on/off:    "ON - ", "OFF - ", "OTH - "
        or re.match(r"^[A-Z]-[A-Z]+", text)    # pop:       "R-RURAL", "U-URBAN"
        or re.match(r"^-[A-Z]", text)          # pop:       "-O", "-I", "-INVALID"
        or text.strip() == "Others"
    )


def _join_continuation(prev, cont):
    """Smart join: 'Co' + 'nnector' -> 'Connector' (broken mid-word),
    but 'Vista Point,' + 'Truck Scale' -> 'Vista Point, Truck Scale'.
    """
    if not prev:
        return cont
    if not cont:
        return prev
    if prev[-1].islower() and cont[0].islower():
        return prev + cont
    return prev + " " + cont


def stitch_wrapped_rows(rows):
    """Combine wrapped continuations and orphan numbers into proper rows."""
    cleaned = [(n, clean_label(l)) for n, l in rows]
    out = []
    open_num, open_label = None, None
    pending_num = None

    def flush():
        nonlocal open_num, open_label
        if open_label is not None or open_num is not None:
            out.append((open_num, open_label or ""))
        open_num, open_label = None, None

    for num, label in cleaned:
        if num is None and not label:
            continue
        if num is not None and not label:
            if open_label is not None and open_num is None:
                open_num = num                  # label was seen first
            else:
                pending_num = num               # hold for next label
            continue
        if num is None and label:
            if is_new_label(label):
                flush()
                open_num = pending_num
                pending_num = None
                open_label = label
            else:
                # continuation of the previous row
                if open_label is not None:
                    open_label = _join_continuation(open_label, label)
                elif out:
                    pn, pl = out[-1]
                    out[-1] = (pn, _join_continuation(pl, label))
            continue
        flush()
        out.append((num, label))
        pending_num = None
    flush()
    return out


def match_schema(rows, schema, used_indices=None):
    """For each schema entry in order, find the next matching row and pull its number."""
    if used_indices is None:
        used_indices = set()
    result = {}
    cursor = 0
    for col_name, pattern in schema:
        found = None
        for i in range(cursor, len(rows)):
            if i in used_indices:
                continue
            num, label = rows[i]
            label_norm = re.sub(r"\s+", " ", label).strip()
            if re.fullmatch(pattern, label_norm):
                found = (i, num)
                break
        if found:
            used_indices.add(found[0])
            cursor = found[0] + 1
            result[col_name] = found[1]
        else:
            result[col_name] = None
    return result


def parse_pdf(path):
    """Return one flat dict for a TSAR ramps summary PDF."""
    record = {"source_file": Path(path).name, "route": None}

    with pdfplumber.open(path) as pdf:
        # Route number from page 1 title
        p1_text = pdf.pages[0].extract_text() or ""
        m = re.search(r"All Ramps on Route\s+(\d+\w*)", p1_text)
        if m:
            record["route"] = m.group(1)

        # Data fields from page 2
        if len(pdf.pages) < 2:
            return record
        page = pdf.pages[1]
        words = page.extract_words()

        left_rows = stitch_wrapped_rows(get_rows_for_column(words, left=True))
        right_rows = stitch_wrapped_rows(get_rows_for_column(words, left=False))

        # Left column: Highway Groups, then On/Off, then Population Groups
        used_left = set()
        record.update(match_schema(left_rows, HIGHWAY_GROUPS, used_left))
        record.update(match_schema(left_rows, ONOFF, used_left))
        record.update(match_schema(left_rows, POP_GROUPS, used_left))

        # Right column: Ramp Types
        record.update(match_schema(right_rows, RAMP_TYPES))

        # Totals are in the page footer, not in either column
        full_text = page.extract_text() or ""
        m = re.search(r"Total Number of Ramps:\s*([\d,]+)", full_text)
        record["total_ramps"] = int(m.group(1).replace(",", "")) if m else None
        m = re.search(r"Ramp Points w/out linework:\s*([\d,]+)", full_text)
        record["ramp_points_no_linework"] = int(m.group(1).replace(",", "")) if m else None

    return record


# =============================================================================
# Records -> Excel
# =============================================================================

# (group_header, [(column_name, display_name)])
GROUPS = [
    ("Source", [
        ("source_file", "Source File"),
        ("route", "Route"),
    ]),
    ("Highway Groups", [(c, c.replace("hwy_", "").title()) for c, _ in HIGHWAY_GROUPS]),
    ("On/Off Indicator", [(c, c.replace("onoff_", "").upper()) for c, _ in ONOFF]),
    ("Population Groups", [
        ("pop_rural_inside",  "Rural-Inside"),
        ("pop_rural_outside", "Rural-Outside"),
        ("pop_urban_inside",  "Urban-Inside"),
        ("pop_urban_outside", "Urban-Outside"),
        ("pop_invalid",       "Invalid"),
    ]),
    ("Ramp Types", [
        ("ramp_A_frontage",    "A-Frontage"),
        ("ramp_B_collector",   "B-Collector"),
        ("ramp_C_connector_L", "C-Conn(L)"),
        ("ramp_D_diamond",     "D-Diamond"),
        ("ramp_E_slip",        "E-Slip"),
        ("ramp_F_connector_R", "F-Conn(R)"),
        ("ramp_G_loop_left",   "G-LoopL"),
        ("ramp_H_buttonhook",  "H-Buttonhook"),
        ("ramp_J_scissors",    "J-Scissors"),
        ("ramp_K_split",       "K-Split"),
        ("ramp_L_loop_noleft", "L-LoopNoL"),
        ("ramp_M_two_way",     "M-TwoWay"),
        ("ramp_R_rest_area",   "R-Rest"),
        ("ramp_Z_other",       "Z-Other"),
    ]),
    ("Totals", [
        ("total_ramps", "Total Ramps"),
        ("ramp_points_no_linework", "Pts w/o Linework"),
    ]),
    ("Audit", [
        ("_chk_hwy",   "Sum Hwy"),
        ("_chk_onoff", "Sum On/Off + NoLW"),
        ("_chk_pop",   "Sum Pop"),
        ("_chk_ramp",  "Sum RampTypes + NoLW"),
        ("_audit_ok",  "Audit OK"),
    ]),
]

THIN = Side(style="thin", color="CCCCCC")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", start_color="305496")
GROUP_FILLS = {
    "Source":            "4472C4",
    "Highway Groups":    "70AD47",
    "On/Off Indicator":  "ED7D31",
    "Population Groups": "7030A0",
    "Ramp Types":        "C00000",
    "Totals":            "BF8F00",
    "Audit":             "595959",
}


def build_workbook(records, out_path):
    """Write a styled, audited workbook with one row per record."""
    wb = Workbook()
    ws = wb.active
    ws.title = "TSAR Ramps Summary"

    # ---- header rows (group + column) ----
    col_idx = 1
    flat_columns = []  # [(col_name, excel_column_index), ...]
    for group_name, cols in GROUPS:
        start = col_idx
        for col_name, display in cols:
            cell = ws.cell(row=2, column=col_idx, value=display)
            cell.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center",
                                       wrap_text=True)
            cell.border = BORDER
            flat_columns.append((col_name, col_idx))
            col_idx += 1
        end = col_idx - 1
        ws.cell(row=1, column=start, value=group_name)
        ws.merge_cells(start_row=1, start_column=start, end_row=1, end_column=end)
        gcell = ws.cell(row=1, column=start)
        gcell.font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
        gcell.fill = PatternFill("solid", start_color=GROUP_FILLS[group_name])
        gcell.alignment = Alignment(horizontal="center", vertical="center")
        gcell.border = BORDER

    col_letters = {name: get_column_letter(idx) for name, idx in flat_columns}
    col_idx_by_name = dict(flat_columns)

    # ---- data rows ----
    for r, rec in enumerate(records, start=3):
        for col_name, c_idx in flat_columns:
            if col_name.startswith("_chk_") or col_name == "_audit_ok":
                continue  # formulas added below
            v = rec.get(col_name)
            cell = ws.cell(row=r, column=c_idx, value=v)
            cell.font = Font(name="Arial", size=10)
            cell.border = BORDER
            if col_name in ("source_file", "route"):
                cell.alignment = Alignment(horizontal="left")
            else:
                cell.alignment = Alignment(horizontal="center")

        def rng(group_cols):
            letters = [col_letters[c] for c, _ in group_cols]
            return f"{letters[0]}{r}:{letters[-1]}{r}"

        nolw = f"{col_letters['ramp_points_no_linework']}{r}"
        total = f"{col_letters['total_ramps']}{r}"

        formulas = {
            "_chk_hwy":   f"=SUM({rng(HIGHWAY_GROUPS)})",
            "_chk_onoff": f"=SUM({rng(ONOFF)})+{nolw}",
            "_chk_pop":   f"=SUM({rng(POP_GROUPS)})",
            "_chk_ramp":  f"=SUM({rng(RAMP_TYPES)})+{nolw}",
        }
        for col_name, f in formulas.items():
            cell = ws.cell(row=r, column=col_idx_by_name[col_name], value=f)
            cell.font = Font(name="Arial", size=10)
            cell.border = BORDER
            cell.alignment = Alignment(horizontal="center")

        chk_cells = [f"{col_letters[c]}{r}" for c in
                     ("_chk_hwy", "_chk_onoff", "_chk_pop", "_chk_ramp")]
        audit_f = "=AND(" + ",".join(f"{c}={total}" for c in chk_cells) + ")"
        cell = ws.cell(row=r, column=col_idx_by_name["_audit_ok"], value=audit_f)
        cell.font = Font(name="Arial", size=10, bold=True)
        cell.border = BORDER
        cell.alignment = Alignment(horizontal="center")

    # ---- conditional formatting on audit_ok ----
    if records:
        audit_col_letter = col_letters["_audit_ok"]
        last_row = 2 + len(records)
        audit_range = f"{audit_col_letter}3:{audit_col_letter}{last_row}"
        ws.conditional_formatting.add(
            audit_range,
            CellIsRule(operator="equal", formula=["TRUE"],
                       fill=PatternFill("solid", start_color="C6EFCE"))
        )
        ws.conditional_formatting.add(
            audit_range,
            CellIsRule(operator="equal", formula=["FALSE"],
                       fill=PatternFill("solid", start_color="FFC7CE"))
        )

    # ---- column widths & freeze ----
    width_overrides = {"source_file": 34, "route": 7}
    for col_name, c_idx in flat_columns:
        letter = get_column_letter(c_idx)
        if col_name in width_overrides:
            ws.column_dimensions[letter].width = width_overrides[col_name]
        elif col_name.startswith("_chk_") or col_name == "_audit_ok":
            ws.column_dimensions[letter].width = 11
        elif col_name in ("total_ramps", "ramp_points_no_linework"):
            ws.column_dimensions[letter].width = 11
        else:
            ws.column_dimensions[letter].width = 8
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 34
    ws.freeze_panes = "C3"  # freeze headers + first two id columns

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


# =============================================================================
# Entry point
# =============================================================================

def main():
    if not INPUT_DIR.exists():
        print(f"ERROR: Input folder is missing: {INPUT_DIR}")
        print('Run "3. run_export (main script).bat" and pick option 1 first.')
        sys.exit(1)

    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"ERROR: No PDFs found in {INPUT_DIR}")
        print('Run "3. run_export (main script).bat" and pick option 1 first.')
        sys.exit(1)

    print("=" * 60)
    print(f"TSAR Ramp Summary Consolidation - {len(pdfs)} file(s)")
    print("=" * 60)
    print()

    records = []
    failed = []
    for i, p in enumerate(pdfs, 1):
        prefix = f"[{i:>3}/{len(pdfs)}] {p.name}"
        try:
            records.append(parse_pdf(str(p)))
            print(f"{prefix} parsed")
        except Exception as e:
            print(f"{prefix} FAILED ({type(e).__name__}): {e}")
            failed.append(p.name)

    print()
    print("Writing consolidated workbook...")
    build_workbook(records, OUT_PATH)

    print()
    print("=" * 60)
    print(f"Parsed:      {len(records)}")
    print(f"Failed:      {len(failed)} {failed if failed else ''}")
    print(f"Output file: {OUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
