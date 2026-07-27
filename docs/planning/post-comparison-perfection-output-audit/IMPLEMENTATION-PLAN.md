# Comparison Deliverable Hotfix Implementation Plan

> Workflow artifact: **Stage 3 — jointly agreed hotfix plan**
>
> Status: **AWAITING SECOND PLANNER**
>
> Authority: Once signed by both planners, this file controls bundle order,
> scope, ownership, branch lifecycle, and acceptance gates. Until then it is a
> draft and **no code change is authorized**.
>
> New-chat entry point: [START-HERE.md](START-HERE.md). Create/challenge the plan
> with
> [Prompt 03 — agree implementation plan](prompts/PROMPT-03-AGREE-IMPLEMENTATION-PLAN.md).

## Stage 3 sign-off

| Planner | Pass | Decision | Commit | Date | Notes |
|---|---|---|---|---|---|
| Claude | **First plan** | **DRAFTED — AWAITING SECOND PLANNER** | this commit | 2026-07-26 | Built the verified overlap map from code inspection; 11 bundles; every canonical finding mapped once |
| Codex | **Final challenge** | NOT STARTED | PENDING | PENDING | |

**Planner-order note.** The template assigns Codex the first plan and Claude the
challenge. Both rows read `NOT STARTED` when Prompt 03 was invoked in a Claude
chat, so under the prompt's own rule ("The first agent drafts and marks the plan
`AWAITING SECOND PLANNER`") Claude is the first planner. The labels above record
the real order — the same reversal Stage 2 documented.

## Precondition verification

| Precondition | Result | Evidence |
|---|---|---|
| Stage 2 documents jointly approved | **PASS** | `FINAL-RECONCILIATION.md` and `FINAL-FINDINGS-FOR-IMPLEMENTATION.md` both read `JOINTLY APPROVED`; both carry two signed reviewer rows |
| Canonical findings committed on clean, current `main` | **PASS** | `main` @ `a29bdb6`, working tree clean, `origin/main` identical (no divergence) |
| No hotfix bundle has begun | **PASS** | Branches are exactly `main`, `gh-pages` (+ their remotes); no `hotfix/*` branch, no `hotfix-bundles/<ID>/` directory beyond `README.md` and `TEMPLATE/` |
| Stage 3 branch is documentation-only | **PASS** | `planning/post-comparison-hotfix-bundles` off `a29bdb6`; this commit touches only `docs/planning/post-comparison-perfection-output-audit/**` |

Canonical finding count carried into planning: **22 records — 20 actionable
(9 P1 / 9 P2 / 2 P3) + 2 no-fix**. 19 need product code; three (PCOA-FINAL-020,
-021, -022) are a vendor escalation and two regression guards.

## Planning rules

- Clean Road is the first implementation bundle because it is the user's
  immediate operational need.
- Prefer one report family per bundle when files and regression risks are
  separable. Use a shared-subsystem bundle only when splitting would duplicate
  changes in the same function or create unsafe intermediate states.
- Every canonical finding maps to exactly one **primary** bundle. A finding may
  appear in other bundles only as *regression surface* — never as a second
  implementation scope.
- **Roles are fixed for the whole program (owner decision, 2026-07-26): Claude
  implements every bundle; Codex performs both adversarial reviews on every
  bundle.** Claude never approves its own work.
- Every bundle starts from the then-current `main`, uses its own
  `hotfix/<bundle-id>-<slug>` branch and worktree, and merges to `main` only
  after two adversarial reviews approve it with at least one non-implementer
  approver.
- A later bundle never branches from an unmerged earlier bundle.
- Every bundle leaves `main` usable and releasable: no bundle may land a
  half-migrated schema, a comparator that refuses a previously accepted input,
  or a workbook a shipped consumer cannot read.
- `main` and `gh-pages` are persistent. Completed hotfix and temporary planning
  branches are deleted only after their commits are confirmed on `main`.
- Audit evidence is immutable. Implementation and review artifacts live under
  `hotfix-bundles/<bundle-id>/`.
- **Statuses move together.** A status change updates the queue table, the
  finding-coverage table, and that bundle's record in the same commit. Index
  tables drifting behind entries caused repeated stale-directive incidents in
  the predecessor project.
- **The full gate, never a subset.** Every bundle runs
  `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k` plus
  `compileall`, `ruff`, and `build.ps1 -SelfTest` before review. A subset run
  shipped a field crash in v0.17.3.
- **Test the shipped path.** Each bundle's acceptance is driven through the
  end-user entry point named in its section and asserts the produced **file**,
  not a log line or an internal helper's return value.

## Verified finding → file / subsystem overlap map

Built by direct inspection of `main` @ `a29bdb6` (not copied from the findings'
ownership hints — every row below was opened and read; line numbers are from
this commit and are anchors, not contracts).

| Findings | Owning code, verified | Report families | Coupling / ordering constraint | Planner conclusion |
|---|---|---|---|---|
| **010** | `consolidate_clean_highway._read_span_layer` — the silent skip is `scripts/consolidate_clean_highway.py:182-184` (`b, e = crl.pm_units(...)` then `if b is None or e is None: continue`), which never reaches the `warnings` list that `_split_parked:323-328` already uses; `_write_workbook(..., warnings)` at `:974`, `completion=PARTIAL if warnings` + `skipped_inputs` at `:984-985`, sidecar `clean_road_build.warnings` at `:988-994`; disclosure surface `compare_clean_highway_tsn._write_notes_sheet:105-156` and `_SCHEMA:158-181` | Clean Road Highway only | None inbound. A per-cell non-asserting display may need one opt-in `CompareSchema` hook (precedent: the per-cell ditto `N` at `compare_core.py:1648-1650`) | **Own bundle, first.** The builder already has a skip-disclosure channel; extending it is family-local. Clean Road is also the only family whose defect is source truth rather than presentation |
| **008, 009, 014, 019** | One shared writer, four sites: `compare_core._write_comparison:2155` (category/key column `c_loc` width **12** at `:2170` = the measured 89 px), `_write_data_sheet:1994` (`key_col` 14 at `:2015`, `back_col` 13 at `:2016`), `_write_spot_check:2292` (`B` **19** at `:2346-2348` = `Spot Check!B6`), `_write_summary:2978` (`B` **46** at `:2998`, the *DIFFERENCES BY FIELD* table at `:3182`, the `Summary!B3` headline); `summary_layout.py:634-635` for the by-category extra sheet | **All** families, both twins | 008 and 009 are inseparable: both need `_write_summary`'s `B` width and the composite key column. 014 and 019 are the *same sheet's* self-description with zero count effect | **One bundle — reject the prompt's statewide/detail split.** Splitting would put two bundles on the same three width statements and the same Summary sheet. Adding 014/019 costs nothing and closes the sheet in one review |
| **002, 003, 016** | One function: `matrix_build.captured_tsn_workbook:227` — `tempfile.mkdtemp(prefix="tsmis-tsn-consumer-")` at `:237` (016), the reduced sidecar it publishes (002), and the captured path that reaches `compare_tsn_common.capture_input_provenance:604` → `"selection": str(path.resolve(...))` at `:625` (003). Used at `matrix_build.py:1045` and `:1191`; re-exported by `matrix.py:52`. The four `claims_notes` fallbacks (`compare_highway_log.py:228`, `compare_highway_sequence_tsn.py:346`, `compare_intersection_summary_tsn.py:290`, `compare_ramp_summary_tsn.py:150`) need **no change** if the sidecar is complete | All vs-TSN families, By Day + Everything lanes | None inbound | **One bundle.** All three are the same capture step; 003's scope (36 workbooks) is strictly wider than 002's (24), and fixing 002 alone leaves 003 standing — the finding says so explicitly |
| **001, 012** | `compare_ramp_detail_tsn._TSMIS_HEADER` + the misdiagnosing `bad_header_msg` in `_load_tsmis`; `compare_env._ramp_detail_canonical_header` (+ `_ramp_detail_env_keys:1294`); the unconditional success in `consolidate_ramp_detail.consolidate`; the self leg's asymmetry in `compare_ramp_detail_pdf.py` — `_NULL_DESC`/`_NULL_MARK:52-53`, `_null_blank:76` applied on the PDF path but not by `_load_excel_collapsed:155` | Ramp Detail, both editions | **012 is hard-coupled to 001**: it is unobservable until the header gate is fixed and the finding states "fixing 001 without this creates a new defect" | **One bundle.** Shipping 001 alone would publish 108 known-false discrepancies on a same-source check |
| **004, 005, 006** | `visual_evidence.generate:547` (roles at `:580-581`, PDF-set gates at `:599-603`), `tsmis_source_role:173`, `_TSN_PDFS_IN_RAW:118`, the two flavors at `:159-161`, the Excel panel at `_excel_strip:1238` → `label[:24]` `:1266` and `text[:26]` `:1270`; per-family targeting in `evidence_highway_log.py` / `evidence_highway_sequence.py` / `evidence_intersection_detail.py` / `evidence_ramp_detail.py`; call sites `matrix_build.run_evidence_only:1016`, `evidence_for_cell:1113` (`generate` at `:1096`… `:1284`), `_run_self_evidence:1304` (`:1327`), plus `day_matrix.py:454`, `gui_matrix.py:711/789/946/1510/1576`, `gui_api.py:372` | HL, HSL, ID (both), RD-PDF | 006's symptom may be retired by 004's gate; the finding forbids assuming either fixes the other. **Blocks HF-10** | **One bundle.** Eligibility, binding and panel fidelity are one renderer contract and one review of the same image sets. Carries an **owner policy gate** (see below) |
| **011** | `compare_highway_sequence_pdf.py` — `_SS_SCHEMA:156`, `_tsmis_row_same_source:118`, `_load_tsmis_same_source:147`, and `_NOTES_PDF_VS_EXCEL:78-107`, which *already* describes the equate class in prose while the totals stay unqualified | Highway Sequence self only | **Owner ruling 2026-07-26: normalize to zero.** Count-affecting (3,714 → 0) and pair-aware → the `compare_core` lock + Phase-3 gates apply, opt-in only | **Own bundle.** Family-local file, but equality/count semantics — it must not travel with presentation work, and it must not touch the HF-09 class the owner ruled stays flagged |
| **015, 018** | 015: `compare_env.EnvComparator.compare_folders:1033` — both sides' member lists already exist at `:1065-1066`, yet side A is loaded first at `:1139+` and emptiness is never checked. 018: `report_catalog.ExportEntry:88` has no export-only field, `MATRIX:381`, the picker derivation `:570-576`, `reports.py`, `scripts/ui/`, and `build/check_report_wiring.py` (already derives required touchpoints) | 015: all statewide PDF families. 018: `ramp_summary_excel`, `intersection_summary_pdf`, `highway_summary` | 015 shares `compare_env.py` with 001 (different function) — sequence after HF-04 | **One bundle.** Both are "the app must tell the user the truth immediately / at all"; neither touches a workbook cell, a count, or an image. Two disjoint files, one review |
| **017** | `tsn_library.build_consolidated:909`, `_write_normalized_workbook:1152`, `normalized_workbook_identity:249`; `report_catalog.TSN` `normalization_version` (D2 auto-rebuild) | All 8 TSN datasets | Root cause is an explicit hypothesis — Stage 4 must establish it first | **Own bundle.** Invalidates every bound comparison generation, so its blast radius is the whole vs-TSN surface and it needs its own review |
| **013** | Per-family classification + Summary/Notes disclosure across `compare_highway_log.py`, `compare_highway_sequence_tsn.py`, `compare_intersection_detail_tsn.py`, `compare_ramp_detail_pdf.py`, `compare_clean_highway_tsn.py`, likely one shared opt-in `CompareSchema` field and `compare_core._write_summary` | HL, HSL, ID (both), RD-PDF, Clean Road | Touches `_write_summary` (HF-02) and Clean Road Notes (HF-01) — must follow both. **Owner ruling 2026-07-26: disclosure only, the cells stay flagged** | **Own bundle, late.** Five families' Summary/Notes disclosure; mixing it into a presentation bundle is exactly what the prompt forbids. Now the lowest-risk semantics bundle — no count moves |
| **007** | `matrix_build.build_cell_comparison:561` takes no evidence argument (verified); a third evidence flavor is needed beside `FLAVOR_TSN`/`FLAVOR_SELF` (`visual_evidence.py:159-161`), plus `matrix_state`/`gui_matrix` toggle+camera plumbing | Ramp Summary, RD-PDF, ID-PDF, HL-PDF, HSL-PDF — Everything ENV | **Depends on HF-05**: the new capability must satisfy 004's exact-source test and 005's targeting assertion at birth | **Own bundle, last of the code work.** It is a new capability, not a repair; building it before the renderer contract is fixed would ship the same defects into a new lane |
| **020, 021, 022** | No product behavior change. 020 is a vendor escalation record; 021 and 022 are must-not-regress guards that exist only as audit prose today (HL PDF-only rows; HSL pre/post re-skin print layouts + the leading `GENERATE` line) | HL both editions; the four re-skinned print families | 021/022 guard parsers that HF-06 and HF-09 touch — land the guards last so they lock the final state | **Own bundle, closeout.** Turning two prose guards into executable checks is real work and deserves its own review |

### Same-file overlaps that remain, and why they are safe

