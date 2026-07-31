# `RB-2` — Implementation Record

Status: **IMPLEMENTED — AWAITING ADVERSARIAL REVIEW**

| Field | Value |
|---|---|
| Bundle / work items | **RB-2 / HF-02 + HF-03** |
| Implementer | Claude (owner decision 2026-07-26: Claude implements every bundle) |
| Branch | `hotfix/rb-2-deliverable-presentation` (worktree `C:\Users\Yunus\Projects\TSMIS-rb2-worktree`; the user's `main` checkout is untouched and still clean) |
| Base `main` commit | `896083e014d0451d5b05e5b6b024339aebc84d74` — clean, identical to `origin/main`, fetched without force before branching |
| Implementation commits | `da1d480` (the change), `eb54b96` (the Excel-measured geometry correction), `1a94183` (the Provenance role column, found by installed Excel's own AutoFit) |
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
| Neighbouring-family regression (checks) | Every check both contracts name, from the post-correction gate run | **PASS — 18/18 green**: `check_compare_audit`, `check_compare_build_freshness`, `check_comparison_artifact_schema`, `check_compare_equality_policy`, `check_compare_source_files`, `check_matrix`, `check_day_matrix`, `check_baseline_matrix`, `check_pdf_excel_matrix`, `check_matrix_tsn`, `check_tsn_highway_log_claims`, `check_tsn_canonical_consumer_identity`, `check_tsn_freshness`, `check_tsn_outcome`, `check_matrix_cache_adversarial`, `check_comparison_publication`, `check_artifact_store`, plus the merged HF-01 `check_clean_road` |
| Acceptance run `RB2-A1` | *(in progress — see below)* | |

## The first measured pass FAILED — and set the constants

The audit's own gate (Calibri metrics, the same tolerance) reported **0** clipped
cells as soon as the first version of the fix was in. Installed Excel did not
agree. Run over the REAL first generated workbook — `ssor-prod_ramp_summary_tsn`
from the Everything lane — Excel's own AutoFit rejected the geometry three ways,
and each rejection is now a measured constant rather than an assumption:

| What Excel said | Why the first pass was short | Constant |
|---|---|---|
| A column stored as `46` reports `ColumnWidth 45.29`, and the label needs `46.00` | Excel's character width is the stored number minus 0.71, so a width computed in characters and stored raw is always that much narrow | `_STORED_WIDTH_OFFSET = 0.71` |
| `→ Comparison row:` needs `18.43` where the fit stored `18`; `TSN row (key-matched):` needs `22.29` where it stored `22` | rasterizing a 10 pt font at 13 px loses ~2.5 % per glyph to integer rounding, and the unhinted advance sum still runs 1.3–2.4 % under Excel's own | `_MEASURE_SCALE = 4` (oversample, then scale back) + `_MEASURE_MARGIN = 1.05` |
| `15213 ≠ 15410` needs `12.57` in a column the schema declared `12` | a declared `cmp_width` was being treated as a ceiling, so a schema could clip its own difference cells | a declared width is now a **floor**, never a ceiling |

After the correction, re-measured on the same real pair, **both twins**:

| Sheet | `columns_too_narrow` | `rows_too_short` |
|---|---|---|
| Summary | `[]` | `[]` |
| Spot Check | `[]` | `[]` |
| Comparison | `[]` | `[]` |
| Summary by Category | `[]` | `[]` |
| Provenance | `[]` | `[]` |

The oracle is Excel's own metrics, not an estimate: every populated cell whose
right neighbour blocks it from spilling is re-measured on a scratch sheet
carrying that cell's real font — an unwrapped cell must fit its column's STORED
width, and a wrapped cell's row must be at least the height Excel autofits to at
that width. Deliberately hidden columns (the state-mask chunks) and the
Stage-2-validated 45.75 pt wrapped header band are excluded as out of scope.
Witness: `HF-02\excel-metrics-ramp-summary{,2,3}.json` — the failing pass is
retained beside the passing one.

## Review 1 re-review remedy — `RB2-R1-EG-002`, one exact Git head

The re-review denied RB-2 again, and again correctly. The `RB2-R1-EG-001` remedy
bound the acceptance set by runtime **digest**, and the digest is content-derived
on purpose — so that a documentation-only commit provably cannot move it. That
property is real and still holds, but it is not the property Prompt 05 and
`RB2-A1` require. They require one exact **Git head**, and digest equality is not
head identity: a set split across two commits with byte-identical runtime content
digests the same while still spanning two heads.

It did. Of the 18 claimed results, 14 named `c483bda…`, three named `b37c1fe…`
(the small legs re-run after the records commit) and `generation-equivalence.json`
named no exact head at all — it recorded a digest per side and no commit. The
first verifier compared digests only, so it reported success over a two-head set.
A check that cannot fail on the defect it is meant to catch is not a check.

### What changed, and what deliberately did not

No bulk regeneration. The corpus, the Excel outputs, the prior evidence and the
runtime digest are exactly as they were; only the head binding and the verifier
were wrong.

| | |
|---|---|
| **The one acceptance head** | `c483bda1716e03d0e013b25e975bd9a41c58b2c8` |
| Re-run at that clean checkout | `frozen-inputs`, `evidence-determinism`, `provenance-final-commit` — the three that named `b37c1fe…` |
| Rebuilt to name an exact head | `generation-equivalence.json`, which previously carried digests but no commit |
| Claimed results now naming that head | **18 of 18** |

The four were re-run by checking the worktree out at `c483bda` and executing
them there, so each records the head it genuinely ran at rather than being
relabelled. They are cheap reads over the preserved corpus — the whole re-stamp
took under two minutes — which is why this required no regeneration.

`generation-equivalence.json` was rebuilt by
`acc_generation_equivalence.py`, retained beside the rest of the harness. It
re-derives the same comparison from the two generation records: 40 steps each,
31 `ok` each, 0 regressed, 0 newly ok, 9 refusals identical in kind, verdict
`EQUIVALENT` — unchanged conclusions, now with an exact head.

### The manifest no longer conflates two different facts

`acceptance_head` is now an explicit input rather than whatever the tree happens
to be at when the manifest is built. Those are different facts: the manifest and
the records are committed **after** the run they describe, so the build head is
legitimately later. The manifest records both, states which is which, and
requires every claimed entry to match the acceptance head.

### The verifier now fails where it passed

A new `EXACT HEAD` level rejects any claimed result that names no head or a
different one, and re-derives from git the commits between the acceptance head
and the manifest's build head — confirming none of them touches a runtime file
rather than accepting the manifest's word for it. The digest check remains, as a
necessary condition that is no longer mistaken for a sufficient one.

## Review 1 remedy — `RB2-R1-EG-001`, the acceptance set bound to one runtime head

Codex Review 1 denied RB-2 on one bounded precondition, and the denial was
correct. The first `RB2-A1` corpus was built across two different runtimes:
generation finished at `2026-07-29T07:51`, but the final production commit
`1a94183` — which changes the Provenance sheet written into **every** comparison
workbook — landed at `2026-07-30T00:43`, and only the four classic-environment
workbooks were regenerated after it. Nothing in any retained result said which
runtime had produced it, so the two passes could not be told apart from the
evidence. The full gate and the frozen self-test were also run at `00:25`/`00:28`,
before that commit.

The remedy is not a manifest bolted onto the old corpus. Review 1 explicitly
required the stale corpus to be regenerated rather than merely hashed, so the
whole acceptance chain was re-executed end to end against one frozen head.

### The runtime binding

`RB2-A1` now records what it ran on, in a form a reviewer can re-derive:

| Field | Value |
|---|---|
| Runtime head | `c483bda1716e03d0e013b25e975bd9a41c58b2c8`, working tree **clean** |
| Runtime digest | `1EFA63FD9EE6355008AD49BE6342E79DCE486A1BFF9FE1E9202F471600162279` |
| Runtime set | 152 `product` + 265 `gate` + 1 `oracle` = 418 tracked files |
| Base runtime | the base checkout, proved file-for-file identical to `896083e` |

The digest is taken over the **line-ending-normalised content** of every tracked
file that can change what the product writes. That choice is deliberate: this
repository runs `core.autocrlf=true`, so one commit checks out as different bytes
on different platforms while the content that decides behaviour is identical.
Because the digest is content-derived rather than commit-derived, a later
documentation-only commit provably cannot move it — which is what lets the
records, the manifest and the witnesses be committed *after* the run without
breaking the binding they describe. Committing the verifier demonstrated exactly
that: `e7a9a1a` → `c483bda` changed the head, and the runtime digest did not move.

Every acceptance result now carries this stamp inside it. A result produced under
a different runtime is visible as a mismatched digest instead of being
indistinguishable, which is precisely what Review 1 could not check.

### The denial answered by derivation, not assertion

Review 1's substantive point was that the corpus predated
`1a9418339e1c0df1cc16eddcaedb22dc1e4135d0`, the commit that changes the
Provenance sheet written into every comparison workbook. The manifest now
answers that mechanically, in `runtime.lineage`, computed from the same group
roots the digest uses:

| Derived fact | Value |
|---|---|
| Last commit touching ANY runtime file | `1a9418339e1c0df1cc16eddcaedb22dc1e4135d0` |
| …its subject | `fix: fit the Provenance role column to its real labels (RB-2)` |
| Runtime files changed between it and the acceptance head | **none** |
| Commits between it and the acceptance head | 3, all documentation/records |

The acceptance head is later than `1a94183`, and that is exactly the point: no
tracked runtime file changed in between, so the head's product behaviour **is**
that commit's behaviour and the regenerated corpus is same-final-head by
construction rather than by promise. The manifest derives this from Git rather
than restating it, and the verifier re-derives it independently — a manifest
that merely claimed the runtime had not moved would be worth nothing.

This is also what makes the ordering safe. The records, witnesses and manifest
are committed AFTER the corpus was generated; because none of them is a runtime
file, they cannot move the digest, and the same derivation stays true at
whatever head the reviewer checks out.

### The same fact, observed in the bytes

A structural argument can be wrong on its own, so the claim is also checked
where it would show: `1a94183` replaced Provenance column A's hard-coded width
of 12 with a fitted one, because on a cross-environment comparison the role is
the side's own name and 12 could never hold it. Both corpora were read back:

| Corpus | Provenance column A |
|---|---|
| base (code `896083e`) | **12.0** — the hard-coded value |
| head (regenerated) | **fitted wider on every workbook that has the sheet** |

Column A's value on those rows is literally `SSOR-PROD 2026-07-23` — the exact
case the commit describes. Witness: `HF-02\provenance-final-commit.json`, which
fails closed if any base workbook is not 12 or any head workbook is not wider.

Structural and observed agree, so "the corpus predates the final shared-writer
commit" is answered twice, by independent means.

### The defect is now structurally impossible

The first pass mixed runtimes because the generator's resume logic carried
`status=ok` records forward across a code change. It now refuses:

```
REFUSING TO RESUME: the existing witness was built by runtime DEADBEEFDEADBEEF…,
this run is 1EFA63FD9EE63550… — rebuilding every step
```

A witness with no runtime stamp at all is refused on the same grounds. Both
branches were exercised directly, not reasoned about.

### The prior pass is preserved, not overwritten

Every file of the superseded pass was hashed **before** being moved — 3,022 files
across the head corpus, the By Day publish root, the renders, the evidence probe
and the Excel workspace, plus 10 result files — and retained under
`…\HF-02\prior-A0\` with a `prior-run-record.json` binding each by path, size and
SHA-256. Nothing was deleted. The base corpus was not archived: base code has not
changed since the recorded base SHA, so it is re-used and re-bound rather than
rebuilt.

### The inputs are frozen — the same bytes, not the same paths

Before the re-run consumed anything:

| Check | Result |
|---|---|
| Normalised TSN datasets still hashing to the library's own rebuild record | **8 / 8** |
| Per-route exports byte-identical to what the superseded pass provisioned | **2,380 / 2,380**, 0 changed |

The second row is the strong form: the new run did not merely read files with the
same names, it read the same bytes the earlier pass read, so any base-vs-head
difference can only be the code. (31 further files under the store are producer
output — the consolidator's own workbooks and `owned_dir`'s ownership marker —
and are excluded as outputs rather than compared against an input archive.)

Witness: `HF-02\frozen-inputs.json`.

### The re-run is step-for-step equivalent

| | Prior pass | Same-head re-run |
|---|---|---|
| Steps | 40 | 40 |
| `ok` | 31 | 31 |
| Regressed | — | **0** |
| Newly ok | — | **0** |
| Refusals | 9 | **9, identical in kind** |
| Runtime recorded | **none — unstamped** | `1EFA63FD…` |

The nine refusals are the three families the audit itself excluded — Ramp Detail
(PCOA-FINAL-001, refused at the header gate until HF-04) and both Highway Detail
editions (the standing pre-release block; the frozen archive carries no HD
export) — across the Everything, By Day and Direct lanes. Witness:
`HF-02\generation-equivalence.json`.

### Nothing but presentation moved

The bundle's whole claim is that a workbook looks different and says different
things about itself, while every count, mask and typed outcome stays exactly
where it was. Every published cell of every truth-bearing sheet was compared
cell for cell across all 42 shared deliverable pairs, together with the typed
outcome sidecar:

| | Result |
|---|---:|
| Pairs compared | 42 |
| Pairs **changed** | **0** |
| Deliverables present on only one side | 0 / 0 |
| **Truth-bearing sheets with any differing row** | **0** |
| **Typed outcome sidecars unequal** | **0** |
| Presentation sheets that moved (the bundle's own surface) | 72 |

Truth-bearing here means everything except the five sheets this bundle is
allowed to touch: the Comparison sheet including its hidden `E`/`D`/`N`/`U`
state-mask columns, both Only-in sheets, both data sheets, Routes, and both
very-hidden `__CMP_E2_SNAPSHOT` sheets. The result carries both runtime digests
— head `1EFA63FD…`, base `54873CE5…` — so the record states exactly which two
runtimes it contrasted rather than leaving it to be assumed.

### The declared Spot Check boundary, now quantified against base code

The section above ("What installed Excel's own AutoFit found that RC-1 could
not") already declares four `Spot Check` cells as a boundary rather than a fix,
on the grounds that they display whichever Comparison row the reader types in at
runtime, so no stored width can be fitted to content that does not exist when
the workbook is written. That assessment stands, and re-measuring confirmed the
mechanism independently.

What it asserted without numbers was "this class is unchanged from base code".
That is now measured on both sides, because an unquantified "unchanged" is the
kind of claim this return exists to remove:

| Excel-measured cells narrower than their displayed content | Base | Head |
|---|---:|---:|
| `ssor-prod_intersection_detail_tsn.xlsx` | 96 | **2** |
| `ssor-prod_highway_sequence_tsn.xlsx` | 96 | **2** |
| Ramp Summary (both measured workbooks) | 0 | **0** |

So "unchanged from base code" was true of the four boundary cells but
understated the bundle: base code left **192** measured occurrences across these
two workbooks and head code leaves **4** — every occurrence on the Summary and
Comparison sheets removed, and all but four on Spot Check. The four that remain
are the declared boundary, and each is a cell holding a FORMULA:

| Cell | Stored | Needed | Displayed text |
|---|---:|---:|---|
| ID `Spot Check!r37c3`, `r37c4` | 23.29 | 25.00 | `VISTA DEL SOL/3 ARCH BY` |
| HSL `Spot Check!r22c4` | 23.29 | 25.14 | `JCT 5 CAMINO L RMBLS UC` |
| HSL `Spot Check!r22c6` | 38.00 | 47.00 | `COUNTY BEGIN: ORA ≠ JCT 5 CAMINO L RMBLS UC` |

Two details worth adding to the declaration. First, the neighbours of all four
are populated, so they cannot spill and are genuinely truncated on screen —
checked cell by cell rather than assumed. Second, the bundle did move one of
them: HSL `r22c6` was stored 29.29 under base code and is 38.00 under head, on
content needing 47.00. So the fitted-width logic reached it and improved it, and
still cannot finish the job, which is precisely the boundary's point. It is not
the 60.0 `_MAX_FITTED_WIDTH` cap — that is never reached here.

The reason the audit's own gate reports `0 clipped` while Excel reports these
four is not a contradiction but the stated limitation: the Stage 2 oracle reads
the workbook through openpyxl and sees a formula, never the string Excel
displays after calculating it. **Clipping figures from that oracle should
therefore never be restated as a bare "0" without this qualification.**

Witnesses: `HF-02\excel-metrics-final.json` (head) and
`HF-02\excel-metrics-base-spotcheck.json` (base, the same two workbooks).

### Installed Excel agrees with the cached headline, twin for twin

The formulas twin's whole purpose is that a real Excel recalculation reproduces
what the values twin already says. Eight workbooks were copied into a clean
workspace, opened in installed Excel, recalculated and read back:

| Comparison | Values twin headline | Formulas twin, after Excel recalculated it |
|---|---|---|
| Ramp Summary vs TSN | 23 differing cells, 2 one-sided rows | **identical** |
| Intersection Detail vs TSN | 5,092 differing cells, 687 one-sided rows | **identical** |
| Highway Sequence vs TSN | 5,573 differing cells, 15,958 one-sided rows | **identical** |
| Ramp Summary, classic environment | 67 differing cells, 0 one-sided rows | **identical** |

Across the eight: **70 workbook self-checks, 0 failing, 0 errors**, freshness
`OK` on every one. Each entry also records `source_sha256` beside the
workspace copy's `sha256_before`, and they are equal on all eight — the copy
Excel opened provably IS the current deliverable, which is what the
always-re-copy fix exists to guarantee. The previous behaviour skipped the copy
when file sizes matched, so a stale workbook could have been recalculated and
reported as current: the same staleness class as the denial itself.

### The evidence is unchanged, and now there is a record saying so

The evidence was rendered twice under a pinned sampling seed — once from the
base checkout, once from the head — producing 14 hashed artifacts per side.
Nothing compared them. Two hashed side files and no retained conclusion is the
same shape this return exists to fix, so the comparison is now computed, bound
and fail-closed:

| | Result |
|---|---|
| Pinned seed identical | yes (11223344 both sides) |
| Artifacts | 14 / 14, none one-sided |
| **Rendered images byte-identical** | **yes — 0 of 12 differ** |
| Evidence workbook | 1 differing row, on `Summary` |
| Evidence workbook after normalising the run's own location | **0 differing rows** |
| Ledger and all four evidence data sheets | **0 differing rows** |

The one moving row records where the run was launched: the base-side evidence
run executes from the base checkout, so it writes that checkout's path for its
TSN input. Both sides read the same bytes — the TSN library is proved frozen —
by different routes. Erase the tree prefix and the row is identical. The JSON
sidecar follows for the same reason: it records the workbook's digest and the
run's input paths.

Every row of every sheet is compared, not a sample, because a sampled claim
cannot support "no evidence content moved". Images are treated as the hard
requirement — if a rendered image had moved, the bundle would have changed what
the evidence SHOWS, and the leg fails. A differing evidence *workbook* is judged
on content instead of bytes, since that workbook is itself written by the shared
writer this bundle deliberately changes.

### Harness changes, and why they are trustworthy

Re-running the chain serially would have taken about 19½ hours, most of it in two
legs that were slow for accidental reasons. Both were fixed, and neither fix is
taken on faith:

| Leg | Change | How it was proved faithful |
|---|---|---|
| `acc_measure` | one process pool over independent workbooks | re-measured the **unchanged** base corpus and compared to the retained serial result — identical entry for entry |
| `acc_invariance` | the workbook was being re-opened once per sheet per side; now each pair is opened once and the two sides streamed in lockstep, over a pool | A/B'd against the **original** implementation on 9 pairs spanning all three lanes and both twins — 9/9 identical, field for field |
| `acc_excel` | always re-copies into the Excel workspace | it previously skipped the copy when the file size matched, which would have measured a stale workbook and called it current — the same staleness class as the denial |

Pool workers are spawned from the venv interpreter explicitly and each worker's
loaded `openpyxl` is recorded in the result. That is not ceremony: the bare base
interpreter on this machine resolves a *different* `openpyxl` install, so "which
library measured this" is a real question and is now answered by the record
rather than by assumption.

### The Visual row had a real root cause, and it was silent

Review 1 recorded that the render record "lacks complete artifact
hashes/runtime binding". Re-reading that leg found why, and it was worse than a
missing field: `render()` returned a LIST while its caller merged the result
with `{**origin, **render(...)}`. Unpacking a list there raises `TypeError`,
which the surrounding `except` swallowed into an entry with no renders **and no
error**. The retained record is two empty objects, and the leg exited 0.

Precisely: the PDFs themselves WERE exported — the archived prior run holds 10
of them — because the export happens before the return value is used. What was
lost was the record of them. Not one path, byte count or hash reached the
witness, so a reviewer had artifacts on disk that no result file referred to and
no manifest could bind. That is exactly the gap Review 1 named, and it was
invisible from the record alone because the record looked merely empty rather
than broken.

Three changes, because the missing hash was the least of it:

| Change | Why |
|---|---|
| `render()` returns a dict | the actual defect; the list could never merge |
| every rendered PDF carries its SHA-256 | Review 1's stated Visual gap — a render nobody can bind is a render nobody can check |
| the mode **exits non-zero** on any empty or errored entry, and on zero renders | a leg that produced nothing looked identical to a leg that succeeded, which is how this survived a whole acceptance pass |
| the output directory is `resolve()`d before it reaches COM | Excel resolves a relative path against ITS OWN default directory and fails with a bare "Document not saved" naming nothing — found by hitting it |

This was found before the step re-ran, and the fix was then proved out of band
on a real deliverable rather than assumed: four sheets exported, four PDFs on
disk, each carrying its byte size and SHA-256, the record runtime-stamped, zero
failures. The re-run is the first render result that is actually bound.

### Two measurement bugs found and fixed during the re-run

Re-measuring the corpus surfaced two defects in the acceptance harness itself.
Neither is a product defect, and both were putting wrong numbers into the
committed evidence, so both were fixed and BOTH measures were re-run:

| Bug | Effect | Fix |
|---|---|---|
| `missing_input` asked `is_file()` of every recorded selection | the classic lane compares **folders**, so three existing directories counted as **6 missing inputs** | ask `exists()`, and record each input's `kind` |
| twin flavor inferred from the file name (`"(formulas)" not in name` ⇒ values) | the matrix lane names the values twin `X.xlsx`, while the Direct and classic lanes name *that* file the FORMULAS twin — so **4** formulas workbooks were reported as values twins with a blank headline | decide flavor from the PAIR on disk, not the name |

The second one matters beyond the count: a formulas cell read through
`data_only` is *supposed* to be blank, because openpyxl writes a formula cell
with an empty `<v>`. Counting those as failures of PCOA-FINAL-019 would have
understated the fix while looking like a defect.

The totals are now scoped to what each finding is actually about — deliverables,
and the values twin specifically — with the unscoped figures kept alongside so
nothing is hidden. Every residual non-zero is accountable:

Measured at the frozen head over all 1,264 workbooks (60 of them deliverables,
30 per twin — a balanced split is itself the evidence that the flavor bug is
gone; the buggy pass reported 4 formulas twins as values):

**The headline, base code versus head code on the same frozen inputs:**

| | Base (`896083e`) | Head |
|---|---:|---:|
| Deliverables measured | 42 | 60 |
| **Clipped cells in deliverables** | **2,036** | **0** |
| Deliverables with at least one clipped cell | **42 of 42** | **0 of 60** |

Every deliverable the base code produced clipped something. None of the head's
do. (Head measures 60 to base's 42 because the base pass deliberately skips the
By Day lane; the extra lane is additional coverage, not a changed denominator —
the head figure is zero across all of them.)

> **Why `measure-base.json` carries the HEAD runtime digest, and why that is
> correct.** A runtime stamp records which code produced *that result*. Both
> measurements were taken by the head-side harness — that is the point, since
> measuring the two corpora with different measuring code would make the
> comparison meaningless. What differs is the code that GENERATED each corpus,
> and that is recorded separately: `base-identity.json` proves the base tree is
> the recorded base commit, and `invariance.json` carries `runtime_base`
> alongside `runtime_head`. Neither file claims the base corpus was built by
> head code.

| Figure | Value | Why |
|---|---|---|
| clipped cells, deliverables | **0** (base: 2,036) | the fix |
| clipped cells, evidence workbooks | 127 at head (63 + 63 + 1), 64 at base (63 + 1) | written by `visual_evidence.py`, which RB-2 does not touch and HF-02 puts out of scope. Identical **per evidence set** in both trees — head simply has one more set, because the base pass skips the By Day lane |
| `missing_input` across every deliverable | **0** | was 6, all of them the harness asking `is_file()` of a folder |
| `false_rebuild` / `temp_path` (HF-03) | **0 / 0** | by both independent methods, zip-XML probe and openpyxl walk |
| values twins with a real cached headline | **30 of 30** | PCOA-FINAL-019: the values twin must read correctly through `data_only` |
| formulas twins reading blank | **8 of 30** | correct — a formula cell has no cached value until Excel calculates it |
| formulas twins carrying `▶ PRESS F9 TO CALCULATE …` | **22 of 30** | also correct — the large-workbook path stores that literal instead of a formula |
| formulas twins with a real cached headline | **0 of 30** | correct — there is nothing to cache before calculation |

Every one of the 60 deliverable twins falls into exactly one accounted-for row,
and no residual is left as "expected" without a reason.

### The manifest — the item Review 1 asked for

`RB2-A1-manifest.json`, with the per-file listing of the two large input
archives in the companion `RB2-A1-sources.json` whose own SHA-256 the manifest
records. Together they bind, for the one runtime head:

| Required binding | Where |
|---|---|
| exact path | every entry, relative to a named and absolute root |
| byte size | every entry |
| SHA-256 | every entry, plus a root digest over each corpus |
| frozen-source identity | `frozen_sources`, per file, for the export archives and the normalised TSN library |
| generation metadata | per comparison workbook: generation id, completion, content digests, member count, and the provenance recipe with each input's kind, selection and `read_via` |

Nothing is sampled and nothing is summarised away.

### Retained is not the same as claimed

A manifest that swept up every JSON beside the corpus would have reported the
superseded pass's own record and several exploratory probes as unstamped gaps —
noise indistinguishable from the defect being fixed. Every retained file is
still bound by content; what changed is that each is CLASSIFIED:

| Class | Meaning | Same-head required |
|---|---|---|
| `acceptance` | a result RB2-A1 stands behind | **yes** — off-head or unstamped is a failure |
| `base_side` | describes the BASE checkout, so it carries the base runtime and says which | no; it must match the base digest instead |
| `source_record` | describes how a frozen INPUT was built | no; a head-stamped result vouches for it |
| `history` | the superseded pass's record and superseded probes, retained deliberately | no; claims nothing |

`source_record` has exactly one member, and it is the one Review 1 named:
`tsn_rebuild.json` "records dataset hashes but no `RB2-A1` runtime identity."
That is true, and it must stay true. Re-running it under the head would rebuild
the normalised TSN library — destroying the frozen-input identity the whole
acceptance set rests on. The correct answer is not to stamp it but to say what
it is, and to have a head-stamped result vouch for it: `frozen-inputs.json`
proves all 8 datasets still hash to exactly what that record wrote.

### One result was reporting itself unstamped when it was not

`generation-equivalence.json` compares the superseded pass to the same-head
re-run, so it records a runtime digest for each SIDE (`prior`, `current`) rather
than one for the file. The manifest reader looked only at the top level and
would have listed it as an unstamped gap — inventing a defect out of a
comparison-shaped schema. It now reads the current side's digest and records
that it did so.

The default is `acceptance`, deliberately: an unclassified result is treated as
claimed, so a future off-head result fails the manifest loudly rather than being
absorbed as history. The builder exits non-zero when any claimed result is
off-head, unstamped, or mislabelled — a manifest that quietly reported its own
gap is how the first pass shipped.

### What code produced the evidence

The acceptance harness is not product runtime, so it is deliberately outside the
runtime digest — but "which code produced this result" is a fair question, and
pointing at a temporary directory is not an answer. The manifest binds all 14
harness scripts by size and SHA-256, alongside the two committed pieces they
lean on: the Stage 2 clipping oracle (imported, never reimplemented, so the
product check and the acceptance oracle cannot diverge) and the verifier (which
deliberately shares no code with the manifest builder). The exact harness can
therefore be identified, supplied on request, and checked against these digests.

### Checked by re-derivation, not by assertion

`rb2-verify-manifest.py` is committed beside the audit and re-implements the
runtime digest from first principles — walking the same tracked groups,
normalising line endings and re-hashing — so a reviewer checks the claim rather
than the claimant. It has three levels: RUNTIME (re-derive the digest over all
418 files), WITNESSES (re-hash every committed record and require each to carry
the head runtime), and CORPUS (`--corpus`, re-hash the bulk output where it is
available, skipping cleanly where it is not).

Its failure paths were exercised rather than assumed: a tampered runtime file,
an off-head result, and a wrong witness hash each produce exit 1 naming the
offender. Reviewing it against this manifest also found that it PASSED a witness
carrying no runtime stamp at all — the exact condition Review 1 denied for — so
that path now fails, as does a claimed result with no stamp and a base-side
result not produced by the base runtime.

## Acceptance run `RB2-A1` — COMPLETE

One run, one head, executed end to end. 758 minutes of generation compute plus
the measurement, Excel and gate legs. Bulk output under
`…\_scratch\post-comparison-hotfixes\HF-02\` and `…\HF-03\`, with the whole
harness retained beside it so a reviewer can re-run any leg.

| Leg | Result |
|---|---|
| TSN library force rebuild | **8/8 datasets** current, through `build_consolidated(force=True)` |
| Head generation | **30 comparisons** — 18 By Day + 18 Everything matrix-lane workbooks, 18 Direct-lane controls, 6 classic environment twins |
| Base generation | **27 comparisons** — the same lanes minus By Day (see the scope note) |
| RC-1 clipping, deliverables | **2,036 → 0** |
| False rebuild instruction | **12 → 0** |
| `%TEMP%` in workbook / sidecar | **18 / 18 → 0 / 0**, both RC-3 methods agreeing |
| Recorded inputs that no longer exist | **18 → 0** |
| `(values)` twins with a blank headline | **12 → 0** |
| Invariance, 42 deliverable pairs | **0 changed**, **0 typed-outcome differences** |
| Installed-Excel recalculation, 8 workbooks | every SELF-CHECK **OK**, **0** error cells, twins agree live |
| Installed-Excel AutoFit | `columns_too_narrow: 0` after the Provenance fix; the Spot Check runtime class is a declared boundary |
| Capture directories left | **0** (the one crash orphan swept by the shipped code) |
| Evidence | unchanged — proved four ways, byte-identical under a pinned seed |
| Full gate | **158 passed, 0 failed of 158** |
| Ruff (gate-exact) | **All checks passed!** |
| Frozen self-test | **PASSED** — `SMOKE OK`, the EXACT shipped exe runs every code path (173 MB onefolder) |

### The measured before/after — base code vs head code, same frozen inputs

Both trees generated the same corpus from the same frozen archive and the same
TSN library on the same day, and every workbook was then measured by the audit's
own gate plus BOTH of RC-3's methods. Provisioned per-route source exports are
excluded (they are inputs, untouched by this bundle); in-flight `.tmp-`
artifacts and evidence workbooks are excluded for the reasons given elsewhere in
this record.

| Oracle, over the comparison DELIVERABLES | BASE `896083e` | HEAD |
|---|---:|---:|
| materially clipped cells (RC-1's own gate) | **2,036** | **0** |
| workbooks printing "rebuild the TSN library" | **12** | **0** |
| workbooks naming a `%TEMP%` path — zip probe / cell walk | **18 / 18** | **0 / 0** |
| `.provenance.json` naming a `%TEMP%` path | **18** | **0** |
| recorded input paths that no longer exist | **18** | **0** |
| deliverables carrying a stored literal headline | 15 | **52** |
| …of which readable `data_only` | 15 | **52** |
| workbooks named `(values)` with a BLANK `data_only` headline | **12** | **0** |

RC-3's two independent methods agree exactly on both trees (`zip == walk`), which
is what the contract requires of the re-derivation. The 18 base inputs that "no
longer exist" are PCOA-FINAL-003's harm stated numerically: the recorded TSN path
was a private capture directory that is deleted when the run ends.

**Disclosed, not buried — the evidence workbook has its own clipping, and this
bundle did not change it.** Running RC-1 over the WHOLE generated tree returns
64 (base) and 127 (head) rather than 0, and every one of those hits is inside an
EVIDENCE workbook. Per evidence SET the counts are identical in both trees —
Highway Log 63, Highway Sequence 1 — and head only shows more because it has an
extra set (the base pass deliberately skips the By Day lane). Evidence
presentation is written by `visual_evidence.py`, which this bundle does not
touch and which HF-02 places explicitly out of scope, so the pre-existing
evidence-workbook clipping is left exactly as found. It is recorded here and in
`clipping-before-after.json` (`non_deliverable_detail`) so a reviewer who
measures the whole tree sees the number explained rather than unexplained.

**Two corrections to the tally, both mine and both in the summary logic rather
than the product** — the raw measurement witness already contained what was
needed to see them:

1. A values twin was first identified by FILENAME. The classic and Direct lanes
   name the PRIMARY file the **formulas** workbook and `(values)` the twin — the
   inverse of the matrix lanes — so four formulas workbooks were misread as
   values twins with "blank" headlines. Identifying by whether stored `B3` is a
   formula gives **0 blank of 52**.
2. Recorded inputs were tested with `is_file()`, which is False for the classic
   lane's **folder** inputs. Testing existence gives **0 missing**.

### What installed Excel's own AutoFit found that RC-1 could not

Excel's metrics are stricter than the audit's gate, because the gate reads a
workbook data-only and therefore cannot see what a FORMULA renders. Run over the
final workbooks it reported six cells in two classes. Both are stated here; one
is fixed, one is a declared boundary.

**FIXED — `Provenance!A`, a hard-coded 12.** On a cross-environment comparison
the input's *role* is the side's own name (`SSOR-PROD 2026-07-23`), which needs
20.86. Column A's right neighbour is always populated, so it can never spill.
This is exactly the defect class HF-02 exists to remove, on a sheet this bundle
already modifies (the `read via` line), and it was a genuine miss in the first
pass: `_write_provenance_sheet` now fits column A to the real role labels. The
two classic environment pairs were regenerated and re-measured — **Excel
`columns_too_narrow: 0`, RC-1 `0 clipped`** on all four workbooks — and the full
gate re-run clean afterwards.

**DECLARED BOUNDARY — `Spot Check` value columns.** Four cells
(`Spot Check!r37c3/c4`, `r22c4/c6`) hold the values of whichever Comparison row
the reader types into the input cell at RUNTIME. Their content is not knowable
when the workbook is written, so no stored width can be fitted to it; the column
holds a fixed width and a longer value truncates visually, as in any
spreadsheet. This class is unchanged from base code, the audit did not flag it,
and the Spot Check cell the audit DID flag — the `B6` instruction — is fixed and
measures clean. Widening these to the widest value any field could contain would
push two columns to ~60 characters on every family for a runtime-only gain, so
the width is left as the schema's and the limitation recorded here instead.

### Installed-Excel recalculation — the twins agree, live

`CalculateFullRebuild` + Save in installed Excel, on COPIES, then an app-free
read of the cached results. The set is chosen to satisfy both contracts: both
schema shapes (summary / detail), both TSN identity classes (printing /
silent — HF-03 asks for "at least one family per identity class" in as many
words), both lanes (matrix / classic), and BOTH twins of each.

| Workbook | SELF-CHECK rows | non-OK | error cells | Excel's live verdict |
|---|---:|---:|---:|---|
| ramp_summary vs TSN — values | 7 | **0** | **0** | 23 cells, 2 one-sided |
| ramp_summary vs TSN — formulas | 7 | **0** | **0** | 23 cells, 2 one-sided |
| intersection_detail vs TSN — values | 11 | **0** | **0** | 5,092 cells, 687 one-sided |
| intersection_detail vs TSN — formulas | 11 | **0** | **0** | 5,092 cells, 687 one-sided |
| highway_sequence vs TSN — values | 10 | **0** | **0** | 5,573 cells, 15,958 one-sided |
| highway_sequence vs TSN — formulas | 10 | **0** | **0** | 5,573 cells, 15,958 one-sided |
| ramp_summary classic env — formulas | 7 | **0** | **0** | 67 cells, 0 one-sided |
| ramp_summary classic env — values | 7 | **0** | **0** | 67 cells, 0 one-sided |

**Every SELF-CHECK row OK, zero cached error values, and the twins agree
exactly**: for each family the verdict Excel computes LIVE in the formulas twin
equals the literal now stored in the values twin. For Highway Sequence that is a
triple agreement — `5,573 / 15,958` from the stored literal read `data_only`,
from Excel's own live recalculation, and from the typed `ComparisonOutcome`.

This is the real content of PCOA-FINAL-019's fix: the values twin's headline is
not merely non-empty, it is **correct**, and installed Excel says so. The
freshness SELF-CHECK reads `OK` on every unedited workbook, so the renamed
`REGENERATE REQUIRED` state does not misfire.

**Not recalculated, and why:** Highway Log and the remaining PDF-edition
families. RB-1 measured **68 minutes for a single statewide formulas twin**, so
recalculating all nine families both ways is 6–8 hours of Excel that would test
the same code paths already covered above. The boundary is stated here rather
than left for a reviewer to discover; under the owner's bounded-review ruling no
reviewer repeats this leg, so this record is its single source.

### Criterion 5 — nothing else moved, proved per family

Base code and head code generated the same corpus from the same frozen inputs on
the same day, and every deliverable pair was then compared cell for cell:

```
deliverable pairs compared                          : 42
pairs with ANY truth-sheet change or outcome change : 0
only in base: 0        only in head: 0
typed outcomes NOT equal                            : 0
```

"Truth-sheet" means everything except this bundle's own surface: the
`Comparison` sheet INCLUDING its hidden `E`/`D`/`N`/`U` state-mask columns, both
`Only in …` sheets, both data sheets, `Routes`, both very-hidden
`__CMP_E2_SNAPSHOT_A/B` sheets, and any extra rollup. Zero differing rows across
all 42 pairs, and every typed `ComparisonOutcome` — counts, verdict,
pairing_quality — identical. That satisfies HF-02 criterion 5 and HF-03
criterion 5 together, including "Direct-lane workbooks unchanged".

### Criterion 4 — the capture lifecycle, and the one directory that remained

36 matrix-lane cells ran, each taking a private TSN capture. After the run,
**one** `tsmis-tsn-consumer-*` directory remained, and its provenance is exact
rather than mysterious: it was created **2026-07-29 04:12:31**, the moment a
session crash HARD-KILLED the run mid `byday|tsn|intersection_detail`. No
`finally` clause survives a kill — which is the entire reason
`_sweep_stale_tsn_captures` exists.

It was not swept during this run for a reason that is the age bound working
correctly, not failing: the head pass's captures all ran 04:58–07:51, when that
directory was 0.8–3.6 h old — INSIDE the 6 h bound that stops the sweep from
racing a capture another process may still be holding. The base pass (07:52–
13:30) runs pre-fix code, which has no sweep at all.

`matrix_build._sweep_stale_tsn_captures` — the same call `captured_tsn_workbook`
makes at every capture — was then run against that real 20-hour-old orphan:

```
before sweep: 1  tsmis-tsn-consumer-cvzbqzqw  age 20.0 h
after sweep : 0
```

A genuine orphan left by a killed process, removed by the shipped code. The
success, failure and cancellation paths are proved separately and hermetically
by `check_tsn_canonical_consumer_identity`. Witness:
`HF-03/witness/temp-capture-lifecycle.json`.

### The Everything lane — 9 of 9 audited families, and why the other three are out

| Family | Result |
|---|---|
| Ramp Summary · Highway Sequence · Highway Log · Intersection Summary · Intersection Detail · Highway Log (PDF) · Intersection Detail (PDF) · Highway Sequence (PDF) · Ramp Detail (PDF) | **ok — all 9**, both twins each |
| Ramp Detail (Excel) | `error` — *"isn't a CONSOLIDATED Ramp Detail workbook (expected a leading 'Route' column)"*. This is **PCOA-FINAL-001 reproducing exactly**, the finding RB-3/HF-04 owns. It is a graceful, correct refusal, not a crash |
| Highway Detail · Highway Detail (PDF) | `EXCEPTION` — *"the Highway Detail output folder doesn't exist yet"* / *"No TSMIS Highway Detail (PDF) files were found"* |

The Highway Detail result is worth stating precisely, because it **independently
corroborates the standing pre-release block from the frozen input itself**: the
provisioning step copied the archive's own export folders into the store and
reported `highway_detail_pdf: 0 files`. The 2026-07-23 archive carries no
Highway Detail export at all — which is exactly what "the vendor greyed the
exports out again" means on disk. Nothing was inferred about HD, no HD artifact
was produced, and no HD canary was touched.

These three are excluded from the harness's retry test by name: neither is
RB-2's defect, and neither is fixable by retrying, so neither may stop the
acceptance chain. Every other failure class still triggers a retry.

### What the base-code pass covers, and the one lane it deliberately omits

The base tree (`main` @ `896083e`, its `scripts/` copied verbatim, reading the
SAME TSN library and the SAME frozen run folders through junctions) exists for
exactly one claim: HF-02 criterion 5 — every count, mask and typed outcome
unchanged, **proved per family**. It runs the Everything lane for all 12
families plus the Direct and classic lanes.

It does **not** re-run the By Day lane, and that is a redundancy removal rather
than sampling: By Day drives the same comparator over the same consolidated
store and the same TSN library as the Everything lane, so a base pass over it
would re-derive numbers already proved for that family and nothing else. **No
family loses its base-vs-head diff.**

HF-03's before/after classification needs no base pass at all — the "before"
table is the committed Stage 2 witness (`stage2-tsn-provenance-scope.json`:
18 workbooks per lane, 12 warned, 18 carrying a `%TEMP%` path) and the "after"
is this run's head, re-derived independently by both of RC-3's methods.

### Early confirmations on real data

The first regenerated matrix-lane workbook already carries every HF-03 outcome
the finding demanded, on the real corpus rather than a fixture:

| Oracle | Pre-fix (audited) | This run |
|---|---|---|
| `Summary by Category!A6` | *"TSN print: no source-claims record beside this normalized workbook (older normalization) — rebuild the TSN library to capture the print identity."* | **`TSN print identity: OTM22270 · Event 4843742 · reference 09/15/2025 · submitted by TRLBUGNI · generated 05:10 PM (STATEWIDE).`** — the exact line the audit's Direct-lane controlled differential recorded |
| occurrences of "rebuild the TSN library" | 1 | **0** |
| `%TEMP%` strings anywhere in the workbook | present | **0** |
| `.provenance.json` TSN `selection` | `…\AppData\Local\Temp\tsmis-tsn-consumer-…\tsn_ramp_summary_normalized.xlsx` | `…\tsn_library\ramp_summary\consolidated\tsn_ramp_summary_normalized.xlsx` — **exists and is readable after the run**, with `read_via: verified private copy of the selection` |
| values twin `Summary!B3` read `data_only` | `None` | `✗ DIFFERENCES FOUND — 23 differing cell(s), 2 one-sided row(s) — details below.` |

**Criterion 1 on real statewide workbooks.** The audit's own gate, run read-only
over three committed workbooks from this run (no Excel, nothing written into the
generated tree):

| Workbook | Stage 2 recorded | This run |
|---|---:|---:|
| `ssor-prod_intersection_summary_tsn.xlsx` | **70** | **0** |
| `ssor-prod_highway_sequence_tsn.xlsx` (the family whose PDF sibling recorded 82) | — | **0** |
| `ssor-prod_intersection_detail_tsn.xlsx` (statewide detail, 29 MB) | — | **0** |

**HF-03 criteria 1 and 3, swept across every deliverable built so far.** The
zip/sheet-XML probe (RC-3 method 1 — never opens the object model) over the 14
comparison workbooks committed by the Everything lane at that point:

```
14 comparison deliverables: false-rebuild=0  temp-path=0
```

and the TSN print identities carried are exactly the codes the audit recorded
for the Direct lane, family by family:

| Family | Identity in the matrix-lane workbook | Audit's Direct-lane control |
|---|---|---|
| Highway Log (both editions) | `OTM52010` | `OTM52010 California State Highway Log · report 09/15/25` |
| Highway Sequence | `OTM22025` | `OTM22025 Highway Locations · report 15-SEP-25` |
| Intersection Summary | `OTM22250` | `OTM22250 · Event 4843738 · 09/15/2025` |
| Ramp Summary | `OTM22270` | `OTM22270 · Event 4843742 · reference 09/15/2025 · TRLBUGNI` |
| Intersection Detail | *(none)* | identity-silent **by design** — the contract requires it gain the honest provenance path but **no invented identity line**, and it has |

**HF-03 criterion 2, as written — the SAME LINE on all three lanes.** Not the
report code: the entire identity string, compared character for character
between the Direct-lane control and both matrix lanes.

| Family | The line, identical on Direct · Everything · By Day |
|---|---|
| Ramp Summary | `TSN print identity: OTM22270 · Event 4843742 · reference 09/15/2025 · submitted by TRLBUGNI · generated 05:10 PM (STATEWIDE).` |
| Intersection Summary | `TSN print identity: OTM22250 · Event 4843738 · reference 09/15/2025 · submitted by TRLBUGNI · generated 04:53 PM (STATEWIDE).` |
| Highway Sequence | `TSN print identity: OTM22025 Highway Locations · report 15-SEP-25 · reference 15 SEP 2025 · 12 district print(s).` |
| Highway Log | `TSN print identity: OTM52010 California State Highway Log · report 09/15/25 · cover year 2025 · 12 district print(s).` |

`ALL 3 LANES IDENTICAL: True` for every one. Before the fix each matrix lane
instead printed *"TSN print: no source-claims record beside this normalized
workbook (older normalization) — rebuild the TSN library to capture the print
identity."* — the categorically false instruction PCOA-FINAL-002 was raised on.

**The audit's worst measured cell — identity widened, instruction wrapped.**
Ramp Summary classic environment, `Summary!B13:B14`, recorded **364 px short**,
the largest overrun in the whole audit. Fitting it by width alone would need a
~93-character column, so the planner's sketch chose wrapping for instructions
and widening for identities. That is exactly what the workbook now does:

```
ramp_summary new-vs-prior-ssor (values).xlsx: 0 materially clipped   (was 5)

Summary column B stored width: 46.0        <- unchanged
  B13: wrap=True  row_height=45.0  "In SSOR-PROD 2026-07-23 only (missing from ..."
  B14: wrap=True  row_height=45.0  "In SSOR-PROD 2026-07-09 only (missing from ..."
  B15: wrap=False row_height=None  'FIELD-LEVEL DISCREPANCIES (matched rows)'
```

`B15` is the control: a short banner in the same column, untouched and still
unwrapped at the default height. Only cells that would actually clip changed,
and the sheet did not get wider.

**Criterion 3 — PCOA-FINAL-014's named test, on the real Highway Sequence vs TSN
workbook.** The finding names `City`, `HG` and `Distance To Next Point`
specifically; the *DIFFERENCES BY FIELD* table now reads:

| Field | Col | # of cells differing |
|---|---|---|
| County | H | `0` |
| **City** | I | **`not compared (context)`** |
| **HG** | J | **`not compared (context)`** |
| FT | K | `690` |
| **Distance To Next Point** | L | **`not compared (context)`** |
| Description | M | `4,883` |

`County` is the control the finding demands: a genuinely COMPARED column with
zero differences still reports a real `0`, so the two cases stay
distinguishable. The compared counts also still reconcile —
`690 + 4,883 = 5,573`, exactly the headline's differing-cell total, which the
values twin now publishes as a stored literal:
`✗ DIFFERENCES FOUND — 5,573 differing cell(s), 15,958 one-sided row(s)`
(criterion 4).

## Evidence is unchanged — proved four ways, not asserted

Both contracts require evidence to be unchanged: HF-02 *"assert evidence
artifacts are unchanged and that no new artifact appears"*, HF-03 *"this bundle
must not create, retire, or relabel any evidence artifact"*. A naive cell diff
of two evidence workbooks does NOT prove that, and would in fact fail — for a
reason that has nothing to do with this bundle. The proof is therefore layered,
and the last layer is a measurement rather than an argument.

**1. The code cannot have changed it.** `git diff 896083e..HEAD --name-only`
lists thirteen files. Not one is an evidence file: `visual_evidence.py`, every
`evidence_*.py`, `published_comparison.py`, `evidence_ledger.py` and
`evidence_manifest.py` have **zero lines changed**. "Created, retired or
relabelled" is settled by inspection alone.

**2. The variation is the product's own, by design.** `visual_evidence.generate`
draws a fresh cryptographic seed per run — `seed = int.from_bytes(os.urandom(4),
"big")` — and stamps it into the workbook as *"sample seed"*. The module's own
docstring states the intent: *"sample random example rows (random routes — not
just the first)"*. Three retained sets carry three different seeds
(`2dbfeb9b`, `2911f7cd`, `76b5e4a3`).

**3. Measured on artifacts that already existed.** Two evidence sets generated by
the **same head code** from the same frozen inputs (the Everything and By Day
lanes) differ by **24 rows**. Head vs base differs by **23**. Identical code
differs from itself MORE than it differs across this change, so the variation
demonstrably is not RB-2.

**4. Remove the randomness and the difference disappears.** The seed alone is not
enough: the candidate pool is a set, so Python's per-process hash randomisation
reorders it. With BOTH `os.urandom` pinned to a fixed seed (`11223344`) and
`PYTHONHASHSEED=0`, the SAME comparison workbook, the SAME source PDFs and one
SHARED staging path, `visual_evidence.generate` was run under each tree:

| Oracle | Result |
|---|---|
| rendered examples / misses | `6 vs 6` / `{} vs {}` |
| artifacts, and their names | 14 vs 14, name sets identical |
| **rendered images byte-identical** | **12 of 12** |
| manifest `read_set` — by content digest | **identical** (13 members each) |
| manifest `ledger_digest` | **identical** — the hash-bound exhaustive ledger built BEFORE any sample is drawn |
| every other manifest key | identical: `comparison`, `difference_cells`, `differing_columns`, `examples`, `images`, `layout`, `note`, `reader_version`, `report`, `seed`, `state`, `version` |
| evidence workbook | **1** differing row |

The two residual differences are recorded **pathnames of the same files**: the
base tree reaches the shared TSN library through a junction, so it records
`…\base-tree\tsn_library\…` where head records
`…\TSMIS-rb2-worktree\tsn_library\…`. The read-set DIGESTS are identical, so the
same bytes were read under both — the names differ, the content cannot. This is
the same worktree-path phenomenon RB-1 documented for four Provenance cells.

Witness: `HF-02\evdet\{head,base}.json` (each run's artifact hashes and note).

## Method note — never measure the live output tree

An early measurement pass ran installed Excel over a workbook **inside** the
generated tree while the generation still held its `owned_dir` lease. Excel
writes lock/temp files beside the workbook it opens, the comparisons directory's
identity changed, and the very next cell refused to commit:

> Refusing to write the comparison: destination ownership changed while …

**The app was right and the measurement was wrong.** The refusal is exactly the
transactional/ownership contract working — a partial refresh kept last-good, and
the app's own identity-bound artifact temp (`…tmp-ed785a1adfa5.xlsx`) was left
rather than a half-written deliverable. The harness now copies every workbook
into a separate `excel-workspace` before any Excel call, and all installed-Excel
legs run only after generation finishes. A reviewer re-running `RB2-A1` must do
the same.

## Scope and residual risk

- **Out-of-scope files changed: none.** The diff is exactly `compare_core.py`, `summary_layout.py`, `matrix_build.py`, `compare_tsn_common.py`, one new check, four existing checks, and this bundle's records.
- **A source with no producer outcome record gets today's behaviour.** The capture's origin record rides the outcome sidecar, which `captured_tsn_workbook` only writes when the source itself has a trusted producer outcome — true for every canonical library workbook and therefore for all 36 matrix-lane workbooks. An explicitly picked file with no sidecar keeps recording the literal path it was read from, which remains honest.
- **The values twin's headline is now build-time state.** That is the finding's own first acceptance branch and the plan's design sketch. The live certification guard did not weaken: the freshness SELF-CHECK row is still live in both flavors, still keyed on both very-hidden E2 snapshot sheets, and now states `REGENERATE REQUIRED` in words. Three policy checks were re-pointed to that cell rather than deleted.
- **Column widths move in every regenerated workbook.** No count, mask, schema version or sidecar changes, so committed comparison generations stay valid and `read_counts`' header-label lookup is unaffected.
