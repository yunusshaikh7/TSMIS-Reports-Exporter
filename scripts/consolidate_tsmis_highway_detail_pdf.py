"""Convert TSMIS Highway Detail PDFs into TSMIS-format Excel and combine.

The TSMIS "Highway Detail (PDF)" export (report 7b — the site's Print layout
saved via `page.pdf()`) renders the report as the printed TASAS two-line-per-
record table. Like Highway Log and Intersection Detail, the PDF and the Excel
export are two renders of the same data that CAN disagree, so this consolidator
parses those per-route PDFs into the SAME 34-column TSMIS Highway Detail format
the Excel export produces, so:
  * the combined workbook lines up column-for-column with the Excel-consolidated
    workbook and the normalized TSN library (for the TSMIS-PDF vs TSN comparison),
  * and it can be diffed against the Excel export to pinpoint exactly which
    cells the two sources disagree on (the TSMIS-PDF vs TSMIS-Excel check).

The inputs ARE this app's own exports: the "Highway Detail (PDF)" export saves
the per-route PDFs (highway_detail_route_<ROUTE>.pdf) to
output/<run>/highway_detail_pdf/, so this consolidator reads that export folder
day-aware, exactly like the Excel consolidator. Converts each PDF to a per-route
workbook (scratch, in output/tsmis_highway_detail_pdf/) and writes one combined
workbook to that run's consolidated/ folder.

PARSING — derived-grid based, like the Intersection Detail PDF consolidator:
TWO physical table rows make ONE record, and only the zebra-shaded records
(`hd-shaded`, idx % 2 === 0) carry cell rectangles. The two lines have
DIFFERENT column geometry (`hd_renderRecord`):
  * line 1 — 10 cells: Post Mile(3) Length(2) Date of Record(2) HG AC
    Acc-Cont Eff(2) City(2) RU RU Eff(2) + an 11-column empty tail;
  * line 2 — 25 cells: Description(3) NA + the 9 Left-Roadbed, 5 Median and
    9 Right-Roadbed attribute cells.
So TWO window sets are derived from the shaded bands (the 10-rect line-1 bands
and the 25-rect line-2 bands; the print layout is one table, so the widths are
uniform across pages) and EVERY text line is assigned to them: a line whose
first line-1 window holds a postmile token is a line 1; the line after it is
its line 2. District-county-route group rows ('11 IMP 007', one colspan-27
cell) and the page furniture never match the postmile test and are skipped.

No value normalization happens here: the PDF already carries the native TSMIS
formats, so values are written through verbatim. The comparison engine applies
any normalization at compare time, exactly as for the Excel side.

Console-free like the other consolidators: progress via events.on_log,
overwrite confirmed through the callback, cancel honored between pages,
ConsolidateResult returned. The console UX lives in cli.run_consolidate_cli.
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

from highway_detail_columns import HEADER as HD_HEADER
import highway_detail_columns as hdc
import outcome
from pdf_table_lib import (assign_columns, cluster_by_top, contiguous_windows,
                           median, norm_route, reconcile_route_identity,
                           run_pdf_conversion, write_route_workbook)
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

# These PDFs ARE produced by this app's "Highway Detail (PDF)" export (report
# 7b), saved to output/<run>/highway_detail_pdf/. So this consolidator reads
# that EXPORT folder, day-aware, exactly like the Excel consolidator.
SUBDIR = "highway_detail_pdf"
FILENAME = "tsmis_highway_detail_pdf_consolidated.xlsx"

# Legacy flat-layout location (pre-dated exports, or a manual drop on a machine
# that can't run the export itself); used when no dated output/<run>/ folders exist.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
CONVERTED_DIR = OUTPUT_ROOT / "tsmis_highway_detail_pdf"   # scratch per-route wb
OUT_PATH = OUTPUT_ROOT / FILENAME                          # legacy flat output

# Friendly report name for user-facing messages (UI-neutral).
REPORT_NAME = "TSMIS Highway Detail (PDF)"

# File pattern the GUI uses to preview how many inputs a folder holds.
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"

# Must match the Highway Detail export exactly (sheet name AND header), so the
# converted files consolidate with the same core and the combined workbook is
# column-compatible with the Excel export and the normalized TSN library.
SHEET_NAME = "Highway Detail"


def input_dir_for(day):
    """The 'Highway Detail (PDF)' export PDFs for `day` (a run-folder name);
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

