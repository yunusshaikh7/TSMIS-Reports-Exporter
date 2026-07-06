# PA — Exact-artifact packaging safety gate (early) — Claude report

## 1. Phase ID and name
**PA** — Exact-artifact packaging safety gate (early) `[blocking; precedes broad extraction]`

## 2. Baseline commit
`4bbee65` (HEAD of `refactor/v0.18.0-structural-overhaul` after P0's three commits).
Baseline state: **48/48** golden checks green, byte-compile green, working tree clean
apart from the untracked `docs/planning/` workspace.

## 3. Changes made
PA proves the **exact shipped exe boots/imports/runs every code path before any module/UI
split** (R1-S02/B04/T06/M02), and closes the two packaging findings F6 + F10. Five threads:

1. **Real-exe self-test path (R1-B04/D11).** Added `--self-test` to the real `gui_main`
   entry. Before any webview is created it runs the shared comprehensive self-test and exits
   with that code. The comprehensive body was **extracted** from `build/full_smoke.py` into a
   new shipped module `scripts/self_test.py` (`run(emit)`), so `gui_main --self-test` and the
   dev `full_smoke.py` run the **identical** exercise (DRY). Previously `-SelfTest` built a
   *separate console exe* (`full_smoke.py` entry, `console=1`, name "TSMIS SelfTest") — a
   different artifact than what ships; now the **windowed** `TSMIS Exporter.exe` self-tests
   itself.
2. **Reachability + completeness check (F6).** New `build/check_app_modules.py`: discovers the
   flat `scripts/*.py` inventory itself and asserts `APP_MODULES` (parsed from `app.spec` via
   AST) is the complete, duplicate-free, locatable inventory. It reproduced F6 (`matrix`,
   `day_matrix`, `report_library` missing) red, then went green after the spec fix. `app.spec`
   now declares those three **plus** `self_test`, and filters the UI `datas` to a web-asset
   extension allowlist (guards a stray file from riding into the bundle).
3. **Corrected build ordering (F10).** `build.ps1` now copies the user-facing readmes
   (`Start Here.txt`, `IT-README.txt`) **before** the prune+DLP scan (they were copied after,
   escaping the content guard — F10), and `-SelfTest` is pivoted to run the **exact** windowed
   exe's `--self-test` *after copy + prune* via `Start-Process -Wait -PassThru` (a windowed exe
   has no console; the exit code is the gate, diagnostics go to `TSMIS_SELFTEST_OUT` + the log).
4. **Source-ZIP console smoke (R1-M02).** New `build/check_source_zip_smoke.py`: offline proof
   that the `.bat`/console flow imports and that the registry-driven menu→module dispatch + a
   consolidation selection resolve, with no browser/auth/network/`input()`.
5. **CI wiring.** `checks.yml` gains a blocking "Packaging + console-flow checks" step (the two
   new offline checks). New `frozen-gate.yml` runs the heavy frozen exact-exe gate (both
   windowed variants) + the source smoke on a **label/nightly/dispatch** trigger. `release.yml`
   is restructured so the **gated `-SelfTest` build is the shipped artifact** (no separate
   un-gated rebuild) and the batch/source zip is gated by the console smoke.

## 4. Files affected
**Product / build (modified):**
- `scripts/gui_main.py` — `_run_self_test()` + the `--self-test` branch (pre-webview).
- `build/app.spec` — `APP_MODULES` += `matrix`, `day_matrix`, `report_library`, `self_test`;
  UI `datas` extension allowlist.
- `build/build.ps1` — always build the windowed app; docs-before-prune (F10); `-SelfTest`
  gates the exact exe via `Start-Process`; `-Sign` guard widened.
- `build/full_smoke.py` — reduced to a thin venv-tool wrapper delegating to `self_test.run`.
- `.github/workflows/checks.yml` — +2 blocking offline checks.
- `.github/workflows/release.yml` — ship the gated exact artifact; source-zip smoke gate.

**New:**
- `scripts/self_test.py` — shared comprehensive self-test body (`run(emit)`).
- `build/check_app_modules.py` — APP_MODULES completeness/reachability guard (F6 tripwire).
- `build/check_source_zip_smoke.py` — offline console menu→module dispatch smoke.
- `.github/workflows/frozen-gate.yml` — label/nightly frozen exact-artifact gate.

No `compare_core`, `updater` (TLS/swap), auth, or core-engine change.

