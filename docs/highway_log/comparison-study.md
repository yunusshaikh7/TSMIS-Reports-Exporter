# Highway Log — comparison study

Working notes for getting the Highway Log consolidations and comparisons
**flawless**. Built from direct inspection of the real TSMIS PDFs, the TSN
district PDFs, the vendor Excel exports, and the existing comparison workbooks
(2026-06-17).

> Status: **IMPLEMENTED (v0.14.0).** The resolution design below (non-asserting
> ditto + roadbed-aware key) shipped — see [../comparison-engine.md](../comparison-engine.md)
> §6–§7 for the engine wiring. This doc remains the authoritative record of the
> **domain convention** and the evidence behind it. (The resolver design here
> supersedes the earlier "track-aware carry-down" idea, which the evidence below
> disproves.)

---

## 1. The 31-column layout (confirmed against the report's own legend)

The legend prints on the PDF cover and defines every abbreviation. Column order
(the single source of truth is `scripts/highway_log_columns.py`):

```
LOCATION & DISTANCE : Location | Length(MI) | NA(Non-Add Mileage) | Cnty Odom | City
GENERAL             : RU | SPD | TER | HG | AC
LEFT  ROADBED  (8)  : ST | #Lns | SF | OT-SH Total | OT-SH Treated | T-W Wid | IN-SH Total | IN-SH Treated
MEDIAN         (2)  : TY/CL/BA | Wid/Var
RIGHT ROADBED  (8)  : ST | #Lns | SF | IN-SH Total | IN-SH Treated | T-W Wid | OT-SH Total | OT-SH Treated
TRAILING            : Description | Date of Rec | Sig Chg. Date
```

The legend does **not** define `+` / `++`. Their meaning was derived from the
data (§3).

## 2. The four data sources

| Source | What it is | Format on disk |
|---|---|---|
| **TSMIS Excel** | The vendor's Excel export. **Buggy** (drops rows / blanks roadbed blocks / pre-expands ditto / pads descriptions with tabs). | per-route `.xlsx` |
| **TSMIS PDF** | The site's Print layout saved as PDF (report 4b). The accurate substitute. | per-route `.pdf` → our consolidator |
| **TSN PDF** | District Highway Log PDFs (OTM52010). | district `.pdf` → our consolidator |
| **TSN (consolidated)** | The `.xlsx` our TSN-PDF consolidator produces. | `.xlsx` |

Both the **TSMIS PDF and the TSN PDF use the `+`/`++` convention**; only the
**Excel pre-expands it**. (TSMIS-PDF: 16,128 ditto cells; TSN: 19,044.)

### Two TSMIS-PDF export *formats* (same data, different rendering)
- "Formatted as the exporter gets them" — **landscape**, what the tool produces. **The production source.**
- "Formatted as manual export" — **portrait** hand-exports of routes 1–5S only.
- The parser is layout-agnostic (per-page column windows from shaded cell rects +
  content-based header), so both parse correctly. Routes 002/005/005S are
  byte-identical across the two formats; 001/003/004 are **different data
  snapshots** (confirmed in raw text: route 003 manual=323 rows, auto=228, each
  with postmiles the other lacks). **Always build from the production (landscape)
  format.**

## 3. The `+` / `++` convention (THE key finding)

Each data row describes **one roadbed**. The Location suffix says which:
`…R` = Right roadbed, `…L` = Left roadbed, no suffix / `…E` / combined = the
whole cross-section.

- A **Right-roadbed row** carries its **Right** block concrete and **dittos its
  Left block** (`+`/`++`).
- A **Left-roadbed row** carries its **Left** block concrete and **dittos its
  Right block**.
- A **combined / undivided row** carries **both** blocks concrete.

`+` (one-char column) / `++` (two-char column) therefore means: **"this roadbed
is not the subject of this row; its value is the one given on the paired
roadbed's own row for this stretch."** It is a *pointer to the other roadbed*,
**not a copy of the row above.**

