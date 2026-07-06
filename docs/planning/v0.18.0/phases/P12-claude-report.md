# P12 — Claude implementation report

## 1. Phase ID and name
**P12 — Residual offline audit hardening + evidence harnesses** (blocking; CR-001;
depends committed P2 ✓ / P3 ✓).

## 2. Baseline commit
`a8d9235` ("fix: harden the self-updater and hash-pin the reproducible build (P10)")
on `refactor/v0.18.0-structural-overhaul`. Pre-change tree clean apart from the
untracked `docs/planning/` workspace. Pre-change suite recorded GREEN: **68/68**
tracked-relevant Python checks + **3/3** Node + byte-compile; the only
`check_no_misspelling` hit is the untracked Codex review file under `docs/planning/`
(never committed — `git grep` over tracked files is clean), exactly as at the P10
commit.

## 3. Changes made
Four offline-doable audit residue items, each independently checked (per the plan,
"each its own commit + offline check" — see §12 for the commit-split boundary).

### Item 1 — `reset` junction/symlink guard (`reset-follows-junctions-symlinks`)
- New `scripts/safe_delete.py`: `scoped_rmtree(root, onerror=...)` — a reparse-point
  -safe recursive delete that UNLINKS a junction/symlink (at the root or any
  descendant) instead of recursing THROUGH it; `is_reparse_point()` detects Windows
  junctions+symlinks (`FILE_ATTRIBUTE_REPARSE_POINT`) and POSIX symlinks. Mirrors
  `shutil.rmtree`'s `onerror(func, path, exc_info)` contract.
- `gui_worker.ResetWorker.run` now deletes directory targets via
  `safe_delete.scoped_rmtree` (was `shutil.rmtree`); the existing locked-file
  `on_error` reporting is preserved unchanged.
- **Honest scope (verified, §9):** on the shipped CPython 3.11, `shutil.rmtree`
  already refuses to follow junctions — a CHILD junction it unlinks safely (3.8+
  guard via `IO_REPARSE_TAG_MOUNT_POINT`), and a ROOT reparse point it REFUSES with
  `OSError` ("Cannot call rmtree on a symbolic link") leaving the link. So the
  audit's data-destruction scenario does NOT reproduce on 3.11. `scoped_rmtree`'s
  genuine value is (a) a clean, UNIFORM unlink of a ROOT reparse point — which reset
  hands every target to deletion as — instead of a confusing "open in Excel" error +
  a lingering link, and (b) explicit, version-independent protection not dependent on
  a stdlib behavior that DID change across versions.

### Item 2 — consolidate-overwrite confirm-then-appears re-check (`consolidate-overwrite-toctou`)
- New `artifact_store.confirm_late_overwrite(dest, existed_at_confirm, confirm)`:
  re-asks ONLY for a destination that did not exist at the first prompt but APPEARED
  while the producer ran; returns True to proceed / False to abort.
- New `artifact_store.atomic_save_if(workbook, out_path, proceed)`: a two-phase
  variant that serializes the workbook to the temp first, then gates the
  `os.replace` on `proceed()` — the re-check at the NARROWEST point, with no
  half-streamed `write_only` workbook to abandon.
- Wired into EVERY confirm→write path (not just the one the audit named):
  `commit_workbook` (the wrapper every `compare_core` comparator uses),
  `consolidate_xlsx_base.consolidate_xlsx` (highway log / sequence / intersection
  detail — via `atomic_save_if`), `consolidate_ramp_summary`,
  `consolidate_intersection_summary`, `consolidate_tsn_highway_sequence`, and the two
  per-route converters `consolidate_tsmis_highway_log_pdf` + `consolidate_tsn_highway_log`
  (which confirm early then finalize via `consolidate_xlsx` with a no-op confirm, so
  the real re-check lives in the converter just before that call).
- **`compare_core` is untouched** — the re-check lives entirely in the non-locked
  `artifact_store` wrapper + the consolidators.

