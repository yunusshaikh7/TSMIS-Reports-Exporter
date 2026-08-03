# `RB-3` — Implementation Record

Status: **MERGED** — `61fcac611de255c56759551a95ccd2e552287bfc`

| Field | Value |
|---|---|
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-3-ramp-detail-layout` (worktree `C:\Users\Yunus\Projects\wt-rb3`; the user's `main` checkout untouched) |
| Base `main` commit | `194b7ee8da095f0300e7e635bb7e7af78643b685` (v0.33.1; verified clean and identical to `origin/main` at branch creation) |
| Implementation commit | `c9b55b6` — `fix: accept both Ramp Detail export layouts (RB-3 / HF-04)` |
| Acceptance / documentation commit | this commit (RB3-A1 record + witnesses) |
| Work items | HF-04 (PCOA-FINAL-001 P1, PCOA-FINAL-012 P2) |
| Generated-output root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-04\` (harness scripts + `rb3-a1\` outputs + logs + JSON witnesses); committed machine-readable witnesses in `../HF-04/witness/` |

## Changes

| File | Change | Finding IDs |
|---|---|---|
| `scripts/compare_ramp_detail_tsn.py` | The consolidated-TSMIS gate becomes DUAL-EDITION: `_TSMIS_HEADER` (classic) + the new `_TSMIS_HEADER_2026` (July-2026: blank labels gone, PM-suffix column dropped, `OF`/`TY` added, values MOVED — Description at position 11), each bound to its own by-position row transform (`_tsmis_row` untouched; new `_tsmis_row_2026` maps `OF`→On/Off and `TY`→Ramp Type context cells verbatim and conserves an empty PM-suffix claim). `_load_tsmis` dispatches per matched edition via `_LayoutDispatch` (header_ok records which accepted header matched; the row transform reads that edition's positions). The refusal message (`_BAD_HEADER_MSG`) now names the REAL gate — the exact supported-edition header bind — and a workable action, replacing the misdiagnosing "expected a leading 'Route' column — consolidate the per-route exports first" that PCOA-FINAL-001 recorded (the workbook HAS that column, and re-consolidating reproduces the identical failure). New public `consolidated_header_ok(header)` — the ONE consumability predicate the consolidator's completion gate shares with the loader. Notes sheet: the context-columns line now states that the July-2026 export carries On/Off (OF) and Ramp Type (TY) (displayed on the TSMIS side, still never counted), and one added line disclosing the July null-token class (`-` / `NO RAMP LINEAR EVENT` printed where the database is blank — counted vs TSN's blanks, since the workbook reports exactly what each source carries) | PCOA-FINAL-001 |
| `scripts/compare_env.py` (RD header path) | `_ramp_detail_canonical_header` recognizes BOTH censused layouts and returns each edition's DISPLAY header: classic → the CMP-AUD-046 corrected labels `_RD_ENV_HEADER` (the job the static `force_header` used to do — a length-matched force_header would have relabelled the same-width July layout WRONGLY, so RAMP_DETAIL's `force_header` is dropped and the relabel moved into the canonicalizer); July-2026 → its own labels (`_RD_ENV_HEADER_2026` — "labelled, not positional"). `_ramp_detail_env_keys` resolves the PM prefix/suffix columns by NAME (`PR`/`PRE`; `PM Suffix`) instead of the fixed `kf-1`/`kf+2` offsets — on the classic and PDF display headers the named columns sit at exactly the old offsets (claims byte-identical), while the July layout, which has NO suffix column, conserves `""` instead of misreading HG as a postmile suffix. NEW opt-in `EnvCompare.layout_merger` hook (default None — inert for every other family), consulted only when the two sides canonicalize to DIFFERENT recognized layouts: `_ramp_detail_merge_layouts` reprojects a mixed classic/July pair onto ONE shared display shape (`_RD_ENV_MIXED_HEADER`: the nine columns both editions export compared by NAME + `PM Suffix`/`OF`/`TY` as CONTEXT — a column only one side exports cannot be compared; a compared blank-vs-value column would flag every row) with a Notes sheet documenting the projection and the July null-token class. Same-edition pairs never reach the merger and compare exactly as before | PCOA-FINAL-001 |
| `scripts/consolidate_ramp_detail.py` | `_consumability_downgrade`: after the shared consolidator returns ok, the PRODUCED workbook's header row is verified against `compare_ramp_detail_tsn.consolidated_header_ok` (the comparator's own gate, so "consolidation ok" and "a comparator will read it" cannot drift apart). An unknown-layout result is downgraded to `status="error"` / `completion=outcome.FAILED` — not promotable, not comparable, not cacheable as fresh — with the combined file kept on disk for inspection and named in the message alongside the supported editions and a workable action. Both accepted editions still report ok/complete. Composes with the CMP-AUD-085 last-complete machinery unchanged: a downgraded refresh attempt is left unpromoted beside last-good and the caller is refused with this producer message | PCOA-FINAL-001 defect (a) |
| `scripts/compare_ramp_detail_pdf.py` | The self check's Excel leg (`_load_excel_collapsed`, used ONLY by `TSMIS_PDF_VS_EXCEL`) now applies the SAME render projections `_pdf_row` has always applied on the PDF leg (`_null_blank_excel_rows`): Area 4 `-`→blank, Description `NO RAMP LINEAR EVENT`→blank, On/Off `-`→blank and print-N→O. A no-op on classic-layout workbooks (census: zero null tokens there — byte-stable); on the July-2026 export it removes exactly the 108-cell false-discrepancy class PCOA-FINAL-012 measured (36 `Area 4` + 36 OF + 36 Description; the 36 TY `-` cells were already symmetric — the PDF leg never projected Ramp Type and both sides carry `-`). `_NOTES_PDF_VS_EXCEL` rewritten to state both editions' behavior; module docstring updated. The vs-TSN flavor (`TSMIS_PDF_VS_TSN`), `_pdf_row`, `_pdf_header_ok` and `_load_tsn_collapsed` are UNTOUCHED | PCOA-FINAL-012 |
| `build/check_compare_ramp_detail_tsn.py` | `test_dual_layout_loader` (July fixture incl. the finding's route-001-row-2 and 005/025.218 null-token shapes; classic still loads; unknown 13-column layout refused with the real gate named and WITHOUT the old misdiagnosis; `consolidated_header_ok` accepts both/refuses junk) + `test_consolidator_completion_truth` (unknown-layout consolidation ≠ ok, completion=failed, file kept + named; both accepted editions ok/complete). Degrades to semantic FAILs on a pre-fix tree (the July load's refusal is caught and reported as the recorded defect signature) | both |
| `build/check_compare_ramp_detail.py` | `test_new_layout_end_to_end` (July pair: export's own labels displayed; a genuine OF change counts), `test_mixed_layout_end_to_end` (mixed pair: the 12-column shared header, exactly one real Description diff counted, OF/TY context shows the exporting side's letters, mixed Notes present), `test_mixed_identical_data_is_clean` (identical shared data → clean MATCH, zero diffs/one-sided), `test_unknown_layout_pairings_still_refuse` (classic-vs-unknown and unknown-vs-unknown both refuse; no workbook written). New `_rd_row_valuepos` fixture builder documents that the real classic export carries values at the CMP-AUD-046 VALUE positions (the pre-existing `_rd_row` mirrors the LABEL positions for the positional same-layout tests and is unchanged) | PCOA-FINAL-001 |
| `build/check_compare_ramp_detail_pdf.py` | `test_self_check_null_parity` — the same-source pair carrying `-` / `NO RAMP LINEAR EVENT` / print-N on BOTH sides reports ZERO differing cells, fully paired, clean-match verdict, no ≠ marker, On/Off context reading the projected O from both legs; the classic-layout (blank-cells) control stays zero. Degrades to semantic FAILs pre-fix (the refused July Excel side) | PCOA-FINAL-012 |
| `build/check_compare_env_flat_schema.py` | The recognizer matrix's `_families()` gains an `expect` column: Ramp Detail's canonicalizer now returns its corrected DISPLAY labels (and a new July-2026 row expects `_RD_ENV_HEADER_2026`); the other families still echo the loader-normalized header. Refusal sub-checks unchanged | wiring the RD surface HF-04 changed |
| `build/check_compare_env_field_labels.py` | The CMP-AUD-046 config-wiring assertion follows the mechanism move: the classic raw layout must canonicalize to the corrected labels and `RAMP_DETAIL.force_header` must now be None (dual-layout); the RD-PDF force_header and both end-to-end display tests (diff under 'Description', not 'R/U') unchanged and still green | wiring |
| `build/check_compare_physical_identity.py` | `test_ramp_env_county_identity`'s fixture header becomes the CANONICAL display header `_schema` actually receives post-HF-04 (the canonicalizer runs before `_schema` on every production path); all claim assertions unchanged and green — the conserved prefix/suffix claims are byte-identical under the name-keyed resolution | wiring |
| `hotfix-bundles/RB-3/BUNDLE.md` | Base `main` SHA filled | — |
| `IMPLEMENTATION-PLAN.md` | RB-3 status → `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW` (queue + coverage rows together) | — |
| `hotfix-bundles/HF-04/witness/` | `two-layout-header-census.json`, `route-001-row-2-trace.json`, `self-check-zero.json`, `rdpdf-tsn-counts-unchanged.json` | — |

## Root cause confirmed

Exactly as the bundle states, re-verified against the frozen corpus before any
code change (census over every per-route file of both pulls — the committed
`two-layout-header-census.json`):

- **One header per pull.** All 126 July files carry
  `Location, PRE, PM, Date of Record, HG, Area 4, City Code, R/U, OF, TY,
  Description`; all 126 classic files carry the blank-labelled shifted layout.
  15,213 July rows / 15,216 classic rows.
- **Values moved.** HG..Description shift one left; Description lands at
  per-route position 10 (consolidated 11); the classic PM-suffix column is
  gone (and was blank on ALL 15,216 classic rows).
- **The null-token class is real and July-only**: exactly 36 rows carry `-`
  in Area 4 / OF / TY and `NO RAMP LINEAR EVENT` in Description (route 005 at
  07-LA-005 / 025.218 among them); the classic pull carries ZERO such tokens.
- **The July OF letters are the PRINT convention** (N 7,635 / F 7,417 /
  Z 125 / `-` 36) — N where TSN stores O — so the self check's Excel leg needs
  the same N→O projection the PDF leg has always applied.
- The misdiagnosing refusal message and the consolidator's unconditional
  126/126 `status=ok` reproduced at the base SHA exactly as PCOA-FINAL-001
  records (the base-red run below prints the exact message).

No material deviation from the plan was found; scope was not expanded.

## Design

1. **Dual-edition acceptance is per-edition position maps behind one gate**,
   not a second label row over one map: the two layouts' value positions
   differ, so the Intersection Detail same-positions precedent
   (`exact_consolidated_header_ok(cur, leg)`) does not apply. `_LayoutDispatch`
   binds header recognition to the matching row transform inside the one
   shared `load_consolidated_rows` skeleton.
2. **OF/TY land in the existing On/Off / Ramp Type context columns** —
   "mapped to the correct fields" with zero count impact (context never
   asserts). They display verbatim on the vs-TSN path (byte-exact posture;
   the Notes disclose the print-letter convention) and projected (`-`→blank,
   N→O) on the same-source self check, mirroring the PDF leg exactly.
3. **The env path canonicalizes each edition to its own display header** and
   merges MIXED pairs name-keyed over the nine shared columns with the three
   edition-specific columns as context. Same-edition pairs (including every
   previously-working classic pair) take exactly the pre-fix path — the
   classic display header, key claims, and counts are unchanged by
   construction (the canonicalizer now returns what force_header used to
   apply; proven by the untouched end-to-end label checks).
4. **Consolidator completion truth is the comparator's own predicate** run
   against the PRODUCED file (test-the-shipped-path: assert the artifact, not
   the input list): unknown layout → error/FAILED, file kept for inspection,
   message names the gate and a workable action.
5. **Null parity is self-check-only.** The vs-TSN and cross-env comparisons
   keep their byte-exact posture: the July export's `-`/`NO RAMP LINEAR
   EVENT` tokens COUNT against TSN's/classic's blanks as real render
   differences of the export, disclosed in Notes (the same disclosure-only
   stance as the owner's PCOA-FINAL-013 ruling; suppressing them would be an
   unauthorized count-affecting normalization). Only the same-source self
   check — where both legs render the SAME report — projects them, exactly
   as its PDF leg always has.

## Focused checks — red at base, green at head

Method: the three extended check files were copied beside an archived
`scripts/` tree at the exact base SHA (`git archive 194b7ee`) and run there,
then at head.

| Check file | At base `194b7ee` | At head |
|---|---|---|
| `check_compare_ramp_detail_tsn.py` | **15 semantic FAILs, all new HF-04 assertions** — the July load refuses with the exact misdiagnosing message (printed by the check), the refusal-message assertions fail, `consolidated_header_ok` absent, and the unknown-layout consolidation reports ok (the PCOA-FINAL-001 defect signature); every pre-existing check still OK | ALL PASS |
| `check_compare_ramp_detail_pdf.py` | **6 semantic FAILs**, all in `test_self_check_null_parity` (the July Excel side is refused outright); all 10 pre-existing checks OK | ALL PASS |
| `check_compare_ramp_detail.py` | red — aborts at `test_new_layout_end_to_end` with the recorded refusal (`does not use a recognized Ramp Detail column layout`) | ALL PASS |

## RB3-A1 — the one executable acceptance run

Acceptance head: **`dd922f7`** on `hotfix/rb-3-ramp-detail-layout` — the
runtime the whole final artifact set was generated with (`c9b55b6` +
the one-sentence Notes-wording precision; an earlier artifact set generated
at `c9b55b6` itself was fully wiped and regenerated so no artifact spans two
runtimes). Commits after `dd922f7` are documentation/witness-only — zero
runtime delta.

**Frozen inputs** (every input, deliverable, result, render, gate log and
committed witness is bound by exact path, byte size, SHA-256, frozen-source
identity and generation metadata to the acceptance head in the COMMITTED
manifest
[`rb3-a1-artifacts.json`](../../rb3-a1-artifacts.json), checked by the
committed independent verifier
[`rb3-verify-manifest.py`](../../rb3-verify-manifest.py) — run
`rb3-verify-manifest.py rb3-a1-artifacts.json --tree <repo> --at dd922f7
--corpus --zips`; a byte-identical retained copy sits in the HF-04 output
root):

| Input | Identity |
|---|---|
| July-2026 pull | `…\post-comparison-output-audit-claude-independent-2026-07-23\raw-extract\2026-07-23 ssor-prod\ramp_detail{,_pdf}` — 126 + 126 files (the Stage 1B frozen extract of the audit archive) |
| Classic prior pull | `…\ground-truth\All Reports 7.9\2026-07-09 ssor-prod\ramp_detail{,_pdf}` — 126 + 126 files |
| TSN raw extract | `…\Downloads\TSMIS\tsn_library\ramp_detail\raw\TSAR - RAMPS DETAIL_TSN_11.04.2025IT.xlsx` |
| Everything store | provisioned the Stage 1B way: `ssor-prod` ← the July pull, `ssor-test` ← the classic pull (2026-07-09 ars-prod is an outage substitute holding no ramp_detail and is NOT an env side — owner clarification 2026-08-02, recorded in the corpus `_INDEX.md`) |

**Entry points** — the same public paths the GUI workers drive, no lower-level
shortcut (the RB-2-accepted bar): `consolidate_ramp_detail.consolidate` /
`consolidate_tsmis_ramp_detail_pdf.consolidate` (Consolidate tab, day-scoped),
`tsn_library.build_consolidated` (the Settings rebuild entry),
`compare_env.RAMP_DETAIL.compare_folders` (classic Compare tab),
`compare_ramp_detail_tsn.compare` / `TSMIS_PDF_VS_TSN.compare` /
`TSMIS_PDF_VS_EXCEL.compare` (Direct), `day_matrix.build_day_cell`,
`baseline_matrix.build_baseline_cell`, `pdf_excel_matrix.build_pve_cell`,
`matrix.build_comparison` (tsn / env / vs_excel) with the worker's own
owned-dir leases and commit guard. Harness: `acc_rb3_generate.py` (retained).

**Every placement produced — 16/16 harness steps ok** (`rb3-a1-generation.json`;
the same typed counts reproduced across four independent generation passes
during the run, so the numbers below are deterministic):

| Placement | status / verdict | paired | A-only | B-only | diff rows | diff cells |
|---|---|--:|--:|--:|--:|--:|
| Consolidate Excel 2026-07-23 | ok / complete | — | — | — | — | 126/126 files, 15,213 rows |
| Consolidate PDF 2026-07-23 | ok / complete | — | — | — | — | 126/126 files, 15,213 rows |
| Consolidate Excel 2026-07-09 | ok / complete | — | — | — | — | classic layout still green |
| TSN library build (`tsn_library.build_consolidated`) | ok / complete | — | — | — | — | 15,410 TSN rows / 126 routes |
| By Day vs TSN | ok / diff | 15,204 | 9 | 206 | 431 | **508** |
| Direct vs TSN | ok / diff | 15,204 | 9 | 206 | 431 | **508** |
| Everything vs TSN | ok / diff | 15,204 | 9 | 206 | 431 | **508** |
| Direct RD-PDF vs TSN (criterion-6 control) | ok / diff | 15,204 | 9 | 206 | 468 | **619** |
| Direct self (PDF vs Excel) | ok / **match** | **15,213** | 0 | 0 | 0 | **0** |
| Everything SELF | ok / **match** | **15,213** | 0 | 0 | 0 | **0** |
| PDF-vs-Excel by-day | ok / **match** | **15,213** | 0 | 0 | 0 | **0** |
| Classic env new-vs-prior | ok / diff | 15,208 | 5 | 8 | 352 | **408** |
| Classic env prior-vs-new (the bundle's stated direction) | ok / diff | 15,208 | 8 | 5 | 352 | **408** |
| Baseline (2026-07-23 vs day:2026-07-09) | ok / diff | 15,208 | 5 | 8 | 352 | **408** |
| Everything ENV (ssor-prod vs ssor-test — the MIXED pair) | ok / diff | 15,208 | 5 | 8 | 352 | **408** |

Lane consistency: the three vs-TSN lanes agree exactly; the four mixed-pair
env placements agree exactly and mirror one-sided counts under direction
reversal; the three self placements agree exactly.

### Measurable acceptance criteria — all seven met

| # | Criterion | Result |
|---|---|---|
| 1 | All 8 topology decisions + the by-day PDF-vs-Excel placement produce BOTH twins from the frozen 2026-07-23 input | **PASS** — the table above; every placement also wrote its formulas twin (`also_formulas=True` / `mode="both"`), 11 formulas workbooks in all |
| 2 | `OF`, `TY`, `Description` proved correct on route 001 row 2 against raw | **PASS** — `witness/route-001-row-2-trace.json`: the raw July row `12-ORA-001 · R · 000.606 · 02/25/1976 · D · Y · DAPT · U · F · D · 001/NB OFF TO DOHENY PK RD` projected and read back from the published Direct workbook's TSMIS sheet with OF→`On/Off`=F, TY→`Ramp Type`=D, Description=`NB OFF TO DOHENY PK RD` (prefix stripped), HG/Area 4/City Code/R-U at the July positions, PR from PRE — five/five workbook checks true |
| 3 | The consolidator no longer reports ok for output no comparator accepts | **PASS** — `test_consolidator_completion_truth` (hermetic red→green: error + completion=failed + file kept + supported editions named); both real frozen pulls consolidate ok/complete |
| 4 | The self check reports ZERO differing cells across all 15,213 rows | **PASS, three ways** — Direct self, Everything SELF and the by-day PvE cell each: 15,213 paired / 0 one-sided / 0 differing; the app-free recount (`witness/self-check-zero.json`) independently pairs all 15,213 rows with 0 missing keys, 0 multiplicity mismatches and 0 differing compared cells; the recalculated formulas twins' live verdict reads "✓ EVERYTHING MATCHES — all 15,213 ramps" |
| 5 | The 2026-07-09 layout still compares; an unknown layout still refuses | **PASS** — the classic pull consolidates ok/complete and pairs in four mixed placements; hermetic checks pin classic-vs-classic behavior, classic-vs-unknown and unknown-vs-unknown refusals, and the loader's unknown-layout refusal message |
| 6 | RD-PDF vs TSN counts unchanged | **PASS** — `witness/rdpdf-tsn-counts-unchanged.json`: base (`194b7ee`) and head runs from IDENTICAL inputs return identical typed counts (15,204/9/206/468/619, same per-field) AND cell-for-cell identical Comparison sheets (0 differing cells) |
| 7 | Full gate green; every new assertion fails pre-fix | **PASS** — gate results below; base-red signatures recorded above |

### Source-truth recounts (app-free, openpyxl-only — `acc_rb3_recount.py`)

- **Direct vs TSN**: the independent recount from the raw per-route exports +
  the raw TSN extract reproduces paired 15,204 / TSMIS-only 9 / TSN-only 206
  exactly, and 507 differing cells over singleton keys with identical
  per-field counts (HG 69 · City Code 156 · Description 162 · R/U 68 ·
  Area 4 36 · Date of Record 15 · District 1); the 508th cell is the ONE
  duplicate-key group (101 / LA / 1.284 — two TSMIS rows, one TSN row), where
  the engine's assignment pairs the real row (`SEG ON FR MISSION RD` vs
  `ON FR MISSION RD` = the +1 Description diff) and leaves the no-linework
  placeholder one-sided. The workbook's own Status counts (15,204 Both /
  9 TSMIS only / 206 TSN only) and Diffs sum (508) agree exactly.
- **The July null-token class**: all 36 censused `-`-rows accounted — 34
  Area-4 tokens pair against real TSN values (18 `Y`, 16 `N`) and 34
  NRLE-Descriptions against real TSN text (all counted, byte-exact posture);
  the remaining token rows sit in the duplicate group / one-sided set. TSN is
  NOT blank on these rows — the tokens mark ramps whose TSMIS row carries no
  linework while TSN still records attributes; the Notes line states the
  class without asserting what TSN carries.
- **Classic env (mixed)**: singleton recount 406 cells (HG 296 · Area 4 55 ·
  Description 55) + the same duplicate group's 2 = the engine's 408 exactly;
  paired/one-sided identical.

### Values / formulas / installed Excel (`acc_rb3_excel.py` + reread)

All **11** formulas workbooks (one per placement) recalculated with installed
Excel (`CalculateFullRebuild` + Save), then read back app-free: every one
carries **10/10 SELF-CHECK rows OK**, **0** error cells on
Summary/Spot Check/Comparison, and a live verdict line equal to the values
twin's (508 / 619 / 408 / "EVERYTHING MATCHES — all 15,213 ramps").
`rb3-a1-excel.json` binds each post-recalculation workbook to its exact
SHA-256.

### Store integrity (`acc_rb3_store_integrity.py`)

- **Pre-recalculation: ALL OK (14 artifacts)** — every committed comparison
  VALUES workbook's generation sidecar read TRUSTED and CURRENT through
  `consolidation_meta.read_comparison_outcome` (the strict reader the matrix
  trusts), and every consolidated workbook's sidecar read
  trusted/current/complete (`rb3-a1-store-integrity-prerecalc.json`).
- **Post-recalculation: ALL OK** — the six store-lane cells stay strictly
  trusted (their formulas twins are settled outside the committed
  generation); the five manual mode="both" outputs correctly report their
  recalculated-and-saved FORMULAS member as content-changed — exactly what
  the truth layer should say about a file installed Excel re-saved — while
  their values members stay current (`rb3-a1-store-integrity-postrecalc.json`).
- Process note, disclosed: the harness initially called the consolidators one
  layer below the tab driver, so the driver's own
  `consolidation_meta.write_outcome` (cli.py / gui_worker_export.py) was
  replayed for the 2026-07-09 consolidated from the recorded producer result
  (bytes untouched since the build; the harness now performs the driver's
  write in-line). An earlier acceptance iteration also let the recalc step
  open matrix VALUES workbooks; that iteration's artifacts were fully wiped
  and regenerated, and the recalc script now refuses to open anything but
  formulas twins.

### Visual / presentation (`renders\` — native Excel, Zoom 100)

Rendered and inspected: the mixed classic-env Summary (the verdict headline,
row counts 15,213/15,216/15,221, the DIFFERENCES-BY-FIELD table listing the
mixed header's 11 fields incl. PM Suffix/OF/TY), Comparison (canonical
`route / county / pm` keys, Status/Diffs), and Notes (the full mixed-layout
disclosure incl. the null-token class); the self Summary (green
"✓ EVERYTHING MATCHES — all 15,213 ramps", 0/0/0); the Direct vs-TSN Summary;
and the July consolidated workbook (every label over its own value).
`acc_rb3_sweep.py` additionally asserts from the stored files: OF/TY/
Description labelled at their own value positions in the July consolidated
header, and the mixed comparison's OF/TY/PM-Suffix context columns + Notes
present.

### Evidence prohibition

**Zero** `*evidence*` artifacts anywhere under the generated outputs or the
worktree output tree (`rb3-a1-sweep.json`: hits = 0). Every run passed
`evidence=None`; RD vs TSN and RD self remain PROHIBITED classes and nothing
appeared as a side effect of unblocking the comparisons.

### Key artifact identities (values twins + consolidated; full inventory with
formulas twins in `rb3-a1-sweep.json` / post-recalc hashes in `rb3-a1-excel.json`)

| Artifact | Bytes | SHA-256 |
|---|--:|---|
| `tsar_ramp_detail_consolidated 2026-07-23 ssor-prod.xlsx` | 760,541 | `3747308A5F57AFF7D9948FB3017D9B4BC1B41F01EBF32CF199EDF737367DD64F` |
| `tsmis_ramp_detail_pdf_consolidated 2026-07-23 ssor-prod.xlsx` | 773,751 | `713B6DD0D492B40F0B9AD840FDC0FE4FF32F5042FA0637315B7A573BAD969769` |
| `tsar_ramp_detail_consolidated 2026-07-09 ssor-prod.xlsx` | 651,579 | `71FBE24D5BC9BF49E3A7A62162466B27641185BE07E1294258D2DCE0A01E6272` |
| By Day values (`ramp_detail_vs_tsn 2026-07-23 ssor-prod.xlsx`) | 11,569,508 | `E67BFB486CDB48F71CE67E3659C70C0C7BEBEF2481171C3C678ABA2FFF865173` |
| Direct vs TSN values | 11,569,440 | `504FA4E077DE6DD489500B2BE7FB6151EAEDAEAA8907D2F917AA5233624493D3` |
| Direct RD-PDF vs TSN values | 11,578,741 | `4254F6112AD85D4442C1361DE01AD4A4F99A45DDAA14CF8A884C7A0C3FA513D5` |
| Direct self values | 11,233,909 | `57BB385AD5CFB8D05019618280A50113627A831854C9D8F34B0E4433BF69B4E9` |
| Classic env new-vs-prior values | 10,754,973 | `2568384354263C089F47042B6B7C19CEEE571ECD01545A5378C9DE6F4E4C82ED` |
| Classic env prior-vs-new values | 10,765,168 | `CFBA51F329299855C6BABC57D146FFF32EDBA829ABAD4F3BF7D4CB40B30A939E` |
| Baseline values | 10,754,972 | `5BD884245F87D3D596F9ADA7047BD9EDF820281AFD3162AB348732D5E2C19390` |
| PvE by-day values | 11,233,908 | `EB63A64CEC4E69237FB8D549AFB8E8FD38C8A1EE9374F6E5AA55142FAA51389C` |
| Everything TSN values | 11,569,528 | `DC45C9CD7F1F6A197869BC0501F633F202D0FD3D51C58ECEE647AA8086F563F7` |
| Everything ENV values | 10,739,814 | `6C722F2A26D508306FDAF22525073C743168DDF790DE6176144A547D83F0FA73` |
| Everything SELF values | 11,233,924 | `1998F19311A5D7A779094000E140A3A599E2703FE8E2B95FAAE8A6DE480129F6` |

### Neighbouring-family regression + full gate

| Gate | Result |
|---|---|
| `check_compare_intersection_detail_tsn.py`, `check_compare_consolidated_layout.py`, `check_compare_env_*`, `check_pdf_excel_matrix.py` | **PASS** (inside the full suite below) |
| RD-PDF vs TSN unchanged | **PASS** (criterion 6 above — base-vs-head cell-for-cell identical) |
| Highway Detail | **untouched** (pre-release block honored; no HD file, canary or artifact touched) |
| Full suite `build\run_checks.py -j 4 -k` | **158 passed, 0 failed of 158** (`gate_log_final.txt`) |
| `compileall` + gate-exact `ruff check scripts` | **PASS** |
| `build.ps1 -SelfTest` (frozen application self-test) | **PASS** (`selftest_log.txt`) |

## Scope and residual risk

- **Files changed: exactly the bundle's allowed surface** (the four scripts +
  the three named RD checks) plus the three neighbouring checks that pinned
  the exact RD wiring HF-04 changes (flat-schema recognizer expectation,
  field-labels force_header assertion, physical-identity fixture header) and
  the required records. No other file moved.
- **The vs-TSN 508 includes ~68 July-render-token cells** (34 Area 4 + 34
  Description) counted byte-exact against real TSN values — the same
  disclosure-only stance as the owner's PCOA-FINAL-013 ruling; suppressing
  them would be an unauthorized count-affecting normalization. Disclosed in
  the workbook Notes.
- **The classic env HG population (296 cells)** is real data movement between
  the 2026-07-09 and 2026-07-23 pulls (recounted independently from raw at
  exactly 296), not a layout artifact — a mis-mapped column would diff all
  15,208 paired rows, and identical-data mixed pairs are pinned to zero by
  `test_mixed_identical_data_is_clean`.
- **Excel-side EVIDENCE bindings for the July layout remain header-gated to
  the classic layout** (`evidence_ramp_detail.excel_column_for` pins
  `_TSMIS_HEADER`): a July-layout Excel cell reads "honestly unevidenced" if
  ever requested. Out of the allowed surface, RD evidence is audit-PROHIBITED
  anyway, and HF-05 owns the evidence contract.
- **The mixed-pair display drops nothing but asserts only the shared nine
  columns**; PM Suffix (blank on all 15,216 censused classic rows), OF and TY
  ride as context. A future classic export that carried a REAL PM suffix
  would still display it (context), never count it, on mixed pairs — a
  deliberate, documented consequence of "a column only one side exports
  cannot be compared".
- **`_LayoutDispatch` is stateful within one `_load_tsmis` call** (header_ok
  records the matched edition for the row transform); each call builds a
  fresh instance, and `load_consolidated_rows` calls header_ok exactly once
  before any transform, so no cross-call or cross-thread state exists.

## Rollback

Revert the merge commit; the previous behaviour (refusal of the July layout)
returns without data loss. Consolidated workbooks on disk stay readable either
way: classic-layout workbooks load under both trees, and a July-layout
consolidated workbook produced by this code is simply refused again by a
reverted tree (no schema/sidecar migration was introduced).

Both Prompt-05 reviews approve this branch. Complete the final-approval merge,
post-merge smoke, record, push, and bounded cleanup sequence.

## Review 1 return — Codex, 2026-08-02 (`RB3-R1-EG-001`)

Review 1 **DENIED — EVIDENCE GAP** at review-entry head `43c6336`: this record
named `rb3-a1-artifacts.json` as an identity record, but no such file existed,
and no single manifest bound the complete RB3-A1 set — frozen inputs, reused
replicas, deliverables, results, renders, gates, and committed witnesses — to
the one exact runtime head `dd922f7` by path, byte size, SHA-256,
frozen-source identity, and generation metadata. Per Prompt 05 the review
stopped at the precondition; no acceptance criterion was adjudicated. The
signed record is [REVIEW.md](REVIEW.md); the denial commit is `df5c6fc`.

## Review 1 remedy — Claude, 2026-08-02 (`RB3-R1-EG-001` CLOSED)

The missing item is supplied as ONE committed manifest plus ONE committed
independent verifier, following the RB-2 remedy precedent and its Review-2
lesson (runtime-digest equality is NOT head identity — every claimed entry
must name the exact commit):

1. **[`rb3-a1-artifacts.json`](../../rb3-a1-artifacts.json)** (committed at
   the audit root; byte-identical retained copy in the HF-04 output root)
   binds, for acceptance head `dd922f7b3b726a87912a26e92d7b5d930d90451e`:
   the per-file LF-normalized runtime set and rolled digest at that commit;
   the git lineage (that commit IS the last runtime-touching commit; the
   later commits are record/review/witness-only); all **504** frozen input
   files + the TSN raw extract by path/bytes/SHA-256 with their
   frozen-source identities; all **1,009** provisioned replica files, each
   required to hash equal to its recorded frozen source; all **106**
   deliverable files (workbooks, twins post-recalculation, sidecars,
   consolidated and normalized-TSN workbooks, the base-vs-head control
   pair); all **30** result/render/witness entries, each carrying
   `runtime_head_commit = dd922f7…`; and the ten acceptance-harness scripts
   bound by content.
2. **Frozen-source identity is proved against the ORIGINAL archives**, not
   asserted: every Ramp Detail member of the retained frozen
   `_inbox\2026-07-23 ssor-prod.zip` (252 files) and of
   `ground-truth\All Reports 7.9\All Reports 7.9.zip` (252 files) was
   decompressed and hash-matched against the exact files the acceptance
   read — 504/504 matched, zero mismatches, zero unaccounted files.
3. **The four committed HF-04 witnesses now carry the binding in their own
   content** (`bound_to_acceptance_head` + the producing script and its
   SHA-256), so a committed witness can no longer be a free-floating claim.
4. **[`rb3-verify-manifest.py`](../../rb3-verify-manifest.py)** (committed)
   re-derives everything from git and from bytes — it fails on any missing
   or mismatched file, any replica that does not equal its frozen source,
   any claimed entry not naming the exact acceptance head, any runtime file
   changed after that head, any unstamped committed witness, and any
   archive-binding mismatch. Run at the reviewed head:

   `rb3-verify-manifest.py rb3-a1-artifacts.json --tree <repo> --at dd922f7
   --corpus --zips` → **VERIFIED — 0 problem(s)** (runtime re-derived at
   `dd922f7` matches; lineage clean; 30/30 claimed entries name the head;
   4/4 witnesses bound; 1,138 corpus files re-hashed; 504 archive members
   re-bound).

No product file, deliverable, result, or count changed in this remedy: the
diff is the manifest, the verifier, the four witness stamps, and the status/
record text. The retained bulk artifacts were BOUND, not regenerated — the
return's "existing bulk artifacts may be retained if their exact bytes and
sources can be proved" branch, which the archive bindings and replica
equality checks prove.

## Review 1 re-review return — Codex, 2026-08-02 (`RB3-R1-EG-002`)

The re-review **CLOSED `RB3-R1-EG-001`** — both the cheap and the full
`--corpus --zips` verifier runs passed against the committed manifest — and
denied on one narrower gap: the committed verifier printed `SKIPPED` and
returned SUCCESS when an explicitly requested declared item was absent
(corpus roots, result files, the TSN raw input, archives), so it could
certify an incomplete acceptance set. A bounded negative probe reproduced
the false pass. No product criterion was failed or adjudicated; the denial
commit is `0554a8f`.

## Review 1 re-review remedy — Claude, 2026-08-02 (`RB3-R1-EG-002` CLOSED)

Verifier-only change (`rb3-verify-manifest.py`); the manifest, corpus,
deliverables, witnesses, and the `dd922f7` acceptance runtime are all
byte-untouched, per the return's own boundary.

1. **Fail-closed on every requested declared item**: with `--corpus`, an
   absent declared corpus root, frozen-source file, TSN raw input, replica
   root/file, deliverable root/file, retained result, or harness record is a
   recorded FAILURE (nonzero exit), never a skip; with `--zips`, so is an
   absent frozen archive. The `SKIPPED` vocabulary is gone from the corpus
   path entirely — the only remaining "not requested" wording is the
   explicit no-`--corpus` summary line, which is a mode statement, not a
   silent pass.
2. **Bounded negative checks are committed in the verifier itself**
   (`--self-test`): fabricated fixtures prove a missing declared root, a
   missing declared file, changed bytes, a replica diverging from its frozen
   source, a missing TSN raw input, a missing result, a missing archive, and
   a wrong-head or unstamped claimed entry each FAIL, and a clean fixture
   verifies with zero failures. Run: **SELF-TEST PASSED — 0 problem(s)**,
   covering exactly the reviewer's missing-root, missing-result/raw, and
   missing-archive paths.
3. **A live negative probe against the real corpus** was also run and
   restored: with one deliverable (`direct/ramp_detail vs tsn
   (values).xlsx`) temporarily renamed away, the full run reported
   `FAIL direct: missing …` and **FAILED — 1 problem(s)**; after restoring
   the file both standard commands pass again.
4. **The existing commands re-ran with the corrected verifier**: the cheap
   run (exit 0) and the full
   `rb3-verify-manifest.py rb3-a1-artifacts.json --tree <repo> --at dd922f7
   --corpus --zips` run — **VERIFIED — 0 problem(s)** (504 frozen inputs +
   TSN raw, 1,009 replicas, all deliverable roots, 30/30 results, 10 harness
   records, both 252-member archives).

## Merge closeout

- Both Codex reviews approved all seven HF-04 criteria.
- `origin/main` was fetched and remained at the recorded base
  `194b7ee8da095f0300e7e635bb7e7af78643b685`.
- RB-3 merged without force as
  `61fcac611de255c56759551a95ccd2e552287bfc`.
- The post-merge full gate passed 158/158.
- The post-merge frozen application self-test passed.
