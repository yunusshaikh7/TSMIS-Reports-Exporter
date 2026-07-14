# Comparison-perfection planning

Last updated: 2026-07-14  
Status: Stage 6 and the Stage-8 base audit are complete at 7/7; the complete
comparison-perfection audit, product remediation, evidence proof, and release
acceptance are not complete

This folder is the dedicated planning and evidence index for the comparison-perfection
project. It was separated from the general planning archive so a new reviewer can
reconcile the project without treating every historical planning document as current.

## Start here

If a new AI or engineer is taking over, begin with
[new-ai-reconciliation-prompt.md](new-ai-reconciliation-prompt.md). Its first pass is
read-only reconciliation. It asks the reviewer to decide—based on dependencies rather
than assumption—whether the deferred Stage 9–10 companion/historical/evidence audit
should finish before any product correction.

For ordinary status review, read in this order:

1. [comparison-perfection-project.md](comparison-perfection-project.md) — owner
   directives, progress, completed audit layers, and deferred stages.
2. [comparison-implementation-handoff.md](comparison-implementation-handoff.md) —
   frozen product boundary and takeover sequence.
3. [comparison-audit-findings.md](comparison-audit-findings.md) — authoritative stable
   finding ledger through CMP-AUD-237.
4. [comparison-canary-bindings.md](comparison-canary-bindings.md) — exact sources,
   counts, result identities, and accepted/rejected witness boundaries.
5. [comparison-phase4-tsn-source-rebaseline.md](comparison-phase4-tsn-source-rebaseline.md)
   — raw TSN roles, manifests, normalization, and source facts.
6. [comparison-remediation-plan.md](comparison-remediation-plan.md) — dependency and
   implementation sequencing reference.

## Supporting records

| Document | Purpose |
|---|---|
| [comparison-phase4-red-fixture-index.md](comparison-phase4-red-fixture-index.md) | Finding-to-red-fixture and family-gate ownership |
| [comparison-phase3-decision-gates.md](comparison-phase3-decision-gates.md) | Approved comparison-engine semantic decisions |
| [claude-comparison-audit-second-opinion.md](claude-comparison-audit-second-opinion.md) | Advisory Claude review; evidence, not authority |
| [fable5-comparison-remediation-decisions.md](fable5-comparison-remediation-decisions.md) | Advisory Fable decision record; evidence, not authority |

The separate repository-wide Fable audit remains at
[../fable5-repo-improvement-audit.md](../fable5-repo-improvement-audit.md). It is not a
comparison-project planning document and must retain its protected SHA-256
`9deedb03d284af4bf005be16600c30544b05e0ba54801a4532b05587418b6d0e`.

## Current boundary

- Stage 6 raw-to-normalized conservation: 7/7 audit coverage.
- Stage 8 current base TSMIS-vs-TSN truth: 7/7 audit coverage.
- Stages 9–10 companion-format, historical-edition, and exhaustive evidence work:
  deferred, not complete.
- Stage 11 product remediation: not authorized by the final audit closeout.
- Stage 12 release acceptance: not complete.
- The seven family gates carry 44 unique known product/evidence finding IDs red; a new
  reviewer must independently reconcile that set rather than treating the count as
  authority.

The dirty takeover baseline for `scripts/` is 321 files / 7,423,809 bytes, canonical
manifest 34,351 bytes, SHA-256
`df7bb8fc3d997d60d82ecb93344f821e858feb015eed62fffe859958c9151bea`.
It identifies the frozen worktree state; it does not certify correctness or attribution.
Do not reset, rewrite, or clean the existing product changes merely to match Git HEAD.

Return to the general [documentation index](../../INDEX.md).
