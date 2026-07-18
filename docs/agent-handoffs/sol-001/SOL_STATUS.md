# SOL_STATUS — sol-001 (Sol owns this file)

> Sol updates this after each meaningful milestone and during long investigations. A status
> update is a checkpoint, not a request for permission — keep working. Commit + push it so
> Claude can `git fetch` and see progress.

- **State:** In progress
- **Last meaningful update:** 2026-07-17 — export/reliability milestone implemented and full gate confirmed
- **Current milestone:** 3 — core implementation, auth/session/browser coverage (C)
- **Completed milestones:** 1 baseline review; 2 diagnosis/plan; 3A updater integrity; 3B export reliability
- **Work in progress:** offline auth/session/browser state transitions, fallbacks, timeout accessors, and error classification
- **Next intended work:** add focused auth/browser fallback tests, then perform the bounded silent-failure sweep (D)
- **Current test status:** post-export full gate 132 passed / 1 known infrastructure red of 133 in 126 s; sole failure F-01 `check_source_zip_smoke`. Focused export suite, `check_silent_swallows`, compileall, diff check, and repo-wide Ruff are green.
- **Blockers / uncertainties:** exact gate green is blocked by F-01; external push of `b02ff5b` was rejected by the environment reviewer, so the checkpoint is local and product work continues
- **Latest stable checkpoint commit:** `b02ff5b` (`harden updater swap readiness`, local; push blocked)

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
