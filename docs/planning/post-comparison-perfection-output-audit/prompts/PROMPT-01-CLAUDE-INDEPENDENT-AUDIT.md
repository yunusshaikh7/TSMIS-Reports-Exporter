# Prompt 01 — Claude Independent Deliverable Audit

Copy and paste everything below into a new Claude chat.

---

You are Claude performing Stage 1B of the TSMIS post-comparison output
program. Conduct a complete, independent, adversarial audit of the comparison
deliverables. Codex has already performed a separate round, but independence
is mandatory: do not read or use Codex's findings, matrices, generated
comparisons, contact sheets, ledgers, handoff folder, or reconciliation
documents until your own round is frozen and committed.

Repository:
`C:\Users\Yunus\Projects\TSMIS-Reports-Exporter`

Read first, in this order:

1. `docs/planning/post-comparison-perfection-output-audit/START-HERE.md`
2. `docs/planning/post-comparison-perfection-output-audit/AUDIT-SCOPE-AND-PROVENANCE.md`
3. `docs/planning/post-comparison-perfection-output-audit/CLAUDE-FINDINGS.md`

Independence embargo before your Round 1 freeze:

- Do not open `MASTER-VERIFICATION.md`.
- Do not open `CODEX-FINDINGS.md`.
- Do not open `FINAL-RECONCILIATION.md`.
- Do not open `FINAL-FINDINGS-FOR-IMPLEMENTATION.md`.
- Do not use the Codex retained audit root ending in
  `post-comparison-perfection-output-audit-2026-07-23`.
- Do not ask another agent to summarize any embargoed artifact.

Use these frozen raw inputs:

- New dev-site SSOR-prod archive:
  `C:\Users\Yunus\Downloads\TSMIS\_inbox\2026-07-23 ssor-prod.zip`
- Prior full batch:
  `C:\Users\Yunus\Downloads\TSMIS\ground-truth\All Reports 7.9`
- TSN sources and normalizers: repository `tsn_library`

Create a separate Claude-only scratch/output root, for example:
`C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-output-audit-claude-independent-2026-07-23`.
Never overwrite the raw archive, the ground-truth batch, or Codex's retained
outputs.

Work on a documentation-only branch from current `main`, preferably
`claude/post-comparison-output-audit`. If that branch already exists, verify it
is the intended Stage 1B branch before continuing. Do not merge it yet.

Required method:

1. Inventory the new archive and the prior batch. Prove report, format, route,
   and sibling coverage before attempting each comparison. If a required
   review-ready source is missing, mark only the affected cells `BLOCKED` and
   state exactly what the user must provide.
2. Build a written execution plan. In `CLAUDE-FINDINGS.md`, instantiate the
   complete neutral 88-decision matrix plus the exact 25-cell Everything
   evidence matrix. Every cell must start `UNVERIFIED`.
3. Normalize the entire supported TSN library through the same user-facing
   normalize-all path used by the application. Record unsupported datasets
   explicitly.
4. Exercise the public comparators and the production By Day, Baseline, and
   Everything dispatch paths. Your generation path must represent what an end
   user actually does; do not approve outputs produced only by a lower-level
   shortcut.
5. Retain all Claude-generated values/formula comparisons, manifests, run
   ledgers, formula-recalculation copies, and evidence images in the
   Claude-only root for later cross-checking.
6. Prioritize the deliverable workbooks before evidence. Inspect every
   user-facing sheet and presentation contract, including Summary, Comparison,
   one-sided sheets, Spot Check, source sheets, Notes, keys, labels,
   instructions, widths, clipping, merged cells, filters, panes, visible
   formulas, and error cells.
7. Audit values and live-formula twins separately. Recalculate formula
   workbooks with installed Excel when available, then compare their cached
   values and semantics with the values twins. A structurally valid workbook
   does not override a false discrepancy or misleading presentation.
8. Independently recount source truth wherever practical. Adversarially inspect
   every discrepancy class for false positives, normalization-only differences,
   punctuation/case/spacing changes, missing rows, null-token projection,
   equation representation, key shifts, and misleading blank values.
9. Compare Excel-vs-TSN and PDF-vs-TSN siblings. If their counts differ, trace
   the difference to the raw exports; do not assume the PDF and Excel editions
   are equivalent.
10. Audit evidence after deliverable sheets. Evidence is required only when
    both semantic sources are PDFs. It is prohibited when either semantic side
    is Excel or a normalized XLSX, even if a sibling PDF is available.
11. For every eligible positive-difference PDF/PDF comparison, verify the
    manifest, evidence workbook, exact image-name set, PDF-only read set, and
    artifact hashes. Inspect every retained evidence image at full resolution
    for the correct report, route, page, row, field, value, target rectangle,
    readable bounds, and caption.
12. Run multiple independent checks in parallel when safe, but personally
    decide every final matrix cell. A successful process exit or generated
    file is never approval by itself.

Finding conventions:

- Use stable IDs `PCOA-CL-001`, `PCOA-CL-002`, and so on.
- Give every finding a severity (`P1`, `P2`, or `P3`), exact affected
  report/workflow cells, observed behavior, source-backed reasoning, impact,
  and durable witness paths.
- Separate verified root cause from hypothesis.
- Record validated clean behavior too; the cross-check round needs to know
  where you found no defect.
- Do not mention whether a finding agrees with Codex during this independent
  round.

Completion gates:

- All 88 deliverable decisions are terminal: `APPROVED`, `DENIED`, `BLOCKED`,
  or `N/A`.
- All 25 Everything evidence cells are terminal.
- Values/formulas, source truth, discrepancies, presentation, workflow parity,
  and evidence have been adjudicated wherever applicable.
- No `UNVERIFIED` result remains in Claude-controlled matrices.
- Generated outputs and witnesses are retained in the Claude-only root.
- `CLAUDE-FINDINGS.md` contains the final matrix, findings, validated clean
  observations, exact artifact root, and a short handoff summary.
- Change its status to `CLAUDE ROUND 1 COMPLETE — EMBARGO MAY END`.
- Commit only the Stage 1B audit documentation and appropriate small witness
  indexes on the Claude audit branch. Record the commit SHA in
  `CLAUDE-FINDINGS.md`.
- Do not implement fixes, edit application behavior, read Codex's work, merge
  to `main`, or begin reconciliation.

When complete, report the terminal decision counts, finding counts by
severity, output root, branch, commit SHA, and that Prompt 02 is now unblocked.

---
