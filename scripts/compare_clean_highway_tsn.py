"""Build the ArcGIS-vs-TSN Clean Road CA HIGHWAYS discrepancy workbook.

Both sides carry the SAME 74-column `THY_*` shape: side A is OUR build from the
ArcGIS layer library (`consolidate_clean_highway` — role-marked with the
`ArcGIS Build` sheet), side B is the vendor's TSN `CA HIGHWAYS` extract (the
raw statewide `Sheet 1`, or the TSN library's normalized copy). One shared
projection loads either side; the role gates keep the sides honest (the ArcGIS
side REQUIRES the build marker, the TSN side REJECTS it), so an ArcGIS build
can never stand in for TSN or vice versa.

Row identity — the roadbed-aware physical span key (the Highway Detail canon
extended with the county, both sides carrying it natively):

    Route (name + suffix) · County · PM prefix · begin PM (decimal-canonical)
    · roadbed (the R/L/X PM suffix)

A row's END PM is deliberately NOT key material: where the two systems cut a
stretch differently, keying on the begin pairs the rows and surfaces the end
as a field difference instead of fabricating two one-sided rows.

Owner decisions (2026-07-22) carried here: every one of the 74 columns is
PRESENT; the columns with no TSMIS ArcGIS source (and TSN's own bookkeeping)
are CONTEXT — shown with TSN's value beside our empty cell, never counted as a
difference — and the Notes sheet indexes EVERY column back to its source layer
(the audit record). Value normalizations (dates to ISO, amounts to canonical
decimals, landmark edge trim) are format-only and documented in the Notes.

Console-free; engine in compare_core via compare_tsn_common.run_files_compare
(mode="both" writes the live-formulas workbook plus its values twin).
"""
import re
from datetime import date, datetime
from pathlib import Path

try:
    from openpyxl import load_workbook
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import clean_highway_columns as chc
import compare_tsn_common as ctc
import comparison_contract as cc
from compare_core import CompareSchema
from paths import today_str

REPORT_NAME = "Clean Road Highway"
ARC_SHEET = chc.ARC_SHEET
TSN_SHEET = chc.TSN_RAW_SHEET
NORMALIZED_SHEET = chc.NORMALIZED_SHEET
# CMP-AUD-037 discipline from day one: the library's normalized workbook is
# stamped with this version (tsn_load_clean_road mirrors it; the catalog's
# clean_highway normalization_version mirrors both).
NORMALIZATION_VERSION = 1
_NORMALIZED_SIDECARS = ()          # the normalized copy is the verbatim 74 cols

TSN_RAW_HEADER = tuple(chc.HEADER)
SHARED_HEADER = list(chc.HEADER)
KEY = "THY_BEGIN_PM_AMT"
KEY_FIELD = SHARED_HEADER.index(KEY)
CONTEXT_FIELDS = chc.CONTEXT_COLUMNS
DATE_FIELDS = ("THY_BEGIN_DATE", "THY_END_DATE", "THY_CREATE_DATE",
               "THY_LEFT_ROAD_EFF_DATE", "THY_MEDIAN_EFF_DATE",
               "THY_RIGHT_ROAD_EFF_DATE", "THY_ACCESS_EFF_DATE",
               "THY_LAST_SIG_CHG_DATE", "THY_RECORD_DATE", "THY_UPDATE_DATE",
               "THY_EXTRACT_DATE")
# Columns compared as canonical decimal amounts (float/int/text spellings of
# one number are the same value).
_AMOUNT_FIELDS = frozenset({
    "THY_BEGIN_OFFSET_AMT", "THY_END_OFFSET_AMT", "THY_SEG_ORDER_ID",
    "THY_END_PM_AMT", "THY_LENGTH_MILES_AMT", "THY_LT_LANES_AMT",
    "THY_LT_O_SHD_TOT_WIDTH_AMT", "THY_LT_O_SHD_TRT_WIDTH_AMT",
    "THY_LT_TRAV_WAY_WIDTH_AMT", "THY_LT_I_SHD_TOT_WIDTH_AMT",
    "THY_LT_I_SHD_TRT_WIDTH_AMT", "THY_MEDIAN_WIDTH_AMT",
    "THY_RT_LANES_AMT", "THY_RT_I_SHD_TOT_WIDTH_AMT",
    "THY_RT_I_SHD_TRT_WIDTH_AMT", "THY_RT_TRAV_WAY_WIDTH_AMT",
    "THY_RT_O_SHD_TOT_WIDTH_AMT", "THY_RT_O_SHD_TRT_WIDTH_AMT",
    "THY_DESIGN_SPEED_AMT", "THY_ADT_AMT", "THY_CHANGE_PER_MILE_AMT",
    "THY_TOLL_FOREST_CODE", "THY_CURB_LANDSCAPE_CODE",
    "THY_MAINT_SVC_LVL_CODE", "THY_NATIONAL_LANDS_CODE",
    "THY_SCENIC_FREEWAY_CODE",
})

