# Highway Log — corrected column labels

What this doc covers: the single source of truth for the Highway Log's 31-column
layout — the corrected canonical labels (the vendor TSMIS Excel export mislabeled
most of them), how those labels are written and recognized, the hover tooltips +
Legend sheet, and where the labeling is wired in. Owned here:
`scripts/highway_log_columns.py`. (v0.14.0.)

## TL;DR

- The vendor TSMIS Excel export **mislabeled most Highway Log columns**; those
  wrong labels propagated to every Highway Log workflow (TSN converter,
  consolidators, comparisons).
- The CORRECT meanings come from the report's own legend (the TSMIS legend page /
  the TSN OTM52010 header), verified against the printed document + the user.
- One source of truth: `scripts/highway_log_columns.py`. `HEADER` = the 31
  canonical labels (doc abbreviation + the vendor's old label in `[brackets]`);
  `VENDOR_HEADER` = the 31 exact old labels; `recognize()` accepts EITHER and
  aligns by column **POSITION**.
- The relabel is **purely cosmetic** — same column positions, so comparison
  RESULTS are unchanged (route-1 PDF-vs-Excel held at **11 diff rows / 67 cells**
  before and after).
- Every column carries a hover **tooltip** (Excel cell comment) and every Highway
  Log workbook gets a **Legend** sheet.
- Locked by `build/check_highway_log_columns.py`.

## Single source of truth: `scripts/highway_log_columns.py`

`highway_log_columns.py` is the ONE place that defines the column labels and
meanings so every Highway Log workflow agrees. It is import-light (the `COLUMNS`
data + `recognize()` need no third-party libs); the openpyxl-based Legend/tooltip
helpers guard their import so importing the module never fails when openpyxl is
missing (`_OPX` flag).

Key module symbols:

| Symbol | What it is |
|---|---|
| `COLUMNS` | list of `(group, canonical label, exact vendor label, meaning)` — the master data |
| `HEADER` | the 31 canonical labels (`[c[1] for c in COLUMNS]`) |
| `VENDOR_HEADER` | the 31 exact old vendor labels (`[c[2] for c in COLUMNS]`) — recognized too |
| `DESC_IDX` | `HEADER.index("Description")` = **28** (filled from follow-on PDF lines) |
| `ROUTE_COL` | `"Route"` — the leading column on consolidated workbooks |
| `recognize(header)` | is this row-1 a Highway Log layout (canonical OR vendor)? returns `has_route` bool or `None` |
| `legend_rows()` | rows for the Legend sheet, in column order |
| `tooltip_for(label)` / `comment_for(label)` | hover text / openpyxl `Comment` for a header label |
| `write_legend_sheet(wb, title="Legend")` | append the Legend worksheet (streaming-safe) |
| `apply_header_tooltips(ws)` | attach tooltips on a non-streaming sheet |

Layout guards assert at import: `DESC_IDX == 28`, `len(HEADER) == 31`,
`len(VENDOR_HEADER) == 31`.

The same module also owns the `+`/`++`/`+++` **ditto** helpers (`is_ditto`,
`LEFT_BLOCK_IDX`, `RIGHT_BLOCK_IDX`, `fill_paired_roadbed`, `display_fills`) and
the **roadbed-aware key** (`roadbed_tag`, `roadbed_canonical_location`). The ditto
CONVENTION + evidence and the roadbed-key derivation are documented in
[./comparison-study.md](./comparison-study.md) (§3, §7, §7b); this doc only owns
the column LABELS.

## The 31-column canonical layout

Column order is the TSMIS layout: Location & Distance, general, LEFT ROADBED (8),
MEDIAN (2), RIGHT ROADBED (8), Description, dates. (The confirmed layout is also
documented in [./comparison-study.md](./comparison-study.md) §1 — this is the same
layout, do not contradict it.)

`HEADER` labels are doc-abbreviation labels with the vendor's old label in
`[brackets]` **where it was wrong** (where the canonical label equals the vendor
label, there is no bracket).

| Idx | Group | Canonical (`HEADER`) | Vendor (`VENDOR_HEADER`) | Meaning |
|---|---|---|---|---|
| 0 | Location & Distance | `Location` | `Location` | Postmile (PM) — route location of the segment |
| 1 | Location & Distance | `Length (MI) [MI]` | `MI` | Segment length in miles (distance to the next postmile) |
| 2 | Location & Distance | `NA [N/A]` | `N/A` | **Non-Add Mileage** — NOT "not applicable" |
| 3 | Location & Distance | `Cnty Odom` | `Cnty Odom` | County odometer (county postmile / odometer reading) |
| 4 | Location & Distance | `City` | `City` | City code |
| 5 | (general) | `RU [R/U]` | `R/U` | Rural / Urban / Urbanized |
| 6 | (general) | `SPD` | `SPD` | Design Speed |
| 7 | (general) | `TER` | `TER` | Terrain |
| 8 | (general) | `HG [H/G]` | `H/G` | Highway Group |
| 9 | (general) | `AC [A/C]` | `A/C` | Access Control |
| 10 | Left Roadbed | `LB ST [LB T]` | `LB T` | Left roadbed — Surface Type (ST) |
| 11 | Left Roadbed | `LB # Lns [LB Lns]` | `LB Lns` | Left roadbed — Number of Lanes (# Lns) |
| 12 | Left Roadbed | `LB SF [LB F]` | `LB F` | Left roadbed — Special Features (SF) |
| 13 | Left Roadbed | `LB OT-SH Total [LB OT]` | `LB OT` | Left — Outside Shoulder (OT-SH), Total width (TO) |
| 14 | Left Roadbed | `LB OT-SH Treated [LB TR]` | `LB TR` | Left — Outside Shoulder (OT-SH), Treated width (TR) |
| 15 | Left Roadbed | `LB T-W Wid [LB T-W]` | `LB T-W` | Left — Traveled Way Width (T-W Wid) |
| 16 | Left Roadbed | `LB IN-SH Total [LB IN]` | `LB IN` | Left — Inside Shoulder (IN-SH), Total width (TO) |
| 17 | Left Roadbed | `LB IN-SH Treated [LB SH]` | `LB SH` | Left — Inside Shoulder (IN-SH), Treated width (TR) |
| 18 | Median | `Med TY/CL/BA [Med TCB]` | `Med TCB` | Median — Type (TY) / Curb & Landscape (CL) / Barrier (BA) |
| 19 | Median | `Med Wid/Var [Med Wid]` | `Med Wid` | Median — Width (Wid) / Variance (Var) |
| 20 | Right Roadbed | `RB ST [RB T]` | `RB T` | Right roadbed — Surface Type (ST) |
| 21 | Right Roadbed | `RB # Lns [RB Lns]` | `RB Lns` | Right roadbed — Number of Lanes (# Lns) |
| 22 | Right Roadbed | `RB SF [RB F]` | `RB F` | Right roadbed — Special Features (SF) |
| 23 | Right Roadbed | `RB IN-SH Total [RB IN]` | `RB IN` | Right — Inside Shoulder (IN-SH), Total width (TO) |
| 24 | Right Roadbed | `RB IN-SH Treated [RB SH]` | `RB SH` | Right — Inside Shoulder (IN-SH), Treated width (TR) — vendor's **first** duplicate "RB SH" |
| 25 | Right Roadbed | `RB T-W Wid [RB T-W]` | `RB T-W` | Right — Traveled Way Width (T-W Wid) |
| 26 | Right Roadbed | `RB OT-SH Total [RB OT]` | `RB OT` | Right — Outside Shoulder (OT-SH), Total width (TO) |
| 27 | Right Roadbed | `RB OT-SH Treated [RB SH]` | `RB SH` | Right — Outside Shoulder (OT-SH), Treated width (TR) — vendor's **second** duplicate "RB SH" |
| 28 | (ungrouped) | `Description` | `Description` | Feature description (printed on its own line below each segment) |
| 29 | (ungrouped) | `Date of Rec` | `Date of Rec` | Date of Record |
| 30 | (ungrouped) | `Sig Chg. Date` | `Sig Chg. Date` | Significant Change Date |

### The headline vendor mislabels

These are the load-bearing corrections (the columns the vendor got wrong; locked
by `EXPECT` in `build/check_highway_log_columns.py`):

- **`NA [N/A]` = Non-Add Mileage**, not "not applicable" (idx 2).
- **`LB ST [LB T]` = Left Surface Type**, not a bare "T" (idx 10); likewise
  `LB SF [LB F]` = Special Features (idx 12).
- The roadbed shoulder columns were cryptic 1–2-letter codes:
  `LB OT-SH Total [LB OT]` (idx 13, outside-shoulder Total) and
  `LB OT-SH Treated [LB TR]` (idx 14, outside-shoulder Treated).
- The vendor labeled **two different columns `RB SH`**: now
  `RB IN-SH Treated [RB SH]` (idx 24, inside-shoulder Treated) and
  `RB OT-SH Treated [RB SH]` (idx 27, outside-shoulder Treated). The `COLUMNS`
  meaning text for both explicitly notes "the vendor labeled this 'RB SH', same as
  the [other]-shoulder column".
- `Med Wid/Var [Med Wid]` = Median Width / Variance (idx 19).

Note the LEFT vs RIGHT roadbed column ORDER is mirror-imaged for the shoulders
(Left: …OT-SH Total, OT-SH Treated, T-W Wid, IN-SH Total, IN-SH Treated; Right:
…IN-SH Total, IN-SH Treated, T-W Wid, OT-SH Total, OT-SH Treated) — this matches
the report's own legend (see [./comparison-study.md](./comparison-study.md) §1).

## Description is column 28 (not a data-table header)

`DESC_IDX == 28`. In the source PDFs the Description prints on its own line BELOW
each segment, not as a header column inside the data table; the parser fills index
28 from those follow-on lines. See
[./pdf-and-tsn-parsing.md](./pdf-and-tsn-parsing.md).

## `recognize()` — accept either label set, align by POSITION

`recognize(header)` answers whether a loaded row-1 list (optionally with a leading
`"Route"`) is a Highway Log layout. It compares against BOTH `HEADER` and
`VENDOR_HEADER`:

- returns `False` when it matches a bare label list (no Route),
- returns `True` when it matches `["Route"] + base`,
- returns `None` when neither matches (so a same-width but different report can't
  sneak through — the comparison is against the full label list).

Accepting both label sets means a workbook built **before** this overhaul (with
the old vendor labels) still compares: the engine aligns by column **POSITION** and
relabels to the canonical `HEADER` for display. This is why the relabel is safe —
nothing keys on the label text; only the displayed header changes.

## Tooltips + Legend sheet on every Highway Log workbook

- **Per-column tooltips:** `tooltip_for(label)` returns the hover text
  (`[group] meaning`, or just the meaning for ungrouped columns).
  `comment_for(label)` wraps it in an openpyxl `Comment` (`320×120`, author
  "TSMIS Exporter"). `apply_header_tooltips(ws)` attaches them on an already-written
  non-streaming sheet; for write_only (streaming) sheets the caller sets
  `.comment` on the `WriteOnlyCell` BEFORE appending.
- **Legend sheet:** `write_legend_sheet(wb, title="Legend")` appends a worksheet
  with columns Group / Column / Vendor label (old) / Meaning (the Vendor cell is
  left blank when canonical == vendor), a dark-navy (`1F3864`) header band, a note
  explaining the bracketed old labels, and a trailing **Ditto row** explaining
  `+ / ++ / +++` (a pointer to the paired roadbed; never counted as a difference —
  see [./comparison-study.md](./comparison-study.md)). It is **streaming-safe**:
  uses only `create_sheet` + `append`, so it works on a write_only workbook too.
  No-op if openpyxl is unavailable.

## Wired through every Highway Log workflow

The corrected labels + tooltips + Legend are opt-in everywhere, so non-Highway-Log
outputs stay byte-identical:

| Workflow | How it opts in | File |
|---|---|---|
| TSMIS Highway Log (PDF) consolidator | `header_override=hlc.HEADER`, `header_comment=hlc.comment_for`, `decorate_workbook=hlc.write_legend_sheet` (+ a direct `write_legend_sheet` call) | `consolidate_tsmis_highway_log_pdf.py` |
| Excel Highway Log consolidator | same three params | `consolidate_highway_log.py` |
| TSN Highway Log consolidator | same three params (+ direct `write_legend_sheet`) | `consolidate_tsn_highway_log.py` |
| Excel consolidator base | gained opt-in `header_override` / `header_comment` / `decorate_workbook` — so Ramp Detail / Highway Sequence (which don't pass them) are untouched | `consolidate_xlsx_base.consolidate_xlsx` |
| Comparison engine | `CompareSchema.header_comment` / `legend_writer` — opt-in (default `None`), so non-HL comparisons are byte-identical; set on `compare_highway_log._SCHEMA` (`header_comment=hlc.comment_for`, `legend_writer=hlc.write_legend_sheet`) | `compare_core.py`, `compare_highway_log.py` |

`consolidate_xlsx_base` writes `header_override` instead of the canonical header
only when its length matches (else it logs a note and keeps the canonical), and
attaches `header_comment(label)` to each header cell when provided. The comparison
wiring is regression-locked — see [../comparison-engine.md](../comparison-engine.md).

## The relabel is purely cosmetic

Same column POSITIONS — only the displayed header changes — so the comparison
RESULTS are unchanged. Route-1 PDF-vs-Excel held at **11 diff rows / 67 cells**
before and after the relabel. Locked by `build/check_highway_log_columns.py`
(asserts `len(HEADER)==31`, `len(VENDOR_HEADER)==31`, `DESC_IDX==28`, the
`EXPECT` position→label corrections, and the exact `VENDOR_EXACT` old-label list).

## TSN log carries an extra group the 31-column format drops

The TSN district Highway Log (OTM52010) additionally has an **ADT Information**
group — Look Back / P / Look Ahead — that the 31-column TSMIS format does NOT
include, so it is not part of `HEADER`. The TSN consolidator drops it when
converting to TSMIS format. See [./pdf-and-tsn-parsing.md](./pdf-and-tsn-parsing.md).

## See also

- [./comparison-study.md](./comparison-study.md) — the `+`/`++`/`+++` ditto
  convention + evidence; the roadbed-aware key; the confirmed 31-column layout (§1).
- [./pdf-and-tsn-parsing.md](./pdf-and-tsn-parsing.md) — how the TSMIS PDF and TSN
  district PDFs are parsed into this layout (Description handling, ADT group drop).
- [../comparison-engine.md](../comparison-engine.md) — the regression-locked
  comparison engine that consumes `recognize()` / `HEADER` / the Legend + tooltips.
