# CLAUDE.md — TSMIS Reports Exporter

## Project Purpose

A unified Windows desktop tool that bulk-exports TSMIS (Caltrans
Transportation System Management Information System) reports for every
California state route. The user picks which report(s) to export from a
menu — one report type, several, or all at once — and one shared login serves
every report type.

Currently supported reports:

| Choice | Report | Output format | Output folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/ramp_summary/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/ramp_detail/` |
| 3 | Highway Sequence Listing | XLSX | `output/highway_sequence/` |
| 4 | Highway Log | XLSX | `output/highway_log/` |

The GUI exports any combination of these (tick checkboxes); the console menu
adds an "A" option to pick several / all at once (see **Exporting Several Report
Types at Once**).

This repo combines the previously separate
`TSMIS-Reports-Export-ALL-Ramp-Summary` and
`TSMIS-Reports-Export-ALL-Ramp-Detail` projects.

## Desktop App Conversion — Status & Resume Point

> **This project is mid-conversion** from `.bat`-launched scripts into a
> **portable, single-folder Windows desktop app** (bundled Python +
> dependencies + a GUI, **no installer**, no Python required on the target PC;
> it drives the machine's installed Edge/Chrome rather than bundling a browser).
> The conversion is **additive** — the original `.bat` workflow
> still works at every step. **If you are a new session, read this section
> first.**

**End goal:** non-technical office staff unzip one folder and double-click an
`.exe` — no setup, no console login. Distributed as a plain zip.

**Locked decisions:**
- **Packaging:** PyInstaller **onefolder** (not onefile), shipped as a
  **portable zip** (no installer).
- **Browser:** **do NOT bundle a browser.** Drive the machine's installed
  **Microsoft Edge** (then Chrome) via `channel="msedge"`/`"chrome"`
  (`scripts/common.launch_browser`). Edge ships with Windows and is Chromium, so
  `page.pdf()` (Ramp Summary) + downloads work — verified frozen. This drops
  ~370 MB and removes the bundled-browser AV/DLP surface entirely (the bundle
  went 587 → **148 MB**). Only Playwright's Node driver (`node.exe`) still ships.
  *(Superseded the earlier "bundle full Chromium via `channel="chromium"`"
  decision.)*
- **Data location — "option A" (portable, never breaks):** the packaged app
  writes `output/`, the auth token, logs, and config **next to the `.exe`**,
  auto-falling back to `%LOCALAPPDATA%\TSMIS Exporter` if that folder is
  read-only. Implemented in `scripts/paths.py`.
- **GUI:** Tkinter (+ optional theme), built. A worker thread owns the Playwright
  session and talks to the UI through the `Events` callbacks (`scripts/events.py`).

**Pinned versions (see `version.py`):**
- `playwright==1.60.0` — pins the bundled **Node driver** only; no Chromium is
  bundled (the app uses system Edge/Chrome, and Playwright's CDP is compatible
  across evergreen Edge/Chrome).
- `pdfplumber==0.11.9` (pulls `pdfminer.six==20251230`), `openpyxl==3.1.5`
- `pyinstaller==6.20.0`, `pyinstaller-hooks-contrib==2026.5`
- Built/tested on **Python 3.11**.

**Phase tracker:**

| Phase | What | Status |
|---|---|---|
| 1 | Prove Playwright/Chromium bundles & runs portably | ✅ done |
| A | Trim bundle to full-Chromium-only (~581 MB onefolder) | ✅ done |
| 0 | Reproducible build infra (`build/`, pinned reqs, `version.py`) | ✅ done |
| 2 | Frozen-aware paths (`scripts/paths.py`, option A) | ✅ done |
| 3a | Decouple export engine from console (`events`/`exporter`/`cli`) | ✅ done — **live-verified** |
| 3b | Make the 3 consolidators importable (return results, no `print`/`exit`) | ✅ done |
| 4 | Build the GUI on the decoupled core | 🟡 built — **visual/live test pending** |
| 5 | Reliability (logging, failure screenshots, preflight, retry) | 🟡 built — live test pending |
| 6 | Package the real GUI app + zip; optional code-signing | 🟡 built — **pending live launch** |

**✓ Live-verified:** Phase 3a passed a live export against TSMIS — logged in via
SSO+MFA through `2. login (update login).bat`, then ran
`3. run_export (main script).bat` and confirmed routes export for each report
type. This is in addition to the unit-level checks (every module imports;
generated `wait_js`/filenames are byte-identical to the originals; `AuthError`
is raised before any browser launches).

**Build the portable app:** from the repo root run
`powershell -ExecutionPolicy Bypass -File build\build.ps1` → windowed
`dist\TSMIS Exporter\` (~148 MB; double-click `TSMIS Exporter.exe`). Add
`-SelfTest` for a headless console build that verifies the frozen bundle without
launching a window. See **Build & Packaging** for details and gotchas.

## Repository Layout

```
.
├── 1. setup (one time).bat            # pip install -r requirements.txt (no browser download; uses system Edge/Chrome)
├── 2. login (update login).bat        # captures auth session
├── 3. run_export (main script).bat    # auth check + menu (single report, or A = several/all) + run
├── 4. consolidate (combine reports).bat  # menu + run chosen consolidator
├── 5. fast export (experimental).bat  # parallel multi-browser export (sets TSMIS_FAST_WORKERS)
├── run app (GUI preview).bat          # dev launcher for the desktop GUI
├── requirements.txt                   # pinned runtime deps (playwright, pdfplumber, openpyxl)
├── requirements-build.txt             # build deps (-r requirements.txt + pyinstaller)
├── version.py                         # app name/version + pinned Playwright (Node driver) version
├── scripts/
│   ├── paths.py                       # frozen-aware paths (output/auth/logs/failures/config); option A
│   ├── logging_setup.py               # rotating file log under LOG_DIR (all entry points call it)
│   ├── common.py                      # URL, ROUTES, timeouts, auth + nav helpers, AuthError, RunCancelled, preflight
│   ├── events.py                      # Events sink + RunResult + ConsolidateResult (engine <-> UI seam)
│   ├── exporter.py                    # shared export engine + ReportSpec + save strategies
│   ├── exporter_parallel.py           # EXPERIMENTAL fast mode: N browsers in parallel; reuses exporter.py
│   ├── run_report.py                  # per-route run report (CSV; auto-saved each run; +multi)
│   ├── cli.py                         # console adapter: run_cli (one report) + run_cli_multi (several)
│   ├── login.py                       # writes the auth file (headed browser)
│   ├── reports.py                     # ONE registry of report types (GUI + export_multi read it)
│   ├── export_ramp_summary.py         # thin: a ReportSpec (PDF) + run_cli
│   ├── export_ramp_detail.py          # thin: a ReportSpec (XLSX download) + run_cli
│   ├── export_highway_sequence.py     # thin: a ReportSpec (XLSX download) + run_cli
│   ├── export_highway_log.py          # thin: a ReportSpec (XLSX download) + run_cli
│   ├── export_multi.py                # entry point: pick several/all report types -> run_cli_multi
│   ├── consolidate_xlsx_base.py       # shared XLSX consolidator core (detail/sequence/log use it)
│   ├── consolidate_ramp_summary.py    # PDFs  -> one XLSX (audit cols); standalone (PDF parsing)
│   ├── consolidate_ramp_detail.py     # thin wrapper over consolidate_xlsx_base
│   ├── consolidate_highway_sequence.py # thin wrapper over consolidate_xlsx_base
│   ├── consolidate_highway_log.py     # thin wrapper over consolidate_xlsx_base
│   ├── gui_main.py                    # GUI entry point (dev import paths, launches App)
│   ├── gui_app.py                     # main window (Tk): header, Export/Consolidate tabs, log
│   ├── gui_worker.py                  # worker threads: Export/Consolidate/Login (Events -> queue)
│   └── gui_theme.py                   # palette/fonts/ttk styles (clam base)
├── build/                             # portable-build infra (Phase 0)
│   ├── build.ps1                      # one-command reproducible onefolder build (-SelfTest for headless verify)
│   ├── prune_bundle.ps1               # strip bundle to runtime-only files + DLP guard (run by build.ps1)
│   ├── app.spec                       # PyInstaller spec (Node driver + pdf/excel; excludes image libs; version-info + icon + manifest; no browser)
│   ├── app.ico                        # app/.exe icon (neutral; how it was made is in Build & Packaging)
│   ├── app.manifest                   # embedded in the .exe (asInvoker, Win10/11) — IT/Defender trust signal
│   ├── gui_main entry → scripts/gui_main.py  # the windowed app's real entry point
│   ├── full_smoke.py                  # comprehensive frozen self-test: system-browser pdf+download, pdfplumber, openpyxl, GUI (the -SelfTest entry)
│   ├── dist_readme.txt               # copied into the build as "Start Here.txt"
│   └── .venv/                         # build venv (git-ignored)
├── dist/                              # build output: dist/TSMIS Exporter/ (git-ignored)
├── output/                            # folder structure tracked, contents ignored
│   ├── ramp_summary/  ramp_detail/  highway_sequence/  highway_log/  consolidated/
│   └── run_reports/                   # auto-saved per-route CSV reports (created on demand)
├── .gitignore
└── CLAUDE.md
```

`scripts/tsmis_auth.json` (auth cookies) is git-ignored. The five `output/`
subfolders are committed (via empty `.gitkeep` files) so the scripts always
have a place to write, but generated files inside them are git-ignored — they
can be gigabytes. The local `.claude/` permission state and build artifacts
(`build/.venv`, `build/ms-playwright`, `build/pyi-work`, `dist/`) are git-ignored.

## Technology Stack

| Component | Detail |
|---|---|
| Language | Python 3.11 (stdlib + Playwright + pdfplumber + openpyxl) |
| Browser automation | `playwright` (sync API) driving the **system** browser — `channel="msedge"`, then `"chrome"` (no bundled browser) |
| PDF parsing | `pdfplumber` (consolidators only) |
| Excel writing | `openpyxl` (consolidators only) |
| Packaging | PyInstaller (onefolder, portable) |
| GUI | Tkinter |
| Target application | `https://rhansonrizing.github.io/tsmis_reports/index.html` |
| Auth mechanism | ArcGIS / Caltrans Azure AD (SSO + MFA) |
| Session persistence | Playwright `storage_state` → `tsmis_auth.json` |
| OS | Windows (`.bat` launchers + packaged build); Python core is OS-agnostic |

