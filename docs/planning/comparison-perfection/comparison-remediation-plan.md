# Comparison remediation implementation plan

Last updated: 2026-07-14  
Status: sequencing/dependency reference. The capability census is complete; Stage 6
source conservation is 7/7 and the Stage 8 base audit is 7/7. Product perfection and
end-to-end evidence remain red; Stages 9/10 companion, historical, and evidence work,
Stage 11 remediation, and Stage 12 release remain. This audit closeout authorizes no
product changes. The implementation stop line and takeover sequence are in
`comparison-implementation-handoff.md`. The frozen `scripts/` baseline is 321 files /
7,423,809 bytes with manifest SHA-256
`df7bb8fc3d997d60d82ecb93344f821e858feb015eed62fffe859958c9151bea`.  
Finding source of truth: `docs/planning/comparison-perfection/comparison-audit-findings.md`  
Independent reviews: `docs/planning/comparison-perfection/claude-comparison-audit-second-opinion.md` and
`docs/planning/comparison-perfection/fable5-comparison-remediation-decisions.md`

## Objective

Correct the comparison-audit findings without silently changing correct field
canaries, silently trusting legacy artifacts, or mixing broad
architectural changes with report-parser repairs. Every finding keeps its stable ID.
A finding moves to `Resolved` only after its original reproduction fails before the
fix, passes after the fix, relevant existing checks remain green, and the acceptance
gate assigned below passes.

This plan defines the order, contracts, migrations, batch boundaries, and proof used
during implementation. Phase 1 changes are tracked in the finding ledger and are not
considered resolved until the full Phase-1 gate recorded below passes.

## Current authorization freeze

Do not begin Stage 11 product remediation from this record alone. A new explicit
implementation authorization must start from
[comparison-implementation-handoff.md](archive/comparison-implementation-handoff.md), preserve
existing dirty product changes, and use finding-owned pre-red/post-green/full gates.

## Reconciled conclusions

Claude's second opinion was substantially correct, but it is advisory rather than an
oracle. The disputed claims were independently checked against code and executable
fixtures. The resulting plan adopts these conclusions:

- The capability census remains 29 classic recipes, 12 Matrix rows, 30 Matrix
  row/mode placements, seven canonical TSN datasets, and five unique PDF-to-Excel
  self-comparators exposed in six row placements.
- No ledger finding was disproved and no extra stable finding ID is needed. Claude's
  new technical observations extend CMP-AUD-003, 004, 006, 008, 016, 088, 090, 114,
  and 116.
- CMP-AUD-085 is a contract conflict plus several unconditional truth defects. The
  historical plan deliberately implemented partial “replace and flag”; current
  canonical docs promise last-complete preservation and complete-only caching. The
  publication policy must be selected explicitly before that batch is coded.
- CMP-AUD-016 excludes normal relative folder-dropdown selections, which receive a
  shallow membership preflight. All file recipes and absolute Browse selections
  remain in scope.
- CMP-AUD-099 remains P2 under this ledger's rubric. It does not inherently corrupt
  results, but it executes an incorrect target set and can spend substantial time
  rebuilding statewide artifacts.
- CMP-AUD-101 applies only to the generic folder shortcut. Per-cell Open is correct.
- CMP-AUD-114 is definitively frozen by the combined validation fixture and totals
  assertion, even though no single assertion names `counts_unreadable`.

Fable 5's decision record is retained at
`docs/planning/comparison-perfection/fable5-comparison-remediation-decisions.md`. It independently selected
the recommended D1–D7 defaults and confirmed that S1–S5 are decision-independent. This
plan treats that response as evidence, not authority. Independent code review accepted
D1, D5, and D7's capability facts, but corrected material parts of D2, D3, D4, and D6:

- D2's Boolean and universal whitespace rules change current Python behavior; they are
  not a behavior-preserving formula repair.
- D3's claimed 316-by-316 worst case is false because the current product cap permits a
  1-by-100,000 group. Square padding is prohibited; the implementation must be truly
  rectangular and prove deterministic tie behavior.
- D4 is settled for Highway Sequence, Ramp Detail, and Intersection Detail. Highway
  Detail remains blocked on an authoritative Excel-side county derivation; the Fable
  collision count used a weaker key than `pm_canon` and is only an upper bound.
- D6's governing same-source principle is sound, but its field profiles omit active
  transformations and miscount Highway Sequence's shared non-key fields. A complete
  per-family projection table is required before a self-comparator changes.

The authoritative ledger currently contains CMP-AUD-001 through CMP-AUD-237. The phase
coverage index below was organized before the later audit closeout and remains a
historical implementation map through CMP-AUD-185; CMP-AUD-186 through CMP-AUD-237 keep
their stable ownership and status in the finding ledger and implementation handoff.
Narrative integration lists are deliberately labelled as integrations below so they
cannot be mistaken for duplicate closure ownership.

## Non-negotiable invariants

These rules apply to every phase:

1. One producer-owned outcome model carries completion, artifact state, discrepancy
   counts, warnings/failures, source identity, and generation identity. Human summary
   text is never parsed as state.
2. No incomplete, unreadable, contradictory, legacy-untrusted, or wrong-generation
   artifact may render a checkmark, `match`, `fully OK`, or green/fresh completion.
3. Values, formulas, Summary, Comparison, Spot Check, Report View, Matrix caches,
   validation, and evidence consume one equality result. Display text is never
   rescanned to infer truth.
4. Source selection is fail-closed. A missing explicit source never silently falls
   back to a different canonical dataset.
5. Every committed member of one comparison generation—values, optional formulas,
   outcome metadata, counts, provenance, and evidence—has one generation identity.
6. Old bytes are preserved until a replacement generation is validated and committed.
   There is no mass-delete migration.
7. Unknown or legacy metadata is stale/untrusted, never implicitly complete.
8. User-owned directories and files are never claimed, overwritten, or recursively
   deleted based on a name or marker written after the directory already existed.
9. Stable recipe/report/action IDs and public output locations remain compatible unless
   an explicit migration below says otherwise.
10. Parser families remain separate. Shared contracts are extracted; report-specific
    parsing is repaired one family at a time rather than replaced with a generic parser.

## Semantic decision record and remaining gates

Fable's selections below are the working defaults after independent review. Items
labelled **user/domain gate** remain deliberately unimplemented until confirmed; code
evidence cannot manufacture business intent. Unaffected typed-contract and loader
groundwork may proceed around a gated family.

### D1 — partial canonical artifact and cache policy

Selected default: keep the last complete canonical generation; publish a useful partial
attempt under a distinct, unpromoted generation; record the current source state as
partial so the old complete artifact is never mistaken for current input; make the
partial attempt explicitly retryable. A comparison may inspect the partial generation
only while loudly carrying partial truth end to end.

The cache represents the last committed trustworthy generation plus a distinct latest-
attempt overlay. An existing canonical workbook already stamped partial must be moved
to an unpromoted partial identity (or left as the only explicitly partial artifact when
no complete bytes survive); it cannot be relabelled into a last-complete generation.
Export-store promotion remains complete-only.

**Phase-2 compatibility choice:** comparison workbooks built from partial inputs use the
normal stable cell path with explicit partial generation/completion flags. This preserves
public paths and makes the observed attempt amber/retryable, but it is not the final D1
publication model: Phase 5 must preserve the last complete generation and move partial
attempts to a distinct unpromoted identity/overlay.

### D2 — canonical equality

