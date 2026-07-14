"""Consolidate Highway Detail XLSX files into a single workbook.

Reads every XLSX in   output/<date>/highway_detail/   (newest day by default)
Writes one workbook in output/<date>/consolidated/highway_detail_consolidated.xlsx
with a leading "Route" column added so rows from different routes are
distinguishable in the combined file.

Thin wrapper over consolidate_xlsx_base (the Highway Log / Ramp Detail /
Highway Sequence pattern). The export's own 34 column labels are CORRECT
(unlike the Highway Log's), so no header override is needed — the combined
workbook keeps them and adds the legend meanings as hover tooltips plus a
Legend sheet (from highway_detail_columns, the labels' one home).

Importable: consolidate(events, confirm_overwrite, day=None) returns a
ConsolidateResult and never prints/prompts/exits, so the GUI can drive it. The
console UX lives in cli.run_consolidate_cli, used by the __main__ entry.
"""
import highway_detail_columns as hdc            # the column labels + legend
from consolidate_xlsx_base import consolidate_xlsx
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

SUBDIR = "highway_detail"
FILENAME = "highway_detail_consolidated.xlsx"

# Legacy flat-layout locations (pre-dated exports); still used when no dated
# output/<YYYY-MM-DD>/ folders exist, so old exports stay consolidatable.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
OUT_DIR = OUTPUT_ROOT / "consolidated"
OUT_PATH = OUT_DIR / FILENAME

# Sheet name produced by the TSMIS export — must match exactly.
SHEET_NAME = "Highway Detail"

# Friendly report name for user-facing messages (UI-neutral).
REPORT_NAME = "Highway Detail"

# Input format badge in the Consolidate list.
INPUT_FMT = "Excel"


def input_dir_for(day):
    """Per-route exports for `day` (a run-folder name); None = the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """Consolidated workbook destination for `day` (a run-folder name); None = the
    legacy location. The filename carries the run's date + source/environment (A1)
    so a copy lifted out of its folder keeps its provenance."""
    if not day:
        return OUT_PATH
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(FILENAME, day)


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, commit_guard=None):
    """Combine every per-route Highway Detail XLSX into one workbook.

    `day` picks which export run folder ("<YYYY-MM-DD> <src>-<env>") to read;
    None means the newest run folder, falling back to the legacy flat layout
    when no run folders exist yet."""
    day = day or latest_output_day()
    return consolidate_xlsx(
        input_dir=input_dir or input_dir_for(day),
        out_path=out_path or out_path_for(day),
        sheet_name=SHEET_NAME, report_name=REPORT_NAME,
        title="Highway Detail Consolidation",
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        # The export labels are already correct; add the legend meanings as
        # hover tooltips + a Legend sheet.
        header_comment=hdc.comment_for,
        decorate_workbook=hdc.write_legend_sheet,
    )


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
