# Review round 1

## 1. Verdict

**BLOCKED**

P1 establishes useful outcome vocabulary and several correct producer fields, but four load-bearing completion paths still violate the approved contract. The new checks are green because they do not exercise those paths.

## 2. Blocking findings

### P1-B01 — Blocking — F4/O4 workbook-layout detection is ambiguous and returns incorrect counts

- **Affected plan area:** F4/O4; `scripts/matrix.py:read_counts`; CT-3/CT-14.
- **Repository evidence:** `read_counts` at `scripts/matrix.py:138-178` treats column A named `"Route"` as proof of the six-ID-column `has_route=True` layout. That is false for the flat `has_route=False` Ramp Summary and Intersection Summary cross-environment adapters: `compare_env.EnvCompare.compare_folders` uses `has_route=False`, while both `RS_HEADER` and `IS_HEADER` begin with `"Route"` (`scripts/compare_env.py:483-490,542-567`). Independent end-to-end reproduction with the existing real fixtures showed:
  - Ramp Summary: correct explicit-flat counts `(1 diff, 2 one-sided)`; automatic detection returned `(1, 1)`.
  - Intersection Summary: correct explicit-flat counts `(1, 0)`; automatic detection returned `(0, 1)`.
  `build/check_read_counts_layout.py` uses `"Category"` for its synthetic flat header, so it cannot catch this ambiguity. Existing aggregate comparator checks validate workbook contents but never call the matrix `read_counts` path.
- **Exact correction expected:** Derive the count columns from the actual invariant headers (`"Status"`, `"Diffs"`, and the fields after them), or carry unambiguous layout metadata from the adapter; do not infer shape from A1 alone. Add end-to-end matrix count assertions using the real Ramp Summary and Intersection Summary cross-environment outputs and the aggregate vs-TSN outputs. The planted diff/one-sided counts must survive through `build_cell_comparison`/`build_comparison` into the cache.

### P1-B02 — Blocking — Batch environments are still marked done after partial or no-data reports

- **Affected plan area:** downstream batch completion; `scripts/gui_worker.py:BatchWorker.run`; batch payload.
- **Repository evidence:** The approved contract says an environment is done only when every selected report is `complete` (`05-claude-final-plan.md:196`). `BatchWorker.run` calls `_run_specs(..., [])` and discards the results at `scripts/gui_worker.py:572`; absent an exception, it unconditionally sets the step to `"done"` and calls `batch_manifest.mark_done` at lines 592-594. A narrow reproduction returning one `completion=partial` report produced `status="done"`, called `mark_done`, and emitted `batch_done.complete=True`. Because the results are discarded, `_last_summary` also remains empty and `_end_task` cannot add the promised batch `completion`/`artifact` fields to `run_ended`.
- **Exact correction expected:** Retain each environment's results, require every selected report to be present and `completion == complete` before marking that environment done, and leave partial/no-data/failed environments pending with an explicit diagnostic. Carry an aggregate batch outcome into the terminal/backend payload. Add producer-path tests for complete, partial, no-data, cancelled, and exception outcomes, including manifest persistence and resume behavior.

### P1-B03 — Blocking — A fresh-staging `exists` anomaly is logged but still promoted

- **Affected plan area:** F1 store promotion; `scripts/gui_worker.py:ExportWorker._run_specs`; CT-1.
- **Repository evidence:** The approved table requires any `exists` result in a fresh staging directory to be rejected and logged (`05-claude-final-plan.md:192`). At `scripts/gui_worker.py:431-436` it is only logged. `outcome.run_completion` counts `exists` as successful presence, and lines 437-445 then promote the staging directory when that derived completion is `complete`. Independent reproduction with a fresh store result containing only `exists=["001"]` yielded `completion=complete`, `artifact=promoted`, and called `_swap_store_dir`.
- **Exact correction expected:** Preserve `exists` as valid for ordinary resume/non-store runs, but make any `in_store and result.exists` outcome non-promotable, discard staging, preserve live, and emit a structured failed/partial outcome plus the anomaly log. Add an integration characterization around `_run_specs` proving the swap is not called and last-good remains intact.

### P1-B04 — Blocking — Run-level reduction can present incomplete multi-report work as green complete

- **Affected plan area:** frontend/backend completion payload; `GuiApi._build_export_summary`; `app.js:renderCompletion`; CT-3/mock.
- **Repository evidence:** `_build_export_summary` correctly computes per-report completions at `scripts/gui_api.py:712-718`, but discards them when determining the run outcome and instead re-derives from summed counts at lines 719-730. A run with one `complete/promoted` report and one `no_data/previous_preserved` report therefore returns run-level `completion=complete`; the independent reproduction confirmed this exact result. `scripts/ui/app.js:939-941` renders that as green `"Export complete"` and does not append the kept-last-good warning because that note is only used in the non-complete branch. A multi-report exception has the same class of gap: `export_partial` builds a summary from only the reports that finished (`gui_api.py:489-498`) without recording that the selected run aborted before all reports completed.
- **Exact correction expected:** Add a run-level reducer over the producer-owned per-report completions plus terminal context/expected-report coverage. Only all-complete reports may yield run `complete`; mixed complete/no-data or incomplete report coverage must be non-green, and an aborted multi-report run must not derive completion solely from finished reports. Add backend and mock/renderer cases for complete+no_data, complete+partial, cancellation before later reports, and exception after an earlier report completed.

## 3. Required fixes

### P1-R01 — Required — Partial consolidation is allowed to compare but its partial flag is discarded

- **Affected plan area:** consolidation consumer contract; matrix result/cache; CT-2.
- **Repository evidence:** The approved contract requires `partial` consolidation to compare **but remain flagged**, while failed/no-data must leave stale prior state (`05-claude-final-plan.md:200-204`). In `scripts/matrix.py:816-841`, `cres` is consulted only to reject non-comparable states; when it is partial, the comparison result is returned without carrying that completion. `build_comparison` then records only verdict/counts at lines 910-918, and both cache writers (`record_result` at lines 125-132 and `record_tsn_result` at 419-425) have no completion field. A partial consolidation can therefore become a normal fresh matrix cell with no durable indication that inputs were omitted. `build/check_consolidate_outcome.py:82-89` only proves `_consolidate_store_folder` returns an object; it does not exercise failed/no-data stale-prior behavior, comparator suppression, cache preservation, or partial propagation despite CT-2's approved definition.
- **Exact correction expected:** Propagate upstream partial completion/counts through the comparison result and cache/snapshot so the matrix can flag it persistently. Expand CT-2 to seed an existing comparison/cache, prove failed/no-data/cancelled consolidation does not invoke the comparator or overwrite stale prior state, and prove partial invokes comparison while retaining a partial flag.

The blocking corrections must also add regression tests that fail on the current implementation; pure helper tests are insufficient for these orchestration defects.

## 4. Non-blocking recommendations

None beyond P1-R01.

## 5. Verification performed

- Confirmed P1 is `awaiting_review` with baseline `65aef98`; workspace `HEAD` remains that baseline.
- Inspected the complete P1 product diff, including seven untracked P1 product files and excluding `docs/planning/`.
- Read the approved P1 contract, P1 Claude report, and relevant P0/PA review history.
- Ran CT-1, CT-2, CT-3, and CT-14: all pass.
- Ran the relevant existing batch, worker lifecycle, matrix, matrix-TSN, day-matrix, Ramp Summary, Intersection Summary, aggregate-vs-TSN, packaging-reachability, and import-direction checks: all pass.
- Ran `node --check scripts/ui/app.js`: pass.
- Ran product `git diff --check`: pass.
- Independently reproduced P1-B01 through the real aggregate comparator outputs and P1-B02/B03/B04 through isolated in-memory/temp-directory worker/API diagnostics.
- Verified `compare_core`, updater, auth, settings, manifests, and output filenames are outside the P1 product diff.
- Did not run the complete 54-check suite, a browser/GUI launch, PyInstaller, or frozen-app checks.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude may remediate P1-B01 through P1-B04 and P1-R01, then return P1 for review round 2. Subsequent phases must not begin.
## Review round 2

### 1. Verdict

