# `HF-01` — Bundle Contract

Status: **DRAFT — AWAITING SECOND PLANNER** (becomes `READY` when both planners
sign [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md))

> This file is transcribed from the HF-01 section of
> [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md), which is the frozen
> contract. Where the two disagree, the plan wins. Only the base `main` SHA and
> the implementer/reviewer names are filled in here at Stage 4.

| Field | Value |
|---|---|
| Queue order | **1 — first implementation bundle** |
| Branch | `hotfix/hf-01-clean-road-source-truth` |
| Base `main` commit | PENDING (the `main` head at branch time; plan drafted against `a29bdb6`) |
| Canonical finding IDs | **PCOA-FINAL-010** (P1) |
| Implementer | Claude |
| First reviewer | **Codex** — non-implementer; holds `source-audit/CLEAN-ROAD-HIGHWAY-RAW-SOURCE-TRUTH-FINAL.md`, `clean-road-highway-raw-source-truth.json`, `CLEAN-ROAD-COMPARISON-UNLOCATABLE-IMPACT.md`, `clean-road-comparison-unlocatable-impact.json` |
| Second reviewer | Claude — challenge pass; must re-derive from source, not ratify review 1 |

## In scope

| Finding ID | User-visible failure | Exact acceptance oracle |
|---|---|---|
| PCOA-FINAL-010 | The Clean Road ArcGIS-vs-TSN workbook shows the ArcGIS side as blank at 165 cells where the raw ArcGIS data demonstrably has values, publishes 161 of them as red differences that are not differences, misrepresents 4 genuine ones, and discloses none of it — while Summary defines red as "ArcGIS ≠ TSN" and `(blank)` as "empty in the system" | "For each of the 102 skipped raw rows, the deliverable either (a) does not publish a difference where the raw ArcGIS value equals TSN, or (b) discloses in Summary/Notes that the ArcGIS side was skipped and why, with the affected count. Assert the 161 false positives fall to zero and the 4 misrepresented cells display the real ArcGIS value or an explicit 'skipped' marker. Re-bless `CRH-SW-E2` with a documented delta." |

**Exact report / workflow / format scope.** Clean Road Highway only — the ArcGIS
build (`clean_highway_built.xlsx`) and the ArcGIS-vs-TSN comparison in **both**
flavors (values + formulas), i.e. Matrix F's 2 decisions.

## Allowed implementation surface

| File or subsystem | Why required |
|---|---|
| `scripts/consolidate_clean_highway.py` | `_read_span_layer:182-184` is the silent skip (`b, e = crl.pm_units(...)` then `if b is None or e is None: continue`); it must record what it dropped and route it into the existing `warnings` channel that `_split_parked:323-328` already uses, and onward to `_write_workbook:974`, the `PARTIAL`/`skipped_inputs` result at `:984-985`, and the `clean_road_build` sidecar at `:988-994` |
| `scripts/compare_clean_highway_tsn.py` | Disclose the skip in the notes writer (`_write_notes_sheet:105-156`) and stop asserting the skipped anchors as differences via `_SCHEMA:158-181` |
| `build/check_clean_road.py` | The hermetic synthetic red→green test (no real data, no network) |
| `scripts/compare_core.py` — **only** one additive opt-in `CompareSchema` field, if the chosen design needs it | A per-cell non-asserting display state. Precedent: the per-cell ditto `N` at `compare_core.py:1648-1650`. Must be inert for every schema that does not set it |
| `docs/planning/comparison-perfection/comparison-canary-bindings.md` | The mandatory `CRH-SW-E2` re-bless with a documented delta |

Anything outside this table is scope leakage and a reviewer must reject it.

## Explicitly out of scope

- The ArcGIS build **rule** — proved rule-faithful over 57,728 rows / 252 routes /
  74 fields / 4,271,872 cells; the finding states the rule is not the defect.
- Odometer- or AR-based span placement. The build model keys on county + PM
  prefix + postmile and **never** on odometers (three calibrations exist), so
  placing a missing endpoint from AR measures is forbidden guessing.
- Clean Road **Intersection** and **Ramp** (DEF-05 — no normalizer; the library
  rebuild refuses both by design).
