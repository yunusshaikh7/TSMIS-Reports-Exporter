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
from collections import Counter
from dataclasses import replace
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
import comparison_contract as cc
import consolidate_tsn_highway_sequence as tsn_hsl
import consolidation_meta
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
    """compare_core.normalize_value plus the OOXML `_xHHHH_` escape decode and
    tab/newline collapse. The TSMIS export pads Description with trailing tabs
    that Excel TRIM does not strip, and its censused `_x000d_` literals are
    encoded CRs (CMP-AUD-197): the Stage-8 oracle xlsx-unescapes every side it
    reads, and the decode is byte-equivalent to openpyxl's — a no-op on the
    escape-free raw-TSN and PDF-render sides."""
    nv = normalize_value(x)
    if not isinstance(nv, str):
        return nv
    return _WS_RE.sub(" ", ctc.decode_ooxml_escapes(nv)).strip()


def _raw_text(x):
    """A cell's lossless source text for identity claims."""
    return "" if x is None else str(x)


def _norm_county(x):
    """Canonical county code. TSMIS writes a trailing period on several codes
    ("LA.", "SB.", "SM.", "SF.", "CC.", "DN.", "ED.", "SD.", "SJ.") that the TSN
    report omits — strip it so the county-relative postmile key matches."""
    s = "" if x is None else str(x).strip().rstrip(".")
    return s.upper()


_DESC_PREFIX_RE = re.compile(r"^(\d{1,3}[A-Z]?)/")
_ROUTE_TOKEN_RE = re.compile(r"(\d{1,3})([A-Za-z]?)")


def _canon_route(tok):
    """A route token in canonical form ("1" -> "001", "14u" -> "014U"), or None
    for a non-route token."""
    m = _ROUTE_TOKEN_RE.fullmatch(("" if tok is None else str(tok)).strip())
    return (m.group(1).zfill(3) + m.group(2).upper()) if m else None


def _desc_plain(x):
    """Description with whitespace runs collapsed to one space — and NOTHING
    else. This is the TSN side (CMP-AUD-204: raw TSN keeps 154 numeric-prefix
    Descriptions — 46 of them deliberately naming a DIFFERENT route — and every
    one is an authoritative source claim; deleting them false-cleaned 81 real
    differences per leg) and both sides of the PDF-vs-Excel self-check."""
    s = _v(x)
    return re.sub(r"\s+", " ", s).strip() if isinstance(s, str) else s


def _desc_tsmis(x, route):
    """The TSMIS Description for the vs-TSN legs: whitespace-collapsed, with the
    separately added leading route label ("001/NB OFF TO DOHENY PK RD") removed
    ONLY when the token names this row's OWN route (CMP-AUD-204). A leading
    cross-route or nested token is genuine source text — TSN prints it too, and
    a pattern-blind strip both hid real differences and fabricated others."""
    s = _desc_plain(x)
    if not isinstance(s, str):
        return s
    m = _DESC_PREFIX_RE.match(s)
    if m and _canon_route(m.group(1)) == _canon_route(route):
        return s[m.end():].lstrip()
    return s


def _glue_pm(prefix, pm, suffix):
    """Re-glue the TSMIS prefix/PM/suffix columns into the canonical postmile the
    TSN side prints ("R" + "000.129" + "" -> "R000.129"; "" + "050.025" + "E"
    -> "050.025E")."""
    p = "" if prefix is None else str(prefix).strip()
    m = "" if pm is None else str(pm).strip()
    s = "" if suffix is None else str(suffix).strip()
    return f"{p}{m}{s}"


# --------------------------------------------------------------------------- #
# physical identity (CMP-AUD-045/199)
# --------------------------------------------------------------------------- #
# The approved HSL identity is (Route, County, complete glued postmile):
# California postmiles are county-relative, and HSL's canonical postmile keeps
# its zero padding, realignment prefix, and — on the vs-TSN and cross-env paths
# — the equate suffix exactly as printed ("R001.000E"). Both sources
# legitimately print rows with NO county (46 raw TSN equate annotations precede
# any county context, CMP-AUD-158) or NO postmile (five TSMIS rows per render),
# so those key under explicit reserved tokens that can never collide with a
# real county/postmile: unknown ownership is disclosed in the key column, never
# dropped, backfilled, or crashed on.
_NO_COUNTY_KEY = "(county not printed)"
_NO_PM_KEY = "(no postmile printed)"


def _physical_pm_key(route, county_raw, pm_glued, claims, source_hint):
    """The HSL PhysicalKey: canonical (route, county, glued postmile) identity
    with the raw prefix/PM/suffix (or the printed glued token) conserved as
    lossless claims. `source_hint` names the failing side in errors."""
    county = _norm_county(county_raw) or _NO_COUNTY_KEY
    pm = pm_glued or _NO_PM_KEY
    try:
        identity = cc.make_physical_identity(
            route, county, pm,
            tuple(cc.RawIdentityClaim(name, value) for name, value in claims),
            f"{route} / {county} / {pm}")
        return cc.physical_key(pm, identity)
    except ValueError as e:
        raise ValueError(f"{source_hint}: could not build the physical "
                         f"identity for route {route!r} PM {pm!r}: {e}")


