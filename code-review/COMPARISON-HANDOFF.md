# COMPARISON-HANDOFF.md — comparison + consolidator scope

Status of the **comparison/consolidator** half of the next-patch audit fixes
(the engine behind the Compare tab + the consolidators that feed it). The other
half (export/GUI/updater/auth/build/CI) is in `OG-SCOPE-HANDOFF.md`. Together
these two hand off to the release agent.

Branch `next-patch-og` (shared with the og scope — see §6) · baseline `897f8e1`.
The comparison scope is **functionally complete, regression-locked, COM-verified,
and ruthlessly audited (engine correct on all real data; no open defect that
fires on real data except one cosmetic label, now fixed).**

---

## 1. What shipped (committed, in order)

| # | Commit | Fix |
|---|--------|-----|
| 1 | `c82c9e1` | **Granular key** — `CompareSchema.key_field`; Highway Sequence + Ramp Detail key on **PM**, not the coarse first column (County / district-county-route). Was a positional-cascade diff-inflator. |
| 2 | `6a4adb5` | **Skip honesty** — unreadable inputs force the verdict off "match" (`run_compare(warnings=…)`), listed in the workbook + summary; consolidator returns error WITHOUT overwriting on all-fail. |
| 3 | `f92d101` | **Formula-injection guard** — leading `= + - @` free text stored as TEXT on every write path (data sheets, Comparison/Only-in, all consolidators). |
| 4 | `4b67557` | **Ramp Summary failures** — one-page/failed PDFs dropped, never overwrite a good workbook; partial = loud INCOMPLETE. |
| 5+7 | `65bd384` | **Date/type coercion parity** (`normalize_value` ISO at load) + **Excel row/col limit** & **sheet-name collision** guards. |
| 6 | `082b6bf` | **TSN Description leak** — totals-block continuations (`(DVMS)`, `CUMULATIVE`, `TOTAL CONST UNCONST`, …) no longer pollute Description. |
| — | `028721a` | COMPARISON-TODO doc. |
| audit | `7ca43dc` | **8 latent gaps** from the ruthless multi-agent audit (P1 helper-key/route-id guard completing #3; P2 spaced-marker COUNTIF + widest-sheet column guard; P3 side-label cap + unnamed-column labels + Ramp-Summary route-key normalize; P4 `datetime.time` + duplicate-name widths). |

**Files touched (mine only):** `scripts/compare_core.py`, `scripts/compare_env.py`,
`scripts/compare_highway_log.py`, `scripts/consolidate_xlsx_base.py`,
`scripts/consolidate_ramp_summary.py`, `scripts/consolidate_tsn_highway_log.py`,
the `COMPARE_REPORTS` block of `scripts/reports.py` (key_col wiring, verified —
no edit needed), and `build/check_compare_*.py` / `check_ramp_summary_partial.py`
/ `check_tsn_description_leak.py`. **No other-scope files touched.**

## 2. Verification (real data + Excel COM — this PC has Excel)

- **Regression lock HELD.** Highway Log (consolidated, key_field=0) + TSMIS-vs-TSN
  (per-route + consolidated) are **cell-for-cell IDENTICAL** before/after fixes
  #1–#7, both flavors (openpyxl cell-dump). The audit round changes ONLY two
  cell classes on real data — the P2 COUNTIF marker text (results identical) and
  the P3 unnamed-column *labels* (counts identical) — everything else byte-identical.
- **Flavor parity PROVEN.** COM-recalc the formulas flavor and compare cell-for-cell
  to the values flavor: **0 mismatches over 554k+ cells** (TSMIS-vs-TSN Route1
  39,540 + cross-env HSL 514,501); the audit's independent Excel-semantics check
  added ~222k more rows, 0 mismatches.
- **Full cross-env audit.** All **6 env pairs × {Highway Sequence, Highway Log} =
  12 comparisons**, every one COM-recalc'd **9/9 SELF-CHECK OK, zero CHECK rows**.
  Fix #1 proof: PROD-vs-DEV HSL diff cells **15,797 → 5,070** (positional cascade
  gone); similar-env pairs collapse to 7–16 cells (correct postmile alignment).
