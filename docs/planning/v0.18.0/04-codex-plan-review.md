# Codex Adversarial Plan Review

## Review round 1

**Plan reviewed:** `03-claude-draft-plan.md` at repository HEAD `d2ee353`  
**Review posture:** Read-only adversarial review against the coordination record, both investigation packets, and current source.

### 1. Overall assessment

Draft Plan v1 has the right central thesis and correctly elevates F1–F5 ahead of cosmetic decomposition. It is unusually evidence-rich, preserves several critical contracts, and avoids an asyncio/plugin/framework rewrite.

It is not yet executable as written. The most consequential problems are architectural rather than editorial:

- the proposed shared outcome enum conflates operation completeness with artifact disposition and does not define how current producer results map into it;
- the transactional lifecycle does not specify crash recovery, multi-file comparison commits, or validation boundaries;
- the proposed `common.py` target dependency chain is contradicted by actual calls and would create a cycle;
- the exact-final-artifact gate is both technically undefined and sequenced after several packaging-sensitive module splits;
- the canonical report descriptor is assigned unrelated packaging and independent-test responsibilities, which would create a new god-registry and tautological checks;
- the stable-key design does not distinguish report-family identity from export, consolidation, comparison, and matrix-operation identity;
- the plan's release scope and definition of done are inconsistent with its own conditional phases.

The correctness work is directionally strong, but these defects must be resolved before implementation begins.

### 2. Blocking plan defects

#### R1-B01 — The terminal-outcome model is not a usable contract

- **Severity:** blocking
- **Affected plan section or phase:** §§5, 7, 9, 11; P1
- **Repository evidence:** `events.RunResult` contains independent `saved`, `empty`, `user_skipped`, `failed`, `exists`, and `per_route` fields but no terminal status. `events.ConsolidateResult` exposes only `ok|cancelled|error`; `consolidate_xlsx_base.consolidate_xlsx` can return `status="ok"` while `summary_lines` announce skipped/failed inputs. `compare_core.run_compare` also returns `status="ok"` with an incomplete warning and forced `verdict="diff"`. P1 lists changes to `outcome.py`, workers, and matrix orchestration but does not list the producer changes needed to stop inferring completeness from human strings.
- **Exact correction expected:** Replace the six-value all-purpose enum with either (a) orthogonal fields such as `completion = complete|partial|no_data|cancelled|failed` and `artifact = promoted|new_unpromoted|previous_preserved|none`, or (b) explicitly separate export, consolidation, and artifact-promotion result types with shared predicates. Add a normative mapping table for every `RunResult` combination (`empty`, `user_skipped`, `failed`, `exists`, cancellation) and every `ConsolidateResult` producer. Extend producers with machine-readable warnings/completeness; never parse `summary_lines`. Define which states permit promotion, manifest completion, cache recording, auto-consolidation, auto-comparison, and green UI.

#### R1-B02 — P2's transaction does not meet its stated crash-safety guarantee

- **Severity:** blocking
- **Affected plan section or phase:** §§5, 10, 11, 18; P2
- **Repository evidence:** The proposed sequence is `stage → rename live to .old → staged to live → drop .old`. A process death between the two renames leaves no directory at the canonical live path. No startup recovery/journal policy is specified. Existing comparison output can be a set: `compare_core.run_compare(mode="both")` writes formulas and values workbooks separately, while matrix code writes a canonical values workbook and a best-effort formulas sibling. Direct `wb.save(...)` calls exist in `compare_core`, `consolidate_xlsx_base`, report-specific consolidators, and TSN builders. Passing a temporary path into existing writers would also leak the temporary name into `ConsolidateResult.output_path` and summary text.
- **Exact correction expected:** Specify an artifact-set transaction protocol, not only a rename sequence: validation before commit, deterministic backup name, startup/re-entry recovery for every crash point, stale backup/staging cleanup, lock behavior, and an explicit invariant for the canonical path. Define whether formulas+values commit together or independently and how rollback handles one successful save. Inventory every writer that is in scope and state whether atomicity is implemented inside the writer or by a wrapper that rewrites returned paths/messages. Make P2 depend on the corrected P1 result contract.

#### R1-B03 — The proposed engine dependency direction is cyclic

