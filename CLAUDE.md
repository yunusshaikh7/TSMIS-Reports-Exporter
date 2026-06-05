# CLAUDE.md — TSMIS Reports Exporter

## Project Purpose

A unified Windows desktop tool that bulk-exports TSMIS (Caltrans
Transportation System Management Information System) reports for every
California state route. The user picks which report to export from a
menu; one shared login serves every report type.

Currently supported reports:

| Choice | Report | Output format | Output folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/ramp_summary/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/ramp_detail/` |
| 3 | Highway Sequence Listing | XLSX | `output/highway_sequence/` |

This repo combines the previously separate
`TSMIS-Reports-Export-ALL-Ramp-Summary` and
`TSMIS-Reports-Export-ALL-Ramp-Detail` projects.

## Desktop App Conversion — Status & Resume Point

> **This project is mid-conversion** from `.bat`-launched scripts into a
> **portable, single-folder Windows desktop app** (bundled Python +
> dependencies + Chromium, a GUI, **no installer**, no Python required on the
> target PC). The conversion is **additive** — the original `.bat` workflow
> still works at every step. **If you are a new session, read this section
> first.**

**End goal:** non-technical office staff unzip one folder and double-click an
`.exe` — no setup, no console login. Distributed as a plain zip.

**Locked decisions:**
- **Packaging:** PyInstaller **onefolder** (not onefile), shipped as a
  **portable zip** (no installer).
- **Browser:** bundle **full Chromium only** and launch headless via
  `channel="chromium"` (new headless mode), so `chrome-headless-shell` need
  not be bundled. Verified that `page.pdf()` (Ramp Summary) works this way.
- **Data location — "option A" (portable, never breaks):** the packaged app
  writes `output/`, the auth token, logs, and config **next to the `.exe`**,
  auto-falling back to `%LOCALAPPDATA%\TSMIS Exporter` if that folder is
  read-only. Implemented in `scripts/paths.py`.
- **GUI (planned, Phase 4):** Tkinter (+ optional theme). A worker thread owns
  the Playwright session and talks to the UI through the `Events` callbacks
  (`scripts/events.py`).

**Pinned versions — must move together (see `version.py`):**
- `playwright==1.60.0` ↔ **Chromium rev 1223** (Chrome for Testing 148.0.7778.96)
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
`dist\TSMIS Exporter\` (~589 MB; double-click `TSMIS Exporter.exe`). Add
`-SelfTest` for a headless console build that verifies the frozen bundle without
launching a window. See **Build & Packaging** for details and gotchas.

## Repository Layout

```
.
├── 1. setup (one time).bat            # pip install playwright + parsers + chromium
├── 2. login (update login).bat        # captures auth session
├── 3. run_export (main script).bat    # auth check + menu + run chosen exporter
├── 4. consolidate (combine reports).bat  # menu + run chosen consolidator
├── 5. fast export (experimental).bat  # parallel multi-browser export (sets TSMIS_FAST_WORKERS)
├── run app (GUI preview).bat          # dev launcher for the desktop GUI (Phase 4)
├── requirements.txt                   # pinned runtime deps (playwright, pdfplumber, openpyxl)
├── requirements-build.txt             # build deps (-r requirements.txt + pyinstaller)
├── version.py                         # app name/version + pinned Playwright/Chromium rev
├── scripts/
│   ├── paths.py                       # frozen-aware paths (output/auth/logs/failures/config); option A
│   ├── logging_setup.py               # rotating file log under LOG_DIR (all entry points call it)
│   ├── common.py                      # URL, ROUTES, timeouts, auth + nav helpers, AuthError, preflight
│   ├── events.py                      # Events sink + RunResult + ConsolidateResult (engine <-> UI seam)
│   ├── exporter.py                    # shared export engine + ReportSpec + save strategies
│   ├── exporter_parallel.py           # EXPERIMENTAL fast mode: N browsers in parallel; reuses exporter.py
│   ├── run_report.py                  # per-route run report (CSV; auto-saved each run)
│   ├── cli.py                         # console adapter (keeps the .bat flow working)
│   ├── login.py                       # writes the auth file (headed browser)
│   ├── export_ramp_summary.py         # thin: a ReportSpec (PDF) + run_cli
│   ├── export_ramp_detail.py          # thin: a ReportSpec (XLSX download) + run_cli
│   ├── export_highway_sequence.py     # thin: a ReportSpec (XLSX download) + run_cli
│   ├── consolidate_ramp_summary.py    # PDFs  -> one XLSX (audit cols); importable consolidate()
│   ├── consolidate_ramp_detail.py     # XLSXs -> one XLSX (adds Route);  importable consolidate()
│   ├── consolidate_highway_sequence.py # XLSXs -> one XLSX (adds Route);  importable consolidate()
│   ├── gui_main.py                    # GUI entry point (sets browser path, launches App)
│   ├── gui_app.py                     # main window (Tk): header, Export/Consolidate tabs, log
│   ├── gui_worker.py                  # worker threads: Export/Consolidate/Login (Events -> queue)
│   └── gui_theme.py                   # palette/fonts/ttk styles (clam base)
├── build/                             # portable-build infra (Phase 0)
│   ├── build.ps1                      # one-command reproducible onefolder build (-SelfTest for headless verify)
│   ├── app.spec                       # PyInstaller spec (Chromium + pdf/excel + flat app modules)
│   ├── gui_main entry → scripts/gui_main.py  # the windowed app's real entry point
│   ├── gui_smoke_entry.py             # headless frozen-GUI self-test (built by -SelfTest)
│   ├── smoke_entry.py                 # standalone non-GUI bundle self-test (playwright/pdf/excel)
│   ├── dist_readme.txt               # copied into the build as "Start Here.txt"
│   ├── .venv/                         # build venv (git-ignored)
│   └── ms-playwright/                 # bundled Chromium, downloaded by build.ps1 (git-ignored)
├── dist/                              # build output: dist/TSMIS Exporter/ (git-ignored)
├── output/                            # folder structure tracked, contents ignored
│   ├── ramp_summary/  ramp_detail/  highway_sequence/  consolidated/
│   └── run_reports/                   # auto-saved per-route CSV reports (created on demand)
├── .gitignore
└── CLAUDE.md
```

`scripts/tsmis_auth.json` (auth cookies) is git-ignored. The four `output/`
subfolders are committed (via empty `.gitkeep` files) so the scripts always
have a place to write, but generated files inside them are git-ignored — they
can be gigabytes. Build artifacts (`build/.venv`, `build/ms-playwright`,
`build/pyi-work`, `dist/`) are git-ignored.

## Technology Stack

| Component | Detail |
|---|---|
| Language | Python 3.11 (stdlib + Playwright + pdfplumber + openpyxl) |
| Browser automation | `playwright` (sync API, Chromium, `channel="chromium"`) |
| PDF parsing | `pdfplumber` (consolidators only) |
| Excel writing | `openpyxl` (consolidators only) |
| Packaging | PyInstaller (onefolder, portable) |
| GUI (planned) | Tkinter |
| Target application | `https://rhansonrizing.github.io/tsmis_reports/index.html` |
| Auth mechanism | ArcGIS / Caltrans Azure AD (SSO + MFA) |
| Session persistence | Playwright `storage_state` → `tsmis_auth.json` |
| OS | Windows (`.bat` launchers + packaged build); Python core is OS-agnostic |

