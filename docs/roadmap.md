# TSMIS Exporter — Roadmap & backlog

The single forward list — bugs to fix, features to add, and standing concerns. The **changelog**
(what already shipped, per release) is `CHANGELOG.md`; the narrative is
[history.md](history.md). This file is what's *left*.

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

## Next patch — code-review fixes (Phase 3 review, 2026-06-18)

A read-only review (6 risk-domain auditors + adversarial refutation) over commit `0a4c071`
confirmed **45 findings (5 P1 · 17 P2 · 23 P3)**; 12 candidates were rejected on refutation. Full
report with code anchors + fix sketches: `code-review/AUDIT-phase3-0a4c071.md` (git-ignored). Do
the field bug + P1s first.

### Field-reported (work-PC logs — CONFIRMED in the field)
- [ ] **`update-stage-rename-no-retry`** — intermittent **`PermissionError: [WinError 5] Access is
  denied`** while *staging* an update (NOT the swap): `download_and_stage`'s bare
  `root.rename(extract\TSMIS Exporter → staged)` (`updater.py:416`) fails when Defender / the
  indexer still holds the freshly-extracted ~150 MB tree; the stage aborts, the user re-downloads
  and it works. **Asymmetry is the bug:** `perform_swap` wraps its file ops in `_retry`
  (12 × 0.5 s, "Defender / slow handle release") but the stage rename has none. Observed 2× on the
  work PC (2026-06-17 ~09:20, 2026-06-18 ~09:39). **Fix:** wrap the rename + `rmtree(extract_dir)`
  in the same `_retry`, or `extractall` straight into `staged`. Evidence:
  `code-review/field-update-stage-rename.md`; note in [internals/updater-swap.md](internals/updater-swap.md) §3.

### P1 — product-risk / data-loss / security (do first)
- [ ] **P1 `navigate-accepts-wrong-env-after-one-reload`** — the export path never re-checks
  `_site_params_ok` after sign-in (only `require_signed_in`), so if the one corrective reload
  doesn't switch the site's `CONFIG`, **wrong-env data is saved under a folder labeled with the
  selected env** and reported as success. Add an env backstop on the export path mirroring the
  env-scan's `wrong_site` verdict. (Re-confirms the v0.10.4 `AUTH-WRONG-ENV-SILENT-SUCCESS`; see
  [it-and-security.md](it-and-security.md) §8.2.)
- [ ] **P1 `empty-routes-read-as-export-complete`** — an all-empty run shows the green "Export
  complete" headline (`app.js renderCompletion` keys only on `failed===0`). Show an amber "Finished
  with no data" when `saved+exists===0 && empty>0`.
- [ ] **P1 `transient-export-click-failure-recorded-empty`** — a transient failure in the Export
  click window is recorded `empty` and **never retried** (`_retry_failed_routes` excludes `empty`).
  Make the first `EmptyExport` retriable; collapse to `empty` only if it reproduces.
- [ ] **P1 `reset-deletes-unvalidated-batch-dest`** — "Delete all reports" `rmtree`s the user-chosen
  Everything destination **wholesale** (incl. foreign files) and the confirm dialog **hides the real
  path** (labels only). Scope deletion to known `<src-env>/` children and show `str(path)`.
- [ ] **P1 `update-trust-is-tls-plus-sibling-sha-only`** — auto-update authenticity = TLS (Windows
  store → a TLS-inspection root is trusted) + a same-release `.sha256`; **no signature**.
  Code-signing (Standing § below) is the fix; consider a pinned-in-build public key.

### P2 — bounded correctness / robustness / IT
- [ ] **P2 PDF Highway Log silent-drop trio** (`pdf-stale-geometry-carryforward-silent-corruption`,
  `pdf-page-skip-unlogged-when-no-prior-geometry`, `pdf-consolidator-no-row-count-verification`) —
  the cell-rect parser carries forward stale page geometry / skips data lines with **no log**, and
  never cross-checks extracted rows vs the PDF's data-row count. Log + guard + add a runtime count.
- [ ] **P2 `report-error-text-blanket-swallow-hides-fatal`** / **`highway-sequence-errored-route-can-record-empty`**
  — `report_error_text` swallows all exceptions to `None` with no log → a fatal route can be
  misclassified `empty`/`saved` (worst on Highway Sequence, whose empty = button-absence).
- [ ] **P2 `auto-consolidate-rmtree-out-dir-before-export`** — the Everything store clears a
  report+env folder **before** re-export → a failed refresh destroys the last-good copy and reads
  fresh. Stage-and-swap (clear on success), or flag a short-route folder as partial.
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
- [ ] **P2 `parallel-reconcile-uses-read-strict-not-lock-tolerant`** / **`parallel-crash-plus-cancel-skips-reconciliation`**
  — fast-mode reconciliation re-marks an Excel-locked-but-complete file `failed`, and a crash+cancel
  combo omits orphaned routes from the run report.
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

## Feature backlog

From a notebook brainstorm (2026-06-16); size `[S/M/L]`. Their original version buckets are now in
the Shipped record below. **⚠ A3 and D1 were the planned v0.13 *and* v0.14 themes but got displaced
both times by interface + Highway Log work — deferred 3× and now unscheduled. Decide: bump, drop,
or accept as someday.**

- [ ] **A3 — Results tab / in-app file browser** [M] (#9) — a tab to open the latest per-route
  files, consolidated workbooks, comparison outputs, failure screenshots, and run reports without
  digging through folders. The v0.13.0 Everything-tab **Saved reports** library + env-labeled
  filenames are a partial down-payment on the "what's been produced, where" index this needs.
  *(deferred 3×.)* NOTE: weigh against the planned GUI overhaul (designed elsewhere).
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

What landed, so the open list stays honest. Full changelog: `CHANGELOG.md`.

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
