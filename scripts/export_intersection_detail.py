"""Bulk-export TSAR: Intersection Detail Excel files for every California state route.

Output: output/intersection_detail/tsar_intersection_detail_route_<ROUTE>.xlsx

Mirrors export_ramp_detail.py (Export-button download). The label must match
the #customReport dropdown text exactly — the Settings env check reads the
dropdown for every registered report, so a mismatch shows up there as
"missing" without running an export.
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
    label="TSAR: Intersection Detail",
    subdir="intersection_detail",
    filename=lambda route: f"tsar_intersection_detail_route_{route}.xlsx",
    # Ready when the Export (download) button appears, or the report's own
    # "no intersections" notice.
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        "return document.querySelector('button.export-btn') !== null "
        "|| t.toLowerCase().includes('no intersections'); }"
    ),
    is_empty=lambda page: "no intersections" in page.inner_text("body").lower(),
    save=save_via_export_button,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Intersection Detail Bulk Export")
