# P13 — Work-PC validation handoff + v0.18.1 close-out plan — Claude report

## 1. Phase ID and name
**P13 — Work-PC validation handoff + v0.18.1 close-out plan** (CR-001 / CR002-RM5; the FINAL
*design* phase). Builds the method to validate everything that can't be proven offline — a
credential-safe, no-admin evidence collector + a manual fallback + the per-item acceptance
checklist (§K2) + the v0.18.1 plan — for the final **8-report** application shape. **Executing the
acceptance on the work PC is v0.18.1, not v0.18.0** — this phase ships only the *kit*.

## 2. Baseline commit
`c32941e` (P15, "forward-port the Intersection Detail vs-TSN comparison evolution"). Branch
`refactor/v0.18.0-structural-overhaul`; clean tree apart from the untracked `docs/planning/`.
Pre-change characterization green at baseline (`check_app_modules`, `check_import_direction`,
`check_source_zip_smoke`; only `check_no_misspelling` "fails" = the known untracked Codex P10
file). HEAD is **unchanged** by this phase (not committed — awaiting Codex review).

## 3. Changes made
- **`scripts/evidence.py` (NEW) — the credential-safe headless evidence collector.** `collect(...)`
  builds ONE zip from an **allowlist** (never a denylist): `manifest.txt`, `self_test.txt` (the
  offline self-test output, reusing `self_test.run`), the rotating logs, the recent run-report
  CSVs, and — only if the user passes `--evidence-dir` — the real source files they explicitly
  placed there (each listed in the manifest). It **never** collects the saved login (`paths.AUTH`),
  the Edge profile (`paths.EDGE_LOGIN_PROFILE_DIR`), failure dumps (`paths.FAILURES_DIR`), the
  exported report data (`output/<run>/…`), the TSN inputs, or the TSN library (RM05) — and it
  refuses a sensitive file even from the user's evidence folder. The manifest lists **every**
  included file, records the login as present-but-excluded (not its value), and derives the
  8-report live-verify set from `reports.EXPORT_REPORTS` (so Intersection Detail (PDF) is automatic
  — CR002-RM5). The self-test output is captured even when it *crashes* (the failing output is the
  evidence); collection never raises for an expected failure.
- **`scripts/gui_main.py` — the `--collect-evidence` entry.** A new branch alongside `--self-test`
  (after logging setup so the log exists to collect), plus `--evidence-dir <path>`. Runs headless
  (no real window), mirrors progress to the log + stderr, and shows the result path in a Windows
  message box (the windowed exe has no console). Collection failures are caught — they cannot crash
  the exe.
- **`build/check_evidence_bundle.py` (NEW) — the RM05 proof.** Plants a realistic DATA_ROOT (a
  saved login with a secret, an Edge profile, failure dumps, report data, TSN inputs, plus the
  legitimate logs/run-reports), runs `collect(run_self_test=False)`, and asserts the bundle
  includes only the allowlist, the secret appears in **no** zip file (manifest included), every
  included file is manifest-listed, a sensitive file dropped in the evidence folder is refused, and
  a self-test crash is captured without failing collection. The self-test is stubbed, so the check
  is offline + CI-safe (no browser).
- **`docs/work-pc-validation.md` (NEW) — the handoff doc.** §1 the collector usage + what it
  does/never collects; §2 the manual fallback for over-locked PCs; §3 the §K2 acceptance checklist
  (the 8-report shape: P8c live paths, the carried §M live-verify, the evidence-driven PDF fixes,
  the Intersection Detail (PDF) live acceptance, no regressions); §4 the v0.18.1 close-out plan.
- **`build/app.spec`** — `APP_MODULES += "evidence"` (the F6 packaging contract). **`checks.yml`** —
  `check_evidence_bundle` wired into the blocking suite.

