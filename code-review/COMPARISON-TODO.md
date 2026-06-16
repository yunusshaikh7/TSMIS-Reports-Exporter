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

## Hardening surfaced during the audit (not blocked)

### TSN Highway Log PDF parser — Description-column pollution (feeds false diffs)
- `consolidate_tsn_highway_log.py`: City/County **TOTALS** blocks wrap across
  lines; continuation lines (`(DVMS) 3,391`, `CUMULATIVE (MILEAGE) …`,
  `UNCONST 000.000`, bare mileage fragments) don't match the `*`-prefix skip and
  fall through into the preceding data row's **Description**, producing
  false-positive Description diffs in TSMIS-vs-TSN (48 / 70 / 150 leaked rows in
  D01 / D02 / D03). Med Wid windows, the Location key, and dates audited clean.
- Tracked as fix #6 on the main brief; landing on this branch.

### Lower-priority (from RECONCILED-FINDINGS WS2)
- ⬜ Excel row-limit guard (union > ~1,048,575 rows).
- ⬜ `CompareSchema.sheet_names()` collision if a side is literally named
  "Summary"/"Comparison"/"Routes"/etc.
- ⬜ `extractall`/junction safety review (only if relevant to comparison inputs).

---

## Full comparison-mechanism audit (to run after the fixes land)

Scope = every comparison path, leaning on the data we CAN fully test
(cross-env Highway Sequence + Highway Log, 4 envs → 6 pairs each; TSMIS-vs-TSN
per-route + consolidated from on-hand inputs). Findings get filed back here.
