# `RB-2` — Adversarial Review Record

Status: **DENIED — EVIDENCE GAP**

## Verdict

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
