# Claude Findings — Independent Output Audit

> Workflow artifact: **Stage 1B — Claude independent audit**
>
> Status: **CLAUDE ROUND 1 COMPLETE — EMBARGO MAY END**
>
> Authority: Claude-round decisions only. Do not copy, confirm, dispute, or
> summarize Codex conclusions in this file during Stage 1B.
>
> Run with
> [Prompt 01 — Claude independent audit](prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md).
> Read [START-HERE.md](START-HERE.md) and
> [AUDIT-SCOPE-AND-PROVENANCE.md](AUDIT-SCOPE-AND-PROVENANCE.md), but preserve
> the independence firewall described there.

This file is the restart-safe workspace and final record for Claude's first
round. Every cell began `UNVERIFIED` and changed only after Claude personally
inspected the generated deliverable and independently checked its source truth.
A successful process exit is not approval.

## Run record

| Field | Value |
|---|---|
| Reviewer | Claude |
| Started (UTC) | 2026-07-26 |
| Completed (UTC) | 2026-07-26 |
| Audit branch | `claude/post-comparison-output-audit` (from `main` @ `617bd52`) |
| Commit | **`c788b297bfc484748d7089bee0b99291d4264c3e`** — the frozen Stage 1B record. This SHA line is written by the single follow-up commit on top of it (a commit cannot contain its own hash). |
| Generated-comparison root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-output-audit-claude-independent-2026-07-23\` |
| Raw-check / evidence-inspection root | `<root>\inspection\` + `<root>\witness\` |
| Retained artifacts | 2,328 files / 9,253,680,327 bytes (`<root>\witness\MANIFEST.json`, path + size + sha256 for each) |
| End-user entry points exercised | `matrix.build_comparison` (Everything: env / tsn / self), `day_matrix.build_day_cell` (By Day), `baseline_matrix.build_baseline_cell` (Baseline), `pdf_excel_matrix.build_pve_cell` (PDF-vs-Excel matrix), `<adapter>.compare_folders` and `<module>.compare` (classic Compare tab), `compare_clean_highway_tsn.compare` (ArcGIS tab), `tsn_library.build_consolidated(force=True)` (TSN normalize-all) |
| Comparison cells generated | 96 across 9 production runs |
| Independence declaration | signed below |

## Independence declaration

Claude did **not** open `MASTER-VERIFICATION.md`, `CODEX-FINDINGS.md`,
`FINAL-RECONCILIATION.md`, `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` or
`IMPLEMENTATION-PLAN.md`; did **not** read anything under the Codex retained audit
root `…\_scratch\post-comparison-perfection-output-audit-2026-07-23`; did **not**
read Codex-generated comparisons, contact sheets, source-audit ledgers or the
`handoff-docs` folder; and did **not** ask another agent to summarize any embargoed
artifact. Every number in this file was produced by Claude in this round from the
frozen inputs named below, and every conclusion was reached before any Codex
material was available.

## Verdict legend

| Verdict | Meaning |
|---|---|
| `UNVERIFIED` | Claude has not personally completed the required checks |
| `APPROVED` | Deliverable, discrepancy truth, formulas, and eligible evidence pass |
| `DENIED` | A material output, truth, formula, usability, or evidence defect exists |
| `BLOCKED` | A required review-ready input is unavailable |
| `N/A` | The product intentionally does not support the combination |

Cells written `V / F` are the values / formulas verdicts, judged separately. For the
decision-arithmetic tables a cell counts once, by its **worst** sub-verdict
(`DENIED` > `BLOCKED` > `N/A` > `APPROVED`). **Every `BLOCKED` in this round is a
genuine source block** — a review-ready export the frozen inputs do not contain.
Nothing was blocked for lack of time.

## Method actually used

1. The frozen archive was extracted to the Claude-only root and copied into
   `output\2026-07-23 ssor-prod` so the By Day / Baseline / PDF-vs-Excel matrices see
   it exactly as an export run folder. The retained batch was copied to
   `output\2026-07-09 ssor-prod` and `output\2026-07-09 ars-prod`. No raw archive,
   ground-truth batch, or other auditor's output was written to.
2. The Everything-matrix destination was created through the application's own
   ownership API (`owned_dir.ensure_owned_dir(..., kind="store")`) and filled with the
   frozen exports. Column slots: `ssor-prod` = NEW 2026-07-23 (matrix baseline),
   `ssor-test` = PRIOR 2026-07-09 **ssor-prod** (the slot name is only a matrix column
   label — the provenance is recorded here so it is never mistaken for real
   test-environment data), `ars-prod` = PRIOR 2026-07-09 ars-prod.
3. The whole supported TSN library was re-normalized with
   `tsn_library.build_consolidated(report, force=True)` — the same call the GUI's
   per-report *Rebuild* and *rebuild every out-of-date report* buttons make.
4. Every comparison was produced through the production dispatch functions listed in
   the run record, never through a lower-level shortcut.
5. Source truth was recounted with readers written for this audit that import no
   application module (`inspection\recount_*.py`), and PDFs were read directly with
   pdfplumber rather than through the app's parsers.
6. Formula twins were recalculated with the installed Excel 16.0
   (`CalculateFullRebuild`, saved data-only) and compared cell-for-cell with their
   values twins.

## Frozen-input coverage proof

Witness: `<root>\witness\inv_sources.json`, `<root>\inspection\inv_sources.py`.

NEW `2026-07-23 ssor-prod` — 12 subdirs, every family complete, siblings
route-for-route identical, no duplicate route tokens, no zero-byte file:

| subdir | files | ext | unique routes |
|---|---:|---|---:|
| `highway_log` | 252 | xlsx | 252 |
| `highway_log_pdf` | 252 | pdf | 252 |
| `highway_sequence` | 252 | xlsx | 252 |
| `highway_sequence_pdf` | 252 | pdf | 252 |
| `intersection_detail` | 217 | xlsx | 217 |
| `intersection_detail_pdf` | 217 | pdf | 217 |
| `intersection_summary` | 217 | xlsx | 217 |
| `intersection_summary_pdf` | 217 | pdf | 217 |
| `ramp_detail` | 126 | xlsx | 126 |
| `ramp_detail_pdf` | 126 | pdf | 126 |
| `ramp_summary` | 126 | pdf | 126 |
| `ramp_summary_excel` | 126 | xlsx | 126 |

**Absent from the frozen archive: `highway_detail`, `highway_detail_pdf`,
`highway_summary`.** Every Highway Detail cell is therefore source-blocked, in line
with the scope document's instruction that historical files do not make the pair
review-ready.

Retained batch `All Reports 7.9`:

* `2026-07-09 ssor-prod` — `highway_detail`, `intersection_detail` and
  `intersection_detail_pdf` are **empty folders**; there is no
  `intersection_summary_pdf` folder. Everything else is complete.
* `2026-07-09 ars-prod` — `highway_detail` 252, `highway_detail_pdf` 252,
  `intersection_detail` 217, `intersection_detail_pdf` 217, `intersection_summary`
  217, `intersection_summary_pdf` 217. This is the **ARS** data source, so it is used
  only as a secondary, clearly-labelled column.

## TSN normalize-all record

`tsn_library.build_consolidated(report, force=True)` for every registered dataset
(witness `<root>\witness\tsn_rebuild_all.json`):

| dataset | result | normalization version | the print's own report date |
|---|---|---:|---|
| `highway_log` | ok | 5 | 09/15/25 (OTM52010, 12 district prints) |
| `ramp_detail` | ok | 5 | extract named `…11.04.2025…` |
| `ramp_summary` | ok | 3 | 09/15/2025 (OTM22270, event 4843742) |
| `intersection_summary` | ok | 3 | 09/15/2025 (OTM22250, event 4843738) |
| `intersection_detail` | ok | 5 | 2025-09 extract |
| `highway_sequence` | ok | 4 | 15-SEP-25 (OTM22025, 12 district prints) |
| `highway_detail` | ok | 3 | 2025-09 extract |
| `clean_highway` | ok | 1 | `CA HIGHWAYS 09.08.2025.xlsx` |
| `clean_intersection` | **unsupported** | — | staged; refused: "no normalizer yet" |
| `clean_ramp` | **unsupported** | — | staged; refused: "no normalizer yet" |

**Material context for every vs-TSN cell:** the TSN side is a **2025-09** print while
the TSMIS side is a **2026-07-23** pull — a ten-month gap. High vs-TSN difference
counts are therefore expected and are not, by themselves, product defects. That gap is
exactly the fact PCOA-CL-002 removes from the deliverable.

## Deliverable decision matrix — 88 decisions

### Matrix A — classic new-batch vs retained-batch comparison (12)

Classic Compare tab, `adapter.compare_folders(new, retained, out, mode="both")`.
Outputs in `<root>\generated-comparisons\direct-env\`.

| Report family | Values / formulas | Output paths | Source recount and adversarial notes |
|---|---|---|---|
| Ramp Summary | APPROVED / APPROVED | `ramp_summary new-vs-prior-ssor{,(values)}.xlsx` | 126 paired, 0 one-sided, 4,032 asserted, 67 differing in 15 rows. Route 001 verified cell-for-cell against BOTH raw PDFs (VC-1); per-field breakdown sums to 67; formulas twin recalculated, 0 errors, 0 real value differences (VC-3). |
| Ramp Detail | DENIED / DENIED | none produced | PCOA-CL-001 — the 2026-07-23 export layout is refused; no workbook of either kind exists. PCOA-CL-004 — the message misdiagnoses it. |
| Highway Sequence Listing | APPROVED / APPROVED | `highway_sequence new-vs-prior-ssor{,(values)}.xlsx` | 1,931 / 1,919 / 60,248 / 6 / 246. Complete statewide independent recount: row universe, one-sided counts and differing-row count all EXACT; 1,929 vs 1,931 cells (0.10%) from my own tie-break (VC-2, VC-6). Formulas twin recalculated over 4,535,641 cells: 0 errors, 0 real differences. |
| Highway Log | APPROVED / APPROVED | `highway_log new-vs-prior-ssor{,(values)}.xlsx` | 89,811 / 22,486 / 50,327 / 2,494 / 1,557. Route-001 recount EXACT on pairing; 12,999 vs my raw 13,036 cells = 37 absorbed by documented normalizations (VC-7). Formulas twin recalculated over 11,118,720 cells: 0 errors, 0 real differences. |
| Intersection Summary | APPROVED / APPROVED | `intersection_summary new-vs-prior-ssor{,(values)}.xlsx` | 16 / 7 / 217 / 0 / 0. WHOLE-FAMILY independent recount over all 434 raw exports reproduces every route/label/value triple exactly (VC-4). Formulas twin recalculated clean. |
| Intersection Detail | BLOCKED / BLOCKED | none produced | `BLOCKED (source)` — the retained SSOR batch's `intersection_detail` folder is empty. The ARS-sourced comparison is judged in Matrix C. |
| Highway Log (PDF) | APPROVED / APPROVED | `highway_log_pdf new-vs-prior-ssor{,(values)}.xlsx` | 88,238 / 22,724 / 50,712 / 2,095 / 1,174, 14,872 context cells (the print's ditto domain; the Excel edition has none). Sibling difference traced to 4 routes (PCOA-CL-013). |
| Intersection Detail (PDF) | BLOCKED / BLOCKED | none produced | `BLOCKED (source)` — retained SSOR side empty. Also the witness for PCOA-CL-012 (429.4 s spent parsing side A first). |
| Highway Detail | BLOCKED / BLOCKED | none produced | `BLOCKED (source)` — absent from the frozen archive. |
| Highway Detail (PDF) | BLOCKED / BLOCKED | none produced | `BLOCKED (source)` — absent from the frozen archive. |
| Highway Sequence Listing (PDF) | APPROVED / APPROVED | `highway_sequence_pdf new-vs-prior-ssor{,(values)}.xlsx` | 1,904 / 1,895 / 60,247 / 7 / 246 — reproduces the Excel edition's statewide result to within 1 row and 27 cells of 481,976 asserted (0.006%); the whole sibling difference is route 010's 2026-07-09 side. |
| Ramp Detail (PDF) | APPROVED / APPROVED | `ramp_detail_pdf new-vs-prior-ssor{,(values)}.xlsx` | 376 / 316 / 15,208 / 5 / 8. Per field HG 296, Area 4 20, Description 20, On/Off 20, Ramp Type 20; all others 0. **The PDF edition of Ramp Detail compares perfectly while the Excel edition is refused** — the family is only half verifiable. |

Also generated as a labelled secondary column (new 2026-07-23 vs retained **ARS**
2026-07-09): `intersection_detail` 17,563 / 16,459 / 0 / 0,
`intersection_detail_pdf` 17,562 (a **one-cell** sibling difference in 559,606),
`intersection_summary` 16 / 7 / 217 — identical to the SSOR pair.

### Matrix B — TSMIS vs freshly normalized TSN (36)

Direct = classic Compare tab file comparison; By Day = `day_matrix.build_day_cell`;
Everything = `matrix.build_comparison(..., "tsn", ...)`.

**Every By Day and Everything cell that produced a workbook is `DENIED` on
PCOA-CL-002 + PCOA-CL-003.** The discrepancy numbers are true — they are identical to
the Direct path's, cell for cell — but the deliverable carries a false "rebuild the TSN
library" instruction and names a `%TEMP%` path as its TSN input. The classic Direct
path is clean on both counts (controlled differential across four families, VC-8).

| Report family | Direct V / F | By Day V / F | Everything V / F | Output paths and adversarial notes |
|---|---|---|---|---|
| Ramp Summary | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 23 / 23 / 29 / 0 / 2. Every TSN category verified against the raw statewide print (VC-9). |
| Ramp Detail | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | PCOA-CL-001 — refused on all three paths. |
| Highway Sequence Listing | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 5,573 / 4,883 / 57,050 / 3,204 / 12,754. Its three whole-column CONTEXT fields are reported as `0` in the Summary (PCOA-CL-011). |
| Highway Log | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 84,709 / 38,478 / 49,195 / 3,626 / 10,888. |
| Intersection Summary | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 53 / 53 / 58 / 8 / 0. TSN side verified against the raw print; the 8 TSMIS-only rows are newer TASAS classes (VC-9). |
| Intersection Detail | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 5,092 / 2,816 / 16,199 / 260 / 427. ML Eff-Date differences verified at the source (VC-10). Discloses no TSN print identity on ANY path. |
| Highway Log (PDF) | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 84,202 / 38,931 / 49,829 / 2,978 / 10,254 — the print pairs 634 MORE rows against TSN than the Excel export, confirming the PDF consolidator's premise. |
| Intersection Detail (PDF) | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 5,092 / 2,816 / 16,199 / 260 / 427 — byte-identical to the Excel edition's vs-TSN result. |
| Highway Detail | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED / BLOCKED | `BLOCKED (source)` — "The TSMIS file doesn't exist". |
| Highway Detail (PDF) | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED / BLOCKED | `BLOCKED (source)`. |
| Highway Sequence Listing (PDF) | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 4,974 / 4,892 / 57,483 / 2,771 / 12,321 — again the print matches TSN better than the Excel export. |
| Ramp Detail (PDF) | APPROVED / APPROVED | DENIED / DENIED | DENIED / DENIED | 619 / 468 / 15,204 / 9 / 206. |

### Matrix C — Baseline and Everything environment paths (24)

Baseline = `baseline_matrix.build_baseline_cell(2026-07-23 vs day:2026-07-09)`;
Everything ENV = `matrix.build_comparison(..., "env", ...)` for the `ssor-test`
(retained SSOR pull) and `ars-prod` columns against the `ssor-prod` baseline.

| Report family | Baseline V / F | Everything ENV V / F | Output paths and adversarial notes |
|---|---|---|---|
| Ramp Summary | APPROVED / APPROVED | APPROVED / APPROVED | 67 / 15 / 126 / 0 / 0 on both, identical to Matrix A (three-way parity, VC-11). |
| Ramp Detail | DENIED / DENIED | DENIED / DENIED | PCOA-CL-001. |
| Highway Sequence Listing | APPROVED / APPROVED | APPROVED / APPROVED | 1,931 / 1,919 / 60,248 / 6 / 246 on both. |
| Highway Log | APPROVED / APPROVED | APPROVED / APPROVED | 89,811 / 22,486 / 50,327 / 2,494 / 1,557 on both. |
| Intersection Summary | APPROVED / APPROVED | APPROVED / APPROVED | 16 / 7 / 217 / 0 / 0 on both and on the ARS column. |
| Intersection Detail | BLOCKED / BLOCKED | APPROVED / APPROVED | Baseline `BLOCKED (source)` (retained SSOR folder empty). Everything ENV runs against the retained ARS column: 16,459 paired, 0 one-sided, 16,328 differing rows concentrated in 4 of 35 columns, verified at the source (VC-12). |
| Highway Log (PDF) | APPROVED / APPROVED | APPROVED / APPROVED | 88,238 / 22,724 / 50,712 on both, identical to Matrix A. |
| Intersection Detail (PDF) | BLOCKED / BLOCKED | APPROVED / APPROVED | Baseline `BLOCKED (source)`; Everything ENV on the ARS column 17,562 / 16,459 / 0 / 0. |
| Highway Detail | BLOCKED / BLOCKED | BLOCKED / BLOCKED | `BLOCKED (source)` on the 2026-07-23 side. |
| Highway Detail (PDF) | BLOCKED / BLOCKED | BLOCKED / BLOCKED | `BLOCKED (source)`. Its ARS-column attempt is the worst PCOA-CL-012 witness (1,229.7 s before reporting the missing side). |
| Highway Sequence Listing (PDF) | APPROVED / APPROVED | APPROVED / APPROVED | 1,904 / 1,895 / 60,247 on both, identical to Matrix A. |
| Ramp Detail (PDF) | APPROVED / APPROVED | APPROVED / APPROVED | 376 / 316 / 15,208 on both, identical to Matrix A. |

### Matrix D — same-day PDF-vs-Excel self-consistency (14)

Direct = classic Compare tab file comparison; Everything SELF =
`matrix.build_comparison(..., "vs_pdf"/"vs_excel", ...)`. The PDF-vs-Excel by-day
matrix was run as a third corroborating path and agreed with both on every family.

| Report family | Direct V / F | Everything SELF V / F | Evidence eligibility | Output paths and adversarial notes |
|---|---|---|---|---|
| Ramp Detail | DENIED / DENIED | DENIED / DENIED | PROHIBITED | Refused on all three paths — the Excel side is PCOA-CL-001. |
| Highway Sequence Listing | APPROVED / APPROVED | APPROVED / APPROVED | PROHIBITED | 3,714 / 1,395 / 60,254 / 0 / 0 on all three paths. Identical row universe; by field PM Suffix 547 · HG 929 · FT 1,119 · Description 1,119. Which edition is right needs source adjudication — recorded, not attributed. |
| Highway Log | APPROVED / APPROVED | APPROVED / APPROVED | PROHIBITED | 3,090 / 1,363 / 52,140 / 667 / 681 on all three paths, and it **catches a real export data loss** — see PCOA-CL-017. |
| Intersection Detail | APPROVED / APPROVED | APPROVED / APPROVED | PROHIBITED | **0 differing cells** across 16,459 paired rows and 0 one-sided rows — the PDF parser reproduces the Excel export exactly. |
| Ramp Summary | N/A / N/A | N/A / N/A | N/A | No PDF-vs-Excel comparator is registered even though BOTH editions are exported (126 PDF + 126 XLSX) — PCOA-CL-007. |
| Intersection Summary | N/A / N/A | N/A / N/A | N/A | Same: 217 XLSX + 217 PDF exported, no self comparator — PCOA-CL-007. |
| Highway Detail | BLOCKED / BLOCKED | BLOCKED / BLOCKED | PROHIBITED | `BLOCKED (source)`. |

### Matrix F — Clean Road Files supplemental comparison (2)

| Deliverable | Verdict | Output path | Independent source trace and adversarial notes |
|---|---|---|---|
| Values | APPROVED | `<root>\generated-comparisons\arcgis\clean_highway arcgis-vs-tsn (values).xlsx` | Run through `tsn_library.build_consolidated('clean_highway')` → `compare_clean_highway_tsn.compare(..., mode="both")`, 2,640.6 s. 52,647 paired · 5,081 ArcGIS-only · 7,436 TSN-only · **291,292 differing cells** — reproduces the repo's blessed `CRH-SW-E2` canary EXACTLY, after a forced re-normalization of the clean_highway library on this machine. |
| Formulas | APPROVED | `…\clean_highway arcgis-vs-tsn.xlsx` | Same committed generation `945b19d6…`, byte-equal typed outcome. Excel recalculation of the 433 MB twin was **not** attempted (the 90 MB Highway Log twin alone took ~50 minutes); the verdict rests on the shared generation, the equal typed outcome, and the 15.7 M recalculated cells proven clean across five sibling comparisons built by the same `compare_core` formula writer. This limitation is stated rather than hidden. |

**Clean Road Intersection / Clean Road Ramp are `N/A` for the product:**
`tsn_load_clean_road` has no normalizer for either and the library rebuild refuses them
by design ("the files are staged, but this report has no normalizer yet — its
ArcGIS-side build and comparison haven't been integrated (Highway went first)"). No
comparison path was invented for them.

### Decision arithmetic

| Matrix | Expected | Closed | Approved | Denied | Blocked | N/A |
|---|---:|---:|---:|---:|---:|---:|
| A | 12 | 12 | 7 | 1 | 4 | 0 |
| B | 36 | 36 | 9 | 21 | 6 | 0 |
| C | 24 | 24 | 16 | 2 | 6 | 0 |
| D | 14 | 14 | 6 | 2 | 2 | 4 |
| F | 2 | 2 | 2 | 0 | 0 | 0 |
| **Total** | **88** | **88** | **40** | **26** | **18** | **4** |

Computed by `<root>\inspection\arith.py` from `<root>\inspection\verdicts.json`, so the
tables and the totals cannot drift.

## Exact Everything evidence matrix — 25 cells

Eligibility follows the audit rule: evidence is required only when **both semantic
sources are PDFs**, and prohibited when either semantic side is Excel or a normalized
XLSX even if a sibling PDF exists. Applied to this product:

* the TSMIS side of a `*_pdf` row is the PDF export; the TSMIS side of an Excel row is
  the workbook (`visual_evidence.tsmis_source_role`);
* the TSN side is a PDF only for `highway_log` and `highway_sequence`, whose library
  **raw** is the district prints (`visual_evidence._TSN_PDFS_IN_RAW`); for Intersection
  Detail, Ramp Detail and Highway Detail the compared TSN side is a statewide **XLSX**
  and the `pdf/` folder holds a different document;
* cross-environment mode has no evidence code path at all
  (`matrix_build.build_cell_comparison` takes no evidence argument) — confirmed
  empirically: no `*evidence*` artifact exists anywhere under the env, baseline or
  PDF-vs-Excel trees.

### Environment comparisons (10)

| Report key | Eligibility | Availability / count | Every image inspected | Verdict | Notes |
|---|---|---:|---|---|---|
| `ramp_summary` | eligible (PDF/PDF) | 0 | n/a | N/A | No env evidence path exists; nothing leaked. Counted in PCOA-CL-014. |
| `ramp_detail` | PROHIBITED (Excel/Excel) | 0 | n/a | N/A | No leakage. |
| `intersection_summary` | PROHIBITED | 0 | n/a | N/A | No leakage; the row is not evidence-capable either. |
| `intersection_detail` | PROHIBITED | 0 | n/a | N/A | No leakage. |
| `intersection_detail_pdf` | eligible (PDF/PDF) | 0 | n/a | N/A | No env evidence path. PCOA-CL-014. |
| `ramp_detail_pdf` | eligible (PDF/PDF) | 0 | n/a | N/A | No env evidence path. PCOA-CL-014. |
| `highway_sequence` | PROHIBITED | 0 | n/a | N/A | No leakage. |
| `highway_log` | PROHIBITED | 0 | n/a | N/A | No leakage. |
| `highway_log_pdf` | eligible (PDF/PDF) | 0 | n/a | N/A | No env evidence path. PCOA-CL-014. |
| `highway_sequence_pdf` | eligible (PDF/PDF) | 0 | n/a | N/A | No env evidence path. PCOA-CL-014. |

### TSN comparisons (10)

| Report key | Eligibility | Availability / count | Every image inspected | Verdict | Notes |
|---|---|---:|---|---|---|
| `ramp_summary` | PROHIBITED | 0 | n/a | N/A | Not evidence-capable; nothing produced on any path. |
| `ramp_detail` | PROHIBITED | 0 | n/a | BLOCKED | The comparison itself is refused (PCOA-CL-001), so no evidence could exist. |
| `intersection_summary` | PROHIBITED | 0 | n/a | N/A | Not evidence-capable; nothing produced. |
| `intersection_detail` | PROHIBITED (Excel side + XLSX-sourced TSN) | 140 images / 70 examples / 25 cols | value fidelity 70/70; 1 at full resolution | DENIED | Generated where prohibited; the TSN panel is drawn from `pdf\Intersection Detail Statewide_TSN.pdf` while the comparison read `tsn_intersection_detail_normalized.xlsx` (PCOA-CL-010). Ledger exhaustive, "Why no example" empty on every row. |
| `intersection_detail_pdf` | PROHIBITED (XLSX-sourced TSN) | 142 images / 25 cols | value fidelity 100%; sampled at full resolution | DENIED | read_set is PDF-only (80 PDFs) yet still prohibited — the compared TSN source was the XLSX. This is the case that proves a "PDF-only read set" test is insufficient (PCOA-CL-010). |
| `ramp_detail_pdf` | PROHIBITED (XLSX-sourced TSN) | 50 images / 9 cols | value fidelity 100% | DENIED | Same pattern: 40 PDFs read, TSN panel from `pdf\Ramp Detail Statewide_TSN.pdf`, comparison read the normalized XLSX. |
| `highway_sequence` | PROHIBITED (Excel side) | 12 images / 6 examples / 2 cols | value fidelity 6/6; **12/12 at full resolution** | DENIED | read_set 1 xlsx + 12 pdf; 2 of 6 examples show a truncated value (PCOA-CL-015); the workbook claims "each source PDF" and names a TSMIS PDF folder it never read (PCOA-CL-010). |
| `highway_log` | PROHIBITED (Excel side) | 176 images / 88 examples / 30 cols | value fidelity 88/88; sampled at full resolution | DENIED | Same class; 1 of 88 truncated. |
| `highway_log_pdf` | **REQUIRED** (PDF/PDF) | 180 images / 90 examples / 30 cols | value fidelity 90/90; 3 at full resolution | DENIED | read_set correctly **123 PDFs, zero xlsx** — but a blank TSN Description boxes the WRONG RECORD (PCOA-CL-016). |
| `highway_sequence_pdf` | **REQUIRED** (PDF/PDF) | 12 images / 6 examples / 2 cols | value fidelity 6/6; 2 at full resolution | **APPROVED** | read_set 29 PDFs, zero xlsx (17 TSMIS prints + the 12 TSN district prints that ARE the compared library's raw). Full 39-character values rendered untruncated; a blank TSMIS FT is boxed cleanly in the empty column; the TSN target box is tight. |

### Self-comparisons (5)

| Report key | Eligibility | Availability / count | Every image inspected | Verdict | Notes |
|---|---|---:|---|---|---|
| `ramp_detail_pdf` | PROHIBITED | 0 | n/a | BLOCKED | The self comparison is refused (PCOA-CL-001), so no evidence could exist. |
| `highway_sequence_pdf` | PROHIBITED | 18 images / 3 cols | value fidelity 100% | DENIED | read_set 1 xlsx + 30 pdf — generated where prohibited. |
| `intersection_detail_pdf` | PROHIBITED | manifest only, 0 images | n/a | N/A | The comparison found **0 differences**, so the generator wrote a `state: no_differences` manifest with an empty read set and the note "the published comparison counts no differing columns to illustrate". Honest and compliant; the prohibition was never exercised. |
| `highway_log` | PROHIBITED | 164 images / 82 examples / 28 cols | value fidelity 82/82 | DENIED | read_set 1 xlsx + 2 pdf — generated where prohibited. |
| `highway_log_pdf` | PROHIBITED | 164 images / 28 cols | value fidelity 100% | DENIED | The mirrored row of the same comparison; same prohibited generation. |

**Decisive contrast:** the SAME Highway Log PDF-vs-Excel comparison, with the SAME
typed outcome, runs on three production paths — the classic Compare tab and the
PDF-vs-Excel by-day matrix write **no evidence at all** (correct), and only
`matrix_build._run_self_evidence` writes it. The product already implements the rule
correctly on two of three paths.

### Evidence arithmetic

| Expected | Closed | Approved | Denied | Blocked | N/A |
|---:|---:|---:|---:|---:|---:|
| 25 | 25 | 1 | 9 | 2 | 13 |

**Image-inspection method, stated honestly.** 380+ evidence images were produced. The
value-fidelity property — whether the drawn string equals the compared value — was
verified **programmatically for 100 % of the rendered examples** (each evidence
workbook's Summary carries the full compared value; the Excel-panel renderer draws
`text[:26]`). Nineteen images were additionally inspected at full resolution, chosen to
cover both layouts (pair + stacked), all four report families that produced evidence,
blank-vs-populated targets on both sides, truncated-vs-untruncated values, and both
audit-REQUIRED PDF/PDF cells. Every defect reported below was found that way.

## Claude findings

### PCOA-CL-001 — P1 — The 2026-07-23 Ramp Detail (Excel) export layout is refused end to end, and the consolidator still writes a workbook nothing can read

* **Affected cells** — Matrix A `Ramp Detail`; Matrix B `Ramp Detail` ×3; Matrix C
  `Ramp Detail` ×2; Matrix D `Ramp Detail` ×2. Values **and** formulas: no workbook of
  either kind is produced. Nine of the twelve Ramp Detail decisions.
* **Observed** — the dev-site Ramp Detail Excel export changed shape:

  | | header |
  |---|---|
  | 2026-07-09 | `Location`, ``, `PM`, `Date of Record`, ``, `HG`, `Area 4`, ``, `City Code`, `R/U`, `Description` |
  | 2026-07-23 | `Location`, `PRE`, `PM`, `Date of Record`, `HG`, `Area 4`, `City Code`, `R/U`, `OF`, `TY`, `Description` |

  The blank labels are gone and the two previously print-only columns (`OF` = On/Off,
  `TY` = Ramp Type) are now IN the Excel export. Values MOVED, they were not merely
  relabelled: prior row 2 is
  `12-ORA-001 | R | 000.606 | 02/25/1976 | (blank) | D | Y | DAPT | U | 001/NB OFF… | (blank)`
  and the new row 2 is
  `12-ORA-001 | R | 000.606 | 02/25/1976 | D | Y | DAPT | U | F | D | 001/NB OFF…`.
  The app pins Ramp Detail to exactly one layout
  (`compare_env._ramp_detail_canonical_header` → `compare_ramp_detail_tsn._TSMIS_HEADER[1:]`),
  so refusal is the CORRECT engine behaviour — but:
  * the classic cross-environment, Everything, By Day, Baseline, PDF-vs-Excel matrix
    and classic vs-TSN paths all refuse;
  * **`consolidate_ramp_detail.consolidate` nevertheless succeeds** (126/126 routes,
    `status=ok`), writing `tsar_ramp_detail_consolidated.xlsx` with header
    `Route, Location, PRE, PM, Date of Record, HG, Area 4, City Code, R/U, OF, TY, Description`
    — a workbook no comparator in the product accepts.
* **Impact** — a user who exports Ramp Detail from the current dev site gets a green
  consolidation and then a refusal from every comparison, with no instruction that will
  ever succeed (PCOA-CL-004). Only the PDF edition of the family remains verifiable.
* **Root cause (verified)** — site-side export change + a single pinned header.
  **Hypothesis (not verified)** — that the change will reach the permanent site; the
  scope document forbids assuming main-site equivalence.
* **Witnesses** — `<root>\witness\header_census.json`, `run_direct_env.json`,
  `run_everything_tsn.json`, `run_byday_2026-07-23.json`, `run_fast.json`,
  `run_baseline_pve_pve.json`, `<root>\inspection\probe_rd_consolidated.xlsx`.

### PCOA-CL-002 — P1 — The private TSN capture strips `tsn_source_claims`, so every matrix-path vs-TSN deliverable loses the TSN print's identity and prints a false "rebuild the TSN library" instruction

* **Affected cells** — every Matrix B `By Day` and `Everything` cell (20 decisions).
* **Observed** — `matrix_build.captured_tsn_workbook` copies the normalized TSN
  workbook into `%TEMP%\tsmis-tsn-consumer-*` and writes a REDUCED outcome sidecar:

  ```
  library  …_normalized.xlsx.outcome.json   1224 bytes
           …, tsn_source_claims, tsn_normalization_version, tsn_raw_manifest,
           tsn_normalized_workbook_identity, tsn_artifact_identity_token
  captured …_normalized.xlsx.outcome.json    159 bytes
           schema_version, completion, skipped_inputs, failed_inputs,
           built_at_mtime, producer_app_version
  ```

  The comparator reads the claims from beside the path it was handed
  (`compare_ramp_summary_tsn.py:347`), so on the matrix path it always finds none and
  writes the fallback (`claims_notes`, line 153) onto the user-facing sheet:

  > `TSN print: no source-claims record beside this normalized workbook (older
  > normalization) — rebuild the TSN library to capture the print identity.`
* **Controlled differential (VC-8)** — the same library workbooks, compared through the
  classic Direct path minutes later, print the real identity for all four comparators
  that expose it: `OTM22270 · Event 4843742 · reference 09/15/2025 · TRLBUGNI`
  (Ramp Summary), `OTM22250 · Event 4843738 · 09/15/2025` (Intersection Summary),
  `OTM52010 California State Highway Log · report 09/15/25` (Highway Log),
  `OTM22025 Highway Locations · report 15-SEP-25` (Highway Sequence).
* **Impact** — (a) a categorically false instruction: the advised rebuild cannot change
  the outcome, so the user is sent into a loop; (b) the deliverable loses the one fact
  that makes it interpretable — that the TSN side is a 2025-09 print being diffed
  against a 2026-07-23 pull. Intersection Detail, Ramp Detail and Highway Detail never
  expose TSN identity on any path, so the net effect is that **no vs-TSN deliverable
  produced through the Everything or By Day matrix discloses its TSN vintage.**
* **Witnesses** — `ssor-prod_ramp_summary_tsn.xlsx` (*Summary by Category*),
  `ssor-prod_highway_sequence_tsn.xlsx` (*Notes*), the library sidecars, the captured
  sidecar in `<root>\witness\temp_captures.txt`,
  `<root>\generated-comparisons\direct-tsn-probe\` and `\direct-tsn\`.

### PCOA-CL-003 — P2 — The vs-TSN Provenance sheet and provenance sidecar name a transient `%TEMP%` capture path as the TSN input

The user-facing *Provenance* sheet of `ssor-prod_ramp_summary_tsn.xlsx` records
`TSN | C:\Users\Yunus\AppData\Local\Temp\tsmis-tsn-consumer-aec_pjwy\tsn_ramp_summary_normalized.xlsx`,
and `.provenance.json` records the same string as `inputs[1].selection`. That directory
is removed after the run. The classic Direct path records the real
`tsn_library\<report>\consolidated\…` path for every family. The sha256 is correct in
both, so the record is verifiable but not actionable — the sheet that exists to answer
"what did this workbook compare?" points at a path the user can never inspect.
Affects every Matrix B `By Day` / `Everything` cell.

### PCOA-CL-004 — P2 — Ramp Detail's refusal message misdiagnoses the failure and prescribes an action that cannot work

`compare_ramp_detail_tsn._load_tsmis` passes
`bad_header_msg="isn't a CONSOLIDATED Ramp Detail workbook (expected a leading 'Route'
column) — consolidate the per-route exports first."` The workbook that triggers it
**has** a leading `Route` column; the real gate is
`ctc.exact_consolidated_header_ok(_TSMIS_HEADER)`. Re-consolidating reproduces the same
header and fails identically. Both sibling reports get this right — Intersection Detail
names "the current (July 2026) site format" and Highway Detail names "the exact
34-column export header". The message sends the user to repeat a step that already
succeeded and hides the reportable fact.

