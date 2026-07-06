"""PDF-sourced Highway Log comparisons that sidestep the buggy vendor Excel.

Two "files"-kind comparison types over the regression-locked compare_core
engine, both consuming two 31-column Highway Log workbooks (per-route OR
consolidated — exactly the shapes compare_highway_log already accepts, so this
reuses its loader and schema):

  * TSMIS_PDF_VS_TSN    — TSMIS (PDF) vs TSN. The accurate replacement for the
    Excel-based TSMIS-vs-TSN comparison: BOTH sides are parsed from PDFs
    (consolidate_tsmis_highway_log_pdf + consolidate_tsn_highway_log), so the
    vendor Excel export's data-integrity bug never enters the comparison.
  * TSMIS_PDF_VS_EXCEL  — TSMIS (PDF) vs TSMIS (Excel). Diffs the PDF-parsed
    data against the vendor Excel export of the SAME report, pinpointing exactly
    which cells/rows the Excel export is getting wrong.

Each overrides ONLY the two side labels and the report-specific notes; the
engine's formula/label text is untouched, so the compare_core regression lock
stays intact. The GUI's Compare tab drives these through COMPARE_REPORTS
("files" input kind); `file_a_label`/`file_b_label` name the two file pickers so
the PDF-vs-Excel pair doesn't mislabel both TSMIS sides as "TSMIS"/"TSN".
"""
from dataclasses import replace

import compare_highway_log as _hl
from compare_tsn_common import run_files_compare, suggest_route_name


class _HighwayLogFileCompare:
    """One Highway-Log file-vs-file comparison: compare(path_a, path_b, …) +
    suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. The compare() skeleton and the pair
    loader live in compare_tsn_common / compare_highway_log — this class is
    just the schema override + the labels."""

    def __init__(self, report_name, side_a, side_b, name_tag,
                 one_sided_note_extra="", trim_note_extra=""):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._name_tag = name_tag
        # Reuse the approved Highway Log schema; override only the side names and
        # the report-specific notes (compare_core's formula/label text is
        # regression-locked and is NOT touched here).
        self._schema = replace(_hl._SCHEMA, side_a=side_a, side_b=side_b,
                               one_sided_note_extra=one_sided_note_extra,
                               trim_note_extra=trim_note_extra)

    def suggest_name(self, path_a):
        """Output filename suggestion, route- / consolidated-aware, with a
        generated-on date stamp (A1)."""
        return suggest_route_name(path_a, "Highway_Log", self._name_tag)

    def compare(self, path_a, path_b, out_path, events=None,
                confirm_overwrite=None, mode="formulas"):
        """Build the comparison workbook(s). Same contract as the other
        comparison modules (ConsolidateResult returned)."""
        return run_files_compare(
            self._schema, path_a, path_b, out_path,
            banner=(f"Highway Log Comparison — {self.file_a_label} vs "
                    f"{self.file_b_label}"),
            has_route=None, loader=_hl._load_pair, deps_ok=_hl._DEPS_OK,
            side_a=self.file_a_label, side_b=self.file_b_label,
            events=events, confirm_overwrite=confirm_overwrite, mode=mode)


TSMIS_PDF_VS_TSN = _HighwayLogFileCompare(
    report_name="Highway Log — TSMIS (PDF) vs TSN (PDF)",
    # Both sides are parsed from PDFs; "(PDF)" on the TSN side too makes the
    # PDF-vs-PDF nature unmistakable (the TSN side comes from the TSN district
    # PDF consolidation). This labels the data sheets / file pickers / banners.
    side_a="TSMIS (PDF)", side_b="TSN (PDF)",
    name_tag="TSMIS_PDF_vs_TSN",
    one_sided_note_extra=" (mostly TSN segment splits and TSMIS realignment "
                         "markers)")

TSMIS_PDF_VS_EXCEL = _HighwayLogFileCompare(
    report_name="Highway Log — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel",
    one_sided_note_extra=" (rows the Excel export added or dropped relative to "
                         "the PDF — a sign of the export bug)",
    trim_note_extra=" — the TSMIS Excel export pads Description with trailing "
                    "blanks")
