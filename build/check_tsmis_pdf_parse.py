"""Golden checks for the TSMIS Highway Log (PDF) consolidator
(scripts/consolidate_tsmis_highway_log_pdf.py).

The TSMIS "Highway Log (PDF)" export renders the report as a bordered HTML
table; this converter parses it into the SAME 31-column TSMIS format the Excel
export and the TSN consolidator produce, so it can be compared against either.
These tests lock the parsing LOGIC (no PDF needed, CI-safe like the other
build\\check_*.py):

  * the 30 cell columns map 1:1, in order, to the 31-column TSMIS layout MINUS
    Description (which sits at index 28, filled from follow-on lines);
  * character assignment is CONSERVING — contiguous windows place every data
    character in exactly one column (no char dropped between cells);
  * the left-margin section marker ("C"/"R"/"L") stays inside the Location cell
    and Location normalizes to the single-token TSN/Excel form;
  * the column-header band is found by CONTENT (the "LOCATION … ODOM … CITY"
    row), so an orphan description on a near-empty page isn't swallowed.

Real-data verified (2026-06-17): character conservation holds across ALL 252
route PDFs (0 char-loss / 0 unclassified lines), per-route row counts equal the
PDF's data-row count, and route-1 PDF-vs-Excel matches the official TSMIS Excel
export on 1,961/1,963 rows — the residual diffs are the Excel export's own bug
(it expands "+"/"++" ditto markers, adds phantom rows, and shifts descriptions).
PDF-vs-TSN reproduces the established Excel-vs-TSN counts cell-for-cell.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_tsmis_pdf_parse.py
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import consolidate_tsmis_highway_log_pdf as M


def _nonspace(s):
    return Counter(ch for ch in s if not ch.isspace())


def _char(text, x0, x1):
    return {"text": text, "x0": x0, "x1": x1}


def check_layout_guard():
    assert M.N_PDF_COLS == 30, M.N_PDF_COLS
    assert len(M.TSMIS_HEADER) == 31, len(M.TSMIS_HEADER)
    assert M._DESC_IDX == 28, M._DESC_IDX
    assert M.TSMIS_HEADER[M._DESC_IDX] == "Description"
    # The two date columns follow Description.
    assert M.TSMIS_HEADER[29] == "Date of Rec"
    assert M.TSMIS_HEADER[30] == "Sig Chg. Date"


def check_norm_route():
    cases = {"1": "001", "6": "006", "101": "101", "5S": "005S",
             "005S": "005S", "101U": "101U", "8u": "008U"}
    for raw, want in cases.items():
        got = M._norm_route(raw)
        assert got == want, (raw, got, want)


def check_normalize_location():
    # A glued left-margin marker prints with a small gap, so the column
    # assembler may insert a space; it must collapse to the single-token form.
    assert M._normalize_location("C 043.925E") == "C043.925E"
    assert M._normalize_location("R012.887") == "R012.887"
    assert M._normalize_location("000.000") == "000.000"
    assert M._normalize_location("R 081.505R") == "R081.505R"


def check_make_row():
    # 30 PDF cell values 0..27 -> Location..RB SH, then Description, then dates.
    vals = [f"v{i}" for i in range(30)]
    vals[0] = "R000.129"
    row = M._make_row(vals, "JCT 5 CAMINO")
    assert len(row) == 31, len(row)
    assert row[0] == "R000.129"                  # Location
    assert row[M._DESC_IDX] == "JCT 5 CAMINO"    # Description slot
    assert row[1] == "v1" and row[27] == "v27"   # MI .. RB SH unchanged, in order
    assert row[29] == "v28" and row[30] == "v29"  # Date of Rec / Sig Chg. Date
    # Blank cells become None.
    blank = M._make_row([""] * 30, None)
    assert blank[0] is None and blank[M._DESC_IDX] is None


def check_assign_columns_conserves():
    # Three contiguous windows; a left-margin "C" + postmile in col0 (the gap
    # between the marker and the postmile yields a space), a value in col1, and a
    # two-token value in col2 (an internal gap yields a space).
    windows = [(float("-inf"), 80.0), (80.0, 120.0), (120.0, float("inf"))]
    chars = (
        [_char("C", 31, 37)]
        + [_char(c, 40 + 4 * i, 44 + 4 * i) for i, c in enumerate("043.925E")]
        + [_char("6", 90, 96), _char("5", 96, 102)]         # col1 = "65"
        + [_char(c, 122 + 3 * i, 125 + 3 * i) for i, c in enumerate("AB")]
        + [_char("C", 140, 146)]                            # col2 second token (gap)
    )
    vals = M._assign_columns(chars, windows)
    assert len(vals) == 3
    assert vals[0] == "C 043.925E", vals[0]      # marker + postmile (gap -> space)
    assert vals[1] == "65", vals[1]
    assert vals[2] == "AB C", vals[2]            # gap inside a column -> space
    # Conservation: every non-space input character lands in exactly one column.
    want = _nonspace("".join(c["text"] for c in chars))
    got = _nonspace("".join(vals))
    assert want == got, (want, got)


def check_carried_line_crossings():
    """The carried-geometry validator (v0.26.2): intra-token window splits.
    0 = the page shares the carried layout (every printed token's chars land in
    one window — the same char-center test assign_columns places by); >0 = a
    drifted/foreign layout is cutting through tokens, the genuinely-risky carry."""
    from pdf_table_lib import carried_line_crossings
    windows = [(float("-inf"), 80.0), (80.0, 120.0), (120.0, float("inf"))]
    aligned = (
        [_char(c, 40 + 4 * i, 44 + 4 * i) for i, c in enumerate("043.925")]   # col0
        + [_char("6", 90, 96), _char("5", 96, 102)]                           # col1
        + [_char(c, 130 + 3 * i, 133 + 3 * i) for i, c in enumerate("AB")])   # col2
    assert carried_line_crossings(aligned, windows, M.WORD_GAP) == 0
    # Two tokens split by a REAL gap across a boundary are two cells, not a split.
    two_cells = [_char("1", 70, 76), _char("2", 90, 96)]
    assert carried_line_crossings(two_cells, windows, M.WORD_GAP) == 0
    # A drifted carry cuts through the col0 token: chars of ONE token (abutting)
    # straddle the 80.0 boundary -> counted.
    straddle = [_char(c, 70 + 4 * i, 74 + 4 * i) for i, c in enumerate("043.925")]
    assert carried_line_crossings(straddle, windows, M.WORD_GAP) >= 1
    # The foreign-table failure mode: the SAME aligned line scored against a
    # shifted layout whose boundary now falls mid-token fires immediately.
    shifted = [(lo - 30, hi - 30) for lo, hi in windows]      # boundary 80 -> 50
    assert carried_line_crossings(aligned, shifted, M.WORD_GAP) >= 1
    # The full misfit score adds the Location-cell re-check: a boundary-0 shift
    # can move WHOLE tokens without cutting any (crossings blind spot) — but it
    # glues MI into col0 / empties col0, which LOCATION_RE catches.
    ok_row = M._make_row(["C 043.925E"] + ["x"] * 29, None)
    assert M._carried_line_misfits(aligned, windows, ok_row) == 0
    glued = M._make_row(["043.925 000.045"] + ["x"] * 29, None)   # MI pulled in
    assert M._carried_line_misfits(aligned, windows, glued) >= 1
    empty0 = M._make_row([""] + ["x"] * 29, None)                 # postmile pushed out
    assert M._carried_line_misfits(aligned, windows, empty0) >= 1


def check_header_bottom():
    def line(y, text):
        return (y, [{"text": t} for t in text.split()], [])

    lines = [
        line(3, "Ref Date: 2026-06-17 Route 001 Page 7"),
        line(27, "LOCATION AND DISTANCE LEFT ROADBED MEDIAN RIGHT ROADBED"),
        line(54, "LOCATION MI A ODOM CITY U D R G C T LNS F TO TR WID"),
        line(74, "09 INY 006"),                  # group header (content)
        line(101, "000.000 000.045 000.000 BIS"),  # data (content)
    ]
    hb = M._header_bottom(lines)
    assert hb == 54, hb                          # the ODOM+CITY row
    # Cover/legend page (no such row) -> None, so the caller falls back.
    assert M._header_bottom([line(10, "California State Highway Log"),
                             line(30, "2026")]) is None


def main():
    check_layout_guard()
    check_norm_route()
    check_normalize_location()
    check_make_row()
    check_assign_columns_conserves()
    check_carried_line_crossings()
    check_header_bottom()
    print("OK  TSMIS Highway Log (PDF) parse: 30->31 column mapping, conserving "
          "character assignment, Location normalization, route padding, "
          "carried-geometry validation, and content-based header detection all "
          "locked.")


if __name__ == "__main__":
    main()
