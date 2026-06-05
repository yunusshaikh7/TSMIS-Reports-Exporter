"""Export SEVERAL TSMIS report types in one run (console).

Prompts which report types and which routes, then runs each selected report with
the proven engine -- sequentially, or in fast mode if TSMIS_FAST_WORKERS is set
(each report runs one after another, so only N browsers are ever open at once).
Backs the "Several / all report types at once" option in the export .bat menus.
"""
import sys

try:
    from playwright.sync_api import sync_playwright  # noqa: F401  (fail early, clearly)
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from cli import run_cli_multi
from export_ramp_summary import SPEC as SUMMARY_SPEC
from export_ramp_detail import SPEC as DETAIL_SPEC
from export_highway_sequence import SPEC as HIGHWAY_SPEC
from export_highway_log import SPEC as HIGHWAY_LOG_SPEC

# (label, ReportSpec) in menu order -- mirrors the single-report menu numbering.
REPORTS = [
    ("TSAR: Ramp Summary", SUMMARY_SPEC),
    ("TSAR: Ramp Detail", DETAIL_SPEC),
    ("Highway Sequence Listing", HIGHWAY_SPEC),
    ("Highway Log", HIGHWAY_LOG_SPEC),
]

if __name__ == "__main__":
    run_cli_multi(REPORTS, title="TSMIS Multi-Report Export")
