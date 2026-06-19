"""Golden check for the matrix GUI bridge (gui_api matrix_* methods) with the
matrix workers stubbed — no browser, no real compare. Pure Python.

Covers: matrix_info shape + the "matrix" snapshot key; set_matrix_baseline
validation + persistence + recompute_pending; the single-task gate on
refresh_cell_comparison / refresh_cell_export / recompute_matrix; bad-key and
baseline-vs-baseline rejection; recompute over an empty store ('nothing') vs a
store with stale cells; and the HIGH-RISK integration — a cell export must NOT
clobber a paused Export-Everything batch's manifest.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_matrix_bridge.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import batch_manifest
import gui_api
import settings

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


class _FakeWorker:
    last = None

    def __init__(self, *args, **kwargs):
        _FakeWorker.last = (args, kwargs)

    def start(self):
        self.started = True


def _touch(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"PK")


def main():
    dest = Path(tempfile.mkdtemp(prefix="tsmis_mxb_"))
    cfgdir = Path(tempfile.mkdtemp(prefix="tsmis_mxbcfg_"))
    saved = (gui_api.MatrixCompareWorker, gui_api.MatrixExportWorker,
             gui_api.MatrixTsnConsolidateWorker,
             settings.get_batch_dest, settings.CONFIG_FILE)
    gui_api.MatrixCompareWorker = _FakeWorker
    gui_api.MatrixExportWorker = _FakeWorker
    gui_api.MatrixTsnConsolidateWorker = _FakeWorker
    settings.get_batch_dest = lambda: str(dest)
    settings.CONFIG_FILE = cfgdir / "config.json"
    settings._cache = settings._cache_mtime = None
    mpath = cfgdir / "batch_job.json"     # explicit test manifest — never the real one
    try:
        a = gui_api.GuiApi()

        print("matrix_info + snapshot key:")
        info = a.matrix_info()
        check("rows are the five comparable reports (incl. both Highway Log formats)",
              info["rows"] == ["ramp_summary", "ramp_detail", "highway_sequence",
                               "highway_log", "highway_log_pdf"])
        check("baseline defaults to ssor-prod", info["baseline"] == "ssor-prod")

        print("set_matrix_report (show/hide rows):")
        check("unknown row rejected", bool(a.set_matrix_report("nope", False).get("error")))
        hide = a.set_matrix_report("highway_log", False)
        check("hide ok + recorded", hide.get("ok") and "highway_log" in hide.get("hidden", []))
        check("hidden row gone from matrix_info", "highway_log" not in a.matrix_info()["rows"])
        check("show puts it back",
              a.set_matrix_report("highway_log", True).get("ok")
              and "highway_log" in a.matrix_info()["rows"])
        # can't hide them all (5 rows: hide 4, the 5th hide is rejected)
        for k in ("ramp_summary", "ramp_detail", "highway_sequence", "highway_log"):
            a.set_matrix_report(k, False)
        last = a.set_matrix_report("highway_log_pdf", False)
        check("can't hide the last remaining row", bool(last.get("error")))
        for k in ("ramp_summary", "ramp_detail", "highway_sequence", "highway_log"):
            a.set_matrix_report(k, True)
        check("snapshot carries the 'matrix' key (None idle)",
              "matrix" in a._state_snapshot() and a._state_snapshot()["matrix"] is None)

        print("set_matrix_baseline:")
        check("unknown baseline rejected",
              bool(a.set_matrix_baseline("nope-x").get("error")))
        res = a.set_matrix_baseline("ars-prod")
        check("valid baseline persists",
              res.get("baseline") == "ars-prod"
              and settings.get_matrix_baseline() == "ars-prod")
        check("recompute_pending present", "recompute_pending" in res)
        a.set_matrix_baseline("ssor-prod")            # back to default for the rest

        print("refresh_cell_comparison gate + validation:")
        check("unknown row rejected",
              bool(a.refresh_cell_comparison("nope", "ars-prod").get("error")))
        check("baseline column rejected",
              bool(a.refresh_cell_comparison("ramp_detail", "ssor-prod").get("error")))
        ok = a.refresh_cell_comparison("ramp_detail", "ars-prod")
        check("valid cell compare launched", ok.get("ok") is True)
        check("task claimed as 'matrix'", a._task == "matrix")
        check("second action refused while running",
              bool(a.refresh_cell_comparison("ramp_detail", "ars-dev").get("error")))
        a._end_task()

        print("recompute_matrix scope:")
        check("empty store -> nothing to do",
              a.recompute_matrix("all").get("nothing") is True)
        check("no task claimed when nothing to do", a._task is None)
        # Two sides present for ramp_detail -> one stale cell to rebuild.
        _touch(dest / "ssor-prod" / "ramp_detail" / "r1.xlsx")
        _touch(dest / "ars-prod" / "ramp_detail" / "r1.xlsx")
        rc = a.recompute_matrix("all")
        check("stale cells -> launched", rc.get("ok") and rc.get("count") >= 1)
        check("matrix progress state set",
              a._matrix is not None and a._matrix.get("total") >= 1)
        a._end_task()

        print("refresh_cell_export does NOT clobber a paused real batch:")
        real = batch_manifest.build([0, 1], [("ssor", "prod"), ("ars", "prod")],
                                    fast=False, workers=1, auto_consolidate=False)
        batch_manifest.save(real, mpath)
        before = batch_manifest.load(mpath)
        check("a real batch is pending", bool(batch_manifest.pending(before)))
        ex = a.refresh_cell_export("ramp_detail", "ars-prod")
        check("cell export launched", ex.get("ok") is True)
        after = batch_manifest.load(mpath)
        check("the paused batch manifest is intact",
              after == before and bool(batch_manifest.pending(after)))
        a._end_task()
        check("bad row for export rejected",
              bool(a.refresh_cell_export("nope", "ars-prod").get("error")))

        print("open_cell_comparison / open_comparisons_folder:")
        opened = []
        a._open_file = lambda p: opened.append(Path(p))
        a._open_folder = lambda p: opened.append(Path(p))
        check("open rejects unknown row",
              bool(a.open_cell_comparison("nope", "ars-prod").get("error")))
        check("open rejects the baseline column",
              bool(a.open_cell_comparison("ramp_detail", "ssor-prod").get("error")))
        check("open errors when no comparison file exists yet",
              bool(a.open_cell_comparison("ramp_detail", "ars-prod").get("error")))
        check("nothing was opened for the missing file", not opened)
        # Plant a comparison workbook where the matrix expects it, then open it.
        import matrix
        cpath = matrix.comparison_path(str(dest), "ssor-prod", "ramp_detail", "ars-prod")
        _touch(cpath)
        r = a.open_cell_comparison("ramp_detail", "ars-prod")
        check("open succeeds once the workbook exists", r.get("ok") is True)
        check("the correct workbook path was opened",
              opened and opened[-1] == cpath)
        fr = a.open_comparisons_folder()
        check("open comparisons folder ok", fr.get("ok") is True)
        check("the baseline comparisons root was opened",
              opened[-1] == matrix.comparisons_root(str(dest), "ssor-prod"))

        print("env-column toggle + per-row modes + global set-all:")
        eh = a.set_matrix_env("ars-dev", False)
        check("hide env ok", eh.get("ok") and "ars-dev" in eh.get("hidden_envs", []))
        check("hidden env gone from envs, kept in all_envs",
              "ars-dev" not in a.matrix_info()["envs"]
              and "ars-dev" in a.matrix_info()["all_envs"])
        a.set_matrix_env("ars-dev", True)
        check("unknown env rejected", bool(a.set_matrix_env("zz-zz", False).get("error")))
        check("unknown row mode-set rejected",
              bool(a.set_matrix_row_mode("nope", "tsn").get("error")))
        check("greyed mode rejected (ramp_summary vs TSN)",
              bool(a.set_matrix_row_mode("ramp_summary", "tsn").get("error")))
        check("supported mode set (HL Excel vs TSN)",
              a.set_matrix_row_mode("highway_log", "tsn").get("ok")
              and a.matrix_info()["modes"]["highway_log"] == "tsn")
        check("HL PDF vs_excel mode set",
              a.set_matrix_row_mode("highway_log_pdf", "vs_excel").get("ok"))
        a.set_matrix_row_mode("highway_log", "env")
        a.set_matrix_row_mode("highway_log_pdf", "env")
        check("set-all bad mode rejected", bool(a.set_all_matrix_modes("nope").get("error")))
        a.set_all_matrix_modes("tsn")
        m = a.matrix_info()["modes"]
        check("set-all tsn applies to the supported HL rows",
              m["highway_log"] == "tsn" and m["highway_log_pdf"] == "tsn")
        a.set_all_matrix_modes("env")
        check("set-all env clears every row to cross-env",
              all(v == "env" for v in a.matrix_info()["modes"].values()))

        print("TSN file pick + scoped refresh + TSN-PDF consolidate gate:")
        check("tsn file bad subdir rejected",
              bool(a.set_matrix_tsn_file("nope", "/x.xlsx").get("error")))
        check("tsn file set ok", a.set_matrix_tsn_file("highway_log", "/x.xlsx").get("ok"))
        a.set_matrix_tsn_file("highway_log", "")
        _touch(dest / "ssor-prod" / "ramp_detail" / "r1.xlsx")
        _touch(dest / "ars-prod" / "ramp_detail" / "r1.xlsx")
        rrow = a.recompute_matrix("all", row="ramp_detail")
        check("per-row refresh launched", rrow.get("ok") and rrow.get("count", 0) >= 1)
        a._end_task()
        rcol = a.recompute_matrix("all", env="ars-prod")
        check("per-column refresh launched", rcol.get("ok") and rcol.get("count", 0) >= 1)
        a._end_task()
        check("consolidate TSN rejects non-Highway-Log",
              bool(a.consolidate_matrix_tsn("ramp_detail").get("error")))
        ct = a.consolidate_matrix_tsn("highway_log")
        check("consolidate TSN launched + task claimed",
              ct.get("ok") is True and a._task == "matrix")
        a._end_task()
    finally:
        (gui_api.MatrixCompareWorker, gui_api.MatrixExportWorker,
         gui_api.MatrixTsnConsolidateWorker,
         settings.get_batch_dest, settings.CONFIG_FILE) = saved
        settings._cache = settings._cache_mtime = None
        shutil.rmtree(dest, ignore_errors=True)
        shutil.rmtree(cfgdir, ignore_errors=True)

    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL MATRIX-BRIDGE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
