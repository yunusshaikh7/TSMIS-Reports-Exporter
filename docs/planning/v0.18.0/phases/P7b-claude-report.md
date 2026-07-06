# P7b — GUI mechanical endpoint extraction (full depth) — Claude report

## 1. Phase ID and name
**P7b — GUI mechanical endpoint extraction (full depth).** Reclassified conditional → blocking by **CR-001**
(RM08 bounds: façade/pywebview API names + event order unchanged; no behavior change mixed with the move; no
one-class-per-action sprawl; no framework/ES-modules). Depends committed **P7a** (the `task_coordinator` state
boundary this builds on).

## 2. Baseline commit
`8eb9cc8` (P5b committed) — branch `refactor/v0.18.0-structural-overhaul`; tree clean apart from the untracked
`docs/planning/`.

## 3. Changes made
Two behavior-neutral mechanical extractions out of the 3741-line `gui_api.py` bridge, plus the RM08 surface
lock:

- **`scripts/gui_win32.py` (new)** — the scattered ctypes/Win32 blocks that were open-coded inside
  `GuiApi`/`_fatal_box` are now four pure free functions with **zero coupling** to the bridge (each takes an
  explicit hwnd / icon path / message text): `find_own_window`, `set_window_icon`, `flash_taskbar`,
  `message_box`. `gui_api` keeps the orchestration (the `notify_on_finish` gate, the icon-path resolution, the
  find→set polling loop, every best-effort `try/except` + log) and calls these for the raw Win32. `import
  ctypes` is removed from `gui_api` (it no longer open-codes any Win32 call).
- **`_begin_compare` (new private helper in `GuiApi`)** — the identical claim→save-dialog→launch→release-on-
  cancel/error tail that `start_compare` and `start_compare_env` each duplicated is now one helper; both
  endpoints validate their inputs then `return self._begin_compare(label, mode, save_dir, suggested_name,
  build)`. This is the plan's "`_begin_task` helper; unify `start_compare`/`start_compare_env`."
- **`build/check_gui_api_surface.py` (new)** — the RM08 API-surface identity check: GuiApi's public method set
  equals a frozen 98-name list (no endpoint dropped/renamed/added), the two touched endpoints keep their exact
  source signatures, `gui_win32` owns the four helpers, `gui_api` delegates (and open-codes no Win32 call), and
  `_begin_compare` has exactly two call sites with one collapsed claim tail. Wired into `checks.yml`;
  `gui_win32` added to `app.spec` APP_MODULES (F6 reachability).

## 4. Files affected
**New (2):** `scripts/gui_win32.py` (96), `build/check_gui_api_surface.py` (165).
**Modified (3):** `scripts/gui_api.py` (3741→3680; the 4 Win32 delegations + `_begin_compare` + the 2 endpoint
tails + the `import ctypes` removal), `build/app.spec` (+`gui_win32`), `.github/workflows/checks.yml` (+the new
check).

## 5. Architectural decisions
- **`gui_win32` is free functions, not a mixin.** The Win32 helpers are genuinely state-free, so free functions
  (called as `gui_win32.flash_taskbar(hwnd)`) are the simplest "one named responsibility per module" — no MRO,
  no shared-state surprises. `_find_own_window` stays as a thin `self.` delegate so its two callers are untouched.
