"""Write a per-route run report for an export.

The route outcomes (saved / empty / skipped / failed / already-had) are a
useful data point on their own -- which routes need another pass, which are
legitimately empty, failure patterns over time. This writes them as a simple
CSV (opens in Excel, easy to aggregate across runs). Console-free; used by both
the engine (auto-save after each run) and the GUI ("Save run report...").
"""
import csv
import time
from pathlib import Path

from paths import OUTPUT_ROOT
from site_target import HOST_LABELS, host_kind

# Auto-saved reports land here (one timestamped CSV per run). Under output/, so
# it's discoverable next to the exports and already git-ignored.
RUN_REPORTS_DIR = OUTPUT_ROOT / "run_reports"

# Friendly labels for the raw per-route status codes.
FRIENDLY_STATUS = {
    "saved":   "Saved",
    "empty":   "No data",
    "skipped": "Skipped",
    "failed":  "Failed",
    "exists":  "Already had",
}


def auto_report_path(subdir, site_tag=None):
    """Default timestamped path for the auto-saved report of one report type.
    `site_tag` (e.g. "ssor-prod_dev-site", see `report_site_tag`) marks which data
    source / environment and which TSMIS host the run hit, so reports from
    different sites stay distinguishable."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    tag = f"_{site_tag}" if site_tag else ""
    return RUN_REPORTS_DIR / f"{subdir}{tag}_run_{stamp}.csv"


def report_site_tag(src, env, site_url):
    """The run report's filename tag for one export: '<src>-<env>_<host>-site'
    ('ssor-prod_dev-site'), the host read from the address the run opened."""
    return f"{src}-{env}_{host_kind(site_url)}-site"


def write_run_report(result, label, path, site_url=None):
    """Write `result.per_route` to `path` as CSV. Returns the Path written.
    `site_url` (the report-page address the export opened) fills a Site column,
    so the report says which TSMIS site — main or dev — every route came from."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    run_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Report", "Route", "Status", "Run At"]
                        + (["Site"] if site_url else []))
        site = [_site_text(site_url)] if site_url else []
        for route, status in result.per_route:
            writer.writerow([label, route, FRIENDLY_STATUS.get(status, status), run_at]
                            + site)
    return path


def _site_text(site_url):
    """'dev site: https://tsmis-dev.dot.ca.gov/index.html?env=prod&src=ssor'
    (plain ASCII around the address: Excel opens a BOM-less UTF-8 CSV as ANSI)."""
    return f"{HOST_LABELS[host_kind(site_url)]}: {site_url}"


def write_run_report_multi(results_by_label, path):
    """Write per-route rows for SEVERAL reports to one CSV (used when the GUI
    exports several report types at once and the user saves a combined report).

    results_by_label is a list of (label, RunResult). The `Report` column keeps
    the rows distinguishable. Returns the Path written.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    run_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Report", "Route", "Status", "Run At"])
        for label, result in results_by_label:
            for route, status in result.per_route:
                writer.writerow([label, route, FRIENDLY_STATUS.get(status, status), run_at])
    return path