| File | Bundles | Functions touched | Mitigation |
|---|---|---|---|
| `scripts/matrix_build.py` | HF-03, HF-05, HF-10 | `captured_tsn_workbook` / the evidence call sites / `build_cell_comparison` | Disjoint functions, merged in order; each bundle names its allowed functions and a reviewer rejects a diff outside them |
| `scripts/compare_env.py` | HF-04, HF-07 | RD canonical header / `compare_folders` preflight | Disjoint functions, HF-04 merges first |
| `scripts/compare_core.py` | HF-02, and *possibly* HF-01/HF-09 for one opt-in `CompareSchema` field | Width + Summary writers / an opt-in non-asserting hook | HF-02 lands first; HF-01's hook (if needed) is additive and gated by a schema field that only Clean Road sets |
| `scripts/visual_evidence.py` | HF-05, HF-10 | Eligibility + panels / a new flavor | HF-10 depends on HF-05 |
| `compare_clean_highway_tsn.py` Notes | HF-01, HF-09 | Skipped-row disclosure / representation class | Additive lines in the same notes tuple; HF-09 rebases onto merged HF-01 |

No other file is claimed by two bundles.

## Why these boundaries

The prompt's likely shape was adopted where the overlap map supported it and
changed in four places, each for a verified reason:

1. **Clean Road stays first** (rule, and the user's need). It is also the only
   bundle whose defect is source truth, so it shares no code with the
   presentation work.
2. **Presentation is one bundle, not two.** The suggested statewide-summary /
   large-detail split fails on inspection: both classes are produced by the same
   `compare_core` writers and both need `_write_summary`'s `B` width and the
   composite key column. Two branches would edit the same three statements.
3. **Presentation moves to second, ahead of the family semantics.** It is the
   highest-leverage change in the program — Stage 2 measured that stored column
   widths alone gate **38 of the 68 denials**, and the capture-step provenance
   another **18** — and it is the change that finishes making the Clean Road
   sheet the user asked for readable (PCOA-FINAL-009 covers Clean Road).
4. **Evidence splits into repair (HF-05) then capability (HF-10).** The audit
   found a broken renderer contract *and* a missing lane. Building the missing
   lane first would replicate the broken contract into it.

Ordering beyond that is: highest user-visible harm per unit of shared-code risk
first (Clean Road truth → presentation → provenance narration → the eight
missing Ramp Detail deliverables → the 1,778 prohibited images), then the
count-affecting semantics that need owner rulings and oracle discipline, then the
new capability, then the guards.

## Agreed bundle queue

| Order | Bundle ID | Name | Canonical finding IDs | Scope style | Depends on | Branch | Status |
|---:|---|---|---|---|---|---|---|
| 1 | **HF-01** | Clean Road skipped-source truth and disclosure | PCOA-FINAL-010 | Report family | None | `hotfix/hf-01-clean-road-source-truth` | BLOCKED |
| 2 | **HF-02** | Shared workbook presentation and self-description | PCOA-FINAL-008, -009, -014, -019 | Shared subsystem | None (HF-01 for the Clean Road witness) | `hotfix/hf-02-workbook-presentation` | BLOCKED |
| 3 | **HF-03** | vs-TSN capture identity, provenance and temp hygiene | PCOA-FINAL-002, -003, -016 | Shared subsystem | None | `hotfix/hf-03-tsn-capture-provenance` | BLOCKED |
| 4 | **HF-04** | Ramp Detail layout compatibility and same-source null parity | PCOA-FINAL-001, -012 | Report family | None | `hotfix/hf-04-ramp-detail-layout` | BLOCKED |
| 5 | **HF-05** | Evidence eligibility, source binding and panel fidelity | PCOA-FINAL-004, -005, -006 | Shared subsystem | None | `hotfix/hf-05-evidence-binding` | BLOCKED |
| 6 | **HF-06** | Highway Sequence self-check equation classification | PCOA-FINAL-011 | Report family (semantics) | HF-02 | `hotfix/hf-06-hsl-self-equation` | BLOCKED |
| 7 | **HF-07** | Missing-side fast fail and export coverage truth | PCOA-FINAL-015, -018 | Shared subsystem | HF-04 | `hotfix/hf-07-fastfail-coverage` | BLOCKED |
| 8 | **HF-08** | TSN normalization identity determinism | PCOA-FINAL-017 | Shared subsystem | HF-03 | `hotfix/hf-08-tsn-identity` | BLOCKED |
| 9 | **HF-09** | Representation-only difference classification | PCOA-FINAL-013 | Cross-family (semantics) | HF-01, HF-02, HF-06 | `hotfix/hf-09-representation-class` | BLOCKED |
| 10 | **HF-10** | Cross-environment PDF-vs-PDF evidence capability | PCOA-FINAL-007 | Shared subsystem (new capability) | HF-05 | `hotfix/hf-10-env-evidence` | BLOCKED |
| 11 | **HF-11** | Source-side escalation and must-not-regress guards | PCOA-FINAL-020, -021, -022 | Program closeout | HF-06, HF-09 | `hotfix/hf-11-source-guards` | BLOCKED |

Allowed statuses:

- `BLOCKED`
- `READY`
- `IMPLEMENTING`
- `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`
- `REVIEW 1 APPROVED — AWAITING REVIEW 2`
- `DENIED — RETURN TO IMPLEMENTATION`
- `JOINTLY APPROVED`
- `MERGED`

**Status transition rule.** On joint planner sign-off, **HF-01 becomes `READY`**
and every other bundle stays `BLOCKED`. A bundle becomes `READY` only when every
bundle in its `Depends on` column reads `MERGED`. This is what keeps
implementation to one branch at a time while the user's `main` checkout stays
usable.

## Proposed merge order

`HF-01 → HF-02 → HF-03 → HF-04 → HF-05 → HF-06 → HF-07 → HF-08 → HF-09 →
HF-10 → HF-11`

Queue order and merge order are identical by construction: each bundle branches
from the `main` produced by its predecessor's merge, so no rebase of an unmerged
hotfix is ever required. HF-03, HF-04 and HF-05 have no inbound dependency and
may be resequenced among themselves if the owner's priority changes, provided
HF-05 still precedes HF-10 and HF-04 still precedes HF-07.

## Finding coverage — every canonical finding exactly once

| Canonical finding ID | Sev | Primary bundle | Acceptance oracle (copied from `FINAL-FINDINGS-FOR-IMPLEMENTATION.md`) | Coverage check |
|---|---|---|---|---|
| PCOA-FINAL-001 | P1 | HF-04 | "(a) all 8 affected decisions produce both a values and a formulas workbook, **or** every affected path refuses with a message that names the actual gate and an action that can succeed; (b) the consolidator's completion status agrees with downstream consumability — a consolidation no comparator accepts must not report `ok`; (c) any accepted layout maps `OF`, `TY` and `Description` to the correct fields, proved on route 001 row 2 against the raw export." | MAPPED ONCE |
| PCOA-FINAL-002 | P1 | HF-03 | "After a successful `tsn_library.build_consolidated(force=True)`, regenerate all 18 By Day and all 18 Everything vs-TSN workbooks: **zero** occurrences of 'rebuild the TSN library'; and every family whose Direct-lane workbook prints a TSN identity line prints the **same** line on both matrix lanes. Assert on the workbook file, not on the log." | MAPPED ONCE |
| PCOA-FINAL-003 | P2 | HF-03 | "No `Provenance` sheet and no `.provenance.json` in any generated comparison names a path under `%TEMP%`; every recorded TSN input path exists and is readable after the run completes." | MAPPED ONCE |
| PCOA-FINAL-004 | P1 | HF-05 | "For every generated evidence set, each read-set member is the exact artifact its side was compared from (assert against the comparison's own provenance, not against file extension); and no evidence artifact of any kind — manifest included — is emitted for a pair failing that test. Re-run all 11 prohibited registry cells plus their By Day counterparts and assert zero artifacts." | MAPPED ONCE |
| PCOA-FINAL-005 | P1 | HF-05 | "For every rendered example whose compared value is blank on either side, the target rectangle must fall inside the row rectangle of the record named in the caption, and must not intersect any glyph belonging to another record or to a different field. Assert on the **whole** generated set, not a sample, specifically over the `EQUATES TO` and blank-Description populations… Apply the same targeting assertion to future eligible PDF-vs-PDF ENV evidence." | MAPPED ONCE |
| PCOA-FINAL-006 | P1 | HF-05 | "For every rendered example, the string drawn inside the target box equals the compared value recorded in that example's Summary row, or is visibly marked as elided. Assert programmatically over 100 % of rendered examples in both layouts." | MAPPED ONCE |
| PCOA-FINAL-007 | P2 | HF-10 | "With evidence enabled, each of the 5 cells produces a bound manifest, evidence workbook, image set, and a PDF-only read set that satisfies PCOA-FINAL-004's exact-source test. Every retained crop is accurate and readable; absence or relabelling the supported comparison as `N/A` does not pass." | MAPPED ONCE |
| PCOA-FINAL-008 | P1 | HF-02 | "In every generated summary workbook, each populated, non-wrapped, non-shrink `Summary` and `Comparison` label cell whose right neighbour is populated must fit its stored column width at Calibri 11 within 6 px — or be wrapped, or the column widened. Assert on the stored workbook, and confirm once by native-Excel render that no category label is ambiguous." | MAPPED ONCE |
| PCOA-FINAL-009 | P2 | HF-02 | "Same measurable rule as PCOA-FINAL-008, applied to `Summary`, `Spot Check` and the composite key column of every non-summary schema, in both twins." | MAPPED ONCE |
| PCOA-FINAL-010 | P1 | **HF-01** | "For each of the 102 skipped raw rows, the deliverable either (a) does not publish a difference where the raw ArcGIS value equals TSN, or (b) discloses in Summary/Notes that the ArcGIS side was skipped and why, with the affected count. Assert the 161 false positives fall to zero and the 4 misrepresented cells display the real ArcGIS value or an explicit 'skipped' marker. Re-bless `CRH-SW-E2` with a documented delta." | MAPPED ONCE |
| PCOA-FINAL-011 | P1 | HF-06 | "The same-day Highway Sequence PDF-vs-Excel self check on the frozen `2026-07-23` pull reports **zero** differing cells, **or** classifies the 1,119 equation relations as a disclosed representation class that is excluded from the differing-cell count and named in Summary and Notes. Prove on all 60,254 rows, not a sample." | MAPPED ONCE |
| PCOA-FINAL-012 | P2 | HF-04 | "With PCOA-FINAL-001 resolved, the same-day Ramp Detail PDF-vs-Excel self check on the frozen pull reports zero differing cells across all 15,213 rows." | MAPPED ONCE |
| PCOA-FINAL-013 | P2 | HF-09 | "Either (a) Summary and Notes disclose the representation-only class and its exact count separately from substantive differences, or (b) a separately approved normalization changes equality and the affected counts move by the exact proved deltas, with re-blessed canaries and cell-for-cell evidence. No undisclosed change to equality semantics is accepted." | MAPPED ONCE |
| PCOA-FINAL-014 | P2 | HF-02 | "In every comparison Summary, a wholly-context column is rendered distinguishably from a compared column with zero differences — e.g. `context` / `not compared` rather than `0`. Assert on Highway Sequence's `City`, `HG` and `Distance To Next Point`, and confirm Highway Log's ditto columns still report real counts." | MAPPED ONCE |
| PCOA-FINAL-015 | P2 | HF-07 | "With side B absent, every comparison path reports the missing side in under 5 seconds regardless of side A's size. Reproduce with the three witnessed configurations." | MAPPED ONCE |
| PCOA-FINAL-016 | P3 | HF-03 | "After N vs-TSN matrix runs including at least one cancellation and one failure, zero `tsmis-tsn-consumer-*` directories remain under `%TEMP%`." | MAPPED ONCE |
| PCOA-FINAL-017 | P2 | HF-08 | "Two consecutive `build_consolidated(report, force=True)` calls over unchanged raw produce byte-identical normalized workbooks and identical `tsn_normalized_workbook_identity` / `tsn_artifact_identity_token`, for all eight supported datasets." | MAPPED ONCE |
| PCOA-FINAL-018 | P2 | HF-07 | "Every export edition enabled in `report_catalog` either has a dispatchable comparison path, or is explicitly marked export-only in the catalog **and** surfaced as export-only in the UI. `check_report_wiring` fails naming any edition that satisfies neither." | MAPPED ONCE |
| PCOA-FINAL-019 | P3 | HF-02 | "Reading each values twin with `data_only=True` yields a non-empty `Summary!B3` matching the typed `ComparisonOutcome`, or the workbook's note discloses that the headline is live like the SELF-CHECK rows." | MAPPED ONCE |
| PCOA-FINAL-020 | P1 (source) | HF-11 | "None in this product. Track the vendor's corrected export; on delivery, the route 140 self check reports zero `X ≠ (blank)` differences on `R/U`, `TER`, `H/G`, `A/C`." | MAPPED ONCE |
| PCOA-FINAL-021 | NO FIX | HF-11 | "Continue retaining both source rows in the PDF-derived universe and do not synthesize them in the Excel-derived universe." | MAPPED ONCE |
| PCOA-FINAL-022 | NO FIX | HF-11 | "The Highway Sequence PDF parser produces correct row counts for both the pre- and post-re-skin print layouts, and the leading `GENERATE` line is ignored on all four affected print families." | MAPPED ONCE |

**Arithmetic:** 22 records, 22 primary assignments, 11 bundles, no finding
assigned twice and none unassigned.

## Secondary regression dependencies (verify, do not re-implement)

| Bundle | Findings it must not break, without owning them | Required evidence |
|---|---|---|
| HF-01 | 009 (Clean Road clipping — still open until HF-02), 013 (the 5 landmark cells stay literal) | The regenerated Clean Road pair shows unchanged landmark cells and unchanged clipping behaviour; the finding's numbers are quoted, not re-measured |
| HF-02 | 010 (Clean Road, merged), 013, 011, and every "validated clean" presentation contract in the Stage 2 clean list (`__CMP_E1_STATE_V1_*` hidden, `__CMP_E2_SNAPSHOT_A/B` veryHidden, autofilter stops before the mask columns, data widths 13.0, the 45.75 pt header row) | Re-run `build/check_compare_audit.py`, `check_compare_build_freshness.py`, `check_comparison_artifact_schema.py`; regenerate the merged HF-01 Clean Road pair and re-measure with `stage2-measure-clipping.py` |
| HF-03 | 016 within the same bundle; the Direct-lane control that already prints the real identity (must stay identical); 017 (bound generations must not be invalidated by the capture change) | The Direct-lane workbooks are byte-compared before/after; the 36-workbook classification in `stage2-tsn-provenance-scope.json` is re-derived and every cell flips to clean |
| HF-04 | 013's RD-PDF 2-cell class; 021/022's RD-PDF print conventions; the RD-PDF vs TSN comparison that currently works | The RD-PDF vs TSN counts are unchanged; the newly unblocked Excel-side comparisons are recounted from raw |
| HF-05 | 004/005/006 are all in-bundle; the two production paths that already refuse evidence correctly (classic Compare tab, PDF-vs-Excel by-day matrix) must still write none; CMP-AUD-210's Excel-side binding (`check_evidence_source_role.py`) | Every existing `check_evidence_*.py` and `check_visual_evidence.py` passes; the two correct paths are re-observed to emit nothing |
| HF-06 | The vs-TSN Highway Sequence equate disclosure that already exists in Notes; the `CORE-ID-78-XLSX-TSN`-style independent oracle discipline; 014 (merged) | The vs-TSN HSL counts are unchanged; the self-check delta is proved on all 60,254 rows by an app-free reader |
| HF-07 | 001/012 (merged) — the RD paths must still fail fast *and* correctly; every export edition's picker grouping | `check_report_wiring.py`, `check_report_catalog.py`, `check_a1_filenames.py`; the `#mock` GUI preview for the export-only labelling |
| HF-08 | 002/003 (merged) — the capture step must still validate identity; every committed comparison generation's binding | Two force rebuilds over unchanged raw; a previously committed comparison still validates as current afterwards |
| HF-09 | 010, 011 (merged) and all their counts; the shipped `_quote_note` decision for KER 046 (suppressing it would reverse a shipped decision) | Every affected family's totals move by exactly the proved deltas and by nothing else; canaries re-blessed with documented evidence |
| HF-10 | 004/005/006 (merged) — the new lane must satisfy them at birth; the env comparison counts must not move | The 5 ENV cells' difference counts are identical before and after; every new image is reviewed individually |
| HF-11 | Everything merged before it — the guards must pass on the final state, not on a historical one | The two new guards fail on a deliberately reverted parser and pass on `main` |

## Per-bundle specification

Each section below is the **frozen contract** for that bundle. At the start of a
bundle's Stage 4, copy its section into
`hotfix-bundles/<ID>/BUNDLE.md` from
[the template](hotfix-bundles/TEMPLATE/BUNDLE.md), filling only the base `main`
SHA, implementer and reviewer names. The BUNDLE.md must not diverge from this
section; where they disagree, this file wins. (`HF-01/BUNDLE.md` is already
created because it is the first `READY` bundle.)

**Role assignment (owner decision, 2026-07-26): Claude implements every bundle;
Codex performs every review.** Both Stage 5 passes are Codex, in two separate
fresh chats: review 1 is the primary adversarial gate, and review 2 must
*challenge* review 1 and re-derive from source rather than copy it. This
satisfies Prompt 05's hard rule — "at least one reviewer must not be the bundle's
implementer" — on every bundle, since Codex is never the implementer, and it is
strictly stronger than the minimum (Claude never approves its own work).

Two consequences the reviewer must plan for:

- **Codex must bind to Claude-authored witnesses on the Claude-unique findings**
  (PCOA-FINAL-003, -006, -014, -015, -017, -018, -019, -022 and the RC-2/RC-3
  rechecks). The independence firewall ended on 2026-07-26, so Claude's retained
  Stage 1B root and the Stage 2 neutral root are both readable; the small
  `stage2-*.json` witnesses are committed in-repo. Binding to a witness is not
  accepting it — Prompt 05 item 5 still requires an independent recount.
- **Review 2 is the same agent as review 1.** Its challenge value comes from
  re-deriving, not re-reading: it must re-run the acceptance generation itself,
  recount from raw, and explicitly list what review 1 did not check. A review 2
  that only restates review 1 is a failed review, and the second planner should
  say so if it happens.

---

### HF-01 — Clean Road skipped-source truth and disclosure

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-01` / `clean-road-source-truth` |
| Branch | `hotfix/hf-01-clean-road-source-truth` |
| Priority / order | **1 — first implementation bundle** |
| Depends on | Nothing |
| Findings | **PCOA-FINAL-010** (P1) |
| Implementer | Claude |
| Review 1 | **Codex** (holds `clean-road-comparison-unlocatable-impact.json` and `CLEAN-ROAD-HIGHWAY-RAW-SOURCE-TRUTH-FINAL.md`) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED → `READY` on joint planner sign-off |

**Exact scope.** Clean Road Highway only: the ArcGIS build
(`clean_highway_built.xlsx`) and the ArcGIS-vs-TSN comparison in **both**
flavors (values + formulas), i.e. Matrix F's 2 decisions. No other report
family, workflow, or format.

**Explicitly out of scope.** The ArcGIS build *rule* (proved rule-faithful over
57,728 rows / 4,271,872 cells — the finding says the rule is not the defect);
odometer-based span placement (the model forbids keying on odometers — three
calibrations exist); the Clean Road Intersection and Ramp builds (DEF-05); the
5 landmark representation cells (HF-09); Clean Road clipping (HF-02); any change
to the 74-column header, the context-column set, or `CONTEXT_FIELDS`.

**Verified root cause.** `consolidate_clean_highway._read_span_layer` drops any
as-of span whose begin **or** end PM measure is unusable
(`scripts/consolidate_clean_highway.py:182-184`) and, unlike
`_split_parked:323-328`, records nothing — so the row never reaches `warnings`,
never reaches the build's `PARTIAL` completion, never reaches the marker sheet,
and never reaches the comparison's Summary or Notes. The affected anchors then
publish as ArcGIS-side blanks that the comparison classifies as differences: 161
exact false positives and 4 genuine differences shown with a false blank side,
across 83 comparison rows / 87 source endpoints.

**Files expected to change.** `scripts/consolidate_clean_highway.py`
(record + surface the skip), `scripts/compare_clean_highway_tsn.py` (disclose it
and stop asserting the skipped anchors), `build/check_clean_road.py` (red→green),
and — only if the design below requires it — one additive opt-in
`CompareSchema` field in `scripts/compare_core.py`.

**Planner design sketch (not binding).** Two acceptance branches exist; only one
satisfies both sentences of the oracle. Recommended: (i) `_read_span_layer`
records each unusable-PM span with its layer, route, county, prefix and the
measures it did have; (ii) the build's marker sheet, message, `PARTIAL`
completion and `clean_road_build` sidecar carry the count and the reason;
(iii) the affected anchors are emitted with a reserved *unavailable* token rather
than an empty cell, and the schema declares that token **non-asserting** so those
cells render as `N`, display the reason, and leave the difference count — the
per-cell precedent is the ditto `N` at `compare_core.py:1648-1650`, and this is
exactly the "opt-in `CompareSchema` for report-specific behavior" carve-out;
(iv) Summary and Notes state the skipped-row count, the affected anchor count and
why. Fallback if the owner refuses any engine hook: disclosure only, which
satisfies branch (b) but leaves the 161 visible — a reviewer must then record
that the oracle's second sentence is unmet. **This is the bundle's one open
design question and is listed in the challenge log.**

**Migration / compatibility.** The build workbook gains a marker-sheet/sidecar
field; `tsn_load_clean_road`'s normalizer and the marker version (`v1`) are
untouched, so a previously built workbook must still compare — or be refused with
a message naming the rebuild. Any comparison-visible change moves `CRH-SW-E2`:
the re-bless is mandatory, documented with exact input/output evidence in
[`comparison-canary-bindings.md`](../comparison-perfection/comparison-canary-bindings.md)
(§ "CRH-SW-E2 — the v0.29.1 re-bless"), and must honor the
[Phase-3 decision gates](../comparison-perfection/comparison-phase3-decision-gates.md).

**Tests to add.** In `build/check_clean_road.py` (hermetic synthetic library —
no real data, no network): a span row with one unusable PM endpoint and usable
AR/odometer measures must (a) appear in the build's skip record, (b) make the
build report `PARTIAL` with a non-zero `skipped_inputs`, (c) surface on the
marker sheet and in the sidecar, and (d) in a real `mode="both"` comparison
against a TSN row carrying the same value, **not** produce a counted difference,
while a genuinely differing anchor still does. The check must fail on
`main` @ `a29bdb6` before the fix.

**Exact end-user generation path.** GUI **ArcGIS tab** → build the Clean Road
Highway workbook from `arcgis_layers/` at the TSN extract's own as-of date →
compare against the TSN `CA HIGHWAYS` extract, `mode="both"`. Drive the shipped
GUI/worker path, not `consolidate()`/`compare()` directly, and assert the written
workbooks.

**Source-truth recount.** For all 102 skipped raw rows, an app-free reader joins
each visible ArcGIS row's `Key (helper)` token to the Comparison sheet's hidden
`__CMP_E2_KEY_V1_TOKEN`, infers no missing span, and reports: the 161 cells where
the raw ArcGIS value equals the visible TSN value, and the 4 at route 036 / TEH /
40.15 and 40.352 where the raw anchors read `1/12` against TSN `2/24`. Recount
statewide totals independently (52,647 / 5,081 / 7,436 paired; 291,292 differing
cells pre-fix) and state the exact post-fix figures.

**Values / formulas and installed-Excel checks.** Both twins regenerated; the
values twin read `data_only=True`; the formulas twin recalculated in installed
Excel with every SELF-CHECK row `OK` and no `#REF!`/`#VALUE!`; the two twins
agree cell-for-cell on every changed cell class.

**Workbook visual / presentation checks.** Inspect *Summary*, *Notes*,
*Comparison*, *ArcGIS Build*, *Provenance* at native scale: the new disclosure is
readable in its stored column width, the 24 grey context headers and
`context_header_fill` are unchanged, the skipped-anchor display is
unambiguous, and no previously legible cell became clipped.

**Evidence.** Clean Road has no evidence adapter; **prove zero evidence
artifacts are produced** by this path, before and after.

**Neighbouring-family regression.** No other family shares this code. Run the
full gate; additionally re-run `check_clean_road.py`,
`check_compare_equality_policy.py`, `check_compare_audit.py`,
`check_comparison_artifact_schema.py`, and — if the `CompareSchema` hook is
used — `check_compare_ditto.py` plus one unaffected family's comparison
(Intersection Summary vs TSN) proved byte-identical to its pre-fix twin.

**Measurable acceptance criteria.**
1. The 161 exact false positives are **0**.
2. The 4 misrepresented cells show the real ArcGIS value or an explicit skipped
   marker — never an unqualified blank.
3. Summary **and** Notes state the skipped-source-row count, the affected anchor
   count, and the reason (`LocError=NO ERROR` rows with a missing PM endpoint).
4. Both twins regenerate; formulas recalculate clean in installed Excel.
5. `CRH-SW-E2` re-blessed with a documented delta and exact evidence.
6. Full gate green; `check_clean_road.py` fails pre-fix and passes post-fix.
7. No genuine difference disappeared: the post-fix differing-cell total equals
   291,292 minus exactly the proved false-positive delta, itemized.

**Rollback.** Revert the bundle's merge commit. The build workbook is
regenerated by the user on demand, and no persisted comparison schema version
changes, so a revert needs no data migration — only a rebuild.

**Retained output / witness.** Bulk (both twins, the built workbook, the
recount) → `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\`.
Committed machine-readable witness (skip census, the 165-cell before/after
join, the recount totals) →
`hotfix-bundles/HF-01/witness/`. Never write into any Stage 1/2 audit root.

---

### HF-02 — Shared workbook presentation and self-description

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-02` / `workbook-presentation` |
| Branch | `hotfix/hf-02-workbook-presentation` |
| Priority / order | 2 |
| Depends on | Nothing (sequenced after HF-01 so its Clean Road witness covers the merged state) |
| Findings | **PCOA-FINAL-008** (P1), **-009** (P2), **-014** (P2), **-019** (P3) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to its own `statewide-summary-visible-text-clipping.json`, `large-detail-no-render-visual-adjudication.json` and native-Excel renders, plus the committed `stage2-measure-clipping.py` / `stage2-clipping-recheck.json` |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** Stored presentation and self-description of the generated
comparison workbook, **all families, both twins**: the `Comparison` category/key
column, the data sheets' key and back-link columns, `Spot Check`, `Summary`
labels, the *DIFFERENCES BY FIELD* rendering of wholly-context columns, and the
values twin's `Summary!B3` headline.

**Explicitly out of scope.** Any equality, normalization, pairing, count, or
mask change; the data columns (explicit width 13.0), the 45.75 pt wrapped header
row, hidden/veryHidden states, autofilter ranges and freeze panes — all Stage
2-validated clean and must stay byte-identical in behaviour; the `Notes` prose of
any family; evidence; the live `Summary!C56:C62` SELF-CHECK rows (deliberately
live and disclosed).

**Verified root cause.** Widths are hard-coded workbook facts in the shared
writer: `compare_core._write_comparison:2170` (`c_loc` = 12 → the measured 89 px
against labels needing up to 309 px), `_write_data_sheet:2015-2016` (key 14,
back 13), `_write_spot_check:2346-2348` (`B` = 19 → `Spot Check!B6` 55–76 px
short), `_write_summary:2998` (`B` = 46 → `Summary!B13:B14` 47–364 px short);
`summary_layout.py:634-635` for the by-category extra sheet. Separately,
`_write_summary` renders a wholly-context column's per-field count as a bare `0`
indistinguishable from a compared column with no differences (014), and writes
the `Summary!B3` headline as a formula with no cached value (019).

**Files expected to change.** `scripts/compare_core.py`,
`scripts/summary_layout.py`, and one new golden check.

**Planner design sketch (not binding).** Prefer wrapping + a widened column over
extreme widths — `Summary!B13`'s worst case needs ~691 px, which is an
instruction string, not an identity; the *identity* cells (`Comparison` category,
composite key, `Spot Check!B6`) should be widened to fit. For 014, render
`context` / `not compared` instead of `0` for a column that is context in its
entirety, leaving Highway Log's per-cell ditto columns reporting real counts. For
019 the low-risk path is the oracle's first branch on the **values** flavor only:
write `Summary!B3` as the computed literal (the values twin already writes
literals everywhere else), leaving the formulas twin live.

**Migration / compatibility.** Column widths and one label string are
presentation; no count, mask, schema version, or sidecar changes, so committed
comparison generations stay valid and `read_counts`' header-label lookup is
unaffected. Bytes move in every regenerated workbook — confirm no check asserts
byte-identity (only `check_compare_tsn_common.py:132` asserts a width, and it
asserts a *widened* column).

**Tests to add.** A new golden check that builds one summary-schema and one
detail-schema comparison in both flavors and applies RC-1's measurement rule —
real Calibri 11 metrics, Excel's width→pixel model, 6 px tolerance, reporting a
cell only when it cannot spill (no wrap, no shrink-to-fit, populated right
neighbour, merged ranges credited) — over `Summary`, `Spot Check`, `Comparison`
label and composite-key cells; plus assertions that a wholly-context column
renders non-numerically and that the values twin's `Summary!B3` is non-empty
`data_only=True`. Reuse `stage2-measure-clipping.py`'s documented gate so the
product check and the audit oracle cannot diverge.

**Exact end-user generation path.** Compare tab → classic current-vs-prior
environment for Ramp Summary, Intersection Summary and Ramp Detail (PDF); Direct
vs TSN for Ramp Summary and Intersection Summary; the Everything matrix for one
summary and one detail family; the merged HF-01 Clean Road pair. Both twins each.

**Source-truth recount.** None required — no count changes. **Prove** that: the
differing-cell and differing-row totals of every regenerated workbook are
identical to their pre-fix values, and every hidden state mask is byte-identical.
That invariance *is* this bundle's source-truth assertion.

**Values / formulas and installed-Excel checks.** Both twins for every
regenerated family; installed-Excel recalculation with every SELF-CHECK row `OK`
and no error values; the formula twin's one-row offset (`B13:B14` → `B14:B15`)
handled explicitly.

**Workbook visual / presentation checks.** Native-Excel render of at least one
summary and one detail workbook: no two category rows share the same visible
text (the P1 harm in 008); `Spot Check` instructions, `Summary` labels and
composite keys legible in the default view without resizing; a re-run of the
RC-1 measurement reporting **zero** materially clipped cells against the 268
recorded in `stage2-clipping-recheck.json`.

**Evidence.** Not in scope; assert evidence artifacts are unchanged and that no
new artifact appears.

**Neighbouring-family regression.** Every family, because the writer is shared:
run the full gate plus `check_compare_audit.py`,
`check_compare_build_freshness.py`, `check_comparison_artifact_schema.py`,
`check_compare_equality_policy.py`, `check_compare_source_files.py`,
`check_matrix.py`, `check_day_matrix.py`, `check_baseline_matrix.py`,
`check_pdf_excel_matrix.py`, and the merged HF-01 Clean Road pair.

**Measurable acceptance criteria.**
1. RC-1's measurement reports **0** materially clipped cells in every
   regenerated workbook, both twins (was 268 across the five measured).
2. Native-Excel render confirms no category label is ambiguous — the
   `Ramp Type: C` / `Highway Group: R` collapse is gone.
3. Highway Sequence's `City`, `HG` and `Distance To Next Point` render as
   context/not-compared; Highway Log's ditto columns still report real counts.
4. Every values twin's `Summary!B3` is non-empty read `data_only=True` and
   matches the typed `ComparisonOutcome`.
5. All pre-existing counts, masks and typed outcomes unchanged, proved per
   family.
6. Full gate green; the new check fails pre-fix.

**Rollback.** Revert the merge commit; regenerate. No persisted artifact needs
migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-02\`
(regenerated workbooks + native-Excel PDFs);
`hotfix-bundles/HF-02/witness/` for the before/after clipping measurement JSON
and the per-family count-invariance table.

---

### HF-03 — vs-TSN capture identity, provenance and temp hygiene

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-03` / `tsn-capture-provenance` |
| Branch | `hotfix/hf-03-tsn-capture-provenance` |
| Priority / order | 3 |
| Depends on | Nothing |
| Findings | **PCOA-FINAL-002** (P1), **-003** (P2), **-016** (P3) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to `run-ledgers/tsn-library-rebuild.json`, `source-audit/all-completed-workflow-note-audit.json`, the committed `stage2-tsn-provenance-scope.json`, and Claude's `witness\temp_captures.txt` (readable since the firewall ended) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** The matrix lanes' private TSN capture step and what the
resulting workbooks say about their own TSN input: all 12 vs-TSN families × the
By Day and Everything lanes (36 workbooks), both twins, plus `%TEMP%` lifetime.

**Explicitly out of scope.** The Direct/classic lane (already clean — must stay
byte-identical); the TSN library's own normalization or identity determinism
(HF-08); the four comparators' `claims_notes` renderers (no change needed if the
sidecar is complete); the three families that expose no TSN identity by design
(Intersection Detail, Intersection Detail (PDF), Ramp Detail (PDF)) — they must
gain the honest provenance path but no invented identity line.

