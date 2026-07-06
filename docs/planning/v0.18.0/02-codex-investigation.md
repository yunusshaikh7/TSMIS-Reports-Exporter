# Codex Investigation Packet — v0.18.0

**Repository:** `TSMIS-Reports-Exporter`  
**Evidence baseline:** Git HEAD `d2ee353`, inspected 2026-06-21  
**Posture:** Independent architectural investigation; this is not the v0.18.0 implementation plan.

This packet is based on read-only source inspection, static dependency and complexity analysis, targeted parsing, Git history inspection, and review of existing public repository documentation and audits. It deliberately did not execute the complete check suite, frozen builds, browsers, GUI, live TSMIS, private configuration, credentials, profiles, report data, or internal site source.

Findings are labeled as:

- **Defect:** current behavior can produce a wrong result, unsafe state, or materially misleading shipped-app behavior.
- **Reliability risk:** a concrete failure mode exists, but reproducing it depends on timing, filesystem behavior, or external state.
- **Structural risk:** maintainability or change-safety is poor even if current behavior is correct.
- **Drift:** two or more representations of one contract disagree or require manual synchronization.

## 1. Repository and dependency map

### Runtime layers

```text
gui_main.py
  ├─ startup logging / cleanup / updater swap handling
  ├─ gui_api.py                     application façade + state owner + JS bridge
  │   ├─ settings.py / paths.py     persisted settings and filesystem locations
  │   ├─ reports.py                 export/consolidate/compare registries
  │   ├─ gui_worker.py              background workers and batch orchestration
  │   ├─ matrix.py                  Everything matrix, consolidation, comparison
  │   ├─ day_matrix.py              by-day matrix and comparison orchestration
  │   ├─ tsn_library.py             TSN source inventory/builders
  │   └─ updater.py                 release discovery, staging, swap helper
  └─ pywebview
      └─ scripts/ui/
          ├─ index.html
          ├─ app.js                 all frontend behavior plus full mock backend
          └─ app.css

Export path
  reports.py registry
    └─ report modules
        └─ exporter.py / exporter_parallel.py
            └─ common.py            site selection, auth, browser, selectors, waits

Consolidation path
  reports.py registry
    └─ report-specific consolidators
        └─ consolidate_xlsx_base.py or PDF-specific parsers

Comparison path
  reports.py / matrix.py dispatch
    └─ report-specific adapters
        └─ compare_core.py           workbook matching, rendering, summary output
```

### Structural measurements

At the inspected HEAD:

- 53 Python scripts are present.
- `scripts/ui/app.js` is approximately 5,003 lines and 242 KB.
- `gui_api.py` is approximately 3,526 lines and 175 KB. `GuiApi` alone spans roughly lines 124–3456, with about 190 methods and 97 methods exposed to JavaScript.
- `compare_core.py` is approximately 1,954 lines and 101 KB.
- `gui_worker.py` is approximately 1,863 lines and 94 KB, containing 15 worker classes.
- `common.py` is approximately 1,654 lines and 76 KB.
- `scripts/ui/app.css` is approximately 1,511 lines; `index.html` is approximately 1,021 lines.
- Static import analysis found no internal strongly connected import component. The problem is therefore not a Python import cycle; it is concentration of responsibilities, eager loading, global state, and manually synchronized contracts.
- Highest internal fan-in modules include `paths`, `events`, `cli`, `compare_core`, `common`, and `exporter`.
- Highest internal fan-out modules include `reports`, `gui_api`, `matrix`, `gui_worker`, and `compare_env`.

### Dependency direction observations

The nominal direction is reasonable: entry point → bridge/orchestrators → registries/workers → domain modules → browser/filesystem libraries. Three deviations reduce that benefit:

1. `reports.py` describes itself as import-light but imports approximately 23 internal report, consolidator, and comparator modules eagerly. Several of those import `openpyxl`, `pdfplumber`, and related heavy libraries at module import time.
2. `gui_api.py` imports `reports`, `matrix`, `day_matrix`, and `gui_worker` during GUI startup. The GUI therefore pays for most report-domain imports before the user chooses a feature.
3. Process-global and thread-local site selection in `common.py` forms a hidden dependency that is not visible in function signatures.

The repository does not need a new abstract framework. It needs explicit ownership boundaries around application state, task coordination, report metadata, persistence, and artifact promotion.

## 2. Highest-value structural findings with evidence

### F1 — Partial exports can replace last-good data and be recorded as complete

**Classification:** Defect; highest severity.

`gui_worker.ExportWorker._run_specs` stages each report in `<report>.staging`, invokes `run_export` or `run_export_parallel`, and then promotes staging with `_swap_store_dir`. Export functions return normally with a `RunResult.failed` collection when routes remain failed after retry. `_run_specs` only rejects staging on an exception or cancellation; it does not gate promotion on `RunResult.failed`.

Evidence:

- `gui_worker.py`, `ExportWorker._run_specs`, approximately lines 358–432.
- `exporter.py` and `exporter_parallel.py` use structured run results for route failures rather than raising the whole run.
- `gui_worker.BatchWorker.run`, approximately lines 460–583, discards the returned per-report results and marks the environment complete in `batch_manifest` whenever no exception/cancellation escapes.
- `gui_worker.MatrixBatchExportWorker.run`, approximately lines 1645–1712, increments successful work when the export step returns, not when all routes succeeded.
- `gui_api.GuiApi._on_matrix_export_done`, approximately lines 2522–2553, chains consolidation/comparison whenever the worker was not cancelled, without requiring `payload["ok"]`.

Consequences:

