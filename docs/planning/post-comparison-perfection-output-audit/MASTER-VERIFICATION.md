# Post-Comparison-Perfection Output Verification

> Workflow artifact: **Stage 1A — Codex independent audit**
>
> Status: **COMPLETE AND FROZEN**
>
> Authority: Codex-round decisions only. This is not yet a joint approval or
> the implementation backlog.
>
> New-chat entry point: [START-HERE.md](START-HERE.md). The next action is
> [Prompt 01 — Claude independent audit](prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md).
> Claude must not read this file until its independent round is frozen.

No implementation is authorized in this phase.

This file is the shared, user-visible control sheet for the deliverable audit
requested on 2026-07-23. A cell began `UNVERIFIED` and changed only after an
adversarial source check, workbook check, discrepancy check, and (where
applicable) evidence-image check. A successful process exit is not approval.

## Audit contract

- Review the generated comparison workbooks as final user deliverables, not as
  code-test artifacts.
- Exercise the public comparator adapters and the production By Day, Baseline,
  and Everything matrix cores that the GUI dispatches.
- Verify both values-only and live-formula twins.
- Recalculate formula copies with installed Excel and compare their data-only
  results against the values twins.
- Independently recount source data without reusing the application parser where
  practical, then challenge every discrepancy class for false positives.
- Require evidence only for source-PDF-vs-source-PDF comparisons. Evidence from
  an Excel-vs-PDF or PDF-vs-Excel comparison is a defect, even if a sibling PDF
  happens to exist.
- Do not approve Highway Detail or Highway Detail (PDF): the current dev site
  greys them out and the new bundle cannot contain review-ready exports.
- Record findings for Claude in `CODEX-FINDINGS.md`. Claude records independent
  findings in `CLAUDE-FINDINGS.md`. Conflicts are resolved in
  `FINAL-RECONCILIATION.md`.

## Status legend

| Status | Meaning |
|---|---|
| `UNVERIFIED` | Not personally approved or denied yet |
| `APPROVED` | Deliverable and claimed discrepancies independently checked |
| `DENIED` | Deliverable is missing, wrong, misleading, or not user-ready |
| `BLOCKED` | Required review-ready source is unavailable |
| `N/A` | The report/workflow combination is intentionally unsupported |

Cells written as `V / F` show **values / formulas** status.

## Frozen inputs and provenance

The 2026-07-23 archive came from the **development site of SSOR-prod**. The
permanent/main site is expected in theory to emit equivalent report content, but
that equivalence is explicitly outside this audit and remains a future test.

| Input | Frozen location or identity | Audit result |
|---|---|---|
| New dev-site SSOR-prod archive | `C:\Users\Yunus\Downloads\TSMIS\_inbox\2026-07-23 ssor-prod.zip` | SHA-256 `217F172F7EF7DB527A1EF30E2BFD12D1D6B810BCA55C0D38B7733CB4BE74266F`; 2,380 readable files; no duplicate member paths |
| New extracted run | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-perfection-output-audit-2026-07-23\2026-07-23 ssor-prod` | Frozen audit copy |
| Prior SSOR-prod batch | `C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9` | Read-only junction in audit tree |
| Prior ARS-prod batch | Existing 2026-07-09 ground truth | Read-only junction in audit tree; used for prior Intersection Detail family |
| Canonical TSN library | Repository `tsn_library` | Rebuilt through `tsn_library.build_consolidated(force=True)` after importing the missing Ramp Summary and Intersection Summary source PDFs. Every supported dataset completed/current. Clean Road Intersection and Clean Road Ramp have raw files staged but no normalizer or comparison integration, so normalize-all explicitly reports them unsupported rather than producing a workbook. |
| Generated deliverables | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-perfection-output-audit-2026-07-23\generated-comparisons` | Retained for human/AI cross-check |
| Durable audit ledgers | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-perfection-output-audit-2026-07-23\run-ledgers` | JSON per run |
| Independent witnesses | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-perfection-output-audit-2026-07-23\source-audit` | JSON source recounts and inventory |

The new archive covers every currently reviewable exported family in both
formats where a sibling format exists:

| Family | New Excel | New PDF | Prior comparison source | Coverage |
|---|---:|---:|---|---|
| Ramp Summary | 126 export-only sibling | 126 integrated reports | SSOR-prod 7.9 | Complete; independent PDF/Excel parity passed |
| Ramp Detail | 126 | 126 | SSOR-prod 7.9 | Complete |
| Highway Sequence Listing | 252 | 252 | SSOR-prod 7.9 | Complete |
| Highway Log | 252 | 252 | SSOR-prod 7.9 | Complete |
| Intersection Summary | 217 integrated reports | 217 export-only siblings | SSOR-prod 7.9 | Complete; all 14,322 PDF/Excel route/category/total values identical |
| Intersection Detail | 217 | 217 | ARS-prod 7.9 | Complete |
| Highway Detail | 0 | 0 | Old files exist but are not review-ready | `BLOCKED` as requested |

Every sibling pair and every selected prior pair has an exact route-token set.
The only absent reports are the deliberately unavailable Highway Detail pair
and Highway Summary, which is not a comparison row.

One workflow-specific source gap remains: the retained Intersection Detail
baseline is ARS-prod, not SSOR-prod. Direct classic and Everything ENV can and
do compare the fresh SSOR output with that genuine prior ARS source. Baseline's
same-environment day model cannot select it, and there is no prior SSOR
Intersection Detail Excel/PDF pair in the supplied ground truth. Those two
Baseline cells are therefore `BLOCKED`; this is not a missing file in the new
bundle.

## Execution and approval gates

1. Freeze and inventory inputs; verify route and sibling coverage.
2. Rebuild the entire TSN library through the same normalize-all entry point a
   user invokes.
3. Consolidate new Excel and PDF exports through public consolidators.
4. Generate classic cross-version, direct-vs-TSN, By Day, Baseline, Everything
   environment, Everything TSN, and PDF-vs-Excel self comparisons.
5. Retain values and formula twins; validate trusted/current sidecars and atomic
   generation membership.
