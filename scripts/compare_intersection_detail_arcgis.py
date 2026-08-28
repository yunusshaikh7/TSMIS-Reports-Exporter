"""Intersection Detail — the ArcGIS-built report vs the TSMIS export.

The fourth Intersection Detail file comparison, beside PDF-vs-TSN, Excel-vs-TSN
and the PDF-vs-Excel self-check. Side A is OUR Intersection Detail rendered from
the ArcGIS layer library (`arcgis_report_intersection_detail`); side B is the
app's own consolidated Intersection Detail export.

This one is TSMIS vs TSMIS. Both sides describe the same intersections from the
same authority, so — unlike vs-TSN, which measures migration drift against a
frozen 2025 snapshot that can never be refreshed — a difference here is either a
gap in OUR reconstruction or a genuine finding about how the report is built.
That is the entire point of the comparison, so it is deliberately unforgiving:

  * VERBATIM values. The vs-TSN reconciliations (the control-type J-P -> S
    crosswalk, the boolean 1/0 fold, numeric padding) exist to bridge TSN's
    encodings; the projection already emits the report's own print forms, so
    applying them here would hide exactly what we are looking for. Only two
    equivalences survive, and both are render-level: dates compare on their
    rendered value (typed vs text), and the owner-ruled same-source render
    artifacts (the Excel export's OOXML escapes and edge tab padding) stay
    forgiven, because they are how a value was WRITTEN, not what it says.
  * No Report View. The vs-TSN flavor's replica classifies Int St / ML / CS
    Eff-Date as "soft" differences, which is a TSN convention: TSN stamps them
    in bulk where TSMIS keeps the historical date. Between two TSMIS renders
    those dates must be IDENTICAL, so carrying that classification here would
    excuse a real finding (the same reasoning the PDF-vs-Excel self-check uses).
  * No context columns. Every column this report prints has a real layer source
    — including `Int St Eff-Date`, which is `InventoryItemStartDate` on the
    intersection row and reproduces exactly. See the build module's docstring.

VINTAGE is the first thing to read on the Notes sheet. The ArcGIS side is a
reconstruction AS OF a chosen date; the TSMIS side is an export from a
particular day. Comparing across a gap measures network change, not correctness,
so the Notes state both dates.

Console-free; engine in compare_core.
"""
import logging
import re
from dataclasses import replace
from pathlib import Path

import arcgis_report_intersection_detail as ari
import compare_intersection_detail_tsn as _id
import compare_tsn_common as ctc
from compare_tsn_common import (load_consolidated_rows, run_files_compare,
                                same_source_render_rows, suggest_route_name)

log = logging.getLogger("tsmis.compare")

REPORT_NAME = "Intersection Detail — ArcGIS vs TSMIS"
SIDE_A = "ArcGIS"
SIDE_B = "TSMIS"
file_a_label = SIDE_A
file_b_label = SIDE_B

SHARED_HEADER = list(_id.SHARED_HEADER)
# The build has no column without a source, so nothing is shown-but-not-counted.
CONTEXT_FIELDS = tuple(ari.CONTEXT_COLUMNS)


def _project(field, raw):
    """Verbatim, except that dates compare on their RENDERED value.

    Both sides already carry the report's own print forms, so no crosswalk is
    wanted. A date is the one cell whose two spellings ('73-10-19' typed as a
    date in one workbook, the same text in the other) mean the same printed
    thing, and `_iso_date` is the projection the vs-TSN legs already trust."""
    if field in _id.DATE_FIELDS:
        return _id._iso_date(raw)
    return _id._v(raw)


def _row(r):
    """One consolidated row. The 045 physical pairing key and the
    Location-derived provenance come from `_id._tsmis_row_with` — the one body
    every Intersection Detail flavor shares — so identity cannot drift between
    this comparison and the others."""
    return _id._tsmis_row_with(r, _project)


