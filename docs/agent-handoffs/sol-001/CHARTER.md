# CHARTER — sol-001: Reliability engine hardening & offline verification

**Owner/integrator:** Claude (this session). **Executor:** GPT-5.6 Sol Max (Codex Cloud).
**Authored:** 2026-07-17. **Status:** Planned → dispatch pending.

> This charter is authoritative for the mission. Sol must not silently rewrite it. If
> repository evidence contradicts it, record the discrepancy in `FINDINGS.md` and proceed
> safely where possible. Material scope/ownership changes come only as a charter amendment
> from Claude (recorded here + in `../STATUS.md`).

---

## 1. Concrete outcome

Bring the **non-comparison, non-GUI reliability engine** — the self-update path, the
export/reliability loop, and the auth/session/browser layer — to a genuinely hardened,
well-tested state: close the offline-doable open defects, and materially raise
**offline golden-check coverage** of their error and edge paths so the app's large
work-PC live-verification debt shrinks and future regressions are caught. Do **not**
change product behavior beyond the low-risk fixes your new tests justify.

## 2. Starting point

- **Repo:** TSMIS Reports Exporter. **Verified baseline commit:** `a4ccd23`
  (branch `comparison-perfection`, CI-green, offline gate 127/127).
- **Your branch:** `agent/sol/reliability-hardening`, cut from the commit that adds this
  charter (its SHA is recorded in `../STATUS.md`). Do all work there.
- **Runtime:** Codex Cloud Linux sandbox. Some checks/tooling are Windows-only (the
  frozen `build.ps1 -SelfTest`, Edge/CDP paths, `os.replace` swap timing). Run what you
  can; where a check cannot run on Linux, note it in `FINDINGS.md` — **Claude runs the
  authoritative full Windows gate at integration.**

## 3. Required context to read first (do not skip)

- `CLAUDE.md` (root) — conventions: **core is console-free** (Events sink, raise; never
  `print`/`input`/`sys.exit`), UI-neutral core strings, log every decision + swallowed
  exception (`type(e).__name__` + first line), call the **timeout accessors**
  (`report_timeout_ms()` …) not raw constants, sync Playwright + thread-affinity.
- `docs/engine-and-reliability.md` — the export loop runtime (resume/retry/skip/cancel/
  fast-fail/timeout/fast-mode) you are hardening.
- `docs/auth-and-signin.md` — the sign-in state machine, device SSO, Edge recapture, LNA.
- `docs/build-and-release.md` §updater + `docs/internals/updater-swap.md` — the updater
  download→verify→stage→swap→rollback path.
- `docs/it-and-security.md` — the work-PC capability model + the updater-TLS rule (**trust
  the Windows cert store via `ssl.create_default_context()`; never switch to
  requests/certifi** — it breaks corporate TLS inspection).
- `docs/roadmap.md` — the OPEN findings you are closing (see §5) and the deferred ones.
- `build/run_checks.py` — the local gate; it auto-globs `build/check_*.py` (never name a
  new check `check_phase*` — that prefix is excluded from the gate).
- `git log --oneline -20` + the modules in §4 before touching them.

## 4. Ownership boundaries

### YOURS to modify (the reliability engine + its checks)
- **Self-update:** `scripts/updater.py`, `scripts/logging_setup.py`
- **Export/reliability:** `scripts/exporter.py`, `scripts/exporter_parallel.py`,
  `scripts/export_multi.py`, `scripts/run_report.py`, `scripts/batch_manifest.py`,
  `scripts/report_library.py`
- **Auth/session/browser:** `scripts/auth_nav.py`, `scripts/session.py`,
  `scripts/login.py`, `scripts/site_target.py`, `scripts/report_nav.py`,
  `scripts/browser_channels.py`, `scripts/edge_device.py`, `scripts/routes.py`,
  `scripts/timeouts.py`, `scripts/credential_safety.py`, `scripts/self_test.py`,
  `scripts/safe_delete.py`
- **Tests:** the matching `build/check_*.py` (e.g. `check_updater`, `check_export_engine`,
  `check_parallel_reconcile`, `check_b1_pause`, `check_b3_batch`, `check_edge_login`,
  `check_validation`, `check_reset_safety`, `check_silent_swallows`, `check_p2_freshness`,
  `check_persistence`) **and NEW `check_*.py`** you add for the above.

