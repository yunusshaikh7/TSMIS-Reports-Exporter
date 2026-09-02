# `RB-6` — Bundle Contract

Status: **MERGED**

> Original readiness froze this contract. Claude implemented the bundle;
> Codex Review 1 returned solely `RB6-R1-EG-001`, which the return round
> supplied. Separate Codex Review 1 and Review 2 approvals now make RB-6
> jointly approved. See [REVIEW.md](REVIEW.md). Scope is unchanged.

This readiness record combines the complete HF-07, HF-08 and HF-11 sections
from [IMPLEMENTATION-PLAN.md](../../IMPLEMENTATION-PLAN.md). The plan remains
authoritative. Readiness is scope preparation only: no branch, product change,
source rebuild or acceptance generation has begun.

| Field | Value |
|---|---|
| Bundle / queue | RB-6 / 6 |
| Work items / findings | HF-07 + HF-08 + HF-11 / PCOA-FINAL-015, -017, -018, -020, -021, -022 |
| Theme | Missing-side latency, export coverage truth, deterministic TSN identity, source guards and owner-facing vendor record |
| Branch to create in Stage 4 | `hotfix/rb-6-hygiene-and-guards` |
| Readiness source main | `a0787e7710b326945797c7c51f56acb7081d0f20` — pushed RB-5 merge closeout |
| RB-5 merge | `f11f9d2546b7775e432a22d5174f895f01210c35`; two separate Codex approvals, post-merge gate 171/171 and packaged application self-test PASS |
| Prerequisites | RB-2, RB-3 and RB-5 all MERGED |
| Implementer / reviewers | Claude / Codex Review 1 and a separate fresh Codex Review 2 |
| Stage-4 base | `62bb0f329c7d7deea6c5ee9010c3d21b0acf6325` — clean pushed `main` (`origin/main` identical), fetched 2026-08-31; the repo is at **v0.43.0**, two releases beyond the v0.41.1 the readiness note assumed |

## Current-main qualifications

- The old eight-dataset count in HF-08 is historical. Read-only catalog inspection
  on this main reports **11** supported TSN entries; Stage 4 must derive the
  exact current set from `report_catalog.TSN`. All-supported-dataset obligations
  remain intact; no normalization content change is authorized.
- Highway Detail's old pre-release rationale predates its release. Preserve
  the explicit parser/schema/canary/data scope exclusions below; do not infer
  permission to widen scope from that stale rationale.
- HF-08's cause remains **unestablished**. Establish it before fixing anything;
  if resolution requires widening beyond `scripts/tsn_library.py`, return RB-6
  to BLOCKED and use the documented HF-08 split fallback. Do not weaken acceptance.
- Fresh main includes later ArcGIS and comparison-speed work. Re-read named
  call sites and catalog topology before trusting historical line numbers/counts.
- RB5-R2-FU-001 (Unicode classification) is an owner-ranked RB-5 follow-up, not
  silently added to RB-6. The Clean Road hardware leg and staged-library support-
  bundle limitation also remain disclosed; readiness does not authorize retrying
  expensive operations or changing unrelated code.
- HF-11 prepares an owner-facing vendor escalation record. This does not
  authorize sending messages or raw internal data to a vendor.

## Combined acceptance and evidence

Stage 4 must name one bounded combined acceptance run and retain exact base/head,
source identities, timing/coverage results, identity/content invariance, typed
outcomes, twin checks, the full gate and small committed witnesses for every
criterion below. Reuse existing evidence only when its runtime/source bindings
remain valid. Do not create this acceptance evidence during readiness.

---

