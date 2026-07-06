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
| 6b | Intersection Detail (PDF) | PDF (Letter, landscape) | `output/<run>/intersection_detail_pdf/` |

`<run>` is a run folder `"<YYYY-MM-DD> <src>-<env>"` (e.g. `2026-06-11 ssor-prod`).
Reports 5–6 (Intersection): export is **enabled** but the report lives on the
**development** TSMIS site — switch via Settings ▸ "Use development site"
(`tsmis-dev.dot.ca.gov`). Highway Log and Intersection Detail each ship in **two
editions** — the Excel export and a print-layout **PDF** edition (4b / 6b; 6b was
forward-ported in v0.18.0 as an exact parallel of 4b). v0.17.0 brought all reports to
parity: **every report consolidates AND compares vs TSN** — all 8 export types have a
vs-TSN comparator, live in both the Everything and by-day matrices (see
[docs/roadmap.md](docs/roadmap.md) / [docs/tsn-parsers.md](docs/tsn-parsers.md) for
the per-report schema + locked canaries). Consolidate-only sources exist too — **TSN**
Highway Log district PDFs (dropped into `input/tsn_highway_log/`) and the app's own
**Highway Log (PDF)** and **Intersection Detail (PDF)** exports. The **Compare** tab
diffs every report **TSMIS-vs-TSN** (the PDF-sourced Highway Log and Intersection
Detail among them, each also offering a **PDF-vs-Excel** self-check) and runs
cross-environment comparisons.

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
- **Completion is producer-owned; a partial never promotes.** `outcome.py` is the
  vocabulary (completion ∈ complete/partial/no_data/cancelled/failed × artifact ∈
  promoted/new_unpromoted/previous_preserved/none) — set it from structured counts,
  **never** inferred from `summary_lines` text. Only a **complete** result may be
  promoted to the live store, cached, or shown green. See
  [docs/engine-and-reliability.md](docs/engine-and-reliability.md).
- **Consolidated artifacts are transactional.** Write to a temp then `os.replace`;
  a partial/failed/cancelled refresh **keeps last-good** (never clobbers it). Each
  persistent workbook carries a producer-set `consolidation_meta` completion sidecar
  whose read is **fail-safe** (corrupt/locked ⇒ conservative partial, never a false
  green). `cache_envelope.py` versions the matrix/by-day caches.
- **Read comparison counts by HEADER LABEL, not column position.** `read_counts`
  locates Status/Diffs from the workbook header so flat vs grouped layouts both work
  (the F4/O4 fix); never hard-code A1/column indices.
- **`report_catalog.py` is the report-metadata SoT**; `reports.py` is **derived** from
  it (EXPORT/CONSOLIDATE/COMPARE lists, matrix rows, stable-ID lookups, the picker
  `group`/`short_label` + `_PICKER_ORDER`). Stable IDs are immutable string keys;
  `batch_manifest._V017_EXPORT_ORDER` (== `EXPORT_KEYS`) is **append-only** — positions
  0–7 frozen; v0.18.1 appended the reserved-but-**DISABLED** Highway Detail/Summary
  groundwork at 8/9 (in `DISABLED_EXPORT_SUBDIRS`: shown greyed, rejected server-side,
  absent from matrix/compare/consolidate). Add a report by editing the catalog;
  `check_report_catalog` proves the derivation. See [docs/reports.md](docs/reports.md).
- **Select reports by stable `data_value`, not visible text** (v0.18.1). `select_report`
  and the env-scan probe match the `#customReport` option by its `data-value` (the site's
  stable id) and reveal the `cs-submenu` flyout for a leaf, falling back to exact text/
  `data-label`. This keeps exports working as the site migrates its report dropdown from a
  flat list to grouped fly-outs (live on **dev**) WITHOUT breaking the current flat **prod**
  menu. Each `ReportSpec` carries its `data_value`; the picker is grouped to mirror the site.
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
  common.py                  a re-export SHIM over the acyclic engine leaves below
  auth_nav.py report_nav.py session.py site_target.py routes.py errors.py timeouts.py
  browser_channels.py edge_device.py   the extracted engine leaves common.py re-exports
  exporter.py exporter_parallel.py export_multi.py run_report.py cli.py events.py settings.py paths.py
  outcome.py cache_envelope.py consolidation_meta.py artifact_store.py   the outcome/transaction contracts
  report_catalog.py          the report-metadata source of truth (P4); reports.py derives from it
  reports.py                 the report/consolidate/compare registry view + stable-ID lookups
  export_*.py                one thin ReportSpec per report type (incl. *_pdf editions)
  consolidate_*.py           per-route exports → one workbook (+ TSN / TSMIS-PDF parsers)
  compare_core.py            the regression-locked comparison-workbook engine
  compare_tsn_common.py      the shared FILE-comparator substrate (P5b; every comparator rides it since v0.19.0)
  compare_env.py compare_highway_log*.py compare_*_tsn.py   the comparison families over compare_core
  pdf_table_lib.py           the shared PDF-table machinery (clusterer/columns/writer/convert loop, R2)
  matrix.py                  the matrix FACADE (patch matrix.<name>) over matrix_state.py + matrix_build.py
  matrix_state.py matrix_build.py day_matrix.py summary_layout.py   matrix reads / builds + by-day + summary
  tsn_library.py tsn_load_*.py   the canonical TSN library (versioned normalization, D2) + its loaders
  highway_log_columns.py intersection_detail_columns.py   the corrected per-report column labels
  gui_main.py gui_api.py     GUI entry / the bridge core (state, pump, gate)
  gui_export_api.py gui_auth_api.py gui_compare_api.py gui_settings_api.py gui_update.py   the endpoint mixins (S1)
  gui_worker.py              re-export SHIM over gui_worker_export/_env/_maint/_matrix.py (S2)
  task_coordinator.py contract.py        GUI task-state owner / Python⇄JS bridge enum SSOT
  gui_endpoint.py gui_matrix.py gui_win32.py   the endpoint envelope (+_task_endpoint/pick_path) / matrix mixin / Win32
  validation.py              the one-click Settings validation (W1)
  ui/                        index.html app.css app.js + ui-export/-batch/-compare/-matrix/-settings/-dom.js + mock.js + contract.js
  self_test.py evidence.py pdf_row_oracle.py owned_dir.py safe_delete.py   self-test / evidence / safety
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
