# P15 — Intersection Detail vs-TSN comparison-behavior forward-port (v0.17.8) — Claude report

## 1. Phase ID and name
**P15 — Intersection Detail vs-TSN comparison-behavior forward-port** (CR-002 / CR002-RM3/RM5).
Re-applies the localized v0.17.5–v0.17.8 comparison evolution onto the refactored
`compare_intersection_detail_tsn` — to its **final v0.17.8 state** (the handoff §9e supersedes
§8/§9d) — plus the matching §9b Summary signal fold. Source: `origin/main` `068b697` (v0.17.8),
a deliberate forward-port (not a merge).

> **`compare_core.context_fill` was NOT ported (CR002-RM3).** v0.17.8's final Intersection Detail
> schema dropped its only use of `context_fill`; it compares the formerly-greyed date columns and
> uses the EXISTING `extra_sheet_writer` opt-in for the Report View. `scripts/compare_core.py` is
> **byte-for-byte unmodified** by this phase (verified: `git diff scripts/compare_core.py` = 0 lines;
> `git grep context_fill` over the tree = 0 occurrences). The `compare_core` regression lock is intact.

## 2. Baseline commit
`380b7e8` (P14, "forward-port the Intersection Detail (PDF) report family"). Branch
`refactor/v0.18.0-structural-overhaul`; clean tree apart from the untracked `docs/planning/`.
Pre-change characterization green at baseline: both vs-TSN Intersection canaries +
`check_compare_audit` + the env/consolidate Intersection checks + `check_intersection_detail_pdf`.
HEAD is **unchanged** by this phase (not committed — awaiting Codex review).

## 3. Changes made
- **`compare_intersection_detail_tsn.py` — the final v0.17.8 state.** Position-aligned date columns
  (the 33-column `SHARED_HEADER`; `_TSN_COL`/`_TSMIS_POS` map each report column to the SAME column
  in the other report — ML/CS 1st eff-dates → geometry `EFF_DATE_ML`/`CROSS_BEGIN_DATE`, ML 2nd/Int
  St → recent `MAIN_EFF_DATE`/`EFF_DATE`; the intersecting-route PM suffix at pos 35); the
  J–P→Signalized control crosswalk (`_norm_control_type` + `_SIGNALIZED_LABEL = "S"`); the
  compare-everything policy (`CONTEXT_FIELDS = ()` — nothing greyed/suppressed); numeric-padding
  normalization (`_norm_num` + `NUMERIC_FIELDS`); read-time TSN-library re-normalization
  (`_normalized_row` on the `_load_tsn` normalized-sheet path — the "Signalized ≠ P" stale-library
  repair); the inline sectioned Notes sheet; and the **"Report View"** two-line replica via the
  EXISTING `extra_sheet_writer` opt-in (a per-call `dataclasses.replace` of the base schema), with
  the write-only techniques preserved (`merged_cells.ranges.add(CellRange(...))`,
  `WriteOnlyCell.comment`, `freeze_panes` set BEFORE the streamed rows).
