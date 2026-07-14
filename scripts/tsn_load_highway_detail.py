"""Normalize the raw TSN Highway Detail statewide workbook into the canonical
TSN library's reusable comparison form.

The TSN Highway Detail source is a single statewide XLSX ("Sheet 1", 56 DB
columns, every route). "Consolidating" it = projecting it once to the shared
comparison shape ([Route] + the vs-TSN header) so every comparison reads a
small ready workbook instead of re-parsing the 60k-row dump. The projection
(route from RTE+RTE_SFX, the canonical roadbed-aware Post Mile, NA/zero-pad/
length/median normalization) lives in compare_highway_detail_tsn; this module
supplies the report-specific glue and delegates the shared find-raw/write/save
skeleton to tsn_library.build_normalized (S04).

Console-free; openpyxl only.
"""
try:
    from openpyxl import Workbook, load_workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_highway_detail_tsn as hdt
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.xlsx"

# Sidecar columns APPENDED after the shared header (normalization_version 2):
# each row's TSN district + county. The comparison's loader slices them off
# (compare_highway_detail_tsn._normalized_row reads exactly the shared width);
# the visual-evidence generator reads them to find a row's district print.
SIDECAR_HEADER = ["TSN District", "TSN County"]


def tsn_rows_with_dcr(path):
    """The raw statewide projection (hdt.tsn_rows_from_raw's rows, same order)
    PLUS each row's (district, county) — a separate loop so the comparator's
    regression-locked loader stays untouched."""
    _s = hdt._s
    with hdt.ctc.exact_raw_rows(
            path, hdt.TSN_SHEET, hdt.TSN_RAW_HEADER, hdt.REPORT_NAME,
            required_nonblank=("DIST", "CNTY", "RTE", "POSTMILE")) as (header, rows_in):
        h = {n: i for i, n in enumerate(header)}
        rows, dcr = [], []
        di, ci = h.get("DIST"), h.get("CNTY")
        for r in rows_in:
            rows.append(hdt._tsn_row(r, h))
            dist = _s(r[di]) if di is not None and di < len(r) else ""
            cnty = _s(r[ci]).rstrip(".") if ci is not None and ci < len(r) else ""
            dcr.append((dist, cnty))
        return rows, dcr


def _project(raw_path):
    """Read the statewide workbook into the consolidated [Route]+SHARED_HEADER
    (+ sidecar) rows and build the success result (rows count + routes)."""
    base, dcr = tsn_rows_with_dcr(raw_path)
    rows = [row + list(dc) for row, dc in zip(base, dcr)]
    n_routes = len({r[0] for r in rows})

    def make_result(out_name):
        return ConsolidateResult(
            status="ok",
            message=f"Normalized {len(rows)} TSN Highway Detail rows ({n_routes} routes).",
            summary_lines=[f"TSN Highway Detail: {len(rows)} rows, {n_routes} routes "
                           f"-> {out_name}"],
            completion=outcome.COMPLETE,
            skipped_inputs=0,
            failed_inputs=0)

    return rows, make_result


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Project the raw TSN Highway Detail statewide workbook in `raw_dir` into
    the normalized workbook at `out_path` (sheet hdt.NORMALIZED_SHEET, header
    ['Route'] + hdt.SHARED_HEADER). Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        no_raw_what="TSN Highway Detail .xlsx",
        no_raw_hint="Import the statewide 'TSAR - HIGHWAY DETAIL' TSN export first.",
        log_label="TSN Highway Detail",
        sheet=hdt.NORMALIZED_SHEET,
        header=["Route"] + hdt.SHARED_HEADER + SIDECAR_HEADER,
        header_align={"horizontal": "center", "vertical": "center", "wrap_text": True},
        project=_project)
