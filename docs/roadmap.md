# TSMIS Exporter — Roadmap & backlog

The single forward list — bugs to fix, features to add, and standing concerns. The **changelog**
(what already shipped, per release) is `CHANGELOG.md`; the narrative is
[history.md](history.md). This file is what's *left*.

> **▶ Owner app-consistency & output-model backlog (13 notes, 2026-07-17) — captured + tracked;
> VERIFY-FIRST.** A 13-item owner list (comparison logging, an Excel-vs-PDF matrix, the
> new/edited-report workflow, matrix date-rearrange, unique comparison names, present-only day
> pickers, manual-Compare autosave + dropdown, unified date-stamped export folders, cross-surface
> export consistency, output-folder standardization, single-pass dual-format export,
> date-on-every-export) is captured + triaged by lane/risk/sequencing in
> **[docs/planning/app-consistency-backlog.md](planning/app-consistency-backlog.md)**. **These are
> owner OBSERVATIONS, not confirmed defects — Step 0 of each is a code-verification pass (some may
> already be correct or only partially true).** The output-model spine (items 9/10/11/13 +
> 5/6/7/8/12) has a design spec:
> **[docs/planning/output-model-unification.md](planning/output-model-unification.md)** (its
> current-state map is verify-first too). Priority: comparison-perfection first; items 1
> (comparison logging) + 5 (unique names) fold in alongside; the rest are design-first (Claude)
> then a future sol-002 for the export mechanics.

> **v0.18.1 — field-validated close-out (SHIPPED 2026-06-26).** The work-PC sign-off release on top of
> the v0.18.0 candidate, bundled in ONE commit (`e2bfade`; tag `v0.18.1` pushed → `release.yml` published
> the 3 zips + `.sha256`). **(A)** report-dropdown selection by stable **`data-value`** + reveal the nested
> `cs-submenu` fly-out — survives the TSMIS site's flat→nested report-menu migration (live on **dev**, prod
> to follow) WITHOUT breaking the flat **prod** menu; **(B)** the matrix **queue-phantom** fix (push state
> on every queue mutation); **(C)** **`wait_js`** config-error validation (the §J2 carried-forward item,
> now CLOSED in code — see below); **(D)** **website-style report grouping** (flat Highway Log/PDF/Sequence
> + Ramp/Intersection groups; catalog `_PICKER_ORDER` + short leaf labels); **(E)** **Highway
> Detail/Summary reserved-DISABLED groundwork** (append-only stable ids 8/9, stub specs that refuse to save,
> greyed "coming soon" picker, absent from matrix/compare/consolidate); + the Intersection Detail
> **"Roadbed"→"Route Suffix"** comparison-column rename. All offline checks + both frozen self-tests green;
> **`compare_core` untouched**.
>
> **Status (updated 2026-06-30):** `main` reconciliation is **DONE** — `main` was superseded onto the
> v0.18.x tree (`-s ours` merge `9514359`) and is now at **v0.18.4**, with the v0.18.2/3/4 field hotfixes
> shipped on top (see the *Shipped* table). The remaining owed item is the **work-PC operational sign-off**,
> tracked under *Next version (v0.18.5)* below (live verification of the field fixes + the §3 checklist).
> **Highway Detail/Summary enablement** stays site-gated.

> **v0.18.0 — structural & engineering overhaul (the offline-validated CANDIDATE).** A large internal
> refactor (engine leaf split / `common.py` shim, the outcome + transactional-artifact contracts, a
> report-catalog SoT, the GUI endpoint split + front-end modularization, the regression-locked
> `compare_core` left byte-identical) **plus** the **Intersection Detail (PDF)** report family
> (forward-ported from v0.17.8, CR-002) and packaging/updater hardening (fail-closed checksum, staged
> re-hash, hash-pinned reproducible build, the work-PC evidence kit). The **Phase-3 audit is reconciled
> below (§J2 dispositions)** — every still-open finding is individually marked Resolved / v0.18.1
> evidence-driven / hard-deferred. **Two-tier release:** v0.18.0 is offline-provable; **v0.18.1** is the
> field-validated close-out OF THE OVERHAUL. The full work-PC **operational sign-off**
> ("enterprise-ready") was DEFERRED past v0.18.1 and now cuts as **v0.18.5** (see *Next version* +
> [work-pc-validation.md](work-pc-validation.md)) — not yet claimed.
>
> ---
>
> **v0.17.1 SHIPPED — hotfix on v0.17.0.** v0.17.0 brought **all-report TSN comparison +
> consolidation** (every report compares **vs TSN** AND **cross-environment** in both matrices;
> Intersection reports **consolidate**; a **canonical TSN library** + **Settings ▸ TSN reports**
> panel; the one-stop **Export today** by-day column; **drag-to-reorder**; a **login/browser
> overhaul**; **env-check flags on both matrices**). **v0.17.1** then fixed field issues found
> using it: matrix tabs scrolling into blank space (the recurring sr-only containing-block bug →
> **Lesson 10**), the cramped Matrix-options panel, Stop/Clear not interrupting a stuck sign-in,
> the TSN "Choose…" dialog default, a self-documenting TSN library — plus two **security** gitignore
> fixes (`tsn_library/` was never ignored; belt-and-suspenders `output/tsn_*`). Per-version detail:
> `CHANGELOG.md`; v0.17.0 build journal: **[v0.17.0-prompt.md](v0.17.0-prompt.md)**.
>
> **Owed (now consolidated in *Next version (v0.18.2)* above):** the work-PC live verification, the
> **gh-pages** landing-page regen, and the two deferred v0.17.1 follow-ups — **cancel-latency** and
> **narrow-mode** (<980 CSS px) matrix-tab polish.

## How to maintain this file

- **Format.** Open item `- [ ]`; done `- [x] ~~…~~ **Done (vX.Y.Z / <commit>)**`. Tag features
  with a rough size `[S/M/L]`; tag code-review findings with severity `P0–P3` + a `slug`.
