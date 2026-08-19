"""Highway Detail — the ArcGIS-built report vs the TSMIS export.

The third Highway Detail file comparison, beside vs-TSN and PDF-vs-Excel. Side A
is OUR Highway Detail rendered from the ArcGIS layer library
(`arcgis_report_highway_detail`, projected off the Clean Road CA HIGHWAYS build);
side B is the app's own consolidated Highway Detail export.

This one is TSMIS vs TSMIS: both sides describe the same network from the same
authority, so — unlike vs-TSN, which measures migration drift against a frozen
2025 snapshot — a difference here is either a gap in OUR reconstruction or a
genuine finding about the report. That is the whole point of the comparison, so
it is deliberately unforgiving:

  * VERBATIM values. The vs-TSN reconciliations (the NA 'A'→blank fold, numeric
    and length padding, the WDA glue, the whitespace collapse) exist to bridge
    TSN's encodings; the projection already emits the report's own print forms,
    so applying them here would hide exactly what we are looking for. Only the
    typed-date render equivalence is kept — openpyxl may type a date cell in one
    workbook and store text in the other, and the printed value is identical.
  * The ditto rule stays OFF. Neither side emits a `+` run (the projection never
    writes one and the Excel export expands them), so there is nothing to
    suppress, and leaving it on would forgive a stray marker.
  * The canonical roadbed-aware Post Mile is the pairing key, with the RAW
    printed token carried as its own compared cell (CMP-AUD-067), so a dropped
    R/L surfaces instead of hiding inside the key.

`RU Eff` is a CONTEXT column: the report prints the Rural/Urban effective date
and the CA HIGHWAYS table we build from carries no date column for the
population code, so ours is empty by construction. It is SHOWN with both sides'
values and never counted — counting it would only ever measure our own known
gap, on every row. See `arcgis_report_highway_detail.CONTEXT_COLUMNS`.

VINTAGE is the first thing to read on the Notes sheet. The ArcGIS side is a
reconstruction AS OF a chosen date; the TSMIS side is an export from a
particular day. Comparing across a gap measures network change, not correctness,
so the Notes state both dates and the comparison says so when they differ.

Console-free; engine in compare_core.
"""
import logging
from dataclasses import replace
from pathlib import Path

import arcgis_report_highway_detail as ah
import compare_highway_detail_tsn as _hd
import compare_tsn_common as ctc
from compare_tsn_common import (load_consolidated_rows, run_files_compare,
                                suggest_route_name)

log = logging.getLogger("tsmis.compare")

REPORT_NAME = "Highway Detail — ArcGIS vs TSMIS"
SIDE_A = "ArcGIS"
SIDE_B = "TSMIS"
file_a_label = SIDE_A
file_b_label = SIDE_B

# The vs-TSN shared header plus the raw printed postmile (CMP-AUD-067).
SHARED_HEADER = list(_hd.SHARED_HEADER) + ["PM (raw)"]
CONTEXT_FIELDS = tuple(ah.CONTEXT_COLUMNS)


def _project(field, raw):
    """Verbatim, except the typed-date render equivalence (see the module
    docstring). Both sides already carry the report's own print forms."""
    if field in _hd.DATE_FIELDS:
        return _hd._norm_date(raw)
    return _hd._s(_hd._v(raw))


def _row(r):
    return _hd._tsmis_row_with(r, _project,
                               extra=lambda _at, token: [_hd._s(_hd._v(token))])


def _load(path, what):
    return load_consolidated_rows(
        path, _hd.TSMIS_SHEET,
        missing_sheet_hint=f"pick the {what}.",
        bad_header_msg=f"isn't a Highway Detail workbook in the report's own "
                       f"34-column layout (expected a leading 'Route' column) — "
                       f"pick the {what}.",
        header_ok=ctc.exact_consolidated_header_ok(_hd._TSMIS_HEADER),
        row_transform=_row)


def _load_pair(arcgis_path, tsmis_path):
    """Both sides, with the ROLE of each enforced: the ArcGIS side must be a
    build this app produced (it carries the report-build marker sheet), and the
    TSMIS side must NOT be — swapping them would silently compare a workbook
    against itself's twin and read as agreement."""
    if not ah.is_arcgis_report(arcgis_path):
        raise ValueError(
            f"The {SIDE_A} side is not an ArcGIS-built Highway Detail workbook "
            f"(no '{ah.MARKER_SHEET}' sheet):\n{arcgis_path}\n\n"
            "Build it on the ArcGIS tab's Reports sub-tab first.")
    if ah.is_arcgis_report(tsmis_path):
        raise ValueError(
            f"The {SIDE_B} side is an ArcGIS-built workbook, not a TSMIS "
            f"export:\n{tsmis_path}\n\nPick the consolidated Highway Detail "
            "export for the day you want to compare against.")
    rows_a, _ = _load(arcgis_path, f"ArcGIS-built Highway Detail workbook")
    rows_b, _ = _load(tsmis_path, "consolidated TSMIS Highway Detail workbook")
    return rows_a, rows_b, None


