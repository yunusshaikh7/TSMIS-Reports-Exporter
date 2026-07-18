"""CMP-AUD-036 — the Ramp Detail (PDF) source gate requires the full print shape.

`compare_ramp_detail_pdf._load_tsmis_pdf` used to accept any workbook with `PM`
among the first five header cells and `On/Off` anywhere, then expand each row by
position. A truncated four-column `Route/Location/PM/On-Off` workbook was accepted
and every absent field fabricated as blank; an Excel-consolidated pick (no
print-only columns) could also slip through. The gate now requires the EXACT
PDF-consolidated width and the two trailing print-only sentinels (On/Off, Ramp
Type) in order. Both PDF-vs-TSN and PDF-vs-Excel ride this loader.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_ramp_detail_pdf.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_ramp_detail_pdf as rdp
import compare_ramp_detail_tsn as _rd
import consolidate_tsmis_ramp_detail_pdf as cons
from openpyxl import Workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _valid_header():
    # The real PDF-consolidated header: ["Route"] + the consolidator's print
    # HEADER, with the shifted/blank labels rendered as empty strings.
    return ["Route"] + [c if c is not None else "" for c in cons.HEADER]


def _write(path, header, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = _rd.TSMIS_SHEET
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)
    wb.close()


def _refused(path):
    try:
        rdp._load_tsmis_pdf(str(path))
        return None
    except ValueError as e:
        return str(e)


def test_width_mirror():
    print("the gate's expected width mirrors the consolidator (CMP-AUD-036):")
    check("_PDF_WIDTH == 1 + len(consolidator HEADER)",
          rdp._PDF_WIDTH == 1 + len(cons.HEADER))
    check("the print-only sentinels are the HEADER's last two labels",
          rdp._PDF_SENTINELS == tuple(cons.HEADER[-2:]) == ("On/Off", "Ramp Type"))


def test_gate():
    print("the PDF source gate requires the full print shape:")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        valid_h = _valid_header()
        # A full PDF-consolidated workbook loads. The row is read BY POSITION
        # (Route0 Location1 PR2 PM3 Date4 sfx5 HG6 Area4-7 City8 R/U9 Desc10
        # blank11 On/Off12 RampType13), so give Location a real "01-DN-101".
        valid_row = ["001", "01-DN-101", "R", "1.000", "2026-01-01", "", "D",
                     "Y", "C", "U", "9/DESC", "", "N", "D"]
        good = d / "good.xlsx"
        _write(good, valid_h, [valid_row])
        try:
            rows, has_route = rdp._load_tsmis_pdf(str(good))
            check("a full PDF-consolidated workbook is accepted",
                  has_route is True and len(rows) == 1)
        except ValueError as e:
            check("a full PDF-consolidated workbook is accepted", False)
            print("     ->", e)

        # The finding's exact fabricated four-column shape refuses.
        trunc4 = d / "trunc4.xlsx"
        _write(trunc4, ["Route", "Location", "PM", "On/Off"],
               [["001", "01-DN-101", "1.000", "N"]])
        check("a truncated four-column Route/Location/PM/On-Off workbook refuses",
              "PDF-CONSOLIDATED" in (_refused(trunc4) or ""))

        # Both sentinels present but the row is still truncated (< full width).
        trunc5 = d / "trunc5.xlsx"
        _write(trunc5, ["Route", "Location", "PM", "On/Off", "Ramp Type"],
               [["001", "01-DN-101", "1.000", "N", "D"]])
        check("a truncated workbook carrying both sentinels still refuses",
              _refused(trunc5) is not None)

        # An Excel-consolidated pick (the print-only columns dropped) refuses.
        excel = d / "excel.xlsx"
        _write(excel, ["Route"] + [c if c is not None else "" for c in cons.HEADER[:-2]],
               [["001"] + ["x"] * (len(cons.HEADER) - 2)])
        check("an Excel-consolidated pick (no print-only columns) refuses",
              _refused(excel) is not None)

        # Every prefix truncation of the valid header refuses; the full one is
        # the only accepted width.
        all_prefixes_refuse = all(
            _refused_prefix(d, valid_h, k) for k in range(1, len(valid_h)))
        check("every prefix truncation of the valid header refuses",
              all_prefixes_refuse)


def _refused_prefix(d, valid_h, k):
    p = d / f"pre{k}.xlsx"
    _write(p, valid_h[:k], [["001"] + ["x"] * (k - 1)])
    return _refused(p) is not None


def test_side_labels():
    """CMP-AUD-069: the missing-input existence message uses the flavor's OWN
    side labels, not the shared driver's TSMIS/TSN defaults — so a PDF-vs-Excel
    run with a missing second file says 'TSMIS (Excel)', never 'TSN'."""
    print("missing-input diagnostics carry the flavor's side labels (CMP-AUD-069):")
    from events import Events
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        exists = d / "exists.xlsx"
        exists.write_bytes(b"x")            # existence check only stats the path
        missing = d / "missing.xlsx"
        out = d / "out.xlsx"

        def msg(flavor, a, b):
            r = flavor.compare(str(a), str(b), str(out), events=Events(),
                               confirm_overwrite=lambda _p: True)
            return r.status, (r.message or "")

        st, m = msg(rdp.TSMIS_PDF_VS_EXCEL, exists, missing)
        check("PDF-vs-Excel missing 2nd file names 'TSMIS (Excel)', not 'TSN'",
              st == "error" and "TSMIS (Excel)" in m and "TSN" not in m)
        st, m = msg(rdp.TSMIS_PDF_VS_TSN, exists, missing)
        check("PDF-vs-TSN missing 2nd file names 'TSN'", st == "error" and "TSN" in m)
        st, m = msg(rdp.TSMIS_PDF_VS_EXCEL, missing, exists)
        check("missing 1st file names 'TSMIS (PDF)' (not the default 'TSMIS')",
              st == "error" and "TSMIS (PDF)" in m)


def main():
    test_width_mirror()
    test_gate()
    test_side_labels()
    print()
    if _fail:
        print(f"{len(_fail)} CHECK(S) FAILED:")
        for f in _fail:
            print("  -", f)
        sys.exit(1)
    print("ALL COMPARE-RAMP-DETAIL-PDF CHECKS PASSED")


if __name__ == "__main__":
    main()
