# P4 — Report metadata catalog (narrowed) + .bat fix + parity — Claude report

## 1. Phase ID and name
**P4** — Report metadata catalog (narrowed) + `.bat` fix + parity `[blocking; depends P3, PA]`

## 2. Baseline commit
`5defe9e` (HEAD after P3 committed). Baseline: **57** offline golden checks + 2 Node frontend
checks green, byte-compile + `node --check app.js` green, tree clean apart from the untracked
`docs/planning/` workspace. Dependencies **P3 committed** (`5defe9e`, the stable-ID taxonomy this
phase builds on) and **PA committed** (`65aef98`, the packaging-reachability gate `check_app_modules`
that stays the independent packaging contract).

## 3. Changes made
P4 makes **one place own the report metadata** and closes the console-menu drift, **without changing
any behavior** — the derived registry lists, keys, and TSN descriptors are proven equal to the v0.17
baseline.

1. **New `scripts/report_catalog.py`** — the report-metadata **single source of truth** (R1-B05/D02).
   It owns *only* report/capability metadata + the report-module references: the ordered EXPORT (7) /
   CONSOLIDATE (8) / COMPARE (15) op descriptors (each carrying its stable `cmp:*`/`cons:*`/family key,
   display label, format/kind/group, and the module/adapter it runs), the `COMPARE_GROUPS`, the
   auto-consolidator-by-subdir map, and the 6 TSN library descriptors (with the lazy `module:function`
   builder strings). It imports the thin `export_*`/`consolidate_*`/`compare_*` modules (moved here from
   `reports.py`) so a frozen build collects them; the TSN builders stay strings so the catalog doesn't
   ALSO import the `tsn_load_*` normalizers eagerly. It is console-free (importing does no runtime I/O)
   but **not** dependency-light — it pulls openpyxl/pdfplumber/playwright via those implementation
   modules, exactly as the literal registry always did. It does **not** own packaging reachability or
   any test oracle. *(P4-R04 corrected: the original draft wrongly said importing "never pulls
   pdfplumber/openpyxl".)*
   Import-time asserts lock its own invariants (keys unique, export key == spec subdir).
2. **`scripts/reports.py` — now a VIEW** over `report_catalog`. `EXPORT_REPORTS` / `EXPORT_KEYS` /
   `CONSOLIDATE_REPORTS` / `CONSOLIDATE_KEYS` / `COMPARE_GROUPS` / `COMPARE_REPORTS` / `COMPARE_KEYS` /
   `_CONSOLIDATOR_BY_SUBDIR` are derived from the catalog accessors; the registry **logic** stays here
   (the app-wide disable gate, `matrix_rows`, `enabled_export_reports`/`export_reports_status`, the P3
   stable-ID lookups, the integrity asserts). Public API unchanged — every consumer keeps reading the
   same names/shapes.
3. **`scripts/tsn_library.py` — `_REPORTS` derived** from `report_catalog.tsn_entries()` (one source for
   each report's TSN descriptor); all TSN logic (resolve/build/status/import) is untouched.
4. **`4. consolidate (combine reports).bat` — the R1-M01 fix.** Added the two missing **Intersection**
   consolidators (Summary + Detail) and reordered the menu to match the registry exactly (8 options).
5. **`build/app.spec`** — `APP_MODULES += "report_catalog"` (the new flat module is a runtime import;
   `check_app_modules`'s F6 completeness contract requires every flat module declared).
6. **New `build/check_report_catalog.py`** — the parity gate: (a) **DERIVE** — `reports.py`/`tsn_library`
   expose exactly the catalog views; (b) **GOLDEN EQUIVALENCE** — the catalog metadata + keys + TSN
   descriptors equal a **FROZEN v0.17 baseline literal** hand-written in the check (an independent
   approved snapshot, R1-R13) → behavior-neutral; (c) **.BAT PARITY** — the console menu covers exactly
   the registry's consolidators (R1-M01); (d) **DYNAMIC-IMPORT RESOLVABILITY** — every lazy TSN builder
   module resolves (R1-T05); (e) **MOCK PARITY** — the `#mock` export/consolidate/compare key lists match
   the catalog, in order (the backend-snapshot vs frontend-expectation check, R1-R13/CT-13).
7. **CI wiring** (`.github/workflows/checks.yml`) — `check_report_catalog` added (blocking).
8. **Docs** — the P4-invalidated statements corrected narrowly (the SoT is now the catalog; the
   consolidate `.bat` has a parity check, not "hand-edited"): `docs/architecture.md` (the registry
   section), `docs/reports.md` (the intro + the add-a-report/consolidator recipes), `CLAUDE.md` (the
   repo-layout line). Broader doc reconciliation stays P11.

## 4. Files affected
**New (2):** `scripts/report_catalog.py`, `build/check_report_catalog.py`.
**Modified product (4):** `scripts/reports.py`, `scripts/tsn_library.py`, `build/app.spec`,
`4. consolidate (combine reports).bat`.
**Modified CI (1):** `.github/workflows/checks.yml`.
**Modified docs (3):** `docs/architecture.md`, `docs/reports.md`, `CLAUDE.md`.
**Untouched:** `compare_core.py` (regression-locked), the updater/TLS, auth, `version.py`,
`scripts/ui/*` (the `#mock` is read for parity, never changed), the matrix `row_key`, and the
**independent** fake-site fixtures + approved snapshots.

## 5. Architectural decisions
- **Catalog is the import hub; `reports.py`/`tsn_library` are views.** The `export_*`/`consolidate_*`/
  `compare_*` imports moved into `report_catalog`, which is cycle-safe — none of those leaf modules
  imports `reports`/`tsn_library`/`report_catalog` (verified; `check_import_direction` stays green).
  This makes the catalog a genuine SoT (one place to edit), not a parallel list kept in sync.
- **Derive, with a golden snapshot as the safety net.** Per the Protected contract ("derived
  EXPORT/CONSOLIDATE/COMPARE order + keys equal today's, golden-assert before/after"), the lists are
  *derived*; the frozen v0.17 baseline in `check_report_catalog` is the **independent** approved
  snapshot (R1-R13) that proves equality. Both the derive check (catalog→reports) and the golden check
  (catalog→frozen) must hold — the golden was proven to catch a catalog drift the derive alone would not.
- **Catalog scope is metadata-only (R1-B05/D02/D05).** Packaging reachability remains
  `check_app_modules` + the frozen `--self-test` gate; the test oracles (fake-site fixtures, the
  `check_report_catalog` baseline) are hand-written, independent of the catalog — never self-validating.
- **`.bat` parity = coverage, ordered to the registry.** The console menu is a convenience surface; the
  check enforces it references exactly the registry's `consolidate_*` modules (no missing/stray), and
  the menu is ordered to the registry for clarity. The Intersection drift is the concrete R1-M01 fix.
- **Mock parity is a CHECK, not codegen.** The plan's "mock report list generated" is realized as a
  backend-vs-frontend parity check: the `#mock`'s export/consolidate/compare/group lists must equal the
  REAL bridge payload **field-for-field** — export `(key, idx, label, fmt, disabled)`, consolidate
  `(key, label, fmt)`, groups `(id, label)`, compare `(key, label, kind, group, file_a_label,
  file_b_label)` — plus the mock's separate `CONS_REPORTS` routing list and a `subdir` cross-check
  (strengthened in P4-R03/round 2). The bridge payload comes from a PURE `gui_api._report_list_payload()`,
  so the check constructs no `GuiApi` and does no I/O (P4-R05). This is P4's report-list **metadata**
  parity; the fuller P9 frontend-renderer CT-13 stays P9's scope (see §10).

## 6. Compatibility and migration handling
- **No persisted-data / format change.** P4 is a pure internal refactor: no `batch_job.json`, cache,
  config, auth, or output-layout touch. Every public registry name/shape (`EXPORT_REPORTS`,
  `CONSOLIDATE_REPORTS`, `COMPARE_REPORTS`, `COMPARE_GROUPS`, the `*_KEYS`, `matrix_rows`,
  `consolidator_for_*`, the stable-ID lookups) is unchanged, so every consumer (gui_api, gui_worker,
  matrix, day_matrix, export_multi, the bridges) keeps working byte-for-byte.
- **Backwards/rollback:** additive new module + view derivation; reverting P4 restores the literal
  lists with no data implications. The golden baseline makes any future catalog edit a deliberate,
  reviewed change (update the catalog AND the frozen snapshot together).
- **Packaging:** `report_catalog` is declared in `APP_MODULES`; `check_app_modules` (offline) + the
  frozen `--self-test` gate carry it into the bundle.

## 7. Tests and commands run
```
# pre-change characterization (green at 5defe9e):
python build/{check_report_library,check_matrix,check_intersection_gate,check_b3_batch,
              check_gui_bridge,check_stable_ids,check_app_modules,check_matrix_tsn,
              check_consolidate_intersection}.py     # all OK

# new check:
python build/check_report_catalog.py          # 24 assertions — derive, golden-equivalence,
                                              # .bat parity, dynamic-import resolvability, mock parity

# RED proofs (revert/run/restore):
#  - .bat parity: point one menu entry at a non-registry module -> 3 parity assertions FAIL
#    (missing intersection_summary + stray); restored -> green.
#  - golden guard: mutate a catalog label -> GOLDEN fails (catalog != frozen baseline) while DERIVE
#    still passes (reports follows the catalog) -> proves the golden is the independent drift guard;
#    restored -> green.

python -m compileall -q scripts build version.py        # OK
node --check scripts/ui/app.js                          # OK (app.js unchanged this phase)
node build/check_mx_partial_render.js                   # OK
node build/check_compare_routing.js                     # OK
python build/check_import_direction.py                  # OK — NO cycle from the report_catalog hub
python build/check_app_modules.py                       # OK — report_catalog declared (F6)
python build/check_no_misspelling.py                    # OK (docs touched)
PYTHONIOENCODING=utf-8  python build/check_*.py  (×58, excl. fake_site/source_zip)  # 58/58
git diff --check -- . ':(exclude)docs/planning/**'      # clean; no REVERT-PROOF marker survives
```

## 8. Results
- **58/58** offline Python suite (57 → 58 with `check_report_catalog`) + 2 Node frontend checks +
  byte-compile + `node --check` + import-direction + app_modules + no-misspelling + diff-check all
  green; no `REVERT-PROOF` marker.
- The catalog's derived EXPORT/CONSOLIDATE/COMPARE lists + keys + the consolidator map + the TSN
  descriptors are proven **identical** to the v0.17 baseline — the consolidation is behavior-neutral.
- The console consolidate menu now covers all 8 registry consolidators (the Intersection drift closed),
  enforced by the parity check; the `#mock`'s key lists are proven to match the catalog.
- `compare_core` / updater-TLS / auth / `app.js` / matrix `row_key` / the fake-site oracle untouched.

## 9. Before/after measurements
| Metric | Before (`5defe9e`) | After (P4) |
|---|---|---|
| Report-metadata source of truth | 3 hand-maintained places (`reports.py` lists + `tsn_library._REPORTS` + the mock, with the `.bat` separate) | **1** (`report_catalog.py`); the rest derive/are parity-checked |
| `scripts/reports.py` | 408 lines (registry literals + logic) | **232** lines (view + logic); `report_catalog.py` +267 |
| `tsn_library._REPORTS` | a 50-line literal dict | derived from the catalog |
| Console consolidate menu | 6 options (Intersection MISSING) | **8** (Intersection added; registry-ordered) |
| Offline golden checks | 57 | **58** (+`check_report_catalog`, 24 assertions) |
| `.bat`↔registry coverage | unchecked (drifted) | enforced (R1-M01) |

No hot-path change: the catalog is imported once at startup (the same modules as before), and the view
accessors build their lists once at import — negligible. (R1-A01 cold-start/matrix baselines from P0
§8 are unaffected; P4 touches no export/matrix loop.)

## 10. Deviations from the approved plan
1. **Mock report list is parity-CHECKED, not build-time GENERATED.** The plan's "mock report list
   generated" is realized as a backend-vs-frontend parity check (the `#mock` lists == the REAL
   `gui_api.get_initial_state` bridge payload, **field-for-field** after P4-R03) rather than a JS-codegen
   step. Generating the JS mock from the Python catalog at build time would add a toolchain step for a
   hand-maintained preview; the field-level parity gives the same drift protection. This is P4's
   report-list metadata parity — **not** the full P9 CT-13 frontend-renderer payload, which stays P9.
   Flagged rather than silently skipped.
2. **TSN descriptors fully derived (not just asserted).** The plan said `tsn_library._REPORTS`
   "derived-OR-asserted"; I derived (the descriptors now live in the catalog), the fuller "one SoT".
3. **Three canonical-doc statements corrected here** (the registry SoT + the "`.bat` hand-edited" claim
   in `architecture.md`/`reports.md`/`CLAUDE.md`) — only what P4 directly invalidated, per the P3-R01
   precedent. `lessons.md` / `compare-core.md` still say "`reports.py` registry," which stays accurate
   (it exposes the registry, now derived); their reconciliation stays P11.

## 11. Known limitations & external verification
- **No work-PC verification required for P4** — every change is offline-verifiable (the golden/parity
  check + the full suite). P4 touches no live auth/browser/export path; `app.js` is unchanged, so the
  `#mock` boot is the same as P3's verified state (the parity check confirms the mock data still
  matches the registry).
- The frozen baseline in `check_report_catalog` must be updated alongside any future catalog edit
  (by design — it makes metadata changes deliberate). The `.bat` parity check covers the **consolidate**
  menu; the `3. run_export`/`5. fast export` `.bat` branch coverage is not yet parity-checked (out of
  scope — R1-M01 named the consolidate drift specifically).

## 12. Exact diff scope for Codex to review
- `scripts/report_catalog.py` — the new SoT: the ordered EXPORT/CONSOLIDATE/COMPARE/TSN descriptors +
  keys + the accessors + the auto-consolidator map + the import-time integrity asserts. Confirm it owns
  metadata only (no packaging/oracle logic) and is console-free (importing does no runtime I/O; it is
  **not** dependency-light — it eagerly imports the report implementation modules).
- `scripts/reports.py` — now derives every registry name from the catalog; the logic (disable gate,
  `matrix_rows`, stable-ID lookups, asserts) is byte-for-byte the prior behavior over the derived data.
- `scripts/tsn_library.py` — `_REPORTS` derived from `report_catalog.tsn_entries()`; all TSN logic
  unchanged.
- `build/check_report_catalog.py` — the derive + **golden-equivalence (frozen v0.17 baseline)** + .bat
  parity + dynamic-import resolvability + mock parity (note the two RED proofs).
- `4. consolidate (combine reports).bat` — the two Intersection consolidators added + registry-ordered.
- `build/app.spec` — `APP_MODULES += "report_catalog"` (F6 completeness).
- `.github/workflows/checks.yml` — one added invocation.
- `docs/architecture.md`, `docs/reports.md`, `CLAUDE.md` — the narrow P4-invalidated wording.

`git diff --stat` vs `5defe9e`: 8 files changed (+116/−309) + 2 new files; `docs/planning/` not staged.
Suggested review order: `report_catalog.py` (the SoT) → `reports.py`/`tsn_library.py` (the derivation)
→ `check_report_catalog.py` (the golden/parity gate) → the `.bat` + `app.spec` → docs.

---

# Remediation — Codex review round 1 (`PASS WITH FIXES`)

**Round addressed:** P4 Codex review **round 1** ([`P4-codex-review.md`](P4-codex-review.md)), verdict
`PASS WITH FIXES` — 0 blocking, **4 required (P4-R01..R04)**, 0 recommendations. Every finding was
verified real against the workspace before fixing (no product routing/persistence/packaging defect was
found — the findings are that the *checks proved less than claimed* and several *claims contradicted the
implementation*). The original report above (with its four false/over-claimed sentences corrected
in-place and flagged) is preserved; this section records the remediation.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P4-R01 | required | **Fixed** | golden equivalence now pins each export key's exact `ReportSpec`, each comparison key's adapter, each consolidate op's module, and each auto-consolidator's module by **object identity** against an independent oracle the check imports itself; TSN builders resolve via `import_module`+`getattr`+`callable`; + negative self-tests |
| P4-R02 | required | **Fixed** | `.bat` parity now asserts the **ordered** chain `choice → goto → block → module` == registry order (+ uniqueness/reachability), with a negative swapped-dispatch case |
| P4-R03 | required | **Fixed (with modification)** | mock parity now compares the `#mock` lists to the **REAL bridge** (`get_initial_state`) **field-for-field** (label/format/kind/group/id), not keys; the report's CT-13/P9 over-claim corrected |
| P4-R04 | required | **Fixed** | the false "never pulls pdfplumber/openpyxl" / "import-light" claims removed from `report_catalog`, `reports`, `tsn_library`, the check, `architecture.md`, and the phase report; 3 stale `reports.md` recipe/fact lines fixed |

### P4-R01 — descriptor equivalence now pins execution identity — Fixed
**Verified real** — reproduced Codex's diagnostic: swapping the first comparison adapter (same
key/label/kind/group) produced zero DERIVE/GOLDEN failures. The frozen baseline recorded metadata only;
`_CONSOLIDATOR_BY_SUBDIR` compared catalog→catalog; the dynamic check did only `find_spec(module)`.
**Fix:** `check_report_catalog` now **imports the expected spec/adapter/consolidate objects itself** (an
independent oracle) and asserts by object identity (`is`) that the catalog's EXPORT spec, COMPARE
adapter, CONSOLIDATE module, and each auto-consolidator subdir's module are exactly those. TSN builders
resolve via `import_module` + `getattr` + `callable`. Four **negative self-tests** prove the tripwires
(wrong adapter / wrong auto-consolidator / wrong spec / missing function each fail). **Live RED proof:**
re-pointing `COMPARE[0]`'s adapter to Ramp Detail now fails "COMPARE adapter IDENTITY" while DERIVE still
passes — exactly Codex's diagnostic, now caught.

### P4-R02 — `.bat` parity now checks ordered dispatch — Fixed
**Verified real** — set-comparison missed a swapped `goto`. **Fix:** the check parses the ordered chain
(menu number → `goto` target → label block → Python module), asserts it equals `cat.CONSOLIDATE` order
(plus unique gotos/blocks + reachability), and a negative self-test swaps the choice-4/5 gotos and
confirms the chain mismatches.

### P4-R03 — mock parity now full-field vs the bridge — Fixed (with modification)
**Verified real** — key-only parity missed label/format/kind/group drift. **Fix:** the mock parity now
builds the REAL backend snapshot from `gui_api.GuiApi().get_initial_state()` and compares the `#mock`'s
export `(key,label,fmt)`, consolidate `(key,label,fmt)`, groups `(id,label)`, and compare
`(key,label,kind,group)` lists **field-for-field**. The deviation stays a parity-check (not JS codegen)
but is now genuinely field-equivalent; the phase report's framing is corrected so it is **not** presented
as the completed P9 CT-13 frontend-renderer payload.

### P4-R04 — truthful dependency-boundary docs — Fixed
**Verified real** — `import report_catalog` loads openpyxl/pdfplumber/playwright/PIL (705 modules, ~1s).
**Fix:** removed the false "never pulls pdfplumber/openpyxl" / "import-light" claims from
`report_catalog.py` (docstring + TSN comment), `reports.py`, `tsn_library.py` (which now also imports
`report_catalog`, so no longer dependency-light), `check_report_catalog.py`, `docs/architecture.md`, and
the phase report — each now says **console-free** (no runtime I/O at import) but **not dependency-light**.
Fixed the three P4-invalidated `docs/reports.md` lines: the add-a-comparison recipe → add a `CompareEntry`
to `report_catalog.py`; the TSN recipe → add a `TsnEntry`; "Intersection Summary's consolidator … still to
come" → it is registered (`consolidate_intersection_summary`).

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_report_catalog.py` | independent identity oracles + ordered `.bat` chain + full mock-vs-bridge parity + `import_module`/`getattr` dynamic check + 4 negative self-tests; ASCII-clean output (so it passes on cp1252 stdout too, not only under `PYTHONIOENCODING=utf-8`) |
| `scripts/report_catalog.py` | docstring + TSN comment: drop the false no-pdfplumber/openpyxl claim; say console-free / not dependency-light (R04) |
| `scripts/reports.py` | docstring: console-free, not dependency-light (R04) |
| `scripts/tsn_library.py` | docstring: now imports `report_catalog` → console-free but not dependency-light (R04) |
| `docs/architecture.md` | the import-light claim → console-free / not-dependency-light (R04) |
| `docs/reports.md` | the 3 stale lines: `CompareEntry`/`TsnEntry` recipes + Intersection Summary registered (R04) |
| `docs/planning/v0.18.0/phases/P4-claude-report.md` | corrected the false no-openpyxl + CT-13 over-claims in the body (R03/R04) |

No **product behavior** changed — the catalog data is byte-identical; only the CHECK got stronger and the
CLAIMS got truthful. `compare_core` / auth / updater-TLS / `version.py` / `app.js` / matrix `row_key`
untouched; no new files added (every touched file was already in the P4 changeset).

## Updated verification

```
PYTHONIOENCODING=utf-8  python build/check_report_catalog.py   # 37 assertions (was 24) — derive,
   golden-equivalence + execution IDENTITY, 4 negative self-tests, ordered .bat dispatch chain,
   dynamic-import (import_module+getattr+callable), full mock-vs-bridge parity — ALL GREEN
python build/check_report_catalog.py  (no env override)        # ALSO green (ASCII-clean on cp1252)
PYTHONIOENCODING=utf-8  python build/check_*.py  (×58)          # 58/58
node --check scripts/ui/app.js + 2 Node renderers              # OK
python build/{check_import_direction,check_app_modules,check_no_misspelling}.py   # OK
python -m compileall -q scripts build version.py               # OK
git diff --check -- . ':(exclude)docs/planning/**'             # clean; no REVERT-PROOF marker
residual "never pulls pdfplumber/openpyxl" / "import-light" sweep (source + check + canonical docs)  # none
```

RED proofs (revert/run/restore): the COMPARE adapter-identity tripwire (wrong adapter → GOLDEN fails,
DERIVE still passes); the four negative self-tests and the swapped-dispatch case are permanent in-check
tripwires (no separate revert needed — they assert the wrong cases fail every run).

## Changed measurements

| Metric | P4 (pre-remediation) | After round-1 remediation |
|---|---|---|
| `check_report_catalog` assertions | 24 (metadata only) | **37** (+ execution identity, ordered dispatch, full mock parity, 4 negative self-tests) |
| Golden equivalence | metadata-only (missed a wrong adapter/consolidator) | + exact spec/adapter/module **IDENTITY** vs an independent oracle |
| `.bat` parity | module **set** (missed a swapped dispatch) | ordered **choice→module chain** |
| Mock parity | key-only (missed label/fmt/kind/group) | **full field** vs the real bridge |
| Dependency-boundary docs | claimed "never pulls pdfplumber/openpyxl" (false) | accurate: console-free, **not** dependency-light |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 2). Not committed;
planning folder untracked.

---

# Remediation — Codex review round 2 (`PASS WITH FIXES`)

**Round addressed:** P4 Codex review **round 2** ([`P4-codex-review.md`](P4-codex-review.md)), verdict
`PASS WITH FIXES` — 0 blocking, **5 required** (P4-R01..R04 *partially resolved* from round 1 + a new
**P4-R05**). Every finding verified real against the workspace before fixing (no product defect — the
findings are that the strengthened guards still accepted concrete bad variants, the dependency sweep
missed three statements, and the new mock check did shared runtime writes + started threads). The
original report + round-1 remediation are preserved; this records round 2.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P4-R01 | required | **Fixed** | the negative self-tests now run mutated catalog inputs THROUGH the production identity helpers (wrong adapter/spec/module/auto-consolidator/missing-fn each asserted rejected), not "two known objects differ" |
| P4-R02 | required | **Fixed** | `.bat` parse is now ordered + label-aware + no-dict-collapse: exactly-one dispatch + unique blocks + displayed-label check + FIRST-match chain, with negatives for a wrong label, duplicate dispatch, duplicate block, and swapped goto |
| P4-R03 | required | **Fixed** | mock parity is now FIELD-FOR-FIELD vs the pure bridge payload (export key/idx/label/fmt/disabled; cons key/label/fmt; groups id/label; compare key/label/kind/group/file_a/file_b) + the separate `CONS_REPORTS` routing list == registry + the bridge `subdir` cross-checked + negatives |
| P4-R04 | required | **Fixed** | the 3 missed statements corrected — `gui_api.py:2185`/`:2579` "(no pdfplumber pull)" + `docs/architecture.md:352-353` — to distinguish lazy builder *invocation* from eager dependency import |
| P4-R05 | required | **Fixed** | extracted a PURE `_report_list_payload()` (no `GuiApi` → no `ensure_layout` writes, no thread starts); the check calls it; `test_no_side_effects` guards it; the I/O description corrected |

### P4-R01 — negative self-tests now exercise the production predicates — Fixed
**Verified real** — mutating `cat.COMPARE[0]` left all four old self-tests green (they only asserted that
two known-unrelated objects differ). **Fix:** factored the identity/resolution into helpers
(`_compare_adapters_match` / `_export_specs_match` / `_consolidate_modules_match` / `_auto_cons_match` /
`_builders_callable`); the production assertions AND the negatives call the SAME helpers, and the
negatives pass a wrong-adapter, wrong-spec, wrong-module, wrong-auto-consolidator, and missing-function
input (via `namedtuple._replace`) asserting rejection.

### P4-R02 — `.bat` parity now ordered, label-aware, no collapse — Fixed
**Verified real** — wrong displayed label, a first-wrong+correct duplicate dispatch, and a
first-wrong+correct duplicate block all passed (dict collapse hid them). **Fix:** `_parse_bat` returns
ORDERED occurrence lists; the check asserts exactly-one dispatch per choice, unique blocks, displayed
labels start with the registry label (in order), and the **FIRST-match** chain (CMD semantics) ==
`cat.CONSOLIDATE`. Negatives for a wrong label, a duplicate/first-wrong dispatch, a duplicate/first-wrong
block, and a swapped goto.

### P4-R03 — mock parity is field-for-field + the second routing list — Fixed
**Verified real** — a changed `file_a_label`, `disabled`, or separate-`CONS_REPORTS` label all passed.
**Fix:** the parity now compares the `#mock` to the PURE bridge payload field-for-field — export
`(key, idx, label, fmt, disabled)` (idx from position, `disabled` from the `.map` literal), consolidate
`(key, label, fmt)`, groups `(id, label)`, compare `(key, label, kind, group, file_a_label, file_b_label)`
with documented defaults. It asserts the mock's SEPARATE `CONS_REPORTS` routing list `(key, label)` ==
the registry, and cross-checks the bridge `subdir` (== the key family for folders, `None` for files).
`subdir` is bridge-only — the frontend resolves folders via `get_compare_folders` and never reads
`compare_reports[].subdir` (confirmed) — so it isn't in the mock; documented. Negatives prove each
compared field participates.

### P4-R04 — the 3 missed dependency-boundary statements — Fixed
**Verified real** — `gui_api.py:2185`/`:2579` "(no pdfplumber pull)" and `docs/architecture.md:352-353`
still claimed a lazy `tsn_library` import avoids pdfplumber, but P4 makes `tsn_library` import
`report_catalog` (eager pdfplumber). **Fix:** the gui_api comments now read "lazy import (tsn_library
pulls pdfplumber via report_catalog)"; the architecture line distinguishes lazy builder *invocation*
from the eager dependency import (console-free but not dependency-light). A targeted re-sweep confirms
no residual "(no pdfplumber pull)" / "never pulls pdfplumber" claim in source or the canonical docs.