- A report with failed routes can replace a complete last-good report directory.
- Batch resume can skip an environment whose route set is incomplete.
- Everything-matrix export can report success and automatically compare incomplete output.
- The UI's “complete” state is not equivalent to complete report coverage.

Current checks characterize `_swap_store_dir` mechanics and successful/cancelled matrix flows, but not the `failed routes + no exception` case. This is a correctness contract that must be fixed and characterized before structural movement.

### F2 — Store promotion is not transactional

**Classification:** Reliability defect.

`gui_worker._swap_store_dir`, approximately lines 180–219, first removes the live directory and then renames staging. If live removal succeeds and rename fails, the exception handler removes staging, leaving no last-good directory. If live removal is incomplete, the fallback merges staged files into the surviving live directory and leaves stale files in place.

Related risks:

- Initial cleanup of a previous staging directory uses `shutil.rmtree(..., ignore_errors=True)` followed by `mkdir(exist_ok=True)`. Locked stale files can survive and be mistaken for valid resumable output.
- `_swap_store_dir` does not return a promotion status that callers can use.
- Callers still record success after fallback merge.

The intended invariant should be explicit: either the new report set is fully accepted and atomically becomes live, or the previous set remains intact. The current implementation guarantees neither under Windows locking or rename failure.

### F3 — Matrix orchestration ignores consolidator status and can compare stale workbooks

**Classification:** Defect.

`matrix._consolidate_store_folder`, approximately lines 671–693, invokes report consolidators but ignores their returned `ConsolidateResult`. Many consolidators return `status="error"` instead of raising. `_ensure_consolidated` and TSN comparison flows then check only whether the output path exists and is non-empty.

If a prior consolidated workbook exists and a forced or stale rebuild returns an error without replacing it, matrix orchestration can continue with the old workbook. The resulting comparison can then be cached as current.

There is a second contract mismatch: some consolidation paths return `status="ok"` while reporting skipped/failed inputs in summary text because the result model has no “partial” state. Matrix code ignores those warnings.

The orchestration layer needs a machine-readable distinction among complete, partial, no-data, cancelled, and failed output. Parsing human summary strings would create another fragile contract.

### F4 — Aggregate Ramp/Intersection TSN discrepancy counts are read with the wrong layout

**Classification:** Defect; user-visible.

`compare_ramp_summary_tsn.compare` and `compare_intersection_summary_tsn.compare` call `compare_core.run_compare(..., has_route=False)`. In this layout, the status and first compared-value columns are one column earlier than in route-keyed workbooks.

`matrix.build_comparison`, approximately lines 817–877, hardcodes `read_counts(out_path, has_route=True)` for TSN/self modes. `day_matrix.build_day_cell`, approximately lines 324–363, does the same. The accompanying comment says all TSN modes are route-keyed, which is false for these aggregate reports.

Likely visible effect:

- The overall comparison workbook can still say “different.”
- Matrix one-sided and differing-cell counts can display as zero because the reader is looking at the wrong columns.

Cross-environment aggregate comparison derives the layout from the adapter and does not share this exact error. Existing matrix checks validate dispatch/guards rather than live aggregate workbook readback.

### F5 — Freshness uses newest mtime, not input identity

**Classification:** Reliability risk.

`matrix._consolidated_stale`, approximately lines 751–766, compares only the newest source-file mtime with the consolidated output. Comparison-state helpers use similar maximum-mtime logic.

This does not detect:

- deletion of a route file when remaining files are older than the consolidated workbook;
- a changed input set with unchanged or older timestamps;
- replacement of one file by another preserving timestamp;
- partial input directories promoted after a failed run.

The stale workbook can therefore continue to include a deleted route, and a comparison sidecar can continue to claim freshness. A lightweight input fingerprint can be based on stable relative names, sizes, and high-resolution mtimes; cryptographic content hashing should be justified only where trust or same-metadata replacement matters.

`day_matrix.snapshot`, approximately lines 192–298, also computes day-level consolidation freshness as “any exists and all existing are fresh.” Missing consolidations are excluded from `all(...)`, so a day with one fresh workbook and another missing workbook can be shown as fresh.

### F6 — Report metadata has many competing sources of truth

**Classification:** Structural risk and drift.

The report catalog is represented independently in:

- `reports.EXPORT_REPORTS`
- `reports.CONSOLIDATE_REPORTS`
- `reports.COMPARE_REPORTS`
- `reports._CONSOLIDATOR_BY_SUBDIR`
- `reports.DISABLED_EXPORT_SUBDIRS`
- `reports.matrix_rows()`
- `matrix.tsn_comparator_for`
- `tsn_library._REPORTS`
- `build/app.spec` `APP_MODULES`
- frontend mock report/consolidator/comparator/matrix fixtures
- `build/check_fake_site.py` report fixtures
- command-menu `.bat` files
- documentation and check inventory tables

The drift is current, not hypothetical:

- Static comparison found 53 Python scripts but 51 names in `APP_MODULES`; `day_matrix`, `matrix`, and `report_library` are absent. Static imports probably still collect them, but the documented “list every flat module” packaging contract is already false.
- The consolidation command menu omits the newer Intersection Summary and Intersection Detail consolidators.
- Frontend mock version/channel/report metadata is stale.
- `reports.py` comments claim one-place report registration and describe an older matrix composition.

The appropriate target is one declarative report descriptor plus narrowly separate descriptors where the concepts genuinely differ, not a universal plugin architecture.

### F7 — Batch resume persists unstable report indices

**Classification:** Reliability and compatibility risk.

The batch manifest stores selected report indices rather than stable report identifiers. Its schema version is fixed at 1 and is not tied to application version or registry identity.

