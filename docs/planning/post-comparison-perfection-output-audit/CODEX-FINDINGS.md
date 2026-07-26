# Codex Findings — Post-Comparison-Perfection Output Audit

> Workflow artifact: **Stage 1A — Codex independent findings**
>
> Status: **COMPLETE AND FROZEN**
>
> Authority: Codex-round findings only. Finding IDs remain stable inputs to the
> later cross-check; they are not yet the joint implementation backlog.
>
> New-chat entry point: [START-HERE.md](START-HERE.md). The next action is
> [Prompt 01 — Claude independent audit](prompts/PROMPT-01-CLAUDE-INDEPENDENT-AUDIT.md).
> Claude must not read this file until its independent round is frozen.

This file is written for the user and the later Claude cross-check. Findings are
about shipped output behavior, not proposed implementation. No fix is included
in this phase.

## Confirmed findings

### PCOA-CX-001 — P1 — Ramp Detail cross-environment comparison cannot consume the new export

Status: **CONFIRMED**

Affected deliverables:

- Classic new dev-site SSOR-prod vs 7.9, values
- Classic new dev-site SSOR-prod vs 7.9, formulas
- Production Baseline environment comparison, values
- Production Baseline environment comparison, formulas
- Production Everything environment comparison, values
- Production Everything environment comparison, formulas

Observed behavior:

The public Ramp Detail folder comparator returns `error/failed` through the
classic, production Baseline, and Everything environment workflows and
publishes no workbook. It reports that the new consolidated input does not use
a recognized Ramp Detail column layout.

Adversarial source check:

- The new raw export has 11 populated source columns:
  `Location, PRE, PM, Date of Record, HG, Area 4, City Code, R/U, OF, TY, Description`.
- The new public consolidator correctly prepends `Route`, producing a populated
  12-column workbook.
- The old 7.9 export contains the earlier shifted/blank-column layout.
- Therefore this is not a malformed user export. The comparator's accepted
  layout contract is stale.

Impact:

The new valid report cannot be compared with an older report, so the requested
deliverable does not exist. Both classic values and formulas cells are denied.

Durable evidence:

- `run-ledgers/cross-version-tabular-values.json`
- `run-ledgers/cross-version-tabular-formulas.json`
- `run-ledgers/baseline-matrix-all-reviewable-both.json`
- `run-ledgers/everything-env-all-reviewable-both.json`
- New route-001 SHA-256:
  `93BAC751BB67D2732718C5C0DA2756F07A548BF04CE20C12E67017C88C5B50DF`
- Old route-001 SHA-256:
  `FE92B7B2C71C381607CF112AA3C1A0F2B85CF65480861BD904B9B65763329A60`
- New consolidated SHA-256:
  `FC376F130F338F771E3EEA9F29E61B2DCF5954D533DC109DF712C1250751A555`

### PCOA-CX-002 — P1 — Ramp Detail Excel vs TSN cannot consume its own fresh consolidation

Status: **CONFIRMED**

Affected deliverables:

- Direct Ramp Detail Excel vs TSN, values
- Direct Ramp Detail Excel vs TSN, formulas
- Production By Day Ramp Detail Excel vs TSN, values
- Production By Day Ramp Detail Excel vs TSN, formulas
- Any other matrix wrapper that reaches the same stale adapter contract

Observed behavior:

The public direct comparator and the production By Day GUI core both reject
their own freshly generated public consolidation as not being a consolidated
TSMIS Ramp Detail workbook, despite its leading `Route` column. Neither path
publishes values or formulas.

Adversarial source check:

The exact-header contract still describes the old shifted blank-column export.
Its positional field mapping would also map the new populated `OF`, `TY`, and
`Description` columns incorrectly if the header guard were bypassed. The
rejection therefore prevents a misleading result, but it also makes the
supported-looking report path unusable.

Impact:

An end user can normalize the TSN library and consolidate the latest TSMIS
export, but cannot produce the Ramp Detail Excel-vs-TSN deliverable.

Durable evidence:

- `run-ledgers/manual-vs-tsn-tabular-a-both.json`
- `run-ledgers/by-day-tsn-remaining-details-both.json`
- The source and consolidated hashes listed under PCOA-CX-001

### PCOA-CX-003 — P2 — By Day workbooks falsely call a fresh TSN library “older”

Status: **CONFIRMED**

Affected deliverables:

- By Day Ramp Summary vs TSN, values and formulas
- By Day Intersection Summary vs TSN, values and formulas
- By Day Highway Sequence Excel-vs-TSN, values and formulas
- By Day Highway Sequence PDF-vs-TSN, values and formulas
- By Day Highway Log Excel-vs-TSN, values and formulas
- By Day Highway Log PDF-vs-TSN, values and formulas

Observed behavior:

The generated workbook visibly says:

`TSN print: no source-claims record beside this normalized workbook (older normalization) — rebuild the TSN library to capture the print identity.`

Exact visible cells:

- Ramp Summary `Summary by Category!A6`
- Intersection Summary `Summary by Category!A7`
- Highway Sequence Excel and PDF `Notes!A9`
- Highway Log Excel and PDF `Notes!A4`

Adversarial source check:

- The TSN library was rebuilt immediately before the run by
  `tsn_library.build_consolidated(force=True)`.
- Both canonical normalized workbooks are complete/current.
- Both canonical `.outcome.json` sidecars contain `tsn_source_claims`, raw-PDF
  manifests, normalized-workbook identities, and artifact tokens.
- The By Day path compares a temporary `tsmis-tsn-consumer-*` workbook whose hash
  exactly matches the canonical workbook, but the consumer copy does not carry
  the adjacent source-claims sidecar.
- The direct public comparator, which reads the canonical library path, does not
  emit this warning.

Impact:

The numeric result is unchanged, but the final deliverable gives a false
provenance warning and tells the user to perform a rebuild that has already
succeeded. The twelve affected By Day workbooks are denied as deliverables
until the warning is truthful.

Durable evidence:

- `run-ledgers/tsn-library-rebuild.json`
- `run-ledgers/by-day-tsn-summaries.json`
- `logs/by-day-tsn-summaries.log`
- `source-audit/all-completed-workflow-note-audit.json`
- Canonical source-claims sidecars under
  `tsn_library/ramp_summary/consolidated` and
  `tsn_library/intersection_summary/consolidated`

### PCOA-CX-004 — P2 — Seven eligible PDF-vs-PDF evidence sets are unavailable

Status: **CONFIRMED AVAILABILITY GAP**

Affected deliverables:

- By Day Ramp Summary vs TSN evidence bundle
- Final Everything ENV Ramp Summary, Intersection Detail PDF, Ramp Detail PDF,
  Highway Log PDF, and Highway Sequence PDF evidence
- Final Everything TSN Ramp Summary evidence

Observed behavior:

Evidence was explicitly enabled in the production By Day run with two examples
and pair layout. The comparison completed but recorded zero evidence files.

The corrected, isolated Everything evidence reruns then reproduced the gap
with evidence explicitly enabled. All six positive-discrepancy Everything
cells above completed with zero evidence PNGs, evidence workbook, and rendered
manifest. The five ENV results include:

- Ramp Summary: 67 differing cells;
- Intersection Detail PDF: 17,562 differing cells;
- Ramp Detail PDF: 376 differing cells plus 5/8 one-sided rows;
- Highway Log PDF: 88,238 differing cells plus 2,095/1,174 one-sided rows;
- Highway Sequence PDF: 1,904 differing cells plus 7/246 one-sided rows.

The TSN Ramp Summary row also has positive discrepancies and zero evidence
artifacts. The UTF-8-safe final ledgers match their frozen arithmetic
references, so these are product availability results, not launcher-output
failures.

Adversarial modality check:

- The integrated TSMIS Ramp Summary consolidator parsed 126
  `tsar_ramp_summary_route_*.pdf` source reports.
- The canonical TSN input was normalized from
  `Ramp Summary Statewide_TSN.pdf`.
- This is therefore source-PDF-vs-source-PDF and is eligible under the user's
  evidence rule.
- By contrast, Intersection Summary's integrated TSMIS side is Excel; its zero
  evidence files are correct. Its PDF edition is currently export-only.
- Every additional affected Everything row above compares a TSMIS PDF-backed
  consolidation with another PDF-backed source set.

Impact:

The arithmetic comparison workbooks can still pass their independent numeric
gates, but all seven required evidence bundles are absent. Each evidence cell
is denied.

