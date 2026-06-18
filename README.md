# TSMIS Reports Exporter

> Bulk-export Caltrans TSMIS reports for every California state route — from a single click.

[![Version](https://img.shields.io/badge/version-0.14.2-blue)](version.py)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6?logo=windows)](#)
[![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](#)
[![Automation](https://img.shields.io/badge/automation-Playwright-2EAD33?logo=microsoftedge&logoColor=white)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A portable Windows desktop tool that bulk-exports reports from the Caltrans
**Transportation System Management Information System (TSMIS)** for every
California state route. Pick the report types you want, sign in once, and the
tool walks every route for you — no copy-pasting route numbers, no babysitting
the browser.

It is distributed as a single zip — unzip, double-click, done — in two flavors:
the standard build drives the **Microsoft Edge or Google Chrome already on the
machine** (nothing extra to install), and a *with-browser* build ships its own
**Built-in Chromium** and uses it by default (Edge/Chrome stay selectable) for
PCs where managed browsers get in the way. The same engine also runs from a set
of `.bat` scripts for development and as a fallback.

---

## Table of Contents

- [Features](#features)
- [Supported reports](#supported-reports)
- [Getting started (end users)](#getting-started-end-users)
- [Usage](#usage)
- [Developer setup](#developer-setup)
- [Building the app](#building-the-app)
- [Project structure](#project-structure)
- [Tech stack](#tech-stack)
- [Known limitations](#known-limitations)
- [Contributing](#contributing)
- [License & disclaimer](#license--disclaimer)

---

## Features

- **Six report types, any combination.** Export one, several, or all at once.
- **One login for everything.** A single SSO + MFA sign-in covers every report.
- **Pick your routes.** Run all routes by default, or narrow to a subset
  (`5, 99, 101` — any casing/zero-padding, suffixes like `101U` accepted).
- **Resumable.** Re-running skips routes already on disk, so an interrupted run
  picks up where it left off.
- **Resilient.** Per-route timeouts, automatic retry of stragglers under lighter
  load, failure screenshots, and rotating logs.
- **Skip & cancel.** Skip a slow route mid-run, or cancel the whole run — the
  current route stops promptly, not after a long wait.
- **Consolidation.** Combine every per-route export into a single workbook —
  including **TSN Highway Log** district PDFs and **TSMIS Highway Log PDFs**,
  both converted into TSMIS-format Excel for side-by-side use.
- **Highway Log comparisons.** Build a discrepancy workbook from two Highway
  Logs (per-route or consolidated): matching values shown plainly, differences
  in red, live Excel formulas throughout, plus per-route coverage stats. Three
  flavors: TSMIS vs TSN, **TSMIS (PDF) vs TSN (PDF)**, and **TSMIS (PDF) vs TSMIS
  (Excel)** — the PDF-sourced ones sidestep the vendor Excel export's bug.
- **Run reports.** Every run records a per-route outcome CSV (saved / empty /
  skipped / failed).
- **Optional fast mode.** Run several browsers in parallel for a 2.5–3×+ speedup.
- **Browser, your way.** The standard download uses the machine's installed
  Edge/Chrome, keeping it small (~148 MB); the with-browser download adds a
  Built-in Chromium that works even where org-managed browsers interfere. A
  header dropdown switches between whatever is available.

## Supported reports

| Report | Output format | Output folder |
|---|---|---|
| TSAR: Ramp Summary | PDF (Letter) | `output/<date>/ramp_summary/` |
| TSAR: Ramp Detail | XLSX | `output/<date>/ramp_detail/` |
| Highway Sequence Listing | XLSX | `output/<date>/highway_sequence/` |
| Highway Log | XLSX | `output/<date>/highway_log/` |
| Intersection Summary | XLSX | `output/<date>/intersection_summary/` |
| Intersection Detail | XLSX | `output/<date>/intersection_detail/` |

The two Intersection reports are **export-only** for now (no consolidate or
compare support yet).

Consolidate-only: **TSN Highway Log** (drop district PDFs into
`input/tsn_highway_log/`) and **TSMIS Highway Log (PDF)** (drop the "Highway Log
(PDF)" route exports into `input/tsmis_highway_log_pdf/`) — both produce
TSMIS-format per-route files + one combined workbook under `output/`. The
**Compare** tab turns two Highway Logs into a formula-driven discrepancy
workbook (TSMIS vs TSN, TSMIS-PDF vs TSN-PDF, or TSMIS-PDF vs TSMIS-Excel).

<!-- Tip: drop a screenshot of the GUI here once available, e.g. ![TSMIS Exporter](docs/screenshot.png) -->

---

## Getting started (end users)

> **Requirements:** Windows 10/11 and TSMIS credentials. No Python or other
> setup needed. The standard download also needs **Microsoft Edge or Google
> Chrome** installed; the with-browser download brings its own.

1. **Download** the variant that fits from the
   [Releases page](https://github.com/yunusshaikh7/TSMIS-Reports-Exporter/releases):
   - `…-win64.zip` — standard; uses the Edge/Chrome already on the PC (smallest).
   - `…-win64-with-browser.zip` — ships its own Built-in Chromium and uses it by
     default (best on managed PCs where Edge sign-in misbehaves and Chrome
     isn't installed); Edge/Chrome remain in the header dropdown.
   - `…-batch-source.zip` — the console/`.bat` flow for developers (see
     [Developer setup](#developer-setup)).
2. **Unblock it** before extracting: right-click the zip → **Properties** →
   tick **Unblock** → **OK**. (It's an unsigned app, so Windows marks downloads
   as untrusted — see [Known limitations](#known-limitations).)
3. **Extract** the folder anywhere you can write (Desktop, Documents, a USB drive).
4. **Run** `TSMIS Exporter.exe`. On first launch, choose
   **More info → Run anyway** if SmartScreen appears.

Exports, logs, and your saved session are written **next to the `.exe`** (or under
`%LOCALAPPDATA%\TSMIS Exporter` if that folder is read-only), so the tool is fully
portable and leaves nothing behind on the system.

## Usage

1. **Log in** — click **Log in**. On managed Caltrans PCs, after your first
   Edge sign-in the tool signs in **automatically** using your Windows account
   (no password, no window) — and exports can even sign themselves in with no
   saved login. Otherwise a browser window opens: complete SSO + MFA, then
   confirm; your session is saved and reused until it expires.
2. **Export** — tick the report types, optionally enter a subset of routes
   (blank = all), and click **Start**. The header dropdowns choose the **data
   source** (SSOR / ARS) and **environment** (Prod / Test / Dev) — defaults
   SSOR + Prod. Each day's files land in their own `output/<date>/` folder.
   Progress, counts, and a live log are shown; use **Skip** for a slow route or
   **Cancel** to stop.
3. **Consolidate** *(optional)* — on the Consolidate tab, pick a report type
   (and which export day — newest by default) to combine that day's per-route
   files into one workbook under `output/<date>/consolidated/`. **TSN Highway
   Log** reads district PDFs from `input/tsn_highway_log/` instead (the pane
   shows the folder).
4. **Compare** *(optional)* — pick a TSMIS and a TSN Highway Log (per-route or
   consolidated) and get a discrepancy workbook: red `value ≠ value` cells,
   route coverage, all live formulas. Big consolidated comparisons open in
   manual calculation — press **F9** once.
5. **Save run report** *(optional)* — export a CSV of every route's outcome.

**Fast mode** (experimental): tick **⚡ Fast mode** and choose a worker count to
run several browsers in parallel. Each worker uses ~0.5 GB RAM — `3` is a safe
default; higher counts give a bigger speedup on a well-resourced PC.

---

## Developer setup

The packaged app is the product, but the same console-free engine runs from
`.bat` scripts (and plain Python) for development.

```bash
git clone https://github.com/yunusshaikh7/TSMIS-Reports-Exporter.git
cd TSMIS-Reports-Exporter
```

Then either double-click the numbered `.bat` files in order, or run the
equivalents directly (Python 3.11):

| Step | `.bat` | Equivalent |
|---|---|---|
| Install deps | `1. setup (one time).bat` | `pip install -r requirements.txt` + `playwright install chromium --no-shell` |
| Sign in | `2. login (update login).bat` | `python scripts/login.py` |
| Export | `3. run_export (main script).bat` | `python scripts/export_multi.py` |
| Consolidate | `4. consolidate (combine reports).bat` | `python scripts/consolidate_*.py` |
| Fast export | `5. fast export (experimental).bat` | set `TSMIS_FAST_WORKERS`, then export |
| GUI (dev) | `run app (GUI preview).bat` | `python scripts/gui_main.py` |

Setup downloads a Built-in Chromium that becomes the default browser; if that
download is skipped or fails, the tool falls back to the system Edge/Chrome.
There are no automated tests; verification is a live export against TSMIS
(requires login) or running a consolidator over existing per-route files.

## Building the app

From the repo root (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1
```

This creates an isolated build venv, runs PyInstaller (onefolder, windowed), and
prunes the bundle to runtime-only files. The result is `dist\TSMIS Exporter\`
(~148 MB) — zip it to distribute.

Add `-BundleChromium` to build the with-browser variant (downloads Playwright's
Chromium into the bundle, which then defaults to it). Add `-SelfTest` to build
and run a headless self-test that verifies the frozen bundle (browser PDF +
download, PDF parsing, Excel, GUI) — a real release gate, not just "it
compiled":

```powershell
powershell -ExecutionPolicy Bypass -File build\build.ps1 -SelfTest
```

**Releases** are built and published by CI: push a `v*` tag (or run the
`release` workflow manually) and `.github/workflows/release.yml` gates both
variants with the frozen self-test, then publishes all three zips.

See [`CLAUDE.md`](CLAUDE.md) for build internals, bundle hygiene, and the DLP guard.

## Project structure

```
scripts/        Core engine (console-free) + console & GUI drivers
  common.py       URL, routes, timeouts, auth/nav helpers, browser launch
  exporter.py     The shared per-route export loop (+ parallel variant)
  cli.py          Console adapters backing the .bat flow
  gui_main.py     Desktop app entry (pywebview / Edge WebView2 window)
  gui_api.py      GUI state + the JS bridge; gui_worker.py = worker threads
  ui/             The interface itself (plain HTML/CSS/JS, no build step)
  export_*.py     One thin file per report type (a ReportSpec)
  consolidate_*.py  Combine per-route exports into one workbook
  compare_highway_log.py  TSMIS-vs-TSN discrepancy workbook (live formulas)
build/          Reproducible PyInstaller build (build.ps1, app.spec, prune, self-test)
output/         Per-report output folders + consolidated/ + run_reports/
*.bat           Numbered launchers for the console workflow
CLAUDE.md       In-depth architecture & contributor reference
```

A single report registry (`scripts/reports.py`) drives both the GUI and the
multi-report selector, so the two never drift. For the full design — the
`Events`/`ReportSpec` seam, retry logic, fast mode, and packaging — see
[`CLAUDE.md`](CLAUDE.md).

## Tech stack

- **Python 3.11** (standard library + four runtime deps)
- **[Playwright](https://playwright.dev/python/)** — browser automation, driving
  the system Edge/Chrome or the optional Built-in Chromium
- **[pdfplumber](https://github.com/jsvine/pdfplumber)** — PDF parsing (consolidation)
- **[openpyxl](https://openpyxl.readthedocs.io/)** — Excel writing (consolidation)
- **[pywebview](https://pywebview.flowrl.com/)** — desktop GUI shell (Edge
  WebView2 rendering a vanilla HTML/CSS/JS interface)
- **[PyInstaller](https://pyinstaller.org/)** — portable onefolder packaging

## Known limitations

- **The app is unsigned.** Windows SmartScreen / Defender and corporate DLP may
  flag it on first run. Unblock the zip before extracting (Properties → Unblock)
  and choose **More info → Run anyway**. Code-signing is the planned fix.
- **The standard build needs a browser installed.** It drives the machine's Edge
  or Chrome and does not bundle one — use the *with-browser* download for
  machines where that's a problem.

## Contributing

Issues and pull requests are welcome. Before contributing, please read
[`CLAUDE.md`](CLAUDE.md) — it documents the architecture and the conventions that
keep the codebase maintainable, notably:

- The core engine is **console-free** — report progress via the `Events` sink and
  raise exceptions; never `print`/`input`/`sys.exit` in core modules.
- User-facing messages must be **UI-neutral** (shown in both the console and GUI).
- Adding a report type or consolidator follows a documented recipe.

Keep commit messages short and imperative (e.g. `add route 395`).

## License & disclaimer

Released under the [MIT License](LICENSE). Bundled third-party components retain
their own licenses.

This is an **unofficial** utility that automates exporting reports a user is
already authorized to access. It is not affiliated with, endorsed by, or
supported by Caltrans or the State of California.
