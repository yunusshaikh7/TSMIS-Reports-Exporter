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


def main():
    test_header()
    test_make_row_mapping()
    test_line1_classifier()
    test_wrap_machinery()
    test_adapters_and_matrix()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL HIGHWAY-DETAIL-PDF CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
