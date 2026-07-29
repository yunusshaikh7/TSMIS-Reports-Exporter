# `RB-1` — Adversarial Review Record

Status: **MERGED** — `560ea5e501fdd76003985753ba7fc9ff0a551320`

## Review identity

| Field | Value |
|---|---|
| Bundle / work item | `RB-1` / `HF-01` |
| Reviewed branch | `hotfix/rb-1-clean-road-source-truth` |
| Recorded base `main` | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` |
| Original denied head | `a26725b59a5dc5c9445d43af03c9a3ea4041b484` |
| Review-return implementation | `84b82de` plus SHA-recording follow-up |
| Review 1 reviewed head | `6d2a2ce2e70688bfaa20e8f2e11039165742d55e` |
| Review 1 record head | `c90908d73e22bf945c4d85484465350ae2882c22` |
| Review 2 requested / record head | `d330312efc949523caf07f1fec4e867afed87cf7` |
| Runtime code head | `84b82de2873f733864b1da3cad037738e898be8d` (no runtime/test/witness change through `d330312`) |
| Review 2 remedy runtime head | `39c5dc3d15501a428a42b0eb0c3cbe0d499b09fd` |
| Review 2 re-review requested / record head | `12d43d86fda19813c688305f2435cda840fa11c9` |
| Implementer | Claude |
| Approving reviewer | Codex — independent; did not implement this bundle |
| Review 2 | Codex — independent; did not implement this bundle; **DENIED — RETURN TO IMPLEMENTATION** |
| Review 2 re-review | Codex — independent; did not implement this bundle; **DENIED — EVIDENCE GAP** |
| Review 2 final re-review | Codex — independent; did not implement this bundle; **APPROVED** |
| Merge | **MERGED** — `560ea5e501fdd76003985753ba7fc9ff0a551320` |

## Review 1 verdict

**APPROVED.** RB-1 satisfies its frozen PCOA-FINAL-010 contract at the exact
reviewed head. The 102 unplaceable source spans are recorded and disclosed,
all 174 affected build anchors carry the explicit unavailable token, all 165
paired positions are non-asserting `N`, the nine one-sided positions remain
`U`, the 161 false positives fall to zero, and the four genuine raw-source
disagreements remain itemized diagnostic facts. The statewide differing-cell
total is exactly **291,127 = 291,292 − 165** with no unexpected asserting or
published-cell change.

The prior blocking finding `RB1-R1-001` is closed. The regenerated
`ArcGIS Build` sheet is an itemized **111-row × 14-column** disclosure with
purposeful widths, wrapped cells, and sufficient stored row heights. Installed
Excel's font metrics report zero narrow columns and zero short wrapped rows;
both native-scale and fit-width PDFs pass page-by-page inspection.

No runtime scope leakage was found. The Prompt 04 change only makes the already
specified denial-return loop executable, and the status/record/witness changes
are required workflow support.

## Commands and source inputs

| Purpose | Reviewer command / method | Result |
|---|---|---|
| Preconditions / exact scope | `git status --short`; `git rev-parse HEAD`; `git diff --name-status --stat --check 9c774d4…..6d2a2ce…`; branch/worktree/origin checks | **PASS** — clean exact head; base and head match the implementation record; retained artifacts present |
| Targeted head tests | `build\.venv\Scripts\python.exe` running `check_clean_road.py`, `check_compare_equality_policy.py`, `check_compare_audit.py`, `check_comparison_artifact_schema.py`, and `check_compare_ditto.py` | **PASS** — all five |
| Required base-red proof | Archived exact base `9c774d4…`, copied only the current `build/check_clean_road.py`, ran it against base scripts | **PASS** — 24 HF-01 failures, including the defect signature `got 3` differing cells instead of `1`; exact head is fully green |
| Full gate | `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k` | **PASS** — 157 / 157 in 109.5 s |
| Compile / lint / frozen app | `python -m compileall -q scripts build`; `uvx ruff check scripts --select E9,F63,F7,F82,F811,F401`; `powershell -File build\build.ps1 -SelfTest` | **PASS** — compile clean; Ruff “All checks passed”; exact frozen executable `SMOKE OK` |
| Relevant failure / publication paths | `check_compare_build_freshness.py`; `check_consolidate_worker_publication.py`; `check_consolidate_toctou.py`; `check_comparison_publication.py` | **PASS** — stale snapshots fail closed; producer certificates survive; TOCTOU declines preserve appeared files; interrupted metadata leaves the workbook untrusted |
| Real end-user generation | Reviewer driver invoked `GuiApi.start_arcgis_build` → `ConsolidateWorker` → GUI terminal, then `GuiApi.start_arcgis_compare` → normal compare worker/terminal; only the native save dialog returned one absent destination | **PASS** — both endpoint replies `ok`; both terminal results `status=ok`, `completion=partial`; zero GUI errors; build and both twins committed |
| Independent source/value audit | Reviewer-owned openpyxl/OOXML scanner over all raw ArcGIS span layers and the frozen pre/post build and values workbooks; imports no product module and does not consume implementation witness counts | **PASS** — exact 102/174/165/9/161/4 relationships; zero unexpected build, comparison, or layout change |
| Formula structure / cached results | Reviewer-owned all-sheet streaming OOXML census plus installed Excel 16 cached-result audit of the retained successful full-rebuild twin; twins opened sequentially, read-only | **PASS** — 6,507,937 formula cells; zero cached errors; exact 291,127 / 50,012 totals; 174/174 target parity; zero Summary/Spot Check/Comparison error cells |
| Native visual audit | Installed Excel font-metric measurement and PDF export; all six rendered pages inspected; prior passed comparison-sheet renders bound to the fresh twin by a complete non-Provenance lockstep audit | **PASS** — all required sheets pass; details below |
| Unaffected-family regression | Reviewer-owned lockstep audit of same-day base/head Intersection Summary values workbooks and typed sidecars | **PASS** — every non-Provenance cell equal, hidden states/dimensions equal, typed payload SHA equal |

The GUI wrapper returned a nonzero console status only after it had written the
complete result JSON, because the CP1252 console could not echo the Unicode
`✗` verdict character. The recorded application endpoints and GUI terminal
results are both successful; this is a reviewer-harness display issue.

### Exact identities

| Input / artifact | Bytes | SHA-256 |
|---|---:|---|
| ArcGIS layer index `arcgis_layers\00_INDEX.xlsx` | 6,993 | `CCD1BDFFC0A122797B95B73CF311D5CB6B8996B7BB55AFDD742A2C4F2CF23ABE` |
| TSN raw `CA HIGHWAYS 09.08.2025.xlsx` | 21,290,781 | `BBD1ACF9D4A8FEF86F96A0A2CF54BE1105E8C919600DBCD05A325B194F5C86E5` |
| TSN normalized input | 14,864,394 | `7F1086FEAFE061531B682B12D0DDA161F5256DF50FCC89A954DF8B87A4656AAB` |
| Frozen pre-fix build | 10,824,390 | `8F9766AC75E3F1CD10729B6090FE2532DA90C821776D3114E28F65DF70BA6376` |
| Frozen pre-fix values comparison | 199,766,125 | `A59177DCDAFCD46369D6438E7773B16A18A3175BCEA11AA347395CE874E493C5` |
| Reviewer fresh build | 10,833,363 | `5BB7B5AB96FA8293280C5C82F57EA44CA2870CB7F8B459F8A8099724024EAE03` |
| Reviewer fresh values twin | 199,821,558 | `90FEF8BF17F96877A6C1584EC292A06994EAD224A8B3283A53B88297CE387B81` |
| Reviewer fresh formulas twin, before recalculation | 468,206,168 | `3B022E5ED951D26CA4750AB6CC45204F2592269C2FBD8010E629CC18217B1455` |
| Retained successful installed-Excel recalculation | 581,844,790 | `F7412CA0D96E926E0CCC8B3CC3B224BB382A88676CD6588B78B4F494B3B2BEAE` |
| Native `ArcGIS Build` top, 100% | 222,771 | `13935BE3CAA445F6655664D050CE2A53E0CB1357112DB8AACF6B403F23E95368` |
| Native `ArcGIS Build` full, fit width | 315,535 | `4EDAE7A64256FB1E923B0543E5FD1D5DC7A6C3259B40B7F50FAD288338205C1C` |

Raw ZIP hashes differ across valid generations because timestamps,
provenance paths, and Excel formula caches are run identity. Published
cells/states, typed payloads, layout, and exact source bindings are the
acceptance invariants.

Reviewer outputs are retained at:

`C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\r1-codex-rereview\`

The implementation's successfully recalculated twin remains at:

`C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\r1-remedy\`

## Contract and diff audit

| Check | Result | Evidence / notes |
|---|---|---|
| PCOA-FINAL-010 fixed | **PASS** | Exact source and discrepancy matrix below |
| No out-of-scope runtime change | **PASS** | Shared `CompareSchema.unavailable_rule` defaults inert; only Clean Road opts in; unchanged Intersection Summary is semantically identical |
| Allowed implementation surface | **PASS** | Producer, Clean Road comparator, one additive shared schema hook, dedicated test, canary, records, and witnesses |
| Migration / prior build behavior | **PASS** | Older/skip-free builds retain plain-schema behavior; skip-free control stays `COMPLETE`; real run propagates `PARTIAL` |
| Atomic publication / stale state | **PASS** | Same generation ID and typed payload on both fresh twins; provenance binds exact build/TSN hashes; stale snapshot and interrupted-publication checks fail closed |
| Rerun / idempotency | **PASS** | Fresh re-generation matches the first-review twin on every non-Provenance cell except the expected Summary created date; typed payload hash is identical |
| Performance | **PASS** | Full data GUI build plus both twins completed in 2,659 s; no changed subsystem exceeded its operation budget |
| Evidence policy | **PASS** | Zero `*evidence*` files before, after, in the delta, and across the complete fresh output tree |
| Canary | **PASS** | `CRH-SW-E3` records the exact −165 delta, per-field deltas, input identities, and supersession of E2 |

## Independent source and discrepancy results

| Measure | Independent result |
|---|---:|
| Raw span layers / live as-of span rows scanned | 26 / 207,602 |
| Skipped raw rows | **102** |
| Layer split | 100 `SHS Travel Way L`; 2 `SHS O Shld Width R` |
| Endpoint / `LocError` | 101 known begins; 1 known end; all `NO ERROR` |
| Usable AR / odometer pairs | 102 / 100 |
| Expected / actual build tokens | **174 / 174** |
| Missing / unexpected tokens | **0 / 0** |
| Build-data changes / unexpected changes | **174 / 0** |
| Paired / one-sided affected positions | **165 / 9** |
| Exact false positives | **161 → 0** |
| Genuine raw-source disagreements | **4**, still itemized and non-asserting |
| Differing cells | **291,127** |
| Paired / ArcGIS-only / TSN-only rows | **52,647 / 5,081 / 7,436** |
| Differing / identical paired rows | **50,012 / 2,635** |
| Unexpected comparison display/state/count changes | **0** |
| Unexpected layout changes | **0** |

The four diagnostic raw disagreements remain at Comparison rows 19,119 and
19,122 for `THY_LT_TRAV_WAY_WIDTH_AMT` and `THY_LT_LANES_AMT`; each is rendered
with the explicit unavailable token and state `N`, not a fabricated value or
asserting difference.

## Values, formulas, visual, evidence, and regression matrix

| Gate | Result | Evidence / notes |
|---|---|---|
| Values twin | **PASS** | Exact 291,127 total; all 174 target displays/states correct; zero unexpected published change |
| Formulas twin | **PASS** | Retained Excel full-rebuild hash `F7412CA0…`; independent OOXML has zero cached errors; installed Excel cached read has 174/174 parity, exact counts, and zero errors |
| Formula self-check | **PASS** | Summary rows 102–111 are ten exact `OK` results; zero exact `CHECK` or error cells on Summary/Spot Check |
| PDF/Excel sibling parity | **N/A** | Clean Road has no PDF edition |
| Evidence images/crops | **N/A** | Clean Road has no evidence adapter |
| Mixed-format evidence leakage | **PASS** | Zero prohibited evidence artifacts |
| Unaffected-family regression | **PASS** | Every non-Provenance Intersection Summary cell equal; both snapshots remain `veryHidden`; typed payload `f7e3296d…` equal; completion `complete` |
| Full regression gate | **PASS** | 157/157, compileall, focused Ruff, frozen executable self-test |

One reviewer-owned full-rebuild attempt on the fresh formulas twin was stopped
after 34 minutes when Excel reached an 8.6 GB working set and host free memory
fell below 1 GB. The workbook had not saved and its hash remained unchanged, so
no pass is claimed from that attempt. Acceptance instead rests on the retained
successful installed-Excel full rebuild, independently checked by all-sheet
OOXML and a resource-safe sequential Excel cached-result audit. This is
transparent reviewer-host safety handling, not a product failure.

### Required native-sheet inspection

| Sheet | Result | Notes |
|---|---|---|
| Summary | **PASS** | 102 skips, 174 anchors, reason, partial status, exact totals, and ten `OK` self-checks remain legible; fresh twin differs from the passed first-review render only by the created date |
| Notes | **PASS** | Skipped-source disclosure is first and fully readable; fresh sheet is cell-for-cell identical to the passed first-review render |
| Comparison | **PASS** | Markers remain visually distinct from genuine red `≠` differences, are excluded from `Diffs`, and freeze/filter/state-mask behavior is unchanged; fresh sheet is cell-for-cell identical |
| ArcGIS Build | **PASS** | Fresh 111×14 sheet; Excel metric oracle: zero narrow columns, zero short wrapped rows; native 100% and full fit-width PDFs inspected on every page |
| Provenance | **PASS** | Exact build and TSN paths/hashes plus producer `partial` are readable; only expected run-identity values changed |

## Finding disposition

| ID | Priority | Original finding | Disposition |
|---|---|---|---|
| RB1-R1-001 | P1 / blocking | New `ArcGIS Build` disclosure was clipped at default widths/heights | **CLOSED** — itemized 14-column table, stored widths, wrapping, sufficient row heights, fresh Excel metrics/PDF inspection green |

The pre-existing `_cancelled(events)` call-shape defect remains present at the
base and is outside RB-1. It is not charged to this bundle.

## Approval history

| Review event | Reviewer relationship | Decision | Reviewed commit / timestamp |
|---|---|---|---|
| Review 1 attempt 1 | Codex; independent non-implementer | **DENIED — RETURN TO IMPLEMENTATION** | `a26725b59a5dc5c9445d43af03c9a3ea4041b484` / `2026-07-28T00:03:08.6792773-07:00` |
| Review 1 re-review | Codex; independent non-implementer | **APPROVED** | `6d2a2ce2e70688bfaa20e8f2e11039165742d55e` / `2026-07-28T08:26:47.3070509-07:00` |
| Review 2 | Codex; independent non-implementer | **DENIED — RETURN TO IMPLEMENTATION** (`RB1-R2-001`) | `d330312efc949523caf07f1fec4e867afed87cf7` / `2026-07-28T14:12:09.5621720-07:00` |

**Reviewer signature:** Codex, Review 1 — APPROVED —
`2026-07-28T08:26:47.3070509-07:00`.

## Review 2 — Codex, 2026-07-28

### Verdict

**DENIED — RETURN TO IMPLEMENTATION.** Review 2 found one concrete failure of
the controlling HF-01 acceptance contract:

`IMPLEMENTATION-PLAN.md` criterion 7 requires the four genuine raw-source
disagreements to remain itemized in **Summary/Notes and the retained witness**
as unavailable, non-asserting source facts. The retained witness itemizes them,
but the reviewed comparison's Summary and Notes do not. They disclose only the
aggregate 102 skipped spans, 174 marked anchors, and missing-postmile reason.

The four required identities are route `036`, county `TEH`, postmiles `40.15`
and `40.352`, for `THY_LT_LANES_AMT` and
`THY_LT_TRAV_WAY_WIDTH_AMT` (Comparison rows 19,119 and 19,122). A bounded
read-only probe of the retained values twin found zero occurrences of `036`,
`TEH`, `40.15`, or `40.352` in either Summary or Notes. The implementation
matches that result: `_schema_for` and `_disclosure_lines` emit only aggregate
coverage prose.

This is not an evidence gap and does not contradict the passed count/state
work. It is a user-facing acceptance failure in the workbook text, so Prompt
05 requires return to Stage 4.

### Review identity and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 2 |
| Implemented bundle? | **No** |
| Branch | `hotfix/rb-1-clean-road-source-truth` |
| Recorded base | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` |
| Runtime code head | `84b82de2873f733864b1da3cad037738e898be8d` |
| Review 1 approved head / record | `6d2a2ce2e70688bfaa20e8f2e11039165742d55e` / `c90908d73e22bf945c4d85484465350ae2882c22` |
| Requested review-record head | `d330312efc949523caf07f1fec4e867afed87cf7` |
| Runtime equivalence | `c90908d..d330312` changes only `START-HERE.md`, `IMPLEMENTATION-PLAN.md`, and Prompt 05; runtime, tests, witnesses, and retained workbook semantics are unchanged |
| Elapsed active review | 26 minutes |
| Resource budget | **RESPECTED** — no generation, recount, Excel recalculation, build, or whole-corpus run; the only workbook probe was read-only, completed in 101 seconds, and created no output; the copied retained PNGs total under 4 MB |

