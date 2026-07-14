"""Convert TSMIS Intersection Detail PDFs into TSMIS-format Excel and combine.

The TSMIS "Intersection Detail (PDF)" export (report 6b — the site's Print layout
saved via `page.pdf()`) renders the report as a real, BORDERED HTML table. Just
like Highway Log, the PDF and the vendor Excel export can DISAGREE on data, so
this consolidator parses those per-route PDFs into the SAME 35-column TSMIS
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
physical table rows make ONE record. Since the July 2026 site update the print
opens with THREE cover pages (report parameters + the policy text) and the site's
`intd_renderRow` emits each intersection as
  * rowA — the Post Mile (now zero-padded, '000.204'), Location, Date of Record
    and the INT / CONTROL / LIGHTING / MAINLINE attribute cells on a 21-column
    grid whose LAST column is a vestigial empty remnant of the dropped second
    'ML Eff-Date'; and
  * rowB — the record's DB intersection NUMBER (printed only here — neither the
    Excel export nor TSN carries it, so it is NOT part of the output row), a WIDE
    Description cell (it spans grid columns 3-6), then the Main Line /
    Intersecting / Intersecting-Route / Xing cells on an 18-column grid.
`intd_renderRow` ZEBRA-SHADES alternate records (`idx % 2 === 0`), and ONLY the
shaded records carry cell rectangles — the un-shaded ones render as borderless
text. So we can't band by rects (that would silently drop every other record).
Instead we derive BOTH grids' column x-windows ONCE from the shaded records'
21-cell (rowA) and 18-cell (rowB) bands (the print layout is a single table, so
column widths are uniform across pages), then assign EVERY text line's characters
to those windows. A line whose Post Mile column holds a zero-padded postmile is a
rowA; the next line whose column 1 holds the plain-integer intersection number is
its rowB (page furniture between them — the repeated table header — is skipped).

Pre-update PDFs (unpadded postmiles, no rowB intersection number) parse to ZERO
rows by construction; they are refused per file with a re-export hint rather than
mis-mapped — the old 36-column layout cannot be represented in the current shape.

No value normalization happens here: the PDF already carries the native TSMIS
formats, so values are written through verbatim. The comparison engine applies any
normalization at compare time, exactly as for the Excel side.

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
    import openpyxl  # noqa: F401 — the gate covers both the PDF and XLSX deps
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from intersection_detail_columns import HEADER as INTD_HEADER
import outcome
from pdf_table_lib import (assign_columns, cluster_by_top, contiguous_windows,
                           median, norm_route, run_pdf_conversion,
                           write_route_workbook)
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

N_COLS_A = 21            # rowA's grid (the last column is a vestigial empty cell)
N_COLS_B = 18            # rowB's grid (its own rects since the July 2026 update)
CELL_MIN_W = 3           # ignore hairline / spacer rects when finding shaded bands
CELL_MIN_H = 3
CELL_MAX_H = 40          # a data cell is one text line tall
Y_TOLERANCE = 3          # chars within this y-distance form one logical line
WORD_GAP = 1.5           # x-gap that opens a new token inside one column

# A rowA's Post Mile is the site's zero-padded '000.204' form — the discriminator
# against a rowB, whose column 1 holds the plain-integer intersection number.
PM_ROWA_RE = re.compile(r"^\d{3}\.\d{3}$")
INT_ROWB_RE = re.compile(r"^\d+$")
# A PRE-update rowA printed the postmile unpadded ('0.204'); counting those lets a
# refused old-layout PDF say WHY instead of a bare "no data found".
OLD_PM_RE = re.compile(r"^\d{1,2}\.\d{3}$")
# A data rowA's Location cell is "<district> <county> <route>", e.g. "04 SOL 780"
# or the period-bearing county codes "04 CC. 004" / "10 SJ. 120". This guards the
# rowA classification against any stray non-data line and is cheap to evaluate.
LOCATION_RE = re.compile(r"\d{2}\s+[A-Z]")
# Route token out of "intersection_detail_route_<ROUTE>.pdf".
ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]?)", re.IGNORECASE)


# The canonical route-token normalizer (pdf_table_lib reconciled the 4 copies;
# this module's behavior is unchanged).
_norm_route = norm_route


def _cluster_lines(page):
    """Cluster the page's non-space characters into logical lines (tolerating the
    small baseline jitter of a row). Returns [(top, [chars sorted by x0]), ...]."""
    return cluster_by_top((c for c in page.chars if c["text"].strip()), Y_TOLERANCE)


def _shaded_column_windows(pdf, n_cols):
    """Derive `n_cols` contiguous column windows from the document's zebra-shaded
    cell rects (rowA bands have 21 cells, rowB bands 18).

    Only the shaded (even-index) records carry rects, but the print layout is ONE
    table, so its column widths are uniform across every page and row — the median
    cell edges of the shaded bands therefore give the grid for EVERY line, shaded
    or not. The windows are made CONTIGUOUS (each boundary is the midpoint between
    adjacent cells; the ends extend to ±infinity) so no character can fall between
    two columns and be dropped. Returns the (lo, hi) windows, or None if no full
    band of that shape was found anywhere (an empty / unreadable PDF)."""
    bands = []
    for page in pdf.pages:
        by_top = defaultdict(list)
        for r in page.rects:
            w = r["x1"] - r["x0"]
            h = r["bottom"] - r["top"]
            if CELL_MIN_W < w < page.width - 10 and CELL_MIN_H < h < CELL_MAX_H:
                by_top[round(r["top"])].append(r)
        for cells in by_top.values():
            if len(cells) == n_cols:
                bands.append(sorted(cells, key=lambda r: r["x0"]))
    if not bands:
        return None

    lo = [median([b[i]["x0"] for b in bands]) for i in range(n_cols)]
    hi = [median([b[i]["x1"] for b in bands]) for i in range(n_cols)]
    return contiguous_windows(lo, hi)


def _doc_windows(pdf):
    """(rowA windows, rowB windows) for the document, or (None, None) when no
    shaded band of either shape exists (an empty / unreadable PDF). rowB's grid
    comes from its OWN 18-cell bands — its merged Description cell (grid columns
    3-6 of rowA) arrives as one window, so WORD_GAP spacing flows continuously
    across it and a word straddling a rowA-column boundary isn't split."""
    wa = _shaded_column_windows(pdf, N_COLS_A)
    wb = _shaded_column_windows(pdf, N_COLS_B)
    if wa is None or wb is None:
        return None, None
    return wa, wb


