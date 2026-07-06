# P8b Codex Review

## Review round 1

### 1. Verdict: `PASS WITH FIXES`

P8b is a successful behavior-neutral mechanical move overall: the new engine layers match the
`bdbda4d` `common.py` bodies by AST, the import graph is acyclic, packaging reachability covers the
new modules, and the relevant engine/GUI/worker characterization checks pass. I found no blocking
runtime regression.

One required shim-contract fix remains before phase approval: two non-private helpers named in the
approved DAG were moved to their new homes but are no longer re-exported by `common.py`, and the new
parity check does not cover them.

### 2. Blocking findings

None.

### 3. Required fixes

#### P8b-R01 — Required — `common.py` shim omits two named public DAG helpers

- **Affected plan/report section:** P8b engine mechanical movement; final plan section E
  (`auth_nav.py` / `edge_device.py` / `common.py SHIM re-exporting all of the above`);
  `P8b-claude-report.md` sections 3, 6, 10, and 12.
- **Repository evidence:** `docs/planning/v0.18.0/05-claude-final-plan.md` names
  `auth_nav.py` as owning `dump_auth_failure` and `edge_device.py` as owning
  `open_edge_device_context`, then describes `common.py` as the shim re-exporting the engine DAG.
  `docs/planning/v0.18.0/phases/P8b-claude-report.md` likewise names both moved helpers and claims
  the shim preserves the import surface. In code, `scripts/auth_nav.py::dump_auth_failure` and
  `scripts/edge_device.py::open_edge_device_context` exist, but `scripts/common.py` does not import
  either name from those modules. A direct probe returned:
  `hasattr(common, "dump_auth_failure") == False` and
  `hasattr(common, "open_edge_device_context") == False`. `build/check_engine_layers.py::OWNS`
  also omits both names, so the parity check cannot catch the gap.
- **Why this is not blocking:** current in-repo `from common import ...` consumers do not import
  these two helpers, and the behavior/worker checks pass.
