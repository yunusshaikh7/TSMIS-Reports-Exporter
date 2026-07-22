# Clean Road — CA HIGHWAYS from the ArcGIS layers (coverage assessment)

**Status: FEASIBLE — the overlay model is value-proven on route 001 (2026-07-22).**
This is the design/coverage record for building our own "CA HIGHWAYS" clean-road
file from the owner's TSMIS ArcGIS layer exports, to compare against the TSN
extract (`CA HIGHWAYS <date>.xlsx`, the `THY_*` table). Intersections and Ramps
follow later on the same pattern (their layer families are already identified).

Everything below is **measured** against the 2026-07-20 layer export and the
2025-09-08 TSN extract — no column mapping is assumed. The census scripts and
exact numbers live locally beside the data in
`Downloads\TSMIS\_inbox\Cleanroad\_analysis\` (see its README; local-only, like
all real data). Sibling doc for the eventual app integration:
[`docs/roadmap.md`](../roadmap.md) "Clean Road Files" + "ArcGIS layer processing".

---

## The shape of the problem (measured)

- **TSN side:** `CA HIGHWAYS` = 60,083 rows × 74 `THY_*` columns, **current-state
  only** (`THY_END_DATE` is the constant sentinel `3000-01-01`), extract date
  stamped in every row (`THY_EXTRACT_DATE`, here 2025-09-08). Same 60,083-record
  universe as the TSAR Highway Detail TSN extract (56 cols) — the clean-road
  table is the SOURCE table the HD report projects from.
- **TSMIS side:** single-attribute **LRS event layers** (one worksheet per layer
  in the export workbook). Shared span shape: `District, RouteNum('001'),
  RouteSuffix('.'=none, S, U), Alignment, Begin/EndCounty, Begin/EndPMPrefix
  ('.'=none), Begin/EndPMMeasure, Begin/EndPMSuffix, Begin/EndODMeasure,
  <attribute column(s)>, InventoryItemStartDate, InventoryItemEndDate,
  LRSFromDate, LRSToDate, RouteID('SHS_001._P'), From/ToARMeasure, LocError`.
- **History:** every layer carries its full slice history. A row is **current
  iff `LRSToDate` is empty** (the owner's rule — confirmed), and the slices
  support **as-of-date reconstruction**: `LRSFromDate <= D < LRSToDate`. The
  layer export (2026-07-20) is 10 months newer than the TSN extract
  (2025-09-08); a fair comparison must either select slices **as-of the TSN
  extract date** or use a same-dated TSN extract.
- **`InventoryItemStartDate` is the DOMAIN effective date** (Excel serial;
  26956 = 1973-10-19 — matches THY eff dates), distinct from the LRS lifecycle
  dates. Do not confuse the two when filtering.
- **City / County Code / Posted Speed cover ALL public roads** (that's why they
  are 481k/825k rows) — the highways build keeps only `RouteID` beginning
  `SHS_`.

## The consolidation model (proven)

Build, per route: select each needed layer's slices as-of the chosen date, keep
single-county spans keyed **county + PM interval** (split the rare cross-county
spans, ≤5 per layer on route 001), union all breakpoints, and emit one output
row per homogeneous stretch with each layer's value painted across it.

**Proof (route 001, ORA+MEN, 502 base THY rows, as-of 2025-09-08):**

| layer column → THY column | agreement |
|---|---|
| Design_Speed → THY_DESIGN_SPEED_AMT | **502/502** |
| Terrain_Type → THY_TERRAIN_CODE | **502/502** |
| Median_Type / Width / Variance → THY_MEDIAN_* | **502/502** ×3 |
| Barrier_Type → THY_MEDIAN_BARRIER_CODE | **502/502** |
| Highway_Group → THY_HIGHWAY_GROUP_CODE | **502/502** |
| SHS_Access_Control → THY_HIGHWAY_ACCESS_CODE | **502/502** |
| Travel_Way_Width_R/L → THY_RT/LT_TRAV_WAY_WIDTH_AMT | **502/502** ×2 |
| Total_Num_Lanes_R/L → THY_RT/LT_LANES_AMT | **502/502** ×2 |
| Shld_Width_Total/Treated_Out_R → THY_RT_O_SHD_TOT/TRT | **502/502** ×2 |
| Shld_Width_Total/Treated_In_R → THY_RT_I_SHD_TOT/TRT | **502/502** ×2 |
| Special_Feature_Type_R → THY_RT_SPEC_FEATURES_CODE | **502/502** (absent span ≡ THY `Z`) |
| Surface_Type_R/L → THY_RT/LT_SURF_TYPE_CODE | **501/502** ×2 (one 0.001-mi boundary sliver at MEN 82.011) |

Traps the proof flushed out (each cost a wrong first result):
- **Join on county+PM, never on the odometers.** THY's `BEGIN/END_OFFSET_AMT`
  is a PM-continued cumulative (route 001 begins at offset 0.129 = its begin
  PM), while the layers' `ODMeasure` is a separately calibrated odometer
  (route-001 end: THY 645.121 vs layer 645.377) and `ARMeasure` is a third
  family (645.377 vs 639.308). Midpoint-matching in OD space silently scrambles
  every fine-grained attribute (28–39% agreement) while coarse ones stay ~85% —
  a false "mostly works" signal.
- **`Total_Num_Lanes`, not `Thru_Num_Lanes`,** is THY's lanes column (100% vs 0%).
- **Layer L/R == THY LT/RT** — no side swap (tested both ways).
- **Boundary slivers:** the two systems can disagree by 0.001 PM on a breakpoint;
  the eventual comparison needs a sliver/tolerance policy, not exact-edge faith.

## Column coverage (74 THY columns)

**Value-proven pulls (on 001)** — the 24 attribute columns in the table above,
plus `THY_TOLL_FOREST_CODE` (mux: **1 = toll** — SHS Tolls spans; verified
geographically: SF 080 Bay Bridge, 160 Antioch, ORA 073/241/261; **2 = forest**
— SHS Forest HWY spans: MPA 140, TRI 003/036, SBD 038, TUO 108/120…; 0 = neither)
and `THY_LANDMARK_SHORT_DESC` (SHS Landmark `Landmarks_Short`, byte-equal spot
check at route-001 begin).

**Mapped, same pattern, not yet value-run** (no reason to doubt, still unproven):
left-side shoulder/special-feature layers (only the R side was run),
`THY_CURB_LANDSCAPE_CODE` ← SHS Curb Landscape, `THY_POPULATION_CODE` ← SHS
Population, `THY_NON_ADD_CODE` ← SHS Non Add Mileage (flag → `N`, default `A`),
`THY_CITY_CODE` ← City (`SHS_` rows only), `THY_RECORD_DATE` + `THY_SEG_ORDER_ID`
← SHS Inv Network Date (`Network_Start_Date`, `SegOrderId`).

**Identity/structural (synthesized by the overlay):** district, county, route,
route suffix, PM prefix/begin/end/suffix, length (= end−begin), the offsets
(cumulate county PM spans along the route — matches THY's convention), and
`THY_PM_SUFFIX_CODE` (mirrors HG for R/L/X rows — counts identical: 1027/965/340).
`THY_BREAK_DESC` is composed: BEG/END/CNTY/DIST are structural (route termini,
county/district lines), R-BR/U-BR ride SHS Route Break, plus equates from
Equation Points (`THY_EQUATE_CODE`).

**Owner decision (2026-07-22): the built file keeps the FULL 74-column THY
header.** A column we cannot source is still PRESENT in the built workbook and
in the comparison sheet — left empty, and explicitly noted as "no TSMIS ArcGIS
source found" (per-column provenance record + the comparison Notes sheet; the
comparison shows it one-sided rather than silently dropping it). Discrepancies
in a correctly-sourced column are the comparison's job to surface, never a
reason to re-source it. Three tiers:

1. **Sourced** — filled from the mapped layer; provenance = layer + column
   (+ FeatureServer URL/layer id from the INDEX sheet).
2. **No TSMIS source** — present + empty + noted (the table below).
3. **TSN-internal bookkeeping** (`THY_ID`, `THY_ELEMENT_ID`, create/update
   user+date, lifecycle `BEGIN/END_DATE`) — present + empty + noted "TSN-internal";
   never fabricated. Exception: `THY_EXTRACT_DATE` is stamped with the build's
   as-of date (that is literally what the column means on our side — flagged in
   the notes so it reads as ours, not TSN's).

**Gaps — cannot be built from the current export:**

| THY columns | why | action |
|---|---|---|
| `THY_ADT_AMT`, `THY_CHANGE_PER_MILE_AMT`, `THY_PROFILE_CODE` | **DELIVERED + source-confirmed (2026-07-22): Traffic Volume Segments.** Not a verbatim pull — a DERIVED family: TVS carries the profile anchors (`AADT`/`AADT_AHEAD`/`AADT_BACK`/`AADT_YEAR` spans) and THY interpolates ADT along them (`CHANGE_PER_MILE` = the slope — `(AHEAD−BACK)/len` matched THY to 4+ decimals on 001, sign convention pending; all 28 THY `P` rows co-locate with TVS spans; `S` = interpolated rows). TVS keeps 3 year-vintages LRS-live concurrently (2022/23/24 as-of Sep-2025), so the consolidator selects latest-year-per-location. `AADT_CODE` is a binary flag, NOT the P/S source. | pin the interpolation + vintage rule at build time (statewide fit, like the block eff dates) |
| `THY_MAINT_SVC_LVL_CODE` | no maintenance layer anywhere in the ~90-layer list | ask the owner whether TSMIS carries it at all |
| `THY_FEDERAL_AID_CODE`, `THY_FA_ROUTE_PREFIX_CODE`, `THY_FA_ROUTE_NAME` | legacy federal-aid system; no layer | likely TSN-legacy-only — owner confirm |
| `THY_NATIONAL_LANDS_CODE`, `THY_SCENIC_FREEWAY_CODE` | no layer | owner confirm |
| the 4 `*_SIG_CHG_IND` + `THY_LAST_SIG_CHG_DATE` | TASAS-side change tracking | likely not derivable — exclude from comparison |
| block eff dates (`THY_LEFT/RIGHT_ROAD_EFF_DATE`, `THY_MEDIAN_EFF_DATE`, `THY_ACCESS_EFF_DATE`) | single-layer item dates agree only 82–96% — the block date is a composite (candidate: max over the block's member layers) | resolve while building; PARTIAL until then |
| bookkeeping (`THY_ID`, `THY_ELEMENT_ID`, create/update user+date, lifecycle dates, `THY_EXTRACT_DATE`) | TSN-internal | synthesize/ignore — never compare |
| `THY_POPULATION_GROUP_CODE`, `THY_FUNCTIONAL_CLASS_CODE` | **all-null in the TSN extract** | nothing to build |

## The layer export list = the IN-APP INPUT CONTRACT (CA HIGHWAYS)

**Owner direction (2026-07-22): the app input is ONE .xlsx PER LAYER**, dropped
into `arcgis_layers/`, re-exported by the owner from this list. **The COMPLETE
library manifest covers ALL THREE clean-road files — 40 layers, in the ArcGIS
contents (screenshot) order** (H = highways, I = intersections, R = ramps;
✅ = already delivered 2026-07-22):

City (H I R) · County Code (H) · Equation Points (H) · IM Complex Intersection
Cross Reference (I) · IM Complex Intersection Influence Segments (I) · IM
Intersection Approach Detail (I) · IM Intersection Approach Segments (I) · IM
Intersection Detail (I) · IM Intersection Point (I) · IM Intersection Route
Table (I) · Route Direction (R) · SHS Access Control (H) · SHS Barrier (H) ·
SHS Curb Landscape (H) · SHS Design Speed (H) · SHS District (H) · SHS Forest
HWY (H) · SHS Highway Group (H I R) · SHS I Shld Width L (H) · SHS I Shld
Width R (H) · SHS Inv Network Date (H I R) · SHS Landmark (H) · SHS Median (H)
· SHS Non Add Mileage (H) · SHS O Shld Width L (H) · SHS O Shld Width R (H) ·
SHS Population (H I R) · SHS Ramp (R) · SHS Ramp Pt (R) · SHS Route Break (H) ·
SHS Special Feature L (H) · SHS Special Feature R (H) · SHS Surface Type L (H)
· SHS Surface Type R (H) · SHS Tolls (H) · SHS Travel Way L (H) · SHS Travel
Way R (H) · Terrain Type (H) · Traffic Volume Ramps (R) ✅ · Traffic Volume
Segments (H I) ✅

The HIGHWAYS consolidator reads its 29; the intersections/ramps sets are staged
for their phases (mapping censused, value proofs pending those phases).

**The delivered per-layer format (2026-07-22 preview — the app input contract):**
a folder of numbered files `NN_<Layer Name>.xlsx` (one sheet, named after the
layer) plus **`00_INDEX.xlsx`** — `Excel File | ArcGIS Layer or Table | Rows
Exported | Fields Exported | ArcGIS Contents Path | Data Source`. The INDEX is
the verification manifest AND the audit-provenance record: the consolidator
verifies each file's row count against it and stamps each output column with
the layer's FeatureServer URL + layer id. One dialect wrinkle: this export
style resolves coded domains to LABELS (`District 7` / `Los Angeles` / `Right`)
where the earlier bundle exports carried CODES (`7` / `LA` / `R`) — the
consolidator normalizes BOTH dialects (fixed 58-county + district + alignment
tables); if the export dialog offers "use domain codes", codes are mildly
preferred but not required.

Export rules: **all rows, all columns** (the history slices are load-bearing —
they enable as-of-date builds); ¹ = all-roads layers, filter `RouteID LIKE
'SHS_%'` at export if ArcGIS allows (≈90% smaller), else the app filters on
load; **filename = layer name** (sheet names truncate at 31 chars, so the
FILENAME is the reliable identity; the `NN_` order prefix is fine). The
consolidator rejects files that match no expected layer name, so the drop-zone
can't accumulate dead weight.

Not needed for highways: Posted Speed Limit (no THY column), SHS Ramp / Ramp Pt
(→ the RAMPS file later), everything in IMLayers.xlsx + Master Intersection AOI
+ IM Roadway Segment (→ the INTERSECTIONS file later), and the 8 empty-in-export
layers (Vertical Grade, Horizontal Curve, 4× RumblStr, Ped Inventory, Bikeway
Inventory — header-only AND unused by THY).

## The other two clean-road files (censused 2026-07-22 — schema-level mapping)

**CA INTERSECTIONS (16,626 rows × 55 `INX_*` cols; current-only — `INX_END_DATE`
all-null)** maps onto the **IM family**: IM Intersection Detail carries the
intersection-level core (name, `Intersection_Geometry`→DESIGN, `Intersection_
Control`→CONTROL, lighted ind, all their begin dates, `Int_Date_Of_Record`→
RECORD_DATE, main+cross route/PM identity, `Cross_AADT`→XSTREET_ADT, Main/Cross
begin dates, the 285-row `INX_X_*` state-crossing block); IM Intersection
Approach Detail + Approach Segments carry the per-leg MAIN_/CROSS_ attributes
(signal mast arm, left/right channelization, flow, lanes, override lengths);
IM Intersection Route Table ties ON/AT routes; the Complex pair covers the
crossing references + influence lengths. Shared with highways: SHS Highway
Group (`INX_HIGHWAY_GROUP`), City (`INX_CITY_CODE`), SHS Population
(`INX_POPULATION_GROUP`), SHS Inv Network Date (`INX_SEG_ORDER_ID` — same
3..361700 id space as THY), Traffic Volume Segments (`INX_MAINLINE_ADT` — the
same interpolation family; note TSN carries NEGATIVE ADTs here, a data quirk
for the comparison to surface). Eff-date-class open item: `INX_LSC_DATE`.
All-null besides END_DATE: `INX_UPDATE_USER/DATE`, `INX_X_ROUTE_SUFFIX_CODE`.

**CA RAMPS (15,410 rows × 32 `RAM_*` cols; `RAM_END_DATE` all-null)** maps onto
**SHS Ramp** (`Ramp_Design`→DESIGN_CODE/DESC — 16 codes incl. Rest Area/Vista
Point/Truck Scale, `Ramp_On_Off_Ind`→ON_OFF {ON,OFF,OTH}, `Area4_Ind`,
`Ramp_Description`/`Ramp_Name`→DESCRIPTION, `InventoryItemStartDate`→
CHANGE_DATE candidate) + **SHS Ramp Pt** (the point identity: district/county/
route/suffix/PM prefix/loc/suffix + ODMeasure→BEGIN_OFFSET, Alignment) +
**Traffic Volume Ramps** (`AADT`→RAM_ADT — a direct point pull, no
interpolation) + the shared City / SHS Population / SHS Highway Group / SHS
Inv Network Date. One derivation to settle at build time:
`RAM_PRIMARY_DIRECTION_CODE` {N,S,E,W} — candidates are SHS Ramp `Side_of_Hwy`
/ Ramp Pt `Alignment` (+ the **Route Direction** layer for the route's cardinal
pair; small, never exported — added to the manifest so no second export run).

**Deliberately NOT in the library** (no clean-road column reads them; the
2026-07-21 bundles hold copies if a build-time question ever needs one):
IM Roadway Segment (810k rows — the largest layer), Master Intersection AOI,
IM Filter Points (never exported), IM Intersection Manager Metadata (2 rows),
MS2 Traffic Station, Posted Speed Limit, the HPMS family, and the 8
empty-in-export SHS layers.

## App integration — SHIPPED v0.29.0 (the ArcGIS tab)

The sketch above became the product on 2026-07-22: `clean_road_layers.py` (the
library substrate: INDEX manifest + dialects + LRS/PM algebra + the overlay),
`clean_highway_columns.py` (the 74-column contract + per-column PROVENANCE
tiers), `consolidate_clean_highway.py` (the build), a live
`tsn_load_clean_road.build_into_highway` (verbatim normalization, marker v1),
`compare_clean_highway_tsn.py` (both flavors via `compare_tsn_common`,
role-gated by the `ArcGIS Build` marker, the no-source/TSN-internal columns as
CONTEXT), and the **ArcGIS tab** (`gui_arcgis_api.py` + `ui-arcgis.js`:
library status vs the 40-layer manifest, Build with an as-of default from the
TSN extract, Compare with formulas+values). `build/check_clean_road.py` pins
all of it on a synthetic library.

**Build-time rules SETTLED against the real 40-layer drop + THY (route 001,
five probe rounds — these supersede the open items above):**

- **Coded attribute domains arrive as `CODE- Label`** ("J- Unpaved Median",
  "N - Non-Add", bare "Z") — `clean_road_layers.code_of` extracts the code.
  Toll/Forest are presence flags ("Toll Roads" / "Yes"); Route Break carries
  "Route Break"/"Route Resume" (+step-down variants) → R-BR/U-BR.
- **THY_DISTRICT_CODE paints from every covering span's own District column**
  (the labels dialect carries it everywhere); the SHS District layer's own
  route-length spans lose middle counties to any two-ended split.
- **Cross-county spans**: end PM < begin PM is their NORMAL shape (the end
  lives in the next county's PM space — never a degenerate row). The split
  walks the county CHAIN: first county to its extent end, odometer-covered
  middle counties WHOLLY, the continuation county from 0 (measured: MON
  101.178 → SCR 0.043 covers SCR from 0.000). Odometers order and apportion,
  never join.
- **The ADT family**: reduce the Traffic Volume spans to the WINNING vintage
  (latest AADT_YEAR, then newest slice) BEFORE the overlay — every vintage's
  edges would otherwise fabricate cuts. The value at a span's BEGIN is its
  **AADT_AHEAD** count (AADT itself is the station's midpoint — anchoring on
  it shifted every row by a constant); slope = (BACK − AHEAD)/length; P marks
  a station row only on a CONTIGUOUS stretch (a span re-entering across a PM
  gap is S — ORA 17.461).
- **No X rows are fabricated.** The HG layer never says X, and TSN skips the
  unconstructed PM ranges entirely (ORA 001 14.057–17.461 has NO row). TSN's
  340 statewide HG=X inventory rows have no layer counterpart and surface
  one-sided in the comparison, by design.
- **Offsets are PM-continued per county**: BEGIN_OFFSET = the row's own begin
  PM plus the prior counties' cumulative largest end PMs (measured: every
  first-county offset IS the begin PM, gaps and prefix handoffs included).
- **City cuts, never values**: the City layer (SHS rows only) contributes row
  BREAKS at city limits; its City_Code carries city NAMES, not TASAS city
  letter codes, so THY_CITY_CODE stays a noted no-source column (ask the
  owner for a TASAS city-code table to upgrade it).
- **Point layers may carry no lifecycle** (Equation Points ships blank
  LRSFromDates) — an undated point is always live; equate points cut rows and
  flag THY_EQUATE_CODE=E; a break/resume point that coincides with an equate
  reads as the equate.
- **Block effective dates**: the OLDEST member layer's InventoryItemStartDate
  is the closest simple composite (~70%; the exact TSN rule remains an open
  question — the comparison surfaces the residual honestly).

Statewide acceptance numbers (the first full build + comparison) live in the
canary bindings doc once blessed; the residual known-diff classes are the
0.001-mi boundary slivers, the eff-date composites, TSN's X rows, and the
±5–10% attribute-coverage holes on multi-county spans whose odometers are
blank (chain-walk needs them).
