"""Clean Road Files (Highway / Intersection / Ramp) -- RESERVED, app-wide-DISABLED
placeholders.

The TSMIS dev site added a "Clean Road Files" group to the #customReport dropdown
on 2026-07-21 (capture `site-captures/TSMIS Dev Site 7.21/`): a `cs-header`
followed by three `cs-option cs-sub cs-disabled` entries --

    data-value="clean_highway"       data-label="Highway"
    data-value="clean_intersection"  data-label="Intersection"
    data-value="clean_ramp"          data-label="Ramp"

They are GREYED and inert: the capture ships no `clean_*.js` report module and
nothing anywhere in the site's JS references those values, so there is no
Generate -> Export flow to drive and no export/print function name to bind to.
That is exactly the state Highway Detail / Summary were in on the 6.26 capture
before v0.18.1 reserved them.

These three entries exist so the reports SHOW UP greyed in the picker (users can
see the site gained them) and their stable export ids are reserved -- the v0.18.1
Highway-pair / v0.25.1 Route History path. `reports.DISABLED_EXPORT_SUBDIRS` gates
them app-wide and the start guards reject their keys server-side.

Enabling one later = give it a real `save` (its site export function, read off a
fresh capture), fill in the ready/empty conventions, and drop its subdir from the
gate. Until then each `save` fails LOUDLY on every route rather than pretending to
export, so an accidental un-gating can never write empty files.

The TSN side of these reports is already staged: `report_catalog.TSN` carries
`clean_highway` / `clean_intersection` / `clean_ramp` library slots for the
"CA HIGHWAYS / CA INTERSECTIONS / CA RAMPS" extracts (see `tsn_load_clean_road`).
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

from errors import ReportError
from exporter import ReportSpec


def _unsupported(label):
    """A `save` that refuses: the site greys this report and offers no export."""
    def save(page, out_path, timeout_ms=None):
        raise ReportError(
            f"The Clean Road {label} report can't be exported yet — on the TSMIS "
            "site it is still greyed out and has no export control.")
    return save


def _reserved_spec(key, label):
    """One reserved-DISABLED Clean Road spec. `key` is the site's stable
    #customReport data-value AND the app's export key / output subdir."""
    return ReportSpec(
        label=f"Clean Road: {label}",
        subdir=key,
        data_value=key,                   # stable #customReport id (dev site, 2026-07-21)
        filename=lambda route, key=key: f"{key}_route_{route}.xlsx",
        # No report module ships yet, so there is no ready/empty state to read.
        # Unreachable while gated; `save` refuses regardless.
        wait_js=lambda route: "() => true",
        is_empty=lambda page: False,
        save=_unsupported(label),
    )


HIGHWAY_SPEC = _reserved_spec("clean_highway", "Highway")
INTERSECTION_SPEC = _reserved_spec("clean_intersection", "Intersection")
RAMP_SPEC = _reserved_spec("clean_ramp", "Ramp")