The desktop image viewer failed on the retained PNGs with a Windows sandbox
ACL-helper error. This is recorded as a reviewer-environment failure, not a
product failure. Review 2 relied on Review 1's signed native-render evidence
and the retained `visual-audit.json`, as the owner-approved bounded-review
policy permits; the denial does not depend on visual layout.

### Evidence reused and bounded commands

| Evidence / command | Binding / result |
|---|---|
| Complete branch diff | `git diff --name-status --stat --check 9c774d4..d330312`; exactly the allowed runtime/test/canary/record/witness surface plus owner-sanctioned Prompt 04/05 workflow support; clean |
| Runtime-equivalence diff | `git diff --name-status c90908d..d330312`; three policy documents only |
| Review 1 signed record | Review 1 approval at `6d2a2ce…`, recorded by `c90908d…`; exact source/count/formula/visual/evidence/regression matrix retained |
| 165-cell recount | `165-cell-before-after-recount.json`, SHA-256 `EDA2B971C19F5B8411D4F84DA7146931D61A96313D04DC7442866C10019ED58D` |
| Four diagnostic facts | `four-raw-source-disagreements.json`, SHA-256 `55E4109BE39E8EEB7B6DB6B84C2A69648017BB3A27BADCFF744752F350D9754F` |
| Formula acceptance | `formulas-twin-recalc.json`, SHA-256 `0BB3B55C404ADFA0EAE45F6D2D54F86C93F776C40C97B8635E3F5C262DD4F934`; retained recalculated twin `F7412CA0…` |
| Build/source truth | `build-diff.json` / `skip-census.json`, SHA-256 `B65F6BF8128CB632F05711DB809A811833DDA8D8C1DF71C61C77E4473D7B1129` / `48135721205CDA801542AFC261B4C013A7FE2C19F9653CAEC25D0064FBBE0441` |
| Neighbor regression | `is-regression.json`, SHA-256 `D703600686EEBF85DD0D1307C5C82CD21F708A30BCFAE240EC6548DE58E892BD` |
| Marker presentation | `r1-marker-excel-metrics.json` / `r1-marker-presentation.json`, SHA-256 `0831A39D0F0D8DC6D39A1C6FD7366E694512D1DA068B0F154707A22E4C62F1D0` / `5E6B704B060D158FC914CF99697D065827423DF7C39729EE4E7DF13B0B5B81CA` |
| Pre-existing Review 2 generation | Runtime-equivalent `c90908d` worktree; manifest-bound build `DB78CA6D…`, values twin `A25F15F7…`, formulas twin `E78C9F0A…`; used only as supplemental retained evidence |
| Targeted adversarial probe | Read-only `openpyxl` scan of Summary and Notes in the retained values twin: aggregate coverage present; zero route/county/postmile identifier hits for the four required facts |

