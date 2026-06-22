"""Convert TSMIS Intersection Detail PDFs into TSMIS-format Excel and combine.

The TSMIS "Intersection Detail (PDF)" export (report 6b — the site's Print layout
saved via `page.pdf()`) renders the report as a real, BORDERED HTML table. Just
like Highway Log, the PDF and the vendor Excel export can DISAGREE on data, so
this consolidator parses those per-route PDFs into the SAME 36-column TSMIS
Intersection Detail format the Excel export and the TSN consolidator produce, so:
  * the combined workbook lines up column-for-column with the consolidated TSN
    Intersection Detail (for the TSMIS-PDF vs TSN comparison), and
  * it can be diffed against the vendor Excel export to pinpoint exactly which
    cells the two sources disagree on (the TSMIS-PDF vs TSMIS-Excel check).

The inputs ARE this app's own exports: the "Intersection Detail (PDF)" export
saves the per-route PDFs (intersection_detail_route_<ROUTE>.pdf) to
output/<run>/intersection_detail_pdf/, so this consolidator reads that export
folder day-aware, exactly like the Excel consolidator (the "Export day" picker
picks which run to combine) — NOT a separate dropped-in folder. Converts each PDF
to a per-route workbook (scratch, in output/tsmis_intersection_detail_pdf/) and
writes one combined workbook to that run's consolidated/ folder.

PARSING — derived-grid based, like the Highway Log PDF consolidator, but TWO
physical table rows make ONE record. The site's `intd_renderRow` emits each
intersection as
  * rowA — the Post Mile, Location, Date of Record and the INT / CONTROL /
    LIGHTING / MAINLINE attribute cells (21 grid columns); and
  * rowB — a WIDE Description cell (it spans grid columns 3-6) then the Main Line /
    Intersecting / Intersecting-Route / Xing cells (grid columns 7-20).
`intd_renderRow` ZEBRA-SHADES alternate records (`idx % 2 === 0`), and ONLY the
shaded records carry cell rectangles — the un-shaded ones render as borderless
text. So we can't band by rects (that would silently drop every other record).
Instead we derive the table's 21 column x-windows ONCE from the shaded rowA bands
(the print layout is a single table, so column widths are uniform across pages),
then assign EVERY text line's characters to those windows (inserting a space where
the x-gap opens a new token, so "04"+"SOL"+"780" -> "04 SOL 780"). A line whose
Post Mile column holds a number is a rowA; the line after it is its rowB. The
report is FLAT — each row's Location already carries "<district> <county>
<route>", so there are NO centered county group headers (unlike Highway Log), and
the print layout carries no route label, so the route comes from the FILENAME.

No value normalization happens here: the PDF already carries the native TSMIS
formats, so values are written through verbatim. The comparison engine applies any
normalization (e.g. Y/N<->1/0) at compare time, exactly as for the Excel side.

Console-free like the other consolidators: progress via events.on_log, overwrite
confirmed through the callback, cancel honored between pages, ConsolidateResult
returned. The console UX lives in cli.run_consolidate_cli.
"""
import logging
import re
from collections import defaultdict
from pathlib import Path

# pdfplumber wraps pdfminer.six, which can log noisy per-page font warnings;
# parsing is unaffected (see consolidate_tsmis_highway_log_pdf).
logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import pdfplumber
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from compare_core import is_formula_injection   # shared formula-injection guard
from consolidate_xlsx_base import consolidate_xlsx
from events import ConsolidateResult, Events
from intersection_detail_columns import HEADER as INTD_HEADER
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

# These PDFs ARE produced by this app's "Intersection Detail (PDF)" export (report
# 6b), saved to output/<run>/intersection_detail_pdf/. So this consolidator reads
# that EXPORT folder, day-aware, exactly like the Excel consolidator — NOT a
# separate user-dropped input folder. The "Export day" picker picks which run.
SUBDIR = "intersection_detail_pdf"
FILENAME = "tsmis_intersection_detail_pdf_consolidated.xlsx"

