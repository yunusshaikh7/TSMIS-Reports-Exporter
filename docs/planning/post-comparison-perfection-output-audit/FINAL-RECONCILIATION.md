# Final Reconciliation — Post-Comparison-Perfection Output Audit

> Workflow artifact: **Stage 2 — independent-audit cross-check**
>
> Status: **AWAITING SECOND REVIEW**
>
> Authority: This becomes the joint decision ledger only after both reviewers
> sign it. Claude has completed the first Stage 2 cross-check; every resolution
> below is provisional until Codex challenges it.
>
> New-chat entry point: [START-HERE.md](START-HERE.md). The second reviewer
> continues on this same branch with
> [Prompt 02 — cross-check and final findings](prompts/PROMPT-02-CROSSCHECK-AND-FINAL-FINDINGS.md).

## Stage 2 sign-off

| Reviewer | Pass | Status | Commit | Notes |
|---|---|---|---|---|
| Claude | **First cross-check** | **SIGNED — AWAITING SECOND REVIEW** | this commit | Filled the conflict matrix, ran three bounded rechecks, built `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` |
| Codex | **Final challenge** | NOT STARTED | PENDING | Must independently challenge every resolution below, especially R-01, R-04, R-06 and R-09 |

**Reviewer-order note.** The template assigned Codex the first cross-check and
Claude the challenge. The actual order is reversed: Codex's Stage 2 sign-off was
`NOT STARTED` when Prompt 02 was invoked in a Claude chat, so Claude is the first
Stage 2 reviewer under the prompt's own rule ("If you are the first Stage 2
reviewer, fill the documents, sign your section, mark both files `AWAITING SECOND
REVIEW`, commit, and stop"). The role labels above record the real order. Codex
owes the second, adversarial pass and must not simply ratify this file.

## Precondition verification

