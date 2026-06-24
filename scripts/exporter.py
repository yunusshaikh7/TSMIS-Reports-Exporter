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
    RETRY_COUNT,
    ROUTES,
    AuthError,
    ReportError,
    RunCancelled,
    current_report_label,
    download_start_timeout_ms,
    get_site,
    get_url,
    has_valid_auth,
    maybe_screenshot,
    navigate_with_auth,
    new_authed_browser,
    preflight,
    report_error_text,
    report_timeout_ms,
    require_signed_in,
    require_site_params,
    retry_report_timeout_ms,
    select_report,
    wait_with_skip_option,
)
from events import Events, RunResult
from paths import FAILURES_DIR, output_run_dir
from run_report import auto_report_path, write_run_report

log = logging.getLogger("tsmis.export")


class EmptyExport(Exception):
    """Raised by a save strategy when the report rendered but produced NO
    download -- the site's Export is a no-op for a route with no exportable rows
    (e.g. an empty Intersection Detail: the button is present but
    intd_exportToExcel early-returns). The engine records the route as `empty`
    rather than waiting out the full per-route ceiling (and then the 15-min
    retry) on a download that will never start. This is the general,
    marker-independent guard against the ~21-min "empty route hangs" class --
    it fires no matter how a report's empty-state text/DOM drifts."""


@dataclass
class ReportSpec:
    """Everything that makes one TSMIS report different from another."""
    label: str                              # exact #customReport dropdown text
    subdir: str                             # output/<subdir>/
    filename: Callable[[str], str]          # route -> output file name
    wait_js: Callable[[str], str]           # route -> JS that resolves when ready OR empty
    is_empty: Callable[[object], bool]      # (page) -> True if the route has no data
    save: Callable[[object, Path, int], None]  # (page, out_path, timeout_ms) -> write the file


# --- saved-file integrity -----------------------------------------------------
# A download interrupted partway, or a save onto a full / locked disk, can leave
# a 0-byte or truncated file. Resume trusts "the file exists" to skip a route, so
# without a content check a partial file would be masked as a finished export
# forever. These verify the file is actually a complete workbook/PDF by its magic
# bytes (cheap, no third-party deps): an .xlsx is a ZIP container (PK\x03\x04),
# a .pdf starts with %PDF. Unknown extensions only need to be non-empty.

def _head_is_complete(suffix, head, size):
    """Does a file's first bytes look like a complete report of `suffix`?
    .xlsx is a ZIP (PK\\x03\\x04), .pdf starts with %PDF; unknown types only need
    to be non-empty. The magic checks inherently reject anything too short."""
    suffix = suffix.lower()
    if suffix == ".xlsx":
        return head == b"PK\x03\x04"
    if suffix == ".pdf":
        return head == b"%PDF"
    return size > 0