def _load(path, what):
    return load_consolidated_rows(
        path, _id.TSMIS_SHEET,
        missing_sheet_hint=f"pick the {what}.",
        bad_header_msg="isn't a CONSOLIDATED Intersection Detail workbook in the "
                       "current (July 2026) site format — a leading 'Route' "
                       "column and the 'Xing Line Lgth' tail column are "
                       f"expected. Pick the {what}.",
        header_ok=_id._header_ok,
        row_transform=_row)


def _load_pair(arcgis_path, tsmis_path):
    """Both sides, with the ROLE of each enforced: the ArcGIS side must be a
    build this app produced (it carries the report-build marker sheet), and the
    TSMIS side must NOT be — swapping them would compare a build against itself
    and read as agreement."""
    if not ari.is_arcgis_report(arcgis_path):
        raise ValueError(
            f"The {SIDE_A} side is not an ArcGIS-built Intersection Detail "
            f"workbook (no '{ari.MARKER_SHEET}' sheet):\n{arcgis_path}\n\n"
            "Build it on the ArcGIS tab's Reports sub-tab first.")
    if ari.is_arcgis_report(tsmis_path):
        raise ValueError(
            f"The {SIDE_B} side is an ArcGIS-built workbook, not a TSMIS "
            f"export:\n{tsmis_path}\n\nPick the consolidated Intersection "
            "Detail export for the day you want to compare against.")
    rows_a, _ = _load(arcgis_path, "ArcGIS-built Intersection Detail workbook")
    rows_b, _ = _load(tsmis_path, "consolidated TSMIS Intersection Detail workbook")
    # The owner-ruled render equivalences (OOXML escapes, edge tab padding) are
    # about how a value was WRITTEN by two renders of one report — exactly this
    # situation. Applied to BOTH sides, as the PDF-vs-Excel self-check does.
    return same_source_render_rows(rows_a), same_source_render_rows(rows_b), None


