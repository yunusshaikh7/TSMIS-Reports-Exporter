"""Bulk-export Highway Detail Excel files for every California state route.

Output: output/highway_detail/highway_detail_route_<ROUTE>.xlsx

ENABLED in v0.19.1 — export only. Reserved as v0.18.1 groundwork while the
site's new "Highway" TSAR group (Highway Detail / Highway Summary) sat
cs-disabled on the development site (2026-06-25); the site is opening the pair,
so the export goes live modeled on its Excel siblings. Where it is still greyed
or absent (production may lag the development site), select_report fails fast —
ReportUnavailableError for cs-disabled, a clear config error for a missing
option — instead of stalling per route.

The pair's final markup was never captured (no highway_detail.js in the dev-site
snapshot), so readiness/empty accept BOTH site conventions: the structural empty
row `td.hl-empty` (the newer intersection/highway-log template) and the loose
"No … found" text (the older hsl template). The engine's no-download fast-fail
(save_via_export_button -> EmptyExport) is the marker-independent backstop if
both drift.

Consolidation / comparison / matrix integration is a LATER feature — the report
deliberately stays absent from those registries until its real schema is known.

`data_value` matches the site's #customReport dropdown id ("highway_detail",
verified against the dev-site capture).
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

# The loose no-results phrase (hsl-style templates render it INSTEAD of the
# Export button; the newer templates render `td.hl-empty` alongside the button).
_EMPTY_RE = re.compile(r"No \w+ found", re.I)

SPEC = ReportSpec(
    label="Highway Detail",
    subdir="highway_detail",
    data_value="highway_detail",          # stable #customReport id (nested menu)
    filename=lambda route: f"highway_detail_route_{route}.xlsx",
    # Ready = the Export button rendered OR either empty marker appeared; either
    # means the report finished, then is_empty decides which it was. (An error
    # state is caught by the engine's report_error_text poll, not here.)
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('td.hl-empty') !== null "
        "|| /No \\w+ found/i.test(t); }"
    ),
    # Empty = the structural empty row first (robust to wording drift), the
    # loose no-results text as the fallback.
    is_empty=lambda page: (
        page.locator("td.hl-empty").count() > 0
        or bool(_EMPTY_RE.search(page.inner_text("body")))
    ),
    save=save_via_export_button,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Highway Detail Bulk Export")
