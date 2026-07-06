# P12 Codex Review

## Review round 1

### 1. Verdict

`BLOCKED`

### 2. Blocking findings

- **P12-B01 — blocking — the TOCTOU re-check is not at the final commit point for several consolidators, so a destination can still appear after the re-check and be overwritten without user consent.**
  - **Affected phase area:** P12 consolidate-overwrite TOCTOU re-check.
  - **Repository evidence:**
    - The intended narrow gate exists in `scripts/artifact_store.py:101-121` as `atomic_save_if()`, and it is used correctly by the shared XLSX consolidator at `scripts/consolidate_xlsx_base.py:268-270`.
    - Several direct writers re-check too early and then save through ungated `atomic_save()`:
      - `scripts/consolidate_intersection_summary.py:252` calls `confirm_late_overwrite()`, then `scripts/consolidate_intersection_summary.py:256` calls `build_workbook()`, whose actual replace path is `artifact_store.atomic_save()` at `scripts/consolidate_intersection_summary.py:185`.
      - `scripts/consolidate_ramp_summary.py:865` calls `confirm_late_overwrite()`, then `scripts/consolidate_ramp_summary.py:870` calls `build_workbook()`, whose actual replace path is `artifact_store.atomic_save()` at `scripts/consolidate_ramp_summary.py:768`.
      - `scripts/consolidate_tsn_highway_sequence.py:361` calls `confirm_late_overwrite()`, while the final workbook writer still uses `artifact_store.atomic_save()` at `scripts/consolidate_tsn_highway_sequence.py:269`.
    - The per-route converter paths also re-check outside the final combining write, then bypass the inner prompt:
      - `scripts/consolidate_tsmis_highway_log_pdf.py:596` re-checks before calling `consolidate_xlsx()` at `scripts/consolidate_tsmis_highway_log_pdf.py:603` with `confirm_overwrite=lambda _p: True`.
      - `scripts/consolidate_tsn_highway_log.py:556` / `scripts/consolidate_tsn_highway_log.py:563` have the same shape.
    - `build/check_consolidate_toctou.py` covers appearances before the current re-check, but not appearances after the outer re-check and before the actual final save/combine. It also does not cover `consolidate_intersection_summary` or `consolidate_tsn_highway_sequence`.
    - Independent temp-dir probe against `consolidate_intersection_summary.consolidate()` reproduced the gap: with an absent destination at the initial prompt and a `confirm_overwrite` callback that would decline, `build_workbook()` created the destination after P12's re-check but before its actual save. Result: `status=ok`, `confirm_calls=0`, `appeared_file_was_overwritten=True`.
  - **Why this blocks approval:** P12 completion requires the consolidate-overwrite re-check to close the confirm-then-appears window. The current implementation narrows only the parse-time window in some paths; it still silently overwrites a newly appeared file during final workbook build/combine in at least one real consolidator shape.
  - **Exact correction expected:** Put the late-overwrite gate at the final commit point for every affected writer. Use `atomic_save_if()` or an equivalent `proceed()` callback inside the direct `build_workbook()` / `_write_workbook()` save paths, and ensure the per-route converter wrappers do not pass a no-op confirm into an inner final write that can still observe a late appearance. Add regression tests where the destination appears after the outer re-check but before the actual final save/combine for `consolidate_intersection_summary`, `consolidate_ramp_summary`, `consolidate_tsn_highway_sequence`, and the representative per-route converter shape; a decline must return `cancelled`, preserve the appeared file, and record a confirm call.

### 3. Required fixes