Durable evidence:

- `run-ledgers/by-day-tsn-summaries.json`
- `logs/by-day-tsn-summaries.log`
- `source-audit/new-bundle-inventory.json`
- `run-ledgers/everything-env-v2-env-evidence-all-reviewable.json`
- `run-ledgers/everything-tsn-v2-tsn-evidence-all-reviewable.json`
- `source-audit/everything-v2-evidence-binding-and-eligibility.json`
- `source-audit/everything-v2-evidence-final-crosscheck.json`

### PCOA-CX-005 — P1 — Ramp Detail PDF-vs-Excel self-comparison cannot consume the new Excel export

Status: **CONFIRMED**

Affected deliverables:

- Direct same-day Ramp Detail PDF-vs-Excel, values
- Direct same-day Ramp Detail PDF-vs-Excel, formulas
- Any SELF matrix wrapper that reaches the same Excel-side loader contract

Observed behavior:

The public same-source comparator opens both fresh consolidations, then rejects
the Excel side and publishes neither workbook. Its message says the workbook is
not consolidated and lacks the expected leading `Route` column.

Adversarial source check:

- The rejected workbook does have a leading `Route` column.
- Its exact 12-column header is:
  `Route, Location, PRE, PM, Date of Record, HG, Area 4, City Code, R/U, OF, TY, Description`.
- The PDF consolidation is also complete and begins with `Route`; its wider
  print schema ends in `On/Off, Ramp Type` as required.
- The Excel-side loader is the same stale old shifted-header/positional contract
  identified in PCOA-CX-002. The error text therefore misdiagnoses a valid new
  consolidation.

Impact:

The user cannot produce the same-day PDF-vs-Excel deliverable that is meant to
prove whether the two exports actually differ. This also blocks the requested
explanation of any PDF-vs-TSN versus Excel-vs-TSN count difference for Ramp
Detail.

Durable evidence:

- `run-ledgers/self-full-both.json`
- `logs/self-full-both.log`
- Excel consolidation SHA-256:
  `FC376F130F338F771E3EEA9F29E61B2DCF5954D533DC109DF712C1250751A555`
- PDF consolidation SHA-256:
  `79D4F4B7ABF4D9B17E612B2AFBC5116753BB2324115877B8D7CB9A211C99ACB7`

### PCOA-CX-006 — P2 — Ramp Detail self-comparison has 108 masked null-token false positives

Status: **CONFIRMED, MASKED BY PCOA-CX-005**

Affected deliverables:

- Direct same-day Ramp Detail PDF-vs-Excel, values and formulas
- Any SELF wrapper that uses the same loader after the header failure is fixed

Observed behavior:

An independent positional comparison paired all 15,213 Excel and PDF rows with
zero missing keys. After the documented whitespace/OOXML render equivalences,
the current loader projection still disagrees on 108 cells across 36 rows:

- 36 `Area 4` cells;
- 36 `OF` cells;
- 36 `Description` cells.

Every residual is one semantic null class. The new Excel export carries `-` in
`Area 4`/`OF` and `NO RAMP LINEAR EVENT` in `Description`; the PDF
consolidator has already projected those printed tokens to blank. A symmetric
same-source null projection reduces all 108 cells to zero differences.

Adversarial raw-source check:

Route 005 at `07-LA-005 / 025.218` visibly contains the same null-render tokens
in both raw exports. The Excel row stores `-`, `-`, and
`NO RAMP LINEAR EVENT`; the PDF text prints the same values. Therefore these
are not genuine source disagreements. The current self-comparison comments
assume the tokens are PDF-only, but this new Excel edition also carries them.

Impact:

PCOA-CX-005 currently prevents any workbook from being produced. If only that
header gate were corrected, this second stale assumption would create 108
false discrepancy cells in a same-source deliverable whose semantic truth is
zero.

Durable evidence:

- `source-audit/ramp-detail-pdf-excel-sibling-parity.json`
- `run-ledgers/self-full-both.json`
- Fresh raw sources
  `ramp_detail/tsar_ramp_detail_route_005.xlsx` and
  `ramp_detail_pdf/tsar_ramp_detail_route_005.pdf`

### PCOA-CX-007 — P1 — Highway Sequence self-comparison is entirely equation-representation false positives

Status: **CONFIRMED**

Affected deliverables:

- Direct same-day Highway Sequence PDF-vs-Excel, values
- Direct same-day Highway Sequence PDF-vs-Excel, formulas
- Any SELF wrapper that reaches the same comparator

Observed behavior:

The published self-comparison claims 1,395 differing matched rows and 3,714
differing cells despite 60,254 paired rows and no one-sided rows. The field
totals are:

- `PM Suffix`: 547;
- `HG`: 929;
- `FT`: 1,119;
- `Description`: 1,119.

The workbook's masks, displayed cells, per-field totals, one-sided sheets,
hash-bound payload, and outcome sidecar all reproduce those claims. This is not
an arithmetic/reporting mismatch inside the workbook.

Adversarial raw-source check:

Every flag belongs to one of 1,119 explicit PDF `EQUATES TO` relations. The PDF
prints an equation as a source line plus a target line; Excel folds the equation
marker, classification, suffix placement, and description onto its source
record.

For example, route 001 / Orange County prints:

- PDF source: `R 018.540`, blank suffix/HG/FT,
  `EQUATES TO END R REALIGNMENT`;
- PDF target: `018.530 E D H`;
- Excel source: `R 018.540 E D H`, `END R REALIGNMENT`;
- Excel target: `018.530 D H`.

An independent full-corpus canonicalization used only explicit equation lines,
their keyed Excel rows, and proven source/target relationships. It covered all
1,119 equation sources, including 39 county/route-boundary relations and three
delayed target markers, with zero unsupported cases. After canonicalization,
all 60,254 rows compare with zero differing rows and zero differing cells.

Impact:

The same-source deliverable presents 3,714 representation cells as data
disagreements even though its semantic truth is zero. Both values and formulas
are denied.

Durable evidence:

- `run-ledgers/self-full-both.json`
- `source-audit/self-highway-sequence-discrepancy-audit.json`
- `source-audit/highway-sequence-pdf-excel-equation-parity.json`
- Fresh route-001 sources
  `highway_sequence/highway_sequence_route_001.xlsx` and
  `highway_sequence_pdf/highway_sequence_route_001.pdf`

### PCOA-CX-008 — P1 — Highway Log vs TSN publishes 1,243 punctuation-only Description false positives per format

Status: **CONFIRMED**

Affected deliverables:

- Direct Highway Log Excel-vs-TSN, values and formulas
- Direct Highway Log PDF-vs-TSN, values and formulas
- Any By Day or Everything TSN wrapper that preserves the same comparison
  payload

Observed behavior:

The Excel-vs-TSN values workbook claims 2,723 Description discrepancies, while
the PDF-vs-TSN values workbook claims 2,827. Their signed payloads, field
totals, discrepancy masks, and displayed cells are internally consistent, so
this is not a workbook-arithmetic defect.

An independent full-field classification found exactly 1,243 token-identical
punctuation-only pairs in each workbook. Those 2,486 cells retain the same
ordered alphanumeric tokens and differ only in presentation punctuation. Common
examples include:

- `NEVADA STATE LINE , END OF COUNTY` versus
  `NEVADA STATE LINE /END OF COUNTY`;
- `BEG HOV ENF AREA NB/SB , IN MEDIAN` versus
  `BEG HOV ENF AREA NB/SB /IN MEDIAN`;
- `JCT 105 , IMPERIAL HWY` versus `JCT 105 /IMPERIAL HWY`.

The classifier independently reproduced every workbook claim, validated the
bound workbook identities, found no malformed displays, and separated real
blank/nonblank or token-changing differences from this punctuation-only class.
The identical 1,243-cell set in both fresh export formats rules out a
PDF-extraction artifact.

Impact:

Each direct deliverable overstates the differing-cell count by exactly 1,243
and presents semantically equivalent descriptions as discrepancies. Some
affected rows also differ in other fields, so no corrected differing-row total
is asserted here. Both values and formula twins are denied because they share
the same comparison masks and discrepancy payload.

Durable evidence:

- `source-audit/direct-all-field-semantic-candidates.json`
- `source-audit/highway-log-description-semantic-classification.json`
- `source-audit/manual-highway-log-vs-tsn-discrepancy-audit.json`
- `generated-comparisons/manual-vs-tsn/highway_log_vs_tsn (values).xlsx`
- `generated-comparisons/manual-vs-tsn/highway_log_pdf_vs_tsn (values).xlsx`

