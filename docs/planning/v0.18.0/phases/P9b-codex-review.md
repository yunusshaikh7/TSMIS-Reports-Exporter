## Review round 1

### 1. Verdict: `PASS WITH FIXES`

P9b is correctly scoped to the approved deeper frontend modularization phase: the product diff is UI-only, keeps classic scripts/no framework/no ES modules, preserves the P9 mock/production boot boundary, and does not touch backend bridge contracts, persisted settings, auth/cache/manifest/output behavior, comparison code, updater code, or packaging Python module reachability. The split appears structurally sound and the targeted UI checks pass.

However, one new P9b test assertion that is supposed to lock module wiring is currently vacuous. This does not prove a product regression, but it means the phase's "extended boot check locks the new module boundaries" completion claim is not fully met yet.

### 2. Blocking findings

None.

### 3. Required fixes

#### `P9b-R01` — Required — `check_ui_boot.js` module-wiring assertion counts declarations as calls

- Affected phase area: P9b frontend module-boundary tests / completion criteria.
- Repository evidence: `build/check_ui_boot.js:119-126` builds `allUi = app + uiDom + uiMatrix + uiSettings` and then checks each moved representative function with `new RegExp("\\b" + fn + "\\s*\\(").test(allUi)`. That regex matches the function declaration itself, so the "still called (wiring intact)" assertion can pass even when no call or handler reference remains. For example, `scripts/ui/ui-settings.js:379` declares `async function verifyEnvironment()`, while the actual app wiring is a non-call reference at `scripts/ui/app.js:1852` (`$("btnVerifyEnv").onclick = verifyEnvironment;`). My independent probe stripped function declarations and found no call-style reference for `verifyEnvironment`; the current check still passes because it sees the declaration.
- Why this matters: P9b's approved test scope requires the extended boot/contract checks to lock the new module boundaries and boot wiring. A check that passes on the declaration alone would not catch a broken moved-function wiring path, especially for handler-style references that are intentionally assigned rather than invoked.
- Exact correction expected: update `build/check_ui_boot.js` so the representative moved-symbol wiring check excludes function declarations and accepts the real non-definition reference forms. For handler-bound symbols, assert the specific wiring where appropriate, e.g. `btnVerifyEnv` assigning `verifyEnvironment`; for internal helpers, assert at least one non-definition use in the intended consumer module. Keep the fix test-only unless the strengthened check exposes a real product issue.

### 4. Non-blocking recommendations

#### `P9b-A01` — Recommended — Clarify the report/check wording around top-level browser listeners

- Affected phase area: P9b report accuracy and future maintainability.
- Repository evidence: `docs/planning/v0.18.0/phases/P9b-claude-report.md` says the new modules contain "only function declarations + literal consts." `scripts/ui/ui-dom.js:60-61` registers the `matchMedia` change listener at load time, and `scripts/ui/ui-dom.js:94-95` registers document click/keydown listeners at load time. These listener registrations existed in the baseline app.js and are self-contained browser/WebView2 APIs, so I do not consider this a product defect.
- Exact correction expected: if Claude touches the P9b report during remediation, soften that wording to "no top-level execution that depends on later app.js symbols" or equivalent. No product-code change is requested for this recommendation.

### 5. Verification performed

Read:

- `docs/planning/v0.18.0/00-coordination.md`
- `docs/planning/v0.18.0/05-claude-final-plan.md`
- `docs/planning/v0.18.0/phases/P9b-claude-report.md`
- `docs/planning/v0.18.0/phases/P9-codex-review.md`

Inspected product diff from baseline `35a5af0`, excluding `docs/planning/**`. Product scope is the expected P9b set: modified `scripts/ui/app.js`, `scripts/ui/index.html`, `build/check_ui_boot.js`, `build/check_ui_contract.py`, `build/check_mx_partial_render.js`, plus new `scripts/ui/ui-dom.js`, `scripts/ui/ui-matrix.js`, and `scripts/ui/ui-settings.js`.

Safe checks/diagnostics run:

- `node --check scripts/ui/ui-dom.js`
- `node --check scripts/ui/ui-matrix.js`
- `node --check scripts/ui/ui-settings.js`
- `node --check scripts/ui/app.js`
- `node --check scripts/ui/mock.js`
- `node --check scripts/ui/contract.js`
- `node build/check_ui_boot.js`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_ui_contract.py`
- `node build/check_mx_partial_render.js`
- `node build/check_compare_routing.js`
- `build/.venv/Scripts/python.exe -B -X utf8 -m py_compile build/check_ui_contract.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_app_modules.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_report_catalog.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_gui_bridge.py`
- `git diff --check 35a5af0 -- . ':(exclude)docs/planning/**'`
- Independent classic-script order evaluation of `contract.js → ui-dom.js → ui-matrix.js → ui-settings.js → app.js` in a stubbed browser-like VM with `#mock`, confirming the scripts evaluate in order and expose `boot`.
- Independent moved-symbol probe showing all baseline top-level functions remain present after the split and only the two intended helper functions are new: `syncMatrixFastControls` and `syncFormulasToggle`.
- Independent probe demonstrating `P9b-R01`: after stripping function declarations, `verifyEnvironment` has no call-style reference even though the current `check_ui_boot.js` "still called" assertion passes on its declaration; the actual app wiring is the handler assignment at `scripts/ui/app.js:1852`.

