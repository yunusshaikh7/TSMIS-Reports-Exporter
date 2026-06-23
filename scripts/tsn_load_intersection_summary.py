"""Normalize the raw TSN Intersection Summary statewide PDF into the canonical TSN
library's reusable Category|Count workbook.

Parses the statewide PDF's 3-column category page once (via
compare_intersection_summary_tsn.parse_tsn_pdf) and writes a small normalized
workbook keyed on the canonical category keys, so the matrix + comparison read a
ready Excel instead of re-parsing the PDF. This module supplies the report-specific
glue (the projection + producer completion) and delegates the shared
find-raw/write/save skeleton to tsn_library.build_normalized (S04). Console-free.
"""
try:
    from openpyxl import Workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_intersection_summary_tsn as istsn
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.pdf"


def _project(raw_path):
    """Parse the statewide PDF into the TSN-applicable [Category, Count] rows (no
    TSMIS-only codes); a missing category makes the workbook PARTIAL (carried via
    skipped_inputs — P1-B05)."""
    counts = istsn.parse_tsn_pdf(raw_path)
    tsn_cats = istsn._SPEC.categories_for("tsn")     # TSN-applicable only (no TSMIS-only codes)
    missing = [key for key, slug in tsn_cats if counts.get(slug) is None]
    rows = [[key, int(counts.get(slug, 0) or 0)] for key, slug in tsn_cats]

    def make_result(out_name):
        summary = [f"TSN Intersection Summary: {len(rows)} categories -> {out_name}",
                   f"Total Intersections: {counts.get('total_intersections')}"]
        if missing:
            summary.insert(0, f"⚠ INCOMPLETE — {len(missing)} categor"
                           f"{'y' if len(missing) == 1 else 'ies'} not found in the PDF: "
                           + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
        return ConsolidateResult(
            status="ok",
            message=f"Normalized TSN Intersection Summary ({len(rows)} categories).",
            summary_lines=summary,
            completion=outcome.PARTIAL if missing else outcome.COMPLETE,
            skipped_inputs=len(missing))

    return rows, make_result


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Parse the raw TSN Intersection Summary statewide PDF into the normalized
    Category|Count workbook at `out_path`. Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (pdfplumber, openpyxl).",
        no_raw_what="TSN Intersection Summary .pdf",
        no_raw_hint="Import the statewide 'Intersection Summary Statewide' TSN export first.",
        log_label="TSN Intersection Summary",
        sheet=istsn.NORMALIZED_SHEET,
        header=["Category", "Count"],
        header_align={"horizontal": "center"},
        project=_project)