## Workflow for End Users (current `.bat` flow)

1. **Setup (once per machine):** Double-click `1. setup (one time).bat` —
   installs Playwright + pdfplumber + openpyxl and downloads Chromium.
2. **Login (once, or when the session expires):** Double-click
   `2. login (update login).bat` — opens a visible browser, the user
   completes SSO + MFA, then presses Enter to save the session into
   `scripts/tsmis_auth.json`. The same file is used by every export script.
3. **Export (repeatable):** Double-click `3. run_export (main script).bat` —
   checks the auth file exists, shows a menu, asks which routes to export (press
   Enter for all, or list specific ones), then runs the selected exporter
   headlessly over those routes.
4. **Consolidate (optional, repeatable):** Double-click
   `4. consolidate (combine reports).bat` — pick one report type and combine
   every per-route export into a single workbook under `output/consolidated/`.

> The packaged GUI app (Phase 4) will replace steps 2–4 with buttons, but the
> `.bat` flow remains for development and as a fallback.

## How the Menu Works

`3. run_export (main script).bat`:

1. Checks that `scripts\tsmis_auth.json` exists — if not, instructs the user
   to run the login BAT first and exits.
2. Shows a numbered menu:
   - `1` → `python scripts\export_ramp_summary.py`
   - `2` → `python scripts\export_ramp_detail.py`
   - `3` → `python scripts\export_highway_sequence.py`
   - `Q` → quit
