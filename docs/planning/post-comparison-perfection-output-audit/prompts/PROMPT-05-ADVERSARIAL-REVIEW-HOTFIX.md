# Prompt 05 — Bounded Adversarial Review and Approval of One Hotfix

Use this prompt sequentially with the two assigned reviewers. At least one
approver must not be the bundle's implementer.

Before using, replace:

- `<BUNDLE_ID>` with the implemented **RB bundle ID**. HF IDs are work-item
  specs and are not reviewed separately while their RB remains combined.
- `<REVIEWER>` with the assigned reviewer.

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

## Preconditions

- For Review 1, the bundle status is
  `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`.
- For Review 2, the bundle status is
  `REVIEW 1 APPROVED — AWAITING REVIEW 2`.
- The hotfix branch and retained outputs exist.
- The implementation document identifies an exact base/head SHA.
- Every expensive acceptance operation required by `BUNDLE.md` has already
  been performed by the implementation and is represented by a retained,
  hash-bound result.
- `<BUNDLE_ID>` and `<REVIEWER>` were replaced.

If a precondition fails, stop and record one exact missing item. Do not review
a different bundle, build replacement implementation evidence, or enter an
open-ended investigation.

## Non-duplication and review budget

**Review validates implementation evidence; it does not repeat the
implementation.** Independence means independent reasoning, diff inspection,
targeted probes, and attempts to falsify the recorded result. It does **not**
mean regenerating the same statewide workbooks, rerunning the same full raw
recount, or recalculating the same large Excel file.

Use evidence in this order:

1. exact source diff and commit identities;
2. committed tests and machine-readable witnesses;
3. retained deliverables bound by path, size, SHA-256, source identity, and
   generation metadata;
4. Review 1's signed evidence, when performing Review 2;
5. small targeted reviewer probes only where the preceding evidence leaves a
   concrete uncertainty.

A `BUNDLE.md` instruction to generate, recalculate, recount, render, or inspect
an acceptance corpus is an obligation for the implementation evidence set. It
is **not** an instruction for each reviewer to repeat that costly operation.
The reviewer verifies its binding, coverage, internal consistency, and selected
adversarial examples. Regenerate only when a concrete mismatch makes the
retained evidence unusable.

Hard limits for one review:

- The review must be shorter than the recorded implementation effort and has
  an absolute ceiling of **30 minutes** of active wall-clock work.
- Reviewer-started processes may not exceed **2 GB additional working memory**.
- Do not start an operation expected to run longer than **5 minutes**, create
  more than **500 MB** of new output, or require installed Excel
  `CalculateFullRebuild` without explicit owner approval obtained **before**
  starting it.
- Never launch a fresh statewide GUI generation, whole-corpus comparison,
  installed-Excel full rebuild, full raw-source recount, complete image
  recapture, or frozen application build when valid same-head evidence already
  exists.
- Do not create a new bespoke whole-corpus audit framework during review.
  Missing implementation evidence is an evidence gap to report, not a project
  for the reviewer to reconstruct.
- Attempt a failing reviewer tool or harness at most once. A sandbox, console,
  rendering, or reviewer-machine failure is not a product failure and does not
  authorize repeated or larger retries.
- At the budget boundary, stop tools and issue the verdict from the evidence
  already checked. Do not leave the review in a self-extending loop.

Any exception requires the owner's explicit approval with the expected runtime,
memory, and output size stated first. Without that approval, use retained
evidence or return one bounded evidence-gap finding.

## Bounded adversarial review

Assume the implementation may be subtly wrong, but test that hypothesis
proportionately:

1. Confirm the diff contains the whole agreed scope and no unrelated changes.
2. Confirm the original defect is bound to a durable pre-fix witness and the
   new tests fail on the recorded base and pass on the reviewed head.
3. Map every acceptance criterion to an exact test, witness, retained artifact,
   or rendered page. Reject stale, unbound, incomplete, or contradictory
   evidence.
4. Inspect the changed logic independently and identify the most plausible
   regression or false-pass mechanism.
5. Run only the targeted tests needed to challenge that mechanism. Verify the
   implementation's recorded full gate rather than rerunning it; the full
   post-merge smoke runs once on `main`.
6. For source truth, inspect the independent reader's method and verify a small
   deterministic set of raw rows, boundary cases, totals, and genuine
   discrepancies. Do not repeat a whole-corpus recount that is already
   hash-bound.
