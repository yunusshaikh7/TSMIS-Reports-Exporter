# App consistency & output-model backlog (owner notes, 2026-07-17)

Owner-supplied feature/hardening notes for *after* (or alongside) the comparison-perfection
project. Captured verbatim-in-intent + triaged by **lane**, **risk**, and **sequencing**.
This is the backlog; detail/decisions land in the owning docs as each is picked up.

> **➡ EXECUTION PLAN (2026-07-22): [v0.30-owner-backlog-plan.md](v0.30-owner-backlog-plan.md)** —
> the owner expanded this list to 20 comments; every item is Step-0 code-verified there
> (several were already implemented or refuted) and sequenced into TWO MARATHON RUNS
> (M1 → v0.30.0, M2 → v0.31.0; owner directive 2026-07-22). That plan supersedes this
> file for execution; this file remains the capture/triage record.

> **⚠ These are OWNER OBSERVATIONS, not verified defects. Step 0 for every item is a
> code-verification pass — confirm what the app ACTUALLY does today before scoping any fix.**
> The owner flagged (2026-07-17) that these were noticed in use, not traced in code, and some may
> be wrong: already-correct, partially correct, or different than described. Example: exports
> from the main Export tab *sometimes* land in the expected place but some reports were seen in a
> different folder — the real pattern (which reports, which surfaces, why) must be traced before
> assuming "all export-tab exports save differently." Treat every "currently does X" below as
> *owner-observed, unconfirmed* until a code audit + a real-run check confirm it. Same rigor as
> the comparison-perfection census-first rule: never build on an unverified assumption.

**Lanes:** `CMP` = comparison engine (Claude, the comparison-perfection lane) · `ARCH` =
cross-cutting architecture (Claude owns the design) · `GUI` = front-end / matrix UX (Claude;
needs `#mock` verification) · `SOL` = safe for a future Codex mission *after* the design is
fixed. Sol's current mission (sol-001, reliability engine) does **not** include any of these.

## The output-model spine (items 9, 10, 11, 13 — design FIRST)

> **DESIGN SPEC WRITTEN:** [output-model-unification.md](output-model-unification.md) — the
> target model, the invariants comparison-perfection depends on, the Claude/sol-002 split, and
> the staged migration. That spec supersedes this section for the output-model work.

These four are one architectural theme: **every export / consolidation / comparison should be
written the same way, in standardized, date-stamped locations, regardless of which surface
(Export tab, Consolidate tab, manual Compare, a matrix) produced it.** This is foundational —
the comparison-perfection work *reads* these locations, so the refactor must be **designed
now but implemented in deliberate stages** (each with a re-bless against the corpus), never as
a concurrent autonomous free-for-all. `paths.py` is the SoT to unify around.

