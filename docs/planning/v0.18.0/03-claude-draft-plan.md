# Claude Draft Plan v1 — Awaiting Codex Adversarial Review

**Release:** v0.18.0 — structural optimization + engineering overhaul.
**Baseline:** HEAD `d2ee353`, tag `v0.17.1`, clean tree; compile green; 44/44 CI golden checks pass.
**Inputs reconciled:** `01-claude-investigation.md` (structure-weighted) + `02-codex-investigation.md`
(correctness-contract-weighted). Every significant Codex finding was re-verified against code before
acceptance (§3, §4).

**Central thesis (revised after reconciliation):** v0.18.0 is **not primarily file-splitting**. The
urgent problem is that **completion, freshness, ownership, and promotion are implicit contracts**
spread across workers, matrices, manifests, caches, and the UI — and at least one (F4) has already
drifted into a user-visible defect. **Make those contracts explicit and regression-test them first;
then decompose the large modules, which becomes far safer and more valuable.**

---

## 1. Verified current-state architecture

One **console-free core** drives two front-ends; one **registry** feeds both.

```
gui_main.main()  ──(SWAP_FLAG branch FIRST)──► setup_logging ► _unblock_dotnet_assemblies (MOTW)
   │                                            ► updater.cleanup_leftovers ► import gui_api ► run()
   ▼
gui_api.GuiApi  (single class, 3525 lines, 97 js_api methods, 2 queue pumps, the single-task gate)
   │  emits (kind,payload) ──► app.js dispatch (10 event types) ──► WebView (Edge WebView2)
   │  ◄── 97 api.* calls (report selection BY INDEX) ◄── app.js (5003 lines incl. 1330-line #mock)
   ▼
gui_worker.py  (15 Thread workers: Export/Batch/Matrix*/Login/EnvScan/Updater/Chromium/Reset …)
   │  Events sink (events.py): on_log/on_route/should_skip/is_cancelled/is_paused/on_status/screenshot
   ▼
exporter.py / exporter_parallel.py ──► common.py (auth state machine, site pin, timeouts, routes,
   │                                              browser channels, edge-device SSO — 8 jobs, 1653 ln)
   ├─ consolidate_*.py ──► consolidate_xlsx_base.py / TSN+PDF parsers
   └─ compare_*.py / matrix.py / day_matrix.py ──► compare_core.py (REGRESSION-LOCKED, 1953 ln)
        └─ output/<YYYY-MM-DD src-env>/<report>/ ; Everything store <dest>/<src-env>/<report>/
```

