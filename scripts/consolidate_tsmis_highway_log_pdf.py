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
    import openpyxl  # noqa: F401 — the gate covers both the PDF and XLSX deps
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import highway_log_columns as hlc               # the corrected column labels
import outcome
from pdf_table_lib import (assign_columns, carried_line_crossings, char_lines,
                           contiguous_windows, median, norm_route,
                           reconcile_route_identity, run_pdf_conversion,
                           write_route_workbook)
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


# The canonical route-token normalizer (pdf_table_lib reconciled the 4 copies;
# this module's behavior is unchanged).
_norm_route = norm_route


def _cluster_lines(page):
    """Cluster the page's characters into logical lines — words for classifying
    the line, raw chars for column parsing (pdf_table_lib.char_lines)."""
    return char_lines(page, Y_TOLERANCE, WORD_GAP)


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

    edges_lo = [median([b[i]["x0"] for b in data_bands]) for i in range(N_PDF_COLS)]
    edges_hi = [median([b[i]["x1"] for b in data_bands]) for i in range(N_PDF_COLS)]
    windows = contiguous_windows(edges_lo, edges_hi)
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
    """Map each character of a data line to its column (pdf_table_lib)."""
    return assign_columns(chars, windows, WORD_GAP)


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


def _carried_line_misfits(line_chars, windows, row):
    """Misfit score for one data line parsed under CARRIED-FORWARD windows —
    0 certifies the carry for this line, >0 is the genuinely-risky carry:
      * intra-token window splits (`carried_line_crossings` — a drifted or
        foreign-table layout cuts printed tokens across column boundaries), and
      * a malformed Location cell (a boundary-0 shift moves whole tokens
        without cutting any — pulling MI into col0 or pushing the postmile
        out — so the emitted row's own key cell is re-checked against
        LOCATION_RE, which every correctly-placed data row satisfies)."""
    n = carried_line_crossings(line_chars, windows, WORD_GAP)
    if not (row[0] and LOCATION_RE.match(row[0])):
        n += 1
    return n


