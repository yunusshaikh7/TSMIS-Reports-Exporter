"""The export-side GUI workers (S2 / ARC-02, split from gui_worker.py).

ExportWorker (one or more bulk exports, engine Events -> GUI messages),
BatchWorker (Export Everything with the resumable manifest + the journaled
store swap), ConsolidateWorker (one consolidation run). Verbatim moves;
gui_worker re-exports these so every existing import keeps working.
"""
import base64
import dataclasses
import logging
import os
import shutil
import threading
from pathlib import Path

import artifact_store
import batch_manifest
import outcome
import consolidation_meta
import owned_dir
from common import (ROUTES, AuthError, BrowserNotFoundError, PreflightError,
                    DATA_SOURCE_LABELS,
                    ENVIRONMENT_LABELS, get_site, set_site)
from events import Events
from exporter import run_export, run_export_combined, _wait_while_paused
from paths import env_tagged_filename

log = logging.getLogger("tsmis.gui")

def _swap_store_dir(live, staged, guard=None):
    """Replace `live` with the freshly-exported `staged` store folder, JOURNALED (P2/F2).

    The Export-Everything store used to rmtree the live folder BEFORE re-export, so a
    failed/crashed refresh destroyed the last-good copy. v0.18.0 delegates to
    `artifact_store.promote_store`: a journaled rename (live -> backup -> staging -> live)
    so a crash BETWEEN the renames is recovered on the next launch from the retained
    backup — there is never a window with zero copies, and a locked `live` keeps the
    last-good (the refresh is discarded), never a half-merged folder. Caller already
    gated on a COMPLETE producer outcome (F1) before promoting."""
    return artifact_store.promote_store(live, staged, guard=guard)


def _coalesce_groups(specs):
    """Group selected specs so both EDITIONS of one on-site report run together.

    Two selected reports coalesce when they share a `data_value` (the stable
    #customReport id) — i.e. they are the same on-site report saved two ways (the
    Excel export + the print-layout PDF: Highway Log, Intersection Detail, Highway
    Detail). Preserves first-occurrence order; a report with only one edition
    selected stays a group of one. Returns a list of spec-lists."""
    groups, index = [], {}
    for spec in specs:
        dv = getattr(spec, "data_value", None)
        if dv is not None and dv in index:
            index[dv].append(spec)
        else:
            g = [spec]
            groups.append(g)
            if dv is not None:
                index[dv] = g
    return groups


def _group_label(group):
    """Progress/log label for a coalesced group: the base report name, noting that
    both editions run together when a pair is coalesced (their spec.label is the
    shared dropdown text, e.g. 'Highway Log')."""
    if len(group) == 1:
        return group[0].label
    return f"{group[0].label} (Excel + PDF)"