### PCOA-CX-009 — P1 — Mixed-source evidence is emitted and 34 of 1,394 reviewed crops are wrong or truncated

Status: **CONFIRMED**

Affected deliverable:

- Production By Day Highway Sequence Excel-vs-TSN evidence
- Production By Day Highway Log Excel-vs-TSN evidence
- Production By Day Intersection Detail Excel-vs-TSN evidence
- Production By Day Ramp Detail PDF-vs-normalized-XLSX TSN evidence
- Production By Day Intersection Detail PDF-vs-normalized-XLSX TSN evidence
- Final Everything TSN Intersection Detail, Intersection Detail PDF, Ramp
  Detail PDF, Highway Sequence, and Highway Log evidence
- Final Everything SELF Highway Sequence PDF, Intersection Detail PDF,
  Highway Log, and Highway Log PDF evidence
- Any wrapper that invokes evidence merely because a TSN PDF print is
  available even though both semantic comparison sides are not PDFs

Observed behavior:

The By Day run compared
`highway_sequence_consolidated 2026-07-23 ssor-prod.xlsx` against normalized
TSN data. Despite one semantic side being Excel, it published:

- `highway_sequence_vs_tsn 2026-07-23 ssor-prod (evidence).xlsx`;
- a bound evidence JSON manifest; and
- 12 PNGs: pair and stacked layouts for three Description and three FT
  examples.

The evidence manifest itself identifies the comparison input as the Excel
consolidation and labels each left panel `TSMIS (Excel)`. This is not a
PDF-vs-PDF comparison, so the entire evidence deliverable is ineligible.

The same production workflow also compared
`highway_log_consolidated 2026-07-23 ssor-prod.xlsx` against normalized TSN
data and nevertheless published a 14,822,812-byte evidence workbook, a bound
32,970-entry JSON manifest, and 180 PNGs. Its manifest read set explicitly
contains the Excel consolidation and twelve TSN PDFs; it does not contain a
TSMIS PDF. Each left panel is labeled `TSMIS (Excel)`. This independently
confirms the same eligibility defect on a second family at much larger scale.

The Intersection Detail Excel-vs-TSN row then reproduced the defect a third
time. It retained a 13,753,524-byte evidence workbook, a 23,472-byte bound
manifest, and 138 PNGs. The manifest read set explicitly contains
`tsar_intersection_detail_consolidated 2026-07-23 ssor-prod.xlsx` and
`Intersection Detail Statewide_TSN.pdf`, so the semantic left side is Excel
and the evidence is prohibited.

The Ramp Detail PDF-vs-TSN row reproduced the underlying source-substitution
defect from the opposite direction. Its semantic TSN side is the normalized
XLSX library, so this is PDF-vs-XLSX and evidence is prohibited. Nevertheless,
the evidence builder opportunistically borrowed
`tsn_library/ramp_detail/pdf/Ramp Detail Statewide_TSN.pdf` and published an
8,263,863-byte evidence workbook, an 18,474-byte rendered manifest, and 50
PNGs.

Intersection Detail PDF-vs-TSN then reproduced the same prohibited
PDF-vs-normalized-XLSX substitution. The renderer borrowed
`Intersection Detail Statewide_TSN.pdf` even though the semantic TSN side was
the normalized XLSX library, publishing 142 PNGs and a manifest-bound read set
of 78 PDFs.

Adversarial visual review:

All 12 full-resolution PNGs were personally inspected.

- Four images are visually aligned: both layouts for Description examples 1
  and 3.
- Description example 2 claims TSN `EQUATES TO`, but both layouts draw the red
  target box over blank description space instead of the printed
  `EQUATES TO` text.
- All six FT images claim a blank TSN value, but the red target box is drawn
  over the final `O` in the printed `EQUATES TO` marker.

Thus 8 of 12 images misidentify the asserted TSN field/value even before the
eligibility violation is considered. The crop contains the correct page and
nearby row, but the highlighted target is not accurate enough to support the
claim.

All 180 full-resolution Highway Log PNGs were also personally inspected. They
were grouped into 30 field contact sheets containing all six pair/stacked
layouts per field.

- 176 images crop the correct source row and accurately target the asserted
  field/value.
- `Description_1_pair.png`, `Description_1_stacked.png`,
  `Description_2_pair.png`, and `Description_2_stacked.png` claim a blank TSN
  Description, but draw the long red target rectangle across the following
  data row rather than the blank Description position for the selected row.

All 138 full-resolution Intersection Detail PNGs were personally inspected
through 25 field contact sheets. Every crop selects the correct route/post
mile, workbook cell, TSN row, and printed TSN field; none has a crop or target
placement error. This includes the quote-only Description discrepancy, where
the evidence accurately shows a real glyph difference that is nevertheless a
formatting-only false positive under PCOA-CX-010.

All 50 full-resolution Ramp Detail PNGs were personally inspected through nine
field contact sheets. Every crop selects the correct route/post mile and
printed field on both source PDFs, including blank/dash cells; none has a crop
or target-placement error. Their visual accuracy does not make the evidence
eligible because the TSN PDF was not the semantic source compared.

All 142 full-resolution Intersection Detail PDF-vs-TSN PNGs were also
inspected. The route/post-mile and field targets are accurate in 140. Both
`Control_Type_1_pair.png` and `Control_Type_1_stacked.png` claim TSMIS `B`
versus normalized TSN `S` at route 046 / post mile 50.904, but the borrowed TSN
PDF red box encloses `P`.

The exact final Everything evidence reruns reproduced the modality defect in
nine more prohibited cells:

- TSN Intersection Detail and Intersection Detail PDF each emitted 142 PNGs;
  each set is 140/142 accurate, with both `Control_Type_1` layouts boxing
  printed `P` while claiming normalized `S`.
- TSN Ramp Detail PDF emitted 50/50 accurate but prohibited PNGs.
- TSN Highway Sequence emitted 12 PNGs; only 2/12 fully support their
  captions, with eight wrong targets and two truncated TSMIS crops.
- TSN Highway Log emitted 180 PNGs; 174/180 are accurate, two target the
  following TSN row, and four truncate the captioned TSMIS Description.
- SELF Highway Sequence PDF emitted 18/18 accurate but prohibited PNGs.
- SELF Highway Log and Highway Log PDF each emitted 164/164 accurate but
  prohibited PNGs. The opposite-direction sets were reviewed separately
  because 152/164 same-name hashes differ.
- SELF Intersection Detail PDF emitted a prohibited evidence manifest despite
  having zero differences and zero PNGs.

The five retained By Day deliverables account for 522 ineligible PNGs and 14
inaccurate targets. The nine final Everything leaks add 872 PNGs, 20
wrong/truncated crops, and the manifest-only leak. Across all fourteen
mixed-source artifact sets, 1,394 PNGs were personally or independently
reviewed and 34 are inaccurate or insufficient.

Impact:

The user can receive evidence for a prohibited mixed-source comparison, and
some of that evidence also points at the wrong source location. The evidence
deliverable is denied. Values/formulas remain separately gated by their own
semantic and formula audits.

Durable evidence:

- `source-audit/highway-sequence-excel-vs-tsn-evidence-manual-review.json`
- `source-audit/highway-log-excel-vs-tsn-evidence-manual-review.json`
- `source-audit/intersection-detail-excel-vs-tsn-evidence-manual-review.json`
- `source-audit/ramp-detail-pdf-vs-tsn-evidence-manual-review.json`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/highway_sequence_vs_tsn
  2026-07-23 ssor-prod (evidence).json`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/highway_sequence_vs_tsn
  2026-07-23 ssor-prod (evidence images)`
- Full-resolution review copies under
  `visual-review/evidence-review/highway-sequence-excel-vs-tsn`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/highway_log_vs_tsn
  2026-07-23 ssor-prod (evidence).json`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/highway_log_vs_tsn
  2026-07-23 ssor-prod (evidence images)`
- Full-resolution review copies and 30 all-image contact sheets under
  `visual-review/evidence-review/highway-log-excel-vs-tsn`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/intersection_detail_vs_tsn
  2026-07-23 ssor-prod (evidence).json`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/intersection_detail_vs_tsn
  2026-07-23 ssor-prod (evidence images)`
