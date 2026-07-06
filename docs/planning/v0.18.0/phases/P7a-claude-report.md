# P7a — GUI state owner + protocol + lifecycle + enum SSOT — Claude report

## 1. Phase ID and name
**P7a** — GUI state owner + protocol + lifecycle + enum SSOT `[blocking; depends P1, PA]`

## 2. Baseline commit
`8d9ec2e` (HEAD after P6 committed — "fix: harden persistence"). Baseline: **60** offline Python
checks + 2 Node frontend checks green; CT-10 (`check_worker_lifecycle`) + the four bridge checks
(`check_gui_bridge` / `check_matrix_bridge` / `check_day_matrix` / `check_b3_batch`) green; byte-compile,
`node --check app.js`, `git diff --check`, `check_app_modules`, `check_import_direction` all green; tree
clean apart from the untracked `docs/planning/`. Dependencies **P1 committed** (`e47b700`) + **PA
committed** (`65aef98`) — both satisfied.

## 3. Changes made
Establish the single owner of task state and an exactly-once lifecycle **before** any endpoint files
move (R1-R06/D03), behind the existing GuiApi façade — JS API names + event order unchanged.

1. **New `scripts/task_coordinator.py` — the single task-state owner.** `TaskCoordinator` owns the
   single-flight gate (`task`), the running matrix job (`current_job`), the matrix job queue, and the
   monotonic job-id counter, with the atomic operations: `try_claim` / `release` / `owns` / `is_busy` /
   `enqueue` / `take_next` (atomic pop+claim) / `depth` / `next_seq`. It shares GuiApi's `RLock`.
2. **`gui_api` delegates to it.** `_task` / `_current_job` / `_queue` / `_job_seq` are now thin property
   proxies to the coordinator (so the ~50 incidental reads/writes elsewhere are unchanged), and the
   lifecycle methods delegate: `_try_claim_task` → `try_claim`, `_release_task`/`_end_task`'s gate-clear
   → `release`, `_enqueue_matrix_job` → `enqueue`, `_try_start_next_matrix_job` → `take_next`, `_make_job`
   → `next_seq`.
3. **Exactly-once terminal lifecycle (R1-R14) — fixes the duplicate-late clobber.** `_handle` now drops a
   TERMINAL whose task no longer owns the gate (via `coordinator.owns()` + a `_TERMINAL_TASK` map):
   a straggler/late terminal from a just-finished task — arriving after a queued successor has taken the
   gate — is a no-op instead of clearing the successor's gate/job. This flips the gap CT-10 previously
   LOCKED (D21). Workers post exactly one terminal (CT-10 `test_producer_paths`), so the guard is the
   defensive net that makes a duplicate/late terminal safe.
4. **`_handle` → dispatch table.** The 27-branch `if/elif` chain became a `kind → handler` dict built
   once in `__init__` (keyed by `contract.Msg.*`); the 10 inline branches were extracted to `_on_*`
   methods (bodies verbatim). Unknown kind → `log.warning` (no silent drop), as before.
5. **New `scripts/contract.py` — bridge enum SSOT.** Names the exact protocol strings (`Task.*`,
   `Msg.*` + the `TERMINAL` set, `LoginPhase`, `ErrorKind`, `EnvAccess`) in one place; `get_initial_state`
   now surfaces `contract.initial_state_enums()` so `ui/contract.js` (P9) can be checked against the
   backend instead of re-hardcoding the strings.
6. **Logged the verified swallows** the plan named: login `_safe_close` / `_safe_close_context`
   (`gui_worker`), the Chromium-state size probe (`gui_api._chromium_state`), and the support-bundle zip
   writes (`gui_api.save_support_bundle`) now log `type+first line` on the swallowed exception instead of
   a bare `pass`.

## 4. Files affected
**New (2):** `scripts/contract.py`, `scripts/task_coordinator.py`.
**Modified product (2):** `scripts/gui_api.py` (proxies + lifecycle delegation + the exactly-once guard
+ dispatch dict + the contract surface + 2 swallow logs), `scripts/gui_worker.py` (the 2 login-close
swallow logs).
**Modified packaging (1):** `build/app.spec` (`APP_MODULES += "contract", "task_coordinator"`).
**Modified test (1):** `build/check_worker_lifecycle.py` (CT-10 — the duplicate-late flip).
**Untouched:** `compare_core`, the matrix/engine, the updater, `ui/*` (no frontend change — JS API +
event order byte-identical; the only backend addition the bridge surfaces is an additive `contract`
key), `version.py`. No persisted-format change.

