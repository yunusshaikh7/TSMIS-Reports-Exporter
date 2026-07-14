"""Build the TSMIS-vs-TSN Highway Sequence (Highway Locations) comparison
workbook (FLAT, keyed on route + county + postmile).

Both sides are highway postmile-sequence listings — the direct analog of the
Highway Log comparison, with the same "TSN lists more segment breaks, TSMIS more
realignment markers" one-sided behavior. Reconciled by hand against the 6.19
ground truth (docs/tsn-parsers.md):

  * TSMIS side — the CONSOLIDATED Highway Sequence workbook (sheet "Highway
    Locations", leading Route column). Its header has two unnamed columns (a
    postmile prefix and an equate suffix), so it is read BY POSITION:
      0 Route · 1 County · 2 City · 3 prefix · 4 PM · 5 suffix · 6 HG · 7 FT
      · 8 Distance To Next Point · 9 Description
    The canonical postmile re-glues prefix+PM+suffix ("R" + "000.129" -> "R000.129").
  * TSN side — the normalized workbook built by consolidate_tsn_highway_sequence
    from the district PDFs (its NORMALIZED_HEADER, postmile already glued).

CALIFORNIA postmiles are COUNTY-RELATIVE (a route restarts at 000.000 in each
county), so route+PM is NOT unique across a route — the key is route + county +
postmile (county folded into the key via key_normalizer, kept as its own visible
column). Landmarks that still share a (route, county, PM) pair (e.g. a "COUNTY
BEGIN" marker at the same postmile) are matched by data similarity in compare_core.

Console-free; engine in compare_core.
"""
import re
from pathlib import Path

try:
    from openpyxl import load_workbook
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import compare_tsn_common as ctc
from compare_tsn_common import (load_consolidated_rows, row_has_data,
                                suggest_route_name)
import consolidate_tsn_highway_sequence as tsn_hsl
from compare_core import CompareSchema, normalize_value

REPORT_NAME = "Highway Sequence"
TSMIS_SHEET = "Highway Locations"          # consolidated sheet (Route prepended)

KEY = "PM"
SHARED_HEADER = ["County", "PM", "City", "HG", "FT",
                 "Distance To Next Point", "Description"]
KEY_FIELD = SHARED_HEADER.index(KEY)       # 1

# Shown but NEVER counted as a difference (completeness gaps / listing artifacts,
# not real disagreements about the highway):
#   HG       — TSMIS leaves the highway-group blank for whole counties while TSN
#              always fills it (U/D); counting it would flood blank-vs-U cells.
#   City     — TSN assigns a city code far more aggressively than TSMIS (TSN tags
#              the nearest incorporated place; TSMIS only within strict limits).
#   Distance — "distance to next point" is measured to each system's OWN next
#              listed point; TSN lists more (finer) breaks, so its gap is usually
#              smaller (TSMIS 003.572 vs TSN 000.174 at the same postmile). It is
#              an artifact of listing granularity, not a data disagreement.
# FT and Description ARE compared (genuine feature-type / wording differences).
# County is part of the key (always equal within a matched pair); PM is the key.
CONTEXT_FIELDS = ("HG", "City", "Distance To Next Point")

# Consolidated-TSMIS VALUE positions (Route at 0; verified on the 6.19 set).
_TSMIS = {"route": 0, "county": 1, "city": 2, "prefix": 3, "pm": 4,
          "suffix": 5, "hg": 6, "ft": 7, "dist": 8, "desc": 9}


# --------------------------------------------------------------------------- #
# normalization
# --------------------------------------------------------------------------- #
_WS_RE = re.compile(r"[\t\n\r\f\v]")


def _v(x):
    """compare_core.normalize_value plus tab/newline collapse (the TSMIS export
    pads Description with trailing tabs that Excel TRIM does not strip)."""
    nv = normalize_value(x)
    return _WS_RE.sub(" ", nv).strip() if isinstance(nv, str) else nv