Evidence (route 011, document order):
```
000.000R | LEFT=+ ++ + ++ ++ ++ ++ ++ | RIGHT=H 02 08 08 24 10 10   (Right row: Left dittoed)
000.199L | LEFT=H 02 10 10 24 08 08   | RIGHT=+ ++ + ++ ++ ++ ++ ++ (Left row: Right dittoed)
000.745  | LEFT=H 02 10 10 24 08 08   | RIGHT=H 02 08 08 24 10 10   (combined: both concrete)
```
The Left value (`H 02 10 10 24 08 08`) and Right value (`H 02 08 08 24 10 10`)
are **different** (mirror-image shoulders), so a ditto must be filled from the
**paired roadbed**, never from "the row above."

### Why carry-down (even track-aware) is WRONG
Route 1, postmile 081.505:
```
R081.017  LEFT IN/SH = 06/05      (previous segment)
R081.505R LEFT = ditto            (Right row)         → correct value 09/08
R081.505L LEFT = …09 08           (Left row)          ← the real Left value
R081.505  LEFT = …09 08           (combined)
```
Carry-down from the row above gives `06/05`; the correct value is `09/08`
(the paired Left row), which is what the Excel shows. The orphan analysis
confirms this at scale: the dittoed value lives in the paired roadbed row, which
prints **before, after, or at the same postmile** (TSMIS-PDF orphans for plain
carry-down: 450 forward-ref, 444 other-track, 254 route-start).

## 4. What this means for each comparison

| Comparison | Both sides ditto? | Ditto effect |
|---|---|---|
| **TSMIS-PDF vs TSN-PDF** | yes | Already apples-to-apples — `++`↔`++` matches; resolving both sides moved only **513 / 171,485** diffs. The 171k are REAL TSMIS-vs-TSN inventory differences. |
| **TSMIS-PDF vs TSMIS-Excel** | PDF yes, Excel no (expanded) | Maximally noisy: PDF `++` vs Excel's expanded value. ~70% of its 21,244 diffs are this notation mismatch. |
| **TSMIS-Excel vs TSN** (old) | Excel no, TSN yes | Same notation noise (the comparison being replaced). |

### TSMIS-vs-TSN diff composition (45,516 matched rows; only 14.1% fully clean)
- Sig Chg. Date **20,438** and Cnty Odom **20,356** (~24%) — **user decision: KEEP comparing both.**
- Length (MI) 8,699 — segmentation-driven.
- Remainder — real median / surface / lane / shoulder disagreements (the point of the comparison).

## 5. Resolution design (proposed — pending confirmation)

Because a ditto is a *pointer, not data*, the safe + flawless model is:

- **Diff logic:** a `+`/`++` cell is **non-asserting** — it never counts as a
  difference against the other side (its real value is compared on the
  authoritative roadbed row). This removes the PDF-vs-Excel notation noise with
  **zero risk of inventing a wrong value**.
- **Display (the "show what it did" requirement):** fill the dittoed cell with
  the best-effort paired-roadbed value and **mark it** (cell note / tint) as
  ditto-derived. Because the *diff* doesn't depend on this fill, an imperfect
  fill can never create a false result — it's purely informational.
- **Consolidated outputs stay byte-faithful** (`++` preserved) — resolution
  happens only in the comparison loader (`compare_highway_log._load_input`), the
  chokepoint shared by `compare_highway_log_pdf` and `compare_env`, so
  `compare_core` stays regression-locked.

Rejected: carry-down / track-aware carry-down (disproved in §3).

## 6. Other accuracy issues (tracked)
- **Trailing-tab descriptions** — Excel pads with tabs; `_xl_trim` strips spaces
  not tabs → 8 cosmetic false-positives (PDF-vs-Excel). Fix: normalize tabs in
  the loader.
- **Snapshot drift** — sample routes 1–5 used the manual (different-date) PDFs.
  Rebuild from the production landscape format.

## 7. Validation (Excel-free structural proof)

Confirmed by classifying every row's blocks across both consolidated sources
(no Excel needed — the structure speaks for itself):

