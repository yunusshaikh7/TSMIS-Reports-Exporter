# P4 Codex review

## Review round 1

### 1. Verdict: `PASS WITH FIXES`

P4 is within its approved structural scope, and independent inspection confirms that the
current catalog points to the same export specs, consolidators, comparison adapters, and
auto-consolidators as the baseline. The new Intersection console choices are also correctly
wired. The phase is not ready for approval, however, because its central equivalence, batch,
and mock tripwires prove less than the report claims, and several P4-owned descriptions now
contradict the implementation.

### 2. Blocking findings

None. No current report-routing, persistence, packaging-inventory, or console-dispatch defect
was found in the P4 product wiring.

### 3. Required fixes

#### P4-R01 — Required — Descriptor equivalence omits execution identity and full lazy-reference resolution

- **Affected phase area:** P4 descriptor-equivalence check, Protected contract, and completion
  claim; `build/check_report_catalog.py:test_golden_equivalence` and
  `test_dynamic_import_resolvable`.
- **Repository evidence:** The frozen `_EXPORT` snapshot records only key/label/format
  (`build/check_report_catalog.py:50-58`), and the export assertion checks only that the selected
  spec has the expected `subdir` (`:124-127`). `_COMPARE` records no adapter identity
  (`:69-85`), and its assertion checks only key/label/kind/group (`:130-131`).
  `_CONSOLIDATOR_BY_SUBDIR` has no independent frozen oracle at all: `:113-114` compares a
  catalog-derived view back to the same catalog. Finally, the claimed
  `module:function` resolution check splits off the function name and calls only
  `find_spec(module)` (`:150-158`).
- **Independent diagnostic:** Replacing the first comparison adapter with a different adapter,
  or mapping `ramp_summary` to the Ramp Detail consolidator, while rebuilding the derived
  `reports` views produced zero DERIVE or GOLDEN failures. Thus a wrong report implementation
  can pass the check advertised as proving behavior-neutral equivalence. The current workspace
  identities were separately checked and are correct, and all six current TSN builder
  functions are callable; this is a missing tripwire, not a discovered current misroute.
- **Exact correction expected:** Extend the independent baseline to assert each export key's
  exact expected `ReportSpec`, every comparison key's exact expected module/adapter identity,
  and every auto-consolidator subdir's exact expected module. Resolve every TSN
  `module:function` with `import_module` plus `getattr` and assert the target is callable.
  Include negative characterization proving a wrong adapter, wrong auto-consolidator, and
  missing function each fail.

#### P4-R02 — Required — `.bat` parity checks module presence, not menu dispatch or registry order

- **Affected phase area:** P4 `.bat`↔registry parity and R1-M01 closure;
  `build/check_report_catalog.py:test_bat_parity`.
- **Repository evidence:** The check gathers a set of every
  `python scripts\consolidate_*.py` line and compares that set with the catalog
  (`build/check_report_catalog.py:137-147`). It does not connect displayed choices
  (`4. consolidate (combine reports).bat:16-23`) to their `goto` targets (`:32-39`), or those
  labels to the invoked modules (`:48-84`), and set comparison discards order. The actual
  eight-choice file is correctly wired today.
- **Independent diagnostic:** Swapping only the choice-4 and choice-5 `goto` targets in memory
  left all three current parity conditions true, even though the displayed Intersection
  choices would execute the opposite consolidators.
- **Exact correction expected:** Parse and assert the ordered chain
  `displayed number/label -> choice goto -> label block -> Python module` against ordered
  `cat.CONSOLIDATE`, including uniqueness and reachability. Add a negative swapped-dispatch
  case that fails.

#### P4-R03 — Required — Key-only mock parity is not equivalent to the approved generated metadata contract

- **Affected phase area:** P4 approved “mock report list generated” change, independent
  display/order snapshot, and the report's deviation/CT-13 claims;
  `build/check_report_catalog.py:test_mock_parity`.
