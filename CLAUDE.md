# CLAUDE.md — TSMIS Reports Exporter

A portable Windows desktop tool that bulk-exports TSMIS (Caltrans Transportation
System Management Information System) reports for every California state route.
The user picks one, several, or all report types from a menu/checkboxes; one
shared login serves them all.

Combines the former `TSMIS-Reports-Export-ALL-Ramp-Summary` and
`…-Ramp-Detail` projects.

## Supported Reports

| # | Report | Output | Folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/<run>/ramp_summary/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/<run>/ramp_detail/` |
| 3 | Highway Sequence Listing | XLSX | `output/<run>/highway_sequence/` |
| 4 | Highway Log | XLSX | `output/<run>/highway_log/` |

`<run>` is a **run folder**, `"<YYYY-MM-DD> <src>-<env>"` (e.g.
`2026-06-11 ssor-prod`, v0.10.0) — see *Key Behaviors: run folders*.

One TSMIS page serves every combination of **data source** (SSOR / ARS) and
**environment** (prod / test / dev) via query parameters — see
`common.get_url()`. Defaults: **SSOR + Prod**; the GUI header has two dropdowns
(`set_site`) plus a **Verify env button** (v0.10.0, `EnvCheckWorker`: opens the
page headless exactly like an export, reads the page's own CONFIG env/src via
`_CONFIG_JS`, screenshots it, and the modal says whether it matches the
selection — the user's "am I really on SSOR DEV?" answer without exporting),
the console flow honors `TSMIS_SRC` / `TSMIS_ENV`. **Per-env URL overrides**
(v0.10.0): the Settings tab can rewrite any combo's address
(`settings.get_site_url` → consulted by `common.get_url()` on every
navigation; `common.expected_host()` follows the effective URL, and
`is_logged_in` + the navigate breadcrumbs compare hosts against IT, not the
built-in TSMIS_HOST) — the stopgap for "the site moved before an app update
shipped". Console flows honor the same overrides automatically.

**Beyond the TSMIS exports (v0.8.0, ported from TSMIS-Report-Consolidator):**
- **TSN Highway Log** (consolidate-only): parses TSN district Highway Log PDFs
  (report OTM52010) that the user drops into `input/tsn_highway_log/`, writes
  TSMIS-format per-route workbooks to `output/tsn_highway_log/` and one
  combined `output/tsn_highway_log_consolidated.xlsx`. The PDF parsing core
  (`consolidate_tsn_highway_log.py`) is verbatim from the sibling repo —
  x-position character-window parsing calibrated against real district PDFs;
  don't re-derive the windows. `day` is ignored (vendor snapshots aren't dated
  exports); the module exposes `INPUT_NOTE`/`INPUT_DIR` so the Consolidate
  pane shows where the PDFs go.
