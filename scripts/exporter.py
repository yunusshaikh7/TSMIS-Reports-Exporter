"""The shared export engine.

One proven per-route loop drives every report. What differs between reports
(dropdown label, output subfolder + filename, the post-Generate wait, the
empty-result check, and how the result is saved) is captured in a ReportSpec,
so a change to one report stays contained -- while the loop, recovery, and
skip/cancel logic live in exactly one place.

The engine is console-free: it reports progress through an Events sink and
raises AuthError on session problems, so the same code backs both the console
shim (cli.py) and the future GUI.
"""
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from common import (
    ERROR_JS,
    REPORT_TIMEOUT_MS,
    RETRY_COUNT,
    RETRY_REPORT_TIMEOUT_MS,
    ROUTES,
    AuthError,
    ReportError,
    RunCancelled,
    is_logged_in,
    navigate_with_auth,
    new_authed_browser,
    preflight,
    report_error_text,
    require_valid_auth,
    select_report,
    wait_with_skip_option,
)
from events import Events, RunResult
from paths import FAILURES_DIR, OUTPUT_ROOT
from run_report import auto_report_path, write_run_report

log = logging.getLogger("tsmis.export")


@dataclass
class ReportSpec:
    """Everything that makes one TSMIS report different from another."""
    label: str                              # exact #customReport dropdown text
    subdir: str                             # output/<subdir>/
    filename: Callable[[str], str]          # route -> output file name
    wait_js: Callable[[str], str]           # route -> JS that resolves when ready OR empty
    is_empty: Callable[[object], bool]      # (page) -> True if the route has no data
    save: Callable[[object, Path, int], None]  # (page, out_path, timeout_ms) -> write the file


# --- reusable save strategies -------------------------------------------------
# All take a timeout_ms so the slower fast-mode / retry windows reach the actual
# download wait, not just the report-generation wait.

def save_pdf_letter(page, out_path, timeout_ms=None):
    """Render the current report to a Letter PDF (TSAR Ramp Summary). The page is
    already rendered, so timeout_ms is unused -- accepted for a uniform save
    signature."""
    page.pdf(
        path=str(out_path),
        format="Letter",
        print_background=True,
        margin={"top": "0.4in", "bottom": "0.4in", "left": "0.4in", "right": "0.4in"},
    )


def save_via_export_button(page, out_path, timeout_ms=None):
    """Click the report's Export button and save the resulting download
    (TSAR Ramp Detail, Highway Sequence Listing). Big reports under heavy load
    can take minutes to produce the download, so honor the caller's window."""
    with page.expect_download(timeout=timeout_ms or REPORT_TIMEOUT_MS) as dl_info:
        page.locator("button.export-btn", has_text="Export").first.click()
    dl_info.value.save_as(str(out_path))


# --- the engine ---------------------------------------------------------------

def _record(result, events, route, status):
    """Record a route's final outcome (for the run report) and notify the UI."""
    result.per_route.append((route, status))
    events.on_route(route, status)


def _recover(page, spec):
    """Re-navigate and re-arm the form after a skip or per-route error.

    Raises AuthError if the session has died so the run stops cleanly.
    """
    navigate_with_auth(page)
    if not is_logged_in(page):
        raise AuthError("Session expired partway through the batch.")
    select_report(page, spec.label)


def _recover_or_stop(page, spec, events):
    """Re-arm the form. Returns True to keep going, False to stop the whole run.
    Re-raises AuthError so the run ends cleanly."""
    try:
        _recover(page, spec)
        return True
    except AuthError:
        raise
    except Exception as e:
        events.on_log(f"Recovery failed: {e}")
        log.exception("recovery failed")
        return False


def _capture_failure(page, spec, route, events):
    """Save a screenshot + page HTML for a failed route. Best-effort: never
    raises, so a capture problem can't mask the original error."""
    try:
        FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        stem = f"{spec.subdir}_route_{route}_{time.strftime('%Y%m%d_%H%M%S')}"
        png = FAILURES_DIR / f"{stem}.png"
        page.screenshot(path=str(png), full_page=True)
        try:
            (FAILURES_DIR / f"{stem}.html").write_text(page.content(), encoding="utf-8")
        except Exception:
            pass
        log.info("failure screenshot saved: %s", png)
        events.on_log(f"  diagnostic screenshot saved ({png.name})")
    except Exception as e:
        log.warning("could not capture failure screenshot: %s", e)


