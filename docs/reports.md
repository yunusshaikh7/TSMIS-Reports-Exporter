# Reports

What this doc covers: the full TSMIS report catalog (the **eight** exportable types, incl. the Highway Log (PDF) and Intersection Detail (PDF) print editions), each report's per-export behavior (`ReportSpec`, save strategy, empty/ready detection), why the site greys reports out (`cs-disabled`), and the three "add a new X" recipes (report type, consolidator, comparison).

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
| 6b | Intersection Detail (PDF) | PDF (Letter, landscape) | `output/<run>/intersection_detail_pdf/` |

`<run>` is a run folder, `"<YYYY-MM-DD> <src>-<env>"` (e.g. `2026-06-11 ssor-prod`) -- see [engine-and-reliability.md](engine-and-reliability.md) for run-folder mechanics.

The catalog (`scripts/report_catalog.py`) is the single source of truth for report metadata (P4); `reports.py` derives `EXPORT_REPORTS` from it, feeding the GUI checkboxes and `export_multi.py`, so the list can't drift. The `.bat` menus keep their own text, with a registry-parity check for the consolidate menu (`build/check_report_catalog.py`). Each row is `(menu label, format hint, ReportSpec)`. **Console** numbering follows `EXPORT_REPORTS` order; the **GUI picker** is grouped to mirror the website — its order comes from the catalog's `_PICKER_ORDER` / `picker_order()` and each entry's optional `group` + `short_label` (v0.18.1; see [Report grouping & site-menu-safe selection](#report-grouping--site-menu-safe-selection-v0181) below).

## `ReportSpec` -- what makes one report differ from another

Defined in `scripts/exporter.py`. Each report's differences live in a `ReportSpec`; the proven per-route loop, recovery, and skip/cancel logic live ONCE in `exporter.py`. To fix one report's behavior, edit only its `ReportSpec`.