- **Severity:** blocking
- **Affected plan section or phase:** §§6–8; P8
- **Repository evidence:** The proposed chain is `report_nav → auth_state → browser_channels → edge_device → site`. Current `common.launch_edge_login_context`, `capture_storage_state_if_logged_in`, `open_edge_device_context`, `try_device_sso_login`, and `storage_state_is_portable` call `navigate_with_auth`, `is_logged_in`, `get_url`, and/or `launch_browser`. Therefore an extracted `edge_device` necessarily depends on auth-page/navigation and browser-channel services; it cannot sit below both while `auth_state` also depends through it.
- **Exact correction expected:** Produce a symbol-level extraction DAG before naming modules. A plausible acyclic direction must keep leaf configuration/site/timeouts below page-auth navigation, keep browser-channel probing independent, place Edge/device flows above both page-auth and browser-channel services, and put `new_authed_browser` in an orchestration/session layer above those. Update the proposed structure, import-direction checks, and extraction order to that verified DAG.

#### R1-B04 — The exact-final-artifact verification is undefined and arrives too late

- **Severity:** blocking
- **Affected plan section or phase:** §§12, 15, 18, 21; P0/P10
- **Repository evidence:** `build/build.ps1 -SelfTest` changes the entry script/app name and builds `TSMIS SelfTest.exe`; it does not exercise the final windowed `TSMIS Exporter.exe`. The release workflow publishes two frozen windowed variants plus one source ZIP, not “three frozen variants.” P7 and P8 create many new modules and P9 changes UI asset loading before P10 adds the exact-artifact gate.
- **Exact correction expected:** Define how the exact final windowed executable will invoke a non-GUI self-test path—such as a pre-webview command-line flag in the real entry point—or define another test that truly executes the same final EXE and bundle. Gate both final windowed variants after all copy/prune steps. Give the batch-source ZIP its own clean-install console smoke rather than calling it frozen. Move this gate, or at least its implementation and first green run, before packaging-sensitive P4/P7/P8/P9 work.

#### R1-B05 — `report_catalog` is assigned unrelated ownership and would make tests tautological

- **Severity:** blocking
- **Affected plan section or phase:** §§5–9, 15; P4/P10
- **Repository evidence:** `build/app.spec:APP_MODULES` contains infrastructure modules (`paths`, `common`, `events`, `updater`, GUI modules, etc.) that are not report metadata. `build/check_fake_site.py` is valuable because its site fixture independently exercises selectors and labels. Deriving `APP_MODULES` and fake-site fixtures from the same catalog used by production would allow a wrong catalog entry to make production and its test agree.
- **Exact correction expected:** Limit the canonical catalog to report/capability metadata and import references. Keep packaging completeness as a separate runtime-module inventory/reachability contract. Preserve independent golden fake-site fixtures and assertions against the catalog where appropriate; do not generate the entire oracle from the code under test. State which UI/mock data is safely derived and which verification data must remain independent.

#### R1-B06 — Stable “report key” is under-specified across non-isomorphic registries

- **Severity:** blocking
- **Affected plan section or phase:** §§5, 9–11; P3/P4
- **Repository evidence:** There are 7 export rows, 8 consolidation rows, and 15 comparison rows. Highway Log alone has distinct export formats, multiple consolidators, cross-environment comparisons, TSN comparisons, and PDF-vs-Excel self-comparisons. A single family key or `subdir` cannot uniquely identify every bridge operation.
- **Exact correction expected:** Define a stable ID taxonomy: report-family/row key, export-operation key, consolidation-operation key, and comparison-operation key where cardinalities differ. Specify uniqueness rules and examples for every current row. State exactly which ID is persisted in `batch_job.json` (export key), which travels through each bridge method, and how matrix row keys relate without being renamed.

#### R1-B07 — P1 omits the frontend migration required by its user-visible contract

- **Severity:** blocking
- **Affected plan section or phase:** P1, §§9, 14
- **Repository evidence:** P1 promises the UI will show “partial — kept last-good,” but its affected-file list omits `scripts/ui/app.js` and the mock. Current `dispatch` handles fixed event shapes and the export/batch/matrix completion handlers infer state from existing booleans and payloads. P7/P9 are scheduled later.
- **Exact correction expected:** Add the exact Python→JS payload changes, affected frontend handlers/state, mock behavior, and bridge tests to P1. Preserve existing event order while adding fields. Define backward/default handling for absent fields inside the same packaged version and test complete, partial, cancelled, failed-preserving-previous, and stale-prior-output cases.

### 3. Required changes

#### R1-R01 — Define promotion semantics for every route result

- **Severity:** required
- **Affected plan section or phase:** P1; CT-1
- **Repository evidence:** A route reported `empty` is not necessarily a failure: it can mean the site validly returned no data, in which case removing a previously present route file may be correct. `user_skipped` and `failed` have different causes. `exists` should not normally occur in a fresh staging directory and can indicate stale staging residue.
- **Exact correction expected:** Add a table that decides completeness and promotion for all route statuses. Explicitly state whether mixed saved+empty is complete, user-skipped is partial, failed is partial, all-empty is no-data, and any `exists` in a supposedly fresh stage is rejected or explained. CT-1 must cover each row, not only `failed`.

