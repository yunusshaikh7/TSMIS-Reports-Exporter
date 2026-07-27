# Final Findings for Implementation

> Workflow artifact: **Stage 2 — canonical joint findings**
>
> Status: **JOINTLY APPROVED**
>
> Authority: Codex and Claude have both signed Stage 2. This is the sole findings
> backlog consumed by implementation planning. Stage 1 finding files remain
> audit evidence and must not be treated as competing backlogs.
>
> New-chat entry point: [START-HERE.md](START-HERE.md). Conflict resolutions and
> the joint decision arithmetic live in
> [FINAL-RECONCILIATION.md](FINAL-RECONCILIATION.md).

This file contains **no proposed code patch and no bundle assignment.** Bundles
are Stage 3 (`prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md`).

## Scope freeze

| Field | Value |
|---|---|
| Reconciliation commit | this commit, branch `audit/post-comparison-final-reconciliation` |
| Codex Stage 1 commit | `617bd52` (`MASTER-VERIFICATION.md`, `CODEX-FINDINGS.md` frozen on `main`) |
| Claude Stage 1 commit | `c788b29` (freeze), SHA recorded by `4bb1f1b`, manifest refreshed by `edf307d` |
| Frozen source archive | `2026-07-23 ssor-prod.zip`, SHA-256 `217F172F7EF7DB527A1EF30E2BFD12D1D6B810BCA55C0D38B7733CB4BE74266F`, 152,681,267 bytes — re-verified in Stage 2 |
| Site of origin | **Development site of SSOR-prod.** Permanent/main-site equivalence is NOT established |
| Canonical record count | **22** (20 actionable findings + two no-fix records) |
| P1 / P2 / P3 / no-fix | **9 / 9 / 2 / 2** |
| Clean Road finding IDs | PCOA-FINAL-010, PCOA-FINAL-013 |
| Source-side (vendor, not code) | PCOA-FINAL-020 |
| Latent (not yet observable) | PCOA-FINAL-012 |
| Open Stage 2 conflicts | **None** |
| Deferred future-test IDs | DEF-01 … DEF-05 |

## Severity definitions used here

| Level | Meaning in this audit |
|---|---|
| **P1** | The deliverable states something untrue, unreadable, or unusable to a user acting on it, **or** no deliverable is produced where one is required |
| **P2** | The deliverable is usable but materially incomplete, misleading in a bounded way, or wastes significant user time |
| **P3** | Correctness and usability hold; hygiene, durability, or a minor presentation gap |

## Index

| ID | Sev | Title | Family / subsystem | Aliases |
|---|---|---|---|---|
| PCOA-FINAL-001 | P1 | Ramp Detail Excel export refused end to end while its consolidation reports success | Ramp Detail | CX-001, CX-002, CX-005, CL-001, CL-004 |
| PCOA-FINAL-002 | P1 | Matrix-lane vs-TSN workbooks lose the TSN print identity and print a false rebuild instruction | vs-TSN, matrix lanes | CX-003, CL-002 |
| PCOA-FINAL-003 | P2 | vs-TSN Provenance names a transient `%TEMP%` path as the compared input | vs-TSN, matrix lanes | CL-003 |
| PCOA-FINAL-004 | P1 | Evidence is generated for prohibited mixed-source pairs, then describes sources it never read | Visual evidence | CX-009, CX-011 (eligibility consequence), CL-010 |
| PCOA-FINAL-005 | P1 | Evidence target boxes can point to the wrong field or record | Visual evidence | CX-011, CL-016, CX-009 (part) |
| PCOA-FINAL-006 | P1 | Excel-side evidence panels silently truncate the drawn value at 26 characters | Visual evidence | CL-015, CX-009 (part) |
| PCOA-FINAL-007 | P2 | Eligible PDF-vs-PDF evidence is unavailable in cross-environment mode | Visual evidence | CX-004 (ENV scope), CL-014 |
| PCOA-FINAL-008 | P1 | Statewide summary workbooks clip category identities beyond recognition | Workbook presentation | CX-013 |
| PCOA-FINAL-009 | P2 | Large/detail workbooks clip Summary, Spot Check, and composite-key content | Workbook presentation | CX-014 |
| PCOA-FINAL-010 | P1 | Clean Road silently skips live source rows, publishing false and misrepresented differences | Clean Road Highway | CX-015 |
| PCOA-FINAL-011 | P1 | Highway Sequence PDF-vs-Excel self check publishes 3,714 representation-only differences | Highway Sequence self | CX-007 |
| PCOA-FINAL-012 | P2 | Ramp Detail self check will publish 108 asymmetric null-token differences once unblocked (latent) | Ramp Detail self | CX-006 |
| PCOA-FINAL-013 | P2 | Representation-only Description differences are not separated from substantive changes | Multiple, shared | CX-008, CX-010, CX-012 |
| PCOA-FINAL-014 | P2 | Per-field table reports never-compared CONTEXT columns as `0` differences | Highway Sequence, shared | CL-011 |
| PCOA-FINAL-015 | P2 | An absent second side is reported only after the first side is fully parsed | Engine, all PDF families | CL-012 |
| PCOA-FINAL-016 | P3 | Private TSN capture directories accumulate in `%TEMP%` | vs-TSN, matrix lanes | CL-005 |
| PCOA-FINAL-017 | P2 | TSN normalization is not identity-deterministic; a no-op rebuild invalidates every bound comparison | TSN library | CL-006 |
| PCOA-FINAL-018 | P2 | Three enabled report editions have no verification path at all | Report catalog | CL-007 |
| PCOA-FINAL-019 | P3 | The values twin's headline verdict is an uncached formula | Workbook presentation | CL-008 |
| PCOA-FINAL-020 | P1 | **Source-side:** the route 140 Highway Log Excel export is missing whole columns its own print carries | Vendor / site | CL-017 |
| PCOA-FINAL-021 | NO FIX | Prior 7.9 Highway Log PDF contains two genuine PDF-only rows | Highway Log source truth | CL-013 |
| PCOA-FINAL-022 | NO FIX | Site-side export changes observed and absorbed — must not regress | Parsers | CL-009 |

---

## PCOA-FINAL-001 — P1 — Ramp Detail Excel export refused end to end while its consolidation reports success

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-001, PCOA-CX-002, PCOA-CX-005, PCOA-CL-001, PCOA-CL-004 |
| **Family** | Ramp Detail (Excel edition) |
| **Workflows** | Classic environment · Direct vs TSN · By Day vs TSN · Everything vs TSN · Baseline · Everything ENV · Direct self · Everything SELF |
| **Values / formulas scope** | Both. **No workbook of either kind is produced** on any of the 8 affected decisions |
| **Evidence scope** | Knock-on `N/A` for three evidence-registry cells (ENV, TSN, SELF `ramp_detail` / `ramp_detail_pdf`) — evidence cannot exist without a comparison |

**Verified behavior.** The 2026-07-23 dev-site Ramp Detail Excel export changed
shape. Header census, independently reproduced by both rounds:

| Pull | Header |
|---|---|
| 2026-07-09 | `Location`, ``, `PM`, `Date of Record`, ``, `HG`, `Area 4`, ``, `City Code`, `R/U`, `Description` |
| 2026-07-23 | `Location`, `PRE`, `PM`, `Date of Record`, `HG`, `Area 4`, `City Code`, `R/U`, `OF`, `TY`, `Description` |

Blank labels are gone and the two previously print-only columns (`OF` = On/Off,
`TY` = Ramp Type) are now *in* the Excel export. Values **moved**, they were not
merely relabelled — prior row 2 is
`12-ORA-001 | R | 000.606 | 02/25/1976 | (blank) | D | Y | DAPT | U | 001/NB OFF… | (blank)`
against new row 2
`12-ORA-001 | R | 000.606 | 02/25/1976 | D | Y | DAPT | U | F | D | 001/NB OFF…`.
The comparator pins exactly one layout, so **refusal is the correct engine
response** — a bypassed header guard would map `OF`/`TY`/`Description`
positionally and publish a wrong answer.

Two things around that correct refusal are defects:

1. **`consolidate_ramp_detail.consolidate` nevertheless succeeds** — 126/126
   routes, `status=ok` — writing `tsar_ramp_detail_consolidated.xlsx` with header
   `Route, Location, PRE, PM, Date of Record, HG, Area 4, City Code, R/U, OF, TY, Description`,
   a workbook no comparator in the product accepts. The user gets a green
   consolidation followed by refusal from every comparison.
