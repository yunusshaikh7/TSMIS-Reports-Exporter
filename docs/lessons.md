# Lessons

The durable, cross-cutting wisdom of the TSMIS Reports Exporter: *why* the design
is shaped the way it is, and *how* we work. Read this to absorb the project's
hard-won judgment. Each lesson is told tersely; the mechanism it refers to is
owned by another doc — follow the link for the detail.

> Companion docs: the narrative is in [history.md](history.md) (the chapter
> story + "Three threads that run through all of it"); the authoritative
> "how it works" is [`../CLAUDE.md`](../CLAUDE.md).

---

## 1. The field keeps rewriting the design

The recurring pattern: a feature works on the dev PC and in CI, then a real
managed Caltrans work PC eats it. Three separate field failures each became a
*permanent* design constraint:

- **Managed Edge relaunches itself mid-login.** Org-managed Edge jumps into the
  work profile mid-Azure-AD sign-in, killing the Playwright window
  (`TargetClosedError` on `storage_state`). Five attempts were tried and reverted
  (compat-layer-relaunch flag, InPrivate, default-to-Chrome) before it was beaten
  three ways at once in v0.5.0–v0.6.0: persistent-profile Edge recapture, an
  unmanaged Built-in Chromium channel, and silent device sign-in. A later
  field failure (v0.10.3) added a fourth rule: *N concurrent Edge instances
  restoring one session time out*, so parallel work avoids managed Edge entirely.
  → [auth-and-signin.md](auth-and-signin.md).
- **Mark-of-the-Web crashes the CLR on download (v0.8.1).** Extracting a release
  zip without Unblock tags every `.dll` with a `Zone.Identifier` stream; .NET
  refuses to load tagged assemblies → instant "Failed to resolve
  Python.Runtime.Loader.Initialize". Only *downloaded* zips ever hit it — dev runs
  and CI never go through a downloaded zip. Fix: `gui_main._unblock_dotnet_assemblies()`
  strips the streams at startup before the CLR loads. → [gui.md](gui.md),
  [build-and-release.md](build-and-release.md).
- **PowerShell-blocked work PCs broke the updater (v0.10.1).** v0.9.0's updater
  ran a PowerShell swap helper from `%TEMP%`; locked-down PCs that block
  PowerShell for standard users killed it *silently* — the update downloaded and
  staged, the app closed, nothing installed. Fix: the staged exe applies itself by
  pure renames; no scripts, no cmd, no admin, and it fails loudly (stays open on
  the old version). → [it-and-security.md](it-and-security.md),
  [build-and-release.md](build-and-release.md).

**The meta-lesson:** the dev PC, CI runners, and the managed work PC are three
different worlds. The managed-PC security controls (Defender / DLP / corporate
proxy / managed Edge) exist on *neither* the personal dev PC nor any cloud
runner, so IT/DLP/endpoint behavior can only be *reasoned about from code*, never
empirically tested off the work PC. When designing anything that runs on the work
PC, assume it must work as a plain unsigned exe from a user-writable folder and
nothing more (see lesson 9).

## 2. Refactor toward one core

The shells were swappable *because* the engine stayed console-free. Everything
converges on a single core:

- **One `ReportSpec` loop** (`scripts/exporter.py`, `class ReportSpec` +
  `save_pdf_letter` / `save_via_export_button`) serves all six/seven report types;
  per-report differences (label, filename, `wait_js`, `is_empty`, `save`) live in
  the spec, the proven loop/recovery/skip/cancel logic lives once.
- **One `compare_core`** serves three comparison families (TSMIS-vs-TSN,
  PDF-sourced, cross-environment) via a schema-parameterized engine.
- **One registry** (`reports.py`: `EXPORT_REPORTS` / `CONSOLIDATE_REPORTS` /
  `COMPARE_REPORTS`) feeds both the GUI checkboxes and `export_multi`, so the
  lists can't drift.

Because the export engine never touches `print`/`input`/the window, the GUI was
torn out (Tkinter → WebView2, v0.8.0, 2,753 insertions) without changing the
engine underneath. **Rule:** core code reports via the `Events` sink and raises
exceptions; only `cli.py`/`gui_*.py` touch I/O; user-facing strings from the core
stay UI-neutral (no ".bat", no "this window", no "menu option N").
→ [architecture.md](architecture.md), [engine-and-reliability.md](engine-and-reliability.md).