Selected architecture: a typed Python equality policy is canonical; values and result
counts are produced from it, and formulas are generated to mirror it exactly. Source
error tokens remain literal text. Numeric normalization is explicit and decimal-safe,
blank and zero remain distinct, and difference-marker text is content rather than state.
A writer can prevent *additional* Excel precision loss but cannot recover digits already
lost in a numeric source cell.

**Approved 2026-07-12:** the concrete package in
[`comparison-phase3-decision-gates.md`](comparison-phase3-decision-gates.md):
case-sensitive text; strict unsigned Med-Wid handling (signed and leading-decimal forms
compare as raw text and suffix case matters); actual-Boolean-only `TRUE/FALSE` folding;
and no universal tab/CR/LF/NBSP folding. Boolean folding changes Python behavior;
universal whitespace folding was rejected as an unmeasured anomaly-hiding expansion.

### D3 — duplicate pairing

Selected objective: deterministic exact minimum-cost assignment for every group within
the documented product bound, preserving the exhaustive small-group behavior and
persisting the pairing trace. Use a rectangular algorithm whose complexity is bounded
by `min(n,m)^2 * max(n,m)`; never pad a 1-by-100,000 group to a square. Pin an executable
monotonicity fixture and prove the exact tie-break rather than assuming stable scan order
defines it.

**Approved 2026-07-12:** the exact lexicographic tie rule and above-cap policy in
[`comparison-phase3-decision-gates.md`](comparison-phase3-decision-gates.md). The
fail-closed policy keeps deterministic positional output for diagnosis but
demotes completion to partial/incomplete with `pairing_quality=capped`; it may not claim
optimal pairing, a match, or a green/fresh result.

### D4 — Ramp and Intersection row identity

Selected for Highway Sequence, Ramp Detail, and Intersection Detail: county is a key
component wherever postmile is county-relative, with exact raw source claims preserved
alongside the canonical key. Highway Sequence's direct PDF-to-TSN/PDF-to-Excel adapters
already inherit the county key; its generic cross-environment paths still need it.
The accepted Ramp Detail oracle makes this concrete: 81 weak `(Route, PM)` TSN keys
span 163 county identities, so every Excel/PDF/raw/normalized leg must use
`(Route, County, norm_pm(PM))`. District remains a separately visible asserted field,
not a substitute key component; CMP-AUD-185 binds its exact `005/SD/72.366`
District 12-vs-11 disagreement.

The accepted Intersection Detail oracle resolves its formerly abbreviated tuple:
all Excel/PDF/raw/normalized legs must use
`(base Route, County, complete PP, numeric Post Mile)`. Raw TSN has 78 weak
Route+numeric-PM cross-county keys / 156 county identities, and six additional
within-county groups where complete PP distinguishes real rows at one numeric PM.
Route suffix, PR, District, explicit member Route, and physical `S` remain separately
asserted claims; they are not substitutes for the complete physical key.

**User/domain gate:** Highway Detail remains unresolved. Its Excel export has no county,
the current PDF loader discards DCR group rows, and an asymmetric county key cannot pair
the Excel side. Supply an authoritative Excel-side county derivation/table or retain the
documented `(Route, pm_canon)` limitation for Excel-involving flavors. County/key changes
land per family in Phase 4, after Phase 3 provides structured-key infrastructure.

### D5 — aggregate taxonomy

Selected: the Ramp footnote is display-only auxiliary metadata, while P/V are TSN-only
structural categories and remain one-sided by design. The result verdict vocabulary is
unchanged. `LoadedSide` needs an auxiliary-metrics channel so excluding the footnote
from comparison rows does not erase it from the familiar display.

### D6 — PDF-to-Excel asserted fields

Selected governing rule: same-source self-checks retain only documented render
equivalences; TSN cross-system crosswalks cannot hide differences between two TSMIS
renderings. Before implementation, create a reviewed five-family table covering every
asserted/context/key/raw-claim field and every active transformation, including HSL raw
PM/county-period handling; HD raw PM/NA/Med V/WDA/Description/HG roadbed; Intersection
Boolean/numeric/PM/route/suffix rules; and Ramp dash/blank and no-linework equivalences.
Highway Sequence has six shared non-key fields, not seven.
Its Stage-8 current-source decision is now explicit: vs-TSN retains Route + County +
complete printed prefix/base-PM/suffix identity, while PDF↔Excel uses Route + County +
prefix + base PM with exact duplicate assignment and asserts suffix as its own source
claim. The latter must expose all 549 suffix cells (272 two-row moves plus five
PDF-only suffixes), not convert them into one-sided rows or cross-pair route 152.
Description handling must decode Excel/OOXML control escapes with installed-Excel
semantics but may not reuse the cross-system route-prefix stripping rule.
Ramp Detail's table must include District and County in both TSMIS forms and both TSN
forms; the normalized District/County sidecar cannot remain evidence-only. District is
asserted on cross-system legs and must remain visible/equal on PDF-to-Excel.

**User/domain gate:** approve that complete table after its mutation fixtures establish
which transformations are render equivalences rather than cross-system laundering.

### D7 — classic accepted input shapes

Selected default: narrow picker filters and hints to shapes the current adapters truly
support; expose the already-implemented raw-PDF Summary inputs; and advertise per-route
plus consolidated dual-shape only for the three Highway Log file recipes. This is a
catalog, server-side recipe/role binding, preflight, picker, and UI change—not UI text
alone.

**User/domain gate:** confirm there is no required non-Highway-Log per-route comparison
workflow. Any named workflow becomes a scoped feature with its own loader contract.

## Dependency graph

```text
red reproductions + decisions
          |
          +----> immediate safety containment
          |
          v
typed contracts and outcome plumbing
          |
          +----> core equality/identity
          |
          +----> validated loaders by family
          |
          v
one coordinated artifact-identity epoch
          |
          v
shared Matrix orchestration
          |
          +----> secondary views/evidence
          |
          +----> validation/bundles
          v
classic UI/docs cleanup
          |
          v
full acceptance and release gate
```

Phase 1 can be implemented independently once authorized. Phases 3 and 4 wait for the
relevant D1–D7 decisions. The artifact epoch waits for typed contracts and must land as
one coordinated writer switch. Evidence and validation wait for generation identity.

## Phase 0 — freeze reproductions and record decisions

### Work

- Turn each finding's existing disposable reproduction into a focused failing check or
  a retained fixture manifest before editing its production path.
- Record D1–D7 with selected behavior, rationale, migration consequence, and affected
  real-data canaries.
- Snapshot the current 95-check blocking list, frozen self-test, Route-1 workbook, and
  available statewide canaries with source identities.
- Treat `C:\Users\Yunus\Downloads\TSMIS\_INDEX.md` as the local-only corpus map.
  Canonical acceptance inputs come from `ground-truth/` (especially `inputs/`,
  `All Reports 6.19/`, `All Reports 7.9/`, and the dated HD/ID/HSL/Ramp bundles);
  `report-samples/` is parser spot-check material, `comparison-outputs/` is historical
  reference only, and `_scratch/` is never an oracle. None of this corpus is copied into
  Git.
- Add a finding-to-check index. Existing green checks that freeze defective behavior
  are labelled `expectation-to-change`, not cited as proof of correctness.

### Exit gate

- Every implementation batch has a red test and an owner decision where required.
- No source dataset is re-blessed without a durable identity record.

## Phase 1 — immediate safety containment

Each item is an isolated implementation batch with negative tests. Do not combine these into a broad
refactor.

### S1 — output/source alias rejection (CMP-AUD-041)

