# `RB-1` — Implementation Record

Status: **IMPLEMENTED — AWAITING ADVERSARIAL REVIEW**

| Field | Value |
|---|---|
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-1-clean-road-source-truth` (worktree `C:\Users\Yunus\Projects\TSMIS-rb1-worktree`; the user's `main` checkout untouched) |
| Base `main` commit | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` (plan drafted against `a29bdb6`; the delta is the Stage 3 planning docs only) |
| Implementation commit | `93e12c23a8eeb8686817248d662e4d30125de0ec` (+ this SHA-recording follow-up) |
| Generated-output root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\` (bulk); committed machine-readable witnesses in `../HF-01/witness/` |

## Changes

| File | Change | Finding IDs |
|---|---|---|
| `scripts/consolidate_clean_highway.py` | `UNAVAILABLE_TOKEN` constant. `_read_span_layer` now RECORDS every as-of span whose begin or end postmile is unreadable (`_skipped_span_record`: layer, route, county, prefix, the one known endpoint, OD + AR measures, `LocError`, the attribute values — read via the new optional `_SKIP_DETAIL_COLS`), instead of silently `continue`-ing. `_skip_warning` renders one itemized line per span (values included) into the existing `warnings` channel, so the marker sheet, `PARTIAL` completion, `skipped_inputs`, the sidecar and the result message all light up through the machinery `_split_parked` already used. `_mark_unavailable_anchors` writes the token into each skipped span's anchor cells — the built row containing the span's one known endpoint (begin anchors `b <= s < e`, end anchors `b < s <= e`), on the roadbed kinds that layer paints (`_skip_kinds` mirrors `_paint_row`), in its direct value columns (`_TAG_MARK_COLUMNS`), and ONLY where the painted value differs from the span's own projected value (`_skip_value` mirrors `_seg_code`/`_seg_num`/City) — a value corroborated by a placeable span is source truth, not an omission. Cell-first evaluation credits every co-anchored span against the ORIGINAL painted value. The marker sheet gains `Skipped source spans` / `Marked anchor cells` / `Unavailable marker` rows; the sidecar gains `clean_road_build.skipped_source_spans` (count, marked cells, reason, marker, per-span records); the result message names the marked-anchor count | PCOA-FINAL-010 |
| `scripts/compare_core.py` | ONE additive opt-in `CompareSchema` field: `unavailable_rule: tuple = ()` (`(token, Summary note)`), plus the `unavailable_token` property. Gated behavior (all inert when unset — the default and ditto-only formula strings are byte-identical): `compared_cell` marks a cell whose ASCII-TRIMmed value equals the token on either side NON-ASSERTING (state `N`, display = side A per the ditto convention); `_matched_state_expr` adds the formula twin (`EXACT(trim, token)` OR-branch), which also covers Spot Check's independent recompute; `_write_summary` renders the schema's resolved disclosure note; `run_compare` validates the pair shape. Precedent: the per-cell ditto `N` | PCOA-FINAL-010 |
| `scripts/compare_clean_highway_tsn.py` | Imports `UNAVAILABLE_TOKEN` from the producer. `_NOTES_TITLE`/`_NOTES_LINES` restructure (same content). `_build_skip_facts` reads the built workbook's marker counts — an older or skip-free build returns `(0, 0)` and gets the plain module schema, so previously built workbooks still compare byte-identically. `_schema_for` builds the per-run schema via `dataclasses.replace`: `unavailable_rule` with the resolved Summary note (102 / 174 / reason) + a Notes writer with `_disclosure_lines` PREPENDED (the disclosure cannot be buried under the 74-line column table). `compare()` uses it | PCOA-FINAL-010 |
| `build/check_clean_road.py` | `test_skipped_span_source_truth` — the hermetic red→green test (synthetic library, no real data): a span with one unreadable PM endpoint and usable OD/AR measures must (a) appear in the skip record (sidecar + marker + per-span exact counts), (b) make the build `PARTIAL` with non-zero `skipped_inputs`, (c) surface on the marker sheet, and (d) in a real `mode="both"` comparison: token vs the span's own value → `N` (the false-positive class), token vs a different value → `N` (the misrepresented class), a correctly placed genuine difference stays `D` and is the only counted cell. Covers begin- and end-anchors, kind eligibility (an R-row anchor), the matches-raw no-mark rule, the marker/token display, the Summary + Notes disclosures, the merged producer-partial note, old-build compatibility, and the skip-free COMPLETE control. `_build_library` gains the `extra=` fixture hook + a `LocError` column; `getattr` fallbacks make the base-commit run fail with semantic FAILs, not a crash | PCOA-FINAL-010 |
| `docs/planning/comparison-perfection/comparison-canary-bindings.md` | **CRH-SW-E3** re-bless (supersedes CRH-SW-E2's expected counts) with the exact input identities and the three acceptance legs | contract requirement |
| `docs/planning/post-comparison-perfection-output-audit/hotfix-bundles/RB-1/BUNDLE.md` | Base `main` SHA filled; status | — |
| `docs/planning/post-comparison-perfection-output-audit/IMPLEMENTATION-PLAN.md` | RB-1 status → `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW` (queue + coverage + HF-01 rows together) | — |
| `hotfix-bundles/HF-01/witness/` | `skip-census.json` (the 102 spans from the build's own sidecar), `165-cell-before-after-recount.json`, `build-diff.json`, `is-regression.json`, `formulas-twin-recalc.json`, `four-raw-source-disagreements.json` | — |

## Root cause confirmed

Exactly as the bundle states: `_read_span_layer`'s `if b is None or e is None: continue`
dropped the span with no record. The 102 affected raw rows (100 `SHS Travel Way L`
route 036, 2 `SHS O Shld Width R` route 016; all `LocError=NO ERROR` with usable
AR/odometer measures) were re-detected by the fixed build at exactly the witnessed
counts, per layer and per anchor class. No material deviation from the plan was found;
scope was not expanded.

## Design as ruled (owner, 2026-07-26 — option (a), mark the skipped anchors)

1. Every unusable-PM span recorded with its layer, route, county, prefix and the
   measures it did have — including the AR/odometer measures the no-guess contract
   refuses to place by, and the attribute values, itemized per span on the
   `ArcGIS Build` sheet and in the sidecar.
2. Marker sheet, result message, `PARTIAL` completion, `skipped_inputs=102` and the
   `clean_road_build` sidecar carry the count and the reason.
3. The affected anchors emit the reserved token `(unavailable: source span skipped)`;
   the schema declares it non-asserting via the ONE opt-in `CompareSchema` field —
   all 165 paired-row cells render `N`, display the marker, and are excluded from the
   differing-cell count. Inert for every schema that does not set it (proved, see below).
4. Summary AND Notes state the skipped-source-span count (102), the marked-anchor
   count (174) and the reason (`LocError=NO ERROR` rows with a missing PM endpoint).

Anchor semantics reproduce Codex's exact-anchor join: the output row containing the
span's one known PM endpoint; token only where the painted value is not the span's
own (the 20 witnessed matches-raw cells stay untouched); no position ever inferred
from AR/odometer calibration; the one endpoint with no covering row (TEH/L 0.017)
stays record-only.

## Verification results

| Contract gate | Command / method | Artifact | Result |
|---|---|---|---|
| End-user path | The real `gui_worker.ConsolidateWorker` driving the exact `start_arcgis_build` / `start_arcgis_compare` + `_begin_compare`/`_launch_compare` closures (source capture, alias gates, `paths.arcgis_comparisons_dir()` destination, the shipped `_comparison_overwrite_authorizer`), headless queue + cancel event; only the native dialogs are replaced by their recorded decisions | `HF-01\build_log2.txt`, `compare_log.txt` | **PASS** — build `status=ok completion=partial skipped_inputs=102`, 57,728 rows / 252 routes; comparison `status=ok completion=partial`, both twins committed |
| Values deliverable | App-free lockstep recount of the retained pre-fix values twin vs the new one (openpyxl only; witness-driven) | `witness/165-cell-before-after-recount.json` | **PASS** — old 291,292 → new **291,127**; all **165** witnessed mask flips `D`→`N` AND display flips (old text == witness, new == token); the **9** one-sided anchors display the token at state `U`; per-field deltas exactly **−82 / −81 / −1 / −1**; statuses/keys/Diffs/rows: **zero unexpected changes** across all 65,164 rows; ArcGIS data sheet: exactly the 174 tokens, nothing else; TSN data sheet: identical |
| Build-level source truth | Cell diff of the new build vs the frozen audit-approved pre-fix build (SHA `8F9766AC…`) | `witness/build-diff.json` | **PASS** — same 57,728-row universe; **174/174** tokens at the witnessed positions; **0** other cell changes; marker delta purely additive |
| Formula deliverable | Installed-Excel `CalculateFullRebuild` + Save, then app-free read of the cached results | `witness/formulas-twin-recalc.json` | **PASS** — verdict "✗ DIFFERENCES FOUND — 291,127 …, 12,517 one-sided"; live Diffs sum 291,127; all 165 positions live-`N` with the token; every SELF-CHECK OK; 0 error cells on Summary/Spot Check/Comparison; both disclosure notes present |
| Source-truth recount | Statewide totals restated independently | same | **PASS** — 52,647 paired / 5,081 ArcGIS-only / 7,436 TSN-only / 50,012 differing rows / 2,635 identical (all unchanged); 291,127 = 291,292 − 165 exactly |
| Visual usability | Native-Excel PDF renders inspected: Summary (headline + counts + per-field + the notes block), Notes (disclosure first), Comparison (TEH 40.15/40.352 window), built `ArcGIS Build` sheet, Provenance | `HF-01\*.pdf` (retained) | **PASS** — the token cells are visibly distinct from red `≠` difference cells and excluded from row Diffs; the disclosure lines read fully; grey context headers unchanged; Provenance names real durable paths + both input shas + "producer completion: partial" |
| PDF/Excel sibling parity | n/a — Clean Road has no PDF edition | — | n/a, stated explicitly |
| Evidence | Clean Road has no evidence adapter | `accept_finalize` sweep | **PASS** — zero `*evidence*` artifacts under the output tree before and after |
| Canary | CRH-SW-E3 re-bless | `comparison-canary-bindings.md` | **DONE** — documented delta (−165, nothing else), exact input identities, three acceptance legs |
| Hook inertness | Intersection Summary vs TSN generated from the SAME inputs on base code and fixed code; full-sheet semantic diff (Provenance excluded) | `witness/is-regression.json` | **PASS** — zero differing cells on every sheet incl. both snapshot sheets |
| Hermetic red→green | `build/check_clean_road.py` | committed | **PASS** with the fix (all checks); **19 semantic FAILs** on the base code (scripts stashed), incl. the defect signature `got 3` differing cells vs `1` |
| Full gate | `build\.venv` `run_checks.py -j 4 -k` + `compileall` + `ruff` + `build.ps1 -SelfTest` | `HF-01\gate_log2.txt`, `selftest_log.txt` | **PASS** — `run_checks`: **157 passed, 0 failed** (the first pass flagged one new swallow in `_build_skip_facts._count`; waived in place with the mandated `# silent-ok:` note and the full gate re-run clean); `compileall` OK; `ruff check scripts` "All checks passed!"; `build.ps1 -SelfTest`: lock-exact venv verified; **frozen self-test PASSED** — the exact shipped exe runs every code path (SMOKE OK: chromium PDF, pdfplumber, openpyxl, evidence render stack, all dynamic report modules, GUI bridge + WebView; 173 MB onefolder) |