## Workflow for End Users (current `.bat` flow)

1. **Setup (once per machine):** Double-click `1. setup (one time).bat` —
   runs `pip install -r requirements.txt` (the pinned Playwright + pdfplumber +
   openpyxl, matching what the app is built against). No browser is downloaded;
   the tool uses the Microsoft Edge / Chrome already on the machine.
2. **Login (once, or when the session expires):** Double-click
   `2. login (update login).bat` — opens a visible browser, the user
   completes SSO + MFA, then presses Enter to save the session into
   `scripts/tsmis_auth.json`. The same file is used by every export script.
3. **Export (repeatable):** Double-click `3. run_export (main script).bat` —
   checks the auth file exists, shows a menu (pick one report, or `A` for
   several / all), asks which routes to export (press Enter for all, or list
   specific ones), then runs the selected report(s) headlessly over those routes.
4. **Consolidate (optional, repeatable):** Double-click
   `4. consolidate (combine reports).bat` — pick one report type and combine
   every per-route export into a single workbook under `output/consolidated/`.

> The packaged GUI app replaces steps 2–4 with buttons, but the `.bat` flow
> remains for development and as a fallback.

## How the Menu Works

`3. run_export (main script).bat`:

1. Checks that `scripts\tsmis_auth.json` exists — if not, instructs the user
   to run the login BAT first and exits.
2. Shows a numbered menu:
   - `1` → `python scripts\export_ramp_summary.py`
   - `2` → `python scripts\export_ramp_detail.py`
   - `3` → `python scripts\export_highway_sequence.py`
   - `4` → `python scripts\export_highway_log.py`
   - `A` → `python scripts\export_multi.py` (pick several / all report types)
   - `Q` → quit
3. Invalid choices loop back to the menu.
4. After a report is chosen, the Python entry point (`run_cli`) prompts for the
   routes to export — Enter (or empty) means **all routes**; otherwise type a
   list like `5, 99, 101` (any casing / zero-padding, suffixes like `101U` ok).
   The same prompt backs the fast-mode BAT. The `A` option (`run_cli_multi`)
   first asks which report types, then the same routes prompt. See **Selecting
   Which Routes to Export** and **Exporting Several Report Types at Once**.

`4. consolidate (combine reports).bat` follows the same pattern but runs no
auth check (the consolidator reads local files, not TSMIS).

Each `export_*.py` still has a `__main__` entry, so the BAT calls are
unchanged after the refactor — they now run `run_cli(SPEC, ...)` internally.

## Code Structure (post Phase-3a refactor)

The core is **console-free** so it can back both the `.bat` console flow and
the planned GUI. Flow: an entry point builds a `ReportSpec` and calls the
engine with an `Events` sink; the engine reports progress through that sink
and raises `AuthError` on session problems.

- **`scripts/paths.py`** — single source of truth for *where* files live
  (frozen-aware; option A). Exposes `DATA_ROOT`, `OUTPUT_ROOT`, `AUTH`,
  `LOG_DIR`, `FAILURES_DIR`, `CONFIG_FILE`. In dev it preserves the original layout
  (`./output`, `scripts/tsmis_auth.json`); when frozen it resolves next to the
  `.exe` with a `%LOCALAPPDATA%` fallback.
- **`scripts/common.py`** — shared, console-free helpers: `URL`, `ROUTES`,
  timeout constants, `AuthError`, `RunCancelled` (raised mid-wait so Cancel
  interrupts the current route — see **Cancelling a Run**), `clear_auth()`,
  `require_valid_auth()`
  (raises `AuthError`), `navigate_with_auth`, `is_logged_in`, `select_report`,
  `wait_with_skip_option(page, js, prefix, events, ...)` (honors both
  `should_skip()` and `is_cancelled()`), `launch_browser` /
  `new_authed_browser` (drive the **system** browser — probe + launch
  `channel="msedge"`, fall back to `"chrome"` if Edge can't be driven,
  `TSMIS_BROWSER_CHANNEL` to override, raising `BrowserNotFoundError` if neither
  works), `set_preferred_channel(ch)` (the GUI picker's choice; tried first, other
  stays a fallback) and `check_browsers()` (probe both for the readiness panel →
  `{channel: ok/missing/broken}`), and the route-selection parsers
  `normalize_route` / `parse_routes` (free-text → validated route list in
  `ROUTES` order; raise a UI-neutral `ValueError` on bad/empty input).
  Re-exports `AUTH` from `paths.py` (output paths come from `paths.py` directly).