def _assign_columns(chars, windows):
    """Map each character of a line to its column (pdf_table_lib), stripped —
    '04'/'SOL'/'780' -> '04 SOL 780' and 'LEMON'/'ST' -> 'LEMON ST'."""
    return [v.strip() for v in assign_columns(chars, windows, WORD_GAP)]


def _is_rowA(vals):
    """A record's FIRST line carries the zero-padded Post Mile in column 1 and a
    real Location in column 3. Header furniture ("POST MILE", …) fails the PM
    shape; a rowB fails it too (its column 1 is the integer intersection number)."""
    return bool(PM_ROWA_RE.match(vals[1]) and LOCATION_RE.search(vals[3] or ""))


def _make_row(a, b):
    """Assemble the 35-column Intersection Detail row from rowA's 21 grid values
    and rowB's 18 grid values.

    rowA columns 0..19 map 1:1 to output columns 0..19 (P .. ML N/L); rowA column
    20 is the vestigial remnant of the dropped second 'ML Eff-Date' (checked empty
    by the caller, never emitted). rowB window 1 is the print-only intersection
    number (discarded — the Excel export has no such column); window 3 is the
    merged Description; windows 4..11 the Main Line / Intersecting / Int-St cells.
    The Excel export emits the intersecting-route pair as 'Intrte S' THEN 'Intrte
    Route' — the REVERSE of their left-to-right order in the PDF — so rowB window
    13 (Intrte S) -> col 29 and window 12 (Intrte Route) -> col 30, keeping the
    two sources column-compatible. Windows 16/17 are the July-2026 'Xing P/S'
    (the crossing postmile's L/R marker) and 'Xing Line Lgth' tail."""
    a = [v or None for v in a]
    b = [v or None for v in b]
    return [
        *a[0:20],   # 0..19  P, Post Mile, S, Location, Date of Record, … ML N/L
        b[3],       # 20 Description    (rowB merged window, rowA grid cols 3-6)
        b[4],       # 21 Main Line Lgth
        b[5],       # 22 Inter Eff-Date
        b[6],       # 23 Inter S
        b[7],       # 24 Inter L
        b[8],       # 25 Inter R
        b[9],       # 26 Inter T
        b[10],      # 27 Inter N
        b[11],      # 28 Int St Eff-Date
        b[13],      # 29 Intrte S       (rowB window 13; Excel lists S first)
        b[12],      # 30 Intrte Route   (rowB window 12)
        b[14],      # 31 Intrte Post
        b[15],      # 32 Intrte Mile
        b[16],      # 33 Xing P/S
        b[17],      # 34 Xing Line Lgth
    ]


