# Code review — two-agent audit

This folder holds the audit prompt and (locally) the two agents' reports. The
audit is a **read-only** risk review of the whole repo — no fixes, no patches,
no running the app. See [AUDIT-PROMPT.md](AUDIT-PROMPT.md) for the full prompt.

## How to run

Run the SAME prompt on **both Claude and Codex**, and reconcile the two reports
afterward. The prompt is built for that: stable slug IDs, a shared severity
rubric, and quoted-code evidence so the reports diff cleanly.

**Run both LOCAL on this personal Windows dev PC — do not mix local + cloud.**
(All development is done here on a personal Windows machine; the locked-down
*work* PC where the app is deployed can't run this audit at all.)
- A large slice of the audit is Windows-specific (Mark-of-the-Web /
  `Zone.Identifier`, SmartScreen, the PowerShell build scripts, WebView2/CLR,
  the unsigned `.exe`, the manifest). This Windows machine can read AND exercise
  Windows tooling against them; a Linux cloud container can only read.
- Both agents see the identical working tree, so report diffs reflect real
  analytical disagreement, not "did the cloud clone the same commit?"
- The repo already lives on GitHub and the auth file is git-ignored either way,
  so cloud-vs-local is **not** a data-sensitivity decision here — it's a
  Windows-fidelity + simplicity one.

Cloud-both is therefore also fine if you want the machine free; just keep both
agents identical and on the same SHA. **Never run one local and one cloud** —
different OS / SHA / tooling breaks the reconciliation design.

> Note: NO environment available for this audit — not this personal PC, not a
> cloud container — reproduces the managed *work* PC's Defender / DLP / corporate
> proxy / managed-Edge controls. Every IT/DLP/endpoint finding (lenses 7, 8) is
> reasoning-from-code, not an empirical test. The prompt treats them that way and
> asks what staging/emulation would be justified (lens 12); that unverifiable gap
> is itself worth surfacing in the reports.

## Same commit, both agents

Both agents pin the commit they audited by running `git rev-parse HEAD` and
recording the SHA at the top of their report. Confirm the tree is clean and on
the same SHA before starting:

```
git status --short --branch
git rev-parse HEAD
```

## Outputs

Each agent writes its report into this folder:
- `code-review/AUDIT-claude-<short-sha>.md`
- `code-review/AUDIT-codex-<short-sha>.md`

These output files are **git-ignored** (see the repo `.gitignore`) so a long
report full of quoted snippets and internal URLs never gets committed. The
prompt and this README are tracked; the per-agent reports are not. The distinct
filenames mean both agents can run in this same folder without clobbering each
other.

## Reconciling the two reports

Once both reports exist, paste one into the other agent's thread (or a third
session) and have it classify each overlapping finding as: Confirmed, Plausible
but unverified, Disagreed / needs proof, Duplicate, or New issue you missed —
matched by slug ID, weighing code evidence over prose.
