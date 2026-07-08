"""The matrix GUI workers (S2 / ARC-02, split from gui_worker.py).

_run_matrix_export_step (one manifest-free report+env export) and the four
matrix job workers: MatrixBatchExportWorker, MatrixCompareWorker,
DayMatrixCompareWorker, MatrixTsnConsolidateWorker. Verbatim moves;
gui_worker re-exports.
"""
import logging
import threading
from pathlib import Path

import owned_dir
import day_matrix
import matrix
import outcome
from common import AuthError, BrowserNotFoundError, get_site, set_site
from events import Events
from gui_worker_export import ExportWorker

log = logging.getLogger("tsmis.gui")

def _run_matrix_export_step(spec, src, env, dest, queue, cancel, skip, pause,
                            workers, on_worker=None, dated=False):
    """Export ONE report for ONE environment, WITHOUT a manifest (so a matrix
    refresh can never clobber a paused Export-Everything batch — BatchWorker alone
    persists batch_job.json). Runs the SAME per-environment body BatchWorker uses
    (set_site + an ExportWorker); fast mode runs N browsers. The caller
    sets/restores the process-global site. Auth / browser failures raise up to the
    batch loop, which stops the run. `on_worker(ew|None)` exposes the live
    ExportWorker to the bridge for the duration of the step (so live screenshot
    previews work, just like a normal export).

    `dated=False` -> the Everything store (`<dest>/<src-env>/<subdir>`, env-tagged
    names). `dated=True` (the Compare by-day matrix) -> out_base=None, so the
    ExportWorker writes a normal DATED run folder `output/<today> <src-env>/
    <subdir>/` with plain route names — the immutable per-day pull the by-day
    matrix consolidates + compares vs TSN. Only today can be exported (run_export
    always names the folder for today)."""
    set_site(src, env)
    out_base = None if dated else Path(dest) / f"{src}-{env}"
    ew = ExportWorker([spec], queue, cancel, skip, workers=workers, routes=None,
                      pause_event=pause, auto_consolidate=False, out_base=out_base)
    if on_worker:
        on_worker(ew)
    results = []
    try:
        ew._run_specs(ew._build_events(), results)
    finally:
        if on_worker:
            on_worker(None)
    # A step counts as "complete" for the matrix only if its export covered
    # everything (no failed/skipped/no-data routes). The F1 swap in _run_specs
    # already kept last-good for a partial/failed refresh; this just lets the
    # matrix report ok / auto-chain a compare on COMPLETE only (§C.1).
    return bool(results) and all(
        outcome.promotable(r.completion or outcome.run_completion(r, cancelled=cancel.is_set()))
        for _s, r in results)


class MatrixBatchExportWorker(threading.Thread):
    """Refresh a SET of (report, env) cells into the Export-Everything store — the
    matrix's live re-export of a single cell (1 step), a whole ROW (one report ×
    every visible env) or a whole COLUMN (every report × one env).

    Each step runs manifest-free via _run_matrix_export_step (so it can't disturb
    a paused Export-Everything batch); steps run sequentially, and fast mode runs
    N browsers PER step. Honors cancel between steps. Posts the reused export
    log/progress, then ('matrix_export_done', {count, total, ok, cancelled}). An
    auth / browser failure stops the batch and posts ('error', …) — the bridge
    then clears the queue (auth) or advances (general). The process-global site is
    restored at the end."""

    def __init__(self, steps, dest, queue, cancel_event, skip_event, pause_event,
                 workers=1, on_worker=None, dated=False):
        super().__init__(daemon=True, name="matrix-batch-export")
        self.steps = list(steps)               # [(spec, src, env), ...]
        self.dest = dest
        self.q = queue
        self.cancel = cancel_event
        self.skip = skip_event
        self.pause = pause_event
        self.workers = workers
        self.on_worker = on_worker             # exposes the live ExportWorker for preview
        # dated=True -> the Compare by-day matrix: write DATED run folders
        # (output/<today> <src-env>/) instead of the always-current Everything store.
        self.dated = bool(dated)

    def run(self):
        original = get_site()
        total = len(self.steps)
        done = ok = 0
        posted = False           # an AuthError already drove the terminal transition
        try:
            for spec, src, env in self.steps:
                if self.cancel.is_set():
                    break
                if total > 1:
                    self.q.put(("log", f"Re-exporting {spec.label} — {src}-{env} "
                                       f"({done + 1} of {total})…"))
                try:
                    if _run_matrix_export_step(spec, src, env, self.dest, self.q,
                                               self.cancel, self.skip, self.pause,
                                               self.workers, on_worker=self.on_worker,
                                               dated=self.dated):
                        ok += 1                  # complete only (§C.1), not "didn't raise"
                except (AuthError, BrowserNotFoundError) as e:
                    log.warning("matrix export %s-%s stopped: %s: %s",
                                src, env, type(e).__name__, e)
                    self.q.put(("error",
                                ("auth" if isinstance(e, AuthError) else "general",
                                 str(e))))
                    posted = True
                    return                       # stop the batch (terminal via _on_error)
                except Exception as e:           # noqa: BLE001
                    log.exception("matrix export %s-%s crashed", src, env)
                    self.q.put(("log", f"  {spec.label} / {src}-{env}: "
                                       f"{type(e).__name__}: {e}"))
                done += 1
        finally:
            set_site(*original)
            # Post the terminal event from finally so an UNEXPECTED escape (e.g. a
            # crash outside the per-step handlers) can never leave the single-task
            # gate wedged with the queue stuck — matching the sibling matrix workers.
            if not posted:
                self.q.put(("matrix_export_done",
                            {"count": done, "total": total, "ok": ok == total,
                             "cancelled": self.cancel.is_set()}))