### HF-07 — Missing-side fast fail and export coverage truth

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-07` / `fastfail-coverage` |
| Split fallback branch | `hotfix/hf-07-fastfail-coverage` |
| Priority / order | 7 |
| Depends on | HF-04 (`compare_env.py` ownership) |
| Findings | **PCOA-FINAL-015** (P2), **-018** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer. Both findings are Claude-unique, so Codex must bind to Claude's `witness\export_coverage.txt`, the committed `claude-round1-export-coverage.txt`, and the three timing witnesses, then re-measure independently |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | Inherits RB-6: MERGED |

**Exact scope.** 015: the folder-comparison preflight on every statewide PDF
family, in classic environment, Baseline and Everything ENV. 018: the catalog's
export-only truth and its UI surfacing for `ramp_summary_excel`,
`intersection_summary_pdf` and `highway_summary`.

**Explicitly out of scope.** Adding comparators for the three unverifiable
editions (that is DEF-04 for Highway Summary and a separate feature for the other
two — this bundle makes the gap *explicit*, not closed); any change to the
comparison's own semantics; the Ramp Detail header contract (HF-04); any change
to Highway Detail's parsers, schema, canaries or data (**pre-release**).

**Highway Detail note.** One of 015's three witnesses is `highway_detail_pdf`
Everything ENV (1,229.7 s). Reproducing a *latency* on that configuration
requires no HD schema judgement, no HD canary, and no trust in any HD artifact,
so it is compatible with the standing HD pre-release rule. The fix itself is in
the shared preflight and reaches HD without touching HD code.

**Verified root cause.** 015: `compare_env.EnvComparator.compare_folders:1033`
already computes both sides' member lists at `:1065-1066`, yet nothing checks
side B for emptiness before side A is fully parsed at `:1139+` — measured
429.4 s, 438.6 s and 1,229.7 s to report a missing second side, against 0.0 s
for a missing first side. 018: `report_catalog.ExportEntry:88` has no export-only
concept, so three enabled editions (343 of 2,380 exported route files, 14.4 %)
have no consolidator, no `MATRIX` row and no recipe, and nothing in the UI says
so; `build/check_report_wiring.py` already derives required touchpoints and is
the natural gate.

**Files expected to change.** `scripts/compare_env.py` (`compare_folders`
preflight only), `scripts/report_catalog.py`, `scripts/reports.py`,
`scripts/ui/` (the export-only label), `build/check_report_wiring.py`.

**Migration / compatibility.** The preflight must not reject a legitimately
empty-but-present side differently from today's eventual message — the *verdict*
stays the same, only the latency changes; and it must not fire on the Ramp
Summary/Intersection Summary aggregate loaders whose discovery shape differs. The
catalog's stable IDs are immutable and `_V017_EXPORT_ORDER` is append-only: an
export-only marker is additive metadata, never a reordering.

**Tests to add.** A check that a comparison with side B's report folder absent or
empty returns its typed error in under 5 s with side A untouched (assert on
elapsed time and that no parse occurred), for one XLSX-sourced and one
PDF-sourced family; and a `check_report_wiring.py` extension that fails naming
any enabled edition that has neither a dispatchable comparison path nor an
explicit export-only marker plus UI surfacing.

**Exact end-user generation path.** 015: Compare tab → classic environment for
`intersection_detail_pdf` with the second run folder's report subfolder absent;
repeat on Baseline and Everything ENV. 018: the report picker, Consolidate tab and
Compare tab in the GUI (verify through the `#mock` preview at
`/index.html#mock`, remembering the browser caches `app.js`/`app.css`).

**Source-truth recount.** None. Assert instead that every non-empty comparison
still produces identical counts, and that the export-coverage census reproduces
126 + 217 = 343 unverifiable files against 2,380.

**Values / formulas and installed-Excel checks.** One regenerated comparison per
family class, both twins, proving the preflight changed nothing about a valid run.

**Workbook visual / presentation checks.** None for 015 (no workbook). For 018,
the export-only labelling is legible in the GUI at default width and does not
break the picker's grouping.

**Evidence.** Unchanged; assert no artifact appears or disappears.

**Neighbouring-family regression.** All folder-comparison families and the whole
catalog derivation: full gate plus `check_report_wiring.py`,
`check_report_catalog.py`, `check_report_recipe.py`, `check_compare_env_*.py`,
`check_matrix.py`, `check_baseline_matrix.py`, `check_a2_compare_filter.py`, and
the `#mock` GUI preview.

**Measurable acceptance criteria.**
1. With side B absent, every comparison path reports the missing side in **under
   5 s** regardless of side A's size — reproduced on all three witnessed
   configurations.
2. A valid comparison's counts, twins and typed outcome are unchanged.
3. Every enabled export edition either has a dispatchable comparison path or is
   marked export-only in the catalog **and** shown as export-only in the UI;
   `check_report_wiring.py` fails naming any that satisfies neither.
4. Full gate green; both new assertions fail pre-fix.

**Rollback.** Revert the merge commit. Catalog metadata is additive, so a revert
only restores the silent gap.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-07\`;
`hotfix-bundles/HF-07/witness/` for the three timing measurements (before/after)
and the re-derived coverage census.

---

### HF-08 — TSN normalization identity determinism

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-08` / `tsn-identity` |
| Split fallback branch | `hotfix/hf-08-tsn-identity` |
| Priority / order | 8 |
| Depends on | HF-03 (the capture step must already be identity-complete) |
| Findings | **PCOA-FINAL-017** (P2) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer. Claude-unique finding, so Codex must bind to Claude's `witness\tsn_rebuild_all.json` and re-run the double rebuild itself; the root cause is an unverified hypothesis and the reviewer's first job is to confirm the implementer actually established it |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | Inherits RB-6: MERGED |