**Verified root cause.** `matrix_build.captured_tsn_workbook:227` copies the
normalized workbook into `tempfile.mkdtemp(prefix="tsmis-tsn-consumer-")`
(`:237`) and publishes a **reduced** 159-byte outcome sidecar beside it, dropping
`tsn_source_claims`, `tsn_normalization_version`, `tsn_raw_manifest`,
`tsn_normalized_workbook_identity` and `tsn_artifact_identity_token`. Claim
lookup is path-adjacent (`consolidation_meta.read_extra(tsn_path,
"tsn_source_claims")`), so on a matrix lane it always finds none and prints the
false "rebuild the TSN library" instruction (24 workbooks, at
`Summary by Category!A6`/`!A7`, `Notes!A9`, `Notes!A4`). The same captured path
becomes the user-facing provenance selection through
`compare_tsn_common.capture_input_provenance:604-625` (36 workbooks), and the
capture directory is not always removed.

**Files expected to change.** `scripts/matrix_build.py`
(`captured_tsn_workbook` only), `scripts/compare_tsn_common.py`
(provenance selection), plus checks.

**Planner design sketch (not binding).** Carry the library sidecar's full extra
payload onto the private copy (or bind claim lookup to the workbook's content
identity rather than its directory), and record provenance against the
**canonical library path** the capture was taken from while keeping the sha256 of
the bytes actually read. Make the capture directory removal unconditional across
success, failure and cancellation.

