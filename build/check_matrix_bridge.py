"""Golden check for the matrix GUI bridge (gui_api matrix_* methods) with the
matrix workers stubbed — no browser, no real compare. Pure Python.

Covers: matrix_info shape + the "matrix" snapshot key; set_matrix_baseline
validation + persistence + recompute_pending; bad-key and baseline-vs-baseline
rejection; recompute over an empty store ('nothing') vs a store with stale cells;
the HIGH-RISK integration — a cell export must NOT clobber a paused
Export-Everything batch's manifest; and (v0.16.0) the matrix JOB QUEUE — a 2nd
action queues instead of being rejected, jobs auto-advance from _end_task,
reorder/remove/clear/stop-all edit the pending queue, row/column re-export
resolves steps, a no-work job is dropped on drain, an auth error clears the
queue, and the fast-mode toggle persists into the snapshot.

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
    saved = (gui_api.MatrixCompareWorker, gui_api.MatrixBatchExportWorker,
             gui_api.MatrixTsnConsolidateWorker, gui_api.clear_auth,
             settings.get_batch_dest, settings.CONFIG_FILE)
    gui_api.MatrixCompareWorker = _FakeWorker
    gui_api.MatrixBatchExportWorker = _FakeWorker
    gui_api.MatrixTsnConsolidateWorker = _FakeWorker
    gui_api.clear_auth = lambda: None     # no auth-file side effects in the test
    settings.get_batch_dest = lambda: str(dest)
    settings.CONFIG_FILE = cfgdir / "config.json"
    settings._cache = settings._cache_mtime = None
    mpath = cfgdir / "batch_job.json"     # explicit test manifest — never the real one
    try:
        a = gui_api.GuiApi()

        print("matrix_info + snapshot key:")
        info = a.matrix_info()
        check("rows are all seven comparable reports (both HL formats + both Intersection, cross-env)",
              info["rows"] == ["ramp_summary", "ramp_detail", "highway_sequence",
                               "highway_log", "intersection_summary",
                               "intersection_detail", "highway_log_pdf"])
        check("baseline defaults to ssor-prod", info["baseline"] == "ssor-prod")

        print("set_matrix_report (show/hide rows):")
        check("unknown row rejected", bool(a.set_matrix_report("nope", False).get("error")))
        hide = a.set_matrix_report("highway_log", False)
        check("hide ok + recorded", hide.get("ok") and "highway_log" in hide.get("hidden", []))
        check("hidden row gone from matrix_info", "highway_log" not in a.matrix_info()["rows"])
        check("show puts it back",
              a.set_matrix_report("highway_log", True).get("ok")
              and "highway_log" in a.matrix_info()["rows"])
        # can't hide them all (7 rows: hide 6, the 7th hide is rejected)
        for k in ("ramp_summary", "ramp_detail", "highway_sequence", "highway_log",
                  "intersection_summary", "intersection_detail"):
            a.set_matrix_report(k, False)
        last = a.set_matrix_report("highway_log_pdf", False)
        check("can't hide the last remaining row", bool(last.get("error")))
        for k in ("ramp_summary", "ramp_detail", "highway_sequence", "highway_log",
                  "intersection_summary", "intersection_detail"):
            a.set_matrix_report(k, True)
        snap0 = a._state_snapshot()
        check("snapshot carries the 'matrix' key (None idle)",
              "matrix" in snap0 and snap0["matrix"] is None)
        check("snapshot carries the queue keys (empty/idle)",
              snap0.get("matrix_queue") == [] and snap0.get("matrix_current") is None)
        check("snapshot carries matrix_fast (off by default)",
              isinstance(snap0.get("matrix_fast"), dict)
              and snap0["matrix_fast"].get("on") is False
              and isinstance(snap0["matrix_fast"].get("workers"), int))
        check("snapshot carries both formulas flags (off by default)",
              snap0.get("matrix_formulas") is False
              and snap0.get("day_matrix_formulas") is False)

        print("set_matrix_baseline:")
        check("unknown baseline rejected",
              bool(a.set_matrix_baseline("nope-x").get("error")))
        res = a.set_matrix_baseline("ars-prod")
        check("valid baseline persists",
              res.get("baseline") == "ars-prod"
              and settings.get_matrix_baseline() == "ars-prod")
        check("recompute_pending present", "recompute_pending" in res)
        a.set_matrix_baseline("ssor-prod")            # back to default for the rest

        print("refresh_cell_comparison enqueue + validation:")
        check("unknown row rejected",
              bool(a.refresh_cell_comparison("nope", "ars-prod").get("error")))
        check("baseline column rejected",
              bool(a.refresh_cell_comparison("ramp_detail", "ssor-prod").get("error")))
        ok = a.refresh_cell_comparison("ramp_detail", "ars-prod")
        check("valid cell compare launched (becomes current)", ok.get("ok") is True)
        check("task claimed as 'matrix'", a._task == "matrix")
        cur = a._state_snapshot().get("matrix_current")
        check("current job mirrored in the snapshot",
              cur and cur.get("kind") == "compare" and cur.get("status") == "running")
        # A SECOND action now QUEUES (it isn't rejected).
        q2 = a.refresh_cell_comparison("ramp_detail", "ars-dev")
        check("second action queues (not rejected)", q2.get("ok") is True)
        check("the queue now holds one pending job",
              len(a._state_snapshot().get("matrix_queue", [])) == 1)
        # Draining the running job auto-advances the queued one into 'current'.
        a._end_task()
        check("auto-advanced: queued job is now running",
              a._task == "matrix" and not a._state_snapshot().get("matrix_queue"))
        a._end_task()
        check("queue fully drained -> idle", a._task is None)

        print("recompute_matrix scope:")
        check("empty store -> nothing to do",
              a.recompute_matrix("all").get("nothing") is True)
        check("no task claimed when nothing to do", a._task is None)
        # Two sides present for ramp_detail -> one stale cell to rebuild.
        _touch(dest / "ssor-prod" / "ramp_detail" / "r1.xlsx")
        _touch(dest / "ars-prod" / "ramp_detail" / "r1.xlsx")
        rc = a.recompute_matrix("all")
        check("stale cells -> launched", rc.get("ok") and a._task == "matrix")
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
        check("highway_sequence vs TSN mode now accepted (v0.17.0 FLAT)",
              a.set_matrix_row_mode("highway_sequence", "tsn").get("ok")
              and a.matrix_info()["modes"]["highway_sequence"] == "tsn")
        check("HL-PDF cross-env mode now accepted (v0.17.0 — env coded)",
              a.set_matrix_row_mode("highway_log_pdf", "env").get("ok")
              and a.matrix_info()["modes"].get("highway_log_pdf", "env") == "env")
        check("supported mode set (HL Excel vs TSN)",
              a.set_matrix_row_mode("highway_log", "tsn").get("ok")
              and a.matrix_info()["modes"]["highway_log"] == "tsn")
        check("HL PDF vs_excel mode set",
              a.set_matrix_row_mode("highway_log_pdf", "vs_excel").get("ok"))
        a.set_matrix_row_mode("highway_log", "env")
        a.set_matrix_row_mode("highway_log_pdf", "env")
        check("set-all bad mode rejected", bool(a.set_all_matrix_modes("nope").get("error")))
        a.set_all_matrix_modes("tsn")
        info = a.matrix_info()
        m = info["modes"]
        # Must apply to EVERY tsn-capable row — not just the two Highway Log rows
        # (the original assumption). v0.17.0 makes every report vs-TSN capable.
        tsn_rows = [r["key"] for r in info["all_rows"]
                    if r.get("tsn_capable") and r["key"] in m]
        check("set-all tsn applies to EVERY tsn-capable row (not just Highway Log)",
              len(tsn_rows) > 2 and all(m[rk] == "tsn" for rk in tsn_rows))
        a.set_all_matrix_modes("env")
        check("set-all env clears every row to cross-env",
              all(v == "env" for v in a.matrix_info()["modes"].values()))

        print("drag-to-reorder bridge (rows + env columns; v0.17.0 Phase 4b):")
        natural = a.matrix_info()["rows"]
        r = a.set_matrix_row_order([natural[-1], "zz-bogus"])   # unknown dropped
        check("set_matrix_row_order persists + drops unknown keys",
              r.get("ok") and r["order"] == [natural[-1]]
              and settings.get_matrix_row_order() == [natural[-1]])
        check("matrix_info applies the row order (chosen row first)",
              a.matrix_info()["rows"][0] == natural[-1])
        envs0 = a.matrix_info()["envs"]
        e = a.set_matrix_env_order([envs0[-1]])
        check("set_matrix_env_order persists + applies",
              e.get("ok") and a.matrix_info()["envs"][0] == envs0[-1])
        a.set_matrix_row_order([]); a.set_matrix_env_order([])   # reset
        check("clearing the order restores natural order",
              a.matrix_info()["rows"] == natural)
        dr = a.set_day_matrix_row_order(["highway_log", "zz"])
        check("set_day_matrix_row_order persists + drops unknown",
              dr.get("ok") and dr["order"] == ["highway_log"]
              and settings.get_day_matrix_row_order() == ["highway_log"])
        a.set_day_matrix_row_order([])

        print("TSN file pick + scoped refresh + TSN-PDF consolidate gate:")
        check("tsn file bad subdir rejected",
              bool(a.set_matrix_tsn_file("nope", "/x.xlsx").get("error")))
        check("tsn file set ok", a.set_matrix_tsn_file("highway_log", "/x.xlsx").get("ok"))
        a.set_matrix_tsn_file("highway_log", "")
        _touch(dest / "ssor-prod" / "ramp_detail" / "r1.xlsx")
        _touch(dest / "ars-prod" / "ramp_detail" / "r1.xlsx")
        rrow = a.recompute_matrix("all", row="ramp_detail")
        check("per-row refresh launched", rrow.get("ok") and a._task == "matrix")
        a._end_task()
        rcol = a.recompute_matrix("all", env="ars-prod")
        check("per-column refresh launched", rcol.get("ok") and a._task == "matrix")
        a._end_task()
        check("consolidate TSN rejects non-Highway-Log",
              bool(a.consolidate_matrix_tsn("ramp_detail").get("error")))
        ct = a.consolidate_matrix_tsn("highway_log")
        check("consolidate TSN launched + task claimed",
              ct.get("ok") is True and a._task == "matrix")
        a._end_task()

        print("matrix job queue — fast toggle, row/column export, edit, drain:")
        check("fast mode off by default", settings.get_matrix_fast() is False)
        a.set_matrix_fast(True)
        check("fast toggle persists + snapshot reflects it",
              settings.get_matrix_fast() is True
              and a._state_snapshot()["matrix_fast"]["on"] is True)
        a.set_matrix_fast(False)
        check("formulas toggle off by default", settings.get_matrix_formulas() is False)
        a.set_matrix_formulas(True)
        check("formulas toggle persists + snapshot reflects it",
              settings.get_matrix_formulas() is True
              and a._state_snapshot().get("matrix_formulas") is True)
        # The by-day matrix has its OWN formulas toggle — independent of the above.
        check("day formulas off by default", settings.get_day_matrix_formulas() is False)
        a.set_day_matrix_formulas(True)
        check("day formulas persists + snapshot reflects it",
              settings.get_day_matrix_formulas() is True
              and a._state_snapshot().get("day_matrix_formulas") is True)
        check("toggling day formulas OFF leaves the Everything one ON (independent)",
              a.set_day_matrix_formulas(False).get("on") is False
              and settings.get_matrix_formulas() is True
              and settings.get_day_matrix_formulas() is False)
        a.set_matrix_formulas(False)
        # Two real exportable sides so row/column export resolves >=1 step.
        _touch(dest / "ssor-prod" / "ramp_detail" / "r1.xlsx")
        rr = a.refresh_row_export("ramp_detail")
        check("row re-export launched", rr.get("ok") is True and a._task == "matrix")
        steps = _FakeWorker.last[0][0]      # MatrixBatchExportWorker(steps, ...)
        check("row export resolved one step per visible env",
              isinstance(steps, list) and len(steps) == len(a.matrix_info()["envs"]))
        a._end_task()
        rc = a.refresh_column_export("ars-prod")
        check("column re-export launched", rc.get("ok") is True and a._task == "matrix")
        csteps = _FakeWorker.last[0][0]
        check("column export resolved one step per exportable row (HL PDF has no export)",
              isinstance(csteps, list) and 1 <= len(csteps) <= len(a.matrix_info()["rows"]))
        check("bad row for row-export rejected",
              bool(a.refresh_row_export("nope").get("error")))
        check("bad env for column-export rejected",
              bool(a.refresh_column_export("zz-zz").get("error")))
        # Build a pending queue behind the running column export, then edit it.
        j1 = a.refresh_cell_comparison("ramp_detail", "ars-dev")["job_id"]
        j2 = a.refresh_cell_comparison("ramp_detail", "ars-test")["job_id"]
        ids = lambda: [j["id"] for j in a._state_snapshot()["matrix_queue"]]
        check("two jobs pending behind the running one", ids() == [j1, j2])
        a.matrix_queue_move(j2, "up")
        check("move up reorders the pending queue", ids() == [j2, j1])
        a.matrix_queue_remove(j1)
        check("remove drops one pending job", ids() == [j2])
        a.matrix_queue_clear()
        check("clear empties the pending queue (running keeps going)",
              ids() == [] and a._task == "matrix")
        a._end_task()
        check("idle after the running export ends", a._task is None)

        print("no-work job is dropped on drain; auth error clears the queue:")
        # A running cell export, with a Highway-Log row rebuild queued behind it.
        # HL has no store exports, so every HL cell has a missing side and the
        # rebuild resolves to ZERO cells — the queued job is a no-op and must be
        # DROPPED (not left stuck) when the gate frees.
        a.refresh_cell_export("ramp_detail", "ars-prod")        # running
        a.recompute_matrix("all", row="highway_log")            # enqueues (not idle)
        check("a no-work rebuild is queued behind the export",
              len(a._state_snapshot()["matrix_queue"]) == 1)
        a._end_task()                          # drains -> no-work job dropped
        check("no-work job dropped, queue idle",
              a._task is None and not a._state_snapshot()["matrix_queue"])
        # Auth error mid-queue clears everything pending.
        a.refresh_cell_export("ramp_detail", "ssor-prod")   # running
        a.refresh_cell_export("ramp_detail", "ars-prod")    # queued
        check("one job queued behind the running export",
              len(a._state_snapshot()["matrix_queue"]) == 1)
        a._on_error(("auth", "session expired"))
        check("auth error clears the pending queue + frees the gate",
              a._task is None and not a._state_snapshot()["matrix_queue"])
        check("stop-all on an empty/idle queue is a no-op",
              a.matrix_stop_all().get("cleared") == 0)
    finally:
        (gui_api.MatrixCompareWorker, gui_api.MatrixBatchExportWorker,
         gui_api.MatrixTsnConsolidateWorker, gui_api.clear_auth,
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
