# SOL_STATUS — sol-001 (Sol owns this file)

> Sol updates this after each meaningful milestone and during long investigations. A status
> update is a checkpoint, not a request for permission — keep working. Commit + push it so
> Claude can `git fetch` and see progress.

- **State:** In progress
- **Last meaningful update:** 2026-07-17 — auth/session/browser coverage and bounded silent-failure sweep implemented
- **Current milestone:** 5 — automated verification and findings ledger (E)
- **Completed milestones:** 1 baseline review; 2 diagnosis/plan; 3A updater integrity; 3B export reliability; 3C auth/session/browser; 4 bounded silent-failure sweep
- **Work in progress:** authoritative full gate, regression/ownership review, source-ZIP independent verification, and final report
- **Next intended work:** run the full gate + compileall + Ruff, commit the auth milestone, then complete the final audit/report
- **Current test status:** auth milestone full gate 133 passed / 1 known infrastructure red of 134 in 219 s; sole failure F-01 `check_source_zip_smoke`. New auth check, existing focused checks, compileall, repo-wide Ruff, and `git diff --check` are green.
- **Blockers / uncertainties:** exact in-worktree gate green is blocked by F-01; external push of `b02ff5b` was rejected by the environment reviewer, so both completed checkpoints remain local and product work continues
- **Latest stable checkpoint commit:** `d1b3502` (`harden export retry accounting`, local; push blocked)

## Updater milestone evidence

- Replaced the fixed two-second death poll with a one-use readiness nonce. The staged helper now
  publishes readiness only after it opens the original process handle and enters the PID-wait
  boundary; the original app remains open on delayed death, malformed readiness, or timeout.
- Preserved old-to-new update compatibility: `run_swap_mode` still accepts the legacy argument
  shape when an older installed app launches the newer staged executable.
- Preserved new-to-old **Revert** compatibility too: nonce-capable helpers publish `starting:`
  before their normal log line and must reach nonce-backed `ready:`; a pre-protocol helper can use
  only the newly appended, PID-specific historical wait line. This compatibility case was caught
  red during diff review and is now golden-checked.
- A failed phase-2 rollback now suppresses relaunch of the mixed install tree. The existing dialog
  continues to distinguish a clean restore from a partial restore and directs reinstall when partial.
- Confirmed the other chartered updater findings were already implemented and remain golden-checked:
  mandatory checksum verification, bounded download retry/socket timeout, and bounded log rotation.
- Red→green: the strengthened updater check produced seven expected failures before implementation
  (late death/readiness wiring/marker cleanup/partial-tree relaunch), then one Revert-compatibility
  failure during regression review; all eight are now green.

## Export/reliability milestone evidence

- Fixed combined-edition slow retry so cancel, in-route cancellation, or recovery stop cannot erase
  the removed first-pass failures. Every unprocessed route is restored once in both edition results,
  and both run reports remain identical. The new check failed three assertions before the fix.
- Hardened `batch_manifest.load()` to reject non-object or incomplete environment steps before
  `pending()`/`mark_done()` can crash. Two malformed-step checks were red before the fix.
- Added auto-discovered `check_export_lifecycle.py`: proves the existing sequential retry's
  success/resume/stop/cancel accounting, run-report status projection/CSV ordering, and
  `export_multi.REPORTS` derivation from the registry. Existing parallel crash/cancel reconciliation,
  timeout, empty, skip, pause, and saved-file resume guards remain green.
- One off-limits `check_pdf_role_provenance` process exited once with no output under `-j 4`; its
  immediate isolated run passed every assertion and the confirming full run passed it. Classified
  suspected/non-blocking as F-10 rather than changing comparison-owned code.

## Auth/session/browser + silent-failure milestone evidence

- Added auto-discovered `check_auth_reliability.py`, using fakes only. It covers saved-session vs
  device-mode selection, browser ordering/cache/re-resolution, optional-permission fallbacks,
  console Chrome-to-Chromium and Edge recapture fallback sequencing, dynamic timeout accessors,
  site target fallback, navigation cancellation, unreachable-site classification, and preview
  request polling. No browser process, auth file, network call, or live TSMIS page is used.
- Red-to-green logging contracts closed meaningful fallback gaps in `browser_channels`,
  `edge_device`, `login`, `session`, `site_target`, `timeouts`, and `report_nav`. Each preserved
  existing behavior while adding exception type + first-line reason; multiline reasons cannot
  split one decision across log lines.
- The bounded AST sweep reports 0 new silent swallows. Two stale exemptions for handlers fixed in
  this lane were removed; three unrelated pre-existing stale entries were deliberately preserved
  to avoid off-lane baseline cleanup. The scanner reports 117 active grandfathered handlers and
  accepts no new waiver.
- Repository evidence supersedes the charter's request to enumerate new checks in CI YAML:
  `checks.yml` deliberately runs the globbing `run_checks.py`, and `check_ci_manifest.py` guards
  that auto-discovery contract. No workflow edit is needed; recorded as F-16.

## Internal plan

1. **Updater (A):** retain/prove checksum fail-closed, download socket timeout + bounded retry,
   and helper-log rotation; replace the arbitrary post-launch death window with an explicit
   helper-ready handshake; refuse to relaunch any tree after incomplete rollback; add adversarial
   updater checks for missing size/checksum, late helper start/death, partial rollback, log bounds,
   and retry exhaustion.
2. **Export reliability (B):** add an offline lifecycle check spanning sequential and combined
   resume/retry/skip/cancel/timeout/reconcile; specifically verify retry bookkeeping is total and
   exactly-once, run-report failures propagate only as documented, manifests fail closed, and
   parallel reconciliation remains lock-tolerant. Fix only localized defects demonstrated red.
3. **Auth/session/browser (C):** add offline state-machine checks for cancel/error transitions,
   saved-session vs device fallback, browser candidate/fallback order, dynamic timeout accessors,
   and error classification; no live Playwright/site calls.
4. **Silent failures (D):** bounded AST/handler sweep over the owned modules; for each swallowed
   exception either prove teardown-only/best-effort semantics or add type + first-line logging and
   a focused check.
5. **Finish (E):** keep FINDINGS current, run focused checks continuously, run full gate +
   compileall + ruff at each checkpoint, independently exercise the source-ZIP gate around F-01,
   review the diff/ownership boundary, write FINAL_REPORT with exact commits, then push.