### HIGH-CONFLICT SHARED FILES — read + test freely, but do NOT modify without flagging
`scripts/outcome.py`, `scripts/errors.py`, `scripts/events.py`, `scripts/settings.py`,
`scripts/paths.py`, `scripts/contract.py`, `scripts/validation.py`,
`.github/workflows/checks.yml` (you WILL append your new checks here — that is expected;
Claude resolves any merge conflict at integration). If a fix genuinely needs a change to
`outcome.py`/`errors.py`/`events.py`/`settings.py`/`paths.py`, record it as a
**required-change finding** and continue with other work — do not change them speculatively.

### OFF-LIMITS (Claude owns / you cannot verify)
- **The comparison engine and everything it touches** (Claude's active lane):
  `compare_core.py`, `compare_tsn_common.py`, `compare_env.py`, `compare_*.py`,
  `consolidate_*.py`, `tsn_*.py`, `matrix*.py`, `day_matrix.py`, `baseline_matrix.py`,
  `evidence*.py`, `visual_evidence.py`, `comparison_contract.py`, `cache_envelope.py`,
  `consolidation_meta.py`, `artifact_store.py`, `owned_dir.py`, `summary_layout.py`,
  `pdf_table_lib.py`, `pdf_row_oracle.py`, `*_columns.py`, and every
  `build/check_{compare,tsn,matrix,phase,evidence,consolidate,comparison,baseline,
  source_files,visual_evidence,physical_identity,ramp,highway,intersection}*` +
  `check_day_matrix`.
- **The GUI** (needs the `#mock` you cannot run in cloud): `scripts/gui_*.py`,
  `scripts/task_coordinator.py`, `scripts/gui_endpoint.py`, `scripts/gui_matrix.py`,
  `scripts/gui_win32.py`, `scripts/ui/**`, and `check_gui_*`/`check_ui_*`/
  `check_worker_lifecycle`. The `handle-no-default-branch` (gui_api) + stale
  `gui_worker.py` docstring findings are Claude's — leave them.
- **Report/release SoT:** `scripts/report_catalog.py`, `scripts/reports.py`,
  `version.py`. **Build PowerShell:** `build/*.ps1`, `build/app.spec`.
  `scripts/site_capture.py` (comparison-adjacent, local-only).
- **`cli.py`** and any GUI/CLI driver interface: you may READ them to understand callers,
  but do not change a public engine signature the GUI/CLI depends on without flagging it
  as a required-change finding.

## 5. Acceptance criteria (the concrete deliverables)

**A. Close the OFFLINE-DOABLE open updater-integrity findings** (`docs/roadmap.md`
"Next patch" P2 + §J2), each with a red→green golden check:
1. `size-and-checksum-guards-both-skippable` — the size **and** checksum guards must not
   both be bypassable; verification is fail-closed.
2. `immediate-death-check-narrow-window` — the post-swap death check must not miss a
   swap crash that happens after the current ~1.5 s window.
3. `no-rollback-when-relaunch-launches-partial-tree` — a partial/failed relaunch must
   roll back, and the user message must never falsely claim the old version was kept.
4. `swap-log-grows-unbounded` — bound/rotate `update_helper.log`.
5. `dl-socket-timeout-may-fail-slow-large-downloads` — confirm the download
   timeout + bounded-retry is correct; add the test if missing.
   (If any of these is already resolved in code, prove it with a test and record it done.)

**B. Export/reliability coverage.** Raise offline golden-check coverage of the
resume / retry / skip / cancel / timeout / reconcile paths in `exporter.py`,
`exporter_parallel.py`, `run_report.py`, `batch_manifest.py`, `export_multi.py` —
prioritizing the error/edge branches the roadmap flags as owing work-PC verification.
Add checks; fix only **low-risk, localized** defects the new tests expose (and test the fix).

**C. Auth/session/browser coverage.** Raise offline coverage of the offline-testable logic
in `auth_nav.py`, `session.py`, `login.py`, `browser_channels.py`, `edge_device.py`,
`timeouts.py` — state transitions, channel/device fallbacks, the timeout **accessors**,
error classification. Do **not** attempt live Playwright/site behavior (mark it a finding).

**D. Silent-failure sweep (bounded).** Within YOUR modules only, find swallowed
exceptions / missing propagation that violate the "log every swallowed exception" rule;
add the log/propagation + a test. Do not extend this into other subsystems.

**E. FINDINGS.md** classifies every discovered issue as (1) in-scope-fixed,
(2) blocking-out-of-scope, (3) non-blocking follow-up, (4) suspected — with evidence,
severity, affected area, and whether it blocks the mission.

## 6. Required verification (before every milestone commit + at completion)

- `build/.venv/Scripts/python.exe build/run_checks.py -j 4 -k --skip-js` — all green
  (on Linux, use a venv from `requirements*.txt`; if a check can't run on Linux, note it
  and ensure it is not one you broke — Claude confirms on Windows).
- `python -m compileall -q scripts build version.py` — clean.
- `uvx ruff check scripts` (or the repo ruff invocation) — clean.
- New checks are `check_*.py` (NOT `check_phase*`), **offline + cross-platform** (no live
  site, no Windows-only assumption unless `sys.platform`-gated), and registered in
  `.github/workflows/checks.yml`.

## 7. Scope-expansion rules (hard)

Classify EVERY discovered issue as one of: **(1) required & in scope** — fix
autonomously; **(2) blocking but out of scope** — document, stop only if it blocks ALL
progress; **(3) non-blocking follow-up** — document, do not pursue; **(4) suspected** —
document. Only category (1) is auto-fixed. A small adjacent fix is allowed only if
directly necessary, low-risk, tested, documented, and unlikely to conflict with Claude's
comparison work. **Do not** turn incidental cleanup, speculative optimization, stylistic
preferences, broad audits, or unrelated defects into work. The comparison engine and the
GUI are never yours to "just fix."

## 8. Milestones (internal phases — not separate delegations; do not wait for approval
between them)

