"""Highway Log adapter for the visual-evidence generator (visual_evidence).

Supplies everything report-specific the engine needs to turn a Highway Log
vs-TSN diff into a pair of highlighted PDF snippets:

  * the DIFF SOURCE — both comparison sides re-loaded through the comparator's
    OWN loader (compare_highway_log._load_input) and each cell judged by the
    engine's OWN compared-cell reader (compare_core.compared_cell), so an
    "example" is exactly a cell the comparison flags: the `+`-run DITTO cells
    (non-asserting by schema) and the Med Wid normalization can never leak in;
  * the TSMIS locator — the same per-page zebra-rect window walk the Highway
    Log PDF consolidator uses, kept in LOCKSTEP with it, but keeping each data
    line's page / y-extent / column geometry and each Description line's own
    box (the print puts descriptions on their own lines below the row);
  * the TSN locator — the district OTM52010 print parsed with the consolidator's
    fixed document-wide column windows, kept in LOCKSTEP with it likewise.

DISTRICT ROUTING — the Highway Log's 31 columns carry NO county/district, so a
diff row cannot be mapped to one district print up front (Highway Detail does
that from its TSN-library sidecar). Instead the adapter owns the fan-out: every
example carries the SENTINEL district '' and `locate_tsn` receives the PDF
FOLDER, scanning every district print route-filtered; each returned record
carries its source print (`src`) plus the district/county it was printed under
(from the print's own group headers), which the engine prefers for rendering
and captions. A key found in more than one print yields multiple records and
the engine's own uniqueness gate skips it — ambiguity can only cost an example,
never mislabel one.

Row identity matches the comparison: the canonical roadbed-aware Location key
(highway_log_columns.roadbed_canonical_location), restricted to keys UNIQUE on
both sides of a route so a highlight is THE row. Verification runs each PDF
cell back through the comparison's normalization (`_hl_normalize` + Excel TRIM)
before accepting an example. Console-free; pdfplumber/openpyxl gated by the
engine.
"""
import logging
import re
from collections import defaultdict
from pathlib import Path

try:
    import pdfplumber
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_highway_log as chl
import consolidate_tsmis_highway_log_pdf as chlp
import consolidate_tsn_highway_log as ctnl
import highway_log_columns as hlc
from compare_core import _xl_trim, compared_cell, published_key_text
from pdf_table_lib import require_document_route

log = logging.getLogger("tsmis.evidence")

REPORT_LABEL = "Highway Log"
KEY_LABEL = hlc.HEADER[0]                     # "Location"
FIELDS = [f for f in hlc.HEADER if f != KEY_LABEL]

# Shared field -> the TSN consolidator's fixed column-window key. ROW_KEYS is
# already in TSMIS column order (Description filled from follow-on lines), so
# the mapping is positional; Description has no window (its own lines).
_TSN_WIN_KEY = dict(zip(hlc.HEADER, ctnl.ROW_KEYS))
_TSN_WINDOWS = {key: (lo, hi) for key, lo, hi in ctnl.COLUMN_WINDOWS}
_DESC_IDX = hlc.DESC_IDX                      # 28


def _canon(row, off=0):
    """The comparison's canonical roadbed-aware Location key for a loaded row."""
    return hlc.roadbed_canonical_location(row, off=off, key_field=0)


# --------------------------------------------------------------------------- #
# diff source — the comparator's own loader + the engine's compared-cell reader
# --------------------------------------------------------------------------- #
def load_sides(consolidated_path, tsn_path):
    """(tsmis_rows, tsn_rows, sidecar, note) — both sides through the Highway
    Log comparator's own loader/normalization. The Highway Log needs no
    district sidecar (see DISTRICT ROUTING above); `sidecar` is a truthy
    placeholder so the engine proceeds."""
    tsmis_rows, has_route_a = chl._load_input(consolidated_path)
    tsn_rows, has_route_b = chl._load_input(tsn_path)
    if not has_route_a or not has_route_b:
        return None, None, None, ("evidence needs the CONSOLIDATED workbooks "
                                  "(a leading Route column) — per-route files "
                                  "don't say which route they are")
    return tsmis_rows, tsn_rows, {"routing": "per-print"}, None


