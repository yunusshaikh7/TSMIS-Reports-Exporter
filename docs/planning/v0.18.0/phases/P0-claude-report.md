# P0 — Claude implementation report

**Status:** `awaiting_review`
**Phase:** **P0 — Safety net + diagnostics + doc-drift + dispatch defaults** (release-blocking)
**Branch:** `refactor/v0.18.0-structural-overhaul`
**Baseline commit:** `d2ee35333f3ebd3a070c1adfec893c10d2ffbe58` (`d2ee353`, tag `v0.17.1` baseline; clean tree)
**Not committed** — awaiting Codex `PASS`. Nothing staged; the planning folder remains untracked.

---

## 1. Objective (from `05` §I)

Additive guards + zero-risk fixes that de-risk every later phase: the two dispatch defaults (F8), the
CT-10 worker-lifecycle and import-direction diagnostic checks (R1-R14 + the P8 acyclicity tripwire),
doc-drift corrections, **plus** the two small **characterized** behavior fixes §J2 assigns here
(env-compare side-label preservation, Ramp Summary schema guard — RR3-C2).

## 2. Changes made

**Diagnostics / dispatch defaults (behavior-neutral):**
- `gui_api._handle`: added an `else` that logs `log.warning("unhandled worker event kind %r …", kind)`.
  Closes F8's "no default branch" silent drop — a protocol-drift event is now logged, never vanishes.
- `app.js dispatch`: replaced the silent `default: break;` with `default: console.warn("dispatch:
  unhandled event type", ev.t, ev); break;`. Known event kinds and event order are unchanged.

**New diagnostic checks (additive, blocking in CI):**
- `build/check_worker_lifecycle.py` (CT-10 / R1-R14): per-terminal-outcome **gate-release + queue-advance**
  lifecycle, asserted as behavior (gate state + queue length), not name membership — success
  (empty + real `RunResult`), cancel, error, **duplicate-late** (no wedge), and matrix queue advancement.
- `build/check_import_direction.py`: AST guard that `scripts/` has **no module-level import cycles**
  (Tarjan SCC) and no self-imports — the tripwire for the P8a/P8b engine split's acyclic DAG.

