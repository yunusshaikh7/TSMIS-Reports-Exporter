# Comparison Deliverable Hotfix Implementation Plan

> Workflow artifact: **Stage 3 — jointly agreed hotfix plan**
>
> Status: **BLOCKED — Stage 2 is not jointly approved**
>
> Authority: Once signed by both reviewers, this file controls bundle order,
> scope, ownership, branch lifecycle, and acceptance gates.
>
> New-chat entry point: [START-HERE.md](START-HERE.md). Create the plan with
> [Prompt 03 — agree implementation plan](prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md).

## Planning rules

- Clean Road is the first implementation bundle because it is the user's
  immediate operational need.
- Prefer one report family per bundle when files and regression risks are
  separable. Use a shared-subsystem bundle only when splitting would duplicate
  changes or create unsafe intermediate states.
- Every canonical finding maps to exactly one implementation bundle.
- Every bundle starts from the then-current `main`, uses its own
  `hotfix/<bundle-id>-<slug>` branch and worktree, and merges to `main` only
  after both adversarial reviews approve it.
- A later bundle never branches from an unmerged earlier bundle.
- `main` and `gh-pages` are persistent. Completed hotfix and temporary audit
  branches are deleted only after their commits are confirmed on `main`.
- Audit evidence is immutable. Implementation and review artifacts live under
  `hotfix-bundles/<bundle-id>/`.

## File-overlap and dependency map

| Finding IDs | Likely implementation files / subsystem | Report families | Coupling or ordering constraint | Planner conclusion |
|---|---|---|---|---|
| PENDING | PENDING | PENDING | PENDING | PENDING |

## Agreed bundle queue

| Order | Bundle ID | Name | Canonical finding IDs | Scope style | Depends on | Branch | Status |
|---:|---|---|---|---|---|---|---|
| 1 | PENDING-CLEAN-ROAD | Clean Road deliverable perfection | PENDING | Report family | None | `hotfix/<bundle-id>-clean-road` | BLOCKED |

Allowed statuses are:

- `BLOCKED`
- `READY`
- `IMPLEMENTING`
- `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`
- `REVIEW 1 APPROVED — AWAITING REVIEW 2`
- `DENIED — RETURN TO IMPLEMENTATION`
- `JOINTLY APPROVED`
- `MERGED`

## Finding coverage

| Canonical finding ID | Bundle ID | Acceptance oracle copied exactly | Coverage check |
|---|---|---|---|
| PENDING | PENDING | PENDING | UNVERIFIED |

The completed table must contain every canonical finding exactly once.

## Per-bundle specification

For each queue row, create `hotfix-bundles/<bundle-id>/BUNDLE.md` from the
template in [hotfix-bundles/README.md](hotfix-bundles/README.md). It must freeze:

- in-scope canonical findings and exact acceptance oracles;
- allowed implementation files and tests;
- explicit out-of-scope items;
- end-user generation paths and source fixtures;
- values, formulas, source-truth, visual, sibling-parity, and evidence gates;
- prerequisite bundles and regression surface;
- implementer/reviewer separation and merge/rollback procedure.

## Planner challenge log

| Question or disputed bundle boundary | First planner position | Second planner challenge | Source-backed resolution |
|---|---|---|---|
| PENDING | PENDING | PENDING | PENDING |

## Joint planning approval

| Reviewer | Pass | Decision | Commit | Date | Notes |
|---|---|---|---|---|---|
| Codex | First plan | NOT STARTED | PENDING | PENDING | |
| Claude | Final challenge | NOT STARTED | PENDING | PENDING | |

No implementation begins until both decisions are `APPROVED`, every finding is
mapped exactly once, and the first bundle is marked `READY`. Then use
[Prompt 04 — implement a hotfix bundle](prompts/PROMPT-04-IMPLEMENT-HOTFIX-BUNDLE.md).