- **Compare tab** — two comparison families since v0.10.0, both built by ONE
  engine: `compare_core.py` (extracted verbatim-then-parameterized from
  compare_highway_log; a `CompareSchema` carries side names — emitted into
  formulas through the quoting-aware `_sref` so `TSMIS!A:A` stays unquoted but
  `'SSOR-PROD'!A:A` quotes — header, normalizer/date fields, label nouns,
  widths, note fragments. The extraction is **regression-verified
  cell-for-cell** — values, formulas, styles, CF, calc mode — against the
  pre-extraction output on the real Route-1 + consolidated pairs; do NOT
  change formula/label text in the core without re-running such a check).
  - **TSMIS vs TSN Highway Log** (`compare_highway_log.py` = schema + loaders
    + `suggest_name`; `"files"` kind in `COMPARE_REPORTS`).
  - **Cross-environment** (`compare_env.py`; `"folders"` kind, v0.10.0): the
    SAME report from two run folders (ssor-prod vs ars-prod, or one env on
    two dates) — per-route files are read straight from both folders (NO
    consolidation step; merged in memory the way the consolidators would,
    Route column prepended, header locked from the first file) and compared
    with the environment names as the sides (`side_label`; same-env sides get
    the date appended so sheet names differ). Ramp Detail / Highway Sequence
    lock their layout from the files (both folders must agree); Highway Log
    pins EXPECTED_HEADER + the Med Wid rule; **Ramp Summary parses the PDFs**
    via consolidate_ramp_summary.parse_pdf, one row per route (per-route
    shape — the route IS the row key; fields = the consolidator's GROUPS
    minus Source/Audit). GUI: folder dropdowns list the run folders
    (baseline defaults to newest ssor-prod) + Browse; saves default to
    `output/comparisons/`. Verified with planted-difference fixtures and a
    real-Excel COM recalc (all SELF-CHECK rows OK).
  **Every comparison leads with a VERDICT** (v0.10.0): summary_lines[0] is
  "✓ EVERYTHING MATCHES …" / "✗ DIFFERENCES FOUND …",
  `ConsolidateResult.verdict` is "match"/"diff" (the GUI keys a green/amber
  result dialog on it; consolidators leave it None), and the workbook's
  Summary carries the same verdict as a big banner cell right under the
  title (B3, or B4 under the manual-calc F9 banner) — a LIVE formula in the
  formulas flavor (CF green/red keyed on the ✓/✗ first character), a
  literal in the values flavor. Match ⟺ zero differing cells AND zero
  one-sided rows.
  The TSMIS-vs-TSN flavor takes a TSMIS and a TSN Highway Log — **either two
  per-route workbooks or two consolidated ones** (`Route` + 31 columns; shapes
  auto-detected, mixed shapes rejected with guidance) — and writes a
  discrepancy workbook — Summary / Comparison / **Only in TSMIS / Only in
  TSN** (every one-sided row pulled onto its own tab in union order, fields
  pulled live from that system's data sheet; consolidated mode adds a
  "Missing from <other>" column — "entire route" rows tinted — so
  wholly-missing routes are impossible to overlook, v0.9.0) / TSMIS / TSN,
  plus a **Routes sheet in consolidated mode** (route coverage:
  Both/TSMIS-only/TSN-only with live per-route row/diff counts; the Summary
  gains a ROUTE COVERAGE section and the run log lists the missing routes).
  NOTE: one-sided routes' rows have ALWAYS been in the Comparison sheet
  (yellow/blue, via `_union_keys`' single-side emit) — the tabs exist
  because 65k-row sheets buried them. The Summary also carries a live
  **SELF-CHECK section** (v0.9.0): each headline number recomputed a second
  independent way (status totals vs union count, MATCH-hit counts, Only-in
  tab row counts, per-field diff sums, Routes-sheet row sums) — every row
  must read OK after F9; a CHECK means formulas no longer point at the right
  rows. **Trust aids for formula skeptics (v0.9.0):** the TSMIS/TSN Row
  numbers on Comparison + Only-in sheets are HYPERLINK jumps that target the
  source row as a WHOLE-ROW reference ("57:57"), so Excel SELECTS the entire
  row on arrival — a temporary highlight that clears on the next click —
  without scrolling; a bounded range (A57:AH57) made Excel scroll to the
  range's RIGHT edge (COM-measured on real Excel) — don't regress to one
  (`_row_link`: the MATCH is computed three times — range start/end +
  display — so the cell value stays NUMERIC; the COUNT self-check depends
  on that); each data-sheet row
  carries a "Comparison row" link back in its LEADING column — column A, so
  Route/Location/fields and the key helper all sit one column right of the
  input layout (literal target — the row universe is build-time-static, only
  values are live); and a **Spot Check sheet** audits
  one location at a time — raw stored values from both sheets next to an
  independently recomputed per-field verdict (same TRIM/Med-Wid rules,
  never reading the Comparison's answer) with an Agree? OK/CHECK column that
  stays meaningful on one-sided rows (verdict column echoes the status,
  tinted, plus a loud callout), a TSMIS-first ≠ legend, and a bold press-F9
  reminder in consolidated mode. **Two output flavors (v0.9.0):**
  `compare(..., mode="formulas"|"values"|"both")` — the Compare tab has two
  checkboxes (both ticked by default; ≥1 required). "values" writes the SAME
  sheets/CF/links but the bulk as plain computed results via the
  `_count_diffs`/`_field_value` mirror (so the flavors can't disagree):
  opens instantly, automatic calc, no F9 banner, ~⅓ the size; only the Spot
  Check sheet and SELF-CHECK rows stay live (they recount the literal
  sheets). "both" writes the picked name (formulas) + `<name> (values).xlsx`.
  In the formulas flavor, EVERY number is a live
  Excel formula (lookup keys, statuses, per-field diffs, summary counts):
  edit a value on a data sheet and the report recalculates. Consolidated
  workbooks ship in **manual calculation mode** (`calcPr calcMode="manual"`,
  calcOnSave off): ~2M live formulas would otherwise recalc for minutes on
  open and after every edit — instead the file opens instantly showing
  blank/0 and the user presses F9 once (Summary note + run log explain;
  per-route files stay automatic). The workbook is written in openpyxl's STREAMING (write_only)
  mode — the consolidated comparison carries ~2M formula cells, which the
  normal in-memory mode cannot save in reasonable time (50+ min vs ~3 min;
  same reason the consolidators stream). Matched cells show the matched
  value; differing cells show "tsmis ≠ tsn" in red (diff detection keys on
  the " ≠ " marker — formulas, conditional formatting and COUNTIFs all rely
  on it). Rows are keyed on (Route +) Location + occurrence; the union is a
  diff-style document-order merge PER ROUTE with first-position dedupe (a key
  can sit in both files at different sequence positions — TSMIS prints some
  postmiles out of order; per-route alignment keeps difflib fast on 50k+
  rows). Column geometry for both shapes lives in compare_core's `_Layout`. The per-route
  format is locked to the approved Route-1 sample and verified cell-for-cell
  against it (same union order, same counts Excel cached: 299 both / 18 / 69 /
  221 diff rows / 971 diff cells) with intended changes — matched values
  shown instead of blank, row numbers rendered as clickable links, and the
  additive Spot Check / Only-in tabs. Med Wid compares after zero-pad
  normalization (TSMIS `0Z` = TSN `00Z`).

## Two Run Modes, One Core

The export engine is **console-free** and backs both:
- **`.bat` console flow** (development + fallback) — see *User Workflow*.
- **Packaged GUI** — a pywebview (**Edge WebView2**) window rendering
  `scripts/ui/` (plain HTML/CSS/JS, no build step / no npm): `gui_main.py`
  (entry) → `gui_api.py` (js_api bridge + state + queue pump) →
  `gui_worker.py` (worker threads, unchanged across the Tk→WebView rewrite).

Only `cli.py` and `gui_*.py` touch `print`/`input`/`msvcrt`/the window. Core code
(`common.py`, `exporter.py`, consolidator cores) reports via the `Events` sink
(`scripts/events.py`) and raises exceptions — never `print`/`input`/`sys.exit`.
User-facing strings from the core must be **UI-neutral** (no ".bat" names, no
"this window" / "menu option N" — that guidance lives in the driver).

**Threading:** Playwright's sync API is thread-affine. All browser work runs on
worker threads, which post `(kind, payload)` messages to a `queue.Queue` (the
protocol is documented in `gui_worker.py`). `gui_api` pumps that queue into its
state machine, and ONE sender thread delivers ordered JSON event batches to JS
via `evaluate_js` → `window.__tsmis.dispatch()`; JS calls back through
`window.pywebview.api.<method>()` (the public `GuiApi` methods). In fast mode
each worker owns its own Playwright/browser/context.

**UI layering:** Python owns app state (auth, task, checks, days) and pushes
full snapshots; `app.js` owns presentation + form fields and NEVER invents log
lines — everything shown in the log pane originates in Python so the `tsmis.ui`
file-log mirror stays complete. A built-in mock API can drive the whole UI,
including simulated runs, without launching the app — **opt-in only**: open
`scripts/ui/index.html#mock` in a browser (that's how the layout is
screenshot-tested). The mock must never auto-start: a cold WebView2 can inject
the real bridge later than any timeout, and a silent mock fallback would show
convincing fake exports inside the real app. Without `#mock`, the page waits
for the bridge and shows a fatal banner if it never arrives.

## The App

The product is a **portable single-folder Windows desktop app** (bundled Python +
deps + WebView2 GUI; no installer, no Python needed on target): non-technical
staff unzip one folder and double-click the `.exe`. The `.bat` console flow
(below) is retained as a development and fallback path, and runs the same core
engine.

**Design decisions (don't relitigate without reason):**
- **Packaging:** PyInstaller **onefolder**, shipped as a portable zip (no installer).
- **UI stack (v0.8.0): pywebview + Edge WebView2 rendering vanilla HTML/CSS/JS.**
  Replaced the original Tkinter window: Tk could neither match the approved
  design (the `tsmis-exporter-ui-demo` Lovable mock — Windows-11 look, dark
  titlebar, two-column layout) nor stop cutting off on small screens; a web
  layout solves both (responsive, stacks + scrolls below ~980px; theme =
  System/Light/Dark header toggle persisted in localStorage and resolved to
  an effective `html[data-theme]` before first paint). WebView2 is a safe
  dependency here: it ships with
  Windows 10/11 and evergreen Edge — the same Edge this tool already requires.
  No frontend framework/build step on purpose (static files ship in the
  bundle; end-user setup stays global-pip). `webview.start(gui="edgechromium")`
  is forced so a missing runtime fails loudly (clear message box) instead of
  silently degrading to MSHTML. tkinter is excluded from the bundle.
  **THREE pywebview traps, all hit during the rewrite:**
  1. pywebview detects "is `start()` already running" via the main thread's
     NAME — `logging_setup` must never rename the main thread (it tags
     `[main]` via a logging Filter instead); renaming it makes
     `create_window` block forever running the GUI loop itself.
  2. **Never do work in window-event handlers** (`shown` etc.): pywebview
     fires them on the WinForms STA thread while WebView2 is still
     initializing asynchronously on it — a handler that blocks (the original
     icon-setter loaded a .NET assembly) starves the message pump and
     INTERMITTENTLY deadlocks the window ("Not responding" + WER AppHangB1
     before the page loads; ~6/8 launches at its worst, machine-state
     dependent). The icon is set from a worker thread with pure Win32
     (`FindWindowW` + `WM_SETICON`); only `closed` (fires after the loop
     ends) is subscribed.
  3. `faulthandler` is disabled in the GUI process
     (`setup_logging(enable_faulthandler=False)`): its Windows handler sees
     the CLR's routine first-chance access violations (pythonnet) and dumps
     all threads mid-exception-dispatch — observed wedging init and spamming
     `crash.log` with dumps from healthy-looking runs. Console entry points
     never load the CLR and keep faulthandler's hard-crash dumps.
  4. **Mark-of-the-Web kills the CLR** (field failure, v0.8.0's first
     download): extracting the release zip without Unblock tags every file
     with a `Zone.Identifier` stream and .NET Framework refuses to load
     tagged assemblies → instant "Failed to resolve Python.Runtime.Loader.
     Initialize". Dev runs and CI never go through a downloaded zip, so ONLY
     releases hit it. `gui_main._unblock_dotnet_assemblies()` strips the
     streams from the bundled .NET trees at startup, before the CLR loads;
     the fatal box also explains the manual Unblock for read-only installs.
     Repro for testing: `Set-Content <dll> -Stream Zone.Identifier` with
     `ZoneId=3` on `_internal\pythonnet\**`.
- **Browser channels — three release variants, one codebase:**
  - **`*-win64.zip` (default build):** no bundled browser. Drives the machine's
    installed Edge (then Chrome) via `channel="msedge"`/`"chrome"`. Edge is
    Chromium, ships with Windows, supports `page.pdf()` + downloads. ~148 MB.
  - **`*-win64-with-browser.zip` (`build.ps1 -BundleChromium`):** additionally
    ships Playwright's own Chromium in `_internal\ms-playwright`; `paths.py`
    points `PLAYWRIGHT_BROWSERS_PATH` at it and `common.py` lists **Built-in
    Chromium** as the *default* channel (Edge/Chrome stay in the dropdown).
  - **`*-batch-source.zip`:** the `.bat` console flow; `1. setup…bat` pip-installs
    the libs **and** runs `playwright install chromium --no-shell`.
  The `chromium` channel only appears when a Playwright Chromium is actually
  present (`common._chromium_available()`): for **packaged** builds that means
  the bundle's own `_internal\ms-playwright`, an explicit
  `PLAYWRIGHT_BROWSERS_PATH`, **or the Settings-tab download** (v0.10.0:
  `paths.DOWNLOADED_BROWSERS_DIR` = `data\ms-playwright` — user data, so it
  survives one-click updates; `gui_worker.ChromiumWorker` drives the BUNDLED
  Playwright Node driver like `playwright install chromium --no-shell` with
  PLAYWRIGHT_BROWSERS_PATH aimed there — works frozen, streams progress to
  the log, cancellable, no console window; delete rmtree's ONLY that folder,
  never the bundle's. Channels are probed at startup, so download/delete
  says "restart the app"). The machine's global Playwright cache is
  deliberately ignored so the default build defaults to Edge even on a
  dev PC; dev/`.bat` runs use the default cache (where setup downloads it),
  and a Settings-tab download wins over the cache in dev too.
  `channel="chromium"` runs the full browser in new-headless mode — one binary
  for headed sign-in and headless exports (no headless shell needed).
- **Data location (option A):** the packaged app writes `output/`, auth token,
  logs, and config **next to the `.exe`**, falling back to
  `%LOCALAPPDATA%\TSMIS Exporter` if read-only. See `scripts/paths.py`.
- **WebView2 profile:** the GUI window uses a persistent app-owned user-data
  folder (`paths.WEBVIEW_PROFILE_DIR`, `data\webview2`) via
  `webview.start(private_mode=False, storage_path=...)`. pywebview's default
  private mode writes a fresh Chromium profile into `%TEMP%` on EVERY launch
  (tens of MB, leaked when the process is killed) and cold-starts the browser
  each time; one stable folder avoids both, and the UI stores nothing
  sensitive in it.

**Pinned versions (`version.py` / `requirements*.txt`):** `playwright==1.60.0`
(pins the bundled **Node driver** only — no Chromium ships), `pdfplumber==0.11.9`
(→ `pdfminer.six==20251230`), `openpyxl==3.1.5`, `pywebview==6.2.1` (→
`pythonnet`/`clr_loader` on Windows), `pyinstaller==6.20.0`,
`pyinstaller-hooks-contrib==2026.5`. Built/tested on **Python 3.11**. The export
engine is live-verified against TSMIS.

> **✅ RESOLVED (v0.5.0) — Edge sign-in in the managed Caltrans environment.**
> Managed Edge relaunches itself into the work profile mid-Azure-AD-login, killing
> the Playwright window (`TargetClosedError` on `storage_state`) — Edge's
> org-managed behavior, with zero interaction from us. Fixed two ways:
> 1. **Persistent-profile Edge recapture** (`login.py` / `LoginWorker`): sign-in
>    opens Edge on a durable app-owned profile (`EDGE_LOGIN_PROFILE_DIR`) with a
>    CDP port; after the user finishes, the session is captured from the live
>    context, else by CDP re-attach to the relaunched Edge, else by reopening the
>    profile tree headless and reading the cookies back. Chrome remains the
>    fallback when nothing was captured.
> 2. **Built-in Chromium** (preferred when present): unmanaged, so org policy
>    can't touch the sign-in window at all. Ships in the with-browser release
>    variant and is downloaded by the `.bat` setup. See *Browser channels* below.
> (Historical: removing mid-login polling, `--edge-skip-compat-layer-relaunch`,
> and InPrivate did NOT help; v0.4.2's "default sign-in to Chrome" regressed
> Chrome too and was rolled back.)

## `.bat` Console Flow (dev / fallback)

The shipped GUI replaces steps 2–4 with buttons; these scripts run the same core
and are kept for development and as a fallback.

1. **`1. setup (one time).bat`** — `pip install -r requirements.txt`, then
   `playwright install chromium --no-shell` (the Built-in Chromium; on download
   failure it warns and the tool falls back to the machine's Edge/Chrome).
2. **`2. login (update login).bat`** — tries the silent Edge device sign-in
   first (no window, no typing — managed Caltrans PCs); else opens a visible
   browser (Built-in Chromium when present, else the persistent-profile Edge
   flow with Chrome fallback); user does SSO+MFA, then confirms to save the
   session to `scripts/tsmis_auth.json` (shared by all exports). Login is
   **validated before saving** (a real TSMIS login must be detected), so
   clicking "finished" without signing in won't save a junk session.
3. **`3. run_export (main script).bat`** — shows a menu (`1`–`4` single report,
   `A` = several/all → `export_multi.py`, `Q` quit), then prompts for routes
   (Enter = all; or `5, 99, 101` — any casing/padding, suffixes like `101U`
   ok), then runs headlessly. A missing saved session is just a note — the
   engine tries the automatic device sign-in itself.
4. **`4. consolidate (combine reports).bat`** — pick a report type (and, when
   several dated export folders exist, which day — Enter = newest, or set
   `TSMIS_DAY`), combine that day's per-route exports into one workbook in
   `output/<date>/consolidated/` (no auth check). Option 5 = TSN Highway Log
   (reads `input/tsn_highway_log/*.pdf`; the day prompt is ignored).
5. **`5. fast export (experimental).bat`** — asks worker count (sets
   `TSMIS_FAST_WORKERS`), then the usual menu.

## Repository Layout

```
1.–5. *.bat                       # setup / login / export / consolidate / fast export
run app (GUI preview).bat         # dev launcher for the GUI
requirements.txt / -build.txt     # pinned runtime / build deps
version.py                        # app name/version + pinned Playwright (Node driver)
.github/workflows/release.yml     # tag push (or manual dispatch) -> self-test gate ->
                                  #   builds + publishes the three release zips
scripts/
  paths.py            # frozen-aware paths (option A): DATA_ROOT, OUTPUT_ROOT, AUTH, LOG_DIR, FAILURES_DIR, CONFIG_FILE;
                      #   run folders: run_folder_name/output_run_dir/parse_run_folder/list_output_days/resolve_day_choice
  logging_setup.py    # rotating file log under LOG_DIR (every entry point calls it); set_debug_logging (Settings toggle)
  settings.py         # persisted user settings (config.json): timeout/worker overrides, debug toggles
  common.py           # site config (get_url/set_site: SSOR|ARS × prod|test|dev), ROUTES, timeouts (+ settings-aware
                      #   *_timeout_ms() accessors), auth+nav helpers, maybe_screenshot (live preview seam),
                      #   AuthError/RunCancelled/PreflightError/ReportError/BrowserNotFoundError, launch_browser,
                      #   set_preferred_channel, check_browsers, preflight, parse_routes/normalize_route
  events.py           # Events sink (+ worker_no / on_status / screenshot seam) + RunResult + ConsolidateResult
  exporter.py         # the one per-route loop: run_export(spec, events), ReportSpec, save_pdf_letter / save_via_export_button, _recover, _retry_failed_routes
  exporter_parallel.py# EXPERIMENTAL fast mode: N browsers off a shared queue; reuses exporter.py internals
  run_report.py       # per-route outcome CSV (auto-saved each run, site-tagged; + multi)
  cli.py              # console adapters: run_cli / run_cli_multi / run_consolidate_cli
  login.py            # writes the auth file (headed browser)
  reports.py          # SINGLE registry: EXPORT_REPORTS + CONSOLIDATE_REPORTS + COMPARE_REPORTS (GUI + export_multi read it)
  updater.py          # one-click self-update (GUI only): GitHub release check/download/stage + PowerShell swap helper
  export_*.py         # thin (~30 lines): a ReportSpec + run_cli; export_multi.py = several/all
  consolidate_xlsx_base.py    # shared XLSX consolidator core
  consolidate_ramp_summary.py # standalone (parses PDFs)
  consolidate_{ramp_detail,highway_sequence,highway_log}.py  # thin wrappers over the base
  consolidate_tsn_highway_log.py  # TSN district PDFs -> TSMIS-format XLSX + combined (input/ folder)
  compare_core.py     # THE discrepancy-workbook engine (schema-parameterized; regression-locked — see Compare tab notes)
  compare_highway_log.py      # TSMIS-vs-TSN Highway Log: schema + loaders over compare_core ("files" kind)
  compare_env.py      # cross-environment comparison: two run folders, all four reports ("folders" kind)
  gui_main.py / gui_api.py / gui_worker.py   # GUI entry / js_api bridge + state / worker threads
  ui/                 # the GUI itself: index.html + app.css + app.js (vanilla; design
                      #   tokens ported from the approved Lovable demo; mock API for browser preview)
build/
  build.ps1           # one-command onefolder build (-SelfTest = headless verify gate;
                      #   -BundleChromium = ship the Built-in Chromium inside the bundle)
  prune_bundle.ps1    # strip to runtime-only files + DLP guard (run by build.ps1)
  app.spec            # PyInstaller spec (Node driver + pdf/excel; excludes image libs; version-info + icon + manifest; no browser)
  release_notes.md    # body of the GitHub release (which zip to pick + highlights)
  app.ico / app.manifest / full_smoke.py / dist_readme.txt / .venv/ (git-ignored)
dist/                 # build output: dist/TSMIS Exporter/ (git-ignored)
output/               # contents git-ignored. Live layout: "<YYYY-MM-DD> <src>-<env>"/{ramp_summary,
  ...               #   ramp_detail,highway_sequence,highway_log,consolidated}/ + run_reports/ + comparisons/
                      #   (the tracked flat .gitkeep stubs are the legacy pre-dated layout; bare-date
                      #   folders from v0.7–0.9 read as ssor-prod)
```

`scripts/tsmis_auth.json` is git-ignored — treat it as a credential. Don't commit
generated `output/` files (only the `.gitkeep` stubs), build artifacts
(`build/.venv`, `dist/`), or `.claude/` permission state.

## Architecture Notes

- **One shared loop, per-report differences in a `ReportSpec`.** Each report's
  differences (label, output filename, post-Generate `wait_js`, `is_empty` check,
  `save` strategy) live in its `ReportSpec`; the proven loop, recovery, and
  skip/cancel logic live once in `exporter.py`. To fix one report's behavior, edit
  only its `ReportSpec`.
- **Single report registry** (`reports.py`) feeds both the GUI checkboxes and
  `export_multi`, so the list can't drift. (The `.bat` menus are hand-edited text.)
- **Route selection** is per-run plumbing into `run_export(..., routes=ROUTES)`.
  `common.parse_routes` is the one parser. Console: `_resolve_routes_console`
  (Enter/`all`/EOF = all; honors `TSMIS_ROUTES`). GUI: a Routes entry + `Choose…`
  picker. To change the route universe permanently, edit `ROUTES` in `common.py`.
- **Multi-report runs** run each selected `ReportSpec` in turn through the same
  engine (so at most `workers` browsers are ever open), each with its own
  browser/preflight/run-report CSV.

## Key Behaviors

- **Run folders (v0.10.0; replaces bare dated outputs):** every run writes into
  `output/<YYYY-MM-DD src-env>/<report>/` (`paths.output_run_dir`, src/env from
  `common.get_site()` at run start), so each day's exports live in their own
  folder AND different source/environment combinations never mix — the folder
  name says exactly what's inside (this labeling is what the cross-environment
  comparison keys on). Legacy bare-date folders read as **ssor-prod**
  (`paths.parse_run_folder`). The consolidators take the run-folder NAME as
  their `day` argument (opaque to them): `day=None` means the **newest** run
  folder (`paths.latest_output_day`), the GUI picker lists run folders, the
  console prompts (Enter = newest; `TSMIS_DAY` accepts a folder name or a bare
  date — `paths.resolve_day_choice` picks that date's newest run folder), and
  the combined workbook lands in `output/<run>/consolidated/`. When NO run
  folders exist the consolidators fall back to the legacy flat
  `output/<report>/` layout, so pre-0.7 exports stay consolidatable.
- **Resume / idempotency:** `run_export` skips a route whose output file already
  exists **in today's run folder for the active src/env**. Delete a file to
  force re-download; a new day (or a different environment) always starts a
  fresh folder (yesterday's files never block today's run).
- **Live browser status + previews (v0.10.0, GUI):** the engines emit a
  one-line per-browser status through `events.on_status(worker_no, text)`
  (phase changes + a ~5 s heartbeat with elapsed time inside
  `wait_with_skip_option`), shown as one row per browser in the progress card.
  Each row's **Preview** button requests a screenshot: GUI →
  `ExportWorker.request_screenshot(worker_no)` sets a flag the worker drains
  at its next safe poll point via `common.maybe_screenshot` (Playwright is
  thread-affine — only the owning thread may touch the page; a blocking
  download wait answers at the next route), and the JPEG comes back as a
  `("preview_shot", (worker, b64, note, url))` message → a closeable modal
  showing the page's address over the screenshot (likewise the Verify-env
  modal; `common.page_url_for_display` strips the URL fragment — the OAuth
  token rides in the hash and must never reach the screen). The Events seam
  (`worker_no`, `on_status`, `screenshot_wanted`, `on_screenshot`) is no-op
  in the console flow.
- **Settings tab (v0.10.0, GUI):** persisted via `settings.py` →
  `data/config.json`. Timeout/worker overrides are read at RUN time through
  `common.*_timeout_ms()` accessors / `exporter_parallel.default_worker_count()`
  (next run picks them up; env vars still win where one exists); verbose
  logging applies live (`logging_setup.set_debug_logging`); DevTools applies
  next launch. **Per-env TSMIS addresses** (six editable rows; custom ones
  chip-marked; clearing restores the default — see *Supported Reports*) and
  the **Built-in Chromium download/remove** (see *Browser channels*) live
  here too. Also: support-bundle zip (logs + run reports + manifest —
  NEVER the auth file/profiles), forget-saved-login, open-folder shortcuts,
  and **Delete all reports** (`gui_worker.reset_targets`/`ResetWorker`):
  removes run folders, legacy flat report folders, consolidated/comparisons,
  run_reports, failure dumps, TSN outputs (+ optionally the TSN input PDFs)
  after a confirm dialog listing the concrete targets with file count + size
  (`reset_preview`); logs, login, Edge profile and settings are NEVER
  deleted; Excel-locked files are reported, not silently skipped.
- **Skip a slow route:** console `S` key / GUI Skip button →
  `events.should_skip()`. After `SKIP_PROMPT_AFTER_MS` a "still working" line
  appears and the skip hatch opens; skipped routes are recorded and the form
  re-armed. (Skip is disabled during the parallel phase — use Cancel.)
- **Cancel:** stops the **current** export immediately (not just between routes).
  `wait_with_skip_option` checks `is_cancelled()` ~every 5 s and raises
  `RunCancelled` mid-wait; engines treat it as a clean stop (not a failure) and
  return a partial `RunResult`. Re-running resumes.
- **End-of-run retry pass** (`_retry_failed_routes`): after the main run, `failed`
  routes get one slow, **serial** retry (`RETRY_REPORT_TIMEOUT_MS`, 15 min). In
  fast mode a single fresh browser retries stragglers serially. Only `failed`
  routes (not skipped/empty) are retried; bookkeeping keeps one CSV row per route;
  the run report is written **after** the retry.
- **In-loop auto-retry:** a transient (non-timeout) route error retries once after
  `_recover()` (`RETRY_COUNT=1`). A hard timeout is not retried in-loop.
- **Site-error fast-fail:** a fatal per-route TSMIS error (`#rampResults` gets an
  `error` class) is detected via `common.ERROR_JS` and raised as `ReportError` —
  recorded `failed` in seconds (with message + screenshot) instead of burning the
  full timeout.
- **Run report:** every route's outcome (`saved`/`empty`/`skipped`/`failed`/
  `exists`) is recorded and auto-saved to `output/run_reports/<report>_run_<ts>.csv`.
  GUI "Save run report…" copies it (combined CSV when several ran).
- **One-click update (v0.9.0, GUI only — `updater.py`):** at launch (quiet
  unless something is found) and on clicking the version chip, the app asks
  the GitHub Releases API for the latest tag and compares it to `version.py`
  (public repo, stdlib urllib; TLS trusts the **Windows cert store** so
  corporate TLS inspection works — never switch this to requests/certifi).
  If newer, a title-bar pill offers **Update** → downloads the
  variant-matching zip (`-with-browser` when `_internal\ms-playwright` ships;
  same probe as `paths.py`) into `data\update\`, extracts + verifies it, then
  **Restart to update** launches the STAGED NEW EXE in swap mode
  (`updater.SWAP_FLAG` / `run_swap_mode`; gui_main branches into it FIRST,
  before logging/paths/CLR — the process runs from the staged tree, so
  normal path resolution would aim at the wrong folder) and exits: the swap
  process waits on the app's PID, renames old bundle pieces
  (exe/`_internal`/`Start Here.txt`) to `*.old`, **copies** itself into
  place (it cannot move the tree it runs from), relaunches, and **rolls
  back** if any step fails (`LOG_DIR\update_helper.log`); user data folders
  are never in the staged tree. A swap process that dies instantly is
  detected BEFORE the window closes (UpdateError; the app stays open on the
  old version). **Why an exe, not a script (v0.10.1, field failure):**
  v0.9.0 ran a PowerShell helper from `%TEMP%`; locked-down PCs that block
  PowerShell entirely killed it silently — the app closed, nothing swapped,
  and the staged download just sat in `data\update`. The swap-mode design
  needs only "exes run from user folders", which is proven anywhere the app
  itself runs. `updater.cleanup_leftovers()` (gui_main
  startup, before the CLR loads) removes `*.old` + stale staging — including
  a staged-but-never-applied download, deliberately, so stale versions are
  re-offered fresh. In-app downloads never carry the Mark-of-the-Web
  (zipfile writes raw bytes), so the v0.8.1 CLR failure can't happen on this
  path. Read-only installs (`update_support()` = "link": DATA_ROOT fell back
  to %LOCALAPPDATA%) get a pill that opens the release page instead; dev runs
  skip the check ("off"). Restart is gated on no task running; the download
  isn't. Update state is pushed in every snapshot (`update:{phase,…}`);
  worker protocol message is `("update_status", dict)`. `full_smoke.py` stubs
  `UpdateWorker` so the release gate never touches the network.

## Timeouts (`scripts/common.py`)

| Constant | Default | Purpose |
|---|---|---|
| `REPORT_TIMEOUT_MS` | 360_000 (6 min) | Per-route ceiling, sequential flow |
| `FAST_REPORT_TIMEOUT_MS` | 600_000 (10 min) | Per-route ceiling, fast mode (server under load) |
| `RETRY_REPORT_TIMEOUT_MS` | 900_000 (15 min) | Per-route ceiling, end-of-run retry pass |
| `SKIP_PROMPT_AFTER_MS` | 60_000 (1 min) | When the "still working" status + skip hatch open |
| `COUNTY_ENABLE_TIMEOUT_MS` | 60_000 (60 s) | Max wait for the county dropdown to enable |
| `RETRY_COUNT` | 1 | In-loop retries after a transient (non-timeout) failure |

Increase these if the TSMIS server is slow. The constants are the DEFAULTS;
since v0.10.0 the GUI's Settings tab overrides the four ceilings via
`settings.py`, and engines read them at run time through the accessor
functions (`report_timeout_ms()` etc.) — when editing engine code, call the
accessors, don't import the constants.

## Fast Mode (experimental, `exporter_parallel.py`)

N headless browsers restore the **same** session and pull routes off a shared
queue. Additive — the sequential engine is untouched and remains the default. Same
contract (merged `RunResult`, same errors, honors cancel, resumes, auto-saves CSV;
one preflight before launching N browsers). A crashed worker never silently drops
routes — others keep draining, and unrecorded routes are reconciled as `failed`.

`DEFAULT_WORKERS=3`, `MAX_WORKERS=30`. The limit is the **client PC, not the
server** (~0.5 GB RAM/worker): 3 = safe (~2.5–3× faster), 8–12 = big speedup on a
healthy multi-core PC, 30 = hard cap. Turn on via `5. fast export…bat`
(`TSMIS_FAST_WORKERS`) or the GUI "⚡ Fast mode" checkbox + spinner.
`run_cli`/`run_cli_multi` route to the parallel engine when workers > 1.

## Auth / Session

- **Signed-in detection** (`common.is_logged_in`): the report page ships its
  whole form in static HTML even when signed out, and the app **never shows a
  signed-out page** — `initAuth()` with no token immediately self-redirects
  into the portal OAuth flow (same tab, `response_type=token`; the token comes
  back in the URL hash and lives **only in page memory**, ~120 min TTL — so a
  storage_state never carries the app session, every fresh navigation re-runs
  the silent round-trip, and `_recover()` re-mints expired tokens mid-run).
  The only trustworthy signal is the app's post-auth UI: any of
  `#modeSelector`/`#controlsGrid`/`#generateRow`/`#appForm`/`#versionCtrl`
  visible (ARS: immediately; SSOR: after the TSMIS_HI group check) with
  `#accessDenied`/`#loginPrompt` hidden (`common._SIGNED_IN_JS`; visibility via
  `Element.checkVisibility()` — offsetParent is wrong for fixed-position
  ancestors). Sign-in gate failures dump `auth_fail_<ts>.png/.html` to
  `FAILURES_DIR` plus a per-signal snapshot to the log
  (`common.require_signed_in` / `dump_auth_failure`). `navigate_with_auth`
  (60 s budget, state-change breadcrumbs in the log) drives the portal
  sign-in page's IdP hop **directly** — `goto` of the button's `data-url` +
  the page's `oauth_state` — then polls for the signed-in state. THREE traps,
  all hit in the field: (1) the portal keeps **no session cookie**, so every
  recovery is a full silent SAML round-trip; (2) the app's `CONFIG` is a
  top-level `const` — a lexical global, NOT `window.CONFIG` — readable only by
  bare identifier in a try/catch (`_CONFIG_JS`); (3) reloading the page
  destroys the memory-only token, so the wrong-env/src check
  (`_site_params_ok`) runs INSIDE the sign-in loop (one corrective reload,
  then a fresh sign-in pass) and NEVER after success — and host checks must
  parse the hostname (`_page_host`), because the portal's authorize URL
  contains the app host inside its `redirect_uri` parameter.
- **Silent device sign-in** (`common.try_device_sso_login` →
  `open_edge_device_context`) is tried first: it reopens the app-owned
  **persistent Edge sign-in profile** (`EDGE_LOGIN_PROFILE_DIR`) headless and
  clicks "Caltrans Azure AD" (via the same `navigate_with_auth` the engine
  uses) — the **one-click Windows sign-in lives in that profile**; a fresh
  cookie-free Edge context does NOT get it, and Chrome never does (manual
  credentials there). Each known profile dir is tried (managed Edge may have
  moved the session into a work profile). The profile is **primed by the headed
  Edge login** — first-ever use still needs one headed sign-in. If the minted
  state passes the portability check it is saved as the normal auth file; if
  sign-in worked but the state is device-bound, **nothing is saved** and the
  app enters **device sign-in mode** (GUI message `login_device_ok`,
  `App._device_ok`): exports don't need a file — each run signs itself in live
  the same way.
- **Engines no longer hard-require the auth file.** They log a notice
  (`has_valid_auth`) instead of raising, and `new_authed_browser` restores the
  saved session when one is valid, else opens the persistent Edge profile via
  `open_edge_device_context` (the context doubles as the browser handle;
  `.close()` shuts the persistent browser down); `_recover()` re-auths the
  same way mid-run. If sign-in still fails, `AuthError` is raised as before.
  The profile can only be open in ONE browser at a time, so **device mode caps
  fast mode to 1 worker** (a saved login is required for real parallelism — the
  GUI greys the Fast-mode checkbox out without one and says why).
  The `.bat` export menus print a note instead of exiting when the file is
  missing; the GUI offers to start anyway.
- **Local Network Access:** the TSMIS page pulls report data from an intranet
  host, which Chromium's LNA checks would block behind a permission prompt no
  one can click headless. Every automated context launches with
  `common._LNA_ARGS` and pre-grants `local-network-access`
  (`common._new_app_context`) — engine contexts, the device sign-in, and the
  portability probe alike. The **headed sign-in windows need it too**
  (`LOGIN_BROWSER_ARGS` + `new_login_context`, used by `login.py` and
  `gui_worker.LoginWorker`): without the grant Chrome re-prompts on every
  sign-in, and an unanswered prompt blocks the signed-in UI — so the login is
  never detected and no session is saved (field bug, fixed v0.8.0; managed
  Edge avoided it via enterprise policy, which is why only Chrome showed it).
- **Headed sign-in browser order** (`login.py` console / `gui_worker.LoginWorker`)
  honors the user's pick first (`get_preferred_channel()` — the GUI Browser
  dropdown / `TSMIS_BROWSER_CHANNEL`; picking Chrome goes straight to Chrome and
  skips the silent attempt). With no pick, after the silent attempt:
  1. **Built-in Chromium** when present — a normal headed sign-in; unmanaged, so
     org policy can't kill the window.
  2. **Persistent-profile Edge recapture** — Edge opens on the app-owned
     `EDGE_LOGIN_PROFILE_DIR` with a CDP port; capture from the live context,
     else `capture_edge_login_state_over_cdp` (re-attach to the relaunched
     managed Edge), else `capture_edge_login_state_from_profiles` (reopen the
     profile tree headless and read the session off disk).
  3. **Chrome fallback**, then any `launch_browser`-resolvable browser.
- **Edge captures are portability-validated before saving**
  (`common.storage_state_is_portable`): the state is restored into a fresh
  headless context and must actually log in, exactly as the engine will use it.
  Managed Edge work profiles can sign in via the Windows device broker (PRT) —
  `amr: ["wia"]`, an `ESTSAUTH` stub with no payload — leaving cookies that look
  captured but can't log in anywhere else; such captures are rejected with a
  clear message and the flow falls back to another browser instead of saving a
  dud auth file.
- The auth file is written only **after** a real login is detected
  (`is_logged_in` on any page — SSO can land in a popup). The GUI `LoginWorker`
  also watches the window closing, but the reliable signal is **no open tabs
  remain** (the SSO flow always keeps ≥1 tab) — it does NOT treat the original
  page closing, a connection blip, or a single transient `ctx.cookies()` error
  as "closed" (that caused false "cancelled"). On any non-save outcome no file
  is written, so a prior valid session is preserved.
- `require_valid_auth()` still validates the file shape (exists, valid JSON,
  `cookies`/`origins` lists) and backs `has_valid_auth()` / the GUI status dot.
  On `AuthError` from a run, `cli.py` clears the stale file and guides re-login;
  the GUI shows a re-login dialog.

## Build & Packaging (portable onefolder)

From the repo root: `powershell -ExecutionPolicy Bypass -File build\build.ps1`
→ windowed `dist\TSMIS Exporter\` (~148 MB; double-click `TSMIS Exporter.exe`).
Add `-BundleChromium` for the with-browser variant (downloads Playwright's
Chromium into `_internal\ms-playwright` before the prune). Add `-SelfTest` for a
headless console build that **builds AND runs** `full_smoke.py` over the pruned
frozen bundle (browser pdf+download, pdfplumber, openpyxl, GUI) — a real release
gate (`-SelfTest -BundleChromium` gates the bundled-Chromium path).

`build.ps1`: (1) creates `build\.venv` from `requirements-build.txt`; (2) runs
PyInstaller with `app.spec`, entry `scripts\gui_main.py`, windowed, copies
`dist_readme.txt` in as "Start Here.txt"; (2b) with `-BundleChromium`, runs
`playwright install chromium --no-shell` with `PLAYWRIGHT_BROWSERS_PATH` aimed
inside the bundle; (3) runs `prune_bundle.ps1`; (4) with `-SelfTest`, runs the
self-test exe and fails on nonzero exit.

**Releasing:** push a `v*` tag (or run the `release` workflow manually with a
tag input — it creates the tag) and `.github/workflows/release.yml` runs both
self-test gates on `windows-latest`, builds the three zips (`win64`,
`win64-with-browser`, `batch-source` via `git archive`), and publishes the
GitHub release with `build/release_notes.md` as the body. Bump `version.py`
first; nothing is published if any gate fails.

`app.spec` highlights:
- `collect_all('playwright')` + Playwright's hooks → the Node driver ships. **No
  browser bundled** (no `ms-playwright` data entry).
- `collect_all('webview'/'pythonnet'/'clr_loader')` — the GUI shell. Their package
  DATA is load-bearing when frozen: `webview/lib` (WebView2 .NET assemblies),
  `pythonnet/runtime` (Python.Runtime.dll + netstandard facades),
  `clr_loader/ffi/dlls` (ClrLoader natives). `hiddenimports += ['clr']`.
- `scripts/ui/*` ships as data files under `_internal/ui/`
  (`gui_api._ui_index_path()` resolves them via `sys._MEIPASS`).
- `collect_data_files('pdfminer')` + `collect_all('pdfplumber'/'openpyxl')` — the
  pdfminer CMap data is the classic frozen trap. `cryptography` is a hard pdfminer
  import and **must stay**.
- `excludes=['PIL','pypdfium2','pypdfium2_raw','tkinter','_tkinter']` — image libs
  the runtime paths (text/table extraction + plain workbooks) don't need, plus
  Tk/Tcl (the UI is a WebView since 0.8.0); proven safe by the frozen `-SelfTest`
  passing with them excluded.
- **Trust metadata** (reduces IT/Defender/DLP false-positives on the unsigned exe):
  version-info resource from `version.py`, `app.ico`, `app.manifest` (`asInvoker` +
  Win10/11), `upx=False`. **Code-signing is the only complete fix** (not yet done).
- **Browser selection** is in `common.launch_browser`: once per process it probes
  each channel (chromium when present → msedge → chrome; override
  `TSMIS_BROWSER_CHANNEL`; GUI dropdown sets `set_preferred_channel`) by
  launching headless and driving a page, so a too-new Edge falls through to the
  next channel. Raises `BrowserNotFoundError` (distinguishing "none installed"
  from "too new — update the tool") only if all fail. `PLAYWRIGHT_BROWSERS_PATH`
  is set by `paths.py` only when the bundle ships `_internal\ms-playwright`.

**Bundle hygiene / DLP (`prune_bundle.ps1`):** strips the bundle to runtime-only
files and **fails the build** if DLP-blocked content remains. Motivating case: the
Playwright Node driver shipped docs (`tracing.md`) containing a test credit-card
number that corporate DLP blocks. Deletes: all prose docs bundle-wide (`*.md`/
`*.rst`/`README`/… — **licenses kept**), sanitizes `dist-info` METADATA to headers
only, Playwright driver extras (`*.d.ts`, `types/`, `skill/`, `tools/trace/`,
`tools/dashboard/`, `vite/`), `tests/`/`*.pyi` stubs, any image-lib dirs that
slipped through. Guards (fail build if found): non-license docs, credit cards
(IIN + length + Luhn), PEM private keys, AWS keys, US SSNs. Re-runnable on an
extracted release: `prune_bundle.ps1 -Target "…\TSMIS Exporter"` (`-GuardOnly` to
audit). The ~149 MB floor is `node.exe` (~80 MB) + Python + pythonnet/WebView2
assemblies + pdf/excel libs.

## Extending

**New report type:**
1. `scripts/export_<name>.py` — a `ReportSpec` (`label` = exact dropdown text,
   `subdir`, `filename`, `wait_js`, `is_empty`, `save` — reuse `save_pdf_letter`/
   `save_via_export_button`) + `run_cli(SPEC, title=…)`.
2. Add a branch to `3. run_export…bat` and `5. fast export…bat`.
3. Add one entry to `EXPORT_REPORTS` in `reports.py` (feeds GUI + export_multi).
4. List the module in `APP_MODULES` in `build/app.spec` (lazy imports need it).
5. Add `output/<name>/.gitkeep`, whitelist in `.gitignore`.
6. Document in the table at the top.

**New consolidator** — implement `consolidate(events, confirm_overwrite) ->
ConsolidateResult` (console-free: log via `events.on_log`, ask before overwrite via
the callback, honor `is_cancelled()`, guard third-party imports with `_DEPS_OK`,
build openpyxl styles inside functions). For an XLSX report, wrap
`consolidate_xlsx_base.consolidate_xlsx` (set `INPUT_DIR`, `OUT_PATH`, `SHEET_NAME`,
`REPORT_NAME`) like `consolidate_highway_log.py`; for a different input format
(like PDF Ramp Summary), write standalone. Then add the `__main__` →
`run_consolidate_cli`, wire `4. consolidate…bat`, add to `APP_MODULES` and
`CONSOLIDATE_REPORTS`, and document here.

**New comparison type:** add one row to `COMPARE_REPORTS` in `reports.py`
(the Compare tab's type list is generated from it; rows are
`(label, module_or_adapter, kind)`) and the module to `APP_MODULES` in
`build/app.spec`. Two input kinds:
- `"files"` — a module exposing
  `compare(path_a, path_b, out_path, events=None, confirm_overwrite=None,
  mode="formulas") -> ConsolidateResult` (console-free, same rules as
  consolidators; the GUI passes `mode` from its values/formulas checkboxes —
  accept it even if only one flavor is implemented) plus `REPORT_NAME` and
  `suggest_name(path_a)`.
- `"folders"` — an adapter exposing
  `compare_folders(dir_a, dir_b, out_path, events=None,
  confirm_overwrite=None, mode="formulas") -> ConsolidateResult` plus
  `REPORT_NAME` and `suggest_name(dir_a, dir_b)` — usually just another
  `compare_env.EnvCompare(...)` instance (give it the report's subdir, sheet
  name, and optionally a pinned header / base `CompareSchema`).
Don't hand-roll workbook output: build a `CompareSchema` and call
`compare_core.run_compare` — that's the approved workbook style for free
(and the core's text/formulas are regression-locked; see *Compare tab*).

**Add/remove a route:** edit `ROUTES` in `common.py` (zero-padded 3-digit, optional
suffixes like `"005S"`/`"101U"` — must match the TSMIS `<select>` option values).

## Reliability

- **Heavy file logging (the "one log upload answers it" contract, v0.7.6):**
  `logging_setup.setup_logging()` → rotating `LOG_DIR/tsmis.log` (5 × 2 MB),
  file-only. Every line is thread-tagged (`[main]`, `[export-w2]`, `[login]` —
  fast mode's interleaved browsers stay distinguishable); the startup banner
  pins build (frozen/dev), Python/OS, resolved paths, and `TSMIS_*`/
  `PLAYWRIGHT_BROWSERS_PATH` overrides. Everything shown in the GUI log pane
  and every engine `on_log` line in the console flow is **mirrored** to the
  `tsmis.ui` logger, so the file carries the user's view (what was clicked,
  what was reported) alongside the engine's own diagnostics. Decision points
  log themselves: site/browser picks, channel probe results + why a fallback
  happened, saved-session-vs-device-mode (with auth-file age), each Edge
  profile attempt, portability verdicts, preflight steps, per-route outcomes
  **with elapsed time and file size**. Crash safety nets: `sys.excepthook` +
  `threading.excepthook` log full tracebacks (a windowed .exe has no stderr);
  every `GuiApi` method is wrapped (`_api_method`) so a bridge-call crash is
  logged AND returned to JS as a structured error instead of a dead Promise;
  uncaught JS errors come back through `api.log_js_error` into `tsmis.crash`;
  `faulthandler` writes hard interpreter crashes to `LOG_DIR/crash.log` for
  the **console entry points only** — it is incompatible with pythonnet and
  disabled in the GUI process (see *Design decisions*, trap 3; the GUI's
  native-crash trail is WER/Event Log).
  NOTE: the `[main]` thread tag is applied by a logging **Filter** — never
  rename the actual main thread (it breaks pywebview; see *Design decisions*).
  **Error messages must name the
  failing step and stay UI-neutral; the WHY (exception text, probe status,
  profile name) always goes to the log** — when adding code, log every
  decision and every swallowed exception (`type(e).__name__` + first line at
  minimum).
- **Preflight** (`common.preflight`): after login, before the loop, confirms the
  report selects and the Route control + Generate button exist — else
  `PreflightError` naming the failed step in the log + a `preflight_fail_*`
  page dump, so the run fails fast with one clear error.
  `SiteUnreachableError` (a `PreflightError`) covers "couldn't open the page
  at all" (network/VPN) with a check-your-connection message.
- **Failure screenshots:** on final failure, `_capture_failure()` writes
  `<report>_route_<route>_<ts>.png` + `.html` to `FAILURES_DIR` (best-effort).
- **Session expiry mid-run:** `_recover()` raises `AuthError`, stopping cleanly.

## Conventions

- Keep core code console-free; messages UI-neutral (see *Two Run Modes*).
- Sync Playwright API (not async). Runtime deps pinned; a browser is bundled
  **only** in the `-BundleChromium` variant.
- End-user setup uses global `pip` (no venv); the build uses `build\.venv`.
- **No tests** — true verification is a live export against TSMIS (needs login) or
  running a consolidator over existing files. Import-level sanity checks can use
  `build\.venv\Scripts\python.exe` without a login.
- **Never commit** `scripts/tsmis_auth.json` or generated `output/`/build artifacts.
  Commit messages: short, imperative (`add route 395`).

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `Playwright is not installed` | Setup not run | Run `1. setup…bat` |
| `LOGIN PROBLEM` (`AuthError`) | Session missing/expired AND automatic device sign-in unavailable | Run `2. login…bat` |
| Route keeps timing out | TSMIS server slow | Raise `REPORT_TIMEOUT_MS` |
| Route fails instantly with a "TSMIS site error" | The site can't build that route | Expected — recorded `failed` (see `FAILURES_DIR`); a TSMIS issue |
| County dropdown timeout | Slow network | Raise `COUNTY_ENABLE_TIMEOUT_MS` |
| One report's output wrong | That report's selector changed | Edit only its `ReportSpec` |
| "page looks different than expected" | Preflight failed — site changed | Check `LOG_DIR`/`FAILURES_DIR`; update selectors |
| `BrowserNotFoundError` | No usable browser found | Install Edge, re-run `1. setup…bat` (downloads Chromium), or use the with-browser zip |
| "The app window could not be created" box | WebView2 runtime missing/broken (very old or stripped Windows) | Install/update Microsoft Edge (ships the Evergreen WebView2 runtime); details in `LOG_DIR` |
| GUI shows a blank window | UI assets missing or JS crashed | `tsmis.log` carries JS errors (`log_js_error`); run with `TSMIS_UI_DEBUG=1` for DevTools |
| Edge sign-in "works" but exports can't log in | Edge signed in via the Windows device broker (PRT) — session never reaches cookies | Expected & detected: the capture is rejected (`storage_state_is_portable`) and login falls back to Chrome / Built-in Chromium |
| Browser launch fails after an Edge/Chrome update | Evergreen browser outran pinned Playwright CDP | Bump `playwright` in `requirements*.txt`, rebuild |
| DLP blocks a release file ("Credit Card Number") | Playwright driver docs bundled | `build.ps1` prunes them; clean a release with `prune_bundle.ps1 -Target …` |
| Build: "GUARD FAILED" | A dep shipped DLP-blocked content | Extend `$killDirs` in `prune_bundle.ps1` |
| Update pill opens a web page instead of installing | App folder is read-only (data fell back to `%LOCALAPPDATA%`) | Expected (`update_support()` = "link") — move the app somewhere writable, or extract the new zip manually |
| Update applied but the old version came back | A swap step failed; the swap rolled back | See `data\logs\update_helper.log`; close anything holding `_internal` open and update again |
| Update downloaded, app closed, but nothing was installed (≤ v0.10.0) | The old PowerShell swap helper was silently blocked (locked-down PCs with no PowerShell) | Fixed in v0.10.1 (the staged exe swaps itself; no scripts). One manual install of ≥ 0.10.1 — the new version sits intact in `data\update\staged`, or download the zip — then auto-update works |
