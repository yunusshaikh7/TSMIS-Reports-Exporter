# `RB-2` — Adversarial Review Record

Status: **JOINTLY APPROVED — AWAITING MERGE**

## Initial Review 1 verdict — 2026-07-30

**DENIED — EVIDENCE GAP.** Prompt 05 requires the implementation record to
identify an exact base and acceptance runtime head, and requires every expensive
acceptance operation to be represented by a retained, hash-bound result before
substantive review begins. RB-2 records the base, but neither the implementation
record nor the retained result files identify the exact runtime head for
`RB2-A1`, and there is no manifest binding the complete retained acceptance set
by path, size, SHA-256, source identity, and generation metadata.

This is the one exact missing item:

> A committed `RB2-A1` acceptance manifest for one exact final runtime head,
> binding every retained deliverable and acceptance result by exact path, byte
> size, SHA-256, frozen-source identity, and generation metadata.

The gap is material rather than clerical. The retained
`head-generation.json` was written at
`2026-07-29T07:51:55.8986132-07:00`, while the final production-code commit
`1a9418339e1c0df1cc16eddcaedb22dc1e4135d0` was committed at
`2026-07-30T00:43:00-07:00`. That commit changes the Provenance sheet written
into every comparison workbook. Its own commit and implementation record say
that only the four classic-environment workbooks were regenerated afterwards.
The remaining retained corpus therefore cannot be accepted as same-final-head
evidence, and the absence of a runtime/head manifest prevents proving otherwise.

No reviewer-created manifest, workbook regeneration, installed-Excel rebuild,
whole-corpus recount, full gate, or replacement acceptance run was performed.
Prompt 05 requires stopping on this precondition failure and returning the one
bounded item to implementation.

## Review identity and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 1 |
| Implemented bundle? | **No** — implementer is Claude |
| Bundle / work items | `RB-2` / `HF-02 + HF-03` |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base | `896083e014d0451d5b05e5b6b024339aebc84d74` |
| Acceptance runtime head | **NOT RECORDED — precondition failure** |
| Last production-code commit | `1a9418339e1c0df1cc16eddcaedb22dc1e4135d0` |
| Review-record head reviewed | `4247e7c3be6e6a79e5f0d09fe837821caf2318ee` |
| Remote branch head | `4247e7c3be6e6a79e5f0d09fe837821caf2318ee` |
| Review 2 | **BLOCKED** — do not run until this return is implemented and Review 1 re-reviews |
| Merge | **BLOCKED** |
| Elapsed active review | Approximately 20 minutes |
| Resource budget | **RESPECTED** — no generation, Excel invocation, application build, full gate, full recount, or new bulk output; only Git/doc/small-JSON inspection |

The Windows sandbox ACL helper failed on the first ordinary repository reads,
so the same bounded read-only checks were performed through the approved host
shell. This is a reviewer-environment event, not a product failure.

## Precondition audit

| Prompt 05 precondition | Result | Evidence |
|---|---|---|
| Review-1 status is `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW` | **PASS** | `START-HERE.md`, `IMPLEMENTATION-PLAN.md`, `BUNDLE.md`, and `IMPLEMENTATION.md` agreed before this verdict |
| Hotfix branch exists and retained roots exist | **PASS** | Local and remote branch both resolved to `4247e7c…`; both `HF-02` and `HF-03` retained roots exist |
| Exact base SHA is recorded | **PASS** | `896083e014d0451d5b05e5b6b024339aebc84d74`; merge-base agrees |
| Exact acceptance runtime head is recorded | **FAIL** | The implementation lists three abbreviated implementation commits but names no runtime head for `RB2-A1`; retained result schemas carry paths such as `tree` but no commit/tree identity |
| Every expensive acceptance result is retained and hash-bound | **FAIL** | No corpus manifest binds the retained deliverables/results by path, bytes, SHA-256, source identity, generation metadata, and runtime head |

Because a precondition failed, no acceptance criterion was substantively
adjudicated and no targeted product test was started.

## Evidence inspected and bounded commands

| Evidence / command | Binding / result |
|---|---|
| Branch identity and complete diff boundary | `git diff --check 896083e…4247e7c` clean; merge-base is the recorded base; local and remote hotfix heads agree |
| Commit sequence | Production changes at `da1d480…`, `eb54b96…`, and final `1a94183…`; later `4247e7c…` is the implementation-record/status commit |
| Final production change | `1a94183…` fits Provenance role column A and states that four classic-environment workbooks were regenerated; the shared writer affects every comparison workbook |
| Retained generation record | `head-generation.json`, 110,605 bytes, SHA-256 `85BCFB711DB78439AAE5575DE85573B9547D83D7F561AEE16AF2A4D2F4929C88`; predates `1a94183…` and has keys `tree,dest,data_root,output_root,records`, with no runtime commit |
| Retained Excel result | `excel-recalc.json`, 16,353 bytes, SHA-256 `54F8972DD61A93913A2452D83852BF399967A0F171E740222AA41B277CE2CEC4`; binds its eight copied workbook byte images before/after Excel but not the `RB2-A1` runtime head or full corpus |
| Retained render result | `excel-renders.json`, 2,423 bytes, SHA-256 `E38F079043D0C621038DB57EEEABC2185550B07BF9F3A9B1A84D50D2A9E9ED22`; no runtime identity and no SHA-256 entries for the rendered deliverables |
| Retained invariance result | `invariance.json`, 74,624 bytes, SHA-256 `781DE18908F7FD1ABAE98132EA48EF1F532F559513F1F1D1A48F65FED4243DDC`; schema has `base,head,only_in_base,only_in_head,workbooks,totals` but no exact code head |
| Retained TSN rebuild result | `tsn_rebuild.json`, 72,205 bytes, SHA-256 `AF3B54C0EBB6894C8C389C3461A7263E0A75872E7F0AB56BD1A74DBC469D5D1A`; records dataset hashes but no `RB2-A1` runtime identity |
| Committed HF-02 witnesses | `clipping-before-after.json` SHA-256 `4559C868…`; `count-invariance.json` SHA-256 `46285D46…`; both are distilled results without a runtime-head/artifact-manifest binding |
| Committed HF-03 witnesses | `temp-capture-lifecycle.json` SHA-256 `794E307F…`; `tsn-provenance-scope.json` SHA-256 `B5C0E227…`; both are distilled results without a runtime-head/artifact-manifest binding |

The reviewer hashes above identify the small records that were inspected. They
do not cure the missing binding between those records, the retained bulk
artifacts, and one exact implementation runtime.

## Acceptance and artifact matrices

| Criterion / gate | Review 1 result | Exact reason |
|---|---|---|
| HF-02 criteria 1–6 | **NOT ADJUDICATED** | Prompt 05 requires stopping at the failed evidence precondition |
| HF-03 criteria 1–6 | **NOT ADJUDICATED** | Prompt 05 requires stopping at the failed evidence precondition |
| Values / source truth | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | Results are not bound to one exact final runtime head |
| Formulas | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | Eight Excel outputs have local hashes, but the result set is not bound to the complete final-head corpus |
| Visual | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | Render record lacks complete artifact hashes/runtime binding; most generated workbooks predate the final shared-writer change |
| Evidence eligibility / parity | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | No same-head acceptance manifest |
| Neighbor regression / full gate / frozen self-test | **RECORDED; NOT FINALLY ADJUDICATED** | No result-to-runtime binding |

## Actionable evidence gap

| ID | Priority | Missing item | Required return |
|---|---|---|---|
| `RB2-R1-EG-001` | P1 / blocking | The complete `RB2-A1` acceptance set is not bound to one exact final runtime head, and most retained generated workbooks predate the final shared Provenance-writer change. | On the existing RB-2 branch, establish one exact final runtime head and supply one committed `RB2-A1` manifest covering the complete acceptance set by exact path, byte size, SHA-256, frozen-source identity, and generation metadata. Regenerate the stale corpus and rerun the required dependent acceptance legs so every claimed result is same-head; do not merely hash the pre-`1a94183` workbooks. Preserve the existing retained evidence as prior-run history, then return Prompt 05 for Review 1 re-review. |

**Reviewer signature:** Codex, Review 1 — DENIED — EVIDENCE GAP —
`2026-07-30T09:02:41.2783734-07:00`.

Do not merge and do not begin Review 2. Resume Prompt 04 on the existing
`hotfix/rb-2-deliverable-presentation` branch only to supply
`RB2-R1-EG-001`.

## Review 1 re-review — Codex, 2026-07-31

### Verdict

**DENIED — EVIDENCE GAP.** The regenerated corpus and the retained results share
one content-derived runtime digest, but the returned item required one exact Git
runtime head. The implementation record names
`c483bda1716e03d0e013b25e975bd9a41c58b2c8`; the committed manifest names
`b37c1fe8f3dc2b56fad204312b0a2cbbc335a4b5`; and the 18 results classified as
claimed acceptance evidence contain three different exact-head states:

- 14 name `c483bda1716e03d0e013b25e975bd9a41c58b2c8`;
- `frozen-inputs.json`, `evidence-determinism.json`, and
  `provenance-final-commit.json` name
  `b37c1fe8f3dc2b56fad204312b0a2cbbc335a4b5`;