### Item 3 — destination-ownership marker (M03)
- New `scripts/owned_dir.py`: `mark_owned` / `is_owned` / `ensure_owned_dir`, a
  `.tsmis-owned.json` marker stamped into app-created directories under a USER-CHOSEN
  destination.
- Stamped on the Export-Everything store `<src>-<env>` folder (`ExportWorker._run_specs`,
  once, surviving the per-report stage→swap) and the `comparisons` tree (both matrix
  compare workers).
- `gui_worker.reset_targets` now PREFERS the marker (proves the app created a dir,
  whatever its name) and keeps the legacy known-NAME trust as an explicit
  backward-compat fallback.

### Item 4 — independent expected-row oracle + evidence-capture contract (`pdf-consolidator-no-row-count-verification`)
- New `scripts/pdf_row_oracle.py`: counts expected Highway Log (PDF) data rows by an
  INDEPENDENT method (text lines beginning with a postmile, authored separately from
  the parser's regex) vs the parser's cell-rect geometry; `reconcile()` flags any
  drop/duplicate; `capture_evidence()` is the PRIVACY-SAFE (counts only — never cell
  contents; RM05) record the P13 work-PC kit runs over REAL PDFs.
- `build/check_tsmis_pdf_reconcile.py` extended to reconcile against the
  consolidator's exact `parse_pdf` 3-tuple contract.

### Packaging + CI wiring
- `build/app.spec` `APP_MODULES` += `safe_delete`, `owned_dir`, `pdf_row_oracle`
  (F6 inventory — `check_app_modules`).
- `.github/workflows/checks.yml` += the 4 new checks in their cohesive blocking steps.

## 4. Files affected
**New product modules (`scripts/`, console-free):** `safe_delete.py` (106),
`owned_dir.py` (70), `pdf_row_oracle.py` (115).
**New offline checks (`build/`):** `check_reset_safety.py` (189),
`check_consolidate_toctou.py` (300), `check_owned_dir.py` (122),
`check_pdf_row_oracle.py` (161).
**Modified (tracked, +224 / −38):** `scripts/artifact_store.py`,
`scripts/gui_worker.py`, `scripts/consolidate_xlsx_base.py`,
`scripts/consolidate_ramp_summary.py`, `scripts/consolidate_intersection_summary.py`,
`scripts/consolidate_tsn_highway_sequence.py`,
`scripts/consolidate_tsmis_highway_log_pdf.py`,
`scripts/consolidate_tsn_highway_log.py`, `build/app.spec`,
`build/check_tsmis_pdf_reconcile.py`, `.github/workflows/checks.yml`.

## 5. Architectural decisions
- **One shared TOCTOU helper, many thin call sites** (DRY): `confirm_late_overwrite`
  + `atomic_save_if` in `artifact_store`; each consolidator captures
  `existed_at_confirm` at its first prompt and re-checks just before its write.
- **Two-phase `atomic_save_if`** for the streaming `write_only` consolidator so a
  declined overwrite never abandons a half-streamed workbook (no dangling
  `openpyxl` row generator / leaked temp). The single-output consolidators re-check
  before building their in-memory workbook (clean by construction).
- **M03 marker is additive + forward-looking, not subtractive** — it ADDS provable
  ownership (a marked dir of any name is reset-deletable) without dropping the legacy
  name trust, so no existing-install behavior regresses; the name fallback can be
  retired in a later release once markers are universal, fully closing the
  name-collision gap.
- **Oracle independence (R1-D05/D12):** the oracle uses a different EXTRACTION METHOD
  (text lines) than the parser (cell rectangles) and an INDEPENDENTLY-authored
  postmile recognizer (not imported from `parse_pdf`), so a future parser drift makes
  the two diverge and the reconciliation flags it.
- **`pdf_row_oracle` ships in `scripts/`** (not `build/`) because the P13 bundled
  `--collect-evidence` mode must import it; declared in `APP_MODULES` accordingly.

## 6. Compatibility and migration handling
- No data formats or on-disk schemas change; **no migration**.
- Item 1: `ResetWorker`'s public message protocol + `onerror` reporting unchanged.
- Item 2: with the default `confirm` (overwrite-freely, e.g. CLI/matrix) behavior is
  IDENTICAL — the re-check only adds a prompt when a REAL confirm callback is supplied
  AND a file appeared mid-produce. The comparator regression checks pass
  byte-identically (`compare_core` untouched).
- Item 3: backward-compatible — pre-P12 store dirs (no marker) are still deleted by
  the legacy name trust; the marker is stamped on the next export/matrix run.
- Item 4: purely additive (new module + extended check); the parser is untouched.

## 7. Tests and commands run
All via `build/.venv/Scripts/python.exe -B -X utf8` (and `node` for the JS checks).
- New: `check_reset_safety` (incl. a behavioral probe of `shutil.rmtree` vs
  `scoped_rmtree` on a real `mklink /J` junction), `check_consolidate_toctou`
  (helper unit + commit_workbook + consolidate_xlsx + ramp_summary + the per-route
  converter shape), `check_owned_dir` (marker round-trip + a real `reset_targets`
  integration), `check_pdf_row_oracle` (oracle logic + reconcile + capture wiring).
- Extended: `check_tsmis_pdf_reconcile` (+ oracle ↔ parse_pdf 3-tuple cross-check).
- Pre-change characterization + regression: `check_artifact_store`, `check_p2_freshness`,
  `check_consolidate_outcome`, `check_consolidate_intersection`,
  `check_ramp_summary_partial`, `check_worker_lifecycle`, `check_b3_batch`,
  `check_matrix`, `check_day_matrix`, `check_matrix_bridge`, `check_matrix_tsn`,
  `check_compare_env_highway_log_pdf`, `check_highway_log_{columns,ditto,roadbed}`,
  `check_compare_ramp_summary{,_tsn}`, `check_app_modules`, `check_import_direction`.
- Full suite (every `build/check_*.py` + the 3 Node checks) + `compileall scripts build version.py`.
- Empirical probes: `shutil._rmtree_unsafe` source inspection + live junction
  behavior on Python 3.11 / win32 (recorded in §9).

## 8. Results
- **Full suite: PASS=72 / FAIL=1 Python + 3/3 Node + byte-compile OK.** The single
  "fail" is `check_no_misspelling`, whose ONLY hit is the untracked Codex review file
  under `docs/planning/` (never committed). The authoritative `git grep` over all
  TRACKED files is **clean** of the product-name transposition, so the committed/CI
  tree passes the guard. (72 = the prior 68 + the 4 new P12 checks.)
- All four new checks pass; all touched-module regression checks pass; `compare_core`
  comparator checks byte-identical.

## 9. Before/after measurements
- **Item 1 (empirical, Python 3.11.0 / win32):** `shutil.rmtree` over a tree
  containing a CHILD junction → target's sentinel **survives** (already guarded);
  `shutil.rmtree` on a ROOT junction → **raises** `OSError` and leaves the link.
  `scoped_rmtree` on a ROOT junction → removes the link, target preserved;
  child-junction case → container deleted, target preserved. So: no data-loss
  before/after on 3.11 (both preserve the target); the behavior DELTA is root reparse
  handling — `shutil` errors + leaves the link, `scoped_rmtree` cleanly unlinks it.
- **Item 2:** the confirm-then-appears window narrows from the WHOLE producer runtime
  (seconds — parsing a folder of PDFs / streaming a large workbook) to the
  microseconds between the re-check and `os.replace`. It is narrowed, NOT atomically
  eliminated (see §11).
- **Item 3:** `reset_targets` deletes a store child on `is_owned(child) OR name-match`
  (was name-match only); a MARKED dir with a non-known name is now deletable (the
  marker is the deciding factor — verified non-inert), an UNMARKED foreign dir is
  preserved as before.
- **Item 4:** 0 → 1 independent oracle + capture path; the parser still has 0
  real-PDF correctness proof offline (that is v0.18.1 — RM04).

## 10. Deviations from the approved plan
- **None in scope.** All four plan items landed with their offline checks.
- **Broader than the literal finding (justified):** the TOCTOU re-check was applied to
  ALL 7 confirm→write paths, not only the single one the audit named, since they share
  the identical pattern and a partial fix would leave the same class of bug in six
  siblings (DRY via one shared helper).
- **Honesty corrections (RM04 applied beyond PDFs):** Item 1 is reported as a
  clean/uniform/version-independent guard + a root-reparse behavior fix, NOT as fixing
  live data-destruction on the shipped Python (which 3.11's `shutil.rmtree` already
  prevents). The reset-safety check asserts the TRUE 3.11 behavior, not a false RED.

## 11. Known limitations and external verification
- **Item 1:** on Python 3.11 the data-destruction scenario the finding describes does
  not reproduce (the stdlib guards it); the guard is explicit/defense-in-depth +
  a cleaner root-reparse outcome. The junction-creation in the check uses `mklink /J`
  (dev-PC / CI Windows only — never the shipped app).
- **Item 2:** the re-check NARROWS but cannot ATOMICALLY eliminate the window — there
  is no "replace-only-if-still-absent" primitive for a deliberate
  overwrite-after-confirm. The truncation half is fully closed (F9 temp + atomic
  replace).
- **Item 3:** the marker closes the user-collision gap only for dirs created AFTER
  P12 ships (stamped on the next export/matrix run); a known-named UNMARKED dir is
  still trusted by name for backward-compat. Retiring the name fallback (full closure)
  is a documented later-release step.
- **Item 4 (RM04 — does NOT over-claim):** the synthetic fixtures are abstract
  TEXT-LINE page representations, NOT real PDFs, and prove the ORACLE logic + the
  capture WIRING only. The parser's real-PDF correctness (the row-count, stale-geometry
  emit, and ramp-summary misattribution items) stays **v0.18.1 evidence-driven** —
  the `capture_evidence` path is what the P13 kit runs over the returned real PDFs.
