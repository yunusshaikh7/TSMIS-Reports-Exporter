"""Normalize the raw TSN Intersection Detail statewide workbook into the canonical
TSN library's reusable comparison form.

The TSN Intersection Detail source is a single statewide XLSX ("Sheet 1", 36 DB
columns, every route). "Consolidating" it = projecting it once to the shared
comparison shape ([Route] + the vs-TSN header) so every comparison reads a small
ready workbook instead of re-parsing the 16k-row dump. The projection (route from
LOCATION, PM/date/boolean normalization) lives in compare_intersection_detail_tsn;
this module supplies the report-specific glue and delegates the shared
find-raw/write/save skeleton to tsn_library.build_normalized (S04).

Console-free; openpyxl only.
"""
try:
    from openpyxl import Workbook, load_workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_intersection_detail_tsn as idt
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.xlsx"

# Sidecar columns APPENDED after the shared header (normalization_version 3):
# each row's TSN district + county, split out of its LOCATION ("12 ORA 001").
# The comparison's loader slices them off (compare_intersection_detail_tsn's
# _normalized_row reads exactly the shared width); the visual-evidence generator
# reads them to find a row in the TSN statewide print.
SIDECAR_HEADER = ["TSN District", "TSN County"]


def _dist_cnty(loc):
    """LOCATION '12 ORA 001' / '04 CC. 004' -> ('12', 'ORA'/'CC')."""
    parts = ("" if loc is None else str(loc)).strip().upper().split()
    dist = parts[0] if parts else ""
    cnty = parts[1].rstrip(".") if len(parts) >= 2 else ""
    return dist, cnty


def tsn_rows_with_dcr(path):
    """The raw statewide projection (idt.tsn_rows_from_raw's rows, same order)
    PLUS each row's (district, county) — a separate loop so the comparator's
    regression-locked loader stays untouched."""
    with idt.ctc.exact_raw_rows(
            path, idt.TSN_SHEET, idt.TSN_RAW_HEADER, idt.REPORT_NAME,
            required_nonblank=("LOCATION", "POST_MILE")) as (header, rows_in):
        h = {n: i for i, n in enumerate(header)}
        li = h["LOCATION"]
        rows, dcr = [], []
        for r in rows_in:
            rows.append(idt._tsn_row(r, h))
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
            message=f"Normalized {len(rows)} TSN Intersection Detail rows ({n_routes} routes).",
            summary_lines=[f"TSN Intersection Detail: {len(rows)} rows, {n_routes} routes "
                           f"-> {out_name}"],
            completion=outcome.COMPLETE,
            skipped_inputs=0,
            failed_inputs=0)

    return rows, make_result


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN Intersection Detail statewide workbook in `raw_dir` into
    the normalized workbook at `out_path` (sheet idt.NORMALIZED_SHEET, header
    ['Route'] + idt.SHARED_HEADER + SIDECAR_HEADER). Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        no_raw_what="TSN Intersection Detail .xlsx",
        no_raw_hint="Import the statewide 'TSAR - INTERSECTION DETAIL' TSN export first.",
        log_label="TSN Intersection Detail",
        sheet=idt.NORMALIZED_SHEET,
        header=["Route"] + idt.SHARED_HEADER + SIDECAR_HEADER,
        header_align={"horizontal": "center", "vertical": "center", "wrap_text": True},
        project=_project)
