# P6 Codex review

## Review round 1

### 1. Verdict: `PASS WITH FIXES`

P6 is correctly scoped to the approved persistence-hardening work: settings writer
deduplication, atomic auth-file write with a best-effort owner ACL, and a support-bundle
settings allowlist. The product diff is limited to `scripts/settings.py`,
`scripts/common.py`, one support-bundle line in `scripts/gui_api.py`, one new check, and
one CI line. I found no persisted-format migration, frontend/backend contract, matrix,
cache, manifest, packaging-inventory, or output correctness regression.

The phase is not ready for approval because the ACL helper silently treats a non-zero
`icacls` result as success. That does not break sign-in, but it undermines the security
deliverable's diagnostics and contradicts the phase's "failure logged and ignored"
contract.

### 2. Blocking findings

None.

### 3. Required fixes

#### P6-R01 — Required — `_restrict_to_owner` does not detect or log failed `icacls` results

- **Affected phase area:** P6 auth-at-rest ACL hardening and diagnostic quality;
  `scripts/common.py::_restrict_to_owner`; `build/check_persistence.py::test_auth_atomic_and_acl`.
- **Repository evidence:** `_restrict_to_owner` invokes `subprocess.run([...], check=False)` but
  discards the returned `CompletedProcess` (`scripts/common.py:420-424`). Only exceptions are logged
  (`scripts/common.py:425-426`). A normal `icacls` process returning non-zero therefore produces no
  log and is indistinguishable from a successful ACL tighten. The P6 report and coordination record
  describe the ACL step as best-effort where failures are logged and ignored, but the check only
  exercises an exception from `subprocess.run` (`build/check_persistence.py:133-135`), not a non-zero
  return code.
- **Independent diagnostic:** I patched `common.subprocess.run` to return an object with
  `returncode = 5` and captured `common.log`; `_restrict_to_owner("dummy.tmp")` emitted no
  "ACL tighten skipped" or failure log. This is a logging/security-hardening gap, not an auth-file
  format or sign-in regression.
- **Exact correction expected:** Capture the `subprocess.run` result, and if its `returncode` is
  non-zero, log an informational ACL-skip/failure message with the return code while still allowing
  `save_auth_state` to continue. Add a focused `check_persistence` assertion that a non-zero
  `icacls` result is logged/treated as best-effort failure, alongside the existing exception and
  invalid-`USERNAME` checks. Do not make `save_auth_state` fail on an ACL command failure.

### 4. Non-blocking recommendations

#### P6-A01 — Recommended — Clarify support-bundle wording now or in P11 so it says allowlisted settings

- **Affected phase area:** support-bundle user/maintainer wording;
  `scripts/gui_api.py::GuiApi.save_support_bundle`; P11 documentation reconciliation.
- **Repository evidence:** The support bundle now writes `settings.support_bundle_settings()` into
  the manifest (`scripts/gui_api.py:3449`), but nearby text still says the bundle includes "current
  settings" (`scripts/gui_api.py:3415-3417`) and the user-facing completion log says "settings"
  (`scripts/gui_api.py:3472-3474`). That was accurate when the manifest embedded
  `settings.all_settings()`, but P6 intentionally changed this to an allowlisted subset.
- **Exact correction expected:** Either adjust the P6 product wording to say "allowlisted settings"
  / "selected diagnostic settings", or explicitly carry this to P11's documentation pass. This is
  non-blocking because the generated bundle no longer leaks `batch_dest`, `site_urls`, or future
  default keys; it is a wording/expectation issue, not a data leak.

### 5. Verification performed

- Confirmed `docs/planning/v0.18.0/00-coordination.md` marks P6 `awaiting_review` with baseline
  `c0cfa39`.
- Read the approved P6 plan section, the current P6 Claude report, and relevant prior phase context
  for settings, artifact atomicity, and support-bundle behavior.
- Inspected the product diff from `c0cfa39`, excluding `docs/planning/**`: modified
  `.github/workflows/checks.yml`, `scripts/common.py`, `scripts/gui_api.py`, `scripts/settings.py`,
  plus new `build/check_persistence.py`.
- Confirmed no P6 diff in protected/out-of-scope areas checked here: `scripts/compare_core.py`,
  `scripts/matrix.py`, `scripts/day_matrix.py`, `scripts/tsn_library.py`,
  `scripts/report_catalog.py`, `scripts/paths.py`, `scripts/updater.py`, `build/app.spec`,
  `version.py`, and frontend app files.
