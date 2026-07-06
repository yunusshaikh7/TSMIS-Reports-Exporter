# P3 — Stable-ID taxonomy + manifest v1/v2 migration — Claude report

## 1. Phase ID and name
**P3** — Stable-ID taxonomy + manifest v1/v2 migration `[blocking; depends P0]`

## 2. Baseline commit
`ca3c2af` (HEAD after P2 committed). Baseline: **56** offline golden checks + the Node matrix
renderer green, byte-compile + `node --check app.js` green, tree clean apart from the
untracked `docs/planning/` workspace. (P3 adds `check_stable_ids.py`, taking the offline
suite 56 → **57**.) Dependency **P0 committed**
(`a009b6d`/`36ce1c4`/`4bbee65`); P3's only declared prereq.

## 3. Changes made
P3 makes report **selection and resume key on stable string IDs instead of registry list
position** (F7). A registry re-order can no longer resume the wrong report, and a legacy
`batch_job.json` (integer indices) migrates forward safely.

1. **`reports.py` — the 4-tier stable-ID taxonomy (§C.5).** Three immutable key tuples,
   each 1:1 with its registry list in registry order:
   - **export-op** `EXPORT_KEYS` = `tuple(spec.subdir …)` (derived, so it can never drift
     from the subdirs): `ramp_summary … intersection_detail` (7). The export-op key **is**
     the report-family key.
   - **consolidation-op** `CONSOLIDATE_KEYS` (8): `cons:<family>` with the Highway Log split
     `cons:highway_log_excel` / `cons:highway_log_pdf` / `cons:tsn_highway_log`.
   - **comparison-op** `COMPARE_KEYS` (15): composite `cmp:<family>:<flavor>` (flavor ∈
     `env` / `tsn` / `pdf_vs_tsn` / `pdf_vs_excel`; the HL-PDF cross-env row keeps the
     distinct family `highway_log_pdf`).
   - Lookups: `export_index_for_key` / `spec_for_export_key` / `export_key_for_spec` /
     `resolve_export_keys` (order-preserving, de-duplicating, unknown/disabled → `dropped`
     **with a logged warning**), `consolidate_index_for_key`, `compare_index_for_key`.
   - **Import-time integrity asserts**: every tier's keys are unique and length-matched to
     its registry list (a programming-error tripwire, not user input). The matrix `row_key`
     is **not** renamed (caches depend on it).
2. **`batch_manifest.py` — v1/v2 (F7 / R1-R04).** `_VERSION` 1→**2** (persists export-op
   **keys**); `build(report_keys, …)` writes keys. A **frozen `_V017_EXPORT_ORDER`** constant
   maps legacy v1 integer indices → keys (never a live view of `EXPORT_REPORTS`). `load()`
   accepts v1 **and** v2, **normalizes the report list to v2 keys in memory** (migrating v1
   indices, dropping out-of-range/non-string entries with a logged warning, de-duplicating),
   and stamps `version=2` so the next `save()` (the first `mark_done` on resume) **rewrites
   the file forward exactly once**. An unsupported version → `None` (corrupt-degrades, as
   before).
3. **`gui_worker.py` — resume resolution + no-env-done-on-empty (§C.5).** `BatchWorker._specs`
   resolves the manifest's **keys** to specs via `resolve_export_keys` (unknown/disabled
   dropped + logged, never mis-resolved by position). `BatchWorker.run` now **stops without
   marking any environment done** when nothing resolves — emitting an `error` + a
   `batch_done` with `completion=failed` — so a batch whose saved report types all vanished
   can't falsely "complete" with zero reports.
4. **`gui_api.py` — bridge is key-based.** `start_export` / `start_batch_export` take
   `report_keys`, resolve via `resolve_export_keys`, and the batch **persists the canonical
   keys**. The seven consolidate/compare endpoints (`consolidate_info`,
   `open_consolidate_input`, `start_consolidate`, `open_consolidated_folder`, `start_compare`,
   `get_compare_folders`, `start_compare_env`) take a `report_key` resolved via
   `consolidate_index_for_key` / `compare_index_for_key` (a bad key → `None` row → the
   existing "not available" error; the slot is never wedged). `get_initial_state` adds a
   `key` to every `reports` / `cons_reports` / `compare_reports` entry.
