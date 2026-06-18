# TSMIS Exporter — Roadmap & backlog

A living backlog of deferred, blocked, and future-work items, updated
collaboratively. **Nothing here blocked the v0.11.0 release** — these are
follow-ups. (Earlier detail lived in `code-review/` working docs that were
retired into this file; that folder is now local audit scratch only — see
[code-review-prompt.md](code-review-prompt.md).)

---

## Code-review findings (Phase 3 review, 2026-06-18)

A read-only code review (6 risk-domain auditors + adversarial refutation) over commit
`0a4c071` confirmed **45 findings (5 P1 · 17 P2 · 23 P3)**; 12 candidates were rejected on
refutation. Full report with code anchors + fix sketches: `code-review/AUDIT-phase3-0a4c071.md`
(git-ignored scratch). The durable, actionable items, by theme:

### Product-risk — does the app ever report success on bad/missing data? (do first)
- [ ] **P1 `navigate-accepts-wrong-env-after-one-reload`** — the export path never re-checks
  `_site_params_ok` after sign-in (only `require_signed_in`), so if the one corrective reload
  doesn't switch the site's `CONFIG`, **wrong-env data is saved under a folder labeled with the
  selected env** and reported as success. Add an env backstop on the export path mirroring the
  env-scan's `wrong_site` verdict. (Re-confirms the v0.10.4 `AUTH-WRONG-ENV-SILENT-SUCCESS`; see
  [it-and-security.md](it-and-security.md) §8.2.)
- [ ] **P1 `empty-routes-read-as-export-complete`** — an all-empty run shows the green "Export
  complete" headline (`app.js renderCompletion` keys only on `failed===0`). Show an amber
  "Finished with no data" when `saved+exists===0 && empty>0`.
- [ ] **P1 `transient-export-click-failure-recorded-empty`** — a transient failure in the Export
  click window is recorded `empty` and **never retried** (`_retry_failed_routes` excludes
  `empty`). Make the first `EmptyExport` retriable; collapse to `empty` only if it reproduces.
- [ ] **P2 PDF Highway Log silent-drop trio** (`pdf-stale-geometry-carryforward-silent-corruption`,
  `pdf-page-skip-unlogged-when-no-prior-geometry`, `pdf-consolidator-no-row-count-verification`) —
  the cell-rect parser carries forward stale page geometry / skips data lines with **no log**, and
  never cross-checks extracted rows vs the PDF's data-row count at runtime (unlike the loud skip
  accounting elsewhere). Log + guard the geometry-miss paths and add a runtime row-count check.
- [ ] **P2 `report-error-text-blanket-swallow-hides-fatal`** / **`highway-sequence-errored-route-can-record-empty`**
  — `report_error_text` swallows all exceptions to `None` with no log, so a fatal route can be
  misclassified `empty`/`saved` (worst on Highway Sequence, whose empty = button-absence). Log the
  swallow; make Highway Sequence's empty signal positive.

### Data-loss / the Export-Everything store
- [ ] **P1 `reset-deletes-unvalidated-batch-dest`** — "Delete all reports" `rmtree`s the
  user-chosen Everything destination **wholesale** (including any foreign files) and the confirm
  dialog **hides the real path** (shows labels only). Scope deletion to known `<src-env>/` children
  and surface `str(path)` in the confirm list.
- [ ] **P2 `auto-consolidate-rmtree-out-dir-before-export`** — the store clears a report+env folder
  **before** re-export, so a failed/crashed refresh destroys the last-good copy and can read as
  fresh. Stage-and-swap (clear on success), or flag a short-route folder as partial.

### Security / IT (re-confirms existing items + new)
- [ ] **P1 `update-trust-is-tls-plus-sibling-sha-only`** — auto-update authenticity = TLS (Windows
  store, so a TLS-inspection root is trusted) + a same-release `.sha256`; **no signature**.
  Code-signing (already the top IT item below) is the fix; consider a pinned-in-build public key.
