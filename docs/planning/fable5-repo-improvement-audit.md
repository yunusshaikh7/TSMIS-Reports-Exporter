# Repo Improvement Audit — v0.18.4 baseline

**Date:** 2026-07-01 · **Auditor:** independent multi-agent audit (13 domain passes + adversarial
per-finding verification + inline ground-truth checks, across three rounds) · **Scope:** entire
`main` tree at `0fa1cd5` (v0.18.4) **plus the `origin/gh-pages` branch** (read via `git show`),
read-only. **No source files were modified.**

**Round 3 (gap-fill) update:** every finding in this report now has a completed verification —
49 adversarially agent-CONFIRMED, ~19 self-verified, **1 REFUTED** (REL-06, retained below for the
record), and 0 unverified. The previously-open areas (export/auth deep pass, gh-pages, packaging
drift, mock.js payload drift, `.bat` files) are covered; see the new sections H2/I2/M and the
updated "Verified good" and "Areas not inspected" sections at the end.

**Verification legend** — every finding carries one of:
- `CONFIRMED-dynamic` — proven by executing code against the repo.
- `CONFIRMED` — an adversarial verifier agent (or the auditor directly) re-read the cited code and
  the claim held.
- `SELF-VERIFIED` — the auditor confirmed the core evidence with targeted reads/greps.
- `REPORTED` — found by a domain auditor with quoted evidence, but no independent second pass.
  (After round 3, no findings remain in this state — every former REPORTED item was verified and
  is annotated below with its verdict.)

---

## Executive summary

This codebase is in **much better shape than "heavily vibe-coded" suggests**. It has unusually
strong invariant discipline for a solo project: producer-owned completion (`outcome.py`),
transactional artifact writes (temp + `os.replace` + journaled promotion), a regression-locked
comparison core with canaries, 78 standalone check scripts wired into CI, append-only stable IDs,
and a knowledge library that mostly matches the code. The audit therefore found few "rotting
foundations" — but it found **real, specific defects**, several of them field-relevant:

1. **A headline v0.18.2 fix shipped dead.** `matrix._comparison_row_count` raises `NameError`
   (`load_workbook` is only imported inside a *different* function), the `except Exception` swallows
   it at DEBUG, and the formulas-twin size guard therefore **never skips** — bulk matrix runs still
   build the multi-minute live-formulas twin for 17k-row Intersection Detail. Proven by execution.
2. **The release pipeline has a gate gap**: `release.yml` builds, self-tests, and publishes without
   running (or requiring) the 78-check offline suite — the exact mechanism that let v0.17.3 ship
   red. There is also no local run-everything script and no guard that a new `check_*.py` actually
   lands in `checks.yml`.
3. **The TSN library staleness trap is still open** (bit the field twice: v0.17.6, v0.18.3): the
   library stores pre-normalized values with no normalization-version stamp, so every future
   normalization fix silently ships broken until a manual rebuild.
4. A handful of **P1 correctness bugs**: `~$` Excel lock files falsely demote whole consolidations
   to PARTIAL; the background env-check can collide with a user export on the single-instance Edge
   profile (device-mode work PCs — the real field config); the Compare tab's Browse… folder
   permanently stomps the dropdown; the falsy-zero `str(v or "")` idiom still lives in normalizers
   that feed row-alignment keys.
5. Systemic (not blocking) debt: 6 files over the 800-line standard, ~25 silent exception swallows
   violating the project's own logging contract, 4 large copy-paste families, a mock that still
   emits events in the order that made the v0.18.4 bug unreproducible, and a public face that has
   drifted — README and the gh-pages landing page are both 4 releases stale, with two un-ignored
   sensitive artifact patterns at the repo root. The round-3 gap fill added one more P2 with an
   ugly failure mode: the export stubs' ImportError guard can kill the GUI process silently
   (EXP-02) — and, on the positive side, refuted three round-1 speculations (exporter/parallel
   duplication, prune_bundle fragility, SignPath) and proved mock↔bridge event/endpoint parity.

**Recommended posture:** cut a small correctness release (the Phase-0/1 items below) before the
planned v0.18.5 operational sign-off, then schedule one structural cleanup version for the splits
and dedup. Nothing found requires an architecture rewrite.

---

## Top 15 highest-leverage improvements

| # | ID | What | Why it's leverage |
|---|----|------|-------------------|
| 1 | BUG-01 | Fix the `_comparison_row_count` NameError (formulas-twin guard is dead code) | A shipped v0.18.2 feature silently does nothing; 1-line fix restores minutes of wall-clock per bulk matrix run |
| 2 | REL-01 | Close the release-gate gap: make `release.yml` run/require the 78-check suite, add a check-list completeness guard, add a local `run_checks` runner | Converts the v0.17.3 "shipped red" class of failure from *possible* to *structurally impossible* |
| 3 | BUG-02 | TSN library normalization-version stamp + auto-rebuild from raw | The only defect here that has shipped wrong *numbers* twice; kills a whole recurring bug class |
| 4 | BUG-03 | Filter `~$` Excel lock files in `consolidate_xlsx` | Trivial fix; stops a routine user action (leaving Excel open) from falsely demoting consolidations |
| 5 | BUG-04 | Make the background env-check claim the task gate (Edge-profile mutual exclusion) | Removes a real launch-failure race in the exact field configuration (device-mode work PC) |
| 6 | BUG-05 | Compare tab: stop the Browse… folder from permanently stomping the dropdown | Users can silently compare the wrong folder — a trust-destroying failure for a comparison tool |
| 7 | BUG-07 | Eradicate the remaining `str(v or "")` falsy-zero sites (incl. `norm_pm` feeding alignment keys) | Same idiom already caused v0.18.3's phantom diffs; the remaining sites are landmines |
| 8 | LOG-01 | Sweep ~25 silent `except: pass/return` sites to the house logging idiom | Restores the project's own "one log upload answers it" contract — the field-debugging superpower |
| 9 | TST-01 | Add 5 checks targeting the field-bug classes that shipped (real-workbook probe, mock event order, staleness, empty projection, endpoint gating) | Each one locks a bug class that *actually* escaped, not hypothetical coverage |
| 10 | FE-02 | Fix mock.js completion-event order to match production | Unblocks reproducing the entire order-sensitive frontend bug class (v0.18.4 queue-phantom) in `#mock` |
| 11 | PRF-01 | De-duplicate the Report View rollup's redundant recompute (2–4× work on the largest report) | Directly shortens the "looks frozen" window v0.18.2 mitigated but didn't remove |
| 12 | ARC-02 | Split `gui_api.py` (2622) and `gui_worker.py` (2005) along their existing section bands | The proven `GuiMatrixMixin` pattern makes this mechanical; stops the every-feature-lands-here growth |
| 13 | DUP-01..04 | Consolidate the four copy-paste families (comparator skeletons, PDF parsers, endpoint claim-gate blocks, frontend progress/button sync) | Each family has already produced divergence bugs (four different `_norm_route`s; five hand-maintained lock lists) |
| 14 | SEC-01 | `.gitignore` the two sensitive dev artifacts (`config.json.corrupt`, `tsmis_evidence_*.zip`) | Public repo; one absent-minded `git add -A` away from publishing user paths/URLs |
| 15 | DOC-01 | Decide `docs/planning/` (track it or ignore it) + refresh README (4 releases stale) + document `frozen-gate.yml` | The public face and the knowledge library both contradict the actual repo today |

---

# Detailed findings

## A. Correctness bugs

### BUG-01 — `matrix._comparison_row_count` NameError: the v0.18.2 formulas-twin size guard is dead code
- **Severity:** P1 · **Confidence:** high · **Status:** CONFIRMED-dynamic
- **Files:** `scripts/matrix.py` (`_comparison_row_count` :712-734, `_try_formulas` :737-768; the only
  `load_workbook` import is *function-local* at :166)
- **Evidence:** matrix.py's module imports (lines 21-34) do not include openpyxl; line 166 does
  `from openpyxl import load_workbook` inside a different function; line 717 calls `load_workbook(...)`
  bare. Executed against the repo: building a real 5-row Comparison workbook and calling
  `matrix._comparison_row_count(path)` returns `None` (the `except Exception` at :718 swallows the
  `NameError` and logs at DEBUG). Per :714-715 and :749-750, `None` ⇒ "the caller writes the twin anyway".
- **Why it matters:** v0.18.2's fix (B) — "skip the live-formulas twin for bulk matrix comparisons over
  12k rows" — has never actually fired. Every bulk matrix rebuild of Intersection Detail (~17k rows)
  still spends minutes building millions of formulas, the exact "looks frozen / keeps getting
  cancelled" behavior v0.18.2 was cut to fix. The skip announcement string is also dead.
- **Fix:** add `from openpyxl import load_workbook` at the top of `_comparison_row_count` (matching the
  lazy-import idiom at :166 keeps openpyxl off the GUI-startup path), or hoist one lazy import to a
  module-level helper. One line either way.
- **Verification:** new check (see TST-01): import `matrix`, write a real ≥2-row xlsx, assert
  `_comparison_row_count(p) == rows`; assert a >12k-row workbook makes `_try_formulas` skip (events
  message emitted, no formulas sibling written).
- **Difficulty:** trivial · **Timing:** before next release

### BUG-02 — TSN library stores pre-normalized values with no normalization-version stamp; freshness is mtime-only
- **Severity:** P1 · **Confidence:** high · **Status:** CONFIRMED (two verifier agents, independently)
- **Files:** `scripts/tsn_library.py` (`status()` :284-285 mtime-only `current`; `build_consolidated`
  :343-348 reuses on that check; `_resolve_source` :507-510 returns `kind='consolidated'` whenever the
  file exists — without even the mtime check), `scripts/tsn_load_*.py` (`build_into` stores
  already-normalized rows, e.g. tsn_load_intersection_detail.py:30), `scripts/gui_matrix.py`
  (`rebuild_tsn_library` :673/695 — the only rebuild trigger).
- **Evidence:** repo-wide grep finds no `normalization_version`/parser-version stamp anywhere in
  `scripts/`. `compare_intersection_detail_tsn.py:283-284` self-documents that compare-time
  re-normalization is only a partial repair (v0.18.3 proved a numeric-0 blanked *inside* the library is
  unrecoverable at compare time: stale library = 43 phantom diffs, rebuilt = 0).
- **Why it matters:** this exact mechanism shipped wrong comparison output twice (v0.17.6
  "Signalized ≠ P", v0.18.3 Intrte-Postmile 0-vs-blank). Every future normalization fix will look
  unfixed in the field until someone remembers Settings ▸ TSN reports ▸ Rebuild. Owner has deferred
  this knowingly (2026-06-29 "fine for now") — flagged here because it is the highest-recurrence
  defect in the repo's history.
