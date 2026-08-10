# RB-4 — the Codex review launch prompt

Copy everything below the line into a fresh Codex task. It is deliberately
short: it points at the governing prompt rather than restating it, declares the
input domain, and sets a stopping condition. RB-2's review burned ten rounds on
column widths because the prompt did neither.

---

You are **Codex**, adversarially reviewing the implemented TSMIS comparison
hotfix bundle **RB-4**.

Follow
`docs/planning/post-comparison-perfection-output-audit/prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md`
with `<BUNDLE_ID> = RB-4` and `<REVIEWER> = Codex`. That prompt is the
procedure; everything here is the scope it needs.

**Where the code is.** The branch is checked out in a worktree, not the main
checkout:

- worktree `C:\Users\Yunus\Projects\wt-rb4`
- branch `hotfix/rb-4-evidence`, pushed, **never merged**
- base `72adf44`, runtime head `f4b55f2`, branch tip `0e59f6c`
- the diff to review: `git diff 72adf44 f4b55f2`

**Read the owner's amendment FIRST**, before the bundle's frozen text: the
amendment section of `hotfix-bundles/RB-4/BUNDLE.md`, then "The 2026-08-05
amendment" in `hotfix-bundles/RB-4/IMPLEMENTATION.md`. The owner re-ruled this
bundle mid-implementation and the amendment CONTROLS over the frozen text.
Reviewing against the original text will produce findings that are already
wrong by decision.

## The declared input domain

The change is **15 runtime files, +2427 / −518**, concentrated in
`scripts/visual_evidence.py` and the five `scripts/evidence_*.py` adapters,
plus the matrix/GUI/UI gates and 14 check files. It changes **what evidence
images are produced and for which cells** — it does not change any comparison
result, and the acceptance re-proved that (`counts` 26/26 identical to base).

Evidence exists for exactly **12 cells** (the four `_pdf` families × Everything
vs-TSN, By Day vs-TSN, Everything ENV) and is refused at the ENGINE BOUNDARY
for **14 others** (4 Excel-row vs-TSN, 5 SELF, Ramp Summary ENV).

## What I need from you

1. A **REACHABILITY verdict on every finding**: can it occur through a shipped
   entry point on the measured corpus? Only reachable findings block. Say so
   explicitly per finding — "unreachable, cosmetic" is a useful answer.
2. An explicit **code-clean verdict** if you find nothing in an area. Silence
   reads as "not checked".
3. Severity per PROMPT-05, and for anything you would block on, the concrete
   input → wrong output.

## Stopping condition

**One round.** Report what you find and stop. Do not end with an invitation to
look for more, and do not open a second pass unless a CRITICAL/HIGH finding
turns out to be real. Match depth to what this change can break: wrong or
misleading evidence images, or evidence appearing where it must not.

## Already known — do not re-report as new

These are measured, documented, and awaiting the owner's decision in
`_scratch/post-comparison-hotfixes/HF-05/rb4-a1/results/chain8-known-gap.md`.
Challenging the DISPOSITION is fair; rediscovering them is not:

- A column that renders some but not all of its target examples records no
  reason (1 column of 176). The zero-rendered path does record one.
- `Sig Chg. Date` renders no evidence in the three Highway Log sets. It is the
  last column, so a blank there can never be bracketed by the record's own ink.
  Disclosed in every Ledger.
- One Intersection Detail blank box (`ML_Traffic_Flow_1_pair.png`, route 232 @
  000.807) is correctly targeted — it is the print's own ruled cell — but no
  record in that crop anchors the column, so a reader cannot confirm it.

## Out of scope

- **Comparison semantics.** Counts are locked identical to base; the Ramp
  Detail `-` null-marker question is tracked separately in `docs/roadmap.md`.
- **Highway Detail.** Pre-release and excluded everywhere by owner ruling.
- The three acceptance chains' timing, and the harness under `_scratch`.