- **Repository evidence:** `_mock_keys` extracts only `key` fields and the three assertions
  compare only ordered key lists (`build/check_report_catalog.py:161-175`). The production
  bridge exposes export key/label/format/disabled, consolidate key/label/format, group
  id/label, and comparison key/label/kind/group/subdir/file-picker labels
  (`scripts/gui_api.py:1040-1072`). The mock independently repeats those fields in
  `scripts/ui/app.js:3716-3738` and `:4271-4315`.
- **Independent diagnostic:** Changing mock export label/format and comparison
  label/kind/group in memory left all three mock-parity assertions green. Therefore the
  key-only check does not provide the “same drift protection” claimed in the phase report
  and is not the full backend-snapshot/frontend-expectation CT-13 planned for P9.
- **Exact correction expected:** Either implement the approved generated report metadata, or
  make the documented deviation genuinely equivalent by independently comparing every
  catalog/bridge-owned mock field, including group metadata and comparison routing fields.
  Correct the phase report so a P4 key-list check is not presented as completed P9 CT-13
  payload parity.

#### P4-R04 — Required — P4-owned documentation and verification claims contradict the new dependency boundary

- **Affected phase area:** P4 documentation updates and supported verification claims;
  `report_catalog.py`, `reports.py`, `check_report_catalog.py`, `docs/architecture.md`,
  `docs/reports.md`, and the Claude phase report.
- **Repository evidence:** `report_catalog.py:19-23` says importing the catalog never pulls
  pdfplumber/openpyxl, `reports.py:14-16` calls the registry import-light,
  `check_report_catalog.py:20` claims “no browser / openpyxl,” and
  `docs/architecture.md:87-88` repeats the import-light claim. In reality,
  `report_catalog.py:27-51` eagerly imports the export, consolidation, and comparison
  implementation modules. A fresh-process import took about 1.01 seconds and loaded
  `openpyxl`, `pdfplumber`, `playwright`, and `PIL` (705 modules). It did not launch a
  browser or perform application runtime I/O, but it is not dependency-light.
  Separately, the P4-touched add-a-comparison recipe still directs maintainers to edit the
  now-derived `reports.COMPARE_REPORTS`/`COMPARE_KEYS` (`docs/reports.md:149`), the TSN recipe
  still directs edits to derived `tsn_library._REPORTS` (`:191`), and `:143` says the already
  registered Intersection Summary consolidator is “still to come.”
- **Exact correction expected:** Describe the modules accurately as console-free and as not
  launching a browser or doing application runtime I/O, while acknowledging the retained
  eager implementation/dependency imports; remove the false no-openpyxl/pdfplumber claim
  from source, check, canonical docs, and the phase report/remediation. Update the three
  directly P4-invalidated `docs/reports.md` instructions/facts to point to
  `CompareEntry`/`TsnEntry` in `report_catalog.py` and the existing Intersection Summary
  consolidator. Broader historical table reconciliation may remain in P11.

### 4. Non-blocking recommendations

None. In particular, this review does not require redesigning the eager catalog imports or
splitting the catalog again; truthful documentation and complete contract checks are enough
for P4.

### 5. Verification performed

- Confirmed coordination marks P4 `awaiting_review`; baseline and current HEAD are
  `5defe9e356e6cd3172e2ccbe5adbf1bde4e92f0c`.
- Inspected the complete product worktree diff from that baseline, excluding
  `docs/planning/**`: eight modified tracked files plus new
  `scripts/report_catalog.py` and `build/check_report_catalog.py`.
- Independently passed:
  - `build/check_report_catalog.py`
  - `build/check_report_library.py`
  - `build/check_matrix.py`
  - `build/check_intersection_gate.py`
  - `build/check_b2_autoconsolidate.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_stable_ids.py`
  - `build/check_gui_bridge.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_compare_routing.js`
  - `node build/check_mx_partial_render.js`
  - product `git diff --check`
- Independently verified exact current export-spec, consolidator-module,
  comparison-adapter, and auto-consolidator identities; all match the intended baseline.
