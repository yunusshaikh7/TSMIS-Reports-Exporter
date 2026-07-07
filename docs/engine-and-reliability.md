# Export Engine & Reliability

What this doc covers: the export engine's runtime behavior — the per-route loop, resume/idempotency, skip/cancel, retries, fast-fail paths, timeouts, fast mode, preflight, and the live status/preview/failure-capture seams.

The engine is **console-free**: it reports progress through an `Events` sink and raises exceptions (`AuthError`, `PreflightError`, `ReportError`, …), so the same core backs both the `.bat` console flow and the GUI. See [architecture.md](architecture.md) for the `ReportSpec` / single-loop design and [auth-and-signin.md](auth-and-signin.md) for sign-in and `_recover()` re-auth.

> **Code-level walkthrough:** [internals/export-engine.md](internals/export-engine.md) — the per-route loop step by step, `_recover`/`_retry_failed_routes`, the save-strategy mechanics, and the parallel engine.

Two engines share one per-route loop:

| File | Entry | Role |
|---|---|---|
| `scripts/exporter.py` | `run_export(spec, events, *, routes, timeout_ms, retry_timeout_ms, out_dir)` | Sequential engine (default). Owns the per-route loop, recovery, retry pass, save strategies. |
| `scripts/exporter_parallel.py` | `run_export_parallel(spec, events, *, workers, routes, …)` | EXPERIMENTAL fast mode. N browsers off a shared queue; **reuses** `exporter.py`'s `_process_route`, `_record`, `_capture_failure`, `_retry_failed_routes`, `_wait_while_paused`, `_can_resume`, `_file_looks_complete`. Only concurrency is new. |

`cli.py`'s `run_cli`/`run_cli_multi` route to the parallel engine when `workers > 1`.

---

## The per-route loop

