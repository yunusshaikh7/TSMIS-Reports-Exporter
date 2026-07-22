"""Evidence is taken from the source the comparison actually READ (CMP-AUD-210).

Both of a report's matrix rows used to be evidenced from the PDF-edition export,
and a candidate was DROPPED whenever that print disagreed with the compared
value. So anything the Excel export holds and the print does not — Highway
Sequence route 037's Description is the censused case — could never be
illustrated at all, and an Excel-only truth looked indistinguishable from "no
verifiable example".

An Excel-compared row is now evidenced from the workbook it was compared from:
sheet, cell address, the row's own neighbouring values. The cell is rendered
only once its own workbook value equals what the comparison compared, which is
the Excel counterpart of the PDF side's parse-back check.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_evidence_source_role.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import visual_evidence as ve
from openpyxl import Workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# --------------------------------------------------------------------------- #
print("which source each row was compared FROM")
check("every '_pdf' row is evidenced from the print, every other from the workbook",
      {rk: ve.tsmis_source_role(rk) for rk in sorted(ve.rows())}
      == {"highway_detail": "excel", "highway_detail_pdf": "pdf",
          "highway_log": "excel", "highway_log_pdf": "pdf",
          "highway_sequence": "excel", "highway_sequence_pdf": "pdf",
          "intersection_detail": "excel", "intersection_detail_pdf": "pdf",
          "ramp_detail": "excel", "ramp_detail_pdf": "pdf"})
check("the role covers exactly the evidence-capable rows",
      set(ve.rows()) == set(ve.TSMIS_PDF_SUBDIR))

# --------------------------------------------------------------------------- #
print("addressing the compared workbook")
_r = Path(tempfile.mkdtemp(prefix="check_ev_role_"))
try:
    _HEADER = ["Route", "Location", "Length (MI) [MI]", "City", "SPD"]
    _ROWS = [["001", "R000.129", "000.075", "DAPT", "65"],
             ["001", "R000.204", "000.027", "DAPT", "65"],
             ["037", "003.809", "000.500", "LODI", "55"]]
    _book = _r / "highway_log_consolidated 2026-07-09 ssor-prod.xlsx"
    _wb = Workbook()
    _ws = _wb.active
    _ws.title = "Highway Log"
    _ws.append(_HEADER)
    for _row in _ROWS:
        _ws.append(_row)
    _wb.save(_book)

    _rows, _header = ve._excel_rows_at(_book, {0, 2})
    check("the header comes back verbatim", _header == _HEADER)
    check("wanted DATA rows map to their real sheet rows (header is row 1)",
          set(_rows) == {0, 2}
          and _rows[0] == ("Highway Log", 2, _ROWS[0])
          and _rows[2] == ("Highway Log", 4, _ROWS[2]))
    check("an empty request reads nothing", ve._excel_rows_at(_book, set()) == ({}, []))
    check("column letters are the ones a user can type into the Name Box",
          [ve._column_letter(n) for n in (1, 3, 26, 27, 28, 52, 53)]
          == ["A", "C", "Z", "AA", "AB", "AZ", "BA"])

    # --------------------------------------------------------------------- #
    print("the Excel cell strip")
    _img = ve._excel_strip(_HEADER, _ROWS[0], 2, (0, 1))
    check("the strip renders and is wide enough to read",
          _img.width > 300 and _img.height > 60)
    check("it boxes the compared cell in the same red the PDF strip uses",
          (220, 20, 20) in [c[1] for c in _img.getcolors(maxcolors=100000)])

    # --------------------------------------------------------------------- #
    print("the TSMIS side of one example")

    class Adapter:
        FIELDS = [f for f in _HEADER[1:] if f != "Location"]
        KEY_LABEL = "Location"

        @staticmethod
        def project(_field, raw):
            return str(raw or "").strip()

    def side(field, va, row_index=0, rows=None, header=None):
        return ve._tsmis_excel_side(
            Adapter, {"row_index": row_index, "va": va}, field,
            _rows if rows is None else rows,
            _HEADER if header is None else header, _book.name)

    _img2, _label, _address, _why = side("Length (MI) [MI]", "000.075")
    check("a matching cell renders, labelled with the workbook and its address",
          _why is None and _img2 is not None and _address == "Highway Log!C2"
          and _label == f"TSMIS (Excel)  —  {_book.name} · Highway Log!C2")
    check("the label says Excel, so the image never poses as a print",
          "TSMIS (Excel)" in _label and "PDF" not in _label)

    _, _, _, _why2 = side("Length (MI) [MI]", "999.999")
    check("a cell that no longer holds the compared value is refused",
          _why2 is not None and "no longer holds" in _why2)
    _, _, _, _why3 = side("Length (MI) [MI]", "000.075", row_index=None)
    check("a candidate with no row position is refused", _why3 is not None)
    _, _, _, _why4 = side("Length (MI) [MI]", "000.075", row_index=99)
    check("a row that is not in the compared workbook is refused",
          _why4 is not None and "not found" in _why4)
    _, _, _, _why5 = side("Nonexistent Column", "000.075")
    check("a column that is not in the workbook header is refused",
          _why5 is not None and "not in the workbook header" in _why5)
    _, _, _, _why6 = side("SPD", "65", rows={0: ("S", 2, ["001", "R000.129"])})
    check("a short workbook row is refused, never read past its end",
          _why6 is not None and "short of the compared column" in _why6)

    # THE FINDING'S CASE: the compared Excel value has no counterpart in the
    # companion print at all. The PDF route can only reject it; the Excel route
    # evidences it, because the workbook is where it was compared from.
    _img3, _label3, _addr3, _why7 = side("City", "LODI", row_index=2)
    check("an Excel value the companion print never carried is still "
          "evidenceable (CMP-AUD-210)",
          _why7 is None and _img3 is not None and _addr3 == "Highway Log!D4")
finally:
    shutil.rmtree(_r, ignore_errors=True)

# --------------------------------------------------------------------------- #
print("every adapter carries the row position its Excel address needs")
for _name in ("evidence_highway_detail", "evidence_highway_log",
              "evidence_highway_sequence", "evidence_intersection_detail",
              "evidence_ramp_detail"):
    _src = Path(__file__).resolve().parent.parent / "scripts" / f"{_name}.py"
    _text = _src.read_text(encoding="utf-8")
    check(f"{_name}.enumerate_diffs emits row_index", "row_index=ia" in _text)

print()
if _fail:
    print(f"FAILED {len(_fail)} check(s):")
    for name in _fail:
        print(f"  - {name}")
    sys.exit(1)
print("check_evidence_source_role: all checks passed")
