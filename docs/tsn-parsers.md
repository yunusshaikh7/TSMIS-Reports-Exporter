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

> **Comparison-perfection reset (2026-07-12):** this long-lived document contains
> historical implementation/count notes that are useful evidence but no longer own
> acceptance. Start with the owner dashboard
> [planning/comparison-perfection/archive/comparison-perfection-project.md](planning/comparison-perfection/archive/comparison-perfection-project.md)
> and exact source record
> [planning/comparison-perfection/comparison-phase4-tsn-source-rebaseline.md](planning/comparison-perfection/comparison-phase4-tsn-source-rebaseline.md).
> Any `route + PM`, `never regress`, or approved-count wording below describes a prior
> implementation/canary until its source-first gate is re-promoted. Raw TSN proves that
> accepted pairing identity must retain county. Exact D4 tuples are HSL
> route+county+full PM, Ramp `(Route, County, norm_pm(PM))`, and Intersection
> `(base Route, County, complete PP, numeric Post Mile)`. Ramp PR/PM_SFX and
> Intersection Route suffix/PR/District/explicit Route/physical `S` remain separately
> asserted/conserved fields. Highway Detail TSN needs route+county+complete PM while its
> vendor-pending TSMIS Excel flavor remains blocked without an authoritative county
> derivation. Highway Log's raw county claim is currently discarded and is being
> re-censused rather than presumed exempt.
>
> TSN XLSX/PDF pairs are semantic, source-date-aware oracles. Different IT export times
> may produce an exact explainable delta; they do not permit silent normalization. The
> explicit Excel-row-to-PDF record/category/section map also owns evidence location and
> layered Report View placement/counts.

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
| Intersection Summary | PDF | **statewide aggregate** | current per-route XLSX ×217 (legacy 6.19 ×218) | **AGGREGATE** |
| Ramp Detail | XLSX `Sheet 1` | statewide flat (15410 rows × 18 col; 126 rtes) | per-route XLSX ×126 | **FLAT** (D4 key: route+county+normalized PM; PR/PM_SFX asserted; current family integration red) |
| Intersection Detail | XLSX `Sheet 1` | statewide flat (16626 rows × 36 col; 216 route+suffix tokens / 211 bases) | per-route XLSX ×218 | **FLAT** (required: base route+county+PP+PM; current family integration red) |
| Highway Sequence | PDF | **per-district**, exactly one internally claimed D01–D12 | per-route XLSX ×252 | **FLAT** (route+**county**+complete PM) |
| Highway Log | PDF | exactly one internally claimed D01–D12 | per-route XLSX + PDF | **FLAT** — admission green; normalized county retention/identity integration still red |
| Highway Detail | XLSX `Sheet 1` | statewide flat (60,083 rows × 56 col; 273 routes) | per-route XLSX + PDF | **FLAT** — TSN route+county+complete PM; TSMIS Excel county derivation blocked |

- **AGGREGATE**: TSN is one statewide category-count table; SUM the TSMIS per-route counts
  into a statewide table, then compare **key = category code, value = count**
  (`has_route=False`). The category blocks/codes align across both sides.
- **FLAT**: consolidate the TSMIS per-route files → one workbook; load the TSN side
  (statewide XLSX for RD/ID/HD; per-district PDFs for HSL/HL); compare on the complete
  source-backed physical identity above. A PM-only implementation is a known defect,
  even when duplicate similarity happens to reproduce historical counts.

The two district-PDF builders fail closed unless every document internally claims one
consistent district and the set is exactly one each of D01-D12. A Dnn filename may
corroborate but never supply identity; filename/document disagreement fails. Failed or
missing district members do not publish partial TSN comparison truth.

Every one of the seven generated TSN libraries is reusable only when its persisted
canonical raw content manifest still matches the exact current member names and bytes;
mtime/cardinality alone never certifies freshness. District builders parse captured PDF
bytes. The five statewide builders parse a private captured copy of their sole raw
XLSX/PDF and re-hash the live source after projection and inside the atomic commit guard.
A transient rewrite cannot mix parser generations. Persistent or pre-commit mutation
preserves the previous normalized workbook and returns an error. Mutation in the
narrow predicate-to-replace window is detected immediately afterward and cannot return
certified success; it may leave one complete captured snapshot at the output path, but
that snapshot is stale/untrusted and cannot be reused against the changed raw source.
The library wrapper also re-reads the required normalization-version/raw-manifest
sidecar before reporting TSN build success. Matrix consumers require the canonical
artifact to be certifiably current; missing/unreadable/ambiguous raw inputs and
legacy/foreign consolidated workbooks stop comparison instead of falling through.

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

