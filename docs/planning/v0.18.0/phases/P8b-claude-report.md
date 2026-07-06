# P8b — Engine mechanical movement (acyclic DAG, shim) — Claude report

## 1. Phase ID and name
**P8b** — Engine mechanical movement (acyclic DAG, shim) `[blocking; depends P8a]`

## 2. Baseline commit
`bdbda4d` (HEAD after P8a committed — "refactor: extract engine leaves … behind common shim (P8a)").
Baseline characterization green: `check_export_engine`, `check_fake_site`, `check_persistence`,
`check_gui_bridge`, `check_import_direction`, `check_app_modules`, `check_engine_leaves`; tree clean apart
from the untracked `docs/planning/`. Dependency **P8a committed** (`bdbda4d`).

## 3. Changes made
Move the rest of `common.py` — the field-hardened browser / auth / Edge-device / session flows — into the
verified acyclic DAG (§E), behind the `common.py` re-export shim, **behavior-neutral** (R1-R08 / R1-B03 /
D04 / F14). Every moved function/constant body is **VERBATIM** (AST-identical to the baseline).

1. **`scripts/browser_channels.py` (L1)** — browser launch + channel resolution/probing (`launch_browser`,
   the channel resolve/probe cache, `set/get/init_preferred_channel`, `check_browsers`, the LNA app/login
   contexts). Independent of auth.
2. **`scripts/auth_nav.py` (L2)** — page sign-in/navigation (`navigate_with_auth`, `is_logged_in`,
   `require_signed_in`/`require_site_params`, `auth_state`, `dump_auth_failure`) **+ the auth-file
   lifecycle** (`save_auth_state`/`require_valid_auth`/`has_valid_auth`/`clear_auth`/`_restrict_to_owner`/
   `_auth_file_age_hours`) — the work P8a deferred here per §E. `page_url_for_display` is homed here too
   (see §10).
3. **`scripts/report_nav.py` (L2', above auth_nav)** — report-form interaction (`select_report`,
   `preflight`, `report_error_text`, `wait_with_skip_option`, `maybe_screenshot`).
4. **`scripts/edge_device.py` (L3)** — Edge device-SSO login + storage-state capture
   (`launch_edge_login_context`, the `capture_*`, `open_edge_device_context`, `try_device_sso_login`,
   `storage_state_is_portable`); uses L1 + L2.
5. **`scripts/session.py` (L4)** — `new_authed_browser`; orchestrates L1 + L2 + L3.
6. **`scripts/common.py`** — now a **58-line pure re-export shim** (1435 → 58): re-imports every public name
   from the leaves (P8a) and the five new layers (P8b), so `from common import X` is unchanged for all
   consumers. The shared `"tsmis.auth"` logger name is preserved in every module (same logger instance), so
   log output is byte-identical. Docstring updated to describe the full layered shim.
7. **`build/app.spec`** — `APP_MODULES += browser_channels, auth_nav, report_nav, edge_device, session`
   (F6 packaging gate).
8. **`build/check_engine_layers.py`** (new) — the P8b structural lock: shim parity (39 `is` identities),
   no-upward-import (no engine module imports `common`), DAG layering (each module imports only its allowed
   lower set), and the thread-agnostic-engine assertion (§5).
9. **Three characterization tests retargeted** to the modules the moved code now lives in (see §6).

## 4. Files affected
**New (6):** `scripts/browser_channels.py`, `scripts/auth_nav.py`, `scripts/report_nav.py`,
`scripts/edge_device.py`, `scripts/session.py`, `build/check_engine_layers.py`.
**Modified product (1):** `scripts/common.py` (engine removed → pure shim + docstring).
**Modified packaging/CI (2):** `build/app.spec` (APP_MODULES +5), `.github/workflows/checks.yml`
(`check_engine_layers` wired into the engine step).
**Modified tests (3):** `build/check_persistence.py`, `build/check_export_engine.py`,
`build/check_gui_bridge.py` (retargets — §6).
**Untouched:** every `common` consumer's call sites (`exporter`, `exporter_parallel`, `cli`, `login`,
`matrix`, `gui_api`, `gui_worker`, the `export_*`, `self_test`), `compare_core`, the matrix/updater,
`ui/*`, `version.py`, and the P8a leaves. No persisted-format / behavior change. The one-shot extraction
generator was deleted (not shipped).

