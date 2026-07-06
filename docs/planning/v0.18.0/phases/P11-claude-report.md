# P11 — Documentation + audit/roadmap reconciliation (LAST phase) — Claude report

## 1. Phase ID and name
**P11 — Documentation + audit/roadmap reconciliation [blocking; the LAST phase].** Reconcile the
canonical `docs/` library + `CLAUDE.md` + `CHANGELOG.md` + the CR-002 doc set to the refactored
v0.18.0 HEAD; write every §J2 audit disposition + the residual hard-deferrals + the now-implemented
M03 destination-ownership marker into `docs/roadmap.md`; fold the planning folder + CR-001/CR-002
amendments in; link `docs/work-pc-validation.md` into `docs/INDEX.md`; set `version.py` to the
v0.18.0 release target.

## 2. Baseline commit
`5d149ea` (P13 committed; clean tree apart from the untracked `docs/planning/` workspace).

## 3. Changes made
Docs-only reconciliation + the single `version.py` bump. **No `scripts/` product code changed**
(`compare_core` / `outcome` / engine / GUI all untouched). Verified each doc claim against shipped
HEAD code before writing (the protected "docs accuracy" contract); used six parallel read-only
`Explore` agents to produce drift reports, then **personally verified every contested claim** against
the code (I am the sole writer; the agents only reported).

- **`version.py`** `0.17.1 → 0.18.0` — the release-coherence change (the About box / PE
  FileVersion-ProductVersion via `app.spec`, the updater's reported version, and `release.yml`'s
  `TAG == v<__version__>` gate all read it). No check pins it to `0.17.1` (the `v0.17.1` strings in
  `check_stable_ids` / `check_gui_bridge` are frozen-order comments). Consistent with CR-002-RM6
  ("version.py stays 0.18.0 target").
- **`CHANGELOG.md`** — a user-facing `## v0.18.0` section (the new Intersection Detail (PDF) report;
  partial-never-green; transactional last-good; the safer updater; junction-safe reset; the under-the-
  hood overhaul). `gen_release_notes.py` needs this section to publish the release body.
- **`README.md`** — version badge `0.14.2 → 0.18.0`; "Eight report types"; the Supported-reports table
  gains both PDF editions; Intersection consolidation/comparison; project-structure refresh (`common.py`
  shim, `report_catalog` SoT, `task_coordinator`); "no automated tests" → the golden-check suite.
- **`CLAUDE.md`** — report **6b** in the Supported-reports table; new **conventions** (the
  producer-owned outcome contract, transactional consolidation + `consolidation_meta`, read-counts-by-
  header-label, the `report_catalog` SoT + append-only stable IDs); the repo-layout orientation block
  refreshed for the refactored module set.
- **`docs/architecture.md`** — the three registry tables corrected (EXPORT 8 / CONSOLIDATE 9 / COMPARE
  18; Intersection now consolidates+compares; Intersection Detail (PDF) added; the auto-consolidate map
  note fixed); the matrix row count `7 → 8`; a new **"v0.18.0 — structural & engineering overhaul"**
  feature bucket mapping every change to its owner doc.
- **`docs/reports.md`** — eight reports; the stale **"APP-WIDE DISABLED / EXPORT-ONLY"** Intersection
  framing replaced with the enabled+consolidating+comparing reality (the gate set is now empty); a new
  **Report 6b** section; `save_intersection_detail_pdf`; the COMPARE table + the "add a report" recipe
  (route through `report_catalog`, update `mock.js`, mirror PDF-edition special-cases).
- **`docs/comparison-engine.md`** — a v0.18.0 regression-lock reaffirmation (`compare_core`
  byte-identical, `context_fill` NOT ported); the `compare_tsn_common` (`ctc`) substrate; the
  Intersection Detail (PDF) comparator; **§9f rewritten to the v0.17.8 behavior** (`CONTEXT_FIELDS=()`
  compare-everything, the J–P+signalized→`S` crosswalk, numeric-pad norm, read-time TSN re-normalization,
  the wired Report View); **§9e corrected to the 66-category signal fold**.
