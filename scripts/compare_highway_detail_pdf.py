"""PDF-sourced Highway Detail comparisons (mirrors compare_intersection_detail_pdf).

Two "files"-kind comparison types over the regression-locked compare_core engine,
both reusing compare_highway_detail_tsn's loaders + schema. The PDF-consolidated
TSMIS workbook has the IDENTICAL 34-column layout the Excel export produces, so
`_load_tsmis` reads it BY POSITION exactly the same way — no new loader is needed:

  * TSMIS_PDF_VS_TSN   — TSMIS (PDF) vs TSN. The PDF replaces the Excel as the
    TSMIS side (the PDF is parsed from this app's own "Highway Detail (PDF)"
    export); the TSN side is unchanged.
  * TSMIS_PDF_VS_EXCEL — TSMIS (PDF) vs TSMIS (Excel). Diffs the two TSMIS
    renders of the SAME report to prove both exports carry the same data (and
    to pinpoint exactly where they disagree when they don't).

Each overrides ONLY the two side labels (and, for the PDF-vs-Excel pair, drops
the TSN-specific Notes sheet — both sides are TSMIS, so the TSN normalization
notes don't apply); the engine's formula/label text is untouched, so the
compare_core regression lock stays intact. The GUI's Compare tab drives these
through COMPARE_REPORTS ("files" input kind); `file_a_label`/`file_b_label`
name the two file pickers.
"""
from dataclasses import replace

import compare_highway_detail_tsn as _hd
from compare_tsn_common import (load_consolidated_rows, reject_pdf_source,
                                require_pdf_source, run_files_compare,
                                suggest_route_name)

# --------------------------------------------------------------------------- #
# the same-source (PDF vs Excel) shape — CMP-AUD-067
# --------------------------------------------------------------------------- #
# The canonical roadbed-aware Post Mile stays the PAIRING key (the Excel
# export genuinely drops roadbed letters the print carries, so verbatim keys
# would explode one-sided rows), but the RAW printed token becomes its own
# compared trailing cell — a dropped R/L now SURFACES instead of hiding
# inside the canonical key. Every other value cell is verbatim: the vs-TSN
# reconciliations (the NA 'A'→blank fold, numeric/length/WDA padding, the
# whitespace collapse) exist to bridge TSN's encodings and must not erase
# render differences between two TSMIS renders. The one kept normalization is
# the typed-date render equivalence (openpyxl may type a date cell in one
# workbook and store text in the other — the printed value is identical).
SS_HEADER = list(_hd.SHARED_HEADER) + ["PM (raw)"]


def _project_same_source(field, raw):
    if field in _hd.DATE_FIELDS:
        return _hd._norm_date(raw)
    return _hd._s(_hd._v(raw))


def _tsmis_row_same_source(r):
    return _hd._tsmis_row_with(
        r, _project_same_source,
        extra=lambda _at, token: [_hd._s(_hd._v(token))])


def _load_tsmis_same_source(path):
    return load_consolidated_rows(
        path, _hd.TSMIS_SHEET,
        missing_sheet_hint="pick the consolidated TSMIS Highway Detail workbook.",
        bad_header_msg="isn't a CONSOLIDATED Highway Detail workbook "
                       "(expected a leading 'Route' column) — consolidate first.",
        row_transform=_tsmis_row_same_source)


_SS_SCHEMA = replace(
    _hd._SCHEMA, header=SS_HEADER,
    data_widths=dict(_hd._SCHEMA.data_widths, **{"PM (raw)": 12}),
    cmp_widths=dict(_hd._SCHEMA.cmp_widths, **{"PM (raw)": 12}))