- **External verification owed (v0.18.1):** live "Delete all reports" over a real
  work-PC store; real-PDF oracle reconciliation; M03 behavior on a real shared store.

## 12. Exact diff scope Codex should review
Tracked diff vs `a8d9235` (+224 / −38) over 11 files + 7 new untracked files:
- **`scripts/safe_delete.py`** (new) + **`scripts/gui_worker.py`** (ResetWorker
  rmtree swap; `_run_specs` out_base stamp; both matrix workers' comparisons stamp
  with the `if self.dest` guard; `reset_targets` marker-preferring loop; `import
  safe_delete`/`owned_dir`).
- **`scripts/artifact_store.py`** (`confirm_late_overwrite`, `atomic_save_if`,
  `commit_workbook` existed-tracking + the primary/twin re-check, header doc).
- **The 6 consolidators** (`consolidate_xlsx_base`, `consolidate_ramp_summary`,
  `consolidate_intersection_summary`, `consolidate_tsn_highway_sequence`,
  `consolidate_tsmis_highway_log_pdf`, `consolidate_tsn_highway_log`) — each:
  `existed_at_confirm` capture + the pre-write re-check (+ `import artifact_store` in
  the two converters).
- **`scripts/owned_dir.py`** (new) + **`scripts/pdf_row_oracle.py`** (new).
- **`build/app.spec`** (APP_MODULES +3) + **`.github/workflows/checks.yml`** (+4
  checks) + the 4 new **`build/check_*.py`** + the **`check_tsmis_pdf_reconcile.py`**
  extension.