6. Recalculate formula copies in installed Excel; compare visible cached values,
   formulas, error cells, sheets, rows, keys, states, and summary totals.
7. Independently recount the source, stratify discrepancies by field/state/value
   pair, and trace deterministic adversarial samples back to raw exports.
8. Compare each Excel-vs-TSN result with its PDF-vs-TSN sibling. Any count
   difference must be proved by a real export-content difference.
9. Audit evidence manifests and every retained crop for availability, correct
   source pages, correct keys/fields, readable bounds, and modality eligibility.
10. Perform Codex/Claude cross-check and issue final approvals/denials.

The authoritative production registry was also frozen independently in
`source-audit/production-matrix-mode-inventory.json`: 12 report rows and 30
Everything cells (environment, TSN, and exposed self modes). The matrices below
account for all 30. Twenty-five have reviewable source inputs; the five Highway
Detail/Highway Detail PDF cells remain source-blocked because that report is
currently unavailable on the dev site.

## Matrix A — classic folder comparison (new dev-site batch vs 7.9)

| Report row | Values / formulas | Source truth | Discrepancies | Workbook QA | Final |
|---|---|---|---|---|---|
| Ramp Summary | DENIED / DENIED | Independent statewide recount passed | Values all-field screen passed; 67 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — both twins materially clip 8 visible Summary labels/instructions | DENIED |
| Ramp Detail | DENIED / DENIED | APPROVED consolidation truth — complete typed-row parity passed for both the new 15,213-row export and retained 15,216-row 7.9 batch; new 11-column export header confirmed legitimate | Comparator produces no deliverable | N/A | DENIED |
| Highway Sequence Listing | DENIED / DENIED | APPROVED consolidation truth — complete typed-row parity passed for all 60,254 new rows and 60,494 retained 7.9 rows | Values all-field screen passed; 1,931 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — material Summary and Spot Check instructions/labels are clipped in both twins | DENIED |
| Highway Log | DENIED / DENIED | APPROVED consolidation truth — complete typed-row parity passed for all 52,821 new rows and 51,884 retained 7.9 rows | Values all-field screen passed; 89,811 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — material Summary and Spot Check instructions/labels are clipped in both twins | DENIED |
| Intersection Summary | DENIED / DENIED | Independent new-batch recount passed | Values all-field screen passed; 16 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — both twins materially clip 13 visible Summary labels/instructions | DENIED |
| Intersection Detail | DENIED / DENIED | APPROVED consolidation truth — complete typed-row parity passed for all 16,459 fresh SSOR-dev rows and all 16,459 retained ARS 7.9 rows | Values all-field screen passed; 17,563 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — material Summary and Spot Check instructions/labels are clipped in both twins | DENIED |
| Highway Log (PDF) | DENIED / DENIED | APPROVED source truth — the reconstructed retained 7.9 PDF has 51,884 paired rows, two genuine PDF-only rows, and 619 genuine cells across 618 rows versus its original Excel sibling. All 23 width value-pair classes, all 11 signal-date cells, and both one-sided keys bind to the reconstructed row, original XLSX row, and original PDF text line. Fresh PDF/Excel source truth was independently approved earlier. | Values all-field screen passed; 88,238 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — material Summary and Spot Check instructions/labels are clipped in both twins | DENIED |
| Intersection Detail (PDF) | DENIED / DENIED | APPROVED source truth — fresh and retained PDF/Excel siblings each contain 16,459 paired rows with no one-sided rows. The retained sources repeat the fresh pull's 278 whitespace-only Description representations, plus exactly one genuine prior raw-source cell: route 108 / `005.870` has H/G `U` in XLSX and `D` in PDF, exactly explaining the classic Excel/PDF discrepancy-count delta of one. | Values all-field screen passed; 17,562 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — material Summary and Spot Check instructions/labels are clipped in both twins | DENIED |
| Highway Detail | BLOCKED / BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| Highway Detail (PDF) | BLOCKED / BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| Highway Sequence Listing (PDF) | DENIED / DENIED | APPROVED source truth — fresh PDF/Excel siblings are identical across all 60,254 rows after 1,119 equation relations are canonicalized; retained 7.9 siblings reconcile across 60,493 shared rows after 1,129 relations, with the only four Description cells and one Excel-only row each verified in the original XLSX/PDF exports | Values all-field screen passed; 1,904 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — material Summary and Spot Check instructions/labels are clipped in both twins | DENIED |
| Ramp Detail (PDF) | DENIED / DENIED | APPROVED source truth — the reconstructed retained 7.9 PDF consolidation matches its original Excel sibling exactly across all 15,216 paired rows, 121,728 asserted cells, and 60,864 context cells; the fresh 15,213-row PDF source was already independently reconciled with its fresh Excel sibling after symmetric null-token projection | Values all-field screen passed; 376 claimed cells, zero semantic-equivalence candidates | DENIED visual gate — material Summary and Spot Check instructions/labels are clipped in both twins | DENIED |

## Matrix B — TSMIS vs TSN

Each workflow must agree on the same semantic comparison. `Direct` is the
public report comparator; `By Day` and `Everything` are production GUI cores.

