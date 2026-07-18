"""Hand-rolled positioned-Helvetica fixture PDFs for TSN Highway Log checks.

Shared by check_tsn_highway_log_claims and check_compare_physical_identity
(the underscore name keeps it out of the run_checks check_*.py glob). The
documents are minimal but valid PDF 1.4 — pdfplumber parses them through the
production pipeline, so the fixtures exercise the real char-window parser,
not a mock.
"""
from pathlib import Path

PAGE_H = 792.0
FONT_SIZE = 8.0


def _esc(text):
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _page_stream(runs, rects=(), encoding="latin-1"):
    parts = []
    for x, top, w, h in rects:
        # A filled light-grey cell rect (pdfplumber reads it from the `re` op)
        # — the TSMIS Highway Log parser derives its column windows from the
        # zebra-shaded data-band rects, so fixtures for it need real rects.
        y = PAGE_H - top - h
        parts.append(f"q 0.9 0.9 0.9 rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f Q")
    parts += ["BT", f"/F1 {FONT_SIZE} Tf"]
    for x, top, text in runs:
        y = PAGE_H - top - FONT_SIZE
        parts.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm ({_esc(text)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode(encoding)


def make_pdf(path, pages, rects_per_page=None, win_ansi=False):
    """pages: list of [(x, top, text)] run-lists -> a minimal valid PDF.
    `rects_per_page` (optional): a parallel list of [(x, top, w, h)] filled
    cell rects per page (for parsers that window on shaded bands).
    `win_ansi` (opt-in): declare WinAnsiEncoding and encode the content stream as
    cp1252, so a fixture can carry the print's en/em dashes (bytes 0x96/0x97 that
    latin-1 can't hold) — pdfplumber then reads them back as U+2013/U+2014. Off by
    default, so every existing ASCII caller is byte-for-byte unchanged."""
    encoding = "cp1252" if win_ansi else "latin-1"
    font = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>" if win_ansi
            else b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objs = []
    kids = []
    for i, runs in enumerate(pages):
        content_num = 4 + i * 2
        page_num = content_num + 1
        rects = () if rects_per_page is None else rects_per_page[i]
        stream = _page_stream(runs, rects, encoding)
        objs.append((content_num,
                     b"<< /Length %d >>\nstream\n%s\nendstream"
                     % (len(stream), stream)))
        objs.append((page_num,
                     b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                     b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
                     % content_num))
        kids.append(f"{page_num} 0 R")
    head = [
        (1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        (2, ("<< /Type /Pages /Kids [%s] /Count %d >>"
             % (" ".join(kids), len(pages))).encode("latin-1")),
        (3, font),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num, body in sorted(head + objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + body + b"\nendobj\n"
    xref_at = len(out)
    n = len(offsets) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % n
    for num in sorted(offsets):
        out += b"%010d 00000 n \n" % offsets[num]
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (n, xref_at))
    Path(path).write_bytes(bytes(out))


def cover(district):
    return [
        (37, 300, "CALIFORNIA DEPARTMENT OF TRANSPORTATION"),
        (201, 330, "California State Highway Log"),
        (263, 360, "2025"),
        (256, 390, f"District {district}"),
    ]


def band(page_no, date="09/15/25"):
    return [
        (11, 30, "OTM52010"),
        (150, 40, f"Date{date} California State Highway Log Page {page_no}"),
    ]


def group(district, county, route, suffix=None, top=70):
    runs = [(255, top, district), (268, top, county), (288, top, route)]
    if suffix is not None:
        runs.append((305, top, suffix))
    return runs


def data_row(top, loc, mi, odom, adt=(), rec="640101", na=None):
    """One data line; `adt` is [(x, text)] runs inside the ADT zone."""
    runs = [(20, top, loc), (55, top, mi), (88, top, odom)]
    if na:
        runs.append((76, top, na))
    runs.extend((x, top, t) for x, t in adt)
    runs.append((492, top, rec))
    return runs


def desc(top, text):
    return [(73.4, top, text)]


def totals(top, kind, total="001.000", const="001.000", unconst="000.000"):
    stars, label = {
        "volume": (11.5, "* * Volume Location Totals"),
        "city": (21.5, "** ** CITY TOTALS"),
        "county": (13.9, "*** *** COUNTY TOTALS"),
        "route": (18.0, "***** ROUTE TOTALS"),
        "district": (7.9, "******* DISTRICT TOTALS"),
    }[kind]
    if kind == "volume":
        return [(stars, top, f"{label} Length {total} DVM 1,000 "
                             f"County Cumulative DVM 1,000")]
    return [(stars, top,
             f"{label} (MILEAGE) TOTAL {total} CONST {const} UNCONST {unconst}")]
