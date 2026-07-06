# P0 Codex review

## Review round 1

### 1. Verdict: `BLOCKED`

P0 is largely within its approved file and behavior scope, and the two characterized
report fixes pass their focused checks. It is not ready for approval because CT-10,
the phase's central lifecycle safety net, does not test the approved per-worker
contract and misses a reproducible late-terminal transition that clears an already
running successor task.

### 2. Blocking findings

#### P0-B01 — CT-10 is not per-worker and its duplicate-late case misses successor-task corruption

- **Evidence:** The approved P0 contract requires per-worker or per-worker-family
  success, cancellation, expected-error, unexpected-error, and duplicate/late
  lifecycle coverage with gate-release and queue-advance assertions. However,
  `build/check_worker_lifecycle.py:test_success_release` drives only
  `export_done`; `test_cancel_release` and `test_error_release` inject generic
  handler messages; no `gui_worker.py` worker `run()` path is exercised.
  `test_duplicate_late` sends `export_done` while the gate is still idle and only
  claims the next task afterward (`build/check_worker_lifecycle.py:83-91`).
- **Concrete defect:** `GuiApi._end_task` unconditionally clears `_task`,
  `_current_job`, and related state (`scripts/gui_api.py:566-583`). In an
  independent queue-path diagnostic, the first terminal event started queued
  matrix job `successor` (`_task == "matrix"` and `_current_job == successor`);
  a duplicate-late `export_done` then cleared both to `None`. Thus the new green
  check does not protect the exact late-event/queue interaction it claims to
  characterize.
- **Exact correction expected:** Replace the message-only sample with a terminal
  contract table covering every task-owning worker class or justified worker
  family, including success, cancel, expected failure, unexpected failure, and
  exactly-one terminal delivery. Add a duplicate-late case in which a queued or
  newly claimed successor is already active, and assert that its gate/current-job
  state remains intact. Do not weaken the assertion to the current idle-only case.
  Because making that case green appears to require lifecycle identity/idempotency
  behavior beyond P0's two approved behavior deltas, Claude must either obtain an
  approved isolated P0 correction or record a coordination-approved sequencing
  change; it may not claim CT-10 complete as written.

### 3. Required fixes

#### P0-R01 — The import-direction guard has built-in false negatives

- **Evidence:** `build/check_import_direction.py:_module_level_deps` accepts only
  imports whose AST `col_offset == 0` (`:35-49`), so imports executed at module
  scope inside `try`, `if`, or similar blocks are omitted. It then removes the
  current module from its dependency set (`return deps - {path.stem}`, `:51`),
  making the later self-loop assertion at `:96-99` impossible to fail.
  Independent in-memory probes returned an empty set for a direct `import alpha`,
  a module-scope `try: import beta`, and a module-scope conditional import.
  A corrected analysis of current HEAD still found 53 modules, zero self-imports,
  and zero cycles, so this is a defective future tripwire rather than a current
  repository cycle.
- **Exact correction expected:** Traverse module-executed statement bodies while
  excluding function/class bodies, retain self-edges, and add source-string
  self-tests proving detection of a direct self-import plus a cycle expressed
  through module-scope `try`/conditional imports.

#### P0-R02 — Canonical GUI-bridge documentation still contradicts the P0 code and its line anchors remain stale

- **Evidence:** `docs/internals/gui-bridge.md:74`, `:411`, and `:426` still state
  that `GuiApi._handle` has no default and silently drops unknown kinds, while
  `scripts/gui_api.py:558-564` now logs them. The supposedly corrected worker
  headings are also already wrong: the document says `ExportWorker` is
  `222-459`, while the class is `scripts/gui_worker.py:223-460`; the same
  one-line error affects the other edited headings. `EnvScanWorker` remains
  documented as `815-1068` at `docs/internals/gui-bridge.md:288`, but is actually
  `scripts/gui_worker.py:904-1162`. The Claude report nevertheless claims all
  nine class-header ranges and the `run()` anchor were corrected. In addition,
  the blocking `check_no_misspelling.py` workflow step remains absent from the
  CI guard list in `docs/build-and-release.md`.