_write_notes_sheet = ctc.make_notes_writer(
    "Clean Road Highway — ArcGIS build vs TSN: comparison notes",
    (
        "Side A is OUR CA HIGHWAYS table, built from the owner's ArcGIS "
        "per-layer exports (arcgis_layers/) by the county+PM overlay "
        "consolidator; side B is the vendor's TSN CA HIGHWAYS extract. Both "
        "carry the same 74 THY_* columns.",
        "Rows are keyed on Route + County + PM prefix + begin postmile "
        "(decimal-canonical) + roadbed (the R/L/X PM suffix). The END "
        "postmile is deliberately not key material — where the two systems "
        "cut a stretch differently the rows still pair, and the end shows as "
        "a field difference instead of two one-sided rows.",
        "Dates are compared as ISO dates (format never counts); amount "
        "columns compare as canonical numbers ('02' = '2', '9.60' = '9.6'); "
        "the landmark text is edge-trimmed on both sides (the TSN extract "
        "pads with trailing blanks). THY_CHANGE_PER_MILE_AMT compares at 3 "
        "decimals: the extract's own per-row slope arithmetic wobbles in the "
        "4th decimal along one constant profile, and a real profile change "
        "moves it by whole units.",
        "CONTEXT columns (shown for reference, never counted as a "
        "difference): the TSN bookkeeping columns (id/element/lifecycle/"
        "create/update), the TASAS change-tracking flags, the columns with "
        "no TSMIS ArcGIS source (maintenance service level, the federal-aid "
        "trio, national lands, scenic freeway, city code — the City layer "
        "carries names, not TASAS city codes), THY_EXTRACT_DATE (ours is "
        "the build's as-of date by definition), the two synthesized OFFSET "
        "columns (our PM-continued cumulative diverges from TSN's own line "
        "wherever the two systems cut a stretch differently — that sliver "
        "already shows once, honestly, on END PM/LENGTH), and the ADT "
        "profile trio (sourced from Traffic Volume Segments, but TSN's "
        "exact per-row interpolation model — cross-county profile "
        "continuations, the vintage choice at overlaps — is not yet pinned; "
        "counting it would tally model noise, not data differences). Owner "
        "decision 2026-07-22: they stay PRESENT — both sides' values "
        "visible — so nothing is silently dropped.",
        "One-sided rows are stretches one side carries at a physical "
        "location (route + county + prefix + begin PM + roadbed) the other "
        "doesn't — segmentation differences show up here.",
        "Column provenance (the audit index — which ArcGIS layer each column "
        "is built from; the built workbook's Provenance sheet adds each "
        "layer's FeatureServer source):",
    ) + tuple("    " + chc.provenance_line(name) for name in chc.HEADER))

_SCHEMA = CompareSchema(
    report_name=REPORT_NAME,
    header=SHARED_HEADER,
    side_a="ArcGIS",
    side_b="TSN",
    id_noun="segment",
    id_noun_plural="segments",
    pair_noun="postmile",
    sides_noun="systems",
    date_fields=DATE_FIELDS,
    data_widths={"THY_LANDMARK_SHORT_DESC": 26, "THY_BREAK_DESC": 10},
    cmp_widths={"THY_LANDMARK_SHORT_DESC": 30},
    one_sided_note_extra=(" (stretches one side carries at a physical "
                          "location the other doesn't)"),
    key_field=KEY_FIELD,
    context_fields=CONTEXT_FIELDS,
    legend_writer=_write_notes_sheet,
)

_ROUTE_RE = re.compile(r"^(\d+)([A-Z]?)$")


