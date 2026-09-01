# RB-6 — Adversarial Review Record

Status: **DENIED — RETURN TO IMPLEMENTATION**

Current decision: **Codex Review 1 is DENIED — EVIDENCE GAP**, solely
`RB6-R1-EG-001`. The implementation retained the HF-08 double-rebuild identity
and cell-content result, but not the contract-required post-rebuild vs-TSN
comparisons for each dataset, both twins, with unchanged counts. No runtime
defect is alleged by this return.

## Review 1 — Codex — DENIED — EVIDENCE GAP

| Field | Reviewed identity |
|---|---|
| Reviewer / pass | Codex / Review 1, fresh task; independent non-implementer |
| Implementer | Claude |
| Branch / worktree | `hotfix/rb-6-hygiene-and-guards` / `C:\Users\Yunus\Projects\TSMIS-hotfix-rb-6` |
| Recorded base | `62bb0f329c7d7deea6c5ee9010c3d21b0acf6325` (`main` and `origin/main` on entry) |
| Product/check/documentation runtime | `cb35bdeff2fde2de8feaf24adbaad45c5852f279` |
| Implementation-evidence head | `0b011efb63a4c2a5de3961529dcef0015b83f881` |
| Entry head | `92538904eac37e27b2c005d2a86114e56cd9945d`; its only delta from `0b011ef` is the implementation-record commit list |
| New review-record commit | This documentation-only commit; resolve with `git log -1 --format=%H -- docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-6/REVIEW.md` |
| Active review accounting | 2026-09-01T05:42:34.2706109Z to 2026-09-01T06:11:34.2706109Z — 29.00 minutes; substantive work stopped at the evidence gap |
| Verdict | **DENIED — EVIDENCE GAP; RETURN TO IMPLEMENTATION** |

The dedicated checkout was clean at entry and remained on the required branch.
There was no prior `RB-6/REVIEW.md`, so the applicable pass is Review 1. The
authoritative plan, `START-HERE.md`, and implementation record established
`IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`; `BUNDLE.md` still carried its
explicitly frozen READY wording and says the plan is authoritative. That stale
readiness label is a NOTE, not a second return.

### Preconditions and stopping point

| Precondition | Result |
|---|---|
| Review 1 status and reviewer identity | PASS — Codex is not the Claude implementer; controlling status was implemented/awaiting review |
| Exact branch, base, runtime, entry head and retained committed witnesses | PASS |
| Every expensive acceptance operation has a retained, bound result | **FAIL — `RB6-R1-EG-001` below** |
| Review 2 / merge eligibility | NOT REACHED — no approving Review 1 exists |

The gap was found while mapping HF-08 criterion 4 and its explicit
values/formulas acceptance path. Substantive work stopped there. Diff inspection,
focused checks and small source probes completed before the gap was recognized;
their observations are retained below but are not represented as a completed
approval.

### RB6-R1-EG-001 — retain the post-rebuild vs-TSN twin/count result

**Exactly one requested item:** the HF-08 acceptance result required by
`BUNDLE.md` under “Values / formulas and installed-Excel checks”: after the
second unchanged-raw deterministic rebuild, run one vs-TSN comparison for each
of the nine buildable registered datasets in `mode="both"`, and retain the
VALUES and FORMULAS outputs with unchanged counts. Retain the existing typed
refusal proof for `clean_intersection` and `clean_ramp`, which have no
normalizer, rather than inventing outputs for them.

The result must bind each case to the reviewed runtime, exact raw manifest,
normalization version, post-rebuild normalized-workbook identity and artifact
token, comparison generation, output paths, sizes and SHA-256 identities. It
must record typed outcome/status/completion, paired/one-sided totals,
differing-row and total/per-field differing-cell counts, VALUES/FORMULAS parity,
and workbook self-check/error state. Counts must be compared with the accepted
pre-fix or pre-change result so “unchanged” is measured rather than asserted.

If these outputs already exist, supply their exact location and binding and do
not regenerate them. Otherwise produce only this missing acceptance leg using
the implementation's existing staged inputs. No product-code change, new audit
framework, reviewer-run statewide rebuild, or unrelated acceptance repeat is
requested.

Evidence for the gap:

- `BUNDLE.md` explicitly requires “one vs-TSN comparison per dataset
  regenerated after the double rebuild, both twins, counts unchanged.”
- `HF-08/witness/double_rebuild.json` contains 11 dataset entries (nine built,
  two documented refusals) and criteria 2–5 for normalized bytes, identity,
  token and cell-content invariance. It has no comparison generation, twin,
  typed-outcome or difference-count record.
