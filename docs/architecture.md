# Architecture

How the TSMIS Reports Exporter is structured — one console-free core driven by two
front-ends, the single report registry, route/run plumbing, the on-disk run-folder
and data-location model, and the high-level v0.12/v0.13 feature buckets. Runtime
*behavior* (the export loop, recovery, resume, skip/cancel, timeouts) lives in
[engine-and-reliability.md](engine-and-reliability.md); GUI internals (threading,
pywebview traps, snapshots) live in [gui.md](gui.md).

## Two run modes, one core

The export engine is **console-free** and backs both front-ends:

- **`.bat` console flow** — development + fallback. Same core engine; menus are
  static hand-edited text.
- **Packaged GUI** — a pywebview (**Edge WebView2**) window rendering `scripts/ui/`
  (plain HTML/CSS/JS, no build step / no npm). Entry chain:
  `gui_main.py` (entry) → `gui_api.py` (js_api bridge + state + queue pump) →
  `gui_worker.py` (worker threads, unchanged across the Tk→WebView rewrite).

**Console boundary.** Only `cli.py` and `gui_*.py` touch
`print`/`input`/`msvcrt`/the window. Core code (`common.py`, `exporter.py`,
consolidator cores) reports via the `Events` sink (`scripts/events.py`) and raises
exceptions — never `print`/`input`/`sys.exit`. User-facing strings from the core
must be **UI-neutral**: no `.bat` names, no "this window" / "menu option N" — that
guidance lives in the driver.

The `gui_main.main()` entry first branches into self-update **swap mode**
(`updater.SWAP_FLAG` in `sys.argv`) *before* logging/paths/CLR setup, then calls
`setup_logging(enable_faulthandler=False)`, strips Mark-of-the-Web from bundled
.NET assemblies (`_unblock_dotnet_assemblies`), runs `updater.cleanup_leftovers()`,
imports `gui_api`, and calls `gui_api.run()`. Details of swap mode / MOTW are owned
by [build-and-release.md](build-and-release.md); pywebview traps and the
threading/queue model are owned by [gui.md](gui.md).

### The Events seam (`scripts/events.py`)

The engine never prints, prompts, or exits — it pushes status through an `Events`
sink and returns a `RunResult`. The console shim wires the callbacks to
`print()`/`msvcrt`; the GUI wires them to its queue + widgets. All callbacks default
to harmless no-ops, so `Events()` is a valid silent sink.

| Callback | Purpose |
|---|---|
| `on_log(message)` | Human-readable status line (console prints; GUI appends to log pane). |
| `on_route(route, status)` | Per-route outcome; status ∈ `{saved, empty, skipped, failed, exists}`. |
| `should_skip()` | Return True to skip the route currently being waited on. |
| `is_cancelled()` | Return True to stop the whole run before the next route. |
| `is_paused()` | Return True to HOLD between routes (B1 pause/resume); honored in fast mode too (all workers park). |
| `on_status(worker, text)` | One-line "what this browser is doing now" — statuses REPLACE, log lines accumulate. |
| `screenshot_wanted(worker) -> bool` | Polled at safe points on the worker's own thread (Playwright is thread-affine); must clear the request before returning True (one request = one shot). |
| `on_screenshot(worker, image, note, url)` | Requested capture — `image` is JPEG bytes (or None on failure; `note` says why), `url` the address at capture time. |
| `worker_no` | Which browser this sink reports for — 1 in the sequential engine; fast mode wraps the shared sink in per-worker `Events` carrying each worker's number. |

**Result types** (also in `events.py`):

- `RunResult` — `saved` (count), `empty` / `user_skipped` / `failed` / `exists`
  (route lists), `output_dir`, `per_route` (ordered `(route, status)` behind the
  saved run report), `report_path` (where the run-report CSV was auto-saved).
