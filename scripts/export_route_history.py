"""Route History Table -- a RESERVED, app-wide-DISABLED placeholder (v0.25.1).

The TSMIS dev site added a "Route History Table" report on 2026-07-09
(`data_value="route_history"`, flat top-level option). It is NOT a query
report: selecting it drops straight into an embedded SSRS report
(`route_history.js` renders an iframe onto the TSN report server; the user
picks District/County/Route/Date in the SSRS parameter panel), so there is no
per-route Generate -> Export flow for the engine to drive.

This entry exists so the report SHOWS UP greyed in the picker (users can see
the site gained it) and its stable export id is reserved -- the same
reserved-DISABLED groundwork path Highway Detail/Summary took in v0.18.1
(`reports.DISABLED_EXPORT_SUBDIRS` gates it app-wide; the start guards reject
its key server-side). If the site later gives Route History a real export
path, enabling it = write the real save + empty the gate.

The spec below is intentionally minimal and CANNOT run while gated; if a
future change un-gates it without replacing `save`, the save fails every
route loudly rather than pretending to export.
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


def _save_unsupported(page, out_path, timeout_ms=None):
    """Route History has no export flow yet (an embedded SSRS report)."""
    raise ReportError(
        "The Route History Table can't be exported yet — on the TSMIS site it "
        "is an embedded report without an export control.")


SPEC = ReportSpec(
    label="Route History Table",
    subdir="route_history",
    data_value="route_history",           # stable #customReport id (dev site, 2026-07-09)
    filename=lambda route: f"route_history_route_{route}.pdf",
    # The embed renders immediately; there is no per-route ready/empty state.
    wait_js=lambda route: "() => true",
    is_empty=lambda page: False,
    save=_save_unsupported,
)

if __name__ == "__main__":
    from cli import run_cli
    run_cli(SPEC, title="TSMIS Route History Table Export (not yet supported)")