| Report row | Direct V / F | By Day V / F | Everything V / F | Independent truth | Final |
|---|---|---|---|---|---|
| Ramp Summary | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Source PDF and all 31 categories recounted; numeric and formula gates pass. Direct and By Day twins materially clip 5 Summary cells and 29 Comparison category cells; By Day also falsely calls the fresh TSN library an older normalization. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material visible clipping. | DENIED |
| Ramp Detail | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Direct, production By Day, and final isolated Everything paths all reject the fresh public consolidation because the shared header contract is stale; none publishes values or formulas | DENIED |
| Highway Sequence Listing | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Published arithmetic passed. Full FT cross-tabs prove 677/690 Excel FT cells and 70/82 PDF FT cells are explicitly disclosed EQUATES TO representation differences; every one of the 13 remaining Excel FT cells was traced through the fresh raw XLSX, normalized TSN row, and original district TSN PDF and is source-real. The cross-format count delta is therefore explained by the raw PDF's two-line equation representation versus Excel's folded relation. Both formats publish the same 11 case/spacing/punctuation-only Description false positives, and their By Day workbooks also display the false fresh-TSN provenance warning. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material Summary/Spot Check clipping. | DENIED |
| Highway Log | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Published arithmetic binds, but 1,243 of 2,723 Description discrepancies are punctuation-only token-identical false positives (for example comma versus slash). The workbook overstates differing cells by exactly 1,243, and its By Day workbook also displays the false fresh-TSN provenance warning. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material Summary/Spot Check clipping. | DENIED |
| Intersection Summary | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | All 58 TSN categories and all 66 TSMIS categories independently recounted; numeric and formula gates pass. Direct and By Day twins materially clip 5 Summary cells and 66 Comparison category cells; By Day also falsely calls the fresh TSN library an older normalization. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material visible clipping. | DENIED |
| Intersection Detail | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Exact published-state recount passed: 16,199 paired, 260 TSMIS-only, 427 TSN-only, 2,816 differing rows, 5,092 cells, exactly matching the PDF sibling. All 16,626 TSN raw rows project to the rebuilt 38-column library with zero differences across 631,788 cells. Four-source tracing proved the literals, but one of four Description claims is semantically identical quote styling (`''F'' ST` vs `"F" ST`) and is a false positive. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material Summary/Spot Check clipping. | DENIED |
| Highway Log (PDF) | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Published arithmetic binds, but the same 1,243 punctuation-only Description false positives occur among 2,827 Description discrepancies. The fresh PDF and Excel siblings reproduce the identical false-positive set, and the By Day workbook also displays the false fresh-TSN provenance warning. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material Summary/Spot Check clipping. | DENIED |
| Intersection Detail (PDF) | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Exact recount matches Excel at 16,199 / 260 / 427 / 2,816 / 5,092; complete TSN raw-to-normalized parity passed for 631,788 cells; the same one quote-style-only Description false positive remains. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material Summary/Spot Check clipping. | DENIED |
| Highway Detail | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED | BLOCKED |
| Highway Detail (PDF) | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED | BLOCKED |
| Highway Sequence Listing (PDF) | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Published arithmetic passed; same semantic source as Excel after 1,119 equation relations are canonicalized, it contains the identical 11 formatting-only Description false positives, and the By Day workbook also displays the false fresh-TSN provenance warning. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material Summary/Spot Check clipping. | DENIED |
| Ramp Detail (PDF) | DENIED / DENIED | DENIED / DENIED | DENIED / DENIED | Published arithmetic independently passed and all 15,410 TSN normalized rows match raw field-for-field, but two Description claims differ only by comma/period spacing and are false positives. Final isolated Everything typed results match Direct and By Day, but both Everything twins are independently denied for material Summary/Spot Check clipping. | DENIED |

## Matrix C — Baseline and Everything environment paths

| Report row | Baseline V / F | Everything ENV V / F | Cross-workflow parity | Final |
|---|---|---|---|---|
| Ramp Summary | DENIED / DENIED | DENIED / DENIED | APPROVED — final isolated Everything ENV matches direct classic and Baseline typed numeric results. Baseline and Everything twins are independently visually denied for material clipping. | DENIED |
| Ramp Detail | DENIED / DENIED | DENIED / DENIED | APPROVED intentional all-error parity — classic, production Baseline, and final isolated Everything ENV all reject the stale Ramp Detail layout without publishing values/formulas workbooks. | DENIED |
| Highway Sequence Listing | DENIED / DENIED | DENIED / DENIED | APPROVED — final isolated Everything ENV matches direct classic and Baseline typed values/formulas results. Baseline and Everything twins are independently visually denied for material Summary/Spot Check clipping. | DENIED |
| Highway Log | DENIED / DENIED | DENIED / DENIED | APPROVED — final isolated Everything ENV matches direct classic and Baseline typed values/formulas results. Baseline and Everything twins are independently visually denied for material Summary/Spot Check clipping. | DENIED |
| Intersection Summary | DENIED / DENIED | DENIED / DENIED | APPROVED — final isolated Everything ENV matches direct classic and Baseline typed numeric results. Baseline and Everything twins are independently visually denied for material clipping. | DENIED |
| Intersection Detail | BLOCKED / BLOCKED | DENIED / DENIED | APPROVED documented source exception — direct classic and final isolated Everything ENV agree exactly; Baseline remains the expected rejection because its same-environment day model cannot select the supplied prior ARS source. Everything twins are visually denied. | DENIED |
| Highway Log (PDF) | DENIED / DENIED | DENIED / DENIED | APPROVED — final isolated Everything ENV matches direct classic and Baseline typed values/formulas results. Baseline and Everything twins are independently visually denied for material Summary/Spot Check clipping. | DENIED |
| Intersection Detail (PDF) | BLOCKED / BLOCKED | DENIED / DENIED | APPROVED documented source exception — direct classic and final isolated Everything ENV agree exactly; Baseline remains the expected rejection because its same-environment day model cannot select the supplied prior ARS PDF source. Everything twins are visually denied. | DENIED |
| Highway Detail | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED | BLOCKED |
| Highway Detail (PDF) | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED | BLOCKED |
| Highway Sequence Listing (PDF) | DENIED / DENIED | DENIED / DENIED | APPROVED — final isolated Everything ENV matches direct classic and Baseline typed values/formulas results. Baseline and Everything twins are independently visually denied for material Summary/Spot Check clipping. | DENIED |
| Ramp Detail (PDF) | DENIED / DENIED | DENIED / DENIED | APPROVED — final isolated Everything ENV matches direct classic and Baseline typed values/formulas results. Baseline and Everything twins are independently visually denied for material Summary/Spot Check clipping. | DENIED |

All seven delivered Baseline formula/value pairs also pass installed-Excel
recalculation and cached-value parity: 8,230,837 live formulas, 1,455,991
intentional values-twin formulas, and 32,819,899 compared cells, with zero
unexpected semantic mismatches or Excel/formula errors. The 628 raw
differences and seven Summary shape offsets are entirely the documented
formula/value flavor prose and help-row presentation.

