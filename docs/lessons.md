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

## 10. A hidden input with no positioned parent escapes its clip

The styled checkbox/radio pattern hides the real `<input>` with `position:absolute`
(kept focusable for a11y). An absolute element resolves against its nearest
*positioned* ancestor — and if it has none, against the viewport, **escaping the
`overflow:hidden` clip on `.app`/`.main`/`.col-*` and inflating
`documentElement.scrollHeight`**. The whole page then scrolls down into a blank
area below the UI. This bit twice: first the v0.13.0 toggles (`.option-row` /
`.fast-toggle`, fixed in v0.13.x), then the v0.16/0.17 matrix-options toggles
(`.mc-fast`, fixed in v0.17.1) — each time because a *new* label class wrapped a
hidden input but was left off the containing-block list. **Rule: every label
class that wraps a hidden input MUST be in the `position:relative` list** beside
the sr-only rule in `app.css`. No pure-Python check can catch this (it needs a
laid-out DOM), so the inline CSS comment carries the warning; verify in the
`#mock` by checking `scrollHeight === innerHeight` on a matrix tab.
→ [gui.md](gui.md).

---

## 11. Read a form's state by its stable id, never its visible label

The site is migrating `#customReport` from a flat list to a grouped fly-out where a
leaf *displays* a short label — "Detail", not "Highway Detail". v0.18.1 learned this
for **selecting** a report (match the `data-value`, not the text). v0.19.3 learned it
again for **reading** the selection: the per-route stale-form guard
(`_ensure_report_armed`) compared the visible `.cs-value` to the full `spec.label`, so
the moment Highway Detail moved into the grouped menu the guard saw "Detail" ≠ "Highway
Detail" and re-selected on **every** route — correct exports, but log spam and ~250
needless re-selects per run. The two sites even *render* the leaf differently (prod
writes `opt.textContent`, dev writes `opt.dataset.label`), so the visible text is not a
reliable identity anywhere. **Rule: any check on "which report/option is active" reads
the stable id** — the hidden `<select id="reportSelect">`'s `data-value` via
`current_report_value` — **and treats the visible label as a last-resort fallback.**
This class of bug (visible text ≠ stable identity) is invisible until a report enters
the grouped menu, which is exactly where the whole catalog is heading — so audit every
`.cs-value`/label-text read the same way. → [engine-and-reliability.md](engine-and-reliability.md).

## 12. Invisible bytes break real gates — keep the toolchain ASCII-safe

Three failures in one day (v0.21.0), all caused by bytes no diff review shows:

- **A PowerShell 5.1 `Set-Content -Encoding utf8` rewrite of `mock.js`** added a UTF-8
  **BOM** and re-flowed line endings; the mock↔bridge **parity check failed** on a file
  whose *content* was "identical". Rule: never bulk-rewrite tracked text via PS 5.1
  cmdlets — use surgical edits, and when a file is mangled, `git checkout --` it and
  redo the edits properly.
- **An em-dash in a `.ps1` string** killed the build: PowerShell 5.1 parses BOM-less
  files as **ANSI**, so a UTF-8 dash decodes as `Ã¢â‚¬â€` mid-string and the *parser*
  errors (the failure names a token, not an encoding). Rule: `.ps1` edits are
  ASCII-only.
- **The OG card shipped with an empty app window for two releases** because Chromium
  silently blocks `file://` images on a `set_content` (about:blank-origin) page — the
  only symptom was a 16px broken-image glyph nobody looked at. Rule: a generator whose
  whole point is an embedded artifact must **assert the artifact decoded**
  (`img.naturalWidth > 0`), not just that the render "completed".

The common thread: these failures pass every eyeball review and fail only at a machine
boundary — so encode the boundary's rule where it runs (ASCII in `.ps1`, an assertion in
the generator) instead of relying on memory. → [build-and-release.md](build-and-release.md),
`tools/screenshots.py`.

## 13. Upstream reshaped a report: census first, then refuse the old format

The July-2026 site update reshaped Intersection Detail (v0.22.0) — the first time an
already-integrated report changed format underneath the app. Two rules made the
re-baseline fast and safe:

