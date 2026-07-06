# P10 — Packaging / deps / updater hardening (expanded) — Claude report

## 1. Phase ID and name
**P10** — Packaging / deps / updater hardening (later; expanded per CR-001: the flipped
updater items + optional perf) `[blocking; depends PA, P4]`

## 2. Baseline commit
`8605eaf` (HEAD of `refactor/v0.18.0-structural-overhaul` after P9b). Baseline state:
**68/68** Python + **3/3** Node golden checks green, byte-compile green, `check_updater.py`
green, working tree clean apart from the untracked `docs/planning/` workspace.

Dependencies confirmed committed: **PA** `65aef98` (exact-artifact packaging gate) and
**P4** `c86dc78` (report-metadata catalog).

## 3. Changes made
Three workstreams, all offline-provable, no protected contract touched.

### A. `scripts/updater.py` — the §J updater audit set (the meat)
Nine hardening items, each fixture-first (RED test in `check_updater.py` before the change),
RED→GREEN proven:

1. **Checksum is mandatory / fail-closed** (`size-and-checksum-guards-both-skippable`, §J row 1).
   `download_and_stage` now **refuses** to extract when no published checksum exists (was: warn +
   proceed "on size only"). Size alone is not integrity; an unverifiable download is deleted and the
   user is pointed at a manual install. `release.yml` publishes an `.sha256` for every zip, so the
   verified path is the normal path.
2. **ZIP member containment / zip-slip** (`extractall-zip-slip-relies-on-stdlib`, §J row 2).
   New `_safe_zip_members(zf, dest)` validates every member resolves INSIDE the extract dir (no
   absolute paths, drive letters, or `..` traversal) **before** any byte is written; an escaping
   member refuses the whole package.
3. **Staged-exe re-hash before swap** (`staged-exe-launched-from-user-writable-dir-no-recheck`, §J row 3).
   `download_and_stage` records the staged exe's SHA-256 to a sibling `staged.sha256`;
   `apply_update_and_restart` re-hashes the staged exe in the **trusted original process** before
   launching it, refusing a staged tree tampered with in its user-writable folder. A missing record
   (an older staged tree) logs and proceeds (the download was checksum-verified that session).
4. **Rollback message reflects the ACTUAL restore outcome** (`no-rollback-when-relaunch-launches-partial-tree`, §J row 4).
   New `_rollback_dialog_text(restored, log_file)`: a **partial** restore no longer reads as "the
   previous version was kept" — it tells the user to reinstall. (The log already distinguished;
   the dialog did not.)
5. **Rotate `update_helper.log`** (`swap-log-grows-unbounded`, §J row 5). New `_rotate_swap_log` moves
   the log aside to `.1` once it passes `_HELPER_LOG_MAX_BYTES` (256 KB), keeping one backup; best-effort.
6. **WebView2 cache-clear moved below `is_frozen()`** (`webview-cache-cleared-on-every-dev-launch`, §J row 6).
   `cleanup_leftovers` now runs `_recover_store_promotions()` (update-independent, must run in dev)
   BEFORE the frozen gate, and `_clear_webview_caches()` only for packaged builds.
7. **Immediate-death-check hardened** (`immediate-death-check-narrow-window`, §J row, CR-001 flip).
   The single `sleep(1.5); poll()` becomes a bounded **windowed poll** (`_DEATH_CHECK_TOTAL_S` 2.0 s /
   `_DEATH_CHECK_INTERVAL_S` 0.25 s) — a death at any point in the window is caught (earlier than
   before); still fail-safe (only a process OBSERVED dead raises; a live one proceeds).
8. **Download socket timeout + bounded retry** (`dl-socket-timeout-may-fail-slow-large-downloads`, CR-001 flip).
   The socket read timeout already existed (`_DL_TIMEOUT_S`); added a bounded retry
   (`_DL_RETRY_ATTEMPTS` = 3) around the stream (extracted to `_stream_to_file`), restarting cleanly
   each attempt, so a transient network failure no longer aborts the whole download.
