"""Shared machinery for the table-PDF parsers/consolidators (v0.19.0 R2).

Before this module, the three PDF consolidators (TSMIS Highway Log, TSMIS
Intersection Detail, TSN Highway Log) + the TSN Highway Sequence loader each
carried verbatim copies of the same building blocks: the y-cluster line builder
(x4), the char->column assigner (x2), the median/contiguous column-window math
(x2), the route-token normalizer (x4, one divergent), the TSMIS-format
route-workbook writer (x3), and the ~110-line per-PDF convert loop (x2). This
module is those blocks, parameterized; each consolidator keeps ONLY its layout
knowledge (band collection, row classification/assembly) — which is what makes
a NEW PDF-sourced report (Highway Detail/Summary) a recipe instead of a port.

`norm_route` is THE canonical route-token normalizer, reconciling the four
copies deliberately:

  * the two TSMIS-PDF copies and the TSN Highway Sequence copy were already
    semantically identical (regex: int-collapse the digits, zero-pad to 3,
    upper-case the suffix) — adopting this changes nothing for them;
  * the TSN Highway Log copy used `zfill(3)`, which (a) never padded a SHORT
    SUFFIXED token ('5S' stayed '5S' while TSMIS prints '005S' — a latent
    row-misalignment) and (b) kept over-padded digits ('0001' stayed '0001').
    The reconciled form fixes both. Real district PDFs print 1-3 digit tokens
    (suffix included in the 'nnnX' form), where the two agree — but because the
    normalized route KEYS the stored TSN library, the highway_log TSN entry's
    `normalization_version` is bumped with this change (D2 auto-rebuild).

Console-free; pdfplumber/openpyxl objects come from the callers (which gate on
their own _DEPS_OK), so this module keeps the same lazy posture and never
imports pdfplumber itself.
"""
import re

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from compare_core import is_formula_injection   # shared formula-injection guard
from consolidate_xlsx_base import consolidate_xlsx
from events import ConsolidateResult, Events


# --------------------------------------------------------------------------- #
# tokens
# --------------------------------------------------------------------------- #
def norm_route(token):
    """'6' -> '006' (TSMIS zero-pads to 3 digits); suffixed routes ('101U',
    '005S') keep their letter and are upper-cased; anything else upper-cased
    as-is. See the module docstring for the 4-copy reconciliation."""
    m = re.fullmatch(r"(\d+)([A-Za-z]?)", token)
    if not m:
        return token.upper()
    return f"{int(m.group(1)):03d}{m.group(2).upper()}"