**Characterized behavior fix 1 — env-compare side-label preservation (`compare_env.py`):**
- Replaced the incidental `cap = lambda s: s[:23]` with `_cap_label()` (+ named `_SIDE_LABEL_CAP = 31 -
  len("Only in ") = 23`). It trims the **base**, preserving a trailing run-date or `(A)`/`(B)`
  distinguisher, so two same-source sides no longer collapse to the same prefix (and degrade to "Side
  A"/"Side B"). The previous comment **claimed** the distinguisher was preserved; the code only did so by
  accident. Locked by `build/check_compare_env_sidelabel.py`.

**Characterized behavior fix 2 — Ramp Summary Combined-sheet schema guard (`consolidate_ramp_summary.py`):**
- Added `_assert_combined_layout()` (+ row-anchor constants) called at the top of `build_combined_sheet`.
  The Combined sheet hand-places sections at fixed row anchors (On/Off=13, Population=19, Totals=28) sized
  for today's schema lengths; a schema-list length change would silently overrun the next section header.
  The guard turns that drift into a **loud `ValueError`**. No change to the verified layout literals or
  output. Locked by `build/check_ramp_summary_schema.py`.

**Doc-drift:**
- `gui_worker.py` module docstring + `CheckWorker` docstring: stale **Tkinter** references
  ("Tk main thread", "root.after()", "Tk widgets") → the pywebview/WebView2 reality (the GuiApi pump
  drains the queue and forwards via `evaluate_js`).
- `login.py`: dropped the stale "(Phase 4)" internal-milestone reference (the GUI shipped long ago).
- `docs/internals/gui-bridge.md` §8: corrected the 9 worker **class-header line ranges** + the ExportWorker
  `run()` anchor to current values (e.g. ExportWorker `:156-369` → `:222-459`, `run() :346` → `:434`).
- `docs/build-and-release.md`: updated the CI golden-check list to match the actual `checks.yml`
  (it was missing the matrix + TSN-compare + intersection checks) **and** the four new P0 checks.

**CI wiring (`.github/workflows/checks.yml`):**
- `check_worker_lifecycle` + `check_import_direction` added to the (renamed) "GUI-bridge + diagnostics"
  blocking step; `check_compare_env_sidelabel` + `check_ramp_summary_schema` added to the
  comparison-engine blocking loop. Suite is now **48** blocking checks (44 → 48).

## 3. Files affected

| File | Kind | Change |
|---|---|---|
| `scripts/gui_api.py` | product (behavior-neutral) | `_handle` `else` log (F8) |
| `scripts/ui/app.js` | product (behavior-neutral) | dispatch `default` warn (F8) |
| `scripts/compare_env.py` | product (**characterized** behavior) | `_cap_label` distinguisher-preserving cap |
| `scripts/consolidate_ramp_summary.py` | product (**characterized** behavior, additive guard) | `_assert_combined_layout` tripwire |
| `scripts/gui_worker.py` | doc (docstring) | Tkinter → pywebview |
| `scripts/login.py` | doc (docstring) | drop "Phase 4" |
| `docs/internals/gui-bridge.md` | doc | §8 worker class-header line numbers |
| `docs/build-and-release.md` | doc | CI check list reconciled + new checks |
| `.github/workflows/checks.yml` | CI | wire the 4 new checks (blocking) |
| `build/check_worker_lifecycle.py` | new test | CT-10 |
| `build/check_import_direction.py` | new test | acyclicity guard |
| `build/check_compare_env_sidelabel.py` | new test | side-label characterization |
| `build/check_ramp_summary_schema.py` | new test | schema-guard characterization |

9 modified + 4 new. (Plus the untracked `docs/planning/` workspace — **not** part of this phase's product diff.)

## 4. Architectural decisions

- **CT-10 tests the invariant, not the worker list.** It drives terminal events through the real
  `GuiApi._handle`/`_end_task`/`_try_start_next_matrix_job` and asserts gate-release + queue-advance —
  exactly the contract the P7a `TaskCoordinator` extraction must preserve. Matrix dispatch is monkeypatched
  to a recorder so no browser/thread launches.
- **Import-direction guard checks MODULE-LEVEL imports only** (function-local/deferred imports can't form
  an import-time cycle). Verified the current graph (53 modules) is already acyclic, so the check is green
  at P0 and becomes the guard for P8a/P8b.
- **Ramp Summary guard is additive.** It does **not** rewrite the hand-tuned layout literals inside
  `build_combined_sheet` (those drive a COM-verified workbook). The guard's anchor constants mirror the
  layout and trip on schema-length drift — the failure mode the audit flagged.
- **Side-label fix makes an incidental guarantee explicit.** `s[:23]` only kept the distinguisher by luck
  of the pre-cap base length; `_cap_label` guarantees it and the check locks it.

## 5. Compatibility & migration handling

- **No persisted-data/format changes.** No `batch_job.json`/`config.json`/cache/output-layout touch.
- **Dispatch defaults are additive** — known kinds and event order unchanged; the new branches only fire
  on an otherwise-silently-dropped unknown kind.
- **Side-label cap** preserves all current outputs (short labels unchanged; the realistic SRC-ENV+date
  labels are ≤ 23 already, so identical) and only changes the degenerate overflow case toward *more*
  provenance, never a sheet-name collision (the Side A/B fallback is retained).
- **Ramp Summary guard** is a no-op for the shipped schema (verified), output byte-identical.

## 6. Tests & commands run

```
python -m compileall -q scripts build version.py          # byte-compile gate (CI step 1) — OK
node --check scripts/ui/app.js                            # JS syntax — OK
PYTHONIOENCODING=utf-8  python build/check_*.py  (×48)     # full suite — 48/48 PASS
#mock preview boot (port 8765 /index.html#mock):
  - cache-busted app.js/app.css reload, navigate to #mock
  - S defined (tab=export), dispatch() defined, 10 tabs, no console errors
  - dispatch([{t:'log',…}]) known-event OK; dispatch([{t:'__unknown__'}]) → console.warn, no throw
  - screenshot: full GUI renders (Export tab, all 7 reports, activity log)
```

## 7. Results

- **48/48 golden checks green** (44 baseline + 4 new). Byte-compile clean. `node --check` clean.
- **`#mock` boots cleanly** — no console errors; the new `default` warns on an unknown event and leaves
  known dispatch unaffected (verified live).
- The two characterization checks prove the behavior fixes (distinguisher preserved + capped; guard passes
  for the real schema and raises on each schema-list growth).

## 8. Before / after measurements

| Metric | Before (`d2ee353`) | After (P0) |
|---|---|---|
| Blocking golden checks | 44/44 | **48/48** |
| `gui_api._handle` unknown kind | silently dropped | logged (`log.warning`) |
| `app.js` unknown event | silently dropped | `console.warn` |
| `scripts/` module-level import cycles | (unguarded) | **0**, now guarded |
| compare_env side-label overflow | distinguisher truncated (incidental) | distinguisher preserved (guaranteed) |
| Ramp Summary schema drift | silent Combined-sheet corruption | loud `ValueError` |

(Cold-start / matrix-snapshot perf baselines per R1-A01 are deferred to the first phase that touches a hot
path — P0 changes no hot path. Noted so it is not silently skipped.)

## 9. Deviations from the approved plan

1. **`gui-bridge.md` §8 — class-header anchors fixed; deeper inline refs deferred to P11.** I corrected the
   9 worker class-header line ranges + the ExportWorker `run()` anchor (the high-value clickable anchors).
   The section's deep method-level refs (`_run_specs`, `_on_route`, the `gui_api.py:NNN` cross-refs) remain
   approximate: P7a/P7b restructure exactly this code and would re-stale any numbers pinned now, so
   re-pinning them belongs in P11's post-restructure doc pass. Flagged rather than silently skipped.
2. **Commit boundary (RR3-C2).** When committed (after PASS) P0 is **three** isolated commits, each
   independently green: (A) diagnostics + dispatch defaults + doc-drift + their 2 checks/CI wiring;
   (B) the side-label fix + `check_compare_env_sidelabel` + its CI line; (C) the Ramp Summary guard +
   `check_ramp_summary_schema` + its CI line. The two behavior changes are isolated per RR3-C2.

No scope expansion; no product behavior beyond the two characterized fixes.

## 10. Known limitations & external verification

- **No work-PC verification required for P0** — every change is offline-verifiable (CI golden checks +
  `node --check` + `#mock`). P0 touches no live auth/browser/export path.
- The side-label fix's realistic inputs never overflow today (SRC-ENV+date ≤ 23), so the fix is forward-
  hardening + a corrected contract; the synthetic-overflow path is exercised by the new check.

## 11. Exact diff scope for Codex to review

- `scripts/gui_api.py` — +6 lines, the `_handle` `else` log branch.
- `scripts/ui/app.js` — the dispatch `default` (silent → `console.warn`).
- `scripts/compare_env.py` — `_SIDE_LABEL_CAP` + `_cap_label` + the cap call-site/comment.
- `scripts/consolidate_ramp_summary.py` — `_assert_combined_layout` + constants + the one call line
  (no change to `build_combined_sheet`'s layout literals).
- `scripts/gui_worker.py`, `scripts/login.py` — docstring text only.
- `docs/internals/gui-bridge.md` — §8 worker class-header line numbers only.
- `docs/build-and-release.md` — the CI golden-check list block only.
- `.github/workflows/checks.yml` — +4 check invocations (one step renamed).
- `build/check_worker_lifecycle.py`, `build/check_import_direction.py`,
  `build/check_compare_env_sidelabel.py`, `build/check_ramp_summary_schema.py` — new test files.

`git diff --stat` vs `d2ee353`: 9 files changed, +119/−30, plus 4 new `build/check_*.py`. Suggested review
order: the two behavior fixes (compare_env, consolidate_ramp_summary) + their checks first, then the
dispatch defaults + CT-10, then the docs/CI.

---

# Remediation — Codex review round 1 (`BLOCKED`)

**Round addressed:** P0 Codex review **round 1** ([`P0-codex-review.md`](P0-codex-review.md)), verdict
`BLOCKED` — 1 blocking, 3 required, 2 non-blocking. Every finding was verified against the workspace before
fixing. The original report above is unchanged; this section records the remediation.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P0-B01 | blocking | **Fixed (CT-10 scope)** + **Deferred (the fix → P7a)** | CT-10 rewritten to a real per-worker contract; the duplicate-late-active-successor *correctness fix* is sequenced to P7a (exactly-once), recorded as coordination D21 |
| P0-R01 | required | **Fixed** | import-direction guard now descends module-scope `try`/`if`, keeps self-edges, and self-tests its own detection |
| P0-R02 | required | **Fixed** | removed the 3 "silent drop" statements; corrected all 10 §8 anchors (the off-by-one + EnvScanWorker); added `check_no_misspelling` to the documented CI list |
| P0-R03 | required | **Fixed** | cold-start + matrix-snapshot baselines recorded with R1-A01 metadata |
| P0-A01 | non-blocking | **Fixed** | guard wording narrowed from "length change" to "growth past the row budget / overlap" |
| P0-A02 | non-blocking | **Acknowledged** | three-commit isolation plan reaffirmed (verifiable only at commit time) |

### P0-B01 — verified, and split into a fix + a sequenced deferral
**Verified real.** `_end_task` (`scripts/gui_api.py`) clears `_task`/`_current_job` unconditionally, so a
straggler/duplicate terminal arriving *after* a queued successor has started clobbers the successor. The
prior CT-10 only tested the idle-duplicate case and so did not characterize this.
- **CT-10 scope — Fixed.** `build/check_worker_lifecycle.py` is rewritten as a **per-worker terminal
  contract** over **15 worker/terminal combinations** (Export/Login/Consolidate/Batch/Reset/Chromium/Matrix-
  compare/Matrix-export + login terminals), each covering success / cancel / expected-failure /
  unexpected-failure, plus queue-advance, duplicate-late-**idle**, and duplicate-late-**active-successor**.
  The active-successor case now **reproduces and LOCKS** the defect: it asserts the precondition (successor
  is the running task), then asserts the duplicate **clobbers** it — marked `[known gap: P7a]`. It does **not**
  claim the interaction is safe (no weakened idle-only assertion).
- **The correctness fix — Deferred to P7a.** Making that case safe requires exactly-once / identity-guarded
  terminal delivery, which the approved plan assigns to **P7a's TaskCoordinator** (R1-R06 / R1-R14,
  "exactly-once transitions") — it is **not** a third P0 behavior delta. This is the
  "coordination-approved sequencing change" Codex offered, recorded as **D21** in `00-coordination.md`.
  When P7a lands, `test_duplicate_late_active_successor` flips (P7a's report will update it).

### P0-R01 — import-direction guard false negatives — Fixed
Both defects confirmed: the `col_offset == 0` filter missed module-scope `try`/`if`/`with` imports, and
`return deps - {path.stem}` made the self-loop assertion vacuous. `build/check_import_direction.py` now walks
module-executed statement bodies (descending compound statements, **skipping** function/class bodies),
**keeps self-edges**, and adds **6 self-tests** proving it detects: a direct self-import, a module-scope
`try`-import, a module-scope conditional import, that a function-local import is ignored, a cycle expressed
through `try`/conditional imports, and a self-loop. Re-run on HEAD: still **53 modules, 0 self-imports, 0
cycles** (a corrected — no longer vacuous — green).

### P0-R02 — gui-bridge doc contradicts the code + stale anchors + missing CI entry — Fixed
- Removed all **three** "silently dropped" statements (`gui-bridge.md:74, 411, 426`); they now state that an
  unknown `kind` hits `_handle`'s `else` and is **logged** (P0), and the stale `gui_api.py:392-480` /
  `app.js:1428` refs were corrected to `gui_api.py:462-564` / `app.js:1482`.
- **Root cause of the off-by-one:** my own P0 docstring edit added one line to `gui_worker.py`, shifting every
  class below it by +1 *after* I computed the anchors. Re-derived against the **final** file and corrected all
  **10** worker headings + the ExportWorker `run()` anchor, including **EnvScanWorker** (was missing: `815-1068`
  → `904-1162`). A scripted cross-check now confirms every doc anchor's start+end equals the actual class
  range (10/10 OK).
- Added the **Product-name guard** (`check_no_misspelling.py`) to the `docs/build-and-release.md` blocking CI
  inventory.

### P0-R03 — performance baselines — Fixed (recorded, not deferred)
Recorded reproducible baselines for the two targets Codex named, with R1-A01 metadata (see **Changed
measurements**). The prior unilateral deferral is withdrawn.

### P0-A01 — guard wording — Fixed
`_assert_combined_layout`'s comment/docstring and `check_ramp_summary_schema`'s docstring/labels now say the
guard raises on **growth past the fixed row budget (overlap)** — shrinkage and in-budget growth are
explicitly allowed — instead of the over-broad "length change."

### P0-A02 — three-commit isolation — Acknowledged
Reaffirmed: on PASS, P0 is three independently-green commits — (A) diagnostics + dispatch defaults + doc-drift
+ their two diagnostic checks/CI wiring; (B) `compare_env._cap_label` + `check_compare_env_sidelabel` + its CI
line; (C) `consolidate_ramp_summary._assert_combined_layout` + `check_ramp_summary_schema` + its CI line.
Neither characterized behavior change is mixed into the diagnostics commit. Verifiable only at commit time.

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_worker_lifecycle.py` | rewritten — per-worker terminal contract + duplicate-late-active-successor gap LOCKED (P0-B01) |
| `build/check_import_direction.py` | rewritten — module-scope descent, self-edges kept, 6 detection self-tests (P0-R01) |
| `docs/internals/gui-bridge.md` | 3 silent-drop statements corrected; 10 worker anchors + EnvScanWorker fixed (P0-R02) |
| `docs/build-and-release.md` | added `check_no_misspelling` to the CI list (P0-R02) |
| `scripts/consolidate_ramp_summary.py` | guard comment/docstring wording narrowed to "growth past budget" (P0-A01) |
| `build/check_ramp_summary_schema.py` | docstring/labels narrowed to "growth past budget" (P0-A01) |

No new product behavior introduced by the remediation (the two approved behavior deltas are unchanged; the
duplicate-late fix is deferred to P7a, not added here).

## Updated verification

```
python -m compileall -q scripts build version.py        # OK
PYTHONIOENCODING=utf-8  python build/check_*.py  (×48)   # 48/48 PASS (post-remediation)
build/check_worker_lifecycle.py   — 26 assertions: 15 per-worker gate-release, 6 queue/idle, precondition
                                    + the 2 [known gap: P7a] active-successor locks — all green
build/check_import_direction.py   — 6 detection self-tests + 53-module graph (0 self, 0 cycles) — green
scripts/gui-bridge anchor cross-check (scripted) — 10/10 doc ranges == actual class ranges
```
`#mock` boot and `node --check` from the original run are unaffected (no `app.js`/UI change in the
remediation).

## Changed measurements

- **Golden checks:** 48/48 (unchanged count; the 2 rewritten checks are stronger — CT-10 went from 13 to 26
  assertions and now covers every gate-owning worker family + the active-successor gap; import-direction went
  from 2 vacuous-ish assertions to 6 real detection self-tests + the graph check).
- **P0 performance baselines (R1-A01)** — environment: Python 3.11.0 (64-bit), Windows 10 (AMD64), AMD Ryzen.
  Data shape: `batch_dest` = `output/All Reports (current)` (2 day-folders), matrix baseline `ssor-prod`,
  snapshot 4 rows. In-process (modules pre-imported), 9 repeats; cold-start measured with the GitHub update
  check and browser probes stubbed (deterministic startup, not network/IO latency):

  | Target | min | median | p95 | max |
  |---|---|---|---|---|
  | cold-start `GuiApi()` + `get_initial_state()` (fresh instance/repeat) | 8.71 ms | **9.08 ms** | 10.14 ms | 10.26 ms |
  | matrix-snapshot `matrix_info()` (warm) | 6.01 ms | **6.21 ms** | 7.01 ms | 7.09 ms |

  Reproduce: the inline harness in this turn's transcript (stubs `GuiApi._start_update_check` /
  `_start_checks_locked`, times `GuiApi()+get_initial_state()` fresh per repeat and `matrix_info()` warm,
  reports min/median/p95/max over 9 repeats). These are regression baselines for later phases; P0 changes no
  hot path, so no before/after delta is expected.

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review. Not committed; planning folder
untracked.

---

# Remediation — Codex review round 2 (`BLOCKED`)

**Round addressed:** P0 Codex review **round 2** ([`P0-codex-review.md`](P0-codex-review.md)), verdict
`BLOCKED`. Round 2 accepted the round-1 fixes (import guard, anchors, CI inventory, wording) and the **D21**
P7a deferral, and re-blocked on three points: CT-10 still tested only handler injection (not producer
paths) and omitted two worker families; the protocol "master map" omitted four real kinds; and the
"cold-start" baseline was a warm constructor measurement. All verified against the workspace before fixing.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P0-B01 | blocking | **Fixed** | CT-10 rewritten to **producer-path**: each gate-owning worker's real `run()` runs with stubbed collaborators; assert exactly-one-terminal per outcome, then feed it through `_handle` and assert gate release. 11 worker classes / 21 producer scenarios incl. the required EnvCheck + EnvScan families. D21 known-gap retained. |
| P0-R02 | required | **Fixed** | Added the four missing protocol rows (`active_env_done`, `matrix_cell`, `matrix_done`, `matrix_export_done`) and corrected the discrepancy note (eight omitted kinds, not four). Cross-check: the table now maps **all 27** worker-posted kinds. |
| P0-R03 | required | **Fixed (with modification)** | Recorded a true **process-cold** baseline that includes `import gui_api`; relabelled the 9 ms number as warm init; preserved the harness as a committed tool. |
| P0-A02 | non-blocking | **Acknowledged** | Three-commit isolation reaffirmed; verifiable only at commit time. |

### P0-B01 — CT-10 now exercises the producer path
**Verified.** The prior CT-10 only injected terminal messages into `_handle`; it never ran a worker's
`run()`, and `_terminal_contract` omitted `EnvCheckWorker`/`env_shot` (started by `verify_environment`,
`_task="envcheck"`) and `EnvScanWorker`/`env_access_done` (started by `check_environments`,
`_task="envscan"`) — both confirmed gate-owning at `scripts/gui_api.py:2672,2724`.

`build/check_worker_lifecycle.py` is rewritten around a **producer-scenario table**. For each gate-owning
worker it stubs only the heavy collaborator at the worker's seam (e.g. `ExportWorker._run_specs`, the
injected `consolidate_fn`, `reset_targets`, `ChromiumWorker._download/_delete`, `new_authed_browser` +
a fake `sync_playwright`, `EnvScanWorker.check_one`, `_run_matrix_export_step`, `matrix.build_comparison`,
`day_matrix.build_day_cell`, `matrix.consolidate_tsn_pdfs`), **runs the real `run()` synchronously**,
captures the queue, and asserts **exactly one terminal of the expected kind** for the outcome — then feeds
that terminal through `GuiApi._handle` and asserts the gate frees. Coverage:

- **11 worker classes, 21 producer scenarios:** ExportWorker (success / expected-error[`AuthError`] /
  unexpected-error / partial→`export_partial`+`error`), ConsolidateWorker (success / error), ResetWorker
  (success / cancel), ChromiumWorker (success / cancel / error), **EnvCheckWorker (success / expected-error
  → `env_shot`)**, **EnvScanWorker (success → `env_access_done`)**, BatchWorker (success / `AuthError`),
  MatrixBatchExportWorker (success / `AuthError`), MatrixCompareWorker, DayMatrixCompareWorker,
  MatrixTsnConsolidateWorker.
- **11 payload-encoded cancel/error variants** fed through `_handle` (the ones Codex flagged: `batch_done`
  cancel/incomplete, `reset_done` cancel/error, `chromium_done` cancel/error, `matrix_done` cancel/error,
  `matrix_export_done` cancel, `env_access_done` cancel, `env_shot` error) — each frees the gate.
- **Queue-advance**, **duplicate-late-idle**, and the **duplicate-late-active-successor** D21 known-gap
  (retained, still LOCKED with `[known gap: P7a]`).
- **LoginWorker** is the one gate-owning worker not producer-tested, with an in-file justification: its
  `run()` is a multi-browser device-SSO/Chromium/Edge-recapture/Chrome-fallback state machine
  (deterministic stubbing ≈ rebuilding the whole Playwright + device-sign-in stack — P7a / work-PC
  territory); its terminal kinds are covered by the payload-variant gate-release rows.