#### R1-R02 — Make consolidator partial status producer-owned

- **Severity:** required
- **Affected plan section or phase:** P1
- **Repository evidence:** `consolidate_xlsx_base` intentionally reports incomplete input through `summary_lines` while keeping `status="ok"`. PDF consolidators also emit reconciliation warnings. Matrix currently ignores the result object.
- **Exact correction expected:** Identify every consolidator capable of skipped/failed inputs and add structured fields or a new partial status at those producers. Update console, GUI, auto-consolidation, matrix, and TSN-library consumers together. Add compatibility tests for a partial but usable workbook versus an error that must preserve the old workbook.

#### R1-R03 — Define fingerprint contents and commit timing

- **Severity:** required
- **Affected plan section or phase:** P2; CT-6/CT-7
- **Repository evidence:** Current freshness uses maximum mtime in `matrix._consolidated_stale`, `_cmp_state`, and day-matrix helpers. Deletions are invisible. The draft says “input-set fingerprint” but does not define it.
- **Exact correction expected:** Specify canonical relative names, file type filters, sizes, high-resolution mtimes and, if justified, content hashes. Define ordering, treatment of temp/lock files, unreadable files, directories, TSN raw sets, formulas/value siblings, and source absence. Write the sidecar only after a successful artifact commit; a missing/corrupt/mismatched sidecar must be stale. Add same-name replacement and deletion tests.

#### R1-R04 — Harden legacy manifest migration against unknown IDs

- **Severity:** required
- **Affected plan section or phase:** P3; CT-9
- **Repository evidence:** `batch_manifest.load` currently accepts only version 1; `BatchWorker._specs` silently drops out-of-range indices, which can leave an empty spec list and still allow an environment to be marked done. The plan covers ordinary int→key mapping only.
- **Exact correction expected:** Support explicit v1 and v2 loaders. Map v1 indices against a frozen v0.17 export-order constant before any reorder, not a mutable future view. Reject—do not silently drop—unknown, duplicate, disabled, or removed keys. Define whether migration rewrites immediately or only on the next save. Test empty/invalid selections and ensure no environment is marked done when no valid report resolved.

#### R1-R05 — Remove the unproven `paths.py` initialization rewrite

- **Severity:** required
- **Affected plan section or phase:** §§2, 6, 17; P6
- **Repository evidence:** Coordination decision D7 says import-time environment mutation is intentional and must not be revived as a defect. `paths.py` sets `PLAYWRIGHT_BROWSERS_PATH` before any `sync_playwright()` starts, and `common._chromium_available` consumes it. The plan nevertheless moves it to `init_browser_path()` without identifying every entry point that must call it.
- **Exact correction expected:** Remove this change from P6 unless a separate proven startup defect requires it. If retained for lazy-startup reasons, enumerate all GUI, CLI, login, test, and batch entry points, add an assertion that initialization precedes Playwright import/start, and classify it as high-risk behavior—not low-risk cleanup.

#### R1-R06 — Do not use mixins as a substitute for state ownership

- **Severity:** required
- **Affected plan section or phase:** §§5–8; P7
- **Repository evidence:** `GuiApi`'s problem is shared mutable coordination state (`_task`, queues, current job, matrix state, workers, cancellation events), not merely file length. Feature mixins sharing one `self` preserve hidden cross-feature coupling and can add MRO/import complexity. Extracting queue pumps and snapshots into `gui_state.py` without an owner can spread that coupling further.
- **Exact correction expected:** Define the single owner of task state and transitions. Prefer composition/delegation to feature services or, if mixins remain, document each mixin's owned fields, allowed calls, and prohibition on cross-mixin private access. Split P7 into protocol/state-machine work and mechanical endpoint extraction; do not combine state movement, dispatch replacement, enum migration, method unification, and all feature splits in one phase.

#### R1-R07 — Resolve O3 as currently non-reproducible and narrow concurrency work

- **Severity:** required
- **Affected plan section or phase:** O3; P8
- **Repository evidence:** `ActiveEnvCheckWorker.run` calls `set_thread_site(self.src, self.env)` and clears it in `finally`; every `EnvScanWorker` scanner does the same. `get_site()` prefers the thread-local pin. `BatchWorker` uses process-global `set_site`, but the concurrent environment checks are pinned and therefore do not inherit the batch target.
- **Exact correction expected:** Record that the proposed wrong-folder race is not reachable through the investigated active/env-scan workers at current HEAD. Do not add a global site lock as a speculative fix. Retain “snapshot site once per run” only if it improves explicit job context without changing behavior, with a focused test. Reopen concurrency changes only if another unpinned concurrent caller is identified.