## 3. Regression-lock discipline

`compare_core`'s text and formulas are **cell-for-cell locked** to the approved
Route-1 sample (values, formulas, styles, conditional formatting, calc mode). The
extraction-then-parameterize of the engine was regression-verified against the
pre-extraction output on real Route-1 + consolidated pairs *before* it shipped.
The discipline that follows: never change formula/label text in the core without
re-running such a check; new behavior is added through **opt-in** schema fields
(`header_comment`, `legend_writer`, `key_normalizer`, `ditto_nonasserting`, …)
so non-HL comparisons stay byte-identical. The approved Route-1 numbers are a
canary — when a refactor was claimed cosmetic, the lock proved it (Route-1 held
at 969 diff cells / 299 both / 87 one-sided through the column-label overhaul and
the ditto fix). → [comparison-engine.md](comparison-engine.md) owns the harness
and the golden checks.

## 4. Always consolidate from raw yourself

A pre-existing consolidated workbook is not trustworthy input. During the Highway
Log audit, a stale `inputs/tsmis_highway_log_consolidated.xlsx` was missing 25
routes and **inflated PDF-vs-Excel to 22,210 diffs**. Rebuilding the Excel side
from the 252 raw per-route `.xlsx` myself dropped it to **5,370 diff cells /
98.5% of rows fully identical, zero missing routes**. The rule: when verifying a
comparison, regenerate *every* side from the raw exports (via the consolidator's
`input_dir`/`out_path` overrides) into an organized workspace — never reuse a
handed-down "consolidated" file whose provenance and completeness you can't see.
→ [highway_log/comparison-study.md](highway_log/comparison-study.md).

## 5. Verify agent/AI claims against ground truth; Excel is not a clean oracle

Two distinct cautions, learned the same week:

- **Don't relay agent claims — re-verify them against the actual PDF/source.** A
  workflow agent claimed `parse_pdf` "undercounts ramp-types" on 9 dense routes; a
  deeper check cross-referenced an independent geometric word-position extraction
  across all 378 PDFs × 14 ramp types (5,292 values) → **0 mismatches**. The
  apparent shortfall was a *TSMIS source-data inconsistency* (the PDF's own Ramp
  Types breakdown sums short of its stated Total), correctly flagged RED by the
  `_audit_ok` column. Fudging it green would have *hidden* a real source issue.
  Likewise the two "parser_bug" flags on routes 041 and 046 in the PDF audit were
  confirmed to be the Excel's *dropped rows*, present and complete in the PDF.
- **Excel is buggy + drifts; do not treat it as the oracle.** The vendor TSMIS
  Excel Highway Log export drops rows and whole roadbed-column blocks, expands
  `+`/`++` ditto markers into values, pads Descriptions with trailing tabs, and
  mis-attributes descriptions to adjacent rows — *that bug is the whole reason the
  PDF consolidator exists*. It also drifts across snapshots (route-5 PDF Jun17-18
  vs Excel Jun15). Two corollaries that bit us: a naive openpyxl reader sees the
  `HYPERLINK` row-link columns as blank (Excel caches no numeric result) — they're
  correct in real Excel, COM-verify don't flag them; and a "<text> ≠ <text>␉␉␉"
  diff is cosmetic trailing tabs, not a content difference (`_xl_trim`/Excel TRIM
  strip spaces, not tabs). → [highway_log/columns.md](highway_log/columns.md),
  [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md).

## 6. Be honest about dead ends

The reverts aren't hidden. The login wars (Chapter 4) tried five Edge approaches,
reverted four of them in a cluster on June 5, parked the problem as a documented
known issue, and beat it properly a week later — and the `✅ RESOLVED (v0.5.0)`
block in CLAUDE.md still records *what didn't help* (removing mid-login polling,
`--edge-skip-compat-layer-relaunch`, InPrivate; v0.4.2's "default to Chrome"
regressed Chrome too and was rolled back). The short-lived "dev update channel"
(v0.10.2–v0.10.3) is likewise recorded as removed, *with the ordering bug that is
why it never worked* — so it isn't casually resurrected. **Document the dead end
and its cause; a known-bad path you can't see is a path someone re-walks.**
→ [history.md](history.md).

