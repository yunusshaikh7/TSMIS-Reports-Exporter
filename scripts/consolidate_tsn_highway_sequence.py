"""Convert the TSN district Highway Sequence (HSL) PDFs into one normalized
Excel the Highway Sequence comparison reads.

The TSN "Highway Locations" report (OTM22025) is a fixed-layout PDF, one per
district (D01..D12), listing every route's postmile sequence: a per-page header
band, a centered "DIST NN RTE NNN DIR X-X" group header, then one data line per
location:

    CO.  CITY  POSTMILE  G/RF  DISTANCE-TO-NXT-POINT  DESCRIPTION
    MEN        000.000    UH   000.056               BEGIN OF COUNTY
    ORA  DAPT  R000.129   DH   000.102               JCT 5 CAMINO L RMBLS UC

Reconciled by hand against the per-route TSMIS "Highway Locations" XLSX
(docs/tsn-parsers.md):
  * CALIFORNIA postmiles are COUNTY-RELATIVE — the same route restarts at
    000.000 in each county it crosses — so the comparison keys on
    route + county + postmile, not route + postmile.
  * The POSTMILE token carries a glued realignment prefix ("R000.129") and/or
    an equate suffix ("050.025E"); TSMIS stores those in separate (unnamed)
    prefix/suffix columns. We keep the glued TSN form as the canonical postmile
    and the TSMIS loader re-glues prefix+PM+suffix to match.
  * The 2-letter "G/RF" flag is HG (1st char) + FT (2nd char) — TSMIS splits
    them into its HG and FT columns.
  * TSN lists every segment break (incl. unnamed ones) and prints equate points
    as a "Rxxx EQUATES TO" annotation; TSMIS omits most unnamed breaks and
    stores the equate as an "END R REALIGNMENT" row. Both differences surface
    honestly as one-sided rows in the comparison (as they already do for the
    Highway Log — "mostly TSN segment splits and TSMIS realignment markers").

Unlike word-fusion-prone Highway Log, HSL columns are widely spaced, so
word-level extraction (with the 2-char flag split) is safe; only the postmile
token must be classed by its x-window. Columns are calibrated to the OTM22025
layout and verified stable across all 12 districts.

Console-free like the other consolidators: progress via events.on_log, overwrite
through the confirm_overwrite callback, cancel honored between pages, a
ConsolidateResult returned. The console UX lives in cli.run_consolidate_cli.
"""
import logging
import re
from pathlib import Path

logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import pdfplumber
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

from compare_core import is_formula_injection
from events import ConsolidateResult, Events
import outcome
import artifact_store
from paths import INPUT_ROOT, OUTPUT_ROOT

# Standalone / console (.bat) default locations — see the matching note in
# consolidate_tsn_highway_log.py. The GUI/matrices build through the canonical
# git-ignored tsn_library/ tree (tsn_library.build_into); this OUT_PATH holds
# Caltrans-internal TSN data and is git-ignored (output/* + the explicit
# output/tsn_* rule in .gitignore) — never add an "!output/tsn_*" allowlist entry.
INPUT_DIR = INPUT_ROOT / "tsn_highway_sequence"
OUT_PATH = OUTPUT_ROOT / "tsn_highway_sequence_consolidated.xlsx"

REPORT_NAME = "TSN Highway Sequence"
INPUT_GLOB = "*.pdf"
INPUT_FMT = "PDF"
INPUT_NOTE = "Drop the TSN district Highway Sequence (HSL) PDFs into the input folder first."

# The normalized workbook the comparison reads: a leading Route column + the
# shared comparison fields, in this exact order (compare_highway_sequence_tsn
# reads it positionally). Postmile is the glued canonical form (prefix+PM+suffix).
NORMALIZED_SHEET = "Highway Locations (TSN)"
NORMALIZED_HEADER = ["Route", "County", "PM", "City", "HG", "FT",
                     "Distance To Next Point", "Description"]


