# `RB-5` — Bundle Contract

Status: **DENIED — RETURN TO IMPLEMENTATION**

> This RB-level contract carries work items **HF-06 and HF-09** and transcribes
> both complete frozen work-item sections from
> [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md). The plan is
> authoritative; where this record and the plan disagree, the plan wins.
> Original readiness froze scope only. Implementation exists; Codex Review 1
> returned `RB5-R1-EG-001`; see [REVIEW.md](REVIEW.md). Scope is unchanged.

| Field | Value |
|---|---|
| Bundle / work items | **RB-5 / HF-06 + HF-09** |
| Queue order | **5** |
| Theme | Difference classification — normalize the ruled Highway Sequence self-equation class while disclosing, but never suppressing, the ruled representation-only class |
| Branch | `hotfix/rb-5-difference-classification` |
| Readiness source `main` | `1e9446bb7f1f9771b7698482d63980840ee5ec28` — RB-4 merged as `83a24896a5a970a3686df87934210f54cea43778`, its 158/158 post-merge gate and frozen application self-test passed, and its merge closeout was committed before this readiness preparation |
| Base `main` commit | **`87e368c3e9a7eaf26395308e8ddea4aba7d303e5`** — fetched 2026-08-30; `main` verified clean and identical to `origin/main` (the `v0.41.2` roadmap closeout). `hotfix/rb-5-difference-classification` was created from it in worktree `C:\Users\Yunus\Projects\wt-rb5`, with a second DETACHED pre-fix worktree at the same SHA (`C:\Users\Yunus\Projects\wt-rb5-base`) supplying the base leg of every before/after measurement. The user's own checkout was never switched or cleaned. |
| Canonical finding IDs | **PCOA-FINAL-011, -013** |
| Implementer | **Claude** (owner decision 2026-07-26) |
| First reviewer | **Codex** — independent non-implementer; owns the 60,254-row equation witness, route-001 adjudication, and four semantic-classification witnesses |
| Second reviewer | **Codex** — separate fresh review that challenges Review 1 and independently re-derives bounded source cases |
| Rush ship | **Eligible, not planned.** Only an explicit owner invocation activates the exception; it cannot waive the full gate, combined acceptance run, source recounts, or two-review merge gate |

## Post-readiness `main` advance — 2026-08-10

The readiness source above is no longer the tip of `main`. Two independent
releases landed afterward: `v0.34.0` (`63a56a0`) and `v0.35.0` (`800bea2`).
`v0.35.0` deliberately changed Highway Sequence **vs-TSN** so `HG`, `City`, and
`Distance To Next Point` are asserted rather than context-only, and updated that
comparator's Notes and focused checks. It did not implement HF-06 or HF-09 and
did not start `RB5-A1`.

Stage 4 therefore must:

1. branch from and record the latest clean pushed `main` (at least `800bea2`),
   never the older readiness source;
2. treat the `v0.35.0` Highway Sequence vs-TSN semantics as an owner-directed
   pre-existing baseline and neither revert nor reclassify them under RB-5;
3. interpret every "Highway Sequence vs-TSN counts unchanged" criterion as an
   exact comparison between the recorded Stage-4 base and the RB-5 acceptance
   head; and
4. bind the required pre-fix signatures and witnesses to that recorded base.

The readiness source remains useful provenance for the frozen scope. It is not
an allowed acceptance baseline after `main` advanced.

## Bundle scope and completeness rule

RB-5 is exactly the union of HF-06 and HF-09 below. Every scope statement,
test, generation path, recount, installed-Excel check, retained witness, and
measurable criterion in both sections controls. The two owner rulings point in
opposite directions and must remain visibly separate:

- HF-06 normalizes only the Highway Sequence PDF-vs-Excel self-equation
  relation, moving its published count from 3,714 cells to zero.
- HF-09 is disclosure only: every representation-only cell remains flagged and
  every affected headline count remains numerically unchanged.

