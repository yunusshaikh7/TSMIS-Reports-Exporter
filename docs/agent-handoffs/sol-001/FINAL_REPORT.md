# FINAL REPORT — sol-001

- **Declaration:** Ready for review
- **Starting commit:** `2543a02`
- **Final implementation commit:** `42c25a5`
- **Reviewed implementation range:** `2543a02..42c25a5`
- **Commits:** `b02ff5b`, `d1b3502`, `42c25a5`
- **Closeout note:** this report and the final status update are the only planned changes after
  the reviewed implementation range; the integrator can review the complete branch as
  `2543a02..HEAD` after the closeout commit.

## Executive summary

The offline-doable reliability mission is complete. The updater now uses an explicit helper
readiness protocol and will not relaunch a partially restored install. Combined-edition retries
retain total route accounting across stop/cancel paths, and malformed batch manifests fail closed.
New offline checks cover export lifecycle and auth/session/browser state transitions. The bounded
silent-failure sweep made meaningful compatibility fallbacks diagnosable without changing their
product behavior.

The final authoritative worktree gate passed 133 of 134 checks. The only failure is the confirmed
linked-worktree infrastructure defect F-01 in `check_source_zip_smoke`; an exact committed source
archive was built separately and passed that check's supplied-archive clean-extract mode.

## Work completed

1. **Updater integrity**

   - Added a one-use `starting:<nonce>` / `ready:<nonce>` helper protocol. Readiness is published
     only after the helper opens the original process handle and enters the PID-wait boundary.
   - Kept old/new Revert compatibility through a cursor-bounded legacy log signal, while a
     nonce-capable helper may not silently downgrade to that weaker signal.
   - Suppressed relaunch after incomplete rollback so a mixed installation tree is never started.
   - Re-proved mandatory checksum, bounded retry/socket timeout, and bounded swap-log rotation.

2. **Export reliability**

   - Fixed combined-edition slow retry so `RunCancelled`, recovery stop, and unprocessed failures
     are reconciled exactly once into both editions and both run reports.
   - Made batch-manifest loading reject non-object or incomplete environment steps before resume.
   - Added `check_export_lifecycle.py` for sequential retry success/resume/stop/cancel accounting,
     run-report CSV projection, and registry-derived multi-report dispatch.

3. **Auth/session/browser reliability**

   - Added `check_auth_reliability.py`, entirely fake/offline, covering saved session vs device
     mode, browser candidate order/re-resolution/cache, persistent-profile permission fallback,
     console browser/profile fallback, dynamic timeouts, target fallback, cancellation, and error
     classification.
   - Added exception type + first-line logging to meaningful fallback decisions in
     `browser_channels`, `edge_device`, `login`, `session`, `site_target`, `timeouts`, and
     `report_nav`; all original fallbacks and public signatures are preserved.

4. **Silent-failure sweep and findings**

   - `check_silent_swallows` reports 0 new silent swallows. Two owned stale baseline exemptions
     were removed; three unrelated pre-existing stale entries were left untouched.
   - Every discovered issue is classified in `FINDINGS.md` as fixed, blocking/out-of-scope,
     follow-up, or suspected.

## Acceptance-criteria checklist (CHARTER §5)

- [x] A. Updater-integrity findings closed with red-to-green checks.
- [x] B. Export/reliability coverage raised across retry/resume/stop/cancel/reconcile and manifest paths.
- [x] C. Auth/session/browser offline coverage raised without a live browser or site.
- [x] D. Bounded silent-failure sweep completed in owned modules with tested fixes.
- [x] E. `FINDINGS.md` complete and classified.

## Files changed and why

- `scripts/updater.py`, `build/check_updater.py`: readiness/rollback hardening and adversarial checks.
- `scripts/exporter.py`, `scripts/batch_manifest.py`, `build/check_coalesce_editions.py`,
  `build/check_b3_batch.py`, `build/check_export_lifecycle.py`: total retry accounting, manifest
  validation, and lifecycle coverage.
- `scripts/browser_channels.py`, `scripts/edge_device.py`, `scripts/login.py`,
  `scripts/report_nav.py`, `scripts/session.py`, `scripts/site_target.py`, `scripts/timeouts.py`,
  `build/check_auth_reliability.py`: offline auth/browser contracts and diagnostic fallbacks.
- `build/silent_swallows_baseline.txt`: removed only the two stale owned entries fixed here.
- `docs/agent-handoffs/sol-001/{SOL_STATUS,FINDINGS,FINAL_REPORT}.md`: mission evidence and handoff.