- Resolve paths and stable file identity before opening Save or committing either
  workbook twin/evidence sibling.
- Reject direct, symlink/junction, hardlink, case-folded, and relative aliases.
- Enforce the guard in direct file/folder adapters as well as GUI/Matrix wrappers;
  capture the effective discovered input set and recheck it before publication.
- Require a single-use, server-bound confirmation for an existing derived values twin;
  a twin that appears without that path-specific decision fails closed.
- Use unpredictable evidence temp/quarantine/alternate names and never clean a path
  that may have become a captured source or unrelated foreign entry.

### S2 — ownership and Reset fail-closed (CMP-AUD-090)

- Replace stamp-on-sight with create-and-mark semantics.
- Make markers purpose-bound and versioned; validate kind, parent/root, and expected
  structure before recursive deletion.
- Remove the Day worker's wrong-root stamp.
- Bind Reset preview to exact entry/root identities and quarantine that exact entry
  before recursive deletion; replacement or marker drift restores/retains it.
- Lease export, Matrix, promotion, journal, staging, consolidation, outcome, fingerprint,
  and recovery writes to exact plain-directory identities. Reject `.staging`/`.promote`
  reparse points, reject any reparse ancestor between the leased root and a descendant
  output, and revalidate immediately around every mutation.
- Treat legacy markers as untrusted for deletion until safely migrated; surface them
  in Reset preview as retained, not deletable.
- Accept the deliberate interim consequence before marker-v2 lands: stores stamped by
  older releases may temporarily require re-export/re-adoption or manual deletion.
  Reset must explain that fail-closed retention rather than calling it a failure.

### S3 — evidence literal-cell guard (CMP-AUD-111)

- Reuse the central literal writer for evidence values, captions, and summaries.
- Guard formula leads and openpyxl error tokens. Prove data types on readback.

### S4 — credential-safe validation bundles (CMP-AUD-117)

- Prefer typed safe error codes in manifests.
- Redact complete Authorization/cookie/token values, including bare Bearer/Basic/JWT
  forms and multiline/query-string variants.
- Scan every ZIP member byte-for-byte before claiming the bundle is credential-safe,
  including UTF-16, member names/metadata/comments, raw Office container bytes, and
  decompressed nested OOXML members.
- On any final scan hit, regenerate a verified-redacted member or abort the bundle and
  name the member. Never publish a bundle containing the hit with only a warning.

### S5 — explicit source selection fail-closed (CMP-AUD-105)

- If an explicit TSN selection disappears or changes identity, block and name it.
- Never resolve a different canonical library behind the persisted explicit choice.
- Persist a versioned content hash, size/time, and file identity; legacy path-only
  choices require re-pick rather than acquiring trust during migration.
- Surface a durable “selection missing—re-pick or clear” state in Everything, day,
  and validation rather than failing only inside the resolver. The baseline matrix
  has no TSN side, so this state is not applicable there.

### Exit gate

- Adversarial alias, foreign-folder, formula/error-token, planted-secret, and missing-
  explicit-source checks pass.
- Full focused security/ownership/artifact tests pass before any semantic core change.

### Phase-1 execution record — complete 2026-07-11

- **S1:** stable source identities and alias checks now cover GUI/direct/Matrix/evidence
  outputs; both-mode uses exact-path, single-use consent; workbook/evidence temps and
  fallbacks are unpredictable and identity-bound.
- **S2:** create-only purpose markers, `OwnershipLease`, exclusive staging, guarded
  consolidators/PDF scratch/sidecars/caches/evidence, bound promotion journals/recovery,
  dual Everything-Matrix leases, and preview-bound Reset quarantine are live. Phase 1
  intentionally retains schema-1 markers with a versioned `creation_claim`; marker-v2
  remains the Phase-5 epoch.
- **S3:** `set_safe_literal_cell` covers evidence and comparison source cells, including
  all formula leads and Excel error tokens.
- **S4:** `credential_safety` provides shared redaction and final nested/member-level ZIP
  scanning; rejected evidence builds preserve the prior good ZIP.
- **S5:** versioned explicit TSN selections bind canonical path/hash/size/mtime/file ID,
  all five PDF aliases share their base dataset, and missing/replaced/legacy picks block.
- **Proof:** focused comparison 26/26; focused cross-surface 9/9; silent-swallow audit
  0 new; `build/run_checks.py -j 4 -k` **98 passed, 0 failed** (41 seconds).

## Phase 2 — typed contracts and truthful outcomes

The dependency-light leaf types and compatibility adapters are implemented without an
equality or workbook-answer change. Producers and truth consumers have been switched in
small batches; the execution record below distinguishes that completed slice from later
artifact-identity policy.

### Types

- `SourceIdentity`: stable recipe/report/role/format, canonical path, content digest,
  producer/parser/normalizer versions, and effective selection kind.
- `LoadedSide`: rows, declared schema, route/record universe, completion, warnings,
  skipped/failed inputs, `SourceIdentity`, raw identity claims, and display-only/
  auxiliary metrics.
- `ComparisonCounts`: paired, side-only, differing rows/cells, per-field counts, and
  asserted/context totals.
- `ComparisonOutcome`: status, completion, verdict, counts, warnings/failures, source
  identities, pairing trace/quality, and capped-group diagnostics.
- `ArtifactGeneration`: generation ID, members, content digests, completion, producer
  versions, and publication state.
- `AttemptState`: attempted/succeeded/partial/failed/cancelled, separate from the last
  committed generation.

Extend `ConsolidateResult` additively during migration. Temporary adapters wrap legacy
tuple-returning loaders; new code must not create a second permanent result type.

### Producer switch

- Make `run_compare` own completion and structured counts (CMP-AUD-017, 077).
- Preserve partial outcomes through direct, environment, PDF, and Matrix paths
  (CMP-AUD-026).
- Return every centrally committed output member and publish the strict comparison-v1
  typed payload beside each member, protected by conservative sentinels, exact peer
  membership, and SHA-bound validation (CMP-AUD-075). This is an explicit compatibility
  bridge, not a second permanent schema: Phase 5 dual-reads these sidecars and replaces
  them with the generation manifest when all writers switch.
- Serialize returned and raised failures through the shared outcome reducer; never
  default absent completion to complete. The validation/classic acceptance slice for
  CMP-AUD-114/116 landed early; all-12 validation orchestration remains Phase 8.

### Exit gate

- Match/diff/one-sided/partial/no-data/cancelled/failed outcomes round-trip as typed
  returned objects. Only complete/partial comparisons that commit an artifact generation
  round-trip through strict member sidecars.
- Existing workbook bytes remain unchanged in this phase.
- No consumer parses `summary_lines` for state.

### Implementation record — 2026-07-11

- `comparison_contract.py` now owns validated `SourceIdentity`, `LoadedSide`,
  `ComparisonCounts`, `ComparisonOutcome`, `ArtifactGeneration`, and `AttemptState`.
- `run_compare` owns exact counts/completion before commit. Direct-file and all five PDF
  environment families preserve both sides' coupled completion, skipped/failed counts,
  warnings/failures, and diagnostics; returned and persisted outcomes agree.
- The real `artifact_store.commit_workbook` path publishes strict single- and multi-member
  generations. Direct/classic `mode="both"` gives values and formulas one generation;
  missing, tampered, mismatched, or interrupted metadata fails closed.
- `consolidation_meta.require_published_comparison` is the shared reducer for Matrix,
  day, baseline, classic UI, validation, and evidence preflight. It requires a successful
  returned result, typed outcome, committed generation, succeeded matching attempt, and
  identical trusted/current persisted truth. `summary_lines` is display-only and
  `read_counts` is diagnostic/migration-only.