An interrupted batch resumed after a release can select different reports if registry order changes. Current append-only ordering conventions reduce the chance but are an undocumented compatibility protocol. Before any report registry cleanup, current manifests and resume behavior must be characterized and a migration or stable-ID comparison defined.

### F8 — GUI state and worker protocol are implicit and distributed

**Classification:** Structural risk with demonstrated failure history.

`GuiApi` owns a `_task` string, current job, queue, matrix state, export worker, active check, and several cancellation events. Task transitions are spread across:

- `_try_claim_task`
- API entry methods
- `_handle`, approximately lines 462–558
- `_end_task`, approximately lines 560–576
- `_on_error`
- feature-specific terminal handlers
- automatic queue/matrix chaining

The worker protocol consists of untyped `(kind, payload)` tuples. The worker module's protocol comments are stale and omit message types. `_handle` has no final unknown-message diagnostic, so protocol drift can be silently dropped.

A recent terminal-message hotfix in `MatrixBatchExportWorker.finally` demonstrates that “each worker emits exactly one terminal message” is a live correctness invariant, not theoretical style. The right improvement is an explicit state transition table and typed/validated event payloads around the existing model. A generalized async framework or wholesale rewrite is not warranted.

### F9 — Artifact writers do not preserve prior valid files on save failure

**Classification:** Reliability risk.

Settings persistence usually uses temporary-file replacement, but generated XLSX/PDF outputs are commonly written directly to their final path. A process crash, disk-full condition, library write error, or endpoint security interruption can corrupt or truncate the previous valid consolidated/comparison artifact.

This interacts badly with F3 and F5: orchestration checks existence/non-zero size and mtime, not a complete-write marker. No targeted fault-injection coverage was found for workbook promotion.

### F10 — The release pipeline does not test or uniformly guard the exact shipped artifact

**Classification:** Release reliability and trust risk.

The build creates self-test executables with a different entry point/name/console mode, runs those, and later builds the final windowed `TSMIS Exporter.exe` variants. The exact final executable is not executed by the same frozen self-test gate.

In addition:

- `build.ps1` runs pruning and DLP scanning before copying `Start Here.txt` and `IT-README.txt` into the windowed application. Those final additions bypass the stated whole-bundle DLP guard.
- The release workflow contains a signing path for the system-browser ZIP but not an equivalent completed path for the with-browser ZIP.
- The updater authenticates a download with a SHA-256 value obtained from the same GitHub release channel as the asset. Without signed binaries or independently trusted metadata, this detects corruption but not a compromised release channel.
- Advisory `ruff`, `bandit`, and `pip-audit` jobs use `continue-on-error`, so they cannot block a release.
- The fake-site browser check may exit as skipped when no browser is available.

The release design should distinguish source checks, frozen import checks, final-artifact checks, content/DLP checks, and publisher trust. They solve different problems.

### F11 — GUI startup eagerly imports most domain and document-processing code

**Classification:** Performance and packaging structural risk.

Because `gui_api` imports `reports`, and `reports` eagerly imports almost every report adapter/consolidator/comparator, GUI cold start loads modules that are irrelevant to the initial screen. This also increases the amount of code PyInstaller must discover through one import path and makes import-time side effects more dangerous.

Lazy module references or import-on-dispatch are justified at the registry boundary. Splitting every small report adapter into new abstractions is not.

### F12 — Matrix snapshots repeatedly rescan large directory trees

**Classification:** Performance risk.

Everything-matrix age computation can inspect roughly seven reports × six environments × hundreds of route files per snapshot. By-day snapshots scan report/day folders, then revisit overlapping paths for consolidated and day-level state. The frontend requests snapshots after render-relevant actions and run completion.

After comparison, `matrix.read_counts` also reopens and scans the comparison workbook even though `compare_core.run_compare` has already computed counts internally. On large sheets, this is an avoidable second workbook pass.

These are plausible shipped-app latency sources. Actual timing on representative data should precede caching complexity.

### F13 — Frontend mock behavior is a second, drifting backend

**Classification:** Drift and testing risk.

`scripts/ui/app.js` contains the production UI, bridge calls, all rendering/state logic, and a substantial preview mock. Current mismatches include:

- mock version `0.14.2 (preview)` versus current 0.17.1-era code;
- stale browser-channel ordering/default metadata;
- an older comparison discrepancy count;
- reset preview data missing the real backend's concrete `paths` list;
- separately maintained report, matrix, and TSN fixtures.

The direct API call surface currently has good broad parity: nearly all decorated Python bridge methods are called by the JavaScript, and emitted event names are handled. The weaker contract is payload shape and semantic parity. A small generated/static contract fixture is preferable to moving all frontend code into a framework merely to reduce file size.

### F14 — `common.py`, `gui_api.py`, `gui_worker.py`, and `matrix.py` are responsibility clusters

**Classification:** Structural risk.

Examples:

- `common.py`: route parsing, mutable site selection, URL construction, auth state machine, selectors, waits, browser channel probing, login capture, CDP/device profile.
- `gui_api.py`: bridge façade, task gate, file dialogs, settings, updater, reset, support bundle, queueing, auth, all feature orchestration.
- `gui_worker.py`: reset/browser install/environment scan/login/updater/check/export/batch/matrix workers plus promotion primitives.
- `matrix.py`: UI snapshot, freshness, caches, TSN comparator dispatch, consolidation, comparison, and workbook count extraction.

These boundaries justify decomposition. `compare_core.py`, while large, is comparatively cohesive and heavily coupled to exact workbook behavior; splitting it by arbitrary line count would increase regression risk.

## 3. Exact files, symbols, and responsibilities