### P4-R05 — the check no longer mutates state or starts threads — Fixed
**Verified real** — `gui_api.GuiApi()` calls `tsn_library.ensure_layout()` (writes the TSN library
skeleton: dirs + README/hint files) and starts the `gui-pump`/`gui-send` threads; `_started = True`
after construction doesn't undo that. **Fix:** extracted a PURE module-level
`gui_api._report_list_payload()` (the report-list builders, no `self` / I/O); `get_initial_state` spreads
it (behavior-neutral — `check_gui_bridge` / `check_intersection_gate` stay green); the parity check calls
the pure function directly and NEVER constructs `GuiApi`. A new `test_no_side_effects` patches
`tsn_library.ensure_layout`, `threading.Thread.start`, and `GuiApi.__init__` and asserts the parity path
calls each **0** times (and `threading.active_count()` is unchanged). The check's docstring now accurately
says it does no filesystem write / thread start / browser-network / GuiApi construction (it does import
the report modules to build the oracle).

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_report_catalog.py` | rewritten — helper-based identity + real mutated-input negatives (R01); ordered/label-aware/no-collapse `.bat` parse + 6 negatives (R02); field-for-field mock parity vs the pure payload + `CONS_REPORTS` + `subdir` cross-check + 3 negatives (R03); `test_no_side_effects` + corrected I/O docstring (R05) |
| `scripts/gui_api.py` | extracted PURE `_report_list_payload()` (`get_initial_state` spreads it; P4-R05); fixed the 2 "(no pdfplumber pull)" comments (R04) |
| `docs/architecture.md` | the `tsn_library` lazy-pdfplumber line corrected (R04) |
| `docs/planning/v0.18.0/phases/P4-claude-report.md` | the §5 mock-parity bullet made precise + this section |

`check_report_catalog` **37 → 47** assertions. **No product behavior changed** — the catalog data is
byte-identical and `get_initial_state` returns the same payload via the pure builder (bridge checks
green). `compare_core` / auth / updater-TLS / `version.py` / `app.js` / matrix `row_key` untouched.

## Updated verification

```
PYTHONIOENCODING=utf-8  python build/check_report_catalog.py   # 47 assertions — derive, golden+identity,
   helper-based negatives, ordered/label-aware .bat + negatives, field-for-field mock parity + CONS_REPORTS
   + subdir cross-check + negatives, no-side-effects guard — ALL GREEN