Suggested review emphasis: (1) the §9 Item-1 honesty — is the 3.11 characterization
correct and not over-claimed? (2) the TOCTOU re-check placement in the two per-route
converters (the real confirm is in the converter, not the inner `consolidate_xlsx`);
(3) M03 backward-compat (no existing-install reset regression); (4) RM04 honesty for
the PDF oracle (harness now, real-PDF acceptance v0.18.1).

---

## Remediation — Codex review round 1 (`BLOCKED`)

**Round addressed:** P12 Codex review round 1 — verdict `BLOCKED` (1 blocking
**P12-B01**, 1 required **P12-R01**, 0 non-blocking).

### Finding dispositions
- **P12-B01 (blocking) — Fixed.** Codex is correct. The round-1 re-check sat BEFORE
  `build_workbook` / `_write_workbook` / the converter's `consolidate_xlsx`, while the
  actual `os.replace` happened LATER inside those — so a destination that appeared
  DURING the build (after the re-check, before the final save) was still overwritten
  with `confirm_calls=0`. Reproduced Codex's `consolidate_intersection_summary` probe.
- **P12-R01 (required) — Fixed.** Codex is correct. The oracle's single-token
  recognizer missed the split realignment-prefix shape `"R 012.345"` that the parser
  explicitly accepts (`consolidate_tsmis_highway_log_pdf.py:366-368,379-381`).
  Reproduced: the old recognizer returns `False` for `"R 012.345 …"`.

