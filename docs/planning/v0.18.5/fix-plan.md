# The audit fix program: v0.18.5 (all fixes) + v0.19.0 (all structure)

> **Execution status (2026-07-03): PART 1 (v0.18.5) CODE-COMPLETE.** All waves
> landed on `fix/v0.18.5-audit-polish` (~29 commits, suite green at 85 checks,
> incl. 6 new goldens). **D3 re-bless PASSED on the real statewide pair:**
> ~2.79M cells cell-for-cell IDENTICAL before(v0.18.4)/after, canary unchanged
> at **163,310 diff cells / 677 one-sided**; the F1 rollup rework cut the
> statewide compare **238s -> 168s (-30%)** at byte-identical output. gh-pages
> polish + fresh v0.18.5 screenshots committed on the local `gh-pages` branch
> (worktree). **HUMAN-GATED remainder:** merge -> tag `v0.18.5` -> push (branch,
> tag, gh-pages), watch release.yml's new offline-checks gate, then the work-PC
> ride-alongs (in-app update 0.18.4->0.18.5; operational sign-off with
> `--collect-evidence`; observe the twin-skip log line, the soft-busy message,
> and the TSN auto-rebuild announcement). Part 2 (v0.19.0 structure) starts on
> `refactor/v0.19.0-structure` off the tag.

**Source:** [`docs/planning/fable5-repo-improvement-audit.md`](../fable5-repo-improvement-audit.md)
(the 2026-07-01 audit; finding IDs refer to it). **Baseline:** `main` @ `0fa1cd5` (v0.18.4).
**Scope (revised 2026-07-03, second revision):** **EVERY audit finding gets addressed** — the bug
and polish fixes ship as **v0.18.5**; the structural findings (splits, dedup, registry, import
graph, verification DX) ship as **v0.19.0** (Part 2 below). No new features in either.

## Program rules (how "you can add a feature midway" is guaranteed)

- **Green checkpoints:** every wave ends with the full suite green (`build/run_checks.py`) and the
  branch in a releasable state. Work lands wave-by-wave; nothing stays half-refactored across a
  checkpoint. If a feature is needed mid-program, branch from the last checkpoint (or ship what's
  landed as a release) and rebase the remainder afterwards.
- **Extension paths get cleaner FIRST in Part 2:** the v0.19.0 waves are ordered so the
  report-family path (catalog → export spec → consolidator → vs-TSN comparator → matrix row) is
  consolidated before anything else — because the next likely feature is exactly a new report
  family.
- **The named future feature — Highway Detail / Highway Summary comparison** — slots in on the
  existing reserved-DISABLED groundwork (stable IDs 8/9, v0.18.1): activating it means filling the
  stub `ReportSpec`s (real `data_value`/`wait_js`/`save`), removing the two ids from
  `reports.DISABLED_EXPORT_SUBDIRS`, adding a consolidator + a vs-TSN comparator via the (soon
  shared) substrate, matrix/by-day wiring, and per-family golden checks — the
  [docs/reports.md](../../reports.md) "add a report" recipe. **After Part 2 Wave R this becomes
  mostly recipe-following**; it can also be done at ANY checkpoint before that, just against the
  older (duplicated) substrate. Nothing in this program moves stable IDs, batch-manifest order, or
  the catalog derivation — the groundwork stays valid throughout.
- Anything Part 2 discovers that would change comparison OUTPUT still routes through the Wave-D
  re-bless procedure; `compare_core` stays regression-locked at every step.

## Scope rules

1. **Every confirmed defect fix is in scope** — including fixes that change comparison output or
   add small fix-supporting surfaces (a warning line, an auto-rebuild). The line is drawn at NEW
   capabilities: no new reports, tabs, settings, or workflows.
2. **Comparison-output changes are allowed ONLY in Wave D**, land as one bundle, and are proven by
   the established v0.18.3 procedure: full offline suite + the `%TEMP%\tsmis_regress` harness + COM
   recalc against the real pairs in `Downloads\TSMIS\inputs`, then re-bless the statewide canary
   (current: 163,310) and update `docs/tsn-parsers.md`. Everything OUTSIDE Wave D stays
   byte-identical.
3. **Every fix lands with (or extends) an offline check.** This release exists because a shipped
   fix had no check executing it.
4. `compare_core.py` itself stays untouched (regression lock); Wave D works entirely in the
   normalizers/loaders/library around it.

## Versioning, branch, release mechanics

- **Version:** `0.18.5` (`version.py`), branch **`fix/v0.18.5-audit-polish`** off `main`. Commit
  style: short imperative, no AI attribution. Commit/push/tag only on explicit go.
- **CHANGELOG.md:** one `## v0.18.5 — <date>` section, user-facing prose (release notes derive
  from it).
