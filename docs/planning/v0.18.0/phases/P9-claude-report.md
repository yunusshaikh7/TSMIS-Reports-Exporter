# P9 — Frontend mock separation — Claude report

## 1. Phase ID and name
**P9** — Frontend mock separation (deeper split → O1) `[blocking (mock); depends P4, PA]`

## 2. Baseline commit
`bb144d4` (HEAD after P8b committed — "refactor: split engine into acyclic DAG layers behind common
shim (P8b)"). Baseline characterization green: `node --check app.js`, `check_mx_partial_render`,
`check_compare_routing`, `check_report_catalog`, `check_gui_bridge`; tree clean apart from the untracked
`docs/planning/`. Dependencies **P4 committed** (fixtures/catalog) + **PA committed** (the exact-artifact
gate precedes the broad UI split) — both satisfied.

## 3. Changes made
Kill the "mock as a 2nd backend" drift (F13): split the `#mock` browser-preview API out of `app.js` into
its own `ui/mock.js`, establish the frontend bridge-enum mirror `ui/contract.js`, and LOCK both the mock's
report lists and the enum mirror to the backend SSOT. **Mock separation + payload parity only — the
renderer merge + deeper app.js modularization are deferred to O1 (R1-N03).**

1. **`scripts/ui/mock.js`** (new) — the browser preview's `makeMockApi` (the simulated checks / login /
   exports / consolidation), extracted VERBATIM from `app.js`, plus the mock boot it now OWNS:
   `boot(makeMockApi())` (RR2-C3). It reads `app.js`'s top-level bindings (`boot`, `S`) as a classic
   script loaded after it. One payload-parity addition: its `get_initial_state` returns
   `contract: window.CONTRACT` so the preview's init payload carries the same bridge-enum surface the real
   `gui_api.get_initial_state` does.
2. **`scripts/ui/app.js`** — the `#mock` API + the mock boot call are removed; app.js now **auto-boots only
   in production** (`if (!WANT_MOCK)`), so the preview can never race the real pywebview bridge and the mock
   code never enters the production boot path. Lines 1–3606 (all production UI code) are **byte-identical**
   to baseline — only the bootstrap tail changed.
3. **`scripts/ui/contract.js`** (new) — the FRONTEND mirror of the bridge-enum SSoT
   (`window.CONTRACT = { tasks, terminal_kinds, env_access }`), mirroring
   `contract.initial_state_enums()` (the surface P7a added to `get_initial_state`). Classic script, loaded
   before `app.js`.
4. **`scripts/ui/index.html`** — classic-`<script>` ordering: `contract.js` → `app.js` → a `#mock`-gated
   injection of `mock.js` (createElement/appendChild, after app.js, only when the URL carries `#mock`).
5. **`build/check_ui_contract.py`** (new) — the bridge-enum mirror lock: `contract.js` `window.CONTRACT` ==
   `contract.initial_state_enums()` (exact, ordered) + the mock's init carries `contract: window.CONTRACT`.