- **Exact correction expected:** Remove all three semantic “silent drop”
  statements, correct every P0-claimed class/run anchor against the final edited
  file (including `EnvScanWorker`), and include the product-name guard in the
  documented blocking CI inventory. Deep volatile references may remain
  explicitly deferred to P11, but P0 must not claim corrected anchors that are
  inaccurate at its own boundary.

#### P0-R03 — The required performance baselines were explicitly deferred

- **Evidence:** The approved P0 completion criteria require cold-start and
  matrix-snapshot baselines with environment and repeats
  (`05-claude-final-plan.md:389-391`). The phase report instead defers both to a
  later hot-path phase (`P0-claude-report.md:139-140`) and records no command,
  environment, representative data shape, cold/warm distinction, repeat count,
  percentile, or result. The concrete repository targets are GUI startup through
  `scripts/gui_api.py:GuiApi.get_initial_state` and matrix generation through
  `GuiApi._matrix_snapshot` / `GuiApi.matrix_info`.
- **Exact correction expected:** Record reproducible P0 cold-start and
  matrix-snapshot baseline measurements with the R1-A01 metadata, or obtain an
  explicit approved scope change before phase approval. A unilateral deferral
  does not satisfy the recorded completion criterion.

### 4. Non-blocking recommendations

#### P0-A01 — Narrow the Ramp Summary guard wording to what it enforces

- **Evidence:** `scripts/consolidate_ramp_summary.py:_assert_combined_layout` and
  `build/check_ramp_summary_schema.py:test_layout_guard` describe a generic schema “length change,”
  but the implementation correctly raises only when growth reaches or crosses
  the next fixed anchor. Shrinkage and small growth that still fits the row
  budget do not raise. This matches the audit's overlap-focused minimum, but the
  broader wording overstates the contract.
- **Exact correction expected:** Reword comments, docstrings, and check labels to
  say “growth beyond the fixed row budget/overlap,” unless exact schema-length
  locking is intentionally added.

#### P0-A02 — Recheck the promised three-commit isolation after corrections

- **Evidence:** HEAD remains the recorded baseline `d2ee353`; all P0 product
  changes are uncommitted, as required by the coordination workflow. Therefore
  separation cannot yet be verified between the diagnostics symbols
  `GuiApi._handle` / `app.js:dispatch`, the side-label symbol
  `compare_env._cap_label`, and the Ramp Summary symbol
  `consolidate_ramp_summary._assert_combined_layout`.
- **Exact correction expected:** After all review fixes pass, preserve the three
  independently green commit boundaries promised in the Claude report; do not
  mix either characterized behavior change into the diagnostics commit.

### 5. Verification performed

- Confirmed phase `P0`, branch `refactor/v0.18.0-structural-overhaul`, baseline
  and current HEAD `d2ee35333f3ebd3a070c1adfec893c10d2ffbe58`.
- Inspected the baseline product diff: 9 modified tracked files plus 4 untracked
  `build/check_*.py` files; planning-directory changes were ignored.
- Ran and passed:
  `check_worker_lifecycle.py`, `check_import_direction.py`,
  `check_compare_env_sidelabel.py`, `check_ramp_summary_schema.py`,
  `check_gui_bridge.py`, `check_matrix_bridge.py`,
  `check_compare_ramp_summary.py`, and `check_ramp_summary_partial.py`.
- Ran `node --check scripts/ui/app.js`, AST-parsed every changed Python product
  file, and ran `git diff --check`; all passed.
- Confirmed all 48 `build/check_*.py` files are referenced by
  `.github/workflows/checks.yml`.
- Ran independent in-memory diagnostics proving the import-check false negatives
  and the duplicate-late successor-task state loss described above.
- Did not rerun the browser/mock launch or the complete 48-check suite; no live
  TSMIS, credentials, profiles, frozen build, or shared build artifact was used.

### 6. Whether Claude may proceed toward phase approval

**No.** Claude may correct P0, but must not approve/commit P0 or begin PA until
P0-B01 and the required fixes are resolved and a new review round yields `PASS`.