A shared hook is allowed only when both uses are explicit opt-ins and the
anti-suppression/count-invariance tests prove they cannot bleed into each other
or into an unrelated family. Any change that normalizes an HF-09 cell, changes
Highway Sequence vs-TSN counts, or broadens equality outside HF-06 returns the
bundle to planning.

The allowed implementation surface is the union named below:
`scripts/compare_highway_sequence_pdf.py`; an opt-in field/rendering hook in
`scripts/compare_core.py` only if needed; the five HF-09 family comparators;
and focused checks/acceptance tooling. A change outside that union requires an
explicit scope explanation and reviewer challenge; it is not silently absorbed.

## One executable acceptance run — `RB5-A1`

Run one combined `RB5-A1` against one exact implementation head. Stage 4 may
add a focused driver under the allowed checks/acceptance-tooling surface. The
retained result must bind the exact base/head, frozen inputs, command or GUI
transactions, output paths/sizes/SHA-256 values, installed-Excel outcomes,
full-gate logs, and committed HF-06/HF-09 witnesses.

The single run must:

1. Bind every new assertion to the exact pre-fix base, require the precise
   HF-06/HF-09 defect signature there, and require it green at the acceptance
   head.
2. Exercise all three Highway Sequence PDF-vs-Excel self paths and both twins;
   independently recount all 60,254 shared rows and all 1,119 equate relations,
   require zero residual self differences, and prove every genuine injected
   Description/HG/FT/one-sided-`E` divergence still reports.
3. Exercise every HF-09 Direct, By Day, Everything-vs-TSN, and Clean Road path
   named below. Re-derive each representation-only membership from raw, require
   the exact per-family disclosure counts, and require every cell state and
   every headline differing-row/cell total unchanged.
4. Recalculate all affected formulas twins in installed Excel; require clean
   SELF-CHECKs and exact values/formulas parity. Inspect Summary and Notes at
   native scale so the normalized-relation disclosure and representation-only
   count lines are legible and cannot be confused with headline totals.
5. Prove Highway Sequence vs-TSN counts unchanged, `_quote_note` preserved,
   evidence behavior unchanged, and one unrelated family's published cells,
   state masks, counts, and typed outcomes identical to its pre-fix twin.
6. Run every named focused/neighboring check, the complete repository gate,
   compileall, ruff, and `build\build.ps1 -SelfTest` at the same head.
7. Retain one machine-readable manifest/verifier and the independent HF-06/HF-09
   witnesses. A missing, off-head, empty, or self-inconsistent claimed result
   fails closed.

## Required verification matrix

| Gate | `RB5-A1` obligation | Approval rule |
|---|---|---|
| End-user paths | Three HSL self paths plus every named HF-09 Direct/matrix/Clean Road path, both twins | Every path executes at one exact accepted runtime |
| HF-06 source truth | Independent 60,254-row / 1,119-relation census and route-001 raw/PDF adjudication | Zero self differences with no anti-suppression false negative |
| HF-09 source truth | Independent per-family representation-class census | Exact disclosed counts; every affected cell and headline total unchanged |
| Values and formulas | Values/formulas twins plus installed-Excel recalculation | Semantic parity, clean SELF-CHECKs, correct typed outcomes |
| Visual presentation | Summary and Notes at native scale | Both ruled classes are named, counted, legible, and unambiguous |
| Neighboring/evidence behavior | HSL vs-TSN, `_quote_note`, unrelated family, and evidence invariance | No cross-class or cross-family leakage |
| Regression | Focused checks, complete gate, frozen app self-test, exact-head verifier | Every required command passes; new assertions fail pre-fix |

---

