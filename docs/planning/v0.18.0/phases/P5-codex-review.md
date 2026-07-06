# P5 Codex review

## Review round 1

### 1. Verdict: `PASS WITH FIXES`

P5 is narrowly within the approved family-1 boundary. The four public
`build_into` entry points and catalog builder strings remain intact, the new dependency
edge is acyclic, protected comparator/schema files are unchanged, and an independent
old-vs-new harness found the six success/partial cases semantically identical. No current
report-output, completion, persistence, packaging-inventory, or comparison regression was
found.

The phase is not ready for approval because its permanent characterization check proves
materially less than the phase report and coordination record claim. The report also uses
the expressly rejected phrase “byte-identical” for a semantic XLSX comparison.

### 2. Blocking findings

None.

### 3. Required fixes

#### P5-R01 — Required — The regression check does not lock the semantic identity claimed for the refactor

- **Affected phase area:** P5 protected behavior and completion criteria;
  `build/check_tsn_normalizer.py::_wb`, `test_detail_loaders`,
  `test_summary_loaders`, and `test_shared_skeleton`; the verification claims in
  `docs/planning/v0.18.0/phases/P5-claude-report.md`.
- **Repository evidence:** `_wb` records only sheet title, cell values, and alignment
  (`build/check_tsn_normalizer.py:60-69`). The check never asserts the baseline header
  font or fill even though the shared factory owns both at
  `scripts/tsn_library.py:404-410`. Detail results are checked only for status/completion,
  a “2 routes” substring, and workbook shape (`build/check_tsn_normalizer.py:93-102`);
  exact `message`, `summary_lines`, output filename, and event log are not asserted.
  Summary cases similarly omit exact result text, warning text/order, total lines, and
  event logs (`:120-154`). `test_shared_skeleton` uses partial predicates for the
  dependency/missing-raw/parse errors and does not exercise the factory’s
  `PermissionError` save contract at `scripts/tsn_library.py:458-464`
  (`build/check_tsn_normalizer.py:159-208`).
- **Independent diagnostic:** I loaded each baseline loader from
  `git show c86dc78:scripts/<module>.py` beside the current loader and compared all
  `ConsolidateResult` fields, emitted log lines, sheet/rows, and every header cell’s
  alignment/font/fill for Ramp Detail, Intersection Detail, and full/partial versions
  of both summaries. All **6/6** current cases matched. I also compared the dependency,
  missing-raw, cancel, parse-error, and save-`PermissionError` result contracts; they
  matched. Thus this is a missing durable tripwire, not a discovered current output
  defect.
- **Unsupported/misleading claim:** The report says the new check “locks” each loader’s
  result and styled workbook (`P5-claude-report.md:48-51,112-114,168`), while those
  fields are only covered by an uncommitted one-off harness. It also calls the result
  “byte-identical” at `P5-claude-report.md:25,95,123`, contrary to the approved plan’s
  semantic-identity rule; the described harness loaded and compared workbook semantics,
  not XLSX ZIP bytes.
- **Exact correction expected:** Strengthen `check_tsn_normalizer.py` with independent,
  frozen expected signatures for all six cases: every `ConsolidateResult` field, exact
  event log, sheet/header/data rows, and every header cell’s alignment/font/fill. Lock
  exact shared error/cancel strings and add an atomic-save `PermissionError` case that
  proves the prior artifact is retained and no temp file remains. Do not make the oracle
  from the same keyword values passed to `build_normalized`. Correct the phase report and
  coordination remediation to say **semantically identical**, describe the compared
  dimensions precisely, and distinguish the permanent check from the one-off baseline
  harness.

### 4. Non-blocking recommendations

#### P5-A01 — Recommended — Preserve the old dependency-gate coverage for the symbols now imported by the factory

- **Affected phase area:** dependency compatibility in the four `tsn_load_*` shims and
  `tsn_library._write_normalized_workbook`.
- **Repository evidence:** Each current shim probes only
  `from openpyxl import Workbook` (for example
  `scripts/tsn_load_ramp_detail.py:15-19`), while the factory later imports
  `WriteOnlyCell`, `Alignment`, `Font`, and `PatternFill`
  (`scripts/tsn_library.py:399-401`) outside the parse and save handlers. The baseline
  loaders’ import gates also covered the style classes (and both Intersection loaders
  covered `WriteOnlyCell`). A partial/broken openpyxl installation or frozen omission can
  therefore pass `_DEPS_OK` and raise instead of returning the existing friendly
  dependency result.
- **Exact correction expected:** Either make the shared dependency probe cover every
  workbook symbol the factory needs, or translate an `ImportError` from workbook creation
  into the shim’s existing `deps_msg`; add a focused negative check. Keep this centralized
  rather than restoring four copies of the writing skeleton.

### 5. Verification performed

- Confirmed coordination marks P5 `awaiting_review` with baseline/current HEAD
  `c86dc78a760cb3e6aeb1d5e618d38d0d2546f149`.