- **`docs/tsn-parsers.md`** — the Intersection Detail section corrected to v0.17.8 (control crosswalk,
  Date-of-Record now counted, `CONTEXT_FIELDS=()`, numeric norm, Report View, the revised canary); the
  Intersection Summary section corrected to the 66-category fold (58 both / 8 only-TSMIS / 0 only-TSN).
- **`docs/engine-and-reliability.md`** — a new section: the **outcome contract** (completion × artifact,
  partial-never-promotes), **transactional consolidation** (`consolidation_meta` / `artifact_store` /
  `cache_envelope`), the **`common.py` shim** over the engine leaves, and the **P8c live-path hardening**.
- **`docs/gui.md`** — the UI-stack file list (the `ui-*.js` / `mock.js` / `contract.js` split); the
  module-ownership table (`task_coordinator`, `contract`, the `gui_endpoint`/`gui_matrix`/`gui_win32`
  split); the worker list (+ `ActiveEnvCheckWorker` + the four matrix workers); the message kinds
  (+ `matrix_*` / `active_env_done`, contract-defined); the frozen-only cache clear.
- **`docs/internals/gui-bridge.md`** — a v0.18.0 structural note (task_coordinator epoch / exactly-once,
  the contract-keyed dispatch dict, the `GuiMatrixMixin`, the front-end split) with a line-anchor-drift
  caveat. **`docs/internals/export-engine.md`** — the `common.py`-is-a-shim note.
  **`docs/internals/updater-swap.md`** — the **fail-closed checksum** corrected in **four** places (the
  now-false "size-only fallback") + the staged re-hash / zip-slip / retry.
- **`docs/build-and-release.md`** — the updater hardening (fail-closed checksum, staged re-hash, zip-slip,
  retry, pagination, 2.0 s death-check, log rotation, frozen-only cache clear); the reproducible hash-
  pinned build + `check_build_env`; the windowed exact-artifact self-test (`-SelfTest` no longer a console
  exe); `APP_MODULES` growth + `check_app_modules`; `.sha256` per-variant enforcement; the **work-PC
  evidence kit**; the **two-tier release** framing; version 0.18.0.
- **`docs/roadmap.md`** — a v0.18.0 status banner + the **§J2 audit-disposition section** (every still-
  open Phase-3 finding individually marked Resolved / v0.18.1-evidence-driven / hard-deferred), the
  **M03 marker recorded as implemented**, the **hard-deferrals** (O2/DPAPI, cert/A03, `min-cost-pairs`),
  and the version table (v0.17.1 + v0.18.0 rows).
- **`docs/INDEX.md`** — the `work-pc-validation.md` row (+ the two-tier note).

## 4. Files affected
16 tracked files: `version.py`; `CHANGELOG.md`; `README.md`; `CLAUDE.md`; `docs/INDEX.md`,
`architecture.md`, `build-and-release.md`, `comparison-engine.md`, `engine-and-reliability.md`,
`gui.md`, `reports.md`, `roadmap.md`, `tsn-parsers.md`; `docs/internals/export-engine.md`,
`gui-bridge.md`, `updater-swap.md`. (+516 / −160.) `docs/planning/` stays untracked.

## 5. Architectural decisions
- **Verify-then-write.** Every structural/behavioral claim checked against HEAD before editing.
  Four contested agent claims were resolved by reading the code directly: (a) the Intersection Detail
  **Report View IS wired** via `extra_sheet_writer` (`compare_intersection_detail_tsn.py:832`) — the
  agent misread; (b) the webview-cache-clear **is frozen-only** (`updater.py:1106-1112`); (c)
  `outcome.py` vocab is `complete|partial|no_data|cancelled|failed × promoted|new_unpromoted|
  previous_preserved|none`; (d) **`wait_js` has no config-error validation at HEAD** (see §10/§11).
- **`version.py` → 0.18.0 in P11.** The release-readiness phase owns the bump (the candidate must
  report 0.18.0; the CHANGELOG has a v0.18.0 section; release.yml gates on tag↔version parity).
- **Scope discipline.** Only the spec's "Affected" docs + the CR-002 doc set were touched. Internals
  line-anchor drift was corrected where I edited and where a claim was false, but a full `file:NNN`
  re-sync of the deep-dive internals was left out of scope (flagged in the gui-bridge note).

