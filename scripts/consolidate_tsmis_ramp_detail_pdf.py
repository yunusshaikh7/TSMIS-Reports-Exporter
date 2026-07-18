"""Convert TSMIS Ramp Detail (PDF) exports into TSMIS-format Excel and combine.

The TSMIS "TSAR: Ramp Detail (PDF)" export (report 2b — the site's Print layout
saved via `page.pdf()`) renders the ramp listing as a landscape Letter print: a
parameters cover page, then data pages. Like the other PDF editions, the PDF and
the Excel export are two renders of the same data, so this consolidator parses
the per-route PDFs into the SAME column layout the Excel export produces — plus
the print's own two BONUS columns — so:
  * the combined workbook lines up column-for-column with the Excel-consolidated
    workbook and the normalized TSN library (for the TSMIS-PDF vs TSN comparison),
  * it can be diffed against the Excel export to pinpoint exactly which cells
    the two sources disagree on (the TSMIS-PDF vs TSMIS-Excel check),
  * and the two print-only columns the Excel export DROPS — the On/Off
    indicator and the Ramp Type letter — become comparable against TSN, which
    carries both in its database (the reason the print pairs RICHER than the
    Excel export; the Highway Log origin story again, in miniature).

The inputs ARE this app's own exports: the "TSAR: Ramp Detail (PDF)" export
saves the per-route PDFs (tsar_ramp_detail_route_<ROUTE>.pdf) to
output/<run>/ramp_detail_pdf/, so this consolidator reads that export folder
day-aware, exactly like the Excel consolidator.

PARSING — header-anchored column windows, censused statewide on the 126-route
7.9 export set against the SAME-DAY Excel exports (15,216 rows on both sides,
route-for-route and row-for-row; every residual difference class explained —
see docs/tsn-parsers.md):
  * Every data page repeats the stacked column header (LOCATION, the vertical
    P/R/E prefix letters, PM, DATE OF RECORD, HG, AREA 4, CITY CODE, R/U, the
    On/Off + Type letter pairs, DESCRIPTION); the page's x-windows derive from
    the anchor words on the header's BASE line plus its three single-letter
    columns (E between LOCATION and PM; U, F, Y between CITY CODE and
    DESCRIPTION), so the parse is stable to layout drift within a page style.
  * Descriptions NEVER wrapped in the statewide census (the column is wide
    enough for every real value), but the wrapped-row fragment machinery is
    kept from the Highway Sequence parser anyway — a future longer Description
    attaches to its data line instead of being dropped, and a fragment that
    attaches nowhere is LOUD, never guessed.
  * The print renders EMPTY fields visibly where the Excel export leaves
    blanks: a lone "-" in the Area 4 / On/Off columns and the Description
    message "NO RAMP LINEAR EVENT" (59 statewide rows — TSAR ramp points
    without linework, the count Ramp Summary prints per route). Values are
    written through VERBATIM here; the comparison flavors project the censused
    null-render tokens at compare time (documented in their Notes sheets).
  * The Excel export's header LABELS are column-shifted right of their values
    (blank/merged header cells after "Area 4"); this consolidator reproduces
    that EXACT header so the combined workbook stays column-compatible with
    the Excel-consolidated workbook (the comparator reads BY POSITION). The
    two print-only columns are appended AFTER the Excel layout with proper
    labels ("On/Off", "Ramp Type"), so every Excel-side reader — and the
    position-based comparison loader — is unaffected by their presence.

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
from pdf_table_lib import (norm_route, reconcile_route_identity,
                           run_pdf_conversion, unexpected_pm_tokens,
                           write_route_workbook)
from paths import (OUTPUT_ROOT, latest_output_day, output_day_dir,
                   stamped_consolidated_filename)

# These PDFs ARE produced by this app's "TSAR: Ramp Detail (PDF)" export
# (report 2b), saved to output/<run>/ramp_detail_pdf/. So this consolidator
# reads that EXPORT folder, day-aware, exactly like the Excel consolidator.
SUBDIR = "ramp_detail_pdf"
FILENAME = "tsmis_ramp_detail_pdf_consolidated.xlsx"

# Legacy flat-layout location (pre-dated exports, or a manual drop on a machine
# that can't run the export itself); used when no dated output/<run>/ folders exist.
INPUT_DIR = OUTPUT_ROOT / SUBDIR
CONVERTED_DIR = OUTPUT_ROOT / "tsmis_ramp_detail_pdf"        # scratch per-route wb
OUT_PATH = OUTPUT_ROOT / FILENAME                            # legacy flat output

# Friendly report name for user-facing messages (UI-neutral).
REPORT_NAME = "TSMIS Ramp Detail (PDF)"

# File pattern the GUI uses to preview how many inputs a folder holds.
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"

# Must match the Ramp Detail Excel export exactly for the first 11 columns —
# sheet name AND the export's own COLUMN-SHIFTED header (its labels sit right of
# the City Code / R/U / Description values behind two unnamed columns), so the
# converted files consolidate with the same core and the combined workbook is
# column-compatible with the Excel export and the position-based comparator.
# The two PRINT-ONLY columns (On/Off, Ramp Type — data the Excel export drops)
# are appended AFTER that layout with proper labels.
SHEET_NAME = "TSAR - Ramp Detail"
HEADER = ("Location", None, "PM", "Date of Record", None, "HG", "Area 4", None,
          "City Code", "R/U", "Description", "On/Off", "Ramp Type")


def input_dir_for(day):
    """The 'TSAR: Ramp Detail (PDF)' export PDFs for `day` (a run-folder name);
    None = the legacy flat layout."""
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
# A wrapped row's desc fragments would sit ~6pt from their data line while
# DISTINCT rows are >= 14.2pt apart (censused) — a fragment farther than this
# from every data line is unattributable (loud, never guessed).
FRAG_MAX_DIST = 13.0

PM_RE = re.compile(r"^\d{3}\.\d{3}$")
# The accepted, versioned post-mile PREFIX vocabulary (CMP-AUD-063), the
# legend's realignment codes (shared with Highway Sequence; the 7.9 census saw
# C,L,M,R,S,T of these). Ramp Detail has NO suffix column, so any prefix-window
# text outside this set alters the canonical postmile key: the parser counts it
# as a `bad_token` and the producer escalates to PARTIAL (never silently
# complete). Bump PM_VOCAB_VERSION when the site's legend adds a code (a
# deliberate, censused change). The 7.9 statewide census (126 RD PDFs) saw ONLY
# these tokens.
PM_VOCAB_VERSION = 1
PREFIX_SET = frozenset("CDGHLMNRST")
# The seven multi-letter column-header words every data page repeats. The three
# single-letter header columns (the prefix "E"; the On/Off "F" and Type "Y"
# bottoms, with "U" ending R/U) are found ON the same header line between these
# anchors — never by bare text, which data letters would collide with.
_HEADER_WORDS = ("LOCATION", "PM", "RECORD", "AREA", "CITY", "CODE", "DESCRIPTION")
# Route token out of "tsar_ramp_detail_route_<ROUTE>.pdf".
ROUTE_FROM_NAME = re.compile(r"route[_ -]*([0-9]+[A-Za-z]?)", re.IGNORECASE)
# The document's own route claim: every data page's banner line above the
# column header ("Route: 004 Direction: W – E" — censused on the 7.9 statewide
# set, suffixed routes print as one token, "005S"). CMP-AUD-049: this
# in-document claim, not the filename, is the authoritative identity.
BANNER_ROUTE_RE = re.compile(r"\bRoute:\s*([0-9]+[A-Za-z]?)\b")


def _page_header(words):
    """The page's column-header anchors -> (boundaries dict, header bottom), or
    (None, None) when this page has no data table (the parameters cover page).
    Anchored to ITS OWN header positions (stable to ±1pt across the statewide
    set, but derived per page anyway): the multi-letter words plus the three
    single-letter columns located BETWEEN known anchors on the header line."""
    hd = {}
    for w in words:
        if w["text"] in _HEADER_WORDS and w["text"] not in hd:
            hd[w["text"]] = w
    if len(hd) != len(_HEADER_WORDS):
        return None, None
    top = hd["DESCRIPTION"]["top"]
    line_letters = [w for w in words
                    if abs(w["top"] - top) <= LINE_TOL and len(w["text"]) == 1]
    prefix = [w for w in line_letters
              if hd["LOCATION"]["x1"] < w["x0"] < hd["PM"]["x0"]]
    tail = sorted((w for w in line_letters
                   if hd["CODE"]["x1"] < w["x0"] < hd["DESCRIPTION"]["x0"]),
                  key=lambda w: w["x0"])
    if len(prefix) != 1 or len(tail) != 3:
        return None, None                       # not the Ramp Detail header
    u, f, y = tail                              # R/U, On/Off, Type header bottoms
    b = {
        "loc_pr": prefix[0]["x0"] - 6,
        "pr_pm": hd["PM"]["x0"] - 12,
        "pm_date": hd["RECORD"]["x0"] - 8,
        "date_hg": hd["RECORD"]["x1"] + 12,
        "hg_area": hd["AREA"]["x0"] - 8,
        "area_city": hd["CITY"]["x0"] - 8,
        "city_ru": u["x0"] - 6,
        "ru_onoff": (u["x1"] + f["x0"]) / 2,
        "onoff_type": (f["x1"] + y["x0"]) / 2,
        "type_desc": hd["DESCRIPTION"]["x0"] - 8,
    }
    hdr_bottom = max(w["bottom"] for w in list(hd.values()) + line_letters)
    return b, hdr_bottom


_COL_ORDER = ("loc", "pr", "pm", "date", "hg", "area4", "city", "ru",
              "onoff", "rtype", "desc")


def _classify_words(line_words, b):
    """One text line's words -> {column: joined text} by word center."""
    cols = {k: [] for k in _COL_ORDER}
    for w in line_words:
        xc = (w["x0"] + w["x1"]) / 2
        if xc >= b["type_desc"]:
            cols["desc"].append(w["text"])
        elif xc >= b["onoff_type"]:
            cols["rtype"].append(w["text"])
        elif xc >= b["ru_onoff"]:
            cols["onoff"].append(w["text"])
        elif xc >= b["city_ru"]:
            cols["ru"].append(w["text"])
        elif xc >= b["area_city"]:
            cols["city"].append(w["text"])
        elif xc >= b["hg_area"]:
            cols["area4"].append(w["text"])
        elif xc >= b["date_hg"]:
            cols["hg"].append(w["text"])
        elif xc >= b["pm_date"]:
            cols["date"].append(w["text"])
        elif xc >= b["pr_pm"]:
            cols["pm"].append(w["text"])
        elif xc >= b["loc_pr"]:
            cols["pr"].append(w["text"])
        else:
            cols["loc"].append(w["text"])
    return {k: " ".join(v) for k, v in cols.items()}