class ExportWorker(threading.Thread):
    """Runs one OR MORE bulk exports, translating engine Events into GUI messages.

    `specs` may be a single ReportSpec or a list. Multiple report types run one
    after another (each reuses the proven engine), so in fast mode only `workers`
    browsers are ever open at once. Posts ('export_done', [(spec, RunResult), ...])
    when all selected reports finish (the list is partial if cancelled)."""

    def __init__(self, specs, queue, cancel_event, skip_event, workers=1, routes=None,
                 pause_event=None, auto_consolidate=False, out_base=None):
        super().__init__(daemon=True, name="export")
        # Accept a single spec or a list, so callers can't trip on the shape.
        self.specs = list(specs) if isinstance(specs, (list, tuple)) else [specs]
        self.q = queue
        self.cancel = cancel_event
        self.skip = skip_event
        self.pause = pause_event or threading.Event()    # B1: between-route hold
        self.auto_consolidate = bool(auto_consolidate)   # B2: combine after each
        self.out_base = Path(out_base) if out_base else None   # B3: always-current dest base
        self._owned_root_lease = None
        # Absolute stage spelling -> stable directory identity.  A predictable
        # `.staging` pathname is never authority by itself.
        self._stage_ids = {}
        self.workers = workers              # >1 -> experimental parallel "fast mode"
        # None means "all routes"; otherwise the chosen subset. Stored as a
        # concrete list so the engine and the progress total agree.
        self.routes = list(routes) if routes is not None else list(ROUTES)
        self._total = len(self.routes)
        # route -> latest status, so the end-of-run retry pass (which re-reports a
        # route, e.g. failed -> saved) updates counts in place rather than
        # double-counting. Counts are derived from this map on each update. Reset
        # per report type so each report's progress starts clean.
        self._route_status = {}
        self._tally_lock = threading.Lock()  # fast mode: several threads call _on_route
        self._ownership_loss_lock = threading.Lock()
        self._ownership_loss_reported = False
        self._cur_label = ""               # report currently running (shown in progress)
        self._report_i = 0                 # 1-based index of the current report
        self._report_n = len(self.specs)   # how many reports this run will do
        # Live-preview requests: worker numbers whose browser should be
        # screenshotted at its next safe poll point. Set from the GUI thread
        # (request_screenshot), drained by the engine threads — hence the lock.
        self._shot_lock = threading.Lock()
        self._shot_requests = set()

    def request_screenshot(self, worker_no):
        """GUI thread: ask browser `worker_no` (1-based) for a live screenshot.
        Answered via a ('preview_shot', ...) message at the worker's next safe
        poll point (≤ ~5 s during a report wait)."""
        with self._shot_lock:
            self._shot_requests.add(int(worker_no))

    def _shot_wanted(self, worker_no):
        """Engine threads: one request = one screenshot."""
        with self._shot_lock:
            if worker_no in self._shot_requests:
                self._shot_requests.discard(worker_no)
                return True
            return False

    def _on_screenshot(self, worker_no, image, note, url=""):
        b64 = base64.b64encode(image).decode("ascii") if image else None
        self.q.put(("preview_shot", (worker_no, b64, note, url)))

    def _auto_consolidate(self, spec, result, events):
        """B2: build `spec`'s combined workbook right after its export, reusing
        the same Events sink so progress flows into the log. Runs inline on this
        worker thread (the single-task gate already holds the 'export' slot, so a
        separate ConsolidateWorker would deadlock). Skipped for export-only
        reports (no consolidator) and when nothing was saved. A consolidation
        failure is logged, never fatal — the export itself already succeeded."""
        from pathlib import Path
        from reports import consolidator_for_spec
        commit_guard = None
        if self.out_base is not None:
            self._require_store_lease("auto-consolidation write")
        mod = consolidator_for_spec(spec)
        if mod is None:
            self.q.put(("log", f"  Auto-consolidate: {spec.label} has no "
                               "consolidator — skipped."))
            return
        if not (result.saved or result.exists):
            self.q.put(("log", f"  Auto-consolidate: nothing to combine for "
                               f"{spec.label} — skipped."))
            return
        if self.out_base is not None:
            # The per-route files in input_dir carry an "<src-env> " name prefix
            # (env_tagged_filename) — fine for the consolidators, which discover
            # inputs by '*.xlsx'/'*.pdf' glob and pull the route from the END of
            # the name (or, for Ramp Summary, from the PDF text). The combined
            # workbook gets the same prefix so it self-labels in the store too.
            day, input_dir = None, self.out_base / spec.subdir
            out_path = (self.out_base / "consolidated"
                        / env_tagged_filename(mod.FILENAME, self.out_base.name))
            input_identity = owned_dir.directory_identity(input_dir)
            self._owned_root_lease.require_safe_descendant(
                input_dir, "auto-consolidation input read",
                directory_identity=input_identity)

            def commit_guard(path):
                # Keep both the promoted input store and each destination
                # spelling under the same still-current lease for the whole
                # long consolidation.
                return (self._owned_root_lease.is_safe_descendant(
                            input_dir, directory_identity=input_identity)
                        and self._owned_root_lease.is_safe_descendant(path))
        else:
            day = Path(result.output_dir).parent.name if result.output_dir else None
            input_dir = out_path = None
        self.q.put(("log", ""))
        self.q.put(("log", f"Auto-consolidating {spec.label}…"))
        try:
            res = mod.consolidate(events=events, confirm_overwrite=lambda _p: True,
                                  day=day, input_dir=input_dir, out_path=out_path,
                                  commit_guard=commit_guard)
            # P1-R01: persist the producer completion beside the workbook this writer
            # produced (the same reusable consolidated the matrix later reuses), through
            # the shared boundary — so an auto-consolidate partial can't be reused green.
            # A False return = the partial flag couldn't be recorded (the incomplete
            # combined file was discarded); surface it in the log (non-fatal — the export
            # itself already succeeded).
            if self.out_base is not None:
                self._require_store_lease("consolidation outcome write")
            if not consolidation_meta.write_outcome(
                    res.output_path or out_path, res, commit_guard=commit_guard):
                self.q.put(("log", "  Auto-consolidate: the outcome could not be recorded; "
                                   "the incomplete combined file was discarded (it will rebuild)."))
            lines = res.summary_lines or ([res.message] if res.message else [])
            for line in lines:
                self.q.put(("log", f"  {line}"))
        except Exception as e:
            log.exception("auto-consolidate failed for %s", spec.label)
            self.q.put(("log", f"  Auto-consolidate failed: {type(e).__name__} "
                               "(details in the log)."))

    def _on_route(self, route, status):
        with self._tally_lock:              # in fast mode this fires from many threads
            self._route_status[route] = status      # latest status wins (retry re-reports)
            counts = {"saved": 0, "empty": 0, "skipped": 0, "failed": 0, "exists": 0}
            for st in self._route_status.values():
                if st in counts:
                    counts[st] += 1
            msg = {"done": len(self._route_status), **counts}
        msg["total"] = self._total
        msg["route"] = route
        msg["report"] = self._cur_label
        msg["report_i"] = self._report_i
        msg["report_n"] = self._report_n
        self.q.put(("progress", msg))

    def _should_skip(self):
        if self.skip.is_set():
            self.skip.clear()               # one press skips one route
            return True
        return False

    def _is_cancelled(self):
        """Treat loss of the exact store lease like cancellation inside engines.

        The exporter polls this immediately before each report save (as well as
        between routes). That is the narrowest portable check before a save
        strategy opens its output path; final staging promotion is guarded at
        every filesystem mutation separately.
        """
        if self.cancel.is_set():
            return True
        lease = self._owned_root_lease
        stages_current = (lease is None or all(
            lease.is_safe_descendant(stage, directory_identity=identity)
            for stage, identity in list(self._stage_ids.values())))
        if lease is None or (lease.is_current() and stages_current):
            return False
        with self._ownership_loss_lock:
            if not self._ownership_loss_reported:
                self._ownership_loss_reported = True
                msg = ("The Export Everything destination changed while the export "
                       "was running. No further report files will be written or promoted.")
                log.error(msg)
                self.q.put(("log", msg))
        return True

    def _build_events(self):
        """The Events sink for this worker — shared by run() (one export) and by
        BatchWorker, which reuses _run_specs once per environment (B3)."""
        events = Events(
            on_log=lambda t: self.q.put(("log", t)),
            on_route=self._on_route,
            should_skip=self._should_skip,
            is_cancelled=self._is_cancelled,
            on_status=lambda w, t: self.q.put(("worker_status", (w, t))),
            screenshot_wanted=self._shot_wanted,
            on_screenshot=self._on_screenshot,
            is_paused=self.pause.is_set,
        )
        # Export engines consult this immediately before every route save. It
        # remains additive so direct/non-store Events users keep their old API.
        events.destination_guard = self._destination_guard
        return events

    def _run_specs(self, events, results):
        """Run every selected report once against the CURRENT site, appending
        (spec, RunResult) to `results`. Posts log/progress/worker_status and the
        B2 auto-consolidate; does NOT post export_done/error — the caller owns the
        run lifecycle (run() for one export; BatchWorker once per environment for
        B3). Appends as it goes so a mid-run exception still leaves partials.

        When BOTH editions of one on-site report are selected (same data_value,
        e.g. Highway Log Excel + Highway Log PDF), the standard (sequential) path
        COALESCES them — the report is generated once per route and both files are
        saved off that single render (run_export_combined) instead of generating it
        twice. Fast mode keeps each edition its own PARALLEL pass (its route
        parallelism is the speed lever there; coalescing it is a follow-up)."""
        fast = bool(self.workers and self.workers > 1)
        # Coalesce dual-edition pairs in the sequential path (a clear ~2x win); in
        # fast mode every group is a singleton so behavior is unchanged.
        groups = [[s] for s in self.specs] if fast else _coalesce_groups(self.specs)
        # Ownership is deletion authority, so claim the store only when this
        # invocation has real work and only through create-and-mark semantics.
        # A pre-existing untrusted folder blocks before staging/report writes.
        if (self.out_base is not None and groups
                and not self.cancel.is_set()):
            self._owned_root_lease = owned_dir.require_owned_dir_lease(
                self.out_base, kind="store")
        self._report_n = len(groups)
        for gi, group in enumerate(groups, 1):
            if self.cancel.is_set():
                break
            self._report_i = gi
            self._cur_label = _group_label(group)
            with self._tally_lock:
                self._route_status = {}         # fresh counts for this report
            if self._report_n > 1:
                self.q.put(("log", ""))
                self.q.put(("log", f"===== Report {gi} of {self._report_n}: {self._cur_label} ====="))
            # Reset the progress bar/counts for this report so the GUI doesn't
            # show the previous report's tally while this one spins up.
            self.q.put(("progress", {
                "done": 0, "total": self._total, "route": "—",
                "saved": 0, "empty": 0, "skipped": 0, "failed": 0, "exists": 0,
                "report": self._cur_label, "report_i": gi, "report_n": self._report_n,
            }))
            # B3 stage-and-swap: prep each edition's live dir + fresh `.staging`
            # sibling + env-tagged run_spec (see _prep_edition).
            preps = []
            try:
                for spec in group:
                    preps.append(self._prep_edition(spec))
            except Exception:
                for _o, created_stage, _rs, _rd in preps:
                    if created_stage is not None:
                        try:
                            self._discard_stage(
                                created_stage, "failed-preparation staging cleanup")
                        except owned_dir.OwnershipError as e:
                            log.warning("store staging cleanup skipped: %s", e)
                raise
            try:
                if self.out_base is not None:
                    self._require_store_lease("export write")
                if len(group) == 1 and fast:
                    from exporter_parallel import run_export_parallel  # lazy
                    _o, _s, run_spec, run_dir = preps[0]
                    edition_results = [run_export_parallel(
                        run_spec, events, workers=self.workers, routes=self.routes, out_dir=run_dir)]
                elif len(group) == 1:
                    _o, _s, run_spec, run_dir = preps[0]
                    edition_results = [run_export(
                        run_spec, events, routes=self.routes, out_dir=run_dir)]
                else:
                    # Coalesced: generate each route once, save every edition.
                    edition_results = run_export_combined(
                        [p[2] for p in preps], events, routes=self.routes,
                        out_dirs=[p[3] for p in preps])
            except Exception:
                # A crash must NOT cost the last-good copy: drop every staging dir,
                # leave the live folders as they were, let the caller handle it.
                for _o, stage_dir, _rs, _rd in preps:
                    if stage_dir is not None:
                        try:
                            self._discard_stage(
                                stage_dir, "crashed-export staging cleanup")
                        except owned_dir.OwnershipError as e:
                            log.warning("store staging cleanup skipped: %s", e)
                raise
            for spec, (out_dir, stage_dir, _rs, _rd), result in zip(group, preps, edition_results):
                self._finish_edition(spec, result, out_dir, stage_dir, events, results)
        return results

    def _prep_edition(self, spec):
        """Prep ONE report edition's output: the live `<dest>/<src-env>/<subdir>`
        dir, a fresh `.staging` sibling (store refreshes stage-and-swap so a
        failed/cancelled refresh never destroys last-good), and an env-tagged
        run_spec (every output file carries the <src-env> tag so a lifted file still
        says which environment it came from). Returns (out_dir, stage_dir, run_spec,
        run_dir). Factored out so a coalesced group preps every edition the same way
        the single path did."""
        out_dir = (self.out_base / spec.subdir) if self.out_base else None
        stage_dir = None
        if out_dir is not None:
            self._require_store_lease("staging directory creation")
            stage_dir = out_dir.with_name(out_dir.name + ".staging")
            self._owned_root_lease.require_safe_descendant(
                stage_dir, "staging directory creation")
            try:
                # Exclusive creation: a stale, foreign, symlink, or junction
                # stage is a hard stop and is never recursively cleared.
                stage_dir.mkdir(exist_ok=False)
            except FileExistsError as e:
                raise owned_dir.OwnershipError(
                    f"The staging folder '{stage_dir.name}' already exists. It was "
                    "left untouched; retry after resolving the interrupted export.") from e
            except OSError as e:
                raise owned_dir.OwnershipError(
                    f"The staging folder '{stage_dir.name}' could not be created "
                    f"safely ({type(e).__name__}).") from e
            stage_identity = owned_dir.directory_identity(stage_dir)
            self._owned_root_lease.require_safe_descendant(
                stage_dir, "export staging write",
                directory_identity=stage_identity)
            self._stage_ids[self._stage_key(stage_dir)] = (
                stage_dir, stage_identity)
        run_spec = spec
        if self.out_base is not None:
            tag = self.out_base.name
            run_spec = dataclasses.replace(
                spec,
                filename=lambda r, _f=spec.filename, _t=tag: env_tagged_filename(_f(r), _t))
        run_dir = stage_dir if stage_dir is not None else out_dir
        return out_dir, stage_dir, run_spec, run_dir

    def _require_store_lease(self, action):
        if self.out_base is None:
            return None
        if self._owned_root_lease is None:
            raise owned_dir.OwnershipError(
                "The Export Everything destination has no active ownership lease.")
        return self._owned_root_lease.require_current(action=action)

    @staticmethod
    def _stage_key(stage_dir):
        return os.path.normcase(os.path.abspath(stage_dir))

    def _stage_binding(self, stage_dir):
        return self._stage_ids.get(self._stage_key(stage_dir))

    def _forget_stage(self, stage_dir):
        self._stage_ids.pop(self._stage_key(stage_dir), None)

    def _destination_guard(self, path):
        """Target-aware route/consolidation guard used at mutation boundaries."""
        if self.out_base is None:
            return True
        lease = self._owned_root_lease
        if lease is None:
            return False
        candidate = Path(os.path.abspath(path))
        for stage, identity in list(self._stage_ids.values()):
            try:
                candidate.relative_to(Path(os.path.abspath(stage)))
            except ValueError:  # silent-ok: this candidate belongs to another active stage
                continue
            return lease.is_safe_descendant(
                candidate, anchor_path=stage, anchor_identity=identity)
        return lease.is_safe_descendant(candidate)

    def _promotion_guard(self, out_dir, stage_dir, stage_identity):
        """Composite guard valid before and after staging is renamed live."""
        lease = self._owned_root_lease
        if lease is None or not lease.is_current():
            return False
        stage_at = None
        for candidate in (stage_dir, out_dir):
            if owned_dir.directory_identity(candidate) == stage_identity:
                stage_at = candidate
                break
        if stage_at is None:
            return False
        if not lease.is_safe_descendant(
                stage_at, directory_identity=stage_identity):
            return False
        if not owned_dir.is_plain_directory_tree(stage_at, stage_identity):
            return False
        # A prior live target is another mutation operand; reject it when it is
        # itself a link/reparse. After commit it is the bound stage object above.
        if out_dir.exists() and out_dir != stage_at:
            return lease.is_safe_descendant(out_dir)
        return True

    def _discard_stage(self, stage_dir, action):
        """Delete only the exact plain staging object this worker created."""
        binding = self._stage_binding(stage_dir)
        if binding is None:
            raise owned_dir.OwnershipError(
                "The staging folder is not bound to this export run.")
        _stage, identity = binding
        self._owned_root_lease.require_safe_descendant(
            stage_dir, action, directory_identity=identity)
        if not owned_dir.is_plain_directory_tree(stage_dir, identity):
            raise owned_dir.OwnershipError(
                "The staging folder changed or contains a linked entry; it was retained.")
        shutil.rmtree(stage_dir)
        self._forget_stage(stage_dir)

    def _finish_edition(self, spec, result, out_dir, stage_dir, events, results):
        """Post-process one finished edition: decide completion, promote or discard
        the staging (store refresh), set the artifact, append (spec, result), and B2
        auto-consolidate. The same logic the single path ran, per edition — so each
        edition of a coalesced pair still stages/swaps and consolidates on its own."""
        cancelled = self.cancel.is_set()
        in_store = stage_dir is not None
        # F1: ONLY a complete refresh may replace the last-good store copy.
        if in_store and result.exists:
            # §C.1: a FRESH staging dir must never report "already had" files. If it
            # does, the staging is untrustworthy — REJECT the promotion so it can't
            # replace last-good, and log the anomaly.
            log.warning("store refresh for %s saw %d 'exists' route(s) in a FRESH "
                        "staging dir (anomaly) — rejecting promotion, keeping last-good",
                        spec.subdir, len(result.exists))
            result.completion = outcome.FAILED
        else:
            result.completion = outcome.run_completion(result, cancelled=cancelled)
        promoted = False
        # P2-A04: a prior store counts only if it's a USABLE store (holds an artifact).
        if in_store:
            self._owned_root_lease.require_safe_descendant(
                out_dir, "store inspection")
        had_prior = bool(in_store and artifact_store.is_usable_store(out_dir))
        if in_store:
            if outcome.promotable(result.completion):
                self._require_store_lease("store promotion")
                binding = self._stage_binding(stage_dir)
                if binding is None:
                    raise owned_dir.OwnershipError(
                        "The export staging identity is unavailable for promotion.")
                _stage, stage_identity = binding
                promoted = _swap_store_dir(
                    out_dir, stage_dir,
                    guard=lambda: self._promotion_guard(
                        out_dir, stage_dir, stage_identity))
                if not promoted:
                    # P2-B01: a COMPLETE export whose journaled swap failed did NOT
                    # promote — the previous live copy is intact; must read as
                    # previous_preserved (or none on a first run).
                    log.warning("store refresh for %s: promotion FAILED — kept last-good, "
                                "NOT promoted", spec.subdir)
            else:
                self._discard_stage(stage_dir, "incomplete-export staging cleanup")
                log.info("store refresh for %s was %s — kept last-good, discarded staging",
                         spec.subdir, result.completion)
        if in_store:
            # Promotion consumed it or the promotion layer retained it under a
            # journal. Either way this worker must never write to the spelling again.
            self._forget_stage(stage_dir)
        # Artifact reflects the ACTUAL store outcome (P2-B06: never falsely claim a
        # prior was preserved).
        if in_store and not promoted:
            result.artifact = outcome.PREVIOUS_PRESERVED if had_prior else outcome.NONE
        else:
            result.artifact = outcome.artifact_after_store(result.completion, in_store)
        results.append((spec, result))
        # B2 auto-consolidate: for a STORE refresh only a run that actually PROMOTED
        # may consolidate (a partial/failed/cancelled refresh kept last-good, so
        # consolidating now would rebuild from the OLD store — P1-B03). A non-store
        # dated run consolidates whatever it got.
        store_ok = (not in_store) or result.artifact == outcome.PROMOTED
        if self.auto_consolidate and not self.cancel.is_set() and store_ok:
            self._auto_consolidate(spec, result, events)

    def run(self):
        events = self._build_events()
        results = []
        try:
            self._run_specs(events, results)
            self.q.put(("export_done", results))
            return
        except AuthError as e:
            log.warning("export worker stopped: AuthError: %s", e)
            err = ("auth", str(e))
        except (PreflightError, BrowserNotFoundError) as e:
            log.warning("export worker stopped: %s: %s", type(e).__name__, e)
            err = ("general", str(e))               # message is already user-safe
        except Exception as e:
            # The full traceback MUST land in the log -- the GUI can only show
            # one line, and "TypeError: ..." with no context is undebuggable.
            log.exception("export worker crashed")
            err = ("general", f"{type(e).__name__}: {e}")
        # An error aborted a multi-report run partway. Hand the GUI whatever
        # reports DID finish so "Save run report…" still covers them (each is also
        # auto-saved under output/run_reports/), then surface the error.
        if results:
            self.q.put(("export_partial", results))
        self.q.put(("error", err))


