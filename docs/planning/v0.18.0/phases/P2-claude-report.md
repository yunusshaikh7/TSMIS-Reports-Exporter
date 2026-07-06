# P2 — Transactional artifact lifecycle (F2/F9/F5) — Claude report

## 1. Phase ID and name
**P2** — Transactional artifact lifecycle (F2/F9/F5) `[blocking; depends P1]`

## 2. Baseline commit
`e47b700` (HEAD after P1 committed). Baseline: **54** offline golden checks + the Node matrix
renderer green, byte-compile + `node --check app.js` green, tree clean apart from the untracked
`docs/planning/` workspace. (`check_source_zip_smoke` / `check_fake_site` are the build/browser
gates excluded from the offline run.)

## 3. Changes made
P2 makes the artifact lifecycle **transactional and identity-aware** so the engine never leaves
zero copies, never truncates a prior workbook on an interrupted write, and never reuses a
consolidated/comparison that its inputs have outgrown. One new leaf module owns all three
concerns; `compare_core` stays untouched (it is handed a temp path and the wrapper finalizes).

1. **New `scripts/artifact_store.py`** — the leaf module (imports only stdlib + `events`):
   - **Atomic single-file write (F9)** — `atomic_save(workbook, out_path)`: write to a
     `<stem>.tmp-<token><suffix>` sibling, then `os.replace` onto `out_path`. An interrupted /
     failed / locked write leaves the prior file intact (the destination open in Excel still
     raises `PermissionError`, so the consolidators' existing handlers are unchanged).
   - **Multi-file commit (F9 / CT-8b)** — `commit_workbook(final, produce_fn, *, twin=False,
     validate=None, confirm_overwrite=None)`: hand `produce_fn` a temp path, validate
     ("openable + a workbook part", cheap stdlib `zipfile`), `os.replace`, and **rewrite the leaked
     temp name out of** `output_path` + `summary_lines`. For `twin=True` (a `mode="both"`
     comparator) the **values** workbook is the single transactional artifact (committed first);
     the **formulas** sibling is best-effort (committed second; failure leaves values committed +
     logs). `confirm_overwrite` is checked against the FINAL destination(s) before producing.
   - **Input fingerprint (F5 / R1-R03)** — `fingerprint(folder)` = a hash of sorted
     `(name, size, mtime_ns)` + the file count over the store's data files (excludes `~$` locks,
     our sidecars, in-flight temp/`.staging`; an unreadable folder/file ⇒ the `_UNREADABLE`
     sentinel ⇒ stale). `write_consolidated_fingerprint` / `consolidated_fresh` persist + read a
     `<workbook>.fingerprint.json` sidecar after a successful build; missing/corrupt/old/mismatch
     ⇒ stale.
   - **Journaled store promotion + recovery (F2)** — `promote_store(live, staged)`: validate
     staging non-empty → write the journal at **`<parent>/.promote/<token>.json`** (never inside
     the renamed `live`) → `rename(live → live.bak-<token>)` → `rename(staged → live)` → delete
     journal → drop backup. A failure mid-swap restores `live` from the backup and discards
     staging; a locked `live` keeps last-good. `recover_promotions(root)`: on next launch, restore
     `live` from its backup when `live` is missing (the crash-between-renames window), else clean
     residue; also sweep orphan `*.staging` / `*.bak-*` whose live exists. Idempotent; never
     raises.
2. **F2 — `gui_worker._swap_store_dir`** now **delegates** to `artifact_store.promote_store` (the
   old rmtree-then-rename-with-merge body is gone; the merge fallback's partial-state risk is
   replaced by the journaled rename + recovery).
3. **F2 recovery — `updater.cleanup_leftovers`** calls `_recover_store_promotions()` →
   `artifact_store.recover_promotions(paths.OUTPUT_ROOT)` on every GUI launch, BEFORE the
   frozen-only branch (so it also repairs in dev). A failure there never wedges startup.
4. **F9 — consolidator save sites atomic.** The base `consolidate_xlsx` (`wb.save` → `atomic_save`)
   covers Ramp Detail / Highway Sequence / Highway Log (Excel) / the PDF & TSN Highway Log
   consolidators; the three standalone final writers
   (`consolidate_intersection_summary.build_workbook`, `consolidate_ramp_summary.build_workbook`,
   `consolidate_tsn_highway_sequence._write_workbook`) and the four `tsn_load_*` normalized-workbook
   builders are wrapped too — every persistent/reused consolidated artifact now writes atomically.
5. **F9 — matrix comparison save sites wrapped.** `consolidate_and_compare_tsn` (vs-TSN),
   `build_comparison` (the self PDF-vs-Excel mode), and `build_cell_comparison` (cross-env) hand the
   comparator a temp path via `commit_workbook` (single-mode) and finalize; `_try_formulas` routes
   the live-formulas sibling through `commit_workbook` too. compare_core is never modified.
6. **F9 — Compare-tab `mode="both"` wrapped.** `gui_api._launch_compare` (the single chokepoint for
   both Compare-tab calls) now wraps the comparator in `commit_workbook(out, …, twin=(mode==
   "both"))`; the two `run_fn` closures take the output path as a parameter. The OS save dialog
   already confirmed the destination, so the inner confirm is a pass-through. This is the only
   `mode="both"` caller — it gives the values-canonical/formulas-best-effort twin policy a real
   production home.
7. **F5 — identity-based freshness.** `matrix._consolidated_stale` is now
   `not artifact_store.consolidated_fresh(...)` (fingerprint, not newest-mtime) — a deleted route
   no longer reads fresh. `_consolidate_store_folder` records the fingerprint sidecar after a
   successful build. The per-cell comparison freshness gains an `input_fingerprint`: `record_result`
   / `record_tsn_result` / `day_matrix.record_result` store the cell's TSMIS source-folder identity
   at build time, and `_cmp_state` / `comparison_state` read the cell STALE ("inputs_changed") when
   it differs (a legacy record with no fingerprint never reads falsely stale).
8. **F5 — by-day "consolidated" indicator.** `day_matrix.day_matrix_snapshot` fixes the
   `all(... if s["exists"])` gap: a day with one report consolidated and another
   exported-but-not-consolidated now reads `day_consolidated.fresh == False`.
9. **One cache rebuild (R1-R15 / RR3-C3).** `cache_envelope.SCHEMA_VERSION` 1→2 (the single
   released v0.18 value carrying the P1 fields + the P2 per-cell fingerprints); an optional
   envelope-level `input_fingerprint` slot is added for a future single-output cache. The matrix /
   by-day caches carry per-cell fingerprints (the right granularity for a multi-cell cache).
