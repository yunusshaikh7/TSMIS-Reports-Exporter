# Review round 1

## 1. Verdict: `BLOCKED`

P2 has sound happy-path coverage and its fingerprint/cache changes passed targeted checks, but the
transaction boundary is not yet safe. A failed promotion can be reported as promoted, rollback
failures erase their own recovery record, startup recovery misses configured stores outside
`OUTPUT_ROOT`, an untrusted journal can delete a directory outside its store, and the workbook
validator can replace a valid prior workbook with an unreadable XLSX-shaped ZIP. These contradict
P2's protected behavior and completion criteria.

## 2. Blocking findings

### P2-B01 — A failed store promotion is reported as `promoted`

- **Severity:** blocking
- **Evidence:** `scripts/gui_worker.py`, `ExportWorker._run_specs`, lines 424-443. The return value
  from `_swap_store_dir(out_dir, stage_dir)` is discarded at line 426. Line 432 then derives
  `result.artifact` only from producer completion, so a complete export receives
  `artifact="promoted"` even when `artifact_store.promote_store` returned `False`.
  `BatchWorker.run` lines 588-597 likewise marks the environment done using completion alone.
- **Reproduction:** with the real `_run_specs`, a complete `RunResult`, and
  `_swap_store_dir = lambda ...: False`, the result was
  `completion="complete", artifact="promoted"` and auto-consolidation ran.
- **Impact:** a locked/failed swap can auto-consolidate stale last-good data, mark the batch
  environment done, and tell the frontend that the new store was promoted.
- **Exact correction expected:** capture the promotion boolean. Keep producer completion
  orthogonal, but set `artifact=previous_preserved` when promotion fails; do not auto-consolidate;
  and require an actual promoted artifact before `BatchWorker` marks an in-store environment done.
  Add a real producer-path regression test where `_swap_store_dir` returns `False` (the current
  `check_batch_outcome._run_instore` stub returns `None` while still expecting promotion, masking
  this contract).

### P2-B02 — Failed rollback/recovery deletes the journal needed for retry

- **Severity:** blocking
- **Evidence:** `scripts/artifact_store.py`, `promote_store`, lines 377-390. If
  `staged.rename(live)` fails and `backup.rename(live)` also fails, the code logs that the next
  launch will repair it but immediately deletes the journal at line 388. `_recover_one`, lines
  409-419, also deletes staging and the journal even when `backup.rename(target)` fails.
- **Reproduction:** fault injection produced `live` missing, `live.bak-*` present, and no journal;
  `recover_promotions` could not restore it. A separately seeded recovery whose first restore was
  temporarily blocked also deleted its journal, so a second unblocked launch still did not restore.
- **Impact:** the canonical store path can remain absent indefinitely, directly violating CT-4,
  the stated retry behavior, and P2's “never leave zero canonical copies” objective.
- **Exact correction expected:** remove journal/staging only after a successful restore or after a
  canonical `live` is known to exist. On restore failure retain the journal and backup (and retain
  staging unless its disposal is independently proven safe) so the next launch retries. Add tests
  for failed inline rollback and failed-first/successful-second startup recovery.

### P2-B03 — Startup recovery does not scan the configured Export Everything destination

- **Severity:** blocking
- **Evidence:** `scripts/updater.py`, `_recover_store_promotions`, lines 795-805, calls
  `recover_promotions(OUTPUT_ROOT)` only. `scripts/settings.py`, `get_batch_dest`, lines 287-301,
  explicitly permits any user-selected local path. `BatchWorker.run` creates stores under that
  configured destination (`scripts/gui_worker.py`, lines 560-564).
- **Impact:** the default store is recoverable only because it happens to sit below `OUTPUT_ROOT`;
  an interrupted promotion in a custom destination is never repaired on startup.
- **Exact correction expected:** recover the effective `settings.get_batch_dest()` tree as well as
  any separately required app-owned output tree, with resolved-path deduplication and safe failure
  isolation. Add an updater/startup test using a custom destination outside `OUTPUT_ROOT`.

### P2-B04 — Journal path traversal permits deletion outside the store

- **Severity:** blocking
- **Evidence:** `scripts/artifact_store.py`, `_recover_one`, lines 399-419, joins journal-controlled
  `target`, `backup`, and `staging` strings directly to `jdir.parent`, then passes them to
  `rename`/`_rmtree` without basename, relationship, or containment validation.
- **Reproduction:** a journal with `target="live"` and `backup="../victim"` caused
  `recover_promotions(base)` to recursively delete the sibling `victim` directory.
- **Impact:** a malformed or planted `.promote/*.json` can make startup delete or rename arbitrary
  directories reachable from the journal parent.
- **Exact correction expected:** reject records unless every path component is a single basename,
  all resolved paths remain direct children of the journal parent, and
  `backup == target + ".bak-" + token` plus the expected staging relationship hold. Invalid records
  must not touch any referenced path. Add traversal/absolute-path/wrong-token tests. The orphan
  sweep should likewise delete only names proven to be app-owned promotion residue.

### P2-B05 — Workbook validation accepts an unreadable workbook and replaces the prior artifact

- **Severity:** blocking
- **Evidence:** `scripts/artifact_store.py`, `_is_valid_xlsx`, lines 93-105, checks only that the
  file is a ZIP containing the name `xl/workbook.xml`; it does not read/parse that part or verify
  an expected sheet. This is weaker than the approved plan's “openable + expected sheet” contract.
- **Reproduction:** a ZIP containing `xl/workbook.xml` with `b"not xml"` passed validation;
  `commit_workbook` returned `status="ok"`, replaced the valid prior workbook, and the committed
  file then failed `openpyxl.load_workbook`.
- **Impact:** validate-before-commit does not actually protect the last-good workbook from a
  malformed XLSX-shaped output.
