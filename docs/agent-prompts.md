# Reusable contributor prompts

These optional prompts work with any coding agent. Routine work follows the user's
task directly; a separate implementer/reviewer workflow is only for larger audits
when requested. Read [project-guide.md](project-guide.md) first; archived
assignments and old release plans do not override the current task. See also
[code-review-prompt.md](code-review-prompt.md) for a read-only audit.

## Roadmap curator

Use [roadmap-curator.md](roadmap-curator.md) for the full workflow. To start or
resume after a context reset:

```text
Maintain the TSMIS Reports Exporter roadmap. Read project-guide.md,
docs/roadmap-curator.md, and docs/roadmap.md. Reconcile the open inventory against
version.py, CHANGELOG.md, and the local Git history, then verify relevant claims
against the code. Mark shipped items complete and retain unresolved work with
its evidence and dependencies. Follow the user's existing Git instructions;
otherwise leave changes uncommitted. Summarize changes, then await new ideas.
```

## Implementer

```text
Implement the requested TSMIS Reports Exporter change.

Start with project-guide.md, docs/INDEX.md, and docs/roadmap.md. Read the owning topic
doc and docs/internals/ walkthrough for the subsystem you touch. Use the
current user request and open inventory to select scope; confirm an old finding
still exists before fixing it. Do not use an archived prompt's priorities or
historical canary counts as today's worklist.

Read the code and evidence, make a focused fix, and add or extend an appropriate
build/check_*.py or check_*.js regression guard for changed behavior. Use the
repository's configured Python 3.11 environment and build/run_checks.py for the
shared offline suite. Check discovery is automatic. Run checks proportional to
the change and report failures, skips, and environment limitations accurately.

Preserve the console-free core, thread-affine synchronous Playwright API,
transactional artifact publication, and Windows work-PC capability constraints.
Comparison semantic changes must follow the approved domain contract and be
proved against the independent oracle and both workbook flavors. Performance
changes must preserve output. Raw source facts override historical counts;
record and explain any deliberate canary re-binding.

For UI changes, serve scripts/ui locally and open /index.html#mock in an available
browser; docs/gui.md and docs/verification-and-testing.md describe the checks.
No assistant-specific preview tool or session configuration is required.
Live authentication and export acceptance require the work PC; do not claim
those passed based on offline checks.

Update the owning docs and the relevant roadmap item when behavior changes.
Keep credentials, source captures, real report data, and generated artifacts
out of Git. Follow project-guide.md's Git rules: branch before work on main, and
commit or push only when requested. Release changes need release scope from
the user; do not bump the version for routine documentation edits.

Finish with what changed, verification results, remaining risks, and any
specific acceptance steps requiring the owner or the work PC.
```
