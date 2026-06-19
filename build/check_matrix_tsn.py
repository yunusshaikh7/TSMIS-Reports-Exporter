"""Golden check for the matrix TSN-vs-TSMIS engine (scripts/matrix.py): the
TSN paths, the supported-row map, TSN source detection (consolidated / PDFs /
none / explicit file), the snapshot's per-row mode + greyed unsupported cells,
the TSN rebuild list, and build_tsn_comparison's guard paths.

Pure filesystem + registry; no workbook content is needed for these (the LIVE
Highway-Log consolidate->compare path reuses the already-golden-locked
consolidate_highway_log + compare_highway_log and is exercised separately /
on the work PC with real TSN data).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_matrix_tsn.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import matrix

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def _touch(p, data=b"PK"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def test_paths_and_support():
    print("TSN paths + supported map:")
    d = "C:\\store"
    check("input root under _tsn_input/<subdir>",
          matrix.tsn_input_root(d, "highway_log").as_posix().endswith("_tsn_input/highway_log"))
    check("comparisons root under comparisons/tsn",
          matrix.tsn_comparisons_root(d).as_posix().endswith("comparisons/tsn"))
    cp = matrix.tsn_comparison_path(d, "highway_log", "ars-prod")
    check("comparison path is dateless + keyed by cell_row",
          cp.name == "ars-prod_highway_log.xlsx" and "comparisons/tsn" in cp.as_posix())
    check("highway_log is TSN-supported", matrix.tsn_supported("highway_log"))
    check("ramp_summary is NOT TSN-supported (greyed)",
          not matrix.tsn_supported("ramp_summary"))


def test_source_detection():
    print("tsn_source detection (file / consolidated / pdfs / none):")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsn_"))
    try:
        sub = "highway_log"
        check("empty folder -> none", matrix.tsn_source(dest, sub)["kind"] == "none")
        # only PDFs -> pdfs + count
        for i in range(3):
            _touch(matrix.tsn_input_root(dest, sub) / f"D0{i}_TSN.pdf", b"%PDF-1.4")
        src = matrix.tsn_source(dest, sub)
        check("only PDFs -> pdfs with count", src["kind"] == "pdfs" and src["pdf_count"] == 3)
        # a consolidated .xlsx wins over PDFs
        _touch(matrix.tsn_input_root(dest, sub) / "tsn_highway_log_consolidated.xlsx")
        src = matrix.tsn_source(dest, sub)
        check("consolidated .xlsx present -> consolidated", src["kind"] == "consolidated"
              and src["path"].endswith("tsn_highway_log_consolidated.xlsx"))
        # an explicit selected file wins over folder scan
        picked = dest / "elsewhere" / "my_tsn.xlsx"
        _touch(picked)
        src = matrix.tsn_source(dest, sub, selected_file=str(picked))
        check("explicit file selection wins", src["kind"] == "file"
              and src["path"] == str(picked))
        check("a non-xlsx selection is ignored (falls back to scan)",
              matrix.tsn_source(dest, sub, selected_file=str(dest / "nope.pdf"))["kind"]
              == "consolidated")
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_snapshot_modes():
    print("snapshot per-row mode + greyed unsupported TSN cells:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsnsnap_"))
    try:
        # HL in vs-TSN mode with both sides present; ramp_summary forced into TSN
        # mode too (unsupported -> greyed).
        _touch(dest / "ars-prod" / "highway_log" / "r1.xlsx")
        _touch(matrix.tsn_input_root(dest, "highway_log") / "tsn.xlsx")
        snap = matrix.matrix_snapshot(dest, baseline_key="ssor-prod",
                                      tsn_rows=["highway_log", "ramp_summary"])
        check("modes carries env vs tsn",
              snap["modes"]["highway_log"] == "tsn"
              and snap["modes"]["ramp_detail"] == "env")
        check("all_rows marks tsn_capable",
              {r["key"]: r["tsn_capable"] for r in snap["all_rows"]}["highway_log"] is True
              and {r["key"]: r["tsn_capable"] for r in snap["all_rows"]}["ramp_summary"] is False)
        hl = snap["cells"]["highway_log"]["ars-prod"]
        check("tsn-mode cell carries a 'tsn' block (not 'comparison')",
              "tsn" in hl and "comparison" not in hl and hl["tsn"]["supported"])
        check("HL tsn cell: both sides present -> not missing, not built yet",
              hl["tsn"]["missing_side"] is None and not hl["tsn"]["built"])
        rs = snap["cells"]["ramp_summary"]["ars-prod"]["tsn"]
        check("unsupported row in tsn mode -> supported False (greyed)",
              rs.get("supported") is False)
        check("env-mode row still has comparison block",
              "comparison" in snap["cells"]["ramp_detail"]["ars-prod"])
        check("tsn_meta carries the source summary for tsn rows",
              snap["tsn_meta"]["highway_log"]["source_kind"] == "consolidated"
              and "input_dir" in snap["tsn_meta"]["highway_log"])
        # rebuild lists: env list skips tsn rows; tsn list lists ready HL cell
        check("cross-env rebuild list skips tsn rows",
              all(rk != "highway_log" for rk, _ in matrix.cells_to_rebuild(snap, "all")))
        tsn_todo = matrix.tsn_cells_to_rebuild(snap, "all")
        check("tsn rebuild list includes the ready HL cell",
              ("highway_log", "ars-prod") in tsn_todo)
        check("tsn rebuild list excludes unsupported rows",
              all(rk != "ramp_summary" for rk, _ in tsn_todo))
        # a cell with a missing side is not rebuildable
        check("tsn rebuild skips a cell with no TSMIS export",
              ("highway_log", "ars-test") not in tsn_todo)
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_build_guards():
    print("build_tsn_comparison guard paths:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_tsnbuild_"))
    try:
        try:
            matrix.build_tsn_comparison(dest, "ramp_summary", "ars-prod", events=None)
            check("unsupported row raises", False)
        except ValueError:
            check("unsupported row raises", True)
        try:
            matrix.build_tsn_comparison(dest, "highway_log", "ars-prod", events=None)
            check("no TSN source raises", False)
        except ValueError:
            check("no TSN source raises", True)
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def main():
    test_paths_and_support()
    test_source_detection()
    test_snapshot_modes()
    test_build_guards()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL MATRIX-TSN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