def join_desc_parts(parts):
    """Join a wrapped Description's line texts top-to-bottom: bare after a
    hyphen (an HTML wrap splitting a hyphenated token), with one space
    otherwise. Mirrors the Highway Sequence consolidator's wrap-join rule;
    shared with the evidence adapter."""
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


# A parsed line -> the 13-column output row (see HEADER): the Excel export's 11
# positions (its two blank columns included) + the two print-only columns.
_ROW_KEYS = ("loc", "pr", "pm", "date", None, "hg", "area4", "city", "ru",
             "desc", None, "onoff", "rtype")
_DESC_I = _ROW_KEYS.index("desc")               # 9 — the Description position


def parse_pdf(path, events):
    """Parse one TSMIS Ramp Detail (PDF) export into 13-column TSMIS-format
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
    data_pages = 0
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            words = page.extract_words()
            b, hdr_bottom = _page_header(words)
            if b is None:
                continue                    # the parameters cover page
            data_pages += 1

            page_rows = []                  # [top, row-list] — mutable for frags
            frags = []                      # (top, text) desc-only lines
            for top, line_words in _cluster_lines(words):
                if top <= hdr_bottom + 2:
                    m = BANNER_ROUTE_RE.search(
                        " ".join(w["text"] for w in line_words))
                    if m:
                        doc_routes.add(m.group(1))
                    continue                # the route banner / header band
                vals = _classify_words(line_words, b)
                if PM_RE.fullmatch(vals["pm"]):
                    # Ramp Detail has no suffix column, so only the prefix window
                    # carries a PM code token (CMP-AUD-063).
                    for kind, tok in unexpected_pm_tokens(
                            vals["pr"], "", prefix_set=PREFIX_SET):
                        bad_tokens += 1
                        events.on_log(
                            f"    p{page_no}: unexpected postmile {kind} {tok!r} "
                            f"at {vals['pm']!r} (kept; vocab v{PM_VOCAB_VERSION})")
                    page_rows.append(
                        [top, ["" if k is None else vals[k] for k in _ROW_KEYS]])
                elif vals["desc"] and not any(
                        vals[k] for k in _COL_ORDER if k != "desc"):
                    frags.append((top, vals["desc"]))
                else:
                    unclassified += 1
                    text = " ".join(w["text"] for w in line_words)
                    events.on_log(f"    p{page_no}: unrecognized line skipped: "
                                  f"{text[:70]!r}")

            # Attach each desc fragment to its row (the nearest data line), then
            # assemble every row's Description in top order. The statewide census
            # found ZERO wrapped rows — this is the keep-it-loud safety net.
            desc_parts = {id(pr): [(pr[0], pr[1][_DESC_I])] for pr in page_rows}
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
                pr[1][_DESC_I] = join_desc_parts(parts)
            rows.extend(pr[1] for pr in page_rows)
    return rows, {"emitted": len(rows), "pages": n_pages, "data_pages": data_pages,
                  "unclassified": unclassified, "stray_frags": stray_frags,
                  "bad_tokens": bad_tokens, "doc_routes": sorted(doc_routes)}


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Ramp Detail workbook (the same
    sheet name + the Excel export's column-shifted 11-column layout, plus the
    two appended print-only columns). Empty strings become None so blank cells
    match the Excel export's."""
    write_route_workbook(rows, out_path, sheet_name=SHEET_NAME, header=HEADER,
                         row_values=lambda r: [v if v else None for v in r],
                         pdf_source_marker=True)


