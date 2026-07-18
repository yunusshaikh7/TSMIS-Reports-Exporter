# Comparison-perfection

Last updated: 2026-07-17

The dedicated planning + evidence folder for the comparison-perfection project. It is
organized so you can see **where the project is** without reading days of audit history.

**Current position (2026-07-17):** the owner-authorized remediation is live on branch
`comparison-perfection` (offline gate 130/130, CI-green). ~159 of 241 findings closed
(Resolved/Remediated), ~10 partial, ~71 open — the correctness-critical core (shared
engine, the 12 comparison families, Stage-8 base audits 7/7, identity gate 11/0, all owned
provenance/projection findings, the C-bucket loader gates) is done; the open tail is
hardening + non-product instrument work. Sol-001 reliability hardening was integrated this
session. See **[COMPLETION-PLAN.md](COMPLETION-PLAN.md)** "YOU ARE HERE" for the live detail.

## ▶ Start here

**[COMPLETION-PLAN.md](COMPLETION-PLAN.md)** — the single "you are here" surface: current
position, the full phase map to completion, the execution waves, external dependencies,
and an append-only progress log. Read it first; everything else is data it points into.

## Structure

```
COMPLETION-PLAN.md   ← the plan & status (start here)
README.md            ← this index
reference/ (below)   ← living data ledgers — trust these over any prose
archive/             ← retired status/handoff/reconciliation history (point-in-time)
```

### Reference — living data

| Document | Role |
|---|---|
| [comparison-audit-findings.md](comparison-audit-findings.md) | The authoritative 241-finding ledger (~159 closed / ~10 partial / ~71 open) |
| [comparison-canary-bindings.md](comparison-canary-bindings.md) | Exact sources, counts, result/acceptance hashes |
| [comparison-phase4-tsn-source-rebaseline.md](comparison-phase4-tsn-source-rebaseline.md) | Raw TSN roles, manifests, source facts |
| [comparison-phase3-decision-gates.md](comparison-phase3-decision-gates.md) | Approved comparison-engine semantics (D1–D7) |
| [comparison-phase4-red-fixture-index.md](comparison-phase4-red-fixture-index.md) | Finding → red-fixture / family-gate ownership |
| [comparison-remediation-plan.md](comparison-remediation-plan.md) | The detailed Phase 0–10 roadmap |

### Archive — history

[archive/](archive/README.md) holds the retired dashboard, handoff, reconciliation
report, takeover prompt, and the advisory Claude/Fable reviews. Kept verbatim as
point-in-time history; their counts and hashes are as-written, not current. Trust
`COMPLETION-PLAN.md` and the reference ledgers over anything there.

## Current boundary (snapshot — the plan is authoritative)

- Stage 6 raw→normalized conservation: **7/7**.
- Stage 8 base TSMIS-vs-TSN audit: **7/7** (witnesses hash-verified on disk).
- Stages 9–10 companion/historical/evidence, Stage 11 remediation, Stage 12 release: **open**.
- 122 reproduced-and-open findings (44 family-gate + 78 unowned).
- Branch `comparison-perfection`, CI green, gate 121/121 (+4 documented-red under CMP-AUD-045).

The separate repository-wide Fable audit remains at
[../fable5-repo-improvement-audit.md](../fable5-repo-improvement-audit.md) with its protected
SHA-256 `9deedb03d284af4bf005be16600c30544b05e0ba54801a4532b05587418b6d0e`.

Return to the general [documentation index](../../INDEX.md).
