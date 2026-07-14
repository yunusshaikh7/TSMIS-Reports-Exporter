# Comparison Engine — Internals

Deep code-level walkthrough of `scripts/compare_core.py` (the schema-parameterized discrepancy-workbook engine) and the three caller modules that delegate to it. This is the "how it actually works" companion to the scannable [../comparison-engine.md](../comparison-engine.md) — read that first for the what/why; come here before you change `run_compare`, the alignment, or the workbook formulas.

Files covered in full: `scripts/compare_core.py` (~1916 lines), `scripts/compare_env.py`, `scripts/compare_highway_log.py`, `scripts/compare_highway_log_pdf.py`. Supporting: `scripts/events.py` (`ConsolidateResult`/`Events`), `scripts/highway_log_columns.py` (the Highway Log schema callables), `scripts/reports.py` (the `COMPARE_REPORTS` registry).

> **The correctness lock.** `compare_core` originated in the approved TSMIS-vs-TSN
> Highway Log workbook, but historical bytes are not an oracle when they encode a
> confirmed defect. Equality, identity, pairing, formula, and count changes must follow
> the approved domain contract and be proved against an independent oracle, both workbook
> flavors, and installed Excel. Preserve output only when it is correct; record and
> explain every deliberate re-bless. See `CLAUDE.md`, the Phase-3 decision gates, and
> [../verification-and-testing.md](../verification-and-testing.md).

---

## 1. The 30,000-foot control flow

`run_compare(sc, rows_t, rows_n, has_route, out_path, *, events, confirm_overwrite,
mode, name_a, name_b, warnings, commit_guard, ...)` is the single core entry point.
Every caller loads and validates its two inputs, turns each into rows in the schema's
column order, and enters through the transactional adapter. The pipeline is:

```
run_compare
├─ guard: _DEPS_OK (openpyxl), sheet-name length (≤31), sheet-name uniqueness (case-fold)
├─ resolve `modes` from mode= ("formulas" | "values" | "both")  →  out_paths{}
├─ overwrite confirm() per output path; empty-input guard; cancel check
├─ lay = _Layout(sc, has_route)                              # column geometry
├─ keys_t = keys_for(rows_t, has_route, sc.key_field, sc.key_normalizer)
├─ keys_n = keys_for(rows_n, …)                              # [(route, key, occ)] in file order
├─ pairing = pair_occurrences_by_similarity(…)               # typed exact/capped result + trace
├─ keys_t, keys_n = pairing.keys_a, pairing.keys_b
├─ union = union_keys(keys_t, keys_n)                        # per-route difflib alignment
├─ helper_tokens = _opaque_helper_tokens(union)              # injective ordinal identities
├─ excel_limit_error(biggest_rows, n_cols)                   # fail BEFORE writing
├─ counts = count_diffs(…)                                   # the Python mirror (run summary + values literals)
├─ derive: only_t / only_n, route_coverage, union_row map, cmp_rows_t/n
└─ for m in modes:                                           # one workbook per flavor
     ├─ build `vals` (values flavor only; None for formulas) + hk_t/hk_n literal helper keys
     ├─ wb = Workbook(write_only=True);  manual calcPr iff (has_route and formulas)
     ├─ _write_summary → _write_spot_check → _write_comparison → [_write_routes]
     │   → _write_only_sheet(a) → _write_only_sheet(b) → _write_data_sheet(a) → _write_data_sheet(b)
     ├─ sc.legend_writer(wb)  (Highway Log only)
     ├─ _write_snapshot_sheet(a) → _write_snapshot_sheet(b) # very-hidden build identity
     └─ guard + wb.save(path)
   → typed ConsolidateResult/ComparisonOutcome
```

The data is parsed, paired, aligned, and counted **once** before the flavor loop and
reused for both outputs. Cancellation is polled through source validation, duplicate
grouping, cost construction, the Hungarian solver, capped fallback, and typed counting.
A cancellation returns unknown counts/quality with no trace and no workbook; no partial
assignment can escape as comparison truth.

---

## 2. CompareSchema → the engine's only report-specific input

`CompareSchema` (`compare_core.py:89`) is a frozen-ish dataclass carrying everything that varies between comparison types. The **defaults reproduce the approved TSMIS-vs-TSN wording** (`side_a="TSMIS"`, `side_b="TSN"`, `id_noun="location"`, …), so a caller that only sets `report_name`/`header` gets the original behavior.

Key fields and how the engine consumes them:

| Field | Default | Consumed by |
|---|---|---|
| `report_name`, `header` | — (required) | titles, the per-route column list `[key, f1..fn]` |
| `side_a`, `side_b` | `"TSMIS"`/`"TSN"` | sheet/tab names AND formula references (via `_sref`) |
| `id_noun`/`id_noun_plural`/`sides_noun`/`pair_noun` | `"location"`/…/`"systems"`/`""` | Summary + Spot Check + notes prose |
| `medwid_fields` | `()` | `is_medwid()` → the zero-pad-normalized equality path |
| `date_fields` | `()` | Spot Check date formatting only |
| `data_widths`/`cmp_widths` | `{}` | column widths via `_apply_field_widths` |
| `scope_flat`/`scope_consolidated` | — | Summary scope label |
| `key_field` | `0` | WHICH header column is the row identity (see §6) |
| `header_comment` | `None` | callable(label)→Comment, hover tooltips on header cells |
| `legend_writer` | `None` | callable(wb) run after sheets, before save |
| `ditto_nonasserting` | `False` | `+`-run cells become non-asserting (see §8) |
| `ditto_resolver` | `None` | display-only ditto fill on data sheets (see §8) |
| `key_normalizer` | `None` | replaces the raw key token for matching (see §7) |

