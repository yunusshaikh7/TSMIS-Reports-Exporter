"""Consolidate the TSMIS Intersection Summary PRINT (PDF) into the same workbook
the Excel consolidator writes (v0.48.0).

The "Intersection Summary (PDF)" export (`ints_printAll`) saves a cover page
plus the on-screen summary: the eleven NUMBER | CODE blocks laid out in
columns. The site has shipped two print layouts — the July 2026 one (three
columns on one page, bracketed headings like "<-----HIGHWAY GROUP----->") and
the October one (two columns over two pages, plain headings). Both are read
the same way:

  * each page's columns are found from the "NUMBER" column headings every
    block prints (one heading x-position per column), never from fixed
    coordinates, so a layout that moves its columns still reads;
  * each column is block-walked by the SAME `summary_layout.counts_from_rows`
    the Excel consolidator and the TSN print parser use, so the three can't
    drift; a category found in two columns refuses (an ambiguous table);
  * the route is the page's own "Route: <r>" claim (the filename token is the
    fallback, exactly like the Excel parser), the total its
    "Total Intersections = N" line.

Censused against the same-day Excel exports on 7/9 (ARS-prod, July layout),
7/23 (SSOR-prod, July layout) and 10/2 (SSOR-prod, October layout): all 217
routes of each read count-for-count equal, and the strict partition
validator (`record_problem`) passes every route.

The workbook carries the PDF-conversion marker (CMP-AUD-066), so the
PDF-vs-Excel self-check can prove which side is which. Console-free.
"""
import logging
import re
from pathlib import Path

logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import pdfplumber
    import openpyxl  # noqa: F401 — the deps gate covers both the PDF and XLSX deps
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import consolidate_intersection_summary as cis
import summary_layout
from compare_intersection_summary_tsn import _cluster
from events import ConsolidateResult
from paths import OUTPUT_ROOT, output_day_dir, stamped_consolidated_filename

SUBDIR = "intersection_summary_pdf"
FILENAME = "tsmis_intersection_summary_pdf_consolidated.xlsx"
SHEET_NAME = cis.SHEET_NAME                 # the consolidated per-route sheet
REPORT_NAME = "TSMIS Intersection Summary (PDF)"
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"

INPUT_DIR = OUTPUT_ROOT / SUBDIR
OUT_PATH = OUTPUT_ROOT / FILENAME           # legacy flat output

_ROUTE_RE = re.compile(r"Route:\s*(\w+)")
_TOTAL_RE = re.compile(r"Total Intersections\s*=\s*([\d,]+)", re.IGNORECASE)
_ROUTE_FROM_NAME = re.compile(r"_route_(\w+)\.pdf$", re.IGNORECASE)
# Column headings closer than this are one column (the July layout's three
# columns sit ~190 pt apart, the October layout's two ~290 pt).
_COLUMN_MIN_GAP = 20
# A column's words start this far left of its NUMBER heading at most (the July
# layout's bracketed block headings start 2.8 pt left of it).
_COLUMN_LEAD = 6


def input_dir_for(day):
    """The print exports for `day` (a run-folder name); None = the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """The consolidated workbook for `day`; None = the legacy location."""
    if not day:
        return OUT_PATH
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(FILENAME, day)


def _columns(words):
    """The page's words split into its printed columns (left to right)."""
    starts = []
    for x in sorted(w["x0"] for w in words if w["text"] == "NUMBER"):
        if not starts or x - starts[-1] > _COLUMN_MIN_GAP:
            starts.append(x)
    if not starts:
        return []
    edges = [x - _COLUMN_LEAD for x in starts]
    cols = [[] for _ in edges]
    for w in words:
        i = max((k for k, e in enumerate(edges) if w["x0"] >= e), default=0)
        cols[i].append(w)
    return cols


def parse_pdf(path):
    """One per-route print -> (route, counts{slug: count}, total) — the shape
    `consolidate_intersection_summary.parse_route` returns for the Excel."""
    name = Path(path).name
    route = total = None
    counts = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "REPORT PARAMETERS" in text:
                continue                         # the cover page
            if route is None:
                m = _ROUTE_RE.search(text)
                if m:
                    route = m.group(1)
            m = _TOTAL_RE.search(text)
            if m:
                total = int(m.group(1).replace(",", ""))
            for col in _columns(page.extract_words()):
                got = summary_layout.counts_from_rows(cis._SPEC, _cluster(col),
                                                      source=name)
                for slug, v in got.items():
                    if slug in counts:
                        raise ValueError(
                            f"{name}: the category {slug!r} appears in two columns "
                            "— refusing to read an ambiguous summary table")
                    counts[slug] = v
    if route is None:
        m = _ROUTE_FROM_NAME.search(name)
        route = m.group(1) if m else Path(path).stem
    return route, counts, total


PDF_EDITION = cis.Edition(
    glob="*.pdf", parse=parse_pdf, noun="PDF", report_name=REPORT_NAME,
    title="TSMIS Intersection Summary (PDF) Consolidation",
    input_dir_for=input_dir_for, out_path_for=out_path_for, pdf_marker=True,
    missing_deps="pdfplumber, openpyxl")


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Parse every per-route Intersection Summary print into the Excel
    consolidator's workbook. `converted_dir` is accepted for the matrix's PDF
    contract and unused: the print parses straight to records. Console-free."""
    if not _DEPS_OK:
        return ConsolidateResult(
            status="error",
            message="Required components are missing (pdfplumber, openpyxl).")
    return cis.consolidate_edition(PDF_EDITION, events=events,
                                   confirm_overwrite=confirm_overwrite, day=day,
                                   input_dir=input_dir, out_path=out_path,
                                   commit_guard=commit_guard)


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