## 4. Files affected
**New (3):** `scripts/evidence.py` (235), `build/check_evidence_bundle.py` (196),
`docs/work-pc-validation.md` (119). **Modified (3; +67):** `scripts/gui_main.py` (+64),
`build/app.spec` (+2), `.github/workflows/checks.yml` (+1). **Untouched (protected):**
`scripts/compare_core.py`, `version.py`, `scripts/gui_api.py` (the existing GUI support-bundle
method is left as-is — the collector is a separate headless entry, not a refactor) — all 0-diff.

## 5. Architectural decisions
- **Allowlist, not denylist (RM05 by construction).** The collector adds ONLY the explicit
  allowlist; it never walks DATA_ROOT broadly, so a new sensitive artifact can't leak by default.
  `_sensitive_roots()` + `_is_sensitive()` are a second guard for the user-evidence folder.
- **Reuse `self_test`, don't refactor `save_support_bundle`.** The plan says "reuse the self-test
  plumbing"; the collector calls `self_test.run`. The existing GUI `save_support_bundle` (a
  `pywebview`-dialog method) is **not** touched — keeping P13 additive (its `Affected` list doesn't
  include `gui_api`). The small log/run-report zipping overlap is accepted; a future DRY-extraction
  into a shared helper is possible but out of this additive phase's scope.
- **Headless, exit-early CLI mode** like `--self-test`: runs from a user folder, no admin/cmd/
  scheduled tasks, no real window — the only shape the locked work PC permits. Failures are caught
  so the exe never crashes mid-collection.
- **Registry-derived live-verify set.** The 8-report list comes from `reports.EXPORT_REPORTS`, so
  the kit covers the final shape (incl. Intersection Detail (PDF)) without a hand-maintained list.

## 6. Compatibility and migration handling
None required. The mode is **inert unless invoked** (`--collect-evidence`); no persisted format, no
settings key, no schema. Backward compatible by construction (a new opt-in CLI flag + a new module
+ a new doc). The existing GUI support-bundle is unchanged, so both coexist.

## 7. Tests and commands run
- Byte-compile: `python -m py_compile scripts/*.py build/*.py` → clean.
- **`check_evidence_bundle.py`** — 19 assertions, all green (the RM05 credential-exclusion: the
  saved login / profile / failure dumps / report data / TSN inputs are excluded; the secret string
  is in no file; the manifest lists every file; a sensitive evidence-folder file is refused; the
  self-test output and a crash are captured).
- **Packaging/structure:** `check_app_modules` (evidence in APP_MODULES — F6), `check_import_direction`
  (no new cycle), `check_source_zip_smoke` (the source archive carries `evidence.py`).
- **Full on-disk suite:** **74/75 `build/check_*.py`** + **3/3 Node** green (the lone failure is the
  pre-existing untracked `P10-codex-review.md` rg-literal; tracked content clean via `git grep`).
- Protected boundary: `git diff scripts/compare_core.py` = `version.py` = `scripts/gui_api.py` = **0
  lines**.

## 8. Results
- The evidence kit, the manual fallback, the §K2 acceptance checklist, and the v0.18.1 plan are
  implemented + committed-ready; the **credential-exclusion test is green** (the P13 completion
  gate). The mode is offline-provable end-to-end (the self-test is stubbed in CI; the *real*
  self-test + live export run on the work PC = v0.18.1).
- Purely additive: 3 new files + 3 small edits (+67); no protected file changed.

## 9. Before/after measurements
| Aspect | Before (HEAD `c32941e`) | After (P13) |
|---|---|---|
| Work-PC evidence path | none (a loose "owed" list in §M) | `--collect-evidence` + `--evidence-dir`, a manifest-listed zip |
| Credential-safety proof | (GUI support bundle only) | `check_evidence_bundle` (19 assertions, RM05) |
| `build/check_*.py` suite | 73 | 74 (+`check_evidence_bundle`) |
| `APP_MODULES` | (P14 set) | +1 (`evidence`) |
| v0.18.1 plan / acceptance checklist | in `05` §K2 only (planning) | `docs/work-pc-validation.md` (committed handoff) |

