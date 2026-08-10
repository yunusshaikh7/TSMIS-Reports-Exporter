# `RB-4` — Bundle Contract

Status: **JOINTLY APPROVED** at runtime `d826877`. `RB4-R1-001` remains closed
by the owner's narrow anchorless-blank ruling. `RB4-R2-001` — missing required
print sources left prior canonical evidence artifacts in place — is closed by
code: all three exits now retire the prior set through binding refusal. The
committed six assertions and an independent no-folder probe leave workbook,
image folder, and manifest absent; the rebound verifier reports zero problems.
Acceptance run **chain11** passed every phase and its 341-image inspection found
zero failures. Both signed approvals are in [REVIEW.md](REVIEW.md); the remedy
is in [IMPLEMENTATION.md](IMPLEMENTATION.md).

> This RB-level contract carries work items **HF-05 and HF-10** and transcribes
> both complete frozen work-item sections from
> [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md). The plan is
> authoritative; where this record and the plan disagree, the plan wins. This
> readiness step freezes scope only. No RB-4 branch, product change, evidence
> generation, or acceptance run has started.

## ⚠️ Owner amendment — 2026-08-05 (controls wherever it conflicts with the frozen text below)

Mid-implementation, after the first `RB4-A1` run completed, the owner inspected
the generated images and **rejected the HF-05 remedy as implemented**: rendering
a compared side as a panel drawn from the compared workbook is CIRCULAR — a
reviewer looking at it can never catch a bad parse, because the panel and the
comparison sheet share the same read. His ruling: *"the whole point was that the
evidence collection was separate and that if some dude looked at the pdf it
would line up with the comparison sheet — that's the ONLY reason this is even a
valid spot check."* Three rulings, issued in sequence the same day, now control
this bundle:

**1. Evidence is an independent spot check made of PRINT CROPS.** Both sides of
every evidence image are crops of actual prints — the TSMIS per-route PDF
export, the TSN library print, or the other environment's per-route print — with
the red box on the compared cell, parse-back-verified. Workbook cell addresses
may appear in caption text; workbook-rendered panels may not appear anywhere.
A print whose parsed value disagrees with the compared value is rendered **with
a disclosure note**, never silently dropped — disagreement is exactly the
parser-bug signal the spot check exists to catch (the old silent drop was
itself a defect).