## Review round 2

### 1. Verdict: `BLOCKED`

The import-direction guard, Ramp Summary wording, dispatch documentation, worker
class anchors, and CI inventory were materially corrected. Coordination decision
D21 also gives the duplicate-late correctness fix a valid owner in P7a. P0 still
cannot pass because CT-10 does not meet the approved per-worker producer-path
coverage, and the required startup baseline is a warm constructor measurement
mislabelled as cold start.

### 2. Blocking findings

#### P0-B01 — CT-10 still does not exercise the approved per-worker lifecycle contract

- **Severity:** blocking
- **Status:** still open; the active-successor gap is now honestly characterized,
  and deferring its correctness fix to P7a under D21 is accepted.
- **Repository evidence:** `build/check_worker_lifecycle.py:_terminal_contract`
  (`:72-94`) injects terminal messages directly into `GuiApi._handle`; it never
  runs a worker's `run()` method or proves the worker emits exactly one terminal
  event on its success, cancellation, expected-error, and unexpected-error
  paths. The table also omits two distinct task-owning families entirely:
  `GuiApi.verify_environment` claims `_task = "envcheck"` and starts
  `EnvCheckWorker` (`scripts/gui_api.py:2672-2680`), whose terminal is
  `env_shot`; `GuiApi.check_environments` claims `_task = "envscan"` and starts
  `EnvScanWorker` (`:2724-2741`), whose terminal is `env_access_done`. Neither
  kind appears in `_terminal_contract`. Other encoded outcomes are sampled only
  as success: `batch_done` cancellation, `reset_done` cancellation/error,
  `chromium_done` cancellation/error, and `matrix_done` cancellation/error are
  not exercised. Generic rows named `"any worker"` for `error` do not prove the
  producing worker's path-dependent terminal behavior.
- **Why the green check is insufficient:** The approved R1-R14 contract explicitly
  arose because worker terminal delivery is path-dependent. Handler injection can
  prove that a received kind releases the gate, but cannot prove that each worker
  posts the right terminal exactly once when its body returns, cancels, raises an
  expected exception, or raises unexpectedly.
- **Exact correction expected:** Keep the D21 known-gap characterization, but add
  deterministic producer-path tests for every gate-owning worker class or
  explicitly justified worker family. Stub browser/filesystem/engine calls, run
  the real `run()` methods synchronously, capture their queues, assert one
  terminal kind per relevant outcome, then feed that terminal through
  `GuiApi._handle` and assert gate release/queue advancement. At minimum include
  the currently absent `EnvCheckWorker`/`env_shot` and
  `EnvScanWorker`/`env_access_done` families plus payload-encoded cancellation
  and failure variants. P0 need not implement the P7a exactly-once fix.

### 3. Required fixes

#### P0-R02 — The corrected canonical protocol map still claims completeness while omitting real kinds

- **Severity:** required
- **Status:** partially resolved. The three silent-drop statements, all ten
  worker class ranges, the `ExportWorker.run()` anchor, and the product-name CI
  entry are now correct.
- **Repository evidence:** `docs/internals/gui-bridge.md:74` calls its table the
  “master map” of every worker-posted kind, but the table omits
  `active_env_done`, `matrix_cell`, `matrix_done`, and `matrix_export_done`,
  all emitted in `scripts/gui_worker.py` and handled at
  `scripts/gui_api.py:480,549-553`. The discrepancy note at
  `docs/internals/gui-bridge.md:102` says the worker protocol docstring omits
  only `check`, `checks_done`, `batch_progress`, and `batch_done`; the docstring
  also omits those four active-env/matrix kinds.
- **Exact correction expected:** Add the four missing protocol rows and correct
  the discrepancy note, or narrow the table's completeness claim and enumerate
  every intentional omission accurately.

#### P0-R03 — The reported cold-start baseline is not a cold-start measurement or reproducible artifact

