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

Inputs arrive as ROWS — the CALLER (each comparison module) owns file loading + shape
validation. Two shapes:

- **per-route**: `[key, f1..fn]`, `has_route=False`.
- **consolidated**: `[route, key, f1..fn]`, `has_route=True`.

Entry point: `run_compare(sc, rows_t, rows_n, has_route, out_path, *, events, confirm_overwrite,
mode, name_a, name_b, warnings)` → `ConsolidateResult` (the same contract the consolidators
return, so GUI/console drive it identically).

The three comparison families (see [§9](#9-the-three-comparison-families)) are all `run_compare`
callers with different schemas.

---

## 2. The regression lock (DO NOT change formula/label text casually)

`compare_core` is **regression-locked**: any change to its formula or label text must be proven
**cell-for-cell identical** for the TSMIS-vs-TSN flavor before shipping.

> **v0.18.0 held the lock.** The structural overhaul left `compare_core.py`
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

**Approved Route-1 sample counts** (per-route TSMIS-vs-TSN, format locked to these — never
regress them): **299 both / 18 (TSMIS-only) / 69 (TSN-only) / 221 diff rows / 969 diff cells**.
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

**The opt-in rule that keeps the lock intact:** every Highway-Log-only or report-specific
behavior is a `CompareSchema` field that defaults to the no-op original. When the flag is OFF
(every non-HL comparison), the equality formula, Spot Check verdict, Python mirrors, helper keys
and MATCH lookups are **byte-identical** to the locked output. This is how the engine gained
ditto/roadbed/legend behaviors without re-running approval on the other comparisons. The
in-repo golden checks (`build/check_compare_*.py`) lock the engine on synthetic fixtures; see
[verification-and-testing.md](verification-and-testing.md).

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
  sheets, NEVER reading the Comparison's answer) and an `Agree?` OK/CHECK column. Opens pre-set to
  `first_diff_row` (the first matched row with differences). Stays LIVE in both flavors.
- **Comparison** — one row per `(route,) key + occurrence` in document order. Matched cells show
  the matched value; differing cells show `a ≠ b` in red (the `_DIFF_MARK = " ≠ "` is the ONLY
  place that string appears — CF, COUNTIFs, the Diffs count all key on it). One-sided rows tinted
  yellow (A-only) / blue (B-only) and show that side's own values.
- **Only in <A>** / **Only in <B>** — every one-sided union row in union order, full field data
  pulled live from that system's data sheet. Consolidated mode adds a "Missing from <other>"
  column ("entire route" — tinted — vs "this <noun> only"). NOTE: one-sided rows have ALWAYS been
  in the Comparison sheet too (via `union_keys`' single-side emit); these tabs exist because
  65k-row sheets buried them.
- **Routes** (consolidated only) — per-route coverage: Both / A-only / B-only with live per-route
  row / matched / with-diffs / differing-cell counts.
- **<A>** / **<B>** — the two inputs copied in, with a leading "Comparison row" back-link column
  (A) and a live "Key (helper)" column at the end. Route/key columns stay in their input
  position.

### Two flavors via `mode=` ("formulas" | "values" | "both")

`run_compare(..., mode=...)` — the GUI Compare tab has two checkboxes (both ticked by default;
≥1 required). The mirror that powers the run summary (`count_diffs` / `_field_value`) ALSO
produces the literal cells of the values workbook, so the two flavors **can never disagree**.

| | formulas | values |
|---|---|---|
| cells | every number is a LIVE Excel formula (lookup keys, statuses, per-field diffs, summary counts); edit a data cell ⇒ report recalculates | the same sheets / CF / links, but the bulk is plain computed RESULTS |
| consolidated calc | ~2M formula cells; ships in **manual calculation mode** (`calcMode="manual"`, `calcOnSave=False`, `fullCalcOnLoad=False`); opens instantly showing blank/0, user presses F9 once, then saves (per-route files stay automatic) | automatic calc, no F9 banner |
| size | larger | ~⅓ the size; opens instantly |
| live in values flavor | n/a | ONLY the Spot Check sheet + the SELF-CHECK rows stay live (they recount the literal sheets) |

`mode="both"` writes the picked name (formulas) + `<name> (values).xlsx` next to it.

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
`1..`, exactly like the live helper column on the data sheets. The key sits at
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

Every comparison LEADS with a one-line answer. `summary_lines[0]` is
`✓ EVERYTHING MATCHES …` / `✗ DIFFERENCES FOUND …` / `⚠ COULD NOT COMPARE EVERYTHING …`.
`ConsolidateResult.verdict` is `"match"` / `"diff"` (consolidators leave it `None`); the GUI keys a
green/amber result dialog on it. The workbook's Summary carries the same verdict as a big banner
cell right under the title (B3, or B4 under the manual-calc F9 banner) — a LIVE formula in the
formulas flavor (CF green/red keyed on the `✓`/`✗` first character), a literal in the values
flavor. **Match ⟺ zero differing cells AND zero one-sided rows.**

### Incompleteness contract (v0.11.0)

An unreadable input is NEVER silently dropped — `run_compare(warnings=…)` keeps `status="ok"` but
forces `verdict="diff"` (a clean match can't be certified) and leads `summary_lines[0]` with the
literal **`⚠ COULD NOT COMPARE EVERYTHING`**. The in-workbook Summary banner uses `✗` so the
existing red CF still applies (no new CF rule ⇒ the no-warnings path stays byte-identical); the GUI
result dialog keys on the `⚠` prefix to title it "Comparison incomplete". The skipped files are
listed in the notes (first 20, then "…and N more"). The loaders feed `warnings` from skipped files
(e.g. `compare_env._load_xlsx_side` / `_load_ramp_summary_side` return a `skipped` list of
"<side> <file>: <reason>" strings). **Match ⟺ zero diff cells AND zero one-sided rows AND zero
skipped inputs.**

### Write-path safety (v0.11.0)

- **Formula-injection guard.** Free text beginning `= + - @` (`_FORMULA_LEAD`) would be interpreted
  by Excel as a formula (the classic CSV/XLSX injection vector — a Description like
  `=cmd|'/C calc'!A1` runs on open). `_styled(..., guard=True)` + `is_formula_injection` force such
  a value to a STRING cell (`data_type="s"`) so Excel shows it verbatim. The value is kept
  byte-for-byte (only the cell TYPE changes), so equal sides still compare equal and clean data is
  unchanged — the regression lock is unaffected. Applied to raw input cells on the data sheets, the
  key cells, the helper key, the Comparison/Only-in/Routes literal id cells — never to the engine's
  own `=formula`/HYPERLINK cells. The same guard is in the openpyxl consolidators. Scope confirmed
  by source verification: the free-text Description columns (ramp detail / HSL / highway log /
  intersection detail) re-emitted raw.
- **Load-time canonicalization.** `normalize_value` renders dates/datetimes/times to a fixed ISO
  string at LOAD time, so the engine only ever sees text and the two flavors can't disagree (Excel's
  TRIM of a live date is locale/number-format dependent and would diverge from Python's
  `str(datetime)`). Callers (the loaders) apply it per cell.
- **Limit / collision guards.** `excel_limit_error` checks before writing: a workbook past
  `XL_MAX_ROWS=1,048,576` or `XL_MAX_COLS=16,384` fails cleanly (with guidance to compare a smaller
  scope) instead of openpyxl raising mid-write (losing the partial file) or silently dropping
  columns. `run_compare` also rejects, before writing, any sheet name over 31 chars and any
  side-name⇄fixed-sheet-name collision (a side literally named `Summary`/`Comparison`/`Routes`/
  `Only in …` would collide).

### Med Wid flavor-parity (dormant gap)

The two flavors normalize Med Wid differently: the **values** flavor uses
`compare_core._medwid_norm` (a Python regex), while the **formulas** flavor relies on Excel's
`VALUE()` (`_medwid_ref`). Excel `VALUE()` accepts MORE strings as numeric than the Python regex
(internal space, leading sign, scientific notation, a bare/trailing decimal point), so an exotic
Med Wid value *could* make the two flavors disagree. **DORMANT:** every real Med Wid value across
the consolidated TSMIS/TSN files is a clean `<digits><letter>` code or `"+++"` (parity-proven over
**554k+** COM-recalc'd cells), so the current deliverable is accurate. Decision (2026-06-16):
leave dormant; revisit only if a Med Wid value ever contains those characters. Tracked in
[roadmap.md](roadmap.md).

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

### 9b. Highway Log (PDF) — `compare_highway_log_pdf.py` (`"files"`, group `highway_log`)

Two file-vs-file comparisons (v0.14.0) that sidestep the buggy vendor Excel by sourcing the TSMIS
side from the **PDF** consolidation. Both reuse `compare_highway_log._load_input` (any 31-column
Highway Log workbook, per-route or consolidated) and `replace(_hl._SCHEMA, …)` to override ONLY the
two side labels + notes (engine text untouched → regression lock intact). Each carries
`file_a_label` / `file_b_label` so the GUI's two file pickers and the data sheets are named for the
actual sides (not hard-coded TSMIS/TSN).

| instance | sides | purpose |
|---|---|---|
| `TSMIS_PDF_VS_TSN` | "TSMIS (PDF)" vs "TSN (PDF)" | accurate replacement for 9a — BOTH sides from PDFs, so the PDF-vs-PDF nature is explicit and the vendor Excel bug never enters |
| `TSMIS_PDF_VS_EXCEL` | "TSMIS (PDF)" vs "TSMIS (Excel)" | diffs PDF-parsed data against the vendor Excel of the SAME report to pinpoint the export's errors |

### 9c. TSMIS vs TSN Ramp Detail — `compare_ramp_detail_tsn.py` (`"files"`, group `tsn`)

The **reference v0.17.0 vs-TSN comparator** (the recipe the other reports follow). Both sides are
XLSX but in DIFFERENT shapes, so each side has its own loader projecting to ONE shared header keyed
on **PM**: the TSMIS side reads the **consolidated** Ramp Detail workbook **by POSITION** (its
header row is column-shifted — the City Code / R/U / Description labels sit right of their values);
the TSN side reads the statewide raw `Sheet 1` (18 DB columns) or the library's normalized workbook,
taking the route from `LOCATION` ("01-DN-101"→"101"). Normalization: PM zero-pad → one canon,
`Date of Record` → ISO, Description drops the TSMIS leading `"<route>/"` prefix; TSN `POP` maps to
TSMIS `R/U`. `_SCHEMA` sets `key_field=PM`, `date_fields=("Date of Record",)`, and
**`context_fields=("Ramp Name","On/Off","Ramp Type","ADT")`** — the TSN-only DB columns, shown for
reference but never counted (see [§3](#3-compareschema-the-parameterization)). Reconciled + locked
on the 6.19 statewide set (approved canary in [tsn-parsers.md](tsn-parsers.md): 15,211 both / 902
diff cells / 0 context-column diffs; TSN normalized 15,410 rows == the Ramp Summary total). The TSN
side is normalized once into the canonical TSN library via `tsn_load_ramp_detail.build_into`.

Project premise CONFIRMED on real data: Excel-vs-TSN has ~4,280 MORE diffs than PDF-vs-TSN — those
extra diffs are the Excel's dropped-geometry artifacts leaking in (98.9% dropped-value blanks), so
sourcing TSMIS from the PDF gives a CLEANER TSMIS-vs-TSN comparison. PDF-vs-Excel at full scale
(self-built from raw, complete Excel) = **49,699/50,455 rows fully identical (98.5%), 5,370 diff
cells / 756 rows, zero missing routes** — of which 90.5% (4,858) = Excel BLANKED roadbed/median
geometry cells (the localized Excel bug). The Excel export drops rows + whole roadbed-column blocks
(route 041: 72 rows + ~4,500 blanked cells; route 046: drops rows in dense postmile bands), EXPANDS
`+`/`++` dittos into values, PADS Descriptions with trailing tabs, and SHIFTS/mis-attributes
descriptions. 21 routes are TSN-only (not in the 252 TSMIS PDFs). LESSON: always consolidate the
Excel side from raw yourself — a stale/partial pre-existing consolidated workbook (missing 25
routes) inflated PDF-vs-Excel to 22,210 diffs.

### 9d. TSMIS vs TSN Ramp Summary — `compare_ramp_summary_tsn.py` (`"files"`, group `tsn`, **AGGREGATE**)

The first **AGGREGATE** vs-TSN comparator — the recipe for the two Summary reports. Unlike the
FLAT comparators (per-PM rows), each side reduces to ONE statewide `{category: count}` table, so
the comparison runs with **`has_route=False`**, `header=[Category, Count]`, `key_field=0` (the
category is the key, the count is the single field). The TSMIS loader **sums** the consolidated
Ramp Summary workbook's per-route sheet column-by-column (the same totals its live "Combined"
sheet shows); the TSN loader parses the **statewide PDF** directly (reusing
`consolidate_ramp_summary`'s geometry helpers — see [tsn-parsers.md](tsn-parsers.md)) or reads the
library's normalized `Category|Count` workbook (`tsn_load_ramp_summary.build_into`). The canonical
category list (the **16-ramp-type superset** incl. the TSN-only **P/V** "Dummy" classes + the
grand Total) lives in `summary_layout.RAMP_SUMMARY_SPEC`, shared with the familiar sheet. A
**"Summary by Category"** familiar-layout sheet (TSN sections/labels/order; *Category | TSMIS |
TSN | Δ*) is appended via `extra_sheet_writer=summary_layout.make_extra_sheet_writer(SPEC)`.
P/V are TSN-only → TSMIS contributes 0 → they read as `0 ≠ 122` / `0 ≠ 81` (both-sided);
`Ramp Points w/out linework` is a TSMIS-only diagnostic emitted on the TSMIS side only (lands in
*Only in TSMIS* + the footer). Approved canary in [tsn-parsers.md](tsn-parsers.md): **31 categories
both, 1 only-TSMIS, 27 diff cells, 4 identical; TSMIS 15215 vs TSN 15410**. Live in both matrices.

### 9e. TSMIS vs TSN Intersection Summary — `compare_intersection_summary_tsn.py` (AGGREGATE, ONE-SIDED divergence)

The AGGREGATE recipe applied to the intersection taxonomy. The category schema (`summary_layout.
INTERSECTION_SUMMARY_SPEC`, 11 blocks, **66 categories** after the v0.17.8 signal fold) is the union
of both systems' taxonomies; the spec-driven block-walk `summary_layout.counts_from_rows` maps a
(count, code-text) stream to `{slug: count}` and is shared by BOTH sides (the TSMIS consolidator AND
the TSN parser) so they can't drift. The TSN side is a **3-column statewide PDF** — split into
left/middle/right x-bands, each block-walked independently. **The v0.17.8 §9b fold** brought CONTROL
TYPES into line with the Detail: TSN's legacy signal sub-types **J–P fold into the single
`S - SIGNALIZED` category**, so Signalized now compares on **both** sides and **no TSN-only categories
remain** (`_IS_TSN_ONLY == ()`). The genuinely TSMIS-only codes stay one-sided — CONTROL **O/Q/R** and
INTERSECTION TYPE **Roundabout/Circular/Midblock** — driven by `Cat.sides` ("both" | "tsmis" | "tsn")
+ `SummarySpec.categories_for(side)`. Keyed on `(block, code-letter)` because TSMIS reworded labels.
Note the distinction from §9f: the **Summary keeps the category LABEL "S - SIGNALIZED"**, while the
Detail's per-cell control value renders as the code **`S`**. Canary in [tsn-parsers.md](tsn-parsers.md):
**66 categories — 58 both / 8 only-TSMIS / 0 only-TSN; TSMIS 16473 vs TSN 16626**. Live in both matrices.

### 9f. TSMIS vs TSN Intersection Detail — `compare_intersection_detail_tsn.py` (FLAT, route+PM)

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

### 9f-2. TSMIS vs TSN Highway Detail — `compare_highway_detail_tsn.py` (FLAT, route + canonical PM; v0.20.0)

The Intersection Detail FLAT recipe applied to Highway Detail, reconciled against the full statewide
dev bundle (252 TSMIS routes / 51,243 rows vs the 60,083-row `TSAR - HIGHWAY DETAIL` extract; 46,847
rows matched in the reconciliation study). TSMIS side = the consolidated workbook read **by position**
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

The FLAT recipe with a **county-relative key** — the direct analog of the Highway Log comparison (a
postmile-sequence listing with the same "TSN lists more segment breaks, TSMIS more realignment markers"
one-sided behavior). TSMIS side = the consolidated `Highway Locations` workbook read **by position**
(two unnamed header columns hold a postmile prefix and an equate suffix); the canonical postmile
**re-glues** prefix+PM+suffix. TSN side = a normalized workbook from `consolidate_tsn_highway_sequence`
(word-level PDF parse of the 12 district `Highway Locations` PDFs; the 2-char `G/RF` flag splits into
HG+FT; `EQUATES TO` annotation lines are emitted so they pair with TSMIS `END R REALIGNMENT` rows).
**California postmiles are county-relative** (a route restarts at `000.000` per county), so the key is
composited via `key_normalizer` → `"COUNTY POSTMILE"` (County stays its own visible column;
`pair_occurrences_by_similarity` handles landmarks still sharing a county+PM). Reconciliations, all
locked: **(1)** County trailing-period strip (`LA.`→`LA` etc. — else whole counties go one-sided);
**(2)** Description strips the TSMIS `^\d{1,3}[A-Z]?/` route prefix + collapses whitespace; **(3)**
`context_fields` = **HG** (TSMIS blanks it for whole counties), **City** (TSN tags it far more
aggressively), **Distance To Next Point** (measured to each system's OWN next listed point — a listing-
granularity artifact, not a disagreement) — shown, never counted; **FT + Description are compared**, with a
**Notes sheet** (`legend_writer`) indicating all of this. Canary in [tsn-parsers.md](tsn-parsers.md):
**57,070 both / 3,369 only-TSMIS / 12,688 only-TSN; 5,538 counted diffs (FT 699 + Description 4,839; 0 in
context); 60,439 vs 69,758 rows; 242 routes both**. Live in both matrices — completing all 6 reports + HL-PDF.

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

`EnvCompare` has three shapes: the **flat** path (Ramp Detail / Highway Sequence / Highway Log /
Intersection Detail — read the per-route sheet rows in consolidated shape); a **flat, PDF-sourced**
variant (`flat_pdf_loader` — Highway Log (PDF) **and Intersection Detail (PDF)**, which parse each
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
- **Duplicate-key pairing by SIMILARITY, not file order** (v0.13.1) —
  `pair_occurrences_by_similarity(sc, rows_t, rows_n, keys_t, keys_n, has_route, events)`, run after
  `keys_for`, before `union_keys`. When a key legitimately repeats (two segments at the same
  postmile), the occurrence # used to be assigned in file order, so a row that matched the other
  side's SECOND instance was flagged as a difference against its FIRST. This re-numbers the
  occurrence component of duplicate keys WITHIN each `(route, key)` group present on BOTH sides so
  the most-alike rows (fewest differing fields, via the SAME `_xl_trim`/`_medwid_norm`/ditto rules as
  `count_diffs` — `_row_diff_count`) share an occurrence #; the larger side's leftovers get higher,
  side-unique occurrence numbers (stay one-sided). `_min_cost_pairs` does an exact min-total-cost 1:1
  assignment by permutation search with pruning up to `_PAIR_EXACT_PERMS=5040` (7!), greedy above;
  groups whose product exceeds `_PAIR_GROUP_CAP=100,000` keep file order. The optimal assignment's
  total ≤ any positional one, so it can ONLY REMOVE phantom diffs, never add one. Deterministic,
  file-order tie-break (lexicographic search tries the positional assignment first). The KEY/identity
  is unchanged — only the duplicate pairing — and the non-duplicate path is byte-identical (the
  approved Route-1 969 is untouched). On real consolidated data it cleared ~3,600 phantom diff cells.
  Occurrence is a build-time LITERAL every sheet MATCHes on, so the reassignment flows through both
  flavors with no formula change. Locked by `build/check_compare_dupmatch.py`.
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
  every row must read OK after F9. A CHECK means formulas no longer point at the right rows. Stays
  live in BOTH flavors.

---

## 11. Constants / symbols cheat-sheet

| Symbol | Value / meaning |
|---|---|
| `_DIFF_MARK` | `" ≠ "` — the ONLY marker of a differing cell; CF / COUNTIFs / Diffs count all key on it |
| `_DITTO_FILL` | `"E4DFEC"` (lavender) — dittoed roadbed cell tint on data sheets |
| `_FORMULA_LEAD` | `("=", "+", "-", "@")` — injection-guard lead chars |
| `_PROGRESS_EVERY` | `10_000` — log + cancel-check cadence on big workbooks |
| `XL_MAX_ROWS` / `XL_MAX_COLS` | `1_048_576` / `16_384` |
| `_PAIR_GROUP_CAP` | `100_000` — `len_t*len_n` above which duplicate groups keep file order |
| `_PAIR_EXACT_PERMS` | `5040` (7!) — exact assignment cap, greedy above |
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
by-day matrix (§12b) carries the same classes, so both matrices get identical layout. It is
strictly **ADDITIVE / orchestration-only**: `matrix.py` NEVER edits the manual comparison code
(`compare_core`, `compare_env`, `compare_highway_log`, `compare_highway_log_pdf`) — it just CALLS those
adapters. The foundation it sits on was audited cell-accurate over the full 6-env batch (2026-06-18; see
[roadmap.md](roadmap.md) closed findings).

- **Rows** = `reports.matrix_rows()` — **all 8 reports**: Ramp Summary, Ramp Detail, Highway Sequence,
  **Highway Log (Excel)**, **Intersection Summary**, **Intersection Detail**, **Highway Log (PDF)**, and
  **Intersection Detail (PDF)** (the two reports with PDF editions are two rows each, keyed by subdir
  `highway_log`/`highway_log_pdf` and `intersection_detail`/`intersection_detail_pdf`). **Every cell of
  the matrix is coded — nothing is greyed**: both Intersection reports gained a cross-env adapter
  (`compare_env.INTERSECTION_SUMMARY` AGGREGATE-per-route + `INTERSECTION_DETAIL` flat) in v0.17.0, the
  **HL-PDF** row's cross-env mode is `compare_env.HIGHWAY_LOG_PDF`, and v0.18.0 added the **Intersection
  Detail (PDF)** row with `compare_env.INTERSECTION_DETAIL_PDF` (both PDF rows parse both sides from the
  PDF export). `reports.tsn_matrix_extra_rows()` is empty (every report is a full row).
- **Per-row comparison MODE** (`matrix._row_modes`, picked via a dropdown under each row's name,
  persisted in `settings.matrix_row_modes`):
  - `env` — cross-environment (env vs baseline; `compare_env.<adapter>.compare_folders`). **All 8 rows.**
  - `tsn` — vs TSN, for **every** report (`matrix.tsn_comparator_for(row_key)`): the FLAT/AGGREGATE
    `compare_*_tsn` comparators for RS/RD/HSL/Int-Summary/Int-Detail, `compare_highway_log` for HL-Excel,
    and the PDF-sourced `compare_highway_log_pdf.TSMIS_PDF_VS_TSN` / `compare_intersection_detail_pdf.TSMIS_PDF_VS_TSN`
    for the two PDF rows. Each PDF row **shares its Excel sibling's TSN subdir** (`highway_log_pdf`→`highway_log`,
    `intersection_detail_pdf`→`intersection_detail`), so one TSN dataset serves both rows.
  - `vs_excel` — the two **PDF-vs-Excel self-checks** (`compare_highway_log_pdf.TSMIS_PDF_VS_EXCEL` and
    `compare_intersection_detail_pdf.TSMIS_PDF_VS_EXCEL`), available only on the two PDF-edition rows.
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
  **discrepancy count** (diff cells + one-sided), color-coded; plus greyed (mode not coded), needs-export,
  needs-TSN / "consolidate N PDFs", and stale states. **Freshness** is pure-filesystem
  (`report_library.cell_ages` mtimes vs the comparison mtime); counts come from the produced VALUES
  workbook and are cached (`comparisons/<baseline>/_results.json` for env, `comparisons/tsn/_tsn_results.json`
  for tsn/self), so `matrix_snapshot()` is a pure offline read.
- **Toggles + refresh:** report and **environment-column** show/hide (`matrix_hidden_reports` /
  `matrix_hidden_envs`); refresh per-cell, **per-row**, **per-column**, or all (`cells_to_rebuild(scope,
  row=, env=)`); **cancel** between cells (`MatrixCompareWorker`) + idempotent resume (re-run stale).
  TSN actions: pick a file, or **consolidate dropped PDFs** (`MatrixTsnConsolidateWorker`).
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
  the "a cell export leaves a paused batch intact" invariant). **Owed on the work PC:** a LIVE per-cell
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
> today: ALL 8 reports — HL Excel/PDF + Ramp Detail + Intersection Detail (Excel + PDF) + Highway
> Sequence (FLAT) + Ramp Summary & Intersection Summary (AGGREGATE)**. The Intersection Detail (PDF)
> row was added in v0.18.0 (its `tsn_subdir` shares `intersection_detail`). Nothing greyed.

A **second, manual** matrix under the **Compare** tab — a sibling of the Everything matrix but
day-keyed instead of env-keyed: **rows = report types, columns = exported days you add, each cell =
(report, day) vs TSN**. ONE data source for the whole matrix (default `ssor-prod`); **no
cross-environment, no live re-export** (it compares specific historical exports). **ALL 10
comparison-integrated reports are live** — HL Excel/PDF + Ramp Detail + Ramp Summary + Intersection
Summary + Intersection Detail (Excel + PDF) + Highway Sequence + Highway Detail (Excel + PDF,
v0.20.0); nothing greyed. (Highway Summary is export-only — no comparator yet, so it isn't a matrix
row.) Like `matrix.py`, it NEVER edits the manual compare code — it only orchestrates.

- **Shared engine:** `day_matrix.build_day_cell` delegates to `matrix.consolidate_and_compare_tsn`
  (the same path `build_comparison`'s tsn branch uses, now keyed on `(row_key, subdir)`) over the
  day's run folder `output/<date src-env>/<subdir>/`. The TSN dataset resolves per row's `tsn_subdir`
  via `matrix.tsn_source` → the **canonical TSN library** (`tsn_library.resolve`), with the legacy
  `<batch_dest>/_tsn_input/<subdir>/` + `settings.matrix_tsn_files` pick as fallback/override. The
  by-day matrix shows a PER-ROW TSN picker (named by its report, like the Everything matrix);
  each cell resolves its own report's TSN.
- **Store:** `output/comparisons/tsn-by-day/<date src-env>/<row>_vs_tsn.xlsx` (stable, dateless per
  cell); counts cached in that tree's `_results.json`. Snapshot (`day_matrix_snapshot`) is a pure stat,
  reusing `matrix._cmp_state`; `cells_to_rebuild(scope, row=, date=)` skips greyed rows + missing sides.
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

## 13. Visual evidence (`scripts/visual_evidence.py` + the per-report adapters, v0.21.0; Intersection Detail joined in v0.22.0)

The manual "screenshot the cell in both PDFs and circle it" workflow, automated, as a
**decoration of a finished vs-TSN comparison** — it never changes the comparison's
status/completion/counts, and any evidence failure only logs + adds a summary note.
Two reports so far, each via its own adapter over the shared engine:
`evidence_highway_detail` (district TSN prints) and `evidence_intersection_detail`
(the statewide TSN print). The HD-specific bullets below apply to ID analogously;
the ID differences are called out inline.

- **What it produces**, next to the comparison workbook (the `(formulas).xlsx` sibling family):
  `<comparison> (evidence).xlsx` (a Summary sheet + every stacked image embedded) and
  `<comparison> (evidence images)/` with each example in BOTH layouts (`*_stacked.png` for
  reading, `*_pair.png` side-by-side for pasting into docs). Keep-last-good: the images render
  into a temp folder and swap in only after the workbook wrote; a locked-open previous set
  diverts to `.new` with a note instead of failing.
- **Sampling:** for every differing column, up to N (user setting, 1–10, default 2) random
  example rows across random routes, keys restricted to UNIQUE-per-route on both sides so a
  highlight is THE row. Each run logs its sample seed.
- **The trust contract:** an example is only used when the value parsed back OUT of each PDF —
  normalized with the comparator's OWN projections — equals the value the comparison compared.
  So an image can never illustrate something other than what was diffed, and each rendered pair
  doubles as an end-to-end spot-check of the comparison at that cell. Failed candidates are
  skipped with a per-column reason (recorded in the workbook), e.g. the TSMIS PDF/Excel
  site-build skew or a TSN reference-date skew.
- **Sources:** TSMIS side = the per-route **(PDF)-edition** export of the report (the Everything
  matrix resolves the row's cell store, the by-day matrix that day's `*_pdf/` run folder);
  TSN side = the prints in the report's `tsn_library/<report>/pdf/` folder — Highway Detail
  takes the 12 **district prints** (the district is read from each file's own DIST-CNTY-ROUTE
  header), Intersection Detail the ONE **statewide print** (district/county read per record
  from `LOCATION`); filenames never matter. The pdf/ folders are **created + hinted by
  `tsn_library.ensure_layout`** (v0.21.1 — driven by the catalog's `TsnEntry.evidence_pdfs`
  flag; v0.21.0 never created it, so an updated install had nowhere to drop the prints), and
  re-entering a matrix tab re-pushes the state so the toggle re-probes and un-greys without a
  restart. The **normalized TSN library appends TSN District/County sidecar columns** (HD since
  its v2, ID since its v3 — `tsn_load_*.SIDECAR_HEADER`) so evidence can find a row's print;
  `_normalized_row` slices to the shared width, so the comparison itself never sees them (a
  pre-sidecar library is refused with a rebuild hint, and the D2 version bump rebuilds it
  automatically).
- **Locators:** each TSMIS locator mirrors its PDF consolidator's parse step for step while
  capturing positions — **keep them in LOCKSTEP** (HD: per-page windows, row groups, the
  postmile test, the date-token guard, cross-page carry, fallback-grid/straddling records
  rejected; ID: the document grids from both band shapes, the padded-postmile rowA test, the
  integer-column-1 rowB pairing, page-straddling records rejected). The TSN locators differ by
  print style: HD parses the TASAS district print line-anchored with the two-line REGEXES
  (word positions kept; an optional group that didn't print boxes the gap between neighbors;
  cross-checked ≥99.9% against the statewide extract); ID rides the statewide print's FIXED
  monospace column template — per-field x-windows with MAX-OVERLAP word assignment (a
  `Y`-flagged date leaning into its neighbor stays in its date window; the flag is stripped
  from the value), LOCATION as one token-split window, and a BLANK cell boxes its template
  window. The ID print is indexed ONCE per file (cached on size+mtime) inside
  `district_index`, so the engine's per-district `locate_tsn` calls are dictionary lookups —
  the engine stayed untouched. Validated statewide: 16,584/16,584 records, 30/32 fields 100.00%
  parse-back vs the raw extract (the rest are print truncations the verifier skips).
- **Wiring:** ONE hook in `matrix.consolidate_and_compare_tsn(evidence_opts=)` covers both
  matrices; callers resolve their own store layout through `matrix.evidence_opts_for` (the shared
  gate — toggle on + `visual_evidence.capable(row_key)`). The user toggle is ONE persisted pair
  (`evidence_images` + `evidence_examples`, endpoints `set_evidence_images` /
  `set_evidence_examples`) surfaced under *Comparison output* on BOTH matrix pages, greyed with a
  drop-hint until at least one report's TSN prints are in place —
  `visual_evidence.availability()` rides the state push and reports **per-report** folders
  (`reports: [{key,label,tsn_pdfs,dir}]`), so the hint names exactly which report still needs
  its prints while the other keeps working. The render stack (Pillow + pypdfium2) SHIPS since
  v0.21.0 — see [build-and-release.md](build-and-release.md).
- **Locked by** `build/check_visual_evidence.py` (registry/sources/clamp for BOTH reports, the
  caller gate, the LOCKSTEP pins, the HD TSN print regexes + the ID fixed-window/max-overlap/
  flag-strip/LOC-tokenizer behavior, span→box math, verification projections, unique-key diff
  enumeration — the ID one mirroring compare_core's cell trim so whitespace-only differences
  never enumerate — and both TSN loaders' sidecar contracts (`tsn_rows_with_dcr` row-identical
  to the locked raw loaders); the frozen self-test proves the render stack itself.
