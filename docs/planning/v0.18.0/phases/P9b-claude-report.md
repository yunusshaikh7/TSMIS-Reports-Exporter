# P9b — Frontend deeper modularization (renderer merge + app.js split) — Claude report

## 1. Phase ID and name
**P9b — Frontend deeper modularization.** The O1-deferred deeper split (CR-001): break the 3706-line
`scripts/ui/app.js` into cohesive **classic-script** modules and merge the duplicated matrix render
paths — **without framework-izing** (no framework, no ES modules; RM08). Behavior-neutral; boot-checked.

## 2. Baseline commit
`35a5af0` (P8c committed) — branch `refactor/v0.18.0-structural-overhaul`; tree clean apart from untracked
`docs/planning/`.

## 3. Changes made
- **Split `app.js` into 3 cohesive classic-script modules** (loaded BEFORE app.js, sharing the global
  lexical scope — the same mechanism `mock.js` already uses to read `S`/`boot`):
  - **`scripts/ui/ui-dom.js`** (326) — the generic DOM / theme / log / modal-dialog primitives
    (`fmtElapsed` … `showRoutePicker`, + their literal state `CHECK_ICON`/`THEME_*`/`modalResolve`).
  - **`scripts/ui/ui-matrix.js`** (1008) — the comparison-matrix + by-day-matrix renderers and their shared
    cell/queue/drag helpers (`updateMatrixProgress` … `updateDayMatrixProgress`, + `MX_HI`).
  - **`scripts/ui/ui-settings.js`** (386) — the Settings-pane renderers (`fillSettings` … `verifyEnvironment`,
    + `TSN_RAW_KIND_LABEL`).
  The moved blocks are **byte-for-byte verbatim** (proven, §7). `app.js` keeps all top-level state (`$`, `S`,
  `LOG_MAX_LINES`, `api`, `SETTING_INPUTS`, `WANT_MOCK`, `bridgeReady`), the entry points (`boot`,
  `bindEvents`, `buildStatic`), the top-level event handlers, the preview-modal cluster, the export/batch/
  consolidate/compare logic, and the `!WANT_MOCK` boot-trigger gate. The modules carry **no top-level
  execution that depends on a later app.js symbol** — they are function declarations + literal `const`s,
  plus a few self-contained top-level listener registrations that already lived at app.js top level in the
  baseline (e.g. `ui-dom.js`'s `matchMedia` theme-follow + the document click/keydown popover-close handlers,
  which reference only browser APIs + ui-dom-internal functions). So nothing at a module's load time touches a
  not-yet-loaded symbol; every cross-module reference resolves at call time (from `boot()`/handlers/event
  callbacks, after every script loaded).
- **Merged the two duplicated matrix render pairs** (the "renderer merge", D4/R1-N03), behind one parameterized
  helper each, with the **four named wrappers preserved** so callers are unchanged:
  - `syncMatrixFast`/`syncDayMatrixFast` → `syncMatrixFastControls(cbId, rowId, wkId)` (they read the SAME
    `matrix_fast` state; only the element ids differed).
  - `syncMatrixFormulas`/`syncDayMatrixFormulas` → `syncFormulasToggle(cbId, stateKey)` (each matrix keeps its
    OWN setting key).
- **`index.html`** — classic-`<script>` order: `contract.js` → `ui-dom.js` → `ui-matrix.js` → `ui-settings.js`
  → `app.js` → (`#mock`) `mock.js`; the ordering comment updated.
- **Tests:** `check_ui_boot.js` extended (compile the 3 modules; lock that representative functions are DEFINED
  in their module + GONE from app.js + still called; the merge helpers + named wrappers; the 5-script load
  order; mock.js still last); `check_ui_contract.py` gains a reference-integrity test (every `<script src>`
  index.html names exists — covers the 3 new modules); `check_mx_partial_render.js` retargeted to read
  `mxCellContent`/`MX_HI` from `ui-matrix.js` (the symbols moved).