## 5. Architectural decisions
- **D24 — extract the comprehensive self-test body to a shipped `scripts/self_test.py`.** The
  PA Protected contract is "the `excludes`/prune behavior proven by `-SelfTest` (**never
  weaken**)". That proof is `full_smoke`'s full runtime exercise (browser+pdf+download,
  pdfplumber, openpyxl, GUI bridge, hidden WebView). To run it on the **exact shipped windowed
  exe** (R1-B04), the body must be importable inside that bundle — hence a shipped module both
  the exe entry and the venv tool call. This is the mechanism that makes "the exact exe runs
  the same self-test `full_smoke` performs" literally true; it is not scope expansion.
- **Independent oracle (R1-B05/D02/D05).** `check_app_modules.py` derives the expected set from
  the real `scripts/` glob, **not** from the spec it validates; the frozen `--self-test` is an
  independent runtime second proof. The reachability/packaging oracle and any report-metadata
  catalog (P4) stay separate.
- **Windowed-exe diagnosability.** The gate's contract is the **exit code** (fail-not-skip on
  import/asset/registry/runtime; only the hidden-window probe may skip). Because a windowed exe
  has no stdout, output is mirrored to the log and an optional `TSMIS_SELFTEST_OUT` file that
  `build.ps1` reads back — verified working (the file was written correctly in the dev run).
