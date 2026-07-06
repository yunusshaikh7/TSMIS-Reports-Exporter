# P5 — Report-family DRY (one family at a time) — Claude report

## 1. Phase ID and name
**P5** — Report-family DRY (one family at a time) `[conditional / deferrable; depends P3, P4]`

This phase has two families (plan §I, line 446): **family 1 = the `tsn_load_*` single-file TSN
normalizers** (collapse to a `tsn_library.build_normalized` factory with thin shims, S04), and
**family 2 = the `compare_*_tsn` comparator driver** (`compare_tsn_common.py`). Per the plan's
explicit completion note — *"(Deferrable: ship the tsn_load factory if time permits; **defer the
comparator driver to a point release** without affecting the DoD.)"* — and the "one family per
reviewable diff" boundary, **this cycle implements family 1 only**; family 2 is deferred (see §10).
The user selected P5 for this cycle.

## 2. Baseline commit
`c86dc78` (HEAD after P4 committed — "refactor: add report-metadata catalog + console-menu parity").
Baseline: **58** offline Python checks + 2 Node frontend checks green; `check_import_direction`,
`check_app_modules`, `check_no_misspelling`, byte-compile, `node --check app.js`, `git diff --check`
all green; tree clean apart from the untracked `docs/planning/`. Dependencies **P3 committed**
(`5defe9e`) and **P4 committed** (`c86dc78`) — both satisfied.

## 3. Changes made
The four single-file TSN loaders shared one ~30-line skeleton (find newest raw → deps gate →
overwrite-confirm → parse → write a styled write-only workbook → atomic save → PermissionError
guard), duplicated 4×. P5 collapses that skeleton into **one factory** and reduces the modules to
thin per-report shims — **with no behavior change** (proven **semantically identical** old-vs-new, §7).

1. **`scripts/tsn_library.py` — new shared substrate (S04/R1-N01):**
   - `_newest_raw(rdir, glob)` — the newest non-`~$` file matching `glob` (the single statewide
     export each loader normalizes), factored out of the four duplicated `_find_raw`.
   - `_write_normalized_workbook(sheet, header, header_align, rows)` — the write-only workbook with
     the shared TSN-library blue header + the report's own `Alignment(**header_align)`, then the
     projected rows. openpyxl is imported lazily inside (so `tsn_library`'s import surface is
     unchanged for its many consumers, and the deps gate runs first).
   - `build_normalized(raw_dir, out_path, *, glob, deps_ok, deps_msg, no_raw_what, no_raw_hint,
     log_label, sheet, header, header_align, project, events, confirm_overwrite)` — the shared
     driver. Runs the deps gate, missing-raw message, overwrite-confirm, the `Normalizing …` log,
     the parse-error wrap, the workbook write, `artifact_store.atomic_save` (F9) + the
     PermissionError guard. `project(raw_path)` returns `(rows, make_result)`, where `make_result(
     out_name)` builds the report's own success `ConsolidateResult` — so per-report result text and
     the producer PARTIAL/skipped completion stay in the shim.
2. **The four `tsn_load_*` shims** (`tsn_load_ramp_detail` / `_intersection_detail` /
   `_ramp_summary` / `_intersection_summary`) — reduced to: a `from openpyxl import Workbook` deps
   probe (`_DEPS_OK`), `RAW_GLOB`, a `_project(raw_path)` that calls the report's projection (which
   already lives in the matching `compare_*_tsn` module — `tsn_rows_from_raw` / `parse_tsn_pdf`) and
   returns `(rows, make_result)`, and a `build_into(...)` that delegates to
   `tsn_library.build_normalized(...)`. `build_into` (the `tsn_library` builder contract / the
   `report_catalog` lazy builder string `tsn_load_*:build_into`) is preserved.
