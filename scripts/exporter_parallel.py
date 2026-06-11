"""EXPERIMENTAL parallel export engine -- "fast mode".

Runs several headless browsers at once, each logged in with the SAME saved
session, pulling routes off a shared work queue until it is empty. This is
purely a speed optimization layered on top of the proven sequential engine
(`exporter.run_export`), which is left completely untouched. The per-route
mechanics -- arm the form, click Generate, wait, save, retry-once on a
transient error, screenshot a hard failure, record the outcome -- are REUSED
from `exporter.py` (`_process_route`, `_record`, `_capture_failure`). Only the
concurrency/coordination is new, so a per-report bug fix in the sequential
engine automatically benefits fast mode too.

Why a shared queue instead of static route shards? A few routes (5, 99, 101...)
take minutes while most take seconds. A queue is self-balancing: a worker that
draws fast routes immediately pulls another, so no single worker gets stuck with
all the slow ones and finishes long after the rest.

How many workers can we realistically use?
  Operator testing shows the shared TSMIS / Caltrans backend handles high
  concurrency fine, so the practical limit is now YOUR PC, not the server: each
  worker is one Chromium process (~300-500 MB under load) plus a Playwright
  driver, so RAM and CPU are what cap useful concurrency.
    * 3 browsers    -- safe default, ~2.5-3x faster (DEFAULT_WORKERS)
    * 8-12 browsers -- big speedup on a healthy multi-core PC with RAM to spare
    * 30 browsers   -- hard cap (MAX_WORKERS); ~9-15 GB RAM for browsers alone,
                       so only on a well-resourced machine
  Pick by the machine running it: budget ~0.5 GB RAM per worker and leave
  headroom. Requested counts are clamped to [1, MAX_WORKERS].

Threading model: Playwright's sync API is thread-affine, so each worker owns its
OWN sync_playwright() instance, browser, context and page, and never shares a
Playwright object across threads. Workers report through the same Events sink as
the sequential engine. The only shared mutable state is the work queue, a couple
of threading.Events, and per-worker RunResults that are merged at the very end
(no locking on the hot path).
"""
import logging
import os
import queue
import threading

from playwright.sync_api import sync_playwright

from common import (
    FAST_REPORT_TIMEOUT_MS,
    RETRY_REPORT_TIMEOUT_MS,
    ROUTES,
    AuthError,
    RunCancelled,
    has_valid_auth,
    is_logged_in,
    navigate_with_auth,
    new_authed_browser,
    preflight,
    select_report,
)
from events import Events, RunResult
# Reuse the proven per-route mechanics and the serial retry pass from the
# sequential engine, so a per-report fix benefits both.
from exporter import _capture_failure, _process_route, _record, _retry_failed_routes
from paths import output_day_dir
from run_report import auto_report_path, write_run_report

log = logging.getLogger("tsmis.export.parallel")

# Number of concurrent browsers. The TSMIS backend handles high concurrency fine
# (operator-tested), so the real limit is client RAM/CPU -- budget ~0.5 GB per
# worker. 3 is a safe default; the cap is generous for well-resourced PCs.
DEFAULT_WORKERS = 3
MAX_WORKERS = 30


def resolve_worker_count(requested=None):
    """Clamp a requested worker count into [1, MAX_WORKERS].

    requested=None falls back to the TSMIS_FAST_WORKERS environment variable,
    then DEFAULT_WORKERS. Garbage in (None, "", non-numeric) -> DEFAULT_WORKERS.
    Always returns a sane int >= 1.
    """
    if requested is None:
        env = os.environ.get("TSMIS_FAST_WORKERS", "").strip()
        requested = int(env) if env.isdigit() else DEFAULT_WORKERS
    try:
        requested = int(requested)
    except (TypeError, ValueError):
        requested = DEFAULT_WORKERS
    return max(1, min(requested, MAX_WORKERS))


def _worker_events(real, stop):
    """A per-worker Events sink.

    Forwards on_log / on_route / is_cancelled to the shared sink, but makes
    should_skip a no-op: with several routes in flight, "skip the route being
    waited on" is ambiguous, so per-route Skip is intentionally disabled in fast
    mode (use Cancel to stop the whole run). is_cancelled also reflects the
    shared stop flag so a fatal error in one worker quiets the others.
    """
    return Events(
        on_log=real.on_log,
        on_route=real.on_route,
        should_skip=lambda: False,
        is_cancelled=lambda: stop.is_set() or real.is_cancelled(),
    )


