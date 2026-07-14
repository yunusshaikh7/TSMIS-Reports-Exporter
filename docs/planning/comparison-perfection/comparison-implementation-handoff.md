# Comparison implementation handoff

Last updated: 2026-07-14  
Status: audit closeout complete; product remediation not started or authorized by this closeout

## Stop line and frozen product baseline

> **Superseded (2026-07-14, Batch 0).** The takeover has happened. The dirty worktree is
> committed to branch `comparison-perfection`; two authorized fixes (`APP_MODULES`, the 14
> silent swallows) then changed product source, so **`df7bb8fc…` no longer reproduces, by
> design**. The "any drift is a stop" rule below was written for the takeover — it has been
> discharged. **Do not hard-stop on that drift and do not restore the old digest.** The
> current boundary is the source-only manifest
> `d87951b2e7cd6b7f9107741c51af8c372da6fb5ea0c12595285070d633271809`
> (135 files / 2,890,535 bytes), and the gate is green at 121/121. No comparison semantics
> were changed; the Stage-8 freeze on comparison behaviour still stands.
> Execution record: [reconciliation-report.md](reconciliation-report.md) §14.

No product comparison code was changed after the freeze to complete this bounded
closeout. The complete `scripts/`
tree was frozen at 321 files / 7,423,809 bytes with canonical manifest SHA-256
`df7bb8fc3d997d60d82ecb93344f821e858feb015eed62fffe859958c9151bea`.
This is the takeover baseline, not permission to rewrite the comparison subsystem.

The worktree already contains user or other-agent changes. Do not reset, revert,
delete, reformat, or overwrite existing dirty product changes. Recompute the frozen
manifest before implementation; any drift is an ownership/reconciliation stop, not a
reason to force the tree back to this digest.

## Audit completion and remaining red scope

The audited capability census is complete:

- 29 classic comparison recipes;
- 12 Matrix rows;
- 30 Matrix row/mode placements;
- seven canonical TSN datasets; and
- five evidence families.

Stage 6 raw-source-to-normalized conservation is complete at 7/7 families. Stage 8
base comparison auditing is complete at 7/7 families. Those statements mean the
source, projection, and observed current-product behavior have been independently
classified and bound. They do **not** mean that product comparison perfection,
physical-source conservation, workbook evidence, or end-to-end correctness is green.

The remaining sequence is deliberately bounded:

1. **Stage 9 — companion and historical variants:** close current PDF/Excel companion
   legs and version-pinned older-report behavior without mixing editions or dates.
2. **Stage 10 — evidence:** prove all five evidence families from raw PDF/Excel inputs
   through normalized data, comparison workbooks, exact cells, and final evidence PDFs.
3. **Stage 11 — remediation:** change product code in small finding-owned batches only
   after the applicable source and evidence oracle is bound.
4. **Stage 12 — release:** run the complete regression, real-source, installed-Excel,
   artifact-generation, evidence, and release gates.

## Source and domain constraints

- TSN formats and semantics are fixed source truth. The raw library at
  `C:\Users\Yunus\Downloads\TSMIS\tsn_library` contains only delivered TSN source
  files and no generated `consolidated/` folders. Generate normalized artifacts only
  in isolated output locations; never admit generated output as raw input.
- Use both TSN PDF and Excel variants where supplied. Their mapping is part of the
  oracle, including which Excel row belongs to each exact PDF category or layered
  report section.
- Use both TSMIS PDF and Excel variants and version-pinned older reports where
  available. A cross-format pull-time difference must be classified, not silently
  normalized away.
- Highway Detail is the only TSMIS report still provisional and not fully approved by
  the vendor for review. Treat future format drift as expected and fail closed; do not
  infer a permanent rule from the current edition.
- If a required source role, edition, or comparison example is absent or ambiguous,
  stop and request the additional file rather than assume what should be compared.

## Highway Log findings that remain open

| Finding | Required correction |
|---|---|
| CMP-AUD-045 | Replace weak PM/location-only pairing with complete source-backed physical identity; retain district/county/route ownership and raw identity claims. |
| CMP-AUD-047 | Apply one Highway Log projection consistently so environment comparisons do not bypass tab/newline normalization. |
| CMP-AUD-048 | Recognize and canonicalize each supported canonical/vendor header edition before comparing layouts. |
| CMP-AUD-049 | Require selected filename, in-document route, emitted route, and requested route to agree; provenance mismatch must fail closed. |
| CMP-AUD-050 | Enforce a complete, unique, nonblank route universe so duplicate PDFs cannot overwrite or double-count and blank routes cannot certify complete. |
| CMP-AUD-066 | Persist and validate producer/report/source-role metadata so renamed or copied wrong-role workbooks cannot pass as PDF, Excel, or TSN inputs. |
| CMP-AUD-067 | Separate same-source PDF-to-Excel projection from cross-system TSN normalization so source differences remain visible. |
| CMP-AUD-157 | Preserve Highway Log group ownership, owner qualifier, three printed ADT fields, totals, and report/PDF provenance through normalization and evidence. |

These findings remain product-red even though their source and projection witnesses are
accepted. Keep their stable IDs; do not create replacement IDs merely because the
implementation is reorganized.

## Ordered implementation plan

1. **Take over safely.** Reconcile the current dirty worktree, bind exact source/code
   identities, and attach every batch to stable finding IDs and existing red fixtures.
2. **Preserve source truth first.** Extend typed rows, identities, sidecars, and report
   views so raw physical identity, provenance, totals, metadata, and currently omitted
   claims survive normalization without guessed meaning.
3. **Separate comparison purposes.** Give cross-system TSMIS-vs-TSN comparison and
   same-source PDF-vs-Excel verification distinct per-family projectors. Share only
   documented render equivalences; keep canonical and raw claims visible together.
4. **Enforce admission and completeness.** Validate source roles, producer/report
   metadata, route identity, exact route universe, duplicate/missing members, supported
   schemas, cancellation, and partial state before comparison can claim completion.
5. **Bind workbooks and evidence.** Give formulas, values, sidecars, payloads, report
   views, evidence crops, and PDFs one generation identity. Independently verify exact
   comparison cells against both normalized source variants and verify each final PDF
   against those cells and the original report location.
6. **Prove each batch.** Run the original fixture before the change and record red;
   run the identical fixture after the change and require green; then run the complete
   owning-family gate and all dependent capability placements. Never re-bless an
   unexplained count or cell delta.
7. **Run the full release gate.** Replay every family, current and historical source
   variant, all 29 classic recipes, all 30 Matrix placements, five evidence families,
   installed-Excel twins, cancellation/publication recovery, and end-to-end raw-source
   conservation before any perfection or release claim.

The detailed finding record remains
[comparison-audit-findings.md](comparison-audit-findings.md); sequencing details remain
in [comparison-remediation-plan.md](comparison-remediation-plan.md); source bindings and
accepted audit facts remain in
[comparison-phase4-tsn-source-rebaseline.md](comparison-phase4-tsn-source-rebaseline.md).