N_COLS_L1 = 10           # line 1's cells (incl. the wide empty tail cell)
N_COLS_L2 = 25           # line 2's cells (Description + NA + 23 attribute cells)
CELL_MIN_W = 3           # ignore hairline / spacer rects when finding shaded bands
CELL_MIN_H = 3
CELL_MAX_H = 40          # a data cell spans at most a few text lines (wraps)
Y_TOLERANCE = 3          # chars within this y-distance form one logical text line
WORD_GAP = 1.5           # x-gap that opens a new token inside one column
# Text lines closer than this belong to ONE physical table row: when a narrow
# cell WRAPS (a squeezed '00-01-01' date renders '00-01-' over '01'; a long
# description over two lines), the row becomes several text lines ~5-6pt apart,
# while DISTINCT rows sit >=9.7pt apart (the print line height). Grouping by
# this gap reassembles a wrapped row before classification, so a wrap fragment
# can never be consumed as a record's second line.
ROW_GAP = 7.5

# A line 1's first window holds the glued postmile token ('S000.000',
# '000.000E', 'R012.243R'). Header furniture, DCR group rows ('11 IMP 007') and
# description lines never match it.
PM_TOKEN_RE = re.compile(r"^[A-Z]{0,2}\d{1,3}\.\d{3}[A-Z]{0,2}$")
# Line 1's second cell (the record length), used by _is_line1 to tell the
# fallback-grid "PM LEN" merge from an OUTDENTED equate description that also
# STARTS with a PM-shaped token ('R42.401 LT EQ 43.185 …' — the 7.9/ARS census).
LEN_TOKEN_RE = re.compile(r"^\d{3}\.\d{3}$")
# A TASAS YY-MM-DD effective date. Tested on the group's RAW TEXT (not the
# window-merged values — a page whose grid sits off the printed columns can
# split '15-10-29' across windows) as the line-2 FAST accept; the page header's
# '2026-07-07' is digit-adjacent, which the lookarounds reject.
DATE_TOKEN_RE = re.compile(r"(?<!\d)\d{2}-\d{2}-\d{2}(?!\d)")
# Furniture a date-less group can be, censused on the 7.9/ARS prints (the only
# things that ever appear between a record's two lines): the reprinted THEAD's
# lines (a continuation page), its one-letter N/A residue, the DCR group rows,
# and the page header/footer. EVERYTHING else following a line 1 is that
# record's line 2 — including the date-less SPARSE rows (roadbed blocks with
# codes but no effective dates) the old always-has-a-date assumption dropped.
# Vocabulary is matched on the SPACELESS raw text; words that also occur in
# real descriptions (CITY, RECORD, LENGTH alone) are deliberately absent —
# a false furniture match only orphans loudly, but a THEAD swallowed as data
# would corrupt silently, so the distinctive multi-token strings below are
# each unique to the header.
THEAD_RE = re.compile(r"POSTMILE|DESCRIPTION|EFF-|ACC-|ROADBED|MEDIAN|DATEOF|"
                      r"T-W|WDA|S#S")
DCR_ROW_RE = re.compile(r"^\d{2}[A-Z]{2,4}\.?\d{1,3}[A-Z]?$")
PAGE_FURNITURE_RE = re.compile(r"RefDate:|Page\d+$")
# The document's own route claim: the data pages' header banner ("Ref Date:
# 2026-07-10 Route 004 Page 44" — matched on the SPACELESS group text like the
# other furniture regexes; censused on the 7.9/ARS statewide set, suffixed
# routes print as one token). CMP-AUD-049: this in-document claim, not the
# filename, is the authoritative identity.
BANNER_ROUTE_RE = re.compile(r"^RefDate:.*?Route([0-9]+[A-Za-z]?)Page\d+$")
# Route token out of "highway_detail_route_<ROUTE>.pdf".
ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]?)", re.IGNORECASE)

_norm_route = norm_route