- **`self_test` import stays cheap.** Heavy third-party imports live **inside** `run()`, so
  importing the module (reachability check, normal startup, packaging) pulls no
  playwright/openpyxl/pdfplumber/webview (verified: "heavy modules loaded by import self_test:
  none").
- **Frozen gate off the hot path.** A full PyInstaller build is too slow for every push, so the
  frozen exact-exe gate runs nightly / on-demand / on a `frozen-gate` PR label
  (`frozen-gate.yml`) and at release; the fast static+regression suite stays in `checks.yml`
  (no trigger change to the required check — respects R1-A05).

## 6. Compatibility and migration handling
- **No persisted-data, output, filename, settings, manifest, or registry change.** PA is
  packaging/CI + an inert new CLI flag. Migration: **none** (matches the plan).
- `--self-test` is inert for normal launches (only branches on the explicit flag), so the
  windowed app's behavior is unchanged.
- `full_smoke.py`'s public entry (`python build/full_smoke.py`, exit 0/nonzero) is preserved;
  only its body moved. Its docstring use #1 (prove PIL/pypdfium2 stay out) still holds — it
  prints the same `optional libs loaded` / `NOTE` lines.
- The UI `datas` filter is **behavior-neutral today** (the folder is exactly
  `index.html`+`app.css`+`app.js`, all allowlisted) and forward-hardening (P9's `mock.js` is a
  `.js`, also allowlisted).
- `build.ps1 -SelfTest` changes meaning (gate the exact exe vs build a separate console exe);
  `release.yml` updated in lockstep so the gated build is the shipped one. The `-BundleChromium`
  / `-Sign` semantics are preserved.

## 7. Tests and commands run
All via `build/.venv/Scripts/python.exe` (the suite's runner), offline, no live TSMIS / auth
file / network:
- **Characterization (red→green) for F6:** `check_app_modules.py` against the unfixed
  `app.spec` → **FAIL** (`MISSING: day_matrix, matrix, report_library`); after the spec fix →
  **PASS**. Its 4 diagnosis self-tests prove the guard catches missing/stray/duplicate.
- **`check_source_zip_smoke.py`** → 10/10 PASS (menu→module dispatch, consolidation selection,
  compare resolution).
- **Real-exe gate logic:** `python scripts/gui_main.py --self-test` (dev) → **EXIT 0**; full
  exercise ran (browser PDF 34 769 bytes + download, pdfplumber, openpyxl round-trip, the F6
  trio imported, GUI bridge 7 reports/252 routes, hidden WebView2 + JS bridge), and the
  `TSMIS_SELFTEST_OUT` file was written.
- **Venv tool post-refactor:** `python build/full_smoke.py` → **EXIT 0** (same body via
  delegation; `full_smoke.run is self_test.run`).
- **Full regression suite:** `for f in build/check_*.py` → **50/50 PASS** (48 baseline + the 2
  new). `check_no_misspelling` PASS; `check_import_direction` PASS (no new module-level cycle).
- **Byte-compile:** `compileall scripts build version.py` → OK.
- **`build.ps1`** PowerShell tokenizer parse → OK. **All 3 workflows** valid YAML
  (`yaml.safe_load`). Readmes scanned clean of card/SSN/PEM/AWS patterns (so the F10 reorder
  can't break a build).
- **Diff hygiene:** `git diff --check 4bbee65` clean; change set is exactly the intended files.

## 8. Results
Every offline-verifiable item is **green**: F6 reproduced then closed; the exact-exe self-test
runs end-to-end (dev) returning 0; the source-zip console dispatch resolves; 50/50 suite +
byte-compile + script parse + YAML all pass. The app remains runnable (the `--self-test` flag
is additive/inert for normal launches; the GUI path is untouched).

## 9. Before/after measurements
| Metric | Before (`4bbee65`) | After |
|---|---|---|
| `APP_MODULES` entries | 51 (50 scripts + `version`; **3 flat modules undeclared**) | 55 (54 scripts + `version`; **complete**) |
| Golden check suite | 48 | 50 (+`check_app_modules`, +`check_source_zip_smoke`) |
| `-SelfTest` gate target | a **separate** console exe (`full_smoke` entry, `console=1`, "TSMIS SelfTest") | the **exact** shipped windowed exe (`TSMIS Exporter.exe --self-test`, `console=0`) |
| Self-test body | inline in `build/full_smoke.py` (~130 body lines) | shared `scripts/self_test.py` (one body, two callers) |
| Docs vs DLP scan | copied **after** the scan (F10) | copied **before** the scan (scanned) |
| UI `datas` | every file in `scripts/ui/` | web-asset extension allowlist (behavior-neutral today) |

## 10. Deviations from the approved plan
- **`scripts/self_test.py` is new** (not literally in PA's "Affected" list). It is the
  **mechanism** the plan's own design requires: §C.3 "runs the same … self-test `full_smoke`
  performs" on the exact exe + the Protected "excludes/prune proven by `-SelfTest` (never
  weaken)". Recorded as **D24**; `full_smoke.py` keeps identical behavior via delegation.
- **`release.yml` restructured** (the plan's PA "Affected" named `gui_main`/`build.ps1`/
  `check_app_modules`/`app.spec`). The change is required by PA "Changes: CI wiring" + Completion
  "the exact windowed exe (both variants) … pass their gates in CI": the gated `-SelfTest` build
  is now the shipped artifact instead of an un-gated rebuild. No checksum/signing/hash-pin
  change (those stay P10).
- **`frozen-gate.yml` is new** — the literal realization of PA "Changes: CI wiring (label/nightly
  for the frozen gate)".
- No other deviations. Nothing regression-locked was touched; no scope from P4/P10 was pulled in
  (the report-metadata catalog, hash-pinning, updater fixes remain their phases').

## 11. Known limitations and external verification
- **The FROZEN build + frozen exe `--self-test` are not run in this environment.** A full
  PyInstaller build is heavy and produces `dist/` artifacts, and the review protocol prohibits
  a destructive build here. I verified (a) the **gate logic** end-to-end offline via the dev
  `--self-test` (EXIT 0, full exercise + result file) and (b) the **build/CI scripts** by parse
  + structural review. The frozen exact-exe gate executes in CI: `frozen-gate.yml`
  (label/nightly/dispatch) and `release.yml` on a tag, both on `windows-latest` (which has a
  drivable Edge + WebView2). **This is the one PA claim that completes in CI, by the plan's
  design** ("medium (CI infra)").
- **Work-PC acceptance still owed** (separate gate, **not** in the DoD — §M): both frozen exes +
  the source ZIP on the locked-down Caltrans PC. Offline CI proves boot/import/run; the work-PC
  run proves it under managed-PC controls.
- `frozen-gate.yml`'s `schedule` runs on the default branch (`main`), so nightly coverage begins
  once PA merges; until then the `workflow_dispatch` + `frozen-gate` PR-label triggers exercise
  it on the branch.

## 12. Exact diff scope Codex should review
Baseline `4bbee65` → working tree (ignore `docs/planning/`):
- **`scripts/gui_main.py`** — `_run_self_test()` + the `--self-test` branch placement (after
  `_unblock_dotnet_assemblies`, before `cleanup_leftovers`/`gui_api.run()`; fail-not-skip; the
  `TSMIS_SELFTEST_OUT` mirror).
- **`scripts/self_test.py`** (new) — faithful port of the prior `full_smoke` body; mandatory
  vs. skippable (only the hidden-window probe skips); heavy imports inside `run()`; the explicit
  F6-trio import.
- **`build/full_smoke.py`** — confirm it is a behavior-preserving delegation (path bootstrap +
  `from self_test import run`).
- **`build/app.spec`** — the 4 `APP_MODULES` additions; the UI `datas` allowlist (incl.
  `os.path.isfile`).
- **`build/check_app_modules.py`** (new) — independence (globs `scripts/` itself), the
  completeness/stray/dup/reachability assertions, and the 4 detection self-tests.
- **`build/check_source_zip_smoke.py`** (new) — no-`input()`/no-browser guarantee (EOF stdin +
  valid env selections), and that it asserts *real* dispatch (different selections → different
  modules).
- **`build/build.ps1`** — the always-windowed build; docs-before-prune (F10); the
  `Start-Process -Wait -PassThru` exit-code gate for the windowed exe; `-Sign` widening.
- **`.github/workflows/checks.yml`** — the new blocking step (no trigger change).
- **`.github/workflows/release.yml`** — the gated build *is* the shipped artifact; ordering
  (zip system before building with-browser); the source-zip smoke gate.
- **`.github/workflows/frozen-gate.yml`** (new) — triggers + the `if` label guard.

Focus areas: (1) is the exact-artifact claim actually satisfied — does the shipped exe equal the
gated exe? (2) is any prune/excludes proof weakened vs the prior `-SelfTest`? (3) the windowed
exe exit-code capture via `Start-Process`; (4) reachability-oracle independence; (5) any
unintended coverage loss from pivoting `-SelfTest`.

---

## Remediation — Review round 1 (Codex verdict: BLOCKED)

### Review round addressed
Codex PA review **round 1** — `BLOCKED` (PA-B01/PA-B02/PA-B03 blocking + PA-A01 recommended).

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **PA-B01** — frozen-build evidence absent | **Fixed** | Ran the local **disposable** builds Codex authorized. **Both** exact windowed variants built, pruned, and their **exact shipped `TSMIS Exporter.exe --self-test` passed** — plus the corrected PA-B03 archive gate. |
| **PA-B02** — PR frozen gate stale after the label event | **Fixed** | `frozen-gate.yml` now triggers on `[opened, reopened, labeled, synchronize]` and the job `if` conditions on the PR's **current** label set (`contains(github.event.pull_request.labels.*.name, 'frozen-gate')`), so every later commit while the label is present re-runs the gate. |
| **PA-B03** — source-ZIP gate tested the checkout, not an archive | **Fixed (rewritten)** | `check_source_zip_smoke.py` now builds the **same** archive `release.yml` uploads (`git archive HEAD --prefix=TSMIS-Exporter-batch/`), extracts it to a disposable clean dir, runs the console smoke in a **fresh interpreter rooted at the extracted tree**, asserts archive membership + prefix, and adds a **negative characterization** (a required member missing from the archive → the gate FAILS). |
| **PA-A01** — temp dir leaks on a self-test failure | **Fixed** | `self_test.run` now owns the temp dir in a `try/finally` (body moved verbatim into `_exercise(tmp, emit)`), so cleanup happens on success **and** on a mandatory-failure raise. |

No findings rejected or deferred. All three blockers + the recommendation are resolved.

### Remediation changes
- **`scripts/self_test.py`** — split `run()` into a thin wrapper that owns the temp dir + `finally`
  cleanup, delegating the exercise to `_exercise(tmp, emit)` (no body re-indent; behavior identical
  on success). (PA-A01)
- **`build/check_source_zip_smoke.py`** — **rewritten** from a checkout test to a real-archive gate:
  `git archive` → `zipfile` extract → fresh-interpreter subprocess smoke (`cwd` = extracted root,
  imports only the archived `scripts/`) → membership/prefix asserts → negative "missing member"
  test. (PA-B03)
- **`.github/workflows/frozen-gate.yml`** — trigger `types` + label-set `if`. (PA-B02)
- No other product files changed this round; `gui_main.py`, `app.spec`, `build.ps1`,
  `full_smoke.py`, `check_app_modules.py`, `checks.yml`, `release.yml` are unchanged from the
  initial submission.

### Updated verification
**Frozen exact-artifact builds — local disposable run (the PA-B01 evidence), env Windows 10
AMD64 / Python 3.11 / the build venv:**

- `build/build.ps1 -SelfTest` (system browser) — docs copied **before** the prune; `Pruned 18
  item(s)`; **DLP guard passed**; ran the exact `dist\TSMIS Exporter\TSMIS Exporter.exe
  --self-test`:
  `chromium: PDF 34772 bytes, download ok` · `pdfplumber ok` · `openpyxl round-trip ok` ·
  **`dynamic report modules import: matrix, day_matrix, report_library ok`** (the F6 trio proven
  IN the frozen bundle) · `gui: bridge api ok (7 reports, 252 routes, ui=…\_internal\ui\index.html)`
  · `gui: WebView window + JS bridge ok` · `SMOKE OK`. **`Frozen self-test PASSED (the EXACT
  shipped exe runs every code path)`**; `Built … 153 MB onefolder`.
- `build/build.ps1 -SelfTest -BundleChromium` (bundled Chromium) — Built-in Chromium downloaded;
  `Pruned 237 item(s), reclaimed 46.7 MB`; **DLP guard passed**; same exact-exe `--self-test`
  → all steps + **`Frozen self-test PASSED`**; `Built … 527 MB onefolder`.
- Built-bundle spot checks before cleanup: `Start Here.txt` + `IT-README.txt` present at the app
  root (F10 — copied before the scan, retained); `_internal/ui/` contains exactly `app.css`,
  `app.js`, `index.html` (the UI `datas` allowlist). Disposable `dist/` + `build/pyi-work/`
  removed afterward (git-ignored throughout).

**Offline checks (re-run after the round-2 edits):**
- `check_source_zip_smoke.py` (now archive-based) — **PASS**, including `archive uses the release
  prefix`, `every required console member is IN the archive`, `clean-extract console smoke passes
  against the archived tree`, and `a member missing from the archive FAILS the smoke (negative
  test)`. Re-run via the build-venv interpreter (the exact `release.yml`/`frozen-gate.yml`
  invocation) — PASS.
- PA-A01 cleanup-on-failure: with `_exercise` forced to raise, `run()` leaves **no** temp dir
  behind ("leaked temp dirs after a forced failure: none").
- `frozen-gate.yml` parsed: triggers `[opened, reopened, labeled, synchronize]`; job `if` uses the
  label-collection `contains(...)`.
- Full suite **50/50 PASS**; byte-compile green; `git status` shows only the intended PA files
  (no `dist/`/`pyi-work` leakage; planning untracked).

### Changed measurements
| Metric | Round 1 report | After remediation |
|---|---|---|
| Exact windowed exe gate | logic verified in dev only (frozen build "not run here") | **both variants built + frozen `--self-test` PASSED** (system 153 MB; with-browser 527 MB) |
| Source-ZIP gate | smoke against the **checkout** | smoke against a **real `git archive` extract** (membership + prefix + clean-root + negative test) |
| PR frozen-gate coverage | label event only (stale on later commits) | label-present on **every** PR revision (`synchronize`) |
| `self_test.run` temp dir | cleaned on success only | cleaned on success **and** failure (`finally`) |
| Golden suite | 50 | 50 (unchanged; the 2 PA checks remain) |

**External verification still owed (unchanged, not in DoD):** the same gates in branch CI
(`frozen-gate.yml` label/nightly, `release.yml` on a tag) and work-PC acceptance (§M). The PA-B01
blocker is resolved by the local disposable build run above, per Codex's explicit allowance.

---

## Remediation — Review round 2 (Codex verdict: BLOCKED)

### Review round addressed
Codex PA review **round 2** — `BLOCKED`, narrowed to a single finding (**PA-B03**); PA-B01,
PA-B02, PA-A01 confirmed **Resolved**. Plus Codex required-fix #2: a **correction** to the round-1
remediation claim.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **PA-B03** — the archive gate clean-extracted `HEAD` (P0), not the PA revision | **Fixed with modification** | `check_source_zip_smoke.py` now defaults to a **worktree-candidate** mode: it archives the *complete intended product worktree* (tracked mods + untracked product files, `.gitignore` respected, `docs/planning/` excluded) via a **throwaway git index** (`GIT_INDEX_FILE`), so the real index is never touched and the gate sees the **uncommitted PA revision under review**. A new `--zip PATH` mode gates an exact caller-built archive; `release.yml` now builds the upload zip first and passes it. Added a permanent **worktree-provenance** assertion (the archive must carry this check's own current content). |
| Round-1 claim correction (Codex required-fix #2) | **Corrected (below)** | The round-1 remediation's source-archive run executed `git archive HEAD`; since PA is uncommitted (D20), that archive was **P0 (`4bbee65`)**, not the PA revision. The frozen-exe PA-B01 evidence was unaffected (it built the real worktree via PyInstaller), but the *source-archive* line tested HEAD. Now fixed by candidate mode. |
| **PA-B01 / PA-B02 / PA-A01** | **Resolved (carried forward)** | Unchanged this round; Codex confirmed all three resolved. No code touched for them. |

No findings rejected or deferred.

### Correction of the round-1 remediation claim
The round-1 section above states the archive gate was "Re-run via the build-venv interpreter (the
exact release.yml/frozen-gate.yml invocation) — PASS." **That run used `git archive HEAD`, which —
because PA is uncommitted per D20 — clean-extracted the committed P0 baseline (`4bbee65`), not the
PA worktree.** It validated the archive *mechanism* (extract + clean-root smoke + negative test) but
not the PA source revision. The PA-B01 frozen-build evidence is **not** affected (PyInstaller
analysed/collected the live worktree, and the F6 trio + new modules were proven inside those
bundles). Round 2 closes the source-archive provenance gap.

### Remediation changes
- **`build/check_source_zip_smoke.py`** — added the two modes (worktree candidate default; `--zip`
  supplied-archive), the throwaway-index archive (`git read-tree HEAD` → `git add -A` →
  `git rm --cached docs/planning` → `git write-tree` → `git archive <tree>`, all under
  `-c core.autocrlf=false`), the worktree-provenance content match, and a tolerant prefix detector.
  The clean-extract fresh-interpreter smoke + membership/prefix asserts + negative missing-member
  test are retained.
- **`.github/workflows/release.yml`** — reordered so the batch/source zip is **built first**, then
  gated with `--zip <that exact zip>` (gates the published archive).
- **`.github/workflows/frozen-gate.yml`** — comment clarified: default (candidate) mode gates the
  checked-out PR revision's worktree. `checks.yml` unchanged (default candidate mode is correct).
- No other product files changed this round.

### Updated verification (offline; build venv / system interpreter)
- **Candidate mode** (`check_source_zip_smoke.py`) — **PASS**, incl. `candidate archive reflects the
  WORKTREE (this file's current content), not HEAD`, membership/prefix, clean-extract smoke, and the
  negative missing-member test.
- **Real index untouched** — `git status --porcelain` is **identical** before/after a candidate run
  (the throwaway `GIT_INDEX_FILE` never touches `.git/index`); also verified the full 50-check suite
  leaves the index unchanged.
- **Demo #1 — candidate archive contains the PA additions:** the built candidate zip lists
  `scripts/self_test.py`, `build/check_app_modules.py`, `build/check_source_zip_smoke.py`,
  `.github/workflows/frozen-gate.yml` (all absent from `HEAD`) and **0** `docs/planning/` entries.
- **Demo #3 — an uncommitted change is observed:** injecting a breaking import into
  `scripts/export_multi.py` (worktree only) makes the candidate gate **FAIL** (`EXIT 1`); restoring
  the exact bytes returns it to green (`EXIT 0`, `git status` clean). Plus the built-in negative
  test (a required member missing from the archive → fail).
- **`--zip` mode** — gating a supplied `git archive` zip passes (`EXIT 0`); `release.yml` uses it on
  the exact uploaded archive.
- **Suite/parse:** **50/50** checks PASS; byte-compile green; all three workflow YAMLs valid;
  `git diff --check` clean.

### Changed measurements
| Metric | Round-1 state | After round-2 |
|---|---|---|
| Source-archive gate provenance | `git archive HEAD` → tested **P0 (`4bbee65`)** | **worktree candidate** (the PA revision) by default; `--zip` for the exact release archive |
| Real git index during the gate | (n/a) | provably **untouched** (throwaway `GIT_INDEX_FILE`) |
| Worktree-change sensitivity | none (HEAD only) | **observed** — uncommitted break fails the gate (demo #3) |
| `release.yml` source gate | smoke then `git archive` | `git archive` then `--zip` smoke on the **published** zip |
| Golden suite | 50 | 50 (unchanged) |

**External verification still owed (unchanged, not in DoD):** branch-CI runs of these gates +
work-PC acceptance (§M).