**BLOCKED**

The remediation resolves P1-B01 and P1-B04, and fixes the central manifest/promotion failures behind P1-B02 and P1-B03. However, two reproducible terminal-path defects remain: failed consecutive batch runs can publish the previous run's outcome, and partial store refreshes still auto-consolidate preserved stale live data as though it belonged to the current run. P1-R01 also remains incomplete for reused and self-comparison paths.

### 2. Blocking findings

#### P1-B02 — Blocking — Batch terminal outcome can leak from a previous run

- **Affected area:** Phase P1 batch outcome normalization; `scripts/gui_api.py`, `GuiApi.start_batch_export`, `GuiApi.resume_batch`, `GuiApi._on_batch_done`, `GuiApi._on_error`, and `GuiApi._end_task`.
- **Repository evidence:** `_last_batch_outcome` is initialized at `scripts/gui_api.py:187`, consumed by `_end_task` at `scripts/gui_api.py:592-594`, and assigned by `_on_batch_done` at `scripts/gui_api.py:1547`. Neither the new-run initialization in `start_batch_export` at `scripts/gui_api.py:1425-1429` nor the resume initialization at `scripts/gui_api.py:1488-1492` clears it. `BatchWorker` authentication/browser failures can emit `error` without first emitting `batch_done`; `_on_error` then reaches `_end_task` at `scripts/gui_api.py:973-1005`. A minimal independent lifecycle reproduction produced `STALE_BATCH_RUN_ENDED={'t':'run_ended','completion':'complete','artifact':'promoted'}` for a failed second run after a successful first run.
- **Why this remains blocking:** The manifest-side completion accounting is corrected, but the GUI/backend terminal contract can still report a failed current run as complete and promoted. That violates P1's required normalized outcome semantics and can mislead frontend state and diagnostics.
- **Exact correction expected:** Clear `_last_batch_outcome` when starting or resuming every batch operation, and assign a current-run failed/partial/cancelled outcome on every batch terminal path, including `_on_error`. Add a consecutive-run characterization test covering previous success followed by authentication or worker exception, and assert the second `run_ended` payload cannot reuse the first outcome.

#### P1-B03 — Blocking — Partial store refresh still consolidates preserved stale live data

- **Affected area:** Phase P1 staging/promotion orchestration; `scripts/gui_worker.py`, `ExportWorker._run_specs` and `ExportWorker._auto_consolidate`.
- **Repository evidence:** The remediation correctly converts a fresh staging `exists` result to failure and prevents promotion. However, `_run_specs` still invokes `_auto_consolidate` at `scripts/gui_worker.py:452` whenever auto-consolidation is enabled and the worker is not cancelled, without gating on normalized completion or artifact disposition. `_auto_consolidate` reads from the live store path `self.out_base / spec.subdir` at `scripts/gui_worker.py:300-308`. For a partial store refresh whose stage is discarded and whose prior live store is preserved, an independent reproduction returned `PARTIAL_STORE_RESULT=('partial','previous_preserved')` while still recording `PARTIAL_STORE_AUTO_CONSOLIDATE_CALLS=[('partial','previous_preserved')]`.
- **Why this remains blocking:** The source store is now protected, but the run can still regenerate or timestamp a derived consolidated artifact from the old live store and present that work as part of the failed/partial refresh. This breaks artifact provenance and can make stale data appear newly produced.
- **Exact correction expected:** For store-backed runs, invoke automatic consolidation only when the refresh outcome is `completion=complete` and `artifact=promoted`. Preserve intentionally supported non-store partial consolidation behavior separately rather than applying a global gate. Add an integration-level test proving that a partial store refresh does not invoke auto-consolidation and that a complete promoted refresh does.

### 3. Required fixes

#### P1-R01 — Required — Partial consolidation state is not durable across reuse or self-comparison

- **Affected area:** Phase P1 matrix/comparison outcome propagation; `scripts/matrix.py`, `_ensure_consolidated`, comparison orchestration/cache construction, and `scripts/gui/app.js`, `mxCellContent`.
- **Repository evidence:** Immediate TSN partial propagation is now retained when a consolidation result exists in the same call (`scripts/matrix.py:839-870`). On a later reuse of that persistent consolidated workbook, `_consolidated_stale` can be false and no new consolidation result exists; the comparison result then has no partial completion, while cache construction defaults missing completion to complete at `scripts/matrix.py:947-949`. Independent reproduction observed first-build completion `partial` and reused completion `None`. Self-comparison invokes `_ensure_consolidated` for each side at `scripts/matrix.py:923-927`, but `_ensure_consolidated` returns only a `Path` at `scripts/matrix.py:874-885`, discarding producer completion. Finally, `mxCellContent` at `scripts/gui/app.js:1883-1908` does not inspect `cmp.completion`, so a partial comparison can still render the green `✓ match` branch at line 1905. The added CT-2 checks immediate TSN propagation and cache round-trip, but not persistent reuse, self-comparison, or renderer behavior.
- **Exact correction expected:** Persist or otherwise robustly recover producer-owned consolidation completion alongside the persistent consolidated artifact; propagate and reduce completion from both sides of self-comparison; retain partial status when an existing artifact is reused; and make the frontend visibly distinguish partial comparison inputs from a fully valid match. Add characterization tests for persistent reuse, self-comparison with one partial side, snapshot serialization, and renderer behavior.

#### Prior blocking-finding dispositions

- **P1-B01 — Resolved.** `scripts/matrix.py:read_counts` now locates exact `Status` and `Diffs` headers and scans the intended count region. The real Ramp Summary fixture independently returned `(1, 2)`, and the expanded CT-2 checks passed.
- **P1-B04 — Resolved.** The shared completion reducer and aborted-path handling now prevent aggregate complete status when children are `no_data`, partial, failed, or aborted. Expanded CT-1/CT-3 checks passed independently.

### 4. Non-blocking recommendations

None beyond the still-required P1-R01 correction above. Further architecture expansion should wait until the remaining phase contracts are correct and characterized.

### 5. Verification performed

- Read the current coordination record, approved final plan, P1 Claude report and remediation addendum, and prior P1 review round.
- Inspected the workspace and product diff from baseline `65aef985f5ba18c8cd77097dc8a9c7f030b99655`, excluding planning-directory changes from product-scope evaluation.
- Ran the safe targeted checks for CT-1, CT-2, CT-3, CT-14, batch outcomes, worker lifecycle, B3 batch behavior, matrix, matrix TSN, and day matrix; all reported pass.
- Ran JavaScript syntax checking, application-module checking, import-direction checking, and diff checking; all reported pass.
- Independently exercised the real Ramp Summary count fixture and confirmed `(1, 2)`.
- Independently reproduced stale `_last_batch_outcome` reuse on a failed consecutive run.
- Independently reproduced auto-consolidation after a partial store refresh that preserved the previous live artifact.
- Independently reproduced loss of partial consolidation completion on persistent reuse and confirmed self-comparison receives only a path from `_ensure_consolidated`.
- Did not run the complete check suite, destructive build, browser/GUI launch, PyInstaller, frozen self-tests, or mutate shared runtime artifacts.

### 6. Whether Claude may proceed toward phase approval

**No.** Claude should correct P1-B02 and P1-B03, complete P1-R01, add the specified regression coverage, and return P1 for another review round.

## Review round 3

### 1. Verdict

**BLOCKED**

The round-2 remediation resolves the previously reproduced stale batch-outcome leak and stale-store auto-consolidation path. The matrix-owned TSMIS consolidation path also now retains partial state through immediate comparison, reuse, self-comparison, cache serialization, and rendering. However, the approved producer/consumer migration remains incomplete for TSN consolidations, and the new persistence mechanism is bypassed by other writers of the same reusable TSMIS workbooks. Those paths can still turn an explicitly incomplete consolidation into a normal green comparison.

### 2. Blocking findings

#### P1-B05 — Blocking — TSN incomplete outcomes are neither produced consistently nor carried into comparisons

