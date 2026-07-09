"""Bulk-export TSAR: Ramp Detail PDFs for every California state route.

The SAME report as the Ramp Detail Excel export (the site's "TSAR: Ramp
Detail" dropdown option), but saved as a PDF via the page's own Print layout
instead of the Excel Export button -- the exact parallel of the Highway Log /
Intersection Detail / Highway Detail / Highway Sequence PDF editions.

Output: output/ramp_detail_pdf/tsar_ramp_detail_route_<ROUTE>.pdf

Ramp Detail has no rd_printAll: its print body IS the site's shared async
`printAll()` dispatcher (shared.js), which on this report awaits a
showPrompt('Enter report title:') modal, then builds a cover page + one
11-column `.rd-print-table`. The save overrides `showPrompt` to auto-answer
with the route (no modal ever opens) alongside the usual `window.print`
override, and captures Landscape like the TSN statewide Ramp Detail print.

The dropdown option text (`label`) stays "TSAR: Ramp Detail" -- the same option
the Excel export selects -- so `wait_js` / `is_empty` are identical to that
export; only the `save` differs. The registry's MENU label is "TSAR: Ramp
Detail (PDF)" (display only); the two must not be conflated.

Verified against the site captures (main website-source AND TSMIS Dev Site
7.7): the action bar wires the shared `printAll()` whose fallthrough body is
the Ramp Detail print, and the empty state is "No ramps found in this segment."
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
from exporter import ReportSpec, save_ramp_detail_pdf

SPEC = ReportSpec(
    label="TSAR: Ramp Detail",            # same dropdown option as the Excel export
    subdir="ramp_detail_pdf",
    data_value="Ramp_Detail",             # same #customReport id as the Excel export
    filename=lambda route: f"tsar_ramp_detail_route_{route}.pdf",
    # Ready when the Export (download) button appears, or "No ramps found" --
    # identical to the Excel sibling.
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| t.includes('No ramps found'); }"
    ),
    # is_empty runs BEFORE save, so the PDF render only runs for routes that
    # actually have ramps.
    is_empty=lambda page: "No ramps found" in page.inner_text("body"),
    save=save_ramp_detail_pdf,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Ramp Detail PDF Bulk Export")
