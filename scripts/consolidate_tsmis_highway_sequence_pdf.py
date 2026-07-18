"""Convert TSMIS Highway Sequence (PDF) exports into TSMIS-format Excel and combine.

The TSMIS "Highway Sequence Listing (PDF)" export (report 3b — the site's Print
layout saved via `page.pdf()`) renders the "Highway Locations" listing as a
portrait Letter print: a parameters cover page, a legend page, then data pages.
Like the other PDF editions, the PDF and the Excel export are two renders of the
same data that CAN disagree (a statewide census found the print carrying a
Description the Excel export dropped), so this consolidator parses the per-route
PDFs into the SAME 9-column TSMIS Highway Sequence format the Excel export
produces, so:
  * the combined workbook lines up column-for-column with the Excel-consolidated
    workbook and the normalized TSN library (for the TSMIS-PDF vs TSN comparison),
  * and it can be diffed against the Excel export to pinpoint exactly which
    cells the two sources disagree on (the TSMIS-PDF vs TSMIS-Excel check).

The inputs ARE this app's own exports: the "Highway Sequence Listing (PDF)"
export saves the per-route PDFs (highway_sequence_route_<ROUTE>.pdf) to
output/<run>/highway_sequence_pdf/, so this consolidator reads that export
folder day-aware, exactly like the Excel consolidator.

PARSING — header-anchored column windows, censused statewide on the 252-route
7.9 export set against the 7.8 Excel exports (60,493 rows; every residual
difference class explained — see docs/tsn-parsers.md):
  * Every data page repeats the column header (COUNTY CITY PM HG FT
    "DISTANCE TO NEXT POINT" DESCRIPTION); the page's x-windows derive from it.
    The postmile PREFIX (realignment codes C,D,G,H,L,M,N,R,S,T) and the equate
    SUFFIX ("E") print in their own narrow windows beside PM — the same two
    unnamed columns the Excel export carries.
  * A LONG Description WRAPS: the print centers the row's other cells vertically
    among the desc lines, so a wrapped row clusters as desc-only fragment lines
    around a data line. Fragments attach to the nearest data line and the parts
    join top-to-bottom — bare after a hyphen ("UC 55-" + "1107" -> "UC 55-1107";
    HTML breaks after a hyphen when no space is near), with one space otherwise
    (HTML wraps at spaces and collapses whitespace runs, like every HTML render
    of this report).
  * A few rows carry NO postmile ("END OF ROUTE …", "CITY END: …",
    "COUNTY END: …") — matched by their single-letter HG/FT windows instead.
  * EQUATES print the TSN way (an annotation row "EQUATES TO <label>" at the
    realignment postmile with HG/FT/Distance blank, the "E" suffix on the
    equated plain postmile) while the Excel export writes the label alone and
    sometimes seats the E elsewhere. Values are written through VERBATIM — the
    representation difference is honest and documented; the PDF side actually
    pairs BETTER against TSN, whose prints use the same convention.
  * The print ends with an "Unresolved Intersections" diagnostics section on
    the last page (site-side translate failures, not report data) — parsing
    hard-stops at its heading.

No value normalization happens here: the PDF already carries the native TSMIS
formats, so values are written through verbatim. The comparison engine applies
any normalization at compare time, exactly as for the Excel side.

Console-free like the other consolidators: progress via events.on_log,
overwrite confirmed through the callback, cancel honored between pages,
ConsolidateResult returned. The console UX lives in cli.run_consolidate_cli.
"""
import logging
import re
from pathlib import Path

# pdfplumber wraps pdfminer.six, which logs noisy per-page font warnings for the
# site's embedded fonts; parsing is unaffected (see consolidate_tsmis_highway_log_pdf).
logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import pdfplumber
    import openpyxl  # noqa: F401 — the gate covers both the PDF and XLSX deps
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import outcome
from pdf_table_lib import (norm_route, page_has_postmile, reconcile_route_identity,
                           run_pdf_conversion, unexpected_pm_tokens,
                           write_route_workbook)
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

# These PDFs ARE produced by this app's "Highway Sequence Listing (PDF)" export
# (report 3b), saved to output/<run>/highway_sequence_pdf/. So this consolidator
# reads that EXPORT folder, day-aware, exactly like the Excel consolidator.
SUBDIR = "highway_sequence_pdf"
FILENAME = "tsmis_highway_sequence_pdf_consolidated.xlsx"

