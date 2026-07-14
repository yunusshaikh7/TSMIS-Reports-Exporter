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
    from openpyxl import Workbook, load_workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_ramp_detail_tsn as rd
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.xlsx"

# Sidecar columns APPENDED after the shared header (normalization_version 3, the
# Intersection Detail pattern): each row's TSN district + county, split out of
# its LOCATION ("01-DN-101"). The comparison's loader slices them off
# (compare_ramp_detail_tsn's _normalized_row reads exactly the shared width);
# the visual-evidence generator reads them to find a row in the TSN statewide
# print.
SIDECAR_HEADER = ["TSN District", "TSN County"]


def _dist_cnty(loc):
    """LOCATION '01-DN-101' / '04-CC.-004' -> ('01', 'DN'/'CC')."""
    parts = ("" if loc is None else str(loc)).strip().upper().split("-")
    dist = parts[0].strip() if parts else ""
    cnty = parts[1].strip().rstrip(".") if len(parts) >= 2 else ""
    return dist, cnty


def tsn_rows_with_dcr(path):
    """The raw statewide projection (rd.tsn_rows_from_raw's rows, same order)
    PLUS each row's (district, county) — a separate loop so the comparator's
    regression-locked loader stays untouched."""
    with rd.ctc.exact_raw_rows(
            path, rd.TSN_SHEET, rd.TSN_RAW_HEADER, rd.REPORT_NAME,
            required_nonblank=("LOCATION", "PM")) as (header, rows_in):
        h = {n: i for i, n in enumerate(header)}
        li = h["LOCATION"]
        rows, dcr = [], []
        for r in rows_in:
            rows.append(rd._tsn_raw_row(r, h))
            dcr.append(_dist_cnty(r[li] if li < len(r) else None))
        return rows, dcr


def _project(raw_path):
    """Read the statewide workbook into the consolidated [Route]+SHARED_HEADER
    (+ sidecar) rows and build the success result (rows count + distinct routes)."""
    base, dcr = tsn_rows_with_dcr(raw_path)
    rows = [row + list(dc) for row, dc in zip(base, dcr)]
    n_routes = len({r[0] for r in rows})

    def make_result(out_name):
        return ConsolidateResult(
            status="ok",
            message=f"Normalized {len(rows)} TSN Ramp Detail rows ({n_routes} routes).",
            summary_lines=[f"TSN Ramp Detail: {len(rows)} rows, {n_routes} routes "
                           f"-> {out_name}"],
            completion=outcome.COMPLETE,
            skipped_inputs=0,
            failed_inputs=0)

    return rows, make_result


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN Ramp Detail statewide workbook in `raw_dir` into the
    normalized comparison workbook at `out_path` (sheet rd.NORMALIZED_SHEET, header
    ['Route'] + rd.SHARED_HEADER + SIDECAR_HEADER). Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        no_raw_what="TSN Ramp Detail .xlsx",
        no_raw_hint="Import the statewide 'TSAR - RAMPS DETAIL' TSN export first.",
        log_label="TSN Ramp Detail",
        sheet=rd.NORMALIZED_SHEET,
        header=["Route"] + rd.SHARED_HEADER + SIDECAR_HEADER,
        header_align={"horizontal": "center", "vertical": "center", "wrap_text": True},
        project=_project)
