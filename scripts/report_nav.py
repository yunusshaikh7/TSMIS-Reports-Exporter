"""Report-form interaction: select / preflight / wait / error read (P8b — L2',
sits above auth_nav).

Extracted verbatim from common.py: picking the report type, the data-round-trip
preflight, the post-Generate wait with the soft skip window, and reading the
site's own fatal-error text. Depends on auth_nav only for `dump_auth_failure`
(the preflight diagnostic) — a single one-way edge, so the layering stays
acyclic. common.py re-exports the public names.

Console-free; the `"tsmis.auth"` logger name is preserved.
"""
import logging
import time

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    PlaywrightTimeoutError = Exception  # only hit if Playwright isn't installed yet

from errors import PreflightError, ReportUnavailableError, RunCancelled
from timeouts import SKIP_PROMPT_AFTER_MS, county_enable_timeout_ms, report_timeout_ms
from auth_nav import dump_auth_failure, page_url_for_display

log = logging.getLogger("tsmis.auth")


def select_report(page, report_label):
    """Pick a report from the #customReport dropdown then fan out
    District/County/Route to -- ALL --.

    report_label is the exact dropdown text, e.g. "TSAR: Ramp Summary".

    Raises ReportUnavailableError if the site has greyed the report out
    (`cs-disabled`): TSMIS can temporarily disable a report from exporting, and
    its disabled `<li>` has no `pointer-events:none`, so a Playwright click would
    silently no-op and the run would stall ~30 s into a generic preflight error.
    Detecting it here turns that into one clear "currently unavailable" message.
    """
    page.locator("#customReport").click()
    option = page.locator("#customReport li.cs-option", has_text=report_label).first
    # The site greys a temporarily-disabled report with the cs-disabled class.
    try:
        classes = (option.get_attribute("class") or "").split()
    except Exception as e:                       # never let the probe itself stop a run
        log.info("select_report: could not read option classes (%s); proceeding",
                 type(e).__name__)
        classes = []
    if "cs-disabled" in classes:
        log.warning("select_report: report %r is cs-disabled on the site", report_label)
        raise ReportUnavailableError(
            f"\"{report_label}\" is currently unavailable on the TSMIS site "
            "(the report is temporarily turned off there). Try another report, "
            "or try this one again later."
        )
    option.click()
    page.get_by_role("button", name="District / County / Route").click()
    page.get_by_label("District").select_option(label="-- ALL --")
    page.wait_for_function(
        "() => !document.querySelector('#districtCountySelect').disabled",
        timeout=county_enable_timeout_ms(),
    )
    page.locator("#districtCountySelect").select_option(label="-- ALL --")


# Every report renders a fatal error into the shared #rampResults box by adding
# the `error` class (e.g. highway_log/hsl: `box.className = 'ramp-results error'`;
# ramp detail/summary via the shared showRampResults('error', ...)). clearResults()
# resets that class on each Generate, so this only ever reflects the CURRENT
# route -- no stale-error false positives. JS expression form for use inside the
# post-Generate wait condition.
ERROR_JS = "document.querySelector('#rampResults.error') !== null"


# Readiness signal for the Excel reports: the report's *Export* button has
# rendered. The site's action bar (shared.js renderActionBar) gives BOTH the
# Export and the Print buttons class `export-btn`, so a bare
# `querySelector('button.export-btn')` matches a Print button too. Keying the
# post-Generate wait on the Export button's TEXT (case-insensitive, matching how
# the save locator filters `has_text="Export"`) keeps the readiness signal
# precise -- no report ships a Print-only bar today, but the exact match costs
# nothing and documents the contract. JS expression form, for use inside a
# report's wait_js arrow function.
EXPORT_READY_JS = (
    "[...document.querySelectorAll('button.export-btn')]"
    ".some(b => /export/i.test(b.textContent || ''))"
)


def report_error_text(page):
    """If the report rendered an error (the site's #rampResults is in its `error`
    state), return the site's message; otherwise None.

    The site shows fatal report errors here with NO Export button and NO "no
    results" text, so without detecting this the export loop would wait out the
    full per-route timeout (then the long retry) on a route the site can't build.
    Best-effort: any lookup problem returns None (treat as "no error seen")."""
    try:
        loc = page.locator("#rampResults.error")
        if loc.count() > 0:
            text = (loc.first.inner_text() or "").strip()
            return text or "The TSMIS site reported an error for this route."
    except Exception as e:
        # Best-effort, but NEVER silent: this swallow is the sole gate that turns
        # a site-rendered error into a `failed` route. If it returns None on an
        # actually-errored page, the route is downgraded to benign "No data" and
        # never retried — so log it (the "one uploaded log answers it" contract).
        log.warning("report_error_text: error-state probe failed (%s: %s); "
                    "treating as 'no error seen'", type(e).__name__,
                    (str(e).splitlines()[0] if str(e) else ""))
        return None
    return None


