"""Bulk-export Intersection Detail Excel files for every California state route.

Output: output/intersection_detail/intersection_detail_route_<ROUTE>.xlsx

Label verified against the live page source (v0.10.4): the dropdown text is
exactly "Intersection Detail" — no "TSAR:" prefix, unlike the ramp pair.

Empty-marker fix (v0.11): an empty route renders its action bar (the Export
button is ALWAYS present, like Highway Log) plus an empty table row
`<td class="hl-empty">No results found.</td>` — NOT the old best-guess
"no intersections". The previous predicate never matched, so the engine clicked
Export, the site's intd_exportToExcel() no-op'd (zero rows -> early return), and
the download wait burned the full ceiling + retry (~21 min) before mislabeling
the route `failed`. Detect the empty row structurally (`td.hl-empty`) with the
text as a fallback. The general no-download fast-fail in the engine
(save_via_export_button -> EmptyExport) is the marker-independent backstop, so
even if these strings drift this can no longer hang.

⚠ Intersections are still under active development on the site — re-verify the
`td.hl-empty` / "No results found." signals once the feature is finalized.
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli
from common import EXPORT_READY_JS
from exporter import ReportSpec, save_via_export_button

SPEC = ReportSpec(
    label="Intersection Detail",
    subdir="intersection_detail",
    data_value="intersection_detail",     # stable #customReport id (flat + nested)
    filename=lambda route: f"intersection_detail_route_{route}.xlsx",
    # The action bar (Export button) renders even for an empty route, so readiness
    # is "Export button present OR the empty row appeared". Either means the
    # report finished; is_empty then decides which it was.
    wait_js=lambda route: (
        "() => { "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('td.hl-empty') !== null; }"
    ),
    # Empty = the site's empty table row. Structural signal first (robust to
    # wording drift), the "No results found." text as a fallback.
    is_empty=lambda page: (
        page.locator("td.hl-empty").count() > 0
        or "no results found" in page.inner_text("body").lower()
    ),
    save=save_via_export_button,
)

if __name__ == "__main__":
    run_cli(SPEC, title="TSMIS Intersection Detail Bulk Export")
