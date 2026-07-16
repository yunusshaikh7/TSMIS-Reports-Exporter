# Phase 3 comparison decision gates

Last updated: 2026-07-12  
Scope: Phase 3 (`compare_core`) entry decisions and evidence  
Implementation state: **Phase 3 complete; D2/D3, corrected independent oracle, E1
installed-Excel parity, E2 exact/capped pairing, opaque identity, snapshots,
cancellation, scaled schema-v3 persistence, and the clean production canary are green**

This record separates architecture that is already fixed by the authorized remediation
plan from semantic recommendations that still require explicit user/domain approval. It
does not turn an agent recommendation, historical plan, canary count, or prior workbook
into an approved business rule.

## Status vocabulary

- **FIXED / APPROVED ARCHITECTURE** — already authorized as a non-negotiable design
  constraint. Implementation may choose mechanics, but may not weaken the constraint.
- **RECOMMENDED — APPROVAL PENDING** — the proposed concrete semantic rule. Do not code
  it as settled behavior until an approval record is appended below.
- **REQUIRED EVIDENCE** — proof needed regardless of which semantic option is approved.
  Evidence can disprove an implementation, but cannot choose a business rule.
- **NOT AN ORACLE** — useful regression evidence that does not independently establish
  the expected answer for the disputed case.

The user/domain owner approved the complete recommended D2/D3 bundle on 2026-07-12.
The preserved recommendation text below is now the implementation contract; the oracle
and acceptance evidence remain mandatory rather than being waived by approval.

## Decision summary

| Gate | State | Rule |
|---|---|---|
| One equality engine | **FIXED / APPROVED ARCHITECTURE** | One typed Python compared-cell result owns normalization, assertiveness, equality, and display; every workbook and consumer surface projects that same result. |
| D2 edge semantics | **APPROVED 2026-07-12** | Case-sensitive ordinary text; narrowly unsigned Med-Wid normalization; only actual Boolean cells fold to `TRUE`/`FALSE`; no universal tab/CR/LF/NBSP folding. |
| D3 within cap | **APPROVED objective and tie rule** | Exact rectangular minimum-cost assignment for every group within the product cap; deterministic lexicographic tie-breaking; persisted trace and quality. |
| D3 above cap | **APPROVED 2026-07-12** | Keep a useful deterministic fallback result, but mark the comparison `partial`/incomplete with `pairing_quality=capped`; never certify a match or optimal pairing. |
| Route-1 | **REQUIRED EVIDENCE / NOT AN EDGE-SEMANTICS ORACLE** | Preserve the bound 969-cell regression unless a reviewed source-level explanation proves a deliberate change. Route-1 has none of the controversial D2 tokens. |
| `CORE-ID-78-XLSX-TSN` | **BASELINE-BOUND / ACCEPTED 2026-07-12** | The immutable 218-member manifest, corrected independent typed oracle, production values/formulas generation, schema-v3 payload, and installed-Excel parity agree exactly. |

## Fixed Phase 3 architecture

The following is already approved architecture and is not reopened by the D2/D3
choices:

1. A pure typed compared-cell result carries, at minimum, the two typed source values,
   normalized values, whether the field asserts equality, the equality result, and its
   display value. Display text is not truth state.
2. Python counts are canonical. Values cells, live formulas, Summary, Comparison-row
   `Diffs`, Spot Check, conditional formatting, Report View input, Matrix/day/baseline,
   validation, and later evidence all consume the same typed result or its persisted
   generation. Excel formulas are a projection of the Python policy, not a second
   equality engine.
3. Literal difference-marker text is content. No count, color, verdict, or cache may
   infer a difference by searching display strings for `≠`.
4. Literal Excel error tokens remain literal text, and blank remains distinct from zero.
   Precision that reaches the engine intact must not be lost merely because Excel would
   coerce a value past its numeric precision.
5. Duplicate-pair cost is computed only from the same asserting compared-cell equality
   state. Context/non-asserting cells cannot influence assignment.
6. Pairing emits a typed deterministic trace and quality result. A capped or otherwise
   non-exact assignment cannot silently claim exact/optimal quality.