def _attempt_route(page, spec, route, prefix, out_path, events, timeout_ms):
    """One attempt at a route. Returns 'saved' | 'empty' | 'skipped'.
    Raises on any failure; the caller decides whether to retry. timeout_ms is the
    hard ceiling for both the report-generation wait and the save/download."""
    page.get_by_label("Route", exact=True).select_option(route)
    page.get_by_role("button", name="Generate").click()
    # Wait for the report to be ready/empty OR for the site to render an error
    # (so a route the site can't build fails in seconds instead of waiting out
    # the whole timeout). spec.wait_js(route) is a full arrow function; invoke it
    # and OR in the shared error check.
    ready_js = spec.wait_js(route)
    wait_js = f"() => (({ready_js}))() || ({ERROR_JS})"
    if not wait_with_skip_option(page, wait_js, prefix, events,
                                 hard_timeout_ms=timeout_ms):
        return "skipped"
    if events.is_cancelled():        # cancel landed between the wait and the save
        raise RunCancelled()
    err = report_error_text(page)    # site rendered a fatal error for this route
    if err:
        raise ReportError(err)
    if spec.is_empty(page):
        return "empty"
    page.wait_for_timeout(1000)
    spec.save(page, out_path, timeout_ms)
    return "saved"


def _process_route(page, spec, route, prefix, out_path, events, result, timeout_ms):
    """Run one route, retrying once on a transient (non-timeout) error. Records
    the outcome in `result`. Returns True to keep going, False to stop the whole
    run (unrecoverable). Raises AuthError to end the run cleanly. timeout_ms is
    the per-route hard ceiling (larger in fast mode and in the retry pass)."""
    for attempt in range(1 + RETRY_COUNT):
        try:
            outcome = _attempt_route(page, spec, route, prefix, out_path, events, timeout_ms)
        except (AuthError, RunCancelled):
            raise                       # session loss / user cancel: never retry, never record as failed
        except ReportError as e:
            # The site rendered a fatal error for this route. Record it as failed
            # right away (with the site's message) instead of burning an in-loop
            # retry -- it's detected in seconds now, and the end-of-run retry pass
            # still gives it one more (also-fast) attempt in case it was transient.
            events.on_log(f"{prefix} TSMIS site error -- {e}")
            log.warning("%s site error: %s", prefix, e)
            _capture_failure(page, spec, route, events)
            result.failed.append(route)
            _record(result, events, route, "failed")
            return _recover_or_stop(page, spec, events)
        except PlaywrightTimeoutError:
            # The hard timeout already gave the user a skip window; don't burn
            # another full timeout retrying -- record it and move on.
            events.on_log(f"{prefix} timed out -- recording as failed")
            log.warning("%s timed out", prefix)
            _capture_failure(page, spec, route, events)
            result.failed.append(route)
            _record(result, events, route, "failed")
            return _recover_or_stop(page, spec, events)
        except Exception as e:
            log.exception("%s attempt %d/%d failed", prefix, attempt + 1, 1 + RETRY_COUNT)
            if attempt < RETRY_COUNT:
                events.on_log(f"{prefix} error ({type(e).__name__}) -- retrying once")
                if not _recover_or_stop(page, spec, events):
                    return False
                continue
            events.on_log(f"{prefix} FAILED ({type(e).__name__})")
            _capture_failure(page, spec, route, events)
            result.failed.append(route)
            _record(result, events, route, "failed")
            return _recover_or_stop(page, spec, events)
        else:
            if outcome == "skipped":
                result.user_skipped.append(route)
                _record(result, events, route, "skipped")
                log.info("%s skipped by user", prefix)
                return _recover_or_stop(page, spec, events)
            if outcome == "empty":
                events.on_log(f"{prefix} empty, skip")
                result.empty.append(route)
                _record(result, events, route, "empty")
                log.info("%s empty", prefix)
                return True
            result.saved += 1                      # outcome == "saved"
            events.on_log(f"{prefix} saved")
            _record(result, events, route, "saved")
            log.info("%s saved", prefix)
            return True
    return True