- **Affected approved area:** P1 outcome contract, `05-claude-final-plan.md` §C.1 lines 200-204; TSN consolidator producers, `scripts/tsn_library.py`, `scripts/matrix.py`, and both matrix caches/renderers.
- **Repository evidence:** Multiple TSN producers still emit a human-readable incomplete warning while leaving the new structured fields unset. `scripts/tsn_load_ramp_summary.py:63,92-99` detects missing categories and returns `status="ok"` without `completion` or `skipped_inputs`; `scripts/tsn_load_intersection_summary.py:58,84-90` does the same; `scripts/consolidate_tsn_highway_sequence.py:321-378` collects failed district PDFs, writes an `⚠ INCOMPLETE` summary, and returns no structured completion/counts. An independent producer-path diagnostic against `tsn_load_ramp_summary.build_into` returned `status=ok`, an `⚠ INCOMPLETE` warning, `completion=None`, and `skipped_inputs=0`.
- **Repository evidence:** Even a TSN builder that does set `completion=partial` loses it downstream. `tsn_library.build_consolidated` delegates and returns the result at `scripts/tsn_library.py:371-396`, but `tsn_library.resolve` later exposes only `kind/path/mtime` at `scripts/tsn_library.py:402-428`. The legacy matrix PDF path discards the consolidator result entirely at `scripts/matrix.py:753-765`. `matrix.build_comparison` receives only the TSN path and propagates completion solely from the TSMIS-side consolidation at `scripts/matrix.py:982-1017`. An independent resolve diagnostic confirmed the TSN source keys are only `kind`, `mtime`, and `path`, with no completion.
- **Why this blocks P1:** The approved contract explicitly names PDF/TSN producers and the TSN library as consumers. A partial TSN normalized workbook can currently be accepted as a normal source, compared, cached with `completion=complete`, and rendered green. This directly violates “partial work can never read as complete.”
- **Exact correction expected:** Set producer-owned completion and structured omitted/failed counts in every TSN builder that can emit incomplete output, including the three paths above. Persist the completion with generated TSN workbooks, carry it through `tsn_library.status/resolve` and the legacy destination-scoped TSN path, reduce TSMIS-side and TSN-side completion in `build_comparison`/`build_day_cell`, and retain the reduced completion in caches and the existing partial renderer. Add producer tests for each incomplete TSN builder plus an end-to-end TSN-library build → resolve/reuse → Everything matrix and by-day matrix test proving the cell remains partial.

### 3. Required fixes

#### P1-R01 — Required — Consolidation outcome persistence is bypassed by other writers and is not fail-safe

- **Affected area:** P1 partial-consolidation durability; `scripts/matrix.py`, `ExportWorker._auto_consolidate`, `ConsolidateWorker.run`, and persistent consolidated-workbook ownership.
- **Repository evidence:** The new sidecar is written only by `matrix._consolidate_store_folder` at `scripts/matrix.py:715-750`; repository search found no other product call to `_write_consolidation_meta`. The same reusable consolidated workbooks can also be written directly by `ExportWorker._auto_consolidate` at `scripts/gui_worker.py:282-320` and `ConsolidateWorker.run` at `scripts/gui_worker.py:634-661`, including the GUI Consolidate tab launched at `scripts/gui_api.py:2879-2902`. Those paths can return `completion=partial` but do not update the sidecar. An independent lifecycle diagnostic produced a partial workbook through the real `ConsolidateWorker`, confirmed no `.outcome.json` existed, then reused it through `consolidate_and_compare_tsn`; the comparison completion was `None`.
- **Repository evidence:** `_write_consolidation_meta` writes directly to the final JSON path and treats persistence as best-effort at `scripts/matrix.py:838-851`. A crash/write failure can therefore leave a valid partial workbook with missing or truncated metadata, after which reuse defaults to complete. `_read_consolidation_completion` also converts `built_at_mtime` outside its parse-error guard at `scripts/matrix.py:854-868`; a syntactically valid malformed sidecar raised `ValueError` in an independent diagnostic instead of degrading safely.
- **Exact correction expected:** Put outcome persistence at the shared persistent-workbook write boundary so matrix builds, auto-consolidation, the GUI/console Consolidate path, and TSN-library builds cannot bypass it. Write metadata atomically, validate its schema/vocabulary/types on read, and ensure a current-version partial workbook is never reused as complete when metadata persistence fails or is corrupt. Preserve deliberate compatibility for legacy workbooks with no metadata. Add tests for direct auto/GUI consolidation followed by matrix reuse, write failure/truncation/malformed metadata, and a current-version partial artifact whose metadata cannot be recovered.

#### P1-B02 — Required (narrowed) — A partially successful batch followed by authentication failure is reported as wholly failed

- **Affected area:** Batch aggregate terminal contract; `BatchWorker.run`, `GuiApi._end_task`, and the consecutive-run test.
- **Repository evidence:** The stale prior-run value is now correctly cleared in `start_batch_export` and `resume_batch`, and a wholly failed new run no longer reuses prior success. But `BatchWorker.run` can mark earlier environments done at `scripts/gui_worker.py:613-616`, then encounter an auth/browser failure in a later environment and return at lines 587-595 before emitting `batch_done` at lines 623-629. `_last_batch_outcome` therefore remains `None`, and `_end_task` unconditionally maps that error path to `failed/previous_preserved` at `scripts/gui_api.py:592-601`. An independent terminal diagnostic for “one environment completed, then browser/auth failure” produced `{'completion': 'failed', 'artifact': 'previous_preserved'}` rather than `partial`.
- **Exact correction expected:** Preserve current-run batch progress on every terminal path and reduce it to `partial` when at least one environment completed before an auth/browser failure; reserve `failed` for a run that produced no completed environment. Add a two-environment producer/lifecycle test: first complete and persisted, second auth/worker exception, with a partial terminal payload and resumable second environment.

#### Prior finding dispositions

- **P1-B01 — Resolved.** Header-label count detection remains correct; CT-14 and matrix checks pass.
- **P1-B03 — Resolved.** Store auto-consolidation is now gated by `artifact == promoted`; targeted tests prove partial/rejected refreshes do not consolidate stale live data and complete refreshes do.
- **P1-B04 — Resolved.** The run-level reducer remains correctly characterized.
- **P1-R01 — Partially resolved.** Immediate matrix-owned partial propagation, matrix-owned reuse, self-comparison reduction, cache serialization, and `mx-partial` rendering all pass. The shared-writer and persisted-state cases above remain open.

### 4. Non-blocking recommendations

None. The remaining work is limited to completing the already-approved outcome contract and its characterization; no broader abstraction or phase expansion is warranted.

### 5. Verification performed

- Read the current coordination record, approved final plan, complete P1 report including both remediation addenda, and P1 review rounds 1-2.
- Inspected the workspace and product diff from baseline `65aef985f5ba18c8cd77097dc8a9c7f030b99655`, excluding planning-directory changes from product-scope evaluation. HEAD remains the baseline; the P1 product worktree contains the intended tracked changes plus the eight untracked P1 product/check modules.
- Ran `check_outcome_contract`, `check_read_counts_layout`, `check_export_summary_outcome`, `check_batch_outcome`, `check_consolidate_outcome`, and `check_mx_partial_render`; all passed.
- Ran `check_worker_lifecycle`, `check_b3_batch`, `check_matrix`, `check_matrix_tsn`, `check_day_matrix`, `check_app_modules`, and `check_import_direction`; all passed.
- Ran `node --check scripts/ui/app.js` and `git diff --check`; both passed.
- Independently confirmed a direct partial `ConsolidateWorker` write creates no outcome sidecar and is subsequently reused with `completion=None`.
- Independently confirmed malformed but valid JSON sidecar metadata can raise `ValueError`.
- Independently confirmed an incomplete TSN Ramp Summary producer returns `status=ok` with an incomplete warning but no structured completion/counts, and that `tsn_library.resolve` exposes no completion.
- Independently confirmed a batch with prior completed work followed by an error terminal is reported as wholly failed.
- Verified `compare_core`, updater, auth, settings, manifests, and output filenames remain outside the P1 product diff.
- Did not run a browser/GUI launch, destructive build, PyInstaller, frozen self-tests, live TSMIS access, or mutate shared runtime artifacts.

### 6. Whether Claude may proceed toward phase approval