Two derived properties drive layout:

- `n_fields` = `len(header) - 1` (`:160`).
- `field_indices` (`:165`) = every header index **except** `key_field`, in display order. With `key_field == 0` this is `[1, 2, …, n]` — the original order, so the default path is byte-identical. This single property is what makes the key column movable without touching the rest of the engine.

`sheet_names(has_route)` returns the visible sheet list plus the fixed internal
`__CMP_E2_SNAPSHOT_A/B` names, so side-label collision checks also protect the
very-hidden build snapshots.

### `_sref` — the quoting-aware sheet reference (`:183`)

Every formula that names a side does so through `_sref(name)`. It returns the bare name for a plain identifier (`TSMIS`, `TSN` → `TSMIS!A:A`, keeping the approved formulas byte-identical) and a single-quoted, `'`-escaped name otherwise (`SSOR-PROD` → `'SSOR-PROD'!A:A`, `Only in TSMIS` → `'Only in TSMIS'!…`). The regex also force-quotes anything that looks like a cell address (`A1`, `ABC123` via the second `re.fullmatch`) so a side literally named like a cell can't produce a broken reference. **This is why cross-env side labels with hyphens work at all** — they would otherwise be invalid Excel formula tokens.

---

## 3. keys_for — turning rows into identity tuples

`keys_for(rows, has_route, key_field=0, key_normalizer=None)` (`:197`) produces `[(route, key, occurrence), …]` in **file order**, one tuple per input row:

1. `off = 1 if has_route else 0` (the leading Route column on consolidated rows). `koff = off + key_field` — where the key column actually sits in the raw row.
2. `route` = `str(r[0])` when `has_route` (else `""`).
3. The key token is either `key_normalizer(r, off, key_field)` (when set) or the raw `str(r[koff])`.
4. `occurrence` is `seen[(route, key)]++` — repeats of the same `(route, key)` are numbered `1, 2, 3, …`. **This occurrence number is exactly what every sheet's helper column and `MATCH` lookups key on.**

So the identity of a row is the triple `(route, key, occurrence)`. Note: blank key cells collapse to `""` and still get a stable occurrence — handled, not punted.

---

## 4. pair_occurrences_by_similarity — the duplicate-pairing algorithm

This is the subtlest piece of the engine. Read the topic doc for the *why*; here is the *how*.

**The problem.** When a key legitimately repeats (two segments at the same postmile), naive occurrence numbering pairs side-A's first with side-B's first, etc. — by FILE ORDER. If a row genuinely matching the other side's SECOND instance got occurrence #1, it would be diffed against the WRONG twin and flagged as a phantom difference.

**The fix.** `pair_occurrences_by_similarity(sc, rows_t, rows_n, keys_t, keys_n, has_route, events)` (`:408`) re-numbers ONLY the occurrence component of duplicate keys, so the most-alike rows share an occurrence #. It runs after `keys_for`, before `union_keys` (`run_compare:1726`).

Step by step:

1. Group row indices by `(route, key)` on each side: `grp_t`, `grp_n` (`:419-422`).
2. For each group present on side A (`grp_t`):
   - Skip if the key isn't on side B (`nis` falsy) **or** there's no duplicate (`len(tis)==1 and len(nis)==1`) — those keep file-order occurrence, byte-identical to before (`:428`).
   - At or below `len(tis) * len(nis) == _PAIR_GROUP_CAP` (`100_000`), build the
     exact rectangular cost matrix and solve it with `_min_cost_pairs`.
   - Above the cap, inspect only the deterministic positional diagonal. The result is
     `pairing_quality="capped"`, completion is partial, and all displayed counts are
     diagnostics—not certified differences. No full matrix is allocated and no green
     or match verdict is possible.
   - Persist one strict `PairingTrace` per duplicate group, including original source
     indices, the smaller-side assignment vector, every selected pair and cost, total
     and positional costs, algorithm, dimensions, and quality. Capped groups also carry
     a matching `CappedGroupDiagnostic`.
   - Matched pairs get occurrence `1, 2, …` in **side-A file order** (`sorted(pairs, key=lambda ab: tis[ab[0]])`, `:440`). The larger side's unmatched leftovers get **higher, side-unique** occurrence numbers starting from `occ` (`:444-453`), so they stay one-sided (never accidentally collide with a matched occ).

### `_row_diff_count` — the cost (`:353`)

The cost of pairing two rows is the number of differing compared-fields, using the comparison's OWN normalization — identical to what the workbook counts: `_xl_trim` both sides, skip if `ditto_nonasserting` and either side is a `+`-run, `_medwid_norm` for med-wid fields, then `va != vb`. Lower cost = more alike. **Because the cost is exactly the per-row diff count, the optimal assignment's total ≤ any positional assignment's total** — file order is just one assignment — so similarity pairing can ONLY remove phantom diffs, never add one.

### `_min_cost_pairs` — exact rectangular assignment

Min-total-cost 1:1 assignment over the `nr × nc` matrix, returning `min(nr, nc)` `(row, col)` pairs:

1. Reject empty, zero-column, ragged, Boolean, fractional, or negative matrices. A
   malformed objective can never acquire an authoritative trace.
2. Orient the smaller side as rows (side A wins equal dimensions). The solver remains
   genuinely rectangular; the `1 × 100,000` boundary does not become a square matrix.
3. Encode the two-level objective as exact integers: scalar difference cost first, then
   the lexicographically smallest smaller-side assignment vector. This is the approved
   deterministic tie rule—not “keep file order.”
4. Run rectangular Hungarian assignment in
   `O(min(n,m)^2 × max(n,m))`, polling cancellation through validation, transpose,
   augmenting scans, result construction, and occurrence renumbering.
5. Assert the exact total never exceeds the positional total. Above-cap positional
   fallback happens outside this solver and is always non-certifying.

**Invariant the rest of the engine relies on:** the route/key identity is unchanged—only
the duplicate occurrence is re-numbered. Workbook lookups use opaque ordinal tokens,
not flattened route/key text. The assignment and its quality flow through the typed
outcome and strict sidecar. Locked by `check_compare_dupmatch.py`,
`check_compare_pairing_policy.py`, and `check_compare_cancellation.py`.

---

## 5. union_keys — the per-route difflib alignment

`union_keys(keys_t, keys_n)` (`:225`) produces the Comparison sheet's row universe: the union of the two key sequences in **document order, grouped by route**.

1. Bucket each side's keys by route (`by_route_t`, `by_route_n`).
2. Route order = side-A's routes in side-A order, then B-only routes in B order (`:251`).
3. Within each route:
   - If one side is empty, `emit` the other (a wholly one-sided route).
   - Else align the two key sequences with `difflib.SequenceMatcher(None, seq_t, seq_n, autojunk=False)` and walk `get_opcodes()`:
     - `equal`/`delete` → emit side-A's block.
     - `insert` → emit side-B's block.
     - `replace` → emit side-A's block, then side-B's block (`:264-266`).
4. `emit` (`:245`) dedupes via a `seen` set: **first position wins**. A key can fall outside the aligner's `equal` blocks when one file lists it out of sequence (seen in the field: TSMIS printed `059.739` after `059.759` while TSN kept order) — first occurrence anchors it, and the Excel `MATCH` lookups pair it with both files regardless of where it landed.

**Why per-route, not global:** SequenceMatcher is roughly O(n²) worst-case; aligning per route keeps it fast on consolidated inputs (50k+ rows). The route bucketing is the performance guard.

---

## 6. _Layout — column geometry for both shapes

`_Layout(sc, has_route)` (`:528`) is the single place that knows where every column lands. It maps the abstract schema onto concrete Excel column letters for the two shapes:

- **per-route data sheet:** `A`=Comparison-row back-link, `B`=key, `C..`=fields, then the Key (helper) at the end.
- **consolidated data sheet:** `A`=back-link, `B`=Route, `C`=key, `D..`=fields, helper at end.

Important members:

- `back_col = "A"` (the back-link column on data sheets), `route_data_col = "B"` when `has_route`.
- `key_col` (`:557`) = the Key (helper) column letter — `len(data_header) + 2` (back-link + all input columns + 1). The `MATCH` lookups search THIS column.
- `data_last_col` = last input column (helper is one past it). `data_header` (`:554`) = `["Route"]? + sc.header` — **all** columns including the key, in input order (the key column stays put on data sheets).
- `id_headers` (`:561`) = the Comparison sheet's lead columns: `[Route?, sc.header[key_field], "#", "<A> Row", "<B> Row", "Status", "Diffs"]`. The KEY column is pulled to the identity slot here.
- `f0` / `first_field_col` / `last_field_col` — the field block on the Comparison sheet starts after `id_headers`.
- Per-column accessors: `data_col(field_idx)`, `field_col(field_idx)`, `field_pos`,
  and `key_expr(row, helper_token)`. `key_expr` accepts only a versioned opaque token;
  it never reconstructs identity with delimiter concatenation.

After the Key helper and any Med-Wid stages, `_Layout` appends hidden build-freshness
chunks. Every source/helper cell has an exact immutable counterpart on a very-hidden
snapshot sheet. A footer sentinel detects appended rows; fixed expected counts detect
deletion/insertion/reordering. Summary requires every chunk to be `OK` and every footer
to be `END` before it exposes the computed verdict.

`c_route`/`c_loc`/`c_occ`/`c_trow`/`c_nrow`/`c_status`/`c_diffs` are unpacked from `id_headers` letters (`:567-574`) and referenced all over the writers.

---

## 7. The key normalizer (roadbed-aware key)

`key_normalizer` (`CompareSchema:158`, opt-in) is a `callable(row, off, key_field) -> str` that returns the canonical identity token to match on **in place of** the raw key-column value. `None` = byte-identical original (raw key string), so every comparison except TSMIS-vs-TSN Highway Log is untouched and the regression lock holds.

The only setter is `highway_log_columns.roadbed_canonical_location` (`highway_log_columns.py:276`), wired in `compare_highway_log._SCHEMA` (`compare_highway_log.py:68`). On a divided highway the two sources encode a segment's two roadbed rows differently — TSMIS (PDF + Excel) suffix the Location (`R021.466R`/`…L`); TSN omits the suffix and instead dittos the non-subject 8-column block. Keying on the raw Location would SPLIT the same physical roadbed row into a false one-sided pair. The normalizer derives the roadbed:

- A Location already ending in `R`/`L` (PDF/Excel) is authoritative — returned unchanged (`:292`).
- A suffix-less Location (TSN) gets `roadbed_tag(row, off)` appended (`:294`), where `roadbed_tag` (`:260`) counts dittoed cells in the Left vs Right 8-column blocks (`LEFT_BLOCK_IDX`/`RIGHT_BLOCK_IDX`): a Left-block-dittoed row describes the RIGHT roadbed (`"R"`), and vice-versa; combined/indeterminate → `""`.

The trailing equation `E` marker and leading alignment prefix are PRESERVED (they are identity, not the roadbed), so a route-start `R000.000` never collapses into a bridge `000.000`. The key STRICTLY REFINES (can split, never merge). **Crucially, `compare_env._HL_BASE` clears it** (`compare_env.py:419` — `key_normalizer=None`): cross-env compares two TSMIS exports that already use the same suffix encoding, so the normalizer is unnecessary there and would perturb validated output. It is a TSMIS-vs-TSN tool. PDF-vs-Excel keeps it (both already suffix, so it's invariant). Locked by `build/check_highway_log_roadbed.py`.

`keys_for` is the only consumer (`:215`). Because the normalizer only changes the match KEY token (not the displayed value), the DATA sheets still show each source's raw Location.

---

## 8. The ditto code path (Highway Log only)

Three flags collaborate, all OFF by default so non-HL comparisons are byte-identical.

### `ditto_nonasserting` — never counts a `+`-run as a difference

A Highway Log ditto marker (`+`, `++`, `+++`) means "this attribute's value is on the paired roadbed's own row" — a pointer, not data. The engine has a Python detector and a formula twin:

- `_is_plus_run(v)` (`:305`) — `set(str(v).strip()) == {"+"}` and non-empty. Kept local so the generic engine carries no Highway-Log import; mirrors `highway_log_columns.is_ditto`.
- `_isditto_xl(trim_ref)` (`:639`) — the Excel expression `AND(ref<>"", SUBSTITUTE(ref,"+","")="")`.
- `_eq_with_ditto(sc, eq, trim_t, trim_n)` (`:645`) — wraps an equality expression as `OR(isditto_t, isditto_n, eq)` when `ditto_nonasserting`, else returns `eq` unchanged.

Where it fires: in `_row_diff_count` (`:360`), `count_diffs` (`:500`), `_field_value` (`:687`) — all `continue`/short-circuit on a ditto. In `_field_formula` (`:670`) and the Spot Check field rows (`:1114`) — wrapped via `_eq_with_ditto`. So the Python mirror and the live formula agree.

### `ditto_resolver` — display-only fill on data sheets

`ditto_resolver` (`CompareSchema:148`) is `callable(rows, has_route) -> {row_index: {col_in_row: resolved_value}}`, set to `highway_log_columns.display_fills`. In `_write_data_sheet` (`:789`) the engine keeps the RAW `++` in the cell (the non-asserting diff needs it) but tints it `_DITTO_FILL` (`"E4DFEC"`, `:57`) and attaches a Comment showing the paired-roadbed value (`:807-811`). `display_fills` (`highway_log_columns.py:220`) groups rows per route and calls `fill_paired_roadbed`, which is COLUMN-AGNOSTIC (a `+`-run in any column, not just the roadbed blocks — divided-highway rows also ditto the shared median/access-control columns). Purely informational; never affects a diff result.

---

## 9. count_diffs — the Python mirror

`count_diffs(sc, rows_t, rows_n, keys_t, keys_n, union, has_route)` computes everything the workbook's formulas will compute, in Python: overall totals (`both`, `t_only`, `n_only`, `diff_rows`, `identical`, `diff_cells`), per-field diff counts (`field_diffs`), per-route aggregates (`route`), `first_diff_row` (the Spot Check default), asserted/context-cell counts, and one compact `E`/`D`/`N`/`U` state mask per union row.

`compared_cell` is the canonical semantic: for each `field_indices` column it returns a typed `ComparedCell` carrying raw values, ASCII-TRIM display operands, exact normalized operands, assertiveness, equality, display text, and a state code. `count_diffs`, `_row_diff_count`, `_field_value`, Report View, and the values state masks consume that object. Formula mode independently derives the same codes into hidden versioned state-mask chunks; display formulas, CF, row `Diffs`, Summary field counts, and Spot Check project from those codes rather than searching rendered text. The `route` aggregates pre-count `t_rows`/`n_rows` from the full key lists, then accumulate `locs`/`matched`/`withdiffs`/`cells` over the union.

**This single result powers BOTH the run summary AND the values workbook's literal cells** — that's the mechanism that makes the two flavors impossible to disagree (§11).

### The normalizers

- `normalize_value(v)` — applied by loaders per loaded cell. Renders real `datetime`/`date`/`time` to fixed ISO strings and actual Booleans to uppercase `TRUE`/`FALSE`; numeric 1/0 and int subclasses do not Boolean-fold.
- `_xl_trim(v)` — Excel TRIM semantics for ASCII U+0020 only: stringify (integer floats → int), collapse internal ordinary-space runs, strip ordinary-space edges. Tabs, CR/LF, NBSP, and other Unicode whitespace remain data.
- `_medwid_norm(t)` — decimal-exact narrow grammar: ASCII `digits[.digits]` plus at most one printable-ASCII non-digit/non-dot suffix; normalize zero padding only inside that grammar and preserve everything else raw. Its formula twin is the five-stage `CMP_E1_MW_V1` hidden helper, not Excel `VALUE()`.

---

## 10. The streaming workbook build, sheet by sheet

The workbook is written in openpyxl's **`write_only=True` (streaming) mode** (`run_compare:1803`): the consolidated comparison carries ~2M formula cells that the in-memory mode cannot save in reasonable time/RAM. Streaming imposes hard rules the writers obey throughout:

1. **Sheets are created in DISPLAY order** — Summary first (so it's the active sheet on open), then Spot Check, Comparison, [Routes], Only-in A/B, data A/B, [Legend]. You cannot reorder after creation.
2. **Sheet-level setup (freeze panes, column widths, auto-filter, conditional formatting) must be set BEFORE any `ws.append`.** Every writer front-loads these.
3. **Every styled cell is a `WriteOnlyCell`** — built by `_styled` (`:719`).

`_styled(ws, value, font, fill, align, guard)` (`:719`) is the universal cell factory. The Summary and Spot Check sheets, being sparse, build a `grid` dict of `(row, col) -> (value, font, …)` first, then emit it row-by-row at the end with `None` for gaps (`_write_summary:1636`, `_write_spot_check:1144`) — the streaming workaround for random-access layout.

### Sheet 1 — Summary (`_write_summary`, `:1348`)

Sparse grid via `put`/`line`/`banner`/`stat`/`check` helpers. The headline is **THE VERDICT** at `B3` (or `B4` under the manual-calc F9 banner — `verdict_row`, `:1409`): a live formula in the formulas flavor, a literal in values. Two CF rules key on the first character (`✓` green / `✗` red, `:1411-1416`). The verdict text:

- formulas flavor (`:1430`): `=IF(AND(SUM(diffs)=0, one_sided=0), "✓ EVERYTHING MATCHES…", "✗ DIFFERENCES FOUND — "&TEXT(...)&…)`.
- values flavor (`:1437`): the literal computed from `counts`.
- `warnings` non-empty (`:1419`) flips the match text to `"✗ COULD NOT COMPARE EVERYTHING…"` — uses `✗` deliberately so the EXISTING red CF applies (no new rule → no-warnings path stays byte-identical).

Then sections: ROW COUNTS, MATCH STATUS, ROUTE COVERAGE (consolidated), FIELD-LEVEL DISCREPANCIES, DIFFERENCES BY FIELD (one `COUNTIF(…,"*≠*")` per field), and **SELF-CHECK** (`:1517`). Each `stat` writes a formula or the literal value. Each `check` (`:1522`) recomputes a headline number a SECOND independent way and emits `=IF(cond,"OK","CHECK")` — e.g. status totals = union count, `COUNT` of row links = both+one-sided, Only-in tab row counts = one-sided counts, per-field sums = total diff cells, Routes-sheet row sums = data-sheet counts. SELF-CHECK rows stay LIVE in BOTH flavors (in values they recount the literal sheets). A `CHECK` means a formula no longer points at the right rows.

### Sheet 2 — Spot Check (`_write_spot_check`, `:929`)

One row under a microscope. Fixed cell addresses: input row at `$C$6`, matched data rows at `$C$12`/`$F$12`, status at `$C$11`, field block from row `F_FIRST=16`. The field rows (`:1095`) lay out raw stored values from both data sheets (`raw()`, `:1091`) next to an **independently recomputed verdict** (`:1120`) — same TRIM/Med-Wid/ditto rules, read straight from the data sheets, **never reading the Comparison sheet's answer** — and an `Agree?` column (`:1127`) that cross-checks the independent verdict against what the Comparison sheet displays (matched rows) or against that system's own value (one-sided rows). Opens pre-set to `default_row` = the first matched-with-differences Comparison row. In manual-calc mode it carries a bold "PRESS F9 AFTER EVERY CHANGE" reminder (`:1010`).

### Sheet 3 — Comparison (`_write_comparison`)

The big sheet — one row per union key. Hidden, versioned state-mask chunks follow the visible fields and carry one `E` / `D` / `N` / `U` code per field. CF is set before rows: a field is red only when its corresponding mask character is `D`; yellow/blue still identify A-only/B-only rows, and positive `Diffs` stays bold red. Rendered text never owns truth.

The id columns per row: `[route?, loc, occ, <A>Row link, <B>Row link, Status, Diffs]`, then one field cell per `field_indices`. In the **formulas** branch (`vals is None`, `:875`):

- `loc`/`occ` are literals (the build-time key).
- `<A>Row`/`<B>Row` via `_row_link` (see below).
- `Status` = `IF(AND(trow<>"",nrow<>""),"Both",IF(trow<>"","<A> only","<B> only"))`.
- `Diffs` = the number of `D` characters across that row's hidden state-mask chunks; one-sided rows stay blank. Literal display text cannot change the count.
- field cells via `_field_formula`.

In the **values** branch: the same shapes come from `vals` — `_row_link_value` (build-time row number, no MATCH), literal status/Diffs, `_field_value` per field, and exact literal state-mask chunks.

#### `_DIFF_MARK = " ≠ "` — presentation only

A differing cell still renders the familiar `a ≠ b`, but the separator is not inspected by CF, `Diffs`, Summary, Spot Check, Matrix counts, or the values mirror. Equal literal source text containing the same sequence remains equal, neutral, and zero-diff. The hidden state codes are the only workbook truth surface.

#### `_field_formula` and `_field_value`

`_field_formula` projects familiar text from the row status plus the field's state-mask character: one-sided → that side's value, `D` → `a ≠ b`, `E`/`N` → the neutral display. Ordinary matched state uses blank-safe ASCII-TRIM operands with case-sensitive `EXACT`; Med-Wid state compares the hidden CANON helpers with `EXACT`; context and configured dittos become `N`. `_field_value` consumes the already-computed Python state code for the literal values twin.

#### `_row_link` (`:605`) — the triple-MATCH and the HYPERLINK-reads-blank trap

`=IFERROR(HYPERLINK("#<side>!"&m&":"&m, m), "")` where `m = MATCH(key, <side>!key_col:key_col, 0)`. The link targets the **entire row** (`"57:57"`) so Excel SELECTS the whole row on arrival (temporary highlight) WITHOUT scrolling right. **Gotcha (COM-measured on real Excel):** a bounded range like `A57:AH57` made Excel scroll to the range's RIGHT edge when it didn't fit the window; row-only references keep `scrollColumn` home — do not regress to a bounded range.

**The triple-MATCH gotcha (`m` appears three times):** the link's friendly value is the MATCH number itself, so the cell still counts as a NUMBER — the Summary SELF-CHECK uses `COUNT(<A>Row:…)`. If the friendly value were text or blank, `COUNT` would undercount and SELF-CHECK would read CHECK. So `m` is computed three times (range start, range end, display). `_row_link_value` (`:622`) is the values-flavor equivalent with the row number known at build time.

### Sheet 4 — Routes (consolidated only) (`_write_routes`, `:1283`)

One row per route with live coverage stats (`COUNTIF`/`COUNTIFS`/`SUMIF` over the data + Comparison sheets in the formulas flavor, `vals["counts"]["route"]` literals in values). Only the route-id cell is injection-guarded (`:1343`) — the rest are our own formulas/safe literals.

### Sheets 5-6 — Only in A / Only in B (`_write_only_sheet`, `:1162`)

Every one-sided union row, in union order, with field data pulled LIVE from that system's data sheet (same MATCH-on-helper-key + INDEX as the Comparison sheet). Consolidated mode adds a `Missing from <other>` column — `"entire route"` (tinted; the other system lacks the whole route, via `COUNTIF(<other>!Route:Route,$A)=0`) vs `"this <noun> only"`. **Edge case handled:** `keys` can be EMPTY when the two sides match perfectly (common cross-env) — the CF range `A2:…1` would be invalid, so the CF is added only `if lay.has_route and keys` (`:1203`).

### Sheets 7-8 — data sheets A / B (`_write_data_sheet`, `:761`)

Each input is copied with a leading `Comparison row` back-link, a trailing opaque
`Key (helper)`, optional hidden Med-Wid stages, and hidden build-freshness chunks.
Helpers are versioned ordinal tokens (`__CMP_E2_KEY_V1_…`) assigned injectively in
union order; route/key text containing delimiters cannot collide. Ditto tint/comment
is applied when `ditto_resolver` is set.

### Sheet 9 — Legend (Highway Log only)

`sc.legend_writer(wb)` (`run_compare:1838`) runs after all sheets. `highway_log_columns.write_legend_sheet` (`:344`) appends a streaming-safe `Legend` sheet.

### Why the helper key is a build-time literal (the COUNTIFS gotcha)

Both flavors write literal opaque helpers, not a live `COUNTIFS` occurrence. A live
`COUNTIFS` mis-numbers blank key fields, while delimiter-flattened route/key/occurrence
text is not injective. The opaque token solves both problems and is guarded as source
text. Comparison and Only-in formulas use only that token in `MATCH`.

### Very-hidden build snapshots

`_write_snapshot_sheet` appends `__CMP_E2_SNAPSHOT_A/B` after all visible/familiar
sheets. Each snapshot stores source-row ordinal, every source cell, the opaque helper,
and literal Med-Wid stages. Live data-sheet formulas compare current cells to the
snapshot with blank-safe `EXACT`; an appended-row sentinel scans the remaining source
range. Summary wraps both formula and values headlines in this predicate. Any source,
key, helper, duplicate-order, insertion, or deletion edit therefore yields
`REGENERATE REQUIRED`; stale live observations are visible only as non-certifying data.

---

## 11. The two-flavor mechanism, precisely

`mode` resolves to `modes` (`:1699`): `formulas`→`("formulas",)`, `values`→`("values",)`, `both`→`("formulas","values")`. The values twin is saved as `<stem> (values)<suffix>` (`:1706`). The loop body builds either:

- **`vals = None`** (formulas) — every writer emits live formulas; `wb.calculation.calcMode = "manual"` + `calcOnSave = False` + `fullCalcOnLoad = False` iff `has_route` (so ~2M formulas don't recalc for minutes on open; the user presses F9 once and saves). Per-route files and the values copy stay automatic.
- **`vals = {…}`** (values) — a precomputed model: `by_t`/`by_n` (key→row), `row_t`/`row_n` (key→data-sheet row number for the links), `routes_t`/`routes_n`, `counts` plus exact row state masks from the SAME `count_diffs` result, `n_t`/`n_n`, and route-coverage sizes. The writers emit literal results.

**The guarantee:** values mode consumes the Python `ComparedCell` decisions and literal state masks; formula mode independently emits the same `E`/`D`/`N`/`U` codes with blank-safe `EXACT`, staged Med-Wid CANON helpers, and matching ditto/context gates. Display, CF, Diffs, and Summary project from those codes. The equality-policy gate compares both twins over adversarial types/content, while installed Excel supplies the final formula evaluator. The run summary is built from the Python counts. Spot Check and SELF-CHECK stay live in the values workbook and independently recount/recompare the literal sheets.

---

## 12. Write-path safety guards

Three guards, all preserving exact clean-data meaning:

1. **Literal-cell guard** — `is_formula_injection(value)` covers text starting with `= + - @` and every Excel error token. `_styled(…, guard=True)` / `set_safe_literal_cell` force those values to STRING cells so Excel displays rather than executes/propagates them. Actual Booleans become uppercase text. Copied source numerics use the explicit `exact_source_numeric` path, which stores every finite value as exact `_xl_trim` text; this prevents Decimal-scale/exponent and finite-float rendering drift. NaN/infinity fail before output interaction. The helper's default keeps the shared >15-significant-digit backstop while small engine counts stay numeric. Engine formulas/HYPERLINK cells are never guarded as source data.
2. **`normalize_value`** (§9) — canonicalizes dates and actual Booleans at LOAD so the two flavors cannot diverge on locale/date or bool/int coercion.
3. **Pre-write limit + collision checks** — `excel_limit_error(biggest, n_cols)` (`:74`, fails before writing past Excel's `1_048_576`-row / `16_384`-col caps, since openpyxl would raise mid-write losing the partial file or silently drop columns); sheet-name length ≤ 31 (`run_compare:1679`); case-insensitive sheet-name uniqueness so a side literally named `Summary`/`Comparison`/… fails early with guidance (`:1687`); and a `PermissionError` on save → "probably open in Excel" message (`:1844`).

---

## 13. The three comparison families (the callers)

All three are `run_compare` callers; they differ only in loading + schema. Registered in `reports.py:COMPARE_REPORTS` as `(label, module_or_adapter, kind, group)` (`:103`), grouped onto Compare sub-tabs by `COMPARE_GROUPS` (`:83`).

### TSMIS-vs-TSN Highway Log — `compare_highway_log.py` ("files", group `highway_log`)

The schema home. `_SCHEMA` (`:48`) sets ALL the Highway Log specials (med-wid, date fields, ditto flags, `header_comment`, `legend_writer`, `key_normalizer`). `_load_input(path)` (`:103`) accepts the per-route (31 cols) or consolidated (`Route` + 31) layout via `hlc.recognize()` (which accepts CORRECTED or OLD vendor labels, aligning by POSITION) and loads through `_hl_normalize` (`:90`) — `normalize_value` PLUS tab/newline→space collapse (the Excel export pads Description with trailing TABs that `_xl_trim` doesn't strip). `compare()` (`:142`) validates both files have the SAME shape (both per-route or both consolidated) then delegates.

### PDF-sourced Highway Log — `compare_highway_log_pdf.py` ("files", group `highway_log`)

`_HighwayLogFileCompare` (`:32`) `replace()`s `_hl._SCHEMA` overriding ONLY `side_a`/`side_b` and the two note fragments — **engine text untouched, regression lock intact**. It REUSES `_hl._load_input`. Two instances: `TSMIS_PDF_VS_TSN` (`"TSMIS (PDF)"` vs `"TSN (PDF)"`) and `TSMIS_PDF_VS_EXCEL` (`"TSMIS (PDF)"` vs `"TSMIS (Excel)"`). `file_a_label`/`file_b_label` name the GUI file pickers so PDF-vs-Excel doesn't mislabel both TSMIS sides.

### Cross-environment — `compare_env.py` ("folders", group `env`/`highway_log`)

`EnvCompare` (`:264`) compares the SAME report from two RUN FOLDERS — no consolidation first; per-route files are merged in memory (Route prepended, header locked from the first file). `compare_folders()` (`:334`) loads each side (`_load_xlsx_side` for XLSX reports, `_load_ramp_summary_side` parsing PDFs for Ramp Summary), validates the two folders' headers match, builds a per-report schema in `_schema()` (`:314`), and delegates. Side labels come from `_side_labels` (`:83`) — `SSOR-PROD` style, date-disambiguated for same-env, capped at 23 chars so `Only in <label>` fits 31.

`_schema` plumbing worth noting:
- `force_header` (`:317`) relabels the loaded (positional) header to the corrected display header — Highway Log uses it so vendor-mislabeled Excel exports still compare.
- `key_col` → `_resolve_key_field(header)` (`:298`) resolves the configured key column NAME to a header index, **falling back to column 0 + a log warning** when absent (layout drift degrades, never crashes). `RAMP_DETAIL`/`HIGHWAY_SEQUENCE` set `key_col="PM"` (the coarse first column would inflate diffs). `_HL_BASE` clears `key_normalizer` (§7).

Each side's loader returns `skipped` strings; `compare_folders` folds `skip_a + skip_b` into `warnings` (`:398`) so an unreadable input can never masquerade as a clean match — the **incompleteness contract** (§14).

---

## 14. The verdict and incompleteness contract

`run_compare`'s return (`:1850-1916`) leads `summary_lines[0]` with one of:

- `✓ EVERYTHING MATCHES…` — `matches and not incomplete`, where `matches = diff_cells == 0 and one_sided == 0`.
- `⚠ COULD NOT COMPARE EVERYTHING…` — `matches and incomplete` (`incomplete = bool(warnings)`).
- `⚠ PARTIAL / PAIRING LIMIT…` — an above-cap duplicate group used positional
  diagnostics; the counts are observable but not certified differences.
- `✗ DIFFERENCES FOUND…` — otherwise.

`ConsolidateResult.verdict` is `"match"` only for complete input coverage, exact pairing,
zero differing cells, and zero one-sided rows. The typed outcome also requires
`pairing_quality="exact"`. In the workbook, snapshot freshness wraps the calculated
headline; any post-build source/helper mutation replaces it with `REGENERATE REQUIRED`
even if the live observations would otherwise look clean.

---

## 15. Extension points

### Add a field to an existing CompareSchema without breaking the correctness lock

The rule: **default it OFF.** Every behavior-changing schema field already follows this (`key_field=0`, `ditto_*=False/None`, `key_normalizer=None`, `header_comment=None`, …). To add one:

1. Add the field to `CompareSchema` (`:89`) with a default that reproduces today's behavior.
2. Gate every new code path on it so the default is a no-op (mirror how `ditto_nonasserting` guards `_eq_with_ditto`/`_row_diff_count`/`count_diffs`/`_field_value`).
3. Provide the formula twin AND the Python mirror if it affects equality (so both flavors agree — see the `_is_plus_run`/`_isditto_xl` pair).
4. Re-run every comparison gate plus installed Excel. Historical bytes may be
   re-blessed only when the independent oracle proves and explains the semantic delta.

Do not change formula or label text casually, but never preserve a confirmed defect to
satisfy a historical byte comparison. Update the oracle-bound expectation with evidence.

### Add a new comparison family

Append one row to `COMPARE_REPORTS` (`reports.py:103`) and list the module in `APP_MODULES` (`build/app.spec`). The two input kinds:

- **"files"** — a module exposing `compare(path_a, path_b, out_path, events=None, confirm_overwrite=None, mode="formulas") -> ConsolidateResult` + `REPORT_NAME` + `suggest_name(path_a)`. Pattern: `compare_highway_log.py` / `compare_highway_log_pdf.py`.
- **"folders"** — an adapter exposing `compare_folders(dir_a, dir_b, out_path, …)` + `REPORT_NAME` + `suggest_name(dir_a, dir_b)`. Usually just another `EnvCompare(...)` instance (give it the subdir, sheet name, optional pinned header / base schema / `key_col`).

`group` is one of `COMPARE_GROUPS` ids — independent of `kind`, so input plumbing is untouched. **Don't hand-roll workbook output** — build a `CompareSchema` and call `run_compare`; that is the shared correctness boundary. Accept `mode` even if you only implement one flavor.

---

## 16. Gotchas checklist for maintainers

- **Streaming order is law.** Sheets in display order; freeze/widths/auto-filter/CF before any `append`; every styled cell is a `WriteOnlyCell`. Sparse sheets (Summary, Spot Check) build a `grid` dict and emit at the end.
- **`_DIFF_MARK = " ≠ "` is display-only.** Never reintroduce marker scans in CF, Summary, Spot Check, Matrix readers, or validation. Truth is the typed `ComparedCell` / versioned state mask.
- **Workbook identity is an opaque build-time token**, not a live `COUNTIFS` or a
  pipe-joined tuple. Blank keys and delimiter-bearing components remain injective.
- **Any source/helper edit invalidates certification.** The very-hidden snapshot and
  tail sentinels must remain current; `REGENERATE REQUIRED` dominates every otherwise
  green/diff headline after an edit.
- **Pairing/count cancellation returns no comparison truth.** Never catch
  `RunCancelled` as a generic failure or return traces/counts accumulated before it;
  quality and counts remain unknown, trace stays empty, and existing output is untouched.
- **HYPERLINK reads blank for COUNT** unless the friendly value is the numeric MATCH — that's why `_row_link` computes the MATCH three times. Don't "simplify" it to a single MATCH stored as text.
- **Row links target whole rows (`"57:57"`)**, never bounded ranges — bounded ranges scroll Excel to the right edge (COM-measured).
- **Manual calcPr** is set ONLY for `has_route and mode=="formulas"`; the loud F9 banner on Summary/Spot Check is the only thing distinguishing an uncalculated workbook from broken data.
- **Empty one-sided tabs** — `keys` can be empty (perfect cross-env match); guard CF ranges on non-empty (`A2:…1` is invalid).
- **The Python and Excel state twins must stay in lockstep.** Python consumers read `ComparedCell`; formula mode independently emits `E`/`D`/`N`/`U` masks using blank-safe `EXACT`, the Med-Wid CANON helpers, and the ditto/context gates. Touch either side only with the equality-policy gate, formula-length/physical-width checks, and installed-Excel rebuild parity.
- **`key_normalizer` is cleared in cross-env** (`compare_env._HL_BASE`) on purpose — re-adding it would perturb validated cross-env output.