### HF-06 — Highway Sequence self-check equation classification

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-06` / `hsl-self-equation` |
| Split fallback branch | `hotfix/hf-06-hsl-self-equation` |
| Priority / order | 6 |
| Depends on | HF-02 (Summary rendering is the disclosure surface) |
| Findings | **PCOA-FINAL-011** (P1) |
| Implementer | Claude |
| Review 1 | **Codex** (owns the 60,254-row equation witness and the route-001 raw adjudication) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | **Inherits RB-5: DENIED — RETURN TO IMPLEMENTATION** |

**Exact scope.** The Highway Sequence PDF-vs-Excel **self** check only, on all
three paths that agree today (Direct self, Everything SELF, PDF-vs-Excel by-day
matrix), both twins — 2 topology decisions.

**Explicitly out of scope.** Highway Sequence **vs TSN** (its equate disclosure
already exists and its counts must not move by a single cell); every other
family's self check; **any shared equality change** — the normalization is opt-in
and scoped to this comparator; the punctuation/case/slash Description class, which
the owner ruled stays **flagged** (HF-09) and must not be swept up by this
normalization; evidence.

**Verified root cause.** The two editions represent one equation differently by
design: the print writes a source line plus a target line, the Excel export folds
marker, classification, suffix placement and description onto its source record.
`compare_highway_sequence_pdf._NOTES_PDF_VS_EXCEL:78-107` already *describes*
this class in prose, but `_SS_SCHEMA:156` asserts every column, so 1,119
equation relations surface as 3,714 differing cells across 1,395 rows
(`PM Suffix` 547, `HG` 929, `FT` 1,119, `Description` 1,119) inside an
unqualified total. Codex's full-corpus canonicalization — 1,119 relations, 39
county/route-boundary relations, three delayed target moves, zero unsupported
cases — leaves **zero** differing rows and cells.

**Files expected to change.** `scripts/compare_highway_sequence_pdf.py` — the
same-source loaders (`_tsmis_row_same_source:118`, `_load_tsmis_same_source:147`),
`_SS_SCHEMA:156` and `_NOTES_PDF_VS_EXCEL:78-107` — plus an opt-in
`CompareSchema` field in `scripts/compare_core.py` if the pair-aware rule needs
engine support, plus checks. The vs-TSN schema (`_hsl._SCHEMA`) and every other
family's schema must be untouched.

**✅ Owner ruling — 2026-07-26: NORMALIZE. These are not real discrepancies.**
The oracle's two branches were "zero differing cells" (canonicalize the relation)
or "a disclosed class excluded from the count". The owner reviewed the actual
cells and ruled the **normalize** branch: the self check must report **zero**
differing cells for the equate population. Summary/Notes disclosure is retained
as documentation of the rule, not as the mechanism.

**The evidence the ruling was made on** — route 001, `ORA 018.540` / `018.530`,
rendered from both editions of the frozen pull (print page 6 vs
`highway_sequence_route_001.xlsx` rows 120–121; images retained locally only,
since they carry real TSMIS content):

| Field | Print (PDF) | Excel export | Why it is not a data difference |
|---|---|---|---|
| `018.540` PM suffix | *blank* | `E` | The same single `E` sits on the **partner row** of the pair on the other side |
| `018.540` HG | *blank* | `D` | Both editions carry `D` on `018.530`; the print does not repeat it on the annotation line |
| `018.540` FT | *blank* | `H` | Same — both carry `H` on `018.530` |
| `018.540` Description | `EQUATES TO END R REALIGNMENT` | `END R REALIGNMENT` | The print prepends the words `EQUATES TO ` |
| `018.530` PM suffix | `E` | *blank* | The partner half of the moved suffix |
| `018.530` HG / FT / Distance | `D` `H` `001.267` | `D` `H` `001.267` | Already equal |

The print additionally colours the whole equate — `018.540`, `EQUATES TO` and the
entire `018.530` line in red, `END R REALIGNMENT` in green, against black
elsewhere (verified from the PDF's own character colours). That marker has no
representation in an XLSX at all, which is precisely why the two editions place
the pieces differently.

**Design consequence Stage 4 must not miss.** A cell-by-cell normalization cannot
close the 547 `PM Suffix` cells, because the `E` genuinely sits on a *different
row* on each side. The rule has to be **pair-aware** — the equate's source and
target rows canonicalized as one relation, which is exactly what Codex's
audit-time canonicalization did over all 1,119 relations (39 county/route-boundary
relations, three delayed target markers, zero unsupported cases, zero residual).

**Guard rails, non-negotiable.** This moves a published count from 3,714 to 0, so:
the change rides an **opt-in** mechanism scoped to this comparator — never a
shared-formula or shared-equality edit; it honors the `compare_core` correctness
lock and
[the Phase-3 decision gates](../../../comparison-perfection/comparison-phase3-decision-gates.md)
(D0's "is this a difference?" criterion); it is proved against an **independent**
oracle over all 60,254 rows, not the product's own parser; Highway Sequence
**vs TSN** counts must not move by a single cell; and the anti-suppression test
below is mandatory — a genuine divergence at an equate row must still be
reported.

**Migration / compatibility.** The published count moves 3,714 → 0, which moves
any bound canary and invalidates nothing persisted — but a committed self-check
generation built under the old rule must be distinguishable from a new one, so the
Notes must state the normalized class explicitly and the workbook must make the
rule self-evident. A reader who compares an old workbook against a new one has to
be able to see *why* the number changed without reading the changelog.

**Tests to add.** Extend `check_compare_highway_sequence.py` with equate
fixtures built to the measured route-001 shape: (a) a source/target pair whose
only differences are the prepended `EQUATES TO`, the non-repeated HG/FT and the
moved `E` reports **zero** differences; (b) the same pair with a real Description
label change still reports a difference; (c) the same pair with a real HG or FT
change on the partner row still reports a difference; (d) an `E` present on one
side only, anywhere in the pair, still reports a difference; (e) a county/route
boundary relation and a delayed target marker are both covered; (f) the rule is
inert for a schema that does not opt in.

**Exact end-user generation path.** Consolidate tab → Highway Sequence both
editions from the frozen `2026-07-23` pull; Compare tab → the PDF-vs-Excel self
check; then the PDF-vs-Excel by-day matrix and the Everything SELF lane. Both
twins.

**Source-truth recount.** Re-derive the 1,119 relations with an app-free reader
over all 60,254 shared rows; independently confirm route 001's XLSX rows 121–122
against rendered PDF page 6; state the exact residual difference count and prove
every remaining difference is a genuine source divergence.

**Values / formulas and installed-Excel checks.** Both twins on all three paths;
installed-Excel recalculation clean; the three paths must agree exactly
(workflow parity is a Stage 2-validated invariant).

**Workbook visual / presentation checks.** Summary and Notes name the class and
its exact count; the disclosure is legible in its stored width on the merged
HF-02 base.

**Evidence.** HSL self is `PROHIBITED`; prove zero artifacts (or the
HF-05-ruled behaviour) and that this bundle changed nothing about evidence.

**Neighbouring-family regression.** Highway Sequence vs TSN (counts must not
move), Highway Log self, Intersection Detail self, and the parity of the three
dispatch paths: full gate plus `check_compare_highway_sequence*.py`,
`check_phase6_highway_sequence_conservation.py` (on demand),
`check_pdf_excel_matrix.py`, `check_day_matrix.py`.

**Measurable acceptance criteria.**
1. The frozen-pull self check reports **zero** differing cells and **zero**
   differing rows, proved over all 60,254 rows by an independent reader — not by
   the product's own parser. (The oracle's disclose-and-exclude alternative is
   closed by owner ruling; normalization is the required mechanism.)
2. All four affected columns close, `PM Suffix` included — so the rule is
   demonstrably pair-aware, not per-cell.
3. **Anti-suppression, mandatory:** a genuine divergence injected at an equate row
   (a changed Description label, a real HG/FT change on the partner row, an `E`
   present on only one side anywhere in the pair) is still reported as a
   difference. A fixture per case.
4. Summary and Notes name the normalized equate class and its relation count so a
   reader knows why the number is zero.
5. HSL **vs TSN** counts unchanged to the cell; all three self paths agree
   exactly.
6. The rule is opt-in and inert for every other family — one unrelated family's
   published cells, state masks, counts and typed outcome proved identical to
   its pre-fix twin. Raw OOXML package bytes are not the invariant.
7. Any moved canary re-blessed with cell-for-cell evidence and a documented
   delta.
8. Full gate green; every new fixture fails pre-fix.

**Rollback.** Revert the merge commit; the self check re-publishes the 3,714
equate cells. Record that explicitly in `IMPLEMENTATION.md` — a revert here is
visible in the deliverable, unlike the presentation bundles.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-06\`;
`hotfix-bundles/HF-06/witness/` for the independent relation census and the
before/after count table.

---
### HF-09 — Representation-only difference classification

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-09` / `representation-class` |
| Split fallback branch | `hotfix/hf-09-representation-class` |
| Priority / order | 9 |
| Depends on | HF-01 (Clean Road Notes), HF-02 (Summary rendering), HF-06 (the disclosed-class pattern) |
| Findings | **PCOA-FINAL-013** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** (owns the four semantic-classification witnesses) |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | **Inherits RB-5: DENIED — RETURN TO IMPLEMENTATION** |