class _HighwayDetailFileCompare:
    """One Highway-Detail file-vs-file comparison: compare(path_a, path_b, …) +
    suggest_name(path_a), with the two side labels carried through to the
    workbook and the GUI's file pickers. `load_b` is the loader for the SECOND
    file (the TSN loader for vs-TSN, the consolidated-TSMIS loader for
    vs-Excel); the first file is always the PDF-consolidated TSMIS workbook."""

    def __init__(self, report_name, side_a, side_b, name_tag, load_b,
                 one_sided_note_extra=None, drop_notes=False,
                 excel_side_b=False, load_a=None, base_schema=None,
                 report_view=False):
        self.REPORT_NAME = report_name
        self.file_a_label = side_a          # the GUI's first / second file-picker
        self.file_b_label = side_b          # labels (also the workbook side names)
        self._excel_side_b = excel_side_b   # CMP-AUD-066 role enforcement
        self._name_tag = name_tag
        self._load_a = load_a or _hd._load_tsmis
        self._load_b = load_b
        # CMP-AUD-068: the vs-TSN flavor gets the two-line 'Report View' replica the
        # Excel-sourced comparison has (added per-call so the writer can read the two
        # input paths). The same-source PDF-vs-Excel self-check does NOT: the replica's
        # structural-date "soft" classification and TSN-only ADT/DCR reference columns
        # are TSN-specific — on two TSMIS renders those must be IDENTICAL, so a "soft"
        # verdict would understate a real render defect (the CMP-AUD-067 principle).
        self._report_view = report_view
        # Source Files: side A is the PDF export (.pdf); side B is the Excel export
        # (.xlsx) for the same-source self-check, else the statewide TSN (no source).
        schema = replace(base_schema or _hd._SCHEMA,
                         side_a=side_a, side_b=side_b,
                         source_file_a=("highway_detail", _hd.TSMIS_SHEET, "pdf"),
                         source_file_b=(("highway_detail", _hd.TSMIS_SHEET, "xlsx")
                                        if excel_side_b else ()))
        if one_sided_note_extra is not None:
            schema = replace(schema, one_sided_note_extra=one_sided_note_extra)
        if drop_notes:
            # PDF-vs-Excel: both sides are TSMIS, so the TSN-specific Notes sheet
            # (NA folding, BEG_DATE semantics, …) doesn't apply.
            schema = replace(schema, legend_writer=None)
        self._schema = schema

    def suggest_name(self, path_a):
        return suggest_route_name(path_a, "Highway_Detail", self._name_tag)

    def _load_pair(self, path_a, path_b):
        # CMP-AUD-066: the "TSMIS (PDF)" side must carry the PDF-conversion
        # marker; a vs-Excel second side must not (the TSN side keeps its own
        # normalization gate inside its loader).
        require_pdf_source(path_a, self.file_a_label, "Highway Detail")
        if self._excel_side_b:
            reject_pdf_source(path_b, self.file_b_label, "Highway Detail")
        rows_a, _ = self._load_a(path_a)   # PDF side: same 34-col consolidated layout
        rows_b, _ = self._load_b(path_b)
        return rows_a, rows_b, None

    def _schema_for(self, path_a, path_b):
        """The per-call schema. The vs-TSN flavor adds the 'Report View' replica
        (needs both paths, so it can't be baked into the __init__ schema); every
        other flavor uses the static schema as-is."""
        if self._report_view:
            return _hd.add_report_view(self._schema, path_a, path_b)
        return self._schema

    def compare(self, path_a, path_b, out_path, events=None, confirm_overwrite=None,
                mode="formulas", commit_guard=None):
        return run_files_compare(
            self._schema_for(path_a, path_b), path_a, path_b, out_path,
            banner=(f"Highway Detail Comparison — {self.file_a_label} vs "
                    f"{self.file_b_label}"),
            has_route=True, loader=self._load_pair, deps_ok=_hd._DEPS_OK,
            side_a=self.file_a_label, side_b=self.file_b_label,
            events=events, confirm_overwrite=confirm_overwrite, mode=mode,
            commit_guard=commit_guard)


TSMIS_PDF_VS_TSN = _HighwayDetailFileCompare(
    report_name="Highway Detail — TSMIS (PDF) vs TSN",
    side_a="TSMIS (PDF)", side_b="TSN",
    name_tag="TSMIS_PDF_vs_TSN_HighwayDetail",
    load_b=_hd._load_tsn, report_view=True)

TSMIS_PDF_VS_EXCEL = _HighwayDetailFileCompare(
    report_name="Highway Detail — TSMIS PDF vs Excel",
    side_a="TSMIS (PDF)", side_b="TSMIS (Excel)",
    name_tag="TSMIS_PDF_vs_Excel_HighwayDetail",
    load_a=_load_tsmis_same_source, load_b=_load_tsmis_same_source,
    base_schema=_SS_SCHEMA,
    one_sided_note_extra=" (locations one source lists at a postmile the other doesn't)",
    drop_notes=True, excel_side_b=True)
