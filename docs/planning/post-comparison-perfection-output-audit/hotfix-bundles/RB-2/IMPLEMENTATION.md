# `RB-2` — Implementation Record

Status: **IMPLEMENTING — acceptance run `RB2-A1` in progress**

| Field | Value |
|---|---|
| Bundle / work items | **RB-2 / HF-02 + HF-03** |
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-2-deliverable-presentation` (worktree `C:\Users\Yunus\Projects\TSMIS-rb2-worktree`; the user's `main` checkout is untouched and still clean) |
| Base `main` commit | `896083e014d0451d5b05e5b6b024339aebc84d74` — clean, identical to `origin/main`, fetched without force before branching |
| Implementation commits | `da1d480ede1f79671f4573b311ac2e402cd16eaf` (the change), `eb54b96` (the Excel-measured geometry correction below) |
| Pushed | `origin/hotfix/rb-2-deliverable-presentation` |
| Canonical findings | PCOA-FINAL-002, -003, -008, -009, -014, -016, -019 |
| Generated-output root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-02\` (workbooks + measurements) and `…\HF-03\` (TSN rebuild + capture lifecycle); committed machine-readable witnesses under `hotfix-bundles/HF-02/witness/` and `hotfix-bundles/HF-03/witness/` |

## Changes

| File | Change | Findings |
|---|---|---|
| `scripts/compare_core.py` | **Measured stored geometry instead of hard-coded widths.** New shared helpers (`fitted_width`, `_text_px`, `_width_to_px`, `_wrapped_lines`, `_grid_geometry`, `_wrap_align`, `_apply_grid_geometry`) measure text in the SAME pixel model the audit gate uses — a stored width of N is `round(N*7)+5` px, a cell pads ~2 px each side — in the real font when the platform can read one (Arial, the workbooks' own font, and Calibri, the gate's, whichever is wider) and by a deliberately generous character estimate when it cannot; the failure direction is always a wider column. `_write_comparison` fits the key/category column and the status column to their real content and gives every field column a width (`_auto_field_widths`, computed ONCE per comparison so both twins are identical); `_write_only_sheet` fits the same keys; `_write_data_sheet` fits the key/back-link columns; `_write_summary` and `_write_spot_check` build their sparse grid first, then declare the widths their own cells need and WRAP (with a row tall enough) the sentences a sane width cannot hold. Identity cells are widened, never wrapped. | 008, 009 |
| `scripts/compare_core.py` | **A wholly-context column says so.** `_write_summary`'s *DIFFERENCES BY FIELD* renders `not compared (context)` for a column that is context in its entirety (`sc.is_context`), instead of a bare `0` that reads exactly like a compared column with no differences. Per-cell context (Highway Log's ditto columns) is untouched and keeps reporting real counts. | 014 |
| `scripts/compare_core.py` | **The values twin publishes its headline.** The values flavor writes `Summary!B3` as the computed literal, so a consumer that never recalculates (openpyxl `data_only`, pandas, any automated reader) reads the same verdict the typed outcome carries; the formulas twin's live guarded verdict is unchanged. Certification does not move: the live SELF-CHECK freshness row now says **`REGENERATE REQUIRED`** itself rather than the generic `CHECK`, in BOTH flavors, and two notes say that the stored headline is build-time and that row is the live guard. | 019 |
| `scripts/compare_core.py` | The Provenance sheet states `read via: …` when a side's bytes were reached through a verified private copy rather than read from the named path directly. | 003 |
| `scripts/summary_layout.py` | The by-category sheet's `Category` column is fitted to its real labels (shared `fitted_width`), not left at 34. | 008 |
| `scripts/matrix_build.py` | **`captured_tsn_workbook` carries the library's own producer record.** The private copy's sidecar now reproduces `tsn_source_claims`, `tsn_normalization_version`, `tsn_raw_manifest`, `tsn_normalized_workbook_identity` and `tsn_artifact_identity_token`, read under the SAME before/after window the outcome contract already used (a record that moved mid-capture is refused, not copied) and only when the recorded workbook identity equals the bytes this capture verified for itself. It also records `tsn_capture_origin` — the canonical path it was taken from plus that identity. | 002, 003 |
| `scripts/matrix_build.py` | **Temp hygiene.** `_sweep_stale_tsn_captures` removes capture directories a KILLED process could never unwind (the audited leftovers), bounded by prefix, by being directly under the temp root, by being a real directory and not a reparse point, by an age longer than any comparison holds its capture (so it can never race a live one), and by containing only the two file shapes a capture creates. Anything unexpected is left alone and logged. | 016 |
| `scripts/compare_tsn_common.py` | **Provenance names the durable input.** `capture_input_provenance` substitutes the canonical selection recorded by the capture — but ONLY when that record's identity equals the sha256/size just hashed here and the canonical file is still readable — and adds `read_via`. The digest always remains that of the bytes actually read. | 003 |
| `build/check_workbook_presentation.py` | **New golden check.** Builds a summary-schema and a detail-schema comparison in both flavors and measures them with the audit's OWN gate, imported from the committed `stage2-measure-clipping.py` so the product check and the oracle cannot diverge; plus the identity-widened-not-wrapped rule, the context rendering (and that a compared column with zero differences still reports a real `0`), the values headline read `data_only`, its agreement with the typed outcome, and the live freshness guard in both twins. | 008, 009, 014, 019 |
| `build/check_tsn_canonical_consumer_identity.py` | Adds `test_capture_carries_its_source_record`: the carried claim fields, a matrix-lane comparison printing the SAME identity line as the Direct lane, provenance naming the durable selection with no `%TEMP%`, an unverifiable origin record keeping the literal path, zero capture directories after success / failure / cancellation, and the sweep's three bounded outcomes. Reads the new constants through `getattr` so it degrades to semantic FAILs on a pre-fix tree instead of crashing. | 002, 003, 016 |
| `build/check_compare_skipwarn.py`, `build/check_compare_pairing_policy.py`, `build/check_compare_build_freshness.py` | Re-point the three policy assertions that locked the values twin's headline as a formula: they now require the stored literal AND the live freshness row carrying `REGENERATE REQUIRED`. Same guarantee, asserted on the cell that now carries it. | 019 |
| `hotfix-bundles/RB-2/BUNDLE.md` | Base `main` SHA filled in before any code change. | — |

## Root causes confirmed

Each was re-opened in code before changing anything; all matched the frozen contract, so no return to planning was needed.

| Finding | Confirmed at | Evidence |
|---|---|---|
| 008 / 009 | `compare_core._write_comparison` (`c_loc` width **12** = 89 px), `_write_data_sheet` (key 14 / back 13), `_write_spot_check` (`B` **19**), `_write_summary` (`B` **46**), `summary_layout` (`A` **34**) | The pre-fix tree reproduces the audit's exact classes — see the red proof below |
| 014 | `_write_summary`'s per-field loop wrote the state-mask `SUMPRODUCT` (or the literal count) for every field, with no notion of a wholly-context column | Pre-fix run renders `City → 0` beside `Description → 5` |
| 019 | Both flavors wrapped the verdict in `=IF(freshness, …)`; openpyxl writes a formula cell with an EMPTY `<v>`, so `data_only=True` reads `None` | Pre-fix run reads `Summary!B3 = None` on both values twins |
| 002 | `captured_tsn_workbook` published `write_outcome(captured, snapshot_result)` with no `extra=`, so the reduced sidecar dropped every claim key; `compare_ramp_summary_tsn.compare` (and its three siblings) read claims with `consolidation_meta.read_extra(tsn_path, …)`, which is path-adjacent | Pre-fix run prints the exact audited sentence: *"TSN print: no source-claims record beside this normalized workbook (older normalization) — rebuild the TSN library to capture the print identity."* |
| 003 | `capture_input_provenance` recorded `str(path.resolve())` of whatever path it was handed | Pre-fix run records `…\AppData\Local\Temp\tsmis-tsn-consumer-…\tsn_ramp_summary_normalized.xlsx` |
| 016 | The `finally` block is identity-bound and correct for success/failure/cancellation, but nothing removes a directory whose process was killed | Pre-fix run leaves an aged abandoned directory in place |

## Red → green, bound to the pre-fix base

Both new check files were run against the **base commit's own `scripts/`** (junctioned into a scratch root so the checks import base code) and then against this head.

| Check | At base `896083e` | At head `da1d480` |
|---|---|---|
| `build/check_workbook_presentation.py` | **17 FAILs**, every one a defect signature: 4 workbooks materially clipped (`Summary!B13/B14` short 176–364 px, `Spot Check!B6` short 48–55 px, `Spot Check!D7` short 115 px, `Comparison!A` short 33–220 px, `Comparison!G` short 8–275 px), the category column 12.0 wide, `City → 0`, `Summary!B3 → None`, no stored-headline note, the freshness row saying `CHECK` | **all good** |
| `build/check_tsn_canonical_consumer_identity.py` (new test) | **4 FAILs**: no claim field carried; the false rebuild instruction printed; provenance naming the `%TEMP%` capture; no sweep. Every pre-existing assertion in the file still passed | **all pass** (21 assertions in the new test) |

## Verification results

| Contract gate | Method | Result |
|---|---|---|
| Full gate | `build/run_checks.py -j 4 -k` (the whole globbed list, from this tree) | **PASS — 158 passed, 0 failed of 158** (212 s). The first run flagged exactly the 2 policy checks that asserted the old headline contract; they were re-pointed and the gate re-run clean |
| Byte-compile | `python -m compileall scripts build` | **PASS** |
| Ruff (gate-exact) | `ruff check scripts` in a throwaway scratch venv | **PASS — "All checks passed!"** |
| Frozen self-test | `build\build.ps1 -SelfTest` | *(pending)* |
| One-sided path | A route-bearing schema with rows on one side only, both flavors | **PASS** — the Only-in key columns fit; the empty-key case falls back to the declared minimum |
| Neighbouring-family regression (checks) | Every check both contracts name, from the post-correction gate run | **PASS — 18/18 green**: `check_compare_audit`, `check_compare_build_freshness`, `check_comparison_artifact_schema`, `check_compare_equality_policy`, `check_compare_source_files`, `check_matrix`, `check_day_matrix`, `check_baseline_matrix`, `check_pdf_excel_matrix`, `check_matrix_tsn`, `check_tsn_highway_log_claims`, `check_tsn_canonical_consumer_identity`, `check_tsn_freshness`, `check_tsn_outcome`, `check_matrix_cache_adversarial`, `check_comparison_publication`, `check_artifact_store`, plus the merged HF-01 `check_clean_road` |
| Acceptance run `RB2-A1` | *(in progress — see below)* | |

## The first measured pass FAILED — and set the constants

The audit's own gate (Calibri metrics, the same tolerance) reported **0** clipped
cells as soon as the first version of the fix was in. Installed Excel did not
agree. Run over the REAL first generated workbook — `ssor-prod_ramp_summary_tsn`
from the Everything lane — Excel's own AutoFit rejected the geometry three ways,
and each rejection is now a measured constant rather than an assumption:

| What Excel said | Why the first pass was short | Constant |
|---|---|---|
| A column stored as `46` reports `ColumnWidth 45.29`, and the label needs `46.00` | Excel's character width is the stored number minus 0.71, so a width computed in characters and stored raw is always that much narrow | `_STORED_WIDTH_OFFSET = 0.71` |
| `→ Comparison row:` needs `18.43` where the fit stored `18`; `TSN row (key-matched):` needs `22.29` where it stored `22` | rasterizing a 10 pt font at 13 px loses ~2.5 % per glyph to integer rounding, and the unhinted advance sum still runs 1.3–2.4 % under Excel's own | `_MEASURE_SCALE = 4` (oversample, then scale back) + `_MEASURE_MARGIN = 1.05` |
| `15213 ≠ 15410` needs `12.57` in a column the schema declared `12` | a declared `cmp_width` was being treated as a ceiling, so a schema could clip its own difference cells | a declared width is now a **floor**, never a ceiling |

After the correction, re-measured on the same real pair, **both twins**:

| Sheet | `columns_too_narrow` | `rows_too_short` |
|---|---|---|
| Summary | `[]` | `[]` |
| Spot Check | `[]` | `[]` |
| Comparison | `[]` | `[]` |
| Summary by Category | `[]` | `[]` |
| Provenance | `[]` | `[]` |

The oracle is Excel's own metrics, not an estimate: every populated cell whose
right neighbour blocks it from spilling is re-measured on a scratch sheet
carrying that cell's real font — an unwrapped cell must fit its column's STORED
width, and a wrapped cell's row must be at least the height Excel autofits to at
that width. Deliberately hidden columns (the state-mask chunks) and the
Stage-2-validated 45.75 pt wrapped header band are excluded as out of scope.
Witness: `HF-02\excel-metrics-ramp-summary{,2,3}.json` — the failing pass is
retained beside the passing one.

## Acceptance run `RB2-A1`

*(in progress — the generation was restarted from scratch after the geometry
correction so every measured workbook carries the final geometry)*

### The measured before/after — base code vs head code, same frozen inputs

Both trees generated the same corpus from the same frozen archive and the same
TSN library on the same day, and every workbook was then measured by the audit's
own gate plus BOTH of RC-3's methods. Provisioned per-route source exports are
excluded (they are inputs, untouched by this bundle); in-flight `.tmp-`
artifacts and evidence workbooks are excluded for the reasons given elsewhere in
this record.

| Oracle, over the comparison DELIVERABLES | BASE `896083e` | HEAD |
|---|---:|---:|
| materially clipped cells (RC-1's own gate) | **2,036** | **0** |
| workbooks printing "rebuild the TSN library" | **12** | **0** |
| workbooks naming a `%TEMP%` path — zip probe / cell walk | **18 / 18** | **0 / 0** |
| `.provenance.json` naming a `%TEMP%` path | **18** | **0** |
| recorded input paths that no longer exist | **18** | **0** |
| deliverables carrying a stored literal headline | 15 | **52** |
| …of which readable `data_only` | 15 | **52** |
| workbooks named `(values)` with a BLANK `data_only` headline | **12** | **0** |

RC-3's two independent methods agree exactly on both trees (`zip == walk`), which
is what the contract requires of the re-derivation. The 18 base inputs that "no
longer exist" are PCOA-FINAL-003's harm stated numerically: the recorded TSN path
was a private capture directory that is deleted when the run ends.

**Disclosed, not buried — the evidence workbook has its own clipping, and this
bundle did not change it.** Running RC-1 over the WHOLE generated tree returns
64 (base) and 127 (head) rather than 0, and every one of those hits is inside an
EVIDENCE workbook. Per evidence SET the counts are identical in both trees —
Highway Log 63, Highway Sequence 1 — and head only shows more because it has an
extra set (the base pass deliberately skips the By Day lane). Evidence
presentation is written by `visual_evidence.py`, which this bundle does not
touch and which HF-02 places explicitly out of scope, so the pre-existing
evidence-workbook clipping is left exactly as found. It is recorded here and in
`clipping-before-after.json` (`non_deliverable_detail`) so a reviewer who
measures the whole tree sees the number explained rather than unexplained.

**Two corrections to the tally, both mine and both in the summary logic rather
than the product** — the raw measurement witness already contained what was
needed to see them:

1. A values twin was first identified by FILENAME. The classic and Direct lanes
   name the PRIMARY file the **formulas** workbook and `(values)` the twin — the
   inverse of the matrix lanes — so four formulas workbooks were misread as
   values twins with "blank" headlines. Identifying by whether stored `B3` is a
   formula gives **0 blank of 52**.
2. Recorded inputs were tested with `is_file()`, which is False for the classic
   lane's **folder** inputs. Testing existence gives **0 missing**.

### What installed Excel's own AutoFit found that RC-1 could not

Excel's metrics are stricter than the audit's gate, because the gate reads a
workbook data-only and therefore cannot see what a FORMULA renders. Run over the
final workbooks it reported six cells in two classes. Both are stated here; one
is fixed, one is a declared boundary.

**FIXED — `Provenance!A`, a hard-coded 12.** On a cross-environment comparison
the input's *role* is the side's own name (`SSOR-PROD 2026-07-23`), which needs
20.86. Column A's right neighbour is always populated, so it can never spill.
This is exactly the defect class HF-02 exists to remove, on a sheet this bundle
already modifies (the `read via` line), and it was a genuine miss in the first
pass: `_write_provenance_sheet` now fits column A to the real role labels. The
two classic environment pairs were regenerated and re-measured — **Excel
`columns_too_narrow: 0`, RC-1 `0 clipped`** on all four workbooks — and the full
gate re-run clean afterwards.

**DECLARED BOUNDARY — `Spot Check` value columns.** Four cells
(`Spot Check!r37c3/c4`, `r22c4/c6`) hold the values of whichever Comparison row
the reader types into the input cell at RUNTIME. Their content is not knowable
when the workbook is written, so no stored width can be fitted to it; the column
holds a fixed width and a longer value truncates visually, as in any
spreadsheet. This class is unchanged from base code, the audit did not flag it,
and the Spot Check cell the audit DID flag — the `B6` instruction — is fixed and
measures clean. Widening these to the widest value any field could contain would
push two columns to ~60 characters on every family for a runtime-only gain, so
the width is left as the schema's and the limitation recorded here instead.

### Installed-Excel recalculation — the twins agree, live

`CalculateFullRebuild` + Save in installed Excel, on COPIES, then an app-free
read of the cached results. The set is chosen to satisfy both contracts: both
schema shapes (summary / detail), both TSN identity classes (printing /
silent — HF-03 asks for "at least one family per identity class" in as many
words), both lanes (matrix / classic), and BOTH twins of each.

| Workbook | SELF-CHECK rows | non-OK | error cells | Excel's live verdict |
|---|---:|---:|---:|---|
| ramp_summary vs TSN — values | 7 | **0** | **0** | 23 cells, 2 one-sided |
| ramp_summary vs TSN — formulas | 7 | **0** | **0** | 23 cells, 2 one-sided |
| intersection_detail vs TSN — values | 11 | **0** | **0** | 5,092 cells, 687 one-sided |
| intersection_detail vs TSN — formulas | 11 | **0** | **0** | 5,092 cells, 687 one-sided |
| highway_sequence vs TSN — values | 10 | **0** | **0** | 5,573 cells, 15,958 one-sided |
| highway_sequence vs TSN — formulas | 10 | **0** | **0** | 5,573 cells, 15,958 one-sided |
| ramp_summary classic env — formulas | 7 | **0** | **0** | 67 cells, 0 one-sided |
| ramp_summary classic env — values | 7 | **0** | **0** | 67 cells, 0 one-sided |

**Every SELF-CHECK row OK, zero cached error values, and the twins agree
exactly**: for each family the verdict Excel computes LIVE in the formulas twin
equals the literal now stored in the values twin. For Highway Sequence that is a
triple agreement — `5,573 / 15,958` from the stored literal read `data_only`,
from Excel's own live recalculation, and from the typed `ComparisonOutcome`.

This is the real content of PCOA-FINAL-019's fix: the values twin's headline is
not merely non-empty, it is **correct**, and installed Excel says so. The
freshness SELF-CHECK reads `OK` on every unedited workbook, so the renamed
`REGENERATE REQUIRED` state does not misfire.

**Not recalculated, and why:** Highway Log and the remaining PDF-edition
families. RB-1 measured **68 minutes for a single statewide formulas twin**, so
recalculating all nine families both ways is 6–8 hours of Excel that would test
the same code paths already covered above. The boundary is stated here rather
than left for a reviewer to discover; under the owner's bounded-review ruling no
reviewer repeats this leg, so this record is its single source.

### Criterion 5 — nothing else moved, proved per family

Base code and head code generated the same corpus from the same frozen inputs on
the same day, and every deliverable pair was then compared cell for cell:

```
deliverable pairs compared                          : 42
pairs with ANY truth-sheet change or outcome change : 0
only in base: 0        only in head: 0
typed outcomes NOT equal                            : 0
```

"Truth-sheet" means everything except this bundle's own surface: the
`Comparison` sheet INCLUDING its hidden `E`/`D`/`N`/`U` state-mask columns, both
`Only in …` sheets, both data sheets, `Routes`, both very-hidden
`__CMP_E2_SNAPSHOT_A/B` sheets, and any extra rollup. Zero differing rows across
all 42 pairs, and every typed `ComparisonOutcome` — counts, verdict,
pairing_quality — identical. That satisfies HF-02 criterion 5 and HF-03
criterion 5 together, including "Direct-lane workbooks unchanged".

### Criterion 4 — the capture lifecycle, and the one directory that remained

36 matrix-lane cells ran, each taking a private TSN capture. After the run,
**one** `tsmis-tsn-consumer-*` directory remained, and its provenance is exact
rather than mysterious: it was created **2026-07-29 04:12:31**, the moment a
session crash HARD-KILLED the run mid `byday|tsn|intersection_detail`. No
`finally` clause survives a kill — which is the entire reason
`_sweep_stale_tsn_captures` exists.

It was not swept during this run for a reason that is the age bound working
correctly, not failing: the head pass's captures all ran 04:58–07:51, when that
directory was 0.8–3.6 h old — INSIDE the 6 h bound that stops the sweep from
racing a capture another process may still be holding. The base pass (07:52–
13:30) runs pre-fix code, which has no sweep at all.

`matrix_build._sweep_stale_tsn_captures` — the same call `captured_tsn_workbook`
makes at every capture — was then run against that real 20-hour-old orphan:

```
before sweep: 1  tsmis-tsn-consumer-cvzbqzqw  age 20.0 h
after sweep : 0
```

A genuine orphan left by a killed process, removed by the shipped code. The
success, failure and cancellation paths are proved separately and hermetically
by `check_tsn_canonical_consumer_identity`. Witness:
`HF-03/witness/temp-capture-lifecycle.json`.

### The Everything lane — 9 of 9 audited families, and why the other three are out

| Family | Result |
|---|---|
| Ramp Summary · Highway Sequence · Highway Log · Intersection Summary · Intersection Detail · Highway Log (PDF) · Intersection Detail (PDF) · Highway Sequence (PDF) · Ramp Detail (PDF) | **ok — all 9**, both twins each |
| Ramp Detail (Excel) | `error` — *"isn't a CONSOLIDATED Ramp Detail workbook (expected a leading 'Route' column)"*. This is **PCOA-FINAL-001 reproducing exactly**, the finding RB-3/HF-04 owns. It is a graceful, correct refusal, not a crash |
| Highway Detail · Highway Detail (PDF) | `EXCEPTION` — *"the Highway Detail output folder doesn't exist yet"* / *"No TSMIS Highway Detail (PDF) files were found"* |

The Highway Detail result is worth stating precisely, because it **independently
corroborates the standing pre-release block from the frozen input itself**: the
provisioning step copied the archive's own export folders into the store and
reported `highway_detail_pdf: 0 files`. The 2026-07-23 archive carries no
Highway Detail export at all — which is exactly what "the vendor greyed the
exports out again" means on disk. Nothing was inferred about HD, no HD artifact
was produced, and no HD canary was touched.

These three are excluded from the harness's retry test by name: neither is
RB-2's defect, and neither is fixable by retrying, so neither may stop the
acceptance chain. Every other failure class still triggers a retry.

### What the base-code pass covers, and the one lane it deliberately omits

The base tree (`main` @ `896083e`, its `scripts/` copied verbatim, reading the
SAME TSN library and the SAME frozen run folders through junctions) exists for
exactly one claim: HF-02 criterion 5 — every count, mask and typed outcome
unchanged, **proved per family**. It runs the Everything lane for all 12
families plus the Direct and classic lanes.

It does **not** re-run the By Day lane, and that is a redundancy removal rather
than sampling: By Day drives the same comparator over the same consolidated
store and the same TSN library as the Everything lane, so a base pass over it
would re-derive numbers already proved for that family and nothing else. **No
family loses its base-vs-head diff.**

HF-03's before/after classification needs no base pass at all — the "before"
table is the committed Stage 2 witness (`stage2-tsn-provenance-scope.json`:
18 workbooks per lane, 12 warned, 18 carrying a `%TEMP%` path) and the "after"
is this run's head, re-derived independently by both of RC-3's methods.

### Early confirmations on real data

The first regenerated matrix-lane workbook already carries every HF-03 outcome
the finding demanded, on the real corpus rather than a fixture:

| Oracle | Pre-fix (audited) | This run |
|---|---|---|
| `Summary by Category!A6` | *"TSN print: no source-claims record beside this normalized workbook (older normalization) — rebuild the TSN library to capture the print identity."* | **`TSN print identity: OTM22270 · Event 4843742 · reference 09/15/2025 · submitted by TRLBUGNI · generated 05:10 PM (STATEWIDE).`** — the exact line the audit's Direct-lane controlled differential recorded |
| occurrences of "rebuild the TSN library" | 1 | **0** |
| `%TEMP%` strings anywhere in the workbook | present | **0** |
| `.provenance.json` TSN `selection` | `…\AppData\Local\Temp\tsmis-tsn-consumer-…\tsn_ramp_summary_normalized.xlsx` | `…\tsn_library\ramp_summary\consolidated\tsn_ramp_summary_normalized.xlsx` — **exists and is readable after the run**, with `read_via: verified private copy of the selection` |
| values twin `Summary!B3` read `data_only` | `None` | `✗ DIFFERENCES FOUND — 23 differing cell(s), 2 one-sided row(s) — details below.` |

**Criterion 1 on real statewide workbooks.** The audit's own gate, run read-only
over three committed workbooks from this run (no Excel, nothing written into the
generated tree):

| Workbook | Stage 2 recorded | This run |
|---|---:|---:|
| `ssor-prod_intersection_summary_tsn.xlsx` | **70** | **0** |
| `ssor-prod_highway_sequence_tsn.xlsx` (the family whose PDF sibling recorded 82) | — | **0** |
| `ssor-prod_intersection_detail_tsn.xlsx` (statewide detail, 29 MB) | — | **0** |

**HF-03 criteria 1 and 3, swept across every deliverable built so far.** The
zip/sheet-XML probe (RC-3 method 1 — never opens the object model) over the 14
comparison workbooks committed by the Everything lane at that point:

```
14 comparison deliverables: false-rebuild=0  temp-path=0
```

and the TSN print identities carried are exactly the codes the audit recorded
for the Direct lane, family by family:

| Family | Identity in the matrix-lane workbook | Audit's Direct-lane control |
|---|---|---|
| Highway Log (both editions) | `OTM52010` | `OTM52010 California State Highway Log · report 09/15/25` |
| Highway Sequence | `OTM22025` | `OTM22025 Highway Locations · report 15-SEP-25` |
| Intersection Summary | `OTM22250` | `OTM22250 · Event 4843738 · 09/15/2025` |
| Ramp Summary | `OTM22270` | `OTM22270 · Event 4843742 · reference 09/15/2025 · TRLBUGNI` |
| Intersection Detail | *(none)* | identity-silent **by design** — the contract requires it gain the honest provenance path but **no invented identity line**, and it has |

**HF-03 criterion 2, as written — the SAME LINE on all three lanes.** Not the
report code: the entire identity string, compared character for character
between the Direct-lane control and both matrix lanes.

| Family | The line, identical on Direct · Everything · By Day |
|---|---|
| Ramp Summary | `TSN print identity: OTM22270 · Event 4843742 · reference 09/15/2025 · submitted by TRLBUGNI · generated 05:10 PM (STATEWIDE).` |
| Intersection Summary | `TSN print identity: OTM22250 · Event 4843738 · reference 09/15/2025 · submitted by TRLBUGNI · generated 04:53 PM (STATEWIDE).` |
| Highway Sequence | `TSN print identity: OTM22025 Highway Locations · report 15-SEP-25 · reference 15 SEP 2025 · 12 district print(s).` |
| Highway Log | `TSN print identity: OTM52010 California State Highway Log · report 09/15/25 · cover year 2025 · 12 district print(s).` |

`ALL 3 LANES IDENTICAL: True` for every one. Before the fix each matrix lane
instead printed *"TSN print: no source-claims record beside this normalized
workbook (older normalization) — rebuild the TSN library to capture the print
identity."* — the categorically false instruction PCOA-FINAL-002 was raised on.

**The audit's worst measured cell — identity widened, instruction wrapped.**
Ramp Summary classic environment, `Summary!B13:B14`, recorded **364 px short**,
the largest overrun in the whole audit. Fitting it by width alone would need a
~93-character column, so the planner's sketch chose wrapping for instructions
and widening for identities. That is exactly what the workbook now does:

```
ramp_summary new-vs-prior-ssor (values).xlsx: 0 materially clipped   (was 5)

