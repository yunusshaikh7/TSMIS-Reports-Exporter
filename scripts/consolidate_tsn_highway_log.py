"""Convert TSN district Highway Log PDFs into TSMIS-format Excel and combine.

Ported from the TSMIS-Report-Consolidator sibling project (the PDF parsing
core is verbatim — it is calibrated against real district PDFs); only the
consolidate() interface is adapted to this app's registry contract.

Reads every district PDF in  input/tsn_highway_log/   (e.g. D01_Highway_Log_TSN.pdf)
Writes per-route workbooks in output/tsn_highway_log/  (tsn_highway_log_d01_route_001.xlsx)
and one combined workbook   output/tsn_highway_log_consolidated.xlsx

Unlike the TSMIS consolidators, the inputs are NOT this app's dated exports:
TSN PDFs are vendor snapshots the user drops into the input folder, so the
"Export day" concept doesn't apply (the `day` parameter is accepted for
interface compatibility and ignored). The per-route conversions this run
writes are exactly what the Highway Log comparison takes as its TSN file.

The TSN (Transportation System Network) "California State Highway Log"
(report OTM52010) is a fixed-layout PDF listing: a 3-line column-header band
per page, a centered "<district> <county> <route>" group header, one data line
per highway segment (sometimes wrapping onto a second baseline), description
lines *below* the segment they belong to, and "* * Volume Location Totals"
summary lines.

Each per-route output uses the SAME sheet name ("Highway Log") and the SAME 31
columns as the per-route TSMIS Highway Log export, so:
  * the shared XLSX consolidator combines them unchanged (Route prepended from
    the filename), and
  * the combined workbook lines up column-for-column with the consolidated
    TSMIS Highway Log for comparison.
TSN-only data that has no TSMIS column (the ADT traffic figures) is dropped;
TSN description lines are joined into the TSMIS "Description" column.

Parsing is x-position based (the PDF is proportional Helvetica, not
monospaced): every data CHARACTER is assigned to a column by the horizontal
window its center falls in -- word-level parsing is not safe here, because
adjacent columns can print closer together than word-segmentation tolerances
(a filled City code starts ~2pt after the county odometer, fusing into one
token like '042.010LKPT'). The windows are calibrated to the OTM52010 layout
and verified stable across every data row of the sample districts.

Console-free like the other consolidators: progress via events.on_log,
overwrite confirmed through the callback, cancel honored between pages, and a
ConsolidateResult returned. The console UX lives in cli.run_consolidate_cli.
"""
import hashlib
import io
import json
import logging
import re
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

# pdfplumber wraps pdfminer.six, which can log noisy per-page font warnings;
# parsing is unaffected (see consolidate_ramp_summary).
logging.getLogger("pdfminer").setLevel(logging.ERROR)

try:
    import pdfplumber
    import openpyxl  # noqa: F401 — the gate covers both the PDF and XLSX deps
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import highway_log_columns as hlc               # the corrected column labels
import consolidation_meta
from consolidate_xlsx_base import consolidate_xlsx
import owned_dir
from pdf_table_lib import char_lines, norm_route, write_route_workbook
import tsn_district_contract as tdc
from events import ConsolidateResult, Events
from paths import INPUT_ROOT, OUTPUT_ROOT

# Standalone / console (.bat) default locations. The GUI + matrices build through
# the canonical TSN library instead — tsn_library.build_into() passes its own
# raw/consolidated paths under the git-ignored tsn_library/<report>/ tree, and
# tsn_library._legacy_{raw_dir,consolidated}() keep these legacy paths readable as
# a back-compat fallback. These output paths hold Caltrans-internal TSN data; they
# are git-ignored (output/* + an explicit output/tsn_* belt-and-suspenders rule in
# .gitignore) — never add an "!output/tsn_*" allowlist entry.
INPUT_DIR = INPUT_ROOT / "tsn_highway_log"
CONVERTED_DIR = OUTPUT_ROOT / "tsn_highway_log"   # per-route TSMIS-format workbooks
OUT_PATH = OUTPUT_ROOT / "tsn_highway_log_consolidated.xlsx"

# Shown in the GUI's Consolidate pane so users know where the PDFs go (this is
# the one report whose input is NOT produced by this app's exports).
INPUT_NOTE = "Drop the TSN district Highway Log PDFs into the input folder first."


def input_dir_for(day):                  # noqa: ARG001 (interface compatibility)
    """TSN PDFs live in one fixed folder; vendor snapshots aren't dated exports."""
    return INPUT_DIR


def out_path_for(day):                   # noqa: ARG001 (interface compatibility)
    """Combined workbook destination (the 'Export day' picker doesn't apply)."""
    return OUT_PATH

# Same sheet name AND header as the TSMIS Highway Log so the converted files
# consolidate with the same core and line up column-for-column with the TSMIS
# Highway Log. The CORRECTED 31-column header lives in one place (the vendor
# Excel mislabeled these; see highway_log_columns).
SHEET_NAME = "Highway Log"
TSMIS_HEADER = hlc.HEADER

# Friendly report name for user-facing messages (shown in both the GUI and the
# console, so keep it UI-neutral -- no ".bat" / "menu option" wording).
REPORT_NAME = "TSN Highway Log"

# File pattern the GUI uses to preview how many inputs a folder holds.
INPUT_GLOB = "*.pdf"

# Input file format, shown as the Consolidate-tab badge (these are district PDFs).
INPUT_FMT = "PDF"


# =============================================================================
# PDF layout -- calibrated to the OTM52010 "California State Highway Log"
# =============================================================================

Y_TOLERANCE = 3      # chars within this y-distance form one logical line
HEADER_BAND = 56     # everything above this y on a page is page furniture
WORD_GAP = 1.5       # x-gap that starts a new token; intra-value gaps are ~0pt

# A real segment description prints LEFT-ALIGNED in the feature-name column at
# x0 ~= 73.4 in the fixed OTM52010 layout. Measured across all 12 districts,
# 99.8% of description lines sit at x0 73-75 and NOTHING legitimate prints
# elsewhere in this band: the only other below-band, non-data, non-totals lines
# are page furniture that occasionally dips past HEADER_BAND ("CALIFORNIA
# DEPARTMENT OF TRANSPORTATION" x0~37, "California State Highway Log" x0~201,
# "District NN" x0~256) and wrapped totals fragments ("TOTAL" / "TOTAL CONST"
# x0~170). Gating descriptions to this band excludes ALL of them structurally,
# independent of the totals-text pattern list — so a stray fragment or a header
# that slips the band can never corrupt a Description.
DESC_X0_MIN, DESC_X0_MAX = 60, 110