def _cluster_lines(page):
    """Cluster the page's non-space characters into logical lines. Returns
    [(top, [chars sorted by x0]), ...]."""
    return cluster_by_top((c for c in page.chars if c["text"].strip()), Y_TOLERANCE)


def _row_groups(page):
    """The page's text lines re-grouped into PHYSICAL TABLE ROWS: consecutive
    lines whose tops are within ROW_GAP form one group (a wrapped cell's
    fragments sit ~5-6pt from the row's other lines; distinct rows are >=9.7pt
    apart). Returns [[(top, chars), ...], ...] in reading order — a group with
    one line is the ordinary unwrapped row."""
    groups = []
    for top, chars in _cluster_lines(page):
        if groups and top - groups[-1][-1][0] <= ROW_GAP:
            groups[-1].append((top, chars))
        else:
            groups.append([(top, chars)])
    return groups


def _join_wrap(a, b):
    """Join two wrap fragments of one cell: HTML wraps AFTER a hyphen (the
    '00-01-'+'01' date split — rejoin bare) or AT a space (swallowed by the
    wrap — rejoin with one space)."""
    if not a:
        return b
    if not b:
        return a
    return a + b if a.endswith("-") else f"{a} {b}"


def _group_values(group, windows):
    """The group's cell values on `windows`: each text line is assigned
    separately, then each window's fragments are joined top-to-bottom (see
    _join_wrap) — so a wrapped cell reads as its full value while single-line
    rows pass through unchanged."""
    vals = _assign(group[0][1], windows)
    for _top, chars in group[1:]:
        nxt = _assign(chars, windows)
        vals = [_join_wrap(a, b) for a, b in zip(vals, nxt)]
    return vals


def _page_bands(page):
    """This page's zebra-shaded cell bands, grouped by rect count:
    {n_rects: [band, ...]} where each band is x0-sorted."""
    by_top = defaultdict(list)
    for r in page.rects:
        w = r["x1"] - r["x0"]
        h = r["bottom"] - r["top"]
        if CELL_MIN_W < w < page.width - 10 and CELL_MIN_H < h < CELL_MAX_H:
            by_top[round(r["top"])].append(r)
    out = defaultdict(list)
    for cells in by_top.values():
        out[len(cells)].append(sorted(cells, key=lambda r: r["x0"]))
    return out


def _windows_from_bands(bands, n_cols):
    """Contiguous column windows from the median cell edges of `bands`
    (each a band of exactly `n_cols` x0-sorted rects), or None when empty."""
    if not bands:
        return None
    lo = [median([b[i]["x0"] for b in bands]) for i in range(n_cols)]
    hi = [median([b[i]["x1"] for b in bands]) for i in range(n_cols)]
    return contiguous_windows(lo, hi)


def _page_windows(page):
    """(win1, win2) — the line-1 (10-cell) and line-2 (25-cell) column windows
    derived from THIS page's own shaded bands, or (None, None) for a page with
    no full band of either shape (the cover/legend pages).

    PER PAGE is essential: each print page is its OWN table whose auto layout
    sizes the columns to THAT page's content, so the geometry varies from page
    to page (on route 001 the second column's x0 ranges ~156→297pt across
    pages) — a document-wide median fits no page. Every DATA page has both
    band shapes (15 records per page, zebra-shaded by global record index, so
    at least ~7 of them carry rects); the one theoretical exception is a
    final page holding a single UNSHADED record, which the caller covers with
    the document-median fallback (logged)."""
    bands = _page_bands(page)
    return (_windows_from_bands(bands.get(N_COLS_L1), N_COLS_L1),
            _windows_from_bands(bands.get(N_COLS_L2), N_COLS_L2))


def _document_windows(pdf, n_cols):
    """Document-median windows across every page's bands — ONLY the fallback
    for a data page with no shaded band of its own (see _page_windows)."""
    bands = []
    for page in pdf.pages:
        bands.extend(_page_bands(page).get(n_cols, []))
    return _windows_from_bands(bands, n_cols)


def _assign(chars, windows):
    """Map each character of a line to its column (pdf_table_lib), stripped."""
    return [v.strip() for v in assign_columns(chars, windows, WORD_GAP)]


