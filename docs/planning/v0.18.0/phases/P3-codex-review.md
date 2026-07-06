# Review round 1

## 1. Verdict: `BLOCKED`

P3 establishes the intended four-tier key taxonomy and removes most persisted and bridge-level
index coupling. It is not ready for approval because manifest validation implements
drop-and-continue semantics instead of the approved explicit rejection contract, the new
empty-resolution path emits two terminal events, and one stale frontend index lookup routes every
folder comparison through the file-comparison path.

## 2. Blocking findings

### P3-B01 — Invalid and duplicate manifest selections are dropped, allowing a narrower batch to false-complete

- **Severity:** blocking
- **Affected area:** approved manifest v1/v2 migration and resume safety;
  `scripts/batch_manifest.py`, `_migrate_v1_reports`, `_normalize_reports`, `build`, and `load`;
  `scripts/reports.py`, `resolve_export_keys`; `scripts/gui_worker.py`, `BatchWorker._specs`;
  `scripts/gui_api.py`, `start_export` and `start_batch_export`; and
  `build/check_stable_ids.py`.
- **Repository evidence:** The approved P3 contract in `05-claude-final-plan.md` §C.5 and P3 says
  unknown, duplicate, disabled, and removed keys are rejected with a logged error and user banner,
  not silently dropped; CT-9 requires invalid/removed v1 selections to be explicitly rejected with
  no environment marked done. The implementation does the opposite:
  - `_migrate_v1_reports` coerces every entry with `int(i)` and drops invalid/out-of-range entries
    (`scripts/batch_manifest.py:35-50`). Thus values such as `True`, `1.9`, and `"3"` are accepted
    as legacy integer indices rather than rejected.
  - `_normalize_reports` silently removes non-string v2 entries and de-duplicates keys
    (`scripts/batch_manifest.py:53-66`); `build` also stringifies every caller value at line 77,
    masking malformed input.
  - `resolve_export_keys` returns valid specs plus a dropped list and continues
    (`scripts/reports.py:361-378`). `BatchWorker._specs` discards that dropped list
    (`scripts/gui_worker.py:521-527`), as do `GuiApi.start_export` and
    `GuiApi.start_batch_export` (`scripts/gui_api.py:1286-1290`, `1425-1431`).
  - The new assertions explicitly lock in de-duplication and dropping:
    `build/check_stable_ids.py:72-88`.
- **Independent reproduction:** v1 `[0, 99]` normalized to `["ramp_summary"]`; v1
  `[True, 1.9, "3"]` normalized to `["ramp_detail", "highway_log"]`; v2
  `["ramp_summary", "ramp_summary", 7]` normalized to `["ramp_summary"]`. More importantly, a
  pending manifest containing `["ramp_summary", "__removed__"]` ran only Ramp Summary, marked
  `ssor-prod` done, and emitted `batch_done` with `complete=True` and
  `completion="complete"`. The user would lose the pending resume for the removed selection.
- **Exact correction expected:** Make v1 and v2 validation fail-safe and all-or-nothing for a saved
  selection. V1 entries must be actual integer indices, not booleans or coercible floats/strings;
  every index must be in the frozen range and duplicates must be rejected. V2 entries must be
  strings, unique, and resolve to known enabled export keys. If any entry is malformed, duplicate,
  unknown, disabled, or removed, abort start/resume with a logged error and user-visible banner,
  preserve the pending manifest, and mark no environment done. Do not stringify malformed caller
  selections. Add regressions for mixed valid+invalid manifests, duplicates, disabled/removed keys,
  non-string v2 entries, and coercible-but-not-integer v1 entries.

### P3-B02 — The empty-resolution path emits two terminal events and violates CT-10

- **Severity:** blocking
- **Affected area:** worker lifecycle and task-state safety; `scripts/gui_worker.py`,
  `BatchWorker.run`; `scripts/gui_api.py`, `_handle`, `_on_error`, `_on_batch_done`, and
  `_end_task`; `build/check_stable_ids.py`; `build/check_worker_lifecycle.py`.