9. **`resolve_previous_release` paginates past the 100 cap** (`releases-list-capped-100-revert-blindspot`, CR-001 flip).
   New `_fetch_release_list()` follows GitHub's `Link: rel="next"` (via `_next_link`) up to a
   `_RELEASES_PAGE_CAP` safety bound, so a revert target older than the newest 100 releases is found.

The **signature** §J row stays **deferred** (blocked on a cert — RM06); no runtime signature
abstraction or new crypto dep was added (A03).

### B. Dependency integrity + reproducible build (R1-R10 / RR1-C2 / R1-R11)
- **`requirements-build.lock.txt`** (new) — the fully **hash-pinned** transitive closure of
  `requirements-build.txt` (runtime + PyInstaller), generated with `pip-compile --generate-hashes
  --allow-unsafe` from the proven `build/.venv` freeze (Windows + CPython 3.11). Documented header +
  regeneration recipe; "semantically identical" pins (exact versions + SHA-256), not "byte-identical".
- **`requirements.txt`** — added the explicit **`cryptography==48.0.1`** pin (the EXISTING
  `pdfminer.six` transitive — lock integrity, NOT a new dependency, RR1-C2); documented the
  Windows/3.11 platform + the `version.py`↔pin contract.
- **`build/check_build_env.py`** (new) — asserts `version.py PLAYWRIGHT_VERSION` == the requirements
  playwright pin == the lock pin; `cryptography` pinned; the lock is hash-pinned and covers every
  direct runtime + build dep at the same version. `--verify-installed` (self-fetches `pip freeze`
  via the running interpreter) fails on an env that does not match the lock exactly
  (unexpected / missing / drifted). Self-tests for the diff logic.
- **`build/build.ps1`** — installs the lock with `--require-hashes`, runs the static integrity gate
  before install and the exact-match verification after (fail on unexpected packages); a new
  `-RecreateVenv` switch for a clean rebuild. `version.py`↔requirements Playwright parity is enforced
  by `check_build_env`.

### C. `release.yml` enforcement (R1-T06 / R1-M02) + CI wiring
- **`.github/workflows/release.yml`** — a new guard step asserts all **three variant zips + each
  `.sha256`** exist before the release is created (fails, never skips). The per-variant `-SelfTest`
  (windowed exes) + console-smoke (source zip) gates already fail-not-skip. **Signing is fully
  deferred (RM06):** the existing SignPath integration is an **inert, deferred template** present only
  for the system-browser zip (gated off by `SIGNPATH_ENABLED`); the with-browser upload/submit pair is
  left as a documented comment to fill when signing is enabled — P10 does **not** implement per-variant
  signing parity and does not claim to (A03). P10 leaves these signing steps unchanged.
- **`.github/workflows/checks.yml`** — wired `check_build_env.py` into the blocking Packaging step
  (the Updater step already runs `check_updater.py`, so the new §J tests run in CI automatically).

### D. Optional perf (A01) — measured, **dropped** for v0.18.0
Built the A01 harness (cold-subprocess import timing, 7 reps, median, baseline-subtracted) and
measured: `import reports` pulls openpyxl/pdfplumber/pdfminer/PIL/playwright (~937 ms over a 66 ms
bare interpreter), on the GUI startup critical path. **Dropped** — see §10/§11 for the full
rationale (the gain is real but the safe realization is a central report-registry refactor whose
frozen-bundle correctness is not offline-provable; out of bounded optional-perf scope for a
candidate release).

## 4. Files affected
**Modified (6):** `scripts/updater.py`, `build/check_updater.py`, `requirements.txt`,
`build/build.ps1`, `.github/workflows/release.yml`, `.github/workflows/checks.yml`.
**New (2):** `requirements-build.lock.txt`, `build/check_build_env.py`.

No `compare_core`, auth-at-rest, core-engine, GUI, or `scripts/ui/` change. No `app.spec` change
(`check_build_env.py` is a build-only check; the lock is a build input — neither is shipped in the
app bundle, so `APP_MODULES`/UI assets are untouched).

