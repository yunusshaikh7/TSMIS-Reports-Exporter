"""Clean Road Files — the SITE export's column contract (v0.48.0).

The TSMIS site's three "Clean Road File" reports (`clean_highway.js` /
`clean_intersection.js` / `clean_ramp.js`, live since the 9.1 dev capture) are
flat, one-row-per-record replicas of the legacy TASAS clean-road files. Each
report has two editions the app exports: the Excel file (`*_exportToExcel`, one
sheet, the full legacy header) and the print (`*_printAll`, landscape,
scale-to-fit, ONLY the columns the site has a source for). This module is the
one home for what both editions look like, so the consolidators, the print
reader and the comparisons can't drift apart:

  * the exact header of each Excel export (Highway / Intersection = the TSN
    extract's header verbatim; Ramp = TSN's 32 columns behind two site-only
    ones), and the TSN extract's own header for the vs-TSN side;
  * the columns the site registry gives NO source (`src: null` in the 9.1
    capture) — present in the Excel and always blank there, never printed;
  * how the print labels a column (`printed_label`, the site's own `hdrHtml`
    rule), so the print reader maps every printed column back to its key and a
    print with an unknown column refuses instead of guessing.

Censused on the owner's statewide 2026-10-02 SSOR-prod pull
(`ground-truth/All Reports 10.2`): 252 / 217 / 126 routes, one header per
report in every file, 51,735 / 16,461 / 15,214 rows, and the unsourced sets
below blank on every row. Kept import-light (no openpyxl / PDF libraries).
"""
from dataclasses import dataclass

import clean_highway_columns as chc

TSN_RAW_SHEET = chc.TSN_RAW_SHEET            # "Sheet 1" — all three TSN extracts

INTERSECTION_HEADER = (
    "INX_CONNECTION_ID", "INX_PLACEMENT_ID", "INX_MAIN_SEQ_ID", "INX_CROSS_SEQ_ID",
    "INX_DESIGN_CODE", "INX_LIGHTED_BEGIN_DATE", "INX_LIGHTED_IND",
    "INX_MAIN_BEGIN_DATE", "INX_MAIN_SIGNAL_MAST_ARM_IND",
    "INX_MAIN_LEFT_CHANNEL_CODE", "INX_MAIN_RIGHT_CHANNEL_CODE",
    "INX_MAIN_FLOW_CODE", "INX_CROSS_BEGIN_DATE", "INX_CROSS_SIGNAL_MAST_ARM_IND",
    "INX_CROSS_LEFT_CHANNEL_CODE", "INX_CROSS_RIGHT_CHANNEL_CODE",
    "INX_CROSS_FLOW_CODE", "INX_CREATE_USER_NAME", "INX_CREATE_DATE",
    "INX_BEGIN_DATE", "INX_END_DATE", "INX_RECORD_DATE", "INX_CROSS_PLACEMENT_ID",
    "INX_INTERSECTION_NAME", "INX_DESIGN_DATE", "INX_CONTROL_DATE",
    "INX_CONTROL_CODE", "INX_MAIN_LANES_AMT", "INX_MAIN_OVERRIDE_LENGTH_AMT",
    "INX_CROSS_LANES_AMT", "INX_CROSS_OVERRIDE_LENGTH_AMT", "INX_ROUTE_NAME",
    "INX_BEGIN_PM_AMT", "INX_END_PM_AMT", "INX_DISTRICT_CODE", "INX_COUNTY_CODE",
    "INX_PM_PREFIX_CODE", "INX_PM_SUFFIX_CODE", "INX_ROUTE_SUFFIX_CODE",
    "INX_SEG_ORDER_ID", "INX_HIGHWAY_GROUP", "INX_CITY_CODE",
    "INX_POPULATION_GROUP", "INX_MAINLINE_ADT", "INX_XSTREET_ADT", "INX_LSC_DATE",
    "INX_UPDATE_USER_NAME", "INX_UPDATE_DATE", "INX_X_ROUTE_NAME",
    "INX_X_PM_PREFIX_CODE", "INX_X_POSTMILE_AMT", "INX_X_PM_SUFFIX_CODE",
    "INX_X_ROUTE_SUFFIX_CODE", "INX_X_SEG_ORDER_ID", "INX_EXTRACT_DATE",
)

