"""Clean Road CA HIGHWAYS (v0.29.0) — the ArcGIS layer substrate, the overlay
consolidator, the TSN normalizer, and the ArcGIS-vs-TSN comparator, all on a
SYNTHETIC mini-library (hermetic: no real data, no network).

Covers:
  * the dialect normalizers (labels export <-> bundle codes <-> TASAS codes);
  * LRS as-of algebra + integer micro-postmile round-trips;
  * stream_layer's name-keyed reads, optional columns, and the INDEX
    row-count gate (truncation refuses; the measured healthy over-count race
    passes);
  * the consolidator end-to-end on a tiny library: base/R/L rows, the X
    coverage-gap row, city cuts, the ADT profile family, TOLL/FOREST mux,
    point attachments, cross-county splitting, the 74-column header, the
    Provenance sheet (every column tiered), the build marker, and the
    missing-layer / truncated-layer refusals;
  * the TSN normalizer (verbatim projection + CMP-AUD-037 marker) and the
    comparator's role gates (the ArcGIS side REQUIRES the build marker, the
    TSN side REJECTS it) + a real mode="both" comparison where a CONTEXT
    column's one-sided values are never counted as differences.

Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_clean_road.py
"""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import city_codes                       # noqa: E402
import clean_highway_columns as chc     # noqa: E402
import clean_road_layers as crl         # noqa: E402
import compare_clean_highway_tsn as cht  # noqa: E402
import consolidate_clean_highway as cch  # noqa: E402
import tsn_load_clean_road as tlc       # noqa: E402
from events import Events               # noqa: E402
from openpyxl import Workbook, load_workbook  # noqa: E402

_fail = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _fail.append(name)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
ASOF = "2025-09-08"
_LIVE = {"LRSFromDate": datetime(2020, 1, 1), "LRSToDate": None}
_DEAD = {"LRSFromDate": datetime(2010, 1, 1), "LRSToDate": datetime(2015, 1, 1)}
_FUTURE = {"LRSFromDate": datetime(2026, 1, 1), "LRSToDate": None}


def _span(county, b, e, od, attrs, align="Right", prefix=".", route="1",
          district="District 12", county2=None, prefix2=None, life=None,
          item=datetime(1990, 5, 5), od_end=None):
    row = {
        "District": district, "RouteNum": route, "RouteSuffix": ".",
        "Alignment": align, "BeginCounty": county,
        "EndCounty": county2 or county, "BeginPMPrefix": prefix,
        "BeginPMMeasure": b, "EndPMPrefix": prefix2 or prefix,
        "EndPMMeasure": e,
        "BeginODMeasure": od,
        "EndODMeasure": od + (e - b) if od_end is None else od_end,
        "InventoryItemStartDate": item, "RouteID": f"SHS_{route}._P",
    }
    row.update(life or _LIVE)
    row.update(attrs)
    return row


def _point(county, pm, attrs, align="Right", prefix=".", route="1", life=None):
    row = {"RouteNum": route, "RouteSuffix": ".", "Alignment": align,
           "County": county, "PMPrefix": prefix, "PMMeasure": pm}
    row.update(life or _LIVE)
    row.update(attrs)
    return row


def _write_layer(lib, nn, layer, rows, columns):
    wb = Workbook()
    ws = wb.active
    ws.title = layer[:31]
    ws.append(columns)
    for r in rows:
        ws.append([r.get(c) for c in columns])
    path = lib / f"{nn:02d}_{layer}.xlsx"
    wb.save(path)
    return len(rows)