- **`scripts/events.py`** — `Events` (callbacks `on_log`, `on_route`,
  `should_skip`, `is_cancelled`; all default to no-ops), `RunResult` (export),
  and `ConsolidateResult` (consolidation: `status` ok/cancelled/error,
  `message`, `output_path`, `summary_lines`). The seam between the engines and
  their driver (console or GUI).
- **`scripts/exporter.py`** — the **one** proven per-route loop,
  `run_export(spec, events)`, plus `ReportSpec`, the reusable save strategies
  `save_pdf_letter` / `save_via_export_button`, and `_recover()`.
- **`scripts/cli.py`** — console adapters that keep both `.bat` flows working:
  `run_cli(spec, title)` for one report and `run_cli_multi(report_options, title)`
  for several (wires `Events` to `print()`/`msvcrt`, prompts for the route subset
  via `_resolve_routes_console` (Enter = all; also honors the `TSMIS_ROUTES` env
  var) and passes `routes=` to the engine, renders `AuthError` like the old
  `handle_bad_auth`). Both share `_run_one_export` (dispatches sequential vs fast
  by `TSMIS_FAST_WORKERS`); `run_cli_multi` adds `_select_reports_console`
  (numbers / `A`, honoring `TSMIS_REPORTS`). `run_consolidate_cli(consolidate_fn)`
  drives consolidators (wires `on_log` to `print`, the overwrite prompt to
  `input()`, maps the `ConsolidateResult` status to the exit code). Imports
  `exporter`/`exporter_parallel` lazily so consolidating never pulls in Playwright.