## 5. Architectural decisions
- **D26 — fail-closed update verification.** Never extract/swap unverified bytes: an absent checksum
  refuses the install (not "size-only"), matching the §J fail-closed disposition. `release.yml` makes
  the verified path the normal path by publishing `.sha256` for every asset.
- **D27 — staged-exe re-hash runs in the TRUSTED (original) process.** A staged exe must not be
  trusted to vet itself; the re-hash is in `apply_update_and_restart` (old process) against a sidecar
  written at download time. A missing sidecar (older staged tree) logs and proceeds — the download was
  already checksum-gated that session — so the change never spuriously blocks a legitimate update.
- **D28 — the hash lock is a build INPUT, separate from the human-edited `requirements*.txt`.** The
  `.bat` source path keeps the editable `requirements.txt` (its `--require-hashes` adoption is
  work-PC-validated, deferred to v0.18.1); the reproducible packaged build installs the lock with
  `--require-hashes`. This bounds the blast radius and keeps the lock regenerable from the freeze.
- **D29 — `check_build_env --verify-installed` self-fetches `pip freeze`.** A Windows-PowerShell
  native-to-native pipe corrupted the first freeze line with a BOM (observed during validation); the
  script runs `pip freeze` inside its own interpreter so `build.ps1` needs no fragile pipe.
- **D30 — windowed death-check, not a single instant.** Polling across a bounded window catches an
  immediate death at any point in it (and earlier than the old fixed 1.5 s), while staying fail-safe.
- **A01 perf gate → drop (D31).** The harness exists and was applied; the optimization is deferred
  with data (see §10/§11), the legitimate outcome of an explicitly-optional gate.

## 6. Compatibility and migration handling
- **No persisted-data, output, filename, settings, manifest, or registry change.** All updater
  public signatures are unchanged: `download_and_stage(info, on_progress)`,
  `apply_update_and_restart(staged_dir)`, `resolve_previous_release(...)`, `perform_swap(...)`,
  `run_swap_mode(argv)`. Callers (`gui_api.update_apply` @1245, `gui_worker` @1608/1628,
  `gui_main.run_swap_mode` @122) are unmodified and behavior-compatible.
- **Fail-closed checksum**: forward updates always carry an `.sha256` (`release.yml`), so the normal
  path is unaffected; only a (rare) revert to a pre-checksum release now refuses with the manual-install
  fallback instead of installing unverified — the intended hardening.
- **Migration: none.** The lock is additive; the `.bat`/source path still uses `requirements.txt`.
- **`build.ps1 -SelfTest`/`-BundleChromium`/`-Sign` semantics preserved**; only step 1 (the venv +
  deps) changed (lock + `--require-hashes` + env verification); steps 2–6 (PyInstaller, docs, prune,
  self-test, sign) are byte-unchanged.

## 7. Tests and commands run
All via `build/.venv/Scripts/python.exe -B -X utf8` (the suite runner), offline, no live TSMIS / auth /
network:
- **Fixture-first RED→GREEN (the 9 §J items):** added 9 test functions to `check_updater.py`; ran it
  against the **unmodified** `updater.py` → the new tests **FAIL/error** (pagination returns None; no
  zip-slip/checksum messaging; no retry; dev cache cleared; `_HELPER_LOG_MAX_BYTES` / `_sha256_file` /
  `_launch_detached` / `_rollback_dialog_text` absent) — RED proven; then implemented → **GREEN**
  (`ALL UPDATER CHECKS PASSED`). Fixed the one existing test (`test_stage_rename_retries`) that staged
  without a checksum (now provides the matching digest, per the fail-closed change).
- **`check_build_env.py`** — static parity + diff self-tests PASS; live `--verify-installed` against
  `build/.venv` → "installed env matches the lock exactly".
- **Lock proof (offline):** `pip install --require-hashes -r requirements-build.lock.txt` into THREE
  fresh throwaway venvs — clean install, `pip check` "No broken requirements", runtime+build imports
  load. **build.ps1 step-1 replay** in PowerShell (recreate → integrity gate → `--require-hashes`
  install → self-fetch verify) PASS, plus a **negative test**: a polluted venv (extra `six`) **fails**
  verification (exit 1).
