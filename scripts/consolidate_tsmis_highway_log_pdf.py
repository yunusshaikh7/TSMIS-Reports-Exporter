"""Convert TSMIS Highway Log PDFs into TSMIS-format Excel and combine.

The TSMIS "Highway Log (PDF)" export (the site's Print layout saved via
`page.pdf()`, report 4b) renders the report as a real, BORDERED HTML table —
unlike the vendor's Excel export, which has a data-integrity bug. This
consolidator parses those per-route PDFs into the SAME 31-column TSMIS Highway
Log format the Excel export and the TSN consolidator produce, so:
  * the combined workbook lines up column-for-column with the consolidated TSN
    Highway Log (for the TSMIS-PDF vs TSN comparison), and
  * it can be diffed against the (buggy) vendor Excel export to pinpoint exactly
    which cells the Excel export is getting wrong.

The inputs ARE this app's own exports: the "Highway Log (PDF)" export (report 4b)
saves the per-route PDFs (highway_log_route_<ROUTE>.pdf) to
output/<run>/highway_log_pdf/, so this consolidator reads that export folder
day-aware, exactly like the Excel Highway Log consolidator (the "Export day"
picker picks which run to combine) — NOT a separate dropped-in folder. Converts
each PDF to a per-route workbook (scratch, in output/tsmis_highway_log_pdf/) and
writes one combined workbook to that run's consolidated/ folder. Each PDF is ONE
route; a route
crosses several counties, each introduced by a centered
"<district> <county> <route>" group header (county is a section marker only —
the 31-column layout has no County column, exactly like the TSN/Excel forms).

PARSING — cell-rect based, NOT character windows. The print view is a genuine
HTML table, so every data row's 30 columns are PRESENT IN THE PDF AS CELL
RECTANGLES. The table is auto-laid-out: column x-boundaries DIFFER from page to
page, and routes render landscape OR portrait (a short spur is portrait). We
therefore derive each page's 30 column boundaries from THAT page's zebra-shaded
data-row cells (only the shaded rows carry rects, so a page's boundaries come
from its shaded bands and apply to every row on the page), make them contiguous
(no character can fall between two windows and be lost), and assign every data
character to the column whose horizontal window contains its center. The 30
cells map 1:1, in document order, to the 31-column TSMIS layout MINUS Description
— which TSMIS (like TSN) prints as separate lines BELOW the data row.

Unlike the TSN converter, NO value normalization happens here: the PDF already
carries the native TSMIS number formats (MI is "000.045", widths are "12"), so
values are written through verbatim. The comparison engine applies the Med Wid
zero-pad rule at compare time.

Console-free like the other consolidators: progress via events.on_log, overwrite
confirmed through the callback, cancel honored between pages, ConsolidateResult
returned. The console UX lives in cli.run_consolidate_cli.
"""
import logging
import re
from collections import defaultdict
from pathlib import Path

# pdfplumber wraps pdfminer.six, which can log noisy per-page font warnings;
# parsing is unaffected (see consolidate_tsn_highway_log / consolidate_ramp_summary).
logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import pdfplumber
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import highway_log_columns as hlc               # the corrected column labels
from compare_core import is_formula_injection   # shared formula-injection guard
from consolidate_xlsx_base import consolidate_xlsx
from events import ConsolidateResult, Events
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

# These PDFs ARE produced by this app's "Highway Log (PDF)" export (report 4b),
# which saves them to output/<run>/highway_log_pdf/. So this consolidator reads
# that EXPORT folder, day-aware, exactly like the Excel Highway Log consolidator —
# NOT a separate user-dropped input folder, which would be redundant (you'd have
# to copy the app's own exports into it). The "Export day" picker therefore DOES
# apply: it picks which export run to combine.
SUBDIR = "highway_log_pdf"
FILENAME = "tsmis_highway_log_pdf_consolidated.xlsx"

# Legacy flat-layout location (pre-dated exports, or a manual drop on a machine
# that can't run the export itself); used when no dated output/<run>/ folders exist.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
CONVERTED_DIR = OUTPUT_ROOT / "tsmis_highway_log_pdf"   # scratch per-route workbooks
OUT_PATH = OUTPUT_ROOT / FILENAME                       # legacy flat combined output

