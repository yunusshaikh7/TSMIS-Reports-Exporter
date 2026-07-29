# `RB-2` — Implementation Record

Status: **IMPLEMENTING — acceptance run `RB2-A1` in progress**

| Field | Value |
|---|---|
| Bundle / work items | **RB-2 / HF-02 + HF-03** |
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-2-deliverable-presentation` (worktree `C:\Users\Yunus\Projects\TSMIS-rb2-worktree`; the user's `main` checkout is untouched and still clean) |
| Base `main` commit | `896083e014d0451d5b05e5b6b024339aebc84d74` — clean, identical to `origin/main`, fetched without force before branching |
| Implementation commit | `da1d480ede1f79671f4573b311ac2e402cd16eaf` |
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
| Acceptance run `RB2-A1` | *(in progress — see below)* | |

## Acceptance run `RB2-A1`

*(to be completed)*

## Scope and residual risk

- **Out-of-scope files changed: none.** The diff is exactly `compare_core.py`, `summary_layout.py`, `matrix_build.py`, `compare_tsn_common.py`, one new check, four existing checks, and this bundle's records.
- **A source with no producer outcome record gets today's behaviour.** The capture's origin record rides the outcome sidecar, which `captured_tsn_workbook` only writes when the source itself has a trusted producer outcome — true for every canonical library workbook and therefore for all 36 matrix-lane workbooks. An explicitly picked file with no sidecar keeps recording the literal path it was read from, which remains honest.
- **The values twin's headline is now build-time state.** That is the finding's own first acceptance branch and the plan's design sketch. The live certification guard did not weaken: the freshness SELF-CHECK row is still live in both flavors, still keyed on both very-hidden E2 snapshot sheets, and now states `REGENERATE REQUIRED` in words. Three policy checks were re-pointed to that cell rather than deleted.
- **Column widths move in every regenerated workbook.** No count, mask, schema version or sidecar changes, so committed comparison generations stay valid and `read_counts`' header-label lookup is unaffected.