class MatrixCompareWorker(threading.Thread):
    """(Re)build matrix cell comparisons for each cell's SELECTED mode.

    `cells` is a list of (row_key, cell_key, mode_id) — one entry for a single
    cell, or many for a per-row / per-column / 'refresh all' recompute. No browser
    — pure orchestration via matrix.build_comparison over the existing comparison
    adapters (cross-env -> comparisons/<baseline>/; TSN/self -> comparisons/tsn/).
    Honors cancel BETWEEN cells (each finished cell is saved, so a cancelled run
    resumes idempotently). Posts ('matrix_cell', {...}) around each cell and
    ('matrix_done', {...}) at the end."""

    def __init__(self, dest, baseline, cells, queue, cancel_event, tsn_files=None,
                 force_consolidate=False, also_formulas=False, evidence=None):
        super().__init__(daemon=True, name="matrix-compare")
        self.dest = dest
        self.baseline = baseline
        # accept 2-tuples (legacy, env mode) or 3-tuples (row, cell, mode)
        self.cells = [(c[0], c[1], c[2] if len(c) > 2 else "env") for c in cells]
        self.q = queue
        self.cancel = cancel_event
        self.tsn_files = tsn_files or {}
        self.force_consolidate = force_consolidate
        self.also_formulas = also_formulas
        self.evidence = evidence

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        # M03: the comparisons tree the matrix writes under the user-chosen
        # destination is app-created — stamp it owned (by marker, not by name).
        if self.dest:
            owned_dir.ensure_owned_dir(Path(self.dest) / matrix.COMPARISONS_DIRNAME,
                                       kind="comparisons")
        total = len(self.cells)
        done = errors = 0
        try:
            for row_key, cell_key, mode_id in self.cells:
                if self.cancel.is_set():
                    break
                self.q.put(("matrix_cell", {"row": row_key, "cell": cell_key,
                                            "status": "running",
                                            "done": done, "total": total}))
                try:
                    res = matrix.build_comparison(
                        self.dest, row_key, cell_key, mode_id, self.baseline,
                        events=events, tsn_files=self.tsn_files,
                        force_consolidate=self.force_consolidate,
                        also_formulas=self.also_formulas, evidence=self.evidence)
                    status = res.status
                    if status != "ok":
                        errors += 1
                        self.q.put(("log", f"  {cell_key} {row_key}: {res.message}"))
                except Exception as e:                   # noqa: BLE001
                    log.exception("matrix compare %s/%s/%s crashed", row_key, cell_key, mode_id)
                    status, errors = "error", errors + 1
                    self.q.put(("log", f"  {cell_key} {row_key}: "
                                       f"{type(e).__name__}: {e}"))
                done += 1
                self.q.put(("matrix_cell", {"row": row_key, "cell": cell_key,
                                            "status": status,
                                            "done": done, "total": total}))
        finally:
            self.q.put(("matrix_done", {"done": done, "total": total,
                                        "errors": errors,
                                        "cancelled": self.cancel.is_set()}))


