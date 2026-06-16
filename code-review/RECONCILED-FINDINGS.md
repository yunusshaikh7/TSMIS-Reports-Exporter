# Reconciled Findings — Claude × Codex audit of `0643fe2`

Merged + adjudicated by a neutral third pass (read both reports in full; verified
the one-sided P0/P1 findings against the working tree). Full evidence/snippets
live in `AUDIT-claude-0643fe2.md` and `AUDIT-codex-0643fe2.md`; this file is the
single triage list.

- **Claude:** 27 findings (1 P0, 4 P1, 9 P2, 13 P3) + 8 unproven.
- **Codex:** 21 findings (3 P0, 11 P1, 6 P2, 1 P3) + 6 unproven.
- **After dedup:** ~35 unique issues. **15 were found independently by BOTH agents**
  — treat those as highest-confidence. The severity *split* on shared findings is
  mostly Codex-rates-higher; adjudicated column is my call with reasoning.

Note: "needs source" = the new website source code resolves a real uncertainty
(this is the input list for the source-backed pass, step 2). It does **not** block
the fix — most fixes are unconditional.

---

## ⟳ SOURCE-VERIFICATION UPDATE (2026-06-15 — Claude + Codex agree) — supersedes the tier severities below

Both agents re-verified the contract findings against the real TSMIS source
(`Report Portal Source`, `BUILD_DATE 2026-06-12`). They agree on every item. Net:
the two scariest security findings are **defanged**, and a **new high-impact
functional bug** surfaced.

**Revised MUST-FIX (highest first):**

| # | Issue | Sev | Source verdict |
|---|---|---|---|
| A | **SITE-NEW-INTD-EMPTY-MARKER** *(new)* — empty Intersection Detail routes hang the full timeout + 15-min retry (~21 min) then mislabel `failed` | **HIGH** | App checks `"no intersections"`; site emits `"No results found."` with the Export button **always present** → `wait_js` resolves, Export no-ops, download times out. Fix: detect `td.hl-empty` / `"No results found."` **before** clicking Export. |
| B | SHEET-COMPARE-SYMMETRIC-SKIP-MATCH | P0/P1 | unchanged (no site dependency) |
| C | SHEET-FORMULA-INJECTION | **P1 confirmed** | site has free-text `Description`/name columns (Ramp Detail, HSL, Highway Log, Intersection Detail); fix = one escaping helper on the openpyxl write path |
| D | EXPORT-EXISTING-FILE / SAVED-NO-INTEGRITY | P1 | unchanged |
| E | UPDATER-NO-SIGNATURE + code-signing | P1 | unchanged |
| F | MOTW-ADS-DELETION | P1 | unchanged |
| G | FAILURE-ARTIFACT-LEAK | P1 → **report-data only** | token is **not** in the DOM (lives in `location.hash`/JS memory) → dumps carry report PII but **not** the token; credential angle gone |
| H | RAMP-SUMMARY-FAILURES-OK | P1/P2 | unchanged |

> ⚠ **Intersection caveat (maintainer, 2026-06-15):** the site's Intersection
> Summary/Detail feature is **still under active development**, so its DOM, empty
> strings, and action-bar markup are a **moving target**. Don't hard-lock fix **A**
> to the literal `"No results found."` — prefer the robust structural signal
> (`td.hl-empty`) AND re-verify once the site finalizes intersections. The durable
> fix is a **general empty/no-download fast-fail** (Export clicked, no download in
> ~N s, no error → treat as empty/skip) so marker drift can never re-create the
> ~21-min hang on *any* report.

**Downgraded by the source:**
- **AUTH-TOKEN-IN-LOG-BUNDLE: P0 → P2/P3.** The SPA strips the token via
  `history.replaceState` synchronously in `initAuth()` (inside `DOMContentLoaded`)
  **before** the app's success-path log fires — it does NOT leak on every run.
  Residual = the failure-path raw `page.url` log. Cheap one-line fix retained:
  route URL logging through the existing `page_url_for_display`
  (`SITE-NEW-AUTH-STATE-RAW-URL`).