def _s(v):
    return "" if v is None else str(v).strip()


def _norm_route(name, suffix):
    s = _s(name)
    if s.endswith(".0"):
        s = s[:-2]
    m = _ROUTE_RE.match(s.upper())
    base = f"{int(m.group(1)):03d}{m.group(2)}" if m else s.upper()
    return base + _s(suffix).upper()


def _norm_date(v):
    """Both sides to YYYY-MM-DD: openpyxl datetime/date cells and the text
    forms iso_date already handles."""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return ctc.iso_date(v)


def _norm_amount(v):
    """One canonical decimal text for a numeric cell in any spelling: 2 / 2.0
    / '02' / '2.40' -> '2' / '2' / '2' / '2.4'. Non-numeric values pass
    through stripped, so nothing is invented."""
    s = _s(v)
    if not s:
        return ""
    try:
        f = float(s)
    except ValueError:
        return s
    if f != f or f in (float("inf"), float("-inf")):
        return s
    text = f"{f:.10f}".rstrip("0").rstrip(".")
    if text in ("-0", ""):
        text = "0"
    return text


def _norm_cell(field, v):
    if field in DATE_FIELDS:
        return _norm_date(v)
    if field == "THY_CHANGE_PER_MILE_AMT":
        # The extract's own per-row slope arithmetic wobbles in the 4th
        # decimal (998.4636…998.4641 along ONE constant profile on route
        # 001); a real profile change moves this by whole units. Compared at
        # 3 decimals so the wobble never buries a real difference — the
        # Notes name the rule.
        s = _norm_amount(v)
        try:
            return _norm_amount(round(float(s), 3)) if s else s
        except ValueError:
            return s
    if field in _AMOUNT_FIELDS:
        return _norm_amount(v)
    return _s(v)


def _physical_span_key(route, county, prefix, begin_raw, roadbed, source_hint):
    """The typed physical identity of one clean-road span row (D4): route +
    county + prefix + decimal-canonical begin PM + roadbed. The displayed key
    text carries the same components so the Comparison sheet reads naturally."""
    if not county:
        raise ValueError(
            f"Clean Road Highway row (route {route}, PM {_s(begin_raw)}) has "
            f"no usable county in {source_hint} — cannot key it to a physical "
            "location")
    numeric = ctc.decimal_pm(begin_raw)
    component = f"{prefix}{numeric}{roadbed}"
    identity = cc.make_physical_identity(
        route, county, component,
        (cc.RawIdentityClaim("route", route),
         cc.RawIdentityClaim("county", county),
         cc.RawIdentityClaim("postmile_prefix", prefix),
         cc.RawIdentityClaim("postmile", _s(begin_raw)),
         cc.RawIdentityClaim("roadbed", roadbed)),
        f"{route} / {county} / {component}")
    return cc.physical_key(component, identity)


def _thy_row(vals, source_hint):
    """Project one 74-cell THY-shaped row (either side) onto
    [route, *SHARED_HEADER] with the begin-PM cell as the physical key."""
    h = {name: i for i, name in enumerate(chc.HEADER)}

    def g(name):
        i = h[name]
        return vals[i] if i < len(vals) else None

    route = _norm_route(g("THY_ROUTE_NAME"), g("THY_ROUTE_SUFFIX_CODE"))
    county = _s(g("THY_COUNTY_CODE")).upper()
    prefix = _s(g("THY_PM_PREFIX_CODE")).upper()
    roadbed = _s(g("THY_PM_SUFFIX_CODE")).upper()
    key = _physical_span_key(route, county, prefix, g("THY_BEGIN_PM_AMT"),
                             roadbed, source_hint)
    out = [route]
    for name in SHARED_HEADER:
        if name == KEY:
            out.append(key)
        else:
            out.append(_norm_cell(name, g(name)))
    return out


# --------------------------------------------------------------------------- #
# role gates (the CMP-AUD-066 pattern): the ArcGIS side must BE our build;
# the TSN side must NOT be.
# --------------------------------------------------------------------------- #
def _arc_marker_present(wb):
    return chc.ARC_MARKER_SHEET in wb.sheetnames


