# P14 — Intersection Detail (PDF) report-family forward-port — Claude report

## 1. Phase ID and name
**P14 — Intersection Detail (PDF) report-family forward-port** (the exact `highway_log_pdf`
parallel), CR-002 / CR002-RM1/RM2/RM4/RM5/RM6/RM7. The §1–§7 plumbing + the §4 parser from
`origin/main` (v0.17.8, `068b697`), forward-ported into the refactored v0.18.0 sources of
truth — **not** a merge/rebase (CR002-RM7). The vs-TSN comparison **evolution** (§8/§9) is
explicitly **P15**, not this phase (CR002-RM5).

## 2. Baseline commit
`d15216d` (P12, "harden reset/consolidate file safety + add the PDF row oracle"). Branch
`refactor/v0.18.0-structural-overhaul`; clean tree apart from the untracked `docs/planning/`
workspace. Pre-change characterization: the full on-disk `build/check_*.py` suite + 3 Node
checks were green at baseline (the only failure is the documented untracked Codex review file
`docs/planning/v0.18.0/phases/P10-codex-review.md:177`, which contains the product-name
transposition inside an example rg command; the authoritative tracked-content guard — a
`git grep` for the transposed name — is clean). HEAD is **unchanged** by this phase (not
committed — awaiting Codex review).

## 3. Changes made
The Intersection Detail (PDF) report is now registered + wired at full HL-PDF parity:

- **Source of truth (RM1).** The report is added to `report_catalog.py` (the ONE SoT): one
  EXPORT row (appended last), one CONSOLIDATE row (grouped next to its Excel sibling), and
  **three** COMPARE rows (cross-env + PDF-vs-TSN + PDF-vs-Excel). `reports.py` is unchanged —
  it derives EXPORT/CONSOLIDATE/COMPARE + `matrix_rows()` from the catalog, so all the derived
  views, the GUI bridge payload, and the stable-ID lookups update automatically.
