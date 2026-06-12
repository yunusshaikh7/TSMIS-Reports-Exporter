"""Bulk-export TSAR: Intersection Summary PDFs for every California state route.

Output: output/intersection_summary/tsar_intersection_summary_route_<ROUTE>.pdf

Mirrors export_ramp_summary.py (renders inline -> printed to PDF). The label
must match the #customReport dropdown text exactly — the Settings env check
reads the dropdown for every registered report, so a mismatch shows up there
as "missing" without running an export.
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli
from exporter import ReportSpec, save_pdf_letter

SPEC = ReportSpec(
    label="TSAR: Intersection Summary",
    subdir="intersection_summary",
    filename=lambda route: f"tsar_intersection_summary_route_{route}.pdf",
    # Renders inline: ready when the route title appears, or the report's
    # own "no intersections" notice (case-insensitive, like the site's
    # "No ramps found" counterpart).
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return t.includes('Route {route}') "
        "|| t.toLowerCase().includes('no intersections'); }"
    ),
    is_empty=lambda page: "no intersections" in page.inner_text("body").lower(),
    save=save_pdf_letter,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Intersection Summary Bulk Export")