# Legacy flat-layout location (pre-dated exports, or a manual drop on a machine
# that can't run the export itself); used when no dated output/<run>/ folders exist.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
CONVERTED_DIR = OUTPUT_ROOT / "tsmis_highway_sequence_pdf"   # scratch per-route wb
OUT_PATH = OUTPUT_ROOT / FILENAME                            # legacy flat output

# Friendly report name for user-facing messages (UI-neutral).
REPORT_NAME = "TSMIS Highway Sequence (PDF)"

# File pattern the GUI uses to preview how many inputs a folder holds.
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"

# Must match the Highway Sequence Excel export exactly (sheet name AND header —
# including its two UNNAMED columns, the postmile prefix and the equate suffix),
# so the converted files consolidate with the same core and the combined workbook
# is column-compatible with the Excel export and the normalized TSN library.
SHEET_NAME = "Highway Locations"
HEADER = ("County", "City", None, "PM", None, "HG", "FT",
          "Distance To Next Point", "Description")


def input_dir_for(day):
    """The 'Highway Sequence Listing (PDF)' export PDFs for `day` (a run-folder
    name); None = the legacy flat layout."""
    return (output_day_dir(day) / SUBDIR) if day else INPUT_DIR


def out_path_for(day):
    """Combined workbook destination for `day` (a run-folder name); None = the
    legacy location. The dated filename carries the run's date + source/environment
    so a copy lifted out of its folder keeps its provenance."""
    if not day:
        return OUT_PATH
    return output_day_dir(day) / "consolidated" / stamped_consolidated_filename(FILENAME, day)


# =============================================================================
# PDF layout — censused statewide on the 7.9 export set (see module docstring)
# =============================================================================

LINE_TOL = 2.0        # words within this top-delta form one text line
# A wrapped row's desc fragments sit 6pt (two desc lines) or 12pt (three) from
# their data line, while DISTINCT rows are >= 14.2pt apart — so a fragment more
# than this far from every data line is unattributable (loud, never guessed).
FRAG_MAX_DIST = 13.0

PM_RE = re.compile(r"^\d{3}\.\d{3}$")
# The accepted, versioned post-mile CODE vocabulary (CMP-AUD-063). The legend's
# realignment PREFIX codes, and the equate SUFFIX ("E") — its one documented
# nonblank value. Anything else in either window alters the canonical postmile
# key, so the parser counts it as a `bad_token` and the producer escalates to
# PARTIAL (never silently complete). Bump PM_VOCAB_VERSION when the site's legend
# adds a code (a deliberate, censused change), so the escalation stays a durable
# contract. The 7.9 statewide census (252 HSL PDFs) saw ONLY these tokens.
PM_VOCAB_VERSION = 1
PREFIX_SET = frozenset("CDGHLMNRST")
SUFFIX_SET = frozenset("E")           # the equate suffix — the only nonblank one
HG_SET = frozenset("DURLX")           # highway-group codes (legend)
FT_SET = frozenset("HIR")             # file-type codes (legend)
# The last page ends with a site-side diagnostics section — not report data.
TRAILER_HEADING = "Unresolved Intersections"
# The seven column-header words every data page repeats.
_HEADER_WORDS = ("COUNTY", "CITY", "PM", "HG", "FT", "NEXT", "DESCRIPTION")
# Route token out of "highway_sequence_route_<ROUTE>.pdf".
ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]?)", re.IGNORECASE)
# The document's own route claim: every data page's banner line above the
# column header ("District: 10 Route: 004 Direction: W – E" — censused on the
# 7.9 statewide set, suffixed routes print as one token, "005S"). CMP-AUD-049:
# this in-document claim, not the filename, is the authoritative identity.
BANNER_ROUTE_RE = re.compile(r"\bRoute:\s*([0-9]+[A-Za-z]?)\b")


def _page_header(words):
    """The page's column-header words -> {text: word}, or None when this page has
    no data table (the cover/legend pages)."""
    hd = {}
    for w in words:
        if w["text"] in _HEADER_WORDS and w["text"] not in hd:
            hd[w["text"]] = w
    return hd if len(hd) == len(_HEADER_WORDS) else None


