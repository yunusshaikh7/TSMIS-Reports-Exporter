"""Consolidate Highway Log XLSX files into a single workbook.

Reads every XLSX in   output/<date>/highway_log/   (newest day by default)
Writes one workbook in output/<date>/consolidated/highway_log_consolidated.xlsx
with a leading "Route" column added so rows from different routes are
distinguishable in the combined file.

Thin wrapper over consolidate_xlsx_base, which is shared with Ramp Detail and
Highway Sequence -- all three are "one sheet, header row + data rows" exports
that differ only by input folder, sheet name, and output name. (The Ramp Summary
consolidator stays standalone because it parses PDFs, not XLSX.)

Importable: consolidate(events, confirm_overwrite, day=None) returns a
ConsolidateResult and never prints/prompts/exits, so the GUI can drive it. The
console UX lives in cli.run_consolidate_cli, used by the __main__ entry (and
therefore by "4. consolidate (combine reports).bat").
"""
import highway_log_columns as hlc               # the corrected column labels
from consolidate_xlsx_base import consolidate_xlsx
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

SUBDIR = "highway_log"
FILENAME = "highway_log_consolidated.xlsx"

# Legacy flat-layout locations (pre-dated exports); still used when no dated
# output/<YYYY-MM-DD>/ folders exist, so old exports stay consolidatable.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
OUT_DIR = OUTPUT_ROOT / "consolidated"
OUT_PATH = OUT_DIR / FILENAME

# Sheet name produced by the TSMIS export — must match exactly.
SHEET_NAME = "Highway Log"

# Friendly report name for user-facing messages (shown in both the GUI and the
# console, so keep it UI-neutral -- no ".bat" / "menu option" wording).
REPORT_NAME = "Highway Log"

# Input format badge in the Consolidate list. Set explicitly (this reads the TSMIS
# Excel export) so the chip is correct regardless of the GUI menu label.
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
    """Combine every per-route Highway Log XLSX into one workbook.

    `day` picks which export run folder ("<YYYY-MM-DD> <src>-<env>") to read; None means
    the newest run folder, falling back to the legacy flat layout when no run
    folders exist yet."""
    day = day or latest_output_day()
    return consolidate_xlsx(
        input_dir=input_dir or input_dir_for(day),
        out_path=out_path or out_path_for(day),
        sheet_name=SHEET_NAME, report_name=REPORT_NAME,
        title="Highway Log Consolidation",
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        # Ship the CORRECTED column labels even though the vendor Excel header is
        # wrong: relabel by position, add hover tooltips + a Legend sheet.
        header_override=hlc.HEADER, header_comment=hlc.comment_for,
        decorate_workbook=hlc.write_legend_sheet,
    )


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
