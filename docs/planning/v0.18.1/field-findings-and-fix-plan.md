# v0.18.1 — work-PC field findings + fix plan (handoff, 2026-06-26)

Context-recovery doc for the v0.18.1 field close-out. Repo canonical knowledge = `docs/INDEX.md`;
this is the v0.18.1-specific delta. **Untracked planning artifact — never staged/committed.**

---

## 0. STATE SNAPSHOT (read first)

- **Branch:** `refactor/v0.18.0-structural-overhaul`, **HEAD `a80c100`** ("prepare v0.18.0", an EMPTY
  release-anchor). `version.py = 0.18.0`. P11 docs reconcile committed `375b48c`. Codex final review =
  **`READY FOR RELEASE PREPARATION`** (no blockers). Full offline suite green (74/75 — the 1 =
  `check_no_misspelling` on the untracked planning `P10-codex-review.md` hit only; CI-clean on the
  committed tree). Both frozen self-tests PASS (win64 150 MB + with-browser 524 MB).
- **v0.18.0 is NOT pushed and NOT tagged yet.** The branch is release-PREPARED only. The user already
  had a v0.18.0 frozen build on the work PC and tested THAT (evidence manifest: `version 0.18.0, frozen`,
  `data_root C:\Users\P311231\Downloads\Apps\TSMIS Exporter`). (An earlier MEMORY note saying "v0.18.0
  RELEASED / release.yml ran" was premature — corrected.)
- **Release decision (made, not executed):** user chose **"Release from the branch now"** — push the
  branch + tag `v0.18.0` → `release.yml` publishes the 3 zips + `.sha256`; **leave `main` at v0.17.8**;
  reconcile `main` later. The push/tag was approved but the user pivoted to the evidence run before I ran it.
- **`main` divergence (important):** `origin/main = 068b697 = v0.17.8`; local `main = 718defc = v0.17.7`
  (2 behind origin). `origin/main` has **11 commits the branch does NOT have** — the original
  v0.17.2–v0.17.8 work that CR-002 **forward-ported** (P14/P15) instead of merging. So histories diverged
  at `d2ee353`; **`git merge --ff-only` is impossible**. To make `main` = v0.18.x later, either an
  `-s ours` supersede merge (clean, no force-push) OR `git branch -f main … && git push --force` (drops
  the v0.17.x commits from main's line; they survive on their tags). Do NOT blind-`git merge` (conflicts +
  risks reintroducing the pre-refactor structure — the thing CR-002 avoided).

## 1. EVIDENCE (LOCAL ONLY — never commit/copy/push)

- Bundle zip: `C:\Users\Yunus\Downloads\TSMIS\tsmis_evidence_20260626_162023.zip` (extracted to
  `%TEMP%\tsmis_ev`). Contents: manifest.txt, self_test.txt, logs/tsmis.log(.1–.5), update_helper.log,
  ~50 run_reports CSVs (6/18–6/26).
- Dev-site source capture: `C:\Users\Yunus\Downloads\TSMIS\TSMIS Dev site 6.26\` — Caltrans-internal;
  `index.html` + the per-report JS. **Ground truth for selectors; never commit.**
- **Validation POSITIVES (v0.18.0 working):** live **Ramp Detail vs-TSN matched the locked canary
  exactly** (`TSMIS 15,215 / TSN 15,410 / union 15,414`); all 8 reports ran; fast mode @ 6 workers OK;
  prod Intersection correctly `cs-disabled` (dev-only, expected); only "errors" were that + one transient
  fast-mode browser timeout the engine reconciled + a normal SSO re-login.

## 2. BUG 1 — Intersection dropdown selector break  **[CONFIRMED, actively breaking]**

The dev site (capture `BUILD_DATE = '2026-06-25 11:45'`) restructured the `#customReport` report dropdown
from a FLAT `li.cs-option` list to a **nested submenu**:
```html
<li class="cs-sub cs-parent">Intersection
  <ul class="cs-submenu">
    <li class="cs-option cs-leaf" data-value="intersection_detail"  data-label="Intersection Detail">Detail</li>
    <li class="cs-option cs-leaf" data-value="intersection_summary" data-label="Intersection Summary">Summary</li>
  </ul></li>
```
- Intersection / Ramp / (disabled) Highway are now **parent** rows (`li.cs-sub.cs-parent`) holding a
  `ul.cs-submenu` of **leaf** options `li.cs-option.cs-leaf` whose **visible text is just "Detail" /
  "Summary"**; full name in `data-label`; stable id in `data-value` (`intersection_detail`,
  `intersection_summary`, `Ramp_Detail`, `Ramp_Summary`). Highway Log + Highway Sequence stay FLAT
  top-level `cs-option`. Note the Ramp relabel: `data-label="Ramp Detail"` (NO "TSAR:" prefix) vs our
  `ReportSpec.label="TSAR: Ramp Detail"`.
- **Why it breaks:** `report_nav._find_exact_option` (`scripts/report_nav.py:27-59`) matches
  `#customReport li.cs-option` by **`text_content() == report_label`**. The Intersection leaf text is
  "Detail" → 0 matches "Intersection Detail" → raises `PreflightError` ("didn't offer exactly one … entry").
- **Scope:** Intersection export on the **dev site is broken NOW**; ALL reports break once **prod** adopts
  this (the user says prod will follow but hasn't yet).
- **FIX (v0.18.1):** in `select_report` / `_find_exact_option`, match by the stable **`data-value`** (add a
  `data_value` to each `ReportSpec`, or a `label → data-value` map: ramp_summary→`Ramp_Summary`,
  ramp_detail→`Ramp_Detail`, highway_sequence→`highway_sequence`, highway_log→`highway_log`,
  intersection_summary→`intersection_summary`, intersection_detail→`intersection_detail`), with a fallback
  to `data-label`/text for the OLD flat menu; and **reveal the `cs-submenu`** (click/hover the
  `cs-parent`) before clicking the `cs-leaf`. Must handle BOTH old-flat and new-nested. Keep the
  `cs-disabled` check (still used). Build a **SYNTHETIC** nested-menu fixture under `build/fake_site/`
  (mimic the structure above — do NOT commit the real captured source) and lock with
  `build/check_fake_site.py` / `build/check_export_engine.py`.
- Memory: `[[tsmis-dropdown-nested-submenu-migration]]` (has the full HTML structure).

## 3. BUG 2 — Matrix queue chip won't clear after a job finishes  **[NARROWED; frontend phantom]**

- **Symptom (user, precise):** after a matrix / by-day job FINISHES, the queue chip **lingers**; the gate
  is FINE ("you can still do whatever you want"). NOT a stuck gate; new actions run.
- **Backend is CORRECT:** `gui_api._end_task` (`scripts/gui_api.py:645-680`) → `_coord.release()`
  (`current_job=None`, `task=None`) + **`_push_state()` (line 676)** + `_try_start_next_matrix_job()`.
  Snapshot fields: `gui_api.py:342-344` (`matrix_queue` = `[_job_view(j) for j in _queue]`,
  `matrix_current` = `_job_view(_current_job)` or null). Both queue panels re-render on EVERY state push:
  `app.js:1182` does `S.st=ev.s; renderState(); updateMatrixProgress(); updateDayMatrixProgress();`.
  `renderQueuePanel` (`ui-matrix.js:68-82`) **hides** the group when `!cur && !pending.length`. So the
  obvious paths all clear correctly.
- **The gap found:** `_try_start_next_matrix_job` (`scripts/gui_matrix.py:174-197`) MUTATES the queue
  (`take_next` pops the next job; drops no-work / errored jobs) but **only pushes state in the "started"
  branch (line 192)**. The no-work drop (`196-197`) and the dispatch-exception drop (`185-190`) do
  `release() + emit_log + continue` with **NO `_push_state()`** → the frontend's `matrix_queue` stays
  stale (shows the just-drained chip) until the next unrelated push. Also re-check the by-day auto-chain in
  `_on_matrix_export_done` (`gui_matrix.py:1062-1081`): it does `_end_task()` THEN `_enqueue_matrix_job(chain)`
  — ordering/timing of the intermediate `current=null` push worth confirming in the mock.
- **FIX (v0.18.1):** push a fresh state after EVERY queue mutation in `_try_start_next_matrix_job` (the
  no-work + exception branches), so the displayed queue always matches the deque. **Reproduce in the
  `#mock`** (mock.js has a queue sim: `matrix_queue`/`matrix_current`, lines ~383-405, 1070-1090) and add a
  Node render check (model on `build/check_mx_partial_render.js`) asserting the panel clears after a
  finished/drained job. Confirm the exact trigger before claiming fixed.
- **Files:** `scripts/gui_matrix.py` (queue: `_enqueue_matrix_job`/`_try_start_next_matrix_job`
  160-197; `_job_view` 124; `matrix_queue_*` 736-782; `matrix_stop_all` 784-799; `_on_matrix_done` 1032,
  `_on_matrix_export_done` 1049), `scripts/gui_api.py` (`_end_task` 645-680; snapshot 342-344; coord
  proxies `_current_job`/`_queue` 496-522), `scripts/task_coordinator.py` (owns `current_job`/`queue`/
  `task`; `release` 66-71, `take_next` 117-128, `enqueue` 104-115), `scripts/ui/ui-matrix.js`
  (`renderQueuePanel` 68-82; `updateMatrixProgress` ~11+55→matrixQueueGroup; `updateDayMatrixProgress`
  961-1010→dayQueueGroup), `scripts/ui/app.js` (state dispatch 1182).

## 4. ALSO OWED for v0.18.1

- **`wait-js-fstring-interpolation-unvalidated`** — `docs/roadmap.md` §J2 records it "Resolved in P8b" but
  it is **NOT in the shipped code** (`scripts/exporter.py:432-433` interpolates `spec.wait_js(route)` with
  no config-error validation; no locking check). Carried-forward; fold the validator + a `check_export_engine`
  case into v0.18.1.
- The full **v0.18.1 work-PC acceptance checklist** lives in `docs/work-pc-validation.md` §3 (the carried
  P1/P2/P3/P8c/P10/PA live items + the Int-Detail (PDF) live reconciliation). This evidence run already
  satisfies several positives (§1).

## 5. v0.18.1 PROCESS (two-tier model; per `docs/work-pc-validation.md` §4)

1. **Fixture-first (RED) then fix**, one bug at a time. **Do the dropdown FIRST** (actively breaking exports).
2. Each fix: committed synthetic fixture / check that fails on current code → fix → green.
3. Re-run the **full offline suite** (`build/check_*.py` + `*.js`; expect 74/75 with the known planning hit)
   **and both frozen self-tests** (`build.ps1 -SelfTest` and `-SelfTest -BundleChromium`).
4. Set `version.py = 0.18.1`; add a `## v0.18.1` `CHANGELOG.md` section; cut the release via `release.yml`
   (push tag `v0.18.1`).
5. Reconcile `main` (the diverged v0.17.8 → v0.18.x) — `-s ours` supersede or force-update (see §0).
6. Optionally cut **v0.18.0** itself first (push branch + tag) if the user wants the candidate published
   before the fixes — but the user already has a working v0.18.0 build, so v0.18.1 may be the first push.

## 6. NON-NEGOTIABLE INVARIANTS (don't break)

- Core is **console-free**; `compare_core` is **regression-locked** (0-diff vs branch point `d2ee353`;
  **no `context_fill`**) — any formula/label change needs cell-for-cell proof.
- `report_catalog.py` is the report-metadata **SoT** (`reports.py` derived); stable-IDs **append-only**
  (`batch_manifest._V017_EXPORT_ORDER`, `intersection_detail_pdf` = index 7).
- Outcome contract: a **partial never promotes / caches / shows green**.
- **No AI attribution** anywhere. Planning folder **never staged**. The product name is ALWAYS **TSMIS**
  (the transposition is CI-guarded by `check_no_misspelling`).
- **LOCAL-ONLY:** the evidence bundle, the dev-site source, and all real TSN/TSMIS test data live under
  `C:\Users\Yunus\Downloads\TSMIS\…` — never commit, copy into the repo, or push.

## 7. SCOPE DECISION (2026-06-26) + IMPLEMENTATION STATUS

User answered: **bundle EVERYTHING into one v0.18.1** (no split). Five phases, plus two new
asks layered on the original field fixes:
- **A — Dropdown selector** (field bug 1): match by stable `data-value`, reveal the flyout. PROD-SAFE.
- **B — Matrix queue phantom** (field bug 2): push state on every queue mutation.
- **C — wait_js** interpolation validation (carried-forward).
- **D — Group reports like the website** (NEW): flat Highway Log/Sequence + Ramp/Highway/Intersection
  groups. **Show the user a UI mock before touching the frontend.**
- **E — Highway Detail/Summary groundwork** (NEW): reserve stable ids + stub modules + catalog
  entries flagged not-usable (mirrors the site's `cs-disabled`); the site ships these `cs-disabled`
  on the dev menu now (`highway_detail` / `highway_summary`), prod to follow.

User constraint: **the nested dropdown is dev-only today; prod must NOT break.** → every selector
path matches `data-value` first and falls back to exact text/`data-label`, so the flat prod menu
behaves exactly as before.

### Phase A — DONE + fully verified (2026-06-26)
- `ReportSpec.data_value` added (default None); set on all 8 export specs (ramp_summary→`Ramp_Summary`,
  ramp_detail→`Ramp_Detail`, highway_sequence, highway_log [+ _pdf reuse], intersection_summary,
  intersection_detail [+ _pdf reuse]).
- `report_nav._find_exact_option(page, label, data_value=None)`: data-value first → exact text/
  `data-label` fallback. New `_reveal_submenu_if_leaf` hovers the `cs-parent` to open the flyout for a
  `cs-leaf`. `select_report`/`preflight` thread `data_value`; call sites in exporter.py:360/417/701,
  exporter_parallel.py:159/307 pass `spec.data_value`. `cs-disabled` guard unchanged.
- Env-scan probe (`gui_worker._REPORT_OPTIONS_JS` + `check_one`): now probes by (label, data-value),
  matches by data-value first, weighs the parent flyout's disabled class → grouped reports read on the
  nested dev site, the Highway group reads greyed.
- Tests: new synthetic `build/fake_site/dropdown_nested.html`; browser-driven `test_nested_menu` +
  `test_env_scan_probe` in check_fake_site; `test_data_value_match` + `test_nested_disabled` in
  check_export_engine. RED confirmed (no `data_value` param) → GREEN. **Full CI blocking suite (77
  checks) PASS** (only the known untracked-planning misspelling hit remains). compare_core untouched;
  diff hygiene clean.
- NOT committed (commit only when asked; bundle ships as one v0.18.1).

### Phase B — DONE + fully verified (2026-06-26)
- Root cause confirmed: `_try_start_next_matrix_job` (gui_matrix.py) pops a job via `take_next()`
  (queue shrinks, gate claimed) then, on a **drop** (no-work or dispatch-exception), did
  `release()+emit_log+continue` with **no `_push_state()`**. The true backend state was correct,
  but the last frontend-facing push was `_end_task`'s — taken BEFORE the pop — so the drained job's
  chip lingered. ("Can't clear/cancel" was a consequence: `matrix_queue_remove/clear` found nothing
  matching the phantom in the real queue.)
- Fix: `_push_state()` after BOTH drop branches. The user-edit/stop methods already push on mutation.
- Test: `check_matrix_bridge` new "queue-phantom regression" — spies the **pushes** (not the final
  state, which the existing test already covers) and asserts the LAST pushed snapshot has the queue
  cleared. RED confirmed → GREEN. The #mock can't reproduce it (pure backend push-timing), so the
  push-spy test is the correct guard. Full suite (77) PASS.

### Extra fix — "Roadbed" → "Route Suffix" mislabel (user-reported, 2026-06-26)
- `compare_intersection_detail_tsn.py` derived `SHARED_HEADER[1]` by splitting an alpha letter (S/U)
  off the route (`_split_route`) and mislabeled it **"Roadbed"** — it's a route **suffix** (the
  printed report's "S" column). Renamed column + the `f=="Roadbed"` placement checks (atomic) +
  docstrings/Notes → **"Route Suffix"**. Propagates to the PDF-vs-TSN / PDF-vs-Excel variants
  (`replace(_id._SCHEMA, …)`). The legitimate Highway Log Left/Right **Roadbed** columns are
  untouched (`check_highway_log_roadbed` green). Updated `check_compare_intersection_detail_tsn`
  (`test_route_suffix_match`) + `check_tsn_normalizer._ID_HEADER`. **Label-only — data/diff-counts
  unchanged**, so regression-safe; a cached TSN library reads by position (no rebuild needed). Full
  suite (77) PASS.

### Phase C — DONE + fully verified (2026-06-26)
- `exporter._build_wait_condition(spec, route)` validates `spec.wait_js(route)` is a non-empty JS
  arrow string before interpolating it; a misauthored spec raises a clear PreflightError + logs
  `log.error` instead of reading as a cryptic Playwright eval error / full route timeout. (route is
  app-controlled — a config tripwire, not input sanitization.) `_attempt_route` uses it. New
  `check_export_engine.test_wait_condition_validation`. Roadmap §J2 carried-forward item now CLOSED
  in code. Full suite (77) PASS.

### Phase D — grouping implemented + verified (UI mock approved; short leaf labels chosen)
- `report_catalog`: `ExportEntry` gained `group` + `short_label` (defaults None); set on Ramp×2 +
  Intersection×3; flat for HL/HL-PDF/HSeq. New `export_display()` → `{key: (group, short_label)}`.
- `reports.EXPORT_DISPLAY` re-exports it; `gui_api.get_initial_state` adds `group`/`short` to each
  `init.reports` dict (lookup by key; no ripple to the `(label, fmt, spec)` unpackings).
- `ui/app.js`: new `fillReportList()` renders flat reports first, then each family under an
  `.option-group` header; grouped rows show `rep.short` (indented `.option-indent`); default tick
  preserved (first enabled = ramp_summary). Both the Export picker AND Export-Everything use it.
  `ui/app.css` `.option-group` + `.option-indent`. `ui/mock.js` REPORTS carry group/short.
- Flat order: user chose MATCH THE WEBSITE (Highway Log, its PDF, then Sequence). Implemented via a
  catalog `_PICKER_ORDER` tuple + `picker_order()` (import-asserted to cover every key); `gui_api`
  sorts the reports payload by it and sets `idx` = the DISPLAY position (no app code reads idx; only
  the parity check). Updated `check_intersection_gate` (verify identity by stable key, idx = 0..N-1)
  + `check_report_catalog`/mock to the display-position idx. UI `fillReportList` simplified to emit a
  header on group change (relies on the pre-sorted order). Default tick naturally moved to the first
  row (Highway Log).
- Verified live in #mock (Highway Log first, both pickers grouped, no console errors) + full suite
  (77) PASS. Phase D DONE.

### Phase E — DONE + fully verified (2026-06-26): Highway Detail/Summary groundwork (disabled)
- New reserved stub specs `export_highway_detail.py` / `export_highway_summary.py` — valid ReportSpec
  (label, subdir, `data_value` = the site id, placeholder wait_js/is_empty) but `save` RAISES
  (fail-loud if prematurely enabled); `__main__` refuses.
- `report_catalog`: imports the 2 stubs; appends 2 ExportEntry (group="Highway", short Detail/Summary,
  Excel placeholder) — stable-id append-only; `_PICKER_ORDER` appends them last (Highway group last).
- `reports.DISABLED_EXPORT_SUBDIRS = {highway_detail, highway_summary}` — the ONE gate greys them in
  the picker, drops them from enabled/library, and the start_* guards reject them server-side.
- `batch_manifest._V017_EXPORT_ORDER` appends them at 8/9 (keeps `== EXPORT_KEYS`; a v1 manifest could
  never carry those indices, and the loader rejects a disabled key anyway). `app.spec` APP_MODULES +2.
- They have NO consolidator / comparator / TSN entry, so they're absent from the matrices, Consolidate,
  and Compare (check_matrix_bridge still 8 rows — confirmed).
- Checks updated: `check_report_catalog` (_EXPORT baseline +2; `_mock_objs` now parses boolean fields;
  mock parity reads per-entry `disabled`); `check_stable_ids` (append-only 8/9); `check_intersection_gate`
  (gate premise flipped: holds the reserved Highway pair, N-2 enabled, the pair greyed); `app.spec`.
  `mock.js` REPORTS +2 disabled Highway (map default-false then per-entry override); picker disabled
  note → "not yet available".
- Verified live in #mock (Highway group greyed at the end, "not yet available") + full suite (77) PASS.

## ALL v0.18.1 IMPLEMENTATION PHASES COMPLETE (A–E + the Roadbed fix).

### RELEASE — DONE (v0.18.1 PUBLISHED 2026-06-27)
- Commit `e2bfade` (`feat: v0.18.1 …`, 38 product files, no planning) → tag `v0.18.1` → pushed (branch
  FF `a80c100..e2bfade`). All 3 CI runs green: `checks`@tag, `release`@tag (published 6 assets), `checks`@branch.
- Release: https://github.com/yunusshaikh7/TSMIS-Reports-Exporter/releases/tag/v0.18.1 — win64 / win64-with-browser /
  batch-source zips + `.sha256` each. **v0.18.0 was ALSO already released** (on origin @ a80c100; the "unpushed" handoff note was stale).
- REMAINING (deferred, user-gated): (1) **work-PC LIVE verification** — download v0.18.1, confirm Intersection
  export works on the nested dev menu + the queue clears (the two original field bugs). (2) **`main` reconcile**
  (origin/main ≈ v0.17.8, diverged) via `-s ours`/force, NOT a blind merge. (3) when the site enables Highway
  Detail/Summary: drop them from `DISABLED_EXPORT_SUBDIRS` + finalize the stub `save`/schema + add comparators.

### (historical) RELEASE prep notes — user authorized "Cut v0.18.1 now (full)"
- DONE: `version.py` → 0.18.1; `CHANGELOG.md` `## v0.18.1` (user-facing); docs — `comparison-engine.md`
  + `tsn-parsers.md` "Roadbed" → "Route Suffix" (the contradiction), `CLAUDE.md` (the data_value
  selection contract + the picker grouping + the disabled Highway groundwork at 8/9). Full suite (77)
  PASS; `gen_release_notes v0.18.1` extracts cleanly.
- NOTE: a stray `git add` had staged everything incl. `docs/planning/`; `git reset` cleaned it — index
  is empty, planning untracked. At commit, stage ONLY the v0.18.1 product files by explicit path.
- IN PROGRESS: both frozen self-tests (`build.ps1 -SelfTest` + `-SelfTest -BundleChromium`).
- PENDING: one focused commit ("…" short imperative) → tag `v0.18.1` → push branch + tag (release.yml
  builds 3 zips + .sha256). Branch is UNPUSHED at a80c100; pushing publishes the branch + the v0.18.1
  tag (v0.18.0 stays an unpushed anchor in history). `main` reconcile is separate/later.
- DEFERRED (additive docs, no contradiction — a quick follow-up): the fuller grouping / nested-dropdown
  / Highway groundwork write-ups in `docs/reports.md`, `docs/architecture.md`, `docs/roadmap.md`.
