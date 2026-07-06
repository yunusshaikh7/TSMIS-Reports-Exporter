# v0.18.0 — Claude Investigation Report

**Release theme:** structural optimization + engineering overhaul (maintainability,
architecture, reliability, testing, security, performance, packaging, shipped-app
cleanup). Few/no major new features.

**Investigator:** Claude (primary planner + eventual sole implementer).
**Method:** read-only repository investigation — baseline measurement, a five-way
parallel deep-dive fan-out (each agent's claims re-verified against current code by
the lead), reconciliation of the prior Phase-3 audit against HEAD, and protected-contract
extraction. No application source, tests, build config, or existing docs were modified.

> This is **not** the final plan. It is the evidence base the plan derives from. A
> second independent investigation (Codex) is running in parallel; §12 lists what it
> should challenge. Reconciliation happens after both land.

---

## 0. Baseline (commands + results)

Recorded at the start of the turn; the tree did not change during the investigation.

| Fact | Value |
|---|---|
| Branch | `main` |
| HEAD | `d2ee353` (`docs: reconcile roadmap to v0.17.1 + log the two deferred follow-ups`) |
| Latest tag | `v0.17.1` |
| `version.py` | `__version__ = "0.17.1"`, `APP_NAME = "TSMIS Exporter"` |
| Working tree | **clean** (`git status --porcelain` empty), up to date with `origin/main` |
| Tracked files | 187 (73 `build/`, 56 `scripts/`, 31 `docs/`, 2 `.github/`, …) |
| `build/.venv`, `dist/` | **not tracked** (local artifacts; `.gitignore` correct) |
| `code-review/` | **not tracked** (git-ignored local audit scratch) |
| Toolchain | `build/.venv/Scripts/python.exe` = CPython **3.11.0**; runtime deps present |

**Compile baseline (green):**
```
python -m compileall -q scripts build version.py      → OK (all tracked .py compile clean)
git ls-files 'scripts/*.py' 'build/*.py' version.py | xargs py_compile  → OK
```

**Regression baseline (green) — the exact CI blocking set, run locally with the venv:**
```
44 golden checks (checks.yml order, PYTHONIOENCODING=utf-8)  → PASS=44 FAIL=0 TOTAL=44
```
This is the known-good floor every v0.18.0 phase must hold. (`check_fake_site.py`
falls back to system Edge / skips cleanly; it passed here.)

**Authoritative module sizes** (`wc -l`; files are **CRLF**, so PowerShell
`Measure-Object -Line` under-reported by ~4–6% — the numbers below are the real ones):

| Module | Lines | Shape |
|---|---:|---|
| `scripts/ui/app.js` | **5003** | one flat file, 117 top-level fns, no modules; 1330-line `#mock` inside |
| `scripts/gui_api.py` | **3525** | a **single `GuiApi` class**, 97 js_api methods |
| `scripts/compare_core.py` | **1953** | regression-locked comparison engine |
| `scripts/gui_worker.py` | **1862** | 15 `threading.Thread` worker classes |
| `scripts/common.py` | **1653** | 8 distinct responsibilities (kitchen sink) |
| `scripts/ui/app.css` | 1511 | |
| `scripts/ui/index.html` | 1021 | |
| `scripts/matrix.py` | 877 | |
| `scripts/consolidate_ramp_summary.py` | 741 | largest consolidator |
| `scripts/updater.py` | 730 | most carefully-reasoned module in the repo |
| `scripts/settings.py` | 621 | |
| `scripts/exporter.py` | 583 | |

`scripts/` totals **~22,200 lines** across 53 `.py`; `scripts/ui/` adds **~7,535**;
`build/` (tracked) **~8,377**. The project's own guideline is **<800 lines/file** —
five modules blow past it, two by **4–6×**.

---

## 1. Current architecture & execution-flow map

**One console-free core, two front-ends** (this is the load-bearing design; see §7):

```
                       ┌─────────────── scripts/reports.py (single registry) ───────────────┐
                       │  EXPORT_REPORTS · CONSOLIDATE_REPORTS · COMPARE_REPORTS · GROUPS     │
                       └────────────────────────────────────────────────────────────────────┘
 .bat console flow                                   Packaged GUI (pywebview / Edge WebView2)
   cli.py / run_report.py                            gui_main.py ──(entry; swap-mode FIRST)──┐
        │                                                  │                                  │
        └──────────────┐                            gui_api.py  (GuiApi: js_api bridge +      │
                       ▼                              state snapshot + 2 queue pumps + gate)   │
              ┌──────────────────┐                         │  ▲ events (kind,payload)         │
              │   Events sink    │◄────────────────────────┘  │                               │
              │  (events.py)     │                     gui_worker.py (15 Thread workers)       │
              └──────────────────┘                            │                               │
                       │  raises exceptions, never print/input/sys.exit                       │
        ┌──────────────┼───────────────────────────────────────────────┐                     │
        ▼              ▼                         ▼                       ▼                     │
   exporter.py    common.py              consolidate_*.py          compare_*.py /             │
   (run loop,    (auth state machine,   (per-route → workbook;     compare_core.py            │
   _recover,      Playwright lifecycle,  consolidate_xlsx_base,    (regression-LOCKED) +      │
   save_*)        timeouts, routes,      TSN/PDF parsers)          compare_env / matrix /     │
   exporter_      browser channels,                               day_matrix / tsn_*          │
   parallel.py    edge device SSO)                                                            │
        └────────────────────────────── output/<YYYY-MM-DD src-env>/<report>/ ────────────────┘
                                          scripts/ui/ (app.js / index.html / app.css) ◄── WebView
```

**Entry / startup chain** (`gui_main.main`, verified): `SWAP_FLAG` branch →
`setup_logging` → `_unblock_dotnet_assemblies` (MOTW strip) → `updater.cleanup_leftovers`
→ `import gui_api` → `gui_api.run()`. The swap-mode-first ordering is a hard invariant
(§7) with **no automated assertion** (§5/I).

