"""Consolidate TSAR: Ramp Detail XLSX files into a single workbook.

Reads every XLSX in   output/<date>/ramp_detail/   (newest day by default)
Writes one workbook in output/<date>/consolidated/tsar_ramp_detail_consolidated.xlsx
with a leading "Route" column added so rows from different routes are
distinguishable in the combined file.

Thin wrapper over consolidate_xlsx_base, which is shared with Highway Sequence
and Highway Log -- all three are "one sheet, header row + data rows" exports that
differ only by input folder, sheet name, and output name. (The Ramp Summary
consolidator stays standalone because it parses PDFs, not XLSX.)

Importable (Phase 3b): consolidate(events, confirm_overwrite, day=None) returns
a ConsolidateResult and never prints/prompts/exits, so the GUI can drive it. The
console UX lives in cli.run_consolidate_cli, used by the __main__ entry (and
therefore by "4. consolidate (combine reports).bat").
"""
from consolidate_xlsx_base import consolidate_xlsx
from paths import OUTPUT_ROOT, latest_output_day, output_day_dir

SUBDIR = "ramp_detail"
FILENAME = "tsar_ramp_detail_consolidated.xlsx"

# Legacy flat-layout locations (pre-dated exports); still used when no dated
# output/<YYYY-MM-DD>/ folders exist, so old exports stay consolidatable.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
OUT_DIR = OUTPUT_ROOT / "consolidated"
OUT_PATH = OUT_DIR / FILENAME

# Sheet name produced by the TSMIS export — must match exactly.
SHEET_NAME = "TSAR - Ramp Detail"

# Friendly report name for user-facing messages (shown in both the GUI and the
# console, so keep it UI-neutral -- no ".bat" / "menu option" wording).
REPORT_NAME = "Ramp Detail"


def input_dir_for(day):
    """Per-route exports for `day` (YYYY-MM-DD); None = the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """Consolidated workbook destination for `day`; None = the legacy location."""
    return (output_day_dir(day) / "consolidated" / FILENAME) if day else OUT_PATH


def consolidate(events=None, confirm_overwrite=None, day=None):
    """Combine every per-route Ramp Detail XLSX into one workbook.

    `day` picks which dated export folder (YYYY-MM-DD) to read; None means the
    newest dated folder, falling back to the legacy flat layout when no dated
    folders exist yet."""
    day = day or latest_output_day()
    return consolidate_xlsx(
        input_dir=input_dir_for(day), out_path=out_path_for(day),
        sheet_name=SHEET_NAME, report_name=REPORT_NAME,
        title="TSAR Ramp Detail Consolidation",
        events=events, confirm_overwrite=confirm_overwrite,
    )


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
