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


# --------------------------------------------------------------------------- #
# synthetic-page harness — shared by the CMP-AUD-053 / CMP-AUD-186 parse tests.
# Builds pdfplumber-shaped pages (chars + zebra-band rects) so the real
# parse_pdf runs end to end without a PDF file on disk.
# --------------------------------------------------------------------------- #
L1_EDGES = [40, 90, 130, 165, 195, 225, 265, 305, 345, 385, 520]       # 10 windows
L2_EDGES = [40, 68, 108, 148, 173, 198, 228, 253, 288, 318, 348, 378, 408, 438,
            468, 498, 523, 553, 583, 608, 638, 668, 698, 728, 758, 788]  # 25 windows
# The same 25 windows with a WIDE Description column, the way the print really
# lays line 2 out (the real win2[0] runs to x=384): long description text has to
# fit inside window 0 or the test measures its own geometry instead of the parser.
L2_WIDE = [40, 320] + [320 + 20 * i for i in range(1, 25)]             # 25 windows


def synth_chars(top, text, x0, cw=2.5):
    """One text line's characters, laid out left to right from `x0`."""
    out, x = [], x0
    for ch in text:
        if ch.strip():
            out.append({"text": ch, "x0": x, "x1": x + cw, "top": top})
        x += cw
    return out


def synth_band(edges, top, h=6.0):
    """A zebra-shaded cell band on `edges` — what _page_windows reads."""
    return [{"x0": edges[i], "x1": edges[i + 1] - 1, "top": top, "bottom": top + h}
            for i in range(len(edges) - 1)]


def synth_x(edges, i=0):
    """An x inside window `i` of `edges` (chars land in that column)."""
    return (edges[i] + edges[i + 1]) / 2


def synth_page(chars, rects):
    from types import SimpleNamespace
    return SimpleNamespace(width=800.0, chars=chars, rects=rects)


class SynthPdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def synth_parse(pages):
    """Run the real parse_pdf over synthetic pages."""
    import events as _E
    ev = _E.Events(on_log=lambda *a: None, is_cancelled=lambda: False)
    saved = hdpdf.pdfplumber.open
    try:
        hdpdf.pdfplumber.open = lambda p: SynthPdf(pages)
        return hdpdf.parse_pdf("f.pdf", ev)
    finally:
        hdpdf.pdfplumber.open = saved


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
    # CMP-AUD-051: the statewide 7.9 census found exactly 3 equate-spill shapes;
    # all 3 are rejected (0 residual phantoms) — the two 101 forms above and the
    # unprefixed 280 form here ('14.752 LT EQU 14.760 RT').
    check("rejects an outdented equate DESCRIPTION that starts PM-shaped",
          not hdpdf._is_line1(["R42.401 LT EQ 43.185 , PM R42401BK=43185E AH"])
          and not hdpdf._is_line1(["R42.401 LT EQ 43.1", "85 , PM"])
          and not hdpdf._is_line1(["14.752 LT EQU 14.760 RT"]))
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
    # CMP-AUD-052: the roadbed header is anchored on the LEFTROADBED/RIGHTROADBED
    # compounds (unique to the header), NOT the bare ROADBED/MEDIAN words — so a
    # real date-less description carrying those words parses as data, not furniture.
    check("the roadbed THEAD line matches via LEFT/RIGHT-ROADBED (not bare words)",
          hdpdf.THEAD_RE.search("DESCRIPTIONALEFTROADBEDMEDIANRIGHTROADBED"))
    check("bare 'MEDIAN'/'ROADBED' no longer trigger furniture (real descriptions "
          "'BEGIN MEDIAN' / 'OLD ROADBED' parse as data)",
          not hdpdf.THEAD_RE.search("BEGINMEDIAN")
          and not hdpdf.THEAD_RE.search("OLDROADBEDREMOVED")
          and not hdpdf._is_header_residue("BEGINMEDIAN", False))
    # CMP-AUD-053: the "Acc-Cont" header wrap fragment (a bare "CONT" line) and a
    # dashed-district group header ("— MER 059") are furniture; a real roadbed /
    # description line is NOT (it becomes a paired line-2 or a counted orphan).
    check("_is_header_residue: 'CONT' wrap + dashed-district headers are furniture",
          hdpdf._is_header_residue("CONT", False)
          and hdpdf._is_header_residue("—MER059", False)
          and hdpdf._is_header_residue("—SBD058U", False)
          and not hdpdf._is_header_residue("FIGUEROASTOFFRAMP", False)
          and not hdpdf._is_header_residue("44THSTREET", False))
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


