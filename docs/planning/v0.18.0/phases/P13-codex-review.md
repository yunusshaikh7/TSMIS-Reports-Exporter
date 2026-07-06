# Review round 1

## 1. Verdict

BLOCKED

## 2. Blocking findings

### P13-B01 — Blocking — `--evidence-dir` can bundle copied cookies/login DBs and internal-site source

Evidence:

- P13's hard privacy requirement in `docs/planning/v0.18.0/05-claude-final-plan.md:686` says the bundle never collects auth state, browser profiles, cookies, DPAPI material, credentials, or private/internal source by default; user-provided evidence is meant for real PDFs/workbooks and must avoid sensitive paths/tokens.
- `scripts/evidence.py:_allowlisted_entries` recursively adds every regular file under `extra_dir` unless `_is_sensitive` rejects it.
- `scripts/evidence.py:_is_sensitive` rejects files that resolve under the original sensitive roots and any file named like `paths.AUTH`, but it does not reject copied browser/profile artifacts by basename (`Cookies`, `Login Data`, etc.), HTML/internal page source, or arbitrary non-evidence file types once they are placed outside the original sensitive root.
- `docs/work-pc-validation.md:31-38` tells the user to place real source files in `--evidence-dir`, but then says every file placed there is added. `docs/work-pc-validation.md:52-55` says sensitive files are refused even if dropped into the evidence folder.
- Independent read-only probe: with `extra_dir` containing files named `Cookies`, `Login Data`, `captured_internal_page.html`, and `real_report.pdf`, `evidence.collect(..., run_self_test=False)` produced a zip containing:
  - `user_evidence/Cookies`
  - `user_evidence/Login Data`
  - `user_evidence/captured_internal_page.html`
  - the planted strings `COOKIE-SECRET-123`, `LOGIN-DB-SECRET-456`, and `SECRET-789`

Why this blocks approval:

The core point of P13 is a credential-safe work-PC evidence kit. Allowing arbitrary copied files from `--evidence-dir` makes the hard RM05 promise dependent on user behavior and contradicts the doc's claim that sensitive evidence-folder files are refused. This also leaves the existing `build/check_evidence_bundle.py` safety proof incomplete: it proves a copied `tsmis_auth.json` is refused, but not copied browser-cookie/profile files or internal HTML/page source.

Exact correction expected:

- Change `scripts/evidence.py` so `--evidence-dir` is a positive allowlist for the intended evidence classes, not arbitrary recursive upload. At minimum, accept only maintainer-requested source evidence types needed for this phase, such as PDF and workbook/TSN export formats, and refuse copied browser/profile/auth/internal-source artifacts by basename/type.
- Explicitly refuse browser/profile basenames such as `Cookies`, `Login Data`, `Web Data`, `Local State`, and internal-page/source formats such as `.html`/`.htm` unless a separate user-approved mechanism is added later.
- Update `build/check_evidence_bundle.py` with adversarial fixtures for copied `Cookies`, copied `Login Data`, and copied `.html` internal page source, and prove their planted secrets are absent from every zip entry and manifest.
- Update `docs/work-pc-validation.md` so the `--evidence-dir` instructions say only the allowed maintainer-requested evidence formats are bundled; sensitive copied files are refused and listed/skipped.
- Re-run `python build/check_evidence_bundle.py`, `python build/check_app_modules.py`, `python build/check_import_direction.py`, `python build/check_source_zip_smoke.py`, `python -m compileall -q scripts build version.py`, and `git diff --check -- . ':!docs/planning'`.

## 3. Required fixes

### P13-R01 — Required — Handoff doc says "no cmd" but only documents command-line invocation

Evidence:

- The approved P13 plan at `docs/planning/v0.18.0/05-claude-final-plan.md:685` requires a no-admin/no-PowerShell evidence collection mode that fits the locked work-PC capability model, including no cmd/scheduled tasks.
- `docs/work-pc-validation.md:14-15` restates that the work PC has no PowerShell/cmd/admin.
- `docs/work-pc-validation.md:22-36` then documents only command examples:
  - `TSMIS Exporter.exe --collect-evidence`
  - `TSMIS Exporter.exe --collect-evidence --evidence-dir "..."`

