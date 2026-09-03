# Comparison-perfection

Last updated: 2026-07-22

> ## ✅ COMPLETE — shipped as v0.28.0, merged to `main` (2026-07-22)
>
> **237 of 242 findings closed (98%).** The branch fast-forwarded into `main`, so `main`
> is the completion state and new work branches from it. Offline gate **152/152**, ruff
> clean, frozen self-test PASSED on the exact shipped exe, CI green.
>
> **UPDATE 2026-08-20: every finding is CLOSED — 245 of 245.** Two more were found and
> fixed after this project shipped, both by the work that came next: **244** (v0.38.2 —
> Highway Detail vs TSN was counting the paired-roadbed ditto convention as data;
> statewide 174,837 → 160,347 differing cells, pairing untouched) and **245** (v0.39.1 —
> the ArcGIS Highway Detail projection counted the HF-01 unavailable marker as data and
> reported COMPLETE over a PARTIAL build). **2026-09-02: 246 of 246** — **246** (the
> Highway Sequence Excel-vs-TSN equate seat: the export puts the `E` on the realignment
> record where TSN puts it on the target, so both rows of ~220 relations went one-sided;
> now seated the TSN way before keying, 57,072 → 57,518 paired on the bound 7.9 pair).
> New findings still get an entry here even
> though the project is closed; open WORK lives in [`docs/roadmap.md`](../../roadmap.md).
>
> **UPDATE 2026-08-18 (v0.38.0): 243 of 243 closed at that date.** The five
> that were open here (133 · 142 · 186 · 192 + 045-HD) were the ⛔ Highway Detail
> pre-release block. The vendor RELEASED Highway Detail on 2026-08-17, which retired the
> freeze; v0.37.0 closed 192 (and found + fixed 243), and v0.38.0 closed 186 · 053 · 133
> · 142 and took the owner's decision on 045-HD. Highway Detail's two editions now agree
> statewide: 51,327 locations, 0 one-sided, 51,327 fully identical, 0 differing cells.
> **Still never infer an HD county answer** — the Excel export does not carry one, and the
> owner ruled the Excel and PDF editions stay separate sources.
>
> **Owed, and only the owner can do it:** the work-PC acceptance run — now targeting
> **v0.41.0** (roadmap B1), not v0.28.0.
>
> **This folder is now the PROJECT RECORD, not a worklist.** Read it to learn why a
> comparison behaves the way it does. If you reopen a finding or open a new one, update
> its entry `Status:` line AND the ledger index table AND the plan together — index
> tables drifting behind entries caused repeated stale-directive incidents.

The dedicated planning + evidence folder for the comparison-perfection project. It is
organized so you can see **where the project ended up** without reading days of audit
history. See **[COMPLETION-PLAN.md](COMPLETION-PLAN.md)** for the full record.

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