- **Fix:** (a) add a `normalization_version` (or per-loader parser-version) field to the consolidated
  workbook's `consolidation_meta` sidecar, bumped whenever a `tsn_load_*`/normalizer changes; (b)
  `status()`/`build_consolidated`/`_resolve_source` treat a missing/mismatched stamp as stale
  (fail-safe: absent ⇒ stale); (c) auto-rebuild from the retained `raw/` files when stale (raw is
  already kept); (d) a check script asserting a version bump invalidates a prebuilt library.
- **Verification:** offline check + re-bless the statewide canary (163,310) after rebuild.
- **Difficulty:** medium · **Timing:** before next release (ride-along for v0.18.5)

### BUG-03 — `consolidate_xlsx` doesn't filter `~$` Excel lock files → false PARTIAL on a healthy consolidation
- **Severity:** P1 · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/consolidate_xlsx_base.py:116` (`files = sorted(input_dir.glob("*.xlsx"))`); failure
  path :218-223 (append to `failed`) → :291 `incomplete=True` → :309 returns `completion=outcome.PARTIAL`.
- **Evidence:** every sibling reader already filters the lock stub — `consolidate_intersection_summary.py:214`,
  `tsn_library.py:112/251/392`, `compare_env.py:296`, `day_matrix.py:160`, `artifact_store.py:325`
  (which even comments "Excel lock file"). All 7 XLSX consolidators funnel through the unfiltered glob.
- **Why it matters:** having any per-route export open in Excel while consolidating produces
  "⚠ INCOMPLETE"; under the producer-owned completion contract a partial never promotes/caches/shows
  green — so a routine user action silently blocks the whole pipeline downstream.
- **Fix:** one line — `files = sorted(p for p in input_dir.glob("*.xlsx") if not p.name.startswith("~$"))`,
  matching the sibling idiom.
- **Verification:** extend `check_consolidate_outcome.py`: drop a `~$route.xlsx` stub into the input
  dir, assert completion stays COMPLETE.
- **Difficulty:** trivial · **Timing:** before next release

### BUG-04 — One-way mutual exclusion: a user task can collide with the background env-check on the single-instance Edge profile
- **Severity:** P1 · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/gui_api.py` (`_maybe_active_env_check` :942-957, `start_export` :1357),
  `scripts/task_coordinator.py` (`try_claim`/`claim_direct`/`take_next` :48-51 gate only on `self.task`),
  `scripts/gui_worker.py` (`ActiveEnvCheckWorker.run` :1325 → `new_authed_browser`),
  `scripts/session.py:29-31`, `scripts/edge_device.py:246-248, 266-273, 285-286`.
- **Evidence:** gui_api.py:942-943 declares "NEVER while another task or check is running … the Edge
  profile opens one at a time", but only the check side checks (`if self._task or self._active_check`);
  no claim path consults `_active_check` (grep: read/written only in `__init__`,
  `_maybe_active_env_check`, `_on_active_env_done`). edge_device.py itself documents "a persistent
  profile can only be open in ONE browser at a time … the classic field failure" with no wait/retry.
- **Why it matters:** the quiet check runs unprompted on app start and every env switch for up to
  ~20-60 s. In device-sign-in mode (no saved auth file — exactly the work-PC field configuration),
  clicking Export/Log-in/Check-all during that window makes a second `launch_persistent_context` on
  the same profile dir → the *user's* action fails with a browser-launch error for no visible reason.
  With a valid saved auth file both sides use plain contexts, so dev machines never see it.
- **Fix (simplest):** have the active check claim the real gate (`try_claim("activeenv")`, release on
  done). Behavior change: a user action during the check gets the normal "a task is already running"
  soft message instead of a crash. Alternative: coordinator-aware `_active_check` + a supersede Event
  the check polls between steps so user actions preempt it.
- **Verification:** offline lifecycle check: stub ActiveEnvCheckWorker as running, assert
  `start_export` returns busy instead of launching. Field: click Export within ~10 s of app start on
  the work PC.
- **Difficulty:** medium · **Timing:** before next release

### BUG-05 — Compare tab: a Browse…-picked custom folder permanently stomps the run-folder dropdown
- **Severity:** P1 · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/ui/app.js` (`fillCompareDirSelect` :1542-1545 restores `custom` **before** `prev`;
  `CMP_DIRS` declared :1521, written only at :1611 in `pickCompareFolder`, never cleared;
  `startCompare` :1616-1622 reads the select's live value).
- **Evidence:** re-renders fire on every `st.days` change (`renderDays` → `renderCompareDirs`,
  app.js:978) and on compare-kind/group changes (:351-354, :1506) — each re-render forces the select
  back to the custom path over the user's subsequent dropdown pick. The selects' `onchange`
  (:1875-1876) only calls `syncCompareButton`, so the user's pick is never persisted.
- **Why it matters:** after using Browse… once, picking a run folder from the dropdown silently
  reverts — the comparison runs against the stale custom folder. Wrong-input comparisons are the
  worst failure mode for this tool's purpose.
- **Fix:** clear `CMP_DIRS[side]` when the user changes the select (`onchange`), and/or add an
  explicit "(custom…)" option so the custom path is a *selection state* rather than a render
  override; restore `prev` (the user's pick) with priority over `custom`.
- **Verification:** `#mock`: Browse a folder, change the dropdown, trigger a state re-render
  (dispatch a `days` update), assert the select still shows the dropdown pick; then startCompare
  and assert the request carries it.
- **Difficulty:** easy · **Timing:** before next release

### BUG-06 — `release.yml` never runs the offline regression suite: a release can ship while checks are red
- **Severity:** P1 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Files:** `.github/workflows/release.yml`, `.github/workflows/checks.yml`
- **Evidence:** release.yml's steps: tag-vs-version check → release notes → `build.ps1 -SelfTest`
  (frozen self-test) → zips → `check_source_zip_smoke.py` → checksums → publish. The only check_*
  script it invokes is the source-zip smoke (line 92). The 78-check suite lives solely in checks.yml,
  a *parallel* workflow that a tag push does not wait on. This is the mechanism behind the v0.17.3
  post-mortem ("a subset let a red CI + a field crash ship").
- **Fix:** either (a) add the checks job as a `needs:` prerequisite job inside release.yml (dup the
  ~5 bash steps or call a shared composite action / the new run-all script from REL-01), or (b) gate
  on the checks.yml run for the same SHA via `gh run list`/commit-status API before building. (a) is
  simpler and hermetic.
- **Verification:** push a tag on a branch with an intentionally failing check in a fork/dry-run;
  release must red.
- **Difficulty:** easy · **Timing:** before next release

