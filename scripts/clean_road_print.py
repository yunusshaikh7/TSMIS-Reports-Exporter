"""Read one Clean Road print (the site's `clh_/cli_/clr_printAll` PDF) back into
the Excel export's rows (v0.48.0).

The print is a cover page followed by ONE HTML table rendered landscape and
scale-to-fit: every printed column is a cell rectangle, the header row is the
first row of cells inside the table frame, and Chrome repeats it on every
page. Only the columns the site has a source for are printed, labelled by the
site's own two-line rule (`clean_road_columns.printed_label`). The text is
tiny — 1.4–1.7 pt on Clean Road Highway's 52 printed columns, 4.7 pt on Ramp's
21 — so this reader never clusters words by gap. It works from the vector
structure instead:

  * columns  = the header row's cell rectangles (exact x ranges, per page);
  * columns are NAMED by reading each header cell's two text lines back and
    reversing the site's label rule — an unknown label refuses the file;
  * rows     = glyphs clustered by baseline with a tolerance of 0.35 x the font
    size. Rows sit 1.8–2.5 font sizes apart, so neighbouring records can never
    merge (pdfplumber's fixed 3-pt default does merge them on the dense routes);
  * cells    = each glyph's x-centre against the column ranges; a glyph outside
    every column refuses the file;
  * spaces   = from the glyph gaps. pdfium drops most space glyphs at this size,
    so a word break is a gap wider than 0.11 em — censused over 1.3 million
    glyph pairs: in-word gaps are -0.06..+0.03 em, word breaks 0.19..0.21 em.

Text is read with pypdfium2 (bundled since v0.21.0 for the evidence renderer):
the Clean Road Highway statewide set is ~430 dense pages, which pdfplumber reads
in ~22 minutes and pdfium in ~2.5, with the identical result. Censused on the
whole 2026-10-02 statewide pull: every one of the 51,735 / 16,461 / 15,214
rows reads back cell-for-cell equal to the Excel export, except where the
Excel keeps a run of spaces the HTML print collapses (the Ramp Detail print
class) or a literal `_x000d_` escape the print omits.

Console-free; raises ValueError naming the page and problem.
"""
import re
import statistics
import threading
from bisect import bisect_right

try:
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_c
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import clean_road_columns as crc

# A word break is a glyph gap wider than this many ems (see the docstring).
WORD_GAP_EM = 0.11
# Glyphs whose baselines sit within this many font sizes are one text line.
ROW_TOLERANCE_EM = 0.35
# A table cell rectangle (not the page frame, not a hairline border).
_CELL_MIN_H, _CELL_MAX_H, _CELL_MAX_W = 1.0, 60.0, 400.0
_FRAME_MIN_W = 400.0
_COVER_ROUTE_RE = re.compile(r"LOCATION CRITERIA:\s*ROUTE\s+([0-9A-Z]+)", re.I)
_WS_RE = re.compile(r"\s+")

# pdfium is not thread-safe; the app runs one consolidation at a time, but the
# reader is cheap to serialize so two callers can never interleave inside it.
_PDFIUM_LOCK = threading.Lock()


class PrintRead:
    """One print, read: the cover's route claim, the printed column keys (in
    print order) and every record as a list in `spec.header` order (columns
    the print doesn't carry are '')."""

    def __init__(self, route_claim, printed, rows, pages):
        self.route_claim = route_claim
        self.printed = printed
        self.rows = rows
        self.pages = pages


def _page_parts(page):
    """(glyphs, path rectangles) for one page in top-down coordinates."""
    height = page.get_height()
    tp = page.get_textpage()
    try:
        n = tp.count_chars()
        text = tp.get_text_range(0, n) if n else ""
        glyphs = []
        for i in range(n):
            ch = text[i] if i < len(text) else ""
            if ch in ("", "\r", "\n") or ch.isspace():
                continue          # spaces are re-derived from the gaps
            if pdfium_c.FPDFText_IsGenerated(tp.raw, i):
                continue
            left, bottom, right, top = tp.get_charbox(i, loose=True)
            glyphs.append((ch, left, right, height - top, height - bottom,
                           pdfium_c.FPDFText_GetFontSize(tp.raw, i)))
    finally:
        tp.close()
    rects = []
    for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_PATH]):
        left, bottom, right, top = obj.get_bounds()
        rects.append((left, right, height - top, height - bottom))
    return glyphs, rects


def _lines(glyphs, tol):
    """Glyphs grouped into text lines by their top edge, top-down."""
    out, cur, ref = [], [], None
    for g in sorted(glyphs, key=lambda g: (g[3], g[1])):
        if ref is None or abs(g[3] - ref) <= tol:
            cur.append(g)
            ref = g[3] if ref is None else ref
        else:
            out.append(cur)
            cur, ref = [g], g[3]
    if cur:
        out.append(cur)
    return out


