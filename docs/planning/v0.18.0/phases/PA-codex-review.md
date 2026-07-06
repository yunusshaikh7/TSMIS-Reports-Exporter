# Review round 1

## 1. Verdict

**BLOCKED**

The implementation substantially matches PA's intended shape, and the targeted offline checks pass, but three acceptance-gate defects prevent phase approval.

## 2. Blocking findings

### PA-B01 — Blocking — PA completion evidence is absent

- **Affected plan area:** PA completion criterion; exact-artifact verification.
- **Evidence:** `docs/planning/v0.18.0/05-claude-final-plan.md:401` requires both exact windowed variants and the source ZIP to pass their gates. `docs/planning/v0.18.0/phases/PA-claude-report.md:155-163` explicitly records that neither frozen build nor frozen executable self-test was run. A development invocation of `scripts/gui_main.py --self-test` does not characterize PyInstaller analysis, collection, pruning, DLL/data inclusion, or the final windowed executable.
- **Exact correction expected:** Before PA approval, provide successful execution evidence for `build/build.ps1 -SelfTest` and `build/build.ps1 -SelfTest -BundleChromium` against their final post-copy/post-prune executables, plus the corrected source-archive gate in PA-B03. This may be from an approved disposable/local run or a successful branch CI run. If CI evidence requires a provisional commit contrary to coordination rule D20, resolve that coordination constraint explicitly; an unexecuted workflow definition is not completion evidence.

### PA-B02 — Blocking — The PR frozen gate becomes stale after the label event

- **Affected plan area:** `.github/workflows/frozen-gate.yml`; PA's early label/nightly tripwire.
- **Evidence:** `.github/workflows/frozen-gate.yml:20-21` subscribes only to `pull_request: types: [labeled]`, and line 30 tests only `github.event.label.name`. After `frozen-gate` is applied, later commits generate `synchronize`, not `labeled`, so the exact-artifact gate does not rerun for those commits. This defeats PA's purpose as protection for subsequent broad restructuring.
- **Exact correction expected:** Trigger on subsequent PR revisions, including `synchronize` (and appropriate opened/reopened events), and condition execution on the PR's current label collection, for example membership in `github.event.pull_request.labels.*.name`, rather than only the label attached to the triggering event. Demonstrate that applying the label runs the gate and that a later commit while the label remains present runs it again.

### PA-B03 — Blocking — The source-ZIP gate does not test a source ZIP or clean extraction

- **Affected plan area:** source-ZIP console gate; PA clean-extract contract.
- **Evidence:** The approved design requires a separate clean-extract source-ZIP smoke (`docs/planning/v0.18.0/05-claude-final-plan.md:396-401`). `build/check_source_zip_smoke.py:19-22` inserts the current workspace root and `scripts/` directly into `sys.path`. In `.github/workflows/release.yml:84-91`, that check runs before `git archive`; `.github/workflows/frozen-gate.yml:52-55` likewise runs it against the checkout. It can therefore pass using files present in the checkout but absent from the shipped archive and cannot detect archive membership, prefix, or clean-root import defects.
- **Exact correction expected:** Create the actual source archive first, extract it into a disposable clean directory, and run the console smoke with the extracted root as the import and working directory using the prepared interpreter. The release workflow must gate the same archive that is uploaded. The PR frozen gate must exercise an equivalent archive produced from the reviewed revision. Add a negative characterization proving that a required source member omitted from the archive causes the gate to fail.

## 3. Required fixes

No additional required findings beyond PA-B01 through PA-B03. All three must be resolved and independently rechecked before approval.

## 4. Non-blocking recommendations

### PA-A01 — Recommended — Clean self-test temporary files on failure

- **Affected area:** `scripts/self_test.py:run`.
- **Evidence:** `scripts/self_test.py:60` creates a temporary directory, while cleanup occurs only on the success path at line 179. Any mandatory assertion or import failure leaves the directory behind, including repeated CI diagnostics.
- **Exact correction expected:** Enclose the temporary-directory-dependent body in `try/finally` (or use an equivalent temporary-directory context) so cleanup occurs on success and failure without changing emitted results or exit behavior.