- Ran and passed:
  - `python -B -X utf8 build/check_persistence.py` through a stderr-capturing wrapper:
    return code 0 and stderr length 0.
  - `python -B -X utf8 build/check_gui_bridge.py`
  - `python -B -X utf8 build/check_report_library.py`
  - `python -B -X utf8 build/check_b3_batch.py`
  - `python -B -X utf8 build/check_export_engine.py`
  - `python -B -X utf8 build/check_matrix_bridge.py`
  - `python -B -X utf8 build/check_day_matrix.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_no_misspelling.py`
  - `python -B -X utf8 -m py_compile scripts/settings.py scripts/common.py scripts/gui_api.py build/check_persistence.py`
  - `git diff --check c0cfa39 -- . ':(exclude)docs/planning/**'`
- Ran an independent temp-directory support-bundle smoke using `GuiApi.save_support_bundle` with
  patched roots and a fake window. The generated `manifest.txt` included allowlisted values and did
  not include a planted `batch_dest`, `site_urls`, or `future_secret_token`.
- Ran an independent diagnostic for P6-R01: a fake non-zero `icacls` return produced no log.
- Did not run build scripts, PyInstaller, frozen self-tests, browser/GUI launches, live TSMIS,
  credentials, browser profiles, private report data, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

Not yet. Claude should remediate P6-R01 and may optionally apply or explicitly defer P6-A01, then
return P6 for another review.

## Review round 2

### 1. Verdict: `PASS`

P6 is ready for phase approval. The round-1 required finding (**P6-R01**) is resolved: `_restrict_to_owner`
now captures the `icacls` process result, logs a non-zero return code with diagnostic output, and still
allows `save_auth_state` to complete. The round-1 recommendation (**P6-A01**) is also resolved: the
support-bundle wording now describes "selected diagnostic settings" / an allowlisted settings subset.

The product diff remains scoped to the approved P6 persistence hardening: settings writer deduplication,
atomic auth-file write with best-effort owner ACL, support-bundle settings allowlist, one persistence
check, and CI wiring. I found no new persisted-format migration, frontend/backend contract regression,
matrix/cache/output change, packaging-inventory change, or unrelated scope.

### 2. Blocking findings

None.

### 3. Required fixes

None.

- **P6-R01 - Resolved.** `scripts/common.py::_restrict_to_owner` now logs non-zero `icacls` results
  (`rc=...` plus the first output line) while preserving the best-effort/no-lockout behavior. The
  added `build/check_persistence.py` assertion covers this path.

### 4. Non-blocking recommendations

None.

- **P6-A01 - Resolved.** `scripts/gui_api.py::GuiApi.save_support_bundle` now says the bundle contains
  selected/allowlisted diagnostic settings, and the generated manifest uses that wording.

### 5. Verification performed

- Confirmed `docs/planning/v0.18.0/00-coordination.md` still marks **P6** `awaiting_review` with
  baseline `c0cfa39`.
- Read the approved P6 plan section, the current P6 Claude report including round-1 remediation, and
  the prior P6 Codex review.
- Inspected the product diff from `c0cfa39`, excluding `docs/planning/**`: modified
  `.github/workflows/checks.yml`, `scripts/common.py`, `scripts/gui_api.py`, `scripts/settings.py`,
  plus new untracked `build/check_persistence.py`.
- Confirmed the current P6 diff does not touch the protected areas checked here: `compare_core`,
  matrix/day-matrix engines, TSN library, report catalog, paths, updater, `app.spec`, `version.py`,
  or frontend app files.
- Ran and passed:
  - `python -B -X utf8 build/check_persistence.py`
  - `python -B -X utf8 build/check_gui_bridge.py`
  - `python -B -X utf8 build/check_report_library.py`
  - `python -B -X utf8 build/check_b3_batch.py`
  - `python -B -X utf8 build/check_export_engine.py`
  - `python -B -X utf8 build/check_matrix_bridge.py`
  - `python -B -X utf8 build/check_day_matrix.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_no_misspelling.py`
  - `python -B -X utf8 -m py_compile scripts/settings.py scripts/common.py scripts/gui_api.py build/check_persistence.py`
  - `git diff --check c0cfa39 -- . ':(exclude)docs/planning/**'`
- Ran an independent ACL diagnostic with `common.subprocess.run` patched to return `returncode=5`
  and stdout `"icacls: Access is denied."`: `save_auth_state` wrote the auth file, `_restrict_to_owner`
  targeted the temporary file before rename, and `common.log.info` included both `non-zero icacls result`
  and `rc=5`.
- Ran an independent support-bundle smoke with a temporary config containing `batch_dest`, `site_urls`,
  and `future_secret_token`: the generated `manifest.txt` used the selected-diagnostic-settings wording,
  included allowlisted values, and did not include those sensitive/future keys or values.
- Did not run the complete `build/check_*.py` suite, build scripts, PyInstaller, frozen self-tests,
  browser/GUI launches, live TSMIS, credentials, browser profiles, private report data, or shared
  release artifacts.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval for P6.