- `generation-equivalence.json` names no exact head at all.

All 18 carry or resolve to runtime digest
`1EFA63FD9EE6355008AD49BE6342E79DCE486A1BFF9FE1E9202F471600162279`.
That proves runtime-content equivalence, not the stronger one-execution-head
claim made by `RB2-A1`, Prompt 05, and the implementation record.

This is the one exact missing item:

> A corrected `RB2-A1` manifest/result set and verifier that bind all 18
> claimed acceptance results to the same exact Git runtime head, with no missing
> or differing `runtime_head_commit`.

The committed verifier does not detect the mismatch. Run against
`--at c483bda…`, it prints the manifest's different `b37c1fe…` head and still
returns `VERIFIED — 0 problem(s)`. It compares the 418-file runtime digest and
trusts `results.all_claimed_same_head`; it never requires each claimed result's
exact commit to equal the manifest/implementation head. Its “non-runtime commits
since” figure is the length of the manifest-supplied list rather than a
re-derived commit list, which is why it reports four while checking the earlier
`c483bda…` commit.

Git independently confirms that no runtime file changed after
`1a9418339e1c0df1cc16eddcaedb22dc1e4135d0`. This is therefore an evidence
identity gap, not a corroborated product failure, and it does not require another
bulk generation, installed-Excel rebuild, full gate, or whole-corpus recount.
Prompt 05 requires stopping before substantive acceptance adjudication.

### Review identity and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 1 re-review |
| Implemented bundle? | **No** — implementer is Claude |
| Bundle / work items | `RB-2` / `HF-02 + HF-03` |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base | `896083e014d0451d5b05e5b6b024339aebc84d74` |
| Implementation-record runtime head | `c483bda1716e03d0e013b25e975bd9a41c58b2c8` |
| Manifest runtime head | `b37c1fe8f3dc2b56fad204312b0a2cbbc335a4b5` |
| Review-record head reviewed | `0b2ad693c07221b5a9de984610f4e0ebaad12f6f` |
| Remote branch head before this record | `0b2ad693c07221b5a9de984610f4e0ebaad12f6f` |
| Review 2 | **BLOCKED** |
| Merge | **BLOCKED** |
| Elapsed active review | Approximately 29 minutes |
| Resource budget | **RESPECTED** — no generation, Excel invocation, application build, full gate, full recount, corpus re-hash, or new bulk output; only Git/doc/manifest inspection and one 22-second committed-verifier run |

The Windows sandbox ACL helper failed on ordinary repository reads and on the
normal patch editor. Read-only checks were moved to the approved host shell; the
record was applied as a narrow UTF-8 Git patch. One PowerShell inventory command
had a syntax error and one manifest-summary query encountered null timestamp
fields; neither was retried as a product probe. These are reviewer-environment
events, not product failures.

### Precondition audit

| Prompt 05 precondition | Result | Evidence |
|---|---|---|
| Review-1 status is `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW` | **PASS on entry** | `START-HERE.md`, `IMPLEMENTATION-PLAN.md`, `BUNDLE.md`, and `IMPLEMENTATION.md` agreed before this verdict |
| Hotfix branch and retained outputs exist | **PASS** | Local/remote branch both resolved to `0b2ad693…`; retained `generation-equivalence.json` was read and hash-checked |
| Exact base SHA is recorded | **PASS** | `896083e014d0451d5b05e5b6b024339aebc84d74`; merge-base agrees |
| Implementation document identifies an exact acceptance head | **PASS in isolation** | It names `c483bda1716e03d0e013b25e975bd9a41c58b2c8` |
| Complete acceptance set is bound to that one exact head | **FAIL** | Manifest head is `b37c1fe…`; claimed results split 14 / 3 / 1 across `c483bda…`, `b37c1fe…`, and missing |
| Every expensive acceptance result is usable as same-head evidence | **FAIL** | The verifier accepts digest equivalence without enforcing exact result-head equality |

Because the returned precondition still fails, no HF-02 or HF-03 acceptance
criterion was substantively adjudicated and no targeted product test was
started.

### Evidence reused and bounded commands

| Evidence / command | Binding / result |
|---|---|
| Branch identity and complete diff boundary | `git merge-base`, `git diff --check`, `--name-status`, and `--stat` from `896083e…` through `0b2ad693…`; clean boundary, 21 changed files |
| Remedy commit sequence | `c483bda…` adds the verifier; `b37c1fe…` updates records/witnesses; `0b2ad693…` commits the manifest/source listing |
| Manifest | 1,801,981 bytes; SHA-256 `19E5C58CC1AF22AE2A869D7680E9A9454FEFFE5417DB1C8C66D3B22D53BC74C5` |
| Frozen-source listing | 962,858 bytes; SHA-256 `44634BB6DDCD18AA8680B19DD99281CB8703C06DD302C73C9097309DC44A5798`; agrees with the manifest |
| Exact-head census | 18 claimed entries: 14 `c483bda…`, 3 `b37c1fe…`, 1 missing |
| Missing-head result | `generation-equivalence.json`, 3,426 bytes, SHA-256 `BA639FA20B47A9CDAA5A8E49F6D1710FB1EE6FADE1EF497A349F26783D0DB7A7`; `current` records only the runtime digest |
| Committed verifier | One run at `--at c483bda…`: 418 runtime files matched, four committed witnesses matched, corpus not requested, final result incorrectly `VERIFIED — 0 problem(s)` despite the exact-head census |
| Runtime lineage | Last runtime change re-derived as `1a9418339e1c…`; zero runtime files changed afterwards |

### Acceptance and artifact matrices

| Criterion / gate | Re-review result | Exact reason |
|---|---|---|
| HF-02 criteria 1–6 | **NOT ADJUDICATED** | Prompt 05 requires stopping at the failed evidence precondition |
| HF-03 criteria 1–6 | **NOT ADJUDICATED** | Prompt 05 requires stopping at the failed evidence precondition |
| Values / source truth | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | Claimed records are not all bound to one exact head |
| Formulas | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | No Excel work was repeated; exact-head precondition failed first |
| Visual | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | Render hashes are retained, but the complete claim is not one-head-bound |
| Evidence eligibility / parity | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | `evidence-determinism.json` is one of the three `b37c1fe…` results |
| Neighbor regression / full gate / frozen self-test | **RECORDED; NOT FINALLY ADJUDICATED** | Exact-head precondition failed |

### Actionable evidence gap

| ID | Priority | Missing item | Required return |
|---|---|---|---|
| `RB2-R1-EG-002` | P1 / blocking | The claimed `RB2-A1` set is runtime-digest-equivalent but not bound to one exact Git head: implementation = `c483bda…`, manifest = `b37c1fe…`, results = 14 / 3 / 1 across `c483bda…` / `b37c1fe…` / missing. | Use `c483bda1716e03d0e013b25e975bd9a41c58b2c8` as the one acceptance head; at that clean checkout re-run only the three small results currently stamped `b37c1fe…` and ensure `generation-equivalence.json` names the same exact head. Rebuild the committed manifest so its acceptance head and all 18 claimed entries agree, and make the verifier fail on any missing/mismatched result head while re-deriving the intervening commit list. Preserve the bulk corpus, Excel outputs, prior evidence, and runtime digest; no bulk regeneration is requested. Then return Prompt 05 for Review 1 re-review. |

**Reviewer signature:** Codex, Review 1 re-review — DENIED — EVIDENCE GAP —
`2026-07-31T07:21:39.4945627-07:00`.

Do not merge and do not begin Review 2. Resume Prompt 04 only to supply
`RB2-R1-EG-002`.

## Review 1 re-review approval — Codex, 2026-07-31

### Verdict

**APPROVED.** The current branch closes both bounded returns in the Review 1
chain. `RB2-R1-EG-001` is closed by the regenerated, path/size/SHA-256/source/
generation-bound `RB2-A1` corpus. `RB2-R1-EG-002` is closed because all 18
claimed result files now name the one exact acceptance head
`c483bda1716e03d0e013b25e975bd9a41c58b2c8`, all 18 retained bytes match the
manifest, and the verifier rejects missing or differing exact heads rather than
accepting runtime-digest equivalence alone.

The user invocation names the re-review of `RB2-R1-EG-001`; the branch also
contains the later `RB2-R1-EG-002` remedy created by the first re-review. This
approval therefore adjudicates the complete current remedy chain rather than
silently ignoring the later controlling return.

### Review identity and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 1 re-review approval |
| Implemented bundle? | **No** — implementer is Claude |
| Bundle / work items | `RB-2` / `HF-02 + HF-03` |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base | `896083e014d0451d5b05e5b6b024339aebc84d74` |
| Acceptance runtime head | `c483bda1716e03d0e013b25e975bd9a41c58b2c8` |
| Manifest build head | `a38ad214932069c8bd928b078011a0964d06182b` |
| Review-record head reviewed | `c5740b9e03d28afb8b295eb02182e7b106b1027d` |
| Remote branch head on entry | `c5740b9e03d28afb8b295eb02182e7b106b1027d` |
| Elapsed active review | Approximately 18 minutes |
| Resource budget | **RESPECTED** — no generation, Excel invocation, build, full gate, corpus recount, corpus re-hash, or new bulk output |
| Review 2 | **ELIGIBLE — separate fresh task required** |
| Merge | **BLOCKED pending Review 2** |