### PCOA-CL-005 — P3 — Private TSN capture directories are left behind in `%TEMP%`

Three `%TEMP%\tsmis-tsn-consumer-*` directories survive on this machine: one from
2026-07-20 (emptied, not removed), one from 2026-07-23 still holding a 2,542,538-byte
`tsn_highway_sequence_normalized.xlsx` plus its sidecar, and one belonging to a run in
flight. Unbounded `%TEMP%` growth proportional to (vs-TSN runs × dataset size; the
Highway Detail dataset is 8.5 MB per capture) on exactly the locked-down work PCs where
the user cannot clean up with a script. Witness `<root>\witness\temp_captures.txt`.

### PCOA-CL-006 — P3 — TSN normalization is not identity-deterministic: a forced rebuild from unchanged raw invalidates every bound comparison generation

The whole library was force-rebuilt from raw whose `tsn_raw_manifest.sha256` and
`normalization_version` were unchanged. All eight datasets came back with a **different**
`tsn_normalized_workbook_identity` and `tsn_artifact_identity_token` (Highway Log
`…81cc9842…` → `…374a3a03…`). Since that token binds a committed comparison generation
to its TSN source, any use of the GUI's *Rebuild* buttons silently invalidates every
existing vs-TSN comparison even when nothing changed, forcing a full statewide
re-comparison. **Root cause is a hypothesis, not verified** (openpyxl writes a fresh
document timestamp; the pre-rebuild bytes were replaced and cannot be re-diffed).
Witness `<root>\witness\tsn_rebuild_all.json`.

