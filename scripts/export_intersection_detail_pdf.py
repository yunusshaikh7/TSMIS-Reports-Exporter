"""Bulk-export Intersection Detail PDFs for every California state route.

The SAME report as the Intersection Detail Excel export (the site's "Intersection
Detail" dropdown option), but saved as a PDF via the page's own Print layout
(`intd_printAll`) instead of the Excel Export button -- exactly like the Highway
Log PDF mirrors the Highway Log Excel export.

Output: output/intersection_detail_pdf/intersection_detail_route_<ROUTE>.pdf

The dropdown option text (`label`) stays "Intersection Detail" -- the same option
the Excel export selects -- so `wait_js` / `is_empty` are identical to that
export; only the `save` differs. The registry's MENU label is "Intersection
Detail (PDF)" (display only); the two must not be conflated.

⚠ Intersections are still under active development on the site -- the empty-state
signals (`td.hl-empty` / "No results found.") are shared with the Excel export and
must be re-verified once the feature is finalized.
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli
from common import EXPORT_READY_JS
from exporter import ReportSpec, save_intersection_detail_pdf

SPEC = ReportSpec(
    label="Intersection Detail",          # same dropdown option as the Excel export
    subdir="intersection_detail_pdf",
    data_value="intersection_detail",     # same #customReport id as the Excel export
    filename=lambda route: f"intersection_detail_route_{route}.pdf",
    # Renders the SAME way as the Excel export: the action bar (Export button)
    # appears even on an empty route, plus the empty table row. Ready = Export
    # button present OR the empty row appeared; is_empty then decides which.
    wait_js=lambda route: (
        "() => { "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('td.hl-empty') !== null; }"
    ),
    # Empty = the site's empty table row (structural, robust to wording drift),
    # the "No results found." text as a fallback. is_empty runs BEFORE save, so
    # the PDF render only runs for routes that actually have rows.
    is_empty=lambda page: (
        page.locator("td.hl-empty").count() > 0
        or "no results found" in page.inner_text("body").lower()
    ),
    save=save_intersection_detail_pdf,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Intersection Detail PDF Bulk Export")