| File / symbol | Current responsibility | Investigation concern |
|---|---|---|
| `gui_main.py` | Startup, swap handling, logging, webview creation | Exact final frozen startup is not exercised after final build |
| `gui_api.GuiApi` | Entire JS bridge and application coordinator | 3,300+ line stateful façade; task transitions and feature ownership mixed |
| `gui_api.GuiApi._handle` | Worker-message dispatch | Untyped protocol; no unknown-kind diagnostic |
| `gui_api.GuiApi._end_task` | Clears task state and advances queued work | Correctness depends on exactly-once worker terminal events |
| `gui_api.GuiApi._on_matrix_export_done` | Matrix export completion/chaining | Does not require successful payload before downstream compare |
| `gui_worker._swap_store_dir` | Promote staged report directory | Destructive-before-rename; fallback can mix stale/new files |
| `gui_worker.ExportWorker._run_specs` | Export selected reports, staging, retry/promotion | Promotes when routes failed but worker did not raise |
| `gui_worker.BatchWorker.run` | Multi-environment export and resume manifest | Discards `RunResult`; records incomplete environments as done |
| `gui_worker.MatrixBatchExportWorker.run` | Matrix refresh orchestration | “ok” means step returned, not full route completion |
| `reports.py` registries | Report metadata and callable dispatch | Many registries and eager imports; one-place-change claim is false |
| `common.py` | Browser/site/auth/navigation shared runtime | Hidden global/thread-local state and multiple subsystems |
| `common.navigate_with_auth` | Navigation/recovery/auth retry | Complex cancellation/auth/site contract; high branch count |
| `exporter.py` / `exporter_parallel.py` | Sequential/parallel route export | Structured failure is not honored by outer orchestration |
| `matrix._consolidate_store_folder` | Run a report consolidator | Ignores `ConsolidateResult` |
| `matrix._consolidated_stale` | Consolidation freshness | Newest-mtime-only; misses deletions/input-set change |
| `matrix.build_comparison` | Dispatch and cache matrix comparisons | Hardcodes route layout for aggregate TSN rows |
| `matrix.read_counts` | Reopen workbook and count statuses/diffs | Wrong layout at some call sites; duplicate full workbook read |
| `day_matrix.snapshot` | Day columns, cell/header state | Repeated scans; missing report can still yield fresh day header |
| `day_matrix.build_day_cell` | Build/compare a by-day cell | Hardcodes route-keyed comparison count layout |
| `compare_core.run_compare` | Full comparison and workbook generation | High complexity but correctness-sensitive and cohesive |
| `compare_core._write_summary` | Summary workbook rendering | Exact labels/formulas/layout are compatibility contracts |
| `consolidate_xlsx_base.consolidate_xlsx` | Generic workbook consolidation | “ok with skipped/failed inputs” cannot be distinguished structurally |
| `consolidate_tsmis_highway_log_pdf` | PDF parsing and consolidation | Stale-geometry/skipped-line telemetry mitigates but does not prove completeness |
| `settings.py` | Settings schema-by-convention and persistence | Mixed domains, duplicated writers, no explicit migration/version model |
| `batch_manifest.py` | Resume state | Persists unstable report indices |
| `tsn_library._REPORTS` | TSN datasets and builders | Duplicates report metadata/dispatch |
| `updater.py` | Discovery, download, staging, swap helper | Trust, rollback, timeout, and validation gaps |
| `build/app.spec` `APP_MODULES` | PyInstaller hidden-import inventory | Manual list already omits current flat modules |
| `build/build.ps1` | Environment setup, PyInstaller, pruning, gates | Reused mutable venv; final artifact/content not fully gated |
| `.github/workflows/release.yml` | CI build/sign/release | Signing asymmetry; advisory checks cannot block |
| `scripts/ui/app.js` | UI behavior, state, mock backend | 5,000-line mixed production/mock source and semantic drift |

## 4. Sources of truth and contracts that currently drift

| Contract | Competing representations | Current evidence of drift |
|---|---|---|
| Report identity/capabilities | `reports.py`, `matrix.py`, `tsn_library.py`, batch files, fake-site fixtures, UI mock | Intersection consolidators missing from console menu; matrix/registry comments stale |
| Packaged Python modules | import graph versus `build/app.spec:APP_MODULES` | `matrix`, `day_matrix`, and `report_library` absent from manual list |
| Browser channels/defaults | `common.BROWSER_CHANNELS`, settings metadata, UI mock, setup text | Mock channel order/default is stale |
| Application version | `version.py`, UI mock, docs | Mock reports 0.14.2-era preview |
| Worker protocol | emitted `(kind, payload)` values, `GuiApi._handle`, comments/docs | Handler covers current values, but comments omit values and unknown kinds disappear |
| JS bridge contract | decorated Python methods, direct JS calls, event payloads, mock | Method/event-name parity is broadly good; payload/semantic parity is not enforced |
| Comparison layout | adapter `has_route`, generated columns, `matrix.read_counts` call sites | Aggregate TSN callers force route-keyed layout |
| Consolidation completion | `ConsolidateResult.status`, summary strings, file existence | Matrix ignores result and treats surviving old file as usable |
| Export completion | `RunResult.failed`, staging promotion, batch manifest, UI payload | Outer layers treat normal return as complete |
| Freshness | input files, consolidated mtime, comparison sidecars | File-set identity/deletion is absent |
| Batch resume identity | report list ordering and persisted integer indices | Registry reorder changes manifest meaning |
| Settings schema | defaults, setters, UI fields, existing JSON | No schema version/migration; validation is distributed |
| Shipped bundle trust | GitHub release metadata, checksum, optional signing | Checksum and asset share trust root; with-browser signing path incomplete |
| Audit/roadmap status | roadmap checkboxes/comments versus current implementation | Stage/swap described as preserving last-good despite failure-path defects |