- **Release:** full local suite green → merge → tag → `git push origin main refs/tags/v0.18.5`
  (tags push explicitly) → `release.yml` (now gated, see Wave 0) → 6 assets → gh-pages push.
- **Ride-alongs (no code):** the **work-PC operational sign-off** runs ON this build
  (`docs/work-pc-validation.md` §3, `--collect-evidence`), and the standing **updater field test**
  (v0.18.4 → v0.18.5 in-app). Both double as field proof for BUG-01/B8/D-wave fixes.
- **Before editing anything:** re-verify each item's cited lines (the audit is 2 days old; anchor
  on the quoted code, not line numbers).

---

## Wave 0 — the guardrail (FIRST; it protects everything after it)

### 0.1 `build/run_checks.py` (REL-01c / #60)
Stdlib runner: glob `build/check_*.{py,js}`, run each (`sys.executable`/`node`,
`PYTHONIOENCODING=utf-8`), stop-on-fail default (`--keep-going`, `-j N` optional), non-zero exit on
any failure, end summary. Mirrors checks.yml's env.
**Verify:** reproduces CI green locally; a sabotaged check → non-zero.
**Commit:** `add build/run_checks.py — run the full offline check suite locally`

### 0.2 `build/check_ci_manifest.py` (REL-01b / #47)
Glob checks on disk vs the names checks.yml runs (direct lines + the bash for-loop + node steps);
fail on any check never run (or listed-but-missing). Self-hosts: add itself to checks.yml.
**Verify:** green today (78/78 per audit); a fake `check_zz.py` → red.
**Commit:** `guard checks.yml completeness (check_ci_manifest)`

### 0.3 `release.yml` gate (BUG-06)
Add an `offline-checks` job (windows-latest, install requirements, `python build/run_checks.py`);
build job gets `needs: offline-checks`. checks.yml itself stays as-is this release.
**Verify:** on the branch via `workflow_dispatch`/throwaway tag with a broken check → release reds
at the gate. Never let a broken tag reach `main`.
**Commit:** `release.yml: require the offline check suite before building (v0.17.3 gate gap)`

---

## Wave A — trivial, behavior-preserving fixes

| # | Finding | Change | Check |
|---|---------|--------|-------|
| A1 | **BUG-01** (P1) | `matrix._comparison_row_count`: add `from openpyxl import load_workbook` as the function's first line (lazy-import idiom, keeps openpyxl off GUI startup). | New `check_formulas_twin_guard.py`: real 5-row workbook → returns 5; `_FORMULAS_TWIN_MAX_ROWS` monkeypatched to 3 → `_try_formulas` SKIPS (events message, no sibling); below limit → sibling written. Wire into checks.yml. |
| A2 | **BUG-03** (P1) | `consolidate_xlsx_base.py:116`: filter `p.name.startswith("~$")` (sibling idiom, cf. artifact_store.py:325). | `check_consolidate_outcome.py`: a `~$route.xlsx` stub in input → completion stays COMPLETE. |
| A3 | **SEC-01** (P2) | `.gitignore`: `/config.json.corrupt`, `/data/config.json.corrupt`, `/tsmis_evidence_*.zip`. | `git check-ignore` both names. |
| A4 | **BUG-09** (P2) | Wrap the PDF branch of both `_load_tsn`s (ramp_summary_tsn:102, intersection_summary_tsn:151) in `raise ValueError(f"Could not read {name}: {type(e).__name__}: {e}")` — mirrors their XLSX branch. | Both `check_compare_*_tsn.py`: corrupt .pdf → clean error result. |
| A5 | **BUG-15** (P3) | `day_matrix._folder_newest_mtime`: per-file try; unreadable entry contributes nothing. | `check_day_matrix.py` case. |
| A6 | **BUG-16** (P3) | `paths._writable`: probe name `f".write_test-{os.getpid()}"`. | Comment + `check_persistence.py` if reachable. |
| A7 | **BUG-17** (P3) | `consolidate_ramp_summary.py:510` `"BFBFBFBF"` → `"BFBFBF"`. | `check_ramp_summary_schema.py` stays green (locks structure, not colors — confirm). |
| A8 | **DED-03** (P3) | `_MTIME_TOL_S` single home in consolidation_meta; matrix imports it. | `check_matrix.py` + `check_p2_freshness.py` green. |
| A9 | **DED-02** (P3) | Delete unused `dest` (gui_matrix.py:548), identity ternary (gui_api.py:645), unused imports (`is_export_disabled` gui_api.py:68, `tempfile` updater.py:55); hoist the mid-file `_api_method` import (gui_api.py:132, stale cycle comment). KEEP the openpyxl probe (gui_worker.py:1697). | compileall + `check_gui_api_surface.py` + `check_updater.py`. |
| A10 | **SEC-03** (P3) | settings.py:303/:334 — log key + "(set)"/"(default)", not the value. | Grep; `check_persistence.py`. |
| A11 | **REL-03** (P3) | README badge → `img.shields.io/github/v/release/...` (never stale again). | Visual. |
| A12 | **REL-04** (P3) | build.ps1: assert `Python 3.11.x` before venv creation, else throw. | Run once / assert unit. |
| A13 | **REL-05** (P3) | backfill_release_notes.ps1: `$LASTEXITCODE` check after the python call. | Bogus-tag dry run throws. |
| A14 | **LOG-01 part** | `logging_setup._enable_faulthandler` swallow → house log line. | Covered by B3's tripwire. |

