# Claude Findings — Independent Output Audit

> Workflow artifact: **Stage 1B — Claude independent audit**
>
> Status: **NOT STARTED**
>
> Authority: Claude-round decisions only. Do not copy, confirm, dispute, or
> summarize Codex conclusions in this file during Stage 1B.
>
> Run with
> [Prompt 01 — Claude independent audit](prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md).
> Read [START-HERE.md](START-HERE.md) and
> [AUDIT-SCOPE-AND-PROVENANCE.md](AUDIT-SCOPE-AND-PROVENANCE.md), but preserve
> the independence firewall described there.

This file is the restart-safe workspace and final record for Claude's first
round. Every cell begins `UNVERIFIED` and may change only after Claude
personally inspects the generated deliverable and independently checks its
source truth. A successful process exit is not approval.

## Run record

| Field | Value |
|---|---|
| Reviewer | Claude |
| Started (UTC) | NOT STARTED |
| Completed (UTC) | NOT STARTED |
| Audit branch | `claude/post-comparison-output-audit` |
| Commit | PENDING |
| Generated-comparison root | PENDING |
| Raw-check / evidence-inspection root | PENDING |
| End-user entry points exercised | PENDING |
| Independence declaration | PENDING |

At completion, the declaration must state that Claude did not read
`MASTER-VERIFICATION.md`, `CODEX-FINDINGS.md`,
`FINAL-RECONCILIATION.md`, Codex-generated comparison artifacts, or Codex
scratch outputs before freezing this file and its artifacts.

## Verdict legend

| Verdict | Meaning |
|---|---|
| `UNVERIFIED` | Claude has not personally completed the required checks |
| `APPROVED` | Deliverable, discrepancy truth, formulas, and eligible evidence pass |
| `DENIED` | A material output, truth, formula, usability, or evidence defect exists |
| `BLOCKED` | A required review-ready input is unavailable |
| `N/A` | The product intentionally does not support the combination |

Cells written `V / F` are the values / formulas verdicts. Do not combine the
twins into one judgment.

## Deliverable decision matrix — 88 decisions

### Matrix A — classic new-batch vs retained-batch comparison (12)

| Report family | Values / formulas | Output paths | Source recount and adversarial notes |
|---|---|---|---|
| Ramp Summary | UNVERIFIED / UNVERIFIED | PENDING | |
| Ramp Detail | UNVERIFIED / UNVERIFIED | PENDING | |
| Highway Sequence Listing | UNVERIFIED / UNVERIFIED | PENDING | |
| Highway Log | UNVERIFIED / UNVERIFIED | PENDING | |
| Intersection Summary | UNVERIFIED / UNVERIFIED | PENDING | |
| Intersection Detail | UNVERIFIED / UNVERIFIED | PENDING | |
| Highway Log (PDF) | UNVERIFIED / UNVERIFIED | PENDING | |
| Intersection Detail (PDF) | UNVERIFIED / UNVERIFIED | PENDING | |
| Highway Detail | UNVERIFIED / UNVERIFIED | PENDING | |
| Highway Detail (PDF) | UNVERIFIED / UNVERIFIED | PENDING | |
| Highway Sequence Listing (PDF) | UNVERIFIED / UNVERIFIED | PENDING | |
| Ramp Detail (PDF) | UNVERIFIED / UNVERIFIED | PENDING | |

### Matrix B — TSMIS vs freshly normalized TSN (36)