def _build_library(lib, *, drop_layer=None, lie_rows=None):
    """A minimal consistent library covering every required highway layer for
    route 001 across Orange + Los Angeles. Returns the INDEX entry list."""
    lib.mkdir(parents=True, exist_ok=True)
    span_cols = ["OBJECTID", "District", "RouteNum", "RouteSuffix", "Alignment",
                 "BeginCounty", "EndCounty", "BeginPMPrefix", "BeginPMMeasure",
                 "BeginPMSuffix", "EndPMPrefix", "EndPMMeasure", "EndPMSuffix",
                 "BeginODMeasure", "EndODMeasure", "InventoryItemStartDate",
                 "InventoryItemEndDate", "RouteID", "LRSFromDate", "LRSToDate"]
    point_cols = ["OBJECTID", "RouteNum", "RouteSuffix", "Alignment", "County",
                  "PMPrefix", "PMMeasure", "PMSuffix", "ODMeasure",
                  "LRSFromDate", "LRSToDate"]

    ora, la = "Orange", "Los Angeles"
    # HG: ORA D 0-1, U 1-2, independent pair 2-2.5 (R) / 2-2.6 (L),
    # D 2.5-3.0, GAP 3-4 (unconstructed), D 4-5; LA D 0-1.
    hg = [
        _span(ora, 0.0, 1.0, 0.0, {"Highway_Group": "D- Divided Highway"}),
        _span(ora, 1.0, 2.0, 1.0, {"Highway_Group": "U- Undivided Highway"}),
        _span(ora, 2.0, 2.5, 2.0, {"Highway_Group": "R- Independent Alignment"}),
        _span(ora, 2.0, 2.6, 2.0, {"Highway_Group": "L- Independent Alignment"},
              align="Left"),
        _span(ora, 2.5, 3.0, 2.5, {"Highway_Group": "D- Divided Highway"}),
        _span(ora, 4.0, 5.0, 4.0, {"Highway_Group": "D- Divided Highway"}),
        _span(la, 0.0, 1.0, 5.0, {"Highway_Group": "D- Divided Highway"},
              district="District 7"),
        _span(ora, 0.0, 5.0, 0.0, {"Highway_Group": "U- Undivided Highway"},
              life=_DEAD),                       # history: never painted
        _span(la, 0.0, 1.0, 5.0, {"Highway_Group": "U- Undivided Highway"},
              district="District 7", life=_FUTURE),  # future: never painted
    ]
    whole = {
        "SHS Median": (["Median_Type", "Median_Width", "Median_Variance"],
                       {"Median_Type": "H- Paved Median", "Median_Width": 12,
                        "Median_Variance": "Z- No Variance"}),
        "Terrain Type": (["Terrain_Type"], {"Terrain_Type": "F- Level"}),
        "SHS Design Speed": (["Design_Speed"], {"Design_Speed": 65}),
        "SHS Curb Landscape": (["Curb_Landscape"],
                               {"Curb_Landscape": "7- No Curbs or Shrubs"}),
        "SHS Barrier": (["Barrier_Type"], {"Barrier_Type": "Z- No Barriers"}),
        "SHS Population": (["Population_Code"],
                           {"Population_Code": "R- Rural"}),
    }
    sides = {
        "SHS Travel Way R": (["Travel_Way_Width_R", "Total_Num_Lanes_R"],
                             {"Travel_Way_Width_R": 24, "Total_Num_Lanes_R": 2},
                             "Right"),
        "SHS Surface Type R": (["Surface_Type_R"],
                               {"Surface_Type_R": "H- AC: Base & Surface"},
                               "Right"),
        "SHS Special Feature R": (["Special_Feature_Type_R"],
                                  {"Special_Feature_Type_R":
                                   "Z- No Special Features"}, "Right"),
        "SHS O Shld Width R": (["Shld_Width_Total_Out_R",
                                "Shld_Width_Treated_Out_R"],
                               {"Shld_Width_Total_Out_R": 8,
                                "Shld_Width_Treated_Out_R": 8}, "Right"),
        "SHS I Shld Width R": (["Shld_Width_Total_In_R",
                                "Shld_Width_Treated_In_R"],
                               {"Shld_Width_Total_In_R": 0,
                                "Shld_Width_Treated_In_R": 0}, "Right"),
        "SHS Travel Way L": (["Travel_Way_Width_L", "Total_Num_Lanes_L"],
                             {"Travel_Way_Width_L": 24, "Total_Num_Lanes_L": 2},
                             "Left"),
        "SHS Surface Type L": (["Surface_Type_L"],
                               {"Surface_Type_L": "H- AC: Base & Surface"},
                               "Left"),
        "SHS Special Feature L": (["Special_Feature_Type_L"],
                                  {"Special_Feature_Type_L":
                                   "Z- No Special Features"}, "Left"),
        "SHS O Shld Width L": (["Shld_Width_Total_Out_L",
                                "Shld_Width_Treated_Out_L"],
                               {"Shld_Width_Total_Out_L": 8,
                                "Shld_Width_Treated_Out_L": 8}, "Left"),
        "SHS I Shld Width L": (["Shld_Width_Total_In_L",
                                "Shld_Width_Treated_In_L"],
                               {"Shld_Width_Total_In_L": 0,
                                "Shld_Width_Treated_In_L": 0}, "Left"),
    }

    entries, nn = [], 0

    def add(layer, rows, columns):
        nonlocal nn
        nn += 1
        if layer == drop_layer:
            return
        n = _write_layer(lib, nn, layer, rows, columns)
        claimed = lie_rows.get(layer, n) if lie_rows else n
        entries.append((f"{nn:02d}_{layer}.xlsx", layer, claimed,
                        len(columns), f"path/{layer}",
                        f"https://gis.example/{layer}/FeatureServer/{nn}"))

    add("SHS Highway Group", hg, span_cols + ["Highway_Group"])
    for layer, (attr_cols, attrs) in whole.items():
        rows = [_span(ora, 0.0, 5.0, 0.0, attrs),
                _span(ora, 2.0, 2.6, 2.0, attrs, align="Left"),
                _span(la, 0.0, 1.0, 5.0, attrs, district="District 7")]
        add(layer, rows, span_cols + attr_cols)
    for layer, (attr_cols, attrs, align) in sides.items():
        rows = [_span(ora, 0.0, 5.0, 0.0, attrs, align=align),
                _span(la, 0.0, 1.0, 5.0, attrs, align=align,
                      district="District 7")]
        add(layer, rows, span_cols + attr_cols)
    # Access Control: a CROSS-COUNTY span ORA 4.5 -> LA 0.3 (odometers carry
    # the apportioning), plus plain coverage before it.
    add("SHS Access Control",
        [_span(ora, 0.0, 4.5, 0.0, {"SHS_Access_Control":
                                    "C- Conventional Highway"}),
         _span(ora, 4.5, 0.3, 4.5, {"SHS_Access_Control":
                                    "F- Freeway (full control)"},
               county2=la, od_end=5.3)],
        span_cols + ["SHS_Access_Control"])
    add("SHS Non Add Mileage",
        [_span(ora, 4.0, 4.4, 4.0, {"Non_Add_Mileage": "N - Non-Add"})],
        span_cols + ["Non_Add_Mileage"])
    add("SHS Tolls",
        [_span(ora, 0.5, 0.8, 0.5, {"Toll_Type": "Toll Roads"})],
        span_cols + ["Toll_Type"])
    add("SHS Forest HWY",
        [_span(la, 0.5, 0.8, 5.5, {"Forest_Hwy": "Yes"},
               district="District 7")],
        span_cols + ["Forest_Hwy"])
    add("SHS Inv Network Date",
        [_span(ora, 0.0, 5.0, 0.0, {"Network_Start_Date": datetime(1964, 1, 1),
                                    "SegOrderId": 100}),
         _span(la, 0.0, 1.0, 5.0, {"Network_Start_Date": datetime(1964, 1, 1),
                                   "SegOrderId": 200},
               district="District 7")],
        [c for c in span_cols if c != "InventoryItemStartDate"]
        + ["Network_Start_Date", "Network_End_Date", "SegOrderId"])
    add("City",
        [_span(ora, 0.2, 0.4, 0.2, {"City_Code": "Los Angeles"}),
         _span(ora, 0.9, 0.95, 0.9, {"City_Code": "Unincorporated Ville"}),
         _span(ora, 90.0, 91.0, 90.0, {"City_Code": "NOT SHS"})
         | {"RouteID": "ORA_X_SIDE ST_P"}],
        span_cols + ["City_Code"])
    add("Traffic Volume Segments",
        [_span(ora, 0.0, 1.0, 0.0,
               {"AADT": 1000, "AADT_YEAR": 2024, "AADT_AHEAD": 700,
                "AADT_BACK": 800}),
         _span(ora, 0.0, 1.0, 0.0,
               {"AADT": 900, "AADT_YEAR": 2022, "AADT_AHEAD": 650,
                "AADT_BACK": 750})],
        span_cols + ["AADT", "AADT_YEAR", "AADT_AHEAD", "AADT_BACK"])
    add("SHS Landmark",
        [_point(ora, 1.0, {"Landmarks_Short": "TEST LANDMARK"}),
         _point(ora, 1.0, {"Landmarks_Short": "X"})],
        point_cols + ["Landmarks_Short", "Landmarks_Long"])
    add("Equation Points",
        [_point(ora, 0.5, {"hslDescription": "EQ"})],
        point_cols + ["hslDescription"])
    add("SHS Route Break",
        [_point(ora, 4.0, {"Route_Break_Type": "Route Resume"})],
        point_cols + ["Route_Break_Type"])

    wb = Workbook()
    ws = wb.active
    ws.append(crl.INDEX_HEADER)
    for row in entries:
        ws.append(list(row))
    wb.save(lib / crl.INDEX_NAME)
    return entries