- Full-resolution review copies and 25 all-image contact sheets under
  `visual-review/evidence-review/intersection-detail-excel-vs-tsn`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/ramp_detail_pdf_vs_tsn
  2026-07-23 ssor-prod (evidence).json`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/ramp_detail_pdf_vs_tsn
  2026-07-23 ssor-prod (evidence images)`
- Nine all-image contact sheets under
  `visual-review/evidence-review/ramp-detail-pdf-vs-tsn`
- `tmp/post_comparison_output_audit/source-audit/subagent-intersection-detail-pdf-vs-tsn-evidence-manual-review.json`
- `tmp/post_comparison_output_audit/source-audit/subagent-evidence-finish-binding-audit.json`
- `tmp/post_comparison_output_audit/visual-review/evidence-review/SUBAGENT-EVIDENCE-AUDIT.md`
- `tmp/post_comparison_output_audit/source-audit/EVERYTHING-V2-EVIDENCE-PERSONAL-REVIEW.md`
- `tmp/post_comparison_output_audit/source-audit/SUBAGENT-EVERYTHING-V2-VISUAL-AUDIT.md`
- `tmp/post_comparison_output_audit/visual-review/everything-v2-evidence-preliminary/`
- `source-audit/everything-v2-evidence-binding-and-eligibility.json`
- `source-audit/everything-v2-evidence-final-crosscheck.json`

Audit-harness exclusion:

The first evidence-enabled By Day launcher inherited a Windows cp1252 stdout
stream. After evidence had been atomically promoted, the disposable launcher's
`print()` callback raised on the production status arrow, so the outer core
logged a late “evidence skipped” message. The traceback terminates in
`run_by_day_tsn_audit.py`, not the GUI event sink. That status contradiction is
therefore excluded from PCOA-CX-009. The audit launchers are explicitly
UTF-8-safe. The exact final ENV, TSN, and SELF evidence sequences completed
through the production core, matched their frozen arithmetic references, and
were closed by the 25-cell eligibility/binding cross-check. The harness-only
status contradiction did not recur. The published, manifest-bound images
remain valid visual witnesses for the independent modality and crop findings.
After that binding JSON was durable, the disposable contact-preparation
wrapper also split an unquoted path containing ` (evidence images)` and
exited. No comparison or evidence generation was rerun. The unchanged contact
helper was invoked directly with quoted paths and produced all 182 contact
sheets across 10 directories with zero helper stderr; this second wrapper-only
argument issue is likewise excluded from product findings.

### PCOA-CX-010 — P2 — Three more report families publish formatting-only Description discrepancies

Status: **CONFIRMED**

Affected direct deliverables:

- Highway Sequence Excel-vs-TSN, values and formulas: 11 cells
- Highway Sequence PDF-vs-TSN, values and formulas: the same 11 cells
- Ramp Detail PDF-vs-TSN, values and formulas: 2 cells
- Intersection Detail Excel-vs-TSN, values and formulas: 1 cell
- Intersection Detail PDF-vs-TSN, values and formulas: the same 1 cell
- Any By Day or Everything TSN wrapper that preserves those comparison
  payloads

Observed behavior:

An independent full-Description sweep decoded each hash-bound comparison
payload, reproduced all published Description counts, and classified every
displayed pair. It found 26 formatting-equivalent cells across the five
workbooks:

- Highway Sequence contains seven case-only pairs and four
  punctuation/spacing-only pairs per format. Examples include
  `CITRUS AVE OC 54-1293` versus `Citrus Ave OC 54-1293`,
  `SEG, NB OFF, LT,SF AIRPRT` versus `SEG,NB OFF,LT,SF AIRPRT`, and
  `SLO SB CO LINE` versus `SLO/SB CO LINE`.
- Ramp Detail PDF repeats two of those punctuation/spacing-only pairs:
  `SEG, NB OFF, LT,SF AIRPRT` versus `SEG,NB OFF,LT,SF AIRPRT`, and
  `NB OFF TO S. GEYSERVILLE` versus `NB OFF TO S.GEYSERVILLE`.
- Both Intersection Detail formats publish `''F'' ST` versus `"F" ST`.
  Ordered alphanumeric tokens are identical; only quotation style changes.

Adversarial source check:

The workbook identities and claims all bind. The two fresh TSMIS siblings agree
on every listed pair. The Intersection Detail quote pair was already traced
through fresh Excel, fresh PDF, normalized TSN, and raw TSN; that trace proves
the literal source forms but also proves the semantic content is the same.
Likewise, the Ramp Detail normalized TSN workbook matches its raw TSN source
field-for-field. These are normalizer misses, not invented workbook displays.

Impact:

The affected deliverables overstate differing-cell totals by 11, 11, 2, 1, and
1 respectively. Affected rows may also differ in another field, so corrected
differing-row totals are not asserted here. Values and formula twins are denied
because they share the same discrepancy masks and payload.

Durable evidence:

- `source-audit/direct-all-field-semantic-candidates.json`
- `source-audit/direct-description-semantic-classification-remaining.json`
- `source-audit/highway-sequence-description-case-four-source-trace.json`
- `source-audit/intersection-detail-description-four-source-trace.json`
- `source-audit/ramp-detail-description-punctuation-four-source-trace.json`
- `source-audit/ramp-detail-tsn-normalization-parity.json`
- `source-audit/highway-sequence-pdf-excel-equation-parity.json`

### PCOA-CX-011 — P1 — Eligible PDF-vs-PDF evidence mislocalizes retained Highway Sequence/Log and final Everything Highway Sequence targets

Status: **CONFIRMED**

Affected deliverables:

- Production By Day Highway Sequence PDF-vs-TSN evidence
- Production By Day Highway Log PDF-vs-TSN evidence
- Final Everything TSN Highway Sequence PDF-vs-TSN evidence

Observed behavior:

This is an eligible evidence comparison: the fresh TSMIS side is a PDF and
the normalized TSN side originates in district PDFs. The production path
retained the evidence workbook, bound manifest, and all 12 requested PNGs:
pair and stacked layouts for three Description and three FT examples.

Every full-resolution PNG was inspected. The pages, row context, labels, and
six non-problem layouts are correct, but six layouts misidentify the target:

- `Description_2_pair.png` and `Description_2_stacked.png` draw the TSN red
  rectangle over blank Description space even though the compared
  `EQUATES TO` text is shifted into the postmile area on this special line.
- `FT_1_pair.png`, `FT_1_stacked.png`, `FT_3_pair.png`, and
  `FT_3_stacked.png` enclose the final `O` in printed `EQUATES TO` rather than
  identifying the compared blank FT position.

The eligible Highway Log PDF-vs-TSN path retained 180 manifest-bound PNGs.
An adversarial second full-resolution review corrected the prior 180/180 pass
to 178/180. `Description_3_pair.png` and
`Description_3_stacked.png` caption route 395 / postmile `T121.831`, with a
blank TSN Description, but the TSN red target is drawn across numeric cells on
the following `T121.945` row. The other 178 layouts are accurate and readable.

The exact final Everything TSN Highway Sequence PDF set is a distinct capture:
all 12 same-name PNG hashes differ from the retained By Day set. Its manifest,
evidence workbook, exact image-name set, and 29-file PDF-only read set all
bind, so every image was independently inspected rather than inheriting the
retained ruling. All six Description layouts and both FT example 1 layouts
are accurate. The four FT example 2 and 3 pair/stacked layouts claim a blank
TSN FT but box the final `O` in printed `EQUATES TO`. The final set therefore
passes artifact binding but fails crop accuracy at 8/12.

The exact final Everything TSN Highway Log PDF set was also independently
reviewed because all 180 same-name hashes differ from the retained set. It
passes at 180/180 and is not included among this finding's affected
deliverables. That distinct pass prevents an invalid inheritance of the
retained route 395 failures.

Impact:

Availability is complete for all three affected bundles, but none is
deliverable-ready. The retained Highway Sequence set mislocalizes three of six
sampled discrepancies in both layouts (six of 12 PNGs); the retained Highway
Log set mislocalizes one sampled discrepancy in both layouts (two of 180
PNGs); and the exact final Everything Highway Sequence set mislocalizes two of
six sampled discrepancies in both layouts (four of 12 PNGs).

Durable evidence:

- `source-audit/highway-sequence-pdf-vs-tsn-evidence-manual-review.json`
- `visual-review/evidence-review/highway-sequence-pdf-vs-tsn`
- `tmp/post_comparison_output_audit/visual-review/highway-log-pdf-vs-tsn-contacts/Description_contact.png`
- `tmp/post_comparison_output_audit/visual-review/everything-v2-evidence-preliminary/tsn-highway_sequence_pdf-final-primary/`
- `tmp/post_comparison_output_audit/source-audit/EVERYTHING-V2-EVIDENCE-PERSONAL-REVIEW.md`
- `tmp/post_comparison_output_audit/source-audit/SUBAGENT-EVERYTHING-V2-VISUAL-AUDIT.md`
- `tmp/post_comparison_output_audit/source-audit/SUBAGENT-FINAL-TSN-HIGHWAY-SEQUENCE-PDF-VISUAL-CHECK.md`
- `source-audit/everything-v2-evidence-binding-and-eligibility.json`
- `source-audit/everything-v2-evidence-final-crosscheck.json`
- `comparisons/tsn-by-day/2026-07-23 ssor-prod/highway_sequence_pdf_vs_tsn
  2026-07-23 ssor-prod (evidence images)`

### PCOA-CX-012 — P2 — Clean Road Highway publishes five formatting-only landmark discrepancies

Status: **CONFIRMED**

Affected deliverables:

- Clean Road Highway ArcGIS-vs-TSN values workbook
- Clean Road Highway ArcGIS-vs-TSN formula workbook

Observed behavior:

The fresh app-generated values workbook is trusted/current. An independent
deliverable-sheet recount passes at 52,647 paired, 5,081 ArcGIS-only, 7,436
TSN-only, 2,635 identical, 50,012 differing rows, and 291,292 displayed
discrepancy claims. Its hash-bound payload and every field total bind. An
all-field semantic screen initially exposed 70
punctuation-looking candidates. Correct numeric classification proved that 65
are real sign changes, leaving exactly five
`THY_LANDMARK_SHORT_DESC` claims:

- one leading apostrophe before `-VIA BIG BEAR BLVD-`;
- three leading apostrophes before an otherwise identical dashed placeholder;
- `SLO SB CO LINE` versus `SLO/SB CO LINE`.

All five were then traced independently through four source stages. Each
displayed left value occurs in `clean_highway_built.xlsx` and its raw ArcGIS
landmark layer row; each right value occurs in the normalized and raw TSN
workbooks. The compared strings have the same semantic tokens. The
60,083-row × 74-column TSN normalization audit also found zero changed,
missing, or extra cells, so normalization did not create these claims.

Impact:

The workbook arithmetic is internally consistent, but the deliverable
overstates differing cells by five. The formula twin uses the same comparison
payload and is denied for the same semantic defect. Its package and structural
gates cover 6,442,773 live formulas with zero formula error tokens and a valid
manual/F9 calculation policy. The completed installed-Excel gate also passes
cached-value parity with no unexpected semantic or Excel errors; that formula
approval cannot make the five false discrepancy claims approvable.

Durable evidence:

- `source-audit/clean-road-highway-all-field-semantic-candidates-existing.json`
- `source-audit/clean-road-highway-all-field-semantic-candidates-fresh.json`
- `source-audit/clean-road-deliverable-sheet-recount.json`
- `source-audit/clean-road-formula-package-integrity.json`
- `source-audit/clean-road-formula-sheet-structures.json`
- `source-audit/clean-road-highway-landmark-four-source-trace.json`
- `source-audit/clean-road-highway-tsn-normalization-parity.json`

### PCOA-CX-013 — P2 — Statewide summary deliverables visibly truncate categories and instructions

Status: **CONFIRMED**

Affected deliverables:

- Classic Ramp Summary and Intersection Summary, values and formulas
- Direct Ramp Summary-vs-TSN and Intersection Summary-vs-TSN, values and
  formulas
- By Day Ramp Summary-vs-TSN and Intersection Summary-vs-TSN, values and
  formulas
- Baseline Ramp Summary and Intersection Summary, values and formulas
- final isolated Everything ENV Ramp Summary and Intersection Summary, values
  and formulas
- final isolated Everything TSN Ramp Summary and Intersection Summary, values
  and formulas

Observed behavior:

A conservative font-metric audit measured only user-visible, non-wrapped cells
whose normal Excel overflow is blocked by a populated adjacent cell or merged
range. Hidden helper columns were excluded and a six-pixel tolerance was
applied. All 24 reviewed workbooks fail:

- classic and Baseline Ramp Summary: 8 materially clipped `Summary` cells per
  twin;
- classic and Baseline Intersection Summary: 13 materially clipped `Summary`
  cells per twin;
- direct and By Day Ramp Summary-vs-TSN: 5 clipped `Summary` cells plus 29
  clipped `Comparison` category cells per twin;
- direct and By Day Intersection Summary-vs-TSN: 5 clipped `Summary` cells plus
  66 clipped `Comparison` category cells per twin;
- Everything ENV Ramp Summary: 6 materially clipped cells per twin;
- Everything ENV Intersection Summary: 11 materially clipped cells per twin;
- Everything TSN Ramp Summary: 34 clipped cells per twin; and
- Everything TSN Intersection Summary: 71 clipped cells per twin.

The final Everything work adds 8 workbooks / 244 clipped cells, expanding the
confirmed scope from 16 workbooks / 504 cells to **24 workbooks / 748 materially
clipped cells**. Installed Excel independently reproduced the direct/By Day
Ramp Summary presentation. For
example, the `Comparison` column is only 89 screen pixels wide while category
labels require up to 292 pixels. Entries such as
`Ramp Type: C - Direct or Semi-direct Connector (Left)` are displayed only as
`Ramp Type: C`, so multiple categories cannot be distinguished from the sheet
without selecting the cell or manually resizing the column. Summary status,
one-sided-row, self-check, and explanatory lines are also visibly cut off.

The spreadsheet artifact renderer reproduced the same clipping, and an
Excel-native PDF export proved it is present in the application an end user
actually opens.

Impact:

The numeric results remain bound and correct where their independent arithmetic
gates passed, but the workbooks are not presentation-ready deliverables. A user
cannot read important category identities and instructions in the default
view. Every affected values/formula twin is denied on visual QA.

Durable evidence:

- `source-audit/statewide-summary-visible-text-clipping.json`
- `tmp/post_comparison_output_audit/source-audit/everything-v2-statewide-summary-visible-text-clipping.json`
- `tmp/post_comparison_output_audit/source-audit/everything-v2-visual-parity-independent-validation.json`
- `tmp/post_comparison_output_audit/artifact_visual/byday-ramp-summary-tsn-values-renders`
- `tmp/post_comparison_output_audit/artifact_visual/byday-intersection-summary-tsn-values-renders`
- `tmp/post_comparison_output_audit/visual-review/excel-native/byday-ramp-summary-comparison.pdf`
- `tmp/post_comparison_output_audit/visual-review/excel-native/byday-ramp-summary-comparison-page1.png`

### PCOA-CX-014 — P2 — Large/detail workbooks clip material Summary, Spot Check, and key content

Status: **CONFIRMED**

Affected deliverables:

- all seven delivered non-summary classic cross-version values/formula pairs;
- seven direct detail TSMIS-vs-TSN values/formula pairs;
- all three delivered direct PDF-vs-Excel self values/formula pairs;
- five non-summary Baseline values/formula pairs;
- Clean Road Highway values and formulas;
- all seven final isolated Everything ENV non-summary values/formula pairs;
- all seven final isolated Everything TSN non-summary values/formula pairs; and
- all four final isolated Everything SELF values/formula pairs.

Observed behavior:

A package-level review covered 32 workbooks across 16 representative
large/detail pairs; all 16 values twins and all 16 formula twins fail the
visual gate. The same shared layout was also checked against the seven classic
detail pairs, including a native-Excel render of classic Ramp Detail (PDF).
Final isolated Everything package adjudication then checked every populated
configured `Summary`/`Spot Check` cell in 18 additional non-summary pairs / 36
workbooks. It records 250 material denied cell instances: ENV 7 pairs / 14
workbooks / 104 instances, TSN 7 / 14 / 84, and SELF 4 / 8 / 62. The confirmed
PCOA-CX-014 scope therefore expands from 23 pairs / 46 workbooks to **41 pairs /
82 workbooks**.

The failures are stored workbook facts, not an alternate renderer's guess:

- `Spot Check!B6` is about 72 px too narrow in every reviewed schema. It has
  neither wrap nor shrink-to-fit, and populated `C6` blocks normal Excel text
  overflow.
- Longer PDF/self/Baseline variants also clip `Spot Check!B12` and/or `E12`
  by about 37–117 px.
