"""PDF-sourced Highway Sequence comparisons (mirrors compare_highway_detail_pdf).

Two "files"-kind comparison types over the regression-locked compare_core engine.
The PDF-consolidated TSMIS workbook has the IDENTICAL 10-column layout the Excel
export produces (Route + the 9 export columns, the postmile prefix/suffix in
their two unnamed columns), so both flavors read it BY POSITION:

  * TSMIS_PDF_VS_TSN   — TSMIS (PDF) vs TSN, riding compare_highway_sequence_tsn's
    loaders/schema unchanged (full glued-postmile identity incl. the equate
    suffix; TSMIS own-route label stripped; TSN Descriptions verbatim). At
    EQUATE points the print uses the SAME convention the TSN prints do, so the
    PDF side pairs BETTER there than the Excel side.
  * TSMIS_PDF_VS_EXCEL — TSMIS (PDF) vs TSMIS (Excel), the same-report
    self-check. CMP-AUD-199: the two renders seat the equate "E" suffix on
    DIFFERENT rows of an equate pair BY DESIGN, so the suffix is NOT identity
    here — rows key on Route + County + the prefixed postmile WITHOUT the
    suffix, and "PM Suffix" is its own compared column (each moved equate = two
    honest suffix cells instead of four fabricated one-sided rows; the census
    proved one route-152 duplicate group where suffix-glued keys silently
    swapped two different physical rows). Both sides are the same system, so
    EVERY column is asserted (no context suppression) and Descriptions are
    compared verbatim (no route-label stripping on either side).

Each flavor owns its Notes sheet; the engine's formula/label text is untouched,
so the compare_core regression lock stays intact. The GUI's Compare tab drives
these through COMPARE_REPORTS ("files" input kind); `file_a_label`/
`file_b_label` name the two file pickers.
"""
from dataclasses import replace

import compare_highway_sequence_tsn as _hsl
import compare_tsn_common as ctc
from compare_core import CompareSchema
from compare_tsn_common import (load_consolidated_rows, run_files_compare,
                                suggest_route_name)

# The vs-TSN notes, adjusted for the PDF-sourced TSMIS side: the key/context/
# description bullets carry over; the equate bullet describes the PRINT
# convention (which matches TSN's, unlike the Excel export's).
_NOTES_PDF_VS_TSN_TITLE = "Highway Sequence — TSMIS (PDF) vs TSN: comparison notes"
_NOTES_PDF_VS_TSN = (
    "Rows are keyed on Route + County + Postmile. California postmiles are "
    "county-relative (a route restarts at 000.000 in each county it crosses), so "
    "the postmile alone is not unique across a route — County is part of the key.",
    "The postmile carries a glued realignment prefix (\"R000.129\") and/or an equate "
    "suffix (\"050.025E\"); the TSMIS prefix/PM/suffix columns are re-glued to match.",
    "A handful of rows print with NO county (46 statewide TSN \"EQUATES TO\" "
    "annotations that appear before the route's first county-bearing row — TSN's own "
    "cover warns equate ownership may be wrong) or NO postmile (five TSMIS rows). "
    "They key under the explicit \"(county not printed)\" / \"(no postmile printed)\" "
    "markers and surface honestly, usually one-sided — never dropped or backfilled.",
    "One-sided rows are expected and honest: TSN lists every segment break (including "
    "unnamed ones), while TSMIS omits most unnamed breaks.",
    "At EQUATE points the TSMIS print uses the SAME convention as the TSN print — an "
    "annotation row at the realignment postmile with no feature type, plus the \"E\" "
    "suffix on the equated plain postmile — so equates mostly pair up cleanly here. "
    "The annotation descriptions still differ on purpose: the TSMIS print writes "
    "\"EQUATES TO <label>\" (or just \"EQUATES TO\") where TSN writes the bare "
    "\"EQUATES TO\".",
    "Descriptions: the TSMIS export prepends the row's own route as a label "
    "(\"001/NB OFF TO DOHENY PK RD\") — that label alone is stripped before "
    "comparing. TSN text is compared VERBATIM: TSN's numeric route prefixes "
    "(including ones naming a DIFFERENT route) are authoritative source claims, so "
    "TSMIS \"103 SEP 53-145\" vs TSN \"1/103 SEP 53-145\" is a REAL difference.",
    "CONTEXT columns (shown for reference, never counted as a difference): HG (TSMIS "
    "leaves the highway-group blank for whole counties while TSN always fills it); City "
    "(TSN assigns a city code far more aggressively than TSMIS); and Distance To Next "
    "Point (measured to each system's OWN next listed point — since TSN lists more breaks, "
    "its gap is usually smaller; TSN also prints pointer markers \"*P*\" and "
    "\"-------->\" there, conserved verbatim). Counting these would bury the "
    "substantive differences. FT and Description ARE compared.",
)

