"""Clean Road Files (Highway / Intersection / Ramp) -- the site's flat legacy-CSV
replicas, exported per route through the universal Export button.

RESERVED 2026-07-22 (dev site 7.21: three `cs-disabled` options with no report
module behind them) and ENABLED 2026-09-02 off the dev site 9.1 capture
(`site-captures/TSMIS Dev Site 9.1/`, BUILD_DATE 2026-08-19 09:35): the three
options are no longer greyed and the site ships their modules --
`clean_highway.js` / `clean_intersection.js` / `clean_ramp.js`. Each renders a
flat, one-row-per-record table in the legacy TASAS CSV column layout (the FULL
header: 74 `THY_*` / 55 `INX_*` / 34 `RAM_*` columns; columns the site has no
layer source for stay present and blank) into #rampResults through the shared
action bar (`renderActionBar`: Export = `clh_/cli_/clr_exportToExcel()`,
Print = `*_printAll()`), so the Excel-sibling model applies unchanged:

  * ready = the Export button rendered (EXPORT_READY_JS) OR the empty marker;
  * empty = `*_showResults('none')` renders `<span class="ramp-empty">No results
    found in this segment.</span>` with NO action bar -- matched by the
    structural `.ramp-empty` first, the loose "No ... found" text second;
  * error = the `error` class on #rampResults (the engine's ERROR_JS);
  * save  = save_via_export_button (a client-side `XLSX.writeFile`; the engine's
    no-download fast-fail is the backstop).

The site names its download `clean_road_<kind>_<district><county><route>.xlsx`;
the app names the saved file itself (`filename`). The options are FLAT
`cs-option cs-sub` rows under a `cs-header` (not a fly-out leaf), so
select_report needs no submenu reveal; it matches the stable `data-value`
(`clean_highway` / `clean_intersection` / `clean_ramp`), and `label` here is the
site's `data-label` (the text it writes into the hidden #reportSelect option).

Run-time note: the reports reuse the site's Highway Log / Intersection Detail /
Ramp Detail query pipelines (Clean Highway runs the WHOLE Highway Log builder
plus four extra layer lookups per route), so expect Highway-Log-class times.

Print editions (`*_printAll`: cover page + landscape scale-to-fit) exist on the
site but are deliberately NOT wired: there is no real print to census a parser
against yet (the HSL / RD-PDF sequence -- ship the export, census real work-PC
output, then integrate). Consolidating / comparing these SITE exports is the
same later tier. The TSN side is already staged: `report_catalog.TSN` carries
the three library slots (`tsn_load_clean_road`; Highway normalizes verbatim,
Intersection / Ramp stay refusing skeletons).

Where the live site still greys a report (prod lags dev), select_report fails
fast with ReportUnavailableError -- no per-route stall.
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

# The loose no-results phrase (`*_showResults('none')` renders "No results found
# in this segment."), the fallback behind the structural `.ramp-empty` marker so
# wording drift never stalls the loop.
_EMPTY_RE = re.compile(r"No \w+ found", re.I)


def _wait_js(route):
    """Ready = the Export button rendered OR the empty marker appeared; either
    means the report finished, then is_empty decides which it was. (An error
    state is caught by the engine's ERROR_JS / report_error_text, not here.)"""
    return (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| document.querySelector('#rampResults .ramp-empty') !== null "
        "|| /No \\w+ found/i.test(t); }"
    )


def _is_empty(page):
    """Empty = the structural marker first (robust to wording drift), the loose
    no-results text as the fallback."""
    return (page.locator("#rampResults .ramp-empty").count() > 0
            or bool(_EMPTY_RE.search(page.inner_text("body"))))


def _spec(key, label):
    """One Clean Road spec. `key` is the site's stable #customReport data-value
    AND the app's export key / output subdir; `label` is the site's data-label
    (the exact text of the hidden #reportSelect option)."""
    return ReportSpec(
        label=label,
        subdir=key,
        data_value=key,                   # stable #customReport id (dev site 9.1)
        filename=lambda route, key=key: f"{key}_route_{route}.xlsx",
        wait_js=_wait_js,
        is_empty=_is_empty,
        save=save_via_export_button,
    )


HIGHWAY_SPEC = _spec("clean_highway", "Clean Road File Highway")
INTERSECTION_SPEC = _spec("clean_intersection", "Clean Road File Intersection")
RAMP_SPEC = _spec("clean_ramp", "Clean Road File Ramp")

if __name__ == "__main__":
    from cli import run_cli
    run_cli(HIGHWAY_SPEC, title="TSMIS Clean Road File (Highway) Bulk Export")
