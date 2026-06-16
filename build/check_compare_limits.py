"""Golden check for the lower-priority comparison guards (compare_core):
Excel row/column limits + sheet-name collision.

  * excel_limit_error(): a comparison larger than Excel's 1,048,576 rows or
    16,384 columns fails cleanly BEFORE writing, instead of openpyxl raising
    mid-write (which would leave a corrupt partial file) or silently dropping
    columns past the cap.
  * run_compare(): a side label that collides (case-insensitively) with a fixed
    sheet name (Summary / Comparison / Routes / Spot Check / 'Only in …') is
    rejected up front rather than crashing mid-write.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_limits.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from compare_core import (XL_MAX_COLS, XL_MAX_ROWS, CompareSchema,
                          excel_limit_error, run_compare)

ROWS = [["1", "x"], ["2", "y"]]


def test_excel_limit_error():
    assert excel_limit_error(100, 30) is None
    assert excel_limit_error(XL_MAX_ROWS, 30) is None          # exactly at cap
    assert excel_limit_error(XL_MAX_ROWS + 1, 30)              # 1 over → error
    assert "row" in excel_limit_error(XL_MAX_ROWS + 1, 30).lower()
    assert excel_limit_error(100, XL_MAX_COLS + 1)
    assert "column" in excel_limit_error(100, XL_MAX_COLS + 1).lower()


def test_sheet_name_collision():
    out = os.path.join(tempfile.gettempdir(), "_collide.xlsx")
    # A side literally named "Summary" collides with the fixed Summary sheet.
    sc = CompareSchema(report_name="C", header=["Loc", "V"], side_a="Summary",
                       side_b="TSN", id_noun="row", id_noun_plural="rows")
    res = run_compare(sc, ROWS, ROWS, False, out, mode="values")
    assert res.status == "error" and "collides" in res.message, res
    assert not os.path.exists(out), "must not write on a collision"

    # Case-insensitive: "comparison" vs the fixed "Comparison" sheet.
    sc = CompareSchema(report_name="C", header=["Loc", "V"], side_a="A",
                       side_b="comparison", id_noun="row", id_noun_plural="rows")
    res = run_compare(sc, ROWS, ROWS, False, out, mode="values")
    assert res.status == "error" and "collides" in res.message, res

    # A normal pair still works.
    sc = CompareSchema(report_name="C", header=["Loc", "V"], side_a="SSOR-PROD",
                       side_b="ARS-PROD", id_noun="row", id_noun_plural="rows")
    res = run_compare(sc, ROWS, ROWS, False, out, mode="values")
    assert res.status == "ok", res
    os.remove(out)


def main():
    test_excel_limit_error()
    test_sheet_name_collision()
    print("OK  comparison limits: oversize row/column counts fail cleanly before "
          "writing; a side label colliding with a fixed sheet name is rejected.")


if __name__ == "__main__":
    main()