- **Exact correction expected:** validate ZIP integrity and parse/open the workbook structure,
  including the required sheet contract for each wrapped comparison. Validation failure must keep
  the prior destination. Add malformed-workbook-part, corrupt-ZIP-member, and missing-expected-sheet
  tests.

## 3. Required fixes

### P2-R01 — Directory-only staging is accepted as a valid replacement

- **Severity:** required
- **Evidence:** `scripts/artifact_store.py`, `_staging_nonempty`, lines 318-326, uses
  `any(staged.iterdir())`, although its docstring requires at least one file and the approved
  protocol requires expected files. A staging directory containing only a nested directory was
  promoted and the valid prior file set was removed.
- **Exact correction expected:** validate at least one eligible regular report file, and preferably
  the report-specific expected artifact set supplied by the caller; exclude locks, temp files,
  sidecars, and directories. Add a directory-only staging test.

### P2-R02 — Error results can expose deleted temp paths

- **Severity:** required
- **Evidence:** `scripts/artifact_store.py`, `commit_workbook`, lines 178-181, returns non-`ok`
  results untouched. `_rewrite_paths`, lines 127-139, does not rewrite `message` at all.
  `compare_core.py` lines 1881-1885 includes `path.name` in a save-error message, which is now the
  temporary filename supplied by the wrapper.
- **Reproduction:** a producer error result containing the supplied path leaked `.tmp-<token>` in
  `message`, `output_path`, and `summary_lines` after the temp file had been deleted.
- **Exact correction expected:** sanitize `message`, `output_path`, and `summary_lines` for every
  returned status before returning. Add an actual producer-save-failure regression test, not only
  an `ok`-result rewrite test.

### P2-R03 — Best-effort formulas failure returns a success result pointing to a missing/stale file

- **Severity:** required
- **Evidence:** `scripts/artifact_store.py`, `commit_workbook`, lines 192-198, commits values, logs
  a formulas failure, then returns the original producer result rewritten to the formulas final.
  The summary still claims that formulas file was produced.
- **Reproduction:** after forcing only the formulas replace to fail, the result was `status="ok"`
  with `output_path=cmp.xlsx`, that path did not exist, the values workbook did exist, and the
  summary still advertised the formulas path.
- **Exact correction expected:** when the formulas commit fails, return a truthful values-canonical
  result: point `output_path` at the committed values workbook and replace/remove the formulas
  success line with an explicit best-effort warning. If an old formulas file remains, identify it
  as not refreshed. Add assertions for result paths and summaries on the second-commit failure.

## 4. Non-blocking recommendations

### P2-A01 — Reconcile stale comments and claims after the fixes

- **Severity:** recommended
- **Evidence:** `scripts/matrix.py`, `consolidated_state` lines 887-890 and
  `consolidate_and_compare_tsn` documentation still describe newest-mtime freshness, while
  `_consolidated_stale` is fingerprint-based. `P2-claude-report.md` calls the current validator
  “openable,” which the malformed-workbook reproduction disproves.
- **Exact correction expected:** update comments/report remediation to describe the actual
  fingerprint and validation contracts; do not claim retry, openability, or expected-sheet checks
  until tests prove them.

### P2-A02 — Guard build-time fingerprints against input changes during a build

- **Severity:** recommended
- **Evidence:** `scripts/matrix.py` records `_cell_input_fingerprint(...)` only after comparison
  output is committed (for example lines 731-746), and `_consolidate_store_folder` records its
  fingerprint only after consolidation (lines 819-823). An external input change during the build
  can therefore stamp a workbook with the post-change identity even if it was built from the
  pre-change or mixed set.
- **Exact correction expected:** characterize whether GUI task exclusion is sufficient for all
  writers. If external mutation is in scope, capture fingerprints before and after the build and
  publish “fresh” metadata only when they match.

## 5. Verification performed

- Confirmed coordination status `P2 = awaiting_review`, baseline
  `e47b700261ab9642f29741b8ae4b3a790d1ffded`, and reviewed the product diff excluding
  `docs/planning/**`.
- Read the approved P2 contract, Claude's P2 report, all changed orchestration boundaries, and the
  new P2 checks.
- Passed independently:
  - `build/check_artifact_store.py`
  - `build/check_p2_freshness.py`
  - `build/check_batch_outcome.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_matrix.py`
  - `build/check_day_matrix.py`
  - `build/check_compare_blankkey.py`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Ran disposable-temp fault injections for failed promotion return propagation, failed rollback,
  failed-first recovery retry, journal traversal, directory-only staging, malformed XLSX
  validation, non-`ok` temp-path leakage, and twin formulas-finalization failure. No shared runtime
  artifacts, profiles, manifests, caches, browser state, or product files were modified.
- Did not run a frozen build, browser/GUI launch, PyInstaller, `full_smoke.py`, or destructive/shared
  artifact operation.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude should remediate P2-B01 through P2-B05 and P2-R01 through P2-R03, add the specified
regressions, rerun the relevant targeted/canary checks, and return P2 for another review round.

# Review round 2

## 1. Verdict: `BLOCKED`

The round-1 remediation resolves P2-B01, P2-B03, P2-B05's prior-replacement defect, P2-R02, and
P2-R03. The targeted suite is green. P2 is still blocked because recovery can delete the valid
backup when an invalid placeholder exists at `live`, the journal-free orphan sweep can recursively
delete unrelated user directories under the configurable destination, and a failed first-ever
promotion deletes its only completed staged copy without a recovery journal.

## 2. Blocking findings

### P2-B02 — Recovery still discards the last-good backup without proving `live` is canonical

- **Severity:** blocking
- **Affected area:** P2 recovery retry/retention contract; `scripts/artifact_store.py`,
  `_recover_one`.