def _text(glyphs):
    """One cell's text: glyphs in x order, a space at every word-break gap."""
    parts, prev = [], None
    for g in sorted(glyphs, key=lambda g: g[1]):
        if prev is not None and g[1] - prev[2] > WORD_GAP_EM * (g[5] or 1.0):
            parts.append(" ")
        parts.append(g[0])
        prev = g
    return _WS_RE.sub(" ", "".join(parts)).strip()


def _cover_route(page):
    tp = page.get_textpage()
    try:
        text = tp.get_text_range()
    finally:
        tp.close()
    m = _COVER_ROUTE_RE.search(text or "")
    return m.group(1).upper() if m else None


def _header(rects, glyphs, tol, by_label, page_no, name):
    """The header row's column ranges + keys for one page."""
    frames = [r for r in rects if r[1] - r[0] >= _FRAME_MIN_W and r[2] >= 0]
    cells = [r for r in rects
             if _CELL_MIN_H < r[3] - r[2] < _CELL_MAX_H and r[1] - r[0] < _CELL_MAX_W]
    if not frames or not cells:
        raise ValueError(f"{name}: page {page_no} has no table — not a Clean Road print")
    top = min(r[2] for r in frames)
    hdr = sorted((r for r in cells if abs(r[2] - top) < 0.05), key=lambda r: r[0])
    if not hdr:
        raise ValueError(f"{name}: page {page_no} has no header row")
    bottom = max(r[3] for r in hdr)
    edges = [(r[0], r[1]) for r in hdr]
    head = [g for g in glyphs if (g[3] + g[4]) / 2 < bottom]
    keys = []
    for x0, x1 in edges:
        mine = [g for g in head if x0 <= (g[1] + g[2]) / 2 < x1]
        label = "\n".join(_text(line) for line in _lines(mine, tol))
        key = by_label.get(label)
        if key is None:
            raise ValueError(
                f"{name}: page {page_no} prints a column labelled {label!r} that "
                "this report doesn't have — the site's layout has changed; this "
                "app needs an update for it")
        keys.append(key)
    return edges, keys, bottom


def read_print(path, spec):
    """Read one Clean Road print (`spec` = a `clean_road_columns` spec).
    Returns a PrintRead; raises ValueError on anything that isn't the censused
    layout (no table, an unknown or repeated column, a header that changes
    between pages, a glyph outside every column)."""
    if not _DEPS_OK:
        raise ValueError("Required components are missing (pypdfium2).")
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    by_label = crc.printed_columns(spec)
    index = {k: i for i, k in enumerate(spec.header)}
    rows, layout = [], None
    with _PDFIUM_LOCK:
        pdf = pdfium.PdfDocument(str(path))
        try:
            pages = len(pdf)
            if pages < 2:
                raise ValueError(f"{name}: no data pages (a cover page only)")
            route_claim = _cover_route(pdf[0])
            for page_no in range(2, pages + 1):
                page = pdf[page_no - 1]
                try:
                    glyphs, rects = _page_parts(page)
                finally:
                    page.close()
                if not glyphs:
                    raise ValueError(f"{name}: page {page_no} carries no text")
                size = statistics.median(g[5] for g in glyphs) or 1.0
                tol = ROW_TOLERANCE_EM * size
                edges, keys, band = _header(rects, glyphs, tol, by_label, page_no, name)
                if len(set(keys)) != len(keys):
                    raise ValueError(f"{name}: page {page_no} prints a column twice")
                if layout is None:
                    layout = keys
                elif keys != layout:
                    raise ValueError(f"{name}: page {page_no}'s columns differ from page 2's")
                starts = [e[0] for e in edges]
                body = [g for g in glyphs if (g[3] + g[4]) / 2 >= band]
                for line in _lines(body, tol):
                    cells = [[] for _ in edges]
                    for g in line:
                        xm = (g[1] + g[2]) / 2
                        i = bisect_right(starts, xm) - 1
                        if i < 0 or xm >= edges[i][1] + 0.01:
                            raise ValueError(
                                f"{name}: page {page_no} has text outside every "
                                f"column ({g[0]!r}) — not the censused layout")
                        cells[i].append(g)
                    row = [""] * len(spec.header)
                    for key, mine in zip(keys, cells):
                        row[index[key]] = _text(mine)
                    rows.append(row)
        finally:
            pdf.close()
    return PrintRead(route_claim, tuple(layout or ()), rows, pages)