# The PDF-vs-Excel self-check notes (CMP-AUD-199): the same report rendered two
# ways — identity excludes the moving equate suffix, every column is asserted.
_NOTES_PDF_VS_EXCEL_TITLE = ("Highway Sequence — TSMIS (PDF) vs TSMIS (Excel): "
                             "comparison notes")
_NOTES_PDF_VS_EXCEL = (
    "Both sides are TSMIS — the same report rendered two ways (the site's Print "
    "layout vs the Excel export). Apart from the by-design classes below, every "
    "cell should match; a residual difference means the two renders genuinely "
    "disagree (the statewide census caught the Excel export dropping a "
    "Description that the print carries).",
    "Rows are keyed on Route + County + the prefixed postmile WITHOUT its equate "
    "suffix; \"PM Suffix\" is its own compared column. The two renders seat the "
    "\"E\" suffix on DIFFERENT rows of an equate pair BY DESIGN (the print uses "
    "the TSN convention — \"E\" on the equated plain postmile — where the Excel "
    "export usually seats it on the realignment row), so each moved equate "
    "surfaces as exactly two honest PM Suffix cell differences instead of four "
    "fabricated one-sided rows; a suffix only ONE render carries anywhere in the "
    "pair is a real source delta.",
    "EQUATE points also differ in content by design: the print writes an "
    "annotation row \"EQUATES TO <label>\" with HG / FT / Distance blank, where "
    "the Excel export writes the label alone (\"END R REALIGNMENT\", \"PM "
    "EQUATION\", …) and keeps the flags — those pairs surface as Description/FT/"
    "HG differences.",
    "EVERY column is compared here (no context columns): both sides are the same "
    "system, so an HG/City/Distance disagreement is a real render difference, not "
    "a listing artifact. Descriptions are compared verbatim on both sides (no "
    "route-label stripping — both renders print the same labels).",
    "The print is an HTML render, so whitespace runs inside a Description collapse "
    "to one space; the comparison collapses both sides, so padding never counts. "
    "The same-source rule also decodes the Excel export's OOXML escapes (a "
    "handful of cells carry an encoded line break, \"_x000d_\") and ignores edge "
    "tab padding — encoding artifacts one render structurally cannot carry are "
    "never counted as data differences.",
)


# --------------------------------------------------------------------------- #
# the same-source (PDF vs Excel) shape — CMP-AUD-199
# --------------------------------------------------------------------------- #
SS_HEADER = ["County", "PM", "PM Suffix", "City", "HG", "FT",
             "Distance To Next Point", "Description"]
SS_KEY_FIELD = SS_HEADER.index("PM")           # 1


def _tsmis_row_same_source(r):
    """One consolidated TSMIS row in the same-source shape: the key is the
    prefixed postmile WITHOUT the equate suffix (the suffix moves between the
    two renders of one equate pair), the suffix is its own compared cell, and
    the Description keeps its route label (both renders print it)."""
    def at(i):
        return r[i] if i < len(r) else None
    route = _hsl._v(at(0))
    county_raw = at(1)
    prefix, pm, suffix = at(3), at(4), at(5)
    key = _hsl._physical_pm_key(
        route, county_raw, _hsl._glue_pm(prefix, pm, None),
        (("route", _hsl._raw_text(at(0))),
         ("county", _hsl._raw_text(county_raw)),
         ("postmile_prefix", _hsl._raw_text(prefix)),
         ("postmile", _hsl._raw_text(pm)),
         ("postmile_suffix", _hsl._raw_text(suffix))),
        "the consolidated TSMIS workbook")
    return [route,
            _hsl._norm_county(county_raw),
            key,
            _hsl._v(suffix),
            _hsl._v(at(2)),
            _hsl._v(at(6)),
            _hsl._v(at(7)),
            _hsl._v(at(8)),
            _hsl._desc_plain(at(9))]


def _load_tsmis_same_source(path):
    return load_consolidated_rows(
        path, _hsl.TSMIS_SHEET,
        missing_sheet_hint="pick the consolidated TSMIS Highway Sequence workbook.",
        bad_header_msg="isn't a CONSOLIDATED Highway Sequence workbook "
                       "(expected a leading 'Route' column) — consolidate first.",
        row_transform=_tsmis_row_same_source)