**Exact scope.** The measured representation-only Description/landmark class in
Direct, By Day and Everything vs TSN plus the Clean Road comparison: Highway Log
1,243 × 2 formats, Highway Sequence 11 × 2, Ramp Detail (PDF) 2, Intersection
Detail 1 × 2, Clean Road Highway 5.

**Explicitly out of scope.** **Any equality, normalization or count change
whatsoever** — the owner ruling above closes that branch, so a diff that removes
even one cell from a published total is scope leakage and a reviewer must reject
it. Also out of scope: suppressing the KER 046 `''F'' ST` vs `"F" ST` pair, which
the product already deliberately annotates through the evidence `_quote_note`;
the Highway Sequence self-check equation class (HF-06); route 140's missing
columns (HF-11 / vendor).

**Verified root cause.** The differences are **real literal differences between
two sources** — normalization is not the cause (all 15,410 Ramp Detail and all
16,626 Intersection Detail TSN rows match raw field-for-field; Clean Road's
60,083 × 74 normalization changes zero cells; the identical 1,243-cell set
appears in *both* fresh export formats, ruling out a PDF-extraction artifact).
The defect is that unqualified headline totals do not distinguish this exactly
measured punctuation/case/quote/presentation class from substantive data changes.

**✅ Owner ruling — 2026-07-26: DISCLOSURE ONLY. These differences stay
flagged.** The oracle offered disclosure **or** a separately approved
normalization; the owner has ruled that the punctuation/case/quote/slash class
must remain counted and visible, so the normalization branch is **closed** and no
equality change may be proposed under this bundle. Concretely: the comma-vs-slash
Description pairs (`NEVADA STATE LINE , END OF COUNTY` vs
`NEVADA STATE LINE /END OF COUNTY`, 1,243 per format), `SLO SB CO LINE` vs
`SLO/SB CO LINE`, `CITRUS AVE OC 54-1293` vs `Citrus Ave OC 54-1293`,
`NB OFF TO S. GEYSERVILLE` vs `NB OFF TO S.GEYSERVILLE`, `''F'' ST` vs `"F" ST`,
and the Clean Road leading-apostrophe landmarks all keep their red `D` state and
stay inside every published total. The bundle adds a **count line**, nothing
more.