- Matrix caches bind output identity, workbook mtime, generation ID, and input
  fingerprint. Missing, malformed, foreign, untrusted, or partial records are
  stale/retryable; partial cells render amber without a checkmark or `match` claim.
- Validation now records explicit OK/partial/untrusted/failed/cancelled/blocked buckets,
  cannot default terminal failures to complete, forwards collector failures, and reports
  the actual ZIP member count.
- The shared public comparison boundary now types every no-artifact terminal return.
  Missing input/folder, malformed shape, producer no-data/failure, overwrite cancellation,
  and artifact commit failure return `ComparisonOutcome` plus `AttemptState` with explicit
  failed/cancelled completion and no invented `ArtifactGeneration`.
- Focused typed/publication/consumer checks and the full offline runner passed 106/106.

### Phase-2 closure boundary and explicit transfers

The Phase-2 exit gate is satisfied: every public returned path is typed, committed
complete/partial generations strict-round-trip through sidecars, workbook semantics were
not changed, and no production consumer parses `summary_lines`/`read_counts` as truth.
The following findings remain deliberately open under their assigned later phases; they
are not hidden prerequisites retroactively attached to the typed-return slice:

- Matrix `also_formulas` still invokes a second comparison, so values/formulas receive
  different generation IDs. The central CMP-AUD-075 publisher slice is fixed, but the
  finding stays open until this secondary formula-twin closure under CMP-AUD-082/Phase 5.
- `SourceIdentity`, producer versions, and pairing trace are validated schema slots but
  are not universally populated. Durable attempt overlays, the postcommit/precache source
  fingerprint race (CMP-AUD-098), and the exact evidence transaction remain later phases.
- Partial comparison generations still use the stable canonical path; D1's retained
  last-complete plus distinct unpromoted partial attempt is Phase-5 work.
- The current-schema statewide files/member manifest and independent oracle must be
  bound before Phase 3. Route-1 is already baseline-bound through real Excel.

## Phase 3 — one comparison equality and identity engine

This is the deliberately regression-sensitive `compare_core` phase. Split it into two
batches and run real Excel after each.

### E1 — equality state (CMP-AUD-001–004, 012)

- Implement D2 once as a pure compared-cell result carrying typed source values,
  normalized values, assertiveness, equality, and display text.
- Make Python counts, values cells, generated formulas, Summary, Spot Check, and
  conditional formatting consume that result.
- Preserve literal difference-marker text as content; never use it as state.
- Force Excel error-code strings to literal text and define error equality explicitly.
- Preserve genuine blanks without the values Spot Check turning them into zero.
- Apply the approved generic whitespace contract here: only ASCII U+0020 receives
  Excel-TRIM semantics. Tabs, CR/LF, NBSP, and other Unicode whitespace remain data;
  any report-specific whitespace crosswalk must be owned and proved in its Phase-4
  loader batch rather than silently generalized in E1.
- Production Matrix/day/baseline/validation count scraping was removed in Phase 2.
  Delete the remaining diagnostic/legacy `read_counts` compatibility path only after the
  Phase-3 semantic re-proof establishes that no migration fixture still needs it.
- Add the Summary-side independent Report View self-check row during this single
  locked-engine re-bless epoch. Phase 7 will re-point its data source without adding a
  second Summary label/formula epoch.

#### E1 execution record — complete 2026-07-12

- `ComparedCell` plus hidden versioned `E/D/N/U` chunks now own all generic workbook
  truth. Formula masks are live; values masks are literal; no marker scan remains.
- Med-Wid uses the approved staged exact CANON twin; Spot Check independently stages
  both sides and preserves typed blank before `INDEX`.
- Copied finite numerics are exact comparison text; float/Decimal NaN and infinity
  fail before output interaction; engine-owned counts remain numeric.
- All Excel error/formula-leading literals are guarded on core and Detail Report View
  surfaces. The Report View aggregate self-check is present and the formulas Summary
  explicitly labels that view as a build-time snapshot.
- Focused oracle/reader/formula checks and all comparison-family checks are green.
  Installed Excel full rebuild proves formula masks, Diffs, displays, Summary, and
  Spot Check equal the literal values twin on the current snapshot-enabled engine.
  The corrected independent ID78 rerun retained the exact 218-member manifest and
  independently reconciled every deliberate numeric-lexical delta.

### E2 — identity and pairing infrastructure (CMP-AUD-005, 008, 009; enables 045)

- Use injective structured identities rather than delimiter-flattened helper strings.
- Apply the domain-approved key normalization separately from display normalization.
- Implement D3's structured assignment infrastructure and persist a deterministic
  pairing trace/quality result.
- Provide injective structured-key support here; switch each report's physical identity
  under D4 only inside its Phase-4 loader-family batch and canary re-proof.

#### E2 execution record — complete 2026-07-12

- Exact rectangular Hungarian assignment implements the approved scalar-cost then
  lexicographic smaller-side objective through the 100,000-cell cap. All retained
  greedy traps, both orientations, malformed matrices, and the `1 × 100,000` boundary
  equal the independent oracle.
- Above-cap positional results are partial/capped diagnostics only. Typed contracts,
  workbook/UI headlines, and Matrix state cannot certify a match or definitive
  differences; lossy capped unpacking is rejected.
- Opaque `CMP_E2_KEY_V1` ordinals make workbook identity injective. Installed Excel
  passes the delimiter-bearing collision fixture and every Summary self-check.
- Very-hidden `CMP_E2_SNAPSHOT_V1` sheets and row/tail guards force
  `REGENERATE REQUIRED` after value/key/helper/duplicate-order/row-universe edits.
- Cancellation is bounded through source validation, pairing, and typed counting and
  returns unknown/empty truth without output mutation.
- Schema v3 writes bounded shared canonical payload chunks beside small peer envelopes;
  schema v2 remains strict read-compatible. The real 41,000 exact-2×2 trace shape
  round-trips at 16,795,872 decoded bytes/five chunks under a 64 MiB, 16-chunk, 32:1
  one-decode policy.
- Chunk installation is process-crash safe and no-replace. Poisoned primary names use
  eight deterministic exact-byte slots; local threads and separate processes serialize
  through one permanent parent lease. Success requires the exact caller outcome,
  generation, and member to be persisted.
- UTF-16 component limits fail before producer entry; the packaged manifest is
  `longPathAware`. All 31 comparison checks and the complete 119-check offline tree are
  green.
- The frozen `CORE-ID-78-XLSX-TSN` `r3` run reproduced 16,199 paired, 260/427
  one-sided, 16,053 differing rows, 21,675 differing cells, 518,368 asserted cells,
  and 106 exact/zero-capped duplicate groups. Installed Excel matched values/formulas
  across every owning surface. Evidence/result SHA-256 is recorded in the canary ledger.

### Exit gate

- For every adversarial case, Python counts = values Summary = live Excel Summary =
  Comparison row Diffs = Spot Check = Report View consumer input.
- The retained 8-by-8 assignment fixtures (14/10/8, 4/6/4, and 31/32) and the
  317-by-316 capped fixture cannot regress or silently change status.
- Real Excel `CalculateFullRebuild` passes, Route-1 remains 969 unless D2 deliberately
  changes it, and any deliberate change is explained cell-by-cell before re-blessing.

#### Phase-3 exit record — accepted 2026-07-12

