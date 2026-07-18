# Agent collaboration — overall status (authoritative)

**Claude owns this file.** Sol never edits it. It is the single source of truth for who
owns what, where each agent is, and what happens next. Product/architecture truth lives in
the `docs/` library and `docs/planning/comparison-perfection/` — this file only links.

_Last updated: 2026-07-17 by Claude._

## Shared baseline
- **Verified integration commit:** `a4ccd23` (branch `comparison-perfection`, CI-green,
  offline gate 127/127). This is the recorded shared starting point.
- **Sol branch-point commit:** `de54eb4` (adds `docs/agent-handoffs/`; `agent/sol/reliability-hardening` is cut from and pushed at this commit).
- **Environment:** Claude works in the primary worktree on `comparison-perfection`
  (Windows). Sol works in a Codex Cloud Linux sandbox on `agent/sol/reliability-hardening`,
  pushing milestone commits to the GitHub remote. Monitoring = `git fetch` of Sol's branch.

## Lanes

| | Claude (integrator + own workstream) | Sol (sol-001) |
|---|---|---|
| **Outcome** | Finish the comparison-perfection project to source-first, byte-proven completion | Harden + offline-test the reliability engine (self-update, export loop, auth/session) |
| **State** | **Active** | **Planned** (dispatch pending) |
| **Branch** | `comparison-perfection` | `agent/sol/reliability-hardening` |
| **Owns (modify)** | comparison engine + consolidators + tsn library + matrices + evidence + their checks + the comparison-perfection docs | updater / exporter* / run_report / batch_manifest / export_multi / auth_nav / session / login / browser_channels / edge_device / timeouts / report_library / logging_setup + their checks |
| **Must avoid** | Sol's engine modules (unless they block comparison — coordinate) | the comparison engine, the GUI (`gui_*`, `ui/`), `report_catalog`/`reports`, `version.py`, build `.ps1` |
| **Charter** | `docs/planning/comparison-perfection/COMPLETION-PLAN.md` (RESUME block) | `sol-001/CHARTER.md` |
| **Next** | findings 063 (PM-token→partial) + 027 (header-only route) → MER-059 census → buckets B/D/E/G/H/I | read charter §3, plan, then §5 A→E |

## High-conflict shared files (either lane may need them — coordinate before modifying)
- `.github/workflows/checks.yml` — both lanes append new check names. **Claude resolves
  conflicts at integration.** (Runner auto-globs, so only this manifest is shared.)
- `scripts/outcome.py`, `errors.py`, `events.py`, `settings.py`, `paths.py`, `contract.py`,
  `validation.py` — shared infra. Sol reads/tests freely; **modifies only via a flagged
  required-change finding.** Claude retains ownership of `outcome.py`.

## Collision analysis (pre-dispatch)
- Sol's modules import shared infra (`outcome`, `errors`, `events`, `settings`, `paths`)
  but Claude is not editing those for the current comparison findings (063/027 live in
  `compare_tsn_common`/`compare_env`). Expected file-level overlap: **only `checks.yml`**
  (append-merge, low risk) and any shared-infra change Sol flags. No overlap in product code.
- `report_library.py` is Sol's (export freshness) and is comparison-adjacent only through
  the matrix, which Claude does not touch this pass. Low risk.

## Parked backlog (owner notes 2026-07-17)
13 owner feature/hardening notes captured + triaged in
[docs/planning/app-consistency-backlog.md](../planning/app-consistency-backlog.md). Most are
comparison-lane / GUI / cross-cutting **architecture** (Claude), NOT Sol's reliability lane.
The spine (items 9/10/11/13 = output-model unification) is design-first + coupled to
comparison-perfection. **Design spec DONE:**
[docs/planning/output-model-unification.md](../planning/output-model-unification.md) —
**sol-002** (export-side conformance: unified run-folder writes, single-pass dual-format,
date-stamping) is now scoped, with a **hard dependency**: Claude lands the additive `paths.py`
SoT functions (migration step 1) BEFORE sol-002 starts. The comparison-side (unique names,
manual-Compare folder) + GUI dropdowns stay Claude's. sol-001 is unchanged by this.

## Fleet scaling (decided 2026-07-17)
Owner can run 3+ Codex agents (unlimited compute); a dedicated **Orchestrator Claude** (local,
Windows) is designed to coordinate + run the authoritative gate on Sol branches so the Lead
(this Claude) stays on comparison-perfection. Orchestrator prompt is authored (in-session);
deploy it when 2+ Sol agents are live. Decision: run sol-001 now (single agent, Lead
coordinates lightly); Lead specs the output-model to generate the next clean lane (sol-002);
stand up the Orchestrator when 2–3 lanes are live. Authority split: Lead owns architecture +
mission definition + final integration + done; Orchestrator owns fleet monitoring/review/test/
docs (no product code, no merge into comparison-perfection); Sol executes.

## Log
- **2026-07-17** — Baseline established at `a4ccd23`. Handoff structure created. sol-001
  charter authored (reliability engine hardening). Environment: Codex Cloud + branch.
  Next: push Sol's branch, dispatch the mission prompt, then resume comparison finding 063.
- **2026-07-17** — Owner supplied a 13-item post-comparison backlog; captured + triaged
  (app-consistency-backlog.md). sol-001 kept focused (not expanded). Output-model unification
  flagged as design-first architecture (Claude), sol-002 candidate for the export mechanics.

## State vocabulary
Planned · Active · Blocked · Verification · Ready for review · Changes requested ·
Accepted · Idle · Superseded.