## 4. Files affected
**New (3):** `scripts/ui/ui-dom.js`, `scripts/ui/ui-matrix.js`, `scripts/ui/ui-settings.js`.
**Modified (5):** `scripts/ui/app.js` (3706→2005, −1701), `scripts/ui/index.html` (load order),
`build/check_ui_boot.js` (+module-boundary + order locks), `build/check_ui_contract.py` (+reference integrity),
`build/check_mx_partial_render.js` (source retarget).
**No `app.spec` change** — the UI ships via the `scripts/ui/*` asset glob (`.js` ∈ `_UI_ASSET_EXTS`), so the
new modules are bundled automatically (no APP_MODULES entry, unlike a `scripts/` Python module).

## 5. Architectural decisions
- **Classic scripts sharing one global scope, NOT ES modules / framework (RM08).** Top-level `function`/`const`
  in any classic `<script>` join the shared global lexical environment; functions resolve free variables at
  call time. Load order only constrains top-level execution + the boot trigger — both kept in app.js (last
  among the real-UI scripts). This is the proven `mock.js` pattern, generalized.
- **State + entry points stay in app.js; only feature renderers move.** `SETTING_INPUTS` stays in app.js (the
  lock-sweep + `bindEvents` read it); the modules reference it at runtime. Keeps the boot/wiring surface in one
  place and the modules dependency-light.
- **Verbatim move, proven byte-exact.** The blocks were cut by boundary MARKERS (robust to line drift) and
  re-homed unchanged; a verifier compared each module's body + the app.js remainder against the baseline
  (0 differences). No body was edited during the move.
- **Bounded renderer merge.** Only the genuinely-duplicated `sync*` pairs (identical modulo ids/keys) were
  unified — provably behavior-neutral. The two big grid renderers (`renderMatrix`/`renderDayMatrix`) render
  structurally different grids (env columns vs day columns) and already share the cell/queue/progress helpers
  from earlier phases; merging them would not be behavior-neutral-provable under the offline verification, so
  they stay distinct (RM08 "bounded decomposition").

## 6. Compatibility and migration handling
No production-UI behavior change, no pywebview bridge/API-name/event-order change, no `#mock` contract change,
no persisted-data change. The 98-method bridge façade, the contract enum mirror (`window.CONTRACT`, tasks=10),
the Lesson-10 `sr-only` rule, and the browser-HTTP-cache reload procedure are all untouched. The four
`sync*` entry points keep their names/signatures (callers unchanged). Rollback: delete the 3 modules and
restore the blocks into app.js (each module is an additive verbatim slice).

## 7. Tests and commands run
- **Verbatim-move proof (byte-exact):** a one-off verifier (since removed) compared `ui-dom`/`ui-matrix`/
  `ui-settings` bodies + the new `app.js` remainder against the baseline `app.js` — **0 content differences**
  across all 4 files.
- **`node --check`** on app.js + the 3 modules (a mis-cut function would fail) — all pass.
- **`check_ui_boot.js` (extended):** all 6 scripts compile; representative functions defined-in-module +
  gone-from-app.js + still-called; the 2 merge helpers + 4 named wrappers; the 5-script load order; mock last —
  GREEN.
- **`check_ui_contract.py` (extended):** enum mirror parity + the new reference-integrity test (the 3 modules
  referenced + every `<script src>` exists) — GREEN.
- **`check_mx_partial_render.js` (retargeted)** + **`check_compare_routing.js`** (compare fns stayed in app.js)
  — GREEN.
- **`#mock` all-tabs smoke (P9b gate):** served `scripts/ui` on :8765, loaded `/index.html#mock` with all
  assets force-fetched fresh (`cache:'reload'`). Clean boot (`S` populated, `S.init.contract.tasks`=10),
  **zero console logs/warnings/errors** throughout; **every cross-module function resolves** (ui-dom +
  ui-matrix + ui-settings + app.js); 5 tabs / 5 panes / 7 report rows; **Comparison matrix renders 56 cells**
  + 6 baselines + 7 toggles; Compare tab shows the 3 sub-tabs (Cross-environment / vs TSN / vs TSN Matrix);
  Settings renders (fillSettings inputs + 6 site-URL rows + 7 TSN-library rows). Screenshot captured.