#### R1-R08 — Separate behavior-neutral engine extraction from live auth changes

- **Severity:** required
- **Affected plan section or phase:** P8
- **Repository evidence:** P8 combines leaf extraction, page/auth extraction, browser-channel movement, site changes, cancellation semantics, exact report selection, CDP lifetime changes, and logging. `common.py` contains field-hardened Playwright flows, and `open_edge_device_context`/portability checks recursively use navigation helpers.
- **Exact correction expected:** Divide P8 into at least: pure leaves; browser/auth mechanical movement behind the shim; and behavior changes requiring work-PC acceptance. Do not move a function and alter its cancellation/CDP/select behavior in the same commit. Give each subphase its own protected imports, thread-affinity assertions, and rollback.

#### R1-R09 — Specify JavaScript module loading before extracting `mock.js`

- **Severity:** required
- **Affected plan section or phase:** P9
- **Repository evidence:** `index.html` currently loads a classic `<script src="app.js">`; all UI functions share classic-script globals. A `mock.js` loaded only for `#mock` requires either static script ordering or dynamic/ES-module loading. File/pywebview origins and the HTTP mock can behave differently, and the current frozen smoke does not prove `#mock`.
- **Exact correction expected:** State whether extraction uses classic scripts, generated data, or ES modules; define load order and local/frozen URL behavior. Add an automated or deterministic browser check that boots real production mode and `#mock` mode, verifies no missing globals/404s, and exercises reset preview plus matrix tabs. Do not merge the two matrix renderers in the same change as mock extraction.

#### R1-R10 — Make build reproducibility address the reused environment

- **Severity:** required
- **Affected plan section or phase:** P10
- **Repository evidence:** `build.ps1` reuses `build/.venv`, upgrades pip, and installs pinned direct requirements. Hash-pinning requirements does not remove stale packages already present in a reused environment. `requirements-build.txt` includes `-r requirements.txt`, and transitive Windows wheels/markers must be locked consistently.
- **Exact correction expected:** Define a clean build-environment policy—recreate the venv, verify an exact lock, or fail on unexpected packages. Specify how hashes are generated and updated for Windows/Python 3.11 and how platform markers are handled. Do not claim reproducibility from `--require-hashes` alone.

#### R1-R11 — Replace raw XLSX byte-identity claims with valid semantic gates

- **Severity:** required
- **Affected plan section or phase:** P2/P5/P10 completion criteria
- **Repository evidence:** XLSX files are ZIP containers and may contain serialization timestamps/order that make raw byte comparison unsuitable. Existing golden checks load workbooks with openpyxl, assert schemas/cells/counts, and use Excel COM for formula recalculation. The plan repeatedly says the produced workbooks will be “byte-identical.”
- **Exact correction expected:** Name the actual parity method: normalized ZIP/XML comparison if truly required, otherwise cell/formula/style/defined-name/property comparison plus existing count canaries and COM F9. Use “behaviorally/semantically identical” unless a deterministic byte comparator already exists and is named.

#### R1-R12 — Resolve the `compare_core` contradiction

- **Severity:** required
- **Affected plan section or phase:** §§5, 8, 15, 22; P5/P10
- **Repository evidence:** The plan says `compare_core` is untouched and explicitly excludes behavior changes, but P5 adds `compare_core.make_notes_sheet` and P10 changes `run_compare` to return counts.
- **Exact correction expected:** Either keep all new helper code outside `compare_core` and add result metadata through an explicitly approved additive `ConsolidateResult` field, or revise the protected-contract statement to permit those exact additive changes with named semantic/COM gates. Do not claim both “untouched” and “modified.”

#### R1-R13 — Keep test fixtures independent of production derivation

- **Severity:** required
- **Affected plan section or phase:** P4/P9; CT-12/CT-13
- **Repository evidence:** Deriving mock/test/fake-site data from `report_catalog` prevents drift but can also make a bad catalog self-validating. Current TSN/report golden checks intentionally encode independently approved counts and shapes.
- **Exact correction expected:** Classify each fixture as generated product data or independent oracle. Generate UI display metadata where useful, but retain explicit approved snapshots for report order, stable IDs, site labels, and comparison layouts. CT-13 must compare independently obtained backend payload snapshots to frontend expectations rather than import the same constants on both sides.

#### R1-R14 — Expand CT-10 beyond static message-name parity

- **Severity:** required
- **Affected plan section or phase:** P0/P7; CT-10
- **Repository evidence:** Exactly-once terminal behavior is path-dependent. Workers can emit success, error, and final messages from `try/except/finally`; a static inventory cannot prove one terminal event across success, cancellation, auth error, unexpected exception, and late-message paths.
- **Exact correction expected:** Define terminal kinds per worker and add deterministic lifecycle tests for every worker class or worker family covering success, cancellation, expected error, unexpected error, and duplicate/late terminal delivery. Assert task-gate release and queue advancement, not only handler membership.

