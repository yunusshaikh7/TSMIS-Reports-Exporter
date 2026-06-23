# Forward-port handoff — what `main` gained after v0.17.1

**Read this before merging `refactor/v0.18.0-structural-overhaul` back into `main`.**

The refactor branched from **v0.17.1**. While it was in flight, `main` shipped three
patch releases (**v0.17.2 → v0.17.4**) plus follow-up commits. This document is the
complete record of that divergence so the merge can forward-port / reconcile every
change — including the docs.

- **Commit range:** `v0.17.1..main` (current tip `0155b39`).
- **My work (the substance):** `d2ee353..main` — 5 commits, **32 files, +1,297 / −80**.
- **Two commits in the range predate this work** (already on `main` at v0.17.1+,
  small): `d2ee353` *docs: reconcile roadmap to v0.17.1*, `4e38a63` *chore: harden
  .gitignore against legacy TSN output* (the latter also nudged
  `consolidate_tsn_highway_log.py` / `consolidate_tsn_highway_sequence.py` output
  paths). Low-risk; mentioned only so the range reconciles.

---

## TL;DR — the one principle for the merge

**Everything here is one feature: Intersection Detail (PDF) — built as an exact
parallel of the existing `highway_log_pdf` report.** A v0.17.2 hotfix first added
the *export*, then v0.17.3 gave it the full treatment (consolidate + compare + both
matrices), v0.17.4 fixed a crash from that, and a doc commit logged one deferred
issue.

So the merge rule is simple: **wherever the refactor moved/renamed/restructured
`highway_log_pdf`, apply the identical structural change to `intersection_detail_pdf`.**
They are siblings in every subsystem (export, consolidate, compare, matrix, registry,
build, UI mock, checks). The wiring map in §3 lists every touch point as a
HL-PDF ↔ Int-Detail-PDF pair.