python build/check_report_catalog.py  (no env override)        # ALSO green (ASCII-clean on cp1252)
PYTHONIOENCODING=utf-8  python build/check_*.py  (×58)          # 58/58
build/check_gui_bridge.py + build/check_intersection_gate.py   # green (get_initial_state behavior-neutral)
node --check + 2 Node renderers + import-direction + app_modules + no-misspelling + compile + diff-check  # OK
residual "(no pdfplumber pull)" / "never pulls pdfplumber" sweep (source + canonical docs)  # none
```

## Changed measurements

| Metric | Round 1 | After round-2 remediation |
|---|---|---|
| `check_report_catalog` assertions | 37 | **47** |
| Negative self-tests | vacuous (known objects differ) | run **mutated inputs through the production helpers** |
| `.bat` parity | module set + dict-collapsed first-pass chain | **ordered, label-aware, no-collapse**, exactly-one, FIRST-match |
| Mock parity | key/label/fmt/kind/group (partial) | **field-for-field** incl. idx/disabled/file labels + the `CONS_REPORTS` routing list + subdir cross-check |
| Check runtime safety | constructed `GuiApi` (`ensure_layout` writes + 2 thread starts) | **pure payload builder**; no writes/threads/GuiApi (guarded) |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 3). Not committed;
planning folder untracked.

### Final round-2 verification addendum

The round-2 remediation above was re-verified against the final workspace. Two guard details were
tightened without changing scope or the **47-assertion** measurement:

- `_builders_callable` now treats malformed references (including a missing `:`) as a clean failed
  predicate rather than letting the check crash.
- `.bat` parity now requires the raw dispatch rows to be **exactly** choices `1..N` in order and the
  runnable consolidator blocks to be **exactly N** unique targets, rejecting extra as well as duplicate
  branches/blocks. Display text must equal the registry label plus only the parenthesized format note
  (not merely share a prefix).

Final verification:

```
PYTHONIOENCODING=utf-8 python build/check_*.py
  # 58/58 safe offline checks passed (excluding check_fake_site.py and
  # check_source_zip_smoke.py, unchanged from the recorded suite boundary)
