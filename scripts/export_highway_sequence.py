"""Bulk-export Highway Sequence Listing Excel files for every California state route.

Output: output/highway_sequence/highway_sequence_route_<ROUTE>.xlsx
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
    label="Highway Sequence Listing",
    subdir="highway_sequence",
    filename=lambda route: f"highway_sequence_route_{route}.xlsx",
    # The Export button only renders when the report has data; an empty route
    # shows a "No ... found" message instead. Match that loosely so unknown
    # empty-state wording doesn't stall the loop.
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| /No \\w+ found/i.test(t); }"
    ),
    is_empty=lambda page: page.locator("button.export-btn").count() == 0,
    save=save_via_export_button,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Highway Sequence Bulk Export")