- **Full offline suite:** **68/68** `build/check_*.py` + **3/3** Node checks green; `git diff --check` clean.

## 8. Results
Green across the board: byte-exact verbatim split (0 diffs) + a bounded behavior-neutral merge; **68/68**
Python + **3/3** Node; `#mock` all tabs render with **0 console errors**; the bridge façade / contract enum /
`compare_core` / auth / updater untouched. `app.js` is 46% smaller and the UI is now 4 cohesive modules.

## 9. Before/after measurements
| File | Before | After | Δ |
|---|---|---|---|
| `scripts/ui/app.js` | 3706 | **2005** | **−1701 (−46%)** |
| `scripts/ui/ui-dom.js` (new) | — | 326 | +326 |
| `scripts/ui/ui-matrix.js` (new) | — | 1008 | +1008 |
| `scripts/ui/ui-settings.js` (new) | — | 386 | +386 |
| duplicated `sync*` render bodies | 4 | **2 helpers + 4 thin wrappers** | 2 bodies eliminated |
| pywebview façade / contract enum | 98 / tasks=10 | 98 / tasks=10 | unchanged |
| offline checks | 68 Py / 3 Node | 68 Py / 3 Node | unchanged (2 extended, 1 retargeted) |

## 10. Deviations from the approved plan
- **Renderer merge scoped to the `sync*` pairs (bounded).** The plan says "merge duplicated render paths." The
  only provably-behavior-neutral duplication is the two `sync*` pairs (merged). The big `renderMatrix`/
  `renderDayMatrix` render different grids and already share the cell/queue helpers, so they're left distinct
  (merging them isn't behavior-neutral-provable offline — RM08). Documented in §5.
- **Module-boundary lock lives in `check_ui_boot.js`** (its natural home — it already owns the app.js/mock.js
  boot structure + index.html ordering). `check_ui_contract.py` (the enum-mirror lock, P9b-neutral) was still
  extended per the plan, with a reference-integrity test (`<script src>` existence) that newly matters now that
  3 modules are referenced.
- No other deviations. No framework / no ES modules; bridge/`#mock`/UI behavior unchanged; nothing
  staged/committed/pushed.

## 11. Known limitations and external verification
- **Offline-verified; the real GUI runs on the work PC.** The split is byte-exact + `#mock`-smoked (all tabs,
  0 errors). The live pywebview/WebView2 + frozen-bundle boot (the exact shipped exe loading the 4 classic
  scripts in order) is exercised by the frozen `--self-test` gate in CI and confirmed on the work PC in the
  v0.18.1 acceptance — the same external gate every UI phase carries. No new credential/live access.
- **Docs:** `docs/gui.md`'s "app.js is one file" description is reconciled in **P11** (the plan scopes P9b to
  code; the doc sweep is P11's job).

## 12. Exact diff scope Codex should review
Product diff from baseline `35a5af0`, excluding `docs/planning/`:
- **New:** `scripts/ui/ui-dom.js`, `scripts/ui/ui-matrix.js`, `scripts/ui/ui-settings.js`.
- **Modified:** `scripts/ui/app.js`, `scripts/ui/index.html`, `build/check_ui_boot.js`,
  `build/check_ui_contract.py`, `build/check_mx_partial_render.js`.

Suggested focus: (a) confirm the move is verbatim (each module body + the app.js remainder == the baseline
slices — a byte compare is the fastest proof); (b) confirm the classic-script load order is correct and no
module top-level execution references a not-yet-loaded symbol; (c) confirm the `sync*` merge is behavior-neutral
(the wrappers reproduce the originals exactly); (d) confirm the façade/`#mock`/contract enum are unchanged and
the boot gate + handlers stayed in app.js; (e) rule on the §10 bounded-merge scope.

---

## Remediation — Codex review round 1 (P9b-R01 Required, P9b-A01 Recommended)

### Review round addressed
Codex **round 1** (`PASS WITH FIXES`): no blocking findings; one **Required** (`P9b-R01`) + one **non-blocking
recommendation** (`P9b-A01`). History preserved in `phases/P9b-codex-review.md`.

### Finding dispositions
- **`P9b-R01` — `check_ui_boot.js` module-wiring assertion counts declarations as calls — FIXED.** Codex was
  correct: the "still called (wiring intact)" assertion used `new RegExp("\\b" + fn + "\\s*\\(")`, which matches
  the function's own declaration (`function verifyEnvironment(`) — vacuous, especially for handler-bound symbols
  (`verifyEnvironment` is *assigned* at `app.js:1852` as `$("btnVerifyEnv").onclick = verifyEnvironment;`, never
  called). A moved-but-unwired function would have passed.
- **`P9b-A01` — Clarify the report wording around top-level browser listeners — FIXED (report wording only).**
  Codex correctly noted `ui-dom.js` registers a `matchMedia` theme-follow listener (`:60-61`) and the document
  click/keydown popover-close handlers (`:94-95`) at load time, so "modules contain only function declarations +
  literal consts" overstated. These are self-contained (browser APIs + ui-dom-internal functions only — no
  app.js symbol), existed at app.js top level in the baseline, and are not a defect. No product-code change was
  requested or made.

