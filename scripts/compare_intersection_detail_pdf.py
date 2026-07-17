"""PDF-sourced Intersection Detail comparisons (mirrors compare_highway_log_pdf).

Two "files"-kind comparison types over the regression-locked compare_core engine,
both reusing compare_intersection_detail_tsn's loaders + schema. The PDF-consolidated
TSMIS workbook has the IDENTICAL 36-column layout the Excel export produces, so
`_load_tsmis` reads it BY POSITION exactly the same way — no new loader is needed:

  * TSMIS_PDF_VS_TSN   — TSMIS (PDF) vs TSN. The PDF replaces the Excel as the
    TSMIS side (the PDF is parsed from this app's own "Intersection Detail (PDF)"
    export); the TSN side is unchanged.
  * TSMIS_PDF_VS_EXCEL — TSMIS (PDF) vs TSMIS (Excel). Diffs the two TSMIS sources
    of the SAME report to pinpoint exactly where they disagree (the reason the PDF
    path exists — like Highway Log, the two exports can differ).

Each overrides ONLY the two side labels (and, for the PDF-vs-Excel pair, drops the
TSN-specific Notes sheet); the engine's formula/label text is untouched, so the
compare_core regression lock stays intact. compare_core's `_xl_trim` collapses
internal space runs at compare time, so the Description's PDF-vs-Excel whitespace
artifacts (the Excel preserves source double-spaces the PDF render collapses) don't
flag as differences. The GUI's Compare tab drives these through COMPARE_REPORTS
("files" input kind); `file_a_label`/`file_b_label` name the two file pickers.
"""
from dataclasses import replace

import compare_intersection_detail_tsn as _id
from compare_tsn_common import (load_consolidated_rows, reject_pdf_source,
                                require_pdf_source, run_files_compare,
                                same_source_render_rows, suggest_route_name)


def _tsmis_row_same_source(r):
    """The same-source (PDF-vs-Excel) row projection: the 045 physical pairing
    key + Location-derived provenance are IDENTICAL to the vs-TSN projection
    (`_id._tsmis_row_with` owns the one body), but every VALUE cell is
    verbatim (`_id._v`) — the cross-system crosswalks (the control-type J→S
    fold, boolean/date/numeric reconciliation) exist to bridge TSN's
    encodings and must NOT erase render differences between two TSMIS renders
    of the SAME report (CMP-AUD-067). The flavor-level
    `same_source_render_rows` still applies the owner-ruled render
    equivalences (OOXML escapes, edge tab padding)."""
    return _id._tsmis_row_with(r, lambda _f, raw: _id._v(raw))


def _load_tsmis_same_source(path):
    return load_consolidated_rows(
        path, _id.TSMIS_SHEET,
        missing_sheet_hint="pick the consolidated TSMIS Intersection Detail workbook.",
        bad_header_msg="isn't a CONSOLIDATED Intersection Detail workbook in the "
                       "current (July 2026) site format — a leading 'Route' column "
                       "and the 'Xing Line Lgth' tail column are expected. "
                       "Consolidate a fresh post-update export; pre-update exports "
                       "used the old 36-column layout, which this version doesn't "
                       "compare.",
        header_ok=_id._header_ok,
        row_transform=_tsmis_row_same_source)


class _IntDetailFileCompare:
    """One Intersection-Detail file-vs-file comparison: compare(path_a, path_b, …)
    + suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. `load_b` is the loader for the SECOND
    file (the TSN loader for vs-TSN, the consolidated-TSMIS loader for vs-Excel);
    the first file is always the PDF-consolidated TSMIS workbook. The compare()
    skeleton lives in compare_tsn_common — this class is the schema override +
    the loader pairing. `same_source=True` (the PDF-vs-Excel self-check) applies
    the shared render-artifact equivalence at load: both sides render the SAME
    report, so the Excel export's OOXML escapes and edge tab padding are false
    positives, not data differences (owner ruling 2026-07-16 — the eight
    censused trailing-tab Descriptions like "HILLCREST RD\\t\\t"); the vs-TSN
    legs keep the accepted ID-79 byte-exact semantics."""

    def __init__(self, report_name, side_a, side_b, name_tag, load_b,
                 one_sided_note_extra=None, drop_notes=False, same_source=False,
                 excel_side_b=False, load_a=None):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._name_tag = name_tag
        self._load_a = load_a or _id._load_tsmis
        self._load_b = load_b
        self._same_source = same_source
        self._excel_side_b = excel_side_b   # CMP-AUD-066 role enforcement
        # Source Files provenance: side A is always the PDF export (.pdf); side B is
        # the Excel export (.xlsx) for the same-source self-check, and the statewide
        # TSN (no per-route source) otherwise.
        schema = replace(
            _id._SCHEMA, side_a=side_a, side_b=side_b,
            source_file_a=("intersection_detail", _id.TSMIS_SHEET, "pdf"),
            source_file_b=(("intersection_detail", _id.TSMIS_SHEET, "xlsx")
                           if excel_side_b else ()))
        if one_sided_note_extra is not None:
            schema = replace(schema, one_sided_note_extra=one_sided_note_extra)
        if drop_notes:
            # PDF-vs-Excel: both sides are TSMIS (1/0 booleans), so the TSN-specific
            # Notes sheet (which contrasts TSN Y/N vs TSMIS 1/0) doesn't apply.
            schema = replace(schema, legend_writer=None)
        self._schema = schema

    def suggest_name(self, path_a):
        return suggest_route_name(path_a, "Intersection_Detail", self._name_tag)

    def _load_pair(self, path_a, path_b):
        # CMP-AUD-066: the "TSMIS (PDF)" side must carry the PDF-conversion
        # marker; a vs-Excel second side must not (the TSN side keeps its own
        # normalization gate inside its loader).
        require_pdf_source(path_a, self.file_a_label, "Intersection Detail")
        if self._excel_side_b:
            reject_pdf_source(path_b, self.file_b_label, "Intersection Detail")
        rows_a, _ = self._load_a(path_a)   # PDF side: same 36-col consolidated layout
        rows_b, _ = self._load_b(path_b)
        if self._same_source:
            rows_a = same_source_render_rows(rows_a)
            rows_b = same_source_render_rows(rows_b)
        return rows_a, rows_b, None

    def compare(self, path_a, path_b, out_path, events=None, confirm_overwrite=None,
                mode="formulas", commit_guard=None):
        return run_files_compare(
            self._schema, path_a, path_b, out_path,
            banner=(f"Intersection Detail Comparison — {self.file_a_label} vs "
                    f"{self.file_b_label}"),
            has_route=True, loader=self._load_pair, deps_ok=_id._DEPS_OK,
            side_a=self.file_a_label, side_b=self.file_b_label,
            events=events, confirm_overwrite=confirm_overwrite, mode=mode,
            commit_guard=commit_guard)


TSMIS_PDF_VS_TSN = _IntDetailFileCompare(
    report_name="Intersection Detail — TSMIS (PDF) vs TSN",
    side_a="TSMIS (PDF)", side_b="TSN",
    name_tag="TSMIS_PDF_vs_TSN_IntersectionDetail",
    load_b=_id._load_tsn)

TSMIS_PDF_VS_EXCEL = _IntDetailFileCompare(
    report_name="Intersection Detail — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel_IntersectionDetail",
    load_a=_load_tsmis_same_source, load_b=_load_tsmis_same_source,
    one_sided_note_extra=" (intersections one source lists at a postmile the other doesn't)",
    drop_notes=True, same_source=True, excel_side_b=True)
