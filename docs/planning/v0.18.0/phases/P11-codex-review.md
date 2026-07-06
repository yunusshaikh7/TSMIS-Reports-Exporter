# Review round 1

## 1. Verdict: `BLOCKED`

P11 is correctly scoped as a docs plus `version.py` phase, and the product diff is clean of `scripts/` changes. However, the phase completion criterion says the canonical docs must match HEAD. They do not yet: two P11-touched documentation areas still describe pre-P10/pre-CR-002 behavior in current, non-historical sections. These are small to fix, but they are blocking for the final documentation/audit-reconciliation phase.

## 2. Blocking findings

### P11-B01 — Current comparison/report/matrix docs still describe the pre-CR-002 7-report or incomplete PDF-edition state

- Severity: blocking
- Affected phase area: P11 docs reconciliation; final-plan P11 "canonical docs reflect v0.18.0"; CR-002 doc absorption.
- Repository evidence:
  - Runtime/catalog source of truth now has 8 export reports and 8 matrix rows, including `intersection_detail_pdf`. Independent probe:
    - `reports.EXPORT_REPORTS` count = 8.
    - `reports.matrix_rows()` count = 8.
    - Matrix rows = `ramp_summary`, `ramp_detail`, `highway_sequence`, `highway_log`, `intersection_summary`, `intersection_detail`, `highway_log_pdf`, `intersection_detail_pdf`.
  - `scripts/compare_env.py:625` defines `INTERSECTION_DETAIL_PDF = EnvCompare(...)` with `flat_pdf_loader=_load_intersection_detail_pdf_side`.
  - `scripts/matrix.py:360-366` gives `intersection_detail_pdf` its `vs TSN` and `vs TSMIS Excel` row modes, with `tsn_subdir="intersection_detail"`.
  - `reports.consolidator_for_spec` returns no inline auto-consolidator for both PDF editions: `highway_log_pdf` and `intersection_detail_pdf`.
  - `docs/comparison-engine.md:568-572` still lists the cross-env PDF-sourced variant as Highway Log PDF only and omits `INTERSECTION_DETAIL_PDF`.
  - `docs/comparison-engine.md:664-676` still says matrix rows are "**all 7 reports**", omits `Intersection Detail (PDF)`, says env mode is "All rows but HL-PDF", and frames `vs_pdf` / `vs_excel` as Highway Log only.
  - `docs/comparison-engine.md:727-734` says "ALL reports" but lists only the pre-CR-002 seven-report set and omits `Intersection Detail (PDF)`.
  - `docs/reports.md:173` says `group="env"` is every report's between-environments comparison but parenthetically lists only Ramp Summary/Detail, Highway Sequence, Highway Log, and the Highway Log PDF-vs-Excel self-check. It omits the Intersection env rows and the new Intersection Detail PDF/PDF-vs-Excel entries, even though the table below was updated.
  - `docs/architecture.md:293` says only Highway Log PDF has no auto-consolidator and every other report consolidates inline; HEAD shows `intersection_detail_pdf` also lacks an inline auto-consolidator and is handled via the matrix/scratch-convert path.
  - `docs/architecture.md:390` says every non-Highway-Log report uses its own `tsn_subdir`; HEAD maps `intersection_detail_pdf` to `tsn_subdir="intersection_detail"`.
- Exact correction expected:
  - Update `docs/comparison-engine.md` section 9c and section 12/12b to the current 8-row matrix state, including the `INTERSECTION_DETAIL_PDF` cross-env adapter, the `intersection_detail_pdf` matrix row, its `vs TSN` and `vs TSMIS Excel` modes, and the fact that both PDF edition rows share the TSN subdir of their Excel families.
  - Update `docs/reports.md` `group="env"` summary so it matches the current compare registry, including all between-environment rows and both PDF-vs-Excel self-check families.
  - Update `docs/architecture.md` B2 and `tsn_subdir` wording so both PDF editions are described as inline-auto-consolidate exceptions with matrix/scratch handling, and so `intersection_detail_pdf -> intersection_detail` TSN source sharing is explicit.

