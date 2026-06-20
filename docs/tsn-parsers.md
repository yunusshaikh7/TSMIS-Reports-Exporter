# Per-report TSN formats & comparison schemas

The single home for what we learn about each report's **TSN** source — its file
format, how its columns map to the TMSIS export, the comparison **key**, the
normalization rules, any ditto/roadbed analog, and the **approved sample counts**
that lock the comparator. This is the cross-report sibling of the Highway Log deep
dives (which stay under [highway_log/](highway_log/columns.md)).

**Status (v0.17.0):** the **format + schema rows** below are filled from the **raw
ground-truth files** (the TSN *and* TMSIS version of every report, inspected directly in
the 6.19 set). The **approved counts** ("canary") for each report are locked as its
consolidator + vs-TSN comparator is built and audited flawless; until then a report shows
greyed in the vs-TSN matrix. Process + audit recipe: [v0.17.0-prompt.md](v0.17.0-prompt.md)
and [verification-and-testing.md](verification-and-testing.md).

> **Rule (from [lessons.md](lessons.md)):** consolidate/compare **from raw**, and
> reconcile both files **by hand first** — the schema comes from the data, never a
> guess. The TMSIS website source + the raw files (LOCAL ONLY under
> `C:\Users\Yunus\Downloads\TSMIS\…`) are the ground truth; never commit them.

## Per-report record (fill during 0.17.0)

For each report, record: **TSN format** (PDF/XLSX, per-route vs per-district, single
sheet vs many) · **column → TMSIS mapping** (a table) · **comparison key** (route /
PM / county / composite) · **normalization** (zero-padding, date→ISO, whitespace,
case) · **ditto/roadbed analog** (does the `+`/`++` or roadbed split apply?) ·
**drop folder** (the canonical TSN library `<data_root>/tsn_library/<report>/`, or a
file pick) · **consolidator** module · **comparator** module + `CompareSchema` ·
**golden check** · **approved counts** (the report's own "Route-1 canary" — the first
user-approved sample, never to regress).

### Data organization (verified from the raw 6.19 ground-truth set)

The TSN side is **not** uniformly per-route; each report's format is its own. The TMSIS
side is per-route throughout. This yields **two comparison shapes**:

| Report | TSN format | TSN granularity | TMSIS | Compare shape |
|---|---|---|---|---|
| Ramp Summary | PDF | **statewide aggregate** (one category-count table) | per-route PDF ×126 | **AGGREGATE** |
| Intersection Summary | PDF | **statewide aggregate** | per-route XLSX ×218 | **AGGREGATE** |
| Ramp Detail | XLSX `Sheet 1` | statewide flat (15410 rows × 18 col; 126 rtes) | per-route XLSX ×126 | **FLAT** (route+PM) |
| Intersection Detail | XLSX `Sheet 1` | statewide flat (16626 rows × 36 col; 216 rtes) | per-route XLSX ×218 | **FLAT** (route+PM) |
| Highway Sequence | PDF | **per-district** D01–D12 (~81 pp ea.) | per-route XLSX ×252 | **FLAT** (route+PM) |
| Highway Log | PDF | per-district D01–D12 | per-route XLSX + PDF | FLAT — already built |

- **AGGREGATE**: TSN is one statewide category-count table; SUM the TMSIS per-route counts
  into a statewide table, then compare **key = category code, value = count**
  (`has_route=False`). The category blocks/codes align across both sides.
- **FLAT**: consolidate the TMSIS per-route files → one workbook; load the TSN side
  (statewide XLSX for RD/ID; the per-district PDF parsed for HSL); compare **key = route + PM**.