## 6. Compatibility and migration handling
None required — docs-only + a version string. No persisted-data format, no API, no check contract
changed. `app.spec` reads `__version__` dynamically (no spec edit needed). The two-tier release framing
(RM02) is preserved throughout (v0.18.0 = offline candidate; v0.18.1 = field-validated sign-off).

## 7. Tests and commands run
- `build/check_no_misspelling.py` — the required P11 gate.
- `git grep` for the transposed product name across **tracked** files (the standing CI-guard contract).
- The **full offline suite**: all 75 `build/check_*.py` + 3 `build/check_*.js` (because `version.py`
  is a product-code change).
- A relative-link checker over every non-planning `.md` (the required link/anchor review).
- `git status` / `git diff --stat` / `git diff --name-only -- scripts/` for diff hygiene.

## 8. Results
- **`check_no_misspelling`:** the sole offender is the known untracked
  `docs/planning/v0.18.0/phases/P10-codex-review.md:177` (CI runs on the committed tree, where
  `docs/planning/` doesn't exist → green). **Tracked content is transposition-clean** — my edits added
  none (the lone tracked `git grep` hit is `check_no_misspelling.py`'s own self-documenting docstring,
  which the guard skips via `_SELF`; pre-existing).
- **Full suite:** **74/75 Python + 3/3 Node pass.** The one "fail" is `check_no_misspelling` on the
  untracked-planning hit above — the known baseline, not a regression. So the `version.py` bump and all
  doc edits break **zero** checks.
- **Links:** all relative file links across the docs resolve; in-page anchors follow the doc's existing
  `#report-4b--…` convention.
- **Diff hygiene:** exactly 15 docs + `version.py`; **no `scripts/` changes** (`git diff --name-only --
  scripts/` is empty → `compare_core`/outcome/engine/GUI untouched); `docs/planning/` untracked.

## 9. Before/after measurements
- `version.py __version__`: `0.17.1 → 0.18.0`.
- Reports documented: 7 → **8** (CLAUDE.md table, README, reports.md, architecture.md).
- architecture.md registry tables: EXPORT 7→8, CONSOLIDATE 6→9, COMPARE 7→**18** (verified against
  `report_catalog`: EXPORT 8 / CONSOLIDATE 9 / COMPARE 18).
- Intersection Detail vs-TSN canary in the docs: v0.17.0 suppressed-context (5,632 diffs) →
  **v0.17.8 compare-everything** (statewide ≈163,353 Excel / 163,361 PDF, v0.18.1 real-data; offline
  behavior fixture locked).
- Intersection Summary categories in the docs: 72 union → **66** (J–P → Signalized fold).
- Open Phase-3 audit findings: now each carries an individual written disposition in `docs/roadmap.md`.

## 10. Deviations from the approved plan
- **`wait-js-fstring-interpolation-unvalidated` — a discovered plan↔code discrepancy.** §J2 records this
  P3 finding as **Resolved in P8b** (a validator that raises a config error, "locked by
  check_export_engine"). Verified at HEAD: `exporter.py:432-433` interpolates `spec.wait_js(route)` into
  the wait JS with **no validation**; there is no validator in `exporter`/`run_report`/`errors`, and no
  `check_export_engine` case asserts it; the P8b/P8c reports never mention it; the *pre-existing*
  `internals/export-engine.md:463` already says a malformed `wait_js` "times out cryptically." Per the
  docs-accuracy contract I did **not** record it as resolved and did **not** implement it (out of P11
  scope — that's a behavior change). I recorded it honestly in `docs/roadmap.md` §J2 as **carried forward
  to v0.18.1 hardening**, and flag it here for Codex.
- **Internals line-anchor drift not fully re-synced** (deliberate). The deep-dive internals
  (`gui-bridge.md`, `export-engine.md`, `updater-swap.md`) carry many `file:NNN` anchors that drifted in
  the refactor. I corrected the **false claims** + added structural notes, but a full anchor re-sync is
  out of P11's practical scope (these are future-development deep-dives, not release-gating). Flagged in
  the gui-bridge structural note.
- **Out-of-scope docs left untouched** (scope discipline): `it-and-security.md`,
  `verification-and-testing.md`, `history.md`, `lessons.md`, `auth-and-signin.md`, `highway_log/*`,
  `website.md` — none are in the spec's P11 "Affected" list or the CR-002 doc set. The evidence-kit
  handoff is owned by `work-pc-validation.md` (committed P13, now linked from INDEX).

## 11. Known limitations and external verification
- **`wait_js` validation** is the one open accuracy item (above) — carried to v0.18.1; needs the
  validator + a `check_export_engine` case before any "resolved" claim.
- **`non-hl-loaders-dont-collapse-tab-whitespace`** (CR-002) recorded as a deferred normalization
  inconsistency in roadmap §J2 (HL + Highway Sequence collapse tab whitespace at load; Ramp Detail +
  Intersection Detail do not — low impact, locked counts stand).
- **The v0.18.1 statewide canaries** (Int-Detail Excel 163,353 / PDF 163,361) are **real-data** and
  remain **work-PC/v0.18.1-deferred** (the dev PC can't reach TSMIS); the offline lock is the synthetic
  behavior fixture. All other doc claims are verified against committed HEAD code.
- **External verification owed:** the entire v0.18.1 work-PC acceptance set (see `work-pc-validation.md`
  §3) — this is by design (two-tier model).

## 12. Exact diff scope Codex should review
`git diff 5d149ea -- version.py CHANGELOG.md README.md CLAUDE.md docs/` (16 files; +516/−160). Suggested
focus:
1. **Accuracy of the corrected behavioral claims** vs HEAD code — especially comparison-engine.md §9e
   (66-cat fold) / §9f (v0.17.8 compare-everything + the `S` crosswalk + the wired Report View),
   tsn-parsers.md's Intersection sections, and the updater-swap.md/build-and-release.md **fail-closed
   checksum** (the now-false size-only fallback removed in 4 places).
2. **The architecture.md registry tables** (EXPORT 8 / CONSOLIDATE 9 / COMPARE 18) vs `report_catalog.py`.
3. **The roadmap §J2 disposition section** — completeness + honesty, especially the discovered
   **`wait_js`** carry-forward (do you agree it is NOT closed in code?) and the hard-deferral list.
4. **`version.py` → 0.18.0** — agree it belongs in P11, and that no offline check depends on the old
   value (full suite is green minus the known untracked-planning misspelling hit).
5. **Scope** — confirm the out-of-scope docs (§10) were correctly left, and that `docs/planning/` is
   untracked / `scripts/` is untouched.

---

## Remediation — Codex review round 1 (`BLOCKED`)

**Round addressed:** P11 Codex review round 1 — verdict `BLOCKED` (2 blocking + 1 non-blocking). Both
blockers were legitimate misses: I updated the user-facing docs but left **parallel current-state
claims** in the same files describing the pre-CR-002 / pre-P10 state. Every finding was verified against
the workspace before acting.

### Finding dispositions
- **P11-B01 (blocking) — `FIXED`.** Current comparison/report/matrix sections still described the
  7-report / incomplete-PDF-edition state. Verified at HEAD: `reports.EXPORT_REPORTS` = 8,
  `reports.matrix_rows()` = 8 (incl. `intersection_detail_pdf`), `tsn_matrix_extra_rows()` = `[]`;
  `compare_env.INTERSECTION_DETAIL_PDF` exists; `intersection_detail_pdf` shares `tsn_subdir="intersection_detail"`;
  both PDF editions lack inline auto-consolidators. All confirmed Codex's evidence — fixed.
- **P11-B02 (blocking) — `FIXED`.** `docs/internals/updater-swap.md` still carried the pre-P10 `sleep(1.5)`
  death check and "cache clear runs in dev / every launch." Verified at HEAD: `updater.py:609-613`
  (`_DEATH_CHECK_TOTAL_S=2.0`, `_DEATH_CHECK_INTERVAL_S=0.25`) and `updater.py:1105-1112`
  (`_recover_store_promotions()` before the gate; `_clear_webview_caches()` below `if not is_frozen()`).
  Confirmed Codex's evidence — fixed (and §7 had the ordering backwards, also corrected).
- **P11-N01 (non-blocking) — `DEFERRED`.** Stale PDF-edition **product-code comments**
  (`matrix.py:340-343,355`, `reports.py:61-63`). Codex itself says "do not edit product code in P11
  unless scope is explicitly expanded." P11 is docs-only, so deferred to the next source-touching pass /
  v0.18.1; recorded here and left for that phase. (No `scripts/` edits in this remediation.)

### Remediation changes (docs-only; still no `scripts/` changes)
- **`docs/comparison-engine.md`** — §9c env-family: added the `INTERSECTION_DETAIL_PDF` adapter row +
  noted Intersection Detail (PDF) in the "flat, PDF-sourced" prose. §12: rows `7 → 8` (added the
  Intersection Detail (PDF) row + `compare_env.INTERSECTION_DETAIL_PDF`); rewrote the per-row MODE list
  — `env` = **all 8 rows**, `tsn` = **every** report via `matrix.tsn_comparator_for` (each PDF row shares
  its Excel sibling's TSN subdir), `vs_excel` = the **two** PDF-vs-Excel self-checks. §12b: both "ALL
  reports" lists now include Intersection Detail (PDF) (8 reports).
- **`docs/reports.md`** — the `group="env"` summary now lists the Intersection env rows + both PDF
  editions + the two PDF-vs-Excel self-checks (the table below it was already correct).
- **`docs/architecture.md`** — the B2 bucket now names **both** PDF editions as the inline-auto-consolidate
  exceptions (scratch-convert via the matrix); the `tsn_subdir` sentence now states each PDF edition shares
  its Excel sibling's subdir (`intersection_detail_pdf → intersection_detail`).
- **`docs/internals/updater-swap.md`** — replaced the `sleep(1.5)` death check with the ~2.0 s / 0.25 s
  windowed-poll contract in all five places (§5, the OpenProcess safety note, the §10 sequence, the §13
  error table, the §13 gotcha); rewrote §7 to the real `cleanup_leftovers` order (store-recovery every
  launch → frozen gate → frozen-only cache clear + staging removal) and flipped the now-inverted
  "runs in dev too" gotcha to "frozen-only (P10)."

### Updated verification (remediation is docs-only — no product code, so the check suite is unaffected)
- **Residual-drift sweep:** `grep` for "all 7 reports" / "ALL reports" 7-lists / "All rows but HL-PDF" /
  "RS/RD/HSL …greyed" / "Highway Log (PDF) has no auto-consolidator" / "every other report uses its own"
  across the edited docs → **none remain** (the lone "every other report uses its own" hit is inside the
  corrected architecture sentence; the updater-swap "1.5" hit is the deliberate "hardened from `sleep(1.5)`"
  historical reference; "every launch" now correctly scopes store-recovery).
- **Registry/matrix probe:** `EXPORT_REPORTS` 8 · `matrix_rows()` 8 (incl. `intersection_detail_pdf`) ·
  `tsn_matrix_extra_rows()` `[]` — the docs now match.
- **`build/check_report_catalog.py`** — PASS. **`build/check_no_misspelling.py`** — only the known
  untracked `docs/planning/…/P10-codex-review.md:177` hit; tracked-only `git grep` for the transposition
  finds only the guard's own self-documenting docstring (pre-existing). **`git diff --check 5d149ea --
  . ':!docs/planning'`** — clean. **Relative-link check** over all docs — resolves.
- **Diff scope unchanged:** 15 docs + `version.py`; `git diff --name-only 5d149ea -- scripts/` is **empty**
  (`compare_core`/engine/GUI untouched); `docs/planning/` untracked.

### Changed measurements
- comparison-engine.md matrix description: 7 → **8** reports (Everything matrix §12 + by-day §12b).
- comparison-engine.md §9c cross-env adapter table: 7 → **8** rows (added `INTERSECTION_DETAIL_PDF`).
- No canary / count changes (the §9e/§9f corrections were already in round 1; this round added no new
  numeric claims). Diff grew from +516/−160 to **+564/−197** (16 files = 15 docs + `version.py`; docs-only).
