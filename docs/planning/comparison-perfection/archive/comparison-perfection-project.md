# Comparison perfection project

> **Archived — historical.** Superseded by the current surface: [COMPLETION-PLAN.md](../COMPLETION-PLAN.md) (plan & status) and [README.md](../README.md). Kept verbatim as point-in-time history; counts/hashes here reflect when it was written.

Last updated: 2026-07-14  
Project state: audit closeout complete through Stage 8; product code frozen; implementation handed off/deferred  
Folder index: [README.md](../README.md)  
New-AI reconciliation prompt: [new-ai-reconciliation-prompt.md](new-ai-reconciliation-prompt.md)  
Primary finding ledger: [comparison-audit-findings.md](../comparison-audit-findings.md)  
Execution plan: [comparison-remediation-plan.md](../comparison-remediation-plan.md)  
Canary ledger: [comparison-canary-bindings.md](../comparison-canary-bindings.md)  
Phase-4 fixture/source index: [comparison-phase4-red-fixture-index.md](../comparison-phase4-red-fixture-index.md)  
Implementation handoff: [comparison-implementation-handoff.md](comparison-implementation-handoff.md)  

Raw TSN source re-baseline: [comparison-phase4-tsn-source-rebaseline.md](../comparison-phase4-tsn-source-rebaseline.md)

## At-a-glance progress

This is the owner-facing progress dashboard. Stage count is a navigation aid, not an
effort percentage: the remaining cross-format/evidence stages are data-heavy.

Current position: **8 outcome stages complete, 4 deferred**. The shared engine
foundation is green. Stage 5 closed on the accepted `raw-2026-07-12-r7` current-code
witness after repeated adversarial reopenings rejected r3-r6. All three XLSX-to-PDF TSN
source-format gates are accepted. Stage 6 is complete: all seven independent
raw-to-normalized family audits are accepted, including Highway Log after two
byte-identical full-corpus replays. Stage 8 base TSMIS-vs-TSN audit truth is complete at
**7/7 families**. Each family is source-bound at the audit/oracle layer. This is not a
claim that product comparison or evidence behavior is perfect: known product defects
remain red and implementation is frozen under the owner's 2026-07-14 directive. The
TSMIS companion-format, historical-edition, and source-to-evidence validation chain
is deferred to the next implementer.