- Inspected the complete product diff from the baseline, excluding
  `docs/planning/**`: five modified product modules, one new check, and one CI-line change.
- Confirmed `compare_core.py`, all four affected `compare_*_tsn` modules,
  `report_catalog.py`, and `build/app.spec` are unchanged.
- Independently passed:
  - `build/check_tsn_normalizer.py`
  - `build/check_tsn_outcome.py`
  - the five `check_compare_*_tsn.py` checks present for TSN
  - `build/check_report_catalog.py`
  - `build/check_report_library.py`
  - `build/check_matrix_tsn.py`
  - `build/check_parallel_reconcile.py`
  - `build/check_tsn_description_leak.py`
  - `build/check_import_direction.py`
  - `build/check_app_modules.py`
  - AST parsing of every changed/new Python file
  - product `git diff --check`
- Ran the independent six-case old-vs-new semantic harness and targeted shared-branch
  comparisons described in P5-R01.
- Did not run the complete check suite, build scripts, PyInstaller, frozen self-tests,
  browser/GUI checks, live TSMIS, credentials, profiles, private report data, or shared
  release artifacts.

### 6. Whether Claude may proceed toward phase approval

**Not yet.** Claude may remediate P5-R01 and optionally P5-A01, then return P5 for another
review. P5 should remain `awaiting_review` until the durable semantic-identity guard and
verification wording are corrected.

## Review round 2

### 1. Verdict: `PASS WITH FIXES`

The P5 product diff remains within the approved family-1 boundary: the four
`tsn_load_*:build_into` shims are preserved, the shared skeleton is centralized in
`tsn_library.build_normalized`, comparator/schema files remain untouched, and targeted
TSN canaries are green. The prior P5-A01 dependency-backstop recommendation is resolved.

The round-1 required characterization finding is substantially improved but not fully
closed. The permanent check now locks the six success/partial signatures, result fields,
event logs, rows, and header styles, but its atomic-save `PermissionError` branch still
does not exercise `artifact_store.atomic_save` or prove temp cleanup. The check also emits
ignored openpyxl/lxml cleanup exceptions while still exiting 0, which makes the reported
"all green / ASCII-clean" verification misleading.

### 2. Blocking findings

None. I found no current report-output, completion, comparison, packaging-inventory, or
dependency-direction regression.

### 3. Required fixes

#### P5-R01 — Required — The save-error tripwire still does not prove the atomic-save contract it claims

- **Affected phase area:** P5 characterization / protected artifact behavior;
  `build/check_tsn_normalizer.py::test_shared_skeleton`; the verification claims in
  `docs/planning/v0.18.0/phases/P5-claude-report.md`.
- **Repository evidence:** The remediated check patches
  `artifact_store.atomic_save` itself to immediately raise `PermissionError`
  (`build/check_tsn_normalizer.py:246-249`). That bypasses the implementation whose
  temp-file cleanup is being claimed (`scripts/artifact_store.py:82-98`) and therefore
  cannot prove a `.tmp-*` sibling is removed. The "no stray file" assertion records and
  compares `raw.iterdir()` (`build/check_tsn_normalizer.py:245,254-255`), but atomic
  save temps are created beside `out_path`, not in the raw input folder. On an actual run,
  `python -B -X utf8 build/check_tsn_normalizer.py` prints `ALL TSN-NORMALIZER CHECKS
  PASSED` and then emits ignored `openpyxl`/`lxml` cleanup exceptions from the unsaved
  write-only workbook created before the monkeypatched `atomic_save` raises.
- **Independent diagnostic:** Driving the real `artifact_store.atomic_save` by
  monkeypatching `artifact_store.os.replace` to raise `PermissionError` did preserve the
  prior artifact and left no `.tmp-*` sibling in the output directory. So this is still a
  missing durable/noisy tripwire, not a discovered product defect.
- **Exact correction expected:** Change the permanent PermissionError test to exercise the
  real `artifact_store.atomic_save` path, for example by monkeypatching
  `artifact_store.os.replace` to raise after `workbook.save(tmp)`. Assert the prior output
  bytes are retained and the output directory contains no `.tmp-*` sibling. The test must
  exit cleanly without ignored openpyxl/lxml cleanup exceptions. Keep the existing exact
  friendly error-message assertion.

### 4. Non-blocking recommendations

None new.

Previously recommended **P5-A01** is resolved: `scripts/tsn_library.py:456-464` now
translates `ImportError` from `_write_normalized_workbook` into the shim's dependency
message, and `build/check_tsn_normalizer.py:256-261` locks that backstop.

### 5. Verification performed

- Confirmed `docs/planning/v0.18.0/00-coordination.md` still marks P5
  `awaiting_review` with baseline `c86dc78`.
- Inspected the product diff from `c86dc78` excluding `docs/planning/**`: modified
  `.github/workflows/checks.yml`, `scripts/tsn_library.py`, the four `scripts/tsn_load_*`
  shims, plus new `build/check_tsn_normalizer.py`.
