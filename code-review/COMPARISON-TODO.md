# COMPARISON-TODO.md — running list for the comparison/consolidator subsystem

A living backlog for the cross-environment + TSMIS-vs-TSN comparison engine and
the consolidators that feed it. Add to it freely. Items here are either (a)
**blocked on data we can't produce yet** (Ramp Detail / Ramp Summary can't be
exported from the work PC right now — site-side block), or (b) lower-priority
hardening surfaced during the audit.

Legend: ✅ done & verified · 🟡 code done, **verification pending data** · ⬜ not started

---

## Blocked on export access (work-PC site block) — fix-and-fixture only for now

### 🟡 Ramp Detail — re-key on PM (granular), not the coarse first column
- **Why:** the Ramp Detail export's FIRST column is `Location`
  (`district-county-route`, e.g. `D01-ALA-01`) which **repeats for every ramp on
  the route** — a coarse key, exactly like Highway Sequence's County. Keying on
  it aligns rows *positionally within the route* and inflates diffs/one-sided
  rows when the two environments differ in count. The granular identity is the
  **`PM`** (postmile) column (index 2 in the live export layout).
  Evidence: TSMIS website source `website-source/shared.js` Ramp Detail export
  (~L2206) — header `['Location','','PM','Date of Record','','HG','Area 4','',
  'City Code','R/U','Description']`.
- **Done in code:** `compare_env.RAMP_DETAIL` now sets `key_col="PM"`; the engine
  resolves it to a header index per loaded layout and falls back to the first
  column if `PM` isn't present (so layout drift degrades, never crashes).
- **PENDING — real-data verification:** cannot export Ramp Detail from the work
  PC. When export access returns:
  1. Export Ramp Detail on two environments (e.g. ssor-prod + ssor-dev).
  2. Confirm the loaded header actually names the postmile column `PM` (exact,
     after strip/casefold) — if it's named differently, update `key_col`.
  3. Regenerate the cross-env comparison; confirm the diff/one-sided counts
     collapse vs the coarse-key baseline and SELF-CHECK reads all-OK (COM recalc).
  4. Add a Ramp Detail misalignment golden fixture (mid-route missing row).

### 🟡 / ⬜ Ramp Summary — confirm route-keying holds; add a fixture
- Ramp Summary is **route-keyed** (one row per route, `has_route=False`,
  `key_field=0` = Route). That is correct and needs no re-key. But it's the only
  comparison family with **zero golden coverage**.
- **PENDING — real-data verification:** cannot export Ramp Summary PDFs from the
  work PC. When access returns: export on two envs, run `compare_env.RAMP_SUMMARY`,
  COM-recalc, confirm SELF-CHECK OK. Add a synthetic per-route fixture
  (planted numeric diff + a route present on only one side).
- ⬜ Audit `consolidate_ramp_summary.parse_pdf` for the same bug classes the TSN
  parser had (page-furniture leakage into parsed fields, silent all-parse-fail
  returning OK). See `RAMP-SUMMARY-FAILURES-OK` in the fixes brief.

---

## Done this patch (next-patch-og)

- ✅ **`COMPARE-KEY-IS-FIRST-COLUMN`** — `CompareSchema.key_field`; Highway
  Sequence (+ Ramp Detail) key on **PM**, not the coarse first column.
  Real-data: full 252-route PROD-vs-DEV HSL diff cells 15,797→5,070, 9/9
  SELF-CHECK OK. Regression IDENTICAL. (`check_compare_keyfield.py`)
- ✅ **`COMPARE-SKIPPED-FILES-MATCH` + `CONSOLIDATE-XLSX-PARTIAL-OK`** — skipped/
  unreadable inputs force the verdict off "match", surface in the workbook +
  summary; consolidator won't overwrite a good file on all-fail.
  (`check_compare_skipwarn.py`)
- ✅ **`SHEET-FORMULA-INJECTION`** — leading `= + - @` free text stored as TEXT
  on every write path. (`check_compare_injection.py`)
- ✅ **`RAMP-SUMMARY-FAILURES-OK` / `SHORT-PDF-BLANK`** — one-page/failed PDFs
  dropped, never overwrite a good workbook. (`check_ramp_summary_partial.py`)
- ✅ **`COMPARE-VALUE-COERCION`** — date/datetime canonicalized at load (flavor
  parity); integer/number-vs-text already match. (`check_compare_coercion.py`)
- ✅ **TSN Description leak** — totals-block continuations (`(DVMS)`,
  `CUMULATIVE`, `TOTAL CONST UNCONST`, `County Cumulative DVM`, bare mileage)
  no longer pollute Description. Real-data: 0 leaks remain (was 48/70/150);
  TSMIS-vs-TSN Route-1 loses its 2 leak-caused false positives.
  (`check_tsn_description_leak.py`)
- ✅ **Excel row/column-limit guard + sheet-name collision** — fail cleanly
  before writing. (`check_compare_limits.py`)

## Found in the full audit — open

### ⬜ Med Wid flavor-parity gap (`compare_core.py`) — latent, dormant on real data
`_medwid_norm` (Python mirror, ~`:251`, used by the VALUES flavor + run summary)
and `_medwid_ref` (the Excel formula, ~`:440`, used by the FORMULAS flavor) can
DISAGREE, because Excel `VALUE()` accepts far more strings as numeric than the
Python regex `\d+(\.\d+)?`. Excel-COM-verified divergences (Python vs Excel):
`".5"`→`.5`/`0.5`; `"5."`→`5.`/`5`; `"+5"`→`+5`/`5`; `"1 2"`→`1 2`/`12`
(VALUE ignores internal spaces); `"0."`→`0.`/`0`; `"1e3"`→text/`1000`; `"$5"`,
`"5%"`, `"1,234"`, `".1"` similar. These cause **verdict flips** (values flavor
says DIFF, formulas says MATCH for the same cell) — a violation of the "the two
flavors can never disagree" invariant.
- **Currently DORMANT:** all 222 distinct Med Wid values across the real
  consolidated TSMIS/TSN files are clean `<digits><letter>` codes (`0Z`,`06V`,
  `99P`) plus `"+++"` (parity-safe). It only fires if a Med Wid ever contains a
  space / sign / bare-or-trailing decimal point / sci-notation / separator.
- **Why not fixed this round:** the fix must change either the regression-locked
  `_medwid_ref` formula TEXT (re-prove cell-for-cell + COM that real results are
  unchanged) or replicate Excel `VALUE()` exactly in Python (fragile). Safer
  direction: gate the Excel `VALUE()` behind a strict `\d+(\.\d+)?`-equivalent
  test so it matches the Python mirror, then re-run the regression lock.
- AREA-1 audit (`compare_highway_log._load_input`: per-route vs consolidated
  shape detection, mixed-shape rejection, date pass-through) came back SOLID;
  `_xl_trim` vs Excel TRIM parity is sound (only sub-1e-4 sci-notation diverges,
  impossible for Highway Log numeric fields).

## Still open / lower-priority
- ⬜ `extractall`/junction safety review (only if relevant to comparison inputs;
  the comparison reads existing files, doesn't extract archives — likely N/A).
- ⬜ Ramp Summary golden fixture from REAL exports (synthetic-only today).
- ⬜ Ramp Detail real-data re-key verification (see above).

---

## Full comparison-mechanism audit (to run after the fixes land)

Scope = every comparison path, leaning on the data we CAN fully test
(cross-env Highway Sequence + Highway Log, 4 envs → 6 pairs each; TSMIS-vs-TSN
per-route + consolidated from on-hand inputs). Findings get filed back here.
