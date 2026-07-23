"""The matrix GUI workers (S2 / ARC-02, split from gui_worker.py).

_run_matrix_export_step (one manifest-free report+env export) and the matrix
job workers: MatrixBatchExportWorker, MatrixCompareWorker,
DayMatrixCompareWorker, BaselineMatrixCompareWorker,
MatrixTsnConsolidateWorker. Verbatim moves; gui_worker re-exports.
"""
import logging
import threading
import time
from pathlib import Path

import owned_dir
import baseline_matrix
import compare_timings
import day_matrix
import matrix
import outcome
from common import AuthError, BrowserNotFoundError, get_site, set_site
from events import Events
from gui_worker_export import ExportWorker

log = logging.getLogger("tsmis.gui")


def _fmt_dur(seconds):
    """Compact human duration for a log/ETA line: '4s', '1m20s', '2m'."""
    s = int(round(seconds or 0))
    if s < 60:
        return f"{s}s"
    m, sec = divmod(s, 60)
    return f"{m}m{sec}s" if sec else f"{m}m"


def _cell_done_line(row_key, cell_key, mode_id, attempt, why, dur):
    """The one structured per-cell outcome line (M1-B): a glyph, the cell's full
    identity, how long it took, and — on anything but a clean success — exactly
    what went wrong. One log read reconstructs a whole run."""
    where = f"{row_key} · {cell_key} ({mode_id})"
    took = _fmt_dur(dur)
    if attempt == matrix.ATTEMPT_OK:
        return f"  ✓ {where} — done in {took}"
    if attempt == "cancelled":
        return f"  ■ {where} — stopped after {took}"
    verb = "incomplete" if attempt == "partial" else "failed"
    glyph = "⚠" if attempt == "partial" else "✗"
    tail = f": {why}" if why else ""
    return f"  {glyph} {where} — {verb} in {took}{tail}"


class _RunClock:
    """Per-run cell timing + a best-effort ETA over an ordered timing-key list
    (M1-B). `keys[i]` is the "<row>|<mode>" of the i-th cell; each finished cell
    feeds the durable history so later runs (and the rest of THIS run, via the
    running-average fallback) estimate better. Diagnostic — never gates output."""

    def __init__(self, keys):
        self.keys = list(keys)
        self.done = 0
        self.elapsed = 0.0

    def start(self):
        return time.perf_counter()

    def finish(self, key, started):
        dur = max(0.0, time.perf_counter() - started)
        self.elapsed += dur
        self.done += 1
        compare_timings.record(key, dur)
        return dur

    def eta_seconds(self):
        avg = self.elapsed / self.done if self.done else None
        return compare_timings.estimate_seconds(self.keys[self.done:], fallback=avg)

    def progress_extra(self):
        """The {elapsed_s, eta_s?} the UI shows beside 'Comparing done/total'."""
        out = {"elapsed_s": round(self.elapsed, 1)}
        eta = self.eta_seconds()
        if eta is not None:
            out["eta_s"] = round(eta, 1)
        return out


# --------------------------------------------------------------------------- #
# CMP-AUD-089: every compare worker reports attempted / succeeded / failed /
# cancelled independently (they used to collapse into "done" + "errors", so a
# cancelled cell read as "1 of 1 done"), and persists the terminal state of each
# cell it touched into the durable last-attempt overlay. The overlay decorates
# the last-good cell; it never replaces the artifact's own truth.
# --------------------------------------------------------------------------- #
class _AttemptTally:
    """The per-run cell accounting shared by the three compare workers."""

    def __init__(self, total):
        self.total = total
        self.done = self.errors = 0
        self.attempted = self.succeeded = self.failed = 0
        self.cancelled_cells = self.partial_cells = 0

    def count(self, attempt_state):
        """Tally one finished cell by its ATTEMPT state, so a cancelled cell is
        never a success and an incomplete one is never a plain failure."""
        self.attempted += 1
        if attempt_state == matrix.ATTEMPT_OK:
            self.succeeded += 1
        elif attempt_state == "cancelled":
            self.cancelled_cells += 1
        elif attempt_state == "partial":
            self.partial_cells += 1
        else:
            self.failed += 1

    def payload(self, cancelled):
        return {"done": self.done, "total": self.total, "errors": self.errors,
                "cancelled": bool(cancelled), "attempted": self.attempted,
                "succeeded": self.succeeded, "failed": self.failed,
                "cancelled_cells": self.cancelled_cells,
                "partial_cells": self.partial_cells}