### Ramp Summary — TSN  *(Stage-8 source-bound contract; current comparator remains product-red)*
- **TSMIS side:** the accepted 2026-07-09 source set has per-route PDF **and XLSX** exports for all 126 exact ordered routes. All **126 × 30 = 3,780** report values agree across those two representations. `consolidate_ramp_summary.parse_pdf` parses the PDFs by word-position columns (`COLUMN_SPLIT_X`) and the consolidator builds a statewide "Combined" total by summing routes. The implementation schema includes the full 16 TSN ramp types, including **P – Dummy Paired** and **V – Dummy, Volume only**, but the authentic TSMIS **Summary representation does not emit P/V at all**. This absence must not be normalized into zero. The same-pull Ramp Detail XLSX/PDF sources contain 22 genuine P/V records (P=2, V=20), proving that the missing Summary classifications are a structural representation gap rather than factual zeroes.
- **TSN format:** **PDF, statewide aggregate** (`Ramp Summary Statewide_TSN.pdf`, 3 pages; page 0 = policy boilerplate, page 1 = report params, **page 2 = the data**). One statewide category-count table only. Two-column page (left = Highway Groups / On-Off / Population; right = **16** Ramp Types incl. P & V); footer `Total number of Ramps: 15410`. Parsed by **reusing** the consolidator's geometry helpers (`get_rows_for_column` / `stitch_wrapped_rows` / `match_schema`) — the shared `clean_label` was extended to strip the TSN section-header brackets (`<----…---->`) and the lowercase `Total number of Ramps:` footer (no-ops on the TSMIS page; verified unchanged).
- **Accepted compare shape:** **AGGREGATE** (`has_route=False`). Each side → `{category-slug: count}`; the comparison key is a unique section-namespaced **category** string, and the single field is the **count**. The business comparison universe is **29 shared categories + P and V as 2 Only-in-TSN categories**. `Ramp Points w/out linework` is a TSMIS display/provenance metric: show its value in the familiar sheet footer, but exclude it from comparison membership and verdicts. The current generic comparison path is product-red because it fabricates TSMIS zeroes for P/V and injects the no-linework footer as Only-in-TSMIS; the familiar sheet's explanatory prose already promises the accepted one-sided/display-only behavior.
- **Familiar layout:** the comparison workbook gets a **"Summary by Category"** sheet (TSN sections, labels, order; columns *Category | TSMIS | TSN | Δ*) via `summary_layout.make_extra_sheet_writer` (the opt-in `CompareSchema.extra_sheet_writer`). The *consolidated* workbook keeps its own Combined sheet (now 16-type) — it already reads like the source, so it was extended, not replaced.
- **Normalization:** category-code labels matched exactly (the canonical list defines them); the two duplicate `-O OUTSIDE CITY` population rows are disambiguated by parent group in the key. **No ditto/roadbed.**
- **Drop folder / consolidator / comparator / checks:** `tsn_library/ramp_summary/` (raw statewide PDF → normalized `Category|Count` workbook via `tsn_load_ramp_summary.build_into`) · TSMIS via `consolidate_ramp_summary` · `compare_ramp_summary_tsn` (`"files"` adapter, `header=[Category, Count]`, `key_field=0`, `extra_sheet_writer=summary_layout`) · permanent source-bound gate `build/check_phase8_ramp_summary_comparison.py`. `check_compare_ramp_summary_tsn.py` remains useful as a legacy/current-product behavior fixture, but it is not the business oracle. Live in both matrices (`matrix.tsn_comparator_for("ramp_summary")`).
- **Accepted Stage-8 counts (2026-07-09 All Reports 7.9 pull):** **29 categories both sides**, only-TSMIS **0**, only-TSN **2** (P/V), differing shared **24**, identical shared **5**. TSMIS Total **15,216** vs TSN **15,410** (TSN − TSMIS = **194**); `Ramp Points w/out linework` = **59 display-only**. The exact ordered TSMIS-minus-TSN comparison digest is `a3cbf7528aa66989f08a0d28efd8ba0e4588b8e3675ef108b0b791fdd35a2d63`.
- **Historical 6/19 production evidence — superseded, never use as the oracle:** 31 both, 1 only-TSMIS, 0 only-TSN, 27 diff, 4 identical, TSMIS 15,215 vs TSN 15,410, P `0/122`, V `0/81`. Those figures remain diagnostic evidence of the old/current normalization behavior; the accepted source-bound contract above replaces them.

### Ramp Detail — TSN  *(accepted Stage-8 source contract; current product red)*
- **TSMIS side:** per-route XLSX ×126, sheet `TSAR - Ramp Detail`, consolidated via `consolidate_xlsx_base`. 11 columns; the header row has blank cells so labels are positionally offset — read the exact positions. `Location` carries district, county, and route (`12-SD-005`), while Description can carry an outer route prefix such as `001/SB TO/FR RTE 101`.
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **15410 data rows × 18 columns**, **126 routes** (`TSAR - RAMPS DETAIL_TSN_…xlsx`). Columns: `RAM_CONNECTION_ID, RAMP_NANE, LOCATION, PR, PM, PM_SFX, DATE_OF_RECORD, HG, AREA_4, CITY_CODE, POP, ON_OFF, ADT_EFF_YEAR, ADT, RAMP_TYPE, EFF_DATE, DESCRIPTION, SEG_ORDER_ID`. `LOCATION` = `01-DN-101` (district-county-route). `PM` zero-padded ` 000.033`. Dates `1992-09-28 00:00:00`.
- **Accepted identity = route + County + normalized PM.** California postmiles restart by county. Route comes from both TSN `LOCATION` and the TSMIS filename/Location; County comes from each side's `LOCATION`. The raw TSN corpus contains **81** weak `(Route, PM)` keys spanning **163** county identities, so the product's current Route+PM key is not acceptable even where this edition happens to pair to the same counts. `PR` and `PM_SFX` remain separately asserted source facts, not key components.

  **Accepted source field map (current product still omits District/County):**

  | Shared label | TSMIS col | TSN col | Note |
  |---|---|---|---|
  | District | Location | LOCATION | **compared**; exact current disagreement at `005/SD/72.366` is TSMIS 12 vs TSN 11 |
  | County *(key)* | Location | LOCATION | preserve visibly and include in D4 identity |
  | PM *(key)* | PM | PM | strict decimal normalization to one three-place canon |
  | PR | PR | PR | direct, separately asserted; zero current differences |
  | HG | HG | HG | direct |
  | Area 4 | Area 4 | AREA_4 | direct |
  | City Code | City Code | CITY_CODE | direct |
  | Date of Record | Date of Record | DATE_OF_RECORD | normalize → ISO (`02/25/1976` vs `1992-09-28 00:00:00`) |
  | R/U | R/U | POP | reconcile by hand (TSN has no `R/U`; `POP` is the rural/urban analog) |
  | Description | Description | DESCRIPTION | strip a leading numeric prefix only when it is the TSMIS outer route; a different numeric prefix is authoritative source data |

