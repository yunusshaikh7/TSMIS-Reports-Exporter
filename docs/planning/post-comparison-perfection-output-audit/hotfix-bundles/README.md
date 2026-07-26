# Hotfix Bundle Records

This directory is the restart-safe handoff area for Stage 4 implementation and
Stage 5 adversarial review. The jointly approved
[implementation plan](../IMPLEMENTATION-PLAN.md) is authoritative.

For each agreed bundle, create:

```text
hotfix-bundles/
  <bundle-id>/
    BUNDLE.md
    IMPLEMENTATION.md
    REVIEW.md
```

- `BUNDLE.md` freezes scope and acceptance before code changes.
- `IMPLEMENTATION.md` records changed files, commands, generated outputs,
  source-truth checks, and residual risk.
- `REVIEW.md` records the two sequential adversarial reviews and merge gate.

Copy the templates below; do not edit the templates in place:

- [BUNDLE template](TEMPLATE/BUNDLE.md)
- [IMPLEMENTATION template](TEMPLATE/IMPLEMENTATION.md)
- [REVIEW template](TEMPLATE/REVIEW.md)

Run [Prompt 04](../prompts/PROMPT-04-IMPLEMENT-HOTFIX-BUNDLE.md) for
implementation and [Prompt 05](../prompts/PROMPT-05-ADVERSARIAL-REVIEW-HOTFIX.md)
for each review/approval loop.
