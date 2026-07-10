"""Bulk-export TSAR: Ramp Summary Excel workbooks for every California state route.

The SAME report as the Ramp Summary PDF export (the site's "TSAR: Ramp Summary"
dropdown option), but saved as an Excel workbook via the site's own Export
button (`rs_exportToExcel` builds the count tables as a workbook) instead of
capturing the inline page as a PDF. The INVERSE of the print editions: the
Excel sibling of a natively-PDF report.

Output: output/ramp_summary_excel/tsar_ramp_summary_route_<ROUTE>.xlsx

The dropdown option text (`label`) stays "TSAR: Ramp Summary" -- the same
option the PDF export selects -- so `wait_js` / `is_empty` are identical to
that export; only the `save` differs. The registry's MENU label is
"TSAR: Ramp Summary (Excel)" (display only); the two must not be conflated.

Verified against the site captures (main website-source AND TSMIS Dev Site
7.9): the Ramp Summary action bar renders an Export button wired to the shared
`exportToExcel()` dispatcher, which routes `Ramp_Summary` to
`rs_exportToExcel()` (an XLSX.writeFile download -- the empty path is a no-op,
caught by the engine's no-download fast-fail as the backstop).
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

from exporter import ReportSpec, save_via_export_button

SPEC = ReportSpec(
    label="TSAR: Ramp Summary",           # same dropdown option as the PDF export
    subdir="ramp_summary_excel",
    data_value="Ramp_Summary",            # same #customReport id as the PDF export
    filename=lambda route: f"tsar_ramp_summary_route_{route}.xlsx",
    # Renders the SAME way as the PDF export: inline, ready when the route
    # title appears or "No ramps found".
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return t.includes('Route {route}') || t.includes('No ramps found'); }}"
    ),
    is_empty=lambda page: "No ramps found" in page.inner_text("body"),
    save=save_via_export_button,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Ramp Summary Excel Bulk Export")