10. **F6 packaging.** `app.spec` `APP_MODULES += "artifact_store"`.

## 4. Files affected
**New (3):** `scripts/artifact_store.py`; `build/check_artifact_store.py`; `build/check_p2_freshness.py`.
**Modified product (16):** `scripts/cache_envelope.py`, `scripts/matrix.py`, `scripts/day_matrix.py`,
`scripts/gui_worker.py`, `scripts/gui_api.py`, `scripts/updater.py`, `scripts/consolidate_xlsx_base.py`,
`scripts/consolidate_intersection_summary.py`, `scripts/consolidate_ramp_summary.py`,
`scripts/consolidate_tsn_highway_sequence.py`, `scripts/tsn_load_intersection_detail.py`,
`scripts/tsn_load_intersection_summary.py`, `scripts/tsn_load_ramp_detail.py`,
`scripts/tsn_load_ramp_summary.py`, `build/app.spec`, `.github/workflows/checks.yml`.
**Modified tests (2):** `build/check_consolidate_outcome.py` (the two stub comparators now write a
VALID workbook — the new commit validation correctly rejects a text stub); `build/check_tsn_outcome.py`
(a record stub gains the additive `input_fingerprint` kwarg). No assertion was weakened.
**Untouched:** `compare_core.py` (regression-locked), the updater TLS path, `scripts/ui/*` (no UI
changes), `scripts/tsmis_auth.json`.

## 5. Architectural decisions
- **Wrap at the caller, not inside `compare_core`.** The wrapper hands the comparator a temp path
  and finalizes — the regression-locked engine is never edited (§C.2). Temp names are rewritten out
  of the result so the user never sees one.
- **Atomic write at the producer for consolidators (base + standalone + TSN loaders), at the caller
  for comparisons.** One change in `consolidate_xlsx` covers most consolidators; the comparators
  can't be edited so they're wrapped where the matrix/Compare-tab call them. No double-wrapping.
- **Fingerprint over the multi-file TSMIS source folder(s); FILE sides (TSN/baseline workbook) stay
  mtime-tracked.** The deleted-route gap only exists for the multi-file side; a file side is replaced
  wholesale (mtime changes). Build-time and read-time fingerprint the same folders in the same order.
- **Fingerprint is a STRICT tightening** of staleness (added as an `elif` after the existing
  mtime/missing checks; only fires when a TRUSTED record carries a recorded fingerprint), so it can
  never make a stale cell read fresh and a pre-P2 record never reads falsely stale.
- **Journal in the destination parent; the shared `.promote` dir is left for recovery to rmdir.**
  Sibling stores under one parent share `.promote`; rmdir'ing it mid-promotion would race a
  concurrent journal write, so `promote_store` removes only the journal FILE + backup.
- **Schema bump to 2 = the single released value** (RR3-C3): P1's v1 was branch-only, so users see
  exactly one rebuild from their unversioned v0.17 caches.

## 6. Compatibility and migration handling
- **Consolidated workbooks:** a legacy workbook with no `.fingerprint.json` reads stale ONCE,
  rebuilds, and records the sidecar — a one-time, deterministic, safe rebuild.
- **Matrix / by-day caches:** `SCHEMA_VERSION` 1→2 ⇒ pre-v2 caches read empty ⇒ one forward rebuild
  that records per-cell fingerprints (old files are left in place until a successful recompute).
- **Promotion residue from a crash** is repaired idempotently on the next launch.
- **Backwards compatibility:** every new field is additive; absent on a legacy record ⇒ the prior
  (mtime-only) behavior. `_swap_store_dir` keeps its name + signature (callers/tests unchanged).
  No persisted format requires a downgrade path beyond the documented one rebuild.

## 7. Tests and commands run (build venv, offline)
- `python -m compileall -q scripts build version.py` — green.
- `node --check scripts/ui/app.js`; `node build/check_mx_partial_render.js` — green.
- `git diff --check` — clean (only benign LF→CRLF normalization notes).
- YAML: `checks.yml` parses (pyyaml in a throwaway target).
- **New `build/check_artifact_store.py` (67 checks)** — CT-8 (atomic_save preserves prior on a failed
  replace; no temp leak), CT-8 single commit (validate + path-rewrite + preserve-on-failure +
  confirm), CT-8b twin (values-canonical, 1st/2nd-save-failure, no temp leak), fingerprint identity,
  `consolidated_fresh` (deleted route ⇒ stale), CT-5 promote validation + locked-live, CT-4 recovery
  (restore-from-backup / clean-residue / orphan sweep / idempotent / corrupt-journal).
- **New `build/check_p2_freshness.py` (15 checks)** — CT-6a (`_consolidated_stale` beats
  newest-mtime), CT-6b (`_cmp_state` inputs_changed + legacy no-false-stale), CT-6c
  (`comparison_state` cross-env), CT-7 (day-level missing-consolidation ⇒ not fresh).
- **Full offline suite: 56 Python golden checks + the Node renderer — all green** (54 prior + the 2
  new), incl. `check_import_direction` (the new `artifact_store` imports satisfy the guard),
  `check_app_modules` (APP_MODULES += artifact_store), and every `check_compare_*` canary (compare
  output unchanged — compare_core untouched + `os.replace` is bit-preserving).

## 8. Results
All green (see §7). Each new test was proven **red on pre-fix code** via revert/run/restore:
| Fix reverted | Test that failed |
|---|---|
| `_consolidated_stale` → old newest-mtime | CT-6a "deleted route ⇒ stale" |
| `_inputs_changed` → disabled | CT-6b/CT-6c "inputs_changed" (4 checks) |
| day-level `all(... if exists)` | CT-7 "missing consolidation ⇒ not fresh" |
| `atomic_save` → direct save | CT-8 "failed replace raises / prior preserved" |
| `_commit_one` → skip validate | CT-8 "invalid workbook ⇒ error / prior preserved" (4 checks) |
| `recover_promotions` → no-op | CT-4 "live restored / residue cleaned" (9 checks) |
| `_staging_nonempty` → always True | CT-5 "empty staging not promoted" (4 checks) |

## 9. Before/after measurements
- Offline golden checks: **54 → 56** Python (+`check_artifact_store`, +`check_p2_freshness`) + the
  Node renderer; **+82** individual assertions (67 + 15).
- `APP_MODULES`: 55 → 56 (artifact_store).
- `cache_envelope.SCHEMA_VERSION`: 1 → 2.
- Freshness signal for the persistent consolidated: newest-mtime → input fingerprint (identity).
- Store swap: best-effort rmtree+merge → journaled rename + startup recovery.
- Comparison/consolidator writes: direct-to-final → temp + validate + `os.replace`.
- `matrix.py`: +167/−… (the freshness + commit-wrap surface). No `compare_core` lines changed.