#### R1-R15 — Give cache migration one versioned envelope and one rebuild

- **Severity:** required
- **Affected plan section or phase:** P1/P2; §10
- **Repository evidence:** Matrix and day caches are currently unversioned raw dictionaries, while P1 changes count interpretation and P2 changes freshness identity. The plan independently proposes cache invalidation in both phases.
- **Exact correction expected:** Define one envelope schema with version, entries, output identity, and input fingerprint. If P1 and P2 ship in one release, avoid two user-visible rebuild migrations. Old dictionaries must be treated as stale without deletion until a successful recompute writes the new envelope.

### 4. Recommended changes

#### R1-A01 — Use objective performance thresholds

- **Severity:** recommended
- **Affected plan section or phase:** P0/P10; §21
- **Repository evidence:** “Measurably improved” can be satisfied by noise. Cold start, matrix snapshot, and 50k-row comparison have no specified environment, repetitions, percentile, or regression threshold.
- **Exact correction expected:** Define the measurement harness, representative data shape, cold/warm distinction, repeat count, and success/no-regression threshold before optimizing. If no material improvement appears, retain the correctness-friendly design and drop the optimization.

#### R1-A02 — Remove the speculative bounded worker queue

- **Severity:** recommended
- **Affected plan section or phase:** §§13, 18; P7/P8
- **Repository evidence:** No queue-growth measurement or field failure is cited. Workers currently use queue delivery for terminal events; bounding without a nonblocking/drop policy can deadlock a worker while the GUI sender is stalled.
- **Exact correction expected:** Remove queue bounding from v0.18.0 unless a measured growth problem is documented. If retained, specify capacity, backpressure, which event classes may coalesce/drop, and how terminal events are guaranteed delivery.

#### R1-A03 — Defer the signature “slot” until its verification contract exists

- **Severity:** recommended
- **Affected plan section or phase:** P10
- **Repository evidence:** SignPath is not enabled, no certificate/publisher policy is final, and Windows Authenticode verification may not need a bundled `cryptography` dependency. A placeholder abstraction can become dead security theater.
- **Exact correction expected:** Keep signing parity in workflow design, but do not add a runtime signature abstraction or new crypto dependency until the signed artifact shape, trusted publisher/certificate chain, offline behavior, and updater verification API are decided.

#### R1-A04 — Do not use line count as the structural definition of done

- **Severity:** recommended
- **Affected plan section or phase:** §21
- **Repository evidence:** The plan requires no `scripts/` module above ~800 lines except `compare_core`, but does not split `gui_worker.py` (~1,862 lines), and deeper `app.js` splitting is conditional on O1. `gui_worker.py` is already class-segmented, so forcing a threshold can produce needless files.
- **Exact correction expected:** Replace the global line limit with named responsibility/ownership outcomes and complexity or dependency metrics for modules actually changed. If a line target remains, list explicit exceptions and ensure every target is covered by a phase.

#### R1-A05 — Keep CI trigger changes separate

- **Severity:** recommended
- **Affected plan section or phase:** §12
- **Repository evidence:** The plan proposes branch-filtering checks to avoid push+PR duplication but does not define branch-protection behavior. A trigger change can accidentally remove the required check from one workflow context.
- **Exact correction expected:** Either omit this optimization or specify exact `on.push.branches`, `pull_request`, required-check names, and validation that branch protection still receives one blocking result.

### 5. Items to remove or narrow

#### R1-N01 — Narrow P5 to independently proven duplication

- **Severity:** required
- **Affected plan section or phase:** P5
- **Repository evidence:** P5 combines TSN loader factories, five comparator drivers, normalization helpers, notes-sheet movement, shared styles, and a ~500-line deletion target. These have different contracts and rollback surfaces.
- **Exact correction expected:** Split or narrow P5 to one duplication family at a time. Keep thin compatibility modules for existing import strings such as `tsn_library.TsnReport.builder`. Remove the line-deletion quota. Move notes-sheet work outside `compare_core` or defer it.

#### R1-N02 — Narrow P6 to evidenced persistence changes

- **Severity:** required
- **Affected plan section or phase:** P6
- **Repository evidence:** `_safe_join`, `full_snapshot()`, and a schema version are named without concrete unsafe call sites or a concrete v0→v1 transformation. The known high-value changes are writer deduplication, auth write atomicity/ACL, and support-bundle allowlisting.
- **Exact correction expected:** Name the exact validation/migration each new settings field solves or remove it. Do not add a schema version solely as ceremony. Remove `_safe_join` unless a specific untrusted path join is identified. Include atomic auth-file replacement before ACL work.

