"""Golden check for the independent expected-row oracle (scripts/pdf_row_oracle.py).

Proves the oracle LOGIC over synthetic page fixtures (text-line lists with KNOWN
data-row counts), the reconciliation (match / drop / duplicate), and the
privacy-safe evidence-capture WIRING (stubbed parser + stubbed extraction — no real
PDF). Per RM04 this is the v0.18.0 deliverable: the oracle + the capture path the
P13 work-PC kit runs over REAL PDFs. Proving the PARSER correct against real
returned PDFs is v0.18.1 acceptance — these abstract text-line fixtures are NOT real
PDFs and do not assert real-PDF parser correctness.

Run with the build venv:
    build\\.venv\\Scripts\\python.exe build\\check_pdf_row_oracle.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pdf_row_oracle as O

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# Synthetic page fixtures: (label, lines, expected_data_rows). A data row BEGINS
# with a postmile; headers / descriptions / footers do not.
_CLEAN = [
    "STATE OF CALIFORNIA - HIGHWAY LOG",          # banner (not data)
    "Route 001  District 04",                     # route header (not data)
    "Location   MI    NA    ...",                 # column header (not data)
    "000.000  0.250  0.000  ...",                 # data row
    "  Bridge 28-0001 over Some Creek",           # description (indented, no PM)
    "000.250  0.500  0.000  ...",                 # data row
    "R012.345  1.000  0.000  ...",                # data row (realignment prefix)
    "123.456A 0.100 0.000 ...",                   # data row (trailing letter)
    "Page 1 of 3",                                # footer (not data)
]
_CLEAN_EXPECTED = 4

_NO_DATA = [
    "STATE OF CALIFORNIA - HIGHWAY LOG",
    "Route 005  District 11",
    "Location   MI    NA",
    "   continued from previous page",
    "",
]
_NO_DATA_EXPECTED = 0

_DENSE = ["%03d.%03d  x  y  z" % (i, i) for i in range(10)]   # 10 data rows
_DENSE_EXPECTED = 10

# pdfplumber sometimes SPLITS a lone realignment/section letter from the postmile
# ("R 012.345 ..."), a shape the parser explicitly accepts (P12-R01). The oracle
# must count it, while a lone letter WITHOUT a following postmile is NOT a data row.
_SPLIT = [
    "Route 020  District 03",                      # header (not data)
    "R 012.345  0.250  0.000  sample",             # split realignment prefix -> data row
    "L 200.000  0.100  0.000  sample",             # split prefix -> data row
    "  N 5 not a postmile here",                    # lone letter, no postmile -> NOT data
    "000.500  1.000  0.000  sample",               # bare postmile -> data row
]
_SPLIT_EXPECTED = 3


def oracle_logic_checks():
    print("oracle logic (line_is_data_row / count_expected_rows):")
    check("a bare postmile line is a data row", O.line_is_data_row("000.001 a b c"))
    check("a prefixed postmile (R012.345) is a data row",
          O.line_is_data_row("R012.345 a b c"))
    check("a trailing-letter postmile (123.456A) is a data row",
          O.line_is_data_row("123.456A a b"))
    check("a SPLIT realignment prefix (R 012.345) is a data row (P12-R01)",
          O.line_is_data_row("R 012.345 0.250 0.000 sample"))
    check("an indented description is NOT a data row",
          not O.line_is_data_row("  Bridge 28-0001 over Creek"))
    check("a column header is NOT a data row",
          not O.line_is_data_row("Location   MI    NA"))
    check("a blank line is NOT a data row", not O.line_is_data_row(""))
    check("a route-number-only token is NOT a postmile",
          not O.line_is_data_row("001 District 04"))
    check("a lone letter WITHOUT a following postmile is NOT a data row",
          not O.line_is_data_row("N 5 junction"))

    for label, lines, expected in (("clean", _CLEAN, _CLEAN_EXPECTED),
                                   ("no-data", _NO_DATA, _NO_DATA_EXPECTED),
                                   ("dense", _DENSE, _DENSE_EXPECTED),
                                   ("split-prefix", _SPLIT, _SPLIT_EXPECTED)):
        got = O.count_expected_rows(lines)
        check(f"count_expected_rows[{label}] == {expected} (got {got})", got == expected)


def reconcile_checks():
    print("reconcile (match / drop / duplicate):")
    m = O.reconcile(10, 10)
    check("match -> not flagged, delta 0", m["flagged"] is False and m["delta"] == 0)
    d = O.reconcile(10, 7)
    check("drop (emitted<expected) -> flagged, delta>0",
          d["flagged"] is True and d["delta"] == 3)
    dup = O.reconcile(10, 12)
    check("duplicate (emitted>expected) -> flagged, delta<0",
          dup["flagged"] is True and dup["delta"] == -2)


def capture_wiring_checks():
    print("evidence capture wiring (stubbed parser + extraction; no real PDF):")

    def fake_pages(_path):
        # two pages: 4 + 10 = 14 expected data rows
        yield _CLEAN
        yield _DENSE

    def make_parse(emitted_rows, stats):
        def parse_fn(path, events, pdf_name=""):
            rows = [["%03d.000" % i] + ["x"] * 30 for i in range(emitted_rows)]
            return "001", rows, dict(stats)
        return parse_fn

    # matching parser (emits 14) -> not flagged
    rec = O.capture_evidence("route001.pdf",
                             make_parse(14, {"skipped_no_geometry": 0,
                                             "stale_geometry_pages": 0}),
                             page_lines_fn=fake_pages)
    check("capture: oracle_expected_rows == 14", rec.get("oracle_expected_rows") == 14)
    check("capture: matching emit -> not flagged", rec.get("flagged") is False)
    check("capture: carries the route", rec.get("route") == "001")
    check("capture: is privacy-safe (no row/cell-content keys)",
          not any(k in rec for k in ("rows", "cells", "content", "text")))

    # dropping parser (emits 11, oracle 14) -> flagged, delta 3, stats surfaced
    rec2 = O.capture_evidence("route001.pdf",
                              make_parse(11, {"skipped_no_geometry": 3,
                                              "stale_geometry_pages": 1}),
                              page_lines_fn=fake_pages)
    check("capture: dropped rows -> flagged, delta 3",
          rec2.get("flagged") is True and rec2.get("delta") == 3)
    check("capture: surfaces the parser's skip stat",
          rec2.get("parser_skipped_no_geometry") == 3)
    check("capture: surfaces the parser's stale-geometry stat",
          rec2.get("parser_stale_geometry_pages") == 1)

    # parser raises -> error record, never propagates
    def boom(*_a, **_k):
        raise ValueError("parse boom")

    rec3 = O.capture_evidence("bad.pdf", boom, page_lines_fn=fake_pages)
    check("capture: a parser crash is recorded, not raised",
          "error" in rec3 and "parser" in rec3["error"])

    # extraction raises -> error record
    def boom_pages(_path):
        raise OSError("cannot read")
        yield  # pragma: no cover

    rec4 = O.capture_evidence("bad.pdf", make_parse(1, {}), page_lines_fn=boom_pages)
    check("capture: an extraction crash is recorded, not raised",
          "error" in rec4 and "oracle" in rec4["error"])

    # split-prefix rows reach the oracle through the capture path (P12-R01): the
    # oracle counts 3, a parser that emits 1 is flagged for the evidence kit.
    def split_pages(_path):
        yield _SPLIT

    rec5 = O.capture_evidence("split.pdf", make_parse(1, {}), page_lines_fn=split_pages)
    check("capture: split-prefix rows counted by the oracle (expected 3)",
          rec5.get("oracle_expected_rows") == 3)
    check("capture: split-prefix drop is flagged (3 expected vs 1 emitted)",
          rec5.get("flagged") is True and rec5.get("delta") == 2)


def main():
    print("PDF expected-row oracle (independent):")
    oracle_logic_checks()
    reconcile_checks()
    capture_wiring_checks()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL PDF-ROW-ORACLE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
