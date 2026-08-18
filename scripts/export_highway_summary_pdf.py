"""Bulk-export Highway Summary PDFs for every California state route.

The SAME report as the Highway Summary Excel export (the site's "Highway
Summary" dropdown option), but saved as a PDF via the page's own Print layout
(`hs_printAll`) instead of the Excel Export button -- exactly like the other
print editions mirror their Excel siblings.

Output: output/highway_summary_pdf/highway_summary_route_<ROUTE>.pdf

The dropdown option text (`label`) stays "Highway Summary" -- the same option
the Excel export selects -- so `wait_js` / `is_empty` are identical to that
export; only the `save` differs. The registry's MENU label is "Highway Summary
(PDF)" (display only); the two must not be conflated. Sharing the `data_value`
means selecting BOTH editions coalesces: the route renders once and both files
are saved off that render.

EXPORT-ONLY, deliberately. The vendor's 2026-08-17 release delivered the Excel
edition only, so there is no real print to verify a parser against; the
consolidator / comparisons land once statewide PDFs exist (the Highway Detail
v0.19.2 -> v0.20.0 sequence, and the same rule the Highway Sequence and Ramp
Detail print editions followed).

Verified against the 2026-08-10 site capture (`highway_summary.js`): the action
bar wires `hs_exportToExcel()` + `hs_printAll()`; the print PREPENDS a cover
page (`.rs-cover.hs-cover`, code OTM22230) to the inline section tables and
calls the shared `printWithTitle('highway_summary')`, which is `window.print()`
plus a title swap. Narrow two-column code/miles tables -> Portrait, like the
Intersection Summary print edition.
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
from exporter import ReportSpec, save_highway_summary_pdf

# The loose no-results phrase, shared with the Excel Highway Summary export
# (hs_showResults('none') renders `<span class="ramp-empty">No results found in
# this segment.</span>`; hsl-style templates render the same phrase instead of
# the Export button).
_EMPTY_RE = re.compile(r"No \w+ found", re.I)

SPEC = ReportSpec(
    label="Highway Summary",              # same dropdown option as the Excel export
    subdir="highway_summary_pdf",
    data_value="highway_summary",         # same #customReport id as the Excel export
    filename=lambda route: f"highway_summary_route_{route}.pdf",
    # Identical to the Excel edition's readiness test (they share one render):
    # the Export button rendered OR either empty marker appeared.
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('td.hl-empty') !== null "
        "|| /No \\w+ found/i.test(t); }"
    ),
    # Identical to the Excel edition's empty test, so the two editions can never
    # disagree about whether a route had data (they are saved off ONE render).
    is_empty=lambda page: (
        page.locator("td.hl-empty").count() > 0
        or bool(_EMPTY_RE.search(page.inner_text("body")))
    ),
    save=save_highway_summary_pdf,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Highway Summary PDF Bulk Export")