- Complete offline runner: 119/119.
- Clean code-bound production result SHA-256:
  `a54448f621beb27cea4e4b7a82af1b0a65580e84c5eac6df313242959a1111b2`.
- Raw input manifest stayed identical pre/before/post at
  `9d1c0ae4f9bc8de098497695cd87d3c543dba01e34cb9f4b03cb883791b52bd6`.
- All 15 evidence artifacts and 11 production source hashes were independently
  rehashed after the runner, and both committed peers strict-read trusted/current.

## Phase 4 — validated loaders, one report family per batch

Every loader returns `LoadedSide`, validates its declared shape/universe, reconciles
producer partial state, and fails closed on ambiguity. Do not mix parser families in
one commit.

### P4-0 — freeze and red-fixture index

- Start only after the clean Phase-3 production canary passes on unchanged code; record
  its source, code, workbook, sidecar, and payload hashes.
- Freeze the executable universe at 29 classic recipes, 12 Matrix rows, and 30 Matrix
  row-mode placements. The comparison checks are not a one-to-one proxy for that
  recipe census.
- Assign every Phase-4-owned finding an independent red reproduction, owning loader
  batch, and real-data gate before implementation. Stop if any changed real count lacks
  exact member identity, producer versions, and a cell-level explanation.

### L0a — shared physical-identity contract

Primary implementation owner: CMP-AUD-045.

- Define structured physical identities and raw source claims, then apply the approved
  county/route/postmile tuple per family inside L2–L7. Highway Detail remains gated until
  an Excel-side county derivation is approved or its limitation is explicitly retained.
- Lock county resets, `1`/`001`, `1S`/`001S`, decimal postmile forms, prefix/suffix
  changes, swapped values, genuine duplicates, and mid-list insertions. Distinct
  physical locations must never merge, and no raw identity claim may disappear.

### L0b — shared PDF conversion, provenance, and projection contract

Primary implementation owners: CMP-AUD-049, 050, 067. Integrates the in-memory
source-role rules for CMP-AUD-066; durable role metadata closes that finding in Phase 5.

- Define shared route-universe, duplicate-route, in-document provenance, source-role,
  and same-source projection rules at the PDF conversion boundary.
- Apply and accept these rules per family inside L3–L7; a shared helper does not replace
  family-specific parsing or canaries.
- Exercise filename/document/emitted-route disagreement, blank and duplicate routes in
  both file orders, renamed foreign PDFs, wrong-role copies, and one mutation through
  every projector/crosswalk. Wrong provenance or hidden same-source differences may
  never certify a match.

### L1 — generic cross-environment and discovery

Primary implementation owners: CMP-AUD-018, 019, 027–032, 040, 044, 046.
Classic recipe/role selection for CMP-AUD-016 is owned by Phase 9.

- Validate file membership, duplicate route ownership, headers, key columns, selected
  roles, same-source aliases, and route provenance before comparison.
- Filter Excel owner-lock files and distinguish header-only valid emptiness from an
  invalid/disappearing route.
- Run A/B/both header-only inputs, padded/suffixed aliases, invalid names, run-root/
  subfolder aliases, overlapping effective sets, file-order permutations, missing
  keys, current/legacy/junk headers, and populated data beyond a blank header tail.
  Identical malformed inputs must not become a clean match.

### L2 — flat normalized TSN detail

Primary implementation owners: CMP-AUD-006, 033–038, 042, 133–143, 147, and 185;
integrates each family's approved slice of CMP-AUD-045.

- Implement the D2/D4 postmile/date/route contracts.
- Validate normalized headers and normalization version; rebuild stale libraries from
  raw source rather than compare-time patching.
- Define `ensure_current` once for current, stale-rebuild, first-build, and no-raw
  states. Phase 8 validation consumes this contract instead of inventing another
  first-build path.
- Execute separate Highway Sequence, Ramp Detail, Intersection Detail, and Highway
  Detail subpasses. Require raw/current-library parity; identity-only schemas,
  reordered headers, malformed dates, or stale partial reprojection fail closed.
- For Ramp Detail, retain County in D4 identity and project District as an asserted
  field on Excel/PDF versus raw/normalized TSN. The exact `005/SD/72.366` positive
  canary must differ 12-vs-11; PDF↔Excel must visibly agree 12-vs-12. Corrected product
  counts must equal the Stage-8 source oracle, not the pre-fix 861/1,012 outputs.
- For Intersection Detail, promote the accepted `ID-79` tuple and preserve the explicit
  Route/`S` source claims. Corrected current counts must remain 16,199 paired with
  260/427 one-sided; Excel/PDF must report 21,676/21,683 differing cells and the
  PDF↔Excel self-check must retain its exact nine-cell source ledger. The corrected raw
  and normalized Report Views must both map all 16,626 source-only traffic/reference
  claims, and PDF-vs-TSN must have the same Report View capability.

### L3a — Ramp Summary

Primary/family owners: shared CMP-AUD-020–022 plus Ramp-only CMP-AUD-024, 025,
071. CMP-AUD-023 is not a Ramp finding. The Ramp-specific CMP-AUD-050 route-universe
slice is accepted here without changing its L0b primary ownership.

- Reconcile section/route totals, numeric types, duplicate categories, footnotes, P/V
  policy, and empty/duplicate route universes under D5. Exercise total-only and one-
  field records, missing/renamed/unknown/duplicate categories, numeric strings,
  integral/fractional floats, booleans, absent-versus-zero, and block reconciliation.
- Bind a real Ramp Summary canary before closure. Existing P/V-as-`Both` and absent-as-
  zero expectations are expectations-to-change, not correctness proof.

### L3b — Intersection Summary

Primary/family owners: shared CMP-AUD-020–022 plus Intersection-only CMP-AUD-023,
CMP-AUD-183, and CMP-AUD-184.
CMP-AUD-024, 025, and 071 are not Intersection findings.

- Exercise missing Total, all-zero categories with nonzero Total, repeated exact keys,
  permitted distinct J–P/S folding, repeated J, count-less parent/child sequences,
  orphan children, every partition reconciliation, and the route universe.
- The accepted Stage-8 Intersection Summary oracle now supplies the `IS-79`
  identity-bound real baseline. Keep its product-red findings open until this batch's
  mutations turn green; acceptance of source truth is not implementation closure.

### L4 — Highway Log PDF and provenance

Primary implementation owners: CMP-AUD-047, 048; integrates the L0b slices of 049,
050, 066, and 067.

- Enforce route/document/source roles and shared normalization without weakening the
  current Highway Log canaries.
- Prove projection parity across all five Highway Log recipes, including tab/newline
  data, canonical/vendor and junk same-width headers, raw Location mutation,
  ditto/Med-Wid controls, and duplicate-route conversion. Bind `HL-PDF-TSN` and
  `HL-PDF-XLSX` in addition to the Route-1 gate.

### L5 — Highway Detail PDF

Primary implementation owners: CMP-AUD-051–054. CMP-AUD-055 is a Highway
Sequence/Ramp repeated-header finding and is owned by L7.

- Repair PM spill, repeated-header/data overlap, orphan reconciliation, fallback-grid
  certification, and damaged-page completeness.
- Cover first/middle/final-page anchor damage, leading/trailing/truncated pairs,
  shifted grids, token crossings, route mismatch/duplicates, and every same-source
  projection mutation. Any unaccounted data-area payload makes completion non-complete.

### L6 — Intersection PDF

Primary implementation owners: CMP-AUD-056–062, 070.

- Preserve wrapped rowB data, count orphans, isolate page geometry, validate mixed
  editions/vestigial fields, honor cancellation, and retain explicit route/suffix data.
