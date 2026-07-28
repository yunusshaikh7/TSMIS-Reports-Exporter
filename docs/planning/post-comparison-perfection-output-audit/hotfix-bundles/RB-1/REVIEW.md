# `RB-1` — Adversarial Review Record

Status: **DENIED — RETURN TO IMPLEMENTATION**

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
| Implementer | Claude |
| Approving reviewer | Codex — independent; did not implement this bundle |
| Review 2 | Codex — independent; did not implement this bundle; **DENIED — RETURN TO IMPLEMENTATION** |
| Merge | BLOCKED — Review 2 denied; branch remains unmerged |

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