- **`build.ps1`** PowerShell AST parse OK; **all 3 workflow YAMLs** valid (`yaml.safe_load`); the
  `release.yml` guard PowerShell AST-parses.
- **Full regression suite:** `for f in build/check_*.py` → **69/69 PASS** (68 + `check_build_env`);
  **3/3 Node**; `compileall scripts build version.py` OK; import smoke (`updater`/`gui_api`/`reports`)
  OK; `check_no_misspelling` PASS; `check_import_direction` PASS (no new cycle);
  `check_worker_lifecycle` PASS (updater callers intact).
- **Diff hygiene:** `git diff --check 8605eaf` clean; the change set is exactly the 8 intended files.
- **Frozen exact-artifact build (local, disposable):** `build.ps1 -SelfTest` ran the FULL new step-1 →
  PyInstaller → prune → frozen self-test end-to-end (env Windows 10 / Python 3.11). Output:
  dependency-integrity `ALL BUILD-ENV CHECKS PASSED`; `--require-hashes` install from the lock
  (setuptools upgraded 65.5.0→82.0.1, all else satisfied); **`installed env matches the lock exactly`**;
  PyInstaller analyzed the `APP_MODULES` hidden imports + the contrib hooks; `Pruned 18 item(s),
  reclaimed 5.4 MB`; the exact shipped exe `--self-test`: `chromium: PDF 34772 bytes, download ok` ·
  `pdfplumber ok` · `openpyxl round-trip ok` · `dynamic report modules import: matrix, day_matrix,
  report_library ok` · `gui: bridge api ok (7 reports, 252 routes)` · `gui: WebView window + JS bridge
  ok` · **`SMOKE OK`** → **`Frozen self-test PASSED (the EXACT shipped exe runs every code path)`** ·
  `Built … 149 MB onefolder`. Disposable `dist/` + `build/pyi-work` removed afterward (git-ignored).

## 8. Results
Every offline-verifiable item is **green**. The 9 §J updater items are RED→GREEN proven and locked by
`check_updater.py` (in CI via checks.yml). The reproducible-build policy is in place and proven: the
hash lock installs clean with `--require-hashes` (3× independently), `check_build_env` enforces
version/requirements/lock parity + fail-on-unexpected, and `build.ps1`'s new step-1 was replayed
end-to-end including a negative pollution test. `release.yml` enforces the full artifact + `.sha256`
set (fails-not-skips). The app remains runnable (no signature/public-API change; updater callers
intact). Perf was measured and deferred with data per A01.

## 9. Before/after measurements
| Metric | Before (`8605eaf`) | After |
|---|---|---|
| `updater.py` lines | 900 | ~1090 (+§J helpers/guards) |
| `check_updater.py` tests | 9 | 18 (+9 §J) |
| Golden Python suite | 68 | 69 (+`check_build_env`) |
| Build deps | un-hashed `requirements-build.txt` | hash-pinned `requirements-build.lock.txt` (`--require-hashes`) |
| `cryptography` transitive | implicit (unpinned) | explicit `==48.0.1` pin (lock integrity) |
| Build-env verification | none | static parity + exact-match fail-on-unexpected (`check_build_env`) |
| Release artifact enforcement | implicit (release create references files) | explicit guard: 3 zips + 3 `.sha256` or fail |
| No-checksum download | proceeds "on size only" | **refused** (fail-closed) |
| ZIP extraction | `extractall` (stdlib only) | explicit member-containment guard first |
| Staged exe before swap | launched as-is | re-hashed vs the download-time record (trusted process) |
| Immediate-death check | single `sleep(1.5)` + 1 poll | windowed poll (2.0 s / 0.25 s) |
| Download transient failure | aborts the whole download | bounded retry (3) + socket timeout |
| Revert resolver | first 100 releases only | paginates (Link `rel=next`, cap 50 pages) |
| `import reports` cold cost (A01) | ~937 ms over a 66 ms bare interp (measured; not changed) | unchanged — optimization deferred (§11) |