7. E1 (equality state) and E2 (identity/pairing) remain separate re-proof batches. Each
   batch runs the focused adversarial fixtures, full offline gate, bound real-data
   canaries, and installed-Excel `CalculateFullRebuild` parity before the next batch.

## D2 — recommended canonical equality choices

**Status: APPROVED 2026-07-12.**

The recommended package preserves ordinary current Python behavior, makes anomalous
data visible, and avoids a broad normalization rule whose real-data effects have not
been established.

### D2.1 Ordinary text is case-sensitive

Compare normalized ordinary text with ordinal, case-sensitive equality. The formulas
projection must use a case-sensitive construction such as `EXACT`, not Excel's
case-insensitive `=`.

Examples:

| Side A | Side B | Recommended result |
|---|---|---|
| `ABC` | `ABC` | equal |
| `ABC` | `abc` | different |
| `6V` | `6v` | different |

Both operational systems normally emit uppercase data, so a case-only difference is
an anomaly worth surfacing. Route-1 contains lowercase only in ten header labels on
each side, not in the compared data that would decide this rule.

### D2.2 Keep ASCII-space trimming narrow

Retain the current engine-level ASCII U+0020 behavior: strip leading/trailing ASCII
spaces and collapse internal runs of ASCII spaces. **Do not universally fold** tabs,
CR, LF, other control characters, or NBSP (`U+00A0`) into ordinary spaces.

Those characters remain significant unless a specific loader has a documented domain
reason, versioned normalization, and family canary for transforming them. Existing
report-specific transformations must stay report-specific; they are not evidence for
a global rule.

This deliberately rejects Fable's proposed universal control/NBSP folding. That rule
would change Python answers and could hide source anomalies before their affected
families have been measured.

### D2.3 Fold actual Booleans only

At the typed-value boundary, normalize actual Boolean cell values to the canonical
text tokens `TRUE` and `FALSE` before ordinary case-sensitive comparison. Do not infer
Boolean meaning from numbers or Boolean-looking strings.

| Side A | Side B | Recommended result |
|---|---|---|
| Boolean `True` | text `TRUE` | equal |
| Boolean `False` | text `FALSE` | equal |
| Boolean `True` | text `true` | different |
| text `true` | text `TRUE` | different |
| Boolean `True` | numeric `1` | different |
| Boolean `False` | numeric `0` | different |
| text `Y` | Boolean `True` | different unless a report-specific loader owns that crosswalk |

The type test must be an actual Boolean check, not Python truthiness and not
`isinstance(value, int)`, because Boolean is an integer subclass in Python.

### D2.4 Keep Med-Wid normalization narrowly unsigned

Normalize a Med-Wid token only when the entire trimmed token is one of:

- unsigned ASCII `digits[.digits]`; or
- unsigned ASCII `digits[.digits]` followed by exactly one printable ASCII
  suffix character other than a digit or dot.

Normalize only the unsigned numeric portion, using decimal-safe text/decimal handling
rather than binary floating-point, and preserve the suffix exactly. There is no sign,
leading-dot shorthand, exponent, multiple-character suffix, or suffix case folding.
Tokens outside that grammar compare as ordinary raw text after ASCII-space trimming.
This printable-ASCII boundary is fail-closed: Unicode digits (including a Unicode
digit in the apparent suffix position), non-ASCII lookalikes/letters, tabs, and other
control characters remain raw anomalous text rather than having their numeric prefix
silently normalized.

| Side A | Side B | Recommended result |
|---|---|---|
| `0Z` | `00Z` | equal |
| `06V` | `6V` | equal |
| `06.00V` | `6V` | equal |
| `-06V` | `-6V` | different; both are raw anomalous text |
| `.50` | `0.5` | different; the leading-dot token is raw text |
| `6v` | `6V` | different; suffix case is significant |

This mirrors the narrow unsigned intent of the current Python rule while removing its
binary-float implementation risk. It intentionally does not copy the broader Excel
`VALUE` behavior.

### D2.5 What this gate does not change

