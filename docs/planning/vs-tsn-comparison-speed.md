# VS TSN comparison speed: implementation ledger

Branch: `codex/vs-tsn-comparison-speed`

Remote: `origin/codex/vs-tsn-comparison-speed`

Started: 2026-08-19

## Goal and correctness boundary

Make repeated comparisons against the effectively locked TSN library materially
faster. Standard mode remains the conservative baseline. Experimental work is
enabled only by explicit toggles, cache identities are mode/version scoped, and
no optimization may change the typed comparison outcome.

Every item below is implemented, tested, benchmarked, and committed separately
on the same branch. Generated-package equivalence is required where the output
contract is unchanged. The optional Compact output deliberately has a different,
documented workbook contract and therefore uses a separate cache identity.

## Shipped foundation

- [x] Add a persisted, default-off **Fast vs TSN (experimental)** toggle.
- [x] Reuse one attempt-local TSN certification and compare an immutable captured
  workbook.
- [x] Add a Fast-mode composite-style cache.
- [x] Version comparison-cache identity by execution mode.
- [x] Recheck TSN status at the atomic publication boundary.
- [x] Prove exact typed outcomes and stable OOXML-member equivalence on real
  Intersection Detail and Ramp Detail exports.
- [x] Push foundation commit `d3cece1d4fc62a392d0b194c2042b81b2f007f3a`
  to GitHub.

Foundation measurements:

| Corpus | Standard | Fast foundation | Improvement |
| --- | ---: | ---: | ---: |
| Intersection Detail | 380.779 s | 241.905 s | 36.47% / 1.574x |
| Ramp Detail | 108.958 s | 98.791 s | 9.33% / 1.103x |

## Improvement 1: direct OOXML post-write validation

Status: **completed**

Replace Fast mode's two post-write `openpyxl` read-only reloads with a fail-closed
OOXML package validator. It will resolve sheets through workbook relationships,
verify required package parts and worksheet XML, and compute Comparison
Status/Diffs counts directly from XML. Standard mode keeps its existing validator.

Correctness gates:

- Match current Comparison counts on representative and real workbooks.
- Reject malformed ZIP/XML, missing expected sheets, duplicate/missing headers,
  invalid statuses, and invalid Diffs values.
- Preserve generated XLSX bytes/stable package members because validation is
  post-write only.
- Run focused artifact-store/schema checks, then benchmark Ramp Detail.

Profile evidence: current Fast Ramp validation reopens the finished workbook
twice. The existing count path took 10.354 s; a direct XML prototype returned the
same `(508, 215, 15419)` in 1.329 s (7.79x for that operation).

Completed result:

- Direct package/count read on the real Ramp artifact: 9.795 s to 2.174 s
  (4.50x).
- Same-day end-to-end control with identical Fast serialization: 68.780 s with
  legacy validation to 53.117 s with direct validation (22.77%, 1.295x).
- Typed outcome and all 20 stable OOXML members were byte-exact; stable package
  SHA-256: `85a43aa3fa805a9aa5d2b04a6f1257b9b8c90be8ce2c5634a45400f102436d03`.
- Direct and openpyxl gates agreed on all focused valid/invalid schema cases;
  malformed package, worksheet, and expected-sheet tests retained last-good
  artifacts with no temp leak.

## Improvement 2: cheaper Fast-mode cell construction

Status: **completed**

Remove deep style-object hashing/equality from the hot cell-writing loop by using
identity-checked style-cache keys. For guarded literal cells, bind the value once
instead of constructing with a value and assigning the same value again.

Correctness gates:

- Keep Standard mode untouched.
- Preserve formula-injection guards and all cell value/data-type behavior.
- Require exact typed outcomes and stable OOXML-member equivalence.
- Run focused Fast-mode checks and benchmark Ramp Detail.

Profile evidence: `_styled_cell` was called 1,339,433 times in the profiled Ramp
run. Deep serialisable hashing/equality consumed roughly 24 cumulative seconds,
and guarded value binding was performed twice.

Completed result:

- Fast style-cache lookup now uses identity keys with retained component
  references; equal-but-distinct objects remain separate cache entries and
  converge to the same registered style.
- Fast guarded literals bind once. Standard mode retains its historical cell
  construction sequence.
- Real Ramp comparison: 53.117 s to 47.931 s (9.76%, 1.108x) over improvement 1.
- Typed outcome and all 20 stable OOXML members remained exact with package
  SHA-256 `85a43aa3fa805a9aa5d2b04a6f1257b9b8c90be8ce2c5634a45400f102436d03`.
- Cumulative same-day reduction versus Fast serialization with legacy validation:
  30.31%; current speed is 2.27x the original Standard Ramp baseline.

## Improvement 3: TSN-library normalized-row cache

Status: **in progress**

Move repeatable TSN parsing/normalization work behind a library-owned cache. The
cache is bound to the consolidated workbook's identity/SHA, report type, and a
normalizer schema version. Captured TSN inputs carry only a matching, validated
cache; a missing, corrupt, stale, or unsupported cache fails open to the current
XLSX loader and can never certify a mismatched workbook.

Correctness gates:

- Canonical TSN-library inputs only; arbitrary/manual workbooks bypass the cache.
- Atomic publication and strict identity/version validation.
- Exact normalized row/type equality against the existing loader for every
  supported report exercised by the corpus.
- Corruption, stale-identity, missing-cache, and concurrent-publication tests.
- Cold-cache and warm-cache benchmarks, plus end-to-end Ramp/Intersection runs.

## Improvement 4: separate Compact comparison toggle

Status: **pending**

Add a second persisted, default-off **Compact comparison (experimental)** toggle.
It is an explicit output-contract tradeoff, separate from Fast execution. Compact
mode omits heavyweight audit/duplicate-data surfaces while retaining the decision
workbook: summary, comparison results, one-sided rows, notes/provenance, and any
report-specific route/result surface required for use.

Before implementation, every reference to candidate omitted sheets will be
mapped so Compact workbooks contain no broken formulas, hyperlinks, defined
names, or self-check claims. Compact and full outputs use distinct cache identities
and filenames/status descriptions where necessary.

Correctness gates:

- Toggle is default off and has no effect on Standard/full output.
- Exact typed comparison outcome and row-level comparison result equality.
- No references to omitted sheets and no formula errors.
- Focused persistence/routing/cache tests and full visual QA.
- Measure wall time, XLSX size, and peak/output surface reduction.

## Final release gate

- [ ] All four improvements completed as separate commits on this branch.
- [ ] Focused checks pass after each improvement.
- [ ] Full repository check suite passes.
- [ ] Real Ramp Detail and Intersection Detail cumulative benchmarks recorded.
- [ ] Full Fast output remains equivalent to Standard under the established
  stable-member comparison.
- [ ] Compact output receives formula scan and visual QA.
- [ ] README, changelog, and comparison-engine documentation updated.
- [ ] Branch pushed to GitHub and remote head verified.

## Progress log

- 2026-08-19: Foundation committed and pushed. Profiling identified validation,
  cell construction, repeat TSN normalization, and optional workbook surface area
  as the next four bounded opportunities.
- 2026-08-19: Improvement 1 completed. Direct OOXML validation removed duplicate
  post-write workbook loads in Fast mode with a controlled 22.77% Ramp speedup
  and exact output equivalence. Improvement 2 started.
- 2026-08-19: Improvement 2 completed. Identity-keyed style reuse and single-bind
  guarded literals produced another 9.76% Ramp reduction with exact output.
  Improvement 3 started.