This is consistent with Stage 2, which explicitly declined to impose a new
equality rule ("the literal differences remain truthful"), and with the shipped
`_quote_note` decision for KER 046, which treats such a pair as worth *showing*.

**Files expected to change.** `scripts/compare_highway_log.py`,
`scripts/compare_highway_sequence_tsn.py`,
`scripts/compare_intersection_detail_tsn.py`,
`scripts/compare_ramp_detail_pdf.py`, `scripts/compare_clean_highway_tsn.py`,
plus a shared opt-in classifier hook (likely one `CompareSchema` field and its
Summary rendering in `scripts/compare_core.py`), plus checks.

**Migration / compatibility.** Under the ruled disclosure branch **no count
moves**, no canary moves, and every committed comparison generation stays valid —
the workbook simply says more about a total it already published. That makes this
the lowest-risk of the semantics bundles. If implementation discovers that
disclosure is impossible without touching equality, it **stops and returns the
bundle to Stage 3** rather than proceeding (Prompt 04 rule).

**Tests to add.** Per family: a fixture pair differing only in punctuation, case,
quote style or landmark edge presentation is counted (disclosure branch) **and**
separately reported in Summary/Notes with an exact count; a substantive change in
the same column is never folded into that class.

**Exact end-user generation path.** Compare tab → Direct vs TSN for Highway Log
(both editions), Highway Sequence (both editions), Intersection Detail (both
editions), Ramp Detail (PDF); the ArcGIS tab's Clean Road comparison; then the By
Day and Everything vs-TSN matrices for the same families. Both twins.