- **`scripts/export_*.py`** — thin ~30-line files: each defines a `ReportSpec`
  and calls `run_cli`. `export_multi.py` derives its report list from `reports.py`
  and calls `run_cli_multi` (backs the menu's `A` option).
- **`scripts/reports.py`** — the **single registry** of report types:
  `EXPORT_REPORTS = [(label, fmt, spec), …]` and
  `CONSOLIDATE_REPORTS = [(label, fn, OUT_PATH), …]`. Both the GUI (`gui_app.py`)
  and `export_multi.py` import from here, so the report list can't drift between
  them. (The `.bat` menus are static text and are still edited by hand.)
- **`scripts/consolidate_*.py`** — each exposes `consolidate(events,
  confirm_overwrite) -> ConsolidateResult` (console-free: logs via `Events`,
  asks before overwrite via the callback, honors `is_cancelled()`, never
  `print`/`input`/`exit`) plus a `__main__` that calls `run_consolidate_cli`. The
  three XLSX reports (Ramp Detail, Highway Sequence, Highway Log) are thin
  wrappers over a shared `consolidate_xlsx_base.consolidate_xlsx`, parameterized
  by input dir / sheet name / output name; Ramp Summary stays standalone (it
  parses PDFs). Third-party imports are guarded with a `_DEPS_OK` flag and openpyxl
  style objects are built inside functions, so the modules import cleanly even if a
  dependency is missing — the GUI gets a clean error `ConsolidateResult` instead
  of a fatal `ImportError`. See **Adding a New Consolidator**.

**GUI — `scripts/gui_*.py`** (built on the same console-free core):
- `gui_main.py` — entry point. Sets the dev import paths (frozen builds need
  nothing — the browser is the system one), then runs `App().mainloop()`.
- `gui_app.py` — the `App(tk.Tk)` window: a header (session dot + Log in button +
  a compact **readiness strip**), an Export/Consolidate **notebook**, a shared
  progress bar + counts + log pane, and a footer (output path + Open folder). The
  Export tab has a **checkbox per report type** (tick one or more — selected types
  run one after another) and a **Routes** entry (blank = all; or type/`Choose…` a
  subset via `parse_routes`), both passed to `ExportWorker(specs, ..., routes=...)`.
  The progress label shows `[i/n] <report>` while several run; **Cancel** stops
  the current route promptly (`RunCancelled`). The header strip has
  a **Browser** dropdown (default Edge → `common.set_preferred_channel`), green/red
  **status dots** for Edge · Chrome · Output · Tools (hover = detail tooltip), and
  a **Re-check** button — all filled in on launch by a `CheckWorker` (login stays
  in the header's status row). The window auto-sizes to its content so the log
  pane can't be squeezed away. Drains the worker queue via `after(100)`; never
  does browser/file work itself.
- `gui_worker.py` — `ExportWorker` / `ConsolidateWorker` / `LoginWorker` /
  `CheckWorker` threads. They drive the engines through `Events` (or, for
  `CheckWorker`, run the readiness probes), posting `(kind, payload)` messages to
  a `queue.Queue`. `ExportWorker` takes a **list of specs** and runs them in turn,
  resetting the per-report tally and posting `("export_done", [(spec, RunResult),
  …])` at the end. Skip/Cancel are `threading.Event`s; login waits on a `done`
  event set by the "I've finished logging in" button (replacing `login.py`'s
  console `input()`s). `CheckWorker` posts `("check", (key, status, text))` per
  item then `("checks_done", {channel: status})`.
- `gui_theme.py` — palette, fonts, ttk styles (clam base). One place to restyle.

**Threading rule:** Playwright's sync API is thread-affine, so *all* browser work
runs on a worker thread; only the main thread touches Tk. Workers talk to the UI
exclusively through the queue. Launch the GUI in dev with
`run app (GUI preview).bat` (or `python scripts\gui_main.py`).

**Why a shared loop now?** The old design kept a full copy of the loop in each
`export_*.py` to isolate report bugs. The refactor preserves that isolation by
moving each report's *differences* into a `ReportSpec` (label, output
filename, post-Generate `wait_js`, `is_empty` check, `save` strategy) — the
per-report data stays isolated, but the proven loop, recovery, and skip/cancel
logic live in one place so the GUI can call a single function.

## Configurable Constants (in `scripts/common.py`)

| Constant | Default | Purpose |
|---|---|---|
| `REPORT_TIMEOUT_MS` | `360_000` (6 min) | Hard ceiling for a single report in the **sequential** (one-browser) flow. Some routes (e.g. Route 5 Ramp Detail) legitimately take minutes. |
| `FAST_REPORT_TIMEOUT_MS` | `600_000` (10 min) | Per-route ceiling in **fast mode**. Larger because N concurrent browsers load the TSMIS server, so big reports (e.g. Highway Sequence) take longer. |
| `RETRY_REPORT_TIMEOUT_MS` | `900_000` (15 min) | Per-route ceiling for the **end-of-run retry pass** (runs one route at a time, so the most generous window). |
| `SKIP_PROMPT_AFTER_MS` | `60_000` (1 min) | Soft timer: after this, a "still working" status is emitted and the skip escape-hatch opens. |
| `COUNTY_ENABLE_TIMEOUT_MS` | `60_000` (60 s) | Max wait for the county dropdown to enable. |
| `RETRY_COUNT` | `1` | Extra in-loop attempts per route after a transient (non-timeout) failure. A hard timeout is never retried in-loop (it gets the end-of-run retry pass instead). |

Increase these if the TSMIS server is slow. The per-route timeout reaches both
the report-generation wait and the export/download wait (so a big report whose
*download* is slow under load is covered too).

## Skipping a Slow Route Mid-Run

While waiting on a slow route, the user can skip it. In the console flow
(`cli.py`) this is the `S` key (Windows `msvcrt`); in the GUI it is the Skip
button. Mechanically, `wait_with_skip_option` polls `events.should_skip()`:

1. Waits up to `SKIP_PROMPT_AFTER_MS` silently.
2. After that, emits a status line every ~30 s and watches for a skip request.
3. If skipped, the route is recorded in `RunResult.user_skipped`, the form is
   re-armed (`_recover`), and the loop continues.
4. If nothing is requested and `REPORT_TIMEOUT_MS` elapses, the route is added
   to `failed` and the loop recovers as usual.

Re-run later and the loop retries any routes without an output file.

## Cancelling a Run

Cancel stops the **current** export immediately, not just between routes. The
driver sets `events.is_cancelled()` (the GUI **Cancel** button → `cancel_event`;
on window close too), and `wait_with_skip_option` checks it at the top of every
poll (~5 s), raising **`RunCancelled`** mid-wait. The engines treat that as a
clean stop, *not* a route failure or a worker crash:

- **Sequential (`exporter.py`):** `_attempt_route` also re-checks cancel just
  before saving; `_process_route` re-raises `RunCancelled` (never records the
  route as failed or retries it); the main loop and the retry pass catch it and
  break. The end-of-run retry pass is skipped when cancelled.
- **Fast mode (`exporter_parallel.py`):** the worker catches `RunCancelled` and
  winds down; `is_cancelled()` (which also reflects the shared `stop` flag)
  quiets the other workers between routes.

Either way the run returns a *partial* `RunResult` (so the run report and the
summary still reflect what completed), and re-running resumes — routes already on
disk are skipped. This replaced the old behavior where Cancel only took effect
after the in-flight route's full report-generation wait finished.

## Retrying Failed Routes (end-of-run pass)

After the main run finishes, both engines automatically give any **failed**
routes one more, more patient attempt (`exporter._retry_failed_routes`):

- **Why:** a big report (e.g. Highway Sequence) can blow the per-route window
  not because it's broken but because the server was slow — especially in fast
  mode, where several browsers compete for it. A second pass under lighter load
  usually lands it.
- **One at a time, generous timeout:** the retry pass is strictly **sequential**
  and uses `RETRY_REPORT_TIMEOUT_MS` (15 min/route default). In **fast mode** the
  parallel run finishes first, then a *single* fresh browser
  (`exporter_parallel._retry_failed_sequential`) retries the stragglers serially
  — so a slow report is no longer fighting N others for the server. (The same
  helper backs both engines; the sequential engine just reuses its open browser.)
- **Scope:** only `failed` routes are retried — not user-skipped (deliberate) or
  empty (legitimately no data) ones. Routes already on disk are still skipped.
- **Clean bookkeeping:** a route's first-pass `failed` record is dropped before
  the retry, then re-recorded with its *final* status, so the run-report CSV has
  one row per route and the GUI progress counts shift (failed → saved) in place
  rather than double-counting. The auto-saved run report is written **after** the
  retry pass, so it reflects final outcomes.
- **Safety:** an `AuthError` during the pass ends the run like the main loop; any
  other unexpected error is logged and swallowed so the run report still saves.
  If the form can't be re-armed, or the user cancels, the un-retried routes stay
  `failed`.

Still failing after the retry pass usually means a genuine problem — check
`FAILURES_DIR` (screenshot + HTML) and `LOG_DIR`. Re-running also resumes, since
the missing output files are simply re-attempted.

## Selecting Which Routes to Export

By default every export covers **all** routes in `ROUTES`. A run can be narrowed
to a specific subset; the default (all) is unchanged if you don't pick any.

- **The engine was already route-aware:** `run_export(spec, events, *,
  routes=ROUTES)` and `run_export_parallel(..., routes=ROUTES)` take the route
  list. The feature is just plumbing a chosen subset to that parameter from each
  driver, so sequential and fast mode both honor the selection identically.
- **Parsing (one place):** `common.parse_routes(text)` turns free-text into a
  validated list in `ROUTES` order. It accepts commas / spaces / semicolons /
  newlines, any casing or zero-padding, and suffixes (`5`, `005`, `5s`, `101U`);
  it de-dupes, and raises a UI-neutral `ValueError` (`"Not valid route(s): …"` /
  `"No routes entered."`) listing unknown tokens. `normalize_route(token)` maps
  one token to its canonical `ROUTES` spelling (or `None`).
- **Console (`cli.py`):** `run_cli` calls `_resolve_routes_console()` — Enter /
  empty / `all` (or EOF) → all routes; otherwise the typed list, re-prompting on
  bad input. It also honors a `TSMIS_ROUTES` env var (a list, or `all`/empty),
  which skips the prompt. The banner and the final "Routes handled: N of M"
  summary reflect the chosen count.
- **GUI (`gui_app.py`):** a **Routes** entry on the Export tab (blank = all) with
  a live count/validation hint and a **Choose…** modal multi-select picker. The
  selection is parsed on Start (a clear messagebox on error) and passed as
  `ExportWorker(..., routes=…)`; the worker uses the subset size as the progress
  total. Fast mode and route selection are independent and compose.
- **Resume still applies:** routes already on disk are skipped, so re-exporting a
  subset only fetches what's missing (delete a file to force a re-download).

This is per-run selection. To change the route universe permanently (add/remove a
route everywhere), edit the `ROUTES` list — see **Adding or Removing Routes**.

## Exporting Several Report Types at Once

A single run can export any combination of the report types (or all of them).
Each selected report runs in turn through the **same** proven engine — there is
no new export path — so route selection, fast mode, resume, retry, and the run
report all behave exactly as for a single report.

- **Engine:** unchanged. The drivers loop over the chosen `ReportSpec`s and call
  `run_export` / `run_export_parallel` once per report; each report opens its own
  browser + preflight and auto-saves its own run-report CSV. Running types
  serially (not all at once) keeps fast mode honest — at most `workers` browsers
  are ever open.
- **Console (`cli.py` + `export_multi.py`):** `run_cli_multi(report_options)`
  first asks which report types (numbers like `1,3`, or `A`/Enter for all; honors
  the `TSMIS_REPORTS` env var via `_select_reports_console`), then the usual routes
  prompt, then runs each and prints a per-report + combined summary. Backed by the
  `A` menu option in `3. run_export` and `5. fast export`.
- **GUI (`gui_app.py`):** the Export tab shows a **checkbox per report type** (tick
  one or more; first ticked by default). `start_export` collects the ticked specs
  and hands the list to `ExportWorker(specs, …)`, which runs them in turn, resets
  the progress tally per report (the label shows `[i/n] <report>`), and posts one
  combined `("export_done", [(spec, RunResult), …])`. **Save run report…** writes a
  single combined CSV (`run_report.write_run_report_multi`) when several ran.
- **Cancel** stops the whole multi-run — the current report's in-flight route ends
  promptly and later reports don't start. See **Cancelling a Run**.

## Resume / Idempotency

`run_export` checks `if out_path.exists(): continue` before each route, so
re-running after an interruption safely skips already-downloaded files. Delete
specific files from an `output/<report>/` folder to force a re-download.

## Experimental Fast Mode (parallel browsers)

`scripts/exporter_parallel.py` is an **experimental** speed mode that runs
several headless browsers at once, each restoring the **same** saved session and
pulling routes off a shared `queue.Queue` until it is empty. It is **additive**:
the proven sequential engine (`exporter.run_export`) is untouched and remains the
default. The per-route mechanics are **reused** from `exporter.py`
(`_process_route`, `_record`, `_capture_failure`, `_retry_failed_routes`), so a
per-report fix benefits both engines; only the concurrency/coordination is new.

- **Self-balancing:** a shared work queue (not static shards) keeps fast workers
  busy, so no single browser gets stuck with all the slow routes (5, 99, 101…).
- **Same contract as the sequential engine:** returns a merged `RunResult`,
  raises `AuthError`/`PreflightError` the same way, honors `is_cancelled()`
  (checked between routes), skips routes whose output file already exists (so it
  resumes), and auto-saves the run-report CSV. A single preflight runs **once**
  before launching N browsers, so a bad session/changed site fails fast.
- **Bigger per-route window:** workers use `FAST_REPORT_TIMEOUT_MS` (10 min vs
  the sequential 6) because the concurrent load slows the server — otherwise big
  reports time out purely from the parallelism, not a real problem.
- **Serial retry of stragglers:** after all workers finish, failed routes get one
  **single-browser, one-at-a-time** retry (`_retry_failed_sequential` →
  `_retry_failed_routes`, `RETRY_REPORT_TIMEOUT_MS`), so a slow report finally
  lands without competing with N other browsers. See **Retrying Failed Routes**.
- **A crashed worker never silently drops routes.** If a worker dies with an
  unexpected error it sets a `worker_crashed` flag and exits, but the **other
  workers keep draining the queue** (one dead browser no longer aborts the whole
  run). After the join, any route with no recorded outcome and no file on disk —
  the crashed worker's in-flight route plus anything left unstarted — is
  **reconciled as `failed`**, so it shows up, gets the serial retry, and is counted
  exactly once in the run report. (Reconciliation is skipped on user cancel: those
  routes are just not-done, to be resumed, not failures.)
- **Per-route Skip is disabled** during the parallel phase (ambiguous with
  several routes in flight) — use **Cancel** to stop the whole run (it now
  interrupts the in-flight wait too; see **Cancelling a Run**). (The serial
  retry phase is one-at-a-time, so the console `S` key works again there.)
- **Threading:** Playwright's sync API is thread-affine, so each worker owns its
  own `sync_playwright()` + browser + context + page and never shares a
  Playwright object across threads. Per-worker `RunResult`s are merged at the
  end; the only locked hot-path state in the GUI is the progress tally
  (`ExportWorker._tally_lock`).

**How many browsers? (`DEFAULT_WORKERS=3`, `MAX_WORKERS=30` in
`exporter_parallel.py`)** The TSMIS/Caltrans backend handles high concurrency
fine (operator-tested), so the practical limit is the **client PC, not the
server**: each worker drives one browser (Edge/Chrome) process (~300–500 MB under
load) plus a Playwright driver. Rule of thumb: **3 = safe default (~2.5–3× faster), 8–12 =
big speedup on a healthy multi-core PC, 30 = hard cap** (~9–15 GB RAM for
browsers alone — only on a well-resourced machine). Budget ~0.5 GB RAM per
worker and leave headroom; requested counts are clamped to `[1, MAX_WORKERS]`.

**How to turn it on:**
- **Console / .bat:** `5. fast export (experimental).bat` asks how many browsers,
  sets the `TSMIS_FAST_WORKERS` env var, then shows the usual report menu (incl.
  `A` for several / all). Any flow that runs an `export_*.py` (or `export_multi.py`)
  honors `TSMIS_FAST_WORKERS`; `run_cli`/`run_cli_multi` route to the parallel
  engine when it is > 1 — the thin exporters are unchanged.
- **GUI:** an "⚡ Fast mode (experimental)" checkbox + worker-count spinner on the
  Export tab; `start_export` passes the count to `ExportWorker(..., workers=N)`.
- **With multi-report export:** report types still run **sequentially** (one after
  another), each using N browsers, so at most N browsers are ever open at once.

## Auth / Session Details

- `scripts/login.py` writes the auth file via `ctx.storage_state(path=...)`
  (path from `paths.AUTH`).
- **Login is validated before it's saved** (both the GUI `LoginWorker` and the
  console `login.py`): the session is only written if a real TSMIS login is
  detected (`is_logged_in` on any page in the context — SSO can land the report
  in a popup). This kills two old footguns: clicking "I've finished logging in"
  *without* signing in no longer saves a junk session + reports "ready". The GUI
  worker also **watches the login window closing**, but the close signal must
  survive the SSO/MFA dance — which navigates, can open a popup, and may replace
  the original tab. So it does **not** treat the *original* page closing, a
  `browser.is_connected()` blip, or a single transient `ctx.cookies()` error as
  "closed" (an earlier version did, and that slammed the window shut the instant a
  password went through, reporting a false **cancelled**). The reliable signal is
  **no open tabs remain in the context**, and only after a **debounce** (a few
  consecutive no-tab ticks) so a brief gap during the redirect isn't a false
  close, with a long all-calls-failing streak as a backstop for a truly dead
  connection. Because the session is captured the *instant* a login is detected
  (`is_logged_in` on any page — SSO can land it in a popup), closing the window
  after signing in still saves it; closing it *without* signing in resolves to
  **cancelled** (the GUI never hangs on "Waiting…"), while clicking "I've finished"
  without a login reports `login_failed`. On any non-save outcome no file is
  written, so a previously-valid session is preserved.
