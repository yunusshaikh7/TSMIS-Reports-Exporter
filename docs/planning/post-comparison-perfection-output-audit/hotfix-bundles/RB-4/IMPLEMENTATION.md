# `RB-4` — Implementation Record

Status: **IMPLEMENTED — AWAITING ADVERSARIAL REVIEW 1 (re-review)**.
Acceptance run **chain10** passed every programmatic phase at head `f4b55f2`
and its native-scale inspection read 336 images with **0 mis-targeted, clipped,
multi-column, out-of-record, or undisclosed crops**.

Review 1 denied the bundle on `RB4-R1-001` — the single Intersection Detail
blank crop that is correctly targeted but has no in-crop anchor. **The remedy is
documentation, by owner ruling of 2026-08-09** (*"this is fine, just document
it"*): HF-10 criterion 2's definition of an accurate crop now states that a
blank drawn from the print's OWN cell rectangle is accurate, and that an
absent in-crop anchor is a disclosed coverage limitation rather than a failed
image. See the [2026-08-09 ruling in BUNDLE.md](BUNDLE.md) — which also records
what the ruling does NOT relax, and why extending Highway Log's bracketing rule
to Intersection Detail was rejected.

**No runtime file changed for this remedy**, so chain10's acceptance binding is
untouched: the manifest's runtime head is still `f4b55f2`, every retained image,
witness and count stands as run, and the exact-head verifier still reports
0 problems. Under the amended criterion the retained set is **336/336**.

The run history matters, because each round's inspection found what the
programmatic gate could not:

| Run | Head | Outcome |
|---|---|---|
| chain6 | `a21e0ba` | passed on the ORIGINAL workbook-panel contract — the owner rejected those images and re-ruled the bundle |
| chain7 | `adfa9f4` | first print-crop run; passed every phase. Its 341-image inspection found **9 defects in 3 classes** |
| chain9 | `c974a00` | passed every phase. Its 342-image inspection found **3 defects**, all one class — a trailing-blank sliver my chain7 fix had only half-closed |
| **chain10** | **`f4b55f2`** | **the acceptance.** Passed every phase; its 336-image inspection found **1 finding**, documented and not a mis-targeted box (below) |

Evidence is PRINT CROPS on the 12 `_pdf`-family PDF-vs-PDF cells only, refused
at the engine boundary everywhere else; see the BUNDLE.md amendment section and
"The 2026-08-05 amendment" below.

| Field | Value |
|---|---|
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-4-evidence` (worktree `C:\Users\Yunus\Projects\wt-rb4`; the user's `main` checkout untouched) |
| Base `main` commit | `72adf447d45a2b74c562ba714008661a180c5d5f` (the RB-4 readiness commit on top of readiness source `ff780af…`; verified clean and identical to `origin/main` at branch creation) |
| Work items | HF-05 (PCOA-FINAL-004 P1, -005 P1, -006 P1) + HF-10 (PCOA-FINAL-007 P2) |
| Generated-output root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-05\rb4-a1\` (lib copy + base/head stores + results + logs); the four env image sets copied to `…\HF-10\rb4-a1\`; the owner's 12-set deliverable at `…\post-comparison-hotfixes\RB-4 evidence deliverable 2026-08-09\` (chain10's images; the superseded chain7/chain9 folders are retained beside it, renamed `(SUPERSEDED …)`); committed machine-readable witnesses in `../HF-05/witness/` and `../HF-10/witness/` |

## Changes

> **Amended 2026-08-05.** The table describes the FINAL tree (the print-crop
> amendment applied over the first implementation). Where a row says a
> mechanism was "replaced under the amendment", the first implementation's
> version shipped through the first RB4-A1 run and was then reversed by the
> owner's ruling — the git history carries both.

| File | Change | Finding IDs |
|---|---|---|
| `scripts/visual_evidence.py` | **The print-crop engine (owner amendment 2026-08-05).** Evidence exists ONLY for the `_pdf` families: `_ADAPTER_MODULES` names exactly the four `_pdf` rows — the registry IS the engine-boundary refusal, and `capable()`/`evidence_opts_for`/both cameras/the UI all gate through it; `FLAVORS = (tsn, env)` so `generate()` refuses FLAVOR_SELF outright; `self_capable()` is always False; `_ENV_ADAPTER_MODULES` drops ramp_summary (the third ruling — its adapter goes dormant). The provenance binding from the first implementation is KEPT UNCHANGED: `_bound_provenance` requires the `.provenance.json` sidecar + a trusted/current typed outcome with a matching committed `generation_id`; the compared workbooks' live bytes digest against the recorded sha256 before anything else runs; a pair that cannot bind RETIRES any prior set and raises `EvidenceSourceBindingError` with NOTHING published. The vs-TSN branch renders PRINT CROPS on both sides: print discovery restored (`_pdf_source_files`/`_ensure_pdf_source_set`), the TSMIS side resolved per route through `find_route_print` (dated/legacy/store-tagged names) and located by `_locate_tsmis_sources` (CMP-AUD-049 identity refusals; resolved paths carried), the TSN side through the adapter district/locate loop; the snapshot buckets hold the prints PLUS the two compared workbooks. `_try_example`'s tsn branch crops both prints under the shared `_box_within_record` engine backstop (both axes — the PCOA-FINAL-005 rule now uniform across print lanes) and implements the amendment's disagreement contract: a print whose parsed value differs from the compared value renders WITH a disclosure note (the image note line AND the Summary's new `Note` column) and a subline that says DISAGREES instead of claiming verification — never the old silent drop. The Summary declares the two print folders under the compared selections (`read_lines`; the data header row floats below them), and `_legend_for(tsn)` states the crop rule + the disclosure promise. `FLAVOR_ENV` (HF-10) is unchanged from the first implementation apart from riding the shared backstop: provenance-resolved run folders (`compare_env._find_input_dir`), candidates from the published universe, `_locate_env_sides` → adapter `env_locate`, per-example COMPOSE-to-published verification. The workbook-panel renderer (`_workbook_side`/`_excel_strip`/`panel_cell_text`/`_workbook_rows_at`/`_display_header`/`_normalization_note`) is DORMANT — kept in code, reachable from nothing ("keeping the code is fine but ts shouldnt be possible") | amendment; 004/005/007 kept, 006's surface retired with the panels |
| `scripts/evidence_highway_log.py` | `pdf_excel_column_for`/`tsn_excel_column_for` = the one corrected-header gate (all three compared HL workbooks share it); `tsn_project`; `workbook_sheet`; `locate_tsmis` gains `key_fn` + `src` capture; blank-Description boxes now REFUSE on both prints (the below-the-record guesses that boxed the NEXT record are gone). **`_blank_cell_span` (post-inspection, `f4b55f2`): a blank cell is boxable ONLY where the record's own ink BRACKETS the column — ink left AND right — and then the full window is the rectangle.** Both sides use it (`_line_cell_box`, `tsn_box`) and the env lane inherits it because `env_box` delegates to `tsmis_box`; `Sig Chg. Date`, being last, can never be bracketed and always refuses. This replaced two earlier partial fixes that the native-scale inspections caught: the first mirrored the refusal to only the TSMIS side, the second refused only an EMPTY window overlap and still drew a 7–12 px sliver where the record's ink merely grazed the window. **`tsn_raw` reads a PRE-normalization snapshot** captured in `_scan_tsn_print` before `ctnl._normalize_row` rewrites the row IN PLACE — reading `rowd` made the hook return the compared value itself and silenced the disclosure on exactly the padded numeric cells that needed it. Env hooks (`env_fields` = the 30 corrected fields, `env_locate` keyed by the projected Location, `env_value`/`env_box`) | 004, 005, 007 |
| `scripts/evidence_highway_sequence.py` | Panel hooks (`pdf_excel_column_for` alias — the conversion reproduces the export header verbatim; `tsn_excel_column_for` over `['Route'] + SHARED_HEADER`; side-aware `tsn_project`; `workbook_sheet` incl. the normalized sheet); `locate_tsmis` gains `key_fn` + `src`; synthetic equate rows are MARKED and their blank fields REFUSE geometry (the final-'O'-of-'EQUATES TO' class), the no-segs Description fixed-zone guess removed; env hooks (`env_fields` incl. the env comparison's own `(col C)`/`(col E)` names for the unnamed postmile columns, `env_locate` keyed by the plain PM cell, strict `env_project`, `env_box` with prefix/suffix zones) | 004, 005, 007 |
| `scripts/evidence_intersection_detail.py` | Panel hooks (`pdf_excel_column_for` alias — the legacy labels ride the same value positions; `tsn_excel_column_for` under the v3-sidecar gate; `tsn_project`; `workbook_sheet`); `locate_tsmis` gains `key_fn` + `src`; env hooks (`env_fields` = the canonical export header minus Route/Post Mile, `_ENV_TO_SHARED` derived from `idt._TSMIS_POS` × `_TSMIS_HEADER` so the mapping can never drift from the loader, padded-PM env keying, strict `env_project`, Location special-cased to its print cell). Probe-driven fix on the real corpus: the two env display columns OUTSIDE the vs-TSN map that the print nevertheless carries as grid cells (`PS` = rowA window 2, `Intrte S` = rowB window 13) get `_ENV_CELL_EXTRA` geometry + positional value reads (`tsmis_box` refactored over `_box_at`); without them every published `PS` diff refused (`box None` on all 12 sampled) | 004, 007 |
| `scripts/evidence_ramp_detail.py` | `excel_column_for` goes DUAL-EDITION (the July-2026 consolidated the loader already accepts resolves through `_TSMIS_POS_2026` — RB-3's deliberately deferred evidence half); `pdf_excel_column_for` over the conversion's own 14-column book (`_PDF_BOOK_POS`); `tsn_excel_column_for` with District resolving to its OWN sidecar column; strict `tsn_project`; `workbook_sheet`; `locate_tsmis` gains `src`; env hooks (`env_fields` from `compare_env._RD_ENV_HEADER` + the print-only pair, strict `env_project`, `env_box` refusing the two structurally-empty conversion columns). Probe-driven fix on the real corpus: the env comparison publishes the export's RAW padded PM text (`043.274`) while the LOCKSTEP walk keys on the normalized PM (`43.274`) — `env_locate` now normalizes the published keys for the walk and re-keys the result by the published text, excluding (never guessing) two published texts that collapse onto one normalized PM; without it every env lookup returned zero records | 004, 006-adjacent, 007 |
| `scripts/evidence_highway_detail.py` | The minimal shared-contract hooks only (`pdf_excel_column_for` alias, `tsn_excel_column_for`, `tsn_project`, `workbook_sheet`) so the shared engine stays uniform. NO parser/canary/behavior change; no env hooks (⛔ HD pre-release honored — its lane is not exercised by RB4-A1) | wiring |
| `scripts/evidence_ramp_summary.py` | NEW env-only adapter, then made DORMANT by the third ruling (evidence is by report type — ramp_summary's env cell is required-silent; the module is registered nowhere, kept on disk with its working HF-10 implementation: values from the consolidator's OWN parser, geometry from a word-box-keeping twin of its two-column walk, mislabel-refusal cross-check, footer totals by their own label lines) | 007 → amendment |
| `scripts/visual_evidence.py` (env candidates) | Probe-driven fix on the real corpus: a route-keyed comparison (Ramp Summary) publishes no separate route column — `_env_candidates` now carries `route = row.route or row.key` so the padded key serves as the print-file route token; without it the engine resolved `tsar_ramp_summary_route_.pdf` (empty token) and every RS example missed | 007 |
| `scripts/matrix_build.py` | `build_cell_comparison` gains `evidence=` → `_run_env_evidence` (decoration-after-`require_published_comparison`+COMPLETE, failure only logs — the existing contract; silently skips env-incapable rows, which now includes ramp_summary); `build_comparison` passes `evidence` through on the env branch; NEW `run_env_evidence_only` (the HF-10 camera: trusted/current/COMPLETE sidecar, cache generation binding, input-fingerprint freshness); `evidence_for_cell` gains `mode_id` ("env" → the env camera) and an EARLY `capable` gate so a required-silent row's camera refuses with a clean sentence instead of a registry KeyError; `_run_self_evidence` is the retired lane — `self_capable` is False everywhere, so it returns silently for every row (its docstring says so) | 007, amendment |
| `scripts/matrix.py` | Facade re-export `run_env_evidence_only` | 007 |
| `scripts/gui_matrix.py` | `matrix_evidence_cell` is mode-aware (the row's SELECTED mode: env → `env_capable` + baseline-cell refusal; job carries the frozen mode per CMP-AUD-110) and — the amendment — refuses every mode other than tsn/env ("Evidence images exist only for the vs-TSN and cross-environment comparisons of the PDF-edition reports"); `_dispatch_evidence_job` routes `mode_id` | 007, amendment |
| `scripts/day_matrix.py` | `evidence_for_day_cell` gains the early `visual_evidence.capable` gate (a required-silent row's by-day camera refuses with a clean sentence, mirroring the Everything camera) | amendment |
| `scripts/gui_api.py` | `_evidence_view`'s `unsupported` list is per ROW under the report-type rule: every matrix row with no lane (`capable` OR `env_capable`) is named — an Excel row is listed even when its PDF sibling is supported, so the hint states exactly what the toggle will and won't generate | 007 → amendment |
| `scripts/self_test.py` | `evidence_ramp_summary` joins `_DYNAMIC_REPORT_MODULES` — kept: the dormant module still ships in the frozen build so the self-test import census stays truthful | wiring |
| `scripts/ui/ui-matrix.js` | The evidence hint is per-family again: a ✓/○ line per supported PDF-edition family (print count / drop folder), the env line, and a "No evidence: …" line naming every other row; `evidenceActionInfo(rowKey, mode)` offers the action ONLY for mode tsn/env of registry rows (self-mode cells lose camera AND open); the row camera badge exists only on the four PDF rows and its tooltip says crops of both source prints | 004, 007, amendment |
| `scripts/ui/mock.js` | Evidence block mirrors the amendment: `rows`/`env_rows` = the four `_pdf` rows, `reports` = the four families, `unsupported` = the eight other matrix-row labels in matrix order (mock parity) | wiring |
| `build/app.spec` | `APP_MODULES` += `evidence_ramp_summary` (F6) | wiring |
| `build/_checklib.py` | NEW `publish_bound_comparison` — fixtures publish the production way (`artifact_store.commit_workbook` → typed outcome sidecars + `write_comparison_provenance`), so checks drive the exact-source binding through the real front door | test infra |
| `build/check_visual_evidence.py` | The stated-contract block asserts the PRINT-CROP contract (registry = the four `_pdf` rows; FLAVOR_SELF out of FLAVORS; `_locate_tsmis_sources` + `tsn_ctx`; `_box_within_record`); the registry/sources/availability blocks pin the four-row maps + the four-family reports + `env_rows` LITERAL four; the engine fixtures (retire-on-clean, dup-only, freshness gate) ported to `intersection_detail_pdf` with stub prints + a sandboxed TSN library; `evidence_opts_for` refuses Excel rows and highway_detail; KEPT: bound-comparison fixtures, snapshot bucket/stat/rename coverage, blank-side refusals (HL both prints, HSL equate lines), env row-rectangle backstop, env candidates, `env_fields` pins, the RS geometry twin (now a dormant-adapter lock) | 004, 005, 007, amendment |
| `build/check_evidence_source_role.py` | The stated-contract block asserts the print-crop contract; the role map covers exactly the four `_pdf` rows; the SELF lane's checks flip to REFUSAL (self_capable False everywhere; `generate(flavor='self')` and an Excel row both ValueError at the engine boundary; ramp_summary's env generate refuses); the env lane pins the LITERAL four placements. The composed-image ink checks are KEPT (live: the crop composer). The workbook-panel unit blocks are KEPT as marked DORMANT-CODE LOCKS. The end-to-end call-site lock is REPLACED: one vs-TSN example driven through `_try_example` on the PRINT path over two hand-built valid blank-page PDFs — agreement renders with the verification subline and no note; a disagreeing TSN print still renders WITH the "print reads '…'" disclosure and a DISAGREES subline while the workbook entry keeps the COMPARED values; and a target outside the record's own lines is refused by the engine backstop | 004, 007, amendment |
| `build/check_evidence_manifest.py` | The stated-contract block asserts the print-crop contract (four rows, four env placements); `run_generate` fixtures ported to `intersection_detail_pdf` with stub prints in a subdir + a sandboxed TSN library (unparseable stubs make every candidate a locate miss — the no_examples terminal reached the amended way); the cancel boundary moved to the locate step (`_locate_tsmis_sources` stub); KEPT: bound fixtures, every terminal state recording itself, the unbindable-pair NOTHING-published case, the env fixture lanes (front-door census, swapped-role refusal) | 004, amendment |
| `build/check_evidence_excel_columns.py` | Seam test on `_workbook_side` ctx + per-family hook probes — KEPT as dormant-code locks (the panel hooks still exist; RD July-2026 dual-edition resolution among them) | 004 (dormant) |
| `build/check_evidence_literal_cells.py` | Literal-cell safety over the writer fixtures (unchanged — the writer still writes summaries/captions); the contract block names the dormant panel renderer as dormant | 004 |
| `build/check_matrix.py` | `build_cell_comparison(evidence=)` accepted; an XLSX env cell stays SILENT with the toggle on; the env camera refuses non-env rows, refuses ramp_summary (no evidence lane at all), and refuses an env-capable cell with no comparison (fixture: ramp_detail_pdf) | 007, amendment |
| `build/check_pdf_excel_matrix.py` | The by-day PDF-vs-Excel lane writes ZERO evidence artifacts (criterion 5's silent control). A bare "the glob found nothing" reads the same whether the lane is silent, the tree is the wrong one, or the pattern is broken — so the probe is CONTROLLED first: an evidence-named artifact is planted where one would land, the probe must see it, and only then is the lane's own silence read | 004 |
| `build/check_pdf_route_identity.py` | The engine-half identity pin covers `_locate_env_sides`; `_locate_tsmis_sources` (restored) carries the same RouteIdentityError-exclusion contract, exercised by check_visual_evidence's fixtures | wiring |
| `build/check_matrix_ownership.py` | The evidence-dispatch stub accepts `mode_id` | wiring |
| `build/check_tsn_canonical_consumer_identity.py` | The evidence entry points' TSN-identity forwarding fixtures ride `highway_log_pdf` (the Excel row is refused before the identity gate under the amendment; the TSN dataset key stays `highway_log`) | wiring, amendment |
| `build/run_rb4_acceptance.py` | NEW — the committed `RB4-A1` driver (provision / generate / cameras / counts / validate / excel / census / checks-at-base phases; worker-parity leases and commit guards; per-phase JSON results + logs; every phase result SELF-STAMPS the tree's exact git head + a runtime-scoped dirty flag — the RB-2 lesson). **Amended populations (2026-08-05):** the comparison universe is unchanged (26 cells across TSN_ROWS/SELF_CELLS/ENV_CELLS/by-day) while `EVIDENCE_ROWS` declares the four `_pdf` rows — 12 evidence sets required, 14 placements REQUIRED-SILENT (their manifests FORBIDDEN, the discovery glob proven live by a planted control); `assert_declared_counts` cross-checks the declared rows against `visual_evidence.rows()`/`env_rows()` so driver and engine cannot drift; `phase_cameras` runs 12 cameras + 5 engine-boundary REFUSAL probes (4 Excel-row tsn + ramp_summary env, each required to refuse with its reason); `phase_validate` re-derives the tsn read-set shape (two compared workbooks + PDF members under the two DECLARED print folders), re-derives the TSMIS side 100 % through the adapter's own locate walk with the disagreement-note contract closed both ways (a disagreeing print must be disclosed; an agreeing one must not carry a false note), records the TSN side's verification scope explicitly (generation parse-back + the native-scale image inspection), and keeps the env re-derivation + value-length/blank-side censuses; `BASE_CHECK_EXPECTATIONS` re-derived at the base tree for the amended checks (8 red / 2 green) | acceptance, amendment |
| `docs/…/rb4-verify-manifest.py` | NEW — the committed fail-closed verifier (RUNTIME / LINEAGE / EXACT HEAD with self-stamps / BASE TREE / WITNESSES / `--corpus` with the sha-bound detached inventory / `--zips` archive re-match / `--self-test` negatives) | acceptance |
| `docs/comparison-engine.md` §13, `docs/gui.md` | The documented contract is the print-crop rule: §13 states the amendment (crops on the `_pdf` families, the disagreement disclosure, the engine-boundary refusals, the dormant renderers); gui.md's badge/camera/hint paragraphs follow | docs |
| `hotfix-bundles/RB-4/BUNDLE.md` | Base `main` SHA filled; the 2026-08-05 owner amendment section added (it controls over the frozen text; HF-05 required-behaviour superseded in place; HF-10 rescoped to four cells) | — |

## Root cause confirmed

Exactly as the bundle records, re-verified in code before any change:

- **004:** `generate()` selected render sources by ROW SHAPE (`role_a = "pdf"
  if row endswith _pdf`, `role_b = "tsn"` → the library print folders), while
  every vs-TSN/self comparison actually reads two WORKBOOKS
  (`compare_tsn_common.run_files_compare` receives exactly two paths and never
  opens a per-route PDF; all five self comparators load the two consolidated
  editions). The workbook then asserted "Red box = the compared cell in each
  source PDF" and declared a `TSMIS PDFs:` directory absent from its own read
  set (`visual_evidence.py` old `:1421-1424`, `:1528-1530`).
- **005:** the blank-side fallbacks guessed where an absent value "would
  print": HL boxed a fixed band BELOW the record (`tsn_box` old `:480-484`,
  `tsmis_box` old `:348-353` — the next record's zone), HSL's fixed windows
  caught the printed `EQUATES TO` words on collapsed equate lines (`tsn_box`
  old `:577-586`) and its no-segs Description guessed a fixed zone ~100 pt
  right of the text (`:568-571`).
- **006:** `_excel_strip` drew `text[:26]` / `label[:24]` with no marker while
  sizing the column for the FULL value.
- **007:** `matrix_build.build_cell_comparison` took no evidence argument;
  `visual_evidence` knew only two flavors; `build_comparison` dropped the
  `evidence` request on the floor for env cells; ramp_summary had no adapter.

One discovery beyond the plan's letter, disclosed: the env comparison's
provenance records each side's RUN-FOLDER ROOT as `selection` while its census
lists the per-route files — the engine therefore resolves the report subdir
through `compare_env._find_input_dir` (the comparison's own resolution) rather
than assuming a layout. No scope expansion: the binding contract is unchanged,
only the resolution is the comparator's own.

## The 2026-08-05 amendment — what happened and why

The first implementation carried the audit's remedy faithfully: since a vs-TSN
comparison reads two workbooks, both evidence panels were REDRAWN from those
workbooks. The first RB4-A1 run passed every phase on that contract. Then the
owner looked at the images and rejected the remedy itself: **a panel rendered
from a compared workbook is circular** — it re-states the comparison's own
read, so a human holding it against the comparison sheet can never catch a bad
parse. The entire value of evidence is that the crop comes from the PRINT, one
step OUTSIDE the compared workbook: "the whole point was that the evidence
collection was separate and that if some dude looked at the pdf it would line
up with the comparison sheet — that's the ONLY reason this is even a valid
spot check." Three rulings followed (transcribed in BUNDLE.md's amendment
section): print crops or nothing; evidence only for the `_pdf`-edition
families (12 cells — Ramp Summary's env cell removed by the report-type rule);
everything else refused at the engine boundary with the UI showing the icon
only where evidence exists.

What this record keeps from the first implementation, because the audit's
findings there were real: the provenance binding and no-artifact refusal
(004's discipline), the blank-side geometry refusals (005 — now
engine-enforced on every print lane via `_box_within_record`), the truthful
Summary/legend/read-set declarations, and the env lane (already print crops).
What it reverses: the render source (crops, not panels) and the silent
disagreement drop — the old engine DROPPED an example whenever the print
disagreed with the compared value, hiding exactly the parser-bug signal the
spot check exists to catch; a disagreement now renders WITH a disclosure note
on the image and in the Summary's Note column. 006's drawn-string surface
retired with the panels (crops draw no strings; the value-length census stays
as inspection guidance).

## Design (as amended 2026-08-05)

1. **The registry IS the engine-boundary refusal.** Evidence exists exactly
   where `_ADAPTER_MODULES`/`_ENV_ADAPTER_MODULES` say it does — the four
   `_pdf` rows in the tsn and env lanes. Every consumer (the toggle-driven
   decoration, both cameras, the day-matrix camera, the UI badge/actions, the
   Settings panel) gates through `capable()`/`env_capable()`, so removing a
   row from the registry removes the capability EVERYWHERE at once, and
   `generate()` refuses FLAVOR_SELF and unregistered rows before touching a
   source. "Shouldn't be possible" is a registry fact, not a UI style.
2. **The comparison binds; the prints render.** The comparison-side binding
   from the first implementation is unchanged (provenance sidecar +
   trusted/current typed outcome + workbook sha digests / env census; an
   unbindable pair publishes NOTHING and retires any prior set, before
   proposals). The prints the crops come from resolve through the product's
   own contracts — the run-folder subdir per route via `find_route_print`
   (dated/legacy/store-tagged), the TSN library print dirs — are
   snapshot-copied with the workbooks, byte-stable at the commit boundary,
   and declared honestly in the Summary and the manifest read set.
3. **Parse-back verifies; disagreement DISCLOSES.** Each crop's value is read
   back through the adapter's LOCKSTEP walk. Agreement makes the image an
   end-to-end check of the comparison at that cell; disagreement renders WITH
   a note on the image and in the Summary's Note column and a subline that
   says DISAGREES — never the old silent drop, which hid exactly the
   parser-bug signal the spot check exists to catch. (The env lane keeps its
   stricter COMPOSE-to-published refusal: there the print values ARE the
   compared values, so non-composure means a wrong locate, not a signal.)
4. **One containment backstop for every print lane.** `_box_within_record`
   (both axes) refuses any target rectangle outside the captioned record's
   own printed lines/width, whatever an adapter returned — the
   PCOA-FINAL-005 rule, now shared by the tsn and env paths.
5. **Blank targets never guess.** A field with no cell rectangle inside the
   record's own printed lines refuses with a recorded reason (HL blank
   Descriptions, HSL equate-line fields); a fixed-window column's blank cell
   still boxes its own window clipped to the record's line. Honest misses
   over plausible-but-wrong boxes.
6. **Decoration stays decoration.** Evidence rides AFTER
   `require_published_comparison` + COMPLETE, failures only log, and both
   cameras carry the same freshness discipline (trusted / current /
   generation-bound / input-fingerprint-unchanged).
7. **The retired renderer is dormant, not deleted.** The workbook-panel chain
   stays in code with unit locks marked DORMANT-CODE LOCKS — per the ruling,
   and as the ready-made panel path should a future ruling revive it.

## Focused checks — red at base, green at head

Method: the ten extended check files are overlaid onto a staged copy of the
exact base tree and run there (`run_rb4_acceptance.py --phase checks-at-base`;
recorded in `results/base-red-checks.json`), and the full gate is run at the
frozen head (`results/checks-at-head.json`).

Each check declares in the driver whether it must be **red with a named failure
signature** or is a **green control**, and the phase fails unless every check
classifies as declared. A check that dies on a load-class error without printing
its signature is `inconclusive` — never counted as red.

**A first pass exposed a weakness in this evidence.** Five of the ten checks
proved nothing at base: each called a function or keyword the hotfix ADDS, so
the run died on the first new call and printed no failure at all. That failure
says "this API is new", never "the old behaviour was wrong". Each of the five
now states the contract it depends on up front and asserts it, so the base run
names what is missing on its own output before it stops. **Red-at-base went from
three of ten checks to eight, with two declared green controls.**

The signatures were RE-DERIVED at the base tree after the 2026-08-05 amendment
edited the check files (a red-at-base claim binds the check file, not the
finding — an edited check has no standing until re-run). The chain7 re-run
classified all ten as declared: **8 red / 2 green / 0 inconclusive**.

| Check file | At base `72adf44` | Signature bound (its own stdout) |
|---|---|---|
| `check_visual_evidence.py` | red | `the read set is captured in labelled per-side buckets, so a manifest names the documents each side's crops were read from` |
| `check_evidence_source_role.py` | red¹ | `the vs-TSN lane renders PRINT CROPS on both sides (tsn_ctx replaces the workbook side ctx in _try_example)` |
| `check_evidence_manifest.py` | red¹ | `the vs-TSN lane locates PRINTS (_locate_tsmis_sources) and evidence exists only for the four `_pdf` rows` |
| `check_evidence_excel_columns.py` | red¹ | `FAIL: July District also resolves to its Location cell` (RB-3's deliberately deferred evidence half; a dormant-code lock since the amendment) |
| `check_evidence_literal_cells.py` | red | `a drawn panel string is full or visibly elided (panel_cell_text)` |
| `check_matrix.py` | red | `a cell comparison can be asked for evidence` (PCOA-FINAL-007's root cause) |
| `check_matrix_ownership.py` | red | `the frozen MODE is routed into evidence_for_cell` |
| `check_pdf_route_identity.py` | red | `FAIL visual_evidence._locate_env_sides exists` |
| `check_pdf_excel_matrix.py` | **green control** | the silent lane was already silent; the new assertion is a must-not-regress lock, not a red→green |
| `check_evidence_bundle.py` | **green control** | likewise |

¹ printed its declared signature, then died on `AttributeError` — expected for a
check that also covers an API the hotfix adds. Recorded as
`died_after_signature`, not downgraded.

**The gate itself was audited for teeth, by mutation.** Reverting a fixed
behaviour in the engine must make some check go red; where it did not, the
behaviour was unguarded and the check was written. Found and closed this way:

- `_display_header` and `_normalization_note` each had ONE production call site
  and no check asserted the call site — deleting either line passed the entire
  gate. One example was driven end to end through `_try_example` to close it.
  *(Both helpers went dormant with the panels under the 2026-08-05 amendment;
  that end-to-end lock was REPLACED, not dropped — the same fixture now drives
  the PRINT path and asserts the crop captions, the disagreement disclosure,
  and the containment refusal, so the live call site is still locked at its
  call site rather than in a unit.)*
- The composition geometry assertions were **circular**: they sized the
  expectation with the same width helper the composer sizes the canvas with, so
  a regression that halved every measurement satisfied both sides. They now
  measure the image's own ink.
- Fifty hook assertions only proved an attribute existed — which a stub
  resolving every field to column 0 also satisfies. Each hook is now probed for
  what it must guarantee.
- The engine's x-axis containment backstop, the Highway Sequence blank-cell
  window, the ambiguous-print refusal, the stale duplicate header label, the
  env side-order assertion, and the env front-door census binding were each
  unguarded; each now has a check that goes red when it is reverted.
- The by-day silence probe could not tell silence from a broken probe. It plants
  a positive control first.

The env front-door case is worth naming: the existing census-drift test rendered
an example first, so the snapshot-time binding caught the drift too and deleting
the front-door check still passed. The front door exists for the paths that
publish a manifest WITHOUT rendering anything, so the case that locks it is a
no-differences comparison with a drifted source.

The DATA-level pre-fix signatures bind to the base runtime through the
base-side generation itself: the read sets of the base-side evidence
manifests name the prints the old engine borrowed — 12 TSN district prints on
the Highway Log cell, and **110** per-route PDFs on the Highway Log PDF cell
(109 on its By Day twin) — alongside the `TSMIS PDFs:` declarations and the
`text[:26]` drawing rule. Counted from the retained base manifests, not from
the audit's prose.

## RB4-A1 — the one executable acceptance run

Driver: `build/run_rb4_acceptance.py` (committed). Root:
`…\_scratch\post-comparison-hotfixes\HF-05\rb4-a1\`. Every phase drives the
same entry points the GUI workers drive — `matrix.build_comparison` under the
worker's own owned-dir leases and commit guard, `day_matrix.build_day_cell`,
the on-demand cameras, and the classic + PDF-vs-Excel silent controls — against
the frozen 2026-07-23 and 2026-07-09 pulls.

**Four complete runs; the last is the acceptance.** The first (chain6, head
`a21e0ba`, 2026-08-05) executed the original workbook-panel contract end to end
and passed every phase — its images are what the owner rejected, producing the
amendment. Its COMPARISON-layer results stand as proof that the panel-era
engine also never touched comparison content, and its base-side records (the
unrepeatable 7.5 h base generation, `counts-base.json`, the base-tree content
binding) carry forward into every later run.

The evidence layer was then reimplemented to the print-crop ruling and the
ENTIRE head side re-produced three times, each at one new frozen head with the
prior head comparisons retired first, so every run's record is one generation
end to end. **Each re-run exists because that round's native-scale image
inspection found a real defect the 158-check gate had passed** — chain7's
inspection found 9 (undisclosed normalization; a Ramp Detail box swallowing two
neighbouring columns; a trailing blank drawn outside the record), and chain9's
found 3 more, all the same trailing-blank class, because the chain7 fix had
refused only an EMPTY window overlap and left the graze case drawing a sliver.
Everything below describes **chain10** unless it says otherwise.

**The fixes the inspections forced, in order.** `1861033` retire a
pre-amendment set beside a now-refusing cell · `c7b75e4` disclose a print token
that normalizes to the compared value (the raw-token hooks) · `82961ef` box the
Ramp Detail District cell alone; refuse a trailing blank on the TSMIS side ·
`c974a00` mirror both of those to the TSN side, where `_normalize_row` had been
rewriting the row in place so the disclosure hook returned the compared value
itself · `f4b55f2` replace the overlap threshold with the rule the geometry
actually supports: a blank cell is boxable only where the record's own ink
BRACKETS the column, left and right. Every one is locked by a check that goes
red against the behaviour it replaced.

**Inputs (frozen, hash-bound).** The 2026-07-23 raw extract the output audit
itself measured; the ground-truth 7.9 ssor and ars pulls (each member re-matched
against `All Reports 7.9.zip` / `ramp_summary_excel.zip`); the Downloads TSN
master library's raw/pdf sources. Provisioned into per-side replica stores
created the way the app creates one (`owned_dir.ensure_owned_dir`). Highway
Detail is excluded everywhere (⛔ pre-release).

**One frozen head, and a harness that fails closed.** The chain script is a
gate: it aborts on the first failing phase rather than echoing an exit code and
continuing, and after every phase it re-asserts both that the runtime files are
clean AND that `HEAD` has not moved. Every retained result SELF-STAMPS that
head plus a runtime-scoped clean/dirty flag; the base side stamps the base
commit, read from a content binding that compares each base-tree runtime file
against the base commit's own git blob. The populations are DECLARED constants
cross-checked against the engine's own registry (`assert_declared_counts`), so
the driver cannot validate a population the product does not produce.

Order: full gate at head → base-tree binding → the same (amended) check files
at base → retire the prior head → generation → cameras → validate → excel →
counts → census.

| Phase | Result (chain10, head `f4b55f2`) |
|---|---|
| checks at head | **158 / 158** (`results/checks-at-head.json`) |
| base-tree binding | 151 / 151 runtime files identical in content to `72adf44` |
| checks at base | **8 red · 2 green controls · 0 inconclusive** (signatures re-derived for the amended check files, including the bracketing locks) |
| generate | 35 cells (8 Everything vs-TSN · 5 SELF · 5 ENV + 5 ENV evidence-OFF controls · 8 By Day · 4 PvE silent controls) — **0 non-ok**; evidence rendered on exactly the 12 `_pdf` placements; both classic Compare controls ok, planted probes seen, 0 control problems |
| cameras | **12 / 12 ok** (4 vs-TSN · 4 By Day · 4 env) **+ 5 / 5 refusal probes REFUSED** (the 4 Excel-row tsn cameras and ramp_summary's env camera, each with its declared reason) |
| validate | **12 evidence sets · 876 checks · 0 failed · 0 problems**; population `required 12 · forbidden 14 · discovered 12 · missing/extra/forbidden-present/duplicate 0`, the discovery glob proven live by a planted control |
| excel | **12 / 12** evidence workbooks opened in INSTALLED Excel, Ledger present in all, **336 embedded pictures** (exactly the 336 images on disk), 0 repair logs; **26 / 26 formulas twins settle** to their values workbook's totals |
| counts | 26 typed sidecars re-read — **26 / 26 identical** to the base runtime (every substantive field; only `generation_id` differs, which a rebuild necessarily changes) |
| census | ok (the audit/base-era recounts unchanged — those roots predate the amendment) |

The chain ran 20:38 → 16:50 (20 h 12 m): generation 13 h 36 m, cameras 2 h 16 m,
validate 1 h 07 m, the Excel leg 2 h 11 m — the twin recalculations are a full
rebuild of workbooks up to 250 MB. (chain9 measured the same phases at 10 h 48 m
/ 1 h 58 m / 1 h 07 m / 2 h 11 m on an otherwise idle machine.)

**A cost note for whoever runs this next.** The runtime diff behind chain9 and
again behind chain10 touched only `scripts/evidence_*.py`, and `counts` re-proved
26/26 both times — so ~11 h of each run recomputed byte-identical comparison
workbooks. `harness/rb4_chain_evidence_only.sh` now exists for exactly that
case: it keeps the retained head-side comparisons and re-runs cameras → validate
→ excel → counts, but only after PROVING eligibility (the retained generation's
self-stamp and all-ok status, and that every runtime file changed since it is an
evidence adapter — anything else aborts). `counts` still runs, so a comparison
that did move is caught rather than assumed absent. It aborts correctly on the
bundle-wide diff (15 files, 9 non-evidence).

**The repository gate, all four legs, at that same frozen head:**
`run_checks.py -j 4 -k` **158/158** · `compileall` clean · `ruff check scripts`
clean · `build.ps1 -SelfTest` **PASSED** — the exact shipped exe runs every code
path, including the evidence render stack.

**What the 12 sets are.** 336 examples across the four `_pdf` families — the
final on-disk sets are the CAMERA phase's regeneration at the shipped Settings
default (`pair` layout, one PNG per example), which is exactly what a user's
per-cell camera produces:

| Lane | Sets | Examples |
|---|---|---|
| Everything vs-TSN | HL-PDF 58 · ID-PDF 48 · RD-PDF 17 · HSL-PDF 4 | 127 |
| By Day vs-TSN (2026-07-23) | the same four families | 127 |
| Everything ENV | HL-PDF 56 · RD-PDF 10 · HSL-PDF 8 · ID-PDF 8 | 82 |

The set is six smaller than chain9's 342, all six in the Highway Log cells:
the bracketing fix refuses a blank whose column the record's own ink does not
reach. One consequence is deliberate and worth knowing: **`Sig Chg. Date` now
renders no evidence at all** in the three Highway Log sets (18,250 counted
differences in the vs-TSN lanes, 2,821 in env). It is the last column, so a
blank there can never be bracketed, and an example needs BOTH sides to yield
geometry. This is disclosed, not silent — each Ledger carries the reason — and
non-blank cells are unaffected, so a both-sides-printed difference still renders
(chain9 drew one: route 395 @ 057.935, TSMIS `960101` vs TSN `000905`). Detail
and the sampler question it raises: `results/chain8-known-gap.md`.

**The independent re-derivation, 100 % — no sampling.** For every vs-TSN and
By Day example, `phase_validate` re-located the route's own per-route print
through `find_route_print` + the adapter's LOCKSTEP walk and re-read the boxed
value: **254 / 254 TSMIS-side values re-derived**, with the disagreement
contract closed both ways — a re-derived value that differed from the compared
one would REQUIRE the image's "print reads '…'" disclosure, and an agreeing one
must carry no false note. **This corpus produced 0 disagreements**: every crop's
parsed value equals the compared value, so the disclosure path is proved by the
focused checks (a live end-to-end fixture) rather than by this run's data. The
TSN side's scope is recorded, not hidden: its verification is the generation's
own parse-back plus the native-scale image inspection — a full TSN district
re-parse per set would repeat the generation's slow half. For the env lane,
**82 / 82 examples** were independently reproduced end to end from the two
environments' own prints — re-located, re-boxed inside the captioned record,
re-read — with 0 failing checks.

**Read sets are prints, declared honestly.** Every rendered vs-TSN set's
manifest carries the two compared workbooks by recorded sha PLUS the prints the
crops were read from (453 print members across the 12 sets), and every print
member is required to be a `.pdf` under one of the two folders the Summary
itself declares (`TSMIS PDFs (read):` / `TSN PDFs (read):`). Env read sets
remain census-bound per side, member for member.

**Recounts.** Blank-side targets (the PCOA-FINAL-005 population — the hardest
crops, where the box marks an EMPTY position inside the record's own line):
**117** across the 336 examples, every one listed by identity for the image
inspection. The audit-era exhaustive recounts (`phase_census`) are unchanged
from the first run — they census the pre-fix roots, which the amendment does
not touch: Audit Everything 529 examples / 10 over the 26-char limit / 208
blank-side; Audit By Day 359 / 7 / 132; Base Everything 357 / 4 / 141; Base By
Day 241 / 5 / 84. The audit By Day root has no frozen copy, so it is declared
UNBOUND in the manifest and its identity rests on the Stage 1B witness hashes,
all of which still match.

**Required-silent cells, proven silent.** The 14 required-silent placements (4
Everything Excel-tsn · 4 By Day Excel-tsn · 5 SELF · ramp_summary ENV) each
built their comparison and produced NO evidence artifact of any kind — their
manifests are declared FORBIDDEN in the population check, which found none. The
by-day PDF-vs-Excel lane ran with the toggle ON and produced zero artifacts;
each ENV cell was additionally built evidence-OFF first (count parity on/off).
The classic Compare tab's comparator ran for real in both lanes (file 389.7 s,
folder 1106.3 s), returned ok, and wrote zero evidence artifacts. Every silence
reading — the classic sweeps, the PvE tree, validate's manifest glob — is
preceded by a **planted positive control** the probe must SEE before the real
tree is read; all probes saw their plants.

**Count/mask invariance.** All **26 / 26** cells compare equal between the base
runtime and the head across every substantive field: verdict, completion,
`trusted`/`current`/`known`/`present`, paired rows, both one-sided counts,
differing rows, differing cells, asserted/context cells, pairing quality, and
the full per-field table. The two sides are bound to different runtimes —
`counts-head.json` self-stamps `adfa9f4`, `counts-base.json` self-stamps
`72adf44`, and the base tree is proven by content to BE `72adf44`. The five ENV
comparisons (ramp_summary's included — its COMPARISON still builds; only its
evidence is silent) reproduce the output audit's own measured numbers EXACTLY:
Ramp Summary 67; Intersection Detail PDF 17,562; Ramp Detail PDF 376 + 5/8
one-sided; Highway Log PDF 88,238 + 2,095/1,174; Highway Sequence PDF 1,904 +
7/246 — PCOA-FINAL-007's own figures.

**Formulas-twin settlement.** Every twin was opened in installed Excel, fully
recalculated, and its Status/Diffs totals read back by header label: **26/26
agree, 0 disagree, 0 excused**, twin expectancy taken from the producer's own
probe.

**Individual native-scale image inspection.** The bundle requires EVERY
retained image inspected, not sampled. The population is proved complete by
construction: `acc_rb4_inspect_manifest.py` reconciles every PNG on disk
against the Summary rows that claim it — an unclaimed image or a
claimed-but-missing one is a recorded problem (**12 sets · 336 images · 0
problems**), the workbook legends must match each set's flavor, and a SELF set
existing at all would itself be a finding. The set was partitioned into 11
slices and inspected image-by-image at native scale against the print-crop
criteria (box on the compared cell within the captioned record, blank-side
targets in the record's own empty position, no clipping, separated captions,
captions naming a print + page, the disagreement contract, and any
workbook-style panel an automatic FAIL).

The historical context that justifies this cost: the inspection of the PRE-fix
set (825 images, retained as `results/inspection-round1.json`) returned **39
failures in six classes — every one a real defect that all 158 programmatic
checks had passed** (shifted strip labels; undisclosed normalization; clipped
titles; overprinted captions; composite source cells; route-prefix
over-enclosure). Those classes are now locked by checks where their surfaces
survive, and the mutation audit that hardened those checks is described in the
focused-checks section. The chain6 head's 838 workbook-panel images were
retired with their sets — that inspection round is history, not a claim about
the accepted set.

**The chain10 inspection's result.** 11 concurrent agents, one per round-robin
slice, every image read at native scale: **336 inspected · 335 passed · 1
finding · 0 unreadable** — the finding being `RB4-R1-001`, which the owner's
2026-08-09 ruling reclassifies as a disclosed limitation, making the retained
set 336/336 under the amended criterion. Recorded as run in
`results/inspection-chain10-round1.json`
(its arithmetic reconciles six ways against the slice sums, the manifest count
and the defect-class instances). This round's agents located red rectangles by
pixel scan rather than by eye, measured box and glyph bounds, counted ink INSIDE
blank boxes, scanned all four canvas edges programmatically, and cross-checked
column identity against the repo's own SoT (`docs/highway_log/columns.md`,
`evidence_intersection_detail._TSMIS_CELL`, the `S`→`PS` relabel) and against
the prints' own headers wherever a crop band contained one.

**chain9's three trailing-blank slivers do not recur**, and no slice found any
degenerate or displaced Highway Log box — the class was checked by name in most
slices. Also clean across all 336: no workbook-style panel anywhere (the
amendment's central claim), every caption naming a `.pdf` + page, no clipping,
no overprinted captions, no multi-column box, correct record targeting, and the
normalization disclosure honoured on every noted image — one slice verified
programmatically that a note band appears on exactly the images whose manifest
entry carries a note and on no others.

**The one finding is documented, not fixed** —
`intersection_detail_pdf_tsn / ML_Traffic_Flow_1_pair.png` (route 232 @
000.807). Its blank box sits ~165 px right of that record's last glyph and,
uniquely in that crop, no record in view prints in that region, so nothing
anchors the column for a reader. It is NOT the Highway Log defect and NOT
mis-targeted: `evidence_intersection_detail._box_at` boxes a blank cell with
`meta["edges"][idx]` — the print's OWN ruled cell rectangle from the PDF's rect
objects — so the box IS that column's real cell and its width is that cell's
real width. What it lacks is a way for a human to CONFIRM that, because the
cell boundaries are geometry rather than stroked rules. Five other slices
examined similar Intersection Detail trailing blanks and passed each after
finding an anchoring value in an adjacent record, so the anchor is normally
present. A real fix means extending the crop band to reach an anchoring record
or the print's own header — a change to band selection with its own risk, not a
patch — or extending Highway Log's bracketing rule to Intersection Detail,
which would refuse this crop but also the many ID trailing blanks a reader CAN
anchor, since that rule bans anchoring off a neighbouring record. Incidence
1 of 336. **The owner inspected the image on 2026-08-09 and ruled it
acceptable** ("this is fine, just document it"); the ruling and its limits are
in [BUNDLE.md](BUNDLE.md), and the measurement stands with the two other
coverage notes in `results/chain8-known-gap.md`.

**A harness defect the round also found and closed.** Three slices reported
their scratchpad files being silently rewritten mid-run: all 11 agents share one
scratchpad directory and chose colliding filenames. Each detected it (one
because the content was visibly from another report), abandoned the shared file
and re-verified. Exposure is bounded — each image's PRIMARY read always goes to
its real path, only derived zoom crops land in the scratchpad — and
`INSPECTION-PROMPT.md` now requires a per-slice subdirectory plus disclosure if
a written file comes back unexpected.

## The bundle's measurable criteria, as amended — where each one is met

The criteria are BUNDLE.md's, read through the 2026-08-05 amendment (which
supersedes the panel-fidelity criterion and rescopes HF-10 from five cells to
four).

| # | Criterion (amended) | Where it is met |
|---|---|---|
| HF-05 · 1 | Zero artifacts — manifest included — for a pair that cannot bind; and the required-silent cells emit nothing | `phase_validate` population: `required 12 · forbidden 14 · discovered 12`, 0 missing/extra/forbidden-present/duplicate, behind a planted control. The unbindable-pair terminal is locked by `check_evidence_manifest` (nothing published, prior set retired) |
| HF-05 · 2 | *(superseded)* every drawn panel string equals the compared value or is visibly elided → **every crop's value is re-derived from the print, or the disagreement is disclosed** | 258/258 TSMIS-side re-derivations in `phase_validate`, disagreement contract closed both ways; 0 disagreements in this corpus, so the disclosure path is proved by the end-to-end fixture in `check_evidence_source_role` |
| HF-05 · 3 | 100 % of blank-side examples: target inside the captioned record, touching no other record or field | 117 blank-side examples, all listed by identity; the engine refuses any box outside the record's own lines/width (`_box_within_record`, both axes, both print lanes) — locked by `check_visual_evidence` + the source-role end-to-end fixture; visually confirmed by the native-scale inspection |
| HF-05 · 4 | No prose asserts an unread source | Summary declares the compared selections PLUS the two print folders actually read; validate asserts every non-workbook read-set member is a `.pdf` under a DECLARED folder (453 print members); legends pinned per flavor |
| HF-05 · 5 | The two already-correct paths still emit nothing | Classic Compare comparator driven for real in both lanes (file 389.7 s · folder 1106.3 s) + the by-day PvE lane with the toggle ON — zero artifacts, each read behind a planted control |
| HF-05 · 6 | All comparison counts and typed outcomes unchanged | 26/26 typed sidecars identical base↔head across every substantive field |
| HF-05 · 7 | Full gate green; every new assertion fails pre-fix | 158/158 at head + compileall + ruff + frozen self-test; 8 red / 2 green / 0 inconclusive at base, signatures re-derived for the amended check files |
| HF-10 · 1 | All four `_pdf` env cells produce a bound manifest, workbook and image set with a PDF-only read set | 4 env sets, 82 examples, census-bound member for member; ramp_summary's env cell builds its comparison and is proven silent |
| HF-10 · 2 | 100 % of retained crops accurate and readable, reviewed individually — as amended 2026-08-09 (an anchorless blank drawn from the print's own cell rectangle is a disclosed limitation, not a failed crop) | 336 images (12 sets), population proved complete by construction (0 unclaimed / 0 missing), inspected image-by-image at native scale: **336/336** under the amended definition. 0 mis-targeted / multi-column / clipped / out-of-record / undisclosed. The one anchorless blank raised as `RB4-R1-001` is retained and disclosed with its measured incidence (1 of 336) in `results/chain8-known-gap.md` |
| HF-10 · 3 | Env comparison counts identical with evidence on and off | Each ENV cell built evidence-OFF first, then ON; counts equal, and equal to the audit's own measured figures |
| HF-10 · 4 | No other lane's evidence behaviour changed | The 14 required-silent placements are FORBIDDEN in the population check and none appeared; 5/5 camera refusal probes refused at the engine boundary |
| HF-10 · 5 | Full gate green; the new assertions fail pre-fix | as HF-05 · 7 |

## Scope and residual risk

**Files outside the bundle's named union.** The bundle expected
`scripts/visual_evidence.py`, the `scripts/evidence_*.py` adapters,
`scripts/matrix_build.py`, the `scripts/day_matrix.py` / `scripts/gui_matrix.py`
guards, and checks. Six changed files sit outside that union, each named in the
Changes table and each a consequence of the lanes' capability surface rather
than a widening of the fix:

| File | Why it had to change |
|---|---|
| `scripts/matrix.py` | facade re-export of `run_env_evidence_only`; the facade is the patch surface every caller uses |
| `scripts/gui_api.py` | the `unsupported` hint list — under the amendment it names every row without an evidence lane, per row, so the toggle's hint states exactly what will and won't generate |
| `scripts/self_test.py` | the dormant `evidence_ramp_summary` module still ships in the frozen build, so the import census must declare it |
| `scripts/ui/ui-matrix.js`, `scripts/ui/mock.js` | the hint/badge/action gating must reflect the capability rule (icons only where evidence exists), and the mock must stay at parity |
| `build/app.spec` | same frozen-build reason as `self_test.py` |

`scripts/day_matrix.py` gained one guard inside the union's spirit: the by-day
camera refuses a required-silent row with a clean sentence (the engine refuses
regardless). Its comparison lane is otherwise untouched.

**⛔ Highway Detail: code changed, never exercised.** `evidence_highway_detail.py`
gained the four shared-contract hooks so the engine stays uniform across
adapters. HD is PRE-RELEASE, so **no HD cell is exercised anywhere in RB4-A1** —
not in generation, not by a camera, not in the inspection. Its hooks are covered
only by the check-level probes. Nothing here re-blesses an HD canary, changes an
HD parser or normalizer, or infers an HD fact; when the vendor delivers official
HD exports, the HD evidence lane needs its own first exercise before it is
trusted.

**The env lane's coverage is four cells on one day.** HF-10 as amended is
proved on the four `_pdf` Everything ENV cells of the acceptance corpus
(ramp_summary's cell builds its COMPARISON and is proven silent). The geometry
adapters were fixed against that corpus's prints, and several needed a
probe-driven fix to work at all — which is evidence that env geometry is
corpus-sensitive. A print whose layout differs from these will REFUSE (that is
the designed failure), but "refuses correctly" is asserted only for the shapes
this corpus contains. The vs-TSN crops carry the same caveat: the TSMIS/TSN
locate walks are LOCKSTEP mirrors of the shipped parsers, pinned by checks,
and exercised here on this corpus's prints.

**One inconsistency, disclosed rather than fixed.** `_snapshot_read_set`'s
same-basename guard raises `EvidenceSourceBindingError` from a call site that is
NOT inside the `refuse_binding` wrapper, so unlike every other binding refusal in
the module it would not retire a stale prior evidence set. It was traced as
unreachable under the current naming conventions — two routes cannot collide on
one basename inside a directory given the end-anchored `…_route_<token>` contract,
and the two compared-workbook basenames are distinct constants per report edition
— so it is a defensive backstop rather than a live bug. The 2026-08-05
amendment reopened the runtime and this was left as-is deliberately: the
amendment diff stays scoped to the owner's ruling, and the guard remains
unreachable under the same naming contracts (the restored tsn print buckets
keep per-route-distinct basenames the same way the env buckets do).

**The parse-back check has a blind spot, and the crop is what covers it.**
Each crop's value is re-read by the adapter's LOCKSTEP walk — a deliberate
mirror of the shipped consolidator parser. So the automated check catches
ADDRESSING errors (wrong row, wrong column, wrong route, a key that resolves
ambiguously) but CANNOT catch a systematic parser misread: the mirror would
reproduce the same wrong value the consolidated workbook holds, the two would
agree, and no disagreement note would fire. That is not a gap this bundle can
close in software — it is the exact reason the owner ruled evidence must be
crops of the actual print: the IMAGE carries the document's own glyphs, so a
human comparing the crop against the comparison sheet sees a systematic
misread that no self-consistent parser pair ever will. This run produced 0
disagreements across 336 examples, which says the addressing is right and says
nothing about the parsers — the native-scale inspection and the owner's own
use of these sets are what speak to that.

**What the acceptance run does not prove.** Excel opens every retained workbook
without an open failure; because the driver runs with `DisplayAlerts=False`, a
SILENT repair is not detected, so this is not a zero-repair claim. Image
correctness is established by exhaustive native-scale human-equivalent
inspection plus programmatic validation of every retained image — not by a
pixel-exact golden, which does not exist for this output.

## Rollback

Revert the merge commit. Evidence sets are regenerable decorations; no
comparison workbook schema, count, or sidecar format changes, so nothing
downstream needs migration. Rolling back restores the pre-RB-4 behavior the
audit recorded (evidence on all ten rows from sometimes-borrowed prints, the
silent disagreement drop, no env lane) — the owner's amendment rulings would
be un-shipped with it, so a rollback is a return to planning, not a safe
steady state.