No full gate, statewide regeneration, raw-source recount, Excel rebuild,
application build, or fresh visual capture was repeated.

### Review 2 challenge to Review 1

Review 1 could miss a contract-transcription mismatch: `RB-1/BUNDLE.md`
shortens criterion 7 to say only that the four facts remain itemized, while
`IMPLEMENTATION-PLAN.md` — which both the bundle and the plan declare
controlling — explicitly says they remain itemized in Summary/Notes and the
retained witness. Review 1 proved that the witness and Comparison rows retain
the facts, but did not test their presence in Summary or Notes. Review 2
challenged that exact blind spot by re-reading the controlling criterion,
inspecting the disclosure-producing code, and scanning only those two retained
sheets.

### Acceptance-criterion coverage

| Criterion | Review 2 result | Exact evidence |
|---|---|---|
| 1. 161 false positives become zero | **PASS (reused, no contradiction)** | 165-cell recount; all affected paired positions `D→N`; exact total 291,127 |
| 2. All 165 paired cells show marker and `N` | **PASS (reused, no contradiction)** | Recount plus Review 1 source/value audit |
| 3. Summary and Notes state 102 / 174 / reason | **PASS (targeted probe)** | Both sheets contain the aggregate coverage line |
| 4. Both twins regenerate; formula twin clean | **PASS (owner-accepted implementation evidence)** | `formulas-twin-recalc.json`; retained `F7412CA0…`; no reviewer rebuild required or permitted |
| 5. Canary re-blessed | **PASS (diff inspection)** | `CRH-SW-E3`, exact −165 delta and input identities |
| 6. Full gate; base-red/head-green | **PASS (signed retained evidence)** | Review 1: 157/157 plus compile, Ruff, frozen self-test; runtime unchanged through `d330312` |
| 7. Exact 291,127; no outside move; four facts itemized in Summary/Notes and witness | **FAIL** | Count/no-outside-move and witness itemization pass; Summary/Notes itemization fails |

