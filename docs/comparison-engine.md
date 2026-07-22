# Comparison Engine

What this doc covers: `compare_core.py` — the one schema-parameterized engine behind every
comparison type — its internals, the regression lock that guards it, the two output flavors,
the verdict / incompleteness contract, the key-field / roadbed / duplicate-pairing logic, the
write-path safety guards, and the three comparison families that delegate to it.

This doc OWNS `compare_core` internals and the regression-lock harness. For the
**code-level walkthrough** (the alignment/pairing algorithms, the exact formula
construction, and the two-flavor mirror), see
[internals/compare-core.md](internals/compare-core.md). Sibling docs:
[reports.md](reports.md) (the `COMPARE_REPORTS` registry, sub-tab wiring),
[verification-and-testing.md](verification-and-testing.md) (the golden checks + verification
loops referenced here), [highway_log/columns.md](highway_log/columns.md) (the corrected
Highway Log column labels), [highway_log/comparison-study.md](highway_log/comparison-study.md)
(the `+`/`++` ditto DOMAIN convention + evidence), and
[highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) (how the inputs are
parsed).

---

## 1. One engine, many comparisons

All comparisons are built by ONE engine: `scripts/compare_core.py`. It was extracted (v0.10.0)
verbatim-then-parameterized from the approved TSMIS-vs-TSN Highway Log workbook
(`compare_highway_log.py`) so the SAME proven engine builds the cross-environment comparisons
too. A report-specific `CompareSchema` carries everything that varies (side names, header,
normalizer/date fields, label nouns, widths, note fragments); the engine's formula and label
text are fixed.

The CALLER (each comparison module) owns file loading and shape validation. Phase 2
represents each loaded input as a typed `LoadedSide` carrying rows plus exact completion,
skipped/failed counts, diagnostics, and identity slots. Compatibility adapters still pass
the following two row shapes into `run_compare`, together with the reduced input coverage:

- **per-route**: `[key, f1..fn]`, `has_route=False`.
- **consolidated**: `[route, key, f1..fn]`, `has_route=True`.

Entry point: `run_compare(sc, rows_t, rows_n, has_route, out_path, *, events, confirm_overwrite,
mode, name_a, name_b, warnings, commit_guard, input_completion, skipped_inputs,
failed_inputs, failures, coverage_diagnostics)` → an additively extended
`ConsolidateResult`. Its
`comparison_outcome`, `artifact_generation`, and `attempt_state` fields are the machine
contract; legacy `verdict`, completion fields, and `summary_lines` remain display/
compatibility data. GUI/console can still drive comparisons and consolidators through the
same outer result type.

The two public adapter boundaries—`compare_tsn_common.run_files_compare` for file recipes and
`compare_env.EnvCompare.compare_folders` for folder recipes—apply
`comparison_contract.comparison_result_boundary` to every returned path. Dependency or missing-
input failures, source/alias preflight rejection, malformed input shape, overwrite cancellation,
`no_data`, and artifact-commit failure therefore return a fail-closed typed
`ComparisonOutcome` plus terminal `AttemptState`; they are never inferred from `summary_lines`.
When such a path committed no workbook, `artifact_generation` remains `None` and the attempt's
`generation_id` remains empty. Only a transaction that actually commits comparison bytes may
invent an `ArtifactGeneration`.