| # | Note | Lane | Risk | Sequencing |
|---|------|------|------|-----------|
| 9 | Export-tab exports should go in a **date-specific run folder** like the vs-TSN matrix exports. *(Owner observed some export-tab reports in a different folder than the run-folder convention — **Step 0: trace where each export type actually writes**: which reports, which surfaces, the exact current paths. The inconsistency may be partial, not uniform.)* | ARCH/SOL | High — everything downstream parses export folders | Verify the real current layout FIRST; then the output-model design; export-engine mechanics can be SOL after design |
| 10 | **Overall export consistency** — all exports done basically the same regardless of surface (except the Everything matrix's own store, which is intentional). Matrices should be a *front-end* over the same comparisons done manually. Owner nuance: today the matrix's comparisons are **split from the manual ones** (it does export + comparison + consolidation on one page, into matrix-owned folders) — both already ride the same `compare_env`/`compare_core` engine, so unify the **output location/naming/discoverability**, not a second implementation, so a matrix cell and a manual compare of the same day/report yield the SAME artifact in the SAME place. | ARCH | High — cross-cutting | Design decision (Claude); the unifying principle for 9/11. See [output-model-unification.md](output-model-unification.md) §2 principle 4. |
| 11 | **Output-folder standardization** — comparisons, consolidations, exports all in sensible, standardized locations so every feature can consume them. | ARCH | Highest — touches `paths.py` + all consumers | Design FIRST (Claude); the foundation for 7/9/12 |
| 13 | Put the **export date onto all exported reports** (already used as an Int Eff-Date identity column in Intersection Detail); integrate properly everywhere. | ARCH/CMP | Med — couples to comparison parsing (filenames/columns) | Design where the date lives (name vs content) before implementing; comparison side is Claude |

## Comparison-lane items (Claude, fold into the comparison work)

| # | Note | Lane | Risk | Notes |
|---|------|------|------|-------|
| 1 | **Detailed comparison logging** — for debugging + status; when something goes wrong, log exactly what. | CMP | Low | Quick win; directly serves comparison-perfection debuggability. Do alongside. |
| 2 | A new **TSMIS Excel-vs-PDF consistency matrix** — verify Excel and PDF versions are consistent across reports. | CMP/GUI | Med | Builds on the existing per-report PDF-vs-Excel self-check comparators (`compare_*_pdf`); a new matrix front-end. Design after core. |
| 5 | **Unique matrix comparison report names** — currently same filename in separate folders; make names self-identifying so multiple comparisons of one report can be opened + told apart. | CMP | Low-Med | Output naming; do alongside once the output-model naming is decided (small). |
| 7 | Manual comparison should **auto-save to a dedicated manual-comparison folder** (not anywhere). | CMP | Low-Med | Depends on the output-model (item 11) decision for the canonical location. |

## GUI / matrix UX items (Claude; need `#mock` verification)

| # | Note | Lane | Risk | Notes |
|---|------|------|------|-------|
| 3 | Prepare a **workflow for new / format-changed reports** so future additions are flawless too (report_catalog SoT + the add-a-report recipe + consolidate/compare/matrix wiring). | ARCH/GUI | Med | The "add a report" story; partly exists (`report_catalog` derivation + `check_report_catalog`). Document + tighten the recipe. |
| 4 | **Rearrange dates (columns)** on the matrices, not just rows. | GUI | Low-Med | Extends `matrix.apply_order` to the day/column axis + the drag UI. |
| 6 | **Consolidate dropdown** should only show days where that report is actually present (not all export days). | GUI | Low | Discovery filter in the consolidate day picker. |
| 8 | **Manual comparison** should use a **dropdown like consolidate**, showing only days with that specific report (manual file-pick kept as a rare fallback). | GUI | Med | Mirrors item 6 for the Compare tab. |

## Export-engine item (candidate for a future SOL mission)

| # | Note | Lane | Risk | Notes |
|---|------|------|------|-------|
| 12 | **Single-pass dual-format export** — when exporting a report's PDF + Excel together, generate the route once and pull BOTH formats there, instead of a second full regeneration pass. Owner thinks this was done (only?) for a specific report. | SOL | Med | `run_export_combined` (v0.19.2) does this for coalesced same-`data_value` editions on the standard path (not fast mode). Task = audit which exports still double-pass + extend the single-pass path. Export-engine (Sol's lane) — but live-verify is owed (Sol can't drive the site) and it couples to item 9. Best as **sol-002 after the output-model design**. |

## Recommended sequencing (Claude's call, owner to confirm)

1. **Now:** dispatch sol-001 (reliability engine) unchanged; it is clean + non-colliding.
2. **Alongside comparison-perfection (quick, no output-model dependency):** item 1 (comparison
   logging), item 5 (unique comparison names).
3. **Foundational design (Claude):** the **output-model unification** (9/10/11/13) — write the
   target-state spec (canonical folders in `paths.py`, run-folder shape, date placement). This
   unblocks 7, 9, 12, 13 and any Sol export work, and de-risks everything downstream. Design
   soon; implement in staged, re-blessed steps so it never destabilizes the comparison corpus.
4. **After the design / after core stabilizes:** the GUI/matrix items (2, 3, 4, 6, 8) and the
   comparison output-path items (7).
5. **sol-002 (future):** implement the export-engine mechanics (item 12, and the export side of
   9/13) to the fixed output-model spec — safe because it implements a decided architecture.