def enumerate_diffs(tsmis_rows, tsn_rows, sidecar):
    """{field: [example]} over canonical keys UNIQUE per route on BOTH sides —
    each example a cell the comparison flags. Judged by compare_core's own
    compared_cell (the comparison's TRIM / Med Wid / non-asserting-ditto
    semantics), so inequality here == a red cell there. District/county are the
    sentinel '' — locate_tsn resolves prints itself."""
    del sidecar
    sc = chl._SCHEMA
    a_route, b_route = defaultdict(list), defaultdict(list)
    # The A-side row's position is carried through so the engine can address the
    # exact CONSOLIDATED-workbook cell an Excel-compared value came from
    # (CMP-AUD-210); the TSN side is always evidenced from its print.
    for i, r in enumerate(tsmis_rows):
        a_route[r[0]].append((i, r))
    for r in tsn_rows:
        b_route[r[0]].append(r)
    diffs = defaultdict(list)
    for route in sorted(set(a_route) & set(b_route)):
        a_ct, b_ct = defaultdict(int), defaultdict(int)
        a_by, b_by = {}, {}
        for i, r in a_route[route]:
            k = _canon(r, off=1)
            a_ct[k] += 1
            a_by[k] = (i, r)
        for r in b_route[route]:
            k = _canon(r, off=1)
            b_ct[k] += 1
            b_by[k] = r
        for key in set(a_by) & set(b_by):
            if a_ct[key] != 1 or b_ct[key] != 1:
                continue                       # duplicates -> the pairing's job
            (ia, ra), rb = a_by[key], b_by[key]
            pub_key = published_key_text(sc, ra)
            for f_idx, field in enumerate(hlc.HEADER):
                if f_idx == 0:                 # the key column itself
                    continue
                cell = compared_cell(sc, f_idx, ra, rb, 1)
                if cell.verdict is False:
                    diffs[field].append(dict(
                        route=route, key=key, field=field,
                        va=cell.display_a, vb=cell.display_b,
                        dist="", cnty="", row_index=ia,
                        pub_key=pub_key, display=cell.display))
    return diffs


# --------------------------------------------------------------------------- #
# verification projection
# --------------------------------------------------------------------------- #
def project(field, raw):
    """A raw PDF cell value -> the compared form: the comparator's load
    normalization (tab/newline collapse) + the engine's Excel TRIM. `field` is
    unused (every Highway Log column normalizes alike; Med Wid equivalence is
    the COMPARISON's verdict, while va/vb stay display forms)."""
    del field
    return _xl_trim(chl._hl_normalize(raw))


# --------------------------------------------------------------------------- #
# TSMIS side — the per-route "Highway Log (PDF)" export (zebra-rect windows)
# --------------------------------------------------------------------------- #
def tsmis_pdf_path(pdf_dir, route):
    return Path(pdf_dir) / f"highway_log_route_{route}.pdf"