- Verified all six current TSN `module:function` builder targets resolve to callable objects.
- Ran in-memory negative diagnostics proving the current golden check misses a wrong comparison
  adapter and wrong auto-consolidator, the `.bat` check misses swapped choice dispatch, and the
  mock check misses changed labels/formats/kinds/groups.
- Measured a fresh `import report_catalog` and inspected its loaded dependency modules, producing
  the P4-R04 evidence above.
- Did not run the complete check suite, source/frozen build gates, PyInstaller, a GUI/browser,
  live TSMIS, credentials, profiles, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may remediate P4-R01 through P4-R04 and return P4 for another review. Under
the coordination rule requiring a final `PASS`, P4 must not be approved/committed and P5/P6
must not begin from this review round.

## Review round 2

### 1. Verdict: `PASS WITH FIXES`

The current catalog still points to the correct baseline specs, consolidators, comparison
adapters, and TSN builders. The remediation materially strengthens execution-identity and
callable-resolution coverage, and all targeted product checks remain green. Round 1 is only
partially resolved, however: three advertised negative/parity guards still accept concrete
bad variants, the dependency-documentation sweep missed directly invalidated statements,
and the new mock check performs shared runtime writes and starts background threads.

### 2. Blocking findings

None. No current report execution misroute, persisted-data migration defect, packaging
inventory omission, or shipped `.bat` dispatch error was found.

### 3. Required fixes

#### P4-R01 — Required — Execution identity is now guarded, but the claimed negative self-tests remain vacuous

- **Status:** Partially resolved. The production assertions now correctly pin export specs,
  consolidate modules, comparison adapters, auto-consolidators, and callable TSN builder
  targets.
- **Repository evidence:** `_negative_self_tests` merely asserts that known unrelated objects
  are different (`build/check_report_catalog.py:186-199`); it does not pass a mutated catalog
  or builder reference through the production predicates. With `cat.COMPARE[0]` changed to
  the Ramp Detail adapter, all four “negative self-tests” still passed, while
  `test_golden_equivalence` separately and correctly failed the adapter-identity assertion.
  Thus the core guard works, but the remediation/report claim that the permanent negative
  tests prove those tripwires is unsupported.
- **Exact correction expected:** Factor the identity and builder-resolution assertions into
  testable helpers and run wrong-adapter, wrong-auto-consolidator, wrong-spec, and missing-
  function inputs through those same helpers, asserting rejection. Alternatively remove the
  self-test/RED-proof claims, but P4-R01's round-1 requested negative characterization must
  still be supplied before approval.

#### P4-R02 — Required — The `.bat` parser still ignores displayed labels and collapses duplicate executable branches

- **Status:** Partially resolved. The normal eight-choice module chain is now checked in
  registry order and is correct.
- **Repository evidence:** `_parse_bat` extracts menu numbers only and converts dispatches and
  blocks directly to dictionaries (`build/check_report_catalog.py:202-208`). It therefore
  does not compare the displayed labels to `cat.CONSOLIDATE`, and duplicate choice lines or
  duplicate label blocks are silently collapsed before the “unique” assertions at
  `:223-226`. Independent in-memory variants with (a) choice 4 displayed as
  “Intersection Detail,” (b) a first wrong choice-4 dispatch followed by the current correct
  line, and (c) a first wrong `:intersection_summary` block followed by the current correct
  duplicate all passed the four main parity conditions. CMD executes the first matching
  branch/block, so the latter two are behaviorally significant.
- **Exact correction expected:** Parse ordered menu `(number, displayed label)` rows and raw
  ordered dispatch/block occurrences without dictionary collapse. Require exactly one
  dispatch and exactly one target block per choice, compare displayed labels and invoked
  modules to ordered `cat.CONSOLIDATE`, and add negative cases for a wrong label, duplicate
  dispatch, and duplicate block in addition to the swapped-goto case.

#### P4-R03 — Required — Mock parity is broader but still not field-for-field and misses a second routing registry

- **Status:** Partially resolved. Export/consolidate key-label-format, group id-label, and
  comparison key-label-kind-group now match the current bridge.
