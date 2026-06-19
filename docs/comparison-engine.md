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
input pairs live at `C:\Users\Yunus\Downloads\TSMIS\inputs` (per-route `tsmis_highway_log_route
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
(v0.14.1: `env` "Cross-environment" default, `highway_log` "Highway Log"); each `COMPARE_REPORTS`
row `(label, module_or_adapter, kind, group)` shows only under its group. `kind` is `"files"`
(file-vs-file) or `"folders"` (folder-vs-folder) — independent of `group`. See
[reports.md](reports.md) for the registry + sub-tab wiring.

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

### 9c. Cross-environment — `compare_env.py` (`"folders"`; group `env` for Ramp Summary/Detail + Highway Sequence, group `highway_log` for the Highway Log cross-env row)

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

Ramp Detail / Highway Sequence lock their layout from the files (both folders must agree, else a
clear error); Highway Log pins `EXPECTED_HEADER` + the Med Wid rule. Verified with
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

The Everything-tab **report × environment comparison matrix** is a thin orchestration layer over
the cross-environment family ([§9c](#9c-cross-environment--compare_envpy-folders-group-env-for-ramp-summarydetail--highway-sequence-highway_log-for-the-highway-log-cross-env-row)). It is **ADDITIVE**:
`matrix.py` never edits `compare_core`'s formula/label text and adds no `CompareSchema` field — it
simply calls the existing audited `EnvCompare.compare_folders(...)`. The foundation it sits on (HSL /
Ramp Detail / Ramp Summary consolidate + cross-env compare) was audited cell-accurate over the full
6-env batch (2026-06-18; see [roadmap.md](roadmap.md) closed findings).

- **Rows** come from `reports.matrix_rows()` (the `env`-group `folders` adapters, mapped to their
  export `ReportSpec` by subdir). Intersection has no adapter → never a row.
- **Cells** are computed against a **baseline** env (default `ssor-prod`, `settings.get/set_matrix_baseline`).
  Each non-baseline cell shows the **discrepancy count** (differing cells + one-sided rows),
  color-coded, with the comparison cached at `<batch_dest>/comparisons/<baseline>/<cell>_<row>.xlsx`
  (a **stable, dateless** name — NOT `suggest_name`, whose date would defeat the mtime-staleness model).
- **Freshness** is pure-filesystem: per-cell export freshness from `report_library.cell_ages`
  (newest file mtime per `<dest>/<src-env>/<subdir>/`); a comparison is **stale** when either side's
  export mtime is newer than the comparison workbook. A baseline switch is an explicit FULL recompute
  against the new baseline tree (the old tree is left intact).
- **Verdict + counts** are read off the produced VALUES workbook (literal Summary/Comparison content,
  no Excel/COM) and cached in `<dest>/comparisons/<baseline>/_results.json`, so `matrix_snapshot()`
  stays a pure offline read. A cached result is trusted only while its recorded build-mtime matches
  the file (else the cell reads "re-run").
- **Workers** (`gui_worker`): `MatrixCompareWorker` (offline, loops `build_cell_comparison`) and
  `MatrixExportWorker` (a single (report,env) refresh that reuses `ExportWorker` with **no manifest**,
  so it can't clobber a paused Export-Everything batch). Bridge: `gui_api.matrix_info` /
  `set_matrix_baseline` / `refresh_cell_export` / `refresh_cell_comparison` / `recompute_matrix`.
- **Locked by** `build/check_matrix.py` (enumeration, mtime staleness, stable paths, real
  orchestration with a planted diff → counts read back) + `build/check_matrix_bridge.py` (gate +
  the "a cell export leaves a paused batch intact" invariant). LIVE per-cell export / a full
  baseline recompute over a real store are owed on the work PC.