The three comparison families (see [§9](#9-the-three-comparison-families)) are all `run_compare`
callers with different schemas.

---

## 2. The correctness lock

`compare_core` is **correctness-locked, not history-locked**. Formula/label/equality/
identity/pairing changes require independent semantic evidence, both workbook flavors,
installed Excel, and an exact explanation of every deliberate delta. Historical bytes remain a
valuable regression input only when they are correct; they do not veto a confirmed shared defect.

> **Historical context.** v0.18.0's structural overhaul left `compare_core.py`
> **byte-for-byte unmodified** (`git diff origin/main…HEAD -- scripts/compare_core.py` is
> empty); the dormant `context_fill` opt-in that the `main` branch added in v0.17.8 was
> **deliberately NOT forward-ported** (it had no live user — CR-002-RM3), so `git grep
> context_fill` is **0**. All new comparison behavior in v0.18.0 (the Intersection Detail
> "Report View", its control-type crosswalk) rides the existing opt-in `CompareSchema`
> fields (notably `extra_sheet_writer`) that default to the no-op original.

**Why:** the per-route comparison format is approved from the user's Route-1 sample. The v0.10.0
extraction was only accepted because **756,892 cell positions** (values, formulas, fonts, fills,
number formats, widths, conditional-formatting rules, calc mode) matched exactly across 4
workbooks (the real Route-1 + consolidated pairs, both flavors).

**Historical Route-1 sample counts** were **299 both / 18 (TSMIS-only) / 69 (TSN-only) /
221 diff rows / 969 diff cells**.
The 969 was **971** before the v0.11.0 TSN totals-block fix dropped Route-1's 2 leak-caused
Description false positives. (CLAUDE.md / older notes that still say 971 are stale — 969 is
current.)

**The harness** lives OUTSIDE the repo at `%TEMP%\tsmis_regress\` (regenerate `before/` from a
pre-change checkout if the folder is gone):

| Script | Role |
|---|---|
| `make_minis.py` | a 3-route consolidated pair from the Downloads consolidated files |
| `gen_outputs.py before\|after` | runs `compare()` on the real `tsmis/tsn_highway_log_route 1.xlsx` pair + the minis, `mode="both"` |
| `diff_outputs.py` | exhaustive cell diff (values, formulas, styles, CF, calc mode) |
| `test_env_compare.py` | planted-difference fixtures for `compare_env` (missing route / removed rows / edited cells must be reported exactly) |
| `com_verify.ps1` | real Excel COM: F9 the formulas flavor, every SELF-CHECK row must read OK |

**The opt-in rule for genuinely report-specific behavior:** every Highway-Log-only
behavior is a `CompareSchema` field that defaults to the no-op original. When the flag is OFF
(every non-HL comparison), the equality formula, Spot Check verdict, Python mirrors, helper keys
and MATCH lookups should remain semantically invariant. This is how the engine gained
ditto/roadbed/legend behaviors without re-running approval on the other comparisons. The
in-repo golden checks (`build/check_compare_*.py`) lock the engine on synthetic fixtures; see
[verification-and-testing.md](verification-and-testing.md). Shared defects are fixed globally,
even when doing so changes the default workbook.

**Verification flow** (the only "test suite" this no-tests repo has for the comparison): real
input pairs live at `C:\Users\Yunus\Downloads\TSMIS\ground-truth\inputs` (per-route `tsmis_highway_log_route
1.xlsx` + `tsn_…`, and consolidated `…consolidated 1.xlsx`, 50k/60k rows — both-flavors
generate+verify ≈ 12 min, run in background). A throwaway `%TEMP%` verifier regenerates the
workbook and checks every cell against expectations rebuilt from the module's own helpers plus a
semantic key→row mirror; deliver samples to Downloads as
`TSMIS_vs_TSN_<scope>_Comparison_vN_SAMPLE.xlsx` for the user to approve (bump N per iteration,
delete superseded). Excel is installed — COM automation works for empirical behavior tests (e.g.
proving whole-row `57:57` link targets don't scroll right while bounded ranges do).

---

## 3. CompareSchema (the parameterization)

`@dataclass CompareSchema` — defaults reproduce the approved TSMIS-vs-TSN wording; new comparison
types override the data-shape fields and side names.

| Field | Default | Purpose |
|---|---|---|
| `report_name` | (required) | titles/messages, e.g. "Highway Log" |
| `header` | (required) | per-route columns `[key, f1..fn]` |
| `side_a` / `side_b` | `"TSMIS"` / `"TSN"` | side sheet/tab names, also emitted into formulas |
| `id_noun` / `id_noun_plural` | `"location"` / `"locations"` | row-identity noun in labels ("row", "route" for others) |
| `pair_noun` | `""` | duplicate-key example noun in the pairing note ("postmile"); `""` ⇒ `id_noun` |
| `sides_noun` | `"systems"` | "both systems" / "both environments" |
| `medwid_fields` | `()` | field NAMES normalized like Med Wid |
| `date_fields` | `()` | field NAMES date-formatted on Spot Check |
| `data_widths` / `cmp_widths` | `{}` | field name → column width |
| `scope_flat` / `scope_consolidated` | "Per-route" / "Consolidated (all routes)" | Summary scope label |
| `one_sided_note_extra` / `trim_note_extra` | `""` | appended to the yellow/blue note / TRIM note |
| `key_field` | `0` | which header column is the row-identity key (see [§5](#5-key-field-which-column-is-a-rows-identity)) |
| `header_comment` | `None` | `callable(label)->Comment\|None`, hover tooltip on each header cell (HL only) |
| `legend_writer` | `None` | `callable(wb)` run after sheets, before save — appends a Legend sheet (HL only) |
| `ditto_nonasserting` | `False` | `+`-run ditto markers never count as a difference (HL only) — [§7](#7-ditto-non-asserting-highway-log-only) |
| `ditto_resolver` | `None` | DISPLAY-only resolver: tint + comment each ditto cell with its paired value (HL only) |
| `key_normalizer` | `None` | `callable(row, off, key_field)->str` canonical identity token IN PLACE OF the raw key (HL roadbed key) — [§6](#6-roadbed-aware-key-normalizer-tsmis-vs-tsn-only) |
| `context_fields` | `()` | field NAMES shown but NON-ASSERTING — never count as a diff, never get the ≠ mark; the cell coalesces to whichever side has a value (v0.17.0; Ramp Detail's TSN-only DB columns) |
| `extra_sheet_writer` | `None` | `callable(wb, ctx)` run after the sheets, before save — appends a custom sheet: the familiar-layout rollup (v0.17.0; the Summary reports) and the Intersection Detail **"Report View"** replica (v0.17.8 / §9f). `ctx = {rows_a, rows_b, has_route, sc, side_a, side_b}` |
| `report_view_diff_check` | `()` | optional `(sheet, Diffs-column, physical-row-repeat)` aggregate Summary invariant for typed two-line Report Views; requires `extra_sheet_writer`. It detects total-count drift, not same-count value changes. |

Both v0.17.0 fields keep the lock: default `()`/`None` → `is_context` is always False / no extra
sheet, so every existing comparison (and the Route-1=969 HL canary) is byte-identical.
`field_indices` still includes context columns (they show), but the per-field equality + the
Comparison-cell formula + the Spot Check skip them, so they contribute zero diff cells.

Derived: `n_fields = len(header)-1`; `field_indices` = every header index except `key_field`, in
display order (`key_field==0` gives `[1..n]` — the original byte-identical path).

**`_sref(name)`** quotes a side name for an Excel formula sheet reference: BARE when it's a plain
identifier (`TSMIS`, `TSN` stay unquoted — byte-identical to the approved sample), QUOTED
otherwise (`'SSOR-PROD'`, `'Only in TSMIS'`). It deliberately quotes names that look like a cell
reference (`A1`..`ZZ9999999`) so a side named like a cell can't be misread. Every formula that
names a side goes through `_sref`, so cross-env labels work without touching the locked TSMIS/TSN
text.

---

## 4. Workbook structure + the two flavors

### Sheets (display order, also creation order in the streaming workbook)

`Summary` / `Spot Check` / `Comparison` / `(Routes)` / `Only in <A>` / `Only in <B>` / `<A>` /
`<B>`. The `Routes` sheet exists only in the consolidated (`has_route`) shape.

- **Summary** — row counts, match status, route coverage (consolidated), per-field diff counts,
  the **verdict banner**, live **SELF-CHECK** rows, how-to notes. First sheet ⇒ active on open.
- **Spot Check** — one row under a microscope: type a Comparison row number (or find by key), the
  sheet lays it out field-by-field with the RAW values from both data sheets next to an
  INDEPENDENTLY recomputed verdict (same TRIM / Med-Wid rules, computed straight from the data
  sheets, NEVER reading the Comparison's answer) and an `Agree?` OK/CHECK column. **The two source
  rows themselves are derived independently too (CMP-AUD-218):** the row's hidden literal key
  token (Comparison's trailing `__CMP_E2_KEY_V1_TOKEN` column, written in both flavors) is
  MATCHed into each side's literal `Key (helper)` column — Comparison's stored row links are
  never consumed for row matching — and the **Row integrity** line (row 14, loud CF)
  EXACT-compares Comparison's claimed rows/status against that derivation, so a consistently
  relinked pair or a falsely one-sided status says CHECK. Opens pre-set to
  `first_diff_row` (the first matched row with differences). Stays LIVE in both flavors.
- **Comparison** — one row per `(route,) key + occurrence` in document order. Matched cells show
  the matched value; differing cells show `a ≠ b` in red. Hidden, versioned state-mask columns
  carry one `E` / `D` / `N` / `U` code per field (equal, different, non-asserting, one-sided).
  Conditional formatting, row `Diffs`, Summary field counts, and Spot Check read those codes;
  `_DIFF_MARK = " ≠ "` is presentation only and literal source text containing it is ordinary
  content. One-sided rows are tinted yellow (A-only) / blue (B-only) and show that side's values.
- **Only in <A>** / **Only in <B>** — every one-sided union row in union order, full field data
  pulled live from that system's data sheet. Consolidated mode adds a "Missing from <other>"
  column ("entire route" — tinted — vs "this <noun> only"). NOTE: one-sided rows have ALWAYS been
  in the Comparison sheet too (via `union_keys`' single-side emit); these tabs exist because
  65k-row sheets buried them.
- **Routes** (consolidated only) — per-route coverage: Both / A-only / B-only with live per-route
  row / matched / with-diffs / differing-cell counts.
- **<A>** / **<B>** — the two inputs copied in, with a leading "Comparison row" back-link column
  (A) and a literal opaque "Key (helper)" column at the end. Route/key columns stay in their input
  position. A Med-Wid field appends five hidden, versioned TRIM/CORE/VALID/MASK/CANON helpers;
  formula mode keeps them live and values mode writes their exact literal twin. Hidden freshness
  chunks compare every current source/helper cell against the corresponding very-hidden
  `__CMP_E2_SNAPSHOT_A/B` sheet, with a tail sentinel for appended rows.
- **`__CMP_E2_SNAPSHOT_A/B`** — very-hidden immutable build snapshots containing every source cell,
  opaque helper, and literal Med-Wid stage. They certify that row identity and duplicate assignment
  still match the visible source sheets; they are not user-facing comparison tabs.

### Two flavors via `mode=` ("formulas" | "values" | "both")

`run_compare(..., mode=...)` — the GUI Compare tab has two checkboxes (both ticked by default;
≥1 required). The mirror that powers the run summary (`count_diffs` / `_field_value`) ALSO
produces the literal cells and literal state masks of the values workbook. Formula mode derives
the same state codes with blank-safe, case-sensitive `EXACT` expressions. The Phase-3 E1 gates
lock Python counts, values displays/masks, formula displays/masks, Summary, Spot Check, and
conditional formatting to that one state model. Familiar secondary views remain separately
tracked in Phase 7, but any post-build source/helper mutation now invalidates the workbook's
certifying headline.

| | formulas | values |
|---|---|---|
| cells | statuses, state masks, displays, per-field diffs, and summary counts are LIVE observations; any source/helper edit makes Summary say `REGENERATE REQUIRED` because build-time identity/pairing is stale | the same sheets / CF / links, but the bulk is plain computed RESULTS plus literal state masks; edits likewise invalidate certification |
| consolidated calc | ~2M formula cells; ships in **manual calculation mode** (`calcMode="manual"`, `calcOnSave=False`, `fullCalcOnLoad=False`); opens instantly showing blank/0, user presses F9 once, then saves (per-route files stay automatic) | automatic calc, no F9 banner |
| size | larger | ~⅓ the size; opens instantly |
| live in values flavor | n/a | ONLY the Spot Check sheet + the SELF-CHECK rows stay live (they recount the literal sheets) |

`mode="both"` writes the picked name (formulas) + `<name> (values).xlsx` next to it.
The values workbook is the canonical transactional member and commits first; formulas is
best-effort and a failure is reported truthfully without retracting committed values. A
pre-existing derived values twin requires a single-use server token bound to that exact path;
a decline, mismatch, replay, or late unapproved twin fails closed.

Every public comparator owns one `artifact_store.commit_workbook` transaction. It binds the
effective selected/discovered source identities, rejects every final/derived destination that
canonically or physically aliases a source (including hardlinks and linked directories),
exclusively reserves unpredictable regular-file temps, validates their identity and workbook
shape, and rechecks before publication/cleanup. Everything-Matrix callers additionally pass a
target-aware `commit_guard`; direct and baseline callers use the same transaction without a
user-destination lease.

After workbook promotion, the transaction attaches one UUID `ArtifactGeneration`, the exact
requested/committed member set, and each member's SHA-256, size, and mtime. Central classic
`mode="both"` publishes values plus the optional formulas workbook as peers in that one
generation. `consolidation_meta.write_comparison_outcomes` first protects every member with a
conservative sentinel. Schema v3 stores one canonical compressed `ComparisonOutcome` in shared,
content-addressed sibling chunks and keeps a small identical manifest in each peer envelope;
strict inline schema-v2 records remain read-compatible. The writer holds a permanent parent-scoped
thread/process lease through sentinel creation, process-interruption-safe no-replace chunk
installation (power-loss durability is not claimed — directory entries are never fsynced and
readers fail closed on torn state, CMP-AUD-131), every
final, sentinel cleanup (identity-bound: Windows deletions go through a verified handle so a
same-path foreign replacement survives, CMP-AUD-130), and an exact-own-generation postcheck. Conflicting chunk names use one of
eight deterministic exact-byte fallback slots and are never replaced. Readers validate every
envelope, peer, sentinel, workbook digest, manifest, and generation binding before decoding the
shared payload once. The decoded limit is 64 MiB in at most sixteen 4 MiB chunks with a 32:1
pre-decompression expansion ceiling. Interrupted, missing, mixed-schema, mismatched-generation,
replaced, over-limit, malformed, or digest-tampered generations remain untrusted. A successful
result carries a matching succeeded `AttemptState`.

This artifact identity is deliberately separate from the public terminal-result contract above.
A returned failure/cancellation/`no_data` attempt is still typed even when it produced no reusable
artifact, but it has no `ArtifactGeneration`, no member sidecar, and no generation ID to offer a
consumer. Conversely, a failure while publishing metadata for already-committed bytes retains the
real generation/attempt axes in their fail-closed publication state rather than fabricating or
discarding identity.

All production consumers call `consolidation_meta.require_published_comparison`: returned status,
typed outcome, committed generation, succeeded attempt, trusted/current persisted sidecar, member
digests, and generation IDs must agree exactly. A returned/persisted disagreement is not repaired
or inferred from workbook prose. The compatibility bridge will eventually be replaced by the
Phase-5 generation manifest.

Current limitation: Matrix `also_formulas` builds values and formulas through two comparator calls,
so those twins still receive different generation IDs. Unifying them, the last-complete versus
unpromoted-partial policy, universal source/producers identity, and durable failed-attempt history
remain Phase-5 work (CMP-AUD-075/082/084/089). Exact-generation evidence publication remains the
separate Phase-7 transaction; the typed public terminal boundary does not claim either later-phase
closure.

### Streaming write (`write_only`)

The workbook is written in openpyxl's **STREAMING (`write_only`) mode**: the consolidated
comparison carries ~2M formula cells, which normal in-memory mode cannot save in reasonable time
or RAM (same reason the consolidators stream). Streaming rules: sheets created in DISPLAY order;
`freeze_panes` / widths / `auto_filter` / conditional formatting set BEFORE rows are appended;
styled cells are `WriteOnlyCell`s.

---

## 5. Key field (which column is a row's identity)

A row's key is `CompareSchema.key_field`, the column that IS its identity — **not necessarily
`header[0]`** (v0.11.0). `keys_for(rows, has_route, key_field, key_normalizer)` builds
`[(route, key, occurrence)]` in file order; repeats of the same `(route, key)` are numbered
`1..`. After exact duplicate pairing, each final tuple receives a versioned opaque ordinal
helper token used by every workbook `MATCH`; raw components are never delimiter-flattened. The key sits at
`r[(1 if has_route else 0) + key_field]`; the column stays in its display position everywhere —
only the alignment identity and the Comparison sheet's lead column change.

Settings in use:

- **Highway Log** keys on **Location** (its first column → `key_field=0`).
- **Cross-env Highway Sequence and Ramp Detail** key on the granular **`PM`** (postmile), NOT
  their coarse first column (County / a district-county-route Location that repeats for hundreds
  of rows). `EnvCompare.key_col="PM"` → `_resolve_key_field` matches it in the loaded header
  (stripped, case-folded) and falls back to the first column **with a log warning** if absent
  (layout drift degrades, never crashes).

Why it mattered: the coarse key aligned rows positionally within the group and inflated
diffs/one-sided rows. PROD-vs-DEV Highway Sequence went **15,797 → 5,070 diff cells** when re-keyed
on PM; cross-env Ramp Detail PROD-vs-TEST was a delivered **1,451 diff cells / 563 rows** that was
~99.4% positional-misalignment inflation (TEST inserts ramps mid-list on routes 005/010S/071/091/101)
— the TRUE difference is **8 cells / 4 rows** (routes 014/395/780/880 missing Area 4 + R/U in
TEST) + 10 genuinely TEST-only ramps. The v0.11.0 PM re-key was validated against real 3-env data
(every number reproduced ≥3 independent ways): PM is NOT unique within ~10 county-crossing routes,
so the engine's `(PM, occurrence#)` keying is the correct design.

### Blank-key-field SELF-CHECK bug (v0.11.0 fix)

Cross-env Highway Sequence failed 6/9 SELF-CHECK rows while Highway Log passed 9/9. Root cause was
**blank values in the key field** (HwySeq County was blank on 4 SSOR-PROD / 117 SSOR-DEV rows),
NOT occurrence collisions. Two general engine bugs (any report with a blank-able key field): (A)
self-checks counted rows via `COUNTA(<keyfield-col>)-1` → undercounted blank rows → false CHECK;
(B) a live-COUNTIFS occurrence key mis-numbered blank-key rows (Excel's blank-criterion quirk) so
they didn't reconcile with the build's literal `#`. **Fix:** the data sheets now write **literal
lookup keys in the formulas flavor too** (not a live COUNTIFS — see `run_compare`'s `hk_t`/`hk_n`
and `_write_data_sheet`), and SELF-CHECK / row counts use the always-present back-link column A +
the numeric occurrence column instead of `COUNTA(<key field>)`. Verified Excel-COM (6/9 CHECK +
wrong verdict → 9/9 OK + correct); locked by `build/check_compare_blankkey.py`.

---

## 6. Roadbed-aware key normalizer (TSMIS-vs-TSN only)

`CompareSchema.key_normalizer` (opt-in; v0.14.0). On a divided highway the TWO sources encode the
roadbed of a segment's two rows DIFFERENTLY:

- **TSMIS (PDF + Excel)** suffix the Location: `R021.466R` / `…L`.
- **TSN** omits the suffix (`R021.466`) and instead **dittos** the non-subject 8-column block (a
  Left-block-dittoed row IS the right roadbed).

Keying on the raw Location therefore SPLIT the same physical roadbed row into a false one-sided
pair (~1,400 rows / TSMIS-vs-TSN comparison, hiding ~4,800 genuine diffs). The suffix↔dittoed-block
correspondence is **100%** (audit-verified, raw-PDF traced: suffix R → left-block-dittoed = right
roadbed 788/788; L → 658/658). `highway_log_columns.roadbed_canonical_location` (set as the
TSMIS-vs-TSN schema's `key_normalizer`) derives the roadbed from the suffix when present, else from
the dittoed block, appending it to suffix-less Locations so the same roadbed row keys identically.

The key **STRICTLY REFINES** (can split, never merge): 0 roadbed crossings (vs 6.2% for a naive
postmile-only pairing), 0 over-merges (TSN 59,156 raw → 59,482 norm keys). The trailing equation
`E` marker and the leading alignment prefix are PRESERVED and deliberately NOT reconciled (a
route-start `R000.000` never collapses into a bridge `000.000`; `E` variants stay distinct).

`keys_for` gained the `key_normalizer` param: `None` = byte-identical raw-Location key, so every
non-HL comparison AND cross-env TSMIS-vs-TSMIS are untouched. It is **cleared on
`compare_env._HL_BASE`** (cross-env compares two TSMIS exports — SAME roadbed encoding, both
suffix — so the unifier is unnecessary and would only perturb the validated cross-env output;
it is a TSMIS-vs-TSN tool). PDF-vs-Excel is INVARIANT (both sources already suffix). The DATA
sheets still show each source's raw Location — only the match/alignment key TOKEN is unified.

**Effect on real data:** PDF-vs-TSN both 45,352 → 46,755 (+1,403 paired), one-sided
5,207/14,731 → 3,804/13,328, diff_cells **170,243 → 175,048** (~4,805 hidden diffs surfaced).
Excel-vs-TSN similarly → **179,328**. PDF-vs-Excel invariant (5,370). Trailing-R/L one-sided
residual 1,446 → 30. Residual: ~11 Excel rows whose own export bug drops the suffix AND blanks
(not dittos) the block stay conservatively one-sided (roadbed unrecoverable there). Locked by
`build/check_highway_log_roadbed.py`; study doc §7b in
[highway_log/comparison-study.md](highway_log/comparison-study.md).

---

## 7. Ditto non-asserting (Highway Log only)

`CompareSchema.ditto_nonasserting` (opt-in; v0.14.0). A cell whose value is a `+`-run ditto marker
(`+`, `++`, `+++`) is **NON-ASSERTING**: it NEVER counts as a difference against the other side
(its real value is compared on the paired roadbed's own row). The DOMAIN convention — a `+`-run
marks a fully-dittoed ROADBED BLOCK meaning "this roadbed is not the subject of this row; its value
is on the paired roadbed's own row" — and its structural evidence are owned by
[highway_log/comparison-study.md](highway_log/comparison-study.md). The detector is
`highway_log_columns.is_ditto`; the engine carries a local mirror `_is_plus_run` (so the generic
engine has no HL import), gated entirely by `ditto_nonasserting` so it is inert for every other
comparison.

Wired through (all gated): the Comparison equality formula (`_eq_with_ditto` wraps the eq with
`OR(_isditto_xl(t), _isditto_xl(n), eq)` so a ditto on EITHER side is equal), the Spot Check
verdict, `_field_value`, `count_diffs`, `_row_diff_count`. The detection is **column-agnostic**
(`_is_plus_run` checks the value, not the column) — so counting was correct even before the
display fix that added the median/AC band; a v0.14.2 fix made the *display* resolver
column-agnostic too (marks all 1,020 median/AC dittos on TSN divided-highway rows, 340 each in
AC / Med TY/CL/BA / Med Wid, not only the two 8-column roadbed blocks).

**Display (`ditto_resolver`):** the data sheets keep the RAW `++` in the cell (the non-asserting
diff needs to detect the `+`-run) but tint it lavender (`_DITTO_FILL = "E4DFEC"`) and attach a
comment with the paired-roadbed value ("Ditto ('++') … resolves to: 11. Not counted as a
difference."). `highway_log_columns.display_fills` is a route-aware wrapper over
`fill_paired_roadbed`. `None` for every other comparison ⇒ data sheets stay byte-identical.

**Impact:** flag OFF = byte-identical (Route-1 unchanged at 969). On real PDF-vs-Excel consolidated
the flag removed EXACTLY **14,896** ditto cells; both/one-sided rows unchanged; values flavor 0
residual ` ≠ `. Impact varies by structure: ~14,900 cells on PDF-vs-Excel (same report, ditto rows
align 1:1) but only ~1,200 on the TSN comparisons (TSN's roadbed-decomposed rows mostly land as
one-sided, not matched-row diffs). Locked by `build/check_compare_ditto.py`.

**Tab fix (related, HL loader only):** the TSMIS Excel export pads Description with trailing TAB
characters, which Excel's TRIM (and `_xl_trim`) do NOT strip → an otherwise-identical description
(`END BR 5-95` vs `END BR 5-95\t\t\t`) showed as a phantom difference. `compare_highway_log.
_hl_normalize` collapses `[\t\n\r\f\v]` → space at LOAD time (HL loader only — other comparisons
go through `normalize_value` directly), so TRIM then collapses them and both flavors agree.

---

## 8. Verdict, incompleteness, and write-path safety

### The verdict (v0.10.0)

Every comparison LEADS with a one-line human answer. `summary_lines[0]` is
`✓ EVERYTHING MATCHES …` / `✗ DIFFERENCES FOUND …` / `⚠ COULD NOT COMPARE EVERYTHING …`.
`ComparisonOutcome.verdict` is `"match"` / `"diff"`, backed by exact `ComparisonCounts`; the legacy
outer verdict mirrors it. Classic UI, Matrix, and validation accept the verdict only from the
trusted returned/persisted generation. `summary_lines` is never parsed as state. The workbook's
Summary carries the same human verdict as a big banner cell right under the title (B3, or B4 under
the manual-calc F9 banner) — a LIVE formula in the formulas flavor (CF green/red keyed on the
`✓`/`✗` first character), a literal in the values flavor. For a complete comparison,
**match ⟺ zero differing cells AND zero one-sided rows**.

### Incompleteness contract (v0.11.0)

An unreadable input is NEVER silently dropped. Loaders reduce both sides into exact completion,
skipped/failed counts, warnings/failures, and diagnostics before `run_compare` commits anything.
An incomplete run may keep outer `status="ok"` because it produced a useful workbook, but its typed
completion is `partial`, its verdict is forced to `diff`, and `summary_lines[0]` leads with the
literal **`⚠ COULD NOT COMPARE EVERYTHING`**. The in-workbook Summary banner uses `✗` so the
existing red CF still applies. Classic UI titles it "Comparison incomplete" from typed completion;
Matrix renders it amber, never with a checkmark or `match`, and treats it as retryable stale. The
skipped files are listed in the notes (first 20, then "…and N more"). A clean match therefore also
requires `completion=complete` and zero skipped/failed inputs.

### Write-path safety (v0.11.0)

- **Formula-injection guard.** Free text beginning `= + - @` (`_FORMULA_LEAD`) or matching an
  Excel/openpyxl error token would otherwise be interpreted as a formula/error cell rather than
  source text. `set_safe_literal_cell` and the guarded writer paths force such values to STRING
  cells (`data_type="s"`) so Excel shows them verbatim. The value is kept
  byte-for-byte (only the cell TYPE changes), so equal sides still compare equal and clean data is
  unchanged — the regression lock is unaffected. Applied to raw input cells on the data sheets, the
  key cells, the helper key, the Comparison/Only-in/Routes literal id cells — never to the engine's
  own `=formula`/HYPERLINK cells. The same guard is in the openpyxl consolidators and visual-evidence
  summaries/captions. Scope confirmed
  by source verification: the free-text Description columns (ramp detail / HSL / highway log /
  intersection detail) re-emitted raw.
- **Load-time canonicalization.** `normalize_value` renders dates/datetimes/times to a fixed ISO
  string and actual Booleans to exact uppercase `TRUE` / `FALSE` text at LOAD time. Numeric 1/0
  and integer subclasses remain numeric. This prevents locale-dependent dates and Python's
  bool-is-an-int inheritance from splitting the two flavors. Callers apply it per cell; the
  copied-source writer stores every finite numeric as its exact `_xl_trim` text so Excel cannot
  rewrite Decimal scale, exponent notation, or precision. NaN/infinity fail before prompts or
  workbook creation. The shared literal helper also retains its >15-significant-digit backstop
  for non-source callers; engine-owned counts/occurrences remain numeric.
- **Limit / collision guards.** `excel_limit_error` checks before writing: a workbook past
  `XL_MAX_ROWS=1,048,576` or `XL_MAX_COLS=16,384` fails cleanly (with guidance to compare a smaller
  scope) instead of openpyxl raising mid-write (losing the partial file) or silently dropping
  columns. `run_compare` also rejects, before writing, any sheet name over 31 chars and any
  side-name⇄fixed-sheet-name collision (a side literally named `Summary`/`Comparison`/`Routes`/
  `Only in …` would collide).

### Med Wid formula/value parity (Phase-3 E1)

Both flavors now implement one narrow, decimal-exact grammar:
`ASCII-digits[.ASCII-digits][optional one printable-ASCII suffix]`. The suffix must be U+0021
through U+007E and cannot itself be a digit or dot. Leading integer zeros and trailing fractional
zeros are insignificant; suffix case is significant. Signs, leading decimals, exponents,
multiple suffixes, Unicode digits/letters, and control-character suffixes remain raw text.

Python canonicalizes with strings/`Decimal` semantics and never binary float. Formula mode uses
five short hidden stages per Med-Wid source field (TRIM, CORE, VALID, MASK, CANON) and compares
CANON with `EXACT`; it never calls `VALUE`, `NUMBERVALUE`, or another lossy/coercive numeric
function. Values mode writes the same stages as literals. Spot Check owns an independent staged
twin and preserves a true blank before `INDEX` can coerce it to numeric zero. Every generated
formula is checked against Excel's 8,192-character ceiling and all hidden physical columns count
toward the 16,384-column preflight.

---

## 9. The three comparison families

All built by `compare_core`. The GUI Compare pane renders one **sub-tab per `COMPARE_GROUPS` id**
(v0.16.1: `env` "Cross-environment" default, `tsn` "vs TSN"; the GUI appends a third sub-tab, the
day-keyed "vs TSN Matrix", on its own). Every report's "between environments" compare lives in
`env` (Highway Log included now); the file-based TSMIS-vs-TSN compares live in `tsn` (every report
as of v0.17.0). Each `COMPARE_REPORTS`
row `(label, module_or_adapter, kind, group)` shows only under its group. `kind` is `"files"`
(file-vs-file) or `"folders"` (folder-vs-folder) — independent of `group`. See
[reports.md](reports.md) for the registry + sub-tab wiring.

> **Shared substrate (`compare_tsn_common`, imported as `ctc`).** The five non-HL vs-TSN
> FILE comparators (§9c Ramp Detail, §9d Ramp Summary, §9e Intersection Summary, §9f
> Intersection Detail, §9g Highway Sequence) share one substrate: `ctc.norm_pm` /
> `ctc.iso_date` (the postmile/date normalizers), `ctc.make_notes_writer` (the Notes-sheet
> builder), and `ctc.run_files_compare` (the load-both-sides-then-`compare_core` driver). A
> comparator supplies its own loaders + `CompareSchema` and calls `ctc.run_files_compare`;
> Highway Log keeps its own (older) driver. **Intersection Detail (PDF)** adds
> `compare_intersection_detail_pdf` — `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL`, reusing
> §9f's schema and loaders, the exact parallel of §9b's Highway Log (PDF) pair.

### 9a. TSMIS vs TSN Highway Log — `compare_highway_log.py` (`"files"`, group `highway_log`)

Schema + loaders + `suggest_name`. Takes a TSMIS Highway Log and a TSN Highway Log — **either two
per-route workbooks (31 columns) or two consolidated ones (`Route` + 31)**. Shapes are
auto-detected by `highway_log_columns.recognize()` (accepts EITHER the corrected labels OR the old
vendor labels — it aligns by POSITION and relabels to the canonical header for display); mixed
shapes are rejected with guidance.

`_SCHEMA` sets: `side_a="TSMIS"` / `side_b="TSN"`, `id_noun="location"`, `pair_noun="postmile"`,
`medwid_fields=(hlc.HEADER[19],)` ("Med Wid/Var [Med Wid]"), `date_fields=("Date of Rec",
"Sig Chg. Date")`, `header_comment=hlc.comment_for`, `legend_writer=hlc.write_legend_sheet`,
`ditto_nonasserting=True`, `ditto_resolver=hlc.display_fills`,
`key_normalizer=hlc.roadbed_canonical_location`. (Highway Log corrected columns →
[highway_log/columns.md](highway_log/columns.md).)

It writes the approved discrepancy workbook — Summary / Comparison / **Only in TSMIS / Only in
TSN** / TSMIS / TSN, plus a **Routes sheet in consolidated mode**. Consolidated mode adds a
"Missing from <other>" column ("entire route" rows tinted, v0.9.0) so wholly-missing routes are
impossible to overlook. Med Wid compares after zero-pad normalization (TSMIS `0Z` = TSN `00Z`,
`6V`/`06V`).

**Since the TSN normalizer's v5 (CMP-AUD-157/045-HL, 2026-07-17)** the TSN side must be a
CURRENT normalized workbook: `_load_pair_tsn` refuses a file without the v5 "TSN Normalization"
marker sheet with a rebuild hint (a pre-v5 file merges the detached suffixed-route sections —
"07 LA 005 S" = route 005S, 317 rows statewide — into the base routes and drops asterisk-leading
printed Descriptions). The per-run schema (`_schema_with_claims`) writes the Legend AND a
**Notes** sheet exposing the normalized workbook's conserved source claims from its sidecar
(print identity, the suffixed sections, the ADT/totals dispositions + totals reconciliation
summary); absent claims get an explicit rebuild hint. The honest HL identity is
(Route, roadbed-canonical Location); the TSMIS export has no County column, so the TSN print's
district/county/route ownership rides the sidecar as a per-document CLAIM, never a key.

### 9b. Highway Log (PDF) — `compare_highway_log_pdf.py` (`"files"`, group `highway_log`)

Two file-vs-file comparisons (v0.14.0) that sidestep the buggy vendor Excel by sourcing the TSMIS
side from the **PDF** consolidation. Both reuse `compare_highway_log._load_input` (any 31-column
Highway Log workbook, per-route or consolidated) and `replace(_hl._SCHEMA, …)` to override ONLY the
two side labels + notes (engine text untouched → regression lock intact). Each carries
`file_a_label` / `file_b_label` so the GUI's two file pickers and the data sheets are named for the
actual sides (not hard-coded TSMIS/TSN).

| instance | sides | purpose |
|---|---|---|
| `TSMIS_PDF_VS_TSN` | "TSMIS (PDF)" vs "TSN (PDF)" | accurate replacement for 9a — BOTH sides from PDFs, so the PDF-vs-PDF nature is explicit and the vendor Excel bug never enters; `tsn_side_b=True` applies 9a's v5 marker gate + claims Notes to its TSN side |
| `TSMIS_PDF_VS_EXCEL` | "TSMIS (PDF)" vs "TSMIS (Excel)" | diffs PDF-parsed data against the vendor Excel of the SAME report to pinpoint the export's errors; no TSN side, so no TSN-marker gate |

**PDF-role provenance (CMP-AUD-066, 2026-07-17).** Every workbook the app writes FROM PDFs —
the five per-route converted files and every combined conversion — carries a very-hidden
versioned `TSMIS PDF Conversion` marker sheet (`pdf_table_lib.write_pdf_source_marker`;
opt-in on `write_route_workbook` because the TSN Highway Log consolidator shares that
writer and stays unmarked). The HL / HSL / HD / ID flavors enforce roles at load
(`compare_tsn_common.require_pdf_source` / `reject_pdf_source`): a "TSMIS (PDF)" side
must carry a valid marker (an unmarked or pre-marker workbook refuses with a
re-consolidate hint — re-consolidating once re-earns the role), a "TSMIS (Excel)" side
must NOT carry one (valid or malformed — `pdf_source_marker_state` fails closed both
ways), and the vs-TSN flavors' PDF sides gate identically. Ramp Detail needs no gate:
its print-only On/Off + Ramp Type columns already make the Excel shape unloadable as
the PDF side. Historical Excel-consolidated workbooks stay fully usable on the Excel
role. Pinned in `check_pdf_role_provenance`.

**Same-source projections (CMP-AUD-067, 2026-07-17).** The PDF-vs-Excel self-check
flavors no longer reuse the cross-system (vs-TSN) value projections — those crosswalks
exist to bridge TSN's encodings and were erasing the render differences the self-checks
exist to detect. Each family now separates PAIRING identity from value projection:
Highway Sequence already had its own same-source loader (CMP-AUD-199/204); Ramp Detail
was always verbatim; **Intersection Detail** projects every value cell verbatim on the
unchanged 045 physical pairing key (`_tsmis_row_with` — the control-type J→S fold and
its display rewrite no longer apply between two TSMIS renders); **Highway Detail** keeps
the canonical roadbed-aware Post Mile as the pairing key but appends the RAW printed
token as its own compared "PM (raw)" cell and compares NA (and everything else)
verbatim; **Highway Log** keeps the §7b roadbed-canonical key + ditto conventions
untouched and appends "Location (raw)" as a compared cell in the PDF-vs-Excel flavor
only. The one kept normalization outside the owner-ruled render equivalences is HD's
typed-date fold (openpyxl cell typing, value-identical). Guarded end to end by the
`check_compare_same_source` mutation matrix (every finding mutation red pre-fix,
identical-render MATCH pins everywhere).

**Direct-path freshness marker (CMP-AUD-037, 2026-07-17).** The matrix/library path
refuses a stale normalized TSN library through the D2 certificate
(`normalization_version`), but a *classic file comparison* trusted ANY workbook that
carried the normalized sheet — so a library built by an older normalizer was silently
compared, resurrecting whatever that version got wrong (an otherwise-identical row split
into two one-sided rows for "005" vs "5"). The XLSX-sourced families now stamp their
normalized workbook with an in-workbook **"TSN Normalization"** marker sheet (the shared
`compare_tsn_common.write_normalization_marker` / `normalization_marker_version` /
`require_current_normalization`; `tsn_library.build_normalized(marker_version=…)` writes
it, the write-only workbook included), and each direct loader (`_load_tsn`) refuses a
pre-current file with a rebuild hint before trusting the sheet — **Highway Detail's loader
had no freshness gate at all before this**. The version constant lives in each comparator
(`NORMALIZATION_VERSION` — Ramp Detail 5, Intersection Detail 5, Highway Detail 3; the
`tsn_load_*` loader already imports the comparator, so this direction avoids a cycle) and
the catalog `normalization_version` MIRRORS it. Each was a marker-ONLY bump: the normalized
rows are byte-identical to the prior version (proven on the real statewide corpus — an
unmarked rebuild's data rows equal the marked rebuild's exactly), so the D2 rebuild that
adds the marker moves no comparison count. This mirrors the consolidator families' own
marker (Highway Sequence v4, Highway Log v5). Pinned in `check_tsn_normalization_marker`
(helper round-trip incl. write-only + the mirror invariant + the real `build_normalized`
seam) plus each family check's refusal/acceptance flow.

**Exact header binding (CMP-AUD-033, 2026-07-17).** The same four `_load_tsn` loaders
discard the header and read cells BY POSITION, so a semantically reordered or renamed
normalized workbook silently mis-mapped every column (a reordered sheet loaded PM as a
county code). Each now calls `compare_tsn_common.require_shared_header_prefix` first: it
binds the header to the EXACT ordered `['Route'] + SHARED_HEADER` prefix (rejecting
missing / renamed / reordered / duplicated shared columns; cell whitespace tolerated) and
requires the trailing columns to be exactly the documented sidecars (Ramp Detail: TSN
District/County/PM Suffix; Intersection + Highway Detail: TSN District/County; Highway
Sequence: none). The comparator owns the sidecar list (`_NORMALIZED_SIDECARS`), gated equal
to the loader's `SIDECAR_HEADER` by `check_tsn_normalization_marker`. This runs alongside
the 037 marker gate, so a reordered header is refused with or without a marker.

### 9c. TSMIS vs TSN Ramp Detail — `compare_ramp_detail_tsn.py` (`"files"`, group `tsn`; remediation pending)

The current **v0.17.0 product comparator** was the recipe later reports followed, but its
source semantics are now superseded by the accepted Stage-8 oracle. Both sides are XLSX
in different shapes, so each side has its own loader projecting to one shared header
currently keyed on **PM**: the TSMIS side reads the **consolidated** Ramp Detail workbook
**by POSITION** (its
header row is column-shifted — the City Code / R/U / Description labels sit right of their values);
the TSN side reads the statewide raw `Sheet 1` (18 DB columns) or the library's normalized workbook,
taking the route from `LOCATION` ("01-DN-101"→"101"). Normalization: PM zero-pad → one canon,
`Date of Record` → ISO, Description drops the TSMIS leading `"<route>/"` prefix; TSN `POP` maps to
TSMIS `R/U`. `_SCHEMA` sets `key_field=PM`, `date_fields=("Date of Record",)`, and
**`context_fields=("Ramp Name","On/Off","Ramp Type","ADT")`** — the TSN-only DB columns, shown for
reference but never counted (see [§3](#3-compareschema-the-parameterization)). The TSN side is
normalized once into the canonical TSN library via `tsn_load_ramp_detail.build_into`; normalization
v3 appends District/County sidecars, but this comparator currently slices them away.

The accepted identity is **`(Route, County, norm_pm(PM))`**, not Route+PM. The exact TSN source has
81 weak Route+PM keys spanning 163 county identities. County must stay visible and participate in
identity; District is a separate asserted field. At `005/SD/72.366`, both TSMIS representations say
District 12 and both TSN representations say 11, but the current product omits District and calls
the row identical (CMP-AUD-185). Description normalization also deletes exactly 15 authoritative
numeric prefixes (CMP-AUD-135), while raw `PM_SFX`, `ADT_EFF_YEAR`, and `EFF_DATE` claims remain
outside the comparison/evidence projection (CMP-AUD-133).

For the bound 2026-07-09 source pull, independent Excel-vs-TSN truth is **15,212 paired, 4/198
one-sided, 14,471 identical, 741 differing rows, and 847 differing cells**. Independent
PDF-vs-TSN truth is **15,212 paired, 4/198 one-sided, 14,438 identical, 774 differing rows, and 998
differing cells**. PDF-vs-Excel pairs all 15,216 rows and differs in exactly four Description cells.
Current production instead reports 861 and 1,012 vs-TSN cells: 15 false Description differences
minus the one hidden District difference. Raw and normalized TSN product paths are semantically
identical, so this is a comparator contract defect, not a stale-library discrepancy. The permanent
source/business gate is `build/check_phase8_ramp_detail_comparison.py`; the legacy product fixture
remains useful only to reproduce the red behavior. Exact bindings are in
[comparison-canary-bindings.md](planning/comparison-perfection/comparison-canary-bindings.md).

### 9d. TSMIS vs TSN Ramp Summary — `compare_ramp_summary_tsn.py` (`"files"`, group `tsn`, **AGGREGATE**; remediation pending)

The first **AGGREGATE** vs-TSN comparator — the recipe for the two Summary reports. Unlike the
FLAT comparators (per-PM rows), each side reduces to ONE statewide `{category: count}` table, so
the comparison runs with **`has_route=False`**, `header=[Category, Count]`, `key_field=0` (the
category is the key, the count is the single field). The TSMIS loader **sums** the consolidated
Ramp Summary workbook's per-route sheet column-by-column (the same totals its live "Combined"
sheet shows); the TSN loader parses the **statewide PDF** directly (reusing
`consolidate_ramp_summary`'s geometry helpers — see [tsn-parsers.md](tsn-parsers.md)) or reads the
library's normalized `Category|Count` workbook (`tsn_load_ramp_summary.build_into`). The canonical
category list (the **16-ramp-type superset** incl. the TSN **P/V** "Dummy" classes + the grand
Total) lives in `summary_layout.RAMP_SUMMARY_SPEC`, shared with the familiar sheet. A
**"Summary by Category"** familiar-layout sheet (TSN sections/labels/order; *Category | TSMIS |
TSN | Δ*) is appended via `extra_sheet_writer=summary_layout.make_extra_sheet_writer(SPEC)`.

The accepted Stage-8 contract does **not** treat missing TSMIS Summary classifications as zero:
P/V are **Only in TSN**, while `Ramp Points w/out linework` is a display/provenance footer and is
excluded from comparison membership and verdicts. For the bound 2026-07-09 source pull, the exact
shape is **29 both, 0 only-TSMIS, 2 only-TSN, 24 differing shared, 5 identical shared; TSMIS 15,216
vs TSN 15,410**. Same-pull Ramp Detail sources contain P=2 and V=20, independently proving that
Summary absence is not factual zero. The current implementation remains product-red: it projects
P/V as TSMIS zeroes and emits no-linework as Only-in-TSMIS, producing the superseded 31/1/0 shape.
See [tsn-parsers.md](tsn-parsers.md) and the permanent
`build/check_phase8_ramp_summary_comparison.py` gate. Live in both matrices.

### 9e. TSMIS vs TSN Intersection Summary — `compare_intersection_summary_tsn.py` (AGGREGATE, ONE-SIDED divergence)

The AGGREGATE recipe applied to the intersection taxonomy. The category schema
(`summary_layout.INTERSECTION_SUMMARY_SPEC`) spans 11 blocks and 65 taxonomy rows; with
`Total Intersections`, the comparison has **66 union rows**. The spec-driven production
block-walk `summary_layout.counts_from_rows` maps a `(count, code-text)` stream to
`{slug: count}` for both consolidation and TSN projection. That shared mapping keeps the
two product paths aligned, but is not independent proof; the accepted Stage-8 oracle
parses the TSMIS Excel, TSMIS PDF, raw TSN PDF, normalized workbook, and TSNR reference
without importing the app parser.

The raw TSN side is a **three-column statewide PDF** split into left/middle/right x-bands.
TSN's six legacy signal rows **J/K/L/M/N/P project into shared `S - SIGNALIZED`**. Their
individual raw rows remain authoritative provenance and must not be mistaken for six
TSN-only comparison rows. The eight genuinely TSMIS-only rows remain structurally absent
(blank, not zero) on TSN: Intersection Type **R/C/P/+**, Control **R/O/Q**, and Left
Channelization **Y**. `Cat.sides` and `SummarySpec.categories_for(side)` drive that
one-sided membership. Keys are `(block, code-letter)` because many labels were reworded.
The Summary keeps the label `S - SIGNALIZED`; the Detail renders the per-record control
value as code `S`.

The current accepted source binding is the 2026-07-09 ARS pull: 217 Excel files and 217
PDF siblings, with the same ordered route universe, six suffix routes, and route 170
absent. All **14,322/14,322** fixed-layout Excel/PDF values match. Independent comparison
truth is **58 shared / 8 only-TSMIS / 0 only-TSN; 53 differing shared / 5 identical
shared; TSMIS 16,459 vs TSN 16,626**. TSNR plus both same-pull TSMIS formats prove
Control F means red on the mainline; the raw TSN Summary PDF erroneously prints Control
G's “red on all” text for F as well.

Current production reproduces all source-backed values, one-sided statuses/blanks,
verdict semantics, formulas/values twins, and familiar-sheet numbers exactly. Acceptance
does not excuse its open strict-count/duplicate/route-universe, raw-fold/correction-
provenance, metadata, or familiar-note defects (CMP-AUD-020/021/022/023/076/144/145/
146/183/184). See [tsn-parsers.md](tsn-parsers.md) and permanent gate
`build/check_phase8_intersection_summary_comparison.py`. Live in both matrices.

### 9f. TSMIS vs TSN Intersection Detail — `compare_intersection_detail_tsn.py` (FLAT; current product route+PM, approved physical key richer)

The Ramp Detail FLAT recipe for Intersection Detail, forward-ported in v0.18.0 to its **v0.17.8**
state (P15). TSMIS side = the consolidated workbook read **by position** (its header is column-shifted
— the "INT Type" label sits over the eff-date value). Both sides store attribute pairs in (eff_date,
type) order. The v0.17.8 policy is **compare-everything, position-aligned** — `CONTEXT_FIELDS = ()`,
so every shared column (incl. PR, Date of Record, and the 5 cross-street attrs) IS counted; nothing is
suppressed as "context" any more. The locked reconciliations: **(1)** mastarm / right-channelization /
lighting are `Y/N` on TSN but `1/0` on TSMIS — **normalized `Y≡1 / N≡0`** so only genuine changes flag;
**(2)** a **control-type crosswalk** now folds TSN's legacy signalized sub-types (J–P) and "signalized"
into TSMIS's single code **`S`** (`_norm_control_type`) — so an S-vs-P pairing no longer flags, while a
genuinely non-signalized control change (A vs B) still does; **(3)** three numeric fields (Main Line
Length / Intrte Route / Intrte Postmile) are **zero-pad normalized** (`058≡58`, `9.560≡9.56`); **(4)**
routes can carry an alpha route suffix (S/U — the report's "S" column) on TSN but not TSMIS — keyed on
the BASE route so the same intersection still pairs, with the suffix surfaced as a compared `Route
Suffix` column (renamed from the v0.18.0 misnomer "Roadbed" in v0.18.1; figures unchanged). The TSN
side is **re-normalized at compare time** (so a library cached before a normalization change can't mask
it), and a **"Report View" replica sheet** — wired through the opt-in `extra_sheet_writer` — renders
the printed two-line record with a soft/hard (red-but-not-Major vs Major) classification.

**July 2026 site update (v0.22.0):** the export reshaped to **35 columns** (the duplicated second
`ML Eff-Date` gone; `Xing P/S` + `Xing Line Lgth` at the tail) and fixed most of the old structural
classes — Date of Record + INT/Ctrl/Light eff-dates now match TSN ≥99.9% (the ~1-day offset is dead),
booleans are natively Y/N, Location carries the route suffix, the CS gap fell ~37%→~1%. The shared
header is now **33 fields ending `Xing Line Lgth`** (↔ TSN `X_CROSS_OVERRIDE`, newly compared); TSN's
`MAIN_EFF_DATE` became Report-View-only (blue, with the ADT pair). The loader's **header gate refuses
pre-update workbooks** (the old 37-col consolidated shape) with a re-export hint — reading them by the
new positions would mis-map everything from Description on. Soft (red, excluded from Major) is now the
data-driven set (user 2026-07-08): **Int St Eff-Date** (TSN's 2022 bulk stamp vs TSMIS's historical
date — ~99% differ, the one wholesale column left), **ML/CS Eff-Date** (TSN carries the later resurvey
date; ~12%/~3%), and **Route Suffix**; Date of Record + INT/Ctrl/Light differences count as Major.
The statewide real-data canary is **21,675 diff cells / 16,199 matched / 260+427 one-sided** (the 7.8
ground-truth bundle; was ≈163,310/677 pre-update). The offline lock is
`check_compare_intersection_detail_tsn.py`'s synthetic behavior fixture (the S-crosswalk, the boolean
norm, the header-gate refusal, Xing Line Lgth zero-pad matching + genuine-diff flagging, the new
soft/hard split, the numeric-0→'0' canon, the sidecar slice + one-sided "Only in TSMIS/TSN" rows).
Live in both matrices.

**Accepted current-source audit (`ID-79`, 2026-07-13):** the exact 7.9 ARS-prod
217-route Excel/PDF pair and both raw TSN forms establish the physical identity as
`(base Route, County, complete PP, numeric Post Mile)`, not the product's Route+PM.
Raw TSN has 78 Route+numeric-PM cross-county keys / 156 county identities and six real
within-county numeric-PM groups separated by complete PP. Under the strong key,
Excel-vs-TSN is **16,199 paired / 260+427 one-sided / 16,053 differing rows / 21,676
cells**; PDF-vs-TSN has the same row universe and **21,683 cells**. PDF↔Excel pairs all
16,459 rows and differs in exactly **nine** cells—eight Excel trailing-tab Description
values that PDF cannot render and one HG value where PDF plus raw/normalized TSN agree
against Excel. Raw↔normalized TSN pairs all 16,626 rows with zero asserted differences.

All five production legs in both workbook modes reproduce the current overlapping cells,
one-sided inventories, visible source sheets, and hidden snapshots exactly. That is not
semantic acceptance: Comparison omits County/District and keys Route+PM; it re-derives
explicit member Route/`S` from Location; both PDF-vs-TSN legs omit Report View; and the
normalized Report View blanks all 16,626 `MAIN_EFF_DATE`, `MAIN_ADT`, and `CROSS_ADT`
claims that the raw leg maps. These are the exact CMP-AUD-045/068/070/133 red paths.
The source result passes 24 audit invariants and the permanent gate passes 31 mutations;
`production_overlapping_comparison_cells_exact=true` while
`production_value_projection_exact=false` and
`production_comparison_semantics_exact=false`. The older 7.8 21,675-cell count above
remains version-pinned history; it does not override the current 7.9 count.

### 9f-2. TSMIS vs TSN Highway Detail — `compare_highway_detail_tsn.py` (FLAT, route + canonical PM; v0.20.0)

The Intersection Detail FLAT recipe applied to Highway Detail, reconciled against the full statewide
dev bundle (252 TSMIS routes / 51,243 rows vs the 60,083-row `TSAR - HIGHWAY DETAIL` extract). An
early weaker-key reconciliation study matched 46,847 rows; that is historical analysis, not the
acceptance canary. The canonical roadbed-aware key below produces the approved **48,644 paired**
rows. TSMIS side = the consolidated workbook read **by position**
(`Route` + the 34 export columns — labels correct as-is, per `highway_detail_columns`); TSN side = the
raw statewide `Sheet 1` (56 named DB columns) or the normalized library sheet `Highway Detail (TSN)`,
**re-normalized at compare time** (stale-library repair, like §9f). The shared header is **35 columns**:
the canonical **Post Mile** key + the derived **PS** column + the remaining 33 export columns;
`CONTEXT_FIELDS = ()` — everything shared is compared and counted. The locked reconciliations:
**(1) the canonical roadbed-aware key** — TSMIS glues `R`/`L` onto the postmile for an
independent-alignment roadbed row (`'000.080R'`) where TSN prints the bare PM and says R/L in `HG`;
the key = prefix + zero-padded mile + roadbed (from the trailing letter, else `HG∈{R,L}` on BOTH
sides), which took routes like 282/880S from 0 matched rows to row-for-row pairing; **(2) the equation
marker `E` is NOT keyed** — the systems disagree on where they print it (TSMIS `'C043.925R'` ≡ TSN
`'C 043.925 E'`+HG=R), so it is compared as the separate `PS` column (a marker difference flags there
instead of splitting the row one-sided); **(3)** TSN prints an explicit **`NON_ADD='A'`** on ordinary
add-mileage rows where TSMIS leaves `NA` blank (98.7% of matched rows) — `'A'` folds to blank;
**(4)** zero-padding (`'02'`≡`'2'`) on the 12 lane/shoulder/width columns; **(5)** Length normalizes
to the printed 3-decimal mile (TSN stores raw DB precision, 0.01098 → `'000.011'`); **(6)** TSN's
separate `M_WID`+`M_VA` glue to the TSMIS `Med V/WDA` code (`'14Z'`; `medwid_fields` forgives
zero-padding inside it); **(7) `RU Eff` is compared BY POSITION against TSN's `BEG_DATE`** — the
legacy TASAS report prints the ADT profile BEGIN date (a Jan-1 count year) in that slot where TSMIS
prints the Rural/Urban layer date, so the column differs on ~99% of rows (structural; documented in
the **Notes** sheet, "soft" in the Report View — red but out of the Major count, like §9f's dates).
The TSN-only **ADT INFORMATION block** (LK-AHD/P/LK-BACK/CHANGE-MILE/DVM — TSMIS omits it by design)
and TSN's `*`/`Y` change flags are not compared; the ADT block + the TSN district-county-route show
in blue on the **"Report View"** replica (the printed two-line TASAS record, via the opt-in
`extra_sheet_writer`, exactly the §9f treatment). `compare_highway_detail_pdf` adds
`TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL` (the exact §9b/§9f-PDF parallel). Offline lock:
`check_compare_highway_detail_tsn.py` + `check_highway_detail_pdf.py`. Live in both matrices.

### 9g. TSMIS vs TSN Highway Sequence — `compare_highway_sequence_tsn.py` (FLAT, route+**county**+PM)

> **Stage-8 current-source resolution (found 2026-07-13; product landed 2026-07-16;
> CMP-AUD-193 closed 2026-07-22 with a shipped-path replay on the current tip):** the
> v0.24/v0.25 counts bound the historical 7.8-Excel/first-7.9-PDF CROSS-BUNDLE fixture,
> not same-run truth. Current truth is the same-run `All Reports 7.9` pair — 60,494
> Excel / 60,493 PDF rows: route 037 `003.809` is FIXED in the same-run Excel (the
> "Excel drops a Description" story was a cross-bundle artifact — a 7.8 Excel read
> against a 7.9 print; the July-9 Excel refresh added six Descriptions + one row on
> routes 002/010/037/101), four paired PDF Description cells are blank, and one
> described Excel row is absent from PDF (five unrepresented Description claims, all
> preserved as visible differences). Installed Excel proves the four lowercase
> `_x000d_` cells are CRLF (CMP-AUD-197 decodes them). PDF↔Excel identity is Route +
> County + prefix + base PM + occurrence with **"PM Suffix" a COMPARED column**
> (CMP-AUD-199) and duplicate assignment under the CMP-AUD-220 source-identity
> objective; full printed PM remains identity for vs-TSN. The historical canaries stay
> named versioned fixtures (`HSL-78`, `HSL-PDF-79`) and are never current acceptance.

The FLAT recipe with a **county-relative key** — the direct analog of the Highway Log comparison (a
postmile-sequence listing with the same "TSN lists more segment breaks, TSMIS more realignment markers"
one-sided behavior). TSMIS side = the consolidated `Highway Locations` workbook read **by position**
(two unnamed header columns hold a postmile prefix and an equate suffix); the canonical postmile
**re-glues** prefix+PM+suffix. TSN side = a normalized workbook from `consolidate_tsn_highway_sequence`
(word-level PDF parse of the 12 district `Highway Locations` PDFs; the 2-char `G/RF` flag splits into
HG+FT; `EQUATES TO` annotation lines are emitted so they pair with TSMIS `END R REALIGNMENT` rows).
**California postmiles are county-relative** (a route restarts at `000.000` per county), so the key is
composited via `key_normalizer` → `"COUNTY POSTMILE"` (County stays its own visible column;
`pair_occurrences_by_similarity` handles landmarks still sharing a county+PM). Historical shipped
reconciliations: **(1)** County trailing-period strip (`LA.`→`LA` etc. — else whole counties go one-sided);
**(2)** Description strips the TSMIS `^\d{1,3}[A-Z]?/` route prefix + collapses whitespace; **(3)**
`context_fields` = **HG** (TSMIS blanks it for whole counties), **City** (TSN tags it far more
aggressively), **Distance To Next Point** (measured to each system's OWN next listed point — a listing-
granularity artifact, not a disagreement) — shown, never counted; **FT + Description are compared**, with a
**Notes sheet** (`legend_writer`) indicating all of this. Current canary in
[tsn-parsers.md](tsn-parsers.md) (same-run 7.9 pair + v4 TSN library, == the Stage-8 oracle exactly):
**both 57,072 / only-TSMIS 3,422 / only-TSN 12,732; asserted 4,894 rows / 5,589 cells (Description
4,894 + FT 695); 60,494 vs 69,804 rows**. Live in both matrices — completing all 6 reports + HL-PDF.
`compare_highway_sequence_pdf` (v0.25.0) adds `TSMIS_PDF_VS_TSN` + `TSMIS_PDF_VS_EXCEL` (the exact
§9f-PDF parallel, riding this module's loaders + schema) — each flavor carries its OWN Notes sheet
because the print represents EQUATES the TSN way (annotation row + `E` on the equated postmile), so
PDF-vs-TSN pairs BETTER than Excel-vs-TSN (current canary: both **57,505** / asserted **4,916 rows /
5,001 cells** vs Excel's 57,072 / 4,894 / 5,589) while PDF-vs-Excel surfaces the two renders'
representation classes as COMPARED truth (**60,493 paired / 0 PDF-only / 1 Excel-only; asserted
1,410 rows / 3,721 cells — Description 1,133, FT 1,129, HG 910, PM Suffix 549**; the four Excel
`_x000D_` escapes decode as same-source CRLF, and the once-reported route-037 "dropped Description"
was the cross-bundle artifact — see the banner above). Historical cross-bundle figures are retired
to `HSL-PDF-79`. Parser + scripts: `ground-truth/HSL PDF + IS Bundle 7.9/_verification-scripts/`.

### 9c. Cross-environment — `compare_env.py` (the `"folders"` family)

> Group: **`env`** for ALL cross-environment comparisons — Ramp Summary/Detail, Highway
> Sequence, AND Highway Log (v0.16.1 moved HL's cross-env row out of the old `highway_log`
> group). The file-based TSMIS-vs-TSN comparisons live in group `tsn` (§9b).

The SAME report from two **run folders** (ssor-prod vs ars-prod, or one env on two dates). Per-route
files are read straight from both folders (NO consolidation step; merged in memory the way the
consolidators would — Route column prepended, header locked from the first readable file) and
compared with the environment names as the sides (`side_label` → "SSOR-PROD" style; same-env sides
get the run date appended so sheet names differ; `_side_labels` caps to fit Excel's 31-char sheet
limit and falls back to "Side A"/"Side B" on collision).

`EnvCompare` is one adapter per report type, exposing `compare_folders(dir_a, dir_b, out_path, …)`
+ `suggest_name(dir_a, dir_b)`:

| constant | report | subdir / sheet | key | notes |
|---|---|---|---|---|
| `RAMP_SUMMARY` | Ramp Summary | `ramp_summary` / PDF | route (first col) | parses PDFs via `consolidate_ramp_summary.parse_pdf`, one row per route (`has_route=False`); fields = the consolidator's `GROUPS` minus Source/Audit |
| `RAMP_DETAIL` | Ramp Detail | `ramp_detail` / "TSAR - Ramp Detail" | `PM` | per-route XLSX, consolidated shape |
| `HIGHWAY_SEQUENCE` | Highway Sequence | `highway_sequence` / "Highway Locations" | `PM` | per-route XLSX; unnamed internal columns get a stable `(col X)` label |
| `HIGHWAY_LOG` | Highway Log | `highway_log` / `_hl.SHEET_NAME` | Location | `base_schema=_HL_BASE`, `force_header=_hl.EXPECTED_HEADER` (relabels the vendor-mislabeled Excel to corrected labels by POSITION); inherits Med Wid + tooltips + Legend but `key_normalizer` is CLEARED |
| `INTERSECTION_SUMMARY` | Intersection Summary | `intersection_summary` / category sheet | route (first col) | **AGGREGATE per route** (v0.17.0): the per-route export is a CATEGORY-summary sheet, not a flat table, so a `side_loader` (`_load_intersection_summary_side`) parses each file into ONE `[route, total, *category counts]` row via the consolidator's own `parse_route` block-walk (`has_route=False`, `agg_header=IS_HEADER`) — the XLSX analog of `RAMP_SUMMARY`'s PDF path |
| `INTERSECTION_DETAIL` | Intersection Detail | `intersection_detail` / "Intersection Detail" | `Post Mile` | **flat** (v0.17.0): a normal per-route XLSX, consolidated shape, route+PM key (the export header is offset within each type/eff-date pair, but both env sides share the layout so the position-wise compare is valid) |
| `HIGHWAY_LOG_PDF` | Highway Log (PDF) | `highway_log_pdf` / "Highway Log" | Location | **flat, PDF-sourced** (v0.17.0): a `flat_pdf_loader` (`_load_highway_log_pdf_side`) converts each side's PDFs to per-route XLSX (the HL-PDF consolidator's parser) then reads them flat; reuses the Highway Log schema (`_HL_BASE`, `force_header`, Med Wid, ditto/roadbed). The PDF is the accurate HL source, so this is the preferred cross-env Highway Log |
| `INTERSECTION_DETAIL_PDF` | Intersection Detail (PDF) | `intersection_detail_pdf` / "Intersection Detail" | `Post Mile` | **flat, PDF-sourced** (v0.18.0): the exact parallel of `HIGHWAY_LOG_PDF` — a `flat_pdf_loader` (`_load_intersection_detail_pdf_side`) parses each side's PDFs to per-route XLSX (the Int-Detail-PDF consolidator's parser) then reads them flat; reuses the Intersection Detail layout |
| `HIGHWAY_DETAIL` | Highway Detail | `highway_detail` / "Highway Detail" | `Post Mile` | **flat** (v0.20.0): per-route XLSX, consolidated shape, route + glued-PM key (both env sides share the TSMIS encoding, so no roadbed canonicalization — that's a vs-TSN tool) |
| `HIGHWAY_DETAIL_PDF` | Highway Detail (PDF) | `highway_detail_pdf` / "Highway Detail" | `Post Mile` | **flat, PDF-sourced** (v0.20.0): `_load_highway_detail_pdf_side`, the `INTERSECTION_DETAIL_PDF` parallel |
| `HIGHWAY_SEQUENCE_PDF` | Highway Sequence (PDF) | `highway_sequence_pdf` / "Highway Locations" | `PM` | **flat, PDF-sourced** (v0.25.0): `_load_highway_sequence_pdf_side` parses each side's prints with the HSL-PDF consolidator, then reads them flat exactly like the Excel `HIGHWAY_SEQUENCE` row (no header pin — the converted files carry the export's own header, unnamed columns included) |

`EnvCompare` has three shapes: the **flat** path (Ramp Detail / Highway Sequence / Highway Log /
Intersection Detail / Highway Detail — read the per-route sheet rows in consolidated shape); a
**flat, PDF-sourced**
variant (`flat_pdf_loader` — Highway Log (PDF), Intersection Detail (PDF), Highway Detail (PDF)
**and Highway Sequence (PDF)**, which parse each
side's PDFs to per-route XLSX first); and the **aggregate-per-route** path (a `side_loader` yielding
one row per route — Ramp Summary's PDFs, Intersection Summary's category sheets). Ramp Detail /
Highway Sequence / Intersection Detail lock their
layout from the files (both folders must agree, else a clear error); Highway Log (both formats) pins
`EXPECTED_HEADER` + the Med Wid rule. Verified with
planted-difference fixtures and a real-Excel COM recalc (all SELF-CHECK rows OK). GUI: folder
dropdowns list run folders (baseline defaults to newest ssor-prod) + Browse; saves default to
`output/comparisons/` (`DEFAULT_OUT_DIR`). The v0.12.0 A2 filter lists only folders that actually
contain the chosen report — see [gui.md](gui.md).

---

## 10. Internal mechanics (quick reference)

- **`union_keys(keys_t, keys_n)`** — union in DOCUMENT order, grouped by route: side-A routes in
  side-A order (B-only routes appended in B order), and within each route a `difflib.SequenceMatcher`
  diff-style alignment of the two row sequences. Common keys appear exactly once (first position
  wins — a key can fall outside the aligner's "equal" blocks when one file lists it out of sequence;
  seen in the field: TSMIS printed 059.739 after 059.759 while TSN kept it in order). The Excel MATCH
  lookups pair each union row with both files regardless of position. Per-route alignment keeps the
  matcher fast on consolidated inputs (50k+ rows).
- **Duplicate-key pairing by SOURCE IDENTITY, not file order** (v0.13.1; the objective upgraded
  2026-07-16 per CMP-AUD-220's owner-approved assignment/verdict split) —
  `pair_occurrences_by_similarity(sc, rows_t, rows_n, keys_t, keys_n, has_route, events)`, run after
  `keys_for`, before `union_keys`. When a key legitimately repeats (two segments at the same
  postmile), the occurrence # used to be assigned in file order, so a row that matched the other
  side's SECOND instance was flagged as a difference against its FIRST. This re-numbers the
  occurrence component of duplicate keys WITHIN each `(route, key)` group present on BOTH sides.
  The assignment minimizes the lexicographic **(all-compared-field diff count, summed character
  edit distance, |within-group position gap|)** tuple — context and ditto cells help decide WHICH
  physical occurrences correspond (they distinguish rows), while VERDICTS and every count stay
  asserted-only (`_row_diff_count`; identity may legitimately pair rows that cost MORE asserting
  cells than file order — the count follows the identity, never the reverse). Values ride the SAME
  `_xl_trim`/`_medwid_norm` normalization as `count_diffs`, computed in one `compared_cell` pass
  per candidate (`_pair_cost_components`; `_char_distance` is the Stage-8 oracle's Levenshtein with
  a per-group symmetric memo). The larger side's leftovers get higher, side-unique occurrence
  numbers (stay one-sided). At or below
  `_PAIR_GROUP_CAP=100,000` matrix cells, `_min_cost_pairs` runs a genuinely rectangular Hungarian
  solver and is exact for every group: the objective tuple is encoded order-preservingly into one
  exact integer, then the lexicographically smallest smaller-side assignment vector breaks ties;
  side A owns the tie when dimensions are equal. Above the cap, only deterministic positional
  diagnostics are produced: pairing quality
  is `capped`, completion is partial, and neither a match nor certified differences can be claimed.
  Every duplicate group carries a strict typed trace of original indices, assignment vector,
  selected pairs/costs, dimensions, algorithm, quality, and positional comparison — v2
  (`SOURCE_PAIRING_ALGORITHM`) traces additionally persist per-pair and group objective triples,
  with monotonicity bound to the objective; v1 payloads keep their own invariants, stay readable,
  and serialize byte-identically (None fields omitted). Cancellation is
  polled through matrix construction, Hungarian scans, capped fallback, trace materialization, and
  counting; cancellation returns unknown/empty truth and writes nothing. Workbook lookups use
  injective opaque ordinal tokens rather than flattened route/key text. Locked by
  `check_compare_dupmatch.py`, `check_compare_pairing_policy.py` (incl. the source-identity and
  context-mutation fixtures), and `check_compare_cancellation.py`.
- **`count_diffs`** — the Python mirror: overall totals, per-field diff counts, per-route aggregates
  (consolidated), and the FIRST matched-with-differences row (Spot Check default). The same numbers
  back the run summary AND become the literal cells of the values workbook. Uses `_xl_trim` (Excel
  TRIM semantics) + `_medwid_norm` + the ditto skip.
- **Row links / trust aids (v0.9.0)** — the TSMIS/TSN Row numbers on the Comparison + Only-in sheets
  are HYPERLINK jumps targeting a WHOLE-ROW reference (`"57:57"`) so Excel SELECTS the entire row on
  arrival (temporary highlight, clears on next click) WITHOUT scrolling; a bounded range (`A57:AH57`)
  made Excel scroll to the range's RIGHT edge (COM-measured) — don't regress. `_row_link` computes the
  MATCH THREE times (range start/end + display) so the cell value stays NUMERIC (the COUNT SELF-CHECK
  depends on it). Each data-sheet row carries a "Comparison row" link back in its LEADING column (A).
  GOTCHA: a naive Python/openpyxl reader sees these HYPERLINK columns as BLANK (Excel caches no
  numeric result for HYPERLINK) — they are correct in real Excel (COM-verified). Don't flag them as
  broken when auditing a workbook programmatically.
- **SELF-CHECK** — each Summary headline number recomputed a second independent way (status totals vs
  union count, MATCH-hit counts, Only-in tab row counts, per-field diff sums, Routes-sheet row sums);
  every row must read OK after F9. Typed Detail schemas also check
  `SUM(Report View!Diffs) = 2 × SUM(Comparison!Diffs)`. A CHECK means formulas no longer point at
  the right rows or the Report View's aggregate count is stale. Report View itself remains a
  build-time view until Phase 7; the E2 source/helper snapshots now ensure that even a same-count
  value/field edit invalidates certification and forces `REGENERATE REQUIRED`. SELF-CHECK stays
  live in both flavors.

---

## 11. Constants / symbols cheat-sheet

| Symbol | Value / meaning |
|---|---|
| `_DIFF_MARK` | `" ≠ "` — presentation separator only; never owns equality/count truth |
| `_STATE_MASK_VERSION` | `"CMP_E1_STATE_V1"` — hidden `E`/`D`/`N`/`U` field-state chunks |
| `_MEDWID_HELPER_VERSION` | `"CMP_E1_MW_V1"` — hidden TRIM/CORE/VALID/MASK/CANON formula twin |
| `_EXCEL_FORMULA_LIMIT` | `8_192` — every generated helper/state/display formula is checked |
| `_DITTO_FILL` | `"E4DFEC"` (lavender) — dittoed roadbed cell tint on data sheets |
| `_FORMULA_LEAD` | `("=", "+", "-", "@")` — injection-guard lead chars |
| `_PROGRESS_EVERY` | `2_500` — progress and bounded cancellation cadence on large scans |
| `XL_MAX_ROWS` / `XL_MAX_COLS` | `1_048_576` / `16_384` |
| `_PAIR_GROUP_CAP` | `100_000` — exact rectangular assignment through this product; above it is explicit partial/capped positional diagnosis |
| `_HELPER_KEY_VERSION` | `CMP_E2_KEY_V1` — opaque injective workbook lookup identity |
| `_BUILD_SNAPSHOT_VERSION` | `CMP_E2_SNAPSHOT_V1` — very-hidden source/helper certification snapshot |
| `_DARK` | `"1F3864"` — header band / banner color |

Extending: a new comparison is one `COMPARE_REPORTS` row + module; build a `CompareSchema` and call
`run_compare` — never hand-roll workbook output. See [reports.md](reports.md) ("New comparison
type") for the full recipe.

---

## 12. The comparison matrix (`scripts/matrix.py`) — orchestration ON TOP of cross-env

The **Everything ▸ Comparison matrix** sub-tab (one of two sub-tabs on the Everything pane — the
other is *Refresh & export*) holds the **report × environment comparison matrix**, a thin
orchestration layer over the cross-environment family
([§9c](#9c-cross-environment--compare_envpy-the-folders-family)).
Selecting it goes **full-width** (`body.matrix-wide`: the right activity column shrinks via animated
`flex-grow` to a slim-but-present log + the matrix **config zone**, so the grid fills the screen). The
full-width CSS is written once against shared classes (`.mx-host`/`.mx-pane`/`.mx-gridsection`) and the
by-day matrix (§12b) carries the same classes, so both matrices get identical layout. It remains
**orchestration-only for comparison semantics**: `matrix.py` calls the same manual adapters and
supplies their target-aware output lease; it does not maintain a forked equality model. The
foundation it sits on was audited cell-accurate over the full 6-env batch (2026-06-18; see
[roadmap.md](roadmap.md) closed findings).

- **Rows** = `reports.matrix_rows()` — **all 12 comparable report editions**: Ramp Summary; Ramp
  Detail Excel/PDF; Highway Sequence Excel/PDF; Highway Log Excel/PDF; Intersection Summary;
  Intersection Detail Excel/PDF; and Highway Detail Excel/PDF. **Every cell of
  the matrix is coded — nothing is greyed**: both Intersection reports gained a cross-env adapter
  (`compare_env.INTERSECTION_SUMMARY` AGGREGATE-per-route + `INTERSECTION_DETAIL` flat) in v0.17.0, the
  **HL-PDF** row's cross-env mode is `compare_env.HIGHWAY_LOG_PDF`, and v0.18.0 added the **Intersection
  Detail (PDF)** row with `compare_env.INTERSECTION_DETAIL_PDF` (both PDF rows parse both sides from the
  PDF export). `reports.tsn_matrix_extra_rows()` is empty (every report is a full row).
- **Per-row comparison MODE** (`matrix._row_modes`, picked via a dropdown under each row's name,
  persisted in `settings.matrix_row_modes`):
  - `env` — cross-environment (env vs baseline; `compare_env.<adapter>.compare_folders`). **All 12 rows.**
  - `tsn` — vs TSN, for **every** report (`matrix.tsn_comparator_for(row_key)`): the FLAT/AGGREGATE
    family-specific comparators for all seven TSN datasets and their PDF siblings. Each PDF row
    **shares its Excel sibling's TSN subdir**, so one TSN dataset serves both editions.
  - `vs_excel` — five PDF-to-Excel self-comparators (Highway Log, Intersection Detail, Highway
    Detail, Highway Sequence, Ramp Detail), one on every PDF row. Highway Log Excel also exposes
    the inverse `vs_pdf` placement. These six placements bring the Matrix total to 30.
  A global "set all comparisons to…" (env|tsn) lives in the config zone.
- **build_comparison** dispatches by mode: env → `build_cell_comparison`; tsn/self → consolidate the env's
  store folder(s) on the fly (`consolidate_highway_log` / `consolidate_tsmis_highway_log_pdf` — the PDF
  one gained an **additive** `input_dir`/`out_path`/`converted_dir` override, no-arg behavior unchanged)
  then call the file-vs-file adapter. The **tsn** branch delegates to the shared
  `matrix.consolidate_and_compare_tsn(tsmis_store_dir, tsn_path, out_path, fmt, …)` (v0.16.0) — the SAME
  helper the by-day matrix uses (§12b), so the two matrices differ only by source folder + output path
  (proven byte-identical: same consolidate-to-temp → same compare → same out_path). TSN/self sheets →
  `<dest>/comparisons/tsn/<cell>_<row>_<mode>.xlsx` (cross-env stays
  `<dest>/comparisons/<baseline>/<cell>_<row>.xlsx`) — both **stable, dateless** names.
- **Cells** carry a unified `cmp` state (env mode also keeps a `comparison` alias). Each shows the
  **typed discrepancy count** (diff cells + one-sided), color-coded; plus greyed (mode not coded),
  needs-export, needs-TSN / "consolidate N PDFs", and stale states. Verdict/counts/completion come
  only from a trusted/current comparison sidecar. The cache additionally must have the expected
  output identity, workbook mtime, matching generation ID, and current input fingerprint; absent,
  malformed, foreign, partial, or mismatched records are stale/rebuildable. `matrix_snapshot()` is
  offline and read-only, but strict validation deliberately re-hashes workbook members—it is not a
  pure-stat trust check. Cache files remain `comparisons/<baseline>/_results.json` for env and
  `comparisons/tsn/_tsn_results.json` for tsn/self.
- **Toggles + refresh:** report and **environment-column** show/hide (`matrix_hidden_reports` /
  `matrix_hidden_envs`); refresh per-cell, **per-row**, **per-column**, or all (`cells_to_rebuild(scope,
  row=, env=)`); **cancel** between cells (`MatrixCompareWorker`) + idempotent resume (re-run stale).
  TSN actions: pick a file, or **consolidate dropped PDFs** (`MatrixTsnConsolidateWorker`).
- **Output authority:** Everything comparison jobs acquire a create-only `comparisons` lease. TSN/self
  cells additionally bind the already app-created environment `store` lease; cross-env cells read
  stores without claiming them. Exact target-aware guards route comparison/cache/evidence writes to
  the comparisons lease and persistent consolidation/PDF/outcome/fingerprint writes to the store
  lease, rejecting any linked/replaced descendant. `_tsn_input` remains explicit user-managed input.
  Day and baseline outputs are app-private and never claim the batch destination.
- **Workers** (`gui_worker`): `MatrixCompareWorker` (loops `build_comparison` over `(row, cell, mode)`),
  `MatrixBatchExportWorker` (v0.16.0; loops `_run_matrix_export_step` over `[(spec, src, env)]` for a cell,
  row or column — manifest-free, `workers=N` ⇒ fast; replaced the single-cell `MatrixExportWorker`),
  `MatrixTsnConsolidateWorker`.
- **The matrix job queue (v0.16.0):** matrix actions ENQUEUE Jobs instead of claiming the gate; the
  queue runs one at a time + auto-advances (see [gui.md](gui.md) for the gate/race details). Bridge
  (`gui_api`): `matrix_info` / `set_matrix_baseline` / `set_matrix_report` / `set_matrix_env` /
  `set_matrix_row_mode` / `set_all_matrix_modes` / `set_matrix_tsn_file` / `pick_matrix_tsn_file` /
  `consolidate_matrix_tsn` / `refresh_cell_export` / **`refresh_row_export`** / **`refresh_column_export`** /
  `refresh_cell_comparison` / `recompute_matrix` / `open_cell_comparison` / `open_comparisons_folder` /
  **`set_matrix_fast`** / **`matrix_queue_remove|move|clear`** / **`matrix_stop_all`**.
- **Locked by** `build/check_matrix.py` (enumeration, mtime staleness, stable paths, real env
  orchestration with a planted diff), `build/check_matrix_tsn.py` (mode registry, TSN source detection,
  greyed cells, scoped rebuilds, build guards) and `build/check_matrix_bridge.py` (every bridge method,
  the **queue** — enqueue/auto-advance/reorder/remove/clear/stop-all/no-work-drop/auth-clear/fast — and
  the "a cell export leaves a paused batch intact" invariant), plus
  `build/check_matrix_ownership.py` for dual-lease/link/replacement/evidence routing. **Owed on the work PC:** a LIVE per-cell
  export, queue auto-advance + fast mode under real exports, a full baseline recompute, and the live HL
  TSN / PDF-vs-Excel comparisons over a real store (the underlying compare adapters are already
  golden-locked; the consolidate→compare glue is what's owed).

### 12b. The Compare-tab "vs TSN Matrix" (`scripts/day_matrix.py`, v0.16.0; generalized v0.16.1)

> **0.17.0 plug-in (GENERALIZED):** the matrix lists EVERY report and the dispatch is now
> report-agnostic. To light a report up, the ONLY required step is adding it to
> **`matrix.tsn_comparator_for(row_key)`** (and, for a FLAT report, its consolidator to
> `reports._CONSOLIDATOR_BY_SUBDIR`) — `tsn_supported()` then flips it on in BOTH matrices
> automatically (`_row_modes` + `day_matrix._day_rows` + `available_days` all gate on it).
> `day_matrix.TSN_SUBDIR` is GONE → per-row `tsn_subdir`; `consolidate_and_compare_tsn` is
> keyed on `(row_key, subdir)` and consolidates via `reports.consolidator_for_subdir`. **Live
> today: **all 12 comparable report editions**. Each PDF row shares its family's TSN dataset key
> with its Excel sibling; nothing is greyed.

A **second, manual** matrix under the **Compare** tab — a sibling of the Everything matrix but
day-keyed instead of env-keyed: **rows = report types, columns = exported days you add, each cell =
(report, day) vs TSN**. ONE data source for the whole matrix (default `ssor-prod`); **no
cross-environment, no live re-export** (it compares specific historical exports). **All 12
comparable report editions are live**; nothing is greyed. (Highway Summary is export-only — no comparator yet, so it isn't a matrix
row.) Like `matrix.py`, it NEVER edits the manual compare code — it only orchestrates.

- **Shared engine:** `day_matrix.build_day_cell` delegates to `matrix.consolidate_and_compare_tsn`
  (the same path `build_comparison`'s tsn branch uses, now keyed on `(row_key, subdir)`) over the
  day's run folder `output/<date src-env>/<subdir>/`. The TSN dataset resolves per row's `tsn_subdir`
  via `matrix.tsn_source` → `tsn_library.resolve`. Automatic mode uses the canonical library and
  legacy `<batch_dest>/_tsn_input/<subdir>/` fallbacks. A `settings.matrix_tsn_files` pick is a
  versioned explicit selection: a missing, replaced, or legacy path-only pick blocks the cell until
  it is re-picked or cleared; it never silently falls through to another dataset. The
  by-day matrix shows a PER-ROW TSN picker (named by its report, like the Everything matrix);
  each cell resolves its own report's TSN.
- **Store:** `output/comparisons/tsn-by-day/<date src-env>/<row>_vs_tsn.xlsx` (stable, dateless per
  cell); typed truth is read from the strict generation and cached in that tree's `_results.json`
  under output identity `tsn-by-day`, generation ID, mtime, and input fingerprint. Snapshot
  (`day_matrix_snapshot`) is offline/read-only rather than pure-stat; missing or mismatched trust
  data is stale. `cells_to_rebuild(scope, row=, date=)` skips greyed rows + missing sides.
- **One queue, both matrices:** day compare Jobs carry `which:"day"` and route to
  `DayMatrixCompareWorker` (mirrors `MatrixCompareWorker`); they share the Everything matrix's queue,
  gate, Cancel and queue panel. Bridge: `day_matrix_info` / `set_day_matrix_source` /
  `add_day_matrix_day` / `remove_day_matrix_day` / `set_day_matrix_report` / **`set_day_matrix_formulas`** /
  `build_day_cell` / `rebuild_day_matrix` / `open_day_cell_comparison` / `open_day_comparisons_folder`.
  Settings (all persist across sessions): `day_matrix_source` / `day_matrix_days` / `day_matrix_hidden` /
  **`day_matrix_formulas`** (its OWN live-formulas toggle, independent of the Everything matrix's
  `matrix_formulas`; the TSN file reuses `matrix_tsn_files`).
- **Large-report formulas-twin cap (v0.18.2):** even with a formulas toggle ON, both matrices
  SKIP the live-formulas twin for very large comparisons — over `matrix._FORMULAS_TWIN_MAX_ROWS`
  (12,000) Comparison rows, e.g. Intersection Detail's ~17k. The twin there is millions of live
  formulas and minutes of work on top of the values workbook, which already holds every value. The
  skip is announced (events log + file log) and applies only to the bulk matrix paths (all three
  funnel through `matrix._try_formulas`, which probes the just-written values workbook via
  `_comparison_row_count`); the manual Compare tab still honors its checkboxes, so a single
  explicitly-requested live-formulas comparison is never dropped.
- **Full-width + own config corner (v0.16.x):** selecting the sub-tab calls `applyMatrixWide()` so the
  by-day matrix fills the screen like the Everything matrix; its corner controls (queue, add-day,
  live-formulas, report toggles) live in a mirrored corner `#dayMatrixConfig` (shown via
  `body.matrix-wide.mw-day`), keeping the grid area lean — the per-report TSN pickers sit in the
  row headers (v0.17.0), not the corner. See [gui.md](gui.md).
- **Boundary guard:** `build_day_cell` rejects any `date`/`source` whose combined folder name doesn't
  parse as a real run folder, so neither can traverse out of `output/`.
- **Locked by** `build/check_day_matrix.py` (rows/sources, available-day detection, snapshot + greyed
  cells, scoped rebuild list, build guards, and the gui_api bridge incl. the shared queue). **Owed on
  the work PC:** building two real days vs TSN end-to-end.

### 12c. The Compare-tab "vs Baseline Matrix" (`scripts/baseline_matrix.py`, v0.26.0)

A **third** matrix, a sibling of the vs TSN Matrix with the same day-column mechanics but a
different other side: **rows = the 12 report types, columns = exported days you add, each cell =
(report, day) vs a picked BASELINE copy of the SAME report** — an earlier day's run folder, or the
Export-Everything store (`<batch_dest>/<source>/`) for the same source. It answers "did this report
change since an earlier pull?" — same source, same report, same FORMAT by construction (each row's
`compare_env` adapter reads the report's own subdir on both sides: Excel rows read the Excel
per-route files, PDF rows parse the PDF exports), so an Excel edition can never be diffed against a
PDF baseline.

- **Engine: `compare_folders`, matrix-ified.** No consolidation and NO TSN dataset — each cell is
  `adapter.compare_folders(<day run folder>, <baseline dir>, …, mode="values",
  labels=("<SRC-ENV> <date>", "<SRC-ENV> <bl-date>|(store)"))`, the classic Compare tab's "export
  folders" path (per-route files read straight from both folders), committed atomically by that
  public adapter's `artifact_store.commit_workbook` transaction. The additive
  `labels=` override on `EnvCompare.compare_folders` (v0.26.0; default None = derived labels,
  regression-locked by `check_compare_env_sidelabel`) exists because the store's folder shape
  derives a side label confusingly close to the run-folder one.
- **Baseline identity:** `"day:<date>"` or `"store"` (`parse_baseline`); the picker
  (`baseline_options`) lists the store + every exported day **with how many of the 12 reports each
  holds** — the "which days have an old copy" answer per option; the grid's per-cell
  `missing_side: "baseline"` state answers it per report. The baseline's own day column renders
  `is_baseline` (skipped by `cells_to_rebuild`; building it is rejected).
- **Store:** `output/comparisons/baseline-by-day/<date src-env>/<row>_vs_<token>.xlsx` — the
  baseline token (`store` / the baseline date) is PART of the name, so each baseline's comparisons
  are distinct artifacts and switching baselines never clobbers the other's. Strict typed truth is
  cached in that tree's `_results.json` under `"<date src-env>|<row>|<baseline-id>"`, with output
  identity `baseline-by-day`, generation ID, mtime, and the **two-folder input fingerprint**
  (`fp_folders=(day, baseline)`). BOTH sides are multi-file folders, so a route deleted on either
  one reads the cell stale; missing or untrusted generation/cache data is stale too.
- **One queue, all three matrices:** baseline compare Jobs carry `which:"baseline"` and route to
  `BaselineMatrixCompareWorker` (compare-only mirror of `DayMatrixCompareWorker`). Bridge:
  `baseline_matrix_info` / `set_baseline_matrix_source` / `set_baseline_matrix_baseline` /
  `add_/remove_baseline_matrix_day` / `set_baseline_matrix_report` / `set_baseline_matrix_row_order` /
  `set_baseline_matrix_formulas` / `build_baseline_matrix_cell` / `rebuild_baseline_matrix` /
  `open_baseline_cell_comparison` / `open_baseline_comparisons_folder`. Settings:
  `baseline_matrix_source/days/baseline/hidden/row_order/formulas` (all its OWN, incl. the
  live-formulas toggle; the `set_baseline_matrix_baseline` endpoint validates the id against the
  CURRENT picker options so a stale/hand-edited id can't aim at a non-existent folder).
- **UI:** the "vs Baseline Matrix" sub-tab under Compare (appended beside "vs TSN Matrix");
  full-width via `body.matrix-wide.mw-bl` with its own corner `#baselineMatrixConfig` (queue,
  add-day, live-formulas, report toggles); Source + Baseline selects live in the section head.
  Compare-only: no export actions, no TSN pickers, no consolidated badges, no evidence cameras.
- **Boundary guards:** `build_baseline_cell` rejects a `date`/`source` that doesn't parse as a real
  run folder AND a baseline id that doesn't parse / points at the cell's own day; the id's date
  shape is regex-pinned so a hand-edited settings file can't traverse out of `output/`.
- **Locked by** `build/check_baseline_matrix.py` (identity parsing, picker options, snapshot states
  incl. `is_baseline` + the two-folder fingerprint staleness, scoped rebuilds, guard paths, **one
  REAL `compare_folders` build per baseline kind** — side labels + counts verified off the produced
  workbook — and the gui_api bridge incl. the shared queue). **Owed on the work PC:** two real days
  vs a real baseline end-to-end.

## 13. Visual evidence (`scripts/visual_evidence.py` + the per-report adapters, v0.21.0; Intersection Detail joined in v0.22.0, Highway Log in v0.24.0, Highway Sequence in v0.25.0, Ramp Detail in v0.26.0)

The manual "screenshot the cell in both PDFs and circle it" workflow, automated, as a
**decoration of a finished vs-TSN comparison** — it never changes the comparison's
status/completion/counts, and any evidence failure only logs + adds a summary note.
Five reports so far, each via its own adapter over the shared engine:
`evidence_highway_detail` (district TSN prints), `evidence_intersection_detail` and
`evidence_ramp_detail` (each ONE statewide TSN print), `evidence_highway_log` and
`evidence_highway_sequence` (district TSN prints, with the per-print routing — below).
The HD-specific bullets below apply to the others analogously; the ID/HL/HSL/RD
differences are called out inline. **Ramp Detail's wrinkle is DUAL-ROW discipline**
(v0.26.0): its two rows ride DIFFERENT compared sets — the PDF row's comparison
compares the print-only On/Off + Ramp Type columns the Excel export lacks — so
`erd.load_sides` detects which consolidated workbook it was handed (the
PDF-consolidated carries the "On/Off" header) and `enumerate_diffs` only samples the
columns THAT row's comparison counts (pinned in `check_visual_evidence`).

- **What it produces**, next to the comparison workbook (the `(formulas).xlsx` sibling family):
  `<comparison> (evidence).xlsx` (a Summary sheet + BOTH image layouts embedded, each on its
  own tab — "Evidence (stacked)" for reading, "Evidence (side-by-side)" for pasting; v0.22.1,
  previously stacked-only) and `<comparison> (evidence images)/` with the same examples as
  loose files in both layouts (`*_stacked.png`, `*_pair.png`). Keep-last-good: the images
  render into a temp folder and swap in only after the workbook wrote; a locked-open previous
  set diverts to `.new` with a note instead of failing.
- **Each strip is a FULL-WIDTH page band** (`_crop_window`, v0.26.0): the engine crops the
  record's band (± the vertical context, stretched over the red cell box) across the page's
  whole width. It previously cropped to the adapter's `xspan` — the record's own word extent —
  which CLIPPED whatever printed beyond it: a blank cell's red box (drawn where the value
  WOULD print, e.g. an HSL blank-Description diff) and the neighbor rows' longer text both
  fell outside the image. The gray record box still uses `xspan`; only the crop widened.
  Pinned in `check_visual_evidence`; re-verified on 99 regenerated examples (HSL Excel/PDF +
  RD Excel/PDF — both page orientations, district + statewide TSN prints).
- **Quote-characters clarifier** (`_quote_note`, v0.26.1): when a sampled pair's two values differ
  ONLY in quote characters (`''` doubled apostrophes vs `"` a quotation mark vs `'`), they
  print near-identically and the pair header reads as a false positive. The header gains a
  third, dark-red line naming both sides' characters in words ("TSMIS prints '' (two
  apostrophes) where TSN prints \" (a quotation mark)"), and the workbook caption carries the
  same note — the difference is REAL (the systems store different characters); the tool now
  says so instead of looking broken. Censused trigger: Intersection Detail KER 046 @ 50.904,
  the single statewide instance (both systems otherwise share the `''X''` convention — TSN 62
  rows / TSMIS 61, near-identical contexts). Every other pair renders without the line. Pinned
  in `check_visual_evidence`; the ID Notes sheet documents that quotes compare literally.
- **Sampling:** for every differing column, up to N (user setting, 1–10, default 2) random
  example rows across random routes, keys restricted to UNIQUE-per-route on both sides so a
  highlight is THE row. Each run logs its sample seed.
- **The trust contract:** an example is only used when the value parsed back OUT of each PDF —
  normalized with the comparator's OWN projections — equals the value the comparison compared.
  Under unchanged source files, each rendered pair therefore doubles as an end-to-end spot-check
  of the comparison at that cell. CMP-AUD-112 remains open for Phase 7: parse-time records and the
  later raster reopen are not yet bound to one immutable PDF generation. Failed candidates are
  skipped with a per-column reason (recorded in the workbook), e.g. the TSMIS PDF/Excel
  site-build skew or a TSN reference-date skew.
- **Sources:** TSMIS side = the per-route **(PDF)-edition** export of the report (the Everything
  matrix resolves the row's cell store, the by-day matrix that day's `*_pdf/` run folder);
  TSN side = the prints in the report's `tsn_library/<report>/pdf/` folder — Highway Detail
  takes the 12 **district prints** (the district is read from each file's own DIST-CNTY-ROUTE
  header), Intersection Detail the ONE **statewide print** (district/county read per record
  from `LOCATION`); filenames never matter. **Highway Log and Highway Sequence are the
  raw-sourced exceptions (v0.24.0 / v0.25.0):** their TSN libraries are BUILT from the
  district prints, so evidence reads the SAME files from `tsn_library/highway_log/raw/` /
  `…/highway_sequence/raw/` (`visual_evidence._TSN_PDFS_IN_RAW`; availability
  reports `source: "raw"`) — no duplicate pdf/ drop, and a user with a working vs-TSN
  comparison for those reports already has evidence ready. The pdf/ folders are **created + hinted by
  `tsn_library.ensure_layout`** (v0.21.1 — driven by the catalog's `TsnEntry.evidence_pdfs`
  flag; v0.21.0 never created it, so an updated install had nowhere to drop the prints), and
  re-entering a matrix tab re-pushes the state so the toggle re-probes and un-greys without a
  restart. **Ramp Detail follows the ID statewide-print pattern** (v0.26.0): ONE TASAS print in
  `tsn_library/ramp_detail/pdf/`, district/county read per record from LOCATION. The
  **normalized TSN library appends TSN District/County sidecar columns** (HD since
  its v2, ID since its v3, RD since its v3 — `tsn_load_*.SIDECAR_HEADER`) so evidence can find
  a row's print; `_normalized_row` slices to the shared width, so the comparison itself never
  sees them (a pre-sidecar library is refused with a rebuild hint, and the D2 version bump
  rebuilds it automatically).
- **Locators:** each TSMIS locator mirrors its PDF consolidator's parse step for step while
  capturing positions — **keep them in LOCKSTEP** (HD: per-page windows, row groups, the
  postmile test, the date-token guard, cross-page carry, fallback-grid/straddling records
  rejected; ID: the document grids from both band shapes, the padded-postmile rowA test, the
  integer-column-1 rowB pairing, page-straddling records rejected; HL: the zebra-rect per-page
  windows with carry-forward — carried-geometry records rejected as approximate — the
  header-bottom cutoff, the col0-right data test, and Description captured from its own
  follow-on lines, page-split descriptions rejected; HSL: the header-anchored per-page
  boundaries, the trailer hard-stop, the PM / PM-less data tests, and wrapped-Description
  fragments attached + hyphen-aware-joined exactly like its consolidator — the evidence
  classifier is the word-object-keeping TWIN of `chslp._classify_words`, pinned identical
  in `check_visual_evidence`; RD: the same header-anchored per-page boundaries as ITS
  consolidator, re-using `rdpdf._page_header`/`_classify_words` directly with a
  word-capturing window loop alongside). The TSN locators differ by
  print style: HD parses the TASAS district print line-anchored with the two-line REGEXES
  (word positions kept; an optional group that didn't print boxes the gap between neighbors;
  cross-checked ≥99.9% against the statewide extract); ID rides the statewide print's FIXED
  monospace column template — per-field x-windows with MAX-OVERLAP word assignment (a
  `Y`-flagged date leaning into its neighbor stays in its date window; the flag is stripped
  from the value), LOCATION as one token-split window, and a BLANK cell boxes its template
  window. The ID print is indexed ONCE per file (cached on size+mtime) inside
  `district_index`, so the engine's per-district `locate_tsn` calls are dictionary lookups —
  the engine stayed untouched. Validated statewide: 16,584/16,584 records, 30/32 fields 100.00%
  parse-back vs the raw extract (the rest are print truncations the verifier skips). RD's TSN
  locator is the same statewide-print pattern one size smaller: single-line records on a fixed
  template (header anchors pixel-identical across the 500 pages; windows censused on 415
  order-assignable full rows, 400/400 sampled records value-identical to the raw extract;
  long Descriptions TRUNCATE — the known skip-class), indexed once per file. HL's TSN
  locator rides the OTM52010 print's fixed document-wide column windows
  (`consolidate_tsn_highway_log.COLUMN_WINDOWS`), LOCKSTEP with that parser's walk (district/
  group headers, totals close, the description x-band + totals-pattern guards, `', '` joins).
- **Per-print routing (Highway Log v0.24.0; Highway Sequence v0.25.0):** those comparisons'
  columns carry NO
  county/district, so a diff row can't be mapped to one district print up front (HD's sidecar
  trick doesn't apply, and the comparator/library shapes stay untouched). The adapter owns the
  fan-out instead: every example carries the SENTINEL district `""`, `district_index` returns
  one `{"": <folder>}` entry, and `locate_tsn` receives the FOLDER — scanning every district
  print route-filtered, tagging each record with its source path + the district/county it was
  printed under (HL: the print's district/group headers; HSL: the "DIST NN RTE NNN" group
  headers + the county carried from the data lines). `_try_example` prefers a record's own
  `src`/`dist`/`cnty` over the district
  index (additive; HD/ID records don't carry them and behave exactly as before), and the
  engine's own uniqueness gate turns any cross-print key collision into a skipped example —
  ambiguity can only cost an example, never mislabel one. Diffs are judged by
  `compare_core.compared_cell` itself, so the `+`-run **ditto** cells (non-asserting by
  schema, HL), the **context fields** (HG/City/Distance, HSL) and the Med Wid normalization
  can never enumerate as examples. Costs a full
  route-filtered scan of the district prints per run (minutes, like the TSN consolidation) —
  the district-parse cache stays on the roadmap alongside HD's.
- **Evidence UX (v0.24.0):** the toggle on both matrix pages lists per report what it will
  do — a ✓ "will generate (N TSN prints)" line, a ○ "needs its TSN PDFs in <dir>" line, and
  one line naming the rows with **no evidence support** (`_evidence_view` derives them from
  `reports.matrix_rows()` × `visual_evidence.capable`, one entry per report family, pushed as
  `evidence.unsupported`). Supported rows also carry a small camera badge on their row header
  in both matrices (lit = prints in place, dimmed = tooltip names the drop folder).
- **Wiring:** ONE hook in `matrix.consolidate_and_compare_tsn(evidence_opts=)` covers both
  matrices; callers resolve their own store layout through `matrix.evidence_opts_for` (the shared
  gate — toggle on + `visual_evidence.capable(row_key)`). The user toggle is ONE persisted pair
  (`evidence_images` + `evidence_examples`, endpoints `set_evidence_images` /
  `set_evidence_examples`) surfaced under *Comparison output* on BOTH matrix pages, greyed with a
  drop-hint until at least one report's TSN prints are in place —
  `visual_evidence.availability()` rides the state push and reports **per-report** folders
  (`reports: [{key,label,tsn_pdfs,dir}]` + the `row_reports` row→report map), so the hint names
  exactly which report still needs its prints while the other keeps working. The render stack
  (Pillow + pypdfium2) SHIPS since v0.21.0 — see [build-and-release.md](build-and-release.md).
- **On-demand per-cell evidence (v0.23.0):** a camera action on every BUILT, FRESH vs-TSN cell
  of an evidence-capable row (both matrices) runs `matrix.run_evidence_only` — images for the
  EXISTING comparison, no consolidation, no compare, toggle-independent (endpoints
  `matrix_evidence_cell` / `day_matrix_evidence_cell` → an `evidence` queue job →
  `MatrixEvidenceWorker`; resolvers `matrix.evidence_for_cell` /
  `day_matrix.evidence_for_day_cell` mirror the build paths' path resolution but do NOT heal
  the TSN library — a heal would rebuild it newer than the comparison and the gate below would
  then rightly refuse). Before rendering, the gate requires a trusted, complete published
  comparison generation and current consolidated/TSN freshness. After rendering it re-reads the
  comparison and requires the same generation ID, refusing success if it changed. This blocks
  known-stale inputs and comparison replacement during the render, but it does not yet bind every
  source/PDF byte or publish workbook+images+retirement as one immutable transaction
  (CMP-AUD-106/109/112 remain Phase 7). The JS side hides the camera on stale cells and on rows
  whose report has no TSN prints (`evidenceActionInfo`).
- **Publication safety:** evidence source/caption cells use `set_safe_literal_cell`, including
  formula leads and every Excel error token. Workbook/image sets use unpredictable identity-bound
  temps, quarantines, and fallbacks; source aliases and target-aware Everything leases are checked
  before writes, swaps, rollback, and cleanup. Uncertain replacements are retained, never removed.
- **Locked by** `build/check_visual_evidence.py` (all five evidence families, source routing,
  transaction/lease rollback, the
  caller gate + the on-demand freshness gate (every refusal message + the pass-through),
  the LOCKSTEP pins, the HD TSN print regexes + the ID fixed-window/max-overlap/
  flag-strip/LOC-tokenizer behavior, span→box math, verification projections, unique-key diff
  enumeration — the ID one mirroring compare_core's cell trim so whitespace-only differences
  never enumerate — and the TSN loaders' sidecar contracts (`tsn_rows_with_dcr` row-identical
  to the locked raw loaders), `build/check_evidence_literal_cells.py`, and
  `build/check_matrix_ownership.py`; the frozen self-test proves the render stack itself.
