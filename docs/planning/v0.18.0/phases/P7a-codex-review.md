# P7a Codex review

## Review round 1

### 1. Verdict: `BLOCKED`

P7a is mostly within its approved structural scope: the product diff is limited to the new
`contract.py`/`task_coordinator.py` boundary, `gui_api.py` lifecycle/dispatch delegation, logged
swallows in `gui_worker.py`, app-spec reachability, and the CT-10 update. The bridge and packaging
checks I ran are green, and the task-specific `export_done` late-terminal case is fixed.

The phase cannot pass yet because the new exactly-once lifecycle is only kind-guarded. It still accepts
late generic terminals (`error`/`cancelled`) against whatever task is currently running, and it still
accepts a late same-kind matrix terminal against a successor matrix job. Both paths can clear an
already-started successor, so the P0/D21 duplicate-late class is not fully closed.

### 2. Blocking findings

#### P7a-B01 - Blocking - The exactly-once terminal guard still clobbers active successors for wildcard and same-kind terminals

- **Affected phase area:** P7a exactly-once lifecycle / CT-10; `scripts/gui_api.py::_handle`;
  `scripts/gui_api.py::_TERMINAL_TASK`; `scripts/task_coordinator.py::TaskCoordinator.owns`;
  `build/check_worker_lifecycle.py::test_duplicate_late_active_successor`.
- **Repository evidence:** `_TERMINAL_TASK` maps `contract.Msg.CANCELLED` and `contract.Msg.ERROR` to
  `None` (`scripts/gui_api.py:106-107`). `_handle` drops terminals only when
  `not self._coord.owns(_TERMINAL_TASK[kind])` (`scripts/gui_api.py:606`), while
  `TaskCoordinator.owns(None)` means "any task running" (`scripts/task_coordinator.py:53-60`). Therefore
  a stale generic `error` or `cancelled` terminal from a finished task is accepted if a successor is
  active. The accepted handlers call `_end_task` (`scripts/gui_api.py:690-704` and
  `scripts/gui_api.py:1098-1133`), which clears the successor's gate/current job via
  `self._coord.release()`.
- **Repository evidence:** CT-10's active-successor duplicate-late test covers only a task-specific
  `export_done` straggler plus a different-kind `consolidate_done` straggler
  (`build/check_worker_lifecycle.py:519-536`). It does not cover duplicate/late `error`, `cancelled`,
  or same-kind matrix terminals, even though the approved P7a test scope is "success/cancel/error/
  duplicate-late asserting gate release + queue advance" (`05-claude-final-plan.md:469-471`).
- **Independent diagnostic:** I drove a real `GuiApi._handle` through the same queue-successor pattern
  used by CT-10. A duplicate task-specific `export_done` preserves the active matrix successor
  (`post=('matrix', True, 0)`), but a duplicate generic `error` or `cancelled` clears it
  (`post=(None, False, 0)`). I also reproduced the same-kind gap: after a first queued matrix job
  completed and auto-started a second matrix job, a stale duplicate `matrix_done` cleared the second
  job (`after duplicate same-kind matrix_done=None None 0`).
- **Impact:** This is the central P7a behavior change. It means the advertised "a duplicate/late terminal
  can't clobber a successor that already started" guarantee is not true for all terminal classes. It also
  leaves CT-10 green while missing the generic terminal paths most likely to be emitted by error/cancel
  outcomes.
- **Exact correction expected:** Make terminal handling owner-aware for every terminal, not just
  different task-specific kinds. Do not treat `error`/`cancelled` as "owned by any running task" when
  deciding whether a terminal is late. Either carry/record a task-instance identity for generic
  terminals, or introduce an equivalently precise guard that can distinguish the terminal's originating
  task/job from the current successor. Add CT-10 active-successor duplicate-late cases for at least
  generic `error`, generic `cancelled`, and queued matrix-to-matrix `matrix_done`, while preserving the
  normal first-terminal behavior: a legitimate first `error`/`cancelled` still frees the current gate and
  advances queued work exactly once.

### 3. Required fixes

#### P7a-R01 - Required - The approved `#mock` completion check is reclassified as external without reconciliation

