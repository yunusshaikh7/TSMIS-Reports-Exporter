# P7c Codex review

## Review round 1

### 1. Verdict: `PASS`

P7c is compliant with the approved phase and may proceed toward approval. The product diff is narrowly scoped to the Matrix feature-endpoint grouping: the Matrix / by-day / TSN-library bridge cluster moved from `scripts/gui_api.py` into `scripts/gui_matrix.py::GuiMatrixMixin`, `scripts/gui_api.py::GuiApi` inherits the mixin, `_api_method` moved to `scripts/gui_endpoint.py` to avoid a cycle, and packaging/test references were updated.

I found no product regression, incomplete migration, dependency-direction violation, stale duplicate implementation, frontend/backend contract breakage, or unrelated scope in this phase.

Accepted plan deviation: the matrix dispatch pairs were moved verbatim rather than unified. That is acceptable for P7c because the final plan qualified unification as "where behavior-neutral", while this phase is the largest bridge move and the independent AST check confirms zero method-body drift. Unifying the dispatch pairs inside this same diff would reduce the value of the mechanical-move proof and is not required for P7c approval.

### 2. Blocking findings

None.

### 3. Required fixes

None.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

Read:

- `docs/planning/v0.18.0/00-coordination.md`
- `docs/planning/v0.18.0/05-claude-final-plan.md`
- `docs/planning/v0.18.0/phases/P7c-claude-report.md`
- relevant prior P7b review history, especially `P7b-R01` / `P7b-R02`

Inspected product diff from phase baseline `07b846b`, excluding `docs/planning/**` for product evaluation:

- Modified tracked files: `scripts/gui_api.py`, `build/check_gui_api_surface.py`, `build/check_matrix_bridge.py`, `build/check_day_matrix.py`, `build/app.spec`
- New untracked product files: `scripts/gui_matrix.py`, `scripts/gui_endpoint.py`
- No `scripts/ui/`, settings, auth, cache, manifest, output-layout, comparison-engine, updater, or release-build files are changed by P7c.

Independent structural checks:

- Parsed `07b846b:scripts/gui_api.py` and current `scripts/gui_matrix.py`; compared every `GuiMatrixMixin` method against the baseline `GuiApi` method by `ast.dump`.
- Result: `71` mixin methods, `0` missing from baseline, `0` AST diffs, `0` moved methods left inline in current `GuiApi`.
- Import/façade smoke: `GuiApi` MRO is `GuiApi -> GuiMatrixMixin -> object`, `GuiApi` still exposes `98` public callable methods, and `matrix_info` resolves through the mixin.

Safe targeted checks run:

- `build/.venv/Scripts/python.exe -B -X utf8 build/check_gui_api_surface.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_matrix_bridge.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_day_matrix.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_matrix.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_matrix_tsn.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_gui_bridge.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_b3_batch.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_worker_lifecycle.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_app_modules.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_import_direction.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_no_misspelling.py`
- `build/.venv/Scripts/python.exe -B -X utf8 -m py_compile scripts/gui_api.py scripts/gui_matrix.py scripts/gui_endpoint.py build/check_gui_api_surface.py build/check_matrix_bridge.py build/check_day_matrix.py`
- `node --check scripts/ui/app.js`
- `node --check scripts/ui/mock.js`
- `node build/check_mx_partial_render.js`
- `node build/check_compare_routing.js`
- `node build/check_ui_boot.js`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_ui_contract.py`
- `git diff --check 07b846b -- . ':(exclude)docs/planning/**'`
- targeted trailing-whitespace scan for `scripts/gui_matrix.py` and `scripts/gui_endpoint.py`

All targeted checks passed. I did not run PyInstaller, frozen self-tests, `build/build.ps1`, `build/full_smoke.py`, the complete check suite as a batch, or any live TSMIS/browser/GUI workflow. I also did not inspect credentials, browser profiles, private report contents, or internal website source.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward P7c phase approval.
