"""Golden check for the v0.32.0 export-engine wave (owner items 1/19 + 20).

Two behaviors, both driven through the SHIPPED entry points with real files on
disk (no browser, no site):

  * DATED per-route filenames — a dated run folder's per-route files carry the
    run identity front-anchored ('2026-07-23 ssor-prod highway_log_route_3.pdf',
    paths.resolve_route_file). The RESUME HAZARD is the heart of it: a pre-v0.32
    partial run holds legacy dateless names, and a resumed run must SKIP those
    finished routes rather than writing a second (dated) file for the same
    route — two files for one route is exactly the duplicate identity the
    consolidators refuse (CMP-AUD-050). The Everything store's env-tagged
    staging keeps its own naming (no date).

  * FAST-MODE dual-format coalescing — run_export_parallel_combined generates
    each route ONCE across N workers and saves every edition off that single
    render; ExportWorker._run_specs dispatches a coalesced group to it in fast
    mode (it used to force singleton groups); MatrixBatchExportWorker groups
    same-report edition steps per environment so one pass satisfies both cells.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_route_file_naming.py
"""
import threading
from pathlib import Path

from _checklib import Checker, patch, scripts_path, temp_dir

scripts_path()

import exporter
import exporter_parallel
import gui_worker_export as gwe
import gui_worker_matrix as gwm
import paths
from events import Events
from exporter import ReportSpec

c = Checker()

RUN_NAME = "2026-07-23 ssor-prod"
XLSX_HEAD = b"PK\x03\x04data"          # _head_is_complete: .xlsx == PK\x03\x04
PDF_HEAD = b"%PDFdata"                 # _head_is_complete: .pdf == %PDF


def _spec(subdir, ext, *, data_value="highway_log", label="Highway Log"):
    head = XLSX_HEAD if ext == "xlsx" else PDF_HEAD

    def save(_page, out_path, _timeout_ms=None):
        Path(out_path).write_bytes(head)

    return ReportSpec(
        label=label, subdir=subdir, data_value=data_value,
        filename=lambda r, _s=subdir, _e=ext: f"{_s}_route_{r}.{_e}",
        wait_js=lambda r: "() => true", is_empty=lambda _p: False, save=save)


def test_resolver():
    print("paths.resolve_route_file — dated in run folders, legacy honored:")
    with temp_dir("tsmis_rrf_") as tmp:
        run_sub = tmp / RUN_NAME / "highway_log"
        run_sub.mkdir(parents=True)
        name = "highway_log_route_3.xlsx"
        dated = run_sub / f"{RUN_NAME} {name}"
        legacy = run_sub / name
        c.check("fresh route in a dated run folder gets the DATED name",
                paths.resolve_route_file(run_sub, name) == dated)
        legacy.write_bytes(XLSX_HEAD)
        c.check("an existing legacy file is preferred (pre-v0.32 resume)",
                paths.resolve_route_file(run_sub, name) == legacy)
        dated.write_bytes(XLSX_HEAD)
        c.check("the dated spelling wins when both exist",
                paths.resolve_route_file(run_sub, name) == dated)
        store_sub = tmp / "ssor-prod" / "highway_log"          # Everything store
        store_sub.mkdir(parents=True)
        c.check("a non-run-folder parent (the store) keeps the bare name",
                paths.resolve_route_file(store_sub, name) == store_sub / name)
        stage = tmp / "ssor-prod" / "highway_log.staging"
        stage.mkdir()
        c.check("store staging keeps the bare (env-tagged-by-spec) name too",
                paths.resolve_route_file(stage, name) == stage / name)


class _FakePage:
    def wait_for_timeout(self, _ms):
        pass


class _FakeBrowser:
    def close(self):
        pass


