# P7b Codex review

## Review round 1

### 1. Verdict: `PASS WITH FIXES`

The implemented P7b slice is technically sound and behavior-neutral as far as I could verify: `gui_win32` is a clean state-free extraction of the Win32 helpers, `_begin_compare` preserves the compare launch tail for the normal paths, the pywebview public method set remains stable, `gui_win32` is included in `app.spec`, and the targeted bridge/package/import checks pass.

The phase is not ready for approval because it does not yet complete the approved P7b scope. The final plan names P7b as "full depth" GUI mechanical endpoint extraction, with Matrix-first feature endpoint grouping and matrix dispatch pairs in scope. Claude's report explicitly defers that work to a future "P7b group-diff" while the coordination table has no separate future P7b phase. That is acceptable as an incremental implementation step inside P7b, but not as a phase-complete review result.

### 2. Blocking findings

None. I found no current product regression in the implemented Win32 extraction or compare-helper collapse.

### 3. Required fixes

#### P7b-R01 - Required - Approved Matrix endpoint grouping remains unimplemented

- **Affected phase area:** P7b phase compliance and completion criteria.
- **Repository evidence:** The approved plan's P7b "Affected" line includes `gui_win32.py`, feature endpoint grouping "Matrix first", `_begin_task` helper, `start_compare`/`start_compare_env`, and "matrix dispatch pairs" (`docs/planning/v0.18.0/05-claude-final-plan.md:529-535`). The current Claude report says this commit "leaves the Matrix endpoints + their ~800-line dispatch machinery in `gui_api`" and asks Codex whether it must land within P7b (`docs/planning/v0.18.0/phases/P7b-claude-report.md:96-105,115-118`). Current `scripts/gui_api.py` still owns the matrix endpoint/machinery cluster, including `matrix_info`, `_try_start_next_matrix_job`, `MatrixCompareWorker` / `DayMatrixCompareWorker` / `MatrixBatchExportWorker` / `MatrixTsnConsolidateWorker` launch code, `refresh_cell_comparison`, `consolidate_matrix_tsn`, `rebuild_tsn_library`, and the queue endpoints (`scripts/gui_api.py:1667,1784,1871,1890,1990,2029,2070,2219,2279,2346-2384`).
- **Exact correction expected:** Continue P7b before phase approval with the next behavior-neutral group-diff that extracts the cohesive Matrix feature endpoint/machinery group behind the existing `GuiApi` façade, or obtain an explicit plan/coordination amendment creating a separate future phase for that exact work. Preserve pywebview method names/return shapes/event order, keep `task_coordinator` as the state owner, avoid one-class-per-action sprawl, and extend `build/check_gui_api_surface.py` to lock the moved Matrix methods' façade names and source-level arity/signatures.

#### P7b-R02 - Required - The approved `#mock` completion gate is not run or explicitly reconciled

- **Affected phase area:** P7b verification and completion criteria.
- **Repository evidence:** The final plan lists a `#mock` smoke in P7b tests and completion (`docs/planning/v0.18.0/05-claude-final-plan.md:534-535`). The P7b report reclassifies it as N/A because no `scripts/ui/` file changed (`docs/planning/v0.18.0/phases/P7b-claude-report.md:72-74`). I agree the current code slice is backend-only, but the phase report should not silently override the final-plan gate, especially once the remaining Matrix endpoint grouping is completed.
- **Exact correction expected:** Before P7b approval, either run and record the deterministic `#mock` all-tabs smoke required by the plan, or record an explicit coordination-approved rationale that removes it for backend-only P7b. If Matrix endpoint grouping is completed in the next P7b group-diff, keep the smoke as the safer default.

### 4. Non-blocking recommendations

#### P7b-A01 - Recommended - Narrow the `_begin_compare` claim/suggest-name wording or make suggestion lazy

- **Affected phase area:** compare-helper characterization / phase-report accuracy.
- **Repository evidence:** The helper docstring says it releases the task if "the dialog/suggest_name raises" (`scripts/gui_api.py:3052-3068`), and the report says the same helper owns the claim→save-dialog→launch→release tail (`docs/planning/v0.18.0/phases/P7b-claude-report.md:23-25`). In current code, however, `mod.suggest_name(tsmis_path)` and `adapter.suggest_name(pa, pb)` are evaluated before `_begin_compare(...)` is called (`scripts/gui_api.py:3085-3086,3149-3150`), so a suggestion error occurs before the compare gate is claimed, unlike the baseline where it occurred inside the claim/release `try` block. I do not see a practical gate-wedging defect because no gate is claimed in the new path, but the documentation/check wording is imprecise.
- **Exact correction expected:** Either pass a lazy `suggested_name` callable into `_begin_compare` so the old claim-before-suggest-name ordering is preserved, or narrow the helper docstring/report/check wording to say the helper releases on save-dialog/launch-prep errors after claim. Add a small targeted assertion only if preserving the old ordering is intentional.

