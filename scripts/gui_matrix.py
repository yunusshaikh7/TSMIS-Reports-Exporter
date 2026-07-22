"""The GUI Matrix / by-day / TSN-library feature endpoints + dispatch machinery (P7c).

Extracted VERBATIM from `gui_api.GuiApi` as a mixin so the cohesive "comparison matrix"
responsibility lives in one module while the pywebview façade is unchanged: `GuiApi`
inherits `GuiMatrixMixin`, so every method keeps its name, signature, return shape, and
event order, and `task_coordinator` stays the single task/queue-state owner (the mixin
reaches it + the shared GUI plumbing through `self`, resolved via MRO). No behavior
change — this is a pure move (P7b-R01 / CR-001). Console-free; the engine stays in
`matrix`/`day_matrix`/`compare_core`.
"""
import collections
import logging
import webview

import baseline_matrix
import day_matrix
import matrix
import settings
from exporter_parallel import MAX_WORKERS, default_worker_count
from gui_endpoint import _api_method, pick_path, pick_paths
from gui_worker import (BaselineMatrixCompareWorker, ConsolidateWorker,
                        DayMatrixCompareWorker, MatrixBatchExportWorker,
                        MatrixCompareWorker, MatrixEvidenceWorker,
                        MatrixTsnConsolidateWorker)
from paths import TSN_LIBRARY_ROOT
from reports import EXPORT_REPORTS, matrix_rows

# `tsn_library` is imported LAZILY inside the methods that need it (it pulls pdfplumber
# via report_catalog) — kept verbatim from gui_api; never import it at module load.
log = logging.getLogger("tsmis.gui")