- **Severity:** required
- **Status:** still open.
- **Repository evidence:** The remediation explicitly says modules were
  pre-imported and times only fresh `GuiApi()` plus `get_initial_state()`
  (`P0-claude-report.md:287-297`). That excludes `gui_api`/`reports` import time,
  the eager-import cost that finding F11 and the later P10 optimization are meant
  to compare. Its “Reproduce” instruction points to an inline harness in a prior
  turn transcript rather than preserving the command or code in the report.
  An independent five-process diagnostic that included `import gui_api` plus the
  same stubbed initialization measured **1160-1561 ms**, versus the reported
  **8.71-10.26 ms**, confirming the metrics describe different operations.
- **Exact correction expected:** Record a real process-cold baseline that includes
  importing the GUI dependency graph and the stubbed initial-state construction,
  with the full reproducible command/harness in the report. Keep the 9 ms number
  only if relabelled as warm, pre-imported initialization. Preserve environment,
  data shape, repeat count, percentile method, and stubbing details for both
  startup and matrix measurements.

### 4. Non-blocking recommendations

#### P0-A02 — Commit-boundary isolation remains pending

- **Severity:** recommended
- **Status:** unchanged and appropriately deferred until after a passing review.
- **Repository evidence:** HEAD remains baseline `d2ee353`; diagnostics,
  `compare_env._cap_label`, and
  `consolidate_ramp_summary._assert_combined_layout` are still uncommitted.
- **Exact correction expected:** After all blocking/required fixes pass, retain
  the promised three independently green commits. This does not itself block the
  current code review.

### 5. Verification performed

- Confirmed P0 remains `awaiting_review`, baseline/current HEAD is
  `d2ee35333f3ebd3a070c1adfec893c10d2ffbe58`, and the product diff remains
  limited to the approved 9 tracked files plus 4 new checks.
- Re-ran and passed `check_worker_lifecycle.py`,
  `check_import_direction.py`, `check_compare_env_sidelabel.py`,
  `check_ramp_summary_schema.py`, `check_gui_bridge.py`, and
  `check_matrix_bridge.py`.
- Ran `node --check scripts/ui/app.js` and `git diff --check`; both passed.
- Confirmed all 48 `build/check_*.py` files are wired into
  `.github/workflows/checks.yml`.
- Independently cross-checked all ten documented worker class ranges against
  `scripts/gui_worker.py`; all now match.
- Independently parsed worker queue emissions against the canonical protocol
  table, identifying the four omitted kinds above.
- Independently measured five fresh Python processes including `import gui_api`
  and stubbed `GuiApi().get_initial_state()`: 1560.95, 1198.91, 1160.44,
  1260.32, and 1322.55 ms.
- Verified P0-R01 and P0-A01 are resolved: import analyzer self-tests detect the
  prior false-negative cases, and the Ramp Summary guard now describes only
  overlap-causing growth.
- Did not run the complete 48-check suite, browser/mock launch, frozen build, or
  live TSMIS paths.

### 6. Whether Claude may proceed toward phase approval

**No.** Claude may remediate P0, but must not approve/commit it or begin PA until
P0-B01, P0-R02, and P0-R03 are resolved and a subsequent review returns `PASS`.

## Review round 3

### 1. Verdict: `BLOCKED`

Round 2's protocol-map and performance-baseline corrections are complete and
independently reproducible. CT-10 is now a real producer-path harness for eleven
worker classes, but it explicitly excludes `LoginWorker`; therefore the approved
per-worker lifecycle criterion remains incomplete.

### 2. Blocking findings

#### P0-B01 — `LoginWorker` remains outside the producer-path lifecycle contract

- **Severity:** blocking
- **Status:** still open, narrowed to one worker. The D21 active-successor
  correctness deferral to P7a remains accepted and is not being reopened.
- **Repository evidence:** `build/check_worker_lifecycle.py:21-27` explicitly
  states that `LoginWorker` is not producer-tested. It is nevertheless a
  gate-owning worker: `GuiApi.start_login` sets `_task = "login"` and starts
  `LoginWorker` (`scripts/gui_api.py:2629-2641`). Its real producer has multiple
  path-dependent terminals in `LoginWorker.run` and
  `_run_login_in_browser` (`scripts/gui_worker.py:1248-1442`):
  `login_saved`, `login_device_ok`, `login_failed`, `cancelled`, and `error`.
  Contrary to the check's claim that these kinds “are covered by the
  gate-release variants below,”
  `test_terminal_payload_variants` (`build/check_worker_lifecycle.py:336-355`)
  contains none of `login_saved`, `login_device_ok`, or `login_failed`.
