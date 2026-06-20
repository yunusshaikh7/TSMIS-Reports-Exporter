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
| Highway Sequence | PDF | **per-district** D01–D12 (~81 pp ea.) | per-route XLSX ×252 | **FLAT** (route+PM) |
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

### Highway Sequence Listing — TSN
- **TSMIS side:** per-route XLSX ×252, sheet `Highway Locations`, 9 columns `[County, City, (unnamed=R/U prefix), PM, (unnamed), HG, FT, Distance To Next Point, Description]`, consolidated via `consolidate_xlsx_base`. Comparison key = **PM**. Some columns are **unnamed** → `compare_env` labels them `(col X)`; the TSN side must align/label the same way.
- **TSN format:** **PDF, per-district** (`D01..D12 HSL TSN.pdf`; D01 ≈ 81 pages). Report header `OTM22025 Highway Locations`, `Ref Dt`, `DIST 01 RTE 001 DIR S-N`. Char-window data layout per row: `CO. | CITY | POSTMILE | G/RF (HG+FT) | DISTANCE TO NXT POINT | DESCRIPTION`. PM carries **prefix/suffix markers** (`R010.179`, `010.637E`, `EQUATES TO`) — roadbed/equate analog, handle like the HL parser. Routes appear sequentially within each district file.
- **Compare shape:** **FLAT**, **key = route + PM**. Needs a **new char-window parser** `consolidate_tsn_highway_sequence.py` modeled on `consolidate_tsn_highway_log` (calibrate `COLUMN_WINDOWS` against the real D01–D12). ⚠ Riskiest fan-out item.
- **Normalization:** PM padding + prefix/suffix markers; whitespace; County repeats down rows (key on PM, not County). **Ditto/roadbed:** PM-marker equate handling (mirror HL).
- **Drop folder / consolidator / comparator / golden check / approved counts:** `tsn_library/highway_sequence/` (raw district PDFs → consolidated) · `consolidate_tsn_highway_sequence` (Phase 3d) · `compare_highway_sequence_tsn` · `check_tsn_highway_sequence_parse.py` + `check_compare_highway_sequence_tsn.py` · **canary TBD.**

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
  - **CONTROL TYPES:** A–I shared (semantic match by letter); **TSN-only J/K/L/M/N/P** (signal pretimed/
    semi-/full-actuated, 2-phase/multi-phase); **TSMIS-only R-YIELD ALL WAYS, S-SIGNALIZED, O-PED HYBRID
    BEACON, Q-FLASH BEACON**; Z + `+` shared. (TSMIS collapsed the 6 legacy signal codes into one S-SIGNALIZED.)
  - **INTERSECTION TYPE:** F/S/Y/M/T/Z shared; **TSMIS-only R-ROUNDABOUT, C-OTHER CIRCULAR, P-MIDBLOCK PED,
    `+`-NO DATA**.
  - Minor one-sided extras elsewhere: NUM OF LANES `+`, LEFT CHAN `Y-CHANNELIZATION NOT SPECIFIED` (TSMIS-only).
- **Canonical spec:** `summary_layout.INTERSECTION_SUMMARY_SPEC` = the **union** of both taxonomies (~72
  `(block, code)` categories) + grand Total, reusing the Ramp Summary AGGREGATE machinery + `extra_sheet_writer`.