## 10. Deviations from the approved plan
- **None material.** The plan's "Affected" line is fully covered. Two scope clarifications:
  - The fingerprint freshness is applied to the consolidated (`_consolidated_stale`, the F5 line-range
    locus) **and** per-cell (TSN/self/env) so a deleted route reads the matrix CELL stale, not just
    the consolidated — both are required for CT-6 end-to-end. It is NOT threaded through
    `report_library.cell_ages` (kept off the hot read path); the per-cell records carry the
    fingerprint instead.
  - The `tsn_load_*` normalized-workbook builders + the standalone summary consolidators were wrapped
    with `atomic_save` (beyond the single base `consolidate_xlsx`) so the F9 fix is uniform across
    every persistent consolidated writer — consistent with "consolidator save sites wrapped".

## 11. Known limitations and external verification
- **Work-PC live verification owed (not DoD):** a real Defender/lock interruption mid-promotion with
  recovery on the next real launch, and the one-time consolidated/cache rebuild on a real upgrade
  (§20 / R1-N04 — no disk-full induction; safe lock/Defender with disposable destinations only).
- **TSN consolidated (district-PDF) freshness vs its raw PDFs** is governed by `tsn_library`, not the
  matrix `_consolidated_stale` F5 locus, so it is NOT fingerprinted in P2 (its write IS atomic via
  the base consolidator). Out of F5's documented scope.
- Validation is "openable + has a workbook part" (cheap), not a full openpyxl load — sufficient to
  reject a truncated/garbage write without paying a full re-parse of a large formulas workbook.

## 12. Exact diff scope for Codex to review
- **`scripts/artifact_store.py`** (NEW) — the whole module: `atomic_save`, `commit_workbook`
  (+ `_commit_one`, `_rewrite_paths`, `_is_valid_xlsx`, `_values_twin`), `fingerprint` /
  `write_consolidated_fingerprint` / `consolidated_fresh`, `promote_store` / `recover_promotions`
  (+ `_recover_one`, `_staging_nonempty`).
- **`scripts/matrix.py`** — `_consolidated_stale` (fingerprint), `_consolidate_store_folder`
  (fingerprint sidecar write), the three comparison save sites wrapped in `commit_workbook`,
  `_try_formulas` (atomic), `_cell_input_fingerprint` / `_inputs_changed`, `_cmp_state` /
  `comparison_state` (the `fp_folders` / inputs_changed staleness + `rec_trusted`), the snapshot's
  `fp_folders=` args, `record_result` / `record_tsn_result` (+ `input_fingerprint`), the
  `dest = Path(dest)` guards.
- **`scripts/day_matrix.py`** — the `all()` day-level fix, `_cmp_state(fp_folders=(tdir,))`,
  `record_result(+input_fingerprint)`, `build_day_cell` fingerprint.
- **`scripts/cache_envelope.py`** — schema bump + the `input_fingerprint` slot.
- **`scripts/gui_worker.py`** — `_swap_store_dir` delegation.
- **`scripts/updater.py`** — `_recover_store_promotions` + the `cleanup_leftovers` call.
- **`scripts/gui_api.py`** — `_launch_compare` twin wrap + the two `run_fn` signatures.
- **The 7 consolidator/`tsn_load_*` save sites** — one-line `wb.save → atomic_save` each + the import.
- **`build/app.spec`** — APP_MODULES.
- **`.github/workflows/checks.yml`** — the new blocking step.
- **`build/check_artifact_store.py`, `build/check_p2_freshness.py`** (NEW) — the CT-4/5/6/7/8/8b
  coverage; **`build/check_consolidate_outcome.py`, `build/check_tsn_outcome.py`** — the minimal stub
  updates (valid workbook / additive kwarg) the new contract requires.

---

## Remediation — Codex review round 1 (`BLOCKED`)

### Review round addressed
Codex P2 **review round 1** — verdict `BLOCKED`: 5 blocking (P2-B01..B05), 3 required
(P2-R01..R03), 2 non-blocking recommendations (P2-A01, P2-A02). All 5+3 verified against the
workspace as REAL and fixed; both recommendations applied (they fit the phase without scope
expansion).

