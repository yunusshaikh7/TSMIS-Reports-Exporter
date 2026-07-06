# P8a — Engine leaf extraction — Claude report

## 1. Phase ID and name
**P8a** — Engine leaf extraction (shim, behavior-neutral) `[blocking; depends PA]`

## 2. Baseline commit
`42122ff` (HEAD after P7a committed — "refactor: add GUI task-state owner + exactly-once
lifecycle + enum SSOT (P7a)"). Baseline characterization green: `check_export_engine`,
`check_import_direction`, `check_app_modules`, `check_fake_site`, `check_persistence`,
`check_parallel_reconcile`; tree clean apart from the untracked `docs/planning/`. Dependency
**PA committed** (`65aef98` — the exact-artifact packaging gate, which proves the new flat
modules freeze).

## 3. Changes made
Extract the pure **L0 leaves** out of `common.py` into their own flat modules, behind a
`common.py` **re-export shim**, behavior-neutral (R1-R08, the verified acyclic DAG §E). No lock
(R1-R07). This is the first, lowest-risk step of the engine decomposition; the channels / auth /
edge / session layers (P8b) and the behavior changes (P8c) follow.

1. **`scripts/errors.py`** — the seven engine exception types (`AuthError`, `PreflightError`,
   `SiteUnreachableError`, `ReportUnavailableError`, `BrowserNotFoundError`, `RunCancelled`,
   `ReportError`), verbatim. The `PreflightError` catch hierarchy is preserved exactly.
2. **`scripts/site_target.py`** — the site/env selection state + report-page URL building
   (`TSMIS_HOST`/`TSMIS_DEV_HOST`, `DATA_SOURCES`/`ENVIRONMENTS` + labels, `set_site` /
   `set_thread_site` / `get_site`, `default_site_url` / `dev_site_url` / `get_url` /
   `expected_host`), verbatim. `settings` import stays lazy (custom-URL override).
3. **`scripts/timeouts.py`** — the timeout default constants + `_settings_ms` + the five
   Settings-backed accessors (`report_timeout_ms()` etc.), verbatim. `settings` import stays lazy.
4. **`scripts/routes.py`** — `ROUTES` + `_ROUTES_SET` + `normalize_route` + `parse_routes`, verbatim.
5. **`scripts/common.py`** — becomes the **re-export shim**: imports every extracted name back so
   `from common import X` is unchanged for all 16 consumers and its own remaining helpers reference
   the names as module globals exactly as before. The unused `import threading` is dropped (only
   `site_target` needs it now); the module docstring is updated to describe the shim role. The
   auth-file lifecycle + the page/channel/edge/session helpers **stay** (P8b).
6. **`build/app.spec`** — `APP_MODULES += "errors", "site_target", "timeouts", "routes"` (the F6
   packaging gate; the frozen `--self-test` + `check_app_modules` enforce every flat module is
   declared).
7. **`build/check_engine_leaves.py`** (new) — unit checks for the four leaves + the **shim-parity
   contract** (`common.X is <leaf>.X` for every re-exported name — proving the 14-module import
   surface is byte-identical, a re-export not a copy).
8. **`build/check_export_engine.py`** — `test_require_site_params` pinned the site by monkeypatching
   the now-moved `common._data_source`/`_environment`; updated to the public `common.set_site(...)`
   API (what `require_site_params` reads via `get_site`).
9. **`.github/workflows/checks.yml`** — runs `check_engine_leaves.py` in the engine step.

## 4. Files affected
**New (5):** `scripts/errors.py`, `scripts/site_target.py`, `scripts/timeouts.py`,
`scripts/routes.py`, `build/check_engine_leaves.py`.
**Modified product (1):** `scripts/common.py` (leaves removed → re-export shim + docstring).
**Modified packaging/CI (2):** `build/app.spec` (APP_MODULES +4), `.github/workflows/checks.yml`.
**Modified test (1):** `build/check_export_engine.py` (site pin via the public API).
**Untouched:** every consumer of `common` (`exporter`, `exporter_parallel`, `cli`, `login`,
`matrix`, `gui_api`, `gui_worker`, the `export_*`, `self_test`), `compare_core`, the matrix/updater,
`ui/*`, `version.py`. No persisted-format change.

## 5. Architectural decisions
- **Re-export shim, not a rewrite.** The leaves are MOVED, not duplicated (`common.py` holds zero
  copies — verified). `common.py` re-imports them so callers and its own helpers are unchanged; the
  shim is the documented compatibility seam and the per-module rollback point.
- **Same `"tsmis.auth"` logger across the split.** `site_target` and `timeouts` keep the exact
  logger name `common.py` used (it is the SAME logger instance — `site_target.log is common.log`),
  so every log record (logger name included) is byte-identical. `errors`/`routes` don't log.
- **Leaves stay import-time leaves.** `settings` is imported lazily inside `get_url` / `_settings_ms`
  (function-local), so the new modules add no module-load sibling import — the import-direction graph
  stays acyclic (`common → {errors, site_target, timeouts, routes}`; the leaves import nothing
  sibling at load time).
- **Auth-file lifecycle stays in `common` for P8b** — see §10.

## 6. Compatibility and migration handling
- **14-module import surface preserved.** `from common import X` yields the SAME object the leaf
  defines for every extracted name (`check_engine_leaves::test_shim_parity` asserts 35 `is` identities
  + the shared logger). No consumer changed.
- **No persisted-format / migration / behavior change.** No `config.json` / manifest / cache / auth /
  output-layout touch; the leaf bodies are verbatim. The one test edit swaps a moved-private-global
  monkeypatch for the equivalent public `set_site` call.
- **Rollback:** per-module — re-inline a leaf and drop its re-export. The shim isolates the seam.

## 7. Tests and commands run
- **Baseline @ `42122ff`:** `check_export_engine` / `check_import_direction` / `check_app_modules` /
  `check_fake_site` / `check_persistence` / `check_parallel_reconcile` green.
- **New `check_engine_leaves` GREEN:** routes (normalize/parse: casing/padding/suffix/dedup/order/
  errors), timeouts (default + override + min×60000 / s×1000 unit conversion + settings-failure
  fall-back), site_target (selection, thread-pin precedence, URL build, custom-URL override,
  expected_host), errors (catch hierarchy), and the 37-assertion shim-parity contract.
- **`check_export_engine` GREEN** after the `set_site` edit (RED-checked: the moved-global
  monkeypatch no longer drives `get_site`; the public-API pin does).
- **Behavior-neutral / packaging:** `check_import_direction` (acyclic with the 4 new nodes),
  `check_app_modules` (red→green after the APP_MODULES +4), `check_source_zip_smoke`,
  `check_fake_site`, `check_persistence` (auth-file untouched) all GREEN.
- **Full blocking suite (CI-style, `set -e`, `PYTHONIOENCODING=utf-8`):** all **63**
  `build/check_*.py` + the 2 Node frontend checks + `node --check app.js` + byte-compile
  (`scripts build version.py`) — GREEN. `git diff --check` clean.
- **Import smoke:** all 17 `from common import` consumers (cli/login/exporter/exporter_parallel/
  matrix/self_test/gui_api/gui_worker/run_report/the `export_*`/reports/report_catalog) import
  cleanly; `common`/`errors`/`routes`/`timeouts`/`site_target` import cleanly.

## 8. Results
All green. `common.py` is now a thin re-export shim over four pure leaves (errors / site_target /
timeouts / routes); the import surface is byte-identical (shim parity proven); the import graph is
still acyclic; the F6 packaging gate covers the new modules; the new unit check locks the leaf
behaviors. No behavior, persisted-format, or log-output change.

## 9. Before/after measurements
| Metric | Before (`42122ff`) | After |
|---|---|---|
| `common.py` | 1713 lines (monolith) | 1435 lines (re-export shim + remaining auth-file/page/channel/edge/session) |
| Engine leaf modules | 0 (inlined in `common`) | 4 — `errors` (65), `site_target` (126), `timeouts` (104), `routes` (78) |
| Moved definitions left in `common` | n/a | 0 (verified — re-exported, not duplicated) |
| `APP_MODULES` | 57 | 61 (+`errors`, +`site_target`, +`timeouts`, +`routes`) |
| Offline Python checks | 62 | 63 (+`check_engine_leaves`) |
| Import-direction graph | acyclic | acyclic (+4 leaf nodes, all sinks) |
| `from common import X` surface | baseline | byte-identical (35 `is` identities + shared logger asserted) |

## 10. Deviations from the approved plan
- **`site.py` → `site_target.py` (stdlib-collision rename).** §E names the site leaf `site.py`, but a
  flat `scripts/site.py` is **shadowed by the Python standard-library `site` module**: `site` is
  preloaded into `sys.modules` at interpreter startup, so `from site import get_url` resolves to the
  stdlib module and raises `ImportError` (empirically verified before extracting). Renamed to
  `site_target.py` (same content, non-colliding); documented in the module header + the shim comment.
  This is the only safe option and is not a scope change.
- **Auth-file lifecycle DEFERRED to P8b.** P8a's *Affected* line says "(+ auth-file lifecycle)
  extracted", but (a) §E — the authoritative final module structure — places the auth-file lifecycle
  inside **`auth_nav.py` (L2, P8b)**, with no L0 auth leaf module; and (b) the auth-file functions
  (`save_auth_state` / `_restrict_to_owner` / `require_valid_auth` / `has_valid_auth` / `clear_auth` /
  `_auth_file_age_hours`) are tightly coupled to `check_persistence`'s patching of
  `common.subprocess` / `common.os` / `common.AUTH` (the P6 security tests) — moving them in P8a would
  silently defeat those patches and force a non-trivial rework of security-sensitive tests, only to
  move them **again** into `auth_nav` in P8b (churn). Resolved toward §E + P8a's "low risk"
  classification + the no-churn principle: the auth-file lifecycle stays in `common.py` and is
  extracted in **P8b** alongside `auth_nav`, where §E places it and where its test rework belongs.
  P8a still fully delivers its core objective (the pure leaves behind the shim). `gui_api`
  (`_auth_file_age_hours`) and `check_persistence` (`_restrict_to_owner`, `common.AUTH`) are
  consequently untouched.
- **No other deviation.** The four leaf bodies are verbatim; no behavior change; no lock (R1-R07).

## 11. Known limitations and external verification
- **Frozen exe gate (PA) — CI/external.** The OFFLINE reachability half (`check_app_modules` — the F6
  tripwire that proves every flat module is declared for freezing, plus `check_source_zip_smoke`) is
  green; the FROZEN `--self-test` exe gate runs in CI (`frozen-gate.yml` / `release.yml`), consistent
  with prior phases. A local PyInstaller build is recommended external verification but is not part of
  the offline DoD (the leaves are pure-stdlib, so the freeze risk is what `check_app_modules` already
  covers). No live TSMIS / browser path is exercised by P8a (the moved code is pure; the page/channel
  helpers that need a browser were not touched).
- **Docs.** `docs/architecture.md` / `docs/INDEX.md` / the CLAUDE.md repo-layout don't yet list the
  new leaf modules; doc reconciliation is **P11** per the plan (§E already anticipates these modules).
  The in-`common.py` docstring is updated so the edited file is self-accurate.

## 12. Exact diff scope Codex should review
Against baseline `42122ff` (exclude `docs/planning/`):
- **`scripts/errors.py`** / **`scripts/site_target.py`** / **`scripts/timeouts.py`** /
  **`scripts/routes.py`** (new) — the four pure leaves; bodies should be VERBATIM vs the deleted
  `common.py` blocks (diff the moved code for any drift). Note `site_target` is the renamed `site`.
- **`scripts/common.py`** — the deletions (the four leaf blocks + the now-unused `import threading`)
  + the re-export shim + the docstring. Confirm zero moved definitions remain and every previously
  exported name is re-imported.
- **`build/app.spec`** — `APP_MODULES += errors, site_target, timeouts, routes`.
- **`build/check_engine_leaves.py`** (new) — the leaf behaviors + the shim-parity (`is`) contract.
- **`build/check_export_engine.py`** — the `set_site` site-pin edit (moved-global monkeypatch → public API).
- **`.github/workflows/checks.yml`** — `check_engine_leaves.py` wired into the engine step.

Key checks: `check_engine_leaves`, `check_export_engine`, `check_import_direction`,
`check_app_modules`, the full 63-check suite. Suggested independent verification: diff each new leaf
against the corresponding deleted `common.py` block (verbatim), and confirm `from common import` for
every name returns the leaf's object.