- **Repository evidence:** `test_mock_parity` compares only those selected tuples
  (`build/check_report_catalog.py:272-290`). The production payload also carries export
  `idx`/`disabled` and comparison `subdir`/`file_a_label`/`file_b_label`
  (`scripts/gui_api.py:1052-1072`). The mock file additionally has a separate
  `CONS_REPORTS` routing list used by `consByKey` and consolidation behavior
  (`scripts/ui/app.js:3725-3742,4904,4975-4978`), but the check reads only the duplicated
  `cons_reports` payload at `:4272-4281`.
- **Independent diagnostic:** Changing a compare `file_a_label`, changing
  `reports[].disabled`, or changing the separate `CONS_REPORTS` label left every current
  mock-parity assertion green. The last mutation changes the mock's output path and displayed
  run text. The mock comparison rows also omit production `subdir` fields, so the report's
  “field-for-field” statement is presently false.
- **Exact correction expected:** Compare the full report-list bridge contract:
  exports `(key, idx, label, fmt, disabled)`, consolidation rows, groups, and comparisons
  including `subdir` and both picker labels, with explicit normalization only where absence
  is intentionally equivalent to a documented default. Also assert the separate
  `CONS_REPORTS` routing list equals the mock payload/catalog or remove that duplicate source.
  Add negative cases for the omitted fields.

#### P4-R04 — Required — The dependency-boundary correction missed P4-invalidated source comments and canonical docs

- **Status:** Partially resolved. The primary `report_catalog.py`, `reports.py`,
  `tsn_library.py`, check header, and registry-section wording now accurately acknowledge
  eager third-party imports.
- **Repository evidence:** `scripts/gui_api.py:2185` and `:2579` still say lazy
  `tsn_library` imports cause “no pdfplumber pull,” but P4 makes `tsn_library` import
  `report_catalog`, which eagerly reaches pdfplumber/openpyxl. The P4-touched canonical
  architecture document repeats the same false statement at
  `docs/architecture.md:352-353`. This contradicts both the implementation and the
  remediation's claimed residual sweep.
- **Exact correction expected:** Correct these three directly P4-invalidated statements to
  distinguish lazy builder invocation from eager dependency import. Re-run a targeted
  residual search and narrow the remediation claim to what was actually checked; broader
  unrelated historical drift may remain assigned to P11.

#### P4-R05 — Required — The new catalog check mutates runtime state and starts background threads

- **Affected phase area:** Verification safety and the claim that
  `check_report_catalog.py` performs no runtime I/O.
- **Repository evidence:** `test_mock_parity` constructs `gui_api.GuiApi`
  (`build/check_report_catalog.py:274-277`). Its constructor reads persisted settings,
  calls `tsn_library.ensure_layout()` (`scripts/gui_api.py:154-165`), and starts the
  `gui-pump` and `gui-send` threads (`:214-215`). `ensure_layout` creates directories and
  writes per-report hints/README files (`scripts/tsn_library.py:174-202`). Setting
  `_started = True` happens only after construction and suppresses later startup checks; it
  does not undo these constructor effects. A patched diagnostic observed one
  `ensure_layout` call and both thread starts. This contradicts
  `build/check_report_catalog.py:23` and makes a blocking CI/check command unsafe to run as a
  supposedly read-only parity check on a developer installation.
- **Exact correction expected:** Obtain the backend report metadata through a pure helper
  used by `GuiApi.get_initial_state`, or isolate every constructor write/thread seam before
  construction. The preferred correction is a pure payload builder so the check neither
  writes user data nor starts workers. Add a guard proving the parity test performs no
  filesystem writes, background-thread starts, browser/network activity, or persisted
  setting changes, and correct the check's I/O description.

### 4. Non-blocking recommendations

None. These fixes should remain narrow verification/documentation corrections; they do not
justify redesigning the catalog or moving unrelated GUI state in P4.

### 5. Verification performed

- Confirmed P4 remains `awaiting_review`; baseline and current HEAD remain
  `5defe9e356e6cd3172e2ccbe5adbf1bde4e92f0c`.
- Re-read the approved P4 contract, Claude's original report plus round-1 remediation, and
  Codex review round 1.