def _load_arc(path):
    """Side A: OUR ArcGIS-built workbook — the exact 74-column sheet plus the
    build marker (an unmarked THY-shaped workbook could be the TSN extract
    itself, and comparing TSN against TSN would certify a match no ArcGIS
    data ever entered)."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if not _arc_marker_present(wb):
            raise ValueError(
                f"{name} does not carry the '{chc.ARC_MARKER_SHEET}' marker, "
                "so it cannot stand as the ArcGIS side — build the Clean Road "
                "Highway workbook from the ArcGIS tab and pick that file.")
        if ARC_SHEET not in wb.sheetnames:
            raise ValueError(f"{name} has no '{ARC_SHEET}' sheet — rebuild "
                             "the Clean Road Highway workbook.")
        it = wb[ARC_SHEET].iter_rows(values_only=True)
        header = [_s(c) for c in (next(it, None) or ())]
        if header != chc.HEADER:
            raise ValueError(
                f"{name} does not carry the exact 74-column THY header — "
                "rebuild the Clean Road Highway workbook with this version.")
        return [_thy_row(list(r), f"{name} ({ARC_SHEET})")
                for r in it if ctc.row_has_data(r)]
    finally:
        wb.close()


def _load_tsn(path):
    """Side B: the TSN CA HIGHWAYS extract — the raw statewide `Sheet 1`, or
    the TSN library's normalized copy (marker-gated). A workbook carrying the
    ArcGIS build marker is refused — it is our side, not TSN's."""
    name = Path(path).name
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Could not open {name}: {type(e).__name__}: {e}")
    try:
        if _arc_marker_present(wb):
            raise ValueError(
                f"{name} is an ArcGIS-built Clean Road workbook (it carries "
                f"the '{chc.ARC_MARKER_SHEET}' marker), so it cannot stand as "
                "the TSN side — pick the TSN CA HIGHWAYS extract or the TSN "
                "library's normalized copy.")
        if NORMALIZED_SHEET in wb.sheetnames:
            it = wb[NORMALIZED_SHEET].iter_rows(values_only=True)
            header = [_s(c) for c in (next(it, None) or ())]
            ctc.require_shared_header_prefix(
                header, chc.HEADER, _NORMALIZED_SIDECARS, name, REPORT_NAME)
            ctc.require_current_normalization(
                wb, name, NORMALIZATION_VERSION,
                "pre-v1: no in-workbook normalization marker")
            return [_thy_row(list(r), f"{name} ({NORMALIZED_SHEET})")
                    for r in it if ctc.row_has_data(r)]
    finally:
        wb.close()
    return tsn_rows_from_raw(path)


def tsn_rows_from_raw(path):
    """Every row from the exact raw TSN statewide workbook."""
    with ctc.exact_raw_rows(
            path, TSN_SHEET, TSN_RAW_HEADER, REPORT_NAME,
            required_nonblank=("THY_COUNTY_CODE", "THY_ROUTE_NAME",
                               "THY_BEGIN_PM_AMT")) as (_header, rows_in):
        return [_thy_row(list(r), f"{Path(path).name} ({TSN_SHEET})")
                for r in rows_in]


# --------------------------------------------------------------------------- #
# adapter surface
# --------------------------------------------------------------------------- #
def suggest_name(_arc_path=None):
    return f"ArcGIS_vs_TSN_CleanRoadHighway_Comparison {today_str()}.xlsx"


def _load_pair(arc_path, tsn_path):
    rows_a = _load_arc(arc_path)
    rows_b = _load_tsn(tsn_path)
    return rows_a, rows_b, None


def compare(arc_path, tsn_path, out_path, events=None, confirm_overwrite=None,
            mode="formulas", commit_guard=None):
    """Build the Clean Road Highway ArcGIS-vs-TSN comparison workbook(s).
    `arc_path` is the ArcGIS-built workbook; `tsn_path` the TSN extract (raw
    or normalized). Returns a ConsolidateResult."""
    return ctc.run_files_compare(
        _SCHEMA, arc_path, tsn_path, out_path,
        banner="Clean Road Highway Comparison — ArcGIS build vs TSN",
        has_route=True, loader=_load_pair, deps_ok=_DEPS_OK,
        deps_msg="Required components are missing (openpyxl).",
        side_a="ArcGIS", side_b="TSN",
        events=events, confirm_overwrite=confirm_overwrite, mode=mode,
        commit_guard=commit_guard)
