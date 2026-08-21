# TSMIS Reports Exporter — knowledge library

The canonical, deduplicated home for everything we know about this project, written
for AI agents (and humans) working on the repo. Each file is the **single source of
truth** for its domain; where topics overlap, the owner holds the detail and the
others link to it.

**Start here:** [`../CLAUDE.md`](../CLAUDE.md) is the slim **router** — it carries the
project snapshot and the non-negotiable conventions, and points into this library.
Read the conventions there first, then come here for the deep dive on whatever you're
touching.

## Current status and work

**Current release: v0.41.0 (2026-08-20).** Correctness has nothing open — all 245
comparison-audit findings are closed.

- **Start every session at [roadmap.md](roadmap.md)** — its `▣ OPEN WORK INVENTORY`
  is the definitive list of what is left, and the banner above it says where things
  stand and what is next. Re-verify a line against the code before acting on it.
- **Active bounded workflow:**
  [planning/post-comparison-perfection-output-audit/START-HERE.md](planning/post-comparison-perfection-output-audit/START-HERE.md)
  is the operational entry point for the post-comparison output program. **RB-1
  through RB-4 are merged; RB-5 is READY and not started, RB-6 is blocked behind
  it** — five work items (HF-06 · 07 · 08 · 09 · 11) are still open and are tracked
  as **group H** in the roadmap. Read START-HERE before starting a bundle; it names
  the queue position, exact-base rule, and controlling prompt. The plan froze at
  v0.35.0, so check its scope statements against today's code.
- **Historical handoff:** [agent-handoffs/STATUS.md](agent-handoffs/STATUS.md) records
  the closed `sol-001` mission. It is retained as evidence, not as current project
  authority or a live worklist.

## The docs

