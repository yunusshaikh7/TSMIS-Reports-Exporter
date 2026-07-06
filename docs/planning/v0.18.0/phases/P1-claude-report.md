# P1 — Completion/outcome contract + F1/F3/F4 + frontend payload — Claude report

## 1. Phase ID and name
**P1** — Completion/outcome contract + F1/F3/F4 + frontend payload `[blocking]`

## 2. Baseline commit
`65aef98` (HEAD after PA committed). Baseline: **50/50** golden checks green, byte-compile green,
tree clean apart from the untracked `docs/planning/` workspace.

## 3. Changes made
The central-thesis phase: make the implicit completion/freshness/promotion contracts **explicit,
producer-owned, and tested**, so partial work can never read as complete, aggregate counts are
correct, and the UI reflects partial. Eight threads:

1. **Orthogonal outcome contract** — new `scripts/outcome.py` defines two producer-owned axes
   (`completion ∈ {complete, partial, no_data, cancelled, failed}`, `artifact ∈ {promoted,
   new_unpromoted, previous_preserved, none}`) + the pure mapping from structured COUNTS to a
   completion (never parsed from `summary_lines`). `events.py` `RunResult`/`ConsolidateResult` gain
   additive fields carrying them.
2. **F1 — promote gate** (`gui_worker._run_specs`): the store staging→live swap now happens **only
   when `completion == complete`**. A partial / no_data / failed / cancelled refresh discards
   staging and keeps last-good (subsumes the old cancel-only discard). The run records
   `result.completion` + `result.artifact`.
3. **F3 — honor the consolidation result** (`matrix`): `_consolidate_store_folder` now **returns**
   the `ConsolidateResult` (was discarded). `consolidate_and_compare_tsn` raises the consolidator's
   own message on a non-comparable (failed/no_data/cancelled) consolidation instead of comparing /
   caching it; `_ensure_consolidated` likewise.
4. **F4 / O4 — layout-correct counts** (`matrix.read_counts`): the count reader **detects the
   layout from the produced Comparison sheet's header** (column A == "Route" ⇒ Route-keyed, else
   flat/aggregate) instead of a hardcoded `has_route=True`. Fixes the aggregate vs-TSN sites
   (matrix `build_comparison`, `day_matrix`) **and** the cross-env site (`build_cell_comparison`,
   O4) — an aggregate adapter can have a `sheet_name` yet emit a flat sheet, which read as 0 diffs.
5. **Producer-owned partial** — all six consolidators (`consolidate_xlsx_base` + ramp/intersection
   summary + the two PDF consolidators) now SET `completion` (+ `skipped_inputs`/`failed_inputs`)
   at their `status="ok"` return; the HL-PDF/TSN consolidators **escalate** PDF-level drops
   (`skipped_no_geometry` / stale geometry / failed PDFs) to `partial` (RR2-B1 / D18 down-payment).
6. **One versioned cache envelope** — new `scripts/cache_envelope.py`; the matrix env / matrix TSN /
   by-day caches read through `unwrap` (a pre-P1 raw dict → empty ⇒ one-time rebuild) and write
   through `wrap` (`{schema_version, output_identity, payload}`). P2 extends the same envelope.
7. **Frontend payload** — `gui_api._build_export_summary` adds per-report + run-level
   `completion`/`artifact`; `run_ended` carries them for export/batch runs. `app.js
   renderCompletion` branches on the producer-owned `completion` (a **skipped-only** run is now
   "Finished — incomplete", not a green "complete") with an absent-field default-derive, and
   surfaces "— kept last-good" for `previous_preserved`; the `#mock` sets the same fields.
8. **Matrix honors completion** — `MatrixBatchExportWorker` counts a step "ok" only when its export
   was complete; `gui_api._on_matrix_export_done` auto-chains the by-day consolidate+compare **only
   when the export was complete** (a partial refresh kept last-good — don't auto-diff stale data).

## 4. Files affected
**New:** `scripts/outcome.py`, `scripts/cache_envelope.py`; checks
`build/check_outcome_contract.py` (CT-1), `build/check_read_counts_layout.py` (CT-14),
`build/check_consolidate_outcome.py` (CT-2), `build/check_export_summary_outcome.py` (CT-3).
**Modified:** `scripts/events.py` (additive fields), `scripts/gui_worker.py` (F1 + matrix step
completion), `scripts/matrix.py` (F3 + F4/O4 + cache envelope), `scripts/day_matrix.py` (F4 +
cache envelope), `scripts/gui_api.py` (summary + run_ended + chain gate), `scripts/ui/app.js`
(renderCompletion + mock), the six consolidators, `build/app.spec` (+`outcome`,+`cache_envelope`),
`.github/workflows/checks.yml` (the 4 CT checks). **Untouched:** `compare_core` (regression-locked),
`updater`, auth.

## 5. Architectural decisions
- **`outcome.py` owns the vocabulary + predicates; `events.py` stays dependency-free** (it declares
  the string/int fields; producers set them via `outcome.*` constants). No import coupling.
- **F4/O4 = detect from the WORKBOOK, not the row's `has_route`.** The old `matrix.py:874` comment
  ("Do NOT switch this to the row's `_hr`") is **respected** — I did not switch to `_hr`; I read the
  produced sheet's header. This is correct for every report (HL is Route-keyed; aggregate is flat)
  regardless of the adapter's declared layout, which is what made O4 wrong (an aggregate adapter
  with a `sheet_name`). The Comparison-sheet column layout (Route in column A iff Route-keyed) is
  now a **documented contract** in `read_counts`' docstring.
- **F3 raises the consolidator's own message** (rather than returning an error result) so the
  existing "nothing to compare → raise" contract + `check_matrix_tsn` stay intact, while the message
  is now the consolidator's specific one (clearer). "Keep stale prior" holds: the cache write is
  skipped (the raise propagates before it), so the prior cached comparison is untouched.
- **Producers set the `partial` distinction; the coarse ok/error/cancelled is inferred.**
  `outcome.consolidate_completion_of` is the intended back-compat seam (status→completion); the
  producers set the one thing inference can't recover — `partial` (a `status="ok"` run that left
  inputs out) — plus the structured counts.
- **Cache migration gates on `schema_version` only** (output_identity is recorded for P2). A pre-P1
  raw dict has no `schema_version` ⇒ reads empty ⇒ exactly one forward rebuild; the old file is left
  until a successful recompute overwrites it.