- **Raw-only/current-context claims:** the 18-column source also carries `RAM_CONNECTION_ID`, `RAMP_NANE`, `PM_SFX`, `ON_OFF`, `ADT_EFF_YEAR`, `ADT`, `RAMP_TYPE`, `EFF_DATE`, and `SEG_ORDER_ID`. Every field must be conserved or explicitly dispositioned. On/Off and Ramp Type are compared when the TSMIS PDF supplies them; Ramp Name and ADT remain context on current product legs. `PM_SFX`, `ADT_EFF_YEAR`, and `EFF_DATE` are source/evidence claims currently omitted by normalization/comparison under CMP-AUD-133.
- **Normalization contract:** strict PM/date normalization; preserve District/County; retain a Description numeric prefix unless it is proven to be the same outer route; classify whitespace/render equivalence without changing cross-system source data. **No ditto/roadbed.** Current normalization wrongly removes 15 different-route/source prefixes (CMP-AUD-135).
- **Drop folder / consolidator / comparator / permanent gates:** `tsn_library/ramp_detail/` (raw XLSX → normalized via `tsn_load_ramp_detail.build_into`) · TSMIS via `consolidate_ramp_detail` · current comparator `compare_ramp_detail_tsn` · legacy/product fixture `check_compare_ramp_detail_tsn.py` · source business oracle `build/check_phase8_ramp_detail_comparison.py` (36 assertions). The product fixture is not authority for the accepted identity or field universe.
- **Accepted Stage-8 current-source counts (2026-07-09 TSMIS / exact TSN chain):** both TSMIS forms have 15,216 rows; raw TSN has 15,410. Excel-vs-TSN is **15,212 paired, 4/198 one-sided, 14,471 identical, 741 differing rows, 847 differing cells**: District 1, Date 15, HG 364, Area 4 58, City 156, R/U 68, Description 185, PR 0. PDF-vs-TSN source truth is **15,212 paired, 4/198 one-sided, 14,438 identical, 774 differing rows, 998 differing cells**, adding On/Off 95 and Ramp Type 60 while Description is 181. The accepted oracle/result hashes are recorded in `planning/comparison-perfection/comparison-canary-bindings.md`.
- **Historical 6.19 evidence — superseded, never re-bless current truth from it:** both 15,211; 4/199 one-sided; 767 differing rows; 902 cells; 14,444 identical. It remains a versioned regression fixture only.
- **Normalization v3 (v0.26.0):** the normalized library appends the **TSN District/County sidecar** columns split from `LOCATION`. Evidence consumes them, but the current comparator slices them away. That behavior is now explicitly product-red under CMP-AUD-185: the exact District 12-vs-11 source disagreement is rendered fully identical.

