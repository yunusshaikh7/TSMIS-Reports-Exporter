Final review round 1

## 1. Verdict: `READY FOR RELEASE PREPARATION`

The completed v0.18.0 branch is ready for release preparation. I found no product-code, packaging, migration, or test-gate blocker. The remaining owed work is correctly framed as v0.18.1/work-PC acceptance or explicit hard deferral, not as unfinished v0.18.0 release-blocking work.

## 2. Blocking findings

None.

## 3. Definition-of-done checklist

- [x] Branch baseline and history reviewed: starting SHA `d2ee35333f3ebd3a070c1adfec893c10d2ffbe58`, current HEAD `375b48ca4bb5da9b1f5c0191998a3225c7c35004`, 25 commits after the recorded branch point.
- [x] Phase gate history reviewed: every phase review ends in `PASS` or a remediated `PASS WITH FIXES`; the two P0 behavior-fix commits (`a009b6d`, `36ce1c4`) are explicitly authorized in the final plan and coordination file.
- [x] No planning files are staged or committed: `git ls-files docs/planning` is empty and `git diff --cached --name-status` is empty.
- [x] No uncommitted product close-out changes exist: `git status --short` shows only untracked `docs/planning/`.
- [x] Product diff inspected from recorded branch point: `d2ee353..HEAD` changes 150 non-planning files. The 148-file metric in the close-out report corresponds to `origin/main..HEAD`, not the recorded branch point; this is a non-blocking measurement clarification.
- [x] Suspicious committed-path scan clean for auth/profile/output/dist/cache/bundle artifacts.
- [x] Core comparison lock held: `scripts/compare_core.py` is unchanged from `d2ee353`; `context_fill` is absent from shipped code.
- [x] Report catalog, stable IDs, manifest append-only compatibility, console/menu parity, mock parity, and packaging reachability checks pass.
- [x] Outcome, transaction, persistence, filesystem-safety, ownership-marker, and updater hardening checks pass.
- [x] Frontend/backend contract, UI boot, matrix rendering, compare routing, GUI bridge, task coordination, and worker lifecycle checks pass.
- [x] Engine decomposition checks pass: import direction is acyclic, engine layers do not import the `common.py` shim, and the compatibility shim re-exports the preserved surface.
- [x] P14/P15 forward-port checks pass for Intersection Detail (PDF), report/matrix wiring, and the v0.17.8 Intersection Detail/Summary vs-TSN behavior.
- [x] Build/release design checks pass: hashed build lock parity, app module reachability, source ZIP smoke, evidence-bundle privacy guard, release workflow artifact completeness logic, and release-notes `-o` path.
- [x] Canonical documentation and audit reconciliation are present in committed docs, including v0.18.0/v0.18.1 two-tier framing and hard deferrals.

## 4. Verification performed

Repository and history:

- `git branch --show-current`
- `git rev-parse HEAD`
- `git log --oneline --reverse d2ee35333f3ebd3a070c1adfec893c10d2ffbe58..HEAD`
- `git diff --stat d2ee35333f3ebd3a070c1adfec893c10d2ffbe58..HEAD -- . ':!docs/planning'`
- `git diff --shortstat origin/main..HEAD -- . ':!docs/planning'`
- `git status --short`
- `git diff --cached --name-status`
- `git ls-files docs/planning`
- suspicious-path scan over the committed diff

Documentation/planning review:

- Read `00-coordination.md`, `05-claude-final-plan.md`, every phase report/review file under `docs/planning/v0.18.0/phases/`, and `final-claude-report.md`.
- Checked final review verdicts across all phase review files.
- Checked committed docs for v0.18.0/v0.18.1 framing, audit disposition, work-PC handoff, and release-prep consistency.

Independent checks run:

- `python -B build/check_report_catalog.py`
- `python -B build/check_stable_ids.py`
- `python -B build/check_app_modules.py`
- `python -B build/check_import_direction.py`
- `python -B build/check_build_env.py`
- `python -B build/check_source_zip_smoke.py`
- `python -B build/check_evidence_bundle.py`
- `python -B build/check_updater.py`
- `python -B build/check_compare_intersection_detail_tsn.py`
- `python -B build/check_compare_intersection_summary_tsn.py`
- `python -B build/check_compare_env_highway_log_pdf.py`
- `python -B build/check_pdf_row_oracle.py`
- `node build/check_ui_boot.js`
- `node build/check_mx_partial_render.js`
- `node build/check_compare_routing.js`
- `python -B build/check_worker_lifecycle.py`
- `python -B build/check_gui_api_surface.py`
- `python -B build/check_gui_bridge.py`
- `python -B build/check_reset_safety.py`
- `python -B build/check_consolidate_toctou.py`
- `python -B build/check_persistence.py`
- `python -B build/check_owned_dir.py`
- `python -B build/check_outcome_contract.py`
- `python -B build/check_artifact_store.py`
- `python -B build/check_batch_outcome.py`
- `python -B build/check_consolidate_outcome.py`
- `python -B build/check_tsn_outcome.py`
- `python -B build/check_read_counts_layout.py`
- `python -B build/check_engine_layers.py`
- `python -B build/check_engine_leaves.py`
- `python -B build/check_tsn_normalizer.py`
- `python -B build/check_compare_tsn_common.py`
- `python -B build/check_edge_login.py`
- `python -B build/check_export_engine.py`
- `python -B build/check_p2_freshness.py`
- `python -B build/check_fake_site.py`
- `python -B build/check_compare_env_sidelabel.py`
- `python -B build/check_ramp_summary_schema.py`
- `python -B build/check_matrix.py`
- `python -B build/check_day_matrix.py`
- `python -B build/check_matrix_tsn.py`
- `python -B build/check_matrix_bridge.py`
- `python -B build/check_intersection_detail_pdf.py`
- `python -B build/check_tsmis_pdf_reconcile.py`
- `python -B build/gen_release_notes.py v0.18.0 -o <tempfile>`

Expected/non-blocking check behavior observed:

- `python -B build/check_no_misspelling.py` fails only because it scans the untracked planning tree and finds the known `TM*SIS` (transposition, starred here to stay guard-clean) string in `P10-codex-review.md`; tracked content is clean except for the guard script's own explanatory docstring.
- `python -B build/gen_release_notes.py v0.18.0` without `-o` fails in this Windows console because CP1252 cannot encode Unicode arrows. The release workflow uses `-o notes.md`, which passed; CI workflows also set `PYTHONIOENCODING=utf-8` where relevant.

I did not rerun PyInstaller, `build/build.ps1`, destructive frozen self-tests, full release builds, live TSMIS access, credential/profile inspection, or push/tag/release operations.

## 5. Work-PC-only checks still owed

These are correctly deferred to the v0.18.1 field gate and should not block v0.18.0 release preparation:

- P8c live export/auth paths on the work PC: report selection, CDP open-on-demand/close, cancel-in-recover latency.
- Carried live validation for P1/P2/P3/P10/PA: partial-keeps-last-good on real refresh, Defender/lock behavior with disposable destinations, paused-batch resume, real v0.17 to v0.18 update, and both frozen variants/source ZIP on the work PC.
- Evidence-driven PDF/parser fixes against returned real PDFs.
- Intersection Detail (PDF) live export/consolidate/PDF-vs-TSN/PDF-vs-Excel/cross-env acceptance against real work-PC outputs.
- Explicitly separate hard deferrals: DPAPI/O2, runtime signing/certificate, and `compare_core` `min-cost-pairs`.

## 6. Non-blocking future recommendations

- Clarify future close-out measurement wording: from the recorded branch point `d2ee353..HEAD`, the non-planning diff is 150 files / +24,789 / -7,945; from `origin/main..HEAD`, it is 148 files / +22,946 / -8,589. Do not reuse the 148-file number as the branch-point diff.
- If release notes are previewed to stdout on Windows, run with UTF-8 output or use the workflow-style `-o` path. The shipped release automation path is already safe.
- Keep the deferred P11 source-comment drift cleanup out of release preparation unless a later maintenance phase touches those files anyway.

## 7. Whether the uncommitted close-out changes are approved for the final commit

Approved with scope clarification: there are no uncommitted product close-out changes to include in a final product commit. The only uncommitted files are planning artifacts under `docs/planning/`, including this review; they should remain untracked and out of the release commit unless the user explicitly asks to archive planning materials.