### PCOA-CL-007 — P3 — Three enabled report editions have no verification path at all

`report_catalog` enables `ramp_summary_excel`, `intersection_summary_pdf` and
`highway_summary` for export (none is in `reports.DISABLED_EXPORT_SUBDIRS`), yet none
has a consolidator, a `report_catalog.MATRIX` row, or any comparison recipe. In the
frozen archive that is 126 `ramp_summary_excel` XLSX + 217 `intersection_summary_pdf`
PDF = **343 of the 2,380 exported route files (14.4 %)** that no workflow can check.
Ramp Summary is verified through its PDF edition while its Excel sibling is
unverifiable; Intersection Summary is the exact inverse. This is also why Matrix D's
Ramp Summary and Intersection Summary rows are `N/A` even though both editions of both
reports sit on disk. Witness `<root>\witness\export_coverage.txt`.

### PCOA-CL-008 — P3 — In the VALUES twin the headline verdict is an uncached formula

The values workbook's `Summary!B3` (the `✗ DIFFERENCES FOUND — …` / `✓` headline) and
`Summary!C56:C62` (the SELF-CHECK results) are live formulas written without a cached
value; read data-only they are empty and only appear once a calculating application
opens the file. The workbook's own note discloses the SELF-CHECK rows ("only the Spot
Check sheet and the SELF-CHECK rows stay live") but not the headline. The single most
important line of the deliverable is therefore blank in any consumer that does not
recalculate. The Comparison sheet's `… Row` hyperlink columns are in the same class but
are navigational, not informational.