# --------------------------------------------------------------------------- #
# loaders -> consolidated-shape rows ([route, *SHARED_HEADER])
# --------------------------------------------------------------------------- #
def _tsmis_row(r):
    def at(i):
        return r[i] if i < len(r) else None
    route = _v(at(_TSMIS["route"]))
    county_raw = at(_TSMIS["county"])
    prefix, pm, suffix = at(_TSMIS["prefix"]), at(_TSMIS["pm"]), at(_TSMIS["suffix"])
    key = _physical_pm_key(
        route, county_raw, _glue_pm(prefix, pm, suffix),
        (("route", _raw_text(at(_TSMIS["route"]))),
         ("county", _raw_text(county_raw)),
         ("postmile_prefix", _raw_text(prefix)),
         ("postmile", _raw_text(pm)),
         ("postmile_suffix", _raw_text(suffix))),
        "the consolidated TSMIS workbook")
    return [route,
            _norm_county(county_raw),
            key,
            _v(at(_TSMIS["city"])),
            _v(at(_TSMIS["hg"])),
            _v(at(_TSMIS["ft"])),
            _v(at(_TSMIS["dist"])),
            _desc_tsmis(at(_TSMIS["desc"]), route)]


def _load_tsmis(path):
    return load_consolidated_rows(
        path, TSMIS_SHEET,
        missing_sheet_hint="pick the consolidated TSMIS Highway Sequence workbook.",
        bad_header_msg="isn't a CONSOLIDATED Highway Sequence workbook "
                       "(expected a leading 'Route' column) — consolidate first.",
        row_transform=_tsmis_row)


def _normalization_version(wb):
    """The normalized workbook's declared version (0 for a pre-v4 workbook —
    the rows sheet kept its SHAPE across v4, so the marker sheet is the only
    reliable signal on a bare file; the library path additionally auto-rebuilds
    via report_catalog's normalization_version, D2)."""
    if tsn_hsl.MARKER_SHEET not in wb.sheetnames:
        return 0
    for r in wb[tsn_hsl.MARKER_SHEET].iter_rows(values_only=True):
        if r and str(r[0]).strip() == "Normalization version":
            try:
                return int(r[1])
            except (TypeError, ValueError, IndexError):  # silent-ok: a malformed marker reads as version 0 — the caller then refuses with the rebuild hint (fail-safe)
                return 0
    return 0