### P11-B02 — `docs/internals/updater-swap.md` still repeats pre-P10 cache-clear and death-check behavior

- Severity: blocking
- Affected phase area: P11 docs reconciliation; P10 updater/packaging hardening absorption.
- Repository evidence:
  - `scripts/updater.py:609-613` defines `_DEATH_CHECK_TOTAL_S = 2.0` and `_DEATH_CHECK_INTERVAL_S = 0.25`; `apply_update_and_restart` polls during that window.
  - `scripts/updater.py:1105-1112` runs `_recover_store_promotions()` before the frozen gate, then returns immediately for non-frozen runs; `_clear_webview_caches()` is below `if not is_frozen(): return`.
  - `docs/build-and-release.md:316-317` already describes the P10 behavior correctly as a ~2.0 s window polling every 0.25 s.
  - `docs/build-and-release.md:390-397` describes WebView cache clearing as frozen-only.
  - `docs/internals/updater-swap.md:178` still says the death check is `time.sleep(1.5); rc = proc.poll()`.
  - `docs/internals/updater-swap.md:292-301` still says `_clear_webview_caches()` runs first on every launch and runs in dev.
  - `docs/internals/updater-swap.md:352` still shows `sleep 1.5s; poll()`.
  - `docs/internals/updater-swap.md:373` still says the swap exe blocked/dies in 1.5 s.
  - `docs/internals/updater-swap.md:417-418` still says `_clear_webview_caches` runs in dev and the 1.5 s window only catches immediate launch refusals.
- Exact correction expected:
  - Replace the stale 1.5 s sleep/poll descriptions with the P10 windowed polling contract: ~2.0 s total, 0.25 s poll cadence, fail-safe if observed dead during the window.
  - Correct the cleanup section to distinguish always-run store-promotion recovery from frozen-only WebView cache clearing.
  - Update the gotchas/error-table/sequence snippets in the same file so they no longer contradict `scripts/updater.py` or `docs/build-and-release.md`.

## 3. Required fixes

- Fix P11-B01 in all affected docs and re-run the targeted doc/source drift probes:
  - registry/matrix count probe over `reports.EXPORT_REPORTS`, `reports.matrix_rows()`, and `reports.tsn_matrix_extra_rows()`;
  - `rg` for stale "all 7 reports", "ALL reports" seven-report lists, and Highway-Log-only PDF matrix/self-check language in the P11-edited docs.
- Fix P11-B02 in `docs/internals/updater-swap.md` and re-run:
  - `rg -n "1\\.5|dev too|runs in dev|_clear_webview_caches|death check|death-check" docs/internals/updater-swap.md docs/build-and-release.md`;
  - a direct read/probe of `scripts/updater.py` constants and `cleanup_leftovers()` placement.
- Re-run `git diff --check 5d149ea -- . ':!docs/planning'`.
- Re-run `python -B build/check_no_misspelling.py` or, if the known untracked planning-file hit remains, also provide a tracked-only grep proving no committed/product docs introduce the transposed product-name typo.

## 4. Non-blocking recommendations

### P11-N01 — Product source comments also carry some of the same PDF-edition drift

- Severity: recommended
- Affected phase area: future code-comment cleanup; not required for P11 because P11 is docs plus version only.
- Repository evidence:
  - `scripts/matrix.py:340-343` still says Highway Log PDF is the two-row special case and that other reports get a greyed TSN placeholder, which no longer describes the all-report matrix after P14/P15.
  - `scripts/matrix.py:355` comments that `highway_log_pdf` cross-env is not coded/greyed, but its `env` mode is supported by the `compare_env.HIGHWAY_LOG_PDF` adapter.
  - `scripts/reports.py:61-63` still says every report except Highway Log PDF auto-consolidates; `intersection_detail_pdf` is also absent from `_CONSOLIDATOR_BY_SUBDIR`.
