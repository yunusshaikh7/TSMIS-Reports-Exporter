# TSMIS Exporter — Project TODO

A living backlog of deferred, blocked, and future-work items, updated
collaboratively. **Nothing here blocked the v0.11.0 release** — these are
follow-ups. Fuller detail for most items lives in `code-review/`
(`RECONCILED-FINDINGS.md`, `COMPARISON-TODO.md`, and the two handoff docs).

---

## Blocked on work-PC export access (real-data verification)

- [ ] **Cross-env Ramp Detail comparison** — code is done (re-keyed on `PM` via
  `CompareSchema.key_field`) but verified by synthetic fixtures only. When real
  exports land (3 envs being built 2026-06-16): confirm the loaded header names
  the postmile column **`PM`** exactly (after strip/casefold; else update
  `key_col`); run `compare_env.RAMP_DETAIL` on each env pair; COM-recalc; the
  Summary SELF-CHECK must read **9/9 OK**; confirm the diff/one-sided counts
  collapse vs the coarse-key baseline. Add a mid-route-missing-row golden
  fixture. (`scripts/compare_env.py`)
- [ ] **Cross-env Ramp Summary comparison** — code is done (route-keyed,
  blank/all-fail guard, route-key zero-pad normalize) but has **zero golden
  coverage**. When real exports land: run `compare_env.RAMP_SUMMARY` per env
  pair; COM-recalc; confirm SELF-CHECK OK. Add a synthetic per-route fixture
  (planted numeric diff + a route present on only one side).
- [ ] **Audit `consolidate_ramp_summary.parse_pdf`** for the same bug classes the
  TSN parser had — page-furniture leaking into parsed fields, and a silent
  all-parse-fail returning OK.

## Live-export verification (needs TSMIS access — this dev PC can't reach it)

- [ ] **EmptyExport 60 s cap** rests on the site's "Export button present ⟺ data
  loaded" contract. Confirm live that it doesn't false-positive on a slow-but-
  valid load (would mark a real route `empty`; resume re-pulls it, but verify).
- [ ] **Intersection empty markers** (`td.hl-empty` / `Total Intersections = 0`)
  — verify against the live site. Intersections are still a moving target
  (site-side development), so the markers may drift; the general no-download
  fast-fail covers drift, but reconfirm the markers + the empty/retry mapping
  once the site finalizes intersections.

## Security / IT

- [ ] **Code-sign the executable** — the one big remaining IT lever (removes most
  Defender / DLP / SmartScreen friction on the unsigned `.exe`). Needs a
  code-signing certificate; the path is scaffolded in `build/IT-NOTES.md` §7.
  The updater checksum + staged-item allowlist (v0.11.0) are the integrity half;
  the signature half waits on the cert.

## Dormant / watch (no action unless the data changes)

- [ ] **Med Wid flavor-parity gap** (`compare_core._medwid_norm` vs `_medwid_ref`)
  — Excel `VALUE()` accepts more strings as numeric than the Python regex, so an
  exotic Med Wid value (internal space, leading sign, sci-notation, bare/trailing
  decimal point) could make the values flavor and the formulas flavor disagree.
  **DORMANT:** every real Med Wid value across the consolidated TSMIS/TSN files is
  a clean `<digits><letter>` code or `"+++"` (parity-proven over 554k+
  COM-recalc'd cells), so the **current deliverable is accurate**. Decision
  (2026-06-16): **leave dormant**; revisit only if a Med Wid value ever contains
  those characters. Repro + fix sketch in `code-review/COMPARISON-TODO.md`.

## Low priority

- [ ] **`extractall` / junction-traversal safety review** — likely N/A (the
  comparison reads existing files; it does not extract archives), but confirm the
  reset path can't follow a junction/symlink outside its targets, and close.
- [ ] **Audit investigate-list residue** — a few low-confidence items from the code
  review were never individually confirmed closed: values-flavor SELF-CHECK
  independence (does it recompute independently, or share the mirror it checks?),
  updater `_wait_pid_exit` PID-recycle, `open_release_page` URL provenance, env-scan
  page-reuse CONFIG bleed. Spot-check each → close or fix.
- [ ] **Auth file at rest** — `storage_state` is plaintext JSON (documented, not
  encrypted). Defense-in-depth only: consider DPAPI if IT ever requires it.
- [ ] **Report upstream to the TSMIS team** — the site hardcodes
  `highway_sequence_listing.xlsx` as *Ramp Detail*'s export filename (a site
  copy-paste bug; cosmetic for us since we rename via `save_as`).

---

# Feature roadmap (cleaned brainstorm — 2026-06-16)

Captured from a notebook brainstorm and cleaned for picking. Each item is tagged
with a rough **size** [S/M/L] and its dependencies. The **version buckets are a
draft** — re-shuffle freely when we actually pick work. Original notebook numbers
in (parens). 11 raw notes collapsed to 9 features (#6 folded into A1; #7 folded
into B1).