class BatchWorker(threading.Thread):
    """B3 "Export Everything": run selected report types across selected
    environments, sequentially, reusing the proven export engine. Each
    environment is exported into its normal run folder (output/<date src-env>/
    <report>/) by reusing ExportWorker._run_specs, so resume/idempotency, fast
    mode, pause (B1) and auto-consolidate (B2) all come for free.

    Per-env targeting uses the PROCESS-GLOBAL common.set_site (NOT
    set_thread_site): the batch is a single sequential orchestrator and the
    single-task gate guarantees no other export runs, so mutating the global is
    safe — and the user's original selection is restored when the batch ends.
    (set_thread_site is only for the parallel env-scanner, where several browsers
    target different environments at once.) Progress is persisted after every
    environment, so a batch survives an app restart and resumes at the next
    pending environment.

    Posts ("batch_progress", dict) before each environment and ("batch_done",
    dict) at the end; the per-report log/progress/worker_status come from the
    reused ExportWorker. A fatal sign-in/browser problem ends the batch with an
    ("error", …) and KEEPS the manifest so the cause can be fixed and resumed.
    """

    def __init__(self, manifest, queue, cancel_event, skip_event, pause_event):
        super().__init__(daemon=True, name="batch")
        self.manifest = manifest
        self.q = queue
        self.cancel = cancel_event
        self.skip = skip_event
        self.pause = pause_event

    def _specs(self):
        # Resolve the manifest's export-op KEYS to specs (P3 / §C.5). The seam the
        # lifecycle tests stub; the real impl never silently narrows — validity is
        # the `_invalid_keys` set, and run() aborts all-or-nothing on any invalid key
        # (F7). A v1 manifest was migrated to keys by batch_manifest.load.
        from reports import resolve_export_keys
        return resolve_export_keys(self.manifest.get("reports", []))[0]

    def _invalid_keys(self):
        """The saved keys that DON'T resolve — unknown, app-wide-disabled, or
        duplicate. A non-empty result means the saved selection can't be honored;
        run() aborts all-or-nothing rather than running a narrower batch (§C.5)."""
        from reports import resolve_export_keys
        return resolve_export_keys(self.manifest.get("reports", []))[1]

    def _step_views(self, cur_src, cur_env):
        """Ordered per-environment view for the progress stepper: each step's
        friendly label + whether it's `done` / `running` now / still `pending`.
        Read from the manifest (the source of truth across a resume), so the
        already-finished envs read `done` and the (cur_src, cur_env) about to
        export reads `running`."""
        views = []
        for s in self.manifest.get("steps", []):
            ssrc, senv = s.get("src"), s.get("env")
            if s.get("status") == "done":
                state = "done"
            elif ssrc == cur_src and senv == cur_env:
                state = "running"
            else:
                state = "pending"
            views.append({
                "key": f"{ssrc}-{senv}",
                "label": f"{DATA_SOURCE_LABELS.get(ssrc, ssrc)} / "
                         f"{ENVIRONMENT_LABELS.get(senv, senv)}",
                "state": state,
            })
        return views

    def run(self):
        specs = self._specs()
        steps = self.manifest.get("steps", [])
        fast = self.manifest.get("fast", False)
        workers = self.manifest.get("workers", 1) if fast else 1
        auto = self.manifest.get("auto_consolidate", False)
        dest = self.manifest.get("dest")
        pause_sink = Events(is_paused=self.pause.is_set,
                            is_cancelled=self.cancel.is_set)
        total = len(steps)
        done = sum(1 for s in steps if s.get("status") == "done")
        if self._invalid_keys() or not specs:
            # The saved selection can't be honored as-is — one or more report keys
            # are unknown/disabled/duplicate, or none resolve (e.g. after an upgrade
            # or registry change). Per §C.5 this is ALL-OR-NOTHING: abort WITHOUT
            # marking any environment done (a narrower batch would silently drop the
            # user's pending selection) and WITHOUT clearing the manifest (it stays
            # resumable/discardable). Emit exactly ONE terminal — the user-visible
            # `error`, mirroring the AuthError path — never a second `batch_done`
            # (CT-10: one terminal per outcome; a stray second terminal could clobber
            # an already-dispatched successor pre-P7a).
            self.q.put(("log", "  This Export Everything batch can't run: one or more "
                               "of its saved report types are no longer available."))
            self.q.put(("error", ("general",
                        "This Export Everything batch can't run — one or more of its "
                        "saved report types are no longer available. Discard it and "
                        "start a fresh Export Everything.")))
            return
        original = get_site()
        try:
            for step in steps:
                if step.get("status") == "done":
                    continue
                _wait_while_paused(pause_sink)          # B1: hold between envs
                if self.cancel.is_set():
                    break
                src, env = step["src"], step["env"]
                set_site(src, env)
                self.q.put(("batch_progress", {
                    "src": src, "env": env,
                    "label": f"{DATA_SOURCE_LABELS.get(src, src)} / "
                             f"{ENVIRONMENT_LABELS.get(env, env)}",
                    "done": done, "total": total,
                    "steps": self._step_views(src, env)}))
                self.q.put(("log", ""))
                self.q.put(("log", f"========== {src.upper()}-{env.upper()}  "
                                   f"({done + 1} of {total}) =========="))
                out_base = (Path(dest) / f"{src}-{env}") if dest else None
                ew = ExportWorker(specs, self.q, self.cancel, self.skip,
                                  workers=workers, routes=None,
                                  pause_event=self.pause, auto_consolidate=auto,
                                  out_base=out_base)
                crashed = False
                results = []
                try:
                    ew._run_specs(ew._build_events(), results)
                except (AuthError, BrowserNotFoundError) as e:
                    # Every environment would hit this — stop and keep the
                    # manifest so the user can fix the cause and resume.
                    log.warning("batch stopped on %s-%s: %s: %s", src, env,
                                type(e).__name__, e)
                    self.q.put(("error",
                                ("auth" if isinstance(e, AuthError) else "general",
                                 str(e))))
                    return                              # finally restores the site
                except Exception as e:
                    crashed = True
                    log.exception("batch: %s-%s crashed", src, env)
                    self.q.put(("log", f"  {src}-{env} stopped unexpectedly "
                                       f"({type(e).__name__}); leaving it pending and "
                                       "moving on (details in the log)."))
                if self.cancel.is_set():
                    break
                if crashed:
                    continue                            # leave pending for a resume
                # §C.1 + P2-B01: mark an environment DONE only when every selected report
                # was actually PROMOTED (completion=complete AND the store swap succeeded).
                # A partial / no_data / failed report, a short result set, OR a complete
                # report whose promotion FAILED (locked/crash, artifact=previous_preserved)
                # leaves the env PENDING so a resume re-pulls it — last-good is intact.
                bad = [s.label for s, r in results
                       if getattr(r, "artifact", None) != outcome.PROMOTED]
                if len(results) == len(specs) and not bad:
                    step["status"] = "done"
                    batch_manifest.mark_done(self.manifest, src, env)
                    done += 1
                else:
                    miss = bad or [s.label for s in specs[len(results):]]
                    self.q.put(("log", f"  {src}-{env}: left PENDING — "
                                       f"{len(miss)} report(s) not complete "
                                       f"({', '.join(miss) or 'none ran'}); kept last-good. "
                                       "Resume to retry."))
            complete = batch_manifest.is_complete(self.manifest)
            batch_completion = (outcome.CANCELLED if self.cancel.is_set()
                                else outcome.COMPLETE if complete else outcome.PARTIAL)
            self.q.put(("batch_done", {
                "done": done, "total": total,
                "cancelled": self.cancel.is_set(),
                "complete": complete, "completion": batch_completion}))
        finally:
            set_site(*original)


