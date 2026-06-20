"""Normalize the raw TSN Intersection Detail statewide workbook into the canonical
TSN library's reusable comparison form.

The TSN Intersection Detail source is a single statewide XLSX ("Sheet 1", 36 DB
columns, every route). "Consolidating" it = projecting it once to the shared
comparison shape ([Route] + the vs-TSN header) so every comparison reads a small
ready workbook instead of re-parsing the 16k-row dump. The projection (route from
LOCATION, PM/date/boolean normalization) lives in compare_intersection_detail_tsn;
this module drives it for the tsn_library builder contract: build_into(raw_dir, out_path, …).

Console-free; openpyxl only.
"""
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_intersection_detail_tsn as idt
from events import ConsolidateResult, Events

RAW_GLOB = "*.xlsx"


def _find_raw(raw_dir):
    cands = [p for p in Path(raw_dir).glob(RAW_GLOB)
             if p.is_file() and not p.name.startswith("~$")]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN Intersection Detail statewide workbook in `raw_dir` into
    the normalized workbook at `out_path` (sheet idt.NORMALIZED_SHEET, header
    ['Route'] + idt.SHARED_HEADER). Returns a ConsolidateResult."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (openpyxl).")
    raw = _find_raw(raw_dir)
    if raw is None:
        return ConsolidateResult(
            status="error",
            message=(f"No raw TSN Intersection Detail .xlsx found in:\n{raw_dir}\n\n"
                     "Import the statewide 'TSAR - INTERSECTION DETAIL' TSN export first."))
    out_path = Path(out_path)
    confirm = confirm_overwrite or (lambda _p: True)
    if out_path.exists() and not confirm(out_path):
        return ConsolidateResult(status="cancelled", message="Cancelled. Existing file kept.")

    events.on_log(f"Normalizing TSN Intersection Detail: {raw.name}")
    try:
        rows = idt.tsn_rows_from_raw(str(raw))
    except Exception as e:
        return ConsolidateResult(status="error",
                                 message=f"Could not read {raw.name}: {type(e).__name__}: {e}")

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(idt.NORMALIZED_SHEET)
    head_fill = PatternFill("solid", start_color="305496")
    head_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    head_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cells = []
    for label in ["Route"] + idt.SHARED_HEADER:
        c = WriteOnlyCell(ws, value=label)
        c.fill, c.font, c.alignment = head_fill, head_font, head_align
        cells.append(c)
    ws.append(cells)
    for r in rows:
        ws.append(r)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(out_path)
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out_path.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))
    n_routes = len({r[0] for r in rows})
    return ConsolidateResult(
        status="ok",
        message=f"Normalized {len(rows)} TSN Intersection Detail rows ({n_routes} routes).",
        summary_lines=[f"TSN Intersection Detail: {len(rows)} rows, {n_routes} routes "
                       f"-> {out_path.name}"])
