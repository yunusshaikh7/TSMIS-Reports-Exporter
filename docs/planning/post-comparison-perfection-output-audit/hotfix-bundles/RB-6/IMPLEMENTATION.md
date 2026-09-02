# `RB-6` — Implementation Record

Status: **IMPLEMENTED — AWAITING ADVERSARIAL REVIEW** (Review 1 return `RB6-R1-EG-001` closed 2026-09-01)

> Codex Review 1 (2026-08-31): **DENIED — EVIDENCE GAP**, solely
> `RB6-R1-EG-001` — retain the contract-required HF-08 post-double-rebuild
> vs-TSN comparisons for every buildable dataset, both twins, with unchanged
> counts and exact runtime/source/library/output bindings. See
> [REVIEW.md](REVIEW.md). The implementation claims below are preserved; this
> precondition return does not allege a product defect.

| Field | Value |
|---|---|
| Implementer | Claude |
| Branch | `hotfix/rb-6-hygiene-and-guards` |
| Base `main` commit | `62bb0f329c7d7deea6c5ee9010c3d21b0acf6325` (clean, `origin/main` identical, fetched 2026-08-31; repo at **v0.43.0**) |
| Implementation commits | `8a295e9` preflight · `b239cb7` export-only · `70b93ab` TSN determinism (last `scripts/` commit) · `cb35bde` guards + VEN-01 · `0b011ef` `9253890` records · `093fdc2` Review 1 return · `a49c43e` docstring correction · the `RB6-R1-EG-001` remedy commit (head at finalization `a49c43e`) |
| Generated-output root | `%TEMP%\claude\…\scratchpad\rb6\` (local, disposable); committed witnesses under `hotfix-bundles/HF-07,08,11/witness/` |
| Work items | HF-07 (PCOA-FINAL-015, -018), HF-08 (-017), HF-11 (-020, -021, -022) |

> **Read this first.** Three scope statements in the bundle were stale against
> today's `main` and are corrected here, with evidence. None widens the bundle.
> They are called out inline and summarised under *Scope and residual risk*.

---

## HF-07 — Missing-side fast fail and export coverage truth

### PCOA-FINAL-015 — an absent second side was reported only after the first side was fully parsed

**Root cause, confirmed.** `EnvCompare.compare_folders` already discovers both
sides' member lists (`files_a` / `files_b`) before loading anything, but it then
handed **side A** to its loader first and only reached side B's "nothing was
exported here" refusal afterwards. Every loader's FIRST act is that refusal, so
the information was available immediately and simply was not consulted in the
right order. The plan's line reference (`:1033`, `:1065-1066`, `:1139+`) still
describes the current code; only the line numbers have moved.

**Design.** Two changes in `scripts/compare_env.py`, both structural rather than
additive:

1. `EnvCompare._side_loader_fn()` resolves, ONCE, the single
   `(folder, label, events) -> LoadedSide` callable this adapter loads a side
   with. `compare_folders` previously repeated that four-way dispatch inline for
   each side; it now calls the one resolver for both sides.
2. The preflight is then two lines:

   ```python
   if files_a and not files_b:
       load_side(dir_b, lb, events)
   ```

   It refuses **through side B's own loader**, on a side that discovered zero
   files — so the loader raises its own message, immediately, having parsed
   nothing. The message therefore CANNOT drift from the real one: it *is* the
   real one.

**Why the verdict is preserved exactly.**

* Firing only when `files_b` is empty means the preflight can never pre-empt a
  side the loader would have accepted. `_find_input_dir` already excludes
  Excel's `~$` owner-lock stubs (CMP-AUD-029), so "discovered nothing" and "the
  loader will refuse" are the SAME predicate for all thirteen families —
  including the two aggregate loaders that filter lock files a second time. The
  plan warned these two could differ; measured, they do not, and
  `check_compare_env_missing_side` asserts it per adapter.
* The `files_a and` guard keeps the BOTH-empty case refusing on side A first,
  exactly as before.
* The alias, same-folder, and provenance guards all run before the preflight and
  keep priority.

**All three witnessed workflows are covered by this one preflight** — classic
(`gui_compare_api.py:525`), Baseline (`baseline_matrix.py:453`) and Everything
ENV (`matrix_build.py:760`) all dispatch to `adapter.compare_folders`.

### PCOA-FINAL-018 — three enabled editions have no verification path

**Root cause, confirmed — and the SET HAS CHANGED.** The finding named
`ramp_summary_excel`, `intersection_summary_pdf` and `highway_summary`. Derived
from today's catalog, the enabled editions with no `MATRIX` row are:

| Edition | Then | Now |
|---|---|---|
| `ramp_summary_excel` | unverifiable | unverifiable |
| `intersection_summary_pdf` | unverifiable | unverifiable |
| `highway_summary` | unverifiable | **verified since v0.37.0** (consolidator + cross-env + vs-TSN) |
| `highway_summary_pdf` | did not exist | **unverifiable** (added v0.38.0, export-only) |

Still exactly three; one member replaced. The gate DERIVES the set and never
transcribes it, so this cannot go stale again.

**Design.** `report_catalog.ExportEntry` gains an `export_only` field
(default `False`), declared on those three. It is an EXPLICIT declaration, never
derived from the absence of a `MATRIX` row — a derived marker would make the gate
tautological and a newly added unwired edition would inherit the same silence.
An import-time assertion forbids an edition being both wired and declared.
`reports.EXPORT_ONLY_KEYS` and `gui_api._export_report_rows()` carry it to the
GUI, where the picker row shows `— export only` and a hover explanation.

`check_report_wiring.py` gains `test_every_enabled_export_is_verifiable_or_declared`:
every ENABLED export edition must have a comparison path **XOR** be declared
export-only, and every declared edition must be marked in the picker rows.

**Compatibility.** Stable IDs are untouched, `_V017_EXPORT_ORDER` is untouched,
and the frozen v0.17 baseline compares `(key, label, fmt)` only — a namedtuple
field with a default changes no positional construction. `check_report_catalog`
passes unchanged.

---

## HF-08 — TSN normalization identity determinism

### PCOA-FINAL-017 — root cause ESTABLISHED (the finding required this first)

The finding labelled the openpyxl explanation an **explicit hypothesis**. It is
now measured, and it is **two** clocks, not one:

1. **`docProps/core.xml`.** `openpyxl.writer.excel.save_workbook` assigns
   `workbook.properties.modified = datetime.now(utc)` UNCONDITIONALLY,
   immediately before serializing; `properties.created` defaults to when the
   object was constructed. Two saves of the same workbook object a second apart
   differ in exactly those two elements and in nothing else — same member names,
   same member content, same everything else.
2. **Every ZIP entry's `date_time`.** `zipfile` stamps each member from the wall
   clock at **MS-DOS two-second resolution**. This is why the first probes
   looked clean and then did not: two builds 1.1 s apart land in the same
   two-second bucket about half the time. It was found only because the
   Highway Sequence writer produced differing bytes with *zero* differing member
   content.

Neither is in a parser or a projection, which is why the fix moves **no
normalized content**. Two saves inside one second were already byte-identical.

**Design.** `artifact_store` gains an OPT-IN stable-identity save:

* `STABLE_DOCUMENT_TIMESTAMP` / `STABLE_ZIP_DATE_TIME` — one fixed epoch
  (1980-01-01, the earliest an MS-DOS timestamp can express);
* `stable_document_identity(wb)` — pins the document properties. openpyxl's
  pre-save assignment has to be made INERT, not merely pre-empted, so this
  installs a `DocumentProperties` subclass whose `modified` setter ignores
  writes. `MetaSerialisable` rebuilds the serialisation registries from the
  subclass namespace and overwrites `__namespaced__` unconditionally, so the
  parent's four registries are restored after class creation — without that the
  part serialises to an empty `<coreProperties/>`, which the check asserts
  against;
* `_StableZipFile` — a `ZipFile` whose `open(zinfo, "w")` pins every member's
  `date_time`. Both `writestr` and `write` funnel through that one call;
* `save_stable(wb, path)` — drives `ExcelWriter` over that archive instead of
  `Workbook.save`, which hard-codes a plain `ZipFile`. Parts, order and content
  are openpyxl's own;
* `atomic_save` / `atomic_save_if` take `stable_identity=False`, and
  `consolidate_xlsx` forwards the same flag.

**Only the TSN library opts in** — the three save paths every registered dataset
reaches: `tsn_library.build_normalized` (9 datasets),
`consolidate_tsn_highway_sequence._write_workbook` (1), and
`consolidate_tsn_highway_log`'s `consolidate_xlsx` call (1). Everything else
saves byte-for-byte as before; the check asserts that the default save is still
time-varying, so the opt-in cannot leak.

**Scope note — files beyond the plan's expectation.** The plan expected
`scripts/tsn_library.py` plus checks, and required a STOP if the cause lay in a
per-report loader. **It does not** — the cause is openpyxl's document/archive
defaults, uniform across every builder. Because two of the eleven datasets save
outside `build_normalized`, the fix needs the shared save boundary:
`artifact_store.py`, `tsn_library.py`, `consolidate_tsn_highway_sequence.py`,
`consolidate_tsn_highway_log.py` and `consolidate_xlsx_base.py`. Each change is
one to three lines and default-off. Flagged here for the reviewer rather than
buried; no bundle scope is widened and no normalization content is touched.

**The one-time invalidation, disclosed.** Making the bytes deterministic changes
every dataset's `tsn_normalized_workbook_identity` and
`tsn_artifact_identity_token` ONCE. Every vs-TSN comparison bound to a
pre-existing library generation is therefore invalidated by the fix itself, and
**one full re-comparison is expected after this bundle merges.** That is the
correct, honest outcome — the acceptance run confirms the identity moves and
that the normalized CONTENT does not. Rollback is asymmetric: reverting makes
identities non-deterministic again and costs a further re-comparison.

---

## HF-11 — Source-side escalation and must-not-regress guards

**No `scripts/` change.** Two prose "must not regress" notes became executable
guards in `build/check_site_change_regression_guards.py`, and the route-140
vendor defect became an owner-facing record.

* **PCOA-FINAL-022a (the TASAS re-skin).** The parser survives a re-skinned print
  because it derives each page's column windows from THAT page's own header-word
  positions. The guard renders one logical page of Highway Sequence data at two
  different text measures — the narrow pre-re-skin skin and the wider TASAS
  skin — from the parser's own boundary formulas, and requires identical rows,
  identical route claims, and zero unclassified lines from both.
* **PCOA-FINAL-022b (the leading `GENERATE` line).** A fixture with the stray
  line must parse identically to one without it. The finding names four print
  families; `intersection_summary_pdf` is EXPORT-ONLY and has no parser at all,
  which is exactly what PCOA-FINAL-018 now declares — so the guard ASSERTS, per
  family, "has a PDF parser, or is declared export-only", and a parser added
  later is automatically guarded rather than silently unguarded.
* **PCOA-FINAL-021 (the two PDF-only rows).** Re-verified at the raw source, then
  locked: a Highway Log comparison whose PDF side carries a row its Excel side
  does not must report it ONE-SIDED, never paired against an invented partner.
* **PCOA-FINAL-020 (route 140).** `docs/vendor-escalations.md` is the new
  owner-facing record, indexed from `docs/INDEX.md` and pointed to from
  `docs/highway_log/columns.md`.

### Source-truth recount (021)

Both rows re-read from the raw PDFs through the shipped char-window reader and
their Excel siblings through openpyxl:

| Route | Location | Raw PDF | Excel | Raw line |
|---|---|---:|---:|---|
| 074 | `000.000` occ. 2 | **2** | 1 | p.7 `000.000 002.080 000.000 R 60 M U C H 01 Z 08 00 12 00 00 B7Z 00Z H 01 Z 00 00 11 02 00 640101` |
| 101 | `R022.828` | **1** | 0 | p.142 `R 022.828 000.007 022.807 U 70 F D F H 04 N 10 10 45 10 10 07 N 840626` |

Both reproduce the Stage-1A audit's recorded text exactly. **A methodology note
worth keeping:** the first probe matched on the line's FIRST word and returned
`0` for route 101 — the postmile PREFIX (`R`) prints as its own token, so the
location never appears as one word. Route 074, which has no prefix, was the
positive control that exposed the broken probe. A probe returning zero is broken
until a positive control says otherwise.

For route 101 the Excel sibling carries no row containing `022.828` in **any**
column, not merely none whose Location equals `R022.828`.

### Source-truth recount (020) — and a materially sharper finding

| Source | Rows | `R/U` blank | `TER` blank | `H/G` blank | `A/C` blank |
|---|---:|---:|---:|---:|---:|
| Excel 2026-06-19 | 199 | 4 | 0 | 4 | 0 |
| Excel 2026-07-09 | 219 | 0 | 0 | 0 | 0 |
| **Excel 2026-07-23** | **213** | **213** | **213** | **213** | **213** |
| Excel 2026-07-23, route **138** (control) | 264 | 0 | 0 | 0 | 0 |
| **PDF 2026-07-23** (route 140's own print) | **214** | **0** | **0** | **0** | **0** |

The finding recorded route 140 as blank. It is blank **on one day**: the same
route was complete two weeks earlier, its same-day sibling is complete, and its
own same-day print is complete (`R/U` R×175 U×39, `TER` F×112 M×62 R×40,
`H/G` D×35 U×179, `A/C` C×214). This is a **one-day, one-route regression in the
vendor's Excel export**, not a standing property — which changes what the owner
asks the vendor. 2026-07-23 is the newest route-140 Highway Log Excel available
locally, so whether it persists is UNKNOWN and needs a fresh pull.

---

## Changes

| File | Change | Finding |
|---|---|---|
| `scripts/compare_env.py` | `_side_loader_fn()` resolver + the missing-side preflight in `compare_folders` | 015 |
| `scripts/report_catalog.py` | `ExportEntry.export_only` + `export_only_keys()` + the mutual-exclusion assertion | 018 |
| `scripts/reports.py` | `EXPORT_ONLY_KEYS` derivation | 018 |
| `scripts/gui_api.py` | `export_only` on each export-picker row | 018 |
| `scripts/ui/app.js`, `app.css`, `mock.js` | the `— export only` note, its tooltip, its style, and the mock parity | 018 |
| `scripts/artifact_store.py` | `stable_document_identity` / `save_stable` / `_StableZipFile` + the `stable_identity` opt-in on both atomic saves | 017 |
| `scripts/tsn_library.py` | `build_normalized` opts in at its save | 017 |
| `scripts/consolidate_tsn_highway_sequence.py` | opts in at its save | 017 |
| `scripts/consolidate_tsn_highway_log.py` | opts in through `consolidate_xlsx` | 017 |
| `scripts/consolidate_xlsx_base.py` | forwards `stable_identity` (default off) | 017 |
| `build/check_compare_env_missing_side.py` | NEW — the preflight gate | 015 |
| `build/check_tsn_identity_determinism.py` | NEW — the determinism gate | 017 |
| `build/check_site_change_regression_guards.py` | NEW — both must-not-regress guards | 021, 022 |
| `build/check_report_wiring.py` | the export-only coverage gate | 018 |
| `build/check_tsn_raw_source_contract.py`, `build/check_consolidate_toctou.py` | three `atomic_save_if` test doubles now forward `**kwargs` | 017 |
| `docs/vendor-escalations.md` | NEW — the owner-facing vendor record (VEN-01) | 020 |
| `docs/INDEX.md`, `docs/highway_log/columns.md` | pointers to it | 020 |
| `hotfix-bundles/HF-07,08,11/witness/` | the committed witnesses | all |
| `hotfix-bundles/RB-6/BUNDLE.md` | the recorded Stage-4 base | — |

---

## Verification results

### Gates

| Gate | Command | Result |
|---|---|---|
| Full offline suite | `python build/run_checks.py -j 4 -k` | **175 passed, 0 failed of 175** (128 s). An earlier run was 174/175: `check_consolidate_toctou` failed because two of its `atomic_save_if` doubles did not forward the new keyword — the doubles now use `**kwargs` |
| Lint | `python -m ruff check .` | **All checks passed** |
| New: missing-side preflight | `build/check_compare_env_missing_side.py` | PASS (**19 assertions RED** with the two-line preflight removed) |
| New: TSN identity determinism | `build/check_tsn_identity_determinism.py` | PASS (**5 assertions RED** with the stable save disabled, reproducing the finding's exact symptom: different `…sha256` and different `tsn-normalized-v1:…` token for unchanged raw) |
| New: site-change guards | `build/check_site_change_regression_guards.py` | PASS (**4 assertions RED** when the HSL parser derives its column windows once instead of per page; the source-universe guard goes RED when a probe synthesizes the PDF-only partners — `{Both: 2, PDF only: 2}` becomes `{Both: 4}`) |
| Extended: report wiring | `build/check_report_wiring.py` | PASS (**RED naming `ramp_summary_excel` and `highway_summary_pdf`** with their declarations removed) |
| Neighbouring sets from the plan | `check_report_catalog`, `check_report_recipe`, `check_ui_contract`, `check_matrix`, `check_baseline_matrix`, `check_a2_compare_filter`, all 8 `check_compare_env_*`, all 10 `check_tsn_*`, `check_artifact_store`, `check_consolidate_worker_publication`, `check_ci_manifest`, `check_app_modules` | all PASS |

### HF-07 / 015 — missing-side latency on real statewide exports

Witness: `HF-07/witness/missing_side_latency.json`.

| Configuration | Side-A prints | Pre-fix side-A load | Post-fix refusal | Verdict |
|---|---:|---:|---:|---|
| `intersection_detail_pdf` (audit witness 429.4 s) | 217 | **439.9 s** (16,459 rows) | **0.49 s** | 898× |
| `highway_detail_pdf` (audit witness 1,229.7 s) | 252 | not re-measured | **0.51 s** | — |

`pre_fix_side_a_load_s` is side A's own loader timed directly — that IS the
pre-fix wait, because pre-fix `compare_folders` handed side A to this loader and
only reached side B's refusal afterwards. 439.9 s independently reproduces the
audit's 429.4 s witness within 2.5 %.

**What was NOT re-run, and why.** The Highway Detail (PDF) pre-fix leg would cost
~20 more minutes to re-derive a number the audit already witnessed, on a change
that lives in the shared preflight. Criterion 1 asks for the POST-fix behaviour on
the witnessed configurations; both are measured and both are under 5 s. The third
witnessed configuration is the same `intersection_detail_pdf` family on Baseline:
Baseline, classic and Everything ENV all dispatch to the same
`adapter.compare_folders`, and the check exercises all 13 registered families.

### HF-07 / 015 — a valid comparison is unchanged

Witness: `HF-07/witness/valid_run_parity.json`. Each family's real
cross-environment comparison (2026-07-09 vs 2026-07-23 ssor-prod) was generated
twice in separate processes — once against `git show <base>:scripts/compare_env.py`
placed first on `sys.path`, once against the head — in `mode="both"`, and both
twins digested cell for cell.

| Family | Dispatch branch | Comparison rows | Base vs head |
|---|---|---:|---|
| `highway_log` | flat XLSX | 54,379 | **identical, both twins** |
| `intersection_summary` | aggregate `side_loader` | 218 | **identical, both twins** |
| `ramp_summary` | Ramp Summary PDF | 127 | **identical, both twins** |

The two runtimes are proven distinct: `base_had_preflight_helper=false`,
`head_had_preflight_helper=true`.

### HF-07 / 018 — export coverage

Witness: `HF-07/witness/export_coverage.json`. Re-derived from the catalog's own
declaration over the frozen archive: **126 `ramp_summary_excel` + 217
`intersection_summary_pdf` = 343 of 2,380 exported route files (14.4 %)** —
reproducing the finding exactly. `highway_summary_pdf` contributes 0 files
because it postdates the archive.

UI surfacing verified in the `#mock` preview at 1400×900 (default desktop width):
the three rows render `Summary (Excel) — export only` / `Summary (PDF) — export
only`, stay **pickable** (unlike the greyed `— not yet available` rows), are not
clipped (`scrollWidth == clientWidth == 472`), carry the hover explanation, and
leave the picker's four group headers intact across all 20 rows.