**TSMIS-PDF (50,723 rows):** 47,502 combined rows = both blocks concrete; **1,047
`…R` rows = Left ditto + Right concrete; 918 `…L` rows = Left concrete + Right
ditto; ZERO mixed/partial blocks.** All 16,128 ditto cells = 2,016 roadbed rows ×
8 — i.e. 100% of dittos are full-block paired-roadbed pointers.

**TSN (60,083 rows):** same block pattern with two refinements —
1. TSN does **not** use `R`/`L` Location suffixes; it dittos the block on a plain
   row. So the rule is keyed on **the block being all-ditto**, not on the suffix.
2. TSN uses a wider ditto token **`+++`** (3-char columns). The ditto test is
   therefore "a run of one or more `+`" (`^\++$`), covering `+`, `++`, `+++`.

⇒ Universal rule (both sources): **a `+`-run cell is a pointer to the paired
roadbed — never data.** It overwhelmingly fills a full roadbed block (the 8 Left
or 8 Right cols), but it is **not confined to those two blocks**: on divided-
highway rows the SHARED median/access-control attributes ditto too (the 2026-06-18
audit found 1,020 such cells on the TSN side — 340 each in `AC`, `Med TY/CL/BA`,
`Med Wid`, always together, alongside a dittoed roadbed block). So both the
non-asserting diff rule (`compare_core._is_plus_run`) and the display fill
(`fill_paired_roadbed`) are **column-agnostic** — keyed on the `+`-run shape, not
the column. Filling those cells from the paired roadbed reproduces the Excel's
expansion on same-snapshot rows (~80%+; residual = the Excel's own drop bug +
cross-date snapshot drift, NOT fill error). Since the diff treats ditto as
**non-asserting**, fill accuracy is display-only and cannot affect correctness.

## 7b. Roadbed-encoding split between sources (2026-06-18 audit)

The adversarial Phase-4 audit found a real **alignment gap**: ~1,919 one-sided rows
per TSN comparison are the same physical segment whose Location is **encoded
differently** by the two sources, so the literal-Location key splits them into a
false (PDF/Excel-only + TSN-only) pair instead of comparing them.

Breakdown (PDF-vs-TSN; Excel-vs-TSN ≈ identical): **trailing R/L 1,446 (75%)**,
trailing `E` 324, leading section-marker 132, other 17. Only 99 are byte-identical;
1,820 carry ~7,836 genuine but currently-**uncompared** field diffs.

The dominant case is the **roadbed designator**: PDF/Excel tag the roadbed in the
Location suffix (`R021.466R` / `…L`); TSN omits it (`R021.466`) and relies on which
block is dittoed. The suffix ↔ dittoed-block correspondence is **100% consistent**
(suffix `R` → left-block-dittoed = right roadbed 788/788; `L` → 658/658), so the
roadbed identity is recoverable on BOTH sides. **But a naive postmile-similarity
reconciliation crosses roadbeds 6.2% of the time (90/1,446)** — pairing a PDF
right-roadbed row with a TSN left-roadbed row — which would manufacture FALSE diffs.

⇒ The only safe fix is a **roadbed-aware key**: `base postmile + roadbed-tag`, where
the tag comes from the trailing `R`/`L` suffix (PDF/Excel) OR the all-dittoed block
(TSN), unifying the two encodings so the same physical roadbed row keys identically.
This is a regression-locked change (it alters `keys_for`/the schema key derivation)
that WILL shift the approved Route-1 sample and the headline one-sided/diff counts,
so it must be built deliberately with full re-verification + sample re-approval — NOT
a quick suffix-strip (which over-merges, e.g. route-start `R000.000` vs bridge
`000.000`, and crosses roadbeds). Pending user decision.

## 8. Resolved decisions
1. `+`/`++`/`+++` = "see paired roadbed" — **confirmed structurally.**
2. Ditto is **non-asserting in the diff**; display fills from the paired roadbed,
   marked. (Full roadbed-merge reconstruction rejected as fragile.)