- Cover every mergeable rowB cell, simultaneous/page-boundary wraps, header/PM-like
  continuation text, numeric furniture, both mixed-edition orders, populated vestigial
  columns, every scan cancellation stage, geometry/rotation/paper changes, and
  Route/Location/suffix claim conflicts. The current 434-member `ID-79` source triangle
  is accepted and proves exact nonblank consolidation projection across all 1,844 PDF
  pages; keep the older 7.8 pair as a separate Stage-9 historical-edition gate. Parser
  mutation findings remain open until this implementation batch turns them green.

### L7 — Highway Sequence and Ramp PDFs

Primary implementation owners: CMP-AUD-055, 063–065, 069; integrates the L0b slices of
049, 050, 066, and 067 plus the Ramp PDF projection slice of CMP-AUD-185.

- Validate PM/equate tokens, separate anomaly types from skipped-input counts, apply
  D6 asserted fields, prevent projection loss, and correct diagnostic roles.
- Run Highway Sequence and Ramp Detail as separate subpasses. Each covers damaged
  anchors on first/middle/final pages, every valid/invalid PM token, route provenance,
  anomaly-count invariants, and all shared-field mutations. Add dedicated parser-
  integrity gates for both families; current checks do not provide them.

### Exit gate per loader batch

- Malformed layout, partial producer, duplicate route, wrong source role, and route-
  universe controls fail or flag exactly as specified.
- Only that family's focused checks and real canary are re-run before the next family.
- No parser fix is accepted solely because a prior consolidated workbook agrees.

## Phase 5 — one coordinated artifact-identity epoch

Do not ship an intermediate mixture of old/new writers. Stage dual readers first,
switch all writers once, and bump all related schemas together.

### Persisted schemas

- `cache_envelope` v2 to v3: exact output identity, generation, producer versions, and
  per-record type/domain validation.
- fingerprint sidecar v1 to v2: content-digest manifest plus source metadata and
  producer/parser/normalizer versions. Hash at build/commit time, not every UI snapshot.
- consolidation metadata v1 to v2: generation, artifact digest, input identities,
  completion, and publication state.
- comparison manifest v1: typed sources, generation, modes, counts, completion,
  values/formulas/evidence membership, per-member digests, and durable producer/source-
  role provenance (the persistence half of CMP-AUD-066).
- TSN source metadata used by CMP-AUD-010: selected origin, effective source kind,
  canonical/explicit path, content identity, and normalization generation. Phase 6
  consumes these fields rather than inventing ad hoc provenance.
- ownership marker v2: purpose, root identity, creation nonce, and schema; legacy
  marker alone never authorizes deletion.

### Findings closed primarily here

CMP-AUD-066, 076, 080–085, 087, 089, 098, 100, and 115, with integration of 017,
026, 075, 077, and the Phase-1 source-selection contract for 105.

- Content identity replaces metadata-only trust (080/081).
- Formula twins share generation membership and stale old twins retire/quarantine
  (082).
- Presence/freshness requires valid report artifacts, not arbitrary files (083).
- Semantic producer version changes invalidate unchanged raw inputs (084).
- D1 governs complete versus partial canonical publication (085).
- Missing/unreadable count records become retryable, not fresh (087).
- Failed/cancelled attempts survive separately from last-good (089).
- Capture all input identities before work and recheck after production but before
  publication (098).
- Require exact cache identity and isolate malformed nested records (100).
- Artifact validation enforces required sheets/headers, allowed statuses, typed counts,
  source/generation identity, and cross-sheet/count/verdict invariants (115).

### Migration behavior

- Legacy/missing metadata reads stale and is regenerated on demand.
- Existing complete bytes stay available until a validated new generation commits.
- No startup sweep deletes legacy caches/workbooks merely because their schema is old.
- A locked migration retains both generations with an explicit not-promoted attempt.
- Interrupted migrations are idempotently recoverable.

### Exit gate

- Same-size/same-mtime replacements, mid-build mutations, semantic-version bumps,
  malformed caches, locked twins, and interrupted commits all fail closed.
- One generation cannot mix members or counts from another.

## Phase 6 — shared Matrix orchestration

Create catalog-derived mode descriptors and one shared buildability, target-selection,
result-recording, and open-artifact policy. Migrate backend first, then Everything,
day, and baseline one surface per integration commit.

### M1 — capability and build boundaries

Primary implementation owners: CMP-AUD-010, 013, 103. Integrates Phase-5 artifact
state for 083–085/087 and the Phase-1 explicit-selection contract for 105.

- Resolve TSN/PDF/self capabilities from catalog metadata.
- Use one buildability predicate for rendering, explicit endpoints, bulk selection,
  queue accounting, validation, and dispatch.

### M2 — queue, attempt, and ownership lifecycle

Primary implementation owners: CMP-AUD-088, 104. Integrates Phase-5 attempt state for
089 and Phase-1 ownership leases for 090.

- Classify job prerequisites; auth failures remove/suspend only auth-dependent work.
- Keep attempted/succeeded/partial/failed/cancelled counts separate.
- Make equivalent queue-capable actions share availability rules.

### M3 — date/source/target truth

Primary implementation owners: CMP-AUD-091–097, 099, 102. Integrates Phase-5
before/after source identity for 098.

- Bind one canonical run date/output identity through enqueue, export, and chained
  comparison.
- Preserve real discovered folder identity; reject impossible dates and invalid scoped
  filters instead of broadening them.
- Retain running targets during UI removal, clear invalid source-scoped state, report
  both missing sides, and fingerprint before/after comparison.
- Baseline changes rebuild only environment-mode cells whose effective input changed.
- Bulk “all” explicitly means authoritative catalog or is renamed to visible rows.

### M4 — cache/folder/open integration

Primary implementation owner: CMP-AUD-101. Integrates Phase-5 generation/cache
identity for 080–087, 098, and 100.

- Adopt Phase-5 generation identities in all three matrices.
- Open the common root or a mode-aware folder from the generic shortcut; retain exact
  per-cell Open behavior.

### Exit gate

- All 12 rows and 30 placements pass match/diff/partial/missing/both-missing/stale/
  failed/cancelled states.
- Everything, day, and baseline pass hidden rows, invalid scopes, source switches,
  midnight, mixed queues, same-metadata replacement, and restart recovery.

## Phase 7 — secondary views and evidence

### V1 — familiar secondary-view parity

Primary implementation owners: CMP-AUD-039, 043, 068, 107.

- Generate Report View and evidence enumeration from the Phase-3 cell state.
- Make formula-mode Report View live or explicitly values-only and generation-labelled.
- Apply the same rule to the Ramp/Intersection `Summary by Category` extra sheets:
  consume typed state for equality/count styling, and either recalculate from the live
  source sheets or carry an unmistakable values-only generation/snapshot label.
- Re-point the independent Summary self-check row added in Phase 3 to the final Report
  View generation/state without changing its label/formula surface again.

### V2 — pairing-aware evidence

Primary implementation owner: CMP-AUD-108.

- Consume the persisted duplicate-pairing trace; do not independently key/filter rows.

### V3 — exact-generation evidence transaction

Primary implementation owners: CMP-AUD-106, 109, 110, 112. Integrates secondary
closure gates for 049 (evidence provenance), 061 (evidence-locator cancellation), and
the Phase-5 identity/race foundations for 080/098.

- Bind queued settings/source/generation at enqueue.
- Verify content identity before parse, after parse, before raster, after raster, and
  before publication.