- Direct/self Summary labels overrun their visible cells by about 43–179 px.
  Baseline one-sided labels overrun by about 360 px and route-only labels by
  about 100 px; populated/formula-bearing count cells block overflow.
- Composite keys are materially clipped on Highway Sequence and selected
  Intersection Detail, Ramp Detail, and Clean Road sheets where exact stored
  width is 12–36 px short.

Formula twins insert the red F9 row, so the primary direct/self Summary
failures shift from values `B13:B14` to formulas `B14:B15`; the defect itself
is unchanged. Native Excel directly confirmed the representative Summary and
Spot Check failures in both a direct Ramp Detail (PDF)-vs-TSN workbook and a
classic Ramp Detail (PDF) workbook.

The structural checks otherwise pass: all 32 open on Summary, no helper sheet
is visible, both snapshots remain very hidden, 16/16 values/formula pairs
match on sheet visibility, panes, widths, and merges, all 136 stored panes are
internally consistent, and no top-of-sheet Excel error token is displayed.
Those passes do not restore missing visible instructions and labels.

Impact:

The workbooks are not presentation-ready deliverables. Users cannot read
important audit instructions, status labels, and selected keys in the default
sheet view. Every affected values and formula twin is denied independently of
whether its arithmetic and installed-Excel formula gates pass.

Durable evidence:

- `source-audit/large-detail-no-render-visual-adjudication.json`
- `tmp/post_comparison_output_audit/source-audit/everything-v2-visual-parity-independent-validation.json`
- external `source-audit/everything-env-v2-visual-adjudication.json`
- external `source-audit/everything-tsn-v2-visual-adjudication.json`
- external `source-audit/everything-self-v2-visual-adjudication.json`
- `tmp/post_comparison_output_audit/visual-review/deliverable-sheets/SUBAGENT-VISUAL-AUDIT.md`
- `tmp/post_comparison_output_audit/visual-review/deliverable-sheets/package-visual-layout-audit.json`
- `tmp/post_comparison_output_audit/visual-review/excel-native/ramp-detail-pdf-summary-a1-d25.pdf`
- `tmp/post_comparison_output_audit/visual-review/excel-native/ramp-detail-pdf-spot-check-a1-d12.pdf`
- `tmp/post_comparison_output_audit/visual-review/excel-native/classic-ramp-detail-pdf-summary-a1-d25.pdf`
- `tmp/post_comparison_output_audit/visual-review/excel-native/classic-ramp-detail-pdf-spot-check-a1-d12.pdf`

### PCOA-CX-015 — P1 — Clean Road silently skipped live source rows become false or materially misrepresented discrepancies

Status: **CONFIRMED**

Affected deliverables:

- Clean Road Highway ArcGIS-vs-TSN values workbook
- Clean Road Highway ArcGIS-vs-TSN formula workbook

Observed behavior:

The independent raw-to-built audit proves that the public ArcGIS builder is
exactly rule-faithful across 57,728 built rows, 252 routes, 74 fields, and
4,271,872 cells. However, 102 current raw source rows marked
`LocError=NO ERROR` have usable AR measures but one missing PM endpoint. The
production no-guess contract silently omits those values at the affected
anchors.

An exact join from each visible ArcGIS row's `Key (helper)` token to the
Comparison sheet's hidden `__CMP_E2_KEY_V1_TOKEN` proves the deliverable impact
without inferring any missing span:

- 161 published `D` cells are exact false positives because the visible TSN
  value equals the current skipped ArcGIS raw value;
- four additional `D` cells are genuine differences but materially
  misrepresent the ArcGIS side as blank. At route 036 / TEH / 40.15 and
  40.352, TSN shows lanes/width `2/24`, the skipped current ArcGIS raw anchors
  show `1/12`, and the workbook displays ArcGIS as blank;
- the 165 affected `D` cells span 83 comparison rows and 87 source endpoints:
  81 left-lane cells, 82 left-travel-width cells, and one each for right
  outside-shoulder total and treated width; and
- 162 affected cells display ArcGIS blank and three display an older or
  alternate ArcGIS value.

The values workbook's Summary and Notes contain no disclosure of unlocatable
rows, missing PM endpoints, skipped raw/source rows, or `LocError`. Summary
instead defines red cells as ArcGIS-not-equal-to-TSN and `(blank)` as empty in
the system, causing the omissions to look authoritative.

Impact:

This is a release-blocking interpretation defect even though workbook
arithmetic and the source builder's stated rule are internally consistent.
The defensible count is **161 exact false positives plus four materially
misrepresented genuine differences**, not 165 false positives. Both values and
formula deliverables remain denied.

Durable evidence:

- `source-audit/CLEAN-ROAD-HIGHWAY-RAW-SOURCE-TRUTH-FINAL.md`
- `source-audit/clean-road-highway-raw-source-truth.json`
- `source-audit/CLEAN-ROAD-COMPARISON-UNLOCATABLE-IMPACT.md`
- `source-audit/clean-road-comparison-unlocatable-impact.json`

## Independently validated observations

These are not defects unless a later gate contradicts them.

### Classic cross-version all-field semantic screen

- Every differing cell in all nine deliverable values workbooks from the new
  dev-site SSOR-prod batch versus 7.9 was independently re-counted against its
  bound comparison payload.
- The screen covered 217,468 claimed discrepant cells: Ramp Summary 67,
  Highway Sequence Excel/PDF 1,931/1,904, Highway Log Excel/PDF
  89,811/88,238, Intersection Summary 16, Intersection Detail Excel/PDF
  17,563/17,562, and Ramp Detail PDF 376.
- Every workbook binding and per-field displayed claim passed, with zero
  malformed displays and zero case/spacing, punctuation, numeric-rendering,
  render-null, or equivalent-date candidates.
- The semantic screen itself is not a substitute for source or formula gates.
  Those gates were subsequently closed by the retained raw-source witnesses
  and `classic-cross-version-installed-excel-formula-audit.json`; the final
  visual gate then closed as a denial under PCOA-CX-014.
- Durable witness:
  `source-audit/classic-all-field-semantic-candidates.json`.

### Classic cross-version installed-Excel formula approval

- Installed Microsoft Excel fully recalculated disposable copies of all nine
  delivered classic cross-version formula/value pairs.
- All nine pairs passed. The formula twins contain 9,682,957 live formula
  cells, the values twins retain 1,654,097 intentional self-check formulas,
  and 39,607,355 data cells were compared.
- There are zero formula-text error tokens, zero cached Excel error values, and
  zero unexpected semantic mismatches after applying only the documented
  formula/value presentation alignments.
- This closes formula execution and cached-value parity for every delivered
  classic row. It does not override the separate statewide-summary clipping
  denials or the Ramp Detail missing-deliverable denial.
- Durable witness:
  `source-audit/classic-cross-version-installed-excel-formula-audit.json`.

### Direct detail all-field semantic screen

- Every differing cell in all seven available direct detail values workbooks
  was independently classified after validating the hash-bound payload and
  reproducing every per-field claim.
- The screen covered Highway Sequence Excel/PDF, Highway Log Excel/PDF, Ramp
  Detail PDF, and Intersection Detail Excel/PDF.
- It found 2,512 formatting-equivalence candidates in total. Every candidate
  is a Description cell already enumerated by PCOA-CX-008 or PCOA-CX-010.
- No other asserted field contains a case/spacing-only, punctuation-only,
  numeric-equivalent, render-null, or equivalent-date candidate, and there are
  no malformed discrepancy displays. Date fields were also reviewed directly
  against their report-specific encodings after the initial classifier pass.
- Durable witness:
  `source-audit/direct-all-field-semantic-candidates.json`.

### Baseline installed-Excel formula approval

- Installed Microsoft Excel fully recalculated disposable copies of all seven
  delivered Baseline formula/value pairs.
- All seven pass: 8,230,837 live formula cells, 1,455,991 intentional
  values-twin formulas, and 32,819,899 cells compared.
- There are zero formula-text errors, cached Excel errors, merge or sheet-state
  mismatches, or unexpected semantic differences. The 628 raw differences and
  seven Summary shape offsets are exactly the documented formula/value flavor
  prose and help-row presentation.
- This closes formula execution and cached-value parity for every delivered
  Baseline row. It does not override the statewide-summary or large/detail
  visual denials, and the two unavailable prior-SSOR Intersection Detail rows
  remain source-blocked.
- Durable witness:
  `source-audit/baseline-installed-excel-formula-audit.json`.

