"""Normalize the raw TSN Ramp Detail statewide workbook into the canonical TSN
library's reusable comparison form.

The TSN Ramp Detail source is a single statewide XLSX (sheet "Sheet 1", 18 DB
columns, every route). "Consolidating" it just means projecting it to the shared
comparison shape ([Route] + the vs-TSN header) once, so every Ramp Detail
comparison reads a small, ready workbook instead of re-parsing the 15k-row DB
dump. The projection (route from LOCATION, PM/date normalization, the TSN-only
context columns) lives in compare_ramp_detail_tsn — this module just drives it for
the tsn_library builder contract: build_into(raw_dir, out_path, …).

Console-free; openpyxl only (no pdfplumber). The library calls build_into lazily.
"""
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_ramp_detail_tsn as rd
import artifact_store
from events import ConsolidateResult, Events

RAW_GLOB = "*.xlsx"


def _find_raw(raw_dir):
    """The newest non-temp .xlsx in raw_dir (the statewide TSN Ramp Detail export)."""
    cands = [p for p in Path(raw_dir).glob(RAW_GLOB)
             if p.is_file() and not p.name.startswith("~$")]
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN Ramp Detail statewide workbook in `raw_dir` into the
    normalized comparison workbook at `out_path` (sheet rd.NORMALIZED_SHEET, header
    ['Route'] + rd.SHARED_HEADER). Returns a ConsolidateResult."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (openpyxl).")
    raw = _find_raw(raw_dir)
    if raw is None:
        return ConsolidateResult(
            status="error",
            message=(f"No raw TSN Ramp Detail .xlsx found in:\n{raw_dir}\n\n"
                     "Import the statewide 'TSAR - RAMPS DETAIL' TSN export first."))
    out_path = Path(out_path)
    confirm = confirm_overwrite or (lambda _p: True)
    if out_path.exists() and not confirm(out_path):
        return ConsolidateResult(status="cancelled", message="Cancelled. Existing file kept.")

    events.on_log(f"Normalizing TSN Ramp Detail: {raw.name}")
    try:
        rows = rd.tsn_rows_from_raw(str(raw))
    except Exception as e:
        return ConsolidateResult(status="error",
                                 message=f"Could not read {raw.name}: {type(e).__name__}: {e}")

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(rd.NORMALIZED_SHEET)
    head_fill = PatternFill("solid", start_color="305496")
    head_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    head_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    hdr = ["Route"] + rd.SHARED_HEADER
    from openpyxl.cell import WriteOnlyCell
    cells = []
    for label in hdr:
        c = WriteOnlyCell(ws, value=label)
        c.fill, c.font, c.alignment = head_fill, head_font, head_align
        cells.append(c)
    ws.append(cells)
    for r in rows:
        ws.append(r)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        artifact_store.atomic_save(wb, out_path)    # F9: temp + os.replace (never truncate prior)
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out_path.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))
    n_routes = len({r[0] for r in rows})
    return ConsolidateResult(
        status="ok",
        message=f"Normalized {len(rows)} TSN Ramp Detail rows ({n_routes} routes).",
        summary_lines=[f"TSN Ramp Detail: {len(rows)} rows, {n_routes} routes "
                       f"-> {out_path.name}"])