- **Run-level completion from aggregated totals** (matches the card's count chips); run-level
  artifact = the most telling per-report outcome (a `previous_preserved` wins over a `promoted`).

## 6. Compatibility and migration handling
- **Additive only.** New result fields default `None`/`0`; any path that doesn't set `completion`
  reads as "absent" — consumers fall back to count-derivation (`run_completion`) or status-inference
  (`consolidate_completion_of`), and `app.js` defaults absent → derive. No output filename, sheet
  layout, or registry change.
- **One cache rebuild** (R1-R15): the versioned envelope makes a pre-P1 matrix/by-day cache read as
  empty once; subsequent records repopulate it in the envelope. P2 extends the **same**
  `schema_version` with `input_fingerprint` (one released value, one rebuild — RR3-C3).
- **`compare_core` byte/semantically unchanged** (untouched); the comparison adapters are unchanged.
  Canary comparison checks pass identically.

## 7. Tests and commands run
All via `build/.venv/Scripts/python.exe`, offline (no live TSMIS / auth file / network / browser
launch):
- **CT-1** `check_outcome_contract.py` — every §C.1 export-completion row, consolidate completion,
  promote/compare/artifact gating. PASS.
- **CT-14** `check_read_counts_layout.py` — synthetic Route-keyed + aggregate Comparison workbooks:
  auto-detect counts both correctly; the F4 bug (aggregate-as-Route → 0 diffs) reproduced; auto-detect
  fixes it. PASS.
- **CT-2** `check_consolidate_outcome.py` — consolidator producer-owned completion (complete /
  partial-with-skipped / error→failed→not-comparable) + `_consolidate_store_folder` returns its
  result (F3 regression guard). PASS.
- **CT-3** `check_export_summary_outcome.py` — `_build_export_summary` run-level + per-report
  completion for every state (skipped→partial, all-empty→no_data, cancelled, multi-report); the
  cache-envelope migration end-to-end (legacy raw → empty, record→load round-trip). PASS.
- **Full regression suite:** `for f in build/check_*.py` → **54/54 PASS** (50 baseline + the 4 CTs),
  incl. `check_matrix*`, `check_day_matrix`, `check_b3_batch`, `check_gui_bridge`, and the
  regression-locked comparison/consolidator checks. Byte-compile clean; `node --check app.js` clean;
  `check_app_modules` green (outcome + cache_envelope declared); `checks.yml` valid YAML;
  `git diff --check` clean.
- **`#mock` (port 8765, `/index.html#mock`, fresh JS):** `renderCompletion` drives every state —
  complete→"Export complete" [ok]; partial+failed→"Finished with failures — kept last-good" [warn];
  **partial+skipped→"Finished — incomplete" [warn]** (the key fix; was a green "complete"); no_data;
  cancelled; absent→default-derive. A partial card showed correct count chips (saved 248, empty 1,
  failed 3 lit), failed-routes line, retry enabled. No console errors.

## 8. Results
All P1 objectives met and verified offline: partial work cannot read as complete (F1 gate +
producer completion + the card); aggregate vs-TSN and cross-env counts are layout-correct (F4/O4);
a failed consolidation is not compared/cached (F3); the orthogonal contract flows producer →
store → summary → run_ended → card; the cache is one versioned envelope. **54/54** suite green; the
app is runnable (additive fields, the `#mock` boots and renders correctly).

## 9. Before/after measurements
| Aspect | Before (`65aef98`) | After |
|---|---|---|
| Partial export into the store | promoted on no-exception (clobbered last-good — F1) | promoted only when `complete`; else last-good kept |
| Aggregate vs-TSN / cross-env counts | `read_counts(has_route=True)` ⇒ 0 diffs on flat sheets (F4/O4) | layout auto-detected from the workbook header |
| Failed store consolidation | `ConsolidateResult` discarded; generic "nothing to compare" (F3) | result honored; raises the consolidator's own message; not cached |
| Consolidation `partial` | hidden inside `status="ok"` + a warning banner | producer-owned `completion=partial` + `skipped/failed_inputs` |
| A skipped-only export | card read "Export complete" (green) | "Finished — incomplete" (amber) |
| Matrix/by-day cache | unversioned raw dict | versioned envelope; one forward rebuild |
| Golden checks | 50 | 54 (+CT-1/CT-2/CT-3/CT-14) |

## 10. Deviations from the approved plan
- **F3 raises (the consolidator's message) rather than returning an error result** — to preserve the
  established "nothing to compare → raise" contract and `check_matrix_tsn`, while still honoring the
  result (clearer message, cache left intact). A faithful, test-compatible realization of "honor the
  ConsolidateResult."
- **Producers set `completion` at the `status="ok"` return** (the `partial` distinction); the
  error/cancelled paths use `outcome.consolidate_completion_of`'s status-inference (the module's
  intended back-compat seam), so they are producer-owned for the load-bearing case without scattering
  constant-setting across every early return.
- **F4/O4 fixed by workbook auto-detection** (the plan's "layout from the adapter/workbook") — this
  also fixes O4 (not merely "verify" it): an aggregate cross-env adapter with a `sheet_name` had
  `has_route=True` and read 0 diffs. No other deviations; nothing regression-locked touched; no
  scope pulled from P2 (the cache envelope carries counts only; fingerprints stay P2).

## 11. Known limitations and external verification
- **Work-PC acceptance owed (not in the DoD — §M):** a real refresh with an induced failed route
  keeping last-good + showing "partial"; verified offline here via CT-1/CT-3 + the `#mock`.
- **`output_identity` is recorded but not gated** in the cache envelope (P2 consults it).
- **Canonical docs unchanged** — the new outcome/column-layout/cache contracts are documented in
  code (outcome.py, read_counts' docstring) for this phase; folding them into `docs/` is P11's job
  (per the plan). `docs/roadmap.md`'s older "P1 empty-routes" line is v0.17.0's narrower item and is
  superseded, not contradicted.
- The frozen build is not exercised here (no PyInstaller run); the new modules are declared in
  `APP_MODULES` (check_app_modules green) and the frozen gate runs in CI (PA's `frozen-gate.yml`).

## 12. Exact diff scope Codex should review
Baseline `65aef98` → worktree (ignore `docs/planning/`):
- **`scripts/outcome.py`** (new) — the two axes + `export_completion`/`run_completion`/
  `consolidate_completion`/`consolidate_completion_of` + the gating predicates.
- **`scripts/events.py`** — the additive `completion`/`artifact`/`skipped_inputs`/`failed_inputs`.
- **`scripts/gui_worker.py`** — F1 (the promote gate + `result.completion`/`artifact`; the
  fresh-staging `exists` anomaly log), and `_run_matrix_export_step` returning completion +
  `MatrixBatchExportWorker` counting `ok` by completion.
- **`scripts/matrix.py`** — `read_counts` header auto-detection (F4/O4) + the three call sites;
  `_consolidate_store_folder` returning its result + `consolidate_and_compare_tsn`/
  `_ensure_consolidated` honoring it (F3); the cache-envelope wrap/unwrap (env + TSN caches).
- **`scripts/day_matrix.py`** — the F4 call site + the by-day cache envelope.
- **`scripts/gui_api.py`** — `_build_export_summary` (per-report + run-level completion/artifact),
  `_end_task` run_ended payload (export/batch only), `_on_matrix_export_done` chain-on-complete.
- **the six consolidators** — producer-owned `completion` + counts at the `ok` return; the HL-PDF /
  TSN escalation to `partial`.
- **`scripts/ui/app.js`** — `renderCompletion` branching on `completion` (+ default-derive + the
  "kept last-good" note) and the mock's `completion`/`artifact`.
- **`scripts/cache_envelope.py`** (new) + **`build/app.spec`** (the two new modules).
- **the 4 new `build/check_*.py`** + their `checks.yml` wiring.

Focus areas: (1) is the F4/O4 header auto-detect correct for every flavor (HL Route-keyed vs
aggregate)? (2) does the F1 gate correctly keep last-good for partial/failed/cancelled? (3) F3 — is
"keep stale prior" actually preserved (cache untouched on the raise)? (4) the additive-field
back-compat / absent-field defaults end to end; (5) the cache migration (one rebuild, never
corrupt).

---

## Remediation — Review round 1 (Codex verdict: BLOCKED)

### Review round addressed
Codex P1 review **round 1** — `BLOCKED` (P1-B01..B04 blocking + P1-R01 required). All five were
legitimate; the round-1 checks were green because they did not exercise the failing orchestration
paths (the central lesson Codex drove home).

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01** — F4/O4 layout detection wrong (A1=='Route' is not a layout signal) | **Fixed** | `read_counts` now locates the count columns by the INVARIANT header **labels** `'Status'`/`'Diffs'` (compare_core writes them in every flavor), not column A. The flat Ramp/Intersection Summary cross-env sheets DO start with 'Route' (`RS_HEADER`/`agg_header`); they now read correctly. The `has_route` arg is only a fallback for label-less sheets. |
| **P1-B02** — batch envs marked done after partial/no-data | **Fixed** | `BatchWorker.run` retains the env's results and marks it done **only when every selected report is complete**; partial/no-data/failed envs are left PENDING with an explicit diagnostic. `batch_done` carries an aggregate `completion`, and `_end_task` adds the batch completion/artifact to `run_ended`. |
| **P1-B03** — fresh-staging `exists` anomaly logged but promoted | **Fixed** | An `in_store and result.exists` outcome now forces `completion = FAILED` (non-promotable) → staging discarded, last-good preserved, anomaly logged. `exists` stays valid for resume/non-store runs. |
| **P1-B04** — run-level reduction shows incomplete multi-report as green | **Fixed** | New `outcome.reduce_completion` reduces over the **per-report** completions (complete only if ALL complete; complete+no_data → partial; cancelled/aborted never complete). `_build_export_summary` uses it instead of summed counts; `export_partial` passes `aborted=True`. |
| **P1-R01** — partial consolidation compares but the flag is discarded | **Fixed** | `consolidate_and_compare_tsn` propagates a PARTIAL consolidation into the comparison `result.completion`; `record_result`/`record_tsn_result` persist a `completion` field; `_cmp_state` surfaces it (old records default complete). Failed/no-data still raise (don't compare/cache). |

No findings rejected or deferred.

### Remediation changes
- **`scripts/matrix.py`** — `read_counts` label-based column location (B01); the cache records +
  `_cmp_state` carry `completion`; `consolidate_and_compare_tsn` propagates partial; the two record
  call sites pass it (R01).
- **`scripts/gui_worker.py`** — `_run_specs` in-store `exists` → failed/non-promotable (B03);
  `BatchWorker.run` retains results + gates env-done on all-complete + emits `batch_done.completion`
  (B02).
- **`scripts/gui_api.py`** — `_build_export_summary` run-level **reducer** + `aborted` (B04);
  `export_partial` aborted; `_on_batch_done` + `_end_task` carry the batch outcome into `run_ended` (B02).
- **`scripts/outcome.py`** — `reduce_completion` (B04).
- **Tests (the regression tests Codex required — each fails on the pre-fix code):**
  `check_read_counts_layout` rebuilt around the flat-with-'Route'-in-A shape **and an end-to-end
  `build_cell_comparison`→cache assertion** (B01); **new `check_batch_outcome`** drives the real
  `BatchWorker.run`/`ExportWorker._run_specs` producer paths for complete/partial/no-data/mixed +
  the `exists` anomaly (B02/B03); `check_export_summary_outcome` + `check_outcome_contract` cover the
  reducer (complete+no_data→partial, aborted) (B04); `check_consolidate_outcome` adds the F3/R01
  orchestration (partial compares + flagged; failed raises + comparator never called; cache durability);
  `check_worker_lifecycle`'s batch stub updated for the results-retaining `BatchWorker`. Wired into
  `checks.yml`.

### Updated verification
- **P1-B01:** `check_read_counts_layout` — a FLAT sheet with column A = 'Route' now reads `(1 diff,
  2 one-sided)` (was the mis-read `(1,1)`); the count survives through `build_cell_comparison` into
  the cache (`diff_cells=1, one_sided=2`). Route-keyed, 'Category'-keyed, label-less fallback, and
  unreadable all covered.
- **P1-B02/B03:** `check_batch_outcome` (new) — a partial/no-data/mixed report leaves the env
  **pending** (no `mark_done`); all-complete marks it done; `batch_done.completion` ∈ complete/partial;
  an in-store `exists` result is **failed**, the swap is **not** called, artifact `previous_preserved`;
  a complete in-store run promotes.
- **P1-B04:** `check_export_summary_outcome` — complete + no_data → run `partial` (not green); an
  aborted run is non-complete; per-report completions preserved. `check_outcome_contract` — the
  `reduce_completion` truth table.
- **P1-R01:** `check_consolidate_outcome` — a partial consolidation invokes the comparator and the
  result carries `partial`; a failed one raises and the comparator is **never** invoked; the partial
  flag round-trips through the TSN cache and `_cmp_state`.
- **Suite:** **55/55** (50 baseline + CT-1/2/3/14 + the new `check_batch_outcome`); byte-compile,
  `node --check app.js`, `check_app_modules`, `checks.yml` YAML, `git diff --check` all green. The
  round-1 `#mock` render verification is unaffected (no JS changed this round).

### Changed measurements
| Metric | Round 1 | After remediation |
|---|---|---|
| read_counts on a flat 'Route'-in-A sheet | mis-read `(1,1)` | correct `(1,2)`, via the Status/Diffs labels |
| Batch env with a partial report | marked **done** (resume skips it) | left **pending** (resume re-pulls) |
| In-store `exists` anomaly | logged then **promoted** | **rejected** (failed, last-good kept) |
| Multi-report complete + no_data | run **complete** (green) | run **partial** (not green) |
| Partial consolidation in the matrix cache | no completion field | `completion=partial` persisted + surfaced |
| Golden checks | 54 | 55 (+`check_batch_outcome`) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a
real refresh (§M).

---

## Remediation — Review round 2 (Codex verdict: BLOCKED)

### Review round addressed
Codex P1 review **round 2** — `BLOCKED`. Codex **confirmed P1-B01 and P1-B04 Resolved** (the
read_counts label detection and the run-level reducer) and re-blocked on two reproducible terminal-path
defects plus an incomplete required fix: **P1-B02** (batch terminal outcome can leak from a previous
run), **P1-B03** (a partial store refresh still auto-consolidates preserved stale live data), and
**P1-R01** (partial consolidation state is not durable across reuse / self-comparison / the renderer).
All three were legitimate and independently reproduced; the round-1 fixes corrected the manifest/promote
accounting but left these adjacent terminal paths uncovered.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01** — read_counts layout detection | **Resolved (round 1)** — no further action; Codex confirmed `(1, 2)` on the real Ramp Summary fixture. |
| **P1-B04** — run-level reducer | **Resolved (round 1)** — no further action; Codex confirmed the reducer prevents a green aggregate over no_data/partial/failed/aborted children. |
| **P1-B02** — batch terminal outcome leaks from a previous run | **Fixed** | `start_batch_export` **and** `resume_batch` now clear `_last_batch_outcome` (alongside `_last_summary`); `_end_task`'s batch branch **defaults a missing outcome to FAILED/previous_preserved**, so a batch that ended via the ERROR path (auth/browser → `error`, not `batch_done`, reaching `_end_task` through `_on_error`) reports the **current** failed run, never the prior success. The normal/cancelled/partial outcomes still come from `_on_batch_done`. |
| **P1-B03** — partial store refresh auto-consolidates stale live data | **Fixed** | `_run_specs` now gates the B2 auto-consolidate: a STORE refresh consolidates **only when it promoted** (`artifact == PROMOTED`, i.e. `completion == complete`); a partial/failed/rejected store refresh discarded its staging and kept last-good, so it no longer rebuilds a derived artifact from the OLD live store. **Non-store (dated-run) consolidation is unchanged** (`store_ok = (not in_store) or artifact==PROMOTED`), preserving the supported "consolidate whatever routes a dated run got" behavior. |
| **P1-R01** — partial consolidation not durable across reuse/self/renderer | **Fixed** | Three gaps closed: (1) **Reuse** — `_consolidate_store_folder` persists the producer completion in an **mtime-guarded sidecar** beside the consolidated workbook; `consolidate_and_compare_tsn` recovers it when the consolidated is REUSED (`cres is None`). (2) **Self-comparison** — `_ensure_consolidated` now returns `(path, completion)`; the PDF-vs-Excel self branch reduces both sides (`PARTIAL in (comp_env, comp_other) → partial`). (3) **Durability + renderer** — `day_matrix.record_result` threads `completion` into the by-day cache (the Everything cache already did, round 1); `app.js mxCellContent` renders a partial cell as a distinct **`mx-partial`** (amber + inset border + "inputs incomplete" note), never the green `mx-match`, with matching `app.css` rules and a legend key. |

No findings rejected or deferred.

### Remediation changes
- **`scripts/gui_api.py`** — `start_batch_export` + `resume_batch` clear `_last_batch_outcome`;
  `_end_task` batch branch defaults a None outcome to `FAILED`/`PREVIOUS_PRESERVED` (B02).
- **`scripts/gui_worker.py`** — `_run_specs` `store_ok` gate on the auto-consolidate (B03).
- **`scripts/matrix.py`** — `_consolidation_meta_path` / `_write_consolidation_meta` /
  `_read_consolidation_completion` (mtime-guarded sidecar); `_consolidate_store_folder` writes it;
  `consolidate_and_compare_tsn` recovers it on reuse; `_ensure_consolidated` returns
  `(path, completion)`; the self branch reduces both sides (R01).
- **`scripts/day_matrix.py`** — `import outcome`; `record_result` gains a `completion` field;
  `build_day_cell` passes `result.completion` (R01 durability for the by-day matrix).
- **`scripts/ui/app.js`** + **`scripts/ui/app.css`** + **`scripts/ui/index.html`** — `mxCellContent`
  partial branch; `.mx-cell.mx-partial` / `.mx-key.mx-partial` rules; a "partial inputs" legend key in
  both matrices (R01 renderer).
- **Tests (each fails on the pre-fix code — verified by revert/run/restore):**
  - **`build/check_batch_outcome.py`** — new `_b02_no_stale_leak` drives the REAL GuiApi terminal
    lifecycle (success → real `resume_batch` clear → failed `_on_error`) and asserts the second
    `run_ended` cannot reuse the first outcome (B02); `_run_instore` extended to capture auto-consolidate
    calls, proving a partial/rejected store refresh does NOT consolidate and a complete one does (B03).
  - **`build/check_consolidate_outcome.py`** — sidecar round-trip + mtime-guard, REUSE-keeps-partial
    (fresh build flags partial, reused build recovers it from the sidecar), self-comparison with one
    partial side, and snapshot serialization of `cmp.completion` (R01).
  - **`build/check_mx_partial_render.js`** (new) — extracts `mxCellContent` into a Node `vm` sandbox and
    asserts a partial cell renders `mx-partial` (not the green `mx-match`); wired into `checks.yml` as a
    blocking step (R01 renderer).

### Updated verification
- **P1-B02:** `check_batch_outcome._b02_no_stale_leak` — run 1 success → `run_ended` complete; the real
  `resume_batch` clears the outcome; run 2 (auth error) → `run_ended` is **failed/previous_preserved**,
  not the prior success. **Reverting either the clear or the `_end_task` default reproduces the leak**
  (3 checks red).
- **P1-B03:** `check_batch_outcome` — a partial store refresh (`saved=3, failed=1`) and a rejected
  `exists` refresh both leave the auto-consolidate **uninvoked**; a complete refresh invokes it exactly
  once with `(complete, promoted)`. **Reverting the gate makes the partial case auto-consolidate** (red).
- **P1-R01:** `check_consolidate_outcome` — sidecar round-trips partial and an mtime bump drops the stale
  flag; a REUSED partial consolidated stays `partial`; a self comparison with one partial side reduces to
  `partial`; the snapshot's tsn cell serializes `completion=partial`. `check_mx_partial_render.js` — the
  loaded renderer maps partial → `mx-partial` + "inputs incomplete". **Reverting the reuse recovery makes
  the reused build read `None`; reverting the renderer makes a partial cell read green `mx-match`** (red).
- **`#mock` (fresh app.js + app.css, port 8765):** the live page's `mxCellContent` returns
  `mx-partial`/"inputs incomplete" for a partial cell (and `+1 one-sided · inputs incomplete` with
  diffs); `getComputedStyle` confirms `.mx-partial` resolves to a **distinct amber background + a 1.5px
  inset warning border** vs `.mx-match`'s green / no-shadow; the legend carries the partial key; **no
  console errors**.
- **Suite:** **55/55** Python checks + the new **`check_mx_partial_render.js`** (56 total, run as a
  separate blocking step) + byte-compile + `node --check app.js` + `check_app_modules` + all-workflow YAML
  + `git diff --check` all green. `compare_core` / updater / auth untouched; HEAD still `65aef98`
  (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Round 1 | After round-2 remediation |
|---|---|---|
| Failed batch after a prior success | `run_ended` = the **prior** complete/promoted (leak) | `run_ended` = **failed/previous_preserved** (current run) |
| Partial store refresh + auto-consolidate | re-consolidates the **old live** store (stale-as-fresh) | auto-consolidate **skipped** (only a promoted refresh consolidates) |
| Reused partial consolidated in the matrix | completion **lost** (`None` → reads complete) | **partial recovered** from the mtime-guarded sidecar |
| Self comparison with one partial side | completion **discarded** (`_ensure_consolidated` → Path only) | **reduced to partial** (both sides' completions) |
| Partial comparison cell in the UI | green **`✓ match` / identical** (indistinct) | **`mx-partial`** amber + "inputs incomplete" (+ legend key) |
| Golden checks | 55 | 55 Python + 1 Node renderer (56) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial vs-TSN consolidation rendering the amber `mx-partial` cell live (§M).

---

## Remediation — Review rounds 3–4 (Codex verdict: BLOCKED)

### Review round addressed
Codex P1 review **rounds 3 and 4** (round 4 re-states round 3 verbatim — it confirmed no remediation
had been submitted yet; this section is that remediation). Codex **confirmed P1-B01/B03/B04 Resolved and
P1-R01 partially resolved** (matrix-owned writes/reuse, self-comparison, cache, rendering), and re-blocked
on the parts of the approved producer/consumer contract still incomplete on the TSN side and at the shared
write boundary: **P1-B05** (blocking), **P1-R01** (required — shared-writer bypass + fail-safety), and
**P1-B02** (required, narrowed — a partial batch then a fatal error read as wholly failed). All three were
legitimate and independently reproduced; the plan §C.1 (lines 200-204) explicitly names "the PDF/TSN
consolidators" as producers and "GUI auto-consolidate, matrix, TSN library" as consumers, so this is
completing the approved contract — no scope expansion (matching Codex's own "no broader abstraction" note).

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01 / P1-B03 / P1-B04** | **Resolved (prior rounds)** — no further action. |
| **P1-B05** — TSN incomplete outcomes neither produced nor carried | **Fixed** | All three incomplete-capable TSN builders now set producer-owned `completion` + structured counts: `tsn_load_ramp_summary` / `tsn_load_intersection_summary` (`partial` + `skipped_inputs` when a category is missing) and `consolidate_tsn_highway_sequence` (`partial` + `failed_inputs` when a district PDF fails). `tsn_library.build_consolidated` **persists** the outcome beside the generated workbook (shared boundary) and `tsn_library.resolve` **exposes** `completion` on every path-bearing source; `matrix.consolidate_tsn_pdfs` (legacy dest PDF path) persists too. `matrix.build_comparison` **and** `day_matrix.build_day_cell` now **reduce the TSN side** (partial TSN ⇒ the cell records partial), flowing to both caches + the `mx-partial` renderer. |
| **P1-R01** — persistence bypassed by other writers + not fail-safe | **Fixed (with modification)** | Outcome persistence moved to a **shared boundary** — new `scripts/consolidation_meta.py` (`write_outcome`/`read_completion`) — called by **every** persistent writer: the matrix store consolidation, `ExportWorker._auto_consolidate`, `ConsolidateWorker.run` (GUI/console Consolidate), and the TSN-library builds. Writes are **atomic** (tmp + `os.replace`); reads **validate** schema/vocabulary/types and **degrade safely** — a present-but-unusable sidecar reads `partial` (a current-version artifact whose outcome can't be trusted never reads green), while NO sidecar reads `None` (deliberate legacy back-compat → complete). *Modification:* rather than thin matrix-private helpers, the boundary is its own leaf module (imported by matrix / gui_worker / tsn_library) so no writer can bypass it. |
| **P1-B02** — partial batch then fatal error reported wholly failed | **Fixed** | `GuiApi._on_error` now consults the live batch progress (`_batch.done`) on the fatal terminal: ≥1 environment completed ⇒ **partial** (those envs were marked done + kept, and stay resumable), zero completed ⇒ **failed**. `_end_task`'s None→failed default remains for any path with no progress at all. |

No findings rejected or deferred.

### Remediation changes
- **New `scripts/consolidation_meta.py`** — the shared, atomic, validated outcome-sidecar boundary
  (`SCHEMA_VERSION`, `write_outcome`, `read_completion`).
- **`scripts/matrix.py`** — removed the round-2 private sidecar helpers; routes `_consolidate_store_folder`,
  `consolidate_and_compare_tsn` (reuse), `_ensure_consolidated`, and `consolidate_tsn_pdfs` through
  `consolidation_meta`; `build_comparison` (tsn branch) reduces the TSN-side completion.
- **`scripts/day_matrix.py`** — `build_day_cell` reduces the TSN-side completion.
- **`scripts/gui_worker.py`** — `_auto_consolidate` + `ConsolidateWorker.run` persist via `consolidation_meta`.
- **`scripts/tsn_library.py`** — `build_consolidated` persists; `resolve` (now a thin wrapper over
  `_resolve_source`) attaches `completion` to any path-bearing source.
- **`scripts/tsn_load_ramp_summary.py`, `scripts/tsn_load_intersection_summary.py`,
  `scripts/consolidate_tsn_highway_sequence.py`** — producer-owned `completion` + counts.
- **`scripts/gui_api.py`** — `_on_error` batch progress-aware partial/failed reduction.
- **`build/app.spec`** — `APP_MODULES += "consolidation_meta"` (F6).
- **Tests (each fails on the pre-fix code — verified by revert/run/restore):**
  - **new `build/check_tsn_outcome.py`** — the three TSN producers set completion/counts; `build_consolidated`
    persists; `resolve` exposes; the Everything matrix **and** by-day matrix reduce a partial TSN side
    (end-to-end build → resolve/reuse → matrix). Wired into `checks.yml`.
  - **`build/check_consolidate_outcome.py`** — `read_completion` degrades safely (corrupt JSON / non-numeric
    mtime / wrong schema → conservative `partial`, never a `ValueError`); `write_outcome` is atomic (no stray
    `.tmp`) + scoped (no sidecar for a failed result); `ConsolidateWorker.run` and `_auto_consolidate` persist,
    and a GUI-Consolidate-written partial is read partial on matrix REUSE (bypass closed). *Also fixed a
    pre-existing test-isolation bug:* `consolidated_store_path` keys off `store_dir.parent`, so the round-2/3
    stores now use unique parents (the round-3 ConsolidateWorker check had been reading the round-2 leftover).
  - **`build/check_batch_outcome.py`** — a two-environment batch (env1 complete + persisted, env2 fatal auth
    error) drives the REAL `BatchWorker` then replays its queue through a REAL `GuiApi`: env2 left pending
    (resumable), terminal reads **partial** (not wholly failed).

### Updated verification
- **P1-B05:** `check_tsn_outcome` — producers complete/partial; `build_consolidated`→sidecar→`resolve`
  completion=partial; Everything + by-day cells reduce to partial. **Reverting the ramp_summary producer
  cascades the whole chain red; reverting the `build_comparison` reduce reds only the Everything cell** (the
  by-day reduce + resolve still pass — clean isolation).
- **P1-R01:** `check_consolidate_outcome` round-3 — corrupt/malformed/wrong-schema sidecars read `partial`
  without raising (**removing the type guard reproduces Codex's `ValueError`**); atomic write leaves no `.tmp`;
  `ConsolidateWorker.run`/`_auto_consolidate` persist and the matrix reuses partial (**reverting the
  `ConsolidateWorker` write reds both the persist + the reuse checks**).
- **P1-B02:** `check_batch_outcome` round-3 — env1-done-then-env2-fatal ⇒ terminal partial + env2 resumable
  (**reverting the `_on_error` reduction reds the partial check**).
- **Suite:** **56/56** Python checks (55 + `check_tsn_outcome`) + the Node renderer check + byte-compile +
  `node --check app.js` + `check_app_modules` (now lists `consolidation_meta`) + `check_import_direction`
  (the new leaf is acyclic) + all-workflow YAML + `git diff --check` all green. No UI files changed this round
  (the prior round's `#mock` render verification stands). `compare_core` / updater / auth untouched; HEAD
  still `65aef98` (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Before round-3/4 remediation | After |
|---|---|---|
| Incomplete TSN consolidation (missing category / failed district PDF) | `status=ok`, no `completion` (warning text only) | producer-owned `completion=partial` + `skipped`/`failed_inputs` |
| A reused PARTIAL TSN workbook in either matrix | read as a green `complete` cell | `resolve` exposes partial → cell flags partial |
| A direct GUI/auto consolidation partial, then matrix reuse | no sidecar → reused as `complete` | persisted at the shared boundary → reused as `partial` |
| A corrupt / non-numeric-mtime sidecar | `ValueError` (crash) | conservative `partial`, never a silent `complete` |
| A batch: env1 done, then env2 auth failure | terminal **failed** (lost env1's work) | terminal **partial**, env2 resumable |
| Golden checks | 56 (55 Py + Node) | 57 (56 Py + Node) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial TSN normalization (district PDFs / categories) rendering the amber `mx-partial` cell
live; a real mid-batch auth failure after a completed environment showing the partial terminal (§M).

---

## Remediation — Review round 5 (Codex verdict: BLOCKED)

### Review round addressed
Codex P1 review **round 5** — `BLOCKED`. Codex **confirmed P1-B01/B02/B03/B04 Resolved and P1-R01
substantially resolved** (TSN-library, GUI/auto/matrix persistence, reuse, self-comparison, cache, render,
fail-safe read of malformed/wrong-schema sidecars). Two narrow contract-completion gaps remained: **P1-B05**
(the legacy matrix TSN-PDF consumer still treated a failed producer as success) and **P1-R01** (the console
entry point bypassed the shared boundary, and metadata-publication failure / a present-but-unreadable sidecar
failed open). Both verified against the workspace and independently reproduced; both are completing the
already-approved §C.1 producer/consumer contract — no scope expansion.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01 / P1-B02 / P1-B03 / P1-B04** | **Resolved (prior rounds)** — no further action. |
| **P1-B05** — legacy TSN-PDF consolidation ignored a failed producer | **Fixed** | `matrix.consolidate_tsn_pdfs` now **honors the producer result**: a failed / no-data / cancelled `ConsolidateResult` **raises** the consolidator's own message (instead of returning a success-shaped path), so `MatrixTsnConsolidateWorker.run` reports a **not-refreshed** terminal (`matrix_done errors=1`, no "TSN workbook ready") and the prior workbook is kept untouched. A partial set stays usable but its flag is persisted. |
| **P1-R01** — console bypass + fail-open on publication failure | **Fixed** | (1) **Console:** `cli.run_consolidate_cli` (the `.bat` / standalone consolidator entry) now routes through `consolidation_meta.write_outcome`, so a partial dated consolidation can no longer be reused with no sidecar. (2) **Publication failure fail-safe:** `write_outcome` cleans the temp file on failure AND, for a non-complete artifact whose flag could not be published, **removes the derived workbook** so the next access rebuilds it (a complete artifact is safely kept — an absent sidecar correctly reads complete). (3) **Read fail-safe:** a present-but-unreadable sidecar (a non-`FileNotFoundError` `OSError`) now reads **conservative partial**, not absent-legacy `None`. |

No findings rejected or deferred.

### Remediation changes
- **`scripts/matrix.py`** — `consolidate_tsn_pdfs` raises on a non-comparable producer result before
  persisting/returning (P1-B05).
- **`scripts/cli.py`** — `import consolidation_meta`; `run_consolidate_cli` persists the producer outcome
  after the consolidator returns (P1-R01 console).
- **`scripts/consolidation_meta.py`** — `write_outcome` cleans the `.tmp` and removes a non-complete workbook
  on publication failure; `read_completion` returns conservative `partial` for a present-but-unreadable
  sidecar (P1-R01 fail-safe).
- **Tests (each fails on the pre-fix code — revert/run/restore-verified), all in
  `build/check_consolidate_outcome.py`:**
  - **P1-B05:** the REAL `MatrixTsnConsolidateWorker.run` over a pre-existing prior workbook with the
    underlying consolidator seam returning `status="error"` → asserts `matrix_done errors=1`, no
    "TSN workbook ready", and the prior workbook bytes unchanged.
  - **P1-R01 console:** the REAL `run_consolidate_cli` wrapper with a partial producer → the sidecar is
    persisted and reads `partial`.
  - **P1-R01 fail-safe:** an injected `PermissionError` at `os.replace` for a PARTIAL workbook leaves no
    stray `.tmp` and removes the workbook (not reusable-as-complete); a COMPLETE workbook survives (reads
    complete); a present-but-unreadable sidecar (a directory at the sidecar path) reads `partial`.

### Updated verification
- **P1-B05:** `check_consolidate_outcome` — failed legacy TSN consolidation ⇒ `errors=1` + prior kept; no
  "ready" success. **Reverting the `consolidate_tsn_pdfs` raise reds both the `errors=1` and the no-"ready"
  checks** (the prior-unchanged check still passes — the consolidator never wrote).
- **P1-R01:** `check_consolidate_outcome` — console wrapper persists partial (**reverting the
  `run_consolidate_cli` write reds it**); publication failure removes the partial workbook + cleans `.tmp`
  (**reverting the workbook-unlink reds the not-reusable check**); a present-but-unreadable sidecar reads
  partial (**reverting the read guard reds it**).
- **Suite:** **56/56** Python checks + the Node renderer + byte-compile + `node --check app.js` +
  `check_app_modules` + `check_import_direction` (cli→consolidation_meta is acyclic) + all-workflow YAML +
  `git diff --check` all green. No UI files changed this round (the prior `#mock` render stands).
  `compare_core` / updater / auth untouched; HEAD still `65aef98` (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Before round-5 remediation | After |
|---|---|---|
| Failed legacy TSN-PDF consolidation (matrix worker) | "TSN workbook ready", `matrix_done errors=0` (success) | raises → `errors=1`, not-refreshed, prior kept |
| Console / `.bat` partial consolidation, then matrix reuse | no sidecar → reused as `complete` | routed through the boundary → reused as `partial` |
| A PARTIAL workbook whose sidecar publication fails | stray `.tmp`, no sidecar → reused as `complete` | `.tmp` cleaned + workbook removed → rebuilt (never false-green) |
| A present-but-unreadable sidecar | `None` (absent-legacy → complete) | conservative `partial` |
| Golden checks | 57 (56 Py + Node) | 57 (56 Py + Node; coverage added to `check_consolidate_outcome`) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial TSN normalization rendering the amber `mx-partial` cell live; a real mid-batch auth
failure after a completed environment showing the partial terminal; a real failed district-PDF TSN
consolidation surfacing the not-refreshed terminal (§M).

---

## Remediation — Review round 6 (Codex verdict: PASS WITH FIXES)

### Review round addressed
Codex P1 review **round 6** — **`PASS WITH FIXES`** (no blocking findings; P1-B05 confirmed Resolved,
P1-B01/B02/B03/B04 remain resolved, P1-R01 otherwise resolved). One narrow required correction: the
round-5 fail-safe was **silent** — `write_outcome` deleted a partial workbook on publication failure but
returned nothing, so CLI/GUI callers still announced success; and if Windows ALSO refused the workbook
deletion (the lock variant the round-5 test omitted), the workbook stayed with no sidecar and later read
complete. Verified against the workspace and reproduced; the correction makes publication failure
**observable to callers** and leaves a **durable conservative state** even when the workbook can't be
removed — completing P1-R01 without expanding scope.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B05 / P1-B01 / P1-B02 / P1-B03 / P1-B04** | **Resolved (prior rounds)** — no further action. |
| **P1-R01** — publication failure not propagated; can still fail open | **Fixed (with modification)** | `consolidation_meta.write_outcome` now **returns a bool**: True when the outcome is safely represented (sidecar published, OR the artifact is COMPLETE so an absent sidecar correctly reads complete, OR nothing to persist); **False** only when a NON-complete artifact's flag could not be published — the caller must not announce a plain success. On that failure it (1) cleans the `.tmp`, (2) writes a **durable conservative `partial` marker** (`_mark_untrusted`, a direct non-atomic write) so reuse stays `partial` even if the workbook can't be removed — the false-green guard no longer relies on best-effort unlink alone — and (3) still removes the derived workbook so it rebuilds. Every announcing caller honors the return: `cli.run_consolidate_cli` prints a failure + `exit(1)` (no success summary); `ConsolidateWorker.run` emits a degraded `error` terminal (not `consolidate_done`); `_auto_consolidate` logs the discard (non-fatal); `matrix.consolidate_tsn_pdfs` raises (the worker reports not-refreshed). |

No findings rejected or deferred.

### Remediation changes
- **`scripts/consolidation_meta.py`** — `write_outcome` returns a bool; new `_silent_unlink` (best-effort,
  reports success) and `_mark_untrusted` (durable conservative `partial` marker on publication failure);
  COMPLETE-publish-failure returns True (harmless), partial returns False.
- **`scripts/cli.py`** — `run_consolidate_cli` captures the return; on False prints a clear failure and
  `sys.exit(1)` instead of the success summary.
- **`scripts/gui_worker.py`** — `ConsolidateWorker.run` emits an `error` terminal on False (not a success
  `consolidate_done`); `_auto_consolidate` logs the discard on False (non-fatal).
- **`scripts/matrix.py`** — `consolidate_tsn_pdfs` raises on False (a partial whose flag couldn't be
  recorded → the legacy worker reports a not-refreshed failure).
- **Tests (each fails on the pre-fix code — revert/run/restore-verified), in
  `build/check_consolidate_outcome.py`:** `write_outcome` returns True/False as specified;
  **publication + workbook-unlink failure** (the Windows-lock variant) returns False, preserves the
  workbook, AND keeps `read_completion` `partial` via the durable marker (no false-green); a COMPLETE
  publication failure returns True and reads complete; `run_consolidate_cli` exits non-zero with no success
  summary; `ConsolidateWorker.run` emits an `error` terminal and no `consolidate_done`.

### Updated verification
- **P1-R01:** all four round-6 assertions green; each reverts to red — neutering `_mark_untrusted` makes the
  locked partial read a false-green; reverting the `run_consolidate_cli` guard prints success + exit 0;
  reverting the `ConsolidateWorker` guard emits a success `consolidate_done`.
- **Suite:** **56/56** Python checks + the Node renderer + byte-compile + `node --check app.js` +
  `check_app_modules` + `check_import_direction` + `check_b2_autoconsolidate` (auto-consolidate honoring) +
  all-workflow YAML + `git diff --check` all green. No UI files changed this round. `compare_core` /
  updater / auth untouched; HEAD still `65aef98` (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Before round-6 remediation | After |
|---|---|---|
| `write_outcome` publication-failure signal | silent (returns None) | observable bool (False only when a partial couldn't be recorded) |
| CLI / GUI after a partial publication failure | announced success (summary / `consolidate_done ok`) | CLI exits non-zero (no summary); GUI emits a degraded `error` terminal |
| Partial workbook whose publish AND unlink both fail (Windows lock) | left with no sidecar → reads complete (false green) | durable conservative `partial` marker → reads partial |
| Golden checks | 57 (56 Py + Node) | 57 (56 Py + Node; round-6 coverage added to `check_consolidate_outcome`) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial TSN normalization rendering the amber `mx-partial` cell live; a real mid-batch auth
failure after a completed environment showing the partial terminal; a real failed district-PDF TSN
consolidation surfacing the not-refreshed terminal (§M).

---

## Remediation — Review round 7 (Codex verdict: PASS WITH FIXES)

### Review round addressed
Codex P1 review **round 7** — **`PASS WITH FIXES`** (no blocking findings; P1-B01..B05 remain resolved,
P1-R01 otherwise resolved). One narrow P1-R01 durability gap: the round-6 fallback marker (`_mark_untrusted`)
is itself best-effort, so a **three-way failure** — atomic publish, the fallback-marker write, AND the
workbook unlink all fail — left a sidecar-less workbook that `read_completion` reads as `None` (legacy →
complete). Codex also noted two persistent-writer callers (`matrix._consolidate_store_folder`,
`tsn_library.build_consolidated`) ignored `write_outcome`'s observable `False`. Both verified and reproduced;
the correction stays confined to the persistence boundary + its callers — no new abstraction.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01..B05** | **Resolved (prior rounds)** — no further action. |
| **P1-R01** — fallback marker can fail with the locked workbook → false-green; two callers ignore `False` | **Fixed (with modification)** | (1) **No false-green even under triple failure:** when atomic publish fails, the already-written `.tmp` holds a VALID payload; `write_outcome` now prefers removing the workbook (clean rebuild), else writes the direct `_mark_untrusted` marker, and **if that also fails, RETAINS the `.tmp` as a last-resort sentinel**. `read_completion` falls back to that `.tmp` on a missing final sidecar → returns `partial`, never `None`. So even when all three operations fail, reuse reads `partial`. (2) **Honor `False` at every writer:** `matrix._consolidate_store_folder` now **raises** on a `False` return (the comparison surfaces not-refreshed), and `tsn_library.build_consolidated` returns an **error** result — neither can claim a safely persisted artifact. |

No findings rejected or deferred.

### Remediation changes
- **`scripts/consolidation_meta.py`** — `write_outcome`'s failure path: remove workbook → else marker → else
  RETAIN the `.tmp` sentinel (only clean the `.tmp` when there is no false-green risk); `read_completion`
  falls back to a retained `.tmp` on a missing final sidecar → conservative `partial`. Docstring updated.
- **`scripts/matrix.py`** — `_consolidate_store_folder` raises when `write_outcome` returns `False`.
- **`scripts/tsn_library.py`** — `build_consolidated` returns an error `ConsolidateResult` when
  `write_outcome` returns `False`.
- **Tests (each fails on the pre-fix code — revert/run/restore-verified):**
  - **`build/check_consolidate_outcome.py`:** the **exact three-way failure** (publish + marker + unlink all
    fault-injected) → `write_outcome` False, workbook preserved, no final sidecar, `.tmp` RETAINED,
    `read_completion` `partial`; **subsequent matrix reuse** of that three-way-failed partial records
    `partial`; `_consolidate_store_folder` raises on a `False` return.
  - **`build/check_tsn_outcome.py`:** `build_consolidated` returns an error result on a `False` return.

### Updated verification
- **P1-R01:** all round-7 assertions green; each reverts to red — neutering the `read_completion` `.tmp`
  fallback makes the three-way-failed partial read a false-green (and the matrix reuse green); reverting the
  `_consolidate_store_folder` raise / the `build_consolidated` error-return lets each claim success.
- **Suite:** **56/56** Python checks + the Node renderer + byte-compile + `node --check app.js` +
  `check_app_modules` + `check_import_direction` + `check_b2_autoconsolidate` + all-workflow YAML +
  `git diff --check` all green. No UI files changed this round. `compare_core` / updater / auth untouched;
  HEAD still `65aef98` (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Before round-7 remediation | After |
|---|---|---|
| Partial workbook: publish + marker + unlink ALL fail (three-way) | sidecar-less workbook → `read_completion` None → false green | `.tmp` retained as sentinel → `read_completion` partial (no false green) |
| `matrix._consolidate_store_folder` on a `False` write | returned the success-shaped result (claimed persisted) | raises → comparison surfaces not-refreshed |
| `tsn_library.build_consolidated` on a `False` write | returned the success-shaped result | returns an error result (UI surfaces the failure) |
| Golden checks | 57 (56 Py + Node) | 57 (56 Py + Node; round-7 coverage added to `check_consolidate_outcome` + `check_tsn_outcome`) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial TSN normalization rendering the amber `mx-partial` cell live; a real mid-batch auth
failure after a completed environment showing the partial terminal; a real failed district-PDF TSN
consolidation surfacing the not-refreshed terminal (§M).

---

## Remediation — Review round 8 (Codex verdict: PASS WITH FIXES)

### Review round addressed
Codex P1 review **round 8** — **`PASS WITH FIXES`** (no blocking findings; P1-B01..B05 remain resolved,
P1-R01 otherwise resolved). One narrower P1-R01 write-stage branch: the round-7 retained-`.tmp` sentinel
assumes a VALID `.tmp` was written, but if `open(tmp)`/`json.dump` itself fails there is NO `.tmp` to
retain — and if the workbook unlink and the fallback marker ALSO fail, nothing durable is left → a
sidecar-less partial workbook reads `None` (legacy → complete). Plus one **non-blocking** recommendation
(**P1-A01**): validate the retained `.tmp` like the final sidecar (it was presence-only, so any stale
`<workbook>.outcome.json.tmp` forced `partial`). Both verified/reproduced; the correction stays confined to
the persistence boundary — no new abstraction.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01..B05** | **Resolved (prior rounds)** — no further action. |
| **P1-R01** — write-stage failure leaves an undeletable workbook false-green | **Fixed (with modification)** | The `write_outcome` failure path is now a full fallback **ladder**: (1) remove the workbook → rebuild; (2) direct `_mark_untrusted` marker; (3) retain a **USABLE** `.tmp` sentinel (validated, not presence-only); (4) **`_quarantine`** — when there is NO usable sentinel (the write-stage branch: `open(tmp)`/`json.dump` failed) and the workbook can't be removed, RENAME it aside so the canonical path resolves as MISSING (the resolver rebuilds; the data is preserved at `<workbook>.unverified`) — it can never read as a legacy-complete cell; (5) all-locked → a `log.critical`. So no `os`-failure combination leaves a non-complete workbook resolving green. |
| **P1-A01** *(non-blocking, applied)* — validate the retained `.tmp` sentinel | **Fixed** | A shared `_read_sidecar(path, consolidated)` validates BOTH the final sidecar AND the `.tmp` sentinel identically (schema / vocabulary / type / **mtime** vs the workbook): a valid-current sentinel → its completion; unreadable/corrupt/malformed → conservative `partial`; **demonstrably stale (mtime mismatch) → ignored (`None`)**. `_mark_untrusted`'s stale "only residual false-green window" wording + log are corrected (it is one rung of the ladder now). |

No findings rejected or deferred.

### Remediation changes
- **`scripts/consolidation_meta.py`** — new shared `_read_sidecar` validator (used by `read_completion` for
  the final sidecar AND the `.tmp` fallback, so the sentinel is mtime-validated — P1-A01); new `_quarantine`
  (rename-aside when no sentinel is possible and the workbook can't be removed); `write_outcome`'s failure
  path becomes the remove → marker → retain-usable-`.tmp` → quarantine → `log.critical` ladder; `read_completion`
  simplified to consult the final sidecar then the validated `.tmp`; `_mark_untrusted` wording/log corrected.
- **Tests (each fails on the pre-fix code — revert/run/restore-verified), in
  `build/check_consolidate_outcome.py`:** the **write-stage failure** (a path-filtered `builtins.open`
  denies the sidecar + `.tmp` writes, marker + unlink also fail) → `write_outcome` False, NO `.tmp`,
  workbook **quarantined** (canonical missing, data at `.unverified`), and **subsequent matrix reuse raises
  not-refreshed (never green)**; a **stale `.tmp` sentinel** is ignored (`None`, not forced `partial`) while
  a valid current sentinel reads `partial`.

### Updated verification
- **P1-R01:** the write-stage assertions green; each reverts to red — short-circuiting `_quarantine` leaves
  the sidecar-less workbook (canonical present, matrix reuse does not raise → would read green).
- **P1-A01:** neutering the shared mtime validation reds BOTH the new stale-sentinel test AND the round-2
  mtime-mismatch test (proving it is load-bearing).
- **Suite:** **56/56** Python checks + the Node renderer + byte-compile + `node --check app.js` +
  `check_app_modules` + `check_import_direction` + `check_b2_autoconsolidate` + all-workflow YAML +
  `git diff --check` all green. No UI files changed this round. `compare_core` / updater / auth untouched;
  HEAD still `65aef98` (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Before round-8 remediation | After |
|---|---|---|
| Write-stage failure (no `.tmp`) + marker + unlink all fail | sidecar-less workbook → `read_completion` None → false green | workbook QUARANTINED (canonical missing) → resolver rebuilds, never green |
| A retained `.tmp` sentinel | presence-only → ANY (even stale) `.tmp` forced `partial` | mtime-validated → stale ignored (`None`), corrupt → `partial`, current → its completion |
| Golden checks | 57 (56 Py + Node) | 57 (56 Py + Node; round-8 coverage added to `check_consolidate_outcome`) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial TSN normalization rendering the amber `mx-partial` cell live; a real mid-batch auth
failure after a completed environment showing the partial terminal; a real failed district-PDF TSN
consolidation surfacing the not-refreshed terminal (§M).

---

## Remediation — Review round 9 (Codex verdict: PASS WITH FIXES)

### Review round addressed
Codex P1 review **round 9** — **`PASS WITH FIXES`** (no blocking findings; P1-B01..B05 resolved, the
round-8 quarantine + P1-A01 resolved, P1-R01 otherwise resolved). One narrow sentinel-INTEGRITY case: the
fallback ladder's step 3 accepted **any** `.tmp` sentinel that wasn't absent/stale as conservative — which
includes a valid current `.tmp` whose recorded completion is **`complete`**. So a pre-existing `complete`
temp (unrelated debris) could certify a newly-FAILED `partial` write, bypassing quarantine and letting the
partial workbook render green. Verified/reproduced; a one-line predicate correction (no new abstraction,
per Codex's guidance).

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01..B05 / round-8 quarantine / P1-A01** | **Resolved (prior rounds)** — no further action. |
| **P1-R01** — a `complete` temp sentinel can certify a failed `partial` write | **Fixed** | The retain-sentinel rung now accepts a `.tmp` **only when it itself reads `partial`** (`_read_sidecar(tmp) == outcome.PARTIAL` — a valid current `partial`, OR a present-but-corrupt/unreadable → conservative `partial`). A valid current `complete` (or any non-`partial`) sentinel is **rejected as incompatible**, so the ladder continues to `_quarantine` — the canonical path resolves as MISSING and can never read green. |

No findings rejected or deferred.

### Remediation changes
- **`scripts/consolidation_meta.py`** — `write_outcome`'s step-3 predicate changed from
  `_read_sidecar(tmp, …) not in (_ABSENT, None)` to `== outcome.PARTIAL`, so only a sentinel that itself
  reads `partial` can protect a failed non-complete write; an incompatible `complete`/stale sentinel falls
  through to quarantine. Ladder comment updated.
- **Tests (fails on the pre-fix code — revert/run/restore-verified), in
  `build/check_consolidate_outcome.py`:** a pre-existing valid CURRENT `complete` `.tmp` is planted beside a
  workbook, then a PARTIAL write is forced to fail (a write-only-deny `builtins.open` keeps the planted tmp
  intact + readable; marker write denied; workbook/tmp deletion fail). Asserts `write_outcome` False, the
  workbook is **quarantined** (canonical missing, data at `.unverified`), `read_completion` never returns the
  false `complete`, and the SHARED matrix consumer (`consolidate_and_compare_tsn`, used by BOTH the Everything
  `build_comparison` and the by-day `build_day_cell`) **raises not-refreshed** — no green match.

### Updated verification
- **P1-R01:** the round-9 assertions green; reverting the predicate to the round-8 form
  (`not in (_ABSENT, None)`) reds 4 checks — the `complete` tmp certifies the failed partial (no quarantine →
  workbook present → `read_completion` returns the false `complete` → matrix produces a green match).
- **Suite:** **56/56** Python checks + the Node renderer + byte-compile + `node --check app.js` +
  `check_app_modules` + `check_import_direction` + `check_b2_autoconsolidate` + all-workflow YAML +
  `git diff --check` all green. No UI files changed this round. `compare_core` / updater / auth untouched;
  HEAD still `65aef98` (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Before round-9 remediation | After |
|---|---|---|
| A current `complete` `.tmp` beside a FAILED partial write | accepted as a sentinel → no quarantine → reads green | rejected as incompatible → quarantined → never green |
| Retain-sentinel predicate | `_read_sidecar(tmp) not in (_ABSENT, None)` (accepts `complete`) | `== outcome.PARTIAL` (only a conservative partial protects it) |
| Golden checks | 57 (56 Py + Node) | 57 (56 Py + Node; round-9 coverage added to `check_consolidate_outcome`) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial TSN normalization rendering the amber `mx-partial` cell live; a real mid-batch auth
failure after a completed environment showing the partial terminal; a real failed district-PDF TSN
consolidation surfacing the not-refreshed terminal (§M).

---

## Remediation — Review round 10 (Codex verdict: PASS WITH FIXES)

### Review round addressed
Codex P1 review **round 10** — **`PASS WITH FIXES`** (no blocking findings; P1-B01..B05, the round-8/9
quarantine + sentinel rejection, and P1-A01 all resolved). One narrow P1-R01 **read-precedence** case:
`read_completion` consulted the final sidecar first and returned it before the `.tmp`. So when a failed
partial publication retains a `partial` `.tmp` BUT the old final sidecar (`complete`) survives — and that
final still validates because the workbook was overwritten within the 1-second mtime tolerance / on a
coarse-resolution filesystem — the conservative sentinel was overridden and reuse rendered green. Verified/
reproduced; a read-precedence correction (no new abstraction).

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P1-B01..B05 / round-8/9 quarantine + sentinel rejection / P1-A01** | **Resolved (prior rounds)** — no further action. |
| **P1-R01** — a locked final `complete` sidecar overrode the retained partial sentinel | **Fixed** | `read_completion` now reconciles final and `.tmp` **conservatively**: a retained `.tmp` that reads `partial` (the most-recent, not-yet-promoted record of a FAILED partial publication) **DOMINATES** the final — even a final that says `complete` but is only stale-yet-within-tolerance. Order: an already-conservative final `partial` returns immediately; else a `partial` `.tmp` wins; else the final's validated value / `None`; else the `.tmp`'s value. The `.tmp` is still mtime-validated, so a genuinely stale `partial` `.tmp` does NOT override a legitimately current `complete` final. |

No findings rejected or deferred.

### Remediation changes
- **`scripts/consolidation_meta.py`** — `read_completion` reworked from "final-first, then `.tmp` only if
  the final is absent" to "a `partial` `.tmp` dominates; otherwise the final; otherwise the `.tmp`". Both
  are validated identically (schema/vocabulary/type/mtime), so stale sentinels stay ignored.
- **Tests (fails on the pre-fix code — revert/run/restore-verified), in
  `build/check_consolidate_outcome.py`:** a valid CURRENT `complete` FINAL sidecar is planted beside a
  workbook, then a PARTIAL write fails (a path-filtered `builtins.open` denies overwriting the FINAL but
  allows the `.tmp` write + reads; `os.replace` and the workbook/`.tmp` deletes fail) → both the
  `complete` final and the `partial` `.tmp` persist; asserts `write_outcome` False, `read_completion`
  returns **partial** (the `.tmp` dominates the stale `complete` final), and the shared
  `consolidate_and_compare_tsn` (Everything + by-day) records **partial** — never a green match.

### Updated verification
- **P1-R01:** the round-10 assertions green; neutering the "`partial` `.tmp` dominates" branch reds 2 checks
  — the stale `complete` final wins → `read_completion` returns `complete` → the matrix produces a green
  match.
- **Suite:** **56/56** Python checks + the Node renderer + byte-compile + `node --check app.js` +
  `check_app_modules` + `check_import_direction` + `check_b2_autoconsolidate` + all-workflow YAML +
  `git diff --check` all green. No UI files changed this round. `compare_core` / updater / auth untouched;
  HEAD still `65aef98` (not committed); P1 stays `awaiting_review`.

### Changed measurements
| Metric | Before round-10 remediation | After |
|---|---|---|
| Conflicting current final `complete` + retained `partial` `.tmp` | final wins (read first) → `complete` → green match | `partial` `.tmp` dominates → `partial` → never green |
| `read_completion` precedence | final-first; `.tmp` only when final absent | `partial` `.tmp` dominates → final → `.tmp` value (all mtime-validated) |
| Golden checks | 57 (56 Py + Node) | 57 (56 Py + Node; round-10 coverage added to `check_consolidate_outcome`) |

**External verification still owed (unchanged, not in DoD):** work-PC partial-keeps-last-good on a real
refresh; a real partial TSN normalization rendering the amber `mx-partial` cell live; a real mid-batch auth
failure after a completed environment showing the partial terminal; a real failed district-PDF TSN
consolidation surfacing the not-refreshed terminal (§M).
