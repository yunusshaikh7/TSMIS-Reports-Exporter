# Post-Comparison Output Program — Start Here

Workflow state: **Stage 1A and 1B complete; Stage 2 has one of two reviewer
signatures — Codex owes the second, adversarial pass**

Last updated: 2026-07-26

This is the entry point for every new Codex or Claude chat. Read this file
before opening the other audit documents. The project deliberately separates
independent observation, cross-checking, planning, implementation, and
approval so that one agent's conclusions do not contaminate another agent's
first pass.

## Next action

Run
[`prompts/PROMPT-02-CROSSCHECK-AND-FINAL-FINDINGS.md`](prompts/PROMPT-02-CROSSCHECK-AND-FINAL-FINDINGS.md)
in a new **Codex** chat, as the **second** Stage 2 reviewer.

Claude filled `FINAL-RECONCILIATION.md` and `FINAL-FINDINGS-FOR-IMPLEMENTATION.md`
and signed the first cross-check. Codex must independently challenge every
conflict resolution and every canonical finding rather than ratify them, correct
errors with an audit trail, and must not erase Claude's reasoning. Both files are
marked `AWAITING SECOND REVIEW` on branch
`audit/post-comparison-final-reconciliation`.

Priority challenges named by the first reviewer: R-01 (the clipping gate that
decides 40 verdicts), R-04/R-05 (evidence crop verdicts that differ by sampling
luck), R-06 plus UN-01 (the evidence-eligibility rule is read two ways), R-09
plus UN-04 (the Highway Sequence equation canonicalization rests on Codex alone),
and R-10 (Clean Road, where Claude's approval rested on canary agreement).

## Workflow

| Stage | Purpose | Current status | Controlling prompt | Primary output |
|---|---|---|---|---|
| 1A | Codex independent deliverable audit | **COMPLETE** | Historical user request, normalized in `AUDIT-SCOPE-AND-PROVENANCE.md` | `MASTER-VERIFICATION.md`, `CODEX-FINDINGS.md` |
| 1B | Claude independent deliverable audit | **COMPLETE** (freeze `c788b29`) | `prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md` | `CLAUDE-FINDINGS.md` |
| 2 | Codex/Claude cross-check and canonical findings | **IN PROGRESS — Claude signed, AWAITING SECOND REVIEW by Codex** | `prompts/PROMPT-02-CROSSCHECK-AND-FINAL-FINDINGS.md` | `FINAL-RECONCILIATION.md`, `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` |
| 3 | Agree on ordered implementation bundles | **BLOCKED on the second Stage 2 signature** | `prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md` | `IMPLEMENTATION-PLAN.md` |
| 4 | Implement one bounded hotfix bundle | **LOOP after Stage 3** | `prompts/PROMPT-04-IMPLEMENT-HOTFIX-BUNDLE.md` | Hotfix branch plus `hotfix-bundles/<ID>/IMPLEMENTATION.md` |
| 5 | Adversarially review and approve that bundle | **LOOP after each Stage 4** | `prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md` | `hotfix-bundles/<ID>/REVIEW.md`; merge or return to Stage 4 |

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
| `hotfix-bundles/<ID>/` | Stage 4 implementation log and Stage 5 review record for one bundle |

No finding is implementation authority until it appears in
`FINAL-FINDINGS-FOR-IMPLEMENTATION.md`. No code change is authorized until its
bundle appears as `READY` in `IMPLEMENTATION-PLAN.md`.

## Branch and worktree policy

- Audit and planning branches contain documentation only.
- Every implementation bundle uses a new branch from the latest `main`, named
  `hotfix/<bundle-id>-<short-slug>`.
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
outputs under `output\comparisons\`. **These are safe to delete** — the raw
archive and the ground-truth batch were never written to — but deleting them
removes the inputs for re-running Stage 2's RC-3 probe.