# (column_key, x_min, x_max): a data word belongs to the column whose window
# contains the word's horizontal CENTER. Order = TSMIS column order; the three
# ADT columns exist in the TSN layout but have no TSMIS counterpart and are
# dropped when rows are written. "Description" has no window -- TSN prints
# descriptions as separate lines below the data row.
COLUMN_WINDOWS = [
    ("location",  0, 50),     # may carry a realignment prefix: "R012.887"
    ("mi",       50, 73),
    ("na",       73, 82),
    ("cnty_odom", 82, 112),
    ("city",    112, 132),
    ("ru",      132, 147),
    ("spd",     147, 160),
    ("ter",     160, 171),
    ("hg",      171, 184),
    ("ac",      184, 197),
    ("lb_t",    197, 208),
    ("lb_lns",  208, 219),
    ("lb_f",    219, 230),
    ("lb_ot",   230, 241),
    ("lb_tr",   241, 253),
    ("lb_tw",   253, 268),
    ("lb_in",   268, 279),
    ("lb_sh",   279, 291),
    ("med_tcb", 291, 308),
    ("med_wid", 308, 326),
    ("rb_t",    326, 338),
    ("rb_lns",  338, 350),
    ("rb_f",    350, 361),
    ("rb_in",   361, 372),
    ("rb_sh",   372, 386),
    ("rb_tw",   386, 398),
    ("rb_ot",   398, 410),
    ("rb_sh2",  410, 424),
    ("adt_back",  424, 448),  # TSN-only (ADT Look Back)   -> dropped
    ("adt_pp",    448, 459),  # TSN-only (ADT P/P flag)    -> dropped
    ("adt_ahead", 459, 486),  # TSN-only (ADT Look Ahead)  -> dropped
    ("rec",     486, 519),
    ("sig",     519, 612),
]

# Row keys in TSMIS column order (Description filled from follow-on lines).
ROW_KEYS = ["location", "mi", "na", "cnty_odom", "city", "ru", "spd", "ter",
            "hg", "ac", "lb_t", "lb_lns", "lb_f", "lb_ot", "lb_tr", "lb_tw",
            "lb_in", "lb_sh", "med_tcb", "med_wid", "rb_t", "rb_lns", "rb_f",
            "rb_in", "rb_sh", "rb_tw", "rb_ot", "rb_sh2",
            "description", "rec", "sig"]

# A segment postmile, optionally with a glued realignment prefix ("R012.887")
# and/or a trailing equation suffix ("026.437E"), as printed in the Location
# column (TSMIS prints the same prefixed form).
LOCATION_RE = re.compile(r"^[A-Z]?\d{3}\.\d{3}[A-Z]?$")
# Centered "<district> <county> <route>[ <suffix>]" group header, e.g.
# "01 MEN 001" or "07 LA 005 S". The optional FOURTH token is the route
# SUFFIX printed as its own glyph token (CMP-AUD-157's "owner qualifier"):
# the 2026-07-17 full-corpus census found exactly 19 four-token headers, and
# their (route, letter) combinations are exactly TSMIS's ten suffixed routes
# (005S 008U 010S 014U 015S 058U 101U 178S 210U 880S) — row-verified against
# the TSMIS per-route exports (route 101U's 8 rows are postmile-for-postmile
# a subset of the "01 MEN 101 U" section, and the print's own COUNTY/ROUTE
# totals for suffixed sections are all-zero, excluding them from the base
# route). The suffix therefore joins the route identity; a fourth token that
# is not a single letter refuses (unknown grammar cannot own rows).
GROUP_RE = (re.compile(r"^\d{2}$"), re.compile(r"^[A-Z]{2,4}$"),
            re.compile(r"^\d{1,3}[A-Z]?$"))
GROUP_SUFFIX_RE = re.compile(r"^[A-Z]$")
DISTRICT_LINE_RE = re.compile(r"^District\s+0?(\d{1,2})$", re.IGNORECASE)

# The normalized-output version (CMP-AUD-157/045-HL). v5: detached route
# suffixes join the route; asterisk-leading printed Descriptions are
# conserved; district/county/route ownership, the three printed ADT claims,
# totals blocks, and report provenance ride the source-claims sidecar with
# typed dispositions; totals reconcile against the parsed row universes.
# report_catalog's highway_log normalization_version mirrors this (D2
# auto-rebuild); the marker sheet gates manually-picked stale files.
NORMALIZATION_VERSION = 5
MARKER_SHEET = "TSN Normalization"

# Per-page band identity: the report id on its own line and one
# "Date<MM/DD/YY> California State Highway Log Page <n>" line (2,109 data
# pages statewide print exactly these). The cover adds the year. All are
# conserved source claims; the 12 members must agree (_cross_member_claims).
_REPORT_ID_RE = re.compile(r"^OTM\d+$")
_BAND_DATE_RE = re.compile(r"^Date(\d{2}/\d{2}/\d{2})\s+(.+?)\s+Page\s+\d+$")
_COVER_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
# Cover furniture (prints exactly once per document, on the title page).
_COVER_FURNITURE = ("CALIFORNIA DEPARTMENT OF TRANSPORTATION",
                    "California State Highway Log")

# Totals-block grammar. Star lines start LEFT of the description band
# (x0 7.9–21.5 across all 29 censused patterns); their wrapped continuation
# fragments join the open block. An asterisk-leading line INSIDE the
# description band is printed Description content, not totals — the corpus
# prints "**** CODE ACCIDENTS TO" (D03 YUB 065 R009.327) and a bare "*"
# there, which pre-v5 parsing silently dropped.
_TOTALS_STAR_X_MAX = DESC_X0_MIN
_OVERFLOW_RE = re.compile(r"^[#*]+$")          # "##########" / "**********"
_NUM_TOKEN_RE = re.compile(r"^-?[\d,]+(?:\.\d+)?$")
# The three ADT claim columns' shared horizontal zone (COLUMN_WINDOWS
# adt_back+adt_pp+adt_ahead). Values are re-tokenized by word gap and split
# around the single-letter P/S flag: wide Look Back figures overhang the
# fixed 448pt window boundary, so window-center assignment would corrupt the
# claim ("24,000" + "P" reading as "24,00" / "0 P").
_ADT_X_MIN, _ADT_X_MAX = 424, 486
_ADT_FLAGS = ("P", "S")

# City/County/District totals blocks (cumulative mileage + DVMS/DVMT volume)
# print BELOW the last data row of a group and WRAP onto their own lines. The
# first line starts with "*" (already skipped), but the wrapped continuations
# ("(DVMS) 3,391", "CUMULATIVE (MILEAGE) TOTAL …", "TOTAL CONST UNCONST",
# "County Cumulative DVM 123,414", bare mileage fragments) do not — and were
# being appended to the preceding row's Description, manufacturing false
# discrepancies in the TSMIS-vs-TSN comparison. These markers never occur in a
# real highway-feature description.
_TOTALS_RE = re.compile(
    r"\(DVM|\bDVM[ST]?\b|\bCUMULATIVE\b"
    r"|\b(?:CITY|COUNTY|DISTRICT|STATE)\s+TOTALS?\b|TOTALS?\s*\(MILEAGE\)",
    re.IGNORECASE)