2. **The refusal message misdiagnoses and prescribes an impossible action.**
   `compare_ramp_detail_tsn._load_tsmis` passes `bad_header_msg=` *"isn't a
   CONSOLIDATED Ramp Detail workbook (expected a leading 'Route' column) —
   consolidate the per-route exports first."* The workbook **has** a leading
   `Route` column; the real gate is `ctc.exact_consolidated_header_ok(_TSMIS_HEADER)`.
   Re-consolidating reproduces the identical header and fails identically. Both
   sibling reports get this right: Intersection Detail names "the current (July
   2026) site format" and Highway Detail names "the exact 34-column export header".

**User impact.** Eight decisions in the exact 88-cell topology do not produce a
deliverable. The separate PDF-vs-Excel by-day corroborating path fails too,
making nine production comparison placements in all. Only the PDF edition's
non-self workflows remain verifiable; because Excel is the self check's other
leg, no path can currently prove that the two editions agree.

**Root cause.** *Verified:* a site-side export change plus a single pinned
positional header contract. *Explicitly a hypothesis, not verified:* that the
change will also reach the permanent site — the scope document forbids assuming
main-site equivalence.

**Ownership hint (inspection-supported).** `compare_env._ramp_detail_canonical_header`
→ `compare_ramp_detail_tsn._TSMIS_HEADER[1:]`; the message at
`compare_ramp_detail_tsn._load_tsmis`; the success path in
`consolidate_ramp_detail.consolidate`.

**Witnesses.** Claude: `witness\header_census.json`, `run_direct_env.json`,
`run_everything_tsn.json`, `run_byday_2026-07-23.json`, `run_fast.json`,
`run_baseline_pve_pve.json`, `inspection\probe_rd_consolidated.xlsx`.
Codex: `run-ledgers/cross-version-tabular-{values,formulas}.json`,
`run-ledgers/manual-vs-tsn-tabular-a-both.json`, `run-ledgers/self-full-both.json`;
consolidated SHA-256 `FC376F130F338F771E3EEA9F29E61B2DCF5954D533DC109DF712C1250751A555`.

**Acceptance test.** Given the frozen `2026-07-23 ssor-prod` Ramp Detail Excel
export: (a) all 8 affected decisions produce both a values and a formulas
workbook, **or** every affected path refuses with a message that names the actual
gate and an action that can succeed; (b) the consolidator's completion status
agrees with downstream consumability — a consolidation no comparator accepts must
not report `ok`; (c) any accepted layout maps `OF`, `TY` and `Description` to the
correct fields, proved on route 001 row 2 against the raw export.

---

## PCOA-FINAL-002 — P1 — Matrix-lane vs-TSN workbooks lose the TSN print identity and print a false rebuild instruction

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-003, PCOA-CL-002 |
| **Family** | All vs-TSN families |
| **Workflows** | By Day vs TSN **and** Everything vs TSN (the Direct/classic path is clean) |
| **Values / formulas scope** | Both twins; **24 workbooks measured in Stage 2** (12 By Day + 12 Everything) |
| **Evidence scope** | None directly |

**Verified behavior.** `matrix_build.captured_tsn_workbook` copies the normalized
TSN workbook into `%TEMP%\tsmis-tsn-consumer-*` and writes a **reduced** outcome
sidecar beside it:

```
library  …_normalized.xlsx.outcome.json  1224 bytes
         …, tsn_source_claims, tsn_normalization_version, tsn_raw_manifest,
         tsn_normalized_workbook_identity, tsn_artifact_identity_token
captured …_normalized.xlsx.outcome.json   159 bytes
         schema_version, completion, skipped_inputs, failed_inputs,
         built_at_mtime, producer_app_version
```

The comparator reads the claims from beside the path it was handed, so on a
matrix lane it always finds none and writes the fallback onto a user-facing
sheet:

> `TSN print: no source-claims record beside this normalized workbook (older
> normalization) — rebuild the TSN library to capture the print identity.`

**Stage 2 measurement (RC-3), two independent readers agreeing exactly:** of the
36 matrix-lane vs-TSN workbooks, **24 carry this text** — 12 By Day and 12
Everything — at `Summary by Category!A6` (Ramp Summary), `!A7` (Intersection
Summary), `Notes!A9` (Highway Sequence, both editions), `Notes!A4` (Highway Log,
both editions). The 12 clean workbooks are Intersection Detail, Intersection
Detail (PDF) and Ramp Detail (PDF) — the three families that expose no TSN
identity anywhere. Direct-lane workbooks: **0**.

**Controlled differential.** The same library workbooks compared through the
classic Direct path minutes later print the real identity for all four
comparators that expose one: `OTM22270 · Event 4843742 · reference 09/15/2025 ·
TRLBUGNI` (Ramp Summary), `OTM22250 · Event 4843738 · 09/15/2025` (Intersection
Summary), `OTM52010 California State Highway Log · report 09/15/25`,
`OTM22025 Highway Locations · report 15-SEP-25`.

**User impact.** Two harms. (a) A categorically false instruction: the library
*was* rebuilt immediately before the run and is complete/current, so the advised
rebuild cannot change the outcome and sends the user into a loop. (b) The
deliverable loses the one fact that makes it interpretable — that the TSN side is
a **2025-09** print being diffed against a **2026-07-23** pull, a ten-month gap
that explains the large difference counts. Combined with the three families that
never disclose TSN identity, the net effect is that **no vs-TSN deliverable
produced through Everything or By Day discloses its TSN vintage.**

**Root cause.** Verified: the capture step writes a reduced sidecar, and claim
lookup is path-adjacent rather than identity-bound.

**Ownership hint (inspection-supported).** `matrix_build.captured_tsn_workbook`;
the claim lookup in `compare_ramp_summary_tsn.py` and its `claims_notes`
fallback.