# Legacy flat-layout location (pre-dated exports, or a manual drop on a machine
# that can't run the export itself); used when no dated output/<run>/ folders exist.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
CONVERTED_DIR = OUTPUT_ROOT / "tsmis_intersection_detail_pdf"  # scratch per-route wb
OUT_PATH = OUTPUT_ROOT / FILENAME                              # legacy flat output

# Friendly report name for user-facing messages (UI-neutral).
REPORT_NAME = "TSMIS Intersection Detail (PDF)"

# File pattern the GUI uses to preview how many inputs a folder holds.
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"

# Must match the Intersection Detail export exactly (sheet name AND header), so the
# converted files consolidate with the same core and the combined workbook is
# column-compatible with the consolidated TSN Intersection Detail and the Excel
# export.
SHEET_NAME = "Intersection Detail"


def input_dir_for(day):
    """The 'Intersection Detail (PDF)' export PDFs for `day` (a run-folder name);
    None = the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """Combined workbook destination for `day` (a run-folder name); None = the
    legacy location. The dated filename carries the run's date + source/environment
    so a copy lifted out of its folder keeps its provenance."""
    if not day:
        return OUT_PATH
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(FILENAME, day)


# =============================================================================
# PDF layout
# =============================================================================

N_COLS = 21              # the 21-column grid (rowA's cells; rowB maps onto it too)
CELL_MIN_W = 3           # ignore hairline / spacer rects when finding shaded bands
CELL_MIN_H = 3
CELL_MAX_H = 40          # a data cell is one text line tall
Y_TOLERANCE = 3          # chars within this y-distance form one logical line
WORD_GAP = 1.5           # x-gap that opens a new token inside one column

# A data rowA's Location cell is "<district> <county> <route>", e.g. "04 SOL 780"
# or the period-bearing county codes "04 CC. 004" / "10 SJ. 120". This guards the
# rowA classification against any stray non-data line and is cheap to evaluate.
LOCATION_RE = re.compile(r"\d{2}\s+[A-Z]")
# Route token out of "intersection_detail_route_<ROUTE>.pdf".
ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]?)", re.IGNORECASE)


def _norm_route(token):
    """'4' -> '004' (TSMIS zero-pads to 3 digits); suffixed routes ('101U',
    '010S') keep their letter, upper-cased."""
    m = re.fullmatch(r"(\d+)([A-Za-z]?)", token)
    if not m:
        return token.upper()
    return f"{int(m.group(1)):03d}{m.group(2).upper()}"


def _cluster_lines(page):
    """Cluster the page's non-space characters into logical lines (tolerating the
    small baseline jitter of a row). Returns [(top, [chars sorted by x0]), ...]."""
    clusters = []                     # [(anchor_top, [char, ...]), ...]
    for c in sorted(page.chars, key=lambda c: (c["top"], c["x0"])):
        if not c["text"].strip():
            continue
        if clusters and abs(c["top"] - clusters[-1][0]) <= Y_TOLERANCE:
            clusters[-1][1].append(c)
        else:
            clusters.append((c["top"], [c]))
    return [(top, sorted(chars, key=lambda c: c["x0"])) for top, chars in clusters]


def _shaded_column_windows(pdf):
    """Derive the 21 contiguous column windows from the document's zebra-shaded
    rowA cell rects.

    Only the shaded (even-index) records carry rects, but the print layout is ONE
    table, so its column widths are uniform across every page and row — the median
    cell edges of the shaded rowA bands therefore give the grid for EVERY line,
    shaded or not. The windows are made CONTIGUOUS (each boundary is the midpoint
    between adjacent cells; the ends extend to ±infinity) so no character can fall
    between two columns and be dropped. Returns the 21 (lo, hi) windows, or None if
    no full rowA band was found anywhere (an empty / unreadable PDF)."""
    bands = []
    for page in pdf.pages:
        by_top = defaultdict(list)
        for r in page.rects:
            w = r["x1"] - r["x0"]
            h = r["bottom"] - r["top"]
            if CELL_MIN_W < w < page.width - 10 and CELL_MIN_H < h < CELL_MAX_H:
                by_top[round(r["top"])].append(r)
        for cells in by_top.values():
            if len(cells) == N_COLS:
                bands.append(sorted(cells, key=lambda r: r["x0"]))
    if not bands:
        return None

    def median(values):
        s = sorted(values)
        return s[len(s) // 2]

    lo = [median([b[i]["x0"] for b in bands]) for i in range(N_COLS)]
    hi = [median([b[i]["x1"] for b in bands]) for i in range(N_COLS)]
    windows = []
    for i in range(N_COLS):
        a = float("-inf") if i == 0 else (hi[i - 1] + lo[i]) / 2
        b = float("inf") if i == N_COLS - 1 else (hi[i] + lo[i + 1]) / 2
        windows.append((a, b))
    return windows


def _rowb_windows(windows):
    """rowB's 18 windows from the 21-column grid: columns 0,1,2 as-is, then ONE
    merged Description window spanning grid columns 3-6, then columns 7..20 as-is.

    The Description is a single wide cell in the table (it spans four grid columns),
    so assigning it as one window lets WORD_GAP spacing flow continuously across it
    — otherwise a word straddling a grid-column boundary ('ARCH' -> 'ARC' + 'H')
    would be rejoined with a false space."""
    desc = (windows[3][0], windows[6][1])
    return windows[0:3] + [desc] + windows[7:21]


def _assign_columns(chars, windows):
    """Map each character of a line to its column by horizontal center, inserting a
    space inside a column where the x-gap >= WORD_GAP opens a new token (so
    '04'/'SOL'/'780' -> '04 SOL 780' and 'LEMON'/'ST' -> 'LEMON ST')."""
    vals = ["" for _ in windows]
    last_x1 = [None] * len(windows)
    for c in chars:                   # x-sorted by _cluster_lines
        center = (c["x0"] + c["x1"]) / 2
        for i, (lo, hi) in enumerate(windows):
            if lo <= center < hi:
                if vals[i] and c["x0"] - last_x1[i] >= WORD_GAP:
                    vals[i] += " "
                vals[i] += c["text"]
                last_x1[i] = c["x1"]
                break
    return [v.strip() for v in vals]


def _is_rowA(vals):
    """A record's FIRST line (rowA) carries the Post Mile (column 1) — a number;
    its second line (rowB) leaves columns 0-2 blank. So a numeric column 1 marks a
    rowA. Header furniture ("POST MILE", "DATE OF RECORD", …) has no digit there."""
    return any(ch.isdigit() for ch in vals[1])


def _make_row(a, b):
    """Assemble the 36-column Intersection Detail row from rowA's 21 grid values
    and rowB's 18 merged-window values (see _rowb_windows).

    rowA columns 0..20 map 1:1 to output columns 0..20 (P .. ML Eff-Date). rowB
    carries the Description (its merged window 3) then the Main Line / Intersecting
    fields (windows 4..17 -> grid columns 7..20). The Excel export emits the
    intersecting-route pair as 'Intrte S' THEN 'Intrte Route' — the REVERSE of their
    left-to-right order in the PDF — so rowB window 13 (Intrte S, grid col 16) -> col
    30 and window 12 (Intrte Route, grid col 15) -> col 31, keeping the two sources
    column-compatible."""
    a = [v or None for v in a]
    b = [v or None for v in b]
    return [
        *a[0:21],   # 0..20  P, Post Mile, S, Location, Date of Record, … ML Eff-Date
        b[3],       # 21 Description    (rowB merged window, grid cols 3-6)
        b[4],       # 22 Main Line Lgth
        b[5],       # 23 Inter Eff-Date
        b[6],       # 24 Inter S
        b[7],       # 25 Inter L
        b[8],       # 26 Inter R
        b[9],       # 27 Inter T
        b[10],      # 28 Inter N
        b[11],      # 29 Int St Eff-Date
        b[13],      # 30 Intrte S       (rowB window 13 = grid col 16; Excel lists S first)
        b[12],      # 31 Intrte Route   (rowB window 12 = grid col 15)
        b[14],      # 32 Intrte Post
        b[15],      # 33 Intrte Mile
        b[16],      # 34 Xing Rte
        b[17],      # 35 Xing S
    ]


def parse_pdf(path, events):
    """Parse one TSMIS Intersection Detail PDF into 36-column TSMIS-format rows.

    Returns (rows, stats): `rows` a list of 36-column row lists in document order,
    `stats` a reconciliation dict (emitted, pages, orphans = a rowA that never got
    its rowB — should be 0; `no_grid` when the column geometry couldn't be derived).
    Returns (None, None) if cancelled.

    Only the zebra-shaded records carry cell rects, so the 21-column grid is derived
    once from those shaded bands (the report is one table, so its widths are uniform)
    and EVERY text line is then placed on that grid — the un-shaded records included.
    A line whose Post Mile column holds a number is a rowA; the line right after it
    is its rowB. The pairing is carried across page boundaries defensively, so a
    future layout change that splits a record surfaces as an orphan, never a silent
    drop."""
    rows = []
    pending_a = None            # a rowA (21 grid vals) awaiting its rowB
    orphans = 0
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        windows = _shaded_column_windows(pdf)
        if windows is None:
            return [], {"emitted": 0, "pages": n_pages, "orphans": 0, "no_grid": True}
        rowb_windows = _rowb_windows(windows)
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            for _top, chars in _cluster_lines(page):
                vals = _assign_columns(chars, windows)
                if _is_rowA(vals):
                    if not LOCATION_RE.search(vals[3] or ""):
                        continue            # a non-data line (no real Location)
                    if pending_a is not None:
                        orphans += 1        # previous rowA never got its rowB
                    pending_a = vals
                elif pending_a is not None:
                    # rowB: re-read with the merged Description window so a word that
                    # straddles a grid-column boundary isn't split by a false space.
                    rows.append(_make_row(pending_a, _assign_columns(chars, rowb_windows)))
                    pending_a = None
    if pending_a is not None:
        orphans += 1
    return rows, {"emitted": len(rows), "pages": n_pages, "orphans": orphans}


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Intersection Detail workbook (same
    sheet name + 36 columns the Excel export uses)."""
    header_fill = PatternFill("solid", start_color="305496")
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(INTD_HEADER)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
    ws.freeze_panes = "A2"
    for i, name in enumerate(INTD_HEADER, start=1):
        ws.column_dimensions[get_column_letter(i)].width = \
            40 if name == "Description" else 12

    for row in rows:
        ws.append(row)
        # Neutralize any formula-looking text (e.g. a Description starting with "=")
        # so it can't execute when the workbook is opened.
        for cell in ws[ws.max_row]:
            if is_formula_injection(cell.value):
                cell.data_type = "s"
    wb.save(out_path)


# =============================================================================
# Entry point
# =============================================================================

def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None):
    """Convert every TSMIS Intersection Detail PDF to a TSMIS-format per-route
    workbook, then combine them into one workbook (Route column added).

    `day` picks which export run folder of "Intersection Detail (PDF)" exports to
    read; None means the newest run folder, falling back to the legacy flat layout.
    Console-free; honors events.is_cancelled() between pages.
    """
    day = day or latest_output_day()
    in_dir = Path(input_dir) if input_dir else input_dir_for(day)
    out = Path(out_path) if out_path else out_path_for(day)
    conv = Path(converted_dir) if converted_dir else CONVERTED_DIR
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(
            status="error",
            message="Required components are missing (pdfplumber, openpyxl).",
        )
    confirm = confirm_overwrite or (lambda _p: True)

    try:
        in_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    pdfs = sorted(in_dir.glob("*.pdf"))
    if not pdfs:
        return ConsolidateResult(
            status="error",
            message=(f"No {REPORT_NAME} files were found in:\n{in_dir}\n\n"
                     f"Export the 'Intersection Detail (PDF)' report first (it saves "
                     f"the per-route PDFs there), then run this again."),
        )

    if out.exists() and not confirm(out):
        return ConsolidateResult(status="cancelled",
                                 message="Cancelled. Existing file kept.")

    events.on_log("=" * 60)
    events.on_log(f"TSMIS Intersection Detail (PDF) Conversion - {len(pdfs)} route PDF(s)")
    events.on_log("=" * 60)
    events.on_log("")

    # The combined workbook reflects exactly THIS run's PDFs: clear previously
    # converted files so routes removed from the input folder don't linger.
    conv.mkdir(parents=True, exist_ok=True)
    stale = list(conv.glob("tsmis_intersection_detail_pdf_*.xlsx"))
    for p in stale:
        try:
            p.unlink()
        except OSError:
            return ConsolidateResult(
                status="error",
                message=(f"Could not replace {p.name}.\n\n"
                         "The file is probably open in Excel. Close it and try again."),
            )
    if stale:
        events.on_log(f"Cleared {len(stale)} previously converted file(s).")

    converted = 0
    total_rows = 0
    total_orphans = 0
    failed = []
    written = set()
    for i, p in enumerate(pdfs, 1):
        if events.is_cancelled():
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        prefix = f"[{i}/{len(pdfs)}] {p.name}"
        events.on_log(f"{prefix} parsing…")
        name_m = ROUTE_FROM_NAME.search(p.stem)
        route = _norm_route(name_m.group(1)) if name_m else None
        if not route:
            events.on_log(f"{prefix} no route in filename; skipping")
            failed.append(p.name)
            continue
        try:
            rows, pstats = parse_pdf(str(p), events)
        except Exception as e:                       # noqa: BLE001
            events.on_log(f"{prefix} FAILED ({type(e).__name__}): {e}")
            failed.append(p.name)
            continue
        if rows is None:                             # cancelled mid-PDF
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        if pstats:
            total_orphans += pstats["orphans"]
            if pstats["orphans"]:
                events.on_log(f"  WARNING: {pstats['orphans']} unpaired row(s) in {p.name} "
                              "(a record's two lines didn't pair) — see the log.")
        if not rows:
            events.on_log(f"{prefix} no intersection data found; skipping")
            failed.append(p.name)
            continue
        out_file = conv / f"tsmis_intersection_detail_pdf_route_{route}.xlsx"
        if out_file.name in written:
            events.on_log(f"  WARNING: route {route} already converted from an earlier "
                          f"PDF; {p.name} replaces it.")
        written.add(out_file.name)
        try:
            _write_route_workbook(rows, out_file)
        except PermissionError:
            return ConsolidateResult(
                status="error",
                message=(f"Could not save {out_file.name}.\n\n"
                         "The file is probably open in Excel. Close it and try again."),
            )
        events.on_log(f"  route {route}: {len(rows)} rows -> {out_file.name}")
        converted += 1
        total_rows += len(rows)

    if converted == 0:
        return ConsolidateResult(
            status="error",
            message=(f"None of the PDFs in:\n{in_dir}\n\ncontained readable "
                     f"{REPORT_NAME} data. Are they the TSMIS Intersection Detail PDFs "
                     "(the 'Intersection Detail (PDF)' export)?"),
        )

    events.on_log("")

    result = consolidate_xlsx(
        input_dir=conv, out_path=out, sheet_name=SHEET_NAME,
        report_name=REPORT_NAME, title="TSMIS Intersection Detail (PDF) Consolidation",
        events=events, confirm_overwrite=lambda _p: True,
    )
    if result.status == "ok":
        notes = []
        if total_orphans:
            notes.append(f"⚠ {total_orphans} unpaired row line(s) — verify (see the log).")
        result.summary_lines = notes + [
            f"Route PDFs:   {len(pdfs) - len(failed)} converted"
            + (f", {len(failed)} failed {failed}" if failed else ""),
            f"Route files:  {converted} (in {conv})",
        ] + result.summary_lines
    return result


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