def _rows_of(path, sheet):
    wb = load_workbook(path, data_only=True)
    try:
        it = wb[sheet].iter_rows(values_only=True)
        header = [str(c) if c is not None else "" for c in next(it)]
        return header, [list(r) for r in it]
    finally:
        wb.close()


# --------------------------------------------------------------------------- #
# unit checks
# --------------------------------------------------------------------------- #
def test_dialects_and_algebra():
    print("== dialects + LRS/PM algebra")
    check("county name -> code", crl.norm_county("Los Angeles") == "LA")
    check("county dotted code", crl.norm_county("LA.") == "LA")
    check("county code passthrough", crl.norm_county("SBD") == "SBD")
    check("district label", crl.norm_district("District 7") == "07")
    check("district number", crl.norm_district(12) == "12")
    check("alignment label", crl.norm_alignment("Right") == "R")
    check("alignment none", crl.norm_alignment(".") == "")
    check("coded label", crl.code_of("J- Unpaved Median") == "J")
    check("coded label spaced", crl.code_of("N - Non-Add") == "N")
    check("coded bare", crl.code_of("Z") == "Z")
    check("coded numeric", crl.code_of("7- No Curbs or Shrubs") == "7")
    check("dot none", crl.dot_none(".") == "")
    check("route pad", crl.norm_route("1") == "001")
    check("city name -> TASAS code", city_codes.norm_city("Los Angeles") == "LA")
    check("city code passthrough", city_codes.norm_city("SJS") == "SJS")
    check("unmapped city surfaces upper",
          city_codes.norm_city("No Such Town") == "NO SUCH TOWN")
    d = crl.to_serial(datetime(2025, 9, 8))
    check("serial of datetime", d == 45908.0)
    check("serial of iso text", crl.to_serial("2025-09-08") == 45908.0)
    check("serial of number", crl.to_serial(45908) == 45908.0)
    check("serial of dot", crl.to_serial(".") is None)
    check("as-of open current", crl.is_asof(45000.0, None, 45908.0))
    check("as-of from-boundary live", crl.is_asof(45908.0, None, 45908.0))
    check("as-of to-boundary dead", not crl.is_asof(45000.0, 45908.0, 45908.0))
    check("pm units float noise", crl.pm_units(82.71599999999999) == 8271600)
    check("pm text trims", crl.pm_text(8271600) == "82.716")
    check("pm text 5dp", crl.pm_text(18623798) == "186.23798")
    segs = crl.overlay({"A": [(0, 10, "a1", (1,)), (0, 10, "a2", (2,))],
                        "B": [(5, 15, "b", (1,))]}, cuts=(7,))
    check("overlay rank wins", segs[0][2]["A"] == "a2")
    check("overlay cut applied", any(s[0] == 7 for s in segs))
    check("overlay union edges", [s[0] for s in segs] == [0, 5, 7, 10])