def _preflight_once(spec, events):
    """Validate auth + the report form a single time, before launching N
    browsers, so a bad session or a changed site fails fast with one clear
    error instead of N. Raises AuthError / PreflightError like the sequential
    engine."""
    with sync_playwright() as p:
        browser, _ctx, page = new_authed_browser(p)
        try:
            navigate_with_auth(page)
            if not is_logged_in(page):
                raise AuthError(
                    "Sign-in didn't complete - the saved session may be expired, "
                    "or automatic sign-in isn't available on this PC. Please log in."
                )
            events.on_log("Logged in. Checking the report form...")
            preflight(page, spec.label)
        finally:
            browser.close()


def _retry_failed_sequential(spec, events, result, out_dir, timeout_ms):
    """Retry the run's failed routes in a SINGLE fresh browser, one at a time.

    Fast mode's failures are usually big reports that ran out of time while N
    browsers hammered the server. Retrying them serially (no concurrent load,
    generous timeout) is the most likely way to finally land them, and matches
    the user's expectation that "failed reports run one at a time." Delegates the
    per-route work to the sequential engine's shared retry helper.
    """
    with sync_playwright() as p:
        browser, _ctx, page = new_authed_browser(p)
        try:
            _retry_failed_routes(page, spec, events, result, out_dir, timeout_ms)
        finally:
            browser.close()