- **Exact correction expected:** re-export `dump_auth_failure` from `auth_nav` and
  `open_edge_device_context` from `edge_device` in `scripts/common.py`; add both names to
  `build/check_engine_layers.py::OWNS` so shim parity locks them permanently; rerun
  `build/check_engine_layers.py`, `build/check_export_engine.py`, `build/check_gui_bridge.py`,
  `build/check_import_direction.py`, `build/check_app_modules.py`, and byte-compile for the
  touched modules. Do not re-export private implementation details unless Claude explicitly updates
  the shim contract and tests to define that boundary.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md` and confirmed **P8b** is the phase currently
  marked `awaiting_review`, with baseline `bdbda4d`.
- Read the P8b section and section E DAG in `docs/planning/v0.18.0/05-claude-final-plan.md`,
  `docs/planning/v0.18.0/phases/P8b-claude-report.md`, and relevant P8a/P6/P7a review context.
- Inspected the product diff from `bdbda4d`, excluding `docs/planning/**`: modified
  `.github/workflows/checks.yml`, `build/app.spec`, `build/check_export_engine.py`,
  `build/check_gui_bridge.py`, `build/check_persistence.py`, `scripts/common.py`; new untracked
  `build/check_engine_layers.py`, `scripts/auth_nav.py`, `scripts/browser_channels.py`,
  `scripts/edge_device.py`, `scripts/report_nav.py`, and `scripts/session.py`.
- Confirmed the product diff does not touch frontend source, comparison/matrix/updater behavior,
  persisted settings/auth/cache/manifest formats, output layout, or P8c behavior-change code.
- Independently AST-compared the moved P8b classes/functions/constants against
  `bdbda4d:scripts/common.py`: all checked moved symbols matched, and none of the moved function/class
  bodies remain defined in current `scripts/common.py`.
- Checked current in-repo `from common import ...` consumers: no currently imported name is missing
  from the shim.
- Checked the broader old `common.py` top-level surface and found `dump_auth_failure` and
  `open_edge_device_context` are no longer present on `common`, which is recorded as P8b-R01 above.
- Ran and passed:
  - `python -B -X utf8 build/check_engine_layers.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_export_engine.py`
  - `python -B -X utf8 build/check_persistence.py`
  - `python -B -X utf8 build/check_gui_bridge.py`
  - `python -B -X utf8 build/check_fake_site.py`
  - `python -B -X utf8 build/check_source_zip_smoke.py`
  - `python -B -X utf8 build/check_engine_leaves.py`
  - `python -B -X utf8 build/check_worker_lifecycle.py`
  - `python -B -X utf8 build/check_b3_batch.py`
  - `python -B -X utf8 build/check_matrix_bridge.py`
  - `python -B -X utf8 build/check_day_matrix.py`
  - `python -B -X utf8 build/check_batch_outcome.py`
  - `python -B -X utf8 build/check_no_misspelling.py`
  - `python -B -X utf8 -m py_compile scripts/common.py scripts/browser_channels.py scripts/auth_nav.py scripts/report_nav.py scripts/edge_device.py scripts/session.py build/check_engine_layers.py build/check_persistence.py build/check_export_engine.py build/check_gui_bridge.py`
  - `node --check scripts/ui/app.js`
  - `git diff --check bdbda4d -- . ':(exclude)docs/planning/**'`
- Ran an import smoke over every flat `scripts/*.py` module; all imports succeeded.
- Did not run the complete `build/check_*.py` suite, build scripts, PyInstaller, frozen self-tests,
  live TSMIS, credentials, browser profiles, private report data, GUI launches, or shared release
  artifacts. The local `check_fake_site.py` browser fixture was the only browser-backed check.

### 6. Whether Claude may proceed toward phase approval

Not yet. Claude should apply P8b-R01 and return P8b for review. No blocking findings remain, so this
should be a small shim/test remediation rather than a phase redesign.

## Review round 2

### 1. Verdict: `PASS`

P8b is ready for phase approval. The round-1 required finding (**P8b-R01**) is resolved: the
`common.py` shim now re-exports both §E-named public DAG helpers, and `build/check_engine_layers.py`
locks those re-exports in its parity contract. I found no new blocking, required, or recommended
findings.

### 2. Blocking findings

None.

### 3. Required fixes

None.

- **P8b-R01 — Resolved.** `scripts/common.py` now imports `dump_auth_failure` from `auth_nav` and
  `open_edge_device_context` from `edge_device`; `build/check_engine_layers.py::OWNS` now includes
  both names. Independent probes confirm `common.dump_auth_failure is auth_nav.dump_auth_failure` and
  `common.open_edge_device_context is edge_device.open_edge_device_context`.

### 4. Non-blocking recommendations

None.

### 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`; confirmed **P8b** remains `awaiting_review`
  with baseline `bdbda4d`, and coordination records round-1 `PASS WITH FIXES` with R01 remediated.
- Re-read the P8b final-plan section, section E DAG, `docs/planning/v0.18.0/phases/P8b-claude-report.md`
  remediation, and this review file's prior round.
- Inspected the product diff from `bdbda4d`, excluding `docs/planning/**`; scope remains the P8b
  mechanical engine-layer move plus test/packaging wiring:
  `.github/workflows/checks.yml`, `build/app.spec`, `build/check_export_engine.py`,
  `build/check_gui_bridge.py`, `build/check_persistence.py`, `scripts/common.py`, and new
  `build/check_engine_layers.py`, `scripts/auth_nav.py`, `scripts/browser_channels.py`,
  `scripts/edge_device.py`, `scripts/report_nav.py`, `scripts/session.py`.
- Confirmed no frontend source, comparison/matrix/updater behavior, persisted settings/auth/cache/
  manifest formats, output layout, or P8c behavior-change code was introduced.
- Ran the exact P8b-R01 probe:
  - `hasattr(common, "dump_auth_failure")`
  - `hasattr(common, "open_edge_device_context")`
  - `common.dump_auth_failure is auth_nav.dump_auth_failure`
  - `common.open_edge_device_context is edge_device.open_edge_device_context`
- Re-ran an AST comparison of the moved P8b symbols against `bdbda4d:scripts/common.py`; no moved
  body/constant mismatches and no moved function/class bodies remain defined in current `common.py`.
- Ran an import smoke over every flat `scripts/*.py` module; all imports succeeded.
- Ran and passed:
  - `python -B -X utf8 build/check_engine_layers.py`
  - `python -B -X utf8 build/check_import_direction.py`
  - `python -B -X utf8 build/check_app_modules.py`
  - `python -B -X utf8 build/check_export_engine.py`
  - `python -B -X utf8 build/check_gui_bridge.py`
  - `python -B -X utf8 build/check_persistence.py`
  - `python -B -X utf8 -m py_compile scripts/common.py scripts/browser_channels.py scripts/auth_nav.py scripts/report_nav.py scripts/edge_device.py scripts/session.py build/check_engine_layers.py build/check_persistence.py build/check_export_engine.py build/check_gui_bridge.py`
  - `node --check scripts/ui/app.js`
  - `git diff --check bdbda4d -- . ':(exclude)docs/planning/**'`
- Did not run the complete `build/check_*.py` suite, build scripts, PyInstaller, frozen self-tests,
  live TSMIS, credentials, browser profiles, private report data, GUI launches, or shared release
  artifacts.

### 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval for P8b. No open Codex findings remain for this phase.
