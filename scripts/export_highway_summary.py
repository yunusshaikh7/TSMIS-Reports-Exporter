"""Reserved groundwork for the coming TSMIS "Highway Summary" TSAR report.

NOT yet usable — the exact parallel of export_highway_detail. The TSMIS site is
adding a new "Highway" report group (Highway Detail / Highway Summary), cs-disabled
on the development site as of 2026-06-25 (production to follow). This module RESERVES
the report's identity so it threads across the app (catalog, stable export key, the
family-grouped picker) and enabling it later is a small, contained change:

  * It is registered as an app-wide-DISABLED export (reports.DISABLED_EXPORT_SUBDIRS),
    so the picker shows it greyed/unpickable and the start_* guards reject it.
  * The per-route behavior (wait_js / is_empty / save) is a PLACEHOLDER — the real
    report schema is unknown until the site turns it on. `save` raises so that
    enabling the report WITHOUT finalizing this spec fails loudly here, rather than
    silently exporting a wrong file.

`data_value` matches the site's #customReport dropdown id ("highway_summary").
"""
import sys

from common import EXPORT_READY_JS
from exporter import ReportSpec


def _save_not_implemented(page, out_path, timeout_ms=None):
    raise NotImplementedError(
        "Highway Summary export is reserved groundwork — its save behavior isn't "
        "finalized yet. Implement it before enabling the report.")


SPEC = ReportSpec(
    label="Highway Summary",
    subdir="highway_summary",
    data_value="highway_summary",         # site dropdown id (the coming TSAR report)
    filename=lambda route: f"highway_summary_route_{route}.xlsx",
    # PLACEHOLDER — finalized when the site enables the report. The report is
    # DISABLED, so the engine never runs this; `save` raises if it somehow does.
    wait_js=lambda route: (
        "() => { const t = document.body.innerText; "
        f"return ({EXPORT_READY_JS}) "
        "|| /No results found/i.test(t); }"
    ),
    is_empty=lambda page: "No results found" in page.inner_text("body"),
    save=_save_not_implemented,
)

if __name__ == "__main__":
    print("Highway Summary is reserved groundwork and is not available yet.")
    sys.exit(1)
