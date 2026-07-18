# Output-model unification — design spec (Claude-owned, 2026-07-17)

Resolves backlog items **5, 6, 7, 8, 9, 10, 11, 12, 13** from
[app-consistency-backlog.md](app-consistency-backlog.md): make every export, consolidation,
and comparison write the **same way, in standardized, self-identifying, date-stamped
locations**, from a single `paths.py` SoT — so any surface (Export tab, Consolidate, manual
Compare, the matrices) produces files any other feature can consume.

**Status:** design (Claude owns the decisions). Implementation is **staged** and **split**
(§5) because the comparison engine READS these locations — see the invariants (§3), which the
migration must not break without a coordinated re-bless.

> This is the foundation for **sol-002**. The design decisions here are Claude's. Sol
> implements the export-side conformance to this spec; Claude implements the comparison-side.

## 1. Current model (from `paths.py` + the surfaces)

> **⚠ VERIFY-FIRST (owner note 2026-07-17).** This current-state map mixes confirmed code facts
> (the `paths.py` helpers — dated run folders, `stamped_consolidated_filename`, the Everything
> store, `list_output_days_for_report`) with **owner OBSERVATIONS that are not yet fully
> code-traced** — especially the 9/10 "export-tab vs matrix don't share plumbing" split and the
> 6/8 day-picker behavior. **Step 1 of any implementation is to confirm each claim against the
> actual code + a real run** (which reports, which surfaces, exact paths). The design below is
> only valid if this map is accurate, so a wrong assumption here invalidates the corresponding
> fix — trace before building.

- **Dated run folders (the good model):** `output/<YYYY-MM-DD src-env>/<report>/…route_<n>.<ext>`
  via `output_run_dir(src, env, day)`. Self-labeling; cross-env parses `<day src-env>`.
- **Consolidated:** `output/<day>/consolidated/<name> <day>.xlsx` (`stamped_consolidated_filename`).
- **Everything store (intentionally different):** an always-current `<dest>/<src-env>/…` with
  `env_tagged_filename` prefixes — a live dashboard, NOT per-day. Item 10 keeps this as-is.
- **Comparisons (scattered):** `output/comparisons/tsn/`, `…/tsn-by-day/<day>/`,
  `…/baseline-by-day/`, matrix comparisons under `<dest>/comparisons/<baseline>/`, and **manual
  Compare wherever the user picks** — with **non-unique filenames** (same name, different
  folder).
- **TSN library (fine):** `tsn_library/<report>/{raw,consolidated,pdf}`.

### The inconsistencies the backlog names
- **9/10:** Export-tab exports and matrix exports don't use the same layout/plumbing.
- **11:** comparison/consolidation/export locations aren't one standardized, discoverable scheme.
- **5:** comparison filenames aren't unique/self-identifying (only the folder distinguishes them).
- **7:** manual Compare saves anywhere.
- **6/8:** the Consolidate + manual-Compare day pickers show ALL days, not days where the report
  is actually present (even though `paths.list_output_days_for_report(subdir)` already exists).
- **13:** the export date isn't uniformly stamped onto exports.
- **12:** dual-format (PDF+Excel) export sometimes regenerates the route twice instead of once.

## 2. Design principles

1. **One SoT.** Every write location is a `paths.py` function; no surface hard-codes a path.
2. **Dated run folders everywhere** for per-route exports (`output/<day src-env>/<report>/`),
   regardless of surface — EXCEPT the Everything always-current store, which stays its own
   deliberate model.
3. **Self-identifying filenames.** A file lifted out of its folder still says what it is
   (report + kind + sides + day/src-env). Preserve the `…_route_<token>.<ext>` **suffix
   anchor** the consolidators glob on (see §3).