### Remediation changes
- **`build/check_ui_boot.js` (test-only):** the wiring assertion now **strips the declaration first**, then
  requires a reference to remain — a real call `fn(...)` OR a handler/value use (`= fn`, `fn,`):
  `refBeyondDecl(fn)` = `allUi.replace(/(?:async\s+)?function\s+fn\b/g, "")` then `\bfn\b`. Added an **explicit
  handler-wiring assertion** for Codex's example: `verifyEnvironment is wired to the btnVerifyEnv handler`
  (`/\$\("btnVerifyEnv"\)\.onclick\s*=\s*verifyEnvironment\b/`). The "defined in module" + "gone from app.js"
  asserts are unchanged.
- **`docs/planning/v0.18.0/phases/P9b-claude-report.md` (§3, wording):** "only function declarations + literal
  consts" → "no top-level execution that depends on a later app.js symbol … plus a few self-contained top-level
  listener registrations that already lived at app.js top level in the baseline." No product code changed for
  A01.

### Updated verification
- **RED→GREEN proven for the strengthened assertion** (one-off probe, since removed): on a synthetic *unwired*
  `verifyEnvironment` (its only real reference, the `btnVerifyEnv` handler, removed) the **old** check returns
  `true` (vacuous — the gap), the **new** check returns `false` (catches it); on the **real** (wired)
  `verifyEnvironment` the new check returns `true` (the handler ref is present). So the assertion is now
  non-vacuous and would catch a broken moved-function wiring.
- **`check_ui_boot.js` GREEN** — all 15 representative-function wiring asserts now read "referenced beyond its
  declaration", plus the explicit `verifyEnvironment ← btnVerifyEnv` handler lock; the module-boundary / merge /
  load-order asserts unchanged.
- **Full suite still green:** **68/68** `build/check_*.py` + **3/3** Node; `node --check` all 4 UI scripts;
  `git diff --check` clean; no temp files left. The product diff is unchanged (the `#mock` all-tabs smoke from
  the original report still stands — no product code was touched in this round).

### Changed measurements
| Area | Round-1 P9b | After remediation |
|---|---|---|
| `check_ui_boot.js` wiring assertion | `\bfn\s*\(` (matches the declaration — vacuous, P9b-R01) | declaration-stripped reference + explicit `verifyEnvironment ← btnVerifyEnv` lock |
| product diff (3 new + 5 modified) | — | **unchanged** (only `check_ui_boot.js` + the report changed this round) |
| offline checks | 68 Python / 3 Node | 68 Python / 3 Node (unchanged) |

Phase remains `awaiting_review`; nothing staged/committed/pushed.
