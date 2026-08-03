# `RB-3` — Implementation Record

Status: **IMPLEMENTED — AWAITING ADVERSARIAL REVIEW**

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

Implementation head: `c9b55b6` on `hotfix/rb-3-ramp-detail-layout`.

**Frozen inputs** (identities recorded in `rb3-a1-generation.json` /
`rb3-a1-artifacts.json`):

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

<!-- RB3-A1-RESULTS -->

## Rollback

Revert the merge commit; the previous behaviour (refusal of the July layout)
returns without data loss. Consolidated workbooks on disk stay readable either
way: classic-layout workbooks load under both trees, and a July-layout
consolidated workbook produced by this code is simply refused again by a
reverted tree (no schema/sidecar migration was introduced).

Do not merge this branch. Run **Prompt 05** (`<BUNDLE_ID> = RB-3`,
`<REVIEWER> = Codex`) against the pushed head.