- Confirmed the protected comparator path remains untouched by the product diff:
  `compare_core.py`, the affected `compare_*_tsn.py` modules, `report_catalog.py`, and
  `build/app.spec` have no P5 changes.
- Ran and passed:
  - `python -B -X utf8 build/check_tsn_normalizer.py` (exit 0, but with ignored
    openpyxl/lxml cleanup exceptions after the pass banner; see P5-R01)
  - `python -B -X utf8 build/check_tsn_outcome.py`
  - `python -B -X utf8 build/check_compare_ramp_detail_tsn.py`
  - `python -B -X utf8 build/check_compare_ramp_summary_tsn.py`
  - `python -B -X utf8 build/check_compare_intersection_detail_tsn.py`
  - `python -B -X utf8 build/check_compare_intersection_summary_tsn.py`
  - `python -B -X utf8 build/check_compare_highway_sequence_tsn.py`
  - `python -B -X utf8 build/check_matrix_tsn.py`
  - `python -B -X utf8 build/check_parallel_reconcile.py`
  - `python -B -X utf8 build/check_tsn_description_leak.py`
  - `python -B -X utf8 build/check_report_catalog.py`
  - `python -B -X utf8 build/check_report_library.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 -m py_compile` on the changed/new Python files
  - `git diff --check c86dc78 -- . ':(exclude)docs/planning/**'`
- Ran an independent temp-directory diagnostic that exercised the real
  `artifact_store.atomic_save` path by forcing `os.replace` to raise `PermissionError`;
  the product retained the prior artifact and removed the temp sibling.
- Did not run build scripts, PyInstaller, frozen self-tests, browser/GUI checks, live
  TSMIS, credentials, profiles, private report data, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

Not yet. Claude should narrow-remediate P5-R01 by fixing the permanent save-error
characterization, then return P5 for another review. No product behavior change appears
necessary unless the corrected test exposes one.

## Review round 3

### 1. Verdict: `PASS`

P5 is ready for phase approval. The implementation remains scoped to the approved
family-1 `tsn_load_*` normalizer collapse, with the old `build_into` entry points and
catalog builder strings preserved. The protected comparator/schema path is still
untouched, the new `tsn_load_* -> tsn_library` dependency edge remains acyclic, and the
targeted TSN canaries are green.

The prior findings are resolved:

- **P5-R01:** Resolved. The permanent normalizer check now locks the six semantic
  signatures and drives the real `artifact_store.atomic_save` save-error path by forcing
  `artifact_store.os.replace` to raise (`build/check_tsn_normalizer.py:242-263`), which
  exercises the real temp sibling creation/cleanup behavior in `scripts/artifact_store.py`
  rather than stubbing `atomic_save`.
- **P5-A01:** Resolved. `scripts/tsn_library.py` translates workbook-symbol
  `ImportError` from `_write_normalized_workbook` into the shim dependency message, and
  `build/check_tsn_normalizer.py` locks that backstop.

### 2. Blocking findings

None.

### 3. Required fixes

None.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Confirmed `docs/planning/v0.18.0/00-coordination.md` still marks P5
  `awaiting_review` with baseline `c86dc78`.
- Read the approved P5 plan section, the current P5 Claude report including round-2
  remediation, and prior P5 Codex review rounds.
- Inspected the product diff from `c86dc78`, excluding `docs/planning/**`: modified
  `.github/workflows/checks.yml`, `scripts/tsn_library.py`, the four `scripts/tsn_load_*`
  shims, plus new `build/check_tsn_normalizer.py`.
- Confirmed no P5 diff in protected comparator/packaging files checked here:
  `scripts/compare_core.py`, the affected `scripts/compare_*_tsn.py` modules,
  `scripts/report_catalog.py`, `build/app.spec`, and frontend app files.
- Ran and passed:
  - `python -B -X utf8 build/check_tsn_normalizer.py` through a stderr-capturing wrapper:
    return code 0 and stderr length 0.
  - `python -B -X utf8 build/check_tsn_outcome.py`
  - `python -B -X utf8 build/check_compare_ramp_detail_tsn.py`
  - `python -B -X utf8 build/check_compare_ramp_summary_tsn.py`
  - `python -B -X utf8 build/check_compare_intersection_detail_tsn.py`
  - `python -B -X utf8 build/check_compare_intersection_summary_tsn.py`
  - `python -B -X utf8 build/check_compare_highway_sequence_tsn.py`
  - `python -B -X utf8 build/check_matrix_tsn.py`
  - `python -B -X utf8 build/check_parallel_reconcile.py`
  - `python -B -X utf8 build/check_tsn_description_leak.py`
  - `python -B -X utf8 build/check_report_catalog.py`
  - `python -B -X utf8 build/check_report_library.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 -m py_compile` on the changed/new Python files
  - `git diff --check c86dc78 -- . ':(exclude)docs/planning/**'`
- Did not run build scripts, PyInstaller, frozen self-tests, browser/GUI checks, live
  TSMIS, credentials, profiles, private report data, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval for P5.
