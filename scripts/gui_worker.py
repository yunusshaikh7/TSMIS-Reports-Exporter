"""Worker threads for the GUI.

Playwright's sync API is thread-affine, so all browser work happens on a
dedicated worker thread -- never on the Tk main thread. Workers communicate by
putting messages on a queue.Queue (thread-safe); the GUI drains it via
root.after(). Workers never touch Tk widgets.

Message protocol (all are (kind, payload) tuples):
    ("log", str)                       one status line
    ("progress", dict)                 {done,total,route,report,report_i,report_n,saved,empty,skipped,failed,exists}
    ("worker_status", (worker, text))  what browser `worker` (1-based) is doing
                                       right now (statuses replace each other)
    ("preview_shot", (worker, b64, note, url))  an on-demand page screenshot
                                       for browser `worker` — b64 is a base64
                                       JPEG string, or None when the capture
                                       failed (note then says why); url is the
                                       page's address at capture time
    ("env_shot", dict)                 the idle "Verify environment" result:
                                       {ok, img (b64 JPEG|None), env, src,
                                        matches, url, error} — url is the
                                       page's address at screenshot time (the
                                       intended one when it never opened)
    ("env_access", dict)               one combo's verdict from the Settings
                                       "Check all environments" scan, posted
                                       as it finishes: {key, source,
                                       environment, label, status, detail,
                                       url, reports} — status is one of ok |
                                       unverified | reports_off | no_reports |
                                       denied | no_signin | wrong_site |
                                       unreachable | error; reports maps each report
                                       type's dropdown label to
                                       ok | greyed | missing (empty when the
                                       dropdown couldn't be read)
    ("env_access_done", dict)          the scan ended:
                                       {ok, done, total, cancelled, error}
    ("reset_done", dict)               outcome of "Delete all reports":
                                       {files, mb, errors: [str, ...]}
    ("chromium_done", dict)            outcome of the Built-in Chromium
                                       download/delete: {ok, action,
                                       cancelled, error}
    ("export_done", [(spec, RunResult), ...])   all selected reports finished
    ("export_partial", [(spec, RunResult), ...]) reports done before an error (then an "error" follows)
    ("consolidate_done", ConsolidateResult)
    ("login_open", None)               headed browser is up; user should finish SSO
    ("login_saved", None)              a VALID session was captured and written
    ("login_device_ok", None)          silent device sign-in works on this PC, but the
                                       session is device-bound: no file saved; exports
                                       sign themselves in live (device sign-in mode)
    ("login_failed", None)             window closed/finished without a real login
    ("cancelled", None)                task stopped at user request
    ("error", (kind, message))         kind is "auth" or "general"
    ("update_status", dict)            one-click update progress; the dict is the
                                       GUI's whole update state (phase, version,
                                       progress, ...) -- see gui_api._on_update_status
"""
import base64
import logging
import queue as queue_mod
import re
import threading
import time

from common import (
    _CONFIG_JS, LOGIN_BROWSER_ARGS, ROUTES, AuthError, BrowserNotFoundError,
    PreflightError, SiteUnreachableError, BROWSER_CHANNELS, CHANNEL_LABELS,
    DATA_SOURCES, DATA_SOURCE_LABELS, ENVIRONMENTS, ENVIRONMENT_LABELS,
    auth_state, check_browsers, get_site, get_url, has_valid_auth,
    is_logged_in,
    capture_edge_login_state_from_profiles, capture_edge_login_state_over_cdp,
    capture_storage_state_if_logged_in, get_preferred_channel,
    launch_edge_login_context, navigate_with_auth, new_authed_browser,
    new_login_context, page_url_for_display, preflight,
    resolve_parallel_channel, save_auth_state, set_site, set_thread_site,
    storage_state_is_portable,
)
import batch_manifest
import dataclasses
import day_matrix
import matrix
from pathlib import Path
from events import Events
from exporter import run_export, _wait_while_paused
from paths import (DOWNLOADED_BROWSERS_DIR, FAILURES_DIR, INPUT_ROOT,
                   OUTPUT_ROOT, env_tagged_filename, parse_run_folder)

log = logging.getLogger("tsmis.gui")

# Legacy flat-layout folders (pre-dated exports) that "Delete all reports"
# also clears. Everything else directly under output/ that isn't a run folder
# is left alone — only content this app generates is ever deleted.
_LEGACY_OUTPUT_DIRS = ("ramp_summary", "ramp_detail", "highway_sequence",
                       "highway_log", "highway_log_pdf", "consolidated",
                       "tsn_highway_log", "tsmis_highway_log_pdf",
                       "run_reports", "comparisons")


def reset_targets(include_input=False):
    """The folders/files "Delete all reports" removes, as (label, Path) pairs
    that currently exist. Reports only — logs, the saved login, the Edge
    sign-in profile and the app's settings are NEVER in this list."""
    targets = []
    try:
        for p in sorted(OUTPUT_ROOT.iterdir()):
            if p.is_dir() and parse_run_folder(p.name):
                targets.append((f"export run folder '{p.name}'", p))
    except OSError:
        pass
    for name in _LEGACY_OUTPUT_DIRS:
        p = OUTPUT_ROOT / name
        if p.is_dir():
            targets.append((f"output folder '{name}'", p))
    for fname, lbl in (("tsn_highway_log_consolidated.xlsx", "TSN consolidated workbook"),
                       ("tsmis_highway_log_pdf_consolidated.xlsx",
                        "TSMIS Highway Log (PDF) consolidated workbook")):
        p = OUTPUT_ROOT / fname
        if p.is_file():
            targets.append((lbl, p))
    # The Export Everything "always-current" store (configurable destination,
    # default output/All Reports (current)) holds generated reports too. The
    # destination is user-chosen and NOT validated as app-owned, so NEVER rmtree
    # it wholesale — only its known "<src-env>/" children (the exact folders the
    # batch writer creates, BatchWorker out_base = dest/"<src>-<env>"). Any
    # foreign files the user keeps alongside the store are left untouched.
    try:
        from settings import get_batch_dest
        from common import DATA_SOURCES, ENVIRONMENTS
        bdest = Path(get_batch_dest())
        known = {f"{s}-{e}" for s in DATA_SOURCES for e in ENVIRONMENTS}
        if bdest.is_dir():
            for child in sorted(bdest.iterdir()):
                # The known <src-env> export folders AND the matrix's own
                # "comparisons" tree are app-owned; foreign files stay untouched.
                if child.is_dir() and (child.name in known
                                       or child.name == "comparisons"):
                    targets.append(
                        (f"Export Everything store: {child.name}", child))
    except Exception:
        pass
    if FAILURES_DIR.is_dir():
        targets.append(("failure screenshots", FAILURES_DIR))
    if include_input:
        p = INPUT_ROOT / "tsn_highway_log"
        if p.is_dir():
            targets.append(("TSN input PDFs", p))
        # The Export-Everything store's TSN drops (user-placed TSN datasets) are
        # inputs too, so they only clear with include_input (the generated TSN
        # comparison sheets under comparisons/tsn are covered by "comparisons").
        try:
            from settings import get_batch_dest
            tsn_in = Path(get_batch_dest()) / "_tsn_input"
            if tsn_in.is_dir():
                targets.append(("Export Everything store: _tsn_input", tsn_in))
        except Exception:
            pass
    return targets


