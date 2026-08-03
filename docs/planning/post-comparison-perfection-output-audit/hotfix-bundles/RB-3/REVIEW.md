# `RB-3` — Adversarial Review Record

Status: **DENIED — RETURN TO IMPLEMENTATION**

## Review 1 verdict — 2026-08-02

**DENIED — EVIDENCE GAP.** Prompt 05 requires every expensive acceptance
operation to be represented by a retained, hash-bound result before substantive
review begins. RB-3 records exact base and runtime heads, but the retained set
does not contain the frozen-input/artifact manifest its implementation record
names and does not otherwise bind the complete `RB3-A1` claim to one exact
runtime and frozen input set.

This is the one exact missing item:

> A committed `RB3-A1` acceptance manifest for runtime head
> `dd922f7b3b726a87912a26e92d7b5d930d90451e`, binding every claimed retained
> input, deliverable, result, render, gate, and committed witness by exact path,
> byte size, SHA-256, frozen-source identity, and generation metadata.

The implementation says frozen input identities are recorded in
`rb3-a1-generation.json / rb3-a1-artifacts.json`. The latter file does not exist
anywhere under the retained HF-04 root. The generation record contains reused
paths, counts, outcomes, and timings, but no runtime-head or SHA-256 binding for
those reused inputs. `rb3-a1-head.txt` separately names `dd922f7…`, while
`rb3-a1-sweep.json` separately inventories output paths, sizes, and hashes; it
does not bind the frozen inputs, acceptance-result files, generation metadata,
or runtime head. The Excel, recount, store-integrity, gate, self-test, render,
and committed-witness records likewise remain separate claims rather than one
verifiable exact-head acceptance set.

No reviewer-created manifest, corpus regeneration, installed-Excel rebuild,
whole-corpus recount, full gate, application build, or replacement acceptance
run was performed. Prompt 05 requires stopping on this precondition failure and
returning one bounded item to implementation.

## Review identity and budget

| Field | Value |
|---|---|
| Reviewer / pass | Codex / Review 1 |
| Implemented bundle? | **No** — implementer is Claude |
| Bundle / work items | `RB-3` / `HF-04` |
| Branch | `hotfix/rb-3-ramp-detail-layout` |
| Recorded base / merge base | `194b7ee8da095f0300e7e635bb7e7af78643b685` / exact match |
| Acceptance runtime head | `dd922f7b3b726a87912a26e92d7b5d930d90451e` |
| Review-entry / review-record head | `43c6336ce33bddad68c2d07fff6a4bd19e000c94` |
| Remote branch head on entry | `43c6336ce33bddad68c2d07fff6a4bd19e000c94` — verified with `git ls-remote` |
| Runtime drift after acceptance | **None** — `dd922f7..43c6336` changes only four committed witnesses and `IMPLEMENTATION.md` |
| Review 2 | **BLOCKED** — do not run until this return is implemented and Review 1 re-reviews |
| Merge | **BLOCKED** |
| Elapsed active review | Approximately 24 minutes |
| Resource budget | **RESPECTED** — no generation, Excel invocation, build, full gate, full recount, corpus re-hash, or new bulk output; only Git/doc/small-record inspection |

The Windows sandbox ACL helper failed on several ordinary repository reads, so
the bounded read-only checks were run through the approved host shell. One
PowerShell small-file hash summary had a syntax error before any hash operation
started and was not retried. These are reviewer-environment events, not product
failures.

## Precondition audit

| Prompt 05 precondition | Result | Evidence |
|---|---|---|
| Review-1 status is `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW` | **PASS on entry** | The controlling top-level status in `START-HERE.md`, `IMPLEMENTATION-PLAN.md`, `BUNDLE.md`, and `IMPLEMENTATION.md` agreed on entry |
| Hotfix branch and retained output root exist | **PASS** | Local HEAD, local remote-tracking ref, and remote branch all resolved to `43c6336…`; the HF-04 retained root exists |
| Exact base SHA is recorded | **PASS** | `194b7ee8…`; `git merge-base` returned that exact commit |
| Exact acceptance runtime head is recorded | **PASS** | `IMPLEMENTATION.md` and `rb3-a1-head.txt` name `dd922f7…`; later commits are record/witness-only |
| Every expensive acceptance result is retained and hash-bound to that head and the frozen inputs | **FAIL** | The named `rb3-a1-artifacts.json` is absent; no equivalent complete manifest joins the separate head, input, output, result, render, gate, and witness claims |

