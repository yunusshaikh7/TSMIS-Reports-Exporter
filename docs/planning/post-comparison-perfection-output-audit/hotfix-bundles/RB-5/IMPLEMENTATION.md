# `RB-5` — Implementation Record

Status: **DENIED — RETURN TO IMPLEMENTATION**

> Codex Review 1 (2026-08-30): **DENIED — EVIDENCE GAP**, solely
> `RB5-R1-EG-001` — the retained HF-09 formulas-twin recalculation/parity
> acceptance result. See [REVIEW.md](REVIEW.md). The implementation claims
> below are preserved; no product defect was established by this precondition return.

| Field | Value |
|---|---|
| Implementer | Claude (owner decision 2026-07-26) |
| Branch | `hotfix/rb-5-difference-classification` (worktree `C:\Users\Yunus\Projects\wt-rb5`; the user's own checkout was never switched or cleaned) |
| Base `main` commit | `87e368c3e9a7eaf26395308e8ddea4aba7d303e5` — fetched 2026-08-30, verified clean and identical to `origin/main` (the `v0.41.2` roadmap closeout). A second DETACHED worktree at the same SHA (`C:\Users\Yunus\Projects\wt-rb5-base`) supplied the base leg of every before/after measurement |
| Head commit | `444e8d9` — the single implementation commit on `hotfix/rb-5-difference-classification` |
| Work items | HF-06 (PCOA-FINAL-011, P1) + HF-09 (PCOA-FINAL-013, P2) |
| Acceptance run | `RB5-A1` |
| Generated-output root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-06\rb5-a1\` and `…\HF-09\rb5-a1\`; committed machine-readable witnesses in `../HF-06/witness/` and `../HF-09/witness/` |

The readiness contract was written against `v0.34.0`-era `main`; `main` is now
eleven releases further on. Every scope statement was re-read against today's
code before it was trusted, and the two known-stale notes in `START-HERE.md`
(HF-07 / HF-08) belong to RB-6, not here. The `v0.35.0` decision that made
`HG`, `City` and `Distance To Next Point` **asserted** in Highway Sequence
vs-TSN is treated as the pre-existing baseline: it is neither reverted nor
reclassified, and every "Highway Sequence vs-TSN counts unchanged" claim below
is measured between the recorded base `87e368c` and this head.

---

## The two rulings, kept visibly apart

RB-5 carries two owner rulings that point in opposite directions, and the
implementation keeps them separated by a mechanism, not by a comment:

| | HF-06 | HF-09 |
|---|---|---|
| Comparison kind | TSMIS **self** check (two renders of one report) | TSMIS **vs TSN** (two different systems) + Clean Road |
| Ruling (2026-07-26) | **NORMALIZE** — not real discrepancies | **DISCLOSURE ONLY** — they stay counted and flagged |
| Mechanism | a pair-aware canonical form applied to the loaded rows of ONE comparator | an opt-in **label** counted alongside the totals; no equality, state or count touched |
| Effect on published counts | 3,714 → 7 differing cells (see below) | **zero** change, by construction |

The separation is enforced in code: every TSMIS-vs-TSMIS flavor that inherits
an HF-09 schema explicitly clears `representation_fields`, and
`check_compare_representation_class.py` fails if that fence is removed.

---

## HF-06 — the Highway Sequence equate relation

### Verified root cause (re-derived, not inherited)

A postmile EQUATION is one fact the two renders spell differently by design.
Measured on the frozen `2026-07-23 ssor-prod` pull, both editions consolidated
through the shipped consolidators (60,254 rows each, 252 routes):

* the print declares **1,119** equate annotation lines — a Description of
  `EQUATES TO` or `EQUATES TO <label>` — and in **1,119 of 1,119** of them the
  `PM Suffix`, `HG`, `FT` and `Distance To Next Point` cells are blank. The
  structure is exact, not approximate;
* the Description pairs exactly, with no unexplained case: **693** are
  `EQUATES TO <label>` against the Excel export's bare `<label>`, and **426**
  are a bare `EQUATES TO` against the Excel export's `PM EQUATION` — the two
  renders' spellings of an equation carrying no landmark label;
* the relation's target (the equated postmile, which carries the `E`) is the
  very next line in **1,112** relations, is delayed by 8 and by 9 rows in two
  more (a left/right alignment branch), and is absent in **5**;
* the Excel export seats the `E` on the annotation row in **270** relations
  and on the target row in **839** — which is why no cell-by-cell rule can
  close the `PM Suffix` column: the marker sits on a different ROW per side.

That spelling is where the published count came from. Per column, at the
recorded base:

| Column | Base cells | Of which the equate spelling |
|---|---:|---:|
| `FT` | 1,119 | 1,119 |
| `Description` | 1,119 | 1,119 |
| `HG` | 929 | 929 |
| `PM Suffix` | 547 | 540 |
| **total** | **3,714** | **3,707** |

### Design

`compare_highway_sequence_pdf` canonicalizes the relation **at load**, after
the existing same-source render decode and before the engine sees a row. That
choice is deliberate:

* the rule has to be pair-aware, and a pair-aware rule cannot be written as a
  per-cell Excel formula — so doing it anywhere else would split the values
  and formulas flavors. Canonicalizing the rows makes the two flavors agree by
  construction;
* `compare_core`'s equality, formulas, state masks and counting are **not
  touched** by HF-06 at all, which is the guard rail the plan demanded ("an
  opt-in mechanism scoped to this comparator — never a shared-formula or
  shared-equality edit");
* load-time normalization is this comparator's established pattern
  (`same_source_render_rows`, `_desc_plain`, `_norm_county` already rewrite
  every cell it loads).

The relation is declared by the PRINT — only the print carries the marker —
and located on both sides by the engine's own `(route, physical key,
occurrence)` identity from `keys_for`, never by row number, so it survives a
genuinely one-sided row. Applied per side, without consulting the other:

1. **the marker** — each render drops only its OWN spelling of it (the
   print's `EQUATES TO ` prefix; the export's label-less `PM EQUATION`),
   keeping every landmark label it printed;
2. **the annotation line's `HG` / `FT`** — blanked, because the print
   structurally has none there and the export is repeating the segment's flags,
   which the target row still carries and still compares on both sides;
3. **the equate suffix** — seated on the relation's TARGET row, which is where
   the print and the TSN prints put it.

Every branch **fails open**: the rule fires only where the print declared an
equate *and* the print's own annotation line is structurally blank; a relation
whose target this render lacks, or whose two rows both carry a suffix, keeps
its suffix cells untouched.

### Result on the frozen pull, through the shipped adapter

| | base `87e368c` | head |
|---|---:|---:|
| Paired rows | 60,254 | 60,254 |
| One-sided rows | 0 / 0 | 0 / 0 |
| Differing rows | 1,395 | **7** |
| Differing cells | 3,714 | **7** |
| `PM Suffix` / `HG` / `FT` / `Description` | 547 / 929 / 1,119 / 1,119 | **7 / 0 / 0 / 0** |

The base run reproduces PCOA-FINAL-011's published numbers **exactly**,
including the per-field split — so the defect signature is bound to the
recorded base, not to the audit's older head.

### The 7 residual cells — stated, not smoothed

Criterion 1 asks for zero. The ruled equate representation class **does** close
completely: `HG`, `FT` and `Description` all report zero, and 540 of the 547
`PM Suffix` cells close. Seven cells survive, and every one of them is a
one-sided equate MARKER — the case acceptance criterion 3(d) explicitly
requires to keep reporting ("an `E` present on one side only, anywhere in the
pair, still reports a difference"). Suppressing them would satisfy criterion 1
by failing criterion 3.

| Route / county / PM | Print | Export | Class |
|---|---|---|---|
| 005 SHA `R030.222` | `E` | *(none in the relation)* | print marks the equated postmile, export marks nothing |
| 032 BUT `R009.571` | `E` | *(none in the relation)* | same |
| 063 TUL `L009.226` | `E` | *(none in the relation)* | same |
| 101 LA `011.725` | `E` | *(none in the relation)* | same |
| 273 SHA `016.184` | `E` | *(none in the relation)* | same |
| 178 KER `R001.694` | `E` | blank | an `E` with no `EQUATES TO` annotation binding it to any relation |
| 580 ALA `L001.101` | *(none in the relation)* | `E` | the reverse: the export marks the annotation row, the print marks nothing |

Two were adjudicated against the RAW sources by hand, one in each direction:

* **032 BUT `R009.571`** — the print's page 10 line reads
  `BUT CHC R 009.571 E L H 000.000 END LT INDEP ALIGN`, preceded by its
  annotation `BUT CHC 009.081 EQUATES TO BEGIN LT INDEP ALIGN`. The raw
  `highway_sequence_route_032.xlsx` row 219 carries the same location with a
  BLANK suffix, and its annotation row (`009.081 BEGIN LT INDEP ALIGN`) is
  blank too — so the export omits the marker for that relation entirely.
* **580 ALA `L001.101`** — the print's page 8 line reads
  `ALA LVMR L 001.101 EQUATES TO END RT INDEP ALIGN` with no `E` anywhere in
  the relation, while raw `highway_sequence_route_580.xlsx` row 77 carries
  `L 001.101` **with** `E`.

Neither is a parser artifact; both are the two renders disagreeing about
whether the marker exists at all. The remaining five are the same shape and are
itemized in the committed witness.

The owner's own adjudication case is unchanged and now closes: route 001
`ORA R018.540` / `018.530`, where the print writes
`EQUATES TO END R REALIGNMENT` with blank flags and seats the `E` on `018.530`,
and the export writes `END R REALIGNMENT` with `D` `H` and seats the `E` on
`018.540`, reports **zero** differing cells.

### Disclosure

The Summary and the Notes sheet both carry a run-resolved line naming the
class and its relation count for THAT comparison (`Equate relations
normalized: 1,119. …`), plus a Notes bullet saying explicitly what the rule
does **not** hide — the landmark label, the target row's own values, and a
one-sided `E`. A reader comparing an old workbook against a new one can see
why the number moved without the changelog, which is what the migration clause
required.

---

## HF-09 — the representation-only class

### Design

One opt-in `CompareSchema` field, `representation_fields`, names the columns
whose **already-counted** differing cells are additionally classified.
`count_diffs` accumulates the subtotal in the same loop that already counted
the cell; `_write_summary` prints it under the headline as a SUBSET, plus a
notes bullet stating that nothing is suppressed. There is one shared
predicate, `compare_core.representation_only`:

> fold letter case and drop every non-alphanumeric character, then compare.

That single rule covers every class the audit measured — separator style,
spacing, letter case, quoting, and a landmark's leading apostrophe — with no
per-case table. It is a LABEL: no verdict, state mask, count, formula or
equality operand depends on it, and `check_compare_representation_class.py`
proves that by rebuilding the same comparison with the label off and asserting
the `Comparison`, both data, `Routes` and both very-hidden `__CMP_E2_SNAPSHOT`
sheets are cell-for-cell identical along with the typed outcome and every
count.

### Scope

Opted in — the audited vs-TSN class, both editions:

| Comparison | Column |
|---|---|
| Highway Log vs TSN (Excel and PDF) | `Description` |
| Highway Sequence vs TSN (Excel and PDF) | `Description` |
| Intersection Detail vs TSN (Excel and PDF) | `Description` |
| Ramp Detail vs TSN (Excel and PDF) | `Description` |
| Clean Road Highway vs TSN | `THY_LANDMARK_SHORT_DESC` |

Explicitly fenced OUT, because the opposite ruling governs a TSMIS-vs-TSMIS
comparison: the Highway Log, Highway Sequence, Intersection Detail and Ramp
Detail PDF-vs-Excel self checks, and cross-environment Highway Log. Each of
those inherits an opted-in schema and clears the field with a comment naming
the reason.

---

## Files changed

| File | Work item | Change |
|---|---|---|
| `scripts/compare_highway_sequence_pdf.py` | HF-06 | the equate relation: detection, per-side canonical form, the run-scoped relation counter, the rewritten self-check Notes |
| `scripts/compare_core.py` | HF-09 (+ HF-06 disclosure) | two opt-in schema fields (`representation_fields`, `disclosure_notes`) with fail-closed validation, the shared `representation_only` predicate, the `count_diffs` subtotal, the Summary subset line and notes |
| `scripts/compare_tsn_common.py` | HF-06 | `make_notes_writer` resolves a CALLABLE note line (a no-op for every existing static line) |
| `scripts/compare_highway_log.py`, `compare_highway_sequence_tsn.py`, `compare_intersection_detail_tsn.py`, `compare_ramp_detail_tsn.py`, `compare_clean_highway_tsn.py` | HF-09 | one `representation_fields=(…)` opt-in each |
| `scripts/compare_highway_log_pdf.py`, `compare_intersection_detail_pdf.py`, `compare_ramp_detail_pdf.py`, `compare_env.py` | HF-09 | the scope fence: clear the inherited field on the TSMIS-vs-TSMIS flavors |
| `build/check_compare_highway_sequence_equate.py` | HF-06 | new — the (a)–(f) fixture matrix, driven through the shipped adapter |
| `build/check_compare_representation_class.py` | HF-09 | new — the class, the anti-fold cases, the label-off control, the wiring fence |
| `docs/planning/.../hotfix-bundles/RB-5/BUNDLE.md` | — | the recorded base SHA |
| `docs/planning/.../IMPLEMENTATION-PLAN.md` | — | RB-5 status |

### Deviation from the plan's expected file list

The plan said "Extend `check_compare_highway_sequence.py` with equate
fixtures". That file locks the **cross-environment** Highway Sequence adapter
(`compare_env.HIGHWAY_SEQUENCE`), not the PDF-vs-Excel self check, so the
fixtures went into a new `build/check_compare_highway_sequence_equate.py`
instead. It is inside the plan's own neighbouring-regression glob
(`check_compare_highway_sequence*.py`), and `build/run_checks.py` globs
`build/check_*.py`, so it is in the blocking gate and in CI automatically.

`compare_ramp_detail_tsn.py` is not on the plan's HF-09 file list, but
`compare_ramp_detail_pdf.py` (which IS) derives its schema from it, so the
opt-in has to live there; the Ramp Detail Excel-vs-TSN sibling therefore also
carries the label. `compare_env.py` and the three `*_pdf.py` files are the
scope fence and only ever clear the field.

---

## Verification — `RB5-A1`

One combined run. Both legs read the SAME frozen inputs and differ only in
product code: the head worktree on `hotfix/rb-5-difference-classification`, and
a DETACHED worktree at the recorded base `87e368c` for the pre-fix leg. Every
comparison below was driven through the SHIPPED adapter, or through the shipped
matrix dispatch — never an internal helper.

### Inputs and their identity

| Input | Identity |
|---|---|
| Report archive | the frozen `2026-07-23 ssor-prod` pull, retained under `…\_scratch\post-comparison-output-audit-claude-independent-2026-07-23\raw-extract\` |
| Highway Sequence, both editions | consolidated through the shipped `consolidate()` entry points: 252 routes, **60,254 rows each side** |
| Self-check inputs | PDF side `sha256 29f96642efdf…`, Excel side `sha256 7ccb8d98e678…` — the base and head runs **logged the same two digests**, so the before/after pair is bound to identical bytes |
| Other TSMIS sides | Highway Log 52,821 (Excel) / 52,807 (PDF); Intersection Detail 16,459 both editions; Ramp Detail (PDF) 15,213 |
| TSN library | rebuilt from the corpus raw sources through the shipped `tsn_library.build_consolidated`: Highway Sequence 69,804 rows, Highway Log 60,083, Intersection Detail, Ramp Detail |
| Clean Road ArcGIS side | freshly built from the 42 staged layers (57,742 rows / 252 routes). The retained 2026-07-22 build is REFUSED by today's header gate — it predates `THY_POPULATION_EFF_DATE` (v0.39.1) — so it could not be reused |

### HF-06 — the self check, on all three paths

| Path | Differing cells | Differing rows | Paired | One-sided |
|---|---:|---:|---:|---:|
| Direct self — **base `87e368c`** | 3,714 | 1,395 | 60,254 | 0 / 0 |
| Direct self — head | **7** | **7** | 60,254 | 0 / 0 |
| PDF-vs-Excel **by-day matrix** — head | **7** | **7** | 60,254 | 0 / 0 |
| **Everything SELF** lane — head | **7** | **7** | 60,254 | 0 / 0 |

All three agree exactly, per field as well as in total (`PM Suffix` 7; `County`,
`City`, `HG`, `FT`, `Distance To Next Point`, `Description` all 0). The base run
reproduces PCOA-FINAL-011's published totals **and** its per-field split
(`PM Suffix` 547 · `HG` 929 · `FT` 1,119 · `Description` 1,119), so the defect
signature is bound to the recorded base, not inherited from the audit's older
head.

### Values and formulas, recalculated in installed Excel

The by-day matrix cell settled its live-formulas twin (57.8 MB). A copy was
opened in **installed Excel 16.0**, `CalculateFullRebuild()`, saved, and read
back:

* every headline number in the recalculated FORMULAS workbook equals the VALUES
  twin — 60,254 / 60,254 / 60,254 / 60,254 / **7** / 60,247 / **7**;
* every per-field count agrees (`PM Suffix` 7, the rest 0);
* **all ten SELF-CHECK rows read `OK`**, including "Build-time source identity
  and duplicate pairing snapshot is current".

That is the point of canonicalizing the ROWS rather than the comparison: the
live formulas recompute the same truth from the same data sheets, so the two
flavors cannot drift. Retained as `../HF-06/witness/installed-excel-recalc.json`.

### HF-06 source-truth recount — an app-free reader

An independent oracle read all 252 raw `.xlsx` exports with openpyxl and all 252
raw `.pdf` prints through pdfplumber's own `extract_text()`, under a line
grammar written for the oracle — **not** the application's header-anchored
column windows. Rows pair on the identity the comparison itself uses (route +
county + prefixed postmile + occurrence); nothing unpaired is assumed away.

| Fact | Independent oracle |
|---|---|
| Print rows / Excel rows | 60,252 / 60,254 |
| `EQUATES TO` annotation lines | **1,117** of the product's 1,119 |
| Annotation lines structurally blank (suffix + HG + FT + Distance) | **1,117 of 1,117** |
| Label pairing | **691** `EQUATES TO <label>` == `<label>`, **426** bare `EQUATES TO` == `PM EQUATION`, **0 unexplained** |
| Equate suffixes | print **1,124**, export **1,119** — identical to the product's parser |
| Relation targets | 1,110 at the next line, one at +8, one at +9, 5 with none |
| County/route-boundary relations | **39** — the exact number the plan cites |
| Suffix seat | print always on the target; export on the annotation 268, on the target 839, nowhere 5 |
| Residual after canonicalization | 11 suffix cells |

The oracle's 11 minus the product's 7 is **exactly** the two relations its
minimal grammar cannot see: both are annotations whose printed Description
WRAPS (route 036 TRI `R028.650`, route 215 RIV `043.679`), which the shipped
parser rejoins by design and the oracle deliberately does not. Their four suffix
cells are `036 TRI R028.650` + `036 TRI 027.232` and `215 RIV 043.679` +
`215 RIV R043.614`. Remove those four and **the independent reader's residual
set is the product's seven rows, exactly** — an app-free reader reproduces the
product's residual row for row. Retained as
`../HF-06/witness/equate-relation-census.json`.

### The seven residual cells — stated, not smoothed

Criterion 1 asks for zero. The ruled equate representation class **does** close
completely: `HG`, `FT` and `Description` all report zero, and 540 of the 547
`PM Suffix` cells close — 3,707 cells across all 1,395 rows.

Seven cells survive, and every one is a one-sided equate MARKER: the two renders
disagree about whether the `E` exists at all, not about where it sits. HF-06
acceptance criterion 3(d) requires precisely this case to keep reporting ("an
`E` present on one side only, anywhere in the pair, still reports a
difference"), so suppressing them would satisfy criterion 1 by failing criterion
3. Two were adjudicated by hand against the raw print and the raw export, one in
each direction:

* **032 BUT `R009.571`** — print page 10 reads
  `BUT CHC R 009.571 E L H 000.000 END LT INDEP ALIGN`, preceded by its
  annotation `BUT CHC 009.081 EQUATES TO BEGIN LT INDEP ALIGN`; raw
  `highway_sequence_route_032.xlsx` row 219 carries the same location with a
  BLANK suffix, and its annotation row is blank too. The export omits the marker
  for that relation entirely.
* **580 ALA `L001.101`** — print page 8 reads
  `ALA LVMR L 001.101 EQUATES TO END RT INDEP ALIGN` with no `E` anywhere in the
  relation; raw `highway_sequence_route_580.xlsx` row 77 carries `L 001.101`
  **with** `E`. The reverse direction, equally genuine.

Neither is a parser artifact. All seven are itemised in
`../HF-06/witness/before-after-counts.json`.

The owner's own adjudication case now closes: route 001 `ORA R018.540` /
`018.530` — the cells the NORMALIZE ruling was made on — reports **zero**
differing cells.

### HF-09 — disclosure only, proved per family

Every affected family was generated at BOTH heads from identical inputs:

| Comparison | base vs head | Disclosed | Independent census | Finding |
|---|---|---:|---:|---:|
| Highway Log vs TSN (Excel) | 84,709 cells / 38,478 rows / 49,195 paired / 3,626 / 10,888 — **identical**, all 30 per-field | 1,243 | **1,243** | 1,243 |
| Highway Sequence vs TSN (Excel) | 28,450 / 22,554 / 57,050 / 3,204 / 12,754 — **identical** | 12 | **12** | 11 |
| Highway Sequence vs TSN (PDF) | 27,601 / 22,728 / 57,483 / 2,771 / 12,321 — **identical** | 12 | **12** | 11 |
| Intersection Detail vs TSN (Excel) | 5,092 / 2,816 / 16,199 / 260 / 427 — **identical**, all 35 per-field | 1 | **1** | 1 |
| Intersection Detail vs TSN (PDF) | 5,092 / 2,816 / 16,199 / 260 / 427 — **identical** | 1 | **1** | 1 |
| Ramp Detail vs TSN (PDF) | 619 / 468 / 15,204 / 9 / 206 — **identical**, all 13 per-field | 3 | **3** | 2 |
| Highway Log vs TSN (PDF) | 84,202 / 38,931 / 49,829 — **identical**, all 30 per-field | 1,243 | **1,243** | 1,243 |
| Clean Road Highway vs TSN | 281,393 / 48,942 / 52,629 / 5,113 / 7,454 — **identical**, all 75 per-field | 2 | **2** | 5 |

Not one published count moved, in any family, in any column.

The census is a SEPARATE re-implementation of the predicate, applied to the two
sides read back out of each committed VALUES workbook's own published
Comparison sheet. It never imports the product's classifier and never asks the
product how many it found.

Highway Log matches the finding exactly, in **both** editions — 1,243 and
1,243, which is precisely PCOA-FINAL-013's claim that "the identical 1,243-cell
set appears in both fresh export formats". Intersection Detail matches exactly
too (1 and 1: the KER 046 `''F'' ST` vs `"F" ST` pair).

**The three deltas are disclosed, not smoothed.**

* Highway Sequence measures **12** where the finding said 11, and Ramp Detail
  **3** where it said 2. Both are the SAME single rule: the shared predicate
  also folds a space that splits or joins a word — `EB ON FR NB RTE 55` vs
  `EBON FR NB RTE 55`, `SEG, NB OFF, LT,SF AIRPRT` vs
  `SEG,NB OFF,LT,SF AIRPRT`. Every classified pair is listed in the witness so
  the reviewer can adjudicate them.
* Clean Road measures **2** where the finding said 5, and the difference is the
  ArcGIS SIDE, not the classifier: the audit measured against the 2026-07-22
  build, which today's header gate refuses, so this run used a fresh build under
  the v0.39.1–v0.39.3 rules — a different row set and therefore a different
  class membership. Both cells found are the finding's own named examples (the
  landmark leading apostrophe and the `SLO/SB` separator pair).

The finding's own acceptance language permits the count to be **restated as
measured on the frozen inputs**, and no published total moves either way — base
and head are identical in every family, in every column.

Clean Road's typed completion is `partial` on BOTH legs identically — that is
the pre-existing HF-01 unavailable-anchor disclosure (the shipped
"span could not be placed" class), untouched by RB-5.

### Regression, and what could not move

| Gate | Result |
|---|---|
| Full repository gate (`build/run_checks.py`) | **171 passed, 0 failed of 171** — 169 at the base plus this bundle's two new checks. A later re-run in the acceptance worktree showed `check_validation` failing; it is ENVIRONMENTAL, not a regression — `evidence.collect` emits a duplicate archive member when a real populated `tsn_library/` is staged beside it (`state/tsn_library/highway_log/consolidated/tsn_highway_log_consolidated.xlsx.outcome.json`), which the acceptance run had staged. Moving the staged library aside and re-running that check alone prints `all good`. Flagged separately; it is not RB-5 scope and no RB-5 file touches the evidence collector. |
| `python -m ruff check scripts build version.py` | **All checks passed** |
| `python -m compileall scripts build version.py` | clean |
| Application self-test (`scripts/self_test.py`, the same routine `build.ps1 -SelfTest` gates) | **SMOKE OK** — every app-required path, including the dynamic import of `compare_highway_sequence_pdf` |
| New fixtures fail PRE-fix | `check_compare_highway_sequence_equate.py` fails **11 assertions plus an AttributeError** at `87e368c`; `check_compare_representation_class.py` fails at import (the mechanism does not exist there) |
| Highway Sequence **vs TSN** counts | unchanged to the cell on BOTH editions — HF-06 criterion 5 |
| An unrelated family | `check_compare_representation_class.py` rebuilds the same comparison with the label OFF and asserts the `Comparison`, both data sheets, `Routes` and BOTH very-hidden `__CMP_E2_SNAPSHOT` sheets are cell-for-cell identical, along with every count and the typed outcome |
| Evidence | no evidence file is touched by the diff. `evidence_highway_sequence.load_sides_self` calls the self comparator's OWN `_load_pair`, so evidence sees the same canonicalized rows the comparison does (CMP-AUD-107/210); `check_visual_evidence` and the evidence checks pass in the gate |

### What was NOT re-run, and why

* **Cross-environment, Baseline and by-day vs-TSN matrices** beyond the
  PDF-vs-Excel cell exercised above. HF-06 is confined to one comparator's
  loader and HF-09 adds a label; neither can move a count, which the per-family
  base-vs-head pairs above prove directly on the real corpus.
* **`build.ps1 -SelfTest`** as a packaged build. The change adds no import that
  PyInstaller could miss (`re` is stdlib and already bundled), and the identical
  self-test routine was run against the head tree and passed. A packaged build
  would re-prove packaging, not this bundle.
* **Ramp Detail and Highway Log self checks**, and the Highway Detail /
  Intersection Detail self checks: the HF-09 scope fence explicitly clears the
  label there, and `check_compare_representation_class.py` asserts it stays
  clear.

---

## Rollback

Revert the merge commit. HF-06's revert is **visible in the deliverable**: the
Highway Sequence PDF-vs-Excel self check immediately re-publishes the 3,707
equate-spelling cells (3,714 total, 1,395 rows) and loses the Summary/Notes
disclosure. HF-09's revert removes only the count line and the notes bullet —
no verdict, count or cell state can change, because none ever depended on it.