RAMP_TSN_HEADER = (
    "RAM_ROUTE_ID", "RAM_NETWORK_ID", "RAM_PRIMARY_DIRECTION_CODE",
    "RAM_DESIGN_CODE", "RAM_DESIGN_DESC", "RAM_PLACEMENT_ID", "RAM_ELEMENT_ID",
    "RAM_BEGIN_OFFSET_AMT", "RAM_BEGIN_DATE", "RAM_CREATE_USER_NAME",
    "RAM_CREATE_DATE", "RAM_DISTRICT_CODE", "RAM_COUNTY_CODE", "RAM_ROUTE_NAME",
    "RAM_ROUTE_SUFFIX_CODE", "RAM_PM_PREFIX_CODE", "RAM_PM_LOC_AMT",
    "RAM_PM_SUFFIX_CODE", "RAM_SEG_ORDER_ID", "RAM_ON_OFF_CODE", "RAM_AREA_4_IND",
    "RAM_DESCRIPTION", "RAM_CITY_CODE", "RAM_END_DATE", "RAM_ADT", "RAM_POP_GROUP",
    "RAM_HIGHWAY_GROUP", "RAM_CHANGE_DATE", "RAM_UPDATE_USER_NAME",
    "RAM_UPDATE_DATE", "RAM_CONNECTION_ID", "RAM_EXTRACT_DATE",
)
# The site's Ramp file leads with two columns the TSN extract doesn't carry.
RAMP_SITE_ONLY = ("RAM_HPMS_ID", "RAM_RAMP_ROUTE_NAME")
RAMP_HEADER = RAMP_SITE_ONLY + RAMP_TSN_HEADER

# The columns each site registry gives no source (`src: null`, 9.1 capture):
# present in the Excel file, blank on every row, absent from the print.
_HIGHWAY_UNSOURCED = (
    "THY_ID", "THY_ELEMENT_ID", "THY_BEGIN_DATE", "THY_END_DATE",
    "THY_CREATE_DATE", "THY_CREATE_USER_NAME", "THY_LT_SIG_CHG_IND",
    "THY_MEDIAN_SIG_CHG_IND", "THY_RT_SIG_CHG_IND", "THY_ACCESS_SIG_CHG_IND",
    "THY_PROFILE_CODE", "THY_ADT_AMT", "THY_CHANGE_PER_MILE_AMT",
    "THY_POPULATION_GROUP_CODE", "THY_UPDATE_DATE", "THY_UPDATE_USER_NAME",
    "THY_MAINT_SVC_LVL_CODE", "THY_FEDERAL_AID_CODE", "THY_FA_ROUTE_PREFIX_CODE",
    "THY_FA_ROUTE_NAME", "THY_NATIONAL_LANDS_CODE", "THY_SCENIC_FREEWAY_CODE",
)
_INTERSECTION_UNSOURCED = (
    "INX_PLACEMENT_ID", "INX_CREATE_USER_NAME", "INX_CREATE_DATE", "INX_END_DATE",
    "INX_CROSS_PLACEMENT_ID", "INX_MAINLINE_ADT", "INX_XSTREET_ADT",
    "INX_LSC_DATE", "INX_UPDATE_USER_NAME", "INX_UPDATE_DATE",
)
_RAMP_UNSOURCED = (
    "RAM_HPMS_ID", "RAM_RAMP_ROUTE_NAME", "RAM_ROUTE_ID", "RAM_PLACEMENT_ID",
    "RAM_ELEMENT_ID", "RAM_BEGIN_OFFSET_AMT", "RAM_CREATE_USER_NAME",
    "RAM_CREATE_DATE", "RAM_ADT", "RAM_CHANGE_DATE", "RAM_UPDATE_USER_NAME",
    "RAM_UPDATE_DATE", "RAM_CONNECTION_ID",
)


@dataclass(frozen=True)
class CleanRoadSpec:
    """One Clean Road report's two site editions and its TSN counterpart.

    `key` / `pdf_key` are the Excel / print export subdirs (the per-route files
    are `<key>_route_<ROUTE>.xlsx` / `.pdf`); `sheet` is the Excel file's one
    sheet; `header` its exact columns; `tsn_header` the TSN extract's exact
    columns (a strict suffix of `header` for Ramp, equal otherwise). The
    location columns name the record's physical identity on both sides."""
    key: str
    pdf_key: str
    label: str
    noun: str
    noun_plural: str
    prefix: str
    sheet: str
    header: tuple
    tsn_header: tuple
    tsn_label: str
    normalized_sheet: str
    unsourced: tuple
    route_col: str
    suffix_col: str
    county_col: str
    pm_prefix_col: str
    pm_col: str
    pm_suffix_col: str

    @property
    def site_only(self):
        """The columns the site file carries that the TSN extract doesn't."""
        return tuple(c for c in self.header if c not in self.tsn_header)