## 5. State-machine, threading, persistence, and orchestration risks

### Application state machine

The application effectively has one primary task gate with task values including export, batch, matrix, compare, consolidate, login, environment checks/scans, browser install, and reset. It also has an active check that can exist outside the gate. The actual state graph is encoded procedurally rather than declared.

Required characterization before moving code:

- Which operations are mutually exclusive?
- Which background checks may overlap a primary task?
- Which task owns each cancellation event?
- Which terminal messages clear which state?
- Which terminal states trigger another queued task?
- What happens when a worker posts an error and then a terminal message?
- What UI event order is relied on by `app.js`?

Adding a transition assertion/log is lower risk than immediately replacing threads with another concurrency model.

### Site/environment state

`common.set_site` controls process-global environment state, with thread-local pinning used in some parallel/background contexts. Batch and matrix workers are safe partly because the task gate serializes environment changes. That serialization is a critical hidden invariant.

Any future concurrency, worker pooling, or “run comparisons while exporting” feature must not inherit global site state accidentally. Environment identity should increasingly be passed through immutable job context, but browser/auth behavior must be characterized before removing the existing globals.

### Cancellation

Cancellation is cooperative and uneven:

- navigation and some retry loops poll cancellation;
- report-selection waits and recovery paths can remain unresponsive for their full timeout;
- stop latency can therefore be dominated by a 60-second wait/auth budget;
- reset consumes its confirmation token before finding that the task gate is busy.

The v0.18.0 work should define cancellation checkpoints and bounded stop latency per operation. It should not assume a forced thread kill is safe around browser automation or workbook writes.

### Queue and chaining

`GuiApi` owns a job queue and matrix auto-chaining. The chain currently interprets “not cancelled” as sufficient to proceed. Completion needs a richer state than boolean success because partial exports and partial consolidation are meaningful.

A useful normalized terminal model would distinguish:

- success/complete;
- success with warnings/partial;
- no data;
- cancelled;
- failed before output;
- failed while preserving previous output.

This can be introduced as a contract before reorganizing files.

### Persistence

Persistence is fragmented:

- settings use mostly atomic JSON replacement, with older setters duplicating the implementation;
- auth state is plaintext and written directly;
- batch manifests and matrix/report caches have separate ad hoc writers;
- generated workbook/PDF artifacts are generally written directly to final paths;
- settings combine preferences, environment URLs, absolute external paths, matrix layout/modes, and day columns in one unversioned document.

Absolute paths and user-selected destinations need explicit ownership semantics. Reset currently limits deletion to known child names and previews paths, which is safer than deleting the selected root. It still assumes a child named `ssor-prod`, `comparisons`, etc. is application-owned. A marker/manifest or stronger destination contract would make deletion and promotion defensible.

## 6. Testing and characterization gaps

The repository has substantial regression coverage, but it is an ad hoc collection of `build/check_*.py` scripts with direct monkeypatching and print-based pass/fail behavior. There is no conventional test runner organization, fixture layer, coverage report, or unit/integration taxonomy. This makes it difficult to know which contracts are protected and encourages broad checks to become expensive.

Highest-priority missing characterizations:

1. `RunResult.failed` must prevent staging promotion, batch-manifest completion, matrix “ok,” and automatic downstream compare.
2. Store promotion failure at each step must leave one complete usable generation and report an explicit failure.
3. Locked/stale staging directories must not be resumed or promoted silently.
4. Consolidator `status="error"` with an existing prior output must not compare or cache the prior output as newly current.
5. Consolidator partial-input outcomes need machine-readable orchestration behavior.
6. Aggregate Ramp Summary and Intersection Summary TSN workbooks need matrix/day count readback tests using `has_route=False`.
7. Deleting a route input must invalidate consolidated and comparison freshness.
8. Missing one report's consolidation must make the day-level header incomplete/stale.
9. Batch manifests must survive registry additions/reordering or reject incompatible state clearly.
10. Every emitted worker message kind should be accepted, validated, and terminal exactly once; unknown kinds should be diagnosed.
11. UI mock and backend should share contract tests for reset preview, settings, report metadata, matrix rows, and event payload shapes.
12. Workbook/PDF write failure should preserve the previous valid final artifact.
13. Exact final frozen application variants should receive post-build import/startup/content checks.
14. DLP/content checks should run after all files are copied into each final bundle.

Existing test caveats:

- `check_b3_batch.py` tests the successful `_swap_store_dir` primitive, not outcome gating or failure atomicity.
- Matrix checks focus on dispatch, guards, caching, successful flows, and cancellation. They explicitly leave live consolidation→comparison correctness to work-PC verification.
- `check_day_matrix.py` does not cover a non-cancelled `ok=False` export completion or the aggregate count layout.
- Browser selector coverage can skip when a browser is absent.
- Frozen GUI startup can be reported as skipped when hidden webview creation is unavailable.
- Several PDF/report correctness claims still depend on work-PC fixtures and human verification.

The new test structure should preserve the value of current regression scripts. Converting all checks at once would create churn and reduce confidence. New deterministic tests can be added around pure contracts, with wrappers allowing old release gates to continue during migration.

## 7. Build, packaging, dependency, performance, and shipped-app findings

### Build and dependencies

