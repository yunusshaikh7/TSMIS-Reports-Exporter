"""Golden check for the TSMIS Highway Detail (PDF) pipeline.

The PDF consolidator parses the printed TASAS two-line-per-record layout whose
un-shaded records carry no cell rects, so TWO window sets are derived from the
shaded bands (the 10-rect line-1 geometry and the 25-rect line-2 geometry) and
every text line is assigned to them. This check locks the parts that don't need
a real PDF (the live parse is reconciled against the statewide PDF+Excel bundle
off-CI):

  * the 34-column header equals the site's Excel-export header (one source of
    truth in highway_detail_columns);
  * the line1(10) + line2(25) -> 34-column mapping;
  * the line-1 classifier (the glued postmile token) accepts every real postmile
    shape and rejects the DCR group rows + page furniture; and
  * the compare adapters + matrix wiring resolve with the right side labels.

CI-safe: pure Python, no browser, no local data files.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import compare_highway_detail_pdf as cmp_pdf
import compare_highway_detail_tsn as _hd
import consolidate_tsmis_highway_detail_pdf as hdpdf
import matrix
import matrix_build
from highway_detail_columns import HEADER

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_header():
    print("34-column header (one source of truth, == the Excel export):")
    check("34 columns", len(HEADER) == 34)
    check("Post Mile leads; Description at index 9; NA at 10",
          HEADER[0] == "Post Mile" and HEADER[9] == "Description"
          and HEADER[10] == "NA")
    check("the three attribute blocks sit at 11..19 / 20..24 / 25..33",
          HEADER[11] == "LB Eff" and HEADER[20] == "Med Eff"
          and HEADER[25] == "RB Eff" and HEADER[33] == "RB OT-TR")
    check("consolidator pins the shared header", hdpdf.HD_HEADER is HEADER)


def test_make_row_mapping():
    print("_make_row: line1(10) + line2(25) -> 34 columns:")
    a = [f"a{i}" for i in range(10)]           # line 1 (window 9 = the empty tail)
    b = [f"b{i}" for i in range(25)]           # line 2
    row = hdpdf._make_row(a, b)
    check("34 output columns", len(row) == 34)
    check("line-1 windows 0..8 map to columns 0..8 (the tail window dropped)",
          row[0:9] == a[0:9])
    check("line-2 windows 0..24 map to columns 9..33", row[9:34] == b)
    check("empty strings become None (blank cells, like the Excel export)",
          hdpdf._make_row([""] * 10, [""] * 25) == [None] * 34)


def test_line1_classifier():
    print("the line-1 classifier (glued postmile in window 0):")
    ok = ("S000.000", "000.000E", "R012.243", "000.080R", "C043.925R", "011.228")
    bad = ("11 IMP 007",                # a DCR group row
           "BEGIN SPUR ROUTE 7",       # a description (line 2)
           "EB 58-330",                # a description with digits
           "Ref Date: 2026-07-07 Route 007 Page 1",   # page furniture
           "P P - Post Mile Prefix",   # legend text
           "")
    check("accepts every real postmile shape",
          all(hdpdf._is_line1([t]) for t in ok))
    check("rejects DCR rows / descriptions / furniture",
          not any(hdpdf._is_line1([t]) for t in bad))
    check("accepts a postmile as the FIRST TOKEN (the over-wide fallback grid "
          "merges 'PM LEN' into window 0)",
          hdpdf._is_line1(["000.000L 000.000 19-10-14"])
          and not hdpdf._is_line1(["04 ALA 880S"]))
    # v0.26.0 (the 7.9/ARS census): an OUTDENTED equate description also opens
    # with a PM-shaped token — but its text runs on as WORDS (not the Length
    # cell), and on the ordinary grid it spills into window 1 too. Treating it
    # as a line 1 orphaned the real record AND minted a phantom one.
    check("rejects an outdented equate DESCRIPTION that starts PM-shaped",
          not hdpdf._is_line1(["R42.401 LT EQ 43.185 , PM R42401BK=43185E AH"])
          and not hdpdf._is_line1(["R42.401 LT EQ 43.1", "85 , PM"]))
    check("a merged 'PM LEN' with window-1 spill is NOT a line 1 (desc overflow)",
          not hdpdf._is_line1(["000.000L 000.000", "overflow text"]))


def test_line2_furniture():
    """The line-2 acceptance's furniture tests (v0.26.0) — matched on the
    SPACELESS raw text. Every string below is a censused 7.9/ARS group; a
    furniture false-NEGATIVE would corrupt silently (a THEAD swallowed as
    data), so these pin the vocabulary."""
    print("line-2 furniture tests (raw-text censused shapes):")
    thead = ("POSTMILELENGTHRECORDGCEFF-DATECODEUEFF-DATE",
             "DATEOFHAACC-CONTCITYR",
             "S#SOTOTT-WININVS#SININT-WOTOT",
             "EFF-S#SOTOTT-WININEFF-VEFF-S#SININT-WOTOT",
             "DATETLNFTOTRWIDTOTRDATETCBWDADATETLNFTOTRWIDTOTR",
             "ACC-")
    check("every censused THEAD line matches THEAD_RE",
          all(hdpdf.THEAD_RE.search(t) for t in thead))
    sparse = ("Z07Z", "Z1010050207Z", "SMAINSTOCBR8-112Z07Z", "B080807Z",
              "NZ080807Z", "07", "OLDUS101UC4-21607", "N.W.P.R.R.07",
              "ACIDCANALZ07Z")
    check("no censused SPARSE line 2 matches THEAD_RE (they must parse)",
          not any(hdpdf.THEAD_RE.search(s) for s in sparse))
    check("DCR rows / page furniture matched on raw text",
          hdpdf.DCR_ROW_RE.match("02TEH005") and hdpdf.DCR_ROW_RE.match("11IMP007")
          and hdpdf.PAGE_FURNITURE_RE.search("RefDate:2026-07-10Route101Page101")
          and hdpdf.PAGE_FURNITURE_RE.search("Page176"))
    check("no sparse line 2 reads as DCR / page furniture",
          not any(hdpdf.DCR_ROW_RE.match(s) or hdpdf.PAGE_FURNITURE_RE.search(s)
                  for s in sparse))
    # The date FAST-accept works on RAW text (a mis-aligned window grid can
    # split '15-10-29' across columns, so the merged values can't carry it).
    # In spaceless raw a description ending in DIGITS glues onto the date
    # ('…LNS 395' + '15-10-29' → '39515-10-29') and the lookbehind rightly
    # rejects it — those line 2s are accepted by the furniture FALLTHROUGH
    # instead, so the contract is: desc-less dated line 2s fast-accept, glued
    # ones at least never read as furniture, and the header date never matches.
    check("raw-text date accept: desc-less dated line 2 matches",
          hdpdf.DATE_TOKEN_RE.search("65-12-21C03Z101036050207Z"))
    glued = "JCT14/395ENDRTE14,RTLNS14OVERLTLNS39515-10-29H02Z101024050515-10-29"
    check("digit-glued dated line 2 falls through to acceptance (not furniture)",
          not hdpdf.THEAD_RE.search(glued) and not hdpdf.DCR_ROW_RE.match(glued)
          and not hdpdf.PAGE_FURNITURE_RE.search(glued))
    check("the page header's digit-adjacent date never matches",
          not hdpdf.DATE_TOKEN_RE.search("RefDate:2026-07-10Route101Page101"))
    # A record whose print carries NO second line is emitted with a blank
    # attribute tail (the single-line flush), not dropped.
    check("single-line flush shape: line 1 + a blank 25-cell tail",
          hdpdf._make_row([f"a{i}" for i in range(10)], [""] * hdpdf.N_COLS_L2)
          == [f"a{i}" for i in range(9)] + [None] * 25)


def test_wrap_machinery():
    """The wrapped-cell machinery: a squeezed cell renders over several text
    lines ~5-6pt apart while distinct rows sit >=9.7pt apart — the row grouping
    and the fragment join reassemble the cell (the 005S wrapped-date finding)."""
    print("wrapped-cell row grouping + fragment join:")

    from types import SimpleNamespace

    def chars(top, text, x0=30.0):
        out = []
        x = x0
        for ch in text:
            out.append({"text": ch, "x0": x, "x1": x + 4.0, "top": top})
            x += 4.0
        return out

    # one wrapped row (fragments at 139.8 / 145.8 / 151.0) then a normal row
    # 9.7pt later — the wrapped trio must group, the next row must not.
    page = SimpleNamespace(chars=(chars(139.8, "00-01-") + chars(145.8, "025.148")
                                  + chars(151.0, "01") + chars(160.7, "NEXT")),
                           rects=[])
    groups = hdpdf._row_groups(page)
    check("fragments within ROW_GAP form ONE group; the next row is separate",
          len(groups) == 2 and len(groups[0]) == 3 and len(groups[1]) == 1)
    check("_join_wrap: a hyphen wrap rejoins bare ('00-01-'+'01'); a word wrap "
          "rejoins with a space",
          hdpdf._join_wrap("00-01-", "01") == "00-01-01"
          and hdpdf._join_wrap("COLO", "EXT.") == "COLO EXT."
          and hdpdf._join_wrap("", "X") == "X" and hdpdf._join_wrap("X", "") == "X")
    win = [(-float("inf"), float("inf"))]
    wrapped_date = [(139.8, chars(139.8, "00-01-")), (151.0, chars(151.0, "01"))]
    wrapped_desc = [(139.8, chars(139.8, "COLO")), (151.0, chars(151.0, "EXT."))]
    check("_group_values reassembles a wrapped cell top-to-bottom",
          hdpdf._group_values(wrapped_date, win)[0] == "00-01-01"
          and hdpdf._group_values(wrapped_desc, win)[0] == "COLO EXT.")
    check("_make_row splits a fallback-merged 'PM LEN' window 0 back apart",
          hdpdf._make_row(["000.000L 000.000"] + [""] * 9, [""] * 25)[0:2]
          == ["000.000L", "000.000"])
    check("DATE_TOKEN_RE: accepts a TASAS date, rejects the page header's "
          "digit-adjacent '2026-07-07'",
          hdpdf.DATE_TOKEN_RE.search("A 97-07-23 P 02") is not None
          and hdpdf.DATE_TOKEN_RE.search("Ref Date: 2026-07-07 Page 1") is None
          and hdpdf.DATE_TOKEN_RE.search("POST MILE LENGTH RECORD") is None)


def test_adapters_and_matrix():
    print("compare adapters + matrix wiring resolve:")
    check("PDF-vs-TSN side labels",
          cmp_pdf.TSMIS_PDF_VS_TSN.file_a_label == "TSMIS (PDF)"
          and cmp_pdf.TSMIS_PDF_VS_TSN.file_b_label == "TSN")
    check("PDF-vs-Excel side labels",
          cmp_pdf.TSMIS_PDF_VS_EXCEL.file_a_label == "TSMIS (PDF)"
          and cmp_pdf.TSMIS_PDF_VS_EXCEL.file_b_label == "TSMIS (Excel)")
    check("PDF-vs-Excel drops the TSN-specific Notes sheet",
          cmp_pdf.TSMIS_PDF_VS_EXCEL._schema.legend_writer is None
          and cmp_pdf.TSMIS_PDF_VS_TSN._schema.legend_writer is not None)
    # CMP-AUD-068: the vs-TSN flavor builds the two-line 'Report View' replica the
    # Excel-sourced comparison has (added per-call so its writer can read both input
    # paths); the same-source PDF-vs-Excel self-check does NOT (TSN-specific soft/
    # structural date semantics + TSN-only ADT/DCR columns don't apply to two TSMIS
    # renders). Parity with the Excel-vs-TSN leg (compare_highway_detail_tsn.compare).
    sc_tsn = cmp_pdf.TSMIS_PDF_VS_TSN._schema_for("a.xlsx", "b.xlsx")
    check("PDF-vs-TSN builds a Report View (like Excel-vs-TSN)",
          sc_tsn.extra_sheet_writer is not None
          and sc_tsn.report_view_diff_check == ("Report View", "B", 2))
    sc_ex = cmp_pdf.TSMIS_PDF_VS_EXCEL._schema_for("a.xlsx", "b.xlsx")
    check("PDF-vs-Excel has NO Report View",
          sc_ex.extra_sheet_writer is None and not sc_ex.report_view_diff_check)
    # The Excel-sourced compare() routes through the SAME shared helper.
    _excel_sc = _hd.add_report_view(_hd._SCHEMA, "a.xlsx", "b.xlsx")
    check("Excel-vs-TSN uses the shared add_report_view helper",
          _excel_sc.extra_sheet_writer is not None
          and _excel_sc.report_view_diff_check == ("Report View", "B", 2))
    check("matrix vs-TSN comparator for highway_detail_pdf is the PDF flavor",
          matrix.tsn_comparator_for("highway_detail_pdf") is cmp_pdf.TSMIS_PDF_VS_TSN)
    check("matrix PDF-vs-Excel self comparator resolves",
          matrix._pdf_self_comparator("highway_detail_pdf") is cmp_pdf.TSMIS_PDF_VS_EXCEL)
    check("matrix store consolidator resolves for highway_detail_pdf",
          matrix_build._pdf_store_consolidator("highway_detail_pdf") is hdpdf)
    modes = {m["id"]: m for m in matrix._row_modes("highway_detail_pdf",
                                                   "highway_detail_pdf", object())}
    check("highway_detail_pdf row modes: env + tsn(fmt=pdf, dataset=highway_detail) "
          "+ vs_excel",
          set(modes) == {"env", "tsn", "vs_excel"}
          and modes["tsn"]["tsn_subdir"] == "highway_detail"
          and modes["tsn"]["fmt"] == "pdf"
          and modes["vs_excel"]["other_subdir"] == "highway_detail")


def test_fallback_recovery():
    """CMP-AUD-054: a page that prints ONLY the 25-cell line-2 band (its line-1
    record is unshaded) recovers its line-1 grid from that page's OWN line-2 band —
    source-backed local geometry that aligns the record correctly, where the old
    document-median fallback shifted every field (and, with no other 10-cell band in
    the document, silently DROPPED the record). A data page with no recoverable grid
    at all now escalates to partial instead of being converted on the median."""
    print("CMP-AUD-054 fallback-grid recovery + escalation:")
    if not hasattr(hdpdf, "_win1_from_l2_band"):
        check("CMP-AUD-054 fix present (_win1_from_l2_band recovers line-1 from line-2)", False)
        return
    from types import SimpleNamespace

    import events as _E
    ev = _E.Events(on_log=lambda *a: None, is_cancelled=lambda: False)

    def _chars(top, text, x0, cw=2.5):
        out, x = [], x0
        for ch in text:
            out.append({"text": ch, "x0": x, "x1": x + cw, "top": top})
            x += cw
        return out

    def _rect(x0, x1, top, h=6.0):
        return {"x0": x0, "x1": x1, "top": top, "bottom": top + h}

    class _FakePdf:
        def __init__(self, pages):
            self.pages = pages

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    # unit: the line-2 -> line-1 base-edge merge (pins the _L1_FROM_L2_EDGES indices)
    win2u = [(float(i * 10), float(i * 10 + 10)) for i in range(hdpdf.N_COLS_L2)]
    check("_win1_from_l2_band merges the 25 line-2 base edges into 10 line-1 windows",
          hdpdf._win1_from_l2_band(win2u)
          == [(0., 10.), (10., 30.), (30., 50.), (50., 60.), (60., 70.),
              (70., 90.), (90., 110.), (110., 120.), (120., 140.), (140., 250.)])
    check("_win1_from_l2_band rejects a non-25-window band (never fabricates a grid)",
          hdpdf._win1_from_l2_band(win2u[:20]) is None
          and hdpdf._win1_from_l2_band([]) is None)

    # e2e: a page with ONLY a 25-cell line-2 band recovers a correctly-aligned record
    edges = [40, 68, 108, 148, 173, 198, 228, 253, 288, 318, 348, 378, 408, 438, 468,
             498, 523, 553, 583, 608, 638, 668, 698, 728, 758, 788]
    band25 = [_rect(edges[i], edges[i + 1], 100.0) for i in range(25)]
    fb_page = SimpleNamespace(
        width=800.0, rects=band25,
        chars=(_chars(90.0, "S005.009", 44.0) + _chars(90.0, "000.083", 72.0)
               + _chars(90.0, "64-01-01", 152.0)
               + _chars(112.0, "TESTDESC", 44.0) + _chars(112.0, "64-01-01", 205.0)))
    saved_open = hdpdf.pdfplumber.open
    try:
        hdpdf.pdfplumber.open = lambda path: _FakePdf([fb_page])
        rows, st = hdpdf.parse_pdf("fake.pdf", ev)
    finally:
        hdpdf.pdfplumber.open = saved_open
    check("recovers exactly one record from the only-line-2-band page (old code dropped it)",
          rows is not None and len(rows) == 1 and st["emitted"] == 1)
    check("...PM / Length / Date of Record / Description correctly aligned (not shifted)",
          bool(rows) and (rows[0][0] or "") == "S005.009" and (rows[0][1] or "") == "000.083"
          and (rows[0][2] or "") == "64-01-01" and (rows[0][9] or "") == "TESTDESC")
    check("...recorded as a validated fallback page; nothing unresolved",
          st["fallback_pages"] == [1] and st["unresolved_pages"] == [])

    # e2e: a data page with NO band escalates (unresolved), never converts on the median
    bandless = SimpleNamespace(width=800.0, rects=[], chars=_chars(90.0, "S007.123", 44.0))
    try:
        hdpdf.pdfplumber.open = lambda path: _FakePdf([bandless])
        _rows2, st2 = hdpdf.parse_pdf("fake2.pdf", ev)
    finally:
        hdpdf.pdfplumber.open = saved_open
    check("a data page with no recoverable grid is unresolved (escalates), not silently converted",
          st2["unresolved_pages"] == [1] and st2["emitted"] == 0)
    check("_has_data_rows: a PM-shaped leading token is data; cover/legend text is not",
          hdpdf._has_data_rows(bandless)
          and not hdpdf._has_data_rows(
              SimpleNamespace(width=800.0, rects=[], chars=_chars(90.0, "LEGEND", 44.0))))


def main():
    test_header()
    test_make_row_mapping()
    test_line1_classifier()
    test_line2_furniture()
    test_wrap_machinery()
    test_adapters_and_matrix()
    test_fallback_recovery()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL HIGHWAY-DETAIL-PDF CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