### Preconditions and return closure

| Prompt 05 precondition / return | Result | Evidence |
|---|---|---|
| Review-1 status is `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW` | **PASS on entry** | Controlling bundle, implementation, plan queue, and START-HERE header agreed; the stale workflow-table rows are synchronized by this record |
| Hotfix branch and retained outputs exist | **PASS** | Clean local branch and remote both at `c5740b9…`; every one of the 18 claimed result paths exists |
| Exact base and implementation head are recorded | **PASS** | Merge-base re-derived as `896083e…`; acceptance head is `c483bda…` |
| Expensive acceptance operations are retained and hash-bound | **PASS** | `RB2-A1-manifest.json` and its source listing bind the complete classified result/output/input set |
| `RB2-R1-EG-001` | **CLOSED** | Regenerated corpus is bound by exact path, bytes, SHA-256, frozen-source identity, generation metadata, runtime digest, and exact acceptance head |
| `RB2-R1-EG-002` | **CLOSED** | 18/18 claimed files contain `c483bda…`; 0/18 contain the former off-head `b37c1fe…`; a missing plus mismatched injected head yields two verifier failures |

### Evidence reused and bounded commands

| Evidence / challenge | Result |
|---|---|
| Complete branch boundary | Merge-base agrees; `git diff --check` clean; 21 changed paths from base through `c5740b9…`; product edits remain inside the frozen four-file surface, with focused checks, witnesses, records, and verifier alongside them |
| Remedy boundary | Three commits after the prior review record change only six evidence/status/verifier files; no product runtime file changed after `1a94183…` |
| `RB2-A1-manifest.json` | 1,803,195 bytes; SHA-256 `3BF96B3B248082AA3C0C2C767908E23054A61C3CDAE4ABD1B56CD3380D0F82E8` |
| `RB2-A1-sources.json` | 962,858 bytes; SHA-256 `44634BB6DDCD18AA8680B19DD99281CB8703C06DD302C73C9097309DC44A5798` |
| Committed verifier, one run at `--at c483bda…` | **VERIFIED — 0 problems**; 418 runtime files matched; last runtime change `1a94183…`; four committed witnesses re-hashed; no runtime changes through manifest build |
| Independent retained-result check | All 18 actual files match manifest byte size and SHA-256; all 18 contain the exact acceptance head; none contains the former off-head commit |
| Negative exact-head challenge | One claimed entry changed to `b37c1fe…` and one head removed in memory; verifier returned the two expected named failures |
| `check_workbook_presentation.py` | **PASS** — four fixture twins build, audit clipping oracle clean, identity/category/context/headline/freshness assertions green |
| `check_tsn_canonical_consumer_identity.py` | **PASS** — canonical identity, carried claims, lane parity, durable provenance, success/failure/cancellation cleanup, and bounded stale sweep all green |
| `check_compare_build_freshness.py` | **PASS** — immutable snapshots, exact chunks, fail-closed Summary, and explicit freshness row green |

The first independent census attempted to locate a non-existent literal
`runtime_head_commit` key in each retained JSON and therefore reported false
schema failures. It was not retried as a product harness. Direct schema
inspection showed the stamp at `runtime.git.head` (and `runtime_head` in the
equivalence side record); the already-computed 18/18 size and SHA-256 matches
remained valid. This reviewer-tool mistake and the known Windows sandbox ACL
helper failure are reviewer-environment events, not product failures.

### HF-02 acceptance matrix

| Criterion | Verdict | Exact evidence |
|---:|---|---|
| 1. Zero material clipping, both twins | **PASS** | Retained RC-1 witness reports 2,036 cells across 42 base deliverables → 0 across 60 head deliverables; focused golden check independently reports no clipped cells |
| 2. Native-Excel labels unambiguous | **PASS** | Hash-bound native-Excel renders and AutoFit record report `columns_too_narrow: 0`; category identities are widened, not wrapped |
| 3. Context fields distinguishable from compared zeroes | **PASS** | Highway Sequence `City`, `HG`, and `Distance To Next Point` say `not compared (context)` while compared `County` remains numeric `0`; both flavors challenged by the focused check |
| 4. Values headline is readable and typed | **PASS** | 52/52 values deliverables have a non-empty cached headline; eight retained Excel-recalculated workbooks agree with typed outcomes; focused check validates both schemas |
| 5. Counts, masks, outcomes invariant | **PASS** | 42 base/head deliverable pairs: zero truth-sheet changes and zero typed-outcome differences |
| 6. Gate green and test red pre-fix | **PASS** | Retained red proof records 17 presentation failures at base and green at head; full gate 158/158; frozen self-test `SMOKE OK` |

### HF-03 acceptance matrix

| Criterion | Verdict | Exact evidence |
|---:|---|---|
| 1. False rebuild instruction absent | **PASS** | Retained dual RC-3 methods report 12 base → 0 head occurrences across the matrix corpus |
| 2. Matrix identity equals Direct identity | **PASS** | Exact full-line parity is retained for Ramp Summary, Intersection Summary, Highway Sequence, and Highway Log across Direct, Everything, and By Day; targeted check challenges the carried claims path |
| 3. Durable readable provenance | **PASS** | Workbook and sidecar `%TEMP%` counts are 18/18 base → 0/0 head; recorded canonical selections exist/read; unverifiable-origin fallback is covered by the focused check |
| 4. Capture lifecycle leaves no owned temp directory | **PASS** | Retained lifecycle witness reports zero after success/failure/cancellation and removal of the real stale orphan; targeted check covers live-age and unrecognized-directory safety |
| 5. Direct lane and semantic truth invariant | **PASS** | Same 42-pair semantic/state/count/typed-outcome witness reports zero changes, including Direct controls |
| 6. Gate green and assertions red pre-fix | **PASS** | Retained red proof records four canonical-consumer failures at base; focused test passes at head; full gate 158/158 |

### Artifact and regression matrix

| Area | Verdict | Binding |
|---|---|---|
| Source truth | **PASS** | No recount required; 42-pair cell/state/count/outcome invariance is hash-bound |
| Values / formulas | **PASS** | Both twins retained; eight installed-Excel recalculations have every SELF-CHECK `OK`, zero cached errors, and matching live/literal outcomes |
| Visual | **PASS** | Native-Excel summary/detail and provenance renders are path/size/SHA-256 bound; deliverable clipping is zero |
| Evidence | **PASS** | No evidence code changed; pinned-seed comparison has 12/12 rendered images byte-identical and matching content identities |
| Neighboring families | **PASS** | All 18 named neighboring checks and merged HF-01 check are retained green; focused freshness check is green |
| Failure / atomic behavior | **PASS** | TSN capture refuses identity drift and cleans success, failure, and cancellation; publication and ownership checks remain in the retained full gate |

### Adversarial conclusion

The likeliest false-pass mechanism was the one exposed by the first re-review:
content-equivalent results spanning different Git commits. The rebuilt manifest
separates acceptance head from later manifest-build head, actual retained files
carry the acceptance head, Git proves the intervening commits are non-runtime,
and the verifier now fails the precise missing/mismatch mutation. Independent
inspection of the product diff found no contradictory count, mask, provenance,
cleanup, freshness, or presentation path, and the focused tests challenge the
two highest-risk code paths without duplicating `RB2-A1`.

No actionable failure or evidence gap remains. Review 1 is approved; Review 2
must be performed in a separate fresh task and merge remains blocked until it
also approves.

**Reviewer signature:** Codex, Review 1 re-review — **APPROVED** —
`2026-07-31T08:06:40.8787498-07:00`.

---

## Review 2 — Codex, 2026-07-31

### Verdict

**DENIED — RETURN TO IMPLEMENTATION.** `RB2-R2-001` is a concrete product
failure in HF-02 criterion 1, not an evidence gap. Merge and cleanup remain
blocked.

### Review identity and bounded execution

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 2 |
| Implemented this bundle? | **No** |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base / independently re-derived merge-base | `896083e014d0451d5b05e5b6b024339aebc84d74` / exact match |
| Acceptance runtime head | `c483bda1716e03d0e013b25e975bd9a41c58b2c8` |
| Manifest-build head | `a38ad214932069c8bd928b078011a0964d06182b` |
| Review 1 record / Review 2 entry head | `abaade5ce4fe592a7cf74867d9133f192d539fc4` |
| Remote branch head on entry | `c5740b9e03d28afb8b295eb02182e7b106b1027d` (local was one commit ahead) |
| Worktree / branch diff on entry | Clean / branch diff check clean |
| Active review time | Approximately 27 minutes, excluding approval and sandbox waiting |
| Resource cap | Respected: no corpus generation, installed-Excel run, or full-gate repeat; one tiny product-function probe and one non-retried follow-up attempt |

### Preconditions, scope, and retained evidence