- **Four new modules** mirror the HL-PDF sibling: `export_intersection_detail_pdf.py`,
  `intersection_detail_columns.py` (the 36-col header SoT), `compare_intersection_detail_pdf.py`
  (PDF-vs-TSN + PDF-vs-Excel adapters reusing `compare_intersection_detail_tsn`'s loaders/schema),
  and the genuinely-new `consolidate_tsmis_intersection_detail_pdf.py` (the 2-row/zebra-shaded
  PDF parser).
- **Engine wiring.** `exporter.save_intersection_detail_pdf` (the `intd_printAll` print-layout
  save); `matrix.py` — a new `_pdf_store_consolidator(subdir)` helper used by BOTH
  `_consolidate_store_folder` and `_consolidated_filename` (closing the v0.17.4 by-day crash
  class by construction), the `intersection_detail_pdf` `_row_modes` branch (env + tsn +
  vs_excel), `tsn_comparator_for`, and a generalized `_pdf_self_comparator(pdf_subdir)` that
  replaces the literal `compare_highway_log_pdf` reference in the self mode; `compare_env.py`
  (`INTERSECTION_DETAIL_PDF` + `_load_intersection_detail_pdf_side`); `day_matrix.py` (the
  `fmt="pdf"` branch); `gui_worker.py` reset-cleanup parity (export folder + scratch dir +
  consolidated workbook).
- **Frontend (RM2).** All `#mock` fixtures (export/consolidate/compare lists + both matrices'
  rows/modes/sample data + per-row TSN dataset mapping) go into `scripts/ui/mock.js`. `app.js`
  is **not** touched — it still has zero `makeMockApi` references.
- **Stable-ID compat (RM4).** `batch_manifest._V017_EXPORT_ORDER` gains `intersection_detail_pdf`
  at index 7 (append-only; positions 0–6 preserved) so a v0.17.8 user's v1 (integer-index)
  manifest with index 7 still migrates to the right key instead of being poisoned.
- **Packaging/console (RM6).** `build/app.spec` `APP_MODULES` += the 4 new modules; the literal
  `4. consolidate (combine reports).bat` gains a new choice 6 (Intersection Detail (PDF)),
  renumbering the Highway Log options to 7/8/9. The **export** `.bat` menus need no edit — they
  derive from `EXPORT_REPORTS` via `export_multi.REPORTS` (proven by `check_source_zip_smoke`).
  `version.py` is **not** ported (stays the refactor's target).
- **Checks.** New `build/check_intersection_detail_pdf.py` + `build/fake_site/intersection_detail_print.html`;
  `check_report_catalog` baseline + `check_stable_ids` + `check_fake_site` + `check_intersection_gate`
  + the three matrix checks + `check_compare_env_highway_log_pdf` reconciled; `checks.yml` wired.

## 4. Files affected
**New product modules (6):** `scripts/intersection_detail_columns.py` (34),
`scripts/export_intersection_detail_pdf.py` (54),
`scripts/consolidate_tsmis_intersection_detail_pdf.py` (508),
`scripts/compare_intersection_detail_pdf.py` (106), `build/check_intersection_detail_pdf.py`
(140), `build/fake_site/intersection_detail_print.html` (63).

**Modified (19; +399/−84):** `scripts/report_catalog.py`, `scripts/exporter.py`,
`scripts/matrix.py`, `scripts/compare_env.py`, `scripts/day_matrix.py`,
`scripts/gui_worker.py`, `scripts/batch_manifest.py`, `scripts/ui/mock.js`, `build/app.spec`,
`4. consolidate (combine reports).bat`, `.github/workflows/checks.yml`, and the checks
`check_report_catalog.py`, `check_stable_ids.py`, `check_fake_site.py`,
`check_intersection_gate.py`, `check_matrix.py`, `check_matrix_bridge.py`,
`check_matrix_tsn.py`, `check_compare_env_highway_log_pdf.py`. `reports.py` is **unchanged**
(fully derived).

## 5. Architectural decisions
- **Mirror the refactored sibling, not `origin/main`'s structure (RM7).** The
  `consolidate_tsmis_intersection_detail_pdf` parser is ported from `origin/main` (the
  genuinely-new logic), but adapted to the **refactored** HL-PDF consolidator's shape: it gains
  the P12 TOCTOU gate (`existed_at_confirm` threaded into `consolidate_xlsx`'s pre-replace
  `atomic_save_if`) and the P1 `outcome.PARTIAL` escalation (orphan/failed PDFs → `partial`, so
  incomplete output isn't promoted/cached/compared as complete) — both of which `origin/main`'s
  pre-refactor version lacked. This keeps the two PDF consolidators structurally identical in
  the refactored tree.
- **DRY the PDF-report wiring.** The refactored `matrix.py` hardcoded
  `if subdir == "highway_log_pdf"` in two places plus a literal self-comparator import. Adding
  the second PDF family is the natural trigger to extract `_pdf_store_consolidator(subdir)` (used
  by both consolidated-filename + store-consolidate paths) and `_pdf_self_comparator(pdf_subdir)`
  — eliminating the v0.17.4 crash class by construction rather than re-introducing a third
  literal branch.
- **Append-only everywhere (RM4).** The export row, `_V017_EXPORT_ORDER`, the cross-env matrix
  row, and the compare rows are all appended so the existing 7-report shape (export keys 0–6,
  matrix rows 1–7) is byte-for-byte unchanged. The new env-folder compare row is placed LAST
  among env rows, so the matrix row order is the previous 7 + the new row at index 8.
- **`compare_core` untouched (RM3 anticipation).** The new comparators reuse
  `compare_intersection_detail_tsn`'s schema/loaders via `dataclasses.replace`; no `compare_core`
  change. The §8/§9 vs-TSN evolution (incl. the dormant `context_fill` that CR-002 does NOT
  port) is P15's scope, not this phase.

## 6. Compatibility and migration handling
- **Manifest v1 (integer index):** a pre-Int-PDF v0.17.1 manifest (indices 0–6) migrates to the
  seven original keys unchanged; a v0.17.8-era manifest carrying index 7 now migrates to
  `intersection_detail_pdf` (was previously out-of-range → poisoned). Locked by the new
  `check_stable_ids.test_v017_append_only_compat`.
- **Caches/stores:** none. The matrix `row_key` is the new family key; no existing cache key
  changes. The new report's stores/comparisons live under their own subdirs.
- **Reset cleanup:** the new export folder, scratch converted dir, and consolidated workbook are
  added to "Delete all reports" (parity with HL-PDF), so the new report's artifacts are cleaned.
- **`compare_core` regression lock:** intact — no change to the engine; the existing Route-1
  Highway Log canary and `check_compare_audit` stay green.

## 7. Tests and commands run
- Byte-compile: `python -m py_compile scripts/*.py build/*.py` → clean.
- The **complete** on-disk `build/check_*.py` suite (73 files) + the 3 Node checks
  (`check_compare_routing.js`, `check_mx_partial_render.js`, `check_ui_boot.js`).
- The Codex-required P14 list, each confirmed passing:
  `check_intersection_detail_pdf`, `check_report_catalog`, `check_stable_ids`, `check_fake_site`,
  `check_intersection_gate`, `check_matrix`, `check_matrix_bridge`, `check_matrix_tsn`,
  `check_day_matrix`, `check_gui_bridge`, `check_app_modules`, `check_import_direction`,
  `check_source_zip_smoke`, `check_ui_boot.js`.
- Regression spot-checks: `check_compare_intersection_detail_tsn`, `check_compare_audit`,
  `check_compare_env_intersection`, `check_consolidate_intersection`, `check_tsmis_pdf_reconcile`
  — all green (the vs-TSN behavior + the Excel Int-Detail are unchanged).
- `node --check scripts/ui/mock.js scripts/ui/app.js` → both valid (the `#mock` JS smoke).
- Misspelling guard + a tracked-content `git grep` for the transposed product name → clean.

## 8. Results
- **73/74 `build/check_*.py` green** (the sole failure is the pre-existing untracked
  `P10-codex-review.md` rg-command literal carrying the transposed name — not product code) +
  **3/3 Node green**.
- One regression found **and fixed** during verification: `check_compare_env_highway_log_pdf`
  asserted HL-PDF was the *last* matrix row; the new row displaced it. This is the exact
  `b70a644` reconciliation the handoff predicted — changed to assert **membership** + that the
  existing order is unchanged (the new row is appended after HL-PDF).
- `check_app_modules` (the F6 packaging tripwire) green with the 4 new modules declared.
- `app.js` carries **zero** `makeMockApi` references (RM2); `version.py` untouched (RM6).

## 9. Before/after measurements
| Registry tier | Before (HEAD) | After (P14) |
|---|---|---|
| EXPORT_REPORTS | 7 (keys 0–6) | 8 (`intersection_detail_pdf` at 7; 0–6 unchanged) |
| CONSOLIDATE_REPORTS | 8 | 9 |
| COMPARE_REPORTS | 15 | 18 (+env, +pdf_vs_tsn, +pdf_vs_excel) |
| Everything-matrix rows | 7 | 8 (new row LAST) |
| `_V017_EXPORT_ORDER` | 7 | 8 (append-only) |
| consolidate `.bat` choices | 8 | 9 |
| `APP_MODULES` | (HL-PDF set) | +4 |

Diff: **19 modified files (+399/−84) + 6 new product files (905 lines)**.

## 10. Deviations from the approved plan
None material. Two judgment calls within the plan's "mirror the refactored HL-PDF sibling"
mandate, both documented:
1. **The new consolidator gains the P12 TOCTOU gate + the P1 `outcome.PARTIAL` escalation** that
   `origin/main`'s version lacked — because the refactored HL-PDF consolidator has them, and
   CR002-RM7's rule is to apply the refactor's structural change to the sibling. (Not a scope
   expansion; it's structural parity.)
2. **`save_intersection_detail_pdf` relies on its spec's `is_empty`** for the empty case (which
   runs before save), matching the v0.17.8 shipped behavior — it does **not** add the
   HL-PDF-specific in-save `EmptyExport` backstop (that was a P8c live-path change coupled to the
   HL print DOM, and the Int-Detail print DOM differs). Empty-path real-PDF acceptance stays
   v0.18.1 (RM04). Noted in `check_fake_site`.

The `matrix._pdf_store_consolidator` / `_pdf_self_comparator` extraction is a small DRY within
the touched file (the handoff's `_pdf_store_consolidator` design), not a deviation — it replaces
two literal branches that would otherwise need a third copy.

## 11. Known limitations and external verification
- **Parser correctness is offline-locked only (RM04).** `check_intersection_detail_pdf` locks the
  36-col header, the rowA(21)+rowB(18)→36 mapping (incl. the `Intrte S`/`Intrte Route` swap +
  merged Description), and the every-matrix-row-resolves-a-filename regression — but NOT a real
  PDF. The handoff's 218/218-route reconciliation (0 content diffs) ran on LOCAL ground truth
  under `Downloads\TSMIS\…`, never in CI. **Real-PDF/Excel/TSN correctness acceptance is
  v0.18.1 (P13)** — identical footing to the other PDF reports + the P12 oracle.
- **Live export/consolidate/compare** of the new report on the work PC is owed to **v0.18.1
  (P13)** — P13's evidence kit now covers the final **8-report** shape (CR002-RM5).
- **vs-TSN comparison behavior is the v0.17.1-era state**, not v0.17.8 — that evolution
  (position-aligned dates, `S` label, numeric-padding norm, Report View, the summary fold) is
  **P15**, which reuses these same `compare_intersection_detail_pdf` adapters once it lands.

## 12. Exact diff scope Codex should review
- **The 4 new product modules** — verify the parser (`consolidate_tsmis_intersection_detail_pdf`)
  faithfully ports `origin/main`'s logic AND correctly adopts the refactored P12/P1 structure;
  the comparator reuse of `compare_intersection_detail_tsn`; the 36-col header.
- **`matrix.py`** — the `_pdf_store_consolidator` + `_pdf_self_comparator` extractions (both
  hardcoded HL-PDF branches fully replaced; no third literal left), the `_row_modes` +
  `tsn_comparator_for` branches, and the generalized self-mode (`.endswith("_pdf")`).
- **`report_catalog.py`** — the EXPORT (append-only, positions 0–6), CONSOLIDATE (position 6),
  and 3 COMPARE rows; that `_AUTO_CONSOLIDATOR` correctly **excludes** the PDF report.
- **`batch_manifest._V017_EXPORT_ORDER`** + **`check_stable_ids`** — the append-only index-7
  migration (v0.17.8 v1 manifest resolves; 0–6 preserved).
- **`scripts/ui/mock.js`** — all fixtures here (RM2); `app.js` unmodified.
- **The reconciled checks** — especially `check_compare_env_highway_log_pdf` (membership not
  last-position) and the matrix row-set 7→8 updates; `check_intersection_gate` now registry-derived.
- **`4. consolidate (combine reports).bat`** + `app.spec` + `checks.yml` packaging/console wiring.
- **Not in scope:** `compare_core` (untouched), `version.py` (untouched), the docs (folded into
  P11), and the §8/§9 vs-TSN evolution (P15).
