"""PDF-sourced Highway Sequence comparisons (mirrors compare_highway_detail_pdf).

Two "files"-kind comparison types over the regression-locked compare_core engine,
both reusing compare_highway_sequence_tsn's loaders + schema. The PDF-consolidated
TSMIS workbook has the IDENTICAL 10-column layout the Excel export produces
(Route + the 9 export columns, the postmile prefix/suffix in their two unnamed
columns), so `_load_tsmis` reads it BY POSITION exactly the same way — no new
loader is needed:

  * TSMIS_PDF_VS_TSN   — TSMIS (PDF) vs TSN. The PDF replaces the Excel as the
    TSMIS side (the PDF is parsed from this app's own "Highway Sequence Listing
    (PDF)" export); the TSN side is unchanged. At EQUATE points the print uses
    the SAME convention the TSN prints do (an "EQUATES TO …" annotation row with
    no flag, the "E" suffix on the equated plain postmile), so the PDF side
    pairs BETTER there than the Excel side: the Excel edition's by-design
    "H ≠ (blank)" FT class disappears, and the equated postmiles key-match.
  * TSMIS_PDF_VS_EXCEL — TSMIS (PDF) vs TSMIS (Excel). Diffs the two TSMIS
    renders of the SAME report to prove both exports carry the same data (and
    to pinpoint exactly where they disagree when they don't — the statewide
    census caught the Excel export dropping a Description the print carries).

Each overrides ONLY the two side labels and the Notes sheet (each flavor gets
notes describing ITS by-design classes); the engine's formula/label text is
untouched, so the compare_core regression lock stays intact. The GUI's Compare
tab drives these through COMPARE_REPORTS ("files" input kind);
`file_a_label`/`file_b_label` name the two file pickers.
"""
from dataclasses import replace

import compare_highway_sequence_tsn as _hsl
import compare_tsn_common as ctc
from compare_tsn_common import run_files_compare, suggest_route_name

# The vs-TSN notes, adjusted for the PDF-sourced TSMIS side: the key/context
# bullets carry over verbatim; the equate bullet describes the PRINT convention
# (which matches TSN's, unlike the Excel export's).
_NOTES_PDF_VS_TSN = ctc.make_notes_writer(
    "Highway Sequence — TSMIS (PDF) vs TSN: comparison notes",
    (
        "Rows are keyed on Route + County + Postmile. California postmiles are "
        "county-relative (a route restarts at 000.000 in each county it crosses), so "
        "the postmile alone is not unique across a route — County is part of the key.",
        "The postmile carries a glued realignment prefix (\"R000.129\") and/or an equate "
        "suffix (\"050.025E\"); the TSMIS prefix/PM/suffix columns are re-glued to match.",
        "One-sided rows are expected and honest: TSN lists every segment break (including "
        "unnamed ones), while TSMIS omits most unnamed breaks.",
        "At EQUATE points the TSMIS print uses the SAME convention as the TSN print — an "
        "annotation row at the realignment postmile with no feature type, plus the \"E\" "
        "suffix on the equated plain postmile — so equates mostly pair up cleanly here. "
        "The annotation descriptions still differ on purpose: the TSMIS print writes "
        "\"EQUATES TO <label>\" (or just \"EQUATES TO\") where TSN writes the bare "
        "\"EQUATES TO\".",
        "CONTEXT columns (shown for reference, never counted as a difference): HG (TSMIS "
        "leaves the highway-group blank for whole counties while TSN always fills it); City "
        "(TSN assigns a city code far more aggressively than TSMIS); and Distance To Next "
        "Point (measured to each system's OWN next listed point — since TSN lists more breaks, "
        "its gap is usually smaller, an artifact of listing granularity rather than a real "
        "disagreement). Counting these would bury the substantive differences. FT and "
        "Description (with the TSMIS leading \"<route>/\" prefix stripped) ARE compared.",
    ))

