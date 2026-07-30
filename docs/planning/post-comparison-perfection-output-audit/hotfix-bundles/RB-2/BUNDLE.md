# `RB-2` — Bundle Contract

Status: **IMPLEMENTED — AWAITING ADVERSARIAL REVIEW** — the complete `RB2-A1`
acceptance run executed in one pass against one head; the mandatory split
trigger was NOT reached. The record, with every measured result, is
[IMPLEMENTATION.md](IMPLEMENTATION.md).

> This RB-level contract carries **HF-02 + HF-03** and transcribes both frozen
> work-item sections from
> [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md). The plan is
> authoritative; where this record and the plan disagree, the plan wins. The
> scope frozen below is unchanged; what has since happened against it is in
> [IMPLEMENTATION.md](IMPLEMENTATION.md).

| Field | Value |
|---|---|
| Bundle / work items | **RB-2 / HF-02 + HF-03** |
| Queue order | **2** |
| Theme | The deliverable looks right and describes itself truthfully — 56 of the 68 Stage 2 denials |
| Branch | `hotfix/rb-2-deliverable-presentation` |
| Readiness source `main` | `3dbd62daa0b3522c5338354b9d80304db8b771b0` — RB-1 merged, its post-merge record committed, and this state pushed to `origin/main` before readiness preparation |
| Base `main` commit | `896083e014d0451d5b05e5b6b024339aebc84d74` — the branch `hotfix/rb-2-deliverable-presentation` was created from this exact clean, current `main` (identical to `origin/main`) in worktree `C:\Users\Yunus\Projects\TSMIS-rb2-worktree` |
| Canonical finding IDs | **PCOA-FINAL-002, -003, -008, -009, -014, -016, -019** |
| Implementer | **Claude** (owner decision 2026-07-26) |
| First reviewer | **Codex** — independent non-implementer |
| Second reviewer | **Codex** — separate fresh review that challenges Review 1 and re-derives from source |
| Rush ship | **Eligible, not planned.** Only an explicit owner invocation activates the plan's rush-ship exception; it cannot waive this bundle's full acceptance run or mandatory split trigger |

## Bundle scope and completeness rule

RB-2 is the union of HF-02 and HF-03, with every criterion below controlling.
The allowed implementation surface is only the union named by those contracts:
`scripts/compare_core.py`, `scripts/summary_layout.py`,
`scripts/matrix_build.py` (`captured_tsn_workbook` only),
`scripts/compare_tsn_common.py` (provenance selection), and the required focused
checks/golden check. A change outside that union requires a return to planning;
it is not silently absorbed here.

The bundle may not exchange fewer reviews for sampled output. Counts, masks,
typed outcomes, Direct-lane behavior, evidence eligibility, and all Stage
2-validated presentation invariants remain unchanged except for the exact
presentation, self-description, canonical provenance, and temp-lifecycle
changes authorized below.

## One executable acceptance run — `RB2-A1`

Run `RB2-A1` once against one exact implementation head and record that head,
all frozen input identities, every output path/size/SHA-256, the commands or GUI
transactions, and the retained witness hashes. This is the union of the two
work-item paths, not a substitute for any criterion below:

1. Bind the new focused checks to the recorded pre-fix base and prove their
   exact defect signatures before accepting head-green results.
2. Through the shipped end-user paths, generate both twins for the classic
   current-vs-prior Ramp Summary, Intersection Summary, and Ramp Detail (PDF)
   cases; Direct-vs-TSN Ramp Summary and Intersection Summary controls; the
   merged RB-1 Clean Road pair; all 18 By Day and all 18 Everything vs-TSN
   matrix outputs; and one Direct-lane control per vs-TSN family. Overlapping
   matrix artifacts satisfy both scopes only when every HF-02 and HF-03 oracle
   is evaluated on them.
3. Force-rebuild the TSN library before the matrix generation, then exercise
   success, failure, and cancellation capture lifecycles. Retain the complete
   36-workbook classification, canonical-path/readability proof, and the
   zero-leftover-temp-directory ledger.
4. On the same output set, prove per-family semantic/state/count/typed-outcome
   invariance; run RC-1 with zero materially clipped cells; verify context
   labels and cached values headlines; prove all required TSN identity lines
   match Direct controls and no workbook/sidecar exposes `%TEMP%` or the false
   rebuild instruction.
5. Recalculate the required formulas twins in installed Excel, require every
   SELF-CHECK `OK` and zero cached error values, and retain the native-Excel
   summary/detail and identity/provenance renders required by both contracts.
