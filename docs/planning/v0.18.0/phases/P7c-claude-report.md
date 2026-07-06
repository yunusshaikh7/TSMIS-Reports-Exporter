# P7c — GUI Matrix feature-endpoint grouping — Claude report

## 1. Phase ID and name
**P7c — GUI Matrix feature-endpoint grouping.** The cohesive Matrix / by-day / TSN-library feature endpoint +
dispatch-machinery cluster is extracted out of `gui_api.GuiApi` into a `GuiMatrixMixin` behind the unchanged
façade (CR-001 / P7b-R01). The largest mechanical move in v0.18.0; behavior-neutral.

## 2. Baseline commit
`07b846b` (P7b committed) — branch `refactor/v0.18.0-structural-overhaul`; tree clean apart from untracked
`docs/planning/`.

## 3. Changes made
- **New `scripts/gui_matrix.py` (`GuiMatrixMixin`)** — the contiguous Matrix block (`_valid_baseline` …
  `_on_matrix_export_done`, **71 methods / ~1048 lines**) moved **VERBATIM** out of `GuiApi`: the matrix +
  by-day + TSN-library endpoints, the `_dispatch_*`/`_resolve_*`/`_make_job`/queue machinery, and the matrix
  `_on_*` handlers. `GuiApi(GuiMatrixMixin)` inherits them, so MRO preserves every method's name, signature,
  return shape, and event order. The mixin reaches the coordinator + shared GUI plumbing through `self`;
  `task_coordinator` stays the sole task/queue-state owner. The 5 deliberate **lazy `import tsn_library`**
  (it pulls pdfplumber via report_catalog) moved verbatim and are NOT hoisted to module load.