- **P12-R01 — required — the PDF expected-row oracle misses the split realignment-prefix row shape that the parser explicitly accepts.**
  - **Affected phase area:** P12 PDF expected-row oracle / evidence-capture contract.
  - **Repository evidence:**
    - `scripts/pdf_row_oracle.py:38` defines a single-token postmile recognizer, and `scripts/pdf_row_oracle.py:48-49` checks only `parts[0]`.
    - `scripts/consolidate_tsmis_highway_log_pdf.py:379-381` explicitly accepts a data row where pdfplumber split a lone realignment/section letter into `texts[0]` and the postmile into `texts[1]`; the no-geometry path has the same shape at `scripts/consolidate_tsmis_highway_log_pdf.py:366-368`.
    - `build/check_pdf_row_oracle.py:60-64` tests `000.001`, `R012.345`, and `123.456A`, but not `R 012.345`.
    - Independent probe: `pdf_row_oracle.line_is_data_row("R 012.345 0.250 0.000 sample")` returned `False`, while the parser's documented split-prefix shape accepted the same first two tokens; the oracle counted `0` expected rows for that line.
  - **Exact correction expected:** Extend the oracle with an independent split-prefix recognizer (do not import the parser regex) so a lone alphabetic prefix followed by a valid postmile token counts as one data row. Add oracle and capture-wiring regression coverage for the split-prefix shape and preserve the privacy-safe counts-only evidence contract.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P12-claude-report.md`, and the relevant prior P10/P12 coordination context.
- Inspected product diff from baseline `a8d9235`, excluding `docs/planning/**`. Product scope matches P12: 11 modified tracked files plus new `scripts/safe_delete.py`, `scripts/owned_dir.py`, `scripts/pdf_row_oracle.py`, and four new `build/check_*` files.
- Ran safe targeted checks:
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_consolidate_toctou.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_pdf_row_oracle.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_owned_dir.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_reset_safety.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_tsmis_pdf_reconcile.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 -m py_compile ...` over touched P12 modules/checks — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_app_modules.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_import_direction.py` — pass.
  - `git diff --check a8d9235 -- . ':(exclude)docs/planning/**'` — pass, with only Git's line-ending warning for `scripts/artifact_store.py`.
- Ran two independent temp-only probes:
  - `consolidate_intersection_summary` late-appearance-after-recheck probe reproduced P12-B01.
  - `pdf_row_oracle` split-prefix probe reproduced P12-R01.
- Did not run the complete `build/check_*.py` suite, `build/full_smoke.py`, `build/build.ps1`, PyInstaller, frozen self-tests, browser/GUI launches, or live TSMIS access.

### 6. Whether Claude may proceed toward phase approval

No. Claude should keep P12 in `awaiting_review`, remediate **P12-B01** and **P12-R01** within the approved P12 scope, append remediation to the P12 Claude report, and return the phase for another Codex review.

## Review round 2

### 1. Verdict

`PASS WITH FIXES`

### 2. Blocking findings

None.

- **P12-B01 — resolved.** The late-overwrite gate is now enforced at the final workbook commit point. Evidence: `scripts/artifact_store.py:101` defines `atomic_save_if()` with the `proceed()` check immediately before `os.replace`; `scripts/consolidate_intersection_summary.py:153` / `:189` and `:257-259`, `scripts/consolidate_ramp_summary.py:635` / `:773` and `:870-873`, and `scripts/consolidate_tsn_highway_sequence.py:235` / `:270` and `:363-365` now route the final save through that gate; `scripts/consolidate_xlsx_base.py:82` / `:130-132` and `:272-274` preserve the early-confirm state and gate the final shared XLSX save; the PDF/TSN converter wrappers pass the real `confirm` plus `existed_at_confirm` into that final shared save at `scripts/consolidate_tsmis_highway_log_pdf.py:502-503` and `:601`, and `scripts/consolidate_tsn_highway_log.py:472-473` and `:561`.

### 3. Required fixes

- **P12-R01 — resolved.** The expected-row oracle now accepts the parser-compatible split realignment-prefix shape. Evidence: `scripts/pdf_row_oracle.py:44-62` adds independent `_BARE_POSTMILE_RE` / `_PREFIX_RE` handling for `"R 012.345"`-style rows; `build/check_pdf_row_oracle.py:62-78` and `:163-171` cover split-prefix counting and evidence-capture wiring.

- **P12-R02 — required — `scripts/safe_delete.py`'s module docstring still over-claims current `shutil.rmtree` junction behavior.**
  - **Affected phase area:** P12 reset junction/symlink guard; documentation honesty / stale comments.
  - **Repository evidence:** `scripts/safe_delete.py:4-6` says Windows junctions make `shutil.rmtree` recurse through the link and delete the target's contents. That contradicts both the P12 report and the new check: `docs/planning/v0.18.0/phases/P12-claude-report.md:29-34` states the shipped CPython 3.11 behavior already preserves child junction targets and that the audit's data-destruction scenario does not reproduce; `build/check_reset_safety.py:7-22` and `:131-163` assert the same, with the genuine improvement narrowed to uniform root-reparse handling and explicit version-independent safety.
  - **Why this must be fixed before approval:** P12 explicitly corrected over-claiming for this audit item, but the product module now carries the stale/stronger claim. That is not a runtime regression, but it is misleading shipped source documentation and can misdirect future maintenance.
  - **Exact correction expected:** Update the top-level docstring in `scripts/safe_delete.py` to match the verified behavior: on the shipped CPython 3.11, child junction/symlink targets are already preserved by `shutil.rmtree`; a root reparse point is refused and left in place; `scoped_rmtree` provides explicit, uniform root-or-descendant unlinking without following targets, plus version-independent defense. Keep the reset behavior and tests unchanged unless the wording change reveals a real code issue.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P12-claude-report.md`, and `docs/planning/v0.18.0/phases/P12-codex-review.md`.
- Inspected product diff from baseline `a8d9235`, excluding `docs/planning/**`. Scope matches P12 plus the remediation follow-through: 12 modified tracked files and 7 new untracked product/check files; no `compare_core` changes observed.
- Inspected the remediated overwrite-gate call sites in `artifact_store`, the three direct consolidator writers, `consolidate_xlsx_base`, and the two per-route converter wrappers.
- Ran safe targeted checks:
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_consolidate_toctou.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_pdf_row_oracle.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_tsmis_pdf_reconcile.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_app_modules.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_owned_dir.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_reset_safety.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_import_direction.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_artifact_store.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_consolidate_outcome.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_consolidate_intersection.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_ramp_summary_partial.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_tsn_outcome.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_worker_lifecycle.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_matrix_tsn.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_matrix.py` — pass.
  - `git diff --check a8d9235 -- . ':(exclude)docs/planning/**'` — pass, with only Git line-ending warnings for `build/check_tsn_outcome.py` and `scripts/artifact_store.py`.
- Ran independent temp-only probes:
  - `consolidate_intersection_summary.consolidate()` with the destination appearing at the patched final `atomic_save_if()` point returned `status=cancelled`, called confirm once, and preserved the appeared file.
  - `pdf_row_oracle.line_is_data_row("R 012.345 0.250 0.000 sample")` returned `True`, and `count_expected_rows([...])` returned `1`.
- Did not run the complete `build/check_*.py` suite, `build/full_smoke.py`, `build/build.ps1`, PyInstaller, frozen self-tests, browser/GUI launches, or live TSMIS access.

### 6. Whether Claude may proceed toward phase approval

Yes, after fixing **P12-R02** and recording the narrow remediation in the P12 Claude report. Do not commit P12 before the docstring is corrected and the relevant safe checks (`check_reset_safety.py` plus `git diff --check`) are re-run. No broader redesign or additional product behavior change is requested.

## Review round 3

### 1. Verdict

`PASS`

### 2. Blocking findings

None.

### 3. Required fixes

None.

- **P12-B01 — resolved.** Reconfirmed by `build\check_consolidate_toctou.py`: the final-save TOCTOU gate catches a destination appearing at the patched `atomic_save_if()` commit point for the shared XLSX path, the three direct writers, and the representative per-route converter.
- **P12-R01 — resolved.** Reconfirmed by `build\check_pdf_row_oracle.py`: split-prefix rows such as `"R 012.345"` are counted by the independent oracle and flow through the privacy-safe capture path.
- **P12-R02 — resolved.** `scripts/safe_delete.py:5-18` now states the verified CPython 3.11 behavior: child junction targets are already preserved by `shutil.rmtree`, root reparse points are refused and left in place, and `scoped_rmtree` provides explicit, uniform, version-independent root-or-descendant unlinking without following targets. This now matches `build/check_reset_safety.py:7-22` and the remediation report at `docs/planning/v0.18.0/phases/P12-claude-report.md:326-341`.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P12-claude-report.md`, and prior P12 Codex review rounds.
- Confirmed current phase remains **P12** with baseline `a8d9235` and status `awaiting_review`.
- Inspected the product diff from baseline `a8d9235`, excluding `docs/planning/**`: 12 modified tracked files plus the 7 new P12 product/check files reported by `git status`; no `compare_core` changes observed.
- Inspected the corrected `scripts/safe_delete.py` module docstring and compared it to `build/check_reset_safety.py` and the P12 remediation report.
- Ran safe targeted checks:
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_reset_safety.py` — pass.
  - `git diff --check a8d9235 -- . ':(exclude)docs/planning/**'` — pass, with only Git line-ending warnings for `build/check_tsn_outcome.py` and `scripts/artifact_store.py`.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_consolidate_toctou.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_pdf_row_oracle.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_app_modules.py` — pass.
  - `build\.venv\Scripts\python.exe -B -X utf8 build\check_import_direction.py` — pass.
- Did not run the complete `build/check_*.py` suite, `build/full_smoke.py`, `build/build.ps1`, PyInstaller, frozen self-tests, browser/GUI launches, or live TSMIS access.

### 6. Whether Claude may proceed toward phase approval

Yes. P12 satisfies the approved phase scope and the prior Codex findings are resolved. Claude may proceed toward phase approval/commit under the coordination rules.
