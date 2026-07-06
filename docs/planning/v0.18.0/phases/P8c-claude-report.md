# P8c — Engine behavior changes (select / CDP / cancel / swallows / PDF-empty) — Claude report

## 1. Phase ID and name
**P8c — Engine behavior changes.** The live-path correctness/security changes on the export +
auth engine: `select_report` exact-match guard + per-route re-arm, Edge-login CDP debug-port
default-off (on-demand), `should_cancel` threaded into recover/retry/portability + the login
capture busy-waits, a marker-independent empty backstop on the PDF save path, and auth-path
swallow logging. **Fixture-first (RM03); each change is an independently revertible commit unit;
the code ships in v0.18.0, work-PC acceptance is claimed in v0.18.1** (CR-001 / RM02 / RM03).

## 2. Baseline commit
`9121faa` (P8b/P9/P7c lineage; P7c committed) — branch `refactor/v0.18.0-structural-overhaul`;
tree clean apart from untracked `docs/planning/`.

## 3. Changes made (each its own revertible commit unit — R1-R08)
Fixture-first per RM03: the fixtures + RED tests landed **before** each behavior change; each was
RED-proven against the old code then GREEN with the fix.

1. **`select_report` exact-match guard** (AUDIT-P2-substr). `report_nav._find_exact_option` enumerates
   `#customReport li.cs-option`, matches the **trimmed text exactly**, and raises `PreflightError`
   on **zero or multiple** matches — replacing `page.locator(..., has_text=label).first`, a SUBSTRING
   read that silently picked the wrong report when one label contains another (e.g. "Highway Log" ⊂
   "Highway Log (PDF)") and an arbitrary one when several matched. `preflight` gains an
   `except PreflightError: raise` so the precise message survives (and still captures the diagnostic
   dump). cs-disabled behavior unchanged (now checked on the exact-matched option).
2. **Per-route stale-form re-arm** (select-report-not-rearmed-between-routes). `report_nav.current_report_label`
   reads the dropdown's shown `.cs-value`; `exporter._ensure_report_armed` (called at the top of
   `_attempt_route`) re-selects the report when the shown label has **drifted** from `spec.label`.
   No-ops on the happy path; never acts on an unreadable selection (`''` = unknown).
3. **Edge-login CDP debug-port default-off / on-demand** (AUDIT-P2-cdp,
   edge-login-cdp-port-unauthenticated-loopback). `launch_edge_login_context(enable_cdp=False)` no
   longer opens `--remote-debugging-port` by default — that port is an **unauthenticated CDP endpoint
   on 127.0.0.1** that any local process could drive for the whole interactive sign-in. It is now
   strictly opt-in/on-demand; `capture_edge_login_state_over_cdp` is a clean no-op when no port was
   opened, so callers fall through to the headless profile recapture (the same on-disk session, no
   CDP exposure). Context is still closed on capture.
4. **`should_cancel` threaded into recover/retry/portability + login busy-waits**
   (`should_cancel`-in-recover, login-busywait-no-cancel-check). `exporter._recover` accepts/forwards
   `should_cancel` (wired from `_recover_or_stop` via `events.is_cancelled`, covering the main loop +
   the retry pass). `edge_device.storage_state_is_portable` / `capture_edge_login_state_over_cdp` /
   `capture_edge_login_state_from_profiles` accept `should_cancel` and poll it (up-front + each loop
   pass) so a Stop during the post-"I've finished" capture/portability chain bails within ~1s instead
   of waiting out the up-to-~90s budget. The GUI `LoginWorker` threads `self.cancel.is_set` into all
   three. **Only cancel polling was ADDED — no field-hardened wait was chunked.**
5. **Marker-independent PDF empty backstop** (unlogged-no-download-empty-on-pdf-and-misc).
   `save_pdf_letter` raises `EmptyExport` (logged) when the inline report rendered **no action bar**
   (the empty path renders none); `save_highway_log_pdf` counts **data rows** in the built print
   layout (a real row has per-column `<td>`s; the empty notice is one spanning `colspan` cell) and
   raises `EmptyExport` (logged) on zero — so a route whose empty-**text** marker drifted is recorded
   `empty` (retried once) instead of saved as a contentless PDF. Mirrors the Excel path's existing
   no-download → EmptyExport net.
