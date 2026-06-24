"""Golden check for the TSMIS-vs-TSN Intersection Summary comparator
(scripts/compare_intersection_summary_tsn.py) — the AGGREGATE recipe applied to
the intersection taxonomy.

Locks: the canonical spec (66 categories after the signal fold; unique keys/slugs),
the CONTROL-TYPE signal crosswalk (TSN sub-types J–P fold into the shared 'S -
SIGNALIZED' category, matching the Detail — so Signalized compares on BOTH sides and
there are NO TSN-only codes left), the remaining genuinely one-sided TSMIS-only codes
(Roundabout R / PHB O / Flash Q / intersection R/C/P / left-chan Y — absent from the
TSN summary PDF), the '+ no data' buckets the TSN PDF reports as 0 being compared
(num-of-lanes '+' is now BOTH), the spec-driven block-walk mapper (incl. the J–P→S
fold and the Rural/Urban '-O OUTSIDE CITY' parent disambiguation), the
consolidated-workbook summing loader, and end-to-end structure. No Excel; CI-safe.

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
    print("spec + signal fold + one-sided marking:")
    sc = cmp._SCHEMA
    check("header Category/Count, key_field 0", sc.header == ["Category", "Count"] and sc.key_field == 0)
    check("extra_sheet_writer set", sc.extra_sheet_writer is not None)
    keys = [k for k, _ in cmp._CATEGORIES]
    slugs = [s for _, s in cmp._CATEGORIES]
    check("66 categories (J-P folded into Signalized), unique keys + slugs",
          len(cmp._CATEGORIES) == 66 and len(set(keys)) == 66 and len(set(slugs)) == 66)
    by_slug = {c.slug: c for sec in SPEC.sections for c in sec.cats}
    check("CONTROL signal sub-types J-P are NOT separate categories (folded -> S)",
          not any(f"is_control_types_{c.lower()}" in by_slug for c in "JKLMNP"))
    check("CONTROL S - Signalized is now BOTH (compared, not one-sided)",
          by_slug["is_control_types_s"].sides == "both")
    check("CONTROL O/Q/R stay TSMIS-only (absent from the TSN summary)",
          all(by_slug[f"is_control_types_{c.lower()}"].sides == "tsmis" for c in "OQR"))
    check("INTERSECTION TYPE Roundabout (R) is TSMIS-only",
          by_slug["is_intersection_type_r"].sides == "tsmis")
    check("MAINLINE NUM OF LANES '+' is now BOTH (TSN reports it as 0)",
          by_slug["is_mainline_num_of_lanes_plus"].sides == "both")
    check("no TSN-only categories remain (signals folded)", len(sl._IS_TSN_ONLY) == 0)
    tsn_cats = dict(SPEC.categories_for("tsn"))
    check("categories_for(tsn) now INCLUDES Signalized (S)", _KEY["is_control_types_s"] in tsn_cats)


def test_block_walk():
    print("spec-driven block-walk mapper (counts_from_rows):")
    rows = [
        (None, "HIGHWAY GROUP"), (None, "NUMBER CODE"),
        (5, "U-UNDIVIDED"), (3, "D-DIVIDED"),
        (None, "<---RURAL/URBAN/SUBURBAN--->"), (None, "NUMBER CODE"),
        (1, "R-RURAL -I INSIDE CITY"), (9, "-O OUTSIDE CITY"),
        (2, "U-URBAN -I INSIDE CITY"), (4, "-O OUTSIDE CITY"),
        (None, "CONTROL TYPES"), (7, "A-NO CONTROL"), (6, "S-SIGNALIZED"),
        (2, "J-SIGNAL PRETIMED (2-PHASE)"), (3, "P-SIGNALS FULL-ACTUATED (MULTI-PHASE)"),
        (None, "MAINLINE NUM OF LANES"), (8, "2"), (1, "+-NO DATA GIVEN"),
    ]
    c = sl.counts_from_rows(SPEC, rows)
    check("HG undivided=5, divided=3", c["is_highway_group_u"] == 5 and c["is_highway_group_d"] == 3)
    check("rural '-O' bound to R-RURAL parent (R-O=9)", c["is_rural_urban_suburban_r_o"] == 9)
    check("urban '-O' bound to U-URBAN parent (U-O=4)", c["is_rural_urban_suburban_u_o"] == 4)
    # CROSSWALK: J–P fold into S — Signalized accumulates 6 (S) + 2 (J) + 3 (P) = 11.
    check("control A=7; signals fold into S (S 6 + J 2 + P 3 = 11)",
          c["is_control_types_a"] == 7 and c["is_control_types_s"] == 11)
    check("folded sub-types leave no separate J/P slug",
          "is_control_types_j" not in c and "is_control_types_p" not in c)
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
    print("end-to-end (signal fold; Signalized compared; only TSMIS-only codes one-sided):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_is_tsn_"))
    tsmis, tsn, out = root / "t.xlsx", root / "n.xlsx", root / "c.xlsx"
    cols = [_KEY["is_highway_group_u"], _KEY["is_control_types_a"],
            _KEY["is_control_types_s"], _KEY["is_control_types_r"]]
    _write_tsmis(tsmis, cols, [["001", 10, 8, 3, 5, 2]])   # TSMIS: U=8,A=3,S=5,R=2
    _write_tsn(tsn, [
        (_KEY["is_highway_group_u"], 8),       # match
        (_KEY["is_control_types_a"], 4),       # diff (3 vs 4)
        (_KEY["is_control_types_s"], 7),       # diff (5 vs 7) — S is now BOTH, compared
        (SPEC.total.key, 12),                  # total diff (10 vs 12)
    ])                                         # R has no TSN row -> Only in TSMIS
    res = cmp.compare(tsmis, tsn, out, events=Events(), confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")

    header, rows = _sheet(out, "Comparison")
    si = header.index("Status")
    both = sum(1 for r in rows if r[si] == "Both")
    tonly = sum(1 for r in rows if r[si] == "TSMIS only")
    nonly = sum(1 for r in rows if r[si] == "TSN only")
    check("structural split: 58 both / 8 only-TSMIS / 0 only-TSN (signals folded)",
          both == 58 and tonly == 8 and nonly == 0)

    oa = {r[0] for r in _sheet(out, "Only in TSMIS")[1]}
    check("no TSN-only categories (signals fold into shared Signalized)", nonly == 0)
    check("TSMIS-only Roundabout (R) is in 'Only in TSMIS'", _KEY["is_control_types_r"] in oa)

    cat_col, cnt_col = header.index("Category"), header.index("Count")
    by = {r[cat_col]: r for r in rows}
    DIFF = " ≠ "
    check("matched HG Undivided (8) has no diff", DIFF not in by[_KEY["is_highway_group_u"]][cnt_col])
    check("Signalized (S) is COMPARED on both and differs (5 vs 7)",
          DIFF in by[_KEY["is_control_types_s"]][cnt_col])
    check("control A differs (3 vs 4)", DIFF in by[_KEY["is_control_types_a"]][cnt_col])
    check("Total Intersections differs (10 vs 12)", DIFF in by[SPEC.total.key][cnt_col])

    fh, fr = _sheet(out, SPEC.sheet_name)
    flat = [c for row in [fh] + fr for c in row]
    check("familiar sheet labels TSMIS/TSN", "TSMIS" in flat and "TSN" in flat)
    check("familiar sheet shows the folded Signalized category (incl. TSN J-P)",
          any("SIGNALIZED" in c for c in flat) and any("J-P" in c or "J–P" in c for c in flat))
    print(f"      (both={both}, only-TSMIS={tonly}, only-TSN={nonly})")


def test_stale_library_fold():
    """A normalized library built BEFORE the signal fold (separate J–P category rows
    + the old 'S - SIGNALIZED' key) is REUSED, not rebuilt, after the code change
    (tsn_library.build_consolidated reuses when current). _load_tsn must fold those
    stale keys into Signalized on read, so a reused pre-fold library still compares
    correctly. Regression lock paired with the Detail's normalized-path repair."""
    print("stale-library signal fold (reused pre-fold normalized workbook):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_is_stale_"))
    stale = root / "stale.xlsx"
    _write_tsn(stale, [
        ("CONTROL TYPES: A - NO CONTROL", 1760),
        ("CONTROL TYPES: J - SIGNAL PRETIMED (2-PHASE)", 207),
        ("CONTROL TYPES: P - SIGNALS FULL-ACTUATED (MULTI-PHASE)", 2023),
        ("CONTROL TYPES: S - SIGNALIZED", 5),        # the OLD label/key
    ])
    rec = cmp._load_tsn(stale)
    check("stale J(207)+P(2023)+old-S(5) fold into Signalized (2235)",
          rec.get(cmp._SIGNALIZED_SLUG) == 207 + 2023 + 5)
    check("non-signal A unchanged (1760)", rec.get("is_control_types_a") == 1760)


def main():
    test_spec()
    test_block_walk()
    test_end_to_end()
    test_stale_library_fold()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-INTERSECTION-SUMMARY-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
