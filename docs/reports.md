# Reports

What this doc covers: the full TSMIS report catalog (the seven exportable types incl. Highway Log (PDF)), each report's per-export behavior (`ReportSpec`, save strategy, empty/ready detection), why the site greys reports out (`cs-disabled`), and the three "add a new X" recipes (report type, consolidator, comparison).

Deep Highway Log internals live under [highway_log/](highway_log/columns.md) -- the corrected 31-column labels in [highway_log/columns.md](highway_log/columns.md), PDF/TSN parsing in [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md), and the PDF-vs-Excel/TSN study in [highway_log/comparison-study.md](highway_log/comparison-study.md). The comparison workbook engine is owned by [comparison-engine.md](comparison-engine.md).

## The report catalog

| # | Report | Output | Folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/<run>/ramp_summary/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/<run>/ramp_detail/` |
| 3 | Highway Sequence Listing | XLSX | `output/<run>/highway_sequence/` |
| 4 | Highway Log | XLSX | `output/<run>/highway_log/` |
| 4b | Highway Log (PDF) | PDF (Letter, landscape) | `output/<run>/highway_log_pdf/` |
| 5 | Intersection Summary | XLSX | `output/<run>/intersection_summary/` |
| 6 | Intersection Detail | XLSX | `output/<run>/intersection_detail/` |

`<run>` is a run folder, `"<YYYY-MM-DD> <src>-<env>"` (e.g. `2026-06-11 ssor-prod`) -- see [engine-and-reliability.md](engine-and-reliability.md) for run-folder mechanics.

The registry (`scripts/reports.py`, `EXPORT_REPORTS`) is the single source of truth feeding both the GUI checkboxes and `export_multi.py`, so the list can't drift. The `.bat` menus are hand-edited text. Display order in the GUI / console numbering follows `EXPORT_REPORTS` order. Each row is `(menu label, format hint, ReportSpec)`.

## `ReportSpec` -- what makes one report differ from another

Defined in `scripts/exporter.py`. Each report's differences live in a `ReportSpec`; the proven per-route loop, recovery, and skip/cancel logic live ONCE in `exporter.py`. To fix one report's behavior, edit only its `ReportSpec`.

| Field | Type | Meaning |
|---|---|---|
| `label` | str | EXACT `#customReport` dropdown text (e.g. `"TSAR: Ramp Summary"`) |
| `subdir` | str | output subfolder name (`output/<run>/<subdir>/`) |
| `filename` | `route -> str` | output file name for a route |
| `wait_js` | `route -> str` | JS that resolves when the report is READY **or** empty (post-Generate wait) |
| `is_empty` | `(page) -> bool` | True if the route has no data |
| `save` | `(page, out_path, timeout_ms) -> None` | writes the file |

Each thin `scripts/export_<name>.py` module is ~30 lines: a `SPEC = ReportSpec(...)` plus a `run_cli(SPEC, title=...)` `__main__` for the console flow.

### Save strategies (reusable, in `exporter.py`)

