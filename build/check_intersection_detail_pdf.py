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


# --------------------------------------------------------------------------- #
# CMP-AUD-056..062 — parse-loop reconciliation hardening. Driven by precise
# synthetic pages (exact char/rect coordinates, monkeypatched pdfplumber.open) so
# the parser's real classification runs without font-metric ambiguity. Every
# defect scenario is 0-occurrence on the statewide 7.9 corpus (16,459/16,459 rows,
# byte-identical fixed vs unfixed), so each fix is a detection->PARTIAL escalation
# that is a no-op on real data — these tests pin the escalation + the clean-render
# no-op.
# --------------------------------------------------------------------------- #
def _cells(widths, x0=20.0, gap=2.0):
    cells, x = [], x0
    for w in widths:
        cells.append((x, x + w))
        x += w + gap
    return cells


# Non-uniform cells so the Post Mile / Location / Description columns are wide
# enough for their tokens (the real print sizes them to content).
_A_CELLS = _cells([10, 42, 10, 64] + [16] * 17)          # 21 rowA cells
_B_CELLS = _cells([10, 34, 10, 90] + [16] * 14)          # 18 rowB cells


def _ac(i):
    return (_A_CELLS[i][0] + _A_CELLS[i][1]) / 2


def _bc(i):
    return (_B_CELLS[i][0] + _B_CELLS[i][1]) / 2


def _band(cells, top, dx=0.0, h=7.0):
    return [{"x0": c[0] + dx, "x1": c[1] + dx, "top": top, "bottom": top + h}
            for c in cells]


def _line(top, items, cw=2.5):
    """Chars for one text line: each (center, text) placed centered at `center`;
    spaces advance x but aren't emitted (they're gaps, like real extraction)."""
    out = []
    for center, text in items:
        x = center - (len(text) * cw) / 2
        for ch in text:
            if ch.strip():
                out.append({"text": ch, "x0": x, "x1": x + cw, "top": top})
            x += cw
    return out


class _FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _page(chars, rects, width=612.0):
    from types import SimpleNamespace
    return SimpleNamespace(width=width, chars=chars, rects=rects)


def _rowA_line(top, pm="000.204", loc="12 ORA 001", vestigial=None):
    items = [(_ac(1), pm), (_ac(3), loc)]
    if vestigial is not None:
        items.append((_ac(20), vestigial))
    return _line(top, items)


def _rowB_line(top, num="11050", desc="MAIN ST"):
    items = [(_bc(1), num)]
    if desc:
        items.append((_bc(3), desc))
    return _line(top, items)


def _cover_page(route="001"):
    """A cover page carrying the document's own ROUTE parameter (CMP-AUD-049), so
    reconcile_route_identity can confirm the route in the consolidate() e2e."""
    return _page(_line(60.0, [(120.0, f"ROUTE : {route}")]), [])


def _parse(pages):
    """Run the REAL parse_pdf against synthetic pages."""
    import events as _E
    saved = idpdf.pdfplumber.open
    try:
        idpdf.pdfplumber.open = lambda path: _FakePdf(pages)
        return idpdf.parse_pdf("fake.pdf", _E.Events(on_log=lambda *a: None,
                                                     is_cancelled=lambda: False))
    finally:
        idpdf.pdfplumber.open = saved


