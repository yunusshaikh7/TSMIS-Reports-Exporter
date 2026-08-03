"""Ramp Summary adapter for the visual-evidence generator (visual_evidence) —
cross-environment flavor ONLY.

The Ramp Summary's one evidence-eligible placement is the Everything ENV cell
(PCOA-FINAL-007): the cross-environment comparison parses each side's per-route
Ramp Summary PDFs directly (compare_env._load_ramp_summary_side →
consolidate_ramp_summary.parse_pdf), so both sides of an example render as
highlighted crops of those exact prints. Its vs-TSN comparison reads a
normalized workbook and its clean evidence absence there is the audit-approved
state — this module therefore exposes NO vs-TSN/self hooks on purpose, and
`visual_evidence.capable()` keeps saying no for ramp_summary.

VALUES come from the consolidator's own parser (parse_pdf — never a second
parser), so an example can only illustrate what the comparison compared.
GEOMETRY comes from a word-box-keeping twin of the parser's two-column walk
(get_rows_for_column + the ordered first-wins schema match), cross-checked at
lookup time: a category's geometry is only usable when the count text at its
box equals the parsed record's value for that category — an attribution drift
can cost an example, never mislabel one. Wrapped labels and the parser's
stitched orphans keep their VALUES but refuse geometry (single-line rows only).

The compared unit is one route's category table: the env comparison keys rows
on the ROUTE (an aggregate row per route), so `env_locate` returns one record
per print keyed by the normalized route. Console-free; pdfplumber gated by the
engine.
"""
import logging
import re
from pathlib import Path

import paths

try:
    import pdfplumber
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_env
import consolidate_ramp_summary as _rs
from pdf_table_lib import cluster_by_top

log = logging.getLogger("tsmis.evidence")

REPORT_LABEL = "Ramp Summary"
KEY_LABEL = "Route"

# (internal column, display name) — the env comparison's own compared columns.
_COL_DISP = list(compare_env._RS_FIELDS)
_DISP_TO_COL = {disp: col for col, disp in _COL_DISP}

_TOTAL_RES = {
    "total_ramps": re.compile(r"(?i)Total Number of Ramps:?\s*$"),
    "ramp_points_no_linework": re.compile(r"(?i)Ramp Points w/out linework:?\s*$"),
}
_NUM_RE = re.compile(r"^-?[\d,]+$")


def env_fields():
    """The env comparison's display columns minus the Route key."""
    return [disp for _col, disp in _COL_DISP]


def tsmis_pdf_path(pdf_dir, route):
    return paths.resolve_route_file(pdf_dir,
                                    f"tsar_ramp_summary_route_{route}.pdf")


def _line_rows_with_boxes(words, left):
    """The word-box-keeping twin of _rs.get_rows_for_column for SINGLE-LINE
    rows: [(number_or_None, label_text, count_word, line_words)]. Multi-line
    (wrapped) labels are the parser's stitching business — their geometry is
    refused, their values still come from parse_pdf."""
    side = [w for w in words
            if (w["x0"] < _rs.COLUMN_SPLIT_X) == left]
    rows = []
    for _top, line_words in cluster_by_top(side, _rs.Y_TOLERANCE):
        line_words = sorted(line_words, key=lambda w: w["x0"])
        texts = [w["text"] for w in line_words]
        if not texts:
            continue
        number = None
        count_word = None
        rest = line_words
        if _NUM_RE.fullmatch(texts[0]):
            try:
                number = int(texts[0].replace(",", ""))
            except ValueError:   # silent-ok: a non-count token keeps its label row
                number = None
            count_word = line_words[0]
            rest = line_words[1:]
        label = _rs.clean_label(" ".join(w["text"] for w in rest))
        rows.append((number, label, count_word, line_words))
    return rows


def _attribute(rows, schema, used, cells):
    """The geometry twin of _rs.match_schema's ordered first-wins walk: assign
    each schema category the FIRST unused numbered row whose cleaned label
    matches its pattern, recording the count word's box. Cross-checked at
    lookup time against parse_pdf's own value, so a drift refuses geometry
    rather than mislabelling it."""
    for col, pattern in schema:
        for i, (number, label, count_word, line_words) in enumerate(rows):
            if i in used or number is None or count_word is None:
                continue
            if re.fullmatch(pattern, label):
                used.add(i)
                cells[col] = (count_word, line_words, number)
                break


def env_locate(pdf_path, needed_keys):
    """{normalized_route: [record]} — ONE record per print (the route's whole
    category table). The record carries the parser's own values plus per-
    category count-word geometry."""
    record = _rs.parse_pdf(pdf_path)
    route = compare_env._norm_route_key(record.get("route")
                                        or compare_env._route_from_name(Path(pdf_path)))
    if route not in needed_keys:
        return {}
    cells = {}
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 2:
            return {}
        page = pdf.pages[1]
        words = page.extract_words()
        left = _line_rows_with_boxes(words, left=True)
        right = _line_rows_with_boxes(words, left=False)
        used_left, used_right = set(), set()
        _attribute(left, _rs.HIGHWAY_GROUPS, used_left, cells)
        _attribute(left, _rs.ONOFF, used_left, cells)
        _attribute(left, _rs.POP_GROUPS, used_left, cells)
        _attribute(right, _rs.RAMP_TYPES, used_right, cells)
        # The two footer totals print as their own label lines with a trailing
        # count; they sit outside both columns' schema walks.
        for _top, line_words in cluster_by_top(list(words), _rs.Y_TOLERANCE):
            line_words = sorted(line_words, key=lambda w: w["x0"])
            texts = [w["text"] for w in line_words]
            if len(texts) < 2 or not _NUM_RE.fullmatch(texts[-1]):
                continue
            label = " ".join(texts[:-1])
            for col, label_re in _TOTAL_RES.items():
                if label_re.match(label):
                    try:
                        number = int(texts[-1].replace(",", ""))
                    except ValueError:   # silent-ok: not a count line; geometry stays absent (refusal)
                        continue
                    cells[col] = (line_words[-1], line_words, number)
    rec = {"record": record, "cells": cells, "src": str(pdf_path),
           "page": 2}
    return {route: [rec]}


def env_project(field, raw):
    del field
    return "" if raw is None else str(raw)


def env_value(rec, field):
    """The parser's OWN value for this category (never the geometry pass's)."""
    col = _DISP_TO_COL.get(field)
    if col is None:
        return ""
    return env_project(field, rec["record"].get(col))


def env_box(rec, field):
    """(page_no, cell_box, record_yspan, record_xspan) for the category's count
    word. Refuses when the geometry pass found no single-line row for the
    category, or its count text disagrees with the parser's value — geometry
    may cost an example, never mislabel one. An absent category prints no line
    at all, so a blank side has no rectangle and honestly refuses
    (PCOA-FINAL-005: no guessed boxes)."""
    col = _DISP_TO_COL.get(field)
    got = rec["cells"].get(col) if col is not None else None
    if got is None:
        return None
    count_word, line_words, number = got
    if env_value(rec, field) != env_project(field, number):
        return None
    y0 = min(w["top"] for w in line_words)
    y1 = max(w["bottom"] for w in line_words)
    xspan = (min(w["x0"] for w in line_words) - 4,
             max(w["x1"] for w in line_words) + 4)
    box = (count_word["x0"] - 2, count_word["top"] - 2,
           count_word["x1"] + 2, count_word["bottom"] + 2)
    return rec["page"], box, (y0, y1), xspan
