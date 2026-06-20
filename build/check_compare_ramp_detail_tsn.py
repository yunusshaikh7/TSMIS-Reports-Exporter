"""Golden check for the TSMIS-vs-TSN Ramp Detail comparator
(scripts/compare_ramp_detail_tsn.py) — the reference v0.17.0 vs-TSN recipe.

Locks: the CompareSchema wiring (PM key + the TSN-only context fields), route
extraction from the TSN LOCATION, PM/date/description normalization, the
position-based TSMIS-consolidated loader, the route+PM key collapsing a mid-list
insert to a single one-sided ramp (no phantom cascade), and — the property the
opt-in `context_fields` exists for — that a context column NEVER contributes a diff
cell while a compared column does. End-to-end through the real compare()/VALUES
workbook, read back with openpyxl (no Excel, CI-safe).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_ramp_detail_tsn.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_ramp_detail_tsn as rd
from events import Events
from openpyxl import Workbook, load_workbook

_fail = []
DIFF = " ≠ "          # the ≠ marker count_diffs / the workbook key on


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# Consolidated TSMIS layout BY POSITION (Route prepended; labels shift right of
# City Code/R/U/Description, which is why the loader reads by position).
_TSMIS_HDR = ["Route", "Location", "", "PM", "Date of Record", "", "HG", "Area 4",
              "", "City Code", "R/U", "Description"]


def _tsmis_row(route, loc, pr, pm, date, hg, area4, city, ru, desc):
    return [route, loc, pr, pm, date, "", hg, area4, city, ru, desc, ""]


def _write_tsmis(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = rd.TSMIS_SHEET
    ws.append(_TSMIS_HDR)
    for r in rows:
        ws.append(r)
    wb.save(path)
    wb.close()


def _write_tsn(path, rows):
    """rows: [route, PR, PM, Date, HG, Area4, City, R/U, Desc, RampName, OnOff, RampType, ADT]"""
    wb = Workbook()
    ws = wb.active
    ws.title = rd.NORMALIZED_SHEET
    ws.append(["Route"] + rd.SHARED_HEADER)
    for r in rows:
        ws.append(r)
    wb.save(path)
    wb.close()


def _comparison(path):
    """(header, rows) of the Comparison sheet from a VALUES workbook."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Comparison"]
        it = ws.iter_rows(values_only=True)
        header = [("" if c is None else str(c)) for c in next(it)]
        rows = [["" if c is None else str(c) for c in r] for r in it
                if r and any(c not in (None, "") for c in r)]
        return header, rows
    finally:
        wb.close()


def test_schema():
    print("schema wiring:")
    sc = rd._SCHEMA
    check("key_field is PM", sc.header[sc.key_field] == "PM" and sc.key_field == rd.KEY_FIELD)
    check("side names TSMIS / TSN", sc.side_a == "TSMIS" and sc.side_b == "TSN")
    check("context_fields = the 4 TSN-only columns",
          set(sc.context_fields) == {"Ramp Name", "On/Off", "Ramp Type", "ADT"})
    check("Date of Record is a date field", "Date of Record" in sc.date_fields)
    check("route from TSN LOCATION '01-DN-101' -> '101'",
          rd._tsn_raw_row(["x", "x", "01-DN-101"], {"LOCATION": 2})[0] == "101")
    check("PM normalizes ' 000.606' and '0.606' to the same canon",
          rd._norm_pm(" 000.606") == rd._norm_pm("0.606") == "0.606")
    check("date ISO from both formats",
          rd._iso_date("02/25/1976") == "1976-02-25"
          and rd._iso_date("1992-09-28 00:00:00") == "1992-09-28")
    check("description drops the TSMIS '001/' route prefix",
          rd._strip_desc_prefix("001/NB OFF TO DOHENY") == "NB OFF TO DOHENY")