### Remediation changes
**P12-B01 — the overwrite gate is now at the FINAL commit point (the `os.replace`) for
every writer:**
- The three direct writers route their save through `atomic_save_if` with a `proceed`
  gate. `consolidate_ramp_summary.build_workbook`,
  `consolidate_intersection_summary.build_workbook`, and
  `consolidate_tsn_highway_sequence._write_workbook` now take `proceed=None` and
  `return artifact_store.atomic_save_if(wb, out_path, proceed or (lambda: True))`. Each
  `consolidate()` removes its pre-build re-check and instead passes
  `proceed=lambda: artifact_store.confirm_late_overwrite(out_path, existed_at_confirm,
  confirm)`, returning `cancelled` when the writer reports not-committed.
- The two per-route converters (`consolidate_tsmis_highway_log_pdf`,
  `consolidate_tsn_highway_log`) no longer re-check before `consolidate_xlsx` with a
  no-op confirm; they pass the REAL `confirm` + `existed_at_confirm` into
  `consolidate_xlsx`. `consolidate_xlsx` gained an `existed_at_confirm` parameter: when
  a caller pre-confirmed (passes it), `consolidate_xlsx` SKIPS its own initial prompt
  but STILL runs the pre-replace gate (`atomic_save_if`) with the real confirm — so a
  late appearance is caught at the final replace, with no double prompt for the
  already-confirmed pre-existing case. The now-unused `import artifact_store` was
  removed from both converters.
- `build/check_consolidate_toctou.py` rewritten: the destination now APPEARS right at
  the final save (patching `atomic_save_if` to create it immediately before the real
  gate), proving `cancelled` + the appeared file preserved + exactly one confirm call
  for `consolidate_intersection_summary`, `consolidate_ramp_summary`,
  `consolidate_tsn_highway_sequence`, and the per-route converter — plus a direct
  `atomic_save_if` gate unit test (`proceed()` False → not committed, destination NOT
  written). These are RED against the old pre-build re-check (the old `atomic_save` had
  no gate) and GREEN now.

**P12-R01 — oracle split-prefix recognition:**
- `scripts/pdf_row_oracle.line_is_data_row` now also accepts a lone alphabetic prefix
  token followed by a bare postmile (`"R 012.345"`), via INDEPENDENTLY-authored
  recognizers (`_PREFIX_RE` + `_BARE_POSTMILE_RE`; NOT imported from `parse_pdf`). A
  lone letter WITHOUT a following postmile stays a non-data line.
- `build/check_pdf_row_oracle.py` adds the split-prefix data-row check, a `_SPLIT`
  count fixture (→ 3), a lone-letter-without-postmile negative, and split-prefix
  capture-wiring coverage (the split rows reach the privacy-safe evidence record).