**No.** Claude should close P1-B05, complete P1-R01 at the shared persistent-artifact boundary, correct the narrowed P1-B02 aggregate terminal case, add the specified regression coverage, and return P1 for another review round.

## Review round 4

### 1. Verdict

**BLOCKED**

No remediation for Review round 3 has been submitted. `P1-claude-report.md` still ends with the Review-round-2 remediation, the product diff from baseline `65aef985f5ba18c8cd77097dc8a9c7f030b99655` is unchanged, and all three Round-3 findings remain reproducible.

### 2. Blocking findings

#### P1-B05 — Blocking — TSN incomplete outcomes remain outside the structured contract

- **Affected area:** P1 producer/consumer outcome migration; TSN builders, `scripts/tsn_library.py`, `scripts/matrix.py`, and both matrix views.
- **Repository evidence:** `scripts/tsn_load_ramp_summary.py:63,92-99` and `scripts/tsn_load_intersection_summary.py:58,84-90` still detect missing categories and emit incomplete warning text while returning `ConsolidateResult(status="ok")` without `completion` or structured counts. `scripts/consolidate_tsn_highway_sequence.py:321-378` still records failed district PDFs only in `summary_lines`. `tsn_library.build_consolidated` still returns the builder result without persisting it at `scripts/tsn_library.py:371-396`, while `tsn_library.resolve` still exposes only path/kind/mtime at `scripts/tsn_library.py:402-428`. Repository search still finds no TSN-source completion propagation into `matrix.build_comparison`.
- **Independent reproduction:** An incomplete Ramp Summary TSN producer again returned `status="ok"`, `completion=None`, and `skipped_inputs=0`. The current targeted P1 checks remain green because they do not exercise this producer → TSN-library reuse → matrix path.
- **Exact correction expected:** Apply the Round-3 correction unchanged: set structured completion/counts in every incomplete-capable TSN producer, persist and recover the TSN artifact outcome, expose it through every generated-TSN source path, reduce both comparison sides, and add end-to-end Everything/by-day matrix regression tests.

### 3. Required fixes

#### P1-R01 — Required — Shared consolidated-workbook writers still bypass outcome persistence

- **Affected area:** Persistent TSMIS consolidation outcome ownership and sidecar robustness.
- **Repository evidence:** The only product call to `_write_consolidation_meta` remains `matrix._consolidate_store_folder` at `scripts/matrix.py:749`. `ExportWorker._auto_consolidate` (`scripts/gui_worker.py:282-320`) and `ConsolidateWorker.run` (`scripts/gui_worker.py:634-661`) still write/rewrite persistent consolidated workbooks without persisting their result. `_read_consolidation_completion` still performs unguarded numeric conversion at `scripts/matrix.py:865-866`.
- **Independent reproduction:** A partial workbook written through the real `ConsolidateWorker` again produced no sidecar and was reused with `completion=None`. A syntactically valid sidecar containing a non-numeric `built_at_mtime` again raised `ValueError`.
- **Exact correction expected:** Apply the Round-3 correction unchanged: move atomic, validated outcome persistence to a shared artifact-write boundary used by every persistent writer; distinguish deliberate legacy no-metadata compatibility from current-version metadata loss; and add direct-writer, write-failure, truncation, malformed-metadata, and reuse tests.

#### P1-B02 — Required (narrowed) — Partial batch progress is still collapsed to failed on fatal error

- **Affected area:** `BatchWorker.run` fatal terminal path and `GuiApi._end_task` batch aggregation.
- **Repository evidence:** `BatchWorker.run` still returns immediately after posting `error` for `AuthError`/`BrowserNotFoundError` at `scripts/gui_worker.py:587-595`, before the `batch_done` outcome at lines 623-629. `_end_task` still maps every missing batch outcome to `failed/previous_preserved` at `scripts/gui_api.py:592-601`, without consulting already persisted completed environments.
- **Independent reproduction:** The modeled terminal after one completed environment followed by a browser/auth error again emitted `{'completion': 'failed', 'artifact': 'previous_preserved'}` instead of `partial`.
- **Exact correction expected:** Apply the Round-3 correction unchanged: carry current-run done/total progress through fatal batch terminals, emit/reduce a partial outcome when any environment completed, reserve failed for zero completed work, and characterize a two-environment complete-then-fatal resume case.

#### Prior finding dispositions

- **P1-B01, P1-B03, and P1-B04 remain resolved.**
- **P1-R01 remains partially resolved only for matrix-owned writes/reuse, self-comparison, cache propagation, and rendering.**

### 4. Non-blocking recommendations

None. No broader design discussion is needed; the missing work is the previously specified contract completion and regression coverage.

### 5. Verification performed

- Confirmed P1 remains `awaiting_review` at baseline/HEAD `65aef985f5ba18c8cd77097dc8a9c7f030b99655`.
- Confirmed `P1-claude-report.md` contains only Review-round-1 and Review-round-2 remediation sections; no response to Review round 3 exists.
- Re-inspected the product diff excluding `docs/planning/`; its file set and diff statistics are unchanged from Review round 3.
- Re-ran `check_batch_outcome.py` and `check_consolidate_outcome.py`; both pass, confirming the already accepted fixes but not the open paths.
- Reproduced the incomplete TSN producer with no structured completion/counts.
- Reproduced direct partial `ConsolidateWorker` output with no sidecar and subsequent reuse with `completion=None`.
- Reproduced malformed sidecar metadata raising `ValueError`.
- Reproduced completed batch progress followed by a fatal terminal being reported as failed rather than partial.
- Ran `git diff --check`; pass.
- Did not run a browser/GUI launch, destructive build, complete suite, PyInstaller, frozen self-tests, live TSMIS access, or mutate shared runtime artifacts.

### 6. Whether Claude may proceed toward phase approval

**No.** P1-B05, P1-R01, and the narrowed P1-B02 remain open. Claude must implement and characterize the Round-3 corrections before requesting another review.

## Review round 5

### 1. Verdict

**BLOCKED**

The Round-3/4 remediation resolves the narrowed P1-B02 batch outcome defect and closes the main TSN-library and GUI/auto/matrix persistence paths. One P1-B05 consumer path still treats a failed TSN consolidation as successful, and P1-R01's claimed shared/fail-safe persistence boundary still bypasses the actual console entry point and fails open when metadata publication is blocked.

### 2. Blocking findings

#### P1-B05 — Blocking — Legacy matrix TSN-PDF consolidation still ignores a failed producer outcome

- **Affected area:** P1 TSN consumer contract; `scripts/matrix.py:consolidate_tsn_pdfs` and `scripts/gui_worker.py:MatrixTsnConsolidateWorker.run`.
- **Repository evidence:** `consolidate_tsn_pdfs` receives the producer's `ConsolidateResult` at `scripts/matrix.py:762-766`, writes metadata only when the shared helper accepts it, but returns `out_path` regardless of `res.status` or `res.completion`. `MatrixTsnConsolidateWorker.run` at `scripts/gui_worker.py:1913-1927` treats any non-exception return as success, logs `TSN workbook ready`, and emits `matrix_done` with `errors=0`.
- **Independent reproduction:** With an existing prior consolidated workbook and the real legacy consolidator seam returning `ConsolidateResult(status="error", message="parse failed")`, `matrix.consolidate_tsn_pdfs` returned the prior workbook path. Replaying the worker produced `TSN workbook ready: ...` and `matrix_done {done: 1, errors: 0}`. This violates §C.1's required failed/no-data behavior: keep stale prior but surface “not refreshed,” and do not present the failed operation as a successful build.
- **Exact correction expected:** Have `consolidate_tsn_pdfs` preserve and honor the producer result. A failed/no-data/cancelled result must not return a success-shaped path to the worker; the worker must report an unsuccessful/not-refreshed terminal while preserving the prior workbook. Partial may remain usable but must retain its structured flag. Add a regression test with a pre-existing prior workbook and an error result, asserting no “ready” success, `errors > 0` (or equivalent explicit failure), and the prior artifact remains unchanged.

### 3. Required fixes

#### P1-R01 — Required — Persistence is still bypassed by the console and fails open on publication errors

