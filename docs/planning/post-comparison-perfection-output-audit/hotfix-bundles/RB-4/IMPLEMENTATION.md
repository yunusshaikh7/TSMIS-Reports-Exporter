# `RB-4` — Implementation Record

Status: **IN PROGRESS — RB4-A1 executing** (this file is completed before the
status flips to `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`)

| Field | Value |
|---|---|
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-4-evidence` (worktree `C:\Users\Yunus\Projects\wt-rb4`; the user's `main` checkout untouched) |
| Base `main` commit | `72adf447d45a2b74c562ba714008661a180c5d5f` (the RB-4 readiness commit on top of readiness source `ff780af…`; verified clean and identical to `origin/main` at branch creation) |
| Work items | HF-05 (PCOA-FINAL-004 P1, -005 P1, -006 P1) + HF-10 (PCOA-FINAL-007 P2) |
| Generated-output root | `C:\Users\Yunus\Downloads\TSMIS\_scratch\post-comparison-hotfixes\HF-05\rb4-a1\` (lib copy + base/head stores + results + logs); the five env image sets copied to `…\HF-10\rb4-a1\`; committed machine-readable witnesses in `../HF-05/witness/` and `../HF-10/witness/` |

## Changes

| File | Change | Finding IDs |
|---|---|---|
| `scripts/visual_evidence.py` | The exact-source rebuild. `generate()` binds BOTH sides to the comparison's own recorded provenance BEFORE anything renders: `_bound_provenance` requires the `.provenance.json` sidecar, a trusted+current typed outcome whose committed `generation_id` equals the sidecar's, and per-flavor input kinds; the live bytes are digested against each side's recorded sha256 (file inputs) or per-file census (env inputs); a pair that cannot bind RETIRES any prior evidence set and raises `EvidenceSourceBindingError` with NOTHING published — no workbook, no images, no manifest (`refuse_binding`; the early byte check closes the no-examples side door a tampered side could exit through). The vs-TSN and self flavors render BOTH panels from the two compared workbooks (`_workbook_side` — the generalized CMP-AUD-210 panel, resolved through each side's own comparator hook: `excel_column_for` / `pdf_excel_column_for` / `tsn_excel_column_for`, projections `project`/`tsn_project`, data sheet via `workbook_sheet`); `tsmis_source_role` now selects the resolve hook, never a print. The manifest read set is exactly the two compared documents named by their DURABLE selections (`_ReadSet.rename_member` — a private TSN capture path never reaches the manifest, PCOA-FINAL-003 discipline). NEW `FLAVOR_ENV` (HF-10): both run folders come from the provenance selections resolved the env comparison's own way (`compare_env._find_input_dir`), candidates derive from the published universe itself (`_env_candidates` — solo matched `D` rows), both sides locate in their own per-route prints (`_locate_env_sides` → adapter `env_locate`, CMP-AUD-049 identity refusals kept), each example's print values must COMPOSE to the published cell display, and the ENGINE refuses any target rectangle outside the captioned record's own printed lines (`_env_example_sides` — the PCOA-FINAL-005 backstop). Panel truncation fixed (`panel_cell_text`: full value or a visibly `…`-elided prefix, column widths sized to the drawn string — PCOA-FINAL-006). Summary declares the compared selections per side ("Compared <role>: <selection>"), image-sheet legends state only what was read (`_legend_for`), captions/labels carry the published side labels. `availability()`: `ready` = imaging deps alone (prints gate nothing), `env_rows` published; `env_capable`/`env_rows`/`env_adapter_for` new; `_snapshot_read_set` gains labelled side buckets + original-stat capture; the dead print-discovery pair (`_pdf_source_files`/`_ensure_pdf_source_set`) and `_locate_tsmis_sources` removed (the env locate loop carries the identity-refusal contract) | 004, 005, 006, 007, (003 discipline) |
| `scripts/evidence_highway_log.py` | `pdf_excel_column_for`/`tsn_excel_column_for` = the one corrected-header gate (all three compared HL workbooks share it); `tsn_project`; `workbook_sheet`; `locate_tsmis` gains `key_fn` + `src` capture; blank-Description boxes now REFUSE on both prints (the below-the-record guesses that boxed the NEXT record are gone); the TSN blank-window fallback clips to the record's own line; env hooks (`env_fields` = the 30 corrected fields, `env_locate` keyed by the projected Location, `env_value`/`env_box`) | 004, 005, 007 |
| `scripts/evidence_highway_sequence.py` | Panel hooks (`pdf_excel_column_for` alias — the conversion reproduces the export header verbatim; `tsn_excel_column_for` over `['Route'] + SHARED_HEADER`; side-aware `tsn_project`; `workbook_sheet` incl. the normalized sheet); `locate_tsmis` gains `key_fn` + `src`; synthetic equate rows are MARKED and their blank fields REFUSE geometry (the final-'O'-of-'EQUATES TO' class), the no-segs Description fixed-zone guess removed; env hooks (`env_fields` incl. the env comparison's own `(col C)`/`(col E)` names for the unnamed postmile columns, `env_locate` keyed by the plain PM cell, strict `env_project`, `env_box` with prefix/suffix zones) | 004, 005, 007 |
| `scripts/evidence_intersection_detail.py` | Panel hooks (`pdf_excel_column_for` alias — the legacy labels ride the same value positions; `tsn_excel_column_for` under the v3-sidecar gate; `tsn_project`; `workbook_sheet`); `locate_tsmis` gains `key_fn` + `src`; env hooks (`env_fields` = the canonical export header minus Route/Post Mile, `_ENV_TO_SHARED` derived from `idt._TSMIS_POS` × `_TSMIS_HEADER` so the mapping can never drift from the loader, padded-PM env keying, strict `env_project`, Location special-cased to its print cell) | 004, 007 |
| `scripts/evidence_ramp_detail.py` | `excel_column_for` goes DUAL-EDITION (the July-2026 consolidated the loader already accepts resolves through `_TSMIS_POS_2026` — RB-3's deliberately deferred evidence half); `pdf_excel_column_for` over the conversion's own 14-column book (`_PDF_BOOK_POS`); `tsn_excel_column_for` with District resolving to its OWN sidecar column; strict `tsn_project`; `workbook_sheet`; `locate_tsmis` gains `src`; env hooks (`env_fields` from `compare_env._RD_ENV_HEADER` + the print-only pair, `env_locate` = the same normalized-PM keying, strict `env_project`, `env_box` refusing the two structurally-empty conversion columns) | 004, 006-adjacent, 007 |
| `scripts/evidence_highway_detail.py` | The minimal shared-contract hooks only (`pdf_excel_column_for` alias, `tsn_excel_column_for`, `tsn_project`, `workbook_sheet`) so the shared engine stays uniform. NO parser/canary/behavior change; no env hooks (⛔ HD pre-release honored — its lane is not exercised by RB4-A1) | wiring |
| `scripts/evidence_ramp_summary.py` | NEW env-only adapter for the fifth PDF-vs-PDF cell: values from the consolidator's OWN parser (`_rs.parse_pdf` — never a second parser), geometry from a word-box-keeping twin of its two-column walk (`_line_rows_with_boxes` + `_attribute`, cross-checked at lookup so an attribution drift can only REFUSE, never mislabel), footer totals located by their own label lines, absent categories honestly refuse geometry. Exposes no vs-TSN/self hooks on purpose — `capable("ramp_summary")` stays False (its clean vs-TSN evidence absence is the audit-approved state) | 007 |
| `scripts/matrix_build.py` | `build_cell_comparison` gains `evidence=` → `_run_env_evidence` (decoration-after-`require_published_comparison`+COMPLETE, failure only logs — the existing contract); `build_comparison` passes `evidence` through on the env branch; NEW `run_env_evidence_only` (the HF-10 camera: trusted/current/COMPLETE sidecar, cache generation binding, input-fingerprint freshness); `evidence_for_cell` gains `mode_id` ("env" → the env camera) | 007 |
| `scripts/matrix.py` | Facade re-export `run_env_evidence_only` | 007 |
| `scripts/gui_matrix.py` | `matrix_evidence_cell` is mode-aware (the row's SELECTED mode: env → `env_capable` + baseline-cell refusal; job carries the frozen mode per CMP-AUD-110); `_dispatch_evidence_job` routes `mode_id` | 007 |
| `scripts/gui_api.py` | ONE truth line in `_evidence_view`: a row counts as supported when ANY lane can illustrate it (`capable` OR `env_capable`) — without it the UI would keep asserting "no evidence support" for ramp_summary, the same untruthful-prose class criterion 4 retires. **Scope note for the reviewer:** `gui_api.py` is not in the bundle's named file union; the alternative was returning the whole bundle to planning over three tokens of availability plumbing. Flagged here deliberately | 007, criterion-4 spirit |
| `scripts/ui/ui-matrix.js` | The evidence hint states the true sources (workbook panels / both environments' prints); `evidenceActionInfo(rowKey, mode)` is lane-aware with NO print requirement; the row camera badge is always lit for supported rows; the Everything cell actions offer the camera+open on env-mode cells of the five env rows (baseline cell excluded) | 004, 007 |
| `scripts/ui/mock.js` | `env_rows` + the corrected `unsupported` list (mock parity) | wiring |
| `build/app.spec` | `APP_MODULES` += `evidence_ramp_summary` (F6) | wiring |
| `build/_checklib.py` | NEW `publish_bound_comparison` — fixtures publish the production way (`artifact_store.commit_workbook` → typed outcome sidecars + `write_comparison_provenance`), so checks drive the exact-source binding through the real front door | test infra |
| `build/check_visual_evidence.py` | Fixtures rebased on bound comparisons; snapshot bucket/stat/rename coverage; availability `ready`/`env_rows` semantics; NEW blocks: blank-side refusals (HL both prints, HSL equate lines), the engine env row-rectangle backstop, env candidates from the published universe, `env_fields` pinned to `compare_env`'s own constants per family, the RS geometry twin (incl. the mislabel-refusal and absent-category refusal) | 004, 005, 006, 007 |
| `build/check_evidence_source_role.py` | `_workbook_rows_at`/`_workbook_side` contract; `panel_cell_text` fidelity (full 34-char value drawn; pathological values visibly elided; strip sized to the drawn string); the TSN-side panel via its own hook; the three-flavor registry; per-adapter hook presence; env-capability registry (ramp_summary env-only) | 004, 006, 007 |
| `build/check_evidence_manifest.py` | `run_generate` publishes BOUND fixtures; the cancel boundary moved to the addressing step; NEW terminal case: an unbindable pair publishes NOTHING — manifest included — and retires the prior set | 004 |
| `build/check_evidence_excel_columns.py` | Seam test on `_workbook_side` ctx (incl. the no-fallback rule for side-specific hooks); RD July-2026 dual-edition resolution; NEW `test_tsn_and_pdf_hooks` per family | 004 |
| `build/check_evidence_literal_cells.py` | The new Summary layout (source lines on rows 3–4, data from row 7) with source-controlled text in every new slot | 004 |
| `build/check_matrix.py` | `build_cell_comparison(evidence=)` accepted; an XLSX env cell stays SILENT with the toggle on; the env camera refuses non-env rows and missing comparisons | 007 |
| `build/check_pdf_excel_matrix.py` | The by-day PDF-vs-Excel lane writes ZERO evidence artifacts (criterion 5's silent control now has teeth) | 004 |
| `build/check_pdf_route_identity.py` | The engine-half identity pin retargeted to `_locate_env_sides` (the one production print-rendering lane) | wiring |
| `build/check_matrix_ownership.py` | The evidence-dispatch stub accepts `mode_id` | wiring |
| `build/run_rb4_acceptance.py` | NEW — the committed `RB4-A1` driver (provision / generate / cameras / counts / validate / excel / census / checks-at-base phases; worker-parity leases and commit guards; per-phase JSON results + logs) | acceptance |
| `docs/comparison-engine.md` §13, `docs/gui.md` | The documented contract moved to the exact-source rule + the env lane; the Sources/UX paragraphs rewritten | docs |
| `hotfix-bundles/RB-4/BUNDLE.md` | Base `main` SHA filled | — |

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

## Design

1. **The binding IS the eligibility rule.** Under the owner's exact-source
   ruling there is no shape-based prohibition left: a pair is eligible exactly
   when both sides bind to the comparison's recorded read set (sha256 for file
   inputs, per-file census + the comparison's own folder resolution for env
   inputs), and an unbindable pair leaves nothing — not even a manifest —
   with any prior set retired. The check runs BEFORE proposals so no failing
   pair can exit through the no-examples path with a fresh record.
2. **One panel renderer, per-side comparator hooks.** `_workbook_side`
   generalizes the CMP-AUD-210 Excel panel to every workbook side; each
   adapter resolves each EDITION through the loader family that reads it
   (Excel / PDF-conversion / normalized-TSN), so evidence and comparison can
   never resolve a column differently, and a side-specific hook that is
   missing REFUSES rather than falling back to labels.
3. **The env flavor reuses the pipeline, not a parallel renderer.** Candidates
   come from the published universe (solo `D` rows); both sides locate through
   the adapters' LOCKSTEP print parsers re-keyed the env comparison's way;
   the located values must COMPOSE to the published cell display before
   anything renders; the same `_strip`/compose/publish machinery draws it.
   The engine refuses any env target outside the captioned record's printed
   lines regardless of adapter geometry — defense in depth over the
   PCOA-FINAL-005 class.
4. **Blank targets never guess.** A field with no cell rectangle inside the
   record's own printed lines refuses with a recorded reason (HL blank
   Descriptions, HSL equate-line fields, RS absent categories); a fixed-window
   column's blank cell still boxes its own window clipped to the record's
   line. Honest misses over plausible-but-wrong boxes.
5. **Drawn strings are the compared values.** `panel_cell_text` is the pure
   decision the renderer draws with — full value up to `PANEL_TEXT_MAX`, else
   a visibly `…`-elided prefix — so fidelity is assertable programmatically
   over 100 % of examples without OCR, and columns are sized to what is drawn.
6. **Decoration stays decoration.** The env evidence rides AFTER
   `require_published_comparison` + COMPLETE, failures only log, and the env
   camera carries the same freshness discipline as the vs-TSN one (trusted /
   current / generation-bound / input-fingerprint-unchanged).

## Focused checks — red at base, green at head

Method: the seven extended check files were overlaid onto a staged copy of the
exact base tree (`git archive 72adf44…`) and run there
(`run_rb4_acceptance.py --phase checks-at-base`; recorded in
`results/base-red-checks.json`), then at head.

| Check file | At base `72adf44` | At head |
|---|---|---|
| `check_visual_evidence.py` | red — `_snapshot_read_set() got an unexpected keyword argument 'buckets'` (the env read-set contract absent) | ALL PASS |
| `check_evidence_source_role.py` | red — `module 'visual_evidence' has no attribute '_workbook_rows_at'` (no workbook-panel addressing) | ALL PASS |
| `check_evidence_manifest.py` | red — same missing contract surface | ALL PASS |
| `check_evidence_excel_columns.py` | red — `_workbook_side` absent + **2 semantic FAILs**: the July-2026 RD edition assertions fail (RB-3's deliberately deferred evidence half) | ALL PASS |
| `check_evidence_literal_cells.py` | red — `KeyError: 'tsmis_dir'` (the base writer requires the untruthful `TSMIS PDFs:` summary contract) | ALL PASS |
| `check_matrix.py` | red — `build_cell_comparison() got an unexpected keyword argument 'evidence'` (PCOA-FINAL-007's root cause verbatim) | ALL PASS |
| `check_pdf_excel_matrix.py` | **green at base and head** — the silent control was already silent; the new zero-artifact assertion is a must-not-regress lock, not a red→green | ALL PASS |

The DATA-level pre-fix signatures bind to the base runtime through the
base-side generation itself (borrowed prints in the read sets — 12 TSN
district prints on the HL cell, 112 PDFs on the HL-PDF cell; the `TSMIS
PDFs:` declarations; the `text[:26]` drawing rule) — see the RB4-A1 section.

## RB4-A1 — the one executable acceptance run

TBD — completed after the head generation, validation, installed-Excel,
census, image inspection, and manifest/verifier land.

## Scope and residual risk

TBD.

## Rollback

Revert the merge commit. Evidence sets are regenerable decorations; no
comparison workbook schema, count, or sidecar format changes, so nothing
downstream needs migration. The five env cells return to
absent-and-required; the vs-TSN/self lanes return to the borrowed-print
behavior the audit recorded.