**Source-truth recount.** Re-derive each family's class membership independently
from raw (not from the product's classifier), and prove the disclosed count
equals the independently derived count exactly — 1,243 / 11 / 2 / 1 / 5 per the
finding, restated as measured on the frozen inputs. **No corrected differing-row
total may be asserted** (affected rows may also differ in other fields — the
finding forbids it).

**Values / formulas and installed-Excel checks.** Both twins per family;
installed-Excel recalculation clean; under disclosure, headline totals are
unchanged and the new class line is additive.

**Workbook visual / presentation checks.** The class line is legible in Summary
and Notes on the merged HF-02 base and cannot be mistaken for the substantive
total.

**Evidence.** The `_quote_note` clarifier still fires for KER 046; evidence
behaviour is otherwise unchanged from HF-05's ruled state.

**Neighbouring-family regression.** All five families plus every other family's
Summary (the shared hook must be inert where unset): full gate plus
`check_compare_equality_policy.py`, `check_compare_audit.py`,
`check_tsn_description_leak.py`, `check_clean_road.py`, and every affected
family's `check_compare_*`.

**Measurable acceptance criteria.**
1. Summary and Notes disclose the representation-only class and its exact count
   separately from substantive differences, per family. (The oracle's
   normalization alternative is closed by owner ruling.)
2. **Every affected cell is still flagged**: each of the 1,243 ×2 / 11 ×2 / 2 /
   1 ×2 / 5 cells keeps its red `D` state, and every published differing-cell and
   differing-row total is **numerically unchanged** from pre-fix, proved per
   family.
3. The disclosed counts equal an independently derived census.
4. No equality change of any kind; no corrected differing-row total asserted.
5. The `_quote_note` behaviour is preserved.
6. Families that do not set the hook are identical in published cells, state
   masks, counts and typed outcomes; raw OOXML package bytes are not the
   invariant.
7. Full gate green; every new fixture fails pre-fix.

**Rollback.** Revert the merge commit; because no count moves, this only removes
the disclosure lines and cannot change any verdict.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-09\`;
`hotfix-bundles/HF-09/witness/` for the per-family independent class census and
the disclosure/count table.

---

## Bundle-level dependencies and rollback

- Queue prerequisites: RB-1 and RB-2 are merged; the readiness source also
  includes merged RB-3 and RB-4 plus their successful post-merge smoke records.
- Internal dependency: HF-09 consumes HF-06's disclosed-class pattern, so HF-06
  and HF-09 implement and review atomically while RB-5 remains combined.
- Split fallback: if one combined implementation or review is infeasible,
  return RB-5 to `BLOCKED`, implement `hotfix/hf-06-hsl-self-equation` first,
  merge it, then prepare `hotfix/hf-09-representation-class`. Do not weaken or
  sample either acceptance contract.
- Rollback: revert RB-5's future merge commit. The exact HF-06 and HF-09 rollback
  clauses above remain controlling.
- Readiness does not authorize Stage 4 inside this review closeout. Prompt 04
  must verify and record the exact clean pushed `main` base before changing code.

## Scope approval

| Planner / readiness check | Decision | Commit / date |
|---|---|---|
| Claude (first plan) | **APPROVED — FIRST PLAN** | `4e34bee` / 2026-07-26 |
| Codex (final challenge and combined-transcription check) | **APPROVED — READY** | this readiness commit / 2026-08-10 |