> **Familiar TSN-summary layout (v0.17.0 requirement):** the statewide "Summary" visual
> arrangement (Ramp Summary's Highway Groups / Ramp Types / On-Off / Population blocks;
> Intersection Summary's multi-block equivalent) is rendered by ONE shared data-driven
> helper (`scripts/summary_layout.py`) and reused in: each Summary report's consolidated
> "Combined" sheet, a **derived rollup sheet** on each *Detail* consolidated workbook
> (rolled up from the detail's category columns), and a familiar-layout sheet on the Ramp
> and Intersection comparison workbooks. The detail-derived rollup must equal the matching
> Summary report's statewide totals (Ramps **15410**, Intersections **16626**) — a built-in
> engine-free cross-check between the two families.

### Ramp Summary — TSN
- **TSMIS side:** standalone PDF parse (`consolidate_ramp_summary.parse_pdf`, word-position; 14 ramp types × 6 highway groups × on/off × population groups). Per-route PDF ×126; `consolidate_ramp_summary` already builds a statewide "Combined" total by summing routes.
- **TSN format:** **PDF, statewide aggregate** (`Ramp Summary Statewide_TSN.pdf`, 3 pages; page 0 = policy boilerplate, page 1 = report params, page 2 = the data). **No per-route breakdown** — one statewide category-count table only. Same category blocks as TMSIS: Highway Groups, Ramp Types, On/Off Indicator, Population Groups. Footer: `Total number of Ramps: 15410`.
- **Compare shape:** **AGGREGATE.** Sum the 126 TMSIS per-route counts → statewide; compare **key = category code**, value = count (`has_route=False`). The TSN page-2 layout is two columns (left = Highway Groups / On-Off / Population; right = Ramp Types) — parse like `consolidate_ramp_summary.parse_pdf`'s word-position columns (`COLUMN_SPLIT_X`).
- **Normalization:** match category-code labels exactly between the TSN PDF text and the TMSIS code maps, or categories split into one-sided rows. **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / golden check / approved counts:** `tsn_library/ramp_summary/` · TSN parser TBD (Phase 3a) · `compare_ramp_summary_tsn` (Phase 3a) · `check_compare_ramp_summary_tsn.py` · **canary TBD** (anchor: Total Ramps **15410**; equals the Ramp-Detail-derived rollup).

### Ramp Detail — TSN  *(the v0.17.0 reference build)*
- **TSMIS side:** per-route XLSX ×126, sheet `TSAR - Ramp Detail`, consolidated via `consolidate_xlsx_base`. 11 columns; the header row has blank cells so labels are positionally offset — resolve columns by name. Comparison key = **PM** (postmile). Description carries the route prefix, e.g. `001/SB TO/FR RTE 101`.
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **15410 data rows × 18 columns**, **126 routes** (`TSAR - RAMPS DETAIL_TSN_…xlsx`). Columns: `RAM_CONNECTION_ID, RAMP_NANE, LOCATION, PR, PM, PM_SFX, DATE_OF_RECORD, HG, AREA_4, CITY_CODE, POP, ON_OFF, ADT_EFF_YEAR, ADT, RAMP_TYPE, EFF_DATE, DESCRIPTION, SEG_ORDER_ID`. `LOCATION` = `01-DN-101` (district-county-route). `PM` zero-padded ` 000.033`. Dates `1992-09-28 00:00:00`.
- **Comparison key = route + PM.** Route from TSN `LOCATION` (`01-DN-101` → `101`) / TMSIS from filename (`…route_001` → `001`). **VERIFIED: all 272/272** TMSIS route-001 ramps match TSN by normalized PM.

  **Column map (shared compared header; key = PM):**

  | Shared label | TMSIS col | TSN col | Note |
  |---|---|---|---|
  | PM *(key)* | PM | PM | normalize padding to one canon |
  | HG | HG | HG | direct |
  | Area 4 | Area 4 | AREA_4 | direct |
  | City Code | City Code | CITY_CODE | direct |
  | Date of Record | Date of Record | DATE_OF_RECORD | normalize → ISO (`02/25/1976` vs `1992-09-28 00:00:00`) |
  | R/U | R/U | POP | reconcile by hand (TSN has no `R/U`; `POP` is the rural/urban analog) |
  | Description | Description | DESCRIPTION | **compared** — strip TMSIS leading `^\d+/` route prefix, then aligns cell-for-cell |

- **`context_fields` (TSN-only; shown, not diff-counted):** `RAM_CONNECTION_ID, RAMP_NANE, PM_SFX, ON_OFF, ADT_EFF_YEAR, ADT, RAMP_TYPE, EFF_DATE, SEG_ORDER_ID`.
- **Normalization:** PM padding unified; date → ISO; Description prefix stripped; whitespace collapsed. **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / golden check / approved counts:** `tsn_library/ramp_detail/` (raw XLSX → normalized via `tsn_load_ramp_detail`) · TMSIS via `consolidate_ramp_detail` (+ derived rollup sheet) · `compare_ramp_detail_tsn` (`"files"` adapter, key_field=PM, `context_fields`, `extra_sheet_writer`) · `check_compare_ramp_detail_tsn.py` · **canary TBD** (anchor: route-001 = 272/272 PM-matched).

### Highway Sequence Listing — TSN
- **TSMIS side:** per-route XLSX ×252, sheet `Highway Locations`, 9 columns `[County, City, (unnamed=R/U prefix), PM, (unnamed), HG, FT, Distance To Next Point, Description]`, consolidated via `consolidate_xlsx_base`. Comparison key = **PM**. Some columns are **unnamed** → `compare_env` labels them `(col X)`; the TSN side must align/label the same way.
- **TSN format:** **PDF, per-district** (`D01..D12 HSL TSN.pdf`; D01 ≈ 81 pages). Report header `OTM22025 Highway Locations`, `Ref Dt`, `DIST 01 RTE 001 DIR S-N`. Char-window data layout per row: `CO. | CITY | POSTMILE | G/RF (HG+FT) | DISTANCE TO NXT POINT | DESCRIPTION`. PM carries **prefix/suffix markers** (`R010.179`, `010.637E`, `EQUATES TO`) — roadbed/equate analog, handle like the HL parser. Routes appear sequentially within each district file.
- **Compare shape:** **FLAT**, **key = route + PM**. Needs a **new char-window parser** `consolidate_tsn_highway_sequence.py` modeled on `consolidate_tsn_highway_log` (calibrate `COLUMN_WINDOWS` against the real D01–D12). ⚠ Riskiest fan-out item.
- **Normalization:** PM padding + prefix/suffix markers; whitespace; County repeats down rows (key on PM, not County). **Ditto/roadbed:** PM-marker equate handling (mirror HL).
- **Drop folder / consolidator / comparator / golden check / approved counts:** `tsn_library/highway_sequence/` (raw district PDFs → consolidated) · `consolidate_tsn_highway_sequence` (Phase 3d) · `compare_highway_sequence_tsn` · `check_tsn_highway_sequence_parse.py` + `check_compare_highway_sequence_tsn.py` · **canary TBD.**

### Intersection Summary — TSN
- **TSMIS side:** per-route XLSX ×218, **sheet `Intersection Summary`** (CONFIRMED), category-count layout: rows `TSAR - Intersection Summary` / `Route: NNN` / `Total Intersections = N` / then category blocks each `NUMBER | CODE` (HIGHWAY GROUP, RURAL/URBAN/SUBURBAN, INTERSECTION TYPE, LIGHTING TYPE, …). **No consolidator exists yet** — build `consolidate_intersection_summary.py` (Phase 3b).
- **TSN format:** **PDF, statewide aggregate** (`Intersection Summary Statewide_TSN.pdf`, 3 pages; data on page 2). Multi-block category-count layout: HIGHWAY GROUP, CONTROL TYPES, MAINLINE MASTARM, RURAL/URBAN/SUBURBAN, MAINLINE LEFT/RIGHT CHANNELIZATION, INTERSECTION TYPE, MAINLINE NUM OF LANES, MAINLINE TRAFFIC FLOW, LIGHTING TYPE. Footer `Total Intersections = 16626`.
- **Compare shape:** **AGGREGATE.** Sum the 218 TMSIS per-route counts → statewide; compare **key = category code**, value = count. ⚠ category-label alignment between PDF and schema codes.
- **Normalization:** exact category-code label matching. **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / golden check / approved counts:** `tsn_library/intersection_summary/` · `consolidate_intersection_summary` (+ shared `summary_layout`) · `compare_intersection_summary_tsn` (Phase 3c) · `check_compare_intersection_summary_tsn.py` · **canary TBD** (anchor: Total Intersections **16626**; equals the Intersection-Detail-derived rollup).

### Intersection Detail — TSN
- **TSMIS side:** per-route XLSX ×218, **sheet `Intersection Detail`** (CONFIRMED), **36 columns** `[P, Post Mile, S, Location, Date of Record, H/G, City Code, R/U, INT Type, INT Eff-Date, Ctrl T, Ctrl Type, Light Eff-Date, Light T/Y, ML Eff-Date, ML S/M, …]`. Free-text **Description** column → **formula-injection guard required**. **No consolidator exists yet** — build `consolidate_intersection_detail.py` (Phase 3b).
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **16626 rows × 36 columns**, **216 routes** (`TSAR - INTERSECTION DETAIL_TSN.xlsx`). Columns: `[PP, POST_MILE, LOCATION, DATE_REC, HG, CITY_CODE, RU, EFF_DATE_INT, TY_INT, EFF_DATE_CT, TY_CT, EFF_DATE_LT, LT_TY, EFF_DATE_ML, MAIN_SM, …]`. `LOCATION` = `12 ORA 001` (space-separated). `POST_MILE` zero-padded ` 000.204`; TMSIS `Post Mile` unpadded `0.204`.
- **Compare shape:** **FLAT**, **key = route + PM** (route from `LOCATION` `12 ORA 001` → `001`). ⚠ **Two reconciliation traps:** (1) **pair-order reversal** — TSN orders each attribute as `(EFF_DATE_x, TY_x)` but TMSIS as `(Type, Eff-Date)`; the loader must reorder TSN pairs before projecting. (2) **`Date of Record` is a TMSIS refresh date** (e.g. `21-12-31`) ≠ TSN `DATE_REC` (`73-10-19`) — **exclude from diff counting** (context only). Eff-dates align (small real diffs expected).
- **Normalization:** PM padding unified; two-digit-year dates normalized; whitespace; injection guard on Description. **No ditto/roadbed** (but watch the pair reordering).
- **Drop folder / consolidator / comparator / golden check / approved counts:** `tsn_library/intersection_detail/` (raw XLSX → normalized) · `consolidate_intersection_detail` (+ derived Intersection-Summary rollup sheet) · `compare_intersection_detail_tsn` (Phase 3e; `context_fields` incl. Date of Record, `extra_sheet_writer`) · `check_compare_intersection_detail_tsn.py` · **canary TBD.**

### Highway Log — TSN (reference, already built)
Fully documented elsewhere — this is the recipe the others follow:
- Format + parsers: [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) (TSN char-window parser + the 3 description guards).
- 31 corrected columns: [highway_log/columns.md](highway_log/columns.md).
- The `+`/`++` ditto domain + roadbed split: [highway_log/comparison-study.md](highway_log/comparison-study.md).
- Approved canary: **Route-1 = 299 both / 969 diff cells** (never regress; see
  [verification-and-testing.md](verification-and-testing.md)).