**Commits:** A1, A2 individually; A3–A14 may batch.

---

## Wave B — small behavior-fixing changes (own commit + check each)

### B1 — **BUG-05** (P1): Compare tab Browse… stomps the dropdown
`app.js`: selects' `onchange` clears `CMP_DIRS[side]`; `fillCompareDirSelect` restores `prev` over
`custom`. Verify in `#mock` (cache-bust recipe) — Browse → dropdown pick → forced re-render → pick
sticks; startCompare carries it. Node case if reachable from `check_compare_routing.js`.
**Commit:** `fix: Compare tab — a Browse-picked folder no longer overrides later dropdown picks`

### B2 — **FE-02** (P2): mock.js event order + tripwire
Reorder every mock task-end emission to production order (`run_ended → state → matrix_refresh`).
New `check_mock_event_order.js` (extract both orders by regex; fail on divergence) into checks.yml.
**Commit:** `fix: #mock emits task-end events in the production order (+ order tripwire)`

### B3 — **LOG-01** (P2): the silent-swallow sweep + tripwire + the reset-preview warning
All ~25 sites from the audit (gui_worker reset_targets/browser-closes/check_one, gui_api
autoscan/fast_workers/devtools, tsn_library probes, compare_intersection_detail_tsn onesided/
locations — add the module logger, exporter/auth_nav/report_nav/login cleanup sites — audit each;
documented last-resorts go on the allowlist). House idiom: `log.<level>("<step> skipped (%s: %s)",
type(e).__name__, first_line)`. Hoist `LoginWorker._safe_close` to a shared `_safe_close(browser)`.
**Included now (was deferred in v1):** the `reset_targets` failure also surfaces in the reset
PREVIEW — one warning line item ("⚠ the Export Everything store could not be inspected — its
reports may not be listed") appended to the targets list the existing dialog already renders. It is
part of the fix: without it the delete-preview silently lies.
New `check_silent_swallows.py` (AST tripwire + allowlist) into checks.yml.
**Commit:** `fix: log every swallowed exception; reset preview warns when the store can't be read`

### B4 — **EXP-02** (P2): export stubs must not sys.exit the GUI at import
Constraint (verified): exporter.py imports playwright at module level, so the stubs' guard is the
guard for the whole chain. In each of the ~12 stubs' `except ImportError:` block:
`if __name__ == "__main__": print(<existing message>); sys.exit(1)` / else `raise`. Console UX
byte-identical; the GUI (via report_catalog) now gets a raisable error its fatal box can SHOW.
New `check_export_stub_guard.py` (subprocess with playwright masked: importing report_catalog
raises ImportError not SystemExit; running a stub as `__main__` exits 1 with the message).
**Commit:** `fix: a missing Playwright no longer silently kills the GUI at import`

### B5 — **BUG-12** (P2): env-mode snapshot drops `completion`
`matrix.comparison_state`: read `completion` under the same `rec_trusted` gate (donor pattern:
`_cmp_state` :541) and return it; confirm `mxCellContent` renders `mx-partial` for env cells.
Extend `check_matrix.py` (+ `check_mx_partial_render.js` if reachable).
**Commit:** `fix: env-mode matrix cells surface the recorded PARTIAL completion on reuse`

### B6 — **BUG-08** (P2): empty TSN projection is an error
`tsn_library.build_normalized`: `rows = list(rows)`; empty → `status="error"` ("parsed but produced
0 rows — the layout may have changed"), nothing written, last-good preserved.
`check_tsn_normalizer.py` case.
**Commit:** `fix: an empty TSN projection is an error, not an empty "complete" library`

### B7 — **BUG-11** (P2): stale-response guard on matrix renderers
Render-sequence token in `renderMatrix`/`renderDayMatrix` (bail if a newer render started during
the await). Leave the double dispatch alone. Node interleaving case beside
`check_mx_partial_render.js`.
**Commit:** `fix: a slow matrix snapshot can no longer overwrite a newer one`

### B8 — **BUG-04** (P1): user task vs background env-check on the Edge profile
Now that polish is in scope, ship BOTH halves of the minimal-correct design (still NOT the task
gate — that would lock the UI ~60 s on every device-mode start):
(a) claim paths consult `_active_check` → soft error "Checking the sign-in status in the
background — try again in a few seconds."; (b) a `supersede` threading.Event the
ActiveEnvCheckWorker polls between its steps (navigate / preflight) — a rejected user click sets
it, the check aborts early (closes the browser, posts `active_env_done` with a superseded marker),
so the retry a few seconds later succeeds.
Extend `check_worker_lifecycle.py`: claim-during-check → soft error + supersede set + no worker;
check polls the event and ends early.
**Commit:** `fix: user actions no longer collide with the background sign-in check on the Edge profile`

---

## Wave D — comparison correctness: the re-bless pair (feature-adjacent bug fixes, IN scope)

> Ship as ONE bundle, late in the branch, so a single harness run + canary re-bless covers both.
> These are the only items allowed to change comparison output (scope rule 2). Their pairing is
> deliberate: **D2's auto-rebuild is what makes D1 safe to ship** — without it, every normalizer
> fix "looks unfixed" in the field until a manual Settings-Rebuild (the v0.17.6/v0.18.3 trap).

### D1 — **BUG-07** (P1 latent): eradicate the remaining `str(v or "")` falsy-zero sites
- **Sites (re-verify; from the audit + grep):** `compare_tsn_common.py:39` (`norm_pm` — feeds the
  Ramp Detail + Intersection Detail ALIGNMENT KEYS) and `:53`;
  `compare_intersection_detail_tsn.py:175` (`_norm_control_type` token), `:229`, `:555`;
  `compare_ramp_detail_tsn.py:77, 90, 105`. Replace with the v0.18.3 idiom
  `("" if v is None else str(v))`.
- **Risk note:** the `norm_pm`/key sites can shift row pairing when a source delivers numeric-0
  postmiles; that's the point. On today's real data the expectation is **zero diff-count change**
  (no current source delivers numeric-0 through these paths) — the harness run proves it either
  way; if counts move, investigate each moved cell before accepting a new canary.
- **Checks:** numeric-0 rows through every touched normalizer in the respective
  `check_compare_*_tsn.py` + `check_compare_tsn_common.py` (0 ≠ blank; '0'=='0.000' canonical).

### D2 — **BUG-02** (P1): TSN library normalization-version stamp + auto-rebuild
- **Design (from the audit, verifier-approved):**
  1. Each `tsn_load_*.py` exports a `NORMALIZATION_VERSION` int (start at 1; bump on any
     normalizer change — D1 bumps them all to 2 in this same release).
  2. `build_normalized`/`build_into` record it in the workbook's `consolidation_meta` sidecar
     (additive field — sidecar readers are already fail-safe).
  3. `tsn_library.status()` / `build_consolidated()` / `_resolve_source()` treat a missing or
     mismatched stamp as **stale** (fail-safe: absent ⇒ stale), alongside the existing mtime check.
  4. Stale + raw files present ⇒ **auto-rebuild from `raw/`** (the raw statewide files are already
     retained) before compare/matrix use — through the existing build path, transactional as today,
     announced in events + log ("TSN library rebuilt: normalization updated (v1 → v2)").
     Stale + NO raw ⇒ surface the existing "import first" guidance (never compare silently stale).
- **Checks:** new `build/check_tsn_freshness.py` — a prebuilt v1 library + a version-2 loader ⇒
  status stale + auto-rebuild fires + result carries v2; absent stamp ⇒ stale; matching ⇒ reused.
- **Field effect:** upgrading users' libraries rebuild themselves on first use — the v0.18.3
  "looks unfixed" trap is closed for this and every future normalizer fix.

### D3 — the re-bless procedure (gate for D1+D2, run once)
1. Full offline suite (`run_checks.py`) green.
2. `%TEMP%\tsmis_regress` harness + COM recalc against the real pairs in
   `C:\Users\Yunus\Downloads\TSMIS\inputs` (docs/verification-and-testing.md): compare workbooks
   diffed cell-for-cell vs v0.18.4 output; every difference must trace to D1's intent (expected:
   none on current data).
3. Rebuild the TSN library in-app (or let D2's auto-rebuild do it — that IS the field path; test
   both), re-run the statewide Intersection Detail comparison, record the canary
   (expected: **163,310 unchanged**; if changed, justify per cell then update
   `docs/tsn-parsers.md` + the Route-1 canary if touched).
4. Update docs: tsn-parsers.md (canary + normalization-version note), comparison-engine.md
   (stamp/auto-rebuild paragraph).

**Commits:** `fix: numeric 0 survives every vs-TSN normalizer (falsy-zero eradication)` then
`fix: TSN library auto-rebuilds when normalization changes (version stamp)` (or one combined
commit if the harness runs once — combined preferred, mirroring v0.18.3's single-commit style).

---

## Wave E — stability fixes (feature-adjacent, IN scope; each timeboxed + check-locked)

### E1 — **BUG-13** (P2): updater phase-2 hard-interrupt recovery
`updater.py`: write `UPDATE_DIR/swap.inprogress` (JSON: pieces + phase) before the phase-2 rename
loop; delete on success. `cleanup_leftovers` (:1095-1115): if the journal exists, **complete or
roll back** from the `.old`/`.new` pieces (renames only, same rules as the handled-failure path)
BEFORE the blanket delete; no journal ⇒ today's behavior.
Extend `check_updater.py`: simulated kill after k of n renames on a fake tree → next-launch
recovery yields a coherent tree (both directions), journal gone after.
**Timebox:** 1 day incl. tests; if the recovery matrix isn't provably clean, pull it (it guards a
seconds-wide window; correctness of the guard matters more than shipping it this week).
**Commit:** `fix: an interrupted update swap now recovers on next launch instead of deleting its rollback pieces`

### E2 — **BUG-10** (P2): cancel/skip/pause race on the task gate
Take the coordinator lock in the cancel/skip/pause endpoints; no-op when `self._task is None` or
the targeted kind doesn't match the running one (frontend already knows the kind it targets — pass
it; the strings exist in contract.js). Extend `check_worker_lifecycle.py` with the
end→cancel→start-next interleaving (cancel must NOT hit the next queued job).
**Commit:** `fix: cancel/skip/pause can no longer race a matrix-queue job transition`

