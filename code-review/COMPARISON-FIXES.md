# COMPARISON-FIXES.md — next-patch comparison + consolidator work (Agent 2)

You own **all comparison + consolidator correctness** for the next patch. A
SECOND agent works the rest of the audit in parallel on its own branch — stay in
your lane (file ownership below) so the two branches merge cleanly.

**Branch: `next-patch-comparison`** (already carries two committed, COM-verified
fixes: `8bf9fad` blank-key handling + self-check row counts, `f20c657` dead-key
removal). Continue here; commit per fix; **do NOT merge to main** (the maintainer
merges both agent branches at the end).

## Files you OWN (edit only these)
- `scripts/compare_core.py` (the **regression-locked** engine), `scripts/compare_env.py`,
  `scripts/compare_highway_log.py`
- the consolidators the comparison depends on: `scripts/consolidate_xlsx_base.py`,
  `scripts/consolidate_ramp_summary.py`, `scripts/consolidate_tsn_highway_log.py`,
  `scripts/consolidate_{ramp_detail,highway_sequence,highway_log}.py`
- `build/check_compare_*.py` (golden fixtures — add one per fix)
- the **`COMPARE_REPORTS`** block of `scripts/reports.py` ONLY

**Do NOT touch** (the other agent owns them, or they're merge-time): everything
else under `scripts/` (exporter, common, gui_*, updater, login, settings, paths,
export_*, ui/), `build/build.ps1`/`prune_bundle.ps1`/`app.spec`, `.github/`,
`*.bat`, **`CLAUDE.md`, `version.py`, `README.md`, `build/release_notes.md`, the UI
mock** (close-out, done once at merge), and the `EXPORT_REPORTS`/`CONSOLIDATE_REPORTS`
blocks of `reports.py`.

## Real data you have — USE IT for verification
- **`C:\Users\Yunus\Downloads\TSMIS\output\`** — real exports straight from the
  work PC: **4 environments** (`2026-06-15 ssor-prod`, `ssor-dev`, `ssor-test`,
  `ars-prod`), each with `highway_log\` and `highway_sequence\` per-route XLSX,
  plus `run_reports\`. That's **6 cross-env pairs per report** to regenerate and
  check (`compare_env` points at two run folders).
- **TSMIS-vs-TSN files on hand:** `C:\Users\Yunus\Downloads\TSMIS\comparisons\`
  (`TSMIS_vs_TSN_*`), `…\samples-approved\` (the approved `*_SAMPLE` references —
  the regression baseline), `…\inputs\` (`tsmis/tsn_highway_log_consolidated*`,
  TSN district PDFs `D01–D03`).
- **Excel COM is available on this machine.** It's the ONLY way to verify the live
  SELF-CHECK formulas — recalc every regenerated workbook (open, `CalculateFull`,
  read the Summary SELF-CHECK rows; they must all read OK) and confirm the verdict.
  Use the same approach as `build/recalc_*` patterns / the `check_compare_blankkey`
  story.

## WAITING / blocked (cannot verify with real data this patch)
- **Cross-env Ramp Detail and Ramp Summary** can't be exported right now — the work
  PC is blocked from exporting them, site-side, beyond our control. Fix their
  code by reading + synthetic fixtures, but mark **"real-data verification pending
  export access"** — do not claim them verified.

## Already DONE (don't redo)
- `COMPARE-BLANK-KEYFIELD-SELFCHECK` — blank key field handling + the SELF-CHECK /
  row-count formulas now count an always-present column, and data sheets write
  literal keys. Guard: `build/check_compare_blankkey.py`. Verify it still passes
  after each of your changes.

## Fixes to do (priority order)
1. **`COMPARE-KEY-IS-FIRST-COLUMN` (HIGH).** The engine hard-keys every row on
   `header[0]` (the report's first column). Highway Log pins a granular key
   (Location/postmile via `EXPECTED_HEADER`); cross-env **Highway Sequence
   inherits County** (coarse) → rows align *positionally within (Route, County)*
   instead of by postmile, so when two environments differ in count within a
   county the alignment shifts and emits **spurious diffs + one-sided rows** (one
   missing point cascades). PM is the right identity. Fix: give HSL a granular key
   — either reorder so PM is `header[0]`, or (preferred) add a `key_field` selector
   to `CompareSchema` (default 0) threaded through `_Layout`/`keys_for`/`key_expr`/
   `count_diffs`. **Verify on real data:** regenerate a PROD-vs-DEV Highway Sequence
   comparison from the output folder before vs after the re-key; the diff count
   should collapse (misalignment gone) and SELF-CHECK stay 9/9. **Verify Ramp
   Detail's first column** too (its key = whatever the export's first column is).
2. **`COMPARE-SKIPPED-FILES-MATCH` + `CONSOLIDATE-XLSX-PARTIAL-OK`.** Skipped/failed/
   header-drift inputs are only logged — never reflected in the verdict or the
   `status`. A route unreadable on BOTH sides → silently dropped → "✓ MATCHES".
   Make skips break the verdict / surface in counts, and consolidators return a
   non-ok (or explicit partial) status on skip/fail. (`compare_env._load_xlsx_side`,
   `consolidate_xlsx_base.consolidate_xlsx`.)
3. **`SHEET-FORMULA-INJECTION`** — one shared escaping helper (guard leading
   `= + - @`) on the openpyxl write path of `compare_core` (both flavors) AND the
   consolidators, scoped to the free-text Description columns.
4. **`RAMP-SUMMARY-FAILURES-OK` / `RAMP-SUMMARY-SHORT-PDF-BLANK`** — all-parse-fail
   or one-page PDFs must NOT yield an OK/blank workbook that can overwrite a good one.
5. **`COMPARE-VALUE-COERCION` (MED/LOW)** — `count_diffs`/`_xl_trim` compare in text
   form; text-vs-number (`"000.129"` vs `0.129`) or date-vs-datetime (`"760225"` vs
   a real date) formatting differences → spurious diffs, plus a formulas-vs-values
   parity risk on real-date cells. Add mixed-type + real-date golden fixtures.
6. **Complete TSMIS-vs-TSN audit.** Audit `compare_highway_log` end to end — the
   per-route AND consolidated loaders, the Med Wid + date handling, and especially
   the **TSN PDF → Highway-Log conversion** in `consolidate_tsn_highway_log` (the
   x-position parser feeds the comparison; a mis-parse = wrong comparison). Re-run
   it against the on-hand TSMIS-vs-TSN inputs/samples; hunt the SAME bug classes
   (blank key, coarse/positional key, type coercion, silent skip) plus anything new.
7. Lower items: Excel row-limit guard; `CompareSchema.sheet_names()` collision with
   a side literally named "Summary"/"Comparison"; `extractall`/junction safety only
   if relevant.

## Constraints
- **`compare_core` is regression-locked** (cell-for-cell vs the approved samples).
  For every change: regenerate the approved-sample comparison and the real cross-env
  ones, COM-recalc, and confirm non-key/non-self-check cells are unchanged and all
  SELF-CHECK read OK. **Add a golden fixture per fix** (model on `check_compare_blankkey.py`).
- Core stays **console-free + UI-neutral**. Don't change formula/label TEXT without
  re-verifying (intended changes are fine — prove them).
- Subagents are fine (fan out for the TSMIS-vs-TSN audit, the consolidator reads,
  building fixtures, adversarial diff review). The TSMIS website source is public
  (inspect-element captures) — subagents may read/use it freely; it's at
  `C:\Users\Yunus\Downloads\TSMIS\website-source\`.

## First action
Read this file + the `COMPARE-*` items in `code-review/RECONCILED-FINDINGS.md`,
confirm `build/check_compare_blankkey.py` passes, then start fix #1 — and prove it
on real PROD-vs-DEV Highway Sequence data from the output folder.