| Field | Type | Meaning |
|---|---|---|
| `label` | str | the `#customReport` option's full text / `data-label` (e.g. `"TSAR: Ramp Summary"`); used as the **fallback** match when `data_value` is unset/unmatched, and as the menu-display label |
| `data_value` | str \| None | the site's **stable option id** — the `<li>`'s `data-value` (== the hidden native `<select>` value, e.g. `"Ramp_Summary"`, `"intersection_detail"`). Matched **FIRST** (v0.18.1) so selection survives the site's flat→nested report-menu migration; `None` ⇒ fall back to `label` text/`data-label`. |
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
- **`save_intersection_detail_pdf(page, out_path, timeout_ms=None)`** -- the Intersection Detail parallel (`intd_printAll`); see [Report 6b](#report-6b--intersection-detail-pdf) below.

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

### Reports 5-6 -- Intersection Summary / Intersection Detail (XLSX)
- **Enabled since v0.17.0** (on the **development** site — Settings ▸ "Use development site"). Both
  export, **consolidate, and compare** (cross-environment + vs-TSN) like every other report, and live
  in both matrices. The old app-wide disable gate still EXISTS as defensive groundwork —
  `reports.is_export_disabled()` over `DISABLED_EXPORT_SUBDIRS`,
  `export_reports_status()`'s per-report `disabled` flag, the JS `.option-static` rendering. The set is
  **empty** again as of **v0.19.1** (every export report enabled) — Intersection enabled since v0.17.0,
  the Highway Detail/Summary pair since v0.19.1 (see [Report grouping & site-menu-safe selection](#report-grouping--site-menu-safe-selection-v0181) above). As of P3 the GUI/manifests pass **stable export-op KEYS** (= each
  report's `subdir`; `idx` is display-order metadata only), so a registry re-order never mis-resumes.
  Locked by `build/check_intersection_gate.py` (now registry-derived).
- **Consolidate + compare:** `consolidate_intersection_summary` (category-count summer) and
  `consolidate_intersection_detail` (a thin `consolidate_xlsx` wrapper, sheet "Intersection Detail",
  36 cols) auto-consolidate on export finish (both in `_CONSOLIDATOR_BY_SUBDIR`); the vs-TSN +
  cross-env comparators are wired per the registry (see [comparison-engine.md](comparison-engine.md)
  §9e / §9f). The **PDF edition** of Intersection Detail has its own consolidator + comparators (Report 6b).
- Labels + formats verified against the live page source: **NO `"TSAR:"` prefix** (unlike the ramp pair), both Excel via the shared Export button.
- **Intersection Summary**: `label="Intersection Summary"`, `subdir="intersection_summary"`, `filename=intersection_summary_route_<ROUTE>.xlsx`. The page never renders an empty notice -- it ALWAYS shows `Total Intersections = N` (including `= 0`) and always offers a working Export. `wait_js` = `EXPORT_READY_JS` or `.ints-total` present. `is_empty` matches the regex `total intersections\s*=\s*0\b` (a zero total; not `= 10`/`= 20`). No hang risk: a drifted marker just reverts to the old benign all-zeros-file behavior, never a stall.
- **Intersection Detail**: `label="Intersection Detail"`, `subdir="intersection_detail"`, `filename=intersection_detail_route_<ROUTE>.xlsx`. The action bar (Export button) renders even for an empty route, plus an empty table row `<td class="hl-empty">No results found.</td>`. `wait_js` = `EXPORT_READY_JS` or `td.hl-empty` present. `is_empty` = `page.locator("td.hl-empty").count() > 0` (structural, robust to wording drift) OR `"no results found"` in body (text fallback). The engine's general no-download fast-fail (`save_via_export_button` -> `EmptyExport`) is the marker-independent backstop.
- **Caveat:** the site's Intersection feature is still under active development -- its empty strings / DOM are a MOVING TARGET. The fixes key on the robust structural signals (`td.hl-empty`, `Total Intersections = 0`) plus the general empty/no-download fast-fail, and must be re-verified once the feature is finalized. Do not hard-lock to `"No results found."`.

### Report 6b -- Intersection Detail (PDF)

The exact parallel of Report 4b (Highway Log (PDF)), forward-ported in v0.18.0 (CR-002).
- **Same dropdown option as #6** -- `label="Intersection Detail"` -- saved as a PDF via the page's own Print layout instead of the Excel Export button. Module `export_intersection_detail_pdf.py`; `subdir="intersection_detail_pdf"`; Letter, **landscape**. The registry's **menu label** is `"Intersection Detail (PDF)"`, but the `ReportSpec`'s `label` stays `"Intersection Detail"` (the dropdown text `select_report` clicks) — the two must not be conflated.
- **Appended LAST** in the export catalog so the seven existing export-op keys keep positions 0–6 — the manifest-v1 integer-index compatibility contract (CR-002-RM4; `batch_manifest._V017_EXPORT_ORDER` index 7 = `intersection_detail_pdf`).
- `wait_js` / `is_empty` are identical to the Excel Intersection Detail (`td.hl-empty` / `"no results found"`); `is_empty` runs BEFORE save, so the PDF render only runs for routes with rows.
- `save=save_intersection_detail_pdf` (in `exporter.py`) — the same print-capture mechanism as `save_highway_log_pdf`: the site's `intd_printAll()` builds the full multi-page layout, `window.print` is overridden to raise so the on-screen restore never runs, then `page.pdf()` captures it; it fails loudly with `ReportError` if the print fn or layout is missing.
- **Consolidator:** `consolidate_tsmis_intersection_detail_pdf.py` parses the PDF route exports into the SAME 36-column format (`intersection_detail_columns.HEADER`, Description at index 21) as the Excel export — a two-row-per-record / zebra-shaded PDF parser. Like HL-PDF it is NOT auto-consolidated inline (it needs a scratch convert dir — the matrix handles it). **Comparators:** `compare_intersection_detail_pdf` — `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL`, reusing the Excel Intersection Detail's vs-TSN schema/loaders.
- Verified offline against the fake-site fixture (`build/check_intersection_detail_pdf.py`, `build/fake_site/intersection_detail_print.html`). **Live-export verification against TSMIS is owed in v0.18.1** (the dev PC can't reach the dev site).

## Report grouping & site-menu-safe selection (v0.18.1)

Two related changes track how TSMIS presents its report dropdown, which is migrating from a **flat** list to **grouped fly-out menus** (live on the dev site; prod to follow).

### Selecting a report by stable `data_value`, not visible text

The `#customReport` dropdown is moving from flat `li.cs-option` rows (whose visible text **was** the full report name) to nested **`cs-parent` → `cs-submenu`** fly-outs, where a leaf's visible text is just **"Detail" / "Summary"**, the full name sits in `data-label`, and the report's stable id sits in **`data-value`** (== the hidden native `<select>` value). Matching by visible text broke the moment the menu changed (a leaf reads "Detail", not "Intersection Detail").

`report_nav._find_exact_option(page, label, data_value=None)` now matches by **`data-value` first** (exactly one hit wins), falling back to exact `text` / `data-label` for the old flat menu. `_reveal_submenu_if_leaf` hovers the option's `cs-parent` ancestor to open the fly-out before clicking (submenus reveal on CSS `:hover` only). `select_report` / `preflight` thread the spec's `data_value` through; the env-scan probe (`gui_worker._REPORT_OPTIONS_JS` + `check_one`) matches the same way and weighs the parent fly-out's disabled class. **Prod-safe by construction:** a `data_value` match is preferred, but an unset/unmatched `data_value` behaves exactly as the old text match — so the current flat prod menu is unaffected, and exports keep working across the changeover with nothing for the user to do. Locked by the synthetic `build/fake_site/dropdown_nested.html` (driven by `check_fake_site` + `check_export_engine`); each `ReportSpec` carries its `data_value` (see the field table above). The `cs-disabled` rule below is unchanged.

### The picker is grouped like the website

The GUI report picker mirrors the site's own grouping: **flat** Highway Log, Highway Log (PDF), and Highway Sequence at the top (the site's order), then the **Ramp** and **Intersection** families under their own headings. Order + grouping are catalog-driven, not UI-hardcoded: each `ExportEntry` carries an optional `group` + `short_label`, and `report_catalog._PICKER_ORDER` (exposed as `picker_order()`, import-asserted to cover every export key) fixes the display sequence. `reports.PICKER_ORDER` / `EXPORT_DISPLAY` re-export them; `gui_api` sorts the `reports` payload by `PICKER_ORDER` and sets each entry's `idx` = its **display position** (no app code reads `idx` — it's parity-check metadata only), plus `group` and `short` (the short leaf label, e.g. "Detail"). `ui/app.js` emits an `.option-group` header on each group change and shows `short || label` (indented under its group). Both the Export picker and Export-Everything use the one `fillReportList()`.

### Highway Detail / Highway Summary — export ENABLED (v0.19.1); Highway Detail (PDF) v0.19.2

The site added two more TSAR reports, **Highway Detail** and **Highway Summary**. v0.18.1 scaffolded them as reserved-DISABLED groundwork; **v0.19.1 enabled their EXPORT**; **v0.19.2 added the Highway Detail print-layout PDF edition** (consolidation / comparison / matrix integration is still a later feature — see [roadmap.md](roadmap.md)):

- **Real modules** `export_highway_detail.py` / `export_highway_summary.py` — each a genuine `ReportSpec` modeled on the Excel siblings (`save = save_via_export_button`). Confirmed against the **7.7 dev capture** (`highway_detail.js` live, action bar wires `hd_exportToExcel()` + `hd_printAll()`): empty = `td.hl-empty` / "No results found in this segment.", matched loosely (`td.hl-empty` OR "No … found"). Highway Detail is un-greyed on 7.7; Highway Summary is still `cs-disabled` there, so its export fail-fasts (`ReportUnavailableError`) until the vendor turns it on.
- **Highway Detail (PDF)** — `export_highway_detail_pdf.py`, `subdir="highway_detail_pdf"`, `data_value="highway_detail"` (same dropdown option), `save=save_highway_detail_pdf` (in `exporter.py`). The twin of `save_highway_log_pdf`: `hd_printAll()` builds the SAME `.hl-print-section` print layout; `window.print` is overridden to raise so the on-screen restore never runs, then `page.pdf()` captures it (Letter, **landscape**, 27 roadbed-grouped columns). Empty backstop counts `.hd-row1` data rows (HD's grouped columns put colspan on real rows, so Highway Log's non-colspan heuristic doesn't apply). **Appended LAST** — stable id **10** (`batch_manifest._V017_EXPORT_ORDER` stays `== EXPORT_KEYS`); `_PICKER_ORDER` places it next to its Excel sibling.
- **The gate is empty** (`reports.DISABLED_EXPORT_SUBDIRS = set()`): all pickable in the Export picker and ticked in Export Everything. Where the **live site** still `cs-disabled`s a report, `select_report` fails fast instead of stalling.
- They have **no consolidator / comparator / TSN entry yet**, so they stay absent from the matrices, Consolidate, and Compare (the env matrix stays 8 rows). Locked by `check_intersection_gate` (empty gate), `check_report_recipe`, `check_stable_ids` (append-only 8/9/10), and `check_report_catalog`.

To integrate the consolidator/comparison later: add their consolidators + comparators + `tsn_library` entries per the proven recipe in `build/check_report_recipe.py` (tracked in [roadmap.md](roadmap.md)).

### Coalescing both editions of a report (v0.19.2)

When the user selects **both editions of one on-site report** — the Excel export and the print-layout PDF, which share a `data_value` (Highway Log, Intersection Detail, Highway Detail) — the standard (sequential) export path generates the report **once per route** and saves both files off that single render, instead of generating it twice. `ExportWorker._run_specs` groups the selected specs by `data_value` (`_coalesce_groups`) and runs a pair through `exporter.run_export_combined`; the **Export-button save runs first** and the **DOM-rebuilding PDF Print save last** (`_PAGE_REBUILDING_SAVES` / `_save_rebuilds_page`), because `hl_printAll`/`intd_printAll`/`hd_printAll` replace `#rampResults` and would remove the Export button. Each edition keeps its own `RunResult`, staging/swap, run report, and auto-consolidation (`_prep_edition` / `_finish_edition`). **Scope:** the single-report `run_export` and the parallel engine are untouched; **fast mode** keeps each edition its own parallel pass (coalescing the parallel engine, and the console `run_cli_multi`, are follow-ups). Locked by `build/check_coalesce_editions.py`.

## `cs-disabled` -- the site can temporarily disable a report (EXPECTED)

TSMIS can temporarily disable individual reports from exporting, **by design (server-side)**. The site greys a disabled report's `<li>` with the `cs-disabled` class. This is NOT a bug -- on the live build the TSAR Ramp Summary + Ramp Detail `<li>` carried `cs-disabled` (observed in the captured live-site source — off-repo, not in this codebase), and the maintainer confirmed this is the intended on-site mechanism. If a report shows up greyed, that's normal, not breakage.

- **`select_report` (`report_nav`, re-exported by `common.py`)** clicks `#customReport`, locates the report's option (by `data-value` first, then exact text / `data-label` — see [Report grouping & site-menu-safe selection](#report-grouping--site-menu-safe-selection-v0181)), reveals the `cs-submenu` fly-out if it's a leaf, reads the option's classes (and its parent fly-out's), and if `cs-disabled` is present **raises `ReportUnavailableError`** (a `PreflightError` subclass) with a specific message: *"<report> is currently unavailable on the TSMIS site (the report is temporarily turned off there). Try another report, or try this one again later."* A disabled `<li>` has no `pointer-events:none`, so a Playwright click would silently no-op and the run would stall ~30 s into a generic preflight error -- `ReportUnavailableError` turns that into one clear "currently unavailable" message, surfaced as-is by `preflight` (it does not re-wrap it as "the page looks different").
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

1. **`scripts/export_<name>.py`** -- a `ReportSpec` (`label` = the option's text / `data-label`, **`data_value`** = the option's stable `data-value` id, `subdir`, `filename`, `wait_js`, `is_empty`, `save` -- reuse `save_pdf_letter` / `save_via_export_button`) + `run_cli(SPEC, title=...)`.
2. Add a branch to `3. run_export...bat` and `5. fast export...bat`.
3. Add one `ExportEntry` to `report_catalog.py` (the metadata SoT — `reports.py` derives `EXPORT_REPORTS`; feeds GUI + `export_multi`; set an optional **`group` + `short_label`** to place it under a picker family + add it to `_PICKER_ORDER`, else it lists flat). Update the frozen baseline in `build/check_report_catalog.py`.
4. List the new export module **and** any new flat module in `APP_MODULES` in `build/app.spec` (lazy imports need it; `check_app_modules` enforces completeness).
5. Add the report's fixtures to `scripts/ui/mock.js` (the `#mock` GUI preview reads its report lists from there, **not** `app.js`; `check_report_catalog` checks mock parity).
6. Add `output/<name>/.gitkeep`, whitelist in `.gitignore`.
7. Document in the table at the top of this doc (and CLAUDE.md's Supported Reports table).

For a PDF print-edition of an existing report (like Highway Log (PDF) / Intersection Detail (PDF)), keep the dropdown `label` of the Excel report, give it a distinct `subdir` + menu label, **append it LAST** in the catalog (so existing export-op keys keep their manifest-v1 positions — CR-002-RM4), and mirror every PDF-edition special-case in `matrix.py` / `day_matrix.py` / `gui_worker.py` (not just the labels).

## Recipe: add a new consolidator

Implement `consolidate(events, confirm_overwrite) -> ConsolidateResult` -- **console-free**: log via `events.on_log`, ask before overwrite via the `confirm_overwrite` callback, honor `is_cancelled()`, guard third-party imports with `_DEPS_OK`, build openpyxl styles inside functions. (The registry calls modules with the day-aware signature `consolidate(events, confirm_overwrite, day=None)` plus `input_dir_for(day)` / `out_path_for(day)`.)

- **For an XLSX report**, wrap `consolidate_xlsx_base.consolidate_xlsx` (set `INPUT_DIR`, `OUT_PATH`, `SHEET_NAME`, `REPORT_NAME`) like `consolidate_highway_log.py`.
- **For a different input format** (like PDF Ramp Summary), write standalone.

Then add the `__main__` -> `run_consolidate_cli`, wire `4. consolidate...bat` (the parity check in `build/check_report_catalog.py` enforces the menu covers every registry consolidator), add to `APP_MODULES`, and add a `ConsolidateEntry` to `report_catalog.py` (`reports.py` derives `CONSOLIDATE_REPORTS`; update the frozen baseline). Document here.

`CONSOLIDATE_REPORTS` (`reports.py`) is `(menu label, module)`. The three Highway Log consolidators are grouped with SOURCE-explicit, parallel labels -- `"<system> Highway Log (<format>)"` -- so the bare "Highway Log" can't be mistaken for one of the others:
- `"TSMIS Highway Log (Excel)"` (`consolidate_highway_log`) -- reads the TSMIS "Highway Log" Excel export, day-aware.
- `"TSMIS Highway Log (PDF)"` (`consolidate_tsmis_highway_log_pdf`) -- reads the app's own "Highway Log (PDF)" export, day-aware (NOT a dropped folder); parsed into the SAME 31-column format as the Excel export, the accurate substitute for the buggy vendor Excel.
- `"TSN Highway Log (PDF)"` (`consolidate_tsn_highway_log`) -- TSN district PDFs the user drops into `input/tsn_highway_log/` (from OUTSIDE the app, so this one keeps an input folder + `day` ignored).
- `"Intersection Detail"` (`consolidate_intersection_detail`, v0.17.0) -- a thin `consolidate_xlsx` wrapper (sheet "Intersection Detail", 36 cols), day-aware; also in `_CONSOLIDATOR_BY_SUBDIR` so it auto-consolidates on export finish and the matrix can build its vs-TSN cell. (Intersection Summary's consolidator — `consolidate_intersection_summary`, a category-count summer — is registered too.)

See [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) for the Highway Log consolidator internals.

## Recipe: add a new comparison type

Add one `CompareEntry` to `report_catalog.py` (the metadata SoT, P4 — its stable `cmp:*` key + label + adapter + `kind` + `group`); `reports.py` derives `COMPARE_REPORTS`/`COMPARE_KEYS` from it, an import-time assert enforces 1:1 keys, and you also update the frozen baseline in `build/check_report_catalog.py` and add the module to `APP_MODULES` in `build/app.spec`. The GUI's per-sub-tab type lists are generated from the derived rows `(label, module_or_adapter, kind, group)`; as of P3 (v0.18.0) **selection travels by each row's stable `cmp:*` key**, so the row order is only the UI-radio display order and never mis-resolves a `start_compare*` call.

**`group`** is one of `COMPARE_GROUPS`' ids. The Compare pane renders one **sub-tab per group** (first = default), and a row shows only under its group's sub-tab. As of v0.16.1 the two registry sub-tabs are:

```python
COMPARE_GROUPS = [
    ("env", "Cross-environment"),
    ("tsn", "vs TSN"),
]
```
- `group="env"` -- every report's **between-environments** comparison (Ramp Summary/Detail, Highway Sequence, Highway Log, **Intersection Summary/Detail**, and the two **PDF editions** — Highway Log (PDF) + Intersection Detail (PDF)), plus the two **PDF-vs-Excel** consistency self-checks (Highway Log + Intersection Detail) which also live in `env`.
- `group="tsn"` -- the file-based **TSMIS-vs-TSN** comparisons. COMPLETE for all 8 comparison-integrated export types (Highway Log Excel/PDF, Ramp Detail, Ramp Summary, Intersection Summary, Intersection Detail Excel/PDF, Highway Sequence). The two PDF editions' PDF-vs-Excel self-checks live under `env`, not `tsn`. (The v0.19.1 Highway Detail/Summary pair is export-only — no vs-TSN comparator yet, so it isn't here.)
- The GUI also appends a **third** sub-tab on its own, the day-keyed **"vs TSN Matrix"** (group id `tsn_by_day`) — not a registry comparison type.

A new cross-environment comparison is `group="env"`; a new TSMIS-vs-TSN one is `group="tsn"`; a brand-new family can add its own sub-tab by appending to `COMPARE_GROUPS`. `group` is independent of `kind`, so the files/folders input plumbing is untouched. (v0.16.1 staging moved HL's cross-env row from the old `highway_log` group to `env` and renamed that sub-tab to `tsn`.)

**`kind`** decides which inputs the pane asks for:
- **`"files"`** -- two workbooks; the module exposes `compare(path_a, path_b, out_path, events=None, confirm_overwrite=None, mode="formulas") -> ConsolidateResult` (console-free, same rules as consolidators; the GUI passes `mode` from its values/formulas checkboxes -- accept it even if only one flavor is implemented) plus `REPORT_NAME` and `suggest_name(path_a)`.
- **`"folders"`** -- two export run folders; the adapter exposes `compare_folders(dir_a, dir_b, out_path, events=None, confirm_overwrite=None, mode="formulas") -> ConsolidateResult` plus `REPORT_NAME` and `suggest_name(dir_a, dir_b)` -- usually just another `compare_env.EnvCompare(...)` instance (give it the report's subdir, sheet name, and optionally a pinned header / base `CompareSchema`). The per-route files are read straight from both folders (no consolidation first).

Current `COMPARE_REPORTS` rows:

| Label | Module / adapter | kind | group |
|---|---|---|---|
| TSAR: Ramp Summary -- between environments | `compare_env.RAMP_SUMMARY` | folders | env |
| TSAR: Ramp Detail -- between environments | `compare_env.RAMP_DETAIL` | folders | env |
| Highway Sequence Listing -- between environments | `compare_env.HIGHWAY_SEQUENCE` | folders | env |
| Highway Log -- between environments | `compare_env.HIGHWAY_LOG` | folders | env |
| TSAR: Intersection Summary -- between environments (v0.17.0, AGGREGATE per route) | `compare_env.INTERSECTION_SUMMARY` | folders | env |
| TSAR: Intersection Detail -- between environments (v0.17.0, flat route+PM) | `compare_env.INTERSECTION_DETAIL` | folders | env |
| Highway Log (PDF) -- between environments (v0.17.0, flat, both sides PDF-parsed) | `compare_env.HIGHWAY_LOG_PDF` | folders | env |
| Intersection Detail (PDF) -- between environments (v0.18.0, flat, both sides PDF-parsed) | `compare_env.INTERSECTION_DETAIL_PDF` | folders | env |
| Highway Log -- TSMIS vs TSN | `compare_highway_log` | files | tsn |
| Highway Log -- TSMIS (PDF) vs TSN (PDF) | `compare_highway_log_pdf.TSMIS_PDF_VS_TSN` | files | tsn |
| Highway Log -- TSMIS (PDF) vs TSMIS (Excel) | `compare_highway_log_pdf.TSMIS_PDF_VS_EXCEL` | files | env |
| TSAR: Ramp Detail -- TSMIS vs TSN (v0.17.0) | `compare_ramp_detail_tsn` | files | tsn |
| TSAR: Ramp Summary -- TSMIS vs TSN (v0.17.0, AGGREGATE) | `compare_ramp_summary_tsn` | files | tsn |
| TSAR: Intersection Summary -- TSMIS vs TSN (v0.17.8, AGGREGATE, 66-cat signal fold) | `compare_intersection_summary_tsn` | files | tsn |
| TSAR: Intersection Detail -- TSMIS vs TSN (v0.17.8, FLAT, compare-everything + S crosswalk) | `compare_intersection_detail_tsn` | files | tsn |
| Intersection Detail -- TSMIS (PDF) vs TSN | `compare_intersection_detail_pdf.TSMIS_PDF_VS_TSN` | files | tsn |
| Intersection Detail -- TSMIS (PDF) vs TSMIS (Excel) | `compare_intersection_detail_pdf.TSMIS_PDF_VS_EXCEL` | files | env |
| Highway Sequence Listing -- TSMIS vs TSN (v0.17.0, FLAT, route+**county**+PM) | `compare_highway_sequence_tsn` | files | tsn |

**Don't hand-roll workbook output**: build a `CompareSchema` and call `compare_core.run_compare` -- that's the approved workbook style for free, and the core's text/formulas are regression-locked. See [comparison-engine.md](comparison-engine.md) (engine + regression-lock harness) and [highway_log/comparison-study.md](highway_log/comparison-study.md) (the PDF-vs-Excel/TSN findings).

**Extra steps for a `group="tsn"` (vs-TSN) report (v0.17.0):** beyond the `COMPARE_REPORTS` row + `APP_MODULES`, (1) register the report's TSN source by adding a `TsnEntry` to `report_catalog.py` (its raw format + a `build_into` builder; `tsn_library._REPORTS` derives from it) so the matrices resolve it from the canonical library; (2) add the golden check (`check_compare_<report>_tsn.py`) to the blocking loop in `.github/workflows/checks.yml`; (3) reconcile both raw files by hand FIRST and lock the approved counts in [tsn-parsers.md](tsn-parsers.md). `compare_ramp_detail_tsn` is the **FLAT** reference: a `"files"` adapter whose two loaders project each side's own shape onto one shared, PM-keyed header, with the TSN-only columns marked `context_fields` (shown, never counted). `compare_ramp_summary_tsn` is the **AGGREGATE** reference: each side reduces to one statewide `{category: count}` table compared with `has_route=False` (key = category, field = count), and a familiar "Summary by Category" sheet is appended via `extra_sheet_writer=summary_layout.make_extra_sheet_writer(SPEC)` — the pattern the Intersection Summary will reuse. `compare_highway_sequence_tsn` shows the **composite-key** variant: when the natural key isn't unique (CA postmiles are county-relative), a `key_normalizer` returns a `"COUNTY POSTMILE"` token while County stays its own visible column — the same mechanism Highway Log uses for roadbed-canonical locations. To light a vs-TSN report up in BOTH matrices, the only required code step is adding it to `matrix.tsn_comparator_for(row_key)`.

## Verification

The golden checks for these reports -- `build/check_export_engine.py`, `build/check_fake_site.py` (drives a real headless Chromium over DOM fixtures, covers the Highway Log PDF `page.pdf()` path), `build/check_gui_bridge.py`, and the comparison/parse checks -- are owned by [verification-and-testing.md](verification-and-testing.md). True verification still means a live export against TSMIS (needs login).