- **`_begin_compare`, not a generic `_begin_task`.** I surveyed all 17 claim/start sites: they are heterogeneous
  (different worker classes + constructor args, `try_claim` vs P7a `claim_direct`, a blocking save dialog in the
  middle for compares, different return shapes). A single generic `_begin_task` would be a leaky, speculative
  abstraction (against KISS/YAGNI and RM08's "no sprawl"). The one genuinely-repeated, clean tail is the compare
  pair, so the `_begin_task` deliverable is realized as the compare-specific `_begin_compare` — the real,
  non-speculative DRY the plan named alongside "unify `start_compare`/`start_compare_env`."
- **Façade identity is locked by the public-method NAME set.** The `@_api_method` wrapper masks runtime arity
  (`inspect.signature` returns the uniform `(self, *args, **kwargs)`), so the enforceable façade invariant is the
  98-name set; the two endpoints P7b actually touches additionally get a source-level `def`-signature lock.
- **Behavior is byte-neutral.** Same banner/log lines, same `"compare"` gate name, same dialog/launch/release
  order, same Win32 calls in the same order. No UI file changed.

## 6. Compatibility and migration handling
No persisted-data, format, contract, or API change. The pywebview façade (98 public methods) is unchanged, so
the frontend (`app.js`/`mock.js`) binds every endpoint exactly as before — verified by the surface check +
`check_gui_bridge`/`check_matrix_bridge`/`check_b3_batch`. No migration. Rollback is per-extraction and
independent: revert the `gui_win32` delegations (the inline Win32 restores) or the `_begin_compare` collapse
(the two tails restore) without touching the other.

## 7. Tests and commands run
All via the build venv (`build/.venv/Scripts/python.exe -B -X utf8`).
- **Pre-change characterization / RED proof:** the new `check_gui_api_surface.py`'s extraction+delegation half is
  RED on the baseline `8eb9cc8` — `git show 8eb9cc8:scripts/gui_api.py` has **0** `import gui_win32`, **0**
  `gui_win32.*` calls, **8** inline `ctypes.windll`/`EnumWindows`/`FlashWindowEx` markers, **0** `_begin_compare`
  (and `gui_win32` didn't exist). After the refactor → all green.
- **Targeted:** `check_gui_api_surface` (GREEN); the bridge golden checks `check_gui_bridge` / `check_matrix_bridge`
  / `check_b3_batch` (GREEN — the façade + matrix bridge behavior unchanged); `check_app_modules` (`gui_win32`
  reachable); `check_import_direction` (no new cycle).
- **Full offline suite:** every `build/check_*.py` (now **67/67**) + the 3 Node checks — all green.
- **Frontend:** P7b touches **no** `scripts/ui/` file, so the frontend-structure verification (incl. the `#mock`
  smoke) is N/A per Codex's conditional — the `#mock` frontend is byte-identical to P9's recorded smoke. The
  Node UI checks (`check_ui_boot.js` etc.) were re-run anyway → green.
- **Hygiene:** byte-compile of `gui_api.py` + `gui_win32.py` + the new check; `git diff --check` (product) clean;
  grep confirms `gui_api` retains zero Win32 code (only docstrings mention "ctypes/Win32").

## 8. Results
Green across the board: **67/67** Python + **3/3** Node; the façade's 98 public endpoints unchanged (locked);
the bridge golden checks pass; no UI file touched; `compare_core`/auth/updater untouched. The extraction+
delegation invariants are RED-proven against the baseline.

## 9. Before/after measurements
| File | Before (`8eb9cc8`) | After | Δ |
|---|---|---|---|
| `scripts/gui_api.py` | 3741 | 3680 | −61 |
| `scripts/gui_win32.py` (new) | — | 96 | +96 |
| **public façade endpoints** | 98 | 98 | **0 (locked)** |

Product diff: **+40 / −100** across the 3 modified files. The four scattered Win32 ctypes blocks now live once
in a cohesive, testable `gui_win32` module; the two duplicated compare claim/dialog/launch tails collapsed to one
`_begin_compare` (the `'A task is already running.'` claim tail went from 2 sites to 1). Offline check suite
66 → 67.

## 10. Deviations from the approved plan
- **Scope: the Matrix feature-endpoint *module* grouping is deferred to the next P7b group-diff.** The plan's
  "Affected" lists `gui_win32`, the `_begin_task`/compare-unify, **and** "feature endpoint grouping (Matrix
  first)." This commit delivers `gui_win32` + `_begin_compare` (the first two) and the RM08 surface lock, but
  leaves the Matrix endpoints + their ~800-line dispatch machinery in `gui_api`. Rationale, grounded in the
  plan's own text: P7b is explicitly framed **"medium risk — one group per diff"** with **"Rollback: per-group
  revert,"** which sanctions incremental group delivery; RM08 makes behavior-neutrality on the field-hardened
  3741-line bridge the hard constraint, and a single commit that also moved ~800 lines of Matrix machinery into a
  mixin would be far less reviewable and materially riskier for a field regression. `gui_win32.py` already
  satisfies the "one named responsibility per module" completion criterion. **For Codex:** please judge whether
  the Matrix-module grouping must land within P7b (I'll extend in a follow-up round) or proceed as the next
  group-diff increment.
- **`_begin_task` realized as `_begin_compare`.** A generic `_begin_task` over the heterogeneous claim/start
  sites would be speculative over-abstraction (§5); the named compare-unify is the clean DRY.
- No other deviations. `compare_core`/auth/updater/UI untouched; no live access; nothing staged/committed/pushed.

## 11. Known limitations and external verification
- **Backend-only, offline-verified — no new work-PC item.** P7b changes no behavior, no UI, and no live path;
  the bridge surface + matrix bridge are locked by offline checks. There is nothing here for §K2/work-PC to
  accept (unlike P8c).
- **The Matrix-module grouping remains** (see §10) — tracked as the next P7b group-diff if Codex requires it.
- **CR-001 statement (per Codex's required note):** this phase implements **P7b's** `gui_win32` extraction +
  `_begin_compare` unify + the RM08 API-surface check. It leaves for later phases: the Matrix feature-module
  grouping (next P7b group-diff), **P8c** (engine behavior, v0.18.1 acceptance), **P9b**, **expanded P10**,
  **P12**, **P13**, **P11**. The hard-deferrals (DPAPI/O2, cert, `min-cost-pairs`) remain untouched.

## 12. Exact diff scope Codex should review
Product diff from baseline `8eb9cc8`, excluding `docs/planning/`:
- **New:** `scripts/gui_win32.py`, `build/check_gui_api_surface.py`.
- **Modified:** `scripts/gui_api.py`, `build/app.spec`, `.github/workflows/checks.yml`.

Suggested focus: (a) confirm the four `gui_win32` functions are behavior-identical to the inline Win32 they
replaced (same calls, same order, same constants); (b) confirm `gui_api` retains no Win32 code and the four
`self.`/module callers still pass the same args; (c) confirm `_begin_compare` reproduces the exact
claim→dialog→launch→release-on-cancel/error semantics of both old endpoint tails (gate name `"compare"`,
release on dialog-cancel and on exception); (d) confirm the 98-name façade is genuinely unchanged; (e) rule on
the §10 Matrix-grouping scope decision.

---

## Remediation — Codex review round 1 (`PASS WITH FIXES`)

**Round addressed:** round 1 — `PASS WITH FIXES`; **no blocking findings**; two Required (P7b-R01, P7b-R02) + one non-blocking recommendation (P7b-A01).

### Finding dispositions
| Finding | Class | Disposition |
|---|---|---|
| **P7b-R01** — approved Matrix endpoint grouping unimplemented | Required | **Fixed-with-modification** (Codex's sanctioned amendment path) — the Matrix feature-endpoint grouping is formalized as a **new blocking phase P7c** in the plan (§H/§I) + coordination (phase table + DoD). P7b's scope is now explicitly the `gui_win32` + `_begin_compare` slice. |
| **P7b-R02** — `#mock` completion gate not run/reconciled | Required | **Fixed** — recorded the explicit coordination-approved rationale that `#mock` is N/A for the backend-only P7b slice (no `scripts/ui/` change → frontend byte-identical to P9's verified smoke); **P7c carries the deterministic `#mock` all-tabs gate** (the safer default once UI-backing endpoints move). |
| **P7b-A01** — `_begin_compare` suggest-name ordering/wording imprecise | Recommended (applied) | **Fixed** — `_begin_compare` now takes a **lazy `suggest` callable** evaluated inside the claim, restoring the exact pre-P7b claim-before-suggest ordering; docstring corrected; the surface check extended. |

### Remediation changes
- **R01 — P7c formalized (the amendment path Codex offered).** Codex flagged that the deferred Matrix grouping had "no separate future P7b phase." Rather than cram the highest-risk ~1000-line / ~50-method mechanical move into a remediation turn, it is given its own properly-baselined, focused phase — matching the plan's own **"one group per diff / per-group revert"** framing and the user's **"add as many phases as needed"** (CR-001) mandate. This is **not a scope change** (the Matrix grouping was always planned); it splits P7b's "full depth" into the committed-quality infra slice (P7b: `gui_win32` + `_begin_compare`) and the Matrix cluster (**P7c**, depends committed P7b). Plan edits: P7b §I "Affected/Tests/Completion" narrowed to the slice + a new **P7c §I entry**; §H amended order `P5b → P7b → P7c → P8c → …` + classification. Coordination: P7c row added (`pending`), DoD set += P7c, P7b stays `awaiting_review`. **P7c's contract** (§I) requires: a behavior-neutral `GuiMatrixMixin` in a new `gui_matrix.py` behind the façade, façade names/return-shapes/event-order preserved, `task_coordinator` stays state owner, **`check_gui_api_surface` extended to lock the moved Matrix methods**, and the **`#mock` all-tabs smoke**.
- **R02 — `#mock` rationale recorded.** P7b touches no `scripts/ui/` file, so the `#mock` frontend is byte-identical to P9's verified smoke and the smoke cannot exercise the backend-only change; the plan §I + coordination now state this explicitly (the coordination-approved removal Codex permitted). P7c keeps the smoke.
- **A01 — lazy suggest-name (behavior-faithful).** `_begin_compare(self, label, mode, save_dir, suggest, build)` — `suggest` is a lazy callable; `out = self._save_dialog_for_compare(save_dir, suggest())` evaluates it **inside the claim `try`**, so a suggest-name error now releases the gate exactly as the pre-P7b code did (vs. the round-1 version that evaluated `suggest_name` before the claim — equivalent outcome, but the wording was imprecise). `start_compare` → `lambda: mod.suggest_name(tsmis_path)`; `start_compare_env` → `lambda: adapter.suggest_name(pa, pb)`. `check_gui_api_surface` gained two asserts: the lazy `suggest` signature + `suggest()` called inside, and both endpoints passing a lazy lambda. The helper docstring now says it releases on a "suggest-name / dialog / launch-prep error."

### Updated verification
- byte-compile `gui_api.py` + `check_gui_api_surface.py` — OK.
- `check_gui_api_surface` — GREEN incl. the **2 new lazy-suggest asserts**.
- Bridge golden checks `check_gui_bridge` / `check_matrix_bridge` / `check_b3_batch` — green (the compare path is unaffected; the lazy callable only moves *when* `suggest_name` runs, not the result).
- Full offline suite — **67/67** `check_*.py` + **3/3** Node green; `git diff --check` clean.
- No UI file touched; `compare_core`/auth/updater untouched. No new product file (A01 edits `gui_api.py` + the check); R01/R02 are planning-doc amendments only.

### Changed measurements
None material. The A01 change is net-neutral (lazy lambdas; `gui_api.py` stays 3680, façade stays 98 names). The Matrix-cluster line reduction now lands in **P7c** (its completion criterion: `gui_api.py` materially smaller).
