# Prompt 04 — Implement One Hotfix Bundle

Before using, replace:

- `<BUNDLE_ID>` with the agreed **RB implementation-bundle ID**, for example
  `RB-1`. HF IDs are work-item specs and are not invoked separately.
- `<IMPLEMENTER>` with `Codex` or `Claude`.

---

You are <IMPLEMENTER> implementing exactly one agreed TSMIS comparison hotfix
bundle: `<BUNDLE_ID>`.

Repository:
`C:\Users\Yunus\Projects\TSMIS-Reports-Exporter`

Read:

1. `docs/planning/post-comparison-perfection-output-audit/START-HERE.md`
2. `docs/planning/post-comparison-perfection-output-audit/FINAL-FINDINGS-FOR-IMPLEMENTATION.md`
3. `docs/planning/post-comparison-perfection-output-audit/IMPLEMENTATION-PLAN.md`
4. `docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/README.md`
5. `docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/<BUNDLE_ID>/BUNDLE.md`
6. Any prior `IMPLEMENTATION.md` or `REVIEW.md` in that bundle directory.

If `<BUNDLE_ID>` was not replaced, the bundle is absent, its status is neither
`READY` nor `DENIED — RETURN TO IMPLEMENTATION`, a dependency is unmerged, or
its acceptance contract is incomplete, stop and report the blocker. Do not
infer a different bundle. A denied bundle is a Prompt 05 return: read its
`REVIEW.md` and resume the recorded branch rather than creating a new one.

Branch/worktree setup:

1. Fetch without force and verify `main` is clean and current.
2. Prefer a separate worktree so the user's normal app checkout remains
   available. Never switch or clean a dirty user worktree.
3. For a `READY` bundle, create the exact RB branch recorded in
   `IMPLEMENTATION-PLAN.md` (`hotfix/<rb-id>-<slug>`) from the latest `main`.
   For `DENIED — RETURN TO IMPLEMENTATION`, resume that existing branch at the
   reviewed head plus its denial record.
4. If the branch already exists, verify it belongs to this bundle and resume
   it rather than creating a duplicate.
5. Do not branch from another hotfix.
6. Before changing code, replace the pending base in
   `hotfix-bundles/<BUNDLE_ID>/BUNDLE.md` with the exact `main` SHA used to
   create the branch.

Implementation rules:

- Change only the agreed bundle scope.
- Preserve unrelated user changes.
- Do not opportunistically fix another finding, refactor unrelated code, bump
  a release, merge, or delete branches.
- If the verified root cause differs materially from the plan, stop before
  expanding scope. Document the discovery and return the bundle to Stage 3 for
  re-planning.
- Add or update tests that fail for the original defect and pass for the fix.
- Exercise the same public/production path an end user uses, not only internal
  helpers.
- Keep compatibility with already approved neighboring behavior.

Spend compute only where it proves something. Match the proof to what the
change can actually reach:

- The proof of a fix is a targeted probe through the SHIPPED entry point — red
  before, green after — plus a check that fails against the pre-fix code. Run
  that first; it is cheap and it is the real evidence.
- Re-run only the acceptance phases the change can move, and say which and
  why. A change confined to one layer does not require re-running phases it
  cannot reach; reuse the retained ones and re-prove the invariant instead
  (e.g. counts identical to base).
- **Never re-run compute so a record can cite a tidier commit.** Record the
  two heads and the reason. A verifier that refuses this should be taught the
  rule, with a negative case proving the rule still fails closed.
- Before any long re-run or long write-up, state in one line what a user would
  see differently. If the answer is "nothing", keep it to that one line.

Verification requirements — apply the ones the change can actually reach, and
record which you skipped and why:

1. Run the bundle's unit and integration tests.
2. Generate the exact affected comparisons from frozen or newly supplied
   acceptance inputs.
3. Recount source truth independently for affected discrepancy classes.
4. Verify values and formulas separately; recalculate formula workbooks with
   installed Excel when required by the bundle.
5. Inspect every affected user-facing workbook sheet and all bundle-specific
   presentation acceptance criteria.
6. Compare affected PDF and Excel report siblings when applicable.
7. Enforce evidence eligibility from semantic sources. For eligible PDF/PDF
   cells, verify binding and inspect every evidence image. For prohibited
   cells, prove the artifact set is absent.
8. Run the neighboring-family regression set named in the plan.

Documentation:

- Create or update
  `hotfix-bundles/<BUNDLE_ID>/IMPLEMENTATION.md`.
- Record implementer, branch, base SHA, commits, files changed, root cause
  confirmed, design, tests, generation commands, outputs, hashes/counts,
  acceptance results, known limitations, and rollback notes.
- Update the bundle status in `IMPLEMENTATION-PLAN.md` to
  `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`, not `APPROVED`.
- Retain generated comparisons and visual/evidence witnesses at the location
  specified by the plan.

Finish:

- Review the diff for scope leakage.
- Commit the implementation and documentation intentionally.
- Push the hotfix branch if the repository remote is available and unchanged.
- Do not merge to `main`.
- Do not delete the branch or worktree.

Report the branch, base and head SHAs, changed files, tests, generated output
root, acceptance results, unresolved risks, and the exact Prompt 05 invocation
for `<BUNDLE_ID>`.

---
