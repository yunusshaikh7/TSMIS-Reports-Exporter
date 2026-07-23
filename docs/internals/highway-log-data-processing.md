# Highway Log data-processing internals

Code-level walkthrough of the PDF/Excel parsers, the shared streaming consolidator, and the column/ditto/roadbed algorithms that feed the Highway Log workflows. Deepens [../highway_log/pdf-and-tsn-parsing.md](../highway_log/pdf-and-tsn-parsing.md) (the scannable "what/why"); for the corrected labels see [../highway_log/columns.md](../highway_log/columns.md); for the comparisons that consume this output see [../comparison-engine.md](../comparison-engine.md).

Files dissected here:
- `scripts/highway_log_columns.py` — the single source of truth for the 31-column layout + the ditto/roadbed algorithms.
- `scripts/consolidate_xlsx_base.py` — the streaming XLSX consolidator core (used by Ramp Detail, Highway Sequence, Excel Highway Log, and as the final combine step of both PDF parsers).
- `scripts/consolidate_tsn_highway_log.py` — TSN district PDFs → 31-column workbooks (FIXED character windows).
- `scripts/consolidate_tsmis_highway_log_pdf.py` — this app's "Highway Log (PDF)" exports → 31-column workbooks (PER-PAGE cell-rect windows).
- `scripts/consolidate_ramp_summary.py` — the unrelated PDF consolidator (word-position extraction + audit reconciliation), included because it shares the pdfplumber idioms.

---

## 1. The shared pdfplumber pipeline: chars → lines → column assignment

Three of these modules parse PDFs and all three share the same skeleton, but they diverge at the **column-assignment geometry**. Understand the skeleton once, then the two Highway Log strategies, then Ramp Summary's separate approach.

### 1.1 Char clustering → logical lines (TSN `_lines`, TSMIS `_cluster_lines`)

`consolidate_tsn_highway_log._lines` (`scripts/consolidate_tsn_highway_log.py:221`) and `consolidate_tsmis_highway_log_pdf._cluster_lines` (`scripts/consolidate_tsmis_highway_log_pdf.py:159`) are **byte-for-byte identical in algorithm**:

1. Sort all `page.chars` by `(top, x0)`.
2. Drop chars whose `text.strip()` is empty — literal spaces carry no data, and including them would defeat the `WORD_GAP` token-splitting later (the gap is measured between glyph bounding boxes, not from space glyphs).
3. Greedily cluster into lines: a char joins the previous cluster if `abs(c["top"] - clusters[-1][0]) <= Y_TOLERANCE` (3pt). The anchor `top` is the *first* char of the cluster, never re-averaged — this is what tolerates the ~1pt baseline jitter of a wrapped data row without letting a cluster "walk" down the page.
4. Within each line, x-sort the chars, then build **word tokens** by joining chars whose inter-glyph gap `c["x0"] - words[-1]["x1"] < WORD_GAP` (1.5pt). Tokens are `{"text", "x0", "x1"}` dicts.

Each line is returned as `(top, words, chars)`: **`words`** is used to *classify* the line (data vs group-header vs description), **`chars`** is used to *parse* a data line into columns. This split is the crux — classification needs whole tokens; column assignment needs raw glyphs (see §1.4).

> Gotcha: `Y_TOLERANCE`, `WORD_GAP` are defined separately in each module with the same values (3 and 1.5). They are *not* imported from a shared constant. A change to one does not propagate.

### 1.2 Line classification — three line kinds + furniture

Both Highway Log parsers walk lines top-to-bottom maintaining one mutable cursor, `last_row` (the most recent data row that descriptions attach to), plus `route` (TSN also tracks `district`). The classification order matters because the tests overlap; the *first* matching branch wins:

| Order | Branch | TSN (`parse_pdf`, `:309`) | TSMIS-PDF (`parse_pdf`, `:314`) |
|---|---|---|---|
| furniture | above header band | `top < HEADER_BAND` (56) `continue` | `top <= cutoff` where `cutoff = hdr_bottom + HEADER_EPS` or `HEADER_BAND` (64) |
| 1 | totals line | `texts[0].startswith("*")` → `last_row = None` | same |
| (TSN) | district pin | `DISTRICT_LINE_RE` "District 01" | — (route comes from filename/cover) |
| 2 | group header | `GROUP_RE` 3-token, `250 <= first["x0"] <= 305` | `GROUP_RE` 3-token, `first_x0 > page.width * 0.30` |
| 3 | data row | `LOCATION_RE.match(texts[0]) and first["x0"] < 50` | postmile inside col0 (`first_x0 < col0_right`), bare OR letter-prefixed |
| 4 | description | else, attach to `last_row` (guards apply) | else, `first_x0 >= col0_right`, attach to `last_row` |

`LOCATION_RE = r"^[A-Z]?\d{3}\.\d{3}[A-Z]?$"` in both (`:175` / `:139`) — optional leading realignment/section letter, the `ddd.ddd` postmile, optional trailing equation/roadbed letter.