- **Measure before rewriting.** Before touching the comparator, a statewide *census*
  diffed the new exports against TSN field-by-field (per-column diff rates + date-delta
  distributions). That one table decided everything downstream with evidence instead of
  judgment: which normalizations were dead (the ~1-day offset: zero occurrences left),
  which Notes were stale (Date of Record now 99.94% matched), the new soft/hard Major
  classification, and roughly where the new canary would land (~21.7k). The same method
  proved the new PDF parser *before it was written* — a scratch mapping run cell-for-cell
  against the same-run Excels (576k cells, 0 real diffs). Never re-baseline a
  regression-locked comparison on reasoning alone when the ground truth can be measured
  in minutes.
- **Refuse retired formats loudly; don't dual-support.** Reading a pre-update workbook by
  the new positions would silently mis-map every column from Description on — the worst
  failure class this project has (plausible wrong numbers). So the comparator gained a
  cheap header gate and the PDF parser a shape discriminator (padded vs unpadded
  postmiles), each erroring with a "re-export" hint. Dual-format support was considered
  and rejected: the old format can never be exported again, so its only future is a stale
  store the user should refresh — an actionable refusal beats a silently wrong
  comparison, and costs ~10 lines instead of a parallel position map. The v0.23.0
  on-demand evidence action applies the same principle as a *freshness gate*: when a
  derived artifact can't be proven to belong to its inputs, decline and say why.

→ [tsn-parsers.md](tsn-parsers.md) (the Intersection Detail update block),
[comparison-engine.md](comparison-engine.md) §9f + §13. The census scripts + expected
numbers are preserved (local-only) in the 7.8 bundle's `_verification-scripts/`.

---

## 14. A green suite that never runs the failing path is not information

The v0.27.0 field failure was a path 265 characters long — a *name* too long, at an
install depth the dev box never had, on a managed PC whose `LongPathsEnabled` is 0 and
cannot be changed. Every check passed throughout, because the only check that could
have caught it tested long paths **"when policy permits"** — and on the dev box policy
always permitted. The machine that runs the tests silently satisfied the precondition
the field violates.

**The rule:** when a check is conditional on an environment property, the condition is
part of the test's coverage, not a detail. Either make the gate unconditional (compute
the failure arithmetically, or shim the OS to refuse), or state plainly that the
property is untested. Both gates are unconditional now, and both were red on the old
code for exactly the field failure.

**The corollary, which cost three field bugs in one day:** drive the SHIPPED entry
point, assert the FILE, reproduce at the real environment's shape, prefer
rebuild-over-existing to first-build. When the field disagrees with the suite, the
suite is wrong.

→ CMP-AUD-242 in the finding ledger; `check_comparison_path_limits`. The work-PC
evidence bundle now reports the long-path policy and a full path-length census, so the
next instance of this class is one file away instead of one field report away.

---

## 15. Build guards, not more careful code — they catch what you write next

Two findings, one week apart, made the same argument from opposite ends.

**Evidence was grading its own homework.** The feature that renders "proof" images for
a comparison worked by re-running the loaders and re-deriving the differences. A
reading mistake therefore appeared identically in the comparison and in its evidence,
and the two agreed — which looked like corroboration and was actually the same
computation twice. Measured statewide on Highway Sequence, that path had been silently
dropping **1,169 of 5,589 real differences (20.9%)**, all at repeated postmiles: an
entire class invisible precisely because it was the class hardest to photograph. The
fix made the published comparison the authority — evidence decodes and authenticates
the workbook's own per-cell state masks, and the loaders only *propose* a row.

**Then that guard caught the next bug.** While proving a later feature, the engine
reported one column's difference from a neighbouring column's cell — a hardcoded copy
of a header shifting every field index under a wider schema. Nothing wrong was
published: the published-cell check refused all 766 candidates because the text
disagreed. A guard written in one marathon caught a defect written in the next.

**The rule:** when two things must agree, do not compute them the same way twice —
make one authoritative and have the other prove itself against it. And treat "0 results"
from a verification path as a question, not a pass; that refusal WAS the bug report.

→ CMP-AUD-208/209/108 and the M-C batch in the finding ledger;
[comparison-engine.md](comparison-engine.md) §13.


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
| 10 | A hidden input with no positioned parent escapes its clip | gui |
| 11 | Read a form's state by its stable id, never its visible label | engine-and-reliability |
| 12 | Invisible bytes break real gates — keep the toolchain ASCII-safe | build-and-release + tools/screenshots.py |
| 13 | Upstream format change: census first, then refuse the old format | tsn-parsers + comparison-engine §9f/§13 |
| 14 | A green suite that never runs the failing path is not information | it-and-security + build-and-release |
| 15 | Build guards, not more careful code — they catch what you write next | comparison-engine §13 |