## Matrix D — same-day PDF vs Excel self-consistency

Only four families have both an active PDF export and Excel export. Evidence is
**not allowed** for these PDF-vs-Excel comparisons.

The Everything Highway Log gate covers both exposed dispatch rows
(`highway_log`/`vs_pdf` and `highway_log_pdf`/`vs_excel`), even though they
reach the same semantic sibling comparator. Both must pass independently.

| Family | Direct self V / F | Everything SELF V / F | Raw sibling truth | Evidence eligibility | Final |
|---|---|---|---|---|---|
| Ramp Detail | DENIED / DENIED | DENIED / DENIED | APPROVED source truth — all 15,213 rows are semantically identical; current adapter projection would create 108 null-token false-positive cells after its header gate is fixed. Final isolated Everything records the expected stale-layout rejection and publishes no workbook. | PROHIBITED | DENIED |
| Highway Sequence Listing | DENIED / DENIED | DENIED / DENIED | APPROVED source truth — all 60,254 rows are semantically identical after exact equation-relation canonicalization; both direct and final isolated Everything typed results falsely report 1,395 rows / 3,714 cells. The Everything twins are also visually denied for material Summary/Spot Check clipping. | PROHIBITED | DENIED |
| Highway Log | DENIED / DENIED | DENIED / DENIED | APPROVED source truth — 52,140 paired, 667 PDF-only, 681 Excel-only, 1,363 differing rows / 3,090 cells. Independent recount passed; route 140 missing Excel fields, route 005 key shift, and route 005 matched-key value changes were verified in the raw PDF/XLSX. Both exposed Everything dispatch cells independently reproduce the same typed result; all four Everything twins are visually denied for material Summary/Spot Check clipping. | PROHIBITED | DENIED |
| Intersection Detail | DENIED / DENIED | DENIED / DENIED | APPROVED source truth — all 16,459 same-day rows and all 559,606 asserted cells match; zero one-sided rows and zero discrepancies. Final isolated Everything typed parity passes exactly, but both Everything twins are visually denied for material Summary/Spot Check clipping. | PROHIBITED | DENIED |
| Ramp Summary | N/A / N/A | N/A / N/A | Excel sibling is export-only; independent PDF/Excel count parity passed | N/A | N/A |
| Intersection Summary | N/A / N/A | N/A / N/A | PDF sibling is export-only; all 14,322 PDF/Excel route/category/total values independently identical | N/A | N/A |
| Highway Detail | BLOCKED / BLOCKED | BLOCKED / BLOCKED | BLOCKED | PROHIBITED | BLOCKED |

## Matrix E — evidence collection

`REQUIRED` means both semantic source sides are PDFs and the production workflow
exposes evidence. `PROHIBITED` means at least one semantic source side is Excel.

The exact final registry contains 25/25 arithmetic-bound cells: eight
`REQUIRED`, 14 `PROHIBITED`, and three expected no-deliverable rejections.
Mechanical artifact binding approves the two available required bundles,
denies six required availability gaps, approves five clean prohibited
absences, and denies nine prohibited leaks. The final human crop gate below
then closes Matrix E at 16 `DENIED`, six `APPROVED`, and three `N/A`.
Across the exact Everything runs, 1,064 PNGs and 182 complete contact sheets
were retained; 872 of those PNGs came from prohibited comparisons.