def test_stream_and_index():
    print("== stream_layer + INDEX gates")
    with tempfile.TemporaryDirectory() as td:
        lib = Path(td) / "lib"
        _build_library(lib)
        inv = crl.inventory(lib)
        check("inventory sees all present", not inv["missing"] or
              set(inv["missing"]) <= (set(crl.EXPECTED_LAYERS)
                                      - set(cch.HIGHWAY_LAYERS) - {"City"}))
        check("index present", inv["index"] is not None)
        idx = crl.read_index(lib)
        check("index carries sources",
              idx["SHS Median"]["source"].startswith("https://gis.example/"))
        hg = lib / "01_SHS Highway Group.xlsx"
        rows = list(crl.stream_layer(hg, ["Highway_Group", "BeginCounty"],
                                     layer_name="SHS Highway Group"))
        check("name-keyed read", rows[0]["Highway_Group"].startswith("D-"))
        rows = list(crl.stream_layer(hg, ["Missing_Col"], optional=("Missing_Col",)))
        check("optional column reads None", rows[0]["Missing_Col"] is None)
        try:
            list(crl.stream_layer(hg, ["Nope"]))
            check("missing wanted column refuses", False)
        except ValueError as e:
            check("missing wanted column refuses", "Nope" in str(e))
        try:
            list(crl.stream_layer(hg, ["Highway_Group"], expected_rows=99))
            check("truncated export refuses", False)
        except ValueError as e:
            check("truncated export refuses", "truncated" in str(e))
        n = len(list(crl.stream_layer(hg, ["Highway_Group"])))
        ok = list(crl.stream_layer(hg, ["Highway_Group"], expected_rows=n - 2))
        check("healthy over-count race passes", len(ok) == n)