### PCOA-CL-009 — P3 — Site-side export changes observed in the frozen archive (recorded, not a product defect)

* A stray leading **`GENERATE`** line is now the first text line of the `ramp_summary`,
  `ramp_detail_pdf`, `intersection_detail_pdf` and `intersection_summary_pdf` prints;
  absent from the retained batch.
* The **Highway Sequence Listing (PDF)** print was re-skinned from
  `California Department of Transportation / Highway Sequence Listing` to the TASAS
  layout `TASAS / Traffic Accident Surveillance and Analysis System / HIGHWAY SEQUENCE
  LISTING (W/CITIES)`, with a wider text measure. **The app's parser absorbs both**
  (route 001 → 2,581 rows from the new print, 2,583 from the prior print), so this is
  validated clean; it is flagged because a future parser change must keep both.
  Witness `<root>\witness\pdf_head_census.txt`.

### PCOA-CL-010 — P2 — vs-TSN and self evidence is generated where the audit rule prohibits it, and the evidence workbook then describes sources it did not read

For `highway_sequence` and `highway_log` (the Excel rows) the compared TSMIS side is the
consolidated **XLSX**; for `intersection_detail`, `intersection_detail_pdf` and
`ramp_detail_pdf` the compared TSN side is a normalized **XLSX** while the TSN panel is
rendered from a print in `tsn_library\<report>\pdf\` that was never compared; for all
five self cells one side is Excel by construction. Evidence is produced in every one of
those cases, on both the Everything and By Day paths. Two concrete proofs:

* the manifest read sets are `1 TSMIS xlsx + 12 TSN pdf` (HL/HSL vs TSN) and
  `1 xlsx + 2 pdf` / `1 xlsx + 30 pdf` (self) — never PDF-only;
* the evidence workbook nonetheless asserts *"Red box = the compared cell in each source
  **PDF**"* on every image sheet, and its Summary declares
  `TSMIS PDFs: …\ssor-prod\highway_sequence_pdf` — a directory whose files appear
  nowhere in the read set.

**A PDF-only read set is not sufficient.** `intersection_detail_pdf` vs TSN reads 80
PDFs and zero XLSX, yet its TSN panel still comes from a different document than the one
compared. The correct test is "every read-set member is the document the corresponding
side was compared from", not "every read-set member is a PDF".

### PCOA-CL-011 — P2 — The per-field difference table reports never-compared CONTEXT columns as `0` differences

On `ssor-prod_highway_sequence_tsn.xlsx` the Summary's *DIFFERENCES BY FIELD* table
lists `City | I | 0`, `HG | J | 0` and `Distance To Next Point | L | 0` — visually
identical to a genuinely identical compared column. Those three are CONTEXT columns that
are never counted; the typed outcome knows it (`context_cells = 171,150` alongside
`asserted_cells = 171,150`), the evidence workbook's *Ledger* marks them explicitly, and
the *Notes* sheet explains the domain reason. The headline sheet does not. A reader of
the Summary alone concludes City/HG/Distance match perfectly across 57,050 rows — and
the evidence images themselves show a Distance difference (`000.562` vs `000.274` at
route 101 @ MEN R101.895). Scope is columns that are context in their entirety; Highway
Log's per-cell ditto context (14,872 cells in the PDF edition) produces no misleading
zero. The Clean Road workbook partially mitigates this with an explicit per-column
counted/context table elsewhere; Highway Sequence has none.

### PCOA-CL-012 — P3 — An empty second side is discovered only after the first side is fully parsed

Three witnesses: `intersection_detail_pdf` cross-environment ran **429.4 s**,
`intersection_detail_pdf` baseline ran **438.6 s**, and `highway_detail_pdf` Everything
ENV ran **1,229.7 s (20.5 minutes)** — each parsing 217–252 statewide prints before
reporting that the *other* side has no export. By contrast a missing FIRST side errors
in 0.0 s. On a statewide PDF family the user waits up to twenty minutes for an answer
the app could give immediately.

### PCOA-CL-013 — P2 — The Highway Log PDF and Excel editions disagree on the row universe, and it localizes to two routes

Cross-environment over the same two days: Excel edition 52,821 / 51,884 rows,
50,327 paired, 89,811 differing cells; PDF edition 52,807 / 51,886 rows, 50,712 paired,
88,238 differing cells. Diffing the two workbooks' own *Routes* sheets localizes the
entire difference to **4 routes** — `005` (15 rows), `074`, `101`, `140` (1 row each),
net −14 / +2, reconciling both totals exactly. The PDF-vs-Excel self check then
adjudicates it: differences exist in **2 of 252 routes** only, and route 005's 15-row
gap is one of them. See PCOA-CL-017 for what route 140 turned out to be.

### PCOA-CL-014 — P3 — Cross-environment comparisons of the PDF editions are evidence-eligible but the product offers no evidence for them

`ramp_summary`, `ramp_detail_pdf`, `intersection_detail_pdf`, `highway_log_pdf` and
`highway_sequence_pdf` compare PDF against PDF in cross-environment mode — the one
configuration the audit rule calls REQUIRED — yet `matrix_build.build_cell_comparison`
has no evidence parameter and no env-mode evidence exists anywhere. Recorded as a scope
gap, not a defect in a produced artifact; the five cells are marked `N/A`.

### PCOA-CL-015 — P1 — The Excel side of an evidence image is silently truncated at 26 characters, so the image can state a different value than the one compared

`scripts/visual_evidence.py:1270` draws each Excel-side cell as `text[:26]` with no
ellipsis (the header label is capped at 24 on line 1266). Every rendered example whose
compared value exceeds 26 characters therefore shows a **different string** inside the
red target box:

| set | example | drawn in the image | actual compared value |
|---|---|---|---|
| Everything HSL vs TSN | 080 @ SOL 002.438 | `BENICIA RD OC 23-88, BENIC` | `BENICIA RD OC 23-88, BENICIA RD OC 23 88` |
| Everything HSL vs TSN | 101 @ MEN R101.895 | `JCT 271-REYNOLDS SEP217, R` | `JCT 271-REYNOLDS SEP217, RTE 271` |
| By Day HSL vs TSN | 046 @ SLO 045.480 | `W JCT RTE 41/46/MCMIL CYN ` | `W JCT RTE 41/46/MCMIL CYN RD [SLO041.R.R 42.171]` |
| Everything HL vs TSN | 101 @ 011.603R | `RIVERSIDE DR OFF RAMP  , O` | `RIVERSIDE DR OFF RAMP , OC 53-1493` |
| By Day HL vs TSN | 005 @ 031.314 | `SAN FERNANDO EB 53-1110, S` | `SAN FERNANDO EB 53-1110, SAN FERNANDO BR UC NO. 53-1110` |

Census over every rendered example: **8 of 190** on the Excel-rendered panels. Verified
that it never affects a PDF-crop panel — the two audit-REQUIRED PDF/PDF cells render
full 39- and 55-character values untruncated. So the defect is confined to exactly the
configurations PCOA-CL-010 says should not be illustrated at all. The heading line above
the image does carry the full value, so the artifact is not internally inconsistent —
but the picture, whose purpose is to show the value in context, endorses a truncated
string, and it bites hardest on Description, the field most often compared.

### PCOA-CL-016 — P1 — A blank TSN Description boxes the WRONG RECORD on the Highway Log district print

In `highway_log_pdf` vs TSN — one of the two configurations the audit rule REQUIRES
evidence for — `Description_1_stacked.png` (route 140 @ R029.757, TSMIS
'BEGIN R REALIGNMENT' vs TSN blank) draws the gray record box correctly around
`R029.757 0.198 029.737 …` on page 137 of `D10 Highway Log TSN.pdf`, but draws the RED
"compared cell" box one line LOWER, across `0.145 029.935 R 55 M U C H 01 B 04` — cells
belonging to the NEXT record (R029.955). On that print a Description sits on a
continuation line below its data line; when the Description is blank there is no
continuation line and the box lands on the following record.

Not systemic, and the boundary is precise: `Description_2` (both sides populated) is
boxed perfectly on both sides; `NA_N_A_1` (TSN blank but an INLINE column) boxes a
correct small empty rectangle on the right row; the Highway Sequence print, whose
descriptions are on the same line, boxes blanks cleanly on both sides. A separate,
milder symptom is a ~1-character left overshoot on some targets (TSN `EQUATES TO` FT
blanks, one Intersection Detail `CS Eff-Date`), while others — e.g. Highway Log
`Med Wid` — are tight and correct.

### PCOA-CL-017 — P1 (source-side) — The 2026-07-23 Highway Log **Excel** export for route 140 is missing whole columns of data that its own print carries

The PDF-vs-Excel self check reports differences in only 2 of 252 routes, and for route
140 every one of the 213 differing rows differs on `R/U`, `TER`, `H/G`, `A/C` in the form
`R ≠ (blank)`, `F ≠ (blank)`, `U ≠ (blank)`, `C ≠ (blank)`. Verified at the raw source:

```
output\2026-07-23 ssor-prod\highway_log\highway_log_route_140.xlsx
    R/U -> '' ×213 | TER -> '' ×213 | H/G -> '' ×213 | A/C -> '' ×213
    (City, N/A and the LB* columns are blank too; only Location/MI/Cnty Odom/SPD carry data)
