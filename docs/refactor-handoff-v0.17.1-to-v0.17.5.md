# Forward-port handoff — what `main` gained after v0.17.1

**Read this before merging `refactor/v0.18.0-structural-overhaul` back into `main`.**

The refactor branched from **v0.17.1**. While it was in flight, `main` shipped seven
patch releases (**v0.17.2 → v0.17.8**) plus follow-up commits. This document is the
complete record of that divergence so the merge can forward-port / reconcile every
change — including the docs.

- **Commit range:** `v0.17.1..main`.
- **The substance:** the **Intersection Detail (PDF)** feature (v0.17.2–v0.17.4, §1–§7); the
  **v0.17.5 control-type crosswalk** (§8); then a run of **localized Intersection-Detail vs-TSN
  comparison** changes (v0.17.6–v0.17.8, §9) — compare-everything, the summary signal fold, the
  stale-library fix, the added + **position-aligned** date columns, numeric-padding normalization,
  and the new **"Report View"** replica sheet. Everything in §8–§9 touches ONE module
  (`compare_intersection_detail_tsn`; the summary fold in §9b also touches `summary_layout`) and
  forward-ports independently of the §3 matrix/registry plumbing.
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
| **v0.17.5** | **control-type crosswalk** | Intersection Detail vs-TSN: fold TSN signal sub-types J–P + TSMIS `S` into one "Signalized" category → diffs 5,632→3,019 (see §8). Localized to `compare_intersection_detail_tsn`. |

(The later patches **v0.17.6 → v0.17.8** are localized Intersection-Detail vs-TSN comparison
changes — documented in **§9b–§9e**, not as PDF-feature rows above.)

All releases were built + published by `release.yml` (frozen self-test gates passed);
`checks.yml` is green on `main`.

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
| `docs/roadmap.md` | The deferred `non-hl-loaders-dont-collapse-tab-whitespace` item (§5); the Intersection Detail backlog entry's canary updated for the v0.17.5 crosswalk. |
| `docs/comparison-engine.md` | "Tab fix (HL loader only)" note → confirmed; the Intersection Detail TSN reconciliation list + canary updated for the v0.17.5 crosswalk. |
| `docs/tsn-parsers.md` | Intersection Detail — TSN: the control-type "no crosswalk" note → the J–P→Signalized crosswalk + the new counts (v0.17.5). |
| `CHANGELOG.md` | v0.17.2, v0.17.3, v0.17.4, v0.17.5 sections (source of the GitHub release bodies). |
| `version.py` | `0.17.1` → `0.17.5`. **Merge note:** v0.18.0 is the refactor's own version; this only matters if the refactor rebases onto these patches rather than superseding them. |

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

---

## 8. v0.17.5 — control-type crosswalk (separate from the PDF feature)

A small, **localized** change to ONE module — does not touch the matrix/registry
plumbing of §3, so it forward-ports independently.

- **What:** in `scripts/compare_intersection_detail_tsn.py`, the TSN→TSNR control-type
  crosswalk from the reference "TSNR - Intersection Control and Geometry Type": TSN
  records signalized intersections under the legacy signal sub-types **J/K/L/M/N/P**,
  which TSMIS collapses into one category (stored `S`). A new `_norm_control_type`
  folds both sides' signalized codes (`{J,K,L,M,N,P,S}`) into the readable label
  **`Signalized`**, applied to the `Control Type` field in `_project`. Geometry
  (INT Type) needs no crosswalk — both systems share F/M/S/T/Y/Z/R.
