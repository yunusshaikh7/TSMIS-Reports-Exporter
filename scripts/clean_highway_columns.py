"""Clean Road CA HIGHWAYS — the shared column contract (v0.29.0).

One home for the 74 `THY_*` column names (order = the TSN `CA HIGHWAYS`
extract, verbatim), the sheet/marker names both sides use, and the per-column
PROVENANCE tiers — which ArcGIS layer each column is built from, the audit
record the owner asked for. The consolidator (`consolidate_clean_highway`),
the TSN normalizer (`tsn_load_clean_road`), and the comparator
(`compare_clean_highway_tsn`) all read these; none redefines them.
"""

# The ArcGIS-built workbook's data sheet + its role marker sheet, and the TSN
# sides' sheet names.
ARC_SHEET = "Clean Road Highway"
ARC_MARKER_SHEET = "ArcGIS Build"
TSN_RAW_SHEET = "Sheet 1"
NORMALIZED_SHEET = "Clean Road Highway (TSN)"

HEADER = [
    "THY_ID", "THY_ELEMENT_ID", "THY_BEGIN_OFFSET_AMT", "THY_END_OFFSET_AMT",
    "THY_BEGIN_DATE", "THY_END_DATE", "THY_CREATE_DATE", "THY_CREATE_USER_NAME",
    "THY_SEG_ORDER_ID", "THY_DISTRICT_CODE", "THY_COUNTY_CODE", "THY_ROUTE_NAME",
    "THY_ROUTE_SUFFIX_CODE", "THY_PM_PREFIX_CODE", "THY_BEGIN_PM_AMT",
    "THY_END_PM_AMT", "THY_PM_SUFFIX_CODE", "THY_LENGTH_MILES_AMT",
    "THY_LEFT_ROAD_EFF_DATE", "THY_LT_SURF_TYPE_CODE", "THY_LT_LANES_AMT",
    "THY_LT_SPEC_FEATURES_CODE", "THY_LT_O_SHD_TOT_WIDTH_AMT",
    "THY_LT_O_SHD_TRT_WIDTH_AMT", "THY_LT_TRAV_WAY_WIDTH_AMT",
    "THY_LT_I_SHD_TOT_WIDTH_AMT", "THY_LT_I_SHD_TRT_WIDTH_AMT",
    "THY_LT_SIG_CHG_IND", "THY_MEDIAN_EFF_DATE", "THY_MEDIAN_TYPE_CODE",
    "THY_CURB_LANDSCAPE_CODE", "THY_MEDIAN_BARRIER_CODE", "THY_MEDIAN_WIDTH_AMT",
    "THY_MEDIAN_WIDTH_VAR_CODE", "THY_MEDIAN_SIG_CHG_IND",
    "THY_RIGHT_ROAD_EFF_DATE", "THY_RT_SURF_TYPE_CODE", "THY_RT_LANES_AMT",
    "THY_RT_SPEC_FEATURES_CODE", "THY_RT_I_SHD_TOT_WIDTH_AMT",
    "THY_RT_I_SHD_TRT_WIDTH_AMT", "THY_RT_TRAV_WAY_WIDTH_AMT",
    "THY_RT_O_SHD_TOT_WIDTH_AMT", "THY_RT_O_SHD_TRT_WIDTH_AMT",
    "THY_RT_SIG_CHG_IND", "THY_CITY_CODE", "THY_HIGHWAY_GROUP_CODE",
    "THY_HIGHWAY_ACCESS_CODE", "THY_ACCESS_EFF_DATE", "THY_ACCESS_SIG_CHG_IND",
    "THY_TERRAIN_CODE", "THY_DESIGN_SPEED_AMT", "THY_NON_ADD_CODE",
    "THY_PROFILE_CODE", "THY_ADT_AMT", "THY_CHANGE_PER_MILE_AMT",
    "THY_LANDMARK_SHORT_DESC", "THY_POPULATION_CODE",
    "THY_POPULATION_GROUP_CODE", "THY_LAST_SIG_CHG_DATE", "THY_RECORD_DATE",
    "THY_FUNCTIONAL_CLASS_CODE", "THY_UPDATE_DATE", "THY_UPDATE_USER_NAME",
    "THY_MAINT_SVC_LVL_CODE", "THY_EQUATE_CODE", "THY_BREAK_DESC",
    "THY_FEDERAL_AID_CODE", "THY_FA_ROUTE_PREFIX_CODE", "THY_FA_ROUTE_NAME",
    "THY_TOLL_FOREST_CODE", "THY_NATIONAL_LANDS_CODE",
    "THY_SCENIC_FREEWAY_CODE", "THY_EXTRACT_DATE",
]

