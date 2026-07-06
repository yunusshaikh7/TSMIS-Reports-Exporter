"""Bulk-export TSAR: Ramp Detail Excel files for every California state route.

Output: output/ramp_detail/tsar_ramp_detail_route_<ROUTE>.xlsx
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    if __name__ == "__main__":     # console run: friendly .bat guidance, clean exit
        print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
        sys.exit(1)
    # Imported (the GUI reaches here via report_catalog -> SPEC): raise a REAL
    # error the caller's fatal-path can SHOW -- print+sys.exit at import time
    # killed a windowed exe silently (exit 1, no dialog).
    raise

from common import EXPORT_READY_JS
from exporter import ReportSpec, save_via_export_button

SPEC = ReportSpec(
    label="TSAR: Ramp Detail",
    subdir="ramp_detail",
    data_value="Ramp_Detail",             # stable #customReport id (flat + nested)
    filename=lambda route: f"tsar_ramp_detail_route_{route}.xlsx",
    # Ready when the Export (download) button appears, or "No ramps found".
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| t.includes('No ramps found'); }"
    ),
    is_empty=lambda page: "No ramps found" in page.inner_text("body"),
    save=save_via_export_button,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Ramp Detail Bulk Export")