**Dependency direction (verified clean):**
- 14 modules import `common`; `common` is the hub.
- `settings.py` and `paths.py` are **leaves** (neither imports `common` — confirmed;
  the architecture relies on this so the console flow reads settings without pulling the
  engine).
- The `from cli import run_consolidate_cli` lines in every `consolidate_*.py` are
  **`__main__`-guarded lazy imports** (verified at `consolidate_ramp_summary.py:840`),
  so the console-free contract holds — importing a consolidator never pulls the driver.
- No core module imports `gui_*`/`webview` at module scope. Boundary intact.

**Registry contract (the spine):** `reports.py` is the single source of truth for both
front-ends — but selection across the three lists is **by positional index**, and that
index is a cross-layer contract (Python → on-disk manifest → JS). This is finding **§4.B**.

---

## 2. Evidence-backed structural findings (the maintainability core of v0.18.0)

The Phase-3 audit (2026-06-18) was **risk-domain focused** (reliability/security/updater).
The **structural/maintainability dimension is largely un-audited** — and it is exactly
what "engineering overhaul" means. The five deep-dives converge on the same shape: a
small number of **god-objects** plus **multi-source-of-truth duplication** that can
silently drift.

### 2.1 God-objects / oversized modules (HIGH)

| File | Lines | Diagnosis | Concrete split seams (already self-evident in the code) |
|---|---:|---|---|
| `app.js` | 5003 | One flat script, 117 globals, no module boundaries; 11+ scattered `let` state-globals besides `S`. | `mock.js` (the 1330-line `#mock`, §2.2), `bridge.js`, `matrix.js`, `modals.js`, `settings.js`, `export.js`/`compare.js`, `dom.js` (a `el()` helper absorbs ~180 `createElement`), `state.js`. |
| `gui_api.py` | 3525 | A **single class** with 97 js_api methods + ~40 privates spanning ~25 feature surfaces; the matrix surface alone is ~1050 lines / 35 methods. | The class already has `# ----` section comments = ready boundaries: `gui_state.py`, `gui_win32.py` (~140 lines pure ctypes, zero coupling), `MatrixApiMixin` (~1050), `ExportApiMixin`, `CompareConsolidateApiMixin`, `SettingsApiMixin`, `UpdaterApiMixin`. |
| `gui_worker.py` | 1862 | Already class-segmented (15 workers) — less acute, but the workers share massive boilerplate (§2.4) and the module docstring is stale (§2.6). | Group by domain (export/batch, matrix, auth/login/env, updater/chromium) once the shared base is extracted. |
| `common.py` | 1653 | 8 unrelated responsibilities in one file (exception taxonomy, site pin, timeouts, routes, auth state machine, report-nav, browser channels, edge-device SSO). `navigate_with_auth` is a ~115-line 6-state machine — the hardest code in the app, in one function. | `errors.py`, `site.py`, `timeouts.py`, `routes.py` (pure, no Playwright — extract first), `auth_state.py`, `browser_channels.py`, `edge_device.py`, `report_nav.py`. Keep `common.py` a **thin re-export shim** during migration (14-module blast radius). |
| `compare_core.py` | 1953 | Large but **regression-locked** (§7). Decomposition here is high-risk and low-reward. | **Leave structurally intact** in v0.18.0; only extract opt-in helpers (notes/legend writer) that the schema already plumbs. |
| `matrix.py` / `day_matrix.py` | 877 / 362 | Correctly share the compute path (`consolidate_and_compare_tsn`) but duplicate the **orchestration shell** (results cache 3×, snapshot builder 2×, rebuild-list 2×). | Extract `matrix_cache.py` + a snapshot substrate; **keep the two orchestrators separate** (env-axis vs day-axis genuinely differ). ~120–150 lines collapse. |

### 2.2 The `#mock` API is a 1330-line second source of truth (HIGH, frontend)

`makeMockApi()` (`app.js:3674–5003`, **27% of the file**) re-implements the entire
backend contract by hand: the report lists, the full 15-row `compare_reports` registry,
the matrix/day-matrix snapshot generators, a job-queue simulator, and ~95 mock methods
mirroring `gui_api` one-for-one. The maintenance burden is **already visible and already
drifting**: comments like *"Mirrors the real reports.COMPARE_REPORTS (15 rows as of
v0.17.0)"* (`app.js:4238`) and *"Indices shifted +2 in v0.17.0"* (`app.js:4839`), plus
stale incidental data — the mock reports `version: "0.14.2 (preview)"` (`app.js:4217`)
and *"latest version (v0.8.0 preview)"* (`app.js:4951`) while the app is at 0.17.1. Every
registry change requires a hand-synced edit in two languages with no compile-time check.

### 2.3 Report-family duplication (HIGH — the highest-ROI/lowest-risk DRY target)

Quantified by the report-family deep-dive (all anchors verified):

- **`tsn_load_*.py` (4 files, 368 lines) — ~280 lines (~75%) collapsible** into one
  `tsn_library.build_normalized(report, raw_glob, projector, header=…)` factory. `_find_raw`
  (`max(glob, key=mtime)` skip `~$`) is identical 4×; the `build_into` skeleton and the
  **blue header style block** are copy-pasted (the *same* header style appears **7×** across
  `tsn_load_*`, `consolidate_tsn_*`, and `consolidate_xlsx_base`). **Zero regression-lock
  exposure** — these outputs aren't locked. Do this first.
- **`compare_*_tsn.py` (5 files, ~1380 lines) — ~280–330 lines collapsible** into a shared
  `run_files_compare(schema, load_tsmis, load_tsn, banner)` driver + a `compare_tsn_normalize`
  helper module. The `compare()` adapter (~30 lines), the `for p, side in (...)` existence
  check (8×), the `events.on_log("="*60)` banner, `suggest_name()` (7×), and the FLAT
  loader skeleton are mechanical repeats. `_norm_pm` is byte-identical 2×; `_norm_route`
  ("zero-pad numeric, keep suffix") appears **5×** (`compare_ramp_detail_tsn:76`,
  `compare_intersection_detail_tsn:107`, `compare_env:48`, `consolidate_tsn_highway_log:293`,
  `consolidate_tsn_highway_sequence:129`). **Touches only the pre-`run_compare` shell** —
  `compare_core` stays untouched; re-run the 6 vs-TSN canaries to prove it.