**Migration / compatibility.** The reduced sidecar must not lose any guarantee it
currently provides: the captured copy's identity validation
(`copied_identity != expected` → refuse; the private-path re-read) is the
integrity gate and must be preserved exactly. A comparison committed before this
bundle must still validate; a workbook produced after it must not claim an
identity it did not verify.

**Tests to add.** A hermetic check that a captured workbook carries the library
sidecar's claim fields; that a matrix-lane comparison's `Notes`/`Summary by
Category` prints the same TSN identity line as the Direct lane for all four
families that expose one; that no `Provenance` cell or `.provenance.json`
`selection` contains a `%TEMP%` path; and that zero `tsmis-tsn-consumer-*`
directories survive a success, a failure and a cancellation. Extend
`check_matrix_tsn.py` / `check_tsn_canonical_consumer_identity.py` rather than
adding a parallel harness.

**Exact end-user generation path.** Compare tab → **Rebuild the TSN library**
(`build_consolidated(force=True)`), then generate all 18 **By Day** and all 18
**Everything** vs-TSN workbooks from the matrix pages, and one Direct-lane
control per family from the classic Compare tab.

**Source-truth recount.** None (no counts change). Prove invariance of every
count and mask, and re-derive the 36-workbook classification independently by
both of RC-3's methods (zip/sheet-XML probe and an openpyxl cell walk) so the
before/after tables are directly comparable.

**Values / formulas and installed-Excel checks.** Both twins on at least one
family per identity class (identity-printing and identity-silent); installed
Excel recalculation clean.

**Workbook visual / presentation checks.** The identity line and the provenance
rows are readable in their stored widths on the merged HF-02 base; the false
instruction is gone from all 24 cells; the disclosed TSN vintage
(`2025-09` print vs `2026-07-23` pull) is visible to a reader.

**Evidence.** Assert unchanged: this bundle must not create, retire, or relabel
any evidence artifact.

**Neighbouring-family regression.** All vs-TSN families and all three lanes:
full gate plus `check_matrix_tsn.py`, `check_tsn_highway_log_claims.py`,
`check_tsn_canonical_consumer_identity.py`, `check_tsn_freshness.py`,
`check_tsn_outcome.py`, `check_matrix_cache_adversarial.py`,
`check_comparison_publication.py`, `check_artifact_store.py`.

**Measurable acceptance criteria.**
1. **Zero** occurrences of "rebuild the TSN library" across all 36 matrix-lane
   workbooks, both twins.
2. Every family whose Direct-lane workbook prints a TSN identity prints the
   **same** line on both matrix lanes.
3. No `Provenance` sheet and no `.provenance.json` names a `%TEMP%` path; every
   recorded TSN path exists and is readable after the run.
4. Zero `tsmis-tsn-consumer-*` directories remain after N runs including one
   cancellation and one failure.
5. Direct-lane workbooks unchanged; all counts, masks and typed outcomes
   unchanged everywhere.
6. Full gate green; the new assertions fail pre-fix.

**Rollback.** Revert the merge commit. Sidecar content is regenerated per run;
nothing persisted requires migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-03\`
(36+3 workbooks); `hotfix-bundles/HF-03/witness/` for the re-derived 36-workbook
classification and the temp-directory lifecycle log.

---

### HF-04 — Ramp Detail layout compatibility and same-source null parity

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-04` / `ramp-detail-layout` |
| Branch | `hotfix/hf-04-ramp-detail-layout` |
| Priority / order | 4 |
| Depends on | Nothing |
| Findings | **PCOA-FINAL-001** (P1), **-012** (P2, latent) |
| Implementer | Claude |
| Review 1 | **Codex** (holds `ramp-detail-pdf-excel-sibling-parity.json` and the header-census run ledgers) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** Ramp Detail, both editions: the 8 topology decisions the Excel
edition currently cannot produce (classic env, Direct/By Day/Everything vs TSN,
Baseline, Everything ENV, Direct self, Everything SELF), the ninth
PDF-vs-Excel by-day placement, the consolidator's completion truth, and the self
check's null-token symmetry.

**Explicitly out of scope.** Any other family's header contract; the PDF
edition's existing vs-TSN comparison counts; the 2-cell RD-PDF representation
class (HF-09); `compare_env.compare_folders`' missing-side preflight (HF-07);
assuming the permanent site matches the development site — the scope document
forbids it, so the fix must accept **both** layouts rather than replacing one
pinned layout with another.

**Verified root cause.** The 2026-07-23 dev-site Excel export changed shape (blank
labels removed; the print-only `OF` and `TY` columns added; values **moved**, not
merely relabelled). `compare_ramp_detail_tsn._TSMIS_HEADER` /
`compare_env._ramp_detail_canonical_header` pin exactly one layout, so refusal is
correct — but (a) `consolidate_ramp_detail.consolidate` still reports 126/126
`status=ok` for a workbook no comparator accepts, and (b) the refusal message
names a "leading 'Route' column" the workbook has, prescribing an action that
reproduces the identical failure. Separately, the self comparator projects
`-` / `NO RAMP LINEAR EVENT` to blank on the PDF leg (`_null_blank:76`) but not
on the Excel leg (`_load_excel_collapsed:155`), so once the gate opens the same
source token renders differently on the two legs of a same-source check: 108
cells / 36 rows (36 `Area 4`, 36 `OF`, 36 `Description`).

**Files expected to change.** `scripts/compare_ramp_detail_tsn.py`,
`scripts/compare_env.py` (RD header only), `scripts/consolidate_ramp_detail.py`,
`scripts/compare_ramp_detail_pdf.py`, plus checks.

