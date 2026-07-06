# P6 — Persistence hardening (narrowed) — Claude report

## 1. Phase ID and name
**P6** — Persistence hardening (narrowed; DPAPI→O2) `[blocking core; depends P0]`

## 2. Baseline commit
`c0cfa39` (HEAD after P5 committed — "refactor: collapse TSN single-file normalizers into a shared
factory"). Baseline: **59** offline Python checks + 2 Node frontend checks green; `check_import_direction`,
`check_app_modules`, `check_no_misspelling`, byte-compile, `node --check app.js`, `git diff --check`
all green; tree clean apart from the untracked `docs/planning/`. Dependency **P0 committed** (`4bbee65`)
— satisfied.

## 3. Changes made
Three evidenced hardenings (R1-N02), no behavior change to the persisted formats:

1. **Settings writer dedup + atomicity (`settings.py`, §2.3).** Four writers still inlined their own
   `tempfile.mkstemp + os.replace` block — `update`, `set_site_url`, `set_batch_dest`,
   `set_matrix_baseline` — while ~13 newer setters already routed through `_atomic_write`. P6 moves
   `_atomic_write` to the top of the module (so it precedes every writer) and routes those four through
   it, removing the four duplicated write blocks and their now-unused `global _cache` declarations. One
   atomic writer for all settings; unknown-key round-trip and corrupt-file move-aside are untouched.

2. **Atomic auth-at-rest write + owner ACL (`common.save_auth_state`, AUDIT-P2-authrest).** The session
   file was written with a direct `open(AUTH, "w")` (a crash/lock mid-write could truncate a prior good
   session) and inherited the folder's ACL. P6:
   - writes via `tempfile.mkstemp + os.replace` (F9 — never truncate a prior good session);
   - adds `_restrict_to_owner(path)`: best-effort tighten the file's NTFS ACL to the current user via
     the built-in `icacls` (`/inheritance:r /grant:r <user>:F`), Windows-only, no admin, no console
     window, any failure logged-and-ignored (the file already lives in the user's own profile, and an
     ACL hiccup must never block sign-in — a total icacls failure just leaves the inherited,
     owner-readable ACL, so no lock-out);
   - applies the ACL to the **temp file before the rename**, so the cookies never sit at the well-known
     `AUTH` path with a broad inherited ACL even briefly (security-review hardening, §5/§10);
   - validates `USERNAME` against the exact set of characters Windows forbids in an account name before
     it flows into the icacls `account:perm` argument (security-review hardening, §5/§10).
   - **DPAPI deferred to O2** (it binds to user+machine and would break `storage_state` portability —
     the file stays plaintext JSON, the bytes unchanged).

3. **Support-bundle settings allowlist (`settings.support_bundle_settings()` + `gui_api`,
   support-bundle-settings-future-leak).** The diagnostic bundle's manifest embedded
   `settings.all_settings()`. P6 adds an explicit `_SUPPORT_BUNDLE_KEYS` allowlist (the current safe
   reliability/debug knobs) + `support_bundle_settings()` returning only those, and switches the
   manifest to it. A future DEFAULTS key that holds something sensitive is therefore **not auto-shared**
   until it is explicitly reviewed and added; an import-time `assert` keeps the allowlist a subset of
   DEFAULTS (catches a typo) without forcing it to equal DEFAULTS (the asymmetry is the safeguard).

4. **New `build/check_persistence.py`** (16 assertions) + CI wiring (`checks.yml`).

**Per R1-N02, deliberately NOT done:** `_safe_join`, `full_snapshot()`, the `paths` init-rewrite, and a
settings schema-version (no concrete settings migration exists, so the version field is omitted).

## 4. Files affected
**Modified product (3):** `scripts/settings.py` (dedup + allowlist), `scripts/common.py` (atomic auth
write + ACL + `import subprocess, tempfile`), `scripts/gui_api.py` (bundle manifest uses the allowlist).
**New test (1):** `build/check_persistence.py`.
**Modified CI (1):** `.github/workflows/checks.yml`.
**Untouched:** `compare_core.py`, the matrix/engine, the updater/TLS, `paths.py`, `report_catalog`,
`tsn_library`, `app.spec` (no new module — the changes live in existing modules; the check isn't
shipped). No persisted-data format change.

## 5. Architectural decisions
- **Reuse the existing `_atomic_write`, moved to the top.** The dedup target already existed; routing
  the four stragglers through it (rather than a new helper) is the minimal change. Moving the def above
  all writers makes the shared writer read top-down.
- **ACL via `icacls`, not pywin32/DPAPI.** `icacls` is a built-in Windows binary (no new dependency, no
  admin for an owned file), invoked **list-form** (no shell → no argument injection) with
  `CREATE_NO_WINDOW` (no console flash on the windowed app) — and works as a plain unsigned exe from a
  user folder (the work-PC constraint). DPAPI is the at-rest *encryption* candidate but binds to
  user+machine and breaks portability, so it stays gated on O2; the ACL is permission-only, so
  `storage_state` stays portable (copying the file to another machine re-inherits that machine's ACL).
- **ACL is best-effort + applied to the temp before the rename.** Best-effort because the file is
  already in the user's profile; applying it to the temp before `os.replace` means `AUTH` is owner-only
  the instant it appears (a security-review fix — closes the brief broad-ACL window).
- **`USERNAME` validated before the icacls arg.** `USERNAME` is just an env var; a value with a `:` or
  `\\` would mis-parse the `account:perm` argument and silently fail to restrict. P6 rejects a
  structurally invalid name (skip + log) rather than issue a malformed grant (security-review fix).
- **Allowlist is an explicit tuple, not `frozenset(DEFAULTS)`.** Deriving it from DEFAULTS would
  auto-include a future key — defeating the purpose. The explicit list + `⊆ DEFAULTS` assert is the
  safeguard.
- **Schema-version omitted (R1-N02).** No concrete settings migration exists, so no ceremony.

## 6. Compatibility and migration handling
- **No persisted-format change, no migration.** `config.json` and `tsmis_auth.json` keep their exact
  shapes/bytes; the changes are the *write path* (atomic) + file ACL + which settings the bundle echoes.
- **Protected contracts preserved** (verified by `check_persistence` + the existing suite): unknown
  keys round-trip through all four routed writers; a corrupt `config.json` still moves aside; an
  existing `config.json` stays readable; the auth file stays portable plaintext JSON (ACL not DPAPI).
- **Backward-readable:** an older config/auth file is read unchanged; a downgrade still reads the files
  (no new required fields).

## 7. Tests and commands run
- **Baseline @ `c0cfa39`:** full suite **59/59**, gates green.
- **New `build/check_persistence.py`** — **16 assertions**, GREEN, ASCII-clean on cp1252:
  settings (4 writers route through `_atomic_write`; unknown-key round-trip; a failed `os.replace`
  raises + prior config intact + no `.tmp`); auth (content round-trips as portable JSON; icacls hits the
  TEMP with `/inheritance:r /grant:r` before the rename; best-effort survives an icacls failure; skipped
  on missing/invalid USERNAME; a failed `os.replace` raises + prior session intact + no temp); bundle
  (allowlist == the explicit set, ⊆ DEFAULTS, excludes site_urls/batch_dest, a future DEFAULTS key is
  not auto-included, `[neg]` a non-DEFAULTS allowlist key fails the subset guard, the manifest line uses
  `support_bundle_settings()`).
- **RED proof:** ran `check_persistence` against the **baseline** (pre-P6) `settings.py`/`common.py`/
  `gui_api.py` (via `git show c0cfa39:`) → FAILS (the dedup-routing assertion fails; the auth ACL test
  errors because baseline `common` has no `subprocess`/ACL path), rc 1; restored → GREEN.
- **Security review** (security-reviewer agent over the diff): no CRITICAL/HIGH; 2 actionable findings
  (MEDIUM USERNAME-validation, LOW ACL-before-rename) **applied**; the atomic-write mechanics,
  list-form subprocess, temp cleanup, and allowlist design were confirmed correct; the bundle confirmed
  to exclude `tsmis_auth.json` and `site_urls`/`batch_dest`.
- **Full suite + gates:** **60/60** Python; `node --check app.js`; `compileall scripts build version.py`;
  `check_import_direction`; `check_app_modules`; `check_no_misspelling`; `git diff --check` clean.

## 8. Results
All green. The four settings writers share one atomic writer; the auth file is written atomically and
best-effort ACL-locked to the owner (DPAPI still deferred); the support bundle echoes only an explicit
allowlist. Suite **59 → 60**.

## 9. Before/after measurements
| Metric | Before (`c0cfa39`) | After |
|---|---|---|
| Settings writers with an inlined `tempfile.mkstemp + os.replace` block | 4 (`update`/`set_site_url`/`set_batch_dest`/`set_matrix_baseline`) | 0 (all route through `_atomic_write`) |
| `tempfile.mkstemp` occurrences in `settings.py` | 5 | 1 (inside `_atomic_write`) |
| `save_auth_state` write | direct `open(AUTH,"w")`, no ACL | atomic temp + `os.replace`, owner-only ACL (icacls) before rename |
| Support-bundle settings source | `all_settings()` (every DEFAULTS key, auto) | `support_bundle_settings()` (explicit allowlist) |
| Offline Python checks | 59 | **60** (+`check_persistence`, 16 assertions) |

## 10. Deviations from the approved plan
- **None on scope.** All three plan deliverables done; the explicitly-dropped items (`_safe_join`,
  `full_snapshot()`, `paths` init-rewrite, settings schema-version) were correctly NOT implemented
  (R1-N02), and DPAPI stays gated on O2.
- **Two security-review hardenings applied beyond the literal plan text** — both in-scope refinements
  to the ACL deliverable, not scope expansion: (a) validate `USERNAME` before the icacls arg (MEDIUM);
  (b) apply the ACL to the temp before the rename (LOW). A third LOW (a hostile process substituting
  `USERNAME` to redirect the grant) is accepted: it requires pre-existing process-env write access, in
  which threat model the auth file is already reachable.
- **`docs/it-and-security.md` auth-at-rest narrative not updated here** — it still reads "protected only
  by NTFS perms; consider DPAPI," which remains *true* (the owner ACL is an NTFS perm; DPAPI is still
  the deferred candidate), so it isn't invalidated. Reconciling it to mention the atomic-write + ACL
  hardening is **P11**'s job (the plan scopes P6 to code; doc reconciliation to P11).

## 11. Known limitations and external verification
- **The ACL tightening is Windows-only + best-effort + work-PC-verified separately.** Offline the check
  stubs `icacls`; the *real* icacls behavior on a managed Caltrans PC (does `/inheritance:r /grant:r`
  succeed for an owned file under the locked-down policy?) is a **work-PC acceptance** step (§M; not in
  the offline DoD). A failure there is non-fatal by design (the file keeps its inherited, owner-readable
  ACL).
- **DPAPI at-rest encryption remains deferred (O2).** The session file is still plaintext JSON
  (portability requirement); the ACL reduces, not eliminates, at-rest exposure.
- **No live sign-in exercised** — `save_auth_state` is driven with a synthetic `storage_state`; a real
  Playwright sign-in writing + the app re-reading the ACL-locked file is a work-PC step.

## 12. Exact diff scope Codex should review
Against baseline `c0cfa39` (exclude `docs/planning/`):
- **`scripts/settings.py`** — `_atomic_write` moved to the top; `update`/`set_site_url`/`set_batch_dest`/
  `set_matrix_baseline` routed through it (inlined write blocks + unused `global` removed); new
  `_SUPPORT_BUNDLE_KEYS` + `support_bundle_settings()` + the `⊆ DEFAULTS` assert. No change to
  `_read_file`/`_clamp`/`get`/the validation/the other setters.
- **`scripts/common.py`** — `import subprocess, tempfile`; new `_restrict_to_owner` (Windows icacls,
  USERNAME-validated, best-effort); `save_auth_state` now atomic + ACL-on-temp-before-rename. No other
  function touched.
- **`scripts/gui_api.py`** — one line: the support-bundle manifest uses `settings.support_bundle_settings()`.
- **`build/check_persistence.py`** (new) — the 16-assertion persistence lock.
- **`.github/workflows/checks.yml`** — one added blocking check line.

Key checks to re-run: `build/check_persistence.py` (+ the baseline RED proof), `build/check_gui_bridge.py`
(settings/export_browser + support bundle), the full 60-check suite, `check_import_direction`,
`check_app_modules`. Security focus: the `icacls` invocation (list-form, USERNAME-validated, temp-before-
rename), the atomic write (no truncation), and the allowlist (no future-leak).

---

# Remediation — Codex review round 1 (`PASS WITH FIXES`)

**Round addressed:** P6 Codex review **round 1** ([`P6-codex-review.md`](P6-codex-review.md)) — verdict
`PASS WITH FIXES`, 0 blocking, **1 required** (**P6-R01**) + **1 recommended** (**P6-A01**). Codex
confirmed the scope, the atomic write, the allowlist (no `batch_dest`/`site_urls`/future-key leak via an
independent bundle smoke), and found no format/contract/packaging regression. Both findings verified
real and addressed.

## Finding dispositions

| ID | Severity | Disposition | One-line resolution |
|---|---|---|---|
| P6-R01 | required | **Fixed** | `_restrict_to_owner` now captures the `subprocess.run` result and LOGS a non-zero `icacls` return (rc + reason) as a best-effort failure, while `save_auth_state` still continues — closing the silent-failure gap; a new check assertion locks it |
| P6-A01 | recommended | **Fixed (applied)** | the support-bundle docstring + manifest NOTE + completion log now say "selected diagnostic settings" / "allowlisted", matching the allowlist change (in-scope product wording, not deferred to P11) |

### P6-R01 — a non-zero `icacls` result is now logged (best-effort) — Fixed
**Verified real** — the round-0 `_restrict_to_owner` ran `subprocess.run([...], check=False)` and
discarded the returned `CompletedProcess`; only an *exception* was logged, so a non-zero `icacls`
return (a real ACL failure — e.g. access denied — that does NOT raise) produced no log and was
indistinguishable from success, contradicting the "failure logged and ignored" contract. Reproduced
Codex's diagnostic (a stubbed `returncode=5` emitted no log).

**Fix** (`scripts/common.py::_restrict_to_owner`): capture `cp = subprocess.run(..., stdout=PIPE,
stderr=STDOUT, text=True, check=False)` (the prior `DEVNULL` is now `PIPE`+merged-stderr so the log can
carry the icacls reason — the "one log upload answers it" contract); on `cp.returncode != 0`,
`log.info("auth: ACL tighten reported a non-zero icacls result (rc=%s)%s; kept the prior inherited
ACL", ...)` with the first non-blank output line. Still strictly best-effort — `save_auth_state` does
not fail on an ACL command failure; the file keeps its prior inherited (owner-readable) ACL. The
exception path and the invalid/missing-`USERNAME` skips are unchanged.

**Check** (`build/check_persistence.py`): a new assertion patches `subprocess.run` to return a
`returncode=5` `CompletedProcess` stand-in and captures `common.log.info`, asserting the
"non-zero icacls result … rc=5" line is emitted AND `save_auth_state` still wrote the file. **RED-proven**:
restoring the pre-fix discard-result `_restrict_to_owner` makes this assertion FAIL.

### P6-A01 — support-bundle wording matches the allowlist — Fixed (applied)
**Verified real** — after P6 the bundle embeds `support_bundle_settings()` (the allowlist), but the
`save_support_bundle` docstring (`gui_api.py:3413-3416`), the manifest NOTE (`:3437`), and the
completion log (`:3474`) still said "current settings" / "settings" — accurate only when the manifest
used `all_settings()`. Applied (this is P6 PRODUCT wording for the change P6 just made, not a `docs/`
reconciliation): the docstring now says "an ALLOWLISTED subset of diagnostic settings
(`settings.support_bundle_settings()`, not `all_settings()` — so no site_urls / batch_dest / future
sensitive key leaks)"; the manifest NOTE and the completion log now say "selected diagnostic settings."
The broader `docs/` narrative reconciliation still belongs to P11.

## Remediation changes (files)

| File | Change |
|---|---|
| `scripts/common.py` | `_restrict_to_owner` captures the `icacls` result + logs a non-zero return (rc + first output line) as a best-effort failure (P6-R01) |
| `scripts/gui_api.py` | support-bundle docstring + manifest NOTE + completion log wording → "selected diagnostic settings" / "allowlisted" (P6-A01) |
| `build/check_persistence.py` | + the non-zero-`icacls`-rc assertion; a `_Completed` `CompletedProcess` stub so the icacls stubs carry a `returncode` (16 → **17** assertions) |
| `docs/planning/v0.18.0/phases/P6-claude-report.md` | this section |

No change to `settings.py`, the atomic-write mechanics, the allowlist set, the `save_auth_state` write
path, or any persisted format. `compare_core` / matrix / engine / updater-TLS untouched.

## Updated verification

```
python build/check_persistence.py            # 17 assertions, ALL GREEN (ASCII-clean on cp1252)
   new: a non-zero icacls return (rc=5) is logged as best-effort failure AND save_auth_state still ok
RED proof: restoring the pre-fix discard-result _restrict_to_owner -> the P6-R01 assertion FAILS (rc 1)
PYTHONIOENCODING=utf-8  python build/check_*.py  (x60)            # 60/60
node --check app.js + compileall + import_direction + app_modules + no_misspelling + git diff --check  # OK
```

## Changed measurements

| Metric | Round 0 | After round-1 remediation |
|---|---|---|
| `check_persistence` assertions | 16 | **17** |
| `icacls` result handling | `run(..., check=False)` + result discarded (non-zero **silent**) | capture; a non-zero return **logged** (rc + reason), still best-effort continue |
| support-bundle wording | "current settings" (stale after the allowlist) | "selected diagnostic settings" / "allowlisted" |

**Status unchanged: `awaiting_review`** — resubmitted for Codex re-review (round 2). Not committed;
planning folder untracked.