### Values, formulas, visual, evidence, and regression matrix

| Gate | Result | Notes |
|---|---|---|
| Values / source truth | **PASS (reused)** | 291,127; 165 paired `N`; nine one-sided `U`; four diagnostic facts retained |
| Formulas | **PASS (owner-accepted retained implementation result)** | All SELF-CHECK rows `OK`; zero cached errors; no Review 2 full rebuild |
| Visual | **PASS evidence reused; reviewer viewer failure recorded separately** | Review 1 signed native-scale inspection and marker metric/PDF witnesses remain same-runtime-head evidence |
| Evidence eligibility | **PASS (reused)** | Clean Road has no adapter; zero prohibited evidence artifacts |
| Neighbor regression | **PASS (reused)** | Intersection Summary semantic/state/count/typed witness unchanged |
| User-facing diagnostic disclosure | **FAIL** | Aggregate disclosure only; four required source facts absent from Summary and Notes |

### Actionable finding

| ID | Priority | Failure | Required return |
|---|---|---|---|
| `RB1-R2-001` | P1 / blocking | `IMPLEMENTATION-PLAN.md` HF-01 criterion 7 requires the four genuine route 036 / TEH / 40.15 and 40.352 lane/width facts to remain itemized in Summary/Notes and the retained witness. The witness passes, but both sheets omit every route/county/postmile identity. | In the existing RB-1 comparator surface, itemize all four facts in **both Summary and Notes** as unavailable/non-asserting facts; add a deterministic `check_clean_road.py` assertion for their exact identities; regenerate both comparison twins and the affected native renders; rerun the scoped acceptance matrix and full implementation gate. Preserve all passed counts, states, marker geometry, and neighbor invariants. |