control highway_log_route_138.xlsx
    R/U -> R×193, U×57, B×14 | TER -> F×117, M×105, R×42
    H/G -> D×142, U×102, R×11 | A/C -> C×223, F×23, E×18
```

This is a genuine site/export defect, not a product defect — but it means every Highway
Log **Excel**-sourced comparison silently compares blanks for route 140, and it is the
strongest single argument in this audit for the PDF-vs-Excel self check's value. It is
recorded at P1 because the owner needs to act on it with the vendor.

## Validated-clean observations

### VC-1 — Ramp Summary cross-environment discrepancies are true, cell for cell

126 paired routes, 0 one-sided, 4,032 asserted cells, 67 differing in 15 rows. Route 001
is reported `Divided 270 ≠ 228`, `Undivided 1 ≠ 0`, `Others 0 ≠ 43`, `Diffs = 3`,
`Total Ramps 272` both sides. Reading the two raw PDFs directly with pdfplumber (not the
app's parser): new → `0 R`, `270 D`, `1 U`, `0 X`, `1 L`, `0 Others`, total 272; prior →
`0 R`, `228 D`, `0 U`, `0 X`, `1 L`, `43 Others`, total 272. Exact agreement, including
that the total is unchanged and the change is a reclassification. The Summary's per-field
breakdown sums to exactly 67.

### VC-2 — Highway Sequence one-sided rows are true, and the occurrence number is an assignment artifact

The prior-only row `001 / MON / R081.505  #4  L | H | 000.000 | BEGIN LT INDEP ALIGN` was
traced to the raw exports: at County `MON`, prefix `R`, PM `081.505` the prior file has
**4** rows and the new file **3**, and the row absent from the new file is exactly
`MON | | R | 081.505 | | L | H | 000.000 | BEGIN LT INDEP ALIGN`. Occurrence 4 comes from
the most-alike duplicate assignment (the workbook's own note 69), not from document order.

### VC-3 — Values / formulas twin agreement under real Excel recalculation

| comparison | cells compared | real value differences | Excel errors | recalculated headline |
|---|---:|---:|---:|---|
| Ramp Summary env | 23,409 | 0 | 0 | 67 differing / 0 one-sided |
| Intersection Summary env | 77,914 | 0 | 0 | 16 differing / 0 one-sided |
| Ramp Summary vs TSN | 1,098 | 0 | 0 | 23 differing / 2 one-sided |
| Highway Sequence env | 4,535,641 | 0 | 0 | 1,931 differing / 252 one-sided |
| Highway Log env | 11,118,720 | 0 | 0 | matches the typed outcome |
| **total** | **15,756,782** | **0** | **0** | |

Every recalculated headline equals the typed `ComparisonOutcome` in the values twin's
sidecar, and all SELF-CHECK rows recalculate to `OK`. The only differences anywhere are
the uncached-formula class of PCOA-CL-008 (318,168 HYPERLINK navigation cells in the
Highway Log pair alone).

### VC-4 — Intersection Summary cross-environment: complete statewide independent recount, zero discrepancy

A reader written for this audit (no application module) parsed all 434 raw per-route
exports: 217 routes each side, 217 paired, 0 one-sided, **7** routes with at least one
differing value, **16** differing values — identical to the typed outcome. Every triple
matches the Comparison sheet: `001 D 737/639, U 556/179`; `075 D 28/29, L 6/5`;
`101 D 231/154, L 35/0, R 35/6, U 91/36`; `145 L 1/0, R 1/2`; `151 L 3/1, R 5/7`;
`282 L 10/9, R 10/11`; `395 L 5/7, R 7/5`. Witness `<root>\witness\recount_is_env.json`.

### VC-5 — The vs-TSN "Summary by Category" sheet discloses rather than hides its one-sided classes

`ssor-prod_ramp_summary_tsn.xlsx` reports 29 TSMIS rows, 31 TSN rows, 2 TSN-only rows
(`Ramp Type: P - Dummy Paired` 122, `V - Dummy, Volume only` 81) and states in prose that
these are TSN bookkeeping classes TSMIS does not tabulate, together with
"TSMIS 'Ramp Types': 15,191 of 15,213 tabulated (22 not …)" and "TSMIS route universe
verified against the producer census: 126 routes (001–980)". The one-sided rows are
counted in the typed outcome, not silently dropped.

### VC-6 — Highway Sequence cross-environment: complete statewide recount confirms the duplicate-identity contract

My own reader over all 504 per-route exports, keyed on route + county + PM prefix + PM:

| duplicate pairing inside a key group | paired | new-only | prior-only | differing rows | differing cells |
|---|---:|---:|---:|---:|---:|
| naive positional (mine) | 60,248 | 6 | 246 | 2,089 | 2,475 |
| minimum-difference assignment (mine) | 60,248 | 6 | 246 | **1,919** | 1,929 |
| the app | 60,248 | 6 | 246 | **1,919** | 1,931 |

Row universe and pairing EXACT; the differing-row count matches exactly once duplicates
are paired most-alike, which is the app's documented contract — my naive pairing is what
is wrong. The residual 2 cells (0.10 %) are attributable to my greedy fallback on 5
oversized groups and my arbitrary tie-break versus the approved lexicographic one.

### VC-7 — Highway Log cross-environment: route-001 recount reconciles, and the corrected Legend is load-bearing

Raw-only recount of route 001: paired 1,927 / A-only 314 / B-only 22 → union 2,263;
1,488 rows with ≥1 difference; 13,036 differing cells. The app's *Routes* sheet says
compared 2,263, matched 1,927, with differences 1,488, differing cells 12,999 — pairing
arithmetic exact, 37 cells (0.28 %) absorbed by documented normalizations. Per column my
naive counter merged the vendor export's **two identically-named `RB SH` columns** into
one bucket (1,941); the app splits them correctly by position as
`RB IN-SH Treated [RB SH]` 738 + `RB OT-SH Treated [RB SH]` 1,204. Sampled row `R000.283`
verified directly: `MI 000.092/000.091`, `LB IN 00/02`, `LB SH 00/02`, and no other field
on that row differs.

### VC-8 — The classic Direct vs-TSN path carries the TSN print identity correctly

The same library workbooks, compared through the classic Compare tab minutes after the
matrix runs, print the real identity line for all four comparators that expose one, and
every provenance sidecar records the real `tsn_library\<report>\consolidated\…` path.
This is the control that isolates PCOA-CL-002/003 to the capture step.

### VC-9 — vs-TSN TSN-side values match the raw statewide prints exactly

Ramp Summary: every category read from `Ramp Summary Statewide_TSN.pdf` matches the
workbook's TSN column (`148 R`, `14991 D`, `106 U`, `0 X`, `165 L`, `0 Others`, `31 A`,
`173 B`, `676 C`, `6809 D`, `335 E`, `2251 F`, `615 G`, `1160 H`, …).
Intersection Summary: `166 R-RIGHT`, `152 L-LEFT`, `0 X`, `10186 U`, `6122 D`,
`346 RURAL-I`, `8270 RURAL-O`, `5500 URBAN-I`, `2510 URBAN-O`, `0 +INVALID` — all match
`Intersection Summary Statewide_TSN.pdf`. The 8 TSMIS-only categories are newer TASAS
classes the 2025-09 print does not carry (ROUNDABOUT, MIDBLOCK PED CROSSING, PEDESTRIAN
HYBRID BEACON, FLASH BEACON, …) — correct one-sided handling. TSMIS's
`+ - INVALID DATA` = 2,620 vs TSN 0 is surfaced, not hidden.

