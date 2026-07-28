# `RB-1` — Adversarial Review Record

Status: **DENIED — RETURN TO IMPLEMENTATION**

## Review identity

| Field | Value |
|---|---|
| Bundle / work item | `RB-1` / `HF-01` |
| Reviewed branch | `hotfix/rb-1-clean-road-source-truth` |
| Recorded base `main` | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` |
| Implementation commit | `93e12c23a8eeb8686817248d662e4d30125de0ec` |
| Reviewed head | `a26725b59a5dc5c9445d43af03c9a3ea4041b484` |
| Implementer | Claude |
| Review 1 | Codex — independent reviewer; **did not implement this bundle** |
| Review 2 | PENDING — do not run until the Review 1 return is implemented |
| Final merge commit | PENDING — branch remains unmerged |

## Verdict

**DENIED.** The source-truth semantics, exact recount, formula-workbook
generation, real GUI generation path, evidence absence, full gate, and
unaffected-family regression all passed independent review. The bundle
nevertheless fails a mandatory acceptance criterion: the newly added disclosure
on
`ArcGIS Build!A4:B108` is clipped and unreadable in its stored presentation.

This violates the frozen bundle's
[visual-usability rule](BUNDLE.md#required-verification-matrix), which requires
the disclosure to be legible in its stored width and forbids new clipping, and
the Stage 3 ruling that RB-1's own marker/disclosure must be legible even though
HF-02 owns the pre-existing cross-family clipping program.

## Commands and source inputs

| Purpose | Reviewer command / method | Result |
|---|---|---|
| Branch and scope | `git status --short --branch`; `git diff --name-status`, `--stat`, and `--check` from recorded base `9c774d4…` to reviewed head `a26725b…` | **PASS** — clean reviewed head; 16 files, 3,239 insertions / 37 deletions; only the allowed producer, Clean Road comparator, inert shared schema hook, test, canary, plan/records, and witnesses |
| Targeted head tests | `build\.venv\Scripts\python.exe` running `build/check_clean_road.py`, `check_compare_equality_policy.py`, `check_compare_audit.py`, `check_comparison_artifact_schema.py`, and `check_compare_ditto.py` | **PASS** — all five |
| Required base-red proof | Archived base `9c774d4…`, copied only head's new `build/check_clean_road.py`, then ran it with the base scripts | **PASS** — 19 semantic failures, including the defect signature `got 3` differing cells instead of `1` |
| Full gate | `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=safe.directory`, `GIT_CONFIG_VALUE_0=C:/Users/Yunus/Projects/TSMIS-Reports-Exporter`; then `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k` | **PASS** — 157 / 157. An initial sandbox run was 156 / 157 only because child `git` rejected the managed workspace; the unchanged invocation-scoped safe-directory rerun was fully green |
| Compile / lint / frozen app | `python -m compileall -q scripts build`; `uvx … ruff check scripts --select E9,F63,F7,F82,F811,F401`; `powershell -File build\build.ps1 -SelfTest` | **PASS** — compile clean; Ruff “All checks passed”; exact shipped executable `SMOKE OK`, 173 MB onefolder |
| Real end-user generation | Reviewer-owned driver called `GuiApi.start_arcgis_build` → `ConsolidateWorker` → GUI terminal, then `GuiApi.start_arcgis_compare` → `_begin_compare` / `_launch_compare` → worker → GUI terminal; only the native save dialog returned one explicit absent destination | **PASS** — both terminal results `status=ok`, `completion=partial`; zero GUI errors; build and both twins written |
| Independent source/value audit | Reviewer-owned openpyxl/OOXML reader over every raw ArcGIS span layer plus the frozen pre/post build and values workbooks; imported no product module and did not consume the implementation witness as an oracle; joined the ArcGIS sheet's visible `Key (helper)` to Comparison's hidden `__CMP_E2_KEY_V1_TOKEN` | **PASS** — exact counts and zero unexpected published changes; details below |
| Installed-Excel formula audit | `powershell -File tmp\rb1-review\audit_formula_excel.ps1` against the independently GUI-generated formulas and values twins; Excel `CalculateFullRebuild`, save, cached/live comparison | **NOT COMPLETED — REVIEWER ENVIRONMENT.** Two attempts drove Excel above 9 GB private memory with severe paging on the 16 GB reviewer host; both ended in host blue screens before Excel saved or emitted audit JSON. No pass is claimed. This lane is not needed to reach denial because visual usability already fails. |
| Native visual audit | Native-Excel PDFs rendered, then every required Summary, Notes, Comparison, ArcGIS Build, and Provenance view inspected; workbook OOXML layout/styles checked separately | **FAIL** — one blocking, newly introduced clipping defect on `ArcGIS Build` |

### Frozen and reviewer-generated identities

| Input / artifact | Bytes | SHA-256 |
|---|---:|---|
| ArcGIS layer library index `arcgis_layers\00_INDEX.xlsx` | 6,993 | `CCD1BDFFC0A122797B95B73CF311D5CB6B8996B7BB55AFDD742A2C4F2CF23ABE` |
| TSN raw `CA HIGHWAYS 09.08.2025.xlsx` | 21,290,781 | `BBD1ACF9D4A8FEF86F96A0A2CF54BE1105E8C919600DBCD05A325B194F5C86E5` |
| Frozen pre-fix build | 10,824,390 | `8F9766AC75E3F1CD10729B6090FE2532DA90C821776D3114E28F65DF70BA6376` |
| Retained post-fix build | 10,828,144 | `8BDD9247771CF2580775F4F0A1DD87706E75F3533C33EC9DB25D41A9AB4B305E` |
| Frozen pre-fix values comparison | 199,766,125 | `A59177DCDAFCD46369D6438E7773B16A18A3175BCEA11AA347395CE874E493C5` |
| Retained post-fix values comparison | 200,034,918 | `AFAAB4BACA82D31694BBE2D98E0EE362C91303A79843ED0DC77F4930DEFE3A12` |
| Independently GUI-generated build | 10,828,183 | `3F420A16C5C2E131A9F092C3DD1E08A887CBE89BA7F9F07CF5413D2A53F84767` |
| Independently GUI-generated values twin | 199,821,578 | `C103C4EC41E6F435C3ABEA8D88F76E817E39DD43DD57B7589778509124050856` |
| Independently GUI-generated formulas twin, before Excel recalc | 468,206,187 | `0A0DB15CF4DDC20FBA1666408A906523E5C3945A25FF4C0005CA14BB60760C54` |
| Same formulas twin, after Excel recalc/save | Not produced | N/A — reviewer audit did not complete |
| Retained native-Excel `built ArcGIS Build top.pdf` | 119,074 | `42A41C5D820A7709285F189A77EA5A619AD86853DA996F5BFC3CBFF595C37141` |

The alternate reviewer-generated workbook byte hashes are expected: generation
time, run identity, provenance paths, and Excel caches differ. The acceptance
invariant is published semantic/state equivalence, not raw ZIP identity.

## Contract and diff audit

| Check | Review 1 | Evidence / notes |
|---|---|---|
| Every in-scope finding is fixed | **FAIL — acceptance incomplete** | PCOA-FINAL-010's value/source-truth defect is fixed, but its RB-1-specific visual-usability criterion fails |
| No out-of-scope behavior changed | **PASS** | Shared `CompareSchema.unavailable_rule` defaults inert; no unrelated production file changed; unaffected Intersection Summary is semantically identical |
| Implementation matches allowed surface | **PASS** | Producer records/marks skipped spans; Clean Road opts into one non-asserting rule; test/canary/docs/witness changes are required support |
| Tests exercise end-user generation paths | **PASS** | New semantic test is base-red/head-green; reviewer also generated through the actual GUI API/worker closures |
| Migration / old-build behavior | **PASS** | Older or skip-free builds use the plain schema; skip-free control stays `COMPLETE`; `PARTIAL` propagates for the real 102-row run |
| Atomic publication / failure behavior | **PASS for changed scope** | GUI logs show temporary pair names followed by both final twins, no GUI error, and zero evidence artifacts; existing atomic/failure checks are included in the 157-test gate |
| Performance / rerun behavior | **PASS for changed scope** | The real 57,728-row build and 65,164-row two-twin comparison completed inside the review driver's 30/60-minute operation budgets; output sizes are recorded above. The marker result is deterministic at 102/174, the skip-free and old-build controls pass, and no publication/performance subsystem was changed |
| Provenance / stale-cache behavior | **PASS** | Provenance names real inputs and hashes and records producer completion `partial`; build-freshness/state snapshots remain valid |

## Independent source and discrepancy audit

| Measure | Independent result | Contract result |
|---|---:|---|
| Raw span layers / live as-of span rows scanned | 26 / 207,602 | Re-derived without product parsing |
| Skipped rows | **102** | Exact |
| Layer split | 100 `SHS Travel Way L`; 2 `SHS O Shld Width R` | Exact |
| Endpoint split / `LocError` | 101 known begins; 1 known end; all `NO ERROR` | Exact |
| Expected / actual build markers | **174 / 174** | Exact; zero missing, zero unexpected |
| Marker split | 171 left travel-way; 3 right outside-shoulder cells | Exact |
| Paired comparison markers | **165**, all old `D` → new `N` | Exact |
| One-sided marker displays | **9**, state remains `U` | Exact; no count change |
| Exact false positives | **161 → 0** | Pass |
| Raw-source disagreement diagnostics | **4**, still itemized | Pass; now non-asserting |
| Differing cells | **291,127 = 291,292 − 165** | Exact |
| Paired / ArcGIS-only / TSN-only rows | **52,647 / 5,081 / 7,436** | Unchanged |
| Differing / identical paired rows | **50,012 / 2,635** | Unchanged |
| Unexpected build-data changes | **0** | Pass |
| Unexpected comparison display/state/count changes | **0** | Pass |
| Unexpected published layout changes | **0** | Pass |

All 174 expected positions were bound independently from raw ArcGIS facts to
the frozen build, then through the published helper-token join. The 165 paired
cells display `(unavailable: source span skipped)` and state `N`; the nine
one-sided positions display the same token while retaining `U`. Nearby genuine
differences remain red/asserting and counted.

## Values, formulas, visual, evidence, and regression matrix

| Gate | Review 1 | Independent artifacts / notes |
|---|---|---|
| Values and discrepancy truth | **PASS** | Exact 174-marker / 165 `D→N` / 9 `U` set; 291,127 differing cells; no out-of-witness asserting change |
| Installed-Excel formula parity | **NOT COMPLETED — REVIEWER ENVIRONMENT** | No independent native-recalc pass is claimed. The implementer witness records a pass and every completed reviewer semantic/value/test gate passed, but two full-rebuild attempts blue-screened the 16 GB reviewer host before save. Rerun on a suitably provisioned host after the P1 return; this cannot change the current denial. |
| Visual deliverable usability | **FAIL** | Summary, Notes, Comparison, and Provenance pass; newly added `ArcGIS Build!A4:B108` disclosure is clipped |
| PDF/Excel sibling parity | **N/A** | Clean Road has no PDF edition |
| PDF/PDF evidence completeness/crops | **N/A** | Clean Road has no evidence adapter |
| No mixed-format evidence leakage | **PASS** | Zero `*evidence*` artifacts before/after and in the independently generated output tree |
| Canary | **PASS** | CRH-SW-E3 records the exact −165 delta and supersedes E2 |
| Unaffected-family regression | **PASS** | Intersection Summary: every non-Provenance cell equal; panes/states/dimensions equal; both snapshots remain `veryHidden`; typed payload SHA on base/head `f7e3296db9aad6a22e42dd4b436aab46fd42e14a7957f53a0e55599df37ddeaf`; completion `complete` |
| Full regression gate | **PASS** | 157 / 157, compileall, focused Ruff, and frozen executable self-test |

### Required native-sheet inspection

| Sheet | Result | Notes |
|---|---|---|
| Summary | **PASS** | 102 skipped spans, 174 anchors, and reason legible; counts/formula results agree |
| Notes | **PASS** | Disclosure is first and fully readable |
| Comparison | **PASS** | Markers are visually distinguishable from genuine red `≠` differences, excluded from `Diffs`, and grey context headers are unchanged |
| ArcGIS Build | **FAIL** | New rows 4–108 are not legible in their stored presentation; details below |
| Provenance | **PASS** | Durable paths, both input hashes, and producer completion `partial` are readable |

## Blocking finding

| ID | Priority | Finding | Required change | Status |
|---|---|---|---|---|
| RB1-R1-001 | **P1 / blocking** | `scripts/consolidate_clean_highway.py:1082-1086` appends three new disclosure rows and 102 warning rows to `ArcGIS Build`, but applies no presentation. OOXML has no explicit column-width records, `baseColWidth=8`, `defaultRowHeight=15`, and every new cell uses style 0 with neither wrap nor shrink-to-fit. Native Excel renders the labels as `Skipped so…`, `Marked an…`, and `Unavailabl…`; B6 is cut off; B7:B108 contain 280–329 characters each yet render only their opening fragment. The retained proof is `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\built ArcGIS Build top.pdf` (SHA above). These are RB-1's newly introduced rows, not HF-02's pre-existing general clipping. | Make all new A4:B108 labels, marker text, and 102 itemized warning/details legible at native scale using purposeful widths/wrapping/row heights or an equivalently readable structure. Regenerate the build and both twins because build hash/provenance changes, then rerun the complete visual/formula/count/GUI/regression matrix. Keep the remedy limited to RB-1's new marker-sheet content. | **OPEN — RETURN TO PROMPT 04** |

The real GUI run completed and produced valid output; its wrapper returned a
non-zero console status only after writing the complete result JSON because the
reviewer's CP1252 terminal could not print the Unicode `✗` verdict character.
That is a reviewer-harness display issue, not an application failure.

The implementation record's pre-existing cancellation observation
(`_cancelled()` takes no argument while unchanged callers pass `events`) was
confirmed as present at the base and is not charged to RB-1. It remains outside
this bundle and does not weaken the blocking visual finding above.

## Approval

| Reviewer | Relationship to implementation | Decision | Reviewed commit / timestamp |
|---|---|---|---|
| Codex — Review 1 | Independent; not the implementer | **DENIED — RETURN TO IMPLEMENTATION** | `a26725b59a5dc5c9445d43af03c9a3ea4041b484` / `2026-07-28T00:03:08.6792773-07:00` |
| Review 2 | PENDING | NOT STARTED | PENDING |

**Reviewer signature:** Codex, Review 1 — `2026-07-28T00:03:08.6792773-07:00`.

Do not merge. Resume
`hotfix/rb-1-clean-road-source-truth` through Prompt 04 with
`<BUNDLE_ID> = RB-1` and `<IMPLEMENTER> = Claude`. After the exact return above
is implemented and the acceptance artifacts are regenerated, run Prompt 05
again from the new reviewed head.