def measure_targets(targets):
    """(file_count, total_bytes) across the target list. Best-effort."""
    files = 0
    size = 0
    for _label, path in targets:
        try:
            if path.is_file():
                files += 1
                size += path.stat().st_size
                continue
            for f in path.rglob("*"):
                if f.is_file():
                    files += 1
                    try:
                        size += f.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return files, size


def _swap_store_dir(live, staged):
    """Replace `live` with the freshly-exported `staged` folder (clear-on-success).

    The Export-Everything store used to rmtree the live folder BEFORE re-export,
    so a failed/crashed refresh destroyed the last-good copy (and a partial set
    could read as fresh). Now each report exports into a `.staging` sibling and
    this swaps it in only on a clean finish. Best-effort against locked files (a
    report the user has open in Excel): a clean clear+rename when possible, else
    merge the staged files over the live folder so the refresh still lands."""
    import shutil
    try:
        if not live.exists():
            staged.rename(live)
            return
        shutil.rmtree(live, ignore_errors=True)
        if not live.exists():
            staged.rename(live)
            return
        # A locked leftover blocked the clean swap — merge staged over live.
        log.warning("batch store: %s could not be fully cleared; merging refresh", live)
        live.mkdir(parents=True, exist_ok=True)
        for item in staged.iterdir():
            target = live / item.name
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                try:
                    target.unlink()
                except OSError:
                    pass
            try:
                shutil.move(str(item), str(target))
            except OSError as e:
                log.warning("batch store: could not place %s: %s: %s",
                            target, type(e).__name__, e)
        shutil.rmtree(staged, ignore_errors=True)
    except OSError as e:
        log.warning("batch store swap failed for %s: %s: %s",
                    live, type(e).__name__, e)
        shutil.rmtree(staged, ignore_errors=True)


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
        else:
            day = Path(result.output_dir).parent.name if result.output_dir else None
            input_dir = out_path = None
        self.q.put(("log", ""))
        self.q.put(("log", f"Auto-consolidating {spec.label}…"))
        try:
            res = mod.consolidate(events=events, confirm_overwrite=lambda _p: True,
                                  day=day, input_dir=input_dir, out_path=out_path)
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

    def _build_events(self):
        """The Events sink for this worker — shared by run() (one export) and by
        BatchWorker, which reuses _run_specs once per environment (B3)."""
        return Events(
            on_log=lambda t: self.q.put(("log", t)),
            on_route=self._on_route,
            should_skip=self._should_skip,
            is_cancelled=self.cancel.is_set,
            on_status=lambda w, t: self.q.put(("worker_status", (w, t))),
            screenshot_wanted=self._shot_wanted,
            on_screenshot=self._on_screenshot,
            is_paused=self.pause.is_set,
        )

    def _run_specs(self, events, results):
        """Run every selected report once against the CURRENT site, appending
        (spec, RunResult) to `results`. Posts log/progress/worker_status and the
        B2 auto-consolidate; does NOT post export_done/error — the caller owns the
        run lifecycle (run() for one export; BatchWorker once per environment for
        B3). Appends as it goes so a mid-run exception still leaves partials."""
        for i, spec in enumerate(self.specs, 1):
            if self.cancel.is_set():
                break
            self._report_i = i
            self._cur_label = spec.label
            with self._tally_lock:
                self._route_status = {}         # fresh counts for this report
            if self._report_n > 1:
                self.q.put(("log", ""))
                self.q.put(("log", f"===== Report {i} of {self._report_n}: {spec.label} ====="))
            # Reset the progress bar/counts for this report so the GUI doesn't
            # show the previous report's tally while this one spins up.
            self.q.put(("progress", {
                "done": 0, "total": self._total, "route": "—",
                "saved": 0, "empty": 0, "skipped": 0, "failed": 0, "exists": 0,
                "report": spec.label, "report_i": i, "report_n": self._report_n,
            }))
            # B3: when an always-current destination is set, write each report
            # into <dest>/<src-env>/<subdir>. STAGE-AND-SWAP: export into a fresh
            # `.staging` sibling (so the run re-pulls everything — a refresh, not a
            # resume-skip) and replace the live folder only on a clean finish, so a
            # failed/crashed/cancelled refresh never destroys the last-good copy.
            out_dir = (self.out_base / spec.subdir) if self.out_base else None
            stage_dir = None
            if out_dir is not None:
                import shutil
                stage_dir = out_dir.with_name(out_dir.name + ".staging")
                shutil.rmtree(stage_dir, ignore_errors=True)
                stage_dir.mkdir(parents=True, exist_ok=True)
            # B3: in the always-current store, prefix every output file with the
            # src-env tag (the dest's <src-env> subfolder name) so a file lifted
            # out still says which environment it came from. Wrapping spec.filename
            # covers the sequential + parallel engines AND both retry passes in one
            # place — they all name files via spec.filename(route). The original
            # spec (label/subdir, consolidator mapping) is kept for results/auto-
            # consolidate; only the per-route NAME changes.
            run_spec = spec
            if self.out_base is not None:
                tag = self.out_base.name
                run_spec = dataclasses.replace(
                    spec,
                    filename=lambda r, _f=spec.filename, _t=tag: env_tagged_filename(_f(r), _t))
            run_dir = stage_dir if stage_dir is not None else out_dir
            try:
                if self.workers and self.workers > 1:
                    from exporter_parallel import run_export_parallel  # lazy
                    result = run_export_parallel(run_spec, events, workers=self.workers,
                                                 routes=self.routes, out_dir=run_dir)
                else:
                    result = run_export(run_spec, events, routes=self.routes, out_dir=run_dir)
            except Exception:
                # A crash must NOT cost the last-good copy: drop staging, leave the
                # live folder as it was, and let the caller handle the error.
                if stage_dir is not None:
                    import shutil
                    shutil.rmtree(stage_dir, ignore_errors=True)
                raise
            # Swap the fresh export into place on a clean finish; on cancel, discard
            # staging so a partial refresh never replaces the last-good copy.
            if stage_dir is not None:
                if self.cancel.is_set():
                    import shutil
                    shutil.rmtree(stage_dir, ignore_errors=True)
                else:
                    _swap_store_dir(out_dir, stage_dir)
            results.append((spec, result))
            if self.auto_consolidate and not self.cancel.is_set():
                self._auto_consolidate(spec, result, events)
        return results

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
        from reports import EXPORT_REPORTS
        return [EXPORT_REPORTS[i][2] for i in self.manifest.get("reports", [])
                if 0 <= i < len(EXPORT_REPORTS)]

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
                try:
                    ew._run_specs(ew._build_events(), [])
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
                step["status"] = "done"
                batch_manifest.mark_done(self.manifest, src, env)
                done += 1
            self.q.put(("batch_done", {
                "done": done, "total": total,
                "cancelled": self.cancel.is_set(),
                "complete": batch_manifest.is_complete(self.manifest)}))
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
            self.q.put(("consolidate_done", result))
        except Exception as e:
            log.exception("consolidate worker crashed")
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))