- **Repository evidence:** lines 488-493 treat `target.exists()` as proof that the canonical live
  store exists, then recursively delete `backup` and `staging` and remove the journal. No directory,
  expected-file, or report-artifact validation is performed.
- **Independent reproduction:** seeded a valid `live.bak-tok` containing `old.xlsx`, a valid
  `live.staging`, an empty placeholder directory at `live`, and a trusted journal. Recovery kept
  the empty placeholder but deleted the valid backup, staging, and journal:
  `target_has_report=False, backup_survived=False, stage_survived=False,
  journal_survived=False`.
- **Why blocking:** the remediation's stated invariant is that the journal is removed only after a
  canonical copy is known to exist. Path existence is not that proof, and this path destroys the
  only last-good report set.
- **Exact correction expected:** validate `target` as a usable live store before deleting either
  recoverable copy. If `target` is absent or invalid and `backup` is valid, restore conservatively;
  if an invalid/conflicting target cannot be safely displaced, retain the journal and backup and
  log the conflict. Add empty-directory, wrong-type target, and invalid-live/valid-backup tests.

### P2-B04 — The orphan sweep still deletes unrelated directories in a user-selected destination

- **Severity:** blocking
- **Affected area:** filesystem containment and destination compatibility;
  `scripts/artifact_store.py`, `recover_promotions._sweep_orphans`; `scripts/updater.py`,
  `_recover_store_promotions`.
- **Repository evidence:** `recover_promotions` lines 542-558 recursively deletes every directory
  matching `*.staging` or `*.bak-*` whenever a same-prefix live directory exists. There is no
  journal or app-ownership proof. `updater._recover_store_promotions` lines 795-831 applies this
  recursive sweep to `settings.get_batch_dest()`, while `scripts/settings.py:get_batch_dest`
  permits any user-selected local directory. This also contradicts `gui_worker.reset_targets`
  lines 122-139, which explicitly preserves foreign content beside the store.
- **Independent reproduction:** under a disposable custom root, created user directories
  `Project/` and `Project.bak-family-photos/keep.txt`; `recover_promotions(root)` deleted the latter
  even though no promotion journal existed.
- **Why blocking:** startup can silently delete unrelated user data. Restricting the sweep from
  files to directories does not establish ownership and does not satisfy round 1's requested
  “proven app-owned residue” correction.
- **Exact correction expected:** remove the journal-free recursive deletion heuristic, or constrain
  cleanup to paths proven by a trusted journal and an app-owned store identity. If cleanup fails,
  retain the trusted journal so a later launch retries; harmless unowned residue is preferable to
  deleting a guessed backup. Add a custom-destination test with unrelated `*.bak-*` and
  `*.staging` directories that must survive.

### P2-B06 — A failed first-ever promotion deletes the only completed copy

- **Severity:** blocking
- **Affected area:** first-refresh transaction path; `scripts/artifact_store.py`,
  `promote_store`.
- **Repository evidence:** lines 394-401 special-case missing `live` by directly renaming staging.
  If that rename fails, `_rmtree(staged)` deletes the only completed artifact set and no journal is
  created.
- **Independent reproduction:** with no prior `live` and a transient injected failure on
  `live.staging -> live`, `promote_store` returned `False`, left no `live`, deleted staging, and
  wrote no journal.
- **Why blocking:** this violates P2's “never leave zero copies” objective and prevents startup
  recovery from completing an otherwise successful first export. The resulting
  `previous_preserved` artifact also claims a prior copy existed when none did.
- **Exact correction expected:** journal the first promotion too, or otherwise retain the valid
  staging copy durably when its rename fails so startup can retry it. The worker outcome must be
  truthful when no previous artifact exists. Add first-promotion rename-failure, next-launch
  recovery, and artifact-disposition tests.

## 3. Required fixes

### P2-R01 — Staging validation still accepts arbitrary regular files

- **Severity:** required
- **Affected area:** validate-before-promote contract; `scripts/artifact_store.py`,
  `_staging_has_report_file`.
- **Repository evidence:** lines 359-375 accept any regular file not matching the generic
  temp/sidecar exclusions. A text file therefore satisfies a function documented as requiring a
  report file.
- **Independent reproduction:** a stage containing only `notes.txt` was promoted over a valid live
  store, deleting `old.xlsx`.
- **Exact correction expected:** require an expected report artifact, either via a caller-supplied
  predicate/suffix or the current report contract (`.xlsx`/`.pdf` as applicable), not merely an
  arbitrary file. Add wrong-extension and sidecar-only cases.

### P2-R04 — Rejected malformed worksheet output can leave a locked temp file

- **Severity:** required
- **Affected area:** workbook validation cleanup; `scripts/artifact_store.py`, `_openable_xlsx`,
  `_commit_one`, and `commit_workbook`.
- **Repository evidence:** `_openable_xlsx` lines 100-114 can have `openpyxl.load_workbook` raise
  before assigning `wb`, leaving openpyxl's archive handle outside the function's `wb.close()`
  path. `_commit_one` then calls `_silent_unlink`, whose failure is ignored.
- **Independent reproduction:** corrupted `xl/worksheets/sheet1.xml` in an otherwise valid workbook.
  Validation correctly returned an error and preserved the prior workbook, but one
  `cmp.tmp-<token>.xlsx` remained and was immediately non-removable on Windows due to an open
  handle.
- **Exact correction expected:** ensure every validation failure closes all opened ZIP/workbook
  resources before cleanup and verify the temp is actually gone. Add malformed expected-sheet XML
  coverage asserting prior preservation and no on-disk/locked temp residue.

### Prior required finding dispositions

- **P2-R02 — Resolved.** `commit_workbook` now sanitizes `message`, `output_path`, and
  `summary_lines` for non-`ok` results using full-path and basename mappings; the independent
  temp-path reproduction no longer leaks `.tmp-*`.
- **P2-R03 — Resolved.** A formulas-finalization failure now returns the committed values path and a
  not-refreshed formulas warning.

