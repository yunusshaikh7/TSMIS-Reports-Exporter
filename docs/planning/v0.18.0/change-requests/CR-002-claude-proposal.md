# CR-002 — Forward-port the v0.17.2–v0.17.8 feature work onto the v0.18.0 structure

**Status:** `awaiting_codex_review` (normal phase execution **paused**)
**Author:** Claude (implementer) · **Reviewer:** Codex (must re-accept before implementation resumes)
**Raised:** 2026-06-25 · **Branch:** `refactor/v0.18.0-structural-overhaul` · **HEAD:** `d15216d`
**Active phase when raised:** between **P12 (committed `d15216d`)** and **P13 (next eligible, `pending`)** — no phase `in_progress`/`awaiting_review`.

---

## 1. Requested change summary

The refactor branched from **v0.17.1** (`d2ee353`). While it has been in flight, `main`
kept shipping: `origin/main` is now **v0.17.8** (`068b697`), **~10 commits ahead** of the
branch point. The user wants those changes **integrated into v0.18.0 and made compliant
with the refactored architecture**, so the shipped v0.18.0 contains everything v0.17.8
has *plus* the structural overhaul — and the eventual `refactor → main` merge is clean.

The divergence is, by the user's own forward-port handoff doc on `main`
(`docs/refactor-handoff-v0.17.1-to-v0.17.5.md`, 412 lines), **one feature**:

1. **Intersection Detail (PDF)** (v0.17.2–v0.17.4) — a print-ready PDF export built as an
   **exact parallel of `highway_log_pdf`**: a new export, a PDF→36-column consolidator, the
   cross-env / vs-TSN / PDF-vs-Excel comparators, and a full row in both matrices.
2. The **Intersection Detail vs-TSN comparison evolution** (v0.17.5–v0.17.8) — localized to
   `compare_intersection_detail_tsn` (+ a `summary_layout` signal fold and one **opt-in
   `compare_core` field**): the J–P→Signalized control crosswalk, the compare-everything
   policy (`CONTEXT_FIELDS=()`), read-time TSN-library re-normalization, position-aligned
   date columns, numeric-padding normalization, the `S` control label, and a new printed
   **"Report View"** replica sheet.

This is a **meaningful scope + definition-of-done change** (new report family, new golden
checks/canaries, a touch to the regression-locked `compare_core`, and a shift to the
live-verify set), so per the workflow it is **paused here for Codex re-acceptance** rather
than implemented.

## 2. Reason for the change

v0.18.0 is a structural overhaul of the SAME modules the v0.17.x feature modified
(`reports.py`, `matrix.py`, `exporter.py`, `compare_env.py`, `compare_intersection_detail_tsn.py`,
`summary_layout.py`, `gui_worker.py`, `app.spec`, the UI mock, the matrix checks). If v0.18.0
ships without forward-porting the feature, then `refactor → main` either (a) silently **drops
a shipped report** (data loss for users on v0.17.8) or (b) is resolved by a blind `git merge`
that reintroduces the **old structure** the refactor just removed — defeating the overhaul and
almost certainly breaking the registry/matrix/stable-ID contracts P3/P4/P1 established.

The clean path is a **deliberate forward-port**: re-implement the feature **in the new
structure**, following the handoff's single rule — *"wherever the refactor moved/renamed/
restructured `highway_log_pdf`, apply the identical structural change to `intersection_detail_pdf`"*
— and re-apply the localized vs-TSN comparison changes onto the refactored
`compare_intersection_detail_tsn`. The handoff doc provides a complete file-by-file map and the
locked canaries, so this is a well-bounded port, not open-ended design.

## 3. Current implementation state

- **All committed v0.18.0 phases are green and unaffected in correctness.** P0, PA, P1, P2, P3,
  P4, P5, P5b, P6, P7a, P7b, P7c, P8a, P8b, P8c, P9, P9b, P10, **P12** are `committed`
  (each Codex-`PASS`ed, one focused commit, planning folder never staged). Latest: **P12**
  (`d15216d`). Pending: **P13** (work-PC handoff, next eligible), **P11** (docs, last).