Diff: **3 modified (+67) + 3 new (550 lines)**; HEAD unchanged at `c32941e`.

## 10. Deviations from the approved plan
None. The plan's P13 `Affected` lists exactly these deliverables (the evidence mode reusing the
self-test plumbing, the manual fallback, the §K2 checklist, the v0.18.1 plan doc, the
credential-exclusion test). I did **not** refactor `gui_api.save_support_bundle` (not in P13's
scope) and did **not** edit `docs/INDEX.md` / `docs/roadmap.md` to link the new doc — that
reconciliation is **P11**'s job (P11's prereqs already say "the v0.18.1 plan (from P13) folded in").

## 11. Known limitations and external verification
- **The acceptance itself is v0.18.1, not v0.18.0.** P13 ships only the kit; the collector is
  proven offline (stubbed self-test). Running `--collect-evidence` on the **real locked work PC**,
  the **live** 8-report export/consolidate/compare, the real v0.17→v0.18 self-update, and the
  Intersection Detail (PDF) 218-route reconciliation are all v0.18.1 acceptance (§K2) — the work PC
  is the only place they can run (the dev PC can't reach the TSMIS intranet).
- **The Windows message box + the real self-test (browser) path** are exercised on the work PC, not
  in CI; the offline test stubs the self-test and skips the message box (`_message_box` is
  best-effort/no-op without `user32`).
- **DRY note:** the collector's log/run-report zipping overlaps `gui_api.save_support_bundle` by a
  few lines; left separate to keep P13 additive (a shared helper is a future option).

## 12. Exact diff scope Codex should review
- **`scripts/evidence.py`** — confirm the allowlist truly excludes every sensitive path (RM05): no
  `paths.AUTH` / `EDGE_LOGIN_PROFILE_DIR` / `FAILURES_DIR` / report data / TSN inputs reaches the
  zip; the manifest lists every file + never the login value; the user-evidence folder is guarded;
  the self-test capture never makes collection fatal.
- **`build/check_evidence_bundle.py`** — that the planted secret/profile/report-data are genuinely
  proven absent (the secret-in-no-file scan, the refused-evidence-folder file, the captured crash).
- **`scripts/gui_main.py`** — the `--collect-evidence` branch runs headless, exits early, and can't
  crash the exe; `--evidence-dir` parsing.
- **`docs/work-pc-validation.md`** — that the §K2 checklist covers the **8-report** shape (incl.
  Intersection Detail (PDF) live acceptance + the v0.17.8 vs-TSN behavior) and the safety wording
  matches the collector.
- **`build/app.spec` + `checks.yml`** — `evidence` in APP_MODULES; `check_evidence_bundle` wired.
- **Not in scope:** `compare_core` / `version.py` / `gui_api` (untouched), and the docs/INDEX +
  roadmap linkage (P11).

---

## Remediation — Round 1 (Codex `BLOCKED`)

**Review round addressed:** P13 Codex review round 1 (verdict `BLOCKED`; 1 blocking, 1 required, 1
non-blocking). The original report above is unchanged.

### Finding dispositions

| Finding | Disposition | Notes |
|---|---|---|
| **P13-B01** (Blocking) — `--evidence-dir` could bundle copied cookies/login DBs/internal HTML source | **Fixed** | `--evidence-dir` is now a **positive allowlist** (PDF/XLSX/XLS only) + an explicit browser/profile-basename refusal, so the RM05 promise no longer depends on user behavior. |
| **P13-R01** (Required) — the doc says "no cmd" but only documented command-line invocation | **Fixed** | Added a no-cmd desktop-shortcut path as the preferred locked-PC route; the CLI examples are kept for maintainer/dev. |
| **P13-A01** (Recommended) — the manifest listed planned entries even if a file failed to write | **Fixed** | The manifest is now built from the files **actually written**; a locked/unreadable allowlisted file is recorded under a `SKIPPED — unreadable` section, never claimed as bundled. Applied since the fix touched the manifest code (Codex's condition). |

### Remediation changes

- **`scripts/evidence.py` (P13-B01)** — `--evidence-dir` is no longer an arbitrary recursive upload.
  New `_refuse_reason(f, roots)` accepts a user-evidence file ONLY when it (a) is not under a
  sensitive root, (b) is not a browser/profile DB basename (`_PROFILE_BASENAMES` =
  `Cookies` / `Login Data` / `Web Data` / `Local State` / `History` / … — matched on the full name
  AND the stem, so a renamed `Cookies.pdf` is still refused), and (c) has an allowed extension
  (`_ALLOWED_EVIDENCE_EXTS` = `.pdf` / `.xlsx` / `.xls` — the real report/TSN source formats).
  Everything else is refused, logged, and recorded in `skipped_user` as `(path, reason)`. The
  manifest's SAFETY line + REFUSED section now state this.
- **`scripts/evidence.py` (P13-A01)** — `collect()` now writes the data entries FIRST (collecting
  the `written` arcnames + an `unreadable` list), then writes `manifest.txt` LAST from that real
  set. `_manifest(contents, unreadable, skipped_user, roots)` lists only the actually-bundled
  files under `BUNDLE CONTENTS`, the refused evidence-folder files (with reasons), and a
  `SKIPPED — unreadable` section. The result dict's `skipped_user` exposes the refused paths.
- **`build/check_evidence_bundle.py`** — adversarial fixtures added: the user evidence folder now
  also contains copied `Cookies`, `Login Data`, `Web Data`, `Local State`, a renamed `Cookies.pdf`,
  a `captured_internal_page.html`, and a stray `notes.txt`, each with planted secrets. New
  assertions prove none reach the zip, their secrets appear in **no** zip file, they are all in the
  `skipped_user`/REFUSED listing, and the allowed `.pdf`/`.xlsx` ARE bundled. New
  `test_unreadable_not_listed_as_bundled` monkeypatches `ZipFile.write` to fail for the log and
  asserts the manifest doesn't list it as bundled (it lists it under `SKIPPED — unreadable`).
  (19 → 35 assertions.)
- **`docs/work-pc-validation.md` (P13-R01 + P13-B01)** — §1 now leads with **the no-cmd desktop
  shortcut** (right-click → Create shortcut → append the flag to Target → double-click), keeping the
  CLI as maintainer/dev reproduction; and the `--evidence-dir` text states that **only `.pdf`/
  `.xlsx`/`.xls`** are bundled and any other file (copied cookie store / login DB / `.html`) is
  refused + listed.

### Updated verification

- `python -m compileall -q scripts build version.py` → clean; `git diff --check -- . ':!docs/planning'`
  → no whitespace errors.
- Codex-required re-runs all green: `check_evidence_bundle` (now **35 assertions** incl. the P13-B01
  adversarial copied-browser/profile/HTML fixtures + the P13-A01 unreadable-entry test),
  `check_app_modules`, `check_import_direction`, `check_source_zip_smoke`.
- Full on-disk suite re-run: **74/75 `build/check_*.py`** + **3/3 Node** green (the lone failure
  remains the pre-existing untracked Codex P10 rg-literal; tracked content clean).
- Protected boundary re-confirmed: `git diff scripts/compare_core.py version.py scripts/gui_api.py`
  = **0 lines** (P13 stays additive — only `evidence.py`, its test, and the doc changed in this
  round).

### Changed measurements

- `check_evidence_bundle` assertions: **19 → 35** (the adversarial P13-B01 fixtures + the P13-A01
  unreadable test).
- `scripts/evidence.py`: 235 → ~258 lines (the positive allowlist + the write-first manifest).
- No file added/removed; the 6-file P13 touch set (3 new + 3 modified) is unchanged. The 8-report
  registry-derived live-verify set and the suite count (74 Python checks) are unchanged.
