# Hotfix Bundle Records

This directory is the restart-safe handoff area for Stage 4 implementation and
Stage 5 adversarial review. The jointly approved
[implementation plan](../IMPLEMENTATION-PLAN.md) is authoritative.

HF IDs in the plan are work-item specs. RB IDs are the actual
implementation/review bundle, branch and Prompt 04/05 unit. For each agreed RB
bundle, create:

```text
hotfix-bundles/
  <RB-ID>/
    BUNDLE.md
    IMPLEMENTATION.md
    REVIEW.md
  <HF-ID>/
    witness/
```

- `BUNDLE.md` freezes scope and acceptance before code changes.
- `IMPLEMENTATION.md` records changed files, commands, generated outputs,
  source-truth checks, and residual risk.
- `REVIEW.md` records the two sequential adversarial reviews and merge gate.
- `<HF-ID>/witness/` holds the small machine-readable oracle evidence for that
  work item; it does not create a separate branch or review.

Copy the templates below; do not edit the templates in place:

- [BUNDLE template](TEMPLATE/BUNDLE.md)
- [IMPLEMENTATION template](TEMPLATE/IMPLEMENTATION.md)
- [REVIEW template](TEMPLATE/REVIEW.md)

Run [Prompt 04](../prompts/PROMPT-04-IMPLEMENT-HOTFIX-BUNDLE.md) for
implementation and [Prompt 05](../prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md)
for each review/approval loop.