def locate_tsmis(pdf_path, needed_keys):
    """{canonical_key: [record]} for `needed_keys`; a record carries the parsed
    31-column row plus geometry (page, y-extent, windows, chars, description
    line boxes).

    LOCKSTEP: this walk mirrors consolidate_tsmis_highway_log_pdf.parse_pdf
    step for step (per-page zebra-rect windows with carry-forward, the
    header-bottom cutoff, the URL/totals/group-header guards, the col0_right
    data test, description lines joined with a SPACE, the CMP-AUD-049 cover
    "Route NNN" capture) — it only ADDS position capture. A behavior change
    there must land here too; check_visual_evidence pins the shared pieces so
    a drift fails the gate.

    CMP-AUD-049 (evidence half): raises pdf_table_lib.RouteIdentityError when
    the document's own cover claim doesn't confirm the route the filename
    names."""
    found = defaultdict(list)
    doc_route = None                   # the cover's own route claim (049)
    fm = re.search(r"route_([0-9A-Za-z]+)\.pdf$", str(pdf_path))
    file_route = fm.group(1) if fm else None
    with pdfplumber.open(pdf_path) as pdf:
        page_windows = None
        col0_right = None
        open_rec = None                # the kept record desc lines attach to
        open_row = None                # the parser's last_row (kept or not)
        for page_no, page in enumerate(pdf.pages, 1):
            derived = chlp._page_column_windows(page)
            if derived is not None:
                page_windows, col0_right = derived
            page_has_own_geometry = derived is not None

            lines = chlp._cluster_lines(page)
            hdr_bottom = chlp._header_bottom(lines)
            cutoff = ((hdr_bottom + chlp.HEADER_EPS) if hdr_bottom is not None
                      else chlp.HEADER_BAND)
            for top, words, line_chars in lines:
                texts = [w["text"] for w in words]
                if not texts:
                    continue
                if any(chlp.URL_MARK in t for t in texts):
                    continue
                if doc_route is None and len(texts) == 2:
                    cm = chlp.ROUTE_HEADER_RE.match(" ".join(texts))
                    if cm:
                        doc_route = chlp._norm_route(cm.group(1))
                        continue
                if top <= cutoff:
                    continue
                first_x0 = words[0]["x0"]
                # POSITIONAL star-guard (the parser's twin): a left-margin
                # totals star closes the record; a description-band star line
                # is a PRINTED description and falls through to attach.
                if texts[0].startswith("*") and (col0_right is None
                                                 or first_x0 < col0_right):
                    open_rec = open_row = None
                    continue
                if (len(texts) >= 3 and first_x0 > page.width * 0.30
                        and chlp.GROUP_RE[0].match(texts[0])
                        and chlp.GROUP_RE[1].match(texts[1])
                        and chlp.GROUP_RE[2].match(texts[2])):
                    open_rec = open_row = None
                    continue
                if page_windows is None:
                    continue
                is_data = (
                    (chlp.LOCATION_RE.match(texts[0]) and first_x0 < col0_right)
                    or (len(texts) >= 2 and len(texts[0]) == 1
                        and texts[0].isalpha()
                        and chlp.LOCATION_RE.match(texts[1])
                        and first_x0 < col0_right))
                if is_data:
                    vals = chlp._assign_columns(line_chars, page_windows)
                    row = chlp._make_row(vals, None)
                    open_row = row
                    canon = _canon(row, off=0)
                    if canon in needed_keys:
                        open_rec = {
                            "row": row, "page": page_no,
                            "top": top,
                            "bottom": max(c["bottom"] for c in line_chars),
                            "chars": line_chars, "windows": page_windows,
                            "approx": not page_has_own_geometry,
                            "desc": []}
                        found[canon].append(open_rec)
                    else:
                        open_rec = None
                    continue
                if open_row is not None and first_x0 >= col0_right:
                    text = " ".join(texts)
                    if open_row[_DESC_IDX]:
                        open_row[_DESC_IDX] += " " + text
                    else:
                        open_row[_DESC_IDX] = text
                    if open_rec is not None:
                        # y/x extents from the line CHARS — the char_lines word
                        # tokens carry only text/x0/x1.
                        open_rec["desc"].append({
                            "page": page_no, "top": top,
                            "bottom": max(c["bottom"] for c in line_chars),
                            "x0": first_x0,
                            "x1": max(c["x1"] for c in line_chars)})
    require_document_route(
        Path(pdf_path).name,
        chlp._norm_route(file_route) if file_route else None,
        [doc_route] if doc_route else [],
        claim_desc="the cover's \"Route NNN\" line")
    return found


def tsmis_value(rec, field):
    """The compared value this PDF record carries for `field` (verification)."""
    return project(field, rec["row"][hlc.HEADER.index(field)])


