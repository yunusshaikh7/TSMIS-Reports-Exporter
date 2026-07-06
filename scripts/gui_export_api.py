"""GuiExportMixin — extracted verbatim from gui_api.GuiApi (S1 / ARC-02, v0.19.0):
route parsing/preview, the single-export flow, and the Export Everything
batch (start/cancel/skip/pause, fast mode, preview shots).
Composition only — every `self._*` it touches lives on GuiApi.
"""
import logging
from pathlib import Path

import webview

import batch_manifest
import outcome
import report_library
import settings
import contract
from common import DATA_SOURCES, ENVIRONMENTS, ROUTES, parse_routes
from exporter_parallel import MAX_WORKERS, default_worker_count
from gui_endpoint import _api_method, pick_path   # + the dialog unwrap
from gui_worker import BatchWorker, ExportWorker
from paths import OUTPUT_ROOT
from reports import enabled_export_reports, resolve_export_keys

ui_log = logging.getLogger("tsmis.ui")


class GuiExportMixin:
    # ---- routes ---------------------------------------------------------------

    @_api_method
    def parse_routes_preview(self, raw):
        try:
            chosen = parse_routes(raw)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "count": len(chosen), "routes": chosen}

    # ---- export ----------------------------------------------------------------

    @_api_method
    def start_export(self, report_keys, routes_text, fast, workers,
                     auto_consolidate=False):
        # Validate inputs BEFORE claiming the task slot (pure, no shared state),
        # then claim atomically -- so two quick clicks can't both pass the gate
        # and launch two export runs (the old check-then-set raced). Selection is
        # by stable export-op KEY now (P3 / §C.5), resolved ALL-OR-NOTHING: any
        # unknown/disabled/duplicate key rejects the whole selection (never a
        # narrower run), never mis-resolved by list position.
        specs, invalid = resolve_export_keys(
            report_keys if isinstance(report_keys, (list, tuple)) else [])
        if invalid:
            return {"error": "One or more selected reports aren't available — "
                             "reopen the tab and pick again."}
        if not specs:
            return {"error": "Tick at least one report to export."}
        raw = (routes_text or "").strip()
        if raw:
            try:
                run_routes = parse_routes(raw)
            except ValueError as e:
                return {"error": f"{e}\n\nExample: 5, 99, 101"}
        else:
            run_routes = list(ROUTES)
        n_workers = 1
        if fast:
            try:
                n_workers = max(2, min(int(workers), MAX_WORKERS))
            except (TypeError, ValueError):
                n_workers = max(2, default_worker_count())

        err = self._claim_task_error("export")
        if err:
            return err
        with self._lock:
            self._fast_run = n_workers > 1
            self._last_summary = None       # the previous run's card clears now
            self._last_run_folder = None
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()

        names = ", ".join(s.label for s in specs)
        msg = f"Starting export: {names}"
        if len(run_routes) != len(ROUTES):
            msg += f"   ·   {len(run_routes)} routes"
        if n_workers > 1:
            msg += f"   ·   FAST MODE ({n_workers} browsers)"
        if auto_consolidate:
            msg += "   ·   auto-consolidate"
        self._emit_log(msg)
        self._set_dot("busy",
                      f"Exporting {len(specs)} report(s)…" if len(specs) > 1
                      else f"Exporting {specs[0].label}…")
        # `workers` tells the UI how many live browser-status rows to show.
        self._emit({"t": "run_started", "mode": "export", "label": "Working…",
                    "workers": n_workers})
        self._push_state()
        worker = ExportWorker(specs, self._gated_queue(), self.cancel_event, self.skip_event,
                              workers=n_workers, routes=run_routes,
                              pause_event=self.pause_event,
                              auto_consolidate=bool(auto_consolidate))
        with self._lock:
            self._export_worker = worker
        worker.start()
        return {"ok": True}

    @_api_method
    def retry_failed(self):
        """Re-run only the routes that FAILED in the last export. Reuses the
        normal export engine (resume skips routes already saved, so only the
        genuinely-missing ones are re-pulled). Serial (workers=1) so it works
        without a saved login, mirroring the engine's own end-of-run retry."""
        with self._lock:
            results = list(self._last_results or [])
        failing = [(spec, list(result.failed)) for spec, result in results if result.failed]
        if not failing:
            return {"error": "There are no failed routes to retry."}
        specs = [spec for spec, _ in failing]
        # The union of every failing report's failed routes, run against all of
        # them. Almost always one report (single-report runs are the norm); when
        # several reports failed DIFFERENT routes, resume idempotency means each
        # report re-pulls only its own still-missing files and skips the rest —
        # so the retry stays complete without the engine needing per-spec lists.
        routes = sorted({r for _, fr in failing for r in fr})

        err = self._claim_task_error("export")
        if err:
            return err
        with self._lock:
            self._fast_run = False
            self._last_summary = None
            self._last_run_folder = None
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()
        self._emit_log(f"Retrying {len(routes)} failed route(s): {', '.join(routes)}")
        self._set_dot("busy", "Retrying failed routes…")
        self._emit({"t": "run_started", "mode": "export",
                    "label": "Retrying failed routes…", "workers": 1})
        self._push_state()
        worker = ExportWorker(specs, self._gated_queue(), self.cancel_event, self.skip_event,
                              workers=1, routes=routes, pause_event=self.pause_event)
        with self._lock:
            self._export_worker = worker
        worker.start()
        return {"ok": True}

    @_api_method
    def open_run_folder(self):
        """Open the output folder of the run that just finished (the dated
        run-folder root). The path is engine-produced under OUTPUT_ROOT, so no
        extra validation is needed."""
        with self._lock:
            folder = self._last_run_folder
        if not folder:
            return {"error": "No recent run to open."}
        self._open_folder(Path(folder))
        return {"ok": True}

    # ---- batch: Export Everything (B3) ----------------------------------------

    @staticmethod
    def _parse_env_keys(env_keys):
        """Validate JS-supplied 'src-env' keys into ordered, de-duped (src, env)
        combos; unknown keys are dropped."""
        out, seen = [], set()
        for k in (env_keys if isinstance(env_keys, (list, tuple)) else []):
            parts = str(k).split("-")
            if (len(parts) == 2 and parts[0] in DATA_SOURCES
                    and parts[1] in ENVIRONMENTS and (parts[0], parts[1]) not in seen):
                seen.add((parts[0], parts[1]))
                out.append((parts[0], parts[1]))
        return out

    def _pending_batch(self):
        """A resumable batch (a saved manifest with pending environments) as a
        small UI summary, or None."""
        m = batch_manifest.load()
        if m and batch_manifest.pending(m):
            return {"reports": list(m.get("reports", [])),
                    "pending": len(batch_manifest.pending(m)),
                    "total": len(m.get("steps", []))}
        return None

    @_api_method
    def start_batch_export(self, report_keys, env_keys, fast, workers,
                           auto_consolidate=False):
        """B3 Export Everything: export the selected report types across the
        selected environments, sequentially, with a persistent manifest so it can
        resume across restarts. Reports travel by stable export-op KEY (P3 / §C.5):
        the manifest persists keys, so a registry re-order can't resume the wrong
        report (F7). Resolved ALL-OR-NOTHING: any unknown/disabled/duplicate key
        rejects the whole selection (never a narrower batch)."""
        specs, invalid = resolve_export_keys(
            report_keys if isinstance(report_keys, (list, tuple)) else [])
        if invalid:
            return {"error": "One or more selected report types aren't available — "
                             "reopen the tab and pick again."}
        if not specs:
            return {"error": "Tick at least one report type to export."}
        keys = [s.subdir for s in specs]   # canonical export-op keys (validated, enabled)
        combos = self._parse_env_keys(env_keys)
        if not combos:
            return {"error": "Pick at least one environment."}
        n_workers = 1
        if fast:
            try:
                n_workers = max(2, min(int(workers), MAX_WORKERS))
            except (TypeError, ValueError):
                n_workers = max(2, default_worker_count())
        err = self._claim_task_error("batch")
        if err:
            return err
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()
        dest = settings.get_batch_dest()
        manifest = batch_manifest.build(keys, combos, bool(fast), n_workers,
                                        bool(auto_consolidate), dest=dest)
        batch_manifest.save(manifest)
        with self._lock:
            self._fast_run = n_workers > 1
            self._batch_resume = None
            self._last_summary = None     # a batch supersedes the last export card
            self._last_run_folder = None
            self._last_batch_outcome = None   # P1-B02: never reuse a prior run's outcome
        msg = (f"Starting Export Everything: {len(keys)} report type(s) "
               f"across {len(combos)} environment(s)")
        if n_workers > 1:
            msg += f"   ·   FAST MODE ({n_workers} browsers)"
        if auto_consolidate:
            msg += "   ·   auto-consolidate"
        self._emit_log(msg)
        self._emit_log(f"  Destination: {dest}")
        self._set_dot("busy", "Export Everything…")
        self._emit({"t": "run_started", "mode": "batch", "label": "Working…",
                    "workers": n_workers})
        self._push_state()
        BatchWorker(manifest, self._gated_queue(), self.cancel_event, self.skip_event,
                    self.pause_event).start()
        return {"ok": True}

    @_api_method
    def report_library_info(self):
        """The always-current destination + per-report freshness, for the
        Export Everything tab's library view (B3). Pure filesystem stat."""
        dest = settings.get_batch_dest()
        reports = [(label, spec.subdir)
                   for _i, label, _fmt, spec in enabled_export_reports()]
        return {"dest": dest, "reports": report_library.report_ages(dest, reports)}

    @_api_method
    def pick_batch_dest(self):
        """Native folder dialog to choose the always-current destination."""
        cur = settings.get_batch_dest()
        start = cur if Path(cur).is_dir() else str(OUTPUT_ROOT)
        picked = pick_path(self._window, webview.FOLDER_DIALOG, directory=start)
        if not picked:
            return {"cancelled": True}
        dest = settings.set_batch_dest(picked)
        self._emit_log(f"Export Everything destination: {dest}")
        self._push_state()
        return {"dest": dest}

    @_api_method
    def resume_batch(self):
        """Continue a saved, interrupted batch from its next pending environment."""
        m = batch_manifest.load()
        if not m or not batch_manifest.pending(m):
            return {"error": "There's no saved batch to resume."}
        err = self._claim_task_error("batch")
        if err:
            return err
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()
        with self._lock:
            self._fast_run = bool(m.get("fast"))
            self._batch_resume = None
            self._last_summary = None
            self._last_run_folder = None
            self._last_batch_outcome = None   # P1-B02: never reuse a prior run's outcome
        pend, total = len(batch_manifest.pending(m)), len(m.get("steps", []))
        self._emit_log(f"Resuming Export Everything — {pend} of {total} "
                       "environment(s) left.")
        self._set_dot("busy", "Export Everything…")
        self._emit({"t": "run_started", "mode": "batch", "label": "Working…",
                    "workers": m.get("workers", 1) if m.get("fast") else 1})
        self._push_state()
        BatchWorker(m, self._gated_queue(), self.cancel_event, self.skip_event,
                    self.pause_event).start()
        return {"ok": True}

    @_api_method
    def discard_batch(self):
        """Forget a saved, interrupted batch (the user doesn't want to resume)."""
        batch_manifest.clear()
        with self._lock:
            self._batch_resume = None
        self._emit_log("Discarded the saved Export Everything batch.")
        self._push_state()
        return {"ok": True}

    def _on_batch_progress(self, payload):
        with self._lock:
            self._batch = {"label": payload.get("label", ""),
                           "done": payload.get("done", 0),
                           "total": payload.get("total", 0),
                           "src": payload.get("src"),
                           "env": payload.get("env"),
                           "steps": payload.get("steps", [])}
        self._push_state()

    def _on_batch_done(self, payload):
        done, total = payload.get("done", 0), payload.get("total", 0)
        if payload.get("complete"):
            batch_manifest.clear()
            self._emit_log(f"Export Everything finished — all {total} "
                           "environment(s) done.")
        elif payload.get("cancelled"):
            self._emit_log(f"Export Everything stopped — {done} of {total} "
                           "environment(s) done. Re-open the app to resume the rest.")
        else:
            self._emit_log(f"Export Everything ended — {done} of {total} "
                           "environment(s) done; some were left pending (see the log).")
        # Aggregate batch outcome for run_ended (P1-B02): complete only when every
        # environment finished; else partial (some kept last-good) / cancelled.
        bcompletion = payload.get("completion") or (
            outcome.COMPLETE if payload.get("complete")
            else outcome.CANCELLED if payload.get("cancelled") else outcome.PARTIAL)
        bartifact = (outcome.PROMOTED if bcompletion == outcome.COMPLETE
                     else outcome.PREVIOUS_PRESERVED)
        resume = self._pending_batch()        # recompute outside the lock
        with self._lock:
            self._batch = None
            self._batch_resume = resume
            self._last_batch_outcome = {"completion": bcompletion, "artifact": bartifact}
        self._flash_taskbar()
        self._end_task()

    @_api_method
    def request_preview(self, worker_no):
        """Ask browser `worker_no` (1-based) for a live screenshot; it answers
        with a 'preview' event at its next safe poll point (≤ ~5 s during a
        report wait; a long download can delay it until the next route)."""
        with self._lock:
            worker = self._export_worker
            running = self._task == "export" or (
                self._task == "matrix" and self._current_job is not None
                and self._current_job.get("kind") == "export")
        if not running or worker is None:
            return {"error": "No export is running."}
        worker.request_screenshot(worker_no)
        ui_log.info("preview requested for browser %s", worker_no)
        return {"ok": True}

    def _matrix_export_running(self):
        """True while a matrix re-EXPORT job is the running task. Pause/Skip + live
        preview apply to it exactly like a normal export — MatrixBatchExportWorker
        forwards pause_event/skip_event to the underlying ExportWorker."""
        with self._lock:
            return (self._task == "matrix" and self._current_job is not None
                    and self._current_job.get("kind") == "export")

    @_api_method
    def skip_route(self):
        # Read+set under the lock: the unlocked pair could race _end_task + the
        # matrix queue advance and stamp the NEXT job with a skip meant for the
        # one that just ended (BUG-10). The queue advance clears the control
        # events under its claim, so a stale set can no longer leak forward.
        with self._lock:
            hit = self._task == "export" or self._matrix_export_running()
            if hit:
                self.skip_event.set()
        if hit:
            self._emit_log("Skip requested — will move on once the current wait ends.")
        return {"ok": True}

    @_api_method
    def cancel_run(self):
        # contract.CANCELLABLE is the ONE home of the cancellable-kind list (E2).
        # Read+set under the lock (BUG-10): unlocked, this could race _end_task
        # and the matrix queue advance, cancelling the NEXT queued job instead of
        # the one the user targeted.
        with self._lock:
            task = self._task
            if task in contract.CANCELLABLE:
                self.cancel_event.set()
                self.pause_event.clear()  # unblock a paused run so cancel lands
        if task in contract.CANCELLABLE:
            self._emit_log("Cancel requested…")
        elif task == "envcheck":
            self._emit_log("The environment check can't be stopped partway — "
                           "it'll finish in a moment.")
        return {"ok": True}

    @_api_method
    def pause_or_resume(self):
        """Toggle a between-routes hold on the running export (B1). The current
        route(s) finish, then the run holds until Resume. Unlike Skip, pause is
        well-defined in fast mode (every browser parks before its next route), so
        it works there too. Also pauses an Export Everything batch (between
        routes, and between environments) and a matrix re-export. No-op unless one
        is running."""
        # Toggle under the lock (BUG-10): matches _end_task's locked
        # pause_event.clear(), so a toggle can't interleave a run transition.
        with self._lock:
            if (self._task not in ("export", "batch")
                    and not self._matrix_export_running()):
                return {"error": "No export is running."}
            resumed = self.pause_event.is_set()
            if resumed:
                self.pause_event.clear()
            else:
                self.pause_event.set()
        if resumed:
            self._emit_log("Resumed.")
        else:
            self._emit_log("Paused — finishing the current route(s), then holding. "
                           "Click Resume to continue.")
        self._push_state()
        return {"ok": True}
