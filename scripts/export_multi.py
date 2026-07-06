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
    if __name__ == "__main__":     # console run: friendly .bat guidance, clean exit
        print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
        sys.exit(1)
    # Imported (the GUI reaches here via report_catalog -> SPEC): raise a REAL
    # error the caller's fatal-path can SHOW -- print+sys.exit at import time
    # killed a windowed exe silently (exit 1, no dialog).
    raise

from cli import run_cli_multi
from reports import EXPORT_REPORTS

# (label, ReportSpec) in menu order, derived from the shared registry so it can't
# drift from the GUI's report list.
REPORTS = [(label, spec) for label, _fmt, spec in EXPORT_REPORTS]

if __name__ == "__main__":
    run_cli_multi(REPORTS, title="TSMIS Multi-Report Export")