- `RB-6/IMPLEMENTATION.md` documents the real double rebuild and states that a
  full re-comparison is expected after merge, but gives no post-rebuild vs-TSN
  result table, path, generation or hash.
- `HF-07/witness/valid_run_parity.json` covers three cross-environment
  comparisons for the missing-side change. It is not an HF-08 vs-TSN result and
  cannot establish that rebuilt library bindings survive in user outputs.
- The full offline gate and the hermetic determinism check validate code paths;
  neither substitutes for the contract's retained real-data twin/count leg.

**Practical-impact gate.** After a user chooses **Rebuild TSN library**, the
next user-visible operation is a vs-TSN comparison. The missing result is the
only acceptance leg proving that the new stable library identity binds to both
published workbook flavors without changing their counts or typed outcomes.
That is a material output/binding artifact, so Prompt 05 permits the bounded
evidence-gap return. This is not a complaint about wording, cosmetics, a commit
hash, or the disclosed one-time invalidation.

### Evidence inspected before the stop

The complete base-to-entry inventory is 32 files, 2,994 insertions and 101
deletions. All six branch commits and the product/check diff were inspected.
The only changes after `cb35bde` are planning/implementation records and
committed witnesses; the only change after `0b011ef` is one implementation
commit-list line. `git diff --check` passed and the checkout was clean before
review finalization.

The following committed witnesses were independently SHA-256 hashed:

| Witness | SHA-256 |
|---|---|
| `HF-07/witness/export_coverage.json` | `6f45e9a3800365d4384e0626423cfbd23016642be3807edc1f946bed55d219b2` |
| `HF-07/witness/missing_side_latency.json` | `3dd39415d472c13c05dcd46c5bdfff8264e012dbebf9f679fef166cdda448e4b` |
| `HF-07/witness/valid_run_parity.json` | `76bcc50ea493142f464dc473e8fe430a263af24c332f37f59ac2fcfa29947ce1` |
| `HF-08/witness/double_rebuild.json` | `29268d76e9dfeb7feaf76c4eceb9f896232174bf90c23690fd8030ea02fd478a` |
| `HF-11/witness/pdf_only_rows.json` | `b623c9b360e0faea495a51d616ed635d160fa5e15117a428760f4b8eee8db021` |
| `HF-11/witness/route_140_raw_census.json` | `4863d94ee326ff14fe5aa92b813101af632814e19a8c3252853be45e015f8499` |

Focused head checks run once with the available project Python all passed:
`check_tsn_identity_determinism`, `check_compare_env_missing_side`,
`check_report_wiring`, `check_site_change_regression_guards`,
`check_artifact_store`, `check_consolidate_toctou`,
`check_tsn_raw_source_contract`, `check_report_catalog`, and
`check_ui_contract`. The implementation's full gate (175/175 in 128 seconds)
and lint result were verified from its retained record, not rerun.

The HF-08 root cause was independently confirmed in installed openpyxl/stdlib
source: `save_workbook` overwrites `properties.modified`, while
`ZipFile.writestr` seeds new members from wall time and funnels writes through
`open`. The opt-in save fixes both clocks at the shared boundary; all non-TSN
callers retain the default path. The focused check confirmed all 11 registered
datasets reach the stable writer or an explicit refusal, unchanged raw/content
moves identity when it should, and the default save remains time-varying.

The export-only set was independently re-derived as exactly
`highway_summary_pdf`, `intersection_summary_pdf`, and `ramp_summary_excel`;
the enabled-entry XOR invariant was true. Real raw-source spots reproduced the
two one-sided Highway Log rows: route 074 `000.000` is 2 PDF / 1 Excel, and
route 101 `R022.828` is 1 PDF / 0 Excel. Route 140 on 2026-07-23 is 214 PDF rows
with all four fields populated versus 213 Excel rows with all four fields blank.

### Acceptance and result matrices