# The PDF-vs-Excel self-check notes: both sides are TSMIS, so the TSN bullets
# don't apply — what DOES need explaining is the two renders' by-design equate
# representations (censused statewide: they account for nearly every diff).
_NOTES_PDF_VS_EXCEL = ctc.make_notes_writer(
    "Highway Sequence — TSMIS (PDF) vs TSMIS (Excel): comparison notes",
    (
        "Both sides are TSMIS — the same report rendered two ways (the site's Print "
        "layout vs the Excel export). Apart from the known classes below, every cell "
        "should match; a residual difference means the two renders genuinely disagree "
        "(the statewide census caught the Excel export dropping a Description that "
        "the print carries).",
        "EQUATE points are represented differently BY DESIGN, so each equate surfaces "
        "as a small cluster of differences: the print writes an annotation row "
        "\"EQUATES TO <label>\" with HG / FT / Distance blank, where the Excel export "
        "writes the label alone (\"END R REALIGNMENT\", \"PM EQUATION\", …) and keeps "
        "the flags; and the print seats the \"E\" suffix on the EQUATED plain postmile "
        "(the TSN convention) where the Excel export often seats it on the realignment "
        "row — those rows then key differently and appear one-sided on both sides.",
        "The print is an HTML render, so whitespace runs inside a Description collapse "
        "to one space; the comparison collapses both sides, so padding never counts. A "
        "handful of Excel cells carry a literal line-break escape (\"_x000D_\") the "
        "print omits — those surface honestly as Description differences.",
    ))


class _HighwaySequenceFileCompare:
    """One Highway-Sequence file-vs-file comparison: compare(path_a, path_b, …) +
    suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. `load_b` is the loader for the SECOND
    file (the TSN loader for vs-TSN, the consolidated-TSMIS loader for
    vs-Excel); the first file is always the PDF-consolidated TSMIS workbook."""

    def __init__(self, report_name, side_a, side_b, name_tag, load_b,
                 legend_writer, one_sided_note_extra=None):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._name_tag = name_tag
        self._load_b = load_b
        schema = replace(_hsl._SCHEMA, side_a=side_a, side_b=side_b,
                         legend_writer=legend_writer)
        if one_sided_note_extra is not None:
            schema = replace(schema, one_sided_note_extra=one_sided_note_extra)
        self._schema = schema

    def suggest_name(self, path_a):
        return suggest_route_name(path_a, "Highway_Sequence", self._name_tag)

    def _load_pair(self, path_a, path_b):
        rows_a, _ = _hsl._load_tsmis(path_a)   # PDF side: same 10-col consolidated layout
        rows_b, _ = self._load_b(path_b)
        return rows_a, rows_b, None

    def compare(self, path_a, path_b, out_path, events=None, confirm_overwrite=None,
                mode="formulas", commit_guard=None):
        return run_files_compare(
            self._schema, path_a, path_b, out_path,
            banner=(f"Highway Sequence Comparison — {self.file_a_label} vs "
                    f"{self.file_b_label}"),
            has_route=True, loader=self._load_pair, deps_ok=_hsl._DEPS_OK,
            side_a=self.file_a_label, side_b=self.file_b_label,
            events=events, confirm_overwrite=confirm_overwrite, mode=mode,
            commit_guard=commit_guard)


TSMIS_PDF_VS_TSN = _HighwaySequenceFileCompare(
    report_name="Highway Sequence — TSMIS (PDF) vs TSN",
    side_a="TSMIS (PDF)", side_b="TSN",
    name_tag="TSMIS_PDF_vs_TSN_HighwaySequence",
    load_b=_hsl._load_tsn,
    legend_writer=_NOTES_PDF_VS_TSN)

TSMIS_PDF_VS_EXCEL = _HighwaySequenceFileCompare(
    report_name="Highway Sequence — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel_HighwaySequence",
    load_b=_hsl._load_tsmis,
    legend_writer=_NOTES_PDF_VS_EXCEL,
    one_sided_note_extra=(" (mostly the equate rows — the two renders seat the "
                          "\"E\" suffix on different rows, see Notes)"))