def test_consolidator_end_to_end():
    print("== consolidator end-to-end (synthetic library)")
    with tempfile.TemporaryDirectory() as td:
        lib = Path(td) / "lib"
        _build_library(lib)
        out = Path(td) / "built.xlsx"
        res = cch.consolidate(events=Events(), asof=ASOF, lib_root=lib,
                              out_path=out)
        check("build ok", res.status == "ok")
        check("build complete", res.completion == "complete")
        check("build names output", res.output_path == str(out))
        header, rows = _rows_of(out, chc.ARC_SHEET)
        check("74-column header", header == chc.HEADER)
        col = {n: i for i, n in enumerate(chc.HEADER)}

        def rows_where(**kw):
            keep = []
            for r in rows:
                if all(str(r[col[k]] or "") == str(v) for k, v in kw.items()):
                    keep.append(r)
            return keep

        ora = rows_where(THY_COUNTY_CODE="ORA")
        la = rows_where(THY_COUNTY_CODE="LA")
        check("both counties built", bool(ora) and bool(la))
        check("district painted per county",
              ora[0][col["THY_DISTRICT_CODE"]] == "12"
              and la[0][col["THY_DISTRICT_CODE"]] == "07")
        check("an HG coverage gap yields NO fabricated row (TSN's X rows "
              "stay one-sided)",
              not any(3.0 <= r[col["THY_BEGIN_PM_AMT"]] < 4.0 for r in ora))
        r_rows = rows_where(THY_PM_SUFFIX_CODE="R")
        l_rows = rows_where(THY_PM_SUFFIX_CODE="L")
        check("independent pair rows exist", r_rows and l_rows)
        check("R row nulls the LT block",
              r_rows[0][col["THY_LT_SURF_TYPE_CODE"]] is None
              and r_rows[0][col["THY_RT_SURF_TYPE_CODE"]] == "H")
        check("L row nulls the RT block",
              l_rows[0][col["THY_RT_SURF_TYPE_CODE"]] is None
              and l_rows[0][col["THY_LT_SURF_TYPE_CODE"]] == "H")
        check("L row spans its own alignment PMs",
              l_rows[0][col["THY_BEGIN_PM_AMT"]] == 2.0
              and l_rows[-1][col["THY_END_PM_AMT"]] == 2.6)
        first = ora[0]
        check("profile anchor: P + AADT_AHEAD at the span begin",
              first[col["THY_PROFILE_CODE"]] == "P"
              and first[col["THY_ADT_AMT"]] == 700
              and first[col["THY_CHANGE_PER_MILE_AMT"]] == 100.0)
        cut_rows = [r for r in ora if r[col["THY_BEGIN_PM_AMT"]] in (0.2, 0.4)]
        check("city boundaries cut rows", len(cut_rows) == 2)
        check("equate point cuts + flags",
              any(r[col["THY_BEGIN_PM_AMT"]] == 0.5
                  and r[col["THY_EQUATE_CODE"]] == "E" for r in ora))
        lmk = [r for r in ora if r[col["THY_BEGIN_PM_AMT"]] == 1.0]
        check("landmark attaches (longest text)",
              lmk and lmk[0][col["THY_LANDMARK_SHORT_DESC"]] == "TEST LANDMARK")
        toll = [r for r in ora if r[col["THY_BEGIN_PM_AMT"]] == 0.5]
        check("toll span -> code 1",
              toll and toll[0][col["THY_TOLL_FOREST_CODE"]] == 1)
        forest = [r for r in la if r[col["THY_BEGIN_PM_AMT"]] == 0.5]
        check("forest span -> code 2",
              forest and forest[0][col["THY_TOLL_FOREST_CODE"]] == 2)
        check("non-add span -> N; default A",
              any(r[col["THY_NON_ADD_CODE"]] == "N" for r in ora)
              and la[0][col["THY_NON_ADD_CODE"]] == "A")
        check("cross-county access reaches LA",
              la[0][col["THY_HIGHWAY_ACCESS_CODE"]] == "F")
        check("cross-county access tail stays in ORA",
              any(r[col["THY_BEGIN_PM_AMT"]] == 4.5
                  and r[col["THY_HIGHWAY_ACCESS_CODE"]] == "F" for r in ora))
        check("no-source columns stay empty",
              all(r[col["THY_MAINT_SVC_LVL_CODE"]] is None for r in rows))
        in_city = [r for r in ora
                   if 0.2 <= r[col["THY_BEGIN_PM_AMT"]] < 0.4]
        check("city names normalize to TASAS codes",
              in_city and all(r[col["THY_CITY_CODE"]] == "LA"
                              for r in in_city))
        unmapped = [r for r in ora
                    if 0.9 <= r[col["THY_BEGIN_PM_AMT"]] < 0.95]
        check("an unmapped city name passes through visibly (upper-cased)",
              unmapped and all(r[col["THY_CITY_CODE"]]
                               == "UNINCORPORATED VILLE" for r in unmapped))
        check("no city outside the spans",
              all(r[col["THY_CITY_CODE"]] is None for r in ora
                  if r[col["THY_BEGIN_PM_AMT"]] >= 1.0))
        check("extract date = the as-of date",
              str(rows[0][col["THY_EXTRACT_DATE"]]).startswith(ASOF))
        offs = [r[col["THY_BEGIN_OFFSET_AMT"]] for r in ora]
        check("offsets are monotone within the route",
              all(a <= b for a, b in zip(offs, offs[1:])))
        check("first-county offsets ARE the begin PMs (PM-continued; the "
              "parallel L roadbed reads but never advances the line)",
              all(r[col["THY_BEGIN_OFFSET_AMT"]]
                  == r[col["THY_BEGIN_PM_AMT"]] for r in ora
                  if r[col["THY_PM_SUFFIX_CODE"]] != "L"))
        check("the county line continues the cumulative (LA starts at ORA's "
              "corridor end)",
              la[0][col["THY_BEGIN_OFFSET_AMT"]]
              == 5.0 + la[0][col["THY_BEGIN_PM_AMT"]])
        check("BEG marks the route start",
              rows[0][col["THY_BREAK_DESC"]] == "BEG")
        check("route-break point -> U-BR (resume)",
              any(r[col["THY_BREAK_DESC"]] == "U-BR" for r in ora))

        pheader, prows = _rows_of(out, "Provenance")
        check("provenance covers all 74 columns",
              len(prows) == len(chc.HEADER)
              and [r[0] for r in prows] == chc.HEADER)
        check("provenance carries FeatureServer sources",
              any("https://gis.example/" in str(r[5] or "") for r in prows))
        mheader, mrows = _rows_of(out, chc.ARC_MARKER_SHEET)
        marker = {str(mheader[0]): mheader[1]}
        for r in mrows:
            marker[str(r[0])] = r[1]
        check("build marker carries the as-of", marker.get("As-of date") == ASOF)

        # refusals
        lib2 = Path(td) / "lib2"
        _build_library(lib2, drop_layer="SHS Median")
        res2 = cch.consolidate(events=Events(), asof=ASOF, lib_root=lib2,
                               out_path=Path(td) / "b2.xlsx")
        check("missing layer refuses by name",
              res2.status == "error" and "SHS Median" in res2.message)
        lib3 = Path(td) / "lib3"
        _build_library(lib3, lie_rows={"SHS Barrier": 99})
        res3 = cch.consolidate(events=Events(), asof=ASOF, lib_root=lib3,
                               out_path=Path(td) / "b3.xlsx")
        check("truncated layer refuses via the INDEX gate",
              res3.status == "error" and "truncated" in res3.message)
        res4 = cch.consolidate(events=Events(), asof="nonsense", lib_root=lib,
                               out_path=Path(td) / "b4.xlsx")
        check("bad as-of refuses", res4.status == "error"
              and "as-of" in res4.message)


