"""Characterization check: Ramp Summary Combined-sheet schema-drift guard.

build_combined_sheet() places sections at FIXED row anchors sized for today's
schema lengths (Highway Groups / On-Off / Population / Ramp Types). The guard
_assert_combined_layout() must (a) pass for the shipped schema and (b) raise if
a section GROWS past its row budget so its rows reach/cross the next section's
header/Totals -- turning silent Combined-sheet corruption into a loud failure.
(Shrinkage and in-budget growth are intentionally allowed; only overlap raises.)
(v0.18.0 P0.)

Pure Python (no browser; the module imports openpyxl/pdfplumber lazily). Run
from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_ramp_summary_schema.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import consolidate_ramp_summary as crs  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


def test_layout_guard():
    print("_assert_combined_layout passes for the shipped schema:")
    ok = True
    try:
        crs._assert_combined_layout()
    except Exception as e:  # noqa: BLE001
        ok = False
        print("   unexpected:", type(e).__name__, e)
    check("shipped schema passes the guard", ok)

    print("the guard trips on growth past the row budget (overlap):")
    for name in ("HIGHWAY_GROUPS", "ONOFF", "POP_GROUPS", "RAMP_TYPES"):
        orig = getattr(crs, name)
        # Grow the list well past its row budget so it must overrun the anchor.
        grown = list(orig) + [(f"extra_{i}", r"^never$") for i in range(20)]
        setattr(crs, name, grown)
        try:
            tripped = _raises(crs._assert_combined_layout)
        finally:
            setattr(crs, name, orig)
        check(f"{name} grown past its budget trips the guard", tripped)

    check("guard clean again after restore", not _raises(crs._assert_combined_layout))


def test_anchors_have_headroom():
    print("each section fits below its anchor for the current schema:")
    cases = [
        ("Highway Groups", crs.HIGHWAY_GROUPS, crs._HG_FIRST_ROW, crs._ONOFF_HEADER_ROW),
        ("On/Off", crs.ONOFF, crs._ONOFF_FIRST_ROW, crs._POP_HEADER_ROW),
        ("Population", crs.POP_GROUPS, crs._POP_FIRST_ROW, crs._TOTALS_ROW),
        ("Ramp Types", crs.RAMP_TYPES, crs._RAMP_FIRST_ROW, crs._TOTALS_ROW),
    ]
    for nm, schema, first, anchor in cases:
        last = first + len(schema) - 1
        check(f"{nm} ({len(schema)} rows -> {first}-{last}) clears anchor {anchor}",
              last < anchor)


def main():
    test_layout_guard()
    test_anchors_have_headroom()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL RAMP-SUMMARY SCHEMA CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
