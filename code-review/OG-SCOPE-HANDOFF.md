# OG-SCOPE-HANDOFF.md — export/GUI/updater/auth/settings/build/CI scope

Status of the **"og"** half of the next-patch audit fixes (the non-comparison
scope). The comparison/consolidator scope is tracked separately in
`COMPARISON-TODO.md` and lands its own handoff. This doc is informational for the
final release; it does **not** direct the comparison work.

Branch `next-patch-og` · baseline `897f8e1`. The og scope is **functionally
complete, CI-green, and adversarially audited (no P0/P1).**

---

## 1. What shipped (committed)

| WS | Area | Highlights |
|----|------|-----------|
| WS1 | export engine | General no-download fast-fail (`EmptyExport`, 60 s `download_start_timeout`) — kills the ~21-min empty-route hang, marker-independent. Intersection Detail `td.hl-empty` / Summary `Total Intersections = 0`. Saved-file integrity (xlsx/pdf magic) + lock-tolerant resume. `EXPORT_READY_JS` (Export text, not Print). `cs-disabled` → `ReportUnavailableError`. |
| WS3 | auth/logging/settings | `auth_state` token-fragment redaction; viewport failure shots; env-scan `unverified` fail-closed; custom site-URL validation (https + `*.ca.gov` + matching `?env=`/`?src=`); corrupt-config `.corrupt` backup. |
| WS4 | updater/supply-chain/IT | Updater **SHA-256 verify** + staged-items allowlist; `release.yml` tag==`version.py` assert + publishes `.sha256`; new `checks.yml` CI; prune DLP scans the Chromium tree; `build/IT-NOTES.md`. |
| WS5 | GUI bridge | Single-flight task gate; `_pick_report` bounds; `_safe_day`/`_resolve_under_output` traversal guards; reset confirm-token. |
| WS6 | polish | Reset cancel + actual-freed; PID-scoped window icon; manifest comment; auth-at-rest note. |
| tests | regression guards | `build/check_{export_engine,gui_bridge,updater,fake_site}.py` — all green in `build/.venv`; the fake-site harness drives a real headless Chromium against 17 DOM fixtures. |

## 2. Audit result (multi-agent, adversarially verified)

**No P0/P1.** The classic risks were independently confirmed absent: the
EmptyExport bound is `min(60 s, ceiling)`; the updater hashes the exact bytes and
aborts-before-extract on mismatch; the staged allowlist matches what `build.ps1`
emits; the single-flight gate has no claimed-but-never-released path; the reset
token is race-free + single-use.

**P2/P3 leftovers FIXED in the audit follow-up commit (`224f406`):**
- `open_consolidated_folder` now has the WS5 `_pick_report`+`_safe_day` guards.
- `checks.yml` chromium install is `continue-on-error` (the fake-site test
  self-skips / falls back to Edge).
- Env-scan fail-closed verdict factored into a pure `gui_worker.env_verdict()` +
  unit-tested; corrupt-config backup + SHA-256 mismatch-abort now tested.
- `set_thread_site` partial-None guard; `_find_own_window` text-call argtypes;
  `download_start_timeout` comments corrected (config.json, no Settings UI);
  fake-site enabled-report branch capped at 2 s (was ~30 s).

## 3. Owed before the release TAG (close-out — NOT merge blockers)

These were deliberately left for close-out (the handoff scoped them out of my
edits). None blocks the *merge*; all should be done before pushing a release tag:

- [ ] **Bump `version.py`** (code/tests already assume `0.11.0`). ⚠ `release.yml`
      now asserts `tag == version.py`, so a `v0.11.0` tag against `0.10.4` **fails
      the build**.
- [ ] **`CLAUDE.md`** — document the WS fixes (EmptyExport / integrity gate /
      `ReportUnavailableError` / `EXPORT_READY_JS` / intersection markers /
      updater SHA-256 + allowlist / IT-NOTES) and add `DOWNLOAD_START_TIMEOUT_MS`
      to the Timeouts table.
- [ ] **`README.md`** — "Four report types" → six (+ Intersection rows; bump the
      0.8.0 badge).
- [ ] **`build/release_notes.md`** — add a section for this patch (it's the
      published GitHub release body).
- [ ] **UI mock `REPORTS`** (`app.js:1635`) lists 4 → add the two Intersection
      reports (mock/`#mock` screenshot fidelity only; the real app reads all 6
      from Python).

## 4. Flagged for coordination (not edited — touch other scopes / contracts)

- **CI does not gate the comparison-scope regression checks** (`checks.yml` runs
  only the four og checks). The comparison scope's `build/check_compare_*.py` +
  `check_ramp_summary_partial.py` exist and pass; wiring them into `checks.yml`
  (an og-scope file) at merge would protect the regression-locked `compare_core`
  from a future silent break. Left for the merge step so it can reference the
  final set of comparison checks. **This is the one consequential merge gap.**
- **Compare result dialog titles an INCOMPLETE comparison "Differences found"**
  (`gui_api._finish_consolidate`). The comparison scope added a third outcome
  (`verdict="diff"` + a `⚠ COULD NOT COMPARE…` summary line for unreadable
  inputs); the og dialog only branches match/else. Body still shows the real ⚠
  reason and amber-not-green is the safe default, so it's title-only. The og-side
  fix (detect the `⚠` prefix → "Comparison incomplete") depends on the comparison
  scope's summary-line contract being final, so it's flagged rather than applied.

## 5. Verification reality (still owed)

- **Live-export checks on the work PC** — this dev PC can't reach TSMIS. Two
  documented tradeoffs to confirm live: (1) the 60 s download-start cap rests on
  the site's "Export-button-present ⟺ data loaded" contract; (2) the
  `EmptyExport`→empty mapping slightly narrows end-of-run retry coverage for the
  intersection pair (a non-`#rampResults.error` transient in the export-click
  window reads as empty, not retried — resume re-pulls next run). Re-verify both
  once the site finalizes intersections (intersections are flagged in-code as a
  moving target).
- **Code-signing** is the one remaining big IT lever — not done (needs a cert);
  the path is scaffolded in `build/IT-NOTES.md` §7. The updater's checksum +
  allowlist are the integrity half; the signature half waits on the cert.

## 6. Bottom line

The og scope is **release-ready on correctness/security** with no merge blocker.
What stands between the branch and a clean `v0.11.0` is **close-out** (§3) plus
the one CI merge action (§4) — not code defects.