| Doc | Read this when… |
|---|---|
| [architecture.md](architecture.md) | You need the big picture — the console-free core + two front-ends, the `Events` seam, the single report registry, run folders, the data-location model, **"The app today"** (the six tabs and the three source lanes, current at v0.41.0), and the v0.12→v0.18 feature buckets as a historical record. |
| [engine-and-reliability.md](engine-and-reliability.md) | You're touching the export loop's runtime behavior — resume + integrity gate, skip/cancel, retry, the fast-fails (`EmptyExport`/`ReportError`/`ReportUnavailableError`), timeouts, fast mode, preflight, run reports. |
| [auth-and-signin.md](auth-and-signin.md) | Anything about signing into TSMIS — the token-in-hash session model, the `CONFIG` lexical-global trap, device sign-in / Edge recapture / portability, LNA pre-grant, signed-in detection, the two login chips. |
| [gui.md](gui.md) | You're in the desktop GUI — pywebview/WebView2, the threading + queue model, Python↔JS layering, the **five pywebview traps**, the `#mock` preview and its gotchas. |
| [reports.md](reports.md) | You need the report catalog, a single report's `ReportSpec`/save/empty behavior, the `cs-disabled` rule, or the "add a report / consolidator / comparison" recipes. |
| [comparison-engine.md](comparison-engine.md) | You're in `compare_core` — the regression lock + harness, the two flavors, key-field / roadbed key / duplicate-pairing, ditto non-asserting, the verdict / incompleteness contract, write-path safety, the comparison families (including the two ArcGIS-sourced ones, §9j Clean Road and §9k Highway Detail vs layers), the **speed contract** (§2b — the composite-style cache and the streamed package read, both output-locked) and the **counts-only preview** (§2c — what it does and why it can never certify), and the **visual-evidence decoration** (§13 — the five print-crop adapters: Highway Log, Highway Sequence, Intersection Detail, Ramp Detail, and **Highway Detail** since v0.37.0; HD is vs-TSN only, the env lane stays at four). |
| [planning/comparison-perfection/README.md](planning/comparison-perfection/README.md) | You want to know **why a comparison behaves the way it does**. The comparison-perfection project's record — **COMPLETE, shipped as v0.28.0**; **245/245 CLOSED, nothing open** — the HD pre-release block (133 · 142 · 186 · 192 + 045-HD) fell to the vendor's 2026-08-17 release in v0.37.0 / v0.38.0, and the last two findings were 244 (v0.38.2) and 245 (v0.39.1). Audit ledgers, source bindings, canary bindings and advisory reviews in one folder. It is a record, not a worklist. |
| [planning/comparison-perfection/comparison-phase4-tsn-source-rebaseline.md](planning/comparison-perfection/comparison-phase4-tsn-source-rebaseline.md) | You're auditing or changing a vs-TSN source, normalizer, comparator, or evidence adapter — exact 29-member comparison-truth and 14-member evidence manifests, source roles, member hashes, raw identity facts, known admission defects, and the Phase-4 source-first gates. |
| [highway_log/columns.md](highway_log/columns.md) | You need the corrected 31-column Highway Log labels (the vendor mislabeled most) — `highway_log_columns.py`, tooltips, the Legend sheet. |
| [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) | You're parsing a Highway Log PDF — the TSMIS cell-rect parser and the TSN character-window parser (with the 3 description guards), the two PDF formats, the flawless-validation results. |
| [highway_log/comparison-study.md](highway_log/comparison-study.md) | You need the `+`/`++` **ditto domain convention** and the raw evidence behind it (the "pointer to the paired roadbed, not data" finding + the roadbed-encoding split §7b). |
| [tsn-parsers.md](tsn-parsers.md) | You need a **non-HL report's TSN format + comparison schema** — the per-report TSN file format, column→TSMIS mapping, key field, normalization, and approved sample counts (filled during v0.17.0). HL's own TSN specifics stay under highway_log/. |
| [build-and-release.md](build-and-release.md) | You're building/packaging/releasing — PyInstaller `app.spec`, `prune_bundle.ps1` + the DLP guard, the three browser-channel variants, the full **updater** (swap mode / MOTW / SHA-256 / revert), and CI (`release.yml` / `checks.yml`). |
| [it-and-security.md](it-and-security.md) | You need the IT/DLP/security view — what the app talks to, files it touches, browser flags, the **work-PC capability model**, the read-only audit's findings + the "good designs," and code-signing. |
| [website.md](website.md) | You're touching the **`gh-pages` landing page** — the single-screen layout, the live-resolving Download button, the System/Light/Dark toggle, screenshot/OG regeneration (`tools/screenshots.py`), favicon, and SEO (sitemap/Search Console). |
| [verification-and-testing.md](verification-and-testing.md) | You need to verify a change — the golden `check_*.py` catalog, the COM-recalc compare loop, the `#mock` preview, the owed live-export, where the real test data + website source live (local only), and the diagnostics. |
| [work-pc-validation.md](work-pc-validation.md) | You're running the **work-PC operational sign-off** (still owed) — the credential-safe `--collect-evidence` kit, the manual fallback, the §K2 work-PC acceptance checklist, and the sign-off process. The current acceptance target and additions are maintained in `CLAUDE.md` and [planning/v0.30-owner-backlog-plan.md](planning/v0.30-owner-backlog-plan.md) §4; do not use this document's historical v0.18.x narrative as a release target. |
| [lessons.md](lessons.md) | You want the project's hard-won judgment — the three field failures, "refactor to one core," regression-lock discipline, "consolidate from raw," "verify agent claims," audit methodology. Distilled; links to the owners. |
| [history.md](history.md) | You want the narrative — how a one-day console script became a self-updating desktop app, the dead ends and reverts, the field failures that rewrote the design, and the four threads running through all of it (17 chapters, through v0.41.0). |
| [roadmap.md](roadmap.md) | **You're picking what to work on next** — the `▣ OPEN WORK INVENTORY` is the definitive remaining-work list (owner-owed acceptance run, vendor/site waits, the ArcGIS findings, the RB-5/RB-6 program, hygiene, and the next large build), with the themed sections below it holding the rationale. |
| [planning/cleanroad-highways.md](planning/cleanroad-highways.md) | You're building or changing a **Clean Road** file from the ArcGIS layers — the measured overlay model, the 74-column THY coverage census, the layer-export input contract, and the already-censused CA INTERSECTIONS / CA RAMPS mappings that the next large build (roadmap G1) starts from. |
| [planning/vs-tsn-comparison-speed.md](planning/vs-tsn-comparison-speed.md) | You're about to make a comparison faster — the v0.40–v0.41 record: what shipped, what was deliberately not taken and why, the measured phase breakdown (writing is 70%), and the benchmarking method that keeps numbers honest on a loaded box. |
| [code-review-prompt.md](code-review-prompt.md) | You're running an audit — the reusable, project-tailored read-only review prompt. |
| [agent-prompts.md](agent-prompts.md) | You're starting the **roadmap-curator** or the **fix-implementer** agent — the post-compact restart line + the fix-implementer prompt. |
| [roadmap-curator.md](roadmap-curator.md) | The **to-do-list manager's** operating manual — point a cloud or local agent at this one file to run the roadmap curator (intake ideas + keep the list synced as patches ship). |