Because a precondition failed, no HF-04 acceptance criterion was finally
adjudicated and no targeted product test was started.

## Evidence inspected and bounded commands

| Evidence / command | Binding / result |
|---|---|
| Branch identity | Clean worktree on full head `43c6336ce33…`; `origin/hotfix/rb-3-ramp-detail-layout` and `git ls-remote` agree |
| Complete diff boundary | Recorded base is the merge base; base-to-entry diff has 18 files, 1,423 insertions / 97 deletions, and `git diff --check` is clean |
| Runtime lineage | `c9b55b6` implementation, `dd922f7` final runtime/Notes precision, `d7f39cd` witnesses/record, `43c6336` acceptance-head correction; no runtime file changes after `dd922f7` |
| Retained head marker | `rb3-a1-head.txt`, 41 bytes, names `dd922f7b3b726a87912a26e92d7b5d930d90451e` but is not joined to a complete artifact/result manifest |
| Retained generation record | `rb3-a1-generation.json`, 46,337 bytes; records paths, counts, outcomes, timings, and 16/16 successful harness steps, but not input hashes or runtime head |
| Retained output sweep | `rb3-a1-sweep.json`, 10,017 bytes; inventories 27 entries / 25 unique deliverable paths with byte sizes and SHA-256 plus presentation/evidence assertions, but not frozen-input identities, result files, generation metadata, or runtime head |
| Other retained results | `rb3-a1-excel.json` 19,370 bytes; recount 4,529; pre/post store-integrity 4,488 / 5,060; final gate log 6,586; self-test log 28,008; all located, none covered by an exact-head master manifest |
| Missing named record | Recursive exact-name and `*artifact*.json` searches under the HF-04 root returned no `rb3-a1-artifacts.json` or alternate artifact manifest |
| Committed witnesses | Four HF-04 JSON witnesses are present at the review-entry head; their Git identity does not bind the retained local result set or reused frozen inputs to `dd922f7` |
| Preliminary source challenge | The changed dual-layout dispatch, mixed-layout projection/keying, consumability downgrade, and self-only null projection were inspected only far enough to identify plausible challenge surfaces; no acceptance disposition was issued after the failed precondition |

The deliverable hashes recorded in the sweep and the Git identities above prove
that individual records exist. They do not cure the missing binding among those
records, the reused frozen inputs, and one exact execution runtime.

## Acceptance and review-domain matrices

| Criterion / gate | Review 1 result | Exact reason |
|---|---|---|
| HF-04 criteria 1–7 | **NOT ADJUDICATED** | Prompt 05 requires stopping at the failed evidence precondition |
| Values / source truth / discrepancy counts | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | No complete frozen-input and runtime-head binding |
| Formulas / installed Excel | **RETAINED RESULT LOCATED; NOT FINALLY ADJUDICATED** | Recalculated workbook hashes are separate from the missing complete acceptance manifest |
| Visual / presentation | **RETAINED RENDERS DESCRIBED; NOT FINALLY ADJUDICATED** | Render coverage is not joined to the exact-head acceptance set |
| Evidence prohibition / sibling parity | **RETAINED RESULTS LOCATED; NOT FINALLY ADJUDICATED** | Separate sweep/witness claims lack the complete manifest binding |
| Neighbor regression / full gate / frozen self-test | **RECORDED; NOT FINALLY ADJUDICATED** | Logs exist but are not bound into the complete exact-head claim |
| Performance / atomic publication / stale cache / failure behavior | **NOT FINALLY ADJUDICATED** | Review stopped at the precondition gap |

## Actionable evidence gap

