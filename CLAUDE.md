# CLAUDE.md — TSMIS Reports Exporter

A portable Windows desktop tool that bulk-exports TSMIS (Caltrans Transportation
System Management Information System) reports for every California state route. The
user picks one, several, or all report types; one shared SSO login serves them all.
It ships as a **single-folder portable app** (bundled Python + an Edge WebView2 GUI;
no installer, no Python needed on the target), with a `.bat` console flow retained
for development and fallback that runs the same core engine.

One TSMIS page serves every combination of **data source** (SSOR / ARS) and
**environment** (prod / test / dev); defaults are SSOR + Prod.

> **This file is the router.** It holds the project snapshot, the report table, and
> the **non-negotiable conventions**. All the deep knowledge — architecture, auth,
> the GUI, the comparison engine, Highway Log internals, build/release, IT/security,
> verification, lessons, history — lives in the **[`docs/`](docs/INDEX.md) library**.
> Start at **[docs/INDEX.md](docs/INDEX.md)** and open the topic doc for whatever
> you're touching. Keep this file a thin index; don't re-expand `docs/` detail here.

---

## Supported reports

| # | Report | Output | Folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/<run>/ramp_summary/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/<run>/ramp_detail/` |
| 3 | Highway Sequence Listing | XLSX | `output/<run>/highway_sequence/` |
| 4 | Highway Log | XLSX | `output/<run>/highway_log/` |
| 4b | Highway Log (PDF) | PDF (Letter, landscape) | `output/<run>/highway_log_pdf/` |
| 5 | Intersection Summary | XLSX | `output/<run>/intersection_summary/` |
| 6 | Intersection Detail | XLSX | `output/<run>/intersection_detail/` |

`<run>` is a run folder `"<YYYY-MM-DD> <src>-<env>"` (e.g. `2026-06-11 ssor-prod`).
Reports 5–6 (Intersection) are **export-only for now** (consolidate + compare-vs-TSN are
**groundwork** — see [docs/roadmap.md](docs/roadmap.md)). Their export is **enabled** but the
report lives on the **development** TSMIS site — switch via Settings ▸ "Use development site"
(`tsmis-dev.dot.ca.gov`). Two consolidate-only
Highway Log sources exist too — **TSN** district PDFs (dropped into
`input/tsn_highway_log/`) and the app's own **Highway Log (PDF)** export. The
**Compare** tab diffs Highway Logs (TSMIS-vs-TSN, the two PDF-sourced flavors) and
runs cross-environment comparisons of the other reports.

→ Per-report behavior + the "add a report/consolidator/comparison" recipes:
[docs/reports.md](docs/reports.md). Highway Log columns / PDF parsing / comparisons:
[docs/highway_log/](docs/highway_log/columns.md) and
[docs/comparison-engine.md](docs/comparison-engine.md).

---

## The knowledge library — read the owning doc before you touch its area

| Area | Doc |
|---|---|
| Big picture: core + front-ends, registry, run folders, data location, feature buckets | [docs/architecture.md](docs/architecture.md) |
| Export loop runtime: resume, retry, skip/cancel, fast-fails, timeouts, fast mode | [docs/engine-and-reliability.md](docs/engine-and-reliability.md) |
| Sign-in: token-in-hash, `CONFIG` trap, device SSO, Edge recapture, LNA, login chips | [docs/auth-and-signin.md](docs/auth-and-signin.md) |
| Desktop GUI: pywebview/WebView2, threading/queue, the **5 pywebview traps**, the `#mock` | [docs/gui.md](docs/gui.md) |
| Report catalog, `ReportSpec`, `cs-disabled`, the extension recipes | [docs/reports.md](docs/reports.md) |
| `compare_core`: regression lock, flavors, key/roadbed/ditto, write-path safety, families | [docs/comparison-engine.md](docs/comparison-engine.md) |
| Corrected 31-column Highway Log labels | [docs/highway_log/columns.md](docs/highway_log/columns.md) |
| Highway Log PDF (cell-rect) + TSN (char-window) parsers | [docs/highway_log/pdf-and-tsn-parsing.md](docs/highway_log/pdf-and-tsn-parsing.md) |
| The `+`/`++` ditto domain convention + evidence | [docs/highway_log/comparison-study.md](docs/highway_log/comparison-study.md) |
| Build, `app.spec`, DLP prune, browser channels, the **updater**, CI | [docs/build-and-release.md](docs/build-and-release.md) |
| IT/DLP/security, the **work-PC capability model**, audit findings, code-signing | [docs/it-and-security.md](docs/it-and-security.md) |
| The **`gh-pages` landing page** — layout, live download button, theme toggle, screenshot/OG regen, SEO | [docs/website.md](docs/website.md) |
| How to verify (no test framework): golden `check_*.py`, COM-recalc, `#mock`, test-data locations | [docs/verification-and-testing.md](docs/verification-and-testing.md) |
| The durable lessons (field failures, one-core, regression discipline, audit method) | [docs/lessons.md](docs/lessons.md) |
| The narrative history | [docs/history.md](docs/history.md) |
| Roadmap / deferred / dormant backlog | [docs/roadmap.md](docs/roadmap.md) |
| The reusable read-only code-review prompt | [docs/code-review-prompt.md](docs/code-review-prompt.md) |