### E3 — **BUG-14** (P2): multi-process log loss
Per-entry-point log filenames with the same rotation policy: `tsmis-gui.log` / `tsmis-cli.log` /
`tsmis-login.log` (logging_setup gains a `name=` param; each entry point passes its own).
`evidence.py` bundles the family glob (`tsmis*.log*`); docs mention the split. Old `tsmis.log`
left in place (picked up by the glob), not migrated.
Extend a check: two setup_logging calls with different names → distinct files; evidence manifest
includes both.
**Commit:** `fix: GUI and console runs no longer drop log records when open simultaneously`

---

## Wave F — performance + UX polish (no features; each independently droppable)

### F1 — **PRF-01** (P2): Report View rollup redundant work
Additive `extra_sheet_writer` ctx fields (pairing/union already computed by `run_compare` —
compare_core change is ADDITIVE-ONLY to the ctx dict, output untouched); hoist shared
Font/PatternFill objects to module constants in `compare_intersection_detail_tsn`; cache the two
side-workbook reads across flavors in one run.
**Gate:** byte-identical output on the real pair (rides D3's harness run — schedule F1 BEFORE D3
so one harness pass proves both), plus a wall-clock before/after note in the commit.
**Commit:** `perf: Intersection Detail Report View rollup stops recomputing what run_compare already knows`

