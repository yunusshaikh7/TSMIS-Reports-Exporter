"""Highway Sequence adapter for the visual-evidence generator (visual_evidence).

Supplies everything report-specific the engine needs to turn a Highway Sequence
vs-TSN diff into a pair of highlighted PDF snippets:

  * the DIFF SOURCE — both comparison sides re-loaded through the comparator's
    OWN loaders (compare_highway_sequence_tsn._load_tsmis / _load_tsn) and each
    cell judged by the engine's OWN compared-cell reader
    (compare_core.compared_cell), so an "example" is exactly a cell the
    comparison counts: the CONTEXT fields (HG / City / Distance To Next Point,
    non-asserting by schema) can never leak in;
  * the TSMIS locator — the same header-anchored page walk the Highway Sequence
    PDF consolidator uses, kept in LOCKSTEP with it (same boundaries, trailer
    stop, PM-less-row test, fragment attachment), but keeping each data line's
    page / y-extent / per-column word geometry and each wrapped Description
    fragment's own box;
  * the TSN locator — the district HSL print parsed with the TSN consolidator's
    fixed column windows, kept in LOCKSTEP with it likewise (group headers,
    carried county, the equate-annotation synthesis, ', ' description joins).

DISTRICT ROUTING — like the Highway Log, the Highway Sequence comparison rows
carry NO district, so a diff row cannot be mapped to one district print up
front. The adapter owns the fan-out (the highway-log pattern): every example
carries the SENTINEL district '' and `locate_tsn` receives the PDF FOLDER,
scanning every district print route-filtered; each returned record carries its
source print (`src`) plus the district (from the print's own "DIST NN RTE NNN"
group headers) and county (carried from the data lines), which the engine
prefers for rendering and captions. A key found in more than one print yields
multiple records and the engine's own uniqueness gate skips it — ambiguity can
only cost an example, never mislabel one.

Row identity matches the comparison: County + the glued postmile
(prefix+PM+suffix — compare_highway_sequence_tsn's key), restricted to keys
UNIQUE on both sides of a route so a highlight is THE row. Verification runs
each PDF cell back through the comparison's normalization before accepting an
example. Console-free; pdfplumber/openpyxl gated by the engine.
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

import compare_highway_sequence_tsn as chsl
import consolidate_tsmis_highway_sequence_pdf as chslp
import consolidate_tsn_highway_sequence as ctnsl
from compare_core import _xl_trim, compared_cell, published_key_text
from pdf_table_lib import norm_route, require_document_route

log = logging.getLogger("tsmis.evidence")

REPORT_LABEL = "Highway Sequence"
KEY_LABEL = "PM"
FIELDS = [f for f in chsl.SHARED_HEADER if f != KEY_LABEL]

# Shared field -> the TSMIS print's column key (chslp._COL_ORDER) and the TSN
# print's x-window. The TSMIS PM is split across prefix/pm/suffix windows; the
# TSN print glues it into one token, exactly like the comparison key.
_TSMIS_COL = {"County": "county", "City": "city", "PM": "pm", "HG": "hg",
              "FT": "ft", "Distance To Next Point": "dist",
              "Description": "desc"}
_TSN_WIN = {"County": ctnsl.W_COUNTY, "City": ctnsl.W_CITY, "PM": ctnsl.W_PM,
            "HG": ctnsl.W_FLAG, "FT": ctnsl.W_FLAG,
            "Distance To Next Point": ctnsl.W_DIST}


def _canon(county, glued_pm):
    """The within-route locating key: 'COUNTY POSTMILE' (county normalized the
    comparator's way — the TSMIS export writes 'LA.' where TSN writes 'LA').
    The string twin of the comparison rows' PhysicalKey identity."""
    return f"{chsl._norm_county(county)} {(glued_pm or '').strip()}".strip()


def _row_key(r):
    """A comparison row's locating key string, from its PhysicalKey identity
    (CMP-AUD-045: the key cell is typed; its canonical county/postmile carry
    the reserved '(county not printed)'/'(no postmile printed)' markers, which
    map back to blanks here so print lookups see the printed text)."""
    key = r[1 + chsl.KEY_FIELD]
    ident = getattr(key, "physical_identity", None)
    if ident is not None:
        comp = dict(ident.canonical_components)
        county = "" if comp["county"] == chsl._NO_COUNTY_KEY else comp["county"]
        pm = "" if comp["postmile"] == chsl._NO_PM_KEY else comp["postmile"]
        return f"{county} {pm}".strip()
    county = r[1 + chsl.SHARED_HEADER.index("County")]
    return f"{'' if county is None else str(county).strip()} " \
           f"{'' if key is None else str(key).strip()}".strip()


# --------------------------------------------------------------------------- #
# diff source — the comparator's own loaders + the engine's compared-cell reader
# --------------------------------------------------------------------------- #
def load_sides(consolidated_path, tsn_path):
    """(tsmis_rows, tsn_rows, sidecar, note) — both sides through the Highway
    Sequence comparator's own loaders/normalization. No district sidecar (see
    DISTRICT ROUTING above); `sidecar` is a truthy placeholder so the engine
    proceeds."""
    try:
        tsmis_rows, _ = chsl._load_tsmis(consolidated_path)
        tsn_rows, _ = chsl._load_tsn(tsn_path)
    except ValueError as e:
        return None, None, None, str(e)
    return tsmis_rows, tsn_rows, {"routing": "per-print"}, None


def enumerate_diffs(tsmis_rows, tsn_rows, sidecar):
    """{field: [example]} over composite keys UNIQUE per route on BOTH sides —
    each example a cell the comparison counts. Judged by compare_core's own
    compared_cell (the comparison's TRIM + context-field semantics), so
    inequality here == a red cell there; the HG / City / Distance context
    columns are non-asserting and can never enumerate. District/county are the
    sentinel '' — locate_tsn resolves prints itself."""
    del sidecar
    sc = chsl._SCHEMA
    key_field = chsl.KEY_FIELD
    a_route, b_route = defaultdict(list), defaultdict(list)
    # The A-side row's position rides along so the engine can address the exact
    # CONSOLIDATED-workbook cell an Excel-compared value came from (CMP-AUD-210).
    for i, r in enumerate(tsmis_rows):
        a_route[r[0]].append((i, r))
    for r in tsn_rows:
        b_route[r[0]].append(r)
    diffs = defaultdict(list)
    for route in sorted(set(a_route) & set(b_route)):
        a_ct, b_ct = defaultdict(int), defaultdict(int)
        a_by, b_by = {}, {}
        for i, r in a_route[route]:
            k = _row_key(r)
            a_ct[k] += 1
            a_by[k] = (i, r)
        for r in b_route[route]:
            k = _row_key(r)
            b_ct[k] += 1
            b_by[k] = r
        for key in set(a_by) & set(b_by):
            if a_ct[key] != 1 or b_ct[key] != 1:
                continue                       # duplicates -> the pairing's job
            (ia, ra), rb = a_by[key], b_by[key]
            pub_key = published_key_text(sc, ra)
            for f_idx, field in enumerate(chsl.SHARED_HEADER):
                if f_idx == key_field:         # the key column itself
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
def project(field, raw, side="tsmis", route=None):
    """A raw PDF cell value -> the compared form, per the comparator's own
    per-field normalization + the engine's Excel TRIM. Description is
    SIDE-AWARE (CMP-AUD-204): the TSMIS side strips its own-route leading
    label only; the TSN side is verbatim (numeric prefixes are authoritative
    source claims)."""
    if field == "Description":
        if side == "tsn":
            return _xl_trim(chsl._desc_plain(raw))
        return _xl_trim(chsl._desc_tsmis(raw, route))
    if field == "County":
        return _xl_trim(chsl._norm_county(raw))
    return _xl_trim(chsl._v(raw))


# --------------------------------------------------------------------------- #
# TSMIS side — the per-route "Highway Sequence Listing (PDF)" export
# --------------------------------------------------------------------------- #
def tsmis_pdf_path(pdf_dir, route):
    return Path(pdf_dir) / f"highway_sequence_route_{route}.pdf"


def _classify_line_words(line_words, b):
    """One text line's words -> {column: [word, ...]} on the consolidator's own
    boundaries — the word-object-keeping twin of chslp._classify_words (pinned
    against it in check_visual_evidence)."""
    cols = {k: [] for k in chslp._COL_ORDER}
    for w in line_words:
        xc = (w["x0"] + w["x1"]) / 2
        if xc >= b["dist_desc"]:
            cols["desc"].append(w)
        elif xc >= b["ft_dist"]:
            cols["dist"].append(w)
        elif xc >= b["hg_ft"]:
            cols["ft"].append(w)
        elif xc >= b["suffix_hg"]:
            cols["hg"].append(w)
        elif xc >= b["pm_suffix"]:
            cols["suffix"].append(w)
        elif xc >= b["prefix_pm"]:
            cols["pm"].append(w)
        elif xc >= b["city_prefix"]:
            cols["prefix"].append(w)
        elif xc >= b["county_city"]:
            cols["city"].append(w)
        else:
            cols["county"].append(w)
    return cols


def locate_tsmis(pdf_path, needed_keys):
    """{composite_key: [record]} for `needed_keys`; a record carries the parsed
    column words plus geometry (page, y-extent, boundaries, wrapped-Description
    fragment boxes).

    LOCKSTEP: this walk mirrors consolidate_tsmis_highway_sequence_pdf
    .parse_pdf step for step (per-page header windows, the trailer hard-stop,
    the PM / PM-less data tests, nearest-line fragment attachment, top-order
    desc assembly, the CMP-AUD-049 banner-claim capture) — it only ADDS
    position capture. A behavior change there must land here too;
    check_visual_evidence pins the shared pieces so a drift fails the gate.

    CMP-AUD-049 (evidence half): raises pdf_table_lib.RouteIdentityError when
    the document's own page-banner claims don't confirm the route the
    filename names — a renamed foreign-route PDF must never be captioned as
    the requested route."""
    found = defaultdict(list)
    doc_routes = set()                  # the pages' own route claims (049)
    stopped = False
    m = re.search(r"route_([0-9A-Za-z]+)\.pdf$", str(pdf_path))
    file_route = m.group(1) if m else None
    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            if stopped:
                break
            words = page.extract_words()
            hd = chslp._page_header(words)
            if hd is None:
                continue                    # the cover / legend pages
            b = chslp._boundaries(hd)
            hdr_bottom = max(w["bottom"] for w in hd.values())

            page_rows = []                  # mutable [top, cols, rec-or-None]
            frags = []                      # (top, bottom, x0, x1, text)
            for top, line_words in chslp._cluster_lines(words):
                if top <= hdr_bottom + 2:
                    bm = chslp.BANNER_ROUTE_RE.search(
                        " ".join(w["text"] for w in line_words))
                    if bm:
                        doc_routes.add(bm.group(1))
                    continue
                text = " ".join(w["text"] for w in line_words)
                if text.startswith(chslp.TRAILER_HEADING):
                    stopped = True
                    break
                cols = _classify_line_words(line_words, b)
                vals = {k: " ".join(w["text"] for w in ws)
                        for k, ws in cols.items()}
                if chslp.PM_RE.fullmatch(vals["pm"]) or chslp._is_pmless_data(vals):
                    page_rows.append([top, cols, vals, None])
                elif cols["desc"] and not any(
                        vals[k] for k in chslp._COL_ORDER if k != "desc"):
                    frags.append((top,
                                  max(w["bottom"] for w in cols["desc"]),
                                  min(w["x0"] for w in cols["desc"]),
                                  max(w["x1"] for w in cols["desc"]),
                                  vals["desc"]))
            for pr in page_rows:
                top, cols, vals, _ = pr
                glued = f"{vals['prefix']}{vals['pm']}{vals['suffix']}"
                canon = _canon(vals["county"], glued)
                if canon not in needed_keys:
                    continue
                line_words = [w for ws in cols.values() for w in ws]
                bottom = max(w["bottom"] for w in line_words)
                rec = {"cols": cols, "vals": vals, "boundaries": b,
                       "route": file_route,
                       "page": page_no, "top": top, "bottom": bottom,
                       "desc": []}
                if cols["desc"]:
                    rec["desc"].append({
                        "page": page_no, "top": top, "bottom": bottom,
                        "x0": min(w["x0"] for w in cols["desc"]),
                        "x1": max(w["x1"] for w in cols["desc"]),
                        "text": vals["desc"], "line_top": top})
                pr[3] = rec
                found[canon].append(rec)
            # Fragment attachment — the consolidator's nearest-data-line rule,
            # capturing each fragment's own box on kept records.
            for ftop, fbottom, fx0, fx1, ftext in frags:
                best = min(page_rows, key=lambda pr: abs(pr[0] - ftop),
                           default=None)
                if best is None or abs(best[0] - ftop) > chslp.FRAG_MAX_DIST:
                    continue
                if best[3] is not None:
                    best[3]["desc"].append({
                        "page": page_no, "top": ftop, "bottom": fbottom,
                        "x0": fx0, "x1": fx1, "text": ftext,
                        "line_top": ftop})
    # Assemble each kept record's Description exactly like the consolidator
    # (top-order, hyphen-aware join), so verification sees the parsed value.
    for recs in found.values():
        for rec in recs:
            parts = [(d["line_top"], d["text"]) for d in rec["desc"]]
            rec["vals"]["desc"] = chslp.join_desc_parts(
                [t for _, t in sorted(parts)])
    require_document_route(
        Path(pdf_path).name, norm_route(file_route) if file_route else None,
        [norm_route(t) for t in doc_routes],
        claim_desc="the page banner's \"Route: NNN\"")
    return found


def tsmis_value(rec, field):
    """The compared value this PDF record carries for `field` (verification).
    PM re-glues the print's prefix/PM/suffix windows, like the comparison; the
    record's own route (stamped at locate time) drives the own-route-label
    Description strip."""
    if field == "PM":
        v = rec["vals"]
        return project(field, f"{v['prefix']}{v['pm']}{v['suffix']}")
    return project(field, rec["vals"][_TSMIS_COL[field]],
                   route=rec.get("route"))


def tsmis_box(rec, field):
    """(page_no, cell_box, record_yspan, record_xspan) for `field`'s cell."""
    line_words = [w for ws in rec["cols"].values() for w in ws]
    xspan = (min(w["x0"] for w in line_words) - 4,
             max(w["x1"] for w in line_words) + 4)
    yspan = (rec["top"],
             max([rec["bottom"]] + [d["bottom"] for d in rec["desc"]]))
    if field == "Description":
        if not rec["desc"]:
            # a blank Description: box the gap where it would print
            x0 = rec["boundaries"]["dist_desc"] + 6
            return (rec["page"], (x0, rec["top"] - 2, x0 + 180,
                                  rec["bottom"] + 2), yspan, xspan)
        segs = rec["desc"]
        box = (min(d["x0"] for d in segs) - 2, min(d["top"] for d in segs) - 2,
               max(d["x1"] for d in segs) + 2, max(d["bottom"] for d in segs) + 2)
        return rec["page"], box, yspan, xspan
    ws = rec["cols"][_TSMIS_COL[field]]
    if ws:
        x0, x1 = min(w["x0"] for w in ws), max(w["x1"] for w in ws)
    else:
        # a blank cell: box its window zone, clipped near the line
        zone = {"County": ("county_city", -60), "City": ("city_prefix", -26),
                "HG": ("suffix_hg", 4), "FT": ("hg_ft", 8),
                "Distance To Next Point": ("ft_dist", 12), "PM": ("prefix_pm", 4)}
        bkey, off = zone[field]
        x0 = rec["boundaries"][bkey] + (off if off > 0 else 0)
        x0 = x0 + off if off < 0 else x0
        x1 = x0 + 30
    return (rec["page"],
            (x0 - 2, rec["top"] - 2, x1 + 2, rec["bottom"] + 2), yspan, xspan)


# --------------------------------------------------------------------------- #
# TSN side — the district HSL prints (fixed x-windows, per-print routing)
# --------------------------------------------------------------------------- #
def district_index(pdf_dir, events=None):
    """{'' : the prints FOLDER} — the sentinel single entry (the highway-log
    pattern). The Highway Sequence maps a diff row to its district print inside
    locate_tsn (see the module docstring); each returned record carries its own
    source path (`src`), which the engine prefers over this index when
    rendering."""
    del events
    return {"": Path(pdf_dir)}


def locate_tsn(pdf_dir, needed_routes, needed_keys):
    """{('', route, composite_key): [record]} scanning EVERY district print in
    `pdf_dir`, route-filtered. LOCKSTEP with consolidate_tsn_highway_sequence
    .parse_pdf (the group-header route switch, carried county, the
    equate-annotation synthesis, the column buckets, single-space description
    joins, verbatim pointer distance tokens) — it only ADDS position capture
    and the per-record district/county/src provenance."""
    found = defaultdict(list)
    for p in sorted(Path(pdf_dir).glob("*.pdf")):
        try:
            _scan_tsn_print(p, needed_routes, needed_keys, found)
        except Exception as e:                    # an unreadable/odd print
            log.warning("evidence: %s unparseable: %s: %s",
                        p.name, type(e).__name__, e)
    return found
# LOCKSTEP note: _scan_tsn_print above mirrors consolidate_tsn_highway_sequence
# .parse_pdf's v4 row rules — pointer distance tokens verbatim (CMP-AUD-156),
# pre-county equate annotations kept with a blank county (CMP-AUD-158), and
# single-space wrapped-description joins (CMP-AUD-159).


def _scan_tsn_print(path, needed_routes, needed_keys, found):
    route = None
    district = ""
    county = None
    open_rec = None
    open_row = None
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            for line in ctnsl._cluster_lines(words):
                text = " ".join(w["text"] for w in line)
                gm = ctnsl.GROUP_RE.search(text)
                if gm:
                    district = gm.group(1).zfill(2)
                    route = ctnsl._norm_route(gm.group(2))
                    county = None
                    open_rec = open_row = None
                    continue
                cols = ctnsl._parse_line(line)
                co = (cols.get("county") or [""])[0]
                pm = next((t for t in (cols.get("pm") or [])
                           if ctnsl.LOCATION_RE.match(t)), None)
                if "EQUATES" in text and pm and not ctnsl.COUNTY_RE.match(co):
                    # the synthetic equate-annotation row (county carried;
                    # a pre-county annotation keeps its blank county, exactly
                    # like the consolidator — CMP-AUD-158)
                    if route is None:
                        continue
                    open_row = dict(county=county, pm=pm, city=None, hg=None,
                                    ft=None, dist=None, description="EQUATES TO")
                    open_rec = _keep_tsn(found, needed_routes, needed_keys, path,
                                         district, county, route, open_row,
                                         page_no, line)
                    continue
                if ctnsl.COUNTY_RE.match(co) and pm:
                    if route is None:
                        continue
                    county = co.rstrip(".")
                    flag = "".join(cols.get("flag") or [])
                    desc = " ".join(cols.get("desc") or []).strip() or None
                    # verbatim first token — numeric distance OR the printed
                    # pointer markers, exactly like the consolidator (CMP-AUD-156)
                    dists = cols.get("dist") or []
                    dist = dists[0] if dists else None
                    open_row = dict(
                        county=county, pm=pm,
                        city=(cols.get("city") or [None])[0],
                        hg=(flag[0] if len(flag) >= 1 else None),
                        ft=(flag[1] if len(flag) >= 2 else None),
                        dist=dist, description=desc)
                    open_rec = _keep_tsn(found, needed_routes, needed_keys, path,
                                         district, county, route, open_row,
                                         page_no, line)
                    continue
                if (open_row is not None and cols.get("desc")
                        and not cols.get("county") and not cols.get("pm")):
                    extra = " ".join(cols["desc"]).strip()
                    if not extra:
                        continue
                    # single-space join, like the consolidator (CMP-AUD-159)
                    open_row["description"] = (
                        extra if not open_row["description"]
                        else open_row["description"] + " " + extra)
                    if open_rec is not None:
                        seg_words = [w for w in line
                                     if ctnsl._bucket(w["x0"]) == "desc"]
                        open_rec["desc"].append({
                            "page": page_no,
                            "top": min(w["top"] for w in seg_words),
                            "bottom": max(w["bottom"] for w in seg_words),
                            "x0": min(w["x0"] for w in seg_words),
                            "x1": max(w["x1"] for w in seg_words)})
    return found


def _keep_tsn(found, needed_routes, needed_keys, path, district, county, route,
              rowd, page_no, line):
    """Record `rowd` if its (route, key) is wanted; returns the record or None."""
    if route not in needed_routes:
        return None
    canon = _canon(county, rowd["pm"])
    if ("", route, canon) not in needed_keys:
        return None
    rec = {"rowd": rowd, "src": str(path), "dist": district, "cnty": county,
           "page": page_no,
           "top": min(w["top"] for w in line),
           "bottom": max(w["bottom"] for w in line),
           "words": list(line), "desc": []}
    if rowd.get("description"):
        seg_words = [w for w in line if ctnsl._bucket(w["x0"]) == "desc"]
        if seg_words:
            rec["desc"].append({
                "page": page_no,
                "top": min(w["top"] for w in seg_words),
                "bottom": max(w["bottom"] for w in seg_words),
                "x0": min(w["x0"] for w in seg_words),
                "x1": max(w["x1"] for w in seg_words)})
    found[("", route, canon)].append(rec)
    return rec


def tsn_value(rec, field):
    """The compared value this print record carries for `field` (TSN side:
    Description verbatim — CMP-AUD-204)."""
    key = {"County": "county", "PM": "pm", "City": "city", "HG": "hg",
           "FT": "ft", "Distance To Next Point": "dist",
           "Description": "description"}[field]
    return project(field, rec["rowd"].get(key), side="tsn")


def tsn_box(rec, field):
    """(page_no, cell_box, record_yspan, record_xspan) for `field`'s cell. The
    TSN flag column fuses HG+FT into one token — the box halves it; a wrapped
    Description that continued onto another page is rejected (None), like the
    highway-log adapter."""
    words = rec["words"]
    xspan = (min(w["x0"] for w in words) - 4, max(w["x1"] for w in words) + 4)
    same_page_desc = [d for d in rec["desc"] if d["page"] == rec["page"]]
    yspan = (rec["top"],
             max([rec["bottom"]] + [d["bottom"] for d in same_page_desc]))
    if field == "Description":
        segs = [d for d in rec["desc"]]
        base = [w for w in words if ctnsl._bucket(w["x0"]) == "desc"]
        if base:
            segs = [{"page": rec["page"], "top": rec["top"],
                     "bottom": rec["bottom"],
                     "x0": min(w["x0"] for w in base),
                     "x1": max(w["x1"] for w in base)}] + rec["desc"]
        if not segs:
            lo, hi = ctnsl.W_DESC
            return (rec["page"], (lo, rec["top"] - 2, lo + 180,
                                  rec["bottom"] + 2), yspan, xspan)
        if {d["page"] for d in segs} != {rec["page"]}:
            return None                          # split across pages
        box = (min(d["x0"] for d in segs) - 2, min(d["top"] for d in segs) - 2,
               max(d["x1"] for d in segs) + 2, max(d["bottom"] for d in segs) + 2)
        return rec["page"], box, yspan, xspan
    lo, hi = _TSN_WIN[field]
    hits = [w for w in words if lo <= w["x0"] < hi]
    if hits:
        x0, x1 = min(w["x0"] for w in hits), max(w["x1"] for w in hits)
        if field in ("HG", "FT") and hits:
            # one fused 2-char flag token: halve it (HG left, FT right)
            mid = (x0 + x1) / 2
            x0, x1 = (x0, mid) if field == "HG" else (mid, x1)
    else:
        x0, x1 = lo, min(hi, lo + 30)
    return (rec["page"],
            (x0 - 2, rec["top"] - 2, x1 + 2, rec["bottom"] + 2), yspan, xspan)