### Finding dispositions
| ID | Severity | Disposition | Resolution |
|---|---|---|---|
| **P2-B01** — a failed store promotion is reported as `promoted` | blocking | **Fixed** | `_run_specs` was discarding the `promote_store` bool and deriving `artifact` from completion alone. It now CAPTURES the bool: a complete export whose journaled swap returns False ⇒ `artifact=previous_preserved` (last-good kept), so the B2 auto-consolidate gate (already keyed on `artifact==PROMOTED`) is suppressed. `BatchWorker.run` env-done gate changed from `promotable(completion)` to `getattr(r, "artifact", None) == PROMOTED`, so a complete-but-failed promotion leaves the env PENDING (resumable). |
| **P2-B02** — failed rollback/recovery deletes the journal needed for retry | blocking | **Fixed** | `promote_store`: when `staged.rename(live)` AND the `backup.rename(live)` restore BOTH fail, the journal + backup are now RETAINED (the journal is deleted only after a restore succeeds). `_recover_one`: a blocked `backup.rename(target)` now RETURNS, retaining the journal + backup (was: deleted regardless). A last-resort "promote the surviving staging" branch covers the (target + backup both gone, staging present) case. |
| **P2-B03** — startup recovery skips the configured Export-Everything destination | blocking | **Fixed** | `updater._recover_store_promotions` now sweeps BOTH `OUTPUT_ROOT` AND `settings.get_batch_dest()`, deduplicated by resolved path, each isolated in its own try/except so one failure never blocks the other or startup. |
| **P2-B04** — journal path traversal permits deletion outside the store | blocking | **Fixed** | New `_trusted_journal_names`: every name must be a single basename (no separators / `..` / absolute) and `backup`/`staging` must be exactly `<target>.bak-<token>` / `<target>.staging`; an untrusted record is dropped touching NO path. The orphan sweep now removes only DIRECTORIES whose stripped live DIR exists (never a user file named `*.bak-*`). |
| **P2-B05** — validation accepts an unreadable XLSX-shaped ZIP | blocking | **Fixed** | `_is_valid_xlsx` (ZIP-namelist only) replaced by `_openable_xlsx`, which `openpyxl.load_workbook(read_only=True)`-OPENS the file (rejecting a corrupt ZIP or a malformed `xl/workbook.xml`) AND checks `expect_sheet` is present. The matrix/Compare-tab comparison commits pass `expect_sheet="Comparison"`. A failed validation keeps the prior destination. |
| **P2-R01** — directory-only staging accepted | required | **Fixed** | `_staging_nonempty` → `_staging_has_report_file`: requires >=1 eligible regular FILE (excludes locks / temp / sidecars / sub-directories). |
| **P2-R02** — error results can expose deleted temp paths | required | **Fixed** | `_rewrite_paths` now sanitizes `message` too; `commit_workbook` rewrites EVERY returned result (ok / error / cancelled); the rewrite map carries BOTH the full temp path AND its basename (compare_core's save-error message names only `path.name`). |
| **P2-R03** — best-effort formulas failure returns a success pointing to a missing file | required | **Fixed** | On a twin formulas-commit failure, `commit_workbook` now points `output_path` at the committed VALUES workbook and turns the "Live-formulas file:" line into a "NOT refreshed (best-effort …)" warning. |
| **P2-A01** — stale comments/claims | recommended | **Fixed** | `matrix.consolidated_state` + `consolidate_and_compare_tsn` docstrings updated from "newest-mtime / newer than every source" to the fingerprint-identity contract; this remediation corrects the report's earlier "openable" characterization (the validator now genuinely opens + checks the sheet). |
| **P2-A02** — fingerprint not guarded against a mid-build input change | recommended | **Fixed (applied)** | `write_consolidated_fingerprint(consolidated, store_dir, built_from=…)`: `_consolidate_store_folder` captures the input fingerprint BEFORE the build and passes it; if it differs from the post-build fingerprint the sidecar is NOT written (the workbook reads stale → rebuilds), so a build that raced an input change is never stamped fresh. Characterization: the GUI task lock already serializes all writers, so before==after in normal operation; this guards an external mid-build mutation. |

### Remediation changes
- **`scripts/artifact_store.py`** — `_openable_xlsx` (replaces `_is_valid_xlsx`); `commit_workbook`
  gains `expect_sheet`, sanitizes every returned result (full-path + basename map), and returns a
  truthful values-canonical result on a formulas-commit failure; `_rewrite_paths` sanitizes
  `message`; `_staging_has_report_file` (replaces `_staging_nonempty`); `promote_store` retains the
  journal/backup on a failed restore; `_trusted_journal_names` + a rewritten `_recover_one`
  (validate-or-touch-nothing, retain-on-blocked-restore, surviving-staging last resort); the orphan
  sweep restricted to directories; `write_consolidated_fingerprint` gains the `built_from` guard.
- **`scripts/gui_worker.py`** — `_run_specs` captures the promotion bool → `previous_preserved` on
  failure; `BatchWorker.run` env-done gate keys off `artifact == PROMOTED`.
- **`scripts/updater.py`** — `_recover_store_promotions` sweeps `OUTPUT_ROOT` + `get_batch_dest()`
  (deduped, isolated).
- **`scripts/matrix.py`** — the four comparison commits + `_try_formulas` pass
  `expect_sheet="Comparison"`; `_consolidate_store_folder` captures + passes the pre-build
  fingerprint; the two stale docstrings corrected.
- **`scripts/gui_api.py`** — the Compare-tab `commit_workbook` passes `expect_sheet="Comparison"`.
- **Tests:** `check_artifact_store.py` grew **67 → 106** assertions — new P2-B02/B04/B05/R01/R02/R03 +
  A02 cases and the B03 updater-wiring test; `check_batch_outcome.py` — the `_swap_store_dir` stub
  now RETURNS the boolean (Codex's "stub returns None masks the contract"), a NEW P2-B01 failed-
  promotion case (artifact=previous_preserved, no auto-consolidate, env NOT done), and the two-env /
  `_run_batch` stubs stamp `artifact` like the real `_run_specs`; `check_worker_lifecycle.py` — the
  batch "success" producer stub sets `artifact=PROMOTED`; `check_consolidate_outcome.py` — the stub
  comparators emit a `"Comparison"` sheet for the new sheet contract.

### Updated verification
Every blocking + required fix was proven RED on pre-fix code via revert/run/restore:

| Fix reverted | Failing test |
|---|---|
| promotion bool discarded | check_batch_outcome P2-B01 (artifact=promoted + auto-consolidate ran) |
| env-done gate → completion-only | check_batch_outcome (complete-but-failed-promotion marked done) |
| restore-failure deletes journal (both sites) | check_artifact_store P2-B02 (no retry; recovery can't restore) |
| `recover_promotions(OUTPUT_ROOT)` only | check_artifact_store P2-B03 (custom dest not swept) |
| journal validation skipped | check_artifact_store P2-B04 (out-of-store victim deleted via `../`) |
| validation → name-only | check_artifact_store P2-B05 (malformed workbook committed over prior) |
| `any(iterdir())` staging | check_artifact_store P2-R01 (directory-only staging promoted) |
| message not sanitized | check_artifact_store P2-R02 (`.tmp-` leaked in the error message) |
| untruthful formulas result | check_artifact_store P2-R03 (output_path → missing formulas file) |
| `built_from` guard removed | check_artifact_store P2-A02 (raced build stamped fresh) |

- **Full offline suite: 56 Python golden checks + the Node renderer — all green**, incl.
  `check_import_direction`, `check_app_modules`, every `check_compare_*` canary (compare output
  unchanged), byte-compile, `node --check app.js`, and `git diff --check` clean. No `REVERT-PROOF`
  marker remains in product or test code. `compare_core` / updater-TLS / auth / UI untouched.

### Changed measurements
- `check_artifact_store.py`: **67 → 106** assertions (+39).
- `check_batch_outcome.py`: **24 → 29** assertions (+5; the P2-B01 failed-promotion cases).
- Offline suite count unchanged at **56** Python checks + the Node renderer (no new check files this
  round; all new coverage landed in existing P2 checks).
- New artifact_store internals: `_is_valid_xlsx`→`_openable_xlsx` (now opens via openpyxl),
  `_staging_nonempty`→`_staging_has_report_file`, `_trusted_journal_names` added,
  `write_consolidated_fingerprint` gains `built_from`.

---

## Remediation — Codex review round 2 (`BLOCKED`)

### Review round addressed
Codex P2 **review round 2** — verdict `BLOCKED`. Round 1's fixes were confirmed resolved
(P2-B01, P2-B03, P2-B05, P2-R02, P2-R03). Round 2 raised 3 blocking (P2-B02 re-opened,
P2-B04 re-opened, P2-B06 new), 2 required (P2-R01 re-opened, P2-R04 new), and 3 non-blocking
recommendations (P2-A01, P2-A02, P2-A03). All 3+2 verified against the workspace as REAL and
fixed; all three recommendations applied.

### Finding dispositions
| ID | Severity | Disposition | Resolution |
|---|---|---|---|
| **P2-B02** — recovery discards the valid backup when an invalid placeholder sits at `live` | blocking | **Fixed** | `_recover_one` no longer treats `target.exists()` as proof of a canonical store. It now requires `_is_usable_store(target)` (a directory holding a report artifact). When `target` is absent or an invalid placeholder it restores from a valid backup (then a valid surviving staging); an EMPTY/disposable placeholder is displaced first, but a placeholder with FOREIGN content is a conflict that RETAINS the journal + copies and logs. The journal is removed only after a proven restore. |
| **P2-B04** — the journal-free orphan sweep deletes unrelated user directories | blocking | **Fixed** | The journal-free `_sweep_orphans` (deleted any `*.bak-*` / `*.staging` dir beside a same-prefix live) is REMOVED entirely. `recover_promotions` now acts ONLY on paths a trust-validated journal names; an unowned `*.bak-*` / `*.staging` directory under a user-chosen destination is left untouched (harmless residue ≫ deleting a guessed backup). A leftover `.staging` is reclaimed by the worker's own pre-export rmtree. |
| **P2-B06** — a failed first-ever promotion deletes the only completed copy | blocking | **Fixed** | `promote_store` now JOURNALS the first promotion too (no prior `live`): on a rename failure it RETAINS the staging + journal so `recover_promotions` promotes the surviving staging next launch — the only completed copy is never deleted. If the journal itself can't be written, the first promotion still attempts a direct rename and retains the staging on failure (a re-export recovers it). `_run_specs` makes the artifact truthful: a failed swap with NO prior reads `none` (not `previous_preserved`), via a pre-swap `had_prior` capture. |
| **P2-R01** — staging validation accepts an arbitrary regular file | required | **Fixed** | `_is_report_artifact` requires a non-excluded name ending in a report suffix (`.xlsx` / `.pdf`); `_staging_has_report_file` uses it, so a `.txt`-only (or sidecar/lock-only) staging is never promoted over a good live store. |
| **P2-R04** — rejected malformed workbook can leave a locked temp | required | **Fixed** | `_openable_xlsx` opens the workbook on a `with open(p, "rb") as fh:` caller-owned handle passed to `openpyxl.load_workbook(fh, …)`, so the OS handle is released on ANY exit (including when `load_workbook` raises on a malformed worksheet) and the temp is removable; `_commit_one` now verifies the rejected temp is actually gone and logs if not. |
| **P2-A01** — stale module/report documentation | recommended | **Fixed** | `artifact_store` module docstring now states openpyxl is a LAZY runtime import (in `_openable_xlsx`); `matrix.consolidate_and_compare_tsn` "byte-identical" → "semantically identical"; this remediation supersedes the original report's "cheap stdlib ZIP / openable" validator description. |
| **P2-A02** — the race guard leaves a stale sidecar certifying the replaced workbook | recommended | **Fixed (applied)** | `write_consolidated_fingerprint`, on a `built_from` mismatch (a build that raced an input change), now durably `_silent_unlink`s the existing sidecar before returning False — so even if the inputs reverted to the old identity, `consolidated_fresh` reads stale and the workbook rebuilds (never a false-fresh after the producer already replaced it). |
| **P2-A03** — silent optional-formulas commit failure | recommended | **Fixed (applied)** | `matrix._try_formulas` now inspects `commit_workbook`'s returned `ConsolidateResult` and logs a non-`ok` status (a validation/finalization failure returns `status="error"` rather than raising), so a not-refreshed best-effort formulas copy is no longer silent. |

### Remediation changes
- **`scripts/artifact_store.py`** — `_is_report_artifact` + report-suffix `_staging_has_report_file`
  (R01); `_is_usable_store` + `_dir_is_disposable_placeholder` helpers; `promote_store` journals the
  first promotion + retains staging/journal on a first-promotion failure (B06); `_recover_one`
  validates `target` is a usable store before deleting any copy, restores from backup-then-staging,
  displaces only an empty/disposable placeholder, retains on conflict/blocked (B02); the journal-free
  orphan sweep removed from `recover_promotions` (B04); `_openable_xlsx` opens via a `with`-managed
  file handle (R04); `_commit_one` verifies the rejected temp is gone (R04);
  `write_consolidated_fingerprint` removes the stale sidecar on a race (A02); module docstring (A01).
- **`scripts/gui_worker.py`** — `_run_specs` captures `had_prior` and maps a failed first promotion
  to `artifact=none`, not `previous_preserved` (B06).
- **`scripts/matrix.py`** — `_try_formulas` logs a non-`ok` commit result (A03);
  `consolidate_and_compare_tsn` docstring "byte-identical" → "semantically identical" (A01).
- **Tests:** `check_artifact_store.py` grew **106 → 129** assertions — new P2-B02 (invalid/empty/
  foreign placeholder), P2-B04 (unrelated orphan survives), P2-B06 (first-promotion failure +
  next-launch recovery), P2-R01 (wrong-extension staging), P2-R04 (malformed-worksheet rejection +
  no locked temp), P2-A02 (exact-identity reversion removes the stale sidecar); `test_recovery`
  State C updated to assert orphans now SURVIVE (B04-safe). `check_batch_outcome.py` (29 → **30**) —
  `_run_instore` gains a `had_prior` knob; a NEW assertion that a failed FIRST promotion reads
  `artifact=none`.

### Updated verification
Every blocking + required round-2 fix was proven RED on pre-fix code via revert/run/restore:

| Fix reverted | Failing test |
|---|---|
| recovery `target.exists()` (not usable-store) | check_artifact_store P2-B02 (empty placeholder kept; valid backup deleted) |
| journal-free orphan sweep re-added | check_artifact_store P2-B04 (unrelated `*.bak-*` dir deleted) |
| first promotion unjournaled + rmtree-on-fail | check_artifact_store P2-B06 (staging deleted, no journal, no recovery) |
| `_run_specs` always `previous_preserved` | check_batch_outcome P2-B06 (failed first promotion not `none`) |
| `_is_report_artifact` accepts any file | check_artifact_store P2-R01 (`.txt`-only staging promoted) |
| `_openable_xlsx` path-based load | check_artifact_store P2-R04 (locked temp residue remained) |
| sidecar not removed on race | check_artifact_store P2-A02 (stale sidecar still certified fresh) |

- **Full offline suite: 56 Python golden checks + the Node renderer — all green**, incl.
  `check_import_direction`, `check_app_modules`, every `check_compare_*` canary, byte-compile,
  `node --check app.js`, and `git diff --check` clean. No `REVERT-PROOF` marker remains in product
  or test code. `compare_core` / updater-TLS / auth / UI untouched.

### Changed measurements
- `check_artifact_store.py`: **106 → 129** assertions (+23).
- `check_batch_outcome.py`: **29 → 30** assertions (+1; the failed-first-promotion `none` case).
- Offline suite count unchanged at **56** Python checks + the Node renderer (no new check files this
  round; all new coverage landed in existing P2 checks).
- New / changed artifact_store internals: `_is_report_artifact`, `_is_usable_store`,
  `_dir_is_disposable_placeholder` added; the journal-free orphan sweep removed;
  `_openable_xlsx` opens on a caller-owned handle; `write_consolidated_fingerprint` invalidates a
  stale sidecar on a race; `_run_specs` adds the `had_prior`/`none` truthful-artifact mapping.

---

## Remediation — Codex review round 3 (`BLOCKED`)

### Review round addressed
Codex P2 **review round 3** — verdict `BLOCKED`. Round 2's fixes were confirmed resolved
(P2-B02, P2-B06, P2-R01, P2-R04, P2-A03). Round 3 left 1 blocking (P2-B04, narrowed to ownership),
1 required (P2-R05, new), and 3 recommendations (P2-A02 follow-up, P2-A04 new, P2-A01 cleanup). All
1+1 blocking/required verified REAL and fixed; all three recommendations applied.

### Finding dispositions
| ID | Severity | Disposition | Resolution |
|---|---|---|---|
| **P2-B04** — shape validation does not establish app ownership | blocking | **Fixed** | `recover_promotions(root, is_owned)` now takes a caller-supplied ownership predicate; `_recover_one` acts on a shape-valid journal ONLY when `is_owned(store_root, target)` is True. The updater builds it from the known `<src>-<env>` store roots (`common.DATA_SOURCES`×`ENVIRONMENTS`) + export report subdirs (`reports.EXPORT_REPORTS`). A planted/unrelated but shape-valid `.promote` tree under a user destination is left entirely untouched. |
| **P2-R05** — cleanup failure discards the only retry record | required | **Fixed** | `_recover_one` now removes the journal ONLY after every journal-owned residue is CONFIRMED gone, via a new `_rmtree_gone(path)->bool` (rmtree + verify absent). A backup/staging that can't be removed (locked) RETAINS the journal so the next launch retries — applied to both the usable-target-cleanup and the post-restore paths. |
| **P2-A02** — sidecar invalidation failure can still produce false freshness | recommended | **Fixed (applied)** | `write_consolidated_fingerprint`, on a race, removes the stale sidecar; if removal FAILS it overwrites the sidecar with a guaranteed-non-matching sentinel (`_write_fp_sentinel` → fingerprint `__race_invalidated__`, which `fingerprint()` can never produce) so `consolidated_fresh` still reads stale; the ACTUAL outcome (removed / sentinel / neither) is logged, not an unconditional claim. |
| **P2-A04** — failure disposition used path existence, not usable-artifact existence | recommended | **Fixed (applied)** | `ExportWorker._run_specs` now derives `had_prior` from `artifact_store.is_usable_store(out_dir)` (the same report-artifact contract recovery uses), so a failed first promotion over an EMPTY or foreign-only pre-existing directory reads `artifact=none`, not `previous_preserved`. (`_is_usable_store` promoted to the public `is_usable_store`.) |
| **P2-A01** — duplicated P2-A02 comment | recommended | **Fixed** | The duplicated comment block in `write_consolidated_fingerprint` is removed (the function now carries a single accurate comment). |

### Remediation changes
- **`scripts/artifact_store.py`** — `recover_promotions(root, is_owned)` + `_recover_one(jdir, journal, is_owned)`
  add the ownership gate (B04); `_rmtree_gone` + `_drop_residue_then_journal` make cleanup observable
  and retain the journal on incomplete cleanup (R05); `_write_fp_sentinel` + the race branch overwrite
  an un-removable sidecar with a non-matching sentinel and log the real outcome (A02); `_is_usable_store`
  → public `is_usable_store` (A04); the duplicated comment removed (A01).
- **`scripts/updater.py`** — `_recover_store_promotions` builds the ownership predicate from
  `common.DATA_SOURCES`×`ENVIRONMENTS` (store roots) + `reports.EXPORT_REPORTS` subdirs (targets) and
  passes it to `recover_promotions` for each root (lazy imports; no module-level cycle).
- **`scripts/gui_worker.py`** — `_run_specs` `had_prior` uses `artifact_store.is_usable_store` (A04).
- **Tests:** `check_artifact_store.py` grew **129 → 143** assertions — `_OWN_ALL` predicate threaded
  through the mechanics call sites; new P2-B04 unowned-journal (the round-3 repro + an owned control),
  P2-R05 (cleanup-failure-after-completed-promotion + after-restore, with a later retry), and P2-A02
  un-removable-sidecar (sentinel) cases. `check_batch_outcome.py` (30 → **31**) — `_run_instore` gains
  `prior_empty`; a NEW P2-A04 assertion that a failed promotion over an empty prior dir reads `none`.

### Updated verification
Every blocking + required round-3 fix was proven RED on pre-fix code via revert/run/restore:

| Fix reverted | Failing test |
|---|---|
| ownership gate skipped | check_artifact_store P2-B04 (unowned backup/staging deleted, journal dropped) |
| journal dropped without observing cleanup | check_artifact_store P2-R05 (locked backup never retried) |
| race ignores unlink failure (no sentinel) | check_artifact_store P2-A02 (un-removable sidecar still reads fresh) |
| `had_prior` = `out_dir.exists()` | check_batch_outcome P2-A04 (empty prior dir -> previous_preserved) |

- **Full offline suite: 56 Python golden checks + the Node renderer — all green**, incl.
  `check_import_direction` (the lazy `common`/`reports` imports in updater keep the graph acyclic),
  `check_app_modules`, every `check_compare_*` canary, byte-compile, `node --check app.js`, and
  `git diff --check` clean. No `REVERT-PROOF` marker remains. `compare_core` / updater-TLS / auth / UI
  untouched.

### Changed measurements
- `check_artifact_store.py`: **129 → 143** assertions (+14).
- `check_batch_outcome.py`: **30 → 31** assertions (+1; the empty-prior-dir `none` case).
- Offline suite count unchanged at **56** Python checks + the Node renderer (no new check files).
- API change: `recover_promotions(root)` → `recover_promotions(root, is_owned)` (the ownership
  predicate is now REQUIRED — there is no unsafe accept-all default in production). New artifact_store
  internals: `_rmtree_gone`, `_write_fp_sentinel`, `_FP_RACE_SENTINEL`; `_is_usable_store` →
  public `is_usable_store`.

---

## Remediation — Codex review round 4 (`BLOCKED`)

### Review round addressed
Codex P2 **review round 4** — verdict `BLOCKED`. Round 3's fixes were confirmed resolved
(P2-B01/B02/B03/B05/B06, P2-R01..R04, P2-A01/A03/A04). Round 4 left 1 blocking (P2-B04 — ownership
still basename-based, not location-based), 1 required (P2-R05 — the normal `promote_store` path still
drops the journal before confirming residue cleanup), and 1 recommendation (P2-A02 — the dual
sidecar-op failure still permits false-fresh). All 1+1 blocking/required verified REAL and fixed; the
recommendation applied.

### Finding dispositions
| ID | Severity | Disposition | Resolution |
|---|---|---|---|
| **P2-B04** — nested app-like names bypass the ownership gate | blocking | **Fixed** | Ownership is now LOCATION-based and established BEFORE any journal is read or deleted. `recover_promotions` calls a LOCATION gate `is_owned(store_root, None)` for each discovered `.promote` and SKIPS the whole directory (no journal read, no malformed-journal delete) when it fails. The updater's predicate requires `store_root.parent.resolve() == <this recovery root>.resolve()` (a DIRECT child) AND a known `<src>-<env>` name; a journal's TARGET is validated only afterward. So `<root>/UnrelatedProject/ssor-prod/.promote` (valid name, wrong location) and a nested malformed journal are both left untouched. |
| **P2-R05** — the normal promotion path loses its cleanup retry record | required | **Fixed** | A shared `_finalize_journal(journal, *residue)` removes the journal ONLY after every named residue is confirmed gone (`_rmtree_gone`). `promote_store` now uses it on BOTH completion branches: after a successful promotion (residue = backup) and after a successful inline restore (residue = staging). A locked backup/staging RETAINS the journal so the next launch's recovery retries the cleanup. `_recover_one` shares the same helper. |
| **P2-A02** — dual sidecar-op failure still permits false freshness | recommended | **Fixed (applied)** | The race fail-safe ladder gains a final rung: when the stale sidecar can be NEITHER removed NOR overwritten with a non-matching sentinel, `_quarantine_workbook` renames the freshly-replaced (race-suspect) workbook aside, so the canonical path resolves MISSING and `consolidated_fresh` reads stale (a clean rebuild). Only an all-locked floor logs `critical`. |

### Remediation changes
- **`scripts/artifact_store.py`** — `recover_promotions` adds the per-`.promote` LOCATION gate
  `is_owned(store_root, None)` before reading/deleting (B04); `_finalize_journal(journal, *residue)`
  (observable cleanup-before-journal, shared by `promote_store` + `_recover_one`); `promote_store`
  uses it on the promotion-success and inline-restore branches (R05); `_quarantine_workbook` + the
  extended race ladder in `write_consolidated_fingerprint` (A02). `_recover_one`'s docstring notes the
  caller proves location ownership first.
- **`scripts/updater.py`** — `_recover_store_promotions` builds the ownership predicate per recovery
  root via `_owned_for(root)`: it requires the store root to be a DIRECT child of that exact root
  (`store_root.parent.resolve() == root.resolve()`) + a known `<src>-<env>` name, and (with a target)
  a known export subdir; `target=None` is the location-only gate.
- **Tests:** `check_artifact_store.py` grew **143 → 156** assertions — `test_b04_unowned_journal`
  rewritten for the round-4 nested valid-NAME-wrong-LOCATION repro + a nested malformed-journal case +
  an owned direct-child control (with the exact-root predicate); new `test_r05_promote_cleanup`
  (locked backup after a successful promotion → journal retained + later-sweep cleanup; locked staging
  after an inline restore → journal retained); new `test_a02_dual_failure_quarantine` (both sidecar
  ops fail → workbook quarantined → reads stale).

### Updated verification
Every blocking + required round-4 fix was proven RED on pre-fix code via revert/run/restore:

| Fix reverted | Failing test |
|---|---|
| location gate skipped in `recover_promotions` | check_artifact_store P2-B04 (nested malformed journal deleted) |
| `promote_store` drops the journal before confirming cleanup | check_artifact_store P2-R05 (locked backup → journal lost, never retried) |
| A02 quarantine rung disabled | check_artifact_store P2-A02 (dual-failure → workbook still reads fresh) |

- **Full offline suite: 56 Python golden checks + the Node renderer — all green**, incl.
  `check_import_direction`, `check_app_modules`, every `check_compare_*` canary, byte-compile,
  `node --check app.js`, and `git diff --check` clean. No `REVERT-PROOF` marker remains.
  `compare_core` / updater-TLS / auth / UI untouched.

### Changed measurements
- `check_artifact_store.py`: **143 → 156** assertions (+13).
- `check_batch_outcome.py`: unchanged at 31.
- Offline suite count unchanged at **56** Python checks + the Node renderer (no new check files).
- New artifact_store internals: `_finalize_journal`, `_quarantine_workbook`. `recover_promotions`
  ownership is now location-based (the updater predicate requires the exact-root direct-child
  relationship). The `is_owned` predicate is now called with `target=None` for the pre-read
  location gate and with a target for the per-journal check.

---

## Remediation — Codex review round 5 (`BLOCKED`)

### Review round addressed
Codex P2 **review round 5** — verdict `BLOCKED`. Round 4's fixes were confirmed resolved
(P2-B04, P2-R05 single-generation, P2-A02). Round 5 raised ONE new blocking finding (P2-B07) exposed
by the round-4 journal-retention behavior; no required findings, no new recommendations.

### Finding dispositions
| ID | Severity | Disposition | Resolution |
|---|---|---|---|
| **P2-B07** — two journals for one target can roll back past last-good | blocking | **Fixed** | Each journal now records a generation marker `seq` (`time.time_ns()`), and `recover_promotions` processes a directory's journals NEWEST-`seq`-FIRST (stable name tie-break) — independent of the filesystem listing order. So when two journals name the same target (an older one retained after a locked backup cleanup + a newer interrupted one), the NEWER generation restores/keeps the true last-good (V2) FIRST; the older journal then only becomes residue-cleanup against an already-canonical live and can never restore an older generation (V1) over it or delete the newer backup/staging. This is Codex's "generation-aware recovery" option; the observable bug (recovery ending at V1, deleting V2 and V3) is closed in both encounter orders. |

### Remediation changes
- **`scripts/artifact_store.py`** — `import time`; `promote_store`'s journal now carries
  `"seq": time.time_ns()` (the transaction generation marker); new `_journal_seq(journal)` reader
  (absent/unreadable ⇒ 0); `recover_promotions` iterates each `.promote`'s journals via
  `sorted(journals, key=lambda p: (_journal_seq(p), p.name), reverse=True)` so the newest generation
  is always processed first regardless of filesystem order. `_recover_one`, `_finalize_journal`, and
  the ownership/location gates are unchanged.
- **No other module changed.** `gui_worker`/`updater`/`matrix` etc. are untouched this round (the
  fix is entirely within the recovery ordering + the journal's generation marker).
- **Tests:** `check_artifact_store.py` grew **156 → 164** assertions — new
  `test_b07_two_journals_generation_aware` seeds the exact reachable two-generation interrupted state
  (live absent; V1 in the older journal's backup, V2 = true last-good in the newer journal's backup,
  V3 in the shared deterministic staging) and asserts recovery preserves V2, discards V1 + the
  un-promoted V3, and clears both journals — run for BOTH name orderings (older-name-first and
  newer-name-first) so the `seq` sort, not the filesystem order, is proven to drive newest-first.

### Updated verification
The B07 fix was proven RED on pre-fix code via revert/run/restore:

| Fix reverted | Failing test |
|---|---|
| recovery sorts by raw name (not `seq`) | check_artifact_store P2-B07 (older-named journal restores V1 first; V2 the true last-good is then deleted) |

- **Full offline suite: 56 Python golden checks + the Node renderer — all green**, incl.
  `check_import_direction` (the added `import time` is stdlib; no new module-graph edge),
  `check_app_modules`, every `check_compare_*` canary, byte-compile, `node --check app.js`, and
  `git diff --check` clean. No `REVERT-PROOF` marker remains. `compare_core` / updater-TLS / auth / UI
  untouched.

### Changed measurements
- `check_artifact_store.py`: **156 → 164** assertions (+8).
- Offline suite count unchanged at **56** Python checks + the Node renderer (no new check files).
- Journal schema gains an additive `seq` field (older journals with no `seq` read as generation 0 —
  harmless for a single journal; only relevant when two same-target journals coexist). New
  artifact_store internal: `_journal_seq`; `recover_promotions` now orders by generation.

---

## Remediation — Codex review round 6 (`BLOCKED`)

### Review round addressed
Codex P2 **review round 6** — verdict `BLOCKED`. Round 5's gen-aware recovery was accepted in
principle, but the generation marker was derived from `time.time_ns()` (wall-clock), which can
REGRESS across application restarts / system-clock corrections — so an older same-target journal
could carry a higher `seq` than a later one and recovery's newest-first ordering would again restore
the older generation. One blocking finding (P2-B07, re-opened); no required findings; no new
recommendations.

### Finding dispositions
| ID | Severity | Disposition | Resolution |
|---|---|---|---|
| **P2-B07** — wall-clock `seq` does not guarantee transaction-generation order | blocking | **Fixed** | The generation marker is now a DURABLE monotonic counter, not wall-clock. New `_next_generation(jdir, target)` returns `max(generation of every valid existing same-target journal) + 1` — derived from the on-disk journals under the single-writer promotion boundary, so a new promotion's `gen` is STRICTLY GREATER than every existing same-target journal's regardless of the system clock. `promote_store` stamps `"gen"` from it (the wall-clock `"seq"` is gone); `recover_promotions` orders by `_journal_gen` descending. An older retained cleanup journal can therefore never out-rank a later promotion, even after a clock rollback across restarts — closing Codex's inverted-clock reproduction (recovery ending at V1 and deleting V2 + V3). This is Codex's accepted "assign the new generation strictly greater than every valid existing same-target journal" option. |

### Remediation changes
- **`scripts/artifact_store.py`** — removed `import time`; new `_next_generation(jdir, target_name)`
  (durable `max(existing same-target gen)+1`, clock-free; first promotion = 1; ignores other
  targets + malformed journals); `promote_store` now stamps `"gen": _next_generation(...)` instead
  of `"seq": time.time_ns()`; `_journal_seq` replaced by `_journal_gen` (reads `gen`);
  `recover_promotions` sorts journals by `(_journal_gen, name)` descending. `_recover_one`, the
  ownership/location gates, `_finalize_journal`, and promotion/restore flow are otherwise unchanged.
- **No other module changed.** The fix is entirely within the journal's generation contract +
  recovery ordering.
- **Tests:** `check_artifact_store.py` grew **164 → 169** assertions —
  `test_b07_two_journals_generation_aware` updated to the durable `gen` field (older=1, newer=2),
  still in BOTH filename orders; new `test_b07_durable_generation` proves `_next_generation` is
  `max+1` (first=1, after a gen=7 journal → 8, a different target's gen=99 ignored) AND that two
  REAL same-target promotions (the first retained via a locked backup) yield strictly increasing
  generations `[1, 2]` — a small monotonic counter, never a wall-clock timestamp, so it cannot
  regress when the clock moves backward between promotions.

### Updated verification
The round-6 fix was proven RED on pre-fix code via revert/run/restore:

| Fix reverted | Failing test |
|---|---|
| `promote_store` stamps `gen = time.time_ns()` (wall-clock) | check_artifact_store P2-B07 durable-generation ("generations are strictly increasing 1,2" fails — the two real promotions record wall-clock timestamps, not the monotonic counter) |

- **Full offline suite: 56 Python golden checks + the Node renderer — all green**, incl.
  `check_import_direction`, `check_app_modules`, every `check_compare_*` canary, byte-compile,
  `node --check app.js`, and `git diff --check` clean. No `REVERT-PROOF` marker remains; no `seq` /
  `time` reference survives in `artifact_store` (only the legitimate `mtime_ns` in the fingerprint).
  `compare_core` / updater-TLS / auth / UI untouched.

### Changed measurements
- `check_artifact_store.py`: **164 → 169** assertions (+5).
- Offline suite count unchanged at **56** Python checks + the Node renderer (no new check files).
- Journal schema: the `seq` (wall-clock) field is replaced by a durable monotonic `gen` (a journal
  with no `gen` reads as generation 0 — harmless for a single journal; only ordering matters when
  two same-target journals coexist, which the durable `max+1` makes strictly increasing). New
  artifact_store internals: `_next_generation`, `_journal_gen`; `import time` removed.
