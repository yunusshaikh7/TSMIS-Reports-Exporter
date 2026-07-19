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
import gui_matrix
import matrix
import paths
import settings
from openpyxl import Workbook

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


def test_newest_mtime_survives_a_bad_entry():
    """One transiently-locked/vanished file must not abort the whole mtime fold
    (it used to mark the day's export 'not present'). Simulated by swapping
    day_matrix.Path for a stub whose second entry raises OSError on stat."""
    good = Path(tempfile.mkdtemp(prefix="tsmis_day_mt_")) / "r001.xlsx"
    _touch(good)

    class _BadEntry:
        name = "r002.xlsx"
        def is_file(self):
            raise OSError("locked / vanished mid-scan")

    class _FakeDir:
        def __init__(self, _p):
            pass
        def iterdir(self):
            return [good, _BadEntry()]

    saved = day_matrix.Path
    day_matrix.Path = _FakeDir
    try:
        got = day_matrix._folder_newest_mtime("ignored")
    finally:
        day_matrix.Path = saved
    check("a locked entry doesn't abort the fold (good file's mtime returned)",
          got == good.stat().st_mtime)


def test_092_folder_identity_and_calendar():
    print("CMP-AUD-092: calendar-valid dates + real (legacy-aware) folder identity:")
    check("valid_calendar_date rejects impossible month/day",
          not paths.valid_calendar_date("2026-99-99")
          and not paths.valid_calendar_date("2026-02-31"))
    check("valid_calendar_date accepts a real date, rejects non-canonical spelling",
          paths.valid_calendar_date("2026-07-09")
          and not paths.valid_calendar_date("2026-7-9"))
    check("parse_run_folder rejects an impossible-date run folder",
          paths.parse_run_folder("2026-99-99 ssor-prod") is None
          and paths.parse_run_folder("2026-07-09 ars-prod") == ("2026-07-09", "ars", "prod"))
    out = Path(tempfile.mkdtemp(prefix="tsmis_day092_"))
    saved = (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT)
    paths.OUTPUT_ROOT = day_matrix.OUTPUT_ROOT = out
    try:
        # A LEGACY pre-v0.10 bare-date export (no '<src>-<env>' suffix, meant ssor-prod).
        _touch(out / "2025-12-31" / "highway_log" / "r1.xlsx")
        check("legacy bare-date export is discovered as an available day",
              "2025-12-31" in day_matrix.available_days("ssor-prod"))
        check("day_source_dir resolves the legacy bare folder, not '<date> ssor-prod'",
              day_matrix.tsmis_dir("2025-12-31", "ssor-prod", "highway_log")
              == out / "2025-12-31" / "highway_log")
        check("...so the legacy day's export reads PRESENT (not 0/N)",
              day_matrix._folder_newest_mtime(
                  day_matrix.tsmis_dir("2025-12-31", "ssor-prod", "highway_log")) is not None)
        # A suffixed folder WINS deterministically when both share a date.
        _touch(out / "2025-12-30 ssor-prod" / "highway_log" / "s.xlsx")
        _touch(out / "2025-12-30" / "highway_log" / "legacy.xlsx")
        check("suffixed folder wins when a legacy + suffixed share a date",
              day_matrix.tsmis_dir("2025-12-30", "ssor-prod", "highway_log")
              == out / "2025-12-30 ssor-prod" / "highway_log")
        # An impossible-date folder on disk is never offered.
        _touch(out / "2026-99-99 ssor-prod" / "highway_log" / "x.xlsx")
        check("an impossible-date folder is not offered as an available day",
              "2026-99-99" not in day_matrix.available_days("ssor-prod"))
    finally:
        paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT = saved
        shutil.rmtree(out, ignore_errors=True)


