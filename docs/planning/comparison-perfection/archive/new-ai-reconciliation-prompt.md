# New-AI comparison-project reconciliation prompt

> **Archived — historical.** Superseded by the current surface: [COMPLETION-PLAN.md](../COMPLETION-PLAN.md) (plan & status) and [README.md](../README.md). Kept verbatim as point-in-time history; counts/hashes here reflect when it was written.

You are taking over a long-running comparison-perfection project in:

`C:\Users\Yunus\Projects\TSMIS-Reports-Exporter`

Your first assignment is **bounded reconciliation and next-step planning**, not product
implementation. The prior effort completed meaningful source/oracle work but also spent
too much time recursively hardening audit harnesses. Establish what is true, what is
changed, what remains unproven, and whether the next authorized phase should finish the
deferred audit or begin a narrowly bounded implementation batch.

## Hard stop for this first pass

You may read files, Git metadata/diffs, source manifests, existing audit outputs, and
the raw development corpus. You may write only one new reconciliation report at the
path specified below.

Do not during this pass:

- modify anything under `scripts/`;
- modify build, test, audit, packaging, UI, source-data, or existing documentation files;
- regenerate normalized files, consolidations, comparisons, evidence, or audit outputs;
- write into `C:\Users\Yunus\Downloads\TSMIS`;
- delete temporary or rejected attempts;
- reset, revert, checkout, stash, reformat, stage, commit, or otherwise clean the dirty
  worktree;
- infer authorship from timestamps, style, or filenames;
- claim that an accepted audit means product behavior is correct;
- create a new audit harness merely because an existing harness could be more elaborate.

Only propose a new check when a concrete raw-source, normalized-row, comparison-cell,
evidence, or publication-integrity contradiction requires it. Do not recursively audit
the audit tools. Prefer reopening existing exact artifacts over rerunning expensive
full-corpus work.

## Starting claims to verify, not trust

- 29 classic comparison recipes.
- 12 Matrix rows and 30 Matrix placements.
- Seven canonical TSN datasets and five evidence families.
- Stage 6 source-to-normalized audit coverage is 7/7.
- Stage 8 base TSMIS-vs-TSN audit coverage is 7/7.
- This does **not** complete the whole audit: Stages 9–10 companion-format,
  historical-edition, Report View, and exhaustive evidence work remain deferred.
- Product remediation and release acceptance remain incomplete.
- CMP-AUD-001 through CMP-AUD-237 should be unique and continuous.
- The seven accepted family records reportedly carry 44 unique product/evidence finding
  IDs red.
- The final bounded closeout changed no product code, but the shared worktree already
  contained extensive product changes.
- A recent Git census reported 62 modified tracked `scripts/` files plus three untracked
  product files. Recompute this; do not assume it is still current.

“Stage 8 accepted” means current source truth and observed product projection were
classified. It does not certify physical identity, comparison semantics, workbook
cells, Report Views, evidence, or end-to-end product perfection.

## Read first

1. Read `CLAUDE.md` completely.
2. Read `docs/planning/comparison-perfection/README.md`.
3. Read every document in `docs/planning/comparison-perfection/`, prioritizing the
   project dashboard, implementation handoff, finding ledger, canary bindings, source
   rebaseline, remediation plan, red-fixture index, and decision gates.
4. Read `docs/planning/fable5-repo-improvement-audit.md` without modifying it.
5. Read the relevant general records: `docs/INDEX.md`, `docs/comparison-engine.md`,
   `docs/tsn-parsers.md`, `docs/reports.md`, and `docs/verification-and-testing.md`.

Claude and Fable records are advisory. Reconcile their claims against current code,
immutable sources, independent oracles, and exact artifact identities.

## Reconciliation sequence

### 1. Inventory the dirty worktree

Capture current Git status and diffs read-only. Classify every relevant changed or
untracked item as:

1. product/runtime code;
2. product regression/check code;
3. independent audit/oracle tooling;
4. packaging/build configuration;
5. comparison-project documentation;
6. generated/temporary artifact; or
7. unrelated work.

For each relevant file or coherent group, record its apparent purpose, whether product
execution imports it, associated finding IDs/stage, completeness, risk, recommended
later disposition, and confidence. If authorship or intent cannot be proven, say so.
Identify unreachable, duplicate, partially integrated, or unexplained code. Do not mark
a finding fixed merely because code or a test exists.