- The 5 landmark representation-only cells → **HF-09**.
- Clean Road workbook clipping → **HF-02** (PCOA-FINAL-009 covers Clean Road).
- The 74-column header, the 24-column context set, `CONTEXT_FIELDS`, and
  `context_header_fill` (v0.32.0, CRH-SW-E2-neutral).
- Any other report family, any other comparison workflow, evidence generation.

## Verified root cause

`consolidate_clean_highway._read_span_layer` drops any as-of span whose begin
**or** end PM measure is unusable and — unlike `_split_parked`, which appends a
warning for a cross-county span it cannot split — records nothing. The dropped
span therefore never reaches `warnings`, never downgrades the build to `PARTIAL`,
never appears on the marker sheet or in the `clean_road_build` sidecar, and never
reaches the comparison's Summary or Notes. 102 current raw rows marked
`LocError=NO ERROR` have usable AR measures and one missing PM endpoint; the
no-guess contract omits their values at the affected anchors, and the comparison
then classifies those blanks as differences: **161 exact false positives**
(visible TSN value equals the skipped ArcGIS raw value) and **4 genuine
differences misrepresented** (route 036 / TEH / 40.15 and 40.352 — TSN `2/24`,
raw ArcGIS `1/12`, workbook shows ArcGIS blank), spanning 165 `D` cells / 83
comparison rows / 87 source endpoints; 162 display a blank ArcGIS side and three
an older or alternate value.

## Design gate (resolve before coding)

Two acceptance branches exist and only one satisfies both sentences of the
oracle:

- **Recommended — suppress + disclose.** (i) `_read_span_layer` records each
  unusable-PM span with its layer, route, county, prefix and the measures it did
  have; (ii) the marker sheet, result message, `PARTIAL` completion and sidecar
  carry the count and reason; (iii) the affected anchors are emitted with a
  reserved *unavailable* token instead of an empty cell and the schema declares
  that token **non-asserting**, so those cells render `N`, show the reason, and
  leave the difference count; (iv) Summary and Notes state the skipped-source-row
  count, the affected anchor count and why.
- **Fallback — disclosure only**, if the owner refuses any engine hook. This
  satisfies oracle branch (b) but leaves the 161 visible; the reviewer must then
  record explicitly that the oracle's second sentence is unmet.

The implementer records which branch the owner ruled for in `IMPLEMENTATION.md`
before changing comparison output. If the verified root cause or the required
design differs materially from this section, **stop and return the bundle to
Stage 3** rather than expanding scope (Prompt 04 rule).

## Migration and compatibility

- The build workbook gains a marker-sheet/sidecar field. `tsn_load_clean_road`'s
  normalizer and its `v1` marker are untouched, so a previously built workbook
  must still compare — or be refused with a message that names the rebuild.
- Any comparison-visible change moves the blessed statewide canary
  **`CRH-SW-E2`** (52,647 / 5,081 / 7,436 paired · 291,292 differing cells). The
  re-bless is mandatory, documented with exact input/output evidence, and must
  honor the
  [Phase-3 decision gates](../../../comparison-perfection/comparison-phase3-decision-gates.md)
  and the `compare_core` correctness lock.
- `main` must stay releasable: the ArcGIS tab must build and compare end to end
  after this bundle with no half-migrated workbook state.

## Required verification matrix