Review 1's `RB1-R1-001` remains **CLOSED**; Review 2 does not reopen the
marker-sheet legibility remedy.


**Reviewer signature:** Codex, Review 2 — DENIED — RETURN TO IMPLEMENTATION —
`2026-07-28T14:12:09.5621720-07:00`.

Do not merge. Resume Prompt 04 on the existing
`hotfix/rb-1-clean-road-source-truth` branch with:

```text
<BUNDLE_ID> = RB-1
<IMPLEMENTER> = Claude
```

## Review 2 re-review — Codex, 2026-07-28

### Verdict

**DENIED — EVIDENCE GAP.** Prompt 05 requires every expensive acceptance
operation to be represented by a retained, hash-bound result before review.
The Review-2 remedy's installed-Excel `CalculateFullRebuild` result is retained
and its checks are recorded, but the accepted post-recalculation workbook is
not bound by SHA-256.

This is the one exact missing item:

> A committed SHA-256 binding for the retained, post-Excel-recalculation
> `RB1-R2-Remedy.xlsx` file of **581,854,795 bytes**, tied to remedy runtime
> head `39c5dc3d15501a428a42b0eb0c3cbe0d499b09fd`.

The retained workbook's existing `.outcome.json` and `.provenance.json`
sidecars bind only the **pre-recalculation** 468,206,894-byte workbook at
SHA-256
`F75189D109D4007DDE3488CB18ADD970DD73AC4FDC5C5D9AE50FCFAA15C41165`.
Installed Excel then changed the workbook to 581,854,795 bytes. The committed
`formulas-twin-recalc.json` records that later size, 4,120.4-second
recalculation, 10/10 `OK` self-checks, zero cached error cells, and the
itemized disclosure, but contains no SHA-256 for that later byte image.
Consequently the successful result cannot be proved to describe the exact
retained workbook now offered for approval.