- **Sections (keep this order; don't reshuffle):** *Next patch* (the immediate worklist) →
  *Feature backlog* → *Standing & cross-cutting* → *Shipped (reconciled record)*. File new items
  under the matching section; start a new theme only if nothing fits. Bugs go under *Next patch*
  (or the findings record), not the feature backlog.
- **Reconcile every session / after each release** — the list rots otherwise. Compare the open
  items + the version table against `git tag` / `version.py` / `CHANGELOG.md`; check
  off what shipped (one line), update the version table to reality, and **flag anything deferred
  across multiple releases** for a keep / drop / bump decision. Record *what* shipped; the owner
  decides *where* deferred items go next.
- This is the backlog, **not** the changelog — keep "done" notes to one line; detail lives in
  `CHANGELOG.md` and the docs.

---

## Next version (v0.18.5) — what's actually owed

> **v0.18.2 / v0.18.3 / v0.18.4 shipped as field-driven hotfixes (2026-06-29)** — v0.18.2: comparison
> progress feedback, the large-report formulas-twin skip, Route Suffix in the Report View; v0.18.3: the
> intersecting-route-postmile 0-vs-blank fix + one-sided locations in the Report View; v0.18.4: the matrix
> queue-phantom (a finished compare stuck "running" in the queue panel). None completed the work-PC field
> sign-off below, so that sign-off (plus the small ride-alongs) now cuts as **v0.18.5**, and the
> "operational / enterprise-ready" claim moves with it.

> The single live worklist. Almost everything still owed collapses into ONE effort — the **work-PC
> field sign-off** (the dev PC can't reach TSMIS). The §J2 dispositions + the Phase-3 list below are
> the historical reconciliation record; *Feature backlog* / *Standing* hold the longer tail.
> v0.18.0's final review found **no offline leftover** — the only product TODO is this field gate;
> everything else is already **Shipped** (§ below) or an explicit **deferral** (the minor opportunistic
> carry-overs from the overhaul are under *Standing → Restructure leftovers*).

**1 — Work-PC field sign-off (GATES v0.18.5).** One session on the locked-down PC: run v0.18.4,
`--collect-evidence`, and confirm the live paths the dev PC can't. Full checklist + acceptance
criteria: [work-pc-validation.md](work-pc-validation.md) §3.
- [ ] The two **v0.18.1 field bugs** live — Intersection export selects on the **nested dev menu**
  (`data-value`); the matrix / by-day **queue clears** after a job drains; the flat **prod** menu still selects.
- [ ] **Carried live paths** — partial **keeps last-good**; stage-and-swap under Defender/lock; a real
  **paused-batch resume across a restart**; the **v0.17→v0.18 self-update**; both frozen exes + the source ZIP run.
- [ ] **P8c** — exact `select_report`, CDP open-on-demand / close-on-capture, cancel-in-recover latency.
- [ ] **Intersection Detail (PDF)** live — export → consolidate → PDF-vs-TSN / PDF-vs-Excel on the real files.
- [ ] **Evidence-driven parser fixes** (need the returned real PDFs) — ramp-summary parse-failure
  misattribution + duplicate-pop misassignment, via the P12 row-oracle. Land offline-RED-proven, then re-bless.

→ Cut **v0.18.5** as the operational sign-off ("enterprise-ready" is claimed here, never before).

**2 — Small & ready (ride along with the sign-off run):**
- [ ] **TSN-library auto-rebuild on a normalization-code change** [S] — `tsn_load_*.build_into` stores
  ALREADY-normalized values, so a normalization fix (e.g. v0.18.3's numeric-0 postmile) does NOT reach an
  existing library; compare-time `_normalized_row` can't recover lossy values (a 0 blanked at build time stays
  blank). Today the user must hit Settings ▸ TSN reports ▸ Rebuild, and it "looks unfixed" until they do (the
  v0.17.6 trap recurring — bit the v0.18.3 Intrte-Postmile fix). Fix: stamp the library with a normalization
  version + auto-rebuild from the stored raw when stale. *(Deferred — user "fine for now" 2026-06-29.)*
- [ ] **gh-pages landing-page regen** — owed since v0.17.0; website only ([website.md](website.md)).
- [ ] **cancel-latency** [S] — poll `should_cancel` in `preflight` / `select_report` (the ~60 s county-enable
  wait) / `_recover` (mid-batch re-login) so Stop interrupts the after-sign-in / recovery windows (same opt-in
  `should_cancel` pattern; verify live — the waits are field-hardened). *(v0.17.1 follow-up.)*
- [ ] **narrow-mode** [S] — (<980 CSS px, e.g. 1366×768 @150% DPI) matrix-tab polish: the card-hide /
  height-fill / config-uncap rules live in `@media (min-width:980px)`, so a small/high-DPI laptop shows stray
  idle cards + a cramped Matrix-options panel on the matrix sub-tabs. *(v0.17.1 follow-up.)*

**Site-gated (not on our schedule):** **Highway Summary enablement** — export shipped app-side (v0.19.1)
but the report is still `cs-disabled` on the site; consolidate/compare integration follows the Highway
Detail recipe once a real export exists (see *Feature backlog*). Highway Detail itself is DONE (v0.20.0).

**Parked — pull in only by a separate decision:** code-signing (SignPath cert), DPAPI at-rest auth,
`compare_core` min-cost-pairs, the A3 / C1 / D1 / F1 feature backlog, and the two
upstream TSMIS-team reports (all in *Standing & cross-cutting* / *Feature backlog* below).

---

## v0.18.0 — audit reconciliation (§J2 dispositions)

v0.18.0 pulled in the offline-doable Phase-3 audit residue and dispositioned the rest. Every
still-open finding at the v0.17.1 baseline now has an individual outcome (this supersedes the open
checkboxes in the *Next patch* section below — that list is the historical worklist):

**Resolved in v0.18.0** (a phase implements + locks it):
- **P0** — `handle-no-default-branch` (the `_handle` else-log), `gui-worker-stale-tkinter-docstring`,
  `env-compare-side-label-cap-truncates-distinguisher`, `ramp-summary-combined-sheet-hardcoded-coordinates`
  (schema-length guard).
- **P1** — `run-report-only-written-when-per-route-nonempty`; `pdf-page-skip-unlogged-when-no-prior-geometry`
  + `pdf-stale-geometry-carryforward-silent-corruption` escalated to a producer-owned **partial** so dropped
  output is never promoted/cached as complete.
- **P6** — `support-bundle-settings-future-leak` (the diagnostic-settings allowlist).
- **P7a** — `device-ok-inferred-from-any-completed-run`, `reset-token-consumed-before-task-gate`.
- **P8c** (offline-proven code; **live acceptance → v0.18.1**) — `select-report-substring-match-no-exact-guard`
  (exact-match guard), `edge-login-cdp-port-unauthenticated-loopback` (open-on-demand / close-on-capture),
  `select-report-not-rearmed-between-routes-on-stale-form`, `login-busywait-no-cancel-check`,
  `unlogged-no-download-empty-on-pdf-and-misc`.
- **P10 / §J updater set** — `size-and-checksum-guards-both-skippable` → **fail-closed** checksum,
  `extractall-zip-slip-relies-on-stdlib`, `staged-exe-launched-from-user-writable-dir-no-recheck` (re-hash
  before swap), `no-rollback-when-relaunch-launches-partial-tree`, `swap-log-grows-unbounded` (rotate),
  `webview-cache-cleared-on-every-dev-launch` (frozen-only), `immediate-death-check-narrow-window` (hardened
  window), `dl-socket-timeout-may-fail-slow-large-downloads` (timeout + bounded retry),
  `releases-list-capped-100-revert-blindspot` (paginate). Plus a hash-pinned reproducible build +
  `release.yml` per-variant `.sha256` enforcement.
- **P12** — `reset-follows-junctions-symlinks` (junction/symlink guard, dev-PC verified) **and the M03
  destination-ownership marker, NOW IMPLEMENTED** (the deferred R1-M03 item); `consolidate-overwrite-toctou`
  (confirm-then-appears re-check at the final replace); the independent **PDF expected-row oracle** harness.

**v0.18.1 evidence-driven** (offline harness shipped; **real-PDF / work-PC acceptance owed** — RM04):
- `ramp-summary-parse-failure-misattributed-to-source`, `ramp-summary-duplicate-pop-pattern-misassignment`,
  `pdf-consolidator-no-row-count-verification` (the P12 row oracle), and the stale-geometry **emit**
  elimination — **RESOLVED in v0.26.2**: a carried-geometry page is now VALIDATED read-only
  (`pdf_table_lib.carried_line_crossings` — every printed token's chars must land in ONE window, the
  same char-center test `assign_columns` places by, so a 0 score certifies the assignment); a
  committed fixture reproduces the exact failure mode (a foreign/drifted layout splits tokens), and
  only a page whose text does NOT fit the carry keeps the ⚠ + PARTIAL. The blanket flag had marked
  every HL (PDF) day "inputs incomplete" (~280 normal zebra-parity band-less pages per statewide
  set — the work-PC field report of 2026-07-10); statewide census + re-verify in
  `ground-truth/All Reports 7.9/_verification-scripts/`.
- The carried live-verify set (P1 partial-keeps-last-good, P2 stage-and-swap, P3 resume-across-restart, the
  P8c live paths, the P10 v0.17→v0.18 self-update, **and the Intersection Detail (PDF) live reconciliation**).
  Full checklist: [work-pc-validation.md](work-pc-validation.md) §3.

**Discovered during P11 (docs reconciliation):**
- `wait-js-fstring-interpolation-unvalidated` (P3) — **RESOLVED in v0.18.1.** The plan's §J2 had recorded
  this Resolved in P8b, but at the v0.18.0 HEAD `exporter.py` still interpolated `spec.wait_js(route)` with
  **no config-error validation**. v0.18.1 added `exporter._build_wait_condition(spec, route)`, which
  validates the spec's `wait_js` is a non-empty JS arrow string before interpolating and otherwise raises a
  clear `PreflightError` + `log.error` (instead of a cryptic Playwright eval error / a full route timeout).
  `route` is app-controlled, so this is a config tripwire, not input sanitization. Locked by
  `check_export_engine.test_wait_condition_validation`.
- `non-hl-loaders-dont-collapse-tab-whitespace` (CR-002) — the Highway Log and Highway Sequence vs-TSN
  loaders collapse tab/whitespace at load, but **Ramp Detail and Intersection Detail do not**. A known
  normalization inconsistency; **still deferred** (low impact — the locked counts stand). Revisit if a
  tab-bearing value ever causes a spurious diff.

**Hard-deferred (each needs an explicit separate user decision — RM06):**
- **DPAPI at-rest auth** (O2 / `auth-file-plaintext-no-acl-dpapi`) — DPAPI breaks `storage_state_is_portable`;
  v0.18.0 did the ACL/atomic-write half (P6), not encryption.
- **Runtime signature / code-signing cert** (A03 / `update-trust-is-tls-plus-sibling-sha-only`) — blocked on
  the SignPath cert; workflow signing parity only, no runtime signature verification yet.
- **`compare_core` `min-cost-pairs` greedy-not-optimal** — inside the regression-locked engine; any fix needs
  a full cell-for-cell re-proof and the 8+ duplicate-key-group frequency is unquantified.

---

## Next patch — code-review fixes (Phase 3 review, 2026-06-18)

> **Reconciled by v0.18.0 — see the §J2 dispositions above.** The open `- [ ]` items below are the
> historical Phase-3 worklist; their v0.18.0 outcome (Resolved / v0.18.1 evidence-driven / hard-deferred)
> is recorded in that section. Kept here for the code anchors + the field-verify notes.

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
- [x] **P2 PDF Highway Log silent-drop trio** (`pdf-stale-geometry-carryforward-silent-corruption`,
  `pdf-page-skip-unlogged-when-no-prior-geometry`, `pdf-consolidator-no-row-count-verification`)
  ✅ **Done (v0.17.0 Phase 1)** — `consolidate_tsmis_highway_log_pdf.parse_pdf` now returns a `stats`
  dict (emitted / skipped_no_geometry / stale_geometry_pages); data-looking lines on a page with no
  column band are COUNTED + logged (WARNING), pages parsed with carried-forward geometry are flagged
  once each (NOTE), and `consolidate()` leads with a ⚠ INCOMPLETE / carried-forward banner. Reporting
  only — the row-emit logic is byte-identical (PDF comparisons unchanged). Locked by
  `check_tsmis_pdf_reconcile.py`. (The TSN sibling already logs per-route row counts.)
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
- [x] **P2 updater integrity** (`size-and-checksum-guards-both-skippable`,
  `immediate-death-check-narrow-window`, `no-rollback-when-relaunch-launches-partial-tree`,
  `swap-log-grows-unbounded`, `dl-socket-timeout-may-fail-slow-large-downloads`)
  ✅ **Done (sol-001, integrated 2026-07-17 @ merge `7a7f0e7`).** Checksum verification is
  fail-closed even when size is absent (proved); the 1.5 s death poll → a **nonce readiness
  handshake** (the staged helper must prove it opened the original PID handle before the old app
  closes — no arbitrary window); a partial rollback now **suppresses relaunch** (never starts a
  mixed tree) and the dialog stays truthful; the helper log rotates at 256 KiB; the download has a
  60 s socket timeout + bounded retry. Red→green in `check_updater`; backward-compatible across all
  upgrade/revert directions. Work-PC re-verify (frozen swap/relaunch + Revert) owed. See
  [docs/agent-handoffs/STATUS.md](agent-handoffs/STATUS.md) "sol-001 integration record".
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

## v0.15.0 — the Everything comparison matrix  ✅ SHIPPED (2026-06-19)

**Shipped — v0.15.0** (tag pushed, GitHub release live; updater offers it to users). Built on
`feat/everything-matrix`, merged to `main`. Carried an **app-wide UI polish + motion pass** —
the matrix controls set the bar and the rest of the app was brought up to it (motion tokens,
bordered secondary buttons, consistent title-bar-vs-card controls, reduced-motion-safe entrance
animations); see [gui.md](gui.md) "Motion layer + control polish". (Items below kept for the
work-PC live-verify list.)

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

## v0.16.0 — matrix queue + fast mode + Compare-tab "TSN by-day" matrix  ✅ SHIPPED (2026-06-19)

Two undertakings, one feature release (committed in stages A → shared-engine factor → B).
Also the release that **field-tests the updater rename-retry fix** (v0.15.0 → v0.16.0).
`compare_core` stays untouched — orchestration only. Golden coverage:
`check_matrix_bridge.py` (queue) + `check_day_matrix.py` (by-day matrix).

**A — Everything-matrix upgrades (commit `a5d7d05`):**
- [x] **Row/column header buttons with distinct icons** — two buttons per header matching the
  cells: ↻ **live re-export** (one report × all envs, or all reports × one env; bulk confirms
  first) + ⟳ **rebuild-comparison** (`recompute_matrix`).
- [x] **Fast (parallel) mode for matrix exports** — toggle in the config zone, reuses the global
  `fast_workers` (`settings.get/set_matrix_fast`); routes through `MatrixBatchExportWorker`
  → `ExportWorker(workers=N)`.
- [x] **Editable, matrix-scoped job queue** — a 2nd action **queues** instead of being rejected;
  jobs run one at a time + auto-advance from `_end_task`; view / remove / reorder / clear /
  stop-all. New manifest-free `MatrixBatchExportWorker`. Gate+popleft claimed atomically (no
  queue↔gate race); an error that ends a matrix job clears the pending queue (no cascade).
  Cuts held: no per-job fast, no drag-drop, no cross-restart persistence, no whole-matrix button.

**B — Compare-tab "TSN by-day" matrix (commit `868d673`):** rows = report types, columns =
exported **days** you add, each cell = (report, day) **vs TSN**; ONE data source (default
SSOR/Prod); no cross-env, no live re-export. New Compare sub-tab; **Highway Log Excel + PDF**
supported, RS/RD/HSL **greyed**. Days from `output/<date src-env>/`; outputs to
`output/comparisons/tsn-by-day/<date src-env>/<row>_vs_tsn.xlsx`. New `day_matrix` engine +
`DayMatrixCompareWorker` + `day_matrix_*` bridge + `day_matrix_*` settings. Everything KEEPS its
vs-TSN (latest-refresh dashboard).

**Cross-cutting:**
- [x] **Shared TSN comparison engine** (commit `21ecdb5`) — `matrix.consolidate_and_compare_tsn`
  ("consolidate TSMIS store folder → `compare_highway_log[_pdf]` TSMIS_*_VS_TSN → write") used by
  BOTH matrices (differ only by source folder + output path); byte-identical to the prior
  Everything output (same consolidate-to-temp → same compare → same out_path).
- [x] **One queue serves both matrices** — a `which: env|day` discriminator on the Job routes to
  `MatrixCompareWorker` vs `DayMatrixCompareWorker`; one queue panel renders in both places.
- **Deviation from the plan's "auto-consolidate WITH prompt":** the user-facing consolidated
  artifact (the **TSN** district-PDF → workbook) already prompts (the existing
  `consolidate_matrix_tsn` flow, reused by both matrices). The TSMIS side is consolidated to a
  throwaway temp per build (internal plumbing), kept **silent** — prompting on every cell build
  would be hostile. Revisit if a per-build TSMIS-consolidation prompt is actually wanted.

**Owed work-PC live verification:** matrix queue auto-advance under real exports; fast mode (N
browsers, bounded, no `batch_job.json` clobber); a row/column live re-export; the by-day matrix
building two real days vs TSN; auth-error clearing the queue; and **the updater field test —
v0.15.0 → v0.16.0 stages with no manual redownload**.

---

## Shipped in v0.16.1 (`polish/matrix-tabs` → `main`, tag `v0.16.1`)

Released 2026-06-19. Fast-forwarded onto `main` and tagged; `release.yml` built + published.
All verified offline (34 golden checks, adversarial reviews); **live behavior is still
work-PC-only to verify** (matrix re-export pause/skip/preview, consolidated reuse over real
exports, the updater field-test v0.15.0→v0.16.1). Beyond the bullets below, v0.16.1 also: gave
the **"vs TSN Matrix"** full-width parity + its own config corner + a fast-mode **worker
picker** + independent per-matrix formulas; **restructured the Compare sub-tabs** to
Cross-environment / vs TSN / vs TSN Matrix (HL cross-env back in "env"); **generalized the
vs-TSN matrix to every report** (HL wired, the rest greyed groundwork) as staging for v0.17.0;
and fixed the dark-mode checkbox eyesore. Next: **v0.17.0** — see `docs/v0.17.0-prompt.md`.

- **Matrix review polish** — queue robustness (`_on_error` clears the queue only when a matrix job
  was running; dispatch wrapped so it can't stick the gate; taskbar flash on queue-drain), worker
  error lines name the cell, corrupt-cache logging, a11y (aria-labels + focus rings), by-day report
  toggles + Build-all, all-hidden empty state, `mx-na` legend swatch.
- **Pause/Resume + Skip + live preview on matrix re-export** — the events were already forwarded to
  `ExportWorker`; widened `pause_or_resume`/`skip_route`/`request_preview` to matrix EXPORT jobs +
  `MatrixBatchExportWorker.on_worker` + buttons.
- **Persist + reuse date/env-stamped consolidated** — both matrices persist the consolidated to the
  run/store `consolidated/` (the Consolidate-tab file) and reuse until a source is newer; `force`
  re-consolidate; per-day consolidated badge.
- **Opt-in live-formulas workbook** — `(formulas)` twin beside values (best-effort 2nd pass;
  values stays canonical). `settings.matrix_formulas` + toggle in both config zones.
- **Intersection export ENABLED + dev-site URL switch** — `DISABLED_EXPORT_SUBDIRS` emptied;
  Settings ▸ "Use development site" (`tsmis-dev.dot.ca.gov`, `gui_api.apply_site_preset`). See the
  Intersection consolidate/compare entry in the backlog below (groundwork; build when the user
  supplies exported Intersection + TSN data).
- **Short/wide-laptop layout fix** — the matrix no longer scrolls after ~2 rows: hidden page
  heading on the matrix sub-tab, cell actions as a hover overlay, inline column header, 82→50px row
  floor + tighter chrome. All 5 rows fit at 1440×720; labels readable (longest ellipses + tooltip).

---

## Feature backlog

- [x] **Ramp Summary vs TSN (AGGREGATE)** [M] — **DONE (v0.17.0).** The first AGGREGATE comparator
  + the shared `summary_layout.py` familiar-layout renderer. `consolidate_ramp_summary` completed to
  the full 16 ramp types (added TSN-only **P/V** "Dummy" classes); `compare_ramp_summary_tsn` sums
  the consolidated TSMIS workbook vs the statewide TSN PDF (key = category), with a "Summary by
  Category" familiar sheet via `extra_sheet_writer`. Registered in `tsn_library` (+
  `tsn_load_ramp_summary.build_into`), live in both matrices, golden `check_compare_ramp_summary_tsn.py`.
  Historical v0.17.0 canary (now superseded; implementation-history evidence only): 31 both /
  1 only-TSMIS / 27 diff / TSMIS 15215 vs TSN 15410. The accepted Stage-8 contract is maintained in
  [tsn-parsers.md](tsn-parsers.md) and the comparison-perfection dashboard.
- [ ] **Intersection consolidate + compare-vs-TSN** [M] — **IN PROGRESS (v0.17.0).** Export enabled
  (dev site, via Settings ▸ "Use development site"). **Done:** `consolidate_intersection_detail`
  (thin `consolidate_xlsx` wrapper); **`consolidate_intersection_summary`** (block-walk category summer,
  218 routes → 16,473) + **`compare_intersection_summary_tsn`** (AGGREGATE; 11-block union taxonomy;
  the diverged CONTROL/INTERSECTION-TYPE codes show one-sided via `Cat.sides`; 3-column TSN PDF parser;
  canary 72 union / 56 both / 10 only-TSMIS / 6 only-TSN; 16473 vs 16626) — live in both matrices, golden
  `check_compare_intersection_summary_tsn.py` + `check_consolidate_intersection.py`. The shared
  `summary_layout.py` (spec + block-walk + familiar sheet) backs both Summary reports.
  **`compare_intersection_detail_tsn`** (FLAT; read TSMIS by position — the planning "pair-order
  reversal" was a shifted-header misread; `Y↔1 / N↔0` boolean normalize + Notes indicator;
  cross-street attrs + Date of Record context; canary 16180 both / 5520 diff; 16473 vs 16626) +
  `tsn_load_intersection_detail` + golden check — live in both matrices. **Intersection is now COMPLETE
  (both reports consolidate + compare vs TSN).** The vs-TSN comparators flip on in BOTH matrices via
  `matrix.tsn_comparator_for`.
  Recipes: [reports.md](reports.md) / [comparison-engine.md](comparison-engine.md); schema + counts:
  [tsn-parsers.md](tsn-parsers.md); resume state: [v0.17.0-prompt.md](v0.17.0-prompt.md).
- [x] **Highway Sequence vs TSN (FLAT, route+county+PM)** [M] — **DONE (v0.17.0; the LAST report).**
  New `consolidate_tsn_highway_sequence` (word-level parse of the 12 district `Highway Locations` PDFs
  → one normalized workbook; 2-char G/RF flag split into HG+FT; equate annotation lines emitted) +
  `compare_highway_sequence_tsn` (FLAT with a **county-relative key** — CA postmiles restart per county,
  so `key_normalizer` composites `"COUNTY POSTMILE"`; TSMIS read by position with prefix+PM+suffix
  re-glued; FT + Description compared, HG/City/Distance context with a Notes indicator). Registered in
  `tsn_library` + `matrix.tsn_comparator_for`, live in both matrices, golden
  `check_compare_highway_sequence_tsn.py`. Canary: 57,070 both / 3,369 only-TSMIS / 12,688 only-TSN /
  5,538 diff (FT 699 + Description 4,839); 60,439 vs 69,758 rows; 242 routes both. **This completes
  v0.17.0's comparator goal — ALL 6 reports + HL-PDF now compare vs TSN in both matrices.** See
  [tsn-parsers.md](tsn-parsers.md).
- [x] **Phase 4 UX (ride-along)** [M] — **DONE (v0.17.0).** **4a** Settings ▸ TSN reports status panel
  (per-report raw/consolidated/current dot + Import raw… / Rebuild over `tsn_library`); **4b**
  drag-to-reorder rows + columns on both matrices (`matrix.apply_order` + persisted order lists). 4c
  (per-cell/row consolidate) + 4d (add-day pipeline) were found to already exist (Everything matrix
  re-export + recompute + refresh-consolidated; by-day per-day refresh) → not rebuilt (user decision).
  A 6-lens adversarial-review workflow over the session's change set confirmed + fixed 3 minor issues
  (incl. Intersection wrongly greyed in the by-day matrix). Verified in `#mock`; suite 42/42.
- [x] **All cross-environment comparisons complete** [S] — **DONE (v0.17.0; Phase 5 closed).** Every
  report now compares env-vs-env: `compare_env.INTERSECTION_SUMMARY` (AGGREGATE-per-route, route-keyed
  via the consolidator block-walk), `compare_env.INTERSECTION_DETAIL` (flat route+PM), and
  `compare_env.HIGHWAY_LOG_PDF` (flat, both sides parsed from the PDF export — the accurate HL source,
  via `flat_pdf_loader`). The HL-PDF matrix env cell is no longer greyed; `tsn_matrix_extra_rows()` is
  empty (all 7 reports are full matrix rows, every cell coded). Golden
  `check_compare_env_intersection.py` + `check_compare_env_highway_log_pdf.py`; all verified on real
  exports + in `#mock`. **The full comparison grid is now complete: every report × {cross-env, vs TSN},
  plus Highway Log's PDF↔Excel self-check.**
- **v0.17.0 is COMPLETE + release-prepped** (all consolidators + comparators + UX + every
  cross-env comparison; `version.py` → 0.17.0 and the `CHANGELOG.md` section are in). It also
  shipped the **login/browser overhaul** (background Edge one-click check + the export-browser
  indicator/setting) and **env-check matrix flags**. **Still owed:** push the `v0.17.0` tag to cut
  the release, and **work-PC verification** of live export/compare with real TSN data (the dev PC
  can't reach TSMIS).

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
- [x] **Highway Detail — FULLY INTEGRATED (v0.20.0)**: export (v0.19.1/2) + consolidators + vs-TSN /
  cross-env / PDF↔Excel comparators + `tsn_library` entry + both matrices, schema verified against the
  full statewide bundle. **Still owed:** **Highway Summary** consolidate/compare [S] — export shipped
  (v0.19.1) but the report is still `cs-disabled` on the site (no real export to verify a schema
  against); integrate via the same recipe when the site turns it on and a statewide sample exists.
  Live-export verification of the Highway reports against the site is owed (the dev PC can't reach it).
- [ ] **Coalescing — extend to fast mode + the console CLI** [S] — v0.19.2 coalesces dual-edition exports
  (Excel + PDF of one report → generated once, both saved) in the **standard sequential** GUI path
  (`run_export_combined`). **Fast mode** still runs each edition as its own parallel pass (route-parallel
  double-generation), and the console `run_cli_multi` (`.bat` multi-export) isn't coalesced. Extend the
  parallel engine to save both editions per route, and share `_coalesce_groups` (move it off
  `gui_worker_export` to a neutral module) so the CLI can group too.
- [x] **Visual evidence — SHIPPED (v0.21.0)** for Highway Detail vs-TSN (both matrix toggles; see
  [comparison-engine.md](comparison-engine.md) §13). **v0.22.0 added Intersection Detail** —
  `evidence_intersection_detail` locates the TSN side on the STATEWIDE print's fixed monospace
  template (indexed once per file, cached on size+mtime — the ID half of the parse-cache
  follow-up), and `availability()` went per-report so the toggle hint names which report still
  needs its prints. **Follow-ups, none started:**
  - [x] **Highway Log evidence adapter — SHIPPED (v0.24.0)** (`evidence_highway_log`: ditto-aware
    via `compared_cell`, per-print sentinel routing, TSN prints read from the library raw/).
  - [x] **Highway Sequence evidence adapter — SHIPPED (v0.25.0)** (`evidence_highway_sequence`:
    context-field-aware via `compared_cell`, the HL per-print sentinel routing, TSN prints read
    from the library raw/).
  - [ ] **TSN district-parse cache for HIGHWAY DETAIL + HIGHWAY LOG + HIGHWAY SEQUENCE** [S] — an
    HD statewide
    evidence run still spends ~10–20 min re-extracting words from ~4,300 district-print pages
    every run, and the HL (v0.24.0) + HSL (v0.25.0) adapters' per-print routing full-scans their
    12 district prints
    likewise; give all three the mtime-keyed index cache the ID adapter shipped with in v0.22.0.
  - [ ] **PDF-vs-Excel self-check evidence** [M] — needs a synthetic render of the Excel side (no
    second PDF exists); park until someone actually asks for it. (The HL/HSL rows'
    `vs_pdf`/`vs_excel`
    self-check modes deliberately show no camera for the same reason.)
  - [ ] **Evidence on the Compare tab's direct file-pair flow** [S] — the matrix surfaces were the
    ask; the manual pick-two-files compare has no toggle (its TSMIS-PDF folder can't be inferred
    from the picked files — needs a picker or the standard-location assumption). The v0.24.0
    "What you'll get" text points users at the matrix pages meanwhile.
  - [ ] **Ramp Detail evidence adapter** [M] — blocked on the same work-PC PDFs as its print
    parser (below). The TSN side is already in hand: the Ramp Detail statewide TSN print
    (`ground-truth/Ramp Detail TSN print 9.15/` → `tsn_library/ramp_detail/pdf/` once flagged).
- [x] **Highway Sequence (PDF) integration — SHIPPED (v0.25.0)** off the first real work-PC print
  set (`ground-truth/HSL PDF + IS Bundle 7.9`, 252 routes): census-first parser
  (`consolidate_tsmis_highway_sequence_pdf` — wrapped-desc hyphen-aware rejoin, PM-less rows, the
  diagnostics-trailer hard stop; 60,493/60,493 parse-back), `compare_highway_sequence_pdf`
  (PDF↔TSN pairs BETTER than Excel↔TSN — the print shares TSN's equate convention; PDF↔Excel
  caught the route-037 Excel-dropped Description), both matrix rows + all special-case mirrors,
  and the evidence adapter above.
- [x] **Ramp Detail (PDF) integration — DONE (v0.26.0, unreleased).** Off the first real work-PC
  pair (`ground-truth/All Reports 7.9`, 126 routes): the census-first print parser
  (15,216/15,216 parse-back, 0 unclassified/strays), `consolidate_tsmis_ramp_detail_pdf` (the
  Excel layout + the two PRINT-ONLY columns the Excel export drops — On/Off + Ramp Type),
  `compare_ramp_detail_pdf` (PDF↔TSN GRADUATES those two columns to compared — +151 verified
  cells statewide; PDF↔Excel 15,212/15,216 identical, the 4 = `_x000d_` Excel escapes), both
  matrix rows + every special-case mirror, `evidence_ramp_detail` (the ID statewide-print
  pattern; TSN library v3 sidecar; e2e 16/8-of-8 + 12/6-of-6). See
  [reports.md](reports.md) / [tsn-parsers.md](tsn-parsers.md).
- [x] **Highway Detail 7.9/ARS print parse gap — CENSUSED + FIXED (v0.26.0).** The 254 unpaired
  lines decomposed into THREE uncensused record shapes (the 7.9 drop has NO ssor-prod HD prints,
  so the ars pair is the only same-build set): (1) sparse rows whose roadbed blocks print codes
  but **no effective dates** (the old "a line 2 always carries a TASAS date" guard dropped them),
  (2) line 2s whose date lands across a shifted window grid (the per-window date test missed it —
  now tested on raw text as the fast accept, with censused furniture tests carrying the date-less
  path), and (3) **outdented equate descriptions starting with a PM-shaped token** that `_is_line1`
  misread as new records (orphaning the real record AND minting a phantom — route 101's 190).
  Re-verified statewide: consolidation **COMPLETE, 0 orphans, 0 single-line records**; PDF↔Excel
  50,171/50,730 matched identical; one-sided fell 1,273 → **1,019 (476 PDF / 543 Excel)** — near-all
  the newly-parsed sparse attribute-only rows at REPEATED postmiles whose duplicate-row pairing
  tie-breaks differ between renders (enumerated on the Only-in sheets; 9 Excel-only carry real
  descriptions). Scripts + expected numbers → `All Reports 7.9/_verification-scripts/`. Follow-up
  [S]: census the duplicate-PM pairing classes if the vendor conversation needs them attributed.
- [x] **Day-vs-baseline comparisons — the "vs Baseline Matrix" — SHIPPED (v0.26.0, unreleased).**
  Same report + format + source, one exported day diffed against an EARLIER pull (a run-folder
  day or the Export-Everything store) — `scripts/baseline_matrix.py` orchestrating the untouched
  `compare_env.compare_folders` per row (an additive `labels=` override names the sides), a third
  Compare sub-tab with its own config corner, all 12 rows, per-baseline artifact store under
  `output/comparisons/baseline-by-day/`, two-folder fingerprint freshness, the shared job queue.
  Locked by `build/check_baseline_matrix.py` (incl. one REAL build per baseline kind); the
  UI verified on the `#mock`. See [comparison-engine.md](comparison-engine.md) §12c. **Owed on
  the work PC:** a real two-day baseline run (the dev PC has no run-folder history).
- [ ] **Shared whitespace-collapse helper** [XS] — `compare_highway_log._hl_normalize` and
  `compare_highway_sequence_tsn._v` carry the same tab/newline collapse
  (`compare_ramp_detail_pdf._collapse` joined the family in v0.26.0, flavor-local by design);
  homing one helper in `compare_tsn_common` needs a locked-comparator re-bless, so it waits for
  a release that re-blesses HL anyway (audit finding, 2026-07-08 — cosmetic, no behavior drift).
- [x] **Ramp Summary (Excel) edition — SHIPPED (v0.25.1**, same day it was backlogged**).** The
  site's `rs_exportToExcel` wired as `ramp_summary_excel` (stable id 13) — the INVERSE of the
  print editions. Shipped alongside **Intersection Summary (PDF)** (`ints_printAll`, id 14) and
  the greyed **Route History** placeholder (id 15), so every enabled on-site report exports in
  both formats the site offers (see the capability matrix in [reports.md](reports.md)). All
  three export-only; the consolidate side (RS-Excel consolidator, IS-PDF print parser) waits for
  real work-PC files, Lesson-13 style.
- [x] **Intersection Detail July-2026 format — SHIPPED (v0.22.0).** The site reshaped the report
  (35 columns; see [reports.md](reports.md) Reports 5–6 + 6b and
  [tsn-parsers.md](tsn-parsers.md) Intersection Detail): consolidators/comparators updated with a
  pre-update-workbook refusal, the comparison re-baselined (canary 163,310 → **21,675**), the TSN
  library moved to normalization v3 (new shape + District/County sidecar), evidence enabled.
- [x] **Intersection Summary July-2026 watch — CLOSED (v0.25.0).** The fresh 7.9 export showed the
  July update touched IS too, but only ONE header (`MAINLINE MASTARM` → `MASTERARM`): fixed with a
  parse-only Section alias + a section-partition layout-drift tripwire (see
  [tsn-parsers.md](tsn-parsers.md) Intersection Summary). The route-170 thread CLOSED with the
  `All Reports 7.9` drop: absent from all four intersection exports across BOTH data sources
  (matching dev) — a data-side removal, not an export glitch.

---

## Standing & cross-cutting (open)

### Security / IT
- [ ] **Code-sign the executable** — the one big remaining IT lever (removes most Defender / DLP /
  SmartScreen friction on the unsigned `.exe`, and is the real fix for the P1 auto-update-trust
  finding above). **In progress:** SignPath Foundation cert applied for; `build.ps1 -Sign`
  self-signs for local/test; `release.yml` has a gated SignPath step (inert until
  `SIGNPATH_ENABLED=true` + secrets). *Remaining:* approval → flip the gate on (add the
  with-browser pair) → enable updater signature verification. See
  [it-and-security.md](it-and-security.md) §7. The updater checksum + staged-item allowlist
  (v0.11.0) are the integrity half; the signature half waits on the trusted cert.
- [ ] **Auth file at rest** — `storage_state` is plaintext JSON (documented, not encrypted).
  Defense-in-depth; consider Windows DPAPI (`CryptProtectData`) if IT ever requires it. (Same as the
  P2 `auth-file-plaintext-no-acl-dpapi` finding.)

### Live-export verification (owed on the work PC — this dev PC can't reach TSMIS)
- [ ] **EmptyExport 60 s cap** rests on the site's "Export button present ⟺ data loaded" contract.
  Confirm live it doesn't false-positive on a slow-but-valid load.
- [ ] **Intersection empty markers** (`td.hl-empty` / `Total Intersections = 0`) — verify against the
  live site once intersections finalize (still site-side development; markers may drift).
- *(The bulk of this — plus the carried §J2 live-verify set: the wrong-env backstop, the empty-routes UX,
  the staging retry, `report_error_text`/Highway-Sequence empty — is consolidated as the **work-PC field
  sign-off** in [Next version](#next-version-v0185--whats-actually-owed) above.)*

### Upstream / external (report to the TSMIS team)
- [ ] **DEV-SITE SSOR REGRESSION (2026-07-09, build 14:41)** — the Route History "restore" line in
  `main.js`'s report-change handler re-hides the Query Method box for SSOR on every report pick
  (clobbers the `checkTsmisHiGroup()` un-hide), so NO SSOR user can export on dev; prod fine. Fix
  = restore `'block'` unconditionally. Relayed to the user with the one-line fix (see
  `site-captures/TSMIS Dev Site 7.9` in the local index); blocks route-170 IS, the HD coalesced
  pair, and all ID/IS/HD dev exports.
- [x] Site hardcodes `highway_sequence_listing.xlsx` as *Ramp Detail*'s export filename (cosmetic
  for us — we rename via `save_as`). **Fixed by the vendor in the dev 7.9 build**
  (`ramp_detail_<route>.xlsx`); prod follows whenever that build promotes.
- [ ] Ramp Summary **source-data** inconsistency on 9 routes (see the Shipped record — not our bug).

### Restructure leftovers (opportunistic — low priority, none release-blocking)
> v0.18.0's final review found the branch **offline-complete** (no product-code leftover). These are the
> only minor hygiene / conditional carry-overs from the overhaul — do them opportunistically.
- [ ] **Non-HL tab/whitespace normalization** — the Highway Log & Highway Sequence vs-TSN loaders collapse
  tab/whitespace at load; **Ramp Detail & Intersection Detail do not** (the disposition is recorded in §J2
  above). Low impact — the locked counts stand; revisit only if a tab-bearing value ever causes a spurious diff.
- [ ] **P11 doc/comment line-ref drift** — the v0.18.0 leaf-split moved code, so some `docs/internals/*`
  inline `file:line` refs + a few source comments still point at pre-split locations (the deeper per-row
  churn the P11 docs reconciliation explicitly deferred; the v0.18.1 docs pass fixed `export-engine.md` §6).
  Fix opportunistically when you next touch those files.
- [ ] **Cold-start / matrix-snapshot perf baselines** (R1-A01) — the import-cost baseline shipped
  (`build/measure_baselines.py`); the runtime cold-start / matrix-snapshot baselines were deferred to the
  first phase that touches a hot path. Measure then, not before.

### Dormant / watch (no action unless the data changes)
- [x] **Med Wid flavor-parity gap — resolved in Phase-3 E1 (2026-07-12).** Python, values,
  formula Comparison, and independent Spot Check now share the approved narrow ASCII grammar via
  exact string canonicalization and hidden staged helpers; no Excel `VALUE()` coercion remains.
  The adversarial grammar/fuzz, formula-length, physical-width, and installed-Excel gates own the
  contract. Detail in [comparison-engine.md](comparison-engine.md) (Med Wid formula/value parity).

---

## Shipped (reconciled record)

What landed, so the open list stays honest. Full changelog: `CHANGELOG.md`.

### Version buckets — reconciled to reality (current: v0.26.0, IN PROGRESS — unreleased)

| Version | Date | What actually shipped |
|---|---|---|
| **v0.11.0–0.11.1** ✅ | Jun 16 | Audit-hardening patch (no-download fast-fail, token redaction, updater SHA-256, PM-keyed compares, incompleteness contract); TSN converter proven flawless. |
| **v0.12.0** ✅ | Jun 16 | **A1, A2, B1, B2, B3** — self-describing filenames, compare-folder filter, Pause/Resume, auto-consolidate, Export Everything. |
| **v0.13.0–0.13.1** ✅ | Jun 17 | UI/UX declutter, run lifecycle + ETA + completion summary, completion notification, accessibility, Compare sub-tabs, revert-to-previous, env-check split, Everything-store labeling/colour-coding; duplicate-key similarity pairing. |
| **v0.14.0–0.14.3** ✅ | Jun 18–19 | **Highway Log PDF** consolidator + PDF-sourced comparisons + corrected 31-column labels + roadbed-aware key + HL Compare sub-tab + consolidate-label clarity + UI-vs-logic audit + the IT-README handout. |
| **v0.15.0** ✅ | Jun 19 | The **Everything comparison matrix** (report × env, cross-env + vs-TSN, two Highway Log rows) + an app-wide UI/motion polish pass. |
| **v0.16.0–0.16.1** ✅ | Jun 19 | Matrix **queue + fast mode**; the Compare-tab **vs-TSN-by-day** matrix; pause/skip/preview, reused consolidated, opt-in formulas; Intersection **export** + dev-site switch. |
| **v0.17.0** ✅ | Jun 20 | **All-report TSN + cross-env comparison** (every report × {env, TSN} + HL PDF↔Excel); Intersection **consolidators**; **canonical TSN library** + Settings panel; one-stop **Export-today** by-day column; **login/browser overhaul** + **env-check matrix flags**; drag-reorder. |
| **v0.17.1** ✅ | Jun 21 | Matrix-tab blank-space + cramped-options fixes; Stop/Clear interrupts a stuck sign-in; TSN picker default + self-documenting TSN library; gitignore security fixes. |
| **v0.18.0** ✅ | Jun 26 | **Structural & engineering overhaul** (engine leaf split / `common.py` shim, the outcome + transactional-artifact contracts, report-catalog SoT, GUI endpoint split + front-end modularization, `compare_core` byte-identical) + **Intersection Detail (PDF)** (CR-002) + updater/packaging hardening + the work-PC evidence kit. Released as the offline-validated candidate. |
| **v0.18.1** ✅ | Jun 26 | **Field-validated close-out** — site-menu-safe selection (pick by stable `data-value` + reveal the `cs-submenu` fly-out; prod-safe), website-style report grouping, Highway Detail/Summary reserved-disabled groundwork (stable ids 8/9), the matrix queue-phantom fix, `wait_js` validation, and the Intersection Detail "Roadbed"→"Route Suffix" rename. `compare_core` untouched. |
| **v0.18.2** ✅ | Jun 29 | **Hotfix** (field-driven) — comparison **progress feedback** (the ~17k-row Intersection Detail vs-TSN build narrates its formerly-silent "Report View" stretch; `_PROGRESS_EVERY` 10k→2.5k ⇒ Stop lands sooner), **skip the live-formulas twin** for huge bulk matrix rebuilds (> `_FORMULAS_TWIN_MAX_ROWS` Comparison rows; the values copy is still complete, the skip is logged, the manual Compare tab is unaffected), and **Route Suffix surfaced in the Report View** (soft: red, not Major). `compare_core` output byte-identical. |
| **v0.18.3** ✅ | Jun 29 | **Hotfix** (field-driven) — two Intersection Detail vs-TSN comparison fixes: the **intersecting-route postmile** no longer false-flags where both sides are 0 (`_norm_num`/`_norm_bool` preserve a numeric 0 instead of blanking it via `str(v or "")`, so TSN's numeric-0 reads `0` and matches TSMIS's `'0.000'`; statewide canary **163,353→163,310**, −43, only that field), and the **Report View marks one-sided locations** "Only in TSMIS/TSN" (a side-colored band, kept out of the Major/Diffs tally) instead of an all-red row. `compare_core` untouched. |
| **v0.18.4** ✅ | Jun 29 | **Hotfix** (field-driven) — the **matrix job-queue phantom**: a finished/cancelled compare lingered in the queue panel marked "running" (BOTH matrices) until the next job replaced it. Backend was correct (the job released + state pushed); the panel is a `.mc-group` whose bare `display:flex` outranked the UA `[hidden]{display:none}`, so `group.hidden=true` never hid it, and `renderQueuePanel` didn't clear the row list on the empty path. Fix = `.mc-group[hidden]{display:none}` + clear the list every path. Frontend-only; reproduced + verified in `#mock` with the production event order (which the mock's own order masked). |
| **v0.18.5** ✅ | Jul 6 | **The audit release** — every confirmed full-repo-audit finding, no new features: TSN library **normalization-version stamp + auto-rebuild from raw** (comparisons self-heal after an update), a real `0` never reads as blank (the `str(v or "")` sites), and the offline check suite now **gates every release** (`run_checks.py` + `release.yml needs: offline-checks`). `compare_core` re-blessed (2.79M cells identical). |
| **v0.19.0** ✅ | Jul 6 | **Usability + trust + structural cleanup** — one-click **"Validate & package results"**; the same report grouping on every tab; add-today to the by-day matrix; laptop side-pane fix; + the R–V structural waves (shared comparator/PDF substrates, `gui_api`/`gui_worker`/`matrix`/`app.js` splits, ruff F821 blocking CI, `checks.yml` = one runner step, SEC-02/05/06 hardening, `compared_cell` re-blessed 2,789,732 cells identical). Work-PC sign-off received. |
| **v0.19.1** ✅ | Jul 7 | **Highway Detail/Summary EXPORT enabled** (the v0.18.1 reserved pair; export-only — consolidate/compare still owed) + **validation phantom-env fix** (`_envs_with_data` walked the store's `_tsn_input` TSN-drop folder as an environment → the Validate run now reads 18/18). |
| **v0.19.2** ✅ | Jul 7 | **Highway Detail (PDF)** print edition (stable id 10, `hd_printAll` — confirmed on the 7.7 dev capture) + **dual-edition coalescing** (selecting both editions of one report generates it once and saves both; `run_export_combined`, standard path — fast mode + CLI are follow-ups). Locked by `check_coalesce_editions`. |
| **v0.19.3** ✅ | Jul 7 | **Hotfix** (field-driven) — the per-route stale-form guard (`_ensure_report_armed`) false-"drifted" on **every** route for a grouped-menu report: it compared the visible `.cs-value` (the short leaf label "Detail") to the full `spec.label` ("Highway Detail") and re-selected each route (correct exports, but log spam + wasted work). Fix = key on the hidden `#reportSelect`'s stable `data-value` (`current_report_value`), text read only as fallback. Affects both Highway Detail editions. Regression-covered in `check_export_engine` + `check_fake_site` (new `test_current_report_value`); `compare_core` untouched. |
| **v0.20.0** ✅ | Jul 7 | **Highway Detail full integration** — consolidators (Excel `consolidate_highway_detail` + PDF-sourced `consolidate_tsmis_highway_detail_pdf` on `pdf_table_lib`), the **vs-TSN comparator** (`compare_highway_detail_tsn`: new opt-in `CompareSchema`, canonical roadbed-aware PM key, PS column, NA/zero-pad/length/WDA normalizations, ID-style **Report View** + **Notes**), the PDF flavors (PDF↔TSN + PDF↔Excel), a `tsn_library` statewide-xlsx entry, both matrices + by-day rows, catalog/`.bat`/mock parity. Schema verified against the full statewide bundle (252 routes / 51,243 rows vs the 60,083-row TSN extract; TSN PDFs cross-checked ≥99.9% vs the extract → the Excel is the library source). `compare_core` untouched (byte-identical; new behavior rides the new schema). Highway Summary stays export-only. |
| **v0.21.0** ✅ | Jul 8 | **Visual evidence** — the manual "screenshot both PDFs and circle the cell" workflow automated as a decoration of the Highway Detail vs-TSN comparisons: per differing column, N (1–10) random verified example rows rendered as highlighted snippets from BOTH PDFs (the app's (PDF) export + the TSN district prints in `tsn_library/highway_detail/pdf/`), each example parse-back-verified against the compared values before it's shown; `… (evidence).xlsx` + a two-layout image folder beside each comparison (keep-last-good). One shared toggle+count on both matrix pages (`evidence_images`/`evidence_examples`), ONE hook in `consolidate_and_compare_tsn`. TSN library v2 appends the District/County sidecar (D2 auto-rebuild). Pillow + pypdfium2 now SHIP (~20 MB; the frozen self-test proves the render path). Locked by `check_visual_evidence`. |
| **v0.21.1** ✅ | Jul 8 | **Hotfix** (field-driven) — the `tsn_library/highway_detail/pdf/` drop folder v0.21.0 pointed at but never created: `TsnEntry.evidence_pdfs` drives `ensure_layout` (folder + hint file; README refreshes when its generated text changes), and `matrix_info`/`day_matrix_info` re-push state so dropping the PDFs + re-entering a tab un-greys the evidence toggle without a restart. |
| **v0.22.0** ✅ | Jul 8 | **Intersection Detail July-2026 format + evidence** — the site's report overhaul absorbed end-to-end: 35-column SoT, the PDF parser rewritten for the reshaped print (cover pages, rowB bands + print-only intersection numbers, padded postmiles; pre-update workbooks/PDFs refused with re-export hints), the vs-TSN comparison re-baselined against the same-run 7.8 statewide bundle (parity 217/217 routes / 576k cells / 0 real diffs; canary 163,310 → **21,675**; Notes + Report-View Major classification rewritten to the data — soft = Int St/ML/CS Eff-Date + Route Suffix), `Xing Line Lgth`↔`X_CROSS_OVERRIDE` newly compared, TSN library **v3** (new shape + District/County sidecar), and **evidence images for both ID rows** via `evidence_intersection_detail` (the statewide TASAS print on a fixed monospace template, indexed once + cached; 16,584/16,584 records, 30/32 fields 100.00% parse-back). `availability()` went per-report; `compare_core` untouched. |
| **v0.22.1** ✅ | Jul 8 | **Evidence workbook: both layouts** — "… (evidence).xlsx" gains a second image tab: **Evidence (stacked)** + **Evidence (side-by-side)** (previously stacked-only; the pair files lived only in the images folder). Engine-level (`_image_sheet`), so HD + ID both get it. |
| **v0.23.0** ✅ | Jul 8 | **On-demand per-cell evidence** — a camera action on built, fresh vs-TSN cells (both matrices) generates/refreshes the evidence set for the EXISTING comparison: no re-compare, toggle-independent (`matrix.run_evidence_only` + `evidence_for_cell`/`evidence_for_day_cell`, an `evidence` queue job, endpoints `matrix_evidence_cell`/`day_matrix_evidence_cell`). The freshness gate refuses when the store/consolidated/TSN moved past the comparison ("refresh the comparison" hint) so images can't illustrate a diff set the workbook doesn't carry; `availability()` gains the `row_reports` map the JS gate reads. Verified e2e on the 7.8 mini-store (real compare → on-demand run → warm-cache re-run → staleness refusal). |
| **v0.24.0** ✅ | Jul 9 | **Highway Log evidence + two print editions + the comparison standards audit + evidence-toggle clarity** — (1) `evidence_highway_log`: both HL rows render evidence images (compared_cell-judged so dittos/Med-Wid never enumerate; per-print sentinel routing since HL's 31 columns carry no district — records carry their own `src`/dist/cnty, the engine prefers them, cross-print collisions skip via the uniqueness gate; TSN side reads the SAME district prints from `tsn_library/highway_log/raw/`, no duplicate drop). (2) **Highway Sequence (PDF)** + **Ramp Detail (PDF)** export-only print editions (stable ids 11/12; `hsl_printAll` portrait / the shared async `printAll()` dispatcher with a `showPrompt` auto-answer + `Promise.race` bound, landscape; coalescing automatic). (3) The audit: HSL re-verified statewide on the fresh 7.8 bundle (library rebuild byte-identical, counts within ~54 rows of the canary, FT-diff census: 681/698 = the by-design equate pairings — Notes updated); Ramp Detail gained a Notes sheet + stale-library re-normalization (idempotence proven on 15,410 real rows) + a width gate; Ramp Summary gained spec notes. (4) The evidence toggle spells itself out per report (✓/○/no-support lines + row-header camera badges); disabled Create-comparison explains why; (PDF) picker rows explain print editions. `check_day_matrix`/`check_matrix_tsn` made HERMETIC (sandbox `TSN_LIBRARY_ROOT` — a stocked dev library flipped their staged fixtures). |
| **v0.25.0** ✅ | Jul 9 | **Highway Sequence (PDF) fully integrated + the Intersection Summary July fix** — off the first real work-PC print set (`ground-truth/HSL PDF + IS Bundle 7.9`, delivered same day): (1) the census-first print parser (`consolidate_tsmis_highway_sequence_pdf` — header-anchored per-page windows, wrapped-desc HYPHEN-AWARE rejoin, PM-less END-OF-ROUTE/CITY-END rows, the "Unresolved Intersections" trailer hard-stop; parse-back **60,493/60,493 rows / 59,082 fully equal** vs the 7.8 Excel — residual = the equate-representation classes + 4 `_x000D_` + the route-037 Description the Excel export DROPS). (2) `compare_highway_sequence_pdf` (PDF↔TSN pairs BETTER than Excel↔TSN — both 57,505 vs 57,071, the print shares TSN's equate convention; PDF↔Excel both 59,946 / identical 59,082; per-flavor Notes sheets) + the `HIGHWAY_SEQUENCE_PDF` env adapter + BOTH matrix rows (env/tsn/vs_excel modes; every special-case mirrored: `matrix_state`, `matrix_build`, `day_matrix`, `gui_worker_maint`, the console menu, the mock). (3) `evidence_highway_sequence` — the HL per-print sentinel routing, context-fields never enumerate (`compared_cell`), TSN prints from `tsn_library/highway_sequence/raw/` (`_TSN_PDFS_IN_RAW`). (4) **Intersection Summary**: the July `MASTARM`→`MASTERARM` rename absorbed via a parse-only Section alias + the section-partition layout-drift tripwire (every block but the site-under-counted Highway Group must sum to the route total); verified on the fresh 217-route export (route 170 missing — flagged). |
| **v0.25.1** ✅ | Jul 9 | **Every edition, everywhere** — (1) **TSAR: Ramp Summary (Excel)** (stable id 13, `rs_exportToExcel` via the shared Export-button save — the site button the app never wired; the INVERSE of the print editions); (2) **Intersection Summary (PDF)** (id 14, `save_intersection_summary_pdf`: `ints_printAll` PREPENDS a cover to the inline count tables — no pagination — `window.print` overridden, `.rs-cover`+`.ints-total` verified, total re-read as the empty backstop, portrait; in `_PAGE_REBUILDING_SAVES`); both coalesce with their siblings (shared `data_value`). (3) **Route History Table** (id 15) wired as reserved-DISABLED groundwork (`DISABLED_EXPORT_SUBDIRS={"route_history"}`, greyed in the picker — the dev site's embedded-SSRS report has no export flow; the v0.18.1 Highway-pair pattern). Export-only; consolidate/compare/matrix untouched. Gate checks re-pointed (`check_intersection_gate._RESERVED`, stable-ids 13–15, catalog baseline + mock parity). |
| **v0.25.2** ✅ | Jul 9 | **Hotfix** (field-driven, same evening) — a plain (non-fast, non-store) export of a coalesced Excel+PDF pair crashed instantly: `run_export_combined` did `Path(out_dirs[i])` on the truthy `[None, None]` list `_prep_edition` passes when there is no store base → `TypeError … not NoneType` before the browser launched. Latent since v0.19.2 (fast mode never coalesces; the Everything store always passes real staging dirs) — the user's first standard-mode pair run (2026-07-09 18:30, three attempts) was the first field exercise. Fix = `_combined_output_dirs`: a None ENTRY falls back to that spec's dated run folder (run_export's `out_dir=None` semantics, per edition). Regression-locked in `check_coalesce_editions.test_combined_output_dirs`. |
| **v0.26.0** 🚧 | Jul 10 (in progress) | **Ramp Detail (PDF) fully integrated** — the LAST export-only print edition graduated off the first real work-PC pair (`All Reports 7.9`): the census-first parser (parse-back **15,216/15,216 rows**, 0 unclassified), the consolidator carrying the Excel layout **plus the two print-only columns the Excel export DROPS** (On/Off, Ramp Type), `compare_ramp_detail_pdf` (PDF↔TSN **graduates On/Off + Ramp Type to compared** — +151 verified cells statewide vs the Excel baseline; PDF↔Excel **15,212/15,216 identical, 0 one-sided** — the 4 = the Excel's `_x000d_` escapes), the `RAMP_DETAIL_PDF` env adapter + BOTH matrix rows (every special-case mirrored), `evidence_ramp_detail` (the ID statewide-print pattern — fixed template censused 400/400 vs the raw extract; TSN library **v3** District/County sidecar; e2e 16 examples across 8/8 PDF-row columns + 12 across 6/6 Excel-row columns; dual-row discipline: the Excel row never enumerates the print-only columns). **+ the "vs Baseline Matrix"** — day-vs-baseline comparisons for all 12 reports (an earlier day or the Everything store as the baseline; `baseline_matrix.py` over the untouched `compare_env.compare_folders` with an additive `labels=` override; a third Compare sub-tab + config corner; per-baseline artifacts under `comparisons/baseline-by-day/`; locked by `check_baseline_matrix`) **+ the evidence full-width-band crop fix** (`_crop_window`: a blank cell's red box / neighbor text no longer clips — the HSL complaint; verified on 99 regenerated examples) **+ the HD-PDF July-print parser fix** (the 254-orphan census: date-less sparse roadbed rows, window-split dates, outdented PM-shaped equate descriptions — all parse; single-line records kept with a blank attribute tail) **+ one-click website-source capture** (Settings; `site_capture.py`, local-only — see [it-and-security.md](it-and-security.md)) **+ mock parity fixes** (the by-day mock gained the two HD rows + the HSL/HD-PDF fmt flags it had drifted on). |

> **The planned "A3 / D1" buckets never shipped** — v0.13 became a UI/UX release and v0.14 became
> Highway Log accuracy, displacing A3 (results tab) and D1 (adaptive fast mode) each time. They're
> now in the Feature backlog above, flagged 3×-deferred.

### Closed findings & decisions (record)
- [x] **`main` reconciled to v0.18.1** (2026-06-27) — a `-s ours` supersede merge (`9514359` = `d775ca0`
  v0.18.1 + `068b697` v0.17.8) fast-forwarded `origin/main` to the v0.18.1 tree; **no force-push**, the
  forward-ported v0.17.2–v0.17.8 line preserved as ancestry, `v0.18.0`/`v0.18.1` tags intact; the merged
  `refactor/v0.18.0-structural-overhaul` branch retired (local + origin). The diverged-histories problem
  (the CR-002 forward-port) is closed.
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
