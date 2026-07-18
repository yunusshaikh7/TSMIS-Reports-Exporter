"""Golden check for the TSMIS Intersection Detail (PDF) pipeline.

The PDF consolidator parses a TWO-physical-rows-per-record bordered table whose
un-shaded records carry no cell rects, so the column geometry is derived from the
shaded records' 21-cell (rowA) and 18-cell (rowB) bands and EVERY line is
assigned to those grids. This check locks the parts that don't need a real PDF
(the live parse is reconciled against the statewide PDF+Excel corpus off-CI —
July 2026 format: 217/217 routes, 16,459/16,459 rows, 0 orphans, 0 non-whitespace
content diffs):

  * the 35-column header equals the site's July-2026 Excel-export header (one
    source of truth);
  * the rowA/rowB line discriminators — a rowA carries the zero-padded postmile,
    a rowB the plain-integer print-only intersection number, a PRE-update rowA
    the unpadded postmile that triggers the old-layout refusal; and
  * the rowA(21) + rowB(18) -> 35-column mapping — including the merged
    Description window, the 'Intrte S' / 'Intrte Route' SWAP the Excel export
    applies, the discarded vestigial rowA column + intersection number, and the
    July-2026 'Xing P/S' / 'Xing Line Lgth' tail; and
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
from intersection_detail_columns import DESC_IDX, HEADER

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_header():
    print("35-column header (one source of truth, == the July-2026 Excel export):")
    check("35 columns", len(HEADER) == 35)
    check("Description at index 20 (DESC_IDX)",
          HEADER[20] == "Description" and DESC_IDX == 20)
    # The intersecting-route pair order is the contract the parser honors.
    check("Intrte S precedes Intrte Route (col 29, 30)",
          HEADER[29] == "Intrte S" and HEADER[30] == "Intrte Route")
    check("the July-2026 tail: Xing P/S then Xing Line Lgth",
          HEADER[33] == "Xing P/S" and HEADER[34] == "Xing Line Lgth")
    check("the duplicated second 'ML Eff-Date' is gone",
          HEADER.count("ML Eff-Date") == 1)
    check("consolidator pins the shared header", idpdf.INTD_HEADER is HEADER)


def test_discriminators():
    print("rowA/rowB/old-layout line discriminators:")
    # rowA: zero-padded postmile + a real Location.
    a = [""] * 21
    a[1], a[3] = "000.204", "12 ORA 001"
    check("padded PM + Location classifies rowA", idpdf._is_rowA(a))
    # A rowB (integer intersection number in column 1) must NOT classify as rowA
    # even when its Description window pattern-matches a Location ('10 TH AVE').
    b = [""] * 21
    b[1], b[3] = "11050", "10 TH AVE RT OID"
    check("a rowB's integer never classifies rowA", not idpdf._is_rowA(b))
    check("rowB pairing keys on the integer intersection number",
          idpdf.INT_ROWB_RE.match("11050") and not idpdf.INT_ROWB_RE.match("000.204"))
    # PRE-update postmiles are unpadded — the old-layout refusal's detector.
    check("old-layout detector matches '0.204'/'30.321' but not '000.204'",
          idpdf.OLD_PM_RE.match("0.204") and idpdf.OLD_PM_RE.match("30.321")
          and not idpdf.OLD_PM_RE.match("000.204"))
    check("header furniture fails the rowA test",
          not idpdf._is_rowA(["P", "POST", "P", "DATE OF"] + [""] * 17))


def test_make_row_mapping():
    print("_make_row: rowA(21) + rowB(18) -> 35 columns, with the Intrte swap:")
    # rowA grid values 0..20 -> output columns 0..19, tagged by index so a mis-map
    # is obvious; a20 is the vestigial dropped column (never emitted). rowB:
    # [c0, INT_NUMBER, c2, DESC, f4..f17].
    a = [f"a{i}" for i in range(21)]
    b = ["", "11050", "", "DESC",            # 0-3: blanks + number + Description
         "mainLgth", "interEff", "interS", "interL", "interR", "interT", "interN",
         "intStEff", "intrteRoute", "intrteS", "intrtePost", "intrteMile",
         "xingPS", "xingLineLgth"]           # 4-17
    row = idpdf._make_row(a, b)
    check("35 output columns", len(row) == 35)
    check("rowA maps 1:1 to columns 0..19", row[0:20] == a[0:20])
    check("the vestigial rowA column 20 is NOT emitted", "a20" not in row)
    check("the print-only intersection number is NOT emitted", "11050" not in row)
    check("Description (col 20) = rowB merged window", row[20] == "DESC")
    check("Main Line Lgth (col 21) = rowB field", row[21] == "mainLgth")
    check("Int St Eff-Date (col 28)", row[28] == "intStEff")
    # THE swap: PDF prints Route(window 12) then S(window 13); Excel writes S then Route.
    check("col 29 'Intrte S'  <- rowB window 13", row[29] == "intrteS")
    check("col 30 'Intrte Route' <- rowB window 12", row[30] == "intrteRoute")
    check("col 33 'Xing P/S' <- rowB window 16", row[33] == "xingPS")
    check("Xing Line Lgth (col 34) = last rowB field", row[34] == "xingLineLgth")


def test_grid_shapes():
    print("document grids: rowA 21 cells (vestigial tail), rowB 18 (own bands):")
    check("N_COLS_A/BOTH band shapes pinned", idpdf.N_COLS_A == 21 and idpdf.N_COLS_B == 18)
    check("_doc_windows derives BOTH shapes (no rowB merge derivation)",
          callable(idpdf._doc_windows) and not hasattr(idpdf, "_rowb_windows"))


def test_adapters_and_matrix():
    print("compare adapters + matrix wiring resolve:")
    check("PDF-vs-TSN side labels", cmp_pdf.TSMIS_PDF_VS_TSN.file_a_label == "TSMIS (PDF)"
          and cmp_pdf.TSMIS_PDF_VS_TSN.file_b_label == "TSN")
    check("PDF-vs-Excel side labels", cmp_pdf.TSMIS_PDF_VS_EXCEL.file_a_label == "TSMIS (PDF)"
          and cmp_pdf.TSMIS_PDF_VS_EXCEL.file_b_label == "TSMIS (Excel)")
    check("PDF-vs-Excel drops the TSN Notes sheet",
          cmp_pdf.TSMIS_PDF_VS_EXCEL._schema.legend_writer is None)
    # The vs-TSN flavor builds the two-line 'Report View' replica the Excel-sourced
    # comparison has (added per-call so its writer can read the two input paths); the
    # same-source PDF-vs-Excel self-check does not (TSN-specific soft/structural
    # semantics don't apply to two TSMIS renders).
    sc_tsn = cmp_pdf.TSMIS_PDF_VS_TSN._schema_for("a.xlsx", "b.xlsx")
    check("PDF-vs-TSN builds a Report View (like Excel-vs-TSN)",
          sc_tsn.extra_sheet_writer is not None
          and sc_tsn.report_view_diff_check == ("Report View", "B", 2))
    sc_ex = cmp_pdf.TSMIS_PDF_VS_EXCEL._schema_for("a.xlsx", "b.xlsx")
    check("PDF-vs-Excel has NO Report View",
          sc_ex.extra_sheet_writer is None and not sc_ex.report_view_diff_check)
    check("matrix tsn comparator -> PDF-vs-TSN",
          matrix.tsn_comparator_for("intersection_detail_pdf") is cmp_pdf.TSMIS_PDF_VS_TSN)
    check("intersection_detail_pdf is a matrix row",
          "intersection_detail_pdf" in [k for k, *_ in reports.matrix_rows()])
    modes = {m["id"] for m in matrix._row_modes(
        "intersection_detail_pdf", "intersection_detail_pdf",
        next(a for k, _l, _s, _i, a in reports.matrix_rows() if k == "intersection_detail_pdf"))}
    check("PDF row offers env + tsn + vs_excel modes", modes == {"env", "tsn", "vs_excel"})


def test_matrix_consolidated_filenames():
    # Regression for the v0.17.3 field crash: day_matrix_info -> consolidated_state
    # -> _consolidated_filename raised ValueError for intersection_detail_pdf because
    # it wasn't wired alongside highway_log_pdf (it's absent from _CONSOLIDATOR_BY_SUBDIR
    # by design, needing a scratch converted_dir). Lock that EVERY matrix row — and
    # every by-day row — resolves a consolidated filename + state without raising, so a
    # future half-wired PDF row can't ship.
    print("every matrix/by-day row resolves a consolidated filename (no crash):")
    import tempfile
    import day_matrix
    from pathlib import Path
    subdirs = {sub for _k, _l, sub, _i, _a in reports.matrix_rows()}
    subdirs |= {sub for _k, _l, sub, *_ in day_matrix._day_rows()}
    for sub in sorted(subdirs):
        try:
            fn = matrix._consolidated_filename(sub)
            d = Path(tempfile.mkdtemp()) / "2026-07-08 ssor-prod" / sub
            d.mkdir(parents=True)
            matrix.consolidated_state(str(d), sub)        # the exact crashing call
            ok = bool(fn)
        except Exception as e:                            # noqa: BLE001
            ok = False
            print(f"      {sub}: {type(e).__name__}: {e}")
        check(f"{sub}: consolidated filename + state resolve", ok)
    check("intersection_detail_pdf filename is the PDF consolidator's",
          matrix._consolidated_filename("intersection_detail_pdf")
          == idpdf.FILENAME)


def main():
    test_header()
    test_discriminators()
    test_make_row_mapping()
    test_grid_shapes()
    test_adapters_and_matrix()
    test_matrix_consolidated_filenames()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL INTERSECTION-DETAIL-PDF CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