class ResetWorker(threading.Thread):
    """"Delete all reports": removes every generated report (run folders,
    legacy flat folders, consolidated/comparison output, run reports, failure
    screenshots, TSN conversions — and the TSN input PDFs only when asked).
    Logs, the saved login and the app settings always survive. Files an open
    Excel still holds are reported, never silently skipped. Posts progress as
    ('log', ...) lines and one final ('reset_done', {files, mb, errors})."""

    def __init__(self, queue, include_input=False, cancel_event=None):
        super().__init__(daemon=True, name="reset")
        self.q = queue
        self.include_input = include_input
        self.cancel = cancel_event

    def run(self):
        import shutil
        targets = reset_targets(self.include_input)
        files, size = measure_targets(targets)
        errors = []
        cancelled = False
        ui = logging.getLogger("tsmis.ui")
        log.info("reset: deleting %d target(s), %d file(s), %.1f MB (input=%s)",
                 len(targets), files, size / 1e6, self.include_input)
        for label, path in targets:
            # Cancellable between targets (a partial delete is harmless -- a
            # re-run removes the rest). The current folder finishes first.
            if self.cancel is not None and self.cancel.is_set():
                cancelled = True
                self.q.put(("log", "  Cancelled — stopped after the current item."))
                break
            failures = []

            def on_error(_fn, p, _exc):
                failures.append(str(p))

            try:
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path, onerror=on_error)
            except OSError as e:
                failures.append(f"{path} ({type(e).__name__})")
            if failures:
                msg = (f"Could not delete {len(failures)} item(s) from {label} — "
                       "a file is probably open in Excel.")
                errors.append(msg)
                ui.info("reset: %s: %s", msg, failures[:5])
                self.q.put(("log", f"  {msg}"))
            else:
                self.q.put(("log", f"  Deleted {label}."))
        # Report what was ACTUALLY freed (before − what remains), so files held
        # open in Excel (or skipped by a cancel) aren't counted as deleted.
        remaining_files, remaining_size = measure_targets(targets)
        freed_files = max(0, files - remaining_files)
        freed_size = max(0, size - remaining_size)
        self.q.put(("reset_done", {"files": freed_files,
                                   "mb": round(freed_size / 1e6, 1),
                                   "errors": errors, "cancelled": cancelled}))


class ChromiumWorker(threading.Thread):
    """Download or delete the app-owned Built-in Chromium (Settings tab).

    Download drives the BUNDLED Playwright Node driver exactly the way
    `playwright install chromium --no-shell` would — that works in the frozen
    app (where there is no `python -m playwright`) and in dev runs alike —
    aimed at paths.DOWNLOADED_BROWSERS_DIR via PLAYWRIGHT_BROWSERS_PATH, so
    the browser lands in the app's own data folder (survives one-click
    updates, removable from the same Settings section). Installer progress is
    forwarded to the log (throttled); no console window is flashed. Delete
    removes ONLY that folder — never the with-browser bundle's
    `_internal\\ms-playwright`. Cancel (the shared cancel_event) kills the
    download; Playwright downloads to a temp name first, so a killed install
    can simply be retried.

    Posts ("log", …) progress + one ("chromium_done",
    {ok, action, cancelled, error})."""

    def __init__(self, queue, action, cancel_event):
        super().__init__(daemon=True, name="chromium")
        self.q = queue
        self.action = action            # "download" | "delete"
        self.cancel = cancel_event

    def run(self):
        out = {"ok": False, "action": self.action, "cancelled": False,
               "error": None}
        try:
            if self.action == "download":
                out["cancelled"] = not self._download()
                out["ok"] = not out["cancelled"]
            else:
                self._delete()
                out["ok"] = True
        except Exception as e:
            log.exception("chromium %s failed", self.action)
            reason = str(e).splitlines()[0] if str(e) else type(e).__name__
            out["error"] = reason
        self.q.put(("chromium_done", out))

    def _download(self):
        """Run the bundled driver's installer. Returns False when cancelled."""
        import os
        import subprocess
        import time

        from playwright._impl._driver import compute_driver_executable
        try:
            from playwright._impl._driver import get_driver_env
            env = dict(get_driver_env())
        except ImportError:
            env = dict(os.environ)
        cmd = compute_driver_executable()
        cmd = list(cmd) if isinstance(cmd, (list, tuple)) else [str(cmd)]
        DOWNLOADED_BROWSERS_DIR.mkdir(parents=True, exist_ok=True)
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(DOWNLOADED_BROWSERS_DIR)
        log.info("chromium: download starting -> %s (driver %s)",
                 DOWNLOADED_BROWSERS_DIR, cmd[0])
        self.q.put(("log", "Downloading the Built-in Chromium (~170 MB)…"))
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            cmd + ["install", "chromium", "--no-shell"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            env=env, creationflags=creationflags)
        last_emit = 0.0
        last_line = ""
        try:
            for line in proc.stdout:
                if self.cancel.is_set():
                    proc.kill()
                    proc.wait()
                    log.info("chromium: download cancelled by user")
                    self.q.put(("log", "Download cancelled."))
                    return False
                # The installer colors its output; ANSI codes would land in
                # the log pane as "[2m" noise.
                line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
                if not line:
                    continue
                last_line = line
                now = time.monotonic()
                if now - last_emit >= 2.0:        # the installer is chatty
                    self.q.put(("log", f"  {line}"))
                    last_emit = now
        finally:
            proc.stdout.close()
        rc = proc.wait()
        if rc != 0:
            log.warning("chromium: installer exited %s (last: %s)", rc, last_line)
            raise RuntimeError(
                "The browser download didn't complete (check the network / "
                "VPN connection and try again).")
        if not any(DOWNLOADED_BROWSERS_DIR.glob("chromium-*")):
            raise RuntimeError("The download finished but no browser was "
                               "found afterwards (details in the log).")
        log.info("chromium: download complete")
        return True

    def _delete(self):
        import shutil
        if not DOWNLOADED_BROWSERS_DIR.is_dir():
            self.q.put(("log", "There was no downloaded browser to remove."))
            return
        failures = []
        shutil.rmtree(DOWNLOADED_BROWSERS_DIR,
                      onerror=lambda _fn, p, _exc: failures.append(str(p)))
        if failures or DOWNLOADED_BROWSERS_DIR.exists():
            log.warning("chromium: delete left %d item(s): %s",
                        len(failures), failures[:5])
            raise RuntimeError(
                "Some browser files couldn't be removed — close the app and "
                "delete the data\\ms-playwright folder by hand, or restart "
                "and try again.")
        log.info("chromium: downloaded browser deleted")