- Inspected the complete product diff from the P4 baseline while excluding
  `docs/planning/**`; scope remains the approved catalog, registry views, `.bat`, packaging
  inventory, CI wiring, and narrow docs.
- Ran `check_report_catalog.main()` with `tsn_library.ensure_layout` and thread starts patched
  out to avoid the new shared-state mutation: all current assertions passed.
- Independently passed:
  - `build/check_report_library.py`
  - `build/check_matrix.py`
  - `build/check_intersection_gate.py`
  - `build/check_b2_autoconsolidate.py`
  - `build/check_stable_ids.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_no_misspelling.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_compare_routing.js`
  - `node build/check_mx_partial_render.js`
  - product `git diff --check`
- Reconfirmed that the actual catalog's execution identities and all six builder callables are
  correct.
- Ran in-memory diagnostics demonstrating the still-green wrong-label/duplicate-branch
  `.bat` variants, omitted mock-field/routing variants, and vacuous negative-self-test
  behavior described above.
- Did not run the complete check suite, the unpatched side-effecting catalog check, source or
  frozen build gates, PyInstaller, a GUI/browser, live TSMIS, credentials, profiles, or shared
  release artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may remediate P4-R01 through P4-R05 and return P4 for review round 3.
Under the coordination rule requiring a final `PASS`, P4 must not be approved/committed and
no dependent phase may begin.

## Review round 3

### 1. Verdict: `PASS WITH FIXES`

P4-R01, P4-R03, P4-R04, and P4-R05 are resolved. The catalog's current execution identities,
full mock metadata checks, dependency-boundary wording, and pure bridge-payload extraction
all passed independent review. P4-R02 remains narrowly open because the `.bat` parser still
does not enumerate all raw label definitions, allowing a behaviorally active duplicate label
to remain invisible to every main parity assertion.

### 2. Blocking findings

None. The actual checked-in eight-choice batch menu is correctly labelled and dispatches each
choice to the intended consolidator.

### 3. Required fixes

#### P4-R02 — Required — Raw duplicate labels with intervening commands still bypass parity

- **Status:** Still open, narrowed. Display labels, numeric dispatch rows, immediate runnable
  blocks, first-match dispatch, and the existing negative variants are now checked correctly.
- **Repository evidence:** `_parse_bat` recognizes a block only when a label is followed
  immediately by a `python scripts\consolidate_*.py` line
  (`build/check_report_catalog.py:232-236`). `_blocks_exact` therefore counts only those
  matched pairs (`:256-259`), not all raw `:<label>` definitions that CMD can target.
- **Independent diagnostic:** An in-memory variant inserted a first
  `:intersection_summary` label followed by a `rem` line and the wrong Intersection Detail
  Python command, then retained the current second `:intersection_summary` plus correct
  command. All five main conditions remained true: menu order, exact dispatch rows, exact
  parsed block count, label parity, and module-chain parity. In CMD the `goto` reaches the
  first label and executes the wrong command (then falls through to the second block), so
  this is not a cosmetic parser edge.
- **Exact correction expected:** Parse every raw batch label occurrence independently of its
  block body. Require each dispatched target label to occur exactly once, then inspect that
  target's commands up to the next label and require exactly the intended consolidator
  invocation before exit/fall-through. Add a negative case with an intervening `rem` or
  other command before a wrong Python invocation, proving the raw duplicate-label variant
  fails. Preserve the existing label, duplicate-dispatch, immediate-duplicate-block, and
  swapped-goto checks.

### 4. Non-blocking recommendations

None.

Prior finding dispositions:

- **P4-R01 — Resolved.** Mutated spec/adapter/module/builder inputs now pass through the same
  helper predicates as the production assertions and are rejected.
- **P4-R03 — Resolved.** Export, consolidation, group, comparison picker metadata, the
  separate `CONS_REPORTS` routing list, and bridge-only subdirs are now explicitly checked
  or documented.