- **AUTH-WRONG-ENV-SILENT-SUCCESS: P1 → P3.** Reload is reliable (URL params win
  first; per-env hosts + OAuth client IDs mean a mismatched session fails to sign
  in, not silently lands wrong). **Caveat (Codex):** a *custom URL override* that
  omits `?env=`/`?src=` defaults the site to `prod/ars` and can still hit the
  one-reload-accept path — keeps the defensive re-check useful and ties into #18
  SITE-URL-ARBITRARY-ORIGIN (`SITE-NEW-CUSTOM-URL-PARAM-OMISSION`).

**Refuted:**
- **PROD-STALE-EXPORT-BUTTON race (#13).** `clearResults()` runs synchronously
  before the first `await` in all six generate paths → no wrong-route save.
  Reframe to: `button.export-btn` is shared by Export *and* Print
  (`SITE-NEW-EXPORT-BTN-PRINT-COLLISION`) and can't distinguish empty from ready
  for Highway Log / Intersection Detail — the root of bug **A**.

**Confirmed (no change):** `CONFIG` is a top-level `const` with `env`/`src`
(env-scan + wrong-site reads correct today); `cs-disabled` detection works; all
signed-in ids, report labels, `-- ALL --`, `District / County / Route`,
`#rampResults.error` match verbatim. The fail-open on a *future* CONFIG rename /
unreadable dropdown remains valid as written.

**New, lower priority:**
- **SITE-NEW-RAMP-REPORTS-DISABLED — EXPECTED, not a bug.** Both TSAR Ramp reports
  are `cs-disabled` on the live site; per the maintainer TSMIS can temporarily
  disable individual reports by design. Env-scan correctly flags it (`reports_off`).
  Residual low-pri UX: the *export* path doesn't consult the scan, clicks the inert
  `<li>`, and stalls ~30 s into a generic preflight error — nicer to pre-check
  `cs-disabled` and say "this report is currently unavailable on the site."
- **SITE-NEW-INTS-NO-EMPTY-STATE (low):** Intersection Summary never emits an empty
  string (always renders `Total Intersections = N`) → the `"no intersections"`
  predicate is dead; it exports an all-zeros workbook instead of recording `empty`.
  Decide intended behavior or detect `Total Intersections = 0`.
- **SITE-NEW-RAMPDETAIL-XLSX-FILENAME (upstream):** the *site* hardcodes
  `highway_sequence_listing.xlsx` for Ramp Detail's export (a site copy-paste bug).
  Cosmetic for the app (it renames via `save_as`); worth reporting to the TSMIS team.

**Fix facts (concrete strings the fixes need)** — full detail in Table C of either source report:
- Empty markers: Ramp `No ramps found in this segment.` · HSL/Highway Log
  `No results found in this segment.` · Intersection Detail `No results found.`
  (`td.hl-empty`) · Intersection Summary none (`Total Intersections = 0`).
- CONFIG: top-level `const CONFIG`, fields `env`/`src` lowercase; default when
  params absent = `prod/ars`.
- Disabled class `cs-disabled` (no `pointer-events:none` → a click is a silent no-op).
- Token hash cleared by `replaceState` → token-fix scope is logging only.
- Injection fields: the `Description`/name columns only; guard leading `= + - @` in
  the shared openpyxl write helper.

---

## TIER 1 — MUST-FIX (P0/P1) — *pre-source severities; see the Source-Verification Update above for the revised list*

| # | Issue (adjudicated sev) | Claude ID | Codex ID | Found by | Needs source? |
|---|---|---|---|---|---|
| 1 | **OAuth token written to log + shipped in "safe to share" support bundle** (P0) | AUTH-TOKEN-IN-LOG-BUNDLE | AUTH-RAW-URL-LOGGING | **Both** | for blast-radius only; fix unconditional |
| 2 | **Cross-env compare can say "✓ EVERYTHING MATCHES" while dropping routes unreadable on both sides** (P0/P1) | SHEET-COMPARE-SYMMETRIC-SKIP-MATCH | COMPARE-SKIPPED-FILES-MATCH | **Both** | no |
| 3 | **Failure dumps persist full report DOM + full-page screenshots to disk, user-openable** (P1) `[Codex P0 / Claude P3]` | AUTH-FAILURE-DUMP-ON-DISK | FAILURE-ARTIFACT-REPORT-LEAK | **Both** | no |
| 4 | **Raw report values become live Excel formulas (leading `=`/`+`/`-`/`@`)** (P1) `[Codex P1 / Claude P2]` | SHEET-FORMULA-INJECTION-DATACELLS | XLSX-FORMULA-INJECTION | **Both** | which fields can start with `=`/`@` |
| 5 | **Saved download gets no integrity check; resume trusts bare `exists()` → partial file masked as done** (P1) `[Codex P1 / Claude P2]` | PROD-SAVED-FILE-NO-INTEGRITY-GATE | EXPORT-EXISTING-FILE-TRUSTED | **Both** | no |
| 6 | **Self-update downloads + runs an unsigned exe with only a byte-count check; no hash/signature** (P1) | UPDATER-NO-SIGNATURE-VERIFY | UPDATER-UNSIGNED-RELEASE-ASSET | **Both** | no |
| 7 | **Startup bulk-deletes `Zone.Identifier` ADS (anti-forensics look) + leaves browser binaries tagged** (P1) `[Codex P1 / Claude P2]` | IT-MOTW-ADS-DELETION | MOTW-REMOVAL-ENDPOINT-FRICTION | **Both** | no |
| 8 | **Wrong env/src accepted after one corrective reload; output folder labeled by *selection*** (P1) | AUTH-WRONG-ENV-SILENT-SUCCESS | — | Claude | **yes** — does the reload guarantee landing on the env? |
| 9 | **Hidden self-replacing unsigned exe = dropper/EDR heuristic; code-signing is the meta-fix** (P1) | IT-UNSIGNED-SELF-MODIFY-EDR | (via MOTW/updater) | Claude (Codex adjacent) | no |
| 10 | **Ramp Summary consolidator writes an OK workbook even when every PDF parse failed (can overwrite a good one)** (P1/P2) | (generic: SHEET-CONSOLIDATE-SKIPPED-STILL-OK) | RAMP-SUMMARY-FAILURES-OK | Codex (Claude generic) | no |

**Adjudication notes**
- **#1** is the strongest finding (both, P0). Fix is unconditional: strip the URL
  fragment before logging (the codebase already has `page_url_for_display` doing
  exactly this for the screen). Source only decides whether the *success-path* log
  also leaks or just the failure paths.
- **#2 / #3** are the "green but incomplete" / "sensitive data persisted" pair the
  product must not ship. I split the difference on #3 (Codex P0 / Claude P3): it's
  sensitive report data definitely persisted + user-surfaced, but on-machine only
  (verified NOT in the support bundle) and failure-gated → P1. Becomes P0 the day
  FAILURES_DIR is ever bundled.
- **#4** — the scary half is the *silent correctness flip* (a cell `=1+1` compares
  equal to `2` and the " ≠ " diff marker the self-checks rely on can vanish), not
  just the DLP surface. One central escaping helper fixes it without touching the
  regression-locked formula text.