3. **New `build/check_tsn_normalizer.py`** (**28** assertions, comprehensive after round-1
   remediation) — locks the factory against an **independent frozen oracle** (the sheet/header/
   alignment literals are hand-written here, NOT re-read from the kwargs the shim passes): for all six
   cases (Ramp/Intersection Detail + full/partial of both summaries) it asserts every
   `ConsolidateResult` field, the exact event-log line, the sheet/header/data rows, and **every header
   cell's alignment + font + fill**; the two summaries flag PARTIAL/skipped (with the exact warning
   line) on a missing category; plus the shared skeleton's exact error/cancel strings + branches (deps
   gate, missing-raw, overwrite-confirm cancel, parse-error wrap, newest-by-mtime pick, `~$` lock
   skip), the atomic-save `PermissionError` contract (prior artifact retained, no stray file), and the
   P5-A01 ImportError backstop.
4. **CI wiring** (`.github/workflows/checks.yml`) — `python build/check_tsn_normalizer.py` added
   after `check_tsn_outcome` (blocking).

## 4. Files affected
**Modified product (5):** `scripts/tsn_library.py` (the factory), `scripts/tsn_load_ramp_detail.py`,
`scripts/tsn_load_intersection_detail.py`, `scripts/tsn_load_ramp_summary.py`,
`scripts/tsn_load_intersection_summary.py` (the four shims).
**New test (1):** `build/check_tsn_normalizer.py`.
**Modified CI (1):** `.github/workflows/checks.yml`.
**Untouched:** `compare_core.py` (regression-locked); the `compare_*_tsn` comparators + their
projection/schema (`tsn_rows_from_raw` / `parse_tsn_pdf` / `_CATEGORIES` / `SHARED_HEADER` /
`NORMALIZED_SHEET` are read, never changed); the two multi-file TSN consolidators
(`consolidate_tsn_highway_log` / `_highway_sequence` — a different shape, out of family-1 scope);
auth, updater/TLS, `version.py`, `report_catalog`, `reports`, the matrix `row_key`; no `app.spec`
change (all five modules were already in `APP_MODULES`; checks aren't shipped).

## 5. Architectural decisions
- **Factory lives in `tsn_library`** (plan: "`tsn_library.build_normalized` factory"). Cycle-safe:
  the `tsn_load_*` shims now import `tsn_library`, and `tsn_library` never imports `tsn_load_*`
  (its builders resolve lazily via `report_catalog` strings), so the new edge is acyclic —
  `check_import_direction` green.
- **`project → (rows, make_result)` split.** The shared skeleton owns find/gate/write/save; the
  report-specific projection AND result-building (message / summary_lines / producer completion)
  stay in the shim's `_project`. `make_result(out_name)` is a closure so the shim can keep its exact
  message/summary while the factory injects the output filename — preserving every result field.
- **`header_align` passed as a plain kwargs dict**, splatted into `Alignment(**header_align)` inside
  the factory (after the deps gate). This (a) reproduces each report's EXACT original `Alignment(...)`
  call — the three distinct variants: detail = `center/center/wrap`, ramp-summary = `center/center`,
  intersection-summary = `center` only — identically, and (b) keeps openpyxl out of the shim's
  eager `build_into(...)` args (so a missing-openpyxl install still returns the deps error, never an
  import crash).
- **Family-1-only scope.** Per the plan's explicit deferral of the comparator driver (§10), and the
  "one family per reviewable diff" boundary, family 2 (`compare_tsn_common.py`) is not in this diff.
- **No doc edits.** Every canonical-doc mention of the loaders describes the unchanged data flow /
  `build_into` contract (e.g. "raw → normalized via `tsn_load_ramp_detail.build_into`"); none
  describe the per-module skeleton, so none are invalidated. Doc reconciliation stays P11 (plan §I).
- **Added a regression check** beyond the plan's "rely on existing checks" — see §10 (a
  strengthening for the new substrate, not scope expansion).

