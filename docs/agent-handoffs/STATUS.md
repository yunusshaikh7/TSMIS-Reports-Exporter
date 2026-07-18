# Agent collaboration — overall status (authoritative)

**Claude owns this file.** Sol never edits it. It is the single source of truth for who
owns what, where each agent is, and what happens next. Product/architecture truth lives in
the `docs/` library and `docs/planning/comparison-perfection/` — this file only links.

_Last updated: 2026-07-17 by Claude._

## Shared baseline
- **Verified integration commit:** `a4ccd23` (branch `comparison-perfection`, CI-green,
  offline gate 127/127). This is the recorded shared starting point.
- **Sol branch-point commit:** `de54eb4`; charter tuned for the local worktree at `2543a02`
  (`agent/sol/reliability-hardening`, pushed to origin).
- **Environment (LOCAL worktrees — Codex Cloud was unavailable for Sol):**
  - Claude (Lead): worktree `C:\Users\Yunus\Projects\TSMIS-Reports-Exporter` on
    `comparison-perfection` (Windows).
  - Sol: **separate** worktree `C:\Users\Yunus\Projects\TSMIS-sol-reliability` on
    `agent/sol/reliability-hardening` (local Codex CLI runs HERE). Shares the same `.git`, so
    Sol's commits are visible to the Lead immediately via `git log agent/sol/reliability-hardening`
    (no fetch needed); Sol also pushes to origin for backup. Sol runs the authoritative Windows
    gate itself (reusing the Lead's `build\.venv` interpreter by absolute path; never pip-installs
    into it). **Neither agent touches the other's worktree.**

## Lanes

| | Claude (integrator + own workstream) | Sol (sol-001) |
|---|---|---|
| **Outcome** | Finish the comparison-perfection project to source-first, byte-proven completion | Harden + offline-test the reliability engine (self-update, export loop, auth/session) |
| **State** | **Active** | **Accepted, integrated + CLEARED** (2026-07-17) |
| **Branch** | `comparison-perfection` | ~~`agent/sol/reliability-hardening`~~ merged @ `7a7f0e7`, then worktree + branch (local + origin) removed — all work is on comparison-perfection |
| **Owns (modify)** | comparison engine + consolidators + tsn library + matrices + evidence + their checks + the comparison-perfection docs | updater / exporter* / run_report / batch_manifest / export_multi / auth_nav / session / login / browser_channels / edge_device / timeouts / report_library / logging_setup + their checks |
| **Must avoid** | Sol's engine modules (unless they block comparison — coordinate) | the comparison engine, the GUI (`gui_*`, `ui/`), `report_catalog`/`reports`, `version.py`, build `.ps1` |
| **Charter** | `docs/planning/comparison-perfection/COMPLETION-PLAN.md` (RESUME block) | `sol-001/CHARTER.md` |
| **Next** | resume comparison-perfection at buckets B/D/E/G/H/I (063 + 027 + MER-059 DONE) | mission complete — no further sol-001 work |

## sol-001 integration record (2026-07-17)

**Reviewed as an untrusted candidate, ACCEPTED, and merged** (`agent/sol/reliability-hardening`
`2543a02..8bcd1e1` → merge `7a7f0e7`, CI-green SHA-verified). Review outcome:
- **Off-limits: clean.** Every touched `scripts/` file is in Sol's owned set (updater, exporter,
  batch_manifest, login, session, site_target, report_nav, browser_channels, edge_device,
  timeouts); build changes are its matching + two new checks. NO comparison / GUI /
  `report_catalog` / `reports` / `version.py` / `.ps1` / `checks.yml` file touched. No
  shared-infra (`outcome`/`errors`/`events`/`settings`/`paths`) modified — Sol flagged F-01 instead.
- **Hard rules: clean.** No `print`/`input`/`sys.exit` in core, no `requests`/`certifi`/`verify=False`
  in the updater (TLS rule intact), only stdlib `secrets` added.
- **Substantive fixes verified sound:** updater readiness-handshake + rollback-relaunch suppression
  (F-02/03/07, backward-compatible across all upgrade/revert directions); combined-export retry
  accounting (F-08); batch-manifest step validation (F-09). Auth changes (F-11–15) verified
  DIAGNOSTIC-ONLY (added type+first-line logging, byte-identical fallback control flow). No check
  weakened (the 16 removed check_updater lines were obsolete death-window tests replaced by the new
  mechanism; the 2 baseline removals are sites Sol actually fixed).
- **Gate:** full offline **130/130** in the main worktree (was 128 + Sol's 2 new checks);
  `check_source_zip_smoke` passes here (Sol's lone red F-01 was a linked-worktree `.git`-is-a-file
  artifact only).
- **F-01 CLOSED by the integrator** (`99b7ab2`): `check_source_zip_smoke` now resolves the object
  store via `git rev-parse --git-common-dir`; red→green proven in a real linked worktree.
- **All 16 findings reconciled.** F-01–09, F-11–15 are the merged fixes/proofs. F-16 (CI YAML
  auto-glob) is a non-issue — Sol correctly left `checks.yml` alone. **F-10 RECONCILED — not a
  defect** (2026-07-17): the suspected `check_pdf_role_provenance` flake did not reproduce in
  **15 runs** (8 standalone + 7 parallel `-j 4` full gates, all green); Sol's single observed
  failure was a nonzero PROCESS exit with no output under heavy parallel pdfplumber load — an
  environmental resource transient (the known RAM-contention lesson), not a logic error. Monitor
  only.
- **Work-PC-only re-verifies for the OWNER** (not verifiable offline — the only remaining Sol
  items): one real frozen update swap/relaunch + Revert (F-02/03/07), headed console sign-in
  (F-14), managed-Edge policy fallback (F-15).
- **CLEARED 2026-07-17** (owner-authorized): everything integrated + reconciled, so Sol's worktree
  `C:\Users\Yunus\Projects\TSMIS-sol-reliability` and the branch `agent/sol/reliability-hardening`
  (local + origin) were removed. Its only untracked file was `AGENTS.md` (a 36 KB local copy of
  `CLAUDE.md` for Codex — regenerate with `cp CLAUDE.md AGENTS.md` for a future sol-002 worktree).
  The sol-001 docs (this record + `sol-001/CHARTER/FINDINGS/FINAL_REPORT/SOL_STATUS`) are KEPT on
  comparison-perfection as the mission record.

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
- **2026-07-17** — **Env correction:** Codex Cloud can't run Sol → switched to LOCAL worktrees.
  Created Sol's worktree `C:\Users\Yunus\Projects\TSMIS-sol-reliability`; charter updated for
  local-Windows runtime (Sol runs the authoritative gate itself). Recovered the Lead worktree
  after it was briefly switched to `main`/`de54eb4` during setup — no work lost (all commits
  safe on `comparison-perfection` @ `9c6db69` + origin). Both worktrees verified isolated.

## State vocabulary
Planned · Active · Blocked · Verification · Ready for review · Changes requested ·
Accepted · Idle · Superseded.
