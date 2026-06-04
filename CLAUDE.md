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
| 3a | Decouple export engine from console (`events`/`exporter`/`cli`) | ✅ done — **live TSMIS test pending** |
| 3b | Make the 3 consolidators importable (return results, no `print`/`exit`) | ⬜ **next** |
| 4 | Build the GUI on the decoupled core | ⬜ |
| 5 | Reliability (logging, failure screenshots, preflight, retry) | ⬜ |
| 6 | Package the real GUI app + zip; optional code-signing | ⬜ |

**⚠ Pending verification:** Phase 3a was checked by unit-level tests (every
module imports; generated `wait_js`/filenames are byte-identical to the
originals; `AuthError` is raised before any browser launches) but **NOT** by a
live export against TSMIS, which needs an SSO+MFA login. Before trusting 3a,
run `3. run_export (main script).bat`, log in, and confirm a few routes export
for each report type.

**Build the portable app:** from the repo root run
`powershell -ExecutionPolicy Bypass -File build\build.ps1`. See the
**Build & Packaging** section for what it does and known gotchas.

## Repository Layout

```
.
├── 1. setup (one time).bat            # pip install playwright + parsers + chromium
├── 2. login (update login).bat        # captures auth session
├── 3. run_export (main script).bat    # auth check + menu + run chosen exporter
├── 4. consolidate (combine reports).bat  # menu + run chosen consolidator
├── requirements.txt                   # pinned runtime deps (playwright, pdfplumber, openpyxl)
├── requirements-build.txt             # build deps (-r requirements.txt + pyinstaller)
├── version.py                         # app name/version + pinned Playwright/Chromium rev
├── scripts/
│   ├── paths.py                       # frozen-aware paths (output/auth/logs/config); option A
│   ├── common.py                      # URL, ROUTES, timeouts, auth + nav helpers, AuthError
│   ├── events.py                      # Events sink + RunResult (engine <-> UI seam)
│   ├── exporter.py                    # shared export engine + ReportSpec + save strategies
│   ├── cli.py                         # console adapter (keeps the .bat flow working)
│   ├── login.py                       # writes the auth file (headed browser)
│   ├── export_ramp_summary.py         # thin: a ReportSpec (PDF) + run_cli
│   ├── export_ramp_detail.py          # thin: a ReportSpec (XLSX download) + run_cli
│   ├── export_highway_sequence.py     # thin: a ReportSpec (XLSX download) + run_cli
│   ├── consolidate_ramp_summary.py    # PDFs  -> one XLSX (audit cols)  [not yet refactored — Phase 3b]
│   ├── consolidate_ramp_detail.py     # XLSXs -> one XLSX (adds Route)  [not yet refactored — Phase 3b]
│   └── consolidate_highway_sequence.py # XLSXs -> one XLSX (adds Route)  [not yet refactored — Phase 3b]
├── build/                             # portable-build infra (Phase 0)
│   ├── build.ps1                      # one-command reproducible onefolder build
│   ├── app.spec                       # PyInstaller spec (bundles Chromium + pdf/excel)
│   ├── smoke_entry.py                 # interim packaged entry / build self-test
│   ├── .venv/                         # build venv (git-ignored)
│   └── ms-playwright/                 # bundled Chromium, downloaded by build.ps1 (git-ignored)
├── dist/                              # build output: dist/TSMIS Exporter/ (git-ignored)
├── output/                            # folder structure tracked, contents ignored
│   ├── ramp_summary/  ramp_detail/  highway_sequence/  consolidated/
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
   checks the auth file exists, shows a menu, runs the selected exporter
   headlessly over every route.
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
  `LOG_DIR`, `CONFIG_FILE`. In dev it preserves the original layout
  (`./output`, `scripts/tsmis_auth.json`); when frozen it resolves next to the
  `.exe` with a `%LOCALAPPDATA%` fallback.
- **`scripts/common.py`** — shared, console-free helpers: `URL`, `ROUTES`,
  timeout constants, `AuthError`, `clear_auth()`, `require_valid_auth()`
  (raises `AuthError`), `navigate_with_auth`, `is_logged_in`, `select_report`,
  `wait_with_skip_option(page, js, prefix, events, ...)`, `new_authed_browser`
  (launches Chromium with `channel="chromium"`). Re-exports `AUTH`/`OUTPUT_ROOT`
  from `paths.py`.
- **`scripts/events.py`** — `Events` (callbacks `on_log`, `on_route`,
  `should_skip`, `is_cancelled`; all default to no-ops) and `RunResult`. The
  seam between the engine and its driver (console or GUI).
- **`scripts/exporter.py`** — the **one** proven per-route loop,
  `run_export(spec, events)`, plus `ReportSpec`, the reusable save strategies
  `save_pdf_letter` / `save_via_export_button`, and `_recover()`.
- **`scripts/cli.py`** — console adapter: `run_cli(spec, title)` wires `Events`
  to `print()`/`msvcrt` and renders `AuthError` like the old `handle_bad_auth`
  (message + clear file + exit). This is what keeps the `.bat` flow working.
- **`scripts/export_*.py`** — now ~33-line files: each defines a `ReportSpec`
  and calls `run_cli`.

**Why a shared loop now?** The old design kept a full copy of the loop in each
`export_*.py` to isolate report bugs. The refactor preserves that isolation by
moving each report's *differences* into a `ReportSpec` (label, output
filename, post-Generate `wait_js`, `is_empty` check, `save` strategy) — the
per-report data stays isolated, but the proven loop, recovery, and skip/cancel
logic live in one place so the GUI can call a single function.

## Configurable Constants (in `scripts/common.py`)

| Constant | Default | Purpose |
|---|---|---|
| `REPORT_TIMEOUT_MS` | `360_000` (6 min) | Hard ceiling for a single report. Some routes (e.g. Route 5 Ramp Detail) legitimately take minutes. |
| `SKIP_PROMPT_AFTER_MS` | `60_000` (1 min) | Soft timer: after this, a "still working" status is emitted and the skip escape-hatch opens. |
| `COUNTY_ENABLE_TIMEOUT_MS` | `60_000` (60 s) | Max wait for the county dropdown to enable. |

Increase these if the TSMIS server is slow.

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

## Resume / Idempotency

`run_export` checks `if out_path.exists(): continue` before each route, so
re-running after an interruption safely skips already-downloaded files. Delete
specific files from an `output/<report>/` folder to force a re-download.

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

> Phase 3b will convert the consolidators to be importable (return a result
> object + a confirm callback instead of `print`/`input`/`sys.exit`) so the GUI
> can drive them. Until then they remain self-contained console scripts.

Each consolidator is self-contained — parsing logic and Excel writing live
together in one `scripts/consolidate_<name>.py`. Don't share parser helpers
between consolidators; each input format (PDF vs XLSX) and report's quirks
differ enough that sharing introduces cross-report bugs.

1. Create `scripts/consolidate_<name>.py`:
   - Read inputs from `OUTPUT_ROOT / "<name>"`.
   - Write to `OUTPUT_ROOT / "consolidated" / "<name>_consolidated.xlsx"`.
   - Wrap third-party imports (`pdfplumber`, `openpyxl`) in
     `try/except ImportError` directing the user to re-run setup.
   - Print a brief progress line per file plus a summary.
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
   script sets) → `dist\TSMIS Exporter\` (~581 MB onefolder). Zip it to
   distribute.

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
- **Entry point:** currently `TSMIS_ENTRY=build\smoke_entry.py` (a self-test).
  Phase 4 will point it at the GUI entry and set `TSMIS_CONSOLE=0` (windowed).
- **AV / SmartScreen:** the unsigned `.exe` will trip SmartScreen on first run.
  Code-signing (Phase 6) is the fix; otherwise tell users to "unblock" the
  downloaded zip (right-click → Properties → Unblock) before extracting.

## Error Handling Patterns

- **Missing/corrupted auth file:** `require_valid_auth()` raises `AuthError`
  (before any browser launches); `cli.py` clears the file and prints next
  steps.
- **Per-route timeout or DOM error:** the route is added to
  `RunResult.failed`; `_recover()` re-navigates and re-arms the form so later
  routes still run.
- **Session expiry mid-run:** `_recover()` checks `is_logged_in()` and raises
  `AuthError` if the session is gone, stopping the run cleanly (browser closed
  in a `finally`).

## Development Conventions

- **Two run modes share one core.** The `.bat` console flow and the (planned)
  GUI both call the same console-free engine; only `cli.py` (and later the
  GUI) touch `print`/`input`/`msvcrt`. Keep new core code console-free —
  report via `Events`, raise exceptions; never `print`/`input`/`sys.exit` in
  `common.py`/`exporter.py`/consolidator cores.
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