def test_end_to_end():
    print("end-to-end VALUES workbook (counts + context non-asserting):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_rd_tsn_"))
    a = root / "tmsis.xlsx"
    b = root / "tsn.xlsx"
    out = root / "cmp.xlsx"
    # Two routes. Matched PMs with: an identical row, a COMPARED diff (HG), a
    # CONTEXT-only value (Ramp Type, TSMIS blank), and one-sided ramps on each side.
    _write_tsmis(a, [
        _tsmis_row("001", "12-ORA-001", "R", "000.606", "02/25/1976", "D", "Y", "DAPT", "U", "001/NB OFF TO X"),
        _tsmis_row("001", "12-ORA-001", "R", "001.000", "02/25/1976", "",  "Y", "DAPT", "U", "001/SB ON FR Y"),   # HG blank vs TSN 'D' -> COMPARED diff
        _tsmis_row("001", "12-ORA-001", "R", "002.000", "01/01/2000", "D", "N", "LGNB", "U", "001/RAMP Z"),       # Ramp Type context only
        _tsmis_row("002", "12-ORA-002", "M", "010.000", "03/03/1990", "U", "Y", "SANA", "R", "002/ON A"),
    ])
    _write_tsn(b, [
        ["001", "R", "0.606", "1976-02-25", "D", "Y", "DAPT", "U", "NB OFF TO X", "101_1", "F", "D", "70"],
        ["001", "R", "1.000", "1976-02-25", "D", "Y", "DAPT", "U", "SB ON FR Y", "101_2", "O", "F", "80"],   # HG 'D' vs TSMIS blank
        ["001", "R", "1.500", "1965-01-01", "D", "Y", "LGNB", "U", "MID INSERT", "101_x", "O", "H", "90"],   # only in TSN (mid-list)
        ["001", "R", "2.000", "2000-01-01", "D", "N", "LGNB", "U", "RAMP Z", "101_3", "F", "M", "55"],       # Ramp Type 'M' (TSMIS blank) -> context, no diff
        ["002", "M", "10.000", "1990-03-03", "U", "Y", "SANA", "R", "ON A", "201_1", "O", "D", "30"],
    ])
    res = rd.compare(a, b, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")
    header, rows = _comparison(out)

    # Key collapse: the mid-list TSN insert is ONE one-sided ramp, no cascade.
    pm_col = header.index("PM")
    by_pm = {r[pm_col]: r for r in rows}
    check("5 union rows on the canonical postmiles (4 matched + 1 TSN-only insert)",
          set(by_pm) == {"0.606", "1.000", "1.500", "2.000", "10.000"})

    # The COMPARED HG diff at PM 1.000 carries the ≠ marker.
    hg_col = header.index("HG")
    pm1 = by_pm["1.000"]
    check("compared HG difference shows the diff marker", DIFF in pm1[hg_col])

    # The CONTEXT 'Ramp Type' column NEVER carries a diff marker, and SHOWS the TSN value.
    rt_col = header.index("Ramp Type")
    check("context 'Ramp Type' never shows a diff marker in any row",
          all(DIFF not in r[rt_col] for r in rows))
    check("context 'Ramp Type' coalesces to the TSN value (M)", by_pm["2.000"][rt_col] == "M")

    # Total diff cells: count the ≠ across the whole Comparison body, and confirm
    # NONE of them are in the four context columns.
    ctx_cols = [header.index(c) for c in ("Ramp Name", "On/Off", "Ramp Type", "ADT")]
    total = sum(1 for r in rows for c in r if DIFF in c)
    ctx_diffs = sum(1 for r in rows for i in ctx_cols if DIFF in r[i])
    check("zero diff cells fall in the context columns", ctx_diffs == 0)
    check("at least the one compared HG diff is counted", total >= 1)
    print(f"      (union rows={len(rows)}, total diff cells={total}, context diff cells={ctx_diffs})")


def main():
    test_schema()
    test_end_to_end()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-RAMP-DETAIL-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