# --------------------------------------------------------------------------- #
# Per-column provenance: {column: (tier, source layer, source column, note)}.
# Tiers: "sourced" (painted from a mapped layer), "synthesized" (derived from
# the overlay structure), "no TSMIS source" (present + empty + noted — owner
# decision 2026-07-22), "TSN-internal" (bookkeeping; never fabricated).
# The consolidator adds each layer's FeatureServer URL from 00_INDEX at build
# time; the comparison Notes list these lines verbatim.
# --------------------------------------------------------------------------- #
_S = "sourced"
_Y = "synthesized"
_N = "no TSMIS source"
_T = "TSN-internal"
PROVENANCE = {
    "THY_ID": (_T, "", "", "TSN bookkeeping — left empty, never compared"),
    "THY_ELEMENT_ID": (_T, "", "", "TSN bookkeeping — left empty, never compared"),
    "THY_BEGIN_OFFSET_AMT": (_Y, "(overlay)", "",
                             "PM-continued cumulative (forward-gap jumps; "
                             "parallel L rows never advance it) — diverges "
                             "from TSN's own line wherever segmentation "
                             "differs, so it is shown, never counted (the "
                             "sliver shows once on END PM/LENGTH instead)"),
    "THY_END_OFFSET_AMT": (_Y, "(overlay)", "",
                           "begin offset + length — shown, never counted "
                           "(see THY_BEGIN_OFFSET_AMT)"),
    "THY_BEGIN_DATE": (_T, "", "", "TSN lifecycle — left empty, never compared"),
    "THY_END_DATE": (_T, "", "", "TSN lifecycle sentinel — left empty"),
    "THY_CREATE_DATE": (_T, "", "", "TSN bookkeeping — left empty"),
    "THY_CREATE_USER_NAME": (_T, "", "", "TSN bookkeeping — left empty"),
    "THY_SEG_ORDER_ID": (_S, "SHS Inv Network Date", "SegOrderId", ""),
    "THY_DISTRICT_CODE": (_S, "SHS District", "District_Code", ""),
    "THY_COUNTY_CODE": (_S, "(every span layer)", "BeginCounty/EndCounty",
                        "the county+PM bucket identity"),
    "THY_ROUTE_NAME": (_S, "(every span layer)", "RouteNum", ""),
    "THY_ROUTE_SUFFIX_CODE": (_S, "(every span layer)", "RouteSuffix", ""),
    "THY_PM_PREFIX_CODE": (_S, "(every span layer)", "BeginPMPrefix", ""),
    "THY_BEGIN_PM_AMT": (_Y, "(overlay)", "", "the breakpoint union"),
    "THY_END_PM_AMT": (_Y, "(overlay)", "", "the breakpoint union"),
    "THY_PM_SUFFIX_CODE": (_Y, "SHS Highway Group", "Highway_Group",
                           "R/L on independent alignments; TSN's X "
                           "(unconstructed) inventory rows have no layer "
                           "counterpart and stay one-sided"),
    "THY_LENGTH_MILES_AMT": (_Y, "(overlay)", "", "end PM − begin PM"),
    "THY_LEFT_ROAD_EFF_DATE": (_S, "(left-road block)",
                               "InventoryItemStartDate",
                               "composite: newest member layer's item date "
                               "(candidate rule)"),
    "THY_LT_SURF_TYPE_CODE": (_S, "SHS Surface Type L", "Surface_Type_L", ""),
    "THY_LT_LANES_AMT": (_S, "SHS Travel Way L", "Total_Num_Lanes_L",
                         "Total lanes, not Thru (proven on 001)"),
    "THY_LT_SPEC_FEATURES_CODE": (_S, "SHS Special Feature L",
                                  "Special_Feature_Type_L",
                                  "absent span ≡ TSN Z"),
    "THY_LT_O_SHD_TOT_WIDTH_AMT": (_S, "SHS O Shld Width L",
                                   "Shld_Width_Total_Out_L", ""),
    "THY_LT_O_SHD_TRT_WIDTH_AMT": (_S, "SHS O Shld Width L",
                                   "Shld_Width_Treated_Out_L", ""),
    "THY_LT_TRAV_WAY_WIDTH_AMT": (_S, "SHS Travel Way L", "Travel_Way_Width_L",
                                  ""),
    "THY_LT_I_SHD_TOT_WIDTH_AMT": (_S, "SHS I Shld Width L",
                                   "Shld_Width_Total_In_L", ""),
    "THY_LT_I_SHD_TRT_WIDTH_AMT": (_S, "SHS I Shld Width L",
                                   "Shld_Width_Treated_In_L", ""),
    "THY_LT_SIG_CHG_IND": (_N, "", "", "TASAS change tracking — no layer"),
    "THY_MEDIAN_EFF_DATE": (_S, "(median block)", "InventoryItemStartDate",
                            "composite: newest of Median/Barrier/Curb "
                            "Landscape"),
    "THY_MEDIAN_TYPE_CODE": (_S, "SHS Median", "Median_Type", ""),
    "THY_CURB_LANDSCAPE_CODE": (_S, "SHS Curb Landscape", "Curb_Landscape", ""),
    "THY_MEDIAN_BARRIER_CODE": (_S, "SHS Barrier", "Barrier_Type", ""),
    "THY_MEDIAN_WIDTH_AMT": (_S, "SHS Median", "Median_Width", ""),
    "THY_MEDIAN_WIDTH_VAR_CODE": (_S, "SHS Median", "Median_Variance", ""),
    "THY_MEDIAN_SIG_CHG_IND": (_N, "", "", "TASAS change tracking — no layer"),
    "THY_RIGHT_ROAD_EFF_DATE": (_S, "(right-road block)",
                                "InventoryItemStartDate",
                                "composite: newest member layer's item date "
                                "(candidate rule)"),
    "THY_RT_SURF_TYPE_CODE": (_S, "SHS Surface Type R", "Surface_Type_R", ""),
    "THY_RT_LANES_AMT": (_S, "SHS Travel Way R", "Total_Num_Lanes_R",
                         "Total lanes, not Thru (proven on 001)"),
    "THY_RT_SPEC_FEATURES_CODE": (_S, "SHS Special Feature R",
                                  "Special_Feature_Type_R",
                                  "absent span ≡ TSN Z"),
    "THY_RT_I_SHD_TOT_WIDTH_AMT": (_S, "SHS I Shld Width R",
                                   "Shld_Width_Total_In_R", ""),
    "THY_RT_I_SHD_TRT_WIDTH_AMT": (_S, "SHS I Shld Width R",
                                   "Shld_Width_Treated_In_R", ""),
    "THY_RT_TRAV_WAY_WIDTH_AMT": (_S, "SHS Travel Way R", "Travel_Way_Width_R",
                                  ""),
    "THY_RT_O_SHD_TOT_WIDTH_AMT": (_S, "SHS O Shld Width R",
                                   "Shld_Width_Total_Out_R", ""),
    "THY_RT_O_SHD_TRT_WIDTH_AMT": (_S, "SHS O Shld Width R",
                                   "Shld_Width_Treated_Out_R", ""),
    "THY_RT_SIG_CHG_IND": (_N, "", "", "TASAS change tracking — no layer"),
    "THY_CITY_CODE": (_S, "City", "City_Code",
                      "the layer carries city NAMES; city_codes.norm_city "
                      "translates them to the TASAS letter codes (the table "
                      "was derived 2026-07-22 from statewide co-location — "
                      "21,906 rows voted, 99.92% agreement); an unmapped "
                      "name passes through verbatim so it surfaces"),
    "THY_HIGHWAY_GROUP_CODE": (_S, "SHS Highway Group", "Highway_Group", ""),
    "THY_HIGHWAY_ACCESS_CODE": (_S, "SHS Access Control", "SHS_Access_Control",
                                ""),
    "THY_ACCESS_EFF_DATE": (_S, "SHS Access Control", "InventoryItemStartDate",
                            ""),
    "THY_ACCESS_SIG_CHG_IND": (_N, "", "", "TASAS change tracking — no layer"),
    "THY_TERRAIN_CODE": (_S, "Terrain Type", "Terrain_Type", ""),
    "THY_DESIGN_SPEED_AMT": (_S, "SHS Design Speed", "Design_Speed", ""),
    "THY_NON_ADD_CODE": (_S, "SHS Non Add Mileage", "Non_Add_Mileage",
                         "flag span → N; default A"),
    "THY_PROFILE_CODE": (_S, "Traffic Volume Segments", "(span anchors)",
                         "P where a row starts a contiguous TVS profile span; "
                         "compared and counted (owner decision 2026-07-22)"),
    "THY_ADT_AMT": (_S, "Traffic Volume Segments",
                    "AADT/AADT_AHEAD/AADT_BACK",
                    "interpolated along the winning profile; compared and "
                    "counted (owner decision 2026-07-22 — a wholesale column "
                    "difference is exactly the signal to surface). Known "
                    "model-fit classes feeding the count: TSN's profiles "
                    "continue ACROSS county lines and its overlap vintage "
                    "rule isn't latest-year — the Notes say so"),
    "THY_CHANGE_PER_MILE_AMT": (_S, "Traffic Volume Segments",
                                "(AADT_BACK−AADT_AHEAD)/length",
                                "the winning span's slope, compared at 3 "
                                "decimals (the extract's own 4th-decimal "
                                "arithmetic wobble never counts)"),
    "THY_LANDMARK_SHORT_DESC": (_S, "SHS Landmark", "Landmarks_Short", ""),
    "THY_POPULATION_CODE": (_S, "SHS Population", "Population_Code", ""),
    "THY_POPULATION_GROUP_CODE": (_N, "", "",
                                  "all-null in the TSN extract too"),
    "THY_LAST_SIG_CHG_DATE": (_N, "", "", "TASAS change tracking — no layer"),
    "THY_RECORD_DATE": (_S, "SHS Inv Network Date", "Network_Start_Date", ""),
    "THY_FUNCTIONAL_CLASS_CODE": (_N, "", "",
                                  "all-null in the TSN extract too"),
    "THY_UPDATE_DATE": (_T, "", "", "TSN bookkeeping — left empty"),
    "THY_UPDATE_USER_NAME": (_T, "", "", "TSN bookkeeping — left empty"),
    "THY_MAINT_SVC_LVL_CODE": (_N, "", "",
                               "no maintenance layer anywhere in the ~90-layer "
                               "list — owner question outstanding"),
    "THY_EQUATE_CODE": (_S, "Equation Points", "(point coverage)",
                        "E where a row starts at an equation point"),
    "THY_BREAK_DESC": (_Y, "SHS Route Break + (structure)", "Route_Break_Type",
                       "BEG/END/CNTY/D-C/DIST from the overlay; R-BR/U-BR "
                       "from Route Break points; BEGL/ENDR at "
                       "independent-alignment edges"),
    "THY_FEDERAL_AID_CODE": (_N, "", "", "legacy federal-aid system — no layer"),
    "THY_FA_ROUTE_PREFIX_CODE": (_N, "", "",
                                 "legacy federal-aid system — no layer"),
    "THY_FA_ROUTE_NAME": (_N, "", "", "legacy federal-aid system — no layer"),
    "THY_TOLL_FOREST_CODE": (_S, "SHS Tolls + SHS Forest HWY", "(coverage)",
                             "1 = toll span; 2 = forest span; else 0"),
    "THY_NATIONAL_LANDS_CODE": (_N, "", "", "no layer found"),
    "THY_SCENIC_FREEWAY_CODE": (_N, "", "", "no layer found"),
    "THY_EXTRACT_DATE": (_Y, "(build)", "",
                         "stamped with the build's as-of date — ours, not "
                         "TSN's"),
}