No recalculation, regeneration, whole-corpus recount, replacement manifest, or
reviewer-created hash was performed. Prompt 05 requires stopping on this
precondition failure and returning the bounded item to implementation.

### Review identity and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 2 re-review |
| Implemented bundle? | **No** |
| Branch | `hotfix/rb-1-clean-road-source-truth` |
| Recorded base | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` |
| Remedy runtime head | `39c5dc3d15501a428a42b0eb0c3cbe0d499b09fd` |
| Requested review-record head | `12d43d86fda19813c688305f2435cda840fa11c9` |
| Review 1 approved head / record | `6d2a2ce2e70688bfaa20e8f2e11039165742d55e` / `c90908d73e22bf945c4d85484465350ae2882c22` |
| Prior Review 2 denied head | `d330312efc949523caf07f1fec4e867afed87cf7` |
| Elapsed active review | Approximately 24 minutes |
| Resource budget | **RESPECTED** — no generation, Excel invocation, application build, full gate, full recount, or new output; only Git/doc/witness inspection and small JSON/sidecar reads |

The Windows sandbox ACL helper failed before the first repository read, so the
same read-only checks were run through the approved host shell. One broad
small-file reference search timed out and was not retried. These are
reviewer-environment events, not product failures; the exact retained formula
sidecars were subsequently read directly.

### Evidence reused and bounded commands

| Evidence / command | Binding / result |
|---|---|
| Complete branch diff | `git diff --name-status --stat --check 9c774d4..12d43d8`; clean, with the remedy runtime at `39c5dc3` and the later implementation-record-only commit at `12d43d8` |
| Remedy diff | `git diff d330312..39c5dc3`; producer detail sheet, comparator itemization, one callable-note resolution, focused test/canary/records/witnesses |
| Review 1 signed record | Approval at `6d2a2ce…`, recorded by `c90908d…`; prior source/count/visual/regression evidence remains available |
| Review-2 shipped path | `r2-shipped-run.json`, SHA-256 `267F20AEA4D1CA21829127DA170F874E3D6FD9B44C642F2FB957175CC05A9DB1`; build `ok/partial`, comparison `ok/partial`, 291,127 differing cells, no evidence delta |
| Source-disagreement disclosure | `r2-source-disagreement-disclosure.json`, SHA-256 `4314B37A97D764E3356E147BEDD60E7428A459A5B8E90C6016AF6B37B4ADE676`; 174 = 159 agree + 6 differ + 9 unpaired, zero unrecorded/duplicated, all six itemized in Summary and Notes |
| Build additive witness | `r2-build-additive.json`, SHA-256 `E72C212B780D4D1AED63D072DF1D7DD1208A5A30FC02403D41EF70E8235F9E4A`; zero data-cell changes, same 174 tokens, additive 183-row marked-anchor sheet |
| Values-twin diff | `r2-values-twin-diff.json`, SHA-256 `30D041AC638301E110DE0C3FC002A624E057CFD24D18B02881317C983C064BCD`; Comparison and all non-disclosure/non-Provenance sheets unchanged |
| Marked-sheet geometry | `r2-marked-sheet-excel-metrics.json`, SHA-256 `2AF50429F87FA8C80F65796E9E93938F24385F0F9959DD91B7F426A2CF49BD71`; zero narrow columns / short rows |
| Formula result record | `formulas-twin-recalc.json`, SHA-256 `6D02F0A8D5E4B19FB2F01880A719BF6133064998A4833116ADDF2879EC3D7D32`; result fields present, but the 581,854,795-byte workbook SHA is absent |
| Retained formula sidecars | Direct read of `r2-remedy\RB1-R2-Remedy.xlsx.outcome.json` and `.provenance.json`; both bind only pre-recalc SHA `F75189D1…` / 468,206,894 bytes |

No targeted product test was started because the failed evidence precondition
requires the reviewer to stop before substantive adjudication.

### Review 2 challenge to Review 1

Review 1 could not cover this remedy artifact because the itemized-disclosure
workbook and its new Excel rebuild did not yet exist. The remedy retained the
original publication sidecars after Excel changed the formulas workbook, so
their member hash became historical rather than a binding for the accepted
cached results. The bounded challenge compared the sidecar identity to the
post-recalculation result record and found the exact size/hash seam.

### Acceptance and artifact matrices

| Criterion / gate | Re-review result | Exact evidence |
|---|---|---|
| Criteria 1–3 | **NOT RE-ADJUDICATED** | Retained witnesses were located, but Prompt 05 requires stopping on the failed precondition |
| Criterion 4 — formulas twin recalculates clean | **DENIED — EVIDENCE GAP** | Successful checks are recorded, but no SHA binds them to the retained 581,854,795-byte workbook |
| Criteria 5–7 | **NOT RE-ADJUDICATED** | No contradiction adjudicated before the required stop |
| Values / source truth | **RETAINED EVIDENCE LOCATED; NOT FINALLY ADJUDICATED** | `r2-source-disagreement-disclosure.json`, `r2-values-twin-diff.json`, and prior signed evidence |
| Formulas | **EVIDENCE GAP** | Post-recalc workbook hash missing |
| Visual | **RETAINED EVIDENCE LOCATED; NOT FINALLY ADJUDICATED** | Metric witness and retained PDFs exist |
| Evidence eligibility | **RETAINED EVIDENCE LOCATED; NOT FINALLY ADJUDICATED** | Shipped-run witness records an empty evidence delta |
| Neighbor regression | **RETAINED EVIDENCE LOCATED; NOT FINALLY ADJUDICATED** | `is-regression.json` is present |

### Actionable evidence gap

| ID | Priority | Missing item | Required return |
|---|---|---|---|
| `RB1-R2-EG-001` | P1 / blocking | The retained post-Excel-recalculation formulas twin (581,854,795 bytes) has no committed SHA-256 binding. Its sidecars still identify the pre-recalculation file. | Without rerunning Excel, calculate the SHA-256 of the existing retained post-recalculation `RB1-R2-Remedy.xlsx`; add that hash, exact path, size, remedy runtime head `39c5dc3…`, and generation/source binding to the committed formula result record; then return Prompt 05 for Review 2 re-review. Preserve all retained workbooks and prior evidence. |

**Reviewer signature:** Codex, Review 2 re-review — DENIED — EVIDENCE GAP —
`2026-07-28T18:29:39.4201856-07:00`.

Do not merge. Resume Prompt 04 only to supply `RB1-R2-EG-001`; no workbook
regeneration or Excel recalculation is requested.

## Review 2 final re-review — Codex, 2026-07-28

### Verdict

**APPROVED.** `RB1-R2-EG-001` is closed. The exact retained
post-recalculation formulas twin is 581,854,795 bytes at SHA-256
`1393164AAF50C7C4D2B7C54B33150C3D6BCDD5CB5BA8604557BC6A78EB8205F0`;
an independent reviewer hash of both the working and retained copies matched
the committed witness exactly. Runtime remains `39c5dc3`; the requested
record head `6558b03` changes evidence/docs only.

The bounded adversarial challenge found no remaining contradiction. The most
plausible false pass was collapsing a co-anchored cell to one “nearest” source
value, which would hide one of the facts the marker withholds. The focused
hermetic test proved that every co-anchored value is retained and that the
derived Summary/Notes itemization classifies the synthetic 1-agrees /
1-differs case correctly. The retained app-free witness independently records
174 markers = 159 agree + 6 differ + 9 unpaired, with all six facts itemized in
both sheets, including the four route 036 / TEH / 40.15 and 40.352 facts
required by criterion 7. The shared-schema `check_compare_ditto.py` gate also
passed, challenging callable-note leakage into unrelated behavior.

### Review identity and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 2 final re-review |
| Implemented bundle? | **No** |
| Branch | `hotfix/rb-1-clean-road-source-truth` |
| Recorded base | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` |
| Runtime head | `39c5dc3d15501a428a42b0eb0c3cbe0d499b09fd` |
| Review-record head reviewed | `6558b039ca84630e1fe55220527c2cd41f00e96c` |
| Review 1 approval | `6d2a2ce2e70688bfaa20e8f2e11039165742d55e` / record `c90908d73e22bf945c4d85484465350ae2882c22` |
| Elapsed active review | Approximately 9 minutes |
| Resource budget | **RESPECTED** — no generation, recount, Excel recalculation, application build, or full gate; two focused tests and read-only artifact/doc probes only |