### F2 — **FE-03** (P2): modal focus trap + dialog semantics
`ui-dom.js openModal/buildModal`: `role="dialog"`, `aria-modal="true"`, a ~15-line Tab/Shift-Tab
trap, focus restore on close. Esc handling already exists.
Verify in `#mock` (keyboard walk); extend `check_ui_boot.js` if it can assert attributes.
**Commit:** `fix: modals keep keyboard focus and announce as dialogs`

### F3 — **FE-04** (P2, stretch): route-picker + tab-bar keyboard access
`tabindex="0"`, `role`, Enter/Space handlers on picker cells; arrow-key pattern on the tab bars.
Medium; ship only if F2 lands cleanly and time remains — otherwise it heads the v0.18.6 list.

### F4 — **FE-08 part** (P3): debounce `renderPreflight`
Match the routes input's existing 200 ms debounce for the body-wide input/change listeners; fix the
matrix-mode hidden-check (:690). (The S-literal field declarations ride along — comment-only.)
**Commit:** `fix: preflight recompute is debounced and matrix-mode aware`

### F5 — **FE-06** (P3): dead CSS
Delete `.auth-status`, `.dm-tsn`, the redundant `.set-radios.hidden`. **Investigate `.mc-mode.on`
first** — the audit flags it as possibly a missing feature (the pills' active state never
renders); if it's meant to be wired, wiring it is a FIX (include); if abandoned, delete it.