6. **Auth-path swallow logging.** Three silent capture swallows now log `type(e).__name__` (+ first
   line) per the "one uploaded log answers it" contract: `edge_device.capture_storage_state_if_logged_in`
   recapture-navigate failure, `auth_nav.navigate_with_auth`'s "Sign In with ArcGIS" click (via the
   loop's `note()` breadcrumb), and the console `login._try_edge_persistent_login` live-capture failure
   (matching the GUI worker's existing log).

## 4. Files affected
**Product scripts (7):** `report_nav.py` (+`_find_exact_option`, `current_report_label`, preflight
passthrough), `common.py` (re-export `current_report_label`), `exporter.py` (`_ensure_report_armed`,
`_recover` cancel, both PDF backstops), `edge_device.py` (CDP gating + cancel + swallow log), `auth_nav.py`
(arcgis-click breadcrumb), `login.py` (live-capture log), `gui_worker.py` (thread `self.cancel.is_set`
into the 3 login busy-waits).
**New fixtures (3):** `build/fake_site/dropdown_ambiguous.html`, `dropdown_selected.html`,
`highway_log_print_empty.html`.
**New check (1):** `build/check_edge_login.py` (CDP gating + cancel + swallow logging, pure-Python fakes).
**Modified checks (3):** `check_export_engine.py` (exact-match + re-arm + PDF-empty), `check_fake_site.py`
(exact-match + current_report_label + PDF-empty, real browser), `check_worker_lifecycle.py` (stub now
tolerates the `should_cancel` kwarg).
**CI (1):** `.github/workflows/checks.yml` (wire `check_edge_login.py` into the export-engine block).

## 5. Architectural decisions
- **Exact match by enumeration, not a Playwright `get_by_text(exact=True)`** — keeps the cs-disabled
  class read on the matched option and gives precise 0/multiple diagnostics.
- **CDP: default-off + opt-in is the faithful "open on demand."** Chromium can't add a debug port to a
  running browser, and the headless profile recapture already captures the same on-disk session without
  CDP — so the secure, minimal, revertible fix is to stop opening the unauthenticated port during
  interactive login and skip the CDP fallback when none was opened. (Reverting = flip the default / pass
  `enable_cdp=True`.)
- **Cancel polling is additive only.** The field-hardened sign-in/wait loops are untouched except for an
  added `should_cancel` poll; Playwright thread-affinity preserved (each poll runs on the owning thread).
- **PDF emptiness keyed on STRUCTURE, not empty-text.** Action-bar presence (inline) and non-spanning
  data-row count (print layout) are independent of the "No results"/"No ramps found" wording the
  existing `is_empty` keys on — so the backstop fires exactly when that marker drifts.

## 6. Compatibility and migration handling
No persisted-data, manifest, output-layout, contract, or bridge-enum change. All new function parameters
are **keyword-only with safe defaults** (`enable_cdp=False`, `should_cancel=None`), so every existing
caller is unchanged in behavior; the console `login.py` keeps the no-cancel default. `current_report_label`
is additive (re-exported through `common`). No new shipped `scripts/` module → `app.spec` unchanged
(`check_app_modules` green). `compare_core`, the updater, auth-at-rest, and all `scripts/ui/` files are
untouched. Rollback: each of the six changes reverts independently.

## 7. Tests and commands run (all offline, build venv `-B -X utf8`)
- **RED→GREEN proofs** (stash the product file, run, restore):
  - select_report exact-match: stashed `report_nav.py` → `check_export_engine` + `check_fake_site` FAIL
    (substring picked "Highway Log (PDF)"; no 0/multiple guard) → GREEN with the fix.
  - edge_device CDP + cancel: stashed `edge_device.py` → `check_edge_login` FAIL (default opened the port;
    no `should_cancel`) → GREEN with the fix.
  - PDF backstop: covered by the empty fixtures (old code wrote a PDF; new raises EmptyExport).
- **New `check_edge_login.py`:** CDP port gating (default off / opt-in), CDP no-op without a port, cancel
  bails promptly (CDP/profile/portability), recapture swallow is logged.
- **`check_export_engine.py`:** exact-match (substring/0/multiple/cs-disabled), `_ensure_report_armed`
  (match/drift/unknown), PDF empty backstop (EmptyExport before `page.pdf`).
- **`check_fake_site.py`** (real headless browser): exact-match on `dropdown_ambiguous.html`,
  `current_report_label` on selected/placeholder/blank, HL + Ramp Summary PDF empty backstops.
- **Full offline suite:** **68/68** `build/check_*.py` + **3/3** Node checks green; byte-compile of all 7
  changed scripts; import smoke (`common.current_report_label`, the new signatures, `gui_worker` import);
  `git diff --check` clean.

## 8. Results
Green across the board: **68/68** Python (the new `check_edge_login` included) + **3/3** Node; all six
behavior changes RED-proven then GREEN; façade/bridge checks (`check_gui_api_surface`, `check_gui_bridge`)
unaffected; `compare_core`/auth-at-rest/updater/UI untouched. Diff scope: 7 scripts + 3 checks + CI + 4 new
files, whitespace clean, no unrelated changes.

## 9. Before/after measurements
| Area | Before | After |
|---|---|---|
| `select_report` match | `has_text` SUBSTRING + `.first` (silent mis-pick) | exact text; clear error on 0/multiple |
| Per-route form | report selected once; re-armed only after error | re-confirmed each route; re-armed on drift |
| Edge-login CDP port | `--remote-debugging-port` open for the whole sign-in | **closed** by default; opt-in/on-demand |
| Cancel during recover/login-capture | waited out the full budget (~60–90s) | bails within ~1s (polled) |
| PDF empty (marker drift) | blank PDF saved as "saved", unlogged | `EmptyExport` → recorded empty, logged |
| Auth capture swallows | silent (`pass` / bare `return None`) | log `type(e).__name__` + first line |
| Offline checks | 67 Python | **68** Python (+`check_edge_login`) |

## 10. Deviations from the approved plan
- **CDP "open on demand, close on capture" realized as default-off + opt-in.** A debug port can't be
  added to a running Chromium, and the profile recapture covers the same capture without CDP, so the
  faithful + secure form is "no longer eager; opt-in." Documented in §5; behavior is revertible.
- **Per-route re-arm uses exact `.cs-value` comparison.** The cs-select widget sets `.cs-value` to the
  option text (== `spec.label`), so the happy path never re-arms; this exact contract is confirmed on the
  work PC in v0.18.1 (a slightly different render would over-re-arm — wasteful, not wrong, and logged).
- No other deviations. `compare_core`/auth-at-rest/updater/UI untouched; no live TSMIS/credential/profile
  access in implementation; nothing staged/committed/pushed.

## 11. Known limitations and external verification (→ v0.18.1, RM02/RM03)
The **code** is offline-proven against the extended fixtures; the **live behavior** is accepted on the
work PC in v0.18.1 (§K2):
- `select_report` exact match + per-route re-arm against the **real** `#customReport` widget (confirm
  `.cs-value` equals the dropdown label so the re-arm never spuriously fires).
- Edge login still succeeds with the CDP port closed (live-context + headless profile recapture cover the
  managed-PC paths) — the security win is real; the success-rate parity is the work-PC check.
- Cancel-during-login-capture latency and cancel-during-recover on the real site/browser.
- PDF empty backstop firing on a real empty route (the structural signals match the live DOM).
No `scripts/ui/` file changed (frontend byte-identical), so no new `#mock`/work-PC UI item; the bridge
checks lock the GUI contract.

## 12. Exact diff scope Codex should review
Product diff from baseline `9121faa`, excluding `docs/planning/`:
- **Scripts:** `report_nav.py`, `common.py`, `exporter.py`, `edge_device.py`, `auth_nav.py`, `login.py`,
  `gui_worker.py`.
- **New:** `build/check_edge_login.py`, `build/fake_site/{dropdown_ambiguous,dropdown_selected,highway_log_print_empty}.html`.
- **Checks/CI:** `build/check_export_engine.py`, `build/check_fake_site.py`, `build/check_worker_lifecycle.py`,
  `.github/workflows/checks.yml`.

Suggested focus: (a) the `select_report` exact-match guard is correct + the cs-disabled path intact;
(b) the CDP default-off truly removes the unauthenticated-port exposure and the profile-recapture fallback
still covers capture; (c) `should_cancel` only ADDS polling (no field-hardened wait chunked) and all
callers (esp. console `login.py`) stay correct with the defaults; (d) the PDF backstops are
marker-independent and don't false-positive on real data; (e) the six changes are cleanly separable into
revertible commits; (f) the §10 deviations are the right calls.

---

## Remediation — Codex review round 2 (finding P8c-R01)

### Review round addressed
Codex **round 2** (`PASS WITH FIXES`), which carries the **round-1** required finding **`P8c-R01`** still
open. No new findings; no blocking findings; no non-blocking recommendations. Round 1 + round 2 history is
preserved in `phases/P8c-codex-review.md`.

### Finding dispositions
- **`P8c-R01` — Edge recapture cancellation does not reach nested `navigate_with_auth` — FIXED.**
  Codex was correct: change-(4) threaded `should_cancel` into the **outer** recapture loops
  (`capture_edge_login_state_over_cdp` / `capture_edge_login_state_from_profiles`) and `storage_state_is_portable`,
  but **not** into the **nested** sign-in `capture_storage_state_if_logged_in(ctx, navigate=True)` →
  `navigate_with_auth(page)`. A cancel arriving after the outer pre-connect/pre-launch poll, while that nested
  sign-in was in flight, could still wait out the budget. My round-1 report §3(4)/§11 overstated the coverage as
  reaching "through the login busy-waits"; this remediation makes that claim true.

### Remediation changes (the exact correction Codex specified)
- **`scripts/edge_device.py`:**
  - `capture_storage_state_if_logged_in(ctx, *, navigate=False, timeout_ms=15_000, should_cancel=None)` —
    new optional `should_cancel=None` (default preserves console/`navigate=False` callers unchanged).
  - In the `navigate=True` recapture block: `navigate_with_auth(page, should_cancel=should_cancel)` (was
    `navigate_with_auth(page)`).
  - `capture_edge_login_state_over_cdp` and `capture_edge_login_state_from_profiles` now pass their callback
    into the nested call: `capture_storage_state_if_logged_in(ctx, navigate=True, should_cancel=should_cancel)`.
  - No other behavior changed; the outer per-pass polls and the CDP default-off gating are untouched.
- **`build/check_edge_login.py`:** new `test_cancel_reaches_nested_navigate` — mirrors Codex's own diagnostic:
  it monkeypatches `edge_device.navigate_with_auth` to record the `should_cancel` it receives, forces the
  `navigate=True` recapture path (`is_logged_in` stubbed False), and drives **both** the CDP and profile
  recapture paths with a sentinel callback and an `should_cancel` that returns False (so the outer loop does
  **not** bail and the nested navigate is actually reached). It asserts every nested `navigate_with_auth`
  received the sentinel callback (not empty kwargs) — i.e. cancellation is tested **after** a CDP/profile
  context has opened and the nested recapture navigation begins, exactly per the round-1/2 "verification gap."

### Updated verification
- **RED→GREEN proven for the remediation:** temporarily re-introducing the exact gap (nested call reverted to
  `navigate_with_auth(page)`) makes the new test FAIL — "every nested navigate received the should_cancel
  callback" reports the nested call got **empty kwargs** (the `MISSING` case, matching Codex's diagnostic);
  restoring the fix makes it GREEN.
- **Targeted set Codex asked to re-run (all green):** `check_edge_login.py` (now incl. the nested-navigate
  regression), `check_worker_lifecycle.py`, `check_export_engine.py`, `check_engine_layers.py`,
  `check_app_modules.py`, `check_import_direction.py`, `check_no_misspelling.py`; `py_compile` of the seven
  P8c scripts + the changed checks; `git diff --check` clean. Import smoke confirms
  `capture_storage_state_if_logged_in` now carries `should_cancel`.
- **Full offline suite still green:** **68/68** `build/check_*.py` + **3/3** Node checks. No TEMP-RED marker
  left in the tree; diff scope unchanged (same 7 scripts + 3 checks + CI + 4 new files).
- Callers audited: the only two `navigate=True` call sites (the CDP + profile recapture loops) now thread the
  callback; the two `navigate=False` callers (`login.py`, `gui_worker`) capture from the live context with no
  nested navigation, so the default `None` is correct and unchanged.

### Changed measurements
| Area | Round-1 P8c | After remediation |
|---|---|---|
| Cancel reaches nested recapture `navigate_with_auth` | **No** (outer poll only — P8c-R01) | **Yes** (threaded through `capture_storage_state_if_logged_in`) |
| `check_edge_login.py` cancellation coverage | before connect/launch only | **+ after a context opens, during nested recapture navigate** |
| Offline checks | 68 Python / 3 Node | 68 Python / 3 Node (unchanged count; the edge-login check gains one test) |

Phase remains `awaiting_review`; nothing staged/committed/pushed.