def _attempt_state(res, cancelled=False):
    """(overlay status, reason) for one finished cell. A cancelled cell is
    cancelled even though it surfaced as an exception; an ok-but-incomplete
    result is a first-class `partial` attempt, not a success."""
    if cancelled:
        return "cancelled", "the rebuild was stopped before it finished"
    if getattr(res, "status", None) != "ok":
        return "error", getattr(res, "message", "") or "the rebuild did not finish"
    if outcome.consolidate_completion_of(res) != outcome.COMPLETE:
        return "partial", (getattr(res, "message", "")
                           or "the rebuild compared incomplete inputs")
    return matrix.ATTEMPT_OK, ""


def _record_attempt(root, result_key, cell_key, status, reason,
                    commit_guard=None, error_type=None):
    """Persist one cell's attempt overlay. Best-effort by contract (matrix_state
    logs the why) — diagnostic state must never fail a published artifact."""
    if not root:
        return
    try:
        matrix.record_attempt(root, result_key, cell_key, status, reason=reason,
                              commit_guard=commit_guard, error_type=error_type)
    except Exception as e:                       # noqa: BLE001 - diagnostic only
        log.warning("matrix: attempt overlay for %s/%s not recorded (%s: %s)",
                    result_key, cell_key, type(e).__name__, e)