6. Prove the evidence-artifact set is unchanged, run the complete named
   neighboring-family gates from both contracts, then run
   `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k` and
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\build\build.ps1 -SelfTest`.
7. Retain bulk output only under the HF-02/HF-03 scratch roots and small
   machine-readable witnesses only under `hotfix-bundles/HF-02/witness/` and
   `hotfix-bundles/HF-03/witness/`. Never write acceptance output into a Stage
   1/2 audit root.

## Mandatory split trigger

If the implementer or either reviewer cannot execute and review all of
`RB2-A1` in one pass, RB-2 returns to `BLOCKED`. The owner may then invoke the
already-defined split fallback branches
`hotfix/hf-02-workbook-presentation` and
`hotfix/hf-03-tsn-capture-provenance`. Sampling, partial output review, a
weakened oracle, or rush ship may not replace that split.

## Frozen work-item contracts — authoritative transcription

### HF-02 — Shared workbook presentation and self-description

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-02` / `workbook-presentation` |
| Split fallback branch | `hotfix/hf-02-workbook-presentation` |
| Priority / order | 2 |
| Depends on | Nothing (sequenced after HF-01 so its Clean Road witness covers the merged state) |
| Findings | **PCOA-FINAL-008** (P1), **-009** (P2), **-014** (P2), **-019** (P3) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to its own `statewide-summary-visible-text-clipping.json`, `large-detail-no-render-visual-adjudication.json` and native-Excel renders, plus the committed `stage2-measure-clipping.py` / `stage2-clipping-recheck.json` |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | **Inherits RB-2: IMPLEMENTED — AWAITING ADVERSARIAL REVIEW** |

**Exact scope.** Stored presentation and self-description of the generated
comparison workbook, **all families, both twins**: the `Comparison` category/key
column, the data sheets' key and back-link columns, `Spot Check`, `Summary`
labels, the *DIFFERENCES BY FIELD* rendering of wholly-context columns, and the
values twin's `Summary!B3` headline.

**Explicitly out of scope.** Any equality, normalization, pairing, count, or
mask change; the data columns (explicit width 13.0), the 45.75 pt wrapped header
row, hidden/veryHidden states, autofilter ranges and freeze panes — all Stage
2-validated clean and must stay byte-identical in behaviour; the `Notes` prose of
any family; evidence; the live `Summary!C56:C62` SELF-CHECK rows (deliberately
live and disclosed).

**Verified root cause.** Widths are hard-coded workbook facts in the shared
writer: `compare_core._write_comparison:2170` (`c_loc` = 12 → the measured 89 px
against labels needing up to 309 px), `_write_data_sheet:2015-2016` (key 14,
back 13), `_write_spot_check:2346-2348` (`B` = 19 → `Spot Check!B6` 55–76 px
short), `_write_summary:2998` (`B` = 46 → `Summary!B13:B14` 47–364 px short);
`summary_layout.py:634-635` for the by-category extra sheet. Separately,
`_write_summary` renders a wholly-context column's per-field count as a bare `0`
indistinguishable from a compared column with no differences (014), and writes
the `Summary!B3` headline as a formula with no cached value (019).

**Files expected to change.** `scripts/compare_core.py`,
`scripts/summary_layout.py`, and one new golden check.

**Planner design sketch (not binding).** Prefer wrapping + a widened column over
extreme widths — `Summary!B13`'s worst case needs ~691 px, which is an
instruction string, not an identity; the *identity* cells (`Comparison` category,
composite key, `Spot Check!B6`) should be widened to fit. For 014, render
`context` / `not compared` instead of `0` for a column that is context in its
entirety, leaving Highway Log's per-cell ditto columns reporting real counts. For
019 the low-risk path is the oracle's first branch on the **values** flavor only:
write `Summary!B3` as the computed literal (the values twin already writes
literals everywhere else), leaving the formulas twin live.

**Migration / compatibility.** Column widths and one label string are
presentation; no count, mask, schema version, or sidecar changes, so committed
comparison generations stay valid and `read_counts`' header-label lookup is
unaffected. Bytes move in every regenerated workbook — confirm no check asserts
byte-identity (only `check_compare_tsn_common.py:132` asserts a width, and it
asserts a *widened* column).

**Tests to add.** A new golden check that builds one summary-schema and one
detail-schema comparison in both flavors and applies RC-1's measurement rule —
real Calibri 11 metrics, Excel's width→pixel model, 6 px tolerance, reporting a
cell only when it cannot spill (no wrap, no shrink-to-fit, populated right
neighbour, merged ranges credited) — over `Summary`, `Spot Check`, `Comparison`
label and composite-key cells; plus assertions that a wholly-context column
renders non-numerically and that the values twin's `Summary!B3` is non-empty
`data_only=True`. Reuse `stage2-measure-clipping.py`'s documented gate so the
product check and the audit oracle cannot diverge.

