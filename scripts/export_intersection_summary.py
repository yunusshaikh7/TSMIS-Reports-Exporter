"""Bulk-export Intersection Summary Excel files for every California state route.

Output: output/intersection_summary/intersection_summary_route_<ROUTE>.xlsx

Label + format verified against the live page source (v0.10.4): the dropdown
text is exactly "Intersection Summary" (no "TSAR:" prefix, unlike the ramp
pair) and the report downloads as Excel via the shared Export button.

Empty-marker fix (v0.11): Intersection Summary never renders an empty notice —
it ALWAYS shows `Total Intersections = N` (including `= 0`) and always offers a
working Export. So the old best-guess "no intersections" predicate never matched
and a zero-intersection route was exported as an all-zeros workbook instead of
being recorded `empty`. Detect a zero total instead, so a no-data route is
skipped like every other report. (No hang risk either way here: the Export
always produces a download, so if this marker drifts the route just reverts to
the old benign all-zeros-file behavior — never the 21-min stall.)

⚠ Intersections are still under active development on the site — re-verify the
`Total Intersections = 0` signal once the feature is finalized.
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
from exporter import ReportSpec, save_via_export_button

# Zero-total marker, e.g. "Total Intersections = 0" (but not "= 10"/"= 20").
_ZERO_TOTAL = re.compile(r"total intersections\s*=\s*0\b")

SPEC = ReportSpec(
    label="Intersection Summary",
    subdir="intersection_summary",
    data_value="intersection_summary",    # stable #customReport id (flat + nested)
    filename=lambda route: f"intersection_summary_route_{route}.xlsx",
    # Ready when the Export button or the summary total line has rendered (the
    # summary is always shown, even at zero).
    wait_js=lambda route: (
        "() => { "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('.ints-total') !== null; }"
    ),
    is_empty=lambda page: bool(_ZERO_TOTAL.search(page.inner_text("body").lower())),
    save=save_via_export_button,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Intersection Summary Bulk Export")
