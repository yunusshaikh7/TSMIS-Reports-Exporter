"""Bulk-export Highway Detail PDFs for every California state route.

The SAME report as the Highway Detail Excel export (the site's "Highway Detail"
dropdown option), but saved as a PDF via the page's own Print layout
(`hd_printAll`) instead of the Excel Export button -- exactly like the Highway
Log PDF mirrors the Highway Log Excel export.

Output: output/highway_detail_pdf/highway_detail_route_<ROUTE>.pdf

The dropdown option text (`label`) stays "Highway Detail" -- the same option the
Excel export selects -- so `wait_js` / `is_empty` are identical to that export;
only the `save` differs (`hd_printAll` builds the `.hl-print-section` print
layout, then `page.pdf()` captures it). The registry's MENU label is "Highway
Detail (PDF)" (display only); the two must not be conflated.

Verified against the dev-site capture (TSMIS Dev Site 7.7): `highway_detail.js`
is live (no longer `cs-disabled`), its action bar wires `hd_exportToExcel()` +
`hd_printAll()`, and the empty state is `td.hl-empty` / "No results found in this
segment." (matched loosely so wording drift never stalls the loop).
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
from exporter import ReportSpec, save_highway_detail_pdf

# The loose no-results phrase, shared with the Excel Highway Detail export.
_EMPTY_RE = re.compile(r"No \w+ found", re.I)

SPEC = ReportSpec(
    label="Highway Detail",               # same dropdown option as the Excel export
    subdir="highway_detail_pdf",
    data_value="highway_detail",          # same #customReport id as the Excel export
    filename=lambda route: f"highway_detail_route_{route}.pdf",
    # Renders the SAME way as the Excel export: the action bar (Export button)
    # appears once the report finishes -- even for an empty route, which also shows
    # the empty row. Ready = Export button present OR either empty marker.
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('td.hl-empty') !== null "
        "|| /No \\w+ found/i.test(t); }"
    ),
    # Empty = the structural empty row first (robust to wording drift), the loose
    # no-results text as the fallback. is_empty runs BEFORE save, so the PDF render
    # only runs for routes that actually have rows.
    is_empty=lambda page: (
        page.locator("td.hl-empty").count() > 0
        or bool(_EMPTY_RE.search(page.inner_text("body")))
    ),
    save=save_highway_detail_pdf,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Highway Detail PDF Bulk Export")
