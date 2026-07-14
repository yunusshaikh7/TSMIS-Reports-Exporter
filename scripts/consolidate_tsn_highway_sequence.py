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
import io
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
from pdf_table_lib import cluster_by_top, norm_route
import outcome
import artifact_store
import tsn_district_contract as tdc
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
GROUP_LIKE_RE = re.compile(r"\bDIST\b.*\bRTE\b.*\bDIR\b", re.IGNORECASE)


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
    return [ws for _top, ws in cluster_by_top(words, Y_TOLERANCE)]


# The canonical route-token normalizer (pdf_table_lib; behavior unchanged —
# this module's copy was already the reconciled regex form).
_norm_route = norm_route


def _parse_line(ws):
    """Classify one clustered line's words into column buckets -> {bucket: [text]}."""
    cols = {}
    for w in ws:
        b = _bucket(w["x0"])
        if b is not None:
            cols.setdefault(b, []).append(w["text"])
    return cols


def parse_pdf(path, events, pdf_name=""):
    """Parse one HSL PDF -> ``(internal district, routes)`` in document order."""
    routes = {}
    district_claims = []
    route = None
    county = None              # carried onto equate-annotation rows (no county token)
    last_row = None            # a wrapped description line attaches here

    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            for line in _cluster_lines(words):
                text = " ".join(w["text"] for w in line)

                gm = GROUP_RE.search(text)
                if gm:
                    district_claims.append(gm.group(1))
                    route = _norm_route(gm.group(2))
                    routes.setdefault(route, [])
                    county = None
                    last_row = None
                    continue
                if GROUP_LIKE_RE.search(text):
                    raise ValueError(
                        f"{pdf_name} p{page_no}: malformed DIST/RTE/DIR group header "
                        f"cannot safely own following rows: {text!r}")

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
                        raise ValueError(
                            f"{pdf_name} p{page_no}: recognizable highway-sequence "
                            "data appeared before any owning route header")
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

    district = tdc.document_district(district_claims, pdf_name or Path(path).name)
    return district, routes


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

    pdfs = sorted(p for p in in_dir.glob("*.pdf") if p.is_file())
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

    try:
        source_manifest, source_bytes = tdc.capture_raw_manifest(pdfs, in_dir)
    except ValueError as e:
        return ConsolidateResult(
            status="error",
            message=f"The TSN Highway Sequence raw source could not be bound: {e}",
        )

    source_problem = [None]

    def source_current():
        try:
            current_pdfs = sorted(p for p in in_dir.glob("*.pdf") if p.is_file())
            current = tdc.canonical_raw_manifest(current_pdfs, in_dir)
        except (OSError, ValueError) as e:
            source_problem[0] = f"{type(e).__name__}: {e}"
            return False
        if current != source_manifest:
            source_problem[0] = "the raw member names or bytes changed during conversion"
            return False
        return True

    def source_changed():
        detail = source_problem[0] or "the raw source changed during conversion"
        return ConsolidateResult(
            status="error",
            message=(f"The TSN Highway Sequence raw source changed while it was being "
                     f"normalized ({detail}); last-good output was preserved."),
        )

    # route -> [row_dict]; same route may appear across districts (different
    # counties) — accumulate so all of a route's counties land in one workbook.
    by_route = {}
    failed = []
    claimed_districts = {}
    for i, p in enumerate(pdfs, 1):
        if events.is_cancelled():
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        prefix = f"[{i}/{len(pdfs)}] {p.name}"
        events.on_log(f"{prefix} parsing…")
        try:
            district, route_rows = parse_pdf(
                io.BytesIO(source_bytes[p.name]), events, pdf_name=p.name)
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
        if district in claimed_districts:
            return ConsolidateResult(
                status="error", failed_inputs=1,
                message=(f"Duplicate internal district claim D{district}: "
                         f"{claimed_districts[district]} and {p.name}. "
                         "Nothing was published."),
            )
        claimed_districts[district] = p.name
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

    if failed:
        return ConsolidateResult(
            status="error", failed_inputs=len(failed),
            message=(f"The TSN Highway Sequence source is incomplete or unreadable: "
                     f"{len(failed)} document(s) failed {failed}. Exactly one "
                     "internally claimed document for every D01-D12 is required; "
                     "nothing was published."),
        )
    try:
        tdc.require_exact_universe(
            (district, claimed_districts[district])
            for district in claimed_districts)
    except ValueError as e:
        return ConsolidateResult(status="error", message=str(e))
    if events.is_cancelled():
        return ConsolidateResult(status="cancelled", message="Cancelled by user.")
    if not source_current():
        return source_changed()

    all_rows = [(route, d) for route in sorted(by_route)
                for d in by_route[route]]

    out.parent.mkdir(parents=True, exist_ok=True)
    events.on_log("")
    events.on_log("Writing normalized workbook...")
    final_gate = [None]

    def may_publish():
        if events.is_cancelled():
            final_gate[0] = "cancelled"
            return False
        if not source_current():
            final_gate[0] = "source"
            return False
        if not artifact_store.confirm_late_overwrite(out, existed_at_confirm, confirm):
            final_gate[0] = "overwrite"
            return False
        return True

    try:
        # P12 TOCTOU: the overwrite gate is INSIDE _write_workbook, at the os.replace
        # (atomic_save_if) — a destination that appears during the BUILD is caught.
        committed = _write_workbook(all_rows, out, proceed=may_publish)
    except PermissionError:
        return ConsolidateResult(
            status="error",
            message=(f"Could not save {out.name}.\n\n"
                     "The file is probably open in Excel. Close it and try again."))
    if not committed:
        if final_gate[0] == "source":
            return source_changed()
        if final_gate[0] == "cancelled":
            return ConsolidateResult(status="cancelled", message="Cancelled by user.")
        return ConsolidateResult(status="cancelled",
                                 message="Cancelled. Existing file kept.")

    summary_lines = []
    summary_lines += [
        f"District PDFs:  {len(pdfs)} parsed; exact D01-D12",
        f"Routes:         {len(by_route)}",
        f"Rows:           {len(all_rows)}",
        f"Output file:    {out}",
    ]
    result = ConsolidateResult(status="ok", output_path=str(out),
                               summary_lines=summary_lines,
                               completion=outcome.COMPLETE, failed_inputs=0)
    result.tsn_raw_manifest = source_manifest
    return result


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