def _boundaries(hd):
    """The column boundaries for one page, anchored to ITS header positions
    (stable to ±1pt across the statewide set, but derived per page anyway).
    Data zones sit slightly off the header text — offsets censused statewide:
    PM data starts ~9pt left of its header; the suffix window opens right of the
    PM zone; prefix letters print between the City and PM zones."""
    return {
        "county_city": hd["CITY"]["x0"] - 4,
        "city_prefix": hd["CITY"]["x0"] + 30,
        "prefix_pm": hd["PM"]["x0"] - 10,
        "pm_suffix": hd["PM"]["x1"] + 12,
        "suffix_hg": hd["HG"]["x0"] - 4,
        "hg_ft": hd["FT"]["x0"] - 4,
        "ft_dist": hd["FT"]["x1"] + 8,
        "dist_desc": hd["DESCRIPTION"]["x0"] - 6,
    }


_COL_ORDER = ("county", "city", "prefix", "pm", "suffix", "hg", "ft", "dist", "desc")


def _classify_words(line_words, b):
    """One text line's words -> {column: joined text} by word center."""
    cols = {k: [] for k in _COL_ORDER}
    for w in line_words:
        xc = (w["x0"] + w["x1"]) / 2
        if xc >= b["dist_desc"]:
            cols["desc"].append(w["text"])
        elif xc >= b["ft_dist"]:
            cols["dist"].append(w["text"])
        elif xc >= b["hg_ft"]:
            cols["ft"].append(w["text"])
        elif xc >= b["suffix_hg"]:
            cols["hg"].append(w["text"])
        elif xc >= b["pm_suffix"]:
            cols["suffix"].append(w["text"])
        elif xc >= b["prefix_pm"]:
            cols["pm"].append(w["text"])
        elif xc >= b["city_prefix"]:
            cols["prefix"].append(w["text"])
        elif xc >= b["county_city"]:
            cols["city"].append(w["text"])
        else:
            cols["county"].append(w["text"])
    return {k: " ".join(v) for k, v in cols.items()}


def _is_pmless_data(vals):
    """A data row with an EMPTY postmile ("END OF ROUTE …", "CITY END: …"):
    single-letter HG *and* FT in their windows, a description, and nothing in
    the prefix/PM/suffix zones. The page furniture never matches (its words
    span the windows or land mid-zone as multi-letter tokens)."""
    return (not vals["pm"] and not vals["prefix"] and not vals["suffix"]
            and vals["desc"]
            and vals["hg"] in HG_SET and vals["ft"] in FT_SET)


def join_desc_parts(parts):
    """Join a wrapped Description's line texts top-to-bottom: bare after a
    hyphen (the HTML wrap split a hyphenated token — "UC 55-"+"1107"), with one
    space otherwise (the wrap swallowed a space). Mirrors the Highway Detail
    consolidator's wrap-join rule; shared with the evidence adapter."""
    out = ""
    for p in parts:
        if not p:
            continue
        if not out:
            out = p
        elif out.endswith("-"):
            out += p
        else:
            out += " " + p
    return out


def _cluster_lines(words):
    """Group extracted words into text lines by top (±LINE_TOL), each line's
    words x-sorted. Returns [(top, [word, ...]), ...] in reading order."""
    lines = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1][0]) <= LINE_TOL:
            lines[-1][1].append(w)
        else:
            lines.append((w["top"], [w]))
    return [(top, sorted(ws, key=lambda w: w["x0"])) for top, ws in lines]