3. Invalid choices loop back to the menu.
4. After a report is chosen, the Python entry point (`run_cli`) prompts for the
   routes to export — Enter (or empty) means **all routes**; otherwise type a
   list like `5, 99, 101` (any casing / zero-padding, suffixes like `101U` ok).
   The same prompt backs the fast-mode BAT. See **Selecting Which Routes to
   Export**.

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
  timeout constants, `AuthError`, `clear_auth()`, `require_valid_auth()`
  (raises `AuthError`), `navigate_with_auth`, `is_logged_in`, `select_report`,
  `wait_with_skip_option(page, js, prefix, events, ...)`, `new_authed_browser`
  (launches Chromium with `channel="chromium"`), and the route-selection
  parsers `normalize_route` / `parse_routes` (free-text → validated route list
  in `ROUTES` order; raise a UI-neutral `ValueError` on bad/empty input).
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
  `run_cli(spec, title)` for exports (wires `Events` to `print()`/`msvcrt`,
  prompts for the route subset via `_resolve_routes_console` (Enter = all; also
  honors the `TSMIS_ROUTES` env var) and passes `routes=` to the engine,
  renders `AuthError` like the old `handle_bad_auth`) and
  `run_consolidate_cli(consolidate_fn)` for consolidators (wires `on_log` to
  `print`, the overwrite prompt to `input()`, maps the `ConsolidateResult`
  status to the exit code). Imports `exporter` lazily so consolidating never
  pulls in Playwright.
- **`scripts/export_*.py`** — now ~33-line files: each defines a `ReportSpec`
  and calls `run_cli`.
- **`scripts/consolidate_*.py`** — each exposes `consolidate(events,
  confirm_overwrite) -> ConsolidateResult` (console-free: logs via `Events`,
  asks before overwrite via the callback, honors `is_cancelled()`, never
  `print`/`input`/`exit`) plus a `__main__` that calls `run_consolidate_cli`.
  Third-party imports are guarded with a `_DEPS_OK` flag and openpyxl style
  objects are built inside functions, so the modules import cleanly even if a
  dependency is missing — the GUI gets a clean error `ConsolidateResult` instead
  of a fatal `ImportError`. Still one self-contained file per report (no shared
  parser helpers).

**GUI (Phase 4) — `scripts/gui_*.py`** (built on the same console-free core):
- `gui_main.py` — entry point. Sets `PLAYWRIGHT_BROWSERS_PATH` when frozen and
  the dev import paths, then runs `App().mainloop()`.
- `gui_app.py` — the `App(tk.Tk)` window: header (session dot + Log in button),
  an Export/Consolidate **notebook**, a shared progress bar + counts + log pane,
  and a footer (output path + Open folder). The Export tab has a **Routes** entry
  (blank = all; or type/`Choose…` a subset via `parse_routes`) passed to
  `ExportWorker(..., routes=...)`. Drains the worker queue via `after(100)`; it
  never does browser/file work itself.
- `gui_worker.py` — `ExportWorker` / `ConsolidateWorker` / `LoginWorker` threads.
  They drive the engines through `Events`, posting `(kind, payload)` messages to
  a `queue.Queue`. Skip/Cancel are `threading.Event`s; login waits on a `done`
  event set by the "I've finished logging in" button (replacing `login.py`'s
  console `input()`s).
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
(`cli.py`) this is the `S` key (Windows `msvcrt`); in the GUI it will be a Skip
button. Mechanically, `wait_with_skip_option` polls `events.should_skip()`:

1. Waits up to `SKIP_PROMPT_AFTER_MS` silently.
2. After that, emits a status line every ~30 s and watches for a skip request.
3. If skipped, the route is recorded in `RunResult.user_skipped`, the form is
   re-armed (`_recover`), and the loop continues.
4. If nothing is requested and `REPORT_TIMEOUT_MS` elapses, the route is added
   to `failed` and the loop recovers as usual.

Re-run later and the loop retries any routes without an output file.

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
- **Per-route Skip is disabled** during the parallel phase (ambiguous with
  several routes in flight) — use **Cancel** to stop the whole run. (The serial
  retry phase is one-at-a-time, so the console `S` key works again there.)
- **Threading:** Playwright's sync API is thread-affine, so each worker owns its
  own `sync_playwright()` + browser + context + page and never shares a
  Playwright object across threads. Per-worker `RunResult`s are merged at the
  end; the only locked hot-path state in the GUI is the progress tally
  (`ExportWorker._tally_lock`).

**How many browsers? (`DEFAULT_WORKERS=3`, `MAX_WORKERS=30` in
`exporter_parallel.py`)** The TSMIS/Caltrans backend handles high concurrency
fine (operator-tested), so the practical limit is the **client PC, not the
server**: each worker is one Chromium process (~300–500 MB under load) plus a
Playwright driver. Rule of thumb: **3 = safe default (~2.5–3× faster), 8–12 =
big speedup on a healthy multi-core PC, 30 = hard cap** (~9–15 GB RAM for
browsers alone — only on a well-resourced machine). Budget ~0.5 GB RAM per
worker and leave headroom; requested counts are clamped to `[1, MAX_WORKERS]`.

**How to turn it on:**
- **Console / .bat:** `5. fast export (experimental).bat` asks how many browsers,
  sets the `TSMIS_FAST_WORKERS` env var, then shows the usual report menu. (Any
  flow that runs an `export_*.py` honors `TSMIS_FAST_WORKERS`; `run_cli` routes
  to the parallel engine when it is > 1 — the thin exporters are unchanged.)
- **GUI:** an "⚡ Fast mode (experimental)" checkbox + worker-count spinner on the
  Export tab; `start_export` passes the count to `ExportWorker(..., workers=N)`.

## Auth / Session Details

- `scripts/login.py` writes the auth file via `ctx.storage_state(path=...)`
  (path from `paths.AUTH`).
- The engine calls `require_valid_auth()` first (file exists + valid JSON),
  then `new_authed_browser()` restores the session via
  `browser.new_context(storage_state=...)`.
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
2. Add a numbered branch to `3. run_export (main script).bat`.
3. Add a `.gitkeep` to a new `output/<name>/` folder and whitelist it in
   `.gitignore`.
4. Document it in the table at the top of this file.

## Adding a New Consolidator

Each consolidator is self-contained — parsing logic and Excel writing live
together in one `scripts/consolidate_<name>.py`. Don't share parser helpers
between consolidators; each input format (PDF vs XLSX) and report's quirks
differ enough that sharing introduces cross-report bugs.

1. Create `scripts/consolidate_<name>.py` modeled on an existing one:
   - Expose `consolidate(events=None, confirm_overwrite=None) -> ConsolidateResult`.
     Read inputs from `OUTPUT_ROOT / "<name>"`, write to
     `OUTPUT_ROOT / "consolidated" / "<name>_consolidated.xlsx"`.
   - Keep it console-free: log progress via `events.on_log`, ask before
     overwriting via `confirm_overwrite(path) -> bool`, honor
     `events.is_cancelled()`, and return a `ConsolidateResult`. Never
     `print`/`input`/`sys.exit` here.
   - Guard third-party imports with a `_DEPS_OK` flag (don't `sys.exit` on
     `ImportError`) and build any openpyxl style objects inside functions, so
     the module stays importable when frozen or when a dep is missing.
   - Surface the "file open in Excel" `PermissionError` as an `error` result.
   - Add `if __name__ == "__main__": from cli import run_consolidate_cli;
     run_consolidate_cli(consolidate)` so the `.bat` flow keeps working.
2. Turn the placeholder branch in `4. consolidate (combine reports).bat` into
   a real call.
3. Document it here.

## Build & Packaging (portable onefolder)