**Exact end-user generation path.** Compare tab → classic current-vs-prior
environment for Ramp Summary, Intersection Summary and Ramp Detail (PDF); Direct
vs TSN for Ramp Summary and Intersection Summary; the Everything matrix for one
summary and one detail family; the merged HF-01 Clean Road pair. Both twins each.

**Source-truth recount.** None required — no count changes. **Prove** that: the
differing-cell and differing-row totals of every regenerated workbook are
identical to their pre-fix values, and every hidden state mask is cell-for-cell
identical.
That invariance *is* this bundle's source-truth assertion.

**Values / formulas and installed-Excel checks.** Both twins for every
regenerated family; installed-Excel recalculation with every SELF-CHECK row `OK`
and no error values; the formula twin's one-row offset (`B13:B14` → `B14:B15`)
handled explicitly.

**Workbook visual / presentation checks.** Native-Excel render of at least one
summary and one detail workbook: no two category rows share the same visible
text (the P1 harm in 008); `Spot Check` instructions, `Summary` labels and
composite keys legible in the default view without resizing; a re-run of the
RC-1 measurement reporting **zero** materially clipped cells against the 268
recorded in `stage2-clipping-recheck.json`.

**Evidence.** Not in scope; assert evidence artifacts are unchanged and that no
new artifact appears.

**Neighbouring-family regression.** Every family, because the writer is shared:
run the full gate plus `check_compare_audit.py`,
`check_compare_build_freshness.py`, `check_comparison_artifact_schema.py`,
`check_compare_equality_policy.py`, `check_compare_source_files.py`,
`check_matrix.py`, `check_day_matrix.py`, `check_baseline_matrix.py`,
`check_pdf_excel_matrix.py`, and the merged HF-01 Clean Road pair.

**Measurable acceptance criteria.**
1. RC-1's measurement reports **0** materially clipped cells in every
   regenerated workbook, both twins (was 268 across the five measured).
2. Native-Excel render confirms no category label is ambiguous — the
   `Ramp Type: C` / `Highway Group: R` collapse is gone.
3. Highway Sequence's `City`, `HG` and `Distance To Next Point` render as
   context/not-compared; Highway Log's ditto columns still report real counts.
4. Every values twin's `Summary!B3` is non-empty read `data_only=True` and
   matches the typed `ComparisonOutcome`.
5. All pre-existing counts, masks and typed outcomes unchanged, proved per
   family.
6. Full gate green; the new check fails pre-fix.

**Rollback.** Revert the merge commit; regenerate. No persisted artifact needs
migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-02\`
(regenerated workbooks + native-Excel PDFs);
`hotfix-bundles/HF-02/witness/` for the before/after clipping measurement JSON
and the per-family count-invariance table.

---

### HF-03 — vs-TSN capture identity, provenance and temp hygiene

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-03` / `tsn-capture-provenance` |
| Split fallback branch | `hotfix/hf-03-tsn-capture-provenance` |
| Priority / order | 3 |
| Depends on | Nothing |
| Findings | **PCOA-FINAL-002** (P1), **-003** (P2), **-016** (P3) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to `run-ledgers/tsn-library-rebuild.json`, `source-audit/all-completed-workflow-note-audit.json`, the committed `stage2-tsn-provenance-scope.json`, and Claude's `witness\temp_captures.txt` (readable since the firewall ended) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | **Inherits RB-2: IMPLEMENTED — AWAITING ADVERSARIAL REVIEW** |

**Exact scope.** The matrix lanes' private TSN capture step and what the
resulting workbooks say about their own TSN input: all 12 vs-TSN families × the
By Day and Everything lanes (36 workbooks), both twins, plus `%TEMP%` lifetime.

**Explicitly out of scope.** The Direct/classic lane (already clean — must stay
byte-identical); the TSN library's own normalization or identity determinism
(HF-08); the four comparators' `claims_notes` renderers (no change needed if the
sidecar is complete); the three families that expose no TSN identity by design
(Intersection Detail, Intersection Detail (PDF), Ramp Detail (PDF)) — they must
gain the honest provenance path but no invented identity line.

**Verified root cause.** `matrix_build.captured_tsn_workbook:227` copies the
normalized workbook into `tempfile.mkdtemp(prefix="tsmis-tsn-consumer-")`
(`:237`) and publishes a **reduced** 159-byte outcome sidecar beside it, dropping
`tsn_source_claims`, `tsn_normalization_version`, `tsn_raw_manifest`,
`tsn_normalized_workbook_identity` and `tsn_artifact_identity_token`. Claim
lookup is path-adjacent (`consolidation_meta.read_extra(tsn_path,
"tsn_source_claims")`), so on a matrix lane it always finds none and prints the
false "rebuild the TSN library" instruction (24 workbooks, at
`Summary by Category!A6`/`!A7`, `Notes!A9`, `Notes!A4`). The same captured path
becomes the user-facing provenance selection through
`compare_tsn_common.capture_input_provenance:604-625` (36 workbooks), and the
capture directory is not always removed.