def parse_pdf(path, events):
    """Parse one TSMIS Highway Sequence (PDF) export into 9-column TSMIS-format
    rows (see HEADER). Returns (rows, stats): rows in document order; stats a
    reconciliation dict (emitted, pages, data_pages, plus the loud counters —
    `unclassified` lines and `stray_frags` desc fragments that attached nowhere;
    both should be 0 — and `doc_routes`, the distinct routes the page banners
    claim for the document itself, CMP-AUD-049). Returns (None, None) if
    cancelled."""
    rows = []
    doc_routes = set()                  # the pages' own route claims (049)
    unclassified = stray_frags = 0
    bad_tokens = 0                      # unexpected PM code tokens (CMP-AUD-063)
    damaged_pages = 0                  # headerless pages carrying data (CMP-AUD-055)
    data_pages = 0
    stopped = False
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None
            if stopped:
                break
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            words = page.extract_words()
            hd = _page_header(words)
            if hd is None:
                # A cover/legend page has no data. CMP-AUD-055: but once the
                # document has entered its data section, a page that lost/damaged
                # its column-header anchors yet still carries data rows (a postmile
                # token) would be skipped WHOLESALE, silently dropping real data.
                # Flag it so the producer escalates to PARTIAL. Censused: ZERO real
                # headerless pages carry a postmile, so a genuine cover/legend/
                # trailer page never trips this.
                if data_pages and page_has_postmile(words):
                    damaged_pages += 1
                    events.on_log(f"    p{page_no}: data-shaped rows but no column "
                                  "header — page skipped (CMP-AUD-055).")
                continue
            data_pages += 1
            b = _boundaries(hd)
            hdr_bottom = max(w["bottom"] for w in hd.values())

            page_rows = []                  # [top, row-list] — mutable for frags
            frags = []                      # (top, text) desc-only lines
            for top, line_words in _cluster_lines(words):
                if top <= hdr_bottom + 2:
                    m = BANNER_ROUTE_RE.search(
                        " ".join(w["text"] for w in line_words))
                    if m:
                        doc_routes.add(m.group(1))
                    continue                # the banner / column-header band
                text = " ".join(w["text"] for w in line_words)
                if text.startswith(TRAILER_HEADING):
                    stopped = True          # site diagnostics; never report data
                    break
                vals = _classify_words(line_words, b)
                if PM_RE.fullmatch(vals["pm"]) or _is_pmless_data(vals):
                    for kind, tok in unexpected_pm_tokens(
                            vals["prefix"], vals["suffix"],
                            prefix_set=PREFIX_SET, suffix_set=SUFFIX_SET):
                        bad_tokens += 1
                        events.on_log(
                            f"    p{page_no}: unexpected postmile {kind} {tok!r} "
                            f"at {vals['pm']!r} (kept; vocab v{PM_VOCAB_VERSION})")
                    page_rows.append([top, [vals[k] for k in _COL_ORDER]])
                elif vals["desc"] and not any(
                        vals[k] for k in _COL_ORDER if k != "desc"):
                    frags.append((top, vals["desc"]))
                else:
                    unclassified += 1
                    events.on_log(f"    p{page_no}: unrecognized line skipped: "
                                  f"{text[:70]!r}")

            # Attach each desc fragment to its row (the nearest data line), then
            # assemble every row's Description in top order — a wrapped desc reads
            # back exactly as printed.
            desc_parts = {id(pr): [(pr[0], pr[1][8])] for pr in page_rows}
            for ftop, ftext in frags:
                best = min(page_rows, key=lambda pr: abs(pr[0] - ftop), default=None)
                if best is None or abs(best[0] - ftop) > FRAG_MAX_DIST:
                    stray_frags += 1
                    events.on_log(f"    p{page_no}: description fragment attached to "
                                  f"no row (skipped): {ftext[:60]!r}")
                    continue
                desc_parts[id(best)].append((ftop, ftext))
            for pr in page_rows:
                parts = [t for _, t in sorted(desc_parts[id(pr)])]
                pr[1][8] = join_desc_parts(parts)
            rows.extend(pr[1] for pr in page_rows)
    return rows, {"emitted": len(rows), "pages": n_pages, "data_pages": data_pages,
                  "unclassified": unclassified, "stray_frags": stray_frags,
                  "bad_tokens": bad_tokens, "damaged_pages": damaged_pages,
                  "doc_routes": sorted(doc_routes)}


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Highway Sequence workbook (the
    same sheet name + 9 columns — two unnamed — the Excel export uses). Empty
    strings become None so blank cells match the Excel export's."""
    write_route_workbook(rows, out_path, sheet_name=SHEET_NAME, header=HEADER,
                         row_values=lambda r: [v if v else None for v in r],
                         pdf_source_marker=True)


# =============================================================================
# Entry point
# =============================================================================