The first PowerShell hash command failed at parse time and was replaced once
with a smaller `certutil` check. The bundled PDF renderer wrapper failed before
producing PNGs and was not retried. The spreadsheet Node kernel likewise
failed on the Windows ACL helper and was not retried. These are
reviewer-environment failures, not product failures. Visual acceptance rests
on the retained zero-short/zero-narrow Excel metric oracle, implementation's
signed native-scale inspection, and Review 1's signed render evidence, as the
owner-approved bounded-review policy permits.

### Evidence reused and commands newly run

| Evidence / command | Result |
|---|---|
| `git diff --check/name-status 9c774d4..6558b03` and `39c5dc3..6558b03` | **PASS** — complete agreed scope; runtime unchanged after `39c5dc3`; later changes are canary/witness/implementation/review records only |
| Independent SHA-256 of working and retained `RB1-R2-Remedy.xlsx` | **PASS** — both 581,854,795 bytes and `1393164A…`; exact committed binding |
| `formulas-twin-recalc.json` | SHA-256 `D34A91CDFF23FCF2502F148F99B06C333A6A06BC65A6825C081BD58862C2B8BB`; 10/10 self-checks `OK`, zero cached errors, exact itemized disclosure, retained copy matches |
| `r2-source-disagreement-disclosure.json` | SHA-256 `4314B37A97D764E3356E147BEDD60E7428A459A5B8E90C6016AF6B37B4ADE676`; exact 159/6/9 census, zero unrecorded/duplicated, all six itemized in Summary and Notes |
| `r2-values-twin-diff.json` / `r2-build-additive.json` | SHA-256 `30D041AC638301E110DE0C3FC002A624E057CFD24D18B02881317C983C064BCD` / `E72C212B780D4D1AED63D072DF1D7DD1208A5A30FC02403D41EF70E8235F9E4A`; Comparison unchanged, zero build data-cell changes, same 174 tokens |
| `r2-marked-sheet-excel-metrics.json` | SHA-256 `2AF50429F87FA8C80F65796E9E93938F24385F0F9959DD91B7F426A2CF49BD71`; zero narrow columns / short rows |
| `r2-shipped-run.json` | SHA-256 `267F20AEA4D1CA21829127DA170F874E3D6FD9B44C642F2FB957175CC05A9DB1`; shipped GUI path `ok/partial`, 291,127 differing cells, zero evidence delta |
| `build\.venv\Scripts\python.exe build\check_clean_road.py` | **PASS** — all checks, including marked-anchor table, co-anchored values, exact itemization, non-asserting counts, compatibility and stored geometry |
| `build\.venv\Scripts\python.exe build\check_compare_ditto.py` | **PASS** — shared opt-in behavior remains inert/unchanged outside its schema |
| Recorded full gate / neighboring family | **PASS (reused)** — 157/157 + compile/Ruff/frozen self-test; Intersection Summary zero semantic/state/count/typed changes |