## 6. Compatibility and migration handling
- **No persisted-data / format / API change.** `build_into(raw_dir, out_path, events,
  confirm_overwrite)` is unchanged for all four modules; the `report_catalog` lazy builder strings
  (`tsn_load_*:build_into`) and `RAW_GLOB` are intact; the normalized workbook (sheet, header,
  styling, rows) is **semantically identical** (§7 — same sheet title, header values, header
  alignment/font/fill, and data rows; the harness compares workbook semantics, not XLSX ZIP bytes).
- **Behavior-neutral, proven.** An old-vs-new harness (`git show HEAD:` for each old module, loaded
  beside the new one) ran both `build_into` on identical synthetic input across all four loaders
  (summaries in both full and partial states) and compared the full `ConsolidateResult` (status,
  message, summary_lines, completion, skipped_inputs) AND the produced workbook (sheet title, header
  values, per-header-cell alignment/font/fill, data rows): **6/6 IDENTICAL**.
- **Producer-completion (P1-B05) preserved:** the summaries still flag PARTIAL + `skipped_inputs` on
  a missing category; the details still set no completion (consumers infer complete from
  `status="ok"`). Confirmed by both `check_tsn_outcome` (unchanged, green) and the new check.

## 7. Tests and commands run
- **Baseline @ `c86dc78`** (pre-change): `check_tsn_outcome`, `check_report_catalog`, the five
  `check_compare_*_tsn`, `check_matrix_tsn`, `check_parallel_reconcile`, `check_tsn_description_leak`
  all green; full suite **58/58**; `check_import_direction` green.
- **Behavior-identity proof — the ONE-OFF harness (§6, not committed):** all four loaders, summaries
  full + partial — `(status, message, summary_lines, completion, skipped_inputs)` and the loaded
  workbook `(sheet, rows, header alignment/font/fill)` compared old-vs-new → **6/6 semantically
  identical** (workbook semantics + result contract, not XLSX ZIP bytes).
- **The PERMANENT `build/check_tsn_normalizer.py`** — **28 assertions** (strengthened in round-1
  remediation to cover every dimension the one-off harness checked), GREEN, ASCII-clean on cp1252.
  RED-proven: a wrong header fill fails the font/fill assertions; removing the factory's ImportError
  backstop fails the P5-A01 assertion; the oldest-raw pick and dropped-`wrap_text` regressions still fail.
- **Targeted/characterization (post-change):** `check_tsn_outcome`, `check_report_catalog`, the five
  `check_compare_*_tsn`, `check_matrix_tsn`, `check_parallel_reconcile`, `check_tsn_description_leak`
  — all green.
- **Full suite + gates:** **59/59** Python; `node --check app.js`, `check_compare_routing.js`,
  `check_mx_partial_render.js`; `compileall scripts build version.py`; `check_import_direction`,
  `check_app_modules`, `check_no_misspelling`; `git diff --check` clean.

## 8. Results
All green. Family-1 DRY done with **proven semantically-identical behavior**. Suite **58 → 59** (the new
`check_tsn_normalizer`). The shared skeleton lives in one place; the four shims carry only their
report-specific glue. `compare_core` and the comparison path are untouched.

## 9. Before/after measurements
| Metric | Before (`c86dc78`) | After |
|---|---|---|
| Copies of the find/gate/write/save loader skeleton | 4 (one per `tsn_load_*`) | 1 (`tsn_library.build_normalized`) |
| Product LOC across `tsn_library` + 4 shims (diff) | — | **+235 / −280** (net −45) |
| `tsn_load_*` module sizes (lines) | 94 / 89 / 107 / 89 = 379 | 61 / 61 / 73 / 71 ≈ 266 |
| Offline Python checks | 58 | **59** (+`check_tsn_normalizer`, 28 assertions) |
| `_find_raw` duplicates | 4 | 0 (one `_newest_raw`) |
| vs-TSN canaries / comparison behavior | green | green (untouched) |