#### R1-N03 — Narrow P9 to mock separation until O1 is answered

- **Severity:** required
- **Affected plan section or phase:** P9
- **Repository evidence:** The GUI is documented as a stopgap, O1 is unresolved, and renderer merging is behavior-changing work unrelated to mock drift.
- **Exact correction expected:** Make mock extraction plus payload parity the default P9 scope. Treat renderer merging and deeper modularization as explicitly deferred unless O1 is resolved before implementation and a browser test net is added.

#### R1-N04 — Remove unsafe work-PC “disk-full” induction

- **Severity:** required
- **Affected plan section or phase:** §§18, 20; P2
- **Repository evidence:** Deliberately filling or pressuring a managed work PC is unnecessary and can affect unrelated applications. Rename/write failures can be injected deterministically in temp directories.
- **Exact correction expected:** Keep disk-full and rename failures in offline fault-injection tests. Limit work-PC verification to safe lock/Defender behavior using disposable test destinations and explicit cleanup.

### 6. Missing repository areas

#### R1-M01 — Console consolidation menu drift is not assigned to an implementation phase

- **Severity:** required
- **Affected plan section or phase:** P4/P10/P11
- **Repository evidence:** `4. consolidate (combine reports).bat` exposes six choices and omits Intersection Summary and Intersection Detail, while `reports.CONSOLIDATE_REPORTS` has eight. The source ZIP is a published release variant.
- **Exact correction expected:** Add the exact batch file to P4 or a dedicated compatibility task, update it, and add a parity/smoke check. Documentation alone in P11 is insufficient.

#### R1-M02 — Batch/source release verification is missing

- **Severity:** required
- **Affected plan section or phase:** P10
- **Repository evidence:** `.github/workflows/release.yml` publishes `*-batch-source.zip`. It is not a frozen artifact and depends on global Python/setup and bare module imports.
- **Exact correction expected:** Add a clean extraction/setup-free or dependency-present console smoke for import, menu-to-module dispatch, consolidation selection, and report registry compatibility. Keep it distinct from the two frozen EXE gates.

#### R1-M03 — Destination ownership and reset safety remain undispositioned

- **Severity:** required
- **Affected plan section or phase:** P2/P6/P11
- **Repository evidence:** Reset and stage/swap treat known child names under a user-selected destination as app-owned; there is no ownership marker. The Codex investigation explicitly retained this residual risk after the root-delete fix.
- **Exact correction expected:** Either include a marker/manifest ownership design with migration behavior for existing destinations, or explicitly defer it with rationale and preserve the current preview/scoped-delete protections. Do not imply `_safe_join` solves ownership.

#### R1-M04 — Updater audit coverage is incomplete

- **Severity:** required
- **Affected plan section or phase:** §§13, 15, 17; P10
- **Repository evidence:** The detailed P10 work omits or only vaguely names explicit open findings: explicit ZIP member containment, download retry/timeout policy, staged-EXE rehash, release-list cap, rollback messaging when restoration fails, old-process death wait, and update-helper log rotation. Section 17 says “death-window hardening” without exact tasks/tests.
- **Exact correction expected:** Add a disposition table mapping each updater audit item to implement/defer/obsolete, with exact symbols and checks. Completion criteria must not say updater hardening is complete while these remain implicit.

#### R1-M05 — Remaining audit items are grouped too vaguely

- **Severity:** required
- **Affected plan section or phase:** §§17, 21; P11
- **Repository evidence:** Open items such as reset-token consumption, empty per-route run reports, report-selection rearming, PDF empty-save backstop, JS wait validation, side-label truncation, greedy duplicate pairing, fixed coordinates, junction handling, and dev cache cleanup are collapsed into “~20 hygiene” or “where cheap.”
- **Exact correction expected:** Give every open audit finding an individual disposition and phase or explicit deferral rationale. “Where cheap” is not executable or objectively reviewable.

### 7. Unsafe sequencing or migration concerns

#### R1-S01 — P2 must follow the corrected outcome contract

- **Severity:** required
- **Affected plan section or phase:** §18 task graph; P1/P2
- **Repository evidence:** `artifact_store` is supposed to report whether a previous artifact was preserved, while `outcome.py` owns the terminal vocabulary. The task graph currently makes P1 and P2 independent children of P0.
- **Exact correction expected:** Make P2 depend on the finalized P1 contract, or merge only the minimal promotion-result portion needed by P2 into a shared prerequisite. Avoid implementing artifact disposition twice.

#### R1-S02 — Packaging safety must precede broad module extraction