- Direct runtime/build requirements are pinned, but transitive dependencies are not locked with hashes.
- `build.ps1` reuses `build/.venv`, upgrades `pip`, and installs requirements into that reused environment. Retained extras or resolver changes can make builds differ despite unchanged direct pins.
- `APP_MODULES` is manually maintained and already incomplete relative to the flat-module inventory.
- UI asset collection uses filesystem listing rather than an explicit/sorted manifest, a minor reproducibility weakness.
- Bundle pruning removes package tests/docs/metadata based on assumptions. It should remain behind exact frozen-artifact tests; broadening pruning for size alone is risky.
- The system-browser bundle is still large because Python, node driver support, spreadsheet/PDF libraries, and pythonnet-related components are shipped. The with-browser bundle adds the Chromium payload. Import and package evidence should identify genuine removable components before pruning.

### Release workflow

- Self-test and final windowed executables are different PyInstaller products.
- Final copied documentation bypasses the earlier DLP gate.
- Optional signing is not symmetrically completed for both published variants.
- Lint, static security, and dependency audit checks are advisory.
- The release design does not currently provide a trusted publisher identity to updater users.

### Runtime performance

Potentially high-value, measurable improvements:

- lazy-load report/consolidation/comparison modules after initial GUI display;
- avoid repeated scans of unchanged report directories during one snapshot;
- return structured comparison counts from `compare_core` instead of reopening the produced workbook;
- preserve workbook read-only/streaming behavior where feasible;
- profile `compare_core` matching and summary generation on representative 50k-row inputs before changing algorithms.

Do not optimize by:

- caching without an invalidation model stronger than the current mtime model;
- parallelizing browser/report work beyond the site/auth invariants;
- replacing report-specific parsers with a generic parser before fixture characterization;
- removing packaged modules based only on import grep.

### Shipped-app quality

Shipped behavior—not just source organization—would improve from:

- accurate incomplete/partial states rather than green completion;
- a transactional last-good refresh;
- visible, structured warnings for skipped consolidation inputs;
- bounded cancellation latency;
- reliable matrix discrepancy counts for aggregate reports;
- less cold-start import work;
- clearer updater publisher trust and rollback diagnostics;
- synchronized preview/mock behavior;
- current console menus if batch files remain supported.

## 8. Security and reliability findings

### Security

1. **Unsigned release/update chain:** SHA-256 from the same release channel is integrity checking, not publisher authentication.
2. **Plaintext auth state:** browser auth state is stored as readable JSON without OS-protected encryption or an explicit restrictive ACL.
3. **Edge login CDP exposure:** persistent login opens an unauthenticated loopback debugging port for the duration of login. Loopback reduces exposure but does not eliminate local-process access.
4. **Updater extraction:** ZIP extraction relies on library behavior and lacks an explicit member-path policy check.
5. **Support bundle future leakage:** current sensitive files are excluded and URL fragments are scrubbed, but scalar settings are broadly serialized. A future secret-like setting could enter diagnostics unless allowlisted.
6. **User-selected destination ownership:** deletion/promotion trusts known child names rather than an ownership marker.

Positive controls that should be preserved:

- site overrides require HTTPS, approved `*.ca.gov` hosts, and expected environment parameters;
- workbook formula-injection defenses are present in consolidation/comparison paths;
- failure dumps and private auth/profile data are excluded from support bundles;
- logging scrubs URL fragments before output;
- reset now previews concrete scoped paths instead of deleting an arbitrary selected root.

### Reliability

- Updater download completeness is weaker when release metadata omits size or checksum, and download has no retry/resume strategy.
- Swap helper waits only a short interval for the old process and does not re-hash the staged executable immediately before installation.
- Partial rollback can relaunch while reporting that the previous version was kept even when restoration failed.
- Release discovery is capped to the first 100 releases.
- Update-helper logs are read in full and have no rotation.
- Webview cache cleanup happens before the frozen-development distinction.
- Direct output saves can damage prior workbooks/PDFs.
- Broad `except Exception` use is widespread. Many occurrences are justified best-effort cleanup or boundary handling, but high-value orchestration paths should preserve exception type/context and distinguish warnings from terminal failure.

## 9. Previous audit-finding dispositions

This section reconciles `code-review/AUDIT-phase3-0a4c071.md` with current HEAD. The audit predates roughly 17,000 lines of subsequent change, including major matrix, TSN, day, bridge, and worker growth. “Fixed” below means the original defect is materially addressed in current code, not that the surrounding subsystem needs no work.

### P1 findings

| Audit finding | Current disposition |
|---|---|
| Auth retry may navigate to wrong environment | **Fixed.** Recovery now verifies required site parameters. Preserve this invariant during site-context refactoring. |
| Transient export click can produce empty output | **Fixed/mitigated.** A retry path exists. Characterize before changing browser flow. |
| Reset can delete selected root | **Substantially fixed.** Deletion is scoped to known child paths and previewed. Ownership-marker risk remains. |
| All-empty export can appear green | **Fixed at the direct export-result layer.** However, partial failed routes can still be promoted/recorded complete through F1. |
| Update chain lacks publisher trust | **Open.** Same-channel checksum is not signature trust. |

### P2 findings

| Audit finding | Current disposition |
|---|---|
| Auth state is plaintext | **Open.** |
| Edge CDP endpoint is unauthenticated | **Open.** |
| Report selection uses substring-first matching | **Open.** |
| Highway Summary error path can look empty/successful | **Fixed.** Positive marker and diagnostic handling were added. |
| Parallel crash plus cancellation can hang/lose result | **Fixed.** Preserve terminal-message behavior. |
| Reconciliation is too permissive | **Fixed.** Strict reconciliation exists. |
| Report-error detail is swallowed | **Mitigated/fixed.** Logging and positive report markers exist. |
| Auto-consolidation deletes last-good before successful refresh | **Partially addressed, not closed.** Staging exists, but failed routes can be promoted and swap is not transactional. |
| Worker message kinds can be silently ignored | **Open.** `_handle` still has no unknown-kind diagnostic. |
| Highway-log PDF stale geometry, skipped lines, and row-accounting gaps | **Mitigated, not proved closed.** Telemetry/warnings were added, but parsing can still carry geometry and no independent completeness oracle exists. |
| Ramp Summary duplicate/misattribution | **Open.** Duplicate `-O OUTSIDE CITY` and source-only wording remain. |
| Updater incomplete download validation | **Open.** |
| Updater short death wait / staged executable trust | **Open.** |
| Updater partial rollback claims success | **Open.** |