def _file_looks_complete(path):
    """True if `path` looks like a fully-written report file (not 0-byte or
    truncated). Used to verify a FRESH save (where the file is readable because
    we just wrote it) -- a read failure here is a real problem, so it returns
    False. Resume uses _can_resume, which is lock-tolerant instead."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            head = f.read(4)
    except OSError:
        return False
    return _head_is_complete(path.suffix, head, size)


def _verify_saved_file(out_path):
    """Confirm a just-written file is complete; on failure delete the partial
    file (so a later resume re-pulls it) and raise so the route records failed.
    A truncated/empty download is a real failure, not an empty route."""
    if _file_looks_complete(out_path):
        return
    try:
        size = out_path.stat().st_size
    except OSError:
        size = -1
    log.warning("saved file failed integrity check: %s (%d bytes)", out_path, size)
    try:
        out_path.unlink()
    except OSError:
        pass
    raise RuntimeError(
        "The downloaded file looked incomplete (it may have been interrupted) — "
        "it was discarded so the route can be tried again."
    )


def _can_resume(out_path):
    """True if `out_path` is an existing file resume may trust to skip the route.

    Only a file we can READ and that is definitively truncated/0-byte is deleted
    and re-pulled (so a partial download from an interrupted run isn't masked as
    finished). A file that EXISTS but can't be read is almost always a finished
    export the user has open in Excel (a sharing-deny lock) -- it is trusted and
    skipped, never deleted, so resume can't turn a done route into a spurious
    failure by trying to re-download over a locked file. Used by both engines."""
    if not out_path.exists():
        return False
    try:
        size = out_path.stat().st_size
        with open(out_path, "rb") as f:
            head = f.read(4)
    except OSError:
        log.info("resume: existing file is locked/unreadable; trusting it: %s",
                 out_path)
        return True
    if _head_is_complete(out_path.suffix, head, size):
        return True
    log.warning("resume: existing file is incomplete; re-pulling: %s", out_path)
    try:
        out_path.unlink()
    except OSError:
        pass
    return False


# --- reusable save strategies -------------------------------------------------
# All take a timeout_ms so the slower fast-mode / retry windows reach the actual
# download wait, not just the report-generation wait.

def save_pdf_letter(page, out_path, timeout_ms=None):
    """Render the current report to a Letter PDF (TSAR Ramp Summary). The page is
    already rendered, so timeout_ms is unused -- accepted for a uniform save
    signature."""
    # Marker-INDEPENDENT empty backstop: the inline report renders its action bar
    # only when it has data (the empty path renders just a short placeholder span).
    # If no action bar is present, treat the route as empty -- recorded `empty`
    # (retried once), never saved as a contentless PDF -- so a drifted empty-text
    # marker can't slip a blank page through unlogged. (is_empty runs first in
    # _attempt_route; this is the second-opinion net for when that marker drifts.)
    if not page.evaluate(
            "() => { const b = document.getElementById('rampResults'); "
            "return !!(b && b.querySelector('.report-action-bar')); }"):
        log.info("ramp PDF: no report action bar rendered for %s; treating as empty",
                 out_path.name)
        raise EmptyExport()
    page.pdf(
        path=str(out_path),
        format="Letter",
        print_background=True,
        margin={"top": "0.4in", "bottom": "0.4in", "left": "0.4in", "right": "0.4in"},
    )
    _verify_saved_file(out_path)


def save_via_export_button(page, out_path, timeout_ms=None):
    """Click the report's Export button and save the resulting download
    (TSAR Ramp Detail, Highway Sequence Listing, Highway Log, Intersection
    reports).

    The report has already rendered by the time this runs (the post-Generate
    wait resolved on the Export button), and the site builds the workbook
    client-side, so a non-empty report's download starts within a second. Bound
    the wait at download_start_timeout_ms() -- never more than the caller's
    overall ceiling -- so a rendered route whose Export produces no download (the
    site's no-op for "nothing to export") is recognised as EMPTY in seconds
    instead of hanging out the full per-route timeout (and the 15-min retry).
    """
    ceiling = timeout_ms or report_timeout_ms()
    download_ms = min(download_start_timeout_ms(), ceiling)
    try:
        with page.expect_download(timeout=download_ms) as dl_info:
            page.locator("button.export-btn", has_text="Export").first.click()
    except PlaywrightTimeoutError:
        # No download started in the window. Distinguish a site error (record it
        # so the route fails with the site's message) from "nothing to export"
        # (the rendered-but-empty no-op -> record the route empty).
        err = report_error_text(page)
        if err:
            raise ReportError(err)
        log.warning("Export produced no download within %ds for %s; treating as "
                    "empty (the site's 'nothing to export' no-op)",
                    download_ms // 1000, out_path.name)
        raise EmptyExport()
    dl_info.value.save_as(str(out_path))
    _verify_saved_file(out_path)


def save_highway_log_pdf(page, out_path, timeout_ms=None):
    """Render the FULL Highway Log to a Landscape PDF, the way the site's Print
    button lays it out.

    The on-screen Highway Log is PAGINATED (one page of rows at a time --
    `hl_renderPage`), so unlike the inline Ramp Summary we can't just `page.pdf()`
    what's shown -- it would capture a single page. The site's global
    `hl_printAll()` builds EVERY page (a cover page + all rows, with page breaks)
    into #rampResults, then calls `window.print()` and SYNCHRONOUSLY restores the
    on-screen view. We override `window.print` to raise FIRST, so that restore
    line never runs and the complete print layout stays in the DOM for
    `page.pdf()` -- which emulates print media, and the site's `@media print`
    hides every control and shows only #rampResults. 30 columns -> Landscape.

    The report has already rendered (is_empty ran first, so this is never an empty
    route), and the layout is built client-side, so timeout_ms is unused (kept for
    the uniform save signature). Fails loudly with ReportError if the site's Print
    function is gone/renamed, rather than silently saving the one paginated page."""
    built = page.evaluate(
        """() => {
            if (typeof hl_printAll !== 'function') return {status: 'no-print-fn', rows: 0};
            window.print = () => { throw new Error('skip-print'); };
            try { hl_printAll(); } catch (e) { /* the throw skips hl_printAll's restore */ }
            const box = document.getElementById('rampResults');
            if (!box || !box.querySelector('.hl-print-section'))
                return {status: 'no-layout', rows: 0};
            // Marker-INDEPENDENT data-row count: a real row carries per-column <td>s,
            // while the "No results" placeholder is a single spanning (colspan) cell.
            // Counting the non-spanning rows lets the empty backstop fire even if the
            // empty-text wording drifts.
            let rows = 0;
            for (const tr of box.querySelectorAll('.hl-print-section table tbody tr')) {
                const tds = tr.querySelectorAll('td');
                if (!tds.length) continue;
                if ([...tds].some(td => td.hasAttribute('colspan'))) continue;
                rows++;
            }
            return {status: 'ok', rows: rows};
        }""")
    status = built.get("status") if isinstance(built, dict) else built
    if status != "ok":
        raise ReportError(
            "Couldn't build the Highway Log print layout for the PDF "
            f"(the site's Print control changed: {status}).")
    if not (built.get("rows") if isinstance(built, dict) else 0):
        # The layout built but holds no data rows (only the spanning empty notice).
        # Marker-INDEPENDENT empty backstop: record the route `empty` (retried once)
        # instead of saving a contentless PDF, even if the empty-text marker drifted.
        log.info("highway_log PDF: print layout has no data rows for %s; treating "
                 "as empty", out_path.name)
        raise EmptyExport()
    page.pdf(
        path=str(out_path),
        format="Letter",
        landscape=True,
        print_background=True,
        margin={"top": "0.4in", "bottom": "0.4in", "left": "0.4in", "right": "0.4in"},
    )
    _verify_saved_file(out_path)


# --- the engine ---------------------------------------------------------------

def _record(result, events, route, status):
    """Record a route's final outcome (for the run report) and notify the UI."""
    result.per_route.append((route, status))
    events.on_route(route, status)


def _brief(e, limit=200):
    """First line of an exception's message, truncated -- specific enough to
    act on in a status line, with the full traceback in the log."""
    text = str(e).splitlines()[0] if str(e) else ""
    text = f"{type(e).__name__}: {text}" if text else type(e).__name__
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _fmt_size(n_bytes):
    if n_bytes >= 1_000_000:
        return f"{n_bytes / 1_000_000:.1f} MB"
    return f"{n_bytes / 1_000:.0f} KB"


def _recover(page, spec, should_cancel=None):
    """Re-navigate and re-arm the form after a skip or per-route error.

    Raises AuthError if the session has died so the run stops cleanly. `should_cancel`
    is threaded into the sign-in re-navigation so a Stop during recovery aborts within
    ~1s instead of waiting out the whole sign-in budget.
    """
    navigate_with_auth(page, should_cancel=should_cancel)
    require_signed_in(page, "Session expired partway through the batch.")
    select_report(page, spec.label)


def _recover_or_stop(page, spec, events):
    """Re-arm the form. Returns True to keep going, False to stop the whole run.
    Re-raises AuthError so the run ends cleanly."""
    try:
        events.on_status(events.worker_no, "Recovering (reloading the report page)…")
        _recover(page, spec, should_cancel=events.is_cancelled)
        return True
    except AuthError:
        raise
    except Exception as e:
        events.on_log(f"Recovery failed: {e}")
        log.exception("recovery failed")
        return False


def _capture_failure(page, spec, route, events):
    """Save a screenshot + page HTML for a failed route. Best-effort: never
    raises, so a capture problem can't mask the original error.

    The screenshot is the VIEWPORT, not the full page: a failed route may have a
    fully-rendered report behind it, and these diagnostics persist on disk under
    FAILURES_DIR (a folder the user can open). The failure state worth capturing
    -- the error box, the button state -- is above the fold, so the viewport
    keeps the diagnostic value while not writing the whole report image to disk.
    (FAILURES_DIR is deliberately NEVER added to the shareable support bundle.)"""
    try:
        FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        stem = f"{spec.subdir}_route_{route}_{time.strftime('%Y%m%d_%H%M%S')}"
        png = FAILURES_DIR / f"{stem}.png"
        page.screenshot(path=str(png), full_page=False)
        try:
            (FAILURES_DIR / f"{stem}.html").write_text(page.content(), encoding="utf-8")
        except Exception:
            pass
        log.info("failure screenshot saved: %s", png)
        events.on_log(f"  diagnostic screenshot saved ({png.name})")
    except Exception as e:
        log.warning("could not capture failure screenshot: %s", e)


def _ensure_report_armed(page, spec, prefix, events):
    """Re-confirm the report dropdown still shows spec.label before a route.

    The report is selected once at preflight and only re-armed by _recover after a
    skip/error; if the site silently reset the dropdown between routes (a stale
    form), the per-route Route selection + Generate would run against the WRONG
    report. This cheap guard re-selects when the shown label has drifted. It
    no-ops on the happy path (the label already matches) and never acts on an
    unreadable selection (current_report_label returns '' = unknown)."""
    shown = current_report_label(page)
    if shown and shown != spec.label:
        log.warning("%s report form shows %r, expected %r -- re-selecting",
                    prefix, shown, spec.label)
        events.on_log(f"{prefix} report form drifted; re-selecting {spec.label}")
        select_report(page, spec.label)


def _attempt_route(page, spec, route, prefix, out_path, events, timeout_ms):
    """One attempt at a route. Returns 'saved' | 'empty' | 'skipped'.
    Raises on any failure; the caller decides whether to retry. timeout_ms is the
    hard ceiling for both the report-generation wait and the save/download."""
    events.on_status(events.worker_no, f"{prefix} generating…")
    _ensure_report_armed(page, spec, prefix, events)   # P8c: stale-form re-arm guard
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
    # One last look before the save grabs the page (a download wait can't
    # answer preview requests until it returns).
    maybe_screenshot(page, events, note=prefix.strip())
    events.on_status(events.worker_no, f"{prefix} saving…")
    # A save that finds no download (and no site error) raises EmptyExport, which
    # PROPAGATES to _process_route rather than being collapsed to "empty" here.
    # The is_empty check above is the POSITIVE (marker-matched) empty; the
    # no-download case is INCONCLUSIVE — a transient export-click flake looks
    # identical to a real no-op — so _process_route retries it once and records
    # "empty" only if it reproduces.
    spec.save(page, out_path, timeout_ms)
    return "saved"


def _process_route(page, spec, route, prefix, out_path, events, result, timeout_ms):
    """Run one route, retrying once on a transient (non-timeout) error. Records
    the outcome in `result`. Returns True to keep going, False to stop the whole
    run (unrecoverable). Raises AuthError to end the run cleanly. timeout_ms is
    the per-route hard ceiling (larger in fast mode and in the retry pass)."""
    t0 = time.monotonic()

    def took():
        return int(time.monotonic() - t0)

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
            log.warning("%s site error after %ds: %s", prefix, took(), e)
            _capture_failure(page, spec, route, events)
            result.failed.append(route)
            _record(result, events, route, "failed")
            return _recover_or_stop(page, spec, events)
        except PlaywrightTimeoutError:
            # The hard timeout already gave the user a skip window; don't burn
            # another full timeout retrying -- record it and move on.
            events.on_log(f"{prefix} timed out after {took()}s "
                          f"(limit {timeout_ms // 1000}s) -- recording as failed")
            log.warning("%s timed out after %ds (limit %ds)",
                        prefix, took(), timeout_ms // 1000)
            _capture_failure(page, spec, route, events)
            result.failed.append(route)
            _record(result, events, route, "failed")
            return _recover_or_stop(page, spec, events)
        except EmptyExport:
            # No download AND no site error in the export-click window. This is
            # the marker-independent empty net -- but a transient flake in that
            # short window is INDISTINGUISHABLE from a real empty, so don't trust
            # it on the FIRST attempt: retry once in-loop and record `empty` only
            # if it reproduces. (A positive is_empty match short-circuits to
            # "empty" in _attempt_route and never reaches here.) This stops a
            # populated route whose Export click flaked from being reported as
            # benign "No data" and never retried.
            if attempt < RETRY_COUNT:
                events.on_log(f"{prefix} no data on first try -- retrying once "
                              "to rule out a transient export hiccup")
                log.info("%s no-download empty on attempt %d/%d; retrying",
                         prefix, attempt + 1, 1 + RETRY_COUNT)
                if not _recover_or_stop(page, spec, events):
                    return False
                continue
            events.on_log(f"{prefix} empty, skip")
            result.empty.append(route)
            _record(result, events, route, "empty")
            log.info("%s empty after retry (%ds)", prefix, took())
            return True
        except Exception as e:
            log.exception("%s attempt %d/%d failed after %ds",
                          prefix, attempt + 1, 1 + RETRY_COUNT, took())
            if attempt < RETRY_COUNT:
                events.on_log(f"{prefix} error -- {_brief(e)} -- retrying once")
                if not _recover_or_stop(page, spec, events):
                    return False
                continue
            events.on_log(f"{prefix} FAILED -- {_brief(e)}")
            _capture_failure(page, spec, route, events)
            result.failed.append(route)
            _record(result, events, route, "failed")
            return _recover_or_stop(page, spec, events)
        else:
            if outcome == "skipped":
                result.user_skipped.append(route)
                _record(result, events, route, "skipped")
                log.info("%s skipped by user after %ds", prefix, took())
                return _recover_or_stop(page, spec, events)
            if outcome == "empty":
                events.on_log(f"{prefix} empty, skip")
                result.empty.append(route)
                _record(result, events, route, "empty")
                log.info("%s empty (%ds)", prefix, took())
                return True
            result.saved += 1                      # outcome == "saved"
            try:
                size = f", {_fmt_size(out_path.stat().st_size)}"
            except OSError:
                size = ""
            events.on_log(f"{prefix} saved ({took()}s{size})")
            _record(result, events, route, "saved")
            log.info("%s saved (%ds%s)", prefix, took(), size)
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
            _wait_while_paused(events)            # B1: hold between routes
            if events.is_cancelled():
                break
            prefix = f"[retry {i + 1}/{total}] Route {route}:"
            out_path = out_dir / spec.filename(route)
            if _can_resume(out_path):
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
    log.info("retry pass done: still failed=%s", result.failed or "none")


_PAUSE_POLL_S = 0.2          # between-route pause poll cadence (B1)


def _wait_while_paused(events):
    """Hold here while the run is paused, returning the moment it resumes OR is
    cancelled (so a cancel during a pause still stops cleanly). Pause is honored
    only BETWEEN routes — never inside a Playwright wait (thread-affine) — so the
    browser sits idle holding no download in flight. Works in fast mode too: the
    shared is_paused() makes every worker park at this point between its routes."""
    while events.is_paused() and not events.is_cancelled():
        time.sleep(_PAUSE_POLL_S)


def run_export(spec, events=None, *, routes=ROUTES, timeout_ms=None, retry_timeout_ms=None,
               out_dir=None):
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
    # No saved session is no longer fatal: new_authed_browser falls back to
    # DEVICE SIGN-IN mode (it reopens the persistent Edge sign-in profile,
    # where the one-click Windows sign-in lives, and the Azure AD click signs
    # it in live on managed Caltrans PCs). If that can't sign in either, it
    # raises AuthError.
    if not has_valid_auth():
        events.on_log("No saved session - will try signing in automatically "
                      "using this PC's work account (Microsoft Edge).")
    timeout_ms = timeout_ms or report_timeout_ms()
    retry_timeout_ms = retry_timeout_ms or retry_report_timeout_ms()

    # Exports are grouped into run folders (output/<YYYY-MM-DD src-env>/
    # <report>/), so a new day starts fresh instead of resuming over
    # yesterday's files AND different source/environment runs never mix —
    # the folder name says exactly which site the files came from.
    src, env = get_site()
    # out_dir override (B3 "always-current" destination): write straight into the
    # caller's folder instead of the dated run folder. Default = the dated layout.
    out_dir = Path(out_dir) if out_dir else output_run_dir(src, env) / spec.subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    result = RunResult(output_dir=str(out_dir))
    total = len(routes)
    run_t0 = time.monotonic()
    # The full run context in one block, so any uploaded log answers "what ran,
    # against what, with which settings" without asking.
    log.info("export start: %s (%d routes) -> %s", spec.label, total, out_dir)
    log.info("export config: site=%s auth_file=%s timeout=%ds retry_timeout=%ds",
             get_url(), has_valid_auth(), timeout_ms // 1000, retry_timeout_ms // 1000)
    if total != len(ROUTES):
        log.info("export routes (subset): %s", ", ".join(routes))

    events.on_status(events.worker_no, "Starting browser…")
    with sync_playwright() as p:
        browser, _ctx, page = new_authed_browser(p)
        try:
            events.on_status(events.worker_no, "Opening TSMIS + signing in…")
            # Poll the cancel signal during the sign-in wait so a Stop / "Stop all"
            # aborts within ~1s instead of waiting out the full budget — and bail
            # cleanly (no AuthError modal) when the user cancelled mid-sign-in.
            navigate_with_auth(page, should_cancel=events.is_cancelled)
            if events.is_cancelled():
                events.on_log("Cancelled by user.")
                log.info("cancelled by user during sign-in")
                return result
            require_signed_in(
                page,
                "Sign-in didn't complete - the saved session may be expired, "
                "or automatic sign-in isn't available on this PC. Please log in.",
            )
            # Env backstop: navigate_with_auth accepts the page after one
            # corrective reload WITHOUT re-confirming env/src, so verify here that
            # the app is on the SELECTED data source / environment before writing
            # anything into a folder labeled with it (raises PreflightError if not).
            require_site_params(page)

            events.on_log("Logged in. Checking the report form...")
            events.on_status(events.worker_no, "Checking the report form…")
            preflight(page, spec.label)
            events.on_log("Ready. Starting export.")

            for i, route in enumerate(routes, 1):
                _wait_while_paused(events)        # B1: hold between routes
                if events.is_cancelled():
                    events.on_log("Cancelled by user.")
                    log.info("cancelled by user at route %s", route)
                    break

                prefix = f"[{i:>3}/{total}] Route {route}:"
                out_path = out_dir / spec.filename(route)
                # Between-route poll point so a Preview click during a long
                # stretch of already-exists skips still gets answered.
                maybe_screenshot(page, events, note=f"Route {route}")

                if _can_resume(out_path):
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

            events.on_status(events.worker_no, "Finishing up…")
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

    log.info("export done in %ds: saved=%d empty=%d skipped=%d failed=%d exists=%d%s",
             int(time.monotonic() - run_t0), result.saved, len(result.empty),
             len(result.user_skipped), len(result.failed), len(result.exists),
             f" failed_routes={result.failed}" if result.failed else "")

    # Auto-save the per-route run report so the data point is never lost. The
    # GUI can also save a copy elsewhere; a write failure here is non-fatal.
    if result.per_route:
        try:
            report_path = write_run_report(
                result, spec.label, auto_report_path(spec.subdir, f"{src}-{env}"))
            result.report_path = str(report_path)
            events.on_log(f"Run report saved: {report_path}")
            log.info("run report saved: %s", report_path)
        except Exception as e:
            log.warning("could not write run report: %s", e)

    return result
