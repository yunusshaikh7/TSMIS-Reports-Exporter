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
    REPORT_TIMEOUT_MS,
    RETRY_COUNT,
    ROUTES,
    AuthError,
    is_logged_in,
    navigate_with_auth,
    new_authed_browser,
    preflight,
    require_valid_auth,
    select_report,
    wait_with_skip_option,
)
from events import Events, RunResult
from paths import FAILURES_DIR, OUTPUT_ROOT

log = logging.getLogger("tsmis.export")


@dataclass
class ReportSpec:
    """Everything that makes one TSMIS report different from another."""
    label: str                              # exact #customReport dropdown text
    subdir: str                             # output/<subdir>/
    filename: Callable[[str], str]          # route -> output file name
    wait_js: Callable[[str], str]           # route -> JS that resolves when ready OR empty
    is_empty: Callable[[object], bool]      # (page) -> True if the route has no data
    save: Callable[[object, Path], None]    # (page, out_path) -> write the file


# --- reusable save strategies -------------------------------------------------

def save_pdf_letter(page, out_path):
    """Render the current report to a Letter PDF (TSAR Ramp Summary)."""
    page.pdf(
        path=str(out_path),
        format="Letter",
        print_background=True,
        margin={"top": "0.4in", "bottom": "0.4in", "left": "0.4in", "right": "0.4in"},
    )


def save_via_export_button(page, out_path):
    """Click the report's Export button and save the resulting download
    (TSAR Ramp Detail, Highway Sequence Listing)."""
    with page.expect_download(timeout=REPORT_TIMEOUT_MS) as dl_info:
        page.locator("button.export-btn", has_text="Export").first.click()
    dl_info.value.save_as(str(out_path))


# --- the engine ---------------------------------------------------------------

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


def _attempt_route(page, spec, route, prefix, out_path, events):
    """One attempt at a route. Returns 'saved' | 'empty' | 'skipped'.
    Raises on any failure; the caller decides whether to retry."""
    page.get_by_label("Route", exact=True).select_option(route)
    page.get_by_role("button", name="Generate").click()
    if not wait_with_skip_option(page, spec.wait_js(route), prefix, events):
        return "skipped"
    if spec.is_empty(page):
        return "empty"
    page.wait_for_timeout(1000)
    spec.save(page, out_path)
    return "saved"


def _process_route(page, spec, route, prefix, out_path, events, result):
    """Run one route, retrying once on a transient (non-timeout) error. Records
    the outcome in `result`. Returns True to keep going, False to stop the whole
    run (unrecoverable). Raises AuthError to end the run cleanly."""
    for attempt in range(1 + RETRY_COUNT):
        try:
            outcome = _attempt_route(page, spec, route, prefix, out_path, events)
        except AuthError:
            raise
        except PlaywrightTimeoutError:
            # The hard timeout already gave the user a skip window; don't burn
            # another full timeout retrying -- record it and move on.
            events.on_log(f"{prefix} timed out -- recording as failed")
            log.warning("%s timed out", prefix)
            _capture_failure(page, spec, route, events)
            result.failed.append(route)
            events.on_route(route, "failed")
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
            events.on_route(route, "failed")
            return _recover_or_stop(page, spec, events)
        else:
            if outcome == "skipped":
                result.user_skipped.append(route)
                events.on_route(route, "skipped")
                log.info("%s skipped by user", prefix)
                return _recover_or_stop(page, spec, events)
            if outcome == "empty":
                events.on_log(f"{prefix} empty, skip")
                result.empty.append(route)
                events.on_route(route, "empty")
                log.info("%s empty", prefix)
                return True
            result.saved += 1                      # outcome == "saved"
            events.on_log(f"{prefix} saved")
            events.on_route(route, "saved")
            log.info("%s saved", prefix)
            return True
    return True


def run_export(spec, events=None, *, routes=ROUTES):
    """Export `spec` for every route. Console-free; returns a RunResult.

    Raises AuthError if the saved session is missing/expired, or PreflightError
    if the TSMIS form doesn't look as expected (the caller surfaces either).
    Honors events.should_skip() while waiting on a route and
    events.is_cancelled() between routes. Already-downloaded files are skipped,
    so re-running resumes where a previous run left off. A transient route error
    is retried once; a route that still fails is screenshotted to FAILURES_DIR
    and recorded in result.failed.
    """
    events = events or Events()
    require_valid_auth()

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
                    events.on_route(route, "exists")
                    continue

                if not _process_route(page, spec, route, prefix, out_path, events, result):
                    break
        finally:
            browser.close()

    log.info("export done: saved=%d empty=%d skipped=%d failed=%d",
             result.saved, len(result.empty), len(result.user_skipped), len(result.failed))
    return result
