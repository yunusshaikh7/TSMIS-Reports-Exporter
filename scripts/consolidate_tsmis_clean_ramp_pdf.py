"""Convert the site's Clean Road Ramp prints into the Excel export's layout
and combine them.

Reads every per-route print in   output/<run>/clean_ramp_pdf/   (the newest
run by default; the "Clean Road: Ramp (PDF)" export). Each print is read
back by `clean_road_print` into the Excel export's exact columns (the print
leaves out the columns the site has no source for; they stay blank here, as
they are in the Excel file), written as a per-route workbook in a scratch
folder, and combined into one workbook in the run's consolidated/ folder. The
result carries the PDF-conversion marker, so the PDF-vs-Excel self-check can
prove which side is which. Console-free.
"""
import clean_road_columns as crc
import clean_road_consolidate as crcon
from paths import OUTPUT_ROOT

SPEC = crc.RAMP
SUBDIR = SPEC.pdf_key
FILENAME = crcon.pdf_filename(SPEC)
SHEET_NAME = SPEC.sheet
REPORT_NAME = f"TSMIS {SPEC.label} (PDF)"
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"

INPUT_DIR = OUTPUT_ROOT / SUBDIR
CONVERTED_DIR = OUTPUT_ROOT / f"tsmis_{SUBDIR}"      # scratch per-route workbooks
OUT_PATH = OUTPUT_ROOT / FILENAME                     # legacy flat output


def input_dir_for(day):
    """The print exports for `day` (a run-folder name); None = the legacy flat layout."""
    return crcon.input_dir_for(SUBDIR, day)


def out_path_for(day):
    """The combined workbook for `day`; None = the legacy location."""
    return crcon.out_path_for(FILENAME, day, OUT_PATH)


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Read every per-route Clean Road Ramp print and combine them into one
    workbook (Route column added). Console-free; returns a ConsolidateResult."""
    return crcon.consolidate_pdf(
        SPEC, events=events, confirm_overwrite=confirm_overwrite, day=day,
        input_dir=input_dir, out_path=out_path, converted_dir=converted_dir,
        commit_guard=commit_guard, report_name=REPORT_NAME,
        legacy_out=OUT_PATH, legacy_converted=CONVERTED_DIR)


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
