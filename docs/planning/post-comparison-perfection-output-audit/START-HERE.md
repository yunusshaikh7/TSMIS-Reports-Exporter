# Post-Comparison Output Program — Start Here

Workflow state: **Stages 1A, 1B, 2, and 3 complete and jointly approved;
RB-1 / Clean Road is IMPLEMENTED — AWAITING ADVERSARIAL REVIEW (Stage 5), with
Review 1's blocking finding RB1-R1-001 implemented and re-accepted**

Last updated: 2026-07-28

This is the entry point for every new Codex or Claude chat. Read this file
before opening the other audit documents. The project deliberately separates
independent observation, cross-checking, planning, implementation, and
approval so that one agent's conclusions do not contaminate another agent's
first pass.

## Next action

Run
[`prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md`](prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md)
in a new **Codex** chat (review 1 of 2, re-review from the new head) with:

```text
<BUNDLE_ID> = RB-1
<REVIEWER> = Codex
```

RB-1 (work item HF-01, branch `hotfix/rb-1-clean-road-source-truth`) was
implemented, denied by Codex Review 1 on the clipped `ArcGIS Build` disclosure
(RB1-R1-001), and that return is now implemented: the marker sheet carries
measured stored column widths, wrapped cells in tall-enough rows, and the 102
skips as an itemized 14-column table. The build and both twins were
regenerated and the whole acceptance matrix re-run — the review's own
`REVIEW.md` findings table, the new "Review 1 remedy" section of
[`hotfix-bundles/RB-1/IMPLEMENTATION.md`](hotfix-bundles/RB-1/IMPLEMENTATION.md),
the frozen contract
[`hotfix-bundles/RB-1/BUNDLE.md`](hotfix-bundles/RB-1/BUNDLE.md) and the
committed witnesses `hotfix-bundles/HF-01/witness/` are the record. Bulk
acceptance output is retained at
`C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\` (the
remedy run in its `r1-remedy\` subfolder; Review 1's own proof files are
untouched). The branch is NOT merged.

Claude drafted the plan as first planner (both sign-off rows read `NOT STARTED`
when Prompt 03 was invoked, so the prompt's own first-planner rule applied — the
same reversal Stage 2 recorded). [`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md)
now holds **11 verified work-item specs (`HF-01` … `HF-11`) grouped into 6
implementation/review bundles (`RB-1` … `RB-6`), Clean Road first** — plus a finding-to-file overlap map
built by code inspection at `main` `a29bdb6`, all 22 canonical findings mapped to
exactly one primary spec, a merge order, a branch/worktree lifecycle, and a
whole-program definition of done. The batch layer is an owner decision (fewer
branches, reviews and releases; 12 Codex passes instead of 22). The plan also
defines **rush ship** — a named, owner-invoked exception under which a batch may be
released to the owner *before* its adversarial review, at most one at a time, with
the full gate, the acceptance run and the implementation record never deferred. It
is a capability, not a plan: no batch is scheduled to use it, and the default path
(implement → two reviews → merge → release) applies everywhere unless the owner
says otherwise for a named batch.

Codex completed the second-planner challenge and signed the plan. The final pass
re-opened the owning code, rechecked all 22 assignments, and made four material
corrections: (1) HF-01's 165 non-asserting cells now have the exact
`291,292 - 165 = 291,127` count oracle; (2) RB IDs now unambiguously control
Prompts 04/05, records, branches, statuses and merges; (3) HF-04 must produce
both censused layouts rather than pass through continued refusal; and (4)
ordinary workbook regression uses published semantic/state equivalence rather
than unreliable raw OOXML package-byte identity.
**All four owner policy gates are now RULED (2026-07-26)** — no open owner
question blocks the second planner:

- **HF-01 — mark the skipped anchors.** The Clean Road cells whose ArcGIS side was
  never built carry an explicit non-asserting "unavailable" marker and are
  excluded from the differing-cell count, rather than a bare blank that reads as
  a disagreement. All 165 affected `D` cells become `N`, so the exact post-fix
  count is **291,127**. Disclosure-only was rejected: it names the problem
  without naming which cells.
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

Both planners signed the Stage 3 plan. **RB-1 was READY, is now DENIED —
RETURN TO IMPLEMENTATION, and no other RB is authorized yet.**

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
| 3 | Agree on ordered implementation bundles | **COMPLETE — JOINTLY AGREED** | `prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md` | `IMPLEMENTATION-PLAN.md`, `hotfix-bundles/RB-1/BUNDLE.md` |
| 4 | Implement one bounded RB bundle | **RB-1 DENIED — RETURN TO IMPLEMENTATION** | `prompts/PROMPT-04-IMPLEMENT-HOTFIX-BUNDLE.md` | Hotfix branch plus `hotfix-bundles/<RB-ID>/IMPLEMENTATION.md` |
| 5 | Adversarially review and approve that bundle | **REVIEW 1 DENIED — LOOP TO STAGE 4** | `prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md` | `hotfix-bundles/<RB-ID>/REVIEW.md`; merge or return to Stage 4 |

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