Run from the repo root: `powershell -ExecutionPolicy Bypass -File build\build.ps1`

`build.ps1` is the single reproducible build:
1. Creates `build\.venv` and installs `requirements-build.txt` (pinned).
2. Downloads the **matching** Chromium into `build\ms-playwright` (skips if
   already present), then **deletes** `chromium_headless_shell-*` and
   `ffmpeg-*` (the app runs headless via `channel="chromium"`).
3. Runs PyInstaller with `build\app.spec` (driven by the `TSMIS_*` env vars the
   script sets), entry = `scripts\gui_main.py`, **windowed** (`TSMIS_CONSOLE=0`),
   and copies `dist_readme.txt` in as "Start Here.txt" → `dist\TSMIS Exporter\`
   (~589 MB onefolder: just the `.exe` + `_internal\`). Zip it to distribute.
   `build.ps1 -SelfTest` instead builds `gui_smoke_entry.py` with a console so
   the frozen bundle can be verified headlessly (no window, no blocking).

`build\app.spec` highlights:
- `collect_all('playwright')` + Playwright's own bundled PyInstaller hooks →
  the Node driver is included.
- `collect_data_files('pdfminer')` + `collect_all('pdfplumber'/'openpyxl')` →
  pdf/excel work when frozen (pdfminer CMap data is the classic trap).
- The `ms-playwright` folder is bundled as data → `_internal/ms-playwright`.
- Entry points must set `PLAYWRIGHT_BROWSERS_PATH` to that folder **before**
  importing Playwright. For onefolder, `sys._MEIPASS` is the `_internal` dir
  (see `build/smoke_entry.py` and `scripts/paths.py` for the pattern).

**Gotchas / TODO:**
- **Version bump:** `build.ps1` reuses `build\ms-playwright` if any
  `chromium-*` folder exists. After bumping the Playwright pin, **delete
  `build\ms-playwright`** so the matching Chromium re-downloads. (Hardening
  idea: key the check on `version.py`'s `CHROMIUM_REVISION`.)
- **Entry point (done):** `build.ps1` builds `scripts\gui_main.py` windowed;
  `app.spec` puts `scripts\` + the repo root on `pathex` and lists the flat app
  modules (`APP_MODULES`) as hidden imports (several are imported lazily, so
  static analysis alone can miss them). Tkinter is collected automatically.
  Verify a frozen build headlessly with `build.ps1 -SelfTest` (the frozen GUI
  self-test passed; the live windowed launch is the remaining manual check).
- **AV / SmartScreen:** the unsigned `.exe` will trip SmartScreen on first run.
  Code-signing (Phase 6) is the fix; otherwise tell users to "unblock" the
  downloaded zip (right-click → Properties → Unblock) before extracting.

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
  end-user flow). Playwright ↔ Chromium revision must move together.
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
| County dropdown timeout | Slow network | Increase `COUNTY_ENABLE_TIMEOUT_MS` in `common.py` |
| Output looks wrong for one report only | That report's selector changed | Edit only that report's `ReportSpec` in its `export_*.py` |
| "TSMIS page looks different than expected" | Preflight failed — site likely changed | Check `LOG_DIR` + `FAILURES_DIR`; update selectors in `common.py`/the `ReportSpec` |
| Packaged `.exe`: "Executable doesn't exist ... chrome-headless-shell" | Launched without `channel="chromium"` | Ensure `new_authed_browser` uses `channel="chromium"` |
| Packaged build bundles wrong Chromium after a Playwright bump | `build\ms-playwright` was cached | Delete `build\ms-playwright` and rebuild |

## Git Conventions

- **Never commit** `scripts/tsmis_auth.json` (live auth tokens). It is
  git-ignored.
- **Don't commit generated files** under `output/`, nor build artifacts
  (`build/.venv`, `build/ms-playwright`, `build/pyi-work`, `dist/`). Only the
  four `output/.gitkeep` stubs are tracked there.
- Track the build *infra* (`build/build.ps1`, `build/app.spec`,
  `build/smoke_entry.py`), `requirements*.txt`, and `version.py`.
- Commit messages should be short and imperative (e.g., `add route 395`,
  `decouple export engine from console`).
