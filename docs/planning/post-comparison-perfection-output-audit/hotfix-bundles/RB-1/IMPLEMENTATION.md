# `RB-1` — Implementation Record

Status: **JOINTLY APPROVED** (Review 1 and Review 2 approved; merge pending)

| Field | Value |
|---|---|
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-1-clean-road-source-truth` (worktree `C:\Users\Yunus\Projects\TSMIS-rb1-worktree`; the user's `main` checkout untouched) |
| Base `main` commit | `9c774d4edacf6ae3b6e86d15b62e5d876a690a48` (plan drafted against `a29bdb6`; the delta is the Stage 3 planning docs only) |
| Implementation commit | `93e12c23a8eeb8686817248d662e4d30125de0ec` (first implementation) |
| Review 1 | Codex, `a26725b…` — **DENIED** on RB1-R1-001 (clipped disclosure), recorded in `5090190…` |
| Review 1 remedy commit | `84b82de` — `fix: make the Clean Road skipped-source disclosure legible (RB-1 review 1)` (+ this SHA-recording follow-up) |
| Review 1 re-review | Codex, `6d2a2ce…` — **APPROVED**; exact matrix and signature in `REVIEW.md` |
| Review 2 | Codex, `d330312…` — **DENIED — RETURN TO IMPLEMENTATION** on `RB1-R2-001` (the four diagnostic source facts are absent from Summary and Notes) |
| Review 2 remedy commit | `39c5dc3d15501a428a42b0eb0c3cbe0d499b09fd` — `fix: itemize the Clean Road unassertable source facts in Summary and Notes (RB-1 review 2)` |
| Generated-output root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-01\` (bulk; each return's run in its own `r1-remedy\` / `r2-remedy\` subfolder, so every earlier reviewer's proof files stay untouched); committed machine-readable witnesses in `../HF-01/witness/` |

## Changes

| File | Change | Finding IDs |
|---|---|---|
| `scripts/consolidate_clean_highway.py` | `UNAVAILABLE_TOKEN` constant. `_read_span_layer` now RECORDS every as-of span whose begin or end postmile is unreadable (`_skipped_span_record`: layer, route, county, prefix, the one known endpoint, OD + AR measures, `LocError`, the attribute values — read via the new optional `_SKIP_DETAIL_COLS`), instead of silently `continue`-ing. `_skip_warning` renders one itemized line per span (values included) into the existing `warnings` channel, so the marker sheet, `PARTIAL` completion, `skipped_inputs`, the sidecar and the result message all light up through the machinery `_split_parked` already used. `_mark_unavailable_anchors` writes the token into each skipped span's anchor cells — the built row containing the span's one known endpoint (begin anchors `b <= s < e`, end anchors `b < s <= e`), on the roadbed kinds that layer paints (`_skip_kinds` mirrors `_paint_row`), in its direct value columns (`_TAG_MARK_COLUMNS`), and ONLY where the painted value differs from the span's own projected value (`_skip_value` mirrors `_seg_code`/`_seg_num`/City) — a value corroborated by a placeable span is source truth, not an omission. Cell-first evaluation credits every co-anchored span against the ORIGINAL painted value. The marker sheet gains `Skipped source spans` / `Marked anchor cells` / `Unavailable marker` rows; the sidecar gains `clean_road_build.skipped_source_spans` (count, marked cells, reason, marker, per-span records); the result message names the marked-anchor count. **Review 1 remedy (RB1-R1-001):** the marker sheet is written by the extracted `_write_marker_sheet` with MEASURED stored column widths, wrapped values in rows tall enough for every wrapped line, and the 102 skips as an itemized 14-column table instead of 102 long warning lines (`_SKIP_TABLE_COLUMNS`, `_skip_table_row`, `_skip_values_text`, `_skip_station_text`, `_wrapped_lines`); `SKIP_REASON` becomes one constant shared by the marker sheet and the sidecar. Values, counts and every other sheet are untouched. **Review 2 remedy (RB1-R2-001):** `_mark_unavailable_anchors` now also RETURNS one record per (marked cell, withholding span) — `_marked_cell_records`: the built row's own identity (route · county · PM prefix · begin PM · roadbed), the column, the value that span would have painted, its layer and its one known postmile — and the build writes them to a new `ArcGIS Marked Anchors` sheet (`_MARKED_TABLE_COLUMNS`, `_marked_table_row`, `_write_marked_sheet`), so the workbook itself says WHAT each marker stands in front of instead of only how many there are. The marker sheet gains one `Marked anchor detail` pointer row and the sidecar a `marked_anchor_sheet` key. The table writer (`_disclosure_sheet`, `_sheet_pen`, `_put_table`, `_lines_for`) is the Review 1 geometry extracted so both sheets share it — the second sheet is legible by construction. Marked CELL count, token placement, values and every other sheet are unchanged | PCOA-FINAL-010 |
| `scripts/compare_core.py` | ONE additive opt-in `CompareSchema` field: `unavailable_rule: tuple = ()` (`(token, Summary note)`), plus the `unavailable_token` property. Gated behavior (all inert when unset — the default and ditto-only formula strings are byte-identical): `compared_cell` marks a cell whose ASCII-TRIMmed value equals the token on either side NON-ASSERTING (state `N`, display = side A per the ditto convention); `_matched_state_expr` adds the formula twin (`EXACT(trim, token)` OR-branch), which also covers Spot Check's independent recompute; `_write_summary` renders the schema's resolved disclosure note; `run_compare` validates the pair shape. Precedent: the per-cell ditto `N`. **Review 2 remedy (RB1-R2-001):** the SAME opt-in field's note may now be a CALLABLE, resolved where it was already read (`_write_summary`), so a report can state facts that only exist once both sides are loaded. Nothing else moved: no other schema sets `unavailable_rule`, a string note behaves exactly as before, and the validator still rejects anything that is neither a non-empty string nor a callable. Necessary because the substrate digests both inputs BEFORE the loader reads them (CMP-AUD-098) — composing the sentence earlier would mean reading the inputs ahead of their own digest, and re-reading the 14 MB TSN extract a second time | PCOA-FINAL-010 |
| `scripts/compare_clean_highway_tsn.py` | Imports `UNAVAILABLE_TOKEN` from the producer. `_NOTES_TITLE`/`_NOTES_LINES` restructure (same content). `_build_skip_facts` reads the built workbook's marker counts — an older or skip-free build returns `(0, 0)` and gets the plain module schema, so previously built workbooks still compare byte-identically. `_schema_for` builds the per-run schema via `dataclasses.replace`: `unavailable_rule` with the resolved Summary note (102 / 174 / reason) + a Notes writer with `_disclosure_lines` PREPENDED (the disclosure cannot be buried under the 74-line column table). `compare()` uses it. **Review 2 remedy (RB1-R2-001):** `_build_skip_facts` also reads the build's new `ArcGIS Marked Anchors` table (`_withheld_values`) into `{(route, county, key component, column): [(withheld value, the span's known PM), …]}`, keyed exactly the way this comparison keys a row. `compare()`'s loader — running AFTER the substrate has digested both inputs — calls `_source_conflicts`, which joins every marker to the TSN row it is paired with and classifies it: agrees (every value withheld there is the one TSN already shows), differs, no TSN counterpart, duplicate key, unrecorded. `_summary_note` and `_disclosure_lines` are resolved at write time from that census and ITEMIZE each differing marker as `route / county / location · column: ArcGIS source <value> @ <postmile>…, TSN <value>` — every value the marker stands in front of, since a stretch can carry two unplaceable spans. Caps are stated, never silent (`_SUMMARY_ITEM_LIMIT` 10 / `_NOTES_ITEM_LIMIT` 100). A build without the table still compares under aggregate-only disclosure | PCOA-FINAL-010 |
| `build/check_clean_road.py` | `test_skipped_span_source_truth` — the hermetic red→green test (synthetic library, no real data): a span with one unreadable PM endpoint and usable OD/AR measures must (a) appear in the skip record (sidecar + marker + per-span exact counts), (b) make the build `PARTIAL` with non-zero `skipped_inputs`, (c) surface on the marker sheet, and (d) in a real `mode="both"` comparison: token vs the span's own value → `N` (the false-positive class), token vs a different value → `N` (the misrepresented class), a correctly placed genuine difference stays `D` and is the only counted cell. Covers begin- and end-anchors, kind eligibility (an R-row anchor), the matches-raw no-mark rule, the marker/token display, the Summary + Notes disclosures, the merged producer-partial note, old-build compatibility, and the skip-free COMPLETE control. `_build_library` gains the `extra=` fixture hook + a `LocError` column; `getattr` fallbacks make the base-commit run fail with semantic FAILs, not a crash. **Review 1 remedy:** `_illegible_marker_cells` asserts the marker sheet's STORED geometry — every cell either fits its stored column width or wraps in a row tall enough for every wrapped line — on both the skipped and skip-free builds, plus the itemized table's header, row count, known-PM values and marked-cell counts. Six of these fail on the reviewed head and nothing else does. **Review 2 remedy:** a FOURTH skipped span is added to the fixture whose known endpoint is the SAME postmile as the third but whose value differs — the real 036 / TEH shape, where one cell stands in front of two unplaceable values and one of them is the value TSN shows. The test now asserts the `ArcGIS Marked Anchors` table (header, one row per (cell, span), the exact withheld values and known postmiles, the anchor rows' own begin postmiles, both roadbeds), that BOTH Summary and Notes itemize the disagreement by its exact identity, that both state the 1-agrees / 1-differs classification, that the co-anchored marker names EVERY value it stands in front of rather than the nearest, and that the corroborated anchor is never itemized. `_illegible_marker_cells` now covers both disclosure sheets. Twelve of these fail on the reviewed head `d330312` and nothing else does | PCOA-FINAL-010 |
| `scripts/clean_highway_columns.py` | `ARC_MARKED_SHEET` — the itemized marked-anchor sheet's name, beside `ARC_MARKER_SHEET`, so producer, comparator and tests share one constant | PCOA-FINAL-010 |
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
| TSN normalized (built in the worktree; content proved identical, bytes differ per PCOA-FINAL-017) — the SAME cached artifact was reused by the remedy run, not rebuilt | `7F1086FEAFE061531B682B12D0DDA161F5256DF50FCC89A954DF8B87A4656AAB` | 14,864,394 |
| Built workbook — first implementation run (superseded) | `8BDD9247771CF2580775F4F0A1DD87706E75F3533C33EC9DB25D41A9AB4B305E` | 10,828,144 |
| Comparison values twin — first run (superseded) | `AFAAB4BACA82D31694BBE2D98E0EE362C91303A79843ED0DC77F4930DEFE3A12` | 200,034,918 |
| Comparison formulas twin — first run, post-recalc (superseded) | `7680C6F37B64FE5469184EA71B81DC81834A84C61F871187EF2813D0CFAE3842` | 581,780,067 |
| **Built workbook — review-1 remedy (current)** | `1ADB594425DD846AC93C8500834FBD24E9D8D497F6595FFCB30D496AE8AD360A` | 10,833,361 |
| **Comparison values twin — remedy (current)** | `3EC093F64E7F65B2D822328CD5C12E333E12F71692C5B38D17534B2AA58032BC` | 199,821,556 |
| **Comparison formulas twin — remedy, post-recalc (current)** | `F7412CA0D96E926E0CCC8B3CC3B224BB382A88676CD6588B78B4F494B3B2BEAE` | 581,844,790 |

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

## Review 1 return — Codex, 2026-07-27

Review 1 independently reproduced the source census, marker/count semantics,
state transitions, formula-workbook generation, GUI generation path, full
gate, and unaffected-family regression, but **denied** the bundle on its
visual-usability acceptance criterion.

The newly appended `ArcGIS Build!A4:B108` disclosure is not legible in the
workbook's stored presentation. The sheet has no explicit column-width records,
uses its 8-character base width and 15-point default row height, and writes
every new cell with style 0 (no wrap and no shrink-to-fit). Native Excel renders
the new labels as `Skipped so…`, `Marked an…`, and `Unavailabl…`; the marker
token is cut off, and all 102 warning/detail rows (280–329 characters each) are
truncated. The retained proof is
`HF-01\built ArcGIS Build top.pdf` (SHA-256
`42A41C5D820A7709285F189A77EA5A619AD86853DA996F5BFC3CBFF595C37141`).

Prompt 04 must resume this same branch and make the new labels, token, and all
102 warning/detail rows legible at native scale (for example, with purposeful
column widths plus wrapping/row heights, or an equivalently readable
structure). Regenerate the build and both comparison twins because the build
hash/provenance changes, then rerun the visual, formula, count, GUI-path, and
regression acceptance matrix. Keep the change confined to RB-1's new marker
sheet content; the pre-existing cross-family clipping program remains HF-02.

## Review 1 remedy — Claude, 2026-07-28 (RB1-R1-001 CLOSED)

The denial is a presentation defect in RB-1's own new marker-sheet content, and
the remedy is confined to it. `consolidate_clean_highway._write_marker_sheet`
(extracted from `_write_workbook`) now declares the sheet's stored geometry
instead of inheriting Excel's 8-character base width and 15-point default row.

1. **Purposeful stored column widths.** The sheet writes explicit `<cols>`
   records — 24 for the label column and 56 for the value column, plus the full
   14-column table geometry when spans were skipped. The widths were MEASURED
   against installed Excel's own font metrics, bold header cells included, not
   estimated: the first measured pass rejected a 54-wide value column that Excel
   said needed 53.43 units for the longest attribute text, and the constants
   were raised until Excel reported no column short and no row short.
2. **Wrapping with a row tall enough for it.** A value too wide for its column
   is written wrapped, and its row height is set to (wrapped lines × 15pt), so
   the whole string is visible in the STORED presentation rather than depending
   on a reader widening anything. Numbers stay unwrapped by design — General
   format rounds a number's display instead of clipping it.
3. **The 102 itemized skips are a TABLE, not 102 sentences** — the review's
   sanctioned "equivalently readable structure". One row per span with every
   field in its own sized column: `Source layer`, `Attribute values`, `Route`,
   `Alignment`, `County`, `PM prefix`, `Known endpoint`, `Known PM`,
   `LocError`, `Begin OD`, `End OD`, `From AR`, `To AR`, `Marked cells`. No
   cell on the sheet is a 280–329-character run-on any more, and the record is
   scannable and sortable.
4. **A `Skipped source reason` row** states the reason on the marker sheet
   itself, wrapped and legible, from the same new `SKIP_REASON` constant the
   sidecar uses — so the two wordings cannot drift.
5. **Alignment**, so the block reads as a block: labels top-aligned against the
   first line of a wrapped value; values left-aligned beside their labels
   instead of counts floating at the far right of a 56-wide column.

The prose warning lines are UNCHANGED and still ride the `warnings` channel
into `skipped_inputs=102`, `PARTIAL`, the result message, the log and the
sidecar (`warnings` list byte-identical). Only the marker sheet's presentation
of them moved, from 102 clipped sentences to the itemized table.

**Deliberately unchanged:** every published value, state mask, display, count
and typed outcome; the comparison workbooks' own layout; the `CompareSchema`
hook; the pre-existing cross-family clipping program (HF-02). Column widths are
a column-scoped record, so making rows 4–108 legible necessarily also renders
the three pre-existing marker rows legible — inherent to the required remedy,
not an additional change.

### Remedy verification

| Gate | Method | Result |
|---|---|---|
| Base-red at the REVIEWED HEAD | `build/check_clean_road.py` from this head run against archived `a26725b…` scripts | **PASS** — exactly **6** FAILs, all presentation (`states the skip reason`, `skip table names every field`, `one itemized table row per skipped span`, `known PM and marked counts`, `every disclosure cell is legible at its stored width`, `a skip-free marker is legible too`) and nothing else — the defect signature isolated to RB-1's new marker content |
| Base-red at the ORIGINAL base | same check against archived `9c774d4…` scripts | **PASS** — **24** semantic FAILs including the original signature `got 3` differing cells instead of `1` |
| Hermetic green | `build/check_clean_road.py` at this head | **PASS** — all checks, including the new stored-geometry assertion on both the skip and skip-free marker sheets |
| Stored-presentation audit (independent) | An OOXML reader over the rebuilt workbook's package — no product module, no openpyxl object model: `<cols>` widths, row `ht`, per-cell `wrapText` via `styles.xml`, values via `sharedStrings` | **PASS** — **0** illegible cells over the whole 111-row sheet; 14 stored column widths; the skip table carries all 14 headers and exactly **102** rows |
| Installed-Excel legibility oracle | Excel's own font metrics decide: per column, AutoFit over that column's unwrapped cells with each cell's real font (bold headers included) must not exceed the STORED width; per wrapped row, AutoFit height at the stored width must not exceed the STORED height | **PASS** — `columns_too_narrow: []`, `rows_too_short: []` on the real rebuilt workbook |
| Native-scale visual | Native-Excel PDF of `ArcGIS Build` at **Zoom 100** (no fit-to-page shrink), rendered and read | **PASS** — labels, counts, the 34-char marker token, the wrapped reason and every table column (through the 10-digit `From AR`/`To AR`) render in full; nothing clipped |
| Presentation-only proof | Every data-sheet cell of the rebuilt workbook vs the pre-remedy build (`8BDD9247…`) | **PASS** — **0** cell differences across all **57,729** rows, Provenance identical, the same **174** tokens, sidecar still `102 / 174` |
| Producer semantics after the remedy | The build's own terminal result and sidecar | **PASS** — `status=ok completion=partial skipped_inputs=102 failed=0`; message still names 102 unplaceable spans and 174 marked anchors; sidecar `102 / 174`; the `warnings` list is unchanged (only the marker sheet's presentation of it moved) |
| Regenerated end-user comparison | The whole shipped path re-run: `start_arcgis_build` → `ConsolidateWorker`, then `start_arcgis_compare` / `_begin_compare` / `_launch_compare` with `mode="both"`, reusing the SAME cached normalized TSN artifact (`7F1086FE…`, not rebuilt) | **PASS** — `status=ok completion=partial`; **52,647** paired / **5,081** ArcGIS-only / **7,436** TSN-only / **50,012** differing rows / **2,635** identical / **291,127** differing cells / asserted **2,579,538** / context **1,263,693** — every CRH-SW-E3 figure reproduced unchanged |
| Regenerated source-truth recount | App-free lockstep recount of the frozen pre-fix values twin (`A59177DC…`) vs the remedy values twin | **PASS** — 291,292 → **291,127**; **165** mask flips AND **165** display flips; the **9** one-sided anchors display the token at state `U`; per-field deltas exactly **−82 / −81 / −1 / −1**; **0** unexpected changes across all **65,164** rows |

| Regenerated formula deliverable | Installed-Excel `CalculateFullRebuild` + Save on the remedy formulas twin, then an app-free read of the cached results | **PASS** — verdict `✗ DIFFERENCES FOUND — 291,127 differing cell(s), 12,517 one-sided row(s)`; live `Diffs` sum **291,127**; all **165** witnessed positions live-`N` displaying the marker; **every** SELF-CHECK OK; **0** error cells on Summary / Spot Check / Comparison; both disclosure notes present |
| Regenerated neighboring-family regression | Intersection Summary vs TSN generated from the SAME inputs by the ORIGINAL base code (`9c774d4…`, archived tree) and by this head, **both on the same day** so code is the only variable; full-sheet semantic diff, Provenance excluded as run identity | **PASS** — **0** differing cells on every sheet, both `__CMP_E2_SNAPSHOT_A/B` included; 58 paired / 53 differing cells on both |
| Regenerated build-level source truth | Cell diff of the rebuilt workbook vs the frozen audit-approved PRE-fix build (`8F9766AC…`) | **PASS** — same **57,728**-row universe (0 extra either side); **174/174** expected tokens present; **0** unexpected cell changes; the marker sheet is purely ADDITIVE (3 rows → 111, the original three keys still first) |
| Full gate (re-run over the final tree) | `build\.venv` `run_checks.py -j 4 -k`, `compileall`, gate-exact `ruff check scripts`, `build.ps1 -SelfTest` | **PASS** — **157 passed, 0 failed of 157**; compile clean; Ruff "All checks passed!"; `Frozen self-test PASSED` — the EXACT shipped exe runs every code path (`SMOKE OK`, 173 MB onefolder) |

Retained: `HF-01\r1-remedy\` (the measurement JSON and both native-Excel PDFs);
the Review 1 proof `HF-01\built ArcGIS Build top.pdf` is untouched.

Note on the regression method: an earlier diff against the previous day's
retained base artifact reported one cell — the Summary banner's `created
2026-07-27` vs `2026-07-28` run stamp. That is run identity, not behavior, so
the base artifact was regenerated from the archived base tree on the same day;
the same-day base-vs-head diff is the zero above.

## Review 2 return — Codex, 2026-07-28 (`RB1-R2-001` OPEN)

Review 2 denied exact head `d330312efc949523caf07f1fec4e867afed87cf7`
on one controlling acceptance failure. `IMPLEMENTATION-PLAN.md` HF-01
criterion 7 requires the four genuine route 036 / TEH / 40.15 and 40.352
lane/width disagreements to remain itemized in **Summary/Notes and the retained
witness**. The witness itemizes them, but a bounded read-only scan of the
retained values twin found none of the route/county/postmile identities in
either sheet; `_schema_for` and `_disclosure_lines` emit aggregate 102 / 174 /
reason prose only.

Resume Prompt 04 on this branch. In the existing allowed comparator/test
surface, itemize the exact four unavailable, non-asserting facts in both
Summary and Notes; add a deterministic `check_clean_road.py` assertion; then
regenerate both comparison twins and affected native renders and rerun the
scoped acceptance matrix plus the full implementation gate. Preserve every
already-passed count, state, marker-sheet geometry, formula result, and
neighboring-family invariant. Review 1's `RB1-R1-001` remains closed.

## Review 2 remedy — Claude, 2026-07-28 (RB1-R2-001 CLOSED)

Criterion 7 requires the genuine raw-source disagreements to stay itemized in
**Summary/Notes and the witness**. They were in the witness only, because the
comparison could not name them: the build recorded HOW MANY anchors it marked,
never WHAT any marker stood in front of, so the comparator had nothing to
itemize and emitted aggregate `102 / 174 / reason` prose. The remedy closes
that gap at the source rather than printing four remembered identities.

1. **The build now records what each marker withholds.**
   `_mark_unavailable_anchors` already knew — it compares each skipped span's
   projected value against the painted cell to decide whether to mark at all —
   but threw the value away. It now returns one record per (marked cell,
   withholding span): the built row's own identity spelled the way the
   comparison keys a row (route · county · PM prefix · begin PM · roadbed),
   the column, the value that span would have painted, its layer, and the one
   postmile the source did give. The workbook carries them on a new
   `ArcGIS Marked Anchors` sheet, with a `Marked anchor detail` pointer row on
   the marker sheet and a `marked_anchor_sheet` key in the sidecar.
2. **The comparison classifies every marker against TSN and itemizes what
   disagrees.** `_source_conflicts` joins each marker to the TSN row this
   comparison pairs it with and sorts it into: agrees (every value withheld
   there is the one TSN already shows), differs, no TSN counterpart,
   duplicate key, or no recorded source value. Summary and Notes state that
   census and name each differing marker as
   `route / county / location · column: ArcGIS source <value> @ <postmile>…,
   TSN <value>`.
3. **Derived, never remembered.** Nothing keys on `036`, `TEH`, `40.15` or
   `40.352`. The hermetic test proves the same code itemizes a completely
   different identity (`001 / ORA / 2R · THY_RT_O_SHD_TOT_WIDTH_AMT`) from a
   synthetic library, and the real corpus produces the four the plan names.
4. **A marker that hides TWO values names both.** ALL FOUR of the cells
   Review 2 named have more than one unplaceable span anchored at them (two at
   `40.15`, three at `40.352`) — the stretch genuinely carries `12 @ 40.18`
   AND `24 @ 40.298`, and TSN shows one of them. An earlier draft treated a multi-valued cell as unclassifiable and
   would have itemized NOTHING on the real corpus while passing a
   single-valued hermetic test. The retained witness caught it before the
   run; a cell now agrees only when EVERY value withheld there is TSN's, and
   the fixture gained a fourth span co-anchored with the third so the case is
   locked.
5. **`compare_core` change is one line of resolution.** The already-opt-in
   `unavailable_rule` note may now be a callable, resolved where it was
   already read. Necessary because the substrate digests both inputs BEFORE
   the loader reads them (CMP-AUD-098): composing the sentence earlier would
   mean reading the inputs ahead of their own digest, and re-reading the
   14 MB TSN extract a second time. No other schema sets the field, and a
   string note behaves exactly as before.
6. **The new sheet is legible by construction and by measurement.** It shares
   the Review 1 geometry helpers (`_disclosure_sheet` / `_sheet_pen` /
   `_put_table`), and its widths were measured against installed Excel's own
   font metrics over the widest real column name, the widest layer name and
   bold headers — the first measured pass **failed**: Excel needed 29.71
   units for `Column` against a stored 29.29 and 14.57 for `Span known PM`
   against 14.29 (Excel stores a width of N as N−0.71, so fitting by
   character count still clips). The constants were raised and re-measured to
   zero narrow columns.

**Deliberately unchanged:** every published value, state mask, display, count
and typed outcome; which cells are marked and the token they carry; the
Review 1 marker-sheet geometry (one added pointer row); the producer's
completion, `skipped_inputs`, warnings and sidecar counts. The withheld values
are disclosed as unplaceable source facts — they are never written into a cell
as our side's answer, and every marker stays non-asserting `N`.

### The itemization is SIX cells, not four — and the 165 reconcile exactly

The four the plan names are all itemized, with the exact identities Review 2
required. The derivation finds **two more**, and the difference is a
classification rule, not a count move:

| Split | Rule | Result |
|---|---|---|
| Witness (`four-raw-source-disagreements.json`) | classify each published `D` cell by its **reference (nearest) anchor** | 161 exact false positives + **4** misrepresented = 165 |
| Published disclosure (this remedy) | a cell agrees only when **EVERY** value withheld there is the one TSN shows | 159 agree + **6** withhold something TSN does not = 165 |

The two that move are `036 / TEH / 39.72` × `THY_LT_LANES_AMT` and
`THY_LT_TRAV_WAY_WIDTH_AMT`. Their nearest anchor (`1 @ 39.72` / `12 @ 39.72`)
is exactly what TSN shows, so the reference-anchor rule called them false
positives — but a SECOND unplaceable span (`2 @ 40.105` / `24 @ 40.105`)
anchors into the same built row, and TSN carries no such value. The marker
there stands in front of a source fact the witness's rule does not surface.
Stating it is the whole point of criterion 7; suppressing it would mean
choosing a "reference" anchor, which is exactly the positional guess the
2026-07-26 owner ruling forbids.

Nothing about the DELIVERABLE's counts changes: all 165 remain non-asserting
`N`, all 165 remain excluded, and the total is still exactly
**291,127 = 291,292 − 165**. The 161/4 witness split stands as the record of
what the pre-fix workbook published; 159/6 is the record of what the markers
withhold.

### Remedy verification

| Gate | Method | Result |
|---|---|---|
| Base-red at the REVIEWED HEAD | `build/check_clean_road.py` from this head run against archived `d330312…` scripts | **PASS** — exactly **12** FAILs, every one an itemization assertion (the marked-anchor sheet's header/rows/values/postmiles/roadbeds, both sheets' itemization and classification, the co-anchored case, the corroborated-anchor guard, the 3-tuple skip facts) and nothing else — the `RB1-R2-001` signature isolated |
| Base-red at the ORIGINAL base | same check against archived `9c774d4…` scripts | **PASS** — **35** semantic FAILs including the original signature `got 3` differing cells instead of `1`; degrades to red, never crashes (an unguarded index in the first draft did crash, and was fixed) |
| Hermetic green | `build/check_clean_road.py` at this head | **PASS** — all checks, including the new co-anchored fixture whose one cell stands in front of two unplaceable values |
| Real end-user generation | Shipped path only: `GuiApi.start_arcgis_build` → `ConsolidateWorker` → GUI terminal, then `GuiApi.start_arcgis_compare` → `_begin_compare` → GUI terminal, `mode="both"`; only the native save dialog was replaced with one absent destination | **PASS** — build `ok/partial`, `skipped_inputs=102`, 57,728 rows / 252 routes / 174 marked; compare `ok/partial`; **zero** GUI errors; **zero** evidence artifacts produced |
| Every CRH-SW-E3 figure | the shipped run's typed outcome | **PASS** — **52,647** paired / **5,081** ArcGIS-only / **7,436** TSN-only / **50,012** differing rows / **2,635** identical / **291,127** differing cells — unchanged |
| The required source facts, app-free | A reader importing NO product module: the build's own two sheets + the RAW TSN extract joined independently, then the published Summary/Notes searched for each derived identity | **PASS** — 174 markers = 159 agree + **6** withhold a value TSN does not + 9 unpaired; `unrecorded` and `duplicated` both **0**; all six itemized in **both** sheets, including the four `036 / TEH / 40.15` and `40.352` lane/width facts Review 2 named |
| Build change is ADDITIVE | Cell diff of the new build against the Review-1-approved build | **PASS** — **0** data-cell differences across all **57,728** rows, Provenance identical, the same **174** tokens, marker sheet 111 → 112 rows (exactly the one added pointer label), and the new sheet's **183** rows = 1 header + 174 cells + the 8 extra records the co-anchored cells owe |
| Comparison change is PROSE ONLY | Full-sheet lockstep diff of the Review-1-approved values twin against the remedy twin | **PASS** — `Comparison` **0** differences over **65,165** rows; `Spot Check`, `Routes`, both `Only in …`, both data sheets and BOTH very-hidden `__CMP_E2_SNAPSHOT_A/B` all **0**; `Summary` **1** (the disclosure bullet); `Notes` **84** (the disclosure block plus the shift its new lines cause); `Provenance` **4** (both inputs' path + SHA — run identity, see below) |
| Installed-Excel legibility | Excel's own font metrics on the REAL build: per column, AutoFit over unwrapped cells with each cell's real font (bold headers included) vs the stored width; per wrapped row, AutoFit height vs the stored height | **PASS** — `ArcGIS Marked Anchors` (183×9) and `ArcGIS Build` (112×14) both report `columns_too_narrow: []` and `rows_too_short: []`; native-scale and fit-width PDFs exported as the visual witness. The first measured pass **failed** and set the constants (see remedy note 6) |
| Native-scale visual | Native-Excel PDFs of BOTH disclosure sheets at **Zoom 100** (no fit-to-page shrink), rendered to images and read page by page | **PASS** — on `ArcGIS Marked Anchors` every column renders in full: route/county/prefix, the begin postmile, the roadbed, the 26-character `THY_*` column names, the withheld values, `SHS Travel Way L` / `SHS O Shld Width R` and the span's known postmile. Numbers keep Excel's conventional right alignment inside their table column, exactly as the Review-1-approved skip table does; the label/value block's left alignment (the RB1-R1-001 fix) is untouched |
| Neighbouring-family regression | Intersection Summary vs TSN generated from the same inputs by the ORIGINAL base code (`9c774d4…`, archived tree) and by this head, both on the same day; full-sheet semantic diff | **PASS** — **0** differing cells on **every** sheet including both `__CMP_E2_SNAPSHOT_A/B` **and** Provenance; 58 paired / 53 differing cells on both. The callable-note hook is inert for every schema that does not set `unavailable_rule` |
| Full gate | `build\.venv` `run_checks.py -j 4 -k`, `compileall`, gate-exact `ruff check scripts`, `build.ps1 -SelfTest` | **PASS** — **157 passed, 0 failed of 157** (169 s); compile clean; Ruff "All checks passed!"; `Frozen self-test PASSED` — the EXACT shipped exe runs every code path (`SMOKE OK`, 173 MB onefolder) |
| Regenerated formula deliverable | Installed-Excel `CalculateFullRebuild` + Save on the remedy formulas twin (68.7 min, `F75189D1…` 468,206,894 → `1393164A…` 581,854,795 bytes), then an app-free read of the cached results that hashes the workbook in the same pass | **PASS** — live verdict `✗ DIFFERENCES FOUND — 291,127 differing cell(s), 12,517 one-sided row(s)`; **10 of 10** SELF-CHECK rows `OK`, including *Per-field difference counts add up to the total differing cells* and *Build-time source identity and duplicate pairing snapshot is current*; **zero** error cells on every sheet; the itemized disclosure bullet present and naming all six facts. So Excel computes the same truth live that the values twin publishes |

**On the four Provenance cells.** Both inputs' recorded path and SHA moved
because the Review 1 remedy ran from the `TSMIS-rb1-worktree` working tree and
this run from the main checkout. `paths.DATA_ROOT` is per-tree, so each tree
holds its OWN normalized TSN copy, independently built from the identical raw
extract (`CA HIGHWAYS 09.08.2025.xlsx`, `BBD1ACF9…`, 21,290,781 bytes — the
same raw both reviews bound to). The two normalized images differ in bytes
(`7F1086FE…` / 14,864,394 vs `30048451…` / 14,864,396 — the PCOA-FINAL-017
non-determinism this canary already documents) but NOT in content: the `TSN`
data sheet and the very-hidden `__CMP_E2_SNAPSHOT_B` are cell-identical across
**60,085** and **60,084** rows. The ArcGIS SHA moved because the build gained
the new sheet, proved additive above.

Retained: `HF-01\r2-remedy\` (both workbooks, the built workbook, the Excel
metric JSONs and the native-scale + fit-width PDFs of both disclosure sheets);
`r1-remedy\` and the Review 1 and Review 2 reviewer folders are untouched.

### Exact identities of the offered artifacts (RB1-R2-EG-001)

Every artifact this bundle offers for approval, by size and SHA-256 — including
the **post-recalculation** formulas twin, so the successful installed-Excel
rebuild is bound to the exact bytes it was performed on rather than only to the
pre-recalculation workbook the sidecars name:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| ArcGIS build (`clean_highway_built.xlsx`) | 10,840,933 | `0D8575CA0C496594D2E47F51BC1BA39673384F4FDDE4A7995D497BE1959A6DDF` |
| Values twin (`RB1-R2-Remedy (values).xlsx`) | 199,822,285 | `173E245248C4A26F06F523577DE41DF062D6433FE801FEFEA4D1EE2D8FE3FB99` |
| Formulas twin, **as generated** (pre-recalculation) | 468,206,894 | `F75189D109D4007DDE3488CB18ADD970DD73AC4FDC5C5D9AE50FCFAA15C41165` |
| Formulas twin, **after the successful installed-Excel `CalculateFullRebuild` + Save** | 581,854,795 | `1393164AAF50C7C4D2B7C54B33150C3D6BCDD5CB5BA8604557BC6A78EB8205F0` |

The first three identities are the shipped run's own record
(`witness/r2-shipped-run.json`, hashed by the driver as each file was
written). The fourth is produced by `witness/formulas-twin-recalc.json`'s own
reader, which hashes the workbook in the SAME pass that reads its cached
results — so the recorded verdict, the ten `OK` self-checks and the zero error
cells are bound to that hash by construction, not by transcription. That
witness also hashes the retained copy at
`HF-01\r2-remedy\RB1-R2-Remedy.xlsx` and records
`retained_copy_matches: true`, so the bytes offered for review are provably
the bytes recalculated.

## Rollback

Revert the bundle's merge commit. The built workbook regenerates on demand; no
persisted comparison schema version changes; an old build compares under the plain
schema by design — a revert needs a rebuild, not a data migration.

Do not merge this branch. `RB1-R2-001` is remedied, gated, recorded and pushed:
run **Prompt 05** again for Review 2 (`<BUNDLE_ID> = RB-1`, `<REVIEWER> = Codex`)
against the new head. Review 1's approval and `RB1-R1-001` closure stand — the
marker-sheet geometry it signed off is unchanged apart from one added pointer
row, re-measured against installed Excel and still green.