| Precondition | Result | Evidence |
|---|---|---|
| Codex Stage 1A complete | **PASS** | `MASTER-VERIFICATION.md` and `CODEX-FINDINGS.md` both read `COMPLETE AND FROZEN` |
| Claude Stage 1B is `CLAUDE ROUND 1 COMPLETE — EMBARGO MAY END` | **PASS** | `claude/post-comparison-output-audit` @ `edf307d`; freeze commit `c788b29` |
| Both independent artifact roots still exist | **PASS** | Codex `…\_scratch\post-comparison-perfection-output-audit-2026-07-23\` (21 subtrees incl. `generated-comparisons`, `source-audit`, `run-ledgers`, `visual-review`, `handoff-docs`); Claude `…\_scratch\post-comparison-output-audit-claude-independent-2026-07-23\` (`generated-comparisons`, `everything-dest`, `inspection`, `witness`, `raw-extract`) |
| Both audits have terminal 88-decision and evidence matrices | **PASS** | Codex 68/16/4 and 16/6/3; Claude 40/26/18/4 and 1/9/2/13. No `UNVERIFIED` cell remains in either |
| No implementation has started | **PASS** | `main` @ `617bd52`; the only branch commits are documentation and witness files |

Frozen-input identity re-verified independently in Stage 2:
`2026-07-23 ssor-prod.zip` → SHA-256
`217F172F7EF7DB527A1EF30E2BFD12D1D6B810BCA55C0D38B7733CB4BE74266F`,
152,681,267 bytes, 2,393 zip members with no duplicate path. This reproduces the
hash Codex froze in `MASTER-VERIFICATION.md` exactly.

**Provenance confirmed (prompt item 9).** The frozen archive came from the
**development site of SSOR-prod**. Permanent/main-site equivalence is *not*
established by this audit and remains future work; it is carried as a deferred
item in `FINAL-FINDINGS-FOR-IMPLEMENTATION.md`, not as a closed check.

## Stage 2 bounded rechecks

Three conflicts could not be resolved from the two narratives because they turned
on facts neither round had measured the same way. Each was rechecked in Stage 2
and retained in a neutral witness folder:
`C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-output-audit-stage2-reconciliation\`.

| ID | Question | Method | Result |
|---|---|---|---|
| **RC-1** | Is the visible-text clipping of `PCOA-CX-013` / `PCOA-CX-014` real, given Claude's `VC-14` "presentation contracts hold"? | `measure_clipping.py` over **Claude's** retained workbooks — real Calibri 11 glyph metrics (PIL), Excel's own width→pixel model, 6 px tolerance, and a deliberately conservative gate that reports a cell **only** when it cannot spill (no wrap, no shrink-to-fit, populated right neighbour, merged ranges credited with full width) | **CLIPPING CONFIRMED.** Ramp Summary vs TSN 33 cells, Intersection Summary vs TSN 70, Ramp Summary env 5, Ramp Detail (PDF) vs TSN 78, Highway Sequence (PDF) self 82. The `Comparison` category column measures **89 px** — Codex's exact figure — against labels needing up to 309 px. `Spot Check!B6` is 55–76 px short; `Summary!B13:B14` 47–364 px short; the composite `Key` column 8–33 px short. Witness `witness\clipping_recheck.json` |
| **RC-2** | Is Everything TSN `highway_sequence_pdf` evidence approvable (Claude `APPROVED`, Codex `DENIED`)? | Direct full-resolution inspection of all three FT layouts in **Claude's own** retained image set | **CODEX CONFIRMED.** `FT_3_stacked.png` (route 092 @ ALA 006.798, caption *TSMIS 'H' vs TSN '(blank)'*) draws the red TSN target around the final **`O`** of the printed `EQUATES TO` — precisely the defect Codex reported on a *different* sampled row in a *different* run. `FT_1`/`FT_2` (blank on the **TSMIS** side) are correct. Claude inspected 2 of 12 at full resolution and missed it |
| **RC-3** | Does the false "rebuild the TSN library" warning reach Everything as well as By Day (Codex 12 workbooks, Claude 20 decisions)? | Two independent readers over all 36 matrix-lane vs-TSN workbooks: a zip/sheet-XML probe and an openpyxl cell walk | **CLAUDE CONFIRMED, both scopes sharpened.** Identical results from both methods: **24 of 36 workbooks warn** (12 By Day + 12 Everything) at exactly Codex's cells — `Summary by Category!A6`, `!A7`, `Notes!A9`, `Notes!A4`. **All 36** disclose the `%TEMP%` capture path. The 12 clean workbooks are Intersection Detail, Intersection Detail (PDF) and Ramp Detail (PDF) — the three families that expose no TSN identity on any path. Direct-lane workbooks: 0 warnings, 0 temp paths. Witness `witness\tsn_provenance_warning_scope.json` |

**Stage 2 witnesses are committed with these documents** so the second reviewer
can challenge them without rebuilding anything:

| In-repo witness | Contents |
|---|---|
| [`stage2-measure-clipping.py`](stage2-measure-clipping.py) | The RC-1 measurement tool, with its conservative gate documented in the module docstring |
| [`stage2-clipping-recheck.json`](stage2-clipping-recheck.json) | Every one of the **268** materially clipped cells across the five measured workbooks, each with available px, needed px, shortfall, character count and the exact text |
| [`stage2-tsn-provenance-scope.json`](stage2-tsn-provenance-scope.json) | All 36 matrix-lane vs-TSN workbooks classified for both the false warning and the `%TEMP%` path, plus the clean Direct-lane control |

RC-1 is reproducible with:

```bash
python docs/planning/post-comparison-perfection-output-audit/stage2-measure-clipping.py "<workbook>.xlsx"
```

## Topology reconciliation

### The 88-decision deliverable topology

Both rounds partition the same 88 decisions and both reconcile to 88 with no open
cell. The partitions are presented differently but are cell-for-cell equivalent:

| Scope-document workflow | Decisions | Codex matrix | Claude matrix |
|---|---:|---|---|
| Classic current-vs-prior environment | 12 | A | A |
| Direct TSMIS-vs-TSN | 12 | B (`Direct`) | B (`Direct`) |
| Production By Day TSMIS-vs-TSN | 12 | B (`By Day`) | B (`By Day`) |
| Production Everything TSMIS-vs-TSN | 12 | B (`Everything`) | B (`Everything`) |
| Production Baseline environment | 12 | C (`Baseline`) | C (`Baseline`) |
| Production Everything environment | 12 | C (`Everything ENV`) | C (`Everything ENV`) |
| Direct same-day PDF-vs-Excel self | 7 | D (`Direct self`) | D (`Direct`) |
| Production Everything self | 7 | D (`Everything SELF`) | D (`Everything SELF`) |
| Clean Road Highway values + formulas | 2 | F | F |
| **Total** | **88** | | |

Clean Road Intersection and Clean Road Ramp are `N/A` **outside** this topology in
both rounds — `tsn_load_clean_road` has no normalizer for either and the library
rebuild refuses them by design. Neither auditor invented a comparison path. This
is a full agreement.

### The 25-cell Everything evidence registry

The neutral scope document fixes this registry at **environment 10, TSN 10,
self 5**. Claude's evidence matrix follows that partition exactly. Codex's
Matrix E is a **superset** presentation: it interleaves production By Day
evidence rows and several roll-up rows ("Excel vs TSN, including summary rows",
"Direct/classic comparators", "Baseline …") alongside the 25, while its prose
correctly states the registry is 25 and closes at 16/6/3.

**Resolution:** the joint registry is rebuilt on the scope document's 10/10/5
partition. Codex's By Day evidence observations are preserved — they are the
same product behaviour on a second dispatch path and are carried as scope inside
the canonical findings, not as extra registry cells.

## Conflict matrix

Every non-identical result, not only explicit disagreements. `=` means the two
rounds produced the same fact and the same verdict.

| ID | Report / workflow / gate | Codex | Claude | Recheck owner | Resolution and evidence |
|---|---|---|---|---|---|
| **R-01** | **All produced values/formulas twins — visible-text clipping** | DENIED (CX-013: 24 workbooks / 748 cells; CX-014: 41 pairs / 82 workbooks) | Not audited; `VC-14` reports "presentation contracts hold … no clipping" | Claude (RC-1) | **CODEX UPHELD.** Not a contradiction — a **scope gap**. `VC-14` measured the *data* columns (explicit width 13.0), the 45.75 pt wrapped header row, mask/snapshot hidden states and filter ranges, and is correct about all of them; it never measured `Summary`, `Spot Check` or the `Comparison` category/key label cells. RC-1 measured exactly those and reproduced Codex's 89 px figure to the pixel. Claude's own note that an early clipped-header probe was "an artifact of reading `column_dimensions.items()`" is about **headers** and does not cover these cells |
| **R-02** | Matrix A Intersection Detail and Intersection Detail (PDF) | DENIED (judged against the retained **ARS** 7.9 prior: 17,563 / 17,562 cells) | BLOCKED (no prior **SSOR** Intersection Detail; the ARS pair recorded as a "labelled secondary column" and judged in Matrix C instead) | Claude | **CODEX UPHELD on assignment.** Both rounds produced the comparison and agree on its counts to the cell. Under the shared verdict legend `BLOCKED` means "a required review-ready source is unavailable"; the ARS prior **is** review-ready and both auditors used it. A cell whose deliverable exists cannot be `BLOCKED`. Joint `BLOCKED` total is therefore **16**, not 18. Claude's stricter same-source reading is recorded, not discarded: the absence of a prior **SSOR** Intersection Detail pair is real and is carried as a deferred source item |
| **R-03** | Baseline Intersection Detail and Intersection Detail (PDF) | BLOCKED | BLOCKED | — | `=` Full agreement, same reason: Baseline's same-environment day model cannot select the supplied prior ARS source. This is a source/workflow limitation, not a missing file in the new bundle |
| **R-04** | Everything TSN `highway_sequence_pdf` evidence | DENIED (8/12 accurate; FT ex. 2 and 3 box the final `O` of `EQUATES TO`) | **APPROVED** (12 images, 2 inspected at full resolution) | Claude (RC-2) | **CODEX UPHELD.** RC-2 reproduced the defect in **Claude's own** image set on a different sampled row. Claude's single evidence approval is withdrawn. Because the two runs sampled different rows and still both exhibit it, the defect is a property of the **population**, not of one sample |
| **R-05** | Everything TSN `highway_log_pdf` evidence | **APPROVED** (final Everything set 180/180) | DENIED (`Description_1_stacked.png`, route 140 @ R029.757: blank TSN Description boxes the *next* record) | Claude | **CLAUDE UPHELD.** Same family, same defect class as R-04, demonstrated on Claude's independent Everything run; Codex independently demonstrated it on its By Day run (route 395 @ `T121.831`). Codex's 180/180 pass is a **sampling** outcome — its own set happened not to draw a blank-Description example. A cell that passes only when the sample misses the defect cannot be approved |
| **R-06** | Everything TSN `ramp_summary` evidence eligibility | REQUIRED → DENIED (absent) | PROHIBITED → N/A | **Codex (open)** | **CODEX ADOPTED, with the rule ambiguity referred to the owner.** Ramp Summary's TSMIS side consolidates 126 route PDFs and its TSN library raw *is* `Ramp Summary Statewide_TSN.pdf` — structurally identical to Highway Log / Highway Sequence, which **both** rounds call `REQUIRED`. Claude's contrary test (`visual_evidence._TSN_PDFS_IN_RAW`) describes what the product currently does, not what the rule requires. **Unresolved underneath:** the neutral rule's literal words ("PDF-vs-normalized-XLSX is prohibited") would prohibit *every* vs-TSN evidence cell including HL/HSL, which neither round adopted. See UN-01 |
| **R-07** | 5 Everything ENV PDF/PDF evidence cells (`ramp_summary`, `intersection_detail_pdf`, `ramp_detail_pdf`, `highway_log_pdf`, `highway_sequence_pdf`) | DENIED — required, positive differences, zero artifacts | N/A — no env evidence code path exists at all | Claude | **CODEX ADOPTED on the label; CLAUDE ADOPTED on the cause.** Identical fact, independently established twice: no evidence artifact exists anywhere under the env, baseline or PDF-vs-Excel trees, and `matrix_build.build_cell_comparison` takes no evidence argument. Scope rule 12 makes an eligible positive-difference PDF/PDF comparison *require* evidence, so absent-and-required is `DENIED`. Claude's mechanism (an unimplemented capability, not a failed one) is the part implementation needs and is preserved in the canonical finding |
| **R-08** | 4–5 Everything ENV Excel-sided evidence cells | APPROVED (clean prohibited absence) | N/A | Claude | **CODEX ADOPTED.** The comparison exists, evidence is correctly prohibited, and nothing leaked — that is a **pass**, not an inapplicable cell. Marking it `N/A` would lose the fact that the product got these right |
| **R-09** | Highway Sequence PDF-vs-Excel self check | DENIED — all 3,714 cells / 1,395 rows are `EQUATES TO` representation; corpus-wide canonicalization of all 1,119 relations yields **zero** differences | APPROVED — same 3,714 / 1,395 and same per-field split (PM Suffix 547 · HG 929 · FT 1,119 · Description 1,119); "which edition is right needs source adjudication — recorded, not attributed" | **Codex (open)** | **CODEX UPHELD.** The two rounds agree on every published number; Claude explicitly declined the source adjudication and Codex performed it over the full corpus with zero unsupported cases. A **same-day, same-pull** self check exists to detect real divergence, so publishing 3,714 representation-only differences is a defect in the self leg — especially since the product already discloses equation relations in the vs-TSN `Notes`. Codex should re-verify its canonicalization in the second pass |
| **R-10** | Clean Road Highway values/formulas | DENIED — 102 live `LocError=NO ERROR` rows silently skipped → 161 exact false positives + 4 genuine differences shown with a false blank ArcGIS side; Summary/Notes disclose none of it | APPROVED — reproduces the blessed `CRH-SW-E2` canary exactly (52,647 / 5,081 / 7,436 / 291,292) | **Codex (open)** | **CODEX UPHELD.** This is the archetype the prompt warns about: Claude's approval rests on internal consistency plus agreement with the repo's own historical canary, which scope rule 8 explicitly forbids as sufficient, and Claude did not audit the ArcGIS build against the raw layers at all. Codex did, via an exact `Key (helper)` → `__CMP_E2_KEY_V1_TOKEN` join that infers no missing span. The canary is **not** invalidated — it was blessed on the same builder rule; what is new is that the rule's silent omissions surface as displayed differences |
| **R-11** | Highway Log vs TSN — 1,243 punctuation-only Description cells per format | DENIED — false positives; the workbook "overstates differing cells by exactly 1,243" | Not audited (`VC-16` covers only the 99 Highway Sequence **cross-environment** Description cells) | **Owner (open)** | **FACT CONFIRMED; CHARACTERIZATION REFERRED.** The 1,243 token-identical-modulo-punctuation pairs (`… , …` vs `… / …`) are real and are counted as differences. Whether the engine *should* normalise them is a domain-contract decision reserved to the owner under the `compare_core` correctness lock — a comparator that faithfully reports two sources literally differing is not lying. Recorded as a disclosure/normalisation decision, not as a proven engine defect. See UN-02 |
| **R-12** | 26 formatting-only Description cells (HSL 11 ×2 formats, RD-PDF 2, ID 1 ×2 formats) | DENIED (CX-010) | Not audited | **Owner (open)** | Same class as R-11. Note a live tension the owner should weigh: the Intersection Detail pair `''F'' ST` vs `"F" ST` is the KER 046 @ 50.904 case the product **already deliberately annotates** via the evidence `_quote_note` — i.e. it has previously been treated as worth *showing*, not suppressing |
| **R-13** | Clean Road 5 landmark formatting-only cells | DENIED (CX-012) | Not audited | **Owner (open)** | Same class as R-11/R-12 |
| **R-14** | Ramp Detail self check — 108 null-token cells | DENIED, "masked by CX-005" | Not reachable (comparison refused) | Codex | **CODEX UPHELD as latent.** Distinct from R-11/R-13: this is an **asymmetry**, not a normalisation preference. The PDF consolidator already projects `-` / `NO RAMP LINEAR EVENT` to blank while the Excel side does not, so the *same* source renders differently on the two legs of a same-source check. Will surface the moment the header gate is fixed |
| **R-15** | Ramp Detail Excel layout refused end to end | CX-001 / CX-002 / CX-005 (split by workflow) | PCOA-CL-001 / CL-004 (one finding + the message defect) | — | `=` Full agreement on behaviour, header census, affected cells, and that refusal is the *correct* engine response to a stale pinned header. Claude adds two facts Codex does not have: `consolidate_ramp_detail.consolidate` nevertheless **succeeds** (126/126, `status=ok`) and writes a workbook no comparator accepts; and the refusal message misdiagnoses. Merged into one canonical finding preserving all scope |
| **R-16** | False "rebuild the TSN library" warning | CX-003 — 12 By Day workbooks | PCOA-CL-002 — By Day **and** Everything, 20 decisions | Claude (RC-3) | **CLAUDE UPHELD.** RC-3, by two independent readers: **24 workbooks** warn (12 By Day + 12 Everything). Codex under-scoped to one lane; Claude's mechanism (`matrix_build.captured_tsn_workbook` writes a reduced 159-byte sidecar in place of the library's 1,224-byte one, dropping `tsn_source_claims`) explains both lanes. Codex's exact cell addresses are adopted into the canonical finding |
| **R-17** | `%TEMP%` capture path named as the TSN input | Not reported | PCOA-CL-003 | Claude (RC-3) | **CLAUDE UPHELD and widened.** All **36** matrix-lane vs-TSN workbooks disclose a `…\Temp\tsmis-tsn-consumer-*\…` path in `Provenance` — including the 12 that do *not* print the rebuild warning. Unique to Claude |
| **R-18** | Excel-side evidence panels truncated at 26 characters | Observed as symptoms — "two truncated TSMIS crops" (HSL), "four truncate the captioned TSMIS Description" (HL) | PCOA-CL-015 — root cause at `visual_evidence.py:1270` (`text[:26]`, no ellipsis), census 8 of 190 rendered examples | — | `=` Same defect found independently on different image sets. Claude's code-level root cause is adopted; Codex's independent sightings on two further sets corroborate it |
| **R-19** | Prohibited mixed-source evidence generated | CX-009 — 14 artifact sets, 1,394 PNGs reviewed | PCOA-CL-010 — 9 prohibited cells | — | `=` Strong independent agreement, including the same corrective test stated in both rounds: Claude — "every read-set member is the document the corresponding side was compared from, not … is a PDF"; Codex — the renderer "opportunistically borrowed" a sibling TSN PDF. Claude's `intersection_detail_pdf` case (80 PDFs, zero XLSX, still wrong) is the decisive proof that a PDF-only read set is insufficient |
| **R-20** | Route 140 Highway Log **Excel** export missing whole columns | Recorded inside "Highway Log same-day sibling approval" as verified source truth, not a finding | PCOA-CL-017 — P1, source-side, owner must act with the vendor | — | `=` Independently identical (213 rows; `R/U`, `TER`, `H/G`, `A/C` blank in Excel, printed in the PDF). Carried as a **source-side** canonical finding: no product code change, vendor action required |
| **R-21** | Context columns reported as `0` in *DIFFERENCES BY FIELD* | Not reported | PCOA-CL-011 | — | Unique to Claude. Well evidenced: `City / HG / Distance To Next Point` show `0` while being wholly context (`context_cells = 171,150`), and the evidence images themselves show a real Distance difference at route 101 @ MEN R101.895 |
| **R-22** | Empty second side found only after the first side is fully parsed | Not reported | PCOA-CL-012 — 429.4 s / 438.6 s / 1,229.7 s | — | Unique to Claude |
| **R-23** | `%TEMP%` capture directories left behind | Not reported | PCOA-CL-005 | — | Unique to Claude |
| **R-24** | TSN normalization not identity-deterministic | Not reported | PCOA-CL-006 (root cause explicitly labelled a hypothesis) | — | Unique to Claude. The hypothesis label is preserved verbatim in the canonical finding |
| **R-25** | Three enabled editions with no verification path (343 of 2,380 files) | Not reported | PCOA-CL-007 | — | Unique to Claude |
| **R-26** | Values-twin headline is an uncached formula | Observed and **dismissed** — "not representative … `fullCalcOnLoad=True`, and installed Excel recalculates every SELF-CHECK result to `OK`" | PCOA-CL-008 — P3 defect for consumers that do not recalculate | — | **BOTH RETAINED.** Fact agreed. Kept at the lowest severity with Codex's mitigation stated in the finding itself, so implementation can see it is cosmetic for Excel users and material only for non-recalculating readers |
| **R-27** | Highway Log PDF/Excel row-universe delta | Route 005 and route 140 traced inside the self-check approval | PCOA-CL-013 — whole delta localized to 4 routes (005, 074, 101, 140), net −14/+2 | — | `=` Complementary and mutually consistent. Two of the four routes are attributed to real source defects; the two single-row residuals (074, 101) are **not** attributed by either round — carried as a residual recheck item |
| **R-28** | Site-side export changes in the frozen archive | Not reported | PCOA-CL-009 — explicitly "recorded, not a product defect"; the HSL PDF re-skin is absorbed by the parser | — | Unique to Claude. Recorded as a **no-fix / must-not-regress** item, not a defect |
| **R-29** | Workflow parity across dispatch paths | "Final isolated Everything typed results match Direct and By Day" throughout | `VC-11` — exact parity on every measurable family across classic / Baseline / Everything ENV, Direct / By Day / Everything TSN, and all three self paths | — | `=` **High-value agreement.** Independently established twice on independently generated artifacts |
| **R-30** | Formula twins vs values twins under installed Excel | 60/60 pairs, 313,497,190 compared cells, zero unexpected mismatches | `VC-3` — 15,756,782 cells, 0 real differences, 0 Excel errors | — | `=` Agreement at very different scales, same conclusion. Per prompt item 5 this agreement is **not** treated as proof of deliverable quality: both used installed Excel on workbooks produced by the same writer, and both rounds state explicitly that formula approval does not override any report-level denial |

### Challenged high-risk agreements (prompt item 5)

| Agreement | Why it was challenged | Outcome |
|---|---|---|
| Both rounds approve Highway Log / Highway Sequence **PDF** vs TSN as evidence-`REQUIRED` | Both may be inheriting the same product assumption (`_TSN_PDFS_IN_RAW`) rather than the neutral rule, whose literal words prohibit PDF-vs-normalized-XLSX | **Not resolvable from source; referred to the owner as UN-01.** It does not change any verdict here — both cells are `DENIED` on crop accuracy regardless of which reading applies |
| Both rounds reproduce the same discrepancy counts on every measurable family | Both drove the same application comparators, so identical counts prove reproducibility, not correctness | Held: correctness rests on the *independent* recounts (Claude's app-free readers; Codex's raw-source traces), which were performed separately and agree — e.g. Intersection Summary 217/7/16 to the cell from two independent readers |
| Both rounds treat Clean Road Intersection / Ramp as `N/A` | Could be a shared assumption that the refusal is intentional | Held on source: `tsn_load_clean_road` has no normalizer and the rebuild refuses both by design with an explicit message. Neither auditor invented a path |
| Codex's `291,292` and Claude's `291,292` Clean Road differing cells | Identical to the digit — could be mutual canary reuse | Held as a *reproducibility* fact only. It is explicitly **not** treated as approval: R-10 denies the deliverable on source grounds Claude never audited |

## Agreed deliverable matrix — exact terminal totals

### 88-decision topology

| Matrix | Expected | Approved | Denied | Blocked | N/A |
|---|---:|---:|---:|---:|---:|
| A — classic environment | 12 | 0 | 10 | 2 | 0 |
| B — TSMIS vs TSN (Direct / By Day / Everything) | 36 | 0 | 30 | 6 | 0 |
| C — Baseline and Everything ENV | 24 | 0 | 18 | 6 | 0 |
| D — same-day PDF vs Excel self | 14 | 0 | 8 | 2 | 4 |
| F — Clean Road Highway | 2 | 0 | 2 | 0 | 0 |
| **Total** | **88** | **0** | **68** | **16** | **4** |

Matrix A blocked: Highway Detail, Highway Detail (PDF) — the two Intersection
Detail cells move to `DENIED` under R-02. Matrix B blocked: Highway Detail and
Highway Detail (PDF) × 3 workflows. Matrix C blocked: Highway Detail and Highway
Detail (PDF) × 2 workflows, plus Baseline Intersection Detail and Baseline
Intersection Detail (PDF). Matrix D blocked: Highway Detail × 2.

**The joint topology closes at Codex's 68 / 16 / 4.** Of Claude's 40 approvals,
**36 are not overturned on their merits** — they are approvals of *arithmetic and
source truth*, they survive intact, and they are outranked only by a presentation
gate Claude never ran and Stage 2 confirmed (R-01). The remaining **4 are
genuinely overturned**: Clean Road values and formulas on R-10, and Highway
Sequence self Direct and Everything on R-09. Both reversals rest on source work
Codex performed and Claude did not attempt.

### Why each of the 68 denials stands — the distinction implementation needs

Codex's uniform `DENIED` is correct but hides that most of these cells are
numerically sound. Recording the reason set separately is the single most useful
output of this cross-check.

| Denial reason | Decisions | Numeric/source truth independently approved? |
|---|---:|---|
| No deliverable produced at all (Ramp Detail Excel-side refusal) | 8 | n/a — nothing to approve |
| Presentation clipping **only** | 38 | **Yes** — approved on source, recount, discrepancy truth and formula parity |
| Presentation clipping **+** false TSN provenance narration **+** `%TEMP%` path | 12 | Yes on numbers; the workbook's provenance prose is false |
| Presentation clipping **+** `%TEMP%` provenance path only | 6 | Yes on numbers |
| Substantive semantic finding — Clean Road skipped rows (2), Highway Sequence self equation projection (2) | 4 | **No** — the published differences are wrong or unexplained |
| **Total** | **68** | |

The 38 clipping-only decisions are 36 of Claude's 40 approvals (its Clean Road
and Highway Sequence-self approvals move to the substantive row) plus the two
Matrix A Intersection Detail cells that R-02 converts from `BLOCKED` to judged.

Read plainly: **the comparison engine's truth held everywhere both rounds could
measure it; the deliverables fail on what they look like and what they say about
themselves.** Fixing the stored column widths alone would make **38 of the 68**
decisions approvable without touching a single comparison semantic; fixing the
capture-step provenance would carry another 18 with it.

### 25-cell Everything evidence registry

Rebuilt on the scope document's 10 / 10 / 5 partition.

| Mode | Report key | Eligibility | Verdict | Basis |
|---|---|---|---|---|
| ENV | `ramp_summary` | REQUIRED | DENIED | Positive differences, zero artifacts (R-07) |
| ENV | `ramp_detail` | — | N/A | Comparison refused before evidence |
| ENV | `intersection_summary` | PROHIBITED | APPROVED | Correctly absent (R-08) |
| ENV | `intersection_detail` | PROHIBITED | APPROVED | Correctly absent |
| ENV | `intersection_detail_pdf` | REQUIRED | DENIED | 17,562 differing cells, zero artifacts |
| ENV | `ramp_detail_pdf` | REQUIRED | DENIED | 376 cells + 5/8 one-sided, zero artifacts |
| ENV | `highway_sequence` | PROHIBITED | APPROVED | Correctly absent |
| ENV | `highway_log` | PROHIBITED | APPROVED | Correctly absent |
| ENV | `highway_log_pdf` | REQUIRED | DENIED | 88,238 cells + 2,095/1,174 one-sided, zero artifacts |
| ENV | `highway_sequence_pdf` | REQUIRED | DENIED | 1,904 cells + 7/246 one-sided, zero artifacts |
| TSN | `ramp_summary` | REQUIRED (R-06) | DENIED | Positive differences, zero artifacts |
| TSN | `ramp_detail` | — | N/A | Comparison refused before evidence |
| TSN | `intersection_summary` | PROHIBITED | APPROVED | Correctly absent |
| TSN | `intersection_detail` | PROHIBITED | DENIED | Prohibited generation, 140–142 images; 2 `Control Type` targets box printed `P` while claiming `S` |
| TSN | `intersection_detail_pdf` | PROHIBITED | DENIED | Prohibited generation, PDF-only read set but the TSN panel is a document never compared |
| TSN | `ramp_detail_pdf` | PROHIBITED | DENIED | Prohibited generation, 50 images |
| TSN | `highway_sequence` | PROHIBITED | DENIED | Prohibited generation, wrong targets and truncated values |
| TSN | `highway_log` | PROHIBITED | DENIED | Prohibited generation, wrong targets and truncated values |
| TSN | `highway_log_pdf` | REQUIRED | DENIED | Blank TSN Description boxes the next record (R-05) |
| TSN | `highway_sequence_pdf` | REQUIRED | DENIED | Blank TSN FT boxes the final `O` of `EQUATES TO` (R-04, RC-2) |
| SELF | `ramp_detail_pdf` | — | N/A | Comparison refused before evidence |
| SELF | `highway_sequence_pdf` | PROHIBITED | DENIED | Prohibited generation, 18 images |
| SELF | `intersection_detail_pdf` | PROHIBITED | DENIED | Manifest-only emission on a zero-difference result. **Mildest instance** — Claude judged it compliant because the read set is empty, the images are zero and the note is accurate. Retained as `DENIED` only for consistency with "do not begin evidence for a prohibited pair" |
| SELF | `highway_log` | PROHIBITED | DENIED | Prohibited generation, 164 images |
| SELF | `highway_log_pdf` | PROHIBITED | DENIED | Prohibited generation, 164 images |

| Expected | Approved | Denied | N/A |
|---:|---:|---:|---:|
| 25 | 5 | 17 | 3 |

Difference from Codex's 16/6/3: exactly one cell — Everything TSN
`highway_log_pdf` moves `APPROVED` → `DENIED` under R-05.
Difference from Claude's 1/9/2/13: Claude's `N/A` category absorbed both the
clean prohibited absences (now `APPROVED`, R-08) and the required-but-absent env
cells (now `DENIED`, R-07), and its one approval is withdrawn (R-04).

**No evidence bundle in this audit is deliverable-ready.** The five approvals are
all approvals of *correct absence*.

## Blocked deliverables — preserved separately

| Item | Decisions | Why blocked | What would unblock it |
|---|---:|---|---|
| Highway Detail and Highway Detail (PDF), all workflows | 14 | Absent from the frozen archive (`highway_detail`, `highway_detail_pdf`, `highway_summary` folders do not exist); the report is greyed out on the dev site and is owner-declared **pre-release**. Historical files do not make it review-ready | The vendor delivers official, review-ready Highway Detail exports on integration. That delivery is also the trigger to re-verify the schema and reopen CMP-AUD-133/142/186/192 and 045-HD |
| Baseline Intersection Detail | 1 | Baseline's same-environment day model cannot select the supplied prior **ARS** source, and the retained SSOR `intersection_detail` folder is empty | A prior **SSOR-prod** Intersection Detail export for a second day, or a Baseline model that can address a cross-source prior |
| Baseline Intersection Detail (PDF) | 1 | Same | Same |
| **Total** | **16** | | |

## Not applicable — preserved separately

| Item | Decisions | Why |
|---|---:|---|
| Direct SELF Ramp Summary / Everything SELF Ramp Summary | 2 | No PDF-vs-Excel comparator is registered, although both editions are exported (126 PDF + 126 XLSX) |
| Direct SELF Intersection Summary / Everything SELF Intersection Summary | 2 | Same, inverted (217 XLSX + 217 PDF) |
| **Total inside the 88** | **4** | |
| Clean Road Intersection, Clean Road Ramp | outside the 88 | Raw files staged; `tsn_load_clean_road` has no normalizer and the library rebuild refuses both by design. No comparison path was invented |

Note that the four in-topology `N/A` cells are the *consequence* of a real
coverage gap (PCOA-FINAL-018) — they are correctly `N/A` for today's product and
should not be read as "nothing to do here".

## Unresolved issues and recheck owners

| ID | Issue | Why it is not resolved here | Owner |
|---|---|---|---|
| **UN-01** | The evidence-eligibility rule is ambiguous. Read literally ("PDF-vs-normalized-XLSX is prohibited") it prohibits *every* vs-TSN evidence cell, including the two both rounds call `REQUIRED`. Read by provenance ("the TSN library raw is a PDF") it permits Ramp Summary, Highway Log and Highway Sequence and prohibits the rest | Two careful auditors read the same neutral sentence differently. This is a contract question, not a fact question, and cannot be settled from source | **Owner**, before any evidence-gating code is written |
| **UN-02** | Whether punctuation/case/quote-only Description differences (R-11, R-12, R-13 — 1,243 + 26 + 5 cells) should be normalised away, disclosed, or left as published | The `compare_core` correctness lock reserves equality/normalisation changes to the approved domain contract. A comparator reporting a literal source difference is not defective by itself | **Owner**, then Codex to re-verify the classification if normalisation is approved |
| **UN-03** | Two single-row Highway Log PDF/Excel residuals (routes 074 and 101) | Neither round attributed them; the other two of the four routes are explained | **Codex** in the second pass, or defer to implementation |
| **UN-04** | Codex's corpus-wide Highway Sequence equation canonicalization (R-09) is the sole basis for denying an otherwise-approved cell | Claude produced the identical counts but explicitly declined the adjudication, so this resolution currently rests on one round only | **Codex** must re-state its method in the second pass so Claude can challenge it |
| **UN-05** | Permanent/main-site equivalence | The frozen archive is a **development-site** SSOR-prod export | **Owner** — supply a review-ready permanent-site export |

## Findings mapped — every Stage 1 finding accounted for

Every `PCOA-CX-*` and `PCOA-CL-*` maps to exactly one canonical ID in
`FINAL-FINDINGS-FOR-IMPLEMENTATION.md`, or is recorded there as a no-fix item.
No Stage 1 finding was rejected.

| Stage 1 ID | Canonical | Stage 1 ID | Canonical |
|---|---|---|---|
| PCOA-CX-001 | PCOA-FINAL-001 | PCOA-CL-001 | PCOA-FINAL-001 |
| PCOA-CX-002 | PCOA-FINAL-001 | PCOA-CL-002 | PCOA-FINAL-002 |
| PCOA-CX-003 | PCOA-FINAL-002 | PCOA-CL-003 | PCOA-FINAL-003 |
| PCOA-CX-004 | PCOA-FINAL-007 | PCOA-CL-004 | PCOA-FINAL-001 |
| PCOA-CX-005 | PCOA-FINAL-001 | PCOA-CL-005 | PCOA-FINAL-016 |
| PCOA-CX-006 | PCOA-FINAL-012 | PCOA-CL-006 | PCOA-FINAL-017 |
| PCOA-CX-007 | PCOA-FINAL-011 | PCOA-CL-007 | PCOA-FINAL-018 |
| PCOA-CX-008 | PCOA-FINAL-013 | PCOA-CL-008 | PCOA-FINAL-019 |
| PCOA-CX-009 | PCOA-FINAL-004 + PCOA-FINAL-005 + PCOA-FINAL-006 | PCOA-CL-009 | PCOA-FINAL-022 (no fix) |
| PCOA-CX-010 | PCOA-FINAL-013 | PCOA-CL-010 | PCOA-FINAL-004 |
| PCOA-CX-011 | PCOA-FINAL-005 | PCOA-CL-011 | PCOA-FINAL-014 |
| PCOA-CX-012 | PCOA-FINAL-013 | PCOA-CL-012 | PCOA-FINAL-015 |
| PCOA-CX-013 | PCOA-FINAL-008 | PCOA-CL-013 | PCOA-FINAL-021 |
| PCOA-CX-014 | PCOA-FINAL-009 | PCOA-CL-014 | PCOA-FINAL-007 |
| PCOA-CX-015 | PCOA-FINAL-010 | PCOA-CL-015 | PCOA-FINAL-006 |
| | | PCOA-CL-016 | PCOA-FINAL-005 |
| | | PCOA-CL-017 | PCOA-FINAL-020 |

15 Codex findings + 17 Claude findings → **22 canonical findings**, each covered
exactly once.

## Final release recommendation

**No audited comparison deliverable is approved for release in its current
form.** Both rounds reach that conclusion by different routes and Stage 2 upholds
it: 68 of 88 decisions are `DENIED`, 16 are source-`BLOCKED`, four are `N/A`, and
none of the 25 evidence cells is deliverable-ready.

The joint conclusion is more useful than either round alone. The comparison
engine's **truth** is strong — whole-family independent recounts reproduce it to
the cell from two independent readers, workflow parity is exact across every
dispatch path, and 313 M / 15.7 M recalculated formula cells show zero
disagreement with their values twins. What fails is **presentation** (38 cells
denied on stored column widths alone), **self-description** (24 workbooks giving
a false rebuild instruction, 36 naming a `%TEMP%` path), and **evidence**
(prohibited generation, mislocalized blank targets, truncated Excel panels).

Two substantive semantic defects sit underneath: Clean Road's undisclosed skipped
source rows and the Highway Sequence self check's equation projection. One
finding is not ours to fix at all — the vendor's route 140 Highway Log Excel
export is missing whole columns its own print carries.