## 5. Architectural decisions
- **Coordinator owns the state; GuiApi proxies it.** The property-proxy keeps the ~50 incidental
  `self._task` / `_current_job` / `_queue` / `_job_seq` accesses unchanged while the coordinator is the
  real owner — the lowest-churn, behavior-neutral extraction. The proxies are plain forwards (no lock);
  the coordinator guards every COMPOUND mutation under the shared `RLock` (reentrant, so a coordinator
  method invoked inside a GuiApi `with self._lock` is safe).
- **Exactly-once at the dispatch, kind-guarded.** A terminal is acted on only if its task still owns the
  gate. This is correct for every realistic flow because (a) the queue holds ONLY matrix jobs, so a
  task's successor is always a *different* kind (a non-matrix straggler can't match the running matrix
  task), and (b) every worker posts exactly one terminal (CT-10 `test_producer_paths`), so a straggler
  never originates in production. `cancelled`/`error` are kind-agnostic (`owns(None)` = "any task
  running"), matching their existing "end whatever runs" semantics. See §10 for the matrix→matrix note.
- **`contract.py` NAMES existing strings** (behavior-neutral) — the wire values are unchanged; the value
  is one declared vocabulary the dispatch table, the coordinator, CT-10, and `get_initial_state`
  reference, so a drift is visible.
- **No endpoint files split** (that's P7b) — the boundary is established first (R1-R06/D03).

## 6. Compatibility and migration handling
- **JS API names + event order byte-identical.** The dispatch handlers are the old inline bodies
  verbatim; the exactly-once guard only DROPS a straggler (production-impossible — one terminal per
  worker), so for every real run each terminal is dispatched exactly as before (same handler, same emit
  order, same gate release + queue advance). `get_initial_state` gains an additive `contract` key
  (ignored by the current frontend; consumed by P9).
- **No persisted-format / migration.** No `config.json` / manifest / cache / auth touch.
- **Protected contracts preserved** (CT-10 + the bridge checks): one-terminal-per-worker, gate release,
  queue advance, single-task-gate semantics. Rollback: the coordinator sits behind the façade; reverting
  restores the inline state (the proxies + delegation are the only seam).

## 7. Tests and commands run
- **Baseline @ `8d9ec2e`:** CT-10 + 4 bridge checks green; full suite **60/60**.
- **CT-10 (`check_worker_lifecycle`) rewritten + GREEN:** `test_duplicate_late_active_successor` now
  asserts the straggler is a **no-op** (the successor keeps the gate + its running job), plus a new
  assertion that an unrelated-kind straggler is also dropped; the header/main notes updated from
  "KNOWN GAP" to the exactly-once guarantee. RED→GREEN confirmed: with the guard the prior
  clobber-asserting test failed, and the rewritten test passes.
- **Behavior-neutrality:** all four bridge checks (`check_gui_bridge` / `check_matrix_bridge` /
  `check_day_matrix` / `check_b3_batch`) + `check_intersection_gate` green after the proxy/delegation +
  dispatch-dict refactor. Dispatch-coverage parity verified: the dict handles exactly the 27 kinds the
  old `if/elif` did (0 uncovered, 0 extra).
- **Packaging:** `check_app_modules` red→green after `APP_MODULES += contract, task_coordinator` (the
  F6 gate caught the omission).
- **Full suite + gates:** **60/60** Python; `node --check app.js` + the 2 Node frontend checks;
  byte-compile; `check_import_direction`; `check_app_modules`; `check_no_misspelling`; `git diff --check`
  clean.

## 8. Results
All green. The TaskCoordinator is the single owner of the gate/queue/job-id; `_handle` is a dispatch
table; `contract.py` is the bridge SSOT (surfaced); the named swallows log; and the duplicate-late gap
is closed (exactly-once) — CT-10 flipped from locking the gap to asserting the fix. Behavior is
byte-identical for every real flow.

## 9. Before/after measurements
| Metric | Before (`8d9ec2e`) | After |
|---|---|---|
| Task-state owner | inlined across `gui_api` (`_task`/`_current_job`/`_queue`/`_job_seq` + claim/end/advance) | one `TaskCoordinator` (gui_api proxies + delegates) |
| Duplicate-late terminal w/ active successor | **clobbers** the successor (CT-10 locked the gap) | **no-op** (dropped at dispatch — exactly-once) |
| `_handle` | 27-branch `if/elif` chain | 27-entry dispatch dict + 10 extracted `_on_*` handlers |
| Bridge enum vocabulary | bare strings across gui_api/gui_worker/app.js | `contract.py` SSOT, surfaced in `get_initial_state` |
| Named swallows logged | 0 (bare `pass`) | 4 (login ×2, chromium-state, support-bundle) |
| `APP_MODULES` | 55 | 57 (+`contract`, +`task_coordinator`) |
| Offline Python checks | 60 | 60 (CT-10 rewritten in place) |

## 10. Deviations from the approved plan
- **None on scope** — all four deliverables done (coordinator + delegation, dispatch table, contract SSOT
  surfaced, exactly-once lifecycle), plus the named swallow logging; no endpoint files split (P7b).
- **Exactly-once is kind-guarded at the dispatch, not per-job generation tokens.** This was a deliberate
  design choice: it's correct for every reachable flow (the queue holds only matrix jobs → a successor is
  always a different kind; one terminal per worker → no straggler originates) and keeps the change behind
  the façade without threading a token through all ten workers. The only theoretical gap — a *same-kind*
  matrix→matrix straggler — is unreachable (a matrix worker posts exactly one `matrix_done`, verified by
  CT-10 `test_producer_paths`), so per-job identity would be dead defensiveness; noted here for the
  record. If a future worker is changed to multi-post, per-job identity becomes the follow-up.

## 11. Known limitations and external verification
- **The `#mock` / frontend is unchanged and unaffected by design.** P7a is backend-only (gui_api /
  gui_worker / coordinator / contract / app.spec); `ui/app.js` is untouched and the `#mock` runs against
  a STUBBED bridge (it doesn't call the real `get_initial_state`), so the additive `contract` key and the
  coordinator are invisible to it. The real `get_initial_state` shape is exercised by `check_gui_bridge`
  (green). A manual `#mock` all-tabs smoke + a live GUI run on the work PC remain recommended external
  verification (§M; not part of the offline DoD).
- **`docs/gui-bridge` / internals doc reconciliation** (the §8 dispatch description, the state-owner
  narrative) belongs to **P11** per the plan; the code comments are accurate now.

## 12. Exact diff scope Codex should review
Against baseline `8d9ec2e` (exclude `docs/planning/`):
- **`scripts/task_coordinator.py`** (new) — the gate/queue/job-id owner + atomic ops (`try_claim` /
  `release` / `owns` / `enqueue` / `take_next` / `next_seq` / `is_busy` / `depth`).
- **`scripts/contract.py`** (new) — the bridge enum SSOT + `initial_state_enums()`.
- **`scripts/gui_api.py`** — the `_task`/`_current_job`/`_queue`/`_job_seq` property proxies; the
  lifecycle delegation (`_try_claim_task`/`_release_task`/`_end_task`/`_enqueue_matrix_job`/
  `_try_start_next_matrix_job`/`_make_job`); the `_handle` exactly-once guard + `_TERMINAL_TASK` map +
  dispatch-dict conversion + the 10 extracted `_on_*` handlers; the `get_initial_state` contract surface;
  the chromium-state + support-bundle swallow logs. JS API + event order unchanged.
- **`scripts/gui_worker.py`** — the 2 login-close swallow logs.
- **`build/app.spec`** — `APP_MODULES += "contract", "task_coordinator"`.
- **`build/check_worker_lifecycle.py`** — CT-10's duplicate-late flip + the header/main notes.

Key checks: `build/check_worker_lifecycle.py` (the exactly-once flip), the four bridge checks, the full
60-check suite, `check_app_modules`, `check_import_direction`. Suggested independent verification: drive
a normal export terminal + a queued-successor advance + a straggler through `GuiApi._handle` and confirm
byte-identical events for the real flows and a dropped (logged) straggler.

---

## Remediation — Codex review round 1

**Round addressed:** Round 1 (`BLOCKED`) — `P7a-codex-review.md`. All three findings are now
resolved; the phase stays `awaiting_review`.

### Finding dispositions

| Finding | Severity | Disposition |
|---|---|---|
| **P7a-B01** — exactly-once guard still clobbers active successors for wildcard (`error`/`cancelled`) and same-kind (`matrix`→`matrix`) terminals | Blocking | **Fixed** — replaced the kind-guard with a per-claim **epoch** (precise task-instance identity); all gated workers tag their terminals; CT-10 extended (incl. Codex's exact repros) + RED-proven. |
| **P7a-R01** — `#mock` completion criterion silently reclassified as optional external verification | Required | **Fixed** — ran + recorded the deterministic `#mock` all-tabs smoke (the plan's gate), superseding §11's "optional" wording. |
| **P7a-A01** — no permanent protocol-coverage assertion for the contract SSOT | Recommended | **Fixed (applied — fits scope)** — added `test_dispatch_covers_contract` (dispatch table + terminal set parity vs `contract.Msg`/`contract.TERMINAL`). |

### P7a-B01 — root cause + fix (the central change)

Codex is correct. The shipped guard `kind in TERMINAL and not owns(_TERMINAL_TASK[kind])` cannot tell a
**stale** terminal from a finished claim apart from a **live successor** when the successor shares the
kind's gate-owner: `_TERMINAL_TASK[error]=_TERMINAL_TASK[cancelled]=None` → `owns(None)` = "any task
running" (so a stale generic terminal is accepted while *any* successor runs), and
`_TERMINAL_TASK[matrix_done]="matrix"` → `owns("matrix")` is True for a successor matrix job (so a stale
`matrix_done` clears it). Both reach `_end_task`→`release()` and clobber the successor. The §10 "deviation"
that called the matrix→matrix straggler "unreachable" was wrong — it is exactly the duplicate/late class the
guard exists to defend against, and Codex reproduced it independently.

The kind-guard is **replaced by a per-claim epoch** — the "task-instance identity" Codex's correction asked
for, applied uniformly to every terminal:

1. **`TaskCoordinator` owns a monotonic `_epoch`**, bumped by *every* claim path: `try_claim`, `take_next`,
   and a new `claim_direct`. (`claim_direct` is for the four endpoints — `start_login` /
   `verify_environment` / `check_environments` / `_start_chromium` — that claimed by direct
   `self._task = …` assignment under the lock, bypassing `try_claim`; they now call `claim_direct`, which
   sets the task **and** bumps the epoch inside the same critical section via the shared RLock, so their
   lock granularity and ordering are unchanged.)
2. **`current_epoch()` + `is_live(epoch)`** replace `owns`. A terminal is live iff a task holds the gate
   **and** its tagged epoch equals the live claim's. `epoch=None` (an untagged terminal — only a
   direct/legacy `_handle` caller; production workers always tag) is treated as the current claim's, so
   2-arg `_handle` callers are byte-identical to the old `owns()` behavior (claimed→process, idle→drop).
3. **`_StampedQueue`** wraps the worker→GUI queue: a TERMINAL message becomes a 3-tuple
   `(kind, payload, epoch)` carrying the claim's epoch; non-terminals pass through unchanged.
   `GuiApi._gated_queue()` builds one at the held claim's epoch, and **all 17 gate-owning worker-start
   sites** now use it instead of the raw `self._q` (the 5 ungated workers — `ActiveEnvCheck`, `Check`,
   `Update`×3 — keep the raw queue; they post no terminals).
4. **`_worker_pump`** reads the optional epoch off the tuple; **`_handle(kind, payload, epoch=None)`** drops
   a terminal when `not is_live(epoch)` (logging kind + epoch + live gate).
5. Removed the now-subsumed `_TERMINAL_TASK` map and `TaskCoordinator.owns` (no remaining references).

Only behavior change: a **stale** terminal (epoch ≠ live claim) is dropped. Every real first/only terminal's
epoch matches the live claim → honored exactly as before (same handler, same emit order, same gate release +
queue advance). The matrix auto-advance is fully correct: job#1's terminal frees the gate, `take_next`
claims job#2 with a fresh epoch, and job#1's stale duplicate is then dropped.

### P7a-R01 — `#mock` run, recorded

Served `scripts/ui` (the existing `.claude/launch.json` `ui-mock` config; `python -m http.server 8765`)
and loaded `/index.html#mock`. Verified: the global mock state `S` is present; all four main tabs
(Export, Consolidate, Compare, Everything) switch; the Everything sub-tabs (Refresh & export / Comparison
matrix) and the matrix grid render; **zero console logs at any level** across the full click-through;
screenshot captured. P7a touches no frontend file (`ui/app.js` / `app.css` / `index.html` are byte-identical
to baseline), so this confirms the unchanged UI still renders across every tab; the backend exactly-once fix
itself is exercised by CT-10 + the bridge checks (the `#mock`'s stubbed bridge does not call the real
coordinator). This recorded run supersedes §11's "recommended external verification / not part of the
offline DoD" wording for `#mock`.

### P7a-A01 — permanent contract-coverage assertion

Added `test_dispatch_covers_contract` to CT-10: asserts `GuiApi._dispatch` covers **exactly** the declared
`contract.Msg` vocabulary (no missing/extra handler) and that every `contract.TERMINAL` kind is both a
declared message and dispatchable — a standing drift tripwire for the new SSOT. (Codex's suggested
`_TERMINAL_TASK.keys() == contract.TERMINAL` assertion is moot now that `_TERMINAL_TASK` is removed; the
epoch guard needs no per-kind owner map, so the parity check targets the dispatch table + terminal set.)

### Remediation changes (files)

- **`scripts/task_coordinator.py`** — `_epoch` field; epoch bump in `try_claim`/`take_next`; new
  `claim_direct` / `current_epoch` / `is_live`; removed `owns`; docstring updated to the epoch model.
- **`scripts/gui_api.py`** — new `_StampedQueue` (replacing the `_TERMINAL_TASK` map) + `_gated_queue`;
  `_worker_pump` epoch extraction; `_handle(…, epoch=None)` epoch guard; the 4 direct-claim endpoints →
  `claim_direct`; the 17 gated worker-start sites → `_gated_queue()`.
- **`build/check_worker_lifecycle.py`** — header updated to the epoch model; `test_duplicate_late_active_successor`
  rewritten (export's real terminal → successor → duplicate `export_done` + generic `error` + generic
  `cancelled` stragglers, none clobber); new `test_duplicate_late_same_kind_matrix` (Codex's matrix→matrix
  repro), `test_stamped_queue_tags_terminals`, `test_coordinator_epoch_is_live`, `test_dispatch_covers_contract`.

No new files; `scripts/gui_worker.py` and `build/app.spec` unchanged from the original P7a handoff. The diff
scope is the same 6 files; `docs/planning/` stays untracked.

### Updated verification

- **CT-10 GREEN** (11 test groups). **RED-proven:** with `is_live` reverted to ignore the epoch, exactly the
  active-successor (2), same-kind-matrix (1), and coordinator-staleness (3) assertions fail — 6 checks — and
  pass once restored. (No `REVERT-PROOF` marker remains.)
- **Behavior-neutral:** `check_gui_bridge` / `check_matrix_bridge` / `check_day_matrix` / `check_b3_batch` /
  `check_intersection_gate` / `check_batch_outcome` (drives the real `_handle` lifecycle) all GREEN.
- **Full blocking suite (CI-style, `set -e`, `PYTHONIOENCODING=utf-8`):** all **62** `build/check_*.py` +
  the 2 Node frontend checks + `node --check app.js` + byte-compile (`scripts build version.py`) — GREEN.
  `check_app_modules` / `check_import_direction` / `check_no_misspelling` GREEN; `git diff --check` clean.

### Changed measurements (vs §9)

| Metric | Original P7a | After remediation |
|---|---|---|
| Exactly-once mechanism | kind-guard (`owns` + `_TERMINAL_TASK`) | per-claim **epoch** (`is_live` + `_StampedQueue` tagging) |
| Stale wildcard `error`/`cancelled` w/ active successor | **clobbers** (B01) | dropped (no-op) |
| Stale same-kind `matrix_done` w/ active matrix successor | **clobbers** (B01) | dropped (no-op) |
| `_handle` signature | `(kind, payload)` | `(kind, payload, epoch=None)` |
| Coordinator gate API | `try_claim`/`release`/`owns`/`take_next` | `try_claim`/`claim_direct`/`release`/`current_epoch`/`is_live`/`take_next` (`owns` removed) |
| Gated worker-start sites routed through `_gated_queue()` | 0 | 17 |
| CT-10 test groups | 7 | 11 |
| `#mock` all-tabs smoke | not run (demoted to optional) | run + recorded, 0 console logs |
| §10 "deviation" (kind-guarded, matrix→matrix unreachable) | open | **resolved** (epoch closes it) |