- **Repository evidence:** CT-10 defines that every gate-owning worker posts exactly one terminal
  event for an outcome (`build/check_worker_lifecycle.py:1-11`). The new branch at
  `scripts/gui_worker.py:563-575` posts both `("error", ...)` and `("batch_done", ...)`.
  `GuiApi._handle` sends each to a separate terminal handler
  (`scripts/gui_api.py:555-566`); both handlers ultimately end the task through
  `_end_task` (`scripts/gui_api.py:574-601`, `_on_error` at line 983 and `_on_batch_done` at
  line 1550). The already-characterized pre-P7a lifecycle gap means a late second terminal can
  clear an active successor. `build/check_stable_ids.py:162-177` incorrectly expects both events,
  while `check_worker_lifecycle.py` does not exercise this new invalid-manifest producer path.
- **Independent reproduction:** Running the real `BatchWorker.run` with an all-unknown manifest
  produced `["log", "error", "batch_done"]`; terminal classification returned
  `["error", "batch_done"]`.
- **Exact correction expected:** Emit exactly one terminal for invalid/empty manifest resolution,
  while still presenting the required user-visible error and leaving the manifest pending. Feed
  that real producer path through `GuiApi._handle` in CT-10 and assert one `_end_task`, gate release,
  and no corruption of an already-dispatched queued successor. Update `check_stable_ids.py` so it
  does not require a lifecycle violation.

### P3-B03 — `compareKind` still indexes `compare_reports` with a string key

- **Severity:** blocking
- **Affected area:** frontend/backend comparison contract migration;
  `scripts/ui/app.js`, `compareChoice`, `currentCompareRep`, `compareKind`,
  `renderCompareKind`, and `startCompare`.
- **Repository evidence:** `compareChoice()` now returns `dataset.key`
  (`scripts/ui/app.js:717-720`), and `currentCompareRep()` correctly finds the row by key
  (`:721-723`). However, `compareKind()` still performs array indexing with that string
  (`:2758-2760`). The lookup therefore returns `undefined` and defaults to `"files"` for every
  selection. `renderCompareKind` consequently shows file inputs for folder comparisons
  (`:2870-2887`), and `startCompare` calls `api.start_compare(...)` rather than
  `api.start_compare_env(...)` (`:2920-2930`). This contradicts the phase report's claim that all
  three selection tiers are key-driven end to end.
- **Independent reproduction:** For a row
  `{key: "cmp:ramp_summary:env", kind: "folders"}`, the exact array-by-key expression returned
  `undefined`, producing `"files"` while a key lookup returned `"folders"`.
- **Exact correction expected:** Resolve comparison metadata by key in `compareKind`, preferably
  through the existing `currentCompareRep()`. Add a deterministic frontend test that selects a
  folders-kind key and verifies folder controls plus `start_compare_env`, then selects a
  files-kind key and verifies file controls plus `start_compare`. A browser row-presence check is
  insufficient; the test must exercise routing.

## 3. Required fixes

No separate required findings. P3-B01 through P3-B03 must be corrected before approval.

## 4. Non-blocking recommendations

None.

## 5. Verification performed

- Confirmed P3 is `awaiting_review`, with baseline and current HEAD
  `ca3c2af8b546a247e8be6ecab1418f6851b2f4ce`; inspected the product diff while excluding
  `docs/planning/**`.
- Re-read the approved P3 contract, Claude's P3 report, and relevant P0/P2 lifecycle and batch
  review history.
