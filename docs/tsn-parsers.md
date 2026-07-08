# Per-report TSN formats & comparison schemas

The single home for what we learn about each report's **TSN** source — its file
format, how its columns map to the TSMIS export, the comparison **key**, the
normalization rules, any ditto/roadbed analog, and the **approved sample counts**
that lock the comparator. This is the cross-report sibling of the Highway Log deep
dives (which stay under [highway_log/](highway_log/columns.md)).

**Status (v0.17.0):** the **format + schema rows** below are filled from the **raw
ground-truth files** (the TSN *and* TSMIS version of every report, inspected directly in
the 6.19 set). The **approved counts** ("canary") for each report are locked as its
consolidator + vs-TSN comparator is built and audited flawless; until then a report shows
greyed in the vs-TSN matrix. Process + audit recipe: [v0.17.0-prompt.md](v0.17.0-prompt.md)
and [verification-and-testing.md](verification-and-testing.md).

> **Rule (from [lessons.md](lessons.md)):** consolidate/compare **from raw**, and
> reconcile both files **by hand first** — the schema comes from the data, never a
> guess. The TSMIS website source + the raw files (LOCAL ONLY under
> `C:\Users\Yunus\Downloads\TSMIS\…`) are the ground truth; never commit them.

## Per-report record (fill during 0.17.0)

For each report, record: **TSN format** (PDF/XLSX, per-route vs per-district, single
sheet vs many) · **column → TSMIS mapping** (a table) · **comparison key** (route /
PM / county / composite) · **normalization** (zero-padding, date→ISO, whitespace,
case) · **ditto/roadbed analog** (does the `+`/`++` or roadbed split apply?) ·
**drop folder** (the canonical TSN library `<data_root>/tsn_library/<report>/`, or a
file pick) · **consolidator** module · **comparator** module + `CompareSchema` ·
**golden check** · **approved counts** (the report's own "Route-1 canary" — the first
user-approved sample, never to regress).

### Data organization (verified from the raw 6.19 ground-truth set)

The TSN side is **not** uniformly per-route; each report's format is its own. The TSMIS
side is per-route throughout. This yields **two comparison shapes**:

| Report | TSN format | TSN granularity | TSMIS | Compare shape |
|---|---|---|---|---|
| Ramp Summary | PDF | **statewide aggregate** (one category-count table) | per-route PDF ×126 | **AGGREGATE** |
| Intersection Summary | PDF | **statewide aggregate** | per-route XLSX ×218 | **AGGREGATE** |
| Ramp Detail | XLSX `Sheet 1` | statewide flat (15410 rows × 18 col; 126 rtes) | per-route XLSX ×126 | **FLAT** (route+PM) |
| Intersection Detail | XLSX `Sheet 1` | statewide flat (16626 rows × 36 col; 216 rtes) | per-route XLSX ×218 | **FLAT** (route+PM) |
| Highway Sequence | PDF | **per-district** D01–D12 (~81 pp ea.) | per-route XLSX ×252 | **FLAT** (route+**county**+PM) |
| Highway Log | PDF | per-district D01–D12 | per-route XLSX + PDF | FLAT — already built |

- **AGGREGATE**: TSN is one statewide category-count table; SUM the TSMIS per-route counts
  into a statewide table, then compare **key = category code, value = count**
  (`has_route=False`). The category blocks/codes align across both sides.
- **FLAT**: consolidate the TSMIS per-route files → one workbook; load the TSN side
  (statewide XLSX for RD/ID; the per-district PDF parsed for HSL); compare **key = route + PM**.

