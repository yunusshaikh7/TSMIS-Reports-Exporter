"""Golden check for the cross-environment comparison MATRIX engine
(scripts/matrix.py). Offline — pure openpyxl, no browser/Excel/network.

Covers: cell enumeration + baseline flag; the mtime-staleness arithmetic;
stable dateless comparison paths; baseline-keyed result cache; and a REAL
orchestration over a synthetic store (tiny per-route xlsx with a planted diff)
that drives compare_env -> compare_core, then reads the discrepancy counts back
out of the produced values workbook and records them.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_matrix.py
"""
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import matrix
from events import Events
from openpyxl import Workbook

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


def test_enumeration():
    print("matrix_snapshot enumeration (empty store):")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_mx_"))
    try:
        snap = matrix.matrix_snapshot(dest, baseline_key="ssor-prod")
        check("four comparable rows incl. highway_log",
              snap["rows"] == ["ramp_summary", "ramp_detail", "highway_sequence", "highway_log"])
        check("all_rows lists every row with labels",
              [r["key"] for r in snap["all_rows"]] == snap["rows"]
              and all(r.get("label") for r in snap["all_rows"]))
        check("six env columns", len(snap["envs"]) == 6
              and snap["envs"][0] == "ssor-prod")
        check("no intersection row",
              not any("intersection" in r for r in snap["rows"]))
        # hidden filter: dropping a row removes it from rows but keeps it in all_rows
        hidden_snap = matrix.matrix_snapshot(dest, baseline_key="ssor-prod",
                                             hidden=["highway_log"])
        check("hidden row dropped from rows",
              "highway_log" not in hidden_snap["rows"] and len(hidden_snap["rows"]) == 3)
        check("hidden row still in all_rows + hidden list",
              any(r["key"] == "highway_log" for r in hidden_snap["all_rows"])
              and hidden_snap["hidden"] == ["highway_log"])
        cell = snap["cells"]["ramp_detail"]
        check("baseline column flagged", cell["ssor-prod"]["is_baseline"]
              and cell["ssor-prod"]["comparison"] is None)
        check("non-baseline cell has a comparison block",
              cell["ars-prod"]["comparison"] is not None)
        check("empty store -> export absent everywhere",
              not cell["ars-prod"]["export"]["present"])
        check("empty store -> comparison missing, both sides absent",
              cell["ars-prod"]["comparison"]["reason"] == "missing"
              and cell["ars-prod"]["comparison"]["missing_side"] == "both")
        check("env label derived", snap["env_labels"]["ssor-prod"] == "SSOR / Prod")
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_comparison_path_stable():
    print("comparison_path is stable + dateless (mtime is the freshness signal):")
    p = matrix.comparison_path("/d", "ssor-prod", "ramp_detail", "ars-test")
    check("keyed by cell+row under comparisons/<baseline>/",
          p.as_posix().endswith("comparisons/ssor-prod/ars-test_ramp_detail.xlsx"))
    check("no date in the name", re.search(r"\d{4}-\d{2}-\d{2}", p.name) is None)


def test_staleness():
    print("comparison_state mtime staleness:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_mxs_"))
    try:
        sub = "ramp_detail"
        cmp_p = matrix.comparison_path(dest, "ssor-prod", "ramp_detail", "ars-prod")
        cmp_p.parent.mkdir(parents=True, exist_ok=True)
        cmp_p.write_bytes(b"PK")
        t = time.time()
        os.utime(cmp_p, (t, t))

        def state(base_m, cell_m):
            ages = {"ssor-prod": {sub: {"mtime": base_m}},
                    "ars-prod": {sub: {"mtime": cell_m}}}
            return matrix.comparison_state(dest, "ssor-prod", "ramp_detail",
                                           "ars-prod", sub, ages, {})

        check("both sides older -> fresh",
              state(t - 100, t - 100)["stale"] is False
              and state(t - 100, t - 100)["reason"] == "fresh")
        check("baseline newer -> stale(baseline_newer)",
              state(t + 100, t - 100)["reason"] == "baseline_newer")
        check("cell newer -> stale(cell_newer)",
              state(t - 100, t + 100)["reason"] == "cell_newer")
        check("both newer -> stale(both_newer)",
              state(t + 100, t + 100)["reason"] == "both_newer")
        # comparison file missing entirely
        cmp_p.unlink()
        check("missing comparison -> stale(missing)",
              state(t - 100, t - 100)["reason"] == "missing"
              and state(t - 100, t - 100)["built"] is False)
        # a side never exported
        miss = state(None, t - 100)
        check("baseline side absent -> missing_side baseline",
              miss["missing_side"] == "baseline")
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def _write_route(path, header, data, sheet="TSAR - Ramp Detail"):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(header)
    for r in data:
        ws.append(r)
    wb.save(path)
    wb.close()