4. **Matrices are a front-end, not a separate storage model OR a separate comparison path**
   (item 10). A matrix cell's export/consolidate/compare must land in the SAME place the manual
   surface would, so the two are interchangeable and mutually consumable. The owner's deeper
   point: today the matrix's comparisons are effectively **split from the manual ones** (the
   matrix does export + comparison + consolidation on one page and writes into matrix-owned
   folders, while manual Compare is a separate flow). Both already ride the same
   `compare_env`/`compare_core` engine, so the unification is about **output location + naming +
   discoverability**, not a second comparison implementation — the goal is that a matrix cell and
   a manual comparison of the same day/report produce the SAME artifact in the SAME place,
   differing only in which button launched them. The Everything-matrix store
   (`All Reports (current)/…`) is the ONE intentional exception (a live per-report dashboard).
5. **Backward-compatible + staged.** New readers accept old layouts; migration is per-surface,
   each with a re-bless of the affected comparison canaries.

## 3. INVARIANTS — do not break without a coordinated re-bless (Claude gate)

These are load-bearing for the comparison engine + consolidators. Any change touching them is
Claude's call and needs the full corpus re-bless (`%TEMP%\tsmis_regress` + the golden checks):

- **`…_route_<token>.<ext>` end-anchored suffix** — consolidators discover inputs with
  `*.xlsx`/`*.pdf` globs and pull the route via `_route_(\w+)\.(xlsx|pdf)$`. A date/tag MUST go
  in FRONT (like `env_tagged_filename`), never before the extension (`env_tagged_filename`
  docstring). CMP-AUD-030/031 also require the `_route_<n>` contract + zero-pad normalization.
- **Run-folder name shape `<YYYY-MM-DD> <src>-<env>`** — `parse_run_folder` / cross-env side
  labels / the by-day + baseline matrices parse it.
- **Consolidated sheet names + headers** (e.g. `"Intersection Detail"`, the leading `Route`
  column, the exact `_TSMIS_HEADER` editions) — the vs-TSN + PDF + cross-env loaders bind them.
- **TSN library layout** `tsn_library/<report>/{raw,consolidated,pdf}` + the normalization
  marker/version gates.
- **Comparison output committing** goes through `artifact_store.commit_workbook` +
  `consolidation_meta` — any new comparison location must still route through that transactional
  path (ownership lease, alias guard, sidecars).

## 4. Target model (the decisions, item by item)

- **Unified export location (9/10):** every per-route export — Export tab, matrix cell,
  by-day — writes `output/<day src-env>/<report>/<report>_route_<token>.<ext>` via
  `output_run_dir`. Retire any alternate export path. (The Everything always-current store is
  the ONE documented exception.) → **sol-002 export-side.**
- **Single-pass dual-format (12):** when both editions of a report (same `data_value`, e.g.
  Excel + PDF) are selected, generate the route ONCE and save both files off it
  (`run_export_combined` already does this for coalesced editions on the standard path — audit
  which surfaces/fast-mode still double-pass and extend it). → **sol-002 export-side.**
- **Date stamping (13):** two distinct things — (a) PROVENANCE: the run-folder `<day src-env>`
  already dates every export by path; make the per-file name carry it too where a file can be
  lifted out (front-anchored, like `env_tagged_filename`). (b) CONTENT: the Intersection Detail
  "Int Eff-Date" identity column is a report-content concern, not the export date — keep these
  separate; do NOT stamp the export date into report content. → provenance side = sol-002;
  content stays report-specific (Claude if comparison-relevant).
- **Standardized comparison outputs (11):** one scheme —
  `output/comparisons/<kind>/<self-identifying-name>.xlsx` where `<kind>` ∈
  {`vs-tsn`, `pdf-vs-excel`, `cross-env`, `baseline`, `manual`}. → **Claude comparison-side.**
- **Unique comparison filenames (5):** the name encodes `report + kind + sideA-vs-sideB + day/
  src-env` (e.g. `intersection_detail_tsmis-vs-tsn_2026-07-17-ssor-prod.xlsx`) so multiple
  comparisons of one report open together and are self-describing. → **Claude comparison-side.**