- Reconcile in-document route identity.
- Publish workbook/images/manifest as one artifact set; a clean comparison publishes
  an explicit current-empty evidence state that retires old red evidence.
- Total publication failure never returns success-shaped canonical paths.

### Exit gate

- Evidence can illustrate only discrepancies that the exact comparison generation
  counts, against the exact parsed/rasterized bytes.
- Partial, clean, failed, locked, retargeted, duplicate, and mid-run replacement cases
  all publish truthful state.

## Phase 8 — validation and evidence bundles

Split this into three ordinary batches after Matrix generation identity is stable.

### A1 — coverage and readiness

Primary implementation owners: CMP-AUD-007, 118, 120.

- Enumerate all expected capabilities through real mode mapping.
- Honor selected TSN sources, consume L2's `ensure_current` first-build/stale contract,
  and check cancellation before any mutating readiness step.

### A2 — truthful outcomes

Primary implementation owners: CMP-AUD-011, 114, 116, 119; integrates Phase-2 outcome
plumbing and the Phase-5 artifact validation for 115.

- Preserve partial counts through worker/API/UI.
- Require valid workbook, typed verdict/counts, complete completion, and agreeing
  generation identities before `comparisons_ok`.
- Record returned and raised failures explicitly failed.
- Correct the healing truth table.

### A3 — bundle accounting and final security integration

Primary implementation owner: CMP-AUD-113; final integration of the Phase-1
credential gate for 117.

- Derive manifests and returned counts from actual successfully written members.
- Run the credential scanner over every final member and fail closed on any hit.

### Exit gate

- All 12 expected rows appear in denominators with separate OK/partial/blocked/failed/
  cancelled/unreadable totals.
- JSON, text digest, ZIP, worker payload, logs, and modal agree exactly.

## Phase 9 — classic UI, taxonomy, and documentation

Primary implementation owners: CMP-AUD-014–016, 072–074, 078, 079, and 086. Integrates
the corrected diagnostic role from 069; Matrix UI parts of 093–104 are completed in
Phase 6 rather than reimplemented here.

- Bind input selection to stable recipe and role; clear or restore only matching state.
- Apply D7 picker filters, extensions, shapes, role labels, and hints.
- Prevent stale async folder discovery from overwriting a newer recipe selection.
- Keep a task-aware Cancel visible across Compare sub-tabs.
- Title comparison failures as comparisons.
- Generate descriptive capability documentation from the catalog while retaining an
  independent executable census check.
- Reconcile `CLAUDE.md`, comparison/reliability docs, and D1–D7 decisions in the same
  change; historical plans remain history and are not silently rewritten.

### Exit gate

- All 29 recipes pass UI-to-API routing, input-state, positive/negative role, picker,
  output-mode, Cancel, and failure-title checks.
- Docs state the exact 29/12/30/7 census and one unambiguous partial policy.

## Phase 10 — acceptance and release gate

### Tier 1 — focused checks per commit

- New red/green finding check.
- Direct owning-module checks.
- Static syntax/lint/type-domain checks.

### Tier 2 — full offline gate per batch

- All blocking Python and Node checks (historical audit close: 95; Phase-1 close:
  98/98; current Phase-2 gate: 106/106, including compileall and five Node checks).
- Check-manifest completeness so no new `check_*` file is omitted.
- Source ZIP smoke.

### Tier 3 — real Excel for semantic/workbook batches

- `CalculateFullRebuild` on formulas workbooks.
- Values/formulas/Python/Spot Check/Report View/Summary/count-cache agreement.
- All Summary and applicable Spot Check self-checks.
- Error tokens, marker text, case/coercion/precision, blanks, helper-key collisions,
  duplicate pairing, formulas twins, and locked-file cases.

### Tier 4 — real source-data canaries

- Route-1 Highway Log: current baseline 969 differing cells unless D2 deliberately
  changes and explains specific cells.
- Resolve each canary through the local corpus index at
  `C:\Users\Yunus\Downloads\TSMIS\_INDEX.md` and record the exact file/directory
  identity before execution; never infer a current baseline from `_scratch/` or a
  historical workbook in `comparison-outputs/`.
- Record selected paths, roles, lengths, SHA-256/member-manifest digests, producer
  versions, expected counts, and readiness in
  `docs/planning/comparison-perfection/comparison-canary-bindings.md`. Route-1 is baseline-bound through real
  Excel; every provisional/blocked entry must be promoted explicitly before its owning
  semantic batch.
- Ramp Summary, Ramp Detail, Highway Sequence, Highway Log PDF-to-TSN, and every
  affected family canary recorded in the ledger.
- Keep `ground-truth/All Reports 6.19/` as historical/raw family evidence, but do not use
  its pre-July Intersection Detail layout as the current Phase-3 engine gate: production
  correctly refuses that obsolete schema. Use the 218-member `CORE-ID-78-XLSX-TSN`
  current-schema set defined in the binding ledger for the next statewide re-proof.
  Use `ground-truth/All Reports 7.9/` for the freshest complete both-format field set, and
  the dedicated Highway Detail 7.7, Intersection Detail 7.8, HSL 7.8/7.9, and Ramp
  Detail TSN-print bundles for their owning parser/triangle/evidence gates.
- Reconcile every same-pull TSMIS Excel/PDF pair available for all seven comparison
  families, not only the five Matrix self-comparators. This explicitly includes the
  Ramp Summary Excel sibling and Intersection Summary PDF sibling even while those
  editions remain export-only in the current comparison UI.
- Retain all five unique Matrix PDF-to-Excel triangles across their six placements as
  product gates inside that broader seven-family cross-format proof.
- Treat retained 6.19/7.7/7.8/7.9 reports as version-pinned regression/drift fixtures:
  each exact edition either proves documented compatibility or an expected fail-closed
  schema transition. Never mix dates/editions silently or re-bless current truth from an
  older output.
- The retained Intersection Detail, Highway Detail, Highway Sequence PDF, Ramp Detail
  PDF, and Intersection Summary work-PC bundles before final acceptance.
- Every canary records full source identity and producer versions before re-blessing.

### Tier 5 — artifact/Matrix/frozen/work-PC acceptance

- Legacy-to-new metadata migration, interrupted writes, locks, same-metadata content
  replacement, semantic-version change, and app restart.
- Isolated real-data Everything, day, and baseline builds; no production destination
  is used for a test.
- One real two-day all-12 baseline run remains explicitly owed; do not substitute a
  synthetic or historical workbook for that acceptance gate.
- Exact frozen self-test for both package variants and source ZIP.
- Work-PC device-sign-in/browser/COM tests where the home environment cannot reproduce
  the configuration.

### Release rule

No finding is closed because a broad suite is green. Closure requires its own original
reproduction, the new negative/positive check, dependent invariants, and assigned real
gate. Any changed real count is a stop condition until source identity, domain decision,
and cell-level delta explain it.

## Safe batch and commit rules

- One safety primitive or one persisted-schema concern per commit.
- Two to five tightly coupled findings per ordinary semantic batch.
- One parser/report family per loader batch.
- One Matrix surface per integration commit.
- Do not combine a domain-policy change with an unrelated refactor.
- Stage dual readers before the artifact-epoch writer switch; do not release halfway.
- Run statewide canaries after core semantics, after each touched family, and once at
  final acceptance—not on every mechanical commit.
- Keep user changes and unrelated worktree edits out of implementation commits.

## Primary finding coverage index