# =============================================================================
# PDF layout — calibrated to OTM22025 "Highway Locations" (verified D01..D12)
# =============================================================================

Y_TOLERANCE = 3      # words within this y-distance form one logical line

# A word belongs to the column whose x-window contains its left edge (x0). The
# columns are widely separated (no fusion risk), so x0 classification is stable.
# The 2-char G/RF flag is one fused token ("UH") split into HG + FT below.
W_COUNTY = (0, 44)
W_CITY = (44, 98)
W_PM = (98, 168)
W_FLAG = (168, 205)
W_DIST = (205, 270)
W_DESC = (270, 700)

# A postmile, optionally with a glued realignment prefix ("R012.887") and/or an
# equate suffix ("050.025E"), exactly as printed in the POSTMILE column.
LOCATION_RE = re.compile(r"^[A-Z]?\d{3}\.\d{3}[A-Z]?$")
# A county code in the CO. column ("MEN", "LA.", "SB.").
COUNTY_RE = re.compile(r"^[A-Z]{2,4}\.?$")
# A distance-to-next value ("000.056"); TSN prints 3-int-digit zero-padded.
DIST_RE = re.compile(r"^\d{1,3}\.\d{3}$")
# Centered group header: "DIST 01 RTE 001 DIR S-N" (route may be suffixed: 005S).
GROUP_RE = re.compile(r"\bDIST\s+(\d+)\s+RTE\s+(\w+)\s+DIR\b")
DISTRICT_FROM_NAME = re.compile(r"D(\d{1,2})", re.IGNORECASE)


def _bucket(x0):
    for name, (lo, hi) in (("county", W_COUNTY), ("city", W_CITY), ("pm", W_PM),
                           ("flag", W_FLAG), ("dist", W_DIST), ("desc", W_DESC)):
        if lo <= x0 < hi:
            return name
    return None


def _cluster_lines(words):
    """Group words into logical lines, tolerating the ~1pt baseline jitter of the
    proportional font (a plain round(top) splits a single row across two buckets
    when its words straddle x.5, dropping rows that then lack a county or PM)."""
    clusters = []                     # [(anchor_top, [word, ...]), ...]
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if clusters and abs(w["top"] - clusters[-1][0]) <= Y_TOLERANCE:
            clusters[-1][1].append(w)
        else:
            clusters.append((w["top"], [w]))
    return [sorted(ws, key=lambda w: w["x0"]) for _, ws in clusters]


def _norm_route(token):
    """'1' -> '001' (TSMIS zero-pads); suffixed routes ('5S') kept as '005S'."""
    m = re.fullmatch(r"(\d+)([A-Z]?)", token.upper())
    return f"{int(m.group(1)):03d}{m.group(2)}" if m else token.upper()


def _parse_line(ws):
    """Classify one clustered line's words into column buckets -> {bucket: [text]}."""
    cols = {}
    for w in ws:
        b = _bucket(w["x0"])
        if b is not None:
            cols.setdefault(b, []).append(w["text"])
    return cols


