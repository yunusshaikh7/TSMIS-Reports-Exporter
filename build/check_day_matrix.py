"""Golden check for the Compare-tab "TSN by day" matrix: the day_matrix engine
(rows/sources, available-day detection, snapshot with greyed rows + TSN source,
the scoped rebuild list, build_day_cell guard paths) AND the gui_api bridge
(source/day/report validation, build/rebuild enqueue onto the SHARED matrix
queue, open guards). Workers stubbed; no browser, no real compare (the live
consolidate -> compare path reuses the already-golden consolidate_*/compare_* and
is exercised on the work PC with real TSN data).

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_day_matrix.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import day_matrix
import gui_api
import matrix
import paths
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


def _touch(p, data=b"PK"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


def main():
    out = Path(tempfile.mkdtemp(prefix="tsmis_day_out_"))
    dest = Path(tempfile.mkdtemp(prefix="tsmis_day_dest_"))
    cfgdir = Path(tempfile.mkdtemp(prefix="tsmis_day_cfg_"))
    saved = (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT, gui_api.DayMatrixCompareWorker,
             gui_api.MatrixCompareWorker, settings.get_batch_dest, settings.CONFIG_FILE)
    paths.OUTPUT_ROOT = out
    day_matrix.OUTPUT_ROOT = out
    gui_api.DayMatrixCompareWorker = _FakeWorker
    gui_api.MatrixCompareWorker = _FakeWorker
    settings.get_batch_dest = lambda: str(dest)
    settings.CONFIG_FILE = cfgdir / "config.json"
    settings._cache = settings._cache_mtime = None
    try:
        # Plant two ssor-prod days (one with both HL formats) + one ars-prod day.
        _touch(out / "2026-06-17 ssor-prod" / "highway_log" / "r1.xlsx")
        _touch(out / "2026-06-18 ssor-prod" / "highway_log" / "r1.xlsx")
        _touch(out / "2026-06-18 ssor-prod" / "highway_log_pdf" / "r1.pdf", b"%PDF-1.4")
        _touch(out / "2026-06-17 ars-prod" / "highway_log" / "r1.xlsx")
        # A consolidated TSN workbook in the shared _tsn_input folder.
        _touch(matrix.tsn_input_root(dest, "highway_log") / "tsn.xlsx")

        print("day_matrix engine — sources, rows, available days:")
        check("six data sources", len(day_matrix.sources()) == 6
              and "ssor-prod" in day_matrix.sources())
        rows = {r[0]: r for r in day_matrix._day_rows()}
        check("HL Excel supported (excel) + HL PDF supported (pdf)",
              rows["highway_log"][3] == "excel" and rows["highway_log"][4]
              and rows["highway_log_pdf"][3] == "pdf" and rows["highway_log_pdf"][4])
        check("ramp_summary / ramp_detail / highway_sequence greyed (unsupported)",
              not rows["ramp_summary"][4] and not rows["ramp_detail"][4]
              and not rows["highway_sequence"][4])
        check("available days for ssor-prod (newest first, both HL days)",
              day_matrix.available_days("ssor-prod") == ["2026-06-18", "2026-06-17"])
        check("available days for ars-prod scoped to that source",
              day_matrix.available_days("ars-prod") == ["2026-06-17"])
        check("available days for an export-less source is empty",
              day_matrix.available_days("ars-dev") == [])

        print("day_matrix snapshot — cells, greyed rows, TSN source:")
        snap = day_matrix.day_matrix_snapshot(
            "ssor-prod", ["2026-06-17", "2026-06-18"], dest=str(dest))
        check("source + day columns recorded",
              snap["source"] == "ssor-prod" and snap["days"] == ["2026-06-17", "2026-06-18"])
        check("TSN source resolves to the shared consolidated workbook",
              snap["tsn_meta"]["source_kind"] == "consolidated")
        hl = snap["cells"]["highway_log"]["2026-06-17"]
        check("HL Excel cell: export present, comparable, not built",
              hl["export"]["present"] and hl["cmp"]["supported"]
              and hl["cmp"]["missing_side"] is None and not hl["cmp"]["built"])
        pdfcell = snap["cells"]["highway_log_pdf"]["2026-06-17"]
        check("HL PDF cell for a day with no PDF export -> missing cell side",
              pdfcell["cmp"]["missing_side"] == "cell")
        greyed = snap["cells"]["ramp_summary"]["2026-06-17"]
        check("greyed row cell -> supported False", greyed["cmp"].get("supported") is False)

        # Without a TSN dataset the supported cells read 'needs TSN'.
        snap_notsn = day_matrix.day_matrix_snapshot(
            "ssor-prod", ["2026-06-17"], dest=str(tempfile.mkdtemp(prefix="tsmis_day_notsn_")))
        check("no TSN dataset -> supported cell missing the tsn side",
              snap_notsn["cells"]["highway_log"]["2026-06-17"]["cmp"]["missing_side"] == "tsn")

        print("day_matrix scoped rebuild list:")
        todo = day_matrix.cells_to_rebuild(snap, scope="all")
        check("all-scope includes the ready HL Excel cells",
              ("2026-06-17", "highway_log") in todo
              and ("2026-06-18", "highway_log") in todo)
        check("excludes greyed rows + missing sides",
              all(rk not in ("ramp_summary", "ramp_detail", "highway_sequence")
                  for _d, rk in todo)
              and ("2026-06-17", "highway_log_pdf") not in todo)
        check("row filter scopes to one report",
              all(rk == "highway_log"
                  for _d, rk in day_matrix.cells_to_rebuild(snap, "all", row="highway_log")))
        check("date filter scopes to one day",
              all(d == "2026-06-18"
                  for d, _rk in day_matrix.cells_to_rebuild(snap, "all", date="2026-06-18")))

        print("build_day_cell guard paths:")
        check("unknown row raises",
              _raises(lambda: day_matrix.build_day_cell("ssor-prod", "2026-06-17", "nope",
                                                        str(dest), None)))
        check("greyed row raises",
              _raises(lambda: day_matrix.build_day_cell("ssor-prod", "2026-06-17",
                                                        "ramp_summary", str(dest), None)))
        notsn = tempfile.mkdtemp(prefix="tsmis_day_notsn2_")
        check("no TSN workbook raises",
              _raises(lambda: day_matrix.build_day_cell("ssor-prod", "2026-06-17",
                                                        "highway_log", notsn, None)))

        print("gui_api bridge — source/day/report validation + enqueue:")
        a = gui_api.GuiApi()
        info = a.day_matrix_info()
        check("day_matrix_info carries available_days + sources",
              "available_days" in info and len(info["sources"]) == 6)
        check("unknown source rejected", bool(a.set_day_matrix_source("zz-zz").get("error")))
        check("valid source set", a.set_day_matrix_source("ssor-prod").get("ok"))
        check("add a day with no export rejected",
              bool(a.add_day_matrix_day("2099-01-01").get("error")))
        check("add a real day", a.add_day_matrix_day("2026-06-17").get("ok")
              and "2026-06-17" in settings.get_day_matrix_days())
        a.add_day_matrix_day("2026-06-18")
        check("hide unknown report rejected",
              bool(a.set_day_matrix_report("nope", False).get("error")))
        check("hide a report row ok",
              a.set_day_matrix_report("ramp_summary", False).get("ok"))
        a.set_day_matrix_report("ramp_summary", True)

        print("gui_api bridge — build/rebuild onto the shared queue:")
        check("build greyed report rejected",
              bool(a.build_day_cell("ramp_summary", "2026-06-17").get("error")))
        check("build a not-added day rejected",
              bool(a.build_day_cell("highway_log", "2026-06-30").get("error")))
        bc = a.build_day_cell("highway_log", "2026-06-17")
        check("build a supported day cell -> launched as a 'matrix' task",
              bc.get("ok") is True and a._task == "matrix")
        check("the day worker (not the env worker) was used",
              isinstance(_FakeWorker.last, tuple))
        # A second action queues behind it (shared queue with the Everything matrix).
        q = a.build_day_cell("highway_log", "2026-06-18")
        check("second day action queues", q.get("ok") is True
              and len(a._state_snapshot()["matrix_queue"]) == 1)
        a._end_task()
        check("auto-advanced the queued day job", a._task == "matrix")
        a._end_task()
        check("queue drained -> idle", a._task is None)
        # Clear day columns -> rebuild finds nothing.
        settings.set_day_matrix_days([])
        check("rebuild with no day columns -> nothing",
              a.rebuild_day_matrix("all").get("nothing") is True and a._task is None)
        settings.set_day_matrix_days(["2026-06-17", "2026-06-18"])
        rb = a.rebuild_day_matrix("all")
        check("rebuild-all over real days -> launched", rb.get("ok") and a._task == "matrix")
        a._end_task()

        print("gui_api bridge — open guards:")
        opened = []
        a._open_file = lambda p: opened.append(Path(p))
        a._open_folder = lambda p: opened.append(Path(p))
        check("open a never-built cell errors",
              bool(a.open_day_cell_comparison("highway_log", "2026-06-17").get("error")))
        _touch(day_matrix.day_out_path("2026-06-17", "ssor-prod", "highway_log"))
        check("open succeeds once the workbook exists",
              a.open_day_cell_comparison("highway_log", "2026-06-17").get("ok") is True)
        check("open by-day folder ok",
              a.open_day_comparisons_folder().get("ok") is True
              and opened[-1] == day_matrix.byday_root())
    finally:
        (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT, gui_api.DayMatrixCompareWorker,
         gui_api.MatrixCompareWorker, settings.get_batch_dest, settings.CONFIG_FILE) = saved
        settings._cache = settings._cache_mtime = None
        for d in (out, dest, cfgdir):
            shutil.rmtree(d, ignore_errors=True)

    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL DAY-MATRIX CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