The fixed architecture still requires literal error tokens, blank-versus-zero,
difference-marker-as-content, and precision safety to agree on every surface. This
decision record does not approve a broader numeric/text, date, control-code, or
report-specific crosswalk beyond the explicit rows above.

For avoidance of doubt, a missing cell, an empty text cell, and text containing only
ASCII spaces all normalize to the same blank value after the approved ASCII-space
trim. Blank remains different from numeric or text zero. Raw source type/value is still
retained in the typed compared-cell record for provenance.

### D2 approval record

The user/domain owner approved this four-part package before E1 implementation:

1. case-sensitive text;
2. actual-Boolean-only `TRUE`/`FALSE` folding;
3. the narrow unsigned Med-Wid grammar and case-sensitive suffix; and
4. no universal tab/CR/LF/NBSP folding.

If any row changes later, preserve a new dated decision and update both the synthetic
oracle and `CORE-ID-78-XLSX-TSN` typed oracle before changing production behavior.

## D3 — duplicate pairing choices

### D3.1 Exact rectangular assignment within the cap

**State: FIXED / APPROVED objective.**

For a duplicate group with side sizes `n` and `m` whose current product bound is within
`n * m <= 100,000`:

1. Build the rectangular cost matrix from D2's asserting unequal-cell count.
2. Match every member of the smaller side to a distinct member of the larger side.
3. Select an assignment with the exact minimum total cost.
4. Use a genuinely rectangular algorithm bounded by
   `min(n,m)^2 * max(n,m)` (or better). Never pad a `1 x 100,000` group to a
   `100,000 x 100,000` square.
5. Preserve unmatched larger-side rows as one-sided rows in their original file order.
6. Persist the selected original-index pairs, total cost, dimensions, algorithm/quality,
   and any capped diagnostics in the typed pairing trace.

The exact result must never be worse than positional file-order pairing. The retained
greedy-worse-than-positional fixtures are hard monotonicity regressions, not optional
performance checks.

### D3.2 Deterministic lexicographic tie-break

**State: APPROVED 2026-07-12.**

For assignments with the same exact minimum cost:

1. Let the smaller side define row order; when sizes are equal, side A is the smaller
   side for this rule.
2. Form the assignment vector whose element at each smaller-side file index is the
   matched larger-side file index.
3. Choose the lexicographically smallest assignment vector.

This precisely defines “first” without depending on hash order, dictionary order,
algorithm scan behavior, or an implementation's internal transpose. It also preserves
the current exhaustive branch's lexicographic behavior. After selection, occurrence
numbers remain assigned in side-A file order, and unmatched leftovers retain file
order.

The same equal-cost fixture must be run with the rectangle in both orientations so a
transpose cannot silently change the declared tie policy.

### D3.3 Fail closed above the cap

**State: APPROVED 2026-07-12.**

When `n * m > 100,000`, retain a deterministic positional/file-order fallback only as
useful diagnostic output, and mark the comparison outcome:

- `completion=partial` (incomplete/non-certifying);
- `pairing_quality=capped`;
- a structured capped-group diagnostic containing the key identity, `n`, `m`, cap,
  fallback policy, and observed fallback cost; and
- no certified `match`, green/fresh cell, fully-OK validation result, or claim of
  optimal pairing. Under the current binary persisted verdict contract, partial uses
  the conservative non-match path.

Observed counts may be shown, but must be labelled as counts under the fallback
pairing, not exact minimum-cost counts. The cell stays amber/retryable. Phase 5's
last-complete/unpromoted-partial artifact policy decides where those bytes live; this
gate decides only their truth status.

This is preferred over Fable's “coverage complete with a caveat” option because row
coverage can be complete while row identity remains unresolved. A clean-looking count
from an unproven pairing must not certify equivalence.

### D3 approval record

The user/domain owner approved before E2 implementation:

1. the lexicographically smallest assignment-vector tie rule; and
2. above-cap `partial`/`pairing_quality=capped` fail-closed semantics.

The exact rectangular minimum-cost objective inside the cap remains fixed.

