"""Consolidate the TSMIS Highway Summary PRINT (PDF) into the same workbook the
Excel consolidator writes (v0.48.0).

The "Highway Summary (PDF)" export (`hs_printAll`) saves a cover page plus the
summary laid out in two columns over three pages — the TSN print's own report
(OTM22230) and arrangement: "*TOTAL MILES SELECTED", then the ten sections as
little CODE | MILES tables placed side by side (HIGHWAY GROUP beside NON-ADD,
MEDIAN TYPE beside MEDIAN BARRIER, …). Read like this:

  * each page's columns come from the "CODE" headings every section prints
    (one heading x-position per column), so the two columns' rows — which do
    not line up vertically — never mix;
  * each column is walked top-down: a section heading opens its section, every
    "<label> <miles>" line is one category, matched to the censused Excel
    taxonomy (`highway_summary_columns`) by its normalized label;
  * the print shows RURAL-URBAN's second rows as "- O - OUTSIDE CITY" under
    their parent ("R- RURAL …" / "U- URBAN …"), which the Excel spells out in
    full — the parent is carried down to name them;
  * MEDIAN TYPE's "(UNDIVIDED)" / "(DIVIDED)" are group sub-headings the print
    shows without a value; the Excel export writes 0 for both on every route
    (verified statewide), and they are recorded the same way;
  * the total is read from the page text (its number sits in the other column).
Every censused category must be found exactly once: an unknown label, a
repeated one or a missing one refuses the route (the layout changed).

Censused against the same-day Excel exports on the 10/2 SSOR-prod pull (the
first real prints): all 252 routes read equal — the total and all 95
categories, to the thousandth of a mile.

The workbook carries the PDF-conversion marker (CMP-AUD-066). Console-free.
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

import consolidate_highway_summary as chs
import highway_summary_columns as hsc
from events import ConsolidateResult
from paths import OUTPUT_ROOT, output_day_dir, stamped_consolidated_filename

SUBDIR = "highway_summary_pdf"
FILENAME = "tsmis_highway_summary_pdf_consolidated.xlsx"
SHEET_NAME = chs.SHEET_NAME                 # the consolidated per-route sheet
REPORT_NAME = "TSMIS Highway Summary (PDF)"
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"

INPUT_DIR = OUTPUT_ROOT / SUBDIR
OUT_PATH = OUTPUT_ROOT / FILENAME           # legacy flat output

_MILES = re.compile(r"^\d[\d,]*\.\d{3}$")
_TOTAL_RE = re.compile(r"\*?\s*TOTAL MILES SELECTED\s+(\d[\d,]*\.\d{3})")
_COVER_ROUTE_RE = re.compile(r"LOCATION CRITERIA:\s*ROUTE\s+([0-9A-Z]+)", re.I)
_ROUTE_FROM_NAME = re.compile(r"_route_(\w+)\.pdf$", re.IGNORECASE)
_SECTIONS = {s.norm: s for s in hsc.SECTIONS}
_SUBHEADINGS = {"(UNDIVIDED)", "(DIVIDED)"}         # MEDIAN TYPE group sub-headings
_COLUMN_MIN_GAP = 20
_COLUMN_LEAD = 6
_Y_TOLERANCE = 3


def input_dir_for(day):
    """The print exports for `day` (a run-folder name); None = the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """The consolidated workbook for `day`; None = the legacy location."""
    if not day:
        return OUT_PATH
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(FILENAME, day)


def _columns(words):
    starts = []
    for x in sorted(w["x0"] for w in words if w["text"] == "CODE"):
        if not starts or x - starts[-1] > _COLUMN_MIN_GAP:
            starts.append(x)
    if not starts:
        return [words] if words else []
    edges = [x - _COLUMN_LEAD for x in starts]
    cols = [[] for _ in edges]
    for w in words:
        i = max((k for k, e in enumerate(edges) if w["x0"] >= e), default=0)
        cols[i].append(w)
    return cols


def _lines(words):
    out, cur, ref = [], [], None
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if ref is None or abs(w["top"] - ref) <= _Y_TOLERANCE:
            cur.append(w)
            ref = w["top"] if ref is None else ref
        else:
            out.append(cur)
            cur, ref = [w], w["top"]
    if cur:
        out.append(cur)
    return [" ".join(w["text"] for w in sorted(line, key=lambda w: w["x0"]))
            for line in out]