- **Edge-specific:** Microsoft Edge can relaunch itself through a "compatibility
  layer", and the relaunched process isn't the one Playwright drives — its context
  silently disconnects, which looks exactly like the login window closing the
  moment SSO completes (Chrome has no such relaunch). The headed login launch
  passes **`--edge-skip-compat-layer-relaunch`** (`common._channel_launch_kwargs`,
  Edge + headed only, so the headless export path is untouched). `LoginWorker`
  also writes **token-free diagnostics** to `LOG_DIR/tsmis.log` (tab-count
  changes, capture, disconnect, the close decision) so an Edge login failure is
  debuggable from the user's `Logs`.
- The engine calls `require_valid_auth()` first — it checks the file exists, is
  valid JSON, **and is shaped like a Playwright storage_state** (`cookies`/
  `origins` lists). That last check matters: a valid-JSON-but-not-storage_state
  file would otherwise crash later inside `new_authed_browser()`'s
  `browser.new_context(storage_state=...)` as a raw traceback; instead it raises
  `AuthError` and the drivers guide a re-login.
- If the session is missing, malformed, or expired, the core raises
  **`AuthError`**. The console adapter (`cli.py`) catches it, clears the stale
  file (`clear_auth()`), prints next steps, and exits; the GUI will catch it
  and show a re-login dialog.
- The BAT menu also gates on `scripts\tsmis_auth.json` existing before the
  menu is shown.
- The auth file is git-ignored — treat it as a credential. In the packaged app
  it lives under the data folder next to the `.exe` (option A).