**The one gotcha that already bit us (don't lose it in the merge):**
`intersection_detail_pdf` is **deliberately absent from `reports._CONSOLIDATOR_BY_SUBDIR`**
(like `highway_log_pdf`, it needs a scratch `converted_dir` to parse PDFs first). That
means it MUST be wired into `matrix._pdf_store_consolidator()` — the helper feeding
both `_consolidated_filename` and `_consolidate_store_folder`. v0.17.3 added the matrix
*row* but missed that helper, and the app **crashed** opening the by-day matrix
(`ValueError: no consolidated filename for intersection_detail_pdf`). v0.17.4 fixed it
and added a regression check. If the refactor reorganizes the matrix/consolidator
plumbing, preserve this wiring.

---

## 1. Releases (what shipped, in order)

| Tag / commit | What | Headline |
|---|---|---|
| **v0.17.2** `27dcdb3` | Intersection Detail (PDF) **export** | A print-ready PDF export of Intersection Detail, mirroring Highway Log (PDF). Export-only. |
| **v0.17.3** `84d39d3` | **consolidate + compare + matrices** | Full HL-PDF parity: a PDF→36-col consolidator, 3 comparisons (cross-env, vs-TSN, PDF-vs-Excel), a full row in both matrices. |
| `b70a644` | CI fix (post-v0.17.3) | A golden check asserted HL-PDF was the *last* matrix row; the new row displaced it → assert membership instead. |
| **v0.17.4** `180c6e4` | **crash hotfix** | Wired `intersection_detail_pdf` into the matrix's consolidated-workbook helpers (the by-day matrix crashed without it) + a regression check + cleanup parity. |
| `0155b39` | docs (deferred issue) | Logged the `_xl_trim` tab-whitespace comparison gap (see §5). |

All three releases were built + published by `release.yml` (frozen self-test gates
passed); `checks.yml` is green on `main`.

---

## 2. New files (create-equivalents for the merge)

| File | Lines | Purpose | HL-PDF sibling |
|---|---|---|---|
| `scripts/export_intersection_detail_pdf.py` | 54 | `ReportSpec` for the PDF export (same `"Intersection Detail"` dropdown option as the Excel export; `subdir="intersection_detail_pdf"`; `save=save_intersection_detail_pdf`). | `export_highway_log_pdf.py` |
| `scripts/intersection_detail_columns.py` | 34 | The canonical **36-column** Intersection Detail header (one source of truth; matches the Excel export incl. the `Intrte S`/`Intrte Route` swap). | `highway_log_columns.py` |
| `scripts/consolidate_tsmis_intersection_detail_pdf.py` | 490 | The PDF parser + consolidator → 36-col TSMIS format. **The hard part.** See §4. | `consolidate_tsmis_highway_log_pdf.py` |
| `scripts/compare_intersection_detail_pdf.py` | 106 | The two file-vs-file adapters: `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL` (thin wrappers reusing `compare_intersection_detail_tsn`'s loaders/schema, relabeled). | `compare_highway_log_pdf.py` |
| `build/check_intersection_detail_pdf.py` | 140 | Golden check: locks the 36-col header, the rowA/rowB→36-col mapping (incl. the Intrte swap + merged Description), the adapter/matrix wiring, AND a **regression test that every matrix row resolves a consolidated filename** (the v0.17.4 crash class). | (covered the v0.17.4 fix) |
| `build/fake_site/intersection_detail_print.html` | 63 | Synthetic Print-layout fixture for `check_fake_site.py` (drives the real `page.pdf()` save). | `highway_log_print.html` |
| `output/intersection_detail_pdf/.gitkeep` | 0 | Output-folder stub (gitignore-whitelisted). | `output/highway_log_pdf/.gitkeep` |

---

## 3. Wiring map — every modified file (the HL-PDF ↔ Int-Detail-PDF parallel)

Each row is a place `highway_log_pdf` already appeared; v0.17.x added the
`intersection_detail_pdf` parallel. **If the refactor changed the HL-PDF side, mirror it here.**

### Core engine
- **`scripts/exporter.py`** (+47) — added `save_intersection_detail_pdf()`. Same
  technique as `save_highway_log_pdf()` (override `window.print` so the site's
  `intd_printAll()` full-table layout stays in the DOM for `page.pdf()`); the only
  difference is the "layout built" marker (`.intd-table` present + `.export-btn`
  stripped, vs HL's `.hl-print-section`).
- **`scripts/reports.py`** (+32) — 3 imports + **EXPORT_REPORTS** row (`"Intersection
  Detail (PDF)"`, appended last → no index shift), **CONSOLIDATE_REPORTS** row
  (`"TSMIS Intersection Detail (PDF)"`), **3 COMPARE_REPORTS** rows (cross-env +
  PDF-vs-TSN + PDF-vs-Excel, appended last). NOTE: deliberately **not** in
  `_CONSOLIDATOR_BY_SUBDIR` (see TL;DR gotcha) — the comment there now says so.
- **`scripts/matrix.py`** (+61) — the most structurally sensitive file:
  - new helper **`_pdf_store_consolidator(subdir)`** → returns the consolidator for
    the two PDF reports (HL-PDF, Int-Detail-PDF); used by BOTH `_consolidated_filename`
    and `_consolidate_store_folder` (DRY'd so a future PDF report is wired in one place).
  - `_row_modes()` branch (env + vs-TSN + vs-Excel; `tsn_subdir="intersection_detail"`
    — shares the Excel report's TSN dataset, like HL-PDF shares `highway_log`).
  - `tsn_comparator_for()` branch → `compare_intersection_detail_pdf.TSMIS_PDF_VS_TSN`.
  - the vs-Excel self-compare was **generalized** (picks comparator + PDF-side by
    `_pdf`-suffix / `intersection_detail` prefix instead of the literal
    `"highway_log_pdf"`).
- **`scripts/compare_env.py`** (+42) — `INTERSECTION_DETAIL_PDF` `EnvCompare` (flat,
  route+PM key, `flat_pdf_loader`) + `_load_intersection_detail_pdf_side()` (consolidate
  the PDFs to a temp dir, read flat). Direct mirror of `HIGHWAY_LOG_PDF` /
  `_load_highway_log_pdf_side`.
- **`scripts/day_matrix.py`** (+2) — `fmt="pdf"` branch in `_day_rows()` (mirrors the
  HL-PDF branch).
- **`scripts/gui_worker.py`** (+9) — added `intersection_detail_pdf` + the scratch
  `tsmis_intersection_detail_pdf` dir + the `…_consolidated.xlsx` to the "Delete all
  reports" cleanup (parity with HL-PDF).

### Build / packaging
- **`build/app.spec`** (+8) — `APP_MODULES` += `intersection_detail_columns`,
  `consolidate_tsmis_intersection_detail_pdf`, `export_intersection_detail_pdf`,
  `compare_intersection_detail_pdf`. **Required** (lazy imports won't be frozen otherwise).
- **`.gitignore`** (+3 in my range) — whitelist `output/intersection_detail_pdf/` +
  ignore its contents + keep its `.gitkeep`.
- **`3. run_export (main script).bat`** / **`5. fast export (experimental).bat`**
  (+11 each) — console menu option **8** + dispatch + label block; prompt range `1-7`→`1-8`.

### UI (preview only — real GUI reads the registry)
- **`scripts/ui/app.js`** (+48) — `#mock` fixtures only: the export list, consolidate
  list, the 3 compare rows, and both matrix mocks (rows, modes, per-row TSN dataset,
  sample data). No functional code — the live GUI renders from `reports.py`.

### Checks
- **`build/check_intersection_detail_pdf.py`** — NEW (see §2).
- **`build/check_fake_site.py`** (+39) — added the Int-Detail-PDF save test + the spec
  to the wait/empty fixture sweep.
- **`build/check_intersection_gate.py`** (+38) — now derives the expected export-report
  count from the registry (was hard-coded "seven"; rather than bump to 8 each time).
- **`build/check_matrix.py` / `check_matrix_bridge.py` / `check_matrix_tsn.py`** — the
  matrix row set is now **8** (was 7); the hide-all test hides 7 and rejects the 8th.
- **`build/check_compare_env_highway_log_pdf.py`** (`b70a644`) — assert HL-PDF is *a*
  matrix row (membership), not the *last* one.
- **`.github/workflows/checks.yml`** (+1) — wired `check_intersection_detail_pdf` into
  the comparison-engine loop.

> **Merge watch-out:** if the refactor changed the matrix row set or order, the
> "8 rows" / "hide 7 reject the 8th" assertions in the three matrix checks will need
> reconciling again.

---

## 4. The PDF parser (the genuinely new logic)

`consolidate_tsmis_intersection_detail_pdf.py` is the only piece without a copy-paste
HL sibling — the layout differs. Key facts the merge must preserve:

- Each intersection is **two physical table rows** (`intd_renderRow`: a 21-cell rowA +
  an 18-cell rowB whose wide Description spans 4 grid columns).
- The site **zebra-shades alternate records, and only shaded rows carry cell rects** —
  so a naïve rect parser drops every other record. The parser derives the 21-column
  grid **once** from the shaded rowA bands (the print layout is one table → uniform
  widths) and assigns **every** text line to that grid, pairing each rowA (numeric Post
  Mile) with the rowB after it.
- rowA → cols 0–20 (1:1). rowB → Description (merged window over grid cols 3–6) = col 21,
  fields → cols 22–35, **with the `Intrte S`/`Intrte Route` pair swapped** to match the
  Excel export's column order.
- **Verified:** reconciled against all **218 routes statewide → 0 content differences**
  vs the Excel export (the only residual is Description whitespace, absorbed by the
  comparison engine's `_xl_trim`). The mapping is locked by `check_intersection_detail_pdf.py`.

(Real PDF/Excel/TSN ground truth is **LOCAL ONLY** under `C:\Users\Yunus\Downloads\TSMIS\…`
— never committed; the reconciliation ran there.)

---

## 5. Deferred follow-up logged (do NOT lose in the merge)

`0155b39` documented a real-but-cosmetic comparison gap in **`docs/roadmap.md`**
(Next-patch item `non-hl-loaders-dont-collapse-tab-whitespace`, P2) and cross-referenced
it from **`docs/comparison-engine.md`**:

- `compare_core._xl_trim` collapses **spaces but not tabs**. Highway Log already works
  around this in its loader (`_hl_normalize` collapses `[\t\n\r\f\v]`→space at load
  time); other comparisons don't.
- Confirmed: the TSMIS **Excel** export pads some Intersection Detail Descriptions with
  trailing tabs — the only 8 cells where its PDF and Excel sides disagree statewide
  (routes 025/033/111×4/299×2). Harmless (identical road names), but inflates the
  PDF-vs-TSN count by 8.
- **Preferred fix is loader-level** (mirror `_hl_normalize`), NOT a change to the
  regression-locked `_xl_trim`/`normalize_value`. Re-bless only the touched report's canary.

---

## 6. Documentation updated (the merge must carry these too)

| Doc | Change |
|---|---|
| `CLAUDE.md` | Supported-reports table gained row **6b** (Intersection Detail (PDF)); the prose note updated from "export-only" → full consolidate/compare treatment. |
| `README.md` | Reports table gained both PDF variants + a note that they're export-only renderings. |
| `docs/reports.md` | Catalog row 6b; a "Report 6b" spec entry + a "Report 6b — consolidation" subsection (the two-row/zebra-shaded parser); the consolidator list + COMPARE_REPORTS table rows. |
| `docs/roadmap.md` | The deferred `non-hl-loaders-dont-collapse-tab-whitespace` item (§5). |
| `docs/comparison-engine.md` | The "Tab fix (HL loader only)" note upgraded from theoretical → confirmed, cross-referencing the roadmap item. |
| `CHANGELOG.md` | v0.17.2, v0.17.3, v0.17.4 sections (source of the GitHub release bodies). |
| `version.py` | `0.17.1` → `0.17.4`. **Merge note:** v0.18.0 is the refactor's own version; this only matters if the refactor rebases onto these patches rather than superseding them. |

---

## 7. Verification state

- **All `checks.yml` golden checks pass** on `main` (CI green); the full suite was also
  run locally CI-style before each release.
- **Parser correctness:** 218/218 routes reconciled, 0 content diffs (local).
- **End-to-end:** consolidate→compare ran clean on the real data (PDF-vs-TSN 16,211
  matched, etc.).
- **Still owed (work-PC only — the dev PC can't reach TSMIS):** a live export of the
  PDF report against the site, and the live matrix consolidate/compare for the new row.
  Same standing caveat as every other report's live verification.