### HF-08 / 017 — the real double rebuild

Witness: `HF-08/witness/double_rebuild.json`. Each dataset's real staged raw was
copied into a private library root and the shipped
`build_consolidated(report, force=True)` ran three times, separated by more than
the ZIP timestamp's two-second resolution: `pre` (stable save OFF), then `post1`
and `post2`. **9 of 9 buildable datasets pass all four criteria.**

| Dataset | Raw kind | 3 builds | post1 == post2 bytes | identity | token | content == pre |
|---|---|---:|---|---|---|---|
| `highway_log` | district PDFs (12) | 2110 s | ✔ | ✔ | ✔ | ✔ |
| `ramp_detail` | statewide XLSX | 15 s | ✔ | ✔ | ✔ | ✔ |
| `ramp_summary` | statewide PDF | 1 s | ✔ | ✔ | ✔ | ✔ |
| `intersection_summary` | statewide PDF | 1 s | ✔ | ✔ | ✔ | ✔ |
| `intersection_detail` | statewide XLSX | 29 s | ✔ | ✔ | ✔ | ✔ |
| `highway_sequence` | district PDFs (12) | 338 s | ✔ | ✔ | ✔ | ✔ |
| `highway_detail` | statewide XLSX | 141 s | ✔ | ✔ | ✔ | ✔ |
| `highway_summary` | statewide PDF | 2 s | ✔ | ✔ | ✔ | ✔ |
| `clean_highway` | statewide XLSX | 174 s | ✔ | ✔ | ✔ | ✔ |
| `clean_intersection`, `clean_ramp` | — | — | **not built** — no normalizer (DEF-05); their builders refuse and write nothing, which `check_tsn_identity_determinism` asserts rather than assumes |

