"""Normalize the raw TSN Highway Summary statewide print into the canonical TSN
library's reusable comparison form.

The TSN Highway Summary source is a single statewide PDF (a two-column
category-mileage document). "Consolidating" it means parsing it once into a small
[Category, Miles] workbook, so every Highway Summary comparison (and the matrix)
reads a ready Excel instead of re-parsing the print. The parse (the two-column
region geometry + the shared code taxonomy) lives in compare_highway_summary_tsn
and highway_summary_columns — this module supplies the report-specific glue (the
projection + the producer completion) and delegates the shared
find-raw/write/save skeleton to tsn_library.build_normalized (S04), exactly like
the Ramp / Intersection Summary loaders.

Console-free; pdfplumber + openpyxl. The library calls build_into lazily.
"""
try:
    from openpyxl import Workbook  # noqa: F401  (deps probe; tsn_library writes the workbook)
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_highway_summary_tsn as hstsn
import highway_summary_columns as hsc
import outcome
import tsn_library
from events import ConsolidateResult

RAW_GLOB = "*.pdf"


def _project(raw_path):
    """Parse the statewide print into the canonical [Category, Miles] rows.

    A category the print states no mileage for is OMITTED, never written as a
    fabricated zero (CMP-AUD-021 absent-vs-zero) — the statewide print masks a
    value that overflows its column width with `**********`, and on the bound
    2025-09-15 print that is exactly `MEDIAN BARRIER: Z- NO BARRIER`. The
    comparison then shows it one-sided instead of comparing an invented figure.
    """
    values = hstsn.parse_tsn_pdf(raw_path)
    # CMP-AUD-146: capture the print's identity claims (report id/dates/
    # submitter/event/generation time) — an unidentifiable print refuses.
    claims = hstsn.parse_tsn_source_claims(raw_path)
    expected = [(c.key, c.slug) for c in hsc.cats_for("tsn")]
    missing = [key for key, slug in expected if values.get(slug) is None]
    rows = [[key, hsc.miles(values[slug])]
            for key, slug in hstsn._CATEGORIES if values.get(slug) is not None]

    def make_result(out_name):
        total = values.get(hsc.TOTAL_SLUG)
        summary = [f"TSN Highway Summary: {len(rows)} categories -> {out_name}",
                   f"{hsc.TOTAL_LABEL}: "
                   + (f"{hsc.miles(total):,.3f}" if total is not None else "not stated")]
        if missing:
            summary.insert(
                0, f"⚠ INCOMPLETE — {len(missing)} categor"
                   f"{'y' if len(missing) == 1 else 'ies'} carried no mileage in the "
                   "print (a masked '**********' value is omitted, never zeroed): "
                   + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
        return ConsolidateResult(
            status="ok",
            message=f"Normalized TSN Highway Summary ({len(rows)} categories).",
            summary_lines=summary,
            completion=outcome.PARTIAL if missing else outcome.COMPLETE,
            skipped_inputs=len(missing),
            producer_extra={"tsn_source_claims": claims})

    return rows, make_result


def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Parse the raw TSN Highway Summary statewide PDF in `raw_dir` into the
    normalized [Category, Miles] workbook at `out_path` (sheet
    hstsn.NORMALIZED_SHEET, keyed on the canonical category keys). Returns a
    ConsolidateResult."""
    return tsn_library.build_normalized(
        raw_dir, out_path, events=events, confirm_overwrite=confirm_overwrite,
        glob=RAW_GLOB, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (pdfplumber, openpyxl).",
        no_raw_what="TSN Highway Summary .pdf",
        no_raw_hint="Import the statewide 'Highway Summary Statewide' TSN export first.",
        log_label="TSN Highway Summary",
        sheet=hstsn.NORMALIZED_SHEET,
        header=["Category", "Miles"],
        header_align={"horizontal": "center", "vertical": "center"},
        project=_project)