All executed checks passed except the deliberately adversarial probe that demonstrates the test assertion gap in `P9b-R01`. I did not run PyInstaller, frozen self-tests, `build/build.ps1`, `build/full_smoke.py`, a browser/GUI smoke, live TSMIS access, credential/profile inspection, or a complete suite batch.

### 6. Whether Claude may proceed toward phase approval

Not yet. Claude should address `P9b-R01`, optionally clarify the report wording in `P9b-A01`, keep P9b marked `awaiting_review`, and return for another Codex review before phase approval.

## Review round 2

### 1. Verdict: `PASS`

P9b now meets the approved phase scope and the round-1 required finding is resolved. The product diff remains limited to the deeper frontend modularization work: the classic-script module split, bounded `sync*` renderer helper merge, script-order updates, and associated UI checks. I found no new blocking or required issue.

### 2. Blocking findings

None.

### 3. Required fixes

None.

- `P9b-R01` — Resolved. `build/check_ui_boot.js:124-133` now strips each representative moved function's declaration before requiring a remaining reference, so the assertion no longer passes on `function fn(` alone. `build/check_ui_boot.js:138-139` also locks the handler-bound `verifyEnvironment` example directly by asserting `$("btnVerifyEnv").onclick = verifyEnvironment` in `scripts/ui/app.js`.
- `P9b-A01` — Resolved. `docs/planning/v0.18.0/phases/P9b-claude-report.md:25-29` now describes the new modules as having no top-level execution that depends on later `app.js` symbols, while acknowledging the self-contained `ui-dom.js` top-level browser listener registrations that already existed in the baseline.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

Read:

- `docs/planning/v0.18.0/00-coordination.md`
- `docs/planning/v0.18.0/05-claude-final-plan.md`
- `docs/planning/v0.18.0/phases/P9b-claude-report.md`
- `docs/planning/v0.18.0/phases/P9b-codex-review.md`
- relevant prior P9 review history in `docs/planning/v0.18.0/phases/P9-codex-review.md`

Inspected product diff from baseline `35a5af0`, excluding `docs/planning/**`. The product scope remains the intended P9b set: modified `scripts/ui/app.js`, `scripts/ui/index.html`, `build/check_ui_boot.js`, `build/check_ui_contract.py`, `build/check_mx_partial_render.js`, plus new `scripts/ui/ui-dom.js`, `scripts/ui/ui-matrix.js`, and `scripts/ui/ui-settings.js`.

Safe checks/diagnostics run:

- Adversarial probe for `P9b-R01`: old call-style check still passes on the real declaration, the new declaration-stripped check passes on the real handler wiring, and both the new reference check plus explicit handler check fail on a synthetic unwired `verifyEnvironment`.
- Independent moved-symbol probe with comments stripped: every representative moved symbol has at least one non-declaration reference, including `verifyEnvironment=1`.
- Independent classic-script order evaluation of `contract.js → ui-dom.js → ui-matrix.js → ui-settings.js → app.js` in a stubbed browser-like VM with `#mock`, confirming ordered evaluation exposes `boot`.
- `node --check scripts/ui/ui-dom.js`
- `node --check scripts/ui/ui-matrix.js`
- `node --check scripts/ui/ui-settings.js`
- `node --check scripts/ui/app.js`
- `node --check scripts/ui/mock.js`
- `node --check scripts/ui/contract.js`
- `node build/check_ui_boot.js`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_ui_contract.py`
- `node build/check_mx_partial_render.js`
- `node build/check_compare_routing.js`
- `build/.venv/Scripts/python.exe -B -X utf8 -m py_compile build/check_ui_contract.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_app_modules.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_report_catalog.py`
- `build/.venv/Scripts/python.exe -B -X utf8 build/check_gui_bridge.py`
- `git diff --check 35a5af0 -- . ':(exclude)docs/planning/**'`

All checks above passed. I did not run PyInstaller, frozen self-tests, `build/build.ps1`, `build/full_smoke.py`, a browser/GUI smoke, live TSMIS access, credential/profile inspection, or a complete suite batch.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval for P9b.