Criteria 2 and 4 are the table. Criterion 3 (a rebuild that SHOULD change
identity still does) is covered by the hermetic gate: changed normalized content
and changed raw bytes each move the token. Criterion 5 — **the one-time
invalidation** — is confirmed on **every** dataset: `pre` and `post1` have
different `tsn_artifact_identity_token`s, from identical raw and identical
content. That is the invalidation this bundle causes by design, measured rather
than predicted.

The raw member set is identical across all three builds for every dataset (the
witness records it per build), so the `_TSN_PDFS_IN_RAW` families' prints and
their bindings are unaffected. Per-sheet row counts are recorded for every build,
so the normalization marker sheet is present and identical post-fix.

### HF-08 / 017 — post-rebuild vs-TSN comparisons (`RB6-R1-EG-001`)

See the *Review 1 remedy* section at the end of this record; its witness is
`HF-08/witness/post_rebuild_vs_tsn.json`.

### HF-11 — source truth

Witnesses: `HF-11/witness/pdf_only_rows.json`,
`HF-11/witness/route_140_raw_census.json`. Both recounts are in the HF-11 section
above. No `scripts/` change; no comparison counts move.

## Scope and residual risk

**Out-of-scope files changed: none.** Four product files beyond the plan's
"expected" list are inside HF-08's own scope (the TSN library's normalized-workbook
build and identity) and are explained under HF-08 — the cause is not in a
per-report loader, so the split trigger does not apply, but two of eleven datasets
save outside `build_normalized`. Three `build/check_*` test doubles were updated to
forward the new keyword; they are doubles, not behaviour.

