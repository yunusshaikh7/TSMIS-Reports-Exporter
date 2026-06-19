"""Bulk-export Highway Sequence Listing Excel files for every California state route.

Output: output/highway_sequence/highway_sequence_route_<ROUTE>.xlsx
"""
import re
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli
from common import EXPORT_READY_JS
from exporter import ReportSpec, save_via_export_button

# The Export button only renders when the report has data; an empty route shows
# a "No results found" message instead (hsl.js). Match it loosely so minor
# wording variants don't stall the loop — the SAME pattern wait_js trusts.
_EMPTY_RE = re.compile(r"No \w+ found", re.I)

SPEC = ReportSpec(
    label="Highway Sequence Listing",
    subdir="highway_sequence",
    filename=lambda route: f"highway_sequence_route_{route}.xlsx",
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| /No \\w+ found/i.test(t); }"
    ),
    # Key empty on the POSITIVE no-results text, NOT on Export-button absence:
    # a fatal error page ALSO lacks the button but renders its message in
    # #rampResults.error (caught first by report_error_text), not as this text,
    # so button-absence alone would misclassify an errored route as "No data".
    is_empty=lambda page: bool(_EMPTY_RE.search(page.inner_text("body"))),
    save=save_via_export_button,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Highway Sequence Bulk Export")