- **Independent feasibility evidence:** A read-only diagnostic ran the real
  `LoginWorker.run()` with a fake Playwright context/browser, immediate fake
  completion event, stubbed `new_login_context`, `is_logged_in`, and
  `save_auth_state`. Without launching a browser or writing auth state it
  deterministically produced exactly one terminal for five paths:
  success→`login_saved`, cancel→`cancelled`, no detected login→`login_failed`,
  `BrowserNotFoundError`→`error`, and unexpected `RuntimeError`→`error`.
  Therefore producer characterization does not require a work PC or rebuilding
  the full live sign-in stack. The Edge-device fallback can likewise be isolated
  by stubbing `_try_edge_persistent_login` and `storage_state_is_portable`.
- **Exact correction expected:** Add offline real-`run()` producer scenarios for
  `LoginWorker` covering at least `login_saved`, `login_device_ok`,
  `login_failed`, cancellation, expected error, and unexpected error. Assert
  exactly one terminal for each, feed it through `GuiApi._handle`, and assert
  gate release/queue behavior consistently with the other worker scenarios.
  Remove the inaccurate exclusion/coverage statement. No live browser, auth
  file, or P7a exactly-once implementation is required.

### 3. Required fixes

None beyond P0-B01.

- **P0-R02:** resolved. The canonical table now maps all 27 statically emitted
  worker kinds, including `active_env_done`, `matrix_cell`, `matrix_done`, and
  `matrix_export_done`; its discrepancy note lists all eight docstring omissions.
- **P0-R03:** resolved. `build/measure_baselines.py` preserves a reproducible
  fresh-process measurement including `import gui_api`, labels initialization
  and matrix timings as warm, and records environment/data-shape/repeat/percentile
  metadata.

### 4. Non-blocking recommendations

#### P0-A02 — Preserve the approved three-commit boundary after PASS

- **Severity:** recommended
- **Status:** unchanged.
- **Repository evidence:** HEAD remains `d2ee353`; the diagnostics/tooling work,
  `compare_env._cap_label`, and
  `consolidate_ramp_summary._assert_combined_layout` remain uncommitted.
- **Exact correction expected:** Once P0-B01 is resolved and reviewed, retain the
  promised independently green diagnostics, side-label, and Ramp Summary
  commits.

### 5. Verification performed

- Confirmed P0 remains `awaiting_review` at baseline/current HEAD
  `d2ee35333f3ebd3a070c1adfec893c10d2ffbe58`.
- Inspected the full approved product diff: 9 modified tracked files plus 5 new
  build files; no persisted settings/auth/cache/manifest/output format or
  packaging source was changed.
- Re-ran and passed `check_worker_lifecycle.py`,
  `check_import_direction.py`, `check_compare_env_sidelabel.py`, and
  `check_ramp_summary_schema.py`.
- Ran `build/measure_baselines.py --repeats 3`; it reproduced process-cold total
  startup at 1285.52-1637.92 ms and warm `matrix_info()` at 7.81-9.72 ms.
- Independently parsed `gui_worker.py` emissions against the
  `gui-bridge.md` master table: 27 worker kinds, 27 mapped, no missing or extra
  rows.
- Independently ran real, fully stubbed `LoginWorker.run()` diagnostics for
  success, cancellation, no-login failure, expected error, and unexpected error;
  each emitted exactly one expected terminal without browser/auth side effects.
- AST-parsed all changed/new Python implementation and build files, ran
  `node --check scripts/ui/app.js`, `git diff --check`, and confirmed all 48
  `check_*.py` files remain wired into CI; all passed.
- Did not run the complete 48-check suite, browser/mock launch, frozen build, or
  live TSMIS paths.

### 6. Whether Claude may proceed toward phase approval

