"""PDF-sourced Ramp Detail comparisons (mirrors compare_highway_sequence_pdf).

Two "files"-kind comparison types over the regression-locked compare_core engine,
both riding compare_ramp_detail_tsn's schema + normalizations. The PDF-consolidated
TSMIS workbook carries the Excel export's exact 11-column layout PLUS the two
print-only columns the Excel export drops (On/Off, Ramp Type) — data TSN's
database also carries — so the PDF side compares RICHER than the Excel side:

  * TSMIS_PDF_VS_TSN   — TSMIS (PDF) vs TSN. The PDF replaces the Excel as the
    TSMIS side (parsed from this app's own "TSAR: Ramp Detail (PDF)" export);
    the TSN side is unchanged. On/Off and Ramp Type GRADUATE from context to
    compared here — the print carries both where the Excel export has nothing —
    so two more columns get verified against TSN (Ramp Name and ADT stay
    context: nothing TSMIS-side to compare them to).
  * TSMIS_PDF_VS_EXCEL — TSMIS (PDF) vs TSMIS (Excel). Diffs the two TSMIS
    renders of the SAME report to prove both exports carry the same data (and
    to pinpoint exactly where they disagree when they don't). On/Off and Ramp
    Type stay CONTEXT here (the Excel side genuinely lacks them — the workbook
    shows the print's values for reference, never counts them).

The PDF side's loader projects the print's CENSUSED render artifacts at compare
time (the workbook itself stays verbatim):
  * whitespace runs inside a Description collapse to one space — the print is
    an HTML render; the database (and so the Excel export AND the TSN extract)
    carries literal double spaces ("SB ON  AVERY PKWY"). BOTH sides of each
    flavor are collapsed, so padding never counts as a difference.
  * the print writes "-" in an empty Area 4 / On/Off cell and the message
    "NO RAMP LINEAR EVENT" in an empty Description (59 statewide rows — TSAR
    ramp points without linework); those project to the blank the other
    sources carry.
  * the print's On/Off letters are N (on) / F (off) / Z (other) where TSN
    stores O / F / Z — N projects to O so the letters compare.

Each flavor overrides ONLY the side labels, the context set, and the Notes
sheet (each gets notes describing ITS by-design classes); the engine's
formula/label text is untouched, so the compare_core regression lock stays
intact. The GUI's Compare tab drives these through COMPARE_REPORTS ("files"
input kind); `file_a_label`/`file_b_label` name the two file pickers.
"""
import re
from dataclasses import replace

import compare_ramp_detail_tsn as _rd
import compare_tsn_common as ctc
from compare_tsn_common import (load_consolidated_rows, run_files_compare,
                                suggest_route_name)

_DESC_I = 1 + _rd.SHARED_HEADER.index("Description")     # in a [route, *header] row

# The print's null-render tokens (censused statewide, 59 rows): what the site
# prints where the Excel export (and TSN) leave the field blank.
_NULL_DESC = "NO RAMP LINEAR EVENT"
_NULL_MARK = "-"

_WS_RUN = re.compile(r"\s+")


def _collapse(text):
    """Collapse internal whitespace runs to one space (the HTML print's own
    rendering; applied to BOTH sides so padding never counts)."""
    return _WS_RUN.sub(" ", text).strip() if isinstance(text, str) else text


def _collapse_desc_rows(rows):
    for r in rows:
        r[_DESC_I] = _collapse(r[_DESC_I])
    return rows


# --------------------------------------------------------------------------- #
# TSMIS (PDF) side: the PDF-consolidated workbook (13 columns + Route)
# --------------------------------------------------------------------------- #
# Consolidated value positions (Route prepended to the consolidator's HEADER):
# Route0 Location1 PR2 PM3 Date4 blank5 HG6 Area4 7 City8 R/U9 Description10
# blank11 On/Off12 RampType13.
def _null_blank(v):
    return "" if v == _NULL_MARK else v


def _pdf_row(r):
    def at(i):
        return r[i] if i < len(r) else None
    route = _rd._norm_route(at(0))
    desc = _rd._strip_desc_prefix(at(10), route)
    if desc == _NULL_DESC:
        desc = ""
    onoff = _null_blank(_rd._v(at(12)))
    loc = _rd._raw_text(at(1)).strip()
    district, county = _rd._dist_cnty(loc)
    # CMP-AUD-045: the same D4 PhysicalKey as every other Ramp Detail path.
    key = _rd._physical_pm_key(route, county, at(3), (
        ("route", route), ("location", loc),
        ("postmile_prefix", _rd._raw_text(at(2))),
        ("postmile", _rd._raw_text(at(3))),
        ("postmile_suffix", _rd._raw_text(at(5)))), f"Location {loc!r}")
    return [route,
            _rd._v(at(2)), key, district, _rd._iso_date(at(4)),
            _rd._v(at(6)), _null_blank(_rd._v(at(7))), _rd._v(at(8)), _rd._v(at(9)),
            _collapse(desc),
            "",                                        # Ramp Name: TSN-only
            "O" if onoff == "N" else onoff,            # print N/F/Z -> TSN O/F/Z
            _rd._v(at(13)),
            ""]                                        # ADT: TSN-only