- **P4-R04 — Resolved.** The cited `gui_api.py` and canonical architecture statements now
  distinguish lazy builder invocation from eager dependency import; the targeted residual
  search is clean.
- **P4-R05 — Resolved.** `_report_list_payload()` is a pure module-level builder used by
  `get_initial_state`; the check no longer constructs `GuiApi`. Independent write-call
  instrumentation observed zero filesystem mutations, no thread starts, and unchanged Git
  status.

### 5. Verification performed

- Confirmed P4 remains `awaiting_review`; baseline and current HEAD remain
  `5defe9e356e6cd3172e2ccbe5adbf1bde4e92f0c`.
- Re-read the approved P4 contract, Claude's report through round-2 remediation/addendum,
  and Codex review rounds 1-2.
- Inspected the complete product diff from the baseline, excluding planning files. The only
  added product scope since round 2 is the narrow pure payload extraction in
  `scripts/gui_api.py`, which preserves the existing `get_initial_state` fields.
- Independently passed:
  - `build/check_report_catalog.py` (47 assertions)
  - `build/check_gui_bridge.py`
  - `build/check_intersection_gate.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_compare_routing.js`
  - `node build/check_mx_partial_render.js`
  - product `git diff --check`
- Confirmed the catalog check leaves the porcelain worktree status unchanged.
- Ran the check under independent write instrumentation covering built-in/Path writes,
  directory creation, unlink, and `os.replace`; zero write calls were observed.
- Re-ran mutated-input diagnostics for adapter identity, export-spec identity, and missing
  builder targets; all are now rejected by the production helpers.
- Reproduced the still-green raw duplicate-label `.bat` variant described in P4-R02.
- Did not run the complete check suite, source/frozen build gates, PyInstaller, a GUI/browser,
  live TSMIS, credentials, profiles, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may apply the narrow P4-R02 parser correction and return P4 for review
round 4. Under the coordination rule requiring a final `PASS`, P4 must not be
approved/committed and no dependent phase may begin.

## Review round 4

### 1. Verdict: `PASS WITH FIXES`

The round-3 raw-label correction works: every label is now enumerated, the previously
invisible duplicate-label decoy is rejected, and the actual menu remains correctly wired.
P4-R02 is still narrowly open because block termination is not modeled. A missing `exit /b`
allows CMD to fall through into the next consolidator while all current parity assertions
remain green.

### 2. Blocking findings

None. The checked-in batch file currently terminates every consolidator block with
`exit /b 0`; no current shipped dispatch defect was found.

### 3. Required fixes

#### P4-R02 — Required — Parity still permits fall-through into the next consolidator

- **Status:** Still open, narrowed to block termination. Raw duplicate labels, wrong labels,
  duplicate/extra dispatches, first-match targets, and sole consolidator identity are now
  covered correctly.
- **Repository evidence:** `_parse_bat` records only consolidator module names for each block
  (`build/check_report_catalog.py:245-269`). `_bat_chain` accepts a block whenever it contains
  exactly one consolidator before the next label (`:286-297`); neither function records or
  requires an `exit /b`, `goto :eof`, or other terminating transfer.
- **Independent diagnostic:** Removing only `exit /b 0` from the
  `:intersection_summary` block left all five main parity conditions true: menu order,
  exact dispatches, target-label uniqueness, displayed labels, and the ordered module chain.
  Under CMD semantics, after the Summary command and `pause`, execution falls through the
  `:intersection_detail` label and runs the Detail consolidator too.
- **Exact correction expected:** Retain each raw block's command/control-flow information and
  require every dispatched block to invoke exactly its intended consolidator and terminate
  before the next label (at minimum accept the repository's `exit /b` form; explicitly define
  any other accepted terminal forms). Add a negative case that removes a block terminator
  and prove the parity check rejects the resulting fall-through. Preserve all existing
  P4-R02 negative cases.

### 4. Non-blocking recommendations

None.

P4-R01, P4-R03, P4-R04, and P4-R05 remain resolved.

### 5. Verification performed

- Confirmed P4 remains `awaiting_review`; baseline and current HEAD are
  `5defe9e356e6cd3172e2ccbe5adbf1bde4e92f0c`.