python build/check_report_catalog.py                 # 47/47 assertions green
python -m compileall -q scripts build version.py     # green
node --check scripts/ui/app.js                       # green
node build/check_mx_partial_render.js                # green
node build/check_compare_routing.js                  # green
python build/check_import_direction.py               # green
python build/check_app_modules.py                    # green
python build/check_no_misspelling.py                 # green
python build/check_gui_bridge.py                     # green
python build/check_intersection_gate.py              # green
git diff --check -- . ':(exclude)docs/planning/**'   # clean
```

All five round-2 finding dispositions remain **Fixed**. No phase status, persisted format, product
behavior, or measurement changed; P4 remains `awaiting_review`, uncommitted.

---

# Remediation — Codex review round 3 (`PASS WITH FIXES`)

**Round addressed:** P4 Codex review **round 3** ([`P4-codex-review.md`](P4-codex-review.md)) — verdict
`PASS WITH FIXES`, 0 blocking, **1 required** (**P4-R02**, narrowed). Codex marked **P4-R01, P4-R03,
P4-R04, P4-R05 Resolved**; only the `.bat` raw-duplicate-label gap remained open. Verified real against
the workspace before fixing. The original report + round-1 + round-2 remediation are preserved.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P4-R02 | required (narrowed) | **Fixed** | the `.bat` parser now enumerates EVERY raw `:label`, requires each dispatched goto-target defined exactly once, and verifies each target's block body (up to the NEXT label) invokes exactly the intended consolidator — so a duplicate `:label` with an intervening `rem` before a WRONG python call is caught |
| P4-R01 | required | **Resolved (Codex)** | no action — Codex confirmed mutated inputs now pass through the production helpers and are rejected |
| P4-R03 | required | **Resolved (Codex)** | no action — full field-for-field mock parity + `CONS_REPORTS` routing list + bridge-only subdirs confirmed |
| P4-R04 | required | **Resolved (Codex)** | no action — `gui_api.py` / architecture wording now distinguishes lazy builder invocation from eager dependency import; residual sweep clean |
| P4-R05 | required | **Resolved (Codex)** | no action — pure `_report_list_payload()` used by `get_initial_state`; zero filesystem writes / thread starts confirmed by independent instrumentation |

### P4-R02 (round 3) — raw duplicate labels with intervening commands now caught — Fixed
**Verified real** — the round-2 parser recognized a block ONLY when a `:label` was IMMEDIATELY followed
by a `python scripts\consolidate_*.py` line (the `:(\w+)\s*\r?\npython ...` regex). A decoy that inserts
a first `:intersection_summary` label, a `rem` line, then `consolidate_intersection_detail.py` (the WRONG
consolidator), followed by the real `:intersection_summary` block, left every main parity assertion green
(`_blocks_exact` saw a single matched block; the chain matched). But CMD's `goto intersection_summary`
reaches the FIRST label and runs the wrong consolidator (then falls through). RED-confirmed against the
old parser: matched-block count for `intersection_summary` = 1, `_blocks_exact` = True, chain == registry
(the miss).

**Fix** (`build/check_report_catalog.py`, `.bat` parity section only — no product code change):
- `_parse_bat` rewritten as a line-scanner that enumerates **every** raw `:label` definition in order
  and, for each, the block body running to the **next** label — returning `(menu, dispatch, labels,
  blocks)` where `blocks` is `[(label, [consolidator-modules])]`. (`::` comment lines are not labels.)
- New `_targets_defined_once(labels, dispatch)` requires each dispatched goto-target to be defined by
  exactly one raw label — replaces the collapsing `_blocks_exact`, which counted only matched pairs.
- `_bat_chain` now resolves choice -> FIRST goto -> FIRST block -> the block's **sole** consolidator
  (a body with 0 or 2+ consolidator invocations yields `None`), enforcing "exactly the intended
  consolidator before exit/fall-through."
- New negative: inject the decoy into the REAL `.bat` text, re-parse end-to-end, and assert BOTH that
  `_targets_defined_once` rejects it AND that the FIRST-match chain runs the wrong consolidator. The
  existing wrong-label, duplicate-dispatch, immediate-duplicate-block, duplicate-label-uniqueness, and
  swapped-goto negatives are all preserved.

RED proof (standalone): against the decoy text the new parser enumerates **2** `:intersection_summary`
labels, `_targets_defined_once` = False, chain != registry, and the FIRST-match block for choice 4
resolves to `consolidate_intersection_detail` (the wrong one) — exactly the CMD execution, now caught.

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_report_catalog.py` | `.bat` parser rewritten — enumerate all raw labels, per-block sole-consolidator resolution, dispatched-target uniqueness; new raw-duplicate-label decoy negative; docstring updated. **Product code untouched.** |
| `docs/planning/v0.18.0/phases/P4-claude-report.md` | this section |