## Internals (deep-dive, for future development)

Code-level walkthroughs under `docs/internals/` — the exhaustive "how it actually works"
companions to the topic docs above (algorithms, data/control flow, edge cases, extension
points), every claim anchored to `file:symbol`.

| Internals doc | Deepens | Covers |
|---|---|---|
| [internals/compare-core.md](internals/compare-core.md) | comparison-engine | `run_compare` end to end: the duplicate-pairing + per-route alignment algorithms, the streaming sheet build, the exact formula construction, the two-flavor mirror, the write-path guards. |
| [internals/highway-log-data-processing.md](internals/highway-log-data-processing.md) | highway_log/pdf-and-tsn-parsing + columns | The pdfplumber char→line→column geometry (fixed vs per-page windows), the 30→31 mapping, the description guards, the ramp-summary parse, the consolidator streaming core, the ditto/roadbed algorithms. |
| [internals/gui-bridge.md](internals/gui-bridge.md) | gui | The full Python⇄JS message lifecycle (kind→handler→event→renderer table), the single-task gate, every worker's `run()`, the env-scan concurrency, the JS boot/dispatch. |
| [internals/auth-state-machine.md](internals/auth-state-machine.md) | auth-and-signin | `navigate_with_auth` as an explicit state machine, the layered sign-in order, the three-step Edge recapture, portability probe, device-mode handles, the concurrency rules. |
| [internals/export-engine.md](internals/export-engine.md) | engine-and-reliability | The per-route loop step by step, the save strategies' mechanics, `_recover`/`_retry_failed_routes`, `wait_with_skip_option`, the parallel engine + crash reconciliation, where each error class is raised. |
| [internals/updater-swap.md](internals/updater-swap.md) | build-and-release | The download→stage→two-phase-swap pipeline, the PID wait + rename rollback, the staged allowlist, `update_support` tiers, revert resolution, cache clearing. |

## Find it fast (topic → doc)

- **Sign-in / OAuth / device SSO / managed Edge** → auth-and-signin.md (+ lessons.md for the field story)
- **pywebview traps / WebView2 / the `#mock`** → gui.md
- **Resume / retry / skip / cancel / timeouts / fast mode** → engine-and-reliability.md
- **`compare_core` / flavors / regression lock / roadbed key / ditto** → comparison-engine.md
- **Highway Log columns / PDF & TSN parsing / ditto evidence** → highway_log/
- **A non-HL report's TSN format / key / comparison schema** → tsn-parsers.md
- **Updater / swap mode / MOTW / DLP / `app.spec` / CI** → build-and-release.md
- **Work-PC constraints / what's safe for IT / audit findings** → it-and-security.md
- **Golden checks / how to verify / test-data locations** → verification-and-testing.md
- **Adding a report / consolidator / comparison** → reports.md
- **ArcGIS layers / Clean Road / rendering a report from the layers** → planning/cleanroad-highways.md + comparison-engine.md §9j–§9k
- **Making a comparison faster (and the rules that keep it output-locked)** → comparison-engine.md §2b–§2c + planning/vs-tsn-comparison-speed.md

## Conventions, archive, and external resources

- **Conventions** (console-free core, UI-neutral strings, no AI attribution, never commit
  the auth file, regression-lock discipline, call the timeout accessors, branch off `main`)
  live in [`../CLAUDE.md`](../CLAUDE.md).
- **`CHANGELOG.md`** (repo root) is the user-facing changelog, one section per version.
  `release.yml` publishes each release body from the matching section + the shared
  `build/release_notes_header.md` (via `build/gen_release_notes.py`); history.md is the narrative.
- **Real test data + the live TSMIS website source are LOCAL ONLY** (under
  `C:\Users\Yunus\Downloads\TSMIS\…` on the dev PC) and are **never** committed, copied
  into the repo, or pushed — the website source is Caltrans-internal. Read that
  corpus's `_INDEX.md` before choosing a fixture; see verification-and-testing.md
  for the repo-side rules.
- The former `~/.claude` session-memory files were harvested into this library and archived
  under `memory/_archive/` (see `MEMORY.md`); this `docs/` library is now the canonical home.