# "UNCONST" alone is a real abbreviation (UNCONSTRUCTED) in genuine descriptions
# ("JCT UNCONST RTE 251", "BEG ST 14 UNCONST RD N") — so it marks a totals line
# ONLY in its footer context: paired with its CONST counterpart (the
# constructed/unconstructed mileage split "TOTAL CONST UNCONST" /
# "CONST 089.826 UNCONST 000.000") or immediately followed by a mileage figure
# ("UNCONST 000.000"). \bCONST\b / \bUNCONST\b word boundaries keep
# "CONSTRUCTION" / "UNCONSTRUCTED" descriptions safe.
_TOTALS_UNCONST_RE = re.compile(
    r"\bCONST\b.*\bUNCONST\b|\bUNCONST\s+[\d.]", re.IGNORECASE)
# A line that is ONLY digits/punctuation (bare cumulative-mileage / volume
# fragments, separator dashes) — but never a lone hyphenated structure number
# like "53-1075", which is a legitimate one-token bridge description.
_TOTALS_NUMERIC_RE = re.compile(r"[\d.,()$ +-]+")
_BRIDGE_NUMBER_RE = re.compile(r"^\d{2,3}-\d{2,4}[A-Z]?$")


def _is_totals_line(text):
    """True for a totals-block continuation line that must NOT be treated as a
    segment description (see _TOTALS_RE / _TOTALS_UNCONST_RE)."""
    stripped = text.strip()
    if _BRIDGE_NUMBER_RE.match(stripped):
        return False
    return bool(_TOTALS_RE.search(text)) \
        or bool(_TOTALS_UNCONST_RE.search(text)) \
        or bool(_TOTALS_NUMERIC_RE.fullmatch(stripped))


def _lines(page):
    """Cluster the page's characters into logical lines — word tokens for
    classifying the line AND raw characters for column parsing (values are
    assigned char by char: adjacent columns can sit closer than any
    word-segmentation tolerance, so pdfplumber's word extraction would fuse
    them, e.g. '042.010LKPT'). pdf_table_lib.char_lines."""
    return char_lines(page, Y_TOLERANCE, WORD_GAP)


def _parse_data_line(chars):
    """Map each character of a data line to its column by horizontal center.
    Characters of one column abut (~0pt apart); a gap >= WORD_GAP inside the
    same column means two separate tokens, kept apart with a space."""
    row = {}
    last_x1 = {}
    for c in chars:                   # x-sorted by _lines
        center = (c["x0"] + c["x1"]) / 2
        for key, lo, hi in COLUMN_WINDOWS:
            if lo <= center < hi:
                if key in row and c["x0"] - last_x1[key] >= WORD_GAP:
                    row[key] += " "
                row[key] = row.get(key, "") + c["text"]
                last_x1[key] = c["x1"]
                break
    return row


def _normalize_row(row):
    """Match the TSMIS number formats where TSN prints the same value
    differently (verified against the consolidated TSMIS Highway Log):
    MI is zero-padded to 3 integer digits (TSMIS '000.075', TSN '0.075');
    traveled-way widths carry no leading zeros (TSMIS '36', TSN '036')."""
    mi = row.get("mi")
    if mi:
        m = re.fullmatch(r"(\d+)\.(\d+)", mi)
        if m:
            row["mi"] = f"{int(m.group(1)):03d}.{m.group(2)}"
    for key in ("lb_tw", "rb_tw"):
        v = row.get(key)
        if v and re.fullmatch(r"\d{3,}", v):
            row[key] = v.lstrip("0").rjust(2, "0")


# The canonical route-token normalizer. RECONCILED (v0.19.0 R2): this module's
# old copy was `token.zfill(3) if token.isdigit() else token.upper()`, which
# never padded a SHORT SUFFIXED token ('5S' stayed '5S' while the TSMIS side
# prints '005S' — a latent row-misalignment) and kept over-padded digits
# ('0001'). Real district PDFs print the 'n'/'nn'/'nnn'/'nnnX' forms where the
# two agree; the highway_log TSN `normalization_version` is bumped anyway (D2)
# so any stored library re-keys itself on the next use.
_norm_route = norm_route


def _adt_zone(line_chars):
    """The row's three printed ADT claims, re-tokenized from the ADT zone.

    Returns {"back", "flag", "ahead", "tokens"} — verbatim printed tokens,
    split around the single-letter P/S flag when exactly one is present
    (every censused row prints one). Look Ahead is not always numeric
    ("D-C", "END" are printed claims and stay verbatim). The tokens tuple is
    always complete, so the claims digest binds the zone even if the flag
    grammar ever changes."""
    toks = []
    last_x1 = None
    for c in line_chars:                       # x-sorted by _lines
        center = (c["x0"] + c["x1"]) / 2
        if not (_ADT_X_MIN <= center < _ADT_X_MAX):
            continue
        if toks and c["x0"] - last_x1 < WORD_GAP:
            toks[-1] += c["text"]
        else:
            toks.append(c["text"])
        last_x1 = c["x1"]
    flags = [i for i, t in enumerate(toks) if t in _ADT_FLAGS]
    if len(flags) == 1:
        i = flags[0]
        return {"back": " ".join(toks[:i]) or None, "flag": toks[i],
                "ahead": " ".join(toks[i + 1:]) or None, "tokens": tuple(toks)}
    return {"back": None, "flag": None, "ahead": None, "tokens": tuple(toks)}


def _block_kind(text):
    """Classify one joined totals block by its printed keywords."""
    if "Volume Location Totals" in text:
        return "volume"
    for kind in ("CITY", "COUNTY", "ROUTE", "DISTRICT", "STATE"):
        if f"{kind} TOTALS" in text:
            return kind.lower()
    if "End of Report" in text:
        return "end_of_report"
    return "other"


# A stranded totals fragment: the print occasionally splits one totals line
# into keyword and value halves across a page break in EITHER order (censused:
# "TOTAL CONST UNCONST" labels at a page bottom whose value half prints
# elsewhere; a bare "164,329" whose star line tops the next page missing its
# DVM value). Such orphans are conserved verbatim as stray fragments — never
# guessed onto a block, never dropped — and only this strict vocabulary
# qualifies; arbitrary text still refuses as residue.
_TOTALS_FRAGMENT_WORDS = frozenset((
    "TOTAL", "CONST", "UNCONST", "CUMULATIVE", "TOTALS", "(MILEAGE)",
    "(DVMS)", "(within", "District)", "County", "Cumulative", "DVM", "Length",
))