- **Affected area:** Shared consolidation metadata boundary; `scripts/cli.py:run_consolidate_cli` and `scripts/consolidation_meta.py:write_outcome/read_completion`.
- **Repository evidence:** The remediation claims every persistent writer, including the “GUI/console Consolidate” path, uses `consolidation_meta`. Repository call-site inspection shows writes only from matrix, TSN library, `ExportWorker._auto_consolidate`, and `ConsolidateWorker`; `run_consolidate_cli` at `scripts/cli.py:351-386` directly invokes the consolidator and never calls `write_outcome`. The `.bat`/standalone consolidator entry points use this function, so a partial dated consolidation can still be reused by the matrix with no sidecar.
- **Independent reproduction:** Running the real `run_consolidate_cli` wrapper with a temporary partial producer wrote the workbook but no sidecar; `read_completion` returned `None`, which callers default to complete.
- **Repository evidence:** `write_outcome` catches `OSError` and returns no status at `scripts/consolidation_meta.py:63-73`. If `os.replace` fails, it leaves the `.tmp`, publishes no final sidecar, and the later `read_completion` returns `None` as legacy/complete. `read_completion` also returns `None` for non-`FileNotFoundError` `OSError` at lines 89-91 even though its module contract says a present-but-unusable sidecar is conservative partial.
- **Independent reproduction:** Injecting `PermissionError` at `os.replace` for a partial workbook left the final sidecar absent, left the temporary sidecar behind, and made subsequent reuse return `None`.
- **Why this remains required:** Normal success, malformed JSON, wrong schema, GUI consolidation, auto-consolidation, matrix reuse, and TSN-library reuse are now correctly covered. The remaining paths still permit current-version partial work to become green solely because metadata could not be published or was written through the console.
- **Exact correction expected:** Route `run_consolidate_cli` through the shared persistence boundary. Make metadata publication failure observable and fail-safe: clean temporary files, do not let a current-version partial artifact become reusable as complete when publication fails, and treat an existing-but-unreadable sidecar conservatively rather than as absent legacy metadata. Add console-wrapper and injected write/read `OSError` tests that prove later reuse remains non-green.

#### Prior finding dispositions

- **P1-B02 — Resolved.** The real two-environment worker/API replay now reports partial after one completed environment followed by a fatal auth error, while leaving the second environment resumable.
- **P1-B01, P1-B03, and P1-B04 remain resolved.**
- **P1-R01 — Substantially resolved but still open for the console and persistence-failure cases above.**

### 4. Non-blocking recommendations

None. The remaining corrections are narrow contract-completion work; no additional abstraction is requested.

### 5. Verification performed

- Read the current coordination record, approved P1 plan, complete P1 report including the Round-3/4 remediation, and prior P1 review rounds.
- Inspected the complete product diff from baseline `65aef985f5ba18c8cd77097dc8a9c7f030b99655`, excluding planning-directory changes.
- Ran `check_tsn_outcome`, `check_consolidate_outcome`, and `check_batch_outcome`; all passed.
- Ran `check_matrix`, `check_matrix_tsn`, `check_day_matrix`, `check_app_modules`, `check_import_direction`, and `check_worker_lifecycle`; all passed.
- Ran JavaScript syntax checking, the matrix partial renderer check, and `git diff --check`; all passed.
- Independently reproduced the console consolidation sidecar bypass and subsequent `completion=None`.
- Independently reproduced metadata publication failure leaving a `.tmp`, no final sidecar, and subsequent `completion=None`.
- Independently reproduced the legacy TSN-PDF worker presenting a producer `status="error"` as `TSN workbook ready` with `errors=0`.
- Verified `compare_core`, updater, auth, settings, and manifests remain outside the P1 product diff.
- Did not run a browser/GUI launch, destructive build, complete check suite, PyInstaller, frozen self-tests, live TSMIS access, or mutate shared runtime artifacts.

### 6. Whether Claude may proceed toward phase approval

**No.** Claude should close the remaining P1-B05 legacy TSN consumer path and the narrowed P1-R01 console/publication-failure cases, add the specified regression coverage, and return P1 for another review round.

## Review round 6

### 1. Verdict

**PASS WITH FIXES**

P1-B05 is resolved, and the normal console/shared-writer persistence paths now work. One narrow P1-R01 failure path remains: `write_outcome` silently deletes a partial workbook when metadata publication fails but still lets CLI/GUI callers announce success; if Windows also refuses the workbook deletion, the workbook remains with no sidecar and is later treated as complete.

### 2. Blocking findings

None.

### 3. Required fixes

#### P1-R01 — Required — Metadata publication failure is not propagated and can still fail open

- **Affected area:** `scripts/consolidation_meta.py:write_outcome`, `scripts/cli.py:run_consolidate_cli`, `scripts/gui_worker.py:ConsolidateWorker.run` / `_auto_consolidate`, and other persistent-writer callers.
- **Repository evidence:** `write_outcome` catches publication `OSError`, removes the temporary sidecar, then best-effort unlinks a non-complete workbook at `scripts/consolidation_meta.py:68-86`. It returns no success/failure indication and suppresses workbook-unlink failure. All callers continue using the original `ConsolidateResult`; `run_consolidate_cli` prints its success summary at `scripts/cli.py:389-393`, and `ConsolidateWorker.run` emits `consolidate_done` with the original `status="ok"` at `scripts/gui_worker.py:661-670`.
- **Independent reproduction — misleading success:** With `os.replace` fault-injected to raise `PermissionError`, a partial CLI consolidation deleted its workbook but still printed the `Output file` success summary. The real `ConsolidateWorker` likewise deleted its workbook but emitted `consolidate_done` with `status="ok"`.
- **Independent reproduction — false green:** With sidecar publication blocked and the partial workbook also locked so `unlink` raised `PermissionError`, `write_outcome` left the workbook present, left no final or temporary sidecar, and `read_completion` returned `None`; matrix consumers therefore default it to complete. This is the exact Windows lock variant omitted by the new test.
- **Exact correction expected:** Make metadata-publication failure observable to every caller (return a result or raise a dedicated exception) so CLI/GUI/auto/TSN/matrix paths cannot announce success for a removed or untrusted workbook. Preserve a durable conservative state when the workbook cannot be removed—do not rely on best-effort unlink as the only false-green guard. Add fault-injection tests for: publication failure plus workbook-unlink failure, CLI terminal/exit behavior, GUI `ConsolidateWorker` terminal behavior, and subsequent matrix reuse. Assert no success terminal and no `completion=None`/green reuse.

#### Prior finding dispositions

- **P1-B05 — Resolved.** A failed legacy TSN-PDF producer now yields `matrix_done errors=1`, no “TSN workbook ready” log, and preserves the prior workbook.
- **P1-B01, P1-B02, P1-B03, and P1-B04 remain resolved.**
- **P1-R01 is otherwise resolved:** normal console, GUI, auto, matrix, and TSN-library writes persist outcomes; valid/corrupt/malformed/unreadable metadata is handled; reuse, self-comparison, caches, and renderer retain partial status.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Read the current coordination record, approved P1 plan, complete P1 Claude report including the Round-5 remediation, and prior P1 review rounds.
- Inspected the product diff from baseline `65aef985f5ba18c8cd77097dc8a9c7f030b99655`, excluding planning-directory changes.
- Ran `check_consolidate_outcome`, `check_tsn_outcome`, and `check_batch_outcome`; all passed.
- Ran `check_matrix`, `check_matrix_tsn`, `check_day_matrix`, `check_app_modules`, and `check_import_direction`; all passed.
- Ran JavaScript syntax checking, the matrix partial-renderer check, and `git diff --check`; all passed.
- Independently confirmed P1-B05's legacy TSN failure path now reports `errors=1`, emits no ready log, and preserves the prior workbook.
- Independently reproduced CLI success output after publication failure removed the workbook.
- Independently reproduced `ConsolidateWorker` emitting `consolidate_done/status=ok` after publication failure removed the workbook.
- Independently reproduced publication failure plus workbook-unlink failure leaving a sidecar-less partial workbook that reads `completion=None`.
- Verified `compare_core`, updater, auth, settings, and manifests remain outside the P1 product diff.
- Did not run a browser/GUI launch, destructive build, complete check suite, PyInstaller, frozen self-tests, live TSMIS access, or mutate shared runtime artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may implement the narrow P1-R01 correction, but P1 should return for review and receive `PASS` before phase approval or commit.