def _run_matrix_export_step(spec, src, env, dest, queue, cancel, skip, pause,
                            workers, on_worker=None, dated=False, day=None):
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
                      pause_event=pause, auto_consolidate=False, out_base=out_base,
                      day=day)          # CMP-AUD-091: captured run date for dated writes
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
                 workers=1, on_worker=None, dated=False, day=None):
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
        # (output/<day> <src-env>/) instead of the always-current Everything store.
        # CMP-AUD-091: `day` is the run date captured at dispatch — every step writes
        # that day's folder rather than re-resolving "today", so a midnight crossing
        # can't split the export or mismatch the chained comparison.
        self.dated = bool(dated)
        self.day = day or None

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
                                               dated=self.dated, day=self.day):
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
        tally = _AttemptTally(len(self.cells))
        total = tally.total
        clock = _RunClock([f"{row}|{mode}" for row, _cell, mode in self.cells])
        attempts_root = (matrix.comparisons_common_root(self.dest)
                         if self.dest else None)
        comparisons_lease = None
        store_lease = None
        ownership_loss_reported = False

        def _active_leases():
            return tuple(lease for lease in (comparisons_lease, store_lease)
                         if lease is not None)

        def _target_guard(path=None, *, anchor_path=None, anchor_identity=None,
                          directory_identity=None):
            """Authorize a mutation only under one of this cell's exact roots."""
            leases = _active_leases()
            if not leases or not all(lease.is_current() for lease in leases):
                return False
            if path is None:
                return True
            return any(lease.is_safe_descendant(
                path, anchor_path=anchor_path, anchor_identity=anchor_identity,
                directory_identity=directory_identity) for lease in leases)

        def _is_cancelled():
            nonlocal ownership_loss_reported
            if self.cancel.is_set():
                return True
            leases = _active_leases()
            if not leases or all(lease.is_current() for lease in leases):
                return False
            if not ownership_loss_reported:
                ownership_loss_reported = True
                self.q.put(("log", "  The comparisons destination changed while "
                                     "a cell was building. Its output will not be committed."))
            return True

        # Comparison engines poll this during long builds, and commit_workbook
        # receives the same exact-identity predicate for its final replace.
        events = Events(is_cancelled=_is_cancelled,
                        on_log=lambda m: self.q.put(("log", m)))
        try:
            # This is the one comparison worker that writes beneath the user's
            # configured Export-Everything destination.  Claim only for actual
            # work and stop before the builder on any pre-existing untrusted root.
            if self.dest and total and not self.cancel.is_set():
                comparisons_lease = owned_dir.require_owned_dir_lease(
                    Path(self.dest) / matrix.COMPARISONS_DIRNAME,
                    kind="comparisons")
            for row_key, cell_key, mode_id in self.cells:
                if self.cancel.is_set():
                    break
                store_lease = None
                if comparisons_lease is not None:
                    comparisons_lease.require_current(action="matrix build")
                self.q.put(("matrix_cell", {"row": row_key, "cell": cell_key,
                                            "status": "running",
                                            "done": tally.done, "total": total,
                                            **clock.progress_extra()}))
                self.q.put(("log", f"  ▸ comparing {row_key} · {cell_key} ({mode_id})…"))
                error_type = None
                started = clock.start()
                try:
                    # Cross-environment cells only publish beneath comparisons.
                    # TSN/self cells also persist consolidation artifacts into the
                    # cell's already app-created environment store; never create or
                    # adopt that root from the comparison path.
                    if self.dest and mode_id != "env":
                        store_lease = owned_dir.require_existing_owned_dir_lease(
                            Path(self.dest) / cell_key, kind="store")
                    res = matrix.build_comparison(
                        self.dest, row_key, cell_key, mode_id, self.baseline,
                        events=events, tsn_files=self.tsn_files,
                        force_consolidate=self.force_consolidate,
                        also_formulas=self.also_formulas, evidence=self.evidence,
                        commit_guard=(_target_guard
                                      if comparisons_lease is not None else None))
                    attempt, why = _attempt_state(res)
                    status = res.status
                    if status != "ok":
                        tally.errors += 1
                except Exception as e:                   # noqa: BLE001
                    log.exception("matrix compare %s/%s/%s crashed", row_key, cell_key, mode_id)
                    # A cell that raised because the run was stopped is CANCELLED,
                    # not failed — the distinction is the point of CMP-AUD-089.
                    cancelled_cell = self.cancel.is_set()
                    status = "cancelled" if cancelled_cell else "error"
                    tally.errors += 1
                    attempt, why = _attempt_state(None, cancelled=cancelled_cell)
                    if not cancelled_cell:
                        why = f"{type(e).__name__}: {e}"
                        error_type = type(e).__name__
                dur = clock.finish(f"{row_key}|{mode_id}", started)
                self.q.put(("log", _cell_done_line(row_key, cell_key, mode_id,
                                                   attempt, why, dur)))
                tally.count(attempt)
                _record_attempt(attempts_root, f"{row_key}|{mode_id}", cell_key,
                                attempt, why, error_type=error_type,
                                commit_guard=(_target_guard
                                              if comparisons_lease is not None
                                              else None))
                tally.done += 1
                self.q.put(("matrix_cell", {"row": row_key, "cell": cell_key,
                                            "status": status,
                                            "done": tally.done, "total": total,
                                            **clock.progress_extra()}))
        except owned_dir.OwnershipError as e:
            tally.errors = max(tally.errors, total - tally.done)
            self.q.put(("log", f"  Comparisons were not written: {e}"))
        finally:
            self.q.put(("matrix_done", {**tally.payload(self.cancel.is_set()),
                                        "elapsed_s": round(clock.elapsed, 1)}))


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
        # Day outputs live under OUTPUT_ROOT/comparisons/tsn-by-day. ``dest`` is
        # only source/store context, so it must never be claimed as output.
        tally = _AttemptTally(len(self.cells))
        total = tally.total
        clock = _RunClock([f"{row}|tsn" for _date, row in self.cells])
        attempts_root = day_matrix.byday_root()
        try:
            for date, row_key in self.cells:
                if self.cancel.is_set():
                    break
                self.q.put(("matrix_cell", {"row": row_key, "cell": date,
                                            "status": "running",
                                            "done": tally.done, "total": total,
                                            **clock.progress_extra()}))
                self.q.put(("log", f"  ▸ comparing {row_key} · {date} vs TSN…"))
                error_type = None
                started = clock.start()
                try:
                    res = day_matrix.build_day_cell(
                        self.source, date, row_key, self.dest, events,
                        tsn_files=self.tsn_files,
                        force_consolidate=self.force_consolidate,
                        also_formulas=self.also_formulas, evidence=self.evidence)
                    attempt, why = _attempt_state(res)
                    status = res.status
                    if status != "ok":
                        tally.errors += 1
                except Exception as e:                   # noqa: BLE001
                    log.exception("day matrix compare %s/%s crashed", date, row_key)
                    cancelled_cell = self.cancel.is_set()
                    status = "cancelled" if cancelled_cell else "error"
                    tally.errors += 1
                    attempt, why = _attempt_state(None, cancelled=cancelled_cell)
                    if not cancelled_cell:
                        why = f"{type(e).__name__}: {e}"
                        error_type = type(e).__name__
                dur = clock.finish(f"{row_key}|tsn", started)
                self.q.put(("log", _cell_done_line(row_key, date, "tsn",
                                                   attempt, why, dur)))
                tally.count(attempt)
                _record_attempt(attempts_root, f"{row_key}|{self.source}", date,
                                attempt, why, error_type=error_type)
                tally.done += 1
                self.q.put(("matrix_cell", {"row": row_key, "cell": date,
                                            "status": status,
                                            "done": tally.done, "total": total,
                                            **clock.progress_extra()}))
        finally:
            self.q.put(("matrix_done", {**tally.payload(self.cancel.is_set()),
                                        "elapsed_s": round(clock.elapsed, 1)}))