def _group_text(group):
    """The group's SPACELESS raw text (each line's characters joined, lines
    concatenated) — what the furniture regexes and the raw-text date accept
    match on, independent of any window grid."""
    return "".join("".join(c["text"] for c in chars).replace(" ", "")
                   for _top, chars in group)


def _is_line1(vals):
    """A record's FIRST line carries the postmile token in its first window —
    ALONE (the ordinary case), or merged with the Length on the document-median
    FALLBACK grid of a band-less page ('000.000L 000.000', window 1 then
    empty). A postmile-shaped first TOKEN is NOT enough on its own: an
    OUTDENTED equate DESCRIPTION also starts with one ('R42.401 LT EQ 43.185 ,
    PM R42401BK=43185E AH' — the 7.9/ARS census), but its text runs on where a
    real line 1 has the Length; treating it as a line 1 orphaned the real
    record AND made the description a phantom record."""
    v = (vals[0] or "").strip()
    if PM_TOKEN_RE.match(v):
        return True
    first, _, rest = v.partition(" ")
    if not (PM_TOKEN_RE.match(first) and rest):
        return False
    # Window 0 carries extra text: genuine only when that text is the merged
    # LENGTH column ('PM LEN …' on the over-wide fallback grid); an equate
    # description's text runs on as WORDS, and on the ordinary grid it also
    # spills into window 1, which a real merged line 1 leaves empty.
    win1 = (vals[1] or "") if len(vals) > 1 else ""
    return bool(LEN_TOKEN_RE.match(rest.split(" ", 1)[0]) and not win1.strip())


def _make_row(a, b):
    """Assemble the 34-column Highway Detail row from line 1's 10 window values
    and line 2's 25. Line 1 windows 0..8 are Post Mile .. RU Eff (window 9 is
    the empty tail); line 2 windows 0..24 are Description, NA, then the 9 Left-
    Roadbed, 5 Median and 9 Right-Roadbed cells — exactly the export's order.
    On the fallback grid window 0 can hold 'PM LEN' merged with window 1 empty
    (see _is_line1) — split the postmile back off so the row stays keyable."""
    a = [v or None for v in a]
    b = [v or None for v in b]
    if a[0] and " " in a[0] and not PM_TOKEN_RE.match(a[0]) and not a[1]:
        pm, rest = a[0].split(" ", 1)
        if PM_TOKEN_RE.match(pm):
            a[0], a[1] = pm, rest
    return a[0:9] + b[0:25]


