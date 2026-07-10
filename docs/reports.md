# Reports

What this doc covers: the full TSMIS report catalog (**fifteen** exportable types — incl. the six print editions (Ramp Detail / Highway Sequence / Highway Log / Intersection Summary / Intersection Detail / Highway Detail) and Ramp Summary's Excel sibling — plus the greyed **Route History** placeholder), the **[capability matrix](#capability-matrix--what-the-app-can-do-with-each-report)** (what the app can do with each report today), each report's per-export behavior (`ReportSpec`, save strategy, empty/ready detection), why the site greys reports out (`cs-disabled`), the **[integration ladder](#the-integration-ladder--every-touchpoint-when-a-report-levels-up)** (every touchpoint when a report gains a tier), and the three "add a new X" recipes (report type, consolidator, comparison).

Deep Highway Log internals live under [highway_log/](highway_log/columns.md) -- the corrected 31-column labels in [highway_log/columns.md](highway_log/columns.md), PDF/TSN parsing in [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md), and the PDF-vs-Excel/TSN study in [highway_log/comparison-study.md](highway_log/comparison-study.md). The comparison workbook engine is owned by [comparison-engine.md](comparison-engine.md).

## The report catalog

| # | Report | Output | Folder |
|---|---|---|---|
| 1 | TSAR: Ramp Summary | PDF (Letter) | `output/<run>/ramp_summary/` |
| 1b | TSAR: Ramp Summary (Excel) | XLSX (export-only) | `output/<run>/ramp_summary_excel/` |
| 2 | TSAR: Ramp Detail | XLSX | `output/<run>/ramp_detail/` |
| 2b | TSAR: Ramp Detail (PDF) | PDF (Letter, landscape) | `output/<run>/ramp_detail_pdf/` |
| 3 | Highway Sequence Listing | XLSX | `output/<run>/highway_sequence/` |
| 3b | Highway Sequence Listing (PDF) | PDF (Letter, portrait) | `output/<run>/highway_sequence_pdf/` |
| 4 | Highway Log | XLSX | `output/<run>/highway_log/` |
| 4b | Highway Log (PDF) | PDF (Letter, landscape) | `output/<run>/highway_log_pdf/` |
| 5 | Intersection Summary | XLSX | `output/<run>/intersection_summary/` |
| 5b | Intersection Summary (PDF) | PDF (Letter, portrait; export-only) | `output/<run>/intersection_summary_pdf/` |
| 6 | Intersection Detail | XLSX | `output/<run>/intersection_detail/` |
| 6b | Intersection Detail (PDF) | PDF (Letter, landscape) | `output/<run>/intersection_detail_pdf/` |
| 7 | Highway Detail | XLSX | `output/<run>/highway_detail/` |
| 7b | Highway Detail (PDF) | PDF (Letter, landscape) | `output/<run>/highway_detail_pdf/` |
| 8 | Highway Summary | XLSX (export-only) | `output/<run>/highway_summary/` |
| — | Route History Table | *(none — greyed reserved placeholder, v0.25.1)* | — |

`<run>` is a run folder, `"<YYYY-MM-DD> <src>-<env>"` (e.g. `2026-06-11 ssor-prod`) -- see [engine-and-reliability.md](engine-and-reliability.md) for run-folder mechanics.

The catalog (`scripts/report_catalog.py`) is the single source of truth for report metadata (P4); `reports.py` derives `EXPORT_REPORTS` from it, feeding the GUI checkboxes and `export_multi.py`, so the list can't drift. The `.bat` menus keep their own text, with a registry-parity check for the consolidate menu (`build/check_report_catalog.py`). Each row is `(menu label, format hint, ReportSpec)`. **Console** numbering follows `EXPORT_REPORTS` order; the **GUI picker** is grouped to mirror the website — its order comes from the catalog's `_PICKER_ORDER` / `picker_order()` and each entry's optional `group` + `short_label` (v0.18.1; see [Report grouping & site-menu-safe selection](#report-grouping--site-menu-safe-selection-v0181) below).

## Capability matrix — what the app can do with each report

The at-a-glance status of every export type across the app's capability tiers, as of
**v0.26.0**. Derived from `report_catalog.py` (EXPORT / CONSOLIDATE / COMPARE / TSN) +
`visual_evidence._ADAPTER_MODULES` — when a tier lands or a report is added, update this
table in the same change.

| # | Export type (stable key) | Saves as | Consolidate | vs TSN | PDF↔Excel self-check | Cross-env | Matrix rows | Evidence images |
|---|---|---|---|---|---|---|---|---|
| 1 | TSAR: Ramp Summary (`ramp_summary`) | PDF | ✓ (parses its own PDFs) | ✓ aggregate | n/a | ✓ | ✓ | — (aggregate ⁵) |
| 1b | TSAR: Ramp Summary (Excel) (`ramp_summary_excel`) | XLSX | — ¹ | — ¹ | — ¹ | — ¹ | — ¹ | — |
| 2 | TSAR: Ramp Detail (`ramp_detail`) | XLSX | ✓ | ✓ flat | n/a | ✓ | ✓ | ✓ |
| 2b | TSAR: Ramp Detail (PDF) (`ramp_detail_pdf`) | PDF | ✓ | ✓ (+ the print-only On/Off + Ramp Type ²) | ✓ | ✓ | ✓ | ✓ |
| 3 | Highway Sequence Listing (`highway_sequence`) | XLSX | ✓ | ✓ flat, county+PM key | n/a | ✓ | ✓ | ✓ |
| 3b | Highway Sequence Listing (PDF) (`highway_sequence_pdf`) | PDF | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 4 | Highway Log (`highway_log`) | XLSX | ✓ | ✓ flat, roadbed/ditto-aware | n/a | ✓ | ✓ | ✓ |
| 4b | Highway Log (PDF) (`highway_log_pdf`) | PDF | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 5 | Intersection Summary (`intersection_summary`) | XLSX | ✓ (category counts) | ✓ aggregate | n/a | ✓ | ✓ | — (aggregate ⁵) |
| 5b | Intersection Summary (PDF) (`intersection_summary_pdf`) | PDF | — ¹ | — ¹ | — ¹ | — ¹ | — ¹ | — (aggregate ⁵) |
| 6 | Intersection Detail (`intersection_detail`) | XLSX | ✓ | ✓ flat | n/a | ✓ | ✓ | ✓ |
| 6b | Intersection Detail (PDF) (`intersection_detail_pdf`) | PDF | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 7 | Highway Detail (`highway_detail`) | XLSX | ✓ | ✓ flat, canonical roadbed key | n/a | ✓ | ✓ | ✓ |
| 7b | Highway Detail (PDF) (`highway_detail_pdf`) | PDF | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 8 | Highway Summary (`highway_summary`) | XLSX ³ | — ³ | — ³ | — | — ³ | — ³ | — ³ |
| — | Route History Table (`route_history`) | — ⁶ | — | — | — | — | — | — |

Plus one **consolidate-only source** (not an export type): **TSN Highway Log (PDF)**
(`cons:tsn_highway_log`) — TSN district prints the user drops into
`input/tsn_highway_log/` (the only consolidator with an input drop folder).

**Footnotes — the current gaps, each with its unlock:**

1. **The v0.25.1 editions are export-only for now.** Ramp Summary (Excel) (id 13, the
   site's `rs_exportToExcel` — an AOA workbook of the same count tables the PDF
   consolidator already extracts) and Intersection Summary (PDF) (id 14,
   `ints_printAll`) ship as exports; consolidate-side integration waits for real
   work-PC files to verify against (Lesson 13), and is low-value until someone needs
   it — both reports' counts already consolidate + compare through their sibling
   editions.
2. **Ramp Detail (PDF) graduated to fully integrated in v0.26.0** (the Highway
   Sequence (PDF) path: export v0.24.0 → the rest off the first real work-PC print
   set, `ground-truth/All Reports 7.9`). The print carries TWO columns the Excel
   export DROPS — the On/Off indicator and the Ramp Type letter — which TSN's
   database also carries, so the PDF-vs-TSN flavor COMPARES them (they stay context
   in the Excel flavor and the PDF↔Excel self-check). See
   [Ramp Detail (PDF)](#ramp-detail-pdf--the-fully-integrated-print-edition-export-v0240-the-rest-v0260)
   for the censused conventions + canaries.
3. **Highway Summary is export-wired but site-greyed** (`cs-disabled` on every capture
   through Dev 7.9) — `select_report` fails fast with "currently unavailable" until
   the vendor turns it on; consolidate/compare integration then waits for a real
   statewide export to verify a schema against (the standard Lesson-13 sequence).
4. **Where each report lives (site-side, as of 2026-07-10):** EVERY enabled report
   now exports from the **production** site — the late-2026-07-09 prod rollout
   un-greyed Intersection Summary/Detail and Highway Detail (verified on both data
   sources in `ground-truth/All Reports 7.9`), ending the dev-site dependency.
   Highway Summary is still greyed everywhere; Route History exists on dev only.
5. **Evidence images require a row-level comparison and a TSMIS PDF edition** — the
   generator renders the exact differing CELL from both systems' prints. The two
   aggregate comparisons (Ramp Summary, Intersection Summary) compare statewide
   category COUNTS, so there is no per-row cell to render; they are named in the
   toggle's no-support line by design.
6. **Route History Table is a wired-but-DISABLED placeholder** (stable id 15,
   v0.25.1 — the v0.18.1 reserved-groundwork pattern): the dev site's new report is
   an embedded SSRS page (`route_history.js` iframes the TSN report server; users
   pick parameters in the SSRS panel) with NO export control, so there is nothing
   for the engine to drive. It shows greyed in the picker
   (`reports.DISABLED_EXPORT_SUBDIRS`); if the site later gives it an export flow,
   enabling it = write the real save + empty the gate.

**Cross-cutting engine capabilities** (all reports, unless noted): resume + retry +
skip/cancel + fast-fail per route; **fast mode** (6 parallel browsers; no coalescing);
**coalescing** (standard path: selecting both editions of one report generates each
route once — HL, ID, HD, HSL, RD pairs); **auto-consolidate on export finish** (the
seven `_AUTO_CONSOLIDATOR` families — the PDF editions consolidate via the matrix
instead, needing a scratch convert dir); the **Everything matrix** + **Compare by-day
matrix** (one row per comparison-integrated family; env / vs-TSN / vs-Excel modes per
row); **on-demand per-cell evidence cameras** on built, fresh vs-TSN cells (the
evidence-capable rows above).

TSN-side datasets backing the vs-TSN column (`report_catalog.TSN`; the library
normalizes each raw source once and caches it — see
[tsn-parsers.md](tsn-parsers.md)):

| TSN dataset | Raw source | Norm ver | Evidence prints |
|---|---|---|---|
| `highway_log` | 12 district PDFs | 3 | the same `raw/` prints (`_TSN_PDFS_IN_RAW`) |
| `ramp_detail` | statewide XLSX | 2 | — |
| `ramp_summary` | statewide PDF | 2 | — |
| `intersection_summary` | statewide PDF | 2 | — |
| `intersection_detail` | statewide XLSX | 3 | `pdf/` drop: the ONE statewide TASAS print |
| `highway_sequence` | 12 district PDFs | 2 | the same `raw/` prints (`_TSN_PDFS_IN_RAW`) |
| `highway_detail` | statewide XLSX | 2 | `pdf/` drop: the 12 district prints |

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

### Report 1b -- TSAR: Ramp Summary (Excel) (v0.25.1)
- **Same dropdown option as #1** -- `label="TSAR: Ramp Summary"` -- saved as an Excel workbook via the site's Export button instead of capturing the inline page as a PDF. The INVERSE of the print editions: the Excel sibling of a natively-PDF report. Module `export_ramp_summary_excel.py`; `subdir="ramp_summary_excel"`, `filename=tsar_ramp_summary_route_<ROUTE>.xlsx`. The registry's **menu label** is `"TSAR: Ramp Summary (Excel)"` (display only).
- `wait_js` / `is_empty` are identical to the PDF Ramp Summary (inline render; `Route <route>` or `No ramps found`).
- `save=save_via_export_button` -- the action bar's Export button calls the shared `exportToExcel()` dispatcher, which routes `Ramp_Summary` to `rs_exportToExcel()` (an `XLSX.writeFile` download of the count tables). The engine's no-download fast-fail is the empty backstop (`rs_exportToExcel` no-ops without a summary).
- **Export-only** -- no consolidator yet (the PDF edition's consolidator already extracts the same counts); coalesces with #1 automatically (shared `data_value`).

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
  `consolidate_intersection_detail` (a thin `consolidate_xlsx` wrapper, sheet "Intersection Detail" —
  header pass-through, so it consolidates whatever shape the run's exports carry) auto-consolidate on
  export finish (both in `_CONSOLIDATOR_BY_SUBDIR`); the vs-TSN + cross-env comparators are wired per
  the registry (see [comparison-engine.md](comparison-engine.md) §9e / §9f). The **PDF edition** of
  Intersection Detail has its own consolidator + comparators (Report 6b).
- **July 2026 format (v0.22.0):** the site reshaped the Intersection Detail export to **35 columns**
  (the duplicated second `ML Eff-Date` dropped; the tail renamed to `Xing P/S` + the NEW
  `Xing Line Lgth`; zero-padded postmiles; native Y/N booleans; historical dates; the Location now
  carries the route suffix). `intersection_detail_columns.HEADER` is the 35-column SoT
  (`DESC_IDX = 20`). The comparators **refuse pre-update consolidated workbooks** (header gate on the
  `Xing Line Lgth` tail) with a re-export hint, and the PDF parser refuses pre-update prints
  (unpadded postmiles) — mis-reading the old 36-column shape by the new positions would silently
  corrupt every column from Description on. Export mechanics (`wait_js`/`is_empty`/save) unchanged.
- Labels + formats verified against the live page source: **NO `"TSAR:"` prefix** (unlike the ramp pair), both Excel via the shared Export button.
- **Intersection Summary**: `label="Intersection Summary"`, `subdir="intersection_summary"`, `filename=intersection_summary_route_<ROUTE>.xlsx`. The page never renders an empty notice -- it ALWAYS shows `Total Intersections = N` (including `= 0`) and always offers a working Export. `wait_js` = `EXPORT_READY_JS` or `.ints-total` present. `is_empty` matches the regex `total intersections\s*=\s*0\b` (a zero total; not `= 10`/`= 20`). No hang risk: a drifted marker just reverts to the old benign all-zeros-file behavior, never a stall.
- **Intersection Detail**: `label="Intersection Detail"`, `subdir="intersection_detail"`, `filename=intersection_detail_route_<ROUTE>.xlsx`. The action bar (Export button) renders even for an empty route, plus an empty table row `<td class="hl-empty">No results found.</td>`. `wait_js` = `EXPORT_READY_JS` or `td.hl-empty` present. `is_empty` = `page.locator("td.hl-empty").count() > 0` (structural, robust to wording drift) OR `"no results found"` in body (text fallback). The engine's general no-download fast-fail (`save_via_export_button` -> `EmptyExport`) is the marker-independent backstop.
- **Caveat:** the site's Intersection feature is still under active development -- its empty strings / DOM are a MOVING TARGET. The fixes key on the robust structural signals (`td.hl-empty`, `Total Intersections = 0`) plus the general empty/no-download fast-fail, and must be re-verified once the feature is finalized. Do not hard-lock to `"No results found."`.

### Report 5b -- Intersection Summary (PDF) (v0.25.1)
- **Same dropdown option as #5** -- `label="Intersection Summary"` -- saved as a PDF via the page's own Print layout. Module `export_intersection_summary_pdf.py`; `subdir="intersection_summary_pdf"`; Letter, **portrait** (count tables, like the native Ramp Summary PDF). The registry's **menu label** is `"Intersection Summary (PDF)"` (display only).
- `wait_js` / `is_empty` are identical to the Excel Intersection Summary (`.ints-total` / `Total Intersections = 0`); `is_empty` runs BEFORE save.
- `save=save_intersection_summary_pdf` (in `exporter.py`). UNLIKE the paginated row reports, the Intersection Summary renders fully INLINE, so the site's `ints_printAll()` merely **prepends a cover page** (`.rs-cover`) to the on-screen report, calls `window.print()`, and restores in an `afterprint` listener. The save overrides `window.print` to raise (no dialog; the afterprint restore never fires), verifies the cover + `.ints-total`, re-reads the total as the marker-independent empty backstop, then `page.pdf()` captures cover + report. In `_PAGE_REBUILDING_SAVES` (the innerHTML reassignment re-creates the Export button), so a coalesced run saves the Excel edition first.
- **Export-only** -- no consolidator/comparisons yet (the Excel edition's aggregate comparison covers the counts); coalesces with #5 automatically (shared `data_value`).

### Report 6b -- Intersection Detail (PDF)

The exact parallel of Report 4b (Highway Log (PDF)), forward-ported in v0.18.0 (CR-002).
- **Same dropdown option as #6** -- `label="Intersection Detail"` -- saved as a PDF via the page's own Print layout instead of the Excel Export button. Module `export_intersection_detail_pdf.py`; `subdir="intersection_detail_pdf"`; Letter, **landscape**. The registry's **menu label** is `"Intersection Detail (PDF)"`, but the `ReportSpec`'s `label` stays `"Intersection Detail"` (the dropdown text `select_report` clicks) — the two must not be conflated.
- **Appended LAST** in the export catalog so the seven existing export-op keys keep positions 0–6 — the manifest-v1 integer-index compatibility contract (CR-002-RM4; `batch_manifest._V017_EXPORT_ORDER` index 7 = `intersection_detail_pdf`).
- `wait_js` / `is_empty` are identical to the Excel Intersection Detail (`td.hl-empty` / `"no results found"`); `is_empty` runs BEFORE save, so the PDF render only runs for routes with rows.
- `save=save_intersection_detail_pdf` (in `exporter.py`) — the same print-capture mechanism as `save_highway_log_pdf`: the site's `intd_printAll()` builds the full multi-page layout, `window.print` is overridden to raise so the on-screen restore never runs, then `page.pdf()` captures it; it fails loudly with `ReportError` if the print fn or layout is missing.
- **Consolidator:** `consolidate_tsmis_intersection_detail_pdf.py` parses the PDF route exports into the SAME 35-column July-2026 format (`intersection_detail_columns.HEADER`, Description at index 20) as the Excel export — a two-row-per-record / zebra-shaded PDF parser (both grids from the shaded records' own 21/18-cell bands; rowA = zero-padded postmile, rowB = the print-only integer intersection number, discarded; the vestigial 21st rowA column is warned about if it ever grows data back; pre-update prints are refused with a re-export hint). Statewide parity proof vs the same-run Excel: 217/217 routes, 16,459/16,459 rows, 0 orphans, 0 non-whitespace cell diffs. Like HL-PDF it is NOT auto-consolidated inline (it needs a scratch convert dir — the matrix handles it). **Comparators:** `compare_intersection_detail_pdf` — `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL`, reusing the Excel Intersection Detail's vs-TSN schema/loaders.
- Verified offline against the fake-site fixture (`build/check_intersection_detail_pdf.py`, `build/fake_site/intersection_detail_print.html`). **Live-export verification against TSMIS is owed in v0.18.1** (the dev PC can't reach the dev site).

## Report grouping & site-menu-safe selection (v0.18.1)

Two related changes track how TSMIS presents its report dropdown, which is migrating from a **flat** list to **grouped fly-out menus** (live on the dev site; prod to follow).

### Selecting a report by stable `data_value`, not visible text

The `#customReport` dropdown is moving from flat `li.cs-option` rows (whose visible text **was** the full report name) to nested **`cs-parent` → `cs-submenu`** fly-outs, where a leaf's visible text is just **"Detail" / "Summary"**, the full name sits in `data-label`, and the report's stable id sits in **`data-value`** (== the hidden native `<select>` value). Matching by visible text broke the moment the menu changed (a leaf reads "Detail", not "Intersection Detail").

`report_nav._find_exact_option(page, label, data_value=None)` now matches by **`data-value` first** (exactly one hit wins), falling back to exact `text` / `data-label` for the old flat menu. `_reveal_submenu_if_leaf` hovers the option's `cs-parent` ancestor to open the fly-out before clicking (submenus reveal on CSS `:hover` only). `select_report` / `preflight` thread the spec's `data_value` through; the env-scan probe (`gui_worker._REPORT_OPTIONS_JS` + `check_one`) matches the same way and weighs the parent fly-out's disabled class. **Prod-safe by construction:** a `data_value` match is preferred, but an unset/unmatched `data_value` behaves exactly as the old text match — so the current flat prod menu is unaffected, and exports keep working across the changeover with nothing for the user to do. Locked by the synthetic `build/fake_site/dropdown_nested.html` (driven by `check_fake_site` + `check_export_engine`); each `ReportSpec` carries its `data_value` (see the field table above). The `cs-disabled` rule below is unchanged.

### The picker is grouped like the website

The GUI report picker mirrors the site's own grouping: **flat** Highway Log, Highway Log (PDF), Highway Sequence, Highway Sequence (PDF) and the greyed Route History Table at the top (the site's order), then the **Ramp** and **Intersection** families under their own headings. Order + grouping are catalog-driven, not UI-hardcoded: each `ExportEntry` carries an optional `group` + `short_label`, and `report_catalog._PICKER_ORDER` (exposed as `picker_order()`, import-asserted to cover every export key) fixes the display sequence. `reports.PICKER_ORDER` / `EXPORT_DISPLAY` re-export them; `gui_api` sorts the `reports` payload by `PICKER_ORDER` and sets each entry's `idx` = its **display position** (no app code reads `idx` — it's parity-check metadata only), plus `group` and `short` (the short leaf label, e.g. "Detail"). `ui/app.js` emits an `.option-group` header on each group change and shows `short || label` (indented under its group). Both the Export picker and Export-Everything use the one `fillReportList()`.

### Highway Detail / Highway Summary — Detail FULLY INTEGRATED (v0.20.0); Summary export-only

The site added two more TSAR reports, **Highway Detail** and **Highway Summary**. v0.18.1 scaffolded them as reserved-DISABLED groundwork; **v0.19.1 enabled their EXPORT**; **v0.19.2 added the Highway Detail print-layout PDF edition**; **v0.20.0 integrated Highway Detail end-to-end** (consolidators + vs-TSN / cross-env / PDF↔Excel comparators + TSN library entry + both matrices — see the Highway Detail family section below). Highway Summary stays export-only until the site un-greys it and a schema can be verified:

- **Real modules** `export_highway_detail.py` / `export_highway_summary.py` — each a genuine `ReportSpec` modeled on the Excel siblings (`save = save_via_export_button`). Confirmed against the **7.7 dev capture** (`highway_detail.js` live, action bar wires `hd_exportToExcel()` + `hd_printAll()`): empty = `td.hl-empty` / "No results found in this segment.", matched loosely (`td.hl-empty` OR "No … found"). Highway Detail is un-greyed on 7.7; Highway Summary is still `cs-disabled` there, so its export fail-fasts (`ReportUnavailableError`) until the vendor turns it on.
- **Highway Detail (PDF)** — `export_highway_detail_pdf.py`, `subdir="highway_detail_pdf"`, `data_value="highway_detail"` (same dropdown option), `save=save_highway_detail_pdf` (in `exporter.py`). The twin of `save_highway_log_pdf`: `hd_printAll()` builds the SAME `.hl-print-section` print layout; `window.print` is overridden to raise so the on-screen restore never runs, then `page.pdf()` captures it (Letter, **landscape**, 27 roadbed-grouped columns). Empty backstop counts `.hd-row1` data rows (HD's grouped columns put colspan on real rows, so Highway Log's non-colspan heuristic doesn't apply). **Appended LAST** — stable id **10** (`batch_manifest._V017_EXPORT_ORDER` stays `== EXPORT_KEYS`); `_PICKER_ORDER` places it next to its Excel sibling.
- **The gate is empty** (`reports.DISABLED_EXPORT_SUBDIRS = set()`): all pickable in the Export picker and ticked in Export Everything. Where the **live site** still `cs-disabled`s a report, `select_report` fails fast instead of stalling.
- **Highway Detail** consolidates + compares like every other report as of **v0.20.0** (the env matrix is 10 rows); **Highway Summary** has no consolidator / comparator / TSN entry yet (no real export exists to verify a schema against), so it alone stays absent from the matrices, Consolidate, and Compare. Locked by `check_intersection_gate` (empty gate), `check_report_recipe` (HD registered, HS absent), `check_stable_ids` (append-only 8/9/10), and `check_report_catalog`.

To integrate Highway Summary later: add its consolidator + comparators + `tsn_library` entry per the same recipe (`build/check_report_recipe.py`), verified against a real statewide export first — exactly how Highway Detail was done (tracked in [roadmap.md](roadmap.md)).

### The Highway Detail family (v0.20.0)

Built on the Intersection Detail recipe, verified against the full statewide dev bundle (252 TSMIS routes / 51,243 rows; the 60,083-row statewide TSN extract; all 12 TSN district PDFs cross-checked ≥99.9% field-identical against the extract):

- **`highway_detail_columns.py`** — the 34-column labels SoT (the export's own labels are CORRECT, unlike Highway Log's) + legend meanings, hover tooltips, a Legend sheet, and `recognize()`.
- **`consolidate_highway_detail.py`** — a thin `consolidate_xlsx` wrapper (sheet `"Highway Detail"`, Route column prepended, tooltips + Legend). Auto-consolidates on export finish (`_AUTO_CONSOLIDATOR`).
- **`consolidate_tsmis_highway_detail_pdf.py`** — parses the app's own **Highway Detail (PDF)** export into the SAME 34-column format via `pdf_table_lib`. The print layout is TWO physical lines per record with DIFFERENT geometry (line 1 = 10 cells, line 2 = 25 cells), so TWO window sets are derived from the zebra-shaded bands; DCR group rows (`11 IMP 007`) and page furniture never match the line-1 postmile test. Orphan reconciliation escalates to a producer-owned PARTIAL. **v0.26.0 (the July-print census, off the first real prod set):** line 2 is now "whatever follows the line 1 except the censused furniture" — the old "always carries a TASAS date" rule dropped real records whose roadbed blocks print codes without effective dates, and pages whose grid splits a date across windows; `_is_line1` requires the postmile ALONE (or PM+Length on the fallback grid), so an outdented equate DESCRIPTION starting with a PM-shaped token no longer minted phantom records; a record whose print carries NO second line is kept with a blank attribute tail (`single_line` in stats, an FYI note — not PARTIAL).
- **`tsn_load_highway_detail.py` + the `TsnEntry`** — normalizes the statewide 56-column `TSAR - HIGHWAY DETAIL` Excel extract (`statewide_xlsx`, `normalization_version=2`) into `Highway Detail (TSN)` = `["Route"] + SHARED_HEADER + SIDECAR_HEADER` (v2 appends the TSN District/County sidecar the visual-evidence generator reads; the comparison loader slices to the shared width). The TSN **district PDFs** were verified consistent with the extract and stay reference-only for the comparison — dropped into `tsn_library/highway_detail/pdf/` they feed the evidence images.
- **`compare_highway_detail_tsn.py`** — the FLAT vs-TSN comparator (route + **canonical Post Mile** key). The key unifies the two systems' roadbed encodings (TSMIS glues R/L onto the PM, `'000.080R'`; TSN prints a bare PM with `HG∈{R,L}`) and EXCLUDES the equation marker (the systems disagree on where they print `E` — it is compared as the separate **PS** column instead). Normalizations (each documented in the workbook's **Notes** sheet): TSN `NON_ADD 'A'` ≡ blank, zero-padding (`'02'`≡`'2'`), Length to the printed 3 decimals, `M_WID`+`M_VA` glued to `'14Z'`, whitespace collapse. `RU Eff` is compared BY POSITION against TSN's `BEG_DATE` (the legacy report's ADT begin-date slot — different semantics, differs on ~99% of rows, documented, soft in the Report View). The TSN-only ADT block + `*`/`Y` change flags are not compared (ADT shows in blue on the **Report View**, the printed two-line TASAS replica with Major/Diffs counts).
- **`compare_highway_detail_pdf.py`** — `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL` (the export-correctness self-check), the exact `compare_intersection_detail_pdf` parallel.
- **`visual_evidence.py` + `evidence_highway_detail.py`** (v0.21.0) — the OPTIONAL **evidence images** decoration of the vs-TSN comparisons: for every differing column, sampled random rows rendered as highlighted snippets from BOTH PDFs (the app's (PDF) export + the TSN district prints), each example verified by parse-back before it's shown; `… (evidence).xlsx` + a two-layout image folder beside the comparison. Toggle + per-column count (1–10) on both matrix pages. → [comparison-engine.md](comparison-engine.md) §13.
- Locked by `check_compare_highway_detail_tsn` + `check_highway_detail_pdf` + `check_visual_evidence` (+ the registry/matrix/mock parity checks).

### Highway Sequence (PDF) — the fully-integrated print edition (export v0.24.0, the rest v0.25.0)

Cloned from the Highway Detail (PDF) recipe; the export was confirmed on BOTH site
captures (main `website-source` + `TSMIS Dev Site 7.7`), and the parser/comparisons/
evidence were **censused-first and blessed on the first real work-PC print set**
(`ground-truth/HSL PDF + IS Bundle 7.9`, 252 routes — parse-back 60,493/60,493 rows vs
the 7.8 Excel exports; every residual class explained):

- **`export_highway_sequence_pdf.py`** — `subdir="highway_sequence_pdf"`,
  `data_value="highway_sequence"` (same dropdown option as the Excel sibling),
  `save=save_highway_sequence_pdf`. The site's `hsl_printAll()` builds a cover page + legend
  page + per-district `.hsl-print-table` sections (9 columns); the save overrides
  `window.print` to raise, calls it, counts non-colspan tbody rows as the empty backstop,
  and captures **PORTRAIT** Letter — matching the TSN district prints (612×792).
- **`consolidate_tsmis_highway_sequence_pdf.py`** — parses the per-route prints into the
  SAME 9-column TSMIS format the Excel export produces (header-anchored per-page windows;
  the postmile prefix/suffix in their two unnamed columns). The censused conventions:
  wrapped Descriptions cluster as fragment lines around a vertically-centered data line
  (top-order, HYPHEN-AWARE rejoin — `join_desc_parts`); a few rows carry NO postmile
  ("END OF ROUTE …", "CITY END: …" — matched by their single-letter HG+FT windows);
  EQUATES print the TSN way (annotation row "EQUATES TO <label>" with HG/FT/Distance
  blank + the `E` suffix on the equated plain postmile — the Excel export seats them
  differently BY DESIGN); the last page ends with an "Unresolved Intersections"
  site-diagnostics trailer (hard stop). Values written verbatim; unparsed lines escalate
  to a producer-owned PARTIAL.
- **`compare_highway_sequence_pdf.py`** — `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL`, the
  `compare_highway_detail_pdf` parallel riding `compare_highway_sequence_tsn`'s loaders +
  schema, each flavor with its OWN Notes sheet (the print's TSN-style equates make
  PDF-vs-TSN pair BETTER than Excel-vs-TSN — both 57,505 vs 57,071, diff cells 4,930 vs
  5,521 on the 7.8/7.9 sets — while PDF-vs-Excel documents the equate-representation
  classes; identical 59,082 of 59,946 both, one-sided 547/547). The self-check caught the
  Excel export DROPPING a Description the print carries (route 037 PM 003.809).
- **`evidence_highway_sequence.py`** (v0.25.0) — evidence images for BOTH Highway
  Sequence rows: the highway-log pattern (per-print SENTINEL routing — HSL rows carry no
  district; records carry their own src/dist/cnty from the prints' "DIST NN RTE NNN"
  group headers), diffs judged via `compare_core.compared_cell` so the CONTEXT columns
  (HG/City/Distance) can never enumerate. TSN prints read from
  `tsn_library/highway_sequence/raw/` — the SAME files the TSN library builds from (the
  `_TSN_PDFS_IN_RAW` pattern; no duplicate drop).
- Matrix rows in BOTH matrices (env + vs TSN + vs TSMIS Excel modes; shares the
  `highway_sequence` TSN dataset with its Excel sibling); `cons:highway_sequence_pdf` on
  the Consolidate tab + the console menu. Locked by `check_report_catalog`,
  `check_matrix_tsn`, `check_visual_evidence` (+ the mock parity checks).

### Ramp Detail (PDF) — the fully-integrated print edition (export v0.24.0, the rest v0.26.0)

The last export-only print edition graduated exactly the Highway Sequence (PDF) way:
censused-first and blessed on the first real work-PC print set
(`ground-truth/All Reports 7.9`, 126 routes — parse-back **15,216/15,216 rows**
route-for-row against the SAME-DAY Excel exports; zero unclassified lines, zero stray
fragments, every residual cell class explained):

- **`export_ramp_detail_pdf.py`** — `subdir="ramp_detail_pdf"`, `data_value="Ramp_Detail"`,
  `save=save_ramp_detail_pdf`. Ramp Detail has **no `rd_printAll`**: its print body IS the
  site's shared async `printAll()` dispatcher, which first `await`s a
  `showPrompt('Enter report title:')` modal. The save overrides BOTH globals —
  `window.print` raises, `showPrompt` resolves immediately with a route-derived title (no
  modal ever opens) — and awaits the dispatcher under a `Promise.race` bound
  (`_RAMP_DETAIL_PRINT_BUILD_MS`) so a future unanswered await fails the route loudly
  instead of hanging it. Captures **LANDSCAPE** Letter (the TSN statewide Ramp Detail print
  is 792×612). Marker `.rd-print-table` (11 columns). Stable ids 11/12 (with Highway
  Sequence (PDF)); coalesces with its Excel sibling (shared `data_value`).
- **`consolidate_tsmis_ramp_detail_pdf.py`** — parses the per-route prints into the Excel
  export's EXACT layout (its column-shifted header included, so the combined workbook is
  position-compatible with the Excel-consolidated one) **plus the two PRINT-ONLY columns
  the Excel export drops** — the On/Off indicator (N/F/Z) and the Ramp Type letter —
  appended after it with real labels. Header-anchored per-page word windows (the three
  single-letter header columns located BETWEEN the multi-letter anchors, never by bare
  text); Descriptions never wrapped statewide (the fragment machinery is kept as a loud
  safety net); the print renders EMPTY fields visibly ("-" in Area 4 / On/Off, the
  Description message "NO RAMP LINEAR EVENT" — 59 statewide rows, the ramp points
  without linework Ramp Summary counts). Values written verbatim; unparsed lines escalate
  to a producer-owned PARTIAL.
- **`compare_ramp_detail_pdf.py`** — `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL`, riding
  `compare_ramp_detail_tsn`'s locked schema via `dataclasses.replace`, each flavor with
  its OWN Notes sheet. The PDF flavors project the censused render artifacts at compare
  time (the workbook stays verbatim): Description whitespace runs collapse on BOTH sides
  (the database — so the Excel export AND the TSN extract — carries literal double
  spaces the HTML print collapses), the null-render tokens project to blank, and the
  print's On/Off letters (N/F/Z) project to TSN's (O/F/Z). **On/Off + Ramp Type GRADUATE
  from context to compared in the PDF-vs-TSN flavor** — the print carries data the Excel
  export doesn't, so the PDF side verifies two more columns against TSN (Ramp Name/ADT
  stay context; the Excel flavor and the PDF↔Excel check keep all four context).
  PDF↔Excel on the same-day statewide pair: **both 15,216, one-sided 0/0, 15,212 fully
  identical** — the only 4 differing cells are the Excel's literal `_x000d_` line-break
  escapes (route 010's rest-area ramps) the print omits, the same honest class HSL's
  self-check carries.
- **`evidence_ramp_detail.py`** — evidence images for BOTH Ramp Detail rows: the
  Intersection Detail pattern on the TSN side (ONE statewide TASAS print, fixed column
  template — header anchors pixel-identical across its 500 pages, censused 400/400
  records against the raw extract — indexed once per file and cached) + the
  consolidator-LOCKSTEP word-window locator on the TSMIS side. The adapter serves the
  two rows' DIFFERENT compared sets (the consolidated workbook names its source — the
  PDF-consolidated carries the "On/Off" header — so the Excel row never enumerates the
  print-only columns). The RD TSN library gained the District/County sidecar
  (`tsn_load_ramp_detail`, normalization **v3**, split from LOCATION "01-DN-101"; D2
  auto-rebuild); the TSN print lives in `tsn_library/ramp_detail/pdf/` (the
  statewide-XLSX-sourced pattern, like Intersection Detail). Known skip-classes recorded
  honestly: the TSN print TRUNCATES long Descriptions; on the Excel row the compared
  Description keeps the database's double spaces the print collapses.
- Matrix rows in BOTH matrices (env + vs TSN + vs TSMIS Excel modes; shares the
  `ramp_detail` TSN dataset with its Excel sibling); `cons:ramp_detail_pdf` on the
  Consolidate tab + the console menu. Locked by `check_report_catalog`,
  `check_matrix_tsn`, `check_visual_evidence` (+ the mock parity checks).

### Route History Table — reserved, app-wide DISABLED (v0.25.1)

The dev site added a **"Route History Table"** report on 2026-07-09 (`data_value="route_history"`, a flat top-level option). It is NOT a query report: selecting it drops into an **embedded SSRS report** (`route_history.js` iframes the TSN report server; District/County/Route/Date are picked in the SSRS parameter panel), with **no export control** — nothing for the engine to drive. The app wires it as **reserved-DISABLED groundwork** (the exact v0.18.1 Highway-pair path): `export_route_history.py` holds a minimal placeholder spec (its `save` raises loudly if ever reached), stable id **15** is reserved (`batch_manifest` appended), and `reports.DISABLED_EXPORT_SUBDIRS = {"route_history"}` shows it **greyed** in the picker while the start guards reject its key server-side. If the site later gives Route History an export flow: write the real save, empty the gate, and update `check_intersection_gate`'s `_RESERVED`.

### Coalescing both editions of a report (v0.19.2)

When the user selects **both editions of one on-site report** — the two formats share a `data_value` (Highway Log, Intersection Detail, Highway Detail; Highway Sequence + Ramp Detail joined in v0.24.0; Ramp Summary + Intersection Summary in v0.25.1) — the standard (sequential) export path generates the report **once per route** and saves both files off that single render, instead of generating it twice. `ExportWorker._run_specs` groups the selected specs by `data_value` (`_coalesce_groups`) and runs a pair through `exporter.run_export_combined`; the **Export-button save runs first** and the **DOM-rebuilding PDF Print save last** (`_PAGE_REBUILDING_SAVES` / `_save_rebuilds_page`), because `hl_printAll`/`intd_printAll`/`hd_printAll` replace `#rampResults` and would remove the Export button. Each edition keeps its own `RunResult`, staging/swap, run report, and auto-consolidation (`_prep_edition` / `_finish_edition`). **Scope:** the single-report `run_export` and the parallel engine are untouched; **fast mode** keeps each edition its own parallel pass (coalescing the parallel engine, and the console `run_cli_multi`, are follow-ups). Locked by `build/check_coalesce_editions.py`.

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

## The integration ladder — every touchpoint when a report levels up

A report climbs four tiers: **export → consolidate → compare (vs TSN / env / self) →
evidence**. Each tier below lists EVERY file/registry a change touches — the recipes
that follow hold the per-file detail; this is the completeness checklist (the v0.17.3
lesson: a missed special-case in one of these shipped a field crash). The proven
sequence for a print edition is Highway Detail (v0.19.2 export → v0.20.0 full) and
Highway Sequence (v0.24.0 export → v0.25.0 full): **ship the export first, then
census real work-PC output before blessing any parser (Lesson 13)** — never integrate
off synthetic renders.

**Tier 0 — Export** ([recipe](#recipe-add-a-new-report-type)):
- [ ] `scripts/export_<name>.py` (`ReportSpec`: `label`, **`data_value`** from the site
      capture, `subdir`, `filename`, `wait_js`, `is_empty`, `save`) + `run_cli`.
- [ ] For a **print edition**: the site's print-function name from the capture
      (`*_printAll` or the shared `printAll()` dispatcher), a `save_*_pdf` in
      `exporter.py` (override `window.print` to raise; fail loudly on missing
      fn/layout), portrait/landscape matched to the TSN print, membership in
      `_PAGE_REBUILDING_SAVES` (coalescing order), an empty-backstop row count.
- [ ] `report_catalog.EXPORT` — **append LAST** (stable ids are append-only;
      `batch_manifest._V017_EXPORT_ORDER == EXPORT_KEYS` must keep holding), plus
      `_PICKER_ORDER` + optional `group`/`short_label`.
- [ ] `3. run export...bat` + `5. fast export...bat` branches; `build/app.spec`
      `APP_MODULES`; `scripts/ui/mock.js` report list; `output/<subdir>/.gitkeep` +
      `.gitignore`; `build/check_report_catalog.py` frozen baseline (+
      `check_stable_ids`).
- [ ] Docs: the catalog table here + CLAUDE.md's table + CHANGELOG.

**Tier 1 — Consolidate** ([recipe](#recipe-add-a-new-consolidator)):
- [ ] `scripts/consolidate_<name>.py` — console-free, day-aware
      (`consolidate(events, confirm_overwrite, day=None)` + `input_dir_for` /
      `out_path_for`), transactional write (temp + `os.replace`, keep-last-good),
      producer-owned completion (`outcome.py` from structured counts) + the
      `consolidation_meta` sidecar. XLSX report → wrap `consolidate_xlsx`; PDF/print
      → a standalone parser censused on real exports first.
- [ ] `report_catalog.CONSOLIDATE` entry; `_AUTO_CONSOLIDATOR` **only for Excel-input
      families** (PDF-sourced consolidators need a scratch convert dir — the matrix
      runs them via `matrix_build._pdf_store_consolidator` instead).
- [ ] `4. consolidate...bat` menu entry + renumber (registry-parity-checked);
      `APP_MODULES`; mock.js `CONS_REPORTS` + consolidate radios; baselines.

**Tier 2 — Compare** ([recipe](#recipe-add-a-new-comparison-type); comparisons ride
`compare_tsn_common` over the regression-locked `compare_core` — never hand-roll):
- [ ] **Hand-reconcile the two raw files FIRST** and lock the approved counts as
      canaries in [tsn-parsers.md](tsn-parsers.md).
- [ ] `report_catalog.TSN` `TsnEntry` (raw kind + lazy builder +
      `normalization_version` — bump it on EVERY normalizer behavior change, or the
      cached library silently bypasses the change) + the `tsn_load_*`/builder module.
- [ ] `scripts/compare_<name>_tsn.py` (flat / aggregate / composite-key per the
      references) and, for a PDF edition, `compare_<name>_pdf.py` with
      `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL` flavors riding the Excel module's
      loaders/schema.
- [ ] `report_catalog.COMPARE` rows (`tsn` + `env`; PDF↔Excel lives under `env`);
      `compare_env.EnvCompare` (+ `flat_pdf_loader` for a PDF edition).
- [ ] **Matrix wiring — mirror EVERY special-case, not just labels:**
      `matrix_state._row_modes` + `tsn_comparator_for` + `_pdf_self_comparator`;
      `matrix_build._pdf_store_consolidator`; `day_matrix`'s pdf-format tuple;
      `gui_worker_maint` delete lists (legacy output dirs + consolidated filenames).
- [ ] Golden check `build/check_compare_<name>_tsn.py` wired into
      `.github/workflows/checks.yml`; row-count pins in `check_matrix` /
      `check_matrix_tsn` / `check_matrix_bridge` / `check_compare_env_*`; mock.js
      matrix rows + `mockMatrixModes` + compare radios (picker-family order).
- [ ] Docs: [comparison-engine.md](comparison-engine.md) §9 tables +
      [tsn-parsers.md](tsn-parsers.md) schema/canaries.

**Tier 3 — Evidence images** (needs a ROW-LEVEL vs-TSN comparison + a TSMIS PDF
edition + TSN prints; → [comparison-engine.md](comparison-engine.md) §13):
- [ ] `scripts/evidence_<name>.py` — the TSMIS locator as the word-object-keeping
      TWIN of the consolidator's classifier (pin them identical in
      `check_visual_evidence`), projections through the comparator's own normalizers,
      diffs judged via `compare_core.compared_cell` (context/ditto cells can never
      enumerate), district routing (sidecar columns, or the HL/HSL per-print SENTINEL
      when the report carries no district).
- [ ] `visual_evidence.py` registration: `_ADAPTER_MODULES` (BOTH rows of the family),
      `TSMIS_PDF_SUBDIR`, `TSN_PDF_REPORT`, `_TSN_PDF_LABELS`, and `_TSN_PDFS_IN_RAW`
      if the TSN prints ARE the library's raw inputs; else set
      `TsnEntry.evidence_pdfs=True` so `ensure_layout` creates + hints the `pdf/`
      drop folder.
- [ ] `self_test._DYNAMIC_REPORT_MODULES` + `APP_MODULES` (the adapter loads
      dynamically); `check_visual_evidence` pins (fields/maps/projection/classifier
      fixtures); mock.js evidence block (rows, reports, `row_reports`, unsupported
      list); e2e on real data before shipping (examples must parse-back-verify).

**Every tier:** run the FULL release gate (`build/run_checks.py -j 4 -k` + byte-compile
+ ruff + `build.ps1 -SelfTest`) — a subset once shipped a field crash — and update the
[capability matrix](#capability-matrix--what-the-app-can-do-with-each-report) above.

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
- `"Intersection Detail"` (`consolidate_intersection_detail`, v0.17.0) -- a thin `consolidate_xlsx` wrapper (sheet "Intersection Detail"; 35 cols since the July-2026 site update — the wrapper passes the files' own header through), day-aware; also in `_CONSOLIDATOR_BY_SUBDIR` so it auto-consolidates on export finish and the matrix can build its vs-TSN cell. (Intersection Summary's consolidator — `consolidate_intersection_summary`, a category-count summer — is registered too.)

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
- `group="env"` -- every report's **between-environments** comparison (Ramp Summary/Detail, Highway Sequence, Highway Log, **Intersection Summary/Detail**, **Highway Detail**, and the three **PDF editions** — Highway Log (PDF) + Intersection Detail (PDF) + Highway Detail (PDF)), plus the three **PDF-vs-Excel** consistency self-checks (Highway Log, Intersection Detail, Highway Detail) which also live in `env`.
- `group="tsn"` -- the file-based **TSMIS-vs-TSN** comparisons. COMPLETE for all 10 comparison-integrated export types (Highway Log Excel/PDF, Ramp Detail, Ramp Summary, Intersection Summary, Intersection Detail Excel/PDF, Highway Sequence, Highway Detail Excel/PDF — the last pair v0.20.0). The PDF editions' PDF-vs-Excel self-checks live under `env`, not `tsn`. (Highway Summary is export-only — no vs-TSN comparator yet, so it isn't here.)
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
