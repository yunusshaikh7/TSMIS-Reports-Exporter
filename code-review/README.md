# Code review — two-agent audit

This folder holds the audit prompt and (locally) the two agents' reports. The
audit is a **read-only** risk review of the whole repo — no fixes, no patches,
no running the app. See [AUDIT-PROMPT.md](AUDIT-PROMPT.md) for the full prompt.

## How to run

Run the SAME prompt on **both Claude and Codex**, and reconcile the two reports
afterward. The prompt is built for that: stable slug IDs, a shared severity
rubric, and quoted-code evidence so the reports diff cleanly.

**Run both LOCAL on this Windows machine — do not mix local + cloud.**
- A large slice of the audit is Windows-specific (Mark-of-the-Web /
  `Zone.Identifier`, SmartScreen, the PowerShell build scripts, WebView2/CLR,
  the unsigned `.exe`, the manifest). A Linux cloud container can only *read*
  those — it can't exercise them.
- This is a Caltrans app with a git-ignored credential file and internal URLs;
  keeping it on-machine matches the audit's own IT/DLP ethos.
- Both agents see the identical working tree, so report diffs reflect real
  analytical disagreement, not "did the cloud clone the same commit?"

Cloud-both is acceptable only if you want the machine free and accept that the
Windows-specific lenses become read-only reasoning. **Never run one local and
one cloud** — different OS / SHA / tooling breaks the reconciliation design.

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