def test_053_leading_orphans():
    """CMP-AUD-053: a data-shaped group that reconciles to NO line-1 (a page-split /
    equate line-2 whose line-1 was already consumed or absent) is now COUNTED and
    escalates the producer to PARTIAL — never silently ignored — while the "ACC-CONT"
    header wrap and a dashed-district group header stay furniture. Not emitted, so
    the output is byte-identical (proven on the 51,201-row corpus off-CI)."""
    print("CMP-AUD-053: unreconciled leading orphans counted + escalate:")
    import events as _E
    import outcome
    L1, L2 = L1_EDGES, L2_EDGES
    c, band, page, parse = synth_chars, synth_band, synth_page, synth_parse

    def w0(edges):
        return synth_x(edges, 0)

    class FakePdf(SynthPdf):
        pass

    bands = band(L1, 90.0) + band(L2, 103.0)
    banner = c(60.0, "RefDate: 2026-07-10 Route 001 Page 1", 40.0)
    rec = (c(100.0, "S000.100", w0(L1) - 10) + c(112.0, "TDESC", w0(L2) - 6)
           + c(112.0, "64-01-01", 200.0))
    rows, st = parse([page(banner + rec, bands)])
    check("clean record pairs; no leading orphan",
          rows is not None and len(rows) == 1 and st["leading_orphans"] == 0)

    # A data-shaped group printed before ANY line 1 has nothing to reconcile to.
    orphan = c(78.0, "44THSTREET", w0(L1) - 12) + c(78.0, "64-01-01", 200.0)
    rows, st = parse([page(banner + orphan + rec, bands)])
    check("a dated data line with no line-1 is a COUNTED orphan (not emitted)",
          len(rows) == 1 and st["leading_orphans"] == 1
          and st["orphan_samples"] and st["orphan_samples"][0][0] == 1)

    # The other half of the 053 hazard, after CMP-AUD-186 made an open record
    # absorb following groups: a FOREIGN line 2 landing on an already-complete
    # record. It is merged (never dropped) but its cells COLLIDE with values the
    # record already had, which is counted and escalates — so a line 1 the parser
    # failed to recognize can still never pass as a clean merge.
    foreign = c(130.0, "44THSTREET", w0(L2) - 12) + c(130.0, "64-01-01", 200.0)
    rows, st = parse([page(banner + rec + foreign, bands)])
    check("a foreign line-2 merged onto a complete record COLLIDES (counted)",
          len(rows) == 1 and st["continuation_lines"] == 1
          and st["continuation_collisions"] >= 1)

    furn = c(130.0, "CONT", w0(L1) - 5) + c(140.0, "—MER059", w0(L1) - 8)
    rows, st = parse([page(banner + rec + furn, bands)])
    check("'CONT' wrap + dashed-district header are furniture, not orphans",
          st["leading_orphans"] == 0 and st["continuation_lines"] == 0)

    # e2e: the orphan escalates the producer to PARTIAL with a structured
    # parse-anomalies diagnostic, and NOT the file-count fields (CMP-AUD-064).
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="cmp053_"))
    try:
        in_dir = tmp / "in"
        in_dir.mkdir()
        (in_dir / "highway_detail_route_001.pdf").write_bytes(b"%PDF-1.4\n%stub\n")
        saved = hdpdf.pdfplumber.open
        try:
            hdpdf.pdfplumber.open = lambda p: FakePdf([page(banner + orphan + rec, bands)])
            result = hdpdf.consolidate(
                events=_E.Events(on_log=lambda *a: None),
                confirm_overwrite=lambda _p: True,
                input_dir=in_dir, out_path=tmp / "out.xlsx", converted_dir=tmp / "conv")
        finally:
            hdpdf.pdfplumber.open = saved
        check(f"e2e: leading orphan escalates to PARTIAL (completion={result.completion!r})",
              result.completion == outcome.PARTIAL)
        pe = (result.producer_extra or {}).get("parse_anomalies", {})
        check(f"e2e: rides parse_anomalies, NOT the file counts (pe={pe}, "
              f"skipped={result.skipped_inputs}, failed={result.failed_inputs})",
              pe.get("leading_orphan_lines") == 1 and result.skipped_inputs == 0
              and result.failed_inputs == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_186_multibaseline_line2():
    """CMP-AUD-186: a logical line 2 can print as SEVERAL physical baselines whose
    tops sit further apart than ROW_GAP (a long Description wraps at the ~11pt print
    line height, so _row_groups hands the wraps over as separate groups). The record
    now stays OPEN and every following non-furniture group merges into its cells;
    it is emitted at the next line 1, a DCR boundary, or the document end.

    Before this, the first baseline was taken as the whole line 2 and the rest were
    dropped as leading orphans — route 395's `R000.000E` came out with its
    Description truncated mid-word and all 23 attribute cells blank, while the run
    still reported complete."""
    print("CMP-AUD-186: multi-baseline line 2 merges (never truncates):")
    L1, L2 = L1_EDGES, L2_WIDE
    bands = synth_band(L1, 90.0) + synth_band(L2, 103.0)
    banner = synth_chars(60.0, "RefDate: 2026-08-17 Route 395 Page 1", 40.0)

    def line1(top, pm):
        return synth_chars(top, pm, L1[0] + 4)

    def desc(top, text):
        return synth_chars(top, text, L2[0] + 4)

    def attr(top, text, col):
        return synth_chars(top, text, L2[col] + 2, cw=2.0)

    # One record whose line 2 prints as three baselines 12pt apart (> ROW_GAP):
    # description / description+attributes / description tail.
    rec = (line1(100.0, "R000.000E")
           + desc(114.0, "KERN/INYO CO LINE / BEGIN RT")
           + desc(126.0, "INDEP ALIGN / NEVADA STATE")
           + attr(126.0, "86-08-07", 2) + attr(126.0, "H", 3)
           + desc(138.0, "LINE-BEG L"))
    nxt = line1(160.0, "R003.981") + desc(174.0, "JCT15.")
    rows, st = synth_parse([synth_page(banner + rec + nxt, bands)])

    check("both records emitted, in document order",
          rows is not None and len(rows) == 2
          and (rows[0][0] or "") == "R000.000E" and (rows[1][0] or "") == "R003.981")
    check("the three description baselines rejoin into ONE Description "
          f"({(rows[0][9] if rows else None)!r})",
          bool(rows) and (rows[0][9] or "")
          == "KERN/INYO CO LINE / BEGIN RT INDEP ALIGN / NEVADA STATE LINE-BEG L")
    check("...and the attributes printed on a LATER baseline survive "
          "(they used to be blanked)",
          bool(rows) and (rows[0][11] or "") == "86-08-07" and (rows[0][12] or "") == "H")
    check("the continuations are counted, not orphaned",
          st["continuation_lines"] == 2 and st["leading_orphans"] == 0
          and st["single_line"] == 0)
    check("the continuation samples name their page",
          len(st["continuation_samples"]) == 2
          and all(s[0] == 1 for s in st["continuation_samples"]))

    # A DCR group row CLOSES the accumulating line 2 — a following data group
    # belongs to the NEXT record, never to the one before the boundary.
    dcr = synth_chars(150.0, "08 SBD 395", L1[0] + 4)
    stray = desc(162.0, "STRAYLINE") + attr(162.0, "64-01-01", 2)
    rows2, st2 = synth_parse([synth_page(banner + rec + dcr + stray, bands)])
    check("a DCR group row closes the record; a group after it is NOT merged in",
          rows2 is not None and len(rows2) == 1
          and (rows2[0][9] or "")
          == "KERN/INYO CO LINE / BEGIN RT INDEP ALIGN / NEVADA STATE LINE-BEG L"
          and st2["leading_orphans"] == 1)

    # A continuation may cross a physical page break: the browser reprints the
    # table header, which stays furniture, and the open record absorbs the rest.
    thead = synth_chars(60.0, "POSTMILE LENGTH RECORD", 40.0)
    p1 = synth_page(banner + line1(100.0, "R000.000E") + desc(114.0, "FIRST HALF"), bands)
    p2 = synth_page(thead + desc(100.0, "SECOND HALF")
                    + attr(100.0, "86-08-07", 2), bands)
    rows3, st3 = synth_parse([p1, p2])
    check("a continuation crosses a page break (reprinted header stays furniture)",
          rows3 is not None and len(rows3) == 1
          and (rows3[0][9] or "") == "FIRST HALF SECOND HALF"
          and (rows3[0][11] or "") == "86-08-07" and st3["leading_orphans"] == 0)

    # A record that printed NO second line at all is still the single_line case.
    only1 = synth_page(banner + line1(100.0, "R000.000E") + line1(130.0, "R003.981"), bands)
    rows4, st4 = synth_parse([only1])
    check("a record with no line 2 at all is still emitted with a blank tail",
          rows4 is not None and len(rows4) == 2 and st4["single_line"] == 2
          and all(v is None for v in rows4[0][9:]))

    # e2e: merged continuations ride a durable diagnostic but stay COMPLETE —
    # merging IS the correct reading of the print (CMP-AUD-186), unlike an orphan.
    import shutil
    import tempfile

    import events as _E
    import outcome
    tmp = Path(tempfile.mkdtemp(prefix="cmp186_"))
    try:
        in_dir = tmp / "in"
        in_dir.mkdir()
        (in_dir / "highway_detail_route_395.pdf").write_bytes(b"%PDF-1.4\n%stub\n")
        saved = hdpdf.pdfplumber.open
        try:
            hdpdf.pdfplumber.open = lambda p: SynthPdf(
                [synth_page(banner + rec + nxt, bands)])
            result = hdpdf.consolidate(
                events=_E.Events(on_log=lambda *a: None),
                confirm_overwrite=lambda _p: True,
                input_dir=in_dir, out_path=tmp / "out.xlsx", converted_dir=tmp / "conv")
        finally:
            hdpdf.pdfplumber.open = saved
        pe = (result.producer_extra or {}).get("parse_anomalies", {})
        check(f"e2e: continuations stay COMPLETE (completion={result.completion!r})",
              result.completion == outcome.COMPLETE)
        check(f"e2e: recorded durably in parse_anomalies (pe={pe})",
              pe.get("continuation_lines") == 2 and "leading_orphan_lines" not in pe)
        check("e2e: and named in the summary",
              any("CMP-AUD-186" in ln for ln in (result.summary_lines or [])))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    test_header()
    test_make_row_mapping()
    test_line1_classifier()
    test_line2_furniture()
    test_wrap_machinery()
    test_adapters_and_matrix()
    test_fallback_recovery()
    test_053_leading_orphans()
    test_186_multibaseline_line2()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL HIGHWAY-DETAIL-PDF CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