def _line_cell_box(chars, windows, idx, top, bottom):
    """The cell box for column `idx` on one parsed data line: its characters'
    extent, or the (contiguous) window bounds clipped to the line's own char
    extent for a BLANK cell (the first/last windows extend to infinity)."""
    lo, hi = windows[idx]
    hits = [c for c in chars if lo <= (c["x0"] + c["x1"]) / 2 < hi]
    if hits:
        x0, x1 = min(c["x0"] for c in hits), max(c["x1"] for c in hits)
    else:
        line_x0 = min(c["x0"] for c in chars)
        line_x1 = max(c["x1"] for c in chars)
        x0, x1 = max(lo, line_x0 - 6), min(hi, line_x1 + 6)
        if x1 <= x0:
            x0, x1 = lo, lo + 10
    return x0 - 2, top - 2, x1 + 2, bottom + 2


def tsmis_box(rec, field):
    """(page_no, cell_box, record_yspan, record_xspan) for `field`'s cell.
    Rejects (None) a record parsed with carried-forward page geometry — not
    evidence-grade — and a Description that spans pages."""
    if rec["approx"]:
        return None
    chars = rec["chars"]
    xspan = (min(c["x0"] for c in chars) - 4, max(c["x1"] for c in chars) + 4)
    same_page_desc = [d for d in rec["desc"] if d["page"] == rec["page"]]
    yspan = (rec["top"],
             max([rec["bottom"]] + [d["bottom"] for d in same_page_desc]))
    if field == "Description":
        if not rec["desc"]:
            # a blank Description: box the gap under the data line
            return (rec["page"],
                    (xspan[0] + 40, rec["bottom"], xspan[0] + 220,
                     rec["bottom"] + 10), yspan, xspan)
        pages = {d["page"] for d in rec["desc"]}
        if len(pages) > 1:
            return None                          # split across pages
        segs = rec["desc"]
        box = (min(d["x0"] for d in segs) - 2, min(d["top"] for d in segs) - 2,
               max(d["x1"] for d in segs) + 2, max(d["bottom"] for d in segs) + 2)
        return segs[0]["page"], box, yspan, xspan
    pos = hlc.HEADER.index(field)
    idx = pos if pos < _DESC_IDX else pos - 1    # 30 PDF cells skip Description
    return (rec["page"],
            _line_cell_box(chars, rec["windows"], idx, rec["top"], rec["bottom"]),
            yspan, xspan)


# --------------------------------------------------------------------------- #
# TSN side — the district OTM52010 prints (fixed document-wide windows)
# --------------------------------------------------------------------------- #
def district_index(pdf_dir, events=None):
    """{'' : the prints FOLDER} — the sentinel single entry. The Highway Log
    maps a diff row to its district print inside locate_tsn (see the module
    docstring); each returned record carries its own source path (`src`),
    which the engine prefers over this index when rendering."""
    del events
    return {"": Path(pdf_dir)}


def locate_tsn(pdf_dir, needed_routes, needed_keys):
    """{('', route, canonical_key): [record]} scanning EVERY district print in
    `pdf_dir`, route-filtered. LOCKSTEP with consolidate_tsn_highway_log
    .parse_pdf (header band, totals close, district/group headers, the
    fixed-window char parse, `_normalize_row`, the description x-band +
    totals-pattern guards, ', ' joins) — it only ADDS position capture and the
    per-record district/county/src provenance."""
    found = defaultdict(list)
    for p in sorted(Path(pdf_dir).glob("*.pdf")):
        try:
            _scan_tsn_print(p, needed_routes, needed_keys, found)
        except Exception as e:                    # an unreadable/odd print
            log.warning("evidence: %s unparseable: %s: %s",
                        p.name, type(e).__name__, e)
    return found