| ID | Priority | Missing item | Required return |
|---|---|---|---|
| `RB3-R1-EG-001` | P1 / blocking | The complete `RB3-A1` acceptance set is not bound to runtime head `dd922f7…` and the reused frozen inputs; the implementation record's named `rb3-a1-artifacts.json` is absent. | On the existing RB-3 branch, supply one committed manifest for `dd922f7…` covering every claimed input, deliverable, result, render, gate, and witness by exact path, byte size, SHA-256, frozen-source identity, and generation metadata. Include a verifier that fails on any missing/mismatched file, source identity, or runtime head. Correct the implementation record's nonexistent-file reference. Existing bulk artifacts may be retained if their exact bytes and sources can be proved; regenerate or rerun only any item that cannot be bound. Then return Prompt 05 for Review 1 re-review. |

**Reviewer signature:** Codex, Review 1 — **DENIED — EVIDENCE GAP** —
`2026-08-02T20:58:01.7470232-07:00`.

Do not merge and do not begin Review 2. Resume Prompt 04 on the existing
`hotfix/rb-3-ramp-detail-layout` branch only to supply `RB3-R1-EG-001`.

---

## Review 1 re-review — Codex, 2026-08-02

### Verdict

**DENIED — EVIDENCE GAP.**

`RB3-R1-EG-001` is **CLOSED**. The remedy supplies the previously missing
complete manifest, binds the retained acceptance set to runtime head
`dd922f7b3b726a87912a26e92d7b5d930d90451e`, and verifies every present byte
in both the cheap and full corpus/archive paths.

One narrower blocking item remains:

> **`RB3-R1-EG-002`:** supply a corrected committed verifier that returns
> nonzero when any declared item covered by an explicitly requested
> verification mode is absent. The current verifier prints `SKIPPED` and
> succeeds for missing corpus roots, result files, the TSN raw input, and
> archives, so it can certify an incomplete acceptance set.

This is one evidence-tooling gap, not a product-code failure. Review 1 stops at
that Prompt-05 precondition and does not adjudicate HF-04 criteria 1–7.

### Review identity, entry state, and budget

| Field | Re-review record |
|---|---|
| Reviewer | Codex, independent non-implementer |
| Bundle / branch | `RB-3` / `hotfix/rb-3-ramp-detail-layout` |
| Bundle base | `194b7ee8da095f0300e7e635bb7e7af78643b685` |
| Acceptance runtime | `dd922f7b3b726a87912a26e92d7b5d930d90451e` |
| Initial denial record | `df5c6fc18710c5e82b2626d337982f3eb3716489` |
| Remedy / review-entry head | `69231d37765f10b2d48491a6abef6f2bce2f3c45` |
| Pushed-head check | Local `HEAD`, remote-tracking ref, and `git ls-remote` all matched `69231d3…`; entry worktree was clean |
| Remedy scope | Ten evidence/status files; no product/runtime file changed after `dd922f7…` |
| Active review time | Approximately 13 minutes; within the 30-minute Prompt-05 cap |
| Resource budget | No Excel launch, regeneration, render pass, or acceptance rerun; verifier operations each completed in under 30 seconds |

The remedy range `df5c6fc…69231d3` passed `git diff --check`. Its runtime tree
remains the exact accepted `dd922f7…` tree; all later commits are evidence and
status records.

### `RB3-R1-EG-001` disposition

| Item | Exact identity / result |
|---|---|
| Complete manifest | `rb3-a1-artifacts.json`; 344,312 bytes; SHA-256 `F63F4A3682D5F8585C71EA3A9C60B02B56AC7F98A1CB1BC42366C24A247E5BB1` |
| Committed verifier | `rb3-verify-manifest.py`; 16,327 bytes; SHA-256 `93D736D74B9E8FC4346A87C9122E1D4E461379E8961BB68CA6AE3BC1C99839EB` |
| Cheap exact-head verification | Exit 0: 417 runtime files exact, lineage exact with zero later runtime changes, 30 claimed entries at the exact head, four witnesses bound, `VERIFIED — 0 problems` |
| Full `--corpus --zips` verification | Exit 0: 504 frozen-input files across four roots plus TSN raw, 1,009 replicas, all declared deliverable roots, 30 results, 10 harness records, and both 252-member archives rehashed; `VERIFIED — 0 problems` |

