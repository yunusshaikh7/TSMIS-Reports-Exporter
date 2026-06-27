"""Golden check for the TSMIS-vs-TSN Intersection Detail comparator
(scripts/compare_intersection_detail_tsn.py) — the FLAT recipe (route+PM).

Locks: the CompareSchema wiring (PM key; NO context fields — every shared column is
compared and counted; boolean fields; the Notes legend_writer), the Y/N<->1/0
boolean normalization, the control-type crosswalk, route-from-LOCATION + PM/date
normalization, the position-based TSMIS-consolidated loader, and end-to-end that a
normalization still produces a MATCH (a Y/1 boolean and a crosswalked S/P compare
EQUAL) while everything present in both systems IS counted — a non-signalized
control change, the cross-street blank-vs-value gap, and the Date-of-Record
refresh-vs-record column all flag as genuine diffs. No Excel; CI-safe.

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
            "MAIN_NL", "DESCRIPTION", "CS_SM", "CS_LC", "CS_RC", "CS_TF", "CS_NL",
            # added columns the comparison now reads
            "EFF_DATE_INT", "EFF_DATE_CT", "EFF_DATE_LT", "EFF_DATE_ML", "MAIN_EFF_DATE",
            "MAIN_OVERRIDE", "CROSS_BEGIN_DATE", "EFF_DATE", "CROSS_ROUTE_NAME",
            "CROSS_PM_PREFIX", "CROSS_POSTMILE", "CROSS_PM_SUFFIX"]
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
    check("position-aligned: NO context fields (nothing suppressed or greyed)",
          tuple(sc.context_fields) == ())
    check("all 8 date cols + Main Line Length + intersecting route ARE compared "
          "(incl. the former context columns ML 2nd / Int St Eff-Date)",
          all(f in sc.header and f not in sc.context_fields for f in (
              "Date of Record", "INT Type Eff-Date", "Control Type Eff-Date",
              "Lighting Eff-Date", "ML Eff-Date", "ML 2nd Eff-Date", "CS Eff-Date",
              "Int St Eff-Date", "Main Line Length", "Intrte Route",
              "Intrte PM Prefix", "Intrte Postmile", "Intrte PM Suffix")))
    check("position-aligned eff-dates: ML/CS Eff-Date -> geometry EFF_DATE_ML/CROSS_BEGIN_DATE; "
          "ML 2nd/Int St Eff-Date -> recent MAIN_EFF_DATE/EFF_DATE",
          idt._TSN_COL["ML Eff-Date"] == "EFF_DATE_ML"
          and idt._TSN_COL["CS Eff-Date"] == "CROSS_BEGIN_DATE"
          and idt._TSN_COL["ML 2nd Eff-Date"] == "MAIN_EFF_DATE"
          and idt._TSN_COL["Int St Eff-Date"] == "EFF_DATE")
    check("intersecting-route PM suffix reads from pos 35 (not the blank pos 31)",
          idt._TSMIS_POS["Intrte PM Suffix"] == 35)
    check("Notes legend_writer set (documents the normalizations)", sc.legend_writer is not None)
    check("Report View extra_sheet_writer set (the printed two-line replica)",
          sc.extra_sheet_writer is None)   # base schema is clean; the closure is added per-call in compare()
    check("boolean normalize Y/1->Y, N/0->N",
          idt._norm_bool("Y") == "Y" and idt._norm_bool("1") == "Y"
          and idt._norm_bool("N") == "N" and idt._norm_bool("0") == "N")
    check("control-type crosswalk: TSN J-P + TSMIS S -> 'S' (signalized); others unchanged",
          all(idt._norm_control_type(c) == "S" for c in "JKLMNPS")
          and idt._norm_control_type("A") == "A" and idt._norm_control_type("B") == "B")
    # Report View (v0.17.8): every date difference renders RED like a genuine conflict but is
    # kept OUT of the per-record Major count; the lighter alternating band is WHITE (user, 2026-06-24).
    check("Report View: date 'soft' diffs share the hard RED palette (all dates red)",
          idt._RV_FILLS["soft"] == idt._RV_FILLS["hard"])
    check("Report View: the normal (lighter) alternating band is WHITE",
          idt._RV_FILLS["eq"][0] == "FFFFFF" and idt._RV_FILLS["id"][0] == "FFFFFF")
    check("Report View: a date diff classifies 'soft' (red, excluded from Major)",
          idt._rv_classify("Date of Record", "2021-12-31", "1973-10-19") == "soft")
    check("Report View: a non-date attribute diff classifies 'hard' (counts as Major)",
          idt._rv_classify("Control Type", "S", "A") == "hard")
    check("route from LOCATION '12 ORA 001' -> '001'", idt._norm_route("12 ORA 001") == "001")
    check("route-suffix split '12 ORA 210U' -> ('210','U')", idt._split_route("12 ORA 210U") == ("210", "U"))
    check("route-suffix split '12 ORA. 210' -> ('210','')", idt._split_route("12 ORA. 210") == ("210", ""))
    check("Route Suffix is a COMPARED column (not context)",
          "Route Suffix" in sc.header and "Route Suffix" not in sc.context_fields)
    check("PM ' 000.204' -> '0.204'", idt._norm_pm(" 000.204") == "0.204")
    check("date ISO from YY-MM-DD ('73-10-19' -> '1973-10-19')",
          idt._iso_date("73-10-19") == "1973-10-19")


def test_end_to_end():
    print("end-to-end (normalizations still match; every shared column counted):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_id_tsn_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    # PM 0.204: signalized sub-type split (TSMIS S vs TSN P) — CROSSWALKED to equal,
    #   raw codes kept in context; booleans equal across encodings; CS present on TSN,
    #   blank on TSMIS (context). PM 1.000: a NON-signalized control diff (A vs B, NOT
    #   crosswalked) + a real ML Num Lanes diff.
    _write_tsmis(tsmis, [
        _tsmis_row("001", "R", "0.204", "21-12-31", "D", "DAPT", "U", "T", "S", "1",
                   "1", "N", "0", "P", "3", "JCT 5"),
        _tsmis_row("001", "R", "1.000", "21-12-31", "D", "DAPT", "U", "T", "A", "1",
                   "1", "N", "0", "P", "4", "JCT 6"),
    ])
    _write_tsn(tsn, [
        {"PP": "R", "POST_MILE": " 000.204", "LOCATION": "12 ORA 001", "DATE_REC": "73-10-19",
         "HG": "D", "CITY_CODE": "DAPT", "RU": "U", "TY_INT": "T", "TY_CT": "P", "LT_TY": "Y",
         "MAIN_SM": "Y", "MAIN_LC": "N", "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
         "DESCRIPTION": "JCT 5", "CS_SM": "N", "CS_LC": "N", "CS_RC": "N", "CS_TF": "P", "CS_NL": 2},
        {"PP": "R", "POST_MILE": " 001.000", "LOCATION": "12 ORA 001", "DATE_REC": "73-10-19",
         "HG": "D", "CITY_CODE": "DAPT", "RU": "U", "TY_INT": "T", "TY_CT": "B", "LT_TY": "Y",
         "MAIN_SM": "Y", "MAIN_LC": "N", "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
         "DESCRIPTION": "JCT 6"},
    ])
    res = idt.compare(tsmis, tsn, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")
    header, rows, sheets = _comparison(out)
    check("Notes sheet present (the indicator)", "Notes" in sheets)
    check("Report View sheet appended (the printed two-line replica)", "Report View" in sheets)
    pm = header.index("PM")
    by = {r[pm]: r for r in rows}

    light = header.index("Lighting")
    mast = header.index("ML Mastarm")
    rc = header.index("ML Right Chan")
    ctrl = header.index("Control Type")
    nl = header.index("ML Num Lanes")
    dor = header.index("Date of Record")
    cs_sm = header.index("CS Mastarm")
    diffs_col = header.index("Diffs")
    # Normalizations still produce a MATCH (the point of "make normalization clear,
    # even though it leads to a match").
    check("Lighting Y(TSN)/1(TSMIS) normalized equal — no diff", DIFF not in by["0.204"][light])
    check("ML Mastarm Y/1 normalized equal — no diff", DIFF not in by["0.204"][mast])
    check("ML Right Chan N/0 normalized equal — no diff", DIFF not in by["0.204"][rc])
    check("Control Type S(TSMIS)/P(TSN) crosswalk to 'S' — no diff",
          DIFF not in by["0.204"][ctrl] and by["0.204"][ctrl] == "S")
    # Everything present in both systems is now COUNTED (no suppression):
    # the cross-street blank-vs-value gap and the Date-of-Record refresh-vs-record
    # column flag like any other diff.
    check("CS Mastarm blank(TSMIS) vs N(TSN) is now a COUNTED diff (no coalescing)",
          DIFF in by["0.204"][cs_sm])
    check("Date of Record refresh(2021)/record(1973) is now a COUNTED diff",
          DIFF in by["0.204"][dor])
    check("PM 0.204 counts the 5 cross-street + 1 Date-of-Record diffs (6)",
          by["0.204"][diffs_col] in ("6", "6.0"))
    # A NON-signalized control change (A vs B) is NOT crosswalked -> still a genuine diff.
    check("Control Type A(TSMIS) vs B(TSN) — non-signalized, still a genuine diff",
          DIFF in by["1.000"][ctrl])
    check("ML Num Lanes 4 vs 3 is a genuine diff", DIFF in by["1.000"][nl])
    check("PM 1.000 counts Control + ML Num Lanes + Date of Record (3)",
          by["1.000"][diffs_col] in ("3", "3.0"))
    total = sum(1 for r in rows for c in r if DIFF in c)
    check("total counted diff cells across both rows == 9", total == 9)
    print(f"      (rows={len(rows)}, total diff cells={total})")


def test_route_suffix_match():
    """A TSN route carrying a route suffix (210U) must MATCH the suffix-less
    TSMIS route (210) on base route + PM — not drop to one-sided — and the suffix
    difference must be FLAGGED in the 'Route Suffix' column (the indicator)."""
    print("route-suffix matching + indicator:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_id_rb_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    # TSMIS lists the route WITHOUT a suffix ("210"); everything else identical.
    _write_tsmis(tsmis, [
        _tsmis_row("210", "R", "5.000", "21-12-31", "D", "DAPT", "U", "T", "S", "1",
                   "1", "N", "0", "P", "3", "JCT 99"),
    ])
    # TSN lists the SAME intersection under "210U" (route suffix 'U'). Every other
    # column (incl. Date of Record, now compared) is identical, so the suffix is the
    # ONLY difference.
    _write_tsn(tsn, [
        {"PP": "R", "POST_MILE": " 005.000", "LOCATION": "12 ORA 210U", "DATE_REC": "21-12-31",
         "HG": "D", "CITY_CODE": "DAPT", "RU": "U", "TY_INT": "T", "TY_CT": "S", "LT_TY": "Y",
         "MAIN_SM": "Y", "MAIN_LC": "N", "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
         "DESCRIPTION": "JCT 99"},
    ])
    res = idt.compare(tsmis, tsn, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")
    header, rows, sheets = _comparison(out)
    check("matched (1 row on the Comparison sheet, not one-sided)", len(rows) == 1)
    rb = header.index("Route Suffix")
    check("Route Suffix flags the suffix-only difference (U vs blank)", DIFF in rows[0][rb])
    # the substantive attributes are identical, so NOTHING else differs.
    other = sum(1 for i, c in enumerate(rows[0]) if i != rb and DIFF in c)
    check("no other column differs (suffix is the only difference)", other == 0)


def test_normalized_path_crosswalk():
    """A normalized TSN-library workbook carrying RAW control codes (a library built
    before the crosswalk existed — 'stale') must STILL get the crosswalk applied when
    read: _load_tsn re-projects the normalized sheet at compare time. Regression lock
    for the 'Signalized ≠ P' bug (the crosswalk used to be skipped on this path)."""
    print("normalized-library path re-applies the crosswalk (stale-library repair):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_id_norm_"))
    norm = root / "tsn_norm.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = idt.NORMALIZED_SHEET
    ws.append(["Route"] + idt.SHARED_HEADER)

    def nrow(route, pm, ctrl, light="Y"):
        d = {"PM": pm, "Control Type": ctrl, "Lighting": light}
        return [route] + [d.get(f, "") for f in idt.SHARED_HEADER]

    ws.append(nrow("001", "1.000", "P"))     # stale RAW signal sub-type
    ws.append(nrow("001", "2.000", "J"))     # another stale RAW signal sub-type
    ws.append(nrow("001", "3.000", "A"))     # non-signal, must stay "A"
    wb.save(norm)
    wb.close()
    rows, _ = idt._load_tsn(norm)
    pm_i = 1 + idt.SHARED_HEADER.index("PM")
    ct_i = 1 + idt.SHARED_HEADER.index("Control Type")
    by_pm = {r[pm_i]: r[ct_i] for r in rows}
    check("raw 'P' in a normalized library workbook -> 'S' on read",
          by_pm.get("1.000") == "S")
    check("raw 'J' likewise -> 'S'", by_pm.get("2.000") == "S")
    check("non-signal 'A' unchanged", by_pm.get("3.000") == "A")


def test_added_columns():
    """The previously-omitted columns are now compared (v0.17.7): an effective-date
    difference flags, and the intersecting-route block + Main Line Length compare
    (matching where equal). Lock against silently dropping them again."""
    print("added columns (eff-dates, intersecting route, main line length):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_id_add_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    r = _tsmis_row("001", "R", "0.204", "21-12-31", "D", "DAPT", "U", "T", "S", "1",
                   "1", "N", "0", "P", "3", "JCT 5")
    r[9] = "73-10-18"      # INT Type Eff-Date — 1 day before TSN (systematic offset)
    r[23] = "100"          # Main Line Length — matches TSN
    r[32] = "005"          # Intrte Route — matches TSN
    _write_tsmis(tsmis, [r])
    _write_tsn(tsn, [{
        "PP": "R", "POST_MILE": " 000.204", "LOCATION": "12 ORA 001", "DATE_REC": "21-12-31",
        "HG": "D", "CITY_CODE": "DAPT", "RU": "U", "TY_INT": "T", "TY_CT": "S", "LT_TY": "Y",
        "MAIN_SM": "Y", "MAIN_LC": "N", "MAIN_RC": "N", "MAIN_TF": "P", "MAIN_NL": 3,
        "DESCRIPTION": "JCT 5", "EFF_DATE_INT": "73-10-19", "MAIN_OVERRIDE": "100",
        "CROSS_ROUTE_NAME": "005",
    }])
    res = idt.compare(tsmis, tsn, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")
    header, rows, _ = _comparison(out)
    row = {r[header.index("PM")]: r for r in rows}["0.204"]
    check("INT Type Eff-Date is COMPARED and flags (1973-10-18 vs 1973-10-19)",
          DIFF in row[header.index("INT Type Eff-Date")])
    check("Main Line Length is COMPARED and matches (100=100)",
          DIFF not in row[header.index("Main Line Length")])
    check("Intrte Route is COMPARED and matches (005=005)",
          DIFF not in row[header.index("Intrte Route")])


def main():
    test_schema()
    test_end_to_end()
    test_route_suffix_match()
    test_normalized_path_crosswalk()
    test_added_columns()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-INTERSECTION-DETAIL-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