- **Adapted to the refactored structure (P5b), not `origin/main`'s.** Kept `import compare_tsn_common
  as ctc`: `_norm_pm = ctc.norm_pm`, `_iso_date = ctc.iso_date`, and `compare()` delegates to
  `ctc.run_files_compare(...)` with `_load_pair` (like the other four vs-TSN file comparators), rather
  than the inline `run_compare` body v0.17.8 shipped. The Report View is attached via the per-call
  schema's `extra_sheet_writer`.
- **`summary_layout.py` — the §9b signal fold.** `_CONTROL_SIGNAL_FOLD` (J–P → `S`) applied inside
  `counts_from_rows` for BOTH sides; the J–P category rows removed; `S` relabeled "SIGNALIZED (incl.
  TSN J-P)" and marked `both`; `MAINLINE NUM OF LANES +` flipped to `both`; `_IS_TSN_ONLY = set()`;
  new `SummarySpec.notes` rendered on the familiar sheet.
- **`compare_intersection_summary_tsn.py` — the §9b read-time fold.** `_slug_for_key` folds stale
  J–P + old `S - SIGNALIZED` library keys into the Signalized slug, and `_load_tsn` SUMS (not
  overwrites) so a reused pre-fold normalized library still compares correctly.
- **`compare_intersection_detail_pdf.py` — no edit needed.** It reuses `_id._SCHEMA`/`_load_tsmis`/
  `_load_tsn`, so the PDF-vs-TSN + PDF-vs-Excel comparators automatically inherit the evolved schema
  (the position-aligned mapping, the `S` crosswalk, the numeric norm). No Report View on the PDF
  comparators (the base schema's `extra_sheet_writer` is None; only the direct `compare()` adds it) —
  matching v0.17.8.
- **Canaries re-blessed to v0.17.8** (`check_compare_intersection_detail_tsn`,
  `check_compare_intersection_summary_tsn`) + two consequential check updates (`check_compare_tsn_common`
  notes-delegation, `check_tsn_normalizer` frozen header).

## 4. Files affected
**Product (3):** `scripts/compare_intersection_detail_tsn.py` (+656/−), `scripts/summary_layout.py`
(+55), `scripts/compare_intersection_summary_tsn.py` (+41). **Checks (4):**
`build/check_compare_intersection_detail_tsn.py`, `build/check_compare_intersection_summary_tsn.py`
(both re-blessed to v0.17.8), `build/check_compare_tsn_common.py` (notes-delegation reconciliation),
`build/check_tsn_normalizer.py` (frozen `_ID_HEADER` re-bless). Total **7 files, +911/−146**.
**Untouched (protected):** `scripts/compare_core.py` (0 diff — RM3), `version.py` (0 diff — RM6),
`compare_intersection_detail_pdf.py` (reuses the evolved schema), and every OTHER vs-TSN comparator.

## 5. Architectural decisions
- **Forward-port behavior onto the refactored module, not revert to `origin/main`'s structure (RM7).**
  Pulled the exact v0.17.8 bytes (`git checkout origin/main`) for correctness, then re-applied the P5b
  `ctc` delegation (shared `norm_pm`/`iso_date`/`run_files_compare`) so the Intersection Detail
  comparator stays consistent with the other four vs-TSN file comparators.
- **The Report View rides the EXISTING `extra_sheet_writer` opt-in — `compare_core` untouched (RM3).**
  `compare()` builds a per-call schema with `dataclasses.replace(_SCHEMA, extra_sheet_writer=…)`; the
  refactored `compare_core` already passes the writer a `{rows_a, rows_b, sc, …}` context that the
  Report View consumes. No core change; no `context_fill`.
- **The Notes sheet legitimately outgrew the shared `make_notes_writer`.** v0.17.8's Notes sheet has
  SECTIONS (normalizations applied / columns that differ wholesale / Report View) the flat shared
  helper can't express, so Intersection Detail keeps its own inline `_write_notes_sheet`; Highway
  Sequence still uses `ctc.make_notes_writer`. `check_compare_tsn_common` was updated to assert this
  (the detail module has its own sectioned writer; the shared one stays for the simpler reports).
- **`SHARED_HEADER` changed deliberately (21 → 33 cols), so the frozen `_ID_HEADER` tripwire in
  `check_tsn_normalizer` was re-blessed** by hand (kept independent of `idt.SHARED_HEADER` so future
  drift is still caught). The TSN library normalizer (`tsn_load_intersection_detail`) auto-derives
  from `idt.SHARED_HEADER`, so it produces the new shape with no module edit.

## 6. Compatibility and migration handling
- **Stale TSN library (read-time repair).** A normalized library built BEFORE this evolution is
  REUSED (not rebuilt) by `tsn_library`. The Detail's `_normalized_row` re-projects each library row
  through `_project` at compare time (idempotent on a fresh library; repairs a stale one — raw `P`/`J`
  → `S`), and the Summary's `_slug_for_key` folds stale J–P/`S - SIGNALIZED` keys into the Signalized
  slug (summed). So a normalization change takes effect immediately, no rebuild required. Locked by
  `test_normalized_path_crosswalk` (Detail) + `test_stale_library_fold` (Summary).
- **No persisted-format migration.** The comparison workbooks are regenerated on demand; the TSN
  library normalized workbook gains columns when next rebuilt (and reads correctly when stale).
- **Other reports unaffected.** The §9b fold is gated to the `CONTROL TYPES` block, so Ramp Summary
  (no such block; default-empty `notes`) is byte-identical. The `CONTEXT_FIELDS = ()` policy is
  Intersection-Detail-specific — Ramp Detail / Highway Sequence keep their context fields (canaries green).

## 7. Tests and commands run
- Byte-compile: `python -m py_compile scripts/*.py build/*.py` → clean.
- **The two v0.17.8 canaries:** `check_compare_intersection_detail_tsn` (schema; position-aligned
  mappings; `S` crosswalk; `context_fields == ()`; the base schema's `extra_sheet_writer` is None;
  Report-View locks `_RV_FILLS["soft"] == ["hard"]`, normal band white, `_rv_classify` soft/hard;
  end-to-end: Notes + Report View sheets present, the 9 synthetic diff cells, the normalized-path
  crosswalk, the added columns) and `check_compare_intersection_summary_tsn` (66 categories, the
  J–P→S fold, 58 both / 8 only-TSMIS / 0 only-TSN, the stale-library fold).
- **The Codex P15 list:** the Int-Detail vs-TSN detail canary; the Int-Summary summary/fold canary;
  the PDF-vs-TSN + PDF-vs-Excel adapter check (`check_intersection_detail_pdf`); `check_compare_audit`
  + the Highway Log (`check_highway_log_columns`/`_ditto`/`_roadbed`), Ramp (`check_compare_ramp_detail_tsn`/
  `_ramp_summary_tsn`), Int-Summary, and Int-Detail comparison regression checks — all green.
- **Full on-disk suite:** **73/74 `build/check_*.py`** + **3/3 Node** (the lone failure is the
  pre-existing untracked `P10-codex-review.md` rg-literal carrying the transposed name; tracked
  content clean via `git grep`).
- Diff hygiene: `git diff scripts/compare_core.py` = 0 lines; `git diff version.py` = 0 lines;
  `git grep context_fill` = 0; no dangling `run_compare`/`Events`/`ConsolidateResult` refs after the
  ctc swap.

## 8. Results
- All targeted + regression checks green. **`compare_core` proven unmodified** (the central RM3
  guarantee). The PDF comparators inherited the evolution with no edit. Two consequential check
  reconciliations (notes-delegation, frozen header) were required by the v0.17.8 behavior and applied.
- Two regressions surfaced during verification and were fixed before completion:
  `check_compare_tsn_common` (asserted the detail module uses `make_notes_writer`; now asserts its own
  sectioned writer) and `check_tsn_normalizer` (the frozen `_ID_HEADER` tripwire; re-blessed to the
  33-col layout). Both are honest reconciliations of a deliberate v0.17.8 change, not workarounds.

## 9. Before/after measurements
| Aspect | Before (HEAD `380b7e8`) | After (P15) |
|---|---|---|
| Detail `SHARED_HEADER` | 21 columns (v0.17.1) | 33 columns (position-aligned, v0.17.8) |
| Detail `CONTEXT_FIELDS` | 7 (PR, Date of Record, 5×CS) | `()` — nothing suppressed |
| Detail control label | (no crosswalk) | J–P + S → `S` (Signalized) |
| Detail Report View | none | the two-line replica (via `extra_sheet_writer`) |
| Detail read-time re-norm | none | `_normalized_row` (stale-library repair) |
| Summary categories | 72 (J–P split one-sided) | 66 (J–P folded into Signalized) |
| Summary one-sided split | 56 both / 10 TSMIS / 6 TSN | 58 both / 8 TSMIS / 0 TSN |
| `compare_core` | (locked) | **unchanged (0 diff)** |

Diff: **7 files, +911/−146.** Statewide canaries (real-data, v0.18.1 acceptance): Excel-vs-TSN
**163,353** / PDF-vs-TSN **163,361** — see §11.

## 10. Deviations from the approved plan
None material. The plan §I anticipated touching `compare_intersection_detail_tsn`,
`compare_intersection_summary_tsn`, `summary_layout`, and the two canaries. Two additional check
updates (`check_compare_tsn_common`, `check_tsn_normalizer`) were necessary consequences of two
in-scope v0.17.8 changes — the inline sectioned Notes sheet and the 33-column header — not scope
expansion. `compare_intersection_detail_pdf` needed no edit (it reuses the evolved schema, exactly as
§I expected: "where it reuses the evolved detail schema/loaders").

## 11. Known limitations and external verification
- **The statewide canaries (163,353 Excel / 163,361 PDF) are real-data figures, NOT offline-verifiable
  (RM04).** They were reconciled on LOCAL ground truth under `Downloads\TSMIS\…`, never in CI. The
  offline canary locks the SCHEMA + the per-cell normalization/diff behavior on synthetic rows + the
  Report-View structure (which IS what CI can prove). Real-PDF/Excel/TSN correctness acceptance — the
  163k counts, the Report-View visual fidelity against the printed PDF, the live matrix vs-TSN — is
  **v0.18.1 (P13)**, the same footing as the other PDF/TSN reports.
- **The Report View is exercised offline by the canary's end-to-end test** (it asserts the sheet is
  appended and the classification/palette locks hold) but on synthetic 2-row data; the full statewide
  render is v0.18.1.

## 12. Exact diff scope Codex should review
- **`compare_intersection_detail_tsn.py`** — confirm the v0.17.8 behavior is faithful (position-aligned
  `_TSN_COL`/`_TSMIS_POS`; `_norm_control_type`/`_SIGNALIZED_LABEL`; `_norm_num`/`NUMERIC_FIELDS`;
  `CONTEXT_FIELDS=()`; `_normalized_row`; the Report View `_RV_*` + `_write_report_view` write-only
  techniques) AND that the P5b `ctc` structure is preserved (ctc aliases + `ctc.run_files_compare` +
  `_load_pair`; no direct `run_compare`); the base `_SCHEMA.extra_sheet_writer` is None (per-call only).
- **`summary_layout.py` + `compare_intersection_summary_tsn.py`** — the §9b fold (gated to CONTROL
  TYPES; Ramp Summary byte-identical) + the read-time `_slug_for_key` sum.
- **The re-blessed canaries** — that the new expectations match v0.17.8 (66 cats / 58·8·0; the detail
  9-diff synthetic case; the frozen `_ID_HEADER` 33-col re-bless; the notes-delegation reconciliation).
- **The protected boundary:** `git diff scripts/compare_core.py` = 0 (RM3 — no `context_fill`), the
  Route-1 HL canary + every other vs-TSN comparator green, `version.py` untouched.
- **Not in scope:** `compare_core` (unchanged), `compare_intersection_detail_pdf` (reuses the schema,
  no edit), and the docs/CHANGELOG (folded into P11).

---

## Remediation — Round 1 (Codex `PASS WITH FIXES`)

**Review round addressed:** P15 Codex review round 1 (verdict `PASS WITH FIXES`; 0 blocking, 1 required, 0
non-blocking). The original report above is unchanged.

### Finding dispositions

| Finding | Disposition | Notes |
|---|---|---|
| **P15-R01** (Required) — stale Intersection Detail control-type/context wording | **Fixed** | The forward-ported v0.17.8 source carried §8-era comments/docstrings/Notes text that the §9d/§9e behavior changes invalidated (a real doc-drift that shipped on `origin/main`). All corrected to the actual contract; **no behavior change**, so the already-green canary stays green. |

### Remediation changes

P15-R01 was a wording-only correction to `scripts/compare_intersection_detail_tsn.py` — the **comparison
semantics are unchanged** (the canary already asserts the Control Type cell equals `"S"`, and
`CONTEXT_FIELDS == ()`; only the prose contradicted it). Six locations fixed:

1. **Module docstring** (the §2 "Control-type crosswalk" note) — "normalized to one readable 'Signalized'
   category … the word 'Signalized' makes the merge visible" → "normalized to that one code **'S'** (the
   Signalized category)". The cell shows `S`, not the word "Signalized".
2. **`SHARED_HEADER` comment** — "Every field … is compared **EXCEPT the two CONTEXT_FIELDS** below" → "compared
   and counted — **nothing is suppressed** (CONTEXT_FIELDS is empty; the position-aligned policy compares every
   column)". (The "two context fields" were dropped in §9e; the comment was stale.)
3. **The `_SIGNALIZED_*` constants comment** — "the compared Control Type **shows the word 'Signalized'**" →
   "the compared Control Type cell **shows 'S'** wherever the crosswalk applied".
4. **`_norm_control_type` docstring** — "fold into the single readable category 'Signalized' … the word
   'Signalized' vs the raw letter codes" → "fold into the single code **'S'** (the Signalized category) … the
   compared cell therefore shows 'S'".
5. **`_normalized_row` docstring** — "phantom **'Signalized ≠ P'**" → "phantom **'S ≠ P'** (a fresh library
   shows the crosswalked code 'S', a stale one the raw 'P')"; the crosswalk named J–P→`S`.
6. **The user-visible Notes-sheet text** (`_write_notes_sheet`) — "normalized to the single readable category
   'Signalized'. HOW TO SEE IT: wherever the Control Type cell **reads the word 'Signalized'**" → "normalized to
   that single code **'S'** (the Signalized category). HOW TO SEE IT: wherever the Control Type cell **reads
   'S'** (a single code that may be a folded TSN J–P)".

**Scope guard:** `compare_core` untouched, `context_fill` not introduced, comparison semantics unchanged
(RM3). The **Summary** side is unaffected — its `S - SIGNALIZED` value is a *category label* (correct per the
handoff §9e: "the Summary keeps its `S - SIGNALIZED` category label; only the Detail's per-cell control value
changed"), so no Summary wording was altered. The Report View's `_RV_COMMENTS["Control Type"]` ("all fold to
'S' (signalized) …") was already correct and left as-is.

### Updated verification

- `python -m py_compile scripts/compare_intersection_detail_tsn.py` → clean (the docstring/Notes edits are
  syntactically valid).
- Codex-required re-runs: `check_compare_intersection_detail_tsn` **PASS**, `check_compare_tsn_common` **PASS**.
  The Notes-sheet wording is **not** test-locked (the canary asserts only that the `Notes` sheet exists, not its
  text), so the wording fix needed no canary update.
- Full on-disk suite re-run: **73/74 `build/check_*.py`** + **3/3 Node** green (the lone failure remains the
  pre-existing untracked `P10-codex-review.md` rg-literal; tracked content clean).
- Protected boundary re-confirmed: `git diff scripts/compare_core.py` = **0 lines**; `git grep context_fill`
  over the tree = **0**; `version.py` untouched.

### Changed measurements

None. The remediation is documentation/comment text only — the 33-column schema, the `S` crosswalk, the
`CONTEXT_FIELDS=()` policy, the diff counts, and all canary expectations are identical to the original report.
The product diff grows by the corrected comment/Notes lines in the single file `compare_intersection_detail_tsn.py`
(no new/removed files; the 7-file touch set is unchanged).
