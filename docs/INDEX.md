# TSMIS Reports Exporter — knowledge library

The canonical, deduplicated home for everything we know about this project, written
for AI agents (and humans) working on the repo. Each file is the **single source of
truth** for its domain; where topics overlap, the owner holds the detail and the
others link to it.

**Start here:** [`../CLAUDE.md`](../CLAUDE.md) is the slim **router** — it carries the
project snapshot and the non-negotiable conventions, and points into this library.
Read the conventions there first, then come here for the deep dive on whatever you're
touching.

## The docs

| Doc | Read this when… |
|---|---|
| [architecture.md](architecture.md) | You need the big picture — the console-free core + two front-ends, the `Events` seam, the single report registry, run folders, the data-location model, and the v0.12/v0.13 feature buckets. |
| [engine-and-reliability.md](engine-and-reliability.md) | You're touching the export loop's runtime behavior — resume + integrity gate, skip/cancel, retry, the fast-fails (`EmptyExport`/`ReportError`/`ReportUnavailableError`), timeouts, fast mode, preflight, run reports. |
| [auth-and-signin.md](auth-and-signin.md) | Anything about signing into TSMIS — the token-in-hash session model, the `CONFIG` lexical-global trap, device sign-in / Edge recapture / portability, LNA pre-grant, signed-in detection, the two login chips. |
| [gui.md](gui.md) | You're in the desktop GUI — pywebview/WebView2, the threading + queue model, Python↔JS layering, the **five pywebview traps**, the `#mock` preview and its gotchas. |
| [reports.md](reports.md) | You need the report catalog, a single report's `ReportSpec`/save/empty behavior, the `cs-disabled` rule, or the "add a report / consolidator / comparison" recipes. |
| [comparison-engine.md](comparison-engine.md) | You're in `compare_core` — the regression lock + harness, the two flavors, key-field / roadbed key / duplicate-pairing, ditto non-asserting, the verdict / incompleteness contract, write-path safety, the three comparison families, the **visual-evidence decoration** (§13 — `visual_evidence` + the `evidence_*` adapters: Highway Detail, Intersection Detail, Highway Log, Highway Sequence). |
| [highway_log/columns.md](highway_log/columns.md) | You need the corrected 31-column Highway Log labels (the vendor mislabeled most) — `highway_log_columns.py`, tooltips, the Legend sheet. |
| [highway_log/pdf-and-tsn-parsing.md](highway_log/pdf-and-tsn-parsing.md) | You're parsing a Highway Log PDF — the TSMIS cell-rect parser and the TSN character-window parser (with the 3 description guards), the two PDF formats, the flawless-validation results. |
| [highway_log/comparison-study.md](highway_log/comparison-study.md) | You need the `+`/`++` **ditto domain convention** and the raw evidence behind it (the "pointer to the paired roadbed, not data" finding + the roadbed-encoding split §7b). |
| [tsn-parsers.md](tsn-parsers.md) | You need a **non-HL report's TSN format + comparison schema** — the per-report TSN file format, column→TSMIS mapping, key field, normalization, and approved sample counts (filled during v0.17.0). HL's own TSN specifics stay under highway_log/. |
| [build-and-release.md](build-and-release.md) | You're building/packaging/releasing — PyInstaller `app.spec`, `prune_bundle.ps1` + the DLP guard, the three browser-channel variants, the full **updater** (swap mode / MOTW / SHA-256 / revert), and CI (`release.yml` / `checks.yml`). |
| [it-and-security.md](it-and-security.md) | You need the IT/DLP/security view — what the app talks to, files it touches, browser flags, the **work-PC capability model**, the read-only audit's findings + the "good designs," and code-signing. |
| [website.md](website.md) | You're touching the **`gh-pages` landing page** — the single-screen layout, the live-resolving Download button, the System/Light/Dark toggle, screenshot/OG regeneration (`tools/screenshots.py`), favicon, and SEO (sitemap/Search Console). |
| [verification-and-testing.md](verification-and-testing.md) | You need to verify a change — the golden `check_*.py` catalog, the COM-recalc compare loop, the `#mock` preview, the owed live-export, where the real test data + website source live (local only), and the diagnostics. |
| [work-pc-validation.md](work-pc-validation.md) | You're running the **work-PC operational sign-off** (still owed; cuts as **v0.18.5**) — the credential-safe `--collect-evidence` kit, the manual fallback, the §K2 work-PC acceptance checklist, and the sign-off process. (Two-tier model: v0.18.0 = offline candidate; v0.18.1 closed out the overhaul; the field sign-off was deferred and now targets v0.18.5.) |
| [lessons.md](lessons.md) | You want the project's hard-won judgment — the three field failures, "refactor to one core," regression-lock discipline, "consolidate from raw," "verify agent claims," audit methodology. Distilled; links to the owners. |
| [history.md](history.md) | You want the narrative — how a one-day console script became a self-updating desktop app, the dead ends and reverts, the field failures that rewrote the design (through v0.18.1). |
| [roadmap.md](roadmap.md) | You're picking future work — the deferred/dormant/blocked backlog (A3, C1, D1, F1, code-signing, live-export verification, the dormant Med Wid gap). |
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

## Conventions, archive, and external resources

- **Conventions** (console-free core, UI-neutral strings, no AI attribution, never commit
  the auth file, regression-lock discipline, call the timeout accessors, branch off `main`)
  live in [`../CLAUDE.md`](../CLAUDE.md).
- **`CHANGELOG.md`** (repo root) is the user-facing changelog, one section per version.
  `release.yml` publishes each release body from the matching section + the shared
  `build/release_notes_header.md` (via `build/gen_release_notes.py`); history.md is the narrative.
- **Real test data + the live TSMIS website source are LOCAL ONLY** (under
  `C:\Users\Yunus\Downloads\TSMIS\…` on the dev PC) and are **never** committed, copied
  into the repo, or pushed — the website source is Caltrans-internal. See
  verification-and-testing.md for what lives where.
- The former `~/.claude` session-memory files were harvested into this library and archived
  under `memory/_archive/` (see `MEMORY.md`); this `docs/` library is now the canonical home.
