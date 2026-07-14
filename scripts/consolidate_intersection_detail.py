"""Consolidate Intersection Detail XLSX files into a single workbook.

Reads every XLSX in   output/<date>/intersection_detail/   (newest day by default)
Writes one workbook in output/<date>/consolidated/tsar_intersection_detail_consolidated.xlsx
with a leading "Route" column added so rows from different routes are
distinguishable in the combined file.

Thin wrapper over consolidate_xlsx_base — Intersection Detail is the same "one
sheet, header row + data rows" shape as Ramp Detail / Highway Sequence / Highway
Log (36 columns; sheet "Intersection Detail"). The shared core already guards
formula injection on the free-text Description column, so no special handling is
needed here. (v0.17.0 — first Intersection consolidator.)

Console-free: consolidate(events, confirm_overwrite, day=None) returns a
ConsolidateResult and never prints/prompts/exits, so the GUI can drive it.
"""
from consolidate_xlsx_base import consolidate_xlsx
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

SUBDIR = "intersection_detail"
FILENAME = "tsar_intersection_detail_consolidated.xlsx"

# Legacy flat-layout locations (pre-dated exports); used when no dated
# output/<YYYY-MM-DD>/ folders exist.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
OUT_DIR = OUTPUT_ROOT / "consolidated"
OUT_PATH = OUT_DIR / FILENAME

# Sheet name produced by the TSMIS export — must match exactly.
SHEET_NAME = "Intersection Detail"

REPORT_NAME = "Intersection Detail"


def input_dir_for(day):
    """Per-route exports for `day` (a run-folder name); None = the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """Consolidated workbook destination for `day` (a run-folder name); None = the
    legacy location. The filename carries the run's date + source/environment so a
    copy lifted out of its folder keeps its provenance."""
    if not day:
        return OUT_PATH
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(FILENAME, day)


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, commit_guard=None):
    """Combine every per-route Intersection Detail XLSX into one workbook.

    `day` picks which export run folder ("<YYYY-MM-DD> <src>-<env>") to read; None means
    the newest run folder, falling back to the legacy flat layout when no run
    folders exist yet."""
    day = day or latest_output_day()
    return consolidate_xlsx(
        input_dir=input_dir or input_dir_for(day),
        out_path=out_path or out_path_for(day),
        sheet_name=SHEET_NAME, report_name=REPORT_NAME,
        title="Intersection Detail Consolidation",
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
    )


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