# CMP-AUD-036: the PDF-consolidated workbook is exactly ["Route"] + the RD-PDF
# consolidator's 13-column print HEADER (14 columns), and its DISTINGUISHING
# feature is the two TRAILING print-only labels On/Off + Ramp Type the Excel
# export drops. check_compare_ramp_detail_pdf pins _PDF_WIDTH against the
# consolidator's own HEADER length.
_PDF_WIDTH = 14
_PDF_SENTINELS = ("On/Off", "Ramp Type")


def _pdf_header_ok(h):
    """A PDF-consolidated Ramp Detail layout: the EXACT 14-column width (trailing
    blanks trimmed), PM among the first five cells, and the two print-only
    sentinels as the final two columns IN ORDER. The old gate ('PM in the first
    five and On/Off anywhere') accepted a truncated four-column
    Route/Location/PM/On-Off workbook and expanded it with every absent field
    fabricated as blank (CMP-AUD-036); this refuses truncated inputs and an
    Excel-consolidated pick (which has neither print-only column)."""
    core = list(h)
    while core and core[-1] == "":
        core.pop()
    return (len(core) == _PDF_WIDTH and "PM" in core[:5]
            and tuple(core[-2:]) == _PDF_SENTINELS)


def _load_tsmis_pdf(path):
    """TSMIS (PDF) side -> (rows, has_route=True). The PDF-CONSOLIDATED Ramp
    Detail workbook — the Excel layout plus the two print-only columns, whose
    exact width + trailing sentinels the header gate requires so a truncated or
    Excel-consolidated pick fails fast (CMP-AUD-036)."""
    return load_consolidated_rows(
        path, _rd.TSMIS_SHEET,
        missing_sheet_hint="pick the consolidated TSMIS Ramp Detail (PDF) workbook.",
        bad_header_msg="isn't a PDF-CONSOLIDATED Ramp Detail workbook "
                       "(expected the full print layout ending in the On/Off / "
                       "Ramp Type columns the PDF consolidator adds) — "
                       "consolidate the 'TSAR: Ramp Detail (PDF)' exports first.",
        header_ok=_pdf_header_ok,
        row_transform=_pdf_row)


# --------------------------------------------------------------------------- #
# the b-side loaders (each flavor's second file), whitespace-collapsed to the
# print's rendering so padding never counts
# --------------------------------------------------------------------------- #
def _load_tsn_collapsed(path):
    rows, has_route = _rd._load_tsn(path)
    return _collapse_desc_rows(rows), has_route


def _load_excel_collapsed(path):
    rows, has_route = _rd._load_tsmis(path)
    return _collapse_desc_rows(rows), has_route


# --------------------------------------------------------------------------- #
# Notes sheets — each flavor documents ITS by-design classes
# --------------------------------------------------------------------------- #
_NOTES_PDF_VS_TSN = ctc.make_notes_writer(
    "Ramp Detail — TSMIS (PDF) vs TSN: comparison notes",
    (
        "Rows are keyed on Route + County + PM (postmile, normalized — '9.6' and "
        "'009.600' are the same ramp; County from each source's Location).",
        "Date of Record is compared as an ISO date — display-format differences "
        "(6/1/2024 vs 2024-06-01) never count.",
        "Description is compared after stripping the TSMIS leading \"<route>/\" "
        "prefix (\"001/NB OFF …\" vs TSN \"NB OFF …\") and collapsing whitespace "
        "runs on BOTH sides — the print is an HTML render that collapses the "
        "database's literal double spaces (\"SB ON  AVERY PKWY\"), which the TSN "
        "extract still carries; without the collapse every such ramp would flag "
        "a phantom Description difference.",
        "On/Off and Ramp Type ARE compared in this flavor — the print carries both "
        "where the Excel export has nothing, so the PDF side verifies two more "
        "columns against TSN. The print marks an on-ramp \"N\" where TSN stores "
        "\"O\"; the PDF side is projected to TSN's O / F / Z letters so they "
        "compare. CONTEXT columns (shown for reference, never counted): Ramp Name "
        "and ADT are TSN database columns with no TSMIS counterpart in either "
        "edition.",
        "The print renders an EMPTY field visibly — \"-\" in Area 4 / On/Off and "
        "the Description message \"NO RAMP LINEAR EVENT\" (ramp points without "
        "linework) — where the database is simply blank; those project to blank "
        "before comparing.",
        "One-sided rows are ramps one system lists at a postmile the other doesn't.",
    ))