Exact correction expected:

Add a no-cmd user path, for example creating a Windows shortcut to `TSMIS Exporter.exe`, appending `--collect-evidence` and optionally `--evidence-dir "..."` to the shortcut Target, then double-clicking it from the user-writable app folder. Keep command-line examples if useful for maintainer/dev reproduction, but do not make cmd/PowerShell the only documented route.

## 4. Non-blocking recommendations

### P13-A01 — Recommended — Build the manifest from successfully written entries or record skipped unreadable entries separately

Evidence:

- `scripts/evidence.py:205-206` builds `contents` and `manifest_text` from all planned `entries` before writing files.
- `scripts/evidence.py:215-219` catches `OSError` from `zf.write(src, arc)` and skips unreadable files, but the already-written `manifest.txt` still lists the skipped `arc` under "BUNDLE CONTENTS".

Why this is non-blocking:

This is not a credential leak and does not invalidate the primary P13 safety mechanism. It can, however, make the manifest diagnostically false when a log/run report is locked or unreadable.

Suggested correction:

Track successfully written archive names and either write the manifest after successful writes, or include a separate "skipped/unreadable" section. A small test can monkeypatch `ZipFile.write` to raise for one allowlisted log and assert the manifest does not list it as bundled.

## 5. Verification performed

- Read `docs/planning/v0.18.0/00-coordination.md`; current phase is P13, `awaiting_review`, baseline `c32941e`.
- Read P13 section of `docs/planning/v0.18.0/05-claude-final-plan.md`.
- Read `docs/planning/v0.18.0/phases/P13-claude-report.md`.
- Reviewed relevant prior context: P15 is committed at `c32941e`; P14/P15 CR-002 context establishes that P13 must cover the final 8-report shape.
- Inspected tracked product diff from `c32941e` excluding `docs/planning/`:
  - `.github/workflows/checks.yml`
  - `build/app.spec`
  - `scripts/gui_main.py`
- Inspected untracked P13 deliverables:
  - `scripts/evidence.py`
  - `build/check_evidence_bundle.py`
  - `docs/work-pc-validation.md`
- Confirmed protected files are unchanged from baseline: `scripts/compare_core.py`, `version.py`, and `scripts/gui_api.py`.
- Confirmed `evidence._report_set()` derives the final 8-report live-verify set, including `Highway Log (PDF)` and `Intersection Detail (PDF)`.
- Ran:
  - `python build/check_evidence_bundle.py` — passed
  - `python build/check_app_modules.py` — passed
  - `python build/check_import_direction.py` — passed
  - `python build/check_source_zip_smoke.py` — passed
  - `python -m compileall -q scripts build version.py` — passed
  - `git diff --check -- . ':!docs/planning'` — passed
- Ran an independent adversarial evidence-folder probe with `run_self_test=False` to avoid browser/GUI launch. It demonstrated P13-B01 by showing copied `Cookies`, copied `Login Data`, and `.html` internal-source-like files are included under `user_evidence/` and their planted secret strings are present in the zip.
- Did not run `scripts/gui_main.py --collect-evidence` because it intentionally invokes the real self-test/browser path; that belongs to work-PC/v0.18.1 acceptance, not this read-only local review.

## 6. Whether Claude may proceed toward phase approval

No. Claude should fix P13-B01 and P13-R01, then keep P13 marked `awaiting_review` and request another Codex review. P13-A01 is recommended and should be addressed if it fits cleanly while touching the manifest code for P13-B01.

# Review round 2

## 1. Verdict

PASS

## 2. Blocking findings

None. Prior blocking finding **P13-B01** is resolved.

Evidence for P13-B01 resolution:

- `scripts/evidence.py:53` defines `_ALLOWED_EVIDENCE_EXTS = {".pdf", ".xlsx", ".xls"}`.
- `scripts/evidence.py:56-59` defines browser/profile basenames to refuse, including `Cookies`, `Login Data`, `Web Data`, and `Local State`.
- `scripts/evidence.py:104-115` implements `_refuse_reason(...)`, which refuses files under sensitive roots, browser/profile artifacts by full name or stem, and any file outside the PDF/XLSX/XLS positive allowlist.
- `build/check_evidence_bundle.py:98-106` now plants allowed PDF/XLSX files plus adversarial copied `Cookies`, `Login Data`, `Web Data`, `Local State`, renamed `Cookies.pdf`, `.html`, and `.txt` files.
- `build/check_evidence_bundle.py:130-145` asserts those adversarial files are not in the bundle, their planted secrets do not appear in any zip entry, and the manifest records refusal reasons.
- Independent probe with copied `Cookies`, `Login Data`, renamed `Cookies.pdf`, and `.html` files confirmed those secrets are absent while intended `real_report.pdf` and `real_tsn.xlsx` are bundled.

## 3. Required fixes

None. Prior required finding **P13-R01** is resolved.

Evidence for P13-R01 resolution:

- `docs/work-pc-validation.md:25-39` now documents the preferred no-cmd desktop-shortcut path: create a shortcut to `TSMIS Exporter.exe`, append `--collect-evidence` and optional `--evidence-dir` in the shortcut Target, then double-click it.
- Command-line examples remain available for maintainer/dev reproduction, but are no longer the only documented route.

Prior recommended finding **P13-A01** is also resolved:

- `scripts/evidence.py:248-264` writes data entries first, records actual `written` archive names and `unreadable` entries, then writes `manifest.txt` from that real set.
- `scripts/evidence.py:200-203` records unreadable files under `SKIPPED — unreadable` and keeps `BUNDLE CONTENTS` limited to files actually in the zip.
- `build/check_evidence_bundle.py:223-252` adds an unreadable-log regression that monkeypatches `ZipFile.write`, confirms the locked log is not in the zip, not listed under `BUNDLE CONTENTS`, and is listed under `SKIPPED — unreadable`.

## 4. Non-blocking recommendations

None.

## 5. Verification performed

- Re-read `docs/planning/v0.18.0/00-coordination.md`; P13 remains `awaiting_review` with baseline `c32941e`.
- Re-read the P13 section of `docs/planning/v0.18.0/05-claude-final-plan.md`.
- Re-read the updated `docs/planning/v0.18.0/phases/P13-claude-report.md`, including the round-1 remediation section.
- Re-read prior P13 Codex review round 1 and relevant P14/P15 context.
- Inspected the actual workspace:
  - tracked modified files remain `.github/workflows/checks.yml`, `build/app.spec`, and `scripts/gui_main.py`;
  - untracked P13 deliverables remain `scripts/evidence.py`, `build/check_evidence_bundle.py`, and `docs/work-pc-validation.md`;
  - `docs/planning/` changes were ignored when evaluating product diff.
- Confirmed protected files are unchanged from baseline: `scripts/compare_core.py`, `version.py`, and `scripts/gui_api.py`.
- Confirmed `evidence._report_set()` still derives the final 8-report live-verify set, including `Highway Log (PDF)` and `Intersection Detail (PDF)`.
- Ran:
  - `python build/check_evidence_bundle.py`
  - `python build/check_app_modules.py`
  - `python build/check_import_direction.py`
  - `python build/check_source_zip_smoke.py`
  - `python -m compileall -q scripts build version.py`
  - `git diff --check -- . ':!docs/planning'`
- Ran an independent adversarial `--evidence-dir` probe with `run_self_test=False` to avoid browser/GUI launch. It verified copied `Cookies`, copied `Login Data`, renamed `Cookies.pdf`, and `.html` internal-source-like files are refused and absent from zip bytes, while allowed `.pdf` and `.xlsx` evidence files are included.

All executed checks passed.

## 6. Whether Claude may proceed toward phase approval

Yes. Claude may proceed toward phase approval/commit for P13. No blocking, required, or non-blocking findings remain from this review round.