This index—not narrative “integrates” lists—is authoritative for primary implementation
ownership. It assigns every stable finding exactly one primary phase. A finding remains
open until all explicitly named secondary closure gates pass; cross-cutting phases
exercise dependencies and per-family slices without double-owning it.

- Phase 1 safety: CMP-AUD-041, CMP-AUD-090, CMP-AUD-105, CMP-AUD-111,
  CMP-AUD-117.
- Phase 2 typed outcomes: CMP-AUD-017, CMP-AUD-026, CMP-AUD-075, CMP-AUD-077.
  The central-publisher item above is the primary Phase-2 slice; its Matrix formula-twin
  secondary closure is explicitly integrated with the artifact-twin finding in Phase 5.
- Phase 3 equality/identity: CMP-AUD-001, CMP-AUD-002, CMP-AUD-003, CMP-AUD-004,
  CMP-AUD-005, CMP-AUD-008, CMP-AUD-009, CMP-AUD-012, CMP-AUD-121,
  CMP-AUD-122, CMP-AUD-123.
- Phase 4 generic loaders: CMP-AUD-018, CMP-AUD-019, CMP-AUD-027,
  CMP-AUD-028, CMP-AUD-029, CMP-AUD-030, CMP-AUD-031, CMP-AUD-032, CMP-AUD-040,
  CMP-AUD-044, CMP-AUD-046.
- Phase 4 shared physical identity: CMP-AUD-045.
- Phase 4 shared PDF contract: CMP-AUD-049, CMP-AUD-050, CMP-AUD-067.
- Phase 4 normalized TSN: CMP-AUD-006, CMP-AUD-033, CMP-AUD-034, CMP-AUD-035,
  CMP-AUD-036, CMP-AUD-037, CMP-AUD-038, CMP-AUD-042, CMP-AUD-133,
  CMP-AUD-134, CMP-AUD-135, CMP-AUD-136, CMP-AUD-137, CMP-AUD-138,
  CMP-AUD-139, CMP-AUD-140, CMP-AUD-141, CMP-AUD-142, CMP-AUD-143,
  CMP-AUD-147, CMP-AUD-185.
- Phase 4 aggregates: CMP-AUD-020, CMP-AUD-021, CMP-AUD-022, CMP-AUD-023,
  CMP-AUD-024, CMP-AUD-025, CMP-AUD-071, CMP-AUD-144, CMP-AUD-145,
  CMP-AUD-146, CMP-AUD-148, CMP-AUD-149, CMP-AUD-150, CMP-AUD-151,
  CMP-AUD-152, CMP-AUD-153, CMP-AUD-154, CMP-AUD-183, CMP-AUD-184.
- Phase 4 Highway Log-specific loaders: CMP-AUD-047, CMP-AUD-048, CMP-AUD-132,
  CMP-AUD-157,
  CMP-AUD-167, CMP-AUD-168, CMP-AUD-169, CMP-AUD-170, CMP-AUD-171,
  CMP-AUD-172, CMP-AUD-173, CMP-AUD-174, CMP-AUD-175, CMP-AUD-176,
  CMP-AUD-177, CMP-AUD-178, CMP-AUD-179, CMP-AUD-180, CMP-AUD-181,
  CMP-AUD-182.
- Phase 4 Highway Detail PDF: CMP-AUD-051, CMP-AUD-052, CMP-AUD-053,
  CMP-AUD-054.
- Phase 4 Intersection PDF: CMP-AUD-056, CMP-AUD-057, CMP-AUD-058, CMP-AUD-059,
  CMP-AUD-060, CMP-AUD-061, CMP-AUD-062, CMP-AUD-070.
- Phase 4 Sequence/Ramp PDF: CMP-AUD-055, CMP-AUD-063, CMP-AUD-064,
  CMP-AUD-065, CMP-AUD-069, CMP-AUD-155, CMP-AUD-156, CMP-AUD-158,
  CMP-AUD-159, CMP-AUD-160, CMP-AUD-161, CMP-AUD-162, CMP-AUD-163,
  CMP-AUD-164, CMP-AUD-165, CMP-AUD-166.
- Phase 5 artifact identity: CMP-AUD-066, CMP-AUD-076, CMP-AUD-080, CMP-AUD-081, CMP-AUD-082,
  CMP-AUD-083, CMP-AUD-084, CMP-AUD-085, CMP-AUD-087, CMP-AUD-089, CMP-AUD-098,
  CMP-AUD-100, CMP-AUD-115, CMP-AUD-124, CMP-AUD-125, CMP-AUD-126,
  CMP-AUD-127, CMP-AUD-128, CMP-AUD-129, CMP-AUD-130, CMP-AUD-131.
- Phase 6 Matrix orchestration: CMP-AUD-010, CMP-AUD-013, CMP-AUD-088,
  CMP-AUD-091, CMP-AUD-092, CMP-AUD-093, CMP-AUD-094, CMP-AUD-095, CMP-AUD-096,
  CMP-AUD-097, CMP-AUD-099, CMP-AUD-101, CMP-AUD-102, CMP-AUD-103, CMP-AUD-104.
- Phase 7 views/evidence: CMP-AUD-039, CMP-AUD-043, CMP-AUD-068, CMP-AUD-106,
  CMP-AUD-107, CMP-AUD-108, CMP-AUD-109, CMP-AUD-110, CMP-AUD-112.
- Phase 8 validation/bundles: CMP-AUD-007, CMP-AUD-011, CMP-AUD-113, CMP-AUD-114,
  CMP-AUD-116, CMP-AUD-118, CMP-AUD-119, CMP-AUD-120.
- Phase 9 classic UI/docs: CMP-AUD-014, CMP-AUD-015, CMP-AUD-016, CMP-AUD-072, CMP-AUD-073,
  CMP-AUD-074, CMP-AUD-078, CMP-AUD-079, CMP-AUD-086.

## Historical authorized implementation progress through Phase 3

This list records the original implementation authorization through Phase 3. It is not a
second live progress surface; use `comparison-perfection-project.md` for current Stage-4+
state, blockers, and promotion conditions.

1. Complete — add/retain red checks for S1–S5.
2. Complete — implement S1 output/source alias rejection.
3. Complete — implement S2 ownership/Reset fail-closed.
4. Complete — implement S3 evidence literal guarding.
5. Complete — implement S4 credential redaction and final ZIP scan.
6. Complete — implement S5 missing-explicit-source failure.
7. Complete — run Phase-1 focused and full offline gates (98/98).
8. Complete — land Phase-2 types and additive result fields.
9. Complete — preserve exact direct/environment/PDF input outcomes before publication.
10. Complete — publish strict SHA-bound comparison generations through the real artifact
    transaction and add the shared fail-closed reducer.
11. Complete — switch Matrix/day/baseline/classic/validation consumers; partial and
    untrusted state can no longer render green.
12. Complete — run the Phase-2 focused and full offline gates (106/106).
13. Complete — type every early/preflight/cancel/commit terminal result and rerun the
    full Phase-2 gate (106/106).
14. Complete — input-bind `CORE-ID-78-XLSX-TSN` to its exact 218-member,
    26,384,760-byte versioned manifest digest.
15. Complete — D2/D3, the generic oracle, hardened XLSX stream, installed-Excel
    Med-Wid primitive, independent ID78 adapter, bound statewide canary, and remaining
    Phase-3 formula-state integration are green. Later source-first work is tracked in
    the dashboard rather than appended here.

Do not begin equality, partial-publication, identity-key, aggregate, or PDF-field
semantic changes until the applicable D1–D7 decisions are recorded.