## 7. Audit methodology

How code is reviewed here (it is read-only, source-backed, and re-verified):

- **Multi-agent fan-out + lead re-verification.** The v0.10.4 audit ran a
  7-domain subagent fan-out, then the lead re-verified every headline finding
  *against the actual code* (not just the subagent's assertion) before recording
  it. Notable *good* designs were noted too, so reviewers don't re-flag them.
- **Source-backed verification against the local website source.** The live TSMIS
  SPA source is kept locally (Caltrans-internal, never committed) and is the
  ground truth for any selector / label / empty-marker / `CONFIG` question. A
  source pass *downgraded* the two scariest security findings (the token-in-log P0
  → ~P2/P3 once `history.replaceState` was confirmed to clear the hash on load;
  wrong-env-silent-success P1 → P3) and *surfaced two functional bugs the audit
  couldn't see* (the wrong Intersection-Detail empty marker). Refer to the source
  before guessing site behavior.
- **Per-finding stable slug IDs.** Findings carry slug IDs
  (`AUTH-TOKEN-IN-LOG-BUNDLE`, `UPDATER-NO-SIGNATURE-VERIFY`,
  `SHEET-FORMULA-INJECTION`, `COMPARE-SKIPPED-FILES-MATCH`, …) so a Claude audit
  and a parallel Codex run can be reconciled finding-by-finding, and so the
  next-patch plan can track each to a fix.

The reusable, generalized audit prompt is
[code-review-prompt.md](code-review-prompt.md) — and the per-run scratch reports
live under `/code-review/` (git-ignored local audit area; the working docs were
retired into [roadmap.md](roadmap.md) once their fixes shipped).

## 8. Two-agent parallel work on a shared branch

The v0.11.0 next-patch was implemented by **two agents in parallel**. The
intended separate worktrees were never created — both ran in the *one* main
working tree on a *shared* branch `next-patch-og`. It worked because of a strict
**ownership split**: Agent 2 owned all comparison/consolidator files
(`compare_*`, `consolidate_*`, `build/check_compare_*`, the `COMPARE_REPORTS`
block of `reports.py`); Agent 1 owned everything else. The one live risk on a
shared branch is a `git add -A` sweeping the other agent's WIP into a commit, so
the discipline is: **review the diff at finish-up** — confirm every commit's
files match its scope before merging. (At merge: no cross-scope contamination,
all golden checks green, then a fast-forward to main.) Neither agent edited the
close-out files (CLAUDE.md / version.py / README / UI mock / CHANGELOG) —
those are done once, at close-out, by the integrator.

## 9. Work-PC reality shapes every shippable feature

The real users run on locked-down Caltrans work PCs: **no PowerShell at all for
standard users, no cmd guarantees, no admin rights, no scheduled tasks, no
elevation.** The only proven capability is "unsigned exes run from user-writable
folders" — which is how the app itself runs. Any feature that must execute *on*
the work PC (updates, helpers, anything) must work within exactly that envelope.
The dev PC is the user's *personal* Windows machine (all coding/audits/tooling
run there, unrestricted) but it **cannot reach the TSMIS intranet host**, so
live-site verification only ever happens on the work PC — which is why many
features ship "implemented + golden-checked, live-export verification pending."
When a problem report comes in, first confirm *which* machine it's on; "works on
my machine" usually means the work PC ate it. → [it-and-security.md](it-and-security.md).

---

### Quick index of the lessons

| # | Lesson | Owns the detail |
|---|---|---|
| 1 | The field keeps rewriting the design | auth-and-signin / gui / build-and-release / it-and-security |
| 2 | Refactor toward one core | architecture / engine-and-reliability |
| 3 | Regression-lock discipline | comparison-engine |
| 4 | Always consolidate from raw yourself | highway_log/comparison-study |
| 5 | Verify agent claims; Excel is not a clean oracle | highway_log/columns + pdf-and-tsn-parsing |
| 6 | Be honest about dead ends | history |
| 7 | Audit methodology | code-review-prompt |
| 8 | Two-agent parallel work on a shared branch | — (this doc) |
| 9 | Work-PC reality shapes every feature | it-and-security |
