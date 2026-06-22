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
import re
from dataclasses import replace
from pathlib import Path

import compare_intersection_detail_tsn as _id
from compare_core import run_compare
from events import ConsolidateResult, Events
from paths import today_str


class _IntDetailFileCompare:
    """One Intersection-Detail file-vs-file comparison: compare(path_a, path_b, …)
    + suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. `load_b` is the loader for the SECOND
    file (the TSN loader for vs-TSN, the consolidated-TSMIS loader for vs-Excel);
    the first file is always the PDF-consolidated TSMIS workbook."""

    def __init__(self, report_name, side_a, side_b, name_tag, load_b,
                 one_sided_note_extra=None, drop_notes=False):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._name_tag = name_tag
        self._load_b = load_b
        schema = replace(_id._SCHEMA, side_a=side_a, side_b=side_b)
        if one_sided_note_extra is not None:
            schema = replace(schema, one_sided_note_extra=one_sided_note_extra)
        if drop_notes:
            # PDF-vs-Excel: both sides are TSMIS (1/0 booleans), so the TSN-specific
            # Notes sheet (which contrasts TSN Y/N vs TSMIS 1/0) doesn't apply.
            schema = replace(schema, legend_writer=None)
        self._schema = schema

    def suggest_name(self, path_a):
        stem = Path(path_a).stem
        m = re.search(r"route[ _-]*([0-9]+[A-Za-z]?)", stem, re.IGNORECASE)
        tag = (f"Route{m.group(1).lstrip('0') or '0'}" if m
               else "Consolidated" if "consolidated" in stem.lower() else "Intersection_Detail")
        return f"{self._name_tag}_{tag}_Comparison {today_str()}.xlsx"

    def compare(self, path_a, path_b, out_path, events=None, confirm_overwrite=None,
                mode="formulas"):
        events = events or Events()
        if not _id._DEPS_OK:
            return ConsolidateResult(
                status="error", message="Required components are missing (openpyxl).")
        a, b = Path(path_a), Path(path_b)
        for p, side in ((a, self.file_a_label), (b, self.file_b_label)):
            if not p.is_file():
                return ConsolidateResult(
                    status="error", message=f"The {side} file doesn't exist:\n{p}")

        events.on_log("=" * 60)
        events.on_log(f"Intersection Detail Comparison — {self.file_a_label} vs "
                      f"{self.file_b_label}")
        events.on_log("=" * 60)
        events.on_log(f"{self.file_a_label}: {a.name}")
        events.on_log(f"{self.file_b_label}: {b.name}")
        events.on_log("")

        try:
            rows_a, _ = _id._load_tsmis(a)      # PDF side: same 36-col consolidated layout
            rows_b, _ = self._load_b(b)
        except ValueError as e:
            return ConsolidateResult(status="error", message=str(e))

        return run_compare(self._schema, rows_a, rows_b, True, out_path,
                           events=events, confirm_overwrite=confirm_overwrite,
                           mode=mode, name_a=a.name, name_b=b.name)


TSMIS_PDF_VS_TSN = _IntDetailFileCompare(
    report_name="Intersection Detail — TSMIS (PDF) vs TSN",
    side_a="TSMIS (PDF)", side_b="TSN",
    name_tag="TSMIS_PDF_vs_TSN_IntersectionDetail",
    load_b=_id._load_tsn)

TSMIS_PDF_VS_EXCEL = _IntDetailFileCompare(
    report_name="Intersection Detail — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel_IntersectionDetail",
    load_b=_id._load_tsmis,
    one_sided_note_extra=" (intersections one source lists at a postmile the other doesn't)",
    drop_notes=True)