1. Baseline review (read §3, map the modules + existing checks, confirm which run on Linux).
2. Diagnosis + internal plan (write it into `SOL_STATUS.md`).
3. Core implementation A → B → C.
4. Edge cases + error handling + the silent-failure sweep (D).
5. Automated verification (E + the gate green).
6. Regression review (diff your own change; confirm no OFF-LIMITS file touched).
7. Cleanup + `FINAL_REPORT.md`.

Update `SOL_STATUS.md` after each meaningful milestone and during long investigations. A
status update is a **checkpoint, not a request for permission** — keep going. Make focused
milestone **commits** on your branch (each a coherent checkpoint with its verification
result), and **push** them so Claude can `git fetch` and review.

## 9. Git restrictions

- Work only on `agent/sol/reliability-hardening`. Milestone commits + pushes to THAT
  branch are expected and encouraged.
- Do NOT: modify any OFF-LIMITS file; merge/rebase Claude's branch; force-push; deploy or
  publish; discard existing changes; touch secrets (`scripts/tsmis_auth.json`, any token);
  bump `version.py`; run destructive commands.
- Claude's `comparison-perfection` branch will advance while you work; you will not see
  those changes and must not merge/rebase them. If an in-scope fix truly needs a change to
  a Claude-owned/shared file, record it and continue elsewhere.

## 10. Mid-turn steering

Steering messages may arrive from Claude (relayed by the owner) while you work. Treat each
as a **delta** from this charter: incorporate it at the next safe boundary, record any
material change in `SOL_STATUS.md`, and continue autonomously unless it says pause.
Steering does not authorize broadening your own scope.

## 11. Stop conditions (otherwise: document, choose the safest tested approach, continue)

Stop and request direction only when: no meaningful in-scope work remains; repository
evidence materially contradicts this charter; completion needs a major product/architecture
decision; destructive actions / secrets / deployment / external changes are required;
substantial changes to Claude-owned files are unavoidable; or credible verification is
impossible.

## 12. Completion condition

All of §5 A–E satisfied on `agent/sol/reliability-hardening`, the offline gate green
(best-effort on Linux; noted exceptions), ruff + compile clean, `FINDINGS.md` complete,
and `FINAL_REPORT.md` written with the exact commit range and a **Ready for review**
declaration. Then STOP and wait for Claude's review — do not open a PR or merge.