7. For values and formulas, verify retained twin identities, cached-error and
   self-check results, exact changed-cell classes, totals, and parity witnesses.
   Do not perform another full Excel recalculation when a successful
   same-head recalculated artifact is retained.
8. Inspect the retained native-scale renders for every changed sheet. Re-render
   only a missing or contradictory page. Large image sets must have an
   automated manifest/coverage oracle; manually inspect the named risk cases,
   not a second complete capture.
9. Verify sibling parity and evidence eligibility from retained manifests,
   source bindings, and targeted images where applicable. Prove prohibited
   artifacts absent with the recorded automated gate.
10. Verify neighboring-family invariance through semantic/state/count/typed
    outcome witnesses and one targeted gate. Raw OOXML package bytes are not an
    ordinary regression invariant.
11. Challenge performance, atomic publication, provenance, stale-cache,
    rerun/idempotency, and failure behavior through existing focused tests and
    retained transaction records.
12. For Review 2, explicitly state what Review 1 could have missed and how the
    bounded challenge addressed it. Do not copy Review 1 and do not recreate
    Review 1's entire run.

Approval does not require the reviewer to reproduce every expensive operation.
It requires exact same-head evidence for every acceptance criterion, an
independent challenge of the changed logic, and no unresolved contradiction.

## Review record

Update `hotfix-bundles/<BUNDLE_ID>/REVIEW.md` with:

- reviewer identity, review number, and whether the reviewer implemented the
  bundle;
- branch/base/runtime-head/review-record-head SHA reviewed;
- elapsed review time and confirmation that the resource budget was respected;
- evidence reused, including hashes, and the small commands newly run;
- acceptance-criterion coverage and the adversarial challenge performed;
- exact deliverable and discrepancy results;
- values/formulas, visual, evidence, and regression matrices;
- Review 2's challenge to Review 1, when applicable;
- actionable failures with file/artifact references;
- final verdict `APPROVED` or `DENIED`;
- reviewer signature and timestamp.

## The practical-impact gate — apply this BEFORE any verdict

This is an internal tool, not an audited system of record. A finding blocks
only if it changes what the app DOES for a user: wrong output, stale or lost
data presented as current, a crash, or a silent failure.

For every candidate finding, write one line: **what would a user see
differently because of this?** If the honest answer is "nothing", it is a
NOTE in the review record — never a denial — no matter how it reads against a
criterion's wording. A criterion whose wording is stricter than its purpose is
a wording bug; say so and note it.

Findings that are NOTES by this test, not denials:

- cosmetics — widths, spacing, colours, layout;
- which commit hash a record cites, or how a record is worded;
- a bounded coverage limitation the implementation already disclosed with its
  measured incidence;
- anything the implementation already recorded as a deliberate trade-off with
  its reasoning.

**Two denials per bundle is the ceiling.** After a second denial, remaining
findings are logged as follow-up items and the bundle proceeds. Whether a
follow-up is worth another round is the owner's call, not the reviewer's.

Never require a re-run whose only effect is to make a record cite a tidier
commit. If the recorded facts are true and the behaviour is proved, that is
acceptance.

## Decision protocol

- A concrete acceptance failure **that passes the practical-impact gate** means
  `DENIED — RETURN TO IMPLEMENTATION`.
- A material missing or unbound artifact means `DENIED — EVIDENCE GAP`, naming
  exactly one bounded item the implementation must supply. The reviewer does
  not generate it.
- Reviewer-environment failures are recorded separately and are not charged to
  the product unless an existing product test or retained transaction record
  corroborates them.
- If every criterion has exact same-head evidence and the adversarial challenge
  finds no contradiction, the verdict is `APPROVED`. Do not withhold approval
  merely because the reviewer did not duplicate an already successful
  expensive run.
- If you are the first approving reviewer, mark it
  `REVIEW 1 APPROVED — AWAITING REVIEW 2`, commit the review record, and stop.
- If you are the second approving reviewer, the bundle is mergeable only when
  both reviews approve and at least one approver is not the implementer.

No review may respond to uncertainty by silently expanding scope. It must
approve, deny for a concrete failure, or deny for one exact evidence gap within
the review budget.

## After final approval

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
9. Prepare the next bundle's readiness record from this updated `main`; do not
   begin its implementation or expensive acceptance run inside this review.

Report the verdict, exact failing criteria or approval evidence, reviewer
sign-offs, merge SHA if merged, branch/worktree cleanup, and the next eligible
bundle ID.

---