### Production By Day installed-Excel formula approval

- Installed Microsoft Excel fully recalculated disposable copies of all nine
  delivered production By Day vs TSN formula/value pairs.
- All nine pass: 11,368,483 live formula cells, 1,810,549 intentional
  values-twin formulas, and 42,813,659 data cells compared.
- There are zero formula-text or cached Excel errors, merge mismatches,
  sheet-state mismatches, stale source hashes, or unexpected semantic
  differences. The 962 raw cached-value differences and nine Summary shape
  offsets are exactly the documented formula/value flavor prose and F9-help-row
  presentation.
- This closes formula execution and cached-value parity for every delivered By
  Day row. It does not override the false provenance warning, semantic
  false-positive, evidence, or visual denials.
- Durable witness:
  `source-audit/by-day-tsn-installed-excel-formula-audit.json`.

### Clean Road installed-Excel formula approval

- Installed Microsoft Excel fully recalculated disposable copies of the one
  delivered Clean Road Highway formula/value pair.
- The pair passes: 6,442,773 live formula cells, 484,374 intentional
  values-twin formulas, and 24,768,177 cells compared.
- There are zero formula-text or cached Excel errors, merge or sheet-state
  mismatches, stale source hashes, or unexpected semantic differences. The 274
  raw differences are exactly 272 Summary and two Spot Check
  flavor-presentation cells; the one Summary shape offset is the expected
  live-formula help row.
- This closes formula execution and cached-value parity for Clean Road. It
  does not override PCOA-CX-012, PCOA-CX-014, or PCOA-CX-015, so both
  deliverable twins remain denied.
- Durable witness:
  `source-audit/clean-road-installed-excel-formula-audit.json`.

### Same-day self all-field semantic screen

- Every differing cell in the three delivered direct self values workbooks was
  screened with the same binding-aware classifier.
- Highway Sequence, Highway Log, and Intersection Detail produced zero
  case/spacing-only, punctuation-only, numeric-equivalent, or render-null
  candidates and zero malformed displays.
- This does not excuse Highway Sequence: its equation-representation defect is
  a substantive multi-field projection already proven by PCOA-CX-007.
- The result strengthens the Highway Log and Intersection Detail self-value
  approvals by finding no additional formatting-equivalence class.
- Durable witness:
  `source-audit/self-all-field-semantic-candidates.json`.

### Ramp Summary statewide counts

- All 126 raw Excel reports were independently read at fixed source cells.
- 3,780 category/total cells were checked.
- Zero route fields or comparison-side counts disagree with the raw source.
- Twenty-two ramps across nine routes are truthfully outside the explicitly
  classified Ramp Type buckets; the source totals, not the comparison engine,
  create that residual.
- The canonical TSN PDF was independently parsed into 31 categories.
- Independent discrepancy recount exactly matches the delivered values
  workbook: 29 paired, 2 TSN-only, 23 differing, 6 identical.

### Intersection Summary statewide counts

- All 217 raw Excel reports were independently read.
- 14,105 raw category cells plus route totals were checked.
- Zero route fields or comparison-side counts disagree with the raw source.
- Five records across routes 010S, 059, 068, and 395 are truthfully outside the
  explicit Highway Group buckets; all other section partitions are exact.
- The canonical TSN PDF was independently parsed into 58 normalized categories.
- Independent discrepancy recount exactly matches the delivered values
  workbook: 58 paired, 8 TSMIS-only, 53 differing, 5 identical.
- TSN control codes J, K, L, M, N, and P independently sum to 2,648 signalized
  intersections.
- The TSN PDF misprints the description for code F as “red on all.” Code F's
  canonical identity is red/mainline; the deliverable's declared correction is
  semantically justified.
- The export-only PDF sibling was independently parsed across all 217 routes.
  All 14,322 same-pull PDF/Excel category and total values are identical, and
  the PDF statewide sum exactly matches the integrated Excel-vs-TSN workbook.

### Ramp Detail source and normalization checks

- The direct PDF-vs-TSN values workbook independently recounts to 15,204
  paired rows, 9 TSMIS-only rows, 206 TSN-only rows, 468 differing matched
  rows, and 619 differing cells; all published masks, field totals, dedicated
  one-sided sheets, and hash-bound payload claims agree.
- All 15,410 normalized TSN rows match the raw statewide TSN XLSX
  field-for-field, including every Description.
- The 163 PDF-vs-TSN Description discrepancies are not normalization-created.
  Suspicious-looking examples such as `N FR GLENDALE BLVD` and `ECTOR RD`
  occur verbatim in the raw TSN workbook, while both fresh TSMIS render
  siblings carry `EB ON FR GLENDALE BLVD` and `COLLECTOR RD`.
- The fresh TSMIS PDF and Excel consolidations have the same 15,213 physical
  rows and zero semantic source differences after symmetric render-null
  handling. The current self adapter's asymmetric handling is separately
  denied under PCOA-CX-006.

### Highway Sequence cross-format count reconciliation

- Excel-vs-TSN independently recounts to 57,050 paired, 3,204 TSMIS-only,
  12,754 TSN-only, 4,883 differing matched rows, and 5,573 cells.
- PDF-vs-TSN independently recounts to 57,483 paired, 2,771 TSMIS-only,
  12,321 TSN-only, 4,892 differing matched rows, and 4,974 cells.
- A full FT/Description cross-tab classifies every FT cell, not a sample. All
  677 Excel `H`-vs-blank FT cells occur on a TSN `EQUATES TO` row. On the PDF
  leg, all 25 `H`-vs-blank cells have a TSN `EQUATES TO` Description and all
  45 blank-vs-`H`/`I` cells have a TSMIS Description beginning `EQUATES TO`.
  These 677 and 70 cells are the exact equation-representation class disclosed
  in the workbook Notes.
- Every one of the 13 remaining Excel FT differences was traced through its
  fresh route XLSX row, normalized TSN row, and original district TSN PDF line:
  eleven `H`-vs-`I`, one `H`-vs-`R`, and one `R`-vs-`H`. All source lines
  visibly print the claimed TSN FT. The PDF leg carries the same semantic set
  except route 211/HUM/073.661 moves into its equation representation, leaving
  12 non-equation FT cells there.
- The 433-row pairing delta and 599-cell total delta are supported by the raw
  export-format difference: TSN and TSMIS PDF both use printed equation lines,
  while TSMIS Excel folds those relations. The TSMIS sibling reports are
  semantically identical, but they are not literally identical before equation
  canonicalization.
- This explains the requested PDF/Excel-vs-TSN count mismatch; the misleading
  same-source classification of that known render difference is the separate
  defect PCOA-CX-007.
- Durable witnesses:
  `source-audit/highway-sequence-ft-description-cross-tab.json` and
  `source-audit/highway-sequence-ft-raw-source-trace.json`.

### Highway Sequence retained 7.9 sibling source approval

- The retained PDF contains 60,493 rows and Excel 60,494. After independently
  canonicalizing all 1,129 explicit equation relations with zero unsupported
  cases, 60,493 physical keys align and only four Description cells plus one
  Excel-only key remain.
- The four raw PDFs visibly leave Description blank at routes
  002/LA/014.348, 010/LA/014.820, 037/SON/003.981, and
  101/SBT/002.999, while the corresponding raw XLSX rows carry the four
  published descriptions.
- Route 010/LA/014.814 is present in the raw XLSX as an `FT=R` row with
  Description `010/EB ON FR VERMONT`; the raw PDF jumps from 014.812 to
  014.820 and contains no 014.814 row. Every residual is therefore real source
  divergence, not a PDF parser omission.
- Durable witnesses:
  `source-audit/highway-sequence-pdf-excel-equation-parity-prior-7.9.json`
  and
  `source-audit/highway-sequence-prior-sibling-residual-adjudication.json`.

### Intersection Detail direct arithmetic and source-trace result

- Both direct values deliverables independently recount to 16,199 paired rows,
  260 TSMIS-only rows, 427 TSN-only rows, 2,816 differing matched rows, and
  5,092 differing cells. Every published mask, field count, one-sided-sheet
  count, and hash-bound claim passes.
- An app-independent projection of all 16,626 TSN raw rows reproduces every
  cell in the rebuilt 38-column normalized workbook: 631,788 cells checked,
  zero differences, with exact headers and no source/normalized formula or
  error cells. The audit independently applies the documented date window,
  signal-control crosswalk, route/suffix split, postmile/numeric rules,
  whitespace handling, and district/county sidecars.