5. **`ui/app.js` — selection travels by key.** Checkboxes/radios carry `dataset.key`;
   `selectedReportKeys()` / `consChoice()` / `compareChoice()` return keys; a new
   `reportByKey()` maps a key back to its payload for display lookups (the Export/Everything
   env-scan overlays now read the row's `dataset.key`, not its DOM position). The `#mock`
   exercises the **identical** key contract: mock `REPORTS` / `CONS_REPORTS` / the
   `compare_reports` payload carry keys, and `repByKey` / `consByKey` resolve them in every
   mock action (export / batch / consolidate).

## 4. Files affected
**New (1):** `build/check_stable_ids.py` (CT-9 + stable-ID uniqueness, R1-T05).
**Modified product (5):** `scripts/reports.py`, `scripts/batch_manifest.py`,
`scripts/gui_worker.py`, `scripts/gui_api.py`, `scripts/ui/app.js`.
**Modified tests (5):** `build/check_b3_batch.py` (manifest/start_batch_export → keys + the
v1→v2 migration assertions), `build/check_gui_bridge.py` (bad-key consolidate +
files-kind compare key), `build/check_intersection_gate.py` (disabled export by key),
`build/check_matrix_bridge.py` (manifest build by keys), `build/check_a2_compare_filter.py`
(get_compare_folders / start_compare_env by key + bad-key fallback).
**Modified CI (1):** `.github/workflows/checks.yml` (wire `check_stable_ids`).
**Modified docs (2):** `docs/architecture.md`, `docs/reports.md` (the two "selection is by
index" statements P3 directly invalidated — see §10).
**Untouched:** `compare_core.py` (regression-locked), `app.spec` (no new module — `reports`
+ `batch_manifest` were already in `APP_MODULES`; `check_app_modules` stays green), the
updater/TLS, auth, the matrix `row_key`, `version.py`.

## 5. Architectural decisions
- **Parallel key tuples, not a new registry row shape.** `EXPORT_KEYS` / `CONSOLIDATE_KEYS`
  / `COMPARE_KEYS` sit beside the existing lists rather than changing each row to
  `(key, …)`. This keeps the registry rows append-only (the Protected contract: index
  consumers remain valid until P4) and avoids touching the many registry-introspection
  checks; the import-time length/uniqueness asserts catch any drift.
- **Export key = subdir (derived).** The family key already exists as `spec.subdir`, so
  `EXPORT_KEYS` is *derived* from the specs — provably never a hand-copied list that can
  drift. The other two tiers' keys are explicit literals (the HL splits/flavors have no
  single attribute), guarded by length + uniqueness asserts.
- **Migration lives in `batch_manifest`, validity lives at resolution.** `batch_manifest`
  stays dependency-light (stdlib json only — it must be importable at startup without
  pulling openpyxl/playwright), so it owns version + structural normalization + the **frozen**
  v1→key map, but does **not** import `reports`. The registry-level reject (unknown/disabled
  key → logged + dropped, no env-done on empty) happens where `reports` is already imported
  (`gui_worker._specs` / `gui_api`).
- **`idx` retained as display-order metadata.** The initial-state payload keeps `idx`
  (relabelled in-comment as display-order-only, not the selection contract) for P4's catalog
  and any remaining index consumer; the **selection** path is 100% key-based.
- **The matrix internal `export_idx`** (`matrix_rows()` row[3]) stays index-based — it is a
  per-process derivation, never persisted across a registry change, so it is outside F7 and
  the Protected "index consumer until P4" carve-out.

## 6. Compatibility and migration handling
- **`batch_job.json` v1 → v2:** a legacy manifest (integer indices) loads, migrates to keys
  via the frozen v0.17 order (out-of-range indices rejected, deduped), and is presented as
  v2; the next `mark_done` rewrites the file to v2. **One forward migration, idempotent.**
  Post-rollback (§G): a v2 manifest written post-P3 is not readable by pre-P3 code → rolling
  back P3 means reverting any v2 manifest (documented; v1 still accepted forward).
- **No output/cache/auth/config format change.** Caches, the matrix `row_key`, output layout,
  filenames, and `tsn_library` are untouched; the P1/P2 cache envelope is not revved here.
- **GUI bridge contract change is self-contained** (frontend + bridge + `#mock`); the
  console/`.bat` path does not use `gui_api`, so it is unaffected.

## 7. Tests and commands run
```
# pre-change characterization (baseline green at ca3c2af):
python build/{check_b3_batch,check_gui_bridge,check_matrix_bridge,
              check_a2_compare_filter,check_intersection_gate,
              check_batch_outcome,check_worker_lifecycle,check_report_library}.py   # all OK

# new check:
python build/check_stable_ids.py            # 24 assertions — uniqueness/round-trip,
                                            # resolve, v1→v2, F7 re-order proof, CT-9 resume,
                                            # no-env-done-on-empty — ALL GREEN

# RED proof (revert/run/restore): removed the gui_worker "no-env-done-on-empty" guard ->
#   check_stable_ids FAILS 3 assertions (env falsely marked done, no error surfaced,
#   batch_done.complete True); restored -> green.

python -m compileall -q scripts build version.py     # OK
node --check scripts/ui/app.js                       # OK
node build/check_mx_partial_render.js                # OK
python build/check_import_direction.py               # OK (no new module cycle)
python build/check_app_modules.py                    # OK (no new APP_MODULES entry needed)
python build/check_no_misspelling.py                 # OK (docs touched)
PYTHONIOENCODING=utf-8  python build/check_*.py  (×57, excl. fake_site/source_zip)  # 57/57

# #mock browser verification (port 8765 /index.html#mock, fresh app.js via cache:reload+reload):
#  - 7 export rows + 8 consolidate rows + 15 compare rows ALL carry dataset.key; 10 tabs
#  - selectedReportKeys()/consChoice()/compareChoice()/reportByKey() return keys
#  - full mock export (per-route ticks + completion summary), batch, and consolidate by KEYS
#    run with ZERO console errors; summary labels resolve via repByKey
#    ("TSAR: Ramp Summary","Highway Log", completion=complete)
```

## 8. Results
- **57/57** offline Python suite (56 → 57 with `check_stable_ids`) + Node renderer +
  byte-compile + `node --check` + import-direction + app_modules + product-name guard all
  green; `git diff --check` clean; no `REVERT-PROOF` marker.
- The new check proves the F7 contract: a **re-ordered registry still resolves saved keys to
  the same reports** (and asserts the key's list index actually moved, so the proof isn't
  vacuous), while an index scheme would not.
- `#mock` boots clean and every selection tier is key-driven end to end (verified live).
- `compare_core` / updater-TLS / auth / `app.spec` / matrix `row_key` untouched.

## 9. Before/after measurements
| Metric | Before (`ca3c2af`) | After (P3) |
|---|---|---|
| Offline golden checks | 56/56 | **57/57** |
| `batch_job.json` report field | integer indices (F7: re-order mis-resumes) | stable export-op **keys**; v1 auto-migrates |
| Bridge selection contract | list **index** (export/consolidate/compare) | stable **key** (all three tiers) |
| Empty manifest resolution | env could be marked **done** with zero reports | **no env-done**; error + `failed` surfaced |
| Stable-ID uniqueness | (unguarded) | import-time asserts + `check_stable_ids` |

No hot-path change: the key lookups are O(7/8/15) `tuple.index` calls per bridge action;
cold-start / matrix-snapshot baselines (R1-A01, P0 §8) are unaffected — P3 touches no export
or matrix hot loop.

## 10. Deviations from the approved plan
1. **`check_stable_ids.py` combines CT-9 + the R1-T05 uniqueness check** in one file (the plan
   lists them as the two P3 tests). They share the same registry/manifest fixtures and read
   naturally together; nothing is omitted.
2. **Two canonical-doc lines corrected here, not deferred to P11.** `docs/architecture.md` and
   `docs/reports.md` each said "selection is by index" — a statement P3 directly made false.
   Doc *reconciliation* remains P11's scope; I corrected only the two lines P3 invalidated
   (and added the "also add a `COMPARE_KEYS` entry" step to the add-a-comparison recipe so the
   recipe doesn't trip the new import-time assert). Flagged rather than silently left stale.
3. **`gui_api._pick_report` kept (not removed).** The plan's Affected list says
   "`_pick_report` + all index call sites." `_pick_report` remains as the bounds-checked
   accessor; the endpoints now feed it a *resolved index* (`<tier>_index_for_key(key)`), and
   the matrix's internal `export_idx` (a per-process, non-persisted derivation) still uses it
   under the Protected "index consumer until P4" carve-out. The **persisted/selection** paths
   are fully key-based — the F7 objective is met without an unnecessary rewrite of the
   bounds-check helper.

## 11. Known limitations & external verification
- **Work-PC acceptance (not DoD):** resuming a **real** v0.17-era paused batch on the
  locked-down work PC (the live v1→v2 migration of an on-disk `batch_job.json`) is the one
  step that can't run offline. The migration is fully covered by `check_b3_batch` +
  `check_stable_ids` against synthetic v1 manifests; the live confirmation is owed (§M).
- **`idx` is now write-only in the payload** (retained for P4). P4's `report_catalog` will
  consume/retire it; until then it is harmless display-order metadata.
- The broader knowledge-library reconciliation (any other doc that describes the registry by
  position) stays with **P11**.

## 12. Exact diff scope for Codex to review
- `scripts/reports.py` — the three `*_KEYS` tuples + lookups (`resolve_export_keys` reject/
  dedup semantics) + the import-time uniqueness/length asserts.
- `scripts/batch_manifest.py` — `_VERSION` 2, the frozen `_V017_EXPORT_ORDER`,
  `_migrate_v1_reports` / `_normalize_reports`, and `load()`'s v1/v2 acceptance + in-memory
  forward migration.
- `scripts/gui_worker.py` — `_specs` key resolution + the **no-env-done-on-empty** guard in
  `run()`.
- `scripts/gui_api.py` — `start_export` / `start_batch_export` key resolution + canonical-key
  persistence; the 7 consolidate/compare endpoints' `key→index`; the initial-state `key`
  fields.
- `scripts/ui/app.js` — `dataset.key` on all three tiers, `selectedReportKeys` /
  `*Choice` / `reportByKey`, the display-overlay lookups, the batch-library `startBatch`
  by-subdir, and the full `#mock` key wiring (`repByKey` / `consByKey`).
- `build/check_stable_ids.py` — the new CT-9 + uniqueness check (note the F7 re-order proof
  and the no-env-done RED-provable guard).
- `build/check_{b3_batch,gui_bridge,matrix_bridge,a2_compare_filter,intersection_gate}.py` —
  index→key migrations (no assertion weakened; new v1→v2 + reject-unknown coverage).
- `.github/workflows/checks.yml` — one added invocation.
- `docs/architecture.md`, `docs/reports.md` — the two corrected "selection is by index" lines.

`git diff --stat` vs `ca3c2af`: 13 files changed (+~430/−170) + 1 new `build/check_*.py`;
`docs/planning/` not staged. Suggested review order: `reports.py` (the key foundation) →
`batch_manifest.py` (v1/v2) → `gui_worker.py` (resume + empty guard) → `gui_api.py`/`app.js`
(bridge+frontend) → `check_stable_ids.py` → the migrated tests → docs.

---

# Remediation — Codex review round 1 (`BLOCKED`)

**Round addressed:** P3 Codex review **round 1** ([`P3-codex-review.md`](P3-codex-review.md)),
verdict `BLOCKED` — 3 blocking (P3-B01/B02/B03), 0 required, 0 recommendations. Every finding
was verified real against the workspace before fixing. The original report above is unchanged;
this section records the remediation.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P3-B01 | blocking | **Fixed** | manifest + selection validation is now all-or-nothing — no coercion, no silent drop/dedup; any invalid/duplicate/unknown/disabled key rejects the WHOLE saved selection (abort, manifest preserved, no env done) |
| P3-B02 | blocking | **Fixed** | the invalid/empty-resolution abort emits exactly ONE terminal (`error`), not `error`+`batch_done`; CT-10 exercises the real producer path through `_handle` |
| P3-B03 | blocking | **Fixed** | `compareKind()` resolves the row by key (`currentCompareRep().kind`) instead of array-indexing with a string; a new Node routing test locks folders→`start_compare_env` / files→`start_compare` |

### P3-B01 — fail-safe, all-or-nothing manifest + selection validation — Fixed

**Verified real.** §C.5 says invalid/duplicate/unknown/disabled/removed keys are *rejected*
(logged + banner), not silently dropped; CT-9 requires invalid v1 selections rejected with no
env done. The implementation coerced (`int(i)` accepted `True`/`1.9`/`"3"`), dropped
out-of-range/non-string entries, de-duplicated, and `resolve_export_keys` returned valid specs
plus a discarded `dropped` list — so a pending `["ramp_summary", "__removed__"]` ran *only*
Ramp Summary, marked the env done (`complete=True`), and lost the pending resume. Reproduced.

**Fix:**
- `batch_manifest._migrate_v1_reports` / `_normalize_reports` are now **1:1 and
  length-preserving**: a v1 entry that is `bool` / not-`int` / out-of-range, or a v2 entry that
  isn't a non-empty `str`, maps to a poison sentinel `_INVALID_KEY` (never coerced); **duplicates
  are kept** (no dedup). `build` no longer `str()`-coerces caller values.
- `reports.resolve_export_keys(keys)` now returns `(specs, invalid)` and **rejects duplicates**
  as well as unknown/disabled keys (each logged). Any non-empty `invalid` is a whole-set rejection.
- `gui_api.start_export` / `start_batch_export` return an error (no start) when `invalid` is
  non-empty.
- `gui_worker.BatchWorker.run` aborts (single terminal, below) when `_invalid_keys()` is
  non-empty **or** nothing resolves — **no environment is marked done, the manifest is preserved**.

So `["ramp_summary", "__removed__"]`, a duplicate, a coercible v1 entry, or an out-of-range index
now **all reject the whole saved selection** and leave the resume intact.

### P3-B02 — exactly one terminal for the invalid/empty path — Fixed

**Verified real.** The empty-resolution branch posted both `("error", …)` and
`("batch_done", …)`; both reach `_end_task`, and the characterized pre-P7a gap means a late
second terminal can clobber an already-dispatched successor.

**Fix:** the abort now emits a single non-terminal `("log", …)` plus exactly one terminal
`("error", ("general", <banner>))` and returns — **mirroring the existing AuthError batch path**
(which already emits only `error`, never `batch_done`). The user still gets a visible banner; the
manifest stays resumable.

**Tests:** `check_worker_lifecycle` gains a real **producer scenario** (`_batch_invalid`) in the
`_SCENARIOS` table, so the existing "emits exactly one terminal = `error`" + "frees the gate via
`_handle`" assertions now cover it; a focused `test_invalid_manifest_batch_advances_successor`
feeds that single terminal through `_handle` with an already-queued successor and asserts the
successor is **dispatched, not clobbered** (`mark_done` is stubbed to RAISE, proving no env is
marked done). `check_stable_ids` updated to assert exactly one `error` terminal + no `batch_done`
for partial / all-unknown / duplicate / empty manifests.

### P3-B03 — `compareKind()` resolved by key — Fixed

**Verified real.** `compareKind()` did `(S.init.compare_reports || [])[compareChoice()]` —
array-indexing with the `cmp:*` **string** key → `undefined` → defaulted to `"files"`, so every
**folders** comparison showed file inputs and `startCompare` called `api.start_compare` instead of
`api.start_compare_env`. My P3 `#mock` check verified row presence, not routing — exactly the gap
Codex named.

**Fix:** `compareKind()` now returns `currentCompareRep().kind || "files"` (key lookup). **New
`build/check_compare_routing.js`** (Node `vm`, like `check_mx_partial_render.js`) extracts
`compareChoice`/`currentCompareRep`/`compareKind`/`startCompare` and asserts a folders-kind key →
`compareKind()==="folders"` + routes to `start_compare_env`, a files-kind key → `"files"` + routes
to `start_compare`, and the no-selection default. Proven **RED** on the pre-fix array-index code
(folders routed to `start_compare`). Wired into `checks.yml`. **Re-verified live in `#mock`:**
selecting `cmp:ramp_summary:env` shows the folder section + routes to `start_compare_env`;
`cmp:highway_log:tsn` shows the file section + routes to `start_compare`; 0 console errors.

## Remediation changes (files)

| File | Change |
|---|---|
| `scripts/reports.py` | `resolve_export_keys` → `(specs, invalid)`, rejects duplicates + unknown/disabled (P3-B01) |
| `scripts/batch_manifest.py` | `_INVALID_KEY` poison; `_migrate_v1_reports`/`_normalize_reports` 1:1 length-preserving (no coerce/drop/dedup); `build` no `str()` (P3-B01) |
| `scripts/gui_worker.py` | `_invalid_keys()`; `run()` aborts all-or-nothing with a SINGLE `error` terminal — no `batch_done`, no env done (P3-B01/B02) |
| `scripts/gui_api.py` | `start_export`/`start_batch_export` reject the whole selection on any `invalid` (P3-B01) |
| `scripts/ui/app.js` | `compareKind()` resolves by key via `currentCompareRep()` (P3-B03) |
| `build/check_stable_ids.py` | all-or-nothing resolve/normalize + single-terminal abort assertions (P3-B01/B02) |
| `build/check_b3_batch.py` | v1 out-of-range → poison kept 1:1 (not dropped) (P3-B01) |
| `build/check_worker_lifecycle.py` | `_batch_invalid` producer scenario + successor-integrity test (P3-B02) |
| `build/check_compare_routing.js` | **new** — Compare kind/routing by key (P3-B03) |
| `.github/workflows/checks.yml` | wire `check_compare_routing.js` |

No product code outside the three findings changed; `compare_core` / updater-TLS / auth /
`app.spec` / `version.py` / matrix `row_key` remain untouched.

## Updated verification

```
python -m compileall -q scripts build version.py        # OK
PYTHONIOENCODING=utf-8  python build/check_*.py  (x57, excl. fake_site/source_zip)  # 57/57
node --check scripts/ui/app.js                          # OK
node build/check_mx_partial_render.js                   # OK
node build/check_compare_routing.js                     # OK (RED-proven on pre-fix compareKind)
python build/{check_import_direction,check_app_modules,check_no_misspelling}.py     # OK
git diff --check -- . ':(exclude)docs/planning/**'      # clean; no REVERT-PROOF marker survives
#mock (port 8765): Compare routing — folders-kind -> folder section + start_compare_env;
   files-kind -> file section + start_compare; 0 console errors
```

Revert/run/restore RED proofs this round: the `compareKind()` by-key fix (reverting to the
array-index form fails 2 `check_compare_routing.js` assertions); the single-terminal abort +
all-or-nothing reject are locked by `check_stable_ids` and the `_batch_invalid` producer scenario.

## Changed measurements

| Metric | P3 (pre-remediation) | After round-1 remediation |
|---|---|---|
| Offline Python suite | 57/57 | **57/57** |
| Node frontend checks | 1 (`mx_partial`) | **2** (+`compare_routing`) |
| `resolve_export_keys` contract | `(specs, dropped)` drop-and-continue | `(specs, invalid)` **all-or-nothing** (rejects dups too) |
| Invalid/empty batch resolution | `error` + `batch_done` (2 terminals) | exactly **one** `error` terminal; manifest preserved; no env done |
| Manifest normalization | coerce + drop + dedup | **1:1 length-preserving**, poison-on-invalid, dups kept |
| Compare tab routing | folders mis-routed to `start_compare` (file UI) | resolves by key → correct folder/file routing |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 2). Not committed;
planning folder untracked.

---

# Remediation — Codex review round 2 (`PASS WITH FIXES`)

**Round addressed:** P3 Codex review **round 2** ([`P3-codex-review.md`](P3-codex-review.md)),
verdict `PASS WITH FIXES` — 0 blocking (P3-B01/B02/B03 confirmed Resolved), **1 required
(P3-R01)**, 0 recommendations. The original report + round-1 remediation above are unchanged;
this section records the round-2 remediation.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P3-B01 / B02 / B03 | blocking | **Resolved (round 1; Codex-confirmed round 2)** | no further change |
| P3-R01 | required | **Fixed** | the eight P3-invalidated index-contract statements in comments/docstrings/canonical docs now describe the stable-key contract; `idx` is named display/current-order metadata; disabled keys are rejected server-side; malformed/duplicate manifest entries are retained for all-or-nothing rejection (not de-duplicated) |

### P3-R01 — stale index-based selection documentation — Fixed

**Verified real** at every cited location. P3 made keys the GUI/persistence contract, but several
comments and canonical descriptions still documented the pre-P3 index contract. Corrected —
**narrowly, only the P3-invalidated statements** (no broadening into P11's documentation
reconciliation, no unrelated historical material touched):

| Location | Was | Now |
|---|---|---|
| `reports.py` COMPARE_REPORTS tail comment | "registry indices above are unchanged (selection is by index)" | "registry ORDER unchanged; selection resolves by each row's stable `cmp:*` key (COMPARE_KEYS)" |
| `reports.py` `enabled_export_reports` docstring | "preserved so callers keep stable indices — manifests / env-scan / start_export index into the full list" | `idx` is the DISPLAY position (current-order metadata); the GUI/persistence contract is the export-op KEY; manifests/start_export travel by key |
| `reports.py` `export_reports_status` docstring | "with its stable index … reject a disabled index server-side" | `idx` is display metadata; the start guards reject a disabled report **by its stable export-op key** server-side |
| `ui/app.js` mock CONS_REPORTS comment | "the Consolidate radios index into THIS list" | the radios carry each row's stable `cons:*` key; `consolidate_info`/`start_consolidate` resolve by key |
| `ui/app.js` mock compare_reports comment | "Order matches the registry so the radios index correctly" | each row carries its `cmp:*` key, so selection/routing resolves by key; order just mirrors the registry for display parity |
| `check_stable_ids.py` module docstring | "out-of-range indices rejected … de-duplicated" | v1 migrates 1:1 (length-preserving); malformed/out-of-range entries poisoned, **duplicates kept** so resolution rejects the whole set all-or-nothing |
| `docs/reports.md` | "reject a disabled index server-side … EXPORT_REPORTS indices stay stable (the GUI passes each report's real `idx`)" | reject a disabled report by its stable export-op key server-side; the GUI/manifests pass **stable export-op KEYS** (`idx` is display-order metadata) |
| `docs/verification-and-testing.md` `check_intersection_gate` row | "reject a disabled index server-side, EXPORT_REPORTS indices stay stable" | reject a disabled report by its stable export-op key server-side (P3 — selection travels by key, not index) |

(Eight statements across the five cited files; `reports.py` had three.)

## Remediation changes (files)

| File | Change |
|---|---|
| `scripts/reports.py` | 3 comment/docstring corrections (COMPARE tail; `enabled_export_reports`; `export_reports_status`) |
| `scripts/ui/app.js` | 2 mock comment corrections (CONS_REPORTS; compare_reports) — comment-only, no behavior change |
| `build/check_stable_ids.py` | module-docstring correction (1:1 / poison / keep-dups) |
| `docs/reports.md` | the disabled-report + stable-key statement |
| `docs/verification-and-testing.md` | the `check_intersection_gate` row |

Documentation/comment-only; no product behavior, no test logic, and no CI wiring changed this
round. `compare_core` / updater-TLS / auth / `app.spec` / `version.py` / matrix `row_key` remain
untouched.

## Updated verification

```
python -m compileall -q scripts build version.py        # OK
PYTHONIOENCODING=utf-8  python build/check_*.py  (x57)   # 57/57
node --check scripts/ui/app.js                          # OK
node build/check_mx_partial_render.js                   # OK
node build/check_compare_routing.js                     # OK
python build/check_no_misspelling.py                    # OK (docs touched)
git diff --check -- . ':(exclude)docs/planning/**'      # clean; no REVERT-PROOF marker survives
grep (selection-is-by-index / index-into / reject-a-disabled-index / indices-stay-stable /
   de-duplicated) across the 5 cited files              # (none) — no P3-invalidated wording remains
```

## Changed measurements

No measurement change: the round is documentation/comment-only. The offline suite stays **57/57**
and the two Node frontend checks stay green. The only delta is wording — eight P3-invalidated
index-contract statements now describe the stable-key contract.

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 3). Not committed;
planning folder untracked.