def test_093_badge_actionable():
    print("CMP-AUD-093: day-consolidation badge is actionable only when the refresh can act:")
    out = Path(tempfile.mkdtemp(prefix="tsmis_day093_out_"))
    dest = Path(tempfile.mkdtemp(prefix="tsmis_day093_dest_"))
    saved = (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT, paths.TSN_LIBRARY_ROOT)
    paths.OUTPUT_ROOT = day_matrix.OUTPUT_ROOT = out
    paths.TSN_LIBRARY_ROOT = out / "_lib"        # hermetic: no real library leaks in
    try:
        # A day whose only export is a report with NO ready TSN dataset — the forced
        # rebuild would select zero cells, so the badge must not offer the action.
        _touch(out / "2026-05-01 ssor-prod" / "ramp_detail" / "r.xlsx")
        dc1 = day_matrix.day_matrix_snapshot(
            "ssor-prod", ["2026-05-01"], dest=str(dest))["day_consolidated"]["2026-05-01"]
        check("no ready TSN -> badge NOT actionable (the action would no-op)",
              dc1.get("actionable") is False)
        # Give highway_log a TSN dataset + an export -> the badge becomes actionable.
        _touch(matrix.tsn_input_root(dest, "highway_log") / "tsn.xlsx")
        _touch(out / "2026-05-02 ssor-prod" / "highway_log" / "r.xlsx")
        dc2 = day_matrix.day_matrix_snapshot(
            "ssor-prod", ["2026-05-02"], dest=str(dest))["day_consolidated"]["2026-05-02"]
        check("a TSN-ready export makes the badge actionable",
              dc2.get("actionable") is True)
    finally:
        paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT, paths.TSN_LIBRARY_ROOT = saved
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(dest, ignore_errors=True)


