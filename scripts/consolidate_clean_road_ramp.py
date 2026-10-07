"""Consolidate the site's Clean Road Ramp Excel exports into one workbook.

Reads every per-route export in   output/<run>/clean_ramp/   (the newest run
by default) and writes one workbook to that run's consolidated/ folder: the
export's own sheet ("Clean Road Ramp") with a leading "Route" column, then the
export's exact columns. The shared glue (and the print sibling) lives in
`clean_road_consolidate`; the column contract in `clean_road_columns`.

This is the SITE's export. The app's own ArcGIS-built table is a different
thing (`consolidate_clean_highway`, the ArcGIS tab). Console-free.
"""
import clean_road_columns as crc
import clean_road_consolidate as crcon
from paths import OUTPUT_ROOT

SPEC = crc.RAMP
SUBDIR = SPEC.key
FILENAME = crcon.excel_filename(SPEC)
SHEET_NAME = SPEC.sheet
REPORT_NAME = SPEC.label
INPUT_FMT = "Excel"

INPUT_DIR = OUTPUT_ROOT / SUBDIR
OUT_DIR = OUTPUT_ROOT / "consolidated"
OUT_PATH = OUT_DIR / FILENAME


def input_dir_for(day):
    """Per-route exports for `day` (a run-folder name); None = the legacy flat layout."""
    return crcon.input_dir_for(SUBDIR, day)


def out_path_for(day):
    """The consolidated workbook for `day`; None = the legacy location."""
    return crcon.out_path_for(FILENAME, day, OUT_PATH)


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, commit_guard=None):
    """Combine every per-route Clean Road Ramp Excel export into one workbook.
    Console-free; returns a ConsolidateResult."""
    return crcon.consolidate_excel(
        SPEC, events=events, confirm_overwrite=confirm_overwrite, day=day,
        input_dir=input_dir, out_path=out_path, commit_guard=commit_guard,
        report_name=REPORT_NAME, legacy_out=OUT_PATH)


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
