# `RB-1` — Adversarial Review Record

Status: **REVIEW 1 APPROVED — AWAITING REVIEW 2**

## Review identity

| Field | Value |
|---|---|
| Bundle / work item | `RB-1` / `HF-01` |
| Reviewed branch | `hotfix/rb-1-clean-road-source-truth` |
| Recorded base `main` | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` |
| Original denied head | `a26725b59a5dc5c9445d43af03c9a3ea4041b484` |
| Review-return implementation | `84b82de` plus SHA-recording follow-up |
| Reviewed head | `6d2a2ce2e70688bfaa20e8f2e11039165742d55e` |
| Implementer | Claude |
| Approving reviewer | Codex — independent; did not implement this bundle |
| Review 2 | PENDING — must independently review this exact approved head plus this review-record commit |
| Merge | PENDING — first approval only; branch remains unmerged |

## Verdict

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
| Review 2 | PENDING — separate review | NOT STARTED | PENDING |

**Reviewer signature:** Codex, Review 1 — APPROVED —
`2026-07-28T08:26:47.3070509-07:00`.

Do not merge. Run Prompt 05 again in a separate Codex review with:

```text
<BUNDLE_ID> = RB-1
<REVIEWER> = Codex
```

The second review must independently challenge the exact approved head plus
this review-record commit. Only joint approval authorizes merge, post-merge
smoke checks, push, and branch/worktree cleanup.