- **#6 + release #16** — signature/checksum on the client AND a publish-side digest
  are a pair; neither works alone. **Code-signing (#9) is the single highest-leverage
  fix** — it addresses the updater trust gap, the EDR look, and SmartScreen at once.

---

## TIER 2 — SHOULD-FIX (P2)

| # | Issue | Claude ID | Codex ID | Found by | Needs source? |
|---|---|---|---|---|---|
| 11 | XLSX consolidators return `status="ok"` after skipped/failed/header-drift inputs | SHEET-CONSOLIDATE-SKIPPED-STILL-OK | CONSOLIDATE-XLSX-PARTIAL-OK | **Both** | no |
| 12 | Env-verify scan fails OPEN to `ok` — two ways: CONFIG unreadable (Claude) **and** report-dropdown unreadable → only first report probed (Codex) | AUTH-ENV-SCAN-UNKNOWN-CONFIG-OK | ENVSCAN-UNKNOWN-REPORTS-OK | **Both** (complementary) | partial |
| 13 | Readiness keys on a *global* Export button / empty-text with no route-specific check → wrong-route or stale save | PROD-STALE-EXPORT-BUTTON-CONTRACT | INTERSECTION-READY-NOT-ROUTE-SPECIFIC | **Both** | **yes** — does `clearResults()` drop the button before Generate? |
| 14 | Whole automation contract = hard-coded ids/labels/best-guess empty markers; no fake-site harness | AUTH-BRITTLE-SELECTOR-CONTRACT | (4 contract items) | **Both** | **yes** |
| 15 | Support bundle / manifest overbroad: usernames in paths, OS, settings, run reports; "safe to share" oversold | FS-BUNDLE-MANIFEST-PII | SUPPORT-BUNDLE-OVERBROAD | **Both** | no |
| 16 | CI publishes unsigned, un-digested zips; deps installed without `--require-hashes`; tag≠`version.py` unchecked | RELEASE-NO-DIGEST-OR-SIGN | RELEASE-WRITE-TOKEN-UNHASHED-DEPS, RELEASE-TAG-VERSION-UNCHECKED | **Both** | no |
| 17 | Local CDP debug port + pre-granted `local-network-access` broaden managed-PC surface | AUTH-CDP-PORT-LOCALHOST | CDP-LNA-ENDPOINT-SURFACE | **Both** | no |
| 18 | Custom site-URL override accepts ANY http(s) origin; host-check follows it | (SETTINGS-SITE-URL-HTTP-ALLOWED, §10) | SITE-URL-ARBITRARY-ORIGIN | **Both** | maintainer Q: restrict to `*.dot.ca.gov`? |
| 19 | `start_export` check-then-set across two lock blocks (TOCTOU) `[Codex P1 / Claude P3]` | GUI-TASK-GATE-TOCTOU | GUI-TASK-START-RACE | **Both** | no |
| 20 | With-browser DLP content scan exempts the whole `ms-playwright` tree | DLP-CHROMIUM-CONTENT-SCAN-SKIP | (PRUNE-…, unproven) | Claude (verified) | no |
| 21 | Bridge accepts raw `day`/folder strings → resolve outside `OUTPUT_ROOT` (**verified**: bounded by needing WebView JS exec) | — | GUI-DAY-PATH-ESCAPE | Codex (verified) | no |
| 22 | Destructive bridge methods trust client-side confirmation (**verified**; bounded by bridge access) | — | GUI-CONFIRMATION-BYPASS | Codex (verified) | no |
| 23 | Update swap installs every staged top-level item, no manifest allowlist (**verified**; amplifier of #6) | — | UPDATER-STAGED-EXTRA-ITEMS | Codex (verified) | no |
| 24 | Headed login saves `storage_state()` without the portability check device captures use | — | LOGIN-STANDARD-SKIPS-PORTABILITY | Codex | no |
| 25 | One-page/partial Ramp Summary PDF parsed as a blank record, not a failure | (PDF-WINDOW-MISPARSE, §10) | RAMP-SUMMARY-SHORT-PDF-BLANK | Codex | no |

---

## TIER 3 — POLISH (P3)

| Issue | ID | Found by |
|---|---|---|
| README / `Start Here.txt` / UI mock still say "4 reports"; registry exports 6 | DOCS-MOCK-REPORT-DRIFT | Codex |
| Manifest cites removed Tk UI; no `dpiAware` → blurry hi-DPI; stale assemblyIdentity | IT-MANIFEST-DPI-STALE | Claude |
| `1. setup.bat` = global pip + Chromium CDN download (most IT-hostile path) | IT-SETUP-BAT-GLOBAL-PIP | Claude |
| Registry indexed with unchecked `int(report_idx)` (inconsistent w/ start_export) | GUI-REGISTRY-INDEX-UNCHECKED | Claude |
| `Cancel` tuple omits `envcheck`/`reset` → silent no-op while they run | GUI-CANCEL-MISSES-TASKS | Claude |
| `FindWindowW(None, APP_NAME)` cross-process `WM_SETICON` to first same-titled window | GUI-ICON-FINDWINDOW-TITLE | Claude |
| Corrupt `config.json` silently → defaults; next write drops `site_urls` overrides | FS-CONFIG-SILENT-RESET | Claude |
| Reset reports pre-deletion file/MB counts even when items failed to delete | FS-RESET-OVERREPORTS-FREED | Claude |
| `storage_state` written as plaintext JSON (no DPAPI) | AUTH-FILE-PLAINTEXT | Claude |
| No guard vs Excel's 1,048,576-row ceiling (doesn't trigger at ~65k today) | SHEET-ROWLIMIT-NO-GUARD | Both (Claude P3 / Codex unproven) |

---

## INVESTIGATE (no quoted-code home; need a fixture, sample data, or the source)

PDF x-window misparse on shifted columns · Ramp Summary `route=None` blank-key row ·
values-flavor SELF-CHECK shares the mirror it's checking · env-scan page-reuse CONFIG
bleed · zip-slip via `extractall` · reset junction/symlink traversal · compare
sheet-name collision with `Summary`/`Comparison` · values-vs-Excel date `TRIM` parity ·
`_wait_pid_exit` PID-recycle · `open_release_page` URL provenance.

---

## WHAT THE WEBSITE SOURCE RESOLVES — ✓ DONE (answers in the Source-Verification Update at top)

1. Does the SPA clear `location.hash` after reading the token? → blast radius of **#1**.
2. Does `clearResults()` remove `button.export-btn` before a new Generate resolves? → **#13**.
3. Is a `goto(url)` reload with corrected `env`/`src` guaranteed to land on that env? → trigger for **#8**.
4. Exact empty-state strings ("No ramps found", "no intersections") + the `#rampResults.error` box. → **#13/#14**.
5. Real `CONFIG` shape (top-level `const`) + report-dropdown labels & disabled-state classes. → **#12/#14**.
6. Which report fields are free text that can begin with `=`/`@`. → severity of **#4**.

These also seed the **fake-site harness + selector-contract tests** both agents call the
top testing gap.

---

## NEXT-PATCH PLAN — complete ALL fixes (goal: next patch)

Ordered by value × safety. `compare_core` changes are gated on the COM-recalc
regression harness; intersection changes are gated on the moving-target caveat above.

**WS1 — Export-engine correctness (isolated specs/engine; no regression-locked code)**
- [ ] **General empty/no-download fast-fail** — Export clicked, no download in ~N s, no error → empty/skip. Robust to marker drift; kills the ~21-min-hang class for every report.
- [ ] Intersection Detail empty marker (`SITE-NEW-INTD-EMPTY-MARKER`) — detect `td.hl-empty` (+ text fallback) before Export; **re-verify when site finalizes intersections**.
- [ ] Intersection Summary dead predicate (`SITE-NEW-INTS-NO-EMPTY-STATE`) — detect `Total Intersections = 0`, or accept always-export (decide).
- [ ] Saved-file integrity gate (`EXPORT-EXISTING-FILE`) — size/validity check; resume re-pulls partial/too-small files.
- [ ] Qualify readiness selector to Export-only (`SITE-NEW-EXPORT-BTN-PRINT-COLLISION`; Print shares `.export-btn`).
- [ ] Expected-disabled report UX (`SITE-NEW-RAMP-REPORTS-DISABLED`) — pre-check `cs-disabled`, say "currently unavailable on the site."

**WS2 — Spreadsheet integrity (⚠ touches regression-locked `compare_core` — run COM harness before/after)**
- [x] **`COMPARE-BLANK-KEYFIELD-SELFCHECK` — ✓ FIXED & VERIFIED** (branch `next-patch-audit-fixes` @ 8bf9fad; Excel-COM before/after on a blank-key fixture: 6/9 CHECK + wrong verdict → 9/9 OK + correct verdict; per-route shape unchanged 6/6 OK; regression guard `build/check_compare_blankkey.py`). *(NEW — root-caused 2026-06-15 against real data; affects ALL comparison types):*
  the cross-env **Highway Sequence** files fail **6 of 9 SELF-CHECK rows** (confirmed by interactive
  F9); both **Highway Log** files pass 9/9. **ROOT CAUSE — blank values in the comparison's key
  field.** Verified from the data: HwySeq keys on Route+**County**, and County is blank on 4 SSOR-PROD
  / 117 SSOR-DEV / 117 union rows; HwyLog keys on Route+**Location** (postmile, never blank) → 0 blanks.
  That blank count is the *entire* difference — **not** occurrence collisions (every row got a unique
  key: uniqkeys == rows on both sides, 0 phantom rows). Two distinct defects, both general, both in
  the schema-parameterized engine (`compare_core`):
  - **(A) Row-count proxy bug → C37 / C43 / C44 / C45 (and the C9–C11 "data rows"):** these count rows
    via `COUNTA('<sheet>'!<keyfield-col>)-1`, which **undercounts blank-key rows** → false CHECK. Fix:
    count by an always-populated column (the leading "Comparison row" link col A, or Route, or `COUNT()`
    of a build-written counter). Clears 4 of the 6 CHECKs; pure noise — the 60k non-blank rows are fine.
  - **(B) Blank-key occurrence reconciliation → C39 / C41:** the data-sheet key
    `=B&"|"&C&"|"&COUNTIFS($B$2:$B2,$B2,$C$2:$C2,$C2)` mis-numbers blank-key rows (Excel's COUNTIFS
    blank-criterion is unreliable), so they don't reconcile with the build's literal `#` → those rows
    mis-look-up and get mis-categorized (the real workbook puts **4 fewer** rows in "Both" than the data
    warrants — exactly the 4 PROD blanks). Fix: author the key/occurrence ONE way — have the build write
    it as a literal (or normalize blank→sentinel in both the build `#` and the data-sheet formula) so
    there's no Excel re-derivation that can diverge.
  **Deliverability:** the 2 HwySeq cross-env files are **NOT deliverable** (self-check fails + the blank-County
  rows are mis-handled); the 60k+ non-blank rows are correct. Both fixes live in the shared engine → they
  harden **every** report's comparison at once. Regression-locked: run the COM harness, and **add a
  blank-key-field fixture** to the golden tests — that's the exact gap the planted-difference fixtures missed.
- [ ] **`COMPARE-KEY-IS-FIRST-COLUMN` (NEW, HIGH — found 2026-06-15 in the thorough pass):** the
  engine hard-keys every row on `header[0]` — the report's **first column**. Only Highway Log makes
  that granular on purpose (pins `EXPECTED_HEADER` with Location/postmile first). Cross-env **Highway
  Sequence inherits County** (coarse) → rows align *positionally within (Route, County)* instead of by
  postmile, so when two environments differ in row count within a county the alignment **shifts and
  emits spurious field-diffs + one-sided rows** (one missing point cascades into many). PM is right
  there in the data and is the correct identity. **The existing HSL cross-env diff counts are likely
  inflated** (this is separate from, and on top of, the blank-key bug). Fix: give HSL a granular key
  (PM) — reorder so PM is `header[0]`, OR add a `key_field` selector to `CompareSchema` (cleaner, keeps
  display order, but touches `_Layout`/`keys_for`/`key_expr`/`count_diffs` which all assume `header[0]`
  is the key). **Verify Ramp Detail's first column too** (its key = whatever the export's first column
  is; no sample on hand). Unaffected: Highway Log (Location), Ramp Summary (route-keyed), TSMIS-vs-TSN
  (Location). Regression-locked → COM harness + a misalignment fixture (two sides, a mid-group missing row).
