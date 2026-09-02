# RB-6 — Adversarial Review Record

Status: **MERGED**

Current decision: **JOINTLY APPROVED AND MERGED**. Codex Review 1 and the
separate Codex Review 2 approved joint-review head
`ab09ce2249a4ac3350d9ffae406abdf8eacfa41c`; neither reviewer implemented the
Claude bundle. The prior evidence return `RB6-R1-EG-001` remains closed, every
criterion has exact bound evidence, and the independent Review 2 challenges
found no practical-impact failure. RB-6 merged without force as
`154e83b86d7b4f43429f05f6a71929f4d6c8e7c3`; both prescribed post-merge smoke
legs passed.

## Post-merge smoke and program closeout — 2026-09-02

| Closeout item | Result |
|---|---|
| Remote-main confirmation | PASS — a fresh fetch left `origin/main` at recorded base `62bb0f329c7d7deea6c5ee9010c3d21b0acf6325`; local `main` also named that base before integration |
| No-force merge | PASS — merge `154e83b86d7b4f43429f05f6a71929f4d6c8e7c3`; parents are unchanged remote-main base `62bb0f329c7d7deea6c5ee9010c3d21b0acf6325` and approved RB-6 head `ab09ce2249a4ac3350d9ffae406abdf8eacfa41c` |
| Full post-merge gate | **PASS — 175 passed, 0 failed of 175 in 161 seconds** via `python build/run_checks.py -j 4 -k` |
| Packaged application | **PASS — exact frozen executable reported `SMOKE OK` and exercised every app-required code path; 171 MB onefolder** via `build/build.ps1 -SelfTest` |
| Non-duplication | PASS — no statewide generation, installed-Excel recalculation, raw-source recount, comparison acceptance corpus, UI recapture or evidence rebuild was performed |
| Next bundle | **NONE — RB-1 through RB-6 are merged; the ordered implementation queue is complete** |

The merge smoke ran once on the integrated tree after both approvals. Build
outputs are ignored local artifacts and are not part of the merge. Preserve
all retained acceptance evidence and review records. After the closeout record
is pushed, only the fully merged RB-6 hotfix branch and its dedicated worktree
are eligible for Prompt 05's bounded cleanup.

## Review 2 — Codex — APPROVED

| Field | Reviewed identity |
|---|---|
| Reviewer / pass | Codex / Review 2, separate fresh task; independent non-implementer |
| Implementer | Claude |
| Branch / worktree | `hotfix/rb-6-hygiene-and-guards` / `C:/Users/Yunus/Projects/TSMIS-hotfix-rb-6` |
| Recorded base | `62bb0f329c7d7deea6c5ee9010c3d21b0acf6325` (`main` and `origin/main` on entry) |
| Last product/check runtime | `70b93ab8e92ee2eaced7d0dc864be6a94179cc0f` |
| Evidence-generation head | `a49c43eeaf278f922afc03f474dbea6920842d69` |
| Remedy head | `b790e1080d7fd463fe8997e93d7fc55c90965bdc` |
| Review entry / Review 1 record head | `4df2c72e7c23c1ba8b2c966782a09416058044ca` |
| New review-record commit | This documentation-only commit; resolve with `git log -1 --format=%H -- docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-6/REVIEW.md` |
| Counted active review | 2026-09-02T03:02:41.6382436Z to 2026-09-02T03:31:41.6382436Z — 29.00 minutes; sandbox/approval wait time excluded |
| Resource budget | RESPECTED — no process expected over five minutes, no operation over 500 MB new output, no Excel, GUI generation, statewide regeneration, full gate, raw recount, frozen build or new audit framework |
| Verdict | **APPROVED — REVIEW 2 COMPLETE; JOINTLY APPROVED** |

The dedicated checkout was clean at review entry. The complete recorded-base
to entry-head history is ten commits and 34 files, with 6,534 insertions and
105 deletions; the increase beyond Review 1's inspected 6,346 insertions is
review/evidence documentation. `git diff --check
62bb0f329c7d7deea6c5ee9010c3d21b0acf6325..4df2c72e7c23c1ba8b2c966782a09416058044ca`
passed. The merge base is the recorded base, and local `main` and
`origin/main` both resolved to it before the final remote-divergence check.
The full branch diff, every changed product/check file, the controlling scope
records, the implementation record, all prior review history and every witness
were independently inspected.