- [ ] **P2 `edge-login-cdp-port-unauthenticated-loopback`** — the headed-Edge fallback opens an
  unauthenticated CDP port on `127.0.0.1` for the whole live SSO session; any local process can
  drive the authenticated session. Open it only when CDP recapture is actually needed; close on
  capture. (Document in IT-notes.)
- [ ] **P2 `auth-file-plaintext-no-acl-dpapi`** — re-confirms the auth-at-rest item below (DPAPI/ACL).
- [ ] **P2 updater integrity** (`size-and-checksum-guards-both-skippable`,
  `immediate-death-check-narrow-window`, `no-rollback-when-relaunch-launches-partial-tree`) — size
  + checksum guards can both be off (size 0 / no `.sha256`); the 1.5 s death-check misses a later
  swap-exe crash; a partially-failed rollback still relaunches and the message box claims the old
  version was kept. Harden each.

### Robustness (P2/P3)
- [ ] **P2 `select-report-substring-match-no-exact-guard`** — `select_report` uses `has_text` +
  `.first` (substring) while the env-scan uses exact-first; a future superstring option could
  silently mis-export. Match exactly.
- [ ] **P2 `parallel-reconcile-uses-read-strict-not-lock-tolerant`** / **`parallel-crash-plus-cancel-skips-reconciliation`**
  — fast-mode reconciliation re-marks an Excel-locked-but-complete file `failed`, and a crash+cancel
  combo omits orphaned routes from the run report.
- [ ] **P2 `handle-no-default-branch`** — `gui_api._handle` silently drops an unrecognized message
  kind; add a logging `else`.
- [ ] **P2 ramp-summary parsing** (`ramp-summary-parse-failure-misattributed-to-source`,
  `ramp-summary-duplicate-pop-pattern-misassignment`) — a parser schema-miss is attributed to the
  source PDF (steering the user away from the tool); the Population-group pattern disambiguates two
  identical regexes only by document order.
- [ ] **P3 hygiene batch** (23 items) — stale `gui_worker.py` Tkinter module docstring; the magic
  `wait_for_timeout(1000)`; `update_helper.log` rotation; dev WebView-cache clearing; the
  `_min_cost_pairs` greedy cliff at 8+ duplicates; ramp-summary combined-sheet hard-coded
  coordinates; etc. See the full report.

---

## Ramp comparisons — VERIFIED on real data (2026-06-16 audit)