class _FakePW:
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _engine_patches(module, gen_log):
    """The browser-layer stubs shared by the shipped-path runs. `gen_log`
    collects one entry per GENERATION so single-pass claims are countable."""
    lock = threading.Lock()

    def fake_generate(_page, _spec, route, _prefix, _events, _timeout):
        with lock:
            gen_log.append(route)
        return "ready"

    ps = [
        patch(module, "sync_playwright", lambda: _FakePW()),
        patch(module, "new_authed_browser",
              lambda _p, parallel=False: (_FakeBrowser(), None, _FakePage())),
        patch(module, "navigate_with_auth", lambda *_a, **_k: None),
        patch(module, "require_signed_in", lambda *_a, **_k: None),
        patch(module, "has_valid_auth", lambda: True),
        patch(module, "get_site", lambda: ("ssor", "prod")),
        patch(module, "get_url", lambda: "https://unit.test"),
        patch(exporter, "_generate_route", fake_generate),
        patch(exporter, "maybe_screenshot", lambda *_a, **_k: None),
    ]
    if module is exporter:
        ps += [patch(module, "require_site_params", lambda *_a, **_k: None),
               patch(module, "preflight", lambda *_a, **_k: None),
               patch(module, "auto_report_path",
                     lambda sub, site: Path(exporter.FAILURES_DIR) / f"{sub}.csv")]
    else:
        ps += [patch(module, "select_report", lambda *_a, **_k: None),
               patch(module, "_preflight_once", lambda *_a, **_k: None),
               patch(module, "auto_report_path",
                     lambda sub, site: Path(exporter.FAILURES_DIR) / f"{sub}.csv")]
    return ps


def _apply(ps):
    ctx = []
    for p in ps:
        p.__enter__()
        ctx.append(p)
    return ctx


def _exit(ctx):
    for p in reversed(ctx):
        p.__exit__(None, None, None)


def test_run_export_dated_and_resume():
    print("run_export (shipped path): dated names, resume, the CMP-AUD-050 hazard:")
    with temp_dir("tsmis_dated_") as tmp:
        out_dir = tmp / RUN_NAME / "highway_log_pdf"
        spec = _spec("highway_log_pdf", "pdf")
        gen = []
        ps = _engine_patches(exporter, gen) + [
            patch(exporter, "FAILURES_DIR", tmp / "_failures")]
        ctx = _apply(ps)
        try:
            r1 = exporter.run_export(spec, Events(), routes=["001", "002"],
                                     out_dir=out_dir)
            dated_1 = out_dir / f"{RUN_NAME} highway_log_pdf_route_001.pdf"
            c.check("fresh run writes DATED per-route filenames",
                    dated_1.is_file()
                    and (out_dir / f"{RUN_NAME} highway_log_pdf_route_002.pdf").is_file(),
                    f"files={[p.name for p in out_dir.iterdir()]}")
            c.check("both routes recorded saved", r1.saved == 2)

            gen.clear()
            r2 = exporter.run_export(spec, Events(), routes=["001", "002"],
                                     out_dir=out_dir)
            c.check("re-run resumes on the dated files (no regeneration)",
                    r2.exists == ["001", "002"] and gen == [],
                    f"exists={r2.exists} gen={gen}")

            # THE HAZARD: a pre-v0.32 partial run left LEGACY names. The resumed
            # run must skip the finished route via its legacy file and give only
            # the missing route a dated file — never two files for one route.
            legacy_dir = tmp / RUN_NAME / "highway_log"
            legacy_dir.mkdir(parents=True)
            lspec = _spec("highway_log", "xlsx")
            (legacy_dir / "highway_log_route_001.xlsx").write_bytes(XLSX_HEAD)
            gen.clear()
            r3 = exporter.run_export(lspec, Events(), routes=["001", "002"],
                                     out_dir=legacy_dir)
            files = sorted(p.name for p in legacy_dir.iterdir())
            c.check("legacy finished route is SKIPPED (exists), not re-pulled",
                    r3.exists == ["001"] and gen == ["002"],
                    f"exists={r3.exists} gen={gen}")
            c.check("exactly ONE file per route after the mixed resume "
                    "(no CMP-AUD-050 duplicate)",
                    files == [f"{RUN_NAME} highway_log_route_002.xlsx",
                              "highway_log_route_001.xlsx"],
                    f"files={files}")

            # Store-shaped destination: the bare (spec-tagged) name is untouched.
            store_dir = tmp / "ssor-prod" / "highway_log.staging"
            store_dir.mkdir(parents=True)
            exporter.run_export(lspec, Events(), routes=["003"], out_dir=store_dir)
            c.check("a store staging destination keeps undated names",
                    (store_dir / "highway_log_route_003.xlsx").is_file(),
                    f"files={[p.name for p in store_dir.iterdir()]}")
        finally:
            _exit(ctx)


