# `RB-3` — Bundle Contract

Status: **IMPLEMENTED — AWAITING ADVERSARIAL REVIEW** (implementation
`c9b55b6` on `hotfix/rb-3-ramp-detail-layout`; see
[IMPLEMENTATION.md](IMPLEMENTATION.md))

> This RB-level contract carries work item **HF-04** and transcribes the frozen
> work-item section from
> [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md). The plan is
> authoritative; where this record and the plan disagree, the plan wins. The
> readiness step freezes scope only. No RB-3 branch, implementation, generation,
> recalculation, or acceptance run has started.

| Field | Value |
|---|---|
| Bundle / work items | **RB-3 / HF-04** |
| Queue order | **3** |
| Theme | Ramp Detail layout compatibility and same-source null parity — restores nine comparison placements that produce nothing today |
| Branch | `hotfix/rb-3-ramp-detail-layout` |
| Readiness source `main` | `4c199d3feb209832076e43af6a7caa34a8da0c1b` — RB-2 merged, its post-merge checks passed, its merge record was committed, and this state was pushed to `origin/main` before readiness preparation |
| Base `main` commit | `194b7ee8da095f0300e7e635bb7e7af78643b685` — v0.33.1; verified clean and identical to `origin/main` before `hotfix/rb-3-ramp-detail-layout` was created from it (Stage 4, 2026-08-02) |
| Canonical finding IDs | **PCOA-FINAL-001, -012** |
| Implementer | **Claude** (owner decision 2026-07-26) |
| First reviewer | **Codex** — independent non-implementer; holds `ramp-detail-pdf-excel-sibling-parity.json` and the header-census run ledgers |
| Second reviewer | **Codex** — separate fresh review that challenges Review 1 and re-derives from source |
| Rush ship | **Eligible, not planned.** Only an explicit owner invocation activates the plan's rush-ship exception; it cannot waive the full gate, acceptance run, or two-review merge gate |

## Bundle scope and completeness rule

RB-3 is exactly HF-04, with every criterion below controlling. The allowed
implementation surface is only `scripts/compare_ramp_detail_tsn.py`, the Ramp
Detail header path in `scripts/compare_env.py`,
`scripts/consolidate_ramp_detail.py`, `scripts/compare_ramp_detail_pdf.py`, and
the focused checks named below. A change outside that union requires a return
to planning; it is not silently absorbed here.

The dual-layout compatibility decision is binding: both censused layouts and a
mixed old/new pair must compare. Accurate refusal is reserved for a third,
unknown layout and cannot substitute for restoring the nine blocked placements.
Counts, evidence eligibility, neighboring-family behavior, and every merged
RB-1/RB-2 guarantee remain unchanged except for the exact HF-04 behavior below.

## One executable acceptance run — `RB3-A1`

Run `RB3-A1` once against one exact implementation head and record that head,
all frozen input identities, every output path/size/SHA-256, the shipped commands
or GUI transactions, installed-Excel results, and retained witness hashes:

1. Bind every new focused assertion to the recorded pre-fix base, require its
   exact defect signature there, and require it green at the acceptance head.
2. Through the exact end-user paths below, consolidate both Ramp Detail editions
   from the frozen 2026-07-23 folder and generate both twins for all eight
   topology decisions plus the by-day PDF-vs-Excel placement.
3. Recount route 001 row 2 field-for-field against raw, independently recount
   the new Excel-side comparisons without the app, and prove all 15,213
   self-check rows pair with zero missing keys and zero differing cells.
4. Recalculate the formulas twins in installed Excel; require clean SELF-CHECKs,
   unchanged RD-PDF-vs-TSN counts, correct 11-column presentation, and readable
   merged-HF-02 geometry on every newly opened path.
5. Prove zero prohibited evidence artifacts, preserve Direct/neighbor behavior,
   run every named neighboring-family check, then run the complete gate and
   frozen application self-test.
6. Retain one bound result set covering both accepted historical layouts, the
   mixed pair, the accurately refused unknown layout, consolidator completion
   truth, raw field mapping, visual checks, twin parity, counts, and failures.

---

