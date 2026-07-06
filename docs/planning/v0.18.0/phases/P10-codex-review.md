# P10 Codex Review

## Review round 1

### 1. Verdict

`BLOCKED`

### 2. Blocking findings

- **P10-B01 — blocking — staged-update re-verification is still fail-open and incomplete.**
  - **Affected phase area:** P10 updater hardening, §J staged-exe re-hash / user-writable staged update trust boundary.
  - **Repository evidence:**
    - `scripts/updater.py:532-538` writes `UPDATE_DIR / "staged.sha256"` but catches `OSError`, logs a warning, and still returns the staged tree.
    - `scripts/updater.py:570-578` makes `_staged_hash()` return `None` when `staged.sha256` is missing or malformed.
    - `scripts/updater.py:613-630` treats `expected is None` as a warning-only path and proceeds to launch the staged executable.
    - `build/check_updater.py:592-630` covers only “sidecar exists + exe changed” and “sidecar exists + exe unchanged”; it does not cover missing sidecar, malformed sidecar, sidecar write failure, or code-bearing `_internal` tampering.
    - The trust record covers only `staged / _EXE_NAME` (`scripts/updater.py:533-534`, `scripts/updater.py:616`), while the staged onefolder app requires `_internal` and `perform_swap()` later copies allowed bundle items including `_internal` (`scripts/updater.py:82`, `scripts/updater.py:806-809`).
    - Independent diagnostics against the current workspace reproduced both bypasses without touching repository files:
      - Missing `staged.sha256`: `missing_sidecar_allowed=True`, `launch_calls=1`.
      - Valid exe hash but tampered `_internal/app.dll`: `internal_tamper_allowed=True`, `launch_calls=1`.
  - **Why this blocks approval:** P10 was meant to close `staged-exe-launched-from-user-writable-dir-no-recheck`. The final plan requires re-verification immediately before swap, and the Claude report states the staged tree is refused when tampered with. The current implementation still launches from the user-writable staged tree when the trust record is absent/garbled, and it does not verify the code-bearing `_internal` tree that the staged executable depends on.
  - **Exact correction expected:** Make the staged trust record mandatory for newly staged updates. If recording it fails in `download_and_stage()`, fail staging and leave no usable staged tree. In `apply_update_and_restart()`, missing or malformed trust data must fail closed before `_launch_detached()`. Expand the trust record and pre-launch verification to cover the staged bundle contents that can be launched or installed, at minimum `_EXE_NAME` plus `_internal/**` and preferably all `_BUNDLE_ITEMS` recursively. Add regression tests for missing sidecar, malformed sidecar, sidecar write failure, and `_internal` tamper after staging but before launch.

### 3. Required fixes

- Resolve **P10-B01** and rerun the targeted updater tests plus the safe packaging/dependency checks.

### 4. Non-blocking recommendations

- **P10-A01 — recommended — SignPath parity wording remains easy to misread.**
  - **Affected phase area:** P10 release workflow / signing-parity disposition.
  - **Repository evidence:** `docs/planning/v0.18.0/05-claude-final-plan.md:590` says with-browser signing parity is “in workflow design only”; `docs/planning/v0.18.0/phases/P10-claude-report.md:78-82` says parity is already present in workflow design only; `.github/workflows/release.yml:94-119` contains only the system-browser SignPath upload/submit pair and a comment saying to repeat it for the with-browser zip.
  - **Exact correction expected:** Either add the inert with-browser SignPath upload/submit pair now, or keep runtime signing deferred and revise the P10 report/coordination wording so it does not imply implemented signing parity. This is not blocking because signing remains disabled/deferred and the artifact/checksum publication guard is present.

### 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, and `docs/planning/v0.18.0/phases/P10-claude-report.md`; no prior P10 Codex review file existed.
- Inspected product diff from baseline `8605eaf`, excluding `docs/planning/**`. Product changes are the P10 packaging/updater/dependency files plus the two new product files `build/check_build_env.py` and `requirements-build.lock.txt`.
- Ran safe checks:
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_updater.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py --verify-installed` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_no_misspelling.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_import_direction.py` — pass.
  - `git diff --check 8605eaf -- . ':(exclude)docs/planning/**'` — pass.
  - PowerShell AST parse of `build/build.ps1` — pass.