| Check | Review 2 result |
|---|---|
| Recorded-base ancestry and merge-base | **PASS** — independently re-derived as the exact recorded base |
| Changed-path scope | **PASS** — 21 paths from base; product changes remain limited to `scripts/compare_core.py`, `scripts/summary_layout.py`, `scripts/matrix_build.py`, and `scripts/compare_tsn_common.py`, with focused checks/docs/witness/verifier changes beside them |
| Acceptance manifest identity | **PASS** — `RB2-A1-manifest.json`, 1,803,195 bytes, SHA-256 `3BF96B3B248082AA3C0C2C767908E23054A61C3CDAE4ABD1B56CD3380D0F82E8` |
| Source manifest identity | **PASS** — `RB2-A1-sources.json`, 962,858 bytes, SHA-256 `44634BB6DDCD18AA8680B19DD99281CB8703C06DD302C73C9097309DC44A5798` |
| Signed Review 1 evidence reused | 18/18 claimed results bind the exact acceptance head; the verifier matched 418 runtime files and four witnesses and rejected injected missing/mismatched heads |
| Retained gates reused | Focused presentation, TSN-capture, freshness, and failure checks green; retained full implementation gate 158/158 |
| Expensive work repeated | None; the signed exact-head evidence was valid to reuse under Prompt 05 |

Review 2 did not copy Review 1's conclusion. It challenged the boundary between
the candidate-selection metric and the claimed clipping oracle in the new
shared writer.

### Independent adversarial challenge and exact discrepancy

`scripts/compare_core.py::_auto_field_widths` says it sizes for the pixel-widest
pair, but its implementation first stores only the longest string per field and
side using `len(s) > len(longest[f][slot])`. It calls `fitted_width` and the
Calibri pixel measurement only after every shorter candidate has already been
discarded. Character count and rendered pixel width are not order-equivalent.

A tiny in-memory probe called the actual product functions with one `Value`
field and these side-A candidates; side B was blank:

| Candidate | Python length | Product pixel measurement | Selection |
|---|---:|---:|---|
| `WWWWWWWWWW` | 10 | 135.25 px | Discarded |
| `iiiiiiiiiii` | 11 | 38.65 px | Selected |

The resulting stored width was `13.0`, providing 91 usable pixels. The discarded
wide-glyph value requires 135.25 pixels, so it is materially clipped by 44.25
pixels. This is an exact false-pass in the new auto-width logic, and the new
golden check contains no fixture where a shorter string is wider in pixels than
a longer string.

### Criterion disposition after the blocking failure

| Work item / criterion | Review 2 disposition | Basis |
|---|---|---|
| HF-02.1 — zero materially clipped cells | **FAIL** | Exact product-function probe above; the selection algorithm can publish a clipped identity value |
| HF-02.2 — native category-label disambiguation | Not re-adjudicated | Review 1 evidence remains retained; one blocking criterion already denies the bundle |
| HF-02.3 — context/not-compared rendering | Not re-adjudicated | No new contradiction found in source inspection |
| HF-02.4 — values `Summary!B3` | Not re-adjudicated | No new contradiction found in source inspection |
| HF-02.5 — counts, masks, typed outcomes unchanged | Not re-adjudicated | Retained Review 1 evidence reused; finding is presentation-only |
| HF-02.6 — full gate and pre-fix failure | **FAIL (coverage gap)** | Existing check does not exercise inverse character-count/pixel-width ordering |
| HF-03.1–6 | No new contradiction; not repeated | Retained Review 1 evidence remains valid, but cannot override HF-02's blocking failure |

| Review domain | Disposition |
|---|---|
| Source truth / count and mask invariance | Not implicated by this finding; retained evidence reused |
| Values and formulas | **FAIL for the shared presentation writer** — affected cell text can be clipped in either twin |
| Visual / presentation | **FAIL** — HF-02.1's zero-clipping guarantee is false |
| Evidence and exact-head binding | **PASS, reused** — Review 1's same-head remedy remains closed |
| Regression coverage | **FAIL** — no wide-glyph/shorter-string adversarial fixture |
| Failure behavior | No new contradiction found |

### Bounded environment failure

The one permitted generated-workbook/oracle follow-up reached result
serialization, then the Windows console's `cp1252` codec rejected the `≠`
character. This is a reviewer-environment failure, not a product failure. Prompt
05 forbids repeated failed expensive operations, so it was not retried. The
successful in-memory probe already used the product's own selection and pixel
measurement functions and is sufficient to establish the defect.

### Actionable finding and exact return

| ID | Priority | Failure | Required return |
|---|---|---|---|
| `RB2-R2-001` | P1 / blocking | `_auto_field_widths` preselects candidates by Python character count before pixel measurement. A shorter pixel-wider identity can be discarded, making HF-02 criterion 1 and the new golden gate false. | Select the maximum by rendered pixel width (measure every candidate pair before choosing); add a deterministic fixture in which a shorter wide-glyph value beats a longer narrow-glyph value; generate both twins and prove the written Comparison/Only-in cells pass the committed clipping oracle. Because this changes the shared writer runtime, establish a new exact acceptance head and refresh/rebind all dependent `RB2-A1` result, manifest, verifier, and witness identities without deleting prior corpus/review history. Run the scoped checks and full implementation gate, then return Prompt 05 for a fresh Review 2 re-review. |

Review 1's evidence-binding remedies remain closed and preserved as history;
they do not make the current product failure acceptable. Do not merge, clean up,
or begin RB-3. Resume Prompt 04 on the existing RB-2 branch with Claude as
implementer.

**Reviewer signature:** Codex, Review 2 — **DENIED — RETURN TO IMPLEMENTATION** —
`2026-07-31T09:50:49.5577999-07:00`.

---

## Review 2 re-review — Codex, 2026-08-01

### Verdict

**DENIED — RETURN TO IMPLEMENTATION.** The returned change closes the specific
candidate-selection defect recorded as `RB2-R2-001`: the shared width helpers
now select by rendered pixel width, the deterministic inverse-order fixture
passes for both twins, and all 21 retained claims are bound to the exact runtime
head. The same-head expanded corpus result nevertheless proves a new concrete
HF-02 criterion 1 failure. It reports 4,978 materially clipped Comparison and
Only-in cells at the declared `60.0` width cap, then calls the corpus clean by
excluding cap-bound clipping from its verdict. The frozen acceptance criterion
requires zero materially clipped cells and grants no cap exception. This is
`RB2-R2-002`.

### Review identity and bounded execution

| Field | Re-review record |
|---|---|
| Reviewer | Codex, Review 2 re-review; not the implementer |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base | `896083e014d0451d5b05e5b6b024339aebc84d74` |
| Merge base | `896083e014d0451d5b05e5b6b024339aebc84d74` — exact match |
| Acceptance runtime head | `81d5bca69b9c7d2e065db24c537c5a305be4815c` |
| Manifest-build head | `c8cbf543c50ba3ad11516f04cafd2506dc4b0e04` |
| Review-entry / reviewed branch head | `040b98190ca86cfac41f0a5b6d3942fd5c71f7a6` |
| Remote branch head on entry | `040b98190ca86cfac41f0a5b6d3942fd5c71f7a6` |
| Entry worktree | Clean |
| Active review budget | Approximately 29 minutes; stopped after the first new blocking acceptance contradiction |

The re-review stayed within the Prompt 05 resource boundary. It did not
regenerate the corpus, automate Excel, repeat the full implementation gate, or
rehash the corpus. It ran one 22.1-second independent manifest verification and
one 2.2-second deterministic presentation fixture, then used the retained
same-head artifacts and small source/history reads.

### Preconditions, scope, and evidence binding

| Check | Result | Evidence |
|---|---|---|
| Re-review authorization | **PASS** | The user explicitly invoked Prompt 05 as the Review 2 re-review of `RB2-R2-001`; the final plan routes a returned Review 2 through the same prompt. |
| Reviewer independence | **PASS** | Codex is the Review 2 reviewer; Claude is the named implementer. |
| Base and merge-base identity | **PASS** | Both resolve to `896083e014d0451d5b05e5b6b024339aebc84d74`. |
| Branch scope | **PASS** | The complete base-to-entry-head diff contains 21 paths, limited to the frozen shared-presentation runtime, its gates/tests, retained evidence, and workflow records. |
| Whitespace integrity | **PASS** | `git diff --check` was clean before this review record. |
| Exact-head manifest | **PASS** | The independent verifier matched all 418 runtime files to `81d5bca69b9c7d2e065db24c537c5a305be4815c`, rejected no retained claim, and reported 21/21 claims at that head. |
| Runtime immutability after acceptance head | **PASS** | The verifier found three later commits and no later runtime changes. |
| Retained witness binding | **PASS** | Four committed witnesses matched their recorded hashes and acceptance head. |

The independently checked manifest is
`RB2-A1-manifest.json`, 1,802,846 bytes, SHA-256
`26FED2CE29CC1F9D1920CA7AB952663EC491662FDD3DE2520AB4E7BD7A410887`.
Its source inventory is 962,858 bytes, SHA-256
`F18DBD96830B6C710642080D71057FE924E481B278A17584544947DCBE54AD98`.
The verifier reproduced runtime digest
`1CC46D40C871ABDB728DEBBB0354F8BA7A54F23A07BF382AEB6F5B945BA9A2D9`.

### `RB2-R2-001` return closure