Summary column B stored width: 46.0        <- unchanged
  B13: wrap=True  row_height=45.0  "In SSOR-PROD 2026-07-23 only (missing from ..."
  B14: wrap=True  row_height=45.0  "In SSOR-PROD 2026-07-09 only (missing from ..."
  B15: wrap=False row_height=None  'FIELD-LEVEL DISCREPANCIES (matched rows)'
```

`B15` is the control: a short banner in the same column, untouched and still
unwrapped at the default height. Only cells that would actually clip changed,
and the sheet did not get wider.

**Criterion 3 — PCOA-FINAL-014's named test, on the real Highway Sequence vs TSN
workbook.** The finding names `City`, `HG` and `Distance To Next Point`
specifically; the *DIFFERENCES BY FIELD* table now reads:

| Field | Col | # of cells differing |
|---|---|---|
| County | H | `0` |
| **City** | I | **`not compared (context)`** |
| **HG** | J | **`not compared (context)`** |
| FT | K | `690` |
| **Distance To Next Point** | L | **`not compared (context)`** |
| Description | M | `4,883` |

`County` is the control the finding demands: a genuinely COMPARED column with
zero differences still reports a real `0`, so the two cases stay
distinguishable. The compared counts also still reconcile —
`690 + 4,883 = 5,573`, exactly the headline's differing-cell total, which the
values twin now publishes as a stored literal:
`✗ DIFFERENCES FOUND — 5,573 differing cell(s), 15,958 one-sided row(s)`
(criterion 4).

## Evidence is unchanged — proved four ways, not asserted

Both contracts require evidence to be unchanged: HF-02 *"assert evidence
artifacts are unchanged and that no new artifact appears"*, HF-03 *"this bundle
must not create, retire, or relabel any evidence artifact"*. A naive cell diff
of two evidence workbooks does NOT prove that, and would in fact fail — for a
reason that has nothing to do with this bundle. The proof is therefore layered,
and the last layer is a measurement rather than an argument.

**1. The code cannot have changed it.** `git diff 896083e..HEAD --name-only`
lists thirteen files. Not one is an evidence file: `visual_evidence.py`, every
`evidence_*.py`, `published_comparison.py`, `evidence_ledger.py` and
`evidence_manifest.py` have **zero lines changed**. "Created, retired or
relabelled" is settled by inspection alone.

**2. The variation is the product's own, by design.** `visual_evidence.generate`
draws a fresh cryptographic seed per run — `seed = int.from_bytes(os.urandom(4),
"big")` — and stamps it into the workbook as *"sample seed"*. The module's own
docstring states the intent: *"sample random example rows (random routes — not
just the first)"*. Three retained sets carry three different seeds
(`2dbfeb9b`, `2911f7cd`, `76b5e4a3`).

**3. Measured on artifacts that already existed.** Two evidence sets generated by
the **same head code** from the same frozen inputs (the Everything and By Day
lanes) differ by **24 rows**. Head vs base differs by **23**. Identical code
differs from itself MORE than it differs across this change, so the variation
demonstrably is not RB-2.

**4. Remove the randomness and the difference disappears.** The seed alone is not
enough: the candidate pool is a set, so Python's per-process hash randomisation
reorders it. With BOTH `os.urandom` pinned to a fixed seed (`11223344`) and
`PYTHONHASHSEED=0`, the SAME comparison workbook, the SAME source PDFs and one
SHARED staging path, `visual_evidence.generate` was run under each tree:

| Oracle | Result |
|---|---|
| rendered examples / misses | `6 vs 6` / `{} vs {}` |
| artifacts, and their names | 14 vs 14, name sets identical |
| **rendered images byte-identical** | **12 of 12** |
| manifest `read_set` — by content digest | **identical** (13 members each) |
| manifest `ledger_digest` | **identical** — the hash-bound exhaustive ledger built BEFORE any sample is drawn |
| every other manifest key | identical: `comparison`, `difference_cells`, `differing_columns`, `examples`, `images`, `layout`, `note`, `reader_version`, `report`, `seed`, `state`, `version` |
| evidence workbook | **1** differing row |

The two residual differences are recorded **pathnames of the same files**: the
base tree reaches the shared TSN library through a junction, so it records
`…\base-tree\tsn_library\…` where head records
`…\TSMIS-rb2-worktree\tsn_library\…`. The read-set DIGESTS are identical, so the
same bytes were read under both — the names differ, the content cannot. This is
the same worktree-path phenomenon RB-1 documented for four Provenance cells.

Witness: `HF-02\evdet\{head,base}.json` (each run's artifact hashes and note).

## Method note — never measure the live output tree

An early measurement pass ran installed Excel over a workbook **inside** the
generated tree while the generation still held its `owned_dir` lease. Excel
writes lock/temp files beside the workbook it opens, the comparisons directory's
identity changed, and the very next cell refused to commit:

> Refusing to write the comparison: destination ownership changed while …

**The app was right and the measurement was wrong.** The refusal is exactly the
transactional/ownership contract working — a partial refresh kept last-good, and
the app's own identity-bound artifact temp (`…tmp-ed785a1adfa5.xlsx`) was left
rather than a half-written deliverable. The harness now copies every workbook
into a separate `excel-workspace` before any Excel call, and all installed-Excel
legs run only after generation finishes. A reviewer re-running `RB2-A1` must do
the same.

## Scope and residual risk

- **Out-of-scope files changed: none.** The diff is exactly `compare_core.py`, `summary_layout.py`, `matrix_build.py`, `compare_tsn_common.py`, one new check, four existing checks, and this bundle's records.
- **A source with no producer outcome record gets today's behaviour.** The capture's origin record rides the outcome sidecar, which `captured_tsn_workbook` only writes when the source itself has a trusted producer outcome — true for every canonical library workbook and therefore for all 36 matrix-lane workbooks. An explicitly picked file with no sidecar keeps recording the literal path it was read from, which remains honest.
- **The values twin's headline is now build-time state.** That is the finding's own first acceptance branch and the plan's design sketch. The live certification guard did not weaken: the freshness SELF-CHECK row is still live in both flavors, still keyed on both very-hidden E2 snapshot sheets, and now states `REGENERATE REQUIRED` in words. Three policy checks were re-pointed to that cell rather than deleted.
- **Column widths move in every regenerated workbook.** No count, mask, schema version or sidecar changes, so committed comparison generations stay valid and `read_counts`' header-label lookup is unaffected.