`check_report_catalog` **47 -> 49** assertions (the 2 new raw-duplicate negatives). **No product
behavior changed** — only the `.bat`-parity CHECK got stronger. `compare_core` / auth / updater-TLS /
`version.py` / `app.js` / `gui_api.py` / `report_catalog.py` / matrix `row_key` untouched this round.

## Updated verification

```
python build/check_report_catalog.py            # 49 assertions, ALL GREEN (ASCII-clean on cp1252)
   new: every dispatched target defined exactly once; choice->block->SOLE-consolidator chain;
   a raw duplicate-label decoy (intervening rem + wrong call) rejected end-to-end through the parser
PYTHONIOENCODING=utf-8  python build/check_*.py  (x58)            # 58/58
node --check app.js + compare_routing + mx_partial + compileall + import_direction + app_modules
   + no_misspelling + product git diff --check                   # all OK
RED proof (standalone): OLD parser misses the decoy (matched-block count 1, chain == registry);
   NEW parser catches it (2 raw labels, targets_defined_once = False, chain != registry)
```

## Changed measurements

| Metric | Round 2 | After round-3 remediation |
|---|---|---|
| `check_report_catalog` assertions | 47 | **49** |
| `.bat` block model | label-immediately-then-python pairs (raw duplicates invisible) | EVERY raw `:label` enumerated; per-block SOLE-consolidator; dispatched targets unique |
| `.bat` negatives | wrong label, dup dispatch, immediate dup block, swapped goto | + duplicate-label uniqueness + raw duplicate-label decoy (intervening `rem` + wrong call) |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 4). Not committed;
planning folder untracked.