class ConsolidateWorker(threading.Thread):
    """Runs one consolidator. Overwrite is resolved by the GUI before start,
    so the injected confirm callback just returns the pre-decided answer.
    `day` is the dated export folder to read (YYYY-MM-DD), or None for the
    legacy flat layout."""

    def __init__(self, consolidate_fn, queue, cancel_event, confirm, day=None):
        super().__init__(daemon=True, name="consolidate")
        self.consolidate_fn = consolidate_fn
        self.q = queue
        self.cancel = cancel_event
        self.confirm = confirm
        self.day = day

    def run(self):
        events = Events(
            on_log=lambda t: self.q.put(("log", t)),
            is_cancelled=self.cancel.is_set,
        )
        log.info("consolidate start: %s (day=%s)",
                 getattr(self.consolidate_fn, "__module__", self.consolidate_fn),
                 self.day or "legacy/newest")
        try:
            result = self.consolidate_fn(events=events, confirm_overwrite=self.confirm,
                                         day=self.day)
            log.info("consolidate done: status=%s output=%s message=%s",
                     result.status, result.output_path or "-", result.message or "-")
            # Ordinary consolidations still publish their one reusable workbook through
            # the legacy single-path sidecar boundary. Comparisons are different: their
            # central publication owns every member (values/formulas/generation metadata)
            # as one transaction. A second generic write here would overwrite that richer
            # record beside only the legacy primary path, so typed comparison/generation
            # results deliberately bypass it.
            centrally_published = (
                getattr(result, "comparison_outcome", None) is not None
                or getattr(result, "artifact_generation", None) is not None)
            if (not centrally_published
                    and not consolidation_meta.write_outcome(
                        result.output_path, result)):
                self.q.put(("error", ("general",
                            "Consolidation finished but its outcome could not be recorded; "
                            "the incomplete output was discarded. Close any open copy and "
                            "run it again.")))
                return
            self.q.put(("consolidate_done", result))
        except Exception as e:
            log.exception("consolidate worker crashed")
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))