def _scan_tsn_print(path, needed_routes, needed_keys, found):
    district = None
    route = None
    county = ""
    open_rec = None
    open_row = None
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            for top, words, line_chars in ctnl._lines(page):
                if top < ctnl.HEADER_BAND:
                    continue
                texts = [w["text"] for w in words]
                first = words[0]
                if texts[0].startswith("*"):
                    open_rec = open_row = None
                    continue
                m = ctnl.DISTRICT_LINE_RE.match(" ".join(texts))
                if m and district is None:
                    district = m.group(1).zfill(2)
                    continue
                if (len(texts) >= 3 and 250 <= first["x0"] <= 305
                        and ctnl.GROUP_RE[0].match(texts[0])
                        and ctnl.GROUP_RE[1].match(texts[1])
                        and ctnl.GROUP_RE[2].match(texts[2])):
                    district = district or texts[0].zfill(2)
                    county = texts[1]
                    route = ctnl._norm_route(texts[2])
                    open_rec = open_row = None
                    continue
                if ctnl.LOCATION_RE.match(texts[0]) and first["x0"] < 50:
                    if route is None or route not in needed_routes:
                        open_rec = open_row = None
                        continue
                    rowd = ctnl._parse_data_line(line_chars)
                    ctnl._normalize_row(rowd)
                    rowd["description"] = None
                    open_row = rowd
                    row31 = [rowd.get(k) for k in ctnl.ROW_KEYS]
                    canon = _canon(row31, off=0)
                    if ("", route, canon) in needed_keys:
                        open_rec = {
                            "rowd": rowd, "src": str(path),
                            "dist": district or "", "cnty": county,
                            "page": page_no, "top": top,
                            "bottom": max(c["bottom"] for c in line_chars),
                            "chars": line_chars, "desc": []}
                        found[("", route, canon)].append(open_rec)
                    else:
                        open_rec = None
                    continue
                if open_row is not None:
                    if not (ctnl.DESC_X0_MIN <= first["x0"] <= ctnl.DESC_X0_MAX):
                        continue
                    text = " ".join(texts)
                    if ctnl._is_totals_line(text):
                        continue
                    open_row["description"] = (
                        text if not open_row["description"]
                        else open_row["description"] + ", " + text)
                    if open_rec is not None:
                        # y/x extents from the line CHARS — the char_lines word
                        # tokens carry only text/x0/x1.
                        open_rec["desc"].append({
                            "page": page_no, "top": top,
                            "bottom": max(c["bottom"] for c in line_chars),
                            "x0": first["x0"],
                            "x1": max(c["x1"] for c in line_chars)})


def tsn_value(rec, field):
    """The compared value this print record carries for `field`."""
    if field == "Description":
        return project(field, rec["rowd"].get("description"))
    return project(field, rec["rowd"].get(_TSN_WIN_KEY[field]))


def tsn_box(rec, field):
    """(page_no, cell_box, record_yspan, record_xspan) for `field`'s cell."""
    chars = rec["chars"]
    xspan = (min(c["x0"] for c in chars) - 4, max(c["x1"] for c in chars) + 4)
    same_page_desc = [d for d in rec["desc"] if d["page"] == rec["page"]]
    yspan = (rec["top"],
             max([rec["bottom"]] + [d["bottom"] for d in same_page_desc]))
    if field == "Description":
        if not rec["desc"]:
            return (rec["page"],
                    (ctnl.DESC_X0_MIN, rec["bottom"],
                     ctnl.DESC_X0_MIN + 180, rec["bottom"] + 10), yspan, xspan)
        pages = {d["page"] for d in rec["desc"]}
        if len(pages) > 1:
            return None
        segs = rec["desc"]
        box = (min(d["x0"] for d in segs) - 2, min(d["top"] for d in segs) - 2,
               max(d["x1"] for d in segs) + 2, max(d["bottom"] for d in segs) + 2)
        return segs[0]["page"], box, yspan, xspan
    lo, hi = _TSN_WINDOWS[_TSN_WIN_KEY[field]]
    hits = [c for c in chars if lo <= (c["x0"] + c["x1"]) / 2 < hi]
    if hits:
        x0, x1 = min(c["x0"] for c in hits), max(c["x1"] for c in hits)
    else:
        x0, x1 = lo, hi
    return (rec["page"],
            (x0 - 2, rec["top"] - 2, x1 + 2, rec["bottom"] + 2), yspan, xspan)
