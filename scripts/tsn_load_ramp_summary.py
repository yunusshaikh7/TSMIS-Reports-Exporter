"""Normalize the raw TSN Ramp Summary statewide PDF into the canonical TSN
library's reusable comparison form.

The TSN Ramp Summary source is a single statewide PDF (one category-count page).
"Consolidating" it means parsing that page once into a small [Category, Count]
workbook, so every Ramp Summary comparison (and the matrix) reads a ready Excel
instead of re-parsing the PDF. The parse (geometry + the 16-ramp-type schema) and
the canonical category list live in compare_ramp_summary_tsn — this module just
drives them for the tsn_library builder contract: build_into(raw_dir, out_path, …).

Console-free; pdfplumber + openpyxl. The library calls build_into lazily.
"""
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_ramp_summary_tsn as rstsn
import outcome
from events import ConsolidateResult, Events

RAW_GLOB = "*.pdf"


def _find_raw(raw_dir):
    """The newest non-temp .pdf in raw_dir (the statewide TSN Ramp Summary export)."""
    cands = [p for p in Path(raw_dir).glob(RAW_GLOB)
             if p.is_file() and not p.name.startswith("~$")]
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Parse the raw TSN Ramp Summary statewide PDF in `raw_dir` into the normalized
    [Category, Count] workbook at `out_path` (sheet rstsn.NORMALIZED_SHEET, keyed on
    the canonical category keys). Returns a ConsolidateResult."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (pdfplumber, openpyxl).")
    raw = _find_raw(raw_dir)
    if raw is None:
        return ConsolidateResult(
            status="error",
            message=(f"No raw TSN Ramp Summary .pdf found in:\n{raw_dir}\n\n"
                     "Import the statewide 'Ramp Summary Statewide' TSN export first."))
    out_path = Path(out_path)
    confirm = confirm_overwrite or (lambda _p: True)
    if out_path.exists() and not confirm(out_path):
        return ConsolidateResult(status="cancelled", message="Cancelled. Existing file kept.")

    events.on_log(f"Normalizing TSN Ramp Summary: {raw.name}")
    try:
        counts = rstsn.parse_tsn_pdf(str(raw))
    except Exception as e:
        return ConsolidateResult(status="error",
                                 message=f"Could not read {raw.name}: {type(e).__name__}: {e}")

    missing = [key for key, slug in rstsn._CATEGORIES if counts.get(slug) is None]

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(rstsn.NORMALIZED_SHEET)
    head_fill = PatternFill("solid", start_color="305496")
    head_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    head_align = Alignment(horizontal="center", vertical="center")
    from openpyxl.cell import WriteOnlyCell
    cells = []
    for label in ("Category", "Count"):
        c = WriteOnlyCell(ws, value=label)
        c.fill, c.font, c.alignment = head_fill, head_font, head_align
        cells.append(c)
    ws.append(cells)
    n = 0
    for key, slug in rstsn._CATEGORIES:
        ws.append([key, int(counts.get(slug, 0) or 0)])
        n += 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(out_path)
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out_path.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))

    summary = [f"TSN Ramp Summary: {n} categories -> {out_path.name}",
               f"Total Number of Ramps: {counts.get('total_ramps')}"]
    if missing:
        summary.insert(0, f"⚠ INCOMPLETE — {len(missing)} categor"
                       f"{'y' if len(missing) == 1 else 'ies'} not found in the PDF: "
                       + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
    # P1-B05: producer-owned completion — a category the PDF didn't yield is a left-out
    # input, so the normalized workbook is PARTIAL (compared, but flagged), never a silent
    # status="ok". Carried structurally (skipped_inputs), not just in the warning text.
    return ConsolidateResult(
        status="ok",
        message=f"Normalized TSN Ramp Summary ({n} categories).",
        summary_lines=summary,
        completion=outcome.PARTIAL if missing else outcome.COMPLETE,
        skipped_inputs=len(missing))
