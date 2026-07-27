# Post-Comparison Output Program — Start Here

Workflow state: **Stages 1A, 1B, and 2 complete and jointly approved; Stage 3
is drafted by the first planner and AWAITING THE SECOND PLANNER**

Last updated: 2026-07-26

This is the entry point for every new Codex or Claude chat. Read this file
before opening the other audit documents. The project deliberately separates
independent observation, cross-checking, planning, implementation, and
approval so that one agent's conclusions do not contaminate another agent's
first pass.

## Next action

Run
[`prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md`](prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md)
as the **second** Stage 3 planner, in a new chat, on the documentation-only
branch `planning/post-comparison-hotfix-bundles`.

Claude drafted the plan as first planner (both sign-off rows read `NOT STARTED`
when Prompt 03 was invoked, so the prompt's own first-planner rule applied — the
same reversal Stage 2 recorded). [`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md)
now holds **11 verified work-item specs (`HF-01` … `HF-11`) grouped into 6 review
batches (`RB-1` … `RB-6`), Clean Road first** — plus a finding-to-file overlap map
built by code inspection at `main` `a29bdb6`, all 22 canonical findings mapped to
exactly one primary spec, a merge order, a branch/worktree lifecycle, and a
whole-program definition of done. The batch layer is an owner decision (fewer
branches, reviews and releases; 12 Codex passes instead of 22), as is the
**pre-review release policy** — a batch may be released to the owner before its
adversarial review, at most one shipped-but-unmerged at a time, with the full gate
never deferred. The second planner challenges batch size, ordering, overlaps,
missing findings and acceptance tests; verifies Clean Road stays first; and either
revises or signs.
**All four owner policy gates are now RULED (2026-07-26)** — no open owner
question blocks the second planner:

- **HF-01 — mark the skipped anchors.** The Clean Road cells whose ArcGIS side was
  never built carry an explicit non-asserting "unavailable" marker and leave the
  difference count, rather than a bare blank that reads as a disagreement.
  Disclosure-only was rejected: it names the problem without naming which cells.
- **HF-05 — exact-source evidence, keep the feature.** Each side is evidenced from
  the document that side was compared from; no borrowed sibling prints; no prose
  asserting unread sources; no artifact at all where a side cannot be bound. The
  literal audit rule, which would retire nearly the whole shipped evidence
  feature, is **not** adopted.

The other two point in opposite directions on purpose:

- **PCOA-FINAL-013 / HF-09 — stays FLAGGED.** The representation-only Description
  class (`NEVADA STATE LINE , END OF COUNTY` vs `… /END OF COUNTY` and its
  siblings) is two independent sources ten months apart whose text genuinely
  differs. HF-09 adds a disclosure count line and **may not change equality**.
- **PCOA-FINAL-011 / HF-06 — NORMALIZED to zero.** The Highway Sequence
  PDF-vs-Excel equate cells are one pull rendered twice: the `E` suffix sits on the
  partner row, HG/FT are simply not repeated on the print's annotation line, and
  the Description is the same label with `EQUATES TO ` prepended. The rule must be
  pair-aware, opt-in, and must not widen into the HF-09 class.

**No code change is authorized until both planners sign and `HF-01` reads
`READY`.**

Stage 2 is closed with no open conflict:

- the 88-decision topology is **0 APPROVED / 68 DENIED / 16 BLOCKED / 4 N/A**;
- the exact 25-cell evidence registry is **6 APPROVED / 16 DENIED / 3 N/A**;
- the canonical handoff contains **22 records**: **9 P1 / 9 P2 / 2 P3 /
  2 NO FIX**, of which 20 are actionable;
- all four formerly open Stage 2 issues were closed, and the controlling
  evidence rule was corrected with an explicit second-review audit trail.

`FINAL-RECONCILIATION.md` and
`FINAL-FINDINGS-FOR-IMPLEMENTATION.md` are now joint implementation authority.

## Workflow

| Stage | Purpose | Current status | Controlling prompt | Primary output |
|---|---|---|---|---|
| 1A | Codex independent deliverable audit | **COMPLETE** | Historical user request, normalized in `AUDIT-SCOPE-AND-PROVENANCE.md` | `MASTER-VERIFICATION.md`, `CODEX-FINDINGS.md` |
| 1B | Claude independent deliverable audit | **COMPLETE** (freeze `c788b29`) | `prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md` | `CLAUDE-FINDINGS.md` |
| 2 | Codex/Claude cross-check and canonical findings | **COMPLETE — JOINTLY APPROVED** | `prompts/PROMPT-02-CROSSCHECK-AND-FINAL-FINDINGS.md` | `FINAL-RECONCILIATION.md`, `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` |
| 3 | Agree on ordered implementation bundles | **DRAFTED — AWAITING SECOND PLANNER** | `prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md` | `IMPLEMENTATION-PLAN.md`, `hotfix-bundles/HF-01/BUNDLE.md` |
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
outputs under `output\comparisons\`. They are technically disposable — the raw
archive and the ground-truth batch were never written to — but **RETAIN them
until the Stage 3 plan's definition of done is met**: they are the by-day /
Baseline / PDF-vs-Excel acceptance inputs for every hotfix bundle, and deleting
them also removes the inputs for re-running Stage 2's RC-3 probe. (This
supersedes the earlier "safe to delete" note.)
