# Post-Comparison Output Program — Start Here

Workflow state: **Stages 1A, 1B, 2, and 3 complete and jointly approved;
RB-1 / Clean Road is MERGED at `560ea5e501fdd76003985753ba7fc9ff0a551320`;
RB-2 is MERGED at `d679f388e0b12ff595751af9edd816674615b7a5`;
RB-3 / HF-04 is IMPLEMENTED — AWAITING ADVERSARIAL REVIEW at `c9b55b6` on
`hotfix/rb-3-ramp-detail-layout` (base `194b7ee`)**

Last updated: 2026-08-02

This is the entry point for every new Codex or Claude chat. Read this file
before opening the other audit documents. The project deliberately separates
independent observation, cross-checking, planning, implementation, and
approval so that one agent's conclusions do not contaminate another agent's
first pass.

## Next action

In a fresh task, run
[`PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md`](prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md)
with `<BUNDLE_ID> = RB-3` and `<REVIEWER> = Codex` (Review 1) against the
pushed head of `hotfix/rb-3-ramp-detail-layout`. The implementation record is
[`hotfix-bundles/RB-3/IMPLEMENTATION.md`](hotfix-bundles/RB-3/IMPLEMENTATION.md);
generated outputs and the RB3-A1 witnesses are retained under
`C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-04\`.

`RB2-R2-004` was correct to refuse the decision from the reviewer's chair. It
returned RB-2 to the plan owner over two surfaces the accepted runtime touches:
`_fit_data_columns` on ordinary data-sheet fields, which HF-02 excluded, and
`write_source_files_sheet`'s geometry, through a file authorized only for
provenance selection.

**The owner amended HF-02 / RB-2 on 2026-08-02 to authorize both, byte-for-byte
against the existing runtime.** The exclusion rested on the data columns being
"Stage 2-validated clean" at an explicit width of 13.0; against the produced
output, base workbooks store no width at all for those columns — they render at
Excel's 8.43 default — and **data sheets are the corpus's largest clipping
class**, 736 cells against `Comparison`'s 392 on the same twelve base
deliverables. That "clean" finding came from `VC-14`, measured through the same
eight-column window `RB2-R2-001` disproved, so HF-02.1 and the exclusion could
not both hold. Criterion 1 governs. `Source Files` was never Stage 2-validated
or frozen — it declared no widths at all and its own header clipped, invisible
to every scan here because they all skip row 1 as a wrapped header band. The
amendment, with its evidence, is in
[`hotfix-bundles/RB-2/BUNDLE.md`](hotfix-bundles/RB-2/BUNDLE.md) and mirrored in
the plan's HF-02 contract.

**No product file changed.** The acceptance head is still `06266eca1a4858dc5ebd000d1dd2e946249c7338`; no corpus
was regenerated, no installed-Excel leg re-ran, the full gate was not re-run, and
no witness, manifest or verifier identity moved — matching the return's own
"authorize the current runtime byte-for-byte" branch. `RB2-R2-EG-003` (60/60
head deliverables, 0 owned clipped cells), `RB2-R2-001`, `RB2-R2-002` and Review
1's `EG-001`/`EG-002` all remain closed.

Review 2 independently checked both controlling scope copies, the complete
base-to-entry diff, the unchanged 418-file runtime identity, and the retained
acceptance manifest. The committed verifier matched all 21 claimed results and
five witnesses at the exact acceptance head with zero problems. Review 1 and
Review 2 now both approve; the signed record is in
[`hotfix-bundles/RB-2/REVIEW.md`](hotfix-bundles/RB-2/REVIEW.md).

One item is carried forward rather than fixed, and is recorded in the amendment:
`_fit_data_columns` inherits openpyxl's `DEFAULT_COLUMN_WIDTH = 13.0` as a floor,
so data columns store at least 13.0. It can only over-widen — never narrower than
measured, so it cannot clip — and correcting it would move the runtime digest and
force a complete RB2-A1 regeneration, so it belongs to a bundle that regenerates
anyway.

RB-2 merged only after the 158/158 post-merge gate and frozen application
self-test passed. This closeout prepared RB-3's scope-only readiness record; it
did not create a branch, modify product code, or begin an acceptance run.

## Workflow

| Stage | Purpose | Current status | Controlling prompt | Primary output |
|---|---|---|---|---|
| 1A | Codex independent deliverable audit | **COMPLETE** | Historical user request, normalized in `AUDIT-SCOPE-AND-PROVENANCE.md` | `MASTER-VERIFICATION.md`, `CODEX-FINDINGS.md` |
| 1B | Claude independent deliverable audit | **COMPLETE** (freeze `c788b29`) | `prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md` | `CLAUDE-FINDINGS.md` |
| 2 | Codex/Claude cross-check and canonical findings | **COMPLETE — JOINTLY APPROVED** | `prompts/PROMPT-02-CROSSCHECK-AND-FINAL-FINDINGS.md` | `FINAL-RECONCILIATION.md`, `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` |
| 3 | Agree on ordered implementation bundles | **COMPLETE — JOINTLY AGREED** | `prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md` | `IMPLEMENTATION-PLAN.md`, `hotfix-bundles/<RB-ID>/BUNDLE.md` |
| 4 | Implement one bounded RB bundle | **RB-3 IMPLEMENTED** (`c9b55b6`) | `prompts/PROMPT-04-IMPLEMENT-HOTFIX-BUNDLE.md` | Hotfix branch plus `hotfix-bundles/<RB-ID>/IMPLEMENTATION.md` |
| 5 | Adversarially review and approve that bundle | **RB-3 AWAITING REVIEW 1** | `prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md` | `hotfix-bundles/<RB-ID>/REVIEW.md`; merge or return to Stage 4 |

Stages 4 and 5 repeat until every accepted implementation bundle is merged.
Each new bundle starts from the latest clean `main`.

## Independence firewall — ENDED 2026-07-26

The firewall is spent. Claude froze Stage 1B at `c788b29` with a signed
independence declaration, so both rounds may now read everything. The section
below is retained as the record of what the rule was while it was in force.

Before Claude freezes Stage 1B, it may read only:

- this file;
- `AUDIT-SCOPE-AND-PROVENANCE.md`;
- `CLAUDE-FINDINGS.md`;
- `prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md`;
- application code and the frozen raw inputs named in the scope document.

Before that freeze, Claude must not read:

- `MASTER-VERIFICATION.md`;
- `CODEX-FINDINGS.md`;
- `FINAL-RECONCILIATION.md`;
- `FINAL-FINDINGS-FOR-IMPLEMENTATION.md`;
- Codex-generated comparisons, contact sheets, source-audit ledgers, or the
  retained `handoff-docs` folder.

The firewall ends only after Claude has marked its own matrix and findings
`CLAUDE ROUND 1 COMPLETE`, committed them, and recorded the commit SHA.

## Document authority

| File | Workflow role |
|---|---|
| `AUDIT-SCOPE-AND-PROVENANCE.md` | Neutral scope, frozen sources, comparison topology, and audit rules |
| `MASTER-VERIFICATION.md` | Closed Stage 1A Codex matrix; not joint truth |
| `CODEX-FINDINGS.md` | Closed Stage 1A Codex findings |
| `CLAUDE-FINDINGS.md` | Stage 1B independent Claude workspace |
| `FINAL-RECONCILIATION.md` | Stage 2 decision-by-decision conflict resolution |
| `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` | Stage 2 canonical, deduplicated findings |
| `IMPLEMENTATION-PLAN.md` | Stage 3 approved bundle queue and acceptance contracts |
| `hotfix-bundles/<RB-ID>/` | Stage 4 contract/implementation log and Stage 5 review record for one implementation bundle |
| `hotfix-bundles/<HF-ID>/witness/` | Small committed witness for one work-item acceptance oracle |

No finding is implementation authority until it appears in
`FINAL-FINDINGS-FOR-IMPLEMENTATION.md`. No code change is authorized until its
owning **RB bundle** appears as `READY` in `IMPLEMENTATION-PLAN.md`.

## Branch and worktree policy

- Audit and planning branches contain documentation only.
- Every implementation bundle uses a new branch from the latest `main`, named
  `hotfix/<rb-id>-<short-slug>`.
- Prefer a separate worktree for every hotfix so the user's normal checkout
  remains available.
- A hotfix branch contains only its agreed bundle. Do not opportunistically
  include another report family or shared cleanup.
- A denied review returns to Stage 4 on the same hotfix branch.
- A bundle merges to `main` only after its required independent approvals.
- After a verified merge, remove that bundle's worktree and fully merged
  hotfix branch. Preserve `gh-pages` and unrelated branches.
- The next bundle always branches from the newly updated `main`, never from a
  previous hotfix branch.

## Frozen artifact locations

- Repository:
  `C:\Users\Yunus\Projects\TSMIS-Reports-Exporter`
- Codex retained audit root:
  `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-perfection-output-audit-2026-07-23`
- Codex generated comparisons:
  `<Codex retained audit root>\generated-comparisons`
- Codex handoff copy:
  `<Codex retained audit root>\handoff-docs`
- Claude retained audit root (Stage 1B):
  `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-output-audit-claude-independent-2026-07-23`
  — 2,336 files / 9,570,952,287 bytes, `witness\MANIFEST.json` carries path, size
  and sha256 for each
- Stage 2 neutral recheck root:
  `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-output-audit-stage2-reconciliation`
  — `measure_clipping.py` plus `witness\clipping_recheck.json` and
  `witness\tsn_provenance_warning_scope.json`

These Codex artifacts became available to Claude only in Stage 2. Claude used a
separate scratch/output root during Stage 1B, and Stage 2 rechecks live in their
own neutral root so neither round's tooling is reused to settle a conflict.

Claude's Stage 1B round also copied the frozen archive and the retained batch
into `output\2026-07-23 ssor-prod`, `output\2026-07-09 ssor-prod` and
`output\2026-07-09 ars-prod` (git-ignored) because the By Day / Baseline /
PDF-vs-Excel matrices read run folders from `OUTPUT_ROOT`, and left By Day
outputs under `output\comparisons\`. They are technically disposable — the raw
archive and the ground-truth batch were never written to — but **RETAIN them
until the Stage 3 plan's definition of done is met**: they are the by-day /
Baseline / PDF-vs-Excel acceptance inputs for every hotfix bundle, and deleting
them also removes the inputs for re-running Stage 2's RC-3 probe. (This
supersedes the earlier "safe to delete" note.)
