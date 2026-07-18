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
                           median, norm_route, reconcile_route_identity,
                           run_pdf_conversion, write_route_workbook)
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
# The document's own route claim (CMP-AUD-049): the cover's REPORT PARAMETERS
# block prints the export's SUBJECT route ("ROUTE : 020"; suffixed routes one
# token, "ROUTE : 178S") — matched on a line's spaceless chars. The per-record
# Location cells canNOT identify the document: an intersection OF this route
# WITH another route prints the OTHER route's mainline in Location, so
# multi-route Location sets are NORMAL (118 of the 217 statewide 7.9 per-route
# prints carry them — censused before this rule was coded). Only the cover
# parameter is the document's claim about itself.
COVER_ROUTE_RE = re.compile(r"^ROUTE:([0-9]+[A-Za-z]?)$")
_COVER_SCAN_PAGES = 2                   # the parameter block sits on the cover
# Route token out of "intersection_detail_route_<ROUTE>.pdf".
ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]?)", re.IGNORECASE)


# The canonical route-token normalizer (pdf_table_lib reconciled the 4 copies;
# this module's behavior is unchanged).
_norm_route = norm_route


def _cluster_lines(page):
    """Cluster the page's non-space characters into logical lines (tolerating the
    small baseline jitter of a row). Returns [(top, [chars sorted by x0]), ...]."""
    return cluster_by_top((c for c in page.chars if c["text"].strip()), Y_TOLERANCE)


# A page's OWN band grid may not diverge from the document median by more than
# this (CMP-AUD-062). The print layout is one table, so the columns are uniform
# across pages — the statewide 7.9 census measured 0.000pt divergence on every
# page carrying a band. A page that shifts past this (a mixed-paper / re-laid-out
# build) would silently stop classifying on the document median, so it escalates
# the producer to PARTIAL instead of being dropped.
_PAGE_GEOM_TOL = 6.0


def _page_bands(page, n_cols):
    """This page's zebra-shaded cell bands of exactly `n_cols` cells (x0-sorted)."""
    by_top = defaultdict(list)
    for r in page.rects:
        w = r["x1"] - r["x0"]
        h = r["bottom"] - r["top"]
        if CELL_MIN_W < w < page.width - 10 and CELL_MIN_H < h < CELL_MAX_H:
            by_top[round(r["top"])].append(r)
    return [sorted(cells, key=lambda r: r["x0"])
            for cells in by_top.values() if len(cells) == n_cols]


def _windows_from_bands(bands, n_cols):
    """Contiguous column windows from the median cell edges of `bands` (each a
    band of exactly `n_cols` x0-sorted rects), or None when empty. CONTIGUOUS
    (each boundary the midpoint between adjacent cells; ends to ±infinity) so no
    character falls between two columns and is dropped."""
    if not bands:
        return None
    lo = [median([b[i]["x0"] for b in bands]) for i in range(n_cols)]
    hi = [median([b[i]["x1"] for b in bands]) for i in range(n_cols)]
    return contiguous_windows(lo, hi)


def _page_geometry_diverges(page, win_a, win_b):
    """True when THIS page's own band grid (either shape) diverges from the
    document-median windows by more than `_PAGE_GEOM_TOL` at any interior
    boundary (CMP-AUD-062). A page with no full band of a shape can't diverge on
    that shape (nothing to compare) — it parses on the document median as before."""
    for own_windows, doc_windows, n in ((_windows_from_bands(_page_bands(page, N_COLS_A), N_COLS_A), win_a, N_COLS_A),
                                        (_windows_from_bands(_page_bands(page, N_COLS_B), N_COLS_B), win_b, N_COLS_B)):
        if own_windows is None or doc_windows is None:
            continue
        for own, doc in zip(own_windows[1:], doc_windows[1:]):   # interior edges
            if abs(own[0] - doc[0]) > _PAGE_GEOM_TOL:
                return True
    return False


def _doc_windows(pdf, events=None):
    """(rowA windows, rowB windows) for the document, or (None, None) when no
    shaded band of either shape exists (an empty / unreadable PDF). rowB's grid
    comes from its OWN 18-cell bands — its merged Description cell (grid columns
    3-6 of rowA) arrives as one window, so WORD_GAP spacing flows continuously
    across it and a word straddling a rowA-column boundary isn't split.

    CMP-AUD-061: derives BOTH grids in ONE pass and polls `events.is_cancelled()`
    between pages, so cancelling during the geometry scan returns promptly instead
    of scanning every page/rectangle first. Returns (None, None) on cancel too; the
    caller distinguishes cancelled from no-grid via `events.is_cancelled()`. The
    collected bands are identical to the previous two-pass derivation (byte-identical
    output)."""
    bands_a, bands_b = [], []
    for page in pdf.pages:
        if events is not None and events.is_cancelled():
            return None, None
        bands_a.extend(_page_bands(page, N_COLS_A))
        bands_b.extend(_page_bands(page, N_COLS_B))
    wa = _windows_from_bands(bands_a, N_COLS_A)
    wb = _windows_from_bands(bands_b, N_COLS_B)
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