- **Affected phase area:** P7a completion criteria / verification reporting.
- **Repository evidence:** The approved final plan lists `#mock` in P7a tests and completion:
  "CT-10 lifecycle ...; `check_gui_bridge`/`matrix_bridge`/`day_matrix`/`b3`; `#mock`" and
  "Completion: CT-10 + bridge checks green; `#mock` all tabs; 44/44 green"
  (`docs/planning/v0.18.0/05-claude-final-plan.md:469-471`). The P7a report instead says a manual
  `#mock` all-tabs smoke remains "recommended external verification" and "not part of the offline DoD"
  (`docs/planning/v0.18.0/phases/P7a-claude-report.md:130-135`).
- **Impact:** I agree `ui/app.js` is untouched and the risk is lower than the lifecycle bug, but this is
  still an unreconciled completion-criteria mismatch. The phase report should not silently demote a final
  plan gate.
- **Exact correction expected:** Either run and record the approved deterministic `#mock` all-tabs
  verification for P7a, or record a coordination/user-approved scope decision that reclassifies it for
  this backend-only phase. Do not leave the final plan saying `#mock` is a completion criterion while the
  phase report treats it as optional external verification.

### 4. Non-blocking recommendations

#### P7a-A01 - Recommended - Add a permanent protocol coverage assertion for the new contract SSOT

- **Affected phase area:** bridge contract drift prevention; `scripts/contract.py`;
  `scripts/gui_api.py::_dispatch`; `scripts/gui_api.py::_TERMINAL_TASK`;
  `build/check_worker_lifecycle.py`.
- **Repository evidence:** `contract.py` is introduced as the bridge enum SSOT, and the runtime dispatch
  currently covers all `contract.Msg` constants in my independent probe. However the permanent lifecycle
  check still defines its own literal `TERMINAL` set (`build/check_worker_lifecycle.py:58-61`), and I did
  not find a committed assertion that `_TERMINAL_TASK.keys() == contract.TERMINAL` or that `_dispatch`
  covers every declared message constant.
- **Exact correction expected:** Add a small permanent assertion, preferably in CT-10 or a bridge check,
  that the runtime dispatch table and terminal-task map are complete relative to `contract.Msg` /
  `contract.TERMINAL`. If the CT intentionally keeps an independent oracle, document that choice and add
  the runtime parity assertion separately.

### 5. Verification performed

- Confirmed `docs/planning/v0.18.0/00-coordination.md` marks **P7a** `awaiting_review` with baseline
  `8d9ec2e`.
- Read `docs/planning/v0.18.0/05-claude-final-plan.md`, the current
  `docs/planning/v0.18.0/phases/P7a-claude-report.md`, and relevant prior P0 lifecycle review history.
- Inspected the product diff from `8d9ec2e`, excluding `docs/planning/**`: modified
  `build/app.spec`, `build/check_worker_lifecycle.py`, `scripts/gui_api.py`, `scripts/gui_worker.py`,
  plus new untracked `scripts/contract.py` and `scripts/task_coordinator.py`.
- Confirmed the P7a diff does not touch frontend files, compare/matrix/engine source, updater, persisted
  settings/auth/cache/manifest formats, or output layout.
- Ran and passed:
  - `python -B -X utf8 build/check_worker_lifecycle.py`
  - `python -B -X utf8 build/check_gui_bridge.py`
  - `python -B -X utf8 build/check_matrix_bridge.py`
  - `python -B -X utf8 build/check_day_matrix.py`
  - `python -B -X utf8 build/check_b3_batch.py`
  - `python -B -X utf8 build/check_intersection_gate.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_no_misspelling.py`
  - `python -B -X utf8 -m py_compile scripts/gui_api.py scripts/gui_worker.py scripts/contract.py scripts/task_coordinator.py build/check_worker_lifecycle.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `node build/check_compare_routing.js`
  - `git diff --check 8d9ec2e -- . ':(exclude)docs/planning/**'`
- Ran an independent dispatch-coverage probe: `_TERMINAL_TASK` has no missing/extra keys relative to
  `contract.TERMINAL`, and a fresh `GuiApi()._dispatch` has no missing/extra handlers relative to the
  declared `contract.Msg` constants.
- Ran independent lifecycle diagnostics proving P7a-B01: task-specific `export_done` duplicate-late is
  now safe, but duplicate/late generic `error`, duplicate/late generic `cancelled`, and duplicate/late
  same-kind `matrix_done` still clear an already-active successor.
- Did not run the complete `build/check_*.py` suite, build scripts, PyInstaller, frozen self-tests,
  live TSMIS, credentials, browser profiles, private report data, or shared release artifacts. I also did
  not launch a browser/GUI for `#mock`; the review treats that as an unreconciled Claude verification
  item rather than performing it here.