class EnvCheckWorker(threading.Thread):
    """The idle "Verify environment" action: open TSMIS headless exactly the
    way an export would (saved session, else device sign-in), read which data
    source / environment the app ACTUALLY loaded (the page's CONFIG — the
    same source _site_params_ok trusts), and screenshot the page so the user
    can see the site's own SSOR/ARS + env label with their own eyes.

    Always posts one ('env_shot', dict) message — also on failure (with
    `error` set) — so the GUI task state can never wedge."""

    def __init__(self, queue):
        super().__init__(daemon=True, name="envcheck")
        self.q = queue

    def run(self):
        from playwright.sync_api import sync_playwright
        out = {"ok": False, "img": None, "env": None, "src": None,
               "matches": None, "url": get_url(), "error": None}
        want_src, want_env = get_site()
        log.info("env check: starting (selected src=%s env=%s)", want_src, want_env)
        try:
            with sync_playwright() as p:
                browser, _ctx, page = new_authed_browser(p)
                try:
                    navigate_with_auth(page)
                    # The address the screenshot will show: the page's REAL
                    # URL (token fragment stripped), not just the intended one.
                    out["url"] = page_url_for_display(page) or out["url"]
                    if not is_logged_in(page):
                        out["error"] = ("Sign-in didn't complete, so the report "
                                        "page couldn't be checked. Log in, then "
                                        "try again.")
                    else:
                        out["ok"] = True
                        try:
                            got = page.evaluate(_CONFIG_JS)   # [env, src] or None
                        except Exception:
                            got = None
                        if got:
                            out["env"], out["src"] = got[0], got[1]
                            out["matches"] = (got == [want_env, want_src])
                    try:
                        out["img"] = base64.b64encode(
                            page.screenshot(type="jpeg", quality=70)).decode("ascii")
                    except Exception as e:
                        log.info("env check: screenshot failed (%s)", type(e).__name__)
                finally:
                    browser.close()
        except (AuthError, BrowserNotFoundError, PreflightError) as e:
            out["error"] = str(e)            # messages are already user-safe
        except Exception as e:
            log.exception("env check crashed")
            out["error"] = f"{type(e).__name__}: {e}"
        log.info("env check: done ok=%s page env=%s src=%s matches=%s url=%s "
                 "error=%s", out["ok"], out["env"], out["src"], out["matches"],
                 out["url"], out["error"] or "-")
        self.q.put(("env_shot", out))


# Availability of each report type in the #customReport dropdown, WITHOUT
# clicking anything (the li.cs-option items are in the DOM whether the list is
# open or not). The site sometimes greys single report types out; the exact
# disable convention isn't pinned, so every common signal counts — a class
# containing "disabled", the disabled/data-disabled attributes, aria-disabled,
# or pointer-events:none — and each non-ok option's class string goes to the
# log so a different convention shows up in one upload. Returns null when the
# option list can't be read at all (callers must treat that as "unknown",
# never as "everything is missing").
_REPORT_OPTIONS_JS = """(labels) => {
  const items = Array.from(document.querySelectorAll('#customReport li.cs-option'));
  if (!items.length) return null;
  const out = {};
  for (const label of labels) {
    const el = items.find((li) => (li.textContent || '').trim() === label)
            || items.find((li) => (li.textContent || '').includes(label));
    if (!el) { out[label] = { state: 'missing' }; continue; }
    const cls = el.className || '';
    const greyed = /(^|[\\s_-])disabled([\\s_-]|$)/i.test(cls)
      || el.hasAttribute('disabled')
      || el.getAttribute('aria-disabled') === 'true'
      || el.hasAttribute('data-disabled')
      || getComputedStyle(el).pointerEvents === 'none';
    out[label] = { state: greyed ? 'greyed' : 'ok', cls };
  }
  return out;
}"""


def env_verdict(config_readable, reports_readable):
    """Fail-closed verdict for a combo that signed in AND pulled report data:
    returns (status, detail). If the site's CONFIG (the environment
    confirmation) or its report-type list couldn't be read, report "unverified"
    (a future contract change must never read as a silent green "ok") naming what
    couldn't be confirmed; otherwise "ok". Pure -> unit-tested directly (the rest
    of the scan needs a live browser)."""
    unconfirmed = []
    if not config_readable:
        unconfirmed.append("the environment couldn't be confirmed from the site")
    if not reports_readable:
        unconfirmed.append("the report-type list couldn't be read "
                           "(only one type was checked)")
    if unconfirmed:
        return "unverified", ("Signed in and pulled report data, but "
                              + "; ".join(unconfirmed) + ".")
    return "ok", "Sign-in and report data OK."