def parse_pdf(path, events):
    """Parse one TSMIS Highway Detail PDF into 34-column TSMIS-format rows.

    Returns (rows, stats): `rows` in document order, `stats` a reconciliation
    dict (emitted, pages, orphans — always 0 now, kept for the reconciliation
    contract; `single_line` = records whose print carried NO second line,
    emitted with a blank attribute tail; `fallback_pages` = data pages parsed
    on the document-median fallback grid; `no_grid` when no page yielded any
    geometry; `doc_routes` = the distinct routes the page banners claim for
    the document itself, CMP-AUD-049 — captured before the geometry gate, so
    a grid-less document still identifies itself). Returns (None, None) if
    cancelled.

    The two window sets are derived PER PAGE from that page's own shaded bands
    (each print page is its own auto-layout table — see _page_windows). The
    page's text lines are re-grouped into PHYSICAL rows first (_row_groups —
    a wrapped cell's fragments rejoin their row, see _group_values); a row
    group whose line-1 shape matches (_is_line1 — the postmile ALONE in window
    0, or postmile+Length on the fallback grid) is a line 1, and the NEXT
    non-furniture row group is its line 2, read on the line-2 grid. A print
    section taller than one physical page splits MID-RECORD (the browser
    repeats the table header on the continuation page), so a pending line 1
    carries across the page boundary; the furniture tests (THEAD_RE /
    DCR_ROW_RE / PAGE_FURNITURE_RE on the raw text) keep the reprinted header
    from being swallowed as its line 2. The old rule — "a genuine line 2
    always carries a TASAS date" — is now only the FAST accept: the 7.9/ARS
    census found real records whose roadbed blocks print codes but no
    effective dates at all, and pages whose window grid splits a date across
    columns; both parse now."""
    rows = []
    doc_routes = set()                 # the pages' own route claims (049)
    orphans = 0
    single_line = 0
    fallback_pages = []
    doc_win = {}                       # lazy document-median fallback per shape
    pending_1 = None                   # carries across pages (mid-record splits)

    def _flush_pending():
        # A line 1 whose record printed NO second line at all (description and
        # every attribute cell empty — censused on the 7.9/ARS prints): emit it
        # with a blank attribute line rather than dropping the record. Counted
        # separately so the summary can say so; the PDF↔Excel check remains the
        # arbiter of whether the blank tail matches the Excel export.
        nonlocal pending_1, single_line
        if pending_1 is not None:
            rows.append(_make_row(pending_1, [""] * N_COLS_L2))
            single_line += 1
            pending_1 = None

    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        any_grid = False
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            # The page banner carries the document's own route claim —
            # captured BEFORE the geometry gate so even a page that yields no
            # parseable grid still identifies itself (CMP-AUD-049). The main
            # row loop below is untouched: banner groups remain page
            # furniture there, exactly as before.
            groups = _row_groups(page)
            for group in groups:
                bm = BANNER_ROUTE_RE.match(_group_text(group))
                if bm:
                    doc_routes.add(bm.group(1))
            win1, win2 = _page_windows(page)
            if win1 is None or win2 is None:
                # No shaded band on this page: the cover/legend pages (no data
                # lines either — harmless), or a page whose only record(s) are
                # unshaded. Try the document-median fallback so those records
                # aren't silently dropped; record which pages needed it.
                if "w1" not in doc_win:
                    doc_win["w1"] = _document_windows(pdf, N_COLS_L1)
                    doc_win["w2"] = _document_windows(pdf, N_COLS_L2)
                win1 = win1 or doc_win["w1"]
                win2 = win2 or doc_win["w2"]
                if win1 is None or win2 is None:
                    continue           # nothing derivable anywhere yet
                used_fallback = True
            else:
                used_fallback = False
                any_grid = True
            page_rows = 0
            in_thead = False           # inside a (reprinted) table header run
            for group in groups:
                vals1 = _group_values(group, win1)
                if _is_line1(vals1):
                    _flush_pending()   # the previous record had no line 2
                    pending_1 = vals1
                    in_thead = False
                elif pending_1 is not None:
                    # A record's line 2 is WHATEVER follows its line 1 except
                    # the censused furniture: the reprinted THEAD (+ its bare
                    # N/A residue line), DCR group rows, and the page
                    # header/footer. A TASAS date anywhere in the RAW text is
                    # the fast accept (a mis-aligned window grid can split a
                    # date, so the merged values can't carry this test); a
                    # date-LESS group is accepted too once the furniture tests
                    # pass — the sparse rows (roadbed codes but no effective
                    # dates) the old always-has-a-date assumption dropped.
                    raw = _group_text(group)
                    if not DATE_TOKEN_RE.search(raw):
                        if THEAD_RE.search(raw):
                            in_thead = True
                            continue
                        if in_thead and len(raw) <= 2 and raw.isalpha():
                            continue   # the THEAD's own N/A column residue
                        if (PAGE_FURNITURE_RE.search(raw)
                                or DCR_ROW_RE.match(raw)):
                            continue
                    in_thead = False
                    vals2 = _group_values(group, win2)
                    rows.append(_make_row(pending_1, vals2))
                    pending_1 = None
                    page_rows += 1
            if used_fallback and page_rows:
                fallback_pages.append(page_no)
        _flush_pending()               # a line 1 dangling at the document end
        if not any_grid and not rows:
            return [], {"emitted": 0, "pages": n_pages, "orphans": 0,
                        "single_line": 0, "fallback_pages": [], "no_grid": True,
                        "doc_routes": sorted(doc_routes)}
    return rows, {"emitted": len(rows), "pages": n_pages, "orphans": orphans,
                  "single_line": single_line, "fallback_pages": fallback_pages,
                  "doc_routes": sorted(doc_routes)}


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Highway Detail workbook (same
    sheet name + 34 columns the Excel export uses, tooltips + Legend included)."""
    write_route_workbook(rows, out_path, sheet_name=SHEET_NAME, header=HD_HEADER,
                         apply_tooltips=hdc.apply_header_tooltips,
                         decorate=hdc.write_legend_sheet,
                         pdf_source_marker=True)


# =============================================================================
# Entry point
# =============================================================================

def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Convert every TSMIS Highway Detail PDF to a TSMIS-format per-route
    workbook, then combine them into one workbook (Route column added).

    `day` picks which export run folder of "Highway Detail (PDF)" exports to
    read; None means the newest run folder, falling back to the legacy flat
    layout. Console-free; honors events.is_cancelled() between pages. The
    convert-loop skeleton lives in pdf_table_lib.run_pdf_conversion; this module
    supplies the layout knowledge (route from the page banner's own "Ref Date:
    … Route NNN Page N" claim, the filename token corroborating —
    CMP-AUD-049; orphan reconciliation) and the ⚠-note / PARTIAL-escalation
    policy."""
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
            ctx["single_line"] = (ctx.get("single_line", 0)
                                  + pstats.get("single_line", 0))
            if pstats["orphans"]:
                ev.on_log(f"  WARNING: {pstats['orphans']} unpaired row(s) in {p.name} "
                          "(a record's two lines didn't pair) — see the log.")
            if pstats.get("single_line"):
                ev.on_log(f"  note: {pstats['single_line']} record(s) in {p.name} "
                          "printed no attribute line — kept with blank attribute "
                          "columns.")
            if pstats.get("fallback_pages"):
                # A data page with no shaded band of its own parsed on the
                # document-median grid — worth eyeballing in the PDF↔Excel check.
                ev.on_log(f"  note: page(s) {pstats['fallback_pages']} of {p.name} "
                          "parsed on the fallback column grid (no shaded band).")
        if not rows:
            ev.on_log(f"{prefix} no highway data found; skipping")
            ctx["failed"].append(p.name)
            return ("skip",)
        route = reconcile_route_identity(
            p.name, name_route,
            [_norm_route(t) for t in pstats["doc_routes"]], ev, ctx,
            claim_desc="the page banner's \"Ref Date: … Route NNN Page N\"")
        if route is None:
            return ("skip",)
        return ("ok", route, rows)

    def finalize(result, ctx):
        orphans = ctx.get("orphans", 0)
        notes = []
        if orphans:
            notes.append(f"⚠ {orphans} unpaired row line(s) — verify (see the log).")
        if ctx.get("single_line"):
            # An FYI, not an escalation: a record whose print carries no second
            # line is emitted with a blank attribute tail; the PDF↔Excel check
            # is the arbiter of whether that matches the Excel export.
            notes.append(f"{ctx['single_line']} record(s) printed no attribute "
                         "line (kept with blank attribute columns).")
        result.summary_lines = notes + result.summary_lines
        # An unpaired record or a failed PDF is invisible to the XLSX
        # consolidator, so ESCALATE to a producer-owned partial — the incomplete
        # output must not be promoted / cached / compared as complete.
        if orphans or ctx["failed"]:
            result.completion = outcome.PARTIAL
            result.skipped_inputs = max(result.skipped_inputs, orphans)
            result.failed_inputs = max(result.failed_inputs, len(ctx["failed"]))

    return run_pdf_conversion(
        in_dir=in_dir, out=out, conv=conv, deps_ok=_DEPS_OK,
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        report_name=REPORT_NAME,
        banner_title="TSMIS Highway Detail (PDF) Conversion",
        export_hint=("Export the 'Highway Detail (PDF)' report first (it saves "
                     "the per-route PDFs there), then run this again."),
        unreadable_hint=("Are they the TSMIS Highway Detail PDFs "
                         "(the 'Highway Detail (PDF)' export)?"),
        converted_prefix="tsmis_highway_detail_pdf",
        convert_one=convert_one, write_one=_write_route_workbook,
        finalize=finalize,
        consolidate_kwargs=dict(
            sheet_name=SHEET_NAME, report_name=REPORT_NAME,
            title="TSMIS Highway Detail (PDF) Consolidation",
            header_comment=hdc.comment_for,
            decorate_workbook=hdc.write_legend_sheet),
    )


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