### 2. Verify the frozen product boundary

Independently rebuild a read-only manifest of the entire `scripts/` tree. For each file,
serialize:

`relative/path<TAB>byte-length<TAB>sha256<LF>`

Use forward-slash paths and ordinal relative-path order. Expected frozen record:

- 321 files;
- 7,423,809 aggregate bytes;
- 34,351 manifest bytes;
- SHA-256 `df7bb8fc3d997d60d82ecb93344f821e858feb015eed62fffe859958c9151bea`.

This digest identifies the dirty takeover baseline; it does not prove correctness or
equivalence to Git HEAD. If it differs, report exact drift without restoring anything.

Verify that `docs/planning/fable5-repo-improvement-audit.md` still hashes to
`9deedb03d284af4bf005be16600c30544b05e0ba54801a4532b05587418b6d0e`.

### 3. Reconcile document and artifact integrity

Verify that:

- the 237 finding summary rows and 237 detailed headings are unique and continuous;
- statuses do not confuse audit-harness remediation with product remediation;
- every moved-document link resolves;
- the dashboard, handoff, remediation plan, source rebaseline, and canary ledger state
  the same stage boundary;
- rejected/interrupted attempts are never accepted witnesses;
- recorded source/result/acceptance/gate hashes correspond to existing files;
- contradictions and missing artifacts are reported rather than silently reconciled.

Use this evidence order:

1. immutable raw TSN/TSMIS bytes and manifests;
2. independent extraction/oracle evidence;
3. observed current-product output;
4. audit acceptance gates;
5. documentation summaries;
6. external-AI opinions.

### 4. Build a seven-family truth matrix

For each report family, separately record:

- raw source coverage;
- normalized-source conservation;
- TSN PDF↔Excel coverage where applicable;
- current TSMIS PDF↔Excel coverage;
- historical-edition coverage;
- Stage-8 source/oracle coverage;
- current product comparison correctness;
- Report View coverage;
- evidence coverage;
- exact open finding IDs;
- missing files or owner decisions.

Independently calculate the unique remaining red set and explain any difference from 44.
Explicitly label “audit complete” separately from “product green.”

TSN source semantics are fixed. The raw-only library is
`C:\Users\Yunus\Downloads\TSMIS\tsn_library`; do not write there or admit generated
outputs as raw inputs. Use both PDF and Excel variants when supplied. Same-source
PDF↔Excel verification is distinct from cross-system TSMIS↔TSN projection. Highway
Detail's TSMIS layout remains vendor-provisional; its TSN source remains fixed.

### 5. Decide the next phase without executing it

Give a reasoned recommendation among:

- finish all or a bounded subset of Stage 9–10 audit work first;
- begin one narrowly scoped product-remediation batch whose source/evidence dependencies
  are already sufficient; or
- stop for missing files, an ownership decision, or unexplained product-tree drift.

Do not assume that all Stage 9–10 work must finish before any safe correction; map the
actual dependency of each proposed batch. Conversely, do not implement a family change
whose companion-format or evidence truth is still needed to define correctness.

For each proposed batch, list stable finding IDs, intended product files, existing red
fixtures, missing oracle work, exact pre-red/post-green conditions, affected classic and
Matrix placements, evidence impact, regression scope, and stop/rollback condition.
Reject a wholesale rewrite unless file-by-file evidence shows incremental correction is
unsafe or impossible.

## Required output

Write only:

`docs/planning/comparison-perfection/reconciliation-report.md`

Use these sections:

1. Executive verdict
2. Authorization and stop-line confirmation
3. Frozen-manifest verification
4. Dirty-worktree inventory and attribution limits
5. Audit acceptance versus product correctness
6. Seven-family truth matrix
7. Findings/status reconciliation
8. Existing-code dependency and risk map
9. Documentation contradictions or broken links
10. Missing source files or owner questions
11. Audit-first versus implementation-first recommendation
12. Ordered next batches
13. Safe-to-proceed decision and prerequisites

Answer plainly:

- What product code is currently changed?
- What was actually completed?
- What remains unproven or incorrect?
- Is the existing audit evidence internally consistent?
- Did the frozen product tree drift?
- Should the next AI finish more audit work first?
- What is the smallest justified next batch?

End by confirming that you changed no product, test, audit-tool, source-data, generated
artifact, or existing-document file, and provide the reconciliation-report path. Stop
after producing that report and wait for owner authorization.