- **`_write_notes_sheet`** duplicated (`compare_intersection_detail_tsn:241`,
  `compare_highway_sequence_tsn:200`); a `compare_core.make_notes_sheet(...)` opt-in helper
  removes ~40 lines safely.
- **`consolidate_xlsx_base.py` is used consistently** (4 XLSX wrappers + both TSN-PDF
  consolidators delegate their combine step) — this is **good** factoring; no action beyond
  optionally a tiny `make_xlsx_consolidator()` for the 4 thin wrappers (~40 lines, low value).
- **`settings.py` atomic-write block copy-pasted 4×** despite `_atomic_write` existing
  (`update:158`, `set_site_url:271`, `set_batch_dest:315`, `set_matrix_baseline:359` — the
  newer setters use the helper, the older ones never migrated). Confirmed at HEAD.

### 2.4 Backend boilerplate duplication (MEDIUM, GUI backend)

- **Task-starter ritual repeated ~12×** in `gui_api` (validate → claim gate → clear events →
  `_emit_log` → `_set_dot("busy")` → `run_started` → `_push_state` → `Worker().start()`):
  `start_export:1236`, `start_consolidate:2825`, `verify_environment:2663`, `start_reset:3259`,
  `rebuild_tsn_library:2154`, the matrix `_dispatch_*`, etc. → one `_begin_task(...)` helper
  (~120 lines).
- `start_compare` / `start_compare_env` are ~90% identical; the four matrix `_dispatch_*` /
  `_resolve_*` methods are pairwise near-identical with a `which == "day"` branch — both want a
  single parametrized path.

### 2.5 Magic-string contracts with no single source of truth (HIGH, drift surface)

The Python↔JS boundary is held together by **hand-synced string literals** with a
**silent-drop default on both ends**:

- `state.task` — a **9-value enum** compared as string literals at ~15 sites across two
  languages (`gui_api` `cancel_run`/`request_preview`/`skip_route`/`pause_or_resume` + ~9
  `st.task === "..."` sites in `app.js`). A rename leaves a button stuck enabled/disabled.
- `env_access[].status` — an **11-value enum** (`ok`/`denied`/`wrong_site`/…) produced as
  scattered literals in `gui_worker.check_one`/`env_verdict`, mapped through a JS lookup table;
  an unmapped value falls through to red "Check failed", **masking the real status**.
- `update.phase` (8), `login_phase` (4), comparison `cmp.missing_side` (`tsn`/`baseline`/
  `both`/…), `run_started.mode` (with `consolidate` overloaded as the generic indeterminate
  mode), mode ids `env`/`tsn`/`vs_pdf`/`vs_excel`/`self`, `DAY_MATRIX_GROUP="tsn_by_day"`.
- `cmp.verdict` is **on the wire but unused** by the real JS render (it keys off counts) — a
  dead field that the mock still maintains.

### 2.6 Dead / stale / doc-drift residue (LOW–MEDIUM)

- `gui_worker.py` module docstring (lines 1–7) still describes the **pre-v0.8.0 Tkinter**
  model ("never on the Tk main thread", "root.after()") and omits 4 real emitted kinds
  (`check`, `checks_done`, `batch_progress`, `batch_done`). **Confirmed at HEAD.**
- `gui-bridge.md §8` describes a **superseded LoginWorker order** (claims device-SSO-first;
  the code does Chrome/Chromium-headed first and `try_device_sso_login` isn't called by
  LoginWorker at all). The internals docs' **line citations are stale by 100–400 lines**
  (the files grew). `build-and-release.md`'s CI section lists a **stale ~25-check subset**
  (CI actually runs all 44).
- `login.py` docstring still references "the GUI (Phase 4)" / `input()` as future.
- `_TSN_MATRIX_EXTRA = []` and `DISABLED_EXPORT_SUBDIRS = set()` are **empty but still
  consumed** (dormant-but-load-bearing scaffolding — CI-locked by `check_intersection_gate`;
  keep, but document as "exercised only by the synthetic gate").
- `paths.output_day_dir(day=None)` flagged as candidate-dead by the seeds; grep before removal.
- `cmp.verdict` dead-on-wire (above); `set_batch_dest` mock method has no caller.

---

## 3. Exact affected files / symbols / responsibilities / contracts

The per-file map the implementation phases will key on (✎ = changes; 🔒 = touch only via
opt-in / with canary re-proof; ⛔ = do not change behavior):