- **Severity:** blocking
- **Affected plan section or phase:** §18 task graph; P4/P7/P8/P9/P10
- **Repository evidence:** New dynamically referenced modules and UI files can pass source checks while failing PyInstaller collection or frozen asset loading. P10 currently lands after all those changes.
- **Exact correction expected:** Split P10 into an early exact-artifact safety gate and later packaging/performance hardening. Require the early gate before broad Python/UI module extraction.

#### R1-S03 — Do not perform two cache migrations in one release

- **Severity:** required
- **Affected plan section or phase:** P1/P2
- **Repository evidence:** P1 invalidates caches for corrected counts; P2 invalidates them again for fingerprints.
- **Exact correction expected:** Use the single envelope/version from R1-R15 and perform one forward invalidation/rebuild after both semantics are in place, unless phases are intentionally shipped as separate releases.

#### R1-S04 — Do not remove legacy TSN/import modules without shims

- **Severity:** required
- **Affected plan section or phase:** P4/P5/P10
- **Repository evidence:** `tsn_library.TsnReport.builder` stores `"module:function"` strings, the spec manually packages those modules, and docs/tests import them directly.
- **Exact correction expected:** Preserve thin old-name modules or migrate every builder string, import, package entry, source ZIP path, and test in one characterized step. State how old external console invocations behave.

### 8. Missing tests and verification

#### R1-T01 — Test artifact recovery after process restart, not only caught exceptions

- **Severity:** required
- **Affected plan section or phase:** P2; CT-4/CT-5
- **Repository evidence:** The proposed transaction can leave `.old`/`.staging` after an abrupt process stop. Monkeypatching a rename to raise only tests in-process rollback.
- **Exact correction expected:** Seed every intermediate on-disk state as if the process died, invoke startup/re-entry recovery, and assert canonical live data, backup retention, diagnostics, and safe cleanup.

#### R1-T02 — Test multi-output comparison commit behavior

- **Severity:** required
- **Affected plan section or phase:** P2; CT-8
- **Repository evidence:** `compare_core.run_compare(mode="both")` writes two files; matrix also maintains a canonical values workbook and formulas sibling.
- **Exact correction expected:** Inject failure on the first and second saves and during promotion. Assert the documented generation policy for both files and that result paths/messages never expose temporary names.

#### R1-T03 — Test UI outcome payload semantics in P1

- **Severity:** required
- **Affected plan section or phase:** P1
- **Repository evidence:** Existing Python checks exercise bridge calls, but the promised new partial/preserved state affects JavaScript rendering and matrix chaining.
- **Exact correction expected:** Add backend payload assertions plus a frontend/mock scenario for complete, valid-empty, user-skipped, failed route, cancellation, consolidation partial, consolidation error with stale prior file, and promotion failure.

#### R1-T04 — Verify exact-match report selection with duplicate/superstring labels

- **Severity:** required
- **Affected plan section or phase:** P8
- **Repository evidence:** `common.select_report` uses `has_text=report_label).first`; the audit finding is a substring/superstring ambiguity.
- **Exact correction expected:** Add a deterministic fake-site fixture containing exact, prefix, suffix, and disabled variants before changing the selector. Assert exact selection and a clear error for zero or multiple exact matches.

#### R1-T05 — Add independent catalog/console/packaging parity checks

- **Severity:** required
- **Affected plan section or phase:** P3/P4/P10
- **Repository evidence:** Report metadata is represented in runtime registries, `.bat` menus, TSN builders, matrix dispatch, fake-site fixtures, and the spec.
- **Exact correction expected:** Add separate checks for stable-ID uniqueness, current display/order snapshots, `.bat` menu coverage, dynamic import resolvability, and runtime-module packaging completeness. Do not satisfy all of them by importing one generated object.

#### R1-T06 — Define final-artifact acceptance per published variant

- **Severity:** required
- **Affected plan section or phase:** P10
- **Repository evidence:** Release variants have different browser assumptions and the source ZIP has a different driver surface.
- **Exact correction expected:** Name the exact checks for system-browser EXE, bundled-browser EXE, and batch-source ZIP; state whether a skipped hidden webview/browser probe is allowed. A release-blocking exact-artifact gate must fail, not silently skip, when its required capability is absent.

### 9. Disagreements with the target architecture

#### R1-D01 — Completion and artifact disposition should not be one enum

- **Severity:** blocking
- **Affected plan section or phase:** Target architecture item 1
- **Repository evidence:** A partial consolidation can produce a usable new workbook, a failed refresh can preserve an old workbook, and a valid no-data export can require deleting a formerly present route file. These are independent axes.
- **Exact correction expected:** Adopt the orthogonal or domain-specific contract described in R1-B01.