### Ramp Detail (PDF) — the TSMIS print edition  *(fully integrated v0.26.0; censused on `All Reports 7.9`)*
- **TSMIS print format:** landscape Letter (792×612), a parameters cover page then data pages; every data page repeats a stacked column header (`LOCATION`, the vertical P/R/E prefix letters, `PM`, `DATE OF RECORD`, `HG`, `AREA 4`, `CITY CODE`, `R/U`, the On/Off + Type letter pairs, `DESCRIPTION`). One line per ramp; **Descriptions never wrapped statewide** (the HSL fragment machinery is kept as a loud safety net); no trailer.
- **The print carries TWO columns the Excel export DROPS:** the **On/Off indicator** (`N`=on / `F`=off / `Z`=other) and the **Ramp Type letter** (the Ramp Summary legend codes D/F/L/H/K/C/G/E/R/J/B/Z…) — both columns TSN's database carries (`ON_OFF` as `O/F/Z`, `RAMP_TYPE`). The PDF-vs-TSN flavor **compares them** (TSMIS `N` projects to TSN's `O`); they stay context in the Excel flavor.
- **Null-render class (59 statewide rows):** the print writes `-` in an empty Area 4 / On/Off cell and `NO RAMP LINEAR EVENT` in an empty Description (TSAR ramp points without linework — the count Ramp Summary prints per route) where the Excel export leaves blanks. Verbatim in the workbook; projected to blank at compare time (documented in each flavor's Notes).
- **Whitespace class:** the database carries literal double spaces in Descriptions (`SB ON  AVERY PKWY` — the Excel export AND the TSN extract keep them); the HTML print collapses them. The PDF flavors collapse BOTH sides at compare time, so padding never counts (310 statewide cells).
- **Parse-back canary (7.9 ssor-prod, 126 routes vs the SAME-DAY Excel exports):** **15,216/15,216 rows** route-for-row; **0 unclassified lines, 0 stray fragments**; raw-cell diffs = 310 whitespace + 59×2 null-render + trailing-space only — every class projected at compare time.
- **Accepted source counts versus current product:** **PDF↔Excel source and product** both pair all **15,216**, have **0/0** one-sided, **15,212** identical, and four Description cells where Excel's literal `_x000d_`/newline is absent from the print. **PDF↔TSN source truth** is 15,212 paired, 4/198 one-sided, 14,438 identical, 774 differing rows, and **998 cells**. Current product instead reports 14,429 identical, 783 differing rows, and **1,012 cells** because it adds 15 false Description losses and omits one real District difference. **Excel↔TSN source truth** is 14,471 identical / 741 differing rows / **847 cells**; product reports 14,462 / 750 / **861** for the same +15−1 reason. On/Off 95 and Ramp Type 60 are genuine additional PDF assertions, not the source of the 14-cell product error.
- **TSN print (evidence side):** ONE statewide TASAS print (`Ramp Detail Statewide_TSN.pdf`, 09/15/2025, 500 data pages, landscape, Helvetica data lines) on a fixed column template. The accepted cross-format oracle maps all **15,410** records and every XLSX field with zero parser residue; source-date differences and truncated render claims are explicit rather than silently skipped. Lives in `tsn_library/ramp_detail/pdf/`.
- **Consolidator / comparator / evidence:** `consolidate_tsmis_ramp_detail_pdf` (the Excel layout + the two print-only columns appended with real labels) · `compare_ramp_detail_pdf` (`TSMIS_PDF_VS_TSN` graduating On/Off + Ramp Type; `TSMIS_PDF_VS_EXCEL`) · `evidence_ramp_detail` (both rows; the ID single-statewide-print pattern + the consolidator-lockstep TSMIS locator) · accepted end-to-end source/comparison gate `build/check_phase8_ramp_detail_comparison.py`. Product correction remains Stage 11 work.

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
- **Stage-8 current-source correction (2026-07-13; product remediation pending):** the
  7.8-Excel/first-7.9-PDF figures below are a historical cross-bundle fixture. The
  freshest same-run pair contains **60,494 Excel / 60,493 PDF** rows; route 037
  `003.809` is fixed, four paired PDF Descriptions are blank, and one described Excel
  row is absent from PDF. Installed Excel decodes the four lowercase `_x000d_` cells
  to CRLF. PDF↔Excel identity is Route + County + prefix + base PM + occurrence with
  suffix asserted; vs-TSN retains full printed PM identity. The shipped comparator and
  Notes remain red until remediation.
- **Historical — re-verified on the 7.8 statewide bundle (v0.24.0 audit; the July-2026 site update did NOT
  reshape HSL):** the per-route export format is UNCHANGED (positional map still exact, `SD.`
  trailing periods and `<route>/` description prefixes still present); rebuilding the library
  from the bundle's 12 district PDFs reproduces the user's installed library **byte-for-byte**
  (69,758 rows — the same 15-SEP-25 TSN snapshot); the fresh comparison (TSMIS **60,493** rows,
  2026-07-08 ssor-prod) lands within a hair of the canary — both **57,071**, only **3,422/12,687**,
  **diff cells 5,521** (FT **698** + Description **4,823**), identical **52,244**, routes
  **242/10/21** — the deltas are exactly the ~54 locations TSMIS added since June. Census of the
  diff classes: **681 of the 698 FT diffs are the by-design equate pairings** (TSN's synthetic
  "EQUATES TO" row carries no flag → `H ≠ (blank)`), 17 genuine (H↔I, R↔H); Description splits
  into TSMIS-labeled-vs-TSN-blank breaks (2,024), TSMIS comma-extended multi-item descriptions
  (1,487), the equate pairings (681), genuine wording drift (522 — incl. real renames like
  "OLD OREGON TRAIL"→"MTN GATE": the TSN snapshot is 10 months older), TSN-labeled (108). No new
  artifact classes; the comparator's Notes sheet now spells out the equate-pairing FT behavior.
  Bundle + scripts: `ground-truth/HSL Bundle 7.8/` (local).
- **Historical cross-bundle PDF edition (v0.25.0 — parser blessed on the first real work-PC print set,
  `ground-truth/HSL PDF + IS Bundle 7.9/`, 252 routes):**
  `consolidate_tsmis_highway_sequence_pdf` parses the print into the SAME 9-column TSMIS shape
  (header-anchored per-page windows; prefix/PM/suffix in their own narrow windows; wrapped
  Descriptions rejoined top-to-bottom HYPHEN-AWARE; PM-less "END OF ROUTE"/"CITY END" rows
  matched by single-letter HG+FT; the last page's "Unresolved Intersections" diagnostics
  trailer hard-stops the parse). Parse-back vs the 7.8 Excel exports: **60,493/60,493 rows,
  59,082 fully equal**; residual = the EQUATE-representation classes (the print writes the
  TSN convention — annotation "EQUATES TO <label>" with HG/FT/Distance blank + `E` on the
  equated plain postmile — where Excel writes the label alone and seats `E` differently:
  blanked-FT 1,129 / blanked-HG 910 / anno-desc 716 / suffix-moved 549 / "PM EQUATION" 413)
  plus 4 Excel `_x000D_` literal escapes and ONE genuine Excel defect (route 037 PM 003.809 —
  the Excel export drops a Description the print carries). Flavor canaries (7.9 PDFs vs the
  7.8 TSN/Excel): **PDF-vs-TSN both 57,505 / only 2,988+12,253 / diffs 4,930 / identical
  52,659 / routes 242/10/21** (pairs BETTER than Excel-vs-TSN — the equates key-match);
  **PDF-vs-Excel both 59,946 / one-sided 547/547 / diffs 1,722 on 864 rows / identical
  59,082** (== the independent positional verify, exactly). Scripts + expected numbers:
  `ground-truth/HSL PDF + IS Bundle 7.9/_verification-scripts/`.

### Intersection Summary — TSN  *(Stage-8 source-bound contract; current product has documented red paths)*
- **TSMIS side:** current per-route XLSX ×217 (the older 6.19 edition has ×218), **sheet
  `Intersection Summary`** (CONFIRMED), 3-col sheet
  (`A`=NUMBER, `B`=CODE). Rows: `TSAR - Intersection Summary` / `Route: NNN` / `Total Intersections = N`,
  then **11 category blocks**, each a `<BLOCK NAME>` header + `NUMBER | CODE` subheader + `count | code-label`
  rows. Block order: HIGHWAY GROUP, RURAL/URBAN/SUBURBAN, INTERSECTION TYPE, LIGHTING TYPE, CONTROL TYPES,
  MAINLINE NUM OF LANES, MAINLINE MASTARM, MAINLINE LEFT/RIGHT CHANNELIZATION, MAINLINE TRAFFIC FLOW. The
  per-route layout is **regular** → a generic block-walk consolidator
  (`consolidate_intersection_summary.py`) sums each `(block, code-letter)` across the
  current 217-route universe.
- **TSN format:** **PDF, statewide aggregate** (`Intersection Summary Statewide_TSN.pdf`, 3 pages; **data on
  page 3**). Same 11 blocks but in a **3-COLUMN** page (left x<190: HIGHWAY GROUP / RURAL-URBAN / INTERSECTION
  TYPE / LIGHTING / NUM OF LANES; middle 190–495: CONTROL TYPES / TRAFFIC FLOW; right x≥495: MASTARM / LEFT
  CHAN / RIGHT CHAN). Parse by **splitting words into the 3 column bands**, then block-walk each band like
  the TSMIS side. Footer `Total Intersections = 16626`.
- **Compare shape:** **AGGREGATE** (the Ramp Summary recipe). Key = **`(block, code-letter)`** — NOT the
  label (TSMIS reworded many labels: "STOP SIGN"→"STOP SIGNS", "FOUR-WAY"→"4-WAY", "...CHAN"→"...CHANNELIZATION").
  Special-case the two blocks whose code-letter isn't unique: RURAL/URBAN (two `-O OUTSIDE CITY` rows —
  disambiguate by parent R-RURAL/U-URBAN, like Ramp Summary's population) and NUM OF LANES (numeric codes 1–8/`+`).
- **⚠ TAXONOMY DIVERGENCE (confirmed on real data):** the systems use different code
  sets. The only authorized projection is raw TSN J–P into shared Control S; every other
  non-shared comparison code stays structurally **one-sided**:
  - **CONTROL TYPES:** A–I shared by canonical code meaning; **v0.17.8 folds TSN's legacy
    signal sub-types J/K/L/M/N/P into the single `S - SIGNALIZED` comparison category**
    (TSMIS collapsed the six legacy codes into one S), so Signalized compares on both
    sides and no TSN-only control comparison rows remain. The six raw TSN rows still
    require source-level disposition/provenance. **TSMIS-only O-PED HYBRID BEACON,
    Q-FLASH BEACON, R-YIELD ALL WAYS** stay one-sided; Z + `+` are shared. TSNR plus the
    same-pull TSMIS Excel/PDF pair prove canonical F is red on mainline and G is red on
    all; the raw TSN Summary PDF incorrectly prints `RED ON ALL` for both.
  - **INTERSECTION TYPE:** F/S/Y/M/T/Z shared; **TSMIS-only R-ROUNDABOUT, C-OTHER CIRCULAR, P-MIDBLOCK PED,
    `+`-NO DATA**.
  - The remaining one-sided row is LEFT CHAN `Y-CHANNELIZATION NOT SPECIFIED`
    (TSMIS-only). NUM OF LANES `+` is shared; TSN explicitly reports zero.
- **Canonical spec:** `summary_layout.INTERSECTION_SUMMARY_SPEC` = the union of both
  taxonomies (**65 `(block, code)` rows** after the signal fold; `_IS_TSN_ONLY == ()`) +
  grand Total = **66 comparison rows**, reusing the Ramp Summary AGGREGATE machinery +
  `extra_sheet_writer`.
- **Normalization:** key on block+code-letter (label text ignored); rural/urban + lanes special-cased.
  **No ditto/roadbed.**
- **July-2026 site rename (v0.25.0):** the per-route export renamed ONE block header,
  `MAINLINE MASTARM` → `MAINLINE MASTERARM` (the 7.9 statewide export's skeleton is otherwise
  IDENTICAL to 6.19 — verified route-by-route). The spec's Section now carries a parse-only
  `aliases=("MAINLINE MASTERARM",)` (all slugs/keys/labels stay derived from the original name, so
  no workbook text changed and no re-bless was needed; the TSN print keeps MASTARM). Because the
  pre-fix failure was SILENT (the block zeroed and its `+` count leaked into Lanes), the
  consolidator gained a **layout-drift tripwire**: every section's category counts must sum to the
  route's `Total Intersections` — true statewide in BOTH eras for every block EXCEPT `HIGHWAY
  GROUP` (the site itself under-counts it: 121/218 routes on 6.19, 6/217 on 7.9 — exempted) — so a
  future renamed header or unknown new code fails the route LOUDLY (named block, re-export hint,
  producer-owned PARTIAL) instead of writing wrong numbers. Fresh-export canary (7.9, 217 routes —
  route 170 missing vs 6.19's 218, flagged): all parse, statewide Total Intersections **16,459**.
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/intersection_summary/`
  (raw statewide PDF → normalized `Category|Count` via `tsn_load_intersection_summary.build_into`) ·
  `consolidate_intersection_summary` (block-walk category summer; per-route sheet + familiar Combined) ·
  `compare_intersection_summary_tsn` (AGGREGATE; `summary_layout.counts_from_rows` shared with the consolidator;
  one-sided diverged codes via `Cat.sides`) · `check_compare_intersection_summary_tsn.py` +
  `check_consolidate_intersection.py`. Live in both matrices (`matrix.tsn_comparator_for("intersection_summary")`).
- **Accepted current counts (Stage 8 — never regress without a newly bound source
  edition):** consolidator **217 routes → 16,459**. Comparison: **66 union rows — 58
  shared, 8 only-TSMIS, 0 only-TSN; 53 differing shared, 5 identical shared**; TSN Total
  **16,626**. The eight TSMIS-only rows are Intersection Type R/C/P/+, Control R/O/Q,
  and Left Channelization Y. Raw CONTROL J–P are six source rows folded into shared S,
  not TSN-only comparison rows. The older 218-route/16,473 count belongs only to the
  historical 6.19 edition and must not override current truth.
- **Stage-8 cross-format/oracle proof:** the current 217 Excel files and 217 PDF siblings
  have the exact same route universe and all **14,322** category/Total values match.
  Independent truth is bound to the raw TSN PDF, accepted r7 normalized workbook,
  Stage-6 result/acceptance, Intersection Detail XLSX↔PDF Summary cross-format oracle,
  and TSNR reference. Permanent gate:
  `build/check_phase8_intersection_summary_comparison.py`. Current production values and
  comparison semantics are exact; CMP-AUD-020/021/022/023/076/144/145/146/183/184
  remain product-red, so raw-source conservation and end-to-end perfection are false.

### Intersection Detail — TSN

> **⚠ July 2026 site update (v0.22.0)** — the site reshaped this report; the bullets
> below this block describe the PRE-update history where they conflict. What changed:
> - **TSMIS export is now 35 columns** (`intersection_detail_columns.HEADER` is the SoT):
>   the duplicated second `ML Eff-Date` is GONE; the tail is `Xing P/S` (the crossing
>   postmile's L/R marker) + **`Xing Line Lgth`** (TSN's `X_CROSS_OVERRIDE`, newly
>   exported and newly COMPARED). Postmiles print **zero-padded** (`000.204`), booleans
>   are **natively Y/N**, `Location` **carries the route suffix** (`11 IMP 008U`), and the
>   historical dates replaced the refresh stamps. The label-over-value shift REMAINS —
>   positions stay authoritative (`_TSMIS_POS`, re-verified statewide on 16,200 paired rows).
> - **Pre-update workbooks/PDFs are REFUSED, not mis-read**: the comparator's header gate
>   demands the `Xing Line Lgth` tail (36 consolidated cols) and errors with a re-export
>   hint on the old 37-col shape; the PDF parser detects unpadded postmiles and skips the
>   file as "pre-July-2026 print layout".
> - **The (PDF) print reshaped too**: 3 cover pages; rowB now carries its own 18-cell
>   rect bands AND a leading print-only DB **intersection number** (discarded — neither
>   Excel nor TSN has it). rowA keeps 21 cells whose last is a vestigial empty column
>   (warned about if it ever grows data back). Discrimination: rowA = zero-padded PM +
>   Location; rowB = integer in column 1. Current 7.9 parity proof: **217/217 routes,
>   16,459/16,459 rows, 0 orphans across 1,844 PDF pages**. Exact typed PDF↔Excel truth
>   is nine cells: eight Description values with Excel trailing tabs that PDF cannot
>   render, plus one HG conflict at `108/TUO/5.870` where PDF and both TSN forms agree
>   against Excel. The older “0 non-whitespace mismatches” shorthand is not current truth.
> - **What the update fixed in the comparison**: Date of Record + INT/Ctrl/Light eff-dates
>   now match TSN ≥99.9% (the old ~1-day offset is DEAD; the ~10 remaining per column are
>   genuine conflicts); the CS completeness gap fell ~37% → ~1%; Route Suffix usually
>   matches now. STILL structural: **Int St Eff-Date** (TSN's `EFF_DATE` is a 2022 bulk
>   stamp vs TSMIS's historical date — ~99% differ, the one wholesale column left) and
>   the smaller **ML/CS Eff-Date** resurvey gap (~12% / ~3%, TSN carries the LATER date).
>   TSN's `MAIN_EFF_DATE` (the second ML eff-date TSMIS dropped) is Report-View-only now.
>   Report View **Major** counts follow the data (user decision 2026-07-08): soft =
>   Int St / ML / CS Eff-Date + Route Suffix; everything else hard.
> - **New statewide canary (v0.22.0, the 7.8 ground-truth bundle): 21,675 diff cells /
>   16,199 matched / 260 TSMIS-only / 427 TSN-only** (was 163,310 / 677 pre-update).
> - **`normalization_version` 2 → 3**: the normalized library takes the new 33-field shape
>   (no `ML 2nd Eff-Date`, + `Xing Line Lgth`) AND appends the `TSN District`/`TSN County`
>   sidecar (from `LOCATION`) for the visual-evidence generator — mirror of Highway
>   Detail's v2 sidecar; the comparison loader slices it off. D2 auto-rebuilds on update.
> - **Evidence images (the second report after Highway Detail):** the TSN side is the
>   **statewide TASAS print** dropped in `tsn_library/intersection_detail/pdf/` (ONE file,
>   any name — district/county read per record from `LOCATION`). It is line-printer
>   Courier on ONE fixed column template document-wide; `evidence_intersection_detail`
>   parses it with fixed x-windows + MAX-OVERLAP word assignment (a `Y`-flagged date like
>   `Y98-08-28` leans left into its neighbor window; overlap keeps it home, the flag is
>   stripped from the value), LOCATION as one token-split window (2-char counties shift
>   the route token). Validated statewide: **16,584/16,584 records; 30/32 fields parse
>   back 100.00% identical** to the raw extract (Description 99.84% — print truncation
>   the verifier correctly skips; 2 ML-Num-Lanes cases). The whole print is indexed ONCE
>   per file (cached on size+mtime); per-district locates are lookups.
> - **Quote convention (censused 2026-07-10, a field report off the evidence images):**
>   both systems use THREE quote styles, character-identically — **doubled apostrophes**
>   for quoted letters (`''F'' ST`; TSN 62 rows / TSMIS 61, matching contexts incl.
>   `''13 DIPS'' RD`), single-quoted letters (route 238's `'G' ST. (LT)` family), and
>   plain possessive apostrophes (`O'BRIEN`, `DEVIL'S`; 60/59 rows, same rows). Exactly
>   ONE cell disagrees statewide — **KER 046 @ 50.904**: TSMIS `''F'' ST` vs TSN `"F" ST`
>   — and that `"` is the ONLY quotation-mark character (U+0022) in the ENTIRE 09/2025
>   TSN extract (TSMIS Descriptions contain zero). A genuine data edit on one side, NOT
>   normalized (folding `''`≡`"` would hide it and mangle possessive-style text for zero
>   count benefit; comparison-engine.md §13 has the census). Because the two forms print
>   near-identically, the evidence header now carries a dark-red `_quote_note` line naming
>   both sides' characters, and the ID Notes sheet documents that quotes compare literally.

> **Accepted Stage-8 current-source oracle (2026-07-13, `ID-79`):** the exact 217-route
> 7.9 Excel/PDF pair, raw TSN XLSX/PDF, accepted r7 normalized workbook, Stage-6 result,
> and TSN cross-format oracle are bound. Approved physical identity is
> `(base Route, County, complete PP, numeric Post Mile)`: raw TSN has 78 weak
> Route+numeric-PM cross-county keys / 156 county identities and six within-county
> numeric-PM collisions separated only by complete PP. Excel-vs-TSN is **16,199 paired,
> 260/427 one-sided, 16,053 differing rows, 21,676 differing cells**; PDF-vs-TSN has the
> same row counts and **21,683 cells**. Raw↔normalized pairs all **16,626** rows with zero
> asserted differences. Current product overlapping cells are exact, but its Route+PM
> identity, missing PDF Report View, ignored explicit Route/`S`, and normalized loss of
> `MAIN_EFF_DATE`/`MAIN_ADT`/`CROSS_ADT` remain red under
> CMP-AUD-045/068/070/133. Permanent gate:
> `build/check_phase8_intersection_detail_comparison.py` (31 assertions).

- **TSMIS side (pre-July-2026 notes):** per-route XLSX ×218, **sheet `Intersection Detail`** (CONFIRMED), **36 columns** `[P, Post Mile, S, Location, Date of Record, H/G, City Code, R/U, INT Type, INT Eff-Date, Ctrl T, Ctrl Type, Light Eff-Date, Light T/Y, ML Eff-Date, ML S/M, …]`. Free-text **Description** column → formula-injection guard (handled by the shared `consolidate_xlsx` core). **Consolidator DONE (v0.17.0):** `consolidate_intersection_detail` (thin `consolidate_xlsx` wrapper) — verified 218 routes → 16,473 rows.
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

> **Current version correction (2026-07-12):** Highway Log is now normalization
> version **4** and Highway Sequence version **3**. Both bumps force every existing
> library through exact internal D01-D12 admission; the older version numbers above are
> historical canary narrative, not the current catalog contract.

### Highway Detail — TSN  *(BUILT + verified — v0.20.0, the statewide-bundle reconciliation)*
- **TSMIS side:** per-route XLSX ×252, **sheet `Highway Detail`**, **34 columns** (labels CORRECT as-is — `highway_detail_columns.py` is the SoT; unlike the Highway Log no relabel is needed): `[Post Mile, Length, Date of Rec, HG, AC, Acc-Cont Eff, City, RU, RU Eff, Description, NA, LB Eff…LB IN-TR (9), Med Eff…Med V/WDA (5), RB Eff…RB OT-TR (9)]`. All-text cells; dates `YY-MM-DD`; single digits zero-padded (`'02'`); `Post Mile` glues prefix+mile+marker (`'S000.000'`, `'000.000E'`, `'000.080R'`). **Consolidator:** `consolidate_highway_detail` (thin `consolidate_xlsx` wrapper + tooltips/Legend) — verified 252 routes → **51,243 rows**. The **PDF edition** parses via `consolidate_tsmis_highway_detail_pdf` (PER-PAGE window derivation — each print page is its OWN auto-layout table whose column x-positions vary page to page; wrapped-cell row grouping + hyphen-aware fragment rejoin; cross-page record carry with a date-token furniture guard; document-median fallback for a band-less page, logged).
- **TSN format:** **XLSX, statewide flat**, single sheet `Sheet 1`, **60,083 rows × 56 columns**, **273 routes** (`TSAR - HIGHWAY DETAIL_TSN.xlsx`; REFERENCE_DATE 2025-09-08). Columns: ids (`THY_ID`, `SEG_ORDER_ID`), the DCR block (`DIST/CNTY/RTE/RTE_SFX`), the split postmile (`PP`/`POSTMILE`/`E_IND`), numeric `LENGTH` (raw DB precision), the attributes (named like the TSMIS columns but UNPADDED), the `*`/`Y` change flags (`ACC_SIG/LT_SIG/MED_SIG/RT_SIG`), and the **ADT block** (`BEG_DATE/ADT_AMT/PROFILE/BREAK_DESC/LK_BACK_ADT/CHNGMILE/DVM`) the TSMIS report omits by design. **The `+`/`++` DITTO marks appear here too** (v0.21.0 finding): on independent-alignment rows TSN stores the Highway Log-style ditto TEXT in the numeric roadbed/median columns (e.g. `R_NO_LANES='++'`), and the district prints render it the same — the comparison flags those cells as ordinary text diffs (TSMIS prints real numbers), and the evidence locator's print regexes accept the marks. The **12 TSN district PDFs** were cross-checked against this extract (57,647 records parsed, every shared field ≥99.9% identical; the one exception BEG_DATE ≈88.8% is the ADT reference-year skew — the PDF pull was REF 09/15 vs the extract's 09/08) → **the Excel is the library source**; the PDFs stay reference-only.
- **Compare shape:** **FLAT**, **key = route + CANONICAL Post Mile** (35 shared columns: the key + a derived `PS` column + the 33 remaining; `CONTEXT_FIELDS = ()`). The reconciliations (all locked in `check_compare_highway_detail_tsn.py`; full detail in [comparison-engine.md](comparison-engine.md) §9f-2): the **roadbed-aware key** (TSMIS trailing `R`/`L` ≡ TSN bare PM + `HG∈{R,L}` — routes 282/880S/011/260 went from 0 matched rows to row-for-row); the **equation marker excluded from the key** (compared as `PS` — the systems print `E` on different rows); **NA `'A'`→blank** (TSN prints an explicit add-mileage `A` on 98.7% of matched rows where TSMIS is blank); **zero-pad** (`'02'`≡`'2'`); **Length → the printed 3 decimals** (TSN stores 0.01098); **`M_WID`+`M_VA` → the glued `'14Z'`**; whitespace collapse. **`RU Eff` ↔ `BEG_DATE` is compared BY POSITION and differs on ~99% of rows** — the legacy report prints the ADT begin year in that slot where TSMIS prints the Rural/Urban layer date (structural; Notes-documented; soft in the Report View).
- **Counts (CANARY — the 2026-07-07 statewide dev bundle, local-only ground truth):** TSMIS consolidated **51,243** (252 routes) vs TSN normalized **60,083** (273 routes; ~21 unconstructed routes TSMIS doesn't export) → **48,644 both / 2,599 only-TSMIS / 11,439 only-TSN; 208,596 counted diff cells** (RU Eff alone 48,211 — the structural slot; next: RB/Med/LB Eff ≈16.2k/16.0k/14.2k, Length 7.5k, PS 999, NA 99). **PDF↔Excel on the bundle: 2,484 of 2,487 rows fully identical** (5 differing cells on 3 rows + 3/5 one-sided) — the residue is a REAL export discrepancy (the bundle's PDFs came from a NEWER site build that merges same-postmile record clusters with ' / '-joined descriptions and carries a record the Excel lacks), exactly what the self-check exists to surface.
- **Drop folder / consolidator / comparator / golden check:** `tsn_library/highway_detail/` (raw statewide XLSX → normalized via `tsn_load_highway_detail.build_into`, **`normalization_version=2`** — v2 appends the `TSN District`/`TSN County` SIDECAR columns after the shared header for the visual-evidence generator; the comparison loader slices to the shared width and never sees them) · `consolidate_highway_detail` + `consolidate_tsmis_highway_detail_pdf` · `compare_highway_detail_tsn` (FLAT; Notes + the two-line TASAS **Report View** via `extra_sheet_writer`) + `compare_highway_detail_pdf` (`TSMIS_PDF_VS_TSN` / `TSMIS_PDF_VS_EXCEL`) · `check_compare_highway_detail_tsn.py` + `check_highway_detail_pdf.py` + `check_visual_evidence.py`. Shares the `compare_tsn_common` (`ctc`) substrate. Live in both matrices. **Optional `tsn_library/highway_detail/pdf/`:** the district prints, read only by the evidence images; app-created + hinted via `ensure_layout` (the catalog's `evidence_pdfs` flag, v0.21.1) — the user only drops files in ([comparison-engine.md](comparison-engine.md) §13).

### Highway Log — TSN (reference, already built)
Fully documented elsewhere — this is the recipe the others follow:
- Format + parsers: [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) (TSN char-window parser + the 3 description guards).
- 31 corrected columns: [highway_log/columns.md](highway_log/columns.md).
- The `+`/`++` ditto domain + roadbed split: [highway_log/comparison-study.md](highway_log/comparison-study.md).
- Approved canary: **Route-1 = 299 both / 969 diff cells** (never regress; see
  [verification-and-testing.md](verification-and-testing.md)).