| File | Responsibility | v0.18.0 disposition |
|---|---|---|
| `reports.py` | The 3 registries + matrix derivation | ✎ add stable `key` per row; keep index as display-order only |
| `batch_manifest.py` | Persists paused-batch `reports:[int]` | ✎ persist keys; **int back-compat shim on load** |
| `gui_worker.py:491` | Manifest replay `EXPORT_REPORTS[i][2]` | ✎ key lookup (this is the **data-correctness** seam, §4.B) |
| `gui_api.py:599 _pick_report` | `registry[i]` chokepoint | ✎ `_pick_report(registry, key)` dict lookup |
| `app.js` `dataset.idx` | Index round-trip to bridge | ✎ `dataset.key`; ✎ split file; ✎ extract mock |
| `common.py` | 8 responsibilities | ✎ decompose behind a re-export shim; 🔒 `navigate_with_auth` logic (work-PC-tied) |
| `settings.py` | Persisted config | ✎ route 4 writers through `_atomic_write`; ✎ validation-at-boundary; consider `_SCHEMA_VERSION` |
| `paths.py` | Path resolution | ✎ move import-time `os.environ` mutation to explicit init; ✎ `_safe_join` containment |
| `gui_api.py` | js_api bridge | ✎ split into mixins + `gui_win32.py`; ✎ `_handle` default branch; ✎ enum SSOT; ✎ `_begin_task` |
| `tsn_load_*.py` (4) | TSN normalize glue | ✎ collapse into `tsn_library.build_normalized` factory |
| `compare_*_tsn.py` (5) | vs-TSN adapters | ✎ shared `run_files_compare` + `compare_tsn_normalize`; 🔒 the `_SCHEMA`/rows into `run_compare` |
| `compare_core.py` | Comparison engine | ⛔ formula/label TEXT; opt-in noop fields only |
| `matrix.py` / `day_matrix.py` | Two matrices | ✎ extract `matrix_cache.py` + snapshot substrate; keep 2 orchestrators |
| `updater.py` | Self-update | 🔒 cert-store TLS, swap order, allowlist; ✎ U-2 checksum-enforce, U-1 signature slot (when cert lands) |
| `gui_main.py` | Entry + swap-mode | ⛔ swap-mode-first ordering; ✎ add an AST/static assertion test for it |
| `build/app.spec` | PyInstaller | ✎ derive/check `APP_MODULES` completeness; ✎ filter UI `datas` by extension |
| `.github/workflows/checks.yml` | CI | ✎ consider frozen self-test on PR (label/nightly); ✎ pip-audit build reqs; ✎ run prune content-guard |

---

## 4. Maintainability & coupling hotspots (ranked)

**A. The two giant god-objects** (`app.js` 5003, `gui_api.py` 3525) — every change risks
unrelated surfaces; neither can be reasoned about in isolation; both violate the project's
own <800-line rule by 4–6×.

