"""Golden check for the TSMIS-vs-TSN Intersection Summary comparator
(scripts/compare_intersection_summary_tsn.py) — the AGGREGATE recipe applied to
the intersection taxonomy, with ONE-SIDED diverged codes.

Locks: the canonical spec (72 categories; unique keys/slugs; the diverged
CONTROL/INTERSECTION-TYPE codes flagged one-sided — TSN-only J-P, TSMIS-only
S/O/Q/R + R/C/P), the spec-driven block-walk mapper (incl. the Rural/Urban
'-O OUTSIDE CITY' parent disambiguation), the consolidated-workbook summing
loader, and end-to-end that a TSN-only code lands in 'Only in TSN', a TSMIS-only
code in 'Only in TSMIS', and the familiar sheet renders. No Excel; CI-safe.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_intersection_summary_tsn.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_intersection_summary_tsn as cmp
import summary_layout as sl
from events import Events
from openpyxl import Workbook, load_workbook

_fail = []
SPEC = sl.INTERSECTION_SUMMARY_SPEC
_KEY = {slug: key for key, slug in cmp._CATEGORIES}


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_spec():
    print("spec + one-sided marking:")
    sc = cmp._SCHEMA
    check("header Category/Count, key_field 0", sc.header == ["Category", "Count"] and sc.key_field == 0)
    check("extra_sheet_writer set", sc.extra_sheet_writer is not None)
    keys = [k for k, _ in cmp._CATEGORIES]
    slugs = [s for _, s in cmp._CATEGORIES]
    check("72 categories, unique keys + slugs",
          len(cmp._CATEGORIES) == 72 and len(set(keys)) == 72 and len(set(slugs)) == 72)
    by_slug = {c.slug: c for sec in SPEC.sections for c in sec.cats}
    check("CONTROL J-P are TSN-only",
          all(by_slug[f"is_control_types_{c.lower()}"].sides == "tsn" for c in "JKLMNP"))
    check("CONTROL S/O/Q/R are TSMIS-only",
          all(by_slug[f"is_control_types_{c.lower()}"].sides == "tsmis" for c in "SOQR"))
    check("INTERSECTION TYPE Roundabout (R) is TSMIS-only",
          by_slug["is_intersection_type_r"].sides == "tsmis")
    tsmis_cats = SPEC.categories_for("tsmis")
    tsn_cats = SPEC.categories_for("tsn")
    check("categories_for(tsmis) excludes TSN-only J", _KEY["is_control_types_j"] not in dict(tsmis_cats).keys())
    check("categories_for(tsn) excludes TSMIS-only S", _KEY["is_control_types_s"] not in dict(tsn_cats).keys())


def test_block_walk():
    print("spec-driven block-walk mapper (counts_from_rows):")
    rows = [
        (None, "HIGHWAY GROUP"), (None, "NUMBER CODE"),
        (5, "U-UNDIVIDED"), (3, "D-DIVIDED"),
        (None, "<---RURAL/URBAN/SUBURBAN--->"), (None, "NUMBER CODE"),
        (1, "R-RURAL -I INSIDE CITY"), (9, "-O OUTSIDE CITY"),
        (2, "U-URBAN -I INSIDE CITY"), (4, "-O OUTSIDE CITY"),
        (None, "CONTROL TYPES"), (7, "A-NO CONTROL"), (6, "S-SIGNALIZED"),
        (None, "MAINLINE NUM OF LANES"), (8, "2"), (1, "+-NO DATA GIVEN"),
    ]
    c = sl.counts_from_rows(SPEC, rows)
    check("HG undivided=5, divided=3", c["is_highway_group_u"] == 5 and c["is_highway_group_d"] == 3)
    check("rural '-O' bound to R-RURAL parent (R-O=9)", c["is_rural_urban_suburban_r_o"] == 9)
    check("urban '-O' bound to U-URBAN parent (U-O=4)", c["is_rural_urban_suburban_u_o"] == 4)
    check("control A=7, S=6", c["is_control_types_a"] == 7 and c["is_control_types_s"] == 6)
    check("lanes '2'=8 and '+'=1", c["is_mainline_num_of_lanes_2"] == 8 and c["is_mainline_num_of_lanes_plus"] == 1)


def _write_tsmis(path, cols, route_rows):
    wb = Workbook()
    ws = wb.active
    ws.title = cmp.TSMIS_SHEET
    ws.append(["Route", "Total Intersections"] + cols)
    for r in route_rows:
        ws.append(r)
    wb.save(path)
    wb.close()


def _write_tsn(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = cmp.NORMALIZED_SHEET
    ws.append(["Category", "Count"])
    for k, v in rows:
        ws.append([k, v])
    wb.save(path)
    wb.close()


def _sheet(path, name):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[name]
        it = ws.iter_rows(values_only=True)
        header = [("" if c is None else str(c)) for c in next(it)]
        rows = [["" if c is None else str(c) for c in r] for r in it
                if r and any(c not in (None, "") for c in r)]
        return header, rows
    finally:
        wb.close()


def test_end_to_end():
    print("end-to-end (one-sided diverged codes):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_is_tsn_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    cols = [_KEY["is_highway_group_u"], _KEY["is_control_types_a"],
            _KEY["is_control_types_s"], _KEY["is_control_types_j"]]
    _write_tsmis(tsmis, cols, [["001", 10, 8, 3, 5, 0]])   # TSMIS: U=8,A=3,S=5,J=0
    _write_tsn(tsn, [
        (_KEY["is_highway_group_u"], 8),       # match
        (_KEY["is_control_types_a"], 4),       # diff (3 vs 4)
        (_KEY["is_control_types_j"], 7),       # TSN-only
        (SPEC.total.key, 12),                  # total diff (10 vs 12)
    ])
    res = cmp.compare(tsmis, tsn, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")

    header, rows = _sheet(out, "Comparison")
    si = header.index("Status")
    both = sum(1 for r in rows if r[si] == "Both")
    tonly = sum(1 for r in rows if r[si] == "TSMIS only")
    nonly = sum(1 for r in rows if r[si] == "TSN only")
    check("structural split: 56 both / 10 only-TSMIS / 6 only-TSN",
          both == 56 and tonly == 10 and nonly == 6)

    oa = {r[0] for r in _sheet(out, "Only in TSMIS")[1]}
    ob = {r[0] for r in _sheet(out, "Only in TSN")[1]}
    check("TSN-only J - SIGNAL PRETIMED is in 'Only in TSN'", _KEY["is_control_types_j"] in ob)
    check("TSMIS-only S - SIGNALIZED is in 'Only in TSMIS'", _KEY["is_control_types_s"] in oa)

    cat_col, cnt_col = header.index("Category"), header.index("Count")
    by = {r[cat_col]: r for r in rows}
    DIFF = " ≠ "
    check("matched HG Undivided (8) has no diff", DIFF not in by[_KEY["is_highway_group_u"]][cnt_col])
    check("control A differs (3 vs 4)", DIFF in by[_KEY["is_control_types_a"]][cnt_col])
    check("Total Intersections differs (10 vs 12)", DIFF in by[SPEC.total.key][cnt_col])

    fh, fr = _sheet(out, SPEC.sheet_name)
    flat = [c for row in [fh] + fr for c in row]
    check("familiar sheet labels TSMIS/TSN", "TSMIS" in flat and "TSN" in flat)
    check("familiar sheet lists a diverged code (S - SIGNALIZED)",
          any("S - SIGNALIZED" in c for c in flat))
    print(f"      (both={both}, only-TSMIS={tonly}, only-TSN={nonly})")


def main():
    test_spec()
    test_block_walk()
    test_end_to_end()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-INTERSECTION-SUMMARY-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