class DayMatrixCompareWorker(threading.Thread):
    """(Re)build Compare-tab "TSN by day" cells — each a (day, report) vs TSN.

    `cells` is a list of (date, row_key). No browser — pure orchestration via
    day_matrix.build_day_cell over the SHARED TSN compare path (the same untouched
    consolidate_*/compare_highway_log[_pdf] adapters the Everything matrix uses).
    Honors cancel BETWEEN cells (each finished cell is saved). Posts
    ('matrix_cell', {...}) around each cell and ('matrix_done', {...}) at the end —
    reusing the Everything matrix's progress events so the bridge handles both."""

    def __init__(self, source, cells, dest, queue, cancel_event, tsn_files=None,
                 force_consolidate=False, also_formulas=False, evidence=None):
        super().__init__(daemon=True, name="day-matrix-compare")
        self.source = source
        self.cells = [(c[0], c[1]) for c in cells]   # (date, row_key)
        self.dest = dest
        self.q = queue
        self.cancel = cancel_event
        self.tsn_files = tsn_files or {}
        self.force_consolidate = force_consolidate
        self.also_formulas = also_formulas
        self.evidence = evidence

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        # M03: the comparisons/tsn tree the by-day matrix writes under the
        # user-chosen destination is app-created — stamp it owned.
        if self.dest:
            owned_dir.ensure_owned_dir(Path(self.dest) / matrix.COMPARISONS_DIRNAME,
                                       kind="comparisons")
        total = len(self.cells)
        done = errors = 0
        try:
            for date, row_key in self.cells:
                if self.cancel.is_set():
                    break
                self.q.put(("matrix_cell", {"row": row_key, "cell": date,
                                            "status": "running",
                                            "done": done, "total": total}))
                try:
                    res = day_matrix.build_day_cell(
                        self.source, date, row_key, self.dest, events,
                        tsn_files=self.tsn_files,
                        force_consolidate=self.force_consolidate,
                        also_formulas=self.also_formulas, evidence=self.evidence)
                    status = res.status
                    if status != "ok":
                        errors += 1
                        self.q.put(("log", f"  {date} {row_key}: {res.message}"))
                except Exception as e:                   # noqa: BLE001
                    log.exception("day matrix compare %s/%s crashed", date, row_key)
                    status, errors = "error", errors + 1
                    self.q.put(("log", f"  {date} {row_key}: "
                                       f"{type(e).__name__}: {e}"))
                done += 1
                self.q.put(("matrix_cell", {"row": row_key, "cell": date,
                                            "status": status,
                                            "done": done, "total": total}))
        finally:
            self.q.put(("matrix_done", {"done": done, "total": total,
                                        "errors": errors,
                                        "cancelled": self.cancel.is_set()}))


class MatrixEvidenceWorker(threading.Thread):
    """Run the ON-DEMAND evidence generation for ONE cell's EXISTING vs-TSN
    comparison (either matrix — the caller pre-binds the resolver). No browser,
    no consolidation, no compare: matrix.evidence_for_cell /
    day_matrix.evidence_for_day_cell gate on freshness and then render the
    evidence set beside the comparison workbook. Posts the same
    ('matrix_cell', …) / ('matrix_done', …) events as the compare workers so
    the bridge lifecycle is identical."""

    def __init__(self, run_fn, row_key, cell_label, queue, cancel_event):
        super().__init__(daemon=True, name="matrix-evidence")
        self.run_fn = run_fn                   # (events) -> ConsolidateResult
        self.row_key = row_key
        self.cell_label = cell_label           # env key or date (display only)
        self.q = queue
        self.cancel = cancel_event

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        errors = 0
        self.q.put(("matrix_cell", {"row": self.row_key, "cell": self.cell_label,
                                    "status": "running", "done": 0, "total": 1}))
        try:
            res = self.run_fn(events)
            status = res.status
            if status != "ok":
                errors = 1
                self.q.put(("log", f"  {self.cell_label} {self.row_key}: {res.message}"))
        except Exception as e:                       # noqa: BLE001
            log.exception("matrix evidence %s/%s crashed", self.row_key, self.cell_label)
            status, errors = "error", 1
            msg = str(e).splitlines()[0] if str(e) else type(e).__name__
            self.q.put(("log", f"  evidence images — {msg}"))
        finally:
            self.q.put(("matrix_cell", {"row": self.row_key, "cell": self.cell_label,
                                        "status": "error" if errors else "ok",
                                        "done": 1, "total": 1}))
            self.q.put(("matrix_done", {"done": 1 - errors, "total": 1,
                                        "errors": errors,
                                        "cancelled": self.cancel.is_set()}))


class MatrixTsnConsolidateWorker(threading.Thread):
    """Consolidate the district TSN PDFs the user dropped in _tsn_input/<subdir>/
    into one TSN workbook (the 'consolidate these PDFs?' prompt path), so the TSN
    comparison can run. Offline (pdfplumber); posts ('matrix_done', …) so the
    bridge clears the task and refreshes the grid."""

    def __init__(self, dest, subdir, queue, cancel_event):
        super().__init__(daemon=True, name="matrix-tsn-consolidate")
        self.dest = dest
        self.subdir = subdir
        self.q = queue
        self.cancel = cancel_event

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        errors = 0
        try:
            res = matrix.consolidate_tsn_pdfs(self.dest, self.subdir, events=events)
            self.q.put(("log", f"TSN workbook ready: {res}"))
        except Exception as e:                       # noqa: BLE001
            errors = 1
            log.exception("matrix TSN consolidate (%s) crashed", self.subdir)
            self.q.put(("log", f"TSN consolidation failed ({type(e).__name__}): {e}"))
        finally:
            self.q.put(("matrix_done", {"done": 1 - errors, "total": 1,
                                        "errors": errors,
                                        "cancelled": self.cancel.is_set()}))