| Required return | Result | Re-review evidence |
|---|---|---|
| Select candidates by rendered width | **PASS** | The bounded source sweep found no remaining character-count shortlist in the affected Comparison, Only-in, or Summary/category paths; the helpers measure candidate text and choose by pixel width. |
| Add inverse character-count/pixel-width fixture | **PASS** | The fixture proves its shorter wide-glyph value is pixel-wider, then passes Comparison, Only-in, and category checks in both twins. |
| Re-establish an exact acceptance head | **PASS** | All 21 claims and four committed witnesses bind to `81d5bca69b9c7d2e065db24c537c5a305be4815c`; no later runtime change exists. |
| Original finding disposition | **CLOSED** | The mechanism described by `RB2-R2-001` is no longer present. |

The direct targeted command
`build\.venv\Scripts\python.exe build\check_workbook_presentation.py`
completed successfully. Its wide-glyph checks cover the shared writer in both
twins and the affected Comparison, Only-in, and category routes.

### Independent Review 2 challenge

Review 1 and the returned unit fixture do not adjudicate long values that reach
the declared maximum column width. The committed HF-02 oracle scans only the
first eight columns and first 80 rows of Summary, Spot Check, and Comparison.
The implementer's later retained expanded-corpus result was therefore examined
as the narrowest same-head challenge to the frozen zero-clipping claim.

The retained file
`HF-02/clipping-corpus-head.json` is 125,725 bytes with independently matched
SHA-256
`1B29E9385C0C829A0976C33E4664AAE4DBE56D266CD3A7B8A44D8A78ABF3D163`.
It is recorded against the exact acceptance runtime head and reports:

| Expanded head-corpus field | Exact result |
|---|---:|
| Deliverables examined | 42 |
| Sheets examined | 126 |
| Columns examined | 3,226 |
| Materially clipped cells | **4,978** |
| Clipped at declared `60.0` cap | **4,978** |
| Clipped below cap | 0 |
| Stored `clean` verdict | `true` |

The first retained hit is
`direct-tsn\highway_log vs tsn (values).xlsx`, `Comparison!AI2`: 425 usable
pixels, 513 required pixels, and an 88-pixel shortfall. This is an actual head
cell containing the long A-not-equal-B description, not a synthetic probe.
The result's own purpose identifies the scan as criterion 1 across every column
of Comparison and Only-in, but its `clean` definition silently changes the
criterion to “no clipping below the cap.”

That semantic substitution is not allowed. HF-02 criterion 1 says that RC-1
must report **0 materially clipped cells in every regenerated workbook, both
twins**. Neither the signed Stage 3 plan nor the bundle grants an exception for
text clipped at a chosen maximum width. The cap was introduced within RB-2's
presentation work rather than inherited from the recorded base, so it cannot be
treated as a frozen external constraint. Exact-head evidence makes this a
stronger contradiction, not a waiver: the evidence accurately demonstrates
that the accepted runtime fails its frozen contract.

### Acceptance and review-domain disposition

| Acceptance criterion | Disposition | Re-review basis |
|---|---|---|
| HF-02.1 — zero materially clipped cells, both twins | **FAIL** | The same-head expanded corpus records 4,978 actual clipped cells. |
| HF-02.2–5 — labels, widths, row heights, counts/masks/typed outcomes | No new contradiction | Retained Review 1 evidence remains usable; it cannot override criterion 1. |
| HF-02.6 — permanent gate plus pre-fix proof | **FAIL** | The committed oracle's first-eight-column/80-row window misses the actual affected columns, and the new result changes `clean` semantics instead of enforcing zero. |
| HF-03.1–6 | No new contradiction | Retained Review 1 evidence remains usable, but HF-03 cannot override HF-02's blocking failure. |

| Review domain | Disposition |
|---|---|
| Source truth / counts / masks | No new contradiction; retained evidence reused |
| Values and formulas | **FAIL for deliverable presentation** — long actual cell values are not fully legible |
| Visual / presentation | **FAIL** — the frozen zero-clipping guarantee is false |
| Evidence and exact-head binding | **PASS** — the manifest and retained artifacts are coherently bound |
| Regression coverage | **FAIL** — the permanent oracle misses the affected columns and accepts cap-bound clipping |
| Failure behavior | No new contradiction found |

### Actionable finding and exact return

| ID | Priority | Failure | Required return |
|---|---|---|---|
| `RB2-R2-002` | P1 / blocking | The exact-head expanded corpus records 4,978 materially clipped Comparison/Only-in cells, all at the declared width cap, while the frozen HF-02.1 contract requires zero. The result calls itself clean only by inventing an unapproved cap exception, and the committed oracle's first-eight-column/80-row window does not see the failing cells. | Make the actual affected Comparison and Only-in cells legible so an expanded oracle reports zero materially clipped cells, or return to the plan owner for an explicit contract change; a reviewer cannot create the exception. Strengthen the permanent gate and witness to scan the actual affected rows/columns across all 60 head deliverables and fail on any materially clipped cell. If runtime changes, establish a new exact acceptance head and refresh/rebind every dependent retained result, witness, manifest, and verifier identity while preserving prior history. Then rerun the scoped/full implementation checks and return Prompt 05 for Review 2 re-review. |

The first ordinary targeted-test launch encountered the same Windows sandbox
ACL helper failure seen during read-only checks. The approved bounded launch
completed successfully; this was a reviewer-environment event, not a product
failure, and it was not counted against the implementation.

Do not merge, switch to `main`, clean up the RB-2 branch, or begin RB-3. Resume
Prompt 04 on `hotfix/rb-2-deliverable-presentation` with Claude as implementer
and preserve the closed `RB2-R2-001` history.

**Reviewer signature:** Codex, Review 2 re-review — **DENIED — RETURN TO
IMPLEMENTATION** (`RB2-R2-002`) — `2026-08-01T11:48:11.5375227-07:00`.

---

## Review 2 re-review of `RB2-R2-002` — Codex, 2026-08-02

### Verdict

**DENIED — EVIDENCE GAP.** The bounded source challenge and permanent
presentation fixture close the specific `RB2-R2-002` product mechanism: the
bundle's `60.0` cap is gone, long Comparison/Only-in values widen past it, and
cells that reach Excel's own `255.0` format ceiling wrap in both twins. The
returned acceptance evidence does not, however, supply the required expanded
scan across all 60 head deliverables.

The exact missing item is:

> One retained, hash-bound all-visible-sheet clipping result covering the 18
> By Day deliverables omitted by `clipping-corpus-head.json`, or one replacement
> result covering all 60 head deliverables, at acceptance head
> `06266eca1a4858dc5ebd000d1dd2e946249c7338`.

This is material because the omitted sheets retain the committed oracle's first
eight-column / first-80-row window. That is the precise blind spot that allowed
the prior real failure at `Comparison!AI2` to pass. A zero over 42 deliverables
cannot prove the returned requirement over 60.

### Review identity and bounded execution

| Field | Re-review record |
|---|---|
| Reviewer / pass | Codex / Review 2 re-review of `RB2-R2-002`; not the implementer |
| Implementer | Claude |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base / merge base | `896083e014d0451d5b05e5b6b024339aebc84d74` / exact match |
| Acceptance runtime head | `06266eca1a4858dc5ebd000d1dd2e946249c7338` |
| Manifest-build head | `1a0028942ffcf83b6bae7351ec11c12541aafe92` |
| Review-entry / reviewed branch head | `efdf9fc8e97bba1d222483a4bb237716dcbcaa1d` |
| Remote branch head on entry | `efdf9fc8e97bba1d222483a4bb237716dcbcaa1d` |
| Entry worktree | Clean; `git diff --check` clean |
| Runtime digest recorded | `9E411BA215C5C511C7351630A688319E9900B25B6C94BE8DBBD0A50469A38483` over 418 tracked runtime files |
| Active review budget | Approximately 30 minutes; stopped at the first material evidence gap |
| Resource budget | **RESPECTED** — no corpus generation, Excel automation, application build, full gate, corpus re-hash, or new bulk output; one 20.4-second focused fixture run |

### Preconditions and exact-head binding

| Prompt 05 precondition | Result | Evidence |
|---|---|---|
| Explicit re-review authorization | **PASS** | The user invoked Prompt 05 specifically for the Review 2 re-review of `RB2-R2-002`. |
| Branch, base, and retained roots exist | **PASS** | Local and remote branch heads agree; merge-base equals the recorded base; retained HF-02/HF-03 roots and the manifest-recorded harness location exist. |
| Exact acceptance head is recorded | **PASS** | Manifest and 20/20 claimed results name `06266eca1a4858dc5ebd000d1dd2e946249c7338`; no runtime file changed in the two later record/manifest commits. |
| Expensive acceptance operations have complete retained coverage | **FAIL** | The all-sheet expanded witness examines 42 head deliverables; the same-head measure record identifies 60, with 18 By Day deliverables outside that witness's only corpus root. |

The current `RB2-A1-manifest.json` is 1,802,846 bytes with reviewer SHA-256
`90BB704BB1D28185F7AF6F1ABA087E7D6ED7DA20C6E95E55EBA04A648FAC4DC3`.
Its source listing is 962,858 bytes with SHA-256
`7CD39FBABDB93EF98C8742D66FABA605315FDD2D934030AED11FE9F31108EC71`.
The manifest classifies 31 result records: 20 acceptance, two base-side, eight
history, and one source record; it records zero off-head, unstamped, or
mislabelled claimed results. The four committed witness bytes independently
matched their manifest hashes.