def test_parallel_combined():
    print("run_export_parallel_combined: one generation per route, both editions:")
    with temp_dir("tsmis_pcomb_") as tmp:
        excel = _spec("highway_log", "xlsx")
        pdf = _spec("highway_log_pdf", "pdf")
        dirs = [tmp / RUN_NAME / "highway_log", tmp / RUN_NAME / "highway_log_pdf"]
        routes = ["001", "002", "003", "004"]
        gen = []
        statuses = []
        ev = Events(on_route=lambda r, s: statuses.append((r, s)))
        ctx = _apply(_engine_patches(exporter_parallel, gen) + [
            patch(exporter, "FAILURES_DIR", tmp / "_failures")])
        try:
            results = exporter_parallel.run_export_parallel_combined(
                [excel, pdf], ev, workers=3, routes=routes, out_dirs=dirs)
            c.check("each route generated exactly ONCE across the workers",
                    sorted(gen) == routes, f"gen={sorted(gen)}")
            missing = [r for r in routes
                       if not (dirs[0] / f"{RUN_NAME} highway_log_route_{r}.xlsx").is_file()
                       or not (dirs[1] / f"{RUN_NAME} highway_log_pdf_route_{r}.pdf").is_file()]
            c.check("both edition files exist per route, DATED", not missing,
                    f"missing={missing}")
            c.check("results return in specs order with the shared tally",
                    len(results) == 2
                    and all(r.saved == len(routes) for r in results)
                    and results[0].output_dir.endswith("highway_log")
                    and results[1].output_dir.endswith("highway_log_pdf"),
                    f"saved={[r.saved for r in results]}")
            c.check("one progress unit per route (not per edition)",
                    sorted(statuses) == [(r, "saved") for r in routes],
                    f"statuses={sorted(statuses)}")

            gen.clear()
            statuses.clear()
            again = exporter_parallel.run_export_parallel_combined(
                [excel, pdf], ev, workers=2, routes=routes, out_dirs=dirs)
            c.check("re-run resumes every route (all editions exist, no regen)",
                    gen == [] and all(sorted(r.exists) == routes for r in again),
                    f"gen={gen} exists={[sorted(r.exists) for r in again]}")
        finally:
            _exit(ctx)


def test_parallel_combined_guards():
    print("run_export_parallel_combined guards match the sequential twin:")
    excel = _spec("highway_log", "xlsx")
    mixed = _spec("ramp_detail", "xlsx", data_value="Ramp_Detail", label="Ramp Detail")

    def _raises(fn):
        try:
            fn()
            return False
        except ValueError:
            return True
        except Exception:
            return False

    c.check("a single edition is rejected",
            _raises(lambda: exporter_parallel.run_export_parallel_combined([excel])))
    c.check("a data_value mismatch is rejected",
            _raises(lambda: exporter_parallel.run_export_parallel_combined([excel, mixed])))