def parse_pdf(path, events):
    """Parse one TSMIS Intersection Detail PDF into 35-column TSMIS-format rows.

    Returns (rows, stats): `rows` a list of 35-column row lists in document order,
    `stats` a reconciliation dict (emitted, pages, orphans = a rowA whose rowB
    never arrived — should be 0; `no_grid` when the column geometry couldn't be
    derived; `old_layout` when the file matches the PRE-July-2026 print instead —
    unpadded postmiles, no rowB intersection numbers; `vestigial` counts rowA
    values in the dropped 21st column, a layout-drift canary that should be 0).
    Returns (None, None) if cancelled.

    A line whose Post Mile column holds a zero-padded postmile is a rowA; its rowB
    is the NEXT line whose column 1 holds the plain-integer intersection number —
    page furniture between them (the table header repeated on every page, the
    cover pages) matches neither shape and is skipped, so a record split across a
    page boundary still pairs. A second rowA arriving before any rowB surfaces as
    an orphan, never a silent drop."""
    rows = []
    pending_a = None            # a rowA (21 grid vals) awaiting its rowB
    orphans = 0
    old_pm_hits = 0
    vestigial = 0
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        win_a, win_b = _doc_windows(pdf)
        if win_a is None:
            return [], {"emitted": 0, "pages": n_pages, "orphans": 0,
                        "no_grid": True, "old_layout": False, "vestigial": 0}
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            for _top, chars in _cluster_lines(page):
                vals = _assign_columns(chars, win_a)
                if _is_rowA(vals):
                    if pending_a is not None:
                        orphans += 1        # previous rowA never got its rowB
                    pending_a = vals
                    if vals[20]:
                        vestigial += 1      # the dropped column grew data back?!
                    continue
                if OLD_PM_RE.match(vals[1]) and LOCATION_RE.search(vals[3] or ""):
                    old_pm_hits += 1        # a PRE-update rowA (unpadded postmile)
                    continue
                if pending_a is not None:
                    vals_b = _assign_columns(chars, win_b)
                    if INT_ROWB_RE.match(vals_b[1] or ""):
                        rows.append(_make_row(pending_a, vals_b))
                        pending_a = None
                    # else: furniture between a rowA and its rowB — skip
    if pending_a is not None:
        orphans += 1
    return rows, {"emitted": len(rows), "pages": n_pages, "orphans": orphans,
                  "no_grid": False, "old_layout": not rows and old_pm_hits > 0,
                  "vestigial": vestigial}


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Intersection Detail workbook (same
    sheet name + 35 columns the Excel export uses)."""
    write_route_workbook(rows, out_path, sheet_name=SHEET_NAME, header=INTD_HEADER)


# =============================================================================
# Entry point
# =============================================================================

def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Convert every TSMIS Intersection Detail PDF to a TSMIS-format per-route
    workbook, then combine them into one workbook (Route column added).

    `day` picks which export run folder of "Intersection Detail (PDF)" exports to
    read; None means the newest run folder, falling back to the legacy flat layout.
    Console-free; honors events.is_cancelled() between pages. The convert-loop
    skeleton lives in pdf_table_lib.run_pdf_conversion; this module supplies the
    layout knowledge: the per-PDF step (route from the FILENAME — the print layout
    carries no route label; orphan reconciliation; the pre-update-layout refusal)
    and the ⚠-note / PARTIAL-escalation policy.
    """
    day = day or latest_output_day()
    in_dir = Path(input_dir) if input_dir else input_dir_for(day)
    out = Path(out_path) if out_path else out_path_for(day)
    conv = Path(converted_dir) if converted_dir else CONVERTED_DIR

    def convert_one(p, prefix, ev, ctx):
        name_m = ROUTE_FROM_NAME.search(p.stem)
        route = _norm_route(name_m.group(1)) if name_m else None
        if not route:
            ev.on_log(f"{prefix} no route in filename; skipping")
            ctx["failed"].append(p.name)
            return ("skip",)
        rows, pstats = parse_pdf(str(p), ev)
        if rows is None:                             # cancelled mid-PDF
            return ("cancelled",)
        if pstats:
            ctx["orphans"] = ctx.get("orphans", 0) + pstats["orphans"]
            if pstats["orphans"]:
                ev.on_log(f"  WARNING: {pstats['orphans']} unpaired row(s) in {p.name} "
                          "(a record's two lines didn't pair) — see the log.")
            if pstats["vestigial"]:
                ctx["vestigial"] = ctx.get("vestigial", 0) + pstats["vestigial"]
                ev.on_log(f"  WARNING: {pstats['vestigial']} value(s) in the dropped "
                          f"21st rowA column of {p.name} — the print layout may have "
                          "changed again; verify before relying on this output.")
            if pstats["old_layout"]:
                ev.on_log(f"{prefix} uses the PRE-July-2026 print layout (unpadded "
                          "postmiles) — this version parses the current layout only. "
                          "Re-export the Intersection Detail (PDF) report; skipping")
                ctx["failed"].append(p.name)
                return ("skip",)
        if not rows:
            ev.on_log(f"{prefix} no intersection data found; skipping")
            ctx["failed"].append(p.name)
            return ("skip",)
        return ("ok", route, rows)

    def finalize(result, ctx):
        orphans = ctx.get("orphans", 0)
        notes = []
        if orphans:
            notes.append(f"⚠ {orphans} unpaired row line(s) — verify (see the log).")
        if ctx.get("vestigial"):
            notes.append(f"⚠ {ctx['vestigial']} value(s) in the dropped 21st rowA "
                         "column — the print layout may have changed; verify.")
        result.summary_lines = notes + result.summary_lines
        # RR2-B1 / D18 parity with the HL-PDF consolidator: an unpaired record or
        # a failed PDF is invisible to the XLSX consolidator, so ESCALATE to a
        # producer-owned partial — the incomplete output must not be promoted /
        # cached / compared as complete.
        if orphans or ctx["failed"]:
            result.completion = outcome.PARTIAL
            result.skipped_inputs = max(result.skipped_inputs, orphans)
            result.failed_inputs = max(result.failed_inputs, len(ctx["failed"]))

    return run_pdf_conversion(
        in_dir=in_dir, out=out, conv=conv, deps_ok=_DEPS_OK,
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        report_name=REPORT_NAME,
        banner_title="TSMIS Intersection Detail (PDF) Conversion",
        export_hint=("Export the 'Intersection Detail (PDF)' report first (it saves "
                     "the per-route PDFs there), then run this again."),
        unreadable_hint=("Are they the TSMIS Intersection Detail PDFs "
                         "(the 'Intersection Detail (PDF)' export)?"),
        converted_prefix="tsmis_intersection_detail_pdf",
        convert_one=convert_one, write_one=_write_route_workbook,
        finalize=finalize,
        consolidate_kwargs=dict(
            sheet_name=SHEET_NAME, report_name=REPORT_NAME,
            title="TSMIS Intersection Detail (PDF) Consolidation"),
    )



if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