### Acceptance and artifact matrices

| Criterion / gate | Final result | Exact evidence |
|---|---|---|
| 1. 161 false positives become zero | **PASS** | Review 1 signed recount; unchanged values/Comparison witnesses |
| 2. All 165 paired cells show marker and `N` | **PASS** | Signed recount, formula witness, focused hermetic test |
| 3. Summary and Notes state 102 / 174 / reason | **PASS** | Both disclosures in retained values/formulas witnesses |
| 4. Both twins regenerate; formulas clean | **PASS** | Post-recalc artifact independently hash-bound; 10/10 checks `OK`; zero errors |
| 5. Canary re-blessed | **PASS** | `CRH-SW-E3` binds build, TSN, values, pre-recalc formulas, and post-recalc formulas identities |
| 6. Full gate; base-red/head-green | **PASS** | Recorded 12-failure remedy signature / 35 original-base failures; head focused tests green; retained full gate 157/157 |
| 7. 291,127; no outside move; facts itemized | **PASS** | Comparison 0 changes; exact total; all six derived facts include the four controlling facts in Summary and Notes |
| Values / source truth | **PASS** | 174 = 159 + 6 + 9; zero unrecorded/duplicated; exact 291,127 |
| Formulas | **PASS** | SHA-bound post-recalc twin; ten `OK`; zero cached errors |
| Visual | **PASS (retained evidence)** | Both disclosure sheets: zero narrow columns/short rows; signed native-scale inspections |
| Evidence eligibility | **PASS** | Clean Road has no adapter; shipped-run evidence delta empty |
| Neighbor regression | **PASS** | Retained same-input Intersection witness plus focused shared-schema gate |
| Performance / publication / stale state | **PASS (retained evidence)** | Shipped transaction, generation binding, freshness/TOCTOU/publication gates and prior signed review |

### Review 2 challenge to Review 1

Review 1 proved source truth, counts, formula behavior, layout and neighboring
invariance, but missed two seams: the controlling plan required itemization in
Summary/Notes, and the later remedy's post-recalculation workbook initially
lacked a hash. Review 2 challenged both. The first return made itemization
source-derived and co-anchor complete; the second bound the exact recalculated
bytes. Independent hashing and the focused multi-value test now close both
without duplicating the expensive acceptance corpus.

### Final decision

No actionable failure or evidence gap remains. Review 1 and Review 2 both
approve, and neither reviewer implemented the bundle. RB-1 is
**JOINTLY APPROVED** and eligible to merge.

**Reviewer signature:** Codex, Review 2 final re-review — APPROVED —
`2026-07-28T19:00:41.8114249-07:00`.

## Merge and post-merge verification

| Item | Result |
|---|---|
| Remote-main divergence check | **PASS** — fetched `origin/main`; local `main`, `origin/main`, `FETCH_HEAD`, and merge-base were all `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` before merge |
| Merge | **PASS** — non-forced `--no-ff` merge via `ort`; merge commit `560ea5e501fdd76003985753ba7fc9ff0a551320` |
| Planned post-merge smoke gate | **PASS** — `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k`: **157 passed, 0 failed** in 260 seconds |
| Frozen application self-test | **PASS** — `powershell -NoProfile -ExecutionPolicy Bypass -File .\build\build.ps1 -SelfTest`: exact shipped executable `SMOKE OK`; frozen self-test passed in 177.6 seconds |

The merge and post-merge verification were performed on `main`. No force was
used, and retained audit artifacts and unrelated branches were not modified.