Code-level deep-dives (algorithms, data/control flow, extension points) live under
**`docs/internals/`** — `compare-core`, `highway-log-data-processing`, `gui-bridge`,
`auth-state-machine`, `export-engine`, `updater-swap`. Full map with "read this when…"
for each topic + internals doc: **[docs/INDEX.md](docs/INDEX.md)**.

---

## Conventions (non-negotiable — apply every session)

- **Core is console-free.** `common.py`, `exporter.py`, the consolidator/comparison
  cores report via the `Events` sink (`scripts/events.py`) and raise exceptions —
  **never** `print`/`input`/`sys.exit`. Only `cli.py` and `gui_*.py` touch
  I/O/the window. User-facing strings from the core stay **UI-neutral** (no ".bat"
  names, no "this window" / "menu option N" — that guidance lives in the driver).
- **No AI attribution anywhere** — commits, PR titles/descriptions, code, comments.
  Write as if the user authored it. (Project-specific reinforcement of the global rule.)
- **Never commit** `scripts/tsmis_auth.json` (treat as a credential), generated
  `output/`, or build artifacts (`build/.venv`, `dist/`, `.claude/` state).
- **`compare_core` is regression-locked.** Any change to its formula/label TEXT must
  be proven **cell-for-cell identical** for the TSMIS-vs-TSN flavor before shipping;
  new behavior is added through **opt-in** `CompareSchema` fields that default to the
  no-op original (so non-HL comparisons stay byte-identical). See
  [docs/comparison-engine.md](docs/comparison-engine.md).
- **Sync Playwright API** (not async); Playwright is **thread-affine** — only the
  owning thread may touch a page.
- **Call the timeout ACCESSORS** (`report_timeout_ms()` etc.) in engine code, not the
  raw constants — they read Settings overrides at run time.
- **Log every decision.** Each decision point (site/browser pick, channel fallback,
  saved-session-vs-device-mode, per-route outcome) and every swallowed exception logs
  at least `type(e).__name__` + the first line — the "one log upload answers it"
  contract. Error messages name the failing step and stay UI-neutral; the WHY goes to
  the log.
- **The updater TLS trusts the Windows cert store** (`ssl.create_default_context()`).
  Never switch it to `requests`/`certifi` — a bundled CA list breaks corporate
  TLS inspection on exactly the managed PCs that need it.
- **Real test data + the live TSMIS website source are LOCAL ONLY** (under
  `C:\Users\Yunus\Downloads\TSMIS\…`) — never commit, copy into the repo, or push;
  the website source is Caltrans-internal. It is the ground truth for selectors/labels.
- **Work-PC reality:** any feature that must run on the locked-down Caltrans work PC
  must work as a plain unsigned exe from a user-writable folder — no PowerShell, cmd,
  admin, temp scripts, or scheduled tasks. See [docs/it-and-security.md](docs/it-and-security.md).
- **Git:** commit/push only when asked; if on `main`, branch first. Commit messages
  are short, imperative (`add route 395`). Release branches share the tag name, so
  push tags explicitly: `git push origin refs/tags/<tag>`.

---

## Repo layout (orientation)

```
1.–5. *.bat                  setup / login / export / consolidate / fast export (console flow)
run app (GUI preview).bat    dev launcher for the GUI
version.py                   app name/version + pinned Playwright (single source of truth)
scripts/                     the engine (console-free) + console & GUI drivers + UI
  common.py exporter.py exporter_parallel.py cli.py run_report.py events.py settings.py paths.py
  reports.py                 the single report/consolidate/compare registry
  export_*.py                one thin ReportSpec per report type
  consolidate_*.py           per-route exports → one workbook (+ TSN / TSMIS-PDF parsers)
  compare_core.py            the regression-locked comparison-workbook engine
  compare_env.py compare_highway_log*.py   the comparison families over compare_core
  highway_log_columns.py     one source of truth for the corrected 31-column labels
  gui_main.py gui_api.py gui_worker.py  GUI entry / js_api bridge + state / worker threads
  ui/                        index.html + app.css + app.js (vanilla; + the #mock API)
  updater.py login.py logging_setup.py batch_manifest.py report_library.py
build/                       build.ps1, app.spec, prune_bundle.ps1, full_smoke.py, check_*.py
  gen_release_notes.py release_notes_header.md backfill_release_notes.ps1   per-version release notes
CHANGELOG.md                 user-facing changelog (one section per version; source of release bodies)
tools/                       dev utilities (not shipped) — screenshots.py regenerates the site/README shots
docs/                        the knowledge library (start at docs/INDEX.md)
output/ input/               generated/user data (git-ignored except .gitkeep stubs)
```

The **landing page** is on a separate **`gh-pages`** branch (GitHub Pages), not in
`main` — see [docs/website.md](docs/website.md). Detail on anything above is in the
matching `docs/` file (see the table above).

---

## Pinned versions

`version.py` / `requirements*.txt`: `playwright==1.60.0` (Node driver only — no
Chromium ships in the default build), `pdfplumber==0.11.9`
(→ `pdfminer.six==20251230`), `openpyxl==3.1.5`, `pywebview==6.2.1`
(→ `pythonnet`/`clr_loader`), `pyinstaller==6.20.0`,
`pyinstaller-hooks-contrib==2026.5`. Built/tested on **Python 3.11**. Rationale +
the three release variants: [docs/build-and-release.md](docs/build-and-release.md).
