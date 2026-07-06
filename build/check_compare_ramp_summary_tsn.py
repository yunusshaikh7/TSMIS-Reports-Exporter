"""Golden check for the TSMIS-vs-TSN Ramp Summary comparator
(scripts/compare_ramp_summary_tsn.py) — the v0.17.0 AGGREGATE recipe.

Unlike the FLAT comparators, this one compares ONE statewide category-count table
per side (has_route=False; key = category, value = count). The check locks:
  * the CompareSchema wiring (Category/Count header, key_field 0, TSMIS/TSN sides,
    the extra_sheet_writer that appends the familiar layout);
  * the canonical category list (unique keys; the TSN-only P/V "Dummy" ramp types
    and the grand Total are present);
  * the TSMIS loader SUMMING a consolidated workbook's per-route columns to slugs
    (incl. a category column the workbook lacks -> 0, the old-export case);
  * end-to-end through compare()/the VALUES workbook (read back with openpyxl, no
    Excel, CI-safe): a category present on one side only (P) compares as 0-vs-N, a
    TSMIS-only metric (Ramp Points w/out linework) lands in 'Only in TSMIS' and on
    the familiar sheet, and there is NO Route column (has_route=False).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_compare_ramp_summary_tsn.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import compare_ramp_summary_tsn as cmp
import summary_layout
from events import Events
from openpyxl import Workbook, load_workbook

_fail = []
DIFF = " ≠ "          # the diff marker count_diffs / the workbook key on

# slug -> compare key, for building synthetic TSN rows from canonical categories.
_KEY = {slug: key for key, slug in cmp._CATEGORIES}


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _write_tsmis(path, displays, perroute):
    """A synthetic CONSOLIDATED Ramp Summary workbook: row1 group band (ignored),
    row2 the display headers, then one row per route."""
    wb = Workbook()
    ws = wb.active
    ws.title = cmp.TSMIS_SHEET
    ws.append(["group"] * len(displays))
    ws.append(displays)
    for d in perroute:
        ws.append([d.get(x, "") for x in displays])
    wb.save(path)
    wb.close()


def _write_tsn_norm(path, rows):
    """A synthetic NORMALIZED TSN workbook (Category | Count), keyed on compare keys."""
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


def test_schema_and_categories():
    print("schema + canonical categories:")
    sc = cmp._SCHEMA
    check("header is Category / Count", sc.header == ["Category", "Count"])
    check("key_field is the category (0)", sc.key_field == 0)
    check("side names TSMIS / TSN", sc.side_a == "TSMIS" and sc.side_b == "TSN")
    check("extra_sheet_writer is set (familiar layout)", sc.extra_sheet_writer is not None)
    keys = [k for k, _s in cmp._CATEGORIES]
    check("category keys are unique", len(keys) == len(set(keys)))
    check("31 compared categories", len(cmp._CATEGORIES) == 31)
    slugs = {s for _k, s in cmp._CATEGORIES}
    check("TSN-only P and V ramp types are in the canonical set",
          {"ramp_P_dummy_paired", "ramp_V_dummy_volume"} <= slugs)
    check("grand Total is a compared category", "total_ramps" in slugs)
    check("Ramp Points w/out linework is a footnote (not a compared category)",
          "ramp_points_no_linework" not in slugs
          and any(f.slug == "ramp_points_no_linework" for f in summary_layout.RAMP_SUMMARY_SPEC.footnotes))


def test_tsmis_loader_sums():
    print("TSMIS loader sums per-route columns to slugs:")
    root = Path(tempfile.mkdtemp(prefix="tsmis_rs_sum_"))
    p = root / "consol.xlsx"
    # Two routes; include P (blank) but OMIT V entirely (old-export case -> 0).
    displays = ["Route", "Right", "Divided", "P-DummyPair", "Total Ramps", "Pts w/o Linework"]
    _write_tsmis(p, displays, [
        {"Route": "001", "Right": 4, "Divided": 10, "P-DummyPair": "", "Total Ramps": 14, "Pts w/o Linework": 2},
        {"Route": "002", "Right": 6, "Divided": 10, "P-DummyPair": "", "Total Ramps": 16, "Pts w/o Linework": 1},
    ])
    s = cmp._load_tsmis(p)
    check("hwy_right summed (4+6=10)", s["hwy_right"] == 10)
    check("hwy_divided summed (10+10=20)", s["hwy_divided"] == 20)
    check("blank P column totals 0", s["ramp_P_dummy_paired"] == 0)
    check("missing V column totals 0 (old export)", s["ramp_V_dummy_volume"] == 0)
    check("total_ramps summed (14+16=30)", s["total_ramps"] == 30)
    check("ramp_points summed (2+1=3)", s["ramp_points_no_linework"] == 3)


def test_end_to_end():
    print("end-to-end VALUES workbook (aggregate compare + familiar sheet):")
    root = Path(tempfile.mkdtemp(prefix="tsmis_rs_tsn_"))
    tsmis_path = root / "tsmis.xlsx"
    tsn_path = root / "tsn.xlsx"
    out_path = root / "cmp.xlsx"
    displays = ["Route", "Right", "Divided", "P-DummyPair", "Total Ramps", "Pts w/o Linework"]
    _write_tsmis(tsmis_path, displays, [
        {"Route": "001", "Right": 4, "Divided": 10, "P-DummyPair": "", "Total Ramps": 14, "Pts w/o Linework": 2},
        {"Route": "002", "Right": 6, "Divided": 10, "P-DummyPair": "", "Total Ramps": 16, "Pts w/o Linework": 1},
    ])
    # TSN: hwy_right matches (10), hwy_divided differs (25), P present (5) vs TSMIS 0,
    # total differs (40). Every other category is absent both sides -> 0 == 0.
    _write_tsn_norm(tsn_path, [
        (_KEY["hwy_right"], 10),
        (_KEY["hwy_divided"], 25),
        (_KEY["ramp_P_dummy_paired"], 5),
        (_KEY["total_ramps"], 40),
    ])
    res = cmp.compare(tsmis_path, tsn_path, out_path, events=Events(),
                      confirm_overwrite=lambda _p: True, mode="values")
    check("compare ok", res.status == "ok")

    header, rows = _sheet(out_path, "Comparison")
    check("NO Route column (has_route=False)", "Route" not in header)
    cat_col = header.index("Category")
    cnt_col = header.index("Count")
    status_col = header.index("Status")
    by_cat = {r[cat_col]: r for r in rows}

    both = sum(1 for r in rows if r[status_col] == "Both")
    tsmis_only = sum(1 for r in rows if r[status_col] == "TSMIS only")
    check("31 categories matched on both sides", both == 31)
    check("Ramp Points w/out linework is the lone TSMIS-only row", tsmis_only == 1)

    ndiff = sum(1 for r in rows if DIFF in r[cnt_col])
    check("exactly 3 differing categories (Divided, P, Total)", ndiff == 3)
    check("P - Dummy Paired compares 0 (TSMIS) vs 5 (TSN)",
          DIFF in by_cat[_KEY["ramp_P_dummy_paired"]][cnt_col]
          and by_cat[_KEY["ramp_P_dummy_paired"]][cnt_col].startswith("0"))
    check("matching category (Right=10) shows no diff marker",
          DIFF not in by_cat[_KEY["hwy_right"]][cnt_col])

    # Familiar layout sheet present + readable.
    fh, fr = _sheet(out_path, summary_layout.RAMP_SUMMARY_SPEC.sheet_name)
    flat = [c for row in [fh] + fr for c in row]
    check("familiar sheet labels sides TSMIS and TSN", "TSMIS" in flat and "TSN" in flat)
    check("familiar sheet lists the P - Dummy Paired row",
          any("P - Dummy Paired" in c for c in flat))
    check("familiar sheet shows the Ramp Points footnote",
          any("Ramp Points w/out linework" in c for c in flat))
    print(f"      (both={both}, TSMIS-only={tsmis_only}, diffs={ndiff})")


def test_corrupt_pdf_is_valueerror():
    """A corrupt/truncated statewide PDF must honor the loader contract:
    ValueError (run_files_compare reports it cleanly), never a raw pdfplumber
    exception escaping into the matrix path."""
    import tempfile
    bad = Path(tempfile.mkdtemp()) / "TSN statewide.pdf"
    bad.write_bytes(b"%PDF-1.4 not really a pdf, just junk bytes with no xref")
    try:
        cmp._load_tsn(bad)
        check("corrupt PDF raises", False)
    except ValueError as e:
        check("corrupt PDF -> ValueError (loader contract)", True)
        check("...message names the file", "TSN statewide.pdf" in str(e))
    except Exception as e:  # noqa: BLE001 — the point of the test
        check(f"corrupt PDF -> ValueError, not {type(e).__name__}", False)


def main():
    test_schema_and_categories()
    test_tsmis_loader_sums()
    test_end_to_end()
    test_corrupt_pdf_is_valueerror()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL COMPARE-RAMP-SUMMARY-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