### F6 — **SEC-04** (P3): ACL-harden the Edge sign-in profile
Apply the auth-file `icacls` treatment (auth_nav.py:76-137 pattern) to `EDGE_LOGIN_PROFILE_DIR`
creation in edge_device.py (:108, :250). Best-effort like the existing hardening; log on failure.
**Commit:** `fix: the Edge sign-in profile gets the same owner-only ACL as the saved login`

---

## Wave C — docs + gh-pages polish

| # | Item | Action |
|---|------|--------|
| C1 | **DOC-01** (P2) | Track `docs/planning/` (recommended; spot-check once that nothing quotes local-only data) — or gitignore it. Ends the permanent `??` noise. |
| C2 | **DOC-04** (P2) | frozen-gate.yml paragraph in docs/build-and-release.md. |
| C3 | **DOC-05** (P2) | CLAUDE.md repo-layout line: `matrix.py day_matrix.py tsn_library.py tsn_load_*.py summary_layout.py`. |
| C4 | **DOC-03** (P2) | verification-and-testing.md: "run everything: `python build/run_checks.py`" + fold the missing check families into the catalog (or replace the hand-list with the runner + a taxonomy table). |
| C5 | **WEB-02** (P3) | gh-pages: release tag via `textContent`/createElement, not innerHTML. |
| C6 | **WEB-01** (P2) | `tools/screenshots.py` regen → copy 3 files to gh-pages → push (also refreshes README screenshots on main). |
| C7 | **DOC-02/README** (P2) | README body refresh — feature/usage sections brought to v0.18.5 reality (matrices, TSN library, Everything tab, updater). Content polish, in scope. |
| C8 | **WEB-03/04** (P3) | Theme-button default glyph + aria state; `prefers-reduced-motion` reset. Riding C5/C6's gh-pages push. |
| C9 | **DOC-07** (P3) | gui.md gets the full cache-trap recipe (it owns the topic); fix the three stale internals anchors (symbol anchors, not line numbers). |
| C10 | **DOC-06** (P3) | Minimal `pyproject.toml` with the ruff ruleset (E9,F63,F7,F82 — F821 deferred until ARC-01 lands in v0.19) covering scripts/ + build/ + version.py; pin ruff/bandit/pip-audit versions in checks.yml. |
| C11 | **DOC-08** (P3) | 30-line CONTRIBUTING.md (setup, dev GUI, run_checks, regression-lock rule, local-only-data rule); README Contributing points at it. |
| C12 | CHANGELOG | The v0.18.5 section — lead with: comparisons self-heal on normalization updates (D2), numeric-0 fix (D1), the twin-skip restoration (A1), lock-file fix (A2), Compare-tab fix (B1), updater crash-recovery (E1), "every swallowed error now logs", release pipeline now gated. |

---

## Moved to Part 2 (v0.19.0) — nothing is dropped

ARC-01 · ARC-02/03 · ARC-04 · ARC-05 · DUP-01..04 · FE-01 · FE-05 · MOCK-01 · SEC-02 retirement
(v0.18.5 ships the stamping half — see B3a below) · SEC-05/06 · PRF-02 · TST-01 check 5 ·
checks.yml→runner consolidation. Full specs in **Part 2** at the end of this file.

### B3a (added) — SEC-02 first half: stamp legacy store dirs on sight
Wave B gains one small item so the SEC-02 deprecation window STARTS in v0.18.5: wherever
`reset_targets`/the batch writer recognizes a legacy `<src>-<env>`/`comparisons` dir by NAME,
call `owned_dir.mark_owned(child)` (best-effort, already never-raises) — so by v0.19.0 every
active install's store is stamped and Part 2 Wave T can retire the name fallback.
**Check:** extend `check_reset_safety.py`: a legacy-named dir gains the marker after one
reset-preview pass. **Commit:** `stamp legacy Export-Everything dirs with the ownership marker`

---

# PART 2 — v0.19.0: the structural cleanup (ALL remaining audit findings)

> Branch `refactor/v0.19.0-structure` off the v0.18.5 tag. Same program rules: every wave a green
> checkpoint; behavior-identical unless stated; `check_gui_api_surface`/`check_ui_contract`/the
> golden families lock each move. Estimated ~2 weeks focused.

## Wave R — the report-family path (FIRST: it's the feature-extension path)

