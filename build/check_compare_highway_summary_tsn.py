"""build/check_compare_highway_summary_tsn.py — the Highway Summary vs-TSN contract.

Highway Summary is the third AGGREGATE summary comparison (statewide category
totals), and the first that measures MILES rather than counts. This check covers
the parts a synthetic fixture can prove:

  * the shared TSMIS/TSN code taxonomy — every category one system classifies
    resolves to a within-section code, the one-sided set is exactly the censused
    three, and the codes pair the two systems' DIFFERENT spellings;
  * the TSN row reader's special cases (glued DVM prefix, MEDIAN TYPE mapping
    parentheses, RURAL-URBAN parent binding and its parentless refusal, the
    masked `**********` value being ABSENT rather than zero);
  * the TSMIS loader's refusals (wrong sheet, un-recognized layout);
  * `summary_layout`'s opt-in MEASURE rendering, and that it left the two COUNT
    specs untouched.

The statewide print itself is local-only, so its numbers are asserted by
build/check_highway_summary_real.py when the corpus is present; everything here
is hermetic.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_highway_summary_tsn.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import compare_highway_summary_tsn as hstsn
import highway_summary_columns as hsc
import summary_layout

_fail = []


def check(name, cond, detail=""):
    suffix = f"  -> {detail}" if (not cond and detail) else ""
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}{suffix}")
    if not cond:
        _fail.append(name)


def test_taxonomy():
    print("the shared TSMIS/TSN code taxonomy:")
    check("95 TSMIS categories, 92 the TSN print classifies",
          len(hsc.cats_for("tsmis")) == 95 and len(hsc.cats_for("tsn")) == 92,
          f"{len(hsc.cats_for('tsmis'))}/{len(hsc.cats_for('tsn'))}")
    one_sided = {(c.section, c.label) for c in hsc.CATS if c.sides == "tsmis"}
    check("the one-sided set is exactly the censused three",
          one_sided == {("MEDIAN TYPE", "(UNDIVIDED)"), ("MEDIAN TYPE", "(DIVIDED)"),
                        ("DESIGN SPEED", "- NO DATA")}, f"{sorted(one_sided)}")
    check("no TSN-only category is claimed (the print's ADT section is not in the "
          "taxonomy at all)", not any(c.sides == "tsn" for c in hsc.CATS))
    idx = hsc.code_index("tsn")
    check("every TSN-classified category is reachable by (section, code)",
          len(idx) == len(hsc.cats_for("tsn")), f"{len(idx)}")
    print("  the code pairs the two systems' different spellings:")
    for section, tsmis_label, tsn_label in (
            ("HIGHWAY GROUP", "R- RIGHT  IND ALIGN", "R-RIGHT IND ALIGN"),
            ("MEDIAN TYPE", "A- NOT SEPARATED OR STRIPED", "A-NOT SEPARATED OR STRIPED"),
            ("MEDIAN BARRIER", "+- NO DATA GIVEN", "+-NO DATA GIVEN"),
            ("MEDIAN WIDTH", "0  -  4", "0 - 4"),
            ("DESIGN SPEED", "70  -  100", "70 - 100"),
            ("NUMBER OF LANES", "12  -  UP", "12 - UP")):
        tsmis_cat = next((c for c in hsc.CATS
                          if c.section == section and hsc.norm_label(c.label)
                          == hsc.norm_label(tsmis_label)), None)
        tsn_code, _ = hstsn._tsn_code(section, tsn_label, None, "probe")
        check(f"    {section}: {tsmis_label!r} pairs {tsn_label!r}",
              tsmis_cat is not None and tsmis_cat.code == tsn_code,
              f"tsmis={getattr(tsmis_cat, 'code', None)!r} tsn={tsn_code!r}")


def test_rural_urban_parent():
    print("RURAL-URBAN parent binding (the CMP-AUD-023 rule):")
    code, parent = hstsn._tsn_code("RURAL-URBAN", "R-RURAL - I - INSIDE CITY", None, "p")
    check("an R-RURAL row sets the parent and codes R", (code, parent) == ("R", "R"),
          f"{(code, parent)}")
    code, parent = hstsn._tsn_code("RURAL-URBAN", "- O - OUTSIDE CITY", parent, "p")
    check("its following '- O -' row binds to R", code == "R-O", f"{code}")
    code, parent = hstsn._tsn_code("RURAL-URBAN", "U-URBAN - I - INSIDE CITY", parent, "p")
    check("a U-URBAN row switches the parent", (code, parent) == ("U", "U"), f"{(code, parent)}")
    code, _ = hstsn._tsn_code("RURAL-URBAN", "- O - OUTSIDE CITY", parent, "p")
    check("the next '- O -' binds to U (not the stale R)", code == "U-O", f"{code}")
    code, _ = hstsn._tsn_code("RURAL-URBAN", "--INVALID DATA", parent, "p")
    check("'--INVALID DATA' is its own code, not an '-O'", code == "INVALID", f"{code}")
    try:
        hstsn._tsn_code("RURAL-URBAN", "- O - OUTSIDE CITY", None, "probe.pdf")
        check("a PARENTLESS '- O -' row is refused", False, "it was accepted")
    except ValueError as e:
        check("a PARENTLESS '- O -' row is refused",
              "cannot be attributed" in str(e), str(e))


def test_label_cleanup():
    print("the TSN row label cleanups:")
    check("the glued DVM prefix is stripped",
          hstsn._LEAD_DVM_RE.sub("", "6,311,760.663R-RIGHT IND ALIGN") == "R-RIGHT IND ALIGN")
    check("a DVM glued to a RANGE is stripped too",
          hstsn._LEAD_DVM_RE.sub("", "111,826,634.85960 - 99").strip() == "60 - 99")
    check("the MEDIAN TYPE mapping parenthetical is stripped",
          hstsn._PAREN_RE.sub("", "B-STRIPED (S )").strip() == "B-STRIPED")
    check("a masked value is recognized", bool(hstsn._MASK_RE.match("**********")))
    check("a real value is not masked", not hstsn._MASK_RE.match("8,586.950"))
    check("a comma'd mileage parses exactly",
          hsc.parse_miles("8,586.950", source="p", category="c") == 8586950)


def test_absent_is_not_zero():
    print("an absent source fact is never a zero:")
    rows = hstsn._rows({hsc.TOTAL_SLUG: 1000})
    keys = [r[0] for r in rows]
    check("a slug with no value is OMITTED from the compared rows",
          keys == [hsc.TOTAL_KEY], f"{keys[:4]}")
    some = next(c for c in hsc.cats_for("tsn") if c.section == "MEDIAN BARRIER")
    rows = hstsn._rows({hsc.TOTAL_SLUG: 1000, some.slug: 0})
    check("an explicit 0 IS carried (a real source zero differs from absent)",
          [r[0] for r in rows] == [some.key, hsc.TOTAL_KEY]
          or [r[0] for r in rows] == [hsc.TOTAL_KEY, some.key],
          f"{[r[0] for r in rows]}")


def test_tsmis_loader_refusals():
    print("the TSMIS loader refuses what it cannot trust:")
    import openpyxl
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="tsmis_hstsn_"))
    wrong = d / "wrong_sheet.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Not Highway Summary"
    wb.save(wrong)
    wb.close()
    try:
        hstsn._load_tsmis(str(wrong))
        check("a workbook without the per-route sheet is refused", False, "accepted")
    except ValueError as e:
        check("a workbook without the per-route sheet is refused",
              "CONSOLIDATED" in str(e) or "sheet" in str(e), str(e)[:90])

    bad_hdr = d / "bad_header.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = hsc.SHEET_NAME
    ws.append(["Route", "Total Miles", "something else"])
    ws.append(["001", 1.0, 2.0])
    wb.save(bad_hdr)
    wb.close()
    try:
        hstsn._load_tsmis(str(bad_hdr))
        check("an un-recognized layout is refused", False, "accepted")
    except ValueError as e:
        check("an un-recognized layout is refused", "layout" in str(e), str(e)[:90])


def test_measure_rendering():
    print("summary_layout's opt-in MEASURE mode:")
    spec = hsc.summary_spec()
    check("the Highway Summary spec carries a measure reader + format",
          spec.value_reader is not None and spec.value_format == "#,##0.000")
    check("its lead noun is Miles, not Counts", spec.measure_noun == "Miles")
    check("a fractional value reads through (the integer reader returns None)",
          spec.value_reader(200.418) == 200.418 and summary_layout._as_int(200.418) is None)
    check("a non-number stays None (absent must not become 0)",
          spec.value_reader("n/a") is None and spec.value_reader(None) is None)
    print("  ...and the two COUNT specs are untouched:")
    for other in (summary_layout.RAMP_SUMMARY_SPEC,
                  summary_layout.INTERSECTION_SUMMARY_SPEC):
        check(f"    {other.report}: no measure reader/format, noun 'Counts'",
              other.value_reader is None and other.value_format is None
              and other.measure_noun == "Counts")
    check("the spec's compared categories == the comparator's",
          spec.categories() == hstsn._CATEGORIES)


def main():
    print("=== Highway Summary vs TSN ===")
    test_taxonomy()
    test_rural_urban_parent()
    test_label_cleanup()
    test_absent_is_not_zero()
    test_tsmis_loader_refusals()
    test_measure_rendering()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL HIGHWAY SUMMARY vs-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
