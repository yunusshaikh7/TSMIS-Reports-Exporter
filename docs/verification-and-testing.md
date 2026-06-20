# Verification & Testing

How this repo — which has **no unit-test framework** — is actually verified: the
golden `build/check_*.py` guards, the frozen `-SelfTest` gate, the comparison
verification loop against real data, the `#mock` GUI preview, and the still-owed
live-export on the work PC. This doc OWNS the golden-checks catalog and the
verification loops; it links out for the regression-lock internals
([comparison-engine.md](comparison-engine.md)) and CI mechanics
([build-and-release.md](build-and-release.md)).

## The core fact: there is no test framework

There is **no pytest / unittest suite, no coverage tooling**. "True"
verification of behavior is one of two real-world acts:

1. **A live export against TSMIS** (needs a login; exercises the engine end to
   end against the real site), or
2. **Running a consolidator / comparison over real exported files** and checking
   the output.

Everything below is the scaffolding that approximates those two acts when they
can't be run — runnable golden guards, a frozen self-test, an Excel-COM recalc,
and a browser preview of the UI. None of them replaces a live export; they catch
regressions cheaply between live runs.

## The verification ladder

Cheapest/fastest first; each rung catches what the rung below can't:

| Rung | What it proves | Needs | Where |
|---|---|---|---|
| **Byte-compile** | nothing imports-broken | python only | CI `compileall` |
| **Golden `check_*.py`** | engine / GUI-bridge / updater / compare-engine / parsers locked | `build\.venv` python; no login, no browser (except fake-site), no Excel, no network | local + CI (blocking) |
| **Fake-site selector contract** | the live-site JS/selector predicates still match real DOM | a drivable headless Chromium/Edge (skips cleanly if none) | `check_fake_site.py`, CI |
| **COM-recalc compare verification** | the formulas/values flavors agree and every SELF-CHECK reads OK after F9 | real Excel installed (dev PC) | `%TEMP%\tsmis_regress\com_verify.ps1` |
| **`#mock` GUI preview** | `scripts/ui/` renders + behaves without launching the app | preview HTTP server on port 8765 | `Claude_Preview` / browser |
| **Frozen `-SelfTest`** | the **pruned frozen bundle** still runs every code path | a build (`build.ps1 -SelfTest`) | release gate, CI release.yml |
| **Live export on the work PC** | the only proof the engine works against the real TSMIS site | the locked-down Caltrans work PC + a login | **STILL OWED** (see below) |

