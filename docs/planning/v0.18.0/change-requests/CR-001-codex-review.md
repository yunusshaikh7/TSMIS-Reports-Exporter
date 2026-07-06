# CR-001 — Codex review

## Verdict

**ACCEPTED WITH REQUIRED MODIFICATIONS**

## Short reasoning

Claude correctly understood the requested direction: the user wants to stop leaving offline-doable cleanup on the table, use v0.18.0 as the code-complete/work-PC validation build, and create a concrete handoff so v0.18.1 can close the field-validation loop. That direction fits the v0.18.0 structural-overhaul goal if the plan remains phase-by-phase, offline-verifiable at each v0.18.0 commit, and honest about what still requires real work-PC evidence.

The current repository state supports pausing for this amendment: `00-coordination.md` records execution paused after P9, Git HEAD is `decced443faa70ef0807c3e80c37605ca0e5e5da`, P9 is committed, P10 is next eligible, and there is no phase `in_progress` or `awaiting_review`. The proposal is mostly additive on top of committed seams (`task_coordinator`, engine DAG modules, P9 mock split), so it does not require reworking already-passed product code.

The proposal must be tightened before implementation resumes. In particular, do not retroactively reopen committed phase IDs, do not mark real-PDF/parser fixes as resolved without fixtures, do not imply v0.18.0 is field-validated, and keep the hard-deferral items out unless the user makes explicit separate decisions.

## Required modifications

### CR001-RM01 — Preserve committed phase history; add new phase IDs instead of reopening P5

`P5` is already committed as family 1 (`c0cfa39`) and reviewed as such. Do not reclassify the committed P5 row as if it were incomplete or newly blocking. Add a new post-P9 phase for the comparator-driver remainder, for example `P5b — TSN comparison driver DRY`, depending on committed P5/P4. That phase can be blocking under the amended plan, but the existing P5 commit remains historical and complete.

This same principle applies generally: pending phases (`P7b`, `P8c`) may be reclassified; committed phases are not reopened.

### CR001-RM02 — Make v0.18.0 an offline-validated validation candidate, not a field-validated GA

The amended plan must say:

- v0.18.0 remains fully offline-provable before commit/release.
- v0.18.0 may include live-path code intended for work-PC validation.
- v0.18.1 is the field-validated close-out after the user returns work-PC evidence.

Avoid plan language that implies v0.18.0 is already “field validated” or fully enterprise-accepted. “Enterprise-ready” is acceptable only if defined as “offline-validated and packaged for enterprise/work-PC validation,” not as operational sign-off.

### CR001-RM03 — P8c may move into v0.18.0 code, but as revertible RC behavior with v0.18.1 acceptance

Codex accepts implementing P8c code in v0.18.0 now that O7 is available as a validation window. Do not add a runtime flag by default; a flag would add temporary surface area and risks testing a different configuration than the user will run. Keep the CR’s proposed “each behavior change is its own revertible commit” discipline.

Required plan text:

- P8c is blocking for v0.18.0 code completion.
- P8c work-PC acceptance is not claimed until v0.18.1.
- P8c must extend the fake-site fixture before behavior changes: exact label, prefix/suffix near-miss labels, disabled option, malformed wait-js/config error, CDP open/close, and cancel-latency coverage as applicable.
- No live TSMIS access or credential/profile inspection during implementation.

### CR001-RM04 — Narrow P12 PDF/parser claims to what can actually be proven offline

The CR overstates the offline closability of the PDF/ramp-summary items. The approved plan explicitly recorded that some parser correctness items need real source PDFs. P12 may add an offline harness, independent expected-row oracle design, synthetic/minimal fixtures, diagnostics, and the capture contract. It must not mark these as fully resolved unless a committed synthetic or returned fixture truly reproduces the failure and the fix is verified against it.

Required plan text:

- `pdf-consolidator-no-row-count-verification`: v0.18.0 may add the independent oracle harness and evidence capture path; real-PDF acceptance remains v0.18.1 unless real fixtures are available during implementation.
- `pdf-stale-geometry-carryforward-silent-corruption`: do not claim stale-geometry emit correctness is closed by synthetic-only coverage unless the synthetic fixture proves the exact row-emission failure mode.
- `ramp-summary-parse-failure-misattributed-to-source` and `ramp-summary-duplicate-pop-pattern-misassignment`: keep as v0.18.1 evidence-driven fixes unless a safe, minimal offline fixture is created that reproduces the exact failure.

### CR001-RM05 — P13 evidence collection must be privacy- and credential-safe

The proposed `--collect-evidence` mode is acceptable only with explicit boundaries:

- Never collect auth state, browser profiles, cookies, DPAPI material, or credentials.
- Do not include private report outputs or source PDFs by default.
- If real PDFs/output workbooks are needed, the user must explicitly select or place them in a documented evidence folder; the bundle manifest must list every included file.
- Redact or avoid sensitive paths/tokens where practical.
- Include a no-code/manual fallback procedure for locked-down PCs where even the evidence mode cannot run.

The evidence-mode code path must be exercised by offline tests and, where feasible, by the existing self-test/frozen gate without launching the GUI.

### CR001-RM06 — Keep hard-deferral items deferred unless the user separately opts in

The amended plan must keep these out of the automatic CR scope:

- DPAPI/O2: still a real portability trade-off. Optional off-by-default encryption can be designed later, but implementing it in v0.18.0 requires explicit user approval.
- Runtime signature verification/code-signing trust: still blocked on a real cert/publisher decision. P10 may keep workflow signing parity and checksum hardening, but no runtime signature abstraction or new crypto dependency without explicit user/procurement approval.
- `compare_core` `min-cost-pairs`: remains deferred under the regression lock unless the user explicitly authorizes a separate compare-core re-proof phase.
- D16-dropped items (`paths` init rewrite, bounded queue, CI trigger change, `run_compare` returns counts, `_safe_join`/`full_snapshot`, generic snapshot-once) remain dropped.

### CR001-RM07 — Correct stale counts and evidence statements

CR-001 says there are 67 Python `build/check_*` files. The workspace currently has 65 Python `build/check_*.py` files. Update all plan/coordination text to use verified counts or avoid hard-coding the count unless it is recomputed at the time of the phase report.

Similarly, keep the P5 “COM/Route-1 harness” wording honest: the current repository has five `check_compare_*_tsn.py` offline canaries and the work-PC Route-1/COM acceptance is still external unless/until a local harness is committed.

### CR001-RM08 — Keep P7b/P9b decomposition bounded

P7b and P9b may become blocking, but the plan must retain the original anti-rewrite constraints:

- no framework rewrite;
- no ES modules unless separately justified and proven in pywebview/file/frozen modes;
- no one-class-per-action endpoint sprawl;
- no behavior change mixed with mechanical movement;
- pywebview API names, event order, `#mock`, classic script ordering, and Lesson-10 `sr-only` behavior remain protected.

P9b must extend `check_ui_boot.js`/`check_ui_contract.py` and include a `#mock` smoke requirement. P7b must prove endpoint extraction with existing bridge checks plus any new API-surface identity check needed for moved methods.

## Specific plan text Claude must update

Update `docs/planning/v0.18.0/05-claude-final-plan.md`:

- Add a CR-001 disposition section or table near the readiness history.
- Update the phase graph/table in §H to add new post-P9 phases without reopening committed P5. Recommended shape: `P5b`, `P7b`, `P8c`, `P9b`, expanded `P10`, `P12`, `P13`, then `P11` last.
- Update §I phase descriptions for `P5b`, `P7b`, `P8c`, `P9b`, expanded `P10`, `P12`, `P13`, and `P11`.
- Update §J and §J2 so previously deferred updater/audit items are either implemented in v0.18.0, split into “v0.18.0 harness/code + v0.18.1 acceptance,” or explicitly still deferred.
- Update §K to define the v0.18.0 offline DoD and add a separate §K2 for v0.18.1 work-PC acceptance.
- Update §L rollback notes for the new phases.
- Update §M to become the P13 evidence/acceptance handoff rather than a loose owed-work list.
- Update §N exclusions to retain O2/cert/min-cost/D16 exclusions unless explicitly approved later.

Update `docs/planning/v0.18.0/00-coordination.md`:

- Mark CR-001 accepted with required modifications after the plan edits are made.
- Add a decision-log entry for the amended two-tier release model.
- Update the phase table and implementation log without changing committed phase history.
- Keep implementation paused until `05` and `00` are amended.

Do not update canonical product docs yet; P11 remains the docs reconciliation phase.

## Whether Claude may resume implementation after updating the plan

Yes, but only after Claude updates `05-claude-final-plan.md` and `00-coordination.md` with the required modifications above. No product implementation should resume while CR-001 is still recorded as awaiting Codex review or while the amended phase graph is ambiguous.

No additional user approval is required for this amended plan if the hard-deferral items remain deferred as specified. Any attempt to implement DPAPI, runtime signature verification, or `compare_core` min-cost pairing requires explicit user approval beyond CR-001.

## Phase impact

- Current phase: none. There is no active implementation phase; P9 is committed and P10 is pending.
- Future phases: yes. P7b and P8c become blocking; P10 expands; P11 remains last and depends on the amended blocking set.
- New phases required: yes. Add separate phases for the P5 comparator-driver remainder, P9b deeper frontend modularization, P12 residual offline audit hardening/evidence harnesses, and P13 work-PC handoff/v0.18.1 plan.
- Already-completed phase risk: acceptable if changes stay additive behind the committed seams and committed phase history is not rewritten.

## Extra verification Codex requires before the next phase commit

For the first implementation phase after CR-001 and every new/expanded phase:

- The phase report must state which CR-001 items it implements and which it deliberately leaves for later phases.
- New behavior or restructuring must be RED-proven with targeted checks before the final green run.
- Run the phase-specific targeted checks plus the existing offline golden checks appropriate to the touched area before Codex review.
- If the phase touches packaging/updater/evidence collection, include source-zip/frozen/self-test reachability checks as scoped by PA/P10, without destructive shared-artifact work unless the approved phase explicitly requires it.
- If the phase touches frontend structure, run `node --check`, `check_ui_boot.js`, `check_ui_contract.py`, the existing Node UI checks, and a `#mock` smoke.
- If the phase touches live-path engine behavior, use the fake-site fixtures and no live TSMIS.
- If the phase touches evidence collection, prove the bundle excludes credentials/auth/browser profile data by test.

Implementation should remain paused until the plan and coordination file reflect this review.