The `*`-totals branch's `last_row = None` is **guard #2** of the TSN description guards and serves the same role in TSMIS-PDF: a totals line marks the structural end of a segment, so any stray footer fragment printed *after* it can never glue onto the prior segment's Description.

### 1.3 Group header detection — and why the x0 test differs

A centered `<district> <county> <route>` header (`01 MEN 001`) introduces each route/county section. The `GROUP_RE` tuple is three compiled regexes matched against `texts[0..2]`:

- TSN (`:177`): `(r"^\d{2}$", r"^[A-Z]{2,4}$", r"^\d{1,3}[A-Z]?$")`.
- TSMIS-PDF (`:142`): county allows a trailing period — `r"^[A-Z]{2,4}\.?$"` — because the print view emits `07 LA. 005S` / `11 SD.  905`.

The horizontal-position gate differs deliberately: TSN's layout is **fixed**, so a literal `250 <= first["x0"] <= 305` pins the centered header. The TSMIS-PDF table is **auto-laid-out and orientation-variable** (landscape 792×612 or portrait 612×792 — see [../highway_log/pdf-and-tsn-parsing.md](../highway_log/pdf-and-tsn-parsing.md)), so a literal x-band would be wrong on portrait; it uses a *relative* `first_x0 > page.width * 0.30`. Both reset `last_row = None` so descriptions never cross a group boundary.

### 1.4 The two column-assignment geometries — the central comparison

Both parsers ultimately call a "center-in-window" assigner that is **algorithmically identical** — `_parse_data_line` (TSN `:252`) and `_assign_columns` (TSMIS-PDF `:249`):

```
for each char c (x-sorted):
    center = (c.x0 + c.x1) / 2
    for each (lo, hi) window in order:
        if lo <= center < hi:
            if this column already has chars and c.x0 - last_x1[col] >= WORD_GAP:
                append a space      # two tokens inside one column
            append c.text to the column
            break
```

The difference is entirely **where the windows come from**:

#### FIXED windows (TSN)

`COLUMN_WINDOWS` (`scripts/consolidate_tsn_highway_log.py:129`) is a hard-coded list of `(key, x_min, x_max)` triples calibrated to the OTM52010 layout — `("location", 0, 50)`, `("mi", 50, 73)`, … `("sig", 519, 612)`. 33 windows total, including **three ADT columns** (`adt_back` 424–448, `adt_pp` 448–459, `adt_ahead` 459–486) that exist in TSN but have no TSMIS column. They are assigned during parsing but **dropped at write time** — `ROW_KEYS` (`:166`) lists only the 31 TSMIS keys (with `description` between `rb_sh2` and `rec`), so `_write_route_workbook` (`:400`) emits `[row.get(k) for k in ROW_KEYS]` and the ADT keys simply aren't pulled.

This works because the OTM52010 PDF is a single fixed template across all 12 districts. The audit (60,083 rows) proved the windows correct, hence the standing rule: **do not re-derive these windows** (see §8).

#### PER-PAGE windows from cell rects (TSMIS-PDF)

The "Highway Log (PDF)" export is a bordered HTML table whose column x-boundaries differ page to page and flip with orientation, so a fixed list is impossible. `_page_column_windows(page)` (`scripts/consolidate_tsmis_highway_log_pdf.py:185`) derives them:

1. **Collect candidate cell rects**: `page.rects` filtered to `3 < width < page.width - 20` and `3 < height < 40`. This keeps real table cells, excludes the full-page border and hairlines.
2. **Group into horizontal bands** by `round(r["top"])`.
3. **Keep only bands with exactly `N_PDF_COLS == 30` rects** (`data_bands`). These are the **zebra-shaded data rows** — only shaded rows carry rect fills, so a page's shaded bands collectively reveal the table's column geometry. A non-shaded row, the header, and partial bands are all excluded by the `== 30` test.
4. If no 30-cell band exists → return `None` (cover/legend page).
5. For each of the 30 columns, take the **median** `x0` and `x1` across all data bands (`median` is `sorted[len//2]`, `:206`). Median (not mean) makes the edge robust to one stray rect.
6. **Make windows CONTIGUOUS**: boundary `i` is the midpoint `(edges_hi[i-1] + edges_lo[i]) / 2`; column 0's `lo` is `-inf` and column 29's `hi` is `+inf` (`:218`). Contiguity is the safety invariant — **no char center can fall in a gap between two cells and be silently dropped**, which a literal `[x0, x1]` window list would allow.
7. Also return `col0_right = edges_hi[0]` — column 0's *true* right edge (not the contiguous boundary). This is the discriminator for data-row-vs-description: a data row's postmile starts left of `col0_right`; a description starts to its right.