The committed verifier was launched once with a reviewer-inferred expansion of
the abbreviated `06266ec` SHA. Git rejected that incorrect expansion as
`not a tree object` before comparing a runtime file. Per Prompt 05 it was not
retried. The exact head was then read directly from the manifest and the
20-result exact-head census, witness hashes, 418-file set, and post-head Git
runtime diff were checked independently. This is a reviewer-tool error, not a
product failure.

### `RB2-R2-002` targeted closure

| Required return | Result | Evidence |
|---|---|---|
| Remove the unapproved `60.0` cap from non-wrapping columns | **PASS, targeted** | Source inspection finds no product cap; long-field fixtures widen beyond `60.0` in both twins. |
| Make Excel-ceiling values legible | **PASS, targeted** | The focused fixture drives Comparison, both Only-in sheets, data sheets, Routes, Provenance, and category rendering to `255.0` and requires qualifying wrapped cells. |
| Strengthen the permanent gate beyond column 8 / row 80 | **PASS for fixtures; incomplete for retained corpus** | `build/check_workbook_presentation.py` scans every visible fixture sheet and completed `all good` in 20.4 seconds. |
| Prove zero on all 60 regenerated head deliverables | **FAIL — EVIDENCE GAP** | `clipping-corpus-head.json` examines 42; the missing 18 By Day deliverables do not receive its all-sheet scan. |

The retained `clipping-corpus-head.json` is 114,090 bytes with independently
matched SHA-256
`3422F0E0CD9A5E324BAA0AA2FAC13EB2044F96BDAB006569F59FF3B31EBFFBCE`.
It records 42 deliverables, 364 visible sheets, 5,890 columns, zero
bundle-owned clipped cells, and 30,048 separately disclosed pre-existing hits
on `Report View`. Those `Report View` hits are not charged to RB-2 in this pass:
the base and head both omit stored widths there, the sheet replicates a printed
report, and it is outside the frozen HF-02 surface. The blocking problem is the
missing 18-deliverable coverage, not that disclosed residue.

### Independent challenge to Review 1

Review 1 could reuse the implementation's 60-deliverable **windowed** RC-1
result and the earlier 42-deliverable expanded result without checking how the
new all-sheet scan reached the By Day publication root. This re-review compared
the two result counts and then read the exact hash-bound harness:

- `measure-head.json` records 1,265 workbooks and **60 deliverables**, including
  **18** paths rooted at `byday/`; its unwindowed helper scans only `Summary`
  and `Spot Check`;
- exact harness `acc_measure.py`, SHA-256
  `878818E5FA0196DE71DFD8473C7C57AE9180216D47DC10D4EE5253173A5E0532`,
  states that Comparison, Only-in, data, and Routes are delegated to
  `acc_clipping_corpus.py`;
- exact harness `acc_clipping_corpus.py`, SHA-256
  `E6D3CE8B5C148AE8C2FF26A0CD12EC09C6296951BBC92A7AA9420F7C4FD5129D`,
  enumerates only `ROOT.rglob("*.xlsx")`; the retained result's sole root is
  `HF-02\head`, where it finds **42**, with zero skips.

Therefore the claim that the two legs leave no visible sheet unmeasured is
false for the 18 By Day deliverables: their Summary and Spot Check sheets are
unwindowed, but their Comparison, Only-in, data, Routes, Provenance, and extra
visible sheets are not.

### Acceptance and review-domain disposition

| Acceptance criterion | Re-review disposition | Basis |
|---|---|---|
| HF-02.1 — zero materially clipped cells, both twins | **NOT FINALLY ADJUDICATED** | The targeted remedy passes, but the required 60-deliverable all-sheet result is incomplete by 18. |
| HF-02.2–5 | **No new contradiction; retained evidence reused** | Native renders, context rendering, cached headline, and semantic/state/count/outcome invariance remain same-head evidence. |
| HF-02.6 — permanent gate and pre-fix proof | **PASS for the focused gate; corpus coverage incomplete** | The focused gate passes and mutation coverage is retained; it cannot replace the missing By Day corpus leg. |
| HF-03.1–6 | **No new contradiction; not repeated** | Review 1's signed same-head evidence remains usable and is not implicated by the clipping-coverage gap. |

| Review domain | Disposition |
|---|---|
| Source truth / counts / masks | No new contradiction; retained invariance reused |
| Values / formulas | Targeted presentation fixture passes both twins; full corpus conclusion withheld |
| Visual / presentation | **EVIDENCE GAP** — 18 deliverables lack an all-sheet expanded result |
| Evidence / exact-head identity | Exact-head census and hashes pass; coverage is incomplete |
| Neighboring-family regression / full gate | Retained 158/158 gate reused; not rerun |
| Failure / atomic behavior | No new contradiction found |

Source inspection also surfaced an unresolved scope question: the remedy calls
`_fit_data_columns` even though the frozen contract limits the data-sheet change
to key/back-link columns and explicitly names data columns out of scope, and it
changes `write_source_files_sheet` although `compare_tsn_common.py` is authorized
only for provenance selection. Prompt 05 requires stopping on the one material
evidence gap, so this pass does **not** issue a second finding or prescribe a
source change. The next re-review must resume that scope challenge rather than
assuming it approved.

### Actionable evidence gap

| ID | Priority | Missing item | Required return |
|---|---|---|---|
| `RB2-R2-EG-003` | P1 / blocking | The returned all-visible-sheet witness covers 42/60 head deliverables. The 18 By Day deliverables receive an unwindowed scan only on Summary and Spot Check, leaving the exact Comparison/Only-in blind spot from `RB2-R2-002` unproved. | Preserve the acceptance runtime and prior history. Produce one hash-bound expanded result from an explicit manifest-derived list of all 60 head deliverables, or add the 18 By Day paths to the existing all-sheet harness; scan every visible sheet with only documented never-rendered/out-of-scope treatment, require zero bundle-owned materially clipped cells, record exact path/size/SHA-256/runtime head, and rebuild the manifest. No product regeneration, installed-Excel rebuild, or full-gate rerun is requested unless product runtime changes. Then return Prompt 05 for a fresh Review 2 re-review. |

Do not merge, switch to `main`, clean up the RB-2 branch, or begin RB-3. Resume
Prompt 04 on the existing branch only to supply `RB2-R2-EG-003`; preserve the
closed `RB2-R2-001` and targeted `RB2-R2-002` remedy history.

**Reviewer signature:** Codex, Review 2 re-review — **DENIED — EVIDENCE GAP**
(`RB2-R2-EG-003`) — `2026-08-02T11:42:41.2637201-07:00`.

---

## Review 2 re-review of `RB2-R2-EG-003` — Codex, 2026-08-02

### Verdict

**DENIED — RETURN TO IMPLEMENTATION** (`RB2-R2-004`). The exact evidence item
requested by `RB2-R2-EG-003` is now present, complete, hash-bound, and verified:
the expanded witness covers all 60 head deliverables and reports zero owned
materially clipped cells. Approval is still blocked by the deferred source-scope
challenge. The accepted runtime knowingly changes two presentation surfaces the
signed bundle contract excludes or does not authorize.

The concrete failure is:

> `_fit_data_columns` changes ordinary data-sheet field columns that HF-02 names
> explicitly out of scope and requires to remain behaviour-identical, while
> `write_source_files_sheet` adds Source Files geometry through
> `compare_tsn_common.py`, whose allowed RB-2 surface is provenance selection.

The implementation accurately discloses both changes and asks the reviewer to
choose among scope policies. A reviewer cannot make that plan-owner decision or
silently expand the frozen contract.

### Review identity and bounded execution

| Field | Re-review record |
|---|---|
| Reviewer / pass | Codex / Review 2 re-review of `RB2-R2-EG-003`; not the implementer |
| Implementer | Claude |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base / merge base | `896083e014d0451d5b05e5b6b024339aebc84d74` / exact match |
| Acceptance runtime head | `06266eca1a4858dc5ebd000d1dd2e946249c7338` |
| Manifest-build head | `4b48df644f0068ff5ec21f814da98e102631e971` |
| Review-entry / reviewed branch head | `7fe2397240e5e0033e9d7638c6255596e5bf5fb6` |
| Remote branch head on entry | `7fe2397240e5e0033e9d7638c6255596e5bf5fb6` |
| Entry worktree | Clean; branch and remote agree; base-to-entry `git diff --check` clean |
| Runtime digest | `9E411BA215C5C511C7351630A688319E9900B25B6C94BE8DBBD0A50469A38483` over 418 tracked runtime files |
| Active review budget | Approximately 20 minutes; stopped at the first concrete acceptance contradiction |
| Resource budget | **RESPECTED** — no workbook generation, corpus re-hash, Excel automation, application build, full gate, or bulk output; one 2.2-second committed verifier run plus small JSON hashes/parses and source inspection |

### Preconditions and exact-head binding