| Workflow / report class | Eligibility | Availability | Crop accuracy | Final |
|---|---|---|---|---|
| By Day vs TSN — Ramp Summary (PDF/PDF) | REQUIRED | NOT AVAILABLE — evidence requested, 0 files | N/A | DENIED evidence gate |
| By Day vs TSN — Highway Sequence PDF | REQUIRED — the normalized TSN library originates in district PDFs | AVAILABLE — all 12 requested pair/stacked PNGs retained with bound manifest/workbook | DENIED — all 12 inspected; six mislocalize the red target on special `EQUATES TO` rows | DENIED |
| By Day vs TSN — Highway Log PDF | REQUIRED — the normalized TSN library originates in district PDFs | AVAILABLE — 180 exact manifest-bound images and 128 PDF read-set files | DENIED — 178/180 are accurate; both route 395 / `T121.831` Description layouts caption a blank TSN value but draw the TSN target across the following `T121.945` row | DENIED |
| By Day vs TSN — Ramp Detail PDF | PROHIBITED — TSN semantic side is XLSX | DENIED — emitted 50 PNGs by opportunistically borrowing the sibling TSN PDF | APPROVED crop accuracy only — all 50 inspected across nine field contact sheets, all targets correct | DENIED |
| By Day vs TSN — Intersection Detail PDF | PROHIBITED — TSN semantic side is XLSX | DENIED — emitted 142 PNGs by borrowing the sibling statewide TSN PDF; manifest/hash binding itself passes | DENIED — 140/142 accurate; both route 046 / 50.904 `Control Type` layouts box `P` while claiming normalized TSN `S` | DENIED |
| Everything ENV — Ramp Summary | REQUIRED — PDF/PDF | DENIED — 67 differing cells but no manifest, evidence workbook, or PNG | N/A — unavailable | DENIED |
| Everything ENV — Ramp Detail | N/A — expected comparison rejection before evidence | N/A — stale-layout rejection; no comparison deliverable | N/A | N/A |
| Everything ENV — Intersection Summary | PROHIBITED — Excel/Excel | APPROVED absent — no manifest, workbook, or PNG | N/A | APPROVED evidence gate |
| Everything ENV — Intersection Detail | PROHIBITED — Excel/Excel | APPROVED absent — no manifest, workbook, or PNG | N/A | APPROVED evidence gate |
| Everything ENV — Intersection Detail PDF | REQUIRED — PDF/PDF | DENIED — 17,562 differing cells but no manifest, evidence workbook, or PNG | N/A — unavailable | DENIED |
| Everything ENV — Ramp Detail PDF | REQUIRED — PDF/PDF | DENIED — 376 differing cells plus 5/8 one-sided rows but no manifest, evidence workbook, or PNG | N/A — unavailable | DENIED |
| Everything ENV — Highway Sequence | PROHIBITED — Excel/Excel | APPROVED absent — no manifest, workbook, or PNG | N/A | APPROVED evidence gate |
| Everything ENV — Highway Log | PROHIBITED — Excel/Excel | APPROVED absent — no manifest, workbook, or PNG | N/A | APPROVED evidence gate |
| Everything ENV — Highway Log PDF | REQUIRED — PDF/PDF | DENIED — 88,238 differing cells plus 2,095/1,174 one-sided rows but no manifest, evidence workbook, or PNG | N/A — unavailable | DENIED |
| Everything ENV — Highway Sequence PDF | REQUIRED — PDF/PDF | DENIED — 1,904 differing cells plus 7/246 one-sided rows but no manifest, evidence workbook, or PNG | N/A — unavailable | DENIED |
| Everything TSN — Ramp Summary | REQUIRED — PDF/PDF | DENIED — positive discrepancies but no manifest, evidence workbook, or PNG | N/A — unavailable | DENIED |
| Everything TSN — Ramp Detail | N/A — expected comparison rejection before evidence | N/A — stale-layout rejection; no comparison deliverable | N/A | N/A |
| Everything TSN — Intersection Summary | PROHIBITED — Excel/normalized XLSX | APPROVED absent — no manifest, workbook, or PNG | N/A | APPROVED evidence gate |
| Everything TSN — Intersection Detail | PROHIBITED — Excel/normalized XLSX | DENIED — emitted manifest, evidence workbook, and 142 PNGs | DENIED — 140/142 accurate; two `Control Type` targets box printed `P` while claiming normalized `S` | DENIED |
| Everything TSN — Intersection Detail PDF | PROHIBITED — PDF/normalized XLSX | DENIED — borrowed a sibling TSN PDF and emitted 142 PNGs | DENIED — 140/142 accurate; the same two `Control Type` target failures | DENIED |
| Everything TSN — Ramp Detail PDF | PROHIBITED — PDF/normalized XLSX | DENIED — borrowed a sibling TSN PDF and emitted 50 PNGs | APPROVED crop accuracy only — 50/50 correct | DENIED |
| Everything TSN — Highway Sequence | PROHIBITED — Excel/normalized XLSX | DENIED — emitted 12 PNGs | DENIED — only 2/12 fully support their captions; eight wrong targets and two truncated TSMIS crops | DENIED |
| Everything TSN — Highway Log | PROHIBITED — Excel/normalized XLSX | DENIED — emitted 180 PNGs | DENIED — 174/180 accurate; two wrong-row targets and four truncated TSMIS descriptions | DENIED |
| Everything TSN — Highway Log PDF | REQUIRED — PDF/PDF-origin TSN | AVAILABLE — 180 exact manifest-bound pair/stacked PNGs | APPROVED — the fresh set differed from the retained By Day set at all 180 PNG hashes, so it was reviewed independently; 180/180 captions, routes, rows, field targets, and compared values are accurate and readable | APPROVED evidence gate |
| Everything TSN — Highway Sequence PDF | REQUIRED — PDF/PDF-origin TSN | AVAILABLE — exact manifest, evidence workbook, 12 pair/stacked PNGs, and 29-file PDF-only read set all bind | DENIED — all 12 hashes differ from the retained By Day set and were reviewed independently; 8/12 are accurate, while both layouts for FT examples 2 and 3 box the final `O` in printed `EQUATES TO` instead of the captioned blank TSN FT | DENIED |
| Everything SELF — Ramp Detail PDF | N/A — expected comparison rejection before evidence | N/A — stale-layout rejection; no comparison deliverable | N/A | N/A |
| Everything SELF — Highway Sequence PDF | PROHIBITED — PDF/Excel | DENIED — emitted manifest, evidence workbook, and 18 PNGs | APPROVED crop accuracy only — 18/18 correct | DENIED |
| Everything SELF — Intersection Detail PDF | PROHIBITED — PDF/Excel | DENIED — emitted a manifest despite a zero-difference result; zero workbook/PNGs | N/A — manifest-only leak | DENIED |
| Everything SELF — Highway Log | PROHIBITED — Excel/PDF | DENIED — emitted manifest, evidence workbook, and 164 PNGs | APPROVED crop accuracy only — 164/164 correct | DENIED |
| Everything SELF — Highway Log PDF | PROHIBITED — PDF/Excel | DENIED — emitted manifest, evidence workbook, and 164 PNGs | APPROVED crop accuracy only — separately reviewed 164/164 correct | DENIED |
| Baseline — Ramp Summary plus four explicit active PDF rows | NOT EXPOSED by the production Baseline core | N/A | N/A | N/A |
| Direct/classic comparators | Not an evidence-capable UI path | N/A | N/A | N/A |
| Excel vs TSN, including summary rows | PROHIBITED | DENIED — By Day emitted evidence for three Excel-vs-TSN comparisons: Highway Sequence (12 PNGs), Highway Log (180 PNGs), and Intersection Detail (138 PNGs) | DENIED — all 330 inspected; 12 misplace the asserted TSN target (8 Highway Sequence equation targets and 4 Highway Log blank-Description targets); all 138 Intersection Detail targets are accurate but ineligible | DENIED |
| Direct/current-prior PDF vs Excel self comparisons | PROHIBITED | APPROVED absent — all reviewed current and retained-source self outputs contain zero evidence artifacts | N/A | APPROVED evidence gate |
| Highway Detail PDF paths | BLOCKED | BLOCKED | BLOCKED | BLOCKED |

## Matrix F — Clean Road Files supplemental comparison

Only Clean Road Highway currently has a comparison contract. Clean Road
Intersection and Clean Road Ramp have raw TSN files staged, but normalize-all
has no dataset normalizer or comparison integration for either one. Their
explicit unsupported result is recorded as `N/A`; they were not silently
skipped.