> **Familiar TSN-summary layout (v0.17.0 requirement) — SUMMARY reports only.** The TSN
> *Summary* documents (Ramp Summary, Intersection Summary) ARE essentially one category-count
> table — Ramp Summary's Highway Groups / Ramp Types / On-Off / Population blocks; Intersection
> Summary's multi-block equivalent. ONE shared data-driven helper (`scripts/summary_layout.py`)
> renders that arrangement as a familiar-layout sheet on each Summary report's **comparison**
> workbook (via the opt-in `CompareSchema.extra_sheet_writer`), so the comparison reads like the
> source. The Summary **consolidated** workbooks keep their own Combined sheet (already source-
> shaped; Ramp Summary's was extended to the full 16 ramp types, not replaced). **Detail /
> Sequence comparisons (Ramp Detail,
> Intersection Detail, Highway Sequence) are normal comparison worksheets** (like Highway Log) —
> no rollup sheet (TSMIS Ramp Detail has no category columns to roll up anyway). The TSN
> statewide totals (Ramps **15410**, Intersections **16626**) stay useful **verification
> anchors** (e.g. TSN Ramp Detail row count == Ramp Summary total), just not a deliverable sheet.

### Ramp Summary — TSN  *(the v0.17.0 AGGREGATE reference build)*
- **TSMIS side:** per-route PDF ×126, parsed by `consolidate_ramp_summary.parse_pdf` (word-position columns, `COLUMN_SPLIT_X`). `consolidate_ramp_summary` builds a statewide "Combined" total by summing routes. **Schema completed to the full 16 ramp types** (added **P – Dummy Paired**, **V – Dummy, Volume only** in TSN document order) so the TSMIS and TSN schemas match exactly; no 6.19 TSMIS route emits P/V, so those columns total 0 (the consolidator captures them should one ever appear).
- **TSN format:** **PDF, statewide aggregate** (`Ramp Summary Statewide_TSN.pdf`, 3 pages; page 0 = policy boilerplate, page 1 = report params, **page 2 = the data**). One statewide category-count table only. Two-column page (left = Highway Groups / On-Off / Population; right = **16** Ramp Types incl. P & V); footer `Total number of Ramps: 15410`. Parsed by **reusing** the consolidator's geometry helpers (`get_rows_for_column` / `stitch_wrapped_rows` / `match_schema`) — the shared `clean_label` was extended to strip the TSN section-header brackets (`<----…---->`) and the lowercase `Total number of Ramps:` footer (no-ops on the TSMIS page; verified unchanged).
- **Compare shape:** **AGGREGATE** (`has_route=False`). Each side → `{category-slug: count}`; the comparison key is a unique section-namespaced **category** string, the single field is the **count**. The canonical category list (the 16-ramp-type superset + the four other sections + the grand Total) lives in `summary_layout.RAMP_SUMMARY_SPEC` and is shared by the comparator and the familiar sheet. **P and V are TSN-only classifications** → TSMIS contributes 0, so they show as `0 ≠ 122` / `0 ≠ 81` diffs (both-sided, not one-sided). `Ramp Points w/out linework` is a TSMIS-only diagnostic → emitted on the TSMIS side only (lands in *Only in TSMIS* + the familiar sheet footer), not a compared category.
- **Familiar layout:** the comparison workbook gets a **"Summary by Category"** sheet (TSN sections, labels, order; columns *Category | TSMIS | TSN | Δ*) via `summary_layout.make_extra_sheet_writer` (the opt-in `CompareSchema.extra_sheet_writer`). The *consolidated* workbook keeps its own Combined sheet (now 16-type) — it already reads like the source, so it was extended, not replaced.
- **Normalization:** category-code labels matched exactly (the canonical list defines them); the two duplicate `-O OUTSIDE CITY` population rows are disambiguated by parent group in the key. **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/ramp_summary/` (raw statewide PDF → normalized `Category|Count` workbook via `tsn_load_ramp_summary.build_into`) · TSMIS via `consolidate_ramp_summary` · `compare_ramp_summary_tsn` (`"files"` adapter, `header=[Category, Count]`, `key_field=0`, `extra_sheet_writer=summary_layout`) · `check_compare_ramp_summary_tsn.py`. Live in both matrices (`matrix.tsn_comparator_for("ramp_summary")`).
- **Approved counts (CANARY — 6.19 statewide set; never regress):** **31 categories both sides**, only-TSMIS **1** (Ramp Points w/out linework), only-TSN **0**, matched-with-diffs **27**, **diff cells 27**, identical **4** (X-Unconstructed 0/0, A-Frontage 31/31, B-Collector 173/173, L-LoopNoLeft 1332/1332). Totals: TSMIS **15215** vs TSN **15410** (anchor — TSN total == the TSN Ramp Detail row count 15410 ✓). P **0/122**, V **0/81**. Verified 3 ways: independent loader recompute + the compare_core workbook + the familiar sheet (all agree); also via the matrix's normalized-workbook path.

### Ramp Detail — TSN  *(the v0.17.0 reference build)*
- **TSMIS side:** per-route XLSX ×126, sheet `TSAR - Ramp Detail`, consolidated via `consolidate_xlsx_base`. 11 columns; the header row has blank cells so labels are positionally offset — resolve columns by name. Comparison key = **PM** (postmile). Description carries the route prefix, e.g. `001/SB TO/FR RTE 101`.
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **15410 data rows × 18 columns**, **126 routes** (`TSAR - RAMPS DETAIL_TSN_…xlsx`). Columns: `RAM_CONNECTION_ID, RAMP_NANE, LOCATION, PR, PM, PM_SFX, DATE_OF_RECORD, HG, AREA_4, CITY_CODE, POP, ON_OFF, ADT_EFF_YEAR, ADT, RAMP_TYPE, EFF_DATE, DESCRIPTION, SEG_ORDER_ID`. `LOCATION` = `01-DN-101` (district-county-route). `PM` zero-padded ` 000.033`. Dates `1992-09-28 00:00:00`.
- **Comparison key = route + PM.** Route from TSN `LOCATION` (`01-DN-101` → `101`) / TSMIS from filename (`…route_001` → `001`). **VERIFIED: all 272/272** TSMIS route-001 ramps match TSN by normalized PM.

  **Column map (shared compared header; key = PM):**

  | Shared label | TSMIS col | TSN col | Note |
  |---|---|---|---|
  | PM *(key)* | PM | PM | normalize padding to one canon |
  | HG | HG | HG | direct |
  | Area 4 | Area 4 | AREA_4 | direct |
  | City Code | City Code | CITY_CODE | direct |
  | Date of Record | Date of Record | DATE_OF_RECORD | normalize → ISO (`02/25/1976` vs `1992-09-28 00:00:00`) |
  | R/U | R/U | POP | reconcile by hand (TSN has no `R/U`; `POP` is the rural/urban analog) |
  | Description | Description | DESCRIPTION | **compared** — strip TSMIS leading `^\d+/` route prefix, then aligns cell-for-cell |

- **`context_fields` (TSN-only; shown, not diff-counted):** `RAM_CONNECTION_ID, RAMP_NANE, PM_SFX, ON_OFF, ADT_EFF_YEAR, ADT, RAMP_TYPE, EFF_DATE, SEG_ORDER_ID`.
- **Normalization:** PM padding unified; date → ISO; Description prefix stripped; whitespace collapsed. **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/ramp_detail/` (raw XLSX → normalized via `tsn_load_ramp_detail.build_into`) · TSMIS via `consolidate_ramp_detail` (no rollup sheet — a normal worksheet) · `compare_ramp_detail_tsn` (`"files"` adapter, `key_field=PM`, `context_fields=(Ramp Name, On/Off, Ramp Type, ADT)`) · `check_compare_ramp_detail_tsn.py`.
- **Approved counts (CANARY — 6.19 statewide set; never regress):** TSN normalized **15,410 rows / 126 routes** (== Ramp Summary statewide total 15410 ✓). Comparison: **both 15,211**, only-TSMIS **4**, only-TSN **199**, matched-with-diffs **767**, **diff cells 902**, identical **14,444**, routes both **126**. Per-field diffs: HG **364**, Description **218**, City Code **156**, Area 4 **81**, R/U **68**, Date of Record **15**, PR **0**; **context columns 0** (verified on real data — the `context_fields` never count). Verified 3 ways: golden check + full compare-suite + live recompute; route-001 = 272/272 PM-matched.

### Highway Sequence Listing — TSN  *(BUILT + verified — v0.17.0 Phase 3e; the LAST report)*
**Reconciled by hand on the real 6.19 set** (several planning-phase guesses were wrong — corrected below):
the layout is **NOT char-window** (columns are widely spaced, so word-level extraction is safe; only the
2-char flag is split), and the key is **route + COUNTY + PM**, not route + PM.

- **TSMIS side:** per-route XLSX ×252, sheet `Highway Locations`, consolidated via `consolidate_xlsx_base`.
  The per-route header has **two unnamed columns** (a postmile prefix and an equate suffix), so the
  consolidated workbook is read **BY POSITION** (NOT by `(col X)` label): `0 Route · 1 County · 2 City ·
  3 prefix · 4 PM · 5 suffix · 6 HG · 7 FT · 8 Distance To Next Point · 9 Description`. The canonical
  postmile **re-glues** prefix+PM+suffix (`"R" + "000.129" → "R000.129"`; `"050.025" + "E" → "050.025E"`).
- **TSN format:** **PDF, per-district** (`D01..D12 HSL TSN.pdf`; D01 ≈ 81 pp). `OTM22025 Highway Locations`;
  group header `DIST 01 RTE 001 DIR S-N`; per row `CO. | CITY | POSTMILE | G/RF | DIST-TO-NXT | DESCRIPTION`.
  The **G/RF** field is one fused 2-char token = **HG (1st char) + FT (2nd char)** (`"DH"` → HG `D`, FT `H`).
  POSTMILE carries a glued realignment prefix (`R010.179`) and/or equate suffix (`050.025E`). Equate points
  print as a `Rxxx.xxx EQUATES TO` annotation line; TSMIS records the same equate as an `END R REALIGNMENT`
  row at that postmile — the parser **emits the equate line** (county carried from context) so the two pair.
- **Parser** `consolidate_tsn_highway_sequence.py` (writes ONE normalized workbook, sheet
  `Highway Locations (TSN)`, header `[Route, County, PM, City, HG, FT, Distance To Next Point, Description]`):
  word-level extraction with x0-windows `county[0,44) city[44,98) pm[98,168) flag[168,205) dist[205,270)
  desc[270,…)`; lines clustered with `Y_TOLERANCE=3` (a plain `round(top)` splits jittered rows and drops
  them). A route appears across MULTIPLE district PDFs (different counties) — rows accumulate per route.
- **Compare shape:** **FLAT, key = route + COUNTY + PM.** California postmiles are **county-relative** (a route
  restarts at `000.000` in each county it crosses), so the postmile alone is not unique across a route. The
  key is composited via `key_normalizer` → `"COUNTY POSTMILE"` (shown in the key column); **County also stays
  its own visible column**. Landmarks still sharing a (route, county, PM) — e.g. a `COUNTY BEGIN` marker at the
  same postmile — are paired by `compare_core`'s similarity matcher.

  **Column map (shared header; key = route+county+PM):**

  | Shared label | TSMIS (consolidated pos) | TSN (parsed) | Note |
  |---|---|---|---|
  | County *(in key)* | 1 | CO. | **strip trailing period** (TSMIS `LA.`/`SB.`/`SM.`/`SF.`/`CC.`/`DN.`/`ED.`/`SD.`/`SJ.` → `LA`…); else whole counties go one-sided |
  | PM *(key)* | 3+4+5 (prefix+PM+suffix) | POSTMILE | glued canonical form on both sides |
  | FT | 7 | flag[1] | **compared** — genuine feature-type diffs (H↔I, R↔H) |
  | Description | 9 | DESCRIPTION | **compared** — strip TSMIS leading `^\d{1,3}[A-Z]?/` route prefix, collapse whitespace runs |
  | HG | 6 | flag[0] | **context** — TSMIS blanks it for whole counties; TSN always fills U/D |
  | City | 2 | CITY | **context** — TSN assigns a city code far more aggressively than TSMIS |
  | Distance To Next Point | 8 | DIST | **context** — measured to each system's OWN next listed point; TSN lists finer breaks → smaller gap (listing artifact, not a disagreement) |

- **One-sided rows are expected & honest** (same as Highway Log: *"mostly TSN segment breaks and TSMIS
  realignment markers"*) — TSN lists every segment break incl. unnamed ones; TSMIS omits most. The
  S/U **suffixed routes** (`005S`, `008U`, `010S`, …) are separate TSMIS route files but TSN folds them
  into the base route → they read as routes-only-in-TSMIS.
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/highway_sequence/` (raw district
  PDFs → `consolidate_tsn_highway_sequence.build_into`) · TSMIS via `consolidate_highway_sequence` (no rollup —
  a normal worksheet) · `compare_highway_sequence_tsn` (`"files"` adapter, `key_field=PM`,
  `key_normalizer=county|PM`, `context_fields=(HG, City, Distance To Next Point)`, Notes legend indicator) ·
  `check_compare_highway_sequence_tsn.py`.
- **Approved counts (CANARY — 6.19 statewide set; never regress):** TSN normalized **69,758 rows / 263 routes**
  (12 district PDFs); TSMIS consolidated **60,439 rows**. Comparison: union **73,127**, **both 57,070**,
  only-TSMIS **3,369**, only-TSN **12,688**, matched-with-diffs **4,843**, **diff cells 5,538**, identical
  **52,227**; routes both **242**, only-TSMIS **10** (the S/U suffixed), only-TSN **21**. Per-field diffs:
  **FT 699**, **Description 4,839**; **County/City/HG/Distance = 0** (key/context — never count). Verified 3
  ways: golden check + full compare-suite + live independent recompute (which confirmed the engine's
  similarity pairing reduces FT 1,504→699 false order-pairs).

### Intersection Summary — TSN  *(BUILT + verified — v0.17.0 Phase 3b/3c)*
- **TSMIS side:** per-route XLSX ×218, **sheet `Intersection Summary`** (CONFIRMED), 3-col sheet
  (`A`=NUMBER, `B`=CODE). Rows: `TSAR - Intersection Summary` / `Route: NNN` / `Total Intersections = N`,
  then **11 category blocks**, each a `<BLOCK NAME>` header + `NUMBER | CODE` subheader + `count | code-label`
  rows. Block order: HIGHWAY GROUP, RURAL/URBAN/SUBURBAN, INTERSECTION TYPE, LIGHTING TYPE, CONTROL TYPES,
  MAINLINE NUM OF LANES, MAINLINE MASTARM, MAINLINE LEFT/RIGHT CHANNELIZATION, MAINLINE TRAFFIC FLOW. The
  per-route layout is **regular** → a generic block-walk consolidator (`consolidate_intersection_summary.py`,
  Phase 3b) sums each `(block, code-letter)` across the 218 routes.
- **TSN format:** **PDF, statewide aggregate** (`Intersection Summary Statewide_TSN.pdf`, 3 pages; **data on
  page 3**). Same 11 blocks but in a **3-COLUMN** page (left x<190: HIGHWAY GROUP / RURAL-URBAN / INTERSECTION
  TYPE / LIGHTING / NUM OF LANES; middle 190–495: CONTROL TYPES / TRAFFIC FLOW; right x≥495: MASTARM / LEFT
  CHAN / RIGHT CHAN). Parse by **splitting words into the 3 column bands**, then block-walk each band like
  the TSMIS side. Footer `Total Intersections = 16626`.
- **Compare shape:** **AGGREGATE** (the Ramp Summary recipe). Key = **`(block, code-letter)`** — NOT the
  label (TSMIS reworded many labels: "STOP SIGN"→"STOP SIGNS", "FOUR-WAY"→"4-WAY", "...CHAN"→"...CHANNELIZATION").
  Special-case the two blocks whose code-letter isn't unique: RURAL/URBAN (two `-O OUTSIDE CITY` rows —
  disambiguate by parent R-RURAL/U-URBAN, like Ramp Summary's population) and NUM OF LANES (numeric codes 1–8/`+`).
- **⚠ TAXONOMY DIVERGENCE (confirmed on real data):** two blocks use different code SETS between systems —
  the comparison shows the non-shared codes **one-sided** (user decision 2026-06-19; honest, no crosswalk):
  - **CONTROL TYPES:** A–I shared (semantic match by letter); **v0.17.8 folds TSN's legacy signal
    sub-types J/K/L/M/N/P into the single `S - SIGNALIZED` category** (TSMIS collapsed the 6 legacy
    signal codes into one S), so Signalized now compares on **both** sides and **no TSN-only control
    codes remain**; **TSMIS-only O-PED HYBRID BEACON, Q-FLASH BEACON, R-YIELD ALL WAYS** stay one-sided;
    Z + `+` shared.
  - **INTERSECTION TYPE:** F/S/Y/M/T/Z shared; **TSMIS-only R-ROUNDABOUT, C-OTHER CIRCULAR, P-MIDBLOCK PED,
    `+`-NO DATA**.
  - Minor one-sided extras elsewhere: NUM OF LANES `+`, LEFT CHAN `Y-CHANNELIZATION NOT SPECIFIED` (TSMIS-only).
- **Canonical spec:** `summary_layout.INTERSECTION_SUMMARY_SPEC` = the union of both taxonomies (**66
  `(block, code)` categories** after the v0.17.8 signal fold; `_IS_TSN_ONLY == ()`) + grand Total, reusing
  the Ramp Summary AGGREGATE machinery + `extra_sheet_writer`.
- **Normalization:** key on block+code-letter (label text ignored); rural/urban + lanes special-cased.
  **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/intersection_summary/`
  (raw statewide PDF → normalized `Category|Count` via `tsn_load_intersection_summary.build_into`) ·
  `consolidate_intersection_summary` (block-walk category summer; per-route sheet + familiar Combined) ·
  `compare_intersection_summary_tsn` (AGGREGATE; `summary_layout.counts_from_rows` shared with the consolidator;
  one-sided diverged codes via `Cat.sides`) · `check_compare_intersection_summary_tsn.py` +
  `check_consolidate_intersection.py`. Live in both matrices (`matrix.tsn_comparator_for("intersection_summary")`).
- **Approved counts (CANARY — never regress; post v0.17.8 signal fold):** consolidator **218 routes → 16,473**
  (== the Intersection Detail row count ✓). Comparison: **66 categories — 58 both, 8 only-TSMIS, 0 only-TSN**
  (J–P signals folded into the shared `S - SIGNALIZED`; the TSMIS-only O/Q/R + Roundabout/Circular/Midblock
  stay one-sided); TSMIS **16,473** vs TSN **16,626**. Locked offline by `check_compare_intersection_summary_tsn.py`.
  Only-in-TSN = the 6 legacy signal codes CONTROL J–P; Only-in-TSMIS = the 10 new codes (CONTROL R/S/O/Q,
  INTERSECTION-TYPE R/C/P/+, NUM-OF-LANES +, LEFT-CHAN Y). Verified 3 ways (independent loader recompute +
  compare_core workbook + familiar sheet, all agree).

### Intersection Detail — TSN
- **TSMIS side:** per-route XLSX ×218, **sheet `Intersection Detail`** (CONFIRMED), **36 columns** `[P, Post Mile, S, Location, Date of Record, H/G, City Code, R/U, INT Type, INT Eff-Date, Ctrl T, Ctrl Type, Light Eff-Date, Light T/Y, ML Eff-Date, ML S/M, …]`. Free-text **Description** column → formula-injection guard (handled by the shared `consolidate_xlsx` core). **Consolidator DONE (v0.17.0):** `consolidate_intersection_detail` (thin `consolidate_xlsx` wrapper) — verified 218 routes → 16,473 rows.
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **16626 rows × 36 columns**, **216 routes** (`TSAR - INTERSECTION DETAIL_TSN.xlsx`). Columns: `[PP, POST_MILE, LOCATION, DATE_REC, HG, CITY_CODE, RU, EFF_DATE_INT, TY_INT, EFF_DATE_CT, TY_CT, EFF_DATE_LT, LT_TY, EFF_DATE_ML, MAIN_SM, …]`. `LOCATION` = `12 ORA 001` (space-separated). `POST_MILE` zero-padded ` 000.204`; TSMIS `Post Mile` unpadded `0.204`.
- **Compare shape:** **FLAT**, **key = route + PM** (route from `LOCATION` `12 ORA 001` → `001`). Reconciled by hand on PM 0.204 (route 1). **CORRECTED findings (the planning-phase guess was wrong):**
  - **NO value pair-order reversal.** BOTH sides store values in **(eff_date, type)** order. What looked like a reversal is the TSMIS **header being column-shifted** (its "INT Type" label sits over the eff-date value, etc. — like Ramp Detail's shifted header). ⇒ read TSMIS **by position**, not by label.
  - ⚠ **Boolean encoding divergence:** the mastarm / right-channelization / lighting attributes are **`Y/N` on TSN** but **`1/0` on TSMIS** (e.g. mastarm TSN `Y` ↔ TSMIS `1`; no-free-right `N` ↔ `0`). **DECISION (user, 2026-06-20):** NORMALIZE `Y≡1` / `N≡0` on those boolean fields so only genuine changes flag, **with a visible indicator** in the workbook that the normalization is applied (a Legend/Notes sheet + a header note). Apply per-field (NOT global: NUM-OF-LANES uses numeric `1`-`8`, so a blanket `1→Y` would corrupt it). Multi-code fields (left-chan C/N/P/R, traffic-flow N/P/R/W/Z) keep their letter codes.
  - ⚠ **Control-type taxonomy divergence** (same as Intersection Summary): TSN legacy codes (e.g. `P` full-actuated) vs TSMIS new (`S` signalized). **v0.17.8 added a crosswalk** (`_norm_control_type`): the legacy signalized sub-types (J–P) and "signalized" fold to TSMIS's single code **`S`**, so an S-vs-P pairing no longer flags — while a genuinely non-signalized change (A vs B) still does.
  - **`Date of Record`** is a TSMIS refresh date (`21-12-31`) ≠ TSN `DATE_REC` (`73-10-19`). **As of v0.17.8 it IS counted** — `CONTEXT_FIELDS = ()` (compare-everything), so the refresh-vs-record date difference flags like any other column. Eff-dates likewise compared (position-aligned).
  - TSMIS has an extra leading `S` column (pos 2, blank) that TSN lacks → the by-position offset differs from Ramp Detail.
  - ⚠ **Route-suffix label asymmetry** (found in the v0.17.0 audit, 2026-06-20): a route name can carry an alpha route suffix (S/U — the report's "S" column) that **TSN keeps (`12 ORA 210U`) but TSMIS omits (`12 ORA. 210`)** for 7 routes (`005`/`008`/`010`/`014`/`058`/`101`/`178`/`210` family). **DECISION (user, 2026-06-20):** key on the **BASE route** so the same intersection still pairs across the label difference (≈31 intersections that previously dropped to one-sided), AND surface the suffix as a **compared `Route Suffix` column** (renamed from the misnomer "Roadbed" in v0.18.1) so a suffix-only difference is **flagged** (TSN `U` vs TSMIS blank) rather than dropped OR silently merged — *match-and-indicate*. `_split_route` returns `(base, suffix)`. **v0.18.2** also surfaces the suffix in the **Report View** (an `SFX` column frozen next to Route): compared like any cell, but classified *soft* (red on a `U`-vs-blank difference, kept OUT of the per-record Major count) since TSMIS is systematically blank — mirroring how the structural date columns are treated.
- **Normalization (v0.17.8):** PM padding unified; route → **base** (route suffix stripped for the key, surfaced as the `Route Suffix` compared column); 2-digit-year dates → ISO (YY≥30 → 19YY); **`Y↔1 / N↔0` boolean normalization APPLIED** to mastarm / right-chan / lighting (with a **Notes sheet** indicator); a **control-type crosswalk** folds TSN's legacy signalized sub-types (J–P) + "signalized" → TSMIS's `S` (`_norm_control_type`); three **numeric fields** (Main Line Length / Intrte Route / Intrte Postmile) are **zero-pad normalized** (`058≡58`); **`CONTEXT_FIELDS = ()` — every shared column (incl. Date of Record, the 5 cross-street attrs, PR) is COUNTED**, position-aligned; the TSN side is **re-normalized at compare time** (a stale cached library can't mask a normalization change); injection guard on Description. **No ditto.**
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/intersection_detail/` (raw XLSX → normalized via `tsn_load_intersection_detail.build_into`) · `consolidate_intersection_detail` (DONE) · `compare_intersection_detail_tsn` (FLAT; reads TSMIS **by position**, base-route key + `Route Suffix` compared column, **`CONTEXT_FIELDS = ()`** compare-everything, control-type crosswalk → `S`, numeric zero-pad norm, booleans normalized, a **"Report View" replica sheet** via the opt-in `extra_sheet_writer`, Notes sheet) · `check_compare_intersection_detail_tsn.py`. The **PDF edition** reuses this schema + loaders via `compare_intersection_detail_pdf` (`TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL`). Shares the `compare_tsn_common` (`ctc`) substrate. Live in both matrices.
- **Counts (CANARY):** the **v0.17.8 compare-everything** policy (`CONTEXT_FIELDS = ()`) supersedes the v0.17.0 suppressed-context numbers — every shared column now counts, so the statewide diff total rises sharply. The real-data canary is **≈163,310 diff cells (Excel)** (real TSN/TSMIS, local-only ground truth — RM04) — down from v0.18.1's 163,353 after the **v0.18.3 numeric-0 fix**: `_norm_num` now canonicalizes a real numeric 0 to `'0'` instead of blanking it (`str(v or "")` dropped a falsy 0 to `""`), so TSN's numeric-0 intersecting-route postmile reads `'0'` and matches TSMIS's text `'0.000'` — 43 phantom 0-vs-blank Intrte-Postmile cells cleared (on real data the fix touches ONLY that field). The **PDF edition** shifts by the same fix. The **offline lock** is `check_compare_intersection_detail_tsn.py`'s synthetic behavior fixture: the S-crosswalk (S/P → `S`, no diff; non-signalized A vs B → diff), the Y/N↔1/0 boolean norm, Date-of-Record now COUNTED, the 5 cross-street + Date-of-Record diffs counted at PM 0.204, the Report View soft(date + route-suffix)/hard(attribute) split, the **numeric-0→'0' canon** (a real 0 preserved, not blanked), and **one-sided locations rendered as "Only in TSMIS/TSN"** in the Report View (a side-colored band, kept out of the per-record Major/Diffs tally — not a row of field mismatches). TSN normalized **16,626 rows / 216 routes**; TSMIS consolidated **16,473** (218 routes). **Re-blessed 2026-07-03 (v0.18.5):** the D1 falsy-zero eradication (`norm_pm`/`_split_route`/ramp-detail tokens now keep a real numeric 0) + the D2 versioned library + the F1 Report-View rework proved **cell-for-cell IDENTICAL** on the real statewide pair (~2.79M cells, 0 mismatches) — canary unchanged at **163,310 / 677 one-sided**. Since v0.18.5 the library carries a **`tsn_normalization_version` stamp** (from `report_catalog.TSN`, currently **2**) in its consolidation sidecar: an absent/mismatched stamp reads STALE and the matrix/by-day compare paths **auto-rebuild from raw** (`tsn_library.ensure_current`) before reading it — bump the catalog version with ANY normalizer change and re-bless this canary. **v0.19.0:** the Intersection Detail canary was re-blessed AGAIN after the R1/V1 engine refactors (compare_tsn_common skeleton + compare_core's shared `compared_cell`): **2,789,732 cells IDENTICAL, canary unchanged 163,310 / 677**. The **Highway Log** TSN entry is now `normalization_version` **3** (R2: its route-token normalizer reconciled onto `pdf_table_lib.norm_route` — a short suffixed token now pads like TSMIS, '5S'→'005S'; proven identical on all 263 real routes, so the bump is defensive re-keying only).

### Highway Detail — TSN  *(BUILT + verified — v0.20.0, the statewide-bundle reconciliation)*
- **TSMIS side:** per-route XLSX ×252, **sheet `Highway Detail`**, **34 columns** (labels CORRECT as-is — `highway_detail_columns.py` is the SoT; unlike the Highway Log no relabel is needed): `[Post Mile, Length, Date of Rec, HG, AC, Acc-Cont Eff, City, RU, RU Eff, Description, NA, LB Eff…LB IN-TR (9), Med Eff…Med V/WDA (5), RB Eff…RB OT-TR (9)]`. All-text cells; dates `YY-MM-DD`; single digits zero-padded (`'02'`); `Post Mile` glues prefix+mile+marker (`'S000.000'`, `'000.000E'`, `'000.080R'`). **Consolidator:** `consolidate_highway_detail` (thin `consolidate_xlsx` wrapper + tooltips/Legend) — verified 252 routes → **51,243 rows**. The **PDF edition** parses via `consolidate_tsmis_highway_detail_pdf` (PER-PAGE window derivation — each print page is its OWN auto-layout table whose column x-positions vary page to page; wrapped-cell row grouping + hyphen-aware fragment rejoin; cross-page record carry with a date-token furniture guard; document-median fallback for a band-less page, logged).
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **60,083 rows × 56 columns**, **273 routes** (`TSAR - HIGHWAY DETAIL_TSN.xlsx`; REFERENCE_DATE 2025-09-08). Columns: ids (`THY_ID`, `SEG_ORDER_ID`), the DCR block (`DIST/CNTY/RTE/RTE_SFX`), the split postmile (`PP`/`POSTMILE`/`E_IND`), numeric `LENGTH` (raw DB precision), the attributes (named like the TSMIS columns but UNPADDED), the `*`/`Y` change flags (`ACC_SIG/LT_SIG/MED_SIG/RT_SIG`), and the **ADT block** (`BEG_DATE/ADT_AMT/PROFILE/BREAK_DESC/LK_BACK_ADT/CHNGMILE/DVM`) the TSMIS report omits by design. **The `+`/`++` DITTO marks appear here too** (v0.21.0 finding): on independent-alignment rows TSN stores the Highway Log-style ditto TEXT in the numeric roadbed/median columns (e.g. `R_NO_LANES='++'`), and the district prints render it the same — the comparison flags those cells as ordinary text diffs (TSMIS prints real numbers), and the evidence locator's print regexes accept the marks. The **12 TSN district PDFs** were cross-checked against this extract (57,647 records parsed, every shared field ≥99.9% identical; the one exception BEG_DATE ≈88.8% is the ADT reference-year skew — the PDF pull was REF 09/15 vs the extract's 09/08) → **the Excel is the library source**; the PDFs stay reference-only.
- **Compare shape:** **FLAT**, **key = route + CANONICAL Post Mile** (35 shared columns: the key + a derived `PS` column + the 33 remaining; `CONTEXT_FIELDS = ()`). The reconciliations (all locked in `check_compare_highway_detail_tsn.py`; full detail in [comparison-engine.md](comparison-engine.md) §9f-2): the **roadbed-aware key** (TSMIS trailing `R`/`L` ≡ TSN bare PM + `HG∈{R,L}` — routes 282/880S/011/260 went from 0 matched rows to row-for-row); the **equation marker excluded from the key** (compared as `PS` — the systems print `E` on different rows); **NA `'A'`→blank** (TSN prints an explicit add-mileage `A` on 98.7% of matched rows where TSMIS is blank); **zero-pad** (`'02'`≡`'2'`); **Length → the printed 3 decimals** (TSN stores 0.01098); **`M_WID`+`M_VA` → the glued `'14Z'`**; whitespace collapse. **`RU Eff` ↔ `BEG_DATE` is compared BY POSITION and differs on ~99% of rows** — the legacy report prints the ADT begin year in that slot where TSMIS prints the Rural/Urban layer date (structural; Notes-documented; soft in the Report View).
- **Counts (CANARY — the 2026-07-07 statewide dev bundle, local-only ground truth):** TSMIS consolidated **51,243** (252 routes) vs TSN normalized **60,083** (273 routes; ~21 unconstructed routes TSMIS doesn't export) → **48,644 both / 2,599 only-TSMIS / 11,439 only-TSN; 208,596 counted diff cells** (RU Eff alone 48,211 — the structural slot; next: RB/Med/LB Eff ≈16.2k/16.0k/14.2k, Length 7.5k, PS 999, NA 99). **PDF↔Excel on the bundle: 2,484 of 2,487 rows fully identical** (5 differing cells on 3 rows + 3/5 one-sided) — the residue is a REAL export discrepancy (the bundle's PDFs came from a NEWER site build that merges same-postmile record clusters with ' / '-joined descriptions and carries a record the Excel lacks), exactly what the self-check exists to surface.
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/highway_detail/` (raw statewide XLSX → normalized via `tsn_load_highway_detail.build_into`, **`normalization_version=2`** — v2 appends the `TSN District`/`TSN County` SIDECAR columns after the shared header for the visual-evidence generator; the comparison loader slices to the shared width and never sees them) · `consolidate_highway_detail` + `consolidate_tsmis_highway_detail_pdf` · `compare_highway_detail_tsn` (FLAT; Notes + the two-line TASAS **Report View** via `extra_sheet_writer`) + `compare_highway_detail_pdf` (`TSMIS_PDF_VS_TSN` / `TSMIS_PDF_VS_EXCEL`) · `check_compare_highway_detail_tsn.py` + `check_highway_detail_pdf.py` + `check_visual_evidence.py`. Shares the `compare_tsn_common` (`ctc`) substrate. Live in both matrices. **Optional `tsn_library/highway_detail/pdf/`:** the district prints, read only by the evidence images ([comparison-engine.md](comparison-engine.md) §13).

### Highway Log — TSN (reference, already built)
Fully documented elsewhere — this is the recipe the others follow:
- Format + parsers: [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) (TSN char-window parser + the 3 description guards).
- 31 corrected columns: [highway_log/columns.md](highway_log/columns.md).
- The `+`/`++` ditto domain + roadbed split: [highway_log/comparison-study.md](highway_log/comparison-study.md).
- Approved canary: **Route-1 = 299 both / 969 diff cells** (never regress; see
  [verification-and-testing.md](verification-and-testing.md)).