### Preconditions, reused evidence and Review 1 challenge

| Precondition | Review 2 result |
|---|---|
| Applicable pass | PASS — entry status was Review 1 approved and awaiting an independent Review 2 |
| Independence | PASS — Claude implemented; Codex performed both reviews in separate tasks, and this task challenged rather than copied Review 1 |
| Exact branch/base/runtime/review head | PASS — identities above matched Git and the committed bindings |
| Expensive acceptance evidence retained and bound | PASS — the full gate, double rebuild, comparisons, raw census, UI capture and discrepancy witnesses exist without reviewer regeneration |
| Prior return | PASS — `RB6-R1-EG-001` remains closed by the retained nine-dataset, two-twin post-rebuild witness |
| Merge eligibility | PASS — both signed reviews approve and at least one approver is not the implementer |

Review 2 explicitly challenged the following plausible Review 1 misses:

| What Review 1 could have missed | Bounded independent challenge | Result |
|---|---|---|
| The retained valid-run parity sample omitted the flat-PDF loader shape | Ran `python build/check_compare_env_pdf_completion.py`, which covers all five PDF converters, valid modes and failure completion | PASS |
| In-process double rebuilding could conceal a short-clock or process-local ZIP timestamp defect | Cross-matched the later remedy corpus against the earlier independent double-rebuild witness; all nine buildable workbook hashes, byte sizes, artifact tokens and normalization versions agree. Inspected all retained ZIP member timestamps and pinned core properties | PASS — one reviewer display rendered DOS local midnight as `08:00Z`; the packages are uniformly pinned, so this is a probe-expectation note, not a product failure |
| The supplemental cell walker pairs rows/cells and could miss a trailing structural-only change | Inspected the helper and attempted one read-only structural probe across the 36 retained twins. The optional probe produced no model-visible result and was not retried under the one-try rule. Exact raw/library bindings, typed results, per-field counts and all 36 hashes still reconcile | NOTE — no demonstrated output difference |
| Publication could leave an interrupted generation looking current | Ran `python build/check_comparison_publication.py`, including interrupted metadata and workbook-rewrite checks | PASS — interrupted state remains untrusted and workbooks are not silently rewritten |
| Stale, absent, unreadable or ambiguous TSN state could escape the identity fix | Ran `python build/check_tsn_freshness.py` across current/stale/missing/unreadable/ambiguous cases and matrix blocking | PASS |
| The HF-11 leading-`GENERATE` fixture is more specific for Highway Sequence than the other parser-backed families | Reconciled the committed guards with Review 1's retained real-PDF spot checks for all affected parser-backed families and the route-140 raw census | NOTE — future fixture specificity only; no current wrong, stale or lost report |

All committed witness files independently matched the hashes signed by Review 1:

| Witness | SHA-256 |
|---|---|
| `HF-07/witness/export_coverage.json` | `6f45e9a3800365d4384e0626423cfbd23016642be3807edc1f946bed55d219b2` |
| `HF-07/witness/missing_side_latency.json` | `3dd39415d472c13c05dcd46c5bdfff8264e012dbebf9f679fef166cdda448e4b` |
| `HF-07/witness/valid_run_parity.json` | `76bcc50ea493142f464dc473e8fe430a263af24c332f37f59ac2fcfa29947ce1` |
| `HF-08/witness/double_rebuild.json` | `29268d76e9dfeb7feaf76c4eceb9f896232174bf90c23690fd8030ea02fd478a` |
| `HF-08/witness/post_rebuild_vs_tsn.json` | `3ec88dda47acfa5643398cda55ff868fa5f613ff9bf4683ab1fd957f6b2e9911` |
| `HF-11/witness/pdf_only_rows.json` | `b623c9b360e0faea495a51d616ed635d160fa5e15117a428760f4b8eee8db021` |
| `HF-11/witness/route_140_raw_census.json` | `4863d94ee326ff14fe5aa92b813101af632814e19a8c3252853be45e015f8499` |

