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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playwright.sync_api import sync_playwright

from common import (
    REPORT_TIMEOUT_MS,
    ROUTES,
    AuthError,
    is_logged_in,
    navigate_with_auth,
    new_authed_browser,
    require_valid_auth,
    select_report,
    wait_with_skip_option,
)
from events import Events, RunResult
from paths import OUTPUT_ROOT


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


def run_export(spec, events=None, *, routes=ROUTES):
    """Export `spec` for every route. Console-free; returns a RunResult.

    Raises AuthError if the saved session is missing/expired (the caller
    decides how to surface it). Honors events.should_skip() while waiting on a
    route and events.is_cancelled() between routes. Already-downloaded files are
    skipped, so re-running resumes where a previous run left off.
    """
    events = events or Events()
    require_valid_auth()

    out_dir = OUTPUT_ROOT / spec.subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    result = RunResult(output_dir=str(out_dir))
    total = len(routes)

    with sync_playwright() as p:
        browser, _ctx, page = new_authed_browser(p)
        try:
            navigate_with_auth(page)
            if not is_logged_in(page):
                raise AuthError("Saved session is expired or invalid.")

            events.on_log("Logged in. Setting up form...")
            select_report(page, spec.label)
            events.on_log("Ready. Starting export.")

            for i, route in enumerate(routes, 1):
                if events.is_cancelled():
                    events.on_log("Cancelled by user.")
                    break

                prefix = f"[{i:>3}/{total}] Route {route}:"
                out_path = out_dir / spec.filename(route)

                if out_path.exists():
                    events.on_log(f"{prefix} already exists, skip")
                    events.on_route(route, "exists")
                    continue

                try:
                    page.get_by_label("Route", exact=True).select_option(route)
                    page.get_by_role("button", name="Generate").click()
                    matched = wait_with_skip_option(page, spec.wait_js(route), prefix, events)
                    if not matched:
                        result.user_skipped.append(route)
                        events.on_route(route, "skipped")
                        _recover(page, spec)
                        continue

                    if spec.is_empty(page):
                        events.on_log(f"{prefix} empty, skip")
                        result.empty.append(route)
                        events.on_route(route, "empty")
                        continue

                    page.wait_for_timeout(1000)
                    spec.save(page, out_path)
                    result.saved += 1
                    events.on_log(f"{prefix} saved")
                    events.on_route(route, "saved")

                except AuthError:
                    raise
                except Exception as e:
                    events.on_log(f"{prefix} FAILED ({type(e).__name__}) -- recovering")
                    result.failed.append(route)
                    try:
                        _recover(page, spec)
                    except AuthError:
                        raise
                    except Exception as recovery_err:
                        events.on_log(f"Recovery failed: {recovery_err}")
                        break
        finally:
            browser.close()

    return result