HIGHWAY = CleanRoadSpec(
    key="clean_highway", pdf_key="clean_highway_pdf",
    label="Clean Road Highway", noun="segment", noun_plural="segments",
    prefix="THY_", sheet="Clean Road Highway",
    header=tuple(chc.HEADER), tsn_header=tuple(chc.HEADER),
    tsn_label="CA HIGHWAYS", normalized_sheet=chc.NORMALIZED_SHEET,
    unsourced=_HIGHWAY_UNSOURCED,
    route_col="THY_ROUTE_NAME", suffix_col="THY_ROUTE_SUFFIX_CODE",
    county_col="THY_COUNTY_CODE", pm_prefix_col="THY_PM_PREFIX_CODE",
    pm_col="THY_BEGIN_PM_AMT", pm_suffix_col="THY_PM_SUFFIX_CODE")

INTERSECTION = CleanRoadSpec(
    key="clean_intersection", pdf_key="clean_intersection_pdf",
    label="Clean Road Intersection", noun="intersection",
    noun_plural="intersections", prefix="INX_", sheet="Clean Road Intersection",
    header=INTERSECTION_HEADER, tsn_header=INTERSECTION_HEADER,
    tsn_label="CA INTERSECTIONS",
    normalized_sheet="Clean Road Intersection (TSN)",
    unsourced=_INTERSECTION_UNSOURCED,
    route_col="INX_ROUTE_NAME", suffix_col="INX_ROUTE_SUFFIX_CODE",
    county_col="INX_COUNTY_CODE", pm_prefix_col="INX_PM_PREFIX_CODE",
    pm_col="INX_BEGIN_PM_AMT", pm_suffix_col="INX_PM_SUFFIX_CODE")

RAMP = CleanRoadSpec(
    key="clean_ramp", pdf_key="clean_ramp_pdf",
    label="Clean Road Ramp", noun="ramp", noun_plural="ramps",
    prefix="RAM_", sheet="Clean Road Ramp",
    header=RAMP_HEADER, tsn_header=RAMP_TSN_HEADER,
    tsn_label="CA RAMPS", normalized_sheet="Clean Road Ramp (TSN)",
    unsourced=_RAMP_UNSOURCED,
    route_col="RAM_ROUTE_NAME", suffix_col="RAM_ROUTE_SUFFIX_CODE",
    county_col="RAM_COUNTY_CODE", pm_prefix_col="RAM_PM_PREFIX_CODE",
    pm_col="RAM_PM_LOC_AMT", pm_suffix_col="RAM_PM_SUFFIX_CODE")

SPECS = (HIGHWAY, INTERSECTION, RAMP)
BY_KEY = {s.key: s for s in SPECS}
BY_PDF_KEY = {s.pdf_key: s for s in SPECS}


def printed_label(key, prefix):
    """How the site's print labels column `key` — the `hdrHtml` rule shared by
    all three `clean_*.js` renderers: drop the table prefix, abbreviate the
    first PREFIX/SUFFIX to PFX/SFX, then split the underscore tokens into two
    lines at the cut that best balances their lengths (first cut wins a tie).
    Returned with the line break as '\\n' (a one-token name has one line)."""
    name = key[len(prefix):] if key.startswith(prefix) else key
    name = name.replace("PREFIX", "PFX", 1).replace("SUFFIX", "SFX", 1)
    tokens = name.split("_")
    if len(tokens) < 2:
        return name
    best_i, best = 1, None
    for i in range(1, len(tokens)):
        diff = abs(len("_".join(tokens[:i])) - len("_".join(tokens[i:])))
        if best is None or diff < best:
            best, best_i = diff, i
    return "_".join(tokens[:best_i]) + "\n" + "_".join(tokens[best_i:])


def printed_columns(spec):
    """{printed label: column key} for every column the site could print —
    the reverse of `printed_label`, so the print reader names each printed
    column. Asserted collision-free below."""
    return {printed_label(c, spec.prefix): c for c in spec.header}


for _spec in SPECS:
    assert len(set(_spec.header)) == len(_spec.header), f"{_spec.key}: duplicate column"
    assert set(_spec.unsourced) <= set(_spec.header), f"{_spec.key}: unsourced not in header"
    assert set(_spec.tsn_header) <= set(_spec.header), f"{_spec.key}: TSN column missing"
    assert len(printed_columns(_spec)) == len(_spec.header), \
        f"{_spec.key}: two columns print the same label"
    for _c in (_spec.route_col, _spec.suffix_col, _spec.county_col,
               _spec.pm_prefix_col, _spec.pm_col, _spec.pm_suffix_col):
        assert _c in _spec.tsn_header, f"{_spec.key}: location column {_c} not shared"
assert HIGHWAY.header == tuple(chc.HEADER) and len(HIGHWAY.unsourced) == 22
assert len(INTERSECTION.header) == 55 and len(INTERSECTION.unsourced) == 10
assert len(RAMP.header) == 34 and RAMP.site_only == RAMP_SITE_ONLY