**B. Index-based report selection — a real data-correctness vector, not just a smell (HIGH).**
Selection across `EXPORT_REPORTS` (7) / `CONSOLIDATE_REPORTS` (8, different order) /
`COMPARE_REPORTS` (15) is by positional index, and that index is the contract in **Python,
the on-disk manifest, and JS**. The worst exposure: a batch paused under v0.17.x persists
`reports:[0,3,5]`; if v0.18.0 reorders `EXPORT_REPORTS`, `gui_worker._specs` (`:491`)
**silently resumes the wrong reports** — the `0<=i<len` guard catches out-of-range, not
semantic drift. The code itself admits the fragility (`reports.py:152` *"Appended at the END
so the registry indices above are unchanged"*). The **matrix subsystem already uses stable
string keys** (`matrix_rows()` → `row_key`) — proof the migration target works.

**C. Multi-source-of-truth duplication** — the 1330-line mock (§2.2), the 9/11-value enums
(§2.5), the report-family skeletons (§2.3), two ditto definitions (`highway_log_columns.is_ditto`
vs `compare_core._is_plus_run`), duplicated calibration constants (`Y_TOLERANCE`/`WORD_GAP`
across both PDF parsers + ramp summary). Each pair can drift independently with no guard.

**D. `common.py` as the 8-responsibility hub** with a 14-module blast radius — route parsing,
timeout math, and a 6-state OAuth machine share one file.

**E. Two silent-drop dispatch defaults** — `gui_api._handle` (35 `kind ==` branches, **no
`else`**, confirmed) and `app.js dispatch` (`default: break`). A renamed event produces **no
symptom anywhere**. One-line fixes, high value.

---

## 5. Reliability / testing / security / performance / packaging findings

### Reliability & error-handling
- **Field-reported updater bug — `download_and_stage` extract→staged rename has no retry**
  (~20% failure on the work PC; Defender/indexer holds the freshly-extracted tree → `WinError 5`).
  **Status: marked FIXED** in roadmap (commit `3839ec9`, wrapped in the swap step's `_retry`,
  locked by `check_updater.py`) but carries **⚠ field-verify owed** (work-PC-only). Confirm it's
  actually in the code and the lock is real during v0.18.0.
- **`set_site` process-global mutated without a lock** (`common.py:103`), read by `get_site`/
  `get_url`/`expected_host` on the export thread; `BatchWorker` mutates it per-env. The docs claim
  the single-task gate makes this safe, **but the gate lives in `gui_api`, not the core, and
  `ActiveEnvCheckWorker` runs outside it** — a stray `get_site()` during a batch could derive a
  wrong-env output folder (the exact class `require_site_params` exists to prevent). `get_url()`/
  `expected_host()` re-read the live global mid-`_recover`. (HIGH — verify reachability; §12.)
- **`_resolved_channel`/`_resolved_parallel` global caches** race-written by N parallel workers
  (idempotent today, but unsynchronized RMW on the hot path).
- **`should_cancel` not threaded into `_recover`/retry/portability navigations** — a Stop during a
  mid-run re-auth waits out the full 60 s budget (the v0.17.1 cancel-fix covered only the initial
  `navigate_with_auth`). Matches the two deferred v0.17.1 follow-ups in the roadmap.
- **Unbounded worker→`_q` queue** (`gui_api:133`); **`_on_error` reads gate locals outside the
  lock**; **`verify_environment` has no cancel path** (only task that can wedge the gate with no
  user escape, bounded only by the sign-in budget).
- **Silent / under-logged swallows** violating the "log `type(e).__name__` + first line" contract.
  Worst cluster (all auth/recapture path, where a swallowed type is most expensive):
  `common.py:611` (`is_logged_in` — the most-called auth predicate, fully silent),
  `:1307`/`:1379`/`:1287`/`:427` (capture chains). In the GUI backend: `save_support_bundle`
  per-file `OSError` silent (`:3346/3354` — the diagnostics bundle silently omitting the files a
  maintainer needs), `_chromium_state` size walk (`:3044`), the `_safe_close*` browser-close
  swallows in `gui_worker` (a leaked browser process leaves no trace). `report_error_text`
  (`common.py:781`) is the **model to copy** (it logs the type + explains *why* a silent None is
  dangerous).

### Testing (characterization safety net — see §9 for why this gates everything)
- **CI runs all 44 golden checks** (none orphaned) — strong coverage of the comparison engine,
  consolidators, matrix bridge, export engine, and updater **pure helpers**. This is a real asset.
- **Critical behaviors with NO golden check** (fill BEFORE the matching refactor):
  `gui_main.py` (the swap-mode-first ordering + MOTW + bootstrap — **highest-value gap**, only
  touched by release-only `full_smoke.py`); **`app.js` (no unit test at all** — only the manual
  `#mock`); `login.py`, `cli.py`/`run_report.py`, `logging_setup.py`; `ExportWorker.run()`'s real
  loop; `updater.perform_swap`'s post-1.5 s-crash + real relaunch (work-PC-only).
- **The frozen build is never exercised on PRs** (C-1, HIGH) — only `release.yml` (tag push)
  freezes. So `APP_MODULES` drift, a stray UI file, a broken `excludes`, or reintroduced
  DLP content all **pass CI and fail only at release**.

### Security (no new CRITICALs; the documented posture holds)
- **Updater authenticity = TLS + sibling SHA-256, no signature** (P1, known, **blocked on the
  SignPath cert**). The cert-store TLS itself is **correct and must not change** (§7). U-2: when no
  checksum is published the download proceeds on **size only** — `release.yml` reliably publishes
  the `.sha256` but nothing *enforces* it.
- **Auth token plaintext at rest** (`common.py:save_auth_state`, NTFS perms only). DPAPI is the
  documented candidate — **but see §10: DPAPI is user+machine-scoped and would break the
  documented auth-file *portability* feature** (`storage_state_is_portable`), so it is **not** a
  free win.
- **Headed-Edge sign-in opens an unauthenticated CDP port on `127.0.0.1`** for the whole SSO
  session (P2, open). `dump_auth_failure` writes full page HTML/screenshots to `FAILURES_DIR`
  with **no retention/cleanup** (as sensitive as the reports themselves).
- **`support_bundle` embeds `settings.all_settings()`** — safe today, would auto-leak any future
  sensitive setting (P3).
- **Frontend XSS surface ≈ nil** (zero `innerHTML`; all dynamic content via `textContent`/
  `createElement`) — a genuine strength to preserve.
- **Deps pinned (`==`) but not hash-pinned** (`--require-hashes`); `cryptography` is a hard
  transitive (pdfminer) that appears in no requirements file; **Playwright version duplicated**
  in `version.py` and `requirements.txt` with no consistency check.

### Performance / startup / bundle
- **Bundle floor ~80 MB is `node.exe`** (the Playwright Node driver, used only to *launch* the
  system browser). Default bundle ~148 MB. The single biggest shrink lever — but likely
  inseparable from Playwright; needs a spike to quantify (§10). Locale prune already reclaims
  ~42 MB on the with-browser variant.
- `paths.py` mutates `os.environ["PLAYWRIGHT_BROWSERS_PATH"]` at **import time** — an invisible
  global side effect (importing `common` mutates process env); move to explicit init.
- `exporter.run_export` calls `has_valid_auth()` ~3× per run (re-reads/validates the file each
  time) — snapshot once.

### Packaging
- `APP_MODULES` (`app.spec:67`) is a **hand-maintained ~55-module list** — a split/rename ships a
  broken frozen build that **passes all of CI**. `datas` ships *whatever* is in `scripts/ui/`
  (`os.listdir`, no extension filter). `prune_bundle.ps1` (the DLP guard — a strong asset:
  Luhn-checked card scan, PEM/AWS/SSN guards) runs **only at release, never in CI**, and hard-codes
  the Playwright driver dir layout (a minor bump silently no-ops the prune; the content guard then
  fails late with a confusing message).

---

## 6. Prior-audit reconciliation (Phase-3 @ `0a4c071` vs HEAD `d2ee353` — 91 commits apart)

The Phase-3 review confirmed **45 findings (5 P1 · 17 P2 · 23 P3)**, 12 rejected on refutation.
The audit commit is **91 commits behind HEAD**; the roadmap is the canonical reconciliation. I
verified the still-open items against current code.

**FIXED since the audit (confirmed via roadmap + spot-checks):**
- Field bug `update-stage-rename-no-retry` (commit `3839ec9`) — ⚠ field-verify owed.
- **4 of 5 P1:** `navigate-accepts-wrong-env-after-one-reload` (`require_site_params`),
  `empty-routes-read-as-export-complete` (amber completion), `transient-export-click-failure-
  recorded-empty` (in-loop retry), `reset-deletes-unvalidated-batch-dest` (scoped delete). Several
  carry ⚠ live work-PC re-test owed.
- **~6 P2:** the PDF Highway-Log silent-drop trio (v0.17.0 stats banner), `report-error-text-
  blanket-swallow` + `highway-sequence-errored-route`, `auto-consolidate-rmtree` (stage-and-swap),
  the parallel-reconcile pair (`_reconcile_unaccounted` lock-tolerant + crash+cancel).

**STILL OPEN and re-verified real at HEAD:**
- P1 `update-trust-is-tls-plus-sibling-sha-only` — **blocked on the SignPath cert** (in progress).
- P2: `edge-login-cdp-port-unauthenticated-loopback`; `auth-file-plaintext-no-acl-dpapi`; updater
  integrity trio (`size-and-checksum-guards-both-skippable`, `immediate-death-check-narrow-window`,
  `no-rollback-when-relaunch-launches-partial-tree`); `select-report-substring-match-no-exact-guard`
  (**confirmed** `common.py:732` `has_text=…).first`); `handle-no-default-branch` (**confirmed** —
  35-branch dispatch, no `else`); ramp-summary parsing pair.
- P3 hygiene (≈20 open): stale Tkinter docstring (**confirmed**), magic `wait_for_timeout(1000)`
  (**confirmed** `exporter.py:343`), `update_helper.log` no rotation, dev WebView-cache clearing,
  `_min_cost_pairs` greedy cliff at 8+ dups, ramp-summary combined-sheet hard-coded coordinates,
  env-compare side-label cap truncating the distinguisher, etc.

**OBSOLETE / do-not-re-raise:** the 12 refutation-rejected candidates (e.g.
`signed-in-selectors-single-point-of-failure` — fails loud; `paths-import-time-env-mutation` —
intended; `settings-mtime-cache-same-second-write` — below bar). **Exception:**
`settings-duplicate-atomic-write` was rejected *as a risk* but the audit explicitly notes it is
"valid as a routine refactor" — it is legitimate v0.18.0 maintainability work (§2.3).

**VALIDATED & PROTECTED (do not "fix"):** the Stage-1 foundation audit (2026-06-18) proved
consolidate + cross-env compare for HSL/Ramp Detail/Ramp Summary **cell-accurate across the full
6-env batch, ≥3 independent ways, zero tool bugs**. The Ramp Summary "Source ≠ total" 9-route
quirk is a **source-data** issue, correctly flagged RED — must NOT be forced green.

**UNCERTAIN / work-PC-only:** many "Done" P1/P2 items carry "⚠ LIVE work-PC re-test owed" — the
dev PC cannot reach TSMIS, so v0.18.0 cannot close these either; they stay owed.

---

## 7. Protected behavior & dangerous refactors to avoid

These are the repository's real contracts. **A v0.18.0 change that violates any of these is a
regression regardless of how clean it looks.**

1. **`compare_core` regression lock.** Formula/label TEXT is cell-for-cell locked. `_DIFF_MARK
   = " ≠ "` is the only differing-cell marker (CF, COUNTIFs, `matrix.read_counts` all key on the
   literal). New behavior is added **only** through opt-in `CompareSchema` fields that default to
   the no-op original (verified: `key_field=0`, `key_normalizer=None`, `ditto_nonasserting=False`,
   `context_fields=()`, `header_comment=None`, `legend_writer=None`, `extra_sheet_writer=None`).
   **Named canaries that must not regress:** Highway Log Route-1 vs TSN = **299 both / 18 TSMIS-only
   / 69 TSN-only / 221 diff rows / 969 diff cells**; Ramp Detail vs TSN 15,211 both / 902 diff;
   Ramp Summary 31 cats / 27 diff; Intersection Summary 72 union / 52 diff; Intersection Detail
   16,211 both / 5,632 diff; Highway Sequence 57,070 both / 5,538 diff. Enforced by the blocking CI
   loop + the manual `%TEMP%\tsmis_regress` COM-recalc harness.
2. **Output-workbook compatibility.** `matrix.read_counts` reads the VALUES-flavor Comparison
   sheet by **fixed column position** (`status_col=6/5`, `first_field=8/7`). Reordering Comparison
   columns silently breaks every cached matrix count. The values flavor must keep storing literal
   `" ≠ "` (no live formulas) — `read_counts` does no F9.
3. **Console-free core.** `common.py`/`exporter.py`/consolidators/comparators report via the
   `Events` sink and raise — never `print`/`input`/`sys.exit`; core strings stay UI-neutral. Any
   decomposition must preserve this (the shim must not pull a driver).
4. **Playwright thread-affinity.** Only the owning thread touches a page; each parallel worker owns
   its own `sync_playwright()`. Pause holds *between* routes, never inside a wait.
5. **Updater: Windows cert-store TLS** (`ssl.create_default_context()`) — **never** `requests`/
   `certifi` (a bundled CA list breaks corporate TLS inspection on the exact managed PCs that need
   it). Plus the two-phase swap, the staged-items allowlist (`_BUNDLE_ITEMS`), rename-only rollback,
   PID-recycle `OpenProcess(SYNCHRONIZE)`, and `safe_release_url`.
6. **Swap-mode-first ordering** (`gui_main.main`): the `SWAP_FLAG` branch runs before logging/paths/
   CLR/`import gui_api`. **No automated assertion guards this** — adding one is a v0.18.0 task.
7. **Work-PC capability model.** No PowerShell (blocked for standard users), no cmd guarantee, no
   admin, no temp scripts, no scheduled tasks. The only proven capability is "unsigned exe from a
   user-writable folder". The updater applies itself by pure renames; the MOTW self-unblock is
   scoped to the app's own .NET trees; the `paths.py` writability fallback gates `update_support()`.
8. **`.bat` console compatibility** — a separate driver surface over the same `export_*.py` /
   `run_consolidate_cli` entry points; must keep working with global pip.
9. **Data-exposure `.gitignore`.** Never commit `scripts/tsmis_auth.json`, `output/`, the
   `tsn_library/`, or `code-review/`. The "**NEVER add `!output/tsn_*`**" rule is deliberate
   (TSN/Caltrans-internal). Real test data + the live site source are LOCAL ONLY.
10. **The sr-only hidden-input CSS rule (Lesson 10).** Every label class wrapping a hidden
    `<input>` must be in the `position:relative` containing-block list or the page scrolls into a
    blank area. No pure-Python check can catch it — verify in the `#mock` (`scrollHeight ===
    innerHeight` on a matrix tab) after any `app.css`/`app.js` layout change.
11. **The planned full GUI replacement.** `architecture.md` states the current GUI is a **stopgap**
    — "a full GUI overhaul is planned (the user designs it elsewhere and will hand it over)… DON'T
    invest in redesigning the current layout." **This directly constrains how much app.js work is
    worthwhile** (§10, §12).

**Dangerous refactors specifically:** decomposing `compare_core` structurally; changing any
Comparison-sheet column order; "simplifying" the `set_site` global to something that changes its
read timing without a lock/pin; chunking the field-hardened `navigate_with_auth`/`preflight` waits
without live work-PC verification; switching updater TLS; touching the swap order; DPAPI-wrapping
the auth file without solving portability.

---

## 8. Candidate target architecture

Same runtime shape (one console-free core, two front-ends, one registry) — but with **single
sources of truth** and **modules under the size guideline**:

- **Registry by stable key.** Every `EXPORT/CONSOLIDATE/COMPARE` row gets an immutable `key`;
  `_pick_report` and all bridge methods take keys; the manifest persists keys (int back-compat
  shim on load); `app.js` passes `dataset.key`. Index becomes display-order only. (Mirrors the
  matrix subsystem, which already works this way.)
- **A declared Python↔JS contract.** The `task` and `env_access.status` enums (and event kinds)
  are defined **once on the Python side** and surfaced in `get_initial_state`, so JS validates
  against a Python-owned set instead of hardcoded literals; both dispatch defaults log on unknown.
  Stretch: generate the mock's registry-shaped fixtures from the same data the Python side consumes,
  so the 1330-line mock can't drift.
- **`common.py` → cohesive modules** (`errors`, `site`, `timeouts`, `routes`, `auth_state`,
  `browser_channels`, `edge_device`, `report_nav`) behind a thin `common` re-export shim.
- **`gui_api.py` → `GuiApi` core + mixins** (`MatrixApiMixin`, `ExportApiMixin`,
  `CompareConsolidateApiMixin`, `SettingsApiMixin`, `UpdaterApiMixin`) + `gui_state.py` +
  `gui_win32.py`; `_handle` becomes a dict dispatch table; a `_begin_task(...)` helper.
- **`app.js` → ES modules** (`mock.js` out first, then `bridge.js`, `matrix.js`, `modals.js`,
  `settings.js`, `dom.js`, `state.js`); `renderMatrix`/`renderDayMatrix` merged into one
  parametrized renderer. (Gated on §11 GUI-replacement decision.)
- **Report-family substrate:** `tsn_library.build_normalized` factory; `run_files_compare` driver
  + `compare_tsn_normalize` helpers; `compare_core.make_notes_sheet` opt-in helper; a shared
  workbook-header-style constant. `compare_core` itself untouched.
- **`matrix_cache.py` + snapshot substrate** shared by the two matrix orchestrators.
- **Hardening baked in:** `settings._atomic_write` everywhere + validation-at-boundary +
  `_SCHEMA_VERSION`; `paths._safe_join` + explicit browser-path init; a lock (or thread-local pin
  snapshot) around `set_site`/channel caches; bounded worker queue; `should_cancel` into recovery;
  DPAPI-or-ACL auth-at-rest (portability-aware); updater checksum-enforce + a signature-verify slot;
  `APP_MODULES` completeness check + `gui_main` swap-ordering assertion + (optionally) a frozen
  self-test on PR; hash-pinned build deps; the documented swallows logged.

---

## 9. Candidate implementation phases (incremental, each independently verifiable)

Ordering principle: **build the safety net first, then do the cheapest/safest extractions, then
the high-ROI correctness fix, then the riskier splits.** Every phase ends green on `compileall` +
the 44 golden checks; compare-touching phases additionally re-prove the Route-1=969 canary + COM
harness; GUI phases verify in the `#mock`; packaging phases gate on `full_smoke`.

- **Phase 0 — Safety net + free wins (no behavior change).** Add the missing characterization
  guards: a static/AST check that the `SWAP_FLAG` branch precedes any paths-resolving import in
  `gui_main`; an `APP_MODULES`-completeness check; broaden `check_updater` where cheap. Fix the
  doc-drift (gui_worker Tkinter docstring, gui-bridge.md §8, stale line numbers, build-release CI
  list). Add the two dispatch **default branches** (`_handle` else-log + `app.js` default-warn).
  *Lowest risk, immediately mergeable.*
- **Phase 1 — Leaf extractions + DRY hygiene.** Pull `errors.py`/`timeouts.py`/`routes.py` from
  `common.py` (pure, no Playwright, trivially testable) behind the shim; route the 4 settings
  writers through `_atomic_write`; move the `paths.py` env mutation to explicit init; add
  `_safe_join`. *Low risk, high readability ROI.*
- **Phase 2 — Registry stable keys (the data-correctness fix).** Key the three registries +
  `_pick_report` + bridge methods + manifest (with int back-compat shim) + `app.js dataset.key`.
  Re-lock with `check_gui_bridge`/`check_matrix_bridge`/`check_b3_batch`. *Highest correctness ROI.*
- **Phase 3 — Report-family DRY.** `tsn_library.build_normalized` factory (collapses ~280 lines,
  no lock exposure) → `run_files_compare` + `compare_tsn_normalize` → `make_notes_sheet` + shared
  header style. Re-run the 6 vs-TSN canaries + COM harness after each.
- **Phase 4 — GUI backend split.** Extract `gui_win32.py` (zero coupling) and `gui_state.py`, then
  the mixins (Matrix first, ~1050 lines); `_handle` → dispatch table; `_begin_task`; enum SSOT in
  `get_initial_state`; log the contract-violating swallows.
- **Phase 5 — Frontend split (gated on §11).** Extract `mock.js` first (removes 27%), then
  `bridge.js`/`matrix.js`/`modals.js`/`settings.js`/`dom.js`/`state.js`; merge the two matrix
  renderers. Verify the sr-only invariant (Lesson 10) in the `#mock`.
- **Phase 6 — Engine auth/browser/edge extraction + concurrency hardening.** The riskier
  `common.py` clusters (work-PC-tied) behind the shim; lock/pin `set_site` + channel caches; bound
  the worker queue; thread `should_cancel` into `_recover`/retry. *Carries work-PC-only residual
  verification — stage carefully.*
- **Phase 7 — Security / packaging / updater hardening.** Portability-aware auth-at-rest; updater
  checksum-enforce in `release.yml` + a signature-verify slot (live when the SignPath cert lands);
  hash-pin build deps; `prune` content-guard in CI; frozen self-test on PR (label/nightly);
  `matrix_cache.py` extraction.

Phases 0–3 are safely shippable as one or more v0.18.0 increments without touching any
work-PC-only path. Phases 5–6 carry the most residual risk and the GUI-replacement question.

---

## 10. Open questions & lower-confidence findings

1. **Should `app.js` be split at all?** `architecture.md` says the current GUI is a stopgap to be
   replaced by a user-designed overhaul, and "DON'T invest in redesigning the current layout."
   Module-splitting is *refactor*, not redesign — but if the GUI is replaced wholesale, Phase 5 is
   wasted effort. **Needs the user's call** before committing to Phase 5. (Extracting `mock.js`
   alone may still be worth it as a drift-reduction, independent of redesign.)
