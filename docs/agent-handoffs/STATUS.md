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

## Log
- **2026-07-17** — Baseline established at `a4ccd23`. Handoff structure created. sol-001
  charter authored (reliability engine hardening). Environment: Codex Cloud + branch.
  Next: push Sol's branch, dispatch the mission prompt, then resume comparison finding 063.

## State vocabulary
Planned · Active · Blocked · Verification · Ready for review · Changes requested ·
Accepted · Idle · Superseded.
