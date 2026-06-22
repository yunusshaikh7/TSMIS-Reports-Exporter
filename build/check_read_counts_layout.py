"""CT-14 -- matrix.read_counts layout detection (F4 / O4).

read_counts locates the count columns by the INVARIANT 'Status'/'Diffs' header
LABELS compare_core writes in every flavor — NOT by guessing the layout from
column A. That matters because the FLAT (has_route=False) Ramp Summary and
Intersection Summary cross-env adapters also put 'Route' in column A (their schema
header begins with 'Route'), so an A1-based guess miscounts them (the P1-B01 bug:
Ramp Summary read (1,1) instead of the correct (1,2)).

This builds Comparison workbooks in the EXACT compare_core shapes — Route-keyed
and flat-with-'Route'-in-A — and proves the counts are correct and survive
end-to-end through build_cell_comparison into the cache.

openpyxl only -- no browser/network. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_read_counts_layout.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import matrix                       # noqa: E402
from events import ConsolidateResult   # noqa: E402
from openpyxl import Workbook       # noqa: E402

_NEQ = matrix._NEQ                  # the real ' ≠ ' diff marker read_counts scans for
_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _comparison_wb(path, header, data_rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Comparison"
    ws.append(header)
    for r in data_rows:
        ws.append(r)
    wb.save(path)


# compare_core id_headers: [("Route" if has_route) + key, "#", "A Row", "B Row",
# "Status", "Diffs"] + fields. Both flavors below put "Route" in column A.
_ROUTE_HEADER = ["Route", "PM", "#", "SSOR Row", "ARS Row", "Status", "Diffs", "FT", "Desc"]
_FLAT_ROUTE_HEADER = ["Route", "#", "SSOR Row", "ARS Row", "Status", "Diffs", "Category", "Count"]


def _route_rows():
    # 1 diff cell (Desc), 1 one-sided (Only A).
    return [["5", "1.0", 1, "r1", "r2", "Both", "", "ok", f"a{_NEQ}b"],
            ["9", "2.0", 1, "r3", "", "Only A", "", "x", "y"]]


def _flat_rows():
    # 1 diff cell (Count), 2 one-sided (Only A + Only B) — Codex's RS shape.
    return [["5", 1, "r1", "r2", "Both", "", "Cat1", f"10{_NEQ}12"],
            ["9", 1, "r3", "", "Only A", "", "Cat2", "z"],
            ["101", 1, "r4", "", "Only B", "", "Cat3", "w"]]


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        route = tmp / "route.xlsx"
        _comparison_wb(route, _ROUTE_HEADER, _route_rows())
        flat = tmp / "flat.xlsx"
        _comparison_wb(flat, _FLAT_ROUTE_HEADER, _flat_rows())     # column A == 'Route', FLAT

        print("counts located by the invariant Status/Diffs labels:")
        check("Route-keyed sheet -> (1 diff, 1 one-sided)", matrix.read_counts(route) == (1, 1))
        check("FLAT aggregate sheet whose column A is 'Route' -> (1 diff, 2 one-sided)",
              matrix.read_counts(flat) == (1, 2))

        print("the P1-B01 bug: an A1=='Route' flat sheet is NOT mis-read as Route-keyed:")
        check("flat-with-Route-in-A no longer returns the wrong (1, 1)",
              matrix.read_counts(flat) != (1, 1))
        check("the has_route HINT cannot override the labels (no A1 reliance)",
              matrix.read_counts(flat, has_route=True) == (1, 2)
              and matrix.read_counts(route, has_route=False) == (1, 1))

        print("a flat sheet with a non-'Route' key (Category) still reads correctly:")
        flat_cat = tmp / "flat_cat.xlsx"
        _comparison_wb(flat_cat, ["Category", "#", "A Row", "B Row", "Status", "Diffs", "F1"],
                       [["c1", 1, "r1", "r2", "Both", "", f"a{_NEQ}b"],
                        ["c2", 1, "r3", "", "Only A", "", "x"]])
        check("flat 'Category' sheet -> (1, 1)", matrix.read_counts(flat_cat) == (1, 1))

        print("fallback when the labels are absent (foreign/malformed sheet):")
        nolabel = tmp / "nolabel.xlsx"
        _comparison_wb(nolabel, ["Route", "key", "#", "A", "B", "S", "D", "F1"],
                       [["5", "k", 1, "r1", "r2", "Both", "", f"a{_NEQ}b"]])
        check("no Status/Diffs labels -> uses the has_route fallback (no crash)",
              matrix.read_counts(nolabel) == (1, 0))
        check("unreadable input -> (None, None)", matrix.read_counts(tmp / "nope.xlsx") == (None, None))

        print("end-to-end: a FLAT-with-Route-in-A comparison survives into the cache (O4):")
        dest = tmp / "dest"

        class _StubAgg:
            """An aggregate cross-env adapter whose Comparison sheet is FLAT with
            'Route' in column A (like compare_env.RAMP_SUMMARY)."""
            subdir = "ramp_summary"
            key = "ramp_summary"
            sheet_name = "TSAR - Ramp Summary"     # has a sheet_name yet emits a FLAT sheet (the O4 trap)
            REPORT_NAME = "Ramp Summary"

            def compare_folders(self, dir_a, dir_b, out_path, events=None,
                                confirm_overwrite=None, mode="values"):
                _comparison_wb(Path(out_path), _FLAT_ROUTE_HEADER, _flat_rows())
                return ConsolidateResult(status="ok", verdict="diff", output_path=str(out_path))

        row_defs = {"ramp_summary": ("Ramp Summary", "ramp_summary", 0, _StubAgg(), True)}
        # both sides need a folder to exist for the path math; the stub ignores contents.
        (dest / "ars-prod").mkdir(parents=True, exist_ok=True)
        (dest / "ssor-prod").mkdir(parents=True, exist_ok=True)
        matrix.build_cell_comparison(dest, "ssor-prod", "ramp_summary", "ars-prod",
                                     events=None, row_defs=row_defs)
        cached = matrix.load_results(dest, "ssor-prod").get("ramp_summary", {}).get("ars-prod", {})
        check("build_cell_comparison cached the CORRECT flat counts (diff=1)",
              cached.get("diff_cells") == 1)
        check("...and one_sided=2 (not the mis-read 1)", cached.get("one_sided") == 2)

        print()
        if _failures:
            print(f"FAILED: {len(_failures)} check(s): {_failures}")
            return 1
        print("ALL READ-COUNTS LAYOUT CHECKS PASSED")
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