## 10. Deviations from the approved plan
- **Family 2 (`compare_tsn_common.py` comparator driver) deferred** — exactly as the plan's P5
  completion note directs (*"defer the comparator driver to a point release without affecting the
  DoD"*) and the "one family per reviewable diff" boundary. P5 is conditional/deferrable and not in
  the v0.18.0 DoD; family 1 is the "ship if time permits" deliverable. No DoD impact.
- **Added `build/check_tsn_normalizer.py`** — the plan's P5 "Tests" line relies on the existing
  vs-TSN golden checks + the COM/Route-1 harness for canary identity. I added a focused regression
  check for the *new* shared factory (the detail loaders' `build_into` and the factory's shared
  branches were otherwise unexercised offline). This is a verification strengthening for the
  substrate P5 introduces, not a scope expansion. No other deviations.

## 11. Known limitations and external verification
- **Real-source normalization is work-PC only.** Offline checks monkeypatch the projections
  (`parse_tsn_pdf` / `tsn_rows_from_raw`) and the old-vs-new identity proof uses synthetic rows; the
  real statewide PDF/XLSX parsing is unchanged (it lives in the untouched `compare_*_tsn` modules).
  The plan's **COM / Route-1 harness** on the real TSN pairs is a work-PC step (§M), not part of the
  offline DoD — but since family 1 doesn't touch the comparison path or any schema, the vs-TSN
  canaries are unaffected by construction (and stay green offline).
- **YAML lib unavailable in this environment** — `checks.yml` was not re-parsed by a YAML library
  locally (no PyYAML/js-yaml/ruby present). The edit is a single `python build/...py` line inside
  the existing `run: |` literal block with byte-matching indentation to its siblings, so it cannot
  alter YAML structure; GitHub Actions validates on push.

## 12. Exact diff scope Codex should review
Against baseline `c86dc78` (exclude `docs/planning/`):
- **`scripts/tsn_library.py`** — new `_newest_raw`, `_write_normalized_workbook`, `build_normalized`
  (the shared single-file normalizer substrate); `Events` added to the `events` import. No change to
  the registry / resolve / status / import-build paths.
- **`scripts/tsn_load_ramp_detail.py` / `_intersection_detail.py` / `_ramp_summary.py` /
  `_intersection_summary.py`** — reduced to thin shims delegating to `build_normalized`; `build_into`
  contract + `RAW_GLOB` preserved; per-report `_project` keeps the projection + result/completion.
- **`build/check_tsn_normalizer.py`** (new) — the factory regression lock (28 assertions).
- **`.github/workflows/checks.yml`** — one added blocking check line.

Key checks to re-run: `build/check_tsn_normalizer.py` (+ the RED proofs), `build/check_tsn_outcome.py`,
the five `build/check_compare_*_tsn.py`, `build/check_import_direction.py`, the full 59-check suite.
Suggested independent verification: the old-vs-new `build_into` identity harness (§7) — fetch each
old module via `git show c86dc78:scripts/<mod>.py` and compare result + workbook on synthetic input.

---

# Remediation — Codex review round 1 (`PASS WITH FIXES`)

**Round addressed:** P5 Codex review **round 1** ([`P5-codex-review.md`](P5-codex-review.md)) — verdict
`PASS WITH FIXES`, 0 blocking, **1 required** (**P5-R01**) + **1 non-blocking** (**P5-A01**). Codex
independently re-ran the six-case old-vs-new semantic harness and the shared-branch comparisons and
found **6/6 + the error/cancel/save contracts matched** — so both findings are *missing durable
tripwire / wording* issues, **not** discovered output defects. The original report body is preserved;
the demonstrably-wrong "byte-identical" phrasing and the now-stale assertion count were corrected
in place (see below), and this section records the round.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P5-R01 | required | **Fixed** | the PERMANENT `check_tsn_normalizer.py` now locks, against an independent frozen oracle, every dimension the one-off §6 harness compared — every `ConsolidateResult` field, the exact event log, sheet/header/data rows, and header alignment **+ font + fill** — for all six cases, plus the exact shared error/cancel strings and an atomic-save `PermissionError` case; the report wording corrected to **semantically identical** (not "byte-identical") and the permanent check distinguished from the one-off harness |
| P5-A01 | recommended | **Fixed (applied)** | a centralized ImportError backstop in `build_normalized` returns the shim's friendly `deps_msg` if a partial/frozen-pruned openpyxl is missing `WriteOnlyCell`/`Alignment`/`Font`/`PatternFill`, instead of crashing — plus a focused negative |

### P5-R01 — the permanent check now locks the claimed semantic identity — Fixed
**Verified real** — the round-0 `_wb` captured only sheet/values/alignment (no font/fill); the detail
cases asserted only status/completion + a "2 routes" substring + workbook shape; the summaries omitted
exact result text/warning/log; `test_shared_skeleton` used substring predicates and never exercised the
factory's `PermissionError` save block. The font/fill/exact-result coverage existed ONLY in the §6
one-off harness, so the report's "locks … result and styled workbook" claim over-stated the permanent
check. The "byte-identical" phrasing was also wrong — the harness compares workbook *semantics*, not
the XLSX ZIP bytes.

**Fix** (`build/check_tsn_normalizer.py`, rewritten; **no product change** for R01):
- A **FROZEN, independent oracle** — sheet names, the full header lists, the three header-alignment
  variants, the header font `("Arial", True, 11.0, "00FFFFFF")` and fill `("solid", "00305496")` are
  hand-written literals, NOT re-read from the kwargs the shim passes to `build_normalized` (Codex's
  independence rule). A deliberate sheet/header/style change must update them (golden tripwire).
- For **all six cases** (Ramp Detail, Intersection Detail, full + partial of both summaries) the check
  asserts: every `ConsolidateResult` field (status, exact message, exact summary_lines incl. the
  PARTIAL `⚠ INCOMPLETE …` warning, completion, skipped_inputs); the **exact emitted event-log line**
  (via `Events(on_log=…)`); the sheet title, header row, and every data row (details = the verbatim
  projected rows; summaries = one `[key, count]` row per category, **distinct fed counts**, in order,
  missing → 0); and **every header cell's alignment AND font AND fill**.
- The shared skeleton now asserts the **exact** deps / missing-raw (+ raw_dir + hint) / cancelled /
  parse-error strings, the **atomic-save `PermissionError` contract** (friendly message, prior artifact
  retained, no stray file from the factory), the newest-by-mtime pick, and the `~$` lock skip.
- RED-proven (revert/run/restore + in-memory): a wrong header fill → the font/fill assertions fail
  (rc 1); removing the factory's ImportError backstop → the P5-A01 assertion fails (rc 1); the prior
  oldest-pick / dropped-`wrap_text` regressions still fail.
- Report wording corrected in place: 4× "byte-identical"/"byte-for-byte" → **semantically identical**
  (with the compared dimensions named); §3/§7 now describe the permanent 28-assertion check and
  distinguish it from the §6 one-off old-vs-new harness.

### P5-A01 — dependency-gate coverage for the factory's workbook symbols — Fixed (applied)
**Verified real** — each shim probes only `from openpyxl import Workbook`, but
`tsn_library._write_normalized_workbook` also imports `WriteOnlyCell` / `Alignment` / `Font` /
`PatternFill`; the baseline loaders' gates covered the style classes (and the Intersection loaders
covered `WriteOnlyCell`). A partial/frozen-pruned openpyxl could pass `_DEPS_OK` then raise instead of
returning the friendly dependency result.