`run_export` (sequential): start Playwright → `new_authed_browser(p)` → `navigate_with_auth` → `require_signed_in` → **`require_site_params(page)`** → `preflight(page, spec.label)` → loop over `routes` (default `ROUTES` from `common.py`). `require_site_params` is the Phase-3 **env backstop**: `navigate_with_auth` accepts the page after one corrective reload WITHOUT re-confirming env/src, so this raises `PreflightError` if the app is still on a different data source / environment than selected — otherwise wrong-env data would be written into a folder LABELED with the selected env and reported as success (it no-ops when the running env/src can't be determined). Mirrors the env-scan's `wrong_site` verdict. For each route:

1. `_wait_while_paused(events)` — hold BETWEEN routes if paused (B1).
2. `events.is_cancelled()` → break the loop cleanly.
3. `maybe_screenshot(page, events, …)` — between-route poll point so a Preview click during a run of already-exists skips still gets answered.
4. `_can_resume(out_path)` → record `exists` and `continue` (resume/idempotency, below).
5. `_process_route(...)` → one route through the attempt/retry/record machinery; returns False to stop the whole run.
6. After the loop (unless cancelled): `_retry_failed_routes(...)` — the end-of-run serial retry pass.

Per-route outcomes flow through `_record(result, events, route, status)`, which appends `(route, status)` to `result.per_route` and calls `events.on_route(route, status)`.

`_attempt_route` is one attempt: select the Route, click Generate, wait on `spec.wait_js(route)` **OR'd with `ERROR_JS`** (`() => ((<ready_js>))() || (<ERROR_JS>)`), then `spec.is_empty(page)`, then `spec.save(page, out_path, timeout_ms)`. Returns `'saved' | 'empty' | 'skipped'`; raises on failure.

### `ReportSpec` and save strategies

A `ReportSpec` (in `exporter.py`) carries everything that differs between reports: `label` (exact `#customReport` dropdown text), `subdir`, `filename(route)`, `wait_js(route)`, `is_empty(page)`, `save(page, out_path, timeout_ms)`. Reusable save strategies:

| Strategy | Used by | Behavior |
|---|---|---|
| `save_pdf_letter` | TSAR Ramp Summary | `page.pdf(format="Letter", print_background=True, margins 0.4in)`. Page already rendered, so `timeout_ms` unused. |
| `save_via_export_button` | Ramp Detail, Highway Sequence, Highway Log, Intersection reports | Click `button.export-btn` filtered `has_text="Export"`; `expect_download` bounded at `min(download_start_timeout_ms(), ceiling)`. On no-download → distinguish site error (`ReportError`) from empty (`EmptyExport`). |
| `save_highway_log_pdf` | Highway Log (PDF), report 4b | Runs the site's global `hl_printAll()` to build the full multi-page layout into `#rampResults`, **overrides `window.print` to throw first** so the site's synchronous restore never runs, then `page.pdf(landscape=True)`. Raises `ReportError` ("no-print-fn" / "no-layout") if the site's Print control is gone. See [reports.md](reports.md). |

Every save ends with `_verify_saved_file(out_path)` (integrity check, below).

---

## Resume / idempotency

`run_export` skips a route whose output file already **exists and passes an integrity check** in today's run folder **for the active src/env** — recorded as `exists`. Delete a file to force a re-download; a new day, or a different environment, always starts a fresh folder (yesterday's files never block today's run). Run folders are `output/<YYYY-MM-DD src-env>/<report>/` via `paths.output_run_dir` (see [architecture.md](architecture.md) for the run-folder model).

### Integrity gate (v0.11.0)

A pre-existing file only counts as "done" if it passes a **magic-byte check** and is non-empty — a half-written/corrupt file from an interrupted run is re-pulled.

`_head_is_complete(suffix, head, size)`:
- `.xlsx` → first 4 bytes must equal `PK\x03\x04` (ZIP container).
- `.pdf` → first 4 bytes must equal `%PDF`.
- Unknown extensions → only need `size > 0`.

`_can_resume(out_path)` (resume path, **lock-tolerant**): if the file doesn't exist → False. If it can be read and is definitively truncated/0-byte → delete it and re-pull (return False). If the file EXISTS but **can't be read** (an `OSError`) → it is almost always a finished export the user has open in Excel (a sharing-deny lock), so it is **trusted and skipped, never deleted** — resume can't turn a done route into a spurious failure by trying to re-download over a locked file.

`_file_looks_complete(out_path)` (fresh-save path, NOT lock-tolerant): used by `_verify_saved_file` after a save we just wrote. A read failure here is a real problem → returns False → the partial file is deleted (so a later resume re-pulls it) and a `RuntimeError` is raised so the route records `failed`.

---

## Completion & artifact outcomes (v0.18.0)

A run's result now carries two ORTHOGONAL, **producer-owned** axes (`scripts/outcome.py`), set from
structured counts, NEVER inferred from human-readable `summary_lines`:

- **completion** — `complete` | `partial` | `no_data` | `cancelled` | `failed`. A run is complete only
  when it covered everything; any failed/skipped input → `partial`; a signed-in env that yields nothing
  for every route → `no_data`. `reduce_completion` rolls per-report completions into one run-level value
  (a mix of complete + no_data is `partial`, never green; an `aborted` multi-report run that didn't
  finish every report is never complete).
- **artifact** — `promoted` | `new_unpromoted` | `previous_preserved` | `none`. Only a **complete**
  refresh `promoted`s into an always-current store; anything else **keeps last-good**
  (`previous_preserved`).

Gates key on these, never on text: `promotable()` (= complete only) guards store-promote (F1) and
cache (F3); `comparable()` lets a partial feed a comparison but flags it. So a **partial run can never be
promoted, cached, or shown green** — the matrix renders a distinct amber **`mx-partial`** cell.

**Transactional consolidation.** Consolidated workbooks are written temp-then-`os.replace`; each carries
a producer-set completion **sidecar** (`scripts/consolidation_meta.py`) written through a fail-safe
ladder (a corrupt/locked/missing sidecar reads as conservative `partial`, never a false green).
`scripts/cache_envelope.py` versions the matrix/by-day caches (one forward rebuild on a schema bump);
`scripts/artifact_store.py` owns the staged store-promote + its interrupted-swap recovery (run on every
launch, before any store is read). The Highway Log PDF consolidator escalates a `skipped_no_geometry`
drop to `partial` (P1), so dropped-line output is never promoted as complete.

## Engine module structure (v0.18.0 — `common.py` is a shim)

`common.py` is now a **re-export shim** over an acyclic set of engine **leaf** modules (`auth_nav`,
`report_nav`, `session`, `site_target`, `routes`, `errors`, `timeouts`, `browser_channels`,
`edge_device`). Existing `from common import X` callers are unchanged; import direction is guarded by
`build/check_import_direction.py`. The fast-fail error classes live in `errors.py` (`ReportError`,
`ReportUnavailableError`) and `exporter.py` (`EmptyExport`); the timeout **accessors**
(`report_timeout_ms()` etc., which read Settings at run time) live in `timeouts.py`.

**P8c live-path hardening (offline-proven; live acceptance owed to v0.18.1).** `select_report` uses an
**exact** option match (no substring mis-pick) — and, as of **v0.18.1**, matches by the option's stable
`data-value` first (falling back to exact text / `data-label`) and reveals the nested `cs-submenu` flyout,
so selection survives the site's flat→nested report-menu migration without breaking the flat prod menu;
every route re-confirms the report dropdown before Generate (`_ensure_report_armed`, the stale-form
guard — as of **v0.19.3** it keys on the hidden `#reportSelect`'s stable `data-value` via
`current_report_value`, **not** the visible `.cs-value` text, so a grouped-menu leaf whose display
label is the short "Detail" no longer false-"drifts" and re-selects on every route; the text read is
the fallback when there's no `data_value`); the sign-in busy-wait gained an **in-loop
cancel check** (`navigate_with_auth(..., should_cancel=…)` polls ~1 s so Stop/Clear interrupt a stuck
login); the Edge sign-in CDP port is opened **on demand** and **closed on capture**; the no-download
empty backstop is marker-independent. See [internals/export-engine.md](internals/export-engine.md).

---

## Skip a slow route

Console `S` key / GUI Skip button → `events.should_skip()`, polled inside `wait_with_skip_option` (in `common.py`). The wait polls `page.wait_for_function` in 5-second chunks so it can honor skip, emit a "still working" status, and enforce the hard timeout independently.

- After `SKIP_PROMPT_AFTER_MS` (60 s) a "still working (Ns elapsed; up to Ns left) — you can skip this route" line appears and the skip hatch opens; thereafter a status line refreshes every 30 s.
- A skipped route is recorded `skipped`, the form is re-armed (`_recover_or_stop`), and the run continues.
- **Skip is disabled during the parallel phase.** `_worker_events` makes `should_skip` a no-op (with several routes in flight, "skip the route being waited on" is ambiguous) — use **Cancel** to stop a fast-mode run.

---

## Cancel

Stops the **current** export immediately, not just between routes. `wait_with_skip_option` checks `events.is_cancelled()` first thing every poll (~5 s) and raises `RunCancelled` mid-wait. `_attempt_route` also re-checks after the wait returns ("cancel landed between the wait and the save"). The engines catch `RunCancelled`, log "Cancelled by user", and stop cleanly — it is **not** a route failure or a worker crash. A partial `RunResult` is returned; re-running resumes. `RunCancelled` and `AuthError` are never retried and never recorded as failed.

**Cancel during the sign-in wait (v0.17.1).** Cancel also interrupts the up-front `navigate_with_auth` sign-in loop, which previously polled nothing and could hold a stuck/failing sign-in for the whole budget (~60 s) — so a matrix-queue **Stop all** / **Clear queued** felt unresponsive while a job was "signing in". `navigate_with_auth(page, *, should_cancel=None)` now polls `should_cancel` once per ~1 s pass and stops early; `run_export` (and the parallel `_preflight_once` + each worker) pass `events.is_cancelled` and, when it fires mid-sign-in, bail **cleanly** — no spurious `AuthError`/login modal (sequential: early `return result`; parallel worker: `raise RunCancelled`; preflight: caller checks `is_cancelled()` and skips launching browsers). Default `should_cancel=None` keeps every other caller unchanged. A genuine login failure still surfaces in ≤ budget with the login modal — but it's now interruptible.

---

## End-of-run serial retry pass

`_retry_failed_routes(page, spec, events, result, out_dir, timeout_ms)` runs after the main loop (skipped when cancelled). Only `failed` routes are retried — not `skipped`, `empty`, or `exists`. Each gets ONE slow, **serial** retry with the more generous `RETRY_REPORT_TIMEOUT_MS` (15 min) ceiling. Rationale: big reports under heavy server load (e.g. Highway Sequence in fast mode) can blow the normal window; a serial retry with no concurrent load is the best chance to land them.

Bookkeeping: the first-pass `failed` records for these routes are dropped (`result.failed` and `result.per_route` filtered by `retry_set`) before re-running, so `_process_route` re-records each route's **final** outcome exactly once — no duplicate run-report rows or double-counted progress. Anything left unrecorded at the end (re-arm failure, cancel, unrecoverable stop) is reconciled back to `failed`. The retry loop also honors `_wait_while_paused`, `is_cancelled()`, and `_can_resume` (a route whose file appeared meanwhile records `exists`).

**Fast mode** runs the same helper in a **single fresh browser** (`_retry_failed_sequential`), so fast-mode retries are sequential too — on the **parallel channel** (Chrome / Built-in Chromium, never managed Edge). The run report is written **after** the retry pass so the CSV reflects final outcomes.

---

## In-loop auto-retry

`_process_route` retries a route once on a **transient (non-timeout)** error: `RETRY_COUNT = 1`, so `for attempt in range(1 + RETRY_COUNT)`. After a transient failure it calls `_recover_or_stop` (re-navigate + re-arm the form) and tries again. **A hard timeout is NOT retried in-loop** (`PlaywrightTimeoutError` is caught separately — the user already had a skip window during the wait — and recorded `failed` immediately). `ReportError` is likewise recorded `failed` immediately without burning an in-loop retry (the end-of-run pass still gives it one more, also-fast attempt).

`_recover(page, spec)` (used by both `_recover_or_stop` and the retry pass): `navigate_with_auth(page)` → `require_signed_in(...)` → `select_report(page, spec.label)`. It raises `AuthError` if the session has died, which ends the run cleanly. See [auth-and-signin.md](auth-and-signin.md) for mid-run re-auth.

---

## Site-error fast-fail (`ReportError`)

A fatal per-route TSMIS error is detected via `common.ERROR_JS`:

```
ERROR_JS = "document.querySelector('#rampResults.error') !== null"
```

The site renders fatal report errors by adding an `error` class to `#rampResults` (e.g. highway_log/hsl set `box.className = 'ramp-results error'`; ramp detail/summary via the shared `showRampResults('error', …)`). `clearResults()` resets that class on each Generate, so it only reflects the CURRENT route — no stale-error false positives. `report_error_text(page)` returns the site's message. The route is recorded `failed` in **seconds** (with message + a failure screenshot) instead of burning the full per-route timeout.

---

## No-download fast-fail (`EmptyExport`, v0.11.0)

In `save_via_export_button`, after clicking Export the engine waits for the download to START, bounded at `download_ms = min(download_start_timeout_ms(), ceiling)` (i.e. capped at `DOWNLOAD_START_TIMEOUT_MS`, 60 s). If no download starts in that window:

- If the site rendered an error (`report_error_text(page)` non-empty) → raise `ReportError` (recorded `failed`).
- Otherwise → raise `EmptyExport()`, recorded **`empty`** in ~60 s instead of hanging the full per-route ceiling (the old empty-route hang was ~21 min).

A no-download `EmptyExport` is a **marker-independent** safety net: `is_empty` may not catch a drifted empty marker, but the no-download guard does. The site builds every Excel export client-side (SheetJS serializes already-rendered rows synchronously), so a non-empty report's download fires within a second — the per-route ceilings size report GENERATION, not this window. `DOWNLOAD_START_TIMEOUT_MS` is settings-backed (`download_start_timeout_s`) but has **no Settings-tab control** — raise it by hand-editing `data/config.json` only if a real report legitimately needs longer.

**Retry-once before trusting it (Phase-3 fix).** A no-download `EmptyExport` is INCONCLUSIVE — a transient flake in the export-click window looks identical to a real no-op. So `_attempt_route` no longer collapses it to `"empty"`; it **propagates** the `EmptyExport`, and `_process_route` retries the route once in-loop (`attempt < RETRY_COUNT`), recording **`empty` only if it reproduces**. A POSITIVE `is_empty` match still short-circuits to `"empty"` immediately (authoritative). This stops a populated route whose Export click flaked from being reported as benign "No data" and never retried. Locked by `check_export_engine.py` (`test_process_route_empty_retry`); ⚠ the true transient flake is only reproducible live on the work PC.

> NOTE on `EXPORT_READY_JS`: this is a SEPARATE readiness signal — a report's post-Generate `wait_js` keys on the Export button's text (`button.export-btn` filtered `/export/i`, not a Print-only bar) to know the report rendered. It is NOT the no-download detector; the detection above is purely the download-start timeout. CLAUDE.md describes the EmptyExport guard as keying on "Export control ready, no download (`EXPORT_READY_JS`)", which is a framing drift — see the discrepancies note.

### `ReportUnavailableError` (greyed-out report, `cs-disabled`)

The site greys a temporarily-disabled report's `<li>` with the `cs-disabled` class. `select_report` reads the option's classes and, if `cs-disabled` is present, raises `ReportUnavailableError` (a `PreflightError` subclass) with a "currently unavailable" message — caught **at preflight time**, BEFORE the inert dropdown click would stall ~30 s into a generic preflight failure. This is a preflight/select-report path, not a per-route loop fast-fail.

---

## Timeouts (`scripts/common.py`)

| Constant | Default | Purpose |
|---|---|---|
| `REPORT_TIMEOUT_MS` | 360_000 (6 min) | Per-route ceiling, sequential flow |
| `FAST_REPORT_TIMEOUT_MS` | 600_000 (10 min) | Per-route ceiling, fast mode (server under load) |
| `RETRY_REPORT_TIMEOUT_MS` | 900_000 (15 min) | Per-route ceiling, end-of-run retry pass |
| `SKIP_PROMPT_AFTER_MS` | 60_000 (1 min) | When the "still working" status + skip hatch open |
| `COUNTY_ENABLE_TIMEOUT_MS` | 60_000 (60 s) | Max wait for the County dropdown to enable |
| `DOWNLOAD_START_TIMEOUT_MS` | 60_000 (60 s) | Max wait for a download to START after Generate; elapsing ⇒ `EmptyExport` no-data fast-fail (capped at `min(60 s, ceiling)`) |
| `RETRY_COUNT` | 1 | In-loop retries after a transient (non-timeout) failure |

Increase these if the TSMIS server is slow. **The constants are the DEFAULTS.** Since v0.10.0 the GUI Settings tab overrides the four ceilings (persisted via `settings.py`), and engines read them at run time through accessor functions — **call the accessors, not the constants, when editing engine code**:

| Accessor | Reads setting (× unit) | Default |
|---|---|---|
| `report_timeout_ms()` | `report_timeout_min` × 60_000 | `REPORT_TIMEOUT_MS` |
| `fast_report_timeout_ms()` | `fast_timeout_min` × 60_000 | `FAST_REPORT_TIMEOUT_MS` |
| `retry_report_timeout_ms()` | `retry_timeout_min` × 60_000 | `RETRY_REPORT_TIMEOUT_MS` |
| `county_enable_timeout_ms()` | `county_timeout_s` × 1_000 | `COUNTY_ENABLE_TIMEOUT_MS` |
| `download_start_timeout_ms()` | `download_start_timeout_s` × 1_000 | `DOWNLOAD_START_TIMEOUT_MS` |

`_settings_ms` never lets a settings read stop a run — it logs and falls back to the default on any exception. Environment variables still win where one exists. `SKIP_PROMPT_AFTER_MS` has no accessor (used directly in `wait_with_skip_option`). `DOWNLOAD_START_TIMEOUT_MS` is config.json-only (no Settings UI).

---

## Fast Mode (experimental, `exporter_parallel.py`)

N headless browsers restore the **same** saved session and pull routes off a shared `queue.Queue` until empty. Additive — the sequential engine is untouched and remains the default. Same contract: merged `RunResult`, same errors, honors cancel, resumes, auto-saves the CSV; **one preflight** (`_preflight_once`) before launching N browsers so a bad session or changed site fails fast with one clear error instead of N.

Why a shared queue, not static route shards? A few routes (5, 99, 101…) take minutes while most take seconds; a queue is self-balancing, so no worker gets stuck with all the slow ones.

**Worker counts** (`DEFAULT_WORKERS = 3`, `MAX_WORKERS = 30`): the limit is the **client PC, not the server** (operator testing shows the TSMIS backend handles high concurrency fine). Each worker is one Chromium process (~300–500 MB under load) plus a Playwright driver — budget **~0.5 GB RAM per worker**:

- **3** browsers — safe default, ~2.5–3× faster.
- **8–12** browsers — big speedup on a healthy multi-core PC with RAM to spare.
- **30** browsers — hard cap (~9–15 GB RAM for browsers alone; only on a well-resourced machine).

Requested counts are clamped to `[1, MAX_WORKERS]` (`resolve_worker_count`); `requested=None` falls back to `TSMIS_FAST_WORKERS`, then the saved Settings default (`default_worker_count` → `settings.get("fast_workers")`). Turn on via `5. fast export…bat` (`TSMIS_FAST_WORKERS`) or the GUI "⚡ Fast mode" checkbox + spinner. `n` is also clamped to `min(n, total) or 1`.

**Threading:** Playwright's sync API is thread-affine, so each worker owns its OWN `sync_playwright()` instance, browser, context, and page — nothing shared across threads except the work queue, a few `threading.Event`s (`stop`, `auth_failed`, `worker_crashed`), and per-worker `RunResult`s merged at the very end. Worker threads are named `export-w{n}`. A crashed worker never silently drops routes: the others keep draining, and any route with no recorded outcome is reconciled as `failed` after the join (the `_reconcile_unaccounted` helper). An `AuthError` in any worker sets `auth_failed` → re-raised as `AuthError` so the driver can clear the stale file and prompt a re-login.

**Reconciliation (Phase-3 fixes, locked by `check_parallel_reconcile.py`).** `_reconcile_unaccounted(routes, result, out_dir, spec, events, *, cancelled, worker_crashed)`: (a) it uses the lock-tolerant **`_can_resume`** (NOT the read-strict `_file_looks_complete`), so a route whose file the worker saved before crashing but the user has open in Excel (sharing-deny lock) is TRUSTED as present, not re-marked `failed` and needlessly re-downloaded; (b) it normally skips on a clean cancel (unreached routes are simply not-done, resume later) **but still runs when a worker CRASHED, even on cancel**, so a crash's orphaned route(s) always reach the run report instead of vanishing.

**Device sign-in caps fast mode to 1 worker:** if there's no saved session, `new_authed_browser` falls back to the persistent Edge sign-in profile, which can only be open in ONE browser — so a requested `n > 1` is forced to 1 (with a log line). The GUI greys the Fast-mode checkbox without a saved login. See [auth-and-signin.md](auth-and-signin.md).

### Parallel browsers AVOID managed Edge

Field failure: N concurrent headless Edge instances restoring the same saved session timed out (org-managed Edge misbehaves under concurrency). Every saved-session browser that runs ALONGSIDE OTHERS — fast mode's workers, its `_preflight_once`, its serial retry pass, and the env scan's scanners — launches with `new_authed_browser(p, parallel=True)` → `launch_browser(..., parallel=True)` → `common._parallel_candidates()`:

- Order: **Built-in Chromium, then Chrome, Edge only as a warned LAST resort.**
- A UI pick of Edge is deliberately **not** honored for parallel work (honoring it is what caused the failure); the hard `TSMIS_BROWSER_CHANNEL` env override still wins for debugging.
- The parallel channel keeps its own process cache (`_resolved_parallel`, separate from `_resolved_channel`).
- Edge keeps its one-click device sign-in role untouched (that flow is sequential by design).

`resolve_parallel_channel(p)` lets callers decide whether running several at once is wise: `"msedge"` returned here means **nothing but managed Edge is usable**, and the env scan then drops to ONE browser instead of risking three concurrent Edge sessions. The full managed-Edge avoidance narrative lives in [lessons.md](lessons.md). The sequential single-browser engine keeps the normal channel order (`chromium` when present → `msedge` → `chrome`; `_candidate_channels`).

---

## Preflight (`common.preflight`)

After login, before the loop, `preflight(page, report_label)` confirms the report form looks as expected:

1. `#customReport` (the report dropdown) must be present, else `PreflightError` + a `preflight_fail_*` page dump.
2. `select_report(page, report_label)` (which itself raises `ReportUnavailableError` on a `cs-disabled` report).
3. The Route control (`get_by_label("Route", exact=True)`) must attach within 15 s.
4. The Generate button must attach within 15 s.

Any failure raises `PreflightError` (UI-neutral message naming the failed step in the log) and dumps a `preflight_fail_*` screenshot, so a TSMIS change fails fast with one clear error instead of every route failing cryptically.

`SiteUnreachableError` (a `PreflightError` subclass) covers "couldn't open the page at all" (network/VPN/DNS) with a check-your-connection message. `ReportUnavailableError` (also a `PreflightError`) is the `cs-disabled` greyed-report case. All three subclass `PreflightError` so every driver shows the message as-is.

---

## Failure screenshots (`FAILURES_DIR`)

On final failure, `_capture_failure(page, spec, route, events)` writes `<subdir>_route_<route>_<YYYYMMDD_HHMMSS>.png` + `.html` to `FAILURES_DIR` (best-effort — it never raises, so a capture problem can't mask the original error). The screenshot is the **viewport** (`full_page=False`), not the full page: the failure state worth capturing (error box, button state) is above the fold, and this avoids writing the whole report image to disk. `FAILURES_DIR` is deliberately **never** added to the shareable support bundle (it can contain report content). Sign-in/preflight failures dump `auth_fail_*` / `preflight_fail_*` separately — see [auth-and-signin.md](auth-and-signin.md).

---

## Live per-browser status + previews (v0.10.0, GUI)

The engines emit a one-line per-browser status through `events.on_status(worker_no, text)` — phase changes ("generating…", "saving…", "Recovering…", "Done") plus a heartbeat inside `wait_with_skip_option` (`"… working… (Ns)"`, refreshed each poll chunk). The GUI shows one row per browser in the progress card.

Each row's **Preview** button requests a screenshot. Because Playwright is thread-affine (only the owning thread may touch the page), the request is answered at the worker's next safe poll point via `common.maybe_screenshot(page, events, note=…)`: it checks `events.screenshot_wanted(worker_no)`, captures the current **viewport** as JPEG (`type="jpeg", quality=70`), and hands the bytes to `events.on_screenshot` along with the page's address. The poll points are: between routes in the main loop, inside `wait_with_skip_option`, and once just before a save grabs the page (a blocking download wait can't answer requests until it returns, so the next route answers any request that lands during it).

`common.page_url_for_display(page)` strips the URL fragment before the address reaches the screen — the OAuth token rides in the hash and must never be displayed. The `Events` seam (`worker_no`, `on_status`, `screenshot_wanted`, `on_screenshot`) is no-op in the console flow. The GUI side of this (progress card, per-browser rows, modal) is in [gui.md](gui.md).

---

## Run report (`scripts/run_report.py`)

Every route's outcome is recorded (`saved` / `empty` / `skipped` / `failed` / `exists`) and **auto-saved** after each run to `output/run_reports/<subdir>_<src-env>_run_<timestamp>.csv` (`auto_report_path` → `RUN_REPORTS_DIR = OUTPUT_ROOT / "run_reports"`). The CSV columns are `Report, Route, Status, Run At`, with friendly status labels (`FRIENDLY_STATUS`: saved→"Saved", empty→"No data", skipped→"Skipped", failed→"Failed", exists→"Already had"). A write failure here is non-fatal (logged, not raised). `write_run_report_multi` writes several reports' rows to one CSV when the GUI exports several report types at once; the GUI "Save run report…" copies the auto-saved file elsewhere.

`RunResult` (from `events.py`) carries `saved` (count), `empty`, `user_skipped`, `failed`, `exists` (lists), `per_route` (the `(route, status)` log), `output_dir`, and `report_path`.

---

## See also

- [architecture.md](architecture.md) — `ReportSpec` / single-loop design, run folders, registry.
- [auth-and-signin.md](auth-and-signin.md) — sign-in, `_recover()` mid-run re-auth, device-mode worker cap.
- [gui.md](gui.md) — the GUI worker/queue model, progress card, preview modal, pywebview traps.
- [lessons.md](lessons.md) — the managed-Edge-under-concurrency field-failure narrative.
- [reports.md](reports.md) — per-report specifics (Highway Log PDF print override, etc.).
- [verification-and-testing.md](verification-and-testing.md) — the `build/check_*.py` golden guards covering the engine.
