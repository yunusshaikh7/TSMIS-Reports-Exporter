# Neutral Audit Scope and Provenance

Workflow role: **shared neutral input for independent Stage 1 audits**

This file describes what must be audited. It intentionally contains no Codex
or Claude verdicts.

## Objective

Audit the comparison outputs as end-user deliverables after the comparison
code project has finished. Verify every supported report/workflow combination,
both values and formulas, the truthfulness of every discrepancy class, workbook
presentation, and PDF evidence behavior. This phase observes and documents;
it does not implement fixes.

## Frozen source inputs

| Input | Location / identity |
|---|---|
| New report archive | `C:\Users\Yunus\Downloads\TSMIS\_inbox\2026-07-23 ssor-prod.zip` |
| Prior full report batch | `C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9` |
| TSN library and normalizers | Repository `tsn_library` |
| Repository | `C:\Users\Yunus\Projects\TSMIS-Reports-Exporter` |

The new archive came from the **development site of SSOR-prod**.
Permanent/main-site equivalence is a future test and must not be assumed by
either independent auditor.

## Report families

The active comparison topology covers:

1. Ramp Summary
2. Ramp Detail
3. Highway Sequence Listing
4. Highway Log
5. Intersection Summary
6. Intersection Detail
7. Highway Log (PDF)
8. Intersection Detail (PDF)
9. Highway Detail
10. Highway Detail (PDF)
11. Highway Sequence Listing (PDF)
12. Ramp Detail (PDF)

Highway Detail and Highway Detail (PDF) are currently greyed out on the dev
site. Historical files do not make them review-ready. Record their affected
cells as source-blocked unless the user supplies a current review-ready export.

Clean Road Highway is a supplemental comparison with separate values and
formulas decisions. Clean Road Intersection and Clean Road Ramp must be
explicitly classified according to actual application support; do not silently
invent a comparison path.

## Comparison workflows

The frozen deliverable topology has 88 decisions:

- Classic current-vs-prior environment: 12 report rows.
- Direct TSMIS-vs-TSN: 12 report rows.
- Production By Day TSMIS-vs-TSN: 12 report rows.
- Production Everything TSMIS-vs-TSN: 12 report rows.
- Production Baseline environment: 12 report rows.
- Production Everything environment: 12 report rows.
- Direct same-day PDF-vs-Excel self comparison: 7 report-family rows.
- Production Everything self comparison: 7 report-family rows.
- Clean Road Highway: 2 decisions, values and formulas.

For each applicable cell, audit values and formulas separately even when the
matrix displays them together as `V / F`.

The exact Everything evidence registry has 25 reviewable cells:

- Environment mode: 10.
- TSN mode: 10.
- Self mode: 5.

Evidence is a separate gate from the 88 deliverable decisions.

## Required audit behavior

1. Plan the work and create a visible matrix whose cells begin
   `UNVERIFIED`.
2. Inventory the source bundle and verify route/report sibling coverage before
   running a comparison.
3. Normalize the entire supported TSN library through the same entry point a
   user invokes.
4. Generate comparisons through public adapters and production By Day,
   Baseline, and Everything dispatch paths—not internal shortcuts that produce
   a different result from the app.
5. Retain generated comparisons in an auditor-specific output folder.
6. Audit the user-facing workbook sheets before evidence:
   Summary, Comparison, one-sided sheets, Spot Check, source sheets, Notes,
   visible formulas, widths, clipping, merged cells, filters, freezes, and
   instructions.
7. Verify values and live-formula twins. Recalculate formula workbooks with
   installed Excel when available and compare cached/data-only values with the
   values twin.
8. Independently recount source data where practical. Do not approve a
   discrepancy merely because the workbook is internally self-consistent.
9. Adversarially classify false positives, normalization-only differences,
   representation changes, missing rows, and materially misleading blanks.
10. Compare Excel-vs-TSN and PDF-vs-TSN siblings. A count mismatch is
    acceptable only when traced to a real difference in the source exports.
11. Require evidence only when both semantic comparison sources are PDFs.
    Evidence from Excel-vs-PDF, PDF-vs-Excel, Excel-vs-TSN, or
    PDF-vs-normalized-XLSX is prohibited even when a sibling PDF can be found.
12. For every eligible positive-difference PDF/PDF comparison, require a bound
    manifest, evidence workbook, image set, PDF-only read set, and accurate
    readable crops.
13. Inspect every retained evidence image, not a sample of the images.
14. Mark unavailable or unsupported cells `BLOCKED` or `N/A` with a precise
    reason. Never convert missing evidence into an approval.
15. Record exact artifact paths, hashes/counts where useful, and enough source
    witnesses for another agent to reproduce the conclusion.

## Verdicts

| Verdict | Meaning |
|---|---|
| `UNVERIFIED` | The auditor has not personally decided the cell |
| `APPROVED` | All applicable source, discrepancy, formula, presentation, workflow, and evidence gates passed |
| `DENIED` | The deliverable is absent, incorrect, misleading, or not release-ready |
| `BLOCKED` | A required review-ready source is unavailable |
| `N/A` | The application intentionally does not support the combination |

A process exit code, generated file, passing unit test, or internally matching
formula total is evidence, not approval by itself.

## Independence and sequencing

Codex and Claude work sequentially, not concurrently. Each performs a complete
first round without reading the other's verdicts. Only after both first rounds
are frozen do they cross-check findings, resolve conflicts against sources, and
build the canonical findings document.