## Adding or Removing Routes

Edit the `ROUTES` list in `scripts/common.py`. The change applies everywhere.
Route strings must match the exact option values in the TSMIS "Route"
`<select>` (zero-padded 3-digit strings, with optional suffixes like `"005S"`,
`"101U"`).

## Adding a New Report Type

1. Create `scripts/export_<name>.py` modeled on the existing thin exporters:
   define a `ReportSpec` (`label` = exact dropdown text, `subdir`, `filename`,
   `wait_js`, `is_empty`, `save`) and call `run_cli(SPEC, title=...)`. Reuse
   `save_pdf_letter` or `save_via_export_button` from `exporter.py`, or write a
   new save strategy there.
2. Add a numbered branch to `3. run_export (main script).bat` (and `5. fast
   export (experimental).bat`).
3. Add one entry to `EXPORT_REPORTS` in `scripts/reports.py` — that single list
   feeds both the GUI checkboxes and `export_multi`'s several/all selector (no
   per-file edits to `gui_app.py`/`export_multi.py`).
4. List the new module(s) in `APP_MODULES` in `build/app.spec` (they're imported
   by bare name, several lazily, so PyInstaller needs them as hidden imports).
5. Add a `.gitkeep` to a new `output/<name>/` folder and whitelist it in
   `.gitignore`.
6. Document it in the table at the top of this file.

## Adding a New Consolidator

Consolidators split two ways. The three **XLSX** reports (Ramp Detail, Highway
Sequence, Highway Log) are near-identical — one sheet, a header row, then data —
so they are thin wrappers over `consolidate_xlsx_base.consolidate_xlsx`,
parameterized by input dir / sheet name / output name / friendly name (a fix to
the combined layout benefits all three at once). The **Ramp Summary**
consolidator stays standalone: it parses PDFs with report-specific column/wrap
logic that must not leak into the others.

**For another XLSX report** (the common case): create
`scripts/consolidate_<name>.py` like `consolidate_highway_log.py` — set
`INPUT_DIR`, `OUT_PATH`, `SHEET_NAME` (exact export sheet name), `REPORT_NAME`,
and a `consolidate(events, confirm_overwrite)` that calls `consolidate_xlsx(...)`
with a `title`; keep the `OUT_PATH` module attribute (the GUI reads it).

**For a genuinely different input format** (like the PDF Ramp Summary): write a
standalone file exposing the same `consolidate(events=None, confirm_overwrite=
None) -> ConsolidateResult` contract — console-free (log via `events.on_log`, ask
before overwrite via `confirm_overwrite(path) -> bool`, honor
`events.is_cancelled()`, never `print`/`input`/`sys.exit`), guard third-party
imports with a `_DEPS_OK` flag, build openpyxl style objects inside functions,
and surface the "open in Excel" `PermissionError` as an `error` result.

Then, for either kind:
1. Add `if __name__ == "__main__": from cli import run_consolidate_cli;
   run_consolidate_cli(consolidate)` so the `.bat` flow keeps working.
2. Turn the branch in `4. consolidate (combine reports).bat` into a real call.
3. List the module(s) in `APP_MODULES` in `build/app.spec`, add one entry to
   `CONSOLIDATE_REPORTS` in `scripts/reports.py` (feeds the GUI Consolidate tab),
   and document it here.

## Build & Packaging (portable onefolder)

Run from the repo root: `powershell -ExecutionPolicy Bypass -File build\build.ps1`