| # | Outcome gate | State | Current evidence / promotion condition |
|---:|---|---|---|
| 1 | Capability census, adversarial findings, independent decisions | Complete | 29 classic recipes, 12 Matrix rows/30 placements, seven TSN datasets, five evidence families; ledger through CMP-AUD-237 |
| 2 | Safety, source selection, ownership, truthful outcome/publication | Complete | Phase 1-2 focused gates and full-suite closures recorded in the finding ledger |
| 3 | Equality, duplicate pairing, workbook twins, installed-Excel production proof | Complete | Phase-3 119/119 plus accepted `CORE-ID-78-XLSX-TSN` r3 canary |
| 4 | Exact raw TSN source/evidence binding and clean pre-hardening baseline | Complete | 29 core + 14 evidence members hash-bound; r2 is the accepted pre-contract semantic/isolation baseline, not a current-code witness |
| 5 | Raw admission, producer completion, build isolation, shared identity substrate | Complete | `r7` builds all seven complete/0/0 from the exact raw manifest, certifies coherent raw+normalized tokens, proves unchanged reuse/global stability, and matches r2 across 5,547,205 typed/value cells; immutable normalized consumer capture and drift/cache/evidence guards are green |
| 6 | Independent raw-to-normalized record/key/field conservation | Complete | All seven source-bound independent oracles are current. The corrected Ramp reissue preserves all 15 raw numeric Description prefixes and passes 14/14 invariants, 6/6 mutations, detached acceptance, and byte-identical full replays while retaining three product-red findings. |
| 7 | TSN XLSX-to-PDF row/category/section parity | Complete | Ramp, Intersection, and Highway Detail permanent gates are exact-source-bound and green with zero unresolved residue; every row/category/section mapping and classified source-date delta is retained |
| 8 | Seven base TSMIS-vs-TSN comparison oracles | **Complete — 7/7 base audits** | All seven families are accepted only at the source-bound audit/oracle layer; product comparison, physical-identity, and evidence perfection remain explicitly false where findings are open |
| 9 | Every available TSMIS companion-format and historical-edition oracle | **Deferred / next implementer** | Same-pull Excel↔PDF↔TSN triangles for all seven report families, including Ramp Summary Excel and Intersection Summary PDF even where currently export-only; older editions must prove versioned compatibility or fail-closed drift without overriding current truth |
| 10 | Evidence and layered Report View end-to-end proof | **Deferred / next implementer** | Both PDFs, normalized rows, Comparison cells, categories/sections, images, and Report View must have zero unexplained residue; exact TSMIS/TSN PDF bytes must be captured/manifest-bound so live-path A-to-B-to-A cannot bless different rendered evidence |
| 11 | Family identity/loader/parser/provenance remediation | **In progress (owner-authorized remediation)** | RD + ID (2026-07-14), HSL (2026-07-16), and HL (2026-07-17 — normalizer v5: detached route suffixes keyed as TSMIS's ten suffixed routes, asterisk-leading Descriptions conserved, ownership/ADT/totals/provenance claims + reconciliation gates, pre-v5 files refused) are integrated + corpus-verified; the CMP-AUD-045 identity gate is 11 green / 0 known-red and HL Route-1 re-blessed exact; HD-Excel county stays vendor-blocked; provenance findings CMP-AUD-050 (route universe), all three CMP-AUD-049 halves (document-authoritative route identity — refusal-free on all 1,099 statewide 7.9 per-route PDFs), and CMP-AUD-066 (PDF-role provenance: the `TSMIS PDF Conversion` marker required on the PDF role, rejected on the Excel role) closed 2026-07-17; CMP-AUD-067 remains open |
| 12 | Full capability regression and release-quality acceptance | **Deferred / next implementer** | All 12 Matrix rows, 29 classic recipes, both workbook modes, validation/evidence, real Excel, and bound canaries green |

### Current work

- The earlier raw boundary remains focused-green for exact-one or exact D01-D12 admission, strict
  schemas/claims, immutable captured parsing, content-manifest reuse, durable certificate
  publication, certified-current consumption, explicit completion, and attempt isolation.
- The lifecycle runner proves the public build, sidecar, current, unchanged reuse,
  exact output universe, whole-run raw/evidence stability, code provenance, and atomic
  acceptance. The production certificate now binds exact normalized bytes, requires a
  coherent multi-pass sidecar/raw/workbook snapshot, and refuses producer-partial reuse.
  Canonical token/cache/target-lease guards and immutable normalized-workbook capture are
  focused-green for Everything/by-day comparison and evidence entry points.
- The accepted `raw-2026-07-12-r7` current-code witness binds the exact 29-member core and
  14-member evidence manifests, all seven complete/0/0 outputs and sidecars, coherent
  tokens, immediate unchanged reuse, exact 14-artifact output universe, stable code, and
  stable sources. An independent r2/r7 stream found zero sheet/type/value differences
  across 5,547,205 cells. r2 remains the pre-hardening semantic baseline; r3-r6 are
  rejected partial audit attempts, not witnesses.
- Ramp, Intersection, and Highway Detail full-corpus XLSX-to-PDF/category/Report-View
  source maps are accepted permanent gates with zero unresolved residue. Highway Detail
  proves 60,081 printed records against 60,083 XLSX rows across all 12 districts and
  4,123 pages, with two exact XLSX-only occurrences and a frozen 443-item dated-delta
  allowlist.
- Stage 6 Ramp Detail is accepted again under the corrected source-preserving contract.
  Its 64,727-byte result classifies exactly 15 current normalized Description losses—nine
  same-route and six different-route prefixes—in addition to 313 omitted `PM_SFX` claims
  and two omitted PDF-printed effective fields. All 14 invariants and six semantic
  mutations pass; two full replays reproduced identical result and acceptance bytes.
  CMP-AUD-133/CMP-AUD-135 remain product-red; audit acceptance does not excuse the loss.
- CMP-AUD-134/CMP-AUD-136/CMP-AUD-137 remain remediated in the reissued Ramp evidence: the
  shared XLSX reader parses only a private captured payload, rejects error-typed cells,
  survives an actual same-object A-to-B-to-A fixture, and the family audit binds all
  order/contiguity and final-publication checks. Intersection and Highway Detail are
  being held to that same acceptance contract rather than inheriting Ramp's result.
- Intersection Detail and Highway Detail are now independently accepted under that
  contract. Intersection preserves three omitted source fields as product-red. Highway
  Detail preserves DCR/ADT/change-flag omissions, the exact one-cell Length defect, and
  two printed snapshot-date omissions as three blocking product findings; its 23
  invariants, 22 probes, result hash, eight post-write identities, and detached
  acceptance passed final second review.
- Ramp Summary is independently accepted over the authoritative three-page PDF and all
  31 normalized rows. All four section axes total 15,410; 18 invariants, 13 mutations,
  exact 13-role disposition coverage, 95 parser modules, and 103 live identities pass.
  Projection is exact and zero-residue; full conservation remains false only because
  CMP-AUD-146's printed report provenance is absent from normalized artifacts.
- Intersection Summary is independently accepted after visual inspection of all three
  pages, byte-identical full replay, 19 invariants, 17 mutations, 62/62 source
  dispositions, and 58/58 per-category typed ledgers including Total. Projection is
  exact/zero-residue; CMP-AUD-144/CMP-AUD-145/CMP-AUD-146 remain product-red.
- Highway Sequence is independently accepted after a 36-page visual sample and two
  byte-identical 1,540-page full replays. Its 22 invariants, 14 mutations, 47 parser
  modules, exact 69,804-source-record/69,758-target-row census, and zero unexplained
  residue pass. Projection/full remain false only for CMP-AUD-155/156/158/159: omitted
  provenance, 565 blanked pointer tokens, 46 dropped pre-county equates, and one invented
  comma.
- Highway Log now closes Stage 6 after the initial diagnostic and corrected candidate
  were adversarially reopened under CMP-AUD-167 through CMP-AUD-182. The accepted
  source-bound audit classifies all 60,083 rows and 13,549 totals across 2,121 pages with
  zero unclassified/unparsed lines, exact projection, eight frozen datasets, all four
  collision domains, 12 document manifests, and an exact stable 47-module parser
  manifest. Its 34 invariants and 53 mutations pass. Fresh 822-second and 823-second
  runs produced byte-identical 10,879,397-byte result and 6,502-byte acceptance files.
  CMP-AUD-045/157 remain product-red for lost ownership/qualifier, ADT, totals, and
  provenance facts; Stage 6 acceptance does not excuse those omissions.
- Stage 8 Ramp Summary base comparison truth is accepted. The oracle binds 504 current
  TSMIS members and the accepted TSN chain, proves all 3,780 same-pull Summary PDF/XLSX
  values identical, reconciles every 15,216 route total to both Detail forms, and
  explains the exact 22-count printed Ramp-Type residual with two P and twenty V Detail
  records. Independent truth is 29 shared categories, two TSN-only Summary categories
  (P/V), no TSMIS-only comparison categories, five identical shared rows, and 24
  differing shared rows. Production emits every source-backed value exactly but remains
  semantic-red under CMP-AUD-024/025: it fabricates TSMIS zeros for P/V and injects the
  59-point no-linework display metric into the verdict universe. Two full source-bound
  runs reproduced byte-identical 491,099-byte result and 11,568-byte acceptance files.
- Stage 8 Intersection Summary base comparison truth is accepted. The oracle binds the
  authoritative 217-file Excel tree, its 217-file PDF sibling, the exact raw TSN PDF,
  accepted normalized/Stage-6/cross-format chain, and the TSNR reference. Every one of
  14,322 same-pull Excel/PDF values is identical. Independent truth is 66 union rows:
  58 shared, eight TSMIS-only, zero TSN-only, 53 differing shared, and five identical
  shared; totals are TSMIS 16,459 and TSN 16,626. Production projects the values and
  current comparison semantics exactly, but full source conservation and end-to-end
  perfection remain red under CMP-AUD-020/021/022/023/076/144/145/146/183/184. Two
  complete direct-authoritative replays reproduced byte-identical 1,124,870-byte result
  and 11,322-byte acceptance files.
- Stage 8 Ramp Detail is accepted from both 126-route current TSMIS trees, the raw TSN
  XLSX and PDF, the accepted r7 normalized workbook, the corrected Stage-6 result, and
  the accepted TSN cross-format oracle. Under the approved D4 key
  `(Route, County, norm_pm(PM))`, Excel source truth is 15,212 paired, four TSMIS-only,
  198 TSN-only, 14,471 identical, 741 differing rows, and 847 differing cells; PDF
  source truth is 15,212 paired, four/198 one-sided, 14,438 identical, 774 differing
  rows, and 998 differing cells. PDF↔Excel pairs all 15,216 rows and has exactly four
  Description render differences. Production remains red under CMP-AUD-045/133/135/185:
  it uses weak Route+PM identity, creates 15 false Description differences, omits the
  sole real District 12-vs-11 disagreement at `005/SD/72.366`, and cannot reconstruct
  the omitted raw claims. Two full runs reproduced byte-identical 1,703,996-byte result
  and 13,473-byte acceptance files; the permanent gate passes 36 assertions.
- Stage 8 Intersection Detail is accepted from the current 217-route ARS-prod Excel/PDF
  pair, raw TSN XLSX/PDF pair, accepted normalized and cross-format chains, and all five
  production legs in both workbook modes. The independent physical key is
  `(base Route, County, complete PP, numeric Post Mile)`. Excel-vs-TSN is 16,199 paired,
  260/427 one-sided, 16,053 differing rows, and 21,676 differing cells; PDF-vs-TSN has
  the same row universe and 21,683 differing cells. PDF-vs-Excel pairs all 16,459 rows
  and differs in exactly nine cells: eight unrenderable trailing-tab Description values
  and one source-backed HG conflict where PDF plus both TSN forms agree against Excel.
  The 1,059,072-byte result reproduced byte-for-byte across two full replays at SHA-256
  `7c7734aae212fbf9ad55de554cd2a0111549479b764ff3b91695fb524f21d86c`.
  All 24 audit invariants and 31 permanent assertions pass. Production remains red under
  CMP-AUD-045/068/070/133 for weak Route+PM identity, missing PDF Report View, discarded
  explicit Route/S claims, and normalized source-only field loss.
- Highway Detail is independently accepted as the fifth Stage-8 family. Its TSN source
  remains authoritative, while every TSMIS layout claim stays version-pinned and
  fail-closed because the vendor has not finally approved that report. The audit-owned
  parser accounts for all 51,273 current Excel rows and 51,216 current PDF rows, 4,065
  DCR headers, and zero unclassified PDF groups. All 60,083 raw/normalized TSN rows are
  retained, with exactly the known `01/HUM/096/R044.236` Length normalization defect.
  No County is inferred from TSN, filename, row order, or folder date.
- Every Excel row now has snapshot-backed physical ownership: 48,143 exact current
  companion signatures, three unanimous current companion keys, 3,125 exact rows from
  the separately bound same-build 7.7 route-005 pair, and two 005S descriptions printed
  as components of one current PDF row. The 005S bridge attests owner only and invents
  no PDF record or non-owner cells. The later route-005 PDF remains a separate snapshot;
  all eight changed DCR owners are frozen as CMP-AUD-192 rather than blended into the
  byte-identical older Excel payload. Snapshot-aware Excel-vs-TSN truth is 48,647 paired,
  2,626/11,436 one-sided, 48,494 differing rows, and 205,809 differing cells. Current
  PDF-vs-TSN truth is 48,163 paired, 3,053/11,920 one-sided, 48,010 differing rows, and
  203,320 differing cells.
- Both 3,384,044-byte full-corpus results are byte-identical at SHA-256
  `9d793fb166197701e20d8ac6bc8aa34bd64221a15507dff5bbe7416bc7095554`.
  All 34 terminal invariants, 79 permanent mutations, post-write source/origin/code/
  dependency checks, and every formula/value publication identity pass. Acceptance is
  deliberately red for product end-to-end semantics: CMP-AUD-042/045/054/068/076/133/
  138/142/186 retain the PS loss, weak identity, PDF parse loss, missing PDF Report View,
  absent durable source identity, omitted source claims, Length conversion, omitted
  snapshot dates, and multi-baseline truncation. No product code was changed.
- Highway Sequence Stage-8 base audit is accepted. Its current base is the freshest
  `All Reports 7.9` same-run SSOR-production pair: 252 Excel members / 24,634,973 bytes
  and 252 PDF members / 39,236,260 bytes, checked against the authoritative 12-district
  TSN PDF library and accepted Stage-6 normalization chain. CMP-AUD-193 was documented
  before changing any assumption: the widely repeated route-037 `003.809` residual
  belongs to the 7.8-Excel/first-7.9-PDF cross-bundle fixture and is fixed in the same-run
  Excel. The full edition census also finds six July-9 Excel Description additions and
  one added row across routes 002/010/037/101; only the old route-037 residual is printed
  in PDF, leaving four paired PDF Description omissions plus one Excel-only described
  row to preserve: five unrepresented Description claims total.
  The immutable capture now binds 1,008 TSMIS members plus the 12 authoritative TSN
  PDFs. Independent parsing closes 60,494 Excel and 60,493 PDF rows across all 3,177
  physical PDF pages (2,673 data pages), 312 wrapped fragments, and zero unclassified
  table lines. Same-source semantic identity gives 60,493 pairs plus the one Excel-only
  row. Exactly 1,410 pairs differ in 3,721 displayed cells: Description 1,133 (1,129
  equate annotations plus four real omissions), FT 1,129, HG 910, and PM suffix 549.
  The 549 suffix cells
  split into 272 two-row representation moves (544 cells) and five PDF-only suffixes;
  route 152 proves the old glued-suffix key cross-pairs two different occurrences.
  Installed Excel independently decodes the four lowercase `_x000d_` cells to CRLF,
  exposing a product false-positive rather than four real source differences.
  Product consolidation then completed from the private bytes in 392 seconds and is
  cell-for-cell exact against both independent TSMIS datasets. The corrected direct-
  source r2 checkpoint now binds all 69,804 raw records, the separate 69,758 keyable
  projection, all 46 explicit unknown-County one-sided equates, 565 printed pointer
  tokens, and the one Description punctuation change. Its current and historical source
  legs, nine mutation rejections, exact-byte TSMIS captures, and zero-residue result are
  independently reopened. The independently reviewed direct runner is frozen at SHA-256
  `bcc952fb3469b0e790e72eb25e1397f4639ef78ef1427ae2ea626d22ca001e91`;
  its Excel-vs-raw and PDF-vs-raw legs completed in 404.636/407.4 seconds with exact
  10-file terminal universes and counts 57,072/3,422/12,732/4,822/5,516 and
  57,505/2,988/12,299/4,845/4,929. The 139,453-byte final gate SHA-256
  `b875437981626449810234922eeafe5f5aa5c716e893d22a5df5b7c65cf66a79`
  produced two byte-identical 42,140-byte results at SHA-256
  `f7f60e526b21935df8109e3772fc99b4cc3aded85e7294a6a83c7f19398d82fe`
  and two byte-identical 1,510-byte acceptances at SHA-256
  `7e2e9ce44c14e3f5a095fa410548ff1de71eaf5820a2c348ed9ed52e40ca1c6c`.
  All 20 direct artifacts rehash exactly. Fourteen known product/evidence findings remain
  red for a later implementer; no product code was changed.
- Highway Log closes the seventh and final Stage-8 base audit without certifying the
  product. The source witness binds matching 252-member current TSMIS Excel and PDF
  route universes plus the accepted 12-PDF/60,083-row TSN chain. The independent oracle
  gives Excel-vs-TSN 48,094 paired / 3,790 Excel-only / 11,989 TSN-only / 39,466
  differing rows / 140,333 differing cells, and PDF-vs-TSN 48,096 / 3,790 / 11,987 /
  39,463 / 139,786. The completed product publications reproduce those counts and all
  989 exact duplicate-assignment groups per leg. Two clean final-gate roots produced
  byte-identical 9,036-byte results at SHA-256
  `7acf9986055750bbc49be0d4fa422329d06893f379da0cd6ded945936549860b`
  and 839-byte acceptances at SHA-256
  `170d622d751e96e97c7f8420c0a60172e57a31838a3d1b3de090c76972dd62b6`.
  The gate deliberately keeps family/product/evidence perfection false and carries
  CMP-AUD-045/047/048/049/050/066/067/157 forward. The interrupted r1 attempts are
  rejected, not witnesses. No product code was changed during this bounded closeout.
- The typed physical-identity core is green for serialization, mixed-mode admission,
  route authority, display, and full-PM claims. Family projector integration belongs to
  Stage 11 after source conservation/comparison/evidence truth is established.

### Current blockers to the next promotion

There is no active promotion under the current authorization. Stage 8 is closed at the
non-certifying base-audit layer, and the product tree is frozen. The remaining blockers
are deliberately handed to a later implementer:

1. Stage 9 must complete every available same-pull TSMIS Excel↔PDF↔TSN triangle and
   historical-edition oracle without mixing snapshots or allowing old data to override
   current truth.
2. Stage 10 must bind both source PDFs, normalized rows, Comparison cells, evidence
   images/captions, and layered Report View placement to one generation with zero
   unexplained residue.
3. Stage 11 must correct every still-red schema, identity, parser, projection, and
   provenance finding using the stable red fixtures. Audit-layer acceptance does not
   waive those defects.
4. Stage 12 must run the complete capability, workbook-mode, evidence, installed-Excel,
   and release-quality regression after remediation.

Next promotion point: none under the current authorization. Resume only from the
[implementation handoff](comparison-implementation-handoff.md) after the owner explicitly
authorizes product changes.

## Project document map

Use this order instead of treating every planning file as equal:

| Need | Authoritative document |
|---|---|
| Owner directives, progress, current blockers, document navigation | This project dashboard |
| Every issue, reproduction, correction requirement, and status | [comparison-audit-findings.md](../comparison-audit-findings.md) |
| Frozen scope, unfinished work, and ordered implementation handoff | [comparison-implementation-handoff.md](comparison-implementation-handoff.md) |
| Phase/batch sequencing and dependency gates | [comparison-remediation-plan.md](../comparison-remediation-plan.md) |
| Phase-4 finding-to-red-check/canary ownership | [comparison-phase4-red-fixture-index.md](../comparison-phase4-red-fixture-index.md) |
| Exact raw/evidence member hashes, source roles, builder witness, identity facts | [comparison-phase4-tsn-source-rebaseline.md](../comparison-phase4-tsn-source-rebaseline.md) |
| Accepted/provisional/blocked real-data counts and artifact hashes | [comparison-canary-bindings.md](../comparison-canary-bindings.md) |
| Approved Phase-3 semantic decisions | [comparison-phase3-decision-gates.md](../comparison-phase3-decision-gates.md) |
| Claude/Fable advisory reviews | [claude-comparison-audit-second-opinion.md](claude-comparison-audit-second-opinion.md) and [fable5-comparison-remediation-decisions.md](fable5-comparison-remediation-decisions.md) |
| Executable test catalog and latest suite closure | [../../verification-and-testing.md](../../../verification-and-testing.md) |

Historical comparison outputs and prose are evidence only. When documents disagree,
the owner directives and exact source facts in this dashboard/source record win; the
conflict must be repaired in the other document rather than silently chosen at runtime.

## Owner directives

These instructions govern the entire comparison-perfection project and supersede
compatibility with known-wrong historical output:

1. The target is a perfect, factually correct comparison every time, regardless of what
   must change or what earlier versions/tests expected.
2. Audit adversarially. Verify claims independently, document every issue before fixing
   it, preserve its red reproduction, and do not close it merely because a broad suite is
   green.
3. Treat the authoritative raw TSN reports as the starting truth for vs-TSN work. Do not
   infer TSN semantics from an old normalized workbook, old comparison output, prose, or a
   historical count.
4. `C:\Users\Yunus\Downloads\TSMIS\tsn_library` is deliberately raw-only. The app owns
   every generated normalized/consolidated derivative; audit rebuilds go only to isolated
   workspace/audit storage so stale generated files cannot interfere.
5. Verify that every TSN source is represented faithfully whether its source format is
   XLSX or PDF. A successful parse is not enough: every authoritative record, identity,
   asserted field, anomaly, and producer-completeness claim must reconcile.
6. Audit the entire chain, not just the comparator:

   `raw TSN -> current normalizer/parser -> normalized rows -> comparison rows/cells -> source PDFs -> evidence artifact`

7. For evidence-supported reports, evidence is an acceptance oracle rather than optional
   decoration. The parsed TSMIS PDF, parsed/located TSN PDF, normalized values, Comparison
   sheet, and evidence captions/highlights must agree. The acceptance target is zero
   unexplained evidence discrepancies.
8. Ask for additional examples/files only when an exact source fact is absent. Stop that
   specific flavor instead of guessing. The current corpus is expected to contain nearly
   everything required.
9. Highway Detail TSN is stable/authoritative. The TSMIS Highway Detail report/export is
   still awaiting full vendor review, so its exact observed TSMIS shape is provisional,
   version-pinned, and fail-closed on drift. That limitation must not weaken any other
   family's contract.
10. Read and carry forward `CLAUDE.md` and its linked documentation; update this record,
    the finding ledger, the canary ledger, and the verification catalog as work advances.
11. As of 2026-07-14, stop before any further product/comparison implementation. Finish
    the bounded Highway Log audit closeout, consolidate the findings and exact handoff,
    prove that the frozen `scripts/` tree did not change during closeout, and leave all
    product remediation for a later implementer unless the owner explicitly reauthorizes it.

## Owner-instruction and progress log

This is the durable hand-off record for Codex, Claude, and any later reviewer. It records
the owner's direction as project requirements rather than relying on task memory.

| Recorded | Owner direction or project event | Consequence / current disposition |
|---|---|---|
| Project start through 2026-07-12 | Enumerate every comparison capability, split the audit into reviewable chunks, audit adversarially, and prefer factual perfection over compatibility with old behavior. | Capability census and phased remediation plan created; every issue keeps a stable finding ID and a red reproduction before correction. |
| Project start through 2026-07-12 | Continue through the phases and document all issues so they can be corrected after verification. | Phases 1-3 completed; Phase 4 inventory contains 49 detailed red-fixture rows. Findings, canaries, and phase gates are linked at the top of this file. |
| Project start through 2026-07-12 | Read `CLAUDE.md` and relevant Claude documentation; solicit and independently verify second opinions from Claude and Fable 5 before implementation. | Both second-opinion records are retained in `docs/planning/comparison-perfection/`; adopted claims were independently checked and corrections are recorded in the remediation plan. Advisory model output is never treated as an oracle. |
| 2026-07-12 | Use the broad development corpus under `C:\Users\Yunus\Downloads\TSMIS`, including report sets from multiple days and TSN files; ask if a required comparison example is genuinely absent. | Corpus is local-only audit evidence. Historical outputs are references, not truth; exact raw inputs and report dates must be bound before use. No missing-example assumption is permitted. |
| 2026-07-12 | Treat `C:\Users\Yunus\Downloads\TSMIS\tsn_library` as deliberately plain raw TSN input. The owner removed generated `consolidated/` folders so app-produced derivatives cannot contaminate the source. | All seven production builders are being run into isolated audit storage. Raw selectors exclude placeholders, lock files, and generated folders. |
| 2026-07-12 | TSN inputs are set in stone and vs-TSN comparisons are the primary comparisons. Reconsider the overall audit because the raw TSN library should have anchored it from the outset. | Phase-4 family edits were paused and the sequence reset to raw-source binding, isolated normalization, conservation oracles, comparison oracles, then evidence. |
| 2026-07-12 | Highway Detail TSN remains authoritative, but the TSMIS Highway Detail report is the one vendor-pending report and may change. | TSN is checked normally; TSMIS HD layouts are version-pinned and fail closed on drift. Provisional TSMIS HD behavior cannot weaken other family contracts. |
| 2026-07-12 | Audit every TSN representation, whether XLSX or PDF. Where TSN XLSX is comparison truth and TSN PDF supports evidence, prove that both represent the same facts. Evidence should find no unexplained discrepancy between the normalized sources, Comparison sheet, and both report PDFs. | The acceptance chain now explicitly spans raw source, normalization, comparison, both PDF renderings, and evidence. Ramp Detail, Intersection Detail, and Highway Detail require XLSX-to-TSN-PDF parity; all five evidence families require end-to-end reconciliation. |
| 2026-07-12 | TSN Excel and PDF variants may contain minor source-date differences when IT exported them at different times, but they should represent essentially the same data. Use the pair to establish which Excel row belongs to which PDF category/section, including non-obvious mappings, and use that mapping to verify complicated layered Report View sheets. | Cross-format acceptance is semantic and source-dated, not byte-identity. Every row/category/section mapping must be explicit; every residue must be classified as a documented render equivalence, an exact dated export delta, or an unresolved discrepancy. Only the last category blocks acceptance, and no category may be silently normalized away. The mapping drives normalization, Comparison, evidence location, and Report View hierarchy/counts. |
| 2026-07-12 | When TSMIS validation begins, audit both Excel and PDF editions wherever the site provides them, including the Ramp Summary Excel sibling and Intersection Summary PDF. Also use older retained reports when available. | Each same-pull Excel/PDF pair must form an independently reconciled triangle against the same TSN truth before comparison/evidence acceptance. Older 6.19/7.7/7.8/7.9 editions are exact versioned regression/drift fixtures: they may prove supported compatibility or required fail-closed behavior, but never override newer source facts or get mixed across dates without explicit provenance. |
| 2026-07-12 | Keep documenting owner instructions and implementation/audit progress for the entire comparison-perfection project. | This log and the progress sections below are mandatory phase-transition artifacts. Detailed bugs remain in the finding ledger and exact hashes/counts in the canary ledger. |
| 2026-07-12 | Resume after the PC restart without assuming interrupted work was complete. | Highway Sequence was rebuilt/reviewed from the persisted source state, audit-gate findings CMP-AUD-160 through 166 were recorded before correction, and two final full-corpus replays produced identical accepted hashes. Stage 6 is now 6/7; Highway Log is next. |
| 2026-07-12 | Continue Highway Log from the persisted checkpoint after the usage-limit reset; re-verify rather than assume the interrupted candidate was final. | CMP-AUD-179 through 182 were hardened into terminal totals/module/collision/dataset/document contracts, the permanent family and shared-reader gates passed, and fresh 822-second/823-second runs produced byte-identical accepted result and acceptance files. CMP-AUD-167 through 182 are resolved audit-gate findings; CMP-AUD-045/157 remain product-red. Stage 6 is 7/7 complete and Stage 8 is active. |
| 2026-07-12 | Resume Stage 8 after the usage limit reset; do not assume the interrupted Ramp Summary oracle was complete. | Revalidated all partial code and all four TSMIS audit copies against the authoritative Downloads trees (504/504 files, zero byte differences). The permanent gate caught and corrected four audit-harness overconstraints without weakening source truth: undocumented prior tree-manifest serialization, legitimate per-file PDF generation metadata, excluded Excel `core.xml` volatility, and signed-delta direction. The final Ramp Summary result/acceptance passed two complete byte-identical source-bound replays. Stage 8 is 1/7 accepted. |
| 2026-07-12 | Continue after the usage limit reset and re-check any interrupted state rather than assuming completion. | Intersection Summary was replayed directly from the authoritative Downloads sources twice, with identical result/acceptance bytes. Its independent Excel/PDF/TSN/TSNR oracle, isolated production witness, permanent mutation gate, 10 product-red findings, and detached publication binding are all verified. Stage 8 is 2/7 accepted; no product correction has begun. |
| 2026-07-12 | Resume the interrupted Ramp Detail deterministic replay after the usage limit reset and continue through the phases. | The second complete five-leg production/oracle replay finished in 818 seconds and reproduced the 1,703,996-byte result SHA-256 `6cdf3ad5f5c1453df77515ca4cc30535f263bbe36eeaf2ab1e392771adbaf556` and 13,473-byte acceptance SHA-256 `77b3af5f5273666296c6304f28eb69137b69f67779d95cd3ca34e4ab6d3bbd64` exactly. Independent filesystem checks found no private-work entries and preserved the protected Fable document hash. CMP-AUD-185 was recorded before correction; Stage 8 is 3/7 accepted and Intersection Detail is next. |
| 2026-07-13 | Resume after the usage reset and network interruption; do not assume the long Intersection Detail replay finished. | The original execution cell was gone and no audit Python process remained, so completion was re-established from disk rather than inferred. Replay 2 had atomically published a valid acceptance record before disconnection. Its 1,059,072-byte result is byte-identical to replay 1 at SHA-256 `7c7734aae212fbf9ad55de554cd2a0111549479b764ff3b91695fb524f21d86c`; both 2,063-byte acceptance records are identical except for their bound result path and both pass all post-write source/origin/dependency/code/artifact checks. Stage 8 is 4/7 accepted; Highway Detail is next. |
| 2026-07-13 | Resume Highway Detail after the network interruption; verify the frozen current TSMIS Excel/PDF sources independently and do not let the product PDF parser define the oracle. | Re-established all exact source/dependency manifests, rendered the current route-005 source, and began an audit-owned word/topology parser. The first complete route probe accounts for 3,125 Excel rows, 3,070 PDF rows, 282 DCR headers, and zero unclassified PDF groups. It also upgrades CMP-AUD-054 from a synthetic exposure to a live current-corpus defect: production applies a document-median line-one grid to a continuation page whose exact local grid is relationally available, shifting the visible `005.009` record across columns while reporting a complete parse. Statewide Highway Detail remains active, not accepted. |
| 2026-07-13 | Continue after the next network/usage interruption and re-run any incomplete Highway Detail work rather than assuming it finished. | Corrected only the independent oracle after first documenting CMP-AUD-186. Route 395 now reconstructs 1,192/1,192 rows with every 34-cell row exact and one proven three-fragment line two. Six parser hard-case regressions stayed green. A fresh four-worker run rebuilt all 252+252 current TSMIS members to 51,273 Excel / 51,216 PDF rows with zero unclassified groups; 50,776 pairs reconcile and only routes 005/005S carry source-format deltas. The TSMIS Excel package was then searched beyond the visible table and still supplies no authoritative County claim. Stage 8 remains 4/7 accepted until the TSN, product, and publication layers close. |
| 2026-07-13 | Resume after the network interruption and preserve only work that can be independently revalidated. | The source comparison now covers raw/normalized TSN plus current TSMIS PDF and the only Excel rows whose County is attested by an exact uniquely owned companion-PDF signature. The first isolated production process exceeded its one-hour wrapper after committing both consolidations and the raw-TSN twin. The process was gone and the normalized outputs were only temporary, so they were rejected. The raw twin was retained only after its two canonical workbooks, two outcome sidecars, generation manifest, member hashes, compressed payload, decoded hash, and structured counts all agreed. The audit witness now checkpoints each committed leg and is rerunning only the incomplete normalized leg; Stage 8 remains 4/7 accepted. |
| 2026-07-13 | Keep launcher mistakes and partial artifacts from being mistaken for comparison evidence. | The resumed normalized leg completed and was promoted only after both canonical twins and sidecars agreed. A later PDF-leg launch mistyped the private-capture UUID and failed before importing or running product code; it changed no comparison artifact and is retained only as a launcher incident until the final helper removes the failure marker. The corrected exact path launched PDF-vs-raw. Final acceptance rejects every temporary, partial-result, or failure artifact in the witness root. |
| 2026-07-13 | Resume after the next network interruption from independently verifiable disk state; authenticate the comparison publications themselves, not merely their returned counts. | Three Highway Detail legs were fully committed and the fourth, PDF-vs-normalized, was still executing with only producer-temporary placeholders, so no completion was assumed. The Stage-8 driver now independently binds both sidecars to both workbook bytes and mtimes, recomputes the shared generation binding, validates the exact sidecar/chunk artifact universe, inflates and hashes every canonical payload, and requires the persisted duplicate-pairing trace and counts to equal the audit-owned oracle. The first committed leg passed this new reader and also confirmed zero persisted source identities, additional current-corpus evidence for CMP-AUD-076. Highway Detail remains 4/7 Stage-8 families accepted until all five legs, the detached decision, and a byte-identical replay close. |
| 2026-07-13 | Treat missing TSMIS Excel County as an epistemic gap, not permission to borrow identity from authoritative TSN; include older editions without mixing snapshots. | Added a second owner-constraint ledger for all 51,273 current Excel rows. Exact uniquely owned companion signatures remain primary; a residue row may be separately constrained only when every current companion-PDF record at its observable Route/PP/numeric-PM/roadbed key has one printed owner. TSN-only candidates are recorded but never promoted, with permanent mutations enforcing that non-circular boundary. Corpus discovery also confirmed a complete, separate `Hwy Detail Dev Bundle 7.7` with TSMIS Excel/PDF and TSN Excel/PDF. It will be identity-bound as a historical replay after the current 7.9 base closes; identical historical signatures may corroborate but never overwrite current source claims. |
| 2026-07-13 | Continue through the phases after the status checkpoint; accept Highway Detail only after full reproducibility and preserve source-snapshot conflicts. | The exact 7.7 route-005 Excel/PDF pair and current 005S composite print mapping close all 51,273 Excel owner claims without borrowing TSN identity; the later route-005 PDF remains a separate snapshot with eight frozen owner conflicts. The 79-assertion permanent gate passes. Two 2,878/2,858-second source-bound runs produced byte-identical 3,384,044-byte results at SHA-256 `9d793fb166197701e20d8ac6bc8aa34bd64221a15507dff5bbe7416bc7095554`; both detached acceptances pass 34/34 invariants and differ only in their bound result path. CMP-AUD-188 through 191 are accepted audit-harness remediations; CMP-AUD-192 remains a verified source-export delta. Stage 8 is 5/7 accepted and Highway Sequence is active. |
| 2026-07-13 | Start Highway Sequence from the freshest same-run pair and keep older HSL editions separate. | Selected the July 9 SSOR-production 252-Excel/252-PDF pair plus the clean 12-district TSN PDF library. The old/current census found four changed Excel members and zero changed PDFs. July-9 Excel adds six Descriptions and one row across routes 002/010/037/101; visual inspection proves only route-037 `003.809` is printed, so that old cross-bundle defect is fixed while four current paired PDF Description omissions plus one Excel-only described row remain. CMP-AUD-193 was expanded before correction; the old 7.8-Excel/7.9-PDF canary remains historical and cannot define current parity. Full statewide equate/parity and product truth remain in progress. |
| 2026-07-13 | Establish current Highway Sequence source parity before letting product comparison semantics define it. | Captured 1,008 TSMIS members plus 12 TSN PDFs immutably; independent fixed-grid PDF and positional Excel readers close 60,494/60,493 rows with zero unclassified lines. Exact duplicate assignment is positional in all 4,030 same-source duplicate groups. The 1,129 equate events split into 852 same-convention, 272 suffix-move, and five PDF-only-suffix cases; the old glued-suffix key is now source-proven wrong for PDF↔Excel at route 152 (CMP-AUD-199). Installed Excel proves four `_x000d_` values are CRLF, exposing CMP-AUD-197. A clean 392-second product run produced complete 252/252 consolidations whose 120,987 rows are cell-for-cell exact against the independent source. Audit-harness defects CMP-AUD-194/195/196/198/200/201 were recorded before correction. Raw-vs-normalized TSN and comparison identity ledgers are active; Stage 8 remains 5/7 accepted. |
| 2026-07-13 | Run all three current Highway Sequence product comparison placements without treating wrapper termination as a product result. | The first comparison witness atomically committed the Excel-vs-normalized-TSN formula/value twins and both outcome sidecars, then its shared 600-second wrapper terminated during temporary PDF-vs-normalized-TSN output creation before a terminal result or any PDF-vs-Excel attempt. CMP-AUD-202 was documented before correction. The partial r1 root is preserved and cannot be accepted as a three-leg witness; each leg will now run in a separate clean source-bound process with its own runtime budget. Stage 8 remains 5/7 accepted. |
| 2026-07-13 | Make the per-leg completion gate distinguish unfinished artifacts from the product's deliberate publication infrastructure. | Source inspection proves `.tsmis-comparison-publication.lock` is an intentionally permanent, zero-byte transaction lease anchor. CMP-AUD-203 was documented before correction. The clean-leg gate will inventory that exact code-backed lease while rejecting every other lock, temp/staging file, sentinel, unknown artifact, or missing committed twin. |
| 2026-07-13 | Adversarially test Highway Sequence Description normalization on both authoritative TSN forms rather than assuming a TSMIS display rule is symmetric. | Raw and normalized TSN each preserve the same 154 numeric-prefix Descriptions, but product loading changes all 154 and false-cleans 81 current differences across Excel/PDF × raw/normalized TSN (CMP-AUD-204). Independent reconciliation also found three TSMIS `route/ text` rows where the non-acceptance draft leaves separator padding after its approved outer-label removal (CMP-AUD-205); those three cannot inflate final oracle totals. |
| 2026-07-13 | Correct only the audit-side delimiter-padding projection after recording CMP-AUD-205. | The corrected 113,580,556-byte non-acceptance comparison draft preserves every pairing/one-sided count while reducing current asserted Description truth by exactly three rows per leg. Excel-vs-raw/normalized now has 4,894 Description differences and PDF-vs-raw/normalized 4,916; the 81 authoritative-TSN prefix losses remain product-red under CMP-AUD-204. Final acceptance will reparse immutable sources rather than promote this cache-backed draft. |
| 2026-07-13 | Authenticate all three current Highway Sequence product comparison publications after splitting the failed monolithic run. | Three clean per-leg witnesses completed in parallel in 365–409 seconds. An independent 482-second reader reconstructed all six workbooks, source snapshots, formula/value twins, one-sided inventories, sidecars, compressed payloads, and exact duplicate traces. Product counts are Excel→TSN 57,072 / 3,422 / 12,686 with 5,517 cells; PDF→TSN 57,505 / 2,988 / 12,253 with 4,930; PDF→Excel 59,946 / 547 / 548 with 1,725. The 42,381-byte parity artifact SHA `bb7c8550724b71e657781f86579e25b2f70c96bf8bf3380d049f70118f98961f` deliberately says `pass_with_expected_product_defect` because source-semantic PDF→Excel truth is 60,493 / 0 / 1 (CMP-AUD-199). Stage 8 remains 5/7 accepted pending raw-TSN twin/final gate/replay. |
| 2026-07-13 | Turn the CMP-AUD-204/205 Description-normalization census into replayable evidence. | A source-bound development probe reproduces the 154 TSN prefix rows, 46 cross-route prefixes, two nested remnants, two collapsed duplicate identities, three audit-only delimiter-padding rows, and exactly 81 product false-cleans on all four current raw/normalized legs. Three runs are byte-identical at 174,929 bytes / SHA `202fcb82b6ba62d15fcd273b19f4f35de672d06da39fd710982ba65350e8bdd1`. It remains explicitly non-acceptance because it consumes frozen development caches; final Highway Sequence acceptance must reparse immutable raw sources. |
| 2026-07-13 | Build a product-consumable raw-TSN audit twin without letting optional XLSX metadata define completeness. | The first write-only workbook was produced, but its verifier required optional worksheet dimensions and stopped when openpyxl correctly reported them as absent. CMP-AUD-206 was documented before correction. The workbook-only root is preserved as failed/non-result evidence; a clean rebuild must stream and exactly close one header plus all 69,804 records, its provenance sidecar, and the Stage-6 bindings. |
| 2026-07-13 | Review final Highway Sequence promotion code for historical-edition role leakage. | The non-acceptance draft applies TSMIS-side duplicate costs only when a source name begins `current_tsmis`, so historical 7.8 Excel is costed as TSN. CMP-AUD-207 was documented before correction. Frozen counts/pairs happen to stay unchanged, but the cost/trace is not promotable; final code must use an explicit typed side role and remain invariant under dataset renaming. |
| 2026-07-13 | Correct CMP-AUD-207 with typed source role and re-run every current/historical development leg. | Historical raw and normalized assignment costs/traces now use `kind=tsmis`; both historical pair maps and every current/historical count remain unchanged. The latest 113,580,300-byte non-acceptance comparison draft SHA is `4198f7e4a65a4afbe164e738defaf36ec0270efc328f0e46d400937c7b9efb1c`. Final raw-source code must independently enforce the same rename-invariant role contract. |
| 2026-07-13 | Rebuild the raw-TSN development twin with streaming extent verification after CMP-AUD-206. | Clean r2 closes one header plus all 69,804 raw records, including 46 blank-County equates, 283 `*P*` and 282 `-------->` pointer tokens, and the sole punctuation delta. The 2,541,734-byte XLSX SHA is `d594e2441b81c4d4d81c11aa5bbf01418bcd2dcc0bedf3ee9a6221a66cb03fa1`; its 23,610,997-byte provenance sidecar and terminal result are bound. It remains development-only until the final oracle reparses the 12 immutable TSN PDFs directly. |
| 2026-07-13 | Audit Highway Sequence evidence as an independent raw-to-Comparison verifier rather than a screenshot sampler. | CMP-AUD-208 through 210 are new P1s. Evidence never opens either published Comparison twin, drops duplicate/key/context/one-sided classes before sampling, and has no Excel-faithful or PDF↔Excel mode. It exposes only 4,358 of 5,517 Excel→TSN and 3,938 of 4,930 PDF→TSN counted cells before sampling, plus none of 31,349 combined one-sided rows. Stage 10 must bind an exhaustive locator ledger to exact workbook cells and both source roles before imagery can be accepted. |
| 2026-07-13 | Harden the raw-twin product witness before launching either expensive comparison leg. | CMP-AUD-211/212 were documented before correction: the first decoder could hash and later decompress different bytes, and the inherited residue gate admitted well-named orphan payload chunks. The corrected per-leg runner performs identity-bound sidecar/chunk reads and requires exact equality between referenced, decoded, inventoried, and final chunk/file sets. |
| 2026-07-14 | Independently reconstruct both Highway Sequence raw-TSN product publications before trusting the development witness. | The 36,706-byte audit artifact at SHA-256 `8b59cb5062be9e3345b68b7d7024436275dd5de8ee9cb0d20bb90a7d4b0e0abd` passes all 15 invariants. It authenticates both formula/value twins, all six bound inputs per leg, 69,804 raw TSN rows with 46 blank-County equates and 565 pointer tokens, every provenance row, embedded sources, Comparison/one-sided/Routes sheets, pairing traces, sidecars/chunks, and exact artifact trees. It remains explicitly non-acceptance and `pass_with_product_defects`: final promotion must build the raw twin directly from the immutable TSN PDFs and replay the complete gate twice. Stage 8 remains 5/7 accepted. |
| 2026-07-14 | Review the first direct-source Highway Sequence core while it is still non-acceptance. | CMP-AUD-215 through 217 were documented before correction: several proposed mutation probes do not rerun the predicates they claim to harden; the raw legs label the 69,758 keyable subset as authoritative raw TSN without exposing the complete 69,804-row publication shape; and the TSMIS capture is hashed before path-based parsers reopen it, so parsed bytes are not identity-bound to the manifest. The first checkpoint cannot be promoted. Its replacement must preserve all 46 unknown-County equates, exercise real mutation failures, and parse the exact member bytes whose digests are recorded. |
| 2026-07-14 | Trace Highway Sequence Spot Check from its reviewer claim back to every precedent. | CMP-AUD-218 was documented before product correction. Spot Check recomputes field equality from the source sheets, but it takes status and both source-row numbers from Comparison and derives one-sided membership from those same links. A consistently wrong duplicate pair or one-sided status can therefore agree with itself and show `OK`. Final evidence/flat-view acceptance must independently derive identity, occurrence, membership, and source rows and must reject planted wrong-pair and wrong-membership workbooks. |
| 2026-07-14 | Audit edition provenance while replacing Highway Sequence path-based parsing with exact captured-byte parsing. | CMP-AUD-219 was documented before correction: the shared PDF member parser hardcodes `current_tsmis_pdf` into rows from both the current and historical PDF trees. Counts are unchanged only because downstream code supplies another dataset label; row-level provenance and digests are still false. The direct-byte replacement must pass a typed edition role through every worker row/diagnostic and reject a role-swap mutation. |
| 2026-07-14 | Reconcile every Highway Sequence product residual instead of stopping at aggregate count disagreement. | A 2,475,505-byte non-acceptance classifier at SHA-256 `ebe0f9efb6025525024d7183211e52f5cf4a10fba1dc9bfcbe02513ce38cb45b` replayed byte-identically. Its exact persisted maps and aggregate arithmetic expand CMP-AUD-204 to 81 false-cleans plus 15 false-positive Description states per leg and measure 90 mutated TSMIS cross-route prefixes per form. CMP-AUD-220 records 445/448 Excel and 357/360 PDF duplicate-group assignment changes. Independent review then documented CMP-AUD-221 through 223: the assignment zero-unexplained claim is tautological, symlink guards dereference before testing, and an aliased output can overwrite a frozen input after the final guard. The artifact stays non-acceptance until those lifecycle/classification gates are hardened. |
| 2026-07-14 | Replay the corrected Highway Sequence source core only after closing the four adversarial review findings. | The clean r2 run took 344.986 seconds and published a 98,943,666-byte checkpoint at SHA-256 `a8da9a24a50bf2b1ba58a8062566c1813a6518d9bede9d6fc2dec24d7fa657ce`; the bound 112,009-byte source-core script SHA is `469c57d9b419b6bfbe6b0ee7a1e7171f896e3585af47cc392c00ebb2383d9dd2`. A detached read confirms all 1,008 TSMIS members were parsed from the exact bytes whose digests are recorded, both 69,758-keyable and 69,804-complete raw contracts are explicit, all 46 unkeyed equates share the exact bound ledger, historical roles are truthful, nine real mutations are rejected, and zero source residue is unexplained. The artifact remains `acceptance_eligible=false`; product publication, exhaustive evidence, permanent gate, detached decision, and two full replays remain. Stage 8 is still 5/7. |
| 2026-07-14 | Subject the cache-backed residual classifier to an independent adversarial second review before promotion. | The authentic four-leg persisted maps, counts, and projection/assignment arithmetic all reconstruct, and a separate 197-second replay is byte-identical at 2,475,505 bytes / SHA `ebe0f9efb6025525024d7183211e52f5cf4a10fba1dc9bfcbe02513ce38cb45b`. Promotion is nevertheless blocked by newly documented CMP-AUD-221 through 223: an arbitrary duplicate pair swap is falsely classified as caused, link guards test only after dereference, and unrestricted `--output` can replace a frozen input after validation. No destructive alias reproduction was run. |
| 2026-07-14 | Independently second-review every direct-source r2 Highway Sequence contract before using it in a final gate. | All 1,028 bound files / 135,692,439 bytes rehash exactly; every current/historical leg equation, pair/cell ledger, assignment cost, role, 46-row unknown-County ledger, and all nine real mutation rejections reconstruct. No source-core contradiction was found. CMP-AUD-224 records one final-gate hardening gap: annotation-to-`E` topology is checked only forward. Current raw truth is already 998 annotations / 998 data-`E` rows / zero orphan `E` rows; the direct raw twin/permanent gate must bind the reverse ledger and reject an added orphan-`E` mutation. |
| 2026-07-14 | Review output containment before adapting the one-leg product witness to the direct raw-TSN twin. | CMP-AUD-225 was documented before correction. The shared clean-root helper accepts any absent descendant of the private visual root, including a child of a bound source/twin artifact root. Such a run leaves every bound input file hash unchanged while contaminating the input tree. The direct-source runner must enforce two-way root disjointness, freeze input tree universes, and reject child/parent/alias placements before either raw leg is launched. |
| 2026-07-14 | Harden and independently replay the residual classifier after documenting CMP-AUD-221 through 223. | The 95,630-byte classifier now proves both assignment objectives for all 445/448 Excel and 357/360 PDF changed groups, sends arbitrary swaps to a terminal unexplained ledger, rejects real Windows file/directory symlinks, rejects hardlink/lexical output aliases, and blocks an actual bound-input output path before reading or writing. Two independent full runs are byte-identical at 3,509,121 bytes / SHA-256 `f6fa06569b28cdba66d059e6e9c9f40b4464149754a2561075b02c6c0307c8cc`; zero unexplained residue remains. The artifact is still cache-backed non-acceptance evidence and cannot replace the direct raw-source replay. |
| 2026-07-14 | Adversarially review direct raw-twin determinism before trusting the first full parse. | CMP-AUD-226 was documented before correction. Although the draft fixes ZIP member order/timestamps/metadata, openpyxl overwrites `docProps/core.xml`'s modified time at save. Two same-input in-memory packages 1.2 seconds apart had different hashes solely at that timestamp. The in-progress r1 is diagnostic; the corrected builder must normalize/validate the core XML and reproduce two delayed in-memory plus two full 69,804-row builds byte-for-byte. CMP-AUD-225 was also expanded to require the builder output root to be disjoint from accepted Stage-6/normalized artifact trees. |
| 2026-07-14 | Review direct raw/static source path claims before accepting the exact-byte capture. | CMP-AUD-227 was documented before correction. The draft rejects a final file symlink but does not test Windows reparse attributes or redirected parent components; resolving both aliases of the same configured raw path is not an independent origin proof. Exact captured bytes remain valid evidence, but the corrected builder must reject real disposable file and directory-component redirections before calling its inputs ordinary/direct. |
| 2026-07-14 | Close the Summary/Spot Check semantic-audit gap across the complete five-leg Highway Sequence surface. | The 80,667-byte independent checker captures and inspects the same exact workbook bytes, reconstructs every Comparison formula/value cell plus exhaustive Summary/Spot maps, and passes all 13 invariants. Its 35,937-byte non-acceptance result SHA is `331d4aba8321cb8e61080678f5b71357f3da249cdf02f5ad23b18ae01b9f7395`. CMP-AUD-214 is present in all 10 workbooks. CMP-AUD-218 is mutation-proved everywhere: both a cross-identity wrong row link and a false one-sided link/status still produce six `OK`s. No third Summary/Spot defect was found; direct-PDF replay and product correction remain pending. |
| 2026-07-14 | Close the final direct-source raw-TSN audit-input twin without confusing an input fixture with family acceptance. | Builder SHA-256 `86d271619f4e446590fe6edaa40e9e85d74da2ca9623f9a5bfcf7877c7101ea5` produced byte-identical r6/r7 roots from the exact 12 TSN PDFs. Each binds 69,804 rows, bidirectional 998/998 equate topology, fixed XLSX core/ZIP metadata, a pre-resolve real reparse mutation, and two-way output containment. Workbook SHA-256 is `68b28921c4ca8290810c92653b4a96077d6a28bdb7954447c287cf3e78d3f67d`; result SHA-256 is `d4c0a5759b0ca9731047b0f7d57fabedb228f7a61697f0c6af3cb4ef8fc4d134`. CMP-AUD-224/226/227 are remediated for the builder and CMP-AUD-225's builder half is remediated; its one-leg runner half remains pending. The result is explicitly non-acceptance, so product comparison/evidence, the permanent gate, detached decision, and final replay remain; Stage 8 stays 5/7. |
| 2026-07-14 | Hold the direct raw-product launch until its runner proves genuinely non-following artifact capture. | CMP-AUD-228 was documented before runner correction. The first component walk used follow-semantic path predicates before `lstat`, and final chunk revalidation resolves the supplied path before capture, erasing the alias it claims to reject. Generic link probes do not prove that final call path. The correction must use direct lexical `lstat`, retain flat-name/output-root containment, and reject a planted final chunk symlink/reparse before reading its target. No product leg has been blessed. |
| 2026-07-14 | Extend the direct-runner prelaunch review through truthful terminal publication and exact v1 contracts. | CMP-AUD-229 through 231 were documented before correction. The runner writes a durable terminal PASS before fallible post-result checks, final success rehashes only payload chunks instead of every workbook/sidecar/manifest/result artifact, and its direct-v1 result/manifest/provenance validators accept extra top-level fields. The runner launch and Stage 8 promotion remain held until lifecycle, full-universe mutation, exact-key, and complete replay evidence is green. |
| 2026-07-14 | Bind the audit code that produces each direct raw-product witness, not only its product modules and source builder. | CMP-AUD-232 was documented before correction. The runner does not capture its own bytes, and the two imported `build/` validation/decoding helpers fall outside the scripts-only loaded product manifest. The corrected witness must bind and revalidate the exact four-file audit-code set (runner, both helpers, direct builder), carry its path-neutral identity ledger in the preterminal result and detached completion, and reject runner/helper replacement or mid-run drift. Direct-leg launch and final-family promotion remain held pending replay. |
| 2026-07-14 | Prove every final direct-runner artifact is a new physical object, not merely a path inside a disjoint root. | CMP-AUD-233 was documented before correction. Final workbook/chunk/sidecar/manifest/lease capture checks ordinary type, name, length, and SHA but not `st_nlink` or `samefile` against all bound inputs. A hardlinked member can therefore retain perfect bytes while remaining a live source alias. The corrected runner must enforce member-level physical distinctness throughout precompletion/staging/commit and reject a real final-artifact hardlink mutation before publishing terminal completion. Launch remains held. |
| 2026-07-14 | Authenticate the exact semantic completion contract at the detached publisher's final commit boundary. | CMP-AUD-234 was documented before correction. The publisher proves staging/identity/rename mechanics but accepts a minimally shaped arbitrary payload, so a hostile terminal/acceptance claim, wrong leg, fabricated audit-code ledger, unbound preterminal result, or inconsistent final manifest can still commit. The corrected runner must apply one exact `completion-v1` validator before staging, mutate every semantic field class (including each of the four audit-code roles), and preserve no terminal residue on rejection. CMP-AUD-230 mutations must target the real workbook and sidecar filenames. Launch remains held pending a fresh independent replay. |
| 2026-07-14 | Reject claimed semantic-mutation evidence unless the runner actually executes and observes every failure. | The first CMP-AUD-234 corrective draft pre-populated its mutation-label census and no-terminal claim without running the semantic publisher mutations. It was caught before any direct-leg output existed. The frozen candidate now executes 12 per-class mutations, derives the census from caught failures, verifies no completion or pending residue after each, and computes the aggregate from observed controls. Independent static controls and the full read-only r7 preflight are green; launch remains held for independent final code review. |
| 2026-07-14 | Treat a green runner preflight as necessary but not sufficient; independently review the frozen publisher hash before launch. | Independent review rejected the 183,748-byte SHA `507237e47dcd2d043fdb3320ed6db18a3926e136ffd2c014b39e1df667703643` despite its green static suite and 29-file/five-tree r7 preflight. Audit-code paths still resolve before their lexical capture, the candidate ledger is not bound to the physical four-file manifest at the publisher, the expected leg is not externally bound, and several completion-v1 semantic branches have no executed mutation. These stay within CMP-AUD-228/232/234. No direct comparison leg or output root was launched; correction and another independent frozen-hash review are required. |
| 2026-07-14 | Investigate repeated frozen-tree failures instead of rerunning until one happens to pass. | CMP-AUD-235 was documented before correction. Three clean final-runner preflights failed on different first-touched directories. An instrumented traversal proved Windows changed only lazy directory `st_size` from 0 to 4096; all retained identity/time/link/attribute fields, all 15 member names, and all 20,967,716 file bytes remained exact. The runner must separate file and directory tokens, exclude only directory size, mutation-test every retained field/member class, and pass a fresh full r7 preflight before launch. |
| 2026-07-14 | Stop recursive audit-harness expansion and finish the bounded comparison sequence. | Owner selected the lock-in path. From this checkpoint, new harness work is authorized only when an active run exposes a concrete source-byte, normalized-row, comparison-cell, or publication-integrity failure. The execution sequence is fixed: finish the two running Highway Sequence direct legs, bind and replay the final gate twice, close Highway Sequence, then move directly to Highway Log. |
| 2026-07-14 | Close Highway Sequence and stop before product remediation. | Both direct raw-TSN legs completed once with exact terminal 10-file universes and no residue. The final gate corrected only its producer-compatible aggregate serialization rule, then two clean process roots produced byte-identical 42,140-byte results (`f7f60e52...`) and 1,510-byte acceptances (`7e2e9ce4...`). A detached verifier rehashed all 20 direct artifacts and both replay pairs. Highway Sequence is the sixth accepted Stage-8 base family. Its 14 known product/evidence findings remain explicitly red; no app comparison code was changed. Highway Log is the final Stage-8 family. |
| 2026-07-14 | Stop before making further product changes; another AI may implement the documented corrections. | Product code was frozen at a 321-file / 7,423,809-byte `scripts/` manifest SHA-256 `df7bb8fc3d997d60d82ecb93344f821e858feb015eed62fffe859958c9151bea`. The remaining authorized work is audit-only: finish the two already-running Highway Log legs, replay one bounded closeout gate twice, update the ledgers/handoff, reproduce that exact product-tree manifest, and stop. Existing dirty product edits are preserved rather than rewritten or reverted. |
| 2026-07-14 | Finish the bounded audit and stop before implementation. | Highway Log's accepted r2 Excel/PDF product-leg witnesses exactly match the independent oracle, including all 989 duplicate-assignment groups per leg. Two clean final-gate roots are byte-identical: result 9,036 bytes / SHA-256 `7acf9986055750bbc49be0d4fa422329d06893f379da0cd6ded945936549860b`; acceptance 839 bytes / SHA-256 `170d622d751e96e97c7f8420c0a60172e57a31838a3d1b3de090c76972dd62b6`. The gate accepts only the Stage-8 base audit and keeps product comparison, physical identity, and evidence perfection false. The r1 timeout/format-consumer attempts are preserved as rejected non-witnesses. Stage 8 is now 7/7 at the audit layer; Stages 9–12 and all product correction are handed off. The final post-documentation check reproduced the frozen 321-file product manifest exactly and preserved the protected Fable review hash. |
| 2026-07-14 | Put the comparison project in its own planning folder and prepare a new-AI reconciliation prompt. | Ten comparison-project records moved together into `docs/planning/comparison-perfection/`; the unrelated protected repository-wide Fable audit stayed in `docs/planning/`. The new prompt authorizes only read-only reconciliation plus one report, requires the next AI to decide whether Stage 9–10 audit work should finish before implementation, and explicitly prohibits recursive audit-harness expansion or product changes during that first pass. |

## Acceptance model

Every family must pass all applicable layers:

| Layer | Required proof | Failure rule |
|---|---|---|
| Raw source identity | Exact ordinary-member selector, lengths, SHA-256 manifest, internal report date/parameters, source role | Missing, mixed, wrong-role, or unbound members stop the family |
| Raw schema/completeness | Exact headers/layout, required fields, route/record universe, duplicate and anomaly census | Shape-only admission or unexplained data loss is non-complete |
| Normalization | Independent raw-to-normalized row/key/field conservation; exact normalizer version and producer outcome | Reordered/stale/partial/fabricated values cannot compare |
| Cross-format TSN parity | For XLSX-source families with TSN evidence prints, explicit Excel-row-to-PDF-record/category/section mapping plus source-date-aware record/field reconciliation | Byte identity is not assumed across different IT pull times; every delta must be a documented render equivalence, an exact dated export delta, or an unresolved discrepancy. Unresolved residue blocks acceptance and no delta is silently folded |
| TSMIS representation | Same-pull Excel/PDF route, row, field, and producer-completeness parity for every available edition, plus version-pinned older-report compatibility/drift tests | Silent parse loss, cross-date mixing, provenance conflict, unsupported schema drift, or wrong-role input blocks truth |
| Comparison | Independent key/pair/equality/count oracle; formulas and values peers; exact per-cell/per-field truth | Historical counts never override the source facts |
| Evidence | Every selected difference maps to the correct records/cells/categories/sections in both PDFs and reproduces the Comparison value/label and layered Report View placement | Wrong route, wrong field, wrong category/section, wrong value, missing record, stale generation, or unexplained residue fails |

The evidence-capable families are Highway Log, Highway Sequence, Ramp Detail,
Intersection Detail, and Highway Detail. Highway Log/Sequence normalize directly from TSN
district PDFs. Ramp/Intersection/Highway Detail use authoritative TSN XLSX plus optional
TSN print PDFs for evidence; those evidence prints never replace the XLSX comparison truth.

## Source roles currently established

| Dataset | Authoritative TSN comparison input | TSN evidence input | TSMIS comparison/evidence forms |
|---|---|---|---|
| Highway Log | 12 district PDFs | same 12 district PDFs | TSMIS Excel and PDF |
| Highway Sequence | 12 district PDFs | same 12 district PDFs | TSMIS Excel and PDF |
| Ramp Detail | one statewide XLSX | statewide/district print PDF set in `pdf/` | TSMIS Excel and PDF |
| Ramp Summary | one statewide PDF | no visual-evidence family | TSMIS PDF base comparison plus Excel sibling cross-format proof |
| Intersection Summary | one statewide PDF | no visual-evidence family | TSMIS Excel base comparison plus PDF sibling cross-format proof |
| Intersection Detail | one statewide XLSX | statewide/district print PDF set in `pdf/` | TSMIS Excel and PDF |
| Highway Detail | one statewide XLSX | 12 district PDFs in `pdf/` | provisional TSMIS Excel and PDF |

### Bound TSMIS corpus selected for Stages 8–10

The primary current TSMIS corpus is the fresh `ground-truth/All Reports 7.9/` production
set plus its later Ramp Summary Excel supplement. SSOR-prod owns the complete both-format
Ramp Summary, Ramp Detail, Highway Sequence, and Highway Log pairs; ARS-prod owns the
complete both-format Intersection Summary, Intersection Detail, and Highway Detail pairs.
All seven families have exact route-token parity between Excel and PDF, including S/U
suffixes. The archive/supplement hashes and per-family counts/bytes are recorded in
`comparison-canary-bindings.md`.

These are same-day/source/environment family pairs, but timestamps show whole-format
sequential exports rather than one coalesced query per route. Acceptance may call them
same-pull only at the dated bundle level and must retain that timing fact. Generated
consolidations/sidecars inside the archive, comparison/evidence outputs, samples, and
scratch subsets are excluded from raw TSMIS truth.

Older 6.19, HD 7.7, HSL/ID 7.8, and duplicate 7.9 bundles remain versioned regression/
drift witnesses. The 7.9 Intersection universe is consistently 217 routes and omits
Route 170 relative to 6.19's 218; that is a dated universe fact, not an unexplained
single-format loss. No primary TSMIS Excel/PDF sibling is missing. A literally coalesced
same-query set or full source/environment parity would require new exports; raw TSN Excel
siblings do not exist in the supplied library for Ramp Summary, Highway Sequence,
Highway Log, or Intersection Summary and are not inferred from app-built XLSX files.

Placeholders/readme files are not source members. Generated `consolidated/` directories are
not permitted in the raw audit selector.

## Progress record

### Stage 6 independent raw-to-normalized conservation

- Ramp Detail corrected accepted result:
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\phase6_ramp_detail_conservation_r7_reissued.json`,
  64,727 bytes, SHA-256
  `3386ca24768c7182ad79069c80d2d4e103a192bb6af6a6c8b1bcba7c6c1ea1bd`.
  Detached acceptance: 5,941 bytes, SHA-256
  `2c346786f27eab3999f225e5821ddf7b08296faf006f5ab2738293a40ccca6cb`.
  Its exact raw/r7 bindings, schemas, 15,410-row order/multiset, per-field typed
  digests, identity/collision/order census, mutation probes, and final revalidation are
  complete. All 14 invariants and six mutation probes pass;
  `stage6_family_audit_complete=true`, `projection_exact=false`, and
  `normalized_full_conservation=false` truthfully preserve the three product findings.
- Ramp full physical identity is unique for all 15,410 rows. Weaker identity proves
  81 route+PM cross-county keys / 163 county identities and 46
  route+PR+PM+suffix keys / 93 county identities; `SEG_ORDER_ID` has no within-DCR
  decrease. The exact 15-row Description-loss manifest—nine same-route and six
  different-route prefixes—is acceptance-bound under CMP-AUD-135.
- Intersection Detail is independently accepted over all 16,626 rows: projection and
  audit are exact, all 24 invariants and 25 mutations pass, and detached acceptance
  binds the result/lifecycle/source/code identities. Full conservation remains correctly
  false because three authoritative traffic/reference fields are absent.
- Highway Detail is independently accepted over all 60,083 rows with zero unexplained
  residue, 23/23 invariants, and 22/22 probes. Projection and full conservation remain
  correctly false for the exact Length defect plus two source-claim omission classes.
  The accepted result/acceptance close CMP-AUD-141/CMP-AUD-143/CMP-AUD-147 without
  weakening CMP-AUD-133/CMP-AUD-138/CMP-AUD-142. The ID/HD exact schemas,
  dispositions, identities, and mutation requirements remain pinned in
  `build/phase6_id_hd_conservation_spec.md`.
- Ramp Summary is independently accepted: 30 comparison categories plus `Total`, four
  independent 15,410 section totals, zero unexplained residue, exact PDF-role coverage,
  and deterministic result/acceptance replay. CMP-AUD-152/CMP-AUD-153 close only its
  audit publication/coverage defects; CMP-AUD-146 remains product-red.
- Intersection Summary is independently accepted: 62 printed source categories have
  exactly one disposition and produce 58 normalized Category rows with complete
  per-category ordered/multiset/target/source typed digests, including Total. Exact
  comparison projection/full-source conservation remain separate: projection is green,
  while the six-to-one control fold, Control F label drift, and printed provenance loss
  remain red under CMP-AUD-144/CMP-AUD-145/CMP-AUD-146.

### Stage 8 base TSMIS-vs-TSN comparison truth

- Ramp Summary is accepted as the first of seven base comparison families. Accepted
  result:
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\ramp_summary_base_r1.json`,
  491,099 bytes, SHA-256
  `f05bad6e7442fd3f345f86c8b61f334f44bd6cbaced1341d4e24b277c2ef3ba2`.
  Detached acceptance is
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\ramp_summary_base_r1.json.acceptance.json`,
  11,568 bytes, SHA-256
  `46ff47b2c73675b321ac88fc872767ef8446d7d09c3a3d1a36923a23fee782ca`.
  Two complete raw-source replays reproduced both files byte-for-byte.
- The canonical TSMIS manifests are Summary PDF
  `81108f5bb35ecffa292fd206724c2ec87001c1d0c32db33f8281a78b24f8c444`,
  Summary Excel
  `d74c19b589108e0dcbd21389f63c1adcd4d9373c4959c168a1e4ba8446c6281e`,
  Detail Excel
  `7c10fbf6b996a8a9fbb0e8c8c30d8d2dac0a80c0befb7c12bdeb0151f7ff7489`,
  and Detail PDF
  `6e8a2b669148738344a0173cca52a16884b972cba4679ba6446547ce8286c4c9`.
  Each tree has 126 unique ordered route members; direct source/copy comparison found
  zero member differences across all 504 files.
- All 126 two-page Summary PDFs and 126 47-row Summary workbooks agree on 3,780/3,780
  typed values, ordered digest
  `57514b890de9d1e49ed605c0fa095fade6a264f821e8177ac19aa852d87c2f1b`.
  Both same-pull Detail forms contain exactly 15,216 rows and match every Summary route
  total. Their 22 P/V rows (P=2, V=20) exactly explain the nine-route printed Ramp-Type
  residual with no remainder.
- Independent comparison truth has 29 shared rows, P and V as two TSN-only Summary rows,
  zero TSMIS-only rows, five identical shared rows, and 24 differing shared rows. Its
  ordered digest (explicit `TSMIS - TSN` delta) is
  `a3cbf7528aa66989f08a0d28efd8ba0e4588b8e3675ef108b0b791fdd35a2d63`.
  TSMIS total is 15,216, TSN total is 15,410, and TSN minus TSMIS is 194.
- `source_truth_exact=true`, `production_value_projection_exact=true`, and
  `stage8_base_oracle_complete=true`. `production_comparison_semantics_exact=false` and
  `comparison_end_to_end_perfect=false` are intentional terminal facts, not audit
  failures: production returns 31 shared + one TSMIS-only row because it zero-fills P/V
  and compares the no-linework footnote. CMP-AUD-019/020/024/025/071/076/146 remain
  documented product-red; no production correction was made in this stage.
- Intersection Summary is accepted as the second of seven base comparison families.
  Accepted result:
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_tsmis_vs_tsn\intersection_summary_base_r1.json`,
  1,124,870 bytes, SHA-256
  `7e4acebabd2efc8ac2d765c78493048117eb0bd2431cd01d032c0272cd9ea7bd`.
  Detached acceptance is the same path plus `.acceptance.json`, 11,322 bytes,
  SHA-256 `d1758926e6fa7672bbce75e02b51686326ea192275393918667386632fedab31`.
  Two complete direct-authoritative replays reproduced both files byte-for-byte.
- The current 217-route Excel and PDF trees bind canonical manifests
  `e3e235e0f48645750b65b9df966a963c5a9bb856798d23661c95ab44056956e5`
  and `63f06f7b7f483a1fcd85be60278e7eebfbab51a79a1de955e9d3eac5bb8c8c2a`.
  They have the same ordered routes, exact suffix set `008U/010S/014U/058U/178S/210U`,
  and both omit route 170. All 14,322 fixed-layout values agree exactly; ordered typed
  digest `9c012be4529d358181010dca4c89d0e0e4a759d9c066248feddf0f7149b2f33a`.
- Independent comparison truth has 66 union rows, 58 shared, eight TSMIS-only, zero
  TSN-only, 53 differing shared, and five identical shared. TSMIS total is 16,459, TSN
  total is 16,626, and TSMIS minus TSN is -167. The exact ordered typed digest is
  `60459ed21842e53460e10ddc60c66e1cdbab1bf716b76826a5f4128c8b8fc120`.
  TSNR and the same-pull TSMIS pair prove Control F is red on mainline; the raw TSN PDF
  incorrectly duplicates Control G's “red on all” label for F.
- `source_truth_exact=true`, `production_value_projection_exact=true`,
  `production_comparison_semantics_exact=true`, and
  `stage8_base_oracle_complete=true`. `normalized_source_full_conservation=false` and
  `comparison_end_to_end_perfect=false` preserve exactly 10 product findings:
  CMP-AUD-020/021/022/023/076/144/145/146/183/184. The 12 source invariants, 24 audit
  invariants, detached binding, compilation, and permanent semantic/publication gate
  all pass; no production correction was made in this stage.
- Ramp Detail is accepted as the third base family. The exact 126+126 current TSMIS
  members, raw TSN XLSX/PDF, normalized r7 workbook/sidecar, Stage-6 result/acceptance,
  and TSN cross-format oracle are bound. Its D4 source truth, five production legs,
  36-assertion permanent gate, byte-identical two-run replay, and documented
  CMP-AUD-045/133/135/185 product-red boundary are recorded in the canary ledger.
- Intersection Detail is accepted as the fourth base family. Accepted result:
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\phase8_intersection_detail_comparison_r1.json`,
  1,059,072 bytes, SHA-256
  `7c7734aae212fbf9ad55de554cd2a0111549479b764ff3b91695fb524f21d86c`.
  Its 2,063-byte detached acceptance has SHA-256
  `67a267b491ecd380a8156af6b5d216cb27d875ac20175e5fe964acc61a0bbb30`.
  A second full replay produced the exact same result bytes; its 2,063-byte acceptance
  differs only in the result pathname and has SHA-256
  `737ceb082ecf0f18d9a21d44b29d1893e4e455e854798d5e9a46779493d659b8`.
- The current TSMIS bindings are 217 Excel members / 23,464,055 bytes / manifest
  `885149005ab9a261ca83b686f68cfc3fc4fe550d8fd42d99252dcd36fb365bc9`
  and 217 PDF members / 31,673,183 bytes / manifest
  `01e62eb195ab0bd5494cdb1b7a6a5ccbc35bd451bb5320a9bab0a045c58773c9`.
  The raw TSN XLSX/PDF, normalized workbook/sidecar, Stage-6 pair, and accepted
  XLSX↔PDF oracle all revalidated immediately before and after publication.
- Independent physical-key truth uses base Route, County, complete PP, and numeric Post
  Mile. Both TSMIS formats pair 16,199 rows against TSN with 260/427 one-sided. Excel
  has 21,676 differing cells; PDF has 21,683. PDF↔Excel pairs 16,459/16,459 with no
  one-sided rows and exactly nine differing cells. Raw↔normalized TSN pairs all 16,626
  rows with zero asserted differences. Production reproduces every overlapping compared
  cell exactly, but its weak Route+PM identity and source visibility remain red.
- Every nonblank typed source cell survives both production consolidations. Excel's only
  representation change is 125,152 explicit empty strings serialized as physical blanks;
  every explicit member Route and physical `S` claim remains exact. The raw Report View
  maps all 16,626 `MAIN_EFF_DATE`, `MAIN_ADT`, and `CROSS_ADT` values; the normalized
  Report View blanks all three, and both PDF-vs-TSN legs omit Report View entirely. These
  facts remain owned by CMP-AUD-045/068/070/133. All 24/24 audit invariants and 31/31
  mutation assertions pass; no production correction was made.

### Completed before the source-first reset

- Phases 1-3 closed the safety, typed-outcome, equality/pairing, workbook-freshness,
  publication, resource, cancellation, and path contracts.
- Complete offline runner: 119/119; comparison-specific selection: 31/31.
- Clean installed-Excel `CORE-ID-78-XLSX-TSN-2026-07-12-r3` canary: exact
  218-member raw manifest SHA-256
  `9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`,
  including raw TSN Intersection XLSX SHA-256
  `5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2`.
- Accepted production result SHA-256
  `a54448f621beb27cea4e4b7a82af1b0a65580e84c5eac6df313242959a1111b2`:
  16,199 paired, 260/427 one-sided, 16,053 differing rows, 21,675 differing
  cells, 518,368 asserted cells, 106 exact duplicate groups.
- Initial Phase-4 inventory: 49 previously known loader/parser findings, corrected family
  ownership, named red checks, source canaries, and hard stops.

This work remains valid: Phase 3 proved the shared comparison engine against one exact raw
TSN-backed current-schema family. The methodological correction is that the other TSN
families were not all re-established from their authoritative raw sources before the
Phase-4 sequence was first written.

### Source-first reset now active

- All family semantic edits were paused on 2026-07-12.
- `build/check_compare_physical_identity.py` was captured red before implementation. Its
  initial failures proved side-B raw-claim loss, PM-only environment pairing, and
  family-projector identity loss. The shared structured-identity substrate is now green
  for typed JSON roundtrip, mixed-mode rejection, outer-route authority, deterministic
  display, exact raw-claim serialization, and full-PM assertions. Family integration is
  intentionally deferred to Stage 11.
- Three authoritative raw XLSX inputs are already hash-bound:

| Family | Rows x columns | Bytes | SHA-256 |
|---|---:|---:|---|
| Ramp Detail | 15,410 x 18 | 1,590,431 | `3e0c552a0a130db07275eed776a05f2a3bd0b438b53eb33ceec54bdd9c722856` |
| Intersection Detail | 16,626 x 36 | 2,920,705 | `5170ab19b957ba78ab0f175571f3aab51e8c49cac13fa307b3d0beaa023c84a2` |
| Highway Detail | 60,083 x 56 | 16,356,075 | `bac3c882002b26433e39fad00c3dcdf9ad95b8dfc9ba9597386c656a71071dd1` |

- Raw identity census corrected an old shorthand: Highway Detail has 453 multi-county
  keys only under the weaker base `RTE + PP + POSTMILE` probe; the current production-
  shaped route-suffix + `pm_canon` key exposes 438 keys / 976 county identities.
- Raw TSN plus current TSMIS independently proved six Intersection groups where prefix
  alone distinguishes two real physical rows at the same route/county/numeric PM. The
  complete glued prefix+PM+suffix token is therefore mandatory; county+numeric-PM is not
  sufficient.
- The r2 seven-family pre-hardening production baseline completed under
  `C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline\`.
- The source census is now exact: 29 comparison-truth members / 52,670,235 bytes /
  canonical manifest
  `c6c91c378c4010682df72f000212df26f9ed5caae89ba38bb6c6b226393a7c54`,
  plus 14 evidence-only PDFs / 53,336,889 bytes /
  `0f2f1edbb7c6eed04b203fdfd4e8941332f55501fae48c6a3daac404f4c3c048`.
- Historical r1/r2 builds against those exact bytes reproduced the expected raw
  row/category counts and supplied the clean pre-hardening semantic baseline. The r1
  defects (implicit detail completion and Highway Log's shared intermediate directory)
  were corrected by r2/CMP-AUD-132. The later admission, manifest, immutable-snapshot,
  coherent-certificate, consumer-capture, and commit-guard changes are covered by the
  accepted `raw-2026-07-12-r7` post-contract witness: all seven families are
  complete/0/0, and an independent r2/r7 stream found zero differences across
  5,547,205 typed/value cells.
- Cross-format TSN parity now explicitly owns Excel-row-to-PDF record/category/section
  mappings and layered Report View placement. Different IT export times may explain a
  precise source-dated delta; they never justify an unclassified or silently folded
  discrepancy.

## Current execution sequence

1. **Complete:** bind all seven raw TSN datasets and internal report parameters.
2. **Complete:** rebuild all seven normalized workbooks from raw into isolated storage.
3. **Complete:** add independent raw schema/cardinality/identity oracles and compare them to each
   production build, including every required source field.
4. **Complete:** prove source-date-aware TSN XLSX-to-TSN-PDF parity for Ramp, Intersection, and
   Highway Detail, including an explicit row-to-record/category/section map used by
   evidence and layered Report View sheets.
5. **Complete at the base-audit layer — 7/7 families:** bind each vs-TSN placement to
   exact current sources and reproduce current product projections without treating a
   reproduced defect as correct behavior.
6. **Deferred / next implementer:** complete the remaining companion-format and
   historical-edition oracles across both workbook flavors.
7. **Deferred / next implementer:** reconcile all five evidence families end to end
   with zero unexplained discrepancies.
8. **Deferred / next implementer:** remediate family loader/identity/provenance/parser
   defects one family at a time, then run full release acceptance.

## Hard stops

- Do not change product/comparison code under the current authorization; begin from the
  implementation handoff only after the owner explicitly reauthorizes implementation.
- Do not accept a normalized workbook because it opens or has the expected width.
- Do not accept a match between two equally malformed/partial inputs.
- Do not use optional evidence PDFs as a substitute for authoritative XLSX truth.
- Do not accept sampled evidence while known unrepresented records/fields remain.
- Do not re-bless a changed count without exact source identity and cell-level cause.
- Do not infer a Highway Detail TSMIS county or silently adapt a vendor-pending layout.
- Do not resume a family semantic batch until its raw-source and normalization gates are
  executable and bound.

## Maintenance rule

Update this file at every phase transition and whenever the owner changes the definition
of perfection, supplies a new authoritative source, or clarifies a source role. Detailed
bugs stay in the finding ledger; exact canary hashes/counts stay in the binding ledger;
this file records the governing instructions, methodology, sequence, and current status.
