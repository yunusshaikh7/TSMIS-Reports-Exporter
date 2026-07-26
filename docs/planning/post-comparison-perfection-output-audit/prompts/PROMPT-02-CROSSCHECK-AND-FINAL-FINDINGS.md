# Prompt 02 — Cross-Check and Build Final Findings

Use this prompt sequentially with Codex and Claude after both independent
rounds are complete. The first reviewer populates the joint worksheet; the
second reviewer challenges every result and closes it.

---

You are one of two Stage 2 reviewers for the TSMIS post-comparison output
program. Codex and Claude have completed independent first rounds. You may now
read both bodies of work. Your task is to cross-check all decisions and
findings against durable evidence and produce the canonical final findings
document that will govern implementation.

Repository:
`C:\Users\Yunus\Projects\TSMIS-Reports-Exporter`

Read:

1. `docs/planning/post-comparison-perfection-output-audit/START-HERE.md`
2. `docs/planning/post-comparison-perfection-output-audit/AUDIT-SCOPE-AND-PROVENANCE.md`
3. `docs/planning/post-comparison-perfection-output-audit/MASTER-VERIFICATION.md`
4. `docs/planning/post-comparison-perfection-output-audit/CODEX-FINDINGS.md`
5. `docs/planning/post-comparison-perfection-output-audit/CLAUDE-FINDINGS.md`
6. `docs/planning/post-comparison-perfection-output-audit/FINAL-RECONCILIATION.md`
7. `docs/planning/post-comparison-perfection-output-audit/FINAL-FINDINGS-FOR-IMPLEMENTATION.md`

Preconditions:

- Codex Stage 1A status is complete.
- Claude Stage 1B status is
  `CLAUDE ROUND 1 COMPLETE — EMBARGO MAY END`.
- Both independent artifact roots still exist.
- Both audits have terminal 88-decision and evidence matrices.
- No implementation has started.

If a precondition is false, stop Stage 2 and state the exact missing condition.
Do not silently fill an absent independent verdict from the other agent's work.

Branch discipline:

- Work sequentially on one documentation-only branch,
  `audit/post-comparison-final-reconciliation`, created from the latest clean
  `main`.
- Bring the frozen `claude/post-comparison-output-audit` commit into this
  reconciliation branch before editing. Verify that this changes only the
  intended Stage 1B documentation/witness indexes and does not overwrite the
  frozen Codex files.
- The first reviewer commits an `AWAITING SECOND REVIEW` draft.
- The second reviewer continues that same branch and does not erase the first
  reviewer's reasoning.
- Do not modify application code in Stage 2.

Cross-check every item, not only explicit disagreements:

1. Reconcile the exact 88-decision topology and the separate exact 25-cell
   Everything evidence topology.
2. Compare every Codex and Claude verdict. Record agreements, disagreements,
   missing scope, and apparent differences in terminology.
3. Reconcile input hashes, route/report coverage, workflow dispatch,
   discrepancy counts, formula totals, cached-value checks, visual findings,
   evidence eligibility, availability, image counts, and crop verdicts.
4. Deduplicate findings that describe the same product defect through
   different workflows or report formats, without hiding their full affected
   scope.
5. Challenge high-risk agreements as well as conflicts. Agreement is not proof
   when both agents reused the same application parser or source assumption.
6. Resolve a conflict only with raw source, independently generated output, or
   a durable artifact that directly supports the decision. Do not resolve by
   majority vote, confidence language, or averaging counts.
7. Where necessary, run a bounded recheck through the end-user production path
   and retain the result in a neutral Stage 2 witness folder.
8. Preserve `BLOCKED` and `N/A` separately. State what source or product
   capability would unblock each item.
9. Confirm that the frozen archive came from the SSOR-prod development site and
   that permanent/main-site equivalence remains future work.

Update `FINAL-RECONCILIATION.md` with:

- a conflict matrix covering every non-identical result;
- one row for every independent finding, mapped to its counterpart or marked
  unique;
- the evidence used to resolve each conflict;
- the agreed deliverable matrix and exact terminal totals;
- any unresolved issue and its recheck owner;
- separate reviewer sign-off sections for Codex and Claude.

Build `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` as the sole canonical findings
inventory:

- assign stable IDs `PCOA-FINAL-001`, `PCOA-FINAL-002`, and so on;
- map every final ID back to all `PCOA-CX-*` and `PCOA-CL-*` source IDs;
- include severity, report family, comparison type/workflow, values/formulas
  scope, evidence scope, verified behavior, user impact, verified root cause
  or explicitly labeled hypothesis, durable witness paths, and a measurable
  acceptance test;
- include a file/subsystem ownership hint only when supported by inspection;
- record clean/approved behavior that must not regress;
- contain no proposed code patch and no bundle assignment yet.

Reviewer protocol:

- If you are the first Stage 2 reviewer, fill the documents, sign your section,
  mark both files `AWAITING SECOND REVIEW`, commit, and stop.
- If you are the second reviewer, independently challenge every conflict
  resolution and every final finding. Correct errors with an audit trail.
- Stage 2 is complete only when both reviewers sign, every independent finding
  is mapped, every matrix decision is terminal, no conflict is unresolved, and
  `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` covers all agreed defects exactly
  once.

After both reviewers approve:

1. Mark both Stage 2 documents `JOINTLY APPROVED`.
2. Commit the documentation.
3. Merge the reconciliation branch, which must already contain the frozen
   Claude Stage 1B commit, into `main` without force.
4. Push `main` only after fetching and confirming it has not diverged.
5. Delete only the fully merged temporary audit/reconciliation branches and
   their worktrees. Preserve `main`, `gh-pages`, and unrelated/unmerged work.
6. Do not implement fixes yet.

Report the joint decision totals, canonical finding count by severity, any
future/blocked tests, the `main` commit SHA, and that Prompt 03 is unblocked.

---