- `ConsolidateResult` — `status` ∈ `{"ok", "cancelled", "error"}`, `message`,
  `output_path`, `summary_lines`, `verdict` (`None | "match" | "diff"` — comparisons
  only; the GUI keys its quick-result dialog on it, consolidators leave it None).

## One shared loop, per-report `ReportSpec`

Each report's differences live in a `ReportSpec` — `label` (exact dropdown text),
output filename, `subdir`, post-Generate `wait_js`, `is_empty` check, and `save`
strategy. The proven per-route loop, recovery, and skip/cancel logic live **once**
in `exporter.py` (`run_export(spec, events)`, `save_pdf_letter` /
`save_via_export_button`, `_recover`, `_retry_failed_routes`). To fix one report's
behavior, edit only its `ReportSpec`. See
[engine-and-reliability.md](engine-and-reliability.md) for the loop internals and
[reports.md](reports.md) for the per-report spec details.

Each `export_<name>.py` module is thin (~30 lines): a `ReportSpec` + `run_cli`.

## Single report registry (`scripts/reports.py`)

One source of truth feeds both the GUI tabs and the console multi-exporter, so the
lists can't drift. `export_multi.py` imports `EXPORT_REPORTS`; `gui_api.py` reads
the registry lists (`EXPORT_REPORTS`, `CONSOLIDATE_REPORTS`, `COMPARE_REPORTS`) plus
`COMPARE_GROUPS`. The `.bat` menus are static text and are still hand-edited
separately. The module is import-light and console-free: importing it never
launches a browser or does I/O.

Four data structures:

**`EXPORT_REPORTS`** — `(menu label, format hint, ReportSpec)`; order is the GUI
display order and console menu numbering:

| Label | Format | Notes |
|---|---|---|
| `TSAR: Ramp Summary` | PDF | |
| `TSAR: Ramp Detail` | Excel | |
| `Highway Sequence Listing` | Excel | |
| `Highway Log` | Excel | |
| `Highway Log (PDF)` | PDF | Same "Highway Log" dropdown option, saved via the page's Print layout (`hl_printAll`) instead of the Excel Export button. Export-only — the consolidator reads the `.xlsx`. |
| `Intersection Summary` | Excel | Export-only (no consolidation/comparison). No `TSAR:` prefix. |
| `Intersection Detail` | Excel | Export-only. |

**`CONSOLIDATE_REPORTS`** — `(menu label, module)`. Each module exposes
`consolidate(events, confirm_overwrite, day=None)` plus `input_dir_for(day)` /
`out_path_for(day)` (paths are day-dependent now that exports group into run
folders, so the registry hands out the module, not a precomputed `OUT_PATH`).
Three Highway Log consolidators are grouped TSMIS-before-TSN with source-explicit
labels:

| Label | Module | Input |
|---|---|---|
| `TSAR: Ramp Summary` | `consolidate_ramp_summary` | |
| `TSAR: Ramp Detail` | `consolidate_ramp_detail` | |
| `Highway Sequence Listing` | `consolidate_highway_sequence` | |
| `TSMIS Highway Log (Excel)` | `consolidate_highway_log` | TSMIS "Highway Log" Excel export, `output/<run>/highway_log/` (day-aware). |
| `TSMIS Highway Log (PDF)` | `consolidate_tsmis_highway_log_pdf` | TSMIS "Highway Log (PDF)" export, `output/<run>/highway_log_pdf/` (day-aware, this app's own export). |
| `TSN Highway Log (PDF)` | `consolidate_tsn_highway_log` | TSN district PDFs dropped in `input/tsn_highway_log/` (from outside the app, so this one keeps an input folder + `day` ignored). |

See [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) for the
PDF parsers.

**`COMPARE_GROUPS`** — the Compare-pane sub-tabs, in order (first = default). As of
v0.16.1: `("env", "Cross-environment")` and `("tsn", "vs TSN")` (the GUI appends a
third, the "vs TSN Matrix"). HL's cross-env compare sits in `env` with the others;
the file-based TSMIS-vs-TSN compares sit in `tsn` (HL today; other reports in 0.17.0).

**`COMPARE_REPORTS`** — `(menu label, module/adapter, input kind, group)`. `kind` is
`"files"` (two workbooks) or `"folders"` (two export run folders); `group` is one of
`COMPARE_GROUPS`' ids (selection is by index, so this order is what the UI radios and
`start_compare*` calls key on):