**Witnesses.** Stage 2 `witness\tsn_provenance_warning_scope.json` (all 36
workbooks classified, both methods). Claude:
`ssor-prod_ramp_summary_tsn.xlsx` (*Summary by Category*),
`ssor-prod_highway_sequence_tsn.xlsx` (*Notes*), `witness\temp_captures.txt`,
`generated-comparisons\direct-tsn-probe\`. Codex:
`run-ledgers/tsn-library-rebuild.json`,
`source-audit/all-completed-workflow-note-audit.json`.

**Acceptance test.** After a successful `tsn_library.build_consolidated(force=True)`,
regenerate all 18 By Day and all 18 Everything vs-TSN workbooks: **zero**
occurrences of "rebuild the TSN library"; and every family whose Direct-lane
workbook prints a TSN identity line prints the **same** line on both matrix
lanes. Assert on the workbook file, not on the log.

---

## PCOA-FINAL-003 — P2 — vs-TSN Provenance names a transient `%TEMP%` path as the compared input

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-003 (unique to Claude) |
| **Family** | All vs-TSN families |
| **Workflows** | By Day vs TSN and Everything vs TSN |
| **Values / formulas scope** | Both twins; **all 36 matrix-lane workbooks** (Stage 2 measured) |
| **Evidence scope** | None |

**Verified behavior.** The user-facing *Provenance* sheet records
`TSN | C:\Users\…\AppData\Local\Temp\tsmis-tsn-consumer-aec_pjwy\tsn_ramp_summary_normalized.xlsx`,
and `.provenance.json` records the same string as `inputs[1].selection`. That
directory is removed after the run. The classic Direct path records the real
`tsn_library\<report>\consolidated\…` path for every family. Stage 2 confirms the
`%TEMP%` marker is present in **all 36** matrix-lane vs-TSN workbooks — a
strictly wider scope than PCOA-FINAL-002's 24, because the three
identity-silent families still record the capture path.

**User impact.** The sha256 is correct, so the record is *verifiable* but not
*actionable*: the sheet that exists to answer "what did this workbook compare?"
points at a path the user can never inspect. This is the same
capture-step root cause as PCOA-FINAL-002 and will very likely be fixed with it,
but it is tracked separately because its scope is larger and a fix to the warning
alone would leave it standing.

**Witnesses.** Stage 2 `witness\tsn_provenance_warning_scope.json`;
Claude `witness\temp_captures.txt`.

**Acceptance test.** No `Provenance` sheet and no `.provenance.json` in any
generated comparison names a path under `%TEMP%`; every recorded TSN input path
exists and is readable after the run completes.

---

## PCOA-FINAL-004 — P1 — Evidence is generated for prohibited mixed-source pairs, then describes sources it never read

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-009 (modality half), PCOA-CX-011 (eligibility consequence), PCOA-CL-010 |
| **Family** | Highway Sequence, Highway Log, Intersection Detail (both editions), Ramp Detail (PDF) |
| **Workflows** | By Day vs TSN, Everything vs TSN, Everything SELF |
| **Values / formulas scope** | None — this is an evidence-only defect |
| **Evidence scope** | **11 registry cells** produce prohibited artifacts; **18 artifact sets / 1,778 retained PNGs** across By Day and Everything |

**Verified behavior.** Evidence is required only when **both semantic sources are
PDFs**. It is produced anyway in three distinct shapes:

* **Excel TSMIS side** — `highway_sequence` and `highway_log` vs TSN compare
  the consolidated **XLSX**; manifest read sets are `1 TSMIS xlsx + 12 TSN pdf`,
  and each left panel is labelled `TSMIS (Excel)`.
* **Normalized-XLSX TSN side** — every vs-TSN comparison reads a normalized
  workbook. `intersection_detail`, `intersection_detail_pdf` and
  `ramp_detail_pdf` borrow a different statewide PDF from
  `tsn_library\<report>\pdf\`. Highway Log / Highway Sequence (including their
  PDF rows) render the raw district PDFs that produced the library, but Prompt
  01 item 10 explicitly says that provenance does not make
  PDF-vs-normalized-XLSX evidence eligible.
* **Self checks** — all five SELF cells have one Excel side by construction.

The workbook then **asserts sources it did not read**: every image sheet says
*"Red box = the compared cell in each source **PDF**"*, and the Summary declares
`TSMIS PDFs: …\ssor-prod\highway_sequence_pdf` — a directory whose files appear
nowhere in the read set.

**The decisive case, found independently by both rounds:** `intersection_detail_pdf`
vs TSN reads **80 PDFs and zero XLSX**, yet its TSN panel still comes from a
different document than the one compared. **A PDF-only read set is therefore not
a sufficient test.** Both rounds converged on the same corrective rule — Claude:
*"every read-set member is the document the corresponding side was compared
from"*; Codex: the renderer *"opportunistically borrowed"* a sibling TSN PDF.

**Decisive contrast (Claude).** The *same* Highway Log PDF-vs-Excel comparison,
with the *same* typed outcome, runs on three production paths: the classic
Compare tab and the PDF-vs-Excel by-day matrix write **no evidence at all**
(correct), and only `matrix_build._run_self_evidence` writes it. **The product
already implements the rule correctly on two of three paths.**

**User impact.** A user receives illustrated "proof" for a comparison whose
illustrated source was never compared, with prose asserting it was.

**Ownership hint (inspection-supported).** `matrix_build._run_self_evidence`;
`visual_evidence.tsmis_source_role`; `visual_evidence._TSN_PDFS_IN_RAW`.

**Witnesses.** Claude: the manifest read sets and evidence workbooks under
`everything-dest\comparisons\tsn\*(evidence)*`. Codex:
`source-audit/{highway-sequence,highway-log,intersection-detail}-excel-vs-tsn-evidence-manual-review.json`,
`source-audit/ramp-detail-pdf-vs-tsn-evidence-manual-review.json`,
`source-audit/everything-v2-evidence-binding-and-eligibility.json`.

**Acceptance test.** For every generated evidence set, each read-set member is
the exact artifact its side was compared from (assert against the comparison's
own provenance, not against file extension); and no evidence artifact of any
kind — manifest included — is emitted for a pair failing that test. Re-run all
11 prohibited registry cells plus their By Day counterparts and assert zero
artifacts.

---

## PCOA-FINAL-005 — P1 — Evidence target boxes can point to the wrong field or record

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-011, PCOA-CL-016, PCOA-CX-009 (wrong-target crops) |
| **Family** | Highway Log and Highway Sequence, both editions |
| **Workflows** | By Day vs TSN, Everything vs TSN |
| **Values / formulas scope** | None |
| **Evidence scope** | All affected artifacts are `PROHIBITED`; this is an independent renderer defect |

**Verified behavior.** When the compared value is **blank on the TSN district
print**, the red target box lands on adjacent printed content instead of the
absent field. Confirmed across three independent runs and both families:

| Run | Case | Where the box actually lands |
|---|---|---|
| Codex, By Day HSL PDF | FT blank | the final `O` of printed `EQUATES TO` (6 of 12 layouts) |
| Codex, Everything HSL PDF | FT blank, ex. 2 and 3 | the final `O` of printed `EQUATES TO` (4 of 12) |
| Codex, By Day HL PDF | route 395 @ `T121.831`, Description blank | across the following `T121.945` row (2 of 180) |
| Claude, Everything HL PDF | route 140 @ `R029.757`, Description blank | one line lower, across the next record `R029.955` (`Description_1_stacked.png`) |
| **Stage 2 RC-2, Claude's Everything HSL PDF** | route 092 @ ALA 006.798, TSN FT blank | **the final `O` of printed `EQUATES TO`** (`FT_3_stacked.png`) |

**The mechanism, sharpened in Stage 2.** The boundary is precise and the TSMIS
side is *not* affected: in the same image set, `FT_1` and `FT_2` have the blank on
the **TSMIS** print and are boxed correctly in the empty column, because the
app's own print has a fixed column grid. The TSN district print collapses an
equation line to `006.798  EQUATES TO` with no column structure, so with no
anchor the renderer boxes the nearest printed text — or, when a Highway Log
Description has no continuation line, the following record. Populated targets are
boxed correctly on both sides (`Description_2`), and inline blanks on a
structured column (`NA_N_A_1`) are boxed correctly.

**Why this cannot be waived as a sampling artifact.** Different runs sample
different example rows, yet every run that drew a blank-on-TSN case exhibited the
defect. Codex's Everything HL PDF set passed 180/180 only because it happened not
to draw one; Claude's run of the same cell did draw one and failed. A crop-accuracy
verdict is therefore not reproducible run-to-run, which is itself worth fixing.

**User impact.** These artifacts must not be generated under the final evidence
rule, but when they are generated the illustrated proof can point at a different
record than the one being asserted — the strongest possible failure for an
artifact whose only job is to show where a difference is. The same targeting
mechanism remains relevant to future eligible PDF-vs-PDF ENV evidence.

**Secondary, milder symptom (both rounds).** A ~1-character left overshoot on
some targets (TSN `EQUATES TO` FT blanks, one Intersection Detail `CS Eff-Date`),
while others — Highway Log `Med Wid` — are tight and correct.

**Witnesses.** Stage 2 direct inspection of
`everything-dest\comparisons\tsn\ssor-prod_highway_sequence_pdf_tsn (evidence images)\FT_{1,2,3}_stacked.png`.
Claude: `…highway_log_pdf_tsn (evidence images)\Description_1_stacked.png`.
Codex: `source-audit/highway-sequence-pdf-vs-tsn-evidence-manual-review.json`,
`visual-review/evidence-review/highway-sequence-pdf-vs-tsn`,
`SUBAGENT-FINAL-TSN-HIGHWAY-SEQUENCE-PDF-VISUAL-CHECK.md`.

**Acceptance test.** For every rendered example whose compared value is blank on
either side, the target rectangle must fall inside the row rectangle of the
record named in the caption, and must not intersect any glyph belonging to
another record or to a different field. Assert on the **whole** generated set,
not a sample, specifically over the `EQUATES TO` and blank-Description
populations that the current sampler reaches only by chance. Apply the same
targeting assertion to future eligible PDF-vs-PDF ENV evidence.

---

## PCOA-FINAL-006 — P1 — Excel-side evidence panels silently truncate the drawn value at 26 characters

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-015, PCOA-CX-009 (truncated-crop sightings) |
| **Family** | Highway Sequence, Highway Log (Excel-panel rows) |
| **Workflows** | By Day vs TSN, Everything vs TSN |
| **Values / formulas scope** | None |
| **Evidence scope** | All Excel-rendered panels; census **8 of 190** rendered examples |

**Verified behavior.** `scripts/visual_evidence.py:1270` draws each Excel-side
cell as `text[:26]` **with no ellipsis** (the header label is separately capped at
24 on line 1266). Every rendered example whose compared value exceeds 26
characters therefore shows a *different string* inside the red target box:

| Set | Example | Drawn in the image | Actual compared value |
|---|---|---|---|
| Everything HSL vs TSN | 080 @ SOL 002.438 | `BENICIA RD OC 23-88, BENIC` | `BENICIA RD OC 23-88, BENICIA RD OC 23 88` |
| Everything HSL vs TSN | 101 @ MEN R101.895 | `JCT 271-REYNOLDS SEP217, R` | `JCT 271-REYNOLDS SEP217, RTE 271` |
| By Day HSL vs TSN | 046 @ SLO 045.480 | `W JCT RTE 41/46/MCMIL CYN ` | `W JCT RTE 41/46/MCMIL CYN RD [SLO041.R.R 42.171]` |
| Everything HL vs TSN | 101 @ 011.603R | `RIVERSIDE DR OFF RAMP  , O` | `RIVERSIDE DR OFF RAMP , OC 53-1493` |
| By Day HL vs TSN | 005 @ 031.314 | `SAN FERNANDO EB 53-1110, S` | `SAN FERNANDO EB 53-1110, SAN FERNANDO BR UC NO. 53-1110` |

Codex independently observed the same class on two further sets ("two truncated
TSMIS crops" on HSL, "four truncate the captioned TSMIS Description" on HL),
which corroborates it on artifacts Claude never opened.

**Verified not to affect PDF crops.** The observed PDF crop panels render full
39- and 55-character values untruncated. All currently generated panels in this
scope are prohibited by PCOA-FINAL-004, so a fix for 004 may retire this, and a
fix for this must not be assumed to fix 004.

**User impact.** The picture, whose entire purpose is to show the value in
context, endorses a **different string** from the one compared. The heading line
above the image does carry the full value, so the artifact is not internally
inconsistent — but it bites hardest on `Description`, the most-compared field.

**Ownership hint (inspection-supported).** `scripts/visual_evidence.py:1270`
(value) and `:1266` (header label).

**Acceptance test.** For every rendered example, the string drawn inside the
target box equals the compared value recorded in that example's Summary row, or
is visibly marked as elided. Assert programmatically over 100 % of rendered
examples in both layouts.

---

## PCOA-FINAL-007 — P2 — Eligible PDF-vs-PDF evidence is unavailable in cross-environment mode

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-004, PCOA-CL-014 |
| **Family** | Ramp Summary, Ramp Detail (PDF), Intersection Detail (PDF), Highway Log (PDF), Highway Sequence (PDF) |
| **Workflows** | Everything ENV (5 cells) |
| **Values / formulas scope** | None |
| **Evidence scope** | **5 registry cells** DENIED for absence |

**Verified behavior.** Five cross-environment cells compare PDF against PDF —
the one configuration the audit rule calls `REQUIRED` — and all have large
positive difference counts (Ramp Summary 67; Intersection Detail PDF 17,562;
Ramp Detail PDF 376 + 5/8 one-sided; Highway Log PDF 88,238 + 2,095/1,174;
Highway Sequence PDF 1,904 + 7/246). **No evidence artifact of any kind exists
anywhere under the env, baseline, or PDF-vs-Excel trees**, and
`matrix_build.build_cell_comparison` **takes no evidence argument at all** — so
this is an unimplemented capability, not a failed generation. Ramp Summary vs
TSN is not part of this finding: that comparison reads a normalized TSN XLSX, so
its clean evidence absence is correctly `APPROVED` under Prompt 01 item 10 even
though raw PDFs exist upstream on both sides.

**User impact.** The user cannot obtain illustrated proof for the comparisons
most likely to need it. Nothing leaked, so no wrong artifact was delivered — the
harm is a missing capability, which is why this is P2 rather than P1.

**Ownership hint (inspection-supported).** `matrix_build.build_cell_comparison`
(no evidence parameter on the env path).

**Acceptance test.** With evidence enabled, each of the 5 cells produces a bound
manifest, evidence workbook, image set, and a PDF-only read set that satisfies
PCOA-FINAL-004's exact-source test. Every retained crop is accurate and readable;
absence or relabelling the supported comparison as `N/A` does not pass.

---

## PCOA-FINAL-008 — P1 — Statewide summary workbooks clip category identities beyond recognition

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-013 |
| **Family** | Ramp Summary, Intersection Summary |
| **Workflows** | Classic · Direct vs TSN · By Day vs TSN · Baseline · Everything ENV · Everything TSN |
| **Values / formulas scope** | **Both twins.** Codex scope: 24 workbooks / 748 materially clipped cells |
| **Evidence scope** | None |

**Verified behavior — independently reconfirmed in Stage 2 (RC-1).** The
`Comparison` sheet's category column measures **89 pixels** — the exact figure
Codex reported — while category labels need up to **309 px**. Measured with real
Calibri 11 glyph metrics, Excel's own width→pixel conversion, a 6 px tolerance,
and a gate that reports a cell only when it *cannot* spill:

| Workbook | Materially clipped cells | Worst case |
|---|---:|---|
| Ramp Summary vs TSN (values) | 33 | `Population: R-RURAL -O OUTSIDE CITY` — 119 px short |
| Intersection Summary vs TSN (values) | 70 | `RURAL/URBAN/SUBURBAN: U-O - URBAN -O OUTSIDE CITY` — 220 px short |
| Ramp Summary classic env (values) | 5 | `Summary!B13` — 364 px short |

Codex additionally proved it end-to-end with a native-Excel PDF export, so it is
present in the application a user actually opens: `Ramp Type: C - Direct or
Semi-direct Connector (Left)` displays as `Ramp Type: C`.

**User impact.** Several categories collapse to the *same* visible text
(`Ramp Type: C`, `Highway Group: R`…), so a reader cannot tell which row is which
without selecting each cell or resizing the column. This is why it is rated P1
while its detail-sheet sibling is P2: the identity of the compared thing is
unreadable, not merely an instruction.

**Reconciliation note.** Claude's `VC-14` "presentation contracts hold" is
**not** a contradiction — it measured data columns (explicit width 13.0), the
45.75 pt wrapped header row, mask/snapshot hidden states and filter ranges, all
of which Stage 2 also finds clean. It never measured these label cells.

**Ownership hint (inspection-supported).** Widths are stored workbook facts
written by the shared `compare_core` writer — hard-coded values at
`scripts/compare_core.py:2015-2023`, `:2169-2179`, `:2348`.

**Witnesses.** Stage 2 `witness\clipping_recheck.json` (per-cell, with available
and required pixels). Codex: `source-audit/statewide-summary-visible-text-clipping.json`,
`visual-review/excel-native/byday-ramp-summary-comparison.pdf`.

**Acceptance test.** In every generated summary workbook, each populated,
non-wrapped, non-shrink `Summary` and `Comparison` label cell whose right
neighbour is populated must fit its stored column width at Calibri 11 within 6 px
— or be wrapped, or the column widened. Assert on the stored workbook, and
confirm once by native-Excel render that no category label is ambiguous.

---

## PCOA-FINAL-009 — P2 — Large/detail workbooks clip Summary, Spot Check, and composite-key content

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-014 |
| **Family** | All non-summary families, plus Clean Road Highway |
| **Workflows** | Classic · Direct vs TSN · Direct self · Baseline · Everything ENV / TSN / SELF |
| **Values / formulas scope** | **Both twins.** Codex scope: 41 pairs / 82 workbooks |
| **Evidence scope** | None |

**Verified behavior — independently reconfirmed in Stage 2 (RC-1)**, on Claude's
retained workbooks, reproducing every class Codex named:

| Cell class | Codex | Stage 2 measurement |
|---|---|---|
| `Spot Check!B6` | ~72 px too narrow "in every reviewed schema" | 55–76 px short in every workbook checked |
| `Summary!B13:B14` labels | overrun by ~43–179 px (Baseline one-sided ~360 px) | 47–183 px short; 364 px on the classic environment twin |
| Composite `Key` column | 12–36 px short | 8–33 px short (`Comparison!B`, e.g. `001 / ORA / R000.129`) |

Formula twins insert the red F9 row so the primary failures shift one row
(`B13:B14` → `B14:B15`); the defect is unchanged. Codex confirmed the
representative Summary and Spot Check failures directly in native Excel on both
a direct and a classic Ramp Detail (PDF) workbook.

**User impact.** Audit instructions, status labels, and selected composite keys
are unreadable in the default sheet view. Rated P2 rather than P1 because the
*data* remains legible and unambiguous — unlike PCOA-FINAL-008, no two rows
become indistinguishable.

**Ownership hint (inspection-supported).** Same writer as PCOA-FINAL-008;
`scripts/compare_core.py` — `key_col` width 14 at `:2015`, `back_col` 13 at
`:2016`, the Spot Check sheet built from `:2314`.

**Witnesses.** Stage 2 `witness\clipping_recheck.json`. Codex:
`source-audit/large-detail-no-render-visual-adjudication.json`,
`visual-review/excel-native/ramp-detail-pdf-{summary,spot-check}-*.pdf`.

**Acceptance test.** Same measurable rule as PCOA-FINAL-008, applied to
`Summary`, `Spot Check` and the composite key column of every non-summary
schema, in both twins.

---

## PCOA-FINAL-010 — P1 — Clean Road silently skips live source rows, publishing false and misrepresented differences

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-015 |
| **Family** | Clean Road Highway (ArcGIS vs TSN) |
| **Workflows** | ArcGIS tab comparison |
| **Values / formulas scope** | Both twins (Matrix F, 2 decisions) |
| **Evidence scope** | None |

**Verified behavior.** The public ArcGIS builder is **exactly rule-faithful**
across 57,728 built rows, 252 routes, 74 fields and 4,271,872 cells — the defect
is not in the build rule. But **102 current raw rows marked `LocError=NO ERROR`**
have usable AR measures and one missing PM endpoint, and the no-guess contract
silently omits their values at the affected anchors. An exact join from each
visible ArcGIS row's `Key (helper)` token to the Comparison sheet's hidden
`__CMP_E2_KEY_V1_TOKEN` — inferring no missing span — proves:

* **161 published `D` cells are exact false positives** — the visible TSN value
  equals the skipped ArcGIS raw value;
* **4 further `D` cells are genuine differences materially misrepresented** —
  at route 036 / TEH / 40.15 and 40.352 TSN shows lanes/width `2/24` and the
  skipped raw ArcGIS anchors show `1/12`, but the workbook displays ArcGIS as
  **blank**;
* the 165 cells span 83 comparison rows and 87 source endpoints; 162 display a
  blank ArcGIS side and three an older or alternate value.

The Summary and Notes **disclose none of this** — no mention of unlocatable rows,
missing PM endpoints, skipped source rows, or `LocError`. Summary instead defines
red as "ArcGIS ≠ TSN" and `(blank)` as "empty in the system", which makes the
omissions look authoritative.

**User impact.** A user reading the deliverable concludes that ArcGIS has no
value where it demonstrably does. Release-blocking as an interpretation defect
even though the workbook arithmetic and the builder's stated rule are internally
consistent.

**Reconciliation note (important).** Claude approved this cell because it
reproduces the repo's blessed `CRH-SW-E2` canary **exactly** (52,647 / 5,081 /
7,436 / 291,292). Scope rule 8 forbids approving on internal consistency alone,
and Claude did not audit the ArcGIS build against the raw layers. **The canary is
not invalidated** — it was blessed on this same builder rule; what is new is that
the rule's silent omissions surface as displayed differences. Any fix will move
the canary and must be re-blessed with exact input/output evidence per the
`compare_core` convention.

**Witnesses.** Codex: `source-audit/CLEAN-ROAD-HIGHWAY-RAW-SOURCE-TRUTH-FINAL.md`,
`clean-road-highway-raw-source-truth.json`,
`CLEAN-ROAD-COMPARISON-UNLOCATABLE-IMPACT.md`,
`clean-road-comparison-unlocatable-impact.json`. Claude:
`generated-comparisons\arcgis\clean_highway arcgis-vs-tsn (values).xlsx`.

**Acceptance test.** For each of the 102 skipped raw rows, the deliverable either
(a) does not publish a difference where the raw ArcGIS value equals TSN, or
(b) discloses in Summary/Notes that the ArcGIS side was skipped and why, with the
affected count. Assert the 161 false positives fall to zero and the 4
misrepresented cells display the real ArcGIS value or an explicit "skipped"
marker. Re-bless `CRH-SW-E2` with a documented delta.

---

## PCOA-FINAL-011 — P1 — Highway Sequence PDF-vs-Excel self check publishes 3,714 representation-only differences

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-007 |
| **Family** | Highway Sequence |
| **Workflows** | Direct self, Everything SELF, PDF-vs-Excel by-day matrix (all three agree) |
| **Values / formulas scope** | Both twins, 2 decisions |
| **Evidence scope** | `PROHIBITED` — related leak tracked under PCOA-FINAL-004 |

**Verified behavior.** The same-day, same-pull self check reports 1,395 differing
matched rows and 3,714 differing cells across 60,254 paired rows with zero
one-sided rows. Both rounds produced identical totals **and identical per-field
splits**: `PM Suffix` 547, `HG` 929, `FT` 1,119, `Description` 1,119. The
workbook's masks, displayed cells, per-field totals, hash-bound payload and
outcome sidecar all reproduce those claims, so this is not a workbook-arithmetic
fault.

Codex's independent full-corpus canonicalization — using only explicit equation
lines, their keyed Excel rows, and proven source/target relationships — covered
all **1,119 `EQUATES TO` relations**, including 39 county/route-boundary
relations and three delayed target markers, with **zero unsupported cases**.
After canonicalization all 60,254 rows compare with **zero** differing rows and
cells. The PDF prints an equation as a source line plus a target line; Excel
folds the marker, classification, suffix placement and description onto its
source record.

**User impact.** A check whose entire purpose is to detect real divergence
between two editions of the *same pull* presents 3,714 known representation
differences as data disagreements. The product already discloses this exact
equation-relation class in the vs-TSN `Notes`, so the omission is inconsistent
within the product itself.

**Final cross-check.** The second reviewer re-ran the adjudication against the
complete 60,254-row witness and directly inspected raw route 001 on both sides.
The XLSX carries the equation source at `ORA R 018.540` and its target at
`ORA 018.530`; the rendered source PDF page 6 prints `ORA R 018.540 EQUATES TO
END R REALIGNMENT` followed by the target line `ORA 018.530 E D H 001.267`.
That source/target representation is exactly the class canonicalized across all
1,119 relations. The cross-check is recorded as `SR-04` in
`stage2-second-review-crosscheck.json`; no unsupported relation remains.

**Witnesses.** Codex: `source-audit/self-highway-sequence-discrepancy-audit.json`,
`highway-sequence-pdf-excel-equation-parity.json`, `run-ledgers/self-full-both.json`.
Claude: `generated-comparisons\direct-self\highway_sequence_pdf pdf-vs-excel (values).xlsx`.

**Acceptance test.** The same-day Highway Sequence PDF-vs-Excel self check on the
frozen `2026-07-23` pull reports **zero** differing cells, **or** classifies the
1,119 equation relations as a disclosed representation class that is excluded
from the differing-cell count and named in Summary and Notes. Prove on all 60,254
rows, not a sample.

---

## PCOA-FINAL-012 — P2 — Ramp Detail self check will publish 108 asymmetric null-token differences once unblocked (latent)

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-006 |
| **Family** | Ramp Detail |
| **Workflows** | Direct self, Everything SELF |
| **Values / formulas scope** | Both — **not currently observable**; masked by PCOA-FINAL-001 |
| **Evidence scope** | `PROHIBITED` |

**Verified behavior.** An independent positional comparison paired all 15,213
Excel and PDF rows with zero missing keys. After the documented whitespace/OOXML
render equivalences, the current loader projection still disagrees on **108 cells
across 36 rows**: 36 `Area 4`, 36 `OF`, 36 `Description`. Every residual is one
semantic null class — the new Excel export carries `-` in `Area 4`/`OF` and
`NO RAMP LINEAR EVENT` in `Description`, and the PDF consolidator has *already*
projected those printed tokens to blank. A symmetric same-source null projection
reduces all 108 to zero. Route 005 at `07-LA-005 / 025.218` visibly carries the
same null tokens in **both** raw exports.

**Why this is not the PCOA-FINAL-013 class.** This is an **asymmetry**, not a
normalization preference: the same source token renders differently on the two
legs of a same-source check because the self comparator's comments assume the
tokens are PDF-only, which the new Excel edition falsifies. No owner contract
decision is required.

**User impact.** None today — PCOA-FINAL-001 prevents any workbook. The moment
that header gate is fixed, a same-source deliverable whose semantic truth is zero
will publish 108 false discrepancies. **Fixing 001 without this creates a new
defect.**

**Witnesses.** Codex: `source-audit/ramp-detail-pdf-excel-sibling-parity.json`;
raw `ramp_detail/tsar_ramp_detail_route_005.xlsx` and
`ramp_detail_pdf/tsar_ramp_detail_route_005.pdf`.

**Acceptance test.** With PCOA-FINAL-001 resolved, the same-day Ramp Detail
PDF-vs-Excel self check on the frozen pull reports zero differing cells across
all 15,213 rows.

---

## PCOA-FINAL-013 — P2 — Representation-only Description differences are not separated from substantive changes

| Field | Value |
|---|---|
| **Aliases** | PCOA-CX-008, PCOA-CX-010, PCOA-CX-012 |
| **Family** | Highway Log (both editions), Highway Sequence (both editions), Ramp Detail (PDF), Intersection Detail (both editions), Clean Road Highway |
| **Workflows** | Direct vs TSN, By Day vs TSN, Everything vs TSN, Clean Road |
| **Values / formulas scope** | Both twins — shared discrepancy masks |
| **Evidence scope** | None |
| **Status** | **CONFIRMED DISCLOSURE / CLASSIFICATION DEFECT** |

**Verified behavior.** Independent full-field classification of hash-bound
comparison payloads found these token-identical-modulo-presentation cells:

| Scope | Cells | Example |
|---|---:|---|
| Highway Log vs TSN, **per format** | 1,243 ×2 | `NEVADA STATE LINE , END OF COUNTY` vs `NEVADA STATE LINE /END OF COUNTY` |
| Highway Sequence vs TSN, per format | 11 ×2 | `CITRUS AVE OC 54-1293` vs `Citrus Ave OC 54-1293`; `SLO SB CO LINE` vs `SLO/SB CO LINE` |
| Ramp Detail (PDF) vs TSN | 2 | `NB OFF TO S. GEYSERVILLE` vs `NB OFF TO S.GEYSERVILLE` |
| Intersection Detail vs TSN, per format | 1 ×2 | `''F'' ST` vs `"F" ST` |
| Clean Road Highway landmarks | 5 | leading apostrophe before `-VIA BIG BEAR BLVD-` |

The identical 1,243-cell set appears in **both** fresh export formats, ruling out
a PDF-extraction artifact. Normalization is not the cause: all 15,410 Ramp Detail
and all 16,626 Intersection Detail TSN rows match their raw sources
field-for-field, and Clean Road's 60,083 × 74 normalization changes zero cells.

**Defect boundary.** These are **real literal differences between two sources**,
so no automatic equality or normalization change is asserted here. The defect is
that unqualified headline totals do not distinguish this exactly measured
punctuation/case/quote/presentation class from substantive data changes. A reader
cannot tell how much of the total is merely representational. Any future equality
or normalization change remains subject to the `compare_core` correctness lock
and must be separately approved and proved cell-for-cell.

**A shipped behavior that constrains any normalization choice.** The Intersection Detail pair
`''F'' ST` vs `"F" ST` is the KER 046 @ 50.904 case the product **already
deliberately annotates** through the evidence `_quote_note` clarifier — i.e. it
has previously been treated as worth *showing*, not suppressing. Suppressing it
now would reverse a shipped decision.

**User impact.** Highway Log vs TSN combines 1,243 presentation-only Description
cells per format with substantive cells under one unqualified total. Because
affected rows may also differ in other fields, **no corrected differing-row total
is asserted.**

**Witnesses.** Codex: `source-audit/direct-all-field-semantic-candidates.json`,
`highway-log-description-semantic-classification.json`,
`direct-description-semantic-classification-remaining.json`,
`clean-road-highway-landmark-four-source-trace.json`.

**Acceptance test.** Either (a) Summary and Notes disclose the representation-only
class and its exact count separately from substantive differences, or (b) a
separately approved normalization changes equality and the affected counts move
by the exact proved deltas, with re-blessed canaries and cell-for-cell evidence.
No undisclosed change to equality semantics is accepted.

---

## PCOA-FINAL-014 — P2 — Per-field table reports never-compared CONTEXT columns as `0` differences

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-011 (unique to Claude) |
| **Family** | Highway Sequence (scope: any column that is context in its entirety) |
| **Workflows** | All vs-TSN paths |
| **Values / formulas scope** | Both twins |
| **Evidence scope** | The evidence *Ledger* already gets this right — see below |

**Verified behavior.** On `ssor-prod_highway_sequence_tsn.xlsx` the Summary's
*DIFFERENCES BY FIELD* table lists `City | I | 0`, `HG | J | 0` and
`Distance To Next Point | L | 0` — visually identical to a genuinely identical
compared column. Those three are **CONTEXT** columns that are never counted. The
typed outcome knows it (`context_cells = 171,150` alongside
`asserted_cells = 171,150`), the evidence workbook's *Ledger* marks them
explicitly, and the *Notes* sheet explains the domain reason. **The headline
sheet does not.**

**User impact.** A reader of the Summary alone concludes that City, HG and
Distance match perfectly across 57,050 rows. They were never compared — and the
evidence images themselves show a real Distance difference (`000.562` vs
`000.274` at route 101 @ MEN R101.895).

**Scope boundary (verified).** Only columns that are context *in their entirety*
produce this. Highway Log's per-cell ditto context (14,872 cells in the PDF
edition) produces no misleading zero. The Clean Road workbook partially mitigates
with an explicit per-column counted/context table; Highway Sequence has none.

**Witnesses.** Claude: `generated-comparisons\direct-tsn\highway_sequence vs tsn (values).xlsx`
(*Summary*, *Notes*), and the matching evidence *Ledger*.

**Acceptance test.** In every comparison Summary, a wholly-context column is
rendered distinguishably from a compared column with zero differences — e.g.
`context` / `not compared` rather than `0`. Assert on Highway Sequence's `City`,
`HG` and `Distance To Next Point`, and confirm Highway Log's ditto columns still
report real counts.

---

## PCOA-FINAL-015 — P2 — An absent second side is reported only after the first side is fully parsed

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-012 (unique to Claude) |
| **Family** | All statewide PDF families |
| **Workflows** | Classic environment, Baseline, Everything ENV |
| **Values / formulas scope** | Neither — a runtime behavior |
| **Evidence scope** | None |

**Verified behavior.** Three measured witnesses: `intersection_detail_pdf`
cross-environment **429.4 s**, `intersection_detail_pdf` baseline **438.6 s**, and
`highway_detail_pdf` Everything ENV **1,229.7 s (20.5 minutes)** — each parsing
217–252 statewide prints before reporting that the *other* side has no export. A
missing **first** side errors in **0.0 s**.

**User impact.** On a statewide PDF family the user waits up to twenty minutes
for an answer the app could give immediately, on exactly the locked-down work PCs
where there is no way to inspect what is happening.

**Acceptance test.** With side B absent, every comparison path reports the
missing side in under 5 seconds regardless of side A's size. Reproduce with the
three witnessed configurations.

---

## PCOA-FINAL-016 — P3 — Private TSN capture directories accumulate in `%TEMP%`

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-005 (unique to Claude) |
| **Family** | All vs-TSN families |
| **Workflows** | By Day vs TSN, Everything vs TSN |
| **Values / formulas scope** | Neither |
| **Evidence scope** | None |

**Verified behavior.** Three `%TEMP%\tsmis-tsn-consumer-*` directories survive on
the audit machine: one from 2026-07-20 (emptied, not removed), one from
2026-07-23 still holding a 2,542,538-byte `tsn_highway_sequence_normalized.xlsx`
plus its sidecar, and one belonging to a run in flight.

**User impact.** Unbounded `%TEMP%` growth proportional to (vs-TSN runs ×
dataset size; the Highway Detail dataset is 8.5 MB per capture) on exactly the
locked-down work PCs where the user cannot clean up with a script.

**Witnesses.** Claude: `witness\temp_captures.txt`.

**Acceptance test.** After N vs-TSN matrix runs including at least one
cancellation and one failure, zero `tsmis-tsn-consumer-*` directories remain
under `%TEMP%`.

---

## PCOA-FINAL-017 — P2 — TSN normalization is not identity-deterministic; a no-op rebuild invalidates every bound comparison

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-006 (unique to Claude) |
| **Family** | All TSN datasets (8 measured) |
| **Workflows** | TSN library rebuild; consequences on every vs-TSN comparison |
| **Values / formulas scope** | Indirect — invalidates bound generations |
| **Evidence scope** | Indirect |

**Verified behavior.** The whole library was force-rebuilt from raw whose
`tsn_raw_manifest.sha256` and `normalization_version` were **unchanged**. All
eight datasets returned a **different** `tsn_normalized_workbook_identity` and
`tsn_artifact_identity_token` (Highway Log `…81cc9842…` → `…374a3a03…`).

**User impact.** That token binds a committed comparison generation to its TSN
source, so pressing the GUI's *Rebuild* button silently invalidates every
existing vs-TSN comparison even when nothing changed, forcing a full statewide
re-comparison.

**Root cause — EXPLICITLY A HYPOTHESIS, NOT VERIFIED.** openpyxl may write a
fresh document timestamp; the pre-rebuild bytes were replaced and cannot be
re-diffed. Any implementation must begin by establishing the real cause.

**Witnesses.** Claude: `witness\tsn_rebuild_all.json`.

**Acceptance test.** Two consecutive `build_consolidated(report, force=True)`
calls over unchanged raw produce byte-identical normalized workbooks and
identical `tsn_normalized_workbook_identity` / `tsn_artifact_identity_token`, for
all eight supported datasets.

---

## PCOA-FINAL-018 — P2 — Three enabled report editions have no verification path at all

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-007 (unique to Claude) |
| **Family** | `ramp_summary_excel`, `intersection_summary_pdf`, `highway_summary` |
| **Workflows** | None exist — that is the finding |
| **Values / formulas scope** | n/a |
| **Evidence scope** | Explains why 4 of the topology's `N/A` cells are `N/A` |

**Verified behavior.** `report_catalog` enables all three for export (none is in
`reports.DISABLED_EXPORT_SUBDIRS`), yet none has a consolidator, a
`report_catalog.MATRIX` row, or any comparison recipe. In the frozen archive that
is 126 `ramp_summary_excel` XLSX + 217 `intersection_summary_pdf` PDF =
**343 of the 2,380 exported route files (14.4 %)** that no workflow can check.
Ramp Summary is verified through its PDF edition while its Excel sibling is
unverifiable; Intersection Summary is the exact inverse.

**User impact.** A user exports files the product will never check, with nothing
in the UI saying so. This is also the direct cause of the four in-topology `N/A`
decisions (Direct/Everything SELF for Ramp Summary and Intersection Summary) —
both editions of both reports sit on disk and no comparator exists.

**Ownership hint (inspection-supported).** `report_catalog.MATRIX` is the single
per-row comparison wiring; `check_report_wiring` already derives required
touchpoints from it and would be the natural place to assert this.

**Witnesses.** Claude: `witness\export_coverage.txt`, and the committed
`claude-round1-export-coverage.txt`.

**Acceptance test.** Every export edition enabled in `report_catalog` either has
a dispatchable comparison path, or is explicitly marked export-only in the
catalog **and** surfaced as export-only in the UI. `check_report_wiring` fails
naming any edition that satisfies neither.

---

## PCOA-FINAL-019 — P3 — The values twin's headline verdict is an uncached formula

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-008 |
| **Family** | All |
| **Workflows** | All |
| **Values / formulas scope** | Values twin specifically |
| **Evidence scope** | None |

**Verified behavior.** The values workbook's `Summary!B3` (the
`✗ DIFFERENCES FOUND — …` / `✓` headline) and `Summary!C56:C62` (the SELF-CHECK
results) are live formulas written **without a cached value**; read data-only they
are empty. The workbook's own note discloses the SELF-CHECK rows ("only the Spot
Check sheet and the SELF-CHECK rows stay live") but **not** the headline. The
Comparison sheet's `… Row` hyperlink columns are in the same class but are
navigational, not informational.

**Codex's mitigation, retained.** The workbook declares `fullCalcOnLoad=True` and
installed Excel recalculates every SELF-CHECK result to `OK`, so an Excel user
never sees a blank. Codex therefore judged it non-representative of the end-user
workbook.

**User impact.** Confined to consumers that do not recalculate — `openpyxl`
`data_only=True`, pandas, automated readers — where the single most important
line of the deliverable is blank. P3 for that reason.

**Acceptance test.** Reading each values twin with `data_only=True` yields a
non-empty `Summary!B3` matching the typed `ComparisonOutcome`, or the workbook's
note discloses that the headline is live like the SELF-CHECK rows.

---

## PCOA-FINAL-020 — P1 — SOURCE-SIDE: the route 140 Highway Log Excel export is missing whole columns its own print carries

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-017; corroborated in Codex's "Highway Log same-day sibling approval" |
| **Family** | Highway Log (Excel edition), route 140 |
| **Workflows** | Every Highway Log Excel-sourced comparison |
| **Values / formulas scope** | Indirect — silently compares blanks |
| **Evidence scope** | None |
| **Status** | **NOT A PRODUCT DEFECT — VENDOR ACTION REQUIRED** |

**Verified behavior.** The PDF-vs-Excel self check reports differences in only 2
of 252 routes; for route 140 every one of the 213 differing rows differs on
`R/U`, `TER`, `H/G`, `A/C` in the form `X ≠ (blank)`. Verified at the raw source
by both rounds independently:

```
output\2026-07-23 ssor-prod\highway_log\highway_log_route_140.xlsx
    R/U -> '' x213 | TER -> '' x213 | H/G -> '' x213 | A/C -> '' x213
    (City, N/A and the LB* columns are blank too; only Location/MI/Cnty Odom/SPD carry data)