- Exact correction expected:
  - Do not edit product code in P11 unless the approved scope is explicitly expanded. Carry these comments to a later comment-cleanup pass or fold them into the next source-touching phase.

## 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md`; confirmed P11 is the current `awaiting_review` phase at baseline `5d149ea` and is the final docs/audit/roadmap phase.
- Read `docs/planning/v0.18.0/05-claude-final-plan.md` P11 and relevant P13/P14/P15 context.
- Read `docs/planning/v0.18.0/phases/P11-claude-report.md`.
- Reviewed relevant prior phase reports/reviews for P13/P15 completion constraints: final 8-report shape, work-PC/v0.18.1 field gate, and `compare_core.context_fill` not ported.
- Inspected the product diff from `5d149ea`, excluding `docs/planning/`.
  - `git diff --name-status 5d149ea -- . ':!docs/planning'` shows 15 docs plus `version.py`.
  - `git diff --name-only 5d149ea -- scripts` is empty.
  - `git diff 5d149ea -- version.py` confirms `__version__` changes from `0.17.1` to `0.18.0`.
- Ran `git diff --check 5d149ea -- . ':!docs/planning'` — passed.
- Ran `python -B build/check_report_catalog.py` — passed.
- Ran a read-only relative Markdown file-link check over the P11-touched docs — passed.
- Ran `python -B build/check_no_misspelling.py` — failed only on the known untracked planning-file hit in `docs/planning/v0.18.0/phases/P10-codex-review.md`; a tracked-only `git grep` found no product-doc hit beyond the guard script's own self-documenting string.
- Ran source-of-truth probes confirming:
  - 8 export reports;
  - 8 matrix rows, including `intersection_detail_pdf`;
  - no `tsn_matrix_extra_rows`;
  - both `highway_log_pdf` and `intersection_detail_pdf` lack inline auto-consolidators.
- Did not run the full build/check suite, PyInstaller, frozen self-tests, browser, GUI, or live TSMIS access.

## 6. Whether Claude may proceed toward phase approval

No. Claude should fix P11-B01 and P11-B02, append a remediation section to the P11 report, keep the phase marked `awaiting_review`, and request another Codex review. After those docs are corrected and the narrow checks above are rerun, this phase should be able to pass without product-code changes.

# Review round 2

## 1. Verdict: `PASS`

The current P11 remediation resolves the two round-1 blockers without changing product source. The phase remains properly scoped to canonical documentation plus the `version.py` release-target bump; the product diff from the recorded `5d149ea` baseline still contains no `scripts/` changes. The remaining stale comments identified in P11-N01 are product-source comments and were correctly deferred rather than edited in this docs-only phase.

## 2. Blocking findings

None.

### P11-B01 — Resolved

- Previous severity: blocking
- Affected phase area: P11 docs reconciliation; CR-002 documentation absorption.
- Repository evidence:
  - `docs/comparison-engine.md` now documents the `INTERSECTION_DETAIL_PDF` cross-environment adapter in the env-family table and describes the PDF-sourced env shape as both Highway Log (PDF) and Intersection Detail (PDF).
  - `docs/comparison-engine.md` now describes `reports.matrix_rows()` as **all 8 reports**, including `intersection_detail_pdf`, and its row modes now match `scripts/matrix.py`: all 8 rows have `env`, every report has `tsn`, and the PDF rows have `vs_excel` self-checks.
  - `docs/comparison-engine.md` section 12b now includes Intersection Detail (PDF) in the by-day/vs-TSN all-report list and notes its shared `intersection_detail` TSN subdir.
  - `docs/reports.md` now states that the `env` group includes Intersection Summary/Detail, both PDF editions, and both PDF-vs-Excel consistency checks.
  - `docs/architecture.md` now names both PDF editions as inline auto-consolidate exceptions and states that `intersection_detail_pdf` shares `intersection_detail` as its TSN subdir.
  - Independent source probe confirmed `reports.EXPORT_REPORTS == 8`, `reports.matrix_rows() == 8`, `reports.tsn_matrix_extra_rows() == []`, and inline auto-consolidators are absent for both `highway_log_pdf` and `intersection_detail_pdf`.
