"""Bulk-export TSAR: Ramp Summary PDFs for every California state route.

Output: output/ramp_summary/tsar_ramp_summary_route_<ROUTE>.pdf
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

from cli import run_cli
from exporter import ReportSpec, save_pdf_letter

SPEC = ReportSpec(
    label="TSAR: Ramp Summary",
    subdir="ramp_summary",
    data_value="Ramp_Summary",            # stable #customReport id (flat + nested)
    filename=lambda route: f"tsar_ramp_summary_route_{route}.pdf",
    # Renders inline: ready when the route title appears, or "No ramps found".
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return t.includes('Route {route}') || t.includes('No ramps found'); }}"
    ),
    is_empty=lambda page: "No ramps found" in page.inner_text("body"),
    save=save_pdf_letter,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Ramp Summary Bulk Export")