### BUG-07 — Falsy-zero `str(v or "")` still live in vs-TSN normalizers — including `norm_pm`, which feeds row-alignment keys
- **Severity:** P1 (latent) · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/compare_tsn_common.py:39` (`s = str(pm or "").strip()` in the shared `norm_pm`)
  and `:53` (`str(d or "")`); `scripts/compare_intersection_detail_tsn.py:175` (`_norm_control_type`
  token path), `:229`, `:555`; `scripts/compare_ramp_detail_tsn.py:77, 90, 105`.
- **Evidence:** grep verified this session. The same idiom in `_norm_num`/`_norm_bool` caused
  v0.18.3's 43 phantom Intrte-Postmile diffs (numeric 0 → `""`). `norm_pm` is used to build alignment
  keys for Ramp Detail and Intersection Detail: a source that ever delivers postmile as numeric
  `0`/`0.0` (instead of text `"0.000"`) will silently mis-align or one-side those rows.
- **Fix:** replace with the v0.18.3 idiom `("" if v is None else str(v))` at every remaining site.
  **Caution:** `norm_pm`/`_split_route` feed alignment keys — changing them shifts row pairing, so
  re-bless the statewide canary (163,310) and diff the comparison workbooks cell-for-cell on the real
  pairs before shipping (the v0.18.3 process). Rebuild the TSN library after (BUG-02 applies).
- **Verification:** unit rows with numeric-0 PMs through each normalizer in the respective
  `check_compare_*_tsn.py`; canary re-bless.
- **Difficulty:** easy (edit) / medium (re-bless) · **Timing:** next correctness release

### BUG-08 — An empty projection writes an "ok"/COMPLETE empty TSN normalized workbook
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Files:** `scripts/tsn_library.py` (`build_normalized` :418-…; no zero-row guard between
  `rows, make_result = project(str(raw))` :449 and writing/`make_result`), all four `tsn_load_*.py`.
- **Evidence:** the only failure paths are deps/no-raw/parse-exception. A raw workbook that parses
  but projects zero rows (e.g. TSN changes a sheet name or header layout non-fatally) yields a
  header-only normalized workbook with a success result — every comparison row then reads
  "Only in TSMIS" instead of an error.
- **Fix:** after projection, `if not rows: return ConsolidateResult(status="error", message=f"…parsed
  but produced 0 rows — the {log_label} layout may have changed…")` (or completion=PARTIAL if a
  zero-row statewide file can ever be legitimate — it can't).
- **Verification:** check: feed a structurally-valid-but-empty raw workbook, assert an error result
  and that no normalized file is written.
- **Difficulty:** easy · **Timing:** next correctness release

### BUG-09 — vs-TSN PDF parse path breaks the loader ValueError contract
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/compare_tsn_common.py:141-144` (`run_files_compare` catches only `ValueError`
  from loaders); `scripts/compare_ramp_summary_tsn.py:102-103` and
  `scripts/compare_intersection_summary_tsn.py:151-152` (`_load_tsn` returns `parse_tsn_pdf(path)`
  unwrapped, while the XLSX branch three lines later wraps into ValueError).
- **Why it matters:** a corrupt/truncated statewide TSN PDF escapes as a raw pdfplumber exception
  instead of the clean "could not read X" result — in the matrix path that turns a bad input file
  into an unhandled-error cell rather than a message.
- **Fix:** wrap the PDF branch in the same try/except → `raise ValueError(f"…: {type(e).__name__}: {e}")`
  as the XLSX branch, in both files.
- **Difficulty:** trivial · **Timing:** next correctness release

### BUG-10 — Unlocked task-gate reads in cancel/skip/pause; `cancel_event.set()` can race a matrix-queue job transition
- **Severity:** P2 · **Confidence:** medium-high · **Status:** CONFIRMED
- **Files:** `scripts/gui_api.py` (`cancel_run` :1664-1671 reads `self._task` via the unlocked property
  and sets `cancel_event` with no lock — against the locking contract the proxy docstring itself
  states at :501-505), `scripts/task_coordinator.py` (`_end_task` frees the gate and immediately
  starts the next queued matrix job on the pump thread).
- **Why it matters:** a Cancel clicked in the gap between job A ending and queued job B starting can
  set the cancel event that job B then consumes — canceling a job the user never targeted. Rare
  window, but it's the same shape as the v0.18.1 queue-phantom family.
- **Fix:** take the coordinator lock in cancel/skip/pause endpoints and no-op when `self._task is None`
  or the task id/kind doesn't match the one the UI targeted (pass the task token from the frontend —
  `contract.js` kinds already exist for this).
- **Verification:** extend `check_worker_lifecycle.py` with an end→cancel→start-next interleaving.
- **Difficulty:** medium · **Timing:** soon after release

### BUG-11 — `renderMatrix`/`renderDayMatrix` have no stale-response guard and run twice per run-end
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/ui/ui-matrix.js` (:487-491, :701-705 — `await api.matrix_info()` with no sequence
  token), `scripts/ui/app.js` (:1219-1220 `run_ended` and :1223-1224 `matrix_refresh` each trigger both).
- **Why it matters:** two concurrent awaits per completion; the older snapshot can resolve last and
  win, re-painting a stale matrix (another cousin of the queue-phantom family).
- **Fix:** a monotonically-increasing render token per renderer (`const seq = ++matrixRenderSeq;`
  … `if (seq !== matrixRenderSeq) return;`), and/or coalesce the double dispatch.
- **Verification:** `check_mx_partial_render.js`-style Node test injecting delayed fake responses.
- **Difficulty:** easy · **Timing:** soon after release

### BUG-12 — `matrix.comparison_state` (env mode) drops the persisted `completion` flag
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Files:** `scripts/matrix.py` — `record_result` :127-134 persists `completion` ("P1-R01: partial
  inputs flagged durably"); the TSN-mode reader `_cmp_state` :541 reads it back
  (`rec.get("completion", outcome.COMPLETE)`) and returns it :556; the env-mode reader
  `comparison_state` :241-294 returns verdict/diff_cells/one_sided but **no `completion` key** (:292-294).
- **Why it matters:** a comparison built from PARTIAL inputs is durably flagged when recorded, and
  surfaced in TSN rows, but on reuse an env-mode cell can render as a full green match — precisely
  what P1-R01/`check_mx_partial_render.js` exist to prevent, on the other row mode.
- **Fix:** mirror `_cmp_state`: read `completion` under the same `rec_trusted` gate and include it in
  the returned dict; confirm `mxCellContent` consumes it for env cells.
- **Verification:** extend `check_matrix.py` with a PARTIAL-completion record and assert the env-mode
  snapshot carries it.
- **Difficulty:** trivial-easy · **Timing:** soon after release

### BUG-13 — Updater phase 2 is not hard-crash-safe, and `cleanup_leftovers` then deletes the recovery pieces
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Files:** `scripts/updater.py` — phase-2 rename loop :881-897 (per-piece `live→.old`, `.new→live`),
  rename-based rollback for *handled* failures :899-918 (good), `cleanup_leftovers` :1095-1115
  (unconditionally removes every `*.old`/`*.new` bundle piece on the next GUI launch).
- **Evidence/why:** a hard interruption (kill, power loss) mid-loop leaves a mixed tree; the narrow
  window where `dest` is renamed to `.old` but `.new` not yet renamed in leaves that piece *missing*.
  If the app still launches, `cleanup_leftovers` deletes the `.old` copies — destroying the only
  rollback material. Handled-failure rollback is solid; only the unhandled-interrupt path is exposed.
  (The documented v0.10.2 field failure shows updater edge cases do occur on managed PCs.)
- **Fix:** write a tiny `swap.inprogress` journal (list of pieces + phase) before phase 2 and remove
  it on success; on next launch, if present, *complete or roll back* from `.old`/`.new` instead of
  deleting them (the pieces are self-describing). Keep `cleanup_leftovers`' delete only when no
  journal exists.
- **Verification:** extend `check_updater.py`: simulate an interrupt after k renames against a fake
  tree; assert next-launch recovery restores a coherent version, both directions.
- **Difficulty:** medium · **Timing:** soon after release

### BUG-14 — Log rotation is not multi-process safe (silent record loss after 2 MB)
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/logging_setup.py:31, :117-119` (shared `tsmis.log`, `RotatingFileHandler
  maxBytes=2_000_000, backupCount=5`); shared by GUI + console + login entry points
  (cli.py:151/242/359, login.py:34, gui_main.py:187) via the same `LOG_DIR`.
- **Why it matters:** two processes (e.g. GUI open + a console .bat run) each hold the file; when one
  rotates, Windows rename fails or the other process keeps writing to the renamed inode — subsequent
  records from one side are silently dropped. Undermines the log-first debugging contract exactly in
  mixed console/GUI sessions.
- **Fix (smallest):** per-process log filenames (`tsmis-<pid>.log` or `tsmis-gui.log`/`tsmis-cli.log`)
  with the same rotation, and have `evidence.py` bundle the family glob. Avoid adding a dependency
  (concurrent-log-handler) — work-PC constraint favors stdlib.
- **Difficulty:** easy · **Timing:** soon after release

### BUG-15 — `day_matrix._folder_newest_mtime` single try around the whole scan
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- `scripts/day_matrix.py:155-166` wraps the whole iterdir/stat fold in one `except OSError: pass`;
  `:258-260` sets `export.present` from that return and `:189/:287` gate available-days and
  consolidation state on it — so one transiently-locked file can mark a day's export "not present".
  Fix: move the try inside the per-file loop.

### BUG-16 — `paths._writable` fixed probe filename race
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- `scripts/paths.py:31-40` writes a fixed `directory/".write_test"` probe and treats ANY OSError as
  not-writable; `_resolve_data_root` (:48-58) then silently falls back to `%LOCALAPPDATA%`, and
  DATA_ROOT resolves once at import (:62) with no single-instance guard — two concurrent frozen
  launches can race the probe and silently split DATA_ROOT. Fix: pid-suffix the probe name.

### BUG-17 — 8-char border color `"BFBFBFBF"` (intended `BFBFBF`)
- **Severity:** P3 · **Confidence:** high · **Status:** SELF-VERIFIED
- `scripts/consolidate_ramp_summary.py:510` — `Side(style="thin", color="BFBFBFBF")` sets alpha 0xBF
  instead of opaque. One-char fix; cosmetic.

---

## B. Error handling & logging

### LOG-01 — ~25 silent exception swallows violate the project's own "every swallow logs type+message" contract
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED (gui/tsn/compare sites) + SELF-VERIFIED (export/auth sites)
- **Files & sites:**
  - `scripts/gui_worker.py:150-151, 166-167` — `reset_targets`: a failure enumerating the
    Export-Everything store **silently drops it from the delete-all target list** (preview and delete
    both omit it; user believes everything was removed). The worst of the family.
  - `scripts/gui_api.py:403-405` (fast_workers fallback), `:923-925` (`_maybe_autoscan` — a settings
    failure silently disables autoscan forever), `:2598-2600` (devtools toggle).
  - `scripts/gui_worker.py:1099-1101, 1335-1338` (browser.close() swallows — contrast
    `LoginWorker._safe_close` :1580-1585 which logs correctly; reuse it).
  - `scripts/gui_worker.py:1199-1202` (`check_one` page.evaluate).
  - `scripts/tsn_library.py:107-114 (_raw_files → return []), :100-104 (_safe_mtime), :255-256,
    and four sites in ensure_layout` — an unreadable raw/ dir reports "no raw files — import first"
    with zero log trail.
  - `scripts/compare_intersection_detail_tsn.py:587-590, 612-615` (`_tsn_onesided`,
    `_tsmis_locations`) — unreadable input silently degrades the Report View; **the module has no
    logger at all** (zero `getLogger` in the file).
  - `scripts/logging_setup.py:61-65` `_enable_faulthandler` bare swallow — CONFIRMED (round 3);
    setup_logging attaches the rotating handler at :137 *before* calling it at :142, so logging IS
    available at the swallow point.
  - `scripts/exporter.py:128-129, 160-161, 401-402`, `scripts/auth_nav.py:141-142, 298-299`,
    `scripts/report_nav.py:303-304`, `scripts/login.py:234-235, 242-243` — audit each; most are
    cleanup paths that still deserve the one-line idiom.
- **Fix:** apply the house pattern (`log.info("<step> skipped (%s: %s)", type(e).__name__,
  str(e).splitlines()[0] if str(e) else "")` — see gui_api.py:250-252). For `reset_targets`,
  log at WARNING **and** surface "store could not be inspected" in the reset preview. Then add a
  tripwire check (grep-based `check_silent_swallows.py`) allowing only an explicit allowlist of
  documented last-resort sites.
- **Difficulty:** easy (mechanical) · **Timing:** next correctness release

---

## C. Security / privacy / data handling

*(Context: single-user desktop tool, but the repo is public on GitHub and logs/evidence bundles get
shared for support.)*

### SEC-01 — `.gitignore` misses two sensitive dev-written artifacts at the repo root
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Evidence:** `settings._backup_corrupt_config` (settings.py:97-100) writes `config.json.corrupt`
  next to config.json (dev = repo root; only `/config.json` is ignored). `evidence.build_bundle`
  (evidence.py:222) defaults to `DATA_ROOT/tsmis_evidence_<ts>.zip` — dev DATA_ROOT is the repo root.
  `git check-ignore config.json.corrupt tsmis_evidence_test.zip` → not ignored (exit 1).
- **Why:** the corrupt-config backup carries site URLs/paths; the evidence zip carries logs and
  machine info. One `git add -A` from publishing them.
- **Fix:** add `/config.json.corrupt`, `/data/config.json.corrupt`, `/tsmis_evidence_*.zip` (the
  `/data/` blanket already covers packaged). 2 minutes.

### SEC-02 — "Delete all reports" legacy name-fallback trusts bare folder names under the user-chosen store
- **Severity:** P3 (downgraded from P2) · **Confidence:** high · **Status:** SELF-VERIFIED with correction
- **Evidence:** gui_worker.py:143-149 — the ownership marker (`owned_dir.is_owned`) is correctly
  preferred; the *fallback* accepts any child named `<src>-<env>`/`comparisons` (pre-marker legacy),
  and `_tsn_input` (:163) is taken purely by name. A user folder named exactly `ssor-prod` inside
  their chosen destination would be swept into the delete list (it does appear in the preview first,
  which is why this is P3 not P2).
- **Fix:** stamp legacy dirs with the marker on first sight (one-time migration in `reset_targets`
  or batch start), then drop the name fallback after a version or two; require the marker for
  `_tsn_input` deletion too.

### SEC-03 — `settings.py` logs setting VALUES at INFO into the logs both support bundles ship
- **Severity:** P3 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Evidence:** settings.py:303 (`site url %s -> %s`), :334 (`batch_dest -> %s`) — custom intranet
  URLs and user paths (often containing the username) flow into `tsmis.log`, which the evidence
  bundle includes; this undercuts the bundle's own settings-allowlist design.
- **Fix:** log key + changed/default status, not the value (or redact the user-profile prefix).

### SEC-04 — Saved-login ACL hardening covers `tsmis_auth.json` but not the Edge sign-in profile
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- auth_nav.py:76-137 tightens the auth file's ACL (`icacls /inheritance:r /grant:r` on the temp
  before `os.replace`), while edge_device.py:108 and :250 create `EDGE_LOGIN_PROFILE_DIR` with a
  bare `mkdir` — that profile's Cookies DB holds the same live TSMIS/Azure session the auth-file
  hardening protects. Apply the same owner-only ACL at profile creation.

### SEC-05 — Updater residual TOCTOU between digest verification and the swap copy
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- The trust record is written beside the staged tree in user-writable UPDATE_DIR (updater.py:418);
  the whole-bundle digest re-verify runs only in the trusted process pre-launch (:660-671), and
  `perform_swap` then waits up to `_SWAP_TIMEOUT_S = 120` (:609, :828) before copying with only an
  exe-existence check. Low practical risk (local attacker required); re-verify the digest inside
  `perform_swap` before phase 1 if cheap.

### SEC-06 — JS-bridge endpoints accept arbitrary unvalidated path strings
- **Severity:** P3 · **Confidence:** high · **Status:** SELF-VERIFIED
- `gui_api.set_batch_dest` (:1536-1541) and `gui_matrix.set_matrix_tsn_file` (:580-587) accept any
  string; the picker endpoints exist but are bypassable. Practical risk is low (the webview runs
  local trusted UI), but `settings.set_batch_dest` should validate existence/writability and reject
  UNC/device paths, since SEC-02's deletion logic later operates under this path.

---

## D. Performance & memory

### PRF-01 — Report View rollup does 2–4× redundant work on the largest report
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Files:** `scripts/compare_intersection_detail_tsn.py` (`_write_report_view` :644-…),
  `scripts/compare_core.py` (`run_compare` :1758-1765 already computes pairing/union;
  `extra_sheet_writer` ctx :1878-1883 passes only rows/schema/sides).
- **Evidence:** the writer re-computes `keys_for`/`pair_occurrences_by_similarity`/`union_keys` that
  `run_compare` just produced, evaluates every cell twice, allocates ~3 openpyxl style objects per
  cell, and `_tsn_onesided`/`_tsmis_locations` re-read both source workbooks per flavor.
- **Why:** this is the exact "silent rollup looks frozen" hot path that produced v0.18.2's field
  complaint; halving it shrinks the cancel-latency window materially on ~17k-row unions.
- **Fix:** extend the `extra_sheet_writer` ctx (an **additive** field — compare_core output
  untouched) to carry the computed pairing/union; hoist shared `Font`/`PatternFill` objects to module
  constants (openpyxl styles are immutable and shareable); cache the two side-workbook reads across
  flavors within one run.
- **Verification:** byte-identical output on the real pair (regression-lock procedure) + wall-clock
  before/after on the statewide pair.
- **Difficulty:** medium · **Timing:** soon after release

### PRF-02 — Filesystem I/O inside the shared lock on every state push; rglob size-scan on every `get_settings`
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- `gui_api._state_snapshot` holds `self._lock` (:330) while calling `list_output_days()` (:344 →
  paths.py:181-187 iterdir) and `_login_states()` (:359 → :372-378 stat + profile iterdir) — and
  `_push_state` has ~70 call sites, so every push does directory I/O under the shared RLock.
  `_chromium_state` (:2124-2131) sums `rglob("*")` sizes; `get_settings` calls it (:2157) and
  `_on_chromium_done` (:2296, dispatched on the pump thread via contract.Msg.CHROMIUM_DONE :208)
  runs the multi-thousand-file rglob while worker messages queue. Fix: cache the browser size
  (invalidate on download/delete) and move fs reads out of the lock.

---

## E. Architecture & module boundaries

### ARC-01 — The function-level lazy-import idiom is pervasive (156 sites) and already caused a shipped P1
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Evidence:** 156 function-level `import`/`from … import` statements across `scripts/`
  (gui_worker.py 21, matrix.py 19, updater.py 9, self_test.py 8, gui_main.py 7 …). Three in matrix.py
  are explicitly cycle workarounds: `:335 "lazy: no import cycle"`, `:904 "lazy (avoid import
  cycle)"`, `:986 "lazy (avoid import cycle)"`. BUG-01 is the direct casualty: the import lives
  inside one function (:166) and a later function assumed module scope.
- **Why:** two distinct motivations are mixed — (a) keeping heavy deps (openpyxl/pdfplumber/playwright)
  off the GUI-startup path (legitimate), and (b) hiding real dependency cycles around
  `matrix ↔ reports ↔ tsn_library ↔ paths` (debt). Every (b) site is a place where module-load-order
  bugs like BUG-01 can hide, and none of the existing layer checks (`check_import_direction`,
  `check_engine_layers`) cover the GUI/matrix layer.
- **Fix:** (1) inventory the 156 sites; convert cycle-driven ones by extracting the shared bits
  (e.g. `stamped_consolidated_filename` out of `paths` into a leaf, or matrix's report metadata
  needs into `report_catalog`) so the imports can be top-level; keep heavy-dep laziness but funnel
  it through per-module `_lazy_openpyxl()`-style helpers so a name is never used outside the
  function that imported it; (2) extend `check_import_direction.py` to assert the matrix/GUI layer
  ordering and to fail on a bare in-function `from openpyxl import …` whose name is used elsewhere
  in the module (cheap AST pass).
- **Difficulty:** medium · **Timing:** cleanup version

### ARC-02 — GUI backend files at 3.3×/2.5×/1.4× the 800-line standard
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** `gui_api.py` 2622 (class `GuiApi` ~2380 lines), `gui_worker.py` 2005, `gui_matrix.py`
  1086. The mixin extraction pattern is already established and working
  (`class GuiApi(GuiMatrixMixin)` :178; section bands at :1203 "one-click update", :2098 "settings &
  maintenance").
- **Fix (mechanical, verbatim moves):** repeat the `GuiMatrixMixin` pattern — `GuiSettingsMixin`
  (gui_api.py ~:2098-2553), `GuiUpdateMixin` (~:1203-…), `GuiCompareMixin`; split gui_worker.py by
  worker class (`ExportWorker` ~301 lines, `EnvScanWorker` ~263, `LoginWorker` ~248, `BatchWorker`
  ~171 → `gui_worker_export.py`, `gui_worker_env.py`, …) with `gui_worker.py` as the re-export shim
  (the `common.py` precedent). `check_gui_api_surface.py` locks the endpoint surface across the move.
- **Difficulty:** medium (mechanical but wide) · **Timing:** cleanup version

### ARC-03 — `matrix.py` (1195 lines) duplicates its staleness logic across the two row modes
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED (duplication + size; see BUG-12 for the behavioral edge)
- **Evidence:** `comparison_state` :241-294 and `_cmp_state` :521-556 hand-synchronize the same
  `rec_trusted`/mtime-tolerance/newer-side logic (identical lines at :270 and :533); `_MTIME_TOL_S`
  is separately duplicated in consolidation_meta.py:39 ("match matrix's float-mtime equality
  tolerance") — see DED-03.
- **Fix:** extract one `_staleness(rec, cmp_m, sides…) → (stale, reason, trusted_rec_fields)` used by
  both readers (fixes BUG-12 in passing); then split matrix.py roughly into `matrix_state.py`
  (freshness/snapshot), `matrix_build.py` (cell build + formulas twin), keeping `matrix.py` as facade.
- **Difficulty:** medium · **Timing:** cleanup version

### ARC-04 — `compare_core.py` (1960) internal structure: five writer functions at 99–302 lines; cell-comparison semantics triplicated
- **Severity:** P3 (locked output makes this low-urgency) · **Confidence:** high · **Status:** SELF-VERIFIED sizes; triplication CONFIRMED (round 3)
- **Evidence:** `_write_summary` ~302 lines, `run_compare` ~274, `_write_spot_check` ~235,
  `EnvCompare` ~238 (compare_env.py). The TRIM+context+ditto+"Med Wid" cell-equality semantics are
  hand-synchronized in three verified places: `_row_diff_count` (compare_core.py:382-390), the
  `count_diffs` inner loop (:523-531), and `_field_value` (:719-727, which re-orders the sequence
  for display coalescing).
- **Fix:** *only* behind the regression lock: extract a pure `cell_equal(schema, col, a, b)` helper
  used by all three sites and prove byte-identity on the locked pairs (the check suite +
  `%TEMP%\tsmis_regress` harness exist for exactly this). Do not split the file for its own sake.
- **Timing:** cleanup version, bundled with any next compare_core change

### ARC-05 — `settings.py`: 17 ad-hoc keys outside the validated DEFAULTS registry, each a hand-rolled ~15-line get/set pair
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** DEFAULTS (:35-47) covers 11 clamped scalar knobs with KeyError-on-typo protection;
  the other 17 keys (site_urls, batch_dest, matrix_row_modes, tsn files, fast flag, …) each repeat
  the `dict(_read_file()) → mutate → _write_file` read-modify-write block (~350 lines total, e.g.
  `set_matrix_fast` :584-594 verbatim-identical shape to its 16 siblings).
- **Fix:** a small key registry (`name → default, validate/clamp, redact-in-logs?`) + generic
  `get_extra(key)`/`set_extra(key, value)`; keep the existing public function names as one-liners
  (no caller churn). The `redact` flag also solves SEC-03.
- **Difficulty:** easy-medium · **Timing:** cleanup version

---

## F. Duplication (copy-paste families)

### DUP-01 — Comparator family: 3 modules never migrated onto `compare_tsn_common.run_files_compare`
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** compare_tsn_common.py's own docstring (:1-25) declares itself "that shared skeleton",
  yet `compare_highway_log.py`, `compare_highway_log_pdf.py`, and (one more legacy flavor) still
  carry the pre-P5b hand-rolled `compare()` skeleton; plus **6 copies of `suggest_name`**, 3 of the
  consolidated-workbook loader skeleton, ~11 of the row-emptiness predicate across the family.
- **Fix:** migrate the 3 stragglers onto `run_files_compare` (the P5b pattern), move `suggest_name`
  and the row-emptiness predicate into compare_tsn_common. Output must stay byte-identical — the
  per-family `check_compare_*` goldens already lock this.
- **Difficulty:** medium · **Timing:** cleanup version

### DUP-02 — PDF-consolidator family: parser internals duplicated 2–3× with four divergent `_norm_route` copies
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** `_assign_columns` body-identical between consolidate_tsmis_highway_log_pdf.py:250-265
  and consolidate_tsmis_intersection_detail_pdf.py:209-224 (one trailing `.strip()` differs — i.e.
  they have *already* drifted); the char-clusterer exists 3× (highway_log_pdf `_cluster_lines`
  :160-183, tsn_highway_log `_lines` :229-257, intersection_detail_pdf); the ~150-line convert-loop
  driver exists 2-3×; `_norm_route` has four divergent copies. Also `consolidate_xlsx` itself is ~230
  lines mixing gate/validate/confirm/lock-in/append/save/summary (:81-310).
- **Fix:** extract `scripts/pdf_table_lib.py` (cluster, assign-columns, route-normalize) + one
  convert-loop driver parameterized like `tsn_library.build_normalized` already is for the
  normalizer family (the in-repo precedent). Reconcile the four `_norm_route`s deliberately — the
  divergence is itself a latent-diff source.
- **Difficulty:** medium-hard (parser goldens exist: check_tsmis_pdf_parse/reconcile, pdf_row_oracle)
  · **Timing:** cleanup version

### DUP-03 — Eleven near-identical "claim gate → clear events → announce → start worker" endpoint blocks + the dialog-unwrap idiom ×8
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** verifier matched the ~7-step tail across all 11 claiming endpoints (start_login,
  verify_environment, check_environments, start_export, retry_failed, start_reset,
  rebuild_tsn_library, …); the `_run_dialog`-result unwrap repeats 8×.
- **Fix:** a `@_task_endpoint(kind, worker_factory)` decorator (or `_start_task(kind, make_worker)`
  helper) in gui_endpoint.py; BUG-04's gate fix should land inside it so exclusion is enforced in
  exactly one place.
- **Difficulty:** easy · **Timing:** cleanup version (or with BUG-04)

### DUP-04 — Frontend: Pause/Skip/Cancel sync copy-pasted 4×; two ~50-line progress-renderer twins; five hand-maintained lock-ID lists
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** pause icon/label sync at ui-matrix.js:45-48, :1000-1003, app.js:540-542, :550-552;
  `updateMatrixProgress` (ui-matrix.js:11-58) vs `updateDayMatrixProgress` (:964-1013) near-twins;
  `renderState` (app.js:423-594) applies task-locking through five separate hand-maintained ID
  arrays (:502-505, :507-510, :560-563, :576-577, +compare lists) — a pattern the code itself
  documents as having drifted before.
- **Fix:** one `syncRunButtons(prefix, st)` helper; one parameterized progress renderer; replace the
  five ID arrays with a `data-lock-when-busy` attribute in index.html swept by a single
  `querySelectorAll` (new IDs then lock by construction).
- **Difficulty:** easy-medium · **Timing:** cleanup version

---

## G. Frontend structure & UX

### FE-01 — `app.js` 2019 / `mock.js` 1396 / `ui-matrix.js` 1013 lines; `bindEvents` 278 lines; four renderers >145 lines
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** wc -l verified; `bindEvents` app.js:1640-1917; `renderState` :423-594. The ui-*.js
  split pattern (classic scripts sharing app.js's global scope, load-ordered in index.html:1022-1026)
  already exists — app.js just never finished migrating.
- **Fix:** continue the established split: `ui-compare.js` (compare tab: fillCompareDirSelect,
  startCompare, CMP_DIRS…), `ui-export.js` (preflight/run/queue), `ui-batch.js`; break `bindEvents`
  into per-tab `bind*` functions; keep app.js = state + boot + dispatch (<800).
- **Difficulty:** medium (mechanical; `#mock` + check_ui_boot.js verify) · **Timing:** cleanup version

### FE-02 — `mock.js` still emits matrix completion events in the inverted order that hid the v0.18.4 bug
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- **Evidence:** mock.js:408-412 (`mockTryStartNext`) pushes `state` **before** `run_ended`/`matrix_refresh`;
  the real backend emits `run_ended` → `state` (gui_api.py:683-684 `_end_task`) → `matrix_refresh`
  (gui_matrix.py:1051/1086). This exact inversion is why the queue-phantom "reproduced only by
  replaying the real order" (v0.18.4 lesson, now recorded in docs/gui.md).
- **Fix:** reorder the mock emission to `run_ended → state → matrix_refresh` everywhere a task ends;
  add `check_mock_event_order.js` that extracts both sequences (regex over gui_api/gui_matrix `_emit`
  order and mock.js) and fails on divergence — the mock can never silently diverge again.
- **Difficulty:** easy · **Timing:** next correctness release

### FE-03 — Modals: no focus trap, no `role=dialog`/`aria-modal`
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- ui-dom.js `openModal`/`buildModal` (:185-210) — Tab walks out of an open modal into the background
  UI; only a global Esc handler exists (app.js:180-181). Fix: role/aria attributes + a ~15-line
  focus-trap keydown in `openModal` (or migrate to `<dialog>`, WebView2 supports it).

### FE-04 — Route-picker cells and tab bars are mouse-only
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- ui-dom.js:280-287 builds route cells as bare `div`s with only `onclick`; exactly two keydown
  listeners exist in the whole UI, neither covering pickers/tabs. Fix: `tabindex="0"`,
  `role="button"`/ARIA tabs pattern, Enter/Space handlers. (Desktop-tool audience makes this P2
  polish, but it's also cheap.)

### FE-05 — `contract.js` is consumed only by mock.js; the real UI hardcodes every task-kind string
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- Repo-wide grep: `window.CONTRACT` is read only by mock.js:596; the real UI carries ~17 literal
  `task ===`/`!==` comparisons (app.js:514/536-585/1202, ui-matrix.js:33/40/987/994,
  ui-settings.js:121/173) against contract.js's own stated purpose (:5-8). Sharper risk: 
  `check_ui_contract.py` locks contract.js↔mock.js to the Python enums but never inspects
  app.js/ui-*.js — after a task-kind rename the check goes green while the render logic's stale
  literals silently misrender. Fix: use `CONTRACT.*` in the real UI and extend the check.

### FE-06 — Dead CSS selectors
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3, with one correction)
- `.auth-status` (app.css:282) and `.dm-tsn` (:1040) — sole occurrences repo-wide (markup uses
  `.auth-cluster`). `.mc-mode.on` (:973) — the buttons exist (index.html:920-921) but nothing ever
  adds class `on`, so the designed active state never shows (possibly a latent UI bug rather than
  dead CSS — check intent before deleting). Correction: `.set-radios.hidden` (:1322) IS matched at
  runtime (ui-settings.js:135/151) but is a no-op duplicate of the global
  `.hidden { display:none !important }` (:102) — delete as redundant, not unmatched. Keep
  `.mc-group[hidden]` (the v0.18.4 fix) as the pattern.

### FE-07 — No cache-busting on `app.css`/`app.js` references
- **Severity:** P3 · **Confidence:** high · **Status:** SELF-VERIFIED
- index.html:26 `<link rel="stylesheet" href="app.css">` (scripts likewise, :1022-1026). The
  documented recurring dev trap (browser HTTP-caches JS/CSS across server restarts); the packaged
  app already clears WebView2 caches on swap (updater.cleanup_leftovers), so this is dev-loop-only —
  fix by appending `?v=<version.py>` at GUI boot (gui_main serves index; can inject) or documenting
  the fetch-reload recipe in gui.md (see DOC-07).

### FE-08 — `S`'s runtime shape drifts from its declaration; `renderPreflight` re-renders on every body input with no debounce
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- The S literal (app.js:22-35) omits `etaSmoothed`, `curEnvKey`, `stepsSig`, `consDropped`,
  `consInputDir`, `_tsnRebuildPending` (assigned ad hoc from app.js and ui-settings.js); the
  body-wide change/input listeners (app.js:1757-1758) call `renderPreflight` with no debounce while
  the routes input has its own 200 ms debounce (:1249-1252); the guard (:690) tests only the
  `.hidden` class, wrong in matrix mode. Fix: declare all fields in the S literal; debounce
  preflight (~100-200 ms) to match the routes input.

---

## H. Consolidators & parsers (beyond BUG-03/BUG-08)

### CON-01 — Oversized parser/driver functions
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- `consolidate_xlsx` :81-310 (~230); highway_log_pdf `parse_pdf` :285-414 + `consolidate` :457-629;
  ramp_summary `parse_pdf` ~159/`build_combined_sheet` ~151/`build_workbook` ~145;
  tsn_highway_log `consolidate` ~153/`out_path_for` ~128. Fold into DUP-02's extraction rather than
  splitting in place.

### CON-02 — Stale cancel-semantics docstrings and dead parameters in the PDF consolidators
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- `consolidate_tsn_highway_log.py` `parse_pdf` docstring claims "Raises RuntimeError on cancel" but
  the body returns `(district, None)`; `consolidate_tsn_highway_sequence.py:149-150` is
  self-contradictory ("Raises on cancel (returns (None,) sentinel…)"); `pdf_name` unused,
  `total_rows` accumulated but never reported. Clean up with DUP-02.

### CON-03 — `consolidate_tsn_highway_log` lacks the `converted_dir` override its two TSMIS-PDF siblings have
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- `consolidate(events, confirm_overwrite, day, input_dir, out_path)` (:430-431) has no
  `converted_dir`; `:484-496` always mkdir + clears stale `tsn_highway_log_*.xlsx` in the module
  constant `CONVERTED_DIR = OUTPUT_ROOT / "tsn_highway_log"` (:77), so TSN-library builds scatter
  and clear scratch in the fixed output folder. Add the parameter for symmetry.

---

## I. Build / release / updater / versioning

### REL-01 — Release-gate integrity cluster (with BUG-06)
- **Severity:** P1 (as a cluster) · **Confidence:** high · **Status:** CONFIRMED + SELF-VERIFIED
- **Three related gaps:**
  1. **BUG-06:** release.yml doesn't run/require the 78-check suite (see above).
  2. **No completeness guard:** checks.yml enumerates all 78 checks by hand (42 direct lines + a
     33-name bash for-loop + 3 node steps). Ground truth this session: currently complete (78/78
     referenced) — but nothing prevents a new `check_*.py` from silently never running. Add
     `build/check_ci_manifest.py`: glob `build/check_*.{py,js}`, parse the three workflow files,
     fail on any check absent from checks.yml (and run it in checks.yml — self-hosting).
  3. **No local runner (#60):** the canonical blocking list lives only inside checks.yml bash steps;
     docs document only one-at-a-time invocation. Add `build/run_checks.py` (stdlib; enumerates the
     same globbed list, honors the same env, parallelizes with `-j`, prints a summary) and make
     checks.yml call *it* so the list exists in exactly one place. This also fixes the
     memory-documented release-gate lesson ("run EVERY check CI-style") structurally.
- **Difficulty:** easy · **Timing:** before next release

### REL-02 — checks.yml regression-tests against floating transitives, not the hash-locked tree releases build from
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- checks.yml:34-38 `pip install -r requirements.txt` (5 direct pins; transitives like
  pythonnet/clr_loader float) vs build.ps1:53-55 `pip install --require-hashes -r
  requirements-build.lock.txt` (Windows+CPython-3.11 hash lock). A transitive bump can make CI green
  and the frozen build differ. Fix: install the lock in checks.yml (drop build-only extras if
  install time matters). Note: the lint tools themselves are also unpinned (checks.yml:38
  `pip install ruff bandit pip-audit`).

### REL-03 — README version badge hardcoded, 4 releases stale
- **Severity:** P2 (public face) · **Confidence:** high · **Status:** SELF-VERIFIED
- README.md:5 says `version-0.18.0` vs version.py `0.18.4`. Fix: point the badge at the GitHub
  releases shield (`img.shields.io/github/v/release/<owner>/<repo>`) so it can never go stale, and
  add a README feature-section refresh to the release checklist (see DOC-02).

### REL-04 — build.ps1 doesn't assert CPython 3.11 for the build venv
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- build.ps1:49 creates the venv with bare `python -m venv` (PATH interpreter) despite the script's
  own "Proven on Windows + Python 3.11" header and the lock's "Windows + CPython 3.11 ONLY"
  declaration (requirements-build.lock.txt:5-7). 3 lines
  (`if (-not ($v -match '^3\.11\.')) { throw … }`) before venv creation.

### REL-05 — backfill_release_notes.ps1 ignores gen_release_notes.py's exit code
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- `:32-34` runs `python build\gen_release_notes.py $tag -o $tmp` then proceeds straight to
  `gh release edit --notes-file` with no `$LASTEXITCODE` check — and
  `$ErrorActionPreference = "Stop"` (:15) does NOT stop on a native command's nonzero exit in
  Windows PowerShell 5.1, so a generation failure would blank a release's notes. Check
  `$LASTEXITCODE` after the call.

### REL-06 — ~~SignPath wiring covers only the win64 zip~~ — **REFUTED (round 3): deliberate, documented decision**
- **Status:** REFUTED · retained for the record
- The facts hold (release.yml:101-119 signs only the win64 zip; the with-browser pair is a
  comment-level TODO), but the verifier found this is an explicitly adjudicated design decision —
  docs/roadmap.md:512-515 lists the exact remaining rollout sequence, and SIGNPATH_ENABLED is off.
  Not a defect; it becomes actionable only when signing is turned on (the roadmap already says so).

---

## J. Tests / check coverage

### TST-01 — Five new checks that lock the field-bug classes that actually escaped
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED (gap analysis run this session)
- **Ground truth:** the 78-check suite is broad — an inverse-map scan found only **3 modules with
  zero check references: `gui_endpoint.py` (the decorator wrapping every endpoint!), `gui_main.py`,
  `logging_setup.py`**. The bigger systemic gap is *fidelity*, not breadth: BUG-01 shipped because
  no check executed `_comparison_row_count` against a real workbook, and the v0.18.4 queue-phantom
  hid because the mock's event order diverged from production.
- **The five checks, in value order:**
  1. `check_formulas_twin_guard.py` — real xlsx through `_comparison_row_count` + a >limit workbook
     through `_try_formulas` asserting the skip fires (catches BUG-01 today, and any regression).
  2. `check_mock_event_order.js` — assert mock.js emission order == backend `_emit` order (FE-02).
  3. `check_tsn_freshness.py` — once BUG-02 lands: a version-stamp bump must invalidate a prebuilt
     library; an unstamped library must read as stale.
  4. `check_silent_swallows.py` — AST/grep tripwire for `except:`-swallows without a log call,
     against an explicit allowlist (locks LOG-01's cleanup).
  5. `check_gui_endpoint.py` — direct tests of the `_api_method` envelope (error wrapping, emit
     fallback) — the one load-bearing zero-coverage module.
- **Also (DX):** each check hand-rolls `sys.path.insert` + `_fail`-list + fake Events; a tiny
  `build/_checklib.py` (path setup, `fail()/summary()`, `FakeEvents`, temp-dir ctx) would cut ~15
  lines per new check and make writing them cheaper — add opportunistically, don't retrofit all 78.

---

## K. Docs / onboarding / DX

### DOC-01 — `docs/planning/` (the whole v0.18.0/v0.18.1 planning + handoff corpus) is neither tracked nor ignored
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- `git status` shows `?? docs/planning/`; `git check-ignore` says not ignored. These are the
  canonical multi-phase plans and field-findings handoffs (referenced from session memory) — one
  `git clean -fd` from being lost, and permanent status noise meanwhile. **Decide:** track them
  (recommended — they quote no local-only data by policy; verify once before committing) or add
  `/docs/planning/` to .gitignore with an archival copy elsewhere.

### DOC-02 — README body is 4 releases stale
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- Beyond the badge (REL-03): the feature/usage sections predate the matrices, TSN library,
  Everything tab, and the self-updater — the public face undersells the actual product. Refresh
  alongside the next release; regenerate the two screenshots via `tools/screenshots.py`.

### DOC-03 — `docs/verification-and-testing.md` documents 45 of 78 checks
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED (45 unique `check_` names in the doc vs 78 on disk)
- The whole v0.18.0 outcome/artifact/contract check family is undocumented. If REL-01's `run_checks.py`
  lands, replace the hand-list with "run `python build/run_checks.py`; the list is the glob" + a
  short taxonomy table.

### DOC-04 — `frozen-gate.yml` is documented nowhere in the tracked library
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED (grep: only untracked docs/planning mention it)
- docs claim CI = checks.yml + release.yml. One paragraph in docs/build-and-release.md (what it
  builds, when it runs, the `frozen-gate` PR label trigger).

### DOC-05 — CLAUDE.md repo-layout omissions
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- The layout section lists neither `matrix.py`, `day_matrix.py`, `tsn_library.py`, `tsn_load_*.py`,
  nor `summary_layout.py` — five load-bearing engine modules invisible to any agent routed by
  CLAUDE.md. Add one line to the layout block.

### DOC-06 — No `pyproject.toml`/ruff config in-repo
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED (round 3)
- checks.yml:179 is exactly `ruff check scripts --select E9,F63,F7,F82` (rules inline, scripts/
  only); no pyproject.toml/ruff.toml/setup.cfg/.editorconfig/Makefile exists at the root. A 10-line
  pyproject makes local `ruff check .` match CI and covers `build/` + `version.py`. **Note:** F821
  (undefined name) is what would statically catch the BUG-01 class — add it once the
  function-local import cleanup (ARC-01) makes it clean.

### DOC-07 — Browser-cache trap documented in the wrong doc; internals line-anchors stale
- **Severity:** P3 · **Status:** CONFIRMED (round 3)
- gui.md's "Cache / stale page" bullet mentions only app.js caching, while
  verification-and-testing.md (~:285-294) carries the fuller, newer trap text (app.js **and**
  app.css + the stylesheet cache-bust snippet). docs/internals/gui-bridge.md carries a v0.18.0
  drift banner (:7-8) yet still asserts stale anchors at :33/:34/:51/:55/:71/:80 — verified real
  positions: `_sender` = gui_api.py:409 (doc says :249), `_worker_pump` = :542 (doc says :383),
  `boot()` = app.js:1921 (doc says :2293, past EOF). Reconcile; prefer symbol anchors over line
  numbers in internals docs.

### DOC-08 — No human-contributor onboarding
- **Severity:** P3 · **Status:** CONFIRMED (round 3)
- README.md:268-279's Contributing section points contributors at CLAUDE.md; no CONTRIBUTING.md
  exists at the root or under .github/; CLAUDE.md self-describes as the AI-session router. A
  30-line CONTRIBUTING.md (setup, run dev GUI, run checks, the regression-lock rule, the
  local-only-data rule) closes it.

---

## L. Dead code & hygiene

### DED-01 — Two dead public functions
- **Severity:** P3 · **Confidence:** high · **Status:** SELF-VERIFIED (zero references across scripts/build/tools/ui)
- `reports.export_key_for_spec` (reports.py:188) and `report_catalog.consolidate_module_names`
  (report_catalog.py:321). Five more are self-reference-only candidates worth a look:
  `compare_core.route_coverage`, `consolidate_ramp_summary.clean_label`/`is_new_label`,
  `paths.run_folder_name`, `pdf_row_oracle.independent_page_lines`. Overall dead-code level is
  **low** — good hygiene.

### DED-02 — Small dead/no-op code in the GUI backend (+ two unused imports, final sweep)
- **Severity:** P3 · **Status:** CONFIRMED (round 3 + final sweep)
- Unused `dest = settings.get_batch_dest()` (gui_matrix.py:548); identity ternary
  `"ok" if status == "ok" else status` (gui_api.py:645); mid-file `from gui_endpoint import
  _api_method` (gui_api.py:132) whose "P7c cycle-break" comment is stale — gui_endpoint.py imports
  only `logging`, so no cycle forces the placement. Final AST sweep added two unused imports:
  `is_export_disabled` (gui_api.py:68 — imported, never referenced in the file) and `tempfile`
  (updater.py:55). (The `import openpyxl` at gui_worker.py:1697 is a deliberate deps probe —
  keep.) Bundle with ARC-02's split.

### DED-03 — `_MTIME_TOL_S = 1.0` duplicated with a comment admitting the coupling
- **Severity:** P3 · **Confidence:** high · **Status:** SELF-VERIFIED
- matrix.py:42 and consolidation_meta.py:39 ("match matrix's float-mtime equality tolerance").
  Move to consolidation_meta (the lower layer); matrix imports it.

### DED-04 — GUI magic numbers
- **Severity:** P3 · **Status:** CONFIRMED (round 3)
- Verified literals: `while len(batch) < 200` (gui_api.py:418, JS batch cap), `deadline =
  time.monotonic() + 20` (:455), `time.sleep(1.2)` (:1268), and `blips >= 20` with a `0.3` poll
  (gui_worker.py:1518/1528) — a *derived* ~6 s dead-connection timeout where editing the poll
  interval silently changes the timeout. The codebase's own dominant pattern is named constants
  (`_PROGRESS_EVERY`, `_FORMULAS_TWIN_MAX_ROWS`, `_SWAP_TIMEOUT_S`). Name them during ARC-02.

---

## M. gh-pages landing page (round 3; audited via `git show origin/gh-pages`, tip `f1ed088` 2026-06-19)

### WEB-01 — Landing-page screenshots and OG card depict the pre-v0.17.0 UI (4 minor versions stale)
- **Severity:** P2 · **Confidence:** high · **Status:** CONFIRMED
- The gh-pages screenshot/og blobs are byte-identical to main's `docs/` copies last touched
  2026-06-18 (`0aab8d1`); the branch tip predates v0.17.0. This is tracked-but-unpaid debt —
  docs/roadmap.md:110 carries the checkbox, and `tools/screenshots.py` self-documents the exact
  regen + copy-to-gh-pages flow. **Fix:** run the tool, copy the 3 files to gh-pages, push. Bundle
  with REL-03/DOC-02 (the README refresh) as one "public face" task.

### WEB-02 — Download-version label injects the GitHub API `tag_name` via `innerHTML`
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED
- `origin/gh-pages:index.html:265-267`: `document.getElementById("ver").innerHTML = "Latest
  release: <b>" + rel.tag_name + "</b>"` — the tag comes unvalidated from the `/releases/latest`
  API response, and git refnames MAY contain `<`, `>`, `/`, `=`. Only exploitable by someone who can
  publish a release (i.e. the owner), so latent — but it's a 1-line fix: use `textContent` on a
  child node (or build the `<b>` via createElement).

### WEB-03 — Theme-toggle button is an empty dead control without JS
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED
- `origin/gh-pages:index.html:186`: the button ships with no content (glyph is JS-injected), and
  `.theme-btn` CSS (:90-94) renders a visible empty 36×36 square when JS is off/failed; its
  aria-label stays "Toggle theme" state-agnostic. Fix: inline a default glyph + `hidden` until JS
  boots, and update the aria-label with the current state.

### WEB-04 — Universal 0.35 s transition with no `prefers-reduced-motion` guard
- **Severity:** P3 · **Confidence:** high · **Status:** CONFIRMED
- `origin/gh-pages:index.html:64`: `* { … transition: background-color .35s ease, … }` plus
  :150-151, and the only media queries are color-scheme/width. Add a
  `@media (prefers-reduced-motion: reduce)` reset.

---

## H2. Export engine & auth — round-3 deep-pass results

### EXP-02 — Export-stub ImportError guard `print` + `sys.exit(1)` at import time is reachable from the GUI via `report_catalog`
- **Severity:** P2 · **Confidence:** high · **Status:** SELF-VERIFIED
- **Evidence:** every `export_*.py` stub runs `print('ERROR: Playwright is not installed. Run "1.
  setup (one time).bat" first.'); sys.exit(1)` at module import on ImportError (e.g.
  export_ramp_summary.py:7-11) — and `report_catalog.py:29-32` imports `SPEC` from these stubs at
  module level. report_catalog is the metadata SoT imported by reports.py and thence by the whole
  GUI/matrix layer.
- **Why:** if playwright is ever missing/damaged in the frozen bundle (a bad prune, a
  half-applied update), the GUI process **prints to nowhere and exits code 1 with no dialog** —
  the worst diagnosable failure mode on a locked-down work PC. It also violates the console-free
  convention (a `.bat`-naming `print` + `sys.exit` in a module the GUI imports).
- **Fix:** in the stubs, either move the guard under `if __name__ == "__main__":` (the specs
  themselves only need `exporter`'s save helpers, which import playwright lazily — verify) or
  `raise` a typed `DepsError` and let the two drivers handle it: `cli.run_cli` prints the .bat
  message; `gui_main`'s fatal-box shows a dialog. One pattern, ~12 files.
- **Verification:** a check that imports report_catalog with a mocked-out playwright and asserts
  the import completes (specs constructible) or raises a typed error — never `SystemExit`.
- **Difficulty:** easy · **Timing:** next correctness release

### Verified good (export/auth deep pass — questions from round 1, now answered)
- **Retry/resume:** `_can_resume` (exporter.py:136-157) deletes incomplete files for re-pull and
  trusts locked ones with a log; `_verify_saved_file` deletes truncated saves and records failure;
  the batch manifest keys steps by **stable report key** ("a registry re-order never resumes the
  wrong report", batch_manifest.py:90), `mark_done` persists immediately after each environment
  (:154-156), and a corrupt manifest degrades to "no batch to resume" (:115-117). No
  double-write/skip mechanism found (static analysis).
- **exporter vs exporter_parallel duplication: refuted.** exporter_parallel.py imports the shared
  machinery from exporter (:63) and adds only orchestration (worker events, preflight-once,
  reconcile, sequential retry). Round 1's speculation of heavy duplication was wrong.
- **Token hygiene:** the access token in the URL hash is deliberately stripped from every displayed/
  logged URL via `page_url_for_display` (auth_nav.py:377, :458).
- **Fast-mode wiring:** `TSMIS_FAST_WORKERS` set by the fast .bat IS consumed —
  cli.`_resolve_workers` (cli.py:111-116) dispatches to `run_export_parallel`. Correct.
- **Disabled-report gating** is centralized (reports.py:102-107 `DISABLED_EXPORT_SUBDIRS` +
  `is_disabled`; batch_manifest.py:43) — no scattered special-cases found.

## I2. Packaging, mock fidelity & `.bat` flow — round-3 results

### MOCK-01 — `#mock` cannot exercise the updater's active phases; one dead JS endpoint + fixture
- **Severity:** P3 · **Confidence:** high · **Status:** SELF-VERIFIED
- The event-name and endpoint sets of mock.js vs the real bridge are in **full parity** (automated
  diff — see the commands table), so the only structural mock gaps are: (a) the already-reported
  completion-event ORDER inversion (FE-02); (b) app.js handles updater phases
  `downloading`/`staged`/`applying` (switch at app.js:914) but mock.js only ever simulates
  `phase: "available"` (mock.js:453) — the download/apply UI states are untestable in `#mock`;
  (c) `gui_api.set_batch_dest` (:1536) is a JS-facing endpoint no UI file calls (the dialog flow
  uses `pick_batch_dest`) and its mock fixture (mock.js:1166) is likewise dead — remove the
  endpoint or note it as API-for-tests.
- **Fix:** add a mock updater sequence (available → downloading → staged) behind a `#mock` zap
  button; decide set_batch_dest's fate.

### Verified good (packaging / build tooling / .bat)
- **build/fake_site/** — 23 fixtures covering BOTH dropdown layouts (`dropdown.html` flat +
  `dropdown_nested.html` + ambiguous/selected variants) plus per-report data/empty/print pages.
- **prune_bundle.ps1** — round-1's "fragility" speculation **refuted**: it discovers the playwright
  dir with a recursive fallback, `throw`s when not found (:54), and has two fail-loud guards
  (leftover docs :191, sensitive data :226).
- **app.spec ↔ module inventory** — hiddenimports seeds from the same `APP_MODULES` list that
  `check_app_modules.py` locks (app.spec:110), so the dynamic-import drift tripwire exists; UI
  assets ship through an extension allowlist (:126-130).
- **check_build_env.py** — asserts version.py ↔ requirements ↔ hash-lock agreement on the
  Playwright pin, the explicit cryptography pin, and lock coverage of every direct dep, with a
  `--verify-installed` mode. (The remaining gap is only REL-02: CI *installs* the floating file.)
- **measure_baselines.py** — intentionally not in CI ("a measurement TOOL, not a pass/fail check",
  its own docstring); not an orphan. tools/screenshots.py documents the full regen flow WEB-01 needs.
- **.bat files** — all use `cd /d "%~dp0"` (spaces + Explorer-launch safe), menu loops validate
  input, and the fast variant's env-var plumbing works (see H2).
- **events.py** — a clean, dependency-free callback seam; thread-safety correctly lives in the
  GUI's queue wiring, not the sink.

### Verified good (final sweep — the areas whose dedicated agents were interrupted)
A last systematic pass over everything the interrupted subagents left thin. Results:
- **No check can silently never-fail:** all 75 `build/check_*.py` contain a real failure path
  (`sys.exit`/`raise`/`assert`/`_fail` — automated scan).
- **Zero commented-out code blocks** (≥4 consecutive code-looking comment lines) across scripts/,
  scripts/ui/, and build/ — unusually good hygiene.
- **Unused imports across the 10 biggest files:** exactly two (now in DED-02) — everything else
  the AST scan flagged was a deliberate probe import.
- **The previously-unread leaf modules are all clean and defensive**, several exemplary:
  `cache_envelope.py` (fail-safe versioned envelope — old/foreign/mismatched reads as empty, never
  corrupt), `owned_dir.py` (the M03 marker; its docstring already plans the SEC-02 name-fallback
  retirement), `safe_delete.py` (junction/symlink-safe rmtree at root AND descendants, preserving
  the `onerror` reporting contract), `report_library.py`, `gui_win32.py` (PID-matched window lookup
  with typed ctypes signatures), `run_report.py`, `routes.py`, `contract.py`, `summary_layout.py`
  (opt-in extra-sheet renderer, ImportError-guarded, write-only-streaming-safe).
- **`exporter.run_export` core loop read end-to-end:** cancel polled during the sign-in wait,
  `require_site_params` verifies data-source/env BEFORE writing into an env-labeled folder (a
  subtle wrong-folder guard), timeout accessors used (not raw constants), the "full run context in
  one block" logging contract honored, the retry pass re-raises AuthError but logs-and-continues
  otherwise, run-report auto-save is non-fatal. No findings.

---

# Quick wins under 30 minutes

| ID | Fix | Size |
|----|-----|------|
| BUG-01 | Add the missing `load_workbook` import in `_comparison_row_count` | 1 line (+ check later) |
| BUG-03 | Filter `~$` in `consolidate_xlsx_base.py:116` | 1 line |
| SEC-01 | `.gitignore`: `/config.json.corrupt`, `/tsmis_evidence_*.zip` | 2 lines |
| REL-03 | Swap README badge to the GitHub-release shield | 1 line |
| BUG-17 | `BFBFBFBF` → `BFBFBF` | 1 char |
| DED-03 | Single `_MTIME_TOL_S` home | 3 lines |
| BUG-09 | Wrap the two PDF `_load_tsn` branches in ValueError | ~6 lines ×2 |
| BUG-15 | Per-file try in `day_matrix._folder_newest_mtime` | ~5 lines |
| REL-04 | Python-3.11 assert in build.ps1 | 3 lines |
| REL-05 | `$LASTEXITCODE` check in backfill_release_notes.ps1 | 2 lines |
| DOC-04 | frozen-gate paragraph in build-and-release.md | prose |
| DOC-05 | CLAUDE.md layout line for the matrix/TSN modules | 1 line |
| FE-06 | Delete the 4 dead CSS rules (grep-confirm first) | deletions |
| DOC-01 | Decide + commit (or ignore) docs/planning/ | 1 command |
| BUG-16 | pid-suffix the `.write_test` probe | 2 lines |
| WEB-02 | `innerHTML` → `textContent` for the release tag on gh-pages | 3 lines |
| WEB-01 | Rerun tools/screenshots.py + copy 3 files to gh-pages | 1 command + push |
| DED-02 | Delete the dead `dest`, the no-op ternary, hoist the stale mid-file import | 3 edits |

# Deep refactors worth planning

1. **GUI backend split (ARC-02 + DUP-03 + DED-02/04):** three new mixins out of gui_api.py, worker
   classes into per-file modules, the `@_task_endpoint` claim-gate decorator (folding in BUG-04's
   exclusion fix and BUG-10's token check). Locked by check_gui_api_surface/check_gui_bridge/
   check_worker_lifecycle.
2. **Frontend split + lock-attribute sweep (FE-01 + DUP-04 + FE-05):** ui-compare/ui-export/ui-batch
   extraction, `data-lock-when-busy`, CONTRACT adoption, per-tab bind functions. Verified in `#mock`.
3. **PDF/parser substrate (DUP-02 + CON-01/02/03):** `pdf_table_lib.py` + one convert-driver;
   reconcile the four `_norm_route`s; goldens (check_tsmis_pdf_parse/reconcile, pdf_row_oracle) gate it.
4. **Comparator substrate completion (DUP-01):** migrate the 3 pre-P5b modules onto
   `run_files_compare`; byte-identity via the per-family goldens.
5. **matrix.py staleness unification + split (ARC-03 + BUG-12):** one `_staleness()` for both row
   modes, then matrix_state/matrix_build.
6. **TSN library versioned freshness (BUG-02):** the one deep item that should NOT wait for the
   cleanup version — it changes field behavior for the better immediately.
7. **settings registry (ARC-05 + SEC-03):** key registry with validation + log-redaction flags.
8. **Import-graph cleanup (ARC-01):** untangle the matrix↔reports↔tsn_library↔paths cycles; then
   enable ruff F821 to make the BUG-01 class statically detectable.

# Risks I would not ignore

1. **The release gate does not gate** (BUG-06/REL-01). Everything else in this repo's quality story
   assumes red checks block a release; today they don't. This is the one finding that multiplies the
   risk of every other finding.
2. **Silently wrong comparison numbers** (BUG-02 + BUG-07). The tool's entire value is "trust these
   diffs". The staleness trap has already shipped wrong numbers twice; the remaining falsy-zero
   sites sit in alignment keys. Both are known-shape fixes.
3. **The Edge-profile collision** (BUG-04) fires only in the configuration you can't test at home
   (device-mode work PC) — the field environment where trust in the tool is won or lost, and where
   the error will look like "the app randomly can't launch the browser".
4. **The updater's unhandled-interrupt window** (BUG-13). Rare, but its failure mode is a bricked
   install on a locked-down PC where the user cannot easily recover — and the next launch actively
   deletes the recovery pieces.
5. **Public-repo leak vectors** (SEC-01, DOC-01): sensitive dev artifacts sitting untracked-but-
   unignored at the root of a public repo is a standing invitation for an accident. Cheap to close.
6. **Verification fidelity drift** (TST-01/FE-02): two of the last three field bugs were invisible
   to the existing suite for the same root cause — the test double (mock order, mocked probe)
   diverged from production. The five proposed checks all target that class.

# Recommended implementation sequence

**Phase 0 — before/with the v0.18.5 sign-off release (a day):**
BUG-01, BUG-03, SEC-01, REL-03 (badge), BUG-17, quick wins batch (DED-03, BUG-09, BUG-15/16,
REL-04/05, DOC-04/05, DED-02, WEB-02), WEB-01 (screenshot regen → gh-pages), DOC-01 decision.
All trivially verifiable; none touch compare_core output.

**Phase 1 — correctness release (~a week):**
REL-01 cluster (run_checks.py + CI manifest guard + release.yml gate), BUG-02 (TSN version stamp +
auto-rebuild + canary re-bless), BUG-04 (gate the active check), BUG-05, BUG-07 (with re-bless),
BUG-08, EXP-02 (de-fang the stub import guard), FE-02 (+ its check), LOG-01 sweep (+ tripwire
check), TST-01 checks 1-2-4.

**Phase 2 — stability & performance (~a week):**
PRF-01 (byte-identity proven), BUG-10/11/12, BUG-13 (swap journal), BUG-14 (per-process logs),
PRF-02, TST-01 checks 3+5.

**Phase 3 — the structural cleanup version:**
Deep refactors 1-5 + 7-8 in that order (GUI split first — it unblocks endpoint-level testing and
absorbs the most future feature pressure), DOC-02/03/06/07/08, FE-03/04 (accessibility), DED-01/02,
ARC-04 only if a compare_core change is scheduled anyway.

**Phase 4 — opportunistic/deferred:**
SEC-02 marker migration, SEC-04/05/06, CON-03, FE-07/08, REL-02, MOCK-01, WEB-03/04.
(REL-06 dropped — refuted; it re-activates only when SIGNPATH_ENABLED is turned on, per the
roadmap's own rollout sequence.)

---

# Commands & checks run (ground truth for this audit)

| Command / probe | Result |
|---|---|
| `git log --oneline -15; git status; git branch -a` | v0.18.4 @ 0fa1cd5; only `?? docs/planning/`; 4 stale-looking local branches (feat/everything-matrix, fix/backfill-whatif-preview, polish/matrix-tabs, v0.17.0-audit-complete) — candidates to delete after confirming merged |
| `wc -l scripts/*.py scripts/ui/* build/*` | 28,333 lines scripts/, 25,242 UI+build; largest: gui_api 2622, app.js 2019, gui_worker 2005, compare_core 1960 |
| Check-vs-CI diff (`ls build/check_*` vs workflow greps) | **All 78 checks currently referenced in CI** (first pass missed the bash for-loop — corrected); no completeness guard exists |
| `python -c "... matrix._comparison_row_count(real_xlsx)"` | Returns `None` for a real 5-row workbook → **NameError proven; formulas-twin guard dead (BUG-01)** |
| grep `or ""` across compare/tsn/consolidate | 7 latent falsy-zero sites incl. compare_tsn_common.py:39 `norm_pm` (BUG-07) |
| grep updater hash/zip handling | sha256 companion + API digest verified pre-stage; `zipfile.extractall` (safe re zip-slip on Py3.11); phase-2 interrupt window + cleanup_leftovers interaction (BUG-13) |
| grep `innerHTML` in scripts/ui | **0 occurrences** — DOM built via createElement helpers; no HTML-injection surface found |
| `git check-ignore config.json.corrupt tsmis_evidence_test.zip` | Not ignored (SEC-01); `docs/planning` not ignored (DOC-01) |
| Oversized-function scan (AST-ish segmentation) | 25 functions >120 lines; top: GuiApi ~2380, GuiMatrixMixin ~1056, `_write_summary` ~302 |
| Inverse check-coverage map | Only gui_endpoint / gui_main / logging_setup have zero check references |
| Function-level import count | 156 sites; matrix.py:335/904/986 explicitly "avoid import cycle" (ARC-01) |
| Dead-function sweep | 2 zero-reference public functions; 5 self-ref-only candidates (DED-01) |
| Mock↔bridge automated diff (round 3) | Event types: mock ∖ real = ∅, real ∖ mock = ∅; endpoints: UI-calls ∖ mock = ∅, UI-calls ∖ real = ∅; real ∖ UI-calls = {set_batch_dest} (+ `put`/`attach` infra false-positives). Only order (FE-02) and updater phases (MOCK-01) drift |
| `git show origin/gh-pages` audit (round 3) | 9 files; 4 findings (WEB-01..04); screenshots byte-identical to main's 2026-06-18 copies |
| fake_site / prune / build_env reads (round 3) | Both dropdown layouts fixtured; prune throws loudly (2 guards); check_build_env asserts version↔req↔lock |
| Never-fail-check scan (final sweep) | 0 of 75 checks lack a failure path |
| Commented-out-code sweep (final sweep) | 0 blocks ≥4 lines across scripts/, ui/, build/ |
| Unused-import AST scan, 10 biggest files (final sweep) | 2 real (gui_api.py:68, updater.py:55); rest are probe imports |
| Leaf-module reads (final sweep) | cache_envelope, owned_dir, safe_delete, report_library, gui_win32, run_report, routes, summary_layout, contract — all clean; run_export core loop verified sound |
| Multi-agent audit | 13 domain auditors + ~56 adversarial verifiers completed across three runs (each run partially cut by a platform usage limit; every cut item was finished inline by the auditor). Final: 49 agent-CONFIRMED, ~19 self-verified, 1 REFUTED (REL-06), 0 unverified |

# Areas not inspected (final, after the round-3 gap fill)

All gaps declared by the original report have been closed (gh-pages → section M; fake_site,
app.spec drift, .bat files, tooling → I2; mock payload diff → MOCK-01/I2; export-auth deep pass →
H2; the 22 REPORTED items → verified in place, 21 confirmed / 1 refuted). A final sweep then
re-covered everything the interrupted subagents had left thin — never-fail checks, commented-out
code, unused imports, all previously-unread leaf modules, and the `run_export` core loop (see
"Verified good (final sweep)" in section I2). What genuinely remains:

- **Live-site behavior** — everything Playwright-facing was audited statically; selector/auth logic
  can only be exercised against the intranet site from the work PC (this is a standing project
  constraint, not an audit shortcut).
- **mock.js payload KEY-level diff** — event/endpoint NAME parity is proven (see the commands
  table); a per-event payload-key diff (every field of every event) was not done. Given the name
  parity and the CI-locked contract mirror, residual risk is low.
- **Interactive `.bat` flow execution** — the scripts were code-reviewed (quoting, cd, menu loops,
  env plumbing), not executed end-to-end; execution requires the console venv + a login.
- **Two per-file items** flagged for a look during their phases: whether `.mc-mode.on` was meant to
  be wired (FE-06 correction — possibly a missing feature, not dead CSS), and whether
  `set_batch_dest` should stay as API-for-tests (MOCK-01).