| Label | Module / adapter | Kind | Group |
|---|---|---|---|
| `TSAR: Ramp Summary — between environments` | `compare_env.RAMP_SUMMARY` | folders | env |
| `TSAR: Ramp Detail — between environments` | `compare_env.RAMP_DETAIL` | folders | env |
| `Highway Sequence Listing — between environments` | `compare_env.HIGHWAY_SEQUENCE` | folders | env |
| `Highway Log — between environments` | `compare_env.HIGHWAY_LOG` | folders | env |
| `Highway Log — TSMIS vs TSN` | `compare_highway_log` | files | tsn |
| `Highway Log — TSMIS (PDF) vs TSN (PDF)` | `compare_highway_log_pdf.TSMIS_PDF_VS_TSN` | files | tsn |
| `Highway Log — TSMIS (PDF) vs TSMIS (Excel)` | `compare_highway_log_pdf.TSMIS_PDF_VS_EXCEL` | files | env |

The comparison engine itself is owned by
[comparison-engine.md](comparison-engine.md).

**`_CONSOLIDATOR_BY_SUBDIR` / `consolidator_for_spec(spec)`** — used by B2
auto-consolidate; maps an export `ReportSpec` to its consolidate module **by the
spec's output subdir** so it can't drift from the lists above. Intersection
Summary/Detail are export-only and absent from the map (→ None).

## Route selection

Route selection is per-run plumbing into `run_export(..., routes=ROUTES)`.
`common.parse_routes` (`common.py:313`) is the one parser. The route universe is
`ROUTES` in `common.py` (`common.py:270`, zero-padded 3-digit values, optional
suffixes like `"005S"`/`"101U"` matching the TSMIS `<select>` option values) — edit
it to change the route universe permanently.

- **Console:** `_resolve_routes_console` (Enter / `all` / EOF = all; honors
  `TSMIS_ROUTES`).
- **GUI:** a Routes entry + `Choose…` picker.

## Multi-report runs

A multi-report run runs each selected `ReportSpec` in turn through the same engine
(so at most `workers` browsers are ever open at once), each spec with its own
browser, preflight, and run-report CSV.

## Run folders (v0.10.0; replaces bare dated outputs)

Every run writes into `output/<YYYY-MM-DD src-env>/<report>/`
(`paths.output_run_dir`; src/env from `common.get_site()` at run start). Each day's
exports live in their own folder AND different source/environment combinations never
mix — the folder name says exactly what's inside, which the cross-environment
comparison keys on (e.g. `2026-06-11 ssor-prod`).