| # | Finding | Work |
|---|---------|------|
| R1 | **DUP-01** (P2) | Migrate the 3 pre-P5b comparators (`compare_highway_log.py`, `compare_highway_log_pdf.py`, + the remaining legacy flavor) onto `compare_tsn_common.run_files_compare`; move `suggest_name` (6 copies) + the row-emptiness predicate (~11 copies) + the consolidated-loader skeleton (3 copies) into compare_tsn_common. Byte-identity via the per-family `check_compare_*` goldens. |
| R2 | **DUP-02 + CON-01** (P2) | Extract `scripts/pdf_table_lib.py` (char clusterer ×3, `_assign_columns` ×2, route-workbook writer, the ~150-line convert-loop driver ×2-3) parameterized like `tsn_library.build_normalized`; **reconcile the four divergent `_norm_route` copies deliberately** (any behavior choice documented; if output shifts → Wave-D re-bless procedure). Splits the oversized `parse_pdf`/`consolidate` functions as a side effect. Goldens: `check_tsmis_pdf_parse/reconcile`, `check_pdf_row_oracle`, `check_consolidate_*`. |
| R3 | readiness | Dry-run the "add a report" recipe against the new substrate on the RESERVED ids (8/9) WITHOUT enabling them: assert a stub comparator/consolidator can be registered end-to-end in a scratch check (`check_report_recipe.py`, new). This is the **feature-ready milestone** for Highway Detail/Summary. |

**Checkpoint R:** suite green; adding a report family is now catalog + spec + recipe.

## Wave S — the splits (mechanical, surface-locked)

| # | Finding | Work |
|---|---------|------|
| S1 | **ARC-02** (P2) | `GuiSettingsMixin` (gui_api ~:2098-2553), `GuiUpdateMixin` (~:1203-…), `GuiCompareMixin` out of gui_api.py (target <800 each, `GuiApi` = composition + task plumbing). Verbatim moves; `check_gui_api_surface.py` locks the endpoint set. |
| S2 | **ARC-02** (P2) | gui_worker.py → per-worker modules (`gui_worker_export/env/login/batch.py`) with gui_worker.py as the re-export shim (the common.py precedent); DED-04 magic numbers become named constants during the move. |
| S3 | **DUP-03** (P2) | The `@_task_endpoint(kind)` decorator in gui_endpoint.py absorbing the 11 claim-gate blocks + the 8 dialog-unwrap idioms; B8's exclusion + E2's kind-check live INSIDE it (one enforcement point). |
| S4 | **ARC-03** (P2) | matrix.py: one `_staleness()` shared by `comparison_state`/`_cmp_state`, then split `matrix_state.py` / `matrix_build.py` with matrix.py as facade (<800 each). `check_matrix*`/`check_day_matrix`/`check_p2_freshness` lock it. |
| S5 | **FE-01 + DUP-04** (P2) | app.js → `ui-compare.js` + `ui-export.js` + `ui-batch.js` (established ui-*.js pattern; load order in index.html); `bindEvents` → per-tab binders; one `syncRunButtons(prefix)`; one parameterized progress renderer; the five lock-ID arrays → `data-lock-when-busy` attribute sweep. Verify per move in `#mock` + `check_ui_boot.js`/`check_mx_partial_render.js`. |

**Checkpoint S:** every file under the 800-line standard except compare_core (see Wave V).

## Wave T — state/config/platform coherence

| # | Finding | Work |
|---|---------|------|
| T1 | **ARC-05** (P2) | settings.py key registry (`name → default, validate, redact`) + generic `get_extra`/`set_extra`; the 17 hand-rolled pairs become one-liners; SEC-03's redaction becomes a flag. `check_persistence.py` extended. |
| T2 | **ARC-01** (P2) | Import-graph untangling: inventory the 156 function-level imports; extract the shared bits breaking the matrix↔reports↔tsn_library↔paths cycles; keep heavy-dep laziness via explicit `_lazy_*()` helpers; extend `check_import_direction.py` to the GUI/matrix layer; **then enable ruff F821** in checks.yml + pyproject (makes the BUG-01 class statically impossible). |
| T3 | **SEC-02** (P3) | Retire the legacy name fallback in `reset_targets` (stamping shipped in v0.18.5/B3a); `_tsn_input` deletion requires the marker too. `check_reset_safety.py` flips its expectation. |
| T4 | **SEC-05/06** (P3) | Re-verify the staged digest inside `perform_swap` pre-phase-1; `settings.set_batch_dest` validates existence/writability + rejects UNC/device paths. |
| T5 | **PRF-02** (P3) | Move fs reads out of `_state_snapshot`'s lock; cache the Chromium size (invalidate on download/delete). |

## Wave U — verification & DX consolidation