**Exact scope.** The TSN library's normalized-workbook build and identity for all
eight supported datasets, and the consequence that pressing *Rebuild* invalidates
every bound vs-TSN comparison.

**Explicitly out of scope.** Any normalization *content* change (a content change
requires a `report_catalog.TSN` `normalization_version` bump plus a full re-bless
and is a different bundle); the clean-road normalizer's marker version; the
comparators' claim rendering (HF-03).

**Verified root cause — unestablished.** A force rebuild over raw whose
`tsn_raw_manifest.sha256` and `normalization_version` were unchanged produced a
different `tsn_normalized_workbook_identity` and `tsn_artifact_identity_token`
for all eight datasets. The finding labels the openpyxl-timestamp explanation an
**explicit hypothesis** and requires implementation to begin by establishing the
real cause; the pre-rebuild bytes were replaced and cannot be re-diffed.
Inspection anchors: `tsn_library.build_consolidated:909`,
`_write_normalized_workbook:1152`, `normalized_workbook_identity:249`.

**Files expected to change.** `scripts/tsn_library.py`, plus checks. If the cause
turns out to lie in a per-report loader, Stage 4 stops and returns the bundle to
Stage 3 rather than widening scope.

**Migration / compatibility.** Making the bytes deterministic changes the
identity **once**, so every existing bound comparison is invalidated by the fix
itself. Plan for it explicitly: state in `IMPLEMENTATION.md` that one full
re-comparison is expected after this bundle, and confirm the invalidation is
detected and reported honestly rather than silently producing a stale-bound
result.

**Tests to add.** A hermetic check that two consecutive
`build_consolidated(report, force=True)` calls over unchanged synthetic raw
produce byte-identical workbooks and identical identity/token values, for every
supported dataset shape; plus a check that a rebuild which *should* change
identity (raw manifest or normalization version changed) still does.