## HF-04 — Ramp Detail layout compatibility and same-source null parity

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-04` / `ramp-detail-layout` |
| Split fallback branch | `hotfix/hf-04-ramp-detail-layout` |
| Priority / order | 4 |
| Depends on | Nothing |
| Findings | **PCOA-FINAL-001** (P1), **-012** (P2, latent) |
| Implementer | Claude |
| Review 1 | **Codex** (holds `ramp-detail-pdf-excel-sibling-parity.json` and the header-census run ledgers) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | **Inherits RB-3: READY** |

**Exact scope.** Ramp Detail, both editions: the 8 topology decisions the Excel
edition currently cannot produce (classic env, Direct/By Day/Everything vs TSN,
Baseline, Everything ENV, Direct self, Everything SELF), the ninth
PDF-vs-Excel by-day placement, the consolidator's completion truth, and the self
check's null-token symmetry.

**Explicitly out of scope.** Any other family's header contract; the PDF
edition's existing vs-TSN comparison counts; the 2-cell RD-PDF representation
class (HF-09); `compare_env.compare_folders`' missing-side preflight (HF-07);
assuming the permanent site matches the development site — the scope document
forbids it, so the fix must accept **both** layouts rather than replacing one
pinned layout with another.

**Verified root cause.** The 2026-07-23 dev-site Excel export changed shape (blank
labels removed; the print-only `OF` and `TY` columns added; values **moved**, not
merely relabelled). `compare_ramp_detail_tsn._TSMIS_HEADER` /
`compare_env._ramp_detail_canonical_header` pin exactly one layout, so refusal is
correct — but (a) `consolidate_ramp_detail.consolidate` still reports 126/126
`status=ok` for a workbook no comparator accepts, and (b) the refusal message
names a "leading 'Route' column" the workbook has, prescribing an action that
reproduces the identical failure. Separately, the self comparator projects
`-` / `NO RAMP LINEAR EVENT` to blank on the PDF leg (`_null_blank:76`) but not
on the Excel leg (`_load_excel_collapsed:155`), so once the gate opens the same
source token renders differently on the two legs of a same-source check: 108
cells / 36 rows (36 `Area 4`, 36 `OF`, 36 `Description`).

**Files expected to change.** `scripts/compare_ramp_detail_tsn.py`,
`scripts/compare_env.py` (RD header only), `scripts/consolidate_ramp_detail.py`,
`scripts/compare_ramp_detail_pdf.py`, plus checks.

**Planner design sketch (not binding).** Accept both censused layouts by
**name-keyed** field resolution rather than position, refusing anything that is
neither; make the consolidator's completion agree with downstream consumability
(a workbook no comparator accepts must not report `ok`); rewrite the refusal
message to name `exact_consolidated_header_ok` semantics and an action that can
succeed, following the sibling wording precedents (Intersection Detail names "the
current (July 2026) site format"; Highway Detail names "the exact 34-column
export header"); and apply the existing null projection symmetrically on the
Excel leg of the self check.

**Migration / compatibility.** Both the 2026-07-09 and 2026-07-23 layouts must
compare, and a mixed pair (old prior vs new current) must compare correctly —
cross-environment and Baseline routinely pair two different days. Only a third,
uncensused/unknown layout may refuse, with an accurate message and workable
action. A consolidated workbook produced by the current code must not become
unreadable.

**Tests to add.** Extend `check_compare_ramp_detail.py`,
`check_compare_ramp_detail_tsn.py`, `check_compare_ramp_detail_pdf.py`: both
header layouts accepted with `OF`/`TY`/`Description` mapped correctly; a
third, unknown layout refused with a message naming the real gate; the
consolidator's completion downgraded when its output is not consumable; and a
same-source self check over rows carrying `-` / `NO RAMP LINEAR EVENT` on both
sides reporting **zero** differences.

**Exact end-user generation path.** Consolidate tab → Ramp Detail (both
editions) from the frozen `2026-07-23` run folder; then Compare tab → classic env
(2026-07-09 vs 2026-07-23), Direct vs TSN, the PDF-vs-Excel self check, the By
Day and Everything vs-TSN matrices, Baseline, Everything ENV, and the
PDF-vs-Excel by-day matrix.

**Source-truth recount.** Route 001 row 2 field-for-field against the raw export
(the finding's exact witness); an independent app-free recount of the newly
produced Excel-side comparisons; and confirmation that all 15,213 self-check rows
pair with zero missing keys.

**Values / formulas and installed-Excel checks.** All 8 decisions produce both
twins; the formulas twins recalculate clean; the RD-PDF vs TSN counts are
unchanged from pre-fix.

**Workbook visual / presentation checks.** On the merged HF-02 base: the new
Excel-side workbooks' `Summary`, `Spot Check`, `Comparison` and composite keys
are legible; the 11-column header renders correctly; `OF`/`TY` are labelled, not
positional.

**Evidence.** RD-PDF vs TSN and RD self are `PROHIBITED` under the audit rule and
currently produce nothing on the newly opened paths — **prove zero artifacts**
appear as a side effect of unblocking the comparison, and re-observe HF-05's rule
if HF-05 has already merged.

**Neighbouring-family regression.** Intersection Detail (the sibling that already
absorbed a site format change) and Highway Detail (whose header contract shares
the pattern, and which is **pre-release — do not touch**): full gate plus
`check_compare_intersection_detail_tsn.py`,
`check_compare_consolidated_layout.py`, `check_compare_env_*` and
`check_pdf_excel_matrix.py`.

**Measurable acceptance criteria.**
1. All 8 topology decisions plus the by-day PDF-vs-Excel placement produce both
   twins from the frozen 2026-07-23 input. The plan has selected the
   dual-layout-compatibility branch of the finding's oracle; accurate refusal is
   reserved for a third unknown layout and does not satisfy this criterion.
2. `OF`, `TY` and `Description` proved correct on route 001 row 2 against raw.
3. The consolidator no longer reports `ok` for output no comparator accepts.
4. The Ramp Detail self check reports **zero** differing cells across all 15,213
   rows.
5. The 2026-07-09 layout still compares; an unknown layout still refuses.
6. RD-PDF vs TSN counts unchanged.
7. Full gate green; every new assertion fails pre-fix.

**Rollback.** Revert the merge commit; the previous behaviour (refusal) returns
without data loss. Consolidated workbooks on disk stay readable either way.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-04\`;
`hotfix-bundles/HF-04/witness/` for the two-layout header census, the route-001
row-2 field trace and the self-check zero proof.

---

## Bundle-level dependencies and rollback

- Queue dependency: none. RB-1 and RB-2 are merged; RB-2 merge
  `d679f388e0b12ff595751af9edd816674615b7a5` supplies the presentation base
  explicitly required by HF-04.
- Rollback: revert RB-3's future merge commit. The exact HF-04 rollback clause
  above remains controlling.
- Readiness does not authorize Stage 4 inside this review closeout. Stage 4
  must fill the exact base SHA before changing code.

## Scope approval

| Planner / readiness check | Decision | Commit / date |
|---|---|---|
| Claude (first plan) | **APPROVED — FIRST PLAN** | `4e34bee` / 2026-07-26 |
| Codex (final challenge and exact transcription check) | **APPROVED — READY** | this readiness commit / 2026-08-02 |