class BaselineMatrixCompareWorker(threading.Thread):
    """(Re)build Compare-tab "vs Baseline" cells — each a (day, report) vs the
    picked baseline (an earlier run folder, or the Everything store).

    `cells` is a list of (date, row_key). No browser, no consolidation, no TSN
    dataset — pure orchestration via baseline_matrix.build_baseline_cell (the
    row's own compare_env adapter reads the per-route files straight from both
    folders). Honors cancel BETWEEN cells (each finished cell is saved). Posts
    the same ('matrix_cell', …) / ('matrix_done', …) events as the other
    compare workers so the bridge lifecycle is identical."""

    def __init__(self, source, cells, baseline_id, dest, queue, cancel_event,
                 also_formulas=False):
        super().__init__(daemon=True, name="baseline-matrix-compare")
        self.source = source
        self.cells = [(c[0], c[1]) for c in cells]   # (date, row_key)
        self.baseline_id = baseline_id
        self.dest = dest
        self.q = queue
        self.cancel = cancel_event
        self.also_formulas = also_formulas

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        # Baseline outputs live under the app's dedicated OUTPUT_ROOT and Reset
        # already scopes that root directly; user-destination ownership is neither
        # needed nor useful here.
        tally = _AttemptTally(len(self.cells))
        total = tally.total
        clock = _RunClock([f"{row}|baseline" for _date, row in self.cells])
        attempts_root = baseline_matrix.byday_root()
        try:
            for date, row_key in self.cells:
                if self.cancel.is_set():
                    break
                self.q.put(("matrix_cell", {"row": row_key, "cell": date,
                                            "status": "running",
                                            "done": tally.done, "total": total,
                                            **clock.progress_extra()}))
                self.q.put(("log", f"  ▸ comparing {row_key} · {date} vs baseline…"))
                error_type = None
                started = clock.start()
                try:
                    res = baseline_matrix.build_baseline_cell(
                        self.source, date, row_key, self.baseline_id, self.dest,
                        events, also_formulas=self.also_formulas)
                    attempt, why = _attempt_state(res)
                    status = res.status
                    if status != "ok":
                        tally.errors += 1
                except Exception as e:                   # noqa: BLE001
                    log.exception("baseline matrix compare %s/%s crashed",
                                  date, row_key)
                    cancelled_cell = self.cancel.is_set()
                    status = "cancelled" if cancelled_cell else "error"
                    tally.errors += 1
                    attempt, why = _attempt_state(None, cancelled=cancelled_cell)
                    if not cancelled_cell:
                        why = f"{type(e).__name__}: {e}"
                        error_type = type(e).__name__
                dur = clock.finish(f"{row_key}|baseline", started)
                self.q.put(("log", _cell_done_line(row_key, date, "baseline",
                                                   attempt, why, dur)))
                tally.count(attempt)
                _record_attempt(attempts_root,
                                f"{row_key}|{self.source}|{self.baseline_id}",
                                date, attempt, why, error_type=error_type)
                tally.done += 1
                self.q.put(("matrix_cell", {"row": row_key, "cell": date,
                                            "status": status,
                                            "done": tally.done, "total": total,
                                            **clock.progress_extra()}))
        finally:
            self.q.put(("matrix_done", {**tally.payload(self.cancel.is_set()),
                                        "elapsed_s": round(clock.elapsed, 1)}))