# Friendly report name for user-facing messages (UI-neutral: no ".bat" /
# "menu option" wording).
REPORT_NAME = "TSMIS Highway Log (PDF)"

# File pattern the GUI uses to preview how many inputs a folder holds.
INPUT_GLOB = "*.pdf"

# Input file format, shown as the Consolidate-tab badge (these are route PDFs).
INPUT_FMT = "PDF"


def input_dir_for(day):
    """The 'Highway Log (PDF)' export PDFs for `day` (a run-folder name); None =
    the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """Combined workbook destination for `day` (a run-folder name); None = the
    legacy location. The dated filename carries the run's date + source/environment
    so a copy lifted out of its folder keeps its provenance."""
    if not day:
        return OUT_PATH
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(FILENAME, day)


# Must match the TSMIS Highway Log export exactly (sheet name AND header), so the
# converted files consolidate with the same core and the combined workbook is
# column-compatible with the consolidated TSN Highway Log and the Excel export.
SHEET_NAME = "Highway Log"
# The corrected 31-column Highway Log header lives in ONE place (the vendor Excel
# mislabeled these; see highway_log_columns). Description is column 28 — filled
# from follow-on lines, not a PDF cell column: the 30 PDF cells map to header
# positions 0..27, then Description, then the two date columns (29, 30).
TSMIS_HEADER = hlc.HEADER
_DESC_IDX = hlc.DESC_IDX                                # 28


# =============================================================================
# PDF layout
# =============================================================================

N_PDF_COLS = 30          # data cells per row = the 31 TSMIS columns minus Description
Y_TOLERANCE = 3          # chars within this y-distance form one logical line
HEADER_BAND = 64         # fallback header cutoff when the column-header row isn't found
HEADER_EPS = 2           # tolerance below the header row before content begins
WORD_GAP = 1.5           # x-gap that starts a new token inside one cell
URL_MARK = "tsmis.dot.ca.gov"   # the page-footer URL line (never report data)

# A segment postmile as printed in the Location column: an optional realignment/
# section letter prefix ("R", "L", "C"), the 3.3 postmile, and an optional
# equation/realignment suffix ("E", "R"). TSMIS prints the same prefixed form
# the TSN log does.
LOCATION_RE = re.compile(r"^[A-Z]?\d{3}\.\d{3}[A-Z]?$")
# Centered "<district> <county> <route>" group header, e.g. "09 INY 006" or the
# period-bearing county codes "07 LA. 005S" / "11 SD. 905".
GROUP_RE = (re.compile(r"^\d{2}$"), re.compile(r"^[A-Z]{2,4}\.?$"),
            re.compile(r"^\d{1,3}[A-Z]?$"))
# Route token out of "highway_log_route_<ROUTE>.pdf".
ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]?)", re.IGNORECASE)
# The "Route 006" / "Route 005S" line on the cover page (a cross-check).
ROUTE_HEADER_RE = re.compile(r"^Route\s+([0-9]+[A-Za-z]?)$", re.IGNORECASE)


def _norm_route(token):
    """'6' -> '006' (TSMIS zero-pads to 3 digits); suffixed routes ('101U',
    '005S') keep their letter and are upper-cased."""
    m = re.fullmatch(r"(\d+)([A-Za-z]?)", token)
    if not m:
        return token.upper()
    return f"{int(m.group(1)):03d}{m.group(2).upper()}"


def _cluster_lines(page):
    """Cluster the page's characters into logical lines (tolerating the small
    baseline jitter of a wrapped row). Each line yields its word tokens (for
    classifying the line) AND the raw characters (for column parsing)."""
    clusters = []                     # [(anchor_top, [char, ...]), ...]
    for c in sorted(page.chars, key=lambda c: (c["top"], c["x0"])):
        if not c["text"].strip():
            continue                  # literal spaces carry no data
        if clusters and abs(c["top"] - clusters[-1][0]) <= Y_TOLERANCE:
            clusters[-1][1].append(c)
        else:
            clusters.append((c["top"], [c]))
    lines = []
    for top, chars in clusters:
        chars.sort(key=lambda c: c["x0"])
        words = []
        for c in chars:
            if words and c["x0"] - words[-1]["x1"] < WORD_GAP:
                words[-1]["text"] += c["text"]
                words[-1]["x1"] = c["x1"]
            else:
                words.append({"text": c["text"], "x0": c["x0"], "x1": c["x1"]})
        lines.append((top, words, chars))
    return lines


def _page_column_windows(page):
    """Derive the page's 30 contiguous data-column windows from its zebra-shaded
    data-row cell rects, or None when the page has no full data band (a cover /
    legend page). Only shaded rows carry rects; every shaded band on a page
    shares the table's column geometry, so the per-column median edge is exact
    and robust to a stray rect.

    The windows are made CONTIGUOUS (each boundary is the midpoint between
    adjacent cells; the first/last extend to ±infinity), so no data character
    can fall between two cells and be silently dropped."""
    cells = [r for r in page.rects
             if 3 < (r["x1"] - r["x0"]) < page.width - 20
             and 3 < (r["bottom"] - r["top"]) < 40]
    bands = defaultdict(list)
    for r in cells:
        bands[round(r["top"])].append(r)
    data_bands = [sorted(v, key=lambda r: r["x0"])
                  for v in bands.values() if len(v) == N_PDF_COLS]
    if not data_bands:
        return None

    def median(values):
        s = sorted(values)
        return s[len(s) // 2]

    centers, edges_lo, edges_hi = [], [], []
    for i in range(N_PDF_COLS):
        lo = median([b[i]["x0"] for b in data_bands])
        hi = median([b[i]["x1"] for b in data_bands])
        edges_lo.append(lo)
        edges_hi.append(hi)
        centers.append((lo + hi) / 2)

    windows = []
    for i in range(N_PDF_COLS):
        lo = float("-inf") if i == 0 else (edges_hi[i - 1] + edges_lo[i]) / 2
        hi = float("inf") if i == N_PDF_COLS - 1 else (edges_hi[i] + edges_lo[i + 1]) / 2
        windows.append((lo, hi))
    # col0's true right edge (not the contiguous boundary) — used to tell a
    # data row (postmile starts inside col0) from a description (starts to the
    # right of col0).
    col0_right = edges_hi[0]
    return windows, col0_right


def _header_bottom(lines):
    """The y (top) of the column-header's BOTTOM row — the
    "LOCATION MI A ODOM CITY …" row that repeats at the top of every data page.
    Lines at or above it are page furniture (the page title + the multi-row
    column header); the report's content (group headers, data, descriptions)
    is strictly below it.

    Found by CONTENT, not a fixed y, because a near-empty "orphan" page (a row's
    description pushed onto the next page) shifts its whole layout up — a fixed
    cutoff would swallow that description. Returns None when the row isn't on the
    page (the cover / legend pages, which carry no report content)."""
    bottom = None
    for top, words, _chars in lines:
        joined = " ".join(w["text"] for w in words).upper()
        if "ODOM" in joined and "CITY" in joined:   # unique to the bottom header row
            bottom = top
    return bottom


def _assign_columns(chars, windows):
    """Map each character of a data line to its column by horizontal center.
    Characters of one column abut (~0pt apart); a gap >= WORD_GAP inside the
    same column means two tokens, kept apart with a space."""
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
    return vals


def _normalize_location(loc):
    """The Location is a single token (optional letter prefix + postmile +
    optional suffix). A glued left-margin marker prints with a small gap, so the
    column assembler may have inserted a space ('C 043.925E'); collapse it so
    the key matches the TSN/Excel single-token form ('C043.925E')."""
    return re.sub(r"\s+", "", loc) if loc else loc


def _make_row(vals, description):
    """Assemble the 31-column TSMIS row from the 30 parsed cell values +
    the accumulated Description. PDF cells 0..27 -> TSMIS Location..RB SH;
    then Description; then PDF cells 28..29 -> Date of Rec / Sig Chg. Date."""
    vals = [v.strip() or None for v in vals]
    vals[0] = _normalize_location(vals[0]) if vals[0] else None
    return vals[0:_DESC_IDX] + [description] + vals[_DESC_IDX:N_PDF_COLS]


def parse_pdf(path, events, pdf_name=""):
    """Parse one TSMIS Highway Log PDF into TSMIS-format rows.

    Returns (route, rows): `route` from the in-PDF cover (cross-checked against
    the filename by the caller), `rows` a list of 31-column row lists in
    document order (all counties concatenated — county is a section marker, not
    a column). Returns (route, None) if cancelled mid-PDF.
    """
    route = None
    rows = []
    last_row = None                   # description lines attach to this row

    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        page_windows = None           # carried forward if a page lacks a data band
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return route, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            derived = _page_column_windows(page)
            if derived is not None:
                page_windows, col0_right = derived

            lines = _cluster_lines(page)
            hdr_bottom = _header_bottom(lines)
            # Skip everything at/above the column header. A precise per-page
            # cutoff (vs a fixed band) keeps an orphan description that a page
            # break pushed just below a top-shifted header on a near-empty page.
            cutoff = (hdr_bottom + HEADER_EPS) if hdr_bottom is not None else HEADER_BAND
            for top, words, line_chars in lines:
                texts = [w["text"] for w in words]
                if not texts:
                    continue
                if any(URL_MARK in t for t in texts):
                    continue                          # page-footer URL
                # Cover page: "Route 006" pins the route (filename is primary).
                if route is None and len(texts) == 2:
                    m = ROUTE_HEADER_RE.match(" ".join(texts))
                    if m:
                        route = _norm_route(m.group(1))
                        continue
                if top <= cutoff:
                    continue                          # per-page column-header band
                first_x0 = words[0]["x0"]

                # "* * * ... TOTALS ..." summary lines mark the END of a segment's
                # data + description, so they CLOSE the open row: any footer
                # fragment that follows must not attach to the preceding
                # Description.
                if texts[0].startswith("*"):
                    last_row = None
                    continue

                # Centered "<district> <county> <route>" group header.
                if (len(texts) >= 3 and first_x0 > page.width * 0.30
                        and GROUP_RE[0].match(texts[0])
                        and GROUP_RE[1].match(texts[1])
                        and GROUP_RE[2].match(texts[2])):
                    route = route or _norm_route(texts[2])
                    last_row = None                   # don't attach across groups
                    continue

                if page_windows is None:
                    continue                          # no table on this page yet

                # Data row: a postmile begins inside the Location column. The
                # optional left-margin letter ("C"/"R"/"L") makes the FIRST token
                # a lone letter, so accept either a bare postmile or letter+postmile.
                is_data = (
                    (LOCATION_RE.match(texts[0]) and first_x0 < col0_right)
                    or (len(texts) >= 2 and len(texts[0]) == 1 and texts[0].isalpha()
                        and LOCATION_RE.match(texts[1]) and first_x0 < col0_right))
                if is_data:
                    vals = _assign_columns(line_chars, page_windows)
                    row = _make_row(vals, None)
                    rows.append(row)
                    last_row = row
                    continue

                # Anything else below the header band that starts to the RIGHT of
                # the Location column is a Description for the previous segment
                # (TSMIS prints them on their own lines below the data row). A
                # long description WRAPS across baselines; rejoin those with a
                # space (not a comma) so the cell matches the report's own text
                # ("… END R" + "REALIGNMENT" -> "… END R REALIGNMENT").
                if last_row is not None and first_x0 >= col0_right:
                    text = " ".join(texts)
                    if last_row[_DESC_IDX]:
                        last_row[_DESC_IDX] += " " + text
                    else:
                        last_row[_DESC_IDX] = text

    return route, rows


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Highway Log workbook (same sheet
    name + 31 columns the Excel export uses)."""
    header_fill = PatternFill("solid", start_color="305496")
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(TSMIS_HEADER)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
    hlc.apply_header_tooltips(ws)            # hover any header for its meaning
    ws.freeze_panes = "A2"
    for i, name in enumerate(TSMIS_HEADER, start=1):
        ws.column_dimensions[get_column_letter(i)].width = \
            40 if name == "Description" else 12

    for row in rows:
        ws.append(row)
        # Neutralize any formula-looking text (e.g. a Description starting with
        # "=") so it can't execute when the workbook is opened.
        for cell in ws[ws.max_row]:
            if is_formula_injection(cell.value):
                cell.data_type = "s"
    hlc.write_legend_sheet(wb)               # a "Legend" tab explaining every column
    wb.save(out_path)