- The Excel-vs-TSN and PDF-vs-TSN deliverables have identical statewide and
  per-field counts, which is supported by the two fresh TSMIS consolidations.
- All four Description literals were traced by route/county/postmile through
  the fresh Excel consolidation, fresh PDF consolidation, rebuilt TSN
  normalized workbook, and raw TSN workbook. Each source contains exactly one
  matching row; the two TSMIS siblings agree, raw and normalized TSN agree, and
  the TSMIS-vs-TSN literal strings differ.
- That source trace does not make quotation style semantic data. One pair is
  `''F'' ST` versus `"F" ST`, so the delivered values and formula twins are
  denied under PCOA-CX-010 despite correct arithmetic and source binding.
- Durable normalization witness:
  `source-audit/intersection-detail-tsn-normalization-parity.json`.

### Intersection Detail retained 7.9 sibling source approval

- The retained ARS 7.9 PDF and Excel siblings each contain 16,459 rows. Every
  row pairs and neither source has a one-sided row.
- The 278 whitespace-only Description representations seen between those
  retained siblings are the exact same 278 signatures present in the fresh
  siblings; they are not prior-only parser omissions.
- Exactly one additional retained cell is source-real: route 108, post mile
  `005.870`, stores H/G `U` in the original `route_108.xlsx`, while page 12 of
  the original PDF visibly/textually stores `D` for
  `VIA ESTE=RNCHO POQUITOS`.
- That single source difference exactly explains why the classic Excel
  deliverable publishes 17,563 discrepant cells and the PDF deliverable
  publishes 17,562.
- Durable witness:
  `source-audit/prior-7.9-intersection-detail-pdf-excel-raw-source-truth.json`.

### Intersection Detail same-day sibling approval

- The direct PDF-vs-Excel values deliverable contains exactly 16,459 paired
  rows, zero one-sided rows, 16,459 identical rows, and zero differing cells
  across 559,606 asserted cells.
- Its generation metadata is trusted/current and its values and formula files
  are bound to the same generation ID.
- The direct self values arithmetic/source gate is approved, and evidence is
  correctly prohibited because one semantic side is Excel. The deliverable is
  nevertheless denied under PCOA-CX-014's material clipping. All three direct
  SELF formula twins have now passed installed-Excel data-only parity:
  4,494,021 live formula cells and 18,664,272 compared data cells, with zero
  formula-text or cached Excel errors.

### Direct-vs-TSN installed-Excel recalculation and cached parity

- Installed Microsoft Excel successfully recalculated disposable copies of all
  nine delivered direct formula/value pairs. Their live twins contain
  11,368,483 formula cells and their values twins retain 1,810,549 intentional
  Spot Check/SELF-CHECK formulas.
- The complete cached-value audit now passes 9/9 pairs and compares 42,813,677
  cells. All source hashes still match the frozen pair manifest. After
  filtering only the documented formula/values flavor prose and the one-row
  F9 presentation offset, every substantive Summary, Spot Check, and data
  sheet has zero unexpected mismatches.
- Across all nine twins there are zero formula-text errors, cached Excel
  errors, merge mismatches, sheet-state mismatches, or failed semantic-parity
  checks. The nine raw shape differences are exactly the expected live-formula
  Summary instruction row.
- Formula execution does not approve the deliverables: Ramp Summary and
  Intersection Summary are denied under PCOA-CX-013; detail rows remain denied
  under PCOA-CX-008/010 and/or PCOA-CX-014.
- A non-Excel render initially displayed two `CHECK` cells. This is not
  representative of the end-user workbook: the original formula caches are
  blank, the workbook declares `fullCalcOnLoad=True`, and installed Excel
  recalculates every SELF-CHECK result to `OK`.
- Durable witness:
  `source-audit/direct-installed-excel-formula-audit.json`.

### Highway Log same-day sibling approval

- The direct PDF-vs-Excel values deliverable independently recounts to 52,140
  paired rows, 667 PDF-only rows, 681 Excel-only rows, 1,363 differing matched
  rows, and 3,090 differing cells. All masks, field totals, side-only sheets,
  signed payload claims, and hashes pass.
- The 213-row route-140 block is real source divergence: the raw PDF visibly
  prints RU/TER/HG/AC and left-surface values while the raw Excel export leaves
  those cells blank.
- A route-005 one-sided example is also source-real: the raw PDF advances an
  otherwise identical payload to `R000.548`, while Excel retains the row at
  `000.243`. This correctly appears as one row on each one-sided sheet because
  Location is the identity key.
- At route 005 / `R025.780`, the raw sides genuinely differ in mileage,
  county odometer, city, RU, roadbed type, and record date. The PDF carries
  `000.096 / 025.376 / (blank) / R / H / 691030`; Excel carries
  `000.014 / 022.678 / SD / U / C / 660621`.
- Description contributes zero self discrepancies, so padding/punctuation does
  not create a same-source description false positive here.
- The direct self values arithmetic/source gate is approved, but both twins
  are denied under PCOA-CX-014's material clipping. Formula recalculation has
  passed its data-only parity audit. Final isolated Everything SELF typed
  parity reproduces the same result in both exposed Highway Log dispatch
  directions, and all four delivered SELF pairs are independently denied under
  PCOA-CX-014.

### Final installed-Excel formula-output approval

- The complete formula gate passes all 60/60 separately generated
  workflow/report pairs across Classic, Direct TSN, Direct SELF, Baseline, By
  Day TSN, Clean Road, and the final isolated Everything ENV, TSN, and SELF
  stores.
- It covers 79,809,913 live formula cells, 12,557,083 values-twin formula
  cells, and 313,497,190 compared cells. All 746 semantic checks pass.
- An additional terminal-subset recheck covers 39/39 Baseline, By Day, Clean
  Road, and final Everything pairs. Fresh SHA-256 plus byte-size verification
  binds all 156/156 source and recalculated workbook files, and all 485
  semantic checks pass.
- Formula-text errors, cached Excel errors, merge mismatches, sheet-state
  mismatches, sheet-name mismatches, and unexpected semantic mismatches are
  all zero.
- The 4,298 raw twin differences are exclusively expected flavor
  presentation: 4,236 Summary cells plus 62 Spot Check cells, with 39 expected
  live-formula Summary help-row shape offsets.
- Formula-output approval does not approve any report deliverable already
  denied for source truth, discrepancy semantics, visible clipping, or
  evidence behavior. Harness-only recovery history is not a product finding.
- Durable witnesses:
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-ALL-WORKFLOWS-AUDIT.md`,
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-ALL-WORKFLOWS-AUDIT.json`,
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-FINAL-AUDIT.md`
  and
  `tmp/post_comparison_output_audit/source-audit/INSTALLED-EXCEL-FINAL-AUDIT.json`.
  Independent rollup witness:
  `tmp/post_comparison_output_audit/source-audit/SUBAGENT-ALL-WORKFLOW-FORMULA-ROLLUP-VERIFICATION.md`.

## Items still under challenge

- The sequential Claude cross-check.

Classic source tracing/formula parity, direct and By Day discrepancy
adjudication, Clean Road formula parity, the complete By Day evidence review,
the non-summary large/detail visual decision, and final isolated Everything v2
arithmetic, post-generation, visual, 25-check typed parity, and installed-Excel
formula-output parity are complete.

## Handoff instructions for Claude

1. Independently challenge the closed Codex decisions. The master has no
   remaining Codex-controlled `UNVERIFIED` cells; a process ledger saying
   `ok` was never sufficient for approval.
2. Reproduce or dispute PCOA-CX-001, PCOA-CX-002, PCOA-CX-005,
   PCOA-CX-006, PCOA-CX-007, PCOA-CX-008, PCOA-CX-009, PCOA-CX-010,
   PCOA-CX-011, PCOA-CX-012, and PCOA-CX-015
   from raw headers/rows or full-resolution evidence; do not rely only on this
   narrative.
3. Reproduce or dispute PCOA-CX-003 and PCOA-CX-004 through the production By
   Day path, and PCOA-CX-013 and PCOA-CX-014 through native Excel visual
   inspection.
4. Sample discrepancy classes independently, with special attention to
   descriptions and normalized code fields.
5. Record any disagreement in `CLAUDE-FINDINGS.md` with the Codex finding ID.
6. Do not overwrite Codex results; final conflicts belong in
   `FINAL-RECONCILIATION.md`.