def _norm_county(x):
    """Canonical county code. TSMIS writes a trailing period on several codes
    ("LA.", "SB.", "SM.", "SF.", "CC.", "DN.", "ED.", "SD.", "SJ.") that the TSN
    report omits — strip it so the county-relative postmile key matches."""
    s = "" if x is None else str(x).strip().rstrip(".")
    return s.upper()


_DESC_PREFIX_RE = re.compile(r"^\d{1,3}[A-Z]?/")


def _norm_desc(x):
    """Description, normalized for comparison:
      * strip the TSMIS leading route prefix "<route>/" ("001/NB OFF TO DOHENY PK
        RD") that TSN omits (same as Ramp Detail; no-op on the prefix-less TSN);
      * collapse internal whitespace runs to one space (the TSMIS export sprinkles
        double spaces — "SB ON  ARGYLE AV" — where TSN has one)."""
    s = _v(x)
    if isinstance(s, str):
        return re.sub(r"\s+", " ", _DESC_PREFIX_RE.sub("", s)).strip()
    return s


def _glue_pm(prefix, pm, suffix):
    """Re-glue the TSMIS prefix/PM/suffix columns into the canonical postmile the
    TSN side prints ("R" + "000.129" + "" -> "R000.129"; "" + "050.025" + "E"
    -> "050.025E")."""
    p = "" if prefix is None else str(prefix).strip()
    m = "" if pm is None else str(pm).strip()
    s = "" if suffix is None else str(suffix).strip()
    return f"{p}{m}{s}"


def _key_county_pm(row, off, key_field):
    """Composite identity 'COUNTY POSTMILE' — California postmiles are
    county-relative (a route restarts at 000.000 in each county), so the postmile
    alone is not unique across a route. The engine shows this in the key column;
    County also stays its own visible column for filtering. (Same idea as the
    Highway Log roadbed-canonical key.)"""
    county = row[off + SHARED_HEADER.index("County")]
    pm = row[off + key_field]
    return f"{'' if county is None else str(county).strip()} " \
           f"{'' if pm is None else str(pm).strip()}".strip()


# --------------------------------------------------------------------------- #
# loaders -> consolidated-shape rows ([route, *SHARED_HEADER])
# --------------------------------------------------------------------------- #
def _tsmis_row(r):
    def at(i):
        return r[i] if i < len(r) else None
    route = _v(at(_TSMIS["route"]))
    return [route,
            _norm_county(at(_TSMIS["county"])),
            _glue_pm(at(_TSMIS["prefix"]), at(_TSMIS["pm"]), at(_TSMIS["suffix"])),
            _v(at(_TSMIS["city"])),
            _v(at(_TSMIS["hg"])),
            _v(at(_TSMIS["ft"])),
            _v(at(_TSMIS["dist"])),
            _norm_desc(at(_TSMIS["desc"]))]


def _load_tsmis(path):
    return load_consolidated_rows(
        path, TSMIS_SHEET,
        missing_sheet_hint="pick the consolidated TSMIS Highway Sequence workbook.",
        bad_header_msg="isn't a CONSOLIDATED Highway Sequence workbook "
                       "(expected a leading 'Route' column) — consolidate first.",
        row_transform=_tsmis_row)