---

# Remediation — Codex review round 4 (`PASS WITH FIXES`)

**Round addressed:** P4 Codex review **round 4** ([`P4-codex-review.md`](P4-codex-review.md)) — verdict
`PASS WITH FIXES`, 0 blocking, **1 required** (**P4-R02**, narrowed further to **block termination**).
Codex confirmed **P4-R01, P4-R03, P4-R04, P4-R05 remain Resolved**. Verified real against the workspace
before fixing. The original report + rounds 1-3 remediation are preserved.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P4-R02 | required (narrowed: termination) | **Fixed** | the `.bat` parser now retains each block's ordered control flow and requires every dispatched block to invoke its sole consolidator AND then terminate (`exit /b` / `exit` / `goto :eof`) before the next label — so a missing terminator that would fall through into the next consolidator is caught |
| P4-R01 | required | **Resolved (Codex)** | no action — mutated inputs pass through the production helpers and are rejected |
| P4-R03 | required | **Resolved (Codex)** | no action — full field-for-field mock parity + `CONS_REPORTS` + bridge-only subdirs |
| P4-R04 | required | **Resolved (Codex)** | no action — dependency-boundary wording; residual sweep clean |
| P4-R05 | required | **Resolved (Codex)** | no action — pure `_report_list_payload()`; zero writes/threads |