## Review round 7

### 1. Verdict

**PASS WITH FIXES**

The round-6 remediation correctly makes ordinary publication failure observable to the CLI, GUI
consolidation worker, auto-consolidation log, and legacy TSN worker. All targeted P1 checks remain green,
and the previously resolved P1-B01 through P1-B05 findings remain resolved. One narrow P1-R01 durability
gap remains: the new conservative fallback marker is itself best-effort, and the test does not exercise
its write failing at the same time as workbook deletion.

### 2. Blocking findings

None.

### 3. Required fixes

#### P1-R01 — Required — The fallback marker can fail with the locked workbook and still permit false-green reuse

- **Affected area:** `scripts/consolidation_meta.py`, `_mark_untrusted`, `write_outcome`, and
  `read_completion`; persistent-writer callers `scripts/matrix.py:_consolidate_store_folder` and
  `scripts/tsn_library.py:build_consolidated`; `build/check_consolidate_outcome.py` round-6 fault
  coverage.
- **Repository evidence:** `_mark_untrusted` at `scripts/consolidation_meta.py:59-74` is explicitly
  best-effort and logs that a later reuse can read complete if its direct write fails. On atomic
  publication failure, `write_outcome` deletes the already-written `.tmp`, calls `_mark_untrusted`
  without checking its return, then best-effort deletes the workbook at lines 108-120. If the final
  sidecar cannot be opened and the workbook is also locked, the function returns `False` but leaves a
  workbook with no sidecar; `read_completion` therefore returns `None` at lines 133-149, which matrix
  consumers interpret as legacy complete. The new regression at
  `build/check_consolidate_outcome.py:451-461` mocks `_silent_unlink` to fail but still permits
  `_mark_untrusted` to write the final sidecar, so it does not cover this remaining branch.
- **Independent reproduction:** Fault-injecting all three operations produced
  `{'write_return': False, 'workbook_exists': True, 'sidecar_exists': False, 'tmp_exists': False,
  'reuse_completion': None}`: atomic `os.replace` failed, opening the fallback sidecar failed, and
  workbook unlink failed. The current log itself reported that later reuse could read the workbook as
  complete.
- **Additional caller evidence:** `matrix._consolidate_store_folder` at `scripts/matrix.py:748` and
  `tsn_library.build_consolidated` at `scripts/tsn_library.py:401` call `write_outcome` but ignore its
  observable `False` result, contrary to the shared-boundary contract. Other announcing callers now
  correctly handle it.
- **Exact correction expected:** Ensure a non-complete workbook cannot be left with every durable
  conservative signal removed when publication, fallback-marker creation, and workbook deletion fail.
  For example, retain and validate a conservative temporary/untrusted sentinel when atomic promotion
  fails, or provide another independently readable marker; `read_completion` must return `partial`, not
  `None`, for that state. Honor `False` at every persistent writer, including
  `_consolidate_store_folder` and `tsn_library.build_consolidated`, so the current operation cannot claim
  a safely persisted artifact. Extend `check_consolidate_outcome` with the exact three-way failure and
  subsequent matrix reuse, and cover the two remaining ignored-return callers.

#### Prior finding dispositions

- **P1-B01, P1-B02, P1-B03, P1-B04, and P1-B05 remain resolved.**
- **P1-R01 remains otherwise resolved:** normal publication, ordinary publication failure, CLI and GUI
  terminals, auto-consolidation, TSN failure reporting, valid/corrupt/unreadable sidecars, comparison
  propagation, caches, and rendering behave as required.

### 4. Non-blocking recommendations

None. The remaining change should stay confined to the existing persistence boundary and its callers;
P1 does not need another abstraction or broader restructuring.

### 5. Verification performed

- Confirmed P1 remains `awaiting_review` at baseline/HEAD
  `65aef985f5ba18c8cd77097dc8a9c7f030b99655`.
- Read the approved P1 phase, the complete Claude report including round-6 remediation, and all prior P1
  review rounds.
- Inspected the product diff from the recorded baseline, excluding `docs/planning/`; verified
  `compare_core`, updater, auth, settings, and manifests remain outside the P1 product diff.
- Ran `check_consolidate_outcome`, `check_tsn_outcome`, and `check_batch_outcome`; all passed.
- Ran `check_matrix`, `check_matrix_tsn`, `check_day_matrix`, `check_app_modules`,
  `check_import_direction`, and `check_b2_autoconsolidate`; all passed.
- Ran JavaScript syntax checking, the matrix partial-renderer check, and product `git diff --check`; all
  passed.
- Independently reproduced atomic-publication failure plus fallback-marker write failure plus
  workbook-unlink failure leaving a sidecar-less workbook with `read_completion=None`.
- Did not run a browser/GUI launch, destructive build, complete check suite, PyInstaller, frozen
  self-tests, live TSMIS access, or mutate shared runtime artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may implement the narrow P1-R01 durability/caller correction, but P1 should return
for review and receive `PASS` before phase approval or commit.

## Review round 8

### 1. Verdict

**PASS WITH FIXES**

The round-7 remediation closes the exact atomic-`os.replace` + fallback-marker + workbook-unlink failure
reported in Review round 7, and the two formerly ignored persistent-writer returns are now honored. All
targeted checks pass and P1-B01 through P1-B05 remain resolved. P1-R01 still has one narrower write-stage
branch: if the temporary sidecar cannot be created or completed, there is no valid `.tmp` sentinel to
retain, so a simultaneously undeletable workbook can still be reused as complete.

### 2. Blocking findings

None.

### 3. Required fixes

#### P1-R01 — Required — Sidecar write-stage failure still leaves an undeletable partial workbook false-green

- **Affected area:** `scripts/consolidation_meta.py:write_outcome` and `read_completion`;
  `scripts/matrix.py:consolidate_and_compare_tsn`; round-7 fault coverage in
  `build/check_consolidate_outcome.py`.
- **Repository evidence:** `write_outcome` wraps both opening/writing the `.tmp` and `os.replace` in the
  same `except OSError` path at `scripts/consolidation_meta.py:109-132`. The new last-resort guarantee
  assumes lines 110-111 successfully produced a valid `.tmp`; however, an `OSError` from `open(tmp, "w")`
  or `json.dump` reaches the same fallback with no usable sentinel. If workbook unlink fails and
  `_mark_untrusted` cannot create the final sidecar, line 131 retains nothing. `read_completion` then sees
  neither final nor `.tmp` and returns `None` at lines 145-159, which matrix reuse defaults to complete.
- **Independent reproduction:** Denying writes to both sidecar paths while making workbook unlink fail
  produced `{'return': False, 'workbook': True, 'final': False, 'tmp': False, 'read': None}`. Replaying
  that workbook through the real `consolidate_and_compare_tsn` reuse path produced
  `{'published': False, 'meta_read': None, 'matrix_completion': None}`: the incomplete input again has no
  structured partial flag.
- **Coverage gap:** The round-7 regression at `build/check_consolidate_outcome.py:519-530` injects failure
  only at `os.replace`, after the valid `.tmp` has already been written. It therefore proves the retained
  sentinel path but not the earlier write-stage branch handled by the same exception block.
- **Exact correction expected:** Separate “valid temporary payload exists but atomic promotion failed”
  from “temporary payload was never durably written.” In the latter case, ensure an undeletable
  non-complete workbook cannot later resolve as legacy complete—persist a conservative signal through an
  independent durable location or make/quarantine the workbook so normal resolvers cannot select it.
  `read_completion` or the resolver boundary must return `partial`/untrusted, never `None`, after this
  failure. Add fault injection at `open(tmp)` and during `json.dump`, with workbook deletion and final
  marker creation also failing, then prove subsequent Everything/by-day matrix reuse stays non-green.
  Keep every caller's current `False` handling.

#### Prior finding dispositions