The deliberately-triggered worker error paths call `log.exception(...)`; the check now does
`logging.disable(logging.CRITICAL)` so those expected tracebacks don't spam CI. **P0 does not implement the
P7a exactly-once fix** (per D21).

### P0-R02 — protocol "master map" completeness — Fixed
**Verified.** The §3 table omitted `active_env_done` (`_on_active_env_done`), `matrix_cell`
(`_on_matrix_cell`), `matrix_done` (`_on_matrix_done`), `matrix_export_done` (`_on_matrix_export_done`),
and the discrepancy note at `:102` claimed the worker docstring omits only four kinds when it omits those
plus the four above (eight total). Added the four rows (handler / JS-event / renderer accurate to current
lines) and rewrote the note to enumerate all eight. A scripted cross-check now confirms the table maps
**every one of the 27 worker-posted `self.q.put` kinds**; the only `kind ==` strings not in the table
(`auth`, `compare`, `export`, `tsn_consolidate`) are the error sub-kind and matrix-job dispatch keys, not
worker→pump messages. (The table's other per-row deep line refs remain the explicitly P11-deferred churn.)

### P0-R03 — true process-cold baseline — Fixed (with modification)
**Verified.** The prior number pre-imported modules and timed only `GuiApi()+get_initial_state()`, excluding
the `import gui_api` eager-import cost that F11 / the P10 lazy-import work target. New committed tool
**`build/measure_baselines.py`** (a measurement tool, **not** a `check_*` — not wired into `checks.yml`)
spawns a fresh process per repeat that times `import gui_api` **and** the stubbed init, plus a warm
`matrix_info()` pass. Reproduce: `python build/measure_baselines.py --repeats 7`. This brings the dominant
cost into the baseline (≈1.45 s import), matching Codex's independent 1160–1561 ms; the 9 ms figure is kept,
relabelled warm.

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_worker_lifecycle.py` | rewritten — producer-path table (21 scenarios/11 workers) + payload variants + log-silencing (P0-B01) |
| `docs/internals/gui-bridge.md` | added 4 protocol rows + corrected the 8-kind discrepancy note (P0-R02) |
| `build/measure_baselines.py` | **new** reproducible R1-A01 baseline tool (P0-R03) |

No new product behavior; no change to the two approved behavior deltas. (`build/measure_baselines.py` is a
dev tool, not shipped, not a CI gate.)

## Updated verification

```
python -m compileall -q scripts build version.py        # OK
PYTHONIOENCODING=utf-8  python build/check_*.py  (×48)   # 48/48 PASS
build/check_worker_lifecycle.py — 63 assertions: 42 producer (21 scenarios × emit+gate-release),
                                   11 payload variants, 6 queue, 1 idle-dup, 3 active-successor — all green
protocol-table completeness cross-check (scripted) — table == all 27 worker-posted kinds
```

## Changed measurements

- **CT-10 strength:** 26 → **63** assertions; from handler-injection only to **real `run()` producer paths**
  across 11 worker classes (incl. the two previously-absent env families) + 11 payload-encoded
  cancel/error variants.
- **P0 startup baseline (R1-A01), corrected — process-COLD (fresh process per repeat, 7 repeats; GitHub
  update check + browser probes stubbed):**

  | Measurement | min | median | p95 | max |
  |---|---|---|---|---|
  | `import gui_api` (eager dep-graph; F11 / P10 target) | 1319.89 ms | **1442.94 ms** | 1722.47 ms | 1752.67 ms |
  | stubbed `GuiApi()+get_initial_state()` (warm init) | 12.59 ms | 13.55 ms | 15.97 ms | 16.47 ms |
  | **TOTAL cold startup** | 1333.03 ms | **1456.49 ms** | 1737.78 ms | 1769.14 ms |
  | `matrix_info()` (warm, in-process) | 6.23 ms | **6.89 ms** | 7.77 ms | 7.86 ms |

  Environment: Python 3.11.0 (64-bit), Windows 10 (AMD64). Data shape: 2 output day-folders, baseline
  `ssor-prod`. The import dominates cold start (matching Codex's 1160–1561 ms) — this is the regression
  baseline the P10 lazy-import work will be measured against.

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 3). Not committed; planning
folder untracked.

---

# Remediation — Codex review round 3 (`BLOCKED`)

**Round addressed:** P0 Codex review **round 3** ([`P0-codex-review.md`](P0-codex-review.md)), verdict
`BLOCKED`, **narrowed to one worker**. Round 3 confirmed **P0-R02 and P0-R03 resolved** and the D21 deferral
accepted; it re-blocked only on **P0-B01 — LoginWorker** being the single gate-owning worker still outside
the producer path (with an *inaccurate* "covered by the gate-release variants" claim, since the variant
table has no `login_*` rows). Verified against the workspace before fixing.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P0-B01 | blocking | **Fixed** | LoginWorker now has offline real-`run()` producer scenarios for all its terminals; the inaccurate exclusion/coverage statement is removed |
| P0-R02 | required | **Resolved (round 2; Codex-confirmed round 3)** | table maps all 27 worker kinds; discrepancy note lists all 8 omissions — no further change |
| P0-R03 | required | **Resolved (round 2; Codex-confirmed round 3)** | `build/measure_baselines.py` reproducible process-cold baseline — no further change |
| P0-A02 | non-blocking | **Acknowledged** | three-commit isolation reaffirmed; verifiable at commit time |

### P0-B01 — LoginWorker producer path — Fixed
**Verified.** `check_worker_lifecycle.py` explicitly excluded LoginWorker, yet `GuiApi.start_login` sets
`_task="login"` and starts it (`scripts/gui_api.py:2629`), and the claim that its terminals were "covered by
the gate-release variants" was false — `test_terminal_payload_variants` had no `login_saved` /
`login_device_ok` / `login_failed` rows. Codex's own diagnostic showed offline producer-testing is feasible.

LoginWorker is now producer-tested like every other gate-owning worker. **Six scenarios** run the real
`run()` / `_run_login_in_browser` offline and assert exactly-one-terminal, then feed it through `_handle`
for gate release:

| Outcome | Terminal | How it's driven (offline) |
|---|---|---|
| success | `login_saved` | fake Playwright browser; `new_login_context`→fake ctx, `is_logged_in`→True, `_save_state`→no-op (no auth-file write) |
| device mode | `login_device_ok` | no Chrome/Chromium launches → Edge fallback; `_try_edge_persistent_login`→fake state, `storage_state_is_portable`→False |
| no login detected | `login_failed` | fake browser; `is_logged_in`→False |
| cancellation | `cancelled` | fake browser; `cancel_event` set |
| expected error | `error` | `new_login_context` raises `BrowserNotFoundError` |
| unexpected error | `error` | `new_login_context` raises `RuntimeError` |

Key subtlety handled: `_run_login_in_browser` **clears** the done-event then waits on it, so a plain pre-set
`Event` would be cleared and hang. A small `_AlwaysDone` fake (clear() is a no-op, wait() returns
immediately) models an instant "I've finished logging in" click — no browser, no auth file, no P7a
exactly-once implementation. The inaccurate exclusion paragraph in the check's docstring is replaced with
the accurate description.

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_worker_lifecycle.py` | added 6 LoginWorker offline producer scenarios + `_AlwaysDone`/fake-Playwright login fakes; removed the inaccurate exclusion/coverage docstring (P0-B01) |

Only the CT-10 check changed; no product code, no doc change this round (P0-R02/R03 already resolved).

## Updated verification

```
python -m compileall -q scripts build version.py        # OK
PYTHONIOENCODING=utf-8  python build/check_*.py  (×48)   # 48/48 PASS
build/check_worker_lifecycle.py — 75 assertions, ALL GREEN; the 6 new LoginWorker scenarios each emit
                                  exactly one terminal (login_saved/login_device_ok/login_failed/cancelled/
                                  error×2) that frees the "login" gate via _handle
```

## Changed measurements

- **CT-10 coverage:** 11 → **12 gate-owning worker classes (no exclusions)**; 21 → **27 producer scenarios**;
  63 → **75 assertions**. LoginWorker is now producer-tested rather than justified-out.
- No performance-baseline change (P0-R03 unchanged from round 2).

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 4). Not committed; planning
folder untracked.