### P4-R02 (round 4) — block fall-through into the next consolidator now caught — Fixed
**Verified real** — the round-3 parser recorded only consolidator module names per block; `_bat_chain`
accepted a block whenever it held exactly one consolidator before the next label, and nothing required a
terminating transfer. Removing ONLY `exit /b 0` from the `:intersection_summary` block left all five main
parity conditions green (menu order, exact dispatch, target-label uniqueness, displayed labels, ordered
module chain). Under CMD semantics, after the Summary command and `pause`, execution falls through the
`:intersection_detail` label and runs the Detail consolidator too. RED-confirmed: with the terminator
removed, the old parser kept all five conditions True and modeled no termination at all.

**Fix** (`build/check_report_catalog.py`, `.bat` parity section only — no product change):
- `_parse_bat` now records, per raw block, an **ordered event list** — `("cons", module)` for each
  consolidator call and `("term", line)` for each UNCONDITIONAL terminator — instead of a bare module
  list. Module-level `_TERMINATOR` accepts `exit /b [code]`, `exit [code]`, and `goto :eof`
  (case-insensitive, whole-line) — `exit /b` is the repository form; the other two are the explicitly
  defined accepted terminal transfers. A line prefixed by `if` is NOT a terminator (conditional).
- New `_terminates_after_consolidator(events)` requires exactly one consolidator followed by an
  unconditional terminator before the next label; `_all_blocks_terminate(dispatch, blocks)` requires it
  of every dispatched block. `_bat_chain` reads the sole consolidator via `_block_mods(events)`
  (behavior unchanged for the chain).