**`CHANGELOG.md` was deliberately NOT touched**, although HF-11 lists it. The
changelog takes one section per RELEASE (`release: vX.Y.Z` commits), Prompt 04
forbids bumping a release, and RB-5's implementation did not touch it either. The
entry belongs to whichever release ships this bundle.

### Residual risk

1. **The one-time TSN identity invalidation is real and intended.** After merge,
   every existing vs-TSN comparison is bound to a superseded library generation
   and must be re-run once. It is detected and reported honestly — the binding
   contract already refuses a stale-bound result rather than silently serving it.
2. **`_stable_properties_class` depends on two openpyxl internals**: that
   `save_workbook` assigns `properties.modified` (so the setter must be inert),
   and that `MetaSerialisable` rebuilds the serialisation registries from the
   subclass namespace (so the parent's four must be restored). Both are asserted
   by `check_tsn_identity_determinism`, which inspects the produced
   `docProps/core.xml` — an openpyxl upgrade that changes either fails the gate
   loudly instead of silently emptying the part or reintroducing the clock.
3. **The `stable_identity` opt-in is off by default and must stay that way** for
   any producer whose bytes are not a published identity; turning it on moves
   that artifact's bytes once. The check asserts the default save is still
   time-varying, so a leak fails the gate.
4. **`_side_loader_fn` is now the single loader dispatch.** A new family that
   adds a fifth loader shape must extend that one resolver; forgetting to would
   route both sides to the wrong loader rather than fail quietly.

### Reviewer focus

* Confirm the HF-08 root cause independently — the finding required the
  implementer to establish it, and the answer here is **two** clocks, not the
  hypothesised one. Disabling only the document-properties half still leaves ZIP
  entry timestamps varying at two-second resolution, which is why short probes
  pass by luck.
* Re-derive the export-only set from the catalog rather than the finding's list.
* Check that the preflight cannot pre-empt a side the loader would accept, and
  that the BOTH-empty verdict is unchanged.
* The route-140 census contradicts the finding's framing (one day, not always);
  re-derive it before trusting the vendor record.

## Review 1 return — Codex, 2026-09-01 (`RB6-R1-EG-001`)

Review 1 **DENIED — EVIDENCE GAP** at review-entry head `9253890`, solely
`RB6-R1-EG-001`: `BUNDLE.md` requires, under HF-08's "Values / formulas and
installed-Excel checks", *one vs-TSN comparison per dataset regenerated after
the double rebuild, both twins, counts unchanged* — and this record retained the
library-level identity and cell-content proof (`double_rebuild.json`) but not
that leg. The reviewer's practical-impact reading is correct: after a user
presses **Rebuild TSN library**, the next user-visible operation is a vs-TSN
comparison, so this is the only acceptance leg proving the new stable library
identity binds to both published workbook flavors without moving their counts
or typed outcomes. No runtime defect was alleged; nine focused checks passed and
the raw-source spots matched the committed witnesses. The signed record is
[REVIEW.md](REVIEW.md); the denial commit is `093fdc2`.

## Review 1 remedy — Claude, 2026-09-01 (`RB6-R1-EG-001` CLOSED)

The missing leg is supplied as ONE committed witness,
[`HF-08/witness/post_rebuild_vs_tsn.json`](../HF-08/witness/post_rebuild_vs_tsn.json),
produced by `hf08_vs_tsn_leg.py` (retained with its inputs' outputs under
`_scratch\post-comparison-hotfixes\HF-08\`). Nothing in `scripts/` changed:
git's own answer to "the last commit touching `scripts/`" is
`70b93ab`, and every file changed between it and the
generation head `a49c43e` is a check, a record or a
witness — the witness lists them.

**Method.** Per buildable dataset the TSMIS side is resolved ONCE and hashed, so
both legs provably compare the same input. `pre` builds the library with the
stable-identity save OFF and runs the family's registered vs-TSN comparator in
`mode="both"`; `post` rebuilds the library TWICE on the shipped path — the
contract's "after the second unchanged-raw deterministic rebuild" — and runs the
SAME comparator over the SAME input. Comparators come from
`matrix.tsn_comparator_for`, the product's own lookup. The library's raw
manifest, normalization version, post-rebuild workbook identity and artifact
token, both legs' generation ids, and all four twins' paths, sizes and SHA-256
are recorded per dataset.

**What must not move, and did not.** The ENTIRE typed outcome — status,
completion, verdict, pairing quality, duplicate-group count, warning/failure
counts, paired and one-sided totals, differing rows, total AND per-field
differing cells — is compared for equality between the legs. Then, beyond the
typed counts, every sheet of both twins of each dataset's PRE and POST workbooks
was walked cell by cell (`eg001_celldiff.py`): Comparison, Summary, Spot Check,
both Only-in sheets, both source sheets, Notes, Source Files and both hidden
`CMP_E2` snapshot sheets are IDENTICAL. The only differing cell, in every twin of
every dataset, is the Provenance row that records the TSN library's sha256 — the
identity the fix moves once, by design.

| Dataset | Compare pre / post | Typed status / completion / verdict | Paired | One-sided | Differing rows | Differing cells | Fields counted | Cells differing PRE→POST, formulas / values | Unchanged |
|---|---:|---|---:|---:|---:|---:|---:|---|---|
| `highway_log` | 1229 / 1447 s | ok / complete / diff | 48,351 | 15,265 | 39,623 | 140,643 | 30 | 1 / 1 | ✔ |
| `ramp_detail` | 124 / 115 s | ok / complete / diff | 15,212 | 202 | 737 | 843 | 12 | 1 / 1 | ✔ |
| `ramp_summary` | 1 / 1 s | ok / complete / diff | 29 | 2 | 24 | 24 | 1 | 1 / 1 | ✔ |
| `intersection_summary` | 1 / 1 s | ok / complete / diff | 58 | 8 | 53 | 53 | 1 | 1 / 1 | ✔ |
| `intersection_detail` | 430 / 344 s | ok / complete / diff | 16,199 | 687 | 2,816 | 5,092 | 34 | 1 / 1 | ✔ |
| `highway_sequence` | 412 / 475 s | ok / complete / diff | 57,072 | 16,154 | 23,691 | 30,005 | 6 | 1 / 1 | ✔ |
| `highway_detail` | 1807 / 1760 s | ok / complete / diff | 48,477 | 14,456 | 48,287 | 160,347 | 34 | 1 / 1 | ✔ |
| `highway_summary` | 1 / 1 s | ok / complete / diff | 92 | 4 | 89 | 89 | 1 | 1 / 1 | ✔ |
| `clean_highway` | 2509 / 2177 s | ok / partial / diff | 52,629 | 12,567 | 48,942 | 281,393 | 74 | 1 / 1 | ✔ |

**9 of 9 buildable datasets: every
check met.** The published VALUES workbook's own Status/Diffs (read by header
label through `matrix_state.read_counts`) equal the typed totals in every leg,
and `consolidation_meta.require_published_comparison` accepts every result —
returned typed outcome, committed generation, succeeded attempt and strict
sidecar agree. `clean_intersection`, `clean_ramp` are retained as
typed refusals (no normalizer, DEF-05), not invented outputs.

**Two cross-checks against blessed numbers, unprompted.** Highway Detail's
160,347 differing cells is exactly the CMP-AUD-244 statewide figure recorded in
`CLAUDE.md`; Highway Summary's 89 of 92 categories differing is the recorded
vintage gap. The leg reproduces known canaries, not merely itself.

**Determinism across sessions, not just within one.** The 2026-08-31
double-rebuild witness recorded each dataset's post-fix library bytes and
token. This run — a separate process, a day later, from the same raw —
reproduced every one of the nine exactly
(`post_library_byte_identical_to_prior_independent_run_all_datasets`:
true).

**One input had to be rebuilt, and the refusal is itself evidence.** The
prebuilt `output/arcgis_cleanroad/clean_highway_built.xlsx` (2026-07-22) carries
the 74-column header; the comparator has required the 75-column `ARC_HEADER`
since v0.39.1 and refused it in BOTH legs — the header gate working as designed.
The Clean Road Highway workbook was rebuilt with the current runtime from the
40-layer library as-of the TSN extract's own date (2025-09-08; 57,742 rows,
252 routes, `partial` with 146 unplaced spans — the disclosed HF-01 class) and
the leg re-run over it. The refused attempt is kept in the witness as
`superseded_attempt`.

**Declared beyond the requested item.** Commit `a49c43e` corrects the docstring
of `build/check_tsn_identity_determinism.py`, which still carried the
pre-discovery claim that ZIP `date_time` fields were identical — contradicting
the two-clock root cause the review independently confirmed. Documentation only;
no assertion changed; the check passes.

Do not merge this branch. When complete, push it and run Prompt 05.