Cross-env Ramp Detail + Ramp Summary were ruthlessly audited against real 3-env
exports (ssor-prod / ssor-test / ars-prod, 126 routes each) — independent
from-scratch recompute + Excel COM self-check/parity + v0.11.0 regeneration +
adversarial refutation; all methods agreed.
- ✅ **v0.11.0 PM re-key VALIDATED on real data.** Ramp Detail keyed on `PM`
  (+occurrence#, since PM repeats within ~10 county-crossing routes) is correct.
  The user's delivered files were made with the OLD v0.10.4 app (Location-keyed):
  its Ramp Detail PROD-vs-TEST headline of **1,451 diff cells is ~99.4% positional
  inflation**; the TRUE difference is **8 cells / 4 rows + 10 TEST-only ramps**
  (reproduced by regenerating with v0.11.0).
- ✅ **Cross-env Ramp Summary VALIDATED** (route-keyed): PROD-vs-TEST = 32 genuine
  diff cells / 9 routes (confirmed vs raw PDF text); PROD==ARS. All 4 delivered
  workbooks internally sound (SELF-CHECK all OK, parity clean, full coverage).
- [x] ~~**STILL TODO — regression-lock it:** add golden fixtures (Ramp Detail
  mid-route-insert misalignment → PM key collapses it; Ramp Summary planted-diff +
  one-sided route) under `build/check_compare_*.py`.~~ **Done (2026-06-16):**
  `build/check_compare_ramp_detail.py` (a mid-route ramp insert that cascades into
  5 spurious diff cells under coarse keying collapses to 1 one-sided ramp / 0 diff
  cells under PM keying — driven end-to-end through `compare_folders`, plus the
  adapter config `key_col="PM"` pinned) and `build/check_compare_ramp_summary.py`
  (planted 1-cell diff + two one-sided routes + padded/unpadded route-key pairing).
  Both wired into `.github/workflows/checks.yml` (blocking).

## Source-data finding (NOT a parser bug) — from the 2026-06-16 audit

- **TSMIS Ramp Summary source data is internally inconsistent on 9 routes.** Routes
  005, 008, 010, 094, 110, 134, 210, 280, 605 fail the Ramp-Types audit-sum (Σ ramp-type
  counts + no-linework ≠ total_ramps) by 1–9 ramps, IDENTICALLY across all 3 envs — i.e.
  the **source PDF's own Ramp Types breakdown sums short of its stated Total** (some ramps
  in the total aren't itemized into a ramp-type code). **`parse_pdf` is CORRECT** — proven
  against an independent geometric extraction across all 378 PDFs × 14 ramp types (0
  mismatches) and the raw page-2 text. The `_audit_ok` cell correctly flags these routes RED
  (working as designed). Do NOT "fix" the parser to force them green — that would hide a real
  TSMIS data issue. Harmless to the cross-env comparison (the identical gap cancels on both sides).
  - [x] ~~Optional UX: when ONLY the ramp-types audit check fails (hwy/onoff/pop reconcile),
    label the red cell self-explanatorily so users don't read it as a tool bug.~~
    **Done (commit `59b0be6`):** the per-route Audit-OK cell now shows
    `⚠ Source ≠ total: <section>` naming the unreconciled section(s).
  - [ ] Optional: report the inconsistency upstream to the TSMIS team.

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
  code-signing certificate; the path is scaffolded in
  [it-and-security.md](it-and-security.md) §7.
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
  those characters. Repro + fix sketch in
  [comparison-engine.md](comparison-engine.md) (Med Wid flavor-parity).

## Low priority

- [x] ~~**`extractall` / junction-traversal safety review** — confirm the reset
  path can't follow a junction/symlink outside its targets, and close.~~
  **Done (2026-06-16):** empirically verified on the build's Python 3.11 +
  Windows — `shutil.rmtree` REFUSES a top-level directory junction
  (onerror/`islink`; the junction's target is left untouched) and does NOT
  recurse into a nested junction (it removes the link only). `reset_targets`
  builds its list solely from path constants (OUTPUT_ROOT run folders / fixed
  legacy names / FAILURES_DIR / INPUT_ROOT), never user-supplied names. The
  updater's `zipfile.extractall` is also safe: 3.11 sanitizes
  `..`/absolute/drive members, and the zip is SHA-256-verified + self-produced.
  (Probes kept in `code-review/_junction_probe*.py`.)
- [x] ~~**Audit investigate-list residue** — values-flavor SELF-CHECK
  independence, updater `_wait_pid_exit` PID-recycle, `open_release_page` URL
  provenance, env-scan page-reuse CONFIG bleed. Spot-check each → close or fix.~~
  **Done (2026-06-16):**
  - *SELF-CHECK independence* — CLOSED: the values flavor's SELF-CHECK rows are
    live Excel formulas over the written sheets (`compare_core._write_summary`
    `check()`), never the Python `counts` mirror — a genuine internal cross-check.
  - *`_wait_pid_exit` PID-recycle* — CLOSED (fail-safe): the swap takes the
    process handle while the app is still alive, which reserves the PID; any
    OpenProcess failure means the app already exited; the sole residual is a
    fail-safe timeout that leaves the old version intact. Documented in the fn.
  - *`open_release_page` URL provenance* — FIXED: `updater.safe_release_url`
    constrains the opened URL to `https://github.com/<repo>/…`, else the constant
    releases page (locked by `build/check_updater.py`).
  - *env-scan CONFIG bleed* — CLOSED: a stale/mismatched CONFIG read can only
    produce `wrong_site` (combos are unique; `got != [env, src]`), and a clean
    "ok" is gated by the fail-closed `env_verdict`; the unreachable branch
    already avoids reading the parked page URL.
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
| v0.12.0 ✅ SHIPPED | Output labeling, run control & batch export | A1, A2, B1, B2, B3 (A3 deferred) |
| v0.13.0 ✅ SHIPPED | Interface declutter, run lifecycle, accessibility, self-revert | UI/UX batch + Compare sub-tabs + revert-to-previous + env-check split + Everything-store labeling/colour-coding (**A3 & D1 pushed down**) |
| v0.14.0 | Discoverability & performance | A3, D1 |
| v0.15.0 | Selection scope & deeper trust | F1, C1 |

**v0.12.0 shipped 2026-06-16** (commits `f0b7baf` A1 · `8d6820b` A2 · `16863eb`
B1 · `4b8bbf1` B2 · `ba05bb0`+`5b9f2fd` B3). A3 (results tab) was deliberately
moved out — lower priority. All five are golden-checked + mock-verified;
**live-export verification on the work PC is still pending** (the B-series touches
the real export engine).

**v0.13.0 became a UI/UX + trust release, NOT the planned A3/D1 bucket.** It
shipped a header declutter, the right-column run lifecycle (pre-flight summary →
progress with ETA → completion summary + retry-failed), a completion
notification (toggleable, on by default), keyboard-accessible checkboxes +
aria-labels, the Compare cross-env / TSMIS-vs-TSN **sub-tabs**, **revert to the
previous version** from Settings, the **env-check setting split** (after sign-in
on by default / after start off by default), the Everything pane greying with the
other tabs during env check, **env-labeled filenames in the Everything store**,
and **colour-coding error-prone reports/environments** in the Everything tab.
**A3 (results tab) and D1 (adaptive fast mode) were pushed down to v0.14.0** —
they were the original v0.13.0 draft bucket but lost priority to the interface
work. Same caveat as the B-series: **live-export verification on the work PC is
still pending** (the Everything-store filename change touches the export engine).

## A. Output organization & discoverability

- [x] **A1 — Self-describing output filenames** [M] — ✅ SHIPPED v0.12.0 (#5, #6) — Stamp date +
  source/env (and "generated on" date) into the *filename* for consolidations
  and both comparison families, not just the parent folder. Today the
  date/env lives only in the run-folder name; consolidated files use a fixed
  `FILENAME` (`consolidate_*.py` `out_path_for`) and comparison outputs carry no
  date (`compare_env.suggest_name`, `compare_highway_log.suggest_name`), so a
  file copied out of its folder loses all provenance. Foundation for A3 and B3.
- [x] **A2 — Comparison selector lists only folders that have the report** [S] — ✅ SHIPPED v0.12.0
  (#2) — The cross-env folder dropdowns list *every* run folder
  (`gui_api` → `list_output_days()`) regardless of whether the chosen report
  exists inside. Filter to runs whose `<report>/` subdir is non-empty, ideally
  re-filtering as the selected report type changes. (`scripts/gui_api.py`)
- [ ] **A3 — Results tab / in-app file browser** [M] — DEFERRED to v0.14.0
  (pushed down — v0.13.0 became a UI/UX release) (#9) — A tab to open the
  latest per-route files, consolidated workbooks, comparison outputs, failure
  screenshots, and run reports without digging through folders. Much more useful
  after A1; shares a "what's been produced, where" index with A2. (The v0.13.0
  Everything-tab **Saved reports** library + env-labeled filenames are a partial
  down-payment on the "what's been produced, where" index this needs.)

## B. Batch export & run control

- [x] **B1 — Pause / Resume button** [M] — ✅ SHIPPED v0.12.0 (#7) — A true hold-then-continue
  control (distinct from existing Skip = one route, Cancel = clean resumable
  stop). Enabling primitive for B3. **Decision:** pause-between-routes (simple,
  recommended) vs. pause-mid-route (must park a live browser).
- [x] **B2 — Auto-consolidate on export finish** [S/M] — ✅ SHIPPED v0.12.0 (#8) — Optional
  per-report "consolidate when export finishes" checkbox; removes the manual
  step for the export-then-consolidate workflow. Pairs with B3.
- [x] **B3 — "Export Everything" batch job** [L] — ✅ SHIPPED v0.12.0 (report-first physical tree deferred) (#3) — All report types × all
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
