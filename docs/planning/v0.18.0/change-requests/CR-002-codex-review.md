# CR-002 Codex review

## Verdict

ACCEPTED WITH REQUIRED MODIFICATIONS

## Short reasoning

Claude correctly identified a real plan gap: the v0.18.0 branch is based before the v0.17.2-v0.17.8 work, while `origin/main` now contains the Intersection Detail (PDF) report family and later Intersection Detail vs-TSN comparison behavior. Shipping v0.18.0 without a deliberate forward-port would regress current shipped behavior.

The amendment fits v0.18.0 because it is not a speculative new feature for this branch; it is a forward-port of already-shipped/current-main behavior into the refactored architecture. A direct merge/rebase would be unsafe because the v0.18.0 branch has already changed report metadata, UI boot/mocking, packaging checks, matrix plumbing, and stable-ID handling.

The proposed P14/P15 split is directionally sound, but the proposal must be corrected before implementation. It still names some pre-refactor targets as if they were authoritative, and it proposes carrying a dormant `compare_core.context_fill` API even though the v0.17.8 final schemas no longer use it and the approved v0.18.0 plan treats `compare_core` as protected.

Evidence checked:

- `origin/main` is `068b697`; the divergence from `d2ee353` is the v0.17.2-v0.17.8 chain documented in the CR.
- `origin/main:docs/refactor-handoff-v0.17.1-to-v0.17.5.md` is the correct feature map and says v0.17.8 supersedes the earlier v0.17.7 comparison notes.
- Current v0.18.0 branch uses `scripts/report_catalog.py` as the report metadata source of truth; `scripts/reports.py` derives from it.
- Current UI mock ownership is `scripts/ui/mock.js`; `build/check_ui_boot.js` explicitly asserts that `app.js` no longer defines or boots `makeMockApi`.
- Current v0.18.0 `scripts/compare_core.py` has `CompareSchema.extra_sheet_writer` but no `context_fill`.
- `origin/main` contains `context_fill` only in `scripts/compare_core.py` and the handoff/docs notes; the v0.17.8 final Intersection Detail schemas dropped the active use.

## Required modifications

### CR002-RM1 - Port into the refactored sources of truth, not the old pre-refactor registry locations

Required correction:

- P14 must say that new report metadata is added to `scripts/report_catalog.py` first, with `scripts/reports.py` remaining derived compatibility/API surface.
- Any mention of updating `scripts/reports.py` registry rows or `_CONSOLIDATOR_BY_SUBDIR` as the primary source of truth must be replaced with current-branch targets: catalog entries, derived report APIs, matrix helper branches, and catalog parity checks.
- P14 must update/extend `build/check_report_catalog.py` so the catalog golden snapshot, derived `reports.py` API, backend bridge payload, and mock payload stay in parity.

Repository evidence:

- `scripts/report_catalog.py` begins with "The ONE source of truth for report metadata".
- `scripts/reports.py` says `report_catalog.py` is the single source of truth and derives `EXPORT_REPORTS`, `EXPORT_KEYS`, consolidate rows, compare rows, and matrix rows.
- `build/check_report_catalog.py` verifies the catalog against the derived report APIs and UI mock payload.

### CR002-RM2 - Port frontend mock changes into `mock.js`, not `app.js`

Required correction:

- P14/P15 UI text must target `scripts/ui/mock.js` for mock fixtures and `scripts/ui/contract.js` / bridge payload checks for contract shape.
- Do not reintroduce `makeMockApi` or mock boot logic into `scripts/ui/app.js`.
- If Intersection Detail (PDF) appears in any UI mock matrix, compare, source-status, or report-list payload, the relevant contract and boot checks must be updated with the same final keys and labels.

Repository evidence:

- `scripts/ui/mock.js` owns `makeMockApi()` and calls `boot(makeMockApi())`.
- `build/check_ui_boot.js` asserts that `app.js` no longer defines `makeMockApi` and that `mock.js` owns mock boot.
- The CR proposal still names `scripts/ui/app.js` fixtures from `origin/main`, which is stale for the refactored branch.

### CR002-RM3 - Do not include dormant `compare_core.context_fill` in this amendment

Required correction:

- P15 must not port `CompareSchema.context_fill` as part of CR-002.
- Replace P15 wording that says "add/adopt the `compare_core` `context_fill` opt-in" with: "Do not port dormant `context_fill`; v0.17.8 final Intersection Detail behavior compares the formerly greyed date columns and uses existing `extra_sheet_writer` for Report View."
- `scripts/compare_core.py` remains protected unless a later separately approved change proves an active schema needs a core opt-in and includes no-op-default identity checks for every non-opted-in schema.

Repository evidence:

- Current v0.18.0 `CompareSchema` already supports `extra_sheet_writer`.
- Current v0.18.0 has no `context_fill`.
- `origin/main` v0.17.8 has `context_fill` only as dormant `compare_core` code and docs/handoff notes; the v0.17.8 handoff says `context_fill` was dropped from the Intersection Detail schema.
- The approved v0.18.0 plan explicitly protects `compare_core` from behavior/formula/label/layout/return drift except where characterized and justified.

### CR002-RM4 - Make stable IDs and persisted batch manifests an explicit P14 compatibility gate

Required correction:

- Adding `intersection_detail_pdf` must be append-only relative to the existing export/report keys.
- Existing seven export keys must not be reordered or renamed.
- `scripts/batch_manifest.py` and `build/check_stable_ids.py` must prove that v1 integer-index manifests from the pre-Intersection-PDF shape still resolve correctly, and that the new v0.17.8-era index/key resolves correctly.
- If `_V017_EXPORT_ORDER` is extended to include `intersection_detail_pdf`, it must preserve positions 0-6 exactly and add the new key only at the correct appended position.

Repository evidence:

- `scripts/batch_manifest.py` documents that manifest v1 stored integer indices into `EXPORT_REPORTS`.
- `build/check_stable_ids.py` currently assumes the frozen v0.17 export order equals the current export keys; adding a report without an explicit compatibility assertion could hide an index migration regression.

### CR002-RM5 - Keep P14 and P15 behavior boundaries distinct

Required correction:

- P14 should cover the Intersection Detail (PDF) report family: export spec/save helper, PDF parser/consolidator, matrix/day-matrix plumbing, catalog/report metadata, backend bridge/mock/contract payloads, cleanup/pruning, packaging hidden imports, fake-site fixtures, and PDF-vs-Excel/PDF-vs-TSN adapter presence.
- P15 should cover the evolved Intersection Detail vs-TSN comparison behavior: J-P signal subtype crosswalk, compare-everything policy, read-time TSN-library re-normalization, position-aligned dates, numeric padding, `_SIGNALIZED_LABEL = "S"`, Report View, summary folding, and final canary expectations.
- P13 must remain after P14 and P15, because work-PC/live verification must verify the final 8-report application behavior, not the pre-forward-port 7-report shape.

Repository evidence:

- `origin/main` separates the initial PDF report-family commits from later vs-TSN behavior commits.
- The CR proposal already recognizes the two problem shapes; the final plan must make the split enforceable in phase entry/exit criteria.

### CR002-RM6 - Update packaging/build verification for the refactored branch, not by copying old files blindly

Required correction:

- P14 must update `build/app.spec` hidden imports for the new export/consolidate/compare modules, but must preserve current v0.18.0 packaging conventions.
- P14 must update source-zip and console/batch checks according to the refactored sources of truth. If console menus now derive from `EXPORT_REPORTS`, the check should prove derivation instead of copying old literal menu edits.
- Do not port `version.py` from `origin/main`; v0.18.0 remains the target release version.
- Do not add output/runtime artifacts beyond intentional tracked placeholder policy already used by the repository.

Repository evidence:

- Current `build/app.spec` has explicit hidden-import lists.
- `build/check_source_zip_smoke.py` already checks that the source-zip export menu derives from `reports.EXPORT_REPORTS`.
- The CR proposal correctly names packaging risk but also references old console-menu edits from `origin/main`.

### CR002-RM7 - Use `origin/main` and the handoff document as inputs, but no merge/rebase

Required correction:

- The plan text must state that implementation is a deliberate forward-port from `origin/main` `068b697`, guided by `origin/main:docs/refactor-handoff-v0.17.1-to-v0.17.5.md`.
- Do not use local `main` as source of truth if it is stale.
- Do not merge or rebase `origin/main` into the v0.18.0 branch; port file-by-file into the refactored architecture.

Repository evidence:

- Current branch HEAD is `d15216d`; `origin/main` is `068b697`.
- A direct diff from current v0.18.0 HEAD to `origin/main` includes many refactor-branch deletions/reversions, so merge-style adoption would endanger already-completed v0.18.0 work.

## Specific plan text Claude must update

Claude must update the approved plan and coordination state before resuming implementation:

1. In `docs/planning/v0.18.0/05-claude-final-plan.md`, add a CR-002 amendment section that:
   - records the accepted source of truth: `origin/main` `068b697` plus `docs/refactor-handoff-v0.17.1-to-v0.17.5.md`;
   - states that this is a forward-port into the refactored v0.18.0 architecture, not a merge/rebase;
   - states that dormant `compare_core.context_fill` is not part of the accepted amendment.

2. In the phase sequence, insert:
   - **P14 - Intersection Detail (PDF) report family forward-port** after committed P12;
   - **P15 - Intersection Detail vs-TSN behavior forward-port** after P14;
   - then P13 work-PC verification and P11 documentation/release finalization.

3. In P14 entry/exit criteria, name concrete affected areas:
   - `scripts/report_catalog.py`;
   - derived `scripts/reports.py` APIs;
   - `scripts/export_intersection_detail_pdf.py`;
   - `scripts/exporter.py`;
   - `scripts/intersection_detail_columns.py`;
   - `scripts/consolidate_tsmis_intersection_detail_pdf.py`;
   - `scripts/compare_intersection_detail_pdf.py`;
   - `scripts/compare_env.py`;
   - `scripts/matrix.py`;
   - `scripts/day_matrix.py`;
   - `scripts/gui_worker.py`;
   - `scripts/gui_api.py` / bridge payloads as needed;
   - `scripts/ui/mock.js` / contract checks as needed;
   - `build/app.spec`;
   - fake-site fixtures/checks;
   - catalog, stable-ID, matrix, day-matrix, source-zip, pruning, and UI-boot checks.

4. In P15 entry/exit criteria, name concrete affected areas:
   - `scripts/compare_intersection_detail_tsn.py`;
   - `scripts/compare_intersection_summary_tsn.py`;
   - `scripts/compare_intersection_detail_pdf.py` where it reuses the evolved detail schema/loaders;
   - `scripts/summary_layout.py` only if Report View support needs current-main parity;
   - TSN library read-time normalization paths;
   - canary checks for Excel-vs-TSN and PDF-vs-TSN final v0.17.8 behavior.

5. In the hard-deferred/protected-behavior section, replace "no new features" with a precise exception:
   - "CR-002 forward-ports current-main v0.17.2-v0.17.8 shipped behavior; unrelated new features remain deferred."

6. In the verification section, add separate P14 and P15 verification lists and update P13's live/work-PC evidence kit to assume the final 8-report shape.

7. In `docs/planning/v0.18.0/00-coordination.md`, mark CR-002 as accepted with required modifications, record the new phase order, and leave implementation paused until the plan text above is updated.

## Whether Claude may resume implementation after updating the plan

Yes, Claude may resume implementation after updating the plan and coordination file with the required modifications above.

No additional user approval is required if Claude follows this review and omits dormant `compare_core.context_fill`.

If Claude still wants to port `compare_core.context_fill`, implementation must remain paused for a separate explicit decision because that would amend a protected core-comparison boundary without an active v0.17.8 schema user.

## Phase impact

This affects future work and requires two new phases:

- New P14 before P13/P11.
- New P15 before P13/P11.
- Existing completed phases should not be reopened.
- P13 must move later and verify the final forward-ported application.
- P11 remains last and must absorb the documentation/release-note impact.

There is no current implementation phase in progress according to the coordination file; the pause point between committed P12 and pending P13 is sane.

## Extra verification Codex requires before the next phase commit

Before committing P14, Claude must run and report at least:

- `build/check_intersection_detail_pdf.py`
- `build/check_report_catalog.py`
- `build/check_stable_ids.py`
- `build/check_fake_site.py`
- `build/check_intersection_gate.py`
- `build/check_matrix.py`
- `build/check_matrix_bridge.py`
- `build/check_matrix_tsn.py`
- `build/check_day_matrix.py`
- `build/check_gui_bridge.py`
- `build/check_app_modules.py`
- `build/check_import_direction.py`
- `build/check_source_zip_smoke.py`
- `build/check_ui_boot.js`
- the relevant UI/contract mock parity check(s) if payloads change

Before committing P15, Claude must run and report at least:

- the Intersection Detail vs-TSN detail canary check;
- the Intersection Summary vs-TSN summary/fold check;
- PDF-vs-TSN and PDF-vs-Excel adapter checks;
- the compare audit/regression checks that protect existing Highway Log, Ramp, Intersection Summary, and Intersection Detail comparison behavior;
- a specific statement that `compare_core.context_fill` was not ported. If that statement is false, the phase must stop for the separate approval described above.

Before P13 can be reviewed, Claude must update the work-PC/live evidence kit so it covers the final eight-report application shape, including Intersection Detail (PDF), without committing private report data, credentials, profiles, or internal site source.

---

# Supplemental CR-002 review after plan amendment

## Verdict

ACCEPTED

## Short reasoning

No newer `CR-###-claude-proposal.md` file exists; the relevant proposal remains CR-002. The current coordination file and amended final plan now reflect the required CR002-RM1 through CR002-RM7 modifications from the review above.

The plan can safely continue with the amendment because it now treats the v0.17.2-v0.17.8 work as a deliberate forward-port into the refactored architecture, not a merge/rebase. It adds P14 and P15 before P13/P11, keeps completed phases additive/untouched, targets the current sources of truth (`report_catalog.py`, `mock.js`, stable IDs, packaging checks), and explicitly omits dormant `compare_core.context_fill`.

Repository/current-state check:

- Current HEAD remains `d15216d`.
- The product tree has no tracked product/source diff; only the untracked planning workspace is present.
- `docs/planning/v0.18.0/00-coordination.md` marks CR-002 accepted with required modifications, P14 pending, and order `P14 -> P15 -> P13 -> P11`.
- `docs/planning/v0.18.0/05-claude-final-plan.md` has §A0d with CR002-RM1 through CR002-RM7 and dedicated P14/P15 sections.

## Required modifications, if any

None beyond the modifications already recorded above. They are now reflected in the amended plan.

Non-blocking caution: the coordination file's one-line CR-002 summary still mentions the historical `context_fill` divergence before immediately clarifying that dormant `context_fill` is not ported. This is not a blocker because §A0d, D26, and the phase text are explicit that `compare_core` remains protected/unmodified.

## Specific plan text Claude must update

No further plan text update is required before implementation resumes.

The amended plan already contains:

- source `origin/main` `068b697` plus the handoff document;
- file-by-file forward-port, no merge/rebase;
- P14/P15 insertion before P13/P11;
- `report_catalog.py` as report metadata SoT;
- `scripts/ui/mock.js` as mock fixture/boot owner;
- append-only stable-ID/manifest compatibility;
- packaging/source-zip/version constraints;
- no dormant `compare_core.context_fill`.

## Whether Claude may resume implementation after updating the plan

Yes. The plan has already been updated, so Claude may resume implementation from P14.

No additional user approval is required provided dormant `compare_core.context_fill` remains omitted.

## Whether this affects the current phase, a future phase, or requires a new phase

This requires the two new future phases already inserted:

- P14: Intersection Detail (PDF) report-family forward-port.
- P15: Intersection Detail vs-TSN comparison-behavior forward-port.

There is no current in-progress implementation phase. P13 and P11 correctly move after P14/P15.

## Any extra verification Codex requires before the next phase commit

No extra verification beyond the P14/P15 lists already recorded above and copied into the amended final plan.

For the next phase commit, P14 must still report the catalog, stable-ID, fake-site, matrix/day-matrix, GUI bridge, app-module/import-direction, source-zip, UI boot, and Intersection Detail PDF checks listed in this review. P15 must still report the final v0.17.8 comparison canaries and explicitly state that `compare_core.context_fill` was not ported.