# --------------------------------------------------------------------------- #
# Notes — what this comparison does and does not assert
# --------------------------------------------------------------------------- #
def _export_day(path):
    """The run day a consolidated export's own filename records, or ''."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(path).name)
    return m.group(1) if m else ""


def _notes_lines(arcgis_path, tsmis_path):
    try:
        facts = ari.report_facts(arcgis_path)
    except Exception as e:   # silent-ok: the Notes sheet is documentation; an unreadable marker costs one stated date, never the comparison (the loaders gate the workbooks themselves)
        log.info("arcgis notes: build facts unreadable (%s: %s)",
                 type(e).__name__, e)
        facts = {}
    asof = facts.get("asof") or "(unknown)"
    export_day = _export_day(tsmis_path)
    return [
        ("§", "What this compares"),
        ("", f"Side A ({SIDE_A}) is Intersection Detail rebuilt from the ArcGIS "
             f"layer library — the IM intersection layers rendered into the "
             f"report's own 35 columns. Side B ({SIDE_B}) is the app's "
             f"consolidated Intersection Detail export."),
        ("", "Both sides come from the same authority, so a difference is a gap "
             "in OUR reconstruction or a finding about the report — never "
             "migration drift. That is what this comparison is for: it "
             "separates a real data discrepancy from an artifact of how the "
             "report is assembled."),
        ("", "Values are compared VERBATIM. The cross-system crosswalks the "
             "vs-TSN comparison applies (the control-type J-P fold, the "
             "boolean 1/0 reconciliation, numeric padding) are deliberately NOT "
             "applied — they exist to bridge TSN's encodings and would hide "
             "what is being looked for here. Only dates compare on their "
             "rendered value, and the same-source render artifacts (the Excel "
             "export's escapes and edge tab padding) stay forgiven."),
        ("§", "Vintage — read this before reading the counts"),
        ("", f"The ArcGIS side is a reconstruction AS OF {asof}. The TSMIS side "
             f"is the export of {export_day or 'an unrecorded day'}."),
        ("", "These must match for the comparison to measure correctness. Across "
             "a gap it measures network change instead: rebuild on the ArcGIS "
             "tab with the as-of date set to the export's day and compare again."),
        ("§", "Row identity"),
        ("", "Rows pair on the physical location — base route, county, postmile "
             "prefix and postmile. The route suffix is compared as its own "
             "column rather than keyed on, so a suffix difference surfaces "
             "instead of splitting a pair."),
        ("§", "Which rows the build renders"),
        ("", f"The IM Intersection Detail layer holds far more rows than the "
             f"report prints: most are IM-managed shells with the whole "
             f"inventory half empty — no route, no postmile, no attributes. The "
             f"build renders the rows that carry a Main postmile and are current "
             f"(not retired, no inventory end date): "
             f"{facts.get('rows', '?')} records across "
             f"{facts.get('routes', '?')} routes, having skipped "
             f"{facts.get('shells', '?')} shells and "
             f"{facts.get('retired', '?')} retired rows."),
        ("§", "Where the mainline and cross-street columns come from"),
        ("", "The report prints one mainline and one cross-street value for mast "
             "arm, channelization, flow, lanes and length, while the layers "
             "carry several approach legs per intersection. The build takes the "
             f"mainline block from the '{ari.MAIN_LEG}' legs and the "
             f"cross-street block from the '{ari.CROSS_LEG}' legs — measured "
             "across the statewide population at 99.4-100% against the export, "
             "where the reverse assignment lands 62-96%. Where legs of one type "
             "disagree with each other, the most frequent value is printed."),
        ("§", "Columns shown but NOT counted"),
        ("", "None. Every column this report prints has a real layer source, so "
             "every column is counted. (Highway Detail's equivalent comparison "
             "once showed 'RU Eff' uncounted for want of a source; the same "
             "question was asked here of 'Int St Eff-Date' and the answer was "
             "that it is InventoryItemStartDate on the intersection row, which "
             "reproduces exactly.)"),
        ("§", "Known weak spots in the reconstruction"),
        ("", "ML Eff-Date and CS Eff-Date are the lowest-agreeing counted "
             "columns and are the first place to look when a run reports more "
             "differences than expected. In the measured baseline the export "
             "frequently prints a legacy default date where the layer carries a "
             "real one — which is a finding about the report, not a build gap, "
             "and is precisely the distinction this comparison exists to draw."),
    ]


def _write_notes(wb, arcgis_path, tsmis_path):
    """The Notes sheet: section headings are marked '§' in `_notes_lines` and
    render as a blank line + the heading, so the sheet reads as sections."""
    body = []
    for mark, text in _notes_lines(arcgis_path, tsmis_path):
        if mark == "§":
            if body:
                body.append("")
            body.append(text.upper())
        else:
            body.append(text)
    writer = ctc.make_notes_writer(
        f"{REPORT_NAME} — how to read this comparison", body)
    return writer(wb)


# --------------------------------------------------------------------------- #
_SCHEMA = replace(
    _id._SCHEMA,
    report_name=REPORT_NAME,
    side_a=SIDE_A, side_b=SIDE_B,
    sides_noun="builds",
    context_fields=CONTEXT_FIELDS,
    one_sided_note_extra=" (an intersection one side records at a postmile the "
                         "other doesn't — a row-universe difference, or network "
                         "change across the two dates)",
    source_file_a=(), source_file_b=(),
    legend_writer=None)


def suggest_name(arcgis_path):
    return suggest_route_name(arcgis_path, "Intersection_Detail",
                              "ArcGIS_vs_TSMIS_IntersectionDetail")


def compare(arcgis_path, tsmis_path, out_path, events=None,
            confirm_overwrite=None, mode="formulas", commit_guard=None):
    """Build the ArcGIS-vs-TSMIS Intersection Detail discrepancy workbook(s)."""
    schema = replace(
        _SCHEMA,
        legend_writer=lambda wb: _write_notes(wb, arcgis_path, tsmis_path))
    return run_files_compare(
        schema, arcgis_path, tsmis_path, out_path,
        banner=f"Intersection Detail Comparison — {SIDE_A} vs {SIDE_B}",
        has_route=True, loader=_load_pair, deps_ok=_id._DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        side_a=SIDE_A, side_b=SIDE_B,
        events=events, confirm_overwrite=confirm_overwrite, mode=mode,
        commit_guard=commit_guard)
