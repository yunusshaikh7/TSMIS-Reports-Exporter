"""Bulk-export Highway Log PDFs for every California state route.

The SAME report as the Highway Log Excel export (the site's "Highway Log"
dropdown option), but saved as a PDF via the page's own Print layout
(`hl_printAll`) instead of the Excel Export button -- like the Ramp Summary PDF.

Output: output/highway_log_pdf/highway_log_route_<ROUTE>.pdf
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli
from common import EXPORT_READY_JS
from exporter import ReportSpec, save_highway_log_pdf

SPEC = ReportSpec(
    label="Highway Log",                 # same dropdown option as the Excel export
    subdir="highway_log_pdf",
    data_value="highway_log",            # same #customReport id as the Excel export
    filename=lambda route: f"highway_log_route_{route}.pdf",
    # The report renders the SAME way for the Excel button and the Print layout,
    # so the ready signal is identical to the Excel export: the action bar (with
    # the Export button) appears once the report finishes -- even for an empty
    # route. (Match a no-results phrase too so the loop never stalls.)
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| /No results found/i.test(t); }"
    ),
    # Empty detected by the table's no-results text (the action bar / Export
    # button is present even on an empty route). Checked BEFORE save, so the PDF
    # render only runs for routes that actually have rows.
    is_empty=lambda page: "No results found" in page.inner_text("body"),
    save=save_highway_log_pdf,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Highway Log PDF Bulk Export")