### P3 findings

| Audit finding | Current disposition |
|---|---|
| Run-report action omitted when per-route list is empty | **Open.** |
| Report selection not re-armed each route | **Open.** |
| PDF empty-save backstop absent | **Open.** |
| JavaScript wait result unvalidated | **Open.** |
| Worker documentation describes obsolete Tk architecture | **Open.** |
| Reset junction/symlink concerns | **Open but reduced by scoped deletion.** Requires Windows-specific verification. |
| Support bundle could leak future scalar secret | **Open.** |
| Overwrite confirmation has TOCTOU window | **Open/low severity.** |
| `device_ok` inferred from any completed run | **Open.** |
| Login wait loop/busy wait | **Behavior remains; invariant is now documented.** Low concern if cancellation always signals completion. |
| Reconciliation cancellation emitted twice | **Fixed.** |
| Reset token consumed before busy check | **Open.** |
| Cross-environment side-label truncation can remove distinguisher | **Open.** |
| Greedy matching quality cliff at 8+ duplicates | **Open.** |
| Combined-sheet fixed coordinates | **Open.** |
| Updater CI/final-artifact gap | **Open.** |
| Download timeout/retry weakness | **Open.** |
| ZIP extraction path policy implicit | **Open.** |
| Only first 100 releases inspected | **Open.** |
| Staged executable not re-hashed at swap | **Open.** |
| Updater log has no rotation/full-file read | **Open.** |
| Development webview cache cleanup | **Open.** |

### Audit candidates that should remain rejected or low priority

Do not revive rejected observations as release-driving defects without new evidence:

- duplicated settings-write code is a maintainability smell, not proof of immediate data loss;
- environment mutation in `paths` is intentional behavior;
- same-second mtime cache behavior alone was not shown to be a practical defect—the stronger file-set/deletion problem in F5 is independently evidenced;
- free-port TOCTOU is low priority because fallback behavior exists;
- broad exception handlers should be reviewed by boundary and consequence, not mechanically eliminated.

## 10. Areas where sweeping changes are justified

“Sweeping” here means coherent subsystem work with compatibility gates, not a rewrite.

1. **Report descriptor/source-of-truth consolidation.** The current manual synchronization burden spans runtime, packaging, UI mock, TSN dispatch, checks, and console tooling.
2. **Export/consolidate/compare outcome model.** The application needs a shared machine-readable terminal vocabulary so partial work cannot masquerade as complete work.
3. **Transactional artifact lifecycle.** Staging, validation, promotion, last-good preservation, ownership, and cleanup should follow one proven pattern for report directories and generated workbooks.
4. **GUI task/state protocol.** Define the state graph and event payload contracts, then divide `GuiApi` by feature coordinators while retaining one public bridge façade.
5. **Persistence schema and atomic writer layer.** Settings, manifests, caches, auth state, and output artifacts need explicit schemas/versions and appropriate security/atomicity.
6. **Release trust and exact-artifact verification.** Final bundles, copied content, signatures, and updater verification need one end-to-end definition of “publishable.”
7. **Frontend production/mock separation.** The mock should consume shared/generated contracts and fixtures instead of maintaining a parallel semantic backend inside the production file.

Each of these areas crosses many files because the existing contract itself is cross-cutting. Piecemeal cosmetic moves would leave the risk intact.

## 11. Areas that should remain stable or isolated

1. **Comparison workbook semantics.** `compare_core` labels, formulas, colors, sheet layouts, matching behavior, sort order, and Route-1 regression canary are user-visible compatibility contracts.
2. **Report-specific parsing rules.** Fixed-width/PDF/workbook peculiarities should remain isolated behind adapters. Shared infrastructure is appropriate; forced parser unification is not.
3. **Authentication and selector behavior.** Current environment verification, retry, and cancellation protections should be characterized before interface movement.
4. **Existing output paths and names.** Users, batch scripts, resume state, and matrix caches may depend on current directory/report names.
5. **Settings compatibility.** Unknown-key preservation and existing defaults should remain readable while schema/version support is introduced.
6. **Support-bundle redaction and formula-injection defenses.**
7. **PyInstaller pruning rules.** Change only with exact final-bundle import/startup tests.
8. **Single-primary-task invariant.** Keep until environment/browser state no longer depends on global mutable selection.

## 12. Refactors likely to cause more harm than benefit

- Rewriting the application around `asyncio` solely to replace threads.
- Introducing a generic plugin framework for a fixed set of report types.
- Splitting every report adapter or every `GuiApi` method into one-class-per-action abstractions.
- Reimplementing `compare_core` before capturing representative workbook fixtures and exact output contracts.
- Replacing report-specific PDF parsers with one generic parser.
- Converting the entire check suite to a new test runner in one release.
- Renaming report subdirectories, row keys, settings keys, or batch-manifest meaning without migration.
- Parallelizing environment exports before removing process-global site selection.
- Adding persistent filesystem caches before defining invalidation from input identity.
- Aggressively removing PyInstaller modules to chase bundle size without final-artifact testing.
- Treating all `except Exception` occurrences as equivalent lint failures.
- Migrating the frontend to a framework merely because `app.js` is large; first separate production state/bridge/mock concerns and prove the payload contracts.