# --------------------------------------------------------------------------- #
# Notes — what this comparison does and does not assert
# --------------------------------------------------------------------------- #
def _notes_lines(arcgis_path, tsmis_path):
    try:
        facts = ah.report_facts(arcgis_path)
    except Exception as e:   # silent-ok: the Notes sheet is documentation; an unreadable marker costs one stated date, never the comparison (the loaders gate the workbooks themselves)
        log.info("arcgis notes: build facts unreadable (%s: %s)",
                 type(e).__name__, e)
        facts = {}
    asof = facts.get("asof") or "(unknown)"
    export_day = _export_day(tsmis_path)
    lines = [
        ("§", "What this compares"),
        ("", f"Side A ({SIDE_A}) is Highway Detail rebuilt from the ArcGIS layer "
             f"library: the Clean Road CA HIGHWAYS build projected onto the "
             f"report's own 34 columns. Side B ({SIDE_B}) is the app's "
             f"consolidated Highway Detail export."),
        ("", "Both sides come from the same authority, so a difference is a gap "
             "in OUR reconstruction or a finding about the report — not "
             "migration drift. Values are compared VERBATIM (no cross-system "
             "normalization); only typed-vs-text dates are rendered alike."),
        ("§", "Vintage — read this before reading the counts"),
        ("", f"The ArcGIS side is a reconstruction AS OF {asof}. The TSMIS side "
             f"is the export of {export_day or 'an unrecorded day'}."),
        ("", "These must match for the comparison to measure correctness. Across "
             "a gap it measures network change instead: rebuild the Clean Road "
             "workbook with the as-of date set to the export's day, re-project, "
             "and compare again."),
        ("§", "Row identity"),
        ("", "Rows pair on the canonical roadbed-aware Post Mile (prefix + "
             "zero-padded mile + the R/L roadbed letter); the equation marker is "
             "compared as the separate 'PS' column, and the raw printed token as "
             "'PM (raw)', so neither can hide inside the key."),
        ("", "Highway Detail carries no county column, so a postmile that recurs "
             "in two counties on one route pairs county-blind (the CMP-AUD-045 "
             "disclosure); those keys are resolved by the engine's duplicate "
             "pairing."),
        ("§", "Row boundaries are not THY row boundaries"),
        ("", "CA HIGHWAYS segments on all 74 of its columns; Highway Detail "
             "prints 34. Adjacent spans that agree across every printed column "
             "are therefore merged into ONE record, and the printed Length is "
             "the merged span's end PM minus its begin PM. A description is "
             "start-anchored (landmarks are point features), so a following "
             "blank continues the record."),
        ("§", "Columns shown but NOT counted"),
        ("", f"{', '.join(CONTEXT_FIELDS)} — the report prints the Rural/Urban "
             "effective date, and the CA HIGHWAYS table carries the population "
             "CODE with no date column for it (TSN's own table doesn't either). "
             "Ours is empty by construction, so counting it would measure a "
             "known gap on every row. Both sides' values are still shown."),
        ("§", "Known weak spots in the reconstruction"),
        ("", "The three block effective dates (LB Eff / Med Eff / RB Eff) are "
             "composites the Clean Road build derives from its member layers' "
             "item dates — a candidate rule, not a proven one. They are the "
             "lowest-agreeing counted columns and are the first place to look "
             "when a run reports more differences than expected."),
    ]
    return lines


def _export_day(path):
    """The run day a consolidated export's own filename records, or ''."""
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(path).name)
    return m.group(1) if m else ""


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
    _hd._SCHEMA,
    report_name=REPORT_NAME,
    header=SHARED_HEADER,
    side_a=SIDE_A, side_b=SIDE_B,
    sides_noun="builds",
    context_fields=CONTEXT_FIELDS,
    context_header_fill="808080",     # the clean-road context tint
    # Both sides are non-TSN renders that expand everything: nothing to forgive.
    ditto_nonasserting=False, ditto_resolver=None,
    one_sided_note_extra=" (a postmile one side records and the other doesn't — "
                         "segmentation, or network change across the two dates)",
    data_widths=dict(_hd._SCHEMA.data_widths, **{"PM (raw)": 12}),
    cmp_widths=dict(_hd._SCHEMA.cmp_widths, **{"PM (raw)": 12}),
    source_file_a=(), source_file_b=(),
    legend_writer=None)


def suggest_name(arcgis_path):
    return suggest_route_name(arcgis_path, "Highway_Detail",
                              "ArcGIS_vs_TSMIS_HighwayDetail")


def compare(arcgis_path, tsmis_path, out_path, events=None,
            confirm_overwrite=None, mode="formulas", commit_guard=None):
    """Build the ArcGIS-vs-TSMIS Highway Detail discrepancy workbook(s)."""
    schema = replace(
        _SCHEMA,
        legend_writer=lambda wb: _write_notes(wb, arcgis_path, tsmis_path))
    return run_files_compare(
        schema, arcgis_path, tsmis_path, out_path,
        banner=f"Highway Detail Comparison — {SIDE_A} vs {SIDE_B}",
        has_route=True, loader=_load_pair, deps_ok=_hd._DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        side_a=SIDE_A, side_b=SIDE_B,
        events=events, confirm_overwrite=confirm_overwrite, mode=mode,
        commit_guard=commit_guard)
