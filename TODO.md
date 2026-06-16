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

- [ ] **`extractall` / junction safety review** — likely N/A (the comparison reads
  existing files; it does not extract archives). Confirm and close.
- [ ] **Distill `code-review/` into this list** and retire the working docs once
  their remaining open items are all captured here.