control highway_log_route_138.xlsx
    R/U -> R x193, U x57, B x14 | TER -> F x117, M x105, R x42
    H/G -> D x142, U x102, R x11 | A/C -> C x223, F x23, E x18
```

Codex states the same independently: "the raw PDF visibly prints RU/TER/HG/AC and
left-surface values while the raw Excel export leaves those cells blank."

**User impact.** Every Highway Log **Excel**-sourced comparison silently compares
blanks for route 140. Recorded at P1 because the owner must act on it with the
vendor, not because the product can fix it.

**Why it matters beyond route 140.** This is the strongest single argument in the
audit for the PDF-vs-Excel self check's value — the defect was found *only*
because that check exists.

**Acceptance test.** None in this product. Track the vendor's corrected export;
on delivery, the route 140 self check reports zero `X ≠ (blank)` differences on
`R/U`, `TER`, `H/G`, `A/C`.

---

## PCOA-FINAL-021 — NO FIX — Prior 7.9 Highway Log PDF contains two genuine PDF-only rows

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-013 |
| **Family** | Highway Log, both editions |
| **Workflows** | Classic environment (the diagnosis path) |
| **Values / formulas scope** | Diagnostic |
| **Evidence scope** | None |
| **Status** | **Validated source truth — regression guard, not a defect** |

**Verified behavior.** Cross-environment over the same two days: Excel edition
52,821 / 51,884 rows, 50,327 paired, 89,811 differing cells; PDF edition
52,807 / 51,886 rows, 50,712 paired, 88,238 differing cells. Diffing the two
workbooks' own *Routes* sheets localizes the entire difference to **4 routes** —
`005` (15 rows), `074`, `101`, `140` (1 row each), net −14 / +2, reconciling both
totals exactly.

**Complete attribution.** Route 140 is PCOA-FINAL-020. Route 005 was
traced by Codex to real source divergence (the raw PDF advances an otherwise
identical payload to `R000.548` while Excel retains it at `000.243`; and at
`R025.780` the raw sides genuinely differ in mileage, county odometer, city, RU,
roadbed type and record date). The final source audit resolves the last two rows:

* route `074`, location `000.000`, occurrence 2 is present in the prior 7.9 raw
  PDF (page 7, line 31) and absent from its Excel sibling: PDF count 2, Excel
  count 1;
* route `101`, location `R022.828` is present in the prior 7.9 raw PDF (page 142,
  line 23) and absent from its Excel sibling: PDF count 1, Excel count 0.

Both are genuine PDF-only source rows retained correctly by the PDF path. The
second review confirmed the witness integrity and closes the former attribution
gap.

**Regression guard.** Continue retaining both source rows in the PDF-derived
universe and do not synthesize them in the Excel-derived universe. Witness:
`source-audit/prior-7.9-highway-log-sibling-raw-source-audit.json`, independently
cross-checked as `SR-02` in `stage2-second-review-crosscheck.json`.

---

## PCOA-FINAL-022 — NO FIX — Site-side export changes observed and absorbed; must not regress

| Field | Value |
|---|---|
| **Aliases** | PCOA-CL-009 |
| **Family** | Ramp Summary, Ramp Detail (PDF), Intersection Detail (PDF), Intersection Summary (PDF), Highway Sequence (PDF) |
| **Status** | **Validated clean — recorded as a regression guard, not a defect** |

**Verified behavior.** Two site-side changes appear in the frozen archive:

1. A stray leading **`GENERATE`** line is now the first text line of the
   `ramp_summary`, `ramp_detail_pdf`, `intersection_detail_pdf` and
   `intersection_summary_pdf` prints; absent from the retained batch.
2. The **Highway Sequence Listing (PDF)** print was re-skinned from
   `California Department of Transportation / Highway Sequence Listing` to the
   TASAS layout `TASAS / Traffic Accident Surveillance and Analysis System /
   HIGHWAY SEQUENCE LISTING (W/CITIES)`, with a wider text measure.

**The app's parser absorbs both** — route 001 yields 2,581 rows from the new print
and 2,583 from the prior print. Flagged only because a future parser change must
keep supporting **both** layouts.

**Witnesses.** Claude: `witness\pdf_head_census.txt`.

**Regression test.** The Highway Sequence PDF parser produces correct row counts
for both the pre- and post-re-skin print layouts, and the leading `GENERATE` line
is ignored on all four affected print families.

---

## Validated-clean and no-fix areas — must not regress

Recorded per prompt item "record clean/approved behavior that must not regress".
Each was adversarially reviewed and passed; several are load-bearing for the
denials above.

| Area | Joint conclusion | Audit evidence |
|---|---|---|
| **Comparison arithmetic and source truth** | Whole-family independent recounts reproduce the engine exactly. Intersection Summary cross-environment: 217 routes, 217 paired, 0 one-sided, 7 routes with a difference, **16 differing values** — reproduced to the cell by an app-free reader over all 434 raw exports, and separately by Codex over 14,105 raw cells | Claude `VC-4`, `witness\recount_is_env.json`; Codex "Intersection Summary statewide counts" |
| **Duplicate-identity pairing contract** | Highway Sequence row universe, one-sided counts and 1,919 differing rows match exactly **once duplicates are paired most-alike** — Claude's naive positional pairing gave 2,089 and was the thing that was wrong. Residual 2 cells of 1,931 (0.10 %) from a tie-break difference | Claude `VC-6` over all 504 per-route exports |
| **Workflow parity across dispatch paths** | Exact on every measurable family: classic == Baseline == Everything ENV; Direct == By Day == Everything TSN on all nine; Direct == PDF-vs-Excel matrix == Everything SELF | Claude `VC-11`; Codex "final isolated Everything typed results match Direct and By Day" throughout |
| **Formula twins vs values twins** | Zero unexpected semantic mismatch under installed-Excel recalculation, at two very different scales | Codex 60/60 pairs, 313,497,190 cells; Claude `VC-3`, 15,756,782 cells, 0 real differences, 0 Excel errors |
| **Workbook state and presentation contracts (data grid)** | `__CMP_E1_STATE_V1_*` and `__CMP_E2_BUILD_FRESH_*` hidden, `__CMP_E2_SNAPSHOT_A/B` `veryHidden`, autofilter stops before the mask columns, data columns carry explicit widths (13.0) with a 45.75 pt wrapped header row and **no clipping**, hidden mask agrees cell-for-cell with rendered content | Claude `VC-14`; Stage 2 RC-1 independently confirms the **data** columns are clean — only label cells fail |
| **Per-row source provenance** | Highway Log *Source Files* maps side-A rows 1–2,241 to `highway_log_route_001.xlsx` and 2,242 onward to route 002 — 2,241 is exactly the independently counted raw row count | Claude `VC-15` |
| **No false-positive class from whitespace/escapes** | Of 99 Highway Sequence cross-environment `Description` difference cells, **zero** are whitespace-only or `_x000D_`-escape-only | Claude `VC-16` |
| **A suspected normalizer defect, tested and refuted** | The 10 TSMIS-only Highway Sequence routes (`005S`, `008U`, …) are genuine source asymmetry, not suffix folding: the TSN print's group header is `DIST 11 RTE 005 DIR S-N` — route plus a **direction** token — and the print carries no suffixed route | Claude `VC-17` |
| **The evidence Ledger is exhaustive and separates context correctly** | Per column: counted differences, unique-row, repeated-key-group, **context cells**, identical, one-sided, examples rendered, why-no-example, totals row, and a ledger digest bound into the manifest. Deterministic across workflows (same digest `401bc6d86fbd4a83` on Everything and By Day) | Claude `VC-18`; contrast with PCOA-FINAL-014 |
| **TSN normalization fidelity** | Intersection Detail: all 16,626 raw rows project to the 38-column library with zero differences across 631,788 cells. Ramp Detail: all 15,410 rows match raw field-for-field. Clean Road: 60,083 × 74 with zero changed, missing or extra cells | Codex `intersection-detail-tsn-normalization-parity.json`, `ramp-detail-tsn-normalization-parity.json`, `clean-road-highway-tsn-normalization-parity.json` |
| **Consolidation completeness** | App-independent raw-XLSX audit of complete typed row multisets across 8 datasets and 288,800 raw rows: zero missing, zero extra consolidated rows | Codex `tabular-consolidation-raw-cell-parity.json` |
| **PDF editions reproduce their Excel siblings** | Intersection Detail cross-environment differs by **one cell** in 559,606; Intersection Detail vs TSN is byte-identical. Against TSN the PDF editions pair *better* (Highway Log +634 rows, Highway Sequence +433) — the premise the PDF consolidators exist for | Claude `VC-13` |
| **Prior 7.9 Highway Log PDF-only rows are source truth** | Route 074 at `000.000` occurrence 2 and route 101 at `R022.828` exist in the raw PDF and not in its Excel sibling; the PDF-derived universe correctly retains both | Codex `prior-7.9-highway-log-sibling-raw-source-audit.json`; Stage 2 `SR-02` |
| **One-sided classes are disclosed, not dropped** | The vs-TSN *Summary by Category* sheet states TSN-only bookkeeping classes in prose and counts them in the typed outcome; TSMIS `+ - INVALID DATA` = 2,620 vs TSN 0 is surfaced | Claude `VC-5`, `VC-9` |
| **Intersection Detail header canonicalization** | 16,328 differing rows concentrate in **4 of 35** columns with the other 31 at exactly 0 — a position misalignment would scatter across all 35. A genuine site-side correction, reported truthfully | Claude `VC-12` |
| **Clean Road ArcGIS build rule fidelity** | Exactly rule-faithful across 57,728 rows, 252 routes, 74 fields, 4,271,872 cells, zero mismatches or duplicate keys. **The build rule is not the defect in PCOA-FINAL-010** | Codex `clean-road-highway-raw-source-truth.json` |
| **The product already gets evidence prohibition right on 2 of 3 paths** | The classic Compare tab and the PDF-vs-Excel by-day matrix write no evidence for the same comparison that `matrix_build._run_self_evidence` illustrates | Claude, PCOA-CL-010 decisive contrast |

## Deferred tests and unavailable scope

| ID | Item | Reason deferred | Trigger to revisit |
|---|---|---|---|
| **DEF-01** | Permanent/main-site parity | The frozen archive is a **development-site** SSOR-prod export. Equivalence is not established and must not be silently assumed | A review-ready permanent-site export is supplied |
| **DEF-02** | Highway Detail and Highway Detail (PDF) — 14 decisions | Absent from the frozen archive; greyed out on the dev site; owner-declared **pre-release**, and no artifact on disk is ground truth | The vendor delivers official review-ready Highway Detail exports. Same trigger reopens CMP-AUD-133 / 142 / 186 / 192 and 045-HD |
| **DEF-03** | Baseline Intersection Detail and Intersection Detail (PDF) — 2 decisions | Baseline's same-environment day model cannot select the supplied prior ARS source, and the retained SSOR folder is empty | A prior **SSOR-prod** Intersection Detail export for a second day |
| **DEF-04** | Highway Summary comparison coverage | Still `cs-disabled` on prod and dev; no schema can be verified | The site un-greys it and a statewide export can be pulled |
| **DEF-05** | Clean Road Intersection and Clean Road Ramp | `tsn_load_clean_road` has no normalizer; the library rebuild refuses both by design | Their ArcGIS-side build and comparison are integrated on the Highway pattern |

## Joint approval

| Reviewer | Decision | Commit | Date | Notes |
|---|---|---|---|---|
| Claude | **APPROVED (first Stage 2 cross-check)** | `aa0d086` | 2026-07-26 | 22 canonical records; every Stage 1 finding mapped |
| Codex | **APPROVED (final Stage 2 cross-check)** | this commit | 2026-07-26 | Challenged every resolution; corrected evidence scope, closed all four formerly open issues, and found no open conflict |

Stage 3 is unblocked. Run
[Prompt 03 — agree implementation plan](prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md).
