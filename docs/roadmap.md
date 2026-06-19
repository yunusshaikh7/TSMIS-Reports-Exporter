# TSMIS Exporter — Roadmap & backlog

The single forward list — bugs to fix, features to add, and standing concerns. The **changelog**
(what already shipped, per release) is `build/release_notes.md`; the narrative is
[history.md](history.md). This file is what's *left*.

## How to maintain this file

- **Format.** Open item `- [ ]`; done `- [x] ~~…~~ **Done (vX.Y.Z / <commit>)**`. Tag features
  with a rough size `[S/M/L]`; tag code-review findings with severity `P0–P3` + a `slug`.
- **Sections (keep this order; don't reshuffle):** *Next patch* (the immediate worklist) →
  *Feature backlog* → *Standing & cross-cutting* → *Shipped (reconciled record)*. File new items
  under the matching section; start a new theme only if nothing fits. Bugs go under *Next patch*
  (or the findings record), not the feature backlog.
- **Reconcile every session / after each release** — the list rots otherwise. Compare the open
  items + the version table against `git tag` / `version.py` / `build/release_notes.md`; check
  off what shipped (one line), update the version table to reality, and **flag anything deferred
  across multiple releases** for a keep / drop / bump decision. Record *what* shipped; the owner
  decides *where* deferred items go next.
- This is the backlog, **not** the changelog — keep "done" notes to one line; detail lives in
  `release_notes.md` and the docs.

---

## Next patch — code-review fixes (Phase 3 review, 2026-06-18)

A read-only review (6 risk-domain auditors + adversarial refutation) over commit `0a4c071`
confirmed **45 findings (5 P1 · 17 P2 · 23 P3)**; 12 candidates were rejected on refutation. Full
report with code anchors + fix sketches: `code-review/AUDIT-phase3-0a4c071.md` (git-ignored). Do
the field bug + P1s first.

### Field-reported (work-PC logs — CONFIRMED in the field)
- [x] **`update-stage-rename-no-retry`** ✅ **Done (this update)** — wrapped the extract→staged
  rename (+ the follow-on cleanup rmtree) in the swap step's `_retry` (12×0.5 s) so a transient
  Defender/indexer lock retries instead of aborting the stage. Locked by `check_updater.py`
  (`test_stage_rename_retries` + `test_retry_recovers_transient_oserror`). ⚠ FIELD-VERIFY on the
  work PC that staging no longer fails (the Defender timing only reproduces there). Original
  evidence: `code-review/field-update-stage-rename.md`; note in
  [internals/updater-swap.md](internals/updater-swap.md) §3.

### P1 — product-risk / data-loss / security (do first)
- [x] **P1 `navigate-accepts-wrong-env-after-one-reload`** ✅ **Done (this update)** — added
  `common.require_site_params(page)` on the export path (after `require_signed_in`), raising
  `PreflightError` when the app is on a different env/src than selected; no-ops when undeterminable.
  Locked by `check_export_engine.py` (`test_require_site_params`). ⚠ LIVE work-PC re-test (only a
  real site returning the wrong env after OAuth truly exercises it).
- [x] **P1 `empty-routes-read-as-export-complete`** ✅ **Done (this update)** — `renderCompletion`
  shows an amber "Finished with no data" when `saved+exists===0 && empty>0`; `appendLog` no longer
  paints a `saved 0` summary green. Verified in the `#mock` preview.
- [x] **P1 `transient-export-click-failure-recorded-empty`** ✅ **Done (this update)** — a no-download
  `EmptyExport` now PROPAGATES from `_attempt_route`; `_process_route` retries it once in-loop and
  records `empty` only if it reproduces (a positive `is_empty` match stays immediate empty). Locked by
  `check_export_engine.py` (`test_attempt_route_empty` + `test_process_route_empty_retry`). ⚠ LIVE
  work-PC re-test (the true transient click flake only occurs against the real site).
- [x] **P1 `reset-deletes-unvalidated-batch-dest`** ✅ **Done (this update)** — `reset_targets` now
  scopes the Export-Everything store to its known `<src-env>/` children (never rmtree's the dest
  wholesale; foreign files untouched); `reset_preview` returns the real `str(path)`s and the confirm
  dialog shows each under its label. Locked by `check_b3_batch.py` (`test_reset_scopes_batch_dest`);
  dialog verified in the `#mock`.
- [ ] **P1 `update-trust-is-tls-plus-sibling-sha-only`** — auto-update authenticity = TLS (Windows
  store → a TLS-inspection root is trusted) + a same-release `.sha256`; **no signature**.
  Code-signing (Standing § below) is the fix; consider a pinned-in-build public key.

### P2 — bounded correctness / robustness / IT
- [ ] **P2 PDF Highway Log silent-drop trio** (`pdf-stale-geometry-carryforward-silent-corruption`,
  `pdf-page-skip-unlogged-when-no-prior-geometry`, `pdf-consolidator-no-row-count-verification`) —
  the cell-rect parser carries forward stale page geometry / skips data lines with **no log**, and
  never cross-checks extracted rows vs the PDF's data-row count. Log + guard + add a runtime count.
- [x] **P2 `report-error-text-blanket-swallow-hides-fatal`** / **`highway-sequence-errored-route-can-record-empty`**
  ✅ **Done (this update)** — `report_error_text` now LOGS the swallowed probe exception (no longer
  silent), and Highway Sequence's `is_empty` keys on the POSITIVE "No results found" text (hsl.js)
  instead of Export-button absence, so an error page is no longer misread as empty. Locked by
  `check_export_engine.py` (`test_report_error_text` + the Highway Sequence marker checks). ⚠ LIVE
  work-PC re-test of the error-page path.
- [x] **P2 `auto-consolidate-rmtree-out-dir-before-export`** ✅ **Done (this update)** — the Everything
  store now STAGE-AND-SWAPS: each report exports into a `.staging` sibling, swapped into place only on
  a clean finish (discarded on cancel/crash), so a failed refresh never destroys the last-good copy.
  Locked by `check_b3_batch.py` (`test_swap_store_dir`). ⚠ LIVE work-PC re-test of the end-to-end
  crash-preserves-last-good path.
- [ ] **P2 `edge-login-cdp-port-unauthenticated-loopback`** — the headed-Edge fallback opens an
  unauthenticated CDP port on `127.0.0.1` for the whole live SSO session. Open it only when CDP
  recapture is needed; close on capture.
- [ ] **P2 `auth-file-plaintext-no-acl-dpapi`** — re-confirms the auth-at-rest item (Standing §).
- [ ] **P2 updater integrity** (`size-and-checksum-guards-both-skippable`,
  `immediate-death-check-narrow-window`, `no-rollback-when-relaunch-launches-partial-tree`) — size +
  checksum guards can both be off; the 1.5 s death-check misses a later swap crash; a partial
  rollback still relaunches and the message box claims the old version was kept. Harden each.
- [ ] **P2 `select-report-substring-match-no-exact-guard`** — `select_report` uses `has_text` +
  `.first` (substring) while the env-scan uses exact-first; a future superstring option could
  silently mis-export. Match exactly.
- [x] **P2 `parallel-reconcile-uses-read-strict-not-lock-tolerant`** / **`parallel-crash-plus-cancel-skips-reconciliation`**
  ✅ **Done (this update)** — extracted `_reconcile_unaccounted`: it now uses the lock-tolerant
  `_can_resume` (an Excel-locked-but-complete file is trusted, not re-failed) and still reconciles on
  cancel when a worker CRASHED (so a crash's orphaned routes always reach the run report). Locked by
  the new `check_parallel_reconcile.py`. ⚠ LIVE work-PC re-test of the real crash+cancel path.
- [ ] **P2 `handle-no-default-branch`** — `gui_api._handle` silently drops an unrecognized message
  kind; add a logging `else`.
- [ ] **P2 ramp-summary parsing** (`ramp-summary-parse-failure-misattributed-to-source`,
  `ramp-summary-duplicate-pop-pattern-misassignment`) — a parser schema-miss is attributed to the
  source PDF; the Population-group pattern disambiguates two identical regexes only by document order.

### P3 — hygiene (batch where cheap; 23 items)
- [ ] Stale `gui_worker.py` Tkinter module docstring; the magic `wait_for_timeout(1000)`;
  `update_helper.log` rotation; dev WebView-cache clearing; the `_min_cost_pairs` greedy cliff at
  8+ duplicates; ramp-summary combined-sheet hard-coded coordinates; etc. — full list in the report.

---

## This update — the Everything comparison matrix (implemented, unreleased)

On branch `feat/everything-matrix`; not yet released (no version bump/tag). Golden-checked
offline; the LIVE paths below are owed on the work PC.

- [x] **Stage-1 foundation audit** — see the closed-findings record below.
- [x] **8 groundwork code-review fixes** — the field bug + 4 P1s + 3 P2s above are checked off.
- [x] **Comparison matrix [L]** — report × environment grid on the Everything tab. Engine
  `scripts/matrix.py` orchestrates `compare_env` (compare_core untouched): per-cell export +
  comparison freshness (mtime staleness), comparisons cached per baseline under
  `<dest>/comparisons/<baseline>/` (stable dateless names) + a `_results.json` verdict/count cache,
  baseline switch = explicit full recompute. Cells show the **discrepancy count, color-coded**
  (green identical → amber/red by magnitude, stale, needs-export). Per-cell refresh-export
  (live) / refresh-comparison (offline) + refresh-all. Bridge in `gui_api` (`matrix_info`,
  `set_matrix_baseline`, `refresh_cell_export`, `refresh_cell_comparison`, `recompute_matrix`);
  workers `MatrixCompareWorker` / `MatrixExportWorker` (the latter reuses ExportWorker with NO
  manifest, so it can't clobber a paused batch). Locks: `check_matrix.py`, `check_matrix_bridge.py`.
- [x] **export-date-in-UI [S]** — per-(report,env) freshness from file mtime
  (`report_library.cell_ages`), surfaced in the matrix cells (no filename changes — the store
  overwrites in place). Lock: `check_report_library.py`.
- [x] **Intersection app-wide disable [S]** — one gate (`reports.DISABLED_EXPORT_SUBDIRS` +
  `export_reports_status`) shows Intersection **greyed/unpickable** (not hidden) in the Export tab +
  Everything report lists, excludes it from the Saved-reports library + matrix, and rejects it
  server-side; `EXPORT_REPORTS` indices stay stable. Flip back by emptying the set. Lock:
  `check_intersection_gate.py`.
- [x] **Matrix → Everything sub-tab + multi-mode + TSN [L]** (the new phase) — the matrix moved to a
  full-width **sub-tab** of Everything; Highway Log is now **two rows** (Excel + PDF); each row has a
  **comparison-mode dropdown** (cross-env / vs TSN (Excel|PDF) / TSMIS PDF-vs-Excel; greyed where no
  code) + a **TSN file picker**. A **config zone** under the slim activity log holds report +
  **environment-column** show/hide toggles and a global "set all". Refresh is per-cell / **per-row** /
  **per-column** / all, **cancellable + resumable**. TSN drops → `<dest>/_tsn_input/<subdir>/`, sheets →
  `<dest>/comparisons/tsn/`. Additive only — the manual compare code is untouched (the PDF *consolidator*
  gained an additive input_dir/out_path override). App-wide **motion layer** + slow theme cross-fade
  landed alongside. Locks: `check_matrix.py`, `check_matrix_tsn.py`, `check_matrix_bridge.py`.

**Owed on the work PC (live; can't verify on the dev PC):** the field bug's Defender-timing fix; the
wrong-env backstop; the transient-empty retry; `report_error_text`/Highway-Sequence empty;
batch stage-and-swap crash-preserves-last-good; parallel crash+cancel reconciliation; the
matrix's **live per-cell Refresh export** + a full **baseline-switch recompute over a real 6-env
store**; and the **live TSN / PDF-vs-Excel comparisons** (consolidate-store-folder → compare glue;
the compare adapters themselves are already golden-locked). Before releasing: bump `version.py` +
`build/release_notes.md`.

---

## Feature backlog

From a notebook brainstorm (2026-06-16); size `[S/M/L]`. Their original version buckets are now in
the Shipped record below. **⚠ A3 and D1 were the planned v0.13 *and* v0.14 themes but got displaced
both times by interface + Highway Log work — deferred 3× and now unscheduled. Decide: bump, drop,
or accept as someday.**

- [ ] **A3 — Results tab / in-app file browser** [M] (#9) — a tab to open the latest per-route
  files, consolidated workbooks, comparison outputs, failure screenshots, and run reports without
  digging through folders. The v0.13.0 Everything-tab **Saved reports** library + env-labeled
  filenames, and now the **comparison matrix** (this-update: a per-cell view of what's been exported
  + compared, with freshness, in the Everything tab), are a partial down-payment on the
  "what's been produced, where" index this needs. **A3 stays parked** (do not revive). *(deferred 3×.)*
- [ ] **C1 — Deeper self-audit so outputs are trustworthy as deliverables** [?] (#1) — **NEEDS
  SCOPING — much may already exist.** Comparisons already have a live SELF-CHECK, a VERDICT banner,
  the v0.11.0 incompleteness contract, write-path safety, and CI COM-recalc. Identify the real gap
  first: likely extend the same self-audit to **consolidations + exports**, or surface a single
  plain-English **trust summary** to the user.
- [ ] **D1 — Adaptive fast mode** [M] (#10) — persist route durations/failures across runs in a
  durable aggregated store (keyed by route+report; survives updates), then recommend/auto-set worker
  count, push historically slow routes later, and retry chronically-slow ones serially sooner.
  Per-run CSVs exist (`run_report.py`) but aren't aggregated/persistent. *(deferred 3×.)*
- [ ] **F1 — "All routes in a district / all in a county"** [M] (#11) — the site forces
  district → county → route and won't let route be "all", so we must enumerate. Needs a
  district→routes / county→routes mapping, likely sourced live from how the site repopulates the
  route dropdown after a district/county pick. **Most research-heavy — do a small site-behavior
  spike before committing to a UX.**

---

## Standing & cross-cutting (open)

### Security / IT
- [ ] **Code-sign the executable** — the one big remaining IT lever (removes most Defender / DLP /
  SmartScreen friction on the unsigned `.exe`, and is the real fix for the P1 auto-update-trust
  finding above). Needs a cert; path scaffolded in [it-and-security.md](it-and-security.md) §7. The
  updater checksum + staged-item allowlist (v0.11.0) are the integrity half; the signature half
  waits on the cert.
- [ ] **Auth file at rest** — `storage_state` is plaintext JSON (documented, not encrypted).
  Defense-in-depth; consider Windows DPAPI (`CryptProtectData`) if IT ever requires it. (Same as the
  P2 `auth-file-plaintext-no-acl-dpapi` finding.)

### Live-export verification (owed on the work PC — this dev PC can't reach TSMIS)
- [ ] **EmptyExport 60 s cap** rests on the site's "Export button present ⟺ data loaded" contract.
  Confirm live it doesn't false-positive on a slow-but-valid load.
- [ ] **Intersection empty markers** (`td.hl-empty` / `Total Intersections = 0`) — verify against the
  live site once intersections finalize (still site-side development; markers may drift).
- Several **Next-patch** fixes also need a live re-test here (the wrong-env backstop, the
  empty-routes UX, the staging retry, `report_error_text`/Highway-Sequence empty).

### Upstream / external (report to the TSMIS team)
- [ ] Site hardcodes `highway_sequence_listing.xlsx` as *Ramp Detail*'s export filename (cosmetic
  for us — we rename via `save_as`).
- [ ] Ramp Summary **source-data** inconsistency on 9 routes (see the Shipped record — not our bug).

### Dormant / watch (no action unless the data changes)
- [ ] **Med Wid flavor-parity gap** (`compare_core._medwid_norm` vs `_medwid_ref`) — Excel `VALUE()`
  accepts more strings as numeric than the Python regex, so an exotic Med Wid value could make the
  values + formulas flavors disagree. **DORMANT:** every real Med Wid value is a clean
  `<digits><letter>` or `"+++"` (parity-proven over 554k+ COM cells), so the current deliverable is
  accurate. Revisit only if a value ever contains those characters. Detail in
  [comparison-engine.md](comparison-engine.md) (Med Wid flavor-parity).

---

## Shipped (reconciled record)

What landed, so the open list stays honest. Full changelog: `build/release_notes.md`.

### Version buckets — reconciled to reality (current: v0.14.2)

| Version | Date | What actually shipped |
|---|---|---|
| **v0.11.0–0.11.1** ✅ | Jun 16 | Audit-hardening patch (no-download fast-fail, token redaction, updater SHA-256, PM-keyed compares, incompleteness contract); TSN converter proven flawless. |
| **v0.12.0** ✅ | Jun 16 | **A1, A2, B1, B2, B3** — self-describing filenames, compare-folder filter, Pause/Resume, auto-consolidate, Export Everything. |
| **v0.13.0–0.13.1** ✅ | Jun 17 | UI/UX declutter, run lifecycle + ETA + completion summary, completion notification, accessibility, Compare sub-tabs, revert-to-previous, env-check split, Everything-store labeling/colour-coding; duplicate-key similarity pairing. |
| **v0.14.0–0.14.2** ✅ | Jun 18 | **Highway Log PDF** consolidator + PDF-sourced comparisons + corrected 31-column labels + roadbed-aware key + HL Compare sub-tab + consolidate-label clarity + UI-vs-logic audit. |

> **The planned "A3 / D1" buckets never shipped** — v0.13 became a UI/UX release and v0.14 became
> Highway Log accuracy, displacing A3 (results tab) and D1 (adaptive fast mode) each time. They're
> now in the Feature backlog above, flagged 3×-deferred.

### Closed findings & decisions (record)
- [x] **Stage-1 foundation audit — consolidate + cross-env compare VERIFIED on the full 6-env
  batch** (2026-06-18; HSL / Ramp Detail / Ramp Summary). 18/18 consolidations + 15/15 cross-env
  comparisons (baseline SSOR-PROD) proven cell-accurate ≥3 independent ways (independent
  from-scratch recompute · values-flavor content · Summary literals · Excel-COM F9 of the
  formulas flavor with SELF-CHECK all OK + flavor parity) + raw-source spot checks. **Zero tool
  bugs.** The Ramp Summary "Source ≠ total" 9-route quirk reproduces identically on all 6 envs
  (SOURCE quirk, correctly flagged RED — not fixed away; geometric parser cross-check = 0
  mismatches across 756 PDFs). HSL cross-env (no prior audit) now covered: an apparent diff-cell
  over-count was traced to duplicate-PM pairing — an independent OPTIMAL recompute matches the
  workbook exactly (the engine's similarity pairing is correct; ~4,474 dup groups/pair). ARS-PROD
  == SSOR-PROD for RD/RS; HSL has 2 genuine ARS-PROD diffs (real source difference, confirmed).
  The 2026-06-16 closed finding below reproduces exactly. New lock: **`build/check_compare_highway_sequence.py`**
  (HSL adapter end-to-end: PM key, "Highway Locations" sheet, "(col X)" unnamed-column labels)
  wired into `checks.yml`. Full report: `code-review/AUDIT-stage1-foundation.md` (git-ignored).
- [x] **Cross-env Ramp comparisons VERIFIED on real data** (2026-06-16, 3-env × 126 routes,
  ≥3 independent methods): v0.11.0 PM re-key correct (Ramp Detail PROD-vs-TEST true diff = 8 cells /
  4 rows + 10 TEST-only, vs the old 1,451-cell positional inflation); Ramp Summary PROD-vs-TEST = 32
  genuine diff cells / 9 routes; PROD==ARS. Regression-locked by `build/check_compare_ramp_detail.py`
  + `check_compare_ramp_summary.py`.
- [x] **Ramp Summary source-data inconsistency on 9 routes** (005/008/010/094/110/134/210/280/605):
  the source PDF's own Ramp-Types breakdown sums short of its stated Total by 1–9 ramps, identically
  across envs. **`parse_pdf` is CORRECT** (0 mismatches vs an independent geometric extraction over
  378 PDFs × 14 ramp types); `_audit_ok` flags these RED on purpose (`⚠ Source ≠ total: <section>`,
  commit `59b0be6`). **Do NOT "fix" the parser to force them green.** (Upstream report is open above.)
- [x] **`extractall` / junction-traversal safety** (2026-06-16) — verified safe: `shutil.rmtree`
  refuses a top-level junction and doesn't recurse a nested one; `reset_targets` builds its list from
  path constants only; the updater's `extractall` is sanitized by 3.11 + SHA-256-verified.
- [x] **Audit investigate-list residue** (2026-06-16) — SELF-CHECK independence (live formulas, not
  the Python mirror); `_wait_pid_exit` PID-recycle (fail-safe); `safe_release_url` URL provenance
  (FIXED, locked by `build/check_updater.py`); env-scan CONFIG bleed (fail-closed). All closed.
- [x] **E1 — env-check day-caching** — DECIDED AGAINST (2026-06-16): the `env_check_*` Settings
  toggles already cover it, and access info is advisory-only (never gates a real export).