def test_orchestration_and_cache():
    print("build_cell_comparison drives compare_env + caches counts:")
    dest = Path(tempfile.mkdtemp(prefix="tsmis_mxo_"))
    try:
        HEADER = ["County", "PM", "Ramp ID", "Lighting"]
        BASE = [["LA", "1.000", "ON-A", "Yes"], ["LA", "2.000", "OFF-B", "No"]]
        # ars-prod: one field changed (1 diff cell) + one extra ramp (1 one-sided).
        CELL = [["LA", "1.000", "ON-A", "Yes"], ["LA", "2.000", "OFF-B", "YES"],
                ["LA", "2.500", "ON-NEW", "Yes"]]
        _write_route(dest / "ssor-prod" / "ramp_detail" / "tsar_ramp_detail_route_001.xlsx",
                     HEADER, BASE)
        _write_route(dest / "ars-prod" / "ramp_detail" / "tsar_ramp_detail_route_001.xlsx",
                     HEADER, CELL)

        res = matrix.build_cell_comparison(dest, "ssor-prod", "ramp_detail",
                                           "ars-prod", events=Events())
        check("compare ran ok", res.status == "ok")
        check("verdict = diff", res.verdict == "diff")
        out = matrix.comparison_path(dest, "ssor-prod", "ramp_detail", "ars-prod")
        check("comparison workbook written", out.exists())

        results = matrix.load_results(dest, "ssor-prod")
        rec = results.get("ramp_detail", {}).get("ars-prod", {})
        check("cache recorded 1 diff cell", rec.get("diff_cells") == 1)
        check("cache recorded 1 one-sided row", rec.get("one_sided") == 1)
        check("cache recorded the verdict", rec.get("verdict") == "diff")

        # The snapshot surfaces the cached counts as a FRESH cell.
        snap = matrix.matrix_snapshot(dest, baseline_key="ssor-prod")
        comp = snap["cells"]["ramp_detail"]["ars-prod"]["comparison"]
        check("snapshot: cell fresh", comp["stale"] is False)
        check("snapshot: surfaces diff_cells", comp["diff_cells"] == 1)
        check("snapshot: surfaces one_sided", comp["one_sided"] == 1)

        # cells_to_rebuild('stale') no longer lists this fresh cell.
        todo = matrix.cells_to_rebuild(snap, scope="stale")
        check("fresh cell not in stale rebuild list",
              ("ramp_detail", "ars-prod") not in todo)

        # Baseline switch -> a different tree; old results untouched.
        snap2 = matrix.matrix_snapshot(dest, baseline_key="ars-prod")
        comp2 = snap2["cells"]["ramp_detail"]["ssor-prod"]["comparison"]
        check("baseline switch: new tree, cell not yet built",
              comp2["built"] is False)
        check("old baseline results.json still present",
              (matrix.comparisons_root(dest, "ssor-prod") / "_results.json").exists())
        check("new baseline tree separate",
              matrix.comparisons_root(dest, "ars-prod")
              != matrix.comparisons_root(dest, "ssor-prod"))
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def main():
    test_enumeration()
    test_comparison_path_stable()
    test_staleness()
    test_orchestration_and_cache()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL MATRIX CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