### 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md`, the P7b section of `docs/planning/v0.18.0/05-claude-final-plan.md`, the full `docs/planning/v0.18.0/phases/P7b-claude-report.md`, prior P7a review history, and CR-001 RM08 requirements.
- Confirmed coordination marks **P7b** `awaiting_review` with baseline `8eb9cc8`.
- Inspected the product diff from `8eb9cc8`, excluding `docs/planning/**`: modified `.github/workflows/checks.yml`, `build/app.spec`, and `scripts/gui_api.py`; new untracked `scripts/gui_win32.py` and `build/check_gui_api_surface.py`.
- Compared the old inline Win32 and compare-start code against current `gui_win32` / `_begin_compare` structure.
- Confirmed no frontend files, settings/auth/cache/manifest/output layout, updater, comparison engine, or live browser/TSMIS code paths were changed by this slice.
- Ran and passed:
  - `python -B -X utf8 build/check_gui_api_surface.py`
  - `python -B -X utf8 build/check_gui_bridge.py`
  - `python -B -X utf8 build/check_matrix_bridge.py`
  - `python -B -X utf8 build/check_b3_batch.py`
  - `python -B -X utf8 build/check_worker_lifecycle.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_no_misspelling.py`
  - `python -B -X utf8 -m py_compile scripts/gui_api.py scripts/gui_win32.py build/check_gui_api_surface.py`
  - `node --check scripts/ui/app.js`
  - `node build/check_mx_partial_render.js`
  - `node build/check_compare_routing.js`
  - `git diff --check 8eb9cc8 -- . ':(exclude)docs/planning/**'`
  - trailing-whitespace scan for the two new untracked files
- Did not run the complete `build/check_*.py` suite, build scripts, PyInstaller, frozen self-tests, browser/GUI launches, live TSMIS, credentials, profiles, private report data, or shared release artifacts.

### 6. Whether Claude may proceed toward phase approval

Not yet. Claude should complete the remaining P7b Matrix endpoint grouping or obtain an explicit plan/coordination amendment that moves it to a separate future phase, and should reconcile the `#mock` completion gate before returning P7b for another review.

## Review round 2

### 1. Verdict: `PASS`

P7b may proceed toward phase approval. The current product diff is consistent with the narrowed P7b scope: Win32 shell/platform helpers moved behind `scripts/gui_win32.py`, compare-start tail logic was centralized in `GuiApi._begin_compare`, and the new guard script covers the P7b API-surface and helper-boundary contracts. No blocking or required product findings remain from review round 1.

Round-1 findings disposition:

- `P7b-R01` — Resolved by approved scope amendment. The Matrix endpoint grouping work was split out of P7b into P7c in `docs/planning/v0.18.0/05-claude-final-plan.md` (`P7b` narrowed to Win32 + compare-start work; `P7c` added for Matrix/day-matrix/TSN-library grouping) and in `docs/planning/v0.18.0/00-coordination.md` (current status notes P7c as the next eligible phase and the phase table lists P7c as pending).
- `P7b-R02` — Resolved by recording the backend-only P7b `#mock` rationale and carrying the deterministic all-tabs `#mock` smoke gate to P7c, where frontend Matrix endpoint grouping will actually occur.
- `P7b-A01` — Resolved. `scripts/gui_api.py::GuiApi._begin_compare` now accepts a lazy `suggest` callable and evaluates it only after the compare slot is claimed, so a failed `start_compare_env` no longer computes the suggested name before the task-state guard runs.

### 2. Blocking findings

None.

### 3. Required fixes

None.

### 4. Non-blocking recommendations

#### `P7b-A02` — Recommended — Clean stale P7c sequencing references

- Affected area: planning/coordination text only.
- Repository evidence: `docs/planning/v0.18.0/00-coordination.md` still has an amended-order summary line that reads `P5b → P7b → P8c ...` even though nearby current-status/table/DoD entries include P7c. `docs/planning/v0.18.0/05-claude-final-plan.md` likewise includes P7c in the phase set and P7c section, but the P11 prerequisite summary still lists prerequisites without P7c.
- Expected correction: before starting P7c or approving a later cross-phase gate, update those stale planning references so all phase-order summaries include P7c consistently. This is not a P7b product blocker because the authoritative current-status/table/DoD entries already identify P7c as pending and next eligible after P7b.

### 5. Verification performed

Read:

- `docs/planning/v0.18.0/00-coordination.md`
- `docs/planning/v0.18.0/05-claude-final-plan.md`
- `docs/planning/v0.18.0/phases/P7b-claude-report.md`
- `docs/planning/v0.18.0/phases/P7b-codex-review.md`

Inspected product diff from phase baseline `8eb9cc8`, excluding `docs/planning/**` for product evaluation:

- `.github/workflows/checks.yml`
- `build/app.spec`
- `scripts/gui_api.py`
- untracked P7b product files `build/check_gui_api_surface.py` and `scripts/gui_win32.py`

Safe targeted checks run:

- `.venv\Scripts\python.exe build/check_gui_api_surface.py`
- `.venv\Scripts\python.exe build/check_gui_bridge.py`
- `.venv\Scripts\python.exe build/check_matrix_bridge.py`
- `.venv\Scripts\python.exe build/check_b3_batch.py`
- `.venv\Scripts\python.exe build/check_worker_lifecycle.py`
- `.venv\Scripts\python.exe build/check_app_modules.py`
- `.venv\Scripts\python.exe build/check_import_direction.py`
- `.venv\Scripts\python.exe build/check_no_misspelling.py`
- `.venv\Scripts\python.exe -m py_compile scripts/gui_api.py scripts/gui_win32.py build/check_gui_api_surface.py`
- `node --check scripts/ui/app.js`
- `node build/check_mx_partial_render.js`
- `node build/check_compare_routing.js`
- `git diff --check 8eb9cc8 -- . ':(exclude)docs/planning/**'`
- targeted trailing-whitespace scan for `scripts/gui_win32.py` and `build/check_gui_api_surface.py`

All targeted checks passed. I did not run the complete build/check suite, PyInstaller, frozen self-tests, browser/GUI launches, or shared-artifact-producing build commands.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward P7b approval. The only remaining item is the non-blocking planning-text cleanup in `P7b-A02`; it should be handled before P7c starts or before a later cross-phase approval gate, but it does not block P7b product approval.