def main():
    test_newest_mtime_survives_a_bad_entry()
    test_092_folder_identity_and_calendar()
    test_093_badge_actionable()
    out = Path(tempfile.mkdtemp(prefix="tsmis_day_out_"))
    dest = Path(tempfile.mkdtemp(prefix="tsmis_day_dest_"))
    cfgdir = Path(tempfile.mkdtemp(prefix="tsmis_day_cfg_"))
    # The matrix workers now live in gui_matrix (P7c) — patch them where the mixin
    # dispatch resolves them. TSN_LIBRARY_ROOT is sandboxed too (HERMETIC): the
    # per-row TSN resolution consults the canonical library, and a dev PC whose
    # real tsn_library/<report>/raw is stocked (the Highway Log district prints
    # double as its evidence source) would otherwise flip these fixtures' staged
    # legacy-drop "consolidated" source to "pdfs".
    saved = (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT, gui_matrix.DayMatrixCompareWorker,
             gui_matrix.MatrixCompareWorker, settings.get_batch_dest, settings.CONFIG_FILE,
             paths.TSN_LIBRARY_ROOT)
    paths.OUTPUT_ROOT = out
    day_matrix.OUTPUT_ROOT = out
    paths.TSN_LIBRARY_ROOT = out / "_lib"
    gui_matrix.DayMatrixCompareWorker = _FakeWorker
    gui_matrix.MatrixCompareWorker = _FakeWorker
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
        check("every report row supported (v0.17.0 — ramp_detail/ramp_summary/highway_sequence)",
              rows["ramp_detail"][4] and rows["ramp_summary"][4]
              and rows["highway_sequence"][4])
        _today = day_matrix.today_str()
        check("available days for ssor-prod (today first, then both HL days)",
              day_matrix.available_days("ssor-prod") == [_today, "2026-06-18", "2026-06-17"])
        check("available days for ars-prod scoped to that source (+ today)",
              day_matrix.available_days("ars-prod") == [_today, "2026-06-17"])
        check("an export-less source still offers TODAY (W3: the matrix exports "
              "into today itself)",
              day_matrix.available_days("ars-dev") == [_today])
        # W3: a TODAY column with NO export renders every cell export-absent (so
        # the UI hides Build and shows only the Export action) — the snapshot
        # must not choke on the not-yet-exported day.
        snap_today = day_matrix.day_matrix_snapshot("ssor-prod", [_today], dest=str(dest),
                                                    today=_today)
        tcell = snap_today["cells"]["highway_log"][_today]
        check("export-less today: cell renders export-absent, comparison unbuilt",
              tcell["export"]["present"] is False and tcell["cmp"]["built"] is False)
        check("export-less today: it IS the exportable column (today == the column)",
              snap_today["today"] == _today and snap_today["days"] == [_today])

        print("day_matrix snapshot — cells, greyed rows, TSN source:")
        snap = day_matrix.day_matrix_snapshot(
            "ssor-prod", ["2026-06-17", "2026-06-18"], dest=str(dest))
        check("source + day columns recorded",
              snap["source"] == "ssor-prod" and snap["days"] == ["2026-06-17", "2026-06-18"])
        check("TSN source is PER-ROW (not a single shared dataset)",
              isinstance(snap["tsn_meta"].get("highway_log"), dict)
              and "source_kind" in snap["tsn_meta"]["highway_log"])
        check("Highway Log's TSN row resolves to its consolidated workbook",
              snap["tsn_meta"]["highway_log"]["source_kind"] == "consolidated")
        missing_pick = str(dest / "deleted-explicit.xlsx")
        missing_snap = day_matrix.day_matrix_snapshot(
            "ssor-prod", ["2026-06-17"], dest=str(dest),
            tsn_files={"highway_log": missing_pick})
        missing_meta = missing_snap["tsn_meta"]["highway_log"]
        check("deleted explicit TSN pick stays visible and fail-closed by day",
              missing_meta["source_kind"] == "missing_explicit"
              and missing_meta.get("selection_missing") is True
              and missing_meta.get("selected_path") == missing_pick
              and missing_snap["cells"]["highway_log"]["2026-06-17"]["cmp"]
                  ["missing_side"] == "tsn"
              and not day_matrix.cells_to_rebuild(missing_snap, scope="all"))
        pdf_to_tsn = {
            "highway_log_pdf": "highway_log",
            "intersection_detail_pdf": "intersection_detail",
            "highway_detail_pdf": "highway_detail",
            "highway_sequence_pdf": "highway_sequence",
            "ramp_detail_pdf": "ramp_detail",
        }
        shared_missing = {}
        for base in set(pdf_to_tsn.values()):
            shared_missing[base] = {
                "version": 1, "path": str(dest / f"deleted-{base}.xlsx"),
                "identity": {"sha256": "0" * 64, "size": 1,
                             "mtime_ns": 1, "file_id": "1:1"},
            }
        pdf_missing_snap = day_matrix.day_matrix_snapshot(
            "ssor-prod", ["2026-06-17"], dest=str(dest),
            tsn_files=shared_missing)
        check("all five PDF rows inherit their shared missing explicit TSN state",
              all(pdf_missing_snap["tsn_meta"][pdf]["source_kind"]
                  == "missing_explicit"
                  and pdf_missing_snap["tsn_meta"][pdf]["selected_path"]
                  == shared_missing[base]["path"]
                  and pdf_missing_snap["cells"][pdf]["2026-06-17"]["cmp"]
                      ["missing_side"] in ("cell", "both")
                  for pdf, base in pdf_to_tsn.items()))
        hl = snap["cells"]["highway_log"]["2026-06-17"]
        check("HL Excel cell: export present, comparable, not built",
              hl["export"]["present"] and hl["cmp"]["supported"]
              and hl["cmp"]["missing_side"] is None and not hl["cmp"]["built"])
        pdfcell = snap["cells"]["highway_log_pdf"]["2026-06-17"]
        check("HL PDF cell for a day with no PDF export -> missing cell side",
              pdfcell["cmp"]["missing_side"] == "cell")
        hs_cell = snap["cells"]["highway_sequence"]["2026-06-17"]
        check("highway_sequence cell now supported (v0.17.0), missing its data side here",
              hs_cell["cmp"].get("supported") is True
              and hs_cell["cmp"]["missing_side"] is not None)

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
        check("excludes not-ready rows (no export/TSN here) + missing sides",
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
        check("supported row with no export/TSN raises",
              _raises(lambda: day_matrix.build_day_cell("ssor-prod", "2026-06-17",
                                                        "highway_sequence", str(dest), None)))
        notsn = tempfile.mkdtemp(prefix="tsmis_day_notsn2_")
        check("no TSN workbook raises",
              _raises(lambda: day_matrix.build_day_cell("ssor-prod", "2026-06-17",
                                                        "highway_log", notsn, None)))
        try:
            day_matrix.build_day_cell(
                "ssor-prod", "2026-06-17", "highway_log", str(dest), None,
                tsn_files={"highway_log": str(dest / "deleted-explicit.xlsx")})
            missing_msg = ""
        except ValueError as e:
            missing_msg = str(e)
        check("day build names missing explicit selection and recovery actions",
              "selected TSN" in missing_msg and "re-pick" in missing_msg.lower()
              and "clear" in missing_msg.lower())

        print("gui_api bridge — source/day/report validation + enqueue:")
        a = gui_api.GuiApi()
        info = a.day_matrix_info()
        check("day_matrix_info carries available_days + sources",
              "available_days" in info and len(info["sources"]) == 6)
        picked = dest / "picked-shared-tsn.xlsx"
        wb = Workbook(); wb.active["A1"] = "TSN"; wb.save(picked); wb.close()
        picked_res = a.set_matrix_tsn_file("highway_log_pdf", str(picked))
        saved_selection = settings.get_matrix_tsn_selections()
        check("bridge canonicalizes a PDF-row pick and persists its verified identity",
              picked_res.get("ok") is True
              and set(saved_selection) == {"highway_log"}
              and saved_selection["highway_log"].get("version") == 1
              and saved_selection["highway_log"]["identity"].get("sha256"))
        bad = dest / "bad.xlsx"; bad.write_bytes(b"not a workbook")
        check("bridge rejects an unreadable/non-workbook explicit .xlsx",
              bool(a.set_matrix_tsn_file("highway_log", str(bad)).get("error")))
        check("bridge rejects a malformed non-path picker payload cleanly",
              bool(a.set_matrix_tsn_file("highway_log", []).get("error")))
        a.set_matrix_tsn_file("highway_log_pdf", "")
        check("clearing through a PDF alias clears the canonical shared selection",
              "highway_log" not in settings.get_matrix_tsn_selections())
        settings.set_matrix_tsn_file("highway_log_pdf", str(dest / "legacy.xlsx"))
        a.day_matrix_info()                       # normal snapshot boundary performs migration
        migrated = settings.get_matrix_tsn_selections()
        check("legacy PDF-keyed config migrates to one blocked base-key record",
              "highway_log_pdf" not in migrated
              and migrated.get("highway_log", {}).get("version") == 0)
        a.set_matrix_tsn_file("highway_log", "")
        check("unknown source rejected", bool(a.set_day_matrix_source("zz-zz").get("error")))
        check("valid source set", a.set_day_matrix_source("ssor-prod").get("ok"))
        check("add a day with no export rejected",
              bool(a.add_day_matrix_day("2099-01-01").get("error")))
        check("add a real day", a.add_day_matrix_day("2026-06-17").get("ok")
              and "2026-06-17" in settings.get_day_matrix_days())
        a.add_day_matrix_day("2026-06-18")
        # CMP-AUD-095: switching source reconciles retained day columns to the NEW
        # source (ars-prod has 2026-06-17 but not 2026-06-18).
        a.set_day_matrix_source("ars-prod")
        check("source switch drops a day absent under the new source",
              "2026-06-18" not in settings.get_day_matrix_days())
        check("source switch keeps a day present under the new source",
              "2026-06-17" in settings.get_day_matrix_days())
        a.set_day_matrix_source("ssor-prod")             # restore for downstream
        settings.set_day_matrix_days(["2026-06-17", "2026-06-18"])
        # CMP-AUD-094: a day with a live export/compare can't be removed (removal
        # would strand the chained comparison — for day jobs `env` holds the date).
        a._coord.current_job = a._make_job("export", "column", "x",
                                           env="2026-06-17", which="day")
        check("remove refuses a day with a running by-day job",
              bool(a.remove_day_matrix_day("2026-06-17").get("error"))
              and "2026-06-17" in settings.get_day_matrix_days())
        check("remove of a different, idle day still works",
              a.remove_day_matrix_day("2026-06-18").get("ok")
              and "2026-06-18" not in settings.get_day_matrix_days())
        a._coord.current_job = None                      # clear the seeded job
        settings.set_day_matrix_days(["2026-06-17", "2026-06-18"])   # restore
        check("hide unknown report rejected",
              bool(a.set_day_matrix_report("nope", False).get("error")))
        check("hide a report row ok",
              a.set_day_matrix_report("ramp_summary", False).get("ok"))
        a.set_day_matrix_report("ramp_summary", True)

        print("gui_api bridge — build/rebuild onto the shared queue:")
        check("build unknown report rejected",
              bool(a.build_day_cell("nope", "2026-06-17").get("error")))
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
        # CMP-AUD-096: a supplied-but-invalid row/date is REJECTED, never silently
        # normalized to None (which the endpoint reads as "no filter" -> a
        # whole-matrix rebuild). Days 2026-06-17/18 are the only valid columns.
        check("rebuild_day_matrix rejects a supplied-but-invalid row (CMP-AUD-096)",
              bool(a.rebuild_day_matrix("all", row="nope").get("error")))
        check("rebuild_day_matrix rejects an impossible date (CMP-AUD-096)",
              bool(a.rebuild_day_matrix("all", date="2026-99-99").get("error")))
        check("rebuild_day_matrix stays idle after a rejected scope", a._task is None)
        # CMP-AUD-093: a FORCED consolidate with zero comparable cells (no TSN)
        # short-circuits to 'nothing' instead of enqueuing a job that drains
        # silently. Remove the only TSN dataset to make every cell non-comparable.
        (matrix.tsn_input_root(dest, "highway_log") / "tsn.xlsx").unlink()
        check("forced re-consolidate with no comparable cell -> nothing, not a silent no-op",
              a.rebuild_day_matrix("all", None, "2026-06-17", True).get("nothing") is True
              and a._task is None)
        _touch(matrix.tsn_input_root(dest, "highway_log") / "tsn.xlsx")   # restore

        print("gui_api bridge — by-day EXPORT (today only) + export->compare chain:")
        today = paths.today_str()
        _touch(out / f"{today} ssor-prod" / "highway_log" / "r1.xlsx")   # today's HL pull
        saved_mbe = gui_matrix.MatrixBatchExportWorker
        gui_matrix.MatrixBatchExportWorker = _FakeWorker
        try:
            settings.set_day_matrix_days([])
            check("snapshot exposes today (the one exportable column)",
                  a._day_matrix_snapshot().get("today") == today)
            check("exporting a PAST day cell is rejected (its pull is preserved)",
                  bool(a.export_day_cell("highway_log", "2026-06-17").get("error")))
            r = a.export_day_column()
            check("export_day_column -> which=day export task on the DATED worker",
                  r.get("ok") is True and a._task == "matrix"
                  and a._current_job["kind"] == "export" and a._current_job["which"] == "day"
                  and isinstance(_FakeWorker.last, tuple)
                  and _FakeWorker.last[1].get("dated") is True)
            check("today auto-added as a column", today in settings.get_day_matrix_days())
            # one (spec, src, env) step per visible supported report
            steps = a._resolve_day_export_steps(a._current_job)
            check("column export = one step per visible supported report",
                  len(steps) >= 5 and all(len(s) == 3 for s in steps))
            a._on_matrix_export_done({"count": 7, "total": 7, "ok": True, "cancelled": False})
            check("a finished export auto-chains a by-day COMPARE (fills the column)",
                  a._current_job is not None and a._current_job["kind"] == "compare"
                  and a._current_job.get("which") == "day")
            a._end_task()
            a.export_day_column()
            a._on_matrix_export_done({"count": 0, "total": 7, "ok": False, "cancelled": True})
            check("a CANCELLED export does NOT chain a compare",
                  a._current_job is None or a._current_job["kind"] != "compare")
            a._end_task()
        finally:
            gui_matrix.MatrixBatchExportWorker = saved_mbe
        settings.set_day_matrix_days(["2026-06-17", "2026-06-18"])   # restore for open guards

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
        (paths.OUTPUT_ROOT, day_matrix.OUTPUT_ROOT, gui_matrix.DayMatrixCompareWorker,
         gui_matrix.MatrixCompareWorker, settings.get_batch_dest, settings.CONFIG_FILE,
         paths.TSN_LIBRARY_ROOT) = saved
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