## 5. Architectural decisions
- **Verbatim move behind the shim.** Bodies are AST-identical to baseline (proven — §7); the shim re-exports
  the same objects (`common.X is module.X`). The decomposition is the only change; behavior, log output, and
  the import surface are preserved.
- **Cycle broken by re-homing one unplaced helper, not by editing a body.** §E's "independent L2/L2'
  siblings" doesn't hold against the real call graph (§10); resolved by homing `page_url_for_display` with
  its sole caller `auth_state` in auth_nav, so report_nav is a clean one-way dependent of auth_nav.
- **Shared `"tsmis.auth"` logger across the split** — every module's `log` is the SAME instance, so log
  records (logger name included) are byte-identical and `common.log` still resolves.
- **Thread-affinity is preserved by construction + locked structurally.** Playwright's sync API is
  thread-affine; thread ownership lives with the calling worker (`gui_worker`), NOT the engine library. The
  verbatim move changes no page-touching body and introduces no new threading, so the contract is unchanged;
  `check_engine_layers` asserts no engine module pulls in `threading` at module level (the static tripwire).

## 6. Compatibility and migration handling
- **Import surface preserved.** All 61 `from common import` names re-export the SAME object (25 P8a leaves +
  36 P8b layer names); `check_engine_layers::test_shim_parity` asserts the 39 P8b identities. No consumer
  call site changed.