def _load_tsn(path):
    """The normalized TSN workbook (consolidate_tsn_highway_sequence output):
    NORMALIZED_HEADER = [Route] + SHARED_HEADER, read positionally. Refuses a
    pre-v4 workbook: it is missing the 46 blank-County equate annotations and
    the printed pointer tokens, and carries an invented join comma
    (CMP-AUD-156/158/159) — silently comparing it would resurrect all three."""
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
        if _normalization_version(wb) < tsn_hsl.NORMALIZATION_VERSION:
            raise ValueError(
                f"{name} was built by an older TSN Highway Sequence converter "
                "(pre-v4: pointer tokens blanked, pre-county equates dropped, "
                "an invented join comma) — rebuild the TSN library and pick "
                "the fresh normalized workbook.")
        it = wb[sn].iter_rows(values_only=True)
        next(it, None)                         # header
        width = len(SHARED_HEADER) + 1         # Route + fields
        pm_idx = 1 + KEY_FIELD
        county_idx = 1 + SHARED_HEADER.index("County")
        desc_idx = 1 + SHARED_HEADER.index("Description")
        rows = []
        for r in it:
            if not row_has_data(r):
                continue
            r = list(r)[:width] + [None] * max(0, width - len(r))
            route = _v(r[0])
            key = _physical_pm_key(
                route, r[county_idx],
                "" if r[pm_idx] is None else str(r[pm_idx]).strip(),
                (("route", _raw_text(r[0])),
                 ("county", _raw_text(r[county_idx])),
                 ("postmile", _raw_text(r[pm_idx]))),
                "the normalized TSN workbook")
            row = [route if i == 0 else key if i == pm_idx
                   else _norm_county(r[i]) if i == county_idx
                   else _desc_plain(r[i]) if i == desc_idx
                   else _v(r[i])
                   for i in range(width)]
            rows.append(row)
        return rows, True
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# Notes sheet — the INDICATOR for the context fields + key
# --------------------------------------------------------------------------- #
_NOTES_TITLE = "Highway Sequence — TSMIS vs TSN: comparison notes"
_NOTES_LINES = (
    "Rows are keyed on Route + County + Postmile. California postmiles are "
    "county-relative (a route restarts at 000.000 in each county it crosses), so "
    "the postmile alone is not unique across a route — County is part of the key.",
    "The postmile carries a glued realignment prefix (\"R000.129\") and/or an equate "
    "suffix (\"050.025E\"); the TSMIS prefix/PM/suffix columns are re-glued to match.",
    "A handful of rows print with NO county (46 statewide TSN \"EQUATES TO\" "
    "annotations that appear before the route's first county-bearing row — TSN's own "
    "cover warns equate ownership may be wrong) or NO postmile (five TSMIS rows). "
    "They key under the explicit \"(county not printed)\" / \"(no postmile printed)\" "
    "markers and surface honestly, usually one-sided — never dropped or backfilled.",
    "One-sided rows are expected and honest: TSN lists every segment break (including "
    "unnamed ones) and prints equate points as \"EQUATES TO\" annotations, while TSMIS "
    "omits most unnamed breaks and records the equate as an \"END R REALIGNMENT\" row.",
    "Equate points that BOTH systems mark pair up by design and then differ on "
    "purpose: TSN's bare \"EQUATES TO\" annotation carries no feature type, so the "
    "pair surfaces as a Description difference (TSMIS's realignment/route-break "
    "label vs \"EQUATES TO\") and usually an FT difference (TSMIS \"H\" vs TSN "
    "blank). Nearly all FT differences statewide are this class; the few remaining "
    "are genuine feature-type disagreements (H vs I, R vs H).",
    "Descriptions: the TSMIS export prepends the row's own route as a label "
    "(\"001/NB OFF TO DOHENY PK RD\") — that label alone is stripped before "
    "comparing. TSN text is compared VERBATIM: TSN's numeric route prefixes "
    "(including ones naming a DIFFERENT route) are authoritative source claims, so "
    "TSMIS \"103 SEP 53-145\" vs TSN \"1/103 SEP 53-145\" is a REAL difference. A "
    "leading cross-route token on the TSMIS side is likewise kept.",
    "CONTEXT columns (shown for reference, never counted as a difference): HG (TSMIS "
    "leaves the highway-group blank for whole counties while TSN always fills it); City "
    "(TSN assigns a city code far more aggressively than TSMIS); and Distance To Next "
    "Point (measured to each system's OWN next listed point — since TSN lists more breaks, "
    "its gap is usually smaller; TSN also prints pointer markers \"*P*\" and "
    "\"-------->\" there, conserved verbatim). Counting these would bury the "
    "substantive differences. FT and Description ARE compared.",
)
_write_notes_sheet = ctc.make_notes_writer(_NOTES_TITLE, _NOTES_LINES)


def claims_notes(claims, side_label="TSN"):
    """Human-readable exposure lines for the Notes sheet (CMP-AUD-155): the
    print identity the 12 districts agreed on, the per-route printed
    directions, and the source's own reliability policy."""
    if not claims:
        return [f"{side_label} print: no source-claims record beside this "
                "normalized workbook — rebuild the TSN library to capture the "
                "print identity, per-route directions, and reliability policy."]
    docs = claims.get("documents") or []
    lines = [f"{side_label} print identity: {claims.get('report_id')} "
             f"{claims.get('report_title')} · report {claims.get('report_date')} "
             f"· reference {claims.get('reference_date')} · "
             f"{len(docs)} district print(s)."]
    directions = Counter()
    for d in docs:
        directions.update((d.get("directions") or {}).values())
    if directions:
        summary = " · ".join(f"{k} ×{v}" for k, v in sorted(
            directions.items(), key=lambda kv: (-kv[1], kv[0])))
        lines.append(f"Printed route directions (per district group): {summary}.")
    lines.append(
        "Every district cover carries TSN's own reliability NOTE: landmark "
        "descriptions at Route Breaks/Equates (and possibly county/district "
        "boundaries) may be wrong. Equate rows and blank-county annotations are "
        "therefore disclosed as printed, never repaired.")
    return lines


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
    context_fields=CONTEXT_FIELDS,
    legend_writer=_write_notes_sheet,
)


def _schema_with_claims(tsn_path, schema=None, title=_NOTES_TITLE,
                        lines=_NOTES_LINES):
    """The per-run schema: the flavor's static Notes plus the normalized
    workbook's persisted source claims (read from its sidecar — absent claims
    get an explicit rebuild hint instead of silence). CMP-AUD-155."""
    base = schema if schema is not None else _SCHEMA
    claim_lines = claims_notes(
        consolidation_meta.read_extra(Path(tsn_path), "tsn_source_claims"))
    return replace(base, legend_writer=ctc.make_notes_writer(
        title, tuple(lines) + tuple(claim_lines)))


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
        _schema_with_claims(tsn_path), tsmis_path, tsn_path, out_path,
        banner="Highway Sequence Comparison — TSMIS vs TSN", has_route=True,
        loader=_load_pair, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        events=events, confirm_overwrite=confirm_overwrite, mode=mode,
        commit_guard=commit_guard)