These results close the original missing-manifest gap and establish that every
item which is present matches the committed claim. Existing bulk artifacts can
be retained.

### Adversarial fail-closed challenge

A bounded in-memory negative probe called the committed verifier's
`rehash_block` with a definitely absent requested root. The observed output
was:

```text
SKIPPED missing-root-probe not present
failure_count 0
```

The probe wrapper rejected that result, but the committed verifier itself
recorded no failure. Source inspection shows the same mechanism at each
relevant boundary:

| Verifier surface | Committed behavior | Re-review result |
|---|---|---|
| `rehash_block`, lines 260–264 | Missing declared root prints `SKIPPED` and returns without adding a problem | **FAIL — reproduced false pass** |
| TSN raw input, lines 293–299 | Missing declared raw input prints `SKIPPED` | **FAIL — static path has no failure** |
| Results, lines 314–320 | Missing declared result prints `SKIPPED` and continues | **FAIL — static path has no failure** |
| Archives, lines 331–335 | Missing requested archive prints `SKIPPED` and continues | **FAIL — static path has no failure** |

The successful full run proves current bytes, but cannot prove the verifier's
required failure behavior. Because Prompt 05 and `RB3-R1-EG-001` require a
verifier that fails on **any missing or mismatched file**, a success exit with a
declared item removed is a blocking false negative.

### Acceptance and review-domain matrices

| Criterion / gate | Review 1 re-review result | Exact reason |
|---|---|---|
| HF-04 criteria 1–7 | **NOT ADJUDICATED** | Prompt 05 stops at the fail-closed evidence precondition |
| Values / source truth / discrepancy counts | **RETAINED RESULTS VERIFIED; NOT FINALLY ADJUDICATED** | Present bytes are exact; missing-item detection is incomplete |
| Formulas / installed Excel | **RETAINED RESULT VERIFIED; NOT FINALLY ADJUDICATED** | No recalculation rerun was required for this bounded return |
| Visual / presentation | **RETAINED RESULTS VERIFIED; NOT FINALLY ADJUDICATED** | The re-review did not proceed beyond the evidence precondition |
| Evidence prohibition / sibling parity | **RETAINED RESULTS VERIFIED; NOT FINALLY ADJUDICATED** | The manifest binding is fixed; the verifier still does not fail closed |
| Neighbor regression / full gate / frozen self-test | **RETAINED RESULTS VERIFIED; NOT FINALLY ADJUDICATED** | Runtime and retained results did not drift |
| Product implementation | **NO FAILURE IDENTIFIED IN THIS RE-REVIEW** | The denial is confined to committed evidence-verifier behavior |

### Actionable evidence gap

| ID | Priority | Missing item | Required return |
|---|---|---|---|
| `RB3-R1-EG-002` | P1 / blocking | The committed verifier can return success when explicitly requested declared evidence is absent. | On the existing RB-3 branch, make requested corpus/archive verification fail nonzero for every absent declared corpus root, replica root, TSN raw input, result, harness record, or archive. Add bounded negative checks covering the missing-root, missing-result/raw, and missing-archive paths, then rerun the existing cheap and full verifier commands. Preserve the current manifest, frozen corpus, deliverables, witnesses, and `dd922f7…` acceptance runtime unless any byte changes; do not regenerate or rerun Excel/gates merely to satisfy this return. |

### Reviewer environment notes

The Windows sandbox ACL helper failed before one read-only inspection and before
the required patch mechanism could read the files. The inspection and a
sandbox-blocked negative probe were rerun through the approved host shell. The
review/status edits used narrow atomic UTF-8 `git apply` patches after
`apply_patch` failed at the ACL boundary. These were reviewer-environment
events, not product or acceptance failures.

**Reviewer signature:** Codex, Review 1 re-review —
**DENIED — EVIDENCE GAP** — `2026-08-02T21:23:12.2917858-07:00`.

Do not merge and do not begin Review 2. Resume Prompt 04 on the existing
`hotfix/rb-3-ramp-detail-layout` branch only to supply `RB3-R1-EG-002`.