- **Normalization:** key on block+code-letter (label text ignored); rural/urban + lanes special-cased.
  **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/intersection_summary/`
  (raw statewide PDF → normalized `Category|Count` via `tsn_load_intersection_summary.build_into`) ·
  `consolidate_intersection_summary` (block-walk category summer; per-route sheet + familiar Combined) ·
  `compare_intersection_summary_tsn` (AGGREGATE; `summary_layout.counts_from_rows` shared with the consolidator;
  one-sided diverged codes via `Cat.sides`) · `check_compare_intersection_summary_tsn.py` +
  `check_consolidate_intersection.py`. Live in both matrices (`matrix.tsn_comparator_for("intersection_summary")`).
- **Approved counts (CANARY — 6.19 statewide set; never regress):** consolidator **218 routes → 16,473**
  (== the Intersection Detail row count ✓). Comparison: **72 union categories — 56 both, 10 only-TSMIS, 6 only-TSN**;
  **52 diff cells**, **4 identical** (CONTROL +/Z, HIGHWAY GROUP X, LIGHTING +); TSMIS **16,473** vs TSN **16,626**.
  Only-in-TSN = the 6 legacy signal codes CONTROL J–P; Only-in-TSMIS = the 10 new codes (CONTROL R/S/O/Q,
  INTERSECTION-TYPE R/C/P/+, NUM-OF-LANES +, LEFT-CHAN Y). Verified 3 ways (independent loader recompute +
  compare_core workbook + familiar sheet, all agree).

### Intersection Detail — TSN
- **TSMIS side:** per-route XLSX ×218, **sheet `Intersection Detail`** (CONFIRMED), **36 columns** `[P, Post Mile, S, Location, Date of Record, H/G, City Code, R/U, INT Type, INT Eff-Date, Ctrl T, Ctrl Type, Light Eff-Date, Light T/Y, ML Eff-Date, ML S/M, …]`. Free-text **Description** column → formula-injection guard (handled by the shared `consolidate_xlsx` core). **Consolidator DONE (v0.17.0):** `consolidate_intersection_detail` (thin `consolidate_xlsx` wrapper) — verified 218 routes → 16,473 rows.
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **16626 rows × 36 columns**, **216 routes** (`TSAR - INTERSECTION DETAIL_TSN.xlsx`). Columns: `[PP, POST_MILE, LOCATION, DATE_REC, HG, CITY_CODE, RU, EFF_DATE_INT, TY_INT, EFF_DATE_CT, TY_CT, EFF_DATE_LT, LT_TY, EFF_DATE_ML, MAIN_SM, …]`. `LOCATION` = `12 ORA 001` (space-separated). `POST_MILE` zero-padded ` 000.204`; TSMIS `Post Mile` unpadded `0.204`.
- **Compare shape:** **FLAT**, **key = route + PM** (route from `LOCATION` `12 ORA 001` → `001`). ⚠ **Two reconciliation traps:** (1) **pair-order reversal** — TSN orders each attribute as `(EFF_DATE_x, TY_x)` but TSMIS as `(Type, Eff-Date)`; the loader must reorder TSN pairs before projecting. (2) **`Date of Record` is a TSMIS refresh date** (e.g. `21-12-31`) ≠ TSN `DATE_REC` (`73-10-19`) — **exclude from diff counting** (context only). Eff-dates align (small real diffs expected).
- **Normalization:** PM padding unified; two-digit-year dates normalized; whitespace; injection guard on Description. **No ditto/roadbed** (but watch the pair reordering).
- **Drop folder / consolidator / comparator / golden check / approved counts:** `tsn_library/intersection_detail/` (raw XLSX → normalized) · `consolidate_intersection_detail` (+ derived Intersection-Summary rollup sheet) · `compare_intersection_detail_tsn` (Phase 3e; `context_fields` incl. Date of Record, `extra_sheet_writer`) · `check_compare_intersection_detail_tsn.py` · **canary TBD.**

### Highway Log — TSN (reference, already built)
Fully documented elsewhere — this is the recipe the others follow:
- Format + parsers: [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) (TSN char-window parser + the 3 description guards).
- 31 corrected columns: [highway_log/columns.md](highway_log/columns.md).
- The `+`/`++` ditto domain + roadbed split: [highway_log/comparison-study.md](highway_log/comparison-study.md).
- Approved canary: **Route-1 = 299 both / 969 diff cells** (never regress; see
  [verification-and-testing.md](verification-and-testing.md)).