### 6. Whether Claude may proceed toward phase approval

No. Claude should remediate P7a-B01, address or reconcile P7a-R01, and may optionally apply P7a-A01,
then return P7a for another review. Claude should not approve/commit P7a or proceed to the next phase
until a subsequent review returns `PASS`.

## Review round 2

### 1. Verdict: `PASS`

P7a is ready for phase approval. The round-1 blocking lifecycle defect is fixed by the per-claim epoch
model, the required `#mock` gate has been recorded in Claude's remediation report, and the recommended
contract parity assertion has been added. I found no new blocking, required, or recommended findings.

### 2. Blocking findings

None open.

- **P7a-B01 — Resolved.** The previous kind-only guard could not distinguish stale wildcard
  `error`/`cancelled` terminals or stale same-kind `matrix_done` terminals from the currently active
  successor. Current code in `scripts/task_coordinator.py` uses a per-claim `_epoch` with
  `current_epoch()`/`is_live()`, and `scripts/gui_api.py` stamps gate-owning workers via
  `_StampedQueue` before `_handle()` accepts terminal messages. Independent diagnostics now show stale
  `export_done`, generic `error`, generic `cancelled`, and same-kind `matrix_done` terminals leave the
  active successor intact; a current-epoch `error` still releases the active task as expected.

### 3. Required fixes

None open.

- **P7a-R01 — Resolved.** Claude's remediation section records the deterministic `#mock` all-tabs smoke
  run (`scripts/ui` served with `python -m http.server 8765`, `/index.html#mock`, main and matrix tabs,
  zero console errors). I did not launch a browser/GUI during this read-only review, but the completion
  criterion is no longer silently reclassified as external/not-DoD in the newest phase report.

### 4. Non-blocking recommendations

None open.

- **P7a-A01 — Resolved.** `build/check_worker_lifecycle.py::test_dispatch_covers_contract` now locks the
  dispatch/terminal vocabulary against `scripts/contract.py`; an independent probe also found no missing
  or extra dispatch handlers and no terminal kinds without handlers.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`,
  `docs/planning/v0.18.0/phases/P7a-claude-report.md`, and this review file's prior round.
- Confirmed P7a is still `awaiting_review` with baseline `8d9ec2e`.
- Inspected the product diff from `8d9ec2e`, excluding `docs/planning/**`: modified
  `build/app.spec`, `build/check_worker_lifecycle.py`, `scripts/gui_api.py`, `scripts/gui_worker.py`,
  plus new untracked `scripts/contract.py` and `scripts/task_coordinator.py`.
- Confirmed the product diff stays within P7a's approved scope: no frontend source changes, no
  compare/matrix/engine/updater/settings/auth/cache/manifest/output-layout migration changes, and no
  P7b endpoint extraction.
- Confirmed raw `self._q` worker starts are limited to ungated non-terminal producers
  (`ActiveEnvCheckWorker`, `CheckWorker`, `UpdateWorker`); gate-owning workers use `_gated_queue()`.
- Ran independent lifecycle diagnostics against `GuiApi._handle()` and `TaskCoordinator` to recheck
  P7a-B01, including stale wildcard and same-kind matrix cases.
- Ran an independent contract/dispatch parity probe against `contract.Msg`, `contract.TERMINAL`, and
  `GuiApi()._dispatch`.
- Ran and passed:
  - `python -B -X utf8 build/check_worker_lifecycle.py`
  - `python -B -X utf8 build/check_gui_bridge.py`
  - `python -B -X utf8 build/check_matrix_bridge.py`
  - `python -B -X utf8 build/check_day_matrix.py`
  - `python -B -X utf8 build/check_b3_batch.py`
  - `python -B -X utf8 build/check_intersection_gate.py`
  - `python -B -X utf8 build/check_batch_outcome.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_no_misspelling.py`
  - `python -B -X utf8 -m py_compile scripts/gui_api.py scripts/gui_worker.py scripts/contract.py scripts/task_coordinator.py build/check_worker_lifecycle.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `node build/check_compare_routing.js`
  - `git diff --check 8d9ec2e -- . ':(exclude)docs/planning/**'`
- Did not run the complete `build/check_*.py` suite, build scripts, PyInstaller, frozen self-tests,
  live TSMIS, credentials, browser profiles, private report data, browser/GUI launches, or shared
  release artifacts.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval for P7a. No open Codex findings remain for this phase.