_SS_SCHEMA = CompareSchema(
    report_name=_hsl.REPORT_NAME,
    header=SS_HEADER,
    side_a="TSMIS (PDF)",
    side_b="TSMIS (Excel)",
    id_noun="location",
    id_noun_plural="locations",
    pair_noun="postmile",
    sides_noun="renders",
    data_widths={"County": 8, "PM": 12, "PM Suffix": 10, "Description": 26},
    cmp_widths={"PM": 12, "PM Suffix": 10, "Description": 30},
    key_field=SS_KEY_FIELD,
)


class _HighwaySequenceFileCompare:
    """One Highway-Sequence file-vs-file comparison: compare(path_a, path_b, …) +
    suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. `load_a`/`load_b` are the two sides'
    loaders; `tsn_claims=True` folds the normalized TSN workbook's persisted
    source claims (CMP-AUD-155) into the Notes per run."""

    def __init__(self, report_name, side_a, side_b, name_tag, load_a, load_b,
                 base_schema, notes_title, notes_lines, tsn_claims=False,
                 one_sided_note_extra=None, same_source=False,
                 excel_side_b=False):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._name_tag = name_tag
        self._load_a = load_a
        self._load_b = load_b
        self._excel_side_b = excel_side_b   # CMP-AUD-066 role enforcement
        self._notes_title = notes_title
        self._notes_lines = notes_lines
        self._tsn_claims = tsn_claims
        # PDF-vs-Excel self-check (owner ruling 2026-07-16, the CMP-AUD-197
        # class): decode the Excel export's OOXML escapes + drop edge tab
        # padding at load — render artifacts, not data differences. The vs-TSN
        # legs keep their oracle-exact byte semantics.
        self._same_source = same_source
        # Source Files: side A is the PDF export (.pdf); side B is the Excel export
        # (.xlsx) for the same-source self-check, else the statewide TSN (no source).
        schema = replace(base_schema, side_a=side_a, side_b=side_b,
                         legend_writer=ctc.make_notes_writer(
                             notes_title, notes_lines),
                         source_file_a=("highway_sequence", _hsl.TSMIS_SHEET, "pdf"),
                         source_file_b=(("highway_sequence", _hsl.TSMIS_SHEET, "xlsx")
                                        if same_source else ()))
        if one_sided_note_extra is not None:
            schema = replace(schema, one_sided_note_extra=one_sided_note_extra)
        self._schema = schema

    def suggest_name(self, path_a):
        return suggest_route_name(path_a, "Highway_Sequence", self._name_tag)

    def _schema_for(self, path_b):
        if not self._tsn_claims:
            return self._schema
        return _hsl._schema_with_claims(
            path_b, schema=self._schema, title=self._notes_title,
            lines=self._notes_lines)

    def _load_pair(self, path_a, path_b):
        # CMP-AUD-066: the "TSMIS (PDF)" side must carry the PDF-conversion
        # marker; a vs-Excel second side must not (the TSN side keeps its own
        # v4 normalization gate inside _load_tsn).
        ctc.require_pdf_source(path_a, self.file_a_label, "Highway Sequence")
        if self._excel_side_b:
            ctc.reject_pdf_source(path_b, self.file_b_label, "Highway Sequence")
        rows_a, _ = self._load_a(path_a)
        rows_b, _ = self._load_b(path_b)
        if self._same_source:
            rows_a = ctc.same_source_render_rows(rows_a)
            rows_b = ctc.same_source_render_rows(rows_b)
        return rows_a, rows_b, None

    def compare(self, path_a, path_b, out_path, events=None, confirm_overwrite=None,
                mode="formulas", commit_guard=None):
        return run_files_compare(
            self._schema_for(path_b), path_a, path_b, out_path,
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
    load_a=_hsl._load_tsmis, load_b=_hsl._load_tsn,
    base_schema=_hsl._SCHEMA,
    notes_title=_NOTES_PDF_VS_TSN_TITLE, notes_lines=_NOTES_PDF_VS_TSN,
    tsn_claims=True)

TSMIS_PDF_VS_EXCEL = _HighwaySequenceFileCompare(
    report_name="Highway Sequence — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel_HighwaySequence",
    load_a=_load_tsmis_same_source, load_b=_load_tsmis_same_source,
    base_schema=_SS_SCHEMA,
    notes_title=_NOTES_PDF_VS_EXCEL_TITLE, notes_lines=_NOTES_PDF_VS_EXCEL,
    one_sided_note_extra=(" (a row genuinely present in only one render — the "
                          "by-design equate suffix moves now pair up and surface "
                          "as PM Suffix cells, see Notes)"),
    same_source=True, excel_side_b=True)