2. **DPAPI vs auth-file portability.** The engine deep-dive recommends DPAPI for the plaintext auth
   token, but DPAPI is user+machine-scoped and the auth file is **designed to be portable**
   (`storage_state_is_portable`). DPAPI would break that. Lower-confidence: maybe NTFS ACL
   tightening (0600-equivalent) is the safer hardening; needs a decision on whether portability is
   still wanted.
3. **`node.exe` ~80 MB removal** — is a Playwright-free CDP launch of the system browser feasible?
   Likely not without losing Playwright, but the size prize justifies a small spike. (Unverifiable
   without building.)
4. **`set_site` race reachability** — the engine deep-dive says `ActiveEnvCheckWorker` runs outside
   the single-task gate and could interleave a `get_site()` read with a batch's `set_site`. I have
   **not** traced the exact interleaving to a concrete wrong-folder outcome; it may be unreachable
   in practice. Lower-confidence HIGH — Codex should adjudicate (§12).
5. **Keep the `check_*.py` model or add pytest/coverage?** The no-framework model is deliberate and
   works (44 blocking checks). Bolting on pytest is probably out of scope; closing the *named* gaps
   (§5) is the better investment. Confirm the user agrees.
6. **Bundle/startup numbers** (148 MB, ~80 MB driver, 42 MB locale prune) are doc-sourced and
   **unverifiable from the repo** without a build — treat as directional.