- **P1-B01, P1-B02, P1-B03, P1-B04, and P1-B05 remain resolved.**
- **The Review-round-7 exact scenario is resolved:** when a valid `.tmp` exists and atomic promotion,
  fallback-marker creation, and workbook deletion fail, the retained sentinel makes reuse partial.
- **P1-R01 remains otherwise resolved:** caller failure propagation, normal metadata publication,
  malformed/unreadable metadata, caches, self-comparison, TSN-library propagation, and frontend rendering
  behave as required.

### 4. Non-blocking recommendations

- **P1-A01 — Recommended — Validate retained `.tmp` metadata rather than treating file presence alone as
  partial.** `read_completion` at `scripts/consolidation_meta.py:149-159` does not parse or mtime-check the
  sentinel; any stale file named `<workbook>.outcome.json.tmp` forces `partial`, despite the module
  contract at lines 20-21 saying an mtime mismatch is ignored. Independently planting a valid but
  1,000-second-stale `.tmp` beside a newer workbook still returned `partial`. Validate the sentinel with
  the same schema/vocabulary/mtime rules as the final sidecar, degrading malformed or unreadable
  sentinels conservatively but ignoring a demonstrably stale sentinel. Also update `_mark_untrusted`'s
  stale “only residual false-green window” wording and log message now that the retained-sentinel fallback
  exists.

### 5. Verification performed

- Confirmed P1 remains `awaiting_review` at baseline/HEAD
  `65aef985f5ba18c8cd77097dc8a9c7f030b99655`.
- Read the approved P1 phase, the complete Claude report including round-7 remediation, and all prior P1
  review rounds.
- Inspected the product diff from the recorded baseline, excluding `docs/planning/`; verified
  `compare_core`, updater, auth, settings, manifests, requirements, and build script remain outside the P1
  product diff.
- Ran `check_consolidate_outcome`, `check_tsn_outcome`, and `check_batch_outcome`; all passed.
- Ran `check_matrix`, `check_matrix_tsn`, `check_day_matrix`, `check_app_modules`,
  `check_import_direction`, and `check_b2_autoconsolidate`; all passed.
- Ran JavaScript syntax checking, the matrix partial-renderer check, and product `git diff --check`; all
  passed.
- Independently confirmed the submitted valid-`.tmp` three-way failure now returns `partial`.
- Independently reproduced sidecar temporary-file creation failure plus fallback-marker failure plus
  workbook-unlink failure leaving no sentinel and `read_completion=None`, including through matrix reuse.
- Independently confirmed a stale `.tmp` sentinel is not mtime-validated and forces a conservative
  `partial`.
- Did not run a browser/GUI launch, destructive build, complete check suite, PyInstaller, frozen
  self-tests, live TSMIS access, or mutate shared build artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may implement the remaining narrow P1-R01 write-stage durability correction; P1
should return for review and receive `PASS` before phase approval or commit.

## Review round 9

### 1. Verdict

**PASS WITH FIXES**

The round-8 remediation correctly quarantines an unmarked partial workbook when no temporary sentinel
exists, and P1-A01's shared validator now ignores demonstrably stale sentinels. All targeted checks pass;
P1-B01 through P1-B05 remain resolved. One P1-R01 sentinel-integrity case remains: the fallback ladder
accepts a current valid `.tmp` whose recorded completion is `complete` as sufficient protection for the
current failed `partial` write. That bypasses quarantine and lets the partial workbook render green.

### 2. Blocking findings

None.

### 3. Required fixes

#### P1-R01 — Required — A pre-existing `complete` temp sentinel can certify a newly failed partial workbook

- **Affected area:** `scripts/consolidation_meta.py:write_outcome`, `_read_sidecar`, and
  `read_completion`; `scripts/matrix.py:consolidate_and_compare_tsn`; round-8 sentinel coverage in
  `build/check_consolidate_outcome.py`.
- **Repository evidence:** For a non-complete result, the failure ladder at
  `scripts/consolidation_meta.py:177-201` treats any `_read_sidecar(tmp, consolidated)` result other than
  `_ABSENT` or `None` as a usable conservative sentinel. That set includes `outcome.COMPLETE`, because
  `_read_sidecar` returns any valid current completion at lines 80-89. Line 194 therefore returns before
  `_quarantine` when a current `.tmp` says `complete`, even though the producer result being persisted is
  `partial`.
- **Independent reproduction:** A canonical workbook representing a new partial result was paired with
  pre-existing valid `.tmp` metadata containing `completion="complete"` and the workbook's current mtime.
  Fault-injecting sidecar writes, workbook deletion, and direct-marker creation made `write_outcome`
  return `False`, but the real quarantine was never attempted. The resulting state was
  `{'write_return': False, 'canonical_exists': True, 'quarantine_exists': False,
  'read_completion': 'complete', 'matrix_completion': None, 'verdict': 'match'}` through the real
  `consolidate_and_compare_tsn` reuse path.
- **Why this remains required:** The phase objective is that partial work can never read as complete. The
  observable `False` protects the current caller, but the persisted canonical workbook remains selectable
  after restart and is explicitly certified complete by unrelated temp debris.
- **Coverage gap:** `build/check_consolidate_outcome.py:611-629` validates only stale-partial and
  current-partial sentinels. The write-stage test at lines 573-609 starts without an existing `.tmp`, so it
  does not exercise a current but semantically incompatible sentinel.
- **Exact correction expected:** A retained sentinel may satisfy a failed non-complete write only when it
  conservatively represents that write—at minimum, its validated completion must be non-complete
  (`partial`), not `complete`. A valid current `complete` sentinel must be rejected as incompatible and
  the ladder must continue to quarantine (or another conservative durable state). Add a regression with
  pre-existing current `complete` temp metadata, failed temp/final writes, failed workbook deletion, and
  failed marker creation; assert the canonical workbook is quarantined or later resolves partial, and
  both Everything and by-day matrix consumers cannot produce a green match.

#### Prior finding dispositions

- **P1-B01, P1-B02, P1-B03, P1-B04, and P1-B05 remain resolved.**
- **Review-round-8 P1-R01 branch is resolved:** when no usable `.tmp` exists, the workbook is quarantined
  and the canonical resolver cannot select it.
- **P1-A01 is resolved:** final and temporary metadata share schema/type/mtime validation; a stale
  sentinel is ignored while a current partial sentinel remains conservative.
- **P1-R01 remains otherwise resolved:** callers honor publication failure, normal and corrupt metadata
  are safe, partial state propagates through caches/self-comparison/TSN paths, and frontend rendering is
  non-green.

### 4. Non-blocking recommendations

None. The correction should remain a predicate/test change inside the existing persistence boundary; no
new abstraction is warranted.

### 5. Verification performed

- Confirmed P1 remains `awaiting_review` at baseline/HEAD
  `65aef985f5ba18c8cd77097dc8a9c7f030b99655`.
- Read the approved P1 phase, the complete Claude report including round-8 remediation, and all prior P1
  review rounds.
- Inspected the product diff from the recorded baseline, excluding `docs/planning/`; verified
  `compare_core`, updater, auth, settings, manifests, requirements, and `build.ps1` remain outside P1.
- Ran `check_consolidate_outcome`, `check_tsn_outcome`, and `check_batch_outcome`; all passed.
- Ran `check_matrix`, `check_matrix_tsn`, `check_day_matrix`, `check_app_modules`,
  `check_import_direction`, and `check_b2_autoconsolidate`; all passed.
- Ran JavaScript syntax checking, the matrix partial-renderer check, targeted Python byte-compilation, and
  product `git diff --check`; all passed.
- Independently confirmed write-stage failure with no sentinel now quarantines the workbook and matrix
  reuse fails closed.
- Independently confirmed interrupted `json.dump` leaves a corrupt sentinel that reads conservative
  `partial`.
- Independently reproduced a current valid `complete` temp sentinel bypassing quarantine and yielding a
  match with `matrix_completion=None`.
- Did not run a browser/GUI launch, destructive build, complete check suite, PyInstaller, frozen
  self-tests, live TSMIS access, or mutate shared build artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may implement the narrow P1-R01 incompatible-sentinel correction; P1 should return