## Source-backed discrepancy checks

| Deliverable | Claimed count | Independent count | False-positive/negative samples | Result |
|---|---:|---:|---|---|
| Clean Road Highway values twin, differing cells | 291,127 | 291,127 (mask recount) + 291,127 (live Excel recompute) | The 161 witnessed false positives are gone (`N`, token); the 4 misrepresented cells (route 036 / TEH / 40.15 & 40.352) show the marker, never a forged value; the 20 matches-raw cells untouched | **PASS** |
| Skipped-source census | 102 spans / 174 marked anchors | Codex witness: 102 endpoints; 174 directly-affected candidate cells (165 paired + 9 one-sided); 9 matches-raw + 1 no-coverage spans mark nothing | Per-layer marked cells: OSR 3, TWL 171 — exactly the witnessed field census | **PASS** |

## Formula and evidence checks

| Check | Count / hash | Result |
|---|---|---|
| Installed-Excel values/formula parity | live mask/display/total at every witnessed position == values twin; Diffs sum 291,127 both | **PASS** |
| Eligible evidence images inspected | n/a — none may exist for this family | n/a |
| Prohibited evidence leakage | 0 artifacts | **PASS** |

## Input identities (frozen acceptance inputs)

| Input | SHA-256 | Bytes |
|---|---|---:|
| ArcGIS layer library | junction to the owner's `arcgis_layers/` — byte-identical to the audited library (`00_INDEX` SHA `CCD1BDFF…`, layer counts reproduced exactly) | — |
| TSN raw `CA HIGHWAYS 09.08.2025.xlsx` | `BBD1ACF9D4A8FEF86F96A0A2CF54BE1105E8C919600DBCD05A325B194F5C86E5` | — |
| Built workbook (new) | `8BDD9247771CF2580775F4F0A1DD87706E75F3533C33EC9DB25D41A9AB4B305E` | 10,828,144 |
| TSN normalized (rebuilt in the worktree; content proved identical, bytes differ per PCOA-FINAL-017) | `7F1086FEAFE061531B682B12D0DDA161F5256DF50FCC89A954DF8B87A4656AAB` | 14,864,394 |
| Comparison formulas twin (post-recalc, cached) | `7680C6F37B64FE5469184EA71B81DC81834A84C61F871187EF2813D0CFAE3842` | 581,780,067 |
| Comparison values twin | `AFAAB4BACA82D31694BBE2D98E0EE362C91303A79843ED0DC77F4930DEFE3A12` | 200,034,918 |

