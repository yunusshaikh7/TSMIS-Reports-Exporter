# Codex Readiness Review

## Readiness round 1

### 1. Verdict: `NOT READY`

### 2. Blocking corrections, if any

- Add the promised item-by-item disposition of every still-open Phase-3 audit finding to the final plan now, assigning each to a phase or an explicit deferral with destination and rationale. Section A says R1-M05 is resolved and points to §I, but §I does not disposition most open findings—for example report-selection rearming, PDF empty-save validation, `wait_js` validation, reset-token consumption, `device_ok` inference, side-label truncation, greedy duplicate matching, fixed Ramp Summary coordinates, junction handling, and overwrite TOCTOU. Deferring the reconciliation itself to P11 leaves v0.18.0 scope and completion unverifiable.
- Resolve the updater integrity disposition within that table: §J labels `size-and-checksum-guards-both-skippable` as “Implement,” but the planned behavior still permits size-only installation with a warning. Either require a trusted checksum before extraction or mark the finding explicitly deferred/accepted with rationale; publication checks alone do not close the runtime fallback identified by the audit.

### 3. Non-blocking cautions

- Correct “13 work units” to “13 release-blocking units plus 3 conditional units,” and make P11 depend only on completed release-blocking phases; the document currently contains 16 phase headings and a broad `P1..P10 → P11` edge.
- Clarify that explicitly pinning `cryptography` is dependency locking for the existing `pdfminer.six` transitive dependency, so it does not contradict “no new crypto dependency.”
- In P2, place the promotion journal outside any directory being renamed and specify how the wrapper handles existing `mode="both"` comparator calls while keeping `compare_core` untouched.

### 4. Short explanation of the verdict

The final plan successfully resolves the prior architectural blockers: outcome and artifact state are separated, packaging verification moves early, identity and migration contracts are concrete, the engine DAG is acyclic, risky phases are split, protected behavior is explicit, and completion tests are substantially objective. Readiness is withheld only because the claimed audit reconciliation is incomplete and one audited updater gap is currently misclassified as closed. Once those scope records are corrected, the plan should be ready for user approval without another broad redesign.

## Readiness round 2

### 1. Verdict: `NOT READY`

### 2. Blocking corrections, if any

- Add explicit dispositions for the three PDF Highway Log audit findings that §J2 currently excludes as closed: `pdf-consolidator-no-row-count-verification`, `pdf-page-skip-unlogged-when-no-prior-geometry`, and `pdf-stale-geometry-carryforward-silent-corruption`. Current HEAD now counts/logs dropped lines and warns when carried-forward geometry is used, but `consolidate_tsmis_highway_log_pdf.py` still emits rows using stale geometry and has no independent expected-row completeness check; `build/check_tsmis_pdf_reconcile.py` verifies warning banners only. Classify each as mitigated, resolved, or deferred with a phase/destination and acceptance evidence. Do not describe the reporting-only change as closing parser correctness.

### 3. Non-blocking cautions

- Move `wait_js` validation out of behavior-neutral P8b or explicitly permit that narrow behavior change there with its characterization test.
- For audit items assigned to conditional P8c, record the default disposition as deferred when O7 is unavailable rather than unconditionally “Resolved.”
- When extracting `mock.js`, specify that the extracted script owns mock boot after defining `makeMockApi`; loading it after `app.js` cannot preserve the current immediate `boot(makeMockApi())` call unchanged.

### 4. Short explanation of the verdict

Round 1’s blockers and cautions are otherwise resolved: the updater is fail-closed on missing checksum, the audit table is comprehensive apart from the PDF trio, phase count/dependencies are corrected, and artifact/build contracts are concrete. Readiness is withheld only because the plan still overstates three parser-risk findings as closed. Correcting those dispositions should make the plan ready for user approval without architectural revision.

## Readiness round 3

### 1. Verdict: `READY FOR USER APPROVAL`

### 2. Blocking corrections, if any

None.

### 3. Non-blocking cautions

- If O7 is unavailable, omit P8c behavior-change commits from v0.18.0 rather than shipping dormant code whose live acceptance is deferred.
- Keep P0's small behavior changes—side-label preservation and the Ramp Summary schema guard—in isolated, characterized commits despite the phase's mostly diagnostic scope.
- Ensure the cache envelope version finalized for release already includes P2 fingerprints so users experience one post-upgrade rebuild, as promised.

### 4. Short explanation of the verdict

The final plan now resolves all verified blockers. It identifies concrete files and contracts, places characterization and exact-artifact gates before risky restructuring, preserves comparison and browser/threading invariants, defines migrations and rollback behavior, covers frontend, console, packaging, persistence, updater, and audit scope, and separates conditional work from the release definition of done. Its phases are reviewable and realistic for sequential implementation.

## Readiness round 4

### 1. Verdict: `READY FOR USER APPROVAL`

### 2. Blocking corrections, if any

None.

### 3. Non-blocking cautions

- Treat the approved plan as the scope baseline during implementation; any attempt to move conditional P8c work into v0.18.0 without O7 acceptance should return for review.
- Preserve the stated phase-boundary rule that every completed phase leaves the application runnable and all applicable blocking checks green.

### 4. Short explanation of the verdict

The plan remains ready after incorporating every Round-3 caution. No unresolved contradiction or missing readiness area was introduced: the scope, characterization gates, protected behavior, migrations, compatibility surfaces, audit dispositions, packaging verification, measurements, and objective completion criteria remain concrete and executable phase by phase.