**Files expected to change.** `scripts/matrix_build.py`
(`captured_tsn_workbook` only), `scripts/compare_tsn_common.py`
(provenance selection), plus checks.

**Planner design sketch (not binding).** Carry the library sidecar's full extra
payload onto the private copy (or bind claim lookup to the workbook's content
identity rather than its directory), and record provenance against the
**canonical library path** the capture was taken from while keeping the sha256 of
the bytes actually read. Make the capture directory removal unconditional across
success, failure and cancellation.

**Migration / compatibility.** The reduced sidecar must not lose any guarantee it
currently provides: the captured copy's identity validation
(`copied_identity != expected` → refuse; the private-path re-read) is the
integrity gate and must be preserved exactly. A comparison committed before this
bundle must still validate; a workbook produced after it must not claim an
identity it did not verify.

**Tests to add.** A hermetic check that a captured workbook carries the library
sidecar's claim fields; that a matrix-lane comparison's `Notes`/`Summary by
Category` prints the same TSN identity line as the Direct lane for all four
families that expose one; that no `Provenance` cell or `.provenance.json`
`selection` contains a `%TEMP%` path; and that zero `tsmis-tsn-consumer-*`
directories survive a success, a failure and a cancellation. Extend
`check_matrix_tsn.py` / `check_tsn_canonical_consumer_identity.py` rather than
adding a parallel harness.

**Exact end-user generation path.** Compare tab → **Rebuild the TSN library**
(`build_consolidated(force=True)`), then generate all 18 **By Day** and all 18
**Everything** vs-TSN workbooks from the matrix pages, and one Direct-lane
control per family from the classic Compare tab.

**Source-truth recount.** None (no counts change). Prove invariance of every
count and mask, and re-derive the 36-workbook classification independently by
both of RC-3's methods (zip/sheet-XML probe and an openpyxl cell walk) so the
before/after tables are directly comparable.

**Values / formulas and installed-Excel checks.** Both twins on at least one
family per identity class (identity-printing and identity-silent); installed
Excel recalculation clean.

**Workbook visual / presentation checks.** The identity line and the provenance
rows are readable in their stored widths on the merged HF-02 base; the false
instruction is gone from all 24 cells; the disclosed TSN vintage
(`2025-09` print vs `2026-07-23` pull) is visible to a reader.

**Evidence.** Assert unchanged: this bundle must not create, retire, or relabel
any evidence artifact.

**Neighbouring-family regression.** All vs-TSN families and all three lanes:
full gate plus `check_matrix_tsn.py`, `check_tsn_highway_log_claims.py`,
`check_tsn_canonical_consumer_identity.py`, `check_tsn_freshness.py`,
`check_tsn_outcome.py`, `check_matrix_cache_adversarial.py`,
`check_comparison_publication.py`, `check_artifact_store.py`.

**Measurable acceptance criteria.**
1. **Zero** occurrences of "rebuild the TSN library" across all 36 matrix-lane
   workbooks, both twins.
2. Every family whose Direct-lane workbook prints a TSN identity prints the
   **same** line on both matrix lanes.
3. No `Provenance` sheet and no `.provenance.json` names a `%TEMP%` path; every
   recorded TSN path exists and is readable after the run.
4. Zero `tsmis-tsn-consumer-*` directories remain after N runs including one
   cancellation and one failure.
5. Direct-lane workbooks unchanged; all counts, masks and typed outcomes
   unchanged everywhere.
6. Full gate green; the new assertions fail pre-fix.

**Rollback.** Revert the merge commit. Sidecar content is regenerated per run;
nothing persisted requires migration.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-03\`
(36+3 workbooks); `hotfix-bundles/HF-03/witness/` for the re-derived 36-workbook
classification and the temp-directory lifecycle log.

---

## Bundle-level dependencies and rollback

- Queue dependency: none; RB-1 is nevertheless merged at
  `560ea5e501fdd76003985753ba7fc9ff0a551320`, so the Clean Road witness in
  HF-02's acceptance run measures the merged state.
- Rollback: revert RB-2's future merge commit and regenerate. The exact HF-02
  and HF-03 rollback clauses below remain controlling.
- Readiness does not authorize Stage 4 inside this review closeout. Stage 4
  must fill the exact base SHA before changing code.

## Scope approval

| Planner / readiness check | Decision | Commit / date |
|---|---|---|
| Claude (first plan) | **APPROVED — FIRST PLAN** | `4e34bee` / 2026-07-26 |
| Codex (final challenge and exact transcription check) | **APPROVED — READY** | this readiness commit / 2026-07-28 |