- **Tests retargeted** (the moved code's patch points moved with it):
  - `check_persistence` → patches `auth_nav.{subprocess,os,AUTH}` + calls `auth_nav.{save_auth_state,
    _restrict_to_owner}` (the auth-file lifecycle now lives in auth_nav).
  - `check_export_engine` → `monkeypatch(auth_nav, "dump_auth_failure", …)` (its caller `require_site_params`
    is in auth_nav and looks the name up there).
  - `check_gui_bridge` → reads the channel internals `browser_channels.{_preferred_channel,
    _candidate_channels,_parallel_candidates}` (the public `set_preferred_channel`/`BROWSER_CHANNELS` stay via
    the shim, which also exercises the re-export).
- **No persisted-format / migration / behavior change.** No config/manifest/cache/auth/output touch; auth
  file path + format unchanged (only its module home moved).
- **Rollback:** per-module — re-inline a layer into `common.py` and drop its re-export; the shim isolates the
  seam. Acyclicity is enforced by `check_import_direction`.

## 7. Tests and commands run
- **Verbatim proof:** AST-compared every moved symbol against `bdbda4d:scripts/common.py` — **0 mismatches**
  (all bodies byte-identical), 0 duplicated (except the intentional per-module `log`), 0 baseline symbols
  left behind.
- **DAG:** `check_import_direction` acyclic with the 5 new nodes; `check_engine_layers` (shim parity +
  no-upward-import + layering + thread-agnostic) GREEN.
- **Behavior-neutral characterization:** `check_fake_site` (the real selector contract over a browser
  fixture — exercises the moved `select_report`/`preflight`/`report_error_text`), `check_export_engine`
  (auth/report logic), `check_persistence` (auth-file atomic + ACL), `check_gui_bridge` (channel order) all
  GREEN after the retargets.
- **Packaging:** `check_app_modules` red→green after the APP_MODULES +5; `check_source_zip_smoke` GREEN.
- **Full blocking suite (CI-style, `set -e`, `PYTHONIOENCODING=utf-8`):** all **64** `build/check_*.py` + 2
  Node frontend checks + `node --check app.js` + byte-compile (`scripts build version.py`) — GREEN.
  `git diff --check` clean.
- **Import smoke:** all **70** flat `scripts/*.py` modules import cleanly; no module imports `common`
  (one-way shim). Unused-import scan: the 5 engine modules are clean (the shim's "unused" names are the
  intentional re-export surface; CI ruff doesn't select F401, matching the P8a shim).

## 8. Results
All green. `common.py` is a 58-line re-export shim over a clean 9-module engine DAG (4 leaves + 5 layers);
every moved body is verbatim; the import surface is byte-identical; the layering is acyclic and locked.
The field-hardened auth/browser/Edge/session flows are relocated, not modified.

## 9. Before/after measurements
| Metric | Before (`bdbda4d`) | After |
|---|---|---|
| `common.py` | 1435 lines | **58** lines (pure re-export shim) |
| Engine layer modules | 0 (inlined) | 5 — browser_channels (376), auth_nav (463), report_nav (255), edge_device (325), session (62) |
| Moved-symbol AST mismatches | n/a | **0** (verbatim); 0 left behind; 0 dupes |
| `APP_MODULES` | 61 | 66 (+5 layers) |
| Offline Python checks | 63 | 64 (+`check_engine_layers`) |
| Import-direction graph | acyclic | acyclic (+5 layer nodes; auth_nav↔report_nav cycle resolved) |
| `from common import X` surface | baseline | byte-identical (61 names; 39 P8b `is` identities asserted) |

## 10. Deviations from the approved plan
- **§E's "independent L2/L2' siblings" was inaccurate — a real `auth_nav ↔ report_nav` cycle.** The actual
  call graph has `auth_state → page_url_for_display` and `preflight → dump_auth_failure`. Since §E explicitly
  places `dump_auth_failure` in auth_nav but leaves `page_url_for_display` **unplaced**, I homed
  `page_url_for_display` with its sole caller `auth_state` in **auth_nav**, making `report_nav` a clean
  one-way dependent of auth_nav (L2', above L2). No body was modified; the resulting DAG is acyclic
  (verified). This is the minimal, body-preserving resolution of the §E inaccuracy.
- **`page_url_for_display` lives in auth_nav, not report_nav.** Consequence of the cycle fix above; it is
  re-exported by the shim, so external callers are unaffected.
- **Auth-file lifecycle landed in auth_nav** — the P8a-deferred work, executed here exactly as §E specifies
  (this is the home P8a's report named).
- **"Thread-affinity assertions" interpreted as a structural lock + verbatim preservation.** A true runtime
  thread-affinity test needs a live Playwright browser (work-PC/external), so it can't run offline. The
  contract is preserved by the verbatim move (no page body changed, no new threading); `check_engine_layers`
  adds the static thread-agnostic-engine assertion. Live thread-affinity verification remains external (§11).
- **No other deviation.** No behavior change; no lock; the field-hardened flows are moved, not modified.

## 11. Known limitations and external verification
- **Frozen exe gate (PA) — CI/external.** The OFFLINE reachability half (`check_app_modules` + the source-ZIP
  smoke) is green; the FROZEN `--self-test` exe gate runs in CI (`frozen-gate.yml` / `release.yml`),
  consistent with prior phases. The moved modules pull in `playwright` lazily (in-function) exactly as
  before, so the freeze profile is unchanged.
- **Live work-PC verification owed (not DoD).** The auth/browser/Edge-device/session flows are field- and
  work-PC-critical; the move is proven behavior-neutral offline (verbatim AST + the selector contract + the
  auth-file tests), but a live sign-in/export + Edge one-click on the managed PC is the final acceptance for
  these flows — external (§M), as for any auth/browser change.
- **Docs.** `docs/architecture.md` / `docs/INDEX.md` / `docs/internals/` and the CLAUDE.md repo-layout don't
  yet list the new layer modules; doc reconciliation is **P11** per the plan (§E already specifies the DAG).
  The in-`common.py` docstring is updated so the edited file is self-accurate.

## 12. Exact diff scope Codex should review
Against baseline `bdbda4d` (exclude `docs/planning/`):
- **`scripts/browser_channels.py` / `auth_nav.py` / `report_nav.py` / `edge_device.py` / `session.py`** (new)
  — diff each moved body against the corresponding `bdbda4d:scripts/common.py` block; they should be VERBATIM
  (AST-identical — §7). Note `page_url_for_display` moved into auth_nav (cycle fix, §10).
- **`scripts/common.py`** — now a pure re-export shim; confirm zero logic remains and every previously
  exported name is re-imported (the import surface).
- **`build/app.spec`** — `APP_MODULES += browser_channels, auth_nav, report_nav, edge_device, session`.
- **`build/check_engine_layers.py`** (new) — shim parity + no-upward-import + DAG layering + thread-agnostic.
- **`build/check_persistence.py` / `check_export_engine.py` / `check_gui_bridge.py`** — the retargets
  (common → auth_nav / browser_channels) for the moved patch points.
- **`.github/workflows/checks.yml`** — `check_engine_layers.py` wired into the engine step.

Key checks: the AST-verbatim comparison, `check_import_direction`, `check_engine_layers`, `check_fake_site`,
`check_export_engine`, `check_persistence`, `check_gui_bridge`, `check_app_modules`, the full 64-check suite.
Suggested independent verification: AST-diff each new module against the baseline `common.py`, confirm the
module graph is acyclic, and confirm `from common import X` returns the owning layer's object for all 61
names.

---

## Remediation — Codex review round 1

**Round addressed:** Round 1 (`PASS WITH FIXES`) — `P8b-codex-review.md`. No blocking findings; the single
required finding is resolved. The phase stays `awaiting_review`.

### Finding dispositions

| Finding | Severity | Disposition |
|---|---|---|
| **P8b-R01** — `common.py` shim omits two named public DAG helpers (`dump_auth_failure`, `open_edge_device_context`) | Required | **Fixed** — both re-exported by the shim + locked in the parity check. |

### P8b-R01 — root cause + fix

Codex is correct. The original shim re-exported only the names some in-repo module imports `from common`
today (the 61-name import surface). But §E names `dump_auth_failure` under `auth_nav` and
`open_edge_device_context` under `edge_device`, and says `common.py` is the SHIM "re-exporting all of the
above" — so the shim contract is the **§E-named public DAG surface**, which includes these two public
(non-underscore) helpers even though no consumer imports them yet. Both were moved to their new homes but
left off the shim, and `check_engine_layers::OWNS` omitted them, so parity could not catch the gap. Codex's
probe (`hasattr(common, "dump_auth_failure") == False`, `… "open_edge_device_context" == False`) was
accurate.

Fix (exactly Codex's correction; no private internals touched):
1. **`scripts/common.py`** — added `dump_auth_failure` to the `from auth_nav import (…)` block and
   `open_edge_device_context` to the `from edge_device import (…)` block. The shim is still a pure re-export
   (59 lines, zero top-level defs/classes; no engine body re-introduced — verified).
2. **`build/check_engine_layers.py`** — added `dump_auth_failure` to `OWNS["auth_nav"]` and
   `open_edge_device_context` to `OWNS["edge_device"]`, with a comment recording that `OWNS` is the §E-named
   public DAG surface (the two helpers no consumer imports today are part of the shim contract). Parity now
   permanently locks both as `common.X is <layer>.X`.

Scope discipline (per Codex's caveat): the OTHER still-unexported moved symbols are all private
implementation details (`_page_host`, `_site_params_ok`, `_resolve_channel`, `_probe_channel`,
`_new_app_context`, `_free_local_port`, `_known_edge_profile_names`, the `_SIGNED_IN_JS`/`_AUTH_DIAG_JS`
constants, the channel caches, …) and §E does **not** name them — they stay internal to their layers; the
shim contract is unchanged for them.

### Updated verification

- **Codex's exact probe now passes:** `hasattr(common, "dump_auth_failure") == True`,
  `hasattr(common, "open_edge_device_context") == True`, and both are the SAME object as the owning layer's
  (`common.dump_auth_failure is auth_nav.dump_auth_failure`, `common.open_edge_device_context is
  edge_device.open_edge_device_context`).
- **`check_engine_layers` GREEN** with the two added parity assertions. **RED-proven:** dropping either
  re-export makes the parity check error with `AttributeError: module 'common' has no attribute …` (the gap
  is now caught), and restoring it passes.
- **Bodies unchanged / no duplication:** the 5 layer modules were not touched; the AST-verbatim comparison
  vs `bdbda4d:scripts/common.py` is still **0 mismatches**, and `common.py` still defines **0** engine
  bodies (pure shim).
- **Reran Codex's checks + the full suite (CI-style):** `check_engine_layers`, `check_export_engine`,
  `check_gui_bridge`, `check_import_direction`, `check_app_modules`, byte-compile of the touched modules —
  all GREEN; plus the full **64** `build/check_*.py` + 2 Node + `node --check app.js` + byte-compile + the
  70-module import smoke + `git diff --check` clean. Diff scope unchanged (same 6 modified + 6 new files;
  `docs/planning/` untracked).

### Changed measurements (vs §9)

| Metric | Original P8b | After remediation |
|---|---|---|
| Shim re-exports | 61 (import-surface names only) | 63 (+ the 2 §E-named public DAG helpers `dump_auth_failure`, `open_edge_device_context`) |
| `check_engine_layers` shim-parity identities | 39 | 41 |
| `common.py` top-level engine defs | 0 (pure shim) | 0 (pure shim) — unchanged |
| Moved-body AST mismatches | 0 | 0 — unchanged (layers untouched) |