- Re-read the approved P4 contract, Claude's report through round-3 remediation, and Codex
  review rounds 1-3.
- Inspected the round-3 `.bat` parser rewrite and the complete product diff from the baseline,
  excluding planning files.
- Independently passed:
  - `build/check_report_catalog.py` (49 assertions)
  - `build/check_gui_bridge.py`
  - `build/check_intersection_gate.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_no_misspelling.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_compare_routing.js`
  - `node build/check_mx_partial_render.js`
  - product `git diff --check`
- Reproduced the round-3 duplicate-label decoy and confirmed the new parser reports two raw
  labels, rejects target uniqueness, and resolves the wrong first block.
- Independently removed one `exit /b 0` in memory and confirmed every current main batch
  parity condition still passes despite CMD fall-through.
- Did not run the complete check suite, source/frozen build gates, PyInstaller, a GUI/browser,
  live TSMIS, credentials, profiles, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may apply the narrow P4-R02 termination check and return P4 for review
round 5. P4 must not be approved/committed and no dependent phase may begin until a review
returns `PASS`.

## Review round 5

### 1. Verdict: `PASS`

P4-R02 is resolved. The batch parity gate now models raw labels, first-match dispatch,
consolidator identity, and unconditional block termination, and independently rejects the
previously green fall-through case. All prior P4 findings remain resolved. The phase meets
its approved catalog, compatibility, console-menu, packaging-inventory, documentation, and
verification boundaries.

### 2. Blocking findings

None.

### 3. Required fixes

None.

Prior finding dispositions:

- **P4-R01 — Resolved.** Independent metadata and execution-identity oracles cover export
  specs, consolidation modules, comparison adapters, auto-consolidators, and callable TSN
  builder references, with mutated-input negatives through the production predicates.
- **P4-R02 — Resolved.** The `.bat` check covers displayed labels, exact dispatch rows, every
  raw target label, first-match block behavior, sole intended consolidator, and an
  unconditional terminator before the next label. Wrong labels, duplicate dispatches/labels,
  swapped targets, hidden decoy blocks, and removed terminators are rejected.
- **P4-R03 — Resolved.** Mock report metadata is checked field-for-field against the pure
  bridge payload, including picker labels and the separate consolidation routing registry.
- **P4-R04 — Resolved.** P4-invalidated dependency-boundary and registry-maintenance
  documentation is accurate.
- **P4-R05 — Resolved.** Catalog parity uses the pure `_report_list_payload()` path and
  performs no filesystem write, background-thread start, or `GuiApi` construction.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Confirmed P4 remains `awaiting_review`; baseline and current HEAD are
  `5defe9e356e6cd3172e2ccbe5adbf1bde4e92f0c`.
- Re-read the approved P4 contract, Claude's report through round-4 remediation, and Codex
  review rounds 1-4.
- Inspected the complete product diff from the phase baseline, excluding planning files.
  Scope remains the approved catalog/view derivation, Intersection `.bat` entries, parity
  gate, packaging inventory, pure report-list payload extraction, CI wiring, and narrow docs.
- Independently passed:
  - `build/check_report_catalog.py` (52 assertions)
  - `build/check_gui_bridge.py`
  - `build/check_intersection_gate.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - `build/check_no_misspelling.py`
  - `python -m compileall -q scripts build version.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_compare_routing.js`
  - `node build/check_mx_partial_render.js`
  - product `git diff --check`
- Independently removed the `:intersection_summary` terminator in memory. The new
  `_all_blocks_terminate` guard returned false while the module chain remained equal to the
  registry, confirming the termination check is real and distinct.
- Confirmed accepted terminators are explicit unconditional forms and conditional/commented
  lookalikes are rejected.
- Did not run the complete check suite, source/frozen build gates, PyInstaller, a GUI/browser,
  live TSMIS, credentials, profiles, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

**Yes.** Claude may mark P4 approved and proceed toward the phase commit under the
coordination rules. It must not begin the next phase in the same turn as the P4 commit.