def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Convert every TSMIS Highway Sequence (PDF) export to a TSMIS-format
    per-route workbook, then combine them into one workbook (Route column added).

    `day` picks which export run folder of "Highway Sequence Listing (PDF)"
    exports to read; None means the newest run folder, falling back to the
    legacy flat layout. Console-free; honors events.is_cancelled() between
    pages. The convert-loop skeleton lives in pdf_table_lib.run_pdf_conversion;
    this module supplies the layout knowledge (route from the page banners'
    own "Route: NNN" claim, the filename token corroborating — CMP-AUD-049)
    and the ⚠-note / PARTIAL-escalation policy."""
    day = day or latest_output_day()
    in_dir = Path(input_dir) if input_dir else input_dir_for(day)
    out = Path(out_path) if out_path else out_path_for(day)
    conv = Path(converted_dir) if converted_dir else CONVERTED_DIR

    def convert_one(p, prefix, ev, ctx):
        name_m = ROUTE_FROM_NAME.search(p.stem)
        name_route = norm_route(name_m.group(1)) if name_m else None
        rows, pstats = parse_pdf(str(p), ev)
        if rows is None:                             # cancelled mid-PDF
            return ("cancelled",)
        if pstats:
            loud = pstats["unclassified"] + pstats["stray_frags"]
            if loud:
                ctx["loud"] = ctx.get("loud", 0) + loud
                ev.on_log(f"  WARNING: {loud} line(s)/fragment(s) in {p.name} "
                          "didn't parse cleanly — see the log.")
            bad = pstats["bad_tokens"]
            if bad:
                ctx["bad_tokens"] = ctx.get("bad_tokens", 0) + bad
                ev.on_log(f"  WARNING: {bad} unexpected postmile code token(s) in "
                          f"{p.name} — the source may be suspect (see the log).")
            dmg = pstats.get("damaged_pages", 0)
            if dmg:
                ctx["damaged_pages"] = ctx.get("damaged_pages", 0) + dmg
                ev.on_log(f"  WARNING: {dmg} page(s) in {p.name} carry data rows but "
                          "no column header — skipped (CMP-AUD-055); see the log.")
        if not rows:
            ev.on_log(f"{prefix} no highway data found; skipping")
            ctx["failed"].append(p.name)
            return ("skip",)
        route = reconcile_route_identity(
            p.name, name_route,
            [norm_route(t) for t in pstats["doc_routes"]], ev, ctx,
            claim_desc="the page banner's \"Route: NNN\"")
        if route is None:
            return ("skip",)
        return ("ok", route, rows)

    def finalize(result, ctx):
        loud = ctx.get("loud", 0)
        bad_tokens = ctx.get("bad_tokens", 0)
        damaged_pages = ctx.get("damaged_pages", 0)
        notes = []
        if loud:
            notes.append(f"⚠ {loud} unparsed line(s)/fragment(s) — verify (see the log).")
        if bad_tokens:
            notes.append(
                f"⚠ {bad_tokens} unexpected postmile code token(s) not in the "
                f"accepted vocabulary (v{PM_VOCAB_VERSION}) — the source may be "
                "suspect (see the log).")
        if damaged_pages:
            notes.append(f"⚠ {damaged_pages} page(s) carry data rows but no column "
                         "header (CMP-AUD-055) — verify (see the log).")
        result.summary_lines = notes + result.summary_lines
        # A dropped line or a failed PDF is invisible downstream, so ESCALATE to
        # a producer-owned partial — the incomplete output must not be promoted /
        # cached / compared as complete.
        if loud or ctx["failed"]:
            result.completion = outcome.PARTIAL
            result.failed_inputs = max(result.failed_inputs, len(ctx["failed"]))
        # `loud` (unparsed lines/fragments), an unexpected postmile code token
        # (CMP-AUD-063), and a damaged-header data page (CMP-AUD-055) are parse
        # ANOMALIES, not input-file counts, so they escalate COMPLETION only —
        # never skipped/failed_inputs, which stay the file-level channels
        # (CMP-AUD-064: a single PDF with three malformed lines is ONE affected
        # input, not three skips). The line/page counts ride a structured
        # diagnostic instead of the file fields.
        if bad_tokens or damaged_pages:
            result.completion = outcome.PARTIAL
        if loud or bad_tokens or damaged_pages:
            result.producer_extra = {
                **(result.producer_extra or {}),
                "parse_anomalies": {"unparsed_lines": loud, "bad_pm_tokens": bad_tokens,
                                    "damaged_header_pages": damaged_pages},
            }

    return run_pdf_conversion(
        in_dir=in_dir, out=out, conv=conv, deps_ok=_DEPS_OK,
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        report_name=REPORT_NAME,
        banner_title="TSMIS Highway Sequence (PDF) Conversion",
        export_hint=("Export the 'Highway Sequence Listing (PDF)' report first "
                     "(it saves the per-route PDFs there), then run this again."),
        unreadable_hint=("Are they the TSMIS Highway Sequence PDFs "
                         "(the 'Highway Sequence Listing (PDF)' export)?"),
        converted_prefix="tsmis_highway_sequence_pdf",
        convert_one=convert_one, write_one=_write_route_workbook,
        finalize=finalize,
        consolidate_kwargs=dict(
            sheet_name=SHEET_NAME, report_name=REPORT_NAME,
            title="TSMIS Highway Sequence (PDF) Consolidation"),
    )


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