**Fix** (`scripts/tsn_library.py`): `build_normalized` now wraps the workbook build in
`try: _write_normalized_workbook(...) except ImportError: return ConsolidateResult(status="error",
message=deps_msg)`. This is the **centralized** option Codex preferred (one backstop in the factory,
not four restored writing skeletons), so any missing workbook symbol degrades to the shim's existing
`deps_msg`. A focused negative (`_write_normalized_workbook` patched to raise `ImportError`) proves the
backstop, RED-confirmed by revert/run/restore.

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_tsn_normalizer.py` | rewritten — frozen independent oracle; full per-case signature (result + event log + sheet/header/rows + alignment/font/fill); exact shared error/cancel strings; atomic-save `PermissionError` case; P5-A01 ImportError-backstop negative. 26 → **28** assertions. |
| `scripts/tsn_library.py` | `build_normalized` ImportError backstop → friendly `deps_msg` (P5-A01) |
| `docs/planning/v0.18.0/phases/P5-claude-report.md` | "byte-identical" → "semantically identical" (4×); permanent check vs one-off harness distinguished; assertion count 26 → 28; this section |

No shim changed this round; the four `tsn_load_*` shims, `compare_core`, the `compare_*_tsn`
comparators + schemas, the matrix `row_key`, auth, updater-TLS, `version.py`, `app.js`, and `app.spec`
are untouched.

## Updated verification

```
python build/check_tsn_normalizer.py            # 28 assertions, ALL GREEN (ASCII-clean on cp1252)
   frozen-oracle signature for all 6 cases (result + event log + sheet/header/rows + align/font/fill),
   exact shared error/cancel strings, atomic-save PermissionError contract, P5-A01 backstop negative