| Prompt 05 precondition | Result | Evidence |
|---|---|---|
| Explicit re-review authorization | **PASS** | The user invoked Prompt 05 specifically for the Review 2 re-review of `RB2-R2-EG-003`. |
| Branch, base, and retained roots exist | **PASS** | Worktree clean; local and remote heads agree; merge-base equals the recorded base; retained result and harness paths exist. |
| No runtime drift after acceptance | **PASS** | Four record/evidence commits follow `06266eca`; `git diff` finds no `scripts/` or `build/` path changed after it. |
| Expensive operations are retained and bound | **PASS** | The rebuilt manifest records 21 claimed results at one acceptance head and five committed witnesses; the committed verifier reports zero problems. |
| Frozen implementation scope is respected | **FAIL** | The accepted runtime changes explicitly excluded data fields and a `compare_tsn_common.py` presentation path outside the authorized provenance-selection surface. |

The current `RB2-A1-manifest.json` is 1,808,348 bytes with reviewer SHA-256
`6256A0FB882BCD29AF5A25C97E57B81A130F0CC68325B00AEA75B8D6B17FFC9F`.
The committed verifier independently re-derived the same 418-file runtime
digest, found zero runtime files changed between the acceptance and manifest
heads, bound all 21 claimed results to the exact acceptance head, matched all
five committed witnesses, and completed `VERIFIED — 0 problem(s)`.

### `RB2-R2-EG-003` disposition — closed

| Required return | Result | Exact evidence |
|---|---|---|
| Derive the expanded corpus from the complete same-head deliverable set | **PASS** | `measure-head.json`, 1,180,593 bytes, SHA-256 `F1D47B4305385791C4B510B7E47ED04A4529A196692CFDBAAFAABDAF88FBC6F7`; the harness resolves all listed keys rather than discovering by glob. |
| Cover all 60 head deliverables | **PASS** | 18 By Day + 18 Direct-vs-TSN + 18 Everything + 6 classic-env; 60 expected, 60 examined, zero missing, zero unlisted. |
| Scan the expanded visible-sheet surface | **PASS for the requested missing lane** | 526 visible sheets and 8,200 columns; the 18 By Day deliverables add the previously omitted Comparison/Only-in/data/Routes/Provenance surface. |
| Require zero owned material clipping | **PASS** | `clipping-corpus-head.json`, 117,385 bytes, SHA-256 `2BF616FC74B8511C6A183C104CD2CA4CFD6481B22A6DD48EEE3A2A4F87EF2FF3`, records zero owned hits and `clean: true`. |
| Preserve before-state proof | **PASS** | `clipping-corpus-base.json`, 129,388 bytes, SHA-256 `2F708943F78FB83B4F74BECDC49F4857CA1A676CFF8336A0F126A1A367ACAA12`, records 42/42 and 1,648,387 owned hits. |
| Commit a compact bound witness and rebuild the manifest | **PASS** | `clipping-expanded-coverage.json`, 4,425 bytes, SHA-256 `BBB1767EDBF4EA6670C779EA209567C88BA099EFDD5B47536BEF9FE733E3740D`; exact harness `acc_clipping_corpus.py`, 22,971 bytes, SHA-256 `B24C32CBEC2D27A67733613CF753244E916FDEC4782717A0CDD337B461C4801A`. |

The 45,072 `Report View` hits remain separately disclosed as pre-existing and
unowned under the unchanged prior disposition. They are not the reason for this
denial.

### Deferred challenge to Review 1 — frozen scope

Review 1 could not have caught this later expansion: the data-field and Source
Files geometry arrived during subsequent `RB2-R2-002` remedy commits. The prior
re-review identified the scope question but correctly stopped at the material
EG-003 gap. This pass resumed it by comparing the frozen contract directly with
the accepted runtime and the implementation's new measurement.

| Frozen authority | Accepted runtime | Disposition |
|---|---|---|
| `BUNDLE.md` permits data-sheet **key and back-link** columns and explicitly excludes ordinary data columns, requiring their behaviour to stay byte-identical. | `compare_core._fit_data_columns` at line 2442, called at line 2610 and introduced by `51b5ab9`, assigns a measured width to every ordinary field column. | **FAIL — out of scope.** |
| `BUNDLE.md` permits `compare_tsn_common.py` only for provenance selection. A change outside the union must return to planning. | `write_source_files_sheet` at line 458 imports `fitted_width` and assigns widths to all four Source Files columns; the geometry arrived in `8f51021`. | **FAIL — unauthorized surface.** |

The implementation independently demonstrates the first behavior change: one
named data sheet goes from five stored-width columns in base to 71 at head,
including 68 columns at `13.0`. That floor is created by openpyxl when
`ws.column_dimensions[col]` is subscripted, not by a selected schema rule. It may
only over-widen, but the contract requires unchanged behavior; absence of clipping
does not waive scope. Likewise, Source Files had a real clipped header, but a
real defect outside the signed surface belongs in a plan-authorized follow-up.

Prompt 05 says no review may answer uncertainty by silently expanding scope.
`BUNDLE.md` is stronger: a change outside its union requires return to planning.
The review therefore cannot select any of the implementation's three proposed
scope policies.

### Acceptance and review-domain disposition

| Acceptance criterion | Re-review disposition | Basis |
|---|---|---|
| Bundle completeness / scope | **FAIL** | Accepted runtime contains excluded and unauthorized presentation changes. |
| HF-02.1 — zero materially clipped cells, both twins | **PASS as evidence; bundle not approvable** | EG-003 is closed at 60/60 and zero owned hits. |
| HF-02.2 — category labels unambiguous | **No new contradiction; retained evidence reused** | Same acceptance runtime; no runtime change in the EG-003 return. |
| HF-02.3 — context labels truthful | **No new contradiction; retained evidence reused** | Same acceptance runtime and same-head witness set. |
| HF-02.4 — values `Summary!B3` cached headline | **No new contradiction; retained evidence reused** | Same acceptance runtime and retained installed-Excel result. |
| HF-02.5 — counts, masks, typed outcomes invariant | **PASS, retained** | Same-head count witness; no runtime drift after acceptance. |
| HF-02.6 — full gate and pre-fix failure | **PASS, retained** | Prior focused fixture and full gate remain same-runtime evidence; neither was needlessly rerun. |
| HF-03.1–6 | **No new contradiction; retained evidence reused** | TSN capture/provenance/temp evidence remains exact-head bound, but it cannot override bundle scope failure. |

| Review domain | Disposition |
|---|---|
| Source truth / counts / masks | Retained same-head invariance passes |
| Values / formulas | Retained recalculation and cached-error evidence passes |
| Visual / presentation | EG-003 coverage closes at 60/60 and zero owned hits; scope still fails |
| Evidence / exact-head identity | **PASS** — verifier reports zero problems |
| Neighboring-family regression / full gate | Retained 158/158 gate reused; no runtime changed |
| Performance / atomic / failure behavior | No new contradiction; retained focused records reused |
| Frozen implementation scope | **FAIL** — excluded data fields and unauthorized Source Files geometry |

### Actionable finding and exact return

| ID | Priority | Failure | Required return |
|---|---|---|---|
| `RB2-R2-004` | P1 / blocking | The accepted runtime exceeds the signed RB-2 implementation surface: it fits explicitly excluded ordinary data columns and changes Source Files geometry through a file authorized only for provenance selection. The implementation asks the reviewer to adjudicate the plan conflict, which Review 2 has no authority to do. | Return RB-2 to the plan owner before another runtime edit. The owner must either (a) explicitly amend and re-approve HF-02/RB-2 to authorize the existing data-field and Source Files presentation behavior, reconciling the “explicit width 13.0” / zero-clipping conflict and the `compare_tsn_common.py` surface, or (b) require the out-of-scope behavior reverted and state how HF-02.1 treats those visible cells. If the chosen return changes runtime, establish a new exact acceptance head and regenerate/rebind the complete RB2-A1 set, including all 60 deliverables, Excel results, gates, witnesses, manifest, and verifier identity. If the owner authorizes the current runtime byte-for-byte, retain the exact-head evidence and rebuild only records whose identities change. Then return Prompt 05 for a fresh Review 2 re-review. |

Do not merge, switch to `main`, clean up the RB-2 branch, or begin RB-3. Preserve
the closed `RB2-R2-001`, targeted `RB2-R2-002`, and closed `RB2-R2-EG-003`
history.

**Reviewer signature:** Codex, Review 2 re-review — **DENIED — RETURN TO
IMPLEMENTATION** (`RB2-R2-004`) — `2026-08-02T14:12:49.5219567-07:00`.

---

## Review 2 re-review of `RB2-R2-004` — Codex, 2026-08-02

### Verdict

**APPROVED.** The plan-owner return required by `RB2-R2-004` is complete. At
owner-amendment and review-entry head
`2dd95862b4f407c6b24c601ad4829129768ac946`, both authoritative scope copies —
`IMPLEMENTATION-PLAN.md` and `BUNDLE.md` — expressly include ordinary
data-sheet field columns, all four `Source Files` columns, and the `Source
Files` stored-geometry surface in `compare_tsn_common.py`. The amendment
authorizes the existing acceptance runtime byte-for-byte, so the exact runtime
head, corpus, installed-Excel results, witnesses, and manifest remain valid.