| # | Finding | Work |
|---|---------|------|
| U1 | REL-01 final | checks.yml collapses to `python build/run_checks.py -j 4` (+ the advisory lint steps) — the list lives ONLY in the glob; `check_ci_manifest.py` reduces to asserting checks.yml calls the runner. |
| U2 | **TST-01 #5** | `check_gui_endpoint.py` — direct tests of the `_api_method`/`_task_endpoint` envelope (error wrapping, emit fallback, gate behavior). |
| U3 | **MOCK-01** (P3) | Mock updater phase sequence (available→downloading→staged) behind a `#mock` zap; decide `set_batch_dest` (delete the dead endpoint + fixture, or mark API-for-tests). |
| U4 | **TST-01 DX** | `build/_checklib.py` (path setup, fail/summary, FakeEvents, temp-dir ctx) — used by NEW checks; old ones migrate opportunistically. |
| U5 | **DOC-06/07/08 leftovers** | Whatever Wave C didn't land: pyproject F821 flip (after T2), internals symbol-anchors, CONTRIBUTING refinements. |

## Wave V — compare_core internal quality (LAST; behind the harness)

| # | Finding | Work |
|---|---------|------|
| V1 | **ARC-04** (P3) | Extract the pure `cell_equal(schema, col, a, b)` used by all three triplicated sites (`_row_diff_count`, `count_diffs`, `_field_value`); prove byte-identity on the locked pairs (`%TEMP%\tsmis_regress` + COM recalc + canaries). Only worth doing while the harness is already warm from any Wave-D-class change; otherwise it waits for the next compare_core-touching need. |

**Part 2 drop-order if squeezed:** V1 → U3/U4 → T4/T5 → S5 (frontend split) — everything else is
load-bearing for the feature path or the standards.

---

## Order of work & release-day checklist

1. Branch `fix/v0.18.5-audit-polish`; **Wave 0**; from then on `run_checks.py` before every push.
2. **Wave A** (A1, A2 first), then **Wave B** (B1…B7, B8 last).
3. **Wave E** (E1 timeboxed 1 day, E2, E3) and **F1/F2/F4/F5/F6** (F3 stretch).
4. **Wave D**: D1+D2 code + checks → **D3 re-bless** (one harness run also gates F1's
   byte-identity). Nothing merges past this point without D3 green.
5. **Wave C** docs on the branch; C5/C6/C8 prepared on a gh-pages checkout (push after the tag).
6. `version.py` → 0.18.5; CHANGELOG (C12).
7. **Full gate CI-style:** `python build/run_checks.py` (all 80+ checks incl. the ~7 new ones) +
   compileall + misspelling guard.
8. Frozen sanity: `build\build.ps1 -SelfTest` locally or `frozen-gate.yml` workflow_dispatch —
   REQUIRED this release (matrix/gui/updater/exporter-adjacent files all changed).
9. Merge to `main` (on explicit go), tag `v0.18.5`, push branch + tag explicitly. Watch
   release.yml: offline-checks gate → 3 variants → 6 assets + checksums.
10. Push gh-pages; verify the live page + new screenshots.
11. **Work-PC field pass:** in-app update 0.18.4→0.18.5 (also field-tests E1's journal path
    passively); operational sign-off session with `--collect-evidence`; observe: (a) bulk
    Intersection Detail logs "Skipping the live-formulas copy…" (A1), (b) Export during the startup
    check → soft-busy message, retry succeeds (B8), (c) first vs-TSN compare after update logs the
    auto-rebuild announcement (D2).
12. Bookkeeping: docs/roadmap + docs/history one-liners; canary + normalization-version recorded in
    tsn-parsers.md (D3); memory note; the operational sign-off milestone closes with this release.

## Risk register

| Risk | Mitigation |
|---|---|
| Stale audit line numbers | Anchor on quoted code before every edit |
| D1 shifts row pairing on real data | Expected zero change on current data; D3's cell-for-cell diff is the arbiter — investigate every moved cell before accepting a new canary |
| D2's auto-rebuild fires unexpectedly in the field | It announces itself (events + log), is transactional (last-good kept), and only triggers on stamp mismatch/absence — first post-update use rebuilds once, by design |
| E1 recovery logic wrong in an edge | Timeboxed + kill-matrix check on fake trees; pull if not provably clean — the journal must never make things worse than today |
| B3's sweep changes control flow | Logging-only rule (never widen/narrow an except); AST tripwire + allowlist |
| B8 supersede introduces a new race | The event only ever SHORTENS the check; claim rejection is stateless; lifecycle check covers claim-during-check both ways |
| Release balloons / stalls | Drop order if time-boxed out: F3 → E1 → F6 → C8-C11 → E3. D-wave and Waves 0/A/B never drop — they're the release's reason to exist |
| CI edits break workflows | 0.3 verified on-branch before the real tag |

**Estimated effort:** Wave 0+A ~1 day · B ~1 day · E ~1.5 days · F ~0.5 day · D (code+re-bless)
~1 day · C + release + field pass ~1 day. **Total ≈ 5–6 focused days.**
