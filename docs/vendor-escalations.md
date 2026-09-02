# Vendor escalations — defects the app can only report, never fix

Some problems this app finds are in the **source data TSMIS produces**, not in
anything the app does. It must keep reporting them truthfully and must never
paper over them: synthesizing a missing value would turn a vendor data defect
into a silent product lie, and every comparison downstream would then be
comparing an invention.

This file is the owner-facing record for each one — what was measured, against
what, and the exact test that says it is fixed when a corrected export arrives.
**Nothing here is a work item for the code.**

| ID | Report | Status | Opened |
|---|---|---|---|
| [VEN-01](#ven-01) | Highway Log (Excel), route 140 | **OPEN — needs a fresh export to confirm** | 2026-07-26 (PCOA-FINAL-020) |

---

## VEN-01 — route 140's Highway Log **Excel** export drops four whole columns
its own print carries {#ven-01}

**What the user sees.** Every Highway Log **Excel**-sourced comparison silently
compares blanks for route 140: `R/U`, `TER`, `H/G` and `A/C` are empty on every
row. The PDF edition of the same route, exported the same day, carries all four.

**How it was found.** The PDF-vs-Excel self check. It reports differences in only
2 of 252 routes, and for route 140 all 213 differing rows differ in the same
shape — `X ≠ (blank)` on those four columns and nothing else. That is the single
strongest argument in the audit for keeping that check: nothing else in the
product would have noticed.

**Measured.** Independently re-verified for RB-6 on 2026-08-31; the machine-
readable census is
[`hotfix-bundles/HF-11/witness/route_140_raw_census.json`](planning/post-comparison-perfection-output-audit/hotfix-bundles/HF-11/witness/route_140_raw_census.json).

| Source | Rows | `R/U` blank | `TER` blank | `H/G` blank | `A/C` blank |
|---|---:|---:|---:|---:|---:|
| Excel, 2026-06-19 | 199 | 4 | 0 | 4 | 0 |
| Excel, 2026-07-09 | 219 | 0 | 0 | 0 | 0 |
| **Excel, 2026-07-23** | **213** | **213** | **213** | **213** | **213** |
| Excel, 2026-07-23 — route **138**, same-day control | 264 | 0 | 0 | 0 | 0 |
| **PDF, 2026-07-23** — route 140's own print | **214** | **0** | **0** | **0** | **0** |

The print of the defective day carries real values throughout: `R/U` R×175 U×39,
`TER` F×112 M×62 R×40, `H/G` D×35 U×179, `A/C` C×214.

**Reading.** This is a **one-day, one-route regression in the vendor's Excel
export**, not a standing property of route 140. The same route was complete two
weeks earlier, its same-day sibling is complete, and its own same-day print is
complete. Something in the 2026-07-23 Excel generation dropped those four
columns for that route alone.

**Still unknown.** 2026-07-23 is the most recent route-140 Highway Log Excel
available locally. Whether the defect persists in a current export is **not
known** and cannot be answered without a fresh pull.

### What the owner needs to do

1. **Re-export** Highway Log for route 140 in both editions from the current
   site, and run the PDF-vs-Excel self check for that route.
2. If the four columns are still blank, raise it with the vendor with the census
   above: the print and the Excel disagree on the same day, for one route, on
   four specific columns.
3. Send the vendor the *measurement*, not the raw export — the exports are
   Caltrans-internal.

### On-delivery acceptance test

> Re-export Highway Log (both editions) for route 140 and run the PDF-vs-Excel
> self check. It must report **zero** `X ≠ (blank)` differences on `R/U`, `TER`,
> `H/G` and `A/C`.

Until that passes, VEN-01 stays open. **Never infer or synthesize the missing
values** — a Highway Log Excel comparison for route 140 is entitled to look
wrong, because the source is.

---

## Related: source truths that are NOT defects

Two neighbouring facts look like the same class and are not. Both are correct
behaviour, and both now have executable guards in
[`build/check_site_change_regression_guards.py`](../build/check_site_change_regression_guards.py):

* **Genuine PDF-only rows** (PCOA-FINAL-021). Route `074` @ `000.000`
  occurrence 2 and route `101` @ `R022.828` exist in the prior-7.9 raw Highway
  Log PDF and not in its Excel sibling. The PDF-derived universe correctly keeps
  them; the Excel-derived universe must never synthesize them. Witness:
  [`hotfix-bundles/HF-11/witness/pdf_only_rows.json`](planning/post-comparison-perfection-output-audit/hotfix-bundles/HF-11/witness/pdf_only_rows.json).
* **Site-side print changes already absorbed** (PCOA-FINAL-022). A stray leading
  `GENERATE` line now precedes four print families, and the Highway Sequence
  Listing (PDF) print was re-skinned to the TASAS layout with a wider text
  measure. Both parse correctly today because the parser derives each page's
  column windows from that page's own header positions; a future parser change
  must keep supporting **both** layouts.