| Helper (`scripts/paths.py`) | Purpose |
|---|---|
| `run_folder_name(src, env, day=None)` | The run-folder name; `day=None` = today. |
| `output_run_dir(src, env, day=None)` | `output/<day src-env>/`. |
| `parse_run_folder(name)` | `(date, src, env)` or None. Legacy bare-date folders (pre-v0.10) read as the old defaults **ssor-prod** (regex `_RUN_RE` makes the ` <src>-<env>` suffix optional). |
| `list_output_days()` | Existing run/legacy folders, newest first. |
| `latest_output_day()` | Newest run-folder name, or None. |
| `list_output_days_for_report(subdir)` | Run folders that actually contain non-empty `<subdir>/` files — the A2 cross-env compare-folder filter. |
| `resolve_day_choice(raw)` | Maps a `TSMIS_DAY` value (exact folder name, or a bare date → that date's newest run folder) to a folder. |

Consolidators take the run-folder NAME as their `day` argument (opaque string;
newest by default via `latest_output_day()`). The GUI picker lists run folders; the
console prompts (Enter = newest; `TSMIS_DAY` accepts a folder name or a bare date).
The combined workbook lands in `output/<run>/consolidated/`. When **no** run folders
exist, consolidators fall back to the legacy flat `output/<report>/` layout, so
pre-0.7 exports stay consolidatable. Resume/idempotency, the integrity gate, and
live browser status are runtime behavior — see
[engine-and-reliability.md](engine-and-reliability.md).

## Data location (option A): next to the exe, `%LOCALAPPDATA%` fallback

`scripts/paths.py` decides WHERE the app reads/writes, so the rest of the code never
cares whether it's a dev script or the packaged exe. Resolved once at import time.

- **Packaged build** (`sys.frozen`): write next to the `.exe`
  (`DATA_ROOT = Path(sys.executable).parent`). If that folder is not writable (e.g.
  unzipped into Program Files or a read-only network share), fall back automatically
  to `%LOCALAPPDATA%\TSMIS Exporter` (`APP_NAME = "TSMIS Exporter"`). Callers
  surface `DATA_ROOT` in the UI so the rare fallback is never a mystery.
- **Dev / `.bat`** (not frozen): `DATA_ROOT` = repo root; `output/` and
  `scripts/tsmis_auth.json` keep their original locations so existing scripts
  behave exactly as before.

Derived paths: `OUTPUT_ROOT = DATA_ROOT/output`, `INPUT_ROOT = DATA_ROOT/input`
(user-supplied input — currently TSN district PDFs; TSMIS reports never read from
here). App-private data (`_PRIVATE` = `DATA_ROOT/data` when frozen, else `DATA_ROOT`):
`AUTH`, `LOG_DIR`, `FAILURES_DIR`, `CONFIG_FILE`, `UPDATE_DIR`,
`EDGE_LOGIN_PROFILE_DIR`, `WEBVIEW_PROFILE_DIR`, `DOWNLOADED_BROWSERS_DIR`. The
frozen auth file is `data/tsmis_auth.json`; the dev auth file is
`scripts/tsmis_auth.json` (git-ignored, treat as a credential). `paths.py` also
points `PLAYWRIGHT_BROWSERS_PATH` at the bundled `_internal/ms-playwright` (with-browser
variant) or the Settings-downloaded `DOWNLOADED_BROWSERS_DIR`, unless one is already
set — browser-channel detail is owned by
[build-and-release.md](build-and-release.md).

Two output-filename helpers: `stamped_consolidated_filename(filename, day)` (A1 —
stamps `<date> <src>-<env>` provenance into a consolidated workbook's name; returns
unchanged for None / legacy-flat `day`) and `env_tagged_filename(filename, tag)`
(Export-Everything — FRONT-stamps the `<src-env>` subfolder name; FRONT on purpose
so the consolidators' `*.xlsx`/`*.pdf` glob + end-anchored `_route_(\w+)\.xlsx$`
route parser keep matching).

## Settings (`scripts/settings.py`)

Persisted user settings in `config.json` under the app's private data dir
(`CONFIG_FILE`). Consumers read through accessor functions at **run time** (not
import time), so a change applies to the next run without restarting; precedence is
explicit function args / `TSMIS_*` env vars (where one exists) > the file > built-in
defaults. The console flow gets the same overrides because `common.py` reads through
here (and so `settings.py` must never import `common`). Tolerant by design: a
missing/broken `config.json` silently means "defaults" (a corrupt file is moved
aside to `config.json.corrupt` first), writes go through a temp file + `os.replace`,
unknown keys survive round-trips.

`DEFAULTS` (numeric ones clamped to `_RANGES`): `report_timeout_min` 6,
`fast_timeout_min` 10, `retry_timeout_min` 15, `county_timeout_s` 60,
`download_start_timeout_s` 60, `fast_workers` 3, `debug_logging` False,
`ui_devtools` False, `env_check_after_signin` True, `env_check_after_start` False,
`notify_on_finish` True. Plus non-scalar state: per-env URL overrides under
`site_urls` (validated https + `*.ca.gov` host + matching `?env=`/`?src=` params;
consulted by `common.get_url()` on every navigation) and the Export-Everything
destination under `batch_dest` (`get/set_batch_dest`, default
`output/All Reports (current)`). The full Settings *tab* (env-access scan, browser
download, support bundle, Delete-all-reports, etc.) is described at a high level
under the feature buckets below; its UI mechanics belong to [gui.md](gui.md).

## High-level feature buckets (v0.12.0 / v0.13.0)

These are the structural shape of recent features. Runtime details and the GUI
mechanics are owned by [engine-and-reliability.md](engine-and-reliability.md) and
[gui.md](gui.md); this is the "what is it and where does it plug in" map.

### v0.12.0 — output labeling, run control, batch export (roadmap A+B; A3 deferred)

| Feature | What it is | Where it plugs in |
|---|---|---|
| **A1 self-describing filenames** | Consolidated workbooks stamp the run's `<date> <src>-<env>` into the filename; both comparison families append a generated-on date in `suggest_name`. TSN Highway Log exempt (no src/env, undated input); legacy flat layout keeps its fixed name. `compare_core/_SCHEMA` text untouched (regression-locked). | `paths.stamped_consolidated_filename` via every `consolidate_*.out_path_for`. Lock: `build/check_a1_filenames.py`. |
| **A2 compare-folder filter** | Cross-env compare folder dropdowns list only runs that actually contain the chosen report (server-side; Browse paths skip the filter). | `paths.list_output_days_for_report` + `GuiApi.get_compare_folders`; `start_compare_env` preflights it. Lock: `build/check_a2_compare_filter.py`. |
| **B1 Pause/Resume** | Holds BETWEEN routes (never inside a thread-affine Playwright wait), in both sequential and parallel engines — so it WORKS in fast mode (all workers park), unlike Skip. | `Events.is_paused` (8th callback) + shared `exporter._wait_while_paused`; `GuiApi.pause_or_resume` toggles `pause_event`, cleared on cancel and at end-of-task. Lock: `build/check_b1_pause.py`. |
| **B2 auto-consolidate** | One Export-tab toggle; `ExportWorker` runs the matching consolidator INLINE after each spec's export (reuses the held task slot + same Events sink). Highway Log (PDF) has no auto-consolidator → skipped (every other report, incl. both Intersection reports, consolidates as of v0.17.0); failures logged, never fatal. | `reports.consolidator_for_spec` maps export→consolidate by subdir. Lock: `build/check_b2_autoconsolidate.py`. |
| **B3 Export Everything (always-current store)** | The **Everything** tab runs selected report types × selected environments SEQUENTIALLY into a configurable, UNDATED, overwritten-in-place destination (always holds the latest of every report), laid out `<dest>/<src-env>/<report>/` (+ `consolidated/`). Each report+env folder is refreshed via **STAGE-AND-SWAP** (`_swap_store_dir`): the export writes into a `.staging` sibling and replaces the live folder only on a clean finish (discarded on cancel/crash), so a failed refresh never destroys the last-good copy — the Phase-3 fix for `auto-consolidate-rmtree-out-dir-before-export`. Reuses B1 pause + B2 auto-consolidate. | `gui_worker.BatchWorker` (per-env, reusing `ExportWorker._run_specs`); per-env targeting via process-global `common.set_site` (NOT `set_thread_site` — a single sequential orchestrator under the single-task gate; original restored at end). Dest = `settings.get/set_batch_dest`. Saved-reports freshness library via `report_library.report_ages` + `GuiApi.report_library_info`. Progress persists to `batch_manifest` (`DATA_ROOT/batch_job.json`, atomic, untouched by Delete-all-reports) → resumes across restarts (startup Resume/Discard banner). Locks: `build/check_b3_batch.py` + `check_report_library.py`. |

A3 (results tab) was deferred. **The current GUI is a stopgap** — a full GUI
overhaul is planned (the user designs it elsewhere and will hand it over). Fix bugs,
but DON'T invest in redesigning the current layout (mock candidates were rejected).

### v0.13.0 — interface declutter, run lifecycle, accessibility & self-revert

A UI/UX + trust release (the planned A3/D1 bucket was pushed down to v0.14.0). At a
structural level:

- **Right-column run lifecycle** — idle: a pre-flight summary of what the active tab
  will do; during a run: a progress card with a live ETA (EMA over per-item times,
  reset when `progress.done===0`); after: a persistent completion summary with **Open
  run folder** and **Retry failed routes** (de-duped failed list).
  `gui_api._build_export_summary` → snapshot `last_summary`/`last_run_folder`.
- **Progress hierarchy** — PRIMARY/SECONDARY lines plus, for Export Everything, a
  per-environment stepper (one pill per env: done/running/pending). Backend ships the
  ordered per-env state list in `batch_progress` (`BatchWorker._step_views`, read from
  the manifest so it's correct across a resume).
- **Completion notification** (default on) — taskbar flash via
  `gui_api._flash_taskbar` (`FlashWindowEx`); toggled by `notify_on_finish`.
- **Compare sub-tabs** — regrouped to two (`COMPARE_GROUPS`): Cross-environment
  (default) and Highway Log (every HL comparison gathered in one place).
- **Revert to the previous version** (Settings ▸ Debugging) — reinstalls the newest
  full release strictly older than this build through the same SHA-verified
  download→stage→swap pipeline. Owned by
  [build-and-release.md](build-and-release.md).
- **Env-check setting split** — `env_check_after_signin` (ON) + `env_check_after_start`
  (OFF); `gui_api._maybe_autoscan(reason)` keys off which event fired.
- **Everything tab brought to convention** — greys with other tabs during any task;
  output files env-labeled via `paths.env_tagged_filename` (FRONT-stamped); env-access
  verdicts colour-coded in the tab.
- **Accessibility** — keyboard-focusable checkboxes (sr-only clipped input + visible
  focus ring), colour-plus-glyph status icons, aria-labels on icon-only controls.

### This update — the cross-environment comparison matrix

A report × environment **comparison matrix** lives on its own **sub-tab** of the
Everything tab (sibling to *Refresh & export*) and goes full-width (the activity
column animates down to a slim log + a config zone). It sits ON TOP of the
always-current store and **orchestrates the existing comparison adapters
(`compare_env` / `compare_highway_log` / `compare_highway_log_pdf`) without editing
them**. **5 rows** at the time (**7 as of v0.17.0** — every report; nothing greyed),
each with a per-row
**comparison-mode** dropdown: cross-environment, **vs TSN** (Excel/PDF flavors), and
**TSMIS PDF-vs-Excel** (the "greyed where no code exists" is now defensive — all coded). Cells show the **discrepancy
count, colour-coded**, with per-cell/row/column/all refresh (cancellable + resumable),
report + **environment-column** toggles (config zone), TSN drops in
`<dest>/_tsn_input/`, and TSN/cross-format sheets in `<dest>/comparisons/tsn/`. New
module `scripts/matrix.py` (console-free engine); freshness via
`report_library.cell_ages`; intersection reports were **shown greyed/unpickable** at
this version via one `reports` gate (`DISABLED_EXPORT_SUBDIRS` / `export_reports_status`)
— **v0.17.0 enabled them** (on the dev site), so `DISABLED_EXPORT_SUBDIRS` is now empty
and the gate stays as defensive groundwork.
A light app-wide motion layer (pane/popover/modal enters, button press, a slow theme
cross-fade) lands with it. Engine internals are owned by
[comparison-engine.md](comparison-engine.md) §12; the UI + bridge + motion by
[gui.md](gui.md). (This delivers a slice of the parked A3 file-browser intent;
A3 stays parked.)

**v0.16.0 extends the matrix in two ways.** (1) Matrix actions now flow through a
**matrix-scoped job queue** in front of the single-task gate — a 2nd action queues
(reorder/remove/clear/stop-all), jobs auto-advance, row/column headers gain distinct
↻ re-export + ⟳ rebuild buttons, and re-exports support **fast mode**
(`MatrixBatchExportWorker`). (2) A **second matrix** lives under the **Compare** tab —
the manual **"vs TSN Matrix"** (`scripts/day_matrix.py`; the sub-tab was "TSN by day"):
rows = EVERY report (HL wired then; all reports wired as of v0.17.0), columns =
exported days, each cell = (report, day) vs TSN; no cross-env, no live re-export.
The two matrices **share** the TSN compare path (`matrix.consolidate_and_compare_tsn`,
factored out — byte-identical to the prior output), the TSN dataset/picker, and the
ONE job queue (a `which:env|day` Job discriminator routes to the right worker). Engine
+ store details: [comparison-engine.md](comparison-engine.md) §12/§12b.

### v0.17.0 — the canonical TSN library + per-row `tsn_subdir`

The six TSN reports essentially never change, so v0.17.0 gives them **one fixed home**
instead of scattering them across drop folders: `scripts/tsn_library.py` over
`<DATA_ROOT>/tsn_library/<report>/` (`raw/` = the raw TSN file(s) as exported — district
PDFs / a statewide PDF / a statewide XLSX, the format is the report's own; `consolidated/`
= the generated consolidated/normalized Excel, built once and reused since a couple of TSN
reports are PDFs). Paths come from `paths.tsn_library_{dir,raw_dir,consolidated_path}`.
The module is console-free with **lazy** consolidator imports (so importing it never pulls
pdfplumber), and exposes `status`/`all_status` (raw present? consolidated present? current
vs the raw?), `import_raw`, `build_consolidated` (reuses when current), and **`resolve`** —
the matrices' single TSN entry point, returning the same `{kind: file|consolidated|pdfs|
raw|none, …}` contract as before.

`matrix.tsn_source` now **delegates to `tsn_library.resolve`**: an explicit user pick
(`settings.matrix_tsn_files`, keyed by report) wins; else the library; else the legacy
fallbacks (`<dest>/_tsn_input/<report>/`, then the global console-flow
`input/tsn_highway_log/` + `output/tsn_highway_log_consolidated.xlsx`) so existing installs
keep working until imported. The report key IS the per-row **`tsn_subdir`**
(`matrix.tsn_subdir_for`): both Highway Log rows share `highway_log`, every other report
uses its own. This replaced `day_matrix.TSN_SUBDIR` (deleted) — the by-day matrix now
resolves TSN per row, so plugging in a report is just registering it + flipping `supported`.

## See also

- [reports.md](reports.md) — the per-report `ReportSpec` details and how to add a
  report.
- [engine-and-reliability.md](engine-and-reliability.md) — the export loop, resume,
  skip/cancel, timeouts, fast mode.
- [auth-and-signin.md](auth-and-signin.md) — sign-in paths, the auth file, device
  mode.
- [gui.md](gui.md) — pywebview traps, the threading/queue model, snapshots, the mock
  UI.
- [comparison-engine.md](comparison-engine.md) — `compare_core` and the schemas.
- [build-and-release.md](build-and-release.md) — packaging, browser channels, the
  updater/swap mode/MOTW, revert.
- [it-and-security.md](it-and-security.md) — work-PC constraints (no
  PowerShell/cmd/admin) and security posture.
- [verification-and-testing.md](verification-and-testing.md) — the golden `check_*`
  list and verification loops.
