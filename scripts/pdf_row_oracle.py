"""Independent expected-row ORACLE for the TSMIS Highway Log (PDF) consolidator.

`pdf-consolidator-no-row-count-verification` (Phase-3 audit): the cell-rect PDF
parser (`consolidate_tsmis_highway_log_pdf.parse_pdf`) emits one row per detected
data line, but NOTHING cross-checks how many rows a page SHOULD have yielded, so a
silently dropped (or duplicated) row goes unnoticed.

This module is an INDEPENDENT oracle — it counts expected data rows by a DIFFERENT
method than the parser. The parser reads CELL RECTANGLES (column geometry); the
oracle scans TEXT LINES and counts those that BEGIN with a Highway Log postmile.
The postmile recognizer here is authored from the printed-document Location format
(highway_log_columns: column 0 = Location / Postmile) and is deliberately NOT
imported from the parser, so if either recognizer drifts the two diverge and the
reconciliation flags it — the test oracle must never be derived from the code under
test (R1-D05 / D12).

RM04 honesty: v0.18.0 ships this oracle + the reconciliation + the privacy-safe
evidence-CAPTURE path (COUNTS only — never cell contents; RM05) that the P13
work-PC kit runs over REAL PDFs. Proving the parser CORRECT against real returned
PDFs is v0.18.1 acceptance; the synthetic text-line fixtures in
`build/check_pdf_row_oracle.py` prove the ORACLE LOGIC and the capture WIRING, not
real-PDF parser correctness.

Stdlib for the oracle + reconcile (counting lines needs no third-party lib, so the
harness runs anywhere); pdfplumber is imported lazily only by the real-PDF
extraction path. Console-free.
"""
import logging
import re
from pathlib import Path

log = logging.getLogger("tsmis.pdf_row_oracle")

# A Highway Log segment postmile as PRINTED in the Location column: an optional
# realignment/section letter, the 3.3 postmile, an optional trailing letter.
# Authored from the printed-document format — deliberately NOT imported from
# parse_pdf, so the oracle stays an INDEPENDENT recognizer.
_POSTMILE_RE = re.compile(r"^[A-Za-z]?\d{3}\.\d{3}[A-Za-z]?$")
# pdfplumber sometimes SPLITS a lone realignment/section letter ("R"/"L"/"C") into
# its own token, leaving the postmile in the NEXT token ("R 012.345 ..."). The
# parser explicitly accepts that shape, so the oracle must too — via its own
# recognizers (a bare postmile + a lone-letter prefix), still not importing the
# parser's regex.
_BARE_POSTMILE_RE = re.compile(r"^\d{3}\.\d{3}[A-Za-z]?$")
_PREFIX_RE = re.compile(r"^[A-Za-z]$")


def line_is_data_row(line):
    """True iff `line` (one page text line) BEGINS with a postmile — either a single
    combined token ("000.001" / "R012.345") OR a lone realignment/section letter
    split from the postmile across two tokens ("R 012.345"). A header / description /
    footer line does not (a description prints indented WITHOUT a leading postmile),
    so it is not counted. Independent of the parser's column geometry."""
    if not line:
        return False
    parts = line.split()
    if not parts:
        return False
    if _POSTMILE_RE.match(parts[0]):
        return True
    return (len(parts) >= 2 and bool(_PREFIX_RE.match(parts[0]))
            and bool(_BARE_POSTMILE_RE.match(parts[1])))


def count_expected_rows(text_lines):
    """The number of expected data rows on a page: the text lines that begin with a
    postmile. `text_lines` is an iterable of strings (one per visual line)."""
    return sum(1 for ln in text_lines if line_is_data_row(ln))


def reconcile(expected, emitted):
    """Compare the oracle's `expected` count with the parser's `emitted` count.
    Returns {expected, emitted, delta, flagged}; `flagged` is True on ANY mismatch
    (a DROP -> emitted < expected, delta > 0; a DUPLICATE -> emitted > expected,
    delta < 0)."""
    delta = int(expected) - int(emitted)
    return {"expected": int(expected), "emitted": int(emitted),
            "delta": delta, "flagged": delta != 0}


def independent_page_lines(pdf_path):
    """Yield each page's text lines via pdfplumber's TEXT extraction — the oracle's
    independent signal (vs the parser's cell rectangles). Lazy pdfplumber import so
    importing this module never requires it (the harness feeds line lists directly)."""
    import pdfplumber
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            yield text.splitlines()


def capture_evidence(pdf_path, parse_fn, page_lines_fn=None):
    """The evidence-capture contract the P13 work-PC kit runs over REAL PDFs.

    Reconciles the parser's emitted row count against the INDEPENDENT oracle for one
    PDF and returns a PRIVACY-SAFE record (RM05): COUNTS, the route, the parser's
    own drop stats, and a flag — NEVER cell contents. `parse_fn` is the
    consolidator's parse_pdf-style callable ``(path, events, pdf_name) ->
    (route, rows, stats)``; `page_lines_fn(pdf_path)` yields each page's text lines
    (defaults to pdfplumber). Never raises into the caller — an extraction/parse
    failure is logged and returned as an ``error`` record so the kit keeps going."""
    name = Path(pdf_path).name
    page_lines_fn = page_lines_fn or independent_page_lines
    try:
        expected = sum(count_expected_rows(lines) for lines in page_lines_fn(pdf_path))
    except Exception as e:                       # noqa: BLE001 — record, never crash the kit
        log.warning("evidence capture: oracle extraction failed for %s (%s: %s)",
                    name, type(e).__name__, e)
        return {"pdf": name, "error": f"oracle: {type(e).__name__}: {e}"}
    try:
        from events import Events
        route, rows, stats = parse_fn(str(pdf_path), Events(), pdf_name=name)
    except Exception as e:                       # noqa: BLE001
        log.warning("evidence capture: parser failed for %s (%s: %s)",
                    name, type(e).__name__, e)
        return {"pdf": name, "error": f"parser: {type(e).__name__}: {e}"}
    rec = reconcile(expected, len(rows))
    stats = stats or {}
    return {
        "pdf": name,
        "route": route,
        "oracle_expected_rows": rec["expected"],
        "parser_emitted_rows": rec["emitted"],
        "delta": rec["delta"],
        "flagged": rec["flagged"],
        "parser_skipped_no_geometry": stats.get("skipped_no_geometry"),
        "parser_stale_geometry_pages": stats.get("stale_geometry_pages"),
        "parser_carried_validated_pages": stats.get("carried_validated_pages"),
    }