RED proofs: wrong header fill -> font/fill FAIL (rc 1); backstop removed -> P5-A01 FAIL (rc 1, restored)
PYTHONIOENCODING=utf-8  python build/check_*.py  (x59)            # 59/59
check_tsn_outcome + the 5 check_compare_*_tsn + check_matrix_tsn + check_parallel_reconcile
   + check_tsn_description_leak                                  # green (comparison path untouched)
node --check app.js + compileall + import_direction + app_modules + no_misspelling + git diff --check  # OK
```

## Changed measurements

| Metric | Round 0 | After round-1 remediation |
|---|---|---|
| `check_tsn_normalizer` assertions | 26 | **28** |
| Permanent-check dimensions | sheet/header/rows + alignment + status/completion + branch substrings | + **font + fill**, exact message/summary_lines/event-log, exact error/cancel strings, atomic-save `PermissionError`, ImportError backstop — vs an **independent frozen oracle** |
| `build_normalized` dependency safety | `_DEPS_OK` (Workbook probe) only | + centralized ImportError backstop for the style/cell symbols (P5-A01) |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 2). Not committed;
planning folder untracked.

---

# Remediation — Codex review round 2 (`PASS WITH FIXES`)

**Round addressed:** P5 Codex review **round 2** ([`P5-codex-review.md`](P5-codex-review.md)) — verdict
`PASS WITH FIXES`, 0 blocking, **1 required** (**P5-R01**, narrowed to the save-error tripwire), 0 new
recommendations. **P5-A01 confirmed Resolved** by Codex (the `build_normalized` ImportError backstop +
its negative). Codex's independent diagnostic (driving the real `atomic_save` via a raising `os.replace`)
preserved the prior artifact and left no temp — so this is still a missing/noisy tripwire, **not** a
product defect. The original report + round-1 remediation are preserved.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P5-R01 | required (narrowed) | **Fixed** | the permanent save-error test now drives the REAL `artifact_store.atomic_save` (forces `os.replace` to raise) — proving the prior artifact is retained AND the `.tmp-*` sibling is cleaned in the OUTPUT dir — and exits with NO ignored openpyxl/lxml cleanup exceptions |
| P5-A01 | recommended | **Resolved (Codex)** | no action — the factory ImportError backstop + its negative were confirmed resolved |

### P5-R01 (round 2) — the save-error tripwire now exercises the real atomic-save contract — Fixed
**Verified real.** The round-1 test patched `artifact_store.atomic_save` itself to raise immediately,
which (a) bypassed the implementation whose temp cleanup it claimed to prove
(`artifact_store.atomic_save` writes the workbook to a `.tmp-<token>` sibling of `out_path`, then
`os.replace`, and `_silent_unlink`s the temp on any exception — `scripts/artifact_store.py:81-96`),
(b) asserted "no stray file" against `raw.iterdir()` — the INPUT folder, while temps are created beside
`out_path` — and (c) left a write-only workbook unsaved, so openpyxl/lxml emitted ignored atexit cleanup
exceptions AFTER the pass banner (making the "all green / ASCII-clean" claim misleading).

**Fix** (`build/check_tsn_normalizer.py`, the save-error case only — no product change):
- The test now keeps the REAL `atomic_save` and instead patches `artifact_store.os.replace` to raise
  `PermissionError`. So `atomic_save` runs for real: it saves the workbook to a `.tmp-*` sibling of the
  output path (consuming/closing the write-only workbook → **no atexit noise**), `os.replace` raises,
  `_silent_unlink` removes the temp, the exception propagates, and the factory's `except PermissionError`
  returns the exact friendly message.
- It writes the prior output into a **dedicated output dir** and asserts: the exact "probably open in
  Excel" message; the prior output **bytes are retained**; and that dir contains **only** the prior
  file — i.e. **no `.tmp-*` sibling** remains (checking the OUTPUT dir, where temps actually live).
- RED-proven: with `atomic_save`'s temp cleanup disabled (`_silent_unlink` → no-op), a real
  `keep.tmp-<token>.xlsx` survives and the "no `.tmp-*` sibling" assertion fails — so the test genuinely
  exercises the real save path and would catch a cleanup regression.
- Verified clean exit: `python build/check_tsn_normalizer.py` exits 0 with an **empty stderr** (the
  openpyxl/lxml atexit exceptions are gone).

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_tsn_normalizer.py` | the atomic-save `PermissionError` case rewritten to drive the REAL `artifact_store.atomic_save` (patch `artifact_store.os.replace`), assert prior-bytes-retained + no `.tmp-*` in the output dir, and exit with no atexit noise; the exact friendly-message assertion kept |
| `docs/planning/v0.18.0/phases/P5-claude-report.md` | this section |

