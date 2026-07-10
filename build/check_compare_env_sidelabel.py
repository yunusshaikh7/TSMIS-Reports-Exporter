"""Characterization check: compare_env side-label cap keeps the distinguisher.

The two compared sides become Excel sheet/tab names, capped to fit the 31-char
sheet-name limit ("Only in <label>" = 8 + 23). The cap must trim the BASE, not
the trailing distinguisher (a run date or an (A)/(B) suffix) -- otherwise two
same-source sides collapse to the same prefix and degrade to "Side A"/"Side B",
losing their provenance. (v0.18.0 P0: the cap was an incidental s[:23]; this
locks the explicit distinguisher-preserving behavior.)

Pure Python (no openpyxl / browser). Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_compare_env_sidelabel.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import compare_env  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def test_cap_label():
    print("_cap_label keeps the trailing distinguisher:")
    cap = compare_env._cap_label
    limit = compare_env._SIDE_LABEL_CAP
    check("cap derives from the 31-char sheet limit", limit == 31 - len("Only in "))
    check("short label unchanged", cap("SSOR-PROD") == "SSOR-PROD")
    # Long base + a run-date suffix: the date must survive the cap.
    capped = cap("VERYLONGSOURCE-ENVIRONMENT 2026-06-11")
    check("dated label fits the cap", len(capped) <= limit)
    check("date suffix preserved", capped.endswith(" 2026-06-11"))
    # Long base + (A)/(B): the suffix must survive and stay distinct.
    a = cap("VERYLONGSOURCE-ENVIRONMENT-NAME (A)")
    b = cap("VERYLONGSOURCE-ENVIRONMENT-NAME (B)")
    check("(A) suffix preserved within the cap", a.endswith(" (A)") and len(a) <= limit)
    check("(B) suffix preserved", b.endswith(" (B)"))
    check("(A)/(B) stay distinct under the cap", a != b)
    # Two same-base, different-date sides stay distinct (the regression).
    x = cap("SAME-LONG-SOURCE-ENVIRONMENT 2026-06-11")
    y = cap("SAME-LONG-SOURCE-ENVIRONMENT 2026-07-22")
    check("same base, different dates stay distinct", x != y)
    # No recognizable suffix -> plain end-truncation, still within the cap.
    plain = cap("X" * 40)
    check("no-suffix label still capped to the limit", len(plain) == limit)


def test_side_labels_integration():
    print("_side_labels preserves provenance (no needless Side A/B):")
    sl = compare_env._side_labels
    limit = compare_env._SIDE_LABEL_CAP
    # Same src-env, different run dates -> dates appended, both retained.
    la, lb = sl(Path("2026-06-11 ssor-prod"), Path("2026-07-22 ssor-prod"))
    check("same src-env, different days -> distinct dated labels",
          la != lb and "2026-06-11" in la and "2026-07-22" in lb)
    check("dated labels are not the Side A/B fallback",
          la != "Side A" and lb != "Side B")
    # Distinct src-env -> the short SRC-ENV names, unchanged.
    da, db = sl(Path("2026-06-11 ssor-prod"), Path("2026-06-11 ars-dev"))
    check("distinct src-env -> SSOR-PROD / ARS-DEV",
          da == "SSOR-PROD" and db == "ARS-DEV")
    for lbl in (la, lb, da, db):
        check(f"'{lbl}' fits the sheet-name cap", len(lbl) <= limit)


def test_labels_override():
    print("compare_folders labels override (v0.26.0, the baseline matrix):")
    # Functional: the override must reach the side machinery (labels=None keeps
    # the derived behavior the tests above lock). Two EMPTY folders make the
    # loader fail fast with a message that NAMES the side label — proving the
    # explicit labels (and the identical-override (A)/(B) fallback) apply.
    import shutil
    import tempfile
    a = Path(tempfile.mkdtemp(prefix="tsmis_lbl_a_"))
    b = Path(tempfile.mkdtemp(prefix="tsmis_lbl_b_"))
    try:
        res = compare_env.RAMP_DETAIL.compare_folders(
            a, b, a / "out.xlsx", labels=("MY DAY LABEL", "MY BASELINE"))
        check("explicit labels reach the side loader (error names them)",
              res.status == "error" and "MY DAY LABEL" in (res.message or ""))
        res2 = compare_env.RAMP_DETAIL.compare_folders(
            a, b, a / "out.xlsx", labels=("SAME", "SAME"))
        check("identical overrides degrade to (A)/(B)",
              res2.status == "error" and "SAME (A)" in (res2.message or ""))
        res3 = compare_env.RAMP_DETAIL.compare_folders(a, b, a / "out.xlsx")
        check("default (no labels) keeps the derived side names",
              res3.status == "error" and "MY DAY LABEL" not in (res3.message or ""))
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)


def main():
    test_cap_label()
    test_side_labels_integration()
    test_labels_override()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL SIDE-LABEL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