def parse_pdf(path, events, pdf_name=""):
    """Parse one TSN district HSL PDF -> {route: [row_dict, ...]} in document
    order. Each row_dict has county/pm/city/hg/ft/dist/description. Raises on
    cancel (returns (None,) sentinel handled by caller via None result)."""
    routes = {}
    route = None
    county = None              # carried onto equate-annotation rows (no county token)
    last_row = None            # a wrapped description line attaches here

    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            for line in _cluster_lines(words):
                text = " ".join(w["text"] for w in line)

                gm = GROUP_RE.search(text)
                if gm:
                    route = _norm_route(gm.group(2))
                    routes.setdefault(route, [])
                    county = None
                    last_row = None
                    continue

                cols = _parse_line(line)
                co = (cols.get("county") or [""])[0]
                pm = next((t for t in (cols.get("pm") or []) if LOCATION_RE.match(t)), None)

                # Equate annotation: "Rxxx.xxx EQUATES TO" — a postmile at the PM
                # window, NO county token. TSMIS records the same equate as an
                # "END R REALIGNMENT" row at that postmile, so emit it (county
                # carried from context) to pair the two rather than orphan it.
                if "EQUATES" in text and pm and not COUNTY_RE.match(co):
                    if route is not None and county is not None:
                        row = dict(county=county, pm=pm, city=None, hg=None,
                                   ft=None, dist=None, description="EQUATES TO")
                        routes[route].append(row)
                        last_row = row
                    continue

                # Data line: a county code AND a postmile in their windows.
                if COUNTY_RE.match(co) and pm:
                    if route is None:
                        events.on_log(f"    {pdf_name} p{page_no}: data before any "
                                      "route header; line skipped")
                        continue
                    county = co.rstrip(".")
                    flag = "".join(cols.get("flag") or [])
                    desc = " ".join(cols.get("desc") or []).strip() or None
                    dist = next((t for t in (cols.get("dist") or [])
                                 if DIST_RE.match(t)), None)
                    row = dict(
                        county=county, pm=pm,
                        city=(cols.get("city") or [None])[0],
                        hg=(flag[0] if len(flag) >= 1 else None),
                        ft=(flag[1] if len(flag) >= 2 else None),
                        dist=dist, description=desc)
                    routes[route].append(row)
                    last_row = row
                    continue

                # A wrapped description continuation: text only in the description
                # window, no county/postmile -> append to the open row.
                if (last_row is not None and cols.get("desc")
                        and not cols.get("county") and not cols.get("pm")):
                    extra = " ".join(cols["desc"]).strip()
                    if extra:
                        last_row["description"] = (
                            extra if not last_row["description"]
                            else last_row["description"] + ", " + extra)

    return routes


# =============================================================================
# Normalized workbook
# =============================================================================

def _row_values(route, d):
    """One normalized row in NORMALIZED_HEADER order."""
    return [route, d["county"], d["pm"], d["city"], d["hg"], d["ft"],
            d["dist"], d["description"]]


def _write_workbook(all_rows, out_path, proceed=None):
    """Write every (route, row_dict) into one normalized workbook (write_only so
    the statewide ~46k rows never exhaust memory)."""
    header_fill = PatternFill("solid", start_color="305496")
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(NORMALIZED_SHEET)
    ws.freeze_panes = "B2"
    ws.column_dimensions["A"].width = 9
    for i, name in enumerate(NORMALIZED_HEADER[1:], start=2):
        ws.column_dimensions[get_column_letter(i)].width = \
            40 if name == "Description" else 14

    head = []
    for name in NORMALIZED_HEADER:
        c = WriteOnlyCell(ws, value=name)
        c.font = header_font
        c.fill = header_fill
        c.alignment = header_align
        head.append(c)
    ws.append(head)

    for route, d in all_rows:
        cells = []
        for v in _row_values(route, d):
            if is_formula_injection(v):       # neutralize a "="-leading description
                c = WriteOnlyCell(ws, value=v)
                c.data_type = "s"
                cells.append(c)
            else:
                cells.append(v)
        ws.append(cells)
    # F9 temp + os.replace + the P12 TOCTOU gate at the replace.
    return artifact_store.atomic_save_if(wb, out_path, proceed or (lambda: True))


# =============================================================================
# Entry points
# =============================================================================