- Independently passed:
  - `build/check_stable_ids.py`
  - `build/check_b3_batch.py`
  - `build/check_gui_bridge.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_batch_outcome.py`
  - `build/check_matrix_bridge.py`
  - `build/check_a2_compare_filter.py`
  - `build/check_intersection_gate.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_report_library.py`
  - `build/check_no_misspelling.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Ran disposable, process-local diagnostics proving mixed-invalid manifest false completion,
  coercive/dropping normalization, duplicate terminal delivery, and the stale frontend
  array-by-string lookup. No product file, shared runtime state, browser profile, build artifact,
  or live TSMIS resource was modified or accessed.
- Did not launch a GUI/browser, run PyInstaller/frozen tests, or replace shared build artifacts.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude may remediate P3, but must not approve/commit it or begin dependent P4 until
P3-B01 through P3-B03 are resolved and a subsequent review returns `PASS`.

# Review round 2

## 1. Verdict: `PASS WITH FIXES`

The round-1 remediation resolves P3-B01 through P3-B03. Invalid, duplicate, disabled, and removed
selections now reject the whole operation; invalid saved manifests remain pending and emit exactly
one terminal; and comparison kind/routing resolves by stable key. One narrow required cleanup
remains because several comments and canonical verification descriptions still document the
pre-P3 index contract.

## 2. Blocking findings

None.

### Prior blocking finding dispositions

- **P3-B01 — Resolved.** `batch_manifest._migrate_v1_reports` and `_normalize_reports` preserve
  entry count and poison malformed entries instead of coercing or dropping them;
  `reports.resolve_export_keys` reports duplicates and unknown/disabled keys as invalid; and
  `GuiApi.start_export`, `GuiApi.start_batch_export`, and `BatchWorker.run` reject the complete
  selection when any invalid entry exists. The original mixed
  `["ramp_summary", "__removed__"]` reproduction now leaves the environment pending, writes no
  narrower result, and emits only an error.
- **P3-B02 — Resolved.** `BatchWorker.run` emits one `error` terminal for an invalid/empty saved
  selection (`scripts/gui_worker.py:570-585`). The real producer path is covered by
  `build/check_worker_lifecycle.py:_batch_invalid` and its queued-successor test; independent
  replay confirmed no accompanying `batch_done`.
- **P3-B03 — Resolved.** `scripts/ui/app.js:compareKind` now reads
  `currentCompareRep().kind`, and `build/check_compare_routing.js` exercises both
  folders-to-`start_compare_env` and files-to-`start_compare` routing by key.

## 3. Required fixes

### P3-R01 — Index-based selection documentation remains in source comments and canonical test docs

- **Severity:** required
- **Affected area:** P3 contract documentation and future-maintainer guidance;
  `scripts/reports.py`, `scripts/ui/app.js`, `build/check_stable_ids.py`,
  `docs/reports.md`, and `docs/verification-and-testing.md`.
- **Repository evidence:**
  - `scripts/reports.py:180` still says comparison selection is by index.
  - `scripts/reports.py:269-284` describes `idx` as a stable caller contract used by manifests,
    env-scan, and `start_export`, and says disabled reports are rejected by index. P3 instead makes
    keys the GUI/persistence contract; these indices are current-order/internal metadata only.
  - `scripts/ui/app.js:3725-3728` says consolidate radios index into `CONS_REPORTS`, and
    `:4286-4289` says compare radio correctness depends on registry order. Both mock paths now use
    `consByKey` / stable comparison keys.
  - `build/check_stable_ids.py:7-9` says migrated v1 report entries are de-duplicated, while the
    corrected contract deliberately preserves duplicates so resolution rejects the whole set.
  - `docs/reports.md:88-91` still says disabled indices are rejected and that the GUI/manifests
    pass stable `idx` values.
  - `docs/verification-and-testing.md:65` still describes
    `check_intersection_gate.py` as testing disabled-index rejection and stable GUI indices.
- **Exact correction expected:** Update only these P3-invalidated statements. Describe stable
  export/consolidation/comparison keys as the selection and persisted contract; describe `idx` as
  display/current-order or internal compatibility metadata where it remains; say disabled keys
  are rejected server-side; state that malformed and duplicate manifest entries are retained for
  all-or-nothing rejection rather than de-duplicated. Do not broaden this into the P11
  documentation reconciliation or rewrite unrelated historical material.

## 4. Non-blocking recommendations

None.

## 5. Verification performed

- Confirmed P3 remains `awaiting_review`; baseline and current HEAD are
  `ca3c2af8b546a247e8be6ecab1418f6851b2f4ce`. Reviewed the complete product diff from that
  baseline while excluding `docs/planning/**`.
- Re-read the approved P3 contract, Claude's report plus round-1 remediation, and review round 1.
- Independently passed:
  - `build/check_stable_ids.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_b3_batch.py`
  - `build/check_gui_bridge.py`
  - `build/check_batch_outcome.py`
  - `build/check_a2_compare_filter.py`
  - `build/check_intersection_gate.py`
  - `build/check_matrix_bridge.py`
  - `build/check_report_library.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_no_misspelling.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `node build/check_compare_routing.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Independently reproduced the round-1 mixed-valid/removed, duplicate, and poison-manifest cases:
  each retained pending status and emitted `["log", "error"]` with one terminal. A fresh
  mixed-invalid `start_batch_export` wrote no manifest, launched no worker, and left the task gate
  free.
- Verified a valid synthetic v1 manifest remains version 1 on disk after `load`, then rewrites to
  version 2 with stable keys on the next `mark_done`, as specified.
- Inspected CI wiring for both Node checks and the stable-ID/lifecycle checks. PyYAML is not
  installed, so no dependency was added and no separate YAML-library parse was performed.
- Did not launch a GUI/browser, access live TSMIS, run PyInstaller/frozen tests, or modify shared
  runtime/build artifacts.

## 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may apply the narrow P3-R01 wording corrections, but under the coordination
rule requiring a final `PASS`, must not approve/commit P3 or begin dependent P4 until a subsequent
review confirms the cleanup.

# Review round 3

## 1. Verdict: `PASS`

P3-R01 is resolved. The source comments, check description, and two canonical documentation
statements cited in round 2 now consistently describe stable keys as the selection/persistence
contract and `idx` as display/current-order metadata. The implementation satisfies the approved
stable-ID taxonomy, fail-safe manifest migration, bridge/frontend contract, lifecycle, packaging,
and protected-behavior boundaries.

## 2. Blocking findings

None.

### Prior blocking finding dispositions

- **P3-B01 — Resolved.** Manifest and fresh-selection validation remains all-or-nothing; invalid,
  duplicate, disabled, and removed entries cannot run a narrower batch or mark an environment
  done.
- **P3-B02 — Resolved.** Invalid/empty saved selections emit exactly one `error` terminal and
  retain the pending manifest.
- **P3-B03 — Resolved.** Comparison kind and execution routing resolve by stable comparison key;
  folders and files paths are independently exercised.

## 3. Required fixes

None.

### Prior required finding dispositions

- **P3-R01 — Resolved.** The eight cited statements in `scripts/reports.py`,
  `scripts/ui/app.js`, `build/check_stable_ids.py`, `docs/reports.md`, and
  `docs/verification-and-testing.md` now match the stable-key contract. A focused residual search
  found none of the stale index/de-duplication wording identified in round 2.

## 4. Non-blocking recommendations

None.

The planned work-PC resume of a real v0.17 paused batch remains external acceptance evidence and
is explicitly outside the offline P3 definition of done.

## 5. Verification performed

- Confirmed P3 remains `awaiting_review`; baseline and current HEAD are
  `ca3c2af8b546a247e8be6ecab1418f6851b2f4ce`. Reviewed the product diff from that baseline while
  excluding `docs/planning/**`.
- Re-read the approved P3 contract, Claude's report through round-2 remediation, and review
  rounds 1-2.
- Inspected all five P3-R01 files and confirmed the correction is wording-only and narrowly
  scoped.
- Independently passed:
  - `build/check_stable_ids.py`
  - `build/check_b3_batch.py`
  - `build/check_worker_lifecycle.py`
  - `build/check_batch_outcome.py`
  - `build/check_gui_bridge.py`
  - `build/check_a2_compare_filter.py`
  - `build/check_intersection_gate.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_no_misspelling.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_compare_routing.js`
  - `node build/check_mx_partial_render.js`
  - `git diff --check -- . ':(exclude)docs/planning/**'`
- Confirmed no `REVERT-PROOF` marker and no residual round-2 stale wording in the cited files.
- Did not launch a GUI/browser, access live TSMIS, run PyInstaller/frozen tests, or modify shared
  runtime/build artifacts.

## 6. Whether Claude may proceed toward phase approval

**Yes.** Claude may mark P3 approved and proceed toward the phase commit under the coordination
rules. It must not begin P4 in the same turn as the P3 commit.
