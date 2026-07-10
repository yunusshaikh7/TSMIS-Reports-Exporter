"""Bulk-export Intersection Summary PDFs for every California state route.

The SAME report as the Intersection Summary Excel export (the site's
"Intersection Summary" dropdown option), but saved as a PDF via the page's own
Print layout (`ints_printAll`) instead of the Excel Export button -- exactly
like the other print editions mirror their Excel siblings.

Output: output/intersection_summary_pdf/intersection_summary_route_<ROUTE>.pdf

The dropdown option text (`label`) stays "Intersection Summary" -- the same
option the Excel export selects -- so `wait_js` / `is_empty` are identical to
that export; only the `save` differs (`ints_printAll` PREPENDS a cover page to
the inline count tables -- no pagination, unlike the row reports -- then
`page.pdf()` captures them, Portrait like the native Ramp Summary PDF). The
registry's MENU label is "Intersection Summary (PDF)" (display only); the two
must not be conflated.

Verified against the site captures (main website-source AND TSMIS Dev Site
7.9): the action bar wires the shared `printAll()` which dispatches
`ints_printAll()` for `intersection_summary`, and the report always renders
`Total Intersections = N` (including `= 0` -- the empty marker).
"""
import re
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
from exporter import ReportSpec, save_intersection_summary_pdf

# Zero-total marker, shared with the Excel Intersection Summary export.
_ZERO_TOTAL = re.compile(r"total intersections\s*=\s*0\b")

SPEC = ReportSpec(
    label="Intersection Summary",         # same dropdown option as the Excel export
    subdir="intersection_summary_pdf",
    data_value="intersection_summary",    # same #customReport id as the Excel export
    filename=lambda route: f"intersection_summary_route_{route}.pdf",
    # Renders the SAME way as the Excel export: ready when the Export button or
    # the summary total line has rendered (the summary is always shown, even at
    # zero).
    wait_js=lambda route: (
        "() => { "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('.ints-total') !== null; }"
    ),
    # A zero total is empty (never a missing-notice text -- the report always
    # renders). is_empty runs BEFORE save, so the PDF render only runs for
    # routes that actually have intersections; the save re-reads the total as
    # its marker-independent backstop.
    is_empty=lambda page: bool(_ZERO_TOTAL.search(page.inner_text("body").lower())),
    save=save_intersection_summary_pdf,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Intersection Summary PDF Bulk Export")
