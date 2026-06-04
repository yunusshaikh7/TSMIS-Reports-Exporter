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


def auto_report_path(subdir):
    """Default timestamped path for the auto-saved report of one report type."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return RUN_REPORTS_DIR / f"{subdir}_run_{stamp}.csv"


def write_run_report(result, label, path):
    """Write `result.per_route` to `path` as CSV. Returns the Path written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    run_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Report", "Route", "Status", "Run At"])
        for route, status in result.per_route:
            writer.writerow([label, route, FRIENDLY_STATUS.get(status, status), run_at])
    return path