def _tsn_raw(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = chc.TSN_RAW_SHEET
    ws.append(list(chc.HEADER))
    for r in rows:
        ws.append(r)
    wb.save(path)


def _thy_row(county="ORA", route="001", begin=0.0, end=1.0, maint=None,
             hg="D"):
    row = [None] * len(chc.HEADER)
    col = {n: i for i, n in enumerate(chc.HEADER)}
    row[col["THY_DISTRICT_CODE"]] = "12"
    row[col["THY_COUNTY_CODE"]] = county
    row[col["THY_ROUTE_NAME"]] = route
    row[col["THY_BEGIN_PM_AMT"]] = begin
    row[col["THY_END_PM_AMT"]] = end
    row[col["THY_LENGTH_MILES_AMT"]] = round(end - begin, 5)
    row[col["THY_HIGHWAY_GROUP_CODE"]] = hg
    row[col["THY_MAINT_SVC_LVL_CODE"]] = maint
    row[col["THY_EXTRACT_DATE"]] = datetime(2025, 9, 8)
    return row


def test_normalizer_and_comparator():
    print("== TSN normalizer + comparator role gates + context columns")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        lib = td / "lib"
        _build_library(lib)
        built = td / "built.xlsx"
        res = cch.consolidate(events=Events(), asof=ASOF, lib_root=lib,
                              out_path=built)
        check("arc side built", res.status == "ok")

        raw_dir = td / "raw"
        raw_dir.mkdir()
        # The TSN side mirrors the built ORA base rows loosely: same first
        # two rows, a MAINT value everywhere (context — never counted), and
        # one REAL difference (HG on the second row).
        header, arows = _rows_of(built, chc.ARC_SHEET)
        col = {n: i for i, n in enumerate(chc.HEADER)}
        tsn_rows = []
        for i, r in enumerate(arows):
            rr = list(r)
            rr[col["THY_MAINT_SVC_LVL_CODE"]] = 2          # context-only delta
            if i == 1:
                rr[col["THY_HIGHWAY_GROUP_CODE"]] = "Q"    # ONE real diff
            tsn_rows.append(rr)
        _tsn_raw(raw_dir / "CA HIGHWAYS test.xlsx", tsn_rows)

        norm = td / "normalized.xlsx"
        nres = tlc.build_into_highway(raw_dir, norm, events=Events())
        check("normalizer ok", nres.status == "ok")
        wb = load_workbook(norm)
        try:
            import compare_tsn_common as ctc
            check("normalized sheet present",
                  chc.NORMALIZED_SHEET in wb.sheetnames)
            check("normalization marker v1",
                  ctc.normalization_marker_version(wb)
                  == cht.NORMALIZATION_VERSION)
        finally:
            wb.close()

        bad = td / "bad_raw"
        bad.mkdir()
        wbx = Workbook()
        wsx = wbx.active
        wsx.title = chc.TSN_RAW_SHEET
        wsx.append(list(chc.HEADER[:-1]) + ["WRONG"])
        wsx.append([None] * len(chc.HEADER))
        wbx.save(bad / "CA HIGHWAYS bad.xlsx")
        nbad = tlc.build_into_highway(bad, td / "n2.xlsx", events=Events())
        check("normalizer refuses a drifted header", nbad.status == "error")

        # Role gates.
        try:
            cht._load_arc(norm)
            check("ARC side refuses an unmarked/TSN workbook", False)
        except ValueError as e:
            check("ARC side refuses an unmarked/TSN workbook",
                  chc.ARC_MARKER_SHEET in str(e))
        try:
            cht._load_tsn(built)
            check("TSN side refuses the ArcGIS build", False)
        except ValueError as e:
            check("TSN side refuses the ArcGIS build",
                  chc.ARC_MARKER_SHEET in str(e))
        check("TSN side loads the normalized library",
              len(cht._load_tsn(norm)) == len(tsn_rows))
        check("TSN side loads the raw extract",
              len(cht._load_tsn(raw_dir / "CA HIGHWAYS test.xlsx"))
              == len(tsn_rows))

        # The full comparison, both flavors, on the shipped path.
        out = td / "cmp.xlsx"
        cres = cht.compare(built, norm, out, events=Events(), mode="both")
        check("comparison ok", cres.status == "ok")
        values_twin = out.with_name(out.stem + " (values)" + out.suffix)
        check("both flavors written", out.is_file() and values_twin.is_file())
        oc = cres.comparison_outcome
        counts = getattr(oc, "counts", None)
        check("typed outcome carries counts",
              counts is not None and counts.known)
        diffs = getattr(counts, "differing_cells", None)
        check("exactly the ONE real difference is counted (context never "
              f"counts) — got {diffs}", diffs == 1)


def main():
    test_dialects_and_algebra()
    test_stream_and_index()
    test_consolidator_end_to_end()
    test_normalizer_and_comparator()
    print()
    if _fail:
        print(f"FAILED: {len(_fail)} check(s): {_fail}")
        return 1
    print("ALL CLEAN-ROAD CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