### VC-10 — Intersection Detail vs TSN: the largest difference column is true and reveals a live vendor pattern

`ML Eff-Date` is the largest column (1,969 cells). Three sampled rows checked on both raw
sides: `001/ORA/007.411` TSMIS `64-01-01` (equal to its own `Date of Record`) vs TSN
`1998-08-28`; `008.501` `64-01-01` vs `1973-06-30`; `008.781` `64-01-01` vs `1972-12-31`
— the workbook shows exactly `1964-01-01 ≠ 1998-08-28` etc., with the two-digit-year
normalization applied correctly. Substantively the current TSMIS export is still filling
`ML Eff-Date` with `Date of Record`.

### VC-11 — Workflow parity is exact everywhere it could be measured

Cross-environment (classic == Baseline == Everything ENV): Ramp Summary
67 / 15 / 126 / 0 / 0; Intersection Summary 16 / 7 / 217 / 0 / 0; Highway Sequence
1,931 / 1,919 / 60,248 / 6 / 246; Highway Log 89,811 / 22,486 / 50,327 / 2,494 / 1,557;
Highway Log (PDF) 88,238 / 22,724 / 50,712; Highway Sequence (PDF)
1,904 / 1,895 / 60,247; Ramp Detail (PDF) 376 / 316 / 15,208.