**No product change this round** — only the check's save-error case. The 4 `tsn_load_*` shims,
`tsn_library` (incl. the P5-A01 backstop), `compare_core`, the `compare_*_tsn` comparators, `app.spec`,
and CI wiring are untouched. `check_tsn_normalizer` stays **28** assertions (the save case is the same
two assertions, now genuinely exercising the real path).

## Updated verification

```
python build/check_tsn_normalizer.py            # exit 0, 28 assertions GREEN, STDERR EMPTY (no
   openpyxl/lxml atexit noise); the save-error case drives the real atomic_save via a raising os.replace
RED proof: atomic_save temp-cleanup disabled (_silent_unlink no-op) -> a real keep.tmp-*.xlsx survives
   -> the 'no .tmp-* sibling' assertion fails (so the tripwire catches a cleanup regression)
PYTHONIOENCODING=utf-8  python build/check_*.py  (x59)            # 59/59
check_tsn_outcome + the 5 check_compare_*_tsn + check_matrix_tsn + check_parallel_reconcile
   + check_tsn_description_leak + check_report_catalog + check_report_library                # green
node --check app.js + compileall + import_direction + app_modules + no_misspelling + git diff --check  # OK
```

## Changed measurements

| Metric | Round 1 | After round-2 remediation |
|---|---|---|
| Save-error tripwire | patched `atomic_save` to raise (bypassed the real path); checked the raw dir | drives the REAL `atomic_save` via a raising `os.replace`; checks the OUTPUT dir for a leaked `.tmp-*` |
| Check stderr | ignored openpyxl/lxml atexit exceptions after the pass banner | **empty** (clean exit) |
| `check_tsn_normalizer` assertions | 28 | 28 (save case strengthened in place) |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 3). Not committed;
planning folder untracked.
