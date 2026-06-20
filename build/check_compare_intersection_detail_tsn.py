"""Golden check for the TSMIS-vs-TSN Intersection Detail comparator
(scripts/compare_intersection_detail_tsn.py) — the FLAT recipe (route+PM).

Locks: the CompareSchema wiring (PM key; the context_fields = PR + Date of Record
+ the five cross-street attributes; boolean fields; the Notes legend_writer), the
Y/N<->1/0 boolean normalization, route-from-LOCATION + PM/date normalization, the
position-based TSMIS-consolidated loader, and end-to-end that a Y/1 boolean
compares EQUAL while a control-type code change is a genuine diff, and that the
context columns (cross-street + Date of Record) contribute ZERO diff cells even
when one side is blank. No Excel; CI-safe.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_intersection_detail_tsn.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_intersection_detail_tsn as idt
from events import Events
from openpyxl import Workbook, load_workbook

_fail = []
DIFF = " ≠ "


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _write_tsmis(path, rows):
    """Synthetic CONSOLIDATED Intersection Detail: header[0]='Route'; the loader
    reads by POSITION, so only the column positions matter (labels are placeholders)."""
    wb = Workbook()
    ws = wb.active
    ws.title = idt.TSMIS_SHEET
    ws.append(["Route"] + [f"c{i}" for i in range(1, 37)])
    for r in rows:
        ws.append(r + [None] * (37 - len(r)))
    wb.save(path)
    wb.close()


def _tsmis_row(route, pr, pm, dor, hg, city, ru, int_t, ctrl_t, light, ml_sm, ml_lc,
               ml_rc, ml_tf, ml_nl, desc, cs_sm=None, cs_lc=None):
    """Place values at the consolidated VALUE positions the loader reads."""
    r = [None] * 37
    r[0], r[1], r[2], r[4], r[5] = route, pr, pm, "12 ORA " + route, dor
    r[6], r[7], r[8] = hg, city, ru
    r[10], r[12], r[14] = int_t, ctrl_t, light
    r[16], r[17], r[18], r[19], r[20] = ml_sm, ml_lc, ml_rc, ml_tf, ml_nl
    r[22] = desc
    r[25], r[26] = cs_sm, cs_lc            # cross-street (context)
    return r


def _write_tsn(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = idt.TSN_SHEET
    cols = ["PP", "POST_MILE", "LOCATION", "DATE_REC", "HG", "CITY_CODE", "RU",
            "TY_INT", "TY_CT", "LT_TY", "MAIN_SM", "MAIN_LC", "MAIN_RC", "MAIN_TF",
            "MAIN_NL", "DESCRIPTION", "CS_SM", "CS_LC", "CS_RC", "CS_TF", "CS_NL"]
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c) for c in cols])
    wb.save(path)
    wb.close()


def _comparison(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["Comparison"]
        it = ws.iter_rows(values_only=True)
        header = [("" if c is None else str(c)) for c in next(it)]
        rows = [["" if c is None else str(c) for c in r] for r in it
                if r and any(c not in (None, "") for c in r)]
        return header, rows, wb.sheetnames
    finally:
        wb.close()


def test_schema():
    print("schema + normalizers:")
    sc = idt._SCHEMA
    check("key is PM", sc.header[sc.key_field] == "PM")
    check("side names TSMIS / TSN", sc.side_a == "TSMIS" and sc.side_b == "TSN")
    check("context = PR + Date of Record + 5 cross-street attrs",
          set(sc.context_fields) == {"PR", "Date of Record", "CS Mastarm",
                                     "CS Left Chan", "CS Right Chan", "CS Traffic Flow",
                                     "CS Num Lanes"})
    check("Notes legend_writer set (the indicator)", sc.legend_writer is not None)
    check("boolean normalize Y/1->Y, N/0->N",
          idt._norm_bool("Y") == "Y" and idt._norm_bool("1") == "Y"
          and idt._norm_bool("N") == "N" and idt._norm_bool("0") == "N")
    check("route from LOCATION '12 ORA 001' -> '001'", idt._norm_route("12 ORA 001") == "001")
    check("roadbed split '12 ORA 210U' -> ('210','U')", idt._split_route("12 ORA 210U") == ("210", "U"))
    check("roadbed split '12 ORA. 210' -> ('210','')", idt._split_route("12 ORA. 210") == ("210", ""))
    check("Roadbed is a COMPARED column (not context)",
          "Roadbed" in sc.header and "Roadbed" not in sc.context_fields)
    check("PM ' 000.204' -> '0.204'", idt._norm_pm(" 000.204") == "0.204")
    check("date ISO from YY-MM-DD ('73-10-19' -> '1973-10-19')",
          idt._iso_date("73-10-19") == "1973-10-19")


def test_end_to_end():
    print("end-to-end (boolean normalize + context non-asserting):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_id_tsn_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    # PM 0.204: control-type diverges (P vs S); booleans equal across encodings;
    #   CS present on TSN, blank on TSMIS (context). PM 1.000: a real ML Num Lanes diff.
    _write_tsmis(tsmis, [
        _tsmis_row("001", "R", "0.204", "21-12-31", "D", "DAPT", "U", "T", "S", "1",
                   "1", "N", "0", "P", "3", "JCT 5"),
        _tsmis_row("001", "R", "1.000", "21-12-31", "D", "DAPT", "U", "T", "S", "1",
                   "1", "N", "0", "P", "4", "JCT 6"),
    ])
    _write_tsn(tsn, [
        {"PP": "R", "POST_MILE": " 000.204", "LOCATION": "12 ORA 001", "DATE_REC": "73-10-19",
         "HG": "D", "CITY_CODE": "DAPT", "RU": "U", "TY_INT": "T", "TY_CT": "P", "LT_TY": "Y",
         "MAIN_SM": "Y", "MAIN_LC": "N", "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
         "DESCRIPTION": "JCT 5", "CS_SM": "N", "CS_LC": "N", "CS_RC": "N", "CS_TF": "P", "CS_NL": 2},
        {"PP": "R", "POST_MILE": " 001.000", "LOCATION": "12 ORA 001", "DATE_REC": "73-10-19",
         "HG": "D", "CITY_CODE": "DAPT", "RU": "U", "TY_INT": "T", "TY_CT": "S", "LT_TY": "Y",
         "MAIN_SM": "Y", "MAIN_LC": "N", "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
         "DESCRIPTION": "JCT 6"},
    ])
    res = idt.compare(tsmis, tsn, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")
    header, rows, sheets = _comparison(out)
    check("Notes sheet present (the indicator)", "Notes" in sheets)
    pm = header.index("PM")
    by = {r[pm]: r for r in rows}

    light = header.index("Lighting")
    mast = header.index("ML Mastarm")
    rc = header.index("ML Right Chan")
    ctrl = header.index("Control Type")
    nl = header.index("ML Num Lanes")
    check("Lighting Y(TSN)/1(TSMIS) normalized equal — no diff", DIFF not in by["0.204"][light])
    check("ML Mastarm Y/1 normalized equal — no diff", DIFF not in by["0.204"][mast])
    check("ML Right Chan N/0 normalized equal — no diff", DIFF not in by["0.204"][rc])
    check("Control Type P vs S is a genuine diff", DIFF in by["0.204"][ctrl])
    check("ML Num Lanes 3 vs 4 is a genuine diff", DIFF in by["1.000"][nl])

    # context columns NEVER carry a diff marker (incl. CS present-vs-blank, Date of Record).
    ctx_cols = [header.index(c) for c in ("PR", "Date of Record", "CS Mastarm",
                                          "CS Left Chan", "CS Right Chan",
                                          "CS Traffic Flow", "CS Num Lanes")]
    ctx_diffs = sum(1 for r in rows for i in ctx_cols if DIFF in r[i])
    check("zero diff cells in any context column (CS blank-vs-N, Date refresh)", ctx_diffs == 0)
    check("CS Mastarm context shows the TSN value (N) when TSMIS is blank",
          by["0.204"][header.index("CS Mastarm")] == "N")
    total = sum(1 for r in rows for c in r if DIFF in c)
    print(f"      (rows={len(rows)}, total diff cells={total}, context diff cells={ctx_diffs})")


def test_roadbed_match():
    """A TSN route carrying a roadbed suffix (210U) must MATCH the suffix-less
    TSMIS route (210) on base route + PM — not drop to one-sided — and the suffix
    difference must be FLAGGED in the 'Roadbed' column (the indicator)."""
    print("roadbed-suffix matching + indicator:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_id_rb_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    # TSMIS lists the route WITHOUT a suffix ("210"); everything else identical.
    _write_tsmis(tsmis, [
        _tsmis_row("210", "R", "5.000", "21-12-31", "D", "DAPT", "U", "T", "S", "1",
                   "1", "N", "0", "P", "3", "JCT 99"),
    ])
    # TSN lists the SAME intersection under "210U" (divided-highway roadbed).
    _write_tsn(tsn, [
        {"PP": "R", "POST_MILE": " 005.000", "LOCATION": "12 ORA 210U", "DATE_REC": "73-10-19",
         "HG": "D", "CITY_CODE": "DAPT", "RU": "U", "TY_INT": "T", "TY_CT": "S", "LT_TY": "Y",
         "MAIN_SM": "Y", "MAIN_LC": "N", "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
         "DESCRIPTION": "JCT 99"},
    ])
    res = idt.compare(tsmis, tsn, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")
    header, rows, sheets = _comparison(out)
    check("matched (1 row on the Comparison sheet, not one-sided)", len(rows) == 1)
    rb = header.index("Roadbed")
    check("Roadbed flags the suffix-only difference (U vs blank)", DIFF in rows[0][rb])
    # the substantive attributes are identical, so NOTHING else differs.
    other = sum(1 for i, c in enumerate(rows[0]) if i != rb and DIFF in c)
    check("no other column differs (suffix is the only difference)", other == 0)


def main():
    test_schema()
    test_end_to_end()
    test_roadbed_match()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-INTERSECTION-DETAIL-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