**Amendment — owner approval, 2026-07-16 (CMP-AUD-220).** In response to the
decision memo (COMPLETION-PLAN RESUME block, 2026-07-16) the owner replied:
*"Whatever you did is approved as long as it results in all correct
comparisons."* Recorded as approval of the recommended **assignment/verdict
split**, superseding fixed-architecture item 5's "context cells cannot
influence assignment" clause: the duplicate-pair ASSIGNMENT cost may use the
source-proven objective (all compared source fields + character edit distance
+ source position, per the Stage-8 Highway Sequence oracle's `_cost`), while
the asserting VERDICT and every count remain computed only from asserting
compared-cell equality state. The condition binds: implementation must prove
all comparisons correct — the exact-DP/cap/typed-trace architecture stays, and
every family's canaries re-bless with exact evidence before the change ships.

**Implemented 2026-07-16 (same day).** `compare_core` assigns within-cap
duplicate groups by the approved objective (encoded order-preservingly into
the exact solver; the D3.1 lex tie rule and D3.2 cap semantics byte-unchanged);
verdicts/counts stay asserted-only; traces carry the additive
`SOURCE_PAIRING_ALGORITHM` objective vocabulary while v1 payloads validate and
serialize byte-identically. The binding condition was met with exact evidence:
the product reproduces the Stage-8 HSL oracle table digit-for-digit on all
three legs; RD/ID pair byte-identically under both objectives on every leg;
HL Route-1 stays 299/18/69/221/969. Full record: the CMP-AUD-220 execution
disposition in `comparison-audit-findings.md` and the 2026-07-16 progress-log
entry in `COMPLETION-PLAN.md`.

## Why Route-1 cannot decide D2 or D3

The bound `HL-R1-E1` canary remains essential regression evidence: exact hashed inputs,
one values/formulas generation, installed-Excel full recalculation, all Summary and
Spot Check self-checks, and the approved 969 differing-cell result agree.

It is **not** an oracle for the controversial policy rows. The recorded census covered
8,736 nonblank TSMIS cells and 10,131 nonblank TSN cells and found no actual Booleans,
control-whitespace/NBSP strings, Excel-error-token strings, literal difference markers,
numbers or digit strings beyond 15 significant digits, or signed/leading-decimal
tokens. Lowercase occurred only in ten header labels per side. Consequently:

- case-sensitive versus case-insensitive compared data produces no Route-1 signal;
- actual-Boolean folding produces no Route-1 signal;
- universal versus narrow control/NBSP handling produces no Route-1 signal; and
- strict signed/leading-decimal Med-Wid handling produces no Route-1 signal.

Route-1 therefore proves ordinary parity and guards the 969 baseline. It cannot approve
an edge rule merely because the total stays 969. Purpose-built adversarial fixtures are
required for every D2 row, and explicit duplicate/tie/cap fixtures are required for D3.

## `CORE-ID-78-XLSX-TSN` independent typed oracle

The current-schema statewide Phase 3 engine gate is the input-bound 218-member
`CORE-ID-78-XLSX-TSN` set (217 current Intersection Detail route exports plus the exact
TSN side selected for the recipe). Input binding alone is necessary but insufficient:
historical workbook totals, agent prose, and the product comparator cannot serve as the
expected-answer oracle.

The binding ledger records the versioned manifest schema, exact selectors and roles,
218 members / 26,384,760 source bytes, and stable SHA-256
`9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`.
That digest proves the selected input identity; the actual acceptance run must also
retain the full 218-record manifest and repeat it immediately before and after execution.

Before Phase 3 starts:

1. Bind every member's role, canonical path, length, and SHA-256 in a sorted manifest;
   record the manifest digest and the comparator/loader/normalizer source identity.
2. Recheck the same input digests after every oracle and comparator run.
3. Implement an independent reader/equality/key/pairing oracle that does **not** import
   or call `compare_core`, `compared_cell`, `_xl_trim`, `_medwid_norm`, `keys_for`,
   `_min_cost_pairs`, the production comparator adapter, persisted sidecars, or an
   existing comparison workbook. Sharing a result dataclass/schema is acceptable;
   sharing the logic under test is not.
4. Encode the approved D2 rules and D3 tie/cap rules independently. Until those rules
   are approved, the oracle is not final.
5. Emit a canonical typed count record with `known`, `paired_rows`,
   `side_a_only_rows`, `side_b_only_rows`, `differing_rows`, `differing_cells`,
   `per_field_counts`, `asserted_cells`, and `context_cells`, plus the independently
   derived pairing trace/quality and capped diagnostics.
6. Freeze only counts, identities, and safe diagnostics in the repository. The local
   corpus remains outside version control.
7. Reconcile the pre-change product result against the independent oracle. Any mismatch
   is an unresolved defect or policy discrepancy, not a baseline to copy into the
   oracle.

The corrected independent rerun satisfied this oracle gate. The raw manifest remained
byte-identical before and after: 218 members, 26,384,760 bytes, digest
`9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`.
It established 16,199 paired rows, 260/427 one-sided rows, 16,053 differing rows,
21,675 differing cells, 518,368 asserting cells, zero context cells, 106 exact
duplicate groups, zero capped groups, and 259 route-provenance diagnostics. An
independent first/corrected-pass reconciliation proved exactly 142 removed cells, all
`Intrte Postmile`; two rows became fully equal; four removals were inside duplicate
groups; total trace cost fell by 142; and no assignment/source-pair changed.

## Required adversarial proof

At minimum, the pre-fix/red and post-fix/green suite must include:

- D2: case-only text; actual Boolean versus `TRUE`/`FALSE`, lowercase text, `1`, and
  `0`; tabs/CR/LF/NBSP versus ASCII spaces; `0Z/00Z`, `06V/6V`, `-06V/-6V`,
  `.50/0.5`, and `6v/6V`; error tokens; blank/zero; literal `≠`; and precision beyond
  15 significant digits.
- D3: the retained 8-by-8 non-monotonic assignments; equal-cost tie fixtures in both
  rectangle orientations; unequal rectangles with leftovers on each side; a
  `1 x 100,000` within-cap proof that no square allocation occurs; and the
  `317 x 316` above-cap fixture proving partial/capped state and no green verdict.
- Every fixture: Python typed counts = values Summary = live Excel Summary = each
  Comparison-row `Diffs` = Spot Check = Report View consumer input, with all applicable
  self-checks `OK` after installed Excel `CalculateFullRebuild`.
- Real data: bound Route-1 remains 969 unless every changed cell is explained before
  re-blessing, and `CORE-ID-78-XLSX-TSN` agrees exactly with its independent typed
  oracle.

## Approval record

Approval does not bless an implementation or a historical count. The independent
oracle, red/green fixtures, full offline gate, installed-Excel parity, and bound real
canaries remain required.

| Date | Approver | Gate | Approved rule or replacement | Evidence/notes |
|---|---|---|---|---|
| 2026-07-12 | User/domain owner | D2.1–D2.4, D3.2–D3.3 | Approved the complete six-part recommended bundle without replacement | Methodology remains perfect comparison regardless of past behavior; proceed through the phases. |

## Phase 3 start condition

Phase 3 may begin only when all of the following are true:

1. Complete — D2.1–D2.4 are explicitly approved.
2. Complete — D3.2 and D3.3 are explicitly approved.
3. `CORE-ID-78-XLSX-TSN` retains the full exact hashed role/member manifest for the
   acceptance run and matches the already-recorded input-binding digest.
4. Its independent typed oracle is frozen and reconciled without importing production
   comparison logic.
5. The Route-1 binding and source-manifest rerun procedure remain available.
6. The adversarial and real-Excel commands for E1 and E2 are named before code changes.

Entry update on 2026-07-12: all six start conditions and every Phase-3 exit gate are
complete. The final offline tree passed 119/119; the 41,000-trace schema-v3 regression
round-tripped the measured 16,795,872-byte/five-chunk outcome; local-thread and real
subprocess publication serialization, crash-safe chunk retry, bounded one-decode
resources, and Windows path boundaries are green. The frozen `r3` production canary
reproduced the corrected oracle exactly and passed installed-Excel formulas/values
parity. Phase 4 may begin from the hashes in the binding ledger.