## 4. Non-blocking recommendations

### P2-A01 — Current documentation still contains contradictory dependency/identity claims

- **Severity:** recommended
- **Affected area:** touched module/report documentation.
- **Repository evidence:** `scripts/artifact_store.py` line 22 still claims the module imports only
  stdlib plus `events`, but `_openable_xlsx` imports openpyxl. `scripts/matrix.py`,
  `consolidate_and_compare_tsn`, still says “byte-identical” around lines 923-935 despite the
  approved semantically-identical terminology. The pre-remediation sections of
  `P2-claude-report.md` still describe the validator as cheap stdlib ZIP validation and say it does
  not use a full openpyxl load.
- **Exact correction expected:** make the current-state documentation unambiguous: openpyxl is a
  lazy runtime dependency, validation behavior is described accurately, and XLSX preservation is
  semantic rather than byte identity.

### P2-A02 — The race guard can leave an old matching sidecar certifying the replaced workbook

- **Severity:** recommended
- **Affected area:** fingerprint publication; `scripts/artifact_store.py`,
  `write_consolidated_fingerprint`.
- **Repository evidence:** lines 288-293 return `False` on a before/after mismatch but leave any
  previous fingerprint sidecar in place. The consolidated workbook has already been replaced by
  the producer at this point.
- **Independent reproduction:** an old sidecar certified input identity B; a rebuild started from
  A, then inputs returned exactly to B (including size and `mtime_ns`) before publication.
  `write_consolidated_fingerprint(..., built_from=A)` returned `False`, yet
  `consolidated_fresh(...)` returned `True` because the old B sidecar remained beside the newly
  replaced workbook.
- **Exact correction expected:** on a detected race, durably invalidate/remove the old sidecar (or
  publish a non-matching sentinel) before returning. If that cannot be made durable, do not leave a
  newly replaced workbook capable of reading fresh.

### P2-A03 — Optional matrix formulas failures can remain silent

- **Severity:** recommended
- **Affected area:** `scripts/matrix.py`, `_try_formulas`.
- **Repository evidence:** lines 679-690 ignore the `ConsolidateResult` returned by
  `artifact_store.commit_workbook`; only raised exceptions are logged. Validation/finalization
  failures normally return `status="error"` rather than raise.
- **Exact correction expected:** inspect the returned status and log its message when the
  best-effort formulas copy was not refreshed.

### Prior blocking finding dispositions

- **P2-B01 — Resolved.** `ExportWorker._run_specs` captures the promotion boolean, suppresses
  auto-consolidation on failure, and `BatchWorker` requires `artifact=promoted` before marking a
  stored environment done.
- **P2-B03 — Resolved.** Startup recovery now includes the configured batch destination with
  deduplication and per-root isolation.
- **P2-B05 — Resolved as originally filed.** Malformed workbook structure and a missing expected
  `Comparison` sheet are rejected before replacing the prior artifact. P2-R04 separately covers
  cleanup of a malformed-sheet validation failure.

## 5. Verification performed

- Confirmed P2 remains `awaiting_review`, baseline/HEAD
  `e47b700261ab9642f29741b8ae4b3a790d1ffded`, and reviewed the current product diff excluding
  `docs/planning/**`.
- Re-read the approved P2 contract, Claude's report and remediation, round 1, and the changed
  artifact, worker, updater, matrix, cache, packaging, and test boundaries.