The retained-root copy of `post_rebuild_vs_tsn.json` has the same hash. Its
binding names remedy commit `b790e1080d7fd463fe8997e93d7fc55c90965bdc`,
runtime `70b93ab8e92ee2eaced7d0dc864be6a94179cc0f`, the exact TSMIS library,
per-dataset raw manifests, identities/tokens, comparison generations, output
paths/sizes/hashes, typed outcomes, counts and per-field counts. A separate
hash pass matched every one of the 36 retained comparison workbooks. The
retained full gate remains 175/175 in 128 seconds and was verified, not rerun.

### Exact deliverable and discrepancy results

The retained post-rebuild comparison witness reports all nine buildable
registered datasets complete and trusted in both VALUES and FORMULAS twins:

| Dataset | Paired | One-sided | Differing rows | Differing cells | Review 2 disposition |
|---|---:|---:|---:|---:|---|
| Highway Log | 48,351 | 15,265 | 39,623 | 140,643 | PASS — typed result and counts unchanged |
| Ramp Detail | 15,212 | 202 | 737 | 843 | PASS — typed result and counts unchanged |
| Ramp Summary | 29 | 2 | 24 | 24 | PASS — typed result and counts unchanged |
| Intersection Summary | 58 | 8 | 53 | 53 | PASS — typed result and counts unchanged |
| Intersection Detail | 16,199 | 687 | 2,816 | 5,092 | PASS — typed result and counts unchanged |
| Highway Sequence | 57,072 | 16,154 | 23,691 | 30,005 | PASS — typed result and counts unchanged |
| Highway Detail | 48,477 | 14,456 | 48,287 | 160,347 | PASS — typed result and counts unchanged |
| Highway Summary | 92 | 4 | 89 | 89 | PASS — typed result and counts unchanged |
| Clean Highway | 52,629 | 12,567 | 48,942 | 281,393 | PASS — typed result and counts unchanged; disclosed partial coverage preserved |

For every row above, pre-fix and post-rebuild results have identical
completion state, paired/one-sided totals, differing rows, total and per-field
differing cells, VALUES/FORMULAS parity and published trust state. The only
recorded pre/post workbook-cell change is the intended Provenance library
SHA-256 cell. `clean_intersection` and `clean_ramp` remain explicit typed
DEF-05 refusals because no normalizer exists; they are not omitted successes.

### Criterion-by-criterion acceptance

| Criterion | Review 2 result and basis |
|---|---|
| HF-07.1 missing-side under 5 s | PASS — bound real timings are 0.49/0.51 s; source inspection and the focused missing-side/PDF-completion tests prove refusal before expensive side-A loading |
| HF-07.2 valid counts/twins/outcome unchanged | PASS — retained three-family parity plus Review 2's all-PDF-converter completion challenge; VALUES and FORMULAS remain cell-identical in the valid samples |
| HF-07.3 export coverage/UI truth | PASS — the exact export-only set is `highway_summary_pdf`, `intersection_summary_pdf`, and `ramp_summary_excel`; catalog XOR, UI labels/tooltips and retained census agree |
| HF-07.4 gate/base failure | PASS — durable base RED and exact-head 175/175 GREEN evidence are bound; focused neighboring tests remain green |
| HF-08.1 root cause | PASS — source and package inspection confirm both clocks are fixed only at the shared opt-in TSN save boundary: core properties and ZIP member timestamps |
| HF-08.2 unchanged-raw double rebuild | PASS — all nine buildable datasets have byte-identical post1/post2 workbooks, identities and tokens; two unsupported builders refuse explicitly |
| HF-08.3 legitimate identity changes | PASS — retained negative controls move identity/token for changed normalized content and changed raw bytes |
| HF-08.4 content and vs-TSN result unchanged | PASS — `RB6-R1-EG-001` covers all nine buildable datasets, both twins, exact typed outcomes and the discrepancy table above |
| HF-08.5 one-time invalidation | PASS — measured and disclosed per buildable dataset; stale pre-fix bindings fail closed |
| HF-08.6 gate/base failure | PASS — exact-head focused determinism evidence and retained base RED/full-gate GREEN binding reconcile |
| HF-11.1 regression guards | PASS — source-universe and leading-`GENERATE` guard groups pass and deliberate regressions go RED; the future-specificity limitation is non-blocking |
| HF-11.2 no scripts behavior change | PASS — HF-11 changes checks and records only |
| HF-11.3 vendor record | PASS — VEN-01 names route 140, records the zero-difference delivery test and sends no raw source data |
| HF-11.4 counts unchanged | PASS — two PDF-only Highway Log rows and the route-140 raw census are retained; no product parser changed |
| HF-11.5 full gate | PASS — retained 175/175 exact-head gate plus bounded Review 2 neighboring challenges |

