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
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/ramp_summary/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/ramp_detail/` |
| 3 | Highway Sequence Listing | XLSX | `output/highway_sequence/` |
| 4 | Highway Log | XLSX | `output/highway_log/` |

## Two Run Modes, One Core

The export engine is **console-free** and backs both:
- **`.bat` console flow** (development + fallback) — see *User Workflow*.
- **Packaged GUI** (`scripts/gui_*.py`, Tkinter) — the shipped desktop app.

Only `cli.py` and `gui_*.py` touch `print`/`input`/`msvcrt`/widgets. Core code
(`common.py`, `exporter.py`, consolidator cores) reports via the `Events` sink
(`scripts/events.py`) and raises exceptions — never `print`/`input`/`sys.exit`.
User-facing strings from the core must be **UI-neutral** (no ".bat" names, no
"this window" / "menu option N" — that guidance lives in the driver).

**Threading:** Playwright's sync API is thread-affine. All browser work runs on a
worker thread; only the main thread touches Tk. Workers talk to the UI through a
`queue.Queue`. In fast mode each worker owns its own Playwright/browser/context.

## The App

The product is a **portable single-folder Windows desktop app** (bundled Python +
deps + Tkinter GUI; no installer, no Python needed on target): non-technical staff
unzip one folder and double-click the `.exe`. The `.bat` console flow (below) is
retained as a development and fallback path, and runs the same core engine.

**Design decisions (don't relitigate without reason):**
- **Packaging:** PyInstaller **onefolder**, shipped as a portable zip (no installer).
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
  the bundle's own `_internal\ms-playwright` (or an explicit
  `PLAYWRIGHT_BROWSERS_PATH`) — the machine's global Playwright cache is
  deliberately ignored so the default build always defaults to Edge even on a
  dev PC; dev/`.bat` runs use the default cache (where setup downloads it).
  `channel="chromium"` runs the full browser in new-headless mode — one binary
  for headed sign-in and headless exports (no headless shell needed).
- **Data location (option A):** the packaged app writes `output/`, auth token,
  logs, and config **next to the `.exe`**, falling back to
  `%LOCALAPPDATA%\TSMIS Exporter` if read-only. See `scripts/paths.py`.

**Pinned versions (`version.py` / `requirements*.txt`):** `playwright==1.60.0`
(pins the bundled **Node driver** only — no Chromium ships), `pdfplumber==0.11.9`
(→ `pdfminer.six==20251230`), `openpyxl==3.1.5`, `pyinstaller==6.20.0`,
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
2. **`2. login (update login).bat`** — opens a visible browser (Built-in Chromium
   when present, else the persistent-profile Edge flow with Chrome fallback);
   user does SSO+MFA, then confirms to save the session to
   `scripts/tsmis_auth.json` (shared by all exports). Login is **validated
   before saving** (a real TSMIS login must be detected), so clicking "finished"
   without signing in won't save a junk session.
3. **`3. run_export (main script).bat`** — checks auth exists, shows a menu
   (`1`–`4` single report, `A` = several/all → `export_multi.py`, `Q` quit), then
   prompts for routes (Enter = all; or `5, 99, 101` — any casing/padding, suffixes
   like `101U` ok), then runs headlessly.
4. **`4. consolidate (combine reports).bat`** — pick a report type, combine all
   per-route exports into one workbook in `output/consolidated/` (no auth check).
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
  paths.py            # frozen-aware paths (option A): DATA_ROOT, OUTPUT_ROOT, AUTH, LOG_DIR, FAILURES_DIR, CONFIG_FILE
  logging_setup.py    # rotating file log under LOG_DIR (every entry point calls it)
  common.py           # URL, ROUTES, timeouts, auth+nav helpers, AuthError/RunCancelled/PreflightError/ReportError/BrowserNotFoundError,
                      #   launch_browser (probe msedge→chrome), set_preferred_channel, check_browsers, preflight, parse_routes/normalize_route
  events.py           # Events sink + RunResult (export) + ConsolidateResult
  exporter.py         # the one per-route loop: run_export(spec, events), ReportSpec, save_pdf_letter / save_via_export_button, _recover, _retry_failed_routes
  exporter_parallel.py# EXPERIMENTAL fast mode: N browsers off a shared queue; reuses exporter.py internals
  run_report.py       # per-route outcome CSV (auto-saved each run; + multi)
  cli.py              # console adapters: run_cli / run_cli_multi / run_consolidate_cli
  login.py            # writes the auth file (headed browser)
  reports.py          # SINGLE registry: EXPORT_REPORTS + CONSOLIDATE_REPORTS (GUI + export_multi read it)
  export_*.py         # thin (~30 lines): a ReportSpec + run_cli; export_multi.py = several/all
  consolidate_xlsx_base.py    # shared XLSX consolidator core
  consolidate_ramp_summary.py # standalone (parses PDFs)
  consolidate_{ramp_detail,highway_sequence,highway_log}.py  # thin wrappers over the base
  gui_main.py / gui_app.py / gui_worker.py / gui_theme.py    # GUI entry / window / worker threads / styles
build/
  build.ps1           # one-command onefolder build (-SelfTest = headless verify gate;
                      #   -BundleChromium = ship the Built-in Chromium inside the bundle)
  prune_bundle.ps1    # strip to runtime-only files + DLP guard (run by build.ps1)
  app.spec            # PyInstaller spec (Node driver + pdf/excel; excludes image libs; version-info + icon + manifest; no browser)
  release_notes.md    # body of the GitHub release (which zip to pick + highlights)
  app.ico / app.manifest / full_smoke.py / dist_readme.txt / .venv/ (git-ignored)
dist/                 # build output: dist/TSMIS Exporter/ (git-ignored)
output/               # folder structure tracked (.gitkeep); contents git-ignored
  ramp_summary/ ramp_detail/ highway_sequence/ highway_log/ consolidated/ run_reports/
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

- **Resume / idempotency:** `run_export` skips a route whose output file already
  exists. Delete a file to force re-download.
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

## Timeouts (`scripts/common.py`)

| Constant | Default | Purpose |
|---|---|---|
| `REPORT_TIMEOUT_MS` | 360_000 (6 min) | Per-route ceiling, sequential flow |
| `FAST_REPORT_TIMEOUT_MS` | 600_000 (10 min) | Per-route ceiling, fast mode (server under load) |
| `RETRY_REPORT_TIMEOUT_MS` | 900_000 (15 min) | Per-route ceiling, end-of-run retry pass |
| `SKIP_PROMPT_AFTER_MS` | 60_000 (1 min) | When the "still working" status + skip hatch open |
| `COUNTY_ENABLE_TIMEOUT_MS` | 60_000 (60 s) | Max wait for the county dropdown to enable |
| `RETRY_COUNT` | 1 | In-loop retries after a transient (non-timeout) failure |

Increase these if the TSMIS server is slow.

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

- **Sign-in browser order** (`login.py` console / `gui_worker.LoginWorker`)
  honors the user's pick first (`get_preferred_channel()` — the GUI Browser
  dropdown / `TSMIS_BROWSER_CHANNEL`; picking Chrome goes straight to Chrome).
  With no pick:
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
- The engine calls `require_valid_auth()` first — checks the file exists, is valid
  JSON, **and is shaped like a storage_state** (`cookies`/`origins` lists) — else
  raises `AuthError`. `cli.py` catches it, clears the stale file, guides re-login;
  the GUI shows a re-login dialog. The `.bat` menu also gates on the file existing.

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
- `collect_data_files('pdfminer')` + `collect_all('pdfplumber'/'openpyxl')` — the
  pdfminer CMap data is the classic frozen trap. `cryptography` is a hard pdfminer
  import and **must stay**.
- `excludes=['PIL','pypdfium2','pypdfium2_raw']` — image libs the runtime paths
  (text/table extraction + plain workbooks) don't need; proven safe by the frozen
  `-SelfTest` passing with PIL excluded.
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
audit). The ~148 MB floor is `node.exe` (~80 MB) + Python + Tcl/Tk + pdf/excel libs.

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

**Add/remove a route:** edit `ROUTES` in `common.py` (zero-padded 3-digit, optional
suffixes like `"005S"`/`"101U"` — must match the TSMIS `<select>` option values).

## Reliability

- **File logging:** `logging_setup.setup_logging()` → rotating `LOG_DIR/tsmis.log`
  (5 × 2 MB), file-only. The engine logs lifecycle, per-route outcomes, tracebacks.
- **Preflight** (`common.preflight`): after login, before the loop, confirms the
  report selects and the Route control + Generate button exist — else
  `PreflightError`, so the run fails fast with one clear error.
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
| `NO SAVED SESSION` / `LOGIN PROBLEM` (`AuthError`) | Session missing/expired/corrupt | Run `2. login…bat` |
| Route keeps timing out | TSMIS server slow | Raise `REPORT_TIMEOUT_MS` |
| Route fails instantly with a "TSMIS site error" | The site can't build that route | Expected — recorded `failed` (see `FAILURES_DIR`); a TSMIS issue |
| County dropdown timeout | Slow network | Raise `COUNTY_ENABLE_TIMEOUT_MS` |
| One report's output wrong | That report's selector changed | Edit only its `ReportSpec` |
| "page looks different than expected" | Preflight failed — site changed | Check `LOG_DIR`/`FAILURES_DIR`; update selectors |
| `BrowserNotFoundError` | No usable browser found | Install Edge, re-run `1. setup…bat` (downloads Chromium), or use the with-browser zip |
| Edge sign-in "works" but exports can't log in | Edge signed in via the Windows device broker (PRT) — session never reaches cookies | Expected & detected: the capture is rejected (`storage_state_is_portable`) and login falls back to Chrome / Built-in Chromium |
| Browser launch fails after an Edge/Chrome update | Evergreen browser outran pinned Playwright CDP | Bump `playwright` in `requirements*.txt`, rebuild |
| DLP blocks a release file ("Credit Card Number") | Playwright driver docs bundled | `build.ps1` prunes them; clean a release with `prune_bundle.ps1 -Target …` |
| Build: "GUARD FAILED" | A dep shipped DLP-blocked content | Extend `$killDirs` in `prune_bundle.ps1` |
