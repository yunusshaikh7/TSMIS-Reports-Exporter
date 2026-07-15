# Second opinion — adversarial comparison audit (CMP-AUD-001…120)

Date: 2026-07-11
Role: independent pre-implementation review of `docs/planning/comparison-perfection/comparison-audit-findings.md`.
No product code, ledger content, or other planning files were modified; the only file this
review writes is this one.

**Method.** The 120 findings were treated as claims. For the six priority clusters I read the
cited executable code directly and re-derived each mechanism from source; where practical I
re-reproduced with disposable fixtures (scratchpad only, plus one live-Excel COM recalculation
of a freshly built comparison workbook). Two read-only sub-reviews verified the UI/state
cluster and the census. The v0.18.0 planning corpus, `outcome.py`, `cache_envelope.py`,
`consolidation_meta.py`, and the current owning docs were read as design-intent evidence for
the context questions. Findings outside the priority clusters (mostly the PDF-parser chunk)
were spot-checked for mechanism plausibility, not independently re-reproduced; that is stated
per finding.

**Bottom line.** The ledger is substantially correct — every priority-cluster finding I could
test reproduced, several with sharper evidence than the ledger records. I found **no false
finding**, but I found **one finding that must be split because half of it is
per-plan-intended behavior** (CMP-AUD-085), **three findings whose blast radius is
overstated** (016, 099, 101), several places where the ledger under-uses design history the
code itself documents, and a handful of defects the audit missed (greedy pairing
non-monotonicity, `read_counts` inheriting the marker ambiguity, the `ensure_owned_dir`
root cause, an intra-doc contract contradiction that MUST be settled before coding 085).

---

## 1. Executable capability census — CONFIRMED

Independently recomputed by importing the live registries (`reports`, `matrix_state`,
`tsn_library`) — not by reading the ledger's tables:

| Claim | My count | Verdict |
|---|---|---|
| 29 classic Compare recipes | `COMPARE_REPORTS`/`COMPARE_KEYS` = **29** (17 `files` + 12 `folders`) | Confirmed |
| 12 Everything-Matrix rows | `reports.matrix_rows()` = **12** | Confirmed |
| 30 supported matrix placements | Enumerating `matrix_state._row_modes` over all rows: **30** supported (12 env + 12 tsn + 6 self) | Confirmed |
| 7 canonical TSN datasets | `tsn_library.reports()` = **7** (`highway_log` v3, `ramp_detail` v3, `ramp_summary` v2, `intersection_summary` v2, `intersection_detail` v3, `highway_sequence` v2, `highway_detail` v2); the 12 tsn modes map onto exactly these 7 subdirs | Confirmed |
| 5 unique PDF↔Excel self-checks | 6 self **placements**, resolving to **5 unique comparator objects** — the Highway Log row's `vs_pdf` and the Highway Log (PDF) row's `vs_excel` share one `TSMIS_PDF_VS_EXCEL` instance | Confirmed |

Corroborating detail: the recipe **group** census is `env=17, tsn=12` — i.e., the five
self-checks really are filed inside the `env` group (CMP-AUD-014 confirmed by count).
`DISABLED_EXPORT_SUBDIRS` has **1** entry and `EXPORT_KEYS` has **16** (15 enabled +
disabled Route History), and the code's Ramp Detail TSN `normalization_version` is **3** —
all three corroborate CMP-AUD-086's claims that current docs saying "empty", "16 live-verify
rows", and "v2" are stale.

---

## 2. Cluster 1 — comparison truth and equality

### CMP-AUD-001 — formulas vs values equality semantics — **Confirmed, P1**

- Python side executed: `compared_cell` ends in case-sensitive `va == vb`
  (`scripts/compare_core.py:391`) over `_xl_trim` (`:319-325`, which also coerces integral
  floats, so `5.0` vs `"5"` compare equal in Python). `"ABC"` vs `"abc"` → **different** in
  the values model.