for review and receive `PASS` before phase approval or commit.

## Review round 10

### 1. Verdict

**PASS WITH FIXES**

The round-9 predicate correction works: a current `complete` `.tmp` no longer certifies a failed partial
write, and the regression now reaches quarantine. All targeted P1 checks pass, and P1-B01 through P1-B05
remain resolved. One P1-R01 ordering case remains: when a pre-existing final sidecar still reads
`complete` and the newly retained `.tmp` reads `partial`, `read_completion` returns the final value first.
The retained conservative sentinel is therefore ineffective and matrix reuse can still render green.

### 2. Blocking findings

None.

### 3. Required fixes

#### P1-R01 — Required — A locked final `complete` sidecar overrides the retained partial sentinel

- **Affected area:** `scripts/consolidation_meta.py:write_outcome` and `read_completion`;
  `scripts/matrix.py:consolidate_and_compare_tsn`; persistence fault coverage in
  `build/check_consolidate_outcome.py`.
- **Repository evidence:** On a failed partial publication, `write_outcome` accepts a validated partial
  `.tmp` at `scripts/consolidation_meta.py:196-197`. The old final sidecar can remain when `os.replace`
  fails and `_mark_untrusted` cannot overwrite it. `read_completion` at lines 219-224 always returns a
  non-absent final result before consulting the `.tmp`, even when the final says `complete` and the temp
  says `partial`. Because mtime matching uses a one-second tolerance, a prior final sidecar can still
  validate after a rapid overwrite or on a coarse-resolution filesystem.
- **Independent reproduction:** With a current valid final sidecar containing `complete`, a newly written
  partial `.tmp`, failed `os.replace`, failed workbook deletion, and failed marker overwrite,
  `write_outcome` returned `False` while both files remained. Direct reads produced
  `{'final_read': 'complete', 'tmp_read': 'partial', 'public_read': 'complete'}`.
- **Consumer impact:** Reusing that state through the real `consolidate_and_compare_tsn` path produced
  `{'write_return': False, 'read': 'complete', 'matrix_completion': None, 'verdict': 'match'}`. The
  current caller sees failure, but after restart the canonical workbook is selected and the cell is
  green-shaped.
- **Coverage gap:** The round-9 test plants only a `complete` `.tmp` with no final sidecar. Existing tests
  do not cover conflicting valid current final/temp metadata.
- **Exact correction expected:** Reconcile final and temporary sidecars conservatively. When both are
  present and current, a `partial`/untrusted value must dominate `complete`; alternatively invalidate or
  quarantine the stale final before accepting the retained partial sentinel. Add a regression with a
  final current `complete` plus temp current `partial` under failed replace/marker/unlink, and prove
  `read_completion` and both Everything/by-day matrix consumers remain partial or not-refreshed, never
  green.

#### Prior finding dispositions

- **P1-B01, P1-B02, P1-B03, P1-B04, and P1-B05 remain resolved.**
- **Review-round-9 P1-R01 branch is resolved:** an incompatible `complete` temp sentinel is rejected and
  falls through to quarantine.
- **P1-A01 remains resolved:** stale metadata is ignored and current metadata is schema/type/mtime
  validated.
- **P1-R01 remains otherwise resolved:** publication failures are observable, callers honor them,
  write-stage no-sentinel failures quarantine, compatible partial sentinels survive, and partial state
  propagates through caches, TSN paths, self-comparison, and rendering.

### 4. Non-blocking recommendations

None. This is a read-precedence/fault-test correction within the existing persistence boundary; no new
abstraction is needed.

### 5. Verification performed

- Confirmed P1 remains `awaiting_review` at baseline/HEAD
  `65aef985f5ba18c8cd77097dc8a9c7f030b99655`.
- Read the approved P1 phase, the complete Claude report including round-9 remediation, and all prior P1
  review rounds.
- Inspected the product diff from the recorded baseline, excluding `docs/planning/`; verified protected
  `compare_core`, updater, auth, settings, manifests, requirements, and `build.ps1` remain outside P1.
- Ran all targeted P1 contract checks: consolidation, TSN, batch, outcome reducer, export summary/cache
  envelope, and read-counts layout; all passed.
- Ran matrix, matrix-TSN, day-matrix, worker-lifecycle, application-module reachability,
  import-direction, and auto-consolidation checks; all passed.
- Ran JavaScript syntax checking, the matrix partial-renderer check, targeted Python byte-compilation, and
  product `git diff --check`; all passed.
- Independently confirmed the submitted incompatible-`complete`-temp scenario now quarantines and cannot
  compare green.
- Independently reproduced conflicting current final `complete` and temp `partial` metadata resolving to
  final `complete`, including a real matrix reuse yielding `verdict=match` with no completion flag.
- Did not run a browser/GUI launch, destructive build, complete check suite, PyInstaller, frozen
  self-tests, live TSMIS access, or mutate shared build artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may implement the narrow P1-R01 final/temp precedence correction; P1 should return
for review and receive `PASS` before phase approval or commit.

## Review round 11

### 1. Verdict

**PASS**

The round-10 remediation resolves the remaining P1-R01 final/temp precedence defect. Conflicting current
metadata now reconciles conservatively: a retained partial sentinel dominates a final complete record,
while a demonstrably stale partial sentinel does not override a current complete result. The full targeted
P1 contract and integration set is green, the approved phase boundaries are respected, and no blocking or
required finding remains open.

### 2. Blocking findings

None.

### 3. Required fixes

None.

#### Prior finding dispositions

- **P1-B01, P1-B02, P1-B03, P1-B04, and P1-B05 are resolved.**
- **P1-R01 is resolved.** Producer completion is durable across all persistent writers and reuse paths;
  publication failures are observable; failed partial metadata publication removes, marks, retains a
  compatible conservative sentinel, or quarantines the workbook; final/temp conflicts resolve
  conservatively; comparison caches and both matrix views retain partial state.
- **P1-A01 is resolved.** Final and temporary sidecars share schema, vocabulary, type, and mtime
  validation; demonstrably stale sentinels are ignored.

### 4. Non-blocking recommendations

None.

The already documented work-PC acceptance items remain outside the P1 definition of done, and the
duplicate-late worker-terminal gap remains characterized and assigned to P7a; neither prevents P1
approval.

### 5. Verification performed

- Confirmed P1 is `awaiting_review` at baseline/HEAD
  `65aef985f5ba18c8cd77097dc8a9c7f030b99655`.
- Read the approved P1 phase, the complete Claude report including round-10 remediation, and all prior P1
  review rounds.
- Inspected the product diff from the recorded baseline, excluding `docs/planning/`; verified
  `compare_core`, updater, auth, settings, manifests, requirements, and `build.ps1` remain outside P1.
- Ran the targeted P1 contract checks: consolidation outcome, TSN outcome, batch outcome, outcome
  vocabulary/reducer, export summary/cache envelope, and read-counts layout; all passed.
- Ran matrix, matrix-TSN, day-matrix, worker-lifecycle, application-module reachability,
  import-direction, and auto-consolidation checks; all passed.
- Ran JavaScript syntax checking, the matrix partial-renderer check, targeted Python byte-compilation, and
  product `git diff --check`; all passed.
- Independently exercised the final/temp reconciliation truth table:
  final-complete + temp-partial resolved partial; a stale temp-partial did not override final-complete;
  final-partial dominated temp-complete; and temp-complete without a final resolved complete.
- Independently replayed the exact failed-publication conflict through
  `consolidate_and_compare_tsn`; `write_outcome` returned false, reuse read partial, and the comparison
  result carried `completion=partial`.
- Verified every persistent writer calls `consolidation_meta.write_outcome` and honors its failure result,
  and the new modules remain included in packaged-module reachability and blocking CI checks.
- Did not run a browser/GUI launch, destructive build, complete check suite, PyInstaller, frozen
  self-tests, live TSMIS access, or mutate shared build artifacts.

### 6. Whether Claude may proceed toward phase approval

**Yes.** Claude may approve and commit P1 in accordance with the coordination rules. The next phase must
not begin in the same turn as the P1 commit.