**Verified dependency facts:** no Python import cycle (Codex static analysis; matches my read).
`settings.py` and `paths.py` are leaves (don't import `common`). `common` has a 14-module blast
radius. Consolidators' `from cli import …` are `__main__`-guarded (console-free contract holds). **But
`import reports` eagerly loads openpyxl + pdfplumber + PIL + playwright** (verified via `sys.modules`
probe) — so GUI cold-start pays for all document/browser imports before the first screen.

**Authoritative sizes (`wc -l`, CRLF):** `app.js` 5003 · `gui_api.py` 3525 · `compare_core.py` 1953 ·
`gui_worker.py` 1862 · `common.py` 1653 · `app.css` 1511 · `index.html` 1021 · `matrix.py` 877. The
project's own guideline is <800/file; five modules exceed it, two by 4–6×.

---

## 2. Evidence-backed problem statement

Two problem classes, in priority order:

**A. Implicit completion/freshness/promotion contracts (correctness — fix first).** Verified defects:
- **F1** — `ExportWorker._run_specs` (`gui_worker.py:423–428`) promotes the staged store into live on
  `not cancel` + no exception, **without consulting `RunResult.failed`** (appended `:429`, unread). The
  stage-and-swap docstring (`:183–188`) claims it prevents "a partial set could read as fresh," but it
  only guards crash/cancel — **not the normal-return-with-failed-routes case**. A refresh with failed
  routes promotes a store missing that fresh data and discards the prior copy. BatchWorker reuses
  `_run_specs`; `_on_matrix_export_done` chains compare on "not cancelled," not on success.
- **F2** — `_swap_store_dir` (`:194–197`) is `rmtree(live)` then `rename(staged→live)`; if rmtree
  succeeds but rename raises, the handler (`:216–219`) drops staging → **neither copy survives**. The
  merge fallback can leave stale files.
- **F3** — `matrix._consolidate_store_folder:692` ignores the consolidator's `ConsolidateResult`;
  `consolidate_and_compare_tsn:795` checks only `exists()`/`size>0`. An errored rebuild that leaves a
  **stale** prior workbook is compared and cached as current.
- **F4** *(user-visible)* — `matrix.build_comparison:874` + `day_matrix.py:355` hardcode
  `read_counts(has_route=True)` for ALL tsn/self modes, but `compare_ramp_summary_tsn` /
  `compare_intersection_summary_tsn` emit **`has_route=False`** workbooks. `read_counts` then reads the
  wrong columns → **diff_cells reads 0 while the workbook shows differences.** The in-code comment
  (`:870–873`) asserting "has_route=True is correct for ALL tsn/self modes" is stale (true only before
  v0.17.0 added the aggregate comparators).
- **F5** — `matrix._consolidated_stale:751–766` uses **newest-mtime only**; a deleted route (with
  remaining files older than the consolidated) is not detected → stale data persists. `day_matrix`
  freshness `all(existing are fresh)` ignores a missing consolidation.
- **F9** — generated XLSX/PDF are written **directly to their final path** (no temp+replace), so a
  crash/disk-full can truncate the prior valid artifact.

**B. Structural debt + drift (maintainability — fix after the contracts).**
- God-objects: `app.js` 5003 (117 globals; 1330-line `#mock` = 27% second source of truth),
  `gui_api.py` 3525 (single class, 97 methods), `common.py` 1653 (8 jobs).
- **Index-based report selection** across three differently-ordered registries → manifest replay can
  resume the wrong reports after a reorder (a real data-correctness vector).
- Multi-source-of-truth drift: the `#mock` (stale `0.14.2`/`v0.8.0` strings), `APP_MODULES` (51 entries;
  `matrix`/`day_matrix`/`report_library` absent), 9-value `task` + 11-value `env_access.status`
  magic-string enums, the console `.bat` menus (missing the Intersection consolidators), two ditto
  definitions, duplicated calibration constants.
- Report-family duplication: `tsn_load_*` ~280 lines collapsible; `compare_*_tsn` ~300; 7× workbook
  header style; `_norm_route` 5×; settings atomic-write 4× despite a helper.
- Two silent-drop dispatch defaults (`gui_api._handle` 35 branches no `else`; `app.js` `default:break`).
- Eager imports (F11) → cold-start cost; `paths.py` import-time `os.environ` mutation.
- Packaging: frozen build never exercised on PRs; final docs copied **after** the DLP scan (F10).
- Updater: no signature (blocked on cert); size-only fallback; non-rotated swap log.

---

## 3. Reconciliation of both investigations

**Where we converge (high confidence):** mock-as-second-backend (my §2.2 ↔ F13); god-object/responsibility
clusters (my §2.1 ↔ F14); index selection + unstable manifest (my §4.B ↔ F7); implicit worker
protocol + no `_handle` default (my §2.5/4.E ↔ F8); report-metadata source-of-truth sprawl (my
§2.3/4.B ↔ F6); eager-import cold-start (my §5 ↔ F11); updater trust/packaging gaps (my build-agent
C-1/P-1 ↔ F6/F10); settings duplication + no migration (my §2.3 ↔ F9/persistence).

**What Codex added that I under-weighted (now verified, accepted, and elevated):** the **F1–F5/F9
correctness cluster**. My investigation noted the PDF silent-drop and the index coupling but **missed
that partial success can silently replace last-good data (F1), that promotion isn't transactional
(F2), that consolidator status is ignored (F3), that aggregate vs-TSN counts read the wrong layout
(F4), and that freshness misses deletions (F5).** These are *defects*, not structural risk, and they
reorder the plan.

**What I added that Codex treated abstractly (accepted, incorporated):** exact split seams + line
counts; the **protected canary values** (Route-1 = 969 both/one-sided/diff …); the magic-string enum
inventory; the report-family DRY line quantification; the specific silent-swallow cluster
(`is_logged_in:611`); the **DPAPI-vs-portability** conflict; the **Lesson-10 sr-only CSS trap**;
`should_cancel`-not-in-`_recover`; the full HEAD-verified audit reconciliation.

**Substantive disagreement — framing/sequencing (resolved in Codex's favor):** my draft framed
v0.18.0 primarily as structural decomposition; Codex argues correctness contracts must come first.
**The F4 defect settles it** — a feature drifted precisely because the contract was implicit, so the
plan now sequences correctness + characterization **before** decomposition (D1). Decomposition remains
the bulk of the work and proceeds once the contracts are locked.

**Rejected / not revived (both agree):** the audit's refutation-rejected items — `paths` import-time
env-mutation (intended), same-second mtime cache (below bar), free-port TOCTOU (graceful), the
"signed-in selectors single point of failure" (fails loud). `settings` duplicate-atomic-write is a DRY
cleanup, **not** a data-loss risk. No framework rewrite (asyncio/plugin) — both warn against it.

**Generic/unsupported recommendations rejected:** none of substance — Codex's recommendations are
evidence-backed. Its lower-confidence items (§15 of 02) are explicitly flagged as needing runtime
evidence and are treated as **measurements/spikes**, not committed changes (e.g. cold-start magnitude,
bundle savings, snapshot latency, junction behavior).

**Important issues missed by BOTH (newly raised here):**
1. **O4 — a possible second instance of F4 on the cross-env path.** Codex scoped F4 to the hardcoded-
   `True` tsn path; neither verified whether the **ENV-mode** aggregate reports (Ramp Summary /
   Intersection Summary cross-env) also mis-read counts via the `_row_defs` heuristic `has_route =
   getattr(adapter,'sheet_name',None) is not None` (`matrix.py:63`), which feeds
   `build_cell_comparison → read_counts(has_route)` (`:631`). **Must verify in P1.**
2. **Frontend refactor a11y trap (Lesson 10).** Any `app.css`/`app.js` layout change risks the sr-only
   positioned-parent bug (page scrolls into blank space). No pure-Python check catches it; it must be a
   `#mock` `scrollHeight===innerHeight` verification gate on P9. (I have it; Codex doesn't.)
3. **`gui-bridge.md §8` is actively *wrong*** (describes a superseded LoginWorker order), not merely
   stale — a doc that will mislead the implementer. Fold into P0/P11.

---

## 4. Finding-disposition table

Severity: **D**efect · **R**eliability · **S**tructural · **Sec**urity · **P**erf · **Pkg**.
Disposition: Accepted / Accepted-with-mod / Rejected / Deferred / Unresolved.

| ID | Finding (source) | Sev | Verified? | Disposition | Phase |
|---|---|---|---|---|---|
| F1 | Partial export promoted as complete (Codex) | D | **Yes** — `gui_worker.py:423–429` | Accepted | P1 |
| F2 | Store promotion not transactional (Codex) | R | **Yes** — `:194–219` | Accepted | P2 |
| F3 | Matrix ignores `ConsolidateResult`; compares stale (Codex) | D | **Yes** — `matrix.py:692, 795` | Accepted | P1 |
| F4 | Aggregate vs-TSN counts read wrong layout (Codex) | D | **Yes** — `matrix.py:874`, `day_matrix.py:355` vs `has_route=False` adapters | Accepted (elevated) | P1 |
| F5 | Freshness is newest-mtime, misses deletions (Codex) | R | **Yes** — `matrix.py:751–766` | Accepted | P2 |
| F6 | Report metadata: many sources of truth; `APP_MODULES` omits `matrix`/`day_matrix`/`report_library` (Codex + Claude) | S/Drift | **Yes** — `app.spec:67–86` | Accepted | P3, P4 |
| F7 | Batch manifest persists unstable indices (Codex + Claude §4.B) | R/compat | **Yes** — `batch_manifest.py`, `gui_worker.py:491` | Accepted | P3 |
| F8 | GUI state/worker protocol implicit; `_handle` no default (Codex + Claude §2.5) | S | **Yes** — `gui_api.py:462` (35 branches, no else) | Accepted | P0 (default), P7 |
| F9 | Workbooks written direct-to-final (Codex) | R | **Yes** — consolidators/`compare_core` save in place | Accepted | P2 |
| F10 | Release: final docs bypass DLP scan; exact artifact not self-tested (Codex + Claude C-1) | Pkg | **Yes** — `build.ps1:95,106,111–112` | Accepted | P10 |
| F11 | GUI startup eagerly imports heavy libs (Codex + Claude §5) | P/S | **Yes** — `sys.modules` probe | Accepted | P10 |
| F12 | Matrix snapshots rescan trees; `read_counts` re-reads workbook (Codex) | P | Plausible (not timed) | Accepted-with-mod (measure first) | P10 |
| F13 | Mock is a 2nd drifting backend (Codex + Claude §2.2) | Drift | **Yes** | Accepted | P9 |
| F14 | `common`/`gui_api`/`gui_worker`/`matrix` clusters (Codex + Claude §2.1) | S | **Yes** | Accepted | P7, P8 |
| C-claude | Index selection across 3 registries; magic-string enums; report-family DRY; silent swallows; `should_cancel` not in `_recover`; `set_site` unlocked; settings atomic-write 4×; Lesson-10 trap | S/R | **Yes** (see §01) | Accepted | P1/P3/P5/P6/P7/P8 |
| O4 | Possible 2nd F4 on cross-env path via `_row_defs` heuristic (Claude, both-missed) | D? | **Unresolved** — verify | Unresolved → P1 | P1 |
| AUDIT-P1-updtrust | Updater no signature (audit, open) | Sec | Yes | Deferred (blocked on SignPath cert) | P10 (slot) |
| AUDIT-P2-authrest | Auth plaintext at rest (audit, open) | Sec | Yes | Accepted (ACL; DPAPI deferred O2) | P6 |
| AUDIT-P2-cdp | Edge CDP unauth loopback (audit, open) | Sec | Yes | Accepted-with-mod (open-on-demand) | P8 |
| AUDIT-P2-substr | `select_report` substring match (audit, open) | D | **Yes** — `common.py:732` | Accepted | P8 |
| AUDIT-P2-rampsum | Ramp Summary dup `-O OUTSIDE CITY` / source-misattrib (audit, open) | D | Yes (per audit) | Deferred (needs work-PC fixture) | P11 (log) / future |
| AUDIT-P3-* | ~20 hygiene (stale Tkinter docstring, `wait_for_timeout(1000)`, log rotation, combined-sheet coords, greedy 8+ cliff, side-label cap, …) | S | Mostly yes | Accepted where cheap; rest Deferred | P0/P6/P8/P11 |
| Rejected | `paths` env-mutation (intended); same-second mtime; free-port TOCTOU; settings-dup-write as *risk* | — | — | Rejected as defects (D7) | — |

---

## 5. Proposed target architecture

Same runtime shape (one console-free core, two front-ends, one registry) — but with **explicit
contracts** and **modules under the size guideline**:

1. **A structured terminal-outcome model** shared by export, consolidate, compare, batch, and matrix:
   `complete | partial | no_data | cancelled | failed_before_output | failed_preserving_previous`.
   Promotion, batch-completion, matrix-"ok", and downstream chaining all key on it (never on
   "no exception"). This is the keystone — it makes F1/F3 fixable and prevents recurrence.
2. **A transactional artifact lifecycle** — one proven stage→validate→promote→keep-last-good→cleanup
   pattern for both store directories and generated workbooks; never leaves zero copies; freshness
   keyed on an **input-set fingerprint**, not newest-mtime.
3. **Stable report identity** — every registry row has an immutable `key`; selection, manifests, and
   the JS bridge use keys; index is display-order only.
4. **A canonical report descriptor** — one declarative table per report from which the EXPORT/
   CONSOLIDATE/COMPARE views, `_CONSOLIDATOR_BY_SUBDIR`, `matrix_rows`, `tsn_library._REPORTS`,
   `APP_MODULES`, and the mock/test fixtures are derived or asserted.
5. **A declared Python↔JS contract** — the `task`/`env_access.status`/event-kind enums defined once on
   the Python side and surfaced to JS; both dispatch ends log unknowns; the mock consumes shared
   fixtures instead of re-declaring the backend.
6. **Decomposed god-objects** behind stable façades/shims: `common.py` → cohesive modules; `GuiApi`
   core + feature mixins + `gui_win32`; report-family shared substrate; `matrix_cache` shared by the
   two matrix orchestrators. `compare_core` untouched.
7. **Hardened persistence/packaging/updater** — atomic writers everywhere, schema versions + migration,
   ACL/portable auth-at-rest, frozen-artifact CI test, lazy report imports, checksum-enforce +
   signature slot.

---

## 6. Proposed directory / module structure

`scripts/` stays flat (PyInstaller + the `.bat` bare-name imports depend on it); new modules are flat
siblings. New/changed files:

```
scripts/
  outcome.py            NEW  the terminal-outcome enum + helpers (RunResult/ConsolidateResult adapters)
  artifact_store.py     NEW  transactional promote/keep-last-good + atomic workbook write + fingerprint
  report_catalog.py     NEW  the canonical declarative report descriptor (P4); reports.py derives views
  contract.py           NEW  shared task/env_access/event-kind enums (Python SoT for the JS bridge)
  errors.py             NEW  exception taxonomy extracted from common.py
  timeouts.py           NEW  timeout constants + accessors extracted from common.py
  routes.py             NEW  ROUTES + parse_routes extracted from common.py
  site.py               NEW  set_site/get_site/get_url/expected_host (+ a lock or thread-local pin)
  auth_state.py         NEW  navigate_with_auth + sign-in detection (from common.py)
  browser_channels.py   NEW  channel resolve/probe/launch (from common.py)
  edge_device.py        NEW  edge persistent-profile / CDP / device SSO (from common.py)
  report_nav.py         NEW  select_report/preflight/report_error_text/wait_with_skip_option
  common.py             SHIM re-exports the above (preserve the 14-module import surface)
  matrix_cache.py       NEW  tolerant-JSON results cache + snapshot substrate (shared by both matrices)
  gui_win32.py          NEW  window-icon/taskbar ctypes (zero coupling) from gui_api.py
  gui_state.py          NEW  _state_snapshot/_emit/_push_state/queue pumps from gui_api.py
  gui_api_*.py mixins   NEW  MatrixApiMixin / ExportApiMixin / CompareConsolidateApiMixin /
                              SettingsApiMixin / UpdaterApiMixin (GuiApi composes them; one façade)
  tsn_load_*.py         COLLAPSE into tsn_library.build_normalized(...) factory
  compare_tsn_common.py NEW  run_files_compare(...) driver + compare_tsn_normalize helpers
  ui/
    mock.js             NEW  the #mock extracted from app.js (loaded only under #mock)
    contract.js         NEW  generated/shared enum + fixture constants (mirrors contract.py)
    app.js              SLIM  production UI; (deeper split into bridge/matrix/modals/settings/dom — O1)
```

`compare_core.py` and the per-report parsers stay where they are (isolated by adapter).

---

## 7. Dependency direction and ownership

Target layering (downward only); each module gets a single owner-concept:

```
gui_main → gui_api(+mixins)/gui_state/gui_win32 → gui_worker → {exporter, matrix/day_matrix, consolidate_*, compare_*}
                                                              → outcome, artifact_store, report_catalog, contract
exporter/exporter_parallel → report_nav → auth_state → browser_channels → edge_device → site → {errors, timeouts, routes}
matrix/day_matrix → matrix_cache → compare_core (LOCKED) ; consolidate_* → consolidate_xlsx_base
settings, paths  = leaves (no `common`/engine imports)   ; reports.py = thin views over report_catalog
```

Ownership rules (enforced by review + the import-direction check in P0):
- **No upward imports** (core never imports `gui_*`/`webview`); the `common` shim must not pull a driver.
- `report_catalog.py` is the single owner of report metadata; `reports.py`, `matrix`, `tsn_library`,
  `app.spec`, mock, and fake-site fixtures **derive or assert against it** (no parallel literal lists).
- `outcome.py` owns the terminal vocabulary; workers/matrices import it, never re-invent booleans.
- `artifact_store.py` owns promotion + atomic writes + fingerprints; `gui_worker` and `matrix` call it.
- `contract.py` (Python) ↔ `contract.js` (mirror) own the bridge enums; `gui_api` and `app.js` import them.
- `site.py` owns environment selection; engine entries snapshot it once per run (no mid-run re-read).

---

## 8. Exact responsibilities to split / merge / isolate / generalize / remove

| Action | Target | Detail |
|---|---|---|
| **Split** | `common.py` (1653) | → `errors`, `timeouts`, `routes` (leaves, first), then `site`, `report_nav`, `auth_state`, `browser_channels`, `edge_device`; `common` becomes a re-export shim. |
| **Split** | `gui_api.GuiApi` (3525) | → `gui_win32` (ctypes), `gui_state` (snapshot/emit/pumps), and feature mixins (Matrix ~1050 first). One public `GuiApi` façade preserved (JS names/event order unchanged). |
| **Split** | `app.js` (5003) | extract `mock.js` (−27%) + `contract.js`; merge `renderMatrix`/`renderDayMatrix`; deeper split gated on O1. |
| **Merge** | results cache + snapshot scaffolds in `matrix.py`/`day_matrix.py` | → `matrix_cache.py` substrate; keep the two orchestrators distinct (env vs day axis). |
| **Merge** | `tsn_load_*` (4) | → one `tsn_library.build_normalized` factory (~280 lines out). |
| **Merge** | `compare_*_tsn` shells (5) | → `run_files_compare` driver + `compare_tsn_normalize` helpers (~300 lines out); adapters keep only their schema + projector. |
| **Isolate** | `compare_core.py` | leave structurally intact; only add opt-in `make_notes_sheet` plumbed through existing schema fields. |
| **Isolate** | report-specific PDF/XLSX parsers | keep behind adapters; no generic-parser unification. |
| **Generalize** | report metadata | → `report_catalog.py` descriptor; views derived. |
| **Generalize** | terminal status | → `outcome.py` model; promotion/chaining key on it. |
| **Generalize** | promotion + workbook writes | → `artifact_store.py` (transactional, atomic, fingerprinted). |
| **Remove** | stale doc text | gui_worker Tkinter docstring; gui-bridge.md §8 wrong order; login.py "Phase 4"; stale internals line numbers; build-release CI list subset. |
| **Remove (guard, don't delete)** | `_TSN_MATRIX_EXTRA=[]`, `DISABLED_EXPORT_SUBDIRS=set()` | dormant-but-CI-locked; assert "intentionally empty," keep the extension point. |
| **Remove** | the two silent-drop defaults | add `else: log.warning` (`_handle`) and `default:` warn (app.js dispatch). |

---

## 9. Sources of truth and contracts to consolidate

| Contract | Today (competing) | Target single source |
|---|---|---|
| Report identity/capabilities | EXPORT/CONSOLIDATE/COMPARE lists, `_CONSOLIDATOR_BY_SUBDIR`, `matrix_rows`, `tsn_library._REPORTS`, `APP_MODULES`, mock, fake-site, `.bat` | `report_catalog.py` (P4); all others derive/assert |
| Report **selection** | positional index (Python + manifest + JS) | stable `key` (P3) |
| Terminal outcome | `RunResult.failed` + "no exception" booleans, summary strings | `outcome.py` enum (P1) |
| Comparison count **layout** | adapter `has_route` vs hardcoded `read_counts(has_route=True)` (`matrix:874`, `day_matrix:355`) + `_row_defs` heuristic (`:63`) | layout carried from the adapter/workbook to the reader (P1) |
| Consolidation completeness | `ConsolidateResult.status` vs file existence/size | `outcome.py` partial/error honored by matrix (P1) |
| Freshness | newest-mtime | input-set fingerprint (P2) |
| Bridge enums (`task`, `env_access.status`, event kinds) | scattered string literals in Python + JS | `contract.py`/`contract.js` (P7/P9) |
| Mock backend | 1330-line hand-mirror | shared fixtures from `contract.py`/`report_catalog` (P9) |
| Settings schema | DEFAULTS + bespoke getters + GUI validation + JSON | versioned schema + boundary validation (P6) |
| Packaged modules | `APP_MODULES` hand-list | derived/asserted from `report_catalog` + a glob check (P4/P10) |
| Version | `version.py` + `requirements.txt` + mock + docs | `version.py`; assert/ derive the rest (P10) |
| Workbook column layout (read by matrix) | fixed positions in `read_counts` | documented contract + adapter-provided layout (P1) |

---

## 10. Compatibility & persisted-data migration strategy

Persisted artifacts that MUST survive a v0.17→v0.18 upgrade (in place, no user action):

| Artifact | Risk | Strategy |
|---|---|---|
| `batch_job.json` (paused batch, integer report indices) | F7 — reorder changes meaning | P3: persist `key`s; **load-time shim** maps legacy ints through the *current* `EXPORT_REPORTS` order once, logs a warning; bump `schema_version`. Characterized by a v0.17-format fixture. |
| `config.json` (settings, unversioned) | rename/format drift | P6: add `_SCHEMA_VERSION` + a migration map; unknown keys still round-trip; corrupt file still moved aside. Never reset silently. |
| Matrix/day `_results.json` + comparison sidecars | F4 fix changes counts; F5 changes freshness key | P1/P2: invalidate (rebuild) on first run after upgrade via a cache-format version; old caches read as "stale → recompute," never as authoritative wrong counts. |
| `tsmis_auth.json` (plaintext session) | P6 auth-at-rest | ACL-tighten only by default; **DPAPI gated on O2** (would break portability). Keep readable until/unless re-encrypted with a migration. |
| Output run folders + Everything store layout + filenames | users/`.bat`/resume/matrix caches depend on them | **No renames** of subdirs, row keys (the new `key`s are additive identifiers, not the on-disk subdir), or output filenames. |
| `tsn_library/` tree | canonical TSN home | unchanged; legacy fallbacks kept read-only. |

Golden rule: **every phase leaves prior persisted data readable; format changes are versioned and
migrate forward, never reset.**

---

## 11. Characterization tests required before risky restructuring

These must exist and pass **before** the matching change (Codex §6 + my §9). Added as `build/check_*.py`
(keeping the existing model — O5), pure-Python, deterministic:

| # | Characterizes | Gates phase |
|---|---|---|
| CT-1 | `RunResult.failed` ⇒ no store promotion, no batch-complete, no matrix-"ok", no auto-compare | P1 |
| CT-2 | Consolidator `status="error"` with a stale prior workbook ⇒ no compare/cache of the stale file | P1 |
| CT-3 | Aggregate (`has_route=False`) Ramp Summary + Intersection Summary workbooks ⇒ matrix/day count readback is correct (and O4: the cross-env aggregate path too) | P1 |
| CT-4 | Promotion failure at each step (locked file, rmtree partial, rename fail) ⇒ exactly one complete usable generation survives + explicit failure | P2 |
| CT-5 | Locked/stale `.staging` dir ⇒ not resumed/promoted silently | P2 |
| CT-6 | Deleting a route input ⇒ consolidated + comparison marked stale (fingerprint) | P2 |
| CT-7 | Missing one report's day consolidation ⇒ day header reads incomplete/stale | P2 |
| CT-8 | Workbook/PDF write interrupted ⇒ previous valid final artifact intact (atomic write) | P2 |
| CT-9 | v0.17-format `batch_job.json` (int indices) ⇒ resumes correct reports; reordered registry ⇒ no mis-resume | P3 |
| CT-10 | Every emitted worker `kind` accepted, validated, terminal-exactly-once; unknown kind diagnosed | P0/P7 |
| CT-11 | `gui_main.main` swap-mode branch precedes any paths-resolving import (AST/static assertion) | P0 |
| CT-12 | `APP_MODULES` == the flat-module inventory (minus an explicit denylist) | P0/P4 |
| CT-13 | Mock ↔ backend contract parity for reset-preview, settings, report metadata, matrix rows, event payload shapes | P9 |
| CT-14 | `read_counts` layout matrix (has_route True/False × route/flat) returns correct (diff_cells, one_sided) | P1 |

Existing 44 golden checks remain the regression floor throughout.

---

## 12. Testing & CI modernization

- **Keep the `build/check_*.py` model** (O5) — it works (44/44) and needs no framework. Add the CT-*
  contract tests in the same style; wire each into `checks.yml` as it lands.
- **Add a frozen-artifact gate** (F10/C-1): a CI job (label-triggered or nightly, ~90 min) that runs
  `build.ps1 -SelfTest` against the **exact final windowed** exe, **after** docs are copied, and runs
  the prune content-guard. Deterministic per-PR checks stay separate from this and from work-PC/live
  acceptance (§20).
- **Promote the advisory chain selectively:** keep `ruff`/`bandit`/`pip-audit` advisory, but add
  `requirements-build.txt` to `pip-audit`, and make `check_no_misspelling` + the new CT-11/CT-12
  blocking.
- **No coverage-percentage target** is imposed (no pytest); "coverage" = the named contracts (CT-*) are
  characterized. (Explicitly note this departs from the generic 80%-rule, by design.)
- **Branch filter** `checks.yml` to avoid the double push+PR run.

---

## 13. Reliability, security, error-handling & logging changes

- **Reliability:** F1 promotion-gating, F2 transactional swap, F3 status-honoring, F5 fingerprint
  freshness, F9 atomic workbook writes (all P1/P2); `should_cancel` threaded into `_recover`/retry/
  portability (P8); bounded worker queue + `_on_error` under a consistent lock snapshot (P7);
  updater checksum-enforce + non-fatal-but-logged size-only path (P10).
- **Security:** auth-at-rest ACL (DPAPI deferred, O2) (P6); Edge CDP port opened on-demand and closed
  on capture (P8); `select_report` exact-match guard (P8); support-bundle setting **allowlist** so a
  future sensitive key can't auto-leak (P6); updater signature-verify **slot** wired (live when the
  SignPath cert lands) (P10); `_safe_join` path containment (P6). Preserve the positive controls
  (HTTPS+`*.ca.gov` URL validation, formula-injection defenses, fragment scrubbing, failure-dump
  exclusion).
- **Error-handling/logging:** add the two dispatch default branches (P0); log `type(e).__name__`+first
  line at the verified silent swallows (`is_logged_in:611`, capture chains, `save_support_bundle`
  per-file `OSError`, `_chromium_state`, `_safe_close*`) (P7/P8); `report_error_text` is the model.
  Updater swap log rotation (P10). **Do not** mechanically delete `except Exception` — review by
  boundary/consequence (both investigations agree).

---

## 14. Frontend/backend bridge & mock strategy

- **Bridge:** define `task`/`env_access.status`/event-kind enums once in `contract.py`, surface them in
  `get_initial_state`, mirror in `contract.js`; both dispatch ends log unknown kinds (P0 adds the
  defaults, P7/P9 the SSOT). Migrate report **selection** from index to `key` end-to-end (P3).
- **Mock:** extract `makeMockApi` to `mock.js` loaded only under `#mock` (P9, −27% of `app.js`); have it
  consume the shared `contract.js` + report fixtures derived from `report_catalog`, so it can't drift
  (kills the `0.14.2`/`v0.8.0` staleness class). Add CT-13 mock↔backend contract parity tests.
- **Deeper `app.js` split** (bridge/matrix/modals/settings/dom/state) is **gated on O1** (planned GUI
  replacement). If deferred, stop after mock extraction + `renderMatrix`/`renderDayMatrix` merge.
- **Every frontend change** verifies the Lesson-10 sr-only invariant in `#mock`
  (`scrollHeight===innerHeight` on a matrix tab) and the documented browser-HTTP-cache reload dance.

---

## 15. Build, packaging, dependency, startup, runtime & bundle work (P10)

- **Frozen-artifact CI test** of the exact windowed exe, after docs copy + prune (F10/C-1).
- **`APP_MODULES`** derived from `report_catalog` (P4) + a completeness check (CT-12) → fixes the
  `matrix`/`day_matrix`/`report_library` omission; filter UI `datas` by known extension.
- **Startup/perf:** make `reports.py` registry imports lazy/import-on-dispatch so GUI cold-start
  doesn't pull openpyxl/pdfplumber/PIL/playwright (F11) — **measure cold-start before/after** (F12).
  Return counts from `compare_core.run_compare` so the matrix doesn't re-read the workbook (F12) —
  measure on a 50k-row input first.
- **Bundle:** quantify the ~80 MB node-driver removal feasibility (O6 spike) before any prune change;
  do not chase size without the frozen-artifact test.
- **Deps:** hash-pin build requirements (`--require-hashes`); pin `cryptography` explicitly; assert
  `version.py` Playwright pin == `requirements.txt`; add `requirements-build.txt` to `pip-audit`.
- **Updater:** enforce `.sha256` publication in `release.yml`; with-browser signing parity; the
  signature-verify slot. **Never** switch the cert-store TLS.

---

## 16. Documentation restructuring (P11)

- **Fix the drift:** rewrite `gui-bridge.md §8` (correct LoginWorker order); refresh stale internals
  line numbers; correct `build-and-release.md`'s CI list to all-44; remove the gui_worker Tkinter
  docstring and login.py "Phase 4."
- **Record the new contracts:** the `outcome` model, `artifact_store` transactional lifecycle, the
  `read_counts` layout fix, stable report `key`s, `report_catalog` as the metadata SoT, the
  `contract.py/js` bridge enums — in `architecture.md`, `comparison-engine.md`, `gui.md`,
  `engine-and-reliability.md`, `build-and-release.md`.
- **Update protected-contract lists** (CLAUDE.md conventions + `comparison-engine.md`) to note the
  matrix workbook-column contract and the new outcome/promotion invariants.
- **Fold this planning folder's outcomes into canonical `docs/`**, then the planning folder may be
  retired (it is not canonical — see coordination reminders).

---

## 17. Audit & roadmap work included or deferred

**Included** (verified open, offline-fixable): `handle-no-default-branch` (P0); `select-report-substring`
(P8); stale Tkinter docstring + magic `wait_for_timeout(1000)` + side-label cap + combined-sheet
coords + greedy-cliff note + dev-WebView-cache + swap-log rotation (P0/P6/P8/P11 as cheap); auth-at-rest
(P6); edge-CDP-loopback (P8); support-bundle allowlist (P6); updater size/checksum/death-window
hardening (P10); the field-bug rename-retry **field-verify** (P2 area, §20).

**Deferred (with rationale):** updater **signature** (blocked on SignPath cert — slot wired P10);
Ramp-Summary duplicate-`-O`/source-misattribution (needs a work-PC PDF fixture); the
work-PC-only live re-tests of the already-"Done" P1/P2 items (dev PC can't reach TSMIS — §20); the
3×-deferred feature ideas (A3 results tab, D1 adaptive fast mode, F1 district enumeration — out of an
engineering-overhaul release's scope).

**Obsolete / not revived:** the 12 refutation-rejected audit candidates (D7).

---

## 18. Phased implementation task graph

Dependency order (each phase ends green on compile + 44 golden checks; correctness phases add CT-*;
compare-touching phases re-prove the canaries + COM harness; GUI phases verify in `#mock`):

```
P0 ──┬─► P1 ──► P7
     ├─► P2
     ├─► P3 ──► P4 ──┬─► P5
     │               ├─► P9
     │               └─► P10
     ├─► P6
     └─► P8
P1..P10 ──► P11
```

The application remains runnable after every phase. Per-phase specs:

---

### P0 — Safety net + free wins
- **Objective:** add diagnostics/characterization and zero-risk fixes that de-risk everything after.
- **Findings:** F8 (dispatch defaults), CT-10/11/12 scaffolding, doc-drift (§3.3), import-direction guard.
- **Affected:** `gui_api._handle` (add `else` log), `app.js dispatch` (add `default` warn), new
  `build/check_swap_order.py` (CT-11), `build/check_app_modules.py` (CT-12), `build/check_worker_protocol.py`
  (CT-10), a small import-direction check; doc fixes (gui-bridge §8, gui_worker docstring).
- **Intended changes:** additive guards + two one-line defaults + doc text only.
- **Protected contracts:** none touched behaviorally.
- **Prerequisites:** none.
- **Tests/measurements:** new checks must pass; CT-12 will FAIL first → add `matrix`/`day_matrix`/
  `report_library` to `APP_MODULES` → green. Capture cold-start + a matrix-snapshot timing baseline.
- **Migration:** none. **Risks:** trivial. **Rollback:** revert the additive files.
- **Completion:** new checks green in CI; 44/44 still green; baselines recorded.

### P1 — Completion contract: structured outcome model + F1/F3/F4
- **Objective:** partial work can never masquerade as complete; aggregate counts read correctly.
- **Findings:** F1, F3, F4, O4, C-claude(outcome).
- **Affected:** new `outcome.py`; `gui_worker._run_specs` (gate promotion on outcome), `BatchWorker.run`,
  `MatrixBatchExportWorker.run`, `gui_api._on_matrix_export_done`; `matrix._consolidate_store_folder` /
  `consolidate_and_compare_tsn` (honor `ConsolidateResult`); `matrix.build_comparison:869–876` +
  `day_matrix:355` + `read_counts` (layout from adapter/workbook, not hardcoded `True`); verify O4 on
  the env path (`_row_defs:63` → `build_cell_comparison:631`).
- **Intended changes:** introduce the outcome enum; thread it through promotion/chaining; fix the count
  layout; surface "partial — kept last-good" to the UI.
- **Protected contracts:** `compare_core` untouched; **the comparison workbook column layout is now an
  explicit contract** (document it); existing output filenames unchanged; matrix `_results.json`
  format-versioned.
- **Prerequisites:** P0 (CT scaffolding), CT-1/CT-2/CT-3/CT-14 written first (TDD).
- **Tests:** CT-1, CT-2, CT-3, CT-14; re-run all matrix/compare checks; **work-PC live**: a real refresh
  with an induced failed route keeps last-good (§20).
- **Migration:** invalidate/rebuild matrix+day caches on first run (format version).
- **Risks:** medium — touches live export/matrix flow; mitigated by CT-* first + cache-rebuild.
- **Rollback:** the outcome gating and the read_counts layout are isolated commits; revert restores
  prior behavior (but reinstates the defects). **Completion:** CT-1/2/3/14 green; matrix shows correct
  Ramp/Intersection Summary counts in `#mock`; 44/44 green.

### P2 — Transactional artifact lifecycle: F2/F9/F5
- **Objective:** never leave zero copies; never truncate a prior artifact; freshness tracks input identity.
- **Findings:** F2, F5, F9.
- **Affected:** new `artifact_store.py` (transactional promote = stage→rename live→`.old`→staged→live→
  drop `.old`, restore on failure; atomic workbook write = temp+fsync+`os.replace`; input-set
  fingerprint); `gui_worker._swap_store_dir` → delegate to it; consolidator/compare save paths →
  atomic write; `matrix._consolidated_stale` + comparison-freshness → fingerprint; `day_matrix`
  day-level freshness (missing consolidation ⇒ not fresh).
- **Intended changes:** one proven lifecycle pattern; fingerprint sidecars.
- **Protected contracts:** output filenames/locations unchanged; `compare_core` output bytes unchanged
  (only the *write mechanism* changes — verify byte-identical via the canary harness).
- **Prerequisites:** P0; CT-4..CT-8 written first.
- **Tests:** CT-4..CT-8 (fault injection: locked file, rename fail, partial rmtree, write interrupt,
  deleted route); canary byte-identity; **work-PC live**: induced lock/disk-full keeps last-good.
- **Migration:** fingerprint sidecar is new/versioned; absence ⇒ treat as stale (rebuild once).
- **Risks:** medium — filesystem edge cases on Windows/Defender; mitigated by fault-injection CT-*.
- **Rollback:** `artifact_store` is additive; callers revert to the old swap. **Completion:** CT-4..8
  green; canaries byte-identical; 44/44 green.

### P3 — Stable report identity (registry keys + manifest migration)
- **Objective:** selection/resume no longer depends on list position.
- **Findings:** F6 (partial), F7, C-claude(index).
- **Affected:** `reports.py` (add `key` per row), `gui_api._pick_report` + all index call sites,
  `app.js dataset.idx→key`, `batch_manifest.py` (+ schema version + int back-compat shim),
  `gui_worker._specs` (key lookup).
- **Intended changes:** keys as the contract; index = display order; manifest persists keys.
- **Protected contracts:** legacy `batch_job.json` resumes correctly (shim); registry **order** stays
  append-only for any remaining index consumers until P4.
- **Prerequisites:** P0; CT-9 first.
- **Tests:** CT-9; `check_gui_bridge`/`check_b3_batch`/`check_matrix_bridge`; **work-PC**: resume a real
  paused batch across the change.
- **Migration:** int→key load shim (logs once). **Risks:** medium-low (well-characterized).
- **Rollback:** keep reading ints as a fallback; revert restores index dispatch. **Completion:** CT-9
  green; a v0.17 manifest resumes correctly; 44/44 green.

### P4 — Canonical report descriptor
- **Objective:** one declarative report SoT; derive the rest.
- **Findings:** F6.
- **Affected:** new `report_catalog.py`; `reports.py` views derived from it; `tsn_library._REPORTS`,
  `matrix_rows`, `_CONSOLIDATOR_BY_SUBDIR` derived/asserted; `APP_MODULES` + fake-site + mock fixtures
  derived/checked.
- **Intended changes:** descriptor + derivation; assertions where derivation is impractical (`.bat`).
- **Protected contracts:** the derived EXPORT/CONSOLIDATE/COMPARE order + keys must equal today's
  (golden-assert before/after).
- **Prerequisites:** P3 (keys).
- **Tests:** a descriptor-equivalence check (derived views == current literals); `check_report_library`,
  `check_matrix`, `check_intersection_gate`.
- **Migration:** none (pure refactor). **Risks:** low-medium (broad but assertable).
- **Rollback:** keep the literal lists beside the descriptor until the equivalence check is trusted.
- **Completion:** equivalence check green; 44/44 green.

### P5 — Report-family DRY
- **Objective:** collapse the parallel `tsn_load_*` / `compare_*_tsn` skeletons.
- **Findings:** §2.3 (Claude).
- **Affected:** `tsn_library.build_normalized` factory (←`tsn_load_*`), `compare_tsn_common.py`
  (`run_files_compare` + normalize/notes/header helpers), the 5 `compare_*_tsn` reduced to
  schema+projector, `compare_core.make_notes_sheet` (opt-in).
- **Intended changes:** shared substrate; adapters become thin.
- **Protected contracts:** **the `_SCHEMA`/rows reaching `run_compare` are unchanged → canaries
  byte-identical**; `compare_core` untouched.
- **Prerequisites:** P3/P4.
- **Tests:** the 6 vs-TSN golden checks + COM/Route-1=969 harness after each collapse; canary parity.
- **Migration:** none. **Risks:** low (no lock exposure) but verify per-collapse.
- **Rollback:** per-adapter; revert one comparator to its inline form. **Completion:** all vs-TSN
  canaries byte-identical; 44/44 green; ~500 lines removed.

### P6 — Persistence & settings hardening
- **Objective:** atomic, versioned, validated persistence; safer auth-at-rest; safe paths.
- **Findings:** §2.3 (settings dup), AUDIT-P2-authrest, support-bundle allowlist, `_safe_join`,
  paths import-time mutation.
- **Affected:** `settings.py` (route 4 writers through `_atomic_write`; `_SCHEMA_VERSION`+migration;
  boundary validation; `full_snapshot()`); `paths.py` (`_safe_join`; explicit `init_browser_path()`);
  `common.save_auth_state` (ACL); `gui_api.save_support_bundle` (setting allowlist).
- **Intended changes:** as above; DPAPI deferred (O2).
- **Protected contracts:** unknown-key round-trip; corrupt-file move-aside; existing `config.json`
  readable; auth-file **portability** preserved (ACL not DPAPI).
- **Prerequisites:** P0; coordinate with P3 (manifest schema).
- **Tests:** new settings-migration check; `check_report_library`; `check_gui_bridge` (support bundle).
- **Migration:** settings `_SCHEMA_VERSION` forward-migrate. **Risks:** low.
- **Rollback:** additive helpers; revert per-writer. **Completion:** settings checks green; 44/44 green.

### P7 — GUI backend decomposition
- **Objective:** break the 3525-line `GuiApi` god-object; make the bridge contract explicit.
- **Findings:** F8, F14, §2.4/2.5 (Claude), the silent swallows.
- **Affected:** new `gui_win32.py`, `gui_state.py`, the feature mixins; `GuiApi` composes them (one
  façade); `_handle`→dispatch table; `contract.py` enum SSOT in `get_initial_state`; `_begin_task`
  helper; unify `start_compare`/`start_compare_env` + matrix dispatch pairs; log the verified swallows.
- **Intended changes:** mechanical extraction + the dispatch table + enum SSOT.
- **Protected contracts:** **JS API method names + event order unchanged** (app.js untouched this
  phase); single-task-gate semantics unchanged; CT-10 holds.
- **Prerequisites:** P1 (outcome model so chaining keys on it); P0.
- **Tests:** `check_gui_bridge`, `check_matrix_bridge`, `check_day_matrix`, `check_b3_batch`,
  `check_b1_pause`; CT-10; `#mock` smoke.
- **Migration:** none. **Risks:** medium (broad surface) — mitigated by the bridge golden checks + the
  façade staying API-identical; do Matrix mixin first, one mixin per reviewable diff.
- **Rollback:** each mixin extraction is its own commit; revert restores the monolithic method.
- **Completion:** all bridge checks green; `#mock` exercises every tab; 44/44 green.

### P8 — Engine (`common.py`) decomposition + concurrency hardening
- **Objective:** split the 8-job hub; close the verified concurrency/cancel/security gaps.
- **Findings:** F14, §5 (set_site, channel caches, should_cancel, swallows), AUDIT-P2-cdp/substr.
- **Affected:** extract `errors`/`timeouts`/`routes` (leaves) → then `site`/`report_nav`/`auth_state`/
  `browser_channels`/`edge_device`; `common.py` shim; lock-or-pin `set_site` + channel caches; snapshot
  `(src,env)` once per run (no mid-`_recover` re-read); thread `should_cancel` into `_recover`/retry/
  portability; `select_report` exact guard; Edge CDP open-on-demand+close; log the auth-path swallows.
- **Intended changes:** as above, behavior-preserving except the hardening (which is verifiable offline
  except live auth).
- **Protected contracts:** Playwright thread-affinity; the field-hardened `navigate_with_auth`/
  `preflight` wait behavior (don't chunk unverified — only ADD cancel polling); console-free shim.
- **Prerequisites:** P0; O3 trace (set_site reachability).
- **Tests:** `check_export_engine`, `check_parallel_reconcile`, `check_fake_site`; new
  routes/timeouts unit checks; **work-PC live**: cancel-during-recover latency, exact-match select,
  channel resolution.
- **Migration:** none. **Risks:** **highest** (work-PC-tied auth/browser) — stage leaves-first; keep
  live-path changes minimal + behind the shim.
- **Rollback:** the shim lets each module revert independently; concurrency changes are isolated commits.
- **Completion:** engine checks green; work-PC cancel/select verified (§20); 44/44 green.

### P9 — Frontend separation (gated on O1)
- **Objective:** kill the mock-as-2nd-backend drift; optionally modularize `app.js`.
- **Findings:** F13, §2.1/2.2 (Claude).
- **Affected:** new `ui/mock.js` (extract `makeMockApi`), `ui/contract.js` (mirror `contract.py` +
  fixtures from `report_catalog`); merge `renderMatrix`/`renderDayMatrix`; **deeper split
  (bridge/matrix/modals/settings/dom/state) only if O1 says the GUI replacement isn't imminent.**
- **Intended changes:** extraction + shared fixtures; (conditional) module split.
- **Protected contracts:** **Lesson-10 sr-only CSS rule**; the browser-HTTP-cache reload procedure; no
  behavior change to production UI.
- **Prerequisites:** P4 (descriptor → fixtures); O1 decision.
- **Tests:** CT-13 (mock↔backend parity); `#mock` visual + `scrollHeight===innerHeight` on matrix tabs;
  `full_smoke` boots `app.js`.
- **Migration:** none. **Risks:** medium (no automated app.js unit net — mitigated by CT-13 + `#mock`).
- **Rollback:** mock extraction is reversible; the deeper split is opt-in. **Completion:** CT-13 green;
  mock has no stale strings; `#mock` parity verified.

### P10 — Build / packaging / release / startup-perf hardening
- **Objective:** test the exact shipped artifact; cut cold-start; harden deps/updater.
- **Findings:** F6, F10, F11, F12, AUDIT updater items, deps.
- **Affected:** `checks.yml`/`release.yml` (frozen-artifact gate after docs+prune; prune content-guard;
  `.sha256` enforce; with-browser signing parity; signature-verify slot; pip-audit build reqs); `app.spec`
  (`APP_MODULES` from `report_catalog`; UI datas extension filter); `reports.py` (lazy registry imports);
  `compare_core.run_compare` (return counts) + `matrix` (use them); `requirements*` (hash-pin, pin
  cryptography, version-consistency assert); `build.ps1` (copy docs **before** the scan).
- **Intended changes:** as above; **measure cold-start + snapshot + 50k-row compare before optimizing.**
- **Protected contracts:** cert-store TLS; swap order; the `excludes`/prune behavior proven by the
  frozen self-test; never weaken `-SelfTest`.
- **Prerequisites:** P4 (descriptor), P0 baselines; CT-12.
- **Tests:** the new frozen-artifact gate; `check_updater`; `full_smoke`; before/after timings.
- **Migration:** none. **Risks:** medium (CI + frozen-only failure classes) — the new gate is exactly
  what catches them. **Rollback:** CI/spec changes are isolated; lazy-import revert restores eager.
- **Completion:** frozen-artifact gate green on all 3 variants; cold-start improvement measured; deps
  hash-pinned; 44/44 green.

### P11 — Documentation restructuring + audit/roadmap reconciliation
- **Objective:** make canonical `docs/` reflect the v0.18.0 reality; close/defer audit items.
- **Findings:** §3.3 doc-drift; §17.
- **Affected:** `docs/` (architecture/gui/gui-bridge/comparison-engine/engine-and-reliability/
  build-and-release/roadmap), `CLAUDE.md` conventions, `CHANGELOG.md`; fold this planning folder's
  outcomes in.
- **Intended changes:** correct drift; document the new contracts + protected lists; reconcile roadmap.
- **Protected contracts:** docs accuracy (verify each claim against the shipped code).
- **Prerequisites:** P1–P10 substantially done.
- **Tests:** `check_no_misspelling`; manual doc review; link/anchor check.
- **Migration:** none. **Risks:** low. **Rollback:** docs-only. **Completion:** docs match HEAD; roadmap
  open items each dispositioned; planning folder folded in.

---

## 19. Risks & rollback points

| Risk | Phase | Mitigation / rollback |
|---|---|---|
| A correctness fix changes matrix counts users have seen | P1 | Cache format-version → rebuild; the counts were *wrong* before (F4); document the change. Rollback = revert the layout commit. |
| Transactional swap mis-handles a Windows lock | P2 | Fault-injection CT-4/5/8; `artifact_store` additive → revert to old swap. |
| Manifest key migration mis-resumes a real paused batch | P3 | CT-9 + a real work-PC resume test; int fallback retained; revert restores index dispatch. |
| Descriptor derivation diverges from the literal lists | P4 | Equivalence check gates; keep literals beside the descriptor until trusted. |
| A report-family collapse perturbs a canary | P5 | Per-collapse canary + COM harness; revert that one adapter. |
| GuiApi split breaks a bridge contract | P7 | Bridge golden checks + façade API-identity; one mixin per diff; revert per mixin. |
| `common.py` split breaks a live auth/browser path (work-PC-only) | P8 | Leaves-first; shim per-module revert; minimal live-path change; work-PC gate. |
| Frontend change triggers the Lesson-10 scroll bug | P9 | `#mock` `scrollHeight===innerHeight` gate; mock extraction reversible. |
| Frozen-only failure ships | P10 | The new frozen-artifact gate is the mitigation; lazy-import revert. |

**Global rollback property:** every phase is one or more isolated commits behind a shim/façade/additive
module, and the application is runnable + 44/44-green at each phase boundary, so any phase can be
reverted without unwinding a later one (except where a dependency edge is declared in §18).

---

## 20. Work-PC-only verification (distinct acceptance gate)

The dev PC cannot reach the TSMIS intranet; managed-PC controls (Defender/DLP/proxy/managed Edge) exist
on neither the dev PC nor CI. These require **work-PC** acceptance and must NOT be a dependency of
deterministic CI (Codex §13.14):

| Item | Phase | What to verify on the work PC |
|---|---|---|
| Partial-export keeps last-good | P1 | A real refresh with an induced/again failed route does NOT replace last-good; UI says "partial." |
| Aggregate vs-TSN counts | P1 | Matrix Ramp/Intersection Summary cells show real diff counts on live data. |
| Transactional swap under Defender lock / disk pressure | P2 | Induced lock/disk-full preserves a complete generation. |
| Batch resume across the key migration | P3 | A genuinely paused v0.17 batch resumes the correct reports under v0.18. |
| Cancel latency in `_recover`/retry; exact `select_report` | P8 | Stop interrupts a mid-recovery re-auth; no superstring mis-select. |
| Edge CDP open-on-demand | P8 | Sign-in still works with the port opened only during capture. |
| Updater field paths | P10 | Staging rename-retry (the prior field bug), checksum-enforce, swap on a real v0.17→v0.18 update. |
| Frozen final exe (both variants) | P10 | The exact shipped exe launches, exports, compares, updates on the work PC. |
| Carried-over "Done but live-verify owed" audit items | — | The P1/P2 audit fixes already shipped offline still need their first live confirmation. |

---

## 21. Measurable definition of done

- **Correctness:** CT-1..CT-9, CT-14 green in CI; F1–F5/F9 closed; O4 resolved; the matrix shows correct
  aggregate vs-TSN counts. No partial run reports "complete."
- **Structure:** no `scripts/` module > ~800 lines except `compare_core` (locked, documented exception);
  `gui_api` is a façade over mixins; `common.py` is a shim; `app.js` mock extracted (and, if O1 permits,
  modularized); ~500 lines removed from the report family.
- **Single sources of truth:** report metadata flows from `report_catalog`; bridge enums from
  `contract.py`; `APP_MODULES` derived/checked; mock consumes shared fixtures; no stale version strings.
- **Tests/CI:** 44 existing + the new CT-* all green; the frozen-artifact gate green on all 3 variants;
  the import-direction + swap-order + app-modules checks blocking.
- **Reliability/security:** atomic workbook writes; fingerprint freshness; `should_cancel` in recovery;
  the verified silent swallows logged; auth-at-rest ACL; support-bundle allowlist; updater checksum
  enforced + signature slot.
- **Performance:** GUI cold-start measurably improved vs the P0 baseline (lazy imports); the matrix
  no longer double-reads the comparison workbook.
- **Persisted data:** every prior `config.json`/`batch_job.json`/`tsn_library`/output layout still works;
  format changes are versioned and migrate forward.
- **Docs:** canonical `docs/` match HEAD; every still-open audit item is dispositioned; planning folder
  folded in.
- **Work-PC:** the §20 gate is signed off (or explicitly carried as owed, per O7).

## 22. Explicit exclusions

- No new user-facing features (A3 results tab, D1 adaptive fast mode, F1 district enumeration — stay
  parked).
- **No `compare_core` behavior/formula/label/layout changes**; no Comparison-sheet column reorder.
- No async/threading-model rewrite; no plugin framework; no one-class-per-action; no frontend framework.
- No generic-parser unification of the report-specific PDF/XLSX parsers.
- No rename of report subdirs, output filenames, on-disk `tsn_library` layout, or settings keys (keys
  are additive identifiers, not renames).
- No switch of updater TLS off the Windows cert store; no signing-on by default (gated on the cert).
- No DPAPI auth encryption until O2 (portability) is decided.
- No conversion of the whole `check_*.py` suite to a new runner in this release.
- No live-TSMIS / credential / browser-profile / internal-site-source access in development.
- No staging, committing, pushing, tagging, releasing, or AI attribution.

---

*Claude Draft Plan v1 — Awaiting Codex Adversarial Review. Phase statuses tracked in
`00-coordination.md`. This is a working planning artifact, not canonical product documentation.*
