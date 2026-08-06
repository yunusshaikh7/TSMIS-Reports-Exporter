# `RB-4` — Implementation Record

Status: **IN PROGRESS — SCOPE AMENDED BY OWNER 2026-08-05** (the first RB4-A1
run completed at `a21e0ba` and its COMPARISON-layer results stand — counts,
masks, formulas twins, silent classic controls, full gate — but the owner
rejected the workbook-panel evidence rendering on sight of the images and
re-ruled the bundle: evidence is PRINT CROPS on the 12 `_pdf`-family
PDF-vs-PDF cells only, refused at the engine boundary everywhere else; see the
BUNDLE.md amendment section. The evidence layer is being reimplemented and
RB4-A1 re-runs at the new head; this file is completed before the status flips
to `IMPLEMENTED — AWAITING ADVERSARIAL REVIEW`. The narrative below this line
still describes the FIRST run and is rewritten as part of that re-run.)

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
| `scripts/evidence_intersection_detail.py` | Panel hooks (`pdf_excel_column_for` alias — the legacy labels ride the same value positions; `tsn_excel_column_for` under the v3-sidecar gate; `tsn_project`; `workbook_sheet`); `locate_tsmis` gains `key_fn` + `src`; env hooks (`env_fields` = the canonical export header minus Route/Post Mile, `_ENV_TO_SHARED` derived from `idt._TSMIS_POS` × `_TSMIS_HEADER` so the mapping can never drift from the loader, padded-PM env keying, strict `env_project`, Location special-cased to its print cell). Probe-driven fix on the real corpus: the two env display columns OUTSIDE the vs-TSN map that the print nevertheless carries as grid cells (`PS` = rowA window 2, `Intrte S` = rowB window 13) get `_ENV_CELL_EXTRA` geometry + positional value reads (`tsmis_box` refactored over `_box_at`); without them every published `PS` diff refused (`box None` on all 12 sampled) | 004, 007 |
| `scripts/evidence_ramp_detail.py` | `excel_column_for` goes DUAL-EDITION (the July-2026 consolidated the loader already accepts resolves through `_TSMIS_POS_2026` — RB-3's deliberately deferred evidence half); `pdf_excel_column_for` over the conversion's own 14-column book (`_PDF_BOOK_POS`); `tsn_excel_column_for` with District resolving to its OWN sidecar column; strict `tsn_project`; `workbook_sheet`; `locate_tsmis` gains `src`; env hooks (`env_fields` from `compare_env._RD_ENV_HEADER` + the print-only pair, strict `env_project`, `env_box` refusing the two structurally-empty conversion columns). Probe-driven fix on the real corpus: the env comparison publishes the export's RAW padded PM text (`043.274`) while the LOCKSTEP walk keys on the normalized PM (`43.274`) — `env_locate` now normalizes the published keys for the walk and re-keys the result by the published text, excluding (never guessing) two published texts that collapse onto one normalized PM; without it every env lookup returned zero records | 004, 006-adjacent, 007 |
| `scripts/evidence_highway_detail.py` | The minimal shared-contract hooks only (`pdf_excel_column_for` alias, `tsn_excel_column_for`, `tsn_project`, `workbook_sheet`) so the shared engine stays uniform. NO parser/canary/behavior change; no env hooks (⛔ HD pre-release honored — its lane is not exercised by RB4-A1) | wiring |
| `scripts/evidence_ramp_summary.py` | NEW env-only adapter for the fifth PDF-vs-PDF cell: values from the consolidator's OWN parser (`_rs.parse_pdf` — never a second parser), geometry from a word-box-keeping twin of its two-column walk (`_line_rows_with_boxes` + `_attribute`, cross-checked at lookup so an attribution drift can only REFUSE, never mislabel), footer totals located by their own label lines, absent categories honestly refuse geometry. Exposes no vs-TSN/self hooks on purpose — `capable("ramp_summary")` stays False (its clean vs-TSN evidence absence is the audit-approved state) | 007 |
| `scripts/visual_evidence.py` (env candidates) | Probe-driven fix on the real corpus: a route-keyed comparison (Ramp Summary) publishes no separate route column — `_env_candidates` now carries `route = row.route or row.key` so the padded key serves as the print-file route token; without it the engine resolved `tsar_ramp_summary_route_.pdf` (empty token) and every RS example missed | 007 |
| `scripts/matrix_build.py` | `build_cell_comparison` gains `evidence=` → `_run_env_evidence` (decoration-after-`require_published_comparison`+COMPLETE, failure only logs — the existing contract); `build_comparison` passes `evidence` through on the env branch; NEW `run_env_evidence_only` (the HF-10 camera: trusted/current/COMPLETE sidecar, cache generation binding, input-fingerprint freshness); `evidence_for_cell` gains `mode_id` ("env" → the env camera) | 007 |
| `scripts/matrix.py` | Facade re-export `run_env_evidence_only` | 007 |
| `scripts/gui_matrix.py` | `matrix_evidence_cell` is mode-aware (the row's SELECTED mode: env → `env_capable` + baseline-cell refusal; job carries the frozen mode per CMP-AUD-110); `_dispatch_evidence_job` routes `mode_id` | 007 |
| `scripts/gui_api.py` | ONE truth line in `_evidence_view`: a row counts as supported when ANY lane can illustrate it (`capable` OR `env_capable`) — without it the UI would keep asserting "no evidence support" for ramp_summary, the same untruthful-prose class criterion 4 retires | 007, criterion-4 spirit |
| `scripts/self_test.py` | `evidence_ramp_summary` joins `_DYNAMIC_REPORT_MODULES` — the HF-10 camera resolves the new adapter lazily, so the frozen build must carry it or the env lane fails only on the packaged app | wiring |
| `scripts/ui/ui-matrix.js` | The evidence hint states the true sources (workbook panels / both environments' prints); `evidenceActionInfo(rowKey, mode)` is lane-aware with NO print requirement; the row camera badge is always lit for supported rows; the Everything cell actions offer the camera+open on env-mode cells of the five env rows (baseline cell excluded) | 004, 007 |
| `scripts/ui/mock.js` | `env_rows` + the corrected `unsupported` list (mock parity) | wiring |
| `build/app.spec` | `APP_MODULES` += `evidence_ramp_summary` (F6) | wiring |
| `build/_checklib.py` | NEW `publish_bound_comparison` — fixtures publish the production way (`artifact_store.commit_workbook` → typed outcome sidecars + `write_comparison_provenance`), so checks drive the exact-source binding through the real front door | test infra |
| `build/check_visual_evidence.py` | Fixtures rebased on bound comparisons; snapshot bucket/stat/rename coverage; availability `ready`/`env_rows` semantics; NEW blocks: blank-side refusals (HL both prints, HSL equate lines), the engine env row-rectangle backstop, env candidates from the published universe, `env_fields` pinned to `compare_env`'s own constants per family, the RS geometry twin (incl. the mislabel-refusal and absent-category refusal) | 004, 005, 006, 007 |
| `build/check_evidence_source_role.py` | `_workbook_rows_at`/`_workbook_side` contract; `panel_cell_text` fidelity (full 34-char value drawn; pathological values visibly elided; strip sized to the drawn string); the TSN-side panel via its own hook; the three-flavor registry; env-capability registry (ramp_summary env-only). The composed image is measured from its OWN INK — the title block must end inside the canvas without being padded far past it, and a long left caption and the right caption must resolve to two separate ink runs; sizing the expectation with the composer's own width helper was circular and a halving regression satisfied both sides of it. The adapter hooks are PROBED, not counted: each column hook must refuse a header it does not recognise (an existence assertion passes against a stub resolving every field to column 0), `tsn_project` must be idempotent and read a blank cell as `""`, `workbook_sheet` must name a sheet per edition with the two TSMIS-side editions sharing one, and `tsmis_pdf_path` must resolve inside the run folder under the end-anchored per-route name. And the two engine helpers with a single call site each — `_display_header`, `_normalization_note` — are locked by one example driven end to end through `_try_example`; without it, deleting either line passed the entire gate | 004, 006, 007 |
| `build/check_evidence_manifest.py` | `run_generate` publishes BOUND fixtures; the cancel boundary moved to the addressing step; NEW terminal case: an unbindable pair publishes NOTHING — manifest included — and retires the prior set | 004 |
| `build/check_evidence_excel_columns.py` | Seam test on `_workbook_side` ctx (incl. the no-fallback rule for side-specific hooks); RD July-2026 dual-edition resolution; NEW `test_tsn_and_pdf_hooks` per family | 004 |
| `build/check_evidence_literal_cells.py` | The new Summary layout (source lines on rows 3–4, data from row 7) with source-controlled text in every new slot | 004 |
| `build/check_matrix.py` | `build_cell_comparison(evidence=)` accepted; an XLSX env cell stays SILENT with the toggle on; the env camera refuses non-env rows and missing comparisons | 007 |
| `build/check_pdf_excel_matrix.py` | The by-day PDF-vs-Excel lane writes ZERO evidence artifacts (criterion 5's silent control). A bare "the glob found nothing" reads the same whether the lane is silent, the tree is the wrong one, or the pattern is broken — so the probe is CONTROLLED first: an evidence-named artifact is planted where one would land, the probe must see it, and only then is the lane's own silence read | 004 |
| `build/check_pdf_route_identity.py` | The engine-half identity pin retargeted to `_locate_env_sides` (the one production print-rendering lane) | wiring |
| `build/check_matrix_ownership.py` | The evidence-dispatch stub accepts `mode_id` | wiring |
| `build/run_rb4_acceptance.py` | NEW — the committed `RB4-A1` driver (provision / generate / cameras / counts / validate / excel / census / checks-at-base phases; worker-parity leases and commit guards; per-phase JSON results + logs). Hardened during the run, before the head side started: the PvE silent-control cells take the PDF-edition row keys the matrix actually registers; `phase_validate`'s env re-derivation runs the engine's own lookup end-to-end and treats legal `…`-elision as a LISTED census for the image inspection (never a failure); every phase result SELF-STAMPS the tree's exact git head + a runtime-scoped dirty flag (`tree_stamp`) so exact-head identity lives in the record itself — the RB-2 lesson | acceptance |
| `docs/…/rb4-verify-manifest.py` | NEW — the committed fail-closed verifier (RUNTIME / LINEAGE / EXACT HEAD with self-stamps / BASE TREE / WITNESSES / `--corpus` with the sha-bound detached inventory / `--zips` archive re-match / `--self-test` negatives) | acceptance |
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

| Check file | At base `72adf44` | Signature bound (its own stdout) |
|---|---|---|
| `check_visual_evidence.py` | red | `the read set is captured in labelled per-side buckets, so a manifest names the document each side was compared from` |
| `check_evidence_source_role.py` | red¹ | `the engine addresses the compared workbook's rows and renders each side's panel from it (_workbook_rows_at + _workbook_side)` |
| `check_evidence_manifest.py` | red¹ | `the engine renders a side from the compared WORKBOOK (_workbook_rows_at + _workbook_side), not from a borrowed print` |
| `check_evidence_excel_columns.py` | red¹ | `FAIL: July District also resolves to its Location cell` (RB-3's deliberately deferred evidence half) |
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
  gate. One example is now driven end to end through `_try_example`.
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

**Inputs (frozen, hash-bound).** The 2026-07-23 raw extract the output audit
itself measured; the ground-truth 7.9 ssor and ars pulls (each member re-matched
against `All Reports 7.9.zip` / `ramp_summary_excel.zip`); the Downloads TSN
master library's raw/pdf sources. Provisioned into per-side replica stores
created the way the app creates one (`owned_dir.ensure_owned_dir`), and
re-hashed AFTER the run: every replica still equals its provision-time hash AND
its frozen source, so the run never mutated an input. Highway Detail is
excluded everywhere (⛔ pre-release).

**One frozen head, and a harness that fails closed.** An earlier attempt was
abandoned deliberately: an adversarial audit of the run itself found the harness
verified *what it found*, so a silently missing evidence set, a camera that
threw, and a base check that failed for the wrong reason all passed. Those holes
were closed before this run started (see the driver's entry in the Changes
table), the prior head-side comparisons were RETIRED, and the complete sequence
was produced against ONE frozen runtime head — runtime-digest equality is not
head identity (the RB-2 Review-2 lesson).

The chain script is itself a gate now: it aborts on the first failing phase
rather than echoing an exit code and continuing, and after every phase it
re-asserts both that the runtime files are clean AND that `HEAD` has not moved.
Every retained result SELF-STAMPS that head plus a runtime-scoped clean/dirty
flag; the base side stamps the base commit, read from a content binding that
compares each base-tree runtime file against the base commit's own git blob.

Order: full gate at head → base-tree binding → the same check files at base →
generation → cameras → validate → excel → counts → census.

| Phase | Result |
|---|---|
| checks at head | 158 / 158 (`results/checks-at-head.json`) |
| base-tree binding | 151 / 151 runtime files identical in content to `72adf44` |
| checks at base | 8 red · 2 green controls · 0 inconclusive |
| generate | 35 cells (8 Everything vs-TSN · 5 SELF · 5 ENV + 5 ENV evidence-OFF controls · 8 By Day · 4 PvE silent controls) — **0 non-ok** |
| cameras | 21 on-demand cells (8 vs-TSN · 8 By Day · the 5 HF-10 env cameras) — **21/21 ok, 0 problems** |
| validate | 26 evidence sets (16 vs-TSN · 5 SELF · 5 ENV; 24 rendered, 2 no-differences) — **0 problems** |
| excel | 24 evidence workbooks opened in INSTALLED Excel — 24/24 without an open failure, Ledger sheet present in all 24, **838 embedded pictures** (exactly the 838 images on disk); **26/26 formulas twins settle to their values workbook's totals**, 0 disagreements |
| counts | 26 typed sidecars re-read — **26/26 identical** to the base runtime |
| census | ok |

The whole chain ran 02:25 → 17:09 (14 h 44 m), generation alone 10 h 02 m and the
Excel leg 2 h 50 m — the twin recalculations are a full rebuild of workbooks up
to 250 MB.

**The repository gate, all four legs, at that same frozen head:**
`run_checks.py -j 4 -k` **158/158** · `compileall` clean · `ruff check scripts`
clean · `build.ps1 -SelfTest` **PASSED** — the exact shipped exe runs every code
path, including the evidence render stack and the lazily-imported
`evidence_ramp_summary` adapter this bundle adds, which is the one packaging
risk it introduces.

**The population is DECLARED, not discovered.** The driver previously globbed
whatever evidence sets it found, so a silently missing set was invisible. It now
declares the expected population and fails naming any shortfall. This run:
`required 26 · discovered 26 · missing 0 · extra 0 · duplicate 0 · forbidden
present 0`. The 5 ENV sets are *required* at head and *forbidden* at base — the
base side's job is to prove they do not exist there.

**The recounts the bundle asked for, rather than a sample.** Across 724 examples
in 24 rendered sets:

| Population | Count |
|---|---|
| Blank-side targets (the PCOA-FINAL-005 population) | **238** |
| Values longer than the old 26-character cut (what PCOA-FINAL-006 silently truncated) | **19** |
| Examples needing visible elision at the 120-character panel limit | **0** |

So every one of the 19 values the pre-fix rule would have cut mid-string is now
drawn in full, and no value in this corpus is long enough to require the elision
path — which is why the elision behaviour is proved by check rather than by this
run's data.

The bundle also asked for these populations to be **recounted rather than
sampled** on the audit's own sets, which `phase_census` now does exhaustively
(`results/prefix-defect-census.json`):

| Set | Examples examined | Over the 26-char prefix limit | Legally elided | Blank-side targets |
|---|---|---|---|---|
| Audit — Everything (11 sets) | 529 | 10 | 0 | 208 |
| Audit — By Day (7 sets) | 359 | 7 | 0 | 132 |
| Base — Everything (13 sets) | 357 | 4 | 0 | 141 |
| Base — By Day (8 sets) | 241 | 5 | 0 | 84 |

The prior figure was a sample; these are complete counts with their denominators,
and legal `…`-elision is counted separately from the defect rather than folded
into it. One caveat, disclosed rather than papered over: the audit By Day root
has no frozen copy, so it is declared UNBOUND in the manifest and its identity
rests on the Stage 1B witness hashes, all of which still match.

**Cross-environment re-derivation.** All 108 env examples (HL-PDF 57 · RS 25 ·
RD-PDF 10 · HSL-PDF 8 · ID-PDF 8) were independently reproduced end to end from
the two environments' own prints — re-located, re-boxed inside the captioned
record, re-read — with **0 failing checks**. Every read-set member was confirmed
both to lie under a compared side's resolved directory and to match that side's
recorded census entry.

**What validate proves, per set** (100 % programmatic, no sampling): the
manifest describes CURRENT with every member verified; the provenance sidecar
is present; the read set is EXACTLY the comparison's own two recorded documents
for a rendered generation (and empty for a non-rendered one, which opened no
source); for env sets every read-set member lies under a compared side's
resolved directory AND matches that side's recorded census entry
(name+size+mtime_ns); the Summary's source lines are the provenance selections
verbatim; every image-sheet legend is the flavor's true-source legend; and for
env sets **every example is re-derived end to end** — both prints re-located,
both boxes re-computed inside the captioned record, both values re-read.

> ENV re-derivation: 59/59 · 23/23 · 10/10 · 8/8 · 8/8 — every published env
> example independently reproduced from the two environments' own prints.

**Silent controls — both driven, neither proxied.** The by-day PDF-vs-Excel lane
ran with the evidence toggle ON and produced ZERO evidence artifacts, proved by
enumeration over its tree; each of the 5 ENV cells was additionally built with
evidence OFF and produced none.

The **classic Compare tab** control was previously a code-comment proxy — the
by-day lane was said to exercise "the same self comparator", and the record did
not disclose the substitution. The tab's endpoint blocks on a native save
dialog and cannot be driven headlessly, but the comparator the endpoint calls
can be, and the comparator is what the silence claim is about. Both lanes now
run for real, resolved through the same registry the endpoint uses and fed the
same two inputs from the source placement's own provenance sidecar: the FILE
lane (`compare(...)`, Highway Sequence vs-TSN, 398.5 s) and the FOLDER lane
(`compare_folders(...)`, Highway Sequence PDF between environments, 1144.4 s).
Both returned `ok` and wrote zero evidence artifacts.

Each silence reading is preceded by a **planted positive control**: an
evidence-named artifact is placed where one would land and the probe must SEE it
before the tree is read for real. A bare "the glob found nothing" reads the same
whether the lane is silent, the tree is the wrong one, or the pattern is broken.
Both lanes' probes saw their planted control.

**Count/mask invariance.** All **26/26** cells compare equal between the base
runtime and the head across every substantive field: verdict, completion,
`trusted`/`current`/`known`/`present`, paired rows, both one-sided counts,
differing rows, differing cells, asserted/context cells, pairing quality, and
the full per-field table. The only difference anywhere is the `generation_id`,
which necessarily changes on a rebuild. HF-05 and HF-10 change evidence
rendering only — never comparison content.

The two sides are bound to different runtimes, which is what makes that
comparison mean anything: `counts-head.json` self-stamps `a21e0ba`,
`counts-base.json` self-stamps `72adf44`, and the base tree is proven by content
to BE `72adf44`. Before this run the base side carried no runtime identity at
all and the verifier's tree argument defaulted to the head worktree — a
forgotten flag would have made base and head the same runtime and every count
would have matched trivially.

**Formulas-twin settlement.** Each comparison publishes a values workbook and a
live-formulas twin, and nothing previously proved the twin agrees. Every twin
was opened in installed Excel, fully recalculated, and its Status/Diffs totals
read back by header label: **26/26 agree, 0 disagree, 0 excused.** Twin
expectancy is taken from the producer's own probe rather than re-derived — a
scanned row count would have wrongly excused the largest comparisons, since the
Highway Log sheet scans past the twin limit yet its twin exists because the
producer's probe returns no stored dimension. The five ENV cells additionally reproduce the output audit's own
measured numbers EXACTLY (Ramp Summary 67; Intersection Detail PDF 17,562;
Ramp Detail PDF 376 + 5/8 one-sided; Highway Log PDF 88,238 + 2,095/1,174;
Highway Sequence PDF 1,904 + 7/246 — PCOA-FINAL-007's own figures).

**Individual native-scale image inspection.** The bundle requires EVERY
retained image inspected, not sampled. The population is proved complete by
construction: `acc_rb4_inspect_manifest.py` reconciles every PNG on disk against
the Summary rows that claim it — an unclaimed image or a claimed-but-missing one
is a recorded problem (0 of each). The set was then partitioned into 11 slices
and inspected image-by-image at native scale.

An inspection of the **pre-fix** set (825 images, retained as
`results/inspection-round1.json`) returned **39 failures in five classes — every
one a real defect that all 158 programmatic checks had passed.** That result is
the reason this bundle carries an image inspection at all: the classes below are
what a programmatic gate could not see, and they became the explicit failure
criteria every later inspection hunts for. The per-class counts below are the
shape of the finding; the retained record carries the totals (39 of 825), not a
per-class breakdown, so the counts are stated as the classes were characterised
at the time rather than as a re-derivable measurement.

| # | Defect | Images | Fix |
|---|---|---|---|
| 1 | Strip header labels shifted against their own values — the ID PDF workbook labels value position 9 (a date) `INT Type`, so a boxed date sat under a neighbour's name | 2 | `_display_header`: every position a compared field resolves to is labelled with THAT field's name; unclaimed positions keep the workbook's label |
| 2 | Source form differs from the compared value with nothing saying so (`64-01-01`→`1964-01-01`, `01/01/2014`, `1,768`, a blank side whose cell holds `-`) — and the legend actively claimed "Values shown are the compared (normalized) forms" | 30 | Panels keep the source's own text (the exact-source rule); `_normalization_note` names both forms on the image; both legends rewritten to state what is actually drawn |
| 3 | Title/subline hard-clipped mid-glyph at the canvas edge (the canvas was sized from the panel images alone) | 3 | `_header_w`: both composers size the canvas to their own text — it grows rather than cutting |
| 4 | A long left caption overran and overprinted the right caption into an unreadable mash | 2 | Each caption gets its own column, widened to hold it |
| 5 | Ramp Detail's District boxes the composite `Location` cell (`12-SD-005`) because District is derived from it | 2 | Disclosed by the same note line |

A sixth class was also caught by that inspection: a red box swallowing a leading
route label (`15/NB OFF TO LIMONITE AVE`) that is not part of the compared value.

**Every one of those six classes is now locked by a check**, so a regression
fails the gate rather than waiting for a human to look at an image again. That
was not true when they were first fixed: a mutation run — reverting each fixed
behaviour and requiring some check to go red — showed the composition classes
were guarded only by assertions that were circular with the composer's own
measurements, and that the two helpers doing the relabelling and the disclosure
could be deleted outright without failing anything. See the focused-checks
section.

*The inspection of the accepted set* re-rendered every image at the frozen head
and re-inspected all of them with the six classes as explicit failure criteria.

> **(pending — the acceptance run's inspection is in progress; its result and
> the retained record replace this line)**

An earlier inspection of an earlier head returned 827/827 pass, but it describes
images that the current run's retire-and-re-render step deleted. It is history,
not a claim about the accepted set, and is not cited as evidence here.

## Scope and residual risk

**Files outside the bundle's named union.** The bundle expected
`scripts/visual_evidence.py`, the `scripts/evidence_*.py` adapters,
`scripts/matrix_build.py`, the `scripts/day_matrix.py` / `scripts/gui_matrix.py`
guards, and checks. Six changed files sit outside that union, each named in the
Changes table and each a consequence of the env lane existing at all rather than
a widening of the fix:

| File | Why it had to change |
|---|---|
| `scripts/matrix.py` | facade re-export of `run_env_evidence_only`; the facade is the patch surface every caller uses |
| `scripts/gui_api.py` | one truth line, without which the UI keeps asserting "no evidence support" for a row that now has it — the untruthful-prose class criterion 4 retires |
| `scripts/self_test.py` | the new adapter is resolved lazily, so the frozen build must declare it or the env lane fails ONLY on the packaged app |
| `scripts/ui/ui-matrix.js`, `scripts/ui/mock.js` | the hint text asserted print sources that no longer exist, and the mock must stay at parity |
| `build/app.spec` | same lazy-import reason as `self_test.py` |

`scripts/day_matrix.py` is in the union and was NOT changed: the by-day lane is
one of the two silent paths, and it stays silent by not gaining a call site.

**⛔ Highway Detail: code changed, never exercised.** `evidence_highway_detail.py`
gained the four shared-contract hooks so the engine stays uniform across
adapters. HD is PRE-RELEASE, so **no HD cell is exercised anywhere in RB4-A1** —
not in generation, not by a camera, not in the inspection. Its hooks are covered
only by the check-level probes. Nothing here re-blesses an HD canary, changes an
HD parser or normalizer, or infers an HD fact; when the vendor delivers official
HD exports, the HD evidence lane needs its own first exercise before it is
trusted.

**The env lane's coverage is five cells on one day.** HF-10 is proved on the five
Everything ENV cells of the acceptance corpus. The geometry adapters were fixed
against that corpus's prints, and three of the five needed a probe-driven fix to
work at all — which is evidence that env geometry is corpus-sensitive. A print
whose layout differs from these will REFUSE (that is the designed failure), but
"refuses correctly" is asserted only for the shapes this corpus contains.

**One inconsistency, disclosed rather than fixed.** `_snapshot_read_set`'s
same-basename guard raises `EvidenceSourceBindingError` from a call site that is
NOT inside the `refuse_binding` wrapper, so unlike every other binding refusal in
the module it would not retire a stale prior evidence set. It was traced as
unreachable under the current naming conventions — two routes cannot collide on
one basename inside a directory given the end-anchored `…_route_<token>` contract,
and the two compared-workbook basenames are distinct constants per report edition
— so it is a defensive backstop rather than a live bug. It is recorded here
instead of being changed, because changing runtime after the acceptance head was
frozen would invalidate the run that proves the rest.

**What the acceptance run does not prove.** Excel opens every retained workbook
without an open failure; because the driver runs with `DisplayAlerts=False`, a
SILENT repair is not detected, so this is not a zero-repair claim. Image
correctness is established by exhaustive native-scale human-equivalent
inspection plus programmatic validation of every retained image — not by a
pixel-exact golden, which does not exist for this output.

## Rollback

Revert the merge commit. Evidence sets are regenerable decorations; no
comparison workbook schema, count, or sidecar format changes, so nothing
downstream needs migration. The five env cells return to
absent-and-required; the vs-TSN/self lanes return to the borrowed-print
behavior the audit recorded.