def _totals_fragment_like(tokens):
    return tokens and all(
        t in _TOTALS_FRAGMENT_WORDS or _NUM_TOKEN_RE.match(t)
        or _OVERFLOW_RE.match(t)
        for t in tokens)


def _keyword_value(tokens, keyword, stop=()):
    """The first numeric-or-overflow token after `keyword`, or None. Stops at
    another keyword so a wrapped label line never steals a later value."""
    for i, t in enumerate(tokens):
        if t != keyword:
            continue
        for t2 in tokens[i + 1:]:
            if _NUM_TOKEN_RE.match(t2) or _OVERFLOW_RE.match(t2):
                return t2
            if t2 in stop:
                return None
        return None
    return None


def _mileage_values(tokens):
    """TOTAL/CONST/UNCONST/(DVMS) claims from one mileage totals block.
    Overflow markers ("##########"/"**********") are typed as overflow with
    no value — the print itself lost the figure. Values stay strings; the
    reconciliation parses them exactly (Decimal), never floats."""
    stop = ("TOTAL", "CONST", "UNCONST", "(DVMS)", "CUMULATIVE")
    out = {}
    for key in ("TOTAL", "CONST", "UNCONST"):
        tok = _keyword_value(tokens, key, stop)
        out[key.lower()] = None if tok is None or _OVERFLOW_RE.match(tok) else tok
        out[f"{key.lower()}_overflow"] = bool(tok and _OVERFLOW_RE.match(tok))
    dv = _keyword_value(tokens, "(DVMS)", stop)
    out["dvms"] = None if dv is None or _OVERFLOW_RE.match(dv) else dv
    out["dvms_overflow"] = bool(dv and _OVERFLOW_RE.match(dv))
    return out


def _block_record(page, kind, words):
    """One typed, conserved totals-block record for the claims sidecar."""
    text = " ".join(words)
    record = {"page": page, "kind": kind, "text": text}
    if kind in ("city", "county", "route", "district", "state"):
        head, _, cumulative = text.partition("CUMULATIVE")
        record["values"] = _mileage_values(head.split())
        if cumulative:
            record["cumulative"] = _mileage_values(cumulative.split())
    elif kind == "volume":
        toks = text.split()
        record["values"] = {
            "length": _keyword_value(toks, "Length", ("DVM",)),
            "dvm": _keyword_value(toks, "DVM", ("County",)),
        }
        m = re.search(r"County Cumulative DVM\s+(\S+)", text)
        record["values"]["county_cumulative_dvm"] = m.group(1) if m else None
    return record