- **Offline suite green at HEAD:** full `build/check_*.py` suite **72/72** + 3 Node + byte-compile
  (the only `check_no_misspelling` hit is the untracked Codex review file).
- **Tree:** clean apart from the untracked `docs/planning/` workspace. `version.py` = `0.17.1`
  (the refactor's own number; v0.18.0 will set it). Nothing pushed.
- **The divergence is local-only / inspectable:** `origin/main` = `068b697` (v0.17.8). The
  feature footprint is `git diff d2ee353..origin/main` = **40 files, +2748 / −261** (see §6).

## 4. Current branch and commit SHA

- **Branch:** `refactor/v0.18.0-structural-overhaul` (off `main` @ `d2ee353`; **not pushed**).
- **HEAD:** `d15216dcf4a375855a0f4c85b1bed76bfad328c4` (`d15216d`, P12).
- **Integration source:** `origin/main` `068b697` (v0.17.8); `merge-base` = `d2ee353` (v0.17.1).
  Local `main` is one release behind (`718defc`, v0.17.7) — **use `origin/main` as the source of truth**.
- **Working tree:** clean apart from untracked `docs/planning/`.

## 5. Current phase status

| Phase | Status | Note |
|---|---|---|
| P0 … P10, P12 (+ P5b/P7b/P7c/P8c/P9b) | `committed` | the full committed set; unaffected |
| **P13** | `pending` (next eligible) | work-PC validation handoff + v0.18.1 close-out |
| **P11** | `pending` (LAST) | docs + audit/roadmap reconciliation |

No phase is `in_progress` or `awaiting_review`. The CR is raised in the gap **after P12,
before P13**.

## 6. Files / areas likely affected (the forward-port footprint)

Mapped from `git diff d2ee353..origin/main` + the handoff §2/§3. **"Mirror" = the refactor's
current `highway_log_pdf` structure is the template.**

**New product modules to create (mirror the HL-PDF sibling, in the refactored layout):**
- `scripts/export_intersection_detail_pdf.py` ← `export_highway_log_pdf.py`
- `scripts/intersection_detail_columns.py` (the 36-col header SoT) ← `highway_log_columns.py`
- `scripts/consolidate_tsmis_intersection_detail_pdf.py` (the PDF parser — the genuinely new
  logic; 2-row/zebra-shaded layout) ← `consolidate_tsmis_highway_log_pdf.py`
- `scripts/compare_intersection_detail_pdf.py` (PDF-vs-TSN + PDF-vs-Excel adapters) ← `compare_highway_log_pdf.py`

**Existing modules to extend (additively, following the committed structure):**
- `scripts/reports.py` (registry rows + the deliberate `_CONSOLIDATOR_BY_SUBDIR` omission) — must
  use **P3's stable-ID taxonomy** for the new report family.
- `scripts/matrix.py` (the `_pdf_store_consolidator` helper — the **v0.17.4 crash class**;
  `_row_modes`/`tsn_comparator_for`/generalized vs-Excel self-compare) — must reconcile with the
  committed P7c/matrix structure + the row-set assertions.
- `scripts/exporter.py` (`save_intersection_detail_pdf`), `scripts/compare_env.py`
  (`INTERSECTION_DETAIL_PDF` EnvCompare), `scripts/day_matrix.py` (`fmt="pdf"` branch),
  `scripts/gui_worker.py` (reset cleanup parity), `scripts/ui/app.js` (`#mock` fixtures only).
- **`scripts/compare_intersection_detail_tsn.py`** (the vs-TSN evolution §8/§9 — the position-aligned
  `_TSN_COL`, `CONTEXT_FIELDS=()`, `_norm_control_type`, `_norm_num`/`NUMERIC_FIELDS`,
  `_SIGNALIZED_LABEL="S"`, read-time `_normalized_row`, the `_RV_*` Report-View config +
  `_write_report_view`).
- **`scripts/summary_layout.py`** (the §9b signal fold) + `scripts/compare_intersection_summary_tsn.py`
  (read-time `_slug_for_key` fold).
- **`scripts/compare_core.py`** — main added the **opt-in `context_fill` field** (+16). It defaults to
  `None` → no-op, so the Route-1=969 HL canary stays byte-identical (verified in §9d on `main`).
  v0.17.8 then dropped its only live user, so it is a **dormant clean opt-in**. (See §9, regression-lock.)

**Build / packaging / checks:**
- `build/app.spec` (`APP_MODULES` += the 4 new modules — required for the frozen lazy imports;
  reconcile with P10/PA's inventory + `check_app_modules`/F6).
- New `build/check_intersection_detail_pdf.py` (locks the 36-col header + mapping + the
  every-matrix-row-resolves-a-filename regression).
- `build/fake_site/intersection_detail_print.html` + `build/check_fake_site.py` (+the save test).
- `build/check_intersection_gate.py` (registry-derived count), `build/check_matrix.py` /
  `check_matrix_bridge.py` / `check_matrix_tsn.py` (row set 7→8 — **reconcile with the refactor's
  current matrix row set**), `build/check_compare_intersection_detail_tsn.py` /
  `check_compare_intersection_summary_tsn.py` (the evolved canaries),
  `build/check_compare_env_highway_log_pdf.py` (membership-not-last), `.github/workflows/checks.yml`.

**Docs (folded into P11, not duplicated here):** `CLAUDE.md` (report 6b), `README.md`, `docs/reports.md`,
`docs/roadmap.md`, `docs/comparison-engine.md`, `docs/tsn-parsers.md`, `CHANGELOG.md`, `version.py`,
the two `.bat` console menus (option 8), `.gitignore` + `output/intersection_detail_pdf/.gitkeep`.

## 7. Whether already-committed work is affected

**No committed phase needs to be reopened, reverted, or re-reviewed.** The forward-port is
**additive** — it registers and wires a NEW report family on top of the committed refactor,
using the contracts those phases established:
- It **uses** P3's stable-ID taxonomy + manifest, P4's catalog, P1's outcome model, P2's
  transactional store, P7a/P7c's GUI structure, PA/P10's packaging inventory — it does not change them.
- It **extends** modules the committed phases produced (`reports.py`, `matrix.py`, `gui_worker.py`,
  `app.spec`, the matrix checks, `compare_env.py`, `summary_layout.py`) with the new report's rows/
  branches, the same way the committed refactor already supports `highway_log_pdf`.
- **`compare_core` regression-lock:** the only `compare_core` delta is the opt-in `context_fill`
  field (default `None`), which the v0.18.0 rule explicitly permits ("new behavior is added through
  opt-in `CompareSchema` fields that default to the no-op original"). It must be proven byte-identical
  for the default + the Route-1=969 HL canary before it lands. The locked row-emit logic is untouched.

The one real reconciliation risk is **structural drift** where the refactor changed the HL-PDF side
or the matrix row set/order vs what v0.17.x assumed (the handoff's "merge watch-outs"). That is
in-scope work for the new phase, not a defect in a committed phase.

## 8. Proposed amendment to the phase plan

Add the forward-port **before P13/P11** (P13 must enumerate the live-verify set, which now
includes the new report; P11 reconciles its docs). Proposed new order:

> **… P12 (committed) → P14 → P15 → P13 → P11 (last).**

- **P14 — Intersection Detail (PDF) report family (structural parallel of `highway_log_pdf`).**
  The §2/§3 plumbing + the §4 parser: create the 4 new modules in the refactored layout; wire the
  registry/stable-IDs, `matrix._pdf_store_consolidator` (incl. the v0.17.4 crash regression),
  `exporter`/`compare_env`/`day_matrix`/`gui_worker`, `app.spec`/`APP_MODULES`, the UI `#mock`, and
  the new + adjusted golden checks. Parser correctness is **offline-proven against the committed
  golden check** (the 36-col mapping); real-PDF acceptance → v0.18.1 (same RM04 footing as the
  other PDF reports). **Blocking.** Depends: committed P3/P4 + the HL-PDF structure.
- **P15 — Intersection Detail vs-TSN comparison evolution (§8/§9).** Re-apply the localized
  `compare_intersection_detail_tsn` evolution (position-aligned dates, `S` label, numeric-padding
  norm, `CONTEXT_FIELDS=()`, read-time re-normalization, the Report View via the existing
  `extra_sheet_writer` opt-in + the write-only techniques), the `summary_layout`/`compare_intersection_summary_tsn`
  fold, and the **`compare_core` `context_fill` opt-in** — each proven against its evolved canary, with
  `compare_core` proven byte-identical at the no-op default. **Blocking (compare-core-adjacent).**
  Depends: P14 (the PDF report exists) + committed P5b.

**Alternative granularity (Claude is flexible):** P14 + P15 may be **one** phase ("Forward-port
v0.17.2–v0.17.8") with internal per-area commits, OR P15 may split further (the §8/§9b crosswalk
vs the §9c–§9e position/Report-View work). The handoff confirms §3-plumbing and §8/§9-comparison
forward-port **independently**, which is why a 2-phase split is the recommended default. **Codex to confirm.**

**DoD impact:** the v0.18.0 offline DoD gains "Intersection Detail (PDF) at full HL-PDF parity in
the new structure + the evolved vs-TSN canaries green." The **v0.18.1 acceptance set (P13)** gains the
new report's live export/consolidate/compare on the work PC — folded into the existing P13 evidence
kit, **not** a new release tier. **No committed phase is renumbered or reopened** (RM01 preserved).

## 9. Proposed verification changes

- **Port every golden check that ships with the feature** and re-prove its **locked canary** in the
  refactored tree: `check_intersection_detail_pdf` (36-col header + mapping + every-matrix-row-resolves-
  a-filename), `check_compare_intersection_detail_tsn` (the **v0.17.8 canary 163,353** Excel / 163,361
  PDF; `CONTEXT_FIELDS=()`; position-aligned mappings; `S` crosswalk; Report-View locks),
  `check_compare_intersection_summary_tsn` (66 categories, 58/8/0, 54 diff cells), `check_fake_site`
  (the new save test), the matrix checks (the **reconciled** row-set / hide-N assertions),
  `check_intersection_gate` (registry-derived count).
- **`compare_core` regression-lock proof:** with `context_fill` added, run the existing
  `check_compare_audit` + the Route-1=969 HL canary and prove **byte-identical** vs HEAD for every
  non-opted-in comparison; the opt-in fires only when a schema sets it.
- **Packaging:** `check_app_modules`/F6 must list the 4 new modules; the frozen `--self-test`/
  `build.ps1 -SelfTest` exercises the new lazy imports.
- **Full suite + byte-compile + `#mock` smoke + `check_no_misspelling`** green at each new-phase
  boundary; `check_import_direction` (no new cycle).
- **RM04 honesty:** parser/real-PDF/real-TSN **correctness** is acceptance-gated to **v0.18.1** (the
  handoff's 218/218-route reconciliation ran on LOCAL ground truth under `Downloads\TSMIS\…`, never in
  CI); v0.18.0 ships the offline-locked mapping + the canaries. No live access during implementation.

## 10. Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Large port across ~15 modules touching the registry, matrix, and comparison engine | High | The handoff doc is a complete file-by-file map; the single rule "mirror `highway_log_pdf`"; per-area commits; golden checks ship with the feature. |
| `compare_core` regression-lock violation | High | The only delta is the opt-in `context_fill` (default `None`); prove byte-identical + Route-1=969 canary before landing; locked row-emit untouched (matches the v0.18.0 rule + how `main` already did it). |
| Structural drift — the refactor changed the HL-PDF side or the matrix row set/order vs v0.17.x assumptions | Medium | Reconcile against the refactor's CURRENT HL-PDF structure (not main's); fix the "8 rows / hide-N" assertions to the refactored matrix; `check_intersection_gate` already derives the count from the registry. |
| Stable-ID taxonomy (P3) must absorb a new report family without manifest churn | Medium | Use the documented "add a report" recipe + the 4-tier stable IDs; `check_stable_ids` + manifest v1/v2 reject-not-drop guard the keys. |
| PDF parser correctness can't be CI-proven (needs real PDFs) | Medium | Lock the 36-col mapping with the golden check (offline); carry real-PDF acceptance to v0.18.1 P13 (RM04) — identical footing to the existing PDF reports + the P12 oracle. |
| The vs-TSN canaries are large/volatile (163k) and report a deliberate policy | Low-Med | Port the canary verbatim from the shipped check; the handoff records each figure + why; re-bless only the touched report's canary, never `compare_core`'s. |
| Write-only comparison-workbook techniques (merged header, comments, freeze-before-rows) | Low | The handoff §9e lists them explicitly; the refactor still writes comparisons in write_only, so they port directly. |
| Scope creep / reopening committed phases | Low | RM01: committed P0–P12 stay historical; the port is additive; no renumbering. |

**Rollback:** the new phases are net-new files + additive edits behind the registry — revertible
per-commit; nothing the committed refactor depends on changes.

## 11. Exact questions Codex should review

1. **Approach:** is a **deliberate forward-port into the new structure** (NOT a `git merge` of
   `origin/main`, NOT a rebase) the correct integration method, given the refactor restructured the
   same files and the goal is architectural compliance?
2. **Phase granularity:** accept **two** new phases (**P14** report-family plumbing + **P15** vs-TSN
   comparison evolution), or collapse to one, or split P15 further? Are the IDs/dependencies/ordering
   (**P12 → P14 → P15 → P13 → P11**) correct — specifically that the port precedes P13 (live-verify set)
   and P11 (docs)?
3. **Committed work:** confirm the port is **additive** and that **no committed phase (incl. P3 stable
   IDs, P1 outcome, P2 store, P7c matrix) is reopened** — only extended.
4. **`compare_core` regression-lock:** is adopting main's **opt-in `context_fill`** acceptable under
   the v0.18.0 rule (default `None` no-op + Route-1=969 byte-identical proof), even though v0.17.8
   left it with no live user (a dormant clean opt-in)? Or should it be **omitted** until a report uses it?
5. **DoD / two-tier release:** confirm the new report's **offline parity + canaries** join the v0.18.0
   DoD while its **live export/consolidate/compare acceptance** folds into the existing **v0.18.1 P13**
   kit (RM02/RM04) — no new release tier.
6. **Source of truth:** confirm integrating from **`origin/main` (v0.17.8, `068b697`)**, with the
   handoff doc `docs/refactor-handoff-v0.17.1-to-v0.17.5.md` as the authoritative map; and that the
   refactor's `version.py` becomes **0.18.0** (which supersedes 0.17.8 — no version conflict).
7. **Any item to defer:** is anything here better left to v0.18.1 or the roadmap (e.g. the deferred
   `non-hl-loaders-dont-collapse-tab-whitespace` tab-trim item the handoff §5 logged)?

## 12. Claude recommendation

**ACCEPT WITH MODIFICATIONS.**

The change is necessary (without it v0.18.0 either drops a shipped report or reintroduces the old
structure via a blind merge) and well-bounded (one feature, a complete handoff map, golden checks +
canaries that ship with it). It does **not** reopen committed work and keeps the regression-lock and
two-tier-release discipline intact. The "modifications" are the open decisions in §11 — chiefly the
**phase granularity (1 vs 2 vs 3)**, the **`context_fill` adopt-vs-defer** call, and confirming the
**ordering before P13/P11** — which are Codex's to settle before implementation resumes. Pending that,
recommend adding **P14 + P15** as above, sequenced **P12 → P14 → P15 → P13 → P11**, with the forward-port
done as a deliberate structural port (not a merge), every shipped canary re-proven in the new tree, and
`compare_core` proven byte-identical at the no-op default.