vs-TSN (Direct == By Day == Everything) on all nine measurable families: ramp_summary
23 / 23 / 29 / 0 / 2 · highway_sequence 5,573 / 4,883 / 57,050 / 3,204 / 12,754 ·
highway_log 84,709 / 38,478 / 49,195 / 3,626 / 10,888 · intersection_summary
53 / 53 / 58 / 8 / 0 · intersection_detail 5,092 / 2,816 / 16,199 / 260 / 427 ·
highway_log_pdf 84,202 / 38,931 / 49,829 / 2,978 / 10,254 · intersection_detail_pdf
5,092 / 2,816 / 16,199 / 260 / 427 · highway_sequence_pdf
4,974 / 4,892 / 57,483 / 2,771 / 12,321 · ramp_detail_pdf 619 / 468 / 15,204 / 9 / 206.

Self checks (Direct == PDF-vs-Excel matrix == Everything SELF): highway_log
3,090 / 1,363 / 52,140 / 667 / 681; highway_sequence 3,714 / 1,395 / 60,254 / 0 / 0;
intersection_detail 0 / 0 / 16,459 / 0 / 0.

The Everything and By Day Highway Sequence evidence sets also carry the **same ledger
digest** `401bc6d86fbd4a83`, so the exhaustive ledger is deterministic across workflows
even though the illustrated sample differs (different seeds).

### VC-12 — Intersection Detail cross-environment: the difference distribution proves the header canonicalization

16,459 rows both sides, 0 one-sided, 16,328 differing rows — concentrated in FOUR of 35
columns with the other 31 at exactly **0**: `Int St Eff-Date` 16,307, `H/G` 683, `PS` 314,
`Location` 259. A position misalignment between the legacy and current site editions
would scatter differences across all 35 columns. The four names also match, one for one,
what `compare_env._id_canonical_header` documents as the genuine changes. Censusing the
column: the pre-July export emitted `Date of Record` in `Int St Eff-Date` (7-09 ARS:
`64-01-01` ×2,307 …), the 2026-07-23 export carries real dates whose distribution matches
TSN's (`23-01-01`, `21-01-01`, `22-01-01`, …), and the vs-TSN comparison consequently
finds only **104** `Int St Eff-Date` differences. A genuine site-side correction, reported
truthfully. *(An early two-row sample led me to describe this as a reset to a constant
`22-01-01`; the full census corrects that, and the correction is recorded rather than
quietly dropped.)*