### Values/formulas, visual, evidence and regression matrices

| Surface | Independent Review 2 disposition |
|---|---|
| Values and formulas | PASS — all 36 retained twins match their bound hashes; every dataset retains the same typed outcome/counts and the sole pre/post cell class is the intended Provenance library identity |
| Visual and presentation | PASS — no workbook-presentation runtime changed. The only UI change truthfully labels and groups the three export-only editions; the retained 1400×900 capture/measurements and focused UI evidence are bound |
| Evidence integrity | PASS — Git heads, seven witness hashes, retained-root binding, raw manifests, library identities/tokens, comparison generations and 36 workbook paths/sizes/hashes reconcile |
| Failure and stale state | PASS — missing-side refusal precedes expensive loading; interrupted comparisons remain untrusted; stale, missing, unreadable and ambiguous TSN state fail closed |
| Regression and compatibility | PASS — normal non-TSN saves retain default behavior, legitimate TSN changes move identity, all PDF converter shapes complete, and source formats/counts are unchanged |
| Performance and resource safety | PASS — real missing-side timings are below one second; Review 2 reused all costly evidence and remained inside the 30-minute, 2 GB, five-minute and 500 MB limits |

Review 2 newly ran only these bounded existing checks, each once and each exit
0:

- `python build/check_compare_env_pdf_completion.py`
- `python build/check_tsn_freshness.py`
- `python build/check_comparison_publication.py`

It did not repeat Review 1's nine focused checks or the implementation's full
gate, double rebuild, statewide comparisons, raw census, UI capture or frozen
application build.

### Practical-impact gate and non-blocking notes

- The supplemental `eg001_celldiff.py` walker can miss a hypothetical trailing
  row/column-only structural difference because it pairs iterators. **What
  would a user see differently?** No demonstrated output difference: the same
  runtime produced both legs, all typed/per-field counts reconcile and all 36
  files are hash-bound. This is a helper-coverage NOTE.
- The Review 2 structural probe produced no model-visible result and was not
  retried. **What would a user see differently?** Nothing; this was an optional
  reviewer-environment probe, while retained product evidence remains valid.
- One timestamp display probe treated pinned MS-DOS local midnight as though it
  must render `00:00Z`; on this machine it rendered `08:00Z`. **What would a
  user see differently?** Nothing; every ZIP member shares the pinned timestamp
  and all nine independently rebuilt package hashes match.
- The leading-`GENERATE` guard fixture is less direct for three families than
  for Highway Sequence. **What would a user see differently?** Nothing in the
  reviewed output; real-PDF spots for the parser-backed families and the raw
  census pass. More specific fixtures are a future test-quality NOTE.
- The short `#ven-01` navigation link in `docs/vendor-escalations.md` is
  renderer-dependent because the visible heading is longer. **What would a
  user see differently?** At most a documentation jump may not scroll; the app
  and generated reports are unchanged. It is not a runtime denial.

There are no actionable acceptance failures and no unbound acceptance
artifacts. The prior evidence-gap denial is historical and closed; no second
denial is charged.

### Verdict, sign-off and merge authorization

**APPROVED.** Every RB-6 criterion has exact same-head evidence. Review 2
challenged the loader-shape gap, clock/process determinism, structural
false-pass possibility, atomic publication, stale-state handling and the
HF-11 fixture boundary without finding a contradiction that passes the
practical-impact gate.

Codex Review 1 and Codex Review 2 both approve, and neither implemented the
Claude bundle. Mark RB-6 **JOINTLY APPROVED**. Prompt 05's final-approval
sequence is authorized: confirm remote `main`, merge without force, run the
one planned post-merge smoke on the merged `main`, record the merge SHA, push,
and remove only the fully merged RB-6 branch/worktree. RB-6 is the final queued
bundle, so there is no later RB readiness record to prepare.

Signed: **Codex — independent non-implementing reviewer, Review 2**,
2026-09-02T03:31:41.6382436Z.

---

## Review 1 re-review — Codex — APPROVED