7. **`paths.output_day_dir(day=None)` dead?** Seeds flag it; not confirmed live-dead. Grep before
   removal.

---

## 11. Baseline commands & results (reproducibility)

```
git rev-parse --abbrev-ref HEAD            → main
git rev-parse HEAD                         → d2ee35333f3ebd3a070c1adfec893c10d2ffbe58
git describe --tags --abbrev=0             → v0.17.1
git status --porcelain                     → (empty; clean)
git log --oneline 0a4c071..HEAD | wc -l    → 91   (audit commit is 91 behind HEAD)

# compile (green)
build/.venv/Scripts/python.exe -m compileall -q scripts build version.py   → OK

# regression (green) — the 44-check checks.yml blocking set, venv, PYTHONIOENCODING=utf-8
for c in <44 checks>: python build/$c.py   → PASS=44 FAIL=0

# authoritative sizes (CRLF; wc -l)
app.js 5003 · gui_api.py 3525 · compare_core.py 1953 · gui_worker.py 1862 · common.py 1653
app.css 1511 · index.html 1021 · matrix.py 877        (scripts/ total ~22,200)

# structural probes
gui_api.py: 1 class (GuiApi), 97 js_api methods, 35 `kind ==` branches, NO else
common.py: 14-module import blast radius; settings.py & paths.py are leaves (no `import common`)
except Exception/bare-except density: common 47 · gui_worker 39 · gui_api 19 (most ARE logged)
TODO/FIXME/HACK/XXX in scripts/: 0
CI ↔ disk: 44 check_*.py on disk == 44 referenced in checks.yml (no orphans, no phantoms)
```