`build.ps1` is the single reproducible build:
1. Creates `build\.venv` and installs `requirements-build.txt` (pinned).
2. Runs PyInstaller with `build\app.spec` (driven by the `TSMIS_*` env vars the
   script sets), entry = `scripts\gui_main.py`, **windowed** (`TSMIS_CONSOLE=0`),
   and copies `dist_readme.txt` in as "Start Here.txt" → `dist\TSMIS Exporter\`
   (~148 MB onefolder: just the `.exe` + `_internal\`). **No browser is
   downloaded or bundled** — the app uses the machine's Edge/Chrome, so only the
   Playwright Node driver ships. Zip the folder to distribute.
   `build.ps1 -SelfTest` instead builds `full_smoke.py` with a console so the
   frozen bundle can be verified headlessly (no window, no blocking) — it
   exercises the **system browser** pdf+download, pdfplumber, openpyxl, and GUI.
3. Runs `prune_bundle.ps1` on the built bundle (see **Bundle hygiene** below) to
   strip non-runtime files / DLP-blocked content and **fail the build** if any
   remains. Final bundle ~148 MB (was ~587 with bundled Chromium).
4. **With `-SelfTest`, then actually RUNS the built self-test `.exe`** and fails
   the build on a nonzero exit — so `-SelfTest` is a real release gate over the
   *pruned, frozen* bundle, not just "it linked." (Building without running it
   would never catch a prune/exclude that broke a runtime import.)

`build\app.spec` highlights:
- `collect_all('playwright')` + Playwright's own bundled PyInstaller hooks →
  the Node driver (`node.exe`) is included. **No browser is bundled** — there is
  no `ms-playwright` data entry; the app drives system Edge/Chrome.
- `collect_data_files('pdfminer')` + `collect_all('pdfplumber'/'openpyxl')` →
  pdf/excel work when frozen (pdfminer CMap data is the classic trap).
- **`excludes=['PIL','pypdfium2','pypdfium2_raw']`** — image libraries the app
  never needs at runtime. Note: openpyxl imports **Pillow eagerly**, so in a
  normal install PIL *does* load — it is not "never imported" (`full_smoke.py`
  reports `PIL: True` against the venv). What makes excluding it safe is that the
  code paths the app uses (text/table extraction + plain workbooks, never image
  insert or `pdfplumber.to_image`) don't need it and tolerate its absence — proven
  not by the import being gone but by the **frozen self-test still passing with PIL
  excluded** (`build.ps1 -SelfTest`). Trims ~20 MB + image codecs. `cryptography`
  is a hard top-level `pdfminer` import (encrypted-PDF support) and **must stay**.
- **`.exe` trust metadata (reduce IT/Defender/DLP false-positives).** An unsigned
  PyInstaller `.exe` with no version resource, generic icon, and no manifest is
  the classic heuristic-flag pattern. The spec adds all the non-signing signals:
  a **version-info resource** built from `version.py` (CompanyName/ProductName/
  FileVersion/…), the **`build\app.ico`** icon, and **`build\app.manifest`**
  (`asInvoker` — declares *no admin* — + Win10/11 `supportedOS`). `upx=False` too
  (UPX-packed exes are themselves a common false-positive). These **reduce, not
  eliminate**, flags — **code-signing is the only complete fix** (next step when a
  cert is available). The icon was generated once with Pillow (in the build venv):
  a 256px rounded blue square + white "TS" + route-tick, saved multi-size via
  `Image.save('build/app.ico', sizes=[(16,16)…(256,256)])`; regenerate the same
  way to tweak it. The GUI also uses it as the window/taskbar icon
  (`gui_app._app_icon_path`, bundled via the spec's `datas`, best-effort).
- **Browser selection** lives in `scripts/common.launch_browser`: once per
  process it **probes** each channel — `msedge`, then `chrome` (override with the
  `TSMIS_BROWSER_CHANNEL` env var) — by launching it *headless and driving a
  page* (`_probe_channel`), so a too-new Edge that Playwright can't actually
  control is detected and it **falls through to Chrome** rather than failing.
  The validated channel is cached; if it later fails a real launch the cache is
  cleared and the chain re-resolves. If nothing works it raises
  `BrowserNotFoundError` (UI-neutral) with a message that **distinguishes
  "none installed" from "found but too new — update the tool."** No
  `PLAYWRIGHT_BROWSERS_PATH` is set — Playwright finds the Node driver relative
  to its own package, and the browser is the system one.

**Bundle hygiene (DLP + size) — `build/prune_bundle.ps1`:** two jobs — strip the
bundle to runtime-only files (smaller + smaller DLP/security surface) and **fail
the build** if anything DLP-blocked remains. Motivating case: the Playwright Node
driver ships documentation / "agent skill" files whose examples contain **test
credit-card numbers** (e.g. `driver\…\skill\references\tracing.md` →
`4111111111111111`); corporate **DLP** (Microsoft 365 / SharePoint) detects
"Credit Card Number" and **blocks** the file, so an uploaded release zip becomes
partly inaccessible. We use none of that tooling (codegen agent, trace viewer,
report dashboard) — only headless launch + `page.pdf()` and downloads.

What it **deletes** (each verified runtime-safe by `build/full_smoke.py`):
- **All prose documentation, bundle-wide:** every `*.md` / `*.markdown` / `*.rst`
  and stray `README` / `CHANGELOG` / `HISTORY` / `AUTHORS` / `CONTRIBUTING` / `NEWS`
  text **anywhere** in the bundle — not just the Playwright driver. Docs are the
  proven DLP surface (the driver's `tracing.md` carried a fake credit-card number).
  **License / notice files are kept** (`LICENSE`/`LICENCE`/`COPYING`/`NOTICE`) — OSS
  licenses legally require redistributing them, and they never carry flagged data.
- **`dist-info` METADATA is sanitized, not deleted:** each embeds the package's
  full README as its long-description body (pdfplumber's was 600+ lines). We keep
  only the RFC822 headers (so `importlib.metadata.version()` still works) and drop
  the body. Verified frozen-safe by the `-SelfTest` gate.
- **Playwright driver extras:** `*.d.ts`, the `types/` dir, and the `skill/`,
  `tools/trace/`, `tools/dashboard/`, `vite/` dirs (~5 MB). Core files (`cli.js`,
  `lib/`, `node.exe`, …) are kept.
- **Chromium locales (defensive no-op now):** would keep only `en-US.pak` — but no
  browser is bundled, so this does nothing today. Kept in case one ever is again.
- **Image libs (safety net for the spec excludes):** any `PIL`/`pypdfium2`/
  `pypdfium2_raw` dir that slipped through (normally excluded at PyInstaller time).
- **Generic dead weight:** `tests/`/`test/` dirs and `*.pyi` stubs in the bundled
  Python packages (never imported at runtime). Chromium is skipped.

What it **guards** afterward — **fails the build** if any of these remain (each
mirrors a corporate-DLP "sensitive information type", and each is tuned to avoid
false positives that would wrongly block a release):
- **Documentation:** any non-license `*.md` / `*.markdown` / `*.rst` anywhere.
- **Credit cards:** IIN prefix + canonical length + **Luhn** (so random 16-digit
  hashes in JS bundles are *not* false-positives).
- **Private keys:** PEM `-----BEGIN … PRIVATE KEY-----` blocks.
- **AWS keys:** `AKIA` + 16 base32.
- **US SSNs:** dashed, with the invalid area/group/serial ranges excluded.

The scan covers common text + source extensions (incl. `.py`, `.json`, `.js`,
`METADATA`, certs); the `ms-playwright` Chromium folder is skipped (defensive
no-op now that no browser is bundled). Re-runnable on any extracted release with
`prune_bundle.ps1 -Target "…\TSMIS Exporter"` (add `-GuardOnly` to audit without
deleting).

Runs automatically from `build.ps1`, and is **reusable on an already-built or
extracted release** to clean it in place:
`powershell -ExecutionPolicy Bypass -File build\prune_bundle.ps1 -Target "…\TSMIS Exporter"`
(add `-GuardOnly` to audit a bundle without deleting anything). Idempotent.

**The irreducible floor (~148 MB)** is the Playwright `node.exe` (~80 MB) + the
Python runtime + Tcl/Tk + the required PDF/Excel libs (`pdfminer`+`cryptography`,
`openpyxl`, `pdfplumber`). No browser ships — that was ~372 MB and is now the
machine's installed Edge/Chrome. The Node driver is required by Playwright's
Python API and can't be dropped without abandoning Playwright entirely.

When adding a dependency, keep the bundle bare-bones: prefer the minimum that
ships, add genuinely-unused transitive libs to `EXCLUDES` in `app.spec` (proving
safety by extending `full_smoke.py`), extend the prune for any new non-runtime
cruft, and let the guard catch DLP regressions. If a future Playwright bump
moves/renames the driver dirs, update `$killDirs` (the guard fails loudly first).

**Gotchas / TODO:**
- **No bundled browser → test on a clean machine:** the app needs Edge or Chrome
  installed. Target machines (Caltrans Windows) ship Edge, but if you support a
  locked-down image without it, the app shows `BrowserNotFoundError`. There's no
  Chromium download step anymore, so builds are much faster.
- **Browser/Playwright compatibility (handled gracefully):** the browser is now
  evergreen Edge/Chrome, not a pinned Chromium. CDP is stable so ordinary Edge
  updates keep working, and `launch_browser` is defensive: it **probes** Edge
  (launch headless + drive a page) and, if a too-new Edge can't be controlled,
  **falls back to Chrome**; only if *both* fail does it raise
  `BrowserNotFoundError` with a "your browser may be too new — update the tool"
  message (vs. "install a browser"). So a routine Edge update won't break the
  app; only a very major Chromium-wide change affecting **both** Edge and Chrome
  would — at which point bump `playwright` in `requirements*.txt` and rebuild.
- **Entry point (done):** `build.ps1` builds `scripts\gui_main.py` windowed;
  `app.spec` puts `scripts\` + the repo root on `pathex` and lists the flat app
  modules (`APP_MODULES`) as hidden imports (several are imported lazily, so
  static analysis alone can miss them). Tkinter is collected automatically.
  Verify a frozen build headlessly with `build.ps1 -SelfTest` (the frozen GUI
  self-test passed; the live windowed launch is the remaining manual check).
- **AV / SmartScreen / IT data-protection:** the unsigned `.exe` can trip
  SmartScreen / Defender / corporate DLP heuristics on first run. The build now
  ships the non-signing trust signals that reduce this (version-info resource,
  icon, `asInvoker` manifest, no UPX — see the `app.spec` highlights) and
  `prune_bundle.ps1` strips DLP-blocked content. **Code-signing remains the only
  complete fix** (Phase 6). Until then, tell users to "unblock" the downloaded
  zip (right-click → Properties → Unblock) before extracting, and choose
  "More info → Run anyway" on the first launch.

## Error Handling & Reliability (Phase 5)

- **File logging:** `logging_setup.setup_logging()` — called by every entry
  point (`gui_main`, `cli.run_cli`/`run_consolidate_cli`, `login`) — installs a
  rotating handler at `LOG_DIR/tsmis.log` (5 × 2 MB). File-only, so it never
  interferes with the console flow or the windowed GUI. The export engine logs
  lifecycle, per-route outcomes, and full tracebacks (`log.exception`).
- **Preflight check:** `common.preflight(page, label)` runs after login and
  before the route loop; it selects the report and confirms the Route control +
  Generate button exist, raising **`PreflightError`** (UI-neutral message) if
  TSMIS appears to have changed — so the run fails fast with one clear error
  instead of every route failing cryptically. Surfaced by `cli.py` and the GUI
  like `AuthError`.
- **Site-error fast-fail:** the TSMIS site can render a fatal error for a single
  route (its `#rampResults` gets an `error` class, e.g. *"Cannot read properties
  of undefined (reading 'size')"*) with **no** Export button and **no** "no
  results" text. The post-Generate wait now ORs in a shared error check
  (`common.ERROR_JS`) so it resolves in seconds, and `_attempt_route` raises
  **`ReportError`** with the site's message (`common.report_error_text`). The loop
  records it `failed` immediately (with the message + a failure screenshot), no
  in-loop retry — so such a route no longer silently burns the full per-route
  timeout *and then* the long retry just "sitting" there. The end-of-run retry
  still gives it one quick second chance in case it was transient. Detection is
  generic (the `error` class is shared by every report), so it covers all of them.