`page_windows` and `col0_right` are **carried forward** across pages: if a page yields `None` (e.g. an orphan page that holds only a wrapped description), the previous page's geometry is reused (`:304`). This is why a description stranded on a near-empty page is still column-assigned correctly.

> Gotcha (per-page vs fixed): the two parsers look superficially similar but the TSMIS-PDF windows are *data-dependent*. If a route PDF ever rendered with a row whose shaded band had ≠30 rects on every page, `page_windows` would stay `None` and every data line on that page falls through the `if page_windows is None: continue` guard (`:347`) — silently skipped. The 252-route audit found this never happens, but it is the failure mode to suspect if a future route loses rows.

### 1.5 Content-based header detection (TSMIS-PDF only)

TSN uses a fixed `HEADER_BAND = 56`. TSMIS-PDF can't, because an orphan page shifts its whole layout up. `_header_bottom(lines)` (`scripts/consolidate_tsmis_highway_log_pdf.py:230`) finds the header's bottom row by **content**: the line whose uppercased joined text contains both `"ODOM"` and `"CITY"` (unique to the `LOCATION … ODOM … CITY` band). It returns the *last* such line's `top` (there can be a multi-row header), or `None` on cover/legend pages. The per-page `cutoff` is then `hdr_bottom + HEADER_EPS` (2) or the `HEADER_BAND = 64` fallback. Lines at or above `cutoff` are furniture.

The page-footer URL line (`URL_MARK = "tsmis.dot.ca.gov"`) is dropped by a separate any-token check (`:318`) before classification — it would otherwise look like content below the header.

### 1.6 30 → 31 column mapping (`_make_row`, DESC at index 28)

`highway_log_columns.DESC_IDX == 28` (asserted at `scripts/highway_log_columns.py:100`). The PDF carries 30 data cells; Description is **not** a PDF cell — TSMIS (like TSN) prints descriptions on follow-on lines. `_make_row(vals, description)` (`scripts/consolidate_tsmis_highway_log_pdf.py:275`) splices them:

```
vals[0:28]  +  [description]  +  vals[28:30]
# header positions 0..27  →   28   →   29,30 (Date of Rec, Sig Chg. Date)
```

So PDF cells 0–27 are Location..`RB OT-SH Treated`, then Description, then PDF cells 28–29 are the two date columns. `vals[0]` is `_normalize_location`'d first (collapses the `C 043.925E` → `C043.925E` gap, `:267`). Empty cells become `None` (`v.strip() or None`).

TSN reaches the same 31-wide shape differently: it builds a `dict` keyed by column name during parsing and emits `[row.get(k) for k in ROW_KEYS]`, with `"description"` already in the key list at the right slot.

### 1.7 Description accumulation + the three TSN guards

After a data row is appended and set as `last_row`, subsequent non-classified lines are its description (the report wraps long features over baselines).

**TSN** (`:362`) applies **three structural guards**, all anchored in code:

1. **x0-gate** — `if not (DESC_X0_MIN <= first["x0"] <= DESC_X0_MAX): continue` (`DESC_X0_MIN, DESC_X0_MAX = 60, 110`, `:122`). A real feature description prints left-aligned at x0 ≈ 73.4; this excludes by **position** the wrapped totals fragments (`TOTAL` at x0 ≈ 170) and page furniture that dips below the band (`CALIFORNIA DEPARTMENT…` x0 ≈ 37, `District NN` x0 ≈ 256) — independent of any text pattern. This is the robust guard.
2. **`*`-totals-close** — handled upstream in the classification loop (`:321`): the `*` branch sets `last_row = None`, so a footer fragment after a totals line has nothing to attach to.
3. **`_is_totals_line(text)` pattern family** (`:210`) — catches totals continuations that *do* land near the description band. It returns `True` if the text matches `_TOTALS_RE` (`(DVM` / `\bDVM[ST]?\b` / `CUMULATIVE` / `CITY|COUNTY|DISTRICT|STATE TOTALS?` / `TOTALS? (MILEAGE)`), `_TOTALS_UNCONST_RE` (`\bCONST\b.*\bUNCONST\b | \bUNCONST\s+[\d.]`), or `_TOTALS_NUMERIC_RE.fullmatch` (a digits/punctuation-only line). **Order-critical edge case**: `_BRIDGE_NUMBER_RE = r"^\d{2,3}-\d{2,4}[A-Z]?$"` is tested FIRST and returns `False` — a lone bridge number like `53-1075` is a legitimate one-token description and must NOT be eaten by `_TOTALS_NUMERIC_RE`. Likewise `UNCONST` alone is kept (it's a real abbreviation, UNCONSTRUCTED) unless it appears in its CONST footer pairing.

When a description survives the guards, TSN joins multiple lines with `", "` (`:368`).

**TSMIS-PDF** (`:370`) is simpler: the only structural test is `first_x0 >= col0_right` (description starts right of Location). It needs no totals-pattern list because the bordered-table layout keeps furniture out of the content band, and wrapped lines are rejoined with a **space, not a comma** (`:373`) — to match the report's own wrap (`"… END R" + "REALIGNMENT"` → `"… END R REALIGNMENT"`). This space-vs-comma difference between the two parsers is intentional and load-bearing for the PDF-vs-Excel comparison fidelity.

### 1.8 Per-route file numbers vs row normalization (TSN only)

`_normalize_row` (`scripts/consolidate_tsn_highway_log.py:270`) is the **only** value transform across both Highway Log parsers, and it exists solely so TSN's print format lines up with TSMIS's:
- **MI** zero-padded to 3 integer digits: `r"(\d+)\.(\d+)"` → `f"{int:03d}.{frac}"` (TSMIS `000.075`, TSN `0.075`).
- **Traveled-way widths** (`lb_tw`, `rb_tw`) strip leading zeros: a 3+ digit value becomes `v.lstrip("0").rjust(2, "0")` (TSMIS `36`, TSN `036`).

TSMIS-PDF does **no** normalization — its PDF already carries native TSMIS formats. The Med Wid `00Z`/`0Z` reconciliation is deliberately left to compare time (`compare_core._medwid_norm`), NOT duplicated here (DRY; see [../highway_log/pdf-and-tsn-parsing.md](../highway_log/pdf-and-tsn-parsing.md) "Decisions deliberately NOT made").

---

## 2. Ramp Summary parser (`consolidate_ramp_summary.parse_pdf`)

Standalone on purpose (`scripts/consolidate_ramp_summary.py`) — a two-column word-position layout unlike the Highway Log char-window model, producing **one row per route** (not per segment).

### 2.1 Schema as ordered (name, regex) lists

Four schemas drive parsing and are matched **in report order**: `HIGHWAY_GROUPS` (6), `ONOFF` (3), `POP_GROUPS` (5), `RAMP_TYPES` (14) (`:70`–`:105`). Each entry is `(column_name, label_match_regex)`. Note `POP_GROUPS` has **two identical** `-O OUTSIDE CITY` patterns (rural-outside, urban-outside) — disambiguated only by order and the used-index cursor (§2.3).

### 2.2 Word extraction → two columns → stitched rows

`parse_pdf` (`:281`) reads the route off **page 1** (`r"All Ramps on Route\s+(\d+\w*)"`) and the data off **page 2** (`page.extract_words()`). Per column:

1. `get_rows_for_column(words, left=True|False)` (`:115`): split by `COLUMN_SPLIT_X = 300` (`(w["x0"] < 300) == left`), cluster into rows by `Y_TOLERANCE` (3), and parse each row into `(number_or_None, label)` — the leading token is the count if it matches `r"-?[\d,]+"` with a digit (thousands separators stripped).
2. `stitch_wrapped_rows(rows)` (`:200`): the heart of the messiness. It `clean_label`s away noise tokens that pdfplumber fuses into rows (`NOISE_PATTERNS`, `:152` — section headers like `Highway Groups`, `NUMBER CODE`, totals lines), then runs a small state machine over `(open_num, open_label, pending_num)` to:
   - reattach an **orphan number** (a number on its own line) to the right label — held in `pending_num` until the next new label, or assigned to `open_num` when the label was seen first;
   - **join wrapped continuations** via `_join_continuation` (`:187`), which does *smart* joining — `'Co' + 'nnector' → 'Connector'` when both sides are lowercase (broken mid-word), else space-joined (`'Vista Point,' + 'Truck Scale'`).
   - `is_new_label` (`:174`) decides start-vs-continuation by the schema-label shapes (`^[A-Z]\s*-\s`, `^[A-Z]{2,}\s*-\s`, `^[A-Z]-[A-Z]+`, `^-[A-Z]`, or `"Others"`).

### 2.3 Schema matching with a forward cursor + used-index set

`match_schema(rows, schema, used_indices)` (`:243`) walks the schema in order, and for each entry scans `rows` **forward from `cursor`**, skipping already-used indices, for the first row whose normalized label `re.fullmatch`es the pattern. On a hit it records the number, marks the index used, and advances `cursor`. The **left column** runs three schemas sharing one `used_left` set (`:303`) — so the duplicate `-O OUTSIDE CITY` patterns resolve to distinct rows (the first match consumes index, the second match finds the next). The right column runs `RAMP_TYPES` with a fresh set.

### 2.4 `_audit_ok` reconciliation — formulas, not Python

There is **no Python-side reconciliation function** named `_audit_ok`; the audit is entirely **Excel formulas** written by `build_workbook` (`:564`). For each route row the consolidator emits four `_chk_*` SUM formulas (`:623`):
- `_chk_hwy = SUM(highway-group cells)`
- `_chk_onoff = SUM(on/off cells) + ramp_points_no_linework`
- `_chk_pop = SUM(population cells)`
- `_chk_ramp = SUM(ramp-type cells) + ramp_points_no_linework`

and `_audit_ok` (`:644`) is an `IF(AND(all four == total_ramps), "OK", "⚠ Source ≠ total: " & …)` formula naming the failing section(s). Conditional formatting (`:665`) greens `EXACT(cell,"OK")` and reds the negation. A red cell means the **source PDF's own breakdown doesn't sum to its own stated total** (a TSMIS data quirk on dense routes — confirmed by the off-repo Ramp-Summary audit) — NOT a parser error. Note the `dxf` fills use `bgColor` not `start_color` (`:668` comment) — the openpyxl CF gotcha.

`record_has_data(record)` (`:268`) is the real Python gate: a record with only a route (page-2 figures missing on a truncated PDF) returns `False` and is **skipped, not written as a blank row** — and if *every* PDF is data-less, nothing is written so a good prior workbook isn't clobbered (`:778`).

### 2.5 `build_combined_sheet` — a fixed-coordinate template

`build_combined_sheet` (`:417`) inserts a `"Combined"` sheet at index 0 whose cells are **hard-coded coordinates** (`A4:C4` section header, rows 6–11 Highway Groups, rows 15–17 On/Off, 21–25 Population, 6–19 Ramp Types on the right, totals at 28–29) with live `=SUM('TSAR Ramps Summary'!{col}3:{col}{last})` formulas linking back to the per-route sheet. `last_data_row = max(3, 2 + n_routes)` keeps the range valid at zero routes. If you add a schema row, these literal coordinates must move (§8).

---

## 3. The streaming consolidator core (`consolidate_xlsx_base.consolidate_xlsx`)

`scripts/consolidate_xlsx_base.py`. One function combines every per-route `*.xlsx` in a folder into a single workbook with a prepended `Route` column. Used directly by Ramp Detail / Highway Sequence / Excel Highway Log, and as the **final combine step** of both PDF parsers (which first write per-route `.xlsx` scratch files, then call this).

### 3.1 Control flow

`consolidate_xlsx(*, input_dir, out_path, sheet_name, report_name, title, events, confirm_overwrite, header_override, header_comment, decorate_workbook)` (`:79`):

1. **Dep + existence guards**: `_DEPS_OK` (openpyxl import), `input_dir.exists()`, `files = sorted(input_dir.glob("*.xlsx"))` non-empty — each returns a clean `ConsolidateResult(status="error", message=…)`, never raises.
2. **Confirm overwrite before reading inputs** (`:123`) — `confirm(out_path)` callback; a "no" returns `status="cancelled"` and leaves the file untouched.
3. **Lock the canonical header** (`:134`): iterate files, `_read_header` the first that yields a non-`None` row-1; record `canonical_header` + `canonical_source`. A file whose header read raises or whose sheet is missing is logged and skipped during this probe.
4. **Open a `Workbook(write_only=True)`** (`:165`) — streaming mode. This is mandatory: a consolidated comparison or a full-state Highway Log can be hundreds of thousands of rows, which in-memory openpyxl cannot save in reasonable time.
5. **Write the header row** (`:184`): `["Route"] + out_header`, each as a `WriteOnlyCell` with header styles, optional `header_comment(label)` comment attached *before append* (write-only cells must carry their comment before they're streamed).
6. **Stream data rows** (`:203`): per file, re-`_read_header` and require exact `h == canonical_header` (else skip — misaligned columns can't silently corrupt the combine); `_extract_route(p)` from the filename; then `_stream_data_rows` yields row 2+ and each is appended as `[route] + [_safe_cell(ws, v) for v in row]`.
7. **Refuse to save an empty combine** (`:240`): if `used_files == 0`, close and return `status="error"` — a header-only workbook claiming "ok" would overwrite a good prior consolidation.
8. **`decorate_workbook(wb)`** (`:251`) opt-in hook runs after rows, before save (Highway Log appends the Legend sheet here).
9. **Save** with a `PermissionError` → "probably open in Excel" message (`:258`).
10. **Incomplete banner** (`:271`): if any file was skipped/failed, `summary_lines[0]` leads with `⚠ INCOMPLETE …`. The status **stays `"ok"`** (so the GUI still offers the partial file) — there is intentionally no `"partial"` status (would need consumer support; tracked in `docs/roadmap.md`).

### 3.2 Route parse from filename

`ROUTE_FROM_NAME = re.compile(r"_route_(\w+)\.xlsx$", re.IGNORECASE)` (`:35`); `_extract_route` (`:49`) returns `m.group(1).upper()` or falls back to `path.stem`. This is **end-anchored** — which is exactly why the Export-Everything env-tagging FRONT-stamps the `<src-env>` label onto filenames (a trailing tag would break this regex). Both PDF parsers name their scratch files `…_route_<ROUTE>.xlsx` to match.

### 3.3 `header_override` / `header_comment` / `decorate_workbook` opt-ins

These three keyword args (`:81`) are how the Highway Log path injects corrected labels without disturbing Ramp Detail / Highway Sequence:

- **`header_override`** (`:177`): a label list written *instead of* the file-locked header. **Length must equal `canonical_header`** or it's ignored with a logged note — the relabel is purely positional (the data rows are untouched), so a length mismatch could silently shift columns. The Highway Log consolidators pass `hlc.HEADER`; the file's own (possibly vendor-mislabeled) header is locked for the position-match but `hlc.HEADER` is what's written.
- **`header_comment`** (`:191`): `callable(label) -> Comment | None`, attached to each header cell. Highway Log passes `hlc.comment_for`.
- **`decorate_workbook`** (`:251`): runs `hlc.write_legend_sheet`.

Ramp Detail / Highway Sequence pass none of these → byte-identical output to pre-overhaul builds. This is the DRY win called out in the module docstring: one fix benefits all three reports.

### 3.4 Formula-injection guard

`_safe_cell(ws, value)` (`:38`) forces a `WriteOnlyCell` to `data_type = "s"` when `compare_core.is_formula_injection(value)` is true — i.e. the text starts with one of `_FORMULA_LEAD = ("=", "+", "-", "@")` (`compare_core.py:711`). A parsed Description beginning `=` can't execute on open. The two PDF parsers apply the same guard at their per-route write step (`is_formula_injection` → `cell.data_type = "s"`).

### 3.5 Incompleteness contract

Skipped/failed files never silently vanish: they're listed in `summary_lines` and trigger the `⚠ INCOMPLETE` lead. The invariant a maintainer must preserve: **a combine that left anything out must announce it loudly, and a combine that produced nothing must NOT write** (so it can't masquerade as a complete result over a good prior file).

---

## 4. `highway_log_columns` — the single source of truth

`scripts/highway_log_columns.py`. Import-light by design: the data + `recognize()` need no third-party libs; the openpyxl helpers guard their import (`_OPX`, `:318`) so importing the module never fails when openpyxl is absent.

### 4.1 The COLUMNS table and derived constants

`COLUMNS` (`:35`) is the master list of `(group, canonical_label, vendor_label, meaning)` tuples in fixed column order. Everything else derives from it:
- `HEADER` (`:95`) = the 31 canonical labels (corrected; vendor's wrong label in `[brackets]`).
- `VENDOR_HEADER` (`:96`) = the 31 old vendor labels — so a pre-overhaul workbook still `recognize()`s.
- `DESC_IDX = 28`, `ROUTE_COL = "Route"`. Two asserts (`:100`) lock `DESC_IDX == 28`, `len(HEADER) == 31`, `len(VENDOR_HEADER) == 31`.
- `LEFT_BLOCK_IDX` / `RIGHT_BLOCK_IDX` (`:144`) = the index positions of the two 8-column roadbed blocks (`group == "Left Roadbed"` / `"Right Roadbed"`), asserted to be 8 each.

`recognize(header)` (`:106`) returns `has_route` (bool) if `header` equals either accepted label set (with or without a leading `"Route"`), else `None`. Comparison is by the **full label list** (so a same-width different report can't sneak through), and accepting *both* sets is what lets vendor-labeled workbooks still compare — the engine aligns by **position** and relabels to `HEADER`.

### 4.2 Ditto algorithm — `is_ditto` / `_is_plus_run` sense

A ditto marker is `+` / `++` / `+++`: "this attribute is not this row's subject; its value is on the PAIRED roadbed's own row." `is_ditto(value)` (`:152`) is `_DITTO_RE.fullmatch` where `_DITTO_RE = re.compile(r"\++")` (`:148`) — one-or-more `+`. The comparison engine carries its **own** mirror, `compare_core._is_plus_run` (`compare_core.py:305`), using `set(s) == {"+"}` — kept local so the generic engine carries no Highway-Log import (gated by `CompareSchema.ditto_nonasserting`). **These are two independent definitions of the same concept**; keep them in sync if you change the marker.

The key insight (`:121`–`:140` comment): a ditto is a **pointer, not data**, so in a comparison it is **non-asserting** (never a difference). And dittos are **column-agnostic** — they fill a whole 8-col roadbed block *but also* the shared median/access-control columns on divided-highway rows, which sit *outside* the blocks. So both the diff rule and the display fill key on the `+`-run **shape**, not the column.

### 4.3 Paired-roadbed fill — `fill_paired_roadbed` / `display_fills`

`fill_paired_roadbed(rows, loc_idx=0)` (`:170`) is display-only: for one route's rows (HEADER-aligned, document order), replace every dittoed cell with the paired roadbed's value and return `(filled_rows, ditto_cells)` where `ditto_cells` is the set of `(row_index, col_index)` it touched.

The fill-source search (`:200`): for a dittoed cell at `(i, col)`, scan all other rows `j` for a concrete (non-ditto, non-empty) value in the **same column**; PREFER a row at the **same base postmile** (`_base_postmile` via `_PM_RE = r"\d{3}\.\d{3}"`, `:149`/`:162` — strips the realignment prefix and roadbed/equation suffix) — that's the true paired roadbed (`same_base` wins and breaks the loop); else the nearest row by `abs(j - i)`. An unfillable ditto stays as-is but is still marked. Because the comparison treats ditto as non-asserting, **this fill never affects a diff result** — purely informational.

`display_fills(rows, has_route)` (`:220`) is the comparison-facing wrapper: it groups rows by route (`r[0]` when `has_route`), aligns each sub-list to HEADER by stripping the leading Route column (`off = 1 if has_route else 0`), runs `fill_paired_roadbed`, and returns `{global_row_index: {col_in_row: resolved_value}}` (shifting `col` back by `off`). The data-sheet writer attaches the resolved value as a cell comment + tint, so a reviewer SEES what a `+` resolved to while the cell keeps the raw ditto.

### 4.4 Roadbed-aware key — `roadbed_tag` / `roadbed_canonical_location`

The two sources encode a divided segment's roadbed differently: TSMIS (PDF + Excel) **suffix** the Location (`R021.466R` / `…L`); TSN **omits** the suffix and instead **dittos** the non-subject 8-col block. Keying on raw Location therefore splits the same physical row into a false one-sided pair across a TSMIS-vs-TSN comparison.

`roadbed_tag(row, off=0)` (`:260`) recovers the roadbed from which block is dittoed: count dittos in `LEFT_BLOCK_IDX` (`ld`) and `RIGHT_BLOCK_IDX` (`rd`); a Left-block-dittoed row describes the **RIGHT** roadbed (its Left geometry points at the paired row) → returns `"R"`; right-dittoed → `"L"`; neither/both → `""` (combined/indeterminate).

`roadbed_canonical_location(row, off=0, key_field=0)` (`:276`) is the canonical key:
- a Location already ending in `R`/`L` (PDF/Excel) is authoritative → returned unchanged;
- a suffix-less Location (TSN) gets `roadbed_tag(row, off)` appended.

The trailing equation `E` marker and the leading alignment prefix are **PRESERVED** — they're identity, not roadbed (a route-start `R000.000` must never collapse into a bridge `000.000`; `E` variants stay distinct). This key **strictly refines** — it can split, never merge — which is why it's safe. It's opt-in via `CompareSchema.key_normalizer`, set only on the TSMIS-vs-TSN schemas; cleared on cross-env/PDF-vs-Excel paths (same-encoding sources are already aligned). See [../comparison-engine.md](../comparison-engine.md) and `build/check_highway_log_roadbed.py`.

### 4.5 openpyxl helpers (Legend + tooltips)

`comment_for(label)` (`:332`) → a 320×120 hover `Comment` of `tooltip_for(label)` (`:303`, `[group] meaning`), or `None`. `write_legend_sheet(wb, title="Legend")` (`:344`) appends a Group / Column / Vendor label / Meaning sheet plus a ditto-explanation row — **streaming-safe** (only `create_sheet` + `append`; uses `WriteOnlyCell` when `wb.write_only`). `apply_header_tooltips(ws)` (`:399`) is the **non-streaming** counterpart — it iterates row 1 and sets `.comment` on each cell (used by the per-route writers, which are normal in-memory workbooks). Two paths because write-only cells must carry their comment before append, whereas a normal sheet is random-access.

---

## 5. End-to-end data flow (both PDF parsers)

```
output/<run>/highway_log_pdf/*.pdf   (or  tsn_library/highway_log/raw/*.pdf)
        │  consolidate()  — clears stale scratch, loops PDFs
        ▼
parse_pdf(path) ── per page ──> _cluster_lines / _lines
        │                          │ classify (totals/group/data/desc)
        │                          ▼
        │                       data line → center-in-window assign
        │                          (per-page rects | fixed COLUMN_WINDOWS)
        ▼
list of 31-col rows  ──> _write_route_workbook(rows, scratch.xlsx)
        │   (hlc.HEADER, apply_header_tooltips, write_legend_sheet,
        │    is_formula_injection guard)
        ▼
CONVERTED_DIR/*_route_<ROUTE>.xlsx
        │  consolidate_xlsx(header_override=hlc.HEADER,
        │     header_comment=hlc.comment_for,
        │     decorate_workbook=hlc.write_legend_sheet)
        ▼
<run>/consolidated/<stamped>.xlsx   ── drops into the Highway Log comparisons
```

`consolidate()` in both PDF modules: `day or latest_output_day()` → `input_dir_for(day)` / `out_path_for(day)`; clears `CONVERTED_DIR` scratch from a prior run (so removed routes don't linger); loops PDFs through `parse_pdf` + `_write_route_workbook`; then calls `consolidate_xlsx`; prepends per-run summary lines. TSN differs only in that `day` is ignored and the input is a fixed drop folder (`INPUT_DIR`, `INPUT_NOTE`).

---

## 6. Concurrency / invariants

- **No threading inside these modules.** They run on whatever worker thread the consolidator queue hands them; pdfplumber + openpyxl are used single-threaded. Cancellation is cooperative: `events.is_cancelled()` is polled between PDFs and (in the streaming combine) between input files; the streaming writer is finalized with `ws.close(); wb.close()` before returning `cancelled` (`consolidate_xlsx_base.py:206`).
- **Column-count invariants**: `len(HEADER) == 31`, `DESC_IDX == 28`, both roadbed blocks `== 8`, TSMIS-PDF `N_PDF_COLS == 30` — all asserted or hard-constant. `_make_row` and `ROW_KEYS` both depend on Description sitting at 28.
- **Header-position invariant** in the combine: a file whose row-1 ≠ `canonical_header` is skipped, never realigned. `header_override` must match length or it's dropped.
- **Empty-combine invariant**: never save a header-only workbook as `"ok"`.

---

## 7. Gotchas a maintainer will trip on

1. **Per-page vs fixed windows.** TSN windows are constant; TSMIS-PDF windows are derived from each page's shaded rects and *carried forward* if a page has no data band. A lost row in TSMIS-PDF almost always means a page yielded `page_windows = None` (no 30-cell band) — check `_page_column_windows` filters first, not `_assign_columns`.
2. **Orphan-page header.** TSMIS-PDF must use `_header_bottom` (content `ODOM`+`CITY`), not the `HEADER_BAND` fallback, or a description pushed onto a top-shifted orphan page gets swallowed. If descriptions go missing on short routes, suspect the header cutoff.
3. **Single-alpha left-margin marker.** TSMIS-PDF's data-row test accepts *any* single alphabetic first token (`texts[0].isalpha()`, `:355`), not a fixed `{C,R,L}` set — broader than the doc's "C/R/L" implies. A stray single letter at the left margin followed by a postmile would be read as a data row.
4. **Two ditto definitions.** `highway_log_columns.is_ditto` (`fullmatch r"\++"`) and `compare_core._is_plus_run` (`set(s) == {"+"}`) are independent; keep them equivalent.
5. **TSN ADT columns are parsed then dropped** — they're in `COLUMN_WINDOWS` but absent from `ROW_KEYS`. Adding a real column near them means editing the windows (which the standing rule forbids — §8).
6. **`Path` is imported but unused** in `consolidate_tsmis_highway_log_pdf.py` (`:49`) and `consolidate_tsn_highway_log.py` (`:47`) — harmless, but a linter will flag it.
7. **Ramp Summary's combined sheet is fixed-coordinate** — schema changes need manual cell-row edits in `build_combined_sheet`.

---

## 8. Extension points

**Add or relabel a Highway Log column** → edit `COLUMNS` in `highway_log_columns.py` only. `HEADER`, `VENDOR_HEADER`, `DESC_IDX`, the roadbed block indices, tooltips, Legend, and `recognize()` all derive from it. BUT: the two asserts (`len == 31`, `DESC_IDX == 28`, blocks `== 8`) will fire if you change the column *count* — and you'd then also have to touch `N_PDF_COLS`/`_make_row` (TSMIS-PDF), `ROW_KEYS`/`COLUMN_WINDOWS` (TSN), and re-run `build/check_highway_log_columns.py`. A pure **relabel** (same positions) is cosmetic and safe — the comparison aligns by position. To relabel only, accept the old labels too by adding to `_ACCEPTED` so pre-overhaul workbooks still `recognize()`.

**Why the windows are not re-derived.** The TSN `COLUMN_WINDOWS` are calibrated against real district PDFs and proven flawless over 60,083 rows; TSMIS-PDF derives windows per page precisely *because* its layout varies. Re-deriving TSN's by hand risks splitting fused columns (the `042.010LKPT` problem the windows exist to solve). Treat them as a verified constant — change them only with a fresh char-conservation audit (`build/check_tsn_description_leak.py`, `build/check_tsmis_pdf_parse.py`).

**Add a new XLSX-input consolidator** → set `INPUT_DIR`/`OUT_PATH`/`SHEET_NAME`/`REPORT_NAME` and call `consolidate_xlsx` (pass `header_override`/`header_comment`/`decorate_workbook` only if you need corrected labels). Per-route filenames MUST end `…_route_<ROUTE>.xlsx` for `ROUTE_FROM_NAME` to extract the route.

**Add a Ramp Summary schema row** → add to the relevant `*_GROUPS` list, the `GROUPS` display table, `LONG_LABELS`, and the fixed cell coordinates in `build_combined_sheet`. The audit `_chk_*` formulas pick up new columns automatically via `rng()`.