def build_into(raw_dir, out_path, events=None, confirm_overwrite=None):
    """Canonical-TSN-library entry point: parse the district PDFs in `raw_dir`,
    write the one normalized workbook to `out_path`. Thin wrapper over
    consolidate() so tsn_library drives every report through one signature."""
    return consolidate(events=events, confirm_overwrite=confirm_overwrite,
                       input_dir=raw_dir, out_path=out_path)


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None):
    """Parse every TSN district HSL PDF in `input_dir` into one normalized
    workbook at `out_path`. `day` is accepted for interface symmetry and ignored
    (TSN PDFs are vendor snapshots, not dated exports). Console-free."""
    in_dir = Path(input_dir) if input_dir else INPUT_DIR
    out = Path(out_path) if out_path else OUT_PATH
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(
            status="error",
            message="Required components are missing (pdfplumber, openpyxl).")
    confirm = confirm_overwrite or (lambda _p: True)

    try:
        in_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    pdfs = sorted(in_dir.glob("*.pdf"))
    if not pdfs:
        return ConsolidateResult(
            status="error",
            message=(f"No {REPORT_NAME} files were found in:\n{in_dir}\n\n"
                     f"Put the district Highway Sequence PDFs (e.g. "
                     f"D01 HSL TSN.pdf) there, then run again."))

    existed_at_confirm = out.exists()
    if existed_at_confirm and not confirm(out):
        return ConsolidateResult(status="cancelled",
                                 message="Cancelled. Existing file kept.")

    events.on_log("=" * 60)
    events.on_log(f"TSN Highway Sequence Conversion - {len(pdfs)} district PDF(s)")
    events.on_log("=" * 60)
    events.on_log("")

    # route -> [row_dict]; same route may appear across districts (different
    # counties) — accumulate so all of a route's counties land in one workbook.
    by_route = {}
    failed = []
    for i, p in enumerate(pdfs, 1):
        if events.is_cancelled():
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        prefix = f"[{i}/{len(pdfs)}] {p.name}"
        events.on_log(f"{prefix} parsing…")
        try:
            route_rows = parse_pdf(str(p), events, pdf_name=p.name)
        except Exception as e:
            events.on_log(f"{prefix} FAILED ({type(e).__name__}): {e}")
            failed.append(p.name)
            continue
        if route_rows is None:
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        if not route_rows:
            events.on_log(f"{prefix} no highway-sequence data found; skipping")
            failed.append(p.name)
            continue
        n = 0
        for route, rows in route_rows.items():
            by_route.setdefault(route, []).extend(rows)
            n += len(rows)
        events.on_log(f"{prefix} +{n} rows across {len(route_rows)} route(s)")

    if not by_route:
        return ConsolidateResult(
            status="error",
            message=(f"None of the PDFs in:\n{in_dir}\n\ncontained readable "
                     f"{REPORT_NAME} data. Are they the TSN Highway Locations PDFs?"))

    all_rows = [(route, d) for route in sorted(by_route)
                for d in by_route[route]]

    out.parent.mkdir(parents=True, exist_ok=True)
    events.on_log("")
    events.on_log("Writing normalized workbook...")
    try:
        # P12 TOCTOU: the overwrite gate is INSIDE _write_workbook, at the os.replace
        # (atomic_save_if) — a destination that appears during the BUILD is caught.
        committed = _write_workbook(all_rows, out, proceed=lambda: artifact_store.confirm_late_overwrite(
            out, existed_at_confirm, confirm))
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))
    if not committed:
        return ConsolidateResult(status="cancelled",
                                 message="Cancelled. Existing file kept.")

    summary_lines = []
    if failed:
        summary_lines.append(
            f"⚠ INCOMPLETE — {len(failed)} district PDF(s) failed {failed}; "
            f"their routes are NOT in the workbook. See the log above.")
    summary_lines += [
        f"District PDFs:  {len(pdfs) - len(failed)} parsed"
        + (f", {len(failed)} failed" if failed else ""),
        f"Routes:         {len(by_route)}",
        f"Rows:           {len(all_rows)}",
        f"Output file:    {out}",
    ]
    # P1-B05: producer-owned completion — district PDFs that failed to parse are
    # left-out inputs whose routes are NOT in the workbook, so it is PARTIAL (compared,
    # but flagged), carried structurally (failed_inputs) rather than only in the warning.
    return ConsolidateResult(status="ok", output_path=str(out),
                             summary_lines=summary_lines,
                             completion=outcome.PARTIAL if failed else outcome.COMPLETE,
                             failed_inputs=len(failed))


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