- **Manual Compare canonical folder (7):** manual comparisons auto-save to
  `output/comparisons/manual/` by the §5 naming, with the current free file-pick kept as a rare
  override. → **Claude comparison-side + GUI.**
- **Present-only day pickers (6/8):** the Consolidate day dropdown and the manual-Compare day
  dropdown filter to `paths.list_output_days_for_report(subdir)` (the plumbing exists); manual
  Compare gains a Consolidate-style dropdown with the free-pick fallback. → **Claude GUI.**

## 5. Work split

| Area | Owner | Why |
|---|---|---|
| The `paths.py` SoT design + the target layout/naming | **Claude** | architecture; comparison reads it |
| Export-side conformance: unified run-folder writes (9/10), single-pass dual-format (12), front-anchored date stamping (13a) | **sol-002 (Codex)** | export engine = Sol's lane; conforms to this spec |
| Comparison-output paths + unique names (5, 11) + manual-Compare canonical folder (7) | **Claude** | touches comparison-output committing + the matrices |
| GUI: present-only dropdowns (6/8), manual-Compare dropdown, date-column reorder (item 4) | **Claude** | needs `#mock` verification (not cloud-doable) |
| The Excel-vs-PDF consistency matrix (item 2) | **Claude** | comparison front-end over existing PDF-vs-Excel comparators |
| New-report workflow hardening (item 3) | **Claude** | report_catalog SoT + the add-a-report recipe |

## 6. Migration (staged, each step re-blessed)

1. **paths.py first:** add the unified functions (new names; keep the old ones as thin
   deprecated shims so nothing breaks mid-migration). No behavior change yet.
2. **Export-side (sol-002):** migrate each export surface to the unified functions; add
   discovery-audit of all current write sites (the 57-file map) as milestone 1; verify the
   `…_route_<token>` invariant holds; run the gate. Live-export verification is owed (Sol can't
   drive the site) → work-PC checklist item.
3. **Comparison-side (Claude):** migrate comparison outputs to the standardized scheme + unique
   names; re-bless every affected canary (the names change, not the cell contents — prove
   cell-for-cell identity, only the file path/name differs).
4. **GUI (Claude):** dropdown filtering + manual-Compare dropdown, verified in `#mock`.
5. **Retire the shims** once every surface is migrated + green.

## 7. sol-002 charter sketch (finalize when dispatched)

- **Outcome:** every export surface writes through the unified `paths.py` run-folder model;
  dual-format exports single-pass; exports carry front-anchored date provenance — no comparison
  or GUI file touched.
- **Owns:** `exporter*.py`, `export_multi.py`, `run_report.py`, `batch_manifest.py`,
  `gui_worker_export.py` (export-worker path calls only), and the NEW export-side `paths.py`
  functions Claude adds first. **Off-limits:** the comparison engine, the comparison-output
  paths, the matrices' compare logic, the GUI front-end, `report_catalog`/`reports`.
- **Milestone 1 (discovery):** map all current export write sites (the 57-file scatter) →
  `FINDINGS`; confirm the `…_route_<token>` invariant everywhere.
- **Acceptance:** gate green; the `…_route_<token>.<ext>` end-anchor preserved
  (CMP-AUD-030/031 checks stay green); a golden check proves each export surface now resolves
  the unified location; live-export verification listed as owed.
- **Hard dependency:** Claude lands the unified `paths.py` functions (migration step 1) BEFORE
  sol-002 starts, so Sol conforms to a fixed SoT rather than inventing one.

## 8. Sequencing vs comparison-perfection (Claude's priority)

Comparison-perfection stays the priority. This spec is produced alongside. Concrete order:
Claude lands **paths.py step 1** (additive, no behavior change) at a safe point → sol-002 runs
the export-side in parallel → Claude does the comparison-side + GUI as comparison-perfection
milestones allow. Nothing here blocks comparison finding 063; the paths.py additive step is
low-risk and can slot between comparison batches.