def _claims_digest(items):
    """SHA-256 over a canonical JSON serialization — the exact typed binding
    for conserved-by-digest claim streams (ADT rows, totals blocks)."""
    canonical = json.dumps(items, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _single_claim(pdf_name, what, values):
    """Exactly one distinct claim value across a document, else refuse —
    a page disagreeing with its own document is a source integrity stop."""
    distinct = sorted({str(v) for v in values if v is not None})
    if len(distinct) != 1:
        detail = ", ".join(distinct) if distinct else "none"
        raise ValueError(
            f"{pdf_name}: expected exactly one printed {what} across the "
            f"document (found {detail})")
    return distinct[0]


def _kind_counts(blocks):
    counts = {}
    for b in blocks:
        counts[b["kind"]] = counts.get(b["kind"], 0) + 1
    return dict(sorted(counts.items()))


def _cross_member_claims(document_claims):
    """CMP-AUD-157: the 12 district prints must agree on the report identity
    — a member from a different TSN pull silently poisoning the library is
    exactly the cross-member inconsistency this refuses. Page counts, row
    counts, ownership manifests, ADT and totals claims stay per-document."""
    record = {"schema_version": 1}
    for field in ("report_id", "report_title", "report_date", "cover_year"):
        values = sorted({str(d[field]) for d in document_claims})
        if len(values) != 1:
            members = {d["member"]: str(d[field]) for d in document_claims}
            raise ValueError(
                f"the district prints disagree on the {field.replace('_', ' ')} "
                f"({members}) — all 12 must come from the same TSN pull")
        record[field] = values[0]
    record["documents"] = [
        {k: d[k] for k in ("member", "district", "pages", "n_rows",
                           "cover_furniture", "ownership", "adt", "totals")}
        for d in sorted(document_claims, key=lambda d: d["district"])
    ]
    suffixed = {}
    for d in document_claims:
        for o in d["ownership"]:
            if o["suffix"]:
                key = (o["route"], d["district"], o["county"])
                suffixed[key] = suffixed.get(key, 0) + o["n_rows"]
    record["suffixed_route_sections"] = [
        f"{route} (D{district} {county}, {rows} row(s))"
        for (route, district, county), rows in sorted(suffixed.items())]
    return record


def _reconciliation_problems(document_claims):
    """The HARD-GATED reconciliation classes (2026-07-17 full-corpus
    measurement: both hold exactly — 2,914/2,914 parsed mileage groups
    incl. the county-cumulative sections, and all 22 suffixed-section
    totals lines print zero). A violation means the print's own arithmetic
    or the suffixed-section accounting broke, i.e. the parse can no longer
    be trusted to have conserved the row universe. Route/county-vs-
    additive-sum tracking stays a recorded measurement (see parse_pdf's
    recon comment)."""
    problems = []
    for d in document_claims:
        recon = d["totals"]["reconciliation"]
        for gate in ("tcu", "suffixed_zero"):
            for detail in recon[gate]["mismatches"][:2]:
                problems.append(f"{d['member']} ({gate}) {detail}")
    return "; ".join(problems)


def parse_pdf(path, events, pdf_name=""):
    """Parse one TSN district Highway Log PDF.

    Returns (district, routes, claims) — routes is {route: [row_dict, ...]}
    in document order (route includes any detached printed suffix, "005S");
    claims is the document's CMP-AUD-157 source-claims record: report
    identity/date/year, the per-group ownership manifest (district/county/
    route/suffix/page/row count), the three per-row ADT claims
    (counts/vocabulary/digest), every totals block (typed values + digest)
    with its row-universe reconciliation, and the zero-residue accounting.
    Every below-band line must classify (data / description / group header /
    district line / totals block or fragment / cover furniture) — anything
    else refuses rather than silently vanishing.
    """
    name = pdf_name or Path(path).name
    district_claims = []
    routes = {}
    route = None
    last_row = None                   # description lines attach to this
    seen_group = False                # cover furniture is only valid before any
    ownership = []                    # one entry per printed group header
    band_ids, band_dates, band_titles = [], [], []
    cover_years, cover_furniture = [], []
    adt_stream = []                   # (route, location, back, flag, ahead)
    adt_counts = {"back": 0, "flag": 0, "ahead": 0}
    adt_vocab = {}
    blocks = []                       # typed totals-block records
    open_block = None                 # {"page":…, "words":[…]} being assembled
    stray_fragments = []              # totals-like in-band lines, no open block
    residue = []                      # unexplained below-band lines -> refuse
    recon = {
        # HARD GATES (_reconciliation_problems): the print's own internal
        # arithmetic and the suffixed-section accounting must hold exactly —
        # 2026-07-17 full-corpus measurement: 2,914/2,914 parsed mileage
        # groups satisfy TOTAL == CONST + UNCONST and all 22 suffixed-
        # section totals lines print zero.
        "tcu": {"checked": 0, "mismatches": []},
        "suffixed_zero": {"checked": 0, "mismatches": []},
        # RECORDED MEASUREMENTS (disclosed, never certified): printed
        # route/county totals track an odometer-based additive-mileage
        # accounting (non-additive NA='N' rows excluded, realignment/equate
        # odometer corrections) that summing the MI column does not fully
        # model — the same full-corpus measurement leaves small two-sided
        # residuals on base routes. Volume DVM tracks Length x ADT.
        "route": {"checked": 0, "exact": 0, "samples": []},
        "county": {"checked": 0, "exact": 0, "samples": []},
        "volume_length": {"checked": 0, "exact": 0, "zero_printed": 0,
                          "off_001": 0, "other": 0},
        "volume_dvm": {"checked": 0, "within_1": 0, "zero_printed": 0,
                       "overflow": 0, "other": 0},
        "disposition": "tcu_and_suffixed_zero_gated_rest_measured",
    }
    route_sums = {}                   # additive MI per route (NA != 'N')
    county_sums = {}                  # additive MI per (route, county)
    vol_mi = Decimal(0)               # MI since the last volume block
    vol_dvm = Decimal(0)              # per-row Length x ADT accumulation
    last_ahead = None                 # most recent numeric Look Ahead claim

    def dec(tok):
        return Decimal(str(tok).replace(",", ""))

    def reconcile_mileage(record, block, page_no):
        """TOTAL == CONST + UNCONST on every fully parsed mileage line and
        all-zero totals on suffixed sections are exact gates; route/county
        totals vs the additive MI sums are recorded measurements. The block
        binds its owning (route, county) at OPEN time — a totals object can
        wrap past the next page's reprinted group header."""
        vals = record.get("values") or {}
        groups = [vals]
        if record.get("cumulative"):
            groups.append(record["cumulative"])
        for g in groups:
            if g.get("total") and g.get("const") and g.get("unconst"):
                recon["tcu"]["checked"] += 1
                if (dec(g["total"]) != dec(g["const"]) + dec(g["unconst"])
                        and len(recon["tcu"]["mismatches"]) < 8):
                    recon["tcu"]["mismatches"].append(
                        f"p{page_no} {record['kind']}: {g['total']} != "
                        f"{g['const']} + {g['unconst']}")
        if record["kind"] not in ("route", "county"):
            return
        printed = vals.get("total")
        if printed is None:
            return
        b_route, b_county = block.get("route"), block.get("county")
        if b_route and b_route[-1].isalpha():
            recon["suffixed_zero"]["checked"] += 1
            if (dec(printed) != 0
                    and len(recon["suffixed_zero"]["mismatches"]) < 8):
                recon["suffixed_zero"]["mismatches"].append(
                    f"p{page_no} {b_route}: printed {printed}")
            return
        parsed = (route_sums.get(b_route, Decimal(0))
                  if record["kind"] == "route"
                  else county_sums.get((b_route, b_county), Decimal(0)))
        bucket = recon[record["kind"]]
        bucket["checked"] += 1
        if dec(printed) == parsed:
            bucket["exact"] += 1
        elif len(bucket["samples"]) < 5:
            bucket["samples"].append(
                f"p{page_no} {b_route}: printed {printed} vs additive {parsed}")

    def reconcile_volume(record, page_no):
        nonlocal vol_mi, vol_dvm
        vals = record.get("values") or {}
        length, dvm = vals.get("length"), vals.get("dvm")
        if length is not None and not _OVERFLOW_RE.match(length):
            printed = dec(length)
            recon["volume_length"]["checked"] += 1
            if printed == vol_mi:
                recon["volume_length"]["exact"] += 1
            elif printed == 0:
                recon["volume_length"]["zero_printed"] += 1
            elif abs(printed - vol_mi) <= Decimal("0.001"):
                recon["volume_length"]["off_001"] += 1
            else:
                recon["volume_length"]["other"] += 1
        if dvm is not None:
            recon["volume_dvm"]["checked"] += 1
            if _OVERFLOW_RE.match(dvm):
                recon["volume_dvm"]["overflow"] += 1
            elif dec(dvm) == 0:
                recon["volume_dvm"]["zero_printed"] += 1
            elif abs(dec(dvm) - vol_dvm.quantize(Decimal(1))) <= 1:
                recon["volume_dvm"]["within_1"] += 1
            else:
                recon["volume_dvm"]["other"] += 1
        vol_mi = Decimal(0)
        vol_dvm = Decimal(0)

    def close_block(page_no):
        nonlocal open_block
        if open_block is None:
            return
        record = _block_record(open_block["page"], open_block["kind"],
                               open_block["words"])
        blocks.append(record)
        block, open_block = open_block, None
        if record["kind"] in ("city", "county", "route", "district", "state"):
            reconcile_mileage(record, block, page_no)
        elif record["kind"] == "volume":
            reconcile_volume(record, page_no)

    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        for page_no, page in enumerate(pdf.pages, 1):
            if events.is_cancelled():
                return None, None, None
            if page_no % 25 == 0:
                events.on_log(f"    …page {page_no}/{n_pages}")
            for top, words, line_chars in _lines(page):
                texts = [w["text"] for w in words]
                first = words[0]
                text = " ".join(texts)
                if top < HEADER_BAND:
                    # Page furniture band; the report id and the
                    # Date/title/page line are conserved identity claims.
                    if _REPORT_ID_RE.match(text):
                        band_ids.append(text)
                    else:
                        m = _BAND_DATE_RE.match(text)
                        if m:
                            band_dates.append(m.group(1))
                            band_titles.append(m.group(2))
                    continue

                # Totals star lines print LEFT of the description band; an
                # asterisk-leading line INSIDE the band is printed Description
                # content (falls through to the description handling below). A
                # totals line still marks the END of the current segment's
                # data + description, so it CLOSES the open row. The one
                # centered star line — "*** End of Report ***" (x0~209) — is
                # its own typed marker, never a description or a fragment.
                if texts[0].startswith("*") and (
                        first["x0"] < _TOTALS_STAR_X_MAX
                        or "End of Report" in text):
                    close_block(page_no)
                    open_block = {"page": page_no, "words": list(texts),
                                  "kind": _block_kind(text), "route": route,
                                  "county": (ownership[-1]["county"]
                                             if ownership else None)}
                    last_row = None
                    continue

                # Title page: "District 01" pins the district number.
                m = DISTRICT_LINE_RE.match(text)
                if m:
                    district_claims.append(m.group(1))
                    continue

                # Centered group header: "<district> <county> <route>" with an
                # optional detached single-letter route suffix ("07 LA 005 S").
                if (len(texts) >= 3 and 250 <= first["x0"] <= 305
                        and GROUP_RE[0].match(texts[0])
                        and GROUP_RE[1].match(texts[1])
                        and GROUP_RE[2].match(texts[2])):
                    if len(texts) > 4 or (len(texts) == 4
                                          and not GROUP_SUFFIX_RE.match(texts[3])):
                        raise ValueError(
                            f"{name} p{page_no}: unrecognized group-header "
                            f"grammar cannot safely own following rows: {text!r}")
                    # A group header does NOT close an open totals block: the
                    # print reprints the current group at each page top, and a
                    # totals object that wraps across the page break continues
                    # BELOW that reprinted header (D02 p7->p8: the county
                    # block's CUMULATIVE value lands after "02 TRI 003").
                    seen_group = True
                    district_claims.append(texts[0])
                    suffix = texts[3] if len(texts) == 4 else ""
                    vol_mi = Decimal(0)
                    vol_dvm = Decimal(0)
                    route = _norm_route(texts[2] + suffix)
                    routes.setdefault(route, [])
                    ownership.append({
                        "page": page_no, "district": texts[0],
                        "county": texts[1], "route_token": texts[2],
                        "suffix": suffix, "route": route, "n_rows": 0,
                    })
                    last_row = None                   # don't attach across groups
                    continue
                # A centered line beginning with a district-like number and a
                # short county-like token is structurally a group header. If it
                # misses the exact district/county/route grammar, retaining the
                # prior route would silently misattribute every following row.
                if (len(texts) >= 2 and 250 <= first["x0"] <= 305
                        and re.fullmatch(r"\d{1,2}", texts[0])
                        and re.fullmatch(r"[A-Z0-9.]{2,5}", texts[1], re.IGNORECASE)):
                    raise ValueError(
                        f"{name} p{page_no}: malformed centered district/county/route "
                        f"group header cannot safely own following rows: {text!r}")

                # Data line: starts with a postmile in the Location window.
                if LOCATION_RE.match(texts[0]) and first["x0"] < 50:
                    if route is None:
                        raise ValueError(
                            f"{name} p{page_no}: recognizable highway-log data "
                            "appeared before any owning route header")
                    close_block(page_no)
                    row = _parse_data_line(line_chars)
                    _normalize_row(row)
                    row["description"] = None
                    routes[route].append(row)
                    ownership[-1]["n_rows"] += 1
                    last_row = row
                    adt = _adt_zone(line_chars)
                    adt_stream.append([route, row.get("location"),
                                       adt["back"], adt["flag"], adt["ahead"]])
                    for k in ("back", "flag", "ahead"):
                        if adt[k] is not None:
                            adt_counts[k] += 1
                    if adt["flag"] is not None:
                        adt_vocab[adt["flag"]] = adt_vocab.get(adt["flag"], 0) + 1
                    mi = row.get("mi")
                    mi_d = dec(mi) if mi and _NUM_TOKEN_RE.match(mi) else Decimal(0)
                    # Volume sections include every printed row; the additive
                    # route/county accounting excludes non-additive NA='N'
                    # rows (measured against the print's own totals).
                    vol_mi += mi_d
                    if str(row.get("na") or "").strip().upper() != "N":
                        county = ownership[-1]["county"]
                        route_sums[route] = (
                            route_sums.get(route, Decimal(0)) + mi_d)
                        county_sums[(route, county)] = (
                            county_sums.get((route, county), Decimal(0)) + mi_d)
                    if adt["ahead"] and _NUM_TOKEN_RE.match(adt["ahead"]):
                        last_ahead = dec(adt["ahead"])
                    if last_ahead is not None:
                        vol_dvm += mi_d * last_ahead
                    continue

                # Below-band, non-data. A wrapped totals continuation joins the
                # open block from any x position — EXCEPT a description-band
                # line that isn't totals-like, which closes the block and is
                # handled as printed Description content.
                in_desc_band = DESC_X0_MIN <= first["x0"] <= DESC_X0_MAX
                if open_block is not None and (not in_desc_band
                                               or _is_totals_line(text)):
                    open_block["words"].extend(texts)
                    if open_block["kind"] == "other":
                        open_block["kind"] = _block_kind(
                            " ".join(open_block["words"]))
                    continue
                if open_block is not None:
                    close_block(page_no)
                if in_desc_band:
                    if _is_totals_line(text):
                        stray_fragments.append(
                            {"page": page_no, "x0": round(first["x0"], 1),
                             "text": text})
                        continue
                    if last_row is not None:
                        last_row["description"] = (
                            text if not last_row["description"]
                            else last_row["description"] + ", " + text)
                        continue
                    residue.append(f"p{page_no} x0={first['x0']:.0f}: {text!r}")
                    continue
                # Cover furniture (title page only, before any group header).
                if not seen_group and (text in _COVER_FURNITURE
                                       or _COVER_YEAR_RE.match(text)):
                    if _COVER_YEAR_RE.match(text):
                        cover_years.append(text)
                    else:
                        cover_furniture.append(text)
                    continue
                # A stranded keyword/value half of a page-break-split totals
                # line: conserved verbatim, never guessed onto a block.
                if _totals_fragment_like(texts):
                    stray_fragments.append(
                        {"page": page_no, "x0": round(first["x0"], 1),
                         "text": text})
                    continue
                residue.append(f"p{page_no} x0={first['x0']:.0f}: {text!r}")
        close_block(n_pages)

    if residue:
        shown = "; ".join(residue[:5])
        raise ValueError(
            f"{name}: {len(residue)} below-band line(s) could not be "
            f"classified (data/description/group/totals/cover) — refusing "
            f"rather than dropping printed source content: {shown}")

    district = tdc.document_district(district_claims, name)
    n_rows = sum(len(rows) for rows in routes.values())
    claims = {
        "member": name,
        "district": district,
        "report_id": _single_claim(name, "report id", band_ids),
        "report_title": _single_claim(name, "report title", band_titles),
        "report_date": _single_claim(name, "report date", band_dates),
        "cover_year": _single_claim(name, "cover year", cover_years),
        "pages": n_pages,
        "n_rows": n_rows,
        "ownership": ownership,
        "cover_furniture": sorted(set(cover_furniture)),
        "adt": {"disposition": "tsn_only_no_tsmis_column_conserved_by_digest",
                "rows": n_rows, "non_empty": adt_counts,
                "flag_vocabulary": dict(sorted(adt_vocab.items())),
                "digest_sha256": _claims_digest(adt_stream)},
        # The typed values were parsed and reconciled above; the sidecar
        # binds the exact verbatim stream by digest (re-derivable from the
        # conserved raw PDFs) rather than duplicating ~10k block texts.
        "totals": {"disposition": "conserved_by_digest_typed_reconciled",
                   "kind_counts": _kind_counts(blocks),
                   "digest_sha256": _claims_digest(
                       [[b["page"], b["kind"], b["text"]] for b in blocks]),
                   "stray_fragments": stray_fragments,
                   "reconciliation": recon},
    }
    return district, routes, claims


# =============================================================================
# TSMIS-format per-route workbooks
# =============================================================================

def _write_marker_sheet(wb):
    """The v5 normalization marker (CMP-AUD-157/045-HL): the rows sheet kept
    its 31-column SHAPE, so a stale pre-v5 workbook — detached route suffixes
    merged into the base route, asterisk-leading Descriptions dropped, no
    conserved source claims — is indistinguishable by shape. The vs-TSN
    comparison loaders gate on this sheet; the library path additionally
    auto-rebuilds via report_catalog's normalization_version (D2)."""
    marker = wb.create_sheet(MARKER_SHEET)
    marker.append(["Report", REPORT_NAME])
    marker.append(["Normalization version", NORMALIZATION_VERSION])


def _decorate_normalized(wb):
    hlc.write_legend_sheet(wb)
    _write_marker_sheet(wb)


def _write_route_workbook(rows, out_path):
    """Write one route's rows as a TSMIS-format Highway Log workbook."""
    write_route_workbook(rows, out_path, sheet_name=SHEET_NAME, header=TSMIS_HEADER,
                         row_values=lambda row: [row.get(k) for k in ROW_KEYS],
                         apply_tooltips=hlc.apply_header_tooltips,
                         decorate=_decorate_normalized)


# =============================================================================
# Entry point
# =============================================================================

def build_into(raw_dir, out_path, events=None, confirm_overwrite=None,
               scratch_root=None, commit_guard=None):
    """Canonical-TSN-library entry point: parse the district PDFs in `raw_dir` and
    write the combined workbook to `out_path`. A thin wrapper over consolidate()
    so tsn_library can build any report through one uniform builder signature."""
    return consolidate(events=events, confirm_overwrite=confirm_overwrite,
                       input_dir=raw_dir, out_path=out_path,
                       scratch_root=scratch_root, commit_guard=commit_guard)


def consolidate(events=None, confirm_overwrite=None, day=None,
                input_dir=None, out_path=None, scratch_root=None,
                commit_guard=None):
    """Convert every TSN district Highway Log PDF to TSMIS-format per-route
    workbooks, then combine them all into one workbook (Route column added).

    `day` is accepted for interface compatibility with the other consolidators
    and ignored — TSN PDFs are vendor snapshots in one fixed input folder, not
    dated exports. `input_dir`/`out_path` override the fixed legacy locations
    (the canonical TSN library passes its own raw/consolidated paths here);
    when omitted they default to the legacy INPUT_DIR / OUT_PATH. Every call uses
    a private temporary conversion directory under ``scratch_root`` or, by
    default, the requested output's parent. The temporary directory is never the
    process-global ``CONVERTED_DIR`` and is removed after every terminal path.

    Console-free: reports progress via events.on_log, asks before overwriting
    through the confirm_overwrite(path)->bool callback, and returns a
    ConsolidateResult. Honors events.is_cancelled() between pages.
    """
    in_dir = Path(input_dir) if input_dir else INPUT_DIR
    out = Path(out_path) if out_path else OUT_PATH
    events = events or Events()
    if not _DEPS_OK:
        return ConsolidateResult(
            status="error",
            message="Required components are missing (pdfplumber, openpyxl).",
        )
    confirm = confirm_overwrite or (lambda _p: True)

    # Create the input folder on first use so the user has somewhere to drop
    # the PDFs (the error below then names a real, openable folder).
    try:
        in_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    pdfs = sorted(p for p in in_dir.glob("*.pdf") if p.is_file())
    if not pdfs:
        return ConsolidateResult(
            status="error",
            message=(f"No {REPORT_NAME} files were found in:\n{in_dir}\n\n"
                     f"Put the district Highway Log PDFs (e.g. "
                     f"D01_Highway_Log_TSN.pdf) there, then run again."),
        )

    # Confirm overwrite *before* spending time parsing PDFs.
    existed_at_confirm = out.exists()
    if existed_at_confirm and not confirm(out):
        return ConsolidateResult(status="cancelled",
                                 message="Cancelled. Existing file kept.")

    events.on_log("=" * 60)
    events.on_log(f"TSN Highway Log Conversion - {len(pdfs)} district PDF(s)")
    events.on_log("=" * 60)
    events.on_log("")

    # Build under the requested output boundary unless the caller explicitly
    # supplies another scratch boundary. This directory is ordinary temporary
    # state (not a persistent Reset-owned store), but its exact filesystem
    # identity is bound from creation through every write and final cleanup.
    scratch_parent = Path(scratch_root) if scratch_root is not None else out.parent
    scratch_parent = scratch_parent.absolute()
    if not consolidation_meta.guard_allows(commit_guard, scratch_parent):
        return ConsolidateResult(
            status="error",
            message="The destination changed while preparing the conversion; nothing was published.",
        )
    try:
        scratch_parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ConsolidateResult(
            status="error",
            message=(f"Could not create temporary conversion space under:\n"
                     f"{scratch_parent}\n\n{type(e).__name__}: {e}"),
        )
    if not consolidation_meta.guard_allows(commit_guard, scratch_parent):
        return ConsolidateResult(
            status="error",
            message="The destination changed while preparing the conversion; nothing was published.",
        )
    try:
        conv = Path(tempfile.mkdtemp(prefix=".tsn-highway-log-attempt-",
                                     dir=scratch_parent))
    except OSError as e:
        return ConsolidateResult(
            status="error",
            message=(f"Could not create temporary conversion space under:\n"
                     f"{scratch_parent}\n\n{type(e).__name__}: {e}"),
        )
    conv_identity = owned_dir.directory_identity(conv)

    def attempt_current(path):
        return (conv_identity is not None
                and owned_dir.directory_identity(conv) == conv_identity
                and consolidation_meta.guard_allows(commit_guard, path))

    def destination_changed():
        return ConsolidateResult(
            status="error",
            message="The destination changed while converting PDFs; nothing was published.",
        )

    try:
        if not attempt_current(conv):
            return destination_changed()

        try:
            source_manifest, source_bytes = tdc.capture_raw_manifest(pdfs, in_dir)
        except ValueError as e:
            return ConsolidateResult(
                status="error",
                message=f"The TSN Highway Log raw source could not be bound: {e}",
            )

        source_problem = [None]

        def source_current():
            try:
                current_pdfs = sorted(
                    p for p in in_dir.glob("*.pdf") if p.is_file())
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
                message=(f"The TSN Highway Log raw source changed while it was being "
                         f"normalized ({detail}); last-good output was preserved."),
            )

        converted = 0
        failed = []
        claimed_districts = {}
        document_claims = []
        written = set()              # duplicate district+route diagnostic
        generated = {}               # exact final member manifest for THIS attempt
        for i, p in enumerate(pdfs, 1):
            if events.is_cancelled():
                return ConsolidateResult(status="cancelled", message="Cancelled by user.")
            prefix = f"[{i}/{len(pdfs)}] {p.name}"
            events.on_log(f"{prefix} parsing…")
            try:
                district, route_rows, doc_claims = parse_pdf(
                    io.BytesIO(source_bytes[p.name]), events, pdf_name=p.name)
            except Exception as e:
                events.on_log(f"{prefix} FAILED ({type(e).__name__}): {e}")
                failed.append(p.name)
                continue
            if route_rows is None:                   # cancelled mid-PDF
                return ConsolidateResult(status="cancelled", message="Cancelled by user.")
            if not route_rows:
                events.on_log(f"{prefix} no highway-log data found; skipping")
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
            document_claims.append(doc_claims)
            for route, rows in route_rows.items():
                out_file = conv / f"tsn_highway_log_d{district}_route_{route}.xlsx"
                if out_file.name in written:
                    events.on_log(f"  WARNING: district {district} route {route} already "
                                  f"converted from an earlier PDF; {p.name} replaces it "
                                  "(is the same district in the folder twice?)")
                written.add(out_file.name)
                if not attempt_current(out_file):
                    return destination_changed()
                try:
                    _write_route_workbook(rows, out_file)
                except PermissionError:
                    return ConsolidateResult(
                        status="error",
                        message=(f"Could not save {out_file.name}.\n\n"
                                 "The file is probably open in Excel. Close it and try again."),
                    )
                if not attempt_current(out_file):
                    return destination_changed()
                generated[out_file.name] = out_file
                events.on_log(f"  district {district} route {route}: {len(rows)} rows "
                              f"-> {out_file.name}")
                converted += 1

        if converted == 0:
            return ConsolidateResult(
                status="error",
                message=(f"None of the PDFs in:\n{in_dir}\n\ncontained readable "
                         f"{REPORT_NAME} data. Are they the TSN California State "
                         "Highway Log PDFs?"),
            )

        if failed:
            return ConsolidateResult(
                status="error", failed_inputs=len(failed),
                message=(f"The TSN Highway Log source is incomplete or unreadable: "
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
        try:
            source_claims = _cross_member_claims(document_claims)
        except ValueError as e:
            return ConsolidateResult(
                status="error",
                message=f"The TSN Highway Log source claims are inconsistent: {e}")
        problems = _reconciliation_problems(document_claims)
        if problems:
            return ConsolidateResult(
                status="error",
                message=("The printed totals do not reconcile with the parsed "
                         f"rows: {problems} — refusing to publish a normalized "
                         "workbook whose row universe disagrees with the "
                         "print's own accounting."))
        if not source_current():
            return source_changed()

        events.on_log("")
        manifest = tuple(generated[name] for name in sorted(generated))
        if (not attempt_current(conv)
                or any(not attempt_current(member) or not member.is_file()
                       for member in manifest)):
            return destination_changed()

        # Combine only the exact member generation produced above. No directory
        # glob participates in this attempt, so a peer build cannot add an input
        # even if it overlaps the parse/combine interval.
        def publish_guard(path):
            return attempt_current(path) and source_current()

        result = consolidate_xlsx(
            input_dir=conv, input_files=manifest,
            out_path=out, sheet_name=SHEET_NAME,
            report_name=REPORT_NAME, title="TSN Highway Log Consolidation",
            events=events, confirm_overwrite=confirm,
            existed_at_confirm=existed_at_confirm,
            header_override=hlc.HEADER, header_comment=hlc.comment_for,
            decorate_workbook=_decorate_normalized,
            commit_guard=publish_guard,
        )
        if source_problem[0] and result.status != "ok":
            return source_changed()
        if result.status == "ok":
            # CMP-AUD-035: re-verify the raw source AFTER the os.replace. The
            # publish_guard checks source_current() AT the replace boundary, but a
            # change in the window between that check and the replace would still
            # publish stale-source bytes as success. The canonical build_consolidated
            # wrapper rehashes post-builder; this DIRECT/CLI path needs its own
            # post-replace recheck so it never returns success for a changed source.
            if not source_current():
                return source_changed()
            result.tsn_raw_manifest = source_manifest
            n_suffixed = len(source_claims["suffixed_route_sections"])
            result.summary_lines = [
                f"District PDFs:  {len(pdfs)} converted; exact D01-D12",
                f"Route files:    {len(manifest)} temporary conversion member(s)",
                (f"Print identity: {source_claims['report_id']} "
                 f"{source_claims['report_title']} · report "
                 f"{source_claims['report_date']} · cover year "
                 f"{source_claims['cover_year']}"),
                (f"Suffixed route sections: {n_suffixed} "
                 "(detached printed suffixes join the route, e.g. 005S)"
                 if n_suffixed else
                 "Suffixed route sections: none printed"),
            ] + result.summary_lines
            # CMP-AUD-157: ownership/qualifier/ADT/totals/provenance claims
            # ride the library sidecar (tsn_library.build_normalized merges
            # producer_extra); the comparison Notes read them back.
            result.producer_extra = {"tsn_source_claims": source_claims}
        return result
    finally:
        # Never traverse a replaced/linked attempt path. If identity or tree
        # safety is lost, retain it and emit an explicit diagnostic for manual
        # inspection instead of deleting an object the attempt no longer owns.
        if (conv_identity is not None
                and owned_dir.directory_identity(conv) == conv_identity
                and owned_dir.is_plain_directory_tree(conv, identity=conv_identity)):
            try:
                shutil.rmtree(conv)
            except OSError as e:
                events.on_log(f"WARNING: temporary conversion folder was retained: "
                              f"{conv} ({type(e).__name__}: {e})")
        else:
            events.on_log("WARNING: temporary conversion folder changed identity or "
                          f"contains a linked entry; it was retained: {conv}")


if __name__ == "__main__":
    from cli import run_consolidate_cli
    run_consolidate_cli(consolidate)
