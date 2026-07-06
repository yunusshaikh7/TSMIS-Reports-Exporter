# P9 Codex Review

## Review round 1

### 1. Verdict

`PASS WITH FIXES`

### 2. Blocking findings

None.

### 3. Required fixes

#### P9-R01 — required — `#mock` can still boot the real pywebview bridge through the ungated ready event

Affected scope: P9 frontend boot split (`scripts/ui/app.js`, `scripts/ui/index.html`, `build/check_ui_boot.js`).

Repository evidence:

- `scripts/ui/app.js:3662` defines `WANT_MOCK` from `location.search + location.hash`.
- `scripts/ui/app.js:3671-3673` registers `window.addEventListener("pywebviewready", ...)` unconditionally and calls `boot(window.pywebview.api)` whenever `bridgeReady()` is true.
- `scripts/ui/app.js:3679` gates only the polling path with `if (!WANT_MOCK)`.
- `scripts/ui/index.html:1024` and the P9 report claim that, under `#mock`, `mock.js` owns boot and never races the real pywebview bridge.
- `build/check_ui_boot.js:41-42` claims to check "app.js auto-boots only in production", but it only asserts that some `if (!WANT_MOCK)` exists; it does not check the `pywebviewready` listener path.

Why this matters:

In a pywebview context with `index.html#mock`, the ready event can fire after `app.js` loads and before `mock.js` boots. Because `boot()` sets `booted = true` at entry, an early real-bridge boot prevents the later `boot(makeMockApi())` call from taking effect. That violates the approved P9 boundary: `app.js` must auto-boot only in production and `mock.js` must own the mock boot.

Exact correction expected:

- Gate every real-bridge boot path on `!WANT_MOCK`, including the `pywebviewready` listener, or move the listener inside the existing production-only block.
- Extend `build/check_ui_boot.js` so it would fail if any app.js pywebview boot path can call `boot(window.pywebview.api)` while `WANT_MOCK` is true. The check should cover both the poll and event-listener paths, not just the presence of `if (!WANT_MOCK)`.
- Keep the fix scoped to the boot boundary; do not broaden P9 into deeper frontend modularization.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, and `docs/planning/v0.18.0/phases/P9-claude-report.md`.
- Inspected product diff from baseline `bb144d4`, excluding `docs/planning/`.
- Confirmed intended product file set: `scripts/ui/app.js`, `scripts/ui/index.html`, `scripts/ui/mock.js`, `scripts/ui/contract.js`, `build/check_ui_boot.js`, `build/check_ui_contract.py`, `build/check_report_catalog.py`, `build/app.spec`, `.github/workflows/checks.yml`.
- Verified `scripts/ui/app.js` lines 1-3606 are byte-identical to `bb144d4`; first app diff is the bootstrap tail at line 3674.
- Verified `makeMockApi` moved out of `app.js` into `mock.js`; the mock function differs from baseline only at the additive `contract: window.CONTRACT` init field plus the owned `boot(makeMockApi())`.
- Ran `git diff --check bb144d4 -- . ':(exclude)docs/planning/**'` — clean apart from Git line-ending warnings.
- Ran `node --check scripts/ui/app.js`, `node --check scripts/ui/mock.js`, `node --check scripts/ui/contract.js` — all green.
- Ran `node build/check_ui_boot.js` — green, but P9-R01 shows the check is incomplete.
- Ran `python -B -X utf8 build/check_ui_contract.py` — green.
- Ran `python -B -X utf8 build/check_report_catalog.py` — green.
- Ran `python -B -X utf8 build/check_app_modules.py` — green.
- Ran `node build/check_mx_partial_render.js` and `node build/check_compare_routing.js` — green.
- Ran `python -B -X utf8 build/check_gui_bridge.py` — green.
- Ran an independent read-only probe over `scripts/ui/app.js` confirming the `pywebviewready` listener is not gated on `!WANT_MOCK`.

I did not independently rerun Claude's browser `#mock` smoke or the full `check_*.py` suite; the targeted checks above were sufficient to evaluate the P9 diff and expose the remaining boot-boundary gap.

### 6. Whether Claude may proceed toward phase approval

Claude should address P9-R01 and keep P9 marked `awaiting_review` for another Codex review. The phase should not be approved until the mock/production boot boundary is true for both the polling path and the `pywebviewready` event path, and the deterministic boot check locks that invariant.

## Review round 2

### 1. Verdict

`PASS`

### 2. Blocking findings

None.

### 3. Required fixes

None.

Prior finding disposition:

- **P9-R01** — resolved. `scripts/ui/app.js:3677-3685` now places both real-bridge boot paths (`pywebviewready` listener and poll) inside the `if (!WANT_MOCK)` block, so `#mock` registers no pywebview boot path and `scripts/ui/mock.js:1367` remains the only mock boot. `build/check_ui_boot.js:56-71` now brace-matches that gate and asserts every `boot(window.pywebview.api)` plus the listener are inside it.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`, `docs/planning/v0.18.0/05-claude-final-plan.md`, `docs/planning/v0.18.0/phases/P9-claude-report.md`, and this review file.
- Inspected product diff from baseline `bb144d4`, excluding `docs/planning/`.
- Confirmed current product scope remains P9-limited: `scripts/ui/app.js`, `scripts/ui/index.html`, `scripts/ui/mock.js`, `scripts/ui/contract.js`, `build/check_ui_boot.js`, `build/check_ui_contract.py`, `build/check_report_catalog.py`, `build/app.spec`, and `.github/workflows/checks.yml`.
- Verified independently that `scripts/ui/app.js` lines 1-3606 are still byte-identical to `bb144d4`; first app diff is now line 3671 in the bootstrap region.
- Verified independently that `scripts/ui/app.js` has zero `makeMockApi` definitions and no `boot(makeMockApi())`; `scripts/ui/mock.js` has the single mock boot call.
- Verified independently that the `!WANT_MOCK` gate contains both `boot(window.pywebview.api)` call sites and the `pywebviewready` listener.
- Ran `node --check scripts/ui/app.js`, `node --check scripts/ui/mock.js`, `node --check scripts/ui/contract.js`, and `node build/check_ui_boot.js` — green.
- Ran `python -B -X utf8 build/check_ui_contract.py` and `python -B -X utf8 build/check_report_catalog.py` — green.
- Ran `python -B -X utf8 build/check_app_modules.py` and `python -B -X utf8 build/check_gui_bridge.py` — green.
- Ran `node build/check_mx_partial_render.js` and `node build/check_compare_routing.js` — green.
- Ran `git diff --check bb144d4 -- . ':(exclude)docs/planning/**'` — clean apart from Git line-ending warnings.

I did not independently rerun Claude's browser `#mock` smoke or the full `check_*.py` suite. The targeted checks and independent containment probe were sufficient for the round-1 remediation and P9 scope.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval for P9.