**Coordination note:** all baseline work was read-only / temp-scoped. No builds replaced `dist/`,
no deps installed, no live TSMIS access, no credential/profile inspection — safe alongside the
parallel Codex investigation.

---

## 12. Areas Codex should independently challenge

1. **Is the index→key registry migration a *real* data-correctness bug (manifest replay across a
   v0.17→v0.18 reorder) or only theoretical?** I rate it HIGH; verify the exact `gui_worker._specs`
   replay path and whether a real reorder is even planned.
2. **`set_site` global-mutation race (§5/§10.4):** trace whether `ActiveEnvCheckWorker` (outside the
   gate) can actually interleave a `get_site()` read with a batch's `set_site` to produce a
   wrong-env output folder, or whether something serializes it. I did not nail the concrete failure.
3. **Should `compare_core` (1953 lines) be decomposed at all?** I argue **no** (regression-lock risk
   ≫ reward). Challenge that — is there a *safe* extraction (e.g. the sheet-writers) that's worth it?
4. **The silent-swallow list (§5):** which of the ~5 auth-path swallows are genuinely dangerous vs.
   intentionally-quiet fail-closed paths? I flagged `is_logged_in:611` as HIGH — is that right, given
   the callers re-check?
5. **app.js scope (§10.1):** given the planned GUI replacement, is *any* frontend refactor justified,
   or only the `mock.js` extraction? This is the biggest scoping fork.
6. **Severity calibration generally** — especially whether the god-object splits (high effort,
   work-PC-tied for `common.py`) are worth it in a single release, or should be staged across two.
7. **Anything I missed entirely** — I weighted structure/maintainability heavily (the audit's blind
   spot); Codex may catch reliability/security/perf items my fan-out under-covered (e.g. the parallel
   engine's reconciliation edges, the PDF parsers' geometry-carryforward, ramp-summary hard-coded
   coordinates).
8. **The "fixed" Phase-3 items** — I trusted the roadmap's checkmarks for ~10 fixes plus spot-checks;
   Codex should independently confirm a sample are actually in the code at HEAD (e.g. the staging
   rename `_retry`, the `_reconcile_unaccounted` lock-tolerance, the batch stage-and-swap).

---

*End of Claude investigation. Awaiting the Codex investigation for finding-by-finding
reconciliation before the plan is drafted.*
