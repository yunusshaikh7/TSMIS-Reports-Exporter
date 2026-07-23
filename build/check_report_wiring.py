"""build/check_report_wiring.py — the report-integration WIRING check (M2-A, v0.31.0).

Derives from `report_catalog` what every registered report MUST have per integration
tier and FAILS naming the missing touchpoint — so the "add a report, forget one
mirror" class (the v0.17.3 field crash, where a matrix cell dispatched to a
comparator the author never registered) is caught at gate time, not in the field.

It asserts the DERIVATIONS agree (check_report_catalog owns the frozen-baseline
equivalence; this owns the cross-module wiring):
  * MATRIX <-> matrix_rows parity — every cross-env matrix row has a MATRIX wiring
    entry and vice versa (no row can reach an unregistered comparator);
  * every declared vs-TSN / self comparator resolves to a dispatchable adapter;
  * every dual-edition (PDF) family is wired both ways — Excel sibling, self
    comparator, vs-TSN comparator, both editions exported, a shared TSN dataset;
  * day_matrix._day_rows agrees with the MATRIX fmt + support for every row;
  * the Reset (Delete-all-reports) cleanup lists cover every wired PDF report, so a
    new report's consolidated outputs are actually removable.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_report_wiring.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import day_matrix
import gui_worker_maint
import matrix
import report_catalog
import reports

_fail = []


def check(name, cond, detail=""):
    suffix = f"  -> {detail}" if (not cond and detail) else ""
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}{suffix}")
    if not cond:
        _fail.append(name)


def _dispatchable(adapter):
    """A comparator adapter is dispatchable iff it exposes compare(...) — the
    contract matrix_build calls (a module or an instance, both qualify)."""
    return callable(getattr(adapter, "compare", None))


def test_matrix_parity():
    print("MATRIX <-> matrix_rows parity (every cross-env row is wired, and vice versa):")
    matrix_row_keys = {rk for rk, *_ in reports.matrix_rows()}
    wired = {m.row_key for m in report_catalog.matrix_rows_meta()}
    missing = sorted(matrix_row_keys - wired)
    check("every matrix row has a report_catalog.MATRIX wiring entry", not missing,
          f"unwired matrix rows (add a MATRIX entry): {missing}")
    extra = sorted(wired - matrix_row_keys)
    check("every MATRIX row is a real cross-environment matrix row", not extra,
          f"MATRIX rows absent from matrix_rows() (missing a cmp:*:env recipe?): {extra}")


def test_comparators_dispatchable():
    print("every declared comparator resolves to a dispatchable adapter:")
    for m in report_catalog.matrix_rows_meta():
        if m.tsn_key is not None:
            adapter = matrix.tsn_comparator_for(m.row_key)
            check(f"{m.row_key}: vs-TSN comparator ({m.tsn_key}) dispatchable",
                  adapter is not None and _dispatchable(adapter),
                  f"could not resolve {m.tsn_key} to a compare()-exposing adapter")
        if m.self_key is not None:
            adapter = matrix._pdf_self_comparator(m.self_pdf)
            check(f"{m.row_key}: self comparator ({m.self_key}) dispatchable",
                  adapter is not None and _dispatchable(adapter),
                  f"could not resolve {m.self_key} (self_pdf={m.self_pdf})")


def test_dual_edition_families():
    print("every dual-edition (PDF) family is fully wired both ways:")
    export_keys = set(report_catalog.export_keys())
    tsn_subdirs = {t.subdir for t in report_catalog.tsn_entries()}
    for m in report_catalog.matrix_rows_meta():
        if m.fmt != "pdf":
            continue
        check(f"{m.row_key}: names a real Excel-sibling subdir (self_other)",
              m.self_other in export_keys, f"self_other={m.self_other!r}")
        check(f"{m.row_key}: has a self (PDF-vs-Excel) comparator", m.self_key is not None)
        check(f"{m.row_key}: has a vs-TSN comparator", m.tsn_key is not None)
        check(f"{m.row_key}: shares its Excel sibling's TSN dataset",
              m.tsn_subdir == m.self_other and m.tsn_subdir in tsn_subdirs,
              f"tsn_subdir={m.tsn_subdir!r}, self_other={m.self_other!r}")


def test_day_matrix_agrees():
    print("day_matrix._day_rows agrees with MATRIX (fmt + presence) for every row:")
    day = {r[0]: r for r in day_matrix._day_rows()}
    for m in report_catalog.matrix_rows_meta():
        row = day.get(m.row_key)
        check(f"{m.row_key}: present in the by-day matrix", row is not None)
        if row is not None:
            check(f"{m.row_key}: by-day fmt == MATRIX fmt ({m.fmt!r})", row[3] == m.fmt,
                  f"by-day fmt={row[3]!r}")


def test_reset_covers_pdf_reports():
    print("the Reset cleanup lists cover every wired PDF report (its outputs removable):")
    legacy_dirs = set(gui_worker_maint._LEGACY_OUTPUT_DIRS)
    legacy_files = {name for name, _lbl in gui_worker_maint._LEGACY_CONSOLIDATED_FILES}
    for m in report_catalog.matrix_rows_meta():
        if m.fmt != "pdf":
            continue
        check(f"{m.row_key}: its output subdir is a Reset legacy-dir target",
              m.row_key in legacy_dirs,
              f"add {m.row_key!r} to gui_worker_maint._LEGACY_OUTPUT_DIRS")
        wb = f"tsmis_{m.row_key}_consolidated.xlsx"
        check(f"{m.row_key}: its consolidated workbook ({wb}) is a Reset target",
              wb in legacy_files,
              f"add {wb!r} to gui_worker_maint._LEGACY_CONSOLIDATED_FILES")


def main():
    print("=== report-integration wiring (M2-A) ===")
    test_matrix_parity()
    test_comparators_dispatchable()
    test_dual_edition_families()
    test_day_matrix_agrees()
    test_reset_covers_pdf_reports()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL REPORT-WIRING CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
