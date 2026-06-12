"""Bulk-export Intersection Summary Excel files for every California state route.

Output: output/intersection_summary/intersection_summary_route_<ROUTE>.xlsx

Label + format verified against the live page source (v0.10.4): the dropdown
text is exactly "Intersection Summary" (no "TSAR:" prefix, unlike the ramp
pair) and the report downloads as Excel via the shared Export button. The
empty-marker text ("no intersections") is still best-guess — the shared
ERROR_JS catch and the per-route timeout cover a different wording.
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli
from exporter import ReportSpec, save_via_export_button

SPEC = ReportSpec(
    label="Intersection Summary",
    subdir="intersection_summary",
    filename=lambda route: f"intersection_summary_route_{route}.xlsx",
    # Ready when the Export (download) button appears, or the report's own
    # "no intersections" notice (case-insensitive).
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        "return document.querySelector('button.export-btn') !== null "
        "|| t.toLowerCase().includes('no intersections'); }"
    ),
    is_empty=lambda page: "no intersections" in page.inner_text("body").lower(),
    save=save_via_export_button,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Intersection Summary Bulk Export")
