# SOL_STATUS — sol-001 (Sol owns this file)

> Sol updates this after each meaningful milestone and during long investigations. A status
> update is a checkpoint, not a request for permission — keep working. Commit + push it so
> Claude can `git fetch` and see progress.

- **State:** In progress
- **Last meaningful update:** 2026-07-17 — updater-integrity milestone implemented and focused checks green
- **Current milestone:** 3 — core implementation, export/reliability coverage (B)
- **Completed milestones:** 1 baseline review; 2 diagnosis/plan; 3A updater integrity
- **Work in progress:** export lifecycle/retry/reconcile branch coverage and localized defect confirmation
- **Next intended work:** lock the combined-edition retry accounting under cancel/unrecoverable exits, then cover remaining sequential/parallel lifecycle edges
- **Current test status:** post-change full gate 131 passed / 1 known infrastructure red in 130 s; the sole failure is F-01 `check_source_zip_smoke`. `check_updater.py`, `check_silent_swallows.py`, repo compileall, diff check, and repo-wide Ruff are green.
- **Blockers / uncertainties:** exact 132/132 gate is blocked by an out-of-scope worktree-incompatible packaging check (F-01); product work is not blocked
- **Latest stable checkpoint commit:** pending updater milestone commit

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