- **TSN leak proof.** D01-D03: 0 leaks remain (was 48/70/150); TSMIS-vs-TSN Route-1
  loses exactly its 2 leak-caused Description false positives (971 → 969 cells).
- **9 golden fixtures**, all green in `build/.venv` (no Excel needed):
  `check_compare_{blankkey,keyfield,skipwarn,injection,coercion,limits,audit}.py`,
  `check_ramp_summary_partial.py`, `check_tsn_description_leak.py`.

## 3. Open — maintainer decision (NOT a merge blocker)

- **Med Wid flavor-parity gap** (`compare_core._medwid_norm` vs `_medwid_ref`).
  Excel `VALUE()` is more permissive than the Python regex `\d+(\.\d+)?`, so on
  exotic inputs (`".5"`, `"+5"`, `"1 2"`, `"1e3"`, `"$5"`) the two flavors can
  disagree — **COM-confirmed** (3/4 fixture rows flip). **Dormant:** every real
  Med Wid value across both consolidated files is a clean `<digits><letter>` code
  or `"+++"` (parity-safe), proven by the 554k-cell parity run. **Not fixed**
  because every fix changes the regression-locked `_medwid_ref` formula text or
  replicates Excel `VALUE()` in Python (fragile), for zero real-data benefit.
  Recommended approach if you want it closed: gate the Excel `VALUE()` behind a
  strict `\d+(\.\d+)?`-equivalent test (NON-volatile — no per-char INDIRECT) so it
  matches the Python mirror; then re-run the cell-dump + COM harness. Details +
  repro in `COMPARISON-TODO.md`.

## 4. Pending real-data verification (blocked — work-PC export access)

- **Cross-env Ramp Detail & Ramp Summary** are fixed in code (Ramp Detail
  re-keyed on PM; Ramp Summary blank/all-fail handling; route-key normalize) and
  covered by synthetic fixtures, but the work PC can't export them (site-side
  block). When access returns: export on two envs, run the comparison, COM-recalc,
  confirm 9/9, and confirm Ramp Detail's postmile column is actually named `PM`
  (the key_col resolver falls back to the first column + logs a warning if not).
  Steps in `COMPARISON-TODO.md`.

## 5. Hand-off to the merge / og scope (contracts they depend on)

- **CI must gate the comparison checks.** `OG-SCOPE-HANDOFF.md` §4 already flags
  this: wire **all 9** `build/check_compare_*.py` + `check_ramp_summary_partial.py`
  + `check_tsn_description_leak.py` into `checks.yml` at merge. They need only the
  `build/.venv` (openpyxl) — no Excel, no network. This protects the
  regression-locked `compare_core` from a future silent break.
- **Incomplete-comparison contract (for the og dialog fix, OG §4).** When inputs
  are unreadable, `run_compare` returns `status="ok"`, `verdict="diff"`, and
  `summary_lines[0]` **starts with the literal `⚠ COULD NOT COMPARE EVERYTHING`**.
  The og side can detect that `⚠` prefix to title the dialog "Comparison
  incomplete" instead of "Differences found". This contract is now FINAL.
- **CLAUDE.md additions** (close-out, maintainer): document `CompareSchema.key_field`
  + the PM re-key (Highway Sequence / Ramp Detail), the `warnings=` incompleteness
  path + verdict downgrade, the formula-injection guard, `normalize_value`, the
  Excel-limit/sheet-collision guards, and the TSN totals-leak skip. (I did not
  touch CLAUDE.md — it's close-out scope.)

## 6. Branch note

All comparison commits are on **`next-patch-og`**, interleaved with the og
scope's (the shared working dir was switched to `next-patch-og` mid-run; the
maintainer confirmed staying there). `next-patch-comparison` is unused (still at
base `897f8e1`). **Merge `next-patch-og`** to get both scopes; merging
`next-patch-comparison` would pick up none of this.

## 7. Bottom line

The comparison/consolidator scope is **release-ready**: every brief fix done +
8 audit gaps closed, regression-locked, COM-verified across all real cross-env
and TSMIS-vs-TSN data, 9 green fixtures. The only un-closed item is the **dormant
Med Wid parity gap** (documented, maintainer's call) and the **export-blocked
Ramp Detail/Summary real-data verification**. No merge blocker.