def test_reconcile_combined():
    print("_reconcile_unaccounted_combined: orphaned routes fail in EVERY edition:")
    from events import RunResult
    with temp_dir("tsmis_reccomb_") as tmp:
        excel = _spec("highway_log", "xlsx")
        pdf = _spec("highway_log_pdf", "pdf")
        d1, d2 = tmp / RUN_NAME / "highway_log", tmp / RUN_NAME / "highway_log_pdf"
        d1.mkdir(parents=True), d2.mkdir(parents=True)
        # Route 002 fully on disk (dated), route 003 nowhere, 001 recorded.
        (d1 / f"{RUN_NAME} highway_log_route_002.xlsx").write_bytes(XLSX_HEAD)
        (d2 / f"{RUN_NAME} highway_log_pdf_route_002.pdf").write_bytes(PDF_HEAD)
        results = [RunResult(), RunResult()]
        for r in results:
            r.saved, r.per_route = 1, [("001", "saved")]

        def targets_for(route):
            return [(excel, paths.resolve_route_file(d1, excel.filename(route))),
                    (pdf, paths.resolve_route_file(d2, pdf.filename(route)))]

        missing = exporter_parallel._reconcile_unaccounted_combined(
            ["001", "002", "003"], results, targets_for, Events(),
            cancelled=False, worker_crashed=True)
        c.check("only the truly-absent route is reconciled as failed",
                missing == ["003"]
                and all(r.failed == ["003"] for r in results), f"missing={missing}")
        c.check("a clean cancel skips reconciliation entirely",
                exporter_parallel._reconcile_unaccounted_combined(
                    ["004"], results, targets_for, Events(),
                    cancelled=True, worker_crashed=False) == [])


def test_worker_dispatch():
    print("ExportWorker._run_specs: fast mode now coalesces to the parallel-combined engine:")
    excel = _spec("highway_log", "xlsx")
    pdf = _spec("highway_log_pdf", "pdf")
    calls = []

    def fake_combined(specs, _events, *, workers=None, routes=None, out_dirs=None):
        calls.append(("combined", [s.subdir for s in specs], workers))
        from events import RunResult
        return [RunResult(output_dir="x") for _ in specs]

    import queue as _q
    ew = gwe.ExportWorker([excel, pdf], _q.Queue(), threading.Event(),
                          threading.Event(), workers=3, routes=["001"])
    with patch(exporter_parallel, "run_export_parallel_combined", fake_combined):
        ew._run_specs(ew._build_events(), [])
    c.check("a coalesced pair in FAST mode runs ONE parallel-combined pass",
            calls == [("combined", ["highway_log", "highway_log_pdf"], 3)],
            f"calls={calls}")
    c.check("the run shows one grouped report (not two singleton passes)",
            ew._report_n == 1, f"report_n={ew._report_n}")


def test_matrix_step_grouping():
    print("MatrixBatchExportWorker groups edition steps per environment:")
    excel = _spec("highway_log", "xlsx")
    pdf = _spec("highway_log_pdf", "pdf")
    ramp = _spec("ramp_detail", "xlsx", data_value="Ramp_Detail", label="Ramp Detail")
    import queue as _q
    w = gwm.MatrixBatchExportWorker(
        [(excel, "ssor", "prod"), (ramp, "ssor", "prod"), (pdf, "ssor", "prod"),
         (excel, "ars", "prod")],
        None, _q.Queue(), threading.Event(), threading.Event(), threading.Event())
    grouped = [([s.subdir for s in specs], src, env)
               for specs, src, env in w._grouped_steps()]
    c.check("same-report editions coalesce within ONE environment only",
            grouped == [(["highway_log", "highway_log_pdf"], "ssor", "prod"),
                        (["ramp_detail"], "ssor", "prod"),
                        (["highway_log"], "ars", "prod")],
            f"grouped={grouped}")


if __name__ == "__main__":
    print("v0.32.0 export engine (dated names + fast-mode coalescing):")
    test_resolver()
    test_run_export_dated_and_resume()
    test_parallel_combined()
    test_parallel_combined_guards()
    test_reconcile_combined()
    test_worker_dispatch()
    test_matrix_step_grouping()
    raise SystemExit(c.summary())