**2. Evidence collection EXISTS ONLY for the `_pdf`-edition report families** —
Highway Log (PDF), Highway Sequence (PDF), Intersection Detail (PDF), Ramp
Detail (PDF); Highway Detail (PDF) joins as the fifth family when the owner
lifts his 2026-07-21 pre-release freeze — in exactly three lanes each:
Everything vs-TSN, By Day vs-TSN, Everything ENV. **12 cells total.** The rule
is by REPORT TYPE, not source format: Ramp Summary's env cell is REMOVED from
HF-10's scope even though its export is PDF-native (owner: "get rid of that one
too, evidence collection only for these type of reports, soon highway detail
too"). Everything else — the 8 Excel-row vs-TSN cells and all 5 SELF
(PDF-vs-Excel) cells — is **refused at the engine boundary**: evidence on
produces zero artifacts of any kind, manifest included (owner: "keeping the
code is fine but ts shouldnt be possible"). The workbook-strip renderer goes
dormant: kept in code, reachable from nothing.

**3. The UI reflects capability.** The evidence toggle and per-cell camera
appear ONLY on the 12 PDF-vs-PDF cells; Excel rows, SELF cells, and the Ramp
Summary env cell show no evidence affordance.

**What survives from the original HF-05 analysis** (real defects, still fixed,
now underneath the print crops): the exact-source read-set rule — each side
evidenced from the document it was compared from or resolved-to print, never a
borrowed sibling print, and no prose asserting an unread source; the
boundary-delimited blank-cell target geometry (PCOA-FINAL-005); no silent
26-character truncation (PCOA-FINAL-006); captions naming the exact print and
page. On a vs-TSN cell the TSN side's crop comes from the library print the
TSN workbook was built from and the TSMIS side's crop from the per-route
export in the compared run folder — both parse-back-verified against the
published cell, with disagreement disclosed per ruling 1.

**Acceptance population under the amendment:** 12 evidence sets
(4 Everything-tsn `_pdf` + 4 By-Day-tsn `_pdf` + 4 Everything-ENV `_pdf`) and
14 required-silent cells (8 Excel-row vs-TSN + 5 SELF + Ramp Summary ENV, each
read behind a planted positive control), plus the two always-silent paths
(classic Compare tab, PDF-vs-Excel by-day matrix). Where the frozen text below
says "11 registry cells", "18 artifact sets", "all five Everything ENV cells",
or requires workbook-panel rendering, this amendment controls.

## ⚠️ Owner ruling — 2026-08-09: what "accurate crop" means for an anchorless blank

Raised by review finding `RB4-R1-001` against HF-10 criterion 2. One retained
crop — `intersection_detail_pdf_tsn / ML_Traffic_Flow_1_pair.png`, route 232 @
`000.807` — boxes a blank cell out in the whitespace right of the record's last
glyph. The box is the column's REAL cell: Intersection Detail takes a blank
target from the print's own ruled cell rectangle (`_box_at` → `meta["edges"]`),
so it is correct by construction. But the print's cell boundaries are geometry
rather than stroked rules, and uniquely in that crop no record in view prints
that column, so a reader has no in-crop anchor to confirm the box by.

The owner inspected the image and ruled it acceptable: *"this is fine, just
document it."* So, for this bundle and any later evidence work:

**A blank cell drawn from the print's OWN cell rectangle is ACCURATE.** Where
no record inside the crop prints that column, the image is an anchorless — not
a failed — crop: it is retained, and the limitation is disclosed with its
measured incidence (`results/chain8-known-gap.md`; 1 of 336 in chain10).

This does NOT relax anything else. A box that is mis-targeted, spans more than
one column, is clipped, falls outside the record's printed extent, or shows a
value differing from the compared one without a disclosure note remains a
failure. In particular it does not re-permit the Highway Log defect fixed in
`f4b55f2`: that box was a 12 px sliver drawn past the record's right edge and
~25 px left of where its column actually prints — invented geometry, not the
print's own cell. The distinction is the SOURCE of the rectangle, not whether
a reader finds it convenient.

Rejected alternative: extending Highway Log's bracketing rule to Intersection
Detail. It would refuse this crop, but it bans anchoring a blank off a
neighbouring record (PCOA-FINAL-005), so it would also refuse the many ID
trailing blanks that a reader CAN anchor — trading one unverifiable image for
a large, silent loss of coverage.

| Field | Value |
|---|---|
| Bundle / work items | **RB-4 / HF-05 + HF-10** |
| Queue order | **4** |
| Theme | Evidence end to end: eligibility, exact-source binding, target geometry, panel fidelity, and the missing cross-environment PDF-vs-PDF lane |
| Branch | `hotfix/rb-4-evidence` |
| Readiness source `main` | `ff780af4b1e3845ba30d120e3c3a0b2f7c47665b` — RB-3 merged, its 158/158 post-merge gate and frozen application self-test passed, and its merge closeout was committed before this readiness preparation |
| Base `main` commit | `72adf447d45a2b74c562ba714008661a180c5d5f` — fetched without force; `main` verified clean and identical to `origin/main`; `hotfix/rb-4-evidence` created from it in worktree `C:\Users\Yunus\Projects\wt-rb4` before any code change (Stage 4, 2026-08-02) |
| Canonical finding IDs | **PCOA-FINAL-004, -005, -006, -007** |
| Implementer | **Claude** (owner decision 2026-07-26) |
| First reviewer | **Codex** — independent non-implementer; binds to the existing evidence ledgers, native-scale review set, source-role witnesses, targeting/truncation census, and the five missing ENV cells |
| Second reviewer | **Codex** — a separate fresh review that challenges Review 1 and re-derives bounded risk cases from source |
| Rush ship | **Eligible, not planned.** Only an explicit owner invocation activates the exception; it cannot waive the full gate, combined acceptance run, exhaustive image review, or two-review merge gate |

## Bundle scope and completeness rule

RB-4 is exactly the union of HF-05 and HF-10 below. Every scope statement,
test, generation path, recount, native-scale inspection, retained witness, and
measurable criterion in both sections controls. HF-10's new ENV capability must
be born on HF-05's exact-source, targeting, and panel-fidelity contract; neither
item may be accepted independently while this bundle remains combined.

The allowed implementation surface is the union named below:
`scripts/visual_evidence.py`; the required `scripts/evidence_*.py` adapters;
the evidence call sites and `build_cell_comparison`/ENV evidence entry point in
`scripts/matrix_build.py`; the evidence guards, toggle, camera, and freshness
plumbing in `scripts/day_matrix.py`, `scripts/matrix_state.py`, and
`scripts/gui_matrix.py`; the required `scripts/ui/` matrix pages; and focused
checks/acceptance tooling. A change outside that union requires a return to
planning. Comparison values, formulas, masks, typed outcomes, and counts are
invariants; evidence is the only product surface authorized to change.

RB-4 is the program's heaviest bundle. If one complete implementation and two
bounded reviews cannot cover the combined run below, return RB-4 to `BLOCKED`
and use the documented HF-05/HF-10 split fallback. Sampling, partial image
review, or silently dropping a criterion is not an allowed substitute.

## One executable acceptance run — `RB4-A1`

At one exact implementation head, execute:

`build\.venv\Scripts\python.exe build\run_rb4_acceptance.py --run-id RB4-A1`

The Stage 4 implementation may add that focused driver under the allowed
checks/acceptance-tooling surface. It must drive the exact end-user paths named
in both work-item sections and retain one machine-readable, hash-bound result
set. `IMPLEMENTATION.md` must record the exact base/head, frozen source
identities, command/GUI transactions, output paths, sizes, SHA-256 values,
generation metadata, installed-Excel results, and witness hashes.

The single run must:

1. Bind every new assertion to the recorded pre-fix base, require the precise
   HF-05/HF-10 defect signature there, and require it green at the acceptance
   head.
2. Re-run every existing By Day vs-TSN, Everything vs-TSN, and Everything SELF
   evidence path, all 11 registry eligibility cells and their By Day
   counterparts under the owner's EXACT-SOURCE ruling, both already-correct
   silent controls, and all five Everything ENV PDF-vs-PDF cells. Any pair that
   cannot bind both sides to the exact compared documents must leave no
   workbook, image directory, manifest, or stale current-looking artifact.
3. Bind every eligible read-set member to the comparison's own provenance and
   published cell. Programmatically validate 100% of rendered strings,
   elision markers, blank-side target rectangles, captions, record/field glyph
   isolation, and read-set declarations; then inspect every retained image
   individually at native scale. Recount the prior 8-of-190 truncation and
   blank-target populations rather than sampling them.
4. Prove every comparison count, mask, typed outcome, value, and formulas-twin
   input invariant before/after and with evidence on/off. Re-derive the five
   ENV count sets from source, verify formulas-twin settlement is unchanged,
   and open every evidence workbook cleanly in installed Excel with images and
   Ledger intact.
5. Prove the classic Compare and PDF-vs-Excel by-day paths remain silent, all
   existing vs-TSN/SELF evidence behavior outside the authorized repairs is
   unchanged, and every named neighboring-family/evidence check passes.
6. Run the complete repository gate, including
   `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k`, `compileall`,
   `ruff`, and `build\build.ps1 -SelfTest`.
7. Retain one complete `RB4-A1` manifest and verifier binding the eligible and
   prohibited sets, all generated workbooks/images, exhaustive verdict tables,
   source/count invariance records, installed-Excel outcomes, full-gate logs,
   and the committed HF-05/HF-10 witnesses to the same acceptance head.

## Required verification matrix

| Gate | `RB4-A1` obligation | Approval rule |
|---|---|---|
| End-user paths | Existing evidence toggles/cameras plus all five Everything ENV cells | Every named path is executed at the exact acceptance head |
| Eligibility and source binding | All current cells, both silence controls, exact comparison provenance | Eligible sets bind both exact compared documents; ineligible sets leave zero artifacts |
| Values and formulas | Semantic before/after and evidence-on/off comparison; installed-Excel open/recalc checks | Counts, masks, typed outcomes, values, and formulas inputs are unchanged |
| Visual fidelity | Automated whole-set oracle plus individual native-scale inspection | 100% correct value/elision, target, crop, caption, and read-set declaration |
| PDF/PDF ENV capability | Five bound workbooks/manifests/image sets and source recounts | All five supported cells exist; no relabelling or absence passes |
| Neighboring lanes | Existing vs-TSN/SELF behavior and silent classic/PDF-vs-Excel controls | No unauthorized evidence or comparison behavior changes |
| Regression | Full focused evidence/matrix checks, complete gate, frozen app self-test | Every required command passes at the same head |

---

### HF-05 — Evidence eligibility, source binding and panel fidelity

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-05` / `evidence-binding` |
| Split fallback branch | `hotfix/hf-05-evidence-binding` |
| Priority / order | 5 |
| Depends on | Nothing (blocks HF-10) |
| Findings | **PCOA-FINAL-004** (P1), **-005** (P1), **-006** (P1) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to its five `source-audit/*evidence*` review ledgers and `visual-review/evidence-review/`, plus Claude's `visual_evidence.py:1270` census and the RC-2 `FT_3_stacked.png` reproduction |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | **Inherits RB-4: JOINTLY APPROVED** |

**Exact scope.** The visual-evidence renderer's eligibility rule, per-side source
binding, target geometry and Excel-panel fidelity, across every path that emits
evidence today: By Day vs TSN, Everything vs TSN, Everything SELF — 11 registry
cells, 18 artifact sets, 1,778 retained PNGs.

**Explicitly out of scope.** Building the cross-environment lane (HF-10); the
comparison counts of any family; the two paths that already correctly emit
nothing (classic Compare tab, PDF-vs-Excel by-day matrix) — they must stay silent
and unchanged; the evidence *Ledger*'s content, which Stage 2 validated as
exhaustive and correct.

**Verified root cause.** Three independent defects in one renderer.
(a) `visual_evidence.generate:547` is entered for pairs whose semantic sides are
not both PDFs: side A can be the consolidated XLSX (`tsmis_source_role:173`),
side B is *always* the normalized TSN workbook on a vs-TSN comparison, and all
five SELF cells have an Excel side by construction — while
`_TSN_PDFS_IN_RAW:118` lets Highway Log/Highway Sequence borrow the library's raw
district prints and `intersection_detail*` / `ramp_detail_pdf` borrow a different
statewide PDF from `tsn_library\<report>\pdf\`; the workbook then asserts *"Red
box = the compared cell in each source PDF"* and declares a `TSMIS PDFs:`
directory absent from its own read set. The decisive case — 80 PDFs, zero XLSX,
still the wrong document — proves a PDF-only read set is not a sufficient test.
(b) When the compared value is blank on the TSN district print, the target box
lands on adjacent printed content (the final `O` of `EQUATES TO`; the *next*
Highway Log record) because the collapsed equation line has no column grid; the
TSMIS side, which has a fixed grid, is boxed correctly. (c)
`visual_evidence.py:1270` draws each Excel-side cell as `text[:26]` with no
ellipsis (header label capped at 24 on `:1266`), so 8 of 190 rendered examples
endorse a **different string** than the one compared.

**✅ Owner ruling — 2026-07-26: EXACT-SOURCE, keep the feature.** The audit's
eligibility rule (Prompt 01 item 10 / neutral scope rule 11: evidence is
prohibited whenever either semantic side is a normalized XLSX) and the finding's
acceptance oracle (each read-set member must be *the exact artifact its side was
compared from*) are not the same rule. Read literally, the first would retire
essentially the entire shipped evidence feature — every vs-TSN cell and all five
SELF cells — including the CMP-AUD-210 Excel-side binding and the v0.32.0
`excel_column_for` work that `check_evidence_source_role.py` locks in. **The owner
has ruled the oracle**: evidence each side from the document that side was
compared from, never from a borrowed sibling print, and stop asserting sources
that were not read. Feature retirement is **not** shipped.

**The evidence the ruling was made on** — the existing
`ssor-prod_highway_log_tsn` set, route 101 @ `011.603R`
(`Description_1_stacked.png`) and its manifest:

| Observation | Detail |
|---|---|
| Manifest read set | **13 entries: 1 consolidated XLSX + 12 TSN district PDFs.** The normalized TSN workbook the comparison actually compared against is *not* in it |
| Top panel | `TSMIS (Excel) — highway_log_consolidated.xlsx · Highway Log!AD31200` — honest; the comparison did read that workbook |
| Bottom panel | `TSN — D07 Highway Log TSN.pdf · page 144` — **not the compared document.** It is the raw input the normalized workbook was built from, so the values agree, but it is not what was read |
| Excel cell drawn | `RIVERSIDE DR OFF RAMP  , O` — cut at 26 characters with no ellipsis, while the caption above carries the full `RIVERSIDE DR OFF RAMP , OC 53-1493` (finding 006, this exact cell) |

**Required behaviour — SUPERSEDED 2026-08-05 by the owner amendment above.**
~~That image keeps existing: the TSMIS panel is unchanged, the TSN panel is
redrawn from the normalized workbook that was compared, the truncation is
fixed, and the workbook stops claiming "the compared cell in each source PDF"
or declaring a `TSMIS PDFs:` directory it never read.~~ The workbook-panel
remedy was implemented, ran through the first `RB4-A1` pass, and was rejected
by the owner on sight of the images: evidence must be print crops or nothing.
The amended required behaviour: that cell (an Excel-row vs-TSN cell) **emits no
evidence at all** — the engine refuses it; the 12 `_pdf`-family cells render
TWO PRINT CROPS (TSMIS per-route export / TSN library print / env partner
print) with the exact-source read set, fixed blank-cell geometry, no silent
truncation, and disagreement disclosed. Where a side cannot be bound to its
print, **no artifact of any kind is emitted** — manifest included.

**Files expected to change.** `scripts/visual_evidence.py`, the
`scripts/evidence_*.py` adapters (targeting), `scripts/matrix_build.py`
(evidence call sites only), and the guards at `scripts/day_matrix.py` /
`scripts/gui_matrix.py`; plus checks.

**Tests to add.** Extend `check_visual_evidence.py`,
`check_evidence_source_role.py`, `check_evidence_manifest.py`,
`check_evidence_bundle.py`, `check_evidence_excel_columns.py`,
`check_evidence_literal_cells.py`: no artifact of any kind (manifest included)
for a pair failing the exact-source test; every read-set member equals the
comparison's own recorded provenance for that side; a blank-on-one-side example's
target rectangle lies inside the captioned record's row rectangle and touches no
other record's or field's glyphs — asserted over the whole generated set, with
explicit `EQUATES TO` and blank-`Description` fixtures so the assertion cannot
depend on sampling luck; and every drawn Excel panel string equals the compared
value or is visibly marked elided, in both layouts.

**Exact end-user generation path.** Matrix pages → the evidence toggle on the
By Day and Everything vs-TSN matrices and the Everything SELF lane, plus the
per-cell camera; and the classic Compare tab plus the PDF-vs-Excel by-day matrix
to prove they still emit nothing.

**Source-truth recount.** For every retained image, bind the drawn value back to
the published comparison cell through `published_comparison.py` (the truth layer
already decodes the workbook's own state masks) and to the raw print/workbook the
side was read from. Recount the 8-of-190 truncation census and the blank-side
target population exhaustively rather than by sample.

**Values / formulas and installed-Excel checks.** Comparison workbooks must be
untouched: assert every affected family's counts, masks and typed outcomes are
semantically identical before and after. Evidence workbooks open clean in installed
Excel with images embedded and the Ledger intact.

**Workbook visual / presentation checks.** Every evidence workbook's image
sheets, Summary and Ledger inspected at native scale on the merged HF-02 base;
no prose asserts a source not in the read set.

**Evidence review requirement.** **Every** retained image is inspected
individually — not a sample — for every cell that still generates after the
ruling; and for every cell that no longer generates, the artifact set (workbook,
image folder, manifest) is proved absent, with the prior set proved retired
rather than left looking current.

**Neighbouring-family regression.** HL, HSL, ID (both), RD-PDF, and HD (**do not
touch — pre-release**): full gate plus every `check_evidence_*`,
`check_visual_evidence.py`, `check_matrix.py`, `check_day_matrix.py`,
`check_pdf_excel_matrix.py`, `check_comparison_publication.py`.

**Measurable acceptance criteria.**
1. Zero artifacts — manifest included — for any pair failing the exact-source
   test; the 11 registry cells and their By Day counterparts re-run and asserted
   under the recorded ruling.
2. 100 % of rendered examples: drawn Excel-panel string equals the compared value
   or is marked elided.
3. 100 % of blank-side examples: target inside the captioned record, touching no
   other record or field.
4. No prose asserts an unread source; the `TSMIS PDFs:` declaration matches the
   read set.
5. The two already-correct paths still emit nothing.
6. All comparison counts and typed outcomes unchanged.
7. Full gate green; every new assertion fails pre-fix.

**Rollback.** Revert the merge commit. Retired artifact sets are regenerable;
no comparison workbook is modified, so nothing downstream needs migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-05\`
(every generated image set, before and after);
`hotfix-bundles/HF-05/witness/` for the exhaustive per-image verdict table, the
truncation census and the target-geometry measurements.

---

### HF-10 — Cross-environment PDF-vs-PDF evidence capability

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-10` / `env-evidence` |
| Split fallback branch | `hotfix/hf-10-env-evidence` |
| Priority / order | 10 |
| Depends on | **HF-05** (the eligibility/binding/targeting contract must exist first) |
| Findings | **PCOA-FINAL-007** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** (found the five absent-but-required cells) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | **Inherits RB-4: JOINTLY APPROVED** |

**Exact scope — AMENDED 2026-08-05.** Evidence for the ~~five~~ **four**
Everything ENV cells of the `_pdf` report families — Ramp Detail (PDF),
Intersection Detail (PDF), Highway Log (PDF), Highway Sequence (PDF). Ramp
Summary's env cell is REMOVED by the owner's third ruling (report-type rule);
it joins the required-silent controls, and its env adapter goes dormant.

**Explicitly out of scope.** Ramp Summary **vs TSN** (correctly approved as a
prohibited absence); Baseline and PDF-vs-Excel lanes unless the owner extends
scope; any change to the env comparisons' counts; the vs-TSN and SELF evidence
rules settled by HF-05.

**Verified root cause.** An unimplemented capability, not a failed generation:
`matrix_build.build_cell_comparison:561` takes **no** evidence argument, and
`visual_evidence` has only `FLAVOR_TSN` and `FLAVOR_SELF` (`:159-161`), so no
env-flavored path exists anywhere; no artifact exists under the env, baseline or
PDF-vs-Excel trees.

**Files expected to change.** `scripts/visual_evidence.py` (a third flavor),
`scripts/matrix_build.py` (`build_cell_comparison` + an env evidence entry
point), `scripts/matrix_state.py` / `scripts/gui_matrix.py` (toggle, camera,
freshness gating), the `scripts/ui/` matrix pages, plus checks.

**Migration / compatibility.** The env lane's comparison output must not change:
evidence is additive decoration and a failed decoration must never fail a
comparison (the existing contract). The new flavor must satisfy HF-05's
exact-source rule at birth and reuse the same targeting and panel code, not a
parallel renderer.

**Tests to add.** Extend `check_visual_evidence.py`, `check_matrix.py` and
`check_evidence_manifest.py`: an env PDF-vs-PDF cell with positive differences
produces a bound manifest, workbook and image set with a PDF-only read set that
passes the exact-source test; a cell whose sides are not both PDFs produces
nothing; and the env comparison's counts are unchanged with evidence on or off.

**Exact end-user generation path.** Everything ENV matrix → evidence toggle on,
plus the per-cell camera, for all five cells.

**Source-truth recount.** Each rendered example bound back to the published
comparison cell and to both raw prints; the five cells' difference counts
re-derived and shown unchanged (Ramp Summary 67; ID-PDF 17,562; RD-PDF 376 +
5/8 one-sided; HL-PDF 88,238 + 2,095/1,174; HSL-PDF 1,904 + 7/246).

**Values / formulas and installed-Excel checks.** The matrix path writes the
values workbook and settles a live-formulas twin only when `also_formulas` is set
and the twin's inputs are unchanged (`build_cell_comparison` →
`_settle_formulas_twin`); assert that behaviour is unchanged with evidence on, and
that installed Excel opens the evidence workbooks clean.

**Workbook visual / presentation checks.** Every evidence workbook's sheets and
Ledger inspected at native scale.

**Evidence review requirement.** **Every** image in all five sets inspected
individually — accurate target, legible crop, correct caption, read-set member
equal to the compared document. Absence, or relabelling a supported comparison
`N/A`, does not pass.

**Neighbouring-family regression.** The vs-TSN and SELF evidence lanes settled by
HF-05 must be unchanged; the classic Compare tab and PDF-vs-Excel by-day matrix
must still emit nothing: full gate plus every `check_evidence_*`,
`check_matrix*.py`, `check_day_matrix.py`, `check_baseline_matrix.py`,
`check_pdf_excel_matrix.py`.

**Measurable acceptance criteria.** *(amended 2026-08-05: four cells, not
five — Ramp Summary's env cell joins the required-silent controls; criterion 2
further amended 2026-08-09 per the owner ruling above)*
1. All four `_pdf`-family env cells produce a bound manifest, evidence workbook
   and image set with a PDF-only read set passing the exact-source test.
2. 100 % of retained crops accurate and readable, reviewed individually —
   "accurate" as defined by the 2026-08-09 ruling: an anchorless blank drawn
   from the print's own cell rectangle is a disclosed coverage limitation,
   not a failed crop.
3. Env comparison counts identical with evidence on and off.
4. No other lane's evidence behaviour changed.
5. Full gate green; the new assertions fail pre-fix.

**Rollback.** Revert the merge commit; the capability disappears and the five
cells return to absent-and-required. No data migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-10\`
(all five image sets); `hotfix-bundles/HF-10/witness/` for the per-image verdict
table and the count-invariance proof.

---

## Bundle-level dependencies and rollback

- Queue prerequisite: RB-3 is merged at
  `61fcac611de255c56759551a95ccd2e552287bfc`; the readiness source is
  `ff780af4b1e3845ba30d120e3c3a0b2f7c47665b`.
- Internal dependency: HF-10 consumes HF-05's repaired renderer contract and
  merges atomically with it while RB-4 remains combined.
- Split fallback: if the complete `RB4-A1` run or either complete review is not
  feasible in one pass, return RB-4 to `BLOCKED` and split into the already
  specified `hotfix/hf-05-evidence-binding` and
  `hotfix/hf-10-env-evidence` sequence. Do not sample or weaken acceptance.
- Rollback: revert RB-4's future merge commit and retire its generated evidence
  sets. Comparison workbooks require no migration because their semantics and
  counts are invariants.

## Scope approval

| Planner / readiness check | Decision | Commit / date |
|---|---|---|
| Claude (first plan) | **APPROVED — FIRST PLAN** | `4e34bee` / 2026-07-26 |
| Codex (final challenge and combined-transcription check) | **APPROVED — READY** | this readiness commit / 2026-08-02 |
