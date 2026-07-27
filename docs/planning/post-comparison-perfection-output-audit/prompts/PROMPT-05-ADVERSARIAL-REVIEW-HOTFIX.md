# Prompt 05 — Adversarial Review and Approval of One Hotfix

Use this prompt sequentially with Codex and Claude. At least one reviewer must
not be the bundle's implementer.

Before using, replace:

- `<BUNDLE_ID>` with the implemented **RB bundle ID**. HF IDs are work-item
  specs and are not reviewed separately while their RB remains combined.
- `<REVIEWER>` with `Codex` or `Claude`.

---

You are <REVIEWER> adversarially reviewing the implemented TSMIS comparison
hotfix bundle `<BUNDLE_ID>`.

Repository:
`C:\Users\Yunus\Projects\TSMIS-Reports-Exporter`

Read:

1. `docs/planning/post-comparison-perfection-output-audit/START-HERE.md`
2. `docs/planning/post-comparison-perfection-output-audit/FINAL-FINDINGS-FOR-IMPLEMENTATION.md`
3. `docs/planning/post-comparison-perfection-output-audit/IMPLEMENTATION-PLAN.md`
4. `docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/<BUNDLE_ID>/BUNDLE.md`
5. `docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/<BUNDLE_ID>/IMPLEMENTATION.md`
6. `docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/<BUNDLE_ID>/REVIEW.md`
7. The complete branch diff from its recorded `main` base.

Preconditions:

- The bundle status is `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`.
- The hotfix branch and retained outputs exist.
- The implementation document identifies an exact base/head SHA.
- `<BUNDLE_ID>` and `<REVIEWER>` were replaced.

If a precondition fails, stop and record the missing item. Do not review a
different bundle.

Review independently and assume the implementation may be subtly wrong:

1. Confirm the diff contains the whole agreed scope and no unrelated changes.
2. Reproduce the original defect or bind to a durable pre-fix witness.
3. Run the planned unit, integration, and neighboring-family regression tests.
4. Generate the affected comparisons through the actual end-user production
   workflow.
5. Recount the relevant raw source independently. Do not accept the
   implementation's own parser as the only oracle.
6. Audit values and formulas separately, including installed-Excel
   recalculation/cached parity when required.
7. Inspect every affected workbook sheet at native scale for correctness,
   clipping, instructions, keys, filters, panes, merges, and formula/error
   behavior.
8. Recheck every targeted false-positive class and deterministic adversarial
   samples. Confirm genuine discrepancies remain visible.
9. Compare PDF and Excel siblings where applicable.
10. Recheck semantic evidence eligibility. Inspect every eligible retained
    evidence image and prove prohibited artifacts are absent.
11. Verify all bundle acceptance criteria and that prior clean behavior did
    not regress.
12. Challenge performance, atomic publication, provenance, stale-cache,
    rerun/idempotency, and failure-path behavior relevant to the changed code.

Update `hotfix-bundles/<BUNDLE_ID>/REVIEW.md` with:

- reviewer identity and whether the reviewer implemented the bundle;
- branch/base/head SHA reviewed;
- commands and source inputs;
- exact deliverable and discrepancy results;
- values/formulas, visual, evidence, and regression matrices;
- actionable failures with file/artifact references;
- final verdict `APPROVED` or `DENIED`;
- reviewer signature and timestamp.

Decision protocol:

- If any acceptance criterion fails, mark the bundle `DENIED — RETURN TO
  IMPLEMENTATION`, leave the hotfix branch unmerged, update
  `IMPLEMENTATION-PLAN.md`, and hand the exact failures back to Prompt 04 on
  the same branch.
- If you are the first approving reviewer, mark it
  `REVIEW 1 APPROVED — AWAITING REVIEW 2`, commit the review record, and stop.
- If you are the second approving reviewer, first challenge the first review;
  do not copy it. The bundle is mergeable only when both reviews approve and
  at least one approver is not the implementer.

After final approval:

1. Mark the bundle `JOINTLY APPROVED`.
2. Fetch and confirm remote `main` has not diverged.
3. Merge the hotfix branch to `main` without force.
4. Run the planned post-merge smoke check on `main`.
5. Update `IMPLEMENTATION-PLAN.md` to `MERGED` with the merge SHA.
6. Push `main`.
7. Remove only the merged bundle worktree and fully merged hotfix branch,
   locally and remotely when applicable.
8. Preserve `main`, `gh-pages`, unrelated branches, retained audit artifacts,
   and review documents.
9. Start the next bundle from this updated `main`.

Report the verdict, exact failing criteria or approval evidence, reviewer
sign-offs, merge SHA if merged, branch/worktree cleanup, and the next eligible
bundle ID.

---