class MatrixEvidenceWorker(threading.Thread):
    """Run the ON-DEMAND evidence generation for ONE cell's EXISTING vs-TSN
    comparison (either matrix — the caller pre-binds the resolver). No browser,
    no consolidation, no compare: matrix.evidence_for_cell /
    day_matrix.evidence_for_day_cell gate on freshness and then render the
    evidence set beside the comparison workbook. Posts the same
    ('matrix_cell', …) / ('matrix_done', …) events as the compare workers so
    the bridge lifecycle is identical."""

    def __init__(self, run_fn, row_key, cell_label, queue, cancel_event,
                 comparisons_dest=None):
        super().__init__(daemon=True, name="matrix-evidence")
        self.run_fn = run_fn                   # (events, commit_guard=...) -> result
        self.row_key = row_key
        self.cell_label = cell_label           # env key or date (display only)
        self.q = queue
        self.cancel = cancel_event
        # User-selected Everything destination. None identifies the app-private
        # Day Matrix path, which must not claim a batch root.
        self.comparisons_dest = comparisons_dest

    def run(self):
        comparisons_lease = None

        def _target_guard(path=None, *, anchor_path=None, anchor_identity=None,
                          directory_identity=None):
            lease = comparisons_lease
            if lease is None:
                return False
            if path is None:
                return lease.is_current()
            return lease.is_safe_descendant(
                path, anchor_path=anchor_path, anchor_identity=anchor_identity,
                directory_identity=directory_identity)

        def _is_cancelled():
            return (self.cancel.is_set()
                    or (comparisons_lease is not None
                        and not comparisons_lease.is_current()))

        events = Events(is_cancelled=_is_cancelled,
                        on_log=lambda m: self.q.put(("log", m)))
        errors = 0
        self.q.put(("matrix_cell", {"row": self.row_key, "cell": self.cell_label,
                                    "status": "running", "done": 0, "total": 1}))
        try:
            if self.comparisons_dest:
                comparisons_lease = owned_dir.require_existing_owned_dir_lease(
                    Path(self.comparisons_dest) / matrix.COMPARISONS_DIRNAME,
                    kind="comparisons")
                res = self.run_fn(events, commit_guard=_target_guard)
            else:
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
            cancelled = self.cancel.is_set()
            self.q.put(("matrix_cell", {"row": self.row_key, "cell": self.cell_label,
                                        "status": "error" if errors else "ok",
                                        "done": 1, "total": 1}))
            self.q.put(("matrix_done", {
                "done": 1 - errors, "total": 1, "errors": errors,
                "cancelled": cancelled, "attempted": 1,
                "succeeded": 0 if errors else 1,
                "failed": errors if not cancelled else 0,
                "cancelled_cells": errors if cancelled else 0,
                "partial_cells": 0}))


class MatrixTsnConsolidateWorker(threading.Thread):
    """Consolidate a report's raw TSN PDFs into one normalized TSN workbook (the
    'consolidate these PDFs?' prompt path), so the TSN comparison can run.
    CMP-AUD-010: routes by `origin` — a `canonical` source builds through the
    registered TSN builder (tsn_library.build_consolidated, reading the library
    raw/ folder — works for every PDF-backed family), while a `legacy` source uses
    the back-compat <dest>/_tsn_input/ Highway-Log consolidator. Offline
    (pdfplumber); posts ('matrix_done', …) so the bridge clears the task and
    refreshes the grid."""

    def __init__(self, dest, subdir, queue, cancel_event, origin="legacy"):
        super().__init__(daemon=True, name="matrix-tsn-consolidate")
        self.dest = dest
        self.subdir = subdir
        self.q = queue
        self.cancel = cancel_event
        self.origin = origin

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
        errors = 0
        try:
            if self.origin == "canonical":
                import tsn_library                    # lazy: pulls pdfplumber
                res = tsn_library.build_consolidated(
                    self.subdir, events=events, force=True)
                if getattr(res, "status", None) != "ok":
                    raise ValueError(getattr(res, "message", None)
                                     or f"the {self.subdir} TSN consolidation failed")
                ready = getattr(res, "output_path", None) or self.subdir
            else:
                ready = matrix.consolidate_tsn_pdfs(self.dest, self.subdir, events=events)
            self.q.put(("log", f"TSN workbook ready: {ready}"))
        except Exception as e:                       # noqa: BLE001
            errors = 1
            log.exception("matrix TSN consolidate (%s) crashed", self.subdir)
            self.q.put(("log", f"TSN consolidation failed ({type(e).__name__}): {e}"))
        finally:
            cancelled = self.cancel.is_set()
            self.q.put(("matrix_done", {
                "done": 1 - errors, "total": 1, "errors": errors,
                "cancelled": cancelled, "attempted": 1,
                "succeeded": 0 if errors else 1,
                "failed": errors if not cancelled else 0,
                "cancelled_cells": errors if cancelled else 0,
                "partial_cells": 0}))