def _retry_failed_routes(page, spec, events, result, out_dir, timeout_ms):
    """Second-chance pass over routes that failed in the main run -- one at a
    time, with a more generous per-route timeout.

    Big reports under heavy server load (e.g. Highway Sequence in fast mode) can
    blow the normal window; this gives the stragglers a slow, serial retry once
    the rest are done. Reused by both engines (the parallel one runs it in a
    single fresh browser, so fast-mode retries are sequential too).

    Mutates `result` IN PLACE so each retried route reflects its *final* outcome:
    the first-pass "failed" record is dropped before re-running, and a route that
    now succeeds (or is finally empty) is re-recorded once -- no duplicate
    run-report rows or double-counted progress. Honors is_cancelled(); raises
    AuthError if the session dies, ending the run like the main loop.
    """
    to_retry = list(result.failed)
    if not to_retry:
        return

    events.on_log(
        f"Retrying {len(to_retry)} failed route(s) one at a time, up to "
        f"{timeout_ms // 60_000} min each: {', '.join(to_retry)}"
    )
    log.info("retry pass: %d route(s): %s", len(to_retry), to_retry)

    # Drop the first-pass 'failed' bookkeeping for these routes; _process_route
    # re-records each route's final status below. Anything left unrecorded at the
    # end (re-arm failure, cancel, unrecoverable stop) is reconciled back to
    # 'failed' so every retried route is accounted for exactly once.
    retry_set = set(to_retry)
    result.failed = [r for r in result.failed if r not in retry_set]
    result.per_route = [(r, s) for (r, s) in result.per_route if r not in retry_set]

    if _recover_or_stop(page, spec, events):       # re-arm once; may raise AuthError
        total = len(to_retry)
        for i, route in enumerate(to_retry):
            if events.is_cancelled():
                break
            prefix = f"[retry {i + 1}/{total}] Route {route}:"
            out_path = out_dir / spec.filename(route)
            if out_path.exists():
                result.exists.append(route)
                _record(result, events, route, "exists")
                continue
            try:
                if not _process_route(page, spec, route, prefix, out_path, events, result, timeout_ms):
                    break
            except RunCancelled:
                break               # leave the rest reconciled back to 'failed' below

    recorded = {r for r, _ in result.per_route}
    for route in to_retry:
        if route not in recorded:
            result.failed.append(route)
            _record(result, events, route, "failed")


def run_export(spec, events=None, *, routes=ROUTES, timeout_ms=None, retry_timeout_ms=None):
    """Export `spec` for every route. Console-free; returns a RunResult.

    Raises AuthError if the saved session is missing/expired, or PreflightError
    if the TSMIS form doesn't look as expected (the caller surfaces either).
    Honors events.should_skip() while waiting on a route and
    events.is_cancelled() between routes. Already-downloaded files are skipped,
    so re-running resumes where a previous run left off. A transient route error
    is retried once; a route that still fails is screenshotted to FAILURES_DIR
    and recorded in result.failed. After the main pass, any failed routes get one
    slow, serial retry with `retry_timeout_ms` (see _retry_failed_routes).

    timeout_ms / retry_timeout_ms override the per-route hard ceilings (defaults:
    REPORT_TIMEOUT_MS for the main pass, RETRY_REPORT_TIMEOUT_MS for the retry).
    """
    events = events or Events()
    require_valid_auth()
    timeout_ms = timeout_ms or REPORT_TIMEOUT_MS
    retry_timeout_ms = retry_timeout_ms or RETRY_REPORT_TIMEOUT_MS

    out_dir = OUTPUT_ROOT / spec.subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    result = RunResult(output_dir=str(out_dir))
    total = len(routes)
    log.info("export start: %s (%d routes)", spec.label, total)

    with sync_playwright() as p:
        browser, _ctx, page = new_authed_browser(p)
        try:
            navigate_with_auth(page)
            if not is_logged_in(page):
                raise AuthError("Saved session is expired or invalid.")

            events.on_log("Logged in. Checking the report form...")
            preflight(page, spec.label)
            events.on_log("Ready. Starting export.")

            for i, route in enumerate(routes, 1):
                if events.is_cancelled():
                    events.on_log("Cancelled by user.")
                    log.info("cancelled by user at route %s", route)
                    break

                prefix = f"[{i:>3}/{total}] Route {route}:"
                out_path = out_dir / spec.filename(route)

                if out_path.exists():
                    events.on_log(f"{prefix} already exists, skip")
                    result.exists.append(route)
                    _record(result, events, route, "exists")
                    continue

                try:
                    if not _process_route(page, spec, route, prefix, out_path, events, result, timeout_ms):
                        break
                except RunCancelled:
                    events.on_log("Cancelled by user.")
                    log.info("cancelled by user during route %s", route)
                    break

            # Give routes that failed the main pass one slow, serial retry.
            if not events.is_cancelled():
                try:
                    _retry_failed_routes(page, spec, events, result, out_dir, retry_timeout_ms)
                except AuthError:
                    raise
                except Exception:
                    log.exception("retry pass failed")
                    events.on_log("Retry pass stopped unexpectedly (details in the log).")
        finally:
            browser.close()

    log.info("export done: saved=%d empty=%d skipped=%d failed=%d",
             result.saved, len(result.empty), len(result.user_skipped), len(result.failed))

    # Auto-save the per-route run report so the data point is never lost. The
    # GUI can also save a copy elsewhere; a write failure here is non-fatal.
    if result.per_route:
        try:
            report_path = write_run_report(result, spec.label, auto_report_path(spec.subdir))
            result.report_path = str(report_path)
            events.on_log(f"Run report saved: {report_path}")
            log.info("run report saved: %s", report_path)
        except Exception as e:
            log.warning("could not write run report: %s", e)

    return result