The dev PC cannot reach the TSMIS intranet host, so rungs 1–6 are everything that
can run off the work PC; the top rung is owed work (see
[Live-export verification is owed](#live-export-verification-is-owed-on-the-work-pc)).

## Golden `check_*.py` catalog

Plain runnable guards (no login). Run them with the build venv interpreter after
any Python edit:

```
build\.venv\Scripts\python.exe build\check_<name>.py
```

`.github/workflows/checks.yml` runs them **blocking** on every push/PR (after a
`compileall` of `scripts build version.py`). CI forces `PYTHONIOENCODING=utf-8`
because the comparison checks print the ` ≠ ` diff marker, which a Windows cp1252
stdout (the runner default) would crash on. Three lint/audit steps (ruff
`E9,F63,F7,F82`; bandit `-lll -iii`; pip-audit) run **advisory** (never block).

### Engine / GUI / updater (the "og" set)

| Check | Locks |
|---|---|
| `check_export_engine.py` | WS1/WS3 audit-fix hardening: integrity helpers (XLSX `PK` / PDF `%PDF` magic), empty-marker predicates incl. Highway Sequence's positive "No results found" marker, `cs-disabled` detection in `select_report`; the Phase-3 fixes — `require_site_params` env backstop, the retry-once-then-empty path (`_process_route`), `report_error_text` logging. Pure Python, no browser. |
| `check_parallel_reconcile.py` | Phase-3 parallel-engine reconciliation (`_reconcile_unaccounted`): lock-tolerant `_can_resume` (not read-strict), and reconcile-on-crash-even-if-cancelled. |
| `check_intersection_gate.py` | the app-wide intersection disable: `export_reports_status` SHOWS Intersection greyed (per-report `disabled` flag) rather than hiding it, `enabled_export_reports`/`report_library_info`/matrix still exclude it, `start_*` reject a disabled index server-side, EXPORT_REPORTS indices stay stable, toggle-back-on. |
| `check_fake_site.py` | Selector contract via a **real headless browser** over authored synthetic HTML fixtures (`build/fake_site/*`) that reconstruct only the contract-bearing DOM (the shared action bar, per-report empty states, `#rampResults` error box, `#customReport` dropdown). Catches selector drift pure Python can't — e.g. `EXPORT_READY_JS` keying on a button's *text*, not the bare `.export-btn` class shared by Print. Fixtures are AUTHORED reconstructions, **not** copies of the Caltrans-internal source. Prints SKIPPED and exits 0 if no Chromium-based browser is drivable. |
| `check_gui_bridge.py` | `gui_api` bridge methods. Its "dialog blew up" traceback is an **intentional** test fixture — the run still reports `[OK]`. |
| `check_updater.py` | WS4 updater hardening (incl. `test_resolve_previous_release` for the v0.13.0 revert). Updater swap/SHA detail is owned by [build-and-release.md](build-and-release.md). |

### Comparison engine (regression-locked `compare_core`)

These lock the regression-locked `compare_core.py` and the consolidators. Pure
openpyxl/pdfplumber — no Excel, no browser, no network. The compare_core
regression-lock contract (cell-for-cell parity before any formula/label change)
is owned by [comparison-engine.md](comparison-engine.md).

| Check | Locks |
|---|---|
| `check_compare_blankkey.py` | blank-key-field self-check path |
| `check_compare_keyfield.py` | key-is-NOT-always-first-column (PM-keyed Highway Sequence / Ramp Detail vs coarse County) |
| `check_compare_skipwarn.py` | skipped-files-still-match + consolidate-xlsx partial-OK (incompleteness contract) |
| `check_compare_injection.py` | sheet formula-injection guard (`= + - @` stored as TEXT) on compare_core + consolidators |
| `check_compare_coercion.py` | `compare_core.normalize_value` value coercion (dates → ISO) |
| `check_compare_limits.py` | Excel row/column-limit overflow + side-name⇄sheet-name collision guards |
| `check_compare_audit.py` | audit-round hardening across compare_core + compare_env |
| `check_compare_ramp_detail.py` | cross-env Ramp Detail PM re-key (planted mid-list insert isolates one new row) |
| `check_compare_ramp_summary.py` | cross-env Ramp Summary route-keyed compare + route-key normalizer (unpadded `5` == zero-padded `005`) |
| `check_compare_highway_sequence.py` | cross-env Highway Sequence adapter end to end: PM key, "Highway Locations" sheet, `(col X)` unnamed-column labels (the stage-1 audit gap) |
| `check_matrix.py` | the comparison-matrix engine (`scripts/matrix.py`): 5-row enumeration (both Highway Log formats), mtime staleness, stable dateless paths, hidden row/env filters, the unified scoped rebuild list, real `compare_env` orchestration with a planted diff → counts read back + cached |
| `check_matrix_tsn.py` | the multi-mode / TSN engine: per-row mode registry (env / vs-TSN / PDF-vs-Excel; HL is two rows), TSN source detection (file > consolidated > PDFs > none), snapshot mode + greyed unsupported cells, `build_comparison` guards |
| `check_matrix_bridge.py` | the matrix `gui_api` bridge (stubbed workers): every method (baseline / report+env toggle / per-row + global mode / TSN file / scoped refresh / consolidate-TSN), single-task gate, and the "a cell export leaves a paused batch's manifest intact" invariant |
| `check_compare_dupmatch.py` | duplicate-key SIMILARITY pairing (`pair_occurrences_by_similarity` — opposite file order still pairs the truly-equal rows) |
| `check_compare_ditto.py` | ditto (`+`-run) cells are NON-ASSERTING in a Highway Log compare (the `+`/`++` domain convention is owned by [highway_log/comparison-study.md](highway_log/comparison-study.md)) |
| `check_ramp_summary_partial.py` | ramp-summary failures-OK + short-PDF-blank |
| `check_tsn_description_leak.py` | TSN Highway Log Description-leak guards (x0-gate / `*`-totals close / `_is_totals_line`) |
| `check_tsmis_pdf_parse.py` | TSMIS Highway Log (PDF) cell-rect consolidator (char-conservation, 1:1 cell mapping) — see [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) |
| `check_tsmis_pdf_reconcile.py` | TSMIS Highway Log (PDF) row-drop reconciliation surfaces ⚠ INCOMPLETE (dropped-no-geometry lines) + carried-forward-geometry NOTE in `summary_lines` (v0.17.0 Phase 1) |
| `check_highway_log_columns.py` | the corrected 31-column Highway Log labels (position → canonical label) — see [highway_log/columns.md](highway_log/columns.md) |
| `check_highway_log_ditto.py` | the Highway Log ditto resolver (`is_ditto` / `fill_paired_roadbed` / `display_fills`) |
| `check_highway_log_roadbed.py` | the roadbed-aware comparison key (`roadbed_tag` / `roadbed_canonical_location` / `keys_for` opt-in; strictly refines, never merges) |

### v0.12.0+ feature checks (GUI/batch/filenames)

| Check | Locks |
|---|---|
| `check_a1_filenames.py` | A1 self-describing output filenames (`<date> <src>-<env>` stamping; env-tagged batch filenames) |
| `check_a2_compare_filter.py` | A2 — the cross-env compare dropdowns only offer run folders that contain the chosen report |
| `check_b1_pause.py` | B1 Pause/Resume (between-routes hold, works in fast mode) |
| `check_b2_autoconsolidate.py` | B2 auto-consolidate on export finish |
| `check_b3_batch.py` | B3 Export Everything batch engine |
| `check_report_library.py` | always-current destination plumbing / report-ages library |

> When adding a check, mirror CI: add it to the relevant blocking step in
> `checks.yml` and to the `APP_MODULES`/loop as appropriate. Several checks are
> grouped into `bash` loop steps with `set -e` so the first failure reds the job.

## Frozen `-SelfTest` gate (`build/full_smoke.py`)

`full_smoke.py` is the **release gate** — it exercises EVERY real code path the
app depends on, used two ways:

1. **Against the build venv**, to prove `PIL` / `pypdfium2` / `pypdfium2_raw` are
   never imported (so they stay excluded from the bundle).
2. **Frozen** (`build.ps1 -SelfTest`), as the gate that proves a **pruned**
   bundle still runs everything. `-SelfTest -BundleChromium` gates the
   bundled-Chromium path.

What it does (exit 0 = all good; nonzero/raise = something the app needs is broken):

1. **Chromium:** `launch_browser` (system Edge/Chrome) → `page.pdf()` (the Ramp
   Summary path, format `Letter`) + a real `expect_download()` round-trip;
   asserts the PDF is non-empty.
2. **pdfplumber:** exactly the calls `consolidate_ramp_summary` makes —
   `extract_text` / `extract_words` / `extract_tables`; asserts `Route 005` in
   the text and the word `1234` is found.
3. **openpyxl:** a write/read round-trip (the consolidator output path);
   asserts `C2 == 1234`.
4. Reports whether the excludable optional libs got imported (and that
   `cryptography`, a hard pdfminer import, did).
5. **GUI:** imports `webview` + `gui_api`, builds `GuiApi`, asserts
   `get_initial_state()` returns reports + routes and the UI assets exist
   (`gui_api._ui_index_path()`); then actually creates a hidden WebView2 window,
   waits up to 30 s for `window.__tsmis` to appear, reads
   `window.__tsmis.test_state()`, with a 60 s watchdog. A window that can't start
   in the environment is **tolerated as a skip** (printed), but a *started*
   window that fails its JS cycle is a hard `AssertionError`. `UpdateWorker` and
   `CheckWorker` are stubbed to `_NoWorker` so the gate is deterministic and
   offline-safe (never touches the network/GitHub).

The frozen gate runs on `windows-latest` in `.github/workflows/release.yml`;
nothing is published if any gate fails. Build/release mechanics are owned by
[build-and-release.md](build-and-release.md).

## Comparison verification loop (the real "test suite" for compares)

The user approves comparison changes by **opening real samples**; the
throwaway verifier is the only test suite this no-tests repo has for the
comparison engine.

### Real input pairs (LOCAL ONLY)

Live under `C:\Users\Yunus\Downloads\TSMIS\inputs` (moved there from the
Downloads root):

- **Per-route (fast):** `tsmis_highway_log_route 1.xlsx` + `tsn_highway_log_route 1.xlsx`.
- **Consolidated (50k/60k rows):** `tsmis_highway_log_consolidated 1.xlsx` +
  `tsn_highway_log_consolidated 1.xlsx`. Both-flavors generate+verify ≈ 12 min —
  **run in background**.

### The loop (established v0.9.0, 2026-06-11)

1. Write a **throwaway verifier script in `%TEMP%`** that regenerates the
   workbook(s) and checks EVERY cell on every sheet against expectations rebuilt
   from the module's own helpers plus a semantic key→row mirror.
2. Deliver samples to Downloads named
   `TSMIS_vs_TSN_<scope>_Comparison_vN_SAMPLE.xlsx` for the user to approve;
   **delete the superseded `vN-1`** files; **bump the `SAMPLE` version per
   iteration**.

### Route-1 approved counts — NEVER regress

The per-route format is locked to the approved **Route-1** sample:

```
299 both / 18 / 69 / 221 diff rows / 969 diff cells
```

**969** is the current approved figure (was **971** before the v0.11.0 TSN
totals-block fix removed Route-1's 2 leak-caused Description false positives).
(The `comparison-verification-flow` memory claims CLAUDE.md "still says 971 and
is stale", but the current CLAUDE.md already reads 969 — the memory note is the
stale one.)

### Regression-lock harness (`%TEMP%\tsmis_regress\`)

`compare_core.py` is **regression-locked** — any formula/label-text change must be
proven cell-for-cell identical for the TSMIS-vs-TSN flavor before shipping (the
v0.10.0 extraction was accepted only because **756,892 cell positions** matched
exactly across 4 workbooks). The harness scripts (`make_minis.py` /
`gen_outputs.py before|after` / `diff_outputs.py` / `test_env_compare.py` /
`com_verify.ps1`) live **outside the repo** at `%TEMP%\tsmis_regress\` (regenerate
`before/` from a pre-change checkout if the folder is gone). **The full harness
table, the regression-lock contract, and `compare_core` internals are owned by
[comparison-engine.md](comparison-engine.md) §2** — that is the canonical home; this
section is just the verification-ladder entry pointing to it.

### Excel is installed → use COM for empirical behavior

Excel is on the dev PC, so COM automation works
(`New-Object -ComObject Excel.Application`) for empirical tests — used to prove,
e.g., that whole-row `57:57` link targets don't scroll right while bounded ranges
do, and to F9-recalc the formulas flavor so every SELF-CHECK reads OK. This is
the **only** way to verify formula/HYPERLINK behavior (see gotchas below).

## Per-report flawless-audit recipe (v0.17.0 standard)

The bar for the v0.17.0 effort (a full audit + rethink + perfection of **every**
consolidator/comparator, existing and new) is **flawless, cell-for-cell, proven ≥3
independent ways**. Run this recipe for each report's consolidator + vs-TSN comparator
before it is marked done; record the result + the report's approved counts in
[tsn-parsers.md](tsn-parsers.md).

1. **Reconcile both raw files by hand FIRST.** Open the TSN and the TMSIS file and agree
   the key column(s), row identity, and normalization rules **before** writing the loader —
   the `CompareSchema` comes from the data, not a guess.
2. **Assert the wiring** in a `check_compare_<report>_tsn.py` / `check_consolidate_<report>.py`:
   the `CompareSchema` key field + side names, the `COMPARE_REPORTS` row (`group="tsn"`),
   `_CONSOLIDATOR_BY_SUBDIR`, and the `day_matrix._day_rows()` `supported` flip + `build_day_cell`
   dispatch.
3. **Synthetic key-collapse test** — plant a mid-list insert; prove the key field collapses
   the spurious diffs to the real rows (the `check_compare_ramp_detail.py` pattern).
4. **End-to-end** — drive `compare()` / `compare_folders` to a VALUES workbook in `%TEMP%`,
   read it back with openpyxl, assert the diff/one-sided counts and a known diff cell.
5. **Throwaway `%TEMP%` verifier vs RAW ground truth** — regenerate the consolidated +
   comparison from the raw files and check **every cell** against an **independent
   from-scratch recompute that does NOT import the engine** (the v0.9.0 loop).
6. **COM recalc** the live-formulas flavor (F9): every SELF-CHECK row reads OK and the
   formulas flavor equals the values flavor.
7. **Adversarial refutation** — a separate agent/method tries to **refute** the counts
   against the raw source; **verify against the actual PDF/XLSX, don't relay an agent's
   claim** (the ramp-audit gotcha below). A real source inconsistency stays flagged RED.
8. **Lock it** — record the approved counts as that report's canary in tsn-parsers.md, add
   the new `check_*.py` to the blocking loop in `.github/workflows/checks.yml`, and for any
   `compare_core` change confirm the **Route-1 = 969** HL canary is unchanged.

`compare_core` stays **regression-locked** — touching its formula/label text needs the
`%TEMP%\tsmis_regress` before/after harness above; **new behavior is an opt-in
`CompareSchema` field defaulting to the no-op original**, never a fork.

## `#mock` GUI preview (verify `scripts/ui/` without the app)

Verify `scripts/ui/` changes without launching the real app, via a preview HTTP
server. The pywebview traps + the GUI threading model are owned by [gui.md](gui.md).

- **Mock server:** `.claude/launch.json` defines `ui-mock` (Python `http.server`
  on **port 8765** serving `scripts/ui`). Start it (`preview_start("ui-mock")`),
  then navigate to **`/index.html#mock`** — the `#mock` hash engages the built-in
  mock API (`app.js` `WANT_MOCK`). Without it the page waits for the real
  pywebview bridge and shows a fatal banner. The mock must **never auto-start**
  (a silent mock fallback inside the real app would show fake exports).
- **Bare `S`, not `window.S`:** app state is `const S` at module scope and does
  NOT attach to `window`. In `preview_eval`, reference **`S.st` / `S.init`**
  directly — `window.S` is always `undefined` (false-negative "not booted").
- **Screenshot service is flaky:** `preview_screenshot` intermittently hangs
  (30 s timeout) while `preview_eval` / `inspect` / `snapshot` keep working.
  Verify via **DOM-state evals** (classes, computed styles, geometry) — they're
  conclusive. Restarting the server sometimes recovers screenshots; don't fight it.
- **Headless freezes CSS transitions + the media query:** the preview renderer
  reports `innerWidth: 0` until you `preview_resize` to an explicit width (then the
  `≥980px` two-column layout engages), and it does **not** advance CSS transitions
  (a property with a `transition` reads its START value forever). To verify
  transitioned layout/colour (e.g. the matrix `flex-grow` widen, the theme fade),
  set the element's `transition='none'` inline and re-toggle to read the END state,
  and confirm the rule applies (`getComputedStyle(...).animationName`, computed
  values). Watch the actual motion only in the real WebView2 window.
- **Cache / stale page:** the browser caches `app.js` **and `app.css`**; a
  `?cb=`/`#mock` cache-bust on the URL only reloads `index.html`, not the linked
  stylesheet — after a CSS edit, force-refresh it too:
  `var l=document.querySelector('link[rel=stylesheet]'); l.href=l.href.split('?')[0]+'?cb='+Date.now()`.
  If the server died/restarted the page can stay on OLD `app.js` (reloads silently
  fail while down); confirm fresh code with `typeof <a-newly-added-fn> !== 'undefined'`,
  else navigate cache-busted:
  `location.replace('/index.html?v='+Math.floor(performance.now())+'#mock')`.
  `Date.now()` / `Math.random()` are fine in `preview_eval` (it's the page, not a
  Workflow script).
- **Async confirms:** clicking `#btnStartExport` shows the "No saved login"
  confirm asynchronously — click Start, then in a **separate** eval click the
  "Start anyway" button, then check `S.st.task`. A single combined eval finds no
  modal yet.

## Where the real test data + the TSMIS website-source live

**LOCAL ONLY — under `C:\Users\Yunus\Downloads\TSMIS\...` on the dev PC.** Never
commit, copy into the repo, or push any of it.

- `…\TSMIS\inputs\` — the real Highway Log input pairs (above).
- `…\TSMIS\v0.10.4 ramp summary and ramp detail comparisons\`, `…\_audit\`,
  `…\_audit\regen\` — the 3-env real exports (ssor-prod / ssor-test / ars-prod,
  126 routes each: ramp_detail XLSX + ramp_summary PDF) + audit scripts +
  regenerated workbooks.
- The **TSMIS website source** (the live page's HTML/JS) is **Caltrans-internal**
  and lives only in Downloads. It is the **ground truth** for selectors, dropdown
  labels, and the page's `CONFIG` (env/src). When prose disagrees with code about
  a selector or label, the website source decides — but it must **never** be
  committed, copied into the repo, or pushed. The fake-site fixtures in
  `build/fake_site/` are *authored synthetic reconstructions* that carry only the
  class names / element types / marker text the predicates depend on, precisely so
  the real source never enters the repo.

## Live-export verification is owed (on the work PC)

The dev/personal PC **cannot reach the TSMIS intranet host**, so live-site
verification only happens on the locked-down Caltrans **work PC**. A live export
against TSMIS is the only proof the engine works end to end, and several releases
carry it as **owed** work (e.g. v0.10.0/0.10.1 shipped 2026-06-12 with work-PC
live checks pending).

Likewise the managed-PC security controls (Defender / DLP / corporate proxy /
managed Edge) exist on **neither** the personal dev PC nor any cloud runner, so
IT/DLP/endpoint behavior can only be **reasoned about from code, never
empirically tested** off the work PC. The work-PC constraints (no PowerShell /
cmd / admin; unsigned-exe-from-user-folder only) are owned by
[it-and-security.md](it-and-security.md).

## Diagnosing field reports — which machine?

Before diagnosing any "couldn't update" / "it failed" report:

- **It is almost always the WORK PC install, not the dev machine.** Stale copies
  of the app exist locally (e.g. an old one in Downloads); diagnosing those wastes
  a round-trip and annoys the user. **Establish which machine/install the report
  concerns first** — ask, or check whether the local evidence even matches the
  symptoms (version/dates). (Historical miss: 2026-06-12, an ancient local install
  was wrongly blamed; the real failure was the PowerShell-blocked work PC.)
- **Chat file attachments fail silently.** When the user says "I attached X" and
  nothing is visible, **say so immediately** and ask for a re-send or paste —
  don't search the filesystem for it.

## Gotchas that waste time

- **openpyxl reads HYPERLINK cells as blank.** A naive Python/openpyxl reader
  sees the `<side> Row` HYPERLINK columns (and any `=HYPERLINK(...)`-backed cell)
  as blank, because Excel caches no numeric result for `HYPERLINK`. They are
  **correct in real Excel** (COM-verified). **Do NOT flag them as broken** —
  verify in real Excel / COM.
- **Verify agent claims against ground truth — don't relay them.** In the
  2026-06-16 ramp audit, a workflow agent claimed `parse_pdf` "undercounts
  ramp-types" on 9 dense routes; a deeper check **refuted it** (cross-checked
  against an independent geometric word-position extraction across all 378 PDFs ×
  14 ramp types = 5,292 values → **0 mismatches**; exact match to raw page-2
  text). The real shortfall was a **TSMIS source-data inconsistency** (the PDF's
  own Ramp Types breakdown sums short of its stated Total), correctly flagged RED
  by `_audit_ok` — fudging it green would HIDE a real source issue. Always verify
  an agent's claim against the **actual ground-truth PDF/source**, not the agent's
  summary.
- **Verify numbers ≥3 independent ways for an audit you'll "take as fact".** The
  high-confidence method in the ramp audit: an independent from-scratch recompute
  (NOT importing the engine) + Excel COM self-check/parity recalc + v0.11.0
  regeneration + an adversarial refutation agent + the workbooks' own literals —
  all agreed.

## Release-branch / tag pitfall

Don't name a release branch after the tag — the v0.9.0 branch+tag collided on
push. If it happens, push tags as `refs/tags/<tag>`.

## See also

- [comparison-engine.md](comparison-engine.md) — the compare_core regression-lock
  contract + engine internals the compare checks guard.
- [build-and-release.md](build-and-release.md) — CI mechanics, the release gate,
  updater swap/SHA/revert.
- [gui.md](gui.md) — the pywebview traps + GUI threading/queue model behind the
  `#mock` preview.
- [it-and-security.md](it-and-security.md) — work-PC constraints (no PowerShell /
  cmd / admin), DLP, managed Edge.
- [highway_log/columns.md](highway_log/columns.md),
  [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md),
  [highway_log/comparison-study.md](highway_log/comparison-study.md) — the
  Highway Log specifics the parser/column/ditto checks lock.