class EnvScanWorker(threading.Thread):
    """The "Check all environments" scan (Settings button + the automatic
    run after startup/sign-in): probe EVERY data source / environment
    combination headless, the way an export would — does sign-in complete,
    does the page load the requested site, can the report form pull data,
    and is every report type offered? The page ships its whole form in
    static HTML even signed out, so form presence proves nothing; only a
    real preflight (report picked, District fanned out, the site's own data
    round-trip enabling the County dropdown) shows report access — "signs in
    fine but can't actually pull reports" is exactly the failure this exists
    to surface.

    FAST on purpose (it runs unprompted after startup): combos are drained
    from a shared queue by up to 3 scanner threads, each owning its own
    Playwright/browser (the fast-mode idiom — the sync API is thread-affine)
    and pinning its target via common.set_thread_site, so the user's header
    selection is never touched and parallel combos can't race each other.
    Device sign-in mode (no saved auth file) caps the scan to ONE thread:
    the persistent Edge profile can only be open in one browser — the same
    rule fast mode applies.

    Posts one ("env_access", dict) per combo AS IT FINISHES (the Settings
    rows and the title-bar chip update live), then ("env_access_done", dict).
    Cancel is honored BETWEEN combos — each combo is already bounded by the
    sign-in budget and the preflight/county timeouts."""

    MAX_SCANNERS = 3

    def __init__(self, queue, cancel_event):
        super().__init__(daemon=True, name="envscan")
        self.q = queue
        self.cancel = cancel_event

    def run(self):
        from reports import EXPORT_REPORTS
        # (registry label for the verdict/UI, dropdown option text to probe &
        # select). These DIFFER for "Highway Log (PDF)": its dropdown option is the
        # same "Highway Log" the Excel export uses (the PDF is that report saved a
        # different way), so probing the registry label would never match the
        # dropdown and would falsely flag it "missing" on every environment.
        report_specs = [(label, getattr(spec, "label", None) or label)
                        for label, _fmt, spec in EXPORT_REPORTS]
        combos = [(s, e) for s in DATA_SOURCES for e in ENVIRONMENTS]
        n = min(self.MAX_SCANNERS, len(combos)) if has_valid_auth() else 1
        if n > 1:
            n = self._parallel_scanners(n)
        log.info("env scan: starting (%d combos, %d scanner browser(s), "
                 "report types %s)", len(combos), n, [r for r, _d in report_specs])
        work = queue_mod.Queue()
        for combo in combos:
            work.put(combo)
        results = {}                      # key -> result dict (lock-protected)
        fatals = []
        lock = threading.Lock()

        def scanner(worker_no):
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    browser = page = None
                    try:
                        while not self.cancel.is_set():
                            try:
                                src, env = work.get_nowait()
                            except queue_mod.Empty:
                                break
                            set_thread_site(src, env)
                            if browser is None:
                                # Scanners run several saved-session browsers
                                # at once -> the parallel channel (not Edge).
                                browser, _ctx, page = new_authed_browser(
                                    p, parallel=True)
                            out = self.check_one(page, src, env, report_specs)
                            with lock:
                                results[out["key"]] = out
                            self.q.put(("env_access", out))
                    finally:
                        set_thread_site(None, None)
                        if browser is not None:
                            try:
                                browser.close()
                            except Exception:
                                pass
            except (AuthError, BrowserNotFoundError) as e:
                # This scanner is out; the others keep draining the queue.
                log.warning("env scan: scanner %d stopped (%s: %s)",
                            worker_no, type(e).__name__, e)
                with lock:
                    fatals.append(str(e))    # messages are already user-safe
            except Exception as e:
                log.exception("env scan: scanner %d crashed", worker_no)
                with lock:
                    fatals.append(f"{type(e).__name__}: {e}")

        threads = [threading.Thread(target=scanner, args=(i + 1,),
                                    daemon=True, name=f"envscan-w{i + 1}")
                   for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        cancelled = self.cancel.is_set()
        fatal = fatals[0] if fatals and len(fatals) == n else None
        if fatal and not cancelled:
            # EVERY scanner died (e.g. no usable login at all): fill the
            # unchecked combos so no row is left saying "checking".
            for src, env in combos:
                key = f"{src}-{env}"
                if key in results:
                    continue
                out = {"key": key, "source": src, "environment": env,
                       "label": f"{DATA_SOURCE_LABELS[src]} / "
                                f"{ENVIRONMENT_LABELS[env]}",
                       "status": "error", "detail": fatal, "url": "",
                       "reports": {}}
                results[key] = out
                self.q.put(("env_access", out))
        ok = sum(1 for r in results.values() if r["status"] == "ok")
        log.info("env scan: done ok=%d/%d cancelled=%s fatal=%s",
                 ok, len(results), cancelled, fatal or "-")
        self.q.put(("env_access_done",
                    {"ok": ok, "done": len(results), "total": len(combos),
                     "cancelled": cancelled, "error": fatal}))

    def _parallel_scanners(self, n):
        """Parallel scanning only when the parallel channel is an unmanaged
        Chromium (Built-in Chromium / Chrome + a saved login): if the only
        usable browser is managed Edge, three concurrent sessions are the
        exact failure fast mode hit in the field — scan serially instead.
        The resolution is probed once and cached, so this costs ~a second
        the first time and nothing after."""
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                channel = resolve_parallel_channel(p)
        except Exception as e:
            log.info("env scan: parallel channel pre-check failed (%s) — "
                     "scanning serially", type(e).__name__)
            return 1
        if channel == "msedge":
            log.info("env scan: only managed Edge is usable — scanning "
                     "serially (no concurrent Edge sessions)")
            return 1
        return n

    @staticmethod
    def check_one(page, src, env, report_labels, *, budget_s=60):
        """One combo's verdict — shared by this scan (all six combos) and the
        quiet ActiveEnvCheckWorker (the selected combo). Never raises: the answer
        (crashes included) rides in the returned dict's status/detail; the WHY is
        in the log and the auth/preflight dumps the shared gates already write.
        `budget_s` bounds the sign-in loop (short for the background check)."""
        label = f"{DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]}"
        out = {"key": f"{src}-{env}", "source": src, "environment": env,
               "label": label, "status": "error", "detail": "", "url": "",
               "reports": {}}
        t0 = time.monotonic()
        try:
            try:
                navigate_with_auth(page, budget_s=budget_s)
            except SiteUnreachableError as e:
                # Don't read page.url here: the failed goto leaves the page
                # parked on the PREVIOUS combo's address.
                out["status"], out["detail"] = "unreachable", str(e)
                return out
            out["url"] = page_url_for_display(page)
            if not is_logged_in(page):
                signals = auth_state(page).get("signals")
                denied = (isinstance(signals, dict) and
                          str(signals.get("accessDenied", "")).startswith("visible"))
                if denied:
                    out["status"] = "denied"
                    out["detail"] = ("Signs in, but TSMIS reports access "
                                     "denied on this site.")
                else:
                    out["status"] = "no_signin"
                    out["detail"] = "Sign-in didn't complete on this site."
                return out
            got = None
            try:
                got = page.evaluate(_CONFIG_JS)          # [env, src] or None
            except Exception:
                pass
            # _CONFIG_JS returns null when the site's CONFIG can't be read (a
            # future rename), so None here = "couldn't confirm the environment".
            config_readable = got is not None
            if got and got != [env, src]:
                out["status"] = "wrong_site"
                out["detail"] = (f"The page loaded {(got[1] or '?').upper()} / "
                                 f"{(got[0] or '?').upper()} instead — check "
                                 "this row's address.")
                return out
            # Which of the report types is actually offered? The site
            # sometimes greys single types out. None readable = unknown
            # (keep the old first-report probe), never "all missing".
            # Probe the dropdown by the OPTION TEXT (de-duplicated — the Excel and
            # PDF Highway Log share one "Highway Log" option), and key the verdict
            # by the registry label the UI reads. None readable = unknown (keep the
            # old first-report probe), never "all missing".
            probe = list(dict.fromkeys(drop for _reg, drop in report_labels))
            options = None
            try:
                options = page.evaluate(_REPORT_OPTIONS_JS, probe)
            except Exception as e:
                log.info("env scan: %s report dropdown read failed (%s)",
                         out["key"], type(e).__name__)
            if options:
                out["reports"] = {reg: options.get(drop, {}).get("state", "missing")
                                  for reg, drop in report_labels}
                for reg, drop in report_labels:
                    state = out["reports"][reg]
                    if state != "ok":
                        log.info("env scan: %s report %r is %s (class=%r)",
                                 out["key"], reg, state,
                                 options.get(drop, {}).get("cls", ""))
            # An AVAILABLE dropdown option text, for the preflight round-trip
            # (preflight SELECTS the report, so it takes the option text).
            avail_drop = [drop for reg, drop in report_labels
                          if out["reports"].get(reg) == "ok"]
            off = [reg for reg, state in out["reports"].items() if state != "ok"]
            if options and not avail_drop:
                out["status"] = "no_reports"
                out["detail"] = ("Signs in, but every report type is greyed "
                                 "out or missing here.")
                return out
            try:
                # The data probe, on the first AVAILABLE report type: County
                # only enables once the site's own route/county round-trip
                # answers (the form itself is static).
                preflight(page, avail_drop[0] if avail_drop else probe[0])
            except PreflightError:
                out["status"] = "no_reports"
                out["detail"] = ("Signs in, but the report form couldn't load "
                                 "its data — reports would fail here.")
                return out
            if off:
                out["status"] = "reports_off"
                out["detail"] = ("Sign-in and report data OK, but unavailable "
                                 "here: " + ", ".join(off) + ".")
                return out
            # Clean sign-in + working report data. The fail-closed verdict logic
            # (don't claim a green "ok" when the site's CONFIG or report list
            # couldn't be read) is a pure mapping, factored out so it's unit
            # tested directly (the rest of this method needs a live browser).
            out["status"], out["detail"] = env_verdict(config_readable,
                                                        options is not None)
            return out
        except Exception as e:
            reason = str(e).splitlines()[0] if str(e) else type(e).__name__
            log.warning("env scan: %s check crashed (%s: %s)", out["key"],
                        type(e).__name__, reason)
            out["detail"] = f"The check failed unexpectedly ({reason})."
            return out
        finally:
            log.info("env scan: %s -> %s in %.1fs (%s)", out["key"],
                     out["status"], time.monotonic() - t0, out["detail"] or "-")


class ActiveEnvCheckWorker(threading.Thread):
    """The QUIET, single-combo env check for the CURRENTLY selected site, run
    unprompted on app start and after an env switch. Where EnvScanWorker probes
    all six combos on the user's command, this checks just ONE — the selected
    src/env — in the background to:
      • prove Edge one-click / device sign-in works (so the title-bar chip lights
        without anyone pressing "Log in"), and
      • refresh that env's report availability, feeding the Export-tab AND the
        matrix warning flags.
    Single browser, short sign-in budget so a managed PC's silent SSO completes
    but an unreachable machine fails fast. Pins its own thread site so the user's
    live header selection is never touched. QUIET on every failure (no modal) — a
    failed check simply doesn't light the chip. `seq` lets a newer env switch
    supersede a result still in flight.

    Posts ("env_access", verdict) [verdict["quiet"]=True] then
    ("active_env_done", {seq, key, signed_in, via_device})."""

    BUDGET_S = 20        # sign-in budget: enough for silent SSO, short on failure

    def __init__(self, queue, src, env, seq):
        super().__init__(daemon=True, name="activeenv")
        self.q = queue
        self.src = src
        self.env = env
        self.seq = seq

    def run(self):
        from reports import EXPORT_REPORTS
        from playwright.sync_api import sync_playwright
        report_specs = [(label, getattr(spec, "label", None) or label)
                        for label, _fmt, spec in EXPORT_REPORTS]
        key = f"{self.src}-{self.env}"
        had_file = has_valid_auth()        # classify device vs saved-file sign-in
        signed_in = False
        set_thread_site(self.src, self.env)
        try:
            with sync_playwright() as p:
                browser = None
                try:
                    # Non-parallel: a saved file → the chosen Chromium browser;
                    # no file → the device Edge context (the path that PROVES the
                    # one-click). Either way a 3-tuple whose first item .close()s.
                    browser, _ctx, page = new_authed_browser(p)
                    verdict = EnvScanWorker.check_one(page, self.src, self.env,
                                                      report_specs,
                                                      budget_s=self.BUDGET_S)
                    verdict["quiet"] = True    # suppress the per-combo scan log line
                    self.q.put(("env_access", verdict))
                    signed_in = verdict["status"] not in (
                        "no_signin", "denied", "unreachable", "error")
                finally:
                    if browser is not None:
                        try:
                            browser.close()
                        except Exception:
                            pass
        except Exception as e:
            log.info("active env check: %s quiet failure (%s: %s)", key,
                     type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        finally:
            set_thread_site(None, None)
        # via_device only when we signed in WITHOUT a saved file — that's the
        # path that actually exercised (and so proves) Edge one-click.
        self.q.put(("active_env_done",
                    {"seq": self.seq, "key": key, "signed_in": signed_in,
                     "via_device": signed_in and not had_file}))


class LoginWorker(threading.Thread):
    """Opens a headed browser for SSO+MFA, waits for the user to signal done
    (done_event, set by a GUI button), then saves the storage_state.

    cancel_event also sets done_event to unblock the wait; if cancel is set the
    session is NOT saved.
    """

    def __init__(self, queue, done_event, cancel_event):
        super().__init__(daemon=True, name="login")
        self.q = queue
        self.done = done_event
        self.cancel = cancel_event

    _CANCELLED = object()

    def run(self):
        from playwright.sync_api import sync_playwright
        log = logging.getLogger("tsmis.login")
        try:
            with sync_playwright() as p:
                # The quiet background active-env check now OWNS silent Edge
                # one-click sign-in. The button's job is to CAPTURE a portable
                # saved login (what fast mode needs, and what normal exports
                # restore) via a headed window in the chosen Chromium-class
                # browser — Chrome by default (preferred when installed), or the
                # Built-in Chromium when that's the pick or Chrome is absent.
                pref = get_preferred_channel()          # 'chrome'|'chromium'|None
                log.info("login: starting (export browser: %s)",
                         pref or "auto (Chrome-first)")
                order = (["chromium", "chrome"] if pref == "chromium"
                         else ["chrome", "chromium"])
                for ch in order:
                    if ch == "chromium" and "chromium" not in BROWSER_CHANNELS:
                        continue
                    try:
                        browser = p.chromium.launch(headless=False, channel=ch,
                                                    args=LOGIN_BROWSER_ARGS)
                    except Exception as e:
                        log.info("login: %s launch failed (%s)", ch, type(e).__name__)
                        continue
                    self._run_login_in_browser(browser, CHANNEL_LABELS[ch], log)
                    return

                # No Chrome/Chromium could open (an Edge-only managed PC): fall
                # back to the persistent-profile Edge recapture, validating the
                # capture is portable before saving (a Windows device-broker/PRT
                # session can't be reused elsewhere -> device mode instead).
                self.q.put(("log", "No Chrome/Chromium browser is available; "
                                   "signing in with Microsoft Edge..."))
                edge_state = self._try_edge_persistent_login(p, log)
                if edge_state is self._CANCELLED:
                    self.q.put(("cancelled", None))
                    return
                if edge_state:
                    # A capture from the live Edge profile can still be useless:
                    # when Edge signed in through the Windows device broker (PRT)
                    # the session never reaches the cookie jar, so the saved file
                    # would not log in anywhere else. Prove the capture works the
                    # way the engine will use it before saving it.
                    self.q.put(("log", "Checking that the captured sign-in can be "
                                       "reused for exports..."))
                    if storage_state_is_portable(p, edge_state):
                        self._save_state(edge_state)
                        self.q.put(("login_saved", None))
                        log.info("login: SAVED via Edge recapture")
                        return
                    # Device-bound capture: don't save it, but exports can still
                    # sign themselves in live (device mode).
                    log.info("login: Edge capture device-bound (not portable); "
                             "device mode")
                    self.q.put(("login_device_ok", None))
                    return
                self.q.put(("error", ("general",
                            "No usable web browser was found to sign in. Install "
                            "Google Chrome or Microsoft Edge, then try again.")))
        except BrowserNotFoundError as e:
            self.q.put(("error", ("general", str(e))))
        except Exception as e:
            log.exception("login worker crashed")
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))

    def _try_edge_persistent_login(self, p, log):
        ctx = None
        cdp_url = None
        try:
            ctx, cdp_url = launch_edge_login_context(p)
        except Exception as e:
            log.info("login: experimental Edge launch unavailable (%s)", type(e).__name__)
            self.q.put(("log", "Experimental Edge sign-in could not open; "
                               "using Google Chrome fallback."))
            return None

        self.done.clear()
        self.q.put(("login_open", None))
        self.q.put(("log", "Experimental Edge sign-in opened. Finish signing in, "
                           "then click \"I've finished logging in.\""))
        log.info("login: experimental Edge persistent profile opened")

        while not self.done.wait(0.2):
            pass

        if self.cancel.is_set():
            self._safe_close_context(ctx)
            log.info("login: cancelled during experimental Edge sign-in")
            return self._CANCELLED

        try:
            state = capture_storage_state_if_logged_in(ctx)
            if state:
                self._safe_close_context(ctx)
                log.info("login: experimental Edge captured from live context")
                return state
        except Exception as e:
            log.info("login: live Edge context capture failed (%s)", type(e).__name__)

        self.q.put(("log", "Edge did not expose a live session; trying to recapture "
                           "the work-profile state..."))
        state = capture_edge_login_state_over_cdp(p, cdp_url)
        if state:
            self._safe_close_context(ctx)
            log.info("login: experimental Edge captured over CDP")
            return state

        self._safe_close_context(ctx)
        state, profile_name = capture_edge_login_state_from_profiles(p)
        if state:
            log.info("login: experimental Edge captured from profile %s", profile_name)
            return state

        log.info("login: experimental Edge capture failed")
        return None

    def _run_login_in_browser(self, browser, label, log):
        """Drive a normal (non-persistent) headed sign-in in `browser` and save
        the session once a real TSMIS login is seen. Used for the Built-in
        Chromium path and the Chrome fallback."""
        # Pre-granted local-network-access context: otherwise Chrome prompts
        # per sign-in and an unanswered prompt blocks the signed-in UI, so the
        # login is never detected (see common.LOGIN_BROWSER_ARGS).
        ctx = new_login_context(browser)
        page = ctx.new_page()
        page.goto(get_url())
        self.done.clear()
        self.q.put(("login_open", None))
        self.q.put(("log", f"Sign-in window opened in {label}."))

        # Wait for the user to finish (the "I've finished" button sets
        # self.done) OR to close the whole browser window. Capture the session
        # the instant a real TSMIS login appears, so closing the window AFTER
        # signing in still saves it.
        #
        # ROBUSTNESS: the SSO/MFA sign-in navigates, can open a popup, and may
        # replace the original tab, and a single Playwright call can blip
        # mid-redirect. So we must NOT treat one ctx.cookies() error -- nor the
        # *original* tab closing -- as "the user gave up" (that bug once slammed
        # the window shut the instant a password went through and reported
        # "cancelled"). The only reliable "user closed the window" signal is
        # that NO tabs remain open in the context (the SSO dance always keeps
        # >= 1 tab), with a long all-calls-failing streak as a backstop for a
        # truly dead connection.
        captured = None
        closed = False
        blips = 0
        while not self.done.wait(0.3):
            try:
                ctx.cookies()                   # pump Playwright events
                blips = 0
            except Exception:
                blips += 1      # transient mid-redirect blip, or gone -- decided below
            try:
                open_pages = [pg for pg in ctx.pages if not pg.is_closed()]
            except Exception:
                open_pages = None   # context momentarily unavailable; re-check next tick
            if (open_pages is not None and len(open_pages) == 0) or blips >= 20:
                closed = True   # every tab gone (or ~6s unreachable) -> window closed
                break
            if captured is None:
                try:
                    if self._any_logged_in(ctx):
                        captured = ctx.storage_state()
                except Exception:
                    pass        # mid-navigation; retry on the next tick

        if closed:
            self.q.put(("log", "Login window closed - checking your sign-in..."))

        if self.cancel.is_set():
            self._safe_close(browser)
            self.q.put(("cancelled", None))
            log.info("login: cancelled during %s sign-in", label)
            return

        if not closed:
            try:
                if self._any_logged_in(ctx):
                    captured = ctx.storage_state()
            except Exception:
                pass
        self._safe_close(browser)

        if captured:
            self._save_state(captured)
            self.q.put(("login_saved", None))
            log.info("login: SAVED via %s", label)
        elif closed:
            self.q.put(("cancelled", None))
            log.info("login: %s window closed without capture", label)
        else:
            self.q.put(("login_failed", None))
            log.info("login: %s finished without detected login", label)

    @staticmethod
    def _any_logged_in(ctx):
        """True if ANY page in the context is the logged-in TSMIS report page
        (SSO sometimes lands it in a popup / new tab, not the original page)."""
        for pg in ctx.pages:
            try:
                if is_logged_in(pg):
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _safe_close(browser):
        try:
            browser.close()
        except Exception:
            pass

    @staticmethod
    def _safe_close_context(ctx):
        try:
            ctx.close()
        except Exception:
            pass

    @staticmethod
    def _save_state(state):
        save_auth_state(state)          # logs path + cookie count