- **Transparency (the user's requirement):** the merge shows on the page — wherever the
  crosswalk applied, the `Control Type` cell reads `Signalized` (a category word, vs
  the raw letter codes), and the Notes sheet documents the mapping. (An earlier attempt
  added a "Ctrl Type (raw)" context column, but compare_core coalesces context fields to
  one side, so it couldn't show both raw codes — reverted in favor of the label.)
- **Impact:** Excel-vs-TSN diffs **5,632 → 3,019** (Control Type 2,614 → 1); same for
  PDF-vs-TSN (5,640 → 3,027). This module is **reused by `compare_intersection_detail_pdf`**
  (PDF-vs-TSN side) and both matrices, so the crosswalk applies everywhere automatically.
- **Files:** `scripts/compare_intersection_detail_tsn.py` (the normalizer + Notes),
  `build/check_compare_intersection_detail_tsn.py` (the golden check now asserts S/P→
  Signalized matches, a non-signalized A/B still flags, and the crosswalked cell is not
  counted), plus the doc updates in §6.
- **Merge note:** the golden canary INTENTIONALLY changed (count dropped). If the refactor
  restructured `compare_intersection_detail_tsn`, re-apply `_norm_control_type` to the
  `Control Type` projection and keep the Notes wording. compare_core itself is untouched
  (regression lock intact). **NOTE:** the 5,632→3,019 figures here are the *mainline-only*
  counts under the pre-2026-06-24 context behavior; §9 (compare-everything) supersedes them.

## 9. Post-v0.17.5 — COMPARE-EVERYTHING policy for Intersection Detail (2026-06-24)

Another **localized** change to the same one module (`compare_intersection_detail_tsn`),
born from an adversarial audit of the vs-TSN comparisons. Independent of §3 plumbing.

- **What:** `CONTEXT_FIELDS = ()` — nothing is suppressed. Every field present in both
  systems is compared and counted (a mechanical diff). Previously PR + Date of Record +
  the 5 cross-street (CS*) attrs were `context_fields` (shown, coalesced to one side,
  never counted); now they all count.
- **Why (user):** "compare anything present on both reports, even if it leads to an entire
  column of mismatches — note it down; the comparison is a mechanical look and comments are
  made based on it." And: "make all normalization clear within the excel files even though
  it may lead to a match."
- **Normalization stays + is documented:** the crosswalk (§8), the Y≡1/N≡0 booleans, PM
  and date normalization, and roadbed keying all REMAIN (they legitimately produce matches).
  `_write_notes_sheet` was rewritten to enumerate every normalization (and how to recognize
  it in a cell — e.g. the word "Signalized", a TSMIS "Y" that was "1") and to *comment* on
  the columns that differ wholesale instead of hiding them.
- **Impact (statewide canary):** Excel-vs-TSN diffs **3,019 → 49,397** = Date of Record
  16,211 (whole column — refresh-vs-record date, structural) + cross-street 30,167 (mostly
  TSMIS completeness gaps; 276 genuine value conflicts) + mainline/identity 3,019. Every
  matched row now differs (Date of Record). PDF-vs-TSN **49,405** (+8 Description tab cells).
- **Files:** `scripts/compare_intersection_detail_tsn.py` (`CONTEXT_FIELDS=()`, docstring,
  Notes sheet rewrite), `build/check_compare_intersection_detail_tsn.py` (golden check now
  asserts the previously-context columns ARE counted while normalizations still match), plus
  doc updates (`comparison-engine.md`, `tsn-parsers.md`, `roadmap.md`).
- **Merge note:** if the refactor restructured this module, keep `context_fields=()` and the
  Notes-sheet normalization documentation. Other vs-TSN comparators (Ramp Detail, Highway
  Sequence) KEEP their context fields — this policy is Intersection-Detail-specific.

### 9b. Same date — Intersection SUMMARY signal fold (consistency with the Detail)

To match the Detail and the user's "compare what's present on both", the Summary now folds
the TSN signal sub-types **J–P → the shared `S - SIGNALIZED` category** so Signalized compares
directly (TSMIS 2,713 vs TSN 2,648) instead of splitting one-sided, and the `+ no data` buckets
the TSN PDF reports as 0 are now compared.

- **Files:** `scripts/summary_layout.py` (`_CONTROL_SIGNAL_FOLD` + the fold in
  `counts_from_rows`; removed J–P category rows; `S` relabeled "SIGNALIZED (incl. TSN J-P)" and
  marked `both`; `num-of-lanes +` flipped to `both`; new `SummarySpec.notes` rendered on the
  familiar sheet), `scripts/compare_intersection_summary_tsn.py` (docstring),
  `build/check_compare_intersection_summary_tsn.py` (golden check: 66 categories, fold asserted,
  58/8/0 split).
- **Canary:** 66 categories — **58 both / 8 only-TSMIS / 0 only-TSN; 54 diff cells**; 16473 vs 16626.
- **Merge note:** the fold is gated to the `CONTROL TYPES` block, so Ramp Summary (which has no
  such block, and a default-empty `notes`) is byte-identical. Roundabout `R` stays one-sided —
  the TSN statewide summary PDF has no roundabout row.

### 9c. Same date — re-normalize the TSN library on READ (the "Signalized ≠ P" fix)

**The bug:** the matrices compare against the cached TSN *library* workbook
(`*_normalized.xlsx`), which `tsn_library.build_consolidated` **reuses, not rebuilds**, after a
code change (it checks current-vs-RAW, not current-vs-code). A library built before the crosswalk
kept raw codes, and the normalized read paths applied NO normalization → "Signalized ≠ P".

**The fix — re-apply normalization at COMPARE time on the normalized-library read path** (so a
normalization change takes effect immediately, no rebuild):
- `compare_intersection_detail_tsn._load_tsn`: new `_normalized_row` re-projects each library row
  through `_project` (idempotent for a fresh library; repairs a stale one).
- `compare_intersection_summary_tsn._load_tsn`: new `_slug_for_key` folds stale `J–P` + old
  `S - SIGNALIZED` keys into the Signalized slug, and counts are **summed** (was overwrite).
- Locked by `check_compare_intersection_detail_tsn.test_normalized_path_crosswalk` and
  `check_compare_intersection_summary_tsn.test_stale_library_fold`.

**Merge note:** keep the read-time re-normalization. The general lesson (a cached normalized
library is not rebuilt on code change) applies to Ramp Detail / Highway Sequence too — if any of
their normalizations ever change, re-apply on read the same way (they have no such change today).

### 9d. v0.17.7 — the omitted columns added + 2 greyed context columns

**What changed (Intersection Detail vs TSN only):** the comparison previously dropped 15 of the 36
columns. After vetting each mapping against real rows with the user, the FINAL set:
- **Added (compared):** the 5 effective dates — INT/Control/Lighting → `EFF_DATE_INT`/`_CT`/`_LT`;
  **Mainline → `MAIN_EFF_DATE`, Cross-street → `EFF_DATE`** (the RECENT TSN dates; the historical
  `EFF_DATE_ML`/`CROSS_BEGIN_DATE` are a 59-year mismatch — do NOT pair the eff-dates to them). All
  five are a **systematic 1-day offset** (TSMIS Dec 31 ↔ TSN Jan 1) → flag raw on that offset (user:
  "compare raw, flag the offset"). Plus **Main Line Length** (`MAIN_OVERRIDE`) and the
  **intersecting-route block** (`CROSS_ROUTE_NAME`/`_PM_PREFIX`/`_POSTMILE`/`_PM_SUFFIX`). ⚠ the
  route **PM suffix is at consolidated pos 35** (the `Xing Rte` value), NOT pos 31 (always blank).
- **Greyed `context_fields` (shown, not counted):** `ML 2nd Eff-Date` (pos 21) + `Int St Eff-Date`
  (pos 30) — a uniform `2024` bulk stamp with no TSN counterpart. New opt-in `CompareSchema.context_fill`
  (`"D9D9D9"`) greys them via conditional formatting on matched rows — default `None` keeps every other
  comparison byte-identical (Route-1=969 HL canary unchanged; verified by `check_compare_audit`).
- **`SHARED_HEADER` reordered to mirror the printed report** (each eff-date next to its type). Name-based
  access throughout, so the canary diff *counts* are order-independent.
- **Canary:** **131,948** counted diffs (Excel) / **131,956** (PDF, +8 Description tabs). Locked by
  `check_compare_intersection_detail_tsn` (`test_added_columns` asserts the eff-date flags + Main Line
  Length/route match; `test_schema` asserts the 2 context fields + suffix pos 35).

**Merge note:** the `context_fill` field is a clean opt-in on `compare_core` — preserve it; it only
fires when a schema sets it. The eff-date↔recent-TSN-column pairing is the non-obvious part: don't
"correct" it back to the historical columns.

> **⚠ SUPERSEDED by §9e (v0.17.8):** the user re-aligned the date columns **by report position** — so
> ML/CS *first* eff-dates now DO map to the geometry `EFF_DATE_ML`/`CROSS_BEGIN_DATE` (the opposite of
> the note just above), the two greyed context columns are now compared (`context_fill` dropped from the
> Detail schema), and the control label is now `S`, not `Signalized`. The v0.17.8 canary (163,353)
> supersedes the 131,948 here. **Read §9e for the current state of this module.**

### 9e. v0.17.8 — position-aligned dates, numeric-padding norm, "S" label + the Report View

The final pre-refactor state of `compare_intersection_detail_tsn`. Still **one module** (+ its golden
check + docs); independent of §3 plumbing. **This subsection is the current source of truth for the
module — it supersedes the eff-date alignment, the greyed columns, and the "Signalized" label of §8/§9d.**

- **Date columns compared BY REPORT POSITION (supersedes §9d value-alignment).** Each report column is
  matched to the SAME column in the other report (user: "just have everything where it is in the pdfs
  and compare with what is in the other pdf"). `_TSN_COL` now maps: INT/Control/Lighting →
  `EFF_DATE_INT`/`_CT`/`_LT` (geometry, the ~1-day offset); **Mainline 1st → `EFF_DATE_ML`,
  Cross-street 1st → `CROSS_BEGIN_DATE`** (the geometry/original dates — TSMIS shows its refresh date
  here, so a structural refresh-vs-original diff like Date of Record); **Mainline 2nd → `MAIN_EFF_DATE`,
  Int St → `EFF_DATE`** (the recent dates). ⚠ This is the REVERSE of §9d — do NOT "fix" ML/CS 1st back
  to the recent dates.
- **Nothing greyed — `context_fill` dropped from `_SCHEMA`** (`context_fields` stays `()`). The two
  former `2024` context columns (ML 2nd / Int St Eff-Date) are now compared. The `context_fill` opt-in
  REMAINS in `compare_core` (retained, now with no live user — keep it; clean default-`None` no-op).
- **Numeric-padding normalization.** New `_norm_num` + `NUMERIC_FIELDS = ("Main Line Length",
  "Intrte Route", "Intrte Postmile")`, applied in `_project`: strips leading AND trailing zeros
  (`058`→`58`, `9.560`→`9.56`) so padding doesn't flag. Dropped Main Line Length 1,398→436, Intrte
  Postmile 98→43.
- **Control-type label `Signalized` → `S`** (`_SIGNALIZED_LABEL = "S"`, the code TSMIS stores) —
  supersedes §8. **NOTE:** the Summary (§9b) keeps its `S - SIGNALIZED` *category* label; only the
  Detail's per-cell control value changed.
- **NEW second sheet — "Report View"**, a faithful two-line replica of the printed Intersection Detail
  record, for visual inspection against the PDF. Appended via the EXISTING `extra_sheet_writer` opt-in
  (the same one the Summary uses): the base `_SCHEMA` leaves it `None`; `compare()` builds a per-call
  schema with `dataclasses.replace(_SCHEMA, extra_sheet_writer=lambda wb, ctx: _write_report_view(...))`.
  Config lives in module constants `_RV_GRID` (the 23-column 2-line grid), `_RV_AUX` (Major/Diffs/Route),
  `_RV_FILLS`/`_RV_FONTCOL` (palettes), `_RV_COMMENTS` (header hover-notes). Behavior: every diff renders
  **red** (`_rv_classify`: date diffs → `soft` = red but EXCLUDED from the per-record **Major** count;
  non-date → `hard` = counted as Major; both count toward **Diffs**); records alternate **white ↔ grey**
  (`_RV_FILLS["eq"][0]="FFFFFF"`); TSN-only columns (X-Ovr/ADT, from `_tsn_onesided`) in blue; locations
  from `_tsmis_locations`.
- **⚠ Write-only-mode techniques the merge MUST preserve** (the comparison workbook is streamed): the
  4-row merged header uses `ws.merged_cells.ranges.add(CellRange(min_col=, min_row=, max_col=, max_row=))`
  (NOT `ws.merge_cells`, which is unavailable in write_only); header hover-comments use
  `WriteOnlyCell.comment = Comment(...)`; **`freeze_panes` is set BEFORE the rows stream** (setting it
  after the appends silently drops it). All cells are appended in order (4 header rows, then 2 data
  rows/record).
- **Notes sheet** reconciled to the position-alignment story (no "greyed/shown-but-not-counted" section;
  the eff-date split documented; a Report-View section added).
- **Canary (supersedes §9d):** Excel-vs-TSN **163,353** counted diffs (eight date columns × 16,211 =
  129,688 + cross-street 30,167 + mainline/identity 3,019 + Main Line Length 436 + Intrte Postmile 43);
  both 16,211 / only-TSMIS 262 / only-TSN 415; identical 0. PDF-vs-TSN **163,361** (+8 Description tabs).
- **Files:** `scripts/compare_intersection_detail_tsn.py` (position-aligned `_TSN_COL`/`_TSMIS_POS`,
  `_norm_num`+`NUMERIC_FIELDS`, `_SIGNALIZED_LABEL="S"`, the `_RV_*` config + `_write_report_view` +
  `_rv_classify`/`_tsn_onesided`/`_tsmis_locations`, Notes + docstring, `context_fill` removed),
  `build/check_compare_intersection_detail_tsn.py` (golden check: `context_fields==()`, position-aligned
  mappings, `S` crosswalk, + Report-View locks — `soft` shares the hard RED palette, the normal band is
  white, a date diff classifies `soft`, a non-date `hard`, and the sheet is appended), doc updates
  (`tsn-parsers.md`, `comparison-engine.md`, `roadmap.md`), `CHANGELOG.md` (v0.17.8), `version.py`
  `0.17.7`→`0.17.8`.
- **Merge note:** if the refactor restructured this module or the comparison-workbook writing,
  (1) keep the position-aligned `_TSN_COL` mapping (don't revert to recent-date pairing);
  (2) keep `_SIGNALIZED_LABEL="S"`; (3) carry the Report View — it relies on the `extra_sheet_writer`
  opt-in and the write-only techniques above (if the refactor stopped writing the comparison workbook in
  write_only mode, the merges/comments/freeze can use the normal-mode APIs instead). The Report View is
  Intersection-Detail-specific (no other report has one). compare_core is untouched (regression lock
  intact — the Route-1=969 HL canary and all compare_core checks stay green).
