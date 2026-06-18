# Highway Log PDF & TSN Parsing

How the two Highway Log **PDF sources** are parsed into the canonical 31-column
TSMIS Highway Log format. There are **two distinct parsers** with two distinct
parsing strategies; this doc covers both and the validation that proved each
flawless.

The corrected 31-column header itself is owned by [columns.md](./columns.md)
(`highway_log_columns.py` — `HEADER`, `VENDOR_HEADER`, `recognize()`, tooltips,
Legend sheet). The vendor Excel bug these parsers exist to expose, and the
comparisons that consume their output, are covered in
[comparison-study.md](./comparison-study.md) and
[../comparison-engine.md](../comparison-engine.md).

---

## The two parsers at a glance

| | **TSN Highway Log** | **TSMIS Highway Log (PDF)** |
|---|---|---|
| Module | `scripts/consolidate_tsn_highway_log.py` | `scripts/consolidate_tsmis_highway_log_pdf.py` |
| Source | TSN district PDFs, report **OTM52010** ("California State Highway Log") | This app's OWN export — report **4b** "Highway Log (PDF)", `highway_log_route_<ROUTE>.pdf` |
| Where inputs come from | Vendor snapshots the user **drops** into `input/tsn_highway_log/` | The exporter produces them into `output/<run>/highway_log_pdf/` |
| Input format | One PDF per **district** (12 districts D01–D12) | One PDF per **route** (252 production routes) |
| Day-awareness | `day` **ignored** (snapshots aren't dated exports) | **day-aware** — reads the export folder like the Excel consolidator; "Export day" picker applies |
| Parsing strategy | **x-position CHARACTER-WINDOW** (fixed layout, proportional Helvetica) | **CELL-RECT** (bordered HTML table; per-page column windows from cell rects) |
| Value normalization | yes (`_normalize_row`: MI zero-pad, width zero-strip) | **none** (PDF already native TSMIS format) |
| Verified flawless over | 60,083 rows / 12 districts | 252 route PDFs / 55,768 matched rows vs Excel |
| Golden guard | `build/check_tsn_description_leak.py` | `build/check_tsmis_pdf_parse.py` |

Both write **per-route** workbooks (same `SHEET_NAME = "Highway Log"`, same
`hlc.HEADER` 31 columns, Legend sheet + header tooltips via
`highway_log_columns`) and then call `consolidate_xlsx_base.consolidate_xlsx`
(with `header_override=hlc.HEADER`, `header_comment=hlc.comment_for`,
`decorate_workbook=hlc.write_legend_sheet`) to combine into one workbook with a
`Route` column prepended. Both neutralize formula-injection text
(`compare_core.is_formula_injection`) before save. Both drop straight into the
Highway Log comparisons.

---

## TSN Highway Log parser — character-window parsing

`scripts/consolidate_tsn_highway_log.py`. **Verbatim-ported** from the
`TSMIS-Report-Consolidator` sibling project; the PDF-parsing core is calibrated
against real district PDFs. **Do not re-derive the column windows** — the audit
proved them correct.

### Inputs & folders
- `INPUT_DIR = INPUT_ROOT / "tsn_highway_log"` — fixed drop folder (created on
  first use). `INPUT_GLOB = "*.pdf"`, `INPUT_FMT = "PDF"`.
- `CONVERTED_DIR = OUTPUT_ROOT / "tsn_highway_log"` — per-route scratch
  workbooks `tsn_highway_log_d<NN>_route_<ROUTE>.xlsx`.
- `OUT_PATH = OUTPUT_ROOT / "tsn_highway_log_consolidated.xlsx"` — combined.
- `input_dir_for(day)` / `out_path_for(day)` both **ignore `day`** (interface
  compatibility only); `INPUT_NOTE` = "Drop the TSN district Highway Log PDFs
  into the input folder first." — the GUI shows this and (since v0.14.2) hides
  the Export-day picker because `input_note` is set. **This is now the ONLY
  report keeping a dropped input folder** (district PDFs are external to the
  app).

### Why character windows (not word extraction)
The PDF is proportional Helvetica, **not** monospaced. Adjacent columns can
print closer together than any word-segmentation tolerance — the county
odometer ends ~2pt before the city code begins, so pdfplumber's word extraction
**fuses** them into one token like `042.010LKPT`. So every data **character** is
assigned to a column by the horizontal window its **center** falls in
(`_parse_data_line`). Within a column, abutting chars (~0pt apart) join; a gap
≥ `WORD_GAP` (1.5pt) inserts a space.

### Layout constants
- `Y_TOLERANCE = 3` — chars within this y-distance form one logical line
  (tolerating ~1pt baseline jitter of wrapped data rows). `_lines()` clusters by
  `top`, then x-sorts.
- `HEADER_BAND = 56` — everything above this y on a page is page furniture
  (the 3-line column-header band).
- `WORD_GAP = 1.5` — x-gap that starts a new token; intra-value gaps are ~0pt.
- `COLUMN_WINDOWS` — a list of `(column_key, x_min, x_max)` in TSMIS column
  order, e.g. `("location", 0, 50)`, `("mi", 50, 73)`, `("na", 73, 82)`,
  `("cnty_odom", 82, 112)`, `("city", 112, 132)` … `("sig", 519, 612)`. The
  **three ADT columns** (`adt_back` 424–448, `adt_pp` 448–459, `adt_ahead`
  459–486) exist in the TSN layout but have **no TSMIS counterpart and are
  dropped** when rows are written. (The TSN log has an ADT Information group —
  Look Back / P / Look Ahead — that the 31-column TSMIS format does not carry.)
  `Description` has no window — TSN prints descriptions on separate lines below
  the data row.
- `ROW_KEYS` — output order, 31 keys, with `description` slotted between
  `rb_sh2` and `rec`.

### Line classification (`parse_pdf`)
Per page, below `HEADER_BAND`:
- `*`-prefixed line → "Volume Location Totals" summary → **closes the open row**
  (`last_row = None`) and `continue`.
- `District 01` (`DISTRICT_LINE_RE`) → pins district when unset.
- Centered `<district> <county> <route>` group header (`GROUP_RE` three-token,
  `first["x0"]` in 250–305) → sets `route = _norm_route(texts[2])`, resets
  `last_row = None` (don't attach descriptions across groups).
- Data line: `LOCATION_RE` (`^[A-Z]?\d{3}\.\d{3}[A-Z]?$`) matches `texts[0]`
  AND `first["x0"] < 50` → `_parse_data_line` + `_normalize_row`, appended.
- Anything else below the band → a **Description** candidate for `last_row`,
  subject to the three guards below.

### Value normalization (`_normalize_row`)
Matches TSMIS number formats where TSN prints the same value differently:
- **MI** zero-padded to 3 integer digits (TSMIS `000.075`, TSN `0.075`).
- **Traveled-way widths** (`lb_tw`, `rb_tw`) strip leading zeros (TSMIS `36`,
  TSN `036`) — `v.lstrip("0").rjust(2, "0")`.

`_norm_route`: `'1' -> '001'`; suffixed routes (`101U`) kept upper-cased.

### The three Description guards (description-fidelity fixes, v0.11.0 + v0.11.1)
Description capture carries **three structural guards** so totals-footer / page
furniture can never corrupt a segment's Description. Background: the
TSMIS-vs-TSN comparison was producing **false-positive Description diffs**
because the converter leaked totals-block footer text and page furniture into
descriptions. The v0.11.0 fix `082b6bf` caught `(DVMS)/CUMULATIVE`; the deeper
audit (D04–D12 PDFs from `Res of hwy logs.zip`) found more leak classes + one
over-strip regression.

1. **x0-gate (the robust, position-based fix).** A real feature description
   prints LEFT-ALIGNED in the feature-name column at **x0 ≈ 73.4**. Constants
   `DESC_X0_MIN, DESC_X0_MAX = 60, 110`; a description-candidate line is ignored
   unless `first["x0"]` is in that band. This excludes — by POSITION,
   independent of any text pattern — wrapped totals fragments (`TOTAL`/`TOTAL
   CONST` at x0 ≈ 170) and page furniture that dips below the header band
   (`CALIFORNIA DEPARTMENT OF TRANSPORTATION` x0 ≈ 37, `California State Highway
   Log` x0 ≈ 201, `District NN` x0 ≈ 256). **Validated** by correctly KEEPING
   `COLORADO RIVER 58-286 /TOTAL LENGTH 837' ONE HALF IN CALIF 419'` — a real
   description containing the word TOTAL that a pure pattern filter would wrongly
   drop.

2. **`*` totals line closes the open row.** The `*`-line branch sets
   `last_row = None` before `continue`, so a footer fragment printed after a
   totals line (e.g. a wrapped `TOTAL`) can't attach to the previous segment.
   Fixed `BOSTON AVE OC 33 323 , TOTAL`.

3. **UNCONST / bridge-number pattern guard (`_is_totals_line`).** `UNCONST`
   alone is a real abbreviation (UNCONSTRUCTED) in genuine descriptions
   (`JCT UNCONST RTE 251`, `BEG ST 14 UNCONST RD N`), so it marks a totals line
   ONLY in footer context: `_TOTALS_UNCONST_RE = r"\bCONST\b.*\bUNCONST\b|\bUNCONST\s+[\d.]"`
   (paired with its CONST counterpart, or immediately followed by a mileage
   figure). The other totals patterns live in `_TOTALS_RE` (`(DVM` / `\bDVM[ST]?\b`
   / `CUMULATIVE` / `CITY|COUNTY|DISTRICT|STATE TOTALS?` / `TOTALS? (MILEAGE)`)
   and `_TOTALS_NUMERIC_RE` (a line that is ONLY digits/punctuation). A lone
   hyphenated **bridge/structure number** like `53-1075` (`_BRIDGE_NUMBER_RE =
   r"^\d{2,3}-\d{2,4}[A-Z]?$"`) is explicitly KEPT — `_is_totals_line` returns
   `False` for it first.

The x0-gate (position) and `_is_totals_line` (pattern) are **defense in depth**.

### TSN audit — flawless over 60,083 rows / 12 districts
The converter was audited against ALL 12 district PDFs (D01–D12) and made
**flawless** (2026-06-16). Verdict:
- **0 char-conservation failures** (every kept PDF char in the right column;
  the only differing char is `0` from the intentional MI zero-pad / TW
  zero-strip, 0 failures survive reversing them).
- **0 row-count mismatches** (1 PDF data row → exactly 1 Excel row).
- **0 footer/furniture description leaks**, **0 real descriptions over-stripped**.
- All 30 window edges clean at glyph-CENTER level (only sub-pt edge, x=448, is
  inside the DROPPED ADT band).
- **County Odometer verified 4 independent ways**, 0 mismatches on 60,083 rows
  (production parse; gap-cluster leading-numeric; pdfplumber `extract_words`; a
  pure structural "3rd NNN.NNN-token" oracle with no x-position). CO glyph
  centers ≤107.55, City ≥112.33 → a clean 4.78pt corridor at x=112; all 60,080
  non-empty CO are `NNN.NNN`; the 3 blanks (d01/101 rows 2&13, d04/880 row 2)
  are faithful (the PDF prints no odometer there). `+`/`++`/`+++` body markers
  and the 646 N/A-flag rows are faithful to source.

Sample impact (v11 replaced v10): Route-1 **969** diff cells (0 TSN leaks; v10
had 3); Consolidated **175,535** diff cells (down from v10's 176,550 = 1,015
false positives removed; TSN footer-leak rows 1,687 → 0). One-sided row counts
**unchanged** (5,216 TSMIS-only / 14,835 TSN-only, 45,248 both) — Descriptions
aren't row keys, so the fixes create/remove no rows.

Shipped in the **v0.11.1 hotfix** (commit `0622b80`). Re-audited 2026-06-17
("County Odometer, but check all") — still flawless, no code change.

### Decisions deliberately NOT made (TSN)
- **Med Wid `00Z` vs TSMIS `0Z`: left faithful-to-PDF.** The PDF shows `00Z`;
  the converter transcribes it verbatim. The comparison's
  `compare_core._medwid_norm` already normalizes `00Z=0Z` / `06V=6V`, so these
  are NOT false positives in the comparison (15,716 such rows, all neutralized).
  Normalizing in the converter too would duplicate that logic (DRY) and reduce
  PDF fidelity. **If you change this, you must also keep `_medwid_norm` and
  re-verify the regression-locked compare samples.**
- **Column x-windows: NOT touched** (CLAUDE.md: "don't re-derive the windows";
  audit proved them correct).
- **Med TCB** 3-char `B7Z/J7Z` vs TSMIS mixed = genuine representational/data
  difference, faithfully transcribed. Not a bug.

---

## TSMIS Highway Log (PDF) parser — cell-rect parsing

`scripts/consolidate_tsmis_highway_log_pdf.py`. The inputs ARE this app's own
export: the "Highway Log (PDF)" report (4b) saves the site's Print layout via
`page.pdf()` as a real, **BORDERED HTML table**. Built to **sidestep the buggy
vendor Excel export** by sourcing the TSMIS side from the PDF instead.

### Inputs & folders (day-aware)
- `SUBDIR = "highway_log_pdf"`. The exporter writes
  `highway_log_route_<ROUTE>.pdf` to `output/<run>/highway_log_pdf/`.
- `input_dir_for(day)` → `output_day_dir(day) / SUBDIR` (or the legacy flat
  `OUTPUT_ROOT / SUBDIR` when `day` is None); `out_path_for(day)` →
  `output_day_dir(day) / "consolidated" / stamped_consolidated_filename(...)`.
  `consolidate()` defaults `day = latest_output_day()`. This is **exactly
  parallel to the Excel Highway Log consolidator** — the "Export day" picker
  DOES apply, choosing which export run to combine.
- `CONVERTED_DIR = OUTPUT_ROOT / "tsmis_highway_log_pdf"` — per-route scratch
  `tsmis_highway_log_pdf_route_<ROUTE>.xlsx`.
- `FILENAME = "tsmis_highway_log_pdf_consolidated.xlsx"`. `INPUT_GLOB = "*.pdf"`,
  `INPUT_FMT = "PDF"`.
- **v0.14.0 modeled this wrongly** on the TSN dropped-input folder
  (`input/tsmis_highway_log_pdf/` + `INPUT_NOTE` + ignored `day`); **fixed
  v0.14.2** — that was redundant since the app produces these PDFs itself. The
  dead input folder + its `.gitkeep`/.gitignore entry were removed, `INPUT_NOTE`
  dropped (so the GUI shows the day picker). **Dev note:** to test PDF
  consolidation locally now, drop PDFs in `output/highway_log_pdf/` (legacy
  flat), NOT `input/`.

### Why cell-rect parsing (not character windows)
The print view is a genuine bordered HTML table, so **every data row's 30
columns are present in the PDF as cell RECTANGLES**. But the table is
**auto-laid-out**: column x-boundaries DIFFER from page to page, and routes
render **landscape OR portrait** (a short spur is portrait). So the windows
can't be a fixed constant like the TSN log — they are **derived per page** from
that page's cell rects.

`N_PDF_COLS = 30` data cells per row = the 31 TSMIS columns **minus
Description** (`_DESC_IDX = hlc.DESC_IDX = 28`; the PDF prints descriptions on
follow-on lines, like TSN).

`_page_column_windows(page)`:
- Collect cell rects (`3 < width < page.width-20`, `3 < height < 40`).
- Group by `round(top)` into bands; keep only bands with **exactly
  `N_PDF_COLS` (30)** cells — these are the **zebra-shaded data rows** (only
  shaded rows carry rects). Every shaded band on a page shares the table's
  column geometry, so the per-column **median** edge is exact and robust to a
  stray rect.
- Make windows **CONTIGUOUS**: each boundary is the midpoint between adjacent
  cells (first/last extend to ±infinity), so **no data character can fall
  between two cells and be silently dropped**.
- Also returns `col0_right` = column 0's true right edge, used to tell a data
  row (postmile starts inside col0) from a description (starts to the right of
  col0).
- Returns `None` on a page with no full 30-cell data band (cover / legend page);
  the previous page's `page_windows` is carried forward.

`_assign_columns(chars, windows)` — same center-in-window assignment + `WORD_GAP`
token split as the TSN parser.

### Content-based header detection (`_header_bottom`)
The column-header band is found by **CONTENT**, not a fixed y: the bottom header
row is the one whose joined text contains both `ODOM` and `CITY`
(case-insensitive). Lines at or above `hdr_bottom + HEADER_EPS` (2) are page
furniture; content is strictly below. Falls back to `HEADER_BAND = 64` only when
the header row isn't found (it returns None on cover/legend pages).

**Why content not a fixed y:** a row whose description got pushed onto a
near-empty "orphan" page shifts that page's whole layout UP — a fixed cutoff
would swallow the description. (`Y_TOLERANCE = 3`, `WORD_GAP = 1.5`,
`URL_MARK = "tsmis.dot.ca.gov"` skips the page-footer URL line.)

### Line classification (`parse_pdf`)
- `Route 006` cover line (`ROUTE_HEADER_RE`, 2-token) → pins `route` (the
  filename via `ROUTE_FROM_NAME` is primary; a mismatch logs a WARNING and uses
  the filename).
- `*`-prefixed TOTALS line → **closes the open row** (`last_row = None`).
- Centered `<district> <county> <route>` group header (`GROUP_RE`,
  `first_x0 > page.width * 0.30`; county codes may bear a period —
  `^[A-Z]{2,4}\.?$`, e.g. `07 LA. 005S`) → resets `last_row` (don't attach
  descriptions across groups). **County is a section marker only** — the
  31-column layout has no County column.
- Data row: a postmile begins inside the Location column (`LOCATION_RE` AND
  `first_x0 < col0_right`). Accepts either a bare postmile OR a lone
  single-letter left-margin marker followed by the postmile — the code accepts
  **any** single alphabetic char (`texts[0].isalpha()`), not a fixed set; in
  practice it is `C`/`R`/`L`.
- Else, starting to the RIGHT of col0 → a Description for `last_row`. A long
  description WRAPS across baselines; wrapped lines rejoin with a **space** (not
  a comma) to match the report's own wrap (`"… END R" + "REALIGNMENT"` →
  `"… END R REALIGNMENT"`).

### 30 cells → 31 columns (`_make_row`)
PDF cells map **1:1, in document order** to the 31-column layout minus
Description: cells `0..27` → Location..RB SH (header positions 0–27), then the
accumulated **Description** at index `_DESC_IDX` (28), then cells `28..29` →
Date of Rec / Sig Chg. Date (positions 29, 30).

### NO value normalization
Unlike the TSN converter, **no normalization** — the PDF already carries native
TSMIS number formats (MI `000.045`, widths `12`), so values are written through
verbatim. A left-margin section marker (`C`/`R`/`L`) stays in the Location cell;
`_normalize_location` collapses the small inserted gap (`C 043.925E`) so the key
matches the single-token TSN/Excel form (`C043.925E`). The comparison engine
applies the Med Wid zero-pad rule at compare time.

### TSMIS PDF audit — flawless over 252 routes
**Char-conservation clean across ALL 252 route PDFs** (0 loss / 0 unclassified
lines; per-route rows == the PDF's data-row count). Route-for-route against the
official TSMIS Excel export of the same route: **55,768 matched rows across 252
routes**, with EVERY residual difference traced to an **Excel-export quirk and
NONE to the parser**. A 12-agent PDF-vs-Excel workflow flagged only routes
**041** and **046** as possible parser bugs — both confirmed to be the Excel's
**dropped rows** (the dropped rows are present and complete in the PDF).
Adversarial Phase-4 audit (2026-06-18): PDF-vs-Excel 8/8 raw-source spot-checks
matched both sides → **0 diffs trace to a PDF parser error**. Locked by
`build/check_tsmis_pdf_parse.py`.

This is what the parser exposes about the vendor Excel: it **drops rows and
whole roadbed-column blocks** (route 041 missing 72 rows + ~4,500 blanked
geometry cells; route 046 drops rows in dense postmile bands, cascading the MI
distance-to-next), **expands `+`/`++` ditto markers** into values, **pads
Descriptions with trailing tabs**, and **mis-attributes/shifts descriptions** to
adjacent rows. See [comparison-study.md](./comparison-study.md) for the full
ditto convention and the quantified Excel-bug breakdown, and
[../comparison-engine.md](../comparison-engine.md) for the comparison families
that consume this output.

---

## TWO TSMIS PDF formats (portrait vs landscape) — layout robustness

Found mid-audit (2026-06-17): the TSMIS "Highway Log (PDF)" PDFs come in two
formats, and the parser handles both because its windows are derived per page
(cell rects + content-based `ODOM…CITY` header):

| Format | Pages | Routes | Origin |
|---|---|---|---|
| **Manual export** ("…you used these routes for 1-5") | PORTRAIT 612×792 | 001–005S | the user's hand-exports |
| **Production** ("Formatted as the exporter gets them") | LANDSCAPE 792×612 | 252 | what the exporter produces |

- Routes **002 / 005 / 005S are BYTE-IDENTICAL** across the two formats →
  **proves the parser is layout-agnostic** (per-page column windows from shaded
  rects + content-based header).
- Routes **001 / 003 / 004 are DIFFERENT DATA SNAPSHOTS**, NOT a parser bug
  (manual 003 = 323 rows vs auto 228; only-in-manual postmiles `000.497` /
  `000.586` / `004.100` are literally in the manual PDF, absent from auto, and
  vice-versa). Both editions say "2026"; the `Length(MI)` diffs are downstream
  of the differing postmile sets ("distance to next"). Cause of the 1/3/4
  snapshot drift unknown (different pull time or version setting).
- **Always build samples/validation from the PRODUCTION landscape format.** The
  earliest sample workbooks used the MANUAL 1-5 and were contaminated by the
  snapshot drift; rebuild with auto 1-5S before final conclusions.

---

## Shared consolidation core

Both parsers feed `consolidate_xlsx_base.consolidate_xlsx`. It locks the header
from the first file, prepends the `Route` column (from the per-route filename's
end-anchored route token), and **streams** the write (openpyxl write-only mode).
The Highway Log path passes the opt-in `header_override` / `header_comment` /
`decorate_workbook` arguments so the corrected labels + tooltips + Legend sheet
apply; Ramp Detail / Highway Sequence pass none and stay byte-identical. See
[columns.md](./columns.md) for the header decoration and
[../reports.md](../reports.md) / [../comparison-engine.md](../comparison-engine.md)
for the consolidator contract.

---

## Cross-references
- Corrected 31-column labels, tooltips, Legend, `recognize()` → [columns.md](./columns.md)
- The `+`/`++` ditto convention, the vendor Excel bug breakdown, roadbed key → [comparison-study.md](./comparison-study.md)
- Comparison families that consume these workbooks (TSMIS-vs-TSN, TSMIS(PDF)-vs-TSN, TSMIS(PDF)-vs-Excel) → [../comparison-engine.md](../comparison-engine.md)
- The "Highway Log (PDF)" export (report 4b) that produces the TSMIS PDFs → [../reports.md](../reports.md)
- Golden checks + verification loops → [../verification-and-testing.md](../verification-and-testing.md)
- Field-failure narratives (e.g. stale-Excel-inflated comparison) → [../lessons.md](../lessons.md)