| Criterion | Evidence / disposition |
|---|---|
| HF-07.1 missing-side under 5 s | Retained real measurements 0.49/0.51 s and focused all-adapter no-load check pass; pre-fix 439.9 s independently binds the mechanism. Not finally approved because review stops on HF-08 precondition. |
| HF-07.2 valid counts/twins/outcome unchanged | Three real family classes retain cell-identical VALUES and FORMULAS twins; focused valid comparison passes. |
| HF-07.3 export coverage/UI truth | Catalog derivation, XOR gate, UI contract and retained 343/2,380 census agree. |
| HF-07.4 gate/base failure | Retained 175/175 and pre-fix RED claims inspected; focused head checks pass. |
| HF-08.1 root cause | Independently established as both document-property and ZIP-member clocks. |
| HF-08.2 double rebuild identity | Nine buildable real datasets have post1 == post2 bytes/identity/token; two unsupported builders refuse. |
| HF-08.3 legitimate identity changes | Hermetic changed-content and changed-raw cases move the token. |
| HF-08.4 content and vs-TSN counts unchanged | Cell-content digests are retained; **post-rebuild vs-TSN twins/counts are missing — `RB6-R1-EG-001`**. |
| HF-08.5 one-time invalidation | Measured for every buildable dataset and clearly disclosed; stale bindings fail closed. |
| HF-08.6 gate/base failure | Focused determinism check passes and retained full gate is green; no reviewer full-gate repeat. |
| HF-11.1 guards | Both new guard groups pass and recorded deliberate regressions go RED; the coverage note below remains. |
| HF-11.2 no scripts behavior change | PASS — HF-11 changes checks/docs only. |
| HF-11.3 vendor record | Record names route 140 and the zero-difference on-delivery test; raw spots match. |
| HF-11.4 counts unchanged | Source-universe guard and committed witnesses retain the two PDF-only rows; no product parser change. |
| HF-11.5 full gate | Retained 175/175 result; focused neighboring checks pass. |

| Surface | Review observation |
|---|---|
| Values / formulas | HF-07's three real parity cases include both twins. HF-08's required per-dataset post-rebuild twins/counts are absent. |
| Visual / presentation | No workbook presentation change. Export-picker grouping/label/tooltip is covered by the retained 1400×900 measurement and focused UI contract; no new screenshot was generated. |
| Evidence | No evidence-image producer changed. Witnesses are committed after the product runtime; the Git chain binds them despite not embedding every head SHA internally. |
| Failure / stale state | Missing-side paths fail before loading side A. The stable-identity path is opt-in and stale pre-fix bindings are disclosed/refused rather than silently treated current. |
| Performance | No statewide work was repeated. Targeted real PDF/source probes completed below one minute each; retained missing-side timing shows the intended latency removal. |

### Notes that do not block

- The leading-`GENERATE` fixture exercises Highway Sequence, not the three
  parser-backed families named by PCOA-FINAL-022. The family loop only asserts
  that a parser exists. This is weaker future-regression coverage. It does not
  establish a current product failure: one real current PDF from each of
  `ramp_summary`, `ramp_detail_pdf`, and `intersection_detail_pdf` begins with
  `GENERATE`, parses cleanly, emits no `GENERATE` value, and reports zero parser
  anomalies where the parser supplies statistics. Preserve this as a Review 1
  note for the next pass; it is not a second return under the practical gate.
- `BUNDLE.md` retains historical READY and eight-dataset wording while its own
  current-main qualification and the authoritative plan/implementation record
  correct the state/count to implemented and 11. These documentation deltas do
  not change application behavior.
- The checkout has no recorded `build\.venv`; two initial launches failed before
  tests began. The same focused checks then passed with the available Python
  3.11 environment. One catalog expression used a nonexistent attribute and one
  raw-source probe used the old vendor labels; each was corrected once. These
  are reviewer-environment/probe issues, not product failures.
- No request is made to rerun the 2,809.1-second double rebuild, the full gate,
  UI capture, or raw census. The implementation's measured double rebuild plus
  full gate already totals at least 2,937.1 seconds (48.95 minutes), longer than
  this bounded review.

### Commands, resources, decision and handoff

New work was limited to Git/diff/file inspection, witness hashing, nine focused
checks, installed-library source inspection, catalog derivation, three small
current-PDF parser probes, and six named Highway Log raw-file spots. No Excel,
network, browser, full rebuild, statewide generation, full gate, frozen build,
whole-corpus recount, or new audit framework was started. No operation was
expected to exceed five minutes; the longest reviewer process was the corrected
raw-source probe at about 51 seconds. New output is this small documentation
record only, far below 500 MB; no process approached the 2 GB ceiling.

**DENIED — EVIDENCE GAP**, solely **RB6-R1-EG-001**. This is denial 1 of the
maximum 2 for RB-6 and is not a demonstrated runtime defect. Return the same
RB-6 branch to implementation for the one retained post-rebuild vs-TSN
twin/count acceptance item. Once supplied, the next applicable pass remains
**Review 1**. Review 2 must still be a separate fresh task that challenges an
eventual approving Review 1.

No merge, push, branch deletion, worktree removal, evidence cleanup, release or
product-code edit was performed. Preserve `main`, the branch, retained sources
and all existing evidence.

Signed: **Codex — independent non-implementing reviewer, Review 1**,
2026-09-01T06:11:34.2706109Z.