## 13. Suggested sequencing constraints, but not a final plan

These are dependency constraints Claude's plan should respect:

1. Characterize current export, promotion, consolidation, comparison, and matrix payload contracts before moving their code.
2. Fix partial-success interpretation and aggregate-count defects before relying on new orchestration abstractions.
3. Define complete/partial/cancelled/failed result models before decomposing workers or `GuiApi`.
4. Make promotion atomic and test failure paths before changing resume/freshness behavior.
5. Introduce stable report IDs and manifest compatibility before consolidating/reordering registries.
6. Establish a canonical report descriptor before generating packaging/UI/test representations from it.
7. Add input-set freshness characterization before adding scan caches.
8. Preserve old settings/manifests while adding schema versions and migrations.
9. Separate bridge façade from feature coordinators incrementally so JavaScript API names and event order stay stable.
10. Capture workbook and PDF golden/semantic fixtures before modifying `compare_core` or parser internals.
11. Build exact-artifact checks before changing hidden imports, pruning, or dependency composition.
12. Complete final-bundle content scanning and signing policy before claiming an end-to-end trusted release path.
13. Measure GUI cold start, matrix snapshot time, and large comparison time before setting performance targets.
14. Keep work-PC/live-site verification as a distinct acceptance gate; do not make deterministic CI depend on the live service.

## 14. Questions Claude’s final plan must answer

1. What exact condition allows staged report data to replace last-good data?
2. How will partial route failures be represented in direct export, batch, matrix, manifest, and UI state?
3. What is the recovery guarantee if Windows blocks delete, rename, or replacement?
4. How will consolidator “partial” and “error” results prevent stale-output comparison?
5. Which stable identifier replaces persisted report indices, and how are existing manifests handled?
6. What becomes the canonical report/capability descriptor, and which artifacts are derived from it?
7. How will comparison layout metadata reach count readers without hardcoded `has_route` assumptions?
8. What input fingerprint invalidates consolidation and comparison after deletion or file-set change?
9. What is the explicit primary-task state graph, and which overlaps remain legal?
10. How are unknown, duplicate, late, and malformed worker messages handled?
11. Which parts of `GuiApi`, `gui_worker`, `common`, and `matrix` move first, and what compatibility tests protect each move?
12. How will generated XLSX/PDF files be written without sacrificing the previous valid artifact?
13. What settings/auth/manifest schema versions and migrations are required?
14. How will auth state be protected without breaking portable or enterprise deployments?
15. What exactly is tested on the final windowed system-browser and with-browser artifacts?
16. Which published artifacts are signed, and what does the updater verify before swap?
17. How will final copied bundle content pass DLP and dependency/license checks?
18. Which performance measurements justify lazy loading, scan caching, or comparison-result changes?
19. Which existing audit findings are explicitly in scope, deferred with rationale, or obsolete?
20. What work-PC acceptance evidence is required for report correctness, cancellation, auth, and updater behavior?

## 15. Lower-confidence claims Claude must independently verify

These findings have strong source-level rationale but need runtime or environment evidence:

- The magnitude of cold-start improvement from lazy report imports.
- Matrix snapshot latency on representative route/day counts and real storage.
- Windows behavior when antivirus, Explorer preview, Excel, or another process holds live/staging files.
- Junction/reparse-point behavior within all reset and promotion paths.
- Whether PyInstaller currently collects the three modules missing from `APP_MODULES` in both final variants.
- Whether the final with-browser artifact is unsigned in the actual configured SignPath workflow.
- Whether the hidden webview self-test skips or runs in the release runner environment.
- The practical compatibility and enterprise-policy implications of DPAPI or another auth-state protection mechanism.
- PDF Highway Log completeness after stale-geometry warnings on representative source documents.
- The real-world frequency of 8+ duplicate-key groups affected by greedy matching.
- Whether direct-final workbook writes have produced observed corruption in field use.
- Whether same/older timestamp replacement occurs on the target network/filesystem; deletion invalidation remains a valid logical gap regardless.
- Exact bundle-size savings available from dependency/import changes.
- Stop latency on the live site's slowest report-selection and auth-recovery paths.
- Current user reliance on `.bat` menus and old manifest/settings formats.

## 16. Concise checklist for Claude’s synthesis

- [ ] Treat F1–F4 as correctness defects, not optional cleanup.
- [ ] Preserve last-good data across route, consolidation, write, and promotion failures.
- [ ] Define structured terminal outcomes before decomposing orchestration.
- [ ] Add stable report identity before registry reordering.
- [ ] Make report metadata canonical and derive manual mirrors where practical.
- [ ] Characterize state transitions, event payloads, cancellation, and exactly-once terminal behavior.
- [ ] Fix freshness around input identity/deletion before caching scans.
- [ ] Preserve comparison workbook and parser contracts with fixtures.
- [ ] Version and migrate settings/manifests rather than resetting them.
- [ ] Test exact final frozen variants after all files are copied and pruned.
- [ ] Address signing/updater trust separately from checksum integrity.
- [ ] Keep deterministic CI separate from live/work-PC acceptance.
- [ ] Measure startup, snapshot, and comparison costs before optimizing.
- [ ] Explicitly disposition every still-open audit item selected for or deferred from v0.18.0.
- [ ] Avoid framework rewrites and abstraction for its own sake.

The central architectural conclusion is that v0.18.0 should not be framed primarily as file splitting. The urgent problem is that completion, freshness, ownership, and promotion are implicit contracts spread across workers, matrices, manifests, caches, and the UI. Once those contracts are made explicit and regression-tested, decomposition of the large modules becomes substantially safer and more valuable.