- [ ] **`COMPARE-VALUE-COERCION` (NEW, MED/LOW — latent):** `count_diffs` and the cell formulas compare
  values in text form (`_xl_trim` → `str()` / Excel `TRIM`). Text-vs-number (postmile `"000.129"` vs
  `0.129`) or date-vs-datetime (`"760225"` vs a real date) formatting differences between the two sides
  → spurious diffs; real-date cells also risk a **formulas-vs-values parity** mismatch (Excel `TRIM(date)`
  ≠ Python `str(datetime)`). Doesn't bite for same-format same-app exports; latent cross-env / post-
  consolidation. Add mixed-type + real-date golden fixtures.
- [ ] Formula-injection escaping helper (guard leading `= + - @`) on the shared openpyxl write path, scoped to the Description columns.
- [ ] Compare false-match — skipped / both-side-unreadable routes break the verdict and surface in counts.
- [ ] Consolidate status honesty — `status != "ok"` (or explicit partial) on skip / header-drift / all-fail (incl. Ramp Summary all-parse-fail).
- [ ] (opt) Excel row-limit guard.

**WS3 — Auth / logging / settings hardening (low risk)**
- [ ] Route all URL logging through `page_url_for_display` (`SITE-NEW-AUTH-STATE-RAW-URL`).
- [ ] Failure-artifact dumps — gate/redact (report PII; token isn't in DOM).
- [ ] Env-scan fail-closed (CONFIG unreadable + report-list unreadable → not "ok").
- [ ] Support-bundle redaction + truthful "safe to share" wording.
- [ ] Custom-URL validation — require `?env=`/`?src=`, restrict host (maintainer Q: `*.dot.ca.gov`?).
- [ ] Document CDP/LNA flags for IT.

**WS4 — Updater / supply chain / IT (infra; biggest IT-approval lever)**
- [ ] **Code-signing** — unlocks updater trust + EDR + SmartScreen at once.
- [ ] Updater signature/checksum verify + staged-items allowlist.
- [ ] Release: publish SHA-256 + sign + assert tag == `version.py`; hashed deps.
- [ ] MOTW approach review + an "what this app does on the network/files" IT note.
- [ ] DLP scan covers the Chromium tree.

**WS5 — GUI bridge hardening (P2)**
- [ ] `start_export` single-flight (close the TOCTOU).
- [ ] Validate `day`/folder inputs (no traversal outside `OUTPUT_ROOT`).
- [ ] Server-side confirm for destructive ops; bounds-check registry indices.

**WS6 — Polish (P3)**
- [ ] Docs/mock report drift (4→6). · Manifest DPI/version. · Cancel covers `envcheck`/`reset`. · Reset over-report. · Config silent-reset signal. · Icon FindWindow. · Auth-file-at-rest note.

**Cross-cutting — tests (both agents' #1 ask; the source now enables a fake-site harness)**
- [ ] Golden-workbook tests (formula-injection, symmetric-skip, all-fail, header-drift, row-limit).
- [ ] Updater swap/rollback sandbox test · token/redaction test · bridge-API tests.
- [ ] Fake-site harness from the source (data / empty / error / disabled fixtures) + selector-contract tests.
- [ ] CI static checks (pip-audit / bandit / ruff / compileall).

**Close-out:** bump `version.py`, update `CLAUDE.md` + README + UI mock (4→6 reports) + `release_notes.md`.