- Independently passed:
  - `build/check_artifact_store.py`
  - `build/check_batch_outcome.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_p2_freshness.py`
  - `build/check_matrix.py`
  - `build/check_day_matrix.py`
  - `build/check_consolidate_outcome.py`
  - `build/check_tsn_outcome.py`
  - `build/check_updater.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Verified `compare_core.py`, `scripts/ui/*`, auth data, and updater TLS logic remain outside the
  product diff.
- Ran disposable-temp fault injections for invalid-live/valid-backup recovery, unrelated orphan
  directories, failed first promotion, wrong-file staging, exact-identity fingerprint reversion,
  and malformed expected-sheet cleanup. Removed the diagnostic temp residue created by the
  malformed-sheet handle test after its process exited.
- Did not run a browser/GUI, live TSMIS access, PyInstaller, frozen self-test, `build.ps1`, or any
  destructive/shared-artifact build.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude should remediate P2-B02, P2-B04, P2-B06, P2-R01, and P2-R04; add the specified
regression cases; and return P2 for review round 3. P2-A01 through P2-A03 are non-blocking but should
be addressed while the affected code is already open.

# Review round 3

## 1. Verdict: BLOCKED

The round-2 remediation resolves P2-B02, P2-B06, P2-R01, P2-R04, and P2-A03, and the expanded
checks pass. P2-B04 remains open in a narrower but still destructive form: recovery now requires a
shape-valid journal, but recursively trusts such journals anywhere below a user-selected recovery
root. A planted or unrelated shape-valid journal can therefore cause deletion of unrelated
directories. One additional retry defect is required to meet the phase's idempotent-cleanup
contract.

## 2. Blocking findings

### P2-B04 — Shape validation does not establish app ownership

- **Severity:** blocking
- **Affected area:** startup promotion recovery; `scripts/artifact_store.py`,
  `_trusted_journal_names`, `_recover_one`, and `recover_promotions`.
- **Repository evidence:** `_trusted_journal_names` at lines 522-539 validates only basename
  syntax and the `<target>.bak-<token>` / `<target>.staging` relationship.
  `recover_promotions` at lines 603-626 recursively discovers every directory named `.promote`
  beneath the supplied root. `_recover_one` at lines 565-568 then deletes the journal-named backup
  and staging whenever the target merely contains a report file. The configured batch destination
  is user-selected and can contain unrelated nested projects, so journal shape alone is not an
  app-owned store identity.
- **Independent reproduction:** beneath a disposable recovery root, created
  `UnrelatedProject/.promote/tok.json` with a fully shape-valid journal naming `Project`,
  `Project.bak-tok`, and `Project.staging`. `Project` contained `r.xlsx`; the backup and staging
  contained unrelated data. `recover_promotions(root)` preserved `Project` but deleted both
  unrelated directories.
- **Exact correction expected:** constrain recovery to explicitly known app-owned promotion
  locations and report-store identities. Pass an allowlist/ownership context from callers (for
  example known source-environment and report-directory names), rather than recursively accepting
  arbitrary `.promote` trees under a user directory. Add a regression case proving a nested,
  shape-valid but unowned journal cannot alter its target, backup, staging, or journal.

### Prior blocking finding dispositions

- **P2-B01 — Resolved.** Promotion failure propagates a non-promoted artifact and blocks
  auto-consolidation and batch completion.
- **P2-B02 — Resolved.** An invalid live placeholder no longer causes a valid backup to be deleted;
  foreign-content conflicts retain all recovery material.
- **P2-B03 — Resolved.** Startup recovery includes the configured batch destination.
- **P2-B05 — Resolved.** Workbook structure and expected-sheet validation protect prior artifacts.
- **P2-B06 — Resolved.** First promotion is journaled and failed first promotion retains staging
  for next-launch recovery.

## 3. Required fixes

### P2-R05 — Cleanup failure discards the only retry record

- **Severity:** required
- **Affected area:** idempotent recovery cleanup; `scripts/artifact_store.py`, `_recover_one`.
- **Repository evidence:** when a usable target already exists, lines 565-568 call `_rmtree` for
  backup and staging and then unconditionally remove the journal. After a restore, lines 590-592
  do the same. Cleanup success is not observed. Because the round-2 fix intentionally removed the
  journal-free orphan sweep, a locked residue is never retried once its journal is deleted.
- **Independent reproduction:** seeded a usable live target, backup, staging, and valid journal;
  injected one backup cleanup failure. Recovery deleted the journal while the backup remained.
  A second normal recovery sweep left that backup permanently because no journal remained.
- **Exact correction expected:** make cleanup success observable and retain the journal whenever
  a named backup or staging directory cannot be removed. Delete the journal only after the
  canonical copy is usable and all journal-owned residue is absent. Add retry tests for cleanup
  failure after both a completed promotion and a recovery restore.

### Prior required finding dispositions

- **P2-R01 — Resolved.** Staging validation now requires `.xlsx` or `.pdf` report artifacts.
- **P2-R02 — Resolved.** Non-OK commit results redact temporary paths.
- **P2-R03 — Resolved.** Formula-finalization failure returns the committed values workbook.
- **P2-R04 — Resolved.** XLSX validation closes the file/workbook resources; malformed worksheet
  cleanup no longer leaves a locked temporary file.

## 4. Non-blocking recommendations

### P2-A02 — Sidecar invalidation failure can still produce false freshness

- **Severity:** recommended
- **Affected area:** fingerprint publication; `scripts/artifact_store.py`,
  `write_consolidated_fingerprint`.
- **Repository evidence:** on a before/after fingerprint mismatch, lines 304-316 call
  `_silent_unlink` but ignore its result and log that the stale sidecar was removed.
- **Independent reproduction:** an old sidecar certified identity B; a build started from A and
  inputs returned exactly to B. With sidecar deletion fault-injected to raise `PermissionError`,
  `write_consolidated_fingerprint(..., built_from=A)` returned `False`, the old sidecar remained,
  and `consolidated_fresh(...)` returned `True`.
- **Exact correction expected:** treat failed sidecar invalidation as a durable fail-safe problem:
  verify removal or publish a safely non-matching marker/quarantine outcome so the replaced
  workbook cannot read fresh. Log the actual result, not an unconditional removal claim.

### P2-A04 — Failure disposition uses path existence instead of usable-artifact existence

- **Severity:** recommended
- **Affected area:** worker outcome truthfulness; `scripts/gui_worker.py`,
  `ExportWorker._run_specs`.
- **Repository evidence:** line 425 sets `had_prior` from `out_dir.exists()`, while recovery's
  artifact contract uses `_is_usable_store`. An empty or foreign-only pre-existing directory can
  therefore make a failed first promotion report `previous_preserved` although no valid report
  artifact was preserved.
- **Exact correction expected:** derive `had_prior` from the same usable-store/report-artifact
  contract used by promotion recovery, and add an empty-directory/foreign-file failure case.

### Other recommendation dispositions

- **P2-A01 — Partially resolved.** Dependency and semantic-identity wording is corrected. Remove
  the duplicated P2-A02 comment at `scripts/artifact_store.py` lines 305-312 when next editing the
  function.
- **P2-A03 — Resolved.** `_try_formulas` now logs non-OK commit results.

## 5. Verification performed

- Confirmed P2 remains `awaiting_review`, with baseline and current HEAD
  `e47b700261ab9642f29741b8ae4b3a790d1ffded`, and inspected the product diff while excluding
  `docs/planning/**`.
- Re-read the approved P2 contract, current Claude report/remediation, and prior review rounds.
- Independently passed:
  - `build/check_artifact_store.py` (129 assertions)
  - `build/check_batch_outcome.py`
  - `build/check_p2_freshness.py`
  - `build/check_matrix.py`
  - `build/check_day_matrix.py`
  - `build/check_consolidate_outcome.py`
  - `build/check_tsn_outcome.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Ran disposable, isolated fault injections for a shape-valid unowned journal, failed recovery
  residue cleanup followed by a second sweep, and failed stale-sidecar removal. No shared output,
  cache, profile, manifest, configuration, build, or distribution artifact was modified.
- Did not launch a browser/GUI, access live TSMIS, run PyInstaller/frozen tests, or run a
  destructive/shared-artifact build.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude should remediate P2-B04 and P2-R05, add the specified ownership and retry
regressions, and return P2 for review round 4. P2-A02 and P2-A04 are non-blocking but should be
addressed while their affected contracts are open.

# Review round 4

## 1. Verdict: BLOCKED

The round-3 changes improve recovery, cleanup observability, and artifact truthfulness, and all
selected checks pass. The ownership boundary is still basename-based rather than location-based:
because recovery recursively scans the whole user-selected destination, an unrelated nested tree
using valid app names is accepted and modified. P2-R05 is also only partially resolved; the normal
promotion path still deletes its journal before confirming residue cleanup.

## 2. Blocking findings

### P2-B04 — Nested app-like names still bypass the ownership gate

- **Severity:** blocking
- **Affected area:** startup promotion recovery; `scripts/updater.py`,
  `_recover_store_promotions`, and `scripts/artifact_store.py`, `recover_promotions` /
  `_recover_one`.
- **Repository evidence:** `recover_promotions` recursively discovers every `.promote` directory
  beneath the supplied root (`artifact_store.py` lines 651-675). The updater predicate accepts a
  store solely when `store_root.name` is one of the six `<src>-<env>` basenames and the target is a
  known report subdirectory (`updater.py` lines 817-832); it does not require the store root to be
  a direct child of the specific configured recovery root. Thus
  `<batch_dest>/UnrelatedProject/ssor-prod/.promote/...` is treated as app-owned. Moreover,
  unreadable or shape-invalid journals are deleted at `artifact_store.py` lines 591-602 before
  ownership can be established, so unrelated malformed journals found by the recursive scan are
  also modified.
- **Independent reproduction:** under a disposable root, created
  `UnrelatedProject/ssor-prod/.promote/tok.json` with a shape-valid journal for the real report
  target `ramp_summary`; the target held `r.xlsx` and the backup/staging held unrelated data. The
  production predicate returned `True`, and `recover_promotions` deleted both backup and staging
  plus the journal.
- **Exact correction expected:** establish ownership from the complete location before reading or
  deleting any journal. Limit discovery to direct, known app store roots under each exact recovery
  root (or pass the exact root into a predicate that requires
  `store_root.parent.resolve() == recovery_root.resolve()`), then validate the report target.
  Do not touch malformed journals outside those locations. Add nested valid-name and nested
  malformed-journal regressions, plus an owned direct-child control. This does not require the
  deferred destination-ownership marker.

### Other blocking finding dispositions

- **P2-B01, P2-B02, P2-B03, P2-B05, and P2-B06 — Resolved.** Promotion outcomes, backup/staging
  recovery, configured-destination coverage, workbook validation, and first-promotion retention
  continue to pass their independent checks.

## 3. Required fixes

### P2-R05 — Normal promotion still loses its cleanup retry record

- **Severity:** required
- **Affected area:** journal lifecycle and residue cleanup; `scripts/artifact_store.py`,
  `promote_store`.
- **Repository evidence:** after a successful inline restore, lines 541-544 remove the journal
  before deleting staging. After a successful promotion, lines 552-553 remove the journal before
  deleting backup. If either directory is locked, the residue remains without a journal; the
  journal-free sweep was intentionally removed, so startup recovery cannot retry it.
  `_recover_one` now has the correct observable cleanup behavior, but `promote_store` does not use
  it.
- **Independent reproduction:** promoted a valid staging store while fault-injecting backup
  deletion failure. `promote_store` returned `True`, left `live.bak-<token>`, and removed the
  journal. A subsequent recovery sweep left the backup permanently.
- **Exact correction expected:** apply the same cleanup-before-journal rule to every
  `promote_store` completion/restore branch: retain the journal until all named residue is
  confirmed absent, allowing next-launch recovery to retry. Add tests for a locked backup after a
  successful promotion and locked staging after a successful inline restore.

### Other required finding dispositions

- **P2-R01 through P2-R04 — Resolved.** Report-file staging validation, temporary-path redaction,
  values-canonical result truthfulness, and malformed-workbook handle cleanup remain green.

## 4. Non-blocking recommendations

### P2-A02 — The final fingerprint invalidation failure still permits false freshness

- **Severity:** recommended
- **Affected area:** fingerprint publication; `scripts/artifact_store.py`,
  `write_consolidated_fingerprint`.
- **Repository evidence:** lines 321-340 remove the stale sidecar or overwrite it with a sentinel,
  but if both operations fail the function only logs that the workbook may read fresh and returns
  `False`. The pre-existing matching sidecar remains authoritative.
- **Independent reproduction:** with both `_silent_unlink` and `_write_fp_sentinel`
  fault-injected to fail, the race path returned `False` while `consolidated_fresh` returned
  `True`.
- **Exact correction expected:** continue the fail-safe ladder when both sidecar operations fail,
  for example by quarantining the newly replaced workbook or otherwise making the canonical
  workbook ineligible for reuse. Add the dual-failure case.

### Other recommendation dispositions

- **P2-A01, P2-A03, and P2-A04 — Resolved.** Documentation cleanup, optional-formulas failure
  logging, and usable-store-based `had_prior` behavior are present and covered.

## 5. Verification performed

- Confirmed P2 remains `awaiting_review`; baseline and current HEAD are
  `e47b700261ab9642f29741b8ae4b3a790d1ffded`. Inspected the product diff excluding
  `docs/planning/**`.
- Re-read the approved P2 contract, Claude's current report including round-3 remediation, and all
  prior P2 review rounds.
- Independently passed:
  - `build/check_artifact_store.py` (143 assertions)
  - `build/check_batch_outcome.py`
  - `build/check_p2_freshness.py`
  - `build/check_updater.py`
  - `build/check_matrix.py`
  - `build/check_day_matrix.py`
  - `build/check_consolidate_outcome.py`
  - `build/check_tsn_outcome.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Ran disposable fault injections for a nested valid-name unowned journal, failed backup cleanup
  on the successful promotion path followed by recovery, and simultaneous sidecar
  removal/sentinel failure. No shared runtime state or build artifact was modified.
- Verified `compare_core.py`, frontend files, auth handling, and updater TLS behavior remain outside
  the P2 product diff. Did not launch a GUI/browser, access live TSMIS, run PyInstaller/frozen
  tests, or run a destructive/shared-artifact build.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude should close P2-B04 using an exact-root ownership boundary and finish P2-R05 across
the normal promotion path, add the specified regressions, and return P2 for review round 5.
P2-A02 remains non-blocking but is not yet fail-safe under its dual-failure case.

# Review round 5

## 1. Verdict: BLOCKED

The round-4 corrections are implemented and independently close P2-B04, P2-R05, and P2-A02 as
previously filed. One transaction-generation defect remains: the new cleanup-retry behavior can
leave an older journal for a target, but a later promotion is allowed to create a second journal
for that same target. Recovery processes the journals independently in filesystem order, allowing
the older journal to restore an older generation and delete both the true last-good backup and the
newer staging copy.

## 2. Blocking findings

### P2-B07 — Multiple journals for one target can roll back past last-good and delete newer copies

- **Severity:** blocking
- **Affected area:** journal generation/serialization; `scripts/artifact_store.py`,
  `promote_store`, `recover_promotions`, and `_recover_one`.
- **Repository evidence:** `promote_store` at lines 504-591 always creates a new token/journal and
  never checks for an unresolved journal naming the same target. Such a journal is now a normal
  state when `_finalize_journal` retains it after locked backup cleanup. `recover_promotions` at
  lines 677-707 then iterates all journal files without grouping or ordering them by target.
  `_recover_one` at lines 643-666 treats each journal independently, restores its own backup before
  staging, and deletes the shared deterministic `<target>.staging` path. Therefore two journal
  generations for the same target are not composable.
- **Independent reproduction:** seeded an owned store in this reachable sequence:
  1. V1 backup plus older journal remained after a successful V1→V2 promotion whose cleanup was
     locked;
  2. a later V2→V3 promotion had its own journal, V2 backup, and V3 staging, with live absent as if
     interrupted after `live→backup`;
  3. recovery encountered the older journal first.
  Recovery restored V1, deleted the shared V3 staging, then processed the newer journal as stale
  residue and deleted V2. Final state contained only V1; V2 (the actual last-good) and V3 were both
  gone, and both journals were removed.
- **Exact correction expected:** enforce a single coherent transaction generation per target.
  Before creating a new journal, safely resolve or refuse an existing same-target journal; if its
  cleanup residue remains locked, do not begin a promotion that can overlap it. Alternatively,
  journal generation-specific staging plus deterministic generation-aware recovery must guarantee
  that an older journal can never restore over or delete a newer generation. Add a seeded
  two-journal same-target regression in both journal encounter orders asserting that recovery
  preserves at least the newest proven last-good V2 and never lets the older journal consume V3 or
  V2.

### Prior blocking finding dispositions

- **P2-B04 — Resolved.** Recovery now proves exact-root/direct-child location ownership before
  reading or deleting journals; nested valid-name and malformed journals remain untouched.
- **P2-B01, P2-B02, P2-B03, P2-B05, and P2-B06 — Resolved.** Their existing checks remain green.

## 3. Required fixes

No additional standalone required finding was identified. P2-B07 itself must be corrected before
approval.

### Prior required finding dispositions

- **P2-R05 — Resolved for a single transaction generation.** `_finalize_journal` retains journals
  after failed residue cleanup in both promotion and recovery paths. P2-B07 covers the newly exposed
  interaction between a retained journal and a later promotion.
- **P2-R01 through P2-R04 — Resolved.**

## 4. Non-blocking recommendations

No new recommendation.

### Prior recommendation dispositions

- **P2-A02 — Resolved.** If sidecar removal and sentinel publication both fail, the race-suspect
  workbook is quarantined and cannot read fresh.
- **P2-A01, P2-A03, and P2-A04 — Resolved.**

## 5. Verification performed

- Confirmed P2 remains `awaiting_review`; baseline and current HEAD are
  `e47b700261ab9642f29741b8ae4b3a790d1ffded`. Inspected the complete product diff excluding
  `docs/planning/**`.
- Re-read the approved P2 contract, Claude's report through round-4 remediation, and all prior P2
  reviews.
- Independently passed:
  - `build/check_artifact_store.py` (156 assertions)
  - `build/check_batch_outcome.py`
  - `build/check_p2_freshness.py`
  - `build/check_updater.py`
  - `build/check_matrix.py`
  - `build/check_day_matrix.py`
  - `build/check_consolidate_outcome.py`
  - `build/check_tsn_outcome.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Independently reproduced the two-journal generation collision entirely in a disposable directory;
  recovery ended at V1 and deleted V2 and V3.
- Verified `compare_core.py`, frontend files, auth handling, and updater TLS behavior remain outside
  the P2 product diff. Did not launch a GUI/browser, access live TSMIS, run PyInstaller/frozen
  tests, or run a destructive/shared-artifact build.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude should serialize or generation-isolate same-target promotions, add both journal-order
regressions, and return P2 for review round 6.

# Review round 6

## 1. Verdict: BLOCKED

The round-5 change passes the nominal two-journal tests, but P2-B07 remains open because journal
generation is derived directly from wall-clock time. `time.time_ns()` is not a monotonic persisted
sequence: the system clock can move backward between two promotions, especially when an older
cleanup journal survives across application restarts. In that case newest-`seq`-first recovery
again processes the older transaction first and destroys the actual last-good generation.

## 2. Blocking findings

### P2-B07 — Wall-clock `seq` does not guarantee transaction-generation order

- **Severity:** blocking
- **Affected area:** same-target promotion serialization and recovery ordering;
  `scripts/artifact_store.py`, `promote_store`, `_journal_seq`, and `recover_promotions`.
- **Repository evidence:** `promote_store` lines 527-534 records `"seq": time.time_ns()` and states
  it is sufficiently monotonic. `_journal_seq` lines 681-690 returns that value, and
  `recover_promotions` lines 728-731 treats descending `seq` as authoritative transaction order.
  No code compares a new value with retained same-target journals, prevents a second transaction
  while one remains unresolved, or otherwise establishes a durable monotonic generation.
- **Independent reproduction:** seeded the same reachable state as round 5, but modeled a system
  clock rollback: the older V1 cleanup journal had `seq=200`; the later interrupted V2→V3 journal
  had `seq=100`. Recovery treated V1 as newer, restored V1, deleted the V3 staging and V2 backup,
  and removed both journals. Final live contained V1 only.
- **Exact correction expected:** make generation ordering independent of wall-clock direction.
  Prefer refusing/finishing an existing same-target transaction before creating another. If
  multiple generations remain supported, assign the new generation strictly greater than every
  valid existing same-target journal (under the existing single-writer boundary), or use another
  durable ordering contract that cannot regress across restarts or clock corrections. Add the
  inverted-clock regression in both filename orders, alongside the existing normal-order cases.

### Prior blocking finding dispositions

- **P2-B04 — Resolved.** Exact-root ownership remains correctly enforced.
- **P2-B01, P2-B02, P2-B03, P2-B05, and P2-B06 — Resolved.**

## 3. Required fixes

No additional standalone required finding.

### Prior required finding dispositions

- **P2-R01 through P2-R05 — Resolved**, subject to P2-B07's same-target generation interaction.

## 4. Non-blocking recommendations

No new recommendation.

### Prior recommendation dispositions

- **P2-A01 through P2-A04 — Resolved.**

## 5. Verification performed

- Confirmed P2 remains `awaiting_review`; baseline and current HEAD are
  `e47b700261ab9642f29741b8ae4b3a790d1ffded`. Inspected the product diff excluding
  `docs/planning/**`.
- Re-read the approved P2 contract, Claude's report through round-5 remediation, and prior reviews.
- Independently passed:
  - `build/check_artifact_store.py` (164 assertions)
  - `build/check_batch_outcome.py`
  - `build/check_p2_freshness.py`
  - `build/check_updater.py`
  - `build/check_matrix.py`
  - `build/check_day_matrix.py`
  - `build/check_consolidate_outcome.py`
  - `build/check_tsn_outcome.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Ran a disposable inverted-clock same-target recovery reproduction; recovery ended at V1 and
  deleted V2 and V3.
- Verified `compare_core.py`, frontend files, auth handling, and updater TLS behavior remain outside
  the P2 product diff. Did not launch a GUI/browser, access live TSMIS, run PyInstaller/frozen
  tests, or run a destructive/shared-artifact build.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude should replace wall-clock ordering with a durable non-regressing same-target
transaction contract, add the inverted-clock regressions, and return P2 for review round 7.

# Review round 7

## 1. Verdict: PASS

The round-6 remediation closes P2-B07. Same-target generations are now derived from durable
on-disk journal state (`max(existing valid same-target gen) + 1`), not wall-clock time, and recovery
processes the highest generation first. The implementation satisfies the approved P2 transaction,
freshness, atomic-write, outcome, packaging-reachability, and protected-behavior boundaries.

## 2. Blocking findings

None.

### Prior blocking finding dispositions

- **P2-B01 through P2-B07 — Resolved.** In particular, P2-B07 now uses `_next_generation` to
  produce strictly increasing same-target generations across retained journals and restarts; both
  journal filename orders recover the newest proven last-good generation.

## 3. Required fixes

None.

### Prior required finding dispositions

- **P2-R01 through P2-R05 — Resolved.**

## 4. Non-blocking recommendations

None.

### Prior recommendation dispositions

- **P2-A01 through P2-A04 — Resolved.**
- The planned work-PC Defender/lock recovery exercise and real-upgrade one-time rebuild remain
  external acceptance evidence, explicitly outside the offline P2 definition of done.

## 5. Verification performed

- Confirmed P2 remains `awaiting_review`; baseline and current HEAD are
  `e47b700261ab9642f29741b8ae4b3a790d1ffded`. Reviewed the product diff excluding
  `docs/planning/**`.
- Re-read the approved P2 contract, Claude's report through round-6 remediation, and all prior P2
  reviews.
- Inspected `_next_generation`, `_journal_gen`, `promote_store`, `recover_promotions`, the exact-root
  ownership predicate, cleanup-before-journal behavior, fingerprint invalidation ladder, worker
  artifact mapping, CI wiring, and `app.spec` reachability.
- Independently passed:
  - `build/check_artifact_store.py` (169 assertions)
  - `build/check_batch_outcome.py`
  - `build/check_p2_freshness.py`
  - `build/check_updater.py`
  - `build/check_matrix.py`
  - `build/check_day_matrix.py`
  - `build/check_consolidate_outcome.py`
  - `build/check_tsn_outcome.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Verified no wall-clock `seq` remains in the transaction implementation, no `REVERT-PROOF`
  marker remains, and `compare_core.py`, frontend files, auth handling, and updater TLS behavior
  remain outside the P2 product diff.
- Did not launch a GUI/browser, access live TSMIS, run PyInstaller/frozen tests, or run a
  destructive/shared-artifact build.

## 6. Whether Claude may proceed toward phase approval

**Yes.** Claude may mark P2 approved and proceed toward the phase commit under the coordination
rules.