| Gate | Required commands / outputs | Approval rule |
|---|---|---|
| End-user path | GUI **ArcGIS tab** → build Clean Road Highway from `arcgis_layers/` at the TSN extract's own as-of date → compare vs the TSN `CA HIGHWAYS` extract, `mode="both"`. Drive the shipped GUI/worker path, not `consolidate()`/`compare()` directly | Generated as a user would generate it; assertions are on the written files |
| Values deliverable | Both twins regenerated; values twin read `data_only=True` | 161 false positives → **0**; the 4 misrepresented cells show the real value or an explicit skipped marker; no genuine difference lost |
| Formula deliverable | Recalculate the formulas twin in installed Excel | Every SELF-CHECK row `OK`, no `#REF!`/`#VALUE!`, semantically equal to the values twin on every changed cell class |
| Source-truth recount | App-free reader joining each visible ArcGIS row's `Key (helper)` to the Comparison sheet's hidden `__CMP_E2_KEY_V1_TOKEN`, inferring no missing span; restate statewide totals | The 165-cell before/after set reproduces the finding exactly pre-fix, and the post-fix total equals 291,292 minus exactly the itemized false-positive delta |
| Visual usability | Inspect *Summary*, *Notes*, *Comparison*, *ArcGIS Build*, *Provenance* at native scale | Disclosure legible in its stored width; grey context headers unchanged; skipped-anchor display unambiguous; nothing newly clipped |
| PDF/Excel sibling parity | n/a — Clean Road has no PDF edition | n/a, stated explicitly |
| PDF/PDF evidence | n/a — Clean Road has no evidence adapter | **Prove zero evidence artifacts** before and after |
| Mixed-format evidence | Same | No evidence leakage of any kind |
| Canary | `CRH-SW-E2` re-blessed in `comparison-canary-bindings.md` | Documented delta with exact input/output evidence |
| Regression | Full gate: `build\.venv\Scripts\python.exe build\run_checks.py -j 4 -k`, `compileall`, `ruff`, `build.ps1 -SelfTest`; plus `check_clean_road.py`, `check_compare_equality_policy.py`, `check_compare_audit.py`, `check_comparison_artifact_schema.py`, and — if the `CompareSchema` hook is used — `check_compare_ditto.py` and one unaffected family (Intersection Summary vs TSN) proved byte-identical to its pre-fix twin | Never a subset of the gate (v0.17.3 lesson). Unrelated approved behavior unchanged |

**New test (must fail on the base commit).** In `build/check_clean_road.py`, on
the synthetic mini-library: a span row with one unusable PM endpoint and usable
AR/odometer measures must (a) appear in the build's skip record, (b) make the
build report `PARTIAL` with non-zero `skipped_inputs`, (c) surface on the marker
sheet and in the sidecar, and (d) in a real `mode="both"` comparison against a
TSN row carrying the same value, **not** produce a counted difference — while a
genuinely differing anchor still does.

## Measurable acceptance criteria

1. The 161 exact false positives are **0**.
2. The 4 misrepresented cells show the real ArcGIS value or an explicit skipped
   marker — never an unqualified blank.
3. Summary **and** Notes state the skipped-source-row count, the affected anchor
   count, and the reason (`LocError=NO ERROR` rows with a missing PM endpoint).
4. Both twins regenerate; the formulas twin recalculates clean in installed Excel.
5. `CRH-SW-E2` re-blessed with a documented delta and exact evidence.
6. Full gate green; `check_clean_road.py` fails pre-fix and passes post-fix.
7. No genuine difference disappeared: the post-fix differing-cell total equals
   291,292 minus exactly the proved false-positive delta, itemized.

## Dependencies and rollback

- Prerequisite merged bundles: **none** — HF-01 is first.
- Regression surface: Clean Road Highway only for code; the shared
  `compare_core` hook (if used) must be proved inert for every other schema.
- Findings to verify but **not** re-implement here: PCOA-FINAL-009 (Clean Road
  clipping, still open until HF-02 — quote the finding's numbers, do not
  re-measure) and PCOA-FINAL-013 (the 5 landmark cells stay literal).
- Rollback method: revert this bundle's merge commit. The build workbook is
  regenerated on demand and no persisted comparison schema version changes, so a
  revert needs a rebuild, not a data migration.

## Retained output and witness locations

| What | Where |
|---|---|
| Bulk: both twins, the built workbook, the recount workspace | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\` |
| Committed machine-readable witness: skip census, the 165-cell before/after join, statewide recount totals | `hotfix-bundles/HF-01/witness/` |
| Never | Any Stage 1/2 audit root — audit evidence is immutable. No real TSMIS data in the repo |

## Scope approval

| Planner | Decision | Commit / date |
|---|---|---|
| Claude (first plan) | **DRAFTED — AWAITING SECOND PLANNER** | this commit / 2026-07-26 |
| Codex (final challenge) | NOT STARTED | PENDING |