_NOTES_PDF_VS_EXCEL = ctc.make_notes_writer(
    "Ramp Detail — TSMIS (PDF) vs TSMIS (Excel): comparison notes",
    (
        "Both sides are TSMIS — the same report rendered two ways (the site's Print "
        "layout vs the Excel export). Apart from the known classes below, every cell "
        "should match; a residual difference means the two renders genuinely disagree.",
        "Whitespace runs inside a Description collapse to one space on BOTH sides: "
        "the Excel export carries the database's literal double spaces "
        "(\"SB ON  AVERY PKWY\") that the print's HTML render collapses — padding "
        "never counts as a difference.",
        "The print renders an EMPTY field visibly where the Excel export leaves the "
        "cell blank: \"-\" in Area 4 / On/Off and the Description message "
        "\"NO RAMP LINEAR EVENT\" (59 statewide rows — TSAR ramp points without "
        "linework, the count Ramp Summary prints per route). Those project to "
        "blank before comparing.",
        "On/Off and Ramp Type are PRINT-ONLY columns the Excel export drops — shown "
        "as context for reference (blank on the Excel side), never counted as a "
        "difference.",
        "The same-source rule decodes the Excel export's OOXML escapes (a handful "
        "of cells carry an encoded line break, \"_x000d_\" — 4 statewide: route "
        "010's rest-area ramps) and ignores edge tab padding — encoding artifacts "
        "one render structurally cannot carry are never counted as data "
        "differences.",
        "One-sided rows are ramps one render lists at a postmile the other doesn't "
        "(none statewide on a same-run pair).",
    ))


# --------------------------------------------------------------------------- #
# the two comparison types
# --------------------------------------------------------------------------- #
class _RampDetailFileCompare:
    """One Ramp Detail file-vs-file comparison: compare(path_a, path_b, …) +
    suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. `load_b` is the loader for the SECOND
    file (the TSN loader for vs-TSN, the consolidated-TSMIS loader for
    vs-Excel); the first file is always the PDF-consolidated TSMIS workbook."""

    def __init__(self, report_name, side_a, side_b, name_tag, load_b,
                 legend_writer, context_fields=None, one_sided_note_extra=None,
                 same_source=False):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._name_tag = name_tag
        self._load_b = load_b
        # PDF-vs-Excel self-check (owner ruling 2026-07-16, the CMP-AUD-197
        # class): both sides render the SAME report, so the Excel export's
        # OOXML escapes ("…_x000d_") and edge tab padding are render artifacts,
        # not data differences. The vs-TSN legs keep the accepted RD-79
        # byte-exact semantics (same_source stays False there).
        self._same_source = same_source
        # Source Files: side A is the PDF export (.pdf); side B is the Excel export
        # (.xlsx) for the same-source self-check, else the statewide TSN (no source).
        schema = replace(_rd._SCHEMA, side_a=side_a, side_b=side_b,
                         legend_writer=legend_writer,
                         source_file_a=("tsar_ramp_detail", _rd.TSMIS_SHEET, "pdf"),
                         source_file_b=(("tsar_ramp_detail", _rd.TSMIS_SHEET, "xlsx")
                                        if same_source else ()))
        if context_fields is not None:
            schema = replace(schema, context_fields=context_fields)
        if one_sided_note_extra is not None:
            schema = replace(schema, one_sided_note_extra=one_sided_note_extra)
        self._schema = schema

    def suggest_name(self, path_a):
        return suggest_route_name(path_a, "Ramp_Detail", self._name_tag)

    def _load_pair(self, path_a, path_b):
        rows_a, _ = _load_tsmis_pdf(path_a)
        rows_b, _ = self._load_b(path_b)
        if self._same_source:
            rows_a = ctc.same_source_render_rows(rows_a)
            rows_b = ctc.same_source_render_rows(rows_b)
        return rows_a, rows_b, None

    def compare(self, path_a, path_b, out_path, events=None, confirm_overwrite=None,
                mode="formulas", commit_guard=None):
        return run_files_compare(
            self._schema, path_a, path_b, out_path,
            banner=(f"Ramp Detail Comparison — {self.file_a_label} vs "
                    f"{self.file_b_label}"),
            has_route=True, loader=self._load_pair, deps_ok=_rd._DEPS_OK,
            deps_msg="Required components are missing (openpyxl).",
            events=events, confirm_overwrite=confirm_overwrite, mode=mode,
            commit_guard=commit_guard)


TSMIS_PDF_VS_TSN = _RampDetailFileCompare(
    report_name="Ramp Detail — TSMIS (PDF) vs TSN",
    side_a="TSMIS (PDF)", side_b="TSN",
    name_tag="TSMIS_PDF_vs_TSN_RampDetail",
    load_b=_load_tsn_collapsed,
    legend_writer=_NOTES_PDF_VS_TSN,
    # On/Off + Ramp Type graduate to COMPARED (the print carries them); Ramp
    # Name and ADT stay context — nothing TSMIS-side to compare them to.
    context_fields=("Ramp Name", "ADT"))

TSMIS_PDF_VS_EXCEL = _RampDetailFileCompare(
    report_name="Ramp Detail — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel_RampDetail",
    load_b=_load_excel_collapsed,
    legend_writer=_NOTES_PDF_VS_EXCEL,
    one_sided_note_extra=(" (none expected on a same-run pair — the two renders "
                          "list the same ramps)"),
    same_source=True)
