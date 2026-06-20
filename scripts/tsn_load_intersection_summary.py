"""Normalize the raw TSN Intersection Summary statewide PDF into the canonical TSN
library's reusable Category|Count workbook.

Parses the statewide PDF's 3-column category page once (via
compare_intersection_summary_tsn.parse_tsn_pdf) and writes a small normalized
workbook keyed on the canonical category keys, so the matrix + comparison read a
ready Excel instead of re-parsing the PDF. tsn_library builder contract:
build_into(raw_dir, out_path, …). Console-free.
"""
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.cell import WriteOnlyCell
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_intersection_summary_tsn as istsn
from events import ConsolidateResult, Events

RAW_GLOB = "*.pdf"


def _find_raw(raw_dir):
    cands = [p for p in Path(raw_dir).glob(RAW_GLOB)
             if p.is_file() and not p.name.startswith("~$")]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Parse the raw TSN Intersection Summary statewide PDF into the normalized
    Category|Count workbook at `out_path`. Returns a ConsolidateResult."""
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(status="error",
                                 message="Required components are missing (pdfplumber, openpyxl).")
    raw = _find_raw(raw_dir)
    if raw is None:
        return ConsolidateResult(
            status="error",
            message=(f"No raw TSN Intersection Summary .pdf found in:\n{raw_dir}\n\n"
                     "Import the statewide 'Intersection Summary Statewide' TSN export first."))
    out_path = Path(out_path)
    confirm = confirm_overwrite or (lambda _p: True)
    if out_path.exists() and not confirm(out_path):
        return ConsolidateResult(status="cancelled", message="Cancelled. Existing file kept.")

    events.on_log(f"Normalizing TSN Intersection Summary: {raw.name}")
    try:
        counts = istsn.parse_tsn_pdf(str(raw))
    except Exception as e:
        return ConsolidateResult(status="error",
                                 message=f"Could not read {raw.name}: {type(e).__name__}: {e}")

    tsn_cats = istsn._SPEC.categories_for("tsn")     # TSN-applicable only (no TSMIS-only codes)
    missing = [key for key, slug in tsn_cats if counts.get(slug) is None]
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(istsn.NORMALIZED_SHEET)
    head_fill = PatternFill("solid", start_color="305496")
    head_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    cells = []
    for label in ("Category", "Count"):
        c = WriteOnlyCell(ws, value=label)
        c.fill, c.font, c.alignment = head_fill, head_font, Alignment(horizontal="center")
        cells.append(c)
    ws.append(cells)
    n = 0
    for key, slug in tsn_cats:
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

    summary = [f"TSN Intersection Summary: {n} categories -> {out_path.name}",
               f"Total Intersections: {counts.get('total_intersections')}"]
    if missing:
        summary.insert(0, f"⚠ INCOMPLETE — {len(missing)} categor"
                       f"{'y' if len(missing) == 1 else 'ies'} not found in the PDF: "
                       + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
    return ConsolidateResult(status="ok",
                             message=f"Normalized TSN Intersection Summary ({n} categories).",
                             summary_lines=summary)
