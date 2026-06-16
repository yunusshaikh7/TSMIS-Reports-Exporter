# code-review/ — index

Artifacts from the 2026-06 two-agent audit + source verification of TSMIS
Reports Exporter, and the plan to fix everything in the next patch. Audited
commit: **`0643fe2`** (app code identical to `v0.10.4`).

## Start here
- **RECONCILED-FINDINGS.md** — THE merged, prioritized findings + the
  **NEXT-PATCH PLAN** (source-verified severities at the top). *(local / git-ignored)*
- **NEXT-PATCH-HANDOFF.md** — kickoff doc for a fresh chat to implement the
  fixes. *(local / git-ignored)*

## Reusable prompts (tracked)
- **AUDIT-PROMPT.md** — the ruthless two-agent audit prompt.
- **SOURCE-VERIFY-PROMPT.md** — the source-backed verification prompt.
- **README.md** — how to run the two-agent audit (both local, same SHA, reconcile).

## Raw agent outputs (evidence — local / git-ignored)
- **AUDIT-claude-0643fe2.md** / **AUDIT-codex-0643fe2.md** — the two independent
  audits (27 / 21 findings).
- **SOURCE-VERIFY-claude-0643fe2.md** / **SOURCE-VERIFY-codex-0643fe2.md** —
  source-backed verification (verdicts + new mismatches).

## Reading order for a newcomer
1. `RECONCILED-FINDINGS.md` (the plan) → 2. the two `SOURCE-VERIFY` reports (what
the live site source confirmed/refuted) → 3. the two `AUDIT` reports (full
code-level evidence) → 4. `NEXT-PATCH-HANDOFF.md` (how to start fixing).

## External reference material (kept LOCAL — Caltrans internal, never in the repo)
- **Website source:** `Downloads\TSMIS\website-source\` (live SPA: `config.js`,
  `index.html`, `shared.js`, one JS per report).
- **Comparison outputs / approved samples / inputs:**
  `Downloads\TSMIS\{comparisons, samples-approved, inputs}\`.
- **Packaged app:** `Downloads\TSMIS\app\`.