- **New `scripts/gui_endpoint.py`** — holds `_api_method` (moved verbatim from `gui_api`) so both `gui_api` and
  `gui_matrix` decorate endpoints without a `gui_api` ↔ `gui_matrix` import cycle (the "small shared decorator
  module" the plan anticipated).
- **`scripts/gui_api.py`** — the block removed; `class GuiApi(GuiMatrixMixin)`; `from gui_endpoint import
  _api_method` (its local def deleted); `from gui_matrix import GuiMatrixMixin`; the now-unused imports the
  block took with it trimmed (the 4 matrix workers, `collections`, `import matrix`, `import day_matrix`,
  `matrix_rows`). `_matrix_export_running` stays (shared by `request_preview`/`skip_route`, reached via `self`).
- **Tests:** `check_gui_api_surface` extended (locks the moved cluster lives in `GuiMatrixMixin`, is gone from
  `GuiApi`, still resolves on `GuiApi` via the mixin, and the public endpoints stay in the frozen 98-name
  façade); `check_matrix_bridge` + `check_day_matrix` retargeted to patch the matrix workers on `gui_matrix`
  (where the dispatch now resolves them). `app.spec` APP_MODULES += `gui_endpoint`, `gui_matrix` (F6).

## 4. Files affected
**New (2):** `scripts/gui_matrix.py` (1082), `scripts/gui_endpoint.py` (26).
**Modified (4):** `scripts/gui_api.py` (3684→2614, −1070), `build/check_gui_api_surface.py` (+matrix-grouping
test), `build/check_matrix_bridge.py` + `build/check_day_matrix.py` (worker-patch retarget), `build/app.spec`.

## 5. Architectural decisions
- **Mixin, not delegation.** A `GuiMatrixMixin` mixed into `GuiApi` keeps the pywebview façade byte-identical
  (the endpoints are inherited; `inspect`/pywebview see them on the instance via MRO) while physically moving
  the code to one cohesive module — no ~50 thin delegating stubs (which would be the "one-class-per-action
  sprawl" RM08 forbids).
- **Cycle break via `gui_endpoint`.** `GuiMatrixMixin` needs `_api_method`; `gui_api` defines `GuiApi(...)` and
  imports the mixin. Homing `_api_method` in a tiny third module removes the cycle cleanly (verified: import
  succeeds, MRO `[GuiApi, GuiMatrixMixin, object]`).
- **Verbatim move, proven by AST.** The block was cut by line range and re-homed unchanged; a verifier parsed
  the baseline `GuiApi` and the new `GuiMatrixMixin` and compared `ast.dump` per method — **71 methods, 0
  differences**. No behavior was altered (RM08: "no behavior change mixed with the move").
- **Imports resolved deterministically.** A static scan (`loaded ∩ baseline-gui_api-globals − provided`)
  proved **0 missing imports** in `gui_matrix`, and the now-unused `gui_api` imports were trimmed only when
  both AST and grep showed zero remaining uses (pre-existing unused `is_export_disabled` was left untouched —
  not P7c's scope).
- **Test patches follow the symbol.** Monkeypatched worker classes were moved from `gui_api.*` to
  `gui_matrix.*` — the checks now patch where the dispatch resolves the name. This is test maintenance for the
  move, not a behavior change.

## 6. Compatibility and migration handling
No persisted-data, format, contract, or API change. The pywebview façade is **identical** — all 98 public
methods remain on `GuiApi` (the 71 moved ones inherited via the mixin), same names/return shapes/event order;
`task_coordinator` still owns task/queue state. Verified by `check_gui_api_surface` (frozen 98-name set +
moved-cluster containment), `check_gui_bridge`/`check_matrix_bridge`/`check_b3_batch`/`check_worker_lifecycle`,
and the `#mock` all-tabs smoke. No migration. Rollback: revert the mixin extraction (the methods restore inline
on `GuiApi`); `gui_matrix`/`gui_endpoint` are additive.

## 7. Tests and commands run
All via the build venv (`build/.venv/Scripts/python.exe -B -X utf8`).
- **AST-verbatim proof** (one-off verifier, since removed): baseline `GuiApi` vs new `GuiMatrixMixin` — **71
  methods moved, 0 AST differences**; **missing-import scan: NONE**.
- **RED→GREEN on the retargeted checks:** before the patch retarget, `check_matrix_bridge` + `check_day_matrix`
  failed (the fake workers patched on `gui_api` no longer intercepted the `gui_matrix` dispatch — a `NoneType`
  capture, not a NameError); after retargeting to `gui_matrix.*`, both pass.
- **Targeted:** `check_gui_api_surface` (incl. the new matrix-grouping test) GREEN; `check_matrix_bridge`,
  `check_day_matrix`, `check_matrix`, `check_matrix_tsn`, `check_gui_bridge`, `check_b3_batch`,
  `check_worker_lifecycle` GREEN; `check_app_modules` (`gui_matrix`/`gui_endpoint` reachable) + `check_import_direction`
  (no cycle) GREEN.
- **Full offline suite:** every `build/check_*.py` (**67/67**) + the 3 Node checks — all green; byte-compile of
  `gui_api`/`gui_matrix`/`gui_endpoint`; import smoke (`GuiApi` MRO + `matrix_info` resolves); `git diff --check`
  clean.
- **`#mock` all-tabs smoke (P7c gate):** served `scripts/ui` on :8765, loaded `/index.html#mock` with fresh-
  fetched assets. `S` booted; `S.init.contract.tasks` = the 10-task enum (contract.js mirror intact); all **9
  tabs** present incl. the matrix-backed **Everything / Comparison matrix / vs TSN Matrix / Refresh & export**;
  the **Comparison matrix grid renders 32 cells**, **vs-TSN matrix 32 cells**, by-day tab clickable; **zero
  console warnings/errors**. (P7c changed no `scripts/ui/` file, so the frontend is byte-identical to P9's
  verified smoke — the smoke is positive confirmation.)

## 8. Results
Green across the board: **67/67** Python + **3/3** Node; AST-verbatim move (0 diffs); façade 98 names unchanged
+ moved cluster locked into `gui_matrix`; `#mock` all tabs render with no console errors; `compare_core`/auth/
updater untouched.

## 9. Before/after measurements
| File | Before (`07b846b`) | After | Δ |
|---|---|---|---|
| `scripts/gui_api.py` | 3684 | **2614** | **−1070 (−29%)** |
| `scripts/gui_matrix.py` (new) | — | 1082 | +1082 |
| `scripts/gui_endpoint.py` (new) | — | 26 | +26 |
| **public façade endpoints** | 98 | 98 | **0 (unchanged)** |
| methods moved (AST-verbatim) | — | 71 | 0 differences |

`gui_api.py` is materially smaller (the P7c completion criterion); the Matrix cluster is now one named
responsibility per module.

## 10. Deviations from the approved plan
- **Matrix dispatch pairs were MOVED verbatim, not unified.** P7c §I says "the matrix dispatch pairs
  (`_dispatch_compare_job`/`_dispatch_day_compare_job`, `_dispatch_export_job`/`_dispatch_day_export_job`)
  unified **where behavior-neutral**." I deliberately kept them **verbatim** (moved, not merged): unifying them
  would alter method bodies and break the AST-verbatim guarantee that makes this 1048-line move provably
  zero-behavior-change (RM08: "no behavior change mixed with the mechanical move"). The optional unify is a
  small, separate behavior-neutral cleanup that can follow without the move's risk. **For Codex:** confirm this
  is the right call, or I can do the pair-unify as a follow-up diff.
- **`_matrix_export_running` left in `gui_api`.** It's consulted by the non-matrix `request_preview`/`skip_route`/
  `cancel_run`/`pause_or_resume` (export controls), so it's shared infrastructure, not matrix-only; the mixin
  reaches it via `self`. Leaving it avoids a non-contiguous cut.
- **`gui_endpoint.py` created** for the `_api_method` cycle-break — the plan explicitly anticipated "a small
  shared decorator module to break the `_api_method` import cycle if needed."
- No other deviations. `compare_core`/auth/updater/UI untouched; no live access; nothing staged/committed/pushed.

## 11. Known limitations and external verification
- **Backend-only, offline-verified — no new work-PC item.** P7c moves Python bridge code with no behavior, UI,
  or live-path change; the façade + matrix bridge are locked by offline checks and the `#mock` smoke.
- **CR-001 statement (per Codex's required note):** this phase implements **P7c** (the Matrix feature-endpoint
  grouping). It leaves for later phases: **P8c** (engine behavior, v0.18.1 acceptance), **P9b**, **expanded
  P10**, **P12**, **P13**, **P11**. The hard-deferrals (DPAPI/O2, cert, `min-cost-pairs`) remain untouched.

## 12. Exact diff scope Codex should review
Product diff from baseline `07b846b`, excluding `docs/planning/`:
- **New:** `scripts/gui_matrix.py`, `scripts/gui_endpoint.py`.
- **Modified:** `scripts/gui_api.py`, `build/check_gui_api_surface.py`, `build/check_matrix_bridge.py`,
  `build/check_day_matrix.py`, `build/app.spec`.

Suggested focus: (a) confirm the move is verbatim (the 71 `GuiMatrixMixin` methods match the baseline `GuiApi`
bodies — an `ast.dump` diff is the fastest proof); (b) confirm `gui_matrix`'s imports are exactly what the block
needs (no missing/over-import; the lazy `tsn_library` preserved); (c) confirm the façade is unchanged and
`task_coordinator` still owns state; (d) confirm the test patch retargets (`gui_api.*` → `gui_matrix.*`) are
correct and the matrix/by-day bridge checks genuinely exercise the dispatch; (e) rule on the §10
dispatch-pair-unify deferral.
