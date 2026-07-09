"""Bulk-export Highway Sequence Listing PDFs for every California state route.

The SAME report as the Highway Sequence Excel export (the site's "Highway
Sequence Listing" dropdown option), but saved as a PDF via the page's own Print
layout (`hsl_printAll`) instead of the Excel Export button -- exactly like the
Highway Log / Intersection Detail / Highway Detail PDF editions mirror their
Excel siblings.

Output: output/highway_sequence_pdf/highway_sequence_route_<ROUTE>.pdf

The dropdown option text (`label`) stays "Highway Sequence Listing" -- the same
option the Excel export selects -- so `wait_js` / `is_empty` are identical to
that export; only the `save` differs (`hsl_printAll` builds the cover + legend
+ per-district `.hsl-print-table` sections, then `page.pdf()` captures them,
Portrait like the TSN district prints). The registry's MENU label is "Highway
Sequence Listing (PDF)" (display only); the two must not be conflated.

Verified against the site captures (main website-source AND TSMIS Dev Site
7.7): the action bar wires the shared `printAll()` which dispatches
`hsl_printAll()` for `highway_sequence`, and the empty state is the
"No results found in this segment." message (matched loosely so wording drift
never stalls the loop).
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
from exporter import ReportSpec, save_highway_sequence_pdf

# The loose no-results phrase, shared with the Excel Highway Sequence export.
_EMPTY_RE = re.compile(r"No \w+ found", re.I)

SPEC = ReportSpec(
    label="Highway Sequence Listing",     # same dropdown option as the Excel export
    subdir="highway_sequence_pdf",
    data_value="highway_sequence",        # same #customReport id as the Excel export
    filename=lambda route: f"highway_sequence_route_{route}.pdf",
    # Renders the SAME way as the Excel export: ready when the Export button
    # appears or the no-results message shows.
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| /No \\w+ found/i.test(t); }"
    ),
    # Key empty on the POSITIVE no-results text, NOT on Export-button absence
    # (same rationale as the Excel sibling: an errored route also lacks the
    # button). is_empty runs BEFORE save, so the PDF render only runs for routes
    # that actually have rows.
    is_empty=lambda page: bool(_EMPTY_RE.search(page.inner_text("body"))),
    save=save_highway_sequence_pdf,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Highway Sequence PDF Bulk Export")