def test_reconciliation_hardening():
    print("CMP-AUD-056..062: parse-loop reconciliation counters + escalation:")

    # unit: _is_rowB requires BOTH the integer AND a Description (058)
    b_ok = ["", "11050", "", "MAIN ST"] + [""] * 14
    b_bare = ["", "2026", "", ""] + [""] * 14                # numeric furniture
    check("058: rowB needs integer AND description (bare integer rejected)",
          idpdf._is_rowB(b_ok) and not idpdf._is_rowB(b_bare))

    # a shaded record (rowA 21-band + rowB 18-band) establishes both grids; the
    # record's two text lines pair into one row.
    clean = _page(_rowA_line(100.0) + _rowB_line(112.0),
                  _band(_A_CELLS, 100.0) + _band(_B_CELLS, 112.0))
    rows, st = _parse([clean])
    check("clean rowA+rowB pairs into exactly one record (grids derive)",
          rows is not None and len(rows) == 1 and st["emitted"] == 1)
    check("clean render: every reconciliation counter is 0 (no false escalation)",
          st["orphans"] == 0 and st["leading_orphan_b"] == 0
          and st["wrapped_rowb"] == 0 and st["vestigial"] == 0
          and st["old_pm_hits"] == 0 and st["geom_divergent_pages"] == 0)

    # 058 e2e: a numeric-furniture line (integer in win1, NO description) between a
    # rowA and its real rowB must NOT be consumed as the rowB — the REAL record
    # (with its description) is emitted, not a blank one.
    p058 = _page(_rowA_line(100.0)
                 + _rowB_line(112.0, num="2026", desc="")     # furniture
                 + _rowB_line(124.0, num="11050", desc="REAL ST"),
                 _band(_A_CELLS, 100.0) + _band(_B_CELLS, 112.0))
    rows, st = _parse([p058])
    check("058: numeric furniture doesn't hijack the record — the REAL rowB pairs",
          rows is not None and len(rows) == 1 and rows[0][20] == "REAL ST")

    # 057: a complete rowB with no rowA pending is a leading orphan (was silently
    # treated as furniture)
    p057 = _page(_rowB_line(100.0) + _rowA_line(120.0) + _rowB_line(132.0),
                 _band(_A_CELLS, 120.0) + _band(_B_CELLS, 132.0))
    rows, st = _parse([p057])
    check("057: a leading rowB with no rowA is counted (leading_orphan_b>=1)",
          st["leading_orphan_b"] >= 1)

    # 060: rowA data in the dropped 21st column escalates (was warned, stayed complete)
    p060 = _page(_rowA_line(100.0, vestigial="DRIFT") + _rowB_line(112.0),
                 _band(_A_CELLS, 100.0) + _band(_B_CELLS, 112.0))
    rows, st = _parse([p060])
    check("060: a value in the vestigial 21st rowA column is counted + kept in "
          "diagnostics", st["vestigial"] == 1 and st["vestigial_cells"] == [(1, "DRIFT")])

    # 059: a PRE-update unpadded postmile alongside current rows (mixed edition)
    p059 = _page(_line(140.0, [(_ac(1), "0.204"), (_ac(3), "12 ORA 001")])
                 + _rowA_line(100.0) + _rowB_line(112.0),
                 _band(_A_CELLS, 100.0) + _band(_B_CELLS, 112.0))
    rows, st = _parse([p059])
    check("059: a legacy unpadded-postmile row alongside current rows is counted "
          "(old_pm_hits>=1, rows>0)", st["old_pm_hits"] >= 1 and len(rows) >= 1)

    # 056: a Description continuation baseline right below a rowB (a wrap) is counted
    p056 = _page(_rowA_line(100.0) + _rowB_line(112.0)
                 + _line(118.0, [(_bc(3), "WRAPPED CONT")]),   # desc-only, +6pt
                 _band(_A_CELLS, 100.0) + _band(_B_CELLS, 112.0))
    rows, st = _parse([p056])
    check("056: a desc-only continuation just below a rowB is counted (wrapped_rowb>=1)",
          st["wrapped_rowb"] >= 1)

    # 062: a second page whose own band grid is shifted past the tolerance is flagged
    pg1 = _page(_rowA_line(100.0) + _rowB_line(112.0),
                _band(_A_CELLS, 100.0) + _band(_B_CELLS, 112.0))
    pg2 = _page(_rowA_line(100.0, pm="000.500", loc="12 ORA 001") + _rowB_line(112.0),
                _band(_A_CELLS, 100.0, dx=60.0) + _band(_B_CELLS, 112.0, dx=60.0))
    rows, st = _parse([pg1, pg2])
    check("062: a page whose column grid diverges from the doc median is flagged "
          f"(geom_divergent_pages>=1, got {st['geom_divergent_pages']})",
          st["geom_divergent_pages"] >= 1)

    # e2e escalation: a clean render stays COMPLETE; an anomaly escalates the
    # producer to PARTIAL with the structured parse-anomalies diagnostic (never the
    # file-count fields — CMP-AUD-064).
    import outcome
    import shutil
    import tempfile
    import events as _E
    for tag, pages, expect_complete in (
            ("clean", [clean], True),
            ("vestigial", [p060], False)):
        tmp = Path(tempfile.mkdtemp(prefix="cmp_id_"))
        try:
            in_dir = tmp / "in"
            in_dir.mkdir()
            stub = in_dir / "intersection_detail_route_001.pdf"
            stub.write_bytes(b"%PDF-1.4\n%stub\n")
            saved = idpdf.pdfplumber.open
            try:
                idpdf.pdfplumber.open = lambda path: _FakePdf([_cover_page()] + pages)
                result = idpdf.consolidate(
                    events=_E.Events(on_log=lambda *a: None),
                    confirm_overwrite=lambda _p: True,
                    input_dir=in_dir, out_path=tmp / "out.xlsx",
                    converted_dir=tmp / "conv")
            finally:
                idpdf.pdfplumber.open = saved
            if expect_complete:
                check(f"e2e {tag}: stays COMPLETE (completion={result.completion!r})",
                      result.completion == outcome.COMPLETE)
            else:
                check(f"e2e {tag}: escalates to PARTIAL (completion={result.completion!r})",
                      result.completion == outcome.PARTIAL)
                pe = (result.producer_extra or {}).get("parse_anomalies", {})
                check(f"e2e {tag}: rides parse_anomalies, NOT the file counts "
                      f"(pe={pe}, skipped={result.skipped_inputs})",
                      pe.get("vestigial_cells") == 1 and result.skipped_inputs == 0
                      and result.failed_inputs == 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_061_cancellation():
    """CMP-AUD-061: cancelling DURING the document geometry scan returns a distinct
    cancelled outcome (None, None) promptly — polling between pages — instead of
    scanning every page/rectangle first and then reporting an unreadable/no-grid
    error."""
    print("CMP-AUD-061: cancellation during the geometry scan:")

    class _CancelAfter:
        def __init__(self, n):
            self.calls = 0
            self.n = n

        def is_cancelled(self):
            self.calls += 1
            return self.calls > self.n

        def on_log(self, *a, **k):
            pass

    bands = _band(_A_CELLS, 100.0) + _band(_B_CELLS, 112.0)
    pages = [_page(_rowA_line(100.0) + _rowB_line(112.0), bands) for _ in range(8)]
    ev = _CancelAfter(2)
    wa, wb = idpdf._doc_windows(_FakePdf(pages), ev)
    check(f"_doc_windows returns (None,None) on cancel + stops early (scanned "
          f"~{ev.calls} of 8 pages, not all)",
          wa is None and wb is None and ev.calls < 8)
    # _doc_windows with no events still derives the grid (backward compatible)
    wa2, wb2 = idpdf._doc_windows(_FakePdf(pages))
    check("_doc_windows(no events) still derives BOTH grids",
          wa2 is not None and wb2 is not None)
    # parse_pdf distinguishes cancelled (None, None) from no-grid ([], {no_grid:True})
    saved = idpdf.pdfplumber.open
    try:
        idpdf.pdfplumber.open = lambda p: _FakePdf(pages)
        rows, stats = idpdf.parse_pdf("f.pdf", _CancelAfter(3))
    finally:
        idpdf.pdfplumber.open = saved
    check("parse_pdf returns cancelled (None, None), not a no_grid result",
          rows is None and stats is None)


def main():
    test_header()
    test_discriminators()
    test_make_row_mapping()
    test_grid_shapes()
    test_adapters_and_matrix()
    test_matrix_consolidated_filenames()
    test_reconciliation_hardening()
    test_061_cancellation()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL INTERSECTION-DETAIL-PDF CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
