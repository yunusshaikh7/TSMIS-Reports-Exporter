# Prompt 03 — Agree on the Implementation Plan

Use this prompt sequentially with Codex and Claude after Stage 2 is jointly
approved.

---

You are a Stage 3 planner for the TSMIS post-comparison output program. The
independent audits and final cross-check are complete. Build an implementation
plan that fixes the canonical findings in small, reviewable hotfix bundles
without preventing the user from continuing normal work on the app.

Repository:
`C:\Users\Yunus\Projects\TSMIS-Reports-Exporter`

Read:

1. `docs/planning/post-comparison-perfection-output-audit/START-HERE.md`
2. `docs/planning/post-comparison-perfection-output-audit/FINAL-RECONCILIATION.md`
3. `docs/planning/post-comparison-perfection-output-audit/FINAL-FINDINGS-FOR-IMPLEMENTATION.md`
4. `docs/planning/post-comparison-perfection-output-audit/IMPLEMENTATION-PLAN.md`
5. Existing code/tests only as needed to map file ownership and dependencies.

Preconditions:

- Stage 2 documents are `JOINTLY APPROVED`.
- The canonical findings are committed on clean, current `main`.
- No hotfix bundle has begun.

Work sequentially with the other planning agent on a documentation-only branch
`planning/post-comparison-hotfix-bundles`. The first agent drafts and marks the
plan `AWAITING SECOND PLANNER`; the second challenges and either revises or
signs it. Do not edit product code in Stage 3.

Planning principles:

- **Clean Road is the first implementation priority** because the user needs
  that comparison sheet first.
- Use a hybrid bundling strategy: prefer one report family when it owns its
  fixes, but group findings by a shared root-cause subsystem when separate
  family branches would repeatedly edit the same central code.
- Before assigning bundles, create a finding-to-file/subsystem overlap map.
- Minimize overlapping file ownership between bundles.
- Keep each bundle small enough for one implementation pass and one complete
  adversarial output review.
- Separate high-risk shared infrastructure from family-specific semantics when
  that reduces blast radius.
- Do not mix unrelated visual cleanup, normalization behavior, evidence policy,
  and source-row correctness merely to reduce the number of branches.
- Every bundle must leave `main` usable and releasable after it merges.
- Every later bundle branches from the latest `main`, never from a prior
  hotfix.

Consider, but do not blindly adopt, this likely shape:

1. Clean Road correctness, skipped-row disclosure, and comparison-sheet
   perfection.
2. Ramp Detail layout compatibility and self/TSN normalization.
3. Highway Sequence semantic and family-specific output behavior.
4. Highway Log semantic and family-specific output behavior.
5. Intersection/summary semantic behavior where ownership is shared.
6. Shared evidence eligibility, required availability, binding, and crop
   targeting.
7. Shared workbook presentation, split into statewide-summary and
   large/detail bundles if they touch different renderers or carry different
   risk.

Change that shape when the verified file-overlap map supports a more efficient
boundary.

For every bundle in `IMPLEMENTATION-PLAN.md`, define:

- bundle ID such as `HF-01`;
- short name and branch slug;
- priority and dependency order;
- included `PCOA-FINAL-*` findings;
- exact report/workflow/format scope;
- explicit out-of-scope items;
- verified root cause and likely files/subsystems;
- migration or compatibility concerns;
- unit/integration tests to add;
- exact end-user generation path to exercise;
- source-truth recount requirements;
- values/formulas and installed-Excel checks;
- workbook visual/presentation checks;
- evidence eligibility, binding, and every-image review requirements;
- neighboring report families that need regression coverage;
- measurable acceptance criteria;
- rollback strategy;
- expected retained output/witness location;
- required reviewers;
- branch name `hotfix/<bundle-id>-<slug>`;
- status, initially `READY` only after both planners sign.

Also include:

- a complete mapping proving every canonical finding belongs to exactly one
  primary bundle;
- secondary regression dependencies without duplicate implementation scope;
- a proposed merge order;
- a branch/worktree lifecycle;
- a definition of done for the whole program.

Second-planner responsibilities:

- challenge bundle size, ordering, overlaps, missing findings, and acceptance
  tests;
- verify Clean Road remains first;
- reject any bundle whose review cannot prove the user-visible output;
- ensure implementation can proceed one branch at a time while the user's main
  checkout remains available.

After both planners agree:

1. Mark `IMPLEMENTATION-PLAN.md` `JOINTLY AGREED`.
2. Commit and merge the planning branch to `main` without force.
3. Push only after confirming remote `main` has not diverged.
4. Delete the fully merged planning branch/worktree.
5. Do not implement a bundle in this planning session.

Report the ordered bundle list, why the boundaries were chosen, the first
Clean Road bundle ID, the `main` commit SHA, and the exact Prompt 04 invocation
for that bundle.

---
