"""Normalize the raw TSN Ramp Detail statewide workbook into the canonical TSN
library's reusable comparison form.

The TSN Ramp Detail source is a single statewide XLSX (sheet "Sheet 1", 18 DB
columns, every route). "Consolidating" it just means projecting it to the shared
comparison shape ([Route] + the vs-TSN header) once, so every Ramp Detail
comparison reads a small, ready workbook instead of re-parsing the 15k-row DB
dump. The projection (route from LOCATION, PM/date normalization, the TSN-only
context columns) lives in compare_ramp_detail_tsn — this module just supplies the
report-specific glue and delegates the shared find-raw/write/save skeleton to
tsn_library.build_normalized (S04).

Console-free; openpyxl only (no pdfplumber). The library calls build_into lazily.
"""
try:
    from openpyxl import Workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_ramp_detail_tsn as rd
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.xlsx"


def _project(raw_path):
    """Read the statewide workbook into the consolidated [Route]+SHARED_HEADER rows
    and build the success result (rows count + distinct routes)."""
    rows = rd.tsn_rows_from_raw(raw_path)
    n_routes = len({r[0] for r in rows})

    def make_result(out_name):
        return ConsolidateResult(
            status="ok",
            message=f"Normalized {len(rows)} TSN Ramp Detail rows ({n_routes} routes).",
            summary_lines=[f"TSN Ramp Detail: {len(rows)} rows, {n_routes} routes "
                           f"-> {out_name}"])

    return rows, make_result


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN Ramp Detail statewide workbook in `raw_dir` into the
    normalized comparison workbook at `out_path` (sheet rd.NORMALIZED_SHEET, header
    ['Route'] + rd.SHARED_HEADER). Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        no_raw_what="TSN Ramp Detail .xlsx",
        no_raw_hint="Import the statewide 'TSAR - RAMPS DETAIL' TSN export first.",
        log_label="TSN Ramp Detail",
        sheet=rd.NORMALIZED_SHEET,
        header=["Route"] + rd.SHARED_HEADER,
        header_align={"horizontal": "center", "vertical": "center", "wrap_text": True},
        project=_project)