def parse_pdf(path, events, pdf_name=""):
    """Parse one TSMIS Highway Log PDF into TSMIS-format rows.

    Returns (route, rows, stats): `route` from the in-PDF cover (the
    document's own authoritative identity — the caller reconciles it against
    the filename token, CMP-AUD-049), `rows` a list of 31-column row lists in
    document order (all counties concatenated — county is a section marker, not a
    column), and `stats` a row-drop reconciliation dict (emitted, pages,
    skipped_no_geometry, stale_geometry_pages, carried_validated_pages).
    Returns (route, None, None) if cancelled mid-PDF.

    The reconciliation is REPORTING ONLY — the row-emit logic is unchanged, so
    the per-route output (and every PDF comparison) is byte-identical. A page
    with data rows but no 30-cell band of its own is parsed with the previous
    page's carried-forward geometry, then VALIDATED read-only
    (`_carried_line_misfits` == 0: no printed token split across windows AND
    the emitted Location still a clean postmile token). Validated pages count
    as `carried_validated_pages` and are ordinary; a page whose text does NOT
    fit the carried windows counts as `stale_geometry_pages` — the
    genuinely-risky case (a new table layout starting on a band-less page) —
    and escalates.
    """
    route = None
    rows = []
    last_row = None                   # description lines attach to this row
    skipped_no_geometry = 0           # data-looking lines dropped: no column band yet
    stale_geometry_pages = 0          # carried-geometry pages whose text did NOT fit
    carried_validated_pages = 0       # carried-geometry pages proven aligned

    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        page_windows = None           # carried forward if a page lacks a data band
        col0_right = None             # carried with the windows (star-line band test)
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return route, None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            derived = _page_column_windows(page)
            if derived is not None:
                page_windows, col0_right = derived
            page_has_own_geometry = derived is not None
            page_carried_lines = 0    # data lines parsed on a band-less page
            page_carried_splits = 0   # intra-token window splits among them

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
                # Cover page: "Route 006" pins the document's own route claim
                # (authoritative — the filename merely corroborates, 049).
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
                # Description. POSITIONAL since the 067 sweep: the totals stars
                # print at the LEFT MARGIN (x0 ≈ 35), but the print also carries
                # star-leading DESCRIPTIONS in the description band (x0 ≈ 156 —
                # "**** CODE ACCIDENTS TO" and three bare "*" rows statewide;
                # the vendor Excel and the TSN print both carry them, and TSN
                # normalizer v5 recovered its side, CMP-AUD-157). A star line
                # INSIDE the description band falls through to the ordinary
                # description-attach branch below and is CONSERVED; without
                # geometry yet (col0_right None) the conservative close-and-drop
                # stands.
                if texts[0].startswith("*") and (col0_right is None
                                                 or first_x0 < col0_right):
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
                    # No column geometry has been derived yet. A postmile-leading
                    # line here is a DATA row we cannot place — COUNT it so a
                    # silently-dropped row surfaces in the reconciliation instead of
                    # vanishing into a "clean" parse.
                    if (LOCATION_RE.match(texts[0])
                            or (len(texts) >= 2 and len(texts[0]) == 1
                                and texts[0].isalpha() and LOCATION_RE.match(texts[1]))):
                        skipped_no_geometry += 1
                        events.on_log(f"    WARNING: page {page_no} has a data-looking line "
                                      f"but no column geometry; dropped: "
                                      f"{' '.join(texts)[:60]}")
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
                    if not page_has_own_geometry:
                        # Data on a page with no column band of its own is parsed
                        # with the previous page's geometry — VALIDATE it instead
                        # of blanket-flagging: score the line's misfits (token
                        # splits + a malformed Location cell; 0 = the page shares
                        # the carried layout, the routine zebra-parity case).
                        # Classified once the page's lines are done.
                        page_carried_lines += 1
                        page_carried_splits += _carried_line_misfits(
                            line_chars, page_windows, row)
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

            # Classify the band-less page now that all its data lines are in:
            # a clean fit is an ordinary page (counted, one quiet per-file log
            # line from the caller); any token split across windows is the
            # genuinely-risky carry — name the page loudly, it escalates.
            if page_carried_lines:
                if page_carried_splits:
                    stale_geometry_pages += 1
                    events.on_log(f"    WARNING: page {page_no} has data rows but no "
                                  f"column band of its own, and its text does NOT fit "
                                  f"the carried geometry ({page_carried_splits} "
                                  f"misfit(s): tokens split across columns or a "
                                  f"malformed Location) — verify this page.")
                else:
                    carried_validated_pages += 1

    stats = {"emitted": len(rows), "pages": n_pages,
             "skipped_no_geometry": skipped_no_geometry,
             "stale_geometry_pages": stale_geometry_pages,
             "carried_validated_pages": carried_validated_pages}
    return route, rows, stats


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Highway Log workbook (same sheet
    name + 31 columns the Excel export uses)."""
    write_route_workbook(rows, out_path, sheet_name=SHEET_NAME, header=TSMIS_HEADER,
                         apply_tooltips=hlc.apply_header_tooltips,
                         decorate=hlc.write_legend_sheet,
                         pdf_source_marker=True)


# =============================================================================
# Entry point
# =============================================================================

def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Convert every TSMIS Highway Log PDF to a TSMIS-format per-route workbook,
    then combine them into one workbook (Route column added).

    `day` picks which export run folder ("<YYYY-MM-DD> <src>-<env>") of
    "Highway Log (PDF)" exports to read; None means the newest run folder, falling
    back to the legacy flat layout when no run folders exist yet — exactly like the
    Excel Highway Log consolidator.

    Console-free: progress via events.on_log, overwrite confirmed through the
    confirm_overwrite(path)->bool callback, a ConsolidateResult returned. Honors
    events.is_cancelled() between pages. The convert-loop skeleton lives in
    pdf_table_lib.run_pdf_conversion; this module supplies the layout knowledge:
    the per-PDF step (route from the PDF cover's own "Route NNN" claim, the
    filename token corroborating — CMP-AUD-049; parse reconciliation stats)
    and the ⚠-note / PARTIAL-escalation policy.
    """
    # input_dir/out_path/converted_dir are OPTIONAL overrides (the matrix points
    # them at an Export-Everything store folder + a scratch dir). When omitted the
    # behavior is byte-identical to before: the dated run folder + the shared dirs.
    day = day or latest_output_day()
    in_dir = Path(input_dir) if input_dir else input_dir_for(day)
    out = Path(out_path) if out_path else out_path_for(day)
    conv = Path(converted_dir) if converted_dir else CONVERTED_DIR

    def convert_one(p, prefix, ev, ctx):
        name_m = ROUTE_FROM_NAME.search(p.stem)
        name_route = _norm_route(name_m.group(1)) if name_m else None
        pdf_route, rows, pstats = parse_pdf(str(p), ev, pdf_name=p.name)
        if rows is None:                             # cancelled mid-PDF
            return ("cancelled",)
        if pstats:
            ctx["skipped"] = ctx.get("skipped", 0) + pstats["skipped_no_geometry"]
            ctx["stale_pages"] = (ctx.get("stale_pages", 0)
                                  + pstats["stale_geometry_pages"])
            ctx["carried_ok"] = (ctx.get("carried_ok", 0)
                                 + pstats["carried_validated_pages"])
            if pstats["carried_validated_pages"]:
                ev.on_log(f"    {pstats['carried_validated_pages']} band-less page(s) "
                          "validated against carried geometry.")
        if not rows:
            ev.on_log(f"{prefix} no highway-log data found; skipping")
            ctx["failed"].append(p.name)
            return ("skip",)
        route = reconcile_route_identity(
            p.name, name_route, [pdf_route] if pdf_route else [], ev, ctx,
            claim_desc="the cover's \"Route NNN\" line")
        if route is None:
            return ("skip",)
        return ("ok", route, rows)

    def finalize(result, ctx):
        skipped = ctx.get("skipped", 0)
        stale_pages = ctx.get("stale_pages", 0)
        carried_ok = ctx.get("carried_ok", 0)
        notes = []
        if skipped:
            notes.append(f"⚠ INCOMPLETE: {skipped} data line(s) dropped (no column "
                         "geometry) — see the log.")
        if stale_pages:
            notes.append(f"⚠ {stale_pages} page(s) whose text does NOT fit the "
                         "carried-forward geometry — verify those pages (see the log).")
        if carried_ok:
            notes.append(f"{carried_ok} band-less page(s) parsed with carried geometry "
                         "— every token fit its column (validated).")
        result.summary_lines = notes + result.summary_lines
        # RR2-B1 / D18: parse losses are invisible to the XLSX consolidator, so
        # ESCALATE to a producer-owned partial — a lossy output must not be
        # promoted / cached / compared as complete. Carried-geometry pages that
        # VALIDATE (every token intact under the carried windows — the normal
        # zebra-parity case) are ordinary output and do NOT escalate; only a
        # carry the page's own text contradicts does.
        if skipped or stale_pages or ctx["failed"]:
            result.completion = outcome.PARTIAL
            result.skipped_inputs = max(result.skipped_inputs, skipped)
            result.failed_inputs = max(result.failed_inputs, len(ctx["failed"]))

    return run_pdf_conversion(
        in_dir=in_dir, out=out, conv=conv, deps_ok=_DEPS_OK,
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        report_name=REPORT_NAME,
        banner_title="TSMIS Highway Log (PDF) Conversion",
        export_hint=("Export the 'Highway Log (PDF)' report first (it saves the "
                     "per-route PDFs there), then run this again."),
        unreadable_hint=("Are they the TSMIS Highway Log PDFs "
                         "(the 'Highway Log (PDF)' export)?"),
        converted_prefix="tsmis_highway_log_pdf",
        convert_one=convert_one, write_one=_write_route_workbook,
        finalize=finalize,
        consolidate_kwargs=dict(
            sheet_name=SHEET_NAME, report_name=REPORT_NAME,
            title="TSMIS Highway Log (PDF) Consolidation",
            header_override=hlc.HEADER, header_comment=hlc.comment_for,
            decorate_workbook=hlc.write_legend_sheet),
    )



if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