| Field | Reviewed identity |
|---|---|
| Reviewer / pass | Codex / Review 1 re-review, fresh task; independent non-implementer |
| Implementer | Claude |
| Branch / worktree | `hotfix/rb-6-hygiene-and-guards` / `C:/Users/Yunus/Projects/TSMIS-hotfix-rb-6` |
| Recorded base | `62bb0f329c7d7deea6c5ee9010c3d21b0acf6325` (`main` and `origin/main` on entry) |
| Last product/check runtime | `70b93ab8e92ee2eaced7d0dc864be6a94179cc0f` |
| Remedy evidence-generation head | `a49c43eeaf278f922afc03f474dbea6920842d69` |
| Review entry / remedy head | `b790e1080d7fd463fe8997e93d7fc55c90965bdc` |
| New review-record commit | This documentation-only commit; resolve with `git log -1 --format=%H -- docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-6/REVIEW.md` |
| Counted active review | 2026-09-02T02:18:36.6051446Z to 2026-09-02T02:47:36.6051446Z — 29.00 minutes; sandbox/approval wait time excluded |
| Verdict | **APPROVED — REVIEW 1 COMPLETE; AWAITING INDEPENDENT REVIEW 2** |

The dedicated checkout was clean at entry and immediately before this review
record was edited. The branch, base and remote-tracking identities matched the
implementation handoff. The complete base-to-entry branch diff was inspected:
34 files, 6,346 insertions and 105 deletions. `git diff --check
62bb0f329c7d7deea6c5ee9010c3d21b0acf6325..HEAD` passed. The remedy commit's
delta from the evidence-generation head is documentation plus the committed
HF-08 witness; there is no undisclosed post-generation product or check change.

### Re-review preconditions and closure of RB6-R1-EG-001

| Precondition | Result |
|---|---|
| Applicable pass and reviewer identity | PASS — the prior bounded return explicitly kept the next applicable pass at Review 1; Codex is not the Claude implementer |
| Controlling implementation status | PASS — authoritative records say implemented and awaiting adversarial review |
| Exact branch, base, runtime, entry head and committed witnesses | PASS |
| Every expensive acceptance operation retained and bound | PASS — the double rebuild, full gate, raw census, UI evidence and post-rebuild comparison leg are retained; none was regenerated by the reviewer |
| Prior bounded return | **CLOSED — all requested datasets, twins, counts, typed outcomes, paths, sizes, hashes and bindings are present** |
| Review 2 / merge eligibility | Review 2 is now eligible in a separate fresh task; merge is **not** yet eligible |

The new witness is
`hotfix-bundles/HF-08/witness/post_rebuild_vs_tsn.json`, SHA-256
`3ec88dda47acfa5643398cda55ff868fa5f613ff9bf4683ab1fd957f6b2e9911`.
It binds the generation head, last product/check runtime, exact TSMIS library
path/size/hash, per-dataset raw manifests, normalization versions, pre/post
library identities and artifact tokens, comparison generations, typed results,
output paths/sizes/hashes, counts, per-field counts, twin parity, published
trust state and errors. Its retained-root copy has the same hash. The retained
`_BINDING.txt` independently names the remedy commit, product runtime and
committed witness path.

A streaming reviewer hash pass covered all 36 retained comparison workbooks
(3,323,213,882 bytes) in 4.36 seconds. Every path existed and every SHA-256
matched the witness. A separate read-only consistency pass over the JSON
confirmed:

- 11 registered datasets: nine built and compared, with typed refusals retained
  for `clean_intersection` and `clean_ramp`, whose builders have no
  normalizer;
- exact pre/post typed status, completion state, paired/one-sided totals,
  differing-row counts, total/per-field differing-cell counts and VALUES /
  FORMULAS parity;
- exact pre/post1/post2 raw manifests, with post1 == post2 library SHA-256 and
  artifact token for every buildable dataset;
- both twins published from a trusted committed generation with no errors; and
- one pre/post cell difference per twin and dataset, consistently identified as
  the Provenance library-SHA cell. No report data, formula or presentation cell
  difference was reported.

The retained discrepancy result is:

| Dataset | Paired | One-sided | Differing rows | Differing cells | VALUES / FORMULAS post-rebuild result |
|---|---:|---:|---:|---:|---|
| Highway Log | 48,351 | 15,265 | 39,623 | 140,643 | PASS / PASS; counts unchanged |
| Ramp Detail | 15,212 | 202 | 737 | 843 | PASS / PASS; counts unchanged |
| Ramp Summary | 29 | 2 | 24 | 24 | PASS / PASS; counts unchanged |
| Intersection Summary | 58 | 8 | 53 | 53 | PASS / PASS; counts unchanged |
| Intersection Detail | 16,199 | 687 | 2,816 | 5,092 | PASS / PASS; counts unchanged |
| Highway Sequence | 57,072 | 16,154 | 23,691 | 30,005 | PASS / PASS; counts unchanged |
| Highway Detail | 48,477 | 14,456 | 48,287 | 160,347 | PASS / PASS; counts unchanged |
| Highway Summary | 92 | 4 | 89 | 89 | PASS / PASS; counts unchanged |
| Clean Highway | 52,629 | 12,567 | 48,942 | 281,393 | PASS / PASS; counts unchanged |

### Evidence hashes and focused checks

All retained witness hashes matched their recorded identities:

| Witness | SHA-256 |
|---|---|
| `HF-07/witness/export_coverage.json` | `6f45e9a3800365d4384e0626423cfbd23016642be3807edc1f946bed55d219b2` |
| `HF-07/witness/missing_side_latency.json` | `3dd39415d472c13c05dcd46c5bdfff8264e012dbebf9f679fef166cdda448e4b` |
| `HF-07/witness/valid_run_parity.json` | `76bcc50ea493142f464dc473e8fe430a263af24c332f37f59ac2fcfa29947ce1` |
| `HF-08/witness/double_rebuild.json` | `29268d76e9dfeb7feaf76c4eceb9f896232174bf90c23690fd8030ea02fd478a` |
| `HF-08/witness/post_rebuild_vs_tsn.json` | `3ec88dda47acfa5643398cda55ff868fa5f613ff9bf4683ab1fd957f6b2e9911` |
| `HF-11/witness/pdf_only_rows.json` | `b623c9b360e0faea495a51d616ed635d160fa5e15117a428760f4b8eee8db021` |
| `HF-11/witness/route_140_raw_census.json` | `4863d94ee326ff14fe5aa92b813101af632814e19a8c3252853be45e015f8499` |

The following focused head checks were run once as the final bounded suite and
all exited 0:

- `python build/check_tsn_identity_determinism.py`
- `python build/check_compare_env_missing_side.py`
- `python build/check_report_wiring.py`
- `python build/check_site_change_regression_guards.py`
- `python build/check_artifact_store.py`
- `python build/check_consolidate_toctou.py`
- `python build/check_tsn_raw_source_contract.py`
- `python build/check_report_catalog.py`
- `python build/check_ui_contract.py`

The retained implementation full gate remains 175/175 in 128 seconds. It was
hash-/record-inspected, not rerun. The 2,809.1-second double rebuild, statewide
comparisons, raw census and UI capture were likewise not repeated.

### Criterion-by-criterion acceptance matrix

| Criterion | Result and independent disposition |
|---|---|
| HF-07.1 missing-side under 5 s | PASS — retained real timings are 0.49/0.51 s; focused checks show the absent second side refuses through its own loader before side A loads |
| HF-07.2 valid counts/twins/outcome unchanged | PASS — retained three-family real parity plus focused normal-run check; VALUES and FORMULAS are cell-identical |
| HF-07.3 export coverage/UI truth | PASS — exactly `highway_summary_pdf`, `intersection_summary_pdf` and `ramp_summary_excel` are export-only; catalog XOR, picker labels/tooltips and retained census agree |
| HF-07.4 gate/base failure | PASS — retained base RED and 175/175 head GREEN, with focused neighboring checks green |
| HF-08.1 root cause | PASS — both the document-property clock and ZIP-member clock are fixed at the shared opt-in TSN save boundary |
| HF-08.2 unchanged-raw double rebuild | PASS — all nine buildable datasets have byte-identical post1/post2 workbooks, identities and tokens; two unsupported builders refuse explicitly |
| HF-08.3 legitimate identity changes | PASS — changed normalized content and changed raw bytes move the required identity/token |
| HF-08.4 content and vs-TSN result unchanged | **PASS — RB6-R1-EG-001 closed** by the retained post-rebuild results above for every buildable dataset and both twins |
| HF-08.5 one-time invalidation | PASS — measured per buildable dataset and disclosed; stale pre-fix bindings fail closed |
| HF-08.6 gate/base failure | PASS — focused determinism check green; retained base RED/full-gate GREEN binding inspected |
| HF-11.1 regression guards | PASS — source-universe and leading-`GENERATE` guard groups pass; deliberate regression records go RED; coverage limitation remains a note below |
| HF-11.2 no scripts behavior change | PASS — the HF-11 delta changes checks and records only |
| HF-11.3 vendor record | PASS — names route 140, records the zero-difference delivery test and sends no raw source data |
| HF-11.4 counts unchanged | PASS — witnesses retain the two PDF-only Highway Log rows and route-140 census; no product parser changed |
| HF-11.5 full gate | PASS — retained 175/175 plus focused neighboring checks |

