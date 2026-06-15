# Source-backed verification pass — TSMIS website source × audit findings

This is a **targeted verification**, NOT a re-audit. The two-agent audit
(`AUDIT-claude-0643fe2.md`, `AUDIT-codex-0643fe2.md`, merged in
`RECONCILED-FINDINGS.md`) had to GUESS at the TSMIS site's behavior because the
website source wasn't available. It now is. Your job: use the real source to
**confirm / refute** the automation-contract findings, set the severities that
depend on site behavior, and **find new selector/label/schema mismatches the
first audit could not see.**

## Operating rules (read-only, source stays local)
- Read-only on BOTH trees: the app repo (HEAD `0643fe2`) and the website source.
  Do not modify, run, build, log into, or export from either.
- The website source is Caltrans internal code: keep it LOCAL. Do not push it,
  paste it into a cloud agent, or copy it into the app repo.
- Don't open/print any credential, token, cookie, or report output.
- Anchor every claim to a file + symbol + a short verbatim snippet from
  whichever tree it comes from (app vs site). Keep findings matchable by the
  slug IDs below; new mismatches get `SITE-NEW-*` IDs.

## Inputs
- **App repo:** this checkout at `git rev-parse HEAD` = `0643fe2`.
- **Website source:** `<<SOURCE_PATH>>`  ← (the location of the TSMIS site source).
- **Findings to verify:** the table below (pulled from `RECONCILED-FINDINGS.md`).

## Where the app's automation contract lives (start here)
- `scripts/common.py` → `select_report`, `ERROR_JS`, `_CONFIG_JS`,
  `_site_params_ok`, `navigate_with_auth`, `page_url_for_display`, `expected_host`.
- `scripts/exporter.py` → `save_via_export_button`, `save_pdf_letter`, the
  per-route wait loop; `scripts/export_*.py` → each `wait_js` / `is_empty` / `label`.
- `scripts/gui_worker.py` → `_CONFIG_JS`, `_REPORT_OPTIONS_JS`,
  `EnvScanWorker._check_one` (CONFIG read + report-dropdown probe).

---

## TASK 1 — Verify each finding against the real source

For each row: read the relevant site source, then mark **Confirmed / Refuted /
Partial / Can't-tell**, quote the deciding site snippet, and state the resulting
severity (some severities are gated on these answers).

| Slug | The claim / assumption to check | The exact question the source answers |
|---|---|---|
| AUTH-TOKEN-IN-LOG-BUNDLE | Token rides in the URL `#fragment` and is still on `page.url` when the app logs it | After the SPA reads the token on load, does it clear `location.hash` (e.g. `history.replaceState`)? If yes → success-path log is clean and only failure-path logs leak; if no → the P0 stands in full. |
| AUTH-WRONG-ENV-SILENT-SUCCESS | A `goto(url)` reload with corrected `env`/`src` is assumed to re-land on that env | Does the site reliably honor the `env`/`src` URL params on reload, or can it revert to a default (sessionStorage/last-used)? Determines whether the "accept after one reload" bug can ever trigger (and whether it's P1 or P0). |
| PROD-STALE-EXPORT-BUTTON-CONTRACT / INTERSECTION-READY-NOT-ROUTE-SPECIFIC | Readiness = a *global* `button.export-btn` present; assumed the prior route's button is gone before the next Generate resolves | Does `clearResults()` (or equivalent) remove/disable `button.export-btn` synchronously *before* a new Generate produces results? If not, a wrong-route export is possible. |
| AUTH-BRITTLE-SELECTOR-CONTRACT | Hard-coded ids/labels: `#customReport`, `#districtCountySelect`, `#rampResults`, `button.export-btn`, `-- ALL --`, `District / County / Route`, `Generate`, report labels (`TSAR: Ramp Detail`, intersection labels w/o `TSAR:` prefix) | Do each of these ids / option values / button texts / report labels exist verbatim in the current site source? Flag any that differ, moved, or are dynamic. |
| AUTH-ENV-SCAN-UNKNOWN-CONFIG-OK | App reads a top-level `const CONFIG` for `env`/`src` via `_CONFIG_JS` | What is the real `CONFIG` object shape and the exact `env`/`src` field names? Is it a top-level `const` (not `window.CONFIG`)? A rename silently disables the wrong-site + env-scan checks. |
| ENVSCAN-UNKNOWN-REPORTS-OK | Report dropdown options + greyed/disabled detection (`cs-disabled` etc.); availability via exact-then-`includes(label)` | What is the real option DOM/structure and the actual disabled-state class(es)? Is the `includes()` substring fallback safe against similar report names? |
| (empty markers) | `is_empty` keys on literal strings: `No ramps found`, `no intersections` (intersection markers documented best-guess) | What are the EXACT empty-result strings the site emits per report, and what is the real `#rampResults.error` error-box markup (`ERROR_JS`)? |
| SHEET-FORMULA-INJECTION-DATACELLS | Severity P1-vs-P2 hinges on whether report fields can hold free text starting with `=`/`+`/`-`/`@` | Which report fields are free text (e.g. Highway Log "Description", TSN description lines)? Can any legitimately begin with `=`/`@`? |

## TASK 2 — Independent mismatch sweep (find what the first audit couldn't)

Don't stop at the table. Enumerate EVERY hard-coded contract token in the app —
element ids, CSS selectors, option `value`s, label/button text, empty-state
strings, error selectors, `CONFIG` reads, URL params + fragment handling, and the
download/export trigger — and for each, locate the corresponding thing in the
site source and classify: **Match / Mismatch / Not-found-in-source**. Every
Mismatch or Not-found is a candidate bug → give it a `SITE-NEW-<slug>` ID with
both the app snippet and the site snippet. Pay special attention to anything the
app waits on, clicks, or parses by position (PDF x-window parsers excluded —
they're calibrated to vendor PDFs, not this site).

## TASK 3 — Fix-relevant details

For the planned fixes, record the concrete source facts they'll need:
- the exact empty-state string(s) to match per report,
- the real `CONFIG` field names,
- the real disabled-state class(es),
- whether the token hash is cleared (decides the token-fix scope),
- the real `clearResults()`/readiness signal to wait on (so the fix can wait on
  the *right* condition, not the global button).

## Output
Write to `code-review/SOURCE-VERIFY-<agent>-<short-sha>.md` (do not commit). Lead with:
- the app SHA + an identifier/path of the site source you read (commit/version if it has one).
- **Table A — Verifications:** Slug | Verdict (Confirmed/Refuted/Partial/Can't-tell) | site evidence | resulting severity / change.
- **Table B — New mismatches:** SITE-NEW-id | app snippet | site snippet | impact | confidence.
- **Table C — Fix facts:** the concrete strings/field names/selectors the fixes need.
- A short "what I could NOT determine from the source and why" list.
Keep slug IDs stable so this slots back into `RECONCILED-FINDINGS.md`.
