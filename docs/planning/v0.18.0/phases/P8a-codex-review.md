# P8a Codex Review

## Review round 1

### 1. Verdict: `PASS`

P8a complies with the approved leaf-extraction phase and is ready for phase approval. The product
diff is limited to the four pure engine leaves, the `common.py` re-export shim, packaging/test wiring,
and one test update that now pins site selection through the public `set_site()` API. I found no
blocking, required, or recommended findings.

The one material phase-boundary deviation is documented and acceptable: the final plan's short P8a
Affected line mentions auth-file lifecycle, but the detailed DAG places auth-file lifecycle in
`auth_nav.py` for P8b. Leaving it in `common.py` for P8a avoids breaking the P6 auth-hardening
characterization tests that still patch `common.subprocess`, `common.os`, and `common.AUTH`; it also
avoids a double move before P8b.

### 2. Blocking findings

None.

### 3. Required fixes

None.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md` and confirmed **P8a** is the phase currently marked
  `awaiting_review`, with baseline `42122ff`.
- Read the P8a section of `docs/planning/v0.18.0/05-claude-final-plan.md`, the detailed engine DAG in
  section E, `docs/planning/v0.18.0/phases/P8a-claude-report.md`, and relevant prior P6/P7a review
  context.
- Inspected the product diff from `42122ff`, excluding `docs/planning/**`: modified
  `.github/workflows/checks.yml`, `build/app.spec`, `build/check_export_engine.py`,
  `scripts/common.py`; new untracked `build/check_engine_leaves.py`, `scripts/errors.py`,
  `scripts/routes.py`, `scripts/site_target.py`, and `scripts/timeouts.py`.
- Confirmed the product diff does not touch frontend source, comparison/matrix/updater behavior,
  persisted settings/auth/cache/manifest formats, output layout, browser/session movement, or P8b
  mechanical engine modules.
- Compared the moved P8a definitions in `scripts/errors.py`, `scripts/site_target.py`,
  `scripts/timeouts.py`, and `scripts/routes.py` against `42122ff:scripts/common.py` by AST dump:
  selected classes, functions, constants, and route data all matched the baseline blocks.
- Confirmed `scripts/common.py` no longer defines duplicate moved class/function bodies and re-exports
  the public leaf objects used by current repo consumers.
- Searched for stale repo references to moved private site globals; the only product references now
  flow through `set_site`, `set_thread_site`, `get_site`, `get_url`, and `expected_host`.
- Ran and passed:
  - `python -B -X utf8 build/check_engine_leaves.py`
  - `python -B -X utf8 build/check_export_engine.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_fake_site.py`
  - `python -B -X utf8 build/check_persistence.py`
  - `python -B -X utf8 build/check_parallel_reconcile.py`
  - `python -B -X utf8 build/check_source_zip_smoke.py`
  - `python -B -X utf8 -m py_compile scripts/common.py scripts/errors.py scripts/site_target.py scripts/timeouts.py scripts/routes.py build/check_engine_leaves.py build/check_export_engine.py`
  - `node --check scripts/ui/app.js`
  - `git diff --check 42122ff -- . ':(exclude)docs/planning/**'`
- Ran an import smoke for `common`, the four new leaves, and the repo consumers named in the P8a report
  (`cli`, `login`, `exporter`, `exporter_parallel`, `matrix`, `self_test`, `gui_api`, `gui_worker`,
  `run_report`, all six `export_*` modules, `reports`, and `report_catalog`); all imports succeeded.
- Did not run the complete `build/check_*.py` suite, build scripts, PyInstaller, frozen self-tests,
  live TSMIS, credentials, browser profiles, private report data, browser/GUI launches, or shared
  release artifacts.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval for P8a. No open Codex findings remain for this phase.