def _entries(page_words, name, total_text):
    """[(section, normalized label, miles text)] for one page, column by column."""
    out = []
    for col in _columns(page_words):
        section, parent = None, None
        for line in _lines(col):
            tokens = line.split()
            miles = tokens[-1] if tokens and _MILES.match(tokens[-1]) else None
            label = " ".join(tokens[:-1]) if miles else line
            norm = hsc.norm_label(label)
            if hsc.norm_label(hsc.TOTAL_LABEL) in norm:
                continue                         # the total (read from the text)
            if norm == "CODE MILES":
                continue
            if miles is None:
                if norm in _SECTIONS:
                    section, parent = _SECTIONS[norm], None
                elif section is not None and section.name == "MEDIAN TYPE" \
                        and norm in _SUBHEADINGS:
                    out.append((section, norm, "0.000"))
                continue                         # footnotes / prose
            if section is None:
                if not label and miles == total_text:
                    continue                     # the total's number, other column
                raise ValueError(f"{name}: the mileage line {line!r} sits outside "
                                 "any section — the print layout has changed")
            if section.name == "RURAL-URBAN":
                if norm.startswith(("R- RURAL", "U- URBAN")):
                    parent = norm.split(" - ")[0]
                elif norm.startswith("- O -") and parent:
                    norm = hsc.norm_label(f"{parent} {norm}")
            out.append((section, norm, miles))
    return out


def parse_pdf(path):
    """One per-route print -> (route, values{slug: thousandths}, total) — the
    shape `consolidate_highway_summary.parse_route` returns for the Excel."""
    name = Path(path).name
    route = total = total_text = None
    entries = []
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if page_no == 1 and "REPORT PARAMETERS" in text:
                m = _COVER_ROUTE_RE.search(text)
                route = m.group(1).upper() if m else None
                continue
            m = _TOTAL_RE.search(text)
            if m:
                if total is not None:
                    raise ValueError(f"{name}: {hsc.TOTAL_LABEL!r} appears twice")
                total_text = m.group(1)
                total = hsc.parse_miles(total_text, source=name,
                                        category=hsc.TOTAL_LABEL)
            entries += _entries(page.extract_words(), name, total_text)
    if total is None:
        raise ValueError(f"{name}: no {hsc.TOTAL_LABEL!r} line was found — the print "
                         "layout has changed; this app needs an update for it")
    values = {}
    for section, norm, miles in entries:
        cat = next((c for c in section.cats if c.norm == norm), None)
        if cat is None:
            raise ValueError(f"{name}: unknown {section.name} category {norm!r} — "
                             "the print layout has changed")
        if cat.slug in values:
            raise ValueError(f"{name}: the {section.name} category {norm!r} appears "
                             "twice — refusing to read an ambiguous table")
        values[cat.slug] = hsc.parse_miles(miles, source=name, category=cat.key)
    missing = [c.key for c in hsc.CATS if c.slug not in values]
    if missing:
        raise ValueError(f"{name}: {len(missing)} categor"
                         f"{'y' if len(missing) == 1 else 'ies'} not found in the "
                         f"print ({', '.join(missing[:3])}…) — the layout has changed")
    if route is None:
        m = _ROUTE_FROM_NAME.search(name)
        route = m.group(1) if m else Path(path).stem
    return route, values, total


PDF_EDITION = chs.Edition(
    glob="*.pdf", parse=parse_pdf, noun="PDF", report_name=REPORT_NAME,
    title="TSMIS Highway Summary (PDF) Consolidation",
    input_dir_for=input_dir_for, out_path_for=out_path_for, pdf_marker=True,
    missing_deps="pdfplumber, openpyxl")


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Parse every per-route Highway Summary print into the Excel
    consolidator's workbook. `converted_dir` is accepted for the matrix's PDF
    contract and unused: the print parses straight to records. Console-free."""
    if not _DEPS_OK:
        return ConsolidateResult(
            status="error",
            message="Required components are missing (pdfplumber, openpyxl).")
    return chs.consolidate_edition(PDF_EDITION, events=events,
                                   confirm_overwrite=confirm_overwrite, day=day,
                                   input_dir=input_dir, out_path=out_path,
                                   commit_guard=commit_guard)


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