def preflight(page, report_label):
    """Confirm the report form looks as expected before a long run.

    Selects the report, then verifies the Route control and Generate button are
    present. Raises PreflightError (UI-neutral message) if anything is missing,
    so a TSMIS change fails fast with one clear error instead of every route
    failing cryptically.
    """
    if page.locator("#customReport").count() == 0:
        log.warning("preflight: #customReport (the report dropdown) is missing")
        dump_auth_failure(page, "preflight: report dropdown missing",
                          stem="preflight_fail")
        raise PreflightError(
            "The TSMIS report list didn't load as expected — the page may have "
            "changed. Please contact the maintainer."
        )
    step = "selecting the report"
    try:
        select_report(page, report_label)
        step = "finding the Route control"
        page.get_by_label("Route", exact=True).wait_for(state="attached", timeout=15000)
        step = "finding the Generate button"
        page.get_by_role("button", name="Generate").wait_for(state="attached", timeout=15000)
        log.info("preflight ok: %s", report_label)
    except ReportUnavailableError:
        # A greyed-out report is a clear, specific condition (select_report
        # already logged + crafted the message) -- surface it as-is, not as the
        # generic "page looks different".
        raise
    except Exception as e:
        log.warning("preflight failed while %s for %r: %s: %s",
                    step, report_label, type(e).__name__,
                    str(e).splitlines()[0] if str(e) else "")
        dump_auth_failure(page, f"preflight: {step} failed",
                          stem="preflight_fail")
        raise PreflightError(
            "The TSMIS page looks different than expected — it may have changed. "
            "Please contact the maintainer."
        ) from e


def maybe_screenshot(page, events, note=""):
    """Answer a pending live-preview request for this worker's browser.

    The GUI's Preview button sets a flag (events.screenshot_wanted); engines
    call this at safe poll points ON THE WORKER'S OWN THREAD (Playwright is
    thread-affine, so the GUI can never screenshot a page directly). Captures
    the current viewport as JPEG bytes and hands them to events.on_screenshot
    along with the page's address. Best-effort: a capture problem reports a
    None image with the reason in `note` (so the GUI stops waiting) and never
    disturbs the run."""
    try:
        if not events.screenshot_wanted(events.worker_no):
            return
    except Exception:
        return
    url = page_url_for_display(page)
    try:
        data = page.screenshot(type="jpeg", quality=70)   # viewport, not full page
        log.info("preview screenshot captured for browser %d (%d bytes, %s)",
                 events.worker_no, len(data), url or "url unknown")
        events.on_screenshot(events.worker_no, data, note, url)
    except Exception as e:
        reason = str(e).splitlines()[0] if str(e) else type(e).__name__
        log.info("preview screenshot failed for browser %d (%s: %s)",
                 events.worker_no, type(e).__name__, reason)
        try:
            events.on_screenshot(events.worker_no, None,
                                 "The screenshot couldn't be taken right now "
                                 "(the browser was busy) — try again.", url)
        except Exception:
            pass


def wait_with_skip_option(page, js_condition, prefix, events,
                          hard_timeout_ms=None,
                          skip_prompt_after_ms=None):
    """Wait for a JS condition with a hard ceiling and a user-skip escape.

    Polls page.wait_for_function in short chunks so we can:
      - honor a skip request (events.should_skip() -> 'S' in the console,
        a Skip button in the GUI),
      - emit a "still working" status (events.on_log) once the soft timer fires,
      - and enforce a hard timeout independent of the skip prompt.

    Returns True when the condition matched, False if the user asked to skip.
    Raises RunCancelled immediately if the user cancels the whole run while we're
    waiting (so Cancel interrupts the current route, not just between routes), and
    PlaywrightTimeoutError when the hard timeout elapses.
    """
    if hard_timeout_ms is None:
        hard_timeout_ms = report_timeout_ms()
    if skip_prompt_after_ms is None:
        skip_prompt_after_ms = SKIP_PROMPT_AFTER_MS

    start = time.monotonic()
    hard_deadline = start + hard_timeout_ms / 1000
    prompt_at = start + skip_prompt_after_ms / 1000
    poll_chunk_ms = 5000
    prompted = False
    next_status = 0.0

    while True:
        # Cancel wins over everything: stop waiting on this route right now rather
        # than only checking between routes (the "Cancel is just a suggestion" bug).
        if events.is_cancelled():
            raise RunCancelled()
        if events.should_skip():
            events.on_log(f"  {prefix} skipped by user")
            return False
        # Live view for the GUI: answer a pending Preview request (≤ one poll
        # chunk of latency) and keep the worker's status row current.
        maybe_screenshot(page, events, note=prefix.strip())
        events.on_status(events.worker_no,
                         f"{prefix} working… ({int(time.monotonic() - start)}s)")

        now = time.monotonic()
        if now >= hard_deadline:
            raise PlaywrightTimeoutError(
                f"Exceeded hard timeout of {int(hard_timeout_ms / 1000)}s"
            )

        chunk = min(poll_chunk_ms, max(100, int((hard_deadline - now) * 1000)))
        try:
            page.wait_for_function(js_condition, timeout=chunk)
            return True
        except PlaywrightTimeoutError:
            pass  # not done yet -- fall through and re-check skip / deadline

        now = time.monotonic()
        if not prompted and now >= prompt_at:
            elapsed = int(now - start)
            remaining = int(hard_deadline - now)
            events.on_log(
                f"  {prefix} still working ({elapsed}s elapsed; "
                f"up to {remaining}s left) -- you can skip this route"
            )
            prompted = True
            next_status = now + 30
        elif prompted and now >= next_status:
            events.on_log(f"  {prefix} still working ({int(now - start)}s)...")
            next_status = now + 30