- Ran two read-only/temp-dir updater diagnostics confirming P10-B01.
- Did not run the full `build/check_*.py` suite, `build/full_smoke.py`, `build/build.ps1`, PyInstaller, frozen self-tests, browser/GUI launches, or live TSMIS access.

### 6. Whether Claude may proceed toward phase approval

No. Claude should stay in P10, remediate **P10-B01**, append remediation to the P10 Claude report, and return the phase for another Codex review. Claude may continue implementation within the approved P10 scope to address this blocker.

## Review round 2

### 1. Verdict

`PASS WITH FIXES`

### 2. Blocking findings

None.

- **P10-B01 — resolved.** The current implementation now refuses both bypasses identified in round 1 before launching the staged helper:
  - `scripts/updater.py:385-412` computes `_bundle_digest()` over the staged bundle contents under `_BUNDLE_ITEMS`, including `_internal/**`.
  - `scripts/updater.py:571-582` makes the staged trust record mandatory; digest compute/write failure removes `UPDATE_DIR` and raises `UpdateError`.
  - `scripts/updater.py:660-670` fails closed on a missing/malformed trust record or bundle digest mismatch before `_launch_detached()`.
  - `build/check_updater.py:622-686` covers matching launch, exe tamper, `_internal` tamper, added `_internal` file, missing record, malformed record, and restored record.
  - `build/check_updater.py:688-742` covers staged-record write failure, uncomputable digest, cleanup of the unusable staged tree, and digest sensitivity to `_internal` changes.

### 3. Required fixes

- **P10-R01 — required — live coordination/status text still describes the old fail-open staged-record path.**
  - **Affected phase area:** P10 coordination/status documentation.
  - **Repository evidence:** `docs/planning/v0.18.0/00-coordination.md:194` still summarizes the P10 staged re-hash as “missing record → logs+proceeds, fail-safe,” while the current code now fails closed (`scripts/updater.py:660-664`) and the appended P10 remediation report says the old path is gone (`docs/planning/v0.18.0/phases/P10-claude-report.md:293-296`).
  - **Exact correction expected:** Update the live P10 coordination summary to say the staged trust record is mandatory, covers the whole staged bundle, and missing/malformed/write-failed records fail closed. Do not rewrite earlier historical review rounds; just make the current coordination/status text match the remediated product behavior.

### 4. Non-blocking recommendations

None.

