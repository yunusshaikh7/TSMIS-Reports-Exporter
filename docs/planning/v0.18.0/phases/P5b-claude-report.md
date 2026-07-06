# P5b — TSN comparison-driver DRY (comparator remainder) — Claude report

## 1. Phase ID and name
**P5b — TSN comparison-driver DRY (comparator remainder).** The deferrable remainder of P5 (committed
family-1 `tsn_load` factory, `c0cfa39`), opted into v0.18.0 by **CR-001** and made **blocking** (RM01 — a new
post-P9 phase; the committed P5 row is NOT reopened). Collapse the five `compare_*_tsn` skeletons onto one
shared driver, behavior-neutral; `compare_core` untouched.

## 2. Baseline commit
`decced4` (`decced443faa70ef0807c3e80c37605ca0e5e5da`) — P9 committed; branch
`refactor/v0.18.0-structural-overhaul`; tree clean apart from the untracked `docs/planning/`.

## 3. Changes made
Extracted the duplicated skeleton shared by the five registry-"files" vs-TSN comparators into a new
**`scripts/compare_tsn_common.py`**, and reduced each comparator to **schema + projector**:

- **`run_files_compare(schema, tsmis_path, tsn_path, out_path, *, banner, has_route, loader, deps_ok, deps_msg, events, confirm_overwrite, mode)`** — the shared `compare()` driver: deps gate → path coercion + per-side existence check → the 6-line log banner → `loader(tsmis_path, tsn_path)` (may raise `ValueError`) → `compare_core.run_compare`. The report's `loader` returns `(rows_t, rows_n, warnings)`; a `warnings` of `None` is normalized to `run_compare`'s `()` default so the FLAT calls stay byte-identical, while the AGGREGATE list passes straight through.
- **`make_notes_writer(title, lines)`** — the identical orange-tabbed "Notes" legend sheet builder that Highway Sequence + Intersection Detail each open-coded (styling fixed; only title + body lines vary). openpyxl is imported lazily inside the returned writer, so the common module stays import-safe where the comparators' deps are absent.
- **`norm_pm` / `iso_date`** — the postmile + Date-of-Record normalizers Ramp Detail and Intersection Detail shared. `iso_date` is the 3-case superset (it carries Intersection Detail's 2-digit TSN year); behavior-neutral for Ramp Detail (its inputs never reach the 2-digit branch — proven by its canary).

Each comparator now: `import compare_tsn_common as ctc`; its `compare()` builds a tiny `_load_pair`/`_loader`
and calls `ctc.run_files_compare(...)`; the two FLAT-detail modules alias `_norm_pm = ctc.norm_pm` /
`_iso_date = ctc.iso_date`; Highway Sequence + Intersection Detail set `_write_notes_sheet =
ctc.make_notes_writer(title, lines)`. Every other public/internal name (the `_load_*`/`parse_tsn_pdf`/
`tsn_rows_from_raw` projectors, `_SCHEMA`, `SHARED_HEADER`, `NORMALIZED_SHEET`, `REPORT_NAME`,
`suggest_name`, `_CATEGORIES`, the FLAT `_v`/`_strip_desc_prefix`/`_glue_pm`/`_norm_county`/`_key_county_pm`)
is preserved verbatim. Newly-unused imports (`run_compare`, `ConsolidateResult`, `Events`, and the four
openpyxl style symbols in the two notes modules) were removed; `compare_tsn_common` was added to
`app.spec` APP_MODULES (F6 reachability) and a new check wired into the comparison-engine CI loop.

## 4. Files affected
**New (2):**
- `scripts/compare_tsn_common.py` (149 lines) — the shared substrate.
- `build/check_compare_tsn_common.py` (230 lines) — the golden lock (substrate behavior + delegation).

**Modified (7):**
- `scripts/compare_ramp_detail_tsn.py`, `scripts/compare_ramp_summary_tsn.py`,
  `scripts/compare_highway_sequence_tsn.py`, `scripts/compare_intersection_detail_tsn.py`,
  `scripts/compare_intersection_summary_tsn.py` — thinned to schema + projector + driver call.
- `build/app.spec` — `compare_tsn_common` added to APP_MODULES.
- `.github/workflows/checks.yml` — `check_compare_tsn_common` added to the comparison-engine loop.

## 5. Architectural decisions
- **One driver, two row-shapes via a `loader` hook.** FLAT comparators load rows directly; the two AGGREGATE summaries load category-count dicts then build rows + a parse-integrity warning. Rather than two drivers, `run_files_compare` takes a `loader(tsmis, tsn) -> (rows_t, rows_n, warnings)` that each report supplies — the FLAT loader returns `(…, …, None)`; the AGGREGATE loader keeps its report-specific warnings/rows build inside the (driver-owned) try. The post-load row/warning build moved inside the try, which is behavior-neutral (those list comprehensions raise no `ValueError`).
- **Names preserved via aliases/closures, not renames.** The five golden canaries call internals directly (`rd._norm_pm`, `idt._iso_date`, the `legend_writer`/"Notes" presence) and `tsn_load_*` import `rd.tsn_rows_from_raw`/`rstsn.parse_tsn_pdf`/`rstsn._CATEGORIES`. Aliasing (`_norm_pm = ctc.norm_pm`) and reassigning `_write_notes_sheet` to the `make_notes_writer` closure keeps every name resolvable with identical behavior — the "shims keep old names working" the plan calls for.
- **`warnings=None → ()` in the driver.** `run_compare`'s default is `()`, and FLAT comparators previously omitted the kwarg; AGGREGATE passed a list. The driver reproduces both exactly.
- **`compare_core` is not touched** (the notes helper lives in `compare_tsn_common`, outside the locked engine), honoring the regression lock and §N.
- **Scope of "header helpers" (deviation note in §10):** delivered the normalize (`norm_pm`/`iso_date`) and notes (`make_notes_writer`) helpers plus the driver; did **not** extract a shared consolidated-sheet loader, because each report's TSMIS loader reads by report-specific column positions/headers — a shared loader would add coupling, not remove duplication (KISS/YAGNI). The shared comparison *header* is the `CompareSchema`, which `run_files_compare` already routes.

## 6. Compatibility and migration handling
No persisted-data or format change — this is an internal refactor. The comparators' public surface
(module names, `compare`/`suggest_name`/`REPORT_NAME`/`_SCHEMA`, the projector functions, `SHARED_HEADER`,
`NORMALIZED_SHEET`) is unchanged, so the registry (`reports.py`/`report_catalog.py`/`matrix.py`), the
`tsn_load_*` normalizers, and the console/GUI drivers bind exactly as before. Output workbooks are
**semantically identical** (same schema, rows, banner, warnings, Notes sheet) — verified by the five vs-TSN
canaries. No migration required; per-module rollback is independent (revert one comparator and it restores
its in-line `compare()`); reverting `compare_tsn_common` would require reverting all six.

## 7. Tests and commands run
All via the build venv (`build/.venv/Scripts/python.exe -B -X utf8`).
- **Pre-change characterization (baseline `decced4`):** the 5 `check_compare_*_tsn.py` canaries — all GREEN.
- **RED proof:** wrote `build/check_compare_tsn_common.py`, ran it against the un-refactored modules → 16 delegation assertions FAILED as designed (substrate half passed). Then implemented the collapse → all GREEN. (The check's two halves: SUBSTRATE behavior + DELEGATION, the latter RED before the refactor.)
- **Targeted:** `check_compare_tsn_common.py` (GREEN after); the 5 vs-TSN canaries (still GREEN — semantic identity); `check_tsn_normalizer.py` (P5 family-1 — exercises the comparators' `tsn_rows_from_raw`/`parse_tsn_pdf`; GREEN); `check_app_modules.py` (reachability incl. the new module; GREEN); `check_import_direction.py` (no new cycle; GREEN).
- **Full offline suite:** every `build/check_*.py` (now 66 incl. the new one) — **66/66 pass**; the 3 Node checks (`check_ui_boot.js`, `check_compare_routing.js`, `check_mx_partial_render.js`) — all pass.
- **Hygiene:** byte-compile of all 6 touched scripts + the new check; `git diff --check` (product files) clean; grep confirms zero stale references to the removed imports; `checks.yml` `run: |` block indentation/continuation verified intact (PyYAML unavailable in the venv, so validated structurally).

## 8. Results
Green across the board: **66/66** Python checks + **3/3** Node checks; the 5 vs-TSN canaries semantically
identical before and after; the new substrate lock passes; reachability + import-direction + the P5
family-1 normalizer check pass. No `compare_core`/auth/updater/UI change.

## 9. Before/after measurements
| Module | Before (`decced4`) | After | Δ |
|---|---|---|---|
| compare_ramp_detail_tsn.py | 259 | 225 | −34 |
| compare_ramp_summary_tsn.py | 230 | 214 | −16 |
| compare_highway_sequence_tsn.py | 303 | 267 | −36 |
| compare_intersection_detail_tsn.py | 348 | 290 | −58 |
| compare_intersection_summary_tsn.py | 240 | 223 | −17 |
| **5-comparator total** | **1380** | **1219** | **−161** |
| compare_tsn_common.py (new, shared once) | — | 149 | +149 |

Product diff: **+108 / −268** across the 7 modified files. The duplicated `compare()` skeleton (≈30 lines ×5),
the Notes builder (≈40 ×2), and the two normalizers (≈20 ×2) now exist once. Offline check suite 65 → 66.

## 10. Deviations from the approved plan
- **"header helpers" interpreted conservatively.** §I/P5b lists "`run_files_compare` + normalize/notes/header helpers." I extracted the driver, the normalizers, and the notes builder, but **did not** extract a shared consolidated-sheet *loader* ("header" reader): each report reads its TSMIS sheet by distinct, position-specific maps, so a shared loader would increase coupling rather than remove real duplication. The shared comparison header is the `CompareSchema`, already centralized by the driver. Flagged for Codex; no behavior impact.
- **`iso_date` unified to the 3-case superset.** Ramp Detail's original was 2-case; the shared `iso_date` adds Intersection Detail's 2-digit-year branch. Behavior-neutral for Ramp Detail (its dates never reach that branch; its canary's two date assertions still pass).
- No other deviations. Each opt-in stayed inside P5b; `compare_core` untouched; no live access; nothing staged/committed/pushed.

## 11. Known limitations and external verification
- **Offline-only proof (by design).** Semantic identity is proven by the five canaries against synthetic fixtures + the structural lock. Per **RM07**, full **Route-1/COM-recalc** acceptance against the real TSMIS/TSN pairs is **external/work-PC** — but this phase changes **no comparison behavior** (the rows/schema/`run_compare` arguments are byte-identical), so the existing Route-1 regression lock is unaffected and no new work-PC item is created by P5b.
- **CR-001 scope (per Codex's required statement):** this phase implements **only P5b** (the P5 comparator-driver remainder, RM01). It deliberately leaves for later phases: **P7b** (GUI endpoints), **P8c** (engine behavior, v0.18.1 acceptance), **P9b** (frontend deep split), **expanded P10**, **P12** (audit hardening), **P13** (work-PC handoff), **P11** (docs). The hard-deferrals (DPAPI/O2, cert, `min-cost-pairs`) remain out.

## 12. Exact diff scope Codex should review
Product diff from baseline `decced4`, excluding `docs/planning/`:
- **New:** `scripts/compare_tsn_common.py`, `build/check_compare_tsn_common.py`.
- **Modified:** `scripts/compare_ramp_detail_tsn.py`, `scripts/compare_ramp_summary_tsn.py`,
  `scripts/compare_highway_sequence_tsn.py`, `scripts/compare_intersection_detail_tsn.py`,
  `scripts/compare_intersection_summary_tsn.py`, `build/app.spec`, `.github/workflows/checks.yml`.

Suggested focus: (a) confirm the five comparators' `compare()` outputs are byte-/semantically identical to
baseline (the canaries + the banner/warnings/`has_route`/`warnings=None→()` mapping in `run_files_compare`);
(b) confirm every preserved name (canary internals, `tsn_load_*` imports, registry surface) still resolves;
(c) confirm `compare_core` is untouched and the Notes text is verbatim; (d) judge the §10 "header helper"
scope interpretation.
