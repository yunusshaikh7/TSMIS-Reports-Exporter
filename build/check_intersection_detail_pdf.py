"""Golden check for the TSMIS Intersection Detail (PDF) pipeline.

The PDF consolidator parses a TWO-physical-rows-per-record bordered table whose
un-shaded records carry no cell rects, so the column geometry is derived from the
shaded rowA bands and EVERY line is assigned to that 21-column grid. This check
locks the parts that don't need a real PDF (the live parse is reconciled against
the statewide PDF+Excel corpus off-CI, 218/218 routes, 0 content diffs):

  * the 36-column header equals the site's Excel-export header (one source of truth);
  * the rowA(21) + rowB(18) -> 36-column mapping — including the merged Description
    window and the 'Intrte S' / 'Intrte Route' SWAP the Excel export applies; and
  * the compare adapters + matrix wiring resolve with the right side labels.

CI-safe: pure Python, no browser, no local data files.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import compare_intersection_detail_pdf as cmp_pdf
import consolidate_tsmis_intersection_detail_pdf as idpdf
import matrix
import reports
from intersection_detail_columns import HEADER

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_header():
    print("36-column header (one source of truth, == the Excel export):")
    check("36 columns", len(HEADER) == 36)
    check("Description at index 21", HEADER[21] == "Description")
    # The intersecting-route pair order is the contract the parser honors.
    check("Intrte S precedes Intrte Route (col 30, 31)",
          HEADER[30] == "Intrte S" and HEADER[31] == "Intrte Route")
    check("consolidator pins the shared header", idpdf.INTD_HEADER is HEADER)


def test_make_row_mapping():
    print("_make_row: rowA(21) + rowB(18) -> 36 columns, with the Intrte swap:")
    # rowA grid values 0..20 -> output columns 0..20, tagged by index so a mis-map
    # is obvious. rowB merged-window values (18): [c0, c1, c2, DESC, f7..f20].
    a = [f"a{i}" for i in range(21)]
    b = ["", "", "", "DESC",                 # 0-3: blanks + the merged Description
         "mainLgth", "interEff", "interS", "interL", "interR", "interT", "interN",
         "intStEff", "intrteRoute", "intrteS", "intrtePost", "intrteMile",
         "xingRte", "xingS"]                  # 4-17
    row = idpdf._make_row(a, b)
    check("36 output columns", len(row) == 36)
    check("rowA maps 1:1 to columns 0..20", row[0:21] == a)
    check("Description (col 21) = rowB merged window", row[21] == "DESC")
    check("Main Line Lgth (col 22) = rowB field", row[22] == "mainLgth")
    check("Int St Eff-Date (col 29)", row[29] == "intStEff")
    # THE swap: PDF prints Route(window 12) then S(window 13); Excel writes S then Route.
    check("col 30 'Intrte S'  <- rowB window 13", row[30] == "intrteS")
    check("col 31 'Intrte Route' <- rowB window 12", row[31] == "intrteRoute")
    check("Xing S (col 35) = last rowB field", row[35] == "xingS")


def test_rowb_windows():
    print("_rowb_windows: 18 windows, Description merged across grid cols 3-6:")
    grid = [(i * 10.0, i * 10.0 + 10) for i in range(21)]   # 21 synthetic columns
    rb = idpdf._rowb_windows(grid)
    check("18 windows", len(rb) == 18)
    check("cols 0-2 unchanged", rb[0:3] == grid[0:3])
    check("window 3 spans grid cols 3..6", rb[3] == (grid[3][0], grid[6][1]))
    check("windows 4..17 are grid cols 7..20", rb[4:18] == grid[7:21])


def test_adapters_and_matrix():
    print("compare adapters + matrix wiring resolve:")
    check("PDF-vs-TSN side labels", cmp_pdf.TSMIS_PDF_VS_TSN.file_a_label == "TSMIS (PDF)"
          and cmp_pdf.TSMIS_PDF_VS_TSN.file_b_label == "TSN")
    check("PDF-vs-Excel side labels", cmp_pdf.TSMIS_PDF_VS_EXCEL.file_a_label == "TSMIS (PDF)"
          and cmp_pdf.TSMIS_PDF_VS_EXCEL.file_b_label == "TSMIS (Excel)")
    check("PDF-vs-Excel drops the TSN Notes sheet",
          cmp_pdf.TSMIS_PDF_VS_EXCEL._schema.legend_writer is None)
    check("matrix tsn comparator -> PDF-vs-TSN",
          matrix.tsn_comparator_for("intersection_detail_pdf") is cmp_pdf.TSMIS_PDF_VS_TSN)
    check("intersection_detail_pdf is a matrix row",
          "intersection_detail_pdf" in [k for k, *_ in reports.matrix_rows()])
    modes = {m["id"] for m in matrix._row_modes(
        "intersection_detail_pdf", "intersection_detail_pdf",
        next(a for k, _l, _s, _i, a in reports.matrix_rows() if k == "intersection_detail_pdf"))}
    check("PDF row offers env + tsn + vs_excel modes", modes == {"env", "tsn", "vs_excel"})


def main():
    test_header()
    test_make_row_mapping()
    test_rowb_windows()
    test_adapters_and_matrix()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL INTERSECTION-DETAIL-PDF CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