| Dataset | Values | Formulas | Source truth | Final |
|---|---|---|---|---|
| Clean Road Highway vs TSN | DENIED | DENIED | TSN source truth APPROVED — all 60,083 raw rows × 74 columns survive normalization with zero cell changes. ArcGIS-build truth APPROVED as rule-faithful across 57,728 rows × 74 fields, but the raw source contains 102 live `LocError=NO ERROR` rows with one missing PM endpoint that the no-guess builder silently skips. Bounded, anchor-exact helper-token tracing proves 161 published false-positive cells plus four genuine differences whose ArcGIS side is materially misrepresented as blank; the values workbook's Summary and Notes disclose none of the condition. | DENIED — 161 skipped-source false positives, four wrong-sided difference displays, five formatting-only landmark false positives, and material Summary/Spot Check/key clipping |
| Clean Road Intersection | N/A | N/A | Intentional refusal/currently unsupported | N/A |
| Clean Road Ramp | N/A | N/A | Intentional refusal/currently unsupported | N/A |

## Completed intermediate witnesses

These are inputs to approval, not shortcuts around the remaining gates.

- New-bundle independent inventory: 2,380 readable files, 285,635,268 bytes,
  no duplicate paths, and one structural Excel signature per report folder.
- Every source XLSX contains zero formulas and zero Excel error cells.
- PDF inventory covers every PDF and records 10,585 total source pages.
- All supported TSN datasets rebuilt successfully and are complete/current.
  Clean Road Intersection and Clean Road Ramp were attempted by normalize-all
  but explicitly reported unsupported because no normalizer/integration exists.
- New consolidations completed with zero skipped or failed inputs.
- Every differing cell in all seven available direct detail deliverables was
  screened for case/spacing, punctuation, numeric, and render-null
  equivalence. All 2,512 candidates are the Description cells already denied
  under PCOA-CX-008/010; no other asserted field produced such a candidate.
- The same screen covered all three delivered direct self workbooks and found
  zero formatting-equivalence candidates or malformed displays. Highway
  Sequence remains denied for its separately proven equation projection.
- Ramp Summary: 3,780 source category/total cells checked; zero consolidation or
  deliverable-side count mismatches. Independent TSN PDF parse reproduced 29
  paired, 2 TSN-only, 23 differing, and 6 identical categories exactly.
- Intersection Summary: 14,105 source category cells plus totals checked; zero
  consolidation or deliverable-side count mismatches. Independent TSN PDF parse
  reproduced 58 paired, 8 TSMIS-only, 53 differing, and 5 identical categories
  exactly. The raw TSN PDF's printed code-F prose defect is preserved as a
  declared semantic correction, not silently counted as a discrepancy.
- Intersection Summary export sibling: all 217 PDFs were parsed independently;
  all 14,322 same-pull PDF/Excel category and total values are identical, and
  their statewide sums equal the generated Excel-vs-TSN deliverable.
- Classic cross-version values/formulas agree on their published counts for all
  completed rows. Ramp Detail fails in both modes before publication.
- An app-independent raw-XLSX audit compared complete typed row multisets from
  every route file with the retained consolidation. All eight exercised
  datasets passed: the four fresh dev-site Ramp Detail, Highway Sequence,
  Highway Log, and Intersection Detail consolidations; the retained SSOR 7.9
  Ramp Detail, Highway Sequence, and Highway Log consolidations; and a newly
  retained audit-only ARS 7.9 Intersection Detail consolidation. Across
  288,800 raw rows there are zero missing and zero extra consolidated rows.
  Durable witnesses are
  `source-audit/tabular-consolidation-raw-cell-parity.json` and
  `source-audit/tabular-consolidation-prior-ars-intersection-detail-parity.json`.
- The retained 7.9 Ramp Detail PDF source was reconstructed from all 126 route
  prints and compared with the retained Excel sibling through the public self
  comparator. All 15,216 rows pair exactly: zero one-sided rows, zero differing
  rows, and zero differences across 121,728 asserted plus 60,864 context cells.
  This closes the prior-PDF source-truth gate for the classic Ramp Detail (PDF)
  comparison.
- The retained 7.9 Highway Log PDF source was reconstructed from all 252 route
  prints and compared with its retained Excel sibling. The result has 51,884
  paired rows, two genuine PDF-only rows, and 619 genuine cells on 618 rows:
  608 left-bound traveled-way widths and 11 signal-change dates. An independent
  raw-source audit passed all 23 distinct width value-pair classes, every signal
  date, and both one-sided keys against the original route XLSX and original PDF
  text lines. Durable witness:
  `source-audit/prior-7.9-highway-log-sibling-raw-source-audit.json`.
- The retained ARS 7.9 Intersection Detail PDF and Excel siblings each contain
  16,459 paired rows with no one-sided rows. All 278 whitespace-only
  Description representation residuals repeat in the fresh siblings. The sole
  extra prior difference was traced to original route 108 sources at post mile
  `005.870`: the XLSX stores H/G `U`, while the PDF visibly prints `D`. This
  genuine source cell exactly explains the classic Excel count of 17,563
  versus the PDF count of 17,562. Durable witness:
  `source-audit/prior-7.9-intersection-detail-pdf-excel-raw-source-truth.json`.
- Production By Day reproduced the expected numeric payloads, but 12
  values/formulas workbooks across Ramp Summary, Intersection Summary, Highway
  Sequence Excel/PDF, and Highway Log Excel/PDF contain a false visible “older
  normalization — rebuild” warning because the temporary TSN consumer copy lost
  the fresh source-claims sidecar. Durable witness:
  `source-audit/all-completed-workflow-note-audit.json`.
- By Day Ramp Summary used 126 TSMIS PDFs and the statewide TSN PDF, but an
  evidence-enabled run retained zero evidence files.