The amendment also resolves the factual conflict rather than merely waiving
it: base data columns store no explicit width and render at Excel's 8.43
default; the former 13.0 premise came from the same eight-column measurement
window later disproved by `RB2-R2-001`; and ordinary data sheets are the
largest measured clipping class (736 cells versus 392 in `Comparison` on the
same twelve base deliverables). `Source Files` was not Stage 2-frozen and its
row-1 header clipping was outside the scans that skipped the wrapped header
band. The accepted openpyxl 13.0 floor can over-widen but cannot make a measured
column narrower, and the owner has explicitly carried any refinement forward.

### Review identity and bounded execution

| Field | Final re-review record |
|---|---|
| Reviewer / pass | Codex / Review 2 re-review of `RB2-R2-004`; not the implementer |
| Implementer | Claude |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Recorded base / merge base | `896083e014d0451d5b05e5b6b024339aebc84d74` / exact match |
| Acceptance runtime head | `06266eca1a4858dc5ebd000d1dd2e946249c7338` |
| Manifest-build head | `4b48df644f0068ff5ec21f814da98e102631e971` |
| Owner-amendment / review-entry head | `2dd95862b4f407c6b24c601ad4829129768ac946` |
| Remote branch head on entry | `2dd95862b4f407c6b24c601ad4829129768ac946` |
| Entry state | Clean worktree; local and remote agree; base-to-entry `git diff --check` clean |
| Runtime identity | 418 tracked files; digest `9E411BA215C5C511C7351630A688319E9900B25B6C94BE8DBBD0A50469A38483`; zero runtime files changed after acceptance |
| Active review budget | Approximately 15 minutes |
| Resource budget | **RESPECTED** — no generation, corpus re-hash, Excel automation, application build, full gate, or bulk output; one 1.6-second committed-verifier run plus bounded source, diff, and record probes |

### Owner ruling and exact-head verification

| Required return / precondition | Result | Evidence |
|---|---|---|
| Plan owner rules on the excluded data-field surface | **PASS** | Owner-authored `2dd9586` amends HF-02 in the authoritative plan and mirrored bundle to include ordinary field columns and authorizes the accepted runtime byte-for-byte. |
| Plan owner rules on `Source Files` geometry | **PASS** | The same commit explicitly includes all four `Source Files` columns and expands `compare_tsn_common.py`'s allowed surface to stored geometry. |
| The two controlling scope copies agree | **PASS** | Direct comparison of the amended HF-02 text in `IMPLEMENTATION-PLAN.md` and `BUNDLE.md`; no contradictory exclusion remains. |
| No unapproved runtime or evidence drift | **PASS** | `git diff --name-only 06266eca..2dd9586 -- scripts build` is empty; only records follow the acceptance runtime. |
| Branch and base are exact | **PASS** | Local and remote entry heads agree; `git merge-base 896083e 2dd9586` returns the recorded base exactly. |
| Retained evidence remains usable | **PASS** | Independent committed verifier re-derived the runtime digest, matched all 418 files, bound all 21 claimed results and five witnesses to `06266eca`, and returned `VERIFIED — 0 problem(s)`. |

The verified `RB2-A1-manifest.json` is 1,808,348 bytes with reviewer SHA-256
`6256A0FB882BCD29AF5A25C97E57B81A130F0CC68325B00AEA75B8D6B17FFC9F`.
The verifier itself is bound at SHA-256
`C13E4720FBD2D77B9B6CED5A0A932A85AEBA1EF6D7ADE0FBA6B7DE7871705775`.

### Acceptance-criterion coverage

| Acceptance criterion | Final result | Exact evidence |
|---|---|---|
| HF-02.1 — zero materially clipped cells, all families and both twins | **PASS** | Manifest-derived expanded result covers 60/60 head deliverables, 526 visible sheets, and 8,200 columns with zero bundle-owned hits; `clipping-corpus-head.json` is 117,385 bytes / `2BF616FC74B8511C6A183C104CD2CA4CFD6481B22A6DD48EEE3A2A4F87EF2FF3`. Base proof covers 42/42 and 1,648,387 owned hits at `2F708943F78FB83B4F74BECDC49F4857CA1A676CFF8336A0F126A1A367ACAA12`. |
| HF-02.2 — category labels are unambiguous | **PASS** | Retained stored-width and native-Excel metric/render results are exact-head manifest entries; the focused permanent presentation gate passed. |
| HF-02.3 — context labels are truthful | **PASS** | Retained comparison witnesses and the focused gate prove `not compared (context)` for wholly-context fields while compared zeroes and Highway Log per-cell context retain their semantics. |
| HF-02.4 — values `Summary!B3` is consumable without recalculation | **PASS** | Exact-head `excel-recalc.json` (120,757 bytes / `ADBD1153D3652645880A4FDD4DFEBF1B08B4D904AFB753C8CB1A7DE8542B3F09`) and the retained headline checks pass with zero cached errors. |
| HF-02.5 — cells, masks, counts, and typed outcomes stay invariant | **PASS** | Committed `count-invariance.json` (23,182 bytes / `4E909DE624CF94F9C13C20CB2B2F84C0706530EE382ABB38438D2B9C8B5CC3F3`) and exact-head `invariance.json` preserve the semantic result set. |
| HF-02.6 — durable red-to-green gate and complete bound evidence | **PASS** | Base/head witness `D272FA310C6E8E8D474CB302789E76CC9D7F7D117103ECCEA2CE952F0B8F7B5F`, expanded coverage witness `BBB1767EDBF4EA6670C779EA209567C88BA099EFDD5B47536BEF9FE733E3740D`, exact harness `B24C32CBEC2D27A67733613CF753244E916FDEC4782717A0CDD337B461C4801A`, retained full gate 158/158, and focused presentation check all pass. |
| HF-03.1 — rebuilt TSN claims remain available on matrix captures | **PASS** | Exact-head `tsn_rebuild.json` and provenance witness retain the same canonical source identity and no false rebuild instruction. |
| HF-03.2 — published provenance names durable canonical inputs | **PASS** | `tsn-provenance-scope.json` (21,144 bytes / `9AAED68A2E5715EF8F797ABE8F017DB3303C8685078948CB19A48176AC08A0CE`) records zero `%TEMP%` paths and readable durable selections. |
| HF-03.3 — sidecar/capture claims are complete | **PASS** | The same-head manifest and focused canonical-consumer test bind the full sidecar payload for all required lanes. |
| HF-03.4 — capture cleanup covers success, failure, and cancellation | **PASS** | `temp-capture-lifecycle.json` (2,019 bytes / `279D285E9A72067E2BF7435EB415B025516F62FB1F1193CC3F86F7870B043F22`) records zero remaining run-owned temp directories. |
| HF-03.5 — neighboring behavior and published outcomes remain invariant | **PASS** | Retained generation-equivalence, count/state/outcome, provenance, publication, and sibling checks are all exact-head manifest entries. |
| HF-03.6 — permanent gates and failure behavior | **PASS** | Focused canonical-consumer, freshness, pairing, skip/warn, publication, cache, and artifact-store gates are included in the retained 158/158 full gate; no runtime changed afterward. |

The expanded clipping witness separately discloses 45,072 `Report View` hits
as pre-existing and unowned under the unchanged disposition. They are neither
hidden nor charged to this bundle.

### Review-domain matrix

| Review domain | Final disposition |
|---|---|
| Source truth / counts / masks | **PASS** — same-head invariance and typed-outcome witnesses remain exact |
| Values / formulas | **PASS** — both twins, cached headline, self-checks, and zero cached-error result remain bound |
| Visual / presentation | **PASS** — 60/60 expanded coverage, zero owned clips, retained native-Excel metrics/renders |
| Evidence eligibility / provenance | **PASS** — durable source identities; no published `%TEMP%` path or false rebuild instruction |
| Neighboring-family regression / full gate | **PASS (retained)** — 158/158; no runtime drift, so the gate was not duplicated during review |
| Performance / atomic publication / stale state / failure behavior | **PASS (retained)** — focused transaction, freshness, cache, cleanup, and publication records remain same-head |
| Frozen implementation scope | **PASS** — both controlling copies expressly authorize every disputed accepted-runtime surface |

### Review 2 challenge to Review 1

Review 1 could not assess the later `RB2-R2-001` and `RB2-R2-002` remedies and
therefore missed the wide-glyph selection failure, the remaining bound-width
clip, the incomplete 18-deliverable all-sheet evidence lane, and the resulting
scope conflict. Review 2 did not copy Review 1: it found and forced closure of
each issue in sequence, then refused to decide `RB2-R2-004` from the reviewer
chair. This final pass challenged the owner's answer by checking both
authoritative copies, their factual reconciliation, the complete branch diff,
and byte-for-byte runtime identity. The retained evidence was then revalidated
with the independent committed verifier. No contradiction remains.

### Final decision

No actionable failure or evidence gap remains. Review 1 and Review 2 both
approve, neither reviewer implemented the bundle, and the owner has resolved
the only planning-authority question. RB-2 is **JOINTLY APPROVED** and eligible
to merge.

**Reviewer signature:** Codex, Review 2 re-review of `RB2-R2-004` —
**APPROVED** — `2026-08-02T14:50:47.3393655-07:00`.
