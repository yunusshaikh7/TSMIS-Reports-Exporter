"""Bulk-export Highway Log Excel files for every California state route.

Output: output/highway_log/highway_log_route_<ROUTE>.xlsx
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli
from common import EXPORT_READY_JS
from exporter import ReportSpec, save_via_export_button

SPEC = ReportSpec(
    label="Highway Log",
    subdir="highway_log",
    filename=lambda route: f"highway_log_route_{route}.xlsx",
    # Highway Log always renders its action bar (with the Export button) once the
    # report finishes -- even for a route with no rows -- so "Export button
    # present" is the ready signal. The form clears the previous report on Generate,
    # so this waits for the NEW button. (An error state shows no button and a
    # message; match a no-results phrase too so the loop never stalls on one.)
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| /No results found/i.test(t); }"
    ),
    # Unlike the other Excel reports, the Export button is present even when a
    # route has no data, so detect empty by the table's no-results text instead of
    # the button's absence. (Clicking Export on an empty route is a no-op on the
    # site and would otherwise hang waiting for a download that never starts.)
    is_empty=lambda page: "No results found" in page.inner_text("body"),
    save=save_via_export_button,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Highway Log Bulk Export")