# =============================================================================
# Entry point
# =============================================================================

def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None):
    """Convert every TSMIS Highway Log PDF to a TSMIS-format per-route workbook,
    then combine them into one workbook (Route column added).

    `day` picks which export run folder ("<YYYY-MM-DD> <src>-<env>") of
    "Highway Log (PDF)" exports to read; None means the newest run folder, falling
    back to the legacy flat layout when no run folders exist yet — exactly like the
    Excel Highway Log consolidator.

    Console-free: progress via events.on_log, overwrite confirmed through the
    confirm_overwrite(path)->bool callback, a ConsolidateResult returned. Honors
    events.is_cancelled() between pages.
    """
    # input_dir/out_path/converted_dir are OPTIONAL overrides (the matrix points
    # them at an Export-Everything store folder + a scratch dir). When omitted the
    # behavior is byte-identical to before: the dated run folder + the shared dirs.
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

    # Ensure the folder exists so the error below names a real, openable path.
    try:
        in_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    pdfs = sorted(in_dir.glob("*.pdf"))
    if not pdfs:
        return ConsolidateResult(
            status="error",
            message=(f"No {REPORT_NAME} files were found in:\n{in_dir}\n\n"
                     f"Export the 'Highway Log (PDF)' report first (it saves the "
                     f"per-route PDFs there), then run this again."),
        )

    # Confirm overwrite *before* spending time parsing PDFs.
    if out.exists() and not confirm(out):
        return ConsolidateResult(status="cancelled",
                                 message="Cancelled. Existing file kept.")

    events.on_log("=" * 60)
    events.on_log(f"TSMIS Highway Log (PDF) Conversion - {len(pdfs)} route PDF(s)")
    events.on_log("=" * 60)
    events.on_log("")

    # The combined workbook reflects exactly THIS run's PDFs: clear previously
    # converted files so routes removed from the input folder don't linger.
    conv.mkdir(parents=True, exist_ok=True)
    stale = list(conv.glob("tsmis_highway_log_pdf_*.xlsx"))
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
    failed = []
    written = set()                  # guard against duplicate route across PDFs
    for i, p in enumerate(pdfs, 1):
        if events.is_cancelled():
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        prefix = f"[{i}/{len(pdfs)}] {p.name}"
        events.on_log(f"{prefix} parsing…")
        name_m = ROUTE_FROM_NAME.search(p.stem)
        name_route = _norm_route(name_m.group(1)) if name_m else None
        try:
            pdf_route, rows = parse_pdf(str(p), events, pdf_name=p.name)
        except Exception as e:
            events.on_log(f"{prefix} FAILED ({type(e).__name__}): {e}")
            failed.append(p.name)
            continue
        if rows is None:                             # cancelled mid-PDF
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        route = name_route or pdf_route
        if not route:
            events.on_log(f"{prefix} no route could be determined; skipping")
            failed.append(p.name)
            continue
        if pdf_route and name_route and pdf_route != name_route:
            events.on_log(f"  WARNING: filename says route {name_route} but the PDF "
                          f"header says {pdf_route}; using {route} (the filename).")
        if not rows:
            events.on_log(f"{prefix} no highway-log data found; skipping")
            failed.append(p.name)
            continue
        out_file = conv / f"tsmis_highway_log_pdf_route_{route}.xlsx"
        if out_file.name in written:
            events.on_log(f"  WARNING: route {route} already converted from an earlier "
                          f"PDF; {p.name} replaces it (is the same route in the "
                          "folder twice?)")
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
                     f"{REPORT_NAME} data. Are they the TSMIS Highway Log PDFs "
                     "(the 'Highway Log (PDF)' export)?"),
        )

    events.on_log("")

    # Combine all converted per-route files with the shared XLSX core (header
    # lock-in, Route column from the filename, streaming write). Overwrite was
    # already confirmed above.
    result = consolidate_xlsx(
        input_dir=conv, out_path=out, sheet_name=SHEET_NAME,
        report_name=REPORT_NAME, title="TSMIS Highway Log (PDF) Consolidation",
        events=events, confirm_overwrite=lambda _p: True,
        header_override=hlc.HEADER, header_comment=hlc.comment_for,
        decorate_workbook=hlc.write_legend_sheet,
    )
    if result.status == "ok":
        result.summary_lines = [
            f"Route PDFs:   {len(pdfs) - len(failed)} converted"
            + (f", {len(failed)} failed {failed}" if failed else ""),
            f"Route files:  {converted} (in {conv})",
        ] + result.summary_lines
    return result


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