# =============================================================================
# Entry point
# =============================================================================

def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, converted_dir=None,
                commit_guard=None):
    """Convert every TSMIS Ramp Detail (PDF) export to a TSMIS-format per-route
    workbook, then combine them into one workbook (Route column added).

    `day` picks which export run folder of "TSAR: Ramp Detail (PDF)" exports to
    read; None means the newest run folder, falling back to the legacy flat
    layout. Console-free; honors events.is_cancelled() between pages. The
    convert-loop skeleton lives in pdf_table_lib.run_pdf_conversion; this module
    supplies the layout knowledge (route from the page banners' own
    "Route: NNN" claim, the filename token corroborating — CMP-AUD-049) and
    the ⚠-note / PARTIAL-escalation policy."""
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
        if not rows:
            ev.on_log(f"{prefix} no ramp data found; skipping")
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
        notes = []
        if loud:
            notes.append(f"⚠ {loud} unparsed line(s)/fragment(s) — verify (see the log).")
        if bad_tokens:
            notes.append(
                f"⚠ {bad_tokens} unexpected postmile code token(s) not in the "
                f"accepted vocabulary (v{PM_VOCAB_VERSION}) — the source may be "
                "suspect (see the log).")
        result.summary_lines = notes + result.summary_lines
        # A dropped line or a failed PDF is invisible downstream, so ESCALATE to
        # a producer-owned partial — the incomplete output must not be promoted /
        # cached / compared as complete.
        if loud or ctx["failed"]:
            result.completion = outcome.PARTIAL
            result.skipped_inputs = max(result.skipped_inputs, loud)
            result.failed_inputs = max(result.failed_inputs, len(ctx["failed"]))
        # An unexpected postmile code token (CMP-AUD-063) is a parse ANOMALY, not
        # an input-file count, so it escalates COMPLETION only — never
        # skipped/failed_inputs (those stay the file-level channels).
        if bad_tokens:
            result.completion = outcome.PARTIAL

    return run_pdf_conversion(
        in_dir=in_dir, out=out, conv=conv, deps_ok=_DEPS_OK,
        events=events, confirm_overwrite=confirm_overwrite,
        commit_guard=commit_guard,
        report_name=REPORT_NAME,
        banner_title="TSMIS Ramp Detail (PDF) Conversion",
        export_hint=("Export the 'TSAR: Ramp Detail (PDF)' report first "
                     "(it saves the per-route PDFs there), then run this again."),
        unreadable_hint=("Are they the TSMIS Ramp Detail PDFs "
                         "(the 'TSAR: Ramp Detail (PDF)' export)?"),
        converted_prefix="tsmis_ramp_detail_pdf",
        convert_one=convert_one, write_one=_write_route_workbook,
        finalize=finalize,
        consolidate_kwargs=dict(
            sheet_name=SHEET_NAME, report_name=REPORT_NAME,
            title="TSMIS Ramp Detail (PDF) Consolidation"),
    )


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