- Installed Excel successfully recalculated disposable copies of all nine
  delivered direct-vs-TSN values/formula pairs. The live twins contain
  11,368,483 formula cells and the values twins retain 1,810,549 intentional
  self-check formulas. The complete 9/9 cached-value audit compares 42,813,677
  cells and passes every substantive Summary, Spot Check, and data-sheet
  parity check after excluding only the documented flavor-specific prose/F9
  row. All source hashes bind, with zero formula-text errors, cached Excel
  errors, merge mismatches, sheet-state mismatches, or unexpected semantic
  differences. Durable witness:
  `source-audit/direct-installed-excel-formula-audit.json`.
  All direct deliverables remain denied independently under their semantic or
  visual findings.
- Installed Excel also fully recalculated all nine delivered production By Day
  vs TSN values/formula pairs. All nine pass cached-value parity: 11,368,483
  live formula cells, 1,810,549 intentional values-twin formulas, and
  42,813,659 compared data cells. The 962 raw cached-value differences and nine
  Summary shape offsets are entirely the documented formula/value flavor prose
  and F9-help-row presentation; every substantive semantic check passes. All
  source hashes bind, with zero formula-text or cached Excel errors, merge
  mismatches, or sheet-state mismatches. Durable witness:
  `source-audit/by-day-tsn-installed-excel-formula-audit.json`.
- Installed Excel also recalculated disposable copies of all nine delivered
  classic cross-version values/formula pairs. All nine passed: 9,682,957 live
  formula cells, 1,654,097 intentionally live formula cells in values twins,
  and 39,607,355 data cells compared, with zero formula-text error tokens,
  cached Excel errors, or unexpected semantic mismatches. Durable witness:
  `source-audit/classic-cross-version-installed-excel-formula-audit.json`.
- Installed Excel recalculated and data-compared all three delivered direct
  PDF-vs-Excel SELF pairs. All three passed: 4,494,021 live formula cells,
  779,179 intentional values-twin formulas, and 18,664,272 data cells
  compared, with zero formula-text errors or cached Excel errors. Their final
  deliverable decisions remain denied under PCOA-CX-007/014. Durable witness:
  `source-audit/direct-self-installed-excel-formula-audit.json`.
- Installed Excel recalculated and data-compared all seven delivered Baseline
  pairs. All seven passed: 8,230,837 live formula cells, 1,455,991 intentional
  values-twin formulas, and 32,819,899 compared cells. There are zero formula
  text errors, cached Excel errors, merge/state mismatches, or unexpected
  semantic differences. The 628 raw differences and seven Summary offsets are
  exactly the documented formula/value prose and help-row presentation.
  Durable witness:
  `source-audit/baseline-installed-excel-formula-audit.json`.
- The application-independent deliverable-sheet gate has passed all nine
  classic cross-version pairs, all nine direct-vs-TSN pairs, all seven
  available Baseline pairs, all nine By Day pairs, all three delivered direct
  SELF pairs, and the one Clean Road Highway pair. It binds the published
  payload, independently recounts every Summary
  and per-field claim, recomputes every Routes rollup, checks visible and
  very-hidden sheet states/order, confirms Comparison filters/freeze panes, and
  verifies provenance against both workbook hashes and the exact input recipe.
  Baseline's seven formula packages also pass: 8,230,837 live formula cells,
  zero formula error tokens, and a valid calculation policy. Large route
  workbooks are correctly accepted only when manual calculation is paired with
  the visible red F9 instruction; summaries remain automatic.
- Native Excel plus the spreadsheet artifact renderer proved a separate visual
  defect that structural gates do not catch. The final isolated Everything
  audit adds eight failing summary workbooks and 244 clipped cells: ENV Ramp
  Summary has six per twin, ENV Intersection Summary has 11 per twin, TSN Ramp
  Summary has 34 per twin, and TSN Intersection Summary has 71 per twin. The
  complete PCOA-CX-013 scope is now 24 statewide summary workbooks and 748
  materially clipped cells after excluding hidden helpers and allowing six
  pixels of measurement tolerance. Durable witnesses:
  `source-audit/statewide-summary-visible-text-clipping.json` and
  `tmp/post_comparison_output_audit/source-audit/everything-v2-statewide-summary-visible-text-clipping.json`.
- A separate large/detail visual gate reviewed 32 workbooks across 16
  representative values/formula pairs, then applied the same exact stored
  layout facts to all seven delivered classic detail pairs. Every pair is
  denied: populated/formula-bearing neighbors block visible overflow from
  materially undersized Summary and Spot Check labels (about 37–360 px), and
  selected composite keys are 12–36 px too narrow. Native Excel directly
  confirmed both the direct and classic Ramp Detail (PDF) Summary/Spot Check
  failures. All 32 otherwise pass active-sheet, helper visibility, snapshot
  state, pane, merge, and top-of-sheet error-token checks. Durable witness:
  `source-audit/large-detail-no-render-visual-adjudication.json`.
- Final isolated Everything package adjudication independently adds all seven
  ENV detail pairs, all seven TSN detail pairs, and all four SELF pairs: 18
  pairs / 36 workbooks with 250 material denied cell instances across the
  shared `Summary` and `Spot Check` sheets. PCOA-CX-014 therefore now covers
  41 affected pairs / 82 workbooks. All 44 final Everything workbook hashes
  bind to their manifests, every populated audited cell has a stored decision
  and reason, and the required shared-clipping checks propagate in every
  workbook. Durable witness:
  `tmp/post_comparison_output_audit/source-audit/everything-v2-visual-parity-independent-validation.json`.
- Clean Road TSN normalization preserves all 60,083 rows × 74 columns exactly.
  A fresh deliverable-sheet recount passes at 52,647 paired rows, 5,081
  ArcGIS-only rows, 7,436 TSN-only rows, 2,635 identical rows, 50,012
  differing rows, and 291,292 differing cells. The fresh all-field screen
  binds every field claim, finds zero malformed displays, and reproduces
  exactly the same five formatting-equivalence candidates. Formula-package
  and structure gates cover 6,442,773 live formulas with zero formula error
  tokens and a valid manual/F9 policy. The five landmark cells were traced
  through the ArcGIS build/raw layer and normalized/raw TSN.
