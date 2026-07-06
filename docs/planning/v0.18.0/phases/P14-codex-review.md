# Review round 1

## 1. Verdict

PASS

## 2. Blocking findings

None.

## 3. Required fixes

None.

## 4. Non-blocking recommendations

### P14-A01 — Refresh comments that still describe Highway Log (PDF) as the only PDF auto-consolidator exception

Evidence:

- `scripts/report_catalog.py:185` comments above `_AUTO_CONSOLIDATOR` say every exportable report except Highway Log (PDF) is auto-consolidated by the registry map.
- `scripts/reports.py:61`, `scripts/reports.py:68`, and `scripts/reports.py:77` still describe only `highway_log_pdf` as absent from `_CONSOLIDATOR_BY_SUBDIR`.
- `scripts/matrix.py:811` correctly introduces `_pdf_store_consolidator(subdir)` for both `highway_log_pdf` and `intersection_detail_pdf`; `scripts/matrix.py:832` still says "PDF Highway Log is the one special case."

Impact:

Behavior is correct: both PDF report families route through `matrix._pdf_store_consolidator`, and the catalog/tests prove `intersection_detail_pdf` is deliberately excluded from the auto-consolidator map. The remaining issue is source-comment drift in exactly the area future maintainers will read while adding/reporting PDF families.

Expected correction:

When convenient, update the comments/docstrings to say PDF-sourced reports that require a scratch `converted_dir` are handled specially by the matrix helper, currently Highway Log (PDF) and Intersection Detail (PDF).

### P14-A02 — Keep future verification wording distinct: `node --check` is not a browser `#mock` smoke

Evidence:

- `docs/planning/v0.18.0/phases/P14-claude-report.md:121` describes `node --check scripts/ui/mock.js scripts/ui/app.js` as "the `#mock` JS smoke."
- The approved P14 verification text in `docs/planning/v0.18.0/05-claude-final-plan.md` requires `check_ui_boot.js` plus UI/contract mock parity and `#mock` smoke green.

Impact:

No phase blocker: Codex independently ran a local headless `index.html#mock` smoke after seeing the wording, and the new `Intersection Detail (PDF)` row rendered in both the Everything matrix and by-day matrix with no console/page errors. The report wording is still easy to misread because syntax checking and browser rendering are different gates.

Expected correction:

Future phase reports should label `node --check` as syntax verification and reserve "`#mock` smoke" for an actual browser/WebView preview render.

## 5. Verification performed

Read:

- `docs/planning/v0.18.0/00-coordination.md`
- `docs/planning/v0.18.0/05-claude-final-plan.md`
- `docs/planning/v0.18.0/phases/P14-claude-report.md`
- relevant CR-002 review/proposal context already present in the planning directory

Inspected:

- Product diff from P14 baseline `d15216d`, excluding `docs/planning`.
- New modules: `scripts/export_intersection_detail_pdf.py`, `scripts/intersection_detail_columns.py`, `scripts/consolidate_tsmis_intersection_detail_pdf.py`, `scripts/compare_intersection_detail_pdf.py`.
- Wiring in `scripts/report_catalog.py`, `scripts/matrix.py`, `scripts/compare_env.py`, `scripts/day_matrix.py`, `scripts/exporter.py`, `scripts/gui_worker.py`, `scripts/batch_manifest.py`, `scripts/ui/mock.js`, `build/app.spec`, and related checks.

Confirmed:

- Product diff matches P14 scope: Intersection Detail (PDF) report-family forward-port; no product docs/P15 comparison evolution included.
- `scripts/compare_core.py`, `version.py`, and `scripts/ui/app.js` are unchanged from baseline.
- Report metadata is added through `report_catalog.py`; `reports.py` remains derived.
- `intersection_detail_pdf` is append-only after the original seven export keys.
- `mock.js` owns the new mock fixtures; `app.js` does not regain `makeMockApi`.
- The new row is visible as the final matrix row and has `env`, `tsn`, and `vs_excel` modes.

Commands/checks run:

- `python build/check_intersection_detail_pdf.py`
- `python build/check_report_catalog.py`
- `python build/check_stable_ids.py`
- `python build/check_matrix.py`
- `python build/check_matrix_tsn.py`
- `python build/check_matrix_bridge.py`
- `python build/check_day_matrix.py`
- `python build/check_source_zip_smoke.py`
- `node build/check_ui_boot.js`
- `python build/check_fake_site.py`
- `python build/check_intersection_gate.py`
- `python build/check_gui_bridge.py`
- `python build/check_app_modules.py`
- `python build/check_import_direction.py`
- `python build/check_compare_env_highway_log_pdf.py`
- `python build/check_compare_intersection_detail_tsn.py`
- `python build/check_compare_audit.py`
- `python -m compileall -q scripts build version.py`
- `python build/check_compare_env_intersection.py`
- `python build/check_consolidate_intersection.py`
- `python build/check_tsmis_pdf_reconcile.py`
- `git diff --check -- . ':!docs/planning'`
- read-only custom temp-dir probe of `matrix.build_comparison(..., "intersection_detail_pdf", mode)` for `env`, `tsn`, and `vs_excel` guard paths.
- read-only hygiene scan for trailing whitespace/tab characters in the six new untracked product/check files.
- local headless `scripts/ui/index.html#mock` smoke using Playwright: booted mock, verified 8 export reports / 18 compare reports, switched to Everything matrix, verified `Intersection Detail (PDF)` renders, switched to by-day matrix, added the first available mock day, verified `Intersection Detail (PDF)` renders, and observed no console errors or page errors.

Results:

- All targeted checks passed.
- The `matrix.build_comparison` temp probe reached expected no-input/no-TSN guard paths for the new row without unknown-row/mode routing failures.
- `git diff --check` was clean for tracked diffs; the six new files had no trailing whitespace/tab issues in the independent scan.
- No destructive build, PyInstaller, frozen self-test, live TSMIS access, credentials/profile inspection, staging, commit, or product-source edit was performed.

## 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward P14 phase approval/commit. The only findings are non-blocking comment/report-wording cleanup recommendations.