- New production assertion: "every dispatched block terminates after its consolidator (no fall-through)."
- New negative: remove the `:intersection_summary` terminator in the REAL `.bat` text, re-parse, and
  assert BOTH that `_all_blocks_terminate` rejects it AND that the module chain alone stays green —
  demonstrating termination is a distinct, necessary guard. The synthetic duplicate-block negative was
  updated to the new event shape; all other round 2-3 negatives are preserved.

RED proof (standalone): on the real file all dispatched blocks terminate; the terminator regex accepts
`exit /b 0` / `exit /b` / `exit 1` / `goto :eof` and rejects `if errorlevel 1 exit /b 1`; with one
`exit /b 0` removed, `_all_blocks_terminate` = False (caught) while the module chain == registry (stays
green — only the termination guard catches the fall-through).

## Remediation changes (files)

| File | Change |
|---|---|
| `build/check_report_catalog.py` | `.bat` parser now retains ordered block control flow (`("cons", …)` / `("term", …)`); `_TERMINATOR` / `_terminates_after_consolidator` / `_all_blocks_terminate`; new production termination assertion + removed-terminator negative; duplicate-block negative migrated to the event shape; docstring updated. **Product code untouched.** |
| `docs/planning/v0.18.0/phases/P4-claude-report.md` | this section |

`check_report_catalog` **49 -> 52** assertions (1 production termination check + 2 negatives). **No
product behavior changed** — only the `.bat`-parity CHECK got stronger. `compare_core` / auth /
updater-TLS / `version.py` / `app.js` / `gui_api.py` / `report_catalog.py` / matrix `row_key` untouched
this round.

## Updated verification

```
python build/check_report_catalog.py            # 52 assertions, ALL GREEN (ASCII-clean on cp1252)
   new: every dispatched block invokes its sole consolidator AND terminates (exit /b / exit / goto :eof)
   before the next label; a removed terminator is rejected while the chain stays green (distinct guard)
PYTHONIOENCODING=utf-8  python build/check_*.py  (x58)            # 58/58
node --check app.js + compare_routing + mx_partial + compileall + import_direction + app_modules
   + no_misspelling + product git diff --check                   # all OK
RED proof (standalone): OLD parser misses a removed terminator (all 5 main conditions green, no
   termination model); NEW parser catches it (_all_blocks_terminate = False; chain == registry)
```

## Changed measurements

| Metric | Round 3 | After round-4 remediation |
|---|---|---|
| `check_report_catalog` assertions | 49 | **52** |
| `.bat` block model | label + per-block sole-consolidator | + ordered control flow per block; required unconditional terminator before the next label |
| `.bat` negatives | wrong label, dup dispatch, immediate dup block, dup-label uniqueness, swapped goto, raw duplicate-label decoy | + removed block terminator (fall-through) caught by a distinct termination guard |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 5). Not committed;
planning folder untracked.
