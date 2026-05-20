"""Consolidate Highway Sequence Listing XLSX files into a single workbook.

Reads every XLSX in   output/highway_sequence/
Writes one workbook in output/consolidated/highway_sequence_consolidated.xlsx
with a leading "Route" column added so rows from different routes are
distinguishable in the combined file.

This script is self-contained on purpose: each consolidator owns its
own read/write logic so a quirk in one report's XLSX layout cannot
affect the others.
"""
import re
import sys
from pathlib import Path

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    print('ERROR: openpyxl is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from common import OUTPUT_ROOT

INPUT_DIR = OUTPUT_ROOT / "highway_sequence"
OUT_DIR = OUTPUT_ROOT / "consolidated"
OUT_PATH = OUT_DIR / "highway_sequence_consolidated.xlsx"

# Sheet name produced by the TSMIS export — must match exactly.
SHEET_NAME = "Highway Locations"

# Pull the route token out of "highway_sequence_route_<ROUTE>.xlsx".
ROUTE_FROM_NAME = re.compile(r"_route_(\w+)\.xlsx$", re.IGNORECASE)

HEADER_FILL = PatternFill("solid", start_color="305496")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)


def extract_route(path):
    m = ROUTE_FROM_NAME.search(path.name)
    return m.group(1).upper() if m else path.stem


def read_header(path):
    """Return row 1 of the expected sheet, or None if the file isn't shaped
    like a Highway Sequence export.
    """
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        if SHEET_NAME not in wb.sheetnames:
            return None
        ws = wb[SHEET_NAME]
        row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        return list(row) if row else None
    finally:
        wb.close()


def stream_data_rows(path):
    """Yield each data row (row 2 onwards) as a tuple."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[SHEET_NAME]
        for row in ws.iter_rows(min_row=2, values_only=True):
            yield row
    finally:
        wb.close()


def confirm_overwrite(path):
    """Ask the user whether to overwrite an existing consolidated workbook.

    Returns True if the user agreed (Y/yes), False otherwise. Exits early
    via sys.exit(0) on EOF so double-clicking the BAT and immediately
    closing the window doesn't look like a crash.
    """
    print()
    print("A consolidated workbook already exists at:")
    print(f"   {path}")
    try:
        ans = input("Overwrite it? [Y/N]: ").strip().lower()
    except EOFError:
        print("\nCancelled.")
        sys.exit(0)
    return ans in ("y", "yes")


def main():
    if not INPUT_DIR.exists():
        print(f"ERROR: Input folder is missing: {INPUT_DIR}")
        print('Run "3. run_export (main script).bat" and pick option 3 first.')
        sys.exit(1)

    files = sorted(INPUT_DIR.glob("*.xlsx"))
    if not files:
        print(f"ERROR: No XLSX files found in {INPUT_DIR}")
        print('Run "3. run_export (main script).bat" and pick option 3 first.')
        sys.exit(1)

    # Confirm overwrite before reading any inputs, and surface the
    # "file is open in Excel" case as a clear message rather than a
    # raw PermissionError from wb.save().
    if OUT_PATH.exists():
        if not confirm_overwrite(OUT_PATH):
            print("Cancelled. Existing file kept.")
            sys.exit(0)

    print("=" * 60)
    print(f"Highway Sequence Consolidation - {len(files)} file(s)")
    print("=" * 60)
    print()

    # Lock in the first readable file's header as the canonical layout.
    # Files that disagree are skipped so misaligned columns can't silently
    # corrupt the combined workbook.
    canonical_header = None
    canonical_source = None
    for p in files:
        try:
            h = read_header(p)
        except Exception as e:
            print(f"  {p.name}: header read FAILED ({type(e).__name__}); skipping")
            continue
        if h is None:
            print(f"  {p.name}: sheet '{SHEET_NAME}' missing; skipping")
            continue
        canonical_header = h
        canonical_source = p.name
        break

    if canonical_header is None:
        print(f"ERROR: No readable XLSX files in {INPUT_DIR}.")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # write_only mode streams rows to disk so the consolidated file can
    # be hundreds of thousands of rows without exhausting memory.
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(SHEET_NAME)
    ws.freeze_panes = "B2"

    ws.column_dimensions["A"].width = 9
    for i, _ in enumerate(canonical_header, start=2):
        ws.column_dimensions[get_column_letter(i)].width = 16

    header_values = ["Route"] + [v if v is not None else "" for v in canonical_header]
    header_cells = []
    for v in header_values:
        cell = WriteOnlyCell(ws, value=str(v))
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        header_cells.append(cell)
    ws.append(header_cells)

    used_files = 0
    appended_rows = 0
    skipped = []
    failed = []

    for i, p in enumerate(files, 1):
        prefix = f"[{i:>3}/{len(files)}] {p.name}"
        try:
            h = read_header(p)
        except Exception as e:
            print(f"{prefix} FAILED reading header ({type(e).__name__}): {e}")
            failed.append(p.name)
            continue
        if h is None:
            print(f"{prefix} skipped: sheet '{SHEET_NAME}' missing")
            skipped.append(p.name)
            continue
        if h != canonical_header:
            print(f"{prefix} skipped: header differs from {canonical_source}")
            skipped.append(p.name)
            continue

        route = extract_route(p)
        try:
            count = 0
            for row in stream_data_rows(p):
                ws.append([route] + list(row))
                count += 1
            print(f"{prefix} +{count} rows  (route {route})")
            appended_rows += count
            used_files += 1
        except Exception as e:
            print(f"{prefix} FAILED reading rows ({type(e).__name__}): {e}")
            failed.append(p.name)

    print()
    print("Writing consolidated workbook...")
    try:
        wb.save(OUT_PATH)
    except PermissionError:
        print()
        print("=" * 60)
        print(f"ERROR: Could not write {OUT_PATH.name}.")
        print()
        print("This usually means the file is open in Excel. Close it")
        print("there and run this consolidator again. (None of the input")
        print("XLSX files were modified.)")
        print("=" * 60)
        sys.exit(1)

    print()
    print("=" * 60)
    print(f"Files combined: {used_files}")
    print(f"Rows added:     {appended_rows}")
    print(f"Files skipped:  {len(skipped)} {skipped if skipped else ''}")
    print(f"Files failed:   {len(failed)} {failed if failed else ''}")
    print(f"Output file:    {OUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
