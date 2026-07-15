"""Normalize the raw TSN Ramp Summary statewide PDF into the canonical TSN
library's reusable comparison form.

The TSN Ramp Summary source is a single statewide PDF (one category-count page).
"Consolidating" it means parsing that page once into a small [Category, Count]
workbook, so every Ramp Summary comparison (and the matrix) reads a ready Excel
instead of re-parsing the PDF. The parse (geometry + the 16-ramp-type schema) and
the canonical category list live in compare_ramp_summary_tsn — this module supplies
the report-specific glue (the projection + the producer completion) and delegates
the shared find-raw/write/save skeleton to tsn_library.build_normalized (S04).

Console-free; pdfplumber + openpyxl. The library calls build_into lazily.
"""
try:
    from openpyxl import Workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_ramp_summary_tsn as rstsn
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.pdf"


def _project(raw_path):
    """Parse the statewide PDF into the canonical [Category, Count] rows; a category
    the PDF didn't yield makes the workbook PARTIAL (carried structurally via
    skipped_inputs, not just the warning line — P1-B05)."""
    counts = rstsn.parse_tsn_pdf(raw_path)
    # CMP-AUD-146: capture the print's identity claims (report id/dates/
    # submitter/event/generation time) — an unidentifiable print refuses.
    claims = rstsn.parse_tsn_source_claims(raw_path)
    missing = [key for key, slug in rstsn._CATEGORIES if counts.get(slug) is None]
    # A category the PDF didn't yield is OMITTED, never written as a fabricated
    # zero (CMP-AUD-021 absent-vs-zero): the comparator's validation then refuses
    # the incomplete table loudly instead of comparing invented counts.
    rows = [[key, int(counts[slug])] for key, slug in rstsn._CATEGORIES
            if counts.get(slug) is not None]

    def make_result(out_name):
        summary = [f"TSN Ramp Summary: {len(rows)} categories -> {out_name}",
                   f"Total Number of Ramps: {counts.get('total_ramps')}"]
        if missing:
            summary.insert(0, f"⚠ INCOMPLETE — {len(missing)} categor"
                           f"{'y' if len(missing) == 1 else 'ies'} not found in the PDF: "
                           + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
        return ConsolidateResult(
            status="ok",
            message=f"Normalized TSN Ramp Summary ({len(rows)} categories).",
            summary_lines=summary,
            completion=outcome.PARTIAL if missing else outcome.COMPLETE,
            skipped_inputs=len(missing),
            producer_extra={"tsn_source_claims": claims})

    return rows, make_result


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Parse the raw TSN Ramp Summary statewide PDF in `raw_dir` into the normalized
    [Category, Count] workbook at `out_path` (sheet rstsn.NORMALIZED_SHEET, keyed on
    the canonical category keys). Returns a ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (pdfplumber, openpyxl).",
        no_raw_what="TSN Ramp Summary .pdf",
        no_raw_hint="Import the statewide 'Ramp Summary Statewide' TSN export first.",
        log_label="TSN Ramp Summary",
        sheet=rstsn.NORMALIZED_SHEET,
        header=["Category", "Count"],
        header_align={"horizontal": "center", "vertical": "center"},
        project=_project)