def _load_tsn(path):
    """The normalized TSN workbook (consolidate_tsn_highway_sequence output):
    NORMALIZED_HEADER = [Route] + SHARED_HEADER, read positionally."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        sn = tsn_hsl.NORMALIZED_SHEET
        if sn not in wb.sheetnames:
            raise ValueError(f"{name} has no '{sn}' sheet — pick the normalized TSN "
                             "Highway Sequence workbook (built from the district PDFs).")
        it = wb[sn].iter_rows(values_only=True)
        next(it, None)                         # header
        width = len(SHARED_HEADER) + 1         # Route + fields
        county_idx = 1 + SHARED_HEADER.index("County")
        desc_idx = 1 + SHARED_HEADER.index("Description")
        rows = []
        for r in it:
            if not row_has_data(r):
                continue
            r = list(r)[:width] + [None] * max(0, width - len(r))
            row = [_v(c) for c in r]
            row[county_idx] = _norm_county(row[county_idx])
            row[desc_idx] = _norm_desc(row[desc_idx])
            rows.append(row)
        return rows, True
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# Notes sheet — the INDICATOR for the context fields + key
# --------------------------------------------------------------------------- #
_write_notes_sheet = ctc.make_notes_writer(
    "Highway Sequence — TSMIS vs TSN: comparison notes",
    (
        "Rows are keyed on Route + County + Postmile. California postmiles are "
        "county-relative (a route restarts at 000.000 in each county it crosses), so "
        "the postmile alone is not unique across a route — County is part of the key.",
        "The postmile carries a glued realignment prefix (\"R000.129\") and/or an equate "
        "suffix (\"050.025E\"); the TSMIS prefix/PM/suffix columns are re-glued to match.",
        "One-sided rows are expected and honest: TSN lists every segment break (including "
        "unnamed ones) and prints equate points as \"EQUATES TO\" annotations, while TSMIS "
        "omits most unnamed breaks and records the equate as an \"END R REALIGNMENT\" row.",
        "Equate points that BOTH systems mark pair up by design and then differ on "
        "purpose: TSN's bare \"EQUATES TO\" annotation carries no feature type, so the "
        "pair surfaces as a Description difference (TSMIS's realignment/route-break "
        "label vs \"EQUATES TO\") and usually an FT difference (TSMIS \"H\" vs TSN "
        "blank). Nearly all FT differences statewide are this class; the few remaining "
        "are genuine feature-type disagreements (H vs I, R vs H).",
        "CONTEXT columns (shown for reference, never counted as a difference): HG (TSMIS "
        "leaves the highway-group blank for whole counties while TSN always fills it); City "
        "(TSN assigns a city code far more aggressively than TSMIS); and Distance To Next "
        "Point (measured to each system's OWN next listed point — since TSN lists more breaks, "
        "its gap is usually smaller, an artifact of listing granularity rather than a real "
        "disagreement). Counting these would bury the substantive differences. FT and "
        "Description (with the TSMIS leading \"<route>/\" prefix stripped) ARE compared.",
    ))


_SCHEMA = CompareSchema(
    report_name=REPORT_NAME,
    header=SHARED_HEADER,
    side_a="TSMIS",
    side_b="TSN",
    id_noun="location",
    id_noun_plural="locations",
    pair_noun="postmile",
    sides_noun="systems",
    data_widths={"County": 8, "PM": 12, "Description": 26},
    cmp_widths={"PM": 12, "Description": 30},
    one_sided_note_extra=" (mostly TSN segment breaks and TSMIS realignment markers)",
    key_field=KEY_FIELD,
    key_normalizer=_key_county_pm,
    context_fields=CONTEXT_FIELDS,
    legend_writer=_write_notes_sheet,
)


# --------------------------------------------------------------------------- #
# adapter surface
# --------------------------------------------------------------------------- #
def suggest_name(tsmis_path):
    return suggest_route_name(tsmis_path, "Highway_Sequence",
                              "TSMIS_vs_TSN_HighwaySequence")


def _load_pair(tsmis_path, tsn_path):
    """(rows_t, rows_n, warnings) for the shared driver — no input warnings here, so
    run_compare uses its () default."""
    rows_t, _ = _load_tsmis(tsmis_path)
    rows_n, _ = _load_tsn(tsn_path)
    return rows_t, rows_n, None


def compare(tsmis_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas", commit_guard=None):
    """Build the Highway Sequence TSMIS-vs-TSN comparison workbook(s). `tsmis_path`
    is the consolidated TSMIS Highway Sequence workbook; `tsn_path` the normalized
    TSN workbook (from consolidate_tsn_highway_sequence)."""
    return ctc.run_files_compare(
        _SCHEMA, tsmis_path, tsn_path, out_path,
        banner="Highway Sequence Comparison — TSMIS vs TSN", has_route=True,
        loader=_load_pair, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        events=events, confirm_overwrite=confirm_overwrite, mode=mode,
        commit_guard=commit_guard)
