# v0.18.0 — Integration & completion pass (close-out) — Claude report

**Scope:** verification + release preparation of the committed v0.18.0 branch, per
`05-claude-final-plan.md` §K (offline DoD) / §L (rollback) / §M (work-PC) / §N (exclusions). **NOT** an
implementation phase: no new architectural/behavioral/security/persistence/packaging design change was
introduced. **HEAD** `375b48c` (P11, the last phase); **branch point** `d2ee353` (`v0.17.1`);
`origin/main` `068b697` (`v0.17.8`).

**Uncommitted close-out PRODUCT changes:** **NONE.** Version, CHANGELOG, and the canonical docs were
already committed in their phases (P11 = `375b48c`). No substantive product-code work was discovered;
no "small correction" was required. The only close-out artifacts are this report + the
`00-coordination.md` status flip — both in the **untracked** `docs/planning/` workspace.

---

## 1. Full regression / test / lint / contract / compilation — **GREEN**
- **Byte-compile:** `compileall scripts/` OK (HEAD `375b48c`).
- **Python golden suite:** **74 / 75 pass.** The single "fail" is `build/check_no_misspelling.py`,
  which fails **only** on the known **untracked** `docs/planning/v0.18.0/phases/P10-codex-review.md:177`
  (an `rg "<typo>"` command string in a planning artifact). It walks the working tree; CI runs the
  **committed** tree, where `docs/planning/` does not exist → green. Tracked content is
  transposition-clean (a tracked `git grep` finds only the guard's own self-documenting docstring).
- **Node golden suite:** **3 / 3 pass** (`check_compare_routing.js`, `check_mx_partial_render.js`,
  `check_ui_boot.js`).
- The suite includes the CT contract tests, the outcome/transaction checks
  (`check_batch_outcome`/`check_consolidate_outcome`/`check_tsn_outcome`/`check_read_counts_layout`/
  `check_mx_partial_render.js`), every vs-TSN + cross-env canary
  (`check_compare_*`, incl. `check_compare_intersection_detail_tsn` / `_summary_tsn`), the stable-ID +
  manifest migration (`check_stable_ids`), packaging reachability (`check_app_modules`), import
  direction (`check_import_direction`), worker lifecycle (`check_worker_lifecycle`), the report-catalog
  derivation (`check_report_catalog`), and the source-ZIP smoke (`check_source_zip_smoke`) — all green.
- **Lint:** the repo has no separate linter; the `check_*` suite + byte-compile are the gate. The
  product-name guard (`check_no_misspelling`) is the lint-equivalent and is clean on tracked content.

## 2. Frozen / package verification (the plan's PA gate) — **GREEN**
- **win64 (default) — `build.ps1 -SelfTest`: PASSED.** Hash-pinned venv install (`--require-hashes`) +
  `check_build_env` parity → PyInstaller windowed build → prune + DLP guard → ran the **EXACT shipped
  `TSMIS Exporter.exe --self-test`** over the pruned bundle. Self-test output: `frozen=True`,
  openpyxl 3.1.5 / pdfplumber 0.11.9, chromium `page.pdf()` (34772 bytes) + download OK, pdfplumber
  text/words/tables OK, openpyxl round-trip OK, cryptography loaded, dynamic `matrix`/`day_matrix`/
  `report_library` import OK, **GUI bridge OK reporting 8 reports / 252 routes**, WebView window + JS
  bridge OK → **"SMOKE OK — every app-required code path works."** Built `dist\TSMIS Exporter` (150 MB).
- **win64-with-browser — `build.ps1 -SelfTest -BundleChromium`: PASSED.** Same windowed self-test over
  the pruned bundle with Playwright's Chromium bundled — `frozen=True`, every code path OK, GUI bridge
  reporting **8 reports / 252 routes**, "SMOKE OK." Built `dist\TSMIS Exporter` (524 MB onefolder).
- **Source ZIP:** `check_source_zip_smoke` (in the offline suite) — PASS. (The release-time `git archive`
  of the source ZIP + both frozen variants are also gated fail-not-skip in `release.yml`.)
- **Changelog/version prep:** `gen_release_notes.py v0.18.0` extracts the `## v0.18.0` CHANGELOG section
  cleanly (the release-body source), confirming `version.py` ↔ CHANGELOG parity for a future tag.

## 3. Before / after measurements (`d2ee353` v0.17.1 → `375b48c` v0.18.0)
| Metric | Before (v0.17.1) | After (v0.18.0) | Note |
|---|---|---|---|
| `version.py` | 0.17.1 | **0.18.0** | P11 |
| `scripts/*.py` modules | 53 | **82** | engine leaf split (P8a/b) + outcome/contract modules (P1/P7a) + the 4 Int-Detail-PDF modules (P14) + evidence/self-test/oracle (P13/PA/P12) |
| Python golden checks | 44 | **75** | +31 (every new contract/behavior RED-proven) |
| Node golden checks | 0 | **3** | renderer/boot/compare-routing guards |
| Export reports | 7 | **8** | +`intersection_detail_pdf` (CR-002) |
| Matrix rows (both matrices) | 7 | **8** | +Intersection Detail (PDF) |
| Compare ops (catalog) | — | **18** | EXPORT 8 / CONSOLIDATE 9 / COMPARE 18 |
| `compare_core.py` | baseline | **0-diff vs branch point** | regression lock held |
| Locked canaries | Route-1 HL **969** diff cells | **969** (unchanged) + Int-Detail vs-TSN Excel **163,353** / PDF **163,361** + Int-Summary **66 cats / 58·8·0** | the Int-Detail statewide pair is real-data → confirmed in v0.18.1 (RM04); offline behavior fixtures locked |
| Full branch diff | — | **148 files, +22,946 / −8,589, 25 commits** | |

## 4. Migration & compatibility reconciliation — **GREEN** (§G/§L)
- **Manifest v1/v2:** `batch_manifest._V017_EXPORT_ORDER` is **append-only** — the 7 original export keys
  keep indices 0–6; `intersection_detail_pdf` is index 7 (CR-002-RM4). v1 (integer-index) manifests stay
  forward-readable; unknown/dup/disabled/removed keys are **rejected (not silently dropped)**. Locked by
  `check_stable_ids` (incl. `test_v017_append_only_compat`).
- **Cache envelope + consolidation sidecars:** `cache_envelope` versions the matrix/by-day caches
  (older code reads a bumped envelope as "unknown → rebuild," never corrupt); `consolidation_meta`
  sidecars degrade fail-safe (corrupt/locked/missing → conservative `partial`). Both outlive a code
  revert by design (§L).
- **No renames** (§N): report subdirs, output filenames, `tsn_library` layout, `tsn_load_*` module
  names, and settings keys are unchanged/additive; `config.json` is backward-readable (unknown keys
  round-trip; corrupt moved aside). Confirmed: every prior layout still resolves.

## 5. Temporary compatibility layers scheduled for removal — **CONFIRMED GONE**
The refactor's shims are **permanent back-compat by design** (S04 / R1-R08 / R1-R04) — none were
scheduled for removal. The items the plan said to **drop/delete** are verified absent at HEAD:
- `_safe_join` → **0** occurrences (R1-N02). `full_snapshot()` → **0** (R1-N02).
- `compare_core.context_fill` → **0** (the v0.17.8 opt-in was deliberately **not** ported — CR-002-RM3).
- `day_matrix.TSN_SUBDIR` (the Highway-Log-only constant) → **deleted**; the only two matches are
  removal-confirming **comments** ("the old … `TSN_SUBDIR` constant is gone").
- **Kept on purpose** (NOT scheduled for removal): the 4 `tsn_load_*` thin shims (S04), `common.py`'s
  re-export shim over the engine leaves (the engine architecture), and the manifest-v1 loader.

## 6. Final canonical documentation — **GREEN**
P11 reconciled the entire `docs/` library + `CLAUDE.md` + `README.md` + `CHANGELOG.md` to HEAD (committed
`375b48c`): the registry tables, the outcome/transaction/catalog contracts, the GUI split, the v0.17.8
Int-Detail/Summary behavior, the updater hardening, the Int-Detail (PDF) report, and the two-tier
framing. All relative doc links resolve. **No further doc change was required during close-out** (DoD
"docs match HEAD" satisfied by P11).

## 7. Roadmap & audit reconciliation — **GREEN**
P11 wrote the **§J2 audit dispositions** into `docs/roadmap.md` (every still-open Phase-3 finding marked
Resolved / v0.18.1-evidence-driven / hard-deferred), recorded the **now-implemented M03
destination-ownership marker** (P12), and the **hard-deferrals** (DPAPI/O2, cert/A03, `min-cost-pairs`).
The honest **P11-discovered** discrepancy is recorded there too: `wait-js-fstring-interpolation-unvalidated`
is **not** closed in code at HEAD (the §J2 "Resolved in P8b" claim is inaccurate) → carried to v0.18.1,
NOT silently implemented.

## 8. v0.18.0 changelog & version preparation — **GREEN**
`version.py = 0.18.0` (committed `375b48c`); `CHANGELOG.md` carries the user-facing `## v0.18.0` section;
`gen_release_notes.py v0.18.0` extracts it. No `v0.18.0` tag/push (excluded — §N).

## 9. Final branch-diff inspection — **CLEAN**
`git diff origin/main..HEAD` = 148 files, +22,946/−8,589 (25 commits). Suspicious-path scan
(`tsmis_auth.json` / `output/` / `dist/` / `.venv` / `.pyc` / `pyi-work` / secrets) → **none**. The
frozen build produced `dist/` + `build/pyi-work/` locally; both are **gitignored** — post-build
`git status` shows only the untracked `docs/planning/`.

## 10. Planning files not staged — **CONFIRMED**
`git status` shows `docs/planning/` as **untracked** (`??`); `git diff --cached` is empty. The planning
workspace (this report included) is never staged/committed.

---

## §K offline-DoD → evidence map
| DoD item | Evidence |
|---|---|
| Correctness: CT green; no partial reports "complete"; matrix aggregate counts | full suite 74/75 (the 1 = untracked-planning misspelling) incl. `check_batch_outcome`/`check_consolidate_outcome`/`check_tsn_outcome`/`check_mx_partial_render.js`; frozen self-test reports 8 reports |
| Contracts: outcome + transactional + cache envelope; `report_catalog` SoT; `contract.py` enums; `task_coordinator` owns state; `compare_core` unmodified | modules present (`outcome`/`artifact_store`/`cache_envelope`/`consolidation_meta`/`contract`/`task_coordinator` 7/7); `gui_api`→TaskCoordinator (4 refs); **`compare_core` 0-diff vs `d2ee353`** |
| Structure: `common.py` shim; `gui_api` delegates; `#mock` separate; shared substrate; `gui_worker` not force-split | `common.py` is a shim over the leaves; `mock.js` + `ui-*.js`/`contract.js` (4/4); `compare_tsn_common` substrate; `gui_worker` intact |
| Packaging/CI: exact windowed exe + source ZIP gates; reachability/import-direction/lifecycle; reproducible hash-pinned; §J updater | `build.ps1 -SelfTest` PASS (win64, 150 MB) **and** `-SelfTest -BundleChromium` PASS (with-browser, 524 MB); `check_app_modules`/`check_import_direction`/`check_worker_lifecycle`/`check_source_zip_smoke`/`check_build_env` green; `release.yml` `.sha256` enforcement |
| Persisted data: prior layouts work; versioned + forward-migrating | §4 above; `check_stable_ids` append-only; `cache_envelope`/`consolidation_meta` fail-safe |
| Docs: canonical docs match HEAD; every audit item dispositioned | P11 (`375b48c`); roadmap §J2 |
| CR-001: P5b/P7b/P8c code/P9b/P12/expanded P10 green offline | all committed; full suite green |
| CR-002: P14+P15 at HL-PDF parity + v0.17.8 canaries; `compare_core` unmodified; keys 0–6 frozen | `check_report_catalog`/`check_stable_ids`/`check_compare_intersection_detail_tsn` green; `context_fill`=0 |

## Exclusions correctly deferred to v0.18.1 (§K2) / hard-deferred (RM06)
Work-PC field acceptance (P8c live paths, P1/P2/P3/P10/PA live, Int-Detail (PDF) live reconciliation, the
real-PDF evidence-driven parser fixes — `docs/work-pc-validation.md` §3); DPAPI/O2; runtime
signature/cert (A03); `compare_core` `min-cost-pairs`. **No push/tag/release** performed (§N).

## Substantive product-code work discovered during close-out
**None.** The branch is offline-complete; the only owed work is the v0.18.1 field gate (above), which is
a separate release, not a v0.18.0 phase. No additional implementation phase is proposed; the workflow is
**not** blocked.