class UpdateWorker(threading.Thread):
    """Drives the one-click update (updater.py) off the GUI thread: action
    "check" compares the latest GitHub release tag to this build; action
    "download" streams + stages the matching release zip. Network + disk
    only, no Playwright. Posts ('update_status', {phase, ...}) — the dict is
    the GUI's whole update state; see gui_api._on_update_status.

    `manual` marks a user-initiated check (the outcome is shown in the log
    pane; the automatic launch check stays quiet unless an update exists).
    """

    def __init__(self, queue, action, manual=False, info=None):
        super().__init__(daemon=True, name="update")
        self.q = queue
        self.action = action            # "check" | "download" | "revert"
        self.manual = manual
        self.info = info                # UpdateInfo (required for "download")

    def run(self):
        import updater                  # lazy; stdlib-only module
        revert = self.action == "revert"
        try:
            if self.action == "check":
                info = updater.check_for_update()
                if info is None:
                    self.q.put(("update_status", {"phase": "none",
                                                  "manual": self.manual}))
                    return
                self.q.put(("update_status", {
                    "phase": "available",
                    "version": info.version,
                    "url": info.release_url,
                    "size_mb": round(info.asset_size / 1e6) or None,
                    "can_apply": updater.update_support()[0] == "ok",
                    "manual": self.manual,
                    "_info": info,      # kept Python-side; stripped before JS
                }))
                return

            if revert:
                # Resolve the newest full release older than this build, then
                # stage it through the SAME proven download path as an update.
                self.info = updater.resolve_previous_release()
                if self.info is None:
                    self.q.put(("update_status", {
                        "phase": "none", "manual": True, "revert": True,
                        "note": "no earlier version was found to revert to"}))
                    return

            last_pct = -1               # "download" / "revert"

            def on_progress(done, total):
                nonlocal last_pct
                pct = min(100, int(done * 100 / total)) if total else 0
                if pct != last_pct:
                    last_pct = pct
                    self.q.put(("update_status", {
                        "phase": "downloading", "progress": pct,
                        "version": self.info.version,
                        "url": self.info.release_url, "can_apply": True,
                        "revert": revert}))

            staged = updater.download_and_stage(self.info, on_progress=on_progress)
            self.q.put(("update_status", {
                "phase": "staged", "version": self.info.version,
                "url": self.info.release_url, "can_apply": True,
                "staged": str(staged), "revert": revert}))
        except updater.UpdateError as e:
            log.warning("update %s failed: %s", self.action, e)
            self.q.put(("update_status", {
                "phase": "failed", "note": str(e),
                "manual": self.manual or self.action in ("download", "revert"),
                "revert": revert}))
        except Exception as e:
            log.exception("update worker crashed (%s)", self.action)
            self.q.put(("update_status", {
                "phase": "failed", "note": f"{type(e).__name__}: {e}",
                "manual": self.manual or self.action in ("download", "revert"),
                "revert": revert}))