class GuiMatrixMixin:
    """The comparison-matrix / by-day / TSN-library half of the GUI bridge (mixed
    into GuiApi; reaches the coordinator + shared plumbing via self)."""

    # ----- comparison matrix (Everything tab) --------------------------------
    def _valid_baseline(self, key):
        return key if key in matrix.env_keys() else None

    def _current_baseline(self):
        return (self._valid_baseline(settings.get_matrix_baseline())
                or matrix.BASELINE_DEFAULT)

    @staticmethod
    def _valid_tsn_dataset_keys():
        import tsn_library
        return {tsn_library.canonical_dataset_key(
                    matrix.tsn_subdir_for(row_key, subdir, adapter))
                for row_key, _label, subdir, _idx, adapter in matrix_rows()}

    def _matrix_tsn_selections(self):
        """Canonical, identity-bearing TSN choices; migrate legacy aliases once."""
        import tsn_library
        raw = settings.get_matrix_tsn_selections()
        canonical, changed = tsn_library.canonicalize_selections(raw)
        if changed:
            settings.set_matrix_tsn_selections(canonical)
        return canonical

    def _matrix_snapshot(self, base):
        """The matrix snapshot for `base`, with the user's hidden rows/columns,
        per-row modes and TSN files applied — used by matrix_info, the
        baseline-switch pending count and recompute."""
        return matrix.matrix_snapshot(
            settings.get_batch_dest(), base,
            hidden=settings.get_matrix_hidden_reports(),
            hidden_envs=settings.get_matrix_hidden_envs(),
            row_modes=settings.get_matrix_row_modes(),
            tsn_files=self._matrix_tsn_selections(),
            row_order=settings.get_matrix_row_order(),
            env_order=settings.get_matrix_env_order())

    @_api_method
    def matrix_info(self, baseline=None):
        """The comparison-matrix snapshot for the Everything tab — a pure
        filesystem read (per-cell export + comparison freshness, cached verdict +
        discrepancy counts). `baseline` overrides the persisted one for a one-off
        view; otherwise the saved baseline (default ssor-prod) is used.

        Also re-pushes the state: the JS calls this on every entry to the tab,
        and the state carries the evidence-availability probe — so dropping the
        TSN district PDFs and returning to the tab un-greys the evidence toggle
        without a restart (v0.21.1)."""
        base = self._valid_baseline(baseline) or self._current_baseline()
        self._push_state()
        return self._matrix_snapshot(base)

    @_api_method
    def set_matrix_report(self, row_key, visible):
        """Show/hide a report ROW on the matrix (hidden rows aren't rendered or
        refreshed). Persisted as the hidden-set; at least one row must stay on."""
        keys = {r[0] for r in matrix_rows()}
        if row_key not in keys:
            return {"error": "Unknown report for the matrix."}
        hidden = set(settings.get_matrix_hidden_reports())
        if visible:
            hidden.discard(row_key)
        else:
            hidden.add(row_key)
        if len(hidden & keys) >= len(keys):
            return {"error": "Keep at least one report on the matrix."}
        settings.set_matrix_hidden_reports(sorted(hidden))
        self._push_state()
        return {"ok": True, "hidden": sorted(hidden)}

    @_api_method
    def set_matrix_row_order(self, keys):
        """Persist the drag-to-reorder ROW order for the Everything matrix. Unknown
        keys are dropped; rows missing from the list keep their natural order."""
        valid = {r[0] for r in matrix_rows()}
        clean = [k for k in (keys or []) if isinstance(k, str) and k in valid]
        settings.set_matrix_row_order(clean)
        self._push_state()
        return {"ok": True, "order": clean}

    @_api_method
    def set_matrix_env_order(self, keys):
        """Persist the drag-to-reorder ENV-column order for the Everything matrix."""
        valid = set(matrix.env_keys())
        clean = [k for k in (keys or []) if isinstance(k, str) and k in valid]
        settings.set_matrix_env_order(clean)
        self._push_state()
        return {"ok": True, "order": clean}

    @_api_method
    def set_matrix_baseline(self, baseline):
        """Persist the matrix baseline. Returns the new baseline and how many
        cells the recompute against it would (re)build (the UI confirms before
        calling recompute_matrix('stale')). CMP-AUD-099: a baseline switch only
        moves the CROSS-ENVIRONMENT cells' reference side; vs-TSN and self-check
        cells are baseline-independent, so only the now-STALE (env) cells rebuild —
        `scope='stale'` counts exactly those, never the fresh baseline-agnostic
        modes."""
        base = self._valid_baseline(baseline)
        if not base:
            return {"error": "Unknown baseline environment."}
        settings.set_matrix_baseline(base)
        self._emit_log(f"Matrix baseline set to {matrix.default_env_label(base)}.")
        pending = len(matrix.cells_to_rebuild(self._matrix_snapshot(base),
                                              scope="stale"))
        self._push_state()
        return {"baseline": base, "recompute_pending": pending}

    # ----- the matrix job queue (v0.16.0) ------------------------------------
    # Matrix actions enqueue a Job instead of claiming the gate directly; a 2nd
    # action queues rather than being rejected. The queue runs one job at a time
    # and auto-advances from _end_task. A Job's TARGETS (export steps / compare
    # cells) are resolved when it STARTS, not when it's queued — so a job reflects
    # exports finished before it. The global gate still serializes everything.
    _QUEUE_LIMIT = 50         # backstop against a stuck UI flooding the queue

    def _job_view(self, job):
        """JSON-safe summary of a Job for the snapshot (queue panel + current)."""
        return {"id": job["id"], "kind": job["kind"], "scope": job["scope"],
                "label": job["label"], "status": job.get("status", "queued"),
                "fast": bool(job.get("fast")), "which": job.get("which", "env")}

    def _matrix_row_label(self, row_key):
        return {r[0]: r[1] for r in matrix_rows()}.get(row_key, row_key)

    def _job_label(self, kind, scope, row=None, env=None):
        """Human label for the queue panel / log from a job's shape."""
        if kind == "tsn_consolidate":
            return "Consolidate TSN Highway Log PDFs"
        if kind == "evidence":
            return (f"Evidence images {self._matrix_row_label(row)} — "
                    f"{matrix.default_env_label(env)}")
        verb = "Re-export" if kind == "export" else "Rebuild"
        rl = self._matrix_row_label(row) if row else None
        el = matrix.default_env_label(env) if env else None
        if scope == "cell":
            return f"{verb} {rl} — {el}"
        if scope == "row":
            return f"{verb} {rl} — all environments"
        if scope == "column":
            return f"{verb} all reports — {el}"
        if scope == "stale":
            return "Refresh stale comparisons"
        return f"{verb} all comparisons"

    def _make_job(self, kind, scope, label, row=None, env=None, subdir=None,
                  fast=False, which="env", force=False, origin=None):
        # `which` ("env" = Everything matrix, "day" = Compare by-day matrix) lets
        # ONE queue serve both matrices; for day jobs `env` carries the date.
        # `force` rebuilds the persistent consolidated even when it looks fresh.
        # `origin` ("canonical"/"legacy") routes a tsn_consolidate job (CMP-AUD-010).
        jid = self._coord.next_seq()
        return {"id": jid, "kind": kind, "scope": scope, "label": label,
                "row": row, "env": env, "subdir": subdir, "fast": bool(fast),
                "which": which, "force": bool(force), "origin": origin,
                "status": "queued"}

    def _enqueue_matrix_job(self, job):
        """Append a Job and try to start it (or leave it queued behind the
        running one). The UI's '2nd action queues' contract lives here."""
        result = self._coord.enqueue(job)
        if result is None:
            return {"error": "The matrix queue is full — let some jobs finish "
                             "first."}
        depth, busy = result
        if busy:
            self._emit_log(f"Queued (#{depth}): {job['label']}.")
        self._push_state()
        self._try_start_next_matrix_job()
        return {"ok": True, "job_id": job["id"], "queued": depth}

    def _try_start_next_matrix_job(self):
        """Start the next queued matrix job if the gate is free. Claims the gate
        and pops the job ATOMICALLY (so a non-matrix task can't slip in between),
        then resolves targets with the gate held. A job that resolves to no work
        is dropped and the next one is tried."""
        while True:
            job = self._coord.take_next()        # atomic pop + claim "matrix"
            if job is None:                      # gate busy or queue empty
                return
            try:
                started = self._dispatch_matrix_job(job)
            except Exception as e:               # noqa: BLE001 — never leave the gate stuck
                log.exception("matrix dispatch failed for %r", job.get("label"))
                self._coord.release()
                self._emit_log(f"ERROR: couldn't start '{job['label']}': "
                               f"{type(e).__name__}: {e} (details are in the log file)")
                self._push_state()               # drained the job -> refresh the queue panel
                continue                         # drop this job, try the next
            if started:
                self._push_state()
                return
            # Nothing to do (e.g. the cells were rebuilt by an earlier job) —
            # release the gate, drop the job, and try the next one. Push so the
            # frontend stops showing the just-drained job (the queue-phantom fix):
            # without it the last push is _end_task's, taken before this pop.
            self._coord.release()
            self._emit_log(f"Skipped (nothing to do): {job['label']}.")
            self._push_state()

    def _dispatch_matrix_job(self, job):
        """Resolve a claimed job's targets and start its worker. Returns True if a
        worker was launched, False if there was no work. The gate is already held
        by _try_start_next_matrix_job."""
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()
        kind = job["kind"]
        if kind == "compare":
            return self._dispatch_compare_job(job)
        if kind == "export":
            return self._dispatch_export_job(job)
        if kind == "evidence":
            return self._dispatch_evidence_job(job)
        if kind == "tsn_consolidate":
            return self._dispatch_tsn_consolidate_job(job)
        return False

    # CMP-AUD-088: only an EXPORT re-authenticates + launches a browser. compare /
    # evidence / tsn_consolidate jobs are LOCAL workbook/PDF operations that never
    # authenticate, so an auth or browser-not-found failure must not drop them from the
    # SHARED matrix queue — only the auth-dependent exports are removed, the rest run on.
    _AUTH_DEPENDENT_MATRIX_KINDS = frozenset({"export"})

    def _matrix_job_needs_auth(self, job):
        """True iff a queued matrix job needs the auth/browser prerequisite (an export).
        The shared-queue error handler drops only these on an auth/browser failure; the
        local comparison / evidence / TSN-consolidate jobs survive and continue."""
        return (isinstance(job, dict)
                and job.get("kind") in self._AUTH_DEPENDENT_MATRIX_KINDS)

    def _resolve_compare_cells(self, job, base):
        """[(row, cell, mode)] for a compare job. A 'cell' job is the one explicit
        cell (always run); row/column/all/stale defer to the staleness-aware
        rebuild list."""
        scope = job["scope"]
        if scope == "cell":
            row, env = job["row"], job["env"]
            mode = settings.get_matrix_row_modes().get(row, "env")
            if mode == "env" and env == base:
                return []
            # CMP-AUD-103: a queued explicit cell whose input side went missing
            # after enqueue resolves to NO work (the shared buildability predicate),
            # so queue accounting can't dispatch a doomed compare.
            cmp = self._matrix_snapshot(base)["cells"].get(row, {}).get(env, {}).get("cmp")
            if not matrix.cell_buildable(cmp):
                return []
            return [(row, env, mode)]
        rebuild_scope = "stale" if scope == "stale" else "all"
        return matrix.cells_to_rebuild(self._matrix_snapshot(base),
                                       scope=rebuild_scope,
                                       row=job.get("row"), env=job.get("env"))

    def _resolve_day_cells(self, job):
        """[(date, row)] for a by-day compare job. 'cell' = the one explicit cell;
        row/column/all/stale defer to day_matrix's staleness-aware list."""
        snap = self._day_matrix_snapshot()
        scope = job["scope"]
        if scope == "cell":
            row, date = job["row"], job["env"]
            if not snap.get("row_supported", {}).get(row) or date not in snap["days"]:
                return []
            cmp = snap["cells"].get(row, {}).get(date, {}).get("cmp")   # CMP-AUD-103
            if not matrix.cell_buildable(cmp):
                return []
            return [(date, row)]
        rebuild_scope = "stale" if scope == "stale" else "all"
        return day_matrix.cells_to_rebuild(snap, scope=rebuild_scope,
                                           row=job.get("row"), date=job.get("env"))

    def _resolve_baseline_cells(self, job):
        """[(date, row)] for a vs-Baseline compare job. 'cell' = the one explicit
        cell; row/column/all/stale defer to baseline_matrix's staleness-aware list."""
        snap = self._baseline_matrix_snapshot()
        scope = job["scope"]
        if scope == "cell":
            row, date = job["row"], job["env"]
            if not snap.get("row_supported", {}).get(row) or date not in snap["days"]:
                return []
            cmp = snap["cells"].get(row, {}).get(date, {}).get("cmp")   # CMP-AUD-103
            if not matrix.cell_buildable(cmp):
                return []
            return [(date, row)]
        rebuild_scope = "stale" if scope == "stale" else "all"
        return baseline_matrix.cells_to_rebuild(snap, scope=rebuild_scope,
                                                row=job.get("row"), date=job.get("env"))

    def _dispatch_baseline_compare_job(self, job):
        source = settings.get_baseline_matrix_source()
        baseline_id = settings.get_baseline_matrix_baseline()
        if not baseline_matrix.parse_baseline(baseline_id):
            self._emit_log("Pick a baseline first — the vs-Baseline matrix has "
                           "nothing to compare against.")
            return False
        cells = self._resolve_baseline_cells(job)
        if not cells:
            return False
        with self._lock:
            self._matrix = {"phase": "comparing", "row": job.get("row"),
                            "cell": job.get("env"), "done": 0, "total": len(cells)}
        self._emit_log(f"{job['label']} — {len(cells)} comparison(s) vs "
                       f"{baseline_matrix.baseline_label(source, baseline_id)}…")
        self._set_dot("busy", "Comparing…")
        self._emit({"t": "run_started", "mode": "consolidate", "label": "Comparing…",
                    "workers": 1})
        BaselineMatrixCompareWorker(
            source, cells, baseline_id, settings.get_batch_dest(),
            self._gated_queue(), self.cancel_event,
            also_formulas=settings.get_baseline_matrix_formulas()).start()
        return True

    def _dispatch_compare_job(self, job):
        if job.get("which") == "day":
            return self._dispatch_day_compare_job(job)
        if job.get("which") == "baseline":
            return self._dispatch_baseline_compare_job(job)
        base = self._current_baseline()
        dest = settings.get_batch_dest()
        cells = self._resolve_compare_cells(job, base)
        if not cells:
            return False
        with self._lock:
            self._matrix = {"phase": "comparing", "row": job.get("row"),
                            "cell": job.get("env"), "done": 0, "total": len(cells)}
        self._emit_log(f"{job['label']} — {len(cells)} comparison(s) against "
                       f"{matrix.default_env_label(base)}…")
        self._set_dot("busy", "Comparing…")
        self._emit({"t": "run_started", "mode": "consolidate", "label": "Comparing…",
                    "workers": 1})
        MatrixCompareWorker(dest, base, cells, self._gated_queue(), self.cancel_event,
                            tsn_files=self._matrix_tsn_selections(),
                            force_consolidate=job.get("force", False),
                            also_formulas=settings.get_matrix_formulas(),
                            evidence=self._evidence_request()).start()
        return True

    def _dispatch_day_compare_job(self, job):
        source = settings.get_day_matrix_source()
        dest = settings.get_batch_dest()
        cells = self._resolve_day_cells(job)
        if not cells:
            return False
        with self._lock:
            self._matrix = {"phase": "comparing", "row": job.get("row"),
                            "cell": job.get("env"), "done": 0, "total": len(cells)}
        self._emit_log(f"{job['label']} — {len(cells)} comparison(s) vs TSN…")
        self._set_dot("busy", "Comparing…")
        self._emit({"t": "run_started", "mode": "consolidate", "label": "Comparing…",
                    "workers": 1})
        DayMatrixCompareWorker(source, cells, dest, self._gated_queue(), self.cancel_event,
                               tsn_files=self._matrix_tsn_selections(),
                               force_consolidate=job.get("force", False),
                               also_formulas=settings.get_day_matrix_formulas(),
                               evidence=self._evidence_request()).start()
        return True

    @staticmethod
    def _evidence_request():
        """The user's persisted evidence toggle+count, read at dispatch time
        (like the formulas toggles). The engine ignores it for rows without
        evidence support; the count is engine-clamped downstream."""
        return {"enabled": settings.get_evidence_images(),
                "examples": settings.get_evidence_examples(),
                "layout": settings.get_evidence_layout()}

    def _capture_evidence_identity(self, which):
        """Freeze the settings that decide WHICH comparison an on-demand evidence
        job targets, at ENQUEUE time (CMP-AUD-110). A queued camera click must
        illustrate the comparison the user clicked — a later baseline, day-source,
        destination, TSN-selection, example, or layout change must not silently
        retarget it. `_dispatch_evidence_job` uses this frozen identity, never the
        live settings."""
        ident = {"dest": settings.get_batch_dest(),
                 "tsn_files": self._matrix_tsn_selections(),
                 "examples": settings.get_evidence_examples(),
                 "layout": settings.get_evidence_layout()}
        if which == "day":
            ident["source"] = settings.get_day_matrix_source()
        else:
            ident["baseline"] = self._current_baseline()
        return ident

    def _dispatch_evidence_job(self, job):
        """Start the on-demand evidence worker for ONE cell's EXISTING vs-TSN
        comparison (either matrix). Runs regardless of the evidence toggle —
        that's the point of the action; the matrix/day resolvers gate on
        comparison freshness and raise actionable errors. Targeting is bound to
        the job's ENQUEUE-time identity (CMP-AUD-110), NOT the live settings, so a
        later baseline/source/destination/TSN/example/layout change can't
        silently retarget a queued click (the pre-CMP-AUD-110 jobs, if any, fall
        back to the live settings)."""
        ident = job.get("evidence") or {}
        dest = ident.get("dest") or settings.get_batch_dest()
        tsn_files = (ident["tsn_files"] if "tsn_files" in ident
                     else self._matrix_tsn_selections())
        examples = ident.get("examples", settings.get_evidence_examples())
        layout = ident.get("layout") or settings.get_evidence_layout()
        row, cell = job["row"], job["env"]
        comparisons_dest = None
        if job.get("which") == "day":
            source = ident.get("source") or settings.get_day_matrix_source()
            run_fn = (lambda events, commit_guard=None:
                      day_matrix.evidence_for_day_cell(
                source, cell, row, dest, events, tsn_files=tsn_files,
                examples=examples, layout=layout, commit_guard=commit_guard))
        else:
            base = ident.get("baseline") or self._current_baseline()
            comparisons_dest = dest
            run_fn = (lambda events, commit_guard=None:
                      matrix.evidence_for_cell(
                dest, row, cell, base, events, tsn_files=tsn_files,
                examples=examples, layout=layout, commit_guard=commit_guard))
        with self._lock:
            self._matrix = {"phase": "comparing", "row": row, "cell": cell,
                            "done": 0, "total": 1}
        self._emit_log(f"{job['label']} — generating from the existing comparison…")
        self._set_dot("busy", "Evidence images…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Evidence images…", "workers": 1})
        MatrixEvidenceWorker(run_fn, row, cell, self._gated_queue(),
                             self.cancel_event,
                             comparisons_dest=comparisons_dest).start()
        return True

    def _matrix_worker_count(self):
        """Fast-mode browser count for matrix re-exports (the shared fast_workers
        knob, clamped to the engine's 2..MAX range)."""
        try:
            return max(2, min(int(settings.get("fast_workers")), MAX_WORKERS))
        except (TypeError, ValueError):
            return max(2, default_worker_count())

    def _resolve_export_steps(self, job):
        """[(spec, src, env)] for an export job. 'cell' = one (report, env); 'row'
        = one report across the visible envs; 'column' = every exportable report
        for one env. Reports with no export adapter are skipped."""
        rows_by_key = {r[0]: r for r in matrix_rows()}

        def spec_for(row_key):
            row = rows_by_key.get(row_key)
            return EXPORT_REPORTS[row[3]][2] if row is not None and row[3] is not None else None

        scope = job["scope"]
        if scope == "cell":
            spec, combo = spec_for(job["row"]), self._parse_env_keys([job["env"]])
            return [(spec, combo[0][0], combo[0][1])] if spec is not None and combo else []
        snap = self._matrix_snapshot(self._current_baseline())
        steps = []
        if scope == "row":
            spec = spec_for(job["row"])
            if spec is None:
                return []
            for env in snap["envs"]:
                combo = self._parse_env_keys([env])
                if combo:
                    steps.append((spec, combo[0][0], combo[0][1]))
        elif scope == "column":
            combo = self._parse_env_keys([job["env"]])
            if not combo:
                return []
            src, env = combo[0]
            for row_key in snap["rows"]:
                spec = spec_for(row_key)
                if spec is not None:
                    steps.append((spec, src, env))
        return steps

    def _resolve_day_export_steps(self, job):
        """[(spec, src, env)] for a by-day EXPORT job — TODAY only, into a dated run
        folder. 'cell'/'row' = the one report; 'column' = every visible supported
        report. src/env come from the matrix's single source. Reports with no
        export adapter are skipped. (Foundation note: a future district-wide pull
        would widen this to per-district steps; the dated/site machinery already
        fits, only the route/district scope would change.)"""
        snap = self._day_matrix_snapshot()
        combo = self._parse_env_keys([snap["source"]])
        if not combo:
            return []
        src, env = combo[0]
        rows_by_key = {r[0]: r for r in matrix_rows()}

        def spec_for(row_key):
            row = rows_by_key.get(row_key)
            if row is not None and row[3] is not None:
                return EXPORT_REPORTS[row[3]][2]
            for _label, _fmt, spec in EXPORT_REPORTS:   # extra rows keyed by subdir
                if spec.subdir == row_key:
                    return spec
            return None

        scope = job["scope"]
        if scope in ("cell", "row"):
            spec = spec_for(job["row"])
            return [(spec, src, env)] if spec is not None else []
        steps = []                                       # column / all: every visible report
        for rk in snap["rows"]:
            if not snap.get("row_supported", {}).get(rk):
                continue
            spec = spec_for(rk)
            if spec is not None:
                steps.append((spec, src, env))
        return steps

    def _dispatch_day_export_job(self, job):
        """Export the by-day matrix's TODAY column (or one report) into a dated run
        folder for the matrix source, then auto-chain the consolidate+compare in
        _on_matrix_export_done so the column 'fills itself'."""
        steps = self._resolve_day_export_steps(job)
        if not steps:
            return False
        n_workers = self._matrix_worker_count() if job.get("fast") else 1
        with self._lock:
            self._fast_run = n_workers > 1
        note = f"   ·   FAST MODE ({n_workers} browsers)" if n_workers > 1 else ""
        self._emit_log(f"{job['label']} — {len(steps)} export(s){note}…")
        self._set_dot("busy", "Exporting…")
        self._emit({"t": "run_started", "mode": "export", "label": "Exporting…",
                    "workers": n_workers})
        MatrixBatchExportWorker(steps, settings.get_batch_dest(), self._gated_queue(),
                                self.cancel_event, self.skip_event, self.pause_event,
                                workers=n_workers, dated=True,
                                # CMP-AUD-091: bind the run date captured at dispatch
                                # (job["env"], the day column) so the export writes
                                # that exact folder and the chained compare matches it.
                                day=job.get("env"),
                                on_worker=self._set_matrix_export_worker).start()
        return True

    def _dispatch_export_job(self, job):
        if job.get("which") == "day":
            return self._dispatch_day_export_job(job)
        dest = settings.get_batch_dest()
        steps = self._resolve_export_steps(job)
        if not steps:
            return False
        n_workers = self._matrix_worker_count() if job.get("fast") else 1
        with self._lock:
            self._fast_run = n_workers > 1
        note = f"   ·   FAST MODE ({n_workers} browsers)" if n_workers > 1 else ""
        self._emit_log(f"{job['label']} — {len(steps)} export(s){note}…")
        self._set_dot("busy", "Refreshing…")
        self._emit({"t": "run_started", "mode": "export", "label": "Refreshing…",
                    "workers": n_workers})
        MatrixBatchExportWorker(steps, dest, self._gated_queue(), self.cancel_event,
                                self.skip_event, self.pause_event,
                                workers=n_workers,
                                on_worker=self._set_matrix_export_worker).start()
        return True

    def _set_matrix_export_worker(self, worker):
        """Track the matrix re-export's live ExportWorker (or None when a step
        ends) so request_preview can reach it, like a normal export."""
        with self._lock:
            self._export_worker = worker

    def _dispatch_tsn_consolidate_job(self, job):
        dest = settings.get_batch_dest()
        origin = job.get("origin") or "legacy"
        self._emit_log(f"Consolidating the {job['subdir']} TSN PDFs…")
        self._set_dot("busy", "Consolidating TSN…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Consolidating TSN…", "workers": 1})
        MatrixTsnConsolidateWorker(dest, job["subdir"], self._gated_queue(),
                                   self.cancel_event, origin=origin).start()
        return True

    # ----- matrix entry methods (enqueue onto the job queue) ------------------
    @_api_method
    def refresh_cell_export(self, row_key, env_key):
        """Queue a LIVE re-export of ONE (report, env) into the store. Reuses the
        export engine with no manifest, so it can't disturb a paused batch."""
        row = {r[0]: r for r in matrix_rows()}.get(row_key)
        if row is None or row[3] is None:
            return {"error": "That report can't be exported from the matrix."}
        if not self._parse_env_keys([env_key]):
            return {"error": "Unknown environment."}
        job = self._make_job("export", "cell",
                             self._job_label("export", "cell", row_key, env_key),
                             row=row_key, env=env_key, fast=settings.get_matrix_fast())
        return self._enqueue_matrix_job(job)

    @_api_method
    def refresh_row_export(self, row_key):
        """Queue a LIVE re-export of ONE report across every visible environment."""
        row = {r[0]: r for r in matrix_rows()}.get(row_key)
        if row is None or row[3] is None:
            return {"error": "That report can't be exported from the matrix."}
        job = self._make_job("export", "row",
                             self._job_label("export", "row", row=row_key),
                             row=row_key, fast=settings.get_matrix_fast())
        return self._enqueue_matrix_job(job)

    @_api_method
    def refresh_column_export(self, env_key):
        """Queue a LIVE re-export of every exportable report for ONE environment."""
        if not self._parse_env_keys([env_key]):
            return {"error": "Unknown environment."}
        job = self._make_job("export", "column",
                             self._job_label("export", "column", env=env_key),
                             env=env_key, fast=settings.get_matrix_fast())
        return self._enqueue_matrix_job(job)

    @_api_method
    def refresh_cell_comparison(self, row_key, env_key):
        """Queue a (re)build of ONE cell's comparison for the row's SELECTED mode."""
        base = self._current_baseline()
        if row_key not in {r[0] for r in matrix_rows()}:
            return {"error": "Unknown report for the matrix."}
        if not self._parse_env_keys([env_key]):
            return {"error": "Unknown environment."}
        mode = settings.get_matrix_row_modes().get(row_key, "env")
        if mode == "env" and env_key == base:
            return {"error": "The baseline column has nothing to compare against."}
        # CMP-AUD-103: refuse a cell whose input side is already known missing, up
        # front — the same buildability predicate the bulk selector uses — instead
        # of claiming the queue only to skip it silently (or fail deep in the worker).
        cmp = self._matrix_snapshot(base)["cells"].get(row_key, {}).get(env_key, {}).get("cmp")
        reason = matrix.cell_unbuildable_reason(cmp)
        if reason:
            return {"error": reason}
        job = self._make_job("compare", "cell",
                             self._job_label("compare", "cell", row_key, env_key),
                             row=row_key, env=env_key)
        return self._enqueue_matrix_job(job)

    @_api_method
    def matrix_evidence_cell(self, row_key, env_key):
        """Queue an ON-DEMAND evidence run for ONE cell's EXISTING vs-TSN
        comparison — images only, no re-compare (runs even with the Evidence
        images toggle off). The worker refuses stale/missing comparisons with
        an actionable message."""
        if row_key not in {r[0] for r in matrix_rows()}:
            return {"error": "Unknown report for the matrix."}
        if not self._parse_env_keys([env_key]):
            return {"error": "Unknown environment."}
        import visual_evidence                       # lazy: pulls PIL/pdfium
        if not visual_evidence.capable(row_key):
            return {"error": "This report doesn't support evidence images."}
        job = self._make_job("evidence", "cell",
                             self._job_label("evidence", "cell", row_key, env_key),
                             row=row_key, env=env_key)
        job["evidence"] = self._capture_evidence_identity("env")
        return self._enqueue_matrix_job(job)

    @_api_method
    def recompute_matrix(self, scope="stale", row=None, env=None, force=False):
        """Queue a comparison rebuild in scope ('stale'/'all') for the current
        baseline — drives refresh-stale, the baseline-switch recompute, and (with
        `row`/`env`) the per-row and per-column rebuild buttons. `force` also
        rebuilds the persistent consolidated workbook ('refresh consolidated').
        Returns {nothing:True} only when the queue is idle AND there's nothing to
        do (and not forced), so
        the UI can say so without queuing a no-op (targets are re-resolved when a
        job actually runs)."""
        base = self._current_baseline()
        scope = scope if scope in ("stale", "all") else "stale"
        # CMP-AUD-096: a SUPPLIED-but-invalid scope filter is REJECTED, never
        # silently normalized to None (which the endpoint reads as "no filter" ->
        # a whole-matrix rebuild). An absent (falsy) filter still means everything.
        if row and row not in {r[0] for r in matrix_rows()}:
            return {"error": "Unknown report row for the rebuild."}
        if env and not self._parse_env_keys([env]):
            return {"error": "Unknown environment for the rebuild."}
        row = row or None
        env = env or None
        job_scope = "row" if row else "column" if env else scope
        with self._lock:
            idle = not self._task and not self._queue
        if idle and not force:
            cells = matrix.cells_to_rebuild(self._matrix_snapshot(base), scope=scope,
                                            row=row, env=env)
            if not cells:
                return {"ok": True, "nothing": True}
        job = self._make_job("compare", job_scope,
                             self._job_label("compare", job_scope, row=row, env=env),
                             row=row, env=env, force=force)
        return self._enqueue_matrix_job(job)

    @_api_method
    def open_cell_comparison(self, row_key, env_key):
        """Open ONE cell's comparison VALUES workbook for the row's SELECTED mode
        (cross-env -> comparisons/<baseline>/, TSN/self -> comparisons/tsn/). The
        path is built from validated keys, so it can't point outside the store."""
        base = self._current_baseline()
        if row_key not in {r[0] for r in matrix_rows()}:
            return {"error": "Unknown report for the matrix."}
        if not self._parse_env_keys([env_key]):
            return {"error": "Unknown environment."}
        mode = settings.get_matrix_row_modes().get(row_key, "env")
        if mode == "env" and env_key == base:
            return {"error": "The baseline column has no comparison to open."}
        dest = settings.get_batch_dest()
        path = matrix.out_path_for_cell(dest, base, row_key, env_key, mode)
        if path is None or not path.exists():
            return {"error": "No comparison built yet — use “↻ compare” first."}
        self._open_file(path)
        return {"ok": True}

    @_api_method
    def set_matrix_env(self, env_key, visible):
        """Show/hide an environment COLUMN on the matrix (hidden columns aren't
        rendered or refreshed). At least one column must stay on."""
        if not self._parse_env_keys([env_key]):
            return {"error": "Unknown environment."}
        all_envs = matrix.env_keys()
        hidden = set(settings.get_matrix_hidden_envs())
        if visible:
            hidden.discard(env_key)
        else:
            hidden.add(env_key)
        if len(hidden & set(all_envs)) >= len(all_envs):
            return {"error": "Keep at least one environment on the matrix."}
        settings.set_matrix_hidden_envs(sorted(hidden))
        self._push_state()
        return {"ok": True, "hidden_envs": sorted(hidden)}

    @_api_method
    def set_matrix_row_mode(self, row_key, mode_id):
        """Set one report row's comparison mode (the dropdown under its name).
        Validated against that row's available, SUPPORTED modes."""
        snap = self._matrix_snapshot(self._current_baseline())
        avail = {m["id"]: m for m in snap.get("row_modes", {}).get(row_key, [])}
        if not avail:
            return {"error": "Unknown report for the matrix."}
        if mode_id not in avail:
            return {"error": "Unknown comparison mode for this report."}
        if not avail[mode_id]["supported"]:
            return {"error": "That comparison isn't available yet for this report."}
        settings.set_matrix_row_mode(row_key, mode_id)
        self._push_state()
        return {"ok": True, "mode": mode_id}

    @_api_method
    def set_all_matrix_modes(self, mode_id):
        """Global 'set all comparisons to…' — apply a mode to every row that
        supports it (others stay on cross-environment). mode_id is 'env' or 'tsn'
        (the two universal axes; per-row PDF/Excel flavors stay row-local)."""
        if mode_id not in ("env", "tsn"):
            return {"error": "Pick Cross-environment or vs TSN."}
        # CMP-AUD-102: apply over the AUTHORITATIVE row catalog (every row, hidden
        # or not), never the visibility-filtered snapshot — otherwise a hidden row
        # keeps a latent disagreeing mode that surfaces the moment it's unhidden,
        # so "all" quietly meant "the visible subset".
        for row_key, modes in matrix.all_row_modes().items():
            avail = {m["id"]: m for m in modes}
            if mode_id == "env":
                settings.set_matrix_row_mode(row_key, "env")
            elif mode_id in avail and avail[mode_id]["supported"]:
                settings.set_matrix_row_mode(row_key, mode_id)
            # rows without a supported tsn mode are left as-is (cross-env)
        self._push_state()
        return {"ok": True, "mode": mode_id}

    @_api_method
    def set_matrix_tsn_file(self, subdir, path):
        """Set/clear the TSN file for a report subdir (the picker under the name).
        An empty path clears it (back to auto-find in _tsn_input/<subdir>/)."""
        import tsn_library
        key = tsn_library.canonical_dataset_key(subdir)
        if key not in self._valid_tsn_dataset_keys():
            return {"error": "Unknown report subdir."}
        if not isinstance(path, str):
            return {"error": "Pick an Excel workbook (.xlsx), or clear the selection."}
        path = path.strip()
        self._matrix_tsn_selections()             # persist any legacy alias migration first
        if path:
            try:
                selection = tsn_library.create_explicit_selection(path)
            except ValueError as e:
                return {"error": str(e)}
        else:
            selection = None
        settings.set_matrix_tsn_selection(key, selection)
        self._push_state()
        return {"ok": True}

    @_api_method
    def pick_matrix_tsn_file(self, subdir):
        """Native open dialog (xlsx) for a report's TSN workbook, defaulting into
        the report's canonical TSN library folder (<library>/<subdir>/, where its
        raw/ + consolidated/ live); persists the choice. Returns {ok, path} or
        {cancelled}."""
        import tsn_library
        key = tsn_library.canonical_dataset_key(subdir)
        if key not in self._valid_tsn_dataset_keys():
            return {"error": "Unknown report subdir."}
        start = TSN_LIBRARY_ROOT / key
        try:
            start.mkdir(parents=True, exist_ok=True)
        except OSError:
            start = TSN_LIBRARY_ROOT
        picked = pick_path(self._window,
            webview.OPEN_DIALOG, allow_multiple=False, directory=str(start),
            file_types=("Excel workbook (*.xlsx)",))
        if not picked:
            return {"cancelled": True}
        try:
            selection = tsn_library.create_explicit_selection(picked)
        except ValueError as e:
            return {"error": str(e)}
        self._matrix_tsn_selections()
        settings.set_matrix_tsn_selection(key, selection)
        self._push_state()
        return {"ok": True, "path": picked}

    @_api_method
    def consolidate_matrix_tsn(self, subdir):
        """Queue building the consolidated TSN workbook for a report from its raw
        TSN PDFs. CMP-AUD-010: routes by SOURCE ORIGIN — a canonical library source
        (raw PDFs imported into the library) builds through the registered TSN
        builder reading the library raw/ folder (so EVERY PDF-backed family works,
        not just Highway Log); a legacy <dest>/_tsn_input/ drop keeps the
        back-compat Highway-Log consolidator. Only a report whose resolved source is
        unconsolidated raw PDFs is accepted (offline; pdfplumber)."""
        import tsn_library
        tsn_key = tsn_library.canonical_dataset_key(subdir)
        if tsn_key not in self._valid_tsn_dataset_keys():
            return {"error": "Unknown report subdir."}
        dest = settings.get_batch_dest()
        selected = self._matrix_tsn_selections().get(tsn_key)
        src = matrix.tsn_source(dest, tsn_key, selected)
        if src.get("kind") not in ("pdfs", "raw"):
            return {"error": "There are no unconsolidated TSN PDFs to build for "
                             "this report — import raw TSN files first."}
        legacy = bool(src.get("legacy"))
        if legacy and tsn_key != "highway_log":
            # The legacy _tsn_input consolidator only knows Highway Log; a canonical
            # source would have routed to build_consolidated instead.
            return {"error": "Legacy TSN consolidation is only available for Highway Log."}
        label = (tsn_library.get(tsn_key).label
                 if tsn_library.is_registered(tsn_key) else tsn_key)
        job = self._make_job("tsn_consolidate", "consolidate",
                             f"Consolidate TSN {label} PDFs", subdir=tsn_key,
                             origin=("legacy" if legacy else "canonical"))
        return self._enqueue_matrix_job(job)

    # ----- canonical TSN library (Settings ▸ TSN reports panel, v0.17.0) ------
    def _tsn_library_status(self):
        """Per-report status rows for the Settings TSN-reports panel. Floats
        (mtimes) are dropped — the panel only needs the booleans/counts/label."""
        import tsn_library                              # lazy import (tsn_library pulls pdfplumber via report_catalog)
        # A TSN report can need TWO distinct assets and the panel used to show only
        # the first: the raw the normalized library is BUILT from (district PDFs or
        # a statewide workbook), and the TSN PRINTS the evidence images are cropped
        # from. Reporting only the build source made "everything green" mean nothing
        # about whether evidence could render. Both are reported per report now.
        prints = {}
        try:
            import visual_evidence                      # lazy (pulls pdfplumber)
            for r in visual_evidence.availability().get("reports", []):
                prints[r["key"]] = r
        except Exception as e:                           # noqa: BLE001
            log.warning("tsn panel: evidence-print probe unavailable (%s): %s",
                        type(e).__name__, e)
        rows = []
        for s in tsn_library.all_status():
            ev = prints.get(s["report"])
            reason = self._tsn_stale_reason(s)
            if reason and s["raw_present"]:
                # "STALE" alone sent the owner back to us twice: a rebuild can
                # succeed and the library still read stale for one of eight
                # independent reasons. status() already decides which; it was
                # simply discarded here.
                log.info("tsn panel: %s reads stale — %s", s["report"], reason)
            rows.append({
                "report": s["report"], "label": s["label"],
                "raw_kind": s["raw_kind"], "raw_present": s["raw_present"],
                "raw_count": s["raw_count"],
                "consolidated_present": s["consolidated_present"],
                "current": s["current"],
                "raw_dir": str(tsn_library.raw_dir(s["report"])),  # where its files live
                # Evidence prints: None when this report has no evidence support at
                # all (a missing print is then not a gap). "in_raw" reports reuse the
                # SAME district prints they build from — never a second drop.
                "evidence_supported": ev is not None,
                "evidence_pdfs": (ev or {}).get("tsn_pdfs", 0),
                "evidence_dir": (ev or {}).get("dir", ""),
                "evidence_in_raw": (ev or {}).get("source") == "raw",
                "stale_reason": reason,
            })
        return rows

    @staticmethod
    def _tsn_stale_reason(s):
        """Why this TSN report is not current — the FIRST failing condition.

        `status()` already decides every one of these independently and returns
        them; the panel used to keep only the collapsed `current` flag, so a
        rebuild that succeeded and a library that was never built looked
        identical ("STALE") and neither said what to do about it.

        Ordered outermost-first: a raw-source problem explains everything after
        it, so report that rather than the derived mismatch it causes.
        """
        if s.get("current"):
            return ""
        if not s.get("raw_present"):
            return "no raw TSN files imported yet"
        if not s.get("raw_admissible"):
            return s.get("raw_admission_error") or "the raw source set is not admissible"
        if not s.get("consolidated_present"):
            return "not built yet — rebuild it"
        if s.get("certificate_error"):
            return f"its build record could not be read ({s['certificate_error']})"
        if not s.get("metadata_current"):
            return ("its build record does not match the workbook on disk "
                    "(rebuilt outside the app, or the file changed after it was built)")
        if not s.get("producer_complete"):
            return "the last build reported skipped or failed inputs — rebuild it"
        if not s.get("normalization_current"):
            stored = s.get("stored_normalization_version")
            expected = s.get("expected_normalization_version")
            if stored is None:
                return (f"its build record carries no normalizer version "
                        f"(this app expects {expected}) — rebuild it")
            if not isinstance(stored, int) or isinstance(stored, bool):
                return (f"its build record's normalizer version is unusable "
                        f"({stored!r}; this app expects {expected}) — rebuild it")
            return (f"built by normalizer version {stored}, this app expects "
                    f"{expected} — rebuild it (expected once after an app update)")
        if not s.get("raw_manifest_current"):
            return "the raw TSN files changed since it was built — rebuild it"
        if not s.get("normalized_workbook_current"):
            return (s.get("workbook_identity_error")
                    or "the consolidated workbook changed after it was built")
        if not s.get("identity_token_current"):
            return "its identity stamp does not match its own inputs — rebuild it"
        if s.get("coherence_error"):
            return f"its files changed while being checked ({s['coherence_error']})"
        return "it did not pass the freshness check"

    @_api_method
    def tsn_library_status(self):
        """Refresh the Settings TSN-reports panel (after an import / rebuild)."""
        return {"reports": self._tsn_library_status()}

    @_api_method
    def import_tsn_raw(self, report):
        """Native open dialog to copy raw TSN file(s) into the canonical library's
        raw/ folder for `report` (PDFs or the statewide XLSX, per the report). The
        consolidated workbook is then out of date until rebuilt. Returns
        {ok, imported, reports} / {cancelled} / {error}."""
        import tsn_library                              # lazy
        if not tsn_library.is_registered(report):
            return {"error": "Unknown TSN report."}
        spec = tsn_library.get(report)
        is_pdf = spec.raw_glob.lower().endswith("pdf")
        ftype = ("PDF document (*.pdf)" if is_pdf else "Excel workbook (*.xlsx)")
        srcs = pick_paths(self._window,
            webview.OPEN_DIALOG, allow_multiple=True, file_types=(ftype,))
        if not srcs:
            return {"cancelled": True}
        try:
            landed = tsn_library.import_raw(report, srcs)
        except (OSError, ValueError) as e:
            self._emit_log(f"TSN import failed for {spec.label} ({type(e).__name__}): {e}")
            return {"error": f"Could not import the file(s): {e}"}
        self._emit_log(f"Imported {len(landed)} raw file(s) for {spec.label}. "
                       "Rebuild its consolidated workbook to use them.")
        return {"ok": True, "imported": len(landed),
                "reports": self._tsn_library_status()}

    @_api_method
    def rebuild_tsn_library(self, report):
        """Rebuild the consolidated/normalized TSN workbook for `report` from its
        library raw/ files (offline; pdfplumber/openpyxl). Runs on the shared
        single-task slot via ConsolidateWorker, so progress shows in the activity
        log like any consolidation. Returns {ok} / {error}."""
        import tsn_library                              # lazy
        if not tsn_library.is_registered(report):
            return {"error": "Unknown TSN report."}
        spec = tsn_library.get(report)
        if not self._tsn_library_status_for(report)["raw_present"]:
            return {"error": f"No raw {spec.label} files are imported yet — "
                             "import the raw TSN file(s) first."}
        err = self._claim_task_error("consolidate")
        if err:
            return err
        self.cancel_event.clear()
        self._emit_log(f"Rebuilding TSN library: {spec.label}…")
        self._set_dot("busy", f"Rebuilding {spec.label}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Rebuilding {spec.label}…"})
        self._push_state()

        def _run(events=None, confirm_overwrite=None, day=None):   # noqa: ARG001
            return tsn_library.build_consolidated(
                report, events=events, confirm_overwrite=lambda _p: True, force=True)

        ConsolidateWorker(_run, self._gated_queue(), self.cancel_event, lambda _p: True).start()
        return {"ok": True}

    @_api_method
    def rebuild_stale_tsn_libraries(self):
        """Rebuild EVERY imported TSN report whose consolidated workbook is out of
        date, on the one shared task slot (the same ConsolidateWorker + per-report
        builder the single-report Rebuild uses — no second code path).

        A report is out of date when its raw files are imported but the consolidated
        workbook is missing or built by a superseded normalizer (the D2 version bump
        after an upgrade). Reports already current are skipped. Returns {ok, reports}
        / {error}."""
        import tsn_library                              # lazy
        stale = [row["report"] for row in self._tsn_library_status()
                 if row["raw_present"] and not row["current"]]
        if not stale:
            return {"error": "Every imported TSN report is already up to date."}
        err = self._claim_task_error("consolidate")
        if err:
            return err
        self.cancel_event.clear()
        labels = ", ".join(tsn_library.get(r).label for r in stale)
        headline = (f"Rebuilding {len(stale)} out-of-date TSN report"
                    f"{'' if len(stale) == 1 else 's'}")
        self._emit_log(f"{headline}: {labels}…")
        self._set_dot("busy", f"{headline}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"{headline}…"})
        self._push_state()

        def _run(events=None, confirm_overwrite=None, day=None):   # noqa: ARG001
            # The FIRST failure is what gets reported: returning the last result
            # would let an early failure hide behind a later success and read green.
            first_bad = last = None
            for report in stale:
                if self.cancel_event.is_set():
                    break
                spec = tsn_library.get(report)
                if events is not None:
                    events.on_log(f"— {spec.label} —")
                last = tsn_library.build_consolidated(
                    report, events=events,
                    confirm_overwrite=lambda _p: True, force=True)
                if first_bad is None and getattr(last, "status", None) != "ok":
                    first_bad = last
            return first_bad or last

        ConsolidateWorker(_run, self._gated_queue(), self.cancel_event, lambda _p: True).start()
        return {"ok": True, "reports": len(stale)}

    def _tsn_library_status_for(self, report):
        import tsn_library                              # lazy
        return tsn_library.status(report)

    # ----- matrix queue management (v0.16.0) ---------------------------------
    @_api_method
    def set_matrix_fast(self, on):
        """Toggle fast (parallel) mode for matrix re-exports (persisted; reuses
        the global fast_workers count)."""
        val = settings.set_matrix_fast(bool(on))
        self._emit_log("Matrix fast mode " + ("on" if val else "off")
                       + (f" — up to {settings.get('fast_workers')} browsers." if val else "."))
        self._push_state()
        return {"ok": True, "on": val}

    @_api_method
    def set_matrix_formulas(self, on):
        """Toggle whether matrix comparisons ALSO write a live-formulas workbook
        beside the values copy (persisted). The values copy always remains the
        offline-count source; the formulas twin is an opt-in auditable extra."""
        val = settings.set_matrix_formulas(bool(on))
        self._emit_log("Matrix live-formulas workbook " + ("on" if val else "off")
                       + (" — each comparison also writes a '… (formulas).xlsx'."
                          if val else "."))
        self._push_state()
        return {"ok": True, "on": val}

    @_api_method
    def set_day_matrix_formulas(self, on):
        """Toggle the by-day matrix's OWN live-formulas option (persisted,
        independent of the Everything matrix's)."""
        val = settings.set_day_matrix_formulas(bool(on))
        self._emit_log("By-day live-formulas workbook " + ("on" if val else "off")
                       + (" — each comparison also writes a '… (formulas).xlsx'."
                          if val else "."))
        self._push_state()
        return {"ok": True, "on": val}

    @_api_method
    def set_evidence_images(self, on):
        """Toggle visual-evidence generation for vs-TSN comparisons of
        evidence-capable reports (persisted; ONE toggle shared by the
        Everything matrix and the by-day matrix)."""
        val = settings.set_evidence_images(bool(on))
        self._emit_log("Evidence images " + ("on" if val else "off")
                       + (" — each supported vs-TSN comparison also writes an "
                          "'… (evidence).xlsx' + highlighted PDF snippets."
                          if val else "."))
        self._push_state()
        return {"ok": True, "on": val}

    @_api_method
    def set_evidence_examples(self, n):
        """Persist how many examples per differing column the evidence set
        samples (engine-clamped to 1–10)."""
        val = settings.set_evidence_examples(n)
        self._emit_log(f"Evidence images: {val} example(s) per column.")
        self._push_state()
        return {"ok": True, "examples": val}

    @_api_method
    def set_evidence_layout(self, layout):
        """Persist the evidence-workbook image layout ('pair' = side-by-side,
        'stacked', or 'both'). Only the selected layout(s) render; each becomes
        a tab per comparison column."""
        val = settings.set_evidence_layout(layout)
        label = {"pair": "side-by-side", "stacked": "stacked",
                 "both": "both layouts"}.get(val, val)
        self._emit_log(f"Evidence images: {label}.")
        self._push_state()
        return {"ok": True, "layout": val}

    @_api_method
    def matrix_queue_remove(self, job_id):
        """Remove ONE pending (not-yet-running) job from the queue."""
        try:
            jid = int(job_id)
        except (TypeError, ValueError):
            return {"error": "Bad job id."}
        with self._lock:
            before = len(self._queue)
            self._queue = collections.deque(j for j in self._queue if j["id"] != jid)
            removed = len(self._queue) != before
        if removed:
            self._push_state()
        return {"ok": True, "removed": removed}

    @_api_method
    def matrix_queue_move(self, job_id, direction):
        """Reorder a pending job up (earlier) or down (later) in the queue."""
        if direction not in ("up", "down"):
            return {"error": "Direction must be up or down."}
        try:
            jid = int(job_id)
        except (TypeError, ValueError):
            return {"error": "Bad job id."}
        with self._lock:
            q = list(self._queue)
            idx = next((i for i, j in enumerate(q) if j["id"] == jid), None)
            moved = False
            if idx is not None:
                swap = idx - 1 if direction == "up" else idx + 1
                if 0 <= swap < len(q):
                    q[idx], q[swap] = q[swap], q[idx]
                    self._queue = collections.deque(q)
                    moved = True
        if moved:
            self._push_state()
        return {"ok": True, "moved": moved}

    @_api_method
    def matrix_queue_clear(self):
        """Drop every PENDING job (the running one keeps going)."""
        with self._lock:
            n = len(self._queue)
            self._queue.clear()
        if n:
            self._emit_log(f"Cleared {n} queued matrix job(s).")
            self._push_state()
        return {"ok": True, "cleared": n}

    @_api_method
    def matrix_stop_all(self):
        """Clear the pending queue AND cancel the running matrix job."""
        with self._lock:
            n = len(self._queue)
            self._queue.clear()
            running = self._task == "matrix"
        if running:
            self.cancel_event.set()
            self.pause_event.clear()
        if n or running:
            self._emit_log("Stopping matrix work — cleared "
                           f"{n} queued"
                           + ("; cancelling the running job." if running else "."))
            self._push_state()
        return {"ok": True, "cleared": n, "cancelling": running}

    @_api_method
    def open_comparisons_folder(self):
        """Open the folder holding EVERY comparison workbook — the common
        <dest>/comparisons/ root, so both the cross-env <baseline>/ tree AND the
        TSN / PDF-vs-Excel self-check tree (comparisons/tsn/) are reachable.
        CMP-AUD-101: the old per-baseline root hid a row's active TSN/self
        artifact, sending the user to an unrelated tree."""
        dest = settings.get_batch_dest()
        self._open_folder(matrix.comparisons_common_root(dest))
        return {"ok": True}

    # ----- Compare-tab "TSN by day" matrix -----------------------------------
    def _day_matrix_snapshot(self):
        """The by-day snapshot with the user's source / day columns / hidden rows
        and the shared TSN dataset applied (dest = the Everything matrix's
        batch_dest, so both matrices reuse one _tsn_input folder)."""
        return day_matrix.day_matrix_snapshot(
            settings.get_day_matrix_source(), settings.get_day_matrix_days(),
            hidden=settings.get_day_matrix_hidden(),
            tsn_files=self._matrix_tsn_selections(),
            dest=settings.get_batch_dest(),
            row_order=settings.get_day_matrix_row_order())

    def _day_job_label(self, scope, row=None, date=None):
        rl = self._matrix_row_label(row) if row else None
        if scope == "cell":
            return f"Rebuild {rl} — {date} vs TSN"
        if scope == "row":
            return f"Rebuild {rl} — all days vs TSN"
        if scope == "column":
            return f"Rebuild all reports — {date} vs TSN"
        if scope == "stale":
            return "Refresh stale by-day comparisons"
        return "Rebuild all by-day comparisons"

    @_api_method
    def day_matrix_info(self):
        """The by-day matrix snapshot for the Compare tab — a pure filesystem read
        plus the add-day picker's available days for the current source. Also
        re-pushes the state so the evidence toggle re-probes on tab entry (see
        matrix_info)."""
        snap = self._day_matrix_snapshot()
        snap["available_days"] = day_matrix.available_days(snap["source"])
        self._push_state()
        return snap

    @_api_method
    def set_day_matrix_source(self, source):
        """Set the by-day matrix data source (the day columns are dates within it)."""
        if source not in day_matrix.sources():
            return {"error": "Unknown data source."}
        settings.set_day_matrix_source(source)
        # CMP-AUD-095: the source switch changes which run folders exist, so a day
        # column retained from the old source can point at a folder that doesn't
        # exist under the new one. Keep only the validated intersection — days that
        # actually have an export for the new source.
        avail = set(day_matrix.available_days(source))
        kept = [d for d in settings.get_day_matrix_days() if d in avail]
        if kept != settings.get_day_matrix_days():
            settings.set_day_matrix_days(kept)
        self._emit_log(f"By-day matrix source set to {matrix.default_env_label(source)}.")
        self._push_state()
        return {"ok": True, "source": source, "days": kept}

    @_api_method
    def add_day_matrix_day(self, date):
        """Add a day COLUMN: a date with an export for the source, or TODAY
        (always addable — the matrix exports into today itself, W3)."""
        if date not in day_matrix.available_days(settings.get_day_matrix_source()):
            return {"error": "That day has no export for this source (only "
                             "exported days — or today — can be added)."}
        days = settings.get_day_matrix_days()
        if date not in days:
            settings.set_day_matrix_days(days + [date])
        self._push_state()
        return {"ok": True, "days": settings.get_day_matrix_days()}

    def _day_job_active_or_queued(self, date):
        """True iff a by-day matrix job (an export or its chained comparison) for
        `date` is running or waiting in the shared queue — for day jobs `env`
        carries the date. CMP-AUD-094: removing such a day would strand the
        automatic comparison (its completion lookup finds no column and spawns
        nothing)."""
        def _targets(job):
            return (isinstance(job, dict) and job.get("which") == "day"
                    and job.get("env") == date)
        with self._lock:                 # snapshot current + queued atomically
            return (_targets(self._coord.current_job)
                    or any(_targets(j) for j in self._coord.queue))

    @_api_method
    def remove_day_matrix_day(self, date):
        """Remove a day column. CMP-AUD-094: refuse while that day's export or its
        chained comparison is running/queued — removing it would silently discard
        the automatic comparison half of the export-and-compare workflow."""
        if self._day_job_active_or_queued(date):
            return {"error": "That day's export/comparison is still running — wait "
                             "for it to finish (or cancel it) before removing it."}
        settings.set_day_matrix_days(
            [d for d in settings.get_day_matrix_days() if d != date])
        self._push_state()
        return {"ok": True, "days": settings.get_day_matrix_days()}

    @_api_method
    def set_day_matrix_report(self, row_key, visible):
        """Show/hide a report ROW on the by-day matrix. At least one stays on."""
        keys = {r["key"] for r in self._day_matrix_snapshot()["all_rows"]}
        if row_key not in keys:
            return {"error": "Unknown report for the matrix."}
        hidden = set(settings.get_day_matrix_hidden())
        if visible:
            hidden.discard(row_key)
        else:
            hidden.add(row_key)
        if len(hidden & keys) >= len(keys):
            return {"error": "Keep at least one report on the matrix."}
        settings.set_day_matrix_hidden(sorted(hidden))
        self._push_state()
        return {"ok": True, "hidden": sorted(hidden)}

    @_api_method
    def set_day_matrix_row_order(self, keys):
        """Persist the drag-to-reorder ROW order for the by-day matrix."""
        valid = {r["key"] for r in self._day_matrix_snapshot()["all_rows"]}
        clean = [k for k in (keys or []) if isinstance(k, str) and k in valid]
        settings.set_day_matrix_row_order(clean)
        self._push_state()
        return {"ok": True, "order": clean}

    def _ensure_day_column(self, date):
        """Make sure `date` is a day column, so an export's results show AND the
        chained compare can target it. Idempotent."""
        days = settings.get_day_matrix_days()
        if date not in days:
            settings.set_day_matrix_days(days + [date])

    @_api_method
    def export_day_column(self):
        """One-stop: export EVERY visible report for TODAY (the matrix source) into
        a dated run folder, then auto-consolidate + compare each vs TSN — the new
        column 'fills itself'. Only today is exportable (past columns are the
        immutable record you pulled). Needs a saved login; the export signs in."""
        snap = self._day_matrix_snapshot()
        today = snap["today"]
        self._ensure_day_column(today)
        job = self._make_job("export", "column", f"Export all reports — {today}",
                             env=today, which="day", fast=settings.get_matrix_fast())
        self._push_state()
        return self._enqueue_matrix_job(job)

    @_api_method
    def export_day_row(self, row_key):
        """Export ONE report for TODAY into the dated run folder, then compare it
        vs TSN (e.g. re-pull a single report for today)."""
        snap = self._day_matrix_snapshot()
        if row_key not in {r["key"] for r in snap["all_rows"]}:
            return {"error": "Unknown report for the matrix."}
        if not snap.get("row_supported", {}).get(row_key):
            return {"error": "That report has no TSN comparison yet."}
        today = snap["today"]
        self._ensure_day_column(today)
        job = self._make_job("export", "row",
                             f"Export {self._matrix_row_label(row_key)} — {today}",
                             row=row_key, env=today, which="day",
                             fast=settings.get_matrix_fast())
        self._push_state()
        return self._enqueue_matrix_job(job)

    @_api_method
    def export_day_cell(self, row_key, date):
        """Export ONE report for TODAY's cell, then compare vs TSN. Only today is
        exportable — a past date is rejected so its pull is preserved."""
        snap = self._day_matrix_snapshot()
        if row_key not in {r["key"] for r in snap["all_rows"]}:
            return {"error": "Unknown report for the matrix."}
        if not snap.get("row_supported", {}).get(row_key):
            return {"error": "That report has no TSN comparison yet."}
        if date != snap["today"]:
            return {"error": "Only today's column can be exported — earlier days "
                             "are kept as the record you pulled. Use the rebuild "
                             "action to re-compare a past day."}
        self._ensure_day_column(date)
        job = self._make_job("export", "cell",
                             f"Export {self._matrix_row_label(row_key)} — {date}",
                             row=row_key, env=date, which="day",
                             fast=settings.get_matrix_fast())
        self._push_state()
        return self._enqueue_matrix_job(job)

    @_api_method
    def build_day_cell(self, row_key, date):
        """Queue a (re)build of ONE (report, day) vs-TSN comparison."""
        snap = self._day_matrix_snapshot()
        if row_key not in {r["key"] for r in snap["all_rows"]}:
            return {"error": "Unknown report for the matrix."}
        if not snap.get("row_supported", {}).get(row_key):
            return {"error": "That comparison isn't available yet for this report."}
        if date not in snap["days"]:
            return {"error": "Add that day first."}
        # CMP-AUD-103: refuse a known-missing input up front (the export or the TSN
        # dataset), naming the absent role — never dispatch a doomed compare.
        cmp = snap["cells"].get(row_key, {}).get(date, {}).get("cmp")
        reason = matrix.cell_unbuildable_reason(cmp)
        if reason:
            return {"error": reason}
        job = self._make_job("compare", "cell",
                             self._day_job_label("cell", row_key, date),
                             row=row_key, env=date, which="day")
        return self._enqueue_matrix_job(job)

    @_api_method
    def day_matrix_evidence_cell(self, row_key, date):
        """Queue an ON-DEMAND evidence run for ONE by-day cell's EXISTING vs-TSN
        comparison — images only, no re-compare (runs even with the Evidence
        images toggle off)."""
        snap = self._day_matrix_snapshot()
        if row_key not in {r["key"] for r in snap["all_rows"]}:
            return {"error": "Unknown report for the matrix."}
        if not snap.get("row_supported", {}).get(row_key):
            return {"error": "That comparison isn't available yet for this report."}
        if date not in snap["days"]:
            return {"error": "Add that day first."}
        import visual_evidence                       # lazy: pulls PIL/pdfium
        if not visual_evidence.capable(row_key):
            return {"error": "This report doesn't support evidence images."}
        job = self._make_job(
            "evidence", "cell",
            f"Evidence images {self._matrix_row_label(row_key)} — {date}",
            row=row_key, env=date, which="day")
        job["evidence"] = self._capture_evidence_identity("day")
        return self._enqueue_matrix_job(job)

    @_api_method
    def rebuild_day_matrix(self, scope="stale", row=None, date=None, force=False):
        """Queue a by-day comparison rebuild in scope ('stale'/'all'), optionally
        scoped to one report row or one day column. `force` also rebuilds the day's
        persistent consolidated workbook ('refresh consolidated'). {nothing:True}
        only when idle, not forced, and there's nothing to do."""
        snap = self._day_matrix_snapshot()
        scope = scope if scope in ("stale", "all") else "stale"
        # CMP-AUD-096: reject a supplied-but-invalid row/day rather than widening
        # the request to the whole matrix (an absent filter still means everything).
        if row and row not in {r["key"] for r in snap["all_rows"]}:
            return {"error": "Unknown report row for the rebuild."}
        if date and date not in snap["days"]:
            return {"error": "Unknown day for the rebuild."}
        row = row or None
        date = date or None
        job_scope = "row" if row else "column" if date else scope
        with self._lock:
            idle = not self._task and not self._queue
        if idle:
            # CMP-AUD-093: force short-circuits on zero targets too. With no
            # comparable cell (e.g. an export but no TSN) there is nothing to
            # (re)consolidate either — the persistent consolidated is built per
            # comparable cell — so enqueuing a forced job would resolve zero cells
            # and drain silently. Force probes ALL cells (it rebuilds even fresh
            # ones); a plain refresh probes only the requested (stale) scope.
            probe_scope = "all" if force else scope
            cells = day_matrix.cells_to_rebuild(snap, scope=probe_scope,
                                                row=row, date=date)
            if not cells:
                return {"ok": True, "nothing": True}
        job = self._make_job("compare", job_scope,
                             self._day_job_label(job_scope, row, date),
                             row=row, env=date, which="day", force=force)
        return self._enqueue_matrix_job(job)

    @_api_method
    def open_day_cell_comparison(self, row_key, date):
        """Open ONE by-day comparison VALUES workbook."""
        snap = self._day_matrix_snapshot()
        if date not in snap["days"] or row_key not in snap["rows"]:
            return {"error": "Unknown cell."}
        path = day_matrix.day_out_path(date, snap["source"], row_key)
        if not path.exists():
            return {"error": "No comparison built yet — use “⟳ rebuild” first."}
        self._open_file(path)
        return {"ok": True}

    @_api_method
    def open_day_comparisons_folder(self):
        """Open the by-day comparison store (output/comparisons/tsn-by-day/)."""
        self._open_folder(day_matrix.byday_root())
        return {"ok": True}

    @_api_method
    def open_tsn_library_folder(self):
        """Open the canonical TSN library root (each report's raw + consolidated
        TSN data lives in <root>/<report>/). Seeds the per-report folders + hint
        files first so the user always lands on a populated, self-documenting
        tree (not an empty folder)."""
        import tsn_library                              # lazy import (tsn_library pulls pdfplumber via report_catalog)
        root = tsn_library.ensure_layout()
        self._open_folder(root)
        return {"ok": True}

    # ----- Compare-tab "vs Baseline" matrix -----------------------------------
    def _baseline_matrix_snapshot(self):
        """The vs-Baseline snapshot with the user's source / day columns /
        baseline / hidden rows applied (dest = the Everything matrix's
        batch_dest — the "store" baseline lives under it)."""
        return baseline_matrix.baseline_matrix_snapshot(
            settings.get_baseline_matrix_source(),
            settings.get_baseline_matrix_days(),
            settings.get_baseline_matrix_baseline() or None,
            hidden=settings.get_baseline_matrix_hidden(),
            dest=settings.get_batch_dest(),
            row_order=settings.get_baseline_matrix_row_order())

    def _baseline_job_label(self, scope, row=None, date=None):
        rl = self._matrix_row_label(row) if row else None
        if scope == "cell":
            return f"Rebuild {rl} — {date} vs baseline"
        if scope == "row":
            return f"Rebuild {rl} — all days vs baseline"
        if scope == "column":
            return f"Rebuild all reports — {date} vs baseline"
        if scope == "stale":
            return "Refresh stale vs-baseline comparisons"
        return "Rebuild all vs-baseline comparisons"

    @_api_method
    def baseline_matrix_info(self):
        """The vs-Baseline matrix snapshot for the Compare tab — a pure
        filesystem read plus the add-day picker's available days and the
        baseline picker's options (store + exported days, each with how many
        reports it covers)."""
        snap = self._baseline_matrix_snapshot()
        snap["available_days"] = baseline_matrix.available_days(snap["source"])
        snap["baseline_options"] = baseline_matrix.baseline_options(
            snap["source"], settings.get_batch_dest())
        self._push_state()
        return snap

    @_api_method
    def set_baseline_matrix_source(self, source):
        """Set the vs-Baseline matrix data source (both sides live within it)."""
        if source not in baseline_matrix.sources():
            return {"error": "Unknown data source."}
        settings.set_baseline_matrix_source(source)
        # CMP-AUD-095: reconcile the source-scoped day columns AND the baseline id
        # against the new source — a switch can otherwise leave either pointing at
        # folders that don't exist for it (a later build then aims at nothing). Keep
        # only the days that have an export for the new source, and clear the baseline
        # unless it's still a valid option there.
        avail = set(baseline_matrix.available_days(source))
        settings.set_baseline_matrix_days(
            [d for d in settings.get_baseline_matrix_days() if d in avail])
        valid_ids = {o["id"] for o in baseline_matrix.baseline_options(
            source, settings.get_batch_dest())}
        if settings.get_baseline_matrix_baseline() not in valid_ids:
            settings.set_baseline_matrix_baseline("")
        self._emit_log("vs-Baseline matrix source set to "
                       f"{matrix.default_env_label(source)}.")
        self._push_state()
        return {"ok": True, "source": source}

    @_api_method
    def set_baseline_matrix_baseline(self, baseline_id):
        """Persist the picked baseline ("store" / "day:<date>"; empty clears).
        Validated against the current picker options so a stale/typo id can't
        aim a comparison at a non-existent folder."""
        baseline_id = (baseline_id or "").strip()
        if baseline_id:
            source = settings.get_baseline_matrix_source()
            valid = {o["id"] for o in baseline_matrix.baseline_options(
                source, settings.get_batch_dest())}
            if baseline_id not in valid:
                return {"error": "That baseline has no exports for this source."}
        settings.set_baseline_matrix_baseline(baseline_id)
        if baseline_id:
            self._emit_log("vs-Baseline matrix baseline set to "
                           f"{baseline_matrix.baseline_label(settings.get_baseline_matrix_source(), baseline_id)}.")
        self._push_state()
        return {"ok": True, "baseline": baseline_id}

    @_api_method
    def add_baseline_matrix_day(self, date):
        """Add a day COLUMN: a date with an export for the source."""
        if date not in baseline_matrix.available_days(
                settings.get_baseline_matrix_source()):
            return {"error": "That day has no export for this source (only "
                             "exported days can be added)."}
        days = settings.get_baseline_matrix_days()
        if date not in days:
            settings.set_baseline_matrix_days(days + [date])
        self._push_state()
        return {"ok": True, "days": settings.get_baseline_matrix_days()}

    @_api_method
    def remove_baseline_matrix_day(self, date):
        """Remove a day column."""
        settings.set_baseline_matrix_days(
            [d for d in settings.get_baseline_matrix_days() if d != date])
        self._push_state()
        return {"ok": True, "days": settings.get_baseline_matrix_days()}

    @_api_method
    def set_baseline_matrix_report(self, row_key, visible):
        """Show/hide a report ROW on the vs-Baseline matrix. At least one stays on."""
        keys = {r["key"] for r in self._baseline_matrix_snapshot()["all_rows"]}
        if row_key not in keys:
            return {"error": "Unknown report for the matrix."}
        hidden = set(settings.get_baseline_matrix_hidden())
        if visible:
            hidden.discard(row_key)
        else:
            hidden.add(row_key)
        if len(hidden & keys) >= len(keys):
            return {"error": "Keep at least one report on the matrix."}
        settings.set_baseline_matrix_hidden(sorted(hidden))
        self._push_state()
        return {"ok": True, "hidden": sorted(hidden)}

    @_api_method
    def set_baseline_matrix_row_order(self, keys):
        """Persist the drag-to-reorder ROW order for the vs-Baseline matrix."""
        valid = {r["key"] for r in self._baseline_matrix_snapshot()["all_rows"]}
        clean = [k for k in (keys or []) if isinstance(k, str) and k in valid]
        settings.set_baseline_matrix_row_order(clean)
        self._push_state()
        return {"ok": True, "order": clean}

    @_api_method
    def set_baseline_matrix_formulas(self, on):
        """Toggle the vs-Baseline matrix's OWN live-formulas option (persisted,
        independent of the other matrices')."""
        val = settings.set_baseline_matrix_formulas(bool(on))
        self._emit_log("vs-Baseline live-formulas workbook " + ("on" if val else "off")
                       + (" — each comparison also writes a '… (formulas).xlsx'."
                          if val else "."))
        self._push_state()
        return {"ok": True, "on": val}

    @_api_method
    def build_baseline_matrix_cell(self, row_key, date):
        """Queue a (re)build of ONE (report, day) vs-baseline comparison."""
        snap = self._baseline_matrix_snapshot()
        if row_key not in {r["key"] for r in snap["all_rows"]}:
            return {"error": "Unknown report for the matrix."}
        if not snap.get("row_supported", {}).get(row_key):
            return {"error": "That comparison isn't available yet for this report."}
        if date not in snap["days"]:
            return {"error": "Add that day first."}
        if not snap["baseline"]["id"]:
            return {"error": "Pick a baseline first."}
        if snap["baseline"]["date"] == date:
            return {"error": "That day IS the baseline — nothing to compare."}
        # CMP-AUD-103: refuse a known-missing input up front (this day's export or
        # the baseline's), naming the absent role — never dispatch a doomed compare.
        cmp = snap["cells"].get(row_key, {}).get(date, {}).get("cmp")
        reason = matrix.cell_unbuildable_reason(cmp)
        if reason:
            return {"error": reason}
        job = self._make_job("compare", "cell",
                             self._baseline_job_label("cell", row_key, date),
                             row=row_key, env=date, which="baseline")
        return self._enqueue_matrix_job(job)

    @_api_method
    def rebuild_baseline_matrix(self, scope="stale", row=None, date=None):
        """Queue a vs-Baseline comparison rebuild in scope ('stale'/'all'),
        optionally scoped to one report row or one day column. {nothing:True}
        only when idle and there's nothing to do."""
        snap = self._baseline_matrix_snapshot()
        if not snap["baseline"]["id"]:
            return {"error": "Pick a baseline first."}
        scope = scope if scope in ("stale", "all") else "stale"
        # CMP-AUD-096: reject a supplied-but-invalid row/day rather than widening
        # the request to the whole matrix (an absent filter still means everything).
        if row and row not in {r["key"] for r in snap["all_rows"]}:
            return {"error": "Unknown report row for the rebuild."}
        if date and date not in snap["days"]:
            return {"error": "Unknown day for the rebuild."}
        row = row or None
        date = date or None
        job_scope = "row" if row else "column" if date else scope
        with self._lock:
            idle = not self._task and not self._queue
        if idle:
            cells = baseline_matrix.cells_to_rebuild(snap, scope=scope,
                                                     row=row, date=date)
            if not cells:
                return {"ok": True, "nothing": True}
        job = self._make_job("compare", job_scope,
                             self._baseline_job_label(job_scope, row, date),
                             row=row, env=date, which="baseline")
        return self._enqueue_matrix_job(job)

    @_api_method
    def open_baseline_cell_comparison(self, row_key, date):
        """Open ONE vs-Baseline comparison VALUES workbook."""
        snap = self._baseline_matrix_snapshot()
        if date not in snap["days"] or row_key not in snap["rows"]:
            return {"error": "Unknown cell."}
        baseline_id = snap["baseline"]["id"]
        if not baseline_id:
            return {"error": "Pick a baseline first."}
        path = baseline_matrix.out_path(date, snap["source"], row_key, baseline_id)
        if not path.exists():
            return {"error": "No comparison built yet — use “⟳ rebuild” first."}
        self._open_file(path)
        return {"ok": True}

    @_api_method
    def open_baseline_comparisons_folder(self):
        """Open the vs-Baseline comparison store (output/comparisons/baseline-by-day/)."""
        self._open_folder(baseline_matrix.byday_root())
        return {"ok": True}

    def _on_matrix_cell(self, payload):
        with self._lock:
            if self._matrix is not None:
                self._matrix = {**self._matrix,
                                "row": payload.get("row"),
                                "cell": payload.get("cell"),
                                "done": payload.get("done", 0),
                                "total": payload.get("total", 0)}
        self._push_state()

    def _on_matrix_done(self, payload):
        done, total = payload.get("done", 0), payload.get("total", 0)
        errs = payload.get("errors", 0)
        # CMP-AUD-089: report what actually happened per cell. "N of M done" alone
        # counted a cancelled or crashed cell as done; the worker now separates
        # attempted / succeeded / failed / cancelled / partial and the terminal
        # line names each non-zero bucket.
        parts = []
        for label, key in (("succeeded", "succeeded"), ("failed", "failed"),
                           ("cancelled", "cancelled_cells"),
                           ("incomplete", "partial_cells")):
            n = payload.get(key)
            if isinstance(n, int) and n:
                parts.append(f"{n} {label}")
        attempted = payload.get("attempted")
        unclean = any(payload.get(k) for k in
                      ("failed", "cancelled_cells", "partial_cells"))
        if isinstance(attempted, int) and unclean:
            stopped = ("Comparison run stopped" if payload.get("cancelled")
                       else "Comparison run finished")
            self._emit_log(f"{stopped} — {attempted} of {total} attempted: "
                           + ", ".join(parts) + " (see the log).")
        elif payload.get("cancelled"):
            self._emit_log(f"Comparison run stopped — {done} of {total} done.")
        elif errs:
            self._emit_log(f"Comparison run finished — {done} of {total} done; "
                           f"{errs} could not be built (see the log).")
        else:
            self._emit_log(f"Comparison run finished — {done} of {total} done.")
        # Nudge only when the WHOLE queue has drained (not after every auto-
        # advancing job), matching exports/consolidations honoring notify_on_finish.
        if not self._queue:
            self._flash_taskbar()
        self._end_task()
        self._emit({"t": "matrix_refresh"})

    def _on_matrix_export_done(self, payload):
        done, total = payload.get("count", 0), payload.get("total", 0)
        if payload.get("cancelled"):
            self._emit_log(f"Re-export stopped — {done} of {total} done.")
        elif payload.get("ok"):
            self._emit_log(f"Re-export finished — {done} of {total} done.")
        else:
            self._emit_log(f"Re-export finished — {done} of {total} done "
                           "(some did not complete; see the log).")
        with self._lock:
            if not self._authed:
                self._device_ok = True   # the run signed itself in (device mode)
            cur = self._current_job      # capture before _end_task clears it
        # By-day export -> auto-chain the consolidate+compare for the SAME scope, so
        # a new column "fills itself" (export -> consolidate -> compare vs TSN) in
        # one action. Skipped on cancel, and (§C.1) only when the export was
        # COMPLETE: a partial/failed refresh kept last-good (F1), so auto-comparing
        # it would diff stale data and read as freshly built.
        chain = None
        if (cur and cur.get("which") == "day" and cur.get("kind") == "export"
                and not payload.get("cancelled") and payload.get("ok")):
            cscope = "cell" if cur["scope"] == "cell" else (
                "row" if cur["scope"] == "row" else "all")
            chain = self._make_job(
                "compare", cscope,
                self._day_job_label("column" if cscope == "all" else cscope,
                                    cur.get("row"), cur.get("env")),
                row=cur.get("row"), env=cur.get("env"), which="day")
        if not self._queue and chain is None:   # flash once the queue is fully drained
            self._flash_taskbar()
        self._end_task()
        if chain is not None:
            self._enqueue_matrix_job(chain)
        self._emit({"t": "matrix_refresh"})