- **P10-A01 — resolved by wording.** The current report/coordination wording no longer claims implemented per-variant SignPath parity; it describes signing as deferred/inert under RM06. No workflow change is required for this phase.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P10-claude-report.md`, and this review file.
- Inspected product diff from baseline `8605eaf`, excluding `docs/planning/**`. The product scope remains the P10 packaging/updater/dependency set plus new `build/check_build_env.py` and `requirements-build.lock.txt`.
- Ran safe checks:
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_updater.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py --verify-installed` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 -m py_compile scripts\updater.py build\check_updater.py build\check_build_env.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_no_misspelling.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_import_direction.py` — pass.
  - `git diff --check 8605eaf -- . ':(exclude)docs/planning/**'` — pass.
  - PowerShell AST parse of `build/build.ps1` — pass.
- Re-ran independent temp-dir probes for the two round-1 bypasses:
  - Missing `staged.sha256`: refused, `launch_calls=0`.
  - Valid recorded digest but tampered `_internal/app.dll`: refused, `launch_calls=0`.
- Did not run the full `build/check_*.py` suite, `build/full_smoke.py`, `build/build.ps1`, PyInstaller, frozen self-tests, browser/GUI launches, or live TSMIS access.

### 6. Whether Claude may proceed toward phase approval

Yes, after applying **P10-R01**. No product-code re-review is required if the only change is the required coordination/status wording correction; if product code changes again, return P10 for another review round.

## Review round 3

### 1. Verdict

`PASS WITH FIXES`

### 2. Blocking findings

None.

- **P10-B01 — resolved.** Carried from round 2. The product implementation still fails closed before launching on missing/malformed staged trust records or staged-bundle tampering, and `build/check_updater.py` passes the bundle-level regression coverage.
- **P10-A01 — resolved.** Carried from round 2. Signing parity wording now states the SignPath path is deferred/inert under RM06.
- **P10-R01 — resolved.** The live P10 coordination row now describes the mandatory whole-bundle staged trust record and fail-closed behavior instead of the old warning-only path.

### 3. Required fixes

- **P10-R02 — required — the P10 report introduced a planning-only product-name typo and now makes its own verification claim false.**
  - **Affected phase area:** P10 phase report, updated verification for the round-2 documentation remediation.
  - **Repository evidence:** `docs/planning/v0.18.0/phases/P10-claude-report.md:364` contains the guarded product-name transposition while saying `check_no_misspelling.py` passed. Running `build\.venv\Scripts\python.exe -B -X utf8 build\check_no_misspelling.py` now fails on that exact planning-report line.
  - **Exact correction expected:** Reword the P10 report line so it does not contain the forbidden product-name typo, rerun `check_no_misspelling.py`, and append a tiny remediation note. No product-code change is needed.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P10-claude-report.md`, and prior P10 Codex review rounds.
- Inspected product diff from baseline `8605eaf`, excluding `docs/planning/**`. Product scope remains the same P10 set: modified `.github/workflows/checks.yml`, `.github/workflows/release.yml`, `build/build.ps1`, `build/check_updater.py`, `requirements.txt`, `scripts/updater.py`, plus new `build/check_build_env.py` and `requirements-build.lock.txt`.
- Ran safe checks:
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_updater.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py --verify-installed` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 -m py_compile scripts\updater.py build\check_updater.py build\check_build_env.py` — pass.
  - `git diff --check 8605eaf -- . ':(exclude)docs/planning/**'` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_no_misspelling.py` — fail, planning-report-only, recorded as **P10-R02**.
- Did not run the full `build/check_*.py` suite, `build/full_smoke.py`, `build/build.ps1`, PyInstaller, frozen self-tests, browser/GUI launches, or live TSMIS access.

### 6. Whether Claude may proceed toward phase approval

Yes, after applying **P10-R02**. No product-code re-review is required if the only change is the required P10 report wording correction and `check_no_misspelling.py` passes; if product code changes again, return P10 for another review round.

## Review round 4

### 1. Verdict

`PASS`

### 2. Blocking findings

None.

- **P10-B01 — resolved.** Carried from round 2 and rechecked by `build/check_updater.py`; staged-bundle verification is mandatory, whole-bundle, and fail-closed before launch.
- **P10-A01 — resolved.** Carried from round 2; signing parity wording now describes SignPath/runtime signing as deferred/inert under RM06.
- **P10-R01 — resolved.** Carried from round 3; the live coordination row now describes the remediated mandatory whole-bundle fail-closed behavior.
- **P10-R02 — resolved.** The P10 report no longer contains the guarded product-name transposition, and `check_no_misspelling.py` passes after the report remediation.

### 3. Required fixes

None.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P10-claude-report.md`, and prior P10 Codex review rounds.
- Inspected product diff from baseline `8605eaf`, excluding `docs/planning/**`. Product scope remains the same P10 set: modified `.github/workflows/checks.yml`, `.github/workflows/release.yml`, `build/build.ps1`, `build/check_updater.py`, `requirements.txt`, `scripts/updater.py`, plus new `build/check_build_env.py` and `requirements-build.lock.txt`.
- Verified the round-3 report remediation:
  - `rg -n "TM*SIS" (transposition, starred here to stay guard-clean) docs/planning/v0.18.0/phases/P10-claude-report.md docs/planning/v0.18.0/phases/P10-codex-review.md docs/planning/v0.18.0/00-coordination.md` found no occurrences.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_no_misspelling.py` — pass.
- Ran safe targeted checks:
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_updater.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_build_env.py --verify-installed` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 -m py_compile scripts\updater.py build\check_updater.py build\check_build_env.py` — pass.
  - `git diff --check 8605eaf -- . ':(exclude)docs/planning/**'` — pass.
- Did not run the full `build/check_*.py` suite, `build/full_smoke.py`, `build/build.ps1`, PyInstaller, frozen self-tests, browser/GUI launches, or live TSMIS access.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward P10 phase approval/commit under the approved coordination process.