#### R1-D02 — Packaging inventory is not report metadata

- **Severity:** blocking
- **Affected plan section or phase:** Target architecture item 4
- **Repository evidence:** Most `APP_MODULES` entries are infrastructure, not reports.
- **Exact correction expected:** Keep runtime packaging inventory/reachability separate from the report catalog, with cross-assertions only for dynamically imported report modules.

#### R1-D03 — Mixins do not establish architectural boundaries

- **Severity:** required
- **Affected plan section or phase:** Target architecture item 6
- **Repository evidence:** All mixins would still mutate one `GuiApi` object's task, queue, worker, and cancellation fields.
- **Exact correction expected:** Define state ownership and dependencies first; choose mixins only for mechanical endpoint grouping after that boundary is enforceable.

#### R1-D04 — The engine layer graph must follow actual call direction

- **Severity:** blocking
- **Affected plan section or phase:** §§6–7
- **Repository evidence:** Edge/device helpers call page-auth and browser-channel helpers, contradicting the proposed lower-layer position.
- **Exact correction expected:** Replace the graph with the verified acyclic DAG required by R1-B03.

#### R1-D05 — Independent test oracles must remain independent

- **Severity:** required
- **Affected plan section or phase:** Target architecture items 4–5
- **Repository evidence:** Generating production registries and test fixtures from one table prevents detection of wrong shared metadata.
- **Exact correction expected:** Separate generated consumer data from independent approved snapshots and fake-site contracts.

### 10. Questions Claude must resolve

1. For each `RunResult` route status, is the refresh complete, partial, or valid-empty, and may it replace last-good?
2. Are completion and artifact disposition separate fields, or how does one enum represent their combinations without losing information?
3. Which consolidators will emit structured partial status, and which consumers change in the same phase?
4. How does artifact recovery work after a process death at every rename/replace point?
5. Are formulas and values workbooks one transaction or two independently valid artifacts?
6. What are the stable IDs for every one of the 7 export, 8 consolidation, and 15 comparison rows?
7. How does a v1 manifest with an invalid/removed index fail without silently marking work complete?
8. What is the corrected acyclic `common.py` extraction DAG?
9. Who owns `_task`, queue advancement, cancellation events, and exactly-once terminal transitions after P7?
10. How will `mock.js` load in direct-file, HTTP mock, pywebview, and frozen contexts?
11. How will the actual final `TSMIS Exporter.exe` enter self-test mode without building a different executable?
12. Which two frozen variants and which source variant are gated, and what is allowed to skip?
13. Which data in `report_catalog` is production-generated, and which tests remain independent?
14. Why should `paths.py` initialization change despite D7, and which entry points prove ordering?
15. Which updater audit findings are fixed, deferred, or explicitly outside v0.18.0?
16. Which optional phases are removed if O1/O2/O7 remain unanswered?

### 11. Phase-count and phase-boundary assessment

#### R1-P01 — Twelve phases are not all release-critical and several are internally too broad

- **Severity:** blocking
- **Affected plan section or phase:** §18 and §21
- **Repository evidence:** P0–P11 is 12 phases. P7 combines five architectural changes; P8 combines extraction with the highest-risk live auth/security changes; P10 combines exact-artifact CI, lazy imports, performance, dependency locking, updater security, signing parity, and bundle work. P5 is discretionary DRY work. P9 is conditional. O1, O2, O3, O6, and O7 remain open, yet §21 treats most resulting work as mandatory.
- **Exact correction expected:** Classify phases as release-blocking, conditional, or deferrable. Divide P7, P8, and P10 along behavior/risk boundaries; move the exact-artifact gate early; make P2 depend on P1; perform one cache migration; and remove conditional/deferred work from the v0.18.0 definition of done. The final plan must be achievable without silently carrying failed work-PC acceptance as “owed.”

#### R1-P02 — Rollback independence is overstated

- **Severity:** required
- **Affected plan section or phase:** §19
- **Repository evidence:** P4 consumers depend on P3 keys; P7 consumes P1 outcomes; P9 fixtures depend on P4; P10 may derive packaging from P4. Reverting an early phase after later phases land can require reverting dependents. Persisted v2 manifests/cache envelopes also outlive a code revert.
- **Exact correction expected:** Replace “any phase can be reverted without unwinding a later one” with dependency-aware rollback rules. For each persisted schema change, state backward-read behavior after rollback or declare rollback requires reverting dependent commits and restoring compatible data.

### 12. Verdict

**NOT READY**

Draft Plan v1 should be revised before implementation. Its evidence base and priorities are strong, but the blocking contract, dependency, packaging-gate, identity, and phase-scope defects above would otherwise cause rework or introduce new failure modes during the overhaul.