## Scope and residual risk

- **Out-of-scope files changed: none.** The diff touches exactly the bundle's allowed
  surface plus the required records.
- **The 9 one-sided anchor cells** (Codex's own `bounded_exclusions`, reason
  "comparison state is 'U'") also carry the token: same skipped-source condition on
  rows that do not pair. Their state (`U`), every count, and the one-sided totals are
  unchanged; only their displayed text moved (blank/stale → the marker) — the ruled
  design marks the BUILD's anchors, and the build cannot know future pairing. The
  witnessed acceptance criterion ("no asserting difference outside the 165 changes")
  holds exactly.
- **The four raw-source disagreements** stay itemized as diagnostic source facts in
  `witness/four-raw-source-disagreements.json`, in the retained Codex witness, and
  per-span (with values) on the built workbook's `ArcGIS Build` sheet; the
  comparison's Summary/Notes disclose the class and counts and point there. The
  deliverable itself cannot assert raw-vs-TSN at an unplaceable anchor — that
  comparison is exactly what the no-guess rule makes unassertable.
- **The comparison completion is now PARTIAL** (the producer's truthful coverage via
  `_merge_input_outcomes`): amber/retryable per the completion conventions, never
  green while source rows are unplaceable. The generic "input file(s) could not be
  read" header wording around the merged note is the existing shared vocabulary
  (HF-02's presentation domain).
- **Spot Check's verdict column reads "match" for an `N` cell** — the pre-existing
  shared N-state vocabulary (same as ditto/context); wording belongs to HF-02.
- **Non-asserting token cells count into the typed outcome's `context_cells` bucket**
  (the shared non-asserting bucket): asserted 2,579,538 / context 1,263,693 — the
  exact 165-cell shift, 52,647 × 73 conserved.
- **Token display width**: in the 13-wide amount columns the 34-char token visually
  truncates at native zoom like any long value (nothing previously legible became
  clipped — those cells were blank or stale). Column-width policy is HF-02
  (PCOA-FINAL-009 explicitly covers Clean Road).
- **Discovered pre-existing defect, deliberately NOT fixed here** (out of the frozen
  scope): `_cancelled()` takes no arguments but three cancellation checkpoints in
  `_consolidate` call `_cancelled(events)` — cancelling an ArcGIS build mid-read
  would raise TypeError instead of returning the cancelled result. Flagged for a
  separate session.
- **Doc mentions of `CRH-SW-E2`** in `CLAUDE.md` / `docs/comparison-engine.md` /
  memory become stale when this bundle merges; the bindings doc's supersession chain
  (E1→E2→E3) is the canonical record. Updating those routers is merge-time
  documentation outside this bundle's allowed surface.
- **Reviewer focus suggestions**: the `_TAG_MARK_COLUMNS` boundary (direct value
  layers marked; HG/TVS/NON/TOLL/FOR/NET + point layers record-only — no real skip
  exists in those layers today, and their outputs are structural/derived/muxed, so no
  single cell IS their value); the co-anchor crediting (per-span `marked_cells` can
  sum above the global 174 — the sidecar's `count`/`marked_anchor_cells` are the
  exact global truth); the symmetric either-side token rule in `compared_cell`
  (mirrors the ditto precedent; only side A can carry it in practice).

## Rollback

Revert the bundle's merge commit. The built workbook regenerates on demand; no
persisted comparison schema version changes; an old build compares under the plain
schema by design — a revert needs a rebuild, not a data migration.

Do not merge this branch. When complete, push it and run Prompt 05.