- **`save_pdf_letter(page, out_path, timeout_ms=None)`** -- `page.pdf(format="Letter", print_background=True, margin 0.4in)`. The report is already rendered inline, so `timeout_ms` is unused. Used by Ramp Summary.
- **`save_via_export_button(page, out_path, timeout_ms=None)`** -- clicks `button.export-btn` (`has_text="Export"`, `.first`) and saves the download. Bounds the download wait at `min(download_start_timeout_ms(), ceiling)`; a rendered route whose Export produces no download (the site's no-op for "nothing to export") raises `EmptyExport` in seconds instead of hanging the full ceiling + 15-min retry. If `report_error_text(page)` is set it raises `ReportError` instead. Used by Ramp Detail, Highway Sequence, Highway Log, both Intersection reports.
- **`save_highway_log_pdf(page, out_path, timeout_ms=None)`** -- see [Highway Log (PDF)](#report-4b--highway-log-pdf) below.

Every save calls `_verify_saved_file` (magic-byte integrity check: `.xlsx` must start `PK\x03\x04`, `.pdf` must start `%PDF`; a truncated/0-byte file is deleted and the route fails so resume re-pulls it). See [engine-and-reliability.md](engine-and-reliability.md) for the resume integrity gate.

## Per-report specifics

All `wait_js` predicates also match a no-results phrase so the loop never stalls on an empty route; `is_empty` then decides whether it was empty. `EXPORT_READY_JS` (`common.py`) watches the Export button.

### Report 1 -- TSAR: Ramp Summary (PDF, Letter)
- `label="TSAR: Ramp Summary"`, `subdir="ramp_summary"`, `filename=tsar_ramp_summary_route_<ROUTE>.pdf`.
- Renders **inline**: `wait_js` ready when `Route <route>` appears or `No ramps found`. `is_empty` = `"No ramps found"` in body.
- `save=save_pdf_letter` (inline page -> `page.pdf()` Letter, no Export button click).
- **Source-data caveat (in the consolidator, not the parser).** On **9 routes** (005, 008, 010, 094, 110, 134, 210, 280, 605) the source PDF's own *Ramp Types* breakdown sums short of its stated *Total* by 1-9 ramps, **identically across all three environments**. `consolidate_ramp_summary.parse_pdf` is **correct** -- cross-checked against an independent geometric word-position extraction over all 378 PDFs x 14 ramp types (0 mismatches) and the raw page-2 text. The consolidator's `_audit_ok` cell flags these routes **RED on purpose** (`⚠ Source ≠ total: <section>`). **Do NOT "fix" the parser to force them green** -- that would hide a real TSMIS source-data issue (the cell exists to catch exactly this). The identical gap cancels on both sides of a cross-env comparison. -> [lessons.md](lessons.md) §5.

### Report 2 -- TSAR: Ramp Detail (XLSX)
- `label="TSAR: Ramp Detail"`, `subdir="ramp_detail"`, `filename=tsar_ramp_detail_route_<ROUTE>.xlsx`.
- `wait_js` = `EXPORT_READY_JS` or `No ramps found`. `is_empty` = `"No ramps found"` in body.
- `save=save_via_export_button`.
- **Site quirk (cosmetic):** the TSMIS page hardcodes `highway_sequence_listing.xlsx` as Ramp Detail's *download* filename (a site copy-paste bug). Harmless for the tool -- `save_via_export_button` renames the download via `save_as` to the `filename` above. (Worth reporting upstream; tracked in [roadmap.md](roadmap.md).)

### Report 3 -- Highway Sequence Listing (XLSX)
- `label="Highway Sequence Listing"`, `subdir="highway_sequence"`, `filename=highway_sequence_route_<ROUTE>.xlsx`.
- The Export button only renders when the report has data; an empty route shows "No results found" (hsl.js). `wait_js` matches `EXPORT_READY_JS` or the loose `/No \w+ found/i`. `is_empty` keys on that **positive** text — `bool(re.search(r"No \w+ found", body, re.I))` — NOT Export-button absence (Phase-3 fix `highway-sequence-errored-route-can-record-empty`): a fatal error page ALSO lacks the button but renders its message in `#rampResults.error` (caught first by `report_error_text`), not as this text, so button-absence alone would misclassify an errored route as "No data". Locked by `check_export_engine.py`.
- `save=save_via_export_button`.

### Report 4 -- Highway Log (XLSX)
- `label="Highway Log"`, `subdir="highway_log"`, `filename=highway_log_route_<ROUTE>.xlsx`.
- The action bar (with the Export button) ALWAYS renders once the report finishes, even for a route with no rows. `wait_js` = `EXPORT_READY_JS` or `/No results found/i`. `is_empty` = `"No results found"` in body -- detected by table text, NOT button absence (clicking Export on an empty route is a site no-op that would otherwise hang waiting for a download).
- `save=save_via_export_button`.
- Output format / corrected column labels: see [highway_log/columns.md](highway_log/columns.md).

### Report 4b -- Highway Log (PDF)
- **Same dropdown option as #4** -- `label="Highway Log"` -- saved as a PDF via the page's own Print layout instead of the Excel Export button. Module `export_highway_log_pdf.py`; `subdir="highway_log_pdf"`, `filename=highway_log_route_<ROUTE>.pdf`. Letter, **landscape** (30 columns).
- The registry uses a distinct **menu label** `"Highway Log (PDF)"`, but the `ReportSpec`'s `label` stays `"Highway Log"` (the actual dropdown text). The two must not be conflated: `label` is what `select_report` clicks; the menu label is GUI/console display only.
- `wait_js` / `is_empty` are identical to the Excel Highway Log (`EXPORT_READY_JS` or `/No results found/i`; empty = `"No results found"` in body). `is_empty` runs BEFORE save, so the PDF render only runs for routes that actually have rows.
- `save=save_highway_log_pdf`. The on-screen Highway Log is **paginated** (`hl_renderPage` shows one page of rows), so a bare `page.pdf()` would capture a single page. The site's global `hl_printAll()` builds the full multi-page layout (cover page + every page, with page breaks) into `#rampResults`, then calls `window.print()` and SYNCHRONOUSLY restores the on-screen view. The save **overrides `window.print` to raise first** (`window.print = () => { throw ... }`), so that restore line never runs and the complete print layout stays in the DOM for `page.pdf()` (which emulates print media -- the site's `@media print` hides every control and shows only `#rampResults`). It checks `box.querySelector('.hl-print-section')` exists and fails loudly with `ReportError` if `hl_printAll` is missing (`no-print-fn`) or the layout didn't build (`no-layout`), rather than silently saving the one paginated page.
- **Export-only** -- no consolidator on the PDF path itself. The TSMIS Highway Log (PDF) **consolidator** (`consolidate_tsmis_highway_log_pdf.py`) reads this export folder day-aware; see [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md). (Historically the Excel-path consolidator reads the `.xlsx` export.)
- Verified against the real site source + a headless `page.pdf()` fixture (`build/check_fake_site.py`). **Live-export verification against TSMIS is still pending** (the dev PC can't reach the site).

### Reports 5-6 -- Intersection Summary / Intersection Detail (XLSX, EXPORT-ONLY)
- **Export-only** -- NO consolidator and NO comparison support. They are absent from `_CONSOLIDATOR_BY_SUBDIR`, so `consolidator_for_spec()` returns `None` and B2 auto-consolidate skips them.
- Labels + formats verified against the live page source (v0.10.4): **NO `"TSAR:"` prefix** (unlike the ramp pair), both Excel via the shared Export button.
- **Intersection Summary**: `label="Intersection Summary"`, `subdir="intersection_summary"`, `filename=intersection_summary_route_<ROUTE>.xlsx`. The page never renders an empty notice -- it ALWAYS shows `Total Intersections = N` (including `= 0`) and always offers a working Export. `wait_js` = `EXPORT_READY_JS` or `.ints-total` present. `is_empty` matches the regex `total intersections\s*=\s*0\b` (a zero total; not `= 10`/`= 20`). No hang risk: a drifted marker just reverts to the old benign all-zeros-file behavior, never a stall.
- **Intersection Detail**: `label="Intersection Detail"`, `subdir="intersection_detail"`, `filename=intersection_detail_route_<ROUTE>.xlsx`. The action bar (Export button) renders even for an empty route, plus an empty table row `<td class="hl-empty">No results found.</td>`. `wait_js` = `EXPORT_READY_JS` or `td.hl-empty` present. `is_empty` = `page.locator("td.hl-empty").count() > 0` (structural, robust to wording drift) OR `"no results found"` in body (text fallback). The engine's general no-download fast-fail (`save_via_export_button` -> `EmptyExport`) is the marker-independent backstop.
- **Caveat:** the site's Intersection feature is still under active development -- its empty strings / DOM are a MOVING TARGET. The fixes key on the robust structural signals (`td.hl-empty`, `Total Intersections = 0`) plus the general empty/no-download fast-fail, and must be re-verified once the feature is finalized. Do not hard-lock to `"No results found."`.

## `cs-disabled` -- the site can temporarily disable a report (EXPECTED)

TSMIS can temporarily disable individual reports from exporting, **by design (server-side)**. The site greys a disabled report's `<li>` with the `cs-disabled` class. This is NOT a bug -- on the live build the TSAR Ramp Summary + Ramp Detail `<li>` carried `cs-disabled` (observed in the captured live-site source — off-repo, not in this codebase), and the maintainer confirmed this is the intended on-site mechanism. If a report shows up greyed, that's normal, not breakage.

- **`select_report` (`common.py`)** clicks `#customReport`, finds the report's `li.cs-option`, reads its classes, and if `cs-disabled` is present **raises `ReportUnavailableError`** (a `PreflightError` subclass) with a specific message: *"<report> is currently unavailable on the TSMIS site (the report is temporarily turned off there). Try another report, or try this one again later."* A disabled `<li>` has no `pointer-events:none`, so a Playwright click would silently no-op and the run would stall ~30 s into a generic preflight error -- `ReportUnavailableError` turns that into one clear "currently unavailable" message, surfaced as-is by `preflight` (it does not re-wrap it as "the page looks different").
- **The env-access scan** (Settings > Check all environments) reads the dropdown's per-report availability for every `EXPORT_REPORTS` row, so any label drift or temporary disable shows up there as "missing"/greyed without running an export. Owned by [it-and-security.md](it-and-security.md); also see the env scan / `EmptyExport` / no-download fast-fail details in [engine-and-reliability.md](engine-and-reliability.md).

## Report-related Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| Route fails instantly with a "TSMIS site error" | The site can't build that route (`#rampResults` gets an `error` class, detected via `common.ERROR_JS` -> `ReportError`) | Expected -- recorded `failed` (see `FAILURES_DIR`); a TSMIS issue |
| One report's output wrong | That report's selector changed | Edit only its `ReportSpec` |
| "page looks different than expected" | Preflight failed -- the site changed | Check `LOG_DIR`/`FAILURES_DIR`; update selectors |
| A report shows greyed / "currently unavailable" | `cs-disabled` on the live site (temporary server-side disable) | Expected -- try another report or later |

For timeouts (`REPORT_TIMEOUT_MS`, `DOWNLOAD_START_TIMEOUT_MS`, etc.) and the fast-fail classes (`EmptyExport`, `ReportError`, `ReportUnavailableError`), see [engine-and-reliability.md](engine-and-reliability.md).

---

## Recipe: add a new report type

1. **`scripts/export_<name>.py`** -- a `ReportSpec` (`label` = exact dropdown text, `subdir`, `filename`, `wait_js`, `is_empty`, `save` -- reuse `save_pdf_letter` / `save_via_export_button`) + `run_cli(SPEC, title=...)`.
2. Add a branch to `3. run_export...bat` and `5. fast export...bat`.
3. Add one entry to `EXPORT_REPORTS` in `reports.py` (feeds GUI + `export_multi`).
4. List the module in `APP_MODULES` in `build/app.spec` (lazy imports need it).
5. Add `output/<name>/.gitkeep`, whitelist in `.gitignore`.
6. Document in the table at the top of this doc (and CLAUDE.md's Supported Reports table).

## Recipe: add a new consolidator

Implement `consolidate(events, confirm_overwrite) -> ConsolidateResult` -- **console-free**: log via `events.on_log`, ask before overwrite via the `confirm_overwrite` callback, honor `is_cancelled()`, guard third-party imports with `_DEPS_OK`, build openpyxl styles inside functions. (The registry calls modules with the day-aware signature `consolidate(events, confirm_overwrite, day=None)` plus `input_dir_for(day)` / `out_path_for(day)`.)

- **For an XLSX report**, wrap `consolidate_xlsx_base.consolidate_xlsx` (set `INPUT_DIR`, `OUT_PATH`, `SHEET_NAME`, `REPORT_NAME`) like `consolidate_highway_log.py`.
- **For a different input format** (like PDF Ramp Summary), write standalone.

Then add the `__main__` -> `run_consolidate_cli`, wire `4. consolidate...bat`, add to `APP_MODULES` and `CONSOLIDATE_REPORTS`, and document here.

`CONSOLIDATE_REPORTS` (`reports.py`) is `(menu label, module)`. The three Highway Log consolidators are grouped with SOURCE-explicit, parallel labels -- `"<system> Highway Log (<format>)"` -- so the bare "Highway Log" can't be mistaken for one of the others:
- `"TSMIS Highway Log (Excel)"` (`consolidate_highway_log`) -- reads the TSMIS "Highway Log" Excel export, day-aware.
- `"TSMIS Highway Log (PDF)"` (`consolidate_tsmis_highway_log_pdf`) -- reads the app's own "Highway Log (PDF)" export, day-aware (NOT a dropped folder); parsed into the SAME 31-column format as the Excel export, the accurate substitute for the buggy vendor Excel.
- `"TSN Highway Log (PDF)"` (`consolidate_tsn_highway_log`) -- TSN district PDFs the user drops into `input/tsn_highway_log/` (from OUTSIDE the app, so this one keeps an input folder + `day` ignored).

See [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) for the Highway Log consolidator internals.

## Recipe: add a new comparison type

Add one row to `COMPARE_REPORTS` in `reports.py` and the module to `APP_MODULES` in `build/app.spec`. Rows are `(label, module_or_adapter, kind, group)`. The GUI's per-sub-tab type lists are generated from it; **selection is by index**, so the row order is what the UI radios and `start_compare*` calls key on.

**`group`** is one of `COMPARE_GROUPS`' ids. The Compare pane renders one **sub-tab per group** (first = default), and a row shows only under its group's sub-tab. As of v0.14.1 the two sub-tabs are:

```python
COMPARE_GROUPS = [
    ("env", "Cross-environment"),
    ("highway_log", "Highway Log"),
]
```
- `group="env"` -- plain cross-environment report comparisons (Ramp Summary/Detail, Highway Sequence).
- `group="highway_log"` -- EVERY Highway Log comparison gathered in one place: cross-env HL, TSMIS-vs-TSN, and the two PDF-sourced ones.

A new Highway Log comparison is `group="highway_log"`; a new plain cross-env one is `group="env"`; a brand-new family can add its own sub-tab by appending to `COMPARE_GROUPS`. `group` is independent of `kind`, so the files/folders input plumbing is untouched.

**`kind`** decides which inputs the pane asks for:
- **`"files"`** -- two workbooks; the module exposes `compare(path_a, path_b, out_path, events=None, confirm_overwrite=None, mode="formulas") -> ConsolidateResult` (console-free, same rules as consolidators; the GUI passes `mode` from its values/formulas checkboxes -- accept it even if only one flavor is implemented) plus `REPORT_NAME` and `suggest_name(path_a)`.
- **`"folders"`** -- two export run folders; the adapter exposes `compare_folders(dir_a, dir_b, out_path, events=None, confirm_overwrite=None, mode="formulas") -> ConsolidateResult` plus `REPORT_NAME` and `suggest_name(dir_a, dir_b)` -- usually just another `compare_env.EnvCompare(...)` instance (give it the report's subdir, sheet name, and optionally a pinned header / base `CompareSchema`). The per-route files are read straight from both folders (no consolidation first).

Current `COMPARE_REPORTS` rows:

| Label | Module / adapter | kind | group |
|---|---|---|---|
| TSAR: Ramp Summary -- between environments | `compare_env.RAMP_SUMMARY` | folders | env |
| TSAR: Ramp Detail -- between environments | `compare_env.RAMP_DETAIL` | folders | env |
| Highway Sequence Listing -- between environments | `compare_env.HIGHWAY_SEQUENCE` | folders | env |
| Highway Log -- between environments | `compare_env.HIGHWAY_LOG` | folders | highway_log |
| Highway Log -- TSMIS vs TSN | `compare_highway_log` | files | highway_log |
| Highway Log -- TSMIS (PDF) vs TSN (PDF) | `compare_highway_log_pdf.TSMIS_PDF_VS_TSN` | files | highway_log |
| Highway Log -- TSMIS (PDF) vs TSMIS (Excel) | `compare_highway_log_pdf.TSMIS_PDF_VS_EXCEL` | files | highway_log |

**Don't hand-roll workbook output**: build a `CompareSchema` and call `compare_core.run_compare` -- that's the approved workbook style for free, and the core's text/formulas are regression-locked. See [comparison-engine.md](comparison-engine.md) (engine + regression-lock harness) and [highway_log/comparison-study.md](highway_log/comparison-study.md) (the PDF-vs-Excel/TSN findings).

## Verification

The golden checks for these reports -- `build/check_export_engine.py`, `build/check_fake_site.py` (drives a real headless Chromium over DOM fixtures, covers the Highway Log PDF `page.pdf()` path), `build/check_gui_bridge.py`, and the comparison/parse checks -- are owned by [verification-and-testing.md](verification-and-testing.md). True verification still means a live export against TSMIS (needs login).