### VC-13 — The PDF-sourced editions reproduce their Excel siblings to within tiny, localized margins

Intersection Detail cross-environment: 17,563 vs 17,562 differing cells of 559,606
asserted — **one cell**, identical row universe. Intersection Detail vs TSN: byte-identical
(5,092 / 2,816 / 16,199 / 260 / 427). Highway Sequence cross-environment: 1 route,
1 row, 27 cells of 481,976. Highway Log cross-environment: 4 routes, 15+3 rows — and the
self check shows the 15 belong to a real Excel-side data loss (PCOA-CL-017). Against TSN
the PDF editions pair *better* than the Excel exports (Highway Log +634 rows, Highway
Sequence +433), which is precisely the premise the PDF consolidators exist for.

### VC-14 — Presentation contracts hold

Across every inspected workbook: the `__CMP_E1_STATE_V1_*` mask columns and the
`__CMP_E2_BUILD_FRESH_*` columns are hidden, the `__CMP_E2_SNAPSHOT_A/B` sheets are
`veryHidden`, the autofilter range stops before the mask columns, data columns carry
explicit widths (13.0) with a 45.75-point wrapped header row (no clipping), and the
`Key (helper)` column is deliberately visible and documented in the Summary notes. For
route 001 of the Ramp Summary comparison the hidden mask reads `EDDEED…` against visible
cells `0`, `270 ≠ 228`, `1 ≠ 0`, `0`, `1`, `0 ≠ 43` — exact agreement between typed state
and rendered content. The recalculated *Spot Check* sheet reports `Row integrity: OK` and
`Agree? OK` on every field, with its independently recomputed verdicts matching both the
Comparison sheet and my raw-PDF reading. *(An early probe appeared to show clipped
headers; that was an artifact of reading `column_dimensions.items()` — resolved per
column there is no clipping. Recorded so it is not re-raised.)*

### VC-15 — Per-row source-file provenance is exact

In the Highway Log cross-environment workbook the *Source Files* sheet maps side-A rows
1–2,241 to `highway_log_route_001.xlsx` and row 2,242 onward to
`highway_log_route_002.xlsx`; 2,241 is exactly the raw row count I counted independently
for route 001, and the source sheet's own Route column agrees at the boundary.

### VC-16 — No false-positive class from punctuation, case or whitespace

Of the 99 `Description` difference cells on the Highway Sequence cross-environment
Comparison sheet, **zero** are whitespace-only or `_x000D_`-escape-only. (The `_x000D_`
vs `_x000d_` differences visible while diffing twins are Excel re-casing openpyxl's hex
escape on save — an artifact of my comparison, not of the app.)

### VC-17 — A suspected normalizer defect was tested and refuted

The 10 TSMIS-only Highway Sequence routes (`005S`, `008U`, `010S`, `014U`, `015S`,
`058U`, `101U`, `178S`, `210U`, `880S`) looked like suffixed routes the TSN normalizer
might be folding into their base. Checked at the source: the TSN Highway Sequence print's
route group header is `DIST 11 RTE 005 DIR S-N` — a three-digit route plus a DIRECTION
token, and the print carries no suffixed route at all. The one-sided routes are a genuine
source asymmetry. (My first regex hit, `015 S`, was the description
`000.015 S. SLIDE CANYON VIADUCT`.)

### VC-18 — The evidence Ledger is exhaustive and correctly separates context

Each evidence workbook's *Ledger* sheet reports, per column, counted differences, those
with a unique row, those inside repeated-key groups, **context cells**, identical cells,
one-sided cells, examples rendered and why-no-example, plus a totals row and a ledger
digest bound into the manifest. For Intersection Detail all 25 differing columns received
examples and "Why no example" is empty on every row. City/HG/Distance are correctly shown
as 57,050 context cells each on the Highway Sequence set — the information PCOA-CL-011
says is missing from the comparison workbook's own Summary.

### VC-19 — Clean Road Highway reproduces its blessed canary exactly

52,647 paired / 5,081 ArcGIS-only / 7,436 TSN-only / **291,292 differing cells**,
matching the repo's blessed `CRH-SW-E2` canary after a forced re-normalization of the
clean_highway library on this machine. Its *Notes* sheet documents the key, the
normalizations, which families are counted, the city-name→TASAS-code derivation, the
context columns and a full per-column provenance table naming each THY column's ArcGIS
layer and marking it COUNTED or context.

## Output manifest

`<root>\witness\MANIFEST.json` — path, size and sha256 for every retained artifact
(2,328 files, 9,253,680,327 bytes).

| Artifact or run group | Path | Files / bytes | Purpose |
|---|---|---:|---|
| Claude generated comparisons | `<root>\generated-comparisons\` | 148 / 3,298,876,816 | classic Compare-tab env / vs-TSN / self outputs and the ArcGIS comparison, both twins + sidecars |
| Everything matrix comparisons | `<root>\everything-dest\comparisons\` | 1,236 / 2,926,182,980 | env (`ssor-prod\`) and tsn/self (`tsn\`) trees, evidence sets, result caches |
| Production by-day trees | `output\comparisons\{tsn-by-day, baseline-by-day, pdf-vs-excel-by-day}\` | 872 / 2,675,399,574 | By Day, Baseline and PDF-vs-Excel matrix outputs in the app's own locations |
| Witnesses | `<root>\witness\` | 20 / 454,192 | inventories, header census, TSN rebuild record, independent recounts, twin comparisons, temp-capture listing, export-coverage table, run records |
| Inspection tooling + recalculated copies | `<root>\inspection\` | 52 / 352,766,765 | every script written for this audit, the verdict data, and the Excel-recalculated data-only copies |

Note for the user: this round copied the frozen archive and the retained batch into
`output\2026-07-23 ssor-prod`, `output\2026-07-09 ssor-prod` and
`output\2026-07-09 ars-prod` (git-ignored) because the By Day / Baseline / PDF-vs-Excel
matrices read run folders from `OUTPUT_ROOT`. They can be deleted freely; the raw archive
and the ground-truth batch were never written to.

## Completion gate

- [x] All TSN files were freshly normalized through the same whole-library path
  available to an end user.
- [x] All 88 deliverable decisions are closed and their arithmetic reconciles.
- [x] Values and formulas were judged separately.
- [x] Formula twins were recalculated with installed Excel and compared with their
  data-only values twins (15,756,782 cells, 0 real differences, 0 Excel errors).
- [x] Deliverable sheets were inspected before evidence.
- [x] Every claimed discrepancy class was challenged against raw source.
- [x] PDF and Excel sibling discrepancy-count differences were explained by actual
  export differences, or recorded as findings.
- [x] All 25 Everything evidence cells are closed and reconcile.
- [x] Every eligible evidence image was personally inspected — value fidelity verified
  programmatically for 100 % of rendered examples, with 19 images inspected at full
  resolution covering both layouts, all four evidencing families, blank and populated
  targets, and both audit-REQUIRED PDF/PDF cells.
- [x] Prohibited mixed-format evidence was checked for leakage.
- [x] Highway Detail availability was judged from the current review-ready bundle, not
  old historical files.
- [x] Generated comparisons and inspection records are retained and manifested.
- [x] Claude findings and validated-clean observations are complete.
- [x] Independence declaration is signed.

## Handoff summary

96 comparison cells were generated through the product's real dispatch paths and every
one of the 88 deliverable decisions and 25 evidence cells is terminal.

**The comparison engine's truth is strong.** Whole-family independent recounts reproduce
it exactly (Intersection Summary 217/7/16 to the cell; Highway Sequence's row universe,
one-sided counts and 1,919 differing rows exactly once duplicates are paired the app's
documented way), workflow parity is exact across every path that could be measured, and
15.7 M recalculated formula cells show zero disagreement with their values twins.

**The defects are in what the deliverables SAY, not what they count.** Three P1s dominate:
the site's changed Ramp Detail Excel layout is refused end to end while the consolidator
still reports success (PCOA-CL-001); the private TSN capture strips the source claims so
every matrix-path vs-TSN workbook loses its TSN vintage and prints an instruction that
cannot help (PCOA-CL-002); and evidence images truncate the Excel-side value at 26
characters (PCOA-CL-015) while one blank-value case boxes the wrong record entirely
(PCOA-CL-016). A fourth P1 is source-side and needs the vendor: the Highway Log Excel
export for route 140 is missing whole columns that its own print carries (PCOA-CL-017) —
found only because the PDF-vs-Excel self check exists.

Prompt 02 (cross-check and final findings) is now unblocked.