# rowB's merged Description window (grid columns 3-6 of rowA), used to validate the
# COMPLETE rowB shape below (CMP-AUD-058) — see _make_row's b[3] -> col 20.
_ROWB_DESC_WIN = 3
# A wrapped Description continuation sits within this top-delta of its rowB (the ID
# print line height is ~9.7pt; a wrapped fragment ~5-6pt), so a desc-only baseline
# this close below a rowB is a wrap the line-by-line parser can't rejoin
# (CMP-AUD-056). The statewide 7.9 census found ZERO — this is the loud safety net.
_ROWB_WRAP_GAP = 7.5


def _is_rowB(vals_b):
    """A record's SECOND line: the plain-integer intersection number in window 1
    AND a populated Description window (CMP-AUD-058). The integer ALONE is not
    enough — a numeric furniture line (a page number, a year like '2026') printed
    with a rowA pending would otherwise be consumed as a mostly-blank rowB, emit a
    corrupt record, and orphan the real rowB. The statewide 7.9 census confirmed
    every one of the 16,459 real rowB records carries a Description, so requiring
    it rejects the numeric furniture without dropping a single real record."""
    return bool(INT_ROWB_RE.match(vals_b[1] or "")
                and (vals_b[_ROWB_DESC_WIN] or "").strip())


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
    `stats` a reconciliation dict. The reconciliation counters (all `should be 0`
    on the current statewide corpus — each drives a producer PARTIAL escalation so
    the anomaly can never certify a clean-looking match):
      * `orphans`          a rowA whose rowB never arrived (existing);
      * `leading_orphan_b` a complete rowB with no rowA pending (CMP-AUD-057) —
                           a rowB-shaped line is now classified independent of the
                           pending state, never silently treated as furniture;
      * `wrapped_rowb`     a Description continuation baseline the line-by-line
                           parser cannot rejoin (CMP-AUD-056);
      * `vestigial`        rowA values in the dropped 21st column, a layout-drift
                           canary (CMP-AUD-060 — now escalates, not just warned);
      * `old_pm_hits`      PRE-July-2026 unpadded-postmile rowAs (CMP-AUD-059 — a
                           legacy hit escalates even when current rows also exist,
                           so a mixed/transitional file can't drop its legacy rows
                           silently); `old_layout` stays the homogeneous-old flag;
      * `geom_divergent_pages` pages whose OWN band grid diverges from the
                           document median past `_PAGE_GEOM_TOL` (CMP-AUD-062 — the
                           finding's shifted page would silently stop classifying).
    Plus `no_grid` when the geometry couldn't be derived and `doc_routes` (the
    cover's own ROUTE claim, CMP-AUD-049 — captured before the geometry gate so a
    record-less or grid-less document still identifies itself). Returns
    (None, None) if cancelled.

    A line whose Post Mile column holds a zero-padded postmile is a rowA; its rowB
    is the NEXT line that carries BOTH the plain-integer intersection number AND a
    Description (CMP-AUD-058 — the integer alone let a numeric furniture line
    hijack a pending record). Page furniture between them (the table header
    repeated on every page, the cover pages) matches neither shape and is skipped,
    so a record split across a page boundary still pairs. Every unreconciled data
    shape surfaces in the counters above, never a silent drop."""
    rows = []
    doc_routes = set()          # the cover's own ROUTE parameter (049)
    pending_a = None            # a rowA (21 grid vals) awaiting its rowB
    last_rowb_top = None        # top of the last rowB — for the wrap check (056)
    orphans = 0
    leading_orphan_b = 0        # a rowB with no rowA pending (057)
    wrapped_rowb = 0            # a Description continuation we can't rejoin (056)
    old_pm_hits = 0
    vestigial = 0
    vestigial_cells = []        # (page, value) for the durable diagnostic (060)
    geom_divergent_pages = 0    # pages off the document median (062)
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        # The cover's ROUTE parameter is captured BEFORE the geometry gate so
        # even a record-less print (an intersection-less route) or a grid-less
        # document still identifies itself.
        for page in pdf.pages[:_COVER_SCAN_PAGES]:
            for _top, chars in _cluster_lines(page):
                cm = COVER_ROUTE_RE.match("".join(c["text"] for c in chars))
                if cm:
                    doc_routes.add(cm.group(1))
            if doc_routes:
                break
        win_a, win_b = _doc_windows(pdf, events)
        if events.is_cancelled():
            return None, None            # cancelled during the geometry scan (061)
        if win_a is None:
            return [], {"emitted": 0, "pages": n_pages, "orphans": 0,
                        "leading_orphan_b": 0, "wrapped_rowb": 0,
                        "geom_divergent_pages": 0, "no_grid": True,
                        "old_layout": False, "old_pm_hits": 0, "vestigial": 0,
                        "vestigial_cells": [], "doc_routes": sorted(doc_routes)}
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            if _page_geometry_diverges(page, win_a, win_b):
                # This page's own columns don't match the document median: parsing
                # it on the median would silently drop its rows (CMP-AUD-062).
                geom_divergent_pages += 1
            for top, chars in _cluster_lines(page):
                vals = _assign_columns(chars, win_a)
                if _is_rowA(vals):
                    if pending_a is not None:
                        orphans += 1        # previous rowA never got its rowB
                    pending_a = vals
                    last_rowb_top = None    # a new record — no wrap can precede it
                    if vals[20]:
                        vestigial += 1      # the dropped column grew data back?!
                        vestigial_cells.append((page_no, vals[20]))
                    continue
                if OLD_PM_RE.match(vals[1]) and LOCATION_RE.search(vals[3] or ""):
                    old_pm_hits += 1        # a PRE-update rowA (unpadded postmile)
                    continue
                vals_b = _assign_columns(chars, win_b)
                if _is_rowB(vals_b):
                    if pending_a is not None:
                        rows.append(_make_row(pending_a, vals_b))
                        pending_a = None
                    else:
                        leading_orphan_b += 1   # a rowB with no rowA (057)
                    last_rowb_top = top
                    continue
                # Neither rowA / legacy-rowA / rowB. A Description continuation of
                # the just-emitted rowB (within a wrap gap, text only in the desc
                # window, no intersection number) is a wrapped rowB the line-by-line
                # parser can't rejoin (CMP-AUD-056); anything else is page furniture.
                if (last_rowb_top is not None
                        and 0 < top - last_rowb_top <= _ROWB_WRAP_GAP
                        and (vals_b[_ROWB_DESC_WIN] or "").strip()
                        and not (vals_b[1] or "").strip()):
                    wrapped_rowb += 1
    if pending_a is not None:
        orphans += 1
    return rows, {"emitted": len(rows), "pages": n_pages, "orphans": orphans,
                  "leading_orphan_b": leading_orphan_b, "wrapped_rowb": wrapped_rowb,
                  "geom_divergent_pages": geom_divergent_pages, "no_grid": False,
                  "old_layout": not rows and old_pm_hits > 0,
                  "old_pm_hits": old_pm_hits, "vestigial": vestigial,
                  "vestigial_cells": vestigial_cells,
                  "doc_routes": sorted(doc_routes)}


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Intersection Detail workbook (same
    sheet name + 35 columns the Excel export uses)."""
    write_route_workbook(rows, out_path, sheet_name=SHEET_NAME, header=INTD_HEADER,
                         pdf_source_marker=True)


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
    layout knowledge: the per-PDF step (route from the cover's own "ROUTE :
    NNN" parameter, the filename token corroborating — CMP-AUD-049; the
    per-record Location cells canNOT identify the document, see
    COVER_ROUTE_RE; orphan reconciliation; the pre-update-layout refusal) and
    the ⚠-note / PARTIAL-escalation policy.
    """
    day = day or latest_output_day()
    in_dir = Path(input_dir) if input_dir else input_dir_for(day)
    out = Path(out_path) if out_path else out_path_for(day)
    conv = Path(converted_dir) if converted_dir else CONVERTED_DIR

    def convert_one(p, prefix, ev, ctx):
        name_m = ROUTE_FROM_NAME.search(p.stem)
        name_route = _norm_route(name_m.group(1)) if name_m else None
        rows, pstats = parse_pdf(str(p), ev)
        if rows is None:                             # cancelled mid-PDF
            return ("cancelled",)
        if pstats:
            ctx["orphans"] = ctx.get("orphans", 0) + pstats["orphans"]
            if pstats["orphans"]:
                ev.on_log(f"  WARNING: {pstats['orphans']} unpaired row(s) in {p.name} "
                          "(a record's two lines didn't pair) — see the log.")
            # Line/page reconciliation anomalies (CMP-AUD-056/057/062) — each a
            # data shape the parser can't reconcile; counted, never silently dropped.
            for key, what in (
                    ("leading_orphan_b", "complete rowB line(s) with no record to pair"),
                    ("wrapped_rowb",
                     "wrapped Description continuation(s) that couldn't be rejoined"),
                    ("geom_divergent_pages",
                     "page(s) whose column grid diverged from the document median")):
                n = pstats.get(key, 0)
                if n:
                    ctx[key] = ctx.get(key, 0) + n
                    ev.on_log(f"  WARNING: {n} {what} in {p.name} — see the log.")
            if pstats["vestigial"]:
                ctx["vestigial"] = ctx.get("vestigial", 0) + pstats["vestigial"]
                ctx.setdefault("vestigial_cells", []).extend(
                    pstats.get("vestigial_cells", []))
                ev.on_log(f"  WARNING: {pstats['vestigial']} value(s) in the dropped "
                          f"21st rowA column of {p.name} — the print layout may have "
                          "changed again; verify before relying on this output.")
            if pstats.get("old_pm_hits") and rows:
                # CMP-AUD-059: a mixed / transitional file — PRE-July-2026 unpadded
                # postmiles alongside current rows. The legacy rows are NOT parsed
                # by the current layout, so they'd drop silently; escalate loudly.
                ctx["mixed_edition"] = ctx.get("mixed_edition", 0) + pstats["old_pm_hits"]
                ev.on_log(f"  WARNING: {pstats['old_pm_hits']} PRE-July-2026 unpadded "
                          f"postmile row(s) in {p.name} alongside current rows — "
                          "legacy rows are not parsed by this layout; see the log.")
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
        route = reconcile_route_identity(
            p.name, name_route,
            [_norm_route(t) for t in pstats["doc_routes"]], ev, ctx,
            claim_desc="the cover's \"ROUTE : NNN\" parameter")
        if route is None:
            return ("skip",)
        return ("ok", route, rows)

    def finalize(result, ctx):
        orphans = ctx.get("orphans", 0)
        leading_orphan_b = ctx.get("leading_orphan_b", 0)
        wrapped_rowb = ctx.get("wrapped_rowb", 0)
        geom_div = ctx.get("geom_divergent_pages", 0)
        vestigial = ctx.get("vestigial", 0)
        mixed = ctx.get("mixed_edition", 0)
        notes = []
        if orphans:
            notes.append(f"⚠ {orphans} unpaired row line(s) — verify (see the log).")
        if leading_orphan_b:
            notes.append(f"⚠ {leading_orphan_b} rowB line(s) with no record to pair "
                         "— verify (see the log).")
        if wrapped_rowb:
            notes.append(f"⚠ {wrapped_rowb} wrapped Description continuation(s) not "
                         "rejoined — verify (see the log).")
        if vestigial:
            notes.append(f"⚠ {vestigial} value(s) in the dropped 21st rowA "
                         "column — the print layout may have changed; verify.")
        if mixed:
            notes.append(f"⚠ {mixed} PRE-July-2026 unpadded-postmile row(s) alongside "
                         "current rows — legacy rows not parsed; verify (see the log).")
        if geom_div:
            notes.append(f"⚠ {geom_div} page(s) whose column grid diverged from the "
                         "document median — verify (see the log).")
        result.summary_lines = notes + result.summary_lines
        # RR2-B1 / D18 parity with the HL-PDF consolidator: an unpaired record or
        # a failed PDF is invisible to the XLSX consolidator, so ESCALATE to a
        # producer-owned partial — the incomplete output must not be promoted /
        # cached / compared as complete.
        if orphans or ctx["failed"]:
            result.completion = outcome.PARTIAL
            result.skipped_inputs = max(result.skipped_inputs, orphans)
            result.failed_inputs = max(result.failed_inputs, len(ctx["failed"]))
        # CMP-AUD-056/057/059/060/062: line/page reconciliation anomalies are parse
        # ANOMALIES, not input-file counts (CMP-AUD-064) — they escalate COMPLETION
        # only and ride a structured parse-anomalies diagnostic, leaving
        # skipped/failed_inputs the file-level channels. All are 0 on the current
        # statewide corpus, so a clean run stays COMPLETE.
        anomalies = leading_orphan_b + wrapped_rowb + vestigial + mixed + geom_div
        if anomalies:
            result.completion = outcome.PARTIAL
            result.producer_extra = {
                **(result.producer_extra or {}),
                "parse_anomalies": {
                    "leading_orphan_rowb": leading_orphan_b,
                    "wrapped_rowb": wrapped_rowb,
                    "vestigial_cells": vestigial,
                    "legacy_layout_rows": mixed,
                    "geom_divergent_pages": geom_div,
                    "vestigial_samples": ctx.get("vestigial_cells", [])[:10],
                },
            }

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