### Proposed version buckets (draft — re-order as priorities shift)

| Version | Theme | Items |
|---|---|---|
| v0.12.0 | Output organization & discoverability | A1, A2, A3 |
| v0.13.0 | Batch export & run control | B1, B2, B3 |
| v0.14.0 | Performance & automation | D1 |
| v0.15.0 | Selection scope & deeper trust | F1, C1 |

Suggested build order within/across versions: **A1 → A2 → B2 → B1 → A3 → B3 →
D1 → F1 → C1**. A1 (labeling) is the low-risk foundation that makes A3 and B3
worth building; B1 (pause) is a prerequisite for B3.

## A. Output organization & discoverability

- [ ] **A1 — Self-describing output filenames** [M] (#5, #6) — Stamp date +
  source/env (and "generated on" date) into the *filename* for consolidations
  and both comparison families, not just the parent folder. Today the
  date/env lives only in the run-folder name; consolidated files use a fixed
  `FILENAME` (`consolidate_*.py` `out_path_for`) and comparison outputs carry no
  date (`compare_env.suggest_name`, `compare_highway_log.suggest_name`), so a
  file copied out of its folder loses all provenance. Foundation for A3 and B3.
- [ ] **A2 — Comparison selector lists only folders that have the report** [S]
  (#2) — The cross-env folder dropdowns list *every* run folder
  (`gui_api` → `list_output_days()`) regardless of whether the chosen report
  exists inside. Filter to runs whose `<report>/` subdir is non-empty, ideally
  re-filtering as the selected report type changes. (`scripts/gui_api.py`)
- [ ] **A3 — Results tab / in-app file browser** [M] (#9) — A tab to open the
  latest per-route files, consolidated workbooks, comparison outputs, failure
  screenshots, and run reports without digging through folders. Much more useful
  after A1; shares a "what's been produced, where" index with A2.

## B. Batch export & run control

- [ ] **B1 — Pause / Resume button** [M] (#7) — A true hold-then-continue
  control (distinct from existing Skip = one route, Cancel = clean resumable
  stop). Enabling primitive for B3. **Decision:** pause-between-routes (simple,
  recommended) vs. pause-mid-route (must park a live browser).
- [ ] **B2 — Auto-consolidate on export finish** [S/M] (#8) — Optional
  per-report "consolidate when export finishes" checkbox; removes the manual
  step for the export-then-consolidate workflow. Pairs with B3.
- [ ] **B3 — "Export Everything" batch job** [L] (#3) — All report types × all
  environments, emitting a deliverable tree organized report-type-first:
  `All Reports / <report type> / <environment> / [per-route files + consolidated]`.
  Must support: selectable subset of report types, **fast mode**, full labeling
  (A1), and **pause/resume across days** → needs a persistent job manifest on
  disk. **Decisions:** (a) new export profile alongside today's
  `output/<run>/<report>/` layout, or a replacement? (b) resume granularity
  (route / report / env). Depends on B1, A1, B2.

## C. Trust / self-audit

- [ ] **C1 — Deeper self-audit so outputs are trustworthy as deliverables** [?]
  (#1) — **NEEDS SCOPING — much may already exist.** Comparisons already have a
  live SELF-CHECK section (headline numbers recomputed independently), a leading
  VERDICT banner, the v0.11.0 incompleteness contract (`⚠ COULD NOT COMPARE
  EVERYTHING`), write-path safety, and CI COM-recalc verification. Identify the
  real remaining gap before building. Likely candidates: extend the same
  self-audit to **consolidations and exports** (not just comparisons), or surface
  a single plain-English **trust summary** to the end user.

## D. Performance & automation

- [ ] **D1 — Adaptive fast mode** [M] (#10) — Persist route durations/failures
  across runs in a durable, aggregated store (keyed by route+report; survives
  updates), then recommend/auto-set worker count, push historically slow routes
  later, and retry chronically-slow ones serially sooner. Per-run outcome CSVs
  exist (`run_report.py`) but aren't aggregated/persistent.

## E. Env-check caching — DECIDED AGAINST (2026-06-16)

- [x] ~~**E1 — Skip env check if already checked today (unless new login)** (#4)~~
  — **Dropped.** The existing `env_check_on_start` Settings toggle already lets
  anyone bothered by repeated scans turn the auto-scan off. Day-caching would only
  add staleness to advisory-only access info — it never gates a real export, which
  preflights live — so it buys nothing the toggle doesn't already give, and isn't
  worth reversing the deliberate "session-only on purpose" design.

## F. Selection scope

- [ ] **F1 — "All routes in a district / all in a county"** [M] (#11) — The site
  forces district → county → route and won't let route be "all," so we must
  enumerate. Needs a district→routes / county→routes mapping, most likely
  sourced live from how the site repopulates the route dropdown after a
  district/county pick. **Most research-heavy item — do a small site-behavior
  spike before committing to a UX.**