def run_export_parallel(spec, events=None, *, workers=None, routes=ROUTES,
                        timeout_ms=None, retry_timeout_ms=None):
    """Export `spec` for every route using several concurrent browsers.

    A drop-in alternative to exporter.run_export with the same contract: returns
    a merged RunResult, raises AuthError / PreflightError the same way, honors
    events.is_cancelled() (checked between routes), and skips routes whose output
    file already exists -- so it resumes a previous run just like the sequential
    engine. Per-route SKIP is disabled in fast mode (see _worker_events).

    Each worker uses a more generous per-route ceiling (FAST_REPORT_TIMEOUT_MS by
    default) because the concurrent load slows the server. After all workers
    finish, any routes that still failed get one serial retry in a single browser
    (retry_timeout_ms), so a big report isn't competing with N others.
    """
    events = events or Events()
    n = resolve_worker_count(workers)
    # No saved session is no longer fatal: new_authed_browser falls back to
    # DEVICE SIGN-IN mode (the persistent Edge sign-in profile, signed in live
    # by Windows on managed Caltrans PCs). That profile can only be open in ONE
    # browser at a time, so device mode caps fast mode to a single worker.
    if not has_valid_auth():
        events.on_log("No saved session - will try signing in automatically "
                      "using this PC's work account (Microsoft Edge).")
        if n > 1:
            events.on_log("Automatic sign-in supports one browser at a time - "
                          "running with 1 browser. Save a login to use fast mode.")
            n = 1
    timeout_ms = timeout_ms or FAST_REPORT_TIMEOUT_MS
    retry_timeout_ms = retry_timeout_ms or RETRY_REPORT_TIMEOUT_MS

    out_dir = output_day_dir() / spec.subdir   # dated layout, like the sequential engine
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(routes)
    n = min(n, total) or 1
    log.info("parallel export start: %s (%d routes, %d workers)", spec.label, total, n)
    events.on_log(f"Fast mode (experimental): {n} browsers in parallel, {total} routes.")

    _preflight_once(spec, events)
    events.on_log("Ready. Starting export.")

    work = queue.Queue()
    for r in routes:
        work.put(r)

    stop = threading.Event()            # set on cancel, auth loss, or an unrecoverable per-route stop
    auth_failed = threading.Event()     # distinguishes auth loss -> re-raise AuthError
    worker_crashed = threading.Event()  # a worker died with an unexpected error
    worker_results = [None] * n

    def worker(idx):
        wr = RunResult(output_dir=str(out_dir))
        worker_results[idx] = wr
        wevents = _worker_events(events, stop)
        tag = f"[browser {idx + 1}]"
        try:
            with sync_playwright() as p:
                browser, _ctx, page = new_authed_browser(p)
                try:
                    navigate_with_auth(page)
                    if not is_logged_in(page):
                        raise AuthError(
                            "Sign-in didn't complete - the session may have "
                            "expired. Please log in."
                        )
                    select_report(page, spec.label)         # arm this worker's form
                    while not stop.is_set():
                        if events.is_cancelled():
                            stop.set()
                            break
                        try:
                            route = work.get_nowait()
                        except queue.Empty:
                            break                            # no work left -> done
                        prefix = f"{tag} Route {route}:"
                        out_path = out_dir / spec.filename(route)
                        if out_path.exists():
                            wevents.on_log(f"{prefix} already exists, skip")
                            wr.exists.append(route)
                            _record(wr, wevents, route, "exists")
                            continue
                        # Reuse the proven per-route loop (retry/recover/record).
                        if not _process_route(page, spec, route, prefix, out_path,
                                              wevents, wr, timeout_ms):
                            stop.set()                       # unrecoverable -> wind down
                            break
                finally:
                    browser.close()
        except AuthError:
            log.warning("%s lost the session", tag)
            auth_failed.set()
            stop.set()
        except RunCancelled:
            stop.set()                  # user cancelled mid-route: wind down, not a crash
        except Exception:
            log.exception("%s crashed", tag)
            events.on_log(f"{tag} stopped unexpectedly; the other browsers keep going "
                          "(details in the log).")
            worker_crashed.set()
            # Deliberately do NOT stop the other workers -- they keep draining the
            # queue so one dead browser doesn't abort the whole run. Any route this
            # worker had in flight is reconciled as failed after the join (below)
            # and gets the serial retry pass.

    threads = [
        threading.Thread(target=worker, args=(i,), daemon=True, name=f"export-w{i + 1}")
        for i in range(n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if auth_failed.is_set():
        # Mirror the sequential engine: surface as AuthError so the driver can
        # clear the stale file and prompt a re-login. Files already saved stay on
        # disk, so a re-run resumes where this one stopped.
        raise AuthError("The saved session expired or became invalid during the run.")

    # Merge the per-worker results into one (order interleaved; fine for the CSV).
    result = RunResult(output_dir=str(out_dir))
    for wr in worker_results:
        if not wr:
            continue
        result.saved += wr.saved
        result.empty.extend(wr.empty)
        result.user_skipped.extend(wr.user_skipped)
        result.failed.extend(wr.failed)
        result.exists.extend(wr.exists)
        result.per_route.extend(wr.per_route)

    # Reconcile: a crashed (or stopped) worker can leave routes with NO recorded
    # outcome -- the one it had in flight, plus any it never reached. Without this
    # those routes would be silently dropped from a "successful" run. Mark every
    # such route failed (unless its file is already on disk) so nothing is lost:
    # the serial retry pass below then gives them a fresh attempt, and the run
    # report + counts account for every route exactly once. Skip when the user
    # cancelled -- those routes are simply not-done (resume later), not failures.
    if not events.is_cancelled():
        accounted = {r for r, _ in result.per_route}
        missing = [r for r in routes
                   if r not in accounted and not (out_dir / spec.filename(r)).exists()]
        if missing:
            if worker_crashed.is_set():
                events.on_log(f"{len(missing)} route(s) weren't completed because a browser "
                              "stopped unexpectedly -- marking them failed to retry.")
            for r in missing:
                result.failed.append(r)
                _record(result, events, r, "failed")

    log.info("parallel export done: saved=%d empty=%d skipped=%d failed=%d",
             result.saved, len(result.empty), len(result.user_skipped), len(result.failed))

    # One serial, single-browser retry of whatever failed under concurrent load.
    # Done before the run report so the CSV reflects the final outcomes.
    if result.failed and not events.is_cancelled():
        try:
            _retry_failed_sequential(spec, events, result, out_dir, retry_timeout_ms)
        except AuthError:
            raise
        except Exception:
            log.exception("parallel retry pass failed")
            events.on_log("Retry pass stopped unexpectedly (details in the log).")

    if result.per_route:
        try:
            report_path = write_run_report(result, spec.label, auto_report_path(spec.subdir))
            result.report_path = str(report_path)
            events.on_log(f"Run report saved: {report_path}")
            log.info("run report saved: %s", report_path)
        except Exception as e:
            log.warning("could not write run report: %s", e)

    return result