| Report family | Direct V / F | By Day V / F | Everything V / F | Output paths and adversarial notes |
|---|---|---|---|---|
| Ramp Summary | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Ramp Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Sequence Listing | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Log | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Intersection Summary | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Intersection Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Log (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Intersection Detail (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Detail (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Sequence Listing (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Ramp Detail (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |

### Matrix C — Baseline and Everything environment paths (24)

| Report family | Baseline V / F | Everything ENV V / F | Output paths and adversarial notes |
|---|---|---|---|
| Ramp Summary | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Ramp Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Sequence Listing | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Log | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Intersection Summary | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Intersection Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Log (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Intersection Detail (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Detail (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Highway Sequence Listing (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |
| Ramp Detail (PDF) | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | |

### Matrix D — same-day PDF-vs-Excel self-consistency (14)

Evidence is prohibited for every mixed-format row in this matrix, even when a
sibling PDF exists elsewhere.

| Report family | Direct V / F | Everything SELF V / F | Evidence eligibility | Output paths and adversarial notes |
|---|---|---|---|---|
| Ramp Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | PROHIBITED | |
| Highway Sequence Listing | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | PROHIBITED | |
| Highway Log | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | PROHIBITED | |
| Intersection Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | PROHIBITED | |
| Ramp Summary | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | N/A | |
| Intersection Summary | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | N/A | |
| Highway Detail | UNVERIFIED / UNVERIFIED | UNVERIFIED / UNVERIFIED | PROHIBITED | |

### Matrix F — Clean Road Files supplemental comparison (2)

| Deliverable | Verdict | Output path | Independent source trace and adversarial notes |
|---|---|---|---|
| Values | UNVERIFIED | PENDING | |
| Formulas | UNVERIFIED | PENDING | |

Decision arithmetic at completion:

| Matrix | Expected | Closed | Approved | Denied | Blocked | N/A |
|---|---:|---:|---:|---:|---:|---:|
| A | 12 | 0 | 0 | 0 | 0 | 0 |
| B | 36 | 0 | 0 | 0 | 0 | 0 |
| C | 24 | 0 | 0 | 0 | 0 | 0 |
| D | 14 | 0 | 0 | 0 | 0 | 0 |
| F | 2 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **88** | **0** | **0** | **0** | **0** | **0** |

## Exact Everything evidence matrix — 25 cells

Every listed cell must be classified independently. `REQUIRED` means the
actual selected source pair is PDF-vs-PDF; `PROHIBITED` means either selected
source is not PDF; `N/A` means no comparison deliverable should exist. For
required evidence, inspect every generated image for target accuracy, legible
context, crop boundaries, stale/wrong-page content, duplication, and complete
coverage of evidence-eligible discrepancies.

### Environment comparisons (10)

| Report key | Eligibility | Availability / count | Every image inspected | Verdict | Notes |
|---|---|---:|---|---|---|
| `ramp_summary` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `ramp_detail` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `intersection_summary` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `intersection_detail` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `intersection_detail_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `ramp_detail_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_sequence` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_log` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_log_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_sequence_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |

### TSN comparisons (10)

| Report key | Eligibility | Availability / count | Every image inspected | Verdict | Notes |
|---|---|---:|---|---|---|
| `ramp_summary` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `ramp_detail` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `intersection_summary` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `intersection_detail` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `intersection_detail_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `ramp_detail_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_sequence` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_log` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_log_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_sequence_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |

### Self-comparisons (5)

| Report key | Eligibility | Availability / count | Every image inspected | Verdict | Notes |
|---|---|---:|---|---|---|
| `ramp_detail_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_sequence_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `intersection_detail_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_log` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |
| `highway_log_pdf` | UNVERIFIED | PENDING | UNVERIFIED | UNVERIFIED | |

Evidence arithmetic at completion:

| Expected | Closed | Approved | Denied | Blocked | N/A |
|---:|---:|---:|---:|---:|---:|
| 25 | 0 | 0 | 0 | 0 | 0 |

## Claude findings

Use stable IDs `PCOA-CL-001`, `PCOA-CL-002`, and so on. Do not reuse Codex IDs.
Each finding must contain:

- priority (`P1`, `P2`, or `P3`) and a concise title;
- exact affected matrix cells and values/formulas scope;
- exact raw inputs and generated outputs;
- observed behavior and expected end-user behavior;
- independent source-recount method and arithmetic;
- adversarial false-positive/false-negative samples traced to raw source;
- sibling PDF-vs-Excel discrepancy-count analysis where applicable;
- evidence eligibility, completeness, and crop accuracy where applicable;
- reproducible end-user-path steps;
- confidence, remaining uncertainty, and a final verdict.

None recorded yet.

## Validated-clean observations

Record material areas that received adversarial review and passed. “No issue
noticed” is not enough; cite outputs, source checks, counts, and samples.

None recorded yet.

## Output manifest

| Artifact or run group | Path | Hash / count | Purpose |
|---|---|---|---|
| PENDING | PENDING | PENDING | PENDING |

## Completion gate

- [ ] All TSN files were freshly normalized through the same whole-library
  path available to an end user.
- [ ] All 88 deliverable decisions are closed and their arithmetic reconciles.
- [ ] Values and formulas were judged separately.
- [ ] Formula twins were recalculated with installed Excel and compared with
  their data-only values twins.
- [ ] Deliverable sheets were inspected before evidence.
- [ ] Every claimed discrepancy class was challenged against raw source.
- [ ] PDF and Excel sibling discrepancy-count differences were explained by
  actual export differences, or recorded as findings.
- [ ] All 25 Everything evidence cells are closed and reconcile.
- [ ] Every eligible evidence image was personally inspected.
- [ ] Prohibited mixed-format evidence was checked for leakage.
- [ ] Highway Detail availability was judged from the current review-ready
  bundle, not old historical files.
- [ ] Generated comparisons and inspection records are retained and manifested.
- [ ] Claude findings and validated-clean observations are complete.
- [ ] Independence declaration is signed before the embargo is lifted.

When every item is true, replace the status with:

`CLAUDE ROUND 1 COMPLETE — EMBARGO MAY END`

Commit the frozen file and artifact manifest before reading any Codex audit
result. The next stage then uses
[Prompt 02 — cross-check and final findings](prompts/PROMPT-02-CROSSCHECK-AND-FINAL-FINDINGS.md).