6. **`build/check_ui_boot.js`** (new) — the deterministic boot check: each UI script COMPILES (syntax), the
   mock is out of app.js, app.js boots production-only, mock.js owns the mock boot, no missing globals
   (mock.js's `boot`/`S` are app.js top-level), contract.js exposes `window.CONTRACT`, and index.html
   orders + `#mock`-gates the scripts with no 404s.
7. **`build/check_report_catalog.py`** — `test_mock_parity` (the report-payload parity = CT-13's report
   half) retargeted to read the mock from `mock.js` instead of `app.js`. It already locks the mock's
   export / consolidate / compare lists to the independently-captured backend payload (R1-R13); no
   duplicate report check was added.
8. **`build/app.spec`** — UI-assets comment updated; `contract.js` + `mock.js` ship automatically via the
   existing `.js` allowlist. **`.github/workflows/checks.yml`** — `check_ui_contract.py` + `check_ui_boot.js`
   wired in.

## 4. Files affected
**New (4):** `scripts/ui/mock.js`, `scripts/ui/contract.js`, `build/check_ui_contract.py`,
`build/check_ui_boot.js`.
**Modified product (2):** `scripts/ui/app.js` (mock removed → production-only boot),
`scripts/ui/index.html` (script ordering + `#mock` gate).
**Modified test/packaging/CI (3):** `build/check_report_catalog.py` (mock parity → mock.js),
`build/app.spec` (comment), `.github/workflows/checks.yml` (2 new checks).
**Untouched:** `app.css`, all Python product code, `compare_core`, the engine, the bridge. The one-shot
extraction generator was deleted (not shipped). No persisted-format change.

## 5. Architectural decisions
- **Verbatim mock move + production-only boot.** `makeMockApi` is byte-identical to baseline (the only mock
  edit is the additive `contract:` parity field); app.js's production code (1–3606) is byte-identical. The
  mock owns its own boot, so production and preview never interleave.
- **Lock, don't generate.** "Report fixtures generated from report_catalog" is realized by
  `check_report_catalog::test_mock_parity` deriving the EXPECTED lists from `report_catalog` and asserting
  the mock matches — drift-proof without a build step (the no-build-step UI keeps its runtime literals; the
  check is the guard). See §10.
- **createElement gate, not document.write.** The `#mock` script injection uses createElement/appendChild
  (reliable under file:// + WebView2 + the preview, independent of parse timing) rather than
  `document.write` (which proved parse-timing-fragile).
- **No deeper split (R1-N03 / O1).** No renderer merge, no app.js modularization, no production-UI change —
  only the mock separation + the payload-parity locks.

## 6. Compatibility and migration handling
- **No production-UI behavior change.** app.js lines 1–3606 are byte-identical; the production boot path is
  unchanged except that it no longer branches into the mock (which moved out). The bundle ships the same UI
  via the `.js` allowlist (+ the two new files).
- **No persisted-format / migration.** Pure frontend file split + two offline checks.
- **Test retarget:** `check_report_catalog::test_mock_parity` reads `mock.js` now (the mock moved); no
  consumer call site changed. **Rollback:** re-inline `mock.js` into `app.js` (restore the
  `if (WANT_MOCK) boot(makeMockApi())` branch) — the split is reversible.

## 7. Tests and commands run
- **Verbatim/clean-split proof:** app.js diff vs `bb144d4` — first change at line 3674 (the bootstrap tail);
  lines 1–3606 byte-identical. `makeMockApi` defined once (mock.js), zero references left in app.js.
- **New `check_ui_boot.js` GREEN** (syntax compile of all 3 UI scripts; boot structure; no missing globals;
  index.html ordering + `#mock` gate + no 404s). **RED-proven** (reintroducing a `boot(makeMockApi())` call
  in app.js fails it).
- **New `check_ui_contract.py` GREEN** (contract.js ≡ `contract.initial_state_enums()` — 10 tasks / 14
  terminal kinds / 9 env-access; mock carries the contract field). **RED-proven** (a changed enum value
  fails it).
- **`check_report_catalog` (CT-13 report parity) GREEN** from mock.js (export 7 / consolidate 8 / compare
  groups + rows / CONS routing all == the backend). **RED-proven** (a changed mock label fails it).
- **`#mock` runtime smoke (browser preview, recorded):** with a fresh load, the `#mock` page injects all
  three scripts (`mock.js` via the gate), **boots** (`window.__tsmis` present, `S.init` set), the init
  payload carries the contract surface (`S.init.contract.tasks.length === 10`), all four main tabs
  (Export/Consolidate/Compare/Everything) switch, the Everything matrix renders (359 cells), and there are
  **zero console logs at any level**.
- **Full blocking suite (CI-style, `set -e`, `PYTHONIOENCODING=utf-8`):** all **65** `build/check_*.py` +
  **3** Node frontend checks + `node --check` of app.js/mock.js/contract.js + byte-compile — GREEN.
  `git diff --check` clean.

## 8. Results
All green. The `#mock` preview is its own file (`mock.js`) that owns its boot; app.js is production-only and
its production code is byte-identical; `contract.js` is the frontend enum mirror; and the mock's report
lists + the enum mirror are LOCKED to the backend SSOT (`report_catalog` / `contract.py`) so the preview can
no longer drift into a 2nd backend. The `#mock` boots correctly end-to-end.

## 9. Before/after measurements
| Metric | Before (`bb144d4`) | After |
|---|---|---|
| `app.js` | 5054 lines (UI + inline mock) | 3705 lines (UI; production-only boot) |
| `#mock` mock code | inline in app.js | `mock.js` (1367 lines; owns the mock boot) |
| Frontend enum mirror | none | `contract.js` (28 lines; `window.CONTRACT`) |
| Mock boot | `if (WANT_MOCK) boot(makeMockApi())` in app.js | mock.js owns it; app.js boots `if (!WANT_MOCK)` |
| app.js production code (1–3606) | baseline | **byte-identical** |
| Offline Python checks | 64 | 65 (+`check_ui_contract`) |
| Node frontend checks | 2 | 3 (+`check_ui_boot`) |
| Mock report-list drift guard | parses app.js | parses mock.js (CT-13, retargeted) |

## 10. Deviations from the approved plan
- **"Report fixtures generated from report_catalog" = LOCK, not a generated file.** The UI has no build
  step (classic scripts), so the mock keeps its runtime report literals and
  `check_report_catalog::test_mock_parity` (the existing P4 mock-parity test, which IS CT-13's report half)
  derives the expected lists FROM `report_catalog` and asserts the mock matches — drift-proof without
  committing a generated artifact. The check was retargeted from app.js → mock.js (no new/duplicate check).
- **CT-13 is split across two checks.** The report-payload parity is `check_report_catalog::test_mock_parity`
  (independently-captured catalog vs the mock); the NEW bridge-enum mirror parity is `check_ui_contract.py`
  (contract.py vs contract.js). Kept separate to avoid duplicating the report-list comparison.
- **`#mock` gate uses createElement/appendChild, not `document.write`.** `document.write` proved
  parse-timing-fragile (it failed to inject in the preview); createElement/appendChild loads `mock.js`
  reliably across file:// + WebView2 + the preview, still classic-script + `#mock`-gated (R1-R09).
- **`contract.js` runtime adoption is deferred (R1-N03 / O1).** It is loaded (available as `window.CONTRACT`),
  CT-13-locked to `contract.py`, and consumed by the mock's init payload (parity); app.js does not read it
  at runtime yet (deeper adoption is the deferred deeper-split work, mirroring how P7a established
  `contract.py` without forcing all consumers to switch).
- **No deeper split / renderer merge** (R1-N03 default). No production-UI behavior change.

## 11. Known limitations and external verification
- **Production boot (pywebview) — static + CI.** The `#mock` boot is verified at runtime (the recorded
  browser smoke). The PRODUCTION boot (real pywebview bridge, no `#mock`) can't run in a plain browser; it is
  covered by `check_ui_boot.js` (the production-only boot wiring is asserted statically) and by the frozen
  `--self-test`, which loads `index.html` (now `contract.js` → `app.js`) in the real WebView2 and waits for
  `window.__tsmis` — that gate runs in CI (`frozen-gate.yml` / `release.yml`). A live work-PC run remains the
  final acceptance (external; §M).
- **`#mock` browser cache.** As documented (docs/gui.md), the browser HTTP-caches the UI files; a reliable
  fresh `#mock` load needs `fetch(...,{cache:'reload'})` per asset then `location.reload()`. This is a
  preview/tooling property, not an app behavior; the frozen app loads fresh from the bundle.
- **Docs.** `docs/gui.md` describes the `#mock` (now a separate file) + the `contract.js` mirror; doc
  reconciliation is **P11** per the plan. The in-`app.spec`/in-file comments are updated.

## 12. Exact diff scope Codex should review
Against baseline `bb144d4` (exclude `docs/planning/`):
- **`scripts/ui/mock.js`** (new) — diff `makeMockApi` against `bb144d4:scripts/ui/app.js`'s mock section;
  it should be VERBATIM except the additive `contract: window.CONTRACT` init field + the owned
  `boot(makeMockApi())`.
- **`scripts/ui/app.js`** — only the bootstrap tail (from line 3674): the mock removed + `if (!WANT_MOCK)`
  production-only boot. Confirm lines 1–3606 are byte-identical and `makeMockApi` is gone.
- **`scripts/ui/contract.js`** (new) — the `window.CONTRACT` mirror.
- **`scripts/ui/index.html`** — `contract.js` → `app.js` → `#mock`-gated `mock.js` (createElement).
- **`build/check_ui_contract.py`** (new) + **`build/check_ui_boot.js`** (new) — the two locks.
- **`build/check_report_catalog.py`** — `test_mock_parity` read source app.js → mock.js (the only change).
- **`build/app.spec`** (comment) + **`.github/workflows/checks.yml`** (2 checks wired).

Key checks: `check_ui_boot`, `check_ui_contract`, `check_report_catalog`, the full 65+3 suite, and the
recorded `#mock` browser smoke. Suggested independent verification: diff mock.js's `makeMockApi` against the
baseline app.js block; confirm contract.js ≡ `contract.initial_state_enums()`; load `index.html#mock` and
confirm `mock.js` injects + the app boots with `S.init.contract`.

---

## Remediation — Codex review round 1

**Round addressed:** Round 1 (`PASS WITH FIXES`) — `P9-codex-review.md`. No blocking findings; the single
required finding is resolved. The phase stays `awaiting_review`.

### Finding dispositions

| Finding | Severity | Disposition |
|---|---|---|
| **P9-R01** — `#mock` can still boot the real pywebview bridge through the ungated `pywebviewready` listener | Required | **Fixed** — the listener moved inside the `!WANT_MOCK` gate; `check_ui_boot.js` now brace-matches the gate and locks containment of every real-bridge boot path. |

### P9-R01 — root cause + fix

Codex is correct. The original P9 split gated only the POLL path on `!WANT_MOCK`; the `pywebviewready`
listener was registered unconditionally and called `boot(window.pywebview.api)` whenever `bridgeReady()`.
In a pywebview context loaded with `index.html#mock`, the ready event could fire after `app.js` loads and
before `mock.js` boots — `boot()` sets `booted = true` at entry, so the real bridge would win and pre-empt
`mock.js`'s `boot(makeMockApi())`. That violates the approved P9 boundary ("app.js auto-boots only in
production; mock.js owns the mock boot"). My browser smoke missed it because a plain browser never fires
`pywebviewready` — only a real pywebview-with-`#mock` would expose the race.

Fix (scoped to the boot boundary; no deeper modularization — per Codex's caveat):
1. **`scripts/ui/app.js`** — moved the `pywebviewready` listener INSIDE the existing `if (!WANT_MOCK) { … }`
   block (at its top, before the poll). Now EVERY real-bridge boot path (listener + poll + the fatal banner)
   lives in the production-only gate, so under `#mock` app.js registers NO bridge boot and `mock.js` owns the
   boot outright. The change is confined to the bootstrap tail — app.js lines 1–3606 (all production UI code)
   remain **byte-identical** to baseline (first diff now at line 3671, the boot region).
2. **`build/check_ui_boot.js`** — replaced the weak "an `if (!WANT_MOCK)` exists" assertion with a
   containment lock: a `gateRange()` helper brace-matches the `if (!WANT_MOCK){…}` block, then the check
   asserts (a) ≥1 `boot(window.pywebview.api)` exists, (b) EVERY such call is inside the gate, and (c) the
   `pywebviewready` listener is inside the gate. So the check now fails if any real-bridge boot path (poll OR
   event listener) can run while `WANT_MOCK` is true.

### Updated verification

- **`check_ui_boot.js` GREEN** with the three new containment assertions (gate present; every
  `boot(window.pywebview.api)` inside; `pywebviewready` listener inside). **RED-proven:** reintroducing an
  ungated `pywebviewready`/`boot(window.pywebview.api)` BEFORE the gate makes the check fail ("EVERY
  real-bridge boot … inside the !WANT_MOCK gate"); restoring it passes.
- **`#mock` browser smoke re-run (recorded):** the boot wiring change does NOT regress the preview — a fresh
  `#mock` load injects all three scripts, **boots** via `mock.js` (`window.__tsmis` + `S.init`), carries the
  contract surface (`S.init.contract.tasks === 10`), switches all four tabs, and logs **zero console
  messages**. (mock.js owning the boot is exactly what the fix enforces: app.js registers no listener under
  `#mock`.)
- **Production code unchanged:** app.js lines 1–3606 byte-identical to `bb144d4` (re-confirmed). `node --check`
  of app.js/mock.js/contract.js + `check_ui_contract` + `check_report_catalog` + `check_gui_bridge` +
  `check_app_modules` + `check_source_zip_smoke` + `check_no_misspelling` + the Node frontend checks all
  GREEN. Diff scope unchanged (same 5 modified + 4 new files; this round touched only `scripts/ui/app.js`
  and `build/check_ui_boot.js`; `docs/planning/` untracked).

### Changed measurements (vs §9)

| Metric | Original P9 | After remediation |
|---|---|---|
| Real-bridge boot paths under `#mock` | 1 ungated (the `pywebviewready` listener) | **0** (listener + poll both inside the `!WANT_MOCK` gate) |
| `check_ui_boot.js` boot-boundary assertion | "an `if (!WANT_MOCK)` exists" | brace-matched containment: every `boot(window.pywebview.api)` + the listener inside the gate |
| app.js production code (1–3606) | byte-identical | byte-identical (unchanged) |