## 5. Verification performed

- Confirmed coordination marks PA `awaiting_review` with baseline `4bbee65`; workspace `HEAD` is `4bbee6574ef521b540cd6d47c7dc17b455595f21`.
- Inspected the complete product diff from `4bbee65`, excluding `docs/planning/`, including the four untracked PA product files.
- Ran `python build/check_app_modules.py`: pass.
- Ran `python build/check_source_zip_smoke.py`: pass against the checkout; PA-B03 explains why this does not satisfy the archive contract.
- Ran `python build/check_import_direction.py`: pass.
- Ran `git diff --check 4bbee65 -- . ':(exclude)docs/planning/**'`: no whitespace errors; only the existing line-ending warning for `build/full_smoke.py`.
- Independently inspected `build/build.ps1`, `build/app.spec`, the shared self-test delegation, CI/release ordering, workflow triggers, and the source-smoke import root.
- Did not run PyInstaller, frozen executables, browser/GUI self-tests, or the complete check suite during this read-only review.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude may remediate PA-B01 through PA-B03 and return PA for another review round. Subsequent implementation phases must not begin.

# Review round 2

## 1. Verdict

**BLOCKED**

PA-B01, PA-B02, and PA-A01 are resolved. PA-B03 remains blocking because the local archive gate still tests the committed P0 baseline rather than the uncommitted PA product revision under review.

## 2. Blocking findings

### PA-B03 — Blocking — The source-archive check is clean-extracting the wrong revision

- **Affected plan area:** `build/check_source_zip_smoke.py`; source-ZIP completion evidence and the pre-commit phase-review safety net.
- **Status:** **Still open, narrowed.** The clean extraction, fresh interpreter, prefix/membership assertions, and negative missing-member characterization are correctly implemented.
- **Repository evidence:** `build/check_source_zip_smoke.py:_git_archive` at lines 94-98 unconditionally executes `git archive ... HEAD`. Coordination requires PA to remain uncommitted until Codex returns `PASS`; workspace `HEAD` is therefore still baseline `4bbee6574ef521b540cd6d47c7dc17b455595f21`. The PA files `scripts/self_test.py`, `build/check_source_zip_smoke.py`, and `.github/workflows/frozen-gate.yml` are absent from `HEAD` and exist only in the worktree. Consequently, the reported and independently repeated green archive run clean-extracted P0, not the PA revision being reviewed. The same design will also make local pre-commit runs blind to tracked worktree changes in later phases such as P4, where this tripwire is intended to protect console/report dispatch.
- **Exact correction expected:** Preserve the release behavior that gates the committed archive, but add an explicit candidate-artifact/worktree mode for pre-commit review that creates a disposable source archive from the complete intended product worktree without changing the real Git index and without including `docs/planning/`. Alternatively, accept a caller-supplied candidate ZIP and make the release workflow create the upload ZIP first and pass that exact file to the checker. Demonstrate that (1) the candidate archive contains the PA product additions, (2) its clean-extract smoke passes, and (3) a temporary uncommitted change or omitted required member is observed by the pre-commit gate rather than silently falling back to `HEAD`.

## 3. Required fixes

- Resolve PA-B03 as specified above and rerun the archive check against the actual PA candidate contents.
- Correct the remediation report's claim that the current local run tested the reviewed/source-upload revision; it tested `HEAD` (`4bbee65`).

Prior finding dispositions:

- **PA-B01 — Resolved.** The report records both disposable frozen variants building and their exact post-prune windowed executables passing `--self-test`; the implementation path is consistent with that evidence. This review did not repeat the destructive builds.
- **PA-B02 — Resolved.** `.github/workflows/frozen-gate.yml:21,34` now covers `opened`, `reopened`, `labeled`, and `synchronize` and checks the PR's current label set.
- **PA-A01 — Resolved.** `scripts/self_test.py:run` now removes its temporary workspace in `finally`; a forced `_exercise` failure followed the cleanup path successfully.