**No.** Claude may make the narrow P0-B01 test correction, but must not
approve/commit P0 or begin PA until a subsequent review returns `PASS`.

## Review round 4

### 1. Verdict: `PASS`

P0 now satisfies the approved phase. The last open blocker, `LoginWorker`
producer-path lifecycle coverage, is resolved without product behavior changes.
All prior blocking and required findings are closed, the known duplicate-late
correctness gap remains honestly locked and assigned to P7a by coordination D21,
and the complete blocking check inventory passes independently.

### 2. Blocking findings

None.

#### P0-B01 — Resolved

- **Repository evidence:** `build/check_worker_lifecycle.py:_login` drives the
  real `LoginWorker.run()` / `_run_login_in_browser` path with isolated fake
  Playwright/browser/context seams and a no-op `_save_state`. `_SCENARIOS`
  includes six `LoginWorker` outcomes: success→`login_saved`,
  device-mode→`login_device_ok`, no-login→`login_failed`,
  cancel→`cancelled`, expected-error→`error`, and
  unexpected-error→`error` (`build/check_worker_lifecycle.py:406-411`).
  Each scenario asserts exactly one terminal and feeds it through
  `GuiApi._handle` to prove gate release. The harness now contains 27 producer
  scenarios spanning all 12 gate-owning worker classes.
- **Disposition:** Closed. The P7a-known active-successor defect is still
  characterized separately and is not falsely presented as fixed in P0.

### 3. Required fixes

None.

- **P0-R01:** resolved — import-time graph analysis includes module-scope
  compound statements, retains self-edges, and self-tests prior false negatives.
- **P0-R02:** resolved — the canonical bridge table maps all 27 statically
  emitted worker kinds; dispatch semantics and worker anchors match current code.
- **P0-R03:** resolved — `build/measure_baselines.py` records reproducible
  process-cold startup and warm matrix baselines with environment, data shape,
  repeats, and percentile methodology.

### 4. Non-blocking recommendations

#### P0-A02 — Preserve the approved commit separation

- **Severity:** recommended
- **Repository evidence:** HEAD remains the phase baseline `d2ee353`; the
  diagnostics/tooling changes, `compare_env._cap_label`, and
  `consolidate_ramp_summary._assert_combined_layout` are still uncommitted in
  accordance with the review workflow.
- **Exact correction expected:** Commit P0 using the promised three independently
  green boundaries: diagnostics/docs/tooling, side-label behavior, and Ramp
  Summary guard. Do not stage or commit the planning directory.

### 5. Verification performed

- Confirmed P0 is `awaiting_review`, branch
  `refactor/v0.18.0-structural-overhaul`, baseline/current HEAD
  `d2ee35333f3ebd3a070c1adfec893c10d2ffbe58`.
- Inspected the complete baseline diff: 9 modified tracked files plus 5 new
  build files, all within approved P0 scope. No settings, auth, cache, manifest,
  output-format, packaging, dependency, or application-registry migration was
  introduced.
- Re-ran `check_worker_lifecycle.py`: all 27 producer scenarios, payload
  variants, queue advancement, idle duplicate, and D21 known-gap assertions
  passed.
- Confirmed `_SCENARIOS` spans 12 worker classes and includes all six required
  `LoginWorker` terminal outcomes.
- Independently parsed worker emissions against `gui-bridge.md`: 27 emitted
  kinds, 27 mapped, no omissions or extras.
- Ran the complete `build/check_*.py` inventory independently: **48/48 PASS**,
  including the fake-site, GUI bridge, matrix, updater, comparison, export,
  lifecycle, import-direction, and characterization checks.
- AST-parsed changed/new Python files, ran `node --check scripts/ui/app.js`, and
  ran `git diff --check`; all passed.
- Verified the check run did not alter the product diff or create additional
  repository artifacts.
- Did not run a frozen build, GUI launch, live TSMIS path, credentials, or
  browser profile.

### 6. Whether Claude may proceed toward phase approval

**Yes.** Claude may mark P0 approved and commit it using the promised isolated
commit boundaries. Per coordination, Claude must not begin PA in the same turn
as the P0 commit.