| Surface | Re-review result |
|---|---|
| Values / formulas | PASS — all nine post-rebuild comparisons retain both twins, unchanged typed outcomes/counts and trusted publication; the only recorded pre/post cell change is the disclosed provenance identity |
| Visual / presentation | PASS — no workbook-presentation runtime changed; export-picker grouping/labels/tooltip retain the accepted 1400×900 measurement and focused UI contract |
| Evidence integrity | PASS — committed hashes, retained-root hashes, Git identities, raw manifests, library identities/tokens, comparison generations and 36 workbook hashes reconcile |
| Failure / stale state | PASS — missing-side work refuses before the expensive first-side load; pre-fix TSN bindings fail closed rather than being silently accepted |
| Regression / compatibility | PASS — non-TSN save behavior remains default, legitimate TSN changes still move identity, source formats/counts are unchanged |
| Performance / resource safety | PASS — no expensive acceptance operation was repeated; longest final focused process was under 10 seconds and no reviewer output approached 500 MB or 2 GB RAM |

### Adversarial notes that do not block

Each candidate was tested against Prompt 05's practical-impact gate:

- `BUNDLE.md` retains historical READY/eight-dataset wording while its own
  qualification and the authoritative plan/implementation records carry the
  corrected state and 11-dataset registry. **What the user sees:** no
  application output or failure; this is record wording only.
- The leading-`GENERATE` fixture directly exercises Highway Sequence, while
  the loop for the three affected parser-backed families chiefly proves parser
  presence. The prior real-PDF spots for all three families parse cleanly and
  emit no `GENERATE` data. **What the user sees:** no current wrong, stale or
  lost report; this is weaker future-regression specificity.
- The retained remedy's supplemental cell-diff helper uses paired row/cell
  iteration and could miss a hypothetical trailing-column-only structural
  difference. This does not contradict the accepted result: pre/post
  comparisons use the same product runtime and exact raw/library cell content,
  typed outcomes and all per-field counts reconcile, and all 36 published
  hashes are retained. **What the user sees:** no demonstrated output
  difference, crash or silent failure; preserve this limitation for Review 2.
- One optional reviewer structural probe exited before producing a result and
  was not retried under the one-try rule. The independent JSON consistency and
  streaming file-hash probes passed. **What the user sees:** nothing; no product
  process or acceptance artifact failed.

None meets the permitted blocking threshold of wrong/stale/lost output, crash
or silent failure. There is no second denial.

### Commands, resources, verdict and handoff

Reviewer work was limited to Git identity/diff inspection, complete source and
record diff review, retained witness/hash inspection, one streaming 36-file
hash pass, one JSON consistency pass and the nine focused checks listed above.
No Excel, network, browser, statewide generation, double rebuild, full gate,
frozen build, raw census, UI capture or new audit framework was started. New
output is only this review record.

**APPROVED.** This is the first approving reviewer. Update the workflow to
**REVIEW 1 APPROVED — AWAITING REVIEW 2** and invoke Prompt 05 again in a
separate fresh task with a different reviewer. Review 2 must independently
challenge this approval. Do not merge before Review 2 also approves.

No merge, push, branch deletion, worktree removal, evidence cleanup, release or
product-code edit was performed. Preserve `main`, the branch, retained sources
and all existing evidence.

Signed: **Codex — independent non-implementing reviewer, Review 1 re-review**,
2026-09-02T02:47:36.6051446Z.

---

## Prior Review 1 return — Codex — DENIED — EVIDENCE GAP

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