**Planner design sketch (not binding).** Accept both censused layouts by
**name-keyed** field resolution rather than position, refusing anything that is
neither; make the consolidator's completion agree with downstream consumability
(a workbook no comparator accepts must not report `ok`); rewrite the refusal
message to name `exact_consolidated_header_ok` semantics and an action that can
succeed, following the sibling wording precedents (Intersection Detail names "the
current (July 2026) site format"; Highway Detail names "the exact 34-column
export header"); and apply the existing null projection symmetrically on the
Excel leg of the self check.

**Migration / compatibility.** Both the 2026-07-09 and 2026-07-23 layouts must
compare, and a mixed pair (old prior vs new current) must either compare
correctly or refuse with an accurate message — cross-environment and Baseline
routinely pair two different days. A consolidated workbook produced by the
current code must not become unreadable.

**Tests to add.** Extend `check_compare_ramp_detail.py`,
`check_compare_ramp_detail_tsn.py`, `check_compare_ramp_detail_pdf.py`: both
header layouts accepted with `OF`/`TY`/`Description` mapped correctly; a
third, unknown layout refused with a message naming the real gate; the
consolidator's completion downgraded when its output is not consumable; and a
same-source self check over rows carrying `-` / `NO RAMP LINEAR EVENT` on both
sides reporting **zero** differences.

**Exact end-user generation path.** Consolidate tab → Ramp Detail (both
editions) from the frozen `2026-07-23` run folder; then Compare tab → classic env
(2026-07-09 vs 2026-07-23), Direct vs TSN, the PDF-vs-Excel self check, the By
Day and Everything vs-TSN matrices, Baseline, Everything ENV, and the
PDF-vs-Excel by-day matrix.

**Source-truth recount.** Route 001 row 2 field-for-field against the raw export
(the finding's exact witness); an independent app-free recount of the newly
produced Excel-side comparisons; and confirmation that all 15,213 self-check rows
pair with zero missing keys.

**Values / formulas and installed-Excel checks.** All 8 decisions produce both
twins; the formulas twins recalculate clean; the RD-PDF vs TSN counts are
unchanged from pre-fix.

**Workbook visual / presentation checks.** On the merged HF-02 base: the new
Excel-side workbooks' `Summary`, `Spot Check`, `Comparison` and composite keys
are legible; the 11-column header renders correctly; `OF`/`TY` are labelled, not
positional.

**Evidence.** RD-PDF vs TSN and RD self are `PROHIBITED` under the audit rule and
currently produce nothing on the newly opened paths — **prove zero artifacts**
appear as a side effect of unblocking the comparison, and re-observe HF-05's rule
if HF-05 has already merged.

**Neighbouring-family regression.** Intersection Detail (the sibling that already
absorbed a site format change) and Highway Detail (whose header contract shares
the pattern, and which is **pre-release — do not touch**): full gate plus
`check_compare_intersection_detail_tsn.py`,
`check_compare_consolidated_layout.py`, `check_compare_env_*` and
`check_pdf_excel_matrix.py`.

**Measurable acceptance criteria.**
1. All 8 topology decisions plus the by-day PDF-vs-Excel placement produce both
   twins — or refuse with a message that names the real gate and a workable
   action (state which branch was taken, per finding).
2. `OF`, `TY` and `Description` proved correct on route 001 row 2 against raw.
3. The consolidator no longer reports `ok` for output no comparator accepts.
4. The Ramp Detail self check reports **zero** differing cells across all 15,213
   rows.
5. The 2026-07-09 layout still compares; an unknown layout still refuses.
6. RD-PDF vs TSN counts unchanged.
7. Full gate green; every new assertion fails pre-fix.

**Rollback.** Revert the merge commit; the previous behaviour (refusal) returns
without data loss. Consolidated workbooks on disk stay readable either way.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-04\`;
`hotfix-bundles/HF-04/witness/` for the two-layout header census, the route-001
row-2 field trace and the self-check zero proof.

---

### HF-05 — Evidence eligibility, source binding and panel fidelity

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-05` / `evidence-binding` |
| Branch | `hotfix/hf-05-evidence-binding` |
| Priority / order | 5 |
| Depends on | Nothing (blocks HF-10) |
| Findings | **PCOA-FINAL-004** (P1), **-005** (P1), **-006** (P1) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to its five `source-audit/*evidence*` review ledgers and `visual-review/evidence-review/`, plus Claude's `visual_evidence.py:1270` census and the RC-2 `FT_3_stacked.png` reproduction |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** The visual-evidence renderer's eligibility rule, per-side source
binding, target geometry and Excel-panel fidelity, across every path that emits
evidence today: By Day vs TSN, Everything vs TSN, Everything SELF — 11 registry
cells, 18 artifact sets, 1,778 retained PNGs.

**Explicitly out of scope.** Building the cross-environment lane (HF-10); the
comparison counts of any family; the two paths that already correctly emit
nothing (classic Compare tab, PDF-vs-Excel by-day matrix) — they must stay silent
and unchanged; the evidence *Ledger*'s content, which Stage 2 validated as
exhaustive and correct.

**Verified root cause.** Three independent defects in one renderer.
(a) `visual_evidence.generate:547` is entered for pairs whose semantic sides are
not both PDFs: side A can be the consolidated XLSX (`tsmis_source_role:173`),
side B is *always* the normalized TSN workbook on a vs-TSN comparison, and all
five SELF cells have an Excel side by construction — while
`_TSN_PDFS_IN_RAW:118` lets Highway Log/Highway Sequence borrow the library's raw
district prints and `intersection_detail*` / `ramp_detail_pdf` borrow a different
statewide PDF from `tsn_library\<report>\pdf\`; the workbook then asserts *"Red
box = the compared cell in each source PDF"* and declares a `TSMIS PDFs:`
directory absent from its own read set. The decisive case — 80 PDFs, zero XLSX,
still the wrong document — proves a PDF-only read set is not a sufficient test.
(b) When the compared value is blank on the TSN district print, the target box
lands on adjacent printed content (the final `O` of `EQUATES TO`; the *next*
Highway Log record) because the collapsed equation line has no column grid; the
TSMIS side, which has a fixed grid, is boxed correctly. (c)
`visual_evidence.py:1270` draws each Excel-side cell as `text[:26]` with no
ellipsis (header label capped at 24 on `:1266`), so 8 of 190 rendered examples
endorse a **different string** than the one compared.

**⚠ Owner policy gate — resolve before implementation.** The audit's eligibility
rule (Prompt 01 item 10 / neutral scope rule 11: evidence is prohibited whenever
either semantic side is a normalized XLSX) and the finding's acceptance oracle
(each read-set member must be *the exact artifact its side was compared from*)
are not the same rule. Read literally, the first would retire essentially the
entire shipped evidence feature — every vs-TSN cell and all five SELF cells —
including the CMP-AUD-210 Excel-side binding and the v0.32.0 `excel_column_for`
work that `check_evidence_source_role.py` locks in. The oracle, by contrast, is
satisfiable while keeping the feature: evidence each side **from the document that
side was compared from** (an Excel-compared side from its workbook; the TSN side
from the normalized workbook it was actually read from), never from a borrowed
sibling print, and stop asserting sources that were not read. **Stage 4 must not
choose between these on its own.** The implementer records the owner's ruling in
`IMPLEMENTATION.md` before changing eligibility; without a ruling, implement the
oracle (exact-source binding + honest prose + no artifact when a side cannot be
bound) and leave feature retirement unshipped.

**Files expected to change.** `scripts/visual_evidence.py`, the
`scripts/evidence_*.py` adapters (targeting), `scripts/matrix_build.py`
(evidence call sites only), and the guards at `scripts/day_matrix.py` /
`scripts/gui_matrix.py`; plus checks.

**Tests to add.** Extend `check_visual_evidence.py`,
`check_evidence_source_role.py`, `check_evidence_manifest.py`,
`check_evidence_bundle.py`, `check_evidence_excel_columns.py`,
`check_evidence_literal_cells.py`: no artifact of any kind (manifest included)
for a pair failing the exact-source test; every read-set member equals the
comparison's own recorded provenance for that side; a blank-on-one-side example's
target rectangle lies inside the captioned record's row rectangle and touches no
other record's or field's glyphs — asserted over the whole generated set, with
explicit `EQUATES TO` and blank-`Description` fixtures so the assertion cannot
depend on sampling luck; and every drawn Excel panel string equals the compared
value or is visibly marked elided, in both layouts.

**Exact end-user generation path.** Matrix pages → the evidence toggle on the
By Day and Everything vs-TSN matrices and the Everything SELF lane, plus the
per-cell camera; and the classic Compare tab plus the PDF-vs-Excel by-day matrix
to prove they still emit nothing.

**Source-truth recount.** For every retained image, bind the drawn value back to
the published comparison cell through `published_comparison.py` (the truth layer
already decodes the workbook's own state masks) and to the raw print/workbook the
side was read from. Recount the 8-of-190 truncation census and the blank-side
target population exhaustively rather than by sample.

**Values / formulas and installed-Excel checks.** Comparison workbooks must be
untouched: assert every affected family's counts, masks and typed outcomes are
byte-identical before and after. Evidence workbooks open clean in installed
Excel with images embedded and the Ledger intact.

**Workbook visual / presentation checks.** Every evidence workbook's image
sheets, Summary and Ledger inspected at native scale on the merged HF-02 base;
no prose asserts a source not in the read set.

**Evidence review requirement.** **Every** retained image is inspected
individually — not a sample — for every cell that still generates after the
ruling; and for every cell that no longer generates, the artifact set (workbook,
image folder, manifest) is proved absent, with the prior set proved retired
rather than left looking current.

**Neighbouring-family regression.** HL, HSL, ID (both), RD-PDF, and HD (**do not
touch — pre-release**): full gate plus every `check_evidence_*`,
`check_visual_evidence.py`, `check_matrix.py`, `check_day_matrix.py`,
`check_pdf_excel_matrix.py`, `check_comparison_publication.py`.

**Measurable acceptance criteria.**
1. Zero artifacts — manifest included — for any pair failing the exact-source
   test; the 11 registry cells and their By Day counterparts re-run and asserted
   under the recorded ruling.
2. 100 % of rendered examples: drawn Excel-panel string equals the compared value
   or is marked elided.
3. 100 % of blank-side examples: target inside the captioned record, touching no
   other record or field.
4. No prose asserts an unread source; the `TSMIS PDFs:` declaration matches the
   read set.
5. The two already-correct paths still emit nothing.
6. All comparison counts and typed outcomes unchanged.
7. Full gate green; every new assertion fails pre-fix.

**Rollback.** Revert the merge commit. Retired artifact sets are regenerable;
no comparison workbook is modified, so nothing downstream needs migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-05\`
(every generated image set, before and after);
`hotfix-bundles/HF-05/witness/` for the exhaustive per-image verdict table, the
truncation census and the target-geometry measurements.

---

### HF-06 — Highway Sequence self-check equation classification

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-06` / `hsl-self-equation` |
| Branch | `hotfix/hf-06-hsl-self-equation` |
| Priority / order | 6 |
| Depends on | HF-02 (Summary rendering is the disclosure surface) |
| Findings | **PCOA-FINAL-011** (P1) |
| Implementer | Claude |
| Review 1 | **Codex** (owns the 60,254-row equation witness and the route-001 raw adjudication) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** The Highway Sequence PDF-vs-Excel **self** check only, on all
three paths that agree today (Direct self, Everything SELF, PDF-vs-Excel by-day
matrix), both twins — 2 topology decisions.

**Explicitly out of scope.** Highway Sequence **vs TSN** (its equate disclosure
already exists and its counts must not move by a single cell); every other
family's self check; **any shared equality change** — the normalization is opt-in
and scoped to this comparator; the punctuation/case/slash Description class, which
the owner ruled stays **flagged** (HF-09) and must not be swept up by this
normalization; evidence.

**Verified root cause.** The two editions represent one equation differently by
design: the print writes a source line plus a target line, the Excel export folds
marker, classification, suffix placement and description onto its source record.
`compare_highway_sequence_pdf._NOTES_PDF_VS_EXCEL:78-107` already *describes*
this class in prose, but `_SS_SCHEMA:156` asserts every column, so 1,119
equation relations surface as 3,714 differing cells across 1,395 rows
(`PM Suffix` 547, `HG` 929, `FT` 1,119, `Description` 1,119) inside an
unqualified total. Codex's full-corpus canonicalization — 1,119 relations, 39
county/route-boundary relations, three delayed target moves, zero unsupported
cases — leaves **zero** differing rows and cells.

**Files expected to change.** `scripts/compare_highway_sequence_pdf.py` — the
same-source loaders (`_tsmis_row_same_source:118`, `_load_tsmis_same_source:147`),
`_SS_SCHEMA:156` and `_NOTES_PDF_VS_EXCEL:78-107` — plus an opt-in
`CompareSchema` field in `scripts/compare_core.py` if the pair-aware rule needs
engine support, plus checks. The vs-TSN schema (`_hsl._SCHEMA`) and every other
family's schema must be untouched.

**✅ Owner ruling — 2026-07-26: NORMALIZE. These are not real discrepancies.**
The oracle's two branches were "zero differing cells" (canonicalize the relation)
or "a disclosed class excluded from the count". The owner reviewed the actual
cells and ruled the **normalize** branch: the self check must report **zero**
differing cells for the equate population. Summary/Notes disclosure is retained
as documentation of the rule, not as the mechanism.

**The evidence the ruling was made on** — route 001, `ORA 018.540` / `018.530`,
rendered from both editions of the frozen pull (print page 6 vs
`highway_sequence_route_001.xlsx` rows 120–121; images retained locally only,
since they carry real TSMIS content):

| Field | Print (PDF) | Excel export | Why it is not a data difference |
|---|---|---|---|
| `018.540` PM suffix | *blank* | `E` | The same single `E` sits on the **partner row** of the pair on the other side |
| `018.540` HG | *blank* | `D` | Both editions carry `D` on `018.530`; the print does not repeat it on the annotation line |
| `018.540` FT | *blank* | `H` | Same — both carry `H` on `018.530` |
| `018.540` Description | `EQUATES TO END R REALIGNMENT` | `END R REALIGNMENT` | The print prepends the words `EQUATES TO ` |
| `018.530` PM suffix | `E` | *blank* | The partner half of the moved suffix |
| `018.530` HG / FT / Distance | `D` `H` `001.267` | `D` `H` `001.267` | Already equal |

The print additionally colours the whole equate — `018.540`, `EQUATES TO` and the
entire `018.530` line in red, `END R REALIGNMENT` in green, against black
elsewhere (verified from the PDF's own character colours). That marker has no
representation in an XLSX at all, which is precisely why the two editions place
the pieces differently.

**Design consequence Stage 4 must not miss.** A cell-by-cell normalization cannot
close the 547 `PM Suffix` cells, because the `E` genuinely sits on a *different
row* on each side. The rule has to be **pair-aware** — the equate's source and
target rows canonicalized as one relation, which is exactly what Codex's
audit-time canonicalization did over all 1,119 relations (39 county/route-boundary
relations, three delayed target markers, zero unsupported cases, zero residual).

**Guard rails, non-negotiable.** This moves a published count from 3,714 to 0, so:
the change rides an **opt-in** mechanism scoped to this comparator — never a
shared-formula or shared-equality edit; it honors the `compare_core` correctness
lock and
[the Phase-3 decision gates](../comparison-perfection/comparison-phase3-decision-gates.md)
(D0's "is this a difference?" criterion); it is proved against an **independent**
oracle over all 60,254 rows, not the product's own parser; Highway Sequence
**vs TSN** counts must not move by a single cell; and the anti-suppression test
below is mandatory — a genuine divergence at an equate row must still be
reported.

**Migration / compatibility.** The published count moves 3,714 → 0, which moves
any bound canary and invalidates nothing persisted — but a committed self-check
generation built under the old rule must be distinguishable from a new one, so the
Notes must state the normalized class explicitly and the workbook must make the
rule self-evident. A reader who compares an old workbook against a new one has to
be able to see *why* the number changed without reading the changelog.

**Tests to add.** Extend `check_compare_highway_sequence.py` with equate
fixtures built to the measured route-001 shape: (a) a source/target pair whose
only differences are the prepended `EQUATES TO`, the non-repeated HG/FT and the
moved `E` reports **zero** differences; (b) the same pair with a real Description
label change still reports a difference; (c) the same pair with a real HG or FT
change on the partner row still reports a difference; (d) an `E` present on one
side only, anywhere in the pair, still reports a difference; (e) a county/route
boundary relation and a delayed target marker are both covered; (f) the rule is
inert for a schema that does not opt in.

**Exact end-user generation path.** Consolidate tab → Highway Sequence both
editions from the frozen `2026-07-23` pull; Compare tab → the PDF-vs-Excel self
check; then the PDF-vs-Excel by-day matrix and the Everything SELF lane. Both
twins.

**Source-truth recount.** Re-derive the 1,119 relations with an app-free reader
over all 60,254 shared rows; independently confirm route 001's XLSX rows 121–122
against rendered PDF page 6; state the exact residual difference count and prove
every remaining difference is a genuine source divergence.

**Values / formulas and installed-Excel checks.** Both twins on all three paths;
installed-Excel recalculation clean; the three paths must agree exactly
(workflow parity is a Stage 2-validated invariant).

**Workbook visual / presentation checks.** Summary and Notes name the class and
its exact count; the disclosure is legible in its stored width on the merged
HF-02 base.

**Evidence.** HSL self is `PROHIBITED`; prove zero artifacts (or the
HF-05-ruled behaviour) and that this bundle changed nothing about evidence.

**Neighbouring-family regression.** Highway Sequence vs TSN (counts must not
move), Highway Log self, Intersection Detail self, and the parity of the three
dispatch paths: full gate plus `check_compare_highway_sequence*.py`,
`check_phase6_highway_sequence_conservation.py` (on demand),
`check_pdf_excel_matrix.py`, `check_day_matrix.py`.

**Measurable acceptance criteria.**
1. The frozen-pull self check reports **zero** differing cells and **zero**
   differing rows, proved over all 60,254 rows by an independent reader — not by
   the product's own parser. (The oracle's disclose-and-exclude alternative is
   closed by owner ruling; normalization is the required mechanism.)
2. All four affected columns close, `PM Suffix` included — so the rule is
   demonstrably pair-aware, not per-cell.
3. **Anti-suppression, mandatory:** a genuine divergence injected at an equate row
   (a changed Description label, a real HG/FT change on the partner row, an `E`
   present on only one side anywhere in the pair) is still reported as a
   difference. A fixture per case.
4. Summary and Notes name the normalized equate class and its relation count so a
   reader knows why the number is zero.
5. HSL **vs TSN** counts unchanged to the cell; all three self paths agree
   exactly.
6. The rule is opt-in and inert for every other family — one unrelated family's
   comparison proved byte-identical to its pre-fix twin.
7. Any moved canary re-blessed with cell-for-cell evidence and a documented
   delta.
8. Full gate green; every new fixture fails pre-fix.

**Rollback.** Revert the merge commit; the self check re-publishes the 3,714
equate cells. Record that explicitly in `IMPLEMENTATION.md` — a revert here is
visible in the deliverable, unlike the presentation bundles.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-06\`;
`hotfix-bundles/HF-06/witness/` for the independent relation census and the
before/after count table.

---

### HF-07 — Missing-side fast fail and export coverage truth

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-07` / `fastfail-coverage` |
| Branch | `hotfix/hf-07-fastfail-coverage` |
| Priority / order | 7 |
| Depends on | HF-04 (`compare_env.py` ownership) |
| Findings | **PCOA-FINAL-015** (P2), **-018** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer. Both findings are Claude-unique, so Codex must bind to Claude's `witness\export_coverage.txt`, the committed `claude-round1-export-coverage.txt`, and the three timing witnesses, then re-measure independently |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** 015: the folder-comparison preflight on every statewide PDF
family, in classic environment, Baseline and Everything ENV. 018: the catalog's
export-only truth and its UI surfacing for `ramp_summary_excel`,
`intersection_summary_pdf` and `highway_summary`.

**Explicitly out of scope.** Adding comparators for the three unverifiable
editions (that is DEF-04 for Highway Summary and a separate feature for the other
two — this bundle makes the gap *explicit*, not closed); any change to the
comparison's own semantics; the Ramp Detail header contract (HF-04); any change
to Highway Detail's parsers, schema, canaries or data (**pre-release**).

**Highway Detail note.** One of 015's three witnesses is `highway_detail_pdf`
Everything ENV (1,229.7 s). Reproducing a *latency* on that configuration
requires no HD schema judgement, no HD canary, and no trust in any HD artifact,
so it is compatible with the standing HD pre-release rule. The fix itself is in
the shared preflight and reaches HD without touching HD code.

**Verified root cause.** 015: `compare_env.EnvComparator.compare_folders:1033`
already computes both sides' member lists at `:1065-1066`, yet nothing checks
side B for emptiness before side A is fully parsed at `:1139+` — measured
429.4 s, 438.6 s and 1,229.7 s to report a missing second side, against 0.0 s
for a missing first side. 018: `report_catalog.ExportEntry:88` has no export-only
concept, so three enabled editions (343 of 2,380 exported route files, 14.4 %)
have no consolidator, no `MATRIX` row and no recipe, and nothing in the UI says
so; `build/check_report_wiring.py` already derives required touchpoints and is
the natural gate.

**Files expected to change.** `scripts/compare_env.py` (`compare_folders`
preflight only), `scripts/report_catalog.py`, `scripts/reports.py`,
`scripts/ui/` (the export-only label), `build/check_report_wiring.py`.

**Migration / compatibility.** The preflight must not reject a legitimately
empty-but-present side differently from today's eventual message — the *verdict*
stays the same, only the latency changes; and it must not fire on the Ramp
Summary/Intersection Summary aggregate loaders whose discovery shape differs. The
catalog's stable IDs are immutable and `_V017_EXPORT_ORDER` is append-only: an
export-only marker is additive metadata, never a reordering.

**Tests to add.** A check that a comparison with side B's report folder absent or
empty returns its typed error in under 5 s with side A untouched (assert on
elapsed time and that no parse occurred), for one XLSX-sourced and one
PDF-sourced family; and a `check_report_wiring.py` extension that fails naming
any enabled edition that has neither a dispatchable comparison path nor an
explicit export-only marker plus UI surfacing.

**Exact end-user generation path.** 015: Compare tab → classic environment for
`intersection_detail_pdf` with the second run folder's report subfolder absent;
repeat on Baseline and Everything ENV. 018: the report picker, Consolidate tab and
Compare tab in the GUI (verify through the `#mock` preview at
`/index.html#mock`, remembering the browser caches `app.js`/`app.css`).

**Source-truth recount.** None. Assert instead that every non-empty comparison
still produces identical counts, and that the export-coverage census reproduces
126 + 217 = 343 unverifiable files against 2,380.

**Values / formulas and installed-Excel checks.** One regenerated comparison per
family class, both twins, proving the preflight changed nothing about a valid run.

**Workbook visual / presentation checks.** None for 015 (no workbook). For 018,
the export-only labelling is legible in the GUI at default width and does not
break the picker's grouping.

**Evidence.** Unchanged; assert no artifact appears or disappears.

**Neighbouring-family regression.** All folder-comparison families and the whole
catalog derivation: full gate plus `check_report_wiring.py`,
`check_report_catalog.py`, `check_report_recipe.py`, `check_compare_env_*.py`,
`check_matrix.py`, `check_baseline_matrix.py`, `check_a2_compare_filter.py`, and
the `#mock` GUI preview.

**Measurable acceptance criteria.**
1. With side B absent, every comparison path reports the missing side in **under
   5 s** regardless of side A's size — reproduced on all three witnessed
   configurations.
2. A valid comparison's counts, twins and typed outcome are unchanged.
3. Every enabled export edition either has a dispatchable comparison path or is
   marked export-only in the catalog **and** shown as export-only in the UI;
   `check_report_wiring.py` fails naming any that satisfies neither.
4. Full gate green; both new assertions fail pre-fix.

**Rollback.** Revert the merge commit. Catalog metadata is additive, so a revert
only restores the silent gap.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-07\`;
`hotfix-bundles/HF-07/witness/` for the three timing measurements (before/after)
and the re-derived coverage census.

---

### HF-08 — TSN normalization identity determinism

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-08` / `tsn-identity` |
| Branch | `hotfix/hf-08-tsn-identity` |
| Priority / order | 8 |
| Depends on | HF-03 (the capture step must already be identity-complete) |
| Findings | **PCOA-FINAL-017** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer. Claude-unique finding, so Codex must bind to Claude's `witness\tsn_rebuild_all.json` and re-run the double rebuild itself; the root cause is an unverified hypothesis and the reviewer's first job is to confirm the implementer actually established it |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** The TSN library's normalized-workbook build and identity for all
eight supported datasets, and the consequence that pressing *Rebuild* invalidates
every bound vs-TSN comparison.

**Explicitly out of scope.** Any normalization *content* change (a content change
requires a `report_catalog.TSN` `normalization_version` bump plus a full re-bless
and is a different bundle); the clean-road normalizer's marker version; the
comparators' claim rendering (HF-03).

**Verified root cause — unestablished.** A force rebuild over raw whose
`tsn_raw_manifest.sha256` and `normalization_version` were unchanged produced a
different `tsn_normalized_workbook_identity` and `tsn_artifact_identity_token`
for all eight datasets. The finding labels the openpyxl-timestamp explanation an
**explicit hypothesis** and requires implementation to begin by establishing the
real cause; the pre-rebuild bytes were replaced and cannot be re-diffed.
Inspection anchors: `tsn_library.build_consolidated:909`,
`_write_normalized_workbook:1152`, `normalized_workbook_identity:249`.

**Files expected to change.** `scripts/tsn_library.py`, plus checks. If the cause
turns out to lie in a per-report loader, Stage 4 stops and returns the bundle to
Stage 3 rather than widening scope.

**Migration / compatibility.** Making the bytes deterministic changes the
identity **once**, so every existing bound comparison is invalidated by the fix
itself. Plan for it explicitly: state in `IMPLEMENTATION.md` that one full
re-comparison is expected after this bundle, and confirm the invalidation is
detected and reported honestly rather than silently producing a stale-bound
result.

**Tests to add.** A hermetic check that two consecutive
`build_consolidated(report, force=True)` calls over unchanged synthetic raw
produce byte-identical workbooks and identical identity/token values, for every
supported dataset shape; plus a check that a rebuild which *should* change
identity (raw manifest or normalization version changed) still does.

**Exact end-user generation path.** Compare tab / Settings → **Rebuild TSN
library** twice in a row over unchanged `tsn_library\<report>\raw\`, then one
vs-TSN comparison per dataset to confirm bindings survive.

**Source-truth recount.** None. Prove instead that normalized content is
unchanged by the fix: every dataset's row/field projection equals its pre-fix
projection cell-for-cell (the Stage 2-validated normalization fidelity must
hold — Intersection Detail 16,626 rows / 631,788 cells, Ramp Detail 15,410 rows,
Clean Road 60,083 × 74 with zero changed cells).

**Values / formulas and installed-Excel checks.** One vs-TSN comparison per
dataset regenerated after the double rebuild, both twins, counts unchanged.

**Workbook visual / presentation checks.** The normalized workbook still opens
in Excel with its marker sheet and normalization marker intact.

**Evidence.** For the two `_TSN_PDFS_IN_RAW` families, confirm the raw prints and
their bindings are unaffected.

**Neighbouring-family regression.** All eight datasets and every vs-TSN
comparison: full gate plus `check_tsn_normalizer.py`,
`check_tsn_normalization_marker.py`, `check_tsn_freshness.py`,
`check_tsn_outcome.py`, `check_tsn_raw_source_contract.py`,
`check_tsn_canonical_consumer_identity.py`, `check_tsn_status_coherence.py`,
`check_artifact_store.py`.

**Measurable acceptance criteria.**
1. The real root cause is **established and documented** before the fix.
2. Two consecutive force rebuilds over unchanged raw produce byte-identical
   workbooks and identical `tsn_normalized_workbook_identity` /
   `tsn_artifact_identity_token`, for all eight datasets.
3. A rebuild that should change identity still does.
4. Normalized content unchanged cell-for-cell; all vs-TSN counts unchanged.
5. The one-time invalidation is disclosed, detected and reported honestly.
6. Full gate green; the determinism check fails pre-fix.

**Rollback.** Revert the merge commit; identities become non-deterministic again
and one further re-comparison is needed. Note this asymmetry in
`IMPLEMENTATION.md`.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-08\`;
`hotfix-bundles/HF-08/witness/` for the double-rebuild identity table across all
eight datasets and the content-invariance proof.

---

### HF-09 — Representation-only difference classification

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-09` / `representation-class` |
| Branch | `hotfix/hf-09-representation-class` |
| Priority / order | 9 |
| Depends on | HF-01 (Clean Road Notes), HF-02 (Summary rendering), HF-06 (the disclosed-class pattern) |
| Findings | **PCOA-FINAL-013** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** (owns the four semantic-classification witnesses) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** The measured representation-only Description/landmark class in
Direct, By Day and Everything vs TSN plus the Clean Road comparison: Highway Log
1,243 × 2 formats, Highway Sequence 11 × 2, Ramp Detail (PDF) 2, Intersection
Detail 1 × 2, Clean Road Highway 5.

**Explicitly out of scope.** **Any equality, normalization or count change
whatsoever** — the owner ruling above closes that branch, so a diff that removes
even one cell from a published total is scope leakage and a reviewer must reject
it. Also out of scope: suppressing the KER 046 `''F'' ST` vs `"F" ST` pair, which
the product already deliberately annotates through the evidence `_quote_note`;
the Highway Sequence self-check equation class (HF-06); route 140's missing
columns (HF-11 / vendor).

**Verified root cause.** The differences are **real literal differences between
two sources** — normalization is not the cause (all 15,410 Ramp Detail and all
16,626 Intersection Detail TSN rows match raw field-for-field; Clean Road's
60,083 × 74 normalization changes zero cells; the identical 1,243-cell set
appears in *both* fresh export formats, ruling out a PDF-extraction artifact).
The defect is that unqualified headline totals do not distinguish this exactly
measured punctuation/case/quote/presentation class from substantive data changes.

**✅ Owner ruling — 2026-07-26: DISCLOSURE ONLY. These differences stay
flagged.** The oracle offered disclosure **or** a separately approved
normalization; the owner has ruled that the punctuation/case/quote/slash class
must remain counted and visible, so the normalization branch is **closed** and no
equality change may be proposed under this bundle. Concretely: the comma-vs-slash
Description pairs (`NEVADA STATE LINE , END OF COUNTY` vs
`NEVADA STATE LINE /END OF COUNTY`, 1,243 per format), `SLO SB CO LINE` vs
`SLO/SB CO LINE`, `CITRUS AVE OC 54-1293` vs `Citrus Ave OC 54-1293`,
`NB OFF TO S. GEYSERVILLE` vs `NB OFF TO S.GEYSERVILLE`, `''F'' ST` vs `"F" ST`,
and the Clean Road leading-apostrophe landmarks all keep their red `D` state and
stay inside every published total. The bundle adds a **count line**, nothing
more.

This is consistent with Stage 2, which explicitly declined to impose a new
equality rule ("the literal differences remain truthful"), and with the shipped
`_quote_note` decision for KER 046, which treats such a pair as worth *showing*.

**Files expected to change.** `scripts/compare_highway_log.py`,
`scripts/compare_highway_sequence_tsn.py`,
`scripts/compare_intersection_detail_tsn.py`,
`scripts/compare_ramp_detail_pdf.py`, `scripts/compare_clean_highway_tsn.py`,
plus a shared opt-in classifier hook (likely one `CompareSchema` field and its
Summary rendering in `scripts/compare_core.py`), plus checks.

**Migration / compatibility.** Under the ruled disclosure branch **no count
moves**, no canary moves, and every committed comparison generation stays valid —
the workbook simply says more about a total it already published. That makes this
the lowest-risk of the semantics bundles. If implementation discovers that
disclosure is impossible without touching equality, it **stops and returns the
bundle to Stage 3** rather than proceeding (Prompt 04 rule).

**Tests to add.** Per family: a fixture pair differing only in punctuation, case,
quote style or landmark edge presentation is counted (disclosure branch) **and**
separately reported in Summary/Notes with an exact count; a substantive change in
the same column is never folded into that class.

**Exact end-user generation path.** Compare tab → Direct vs TSN for Highway Log
(both editions), Highway Sequence (both editions), Intersection Detail (both
editions), Ramp Detail (PDF); the ArcGIS tab's Clean Road comparison; then the By
Day and Everything vs-TSN matrices for the same families. Both twins.

**Source-truth recount.** Re-derive each family's class membership independently
from raw (not from the product's classifier), and prove the disclosed count
equals the independently derived count exactly — 1,243 / 11 / 2 / 1 / 5 per the
finding, restated as measured on the frozen inputs. **No corrected differing-row
total may be asserted** (affected rows may also differ in other fields — the
finding forbids it).

**Values / formulas and installed-Excel checks.** Both twins per family;
installed-Excel recalculation clean; under disclosure, headline totals are
unchanged and the new class line is additive.

**Workbook visual / presentation checks.** The class line is legible in Summary
and Notes on the merged HF-02 base and cannot be mistaken for the substantive
total.

**Evidence.** The `_quote_note` clarifier still fires for KER 046; evidence
behaviour is otherwise unchanged from HF-05's ruled state.

**Neighbouring-family regression.** All five families plus every other family's
Summary (the shared hook must be inert where unset): full gate plus
`check_compare_equality_policy.py`, `check_compare_audit.py`,
`check_tsn_description_leak.py`, `check_clean_road.py`, and every affected
family's `check_compare_*`.

**Measurable acceptance criteria.**
1. Summary and Notes disclose the representation-only class and its exact count
   separately from substantive differences, per family. (The oracle's
   normalization alternative is closed by owner ruling.)
2. **Every affected cell is still flagged**: each of the 1,243 ×2 / 11 ×2 / 2 /
   1 ×2 / 5 cells keeps its red `D` state, and every published differing-cell and
   differing-row total is **numerically unchanged** from pre-fix, proved per
   family.
3. The disclosed counts equal an independently derived census.
4. No equality change of any kind; no corrected differing-row total asserted.
5. The `_quote_note` behaviour is preserved.
6. Families that do not set the hook are byte-identical.
7. Full gate green; every new fixture fails pre-fix.

**Rollback.** Revert the merge commit; because no count moves, this only removes
the disclosure lines and cannot change any verdict.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-09\`;
`hotfix-bundles/HF-09/witness/` for the per-family independent class census and
the disclosure/count table.

---

### HF-10 — Cross-environment PDF-vs-PDF evidence capability

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-10` / `env-evidence` |
| Branch | `hotfix/hf-10-env-evidence` |
| Priority / order | 10 |
| Depends on | **HF-05** (the eligibility/binding/targeting contract must exist first) |
| Findings | **PCOA-FINAL-007** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** (found the five absent-but-required cells) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** Evidence for the five Everything ENV cells that compare PDF
against PDF — Ramp Summary, Ramp Detail (PDF), Intersection Detail (PDF),
Highway Log (PDF), Highway Sequence (PDF) — the one configuration the audit rule
calls `REQUIRED`.

**Explicitly out of scope.** Ramp Summary **vs TSN** (correctly approved as a
prohibited absence); Baseline and PDF-vs-Excel lanes unless the owner extends
scope; any change to the env comparisons' counts; the vs-TSN and SELF evidence
rules settled by HF-05.

**Verified root cause.** An unimplemented capability, not a failed generation:
`matrix_build.build_cell_comparison:561` takes **no** evidence argument, and
`visual_evidence` has only `FLAVOR_TSN` and `FLAVOR_SELF` (`:159-161`), so no
env-flavored path exists anywhere; no artifact exists under the env, baseline or
PDF-vs-Excel trees.

**Files expected to change.** `scripts/visual_evidence.py` (a third flavor),
`scripts/matrix_build.py` (`build_cell_comparison` + an env evidence entry
point), `scripts/matrix_state.py` / `scripts/gui_matrix.py` (toggle, camera,
freshness gating), the `scripts/ui/` matrix pages, plus checks.

**Migration / compatibility.** The env lane's comparison output must not change:
evidence is additive decoration and a failed decoration must never fail a
comparison (the existing contract). The new flavor must satisfy HF-05's
exact-source rule at birth and reuse the same targeting and panel code, not a
parallel renderer.

**Tests to add.** Extend `check_visual_evidence.py`, `check_matrix.py` and
`check_evidence_manifest.py`: an env PDF-vs-PDF cell with positive differences
produces a bound manifest, workbook and image set with a PDF-only read set that
passes the exact-source test; a cell whose sides are not both PDFs produces
nothing; and the env comparison's counts are unchanged with evidence on or off.

**Exact end-user generation path.** Everything ENV matrix → evidence toggle on,
plus the per-cell camera, for all five cells.

**Source-truth recount.** Each rendered example bound back to the published
comparison cell and to both raw prints; the five cells' difference counts
re-derived and shown unchanged (Ramp Summary 67; ID-PDF 17,562; RD-PDF 376 +
5/8 one-sided; HL-PDF 88,238 + 2,095/1,174; HSL-PDF 1,904 + 7/246).

**Values / formulas and installed-Excel checks.** The matrix path writes the
values workbook and settles a live-formulas twin only when `also_formulas` is set
and the twin's inputs are unchanged (`build_cell_comparison` →
`_settle_formulas_twin`); assert that behaviour is unchanged with evidence on, and
that installed Excel opens the evidence workbooks clean.

**Workbook visual / presentation checks.** Every evidence workbook's sheets and
Ledger inspected at native scale.

**Evidence review requirement.** **Every** image in all five sets inspected
individually — accurate target, legible crop, correct caption, read-set member
equal to the compared document. Absence, or relabelling a supported comparison
`N/A`, does not pass.

**Neighbouring-family regression.** The vs-TSN and SELF evidence lanes settled by
HF-05 must be unchanged; the classic Compare tab and PDF-vs-Excel by-day matrix
must still emit nothing: full gate plus every `check_evidence_*`,
`check_matrix*.py`, `check_day_matrix.py`, `check_baseline_matrix.py`,
`check_pdf_excel_matrix.py`.

**Measurable acceptance criteria.**
1. All five cells produce a bound manifest, evidence workbook and image set with
   a PDF-only read set passing the exact-source test.
2. 100 % of retained crops accurate and readable, reviewed individually.
3. Env comparison counts identical with evidence on and off.
4. No other lane's evidence behaviour changed.
5. Full gate green; the new assertions fail pre-fix.

**Rollback.** Revert the merge commit; the capability disappears and the five
cells return to absent-and-required. No data migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-10\`
(all five image sets); `hotfix-bundles/HF-10/witness/` for the per-image verdict
table and the count-invariance proof.

---

### HF-11 — Source-side escalation and must-not-regress guards

| Field | Value |
|---|---|
| Bundle ID / slug | `HF-11` / `source-guards` |
| Branch | `hotfix/hf-11-source-guards` |
| Priority / order | 11 — program closeout |
| Depends on | HF-06, HF-09 (the guards must lock the final parser/comparator state) |
| Findings | **PCOA-FINAL-020** (P1, source-side), **-021** (NO FIX), **-022** (NO FIX) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to `source-audit/prior-7.9-highway-log-sibling-raw-source-audit.json` (its own 021 witness) and to Claude's `witness\pdf_head_census.txt` for 022 |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | BLOCKED |

**Exact scope.** Turn two prose regression guards into executable checks, and
create the owner-facing vendor escalation record for route 140. **No product
behavior change.**

**Explicitly out of scope.** Synthesizing route 140's missing columns, or any
workaround that masks a vendor data defect; changing either parser's behaviour;
adding Highway Detail coverage (**pre-release**).

**Verified basis.** 021: route `074` @ `000.000` occurrence 2 (prior 7.9 raw PDF
page 7 line 31) and route `101` @ `R022.828` (page 142 line 23) are genuine
PDF-only source rows the PDF path correctly retains; they must never be
synthesized into the Excel-derived universe. 022: a stray leading `GENERATE` line
now precedes four print families and the Highway Sequence Listing (PDF) print was
re-skinned to the TASAS layout with a wider text measure; the parser absorbs both
(route 001 → 2,581 rows new, 2,583 prior) and must keep supporting **both**
layouts. 020: `highway_log_route_140.xlsx` leaves `R/U`, `TER`, `H/G`, `A/C`
blank on all 213 rows where its own print carries values — vendor action, not a
product fix.

**Files expected to change.** `build/check_*.py` (two new or extended guards),
`docs/` (the vendor escalation record and a pointer from the reports/Highway Log
docs), `CHANGELOG.md`. No `scripts/` change is expected; a reviewer should reject
one unless the guard cannot otherwise be written.

**Tests to add.** A parser guard that produces correct row counts for both the
pre- and post-re-skin Highway Sequence print layouts and ignores the leading
`GENERATE` line on all four affected families; and a source-universe guard that
the two PDF-only rows are retained in the PDF-derived universe and absent from
the Excel-derived one. Both must fail against a deliberately reverted parser /
universe rule.

**Exact end-user generation path.** Consolidate tab → Highway Sequence (PDF) from
both a pre-re-skin and a post-re-skin print; Compare tab → classic environment
Highway Log, both editions, over the two days that exhibit the four-route delta.

**Source-truth recount.** Re-verify both PDF-only rows at their original PDF
page/line; re-verify route 140's blank columns against the raw export and its
print; re-derive the four-route delta (net −14 / +2) reconciling 89,811 and
88,238 differing cells.

**Values / formulas and installed-Excel checks.** One Highway Log classic-env
pair regenerated in both twins to confirm the universe rule and counts are
unchanged.

**Workbook visual / presentation checks.** None beyond confirming the regenerated
pair is unchanged.

**Evidence.** Unchanged.

**Neighbouring-family regression.** Highway Log and Highway Sequence, both
editions: full gate plus `check_compare_highway_log.py`,
`check_compare_env_highway_log*.py`, `check_compare_highway_sequence*.py`,
`check_tsn_district_source_contract.py`.

**Measurable acceptance criteria.**
1. Both guards exist, fail on a deliberate regression, and pass on `main`.
2. No `scripts/` behaviour change (or an explicitly justified minimal one).
3. The vendor escalation record exists, names the exact witness, and states the
   on-delivery acceptance test (route 140 self check reports zero
   `X ≠ (blank)` on `R/U`, `TER`, `H/G`, `A/C`).
4. All Highway Log / Highway Sequence counts unchanged.
5. Full gate green.

**Rollback.** Revert the merge commit; only guards and docs disappear.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-11\`;
`hotfix-bundles/HF-11/witness/` for the two row-level source traces and the
route-140 raw census.

---

## Branch and worktree lifecycle

1. **Planning (this stage).** `planning/post-comparison-hotfix-bundles` off
   `main`, documentation only. On joint agreement it merges to `main` without
   force (after confirming remote `main` has not diverged) and is deleted.
2. **Per bundle.** From the latest `main`:
   `git worktree add ../TSMIS-hotfix-<id> -b hotfix/<bundle-id>-<slug> main`.
   A separate worktree is preferred so the user's normal checkout stays usable;
   never switch or clean a dirty user worktree.
3. **During Stage 4.** Only that bundle's agreed surface changes. The branch is
   pushed if the remote is available and unchanged. It is never merged by the
   implementer.
4. **During Stage 5.** A `DENIED` review returns to Stage 4 on the **same**
   branch. Two approvals with at least one non-implementer approver are required
   to merge.
5. **On merge.** Fetch, confirm `main` has not diverged, merge without force, run
   the post-merge smoke check (`build/run_checks.py -j 4 -k` plus
   `build.ps1 -SelfTest`) on `main`, push, then remove **only** that bundle's
   worktree and fully merged branch (`git worktree remove`, `git branch -d`,
   `git worktree prune` if a stale entry lingers).
6. **Always preserved.** `main`, `gh-pages`, unrelated branches, every Stage 1/2
   audit root, and all `hotfix-bundles/**` records.
7. **Next bundle** branches from the newly updated `main`, never from a previous
   hotfix.

## Acceptance inputs and retained-witness policy

| Item | Location | Rule |
|---|---|---|
| Frozen source archive | `2026-07-23 ssor-prod.zip`, SHA-256 `217F172F7EF7DB527A1EF30E2BFD12D1D6B810BCA55C0D38B7733CB4BE74266F`, 152,681,267 bytes | The acceptance input for every bundle. Re-verify the hash before a bundle's acceptance run |
| Extracted run folders | `output\2026-07-23 ssor-prod`, `output\2026-07-09 ssor-prod`, `output\2026-07-09 ars-prod` (git-ignored) | **Retain until the program's definition of done is met.** `START-HERE.md` calls them safe to delete; they are now the by-day / Baseline / PDF-vs-Excel matrix inputs for every bundle's acceptance run. Release them only after closeout |
| TSN libraries | `tsn_library\<report>\raw\` → the library's normalized copies | Rebuild once per bundle that needs it; a normalizer change requires a `normalization_version` bump and a re-bless |
| ArcGIS layers | `arcgis_layers\` (40-layer library) | HF-01's build input; as-of date = the TSN extract's own date |
| Ground-truth oracle corpus | `C:\Users\Yunus\Downloads\TSMIS\ground-truth\…` | Read `_INDEX.md` first. `ground-truth/` is the acceptance oracle; `report-samples/` is for parser spot checks; `comparison-outputs/` is historical reference; `_scratch/` is disposable and must never become an oracle |
| Bulk hotfix outputs | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\<HF-ID>\` | Local only. Never write into a Stage 1/2 audit root — audit evidence is immutable |
| Committed witnesses | `hotfix-bundles/<HF-ID>/witness/` | Small machine-readable JSON/text only, so a reviewer can bind without the local corpus (the pattern Stage 2 used with `stage2-*.json`) |
| Never committed | `scripts/tsmis_auth.json`, generated `output/`, build artifacts, any real TSMIS data or site source | Project rule; the site source is Caltrans-internal |

**Environment reality.** Every bundle's acceptance runs from the frozen archive
on the dev PC — none needs TSMIS intranet access. Live-export and IT/DLP
behaviour remain owner-only work-PC items and are **not** gates for these
bundles. The owner's outstanding v0.32.0 work-PC acceptance run is tracked
separately in [the backlog plan](../v0.30-owner-backlog-plan.md) and is not
blocked by this program.

## Definition of done — whole program

1. All eleven bundles read `MERGED`, each implemented by Claude and approved by
   two Codex reviews — so every bundle has two adversarial approvals and no
   approver was its implementer.
2. Every canonical finding's acceptance oracle is demonstrated on the frozen
   archive, with its committed witness under `hotfix-bundles/<ID>/witness/`.
3. The 88-decision topology is re-adjudicated: every decision denied in Stage 2
   is `APPROVED`, or is explicitly carried as a deferred item with a stated
   reason. The 16 `BLOCKED` stay governed by DEF-02/DEF-03 and the 4 in-topology
   `N/A` by PCOA-FINAL-018's outcome and DEF-04.
4. The 25-cell evidence registry is re-adjudicated under the owner's ruled
   evidence policy, with the ruling recorded.
5. The full gate is green on `main` at the final merge:
   `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k`, `compileall`,
   `ruff`, `build.ps1 -SelfTest`.
6. Every canary a bundle moved is re-blessed with a documented delta and exact
   input/output evidence in
   [`comparison-canary-bindings.md`](../comparison-perfection/comparison-canary-bindings.md)
   — `CRH-SW-E2` at minimum.
7. `CHANGELOG.md` and the owning `docs/` topics
   ([comparison-engine.md](../../comparison-engine.md),
   [reports.md](../../reports.md),
   [cleanroad-highways.md](../cleanroad-highways.md)) describe the shipped
   behaviour, and `CLAUDE.md`'s snapshot no longer describes superseded
   behaviour.
8. PCOA-FINAL-020 is escalated to the vendor with a tracked record and an
   on-delivery acceptance test.
9. `START-HERE.md` records the program as complete, and the retained
   `output\…` acceptance folders are explicitly released.
10. No `hotfix/*` branch or worktree remains; `main` and `gh-pages` are intact.

## Planner challenge log

| Question or disputed bundle boundary | First planner position (Claude) | Second planner challenge | Source-backed resolution |
|---|---|---|---|
| Split presentation into statewide-summary and large/detail, as the prompt's likely shape suggests? | **No.** Both classes are produced by the same `compare_core` writers; both need `_write_summary`'s `B` width (`:2998`) and the composite key column (`:2015`, `:2170`). Two branches would edit the same statements | PENDING | PENDING |
| Should Clean Road (HF-01) also carry its own clipping fix so the user's sheet is complete in one bundle? | **No.** Clipping is one canonical finding (009) covering every family; fixing it inside HF-01 would put shared-writer changes in bundle 1. Instead HF-02 is sequenced second and must regenerate the merged HF-01 pair as its witness | PENDING | PENDING |
| HF-01's design: can the 161 false positives fall to zero without an engine hook? | **Probably not.** Disclosure alone satisfies oracle branch (b) but not its second sentence. The recommended path marks the skipped anchors non-asserting via one opt-in `CompareSchema` field, on the per-cell ditto `N` precedent (`compare_core.py:1648-1650`). Odometer-based placement is forbidden by the build model | PENDING | PENDING |
| Normalize or disclose the Highway Sequence self-check equates (HF-06)? | **RULED AND CLOSED by the owner, 2026-07-26 after reviewing the rendered cells: NORMALIZE to zero.** Route 001's five differing cells are the moved `E` suffix, the non-repeated HG/FT, and a prepended `EQUATES TO` — none is a disagreement about the road, and the print's red/green equate colouring cannot exist in an XLSX at all. Must be pair-aware (a per-cell rule cannot close `PM Suffix`), opt-in, proved by an independent oracle over all 60,254 rows, with vs-TSN counts frozen and an anti-suppression fixture per case | N/A — settled by the owner on rendered evidence | N/A |
| Isn't that inconsistent with the HF-09 ruling? | **No — the two classes differ in kind, and the owner ruled each on its own evidence.** HF-09 is two independent sources ten months apart whose text genuinely differs (`,` vs `/`) → stays flagged. HF-06 is one pull rendered twice, where every piece of information is present on both sides but placed differently within a two-row pair → normalized. HF-06 must not widen into the HF-09 class | N/A | N/A |
| Disclosure or normalization for representation-only Description differences (HF-09)? | **RULED AND CLOSED by the owner, 2026-07-26: disclosure only — the cells stay flagged and counted.** The comma-vs-slash Highway Log class (1,243 per format) and its siblings keep their red `D` state and stay in every total; HF-09 adds a count line and may not touch equality. This matches Stage 2's refusal to impose a new equality rule and the shipped `_quote_note` decision | N/A — settled by the owner | N/A |
| Is the audit's evidence-eligibility rule a product requirement (HF-05)? | **Escalate, do not decide.** Applied literally it retires nearly the whole shipped evidence feature, including CMP-AUD-210's Excel-side binding and v0.32.0's `excel_column_for`. The finding's own oracle (exact-source binding) is satisfiable without that. Recorded as an owner policy gate; absent a ruling, implement the oracle | PENDING | PENDING |
| 001 and 012 in one bundle? | **Yes, mandatory.** 012 is unobservable until 001 lands and the finding states that fixing 001 alone creates a new defect (108 false discrepancies on a same-source check) | PENDING | PENDING |
| 015 and 018 together — unrelated fixes? | **Accepted as one bundle.** Two disjoint files, no workbook/count/image effect, one coherent theme (tell the user immediately, and tell them at all). If the second planner disagrees, split into HF-07a/HF-07b without changing any other boundary | PENDING | PENDING |
| Per-bundle `BUNDLE.md` at Stage 3 or Stage 4? | **This plan's section is the frozen contract**; `BUNDLE.md` is transcribed from it at the start of each Stage 4 with only base SHA/implementer/reviewer filled. Writing eleven near-duplicate contracts now would create a second authority that drifts — the failure mode the predecessor project logged repeatedly. `HF-01/BUNDLE.md` exists because it is the first `READY` bundle | PENDING | PENDING |
| Who implements and who reviews? | **Settled by owner decision (2026-07-26): Claude implements all eleven bundles; Codex performs both reviews on every bundle.** Codex is therefore never the implementer, so Prompt 05's "at least one non-implementer approver" holds everywhere and Claude never approves its own work. The cost is that both reviews come from one agent — review 2 must re-derive independently and name what review 1 missed, not restate it | PENDING | PENDING |
| Does Codex-only review weaken the Claude-unique findings? | **It is a scheduling constraint, not a soundness one.** For PCOA-FINAL-003, -006, -014, -015, -017, -018, -019 and -022 the durable witness is Claude's, but the firewall has ended, the key witnesses are committed in-repo, and Prompt 05 item 5 independently requires the reviewer to recount from raw rather than trust any prior parser. Each affected bundle names the exact witness Codex must bind to | PENDING | PENDING |
| Are eleven bundles too many? | **No.** Each is one implementation pass with one complete adversarial output review, and the map shows only five same-file overlaps, all on disjoint functions in merge order. Fewer bundles would mix normalization behaviour, evidence policy, visual cleanup and source-row correctness — which the prompt forbids | PENDING | PENDING |
| Does any bundle leave `main` unreleasable? | **No.** HF-04 is the only one that changes an input contract, and it must accept both censused layouts rather than swapping one pinned layout for another; HF-08 forces exactly one disclosed re-comparison; every other bundle is additive or presentation-only | PENDING | PENDING |

## Joint planning approval

| Reviewer | Pass | Decision | Commit | Date | Notes |
|---|---|---|---|---|---|
| Claude | First plan | **AWAITING SECOND PLANNER** | this commit | 2026-07-26 | 11 bundles, 22 findings mapped once, overlap map built from code inspection at `a29bdb6` |
| Codex | Final challenge | NOT STARTED | PENDING | PENDING | |

No implementation begins until both decisions are `APPROVED`, every finding is
mapped exactly once, and HF-01 is marked `READY`. Then use
[Prompt 04 — implement a hotfix bundle](prompts/PROMPT-04-IMPLEMENT-HOTFIX-BUNDLE.md).