def median(values):
    """The parsers' median: upper-middle element (robust to a stray rect)."""
    s = sorted(values)
    return s[len(s) // 2]


# --------------------------------------------------------------------------- #
# line clustering + column assignment
# --------------------------------------------------------------------------- #
def cluster_by_top(items, y_tolerance):
    """Cluster x0/top-carrying items (chars or words) into logical lines,
    tolerating the small baseline jitter of a wrapped row. Returns
    [(anchor_top, [item, ... x0-sorted]), ...] in reading order."""
    clusters = []                     # [(anchor_top, [item, ...]), ...]
    for it in sorted(items, key=lambda i: (i["top"], i["x0"])):
        if clusters and abs(it["top"] - clusters[-1][0]) <= y_tolerance:
            clusters[-1][1].append(it)
        else:
            clusters.append((it["top"], [it]))
    return [(top, sorted(cs, key=lambda i: i["x0"])) for top, cs in clusters]


def words_from_chars(chars, word_gap):
    """Build word tokens from one x0-sorted char line: chars closer than
    `word_gap` fuse into one token."""
    words = []
    for c in chars:
        if words and c["x0"] - words[-1]["x1"] < word_gap:
            words[-1]["text"] += c["text"]
            words[-1]["x1"] = c["x1"]
        else:
            words.append({"text": c["text"], "x0": c["x0"], "x1": c["x1"]})
    return words


def char_lines(page, y_tolerance, word_gap):
    """Cluster the page's non-space characters into logical lines. Each line
    yields its word tokens (for classifying the line) AND the raw characters
    (for column parsing — adjacent columns can sit closer than any word
    tolerance, so values are assigned char by char, never word by word)."""
    chars = [c for c in page.chars if c["text"].strip()]
    return [(top, words_from_chars(cs, word_gap), cs)
            for top, cs in cluster_by_top(chars, y_tolerance)]


def assign_columns(chars, windows, word_gap):
    """Map each character of a data line to its column by horizontal center.
    Characters of one column abut (~0pt apart); a gap >= `word_gap` inside the
    same column means two tokens, kept apart with a space. Values are returned
    RAW (unstripped) — callers strip to taste."""
    vals = ["" for _ in windows]
    last_x1 = [None] * len(windows)
    for c in chars:                   # x-sorted by the clusterer
        center = (c["x0"] + c["x1"]) / 2
        for i, (lo, hi) in enumerate(windows):
            if lo <= center < hi:
                if vals[i] and c["x0"] - last_x1[i] >= word_gap:
                    vals[i] += " "
                vals[i] += c["text"]
                last_x1[i] = c["x1"]
                break
    return vals


def contiguous_windows(edges_lo, edges_hi):
    """Column x-windows from per-column median edges, made CONTIGUOUS (each
    boundary is the midpoint between adjacent cells; the first/last extend to
    ±infinity) so no data character can fall between two cells and be
    silently dropped."""
    n = len(edges_lo)
    windows = []
    for i in range(n):
        lo = float("-inf") if i == 0 else (edges_hi[i - 1] + edges_lo[i]) / 2
        hi = float("inf") if i == n - 1 else (edges_hi[i] + edges_lo[i + 1]) / 2
        windows.append((lo, hi))
    return windows


def carried_line_crossings(chars, windows, word_gap):
    """How badly a data line disagrees with CARRIED-FORWARD column windows:
    the number of intra-token window splits — consecutive characters closer
    than `word_gap` (one printed token) whose centers fall in different
    windows. A page that shares the carried table's layout scores 0 (a
    printed cell never straddles a column boundary); a drifted or
    foreign-table geometry cuts through tokens and scores immediately.
    Read-only, and it applies the same char-center window test as
    `assign_columns` — so a 0 score certifies that assignment placed every
    token of the line intact."""
    n = 0
    prev_win = None
    prev_x1 = None
    for c in chars:                   # x-sorted by the clusterer
        center = (c["x0"] + c["x1"]) / 2
        win = None
        for i, (lo, hi) in enumerate(windows):
            if lo <= center < hi:
                win = i
                break
        if (prev_win is not None and prev_x1 is not None
                and (c["x0"] - prev_x1) < word_gap and win != prev_win):
            n += 1
        prev_win, prev_x1 = win, c["x1"]
    return n


# --------------------------------------------------------------------------- #
# TSMIS-format per-route workbooks
# --------------------------------------------------------------------------- #
def write_route_workbook(rows, out_path, *, sheet_name, header,
                         row_values=None, apply_tooltips=None, decorate=None):
    """Write one route's rows as a TSMIS-format workbook (the same sheet name +
    columns the report's Excel export uses): the standard blue header row,
    frozen panes, per-column widths (Description wide), the formula-injection
    guard on every data cell, and the report's optional header tooltips /
    workbook decoration (e.g. the Highway Log Legend sheet)."""
    header_fill = PatternFill("solid", start_color="305496")
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(list(header))
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
    if apply_tooltips is not None:
        apply_tooltips(ws)                   # hover any header for its meaning
    ws.freeze_panes = "A2"
    for i, name in enumerate(header, start=1):
        ws.column_dimensions[get_column_letter(i)].width = \
            40 if name == "Description" else 12

    for row in rows:
        ws.append(row_values(row) if row_values is not None else row)
        # Neutralize any formula-looking text (e.g. a Description starting with
        # "=") so it can't execute when the workbook is opened.
        for cell in ws[ws.max_row]:
            if is_formula_injection(cell.value):
                cell.data_type = "s"
    if decorate is not None:
        decorate(wb)                         # e.g. a "Legend" tab
    wb.save(out_path)


# --------------------------------------------------------------------------- #
# the per-PDF convert loop (the TSMIS PDF consolidators' shared driver)
# --------------------------------------------------------------------------- #
def run_pdf_conversion(*, in_dir, out, conv, deps_ok, events, confirm_overwrite,
                       report_name, banner_title, export_hint, unreadable_hint,
                       converted_prefix, convert_one, write_one, finalize,
                       consolidate_kwargs):
    """The convert-every-PDF-then-combine driver both TSMIS PDF consolidators
    wrote verbatim: deps gate -> glob + the no-inputs error -> the EARLY
    overwrite confirm (before any parsing) -> banner -> clear the stale
    converted files -> the per-PDF loop (cancel, parse via `convert_one`,
    duplicate-route warning, write via `write_one`, the locked-file error) ->
    the none-readable error -> `consolidate_xlsx` -> the shared summary lines +
    the report's `finalize` (its ⚠ notes + producer-owned PARTIAL escalation).

    `convert_one(p, prefix, events, ctx)` owns the per-report step: route
    resolution, parse, its own stats in `ctx`, and its own skip logging (it
    appends skipped names to ctx["failed"]). It returns ("ok", route, rows),
    ("skip",), or ("cancelled",). `write_one(rows, out_file)` writes one route
    workbook. `finalize(result, ctx)` runs only on a successful combine.
    """
    events = events or Events()
    if not deps_ok:
        return ConsolidateResult(
            status="error",
            message="Required components are missing (pdfplumber, openpyxl).",
        )
    confirm = confirm_overwrite or (lambda _p: True)

    # Ensure the folder exists so the error below names a real, openable path.
    try:
        in_dir.mkdir(parents=True, exist_ok=True)
    except OSError:  # silent-ok: the no-inputs error below names the path
        pass

    pdfs = sorted(in_dir.glob("*.pdf"))
    if not pdfs:
        return ConsolidateResult(
            status="error",
            message=(f"No {report_name} files were found in:\n{in_dir}\n\n"
                     f"{export_hint}"),
        )

    # Confirm overwrite *before* spending time parsing PDFs.
    existed_at_confirm = out.exists()
    if existed_at_confirm and not confirm(out):
        return ConsolidateResult(status="cancelled",
                                 message="Cancelled. Existing file kept.")

    events.on_log("=" * 60)
    events.on_log(f"{banner_title} - {len(pdfs)} route PDF(s)")
    events.on_log("=" * 60)
    events.on_log("")

    # The combined workbook reflects exactly THIS run's PDFs: clear previously
    # converted files so routes removed from the input folder don't linger.
    conv.mkdir(parents=True, exist_ok=True)
    stale = list(conv.glob(f"{converted_prefix}_*.xlsx"))
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

    ctx = {"failed": [], "pdfs": len(pdfs)}
    converted = 0
    written = set()                  # guard against duplicate route across PDFs
    for i, p in enumerate(pdfs, 1):
        if events.is_cancelled():
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        prefix = f"[{i}/{len(pdfs)}] {p.name}"
        events.on_log(f"{prefix} parsing…")
        try:
            step = convert_one(p, prefix, events, ctx)
        except Exception as e:                       # noqa: BLE001 — one bad PDF must not sink the run
            events.on_log(f"{prefix} FAILED ({type(e).__name__}): {e}")
            ctx["failed"].append(p.name)
            continue
        if step[0] == "cancelled":
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        if step[0] == "skip":
            continue
        _tag, route, rows = step
        out_file = conv / f"{converted_prefix}_route_{route}.xlsx"
        if out_file.name in written:
            events.on_log(f"  WARNING: route {route} already converted from an earlier "
                          f"PDF; {p.name} replaces it (is the same route in the "
                          "folder twice?)")
        written.add(out_file.name)
        try:
            write_one(rows, out_file)
        except PermissionError:
            return ConsolidateResult(
                status="error",
                message=(f"Could not save {out_file.name}.\n\n"
                         "The file is probably open in Excel. Close it and try again."),
            )
        events.on_log(f"  route {route}: {len(rows)} rows -> {out_file.name}")
        converted += 1

    if converted == 0:
        return ConsolidateResult(
            status="error",
            message=(f"None of the PDFs in:\n{in_dir}\n\ncontained readable "
                     f"{report_name} data. {unreadable_hint}"),
        )

    events.on_log("")

    # Combine all converted per-route files with the shared XLSX core. P12 TOCTOU:
    # pass the REAL confirm + the existence we saw at the early prompt down into
    # consolidate_xlsx so its pre-replace gate (atomic_save_if) catches a destination
    # that APPEARED after that prompt — at the final os.replace — without
    # re-prompting for the already-confirmed pre-existing case.
    result = consolidate_xlsx(
        input_dir=conv, out_path=out,
        events=events, confirm_overwrite=confirm, existed_at_confirm=existed_at_confirm,
        **consolidate_kwargs)
    if result.status == "ok":
        failed = ctx["failed"]
        result.summary_lines = [
            f"Route PDFs:   {len(pdfs) - len(failed)} converted"
            + (f", {len(failed)} failed {failed}" if failed else ""),
            f"Route files:  {converted} (in {conv})",
        ] + result.summary_lines
        # RR2-B1 / D18: every converted per-route file may have combined cleanly
        # (consolidate_xlsx -> complete), yet the PDF->row parse dropped data.
        # Those losses are NOT visible to the XLSX consolidator, so the report's
        # finalize ESCALATES to a producer-owned partial — a lossy output must
        # not be promoted / cached / compared as complete.
        finalize(result, ctx)
    return result