**Exact end-user generation path.** Compare tab / Settings → **Rebuild TSN
library** twice in a row over unchanged `tsn_library\<report>\raw\`, then one
vs-TSN comparison per dataset to confirm bindings survive.

**Source-truth recount.** None. Prove instead that normalized content is
unchanged by the fix: every dataset's row/field projection equals its pre-fix
projection cell-for-cell (the Stage 2-validated normalization fidelity must
hold — Intersection Detail 16,626 rows / 631,788 cells, Ramp Detail 15,410 rows,
Clean Road 60,083 × 74 with zero changed cells).

**Values / formulas and installed-Excel checks.** One vs-TSN comparison per
dataset regenerated after the double rebuild, both twins, counts unchanged.

**Workbook visual / presentation checks.** The normalized workbook still opens
in Excel with its marker sheet and normalization marker intact.

**Evidence.** For the two `_TSN_PDFS_IN_RAW` families, confirm the raw prints and
their bindings are unaffected.

**Neighbouring-family regression.** All eight datasets and every vs-TSN
comparison: full gate plus `check_tsn_normalizer.py`,
`check_tsn_normalization_marker.py`, `check_tsn_freshness.py`,
`check_tsn_outcome.py`, `check_tsn_raw_source_contract.py`,
`check_tsn_canonical_consumer_identity.py`, `check_tsn_status_coherence.py`,
`check_artifact_store.py`.

**Measurable acceptance criteria.**
1. The real root cause is **established and documented** before the fix.
2. Two consecutive force rebuilds over unchanged raw produce byte-identical
   workbooks and identical `tsn_normalized_workbook_identity` /
   `tsn_artifact_identity_token`, for all eight datasets.
3. A rebuild that should change identity still does.
4. Normalized content unchanged cell-for-cell; all vs-TSN counts unchanged.
5. The one-time invalidation is disclosed, detected and reported honestly.
6. Full gate green; the determinism check fails pre-fix.

**Rollback.** Revert the merge commit; identities become non-deterministic again
and one further re-comparison is needed. Note this asymmetry in
`IMPLEMENTATION.md`.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-08\`;
`hotfix-bundles/HF-08/witness/` for the double-rebuild identity table across all
eight datasets and the content-invariance proof.

---

### HF-11 — Source-side escalation and must-not-regress guards

| Field | Value |
|---|---|
| Work-item ID / split slug | `HF-11` / `source-guards` |
| Split fallback branch | `hotfix/hf-11-source-guards` |
| Priority / order | 11 — program closeout |
| Depends on | HF-06, HF-09 (the guards must lock the final parser/comparator state) |
| Findings | **PCOA-FINAL-020** (P1, source-side), **-021** (NO FIX), **-022** (NO FIX) |
| Implementer | Claude |
| Review 1 | **Codex** — non-implementer; binds to `source-audit/prior-7.9-highway-log-sibling-raw-source-audit.json` (its own 021 witness) and to Claude's `witness\pdf_head_census.txt` for 022 |
| Review 2 | **Codex** — a second, separate chat that must challenge review 1 and re-derive from source, never copy it |
| Status | Inherits RB-6: MERGED |

**Exact scope.** Turn two prose regression guards into executable checks, and
create the owner-facing vendor escalation record for route 140. **No product
behavior change.**

**Explicitly out of scope.** Synthesizing route 140's missing columns, or any
workaround that masks a vendor data defect; changing either parser's behaviour;
adding Highway Detail coverage (**pre-release**).

**Verified basis.** 021: route `074` @ `000.000` occurrence 2 (prior 7.9 raw PDF
page 7 line 31) and route `101` @ `R022.828` (page 142 line 23) are genuine
PDF-only source rows the PDF path correctly retains; they must never be
synthesized into the Excel-derived universe. 022: a stray leading `GENERATE` line
now precedes four print families and the Highway Sequence Listing (PDF) print was
re-skinned to the TASAS layout with a wider text measure; the parser absorbs both
(route 001 → 2,581 rows new, 2,583 prior) and must keep supporting **both**
layouts. 020: `highway_log_route_140.xlsx` leaves `R/U`, `TER`, `H/G`, `A/C`
blank on all 213 rows where its own print carries values — vendor action, not a
product fix.

**Files expected to change.** `build/check_*.py` (two new or extended guards),
`docs/` (the vendor escalation record and a pointer from the reports/Highway Log
docs), `CHANGELOG.md`. No `scripts/` change is expected; a reviewer should reject
one unless the guard cannot otherwise be written.

**Tests to add.** A parser guard that produces correct row counts for both the
pre- and post-re-skin Highway Sequence print layouts and ignores the leading
`GENERATE` line on all four affected families; and a source-universe guard that
the two PDF-only rows are retained in the PDF-derived universe and absent from
the Excel-derived one. Both must fail against a deliberately reverted parser /
universe rule.

**Exact end-user generation path.** Consolidate tab → Highway Sequence (PDF) from
both a pre-re-skin and a post-re-skin print; Compare tab → classic environment
Highway Log, both editions, over the two days that exhibit the four-route delta.

**Source-truth recount.** Re-verify both PDF-only rows at their original PDF
page/line; re-verify route 140's blank columns against the raw export and its
print; re-derive the four-route delta (net −14 / +2) reconciling 89,811 and
88,238 differing cells.

**Values / formulas and installed-Excel checks.** One Highway Log classic-env
pair regenerated in both twins to confirm the universe rule and counts are
unchanged.

**Workbook visual / presentation checks.** None beyond confirming the regenerated
pair is unchanged.

**Evidence.** Unchanged.

**Neighbouring-family regression.** Highway Log and Highway Sequence, both
editions: full gate plus `check_compare_highway_log.py`,
`check_compare_env_highway_log*.py`, `check_compare_highway_sequence*.py`,
`check_tsn_district_source_contract.py`.

**Measurable acceptance criteria.**
1. Both guards exist, fail on a deliberate regression, and pass on `main`.
2. No `scripts/` behaviour change (or an explicitly justified minimal one).
3. The vendor escalation record exists, names the exact witness, and states the
   on-delivery acceptance test (route 140 self check reports zero
   `X ≠ (blank)` on `R/U`, `TER`, `H/G`, `A/C`).
4. All Highway Log / Highway Sequence counts unchanged.
5. Full gate green.

**Rollback.** Revert the merge commit; only guards and docs disappear.

**Retained output / witness.** `…\_scratch\post-comparison-hotfixes\HF-11\`;
`hotfix-bundles/HF-11/witness/` for the two row-level source traces and the
route-140 raw census.

---

## Dependencies, split fallback and rollback

RB-2, RB-3 and RB-5 are merged. HF-07 and HF-11 do not authorize product
semantics changes; HF-08 permits identity determinism only. If the HF-08 root
cause exceeds its allowed file, split using `hotfix/hf-08-tsn-identity` after
returning the combined bundle to planning. Each work-item rollback above remains
controlling; the expected one-time identity invalidation must be disclosed.

## Readiness signature

Prepared by **Codex**, `2026-08-31T18:45:35.043861+00:00`, after RB-5's reviewed merge,
passing smoke, push and bounded cleanup. **READY — implementation not started.**