# --- startup readiness checks -------------------------------------------------
# (Login isn't checked here -- the header status row + Log in button own it.)

def _check_output():
    try:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        probe = OUTPUT_ROOT / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return ("ok", "Output folder: writable")
    except Exception:
        return ("bad", "Output folder: NOT writable")


def _check_tools():
    try:
        import pdfplumber  # noqa: F401
        import openpyxl    # noqa: F401
        return ("ok", "Report tools (PDF/Excel): ready")
    except Exception as e:
        return ("bad", f"Report tools: missing ({type(e).__name__})")


class CheckWorker(threading.Thread):
    """Runs the launch-time readiness checks off the Tk thread, posting each
    result as ('check', (key, status, text)) and a final ('checks_done', dict).

    The instant checks (login, output folder, PDF/Excel tools) are posted first;
    the browser probes are slower (each launches a headless browser) so they land
    a couple seconds later. status is one of 'ok' | 'bad'.
    """

    def __init__(self, queue):
        super().__init__(daemon=True, name="checks")
        self.q = queue

    def run(self):
        for key, fn in (("output", _check_output), ("tools", _check_tools)):
            try:
                status, text = fn()
            except Exception as e:
                status, text = "bad", f"{key}: error ({type(e).__name__})"
            if status != "ok":
                log.warning("readiness check %s: %s", key, text)
            self.q.put(("check", (key, status, text)))

        try:
            results = check_browsers()           # {channel: ok|missing|broken}
        except Exception:
            log.exception("browser readiness check crashed")
            results = {ch: "broken" for ch in BROWSER_CHANNELS}
        detail = {"ok": "ready", "missing": "not installed",
                  "broken": "found, but this tool can't control it (it may be too new)"}
        for ch in BROWSER_CHANNELS:
            status = results.get(ch, "broken")
            self.q.put(("check", (f"browser_{ch}", "ok" if status == "ok" else "bad",
                                   f"{CHANNEL_LABELS[ch]}: {detail[status]}")))
        self.q.put(("checks_done", results))


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
    try:
        ew._run_specs(ew._build_events(), [])
    finally:
        if on_worker:
            on_worker(None)


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
                    _run_matrix_export_step(spec, src, env, self.dest, self.q,
                                            self.cancel, self.skip, self.pause,
                                            self.workers, on_worker=self.on_worker,
                                            dated=self.dated)
                    ok += 1
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
                 force_consolidate=False, also_formulas=False):
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

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
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
                        also_formulas=self.also_formulas)
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
                 force_consolidate=False, also_formulas=False):
        super().__init__(daemon=True, name="day-matrix-compare")
        self.source = source
        self.cells = [(c[0], c[1]) for c in cells]   # (date, row_key)
        self.dest = dest
        self.q = queue
        self.cancel = cancel_event
        self.tsn_files = tsn_files or {}
        self.force_consolidate = force_consolidate
        self.also_formulas = also_formulas

    def run(self):
        events = Events(is_cancelled=self.cancel.is_set,
                        on_log=lambda m: self.q.put(("log", m)))
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
                        also_formulas=self.also_formulas)
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