## 10. Deviations from the approved plan
- **Optional perf DROPPED (A01).** §I lists "optional perf (lazy `reports` imports) only with the
  R1-A01 harness + threshold." The harness was built and the cost measured as material (~937 ms), but
  the optimization is **deferred to a future focused effort**, not shipped — because (a) the report
  registry is needed at bridge-init (the UI's report list renders at startup), so deferring `reports`
  only relocates the cost unless the registry is restructured to build from P4 catalog metadata and
  lazy-resolve heavy modules at run time; (b) `playwright` (~250 ms) loads via `common` at startup
  regardless; and (c) the safe realization's frozen-bundle correctness (PyInstaller static-graph
  completeness for now-dynamically-imported modules) is **not offline-provable** and a frozen
  `ImportError` would be a severe candidate-release regression. This is the legitimate outcome of an
  explicitly-optional gate, recorded with data for the roadmap (P11), not a silent drop.
- **`build/check_build_env.py` is new** (not literally in P10's "Affected" list). It is the mechanism
  the plan's own deliverables require — "assert `version.py`↔`requirements` Playwright" and the
  "fail on unexpected packages" env policy (R1-R10) — homed in the offline `check_*` model. Recorded
  as **D29**.
- **The hash lock is a separate file (`requirements-build.lock.txt`)**, not in-place hashes on
  `requirements.txt` — see **D28** (bounds the blast radius; keeps the `.bat` source path stable for
  its v0.18.1 work-PC validation; the lock is regenerable from the freeze).
- No other deviations. Nothing regression-locked was touched; cert-store TLS, the two-phase swap
  order, and the `excludes`/prune are unchanged; no runtime signature abstraction / new crypto dep (A03).

## 11. Known limitations and external verification
- **The FULL frozen build + the real update SWAP are not fully proven in this environment.** The
  step-1 build changes are independently proven offline (the PowerShell replay does the exact
  recreate → integrity-gate → `--require-hashes` install → verify sequence, plus a negative pollution
  test; the lock installs clean 3×; `build.ps1` AST-parses); steps 2–6 (PyInstaller/prune/self-test)
  are byte-unchanged from PA. A local disposable `build.ps1 -SelfTest` was run for end-to-end evidence
  (see §7). The **frozen exact-exe gate** runs in CI (`frozen-gate.yml` label/nightly, `release.yml`
  on a tag), as the plan designs. The **real updater swap** (download→stage→re-hash→swap→relaunch on a
  managed PC, a real v0.17→v0.18 update, the pagination/retry/checksum paths against live GitHub) is
  **work-PC acceptance — owed to v0.18.1** (§K2/§M), not the v0.18.0 DoD.
- **The `.bat`/source path still uses the un-hashed `requirements.txt`** (D28). Adopting
  `--require-hashes` there is a behavior change on locked-down PCs that can only be field-validated,
  so it is deferred to v0.18.1.
- **Deferred perf opportunity (data captured):** restructure the report registry to build from P4
  catalog metadata and lazy-resolve the heavy export/consolidate modules at run time (~688 ms
  deferrable beyond the `playwright` floor), with frozen-gate verification — a future focused effort
  (roadmap, written by P11).
- **The §J signature row stays deferred** (RM06; blocked on a cert) — no runtime signature work shipped.

## 12. Exact diff scope Codex should review
Baseline `8605eaf` → working tree (ignore `docs/planning/`):
- **`scripts/updater.py`** — the 9 §J items: fail-closed checksum (`download_and_stage`), zip-slip
  guard (`_safe_zip_members`), bounded download retry (`_stream_to_file` + the loop), pagination
  (`_next_link`/`_fetch_release_list`/`resolve_previous_release`), staged-exe re-hash
  (`_sha256_file`/`staged.sha256`/`_staged_hash` + `apply_update_and_restart`), windowed death-check
  (`_DEATH_CHECK_*` + `_launch_detached`), log rotation (`_rotate_swap_log`/`_swap_log`), rollback
  message (`_rollback_dialog_text` + `perform_swap`), and the `cleanup_leftovers` reorder
  (cache-clear below `is_frozen()`). Confirm: cert-store TLS untouched; swap order (copy-then-rename)
  untouched; no public signature change; the missing-sidecar path stays fail-safe.
- **`build/check_updater.py`** — the 9 new tests (RED→GREEN); the `_StreamResp`/`_FakeProc` fakes;
  the `_FakeReleasesResp.headers` add (pagination); the existing `test_stage_rename_retries` checksum fix.
- **`requirements-build.lock.txt`** (new) — hash-pinned; cryptography + setuptools + the full tree;
  the documented provenance/regeneration header.
- **`requirements.txt`** — the `cryptography==48.0.1` pin + platform/version-parity docs.
- **`build/check_build_env.py`** (new) — parity asserts, the `--verify-installed` self-fetch + BOM
  tolerance, and the diff self-tests.
- **`build/build.ps1`** — step-1: `-RecreateVenv`, the static integrity gate, `--require-hashes`
  install from the lock, and the self-fetch exact-match verification (fail on unexpected).
- **`.github/workflows/release.yml`** — the artifact+`.sha256` completeness guard (fails-not-skips).
- **`.github/workflows/checks.yml`** — `check_build_env.py` wired into the blocking Packaging step.

Focus areas: (1) is the fail-closed checksum + staged re-hash actually fail-safe (no spurious block of
a legitimate update)? (2) is the lock genuinely reproducible + complete (the `--require-hashes` proof)?
(3) does `check_build_env --verify-installed` correctly fail on unexpected/missing/drifted packages?
(4) is the A01 perf drop justified + fully documented? (5) any protected-contract drift (TLS, swap
order, prune, no new crypto dep)?

---

## Remediation — Review round 1 (Codex verdict: BLOCKED)

### Review round addressed
Codex P10 review **round 1** — `BLOCKED` (one blocking **P10-B01** + one non-blocking **P10-A01**).

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P10-B01** — staged-update re-verification is fail-open + incomplete | **Fixed** | The staged trust record is now **mandatory** and covers the **whole bundle**, and `apply_update_and_restart` **fails closed**. Both bypasses Codex measured (`internal_tamper_allowed`, `missing_sidecar_allowed`, each `launch_calls=1`) are closed — reproduced and verified at **0 launches**. |
| **P10-A01** — SignPath parity wording is misreadable | **Fixed (wording)** | Report §3.C + the coordination log row now state signing is **fully deferred (RM06)** and the SignPath integration is an **inert deferred template, NOT implemented per-variant parity**. No workflow change (adding the inert with-browser pair would be untested deferred-signing surface; the approved plan says "workflow design only" and signing stays deferred). |

No findings rejected or deferred.

### Remediation changes (all in `scripts/updater.py` + `build/check_updater.py`)
- **Whole-bundle trust digest.** New `_bundle_digest(staged)` folds a SHA-256 over **every file under each
  `_BUNDLE_ITEMS` entry** (the exe **and** the code-bearing `_internal/**` tree **and** the readmes), by
  sorted POSIX relative path. This replaces the exe-only `_sha256_file(new_exe)` record/compare, so
  tampering with `_internal` (or adding/removing any bundled file) is detected — Codex's core gap.
- **Mandatory record (fail staging on failure).** `download_and_stage` now computes `_bundle_digest`
  and writes it via a new `_write_staged_record` seam; if the digest can't be computed (`None`) **or**
  the write raises `OSError`, the stage **fails** and `UPDATE_DIR` is removed (`shutil.rmtree`) — **no
  usable staged tree** is left, so apply can never launch an unverifiable one.
- **Fail closed in apply.** `apply_update_and_restart` now: `expected = _staged_hash(staged)`; if
  `expected is None` (missing/malformed record) → **raise** before `_launch_detached`; else recompute
  `_bundle_digest(staged)` and **raise** on any mismatch (an unreadable tree → `None` ≠ expected →
  refuse). The old "missing record → log + proceed" path is gone.
- **`_staged_hash` docstring** updated (it now holds the bundle digest; absent/garbled → fail closed).
- **Tests (`check_updater.py`):** `test_staged_exe_rehash` replaced by **`test_staged_bundle_reverify`**
  (matching → launches; `_internal` tamper / exe tamper / **added** `_internal` file / **missing** record
  / **malformed** record → refused with a **launch-call counter asserting 0 launches**; restored record
  → launches again) and **`test_staged_record_mandatory`** (record **write failure** → staging fails +
  `UPDATE_DIR` removed; **uncomputable** digest → same; happy path records a 64-hex digest that
  **changes when `_internal` changes**). `test_death_check_window` updated to record a real bundle digest.

### Updated verification
- **RED→GREEN (behavioral, self-contained probe, since the new tests target the new contract):** a
  throwaway probe reconstructed the OLD gate (exe-only compare, fail-open on missing) and reproduced
  Codex's exact bypasses — `OLD internal_tamper_allowed = True`, `OLD missing_sidecar_allowed = True`;
  the **current** `apply_update_and_restart` refused both — `NEW internal_tamper refused = True`,
  `NEW missing_sidecar refused = True`, **total launches during the refused cases = 0**. Probe deleted.
- `build/check_updater.py` → **ALL UPDATER CHECKS PASSED** (the 6 new B01 assertions + the 6 mandatory-
  record assertions green); byte-compile (`scripts`/`build`/`version.py`) OK; import smoke
  (`updater`/`gui_api`) OK; `check_worker_lifecycle` (imports updater) PASS.
- Full regression suite re-run: **69/69 Python + 3/3 Node** green; `git diff --check 8605eaf` clean; the
  change set is unchanged (still the 8 P10 product files — the remediation touched only `scripts/updater.py`
  + `build/check_updater.py`, both already in scope). The hash-pinned lock / `build.ps1` / `release.yml`
  workstreams are untouched by this round, so their proofs (incl. the full local frozen `-SelfTest`) stand.

### Changed measurements
| Metric | Round-1 submission | After remediation |
|---|---|---|
| Staged trust record | exe-only (`_sha256_file(_EXE_NAME)`) | **whole bundle** (`_bundle_digest`: exe + `_internal/**` + readmes) |
| Missing/malformed record at apply | **proceeds** (logs, launches) | **fails closed** (refuses before `_launch_detached`) |
| Record write/compute failure at stage | logs + returns a usable staged tree | **fails staging**, removes `UPDATE_DIR` (no usable tree) |
| `_internal` tamper before launch | **launched** (`launch_calls=1`) | **refused**, `0` launches |
| `check_updater.py` updater tests | 18 | 22 (split + added missing/malformed/write-fail/`_internal`-tamper coverage) |

**External verification still owed (unchanged, not in DoD):** a real v0.17→v0.18 update on a managed PC
exercising the live download→stage→**bundle re-verify**→swap path — work-PC acceptance, v0.18.1 (§K2/§M).

---

## Remediation — Review round 2 (Codex verdict: PASS WITH FIXES)

### Review round addressed
Codex P10 review **round 2** — `PASS WITH FIXES`: **P10-B01 resolved** and **P10-A01 resolved (wording)**
(both confirmed by Codex), with one new required documentation-only fix **P10-R01**.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P10-R01** — coordination/status text still describes the old fail-open staged-record path | **Fixed (docs-only)** | The live P10 coordination log row (`00-coordination.md`) still summarized staged re-verify as "missing record → logs+proceeds, fail-safe" — the pre-remediation behavior. Corrected to state the trust record is **mandatory**, covers the **whole staged bundle** (`_EXE_NAME` + `_internal/**` + readmes), and **fails closed** on missing/malformed/write-failed records or any content mismatch. **No product-code change** (Codex: no product re-review needed for the wording fix). |
| **P10-B01** | **Resolved (carried)** | Confirmed resolved by Codex round 2; no code touched this round. |
| **P10-A01** | **Resolved (carried)** | Confirmed resolved (wording) by Codex round 2; no change this round. |

No findings rejected or deferred.

### Remediation changes
- **`docs/planning/v0.18.0/00-coordination.md`** (the live P10 log row) — item (3) "staged-exe re-hash"
  rewritten to "**staged-bundle re-verify (mandatory, whole-bundle, fail-closed)**" matching the
  remediated code (`_bundle_digest` over `_EXE_NAME`+`_internal/**`+readmes; staging fails closed when
  the record can't be computed/written, removing `UPDATE_DIR`; apply fails closed before
  `_launch_detached` on missing/malformed/mismatch). The log row's review-status tail now records the
  round-1 (`BLOCKED`→B01/A01 fixed) and round-2 (`PASS WITH FIXES`→R01) history. Earlier historical
  review rounds in this report are **not** rewritten (preserved verbatim).
- **No product file changed this round.** `scripts/updater.py`, `build/check_updater.py`,
  `requirements.txt`, `requirements-build.lock.txt`, `build/build.ps1`, `build/check_build_env.py`,
  `.github/workflows/release.yml`, `.github/workflows/checks.yml` are byte-identical to the round-1
  remediation state.

### Updated verification
- **Product set unchanged:** `git status` shows the same 8 P10 product files as round 1; this round's only
  edit is `docs/planning/v0.18.0/00-coordination.md` (untracked planning, never staged).
- `check_no_misspelling.py` → PASS (the added coordination text contains no transposed product-name spelling).
- The round-1 product verification stands unchanged (it was the last code change): `check_updater.py`
  GREEN incl. the B01 tests; the behavioral RED→GREEN probe (`internal_tamper`/`missing_sidecar` refused
  at 0 launches); full suite **69/69 Python + 3/3 Node**; the full local frozen `build.ps1 -SelfTest`.

### Changed measurements
None — documentation-only round (no product behavior or test-count change vs round 1).

---

## Remediation — Review round 3 (Codex verdict: PASS WITH FIXES)

### Review round addressed
Codex P10 review **round 3** — `PASS WITH FIXES`: **P10-B01 / P10-A01 / P10-R01 resolved** (carried), with
one new required documentation-only fix **P10-R02**.

### Finding dispositions
| ID | Disposition | Summary |
|---|---|---|
| **P10-R02** — the round-2 report line contained the guarded product-name transposition, making its own `check_no_misspelling` claim false | **Fixed (docs-only)** | The round-2 "Updated verification" line spelled out the forbidden product-name transposition verbatim (to assert "no typo"), which the repo-wide `check_no_misspelling.py` guard flags — and the round-2 check had been run **before** that section was appended, so the claim was stale. The line is reworded to "contains no transposed product-name spelling" (no literal misspelling), and `check_no_misspelling.py` is re-run **after** this section is in place. **No product-code change.** |
| **P10-B01 / P10-A01 / P10-R01** | **Resolved (carried)** | Confirmed resolved across rounds 2–3; no code or further doc change. |

No findings rejected or deferred.

### Remediation changes
- **`docs/planning/v0.18.0/phases/P10-claude-report.md`** — reworded the single round-2 verification
  line that carried the forbidden product-name transposition; the rest of the report (incl. all earlier
  remediation rounds) is preserved verbatim. Process fix: the misspelling guard is now re-run **after**
  appending this round's section, so the verification claim is true of the final report state (the
  round-2 ordering error — check-then-append — is corrected here).
- **No product file changed this round** (and none in round 2): `scripts/updater.py`,
  `build/check_updater.py`, `requirements.txt`, `requirements-build.lock.txt`, `build/build.ps1`,
  `build/check_build_env.py`, `.github/workflows/release.yml`, `.github/workflows/checks.yml` are
  byte-identical to the round-1 remediation state.

### Updated verification
- `check_no_misspelling.py` → **PASS** (re-run after this section was appended; the whole report,
  including this round-3 text, is clean of the guarded transposition).
- **Product set unchanged:** `git status` shows the same 8 P10 product files; this round's only edit is
  `docs/planning/v0.18.0/phases/P10-claude-report.md` (untracked planning, never staged).
- The round-1 product verification stands (last code change): `check_updater.py` GREEN incl. the B01
  tests; the behavioral probe refused at 0 launches; full suite **69/69 Python + 3/3 Node**; the full
  local frozen `build.ps1 -SelfTest`.

### Changed measurements
None — documentation-only round.