- **Auto-retry once (in-loop):** a transient (non-timeout) route error is retried
  a single time after `_recover()` re-arms the form (`RETRY_COUNT`, default 1). A
  hard **timeout is not retried in-loop** (the user already had a skip window
  during it).
- **End-of-run retry pass:** whatever is still in `result.failed` after the main
  run gets one slow, **serial** retry with a generous timeout — including a
  timed-out route, which the in-loop retry deliberately skips. See **Retrying
  Failed Routes**. This is the catch-all for big reports that lost to server load
  (especially in fast mode).
- **Failure screenshots:** when a route ultimately fails, `_capture_failure()`
  writes `<report>_route_<route>_<ts>.png` + `.html` to `FAILURES_DIR`
  (best-effort; a capture error never masks the real one). Invaluable when a
  selector breaks.
- **Missing/corrupted auth file:** `require_valid_auth()` raises `AuthError`
  before any browser launches; the driver clears the file and guides re-login.
- **Session expiry mid-run:** `_recover()` raises `AuthError` if the session is
  gone, stopping the run cleanly (browser closed in a `finally`).

## Run Report (per-route outcomes)

Each export records every route's outcome (`saved` / `empty` / `skipped` /
`failed` / `exists`) in `RunResult.per_route` (via `exporter._record`, which
also notifies the UI). At the end of a run the engine **auto-saves** a CSV to
`output/run_reports/<report>_run_<ts>.csv` (`run_report.write_run_report`); the
path is stored in `RunResult.report_path` and logged. The GUI's **"Save run
report…"** button (Export tab, enabled once a run has completed) writes a copy
wherever the user picks. Columns: `Report, Route, Status` (friendly label),
`Run At` — CSV so it opens in Excel and aggregates easily across runs.

## Development Conventions

- **Two run modes share one core.** The `.bat` console flow and the GUI both
  call the same console-free engine; only `cli.py` and the GUI (`gui_*.py`)
  touch `print`/`input`/`msvcrt`/widgets. Keep new core code console-free —
  report via `Events`, raise exceptions; never `print`/`input`/`sys.exit` in
  `common.py`/`exporter.py`/consolidator cores.
- **User-facing messages must be UI-neutral.** Strings the core returns or
  raises (`ConsolidateResult.message`, `AuthError` reasons) are shown in *both*
  the console and the GUI, so they must not assume one UI — no ".bat" filenames,
  "menu option N", or "this window" wording. State the problem plus a neutral
  next step ("Export the X report first, then consolidate."). UI-specific
  guidance ("click Log in" vs. running the login BAT) belongs in the driver
  (`cli.py` or the GUI), not the core.
- **Runtime deps are pinned** in `requirements.txt` (and the setup BAT for the
  end-user flow). No browser is bundled — the app uses the system Edge/Chrome.
- **End-user setup uses no venv** (global `pip` via the setup BAT). The
  **build** uses an isolated `build\.venv` created by `build.ps1`.
- **Sync Playwright API** (not async) — one sequential worker.
- **No tests** — true verification is a live export against TSMIS (needs
  login), or running a consolidator over existing per-route files.
  Module imports/behavior can be sanity-checked with the build venv Python
  (`build\.venv\Scripts\python.exe`) without a login.

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR: Playwright is not installed` | Setup not run | Run `1. setup (one time).bat` |
| `NO SAVED SESSION FOUND` in BAT menu | `tsmis_auth.json` missing | Run `2. login (update login).bat` |
| `LOGIN PROBLEM — ...` | Session missing/expired/corrupt (`AuthError`) | Run `2. login (update login).bat` |
| Route keeps timing out | TSMIS server slow | Increase `REPORT_TIMEOUT_MS` in `common.py` |
| One route fails instantly with a "TSMIS site error" (e.g. "Cannot read properties of undefined") | The site itself can't build that route | Expected — the route is recorded `failed` with the message (see `FAILURES_DIR`); it's a TSMIS data/site issue, not the exporter |
| County dropdown timeout | Slow network | Increase `COUNTY_ENABLE_TIMEOUT_MS` in `common.py` |
| Output looks wrong for one report only | That report's selector changed | Edit only that report's `ReportSpec` in its `export_*.py` |
| "TSMIS page looks different than expected" | Preflight failed — site likely changed | Check `LOG_DIR` + `FAILURES_DIR`; update selectors in `common.py`/the `ReportSpec` |
| "No compatible web browser was found" (`BrowserNotFoundError`) | Neither Edge nor Chrome is installed/launchable | Install Microsoft Edge (or set `TSMIS_BROWSER_CHANNEL`); see `common.launch_browser` |
| Browser launch fails only after an Edge/Chrome auto-update | Evergreen browser outran the pinned Playwright CDP | Bump `playwright` in `requirements*.txt` and rebuild |
| DLP/SharePoint blocks a file in the release ("Credit Card Number") | Playwright driver docs (e.g. `tracing.md`) bundled | `build.ps1` now prunes them; clean an existing release with `build\prune_bundle.ps1 -Target "…\TSMIS Exporter"`, then re-zip |
| Build fails: "GUARD FAILED: … credit-card-like number" | A bundled dep shipped DLP-blocked content | Extend `$killDirs` in `prune_bundle.ps1` to drop the offending non-runtime files |

## Git Conventions

- **Never commit** `scripts/tsmis_auth.json` (live auth tokens). It is
  git-ignored.
- **Don't commit generated files** under `output/`, nor build artifacts
  (`build/.venv`, `build/ms-playwright`, `build/pyi-work`, `dist/`). Only the
  five `output/.gitkeep` stubs are tracked there. The local `.claude/` permission
  state is git-ignored too.
- Track the build *infra* (`build/build.ps1`, `build/prune_bundle.ps1`,
  `build/app.spec`, `build/full_smoke.py`, `build/app.ico`, `build/app.manifest`),
  `requirements*.txt`, and `version.py`.
- Commit messages should be short and imperative (e.g., `add route 395`,
  `decouple export engine from console`).