- Exact correction expected: none.

### P11-B02 — Resolved

- Previous severity: blocking
- Affected phase area: P11 docs reconciliation; P10 updater/packaging documentation absorption.
- Repository evidence:
  - `docs/internals/updater-swap.md` now describes the P10 death check as a ~2.0 s window with 0.25 s polling, consistent with `scripts/updater.py` `_DEATH_CHECK_TOTAL_S = 2.0` and `_DEATH_CHECK_INTERVAL_S = 0.25`.
  - The same doc's sequence diagram and failure table now use the ~2.0 s windowed-polling contract rather than a single 1.5 s sleep/poll.
  - `docs/internals/updater-swap.md` now describes `cleanup_leftovers()` as store-promotion recovery on every launch, then a non-frozen return, with WebView cache clearing and staging cleanup frozen-only. This matches `scripts/updater.py` where `_recover_store_promotions()` precedes `if not is_frozen(): return` and `_clear_webview_caches()` is below that gate.
  - The remaining `1.5` hit in P11-edited release docs is a historical "hardened from a single ~1.5 s check" reference, not a current behavior claim.
- Exact correction expected: none.

## 3. Required fixes

None.

## 4. Non-blocking recommendations

### P11-N01 — Still deferred appropriately

- Severity: recommended
- Affected phase area: future source-comment cleanup, not P11.
- Repository evidence:
  - The stale source comments previously identified in `scripts/matrix.py` and `scripts/reports.py` are product-code comments, and the approved P11 write scope is canonical docs plus `version.py`.
  - P11's remediation intentionally left `scripts/` untouched, which is the safer choice for this docs-only final phase.
- Exact correction expected: carry this to a future source-touching cleanup pass or v0.18.1; do not block P11.

## 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`; confirmed P11 remains the current `awaiting_review` phase at baseline `5d149ea`, with round-1 blockers reported as remediated.
- Re-read the P11 section of `docs/planning/v0.18.0/05-claude-final-plan.md`.
- Re-read `docs/planning/v0.18.0/phases/P11-claude-report.md`, including the appended remediation section.
- Re-read `docs/planning/v0.18.0/phases/P11-codex-review.md` round 1 and reused the existing finding IDs.
- Inspected the product diff from `5d149ea`, excluding `docs/planning/`:
  - 16 tracked files changed: 15 docs plus `version.py`.
  - `git diff --name-only 5d149ea -- scripts` is empty.
  - `git diff --check 5d149ea -- . ':!docs/planning'` passed.
- Ran source-of-truth probes over `scripts/reports.py`:
  - `EXPORT_REPORTS` count: 8.
  - `matrix_rows()` count: 8, including `intersection_detail_pdf`.
  - `tsn_matrix_extra_rows()`: empty.
  - Inline auto-consolidators absent for `highway_log_pdf` and `intersection_detail_pdf`.
- Ran stale-doc sweeps for the round-1 blocker terms across the P11-edited docs. Current-state blocker terms are gone; remaining hits are historical roadmap/worklist text or explicit "hardened from" historical references.
- Ran `python -B build/check_report_catalog.py` — passed.
- Ran `python -B build/check_no_misspelling.py` — failed only on the known untracked planning-file hit in `docs/planning/v0.18.0/phases/P10-codex-review.md`; tracked grep outside `docs/planning` finds only the guard script's own self-documenting string.
- Ran a relative Markdown file-link check over the P11-touched docs — passed.
- Did not run the full suite, PyInstaller, frozen self-tests, browser/GUI launch, or live TSMIS access.

## 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval/commit for P11.