## 4. Non-blocking recommendations

None beyond the resolved PA-A01 recommendation.

## 5. Verification performed

- Confirmed PA remains `awaiting_review`, baseline `4bbee65`, with workspace `HEAD` exactly `4bbee6574ef521b540cd6d47c7dc17b455595f21`.
- Re-inspected the complete product worktree delta from `4bbee65`, including all four untracked PA product files and excluding planning files.
- Re-ran `python build/check_source_zip_smoke.py`: all assertions pass, but inspection and `git cat-file` prove its archive is the P0 `HEAD`, not PA.
- Re-ran `python build/check_app_modules.py`: pass.
- Re-ran `python build/check_import_direction.py`: pass.
- Parsed `build/build.ps1` as PowerShell: pass.
- Byte-compiled the five directly affected Python entry/check modules: pass.
- Re-ran `git diff --check` for the product delta: no whitespace errors; only the existing `build/full_smoke.py` line-ending warning.
- Inspected the corrected PR event/label expression, exact-executable build flow, release ordering, archive extraction/subprocess isolation, and self-test cleanup.
- Did not rerun PyInstaller, frozen executables, browser/GUI checks, or the complete regression suite.

## 6. Whether Claude may proceed toward phase approval

**No.** Claude may correct PA-B03 and return PA for review round 3. No subsequent implementation phase should begin.

# Review round 3

## 1. Verdict

**PASS**

The remaining PA-B03 blocker is resolved. The phase now provides a pre-commit candidate-archive gate for the reviewed worktree and a supplied-archive mode that gates the exact source ZIP published by the release workflow.

## 2. Blocking findings

None.

Prior blocking finding dispositions:

- **PA-B01 — Resolved.** Both post-copy/post-prune frozen windowed variants were built and their exact executables passed the shared `--self-test`; the implementation and recorded evidence remain consistent.
- **PA-B02 — Resolved.** The PR frozen gate reruns on later revisions while the `frozen-gate` label remains present.
- **PA-B03 — Resolved.** `build/check_source_zip_smoke.py:_candidate_archive` now uses a throwaway `GIT_INDEX_FILE` to archive tracked and untracked product worktree content while excluding `docs/planning/`. `main` also accepts `--zip`; `.github/workflows/release.yml:84-92` creates the source ZIP first and gates that exact file before publication.

## 3. Required fixes

None.

## 4. Non-blocking recommendations

None. PA-A01 remains resolved by `scripts/self_test.py:run` cleanup in `finally`.

## 5. Verification performed

- Confirmed PA is `awaiting_review`, baseline `4bbee65`, and workspace `HEAD` remains the baseline commit as required by the pre-approval workflow.
- Inspected the complete PA product diff and all untracked PA product files, excluding planning-directory changes.
- Ran the default worktree-candidate source archive gate: pass, including prefix, required membership, worktree provenance, clean-extract fresh-interpreter dispatch, and negative missing-member checks.
- Hashed `.git/index` and compared full porcelain status before/after the candidate run: both unchanged.
- Independently built a candidate ZIP in a disposable external directory. It contained all four uncommitted PA additions (`scripts/self_test.py`, both new build checks, and `frozen-gate.yml`), contained zero `docs/planning/` entries, and passed `--zip` supplied-artifact mode.
- Re-ran `build/check_app_modules.py` and `build/check_import_direction.py`: pass.
- Parsed `build/build.ps1` and byte-compiled the directly affected Python modules: pass.
- Re-ran product `git diff --check`: no whitespace errors; only the existing line-ending warning for `build/full_smoke.py`.
- Reconfirmed PA-B02's event set and current-label condition and PA-A01's failure-safe temporary-directory cleanup.
- Did not repeat the destructive PyInstaller/frozen-executable builds or the complete regression suite; the prior remediation report supplies that evidence.

## 6. Whether Claude may proceed toward phase approval

**Yes.** Claude may mark PA approved, commit the phase under the coordination rules, and proceed only in a later turn to the next eligible phase.
