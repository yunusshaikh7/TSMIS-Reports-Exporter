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