- Installed Excel fully recalculated disposable copies of the Clean Road
  values/formula pair. Cached-value parity passes across 24,768,177 cells:
  6,442,773 live formula cells, 484,374 intentional values-twin formulas,
  zero formula-text or cached Excel errors, zero merge/state mismatches, and
  zero unexpected semantic differences. The 274 raw differences are exactly
  272 Summary plus two Spot Check flavor-presentation cells, and the one shape
  offset is the expected live-formula Summary help row. Both source hashes
  remain current and match the frozen pair manifest. Durable witness:
  `source-audit/clean-road-installed-excel-formula-audit.json`.
- The independent Clean Road ArcGIS-build audit is complete. The public build
  is exactly rule-faithful across 57,728 rows, 252 routes, 74 fields, and
  4,271,872 cells, with zero mismatches, duplicate keys, or route-count
  failures. It also exposes a material raw-input limitation: 102 current rows
  marked `LocError=NO ERROR` have one missing PM endpoint and are silently
  skipped under the no-guess contract. Exact output-key joins prove 161
  published false-positive cells plus four additional genuine differences
  displayed with a false blank ArcGIS side, across 83 comparison rows. No
  missing span was inferred, and the values workbook's Summary/Notes disclose
  none of the condition.
  Durable witnesses:
  `source-audit/clean-road-highway-raw-source-truth.json` and
  `source-audit/clean-road-comparison-unlocatable-impact.json`.
- Intersection Detail TSN normalization independently passed for all 16,626
  rows × 38 output columns (631,788 cells), including strict date conversion,
  signal-control crosswalks, route suffixes, numeric canonicalization, and
  district/county sidecars.
- The first evidence-eligible detail review is complete. Highway Sequence
  PDF-vs-PDF retained all 12 requested images and a PDF-only bound read set, but
  six crops mark the wrong target on special `EQUATES TO` lines; the cell is
  denied rather than credited merely for file availability.
- The eligible By Day Highway Log PDF-vs-PDF bundle is complete but visually
  denied: all 180 images and the 128-file PDF read set bind to the manifest,
  but an adversarial second full-resolution review corrected the crop ruling
  to 178/180. Both route 395 / `T121.831` Description layouts draw the TSN
  target across the following row. By contrast, the
  prohibited Intersection Detail PDF-vs-normalized-XLSX row emitted 142
  borrowed-PDF images; 140 targets are accurate and two `Control Type` layouts
  box `P` while claiming normalized TSN `S`.
- A late “evidence skipped” message in the first By Day records was traced to
  the disposable audit launcher's cp1252 stdout callback, after atomic evidence
  publication. It is not counted as a product defect. The launchers are now
  UTF-8-safe. The exact final Everything evidence sequences subsequently
  completed through the same production core; their ledgers, artifact
  bindings, eligibility decisions, and crop decisions are recorded in Matrix
  E and the final evidence witnesses.
- The interrupted first Everything SELF launcher is also quarantined as
  harness history. It passed the generic word `self`, while production rows
  expose concrete `vs_pdf` or `vs_excel` ids; the registry therefore fell back
  to the row's default Environment mode. The corrected launcher resolves the
  actual supported mode id from `matrix.all_row_modes()`. Final SELF coverage is
  the five reviewable production cells: Highway Log in both directions,
  Intersection Detail PDF, Highway Sequence PDF, and Ramp Detail PDF.
- The first set of nominally isolated Everything stores is provisional only.
  Its comparison destinations are separate, but each complete environment
  directory was junctioned to the common fixture, which also shared that
  environment's generated `consolidated` directory. Atomic deterministic writes
  prevented a known corrupt workbook, but concurrent shared provenance is not
  strong enough for personal approval. The final Everything arithmetic
  decisions therefore use only the restaged v2 stores whose raw report folders
  alone are junctioned and whose `consolidated` and `comparisons` directories
  are lane-local.
- Those corrected final isolated v2 stores are now complete. All 22 delivered
  pairs pass manifest binding, sheet contracts, package integrity, formula
  structure, and independent recounts; the exact 25-check typed-result parity
  audit passes. Visual adjudication nevertheless denies all 44 delivered
  values/formulas workbooks for propagated material clipping. Ramp Detail ENV
  and TSN, plus Ramp Detail PDF SELF, remain the three intentional
  no-deliverable product rejections.
- The installed-Excel gate is complete for every separately generated
  workflow/report pair: 60/60 pairs, 79,809,913 live formula cells, 12,557,083
  values-twin formula cells, and 313,497,190 compared cells. All 746 semantic
  checks pass, with zero unexpected formula, cached-value, merge, state, or
  semantic failures. The additional terminal-subset recheck covers 39/39
  Baseline, By Day, Clean Road, and final Everything pairs; all 485 semantic
  checks and all 156/156 fresh workbook hash/size bindings pass. Its 4,298 raw
  presentation differences are exactly 4,236 Summary plus 62 Spot Check flavor
  cells, with 39 expected Summary shape offsets. This approves the formula
  execution/output gate only; it does not override the report-level denials.
  Durable witnesses:
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-ALL-WORKFLOWS-AUDIT.md`,
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-ALL-WORKFLOWS-AUDIT.json`,
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-FINAL-AUDIT.md`
  and
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-FINAL-AUDIT.json`.
  Independent rollup witness:
  `tmp/post_comparison_output_audit/source-audit/SUBAGENT-ALL-WORKFLOW-FORMULA-ROLLUP-VERIFICATION.md`.

## Remaining work before joint approval

Codex has closed the frozen topology at **88 decisions = 68 `DENIED` + 16
`BLOCKED` + four `N/A`**, with zero open topology decisions, zero remaining
`UNVERIFIED` status cells in the Codex-controlled matrices, and no
registry/structure mismatch. Matrix E evidence gates are a separate exact
25-cell registry and are also terminal at 16 `DENIED`, six `APPROVED`, and
three `N/A`.

The only remaining work is the sequential Claude challenge and
Codex/Claude conflict reconciliation. These are Codex decisions, not joint
approvals.