# The columns the comparison SHOWS but never counts (CompareSchema
# context_fields): everything with no TSMIS source or TSN-internal,
# THY_EXTRACT_DATE (ours is the as-of date by definition), and the two
# SYNTHESIZED offset columns (both sides' offsets are their OWN derived
# cumulatives; ours diverges from TSN's line at every segmentation sliver,
# and the sliver already shows once on END PM/LENGTH). The ADT profile trio
# IS compared and counted (owner decision 2026-07-22: a wholesale column
# difference is exactly the signal to surface; the Notes name the known
# model-fit classes inside that count). All context columns stay PRESENT in
# the sheet with both sides' values visible.
_SYNTHESIZED_CONTEXT = ("THY_BEGIN_OFFSET_AMT", "THY_END_OFFSET_AMT")
CONTEXT_COLUMNS = tuple(
    name for name in HEADER
    if PROVENANCE[name][0] in (_N, _T) or name == "THY_EXTRACT_DATE"
    or name in _SYNTHESIZED_CONTEXT)


def provenance_line(name):
    """One human-readable audit line: 'THY_X — sourced: SHS Median
    (Median_Type)' (+ the note when it carries one)."""
    tier, layer, column, note = PROVENANCE[name]
    src = f": {layer}" if layer else ""
    if column:
        src += f" ({column})"
    tail = f" — {note}" if note else ""
    return f"{name} — {tier}{src}{tail}"