- Excel side executed **live** (my own COM run, not the audit's): I built a fresh both-mode
  workbook via the real `run_compare` with rows `k1: ("ABC","06v")` vs `("abc","6V")` and
  `k2: ("North ≠ South", ".50")` vs `("North ≠ South", "0.5")`, ran
  `CalculateFullRebuild()`:
  - **live formulas**: `Diffs(k1)=0`, `Diffs(k2)=1`, Summary "Total differing cells" = **1**;
  - **values twin** (openpyxl readback): `Diffs(k1)=2`, `Diffs(k2)=2` (sum **4**), cells
    literally `ABC ≠ abc`, `06v ≠ 6V`, `.50 ≠ 0.5`;
  - **Python `count_diffs`** for the same inputs = **3**.
  One comparison, three different totals across its own advertised surfaces. This is
  stronger than the ledger's 3/4/6 example and fully independent.
- Correction constraint the ledger missed: `matrix_state.read_counts` (see §CMP-AUD-004
  below) and validation's counts consume the **values** semantics, while a user pressing F9
  consumes the **live** semantics — so the cache/validation layer must be included in the
  "one equality contract" migration, or the matrix and the opened workbook will still
  disagree after the fix.
- Required tests: the ledger's real-Excel case list is right; add "the three surfaces agree"
  as a single assertion (live Summary == values Summary == Python counts) per fixture.

### CMP-AUD-002 — Med-Wid normalization divergence — **Confirmed, P1**

Executed both halves: Python `_medwid_norm` (`compare_core.py:339-355`, unsigned
`\d+(\.\d+)?` only, suffix case preserved) gives `06v≠6V`, `-06V≠-6V`, `.50≠0.5` as
**different**; my live-Excel run shows `06v`/`6V` and `.50`/`0.5` as **equal**
(`VALUE(LEFT(...))&RIGHT(...)` + case-insensitive `=`, `_medwid_ref` at `:665-669`).
The `0Z`/`00Z` documented pair works in both. No disagreement with the ledger.

### CMP-AUD-003 — Excel error cells hide differences — **Confirmed, P1** (mechanism executed; full fixture not re-run)

I verified the load-bearing premise executably: openpyxl assigns `data_type='e'` to a
**string** `"#N/A"` — including through `compare_core._styled(..., guard=True)`, because the
injection guard checks only `=,+,-,@` (`compare_core.py:749-754`) and not
`openpyxl ERROR_CODES`. So error-text input becomes a **live error cell** on the data
sheets; `TRIM(INDEX(...))` propagates it; `SUMPRODUCT(--ISNUMBER(SEARCH(...)))`
(`:923-924`) yields FALSE for the error row → Diffs 0 → clean Summary. The audit's
`#N/A vs OK` and `#N/A vs #N/A` live results follow necessarily. Correction constraint the
ledger missed: **extend the literal-cell guard to `ERROR_CODES`** (write error-text as
strings) — it is the same one-line class of fix as the formula-lead guard and closes the
data-sheet half regardless of the counting redesign.

### CMP-AUD-004 — literal `≠`-marker text corrupts counts — **Confirmed, P1** (live)

Reproduced end-to-end: an **equal** value `North ≠ South` produced `compared_cell` verdict
equal, `_field_value` containing the marker, values-mode `Diffs=1` (`compare_core.py:937`),
and — in my live COM run — live `Diffs(k2)=1` + Summary total 1 counted **solely** from the
false marker hit. Two additions the ledger missed:

1. **`matrix_state.read_counts` uses the same marker scan** (`matrix_state.py:191`:
   `if isinstance(v, str) and _NEQ in v`). The matrix cache, day/baseline caches, and
   validation counts all inherit the ambiguity. Any fix that stores structured per-cell
   state must also re-point `read_counts` (or replace it with result-carried counts,
   CMP-AUD-077), else the cells and the workbook diverge again.
2. The conditional formatting (`:894-897`) keys on the same `SEARCH`, so equal
   marker-bearing values also render red — worth one display assertion in the fix.

### CMP-AUD-005 — pipe-flattened helper keys collide — **Confirmed, P1**

Executed: `keys_for` keeps `("R|X","K",1)` and `("R","X|K",1)` distinct as tuples, and the
helper strings `f"{route}|{loc}|{occ}"` (`compare_core.py:1835-1838`; the formula twin at
`:622-626`) both flatten to `R|X|K|1`. Excel `MATCH` first-wins behavior is standard; the
audit's zero-diff live result follows. Confirmed as written; the length-prefix/injective
encoding correction is right, with the caveat that helper-key text is part of the
regression-locked byte surface — this fix **requires** a locked-engine re-proof cycle.

### CMP-AUD-012 — Spot Check renders blank as zero — **Confirmed, P2** (static + Excel semantics)

`raw()` wraps as-stored cells in `IF(ISBLANK(...))` (`compare_core.py:1129-1131`) but the
"Comparison sheet shows" cell is bare `=IFERROR(INDEX(...),"")` (`:1162`), and in the values
flavor an empty field is appended as `None` (`:939`), i.e., a genuinely blank cell → Excel
`INDEX` → `0`. `Agree?` checks marker presence only (`:1167-1171`). Consistent with the
ledger; I did not re-run this specific case in COM.

### CMP-AUD-039 — Report View is a second equality engine — **Confirmed, P1**

`compare_intersection_detail_tsn.py:692-696` (`aval`: `str(v).strip()`) compares raw
strings, so internal-space runs and Med-Wid equivalences that `compared_cell` folds are
reported as Report View differences. The Highway Detail twin is the same pattern. One
strengthening the ledger missed: `docs/comparison-engine.md:911` explicitly documents that
evidence/secondary surfaces illustrate "columns THAT row's comparison counts" — so the
one-equality-engine requirement is already the documented contract, not a new invention.

### CMP-AUD-043 — Report View stays stale after live recalc — **Confirmed (static), P1**

The Report View writers emit literal snapshot values in both flavors (the `aval` values feed
`ws.append`-style literals; no `INDEX`/`MATCH` into the data sheets). The audit's COM result
(Comparison/Summary/Spot Check update; Report View frozen; self-checks stay OK because none
covers Report View) follows from construction. Correction constraint: whichever way this is
resolved, **add Report View to the Summary SELF-CHECK block** — the self-check design's gap
(no cross-check covers the sheet) is what let two answers coexist silently.

### Cluster-1 additions the audit missed

- **CMP-AUD-008 is understated in one respect** (verdict on 008 itself: Confirmed, P2 —
  but with a new correction constraint). The engine's docstring claims the pairing "can only
  REMOVE phantom diffs, never add one" (`compare_core.py:366-370`). That is only proven for
  the exact-permutation branch. I constructed an 8×8 cost matrix (greedy branch, since
  `perm(8,8)=40320 > 5040`) where the greedy fallback scores **56** while plain file order
  scores **8**: greedy pairing can *create* phantom diffs relative to the pre-v0.14 behavior,
  not merely be sub-optimal. Any fix (or any decision to keep greedy) must either restore
  the monotonicity invariant (e.g., fall back to file order whenever greedy's total exceeds
  the positional total — a two-line guard) or delete the docstring claim and re-bless. Note
  the v0.18 plan explicitly deferred this ("min-cost-pairs-greedy-not-optimal … Deferred
  (repo-backed)… needs a locked-engine change + full cell re-proof"), so the ledger should
  cross-reference that standing decision rather than treat it as newly discovered.
- **`norm_pm`'s own docstring contradicts its behavior** (`compare_tsn_common.py:91-95`
  claims "'0.606' stays distinct from '000.606'"; executed: both → `0.606`). Trivial, but it
  shows the comment layer around CMP-AUD-006 cannot be trusted as the spec — the correction
  for 006 must start by writing the PM canon down somewhere authoritative.

---

## 3. Cluster 2 — completeness and validation

### CMP-AUD-017 — skipped inputs lose partial state — **Confirmed, P1** (end-to-end)

Reproduced mechanically: `run_compare(..., warnings=[...])` returns
`status=ok, verdict=diff, completion=None, skipped_inputs=0, failed_inputs=0`
(`compare_core.py:1967-1968` simply never sets the fields), while the workbook itself
correctly says "⚠ COULD NOT COMPARE EVERYTHING". `matrix_build.py:177` then coerces
`completion=result.completion or outcome.COMPLETE`; `read_counts` on my fixture returned
`(0,0)`; and the renderer (`ui-matrix.js:284-299`) decides from counts+completion — the
recorded `verdict="diff"` is never consulted — landing in the green
`mx-match / ✓ match / identical` branch. Full chain verified.

Reframing that matters for the fix: the defect is **`run_compare` was never made an outcome
producer**. v0.18's R1-R02 rolled `completion` out to "consolidate_xlsx_base + PDF/TSN
consolidators" only; comparisons were assumed complete-by-construction, and the `warnings`
path (unreadable per-route files) falsifies that assumption. The renderer's own comment
(`ui-matrix.js:290-294`: "Cross-env cells carry no completion, so they're unaffected")
documents the wrong assumption. So the correction is exactly the ledger's: make
`run_compare` set `completion=PARTIAL` + structured counts when `warnings` is non-empty,
and additionally make the renderer treat a recorded `verdict="diff"` with 0/0 counts as a
contradiction (fail visible), not a green.

### CMP-AUD-007 — validation omits five PDF rows and selected TSN files — **Confirmed, P1**

Verified both omission classes in source: `_comparisons_stage` passes the row's raw export
`subdir` to `_ensure_tsn_ready` (`validation.py:196-200`), which requires
`tsn_library.is_registered(subdir)` — the five `*_pdf` subdirs are not among the 7 registered
datasets, while production routing maps them via `_row_modes(...)['tsn_subdir']`
(`matrix_state.py:356-389`) and `tsn_subdir_for` (`:477-485`). And `_run_one` calls
`matrix.build_comparison(dest, row_key, env, "tsn", baseline, events)` without the
`tsn_files=` parameter the signature offers (`matrix_build.py:576-578`), so an explicit
selection is ignored. Denominator claim confirmed: skipped rows carry no `"status"` key so
they drop out of `ran` (`validation.py:232`). Fix should reuse `tsn_subdir_for` — the
correct mapping already exists; validation just bypassed it.

### CMP-AUD-011 — worker drops partial count and failure message — **Confirmed, P2**

`gui_worker_maint.py:192-198`: the terminal carries `comparisons_run/ok/cancelled` only —
`comparisons_partial` (computed at `validation.py:238`) is dropped, and on `res.ok=False`
no `message` from `evidence.collect`'s result is forwarded. Both halves verified in source.

### CMP-AUD-026 — PDF paths discard producer completeness — **Confirmed, P1**

Env half verified: all five `_load_*_pdf_side` loaders check `res.status` only
(`compare_env.py:349-352` and parallels) and discard
`completion/skipped_inputs/failed_inputs`. Direct half verified: `run_files_compare`
(`compare_tsn_common.py:172-222`) never consults `consolidation_meta.read_completion` on its
inputs. The correction must thread producer completion through **both** the env loaders and
the shared file driver; note `day_matrix.build_day_cell:415-418` already shows the intended
consumer-side pattern (P1-B05 reduces the TSN side's partial into the cell result) — extend
that pattern rather than inventing a new one.

### CMP-AUD-075 — both-mode completion persisted for one output — **Confirmed, P1**

`gui_compare_api._launch_compare` commits via `commit_workbook(..., twin=mode=="both")` and
`ConsolidateWorker` writes exactly one sidecar at `result.output_path`
(`gui_worker_export.py:591`). `commit_workbook` flips `output_path` to the values twin when
the formulas commit fails (`artifact_store.py:307-317`), so which artifact carries the truth
sidecar depends on commit order — exactly as the ledger says. Note the values-canonical /
formulas-best-effort **ordering itself is the v0.18 plan's Q5 policy** (final plan lines
297-302); the defect is only the single-sidecar publication, so the fix is "publish the
outcome beside every committed artifact", not a transaction redesign.

### CMP-AUD-077 — structured counts discarded — **Confirmed, P2**

`run_compare` computes `counts` and returns only verdict + `summary_lines`
(`compare_core.py:1909-1968`). Straightforward; fixing it is the enabling move for 001/004's
"one truth" requirement and removes the `read_counts` re-scrape entirely.

### CMP-AUD-085 — partial artifacts overwrite last-good and remain fresh — **SPLIT: half Reframed (intended per plan), half Confirmed P1**

This is my largest disagreement with the ledger's framing. Four behaviors are bundled:

1. **Partial consolidation replaces the canonical consolidated workbook.** The v0.18 final
   plan §C.1 says explicitly: consolidations — "`failed`/`no_data` ⇒ do not compare/cache,
   keep any stale prior workbook…; `partial` ⇒ compare but flag" (05-claude-final-plan.md:
   274-278), and `consolidate_xlsx_base.py:289-294` implements exactly that ("status stays
   ok so the file that WAS produced is still offered"). Keep-last-good applies to the
   **export store promotion** (§C.1: partial → `previous_preserved`), which the code honors
   (`gui_worker_matrix.py:52-58`). So "partial overwrote the complete canonical
   consolidation" is **designed behavior under the governing plan**, and the current
   `CLAUDE.md` sentence ("a partial/failed/cancelled refresh keeps last-good") plus
   `docs/engine-and-reliability.md:83-84` ("a partial run can never be promoted, **cached**,
   or shown green") are the artifacts that drifted — they generalize the export-store rule
   to consolidations and caches where the plan deliberately chose replace-but-flag.
   Verdict for this sub-claim: **Reframed** — it is a documentation/contract contradiction
   (fold into CMP-AUD-086 or settle as an architectural decision), not a straight code bug.
   The ledger itself half-notices this ("the historical v0.18 plan, however, also says
   partial cache records are allowed") but still lists "keep the last complete canonical
   consolidation" as the correction requirement — that is a **product decision, not a bug
   fix**, and implementing it would change v0.18-intended behavior.
2. **Renderer shows `✓ match` main text on a partial cell.** Confirmed
   (`ui-matrix.js:296-299`: `mx-partial` class but main `"✓ match"`). Under the plan's own
   words ("green UI requires complete… partial→amber") the amber class is compliant but the
   checkmark-plus-"match" main text is not defensible for an incomplete universe. Real
   defect; P2 on its own.
3. **Partial cells are excluded from "Refresh stale".** Confirmed: `_staleness` never marks
   a partial-completion record stale (`matrix_state.py:248-259`) and
   `cells_to_rebuild(scope="stale")` keys on `stale` alone (`matrix_build.py:203`). A
   partial cell can therefore never self-heal short of "Refresh all"/re-export. Real defect;
   this is the operationally painful half (the v0.26.2 memory records exactly this workflow
   pain: work-PC amber HL(PDF) days needed manual force re-consolidation).
4. **Day badge green / evidence publishes partial silently.** Confirmed by structure
   (`consolidated_state` has no completion input, `matrix_build.py:353-360`; evidence's
   automatic path gates on `status=ok` only). Real defects.

Recommended severity after the split: the contract contradiction is the P1 (it blocks
correct implementation of everything else); sub-defects 2–4 are P2s that become mechanical
once the contract is settled.

### CMP-AUD-087 — unavailable count caches can't refresh as stale — **Confirmed, P2**

Verified: renderer treats `diff_cells == null` as "re-run / stale — refresh"
(`ui-matrix.js:284-288`) while the selector checks only `cmp.stale`
(`matrix_build.py:203`); `_staleness` leaves `stale=false` for an untrusted record with
no newer mtimes (`matrix_state.py:238-259`). The one-predicate correction is right.

### CMP-AUD-114 — unreadable results certified fully OK — **Confirmed, P1**

`_is_full_ok` (`validation.py:215-216`) tests `status=="ok" and completion==COMPLETE`,
ignoring `counts_unreadable` (`:171-172`); no verdict is ever persisted (the rec carries
status/completion/counts only). The code's own comment defines the intent —
`comparisons_ok` is "COMPLETE only — a full, trustable pass" (`:237`) — so "fully OK" was
meant as *trustworthy result*, and the unreadable-counts case violates the stated intent.
One caveat: the ledger's claim that the golden check "explicitly expects the
unreadable-count cell inside `comparisons_ok`" — I could not find a `counts_unreadable`
assertion in `build/check_validation.py` (it does correctly test partial-vs-ok separation at
`:262-264`); before "fixing" the golden check, re-verify which assertion actually entrenches
the behavior.

### CMP-AUD-115 — commit accepts semantically empty workbooks — **Confirmed, P1**

`_openable_xlsx` (`artifact_store.py:127-154`) validates openability + `expect_sheet`
membership only. The `read_counts` positional fallback exists exactly as claimed
(`matrix_state.py:174-181`) and its own comment ("Foreign/malformed sheet … fall back")
rationalizes trusting positions precisely when the sheet is least trustworthy —
contradicting the CLAUDE.md "by header label, never position" rule for the case that
matters. Both sub-claims verified.

### CMP-AUD-116 — failed validation records default complete — **Confirmed, P1** (+ refinement)

Executed: `getattr(res,'completion',None) or COMPLETE` yields `complete` for an
error-status result; `outcome.consolidate_completion_of` — sitting in the same repo,
documented as the safe reducer — yields `failed`. Refinement the ledger missed: the invalid
`status=error, completion=complete` combination arises only for **returned** error results
(`validation.py:164-165`); a **raised** exception leaves `completion` absent entirely
(`:175-182`), which downstream `rec.get("completion", COMPLETE)` readers will *also* read as
complete — the fix must cover both shapes.

### CMP-AUD-117 — Bearer secrets survive redaction — **Confirmed, P1**

Executed against the verbatim regex (`validation.py:53-56`):
`Authorization: Bearer SECRET-ABC-123` → `Authorization=[redacted] SECRET-ABC-123`
(the `\S+` consumes only "Bearer"); bare `Bearer SECRET-ABC-123` is untouched (no `[=:]`).
The correction list is right; add `Negotiate`/`NTLM` blobs and `key=value&`-style URL query
tokens to the test matrix (the `#\S{16,}` hash rule covers fragment tokens only).

### CMP-AUD-118/119/120 — **all Confirmed, P2**

- 118: `ensure_current` returns `None` when no consolidated exists, **by documented design**
  ("the not-yet-built flow keeps its explicit import-and-build UX",
  `tsn_library.py:457-469`); `_ensure_tsn_ready` misuses it as a first-build. The fix is a
  contract choice: either validation calls `build_consolidated` for `raw/pdfs`, or it
  reports "imported, awaiting build" as blocked — the ledger correctly offers both.
- 119: `summary_lines`' state ladder tests `current_after` before `healed`
  (`validation.py:255-257`) — healed-and-current prints `current`, healed-but-stale prints
  `HEALED`. Verified.
- 120: `_tsn_stage` contains no cancellation check and runs `ensure_current` rebuilds before
  the comparisons stage ever polls (`validation.py:91-110`, `run_validation:228-231`).
  Verified.

---

## 4. Cluster 3 — source identity, caching, races, publication

### CMP-AUD-041 — output aliasing can destroy a source — **Confirmed, P1**

Classic path verified in source: `_launch_compare` (`gui_compare_api.py:152-157`) passes
**no** `confirm_overwrite` to `commit_workbook`, so the derived ` (values)` twin is approved
by the default `lambda _p: True` (`artifact_store.py:246`), and nothing anywhere compares the
final destination(s) against the comparison's inputs — `commit_workbook` has no concept of
inputs. The matrix/day/evidence variants follow the same structure (evidence:
`sibling_paths` + `_write_workbook` replace whatever is at the derived name). The ledger's
correction requirements are right; add one more: **the alias check must run on resolved
identities** (`Path.resolve` + `os.path.samefile` where possible) *inside*
`commit_workbook`, not only in the API layer, so the matrix/day/evidence callers inherit it
for free.

### CMP-AUD-076 — no durable source provenance — **Confirmed, P2**, with important context for the 164-row question

`run_files_compare` passes `name_a=tsmis_path.name` (`compare_tsn_common.py:221`) — basename
only — and the outcome sidecar records no identity. Confirmed. On the Highway Log shift, the
ledger under-reads its own numbers; the arithmetic decomposes exactly:

- documented (docs/comparison-engine.md:269-270, the v0.14.0 roadbed-key effect measurement):
  both **46,755**, one-sided **3,804 / 13,328**, diff cells 175,048 → implied TSMIS side
  46,755+3,804 = **50,559** rows, TSN side 46,755+13,328 = **60,083**;
- chunk-12 fresh build: both **46,919**, one-sided **3,804 / 13,164**, TSMIS
  46,919+3,804 = **50,723**, TSN 46,919+13,164 = **60,083**.

TSN is byte-stable (same 60,083 extract), TSMIS-only is **unchanged at 3,804**, and the
TSMIS side simply **gained 164 rows, every one of which landed on a previously TSN-only
key**. That is the signature of a newer TSMIS pull printing rows the TSN extract always had
(consistent with the June→July site builds; the same drift class was measured for HSL —
"within ~54 rows of the 6.19 canary"). Also note 46,755 was never a standing canary for the
current bundle: it is the *effect line* of the roadbed-key change measured on the v0.14-era
PDF set (50,559 rows), so the two numbers were produced from **different TSMIS pulls by
construction**. The ledger's conclusion (drift is arithmetically consistent but unprovable
without provenance) stands — this decomposition just makes drift the overwhelmingly
parsimonious explanation and sharpens what provenance must capture (per-side row counts and
source fingerprints in the workbook/sidecar would have settled it instantly).

### CMP-AUD-080 — metadata-only identity — **Confirmed, P1**

Executed: same-length byte replacement + `os.utime` restore → identical
`artifact_store.fingerprint` string. The `_MTIME_TOL_S` record-trust window
(`matrix_state.py:238-239`) and the absence of size/content checks on cached outputs are as
described. On intent: the v0.18 plan committed to metadata-only **with a defined migration
trigger** ("content hash only if a same-metadata replacement case is later proven",
05-claude-final-plan.md:303-305). The audit's constructed counterexample satisfies the
letter of that trigger; whether a lab construction (vs a field event) was meant is a user
decision — but timestamp-preserving copy/restore/sync tools make the case real enough that I
side with the audit. Correction constraint the ledger missed: fingerprint cost — statewide
stores are hundreds of files and snapshots run on every push; hash **at build/commit time
and store it**, never hash-on-snapshot, or the matrix UI will pay seconds per refresh.

### CMP-AUD-081 — TSN freshness ignores source identity — **Confirmed, P1** (by structure)

`_staleness` freshness inputs are mtimes + the recorded TSMIS-folder fingerprint only; the
TSN side contributes an mtime through `sources` and nothing else; `resolve` returns
path+mtime with no content identity or normalization version in the cell record. Consistent
with the audit's switch/stale-library reproductions (not re-run here).

### CMP-AUD-082 — stale formulas twins — **Confirmed, P1**

`_try_formulas` (`matrix_build.py:88-121`): best-effort commit, failure logs only, the
12,000-row skip returns without touching a prior sibling, and no manifest/freshness state
exists for the twin. One mitigation worth recording: the skip **is** announced at build time
(`:104-110`), so the ledger's "expose the skip before execution" is an enhancement, not a
missing disclosure.

### CMP-AUD-083 — presence counts arbitrary files — **Plausible, not re-verified**

I did not re-read `report_library._newest_in`/`_folder_newest_mtime`. The claim is
consistent with the `fingerprint` exclusion asymmetry I did verify. No disagreement; keep as
Verified per the audit's own reproductions.

### CMP-AUD-084 — semantic changes don't invalidate caches — **Confirmed, P1**

`cache_envelope.SCHEMA_VERSION=2` is documented as record-shape-only ("Bump ONLY when the
cached record shape changes incompatibly", `cache_envelope.py:29-33`); no producer/semantic
version exists in cell records or consolidation sidecars (`consolidation_meta.write_outcome`
payload). Confirmed as a designed-in gap. Note the repo already has the pattern to copy: the
TSN library's `normalization_version` (D2) does exactly this per-dataset — the correction is
to generalize D2 to comparator/parser/consolidator versions.

### CMP-AUD-089 — failed rebuilds aren't durable state — **Confirmed, P2**

`_on_matrix_cell` copies row/cell/done/total and drops `payload["status"]`
(`gui_matrix.py:1373-1381`); `_on_matrix_done` emits transient log text only. Verified.

### CMP-AUD-098 — mid-comparison mutation recorded fresh — **Confirmed, P1**

`build_cell_comparison` computes `_cell_input_fingerprint` **after** the comparator ran
(`matrix_build.py:175-179`). The repo already contains the correct pattern in the very same
flow: `_consolidate_store_folder` captures `fp_before` and
`write_consolidated_fingerprint(..., built_from=fp_before)` refuses to certify on mismatch
(P2-A02, `matrix_build.py:249-252,287-290`; `artifact_store.py:397-437` with its
remove→sentinel→quarantine ladder). The correction is to apply the existing P2-A02 pattern
to the comparison cache and the evidence gate — cite it in the fix rather than designing a
new mechanism.

### CMP-AUD-100 — cache identity/record schema unvalidated — **Confirmed, P2**

Verified (via sub-review + my own read): writers stamp `output_identity="tsn-by-day"`
(`day_matrix.py:147`) but every reader calls `unwrap(data)` without it
(`day_matrix.py:122`, `matrix_state.py:92`, `baseline_matrix.py:147`), even though
`cache_envelope.unwrap` supports the check (`:59-60`) — and the envelope docstring documents
the pass-None decision ("the cache path scopes by baseline/day"). So: deliberate, now shown
unsafe. The list-typed-record crash needs the workbook present (`built and rec` guard) but is
then deterministic.

### CMP-AUD-105 — missing explicit TSN override silently substitutes — **Confirmed, P1**

Executed: `_resolve_source("highway_log", selected_file=<nonexistent>)` returned the
canonical library source (`kind="pdfs"` on this machine), not an error. The docstring's own
words — "an explicit user-picked `selected_file` (a real .xlsx) — **always wins**"
(`tsn_library.py:608-609`) — describe selection-as-authoritative; the `is_file()` fall-through
(`:617-620`) contradicts it. Nothing in code or planning docs marks silent fallback as a
product decision; I concur with fail-closed.

### CMP-AUD-106 — stale evidence beside a clean comparison — **Confirmed, P1**

`generate` returns before touching siblings on the no-differing-columns path
(`visual_evidence.py:227-231`), the no-rendered path (`:321-326`), and every `_cancelled()`
return. Verified.

### CMP-AUD-109 — evidence workbook/images not one transaction — **Confirmed, P1**

Verified: `_write_workbook` commits (or diverts to `.new`) the workbook, then `_swap_dir`
independently commits (or diverts) the images (`visual_evidence.py:592-676`); cancellation
is last checked **before** the workbook write (`:319-320`); divert/failure outcomes are
appended to the human `note` while the returned dict always carries the canonical
`workbook`/`folder` paths (`:341-347`) — so a total publication failure still returns
success-shaped paths. All three ledger sub-claims hold.

### CMP-AUD-112 — parse/rasterize race — **Confirmed, P1**

`_try_example` verifies values against the earlier `locate_*` parse (`:394-412`), then
`_strip`→`_render_page` re-opens the path at render time (`:426-427`, `:450-458`). The
`page_cache` is keyed on `(path, page_no)` with LRU eviction, so pixels can even come from a
**third** generation (a page rendered for an earlier example survives the file's
replacement). No content identity anywhere between parse and raster. Verified.

---

## 5. Cluster 4 — destructive / security-sensitive

### CMP-AUD-090 — day worker stamps a foreign folder for Reset — **Confirmed, P1**, root cause reframed

All elements verified executably or in source:

- `day_matrix.day_out_path` writes day comparisons under
  `OUTPUT_ROOT/comparisons/tsn-by-day/...` (`day_matrix.py:98-109`) — **not** under the
  batch destination; `build_day_cell` uses `dest` only to resolve the TSN drop tree.
- `DayMatrixCompareWorker.run` stamps `<dest>/comparisons` unconditionally, before knowing
  whether it has any cells (`gui_worker_matrix.py:226-228`), with a comment asserting the
  by-day matrix writes there — factually wrong, evidently copied from the Everything worker
  (`:162`), for which the claim is true (`comparison_path(dest, ...)`).
- Executed: `ensure_owned_dir` on a pre-existing folder containing a user file flips
  `is_owned` False→True without touching the file.
- Reset (SEC-02) deletes **any marker-bearing direct child** of the batch dest
  (`gui_worker_maint.py:86-89`) — and its comment states the marker "proves the app created
  this dir".

Reframe the ledger should adopt: the day worker's stamp is the *trigger*, but the root cause
is that `mark_owned`/`ensure_owned_dir` are **stamp-on-sight** while Reset treats the marker
as **proof of creation** — the v0.19.0 SEC-02 change explicitly retired name-based
stamp-on-sight for exactly this reason, and the marker mechanism reintroduced it one level
down. Consequently the Everything worker's legitimate stamp has the same hazard for a
pre-existing user `comparisons` folder (it will write inside it AND make the user's
co-located files Reset-deletable). Fix at the `owned_dir` layer (only stamp directories the
caller just created, or require empty/app-shaped content before stamping a pre-existing
one), plus remove the day worker's stamp; do not fix only the day worker.

### CMP-AUD-111 — evidence formula injection — **Confirmed, P1** (executed)

`_write_workbook` writes `e["va"]`/`e["vb"]` via plain `ws.cell(...)`
(`visual_evidence.py:616-621`) in normal (non-write-only) mode; executed: a value `=1+1`
round-trips with `data_type='f'` (live formula), `=HYPERLINK(...)` likewise, while
`compare_core._styled(..., guard=True)` yields `'s'`. Confirmed, and the fix is mechanical
(reuse `is_formula_injection` + force string type; the caption strings built from
`field/route/key/va/vb` in `_image_sheet:581-584` start with the field name so are safe, but
guard them anyway). Add the `ERROR_CODES` guard here too (see 003).

### CMP-AUD-117 — see Cluster 2 above. Confirmed P1 by execution.

---

## 6. Cluster 5 — evidence integrity (107–113 and extensions)

- **107 — Confirmed, P1.** `evidence_highway_detail` trips on stripped-string inequality
  while production uses `compared_cell` (whitespace folding + Med-Wid). Combined with
  `docs/comparison-engine.md:911`'s explicit count-consistency promise, this is a
  contract violation, not a mere inconsistency. (Static verification; the audit's
  fixtures accepted.)
- **108 — Plausible, not re-verified, P2.** I did not re-read every adapter's duplicate
  filter; the engine-side claim (comparison counts duplicate-group diffs via similarity
  pairing) is verified. No disagreement.
- **109/111/112 — Confirmed P1**, see above.
- **110 — Confirmed, P2** (sub-review): jobs store only row/cell/kind
  (`gui_matrix.py:167-169`) and `_dispatch_evidence_job` re-reads dest/tsn_files/examples/
  source/baseline at dispatch (`:358-368`).
- **113 — Confirmed, P3** (read directly): `total = len(written) + 2`
  (`evidence.py:297`) while `contents` includes the validation members (`:284-286`).
- **106 — Confirmed, P1**, see above. On the *intent* question: the evidence output layer
  was explicitly designed as per-artifact keep-last-good for **locked-file** availability
  (the section header at `visual_evidence.py:565-566` and the `.new` diversion), and §13
  documents evidence as a best-effort decoration whose failures only log. Retirement of
  stale evidence on a now-clean comparison was simply never designed — there is no
  documented decision to preserve it. So the audit's correction (atomic per-generation
  publish with an explicit "current: no differences" state) is a new requirement, and a
  right one.
- **049 evidence extension — Confirmed.** `_try_example` builds the TSMIS path from the
  expected route's filename and verifies parsed **values** only (`visual_evidence.py:394-419`);
  no in-document route identity is reconciled, so a renamed foreign-route PDF with a
  matching key/value can be captioned as the requested route.
- **061 evidence extension — Confirmed by structure** (the per-district `locate_tsn` calls
  poll cancellation between districts but a single statewide print scan is one
  uninterruptible call; HL/HSL locators run inside `district_index`/`locate` without the
  events object).
- **080/085/098 evidence extensions — Confirmed** (the on-demand gate checks freshness
  before generation only; `(size, mtime_ns)` print caches; partial published silently — all
  consistent with the code read in §4/§3).

---

## 7. Cluster 6 — source-scoped state and action targeting (sub-review + spot checks)

All eighteen examined findings **Confirmed**: 095 (`settings.py:711/771` persist source
only; the mock clears; note the baseline *setter* itself validates options — the leak is
specifically the source-switch path), 096 (`gui_matrix.py:602-604/1140-1142/1337-1339`
coerce invalid → None → unscoped; "full-matrix" is literal only for `scope="all"`),
097 (`matrix_state.py:571-572` `missing[0]`), 099 (`ui-matrix.js:789-792`
`recompute_matrix("all")` vs the confirm text; **wasteful rebuild, not wrong results — I
recommend P3, not P2**), 100 (above), 101 (`gui_matrix.py:940-941` always opens the
env-baseline tree; **the per-cell open action is mode-correct**, so only the folder shortcut
misdirects — impact overstated), 102 (`matrix_state.py:610` hides rows before mode
iteration), 103 (missing `missing_side` guard in explicit paths, both day and Everything),
104 (`ui-matrix.js:1123-1124`; the inline comment admits it), 110, 072 (no generation token;
contrast the guarded `_dayRenderSeq` pattern at `ui-matrix.js:825-828` — reuse it), 079,
088 (`gui_api.py:1136-1139` clears indiscriminately; `check_matrix_bridge.py:356-358`
entrenches it — and only ever tests export-behind-export, so the frozen assertion never
exercises the mixed case), 094, 016 (**overstated in one respect**: `start_compare_env`
*does* preflight dropdown-selected folders for subdir presence,
`gui_compare_api.py:246-257`, skipping only Browse-absolute paths; the no-preflight claim
holds fully for file recipes), 013 (hardcoded `supported: True` at
`matrix_state.py:352-389` — verified directly), 014 (verified by census: `env` group = 17),
015 (four `TSAR:`-prefixed labels verified).

---

## 8. Findings outside the priority clusters

Chunks 4–8 (aggregate loaders, flat-schema gates, PDF parser integrity: 018–025, 027–038,
040, 042, 044–071, 073–074, 078, 091–093) were **not independently re-reproduced** in this
review. Where their mechanisms crossed files I did read (e.g., 038/006 in
`compare_tsn_common`, 040/069/076 in the shared driver, 044's trim-and-slice shape, 065's
schema clone at `compare_highway_sequence_pdf.py:101-105`, 069's missing `side_a/side_b`
at `compare_ramp_detail_pdf.py:217-223`, 091's `dated=True`/"today" resolution at
`gui_worker_matrix.py:34-41`), the code matched the ledger exactly. I found **no
disagreement** in this population; treat their `Verified` statuses as unchallenged rather
than re-confirmed. CMP-CAND-001's disposition (candidate awaiting reproduction) is correct.

---

## 9. Context questions

**Q1 — partial artifacts vs the v0.18 partial cache records.** The intended distinction is
three different gates that the current docs have since blurred into one sentence:
(a) **export-store promotion** (F1): complete-only; partial → `previous_preserved`
(keep-last-good) — implemented and honored; (b) **consolidated artifacts**: partial
*replaces* the canonical workbook but must be flagged everywhere
("`partial` ⇒ compare but flag", plan §C.1) — implemented; (c) **comparison cache records**:
allowed for complete|partial consolidations, but "green UI requires complete" — partially
implemented (amber class yes; `✓ match` text, refresh-stale exclusion, day badge, evidence
no). `CLAUDE.md`'s "a partial/failed/cancelled refresh keeps last-good" and
`engine-and-reliability.md`'s "never promoted, cached, or shown green" over-generalize (a)
onto (b)/(c). Before coding CMP-AUD-085 the user must pick: keep the plan's
replace-but-flag (then fix docs + the four flagging gaps) or adopt the stricter
keep-last-good-for-consolidations (then design a side-channel for partial artifacts, e.g.
`…（partial).xlsx`, because a stale-complete workbook silently feeding comparisons has its
own falseness).

**Q2 — was `completion=None` ≡ complete intentional?** Yes, thrice-documented as an
*intra-version back-compat inference*, never as a producer license: `outcome.
consolidate_completion_of` ("a safe inference … when a producer hasn't set it: ok→complete,
cancelled→cancelled, error→failed"), the v0.18 plan ("absent ⇒ default complete for
intra-version safety"), and `tsn_library.resolve` ("a user pick / legacy workbook reads
complete — deliberate"). Two failures followed: `run_compare` was never promoted to a
producer (so the inference fires exactly where it's wrong — CMP-AUD-017/026), and callers
inlined the inference as `x or COMPLETE` instead of calling `consolidate_completion_of`,
losing the error→failed/cancelled mapping (CMP-AUD-116, `matrix_build.py:177`). On
warning/error/cancelled paths it was **never** intended to mean complete — the reducer
proves that.

**Q3 — metadata-only identity.** An explicit, recorded performance tradeoff with a named
migration trigger: "content hash only if a same-metadata replacement case is later proven"
(05-claude-final-plan.md:303-305). CMP-AUD-080's construction satisfies the trigger's
letter; timestamp-preserving restore/sync tools make it realistic. When migrating, hash at
build/commit time and persist (never hash-on-snapshot), and migrate legacy sidecars to
stale exactly once, as the ledger says.

**Q4 — missing explicit TSN override.** Fail closed. The resolver's own contract line
("always wins") treats the selection as authoritative; the silent `is_file()` fall-through
is an unowned robustness guard, not a recorded decision. Distinguish "automatic (canonical)"
from "explicit override" as modes; a missing override blocks dependent cells with a
re-pick/clear prompt.

**Q5 — validation's "fully OK".** Intended as *a full, trustable pass* — the code comments
say so ("COMPLETE only — a full, trustable pass") and the partial tally exists precisely to
keep non-trustable passes out of it. It was never meant as "code executed". CMP-AUD-114's
unreadable-counts case is therefore a violation of the stated intent, and the fix is to add
readability/verdict-consistency (and eventually workbook validation, CMP-AUD-115) to
`_is_full_ok`'s conjunction.

**Q6 — old red evidence when the new comparison is clean.** No historical decision exists;
the early-return predates any retirement design. Given evidence's charter (a verified
*decoration* of the current comparison, never a second source of truth), the right behavior
is: atomically publish a current "no differences to illustrate" state (workbook Summary
saying exactly that) and remove or `.stale`-quarantine the old images. Plain retention as
"labelled history" contradicts the decoration charter (siblings carry current-looking
canonical names); if history is wanted it belongs in dated subfolders, a separate feature.

**Q7 — the `.new` diversion.** The diversion was designed intent — per-artifact
keep-last-good for the locked-open-in-Excel case ("outputs (keep-last-good)",
`visual_evidence.py:565`), accepting temporary divergence in exchange for not losing a
render. What was **not** intended is the missing generation identity binding workbook,
images, comparison, and sources — nothing marks a diverged pair as mismatched, cancellation
isn't rechecked at commit, and the result reports canonical paths regardless. So: keep the
lock-diversion affordance if desired, but wrap both artifacts in one manifested generation
with structured promoted/diverted/failed status (the ledger's correction), and treat a
diverged set as not-current.

**Q8 — the day worker's ownership stamp.** No legitimate reason. Day outputs go under
`OUTPUT_ROOT` (`day_out_path`); `dest` is only the TSN drop root. The stamp (and its
comment) is a copy of the Everything worker's — where it *is* the output tree. History
explains it as a copy-paste during the by-day build-out, nothing more. Fix at the
`owned_dir` layer as argued in §5 (the Everything worker's stamp-on-sight of a pre-existing
folder carries the same hazard).

**Q9 — census.** Confirmed in full: 29 recipes, 12 rows, 30 supported placements, 7
canonical TSN datasets, 5 unique PDF↔Excel self-checks across 6 placements (§1).

**Q10 — the Highway Log +164.** See CMP-AUD-076 above: TSN constant (60,083), TSMIS-only
constant (3,804), TSMIS side 50,559 → 50,723; all 164 new TSMIS rows paired against
previously TSN-only keys; diff cells +221. The "older documented canary" is the v0.14.0
roadbed-key effect measurement taken on the older PDF pull — a cross-bundle comparison by
construction. Drift (newer site builds printing rows the TSN extract always had — the July
overhaul window; cf. the HSL ~54-row drift precedent and the vendor's known dropped-row
behavior that made the PDF the preferred HL source) is the parsimonious explanation. The
provenance finding stands: nothing durable can *prove* it.

**Q11 — findings incorrectly split/merged/prioritized/phrased.** (1) **085 must be split**
(§3): the consolidation-overwrite half is plan-intended; the presentation/retryability/
badge/evidence halves are the defects. (2) **090's root cause belongs in `owned_dir`**, not
the day worker (§5). (3) **099 → P3** (wasteful rebuild, not wrong results). (4) **101** —
note the per-cell open is correct; only the folder shortcut misdirects. (5) **016** — the
folder-dropdown path does preflight; narrow the claim to file recipes + Browse paths.
(6) **008** should cross-reference the v0.18 deferral decision and gain the
greedy-worse-than-positional constraint. (7) **014/015/086** are correctly P3. (8) The
"golden check entrenches 114" sub-claim needs re-verification before the fix edits that
check (§3).

**Q12 — what the audit still missed.** (1) Greedy pairing **non-monotonicity** (proven,
§2). (2) `read_counts` inherits the marker-scan ambiguity — cache/validation counts are
wrong for marker-bearing equal values even after a workbook-display fix (§2). (3) The
**intra-doc contract contradiction** (`engine-and-reliability.md` "never cached" vs
`outcome.comparable` "partial → compare but flag" vs the plan's "complete|partial cache
records") — must be settled first (§3, Q1). (4) `ensure_owned_dir` stamp-on-sight as the
090 root cause; the Everything worker shares it (§5). (5) `_styled`'s guard misses
`ERROR_CODES` — the data-sheet half of 003 has a one-line hardening (§2). (6) Validation's
raised-exception path leaves `completion` **absent**, a second shape 116's fix must cover
(§3). (7) The 164-row decomposition (t_only constant) that all but settles Q10 (§4).
(8) `check_matrix_bridge`'s queue-clear assertion only ever tests export-behind-export, so
it doesn't even cover the behavior it freezes (088). (9) `norm_pm`'s docstring self-
contradiction (§2). (10) Positive finding worth recording: the P2-A02 pre/post fingerprint
ladder in `artifact_store.write_consolidated_fingerprint` is exactly the mechanism 098's fix
needs — the correction is generalization, not invention.

---

## 10. Strongest disagreements with the audit

1. **CMP-AUD-085's headline.** "Partial Matrix artifacts overwrite last-good" indicts
   behavior the governing v0.18 plan specified ("partial ⇒ compare but flag"; keep-last-good
   is the *export-store* rule). The real P1 is the unresolved contract contradiction plus
   the four flagging gaps. Implementing the ledger's correction as written would silently
   change intended semantics without a product decision.
2. **CMP-AUD-099's severity** — a spurious rebuild of baseline-independent artifacts wastes
   time and churns mtimes but produces correct results; P3.
3. **CMP-AUD-016/101's blast radius** — both overstate: folder dropdowns are preflighted;
   the per-cell open action reaches the right artifact.
4. **CMP-AUD-080's "the trigger is now satisfied"** — technically yes, but the ledger
   should be explicit that the counterexample is constructed, and that the plan left the
   hash-cost question open; the fix needs a costed design (hash-at-commit), not just a
   stronger identity.
5. **Tone on 100** — the reader-side `unwrap(data)` without identity was a documented
   decision (envelope docstring), not an oversight; the finding is right that it's unsafe,
   but corrections go faster when they name the decision they're reversing.

## 11. Most dangerous findings (my ranking)

1. **CMP-AUD-090** — the only finding that can destroy user data outside the app's tree
   (via Reset), and it's cheap to trigger accidentally.
2. **CMP-AUD-017 + 026 + 075** (one family) — silent conversion of incomplete comparisons
   into green "match" across matrix, day, baseline, and classic surfaces; this is the exact
   class of trust failure the tool exists to prevent.
3. **CMP-AUD-001/002/004 (+ read_counts)** — the two output flavors of the flagship
   artifact disagree with each other and with the run summary in live Excel; every
   downstream count inherits one of the two semantics arbitrarily.
4. **CMP-AUD-041** — a normal-looking save flow can atomically destroy a source workbook
   (or its unselected twin/evidence sibling).
5. **CMP-AUD-111 + 117** — spreadsheet payload execution in a trusted evidence artifact;
   credentials in a bundle whose whole promise is credential-safety.
6. **CMP-AUD-105 + 106 + 112** — quiet substitution of the comparison's reference dataset
   and evidence that can attest to bytes it never parsed; these undermine the audit-grade
   claims the evidence feature makes.

## 12. Recommended implementation order

The ledger's seven-step order is sound; I would re-cut it as follows (differences bolded):

1. **Settle the three contracts first (no code):** partial-artifact policy (Q1), explicit-
   TSN-override semantics (Q4), evidence lifecycle/transaction (Q6/Q7). Update `CLAUDE.md` /
   `engine-and-reliability.md` / `comparison-engine.md` in the same change so the fixes have
   one oracle (folds CMP-AUD-086).
2. **Safety hotfixes that don't touch the locked engine:** 090 (owned_dir semantics + day
   worker), 111 (+ ERROR_CODES guard), 117, 105 (fail-closed override), 041's alias guard in
   `commit_workbook`. These are small, independent, and close the destructive/security
   surface before the long engine work.
3. **Outcome truth plumbing:** make `run_compare` an outcome producer (017), thread producer
   completion through env/direct paths (026), per-artifact sidecars (075), structured counts
   in results (077), validation truth fixes (114/116/118/119/120 + 007/011). All additive
   `CompareSchema`-adjacent or consumer-side work; no locked formula text changes.
4. **Identity/caching:** content identity + build-time hashing (080/081/083), semantic
   producer versions (084), pre/post identity via the P2-A02 pattern (098), envelope
   identity + per-record validation (100), durable provenance (076), failed-attempt state
   (089), 087's one predicate, 082's twin manifest.
5. **The equality model** (001–005, 012, 039, 043, 065, 067, 107/108) — the big
   regression-locked change: one structured per-cell state consumed by formulas text,
   values text, counts, `read_counts`, Spot Check, Report View, and evidence. This is last
   among the majors because every earlier layer must be able to *carry* its output, and it
   requires the full cell-for-cell re-proof + real-Excel gates.
6. **Evidence transaction/lifecycle** (106/109/110/112 + the 049 route reconciliation)
   once the identity layer (step 4) exists to bind generations to.
7. **UI state/taxonomy sweep** (013–016, 069, 072–074, 078, 079, 088, 093–096, 099,
   101–104, 113) — mechanical once the above land.

Steps 2 and 3 can proceed in parallel; step 5 must not start before step 1's equality
contract decision (case sensitivity, numeric coercion, error policy) is written down.

## 13. Architectural decisions that must be settled before coding

1. **The canonical equality contract** — case sensitivity, Excel-vs-Python numeric
   precision (15-digit), text/number/boolean coercion, error-cell policy, Med-Wid grammar
   (signs? leading decimals? suffix case?), and whether live formulas remain a *computation*
   surface or become a *presentation* of Python-computed truth (the only way the two flavors
   can never disagree is if exactly one engine decides).
2. **Partial-artifact policy** (Q1) — replace-but-flag vs keep-last-good for consolidations
   and caches, and the renderer vocabulary for partial (no `✓`, retryable-by-default).
3. **Identity architecture** — what constitutes source identity (content hash at commit,
   producer semantic versions, generation IDs binding output↔cache↔evidence), and the
   one freshness predicate shared by snapshot, renderer, target selection, and gates.
4. **Ownership/deletion trust model** — what `is_owned` may prove, when stamping is legal,
   and what Reset requires beyond a marker.
5. **Explicit-selection semantics** — overrides fail closed (TSN files, baselines, days)
   with a uniform "selection invalid — re-pick or clear" state.
6. **Evidence transaction charter** — one generation manifest for workbook+images bound to
   the comparison generation, with an explicit current-clean state.
7. **The duplicate-pairing contract** — either fund the locked-engine optimal-assignment
   re-proof (v0.18 deferred it) or pin the monotonic fallback and document greedy's limits.

## 14. Real-data / real-Excel gates before declaring corrections complete

1. **Regression-lock re-proof** for any step-5 change: the `%TEMP%\tsmis_regress` harness +
   COM `CalculateFullRebuild` against `Downloads\TSMIS\ground-truth\inputs`; Route-1 Highway
   Log canary (299 paired / 18/69 / 221 / **969** cells) byte-for-byte for the vs-TSN
   flavor, or a formally re-blessed replacement canary if the equality contract changes
   values (that decision must be explicit and user-approved).
2. **Live-Excel adversarial matrix** (001–005, 012): casing, boolean/text, ≥15-digit
   numbers, precise decimals, signed/leading-decimal/suffix-case Med-Wid, error cells,
   marker-bearing equal values, delimiter-bearing keys, blank-vs-zero Spot Check — asserted
   as *three-surface agreement* (live Summary == values Summary == Python counts) after
   `CalculateFullRebuild`.
3. **Statewide re-blesses through the LIBRARY path** (never raw-file feeds) for every
   report whose loader/normalizer/schema changes, with `normalization_version` bumps: the
   locked canaries — ID 21,675/687 on the 7.8 bundle; HSL 60,493/69,758 · 57,071 both ·
   5,521 cells; HD 48,644/208,596 (+ PDF↔Excel 2,484/2,487); RD 15,211 both/902 cells
   (+ PDF↔Excel 15,212/15,216, 0 one-sided); RS 31 categories; IS 58/8/0; HL Route-1 969 —
   from `ground-truth/All Reports 7.9`, `Intersection Detail Bundle 7.8`, `HSL PDF + IS
   Bundle 7.9`, `Hwy Detail Dev Bundle 7.7`, `All Reports 6.19` (the audit's five
   still-owed bundle gates).
4. **A real work-PC pass**: the owed two-day baseline-matrix run, the amber-day
   re-consolidation clear-out (v0.26.2 memory), a validation run whose bundle is
   byte-scanned for planted credentials, and a Reset preview against a store containing a
   deliberately foreign `comparisons` folder (must be surfaced, not listed for deletion).
5. **Cache migration proof**: upgrade from a pre-fix cache/artifact tree — every affected
   cell reads stale exactly once, rebuilds, and no false-fresh survives (including the
   metadata-only→content-identity sidecar migration and a comparator-version bump).
6. **Evidence end-to-end on real prints** (HD/ID/HL/HSL/RD): regenerate the blessed example
   sets; diff→clean transition retires old artifacts; a locked-workbook divert is reported
   as diverted, not success; injection payloads planted in source data round-trip as
   literal text in the evidence Summary.

---

## Appendix — reproductions performed (this review)

Scratchpad `second_opinion_repro.py` + `census_check.py` + `excel_com_check.py` +
PowerShell COM (all disposable; no repo writes):

| # | What | Result |
|---|---|---|
| R1 | `compared_cell`/`_medwid_norm` on the 001/002 pairs | case-sensitive; `06v/6V`, `-06V/-6V`, `.50/0.5` differ in Python |
| R2 | equal value containing `" ≠ "` | verdict equal, marker-counted as diff |
| R3 | helper keys for `("R|X","K")` vs `("R","X|K")` | both `R|X|K|1` |
| R4 | `run_compare(warnings=…)` end-to-end | `ok/diff/completion=None/0/0`; matrix coerces `complete`; `read_counts=(0,0)` |
| R5 | same-size+mtime byte replacement | identical fingerprint |
| R6 | credential scrub (verbatim regex) | `Authorization=[redacted] SECRET-ABC-123`; bare Bearer untouched |
| R7 | error result through validation's default | `complete` (reducer says `failed`) |
| R8 | openpyxl `=1+1` in evidence-style write; `_styled(guard=True)` | `'f'` vs `'s'`; `"#N/A"` → `'e'` even guarded |
| R9 | 8×8 greedy cost matrix | greedy 56 > positional 8 (non-monotonic) |
| R10 | `ensure_owned_dir` on pre-existing folder with user file | `is_owned` False→True |
| R11 | `_resolve_source` with deleted explicit selection | silently resolves the canonical library |
| R12 | `norm_pm`/`iso_date` | `9.6≠9.600`, `0/0.0/0.000` split; `000.606→0.606` (docstring wrong); junk-suffixed + impossible dates accepted |
| COM | fresh both-mode workbook, `CalculateFullRebuild` | live Diffs `0/1`, Summary total **1** vs values Diffs **2/2** (sum 4) vs Python **3** |
| Census | registries imported and counted | 29 / 12 / 30 / 7 / 5-of-6 confirmed |