No comparison, GUI, report-catalog, release-version, secret, generated-output, or build-artifact
file was changed. The pre-existing untracked root `AGENTS.md` was preserved and excluded.

## Important implementation decisions

- Helper readiness is based on the original PID handle, not an arbitrary elapsed-time death poll.
- Legacy Revert proof is accepted only when no protocol marker appears after helper launch and only
  from the newly appended, PID-specific log region.
- Combined retry reconciliation uses the shared tally path so both editions receive identical,
  exactly-once terminal route state.
- Auth changes are diagnostic-only: retries, channel priority, session choice, and error classes are
  unchanged. Multiline exception messages are reduced to one log line.
- New checks remain auto-registered through `run_checks.py`; CI intentionally does not enumerate
  individual checks in YAML (F-16).

## Automated tests and exact results

- Final full gate: **133 passed, 1 failed of 134 (130 s)**.
  The sole red was F-01 `check_source_zip_smoke`; all product checks, both new checks, updater,
  export, auth, UI, and comparison-owned regression checks passed.
- Exact committed source ZIP (`git archive HEAD`, release prefix), supplied-archive mode:
  **ALL SOURCE-ZIP CONSOLE-FLOW CHECKS PASSED**. Required membership, clean-extract imports,
  menu selection, report dispatch, consolidation entries, and comparison entries were green.
- `python -m compileall -q scripts build version.py`: clean.
- Repo Ruff invocation: **All checks passed**.
- `git diff --check`: clean.
- Focused `check_auth_reliability`, `check_edge_login`, `check_engine_leaves`,
  `check_silent_swallows`, export lifecycle/coalescing/batch checks, and updater check: green.

Milestone full-gate history:

- Updater: 131 passed / 1 F-01 of 132.
- Export: 132 passed / 1 F-01 of 133.
- Auth implementation: 133 passed / 1 F-01 of 134 (219 s).
- Final closeout worktree: 133 passed / 1 F-01 of 134 (130 s).

## Manual and artifact verification

- Reviewed the complete `2543a02..42c25a5` name/status and behavior diff against ownership rules.
- Built a real ZIP from committed `HEAD`, extracted it into a clean temporary directory, and ran
  the source-archive console smoke using only extracted files. The temporary archive was removed.
- No live TSMIS, OAuth/SAML, browser process, auth credential, or external deployment was used.

## Deviations from the charter

- The exact default full gate cannot be green in this linked worktree because the out-of-scope
  source-ZIP candidate builder assumes `.git` is a directory. The supplied-archive mode proves the
  committed artifact itself is green; F-01 records the required shared-infrastructure fix.
- No CI YAML line was appended because repository policy deliberately auto-discovers every
  `check_*.py`; `check_ci_manifest.py` guards that design. F-16 records the charter/repository
  discrepancy.
- Milestone commits are local. The environment reviewer rejected the attempted push of `b02ff5b`;
  no retry or workaround was attempted. The branch therefore requires local review or an
  authorized push by the integrator.

## Known limitations and remaining risks

- Live TSMIS DOM/auth/export behavior and the locked-down Caltrans work-PC environment remain
  unverifiable here.
- Managed Edge policies, Defender/file locks, corporate proxy/TLS inspection, unsigned frozen-exe
  swap/relaunch, and real Revert timing require work-PC acceptance.
- F-01 still prevents the default candidate-archive check from running in a linked worktree.
- F-10 is a one-time, non-reproduced off-limits check-process anomaly; it passed the confirming and
  final full gates.

## Out-of-scope findings

See `FINDINGS.md`. Headline items are F-01 (linked-worktree source-ZIP candidate construction),
F-10 (non-reproduced PDF-role check anomaly), and F-16 (CI auto-discovery contradicts the charter's
obsolete YAML-enumeration direction). All runtime findings F-02 through F-09 and F-11 through F-15
are fixed or proved already fixed.

## Recommended review focus

- `b02ff5b`: nonce/legacy readiness negotiation, stale-log exclusion, and partial rollback relaunch.
- `d1b3502`: combined retry reconciliation under cancellation/recovery stop and manifest validation.
- `42c25a5`: fake-only auth coverage and assurance that logging additions do not alter fallback order.
- Confirm the integrator's own full gate reproduces all product checks green; fix F-01 separately in
  shared build infrastructure rather than weakening or bypassing the archive check.