**Test-signature follow-through:**
- `build/check_tsn_outcome.py` — the existing `_write_workbook` stub was updated to
  accept the new `proceed` kwarg and return committed=True (mirrors `atomic_save_if`);
  no production behavior change.

### Updated verification
- Full suite **72/72** Python + **3/3** Node + `compileall` (the lone
  `check_no_misspelling` hit remains the UNTRACKED Codex review file; the `git grep`
  over all tracked files is clean).
- RED→GREEN re-proven: **P12-B01** — the rewritten TOCTOU tests fail against a
  pre-build re-check / ungated `atomic_save` and pass with the gate at the replace;
  **P12-R01** — the old single-token recognizer returns `False` for `"R 012.345"`
  (matching Codex's probe), the new one returns `True`.
- Touched-module regressions green; `compare_core` comparator checks byte-identical;
  `check_import_direction` (converter import removals) + `check_app_modules` green;
  `git diff --check` clean.

### Changed measurements
- The confirm-then-appears window for all six consolidators is now closed at the FINAL
  `os.replace` (not merely the parse-time window) — an appearance ANY time before the
  replace is caught, matching the comparator (`commit_workbook`) and `consolidate_xlsx`
  paths. (§9 "narrows, not eliminates" still holds only for the irreducible microsecond
  between the gate and `os.replace`.)
- Diff vs `a8d9235` is now **12 modified tracked files** (+`build/check_tsn_outcome.py`)
  + the 7 new untracked files; still no `docs/planning`, no `compare_core`, no live
  access. Phase remains `awaiting_review`.

---

## Remediation — Codex review round 2 (`PASS WITH FIXES`)

**Round addressed:** P12 Codex review round 2 — verdict `PASS WITH FIXES`
(**P12-B01** + **P12-R01** confirmed resolved; 1 required **P12-R02**; 0 non-blocking).

### Finding dispositions
- **P12-B01 — resolved (round 1), reconfirmed by Codex.** No action.
- **P12-R01 — resolved (round 1), reconfirmed by Codex.** No action.
- **P12-R02 (required) — Fixed (docs-only).** Codex is correct: `scripts/safe_delete.py`'s
  module docstring still carried the original over-claim — that Windows junctions make
  `shutil.rmtree` recurse THROUGH the link and delete the target's contents —
  contradicting the verified shipped-3.11 behavior that the P12 report (§3 / §9) and
  `build/check_reset_safety.py` already document. It was the one place the
  pre-investigation framing survived.

### Remediation changes
- Rewrote the `scripts/safe_delete.py` top-level docstring to match the verified
  CPython 3.11 behavior: a CHILD junction/symlink target is ALREADY preserved by
  `shutil.rmtree` (3.8+ guard via `IO_REPARSE_TAG_MOUNT_POINT`); a ROOT reparse point
  is REFUSED with `OSError` and left in place; so no data is destroyed on 3.11, and the
  residual gaps are (a) reset hands every target to deletion AS A ROOT, so a
  junction/symlink target errors and lingers (misleading message) instead of being
  cleanly removed, and (b) the protection would otherwise depend on a stdlib behavior
  that changed across versions. `scoped_rmtree` is framed as the EXPLICIT, UNIFORM,
  version-independent guard (root-or-descendant unlink without following).
  **No code or behavior change** — only the module docstring; `scoped_rmtree`,
  `is_reparse_point`, and the ResetWorker wiring are byte-identical.

### Updated verification
- `scripts/safe_delete.py` byte-compiles; **`build/check_reset_safety.py` — PASS**
  (reset behavior + tests unchanged); **`git diff --check` — clean**; `safe_delete.py`
  transposition scan clean. These are exactly the re-runs Codex requested.
- No other check needed re-running (no code path changed); the round-1 full-suite
  **72/72** Python + **3/3** Node result stands.

### Changed measurements
- None (documentation-only). The diff file count is unchanged — `scripts/safe_delete.py`
  is one of the 7 new untracked files, so editing its docstring changes its content but
  not the 12-modified / 7-new file tally. Phase remains `awaiting_review`.
