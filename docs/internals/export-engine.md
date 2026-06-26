# Export Engine Internals

Deep code-level walkthrough of the export loop — every step from `run_export` to a saved file, the save strategies' mechanics, the integrity gate, the skip/cancel/heartbeat wait, recovery/retry, and the parallel engine. Companion to the scannable [../engine-and-reliability.md](../engine-and-reliability.md) (read that first for the "what/why"; this is the "how it actually works").

Files in scope:

| File | Contents |
|---|---|
| `scripts/exporter.py` | Sequential engine + `ReportSpec` + the three save strategies + the integrity gate + the per-route loop, recovery, and retry pass. Everything reusable. |
| `scripts/exporter_parallel.py` | Fast mode: N browsers off a shared queue. **Imports** the per-route mechanics from `exporter.py`; only concurrency is new. |
| `scripts/common.py` | `preflight`, `select_report`, `wait_with_skip_option`, `launch_browser`/channel resolution, `new_authed_browser`, the report-ready/error JS, `report_error_text`, `maybe_screenshot`, `report_*_timeout_ms()` accessors. **(v0.18.0: `common.py` is now a re-export SHIM over the acyclic engine leaves — `auth_nav`/`report_nav`/`session`/`site_target`/`routes`/`errors`/`timeouts`/`browser_channels`/`edge_device`. `from common import X` is unchanged, so the symbols + `common.py:NNN` line refs in this doc resolve through the shim; the live implementation sits in the named leaf.)** |
| `scripts/events.py` | `Events` sink (the engine↔driver seam) + `RunResult`. |

---

## 1. Module map / who-calls-what

```
cli.run_cli / run_cli_multi
  └─ workers>1 ? exporter_parallel.run_export_parallel : exporter.run_export
       │
exporter.run_export(spec, events, *, routes, timeout_ms, retry_timeout_ms, out_dir)
  ├─ has_valid_auth()                       (common)  notice-only, not fatal
  ├─ sync_playwright() as p
  ├─ new_authed_browser(p)                  (common)  saved session OR device mode
  ├─ navigate_with_auth(page)               (common)  drives the OAuth hop
  ├─ require_signed_in(page, msg)           (common)  AuthError if not
  ├─ require_site_params(page)              (common)  PreflightError on wrong env/src (Phase-3 backstop)
  ├─ preflight(page, spec.label)            (common)  PreflightError if form wrong
  └─ for route in routes:
        _wait_while_paused(events)                    B1 hold between routes
        events.is_cancelled() -> break
        maybe_screenshot(page, events, …)   (common)  answer a Preview click
        _can_resume(out_path) -> record "exists", continue
        _process_route(page, spec, route, prefix, out_path, events, result, timeout_ms)
            for attempt in range(1 + RETRY_COUNT):
                _attempt_route(…)                     one Generate→wait→save
                    select Route, click Generate
                    wait_with_skip_option(page, wait_js OR ERROR_JS, …)   (common)
                    report_error_text(page) -> ReportError                (common)
                    spec.is_empty(page) -> "empty"
                    maybe_screenshot(…)
                    spec.save(page, out_path, timeout_ms)
                        save_pdf_letter / save_via_export_button / save_highway_log_pdf
                        └─ _verify_saved_file(out_path)
        _retry_failed_routes(page, spec, events, result, out_dir, retry_timeout_ms)
```

The parallel engine substitutes its own `worker(idx)` for the `for route` loop but calls the **same** `_can_resume`, `_process_route`, `_record`, `_capture_failure`, `_file_looks_complete`, `_retry_failed_routes`, `_wait_while_paused`, imported at `exporter_parallel.py:63`.

---

## 2. `run_export` — the sequential entry point (`exporter.py:504`)

### 2.1 Setup, before the browser opens

1. `events = events or Events()` (`exporter.py:520`) — a bare `Events()` is a valid silent sink (`events.py:70`), so the engine is driver-agnostic.
2. `has_valid_auth()` is checked **only to log a notice** (`exporter.py:526`): a missing session is no longer fatal — `new_authed_browser` falls back to device sign-in mode. This is the deliberate change documented in the docstring at `exporter.py:521`.
3. Timeouts are resolved through the **accessors**, not the constants: `timeout_ms or report_timeout_ms()` and `retry_timeout_ms or retry_report_timeout_ms()` (`exporter.py:529-530`). Always call the accessor — `_settings_ms` (`common.py:232`) reads the Settings override and **falls back to the constant on any exception** (a settings read can never stop a run, `common.py:236`).
4. `src, env = get_site()` (`exporter.py:536`) snapshots the active data-source/environment **once, at run start**.
5. Output directory (`exporter.py:539`):
   ```python
   out_dir = Path(out_dir) if out_dir else output_run_dir(src, env) / spec.subdir
   ```
   The default is the dated run folder `output/<YYYY-MM-DD src-env>/<spec.subdir>/`. The `out_dir` override is the B3 "always-current" batch destination — it writes straight into the caller's folder instead of a dated one (see [../architecture.md](../architecture.md) for the run-folder model).
6. `RunResult(output_dir=str(out_dir))` is created (`exporter.py:541`). Note this carries `output_dir` as a **string**, while `out_dir` stays a `Path` for filesystem ops.
7. Two `log.info` blocks (`exporter.py:546-548`) pin the full run context (label, route count, dest, resolved URL, auth state, both ceilings) so one uploaded log answers "what ran against what with which settings" — the heavy-logging contract.

### 2.2 The browser + sign-in block (`exporter.py:553-607`)

Everything runs inside `with sync_playwright() as p:` and a `try/finally` that **always** `browser.close()`s (`exporter.py:606-607`). Inside:

1. `new_authed_browser(p)` returns `(browser, ctx, page)` (`exporter.py:554`). With a valid saved session it `launch_browser(p, headless=True, …)` + restores the storage_state (`common.py:1501-1503`). With no session it opens the persistent Edge device profile and returns `(ctx, ctx, page)` — the context **doubles** as the browser handle, and its `.close()` shuts the persistent browser (`common.py:1494-1495`).
2. `navigate_with_auth(page)` (`common.py:449`) drives the OAuth round-trip (60 s budget, breadcrumbed). It raises `SiteUnreachableError` if `page.goto` fails (`common.py:471`).
3. `require_signed_in(page, msg)` (`common.py:652`) raises `AuthError` if the post-auth UI never appeared.
4. `preflight(page, spec.label)` (`common.py:741`) — see §6.
5. The route loop, then the retry pass.

The retry pass is wrapped so an `AuthError` propagates (re-raised, `exporter.py:601-602`) but any **other** retry-pass exception is swallowed with a log line (`exporter.py:603-605`) — a retry-pass crash must not discard the main run's results.

### 2.3 The per-route loop body (`exporter.py:569-594`)

For each `(i, route)` (1-based enumerate over `routes`):

1. `_wait_while_paused(events)` (`exporter.py:570`) — B1 pause hold, between routes only (§7).
2. `events.is_cancelled()` → log "Cancelled by user", `break` (`exporter.py:571-574`).
3. `prefix = f"[{i:>3}/{total}] Route {route}:"` and `out_path = out_dir / spec.filename(route)` (`exporter.py:576-577`).
4. `maybe_screenshot(page, events, note=f"Route {route}")` (`exporter.py:580`) — a between-route poll point so a Preview click during a long run of already-exists skips still gets answered within one iteration.
5. `_can_resume(out_path)` → record `exists` and `continue` (`exporter.py:582-586`) — §4.
6. `_process_route(...)` inside a `try/except RunCancelled` (`exporter.py:588-594`). `_process_route` returning `False` `break`s the whole loop (unrecoverable stop); `RunCancelled` raised from inside also `break`s cleanly.

### 2.4 After the loop (`exporter.py:596-626`)

`_retry_failed_routes` runs **only if not cancelled** (`exporter.py:598`). Then, outside the playwright block, a single `log.info` summary line (`exporter.py:609`) and the auto-saved run report (`write_run_report` → `auto_report_path(spec.subdir, f"{src}-{env}")`, `exporter.py:616-624`). A run-report write failure is non-fatal (`exporter.py:623-624`). The function returns `result`.

---

## 3. `_attempt_route` — one Generate→wait→save (`exporter.py:319`)

Returns `'saved' | 'empty' | 'skipped'`; **raises** on any failure (the caller `_process_route` decides retry vs record). Step by step:

| Step | Code | Notes |
|---|---|---|
| status | `events.on_status(events.worker_no, f"{prefix} generating…")` | one-line "what this browser is doing" |
| select Route | `page.get_by_label("Route", exact=True).select_option(route)` (`:324`) | `route` is the exact `<option>` value (canonical 3-digit + suffix) |
| Generate | `page.get_by_role("button", name="Generate").click()` (`:325`) | |
| build wait JS | `ready_js = spec.wait_js(route)`; `wait_js = f"() => (({ready_js}))() || ({ERROR_JS})"` (`:330-331`) | **`spec.wait_js` returns a full arrow function string**; it is wrapped in parens, **invoked** `(())()`, and OR'd with the shared error check so a site error short-circuits the wait |
| wait | `wait_with_skip_option(page, wait_js, prefix, events, hard_timeout_ms=timeout_ms)` (`:332`) | returns `False` ⇒ user skipped ⇒ `return "skipped"` |
| cancel re-check | `if events.is_cancelled(): raise RunCancelled()` (`:335-336`) | covers "cancel landed between the wait returning and the save" |
| error check | `err = report_error_text(page)`; `if err: raise ReportError(err)` (`:337-339`) | the site rendered a fatal error for this route |
| empty check | `if spec.is_empty(page): return "empty"` (`:340-341`) | report-specific empty marker |
| settle | `page.wait_for_timeout(1000)` (`:342`) | a 1 s settle before grabbing the page |
| preview | `maybe_screenshot(page, events, note=prefix.strip())` (`:345`) | last poll point before a blocking download wait |
| save | `spec.save(page, out_path, timeout_ms)` — `EmptyExport` **propagates** (no longer caught here) | a no-download empty is inconclusive; `_process_route` retries it once |
| | `return "saved"` | |

**Why the `wait_js` is OR'd with `ERROR_JS`:** without it, a route the site can't build would sit in `wait_with_skip_option` until the **full** per-route ceiling, then the 15-min retry. OR-ing the error check makes the wait resolve the instant the site flags an error, and the immediate `report_error_text` lookup turns it into a `ReportError` in seconds.

**The `EmptyExport` from `save` is the marker-independent safety net — now retry-once (Phase-3 fix `transient-export-click-failure-recorded-empty`):** `spec.is_empty` may miss a drifted empty marker, but `save_via_export_button`'s no-download guard raises `EmptyExport`. That no-download case is INCONCLUSIVE (a transient export-click flake looks identical to a real no-op), so `_attempt_route` lets it **propagate** and `_process_route` retries the route once in-loop, recording `empty` only if it reproduces (a POSITIVE `is_empty` match at the empty-check step is authoritative and still returns `"empty"` immediately). Locked by `check_export_engine.py` (`test_attempt_route_empty`, `test_process_route_empty_retry`).

---

## 4. The integrity gate (`exporter.py:81-154`)

Three functions, one shared predicate. Resume trusts "the file exists" to skip a route, so without a content check a 0-byte/truncated file from an interrupted run would mask a route as finished forever.

### 4.1 `_head_is_complete(suffix, head, size)` (`exporter.py:81`)

The magic-byte predicate (no third-party deps):

| suffix | check |
|---|---|
| `.xlsx` | `head == b"PK\x03\x04"` (ZIP container) |
| `.pdf` | `head == b"%PDF"` |
| anything else | `size > 0` |

The magic checks inherently reject anything shorter than 4 bytes (a short read won't equal the 4-byte signature).

### 4.2 `_file_looks_complete(path)` (`exporter.py:93`) — fresh-save, NOT lock-tolerant

`stat().st_size` + `open(path,"rb").read(4)`. **An `OSError` here returns `False`** (`:102-103`) — a read failure on a file we just wrote is a real problem. Used by `_verify_saved_file`. Also used by the parallel reconciliation (§9.4).

### 4.3 `_verify_saved_file(out_path)` (`exporter.py:107`)

Called at the end of **every** save strategy. If `_file_looks_complete` passes, returns. Otherwise: log a warning with the byte size, `out_path.unlink()` the partial file (so a later resume re-pulls it), and **raise `RuntimeError`** with a user-safe message (`:122-125`). That `RuntimeError` propagates up through `spec.save` → `_attempt_route` → `_process_route`'s generic `except Exception` → recorded `failed`.

### 4.4 `_can_resume(out_path)` (`exporter.py:128`) — resume path, **lock-tolerant**

The asymmetry vs `_file_looks_complete` is the key invariant:

```
not exists                                  -> False  (will export)
read OK + magic OK                          -> True   (skip; record "exists")
read OK + magic FAILS (truncated/0-byte)    -> unlink, return False (re-pull)
read FAILS (OSError)                         -> True   (trust + skip, never delete)
```

The last row is the critical edge (`:143-146`): a file that exists but can't be read is **almost always a finished export the user has open in Excel** (a Windows sharing-deny lock). Trusting it means resume can never turn a done route into a spurious failure by trying to re-download over a locked file. Contrast `_file_looks_complete`, where an `OSError` is `False` — these two functions deliberately treat a read failure **oppositely**, because one is "did the file I just wrote land?" and the other is "should I skip a pre-existing file?".

---

## 5. Save strategies (`exporter.py:161-244`)

All share the signature `save(page, out_path, timeout_ms=None)` and end with `_verify_saved_file(out_path)`. `timeout_ms` exists so the slower fast-mode/retry windows reach the **download** wait, not just report generation — but two of the three ignore it (the page is already rendered).

### 5.1 `save_pdf_letter` (`exporter.py:161`) — TSAR Ramp Summary

```python
page.pdf(path=str(out_path), format="Letter", print_background=True,
         margin={"top":"0.4in", "bottom":"0.4in", "left":"0.4in", "right":"0.4in"})
```
The Ramp Summary renders inline on the page, so `page.pdf()` (which emulates print media) captures it directly. `timeout_ms` unused.

### 5.2 `save_via_export_button` (`exporter.py:174`) — the Excel reports

Used by Ramp Detail, Highway Sequence, Highway Log (XLSX), and the Intersection reports. The mechanics that matter:

```python
ceiling = timeout_ms or report_timeout_ms()
download_ms = min(download_start_timeout_ms(), ceiling)          # :187-188
try:
    with page.expect_download(timeout=download_ms) as dl_info:
        page.locator("button.export-btn", has_text="Export").first.click()
except PlaywrightTimeoutError:
    err = report_error_text(page)
    if err:
        raise ReportError(err)                                   # :198
    raise EmptyExport()                                          # :202
dl_info.value.save_as(str(out_path))                             # :203
_verify_saved_file(out_path)                                     # :204
```

- The download wait is **bounded at `min(DOWNLOAD_START_TIMEOUT_MS, ceiling)`** — at most 60 s (`download_start_timeout_ms()`), never more than the per-route ceiling. Rationale (`common.py:198-210`): the site serializes the **already-rendered** rows client-side (SheetJS), so a non-empty report's download fires within a second of the click. The per-route ceilings size report *generation*, not this download-start window.
- **No-download branch** (`:192-202`): if no download starts in the window, distinguish a site error (`report_error_text` non-empty ⇒ `ReportError`, recorded `failed`) from "nothing to export" (the rendered-but-empty no-op ⇒ `EmptyExport`, recorded `empty`). This is the no-download fast-fail that replaced the old ~21-min empty-route hang.
- The Export-button locator is `button.export-btn` filtered `has_text="Export"`, `.first` (`:191`) — the site's action bar gives **both** Export and Print the `export-btn` class, so the text filter disambiguates.

### 5.3 `save_highway_log_pdf` (`exporter.py:207`) — report 4b (Highway Log PDF)

The trickiest save. The on-screen Highway Log is **paginated** (`hl_renderPage` shows one page of rows), so a bare `page.pdf()` would capture a single page. The site's global `hl_printAll()` builds the full multi-page layout into `#rampResults`, then calls `window.print()` and **synchronously restores** the on-screen view. The trick is to make that restore never run:

```python
built = page.evaluate("""() => {
    if (typeof hl_printAll !== 'function') return 'no-print-fn';
    window.print = () => { throw new Error('skip-print'); };       # override print to THROW
    try { hl_printAll(); } catch (e) { /* the throw skips hl_printAll's restore */ }
    const box = document.getElementById('rampResults');
    return (box && box.querySelector('.hl-print-section')) ? 'ok' : 'no-layout';
}""")
if built != "ok":
    raise ReportError("Couldn't build the Highway Log print layout … " + built)
page.pdf(path=str(out_path), format="Letter", landscape=True, print_background=True, margin=…)
```

Mechanics (`exporter.py:225-243`):
1. **`window.print` is overridden to `throw` BEFORE `hl_printAll()` runs.** `hl_printAll` builds the full layout, calls `window.print()` (which now throws), and the throw propagates out of `hl_printAll` **before** its synchronous restore line — so the complete print layout stays in the DOM.
2. The throw is caught in the JS `try/catch` (the `catch` body is empty by design).
3. Verify the layout actually built: `#rampResults` must contain `.hl-print-section`. Returns `'ok'` / `'no-layout'` / `'no-print-fn'`.
4. Any non-`'ok'` ⇒ **`ReportError`** (loud failure) rather than silently saving the one paginated page.
5. `page.pdf(landscape=True)` — 30 columns ⇒ landscape; the site's `@media print` CSS hides every control and shows only `#rampResults`, which `page.pdf()`'s print-media emulation honors.

`timeout_ms` unused (the layout is built client-side; `is_empty` already ran so this is never an empty route). See [../reports.md](../reports.md) for the report-side detail.

---

## 6. `preflight` and `select_report` (`common.py`)

### 6.1 `preflight(page, report_label)` (`common.py:741`)

Runs after sign-in, before the loop. Four checks, each a fast-fail with a `preflight_fail_*` page dump:

1. `#customReport` dropdown present (`count() == 0` ⇒ `PreflightError` + dump, `:749-756`).
2. `select_report(page, report_label)` (`:759`) — arms the form; itself raises `ReportUnavailableError` on a `cs-disabled` report.
3. Route control attaches within 15 s: `page.get_by_label("Route", exact=True).wait_for(state="attached", timeout=15000)` (`:761`).
4. Generate button attaches within 15 s (`:763`).

A `step` string is tracked so the log names the failed step (`:757,760,762`). `ReportUnavailableError` is re-raised **as-is** (`:765-769`) — it's a clear, specific condition, not the generic "page looks different". Any other exception ⇒ generic `PreflightError` (`:770-779`). `SiteUnreachableError` and `ReportUnavailableError` both subclass `PreflightError` (`common.py:44,51`), so every driver shows the message verbatim.

### 6.2 `select_report(page, report_label)` (`common.py:661`)

1. Click `#customReport`, locate the `li.cs-option` whose text matches `report_label` (`:673-674`).
2. **Read the option's classes**; if `cs-disabled` is present ⇒ `ReportUnavailableError` (`:682-688`). The disabled `<li>` has no `pointer-events:none`, so a Playwright click would silently no-op and stall ~30 s into a generic preflight error — detecting the class here turns that into one clear "currently unavailable" message. The class read is wrapped so the probe itself can never stop a run (`:676-681`).
3. Click the option, then **fan out District/County/Route to `-- ALL --`** (`:689-696`): click "District / County / Route", select District `-- ALL --`, `wait_for_function` that `#districtCountySelect` is no longer disabled (bounded at `county_enable_timeout_ms()`, default 60 s), then select that to `-- ALL --`. The county-enable wait is the only place `COUNTY_ENABLE_TIMEOUT_MS` is used.

### 6.3 The report-ready / error JS

| Symbol | Value | Used where |
|---|---|---|
| `ERROR_JS` (`common.py:705`) | `document.querySelector('#rampResults.error') !== null` | OR'd into every route's wait (`_attempt_route:331`) |
| `EXPORT_READY_JS` (`common.py:717`) | `[...querySelectorAll('button.export-btn')].some(b => /export/i.test(b.textContent||''))` | a readiness signal a report's `wait_js` keys on (NOT the no-download detector) |
| `report_error_text(page)` (`common.py:759`) | reads `#rampResults.error`'s inner text, or a default message; best-effort `None` on any lookup problem — but a swallowed probe exception is now **logged** (Phase-3 fix `report-error-text-blanket-swallow-hides-fatal`: a silent `None` on a real error page would downgrade a `failed` route to benign `empty`) | error short-circuit in `_attempt_route` and `save_via_export_button` |

`clearResults()` resets the `error` class on each Generate, so `ERROR_JS` only ever reflects the **current** route (no stale-error false positives, `common.py:699-704`).

> **Framing-drift note:** `EXPORT_READY_JS` is a *readiness* signal (the Export button rendered), **not** the no-download detector. CLAUDE.md describes the `EmptyExport` guard as keying on "Export control ready, no download (`EXPORT_READY_JS`)", but the actual detection in `save_via_export_button` is purely the **download-start timeout** — `EXPORT_READY_JS` is not referenced there at all. The topic doc flags the same drift.

---

## 7. `wait_with_skip_option` — the skip/cancel/heartbeat wait (`common.py:825`)

The poll loop every route's wait runs through. Returns `True` when the JS condition matched, `False` if the user skipped; raises `RunCancelled` on cancel mid-wait and `PlaywrightTimeoutError` on the hard timeout.

Setup (`:841-851`): `hard_timeout_ms` defaults to `report_timeout_ms()`; `skip_prompt_after_ms` defaults to `SKIP_PROMPT_AFTER_MS` (60 s). `poll_chunk_ms = 5000`. Deadlines computed from `time.monotonic()`.

Each iteration of `while True` (`:853-892`):

1. **Cancel wins first** (`:856-857`): `if events.is_cancelled(): raise RunCancelled()` — so Cancel interrupts the *current* route, not just between routes (the "Cancel is just a suggestion" bug this fixes).
2. **Skip** (`:858-860`): `if events.should_skip(): … return False`.
3. **Live view** (`:863-865`): `maybe_screenshot(...)` answers a pending Preview request (≤ one poll chunk of latency) and `events.on_status(...)` refreshes the worker's row with elapsed seconds.
4. **Hard deadline** (`:867-871`): if `now >= hard_deadline` ⇒ `raise PlaywrightTimeoutError`.
5. **The wait chunk** (`:873-878`): `chunk = min(5000, max(100, remaining_ms))`; `page.wait_for_function(js_condition, timeout=chunk)` — on success `return True`, on its own `PlaywrightTimeoutError` `pass` and fall through to re-check skip/deadline. The `max(100, …)` floor avoids a 0 ms timeout near the deadline.
6. **Heartbeat** (`:880-892`): once `now >= prompt_at`, emit the "still working (Ns elapsed; up to Ns left) — you can skip this route" line, set `prompted = True`, and schedule the next status 30 s out; thereafter emit "still working (Ns)..." every 30 s.

So the effective cadence is ~5 s (the poll chunk drives cancel/skip/preview responsiveness), with the skip hatch opening at `SKIP_PROMPT_AFTER_MS` and a 30 s status refresh after that. The hard timeout is enforced **independently** of the skip prompt.

### 7.1 `_wait_while_paused` (`exporter.py:494`) — B1 pause

```python
while events.is_paused() and not events.is_cancelled():
    time.sleep(_PAUSE_POLL_S)        # 0.2 s
```
Pause is honored **only between routes** — never inside a Playwright wait (thread-affine), so the browser sits idle holding **no download in flight**. The shared `is_paused()` makes every fast-mode worker park at the same point. A cancel during a pause exits the loop so cancel-during-pause still stops cleanly.

---

## 8. `_process_route` — retry/record machinery (`exporter.py:358`)

Wraps `_attempt_route` in the retry/record loop. Returns `True` to keep going, `False` to stop the whole run; raises `AuthError` to end cleanly. `t0`/`took()` track elapsed seconds for log lines.

`for attempt in range(1 + RETRY_COUNT)` (`:368`, so 2 attempts max). The `try/except/else` dispatches by exception class:

| Caught | Action | Recorded |
|---|---|---|
| `AuthError`, `RunCancelled` (`:371-372`) | **re-raise** — never retried, never recorded as failed | — |
| `ReportError` (`:373-383`) | log site error, `_capture_failure`, append to `result.failed`, `_record(…, "failed")`, **then `return _recover_or_stop(...)`** | `failed` (immediately — no in-loop retry burned; the end-of-run pass gives it one more fast attempt) |
| `PlaywrightTimeoutError` (`:384-394`) | same as ReportError | `failed` (the hard timeout already gave a skip window — don't burn another full timeout retrying) |
| other `Exception` (`:395-407`) | if `attempt < RETRY_COUNT`: log, `_recover_or_stop` (False ⇒ `return False`), `continue` to retry. Else: `_capture_failure`, append failed, record, `return _recover_or_stop(...)` | retried once, then `failed` |
| no exception (`else`, `:408-428`) | dispatch on `outcome`: `"skipped"` ⇒ `user_skipped` + record + `_recover_or_stop`; `"empty"` ⇒ `empty` + record + `return True`; `"saved"` ⇒ `result.saved += 1` + size log + record + `return True` | per outcome |

So the **only** error retried in-loop is a transient non-timeout, non-report exception. After every recorded outcome that needs the form re-armed (skip / report-error / failure), `_recover_or_stop` re-navigates and re-selects the report.

### 8.1 `_recover` / `_recover_or_stop` (`exporter.py:269-291`)

`_recover(page, spec)` (`:269`): `navigate_with_auth(page)` → `require_signed_in(…)` → `select_report(page, spec.label)`. Raises `AuthError` if the session died mid-batch (ends the run cleanly). This is the mid-run re-auth path — `navigate_with_auth` re-mints an expired memory-only token via a fresh silent SAML round-trip (see [../auth-and-signin.md](../auth-and-signin.md)).

`_recover_or_stop(page, spec, events)` (`:279`): wraps `_recover` in `try`, emits a "Recovering…" status, returns `True` on success. **Re-raises `AuthError`** (`:286-287`) but swallows any other exception with a log line and returns `False` (`:288-291`) — a failed re-arm stops the whole run rather than crashing it.

### 8.2 `_capture_failure` (`exporter.py:294`)

Best-effort screenshot + HTML to `FAILURES_DIR`, named `<spec.subdir>_route_<route>_<YYYYMMDD_HHMMSS>.{png,html}`. **Never raises** (`:315-316`) so a capture problem can't mask the original error. Screenshot is the **viewport** (`full_page=False`, `:308`) — the failure state worth capturing is above the fold, and this avoids writing the whole report image to disk. `FAILURES_DIR` is deliberately never added to the support bundle (can contain report content).

---

## 9. `_retry_failed_routes` — the serial slow pass (`exporter.py:432`)

Runs after the main loop (and as fast mode's retry, via `_retry_failed_sequential`). One route at a time with the generous `RETRY_REPORT_TIMEOUT_MS` (15 min) ceiling. The bookkeeping is the subtle part.

1. `to_retry = list(result.failed)`; bail if empty (`:447-449`).
2. **Drop the first-pass `failed` records for these routes** (`:461-463`):
   ```python
   retry_set = set(to_retry)
   result.failed     = [r for r in result.failed if r not in retry_set]
   result.per_route  = [(r, s) for (r, s) in result.per_route if r not in retry_set]
   ```
   so `_process_route` can re-record each route's **final** status exactly once — no duplicate run-report rows, no double-counted progress.
3. `_recover_or_stop` once to re-arm (`:465`; may raise `AuthError`). Then for each route:
   - `_wait_while_paused` + `is_cancelled()` break (`:468-470`).
   - `_can_resume(out_path)` ⇒ record `exists`, `continue` (`:473-476`) — a route whose file appeared meanwhile (e.g. a concurrent run) records `exists`.
   - `_process_route(...)`; `False` ⇒ break; `RunCancelled` ⇒ break (`:477-481`).
4. **Reconcile** (`:483-488`): anything in `to_retry` not in the final `recorded` set (re-arm failure, cancel, unrecoverable stop) is appended back to `result.failed` and recorded `failed` — so every retried route is accounted for exactly once.

---

## 10. The parallel engine (`exporter_parallel.py`)

Layered on top of the sequential engine; the per-route mechanics are **imported** (`:63-71`), so a per-report fix in `exporter.py` benefits both. Only concurrency/coordination is new.

### 10.1 Worker-count resolution (`exporter_parallel.py:85-110`)

- `DEFAULT_WORKERS = 3`, `MAX_WORKERS = 30` (`:81-82`).
- `default_worker_count()` (`:85`): the saved Settings `fast_workers`, clamped to `[1, MAX_WORKERS]`; falls back to `DEFAULT_WORKERS` on any exception.
- `resolve_worker_count(requested=None)` (`:96`): `None` ⇒ the `TSMIS_FAST_WORKERS` env var (if `isdigit()`) ⇒ `default_worker_count()`. Garbage ⇒ default. Always returns `max(1, min(requested, MAX_WORKERS))`.
- In `run_export_parallel`: `n = resolve_worker_count(workers)` (`:194`); then `n = min(n, total) or 1` (`:214`) — never more workers than routes.

### 10.2 Device-mode cap (`exporter_parallel.py:199-206`)

If `not has_valid_auth()` and `n > 1`, **force `n = 1`** with a log line and a GUI message — the persistent Edge device profile can only be open in one browser at a time. Real parallelism requires a saved login.

### 10.3 `_preflight_once` (`exporter_parallel.py:137`)

Validates auth + the report form **a single time**, before launching N browsers, so a bad session / changed site fails fast with one clear error instead of N. Uses `new_authed_browser(p, parallel=True)` — the **same parallel channel** the workers will use — so the session is validated in the right browser.

### 10.4 The worker function (`exporter_parallel.py:241-300`)

Each `worker(idx)` (one per thread, named `export-w{idx+1}`, daemon) owns its **own** `sync_playwright()` instance, browser, context, and page (Playwright is thread-affine — nothing Playwright is shared across threads). Its `RunResult` lands in `worker_results[idx]`, and it gets a per-worker `Events` from `_worker_events(events, stop, idx+1)`.

Body:
1. `new_authed_browser(p, parallel=True)` → `navigate_with_auth` → `require_signed_in` → `select_report(page, spec.label)` to arm this worker's form (`:250-259`).
2. `while not stop.is_set():` (`:260`):
   - `_wait_while_paused(events)` (shared sink, so all workers park together) (`:261`).
   - `events.is_cancelled()` ⇒ `stop.set(); break` (`:262-264`).
   - `route = work.get_nowait()` from the shared `queue.Queue`; `queue.Empty` ⇒ `break` (no work left) (`:265-268`).
   - `_can_resume(out_path)` ⇒ record `exists`, `continue` (`:271-275`).
   - `_process_route(...)`; `False` ⇒ `stop.set(); break` (unrecoverable winds down the whole run) (`:277-280`).
3. `finally: browser.close()` (`:281-282`).

Exception handling at the worker boundary (`:285-300`):

| Caught | Action |
|---|---|
| `AuthError` | `auth_failed.set(); stop.set()` — re-raised after the join as `AuthError` (`:285-287`) |
| `RunCancelled` | `stop.set()` — user cancelled mid-route; wind down, **not** a crash (`:289-291`) |
| other `Exception` | `worker_crashed.set()`; log + GUI line; **deliberately does NOT `stop.set()`** — the other workers keep draining the queue so one dead browser doesn't abort the run (`:292-300`) |

### 10.5 `_worker_events` (`exporter_parallel.py:113`)

Forwards `on_log` / `on_route` / `on_status` / screenshot seams / `is_paused` to the shared sink, but:
- **`should_skip = lambda: False`** — per-route Skip is intentionally a no-op in fast mode: with several routes in flight, "skip the route being waited on" is ambiguous. Use **Cancel**.
- **`is_cancelled = lambda: stop.is_set() or real.is_cancelled()`** — so a fatal error in one worker (which sets `stop`) quiets the others' waits via `wait_with_skip_option`'s cancel check.
- `worker_no = idx+1` tags the status line / screenshot requests so the GUI's per-browser rows stay distinguishable.

### 10.6 Shared state, join, and crash reconciliation (`exporter_parallel.py:232-351`)

Shared mutable state is only: the `work` queue, three `threading.Event`s (`stop`, `auth_failed`, `worker_crashed`), and `worker_results[]` (merged at the end — no locking on the hot path). After `t.start()`/`t.join()` for all threads:

1. **Auth** (`:311-315`): `auth_failed` set ⇒ `raise AuthError(...)` so the driver clears the stale file and prompts re-login. Files already saved stay on disk (a re-run resumes).
2. **Merge** (`:318-327`): sum `saved`, extend the lists and `per_route` from each `worker_results` entry into one `result`.
3. **Reconcile** — the extracted `_reconcile_unaccounted(routes, result, out_dir, spec, events, *, cancelled, worker_crashed)` helper (Phase-3 fixes, locked by `check_parallel_reconcile.py`): a crashed/stopped worker can leave routes with **no recorded outcome** — the one it had in flight plus any it never reached.
   ```python
   if cancelled and not worker_crashed:
       return []                            # clean cancel: not-done, resume later
   accounted = {r for r, _ in result.per_route}
   missing = [r for r in routes
              if r not in accounted
              and not _can_resume(out_dir / spec.filename(r))]
   ```
   Two corrected behaviors: (a) it still reconciles when a worker **CRASHED even on cancel** (`parallel-crash-plus-cancel-skips-reconciliation`), so a crash's orphaned routes always reach the run report instead of vanishing — only a *clean* cancel skips; (b) it uses the lock-tolerant **`_can_resume`** instead of the read-strict `_file_looks_complete` (`parallel-reconcile-uses-read-strict-not-lock-tolerant`), so a route whose file landed but is open in Excel (sharing-deny lock) is trusted as present, not re-failed and needlessly re-downloaded. Every `missing` route is appended to `result.failed` and recorded `failed`.
4. **Serial retry** (`:359-366`): if `result.failed` and not cancelled, `_retry_failed_sequential(...)` runs the shared `_retry_failed_routes` in a **single fresh browser** (`new_authed_browser(p, parallel=True)`) — fast-mode retries are sequential too, on the parallel channel (Chrome / Built-in Chromium, never managed Edge). Done **before** the run report so the CSV reflects final outcomes.
5. Run report written (`:368-376`), same as the sequential engine.

---

## 11. Browser channel resolution (`common.py`)

`new_authed_browser(p, parallel=False)` (`common.py:1464`) is the single entry. With a valid session it `launch_browser(p, headless=True, parallel=parallel, args=_LNA_ARGS)` (`:1501`) + restores the storage_state into a fresh app context. With none it opens the device profile.

`launch_browser` (`common.py:1126`) resolves a channel via `_resolve_channel`, probes it once per process (a real launch + drive-a-page test, `_probe_channel:1034`), caches it, and launches for real. If the real launch fails despite a passing probe, it clears the cache and re-resolves **excluding** the failed channel (`:1144-1168`).

Two channel orders:

| | Function | Order | Cache |
|---|---|---|---|
| sequential | `_candidate_channels` (`:992`) | `BROWSER_CHANNELS` = (`chromium` if available) + `msedge`, `chrome`; user pick first | `_resolved_channel` |
| parallel | `_parallel_candidates` (`:1001`) | Chromium, then Chrome, **`msedge` last** (and only as a warned fallback) | `_resolved_parallel` |

`BROWSER_CHANNELS` is `(("chromium",) if _chromium_available() else ()) + ("msedge","chrome")` (`common.py:958`). The parallel order **drops `msedge` from the middle and appends it last** (`:1015-1020`), and a UI pick of Edge is *not* honored for parallel work — only `TSMIS_BROWSER_CHANNEL` hard-overrides. Field reason: N concurrent managed-Edge instances restoring the same session timed out. `resolve_parallel_channel(p)` (`:1116`) returns the would-be parallel channel so the env scan can drop to one browser when only managed Edge is usable. Full narrative: [../lessons.md](../lessons.md).

---

## 12. Error-class raise sites (precise)

| Class | Raised at | Recorded as |
|---|---|---|
| `SiteUnreachableError` (PreflightError) | `navigate_with_auth` when `page.goto` fails (`common.py:471`) | run aborts |
| `AuthError` | `require_signed_in` (`common.py:658`); `_recover` via it; parallel after join (`exporter_parallel.py:315`) | never recorded failed; run ends cleanly, driver clears the file |
| `PreflightError` | `preflight` (`common.py:753,776`) | run aborts before the loop |
| `ReportUnavailableError` (PreflightError) | `select_report` on `cs-disabled` (`common.py:684`) | surfaced at preflight, before the loop |
| `ReportError` | `report_error_text` non-empty in `_attempt_route` (`exporter.py:339`); `save_via_export_button` no-download + site error (`exporter.py:198`); `save_highway_log_pdf` layout-build failure (`exporter.py:234`) | `failed` (in seconds; one fast retry in the end-of-run pass) |
| `EmptyExport` | `save_via_export_button` no-download + no site error (`exporter.py:202`) | `empty` (~60 s) |
| `RunCancelled` | `wait_with_skip_option` (`common.py:857`); `_attempt_route` post-wait re-check (`exporter.py:336`) | not a failure; clean partial stop |
| `RuntimeError` | `_verify_saved_file` integrity failure (`exporter.py:122`) | generic-Exception path ⇒ retried once ⇒ `failed` |
| `PlaywrightTimeoutError` | `wait_with_skip_option` hard deadline (`common.py:869`) | `failed` immediately (no in-loop retry) |
| `BrowserNotFoundError` | `_resolve_channel` (`common.py:1103,1109`) | run aborts |

---

## 13. Extension points

### 13.1 Add a save strategy

Write a function `save(page, out_path, timeout_ms=None) -> None` in `exporter.py` that writes the file and **ends with `_verify_saved_file(out_path)`** (the integrity gate is not optional — every save relies on it). If it can detect a rendered-but-empty route, raise `EmptyExport()` (translated to `"empty"` in `_attempt_route`); if it hits a fatal site condition, raise `ReportError(msg)` (recorded `failed`). Then point a `ReportSpec.save` at it. The existing three are the templates: inline-render PDF (`save_pdf_letter`), download button (`save_via_export_button`), and synthesized print layout (`save_highway_log_pdf`).

### 13.2 Add a `ReportSpec` (a new report)

`ReportSpec` (`exporter.py:62`) carries `label`, `subdir`, `filename(route)`, `wait_js(route)`, `is_empty(page)`, `save(page, out_path, timeout_ms)`. The full new-report checklist (registry, `.bat` branches, `app.spec` `APP_MODULES`, `.gitkeep`) is in [../architecture.md](../architecture.md) / CLAUDE.md *Extending*. Two engine-level contracts to honor:
- **`wait_js(route)` must return a complete arrow-function string** — `_attempt_route` wraps and **invokes** it: `f"() => (({ready_js}))() || ({ERROR_JS})"` (`exporter.py:331`). A bare boolean expression (not an arrow function) will not work; it must be callable.
- `is_empty(page)` runs **before** the save. It's a fast pre-check; the no-download guard in `save_via_export_button` is the marker-independent backstop, so `is_empty` drifting can't reintroduce the empty-route hang.

### 13.3 Add a timeout knob

Add the constant + a `*_timeout_ms()` accessor in `common.py` (model on `report_timeout_ms`, `common.py:242`), reading via `_settings_ms(key, default, unit)`. **Engines must call the accessor, never the constant** — that's how a Settings change applies without a restart and how a settings read can never stop a run.

---

## 14. Gotchas a maintainer will trip on

- **Thread-affinity is absolute.** Only the thread that created a Playwright `page` may touch it. This is why `maybe_screenshot` runs *on the worker thread at poll points* (the GUI can never screenshot directly), why pause holds *between* routes (never inside a Playwright wait), and why each parallel worker owns its own `sync_playwright()`. Don't move a `page` call onto another thread.
- **`_file_looks_complete` vs `_can_resume` treat a read failure oppositely.** Fresh-save: `OSError` ⇒ `False` (re-pull). Resume: `OSError` ⇒ `True` (trust the locked file). Mixing them up either re-downloads over Excel-locked files or masks truncated downloads.
- **Resume keys on `out_dir`, which encodes `src-env` + date.** A different environment or a new day ⇒ a fresh folder ⇒ nothing skipped. The same route from `ssor-prod` and `ars-prod` never collide because they're in different run folders. The B3 `out_dir` override breaks the dated convention deliberately (always-current store).
- **The non-`#rampResults.error`-in-the-export-window → `empty` edge is now retry-once.** A transient hiccup *inside* `save_via_export_button`'s download wait that doesn't render a `#rampResults.error` raises `EmptyExport`, which `_attempt_route` now PROPAGATES; `_process_route` retries the route once in-loop and records `empty` only if it reproduces (Phase-3 fix). A positive `is_empty` match stays immediate `empty`. This closes the old "populated route whose Export click flaked, reported as No data and never retried" gap.
- **`ReportError` and `PlaywrightTimeoutError` are NOT retried in-loop** — only a transient non-timeout `Exception` is (`RETRY_COUNT = 1`). The end-of-run serial pass is the second chance for `ReportError`/timeout routes.
- **The retry pass mutates `result` in place** and *drops* the first-pass `failed` records before re-running (`exporter.py:461-463`). If you add per-route bookkeeping to `RunResult`, mirror this filter or you'll get duplicate/stale rows.
- **Skip is silently a no-op in fast mode** (`_worker_events`). Don't wire a Skip button to fast mode expecting per-route behavior — only Cancel works there.
- **`spec.wait_js` is OR'd with `ERROR_JS` and invoked.** If a new report's `wait_js` is malformed JS, the whole wait throws inside `page.wait_for_function` and the route times out cryptically — test the arrow function in isolation.
- **A crashed parallel worker does NOT stop the others** (by design). Lost-in-flight routes are reconciled to `failed` after the join *unless their file already landed* — don't "fix" this by setting `stop` on a generic worker exception, or one dead browser aborts the whole run.

---

## See also

- [../engine-and-reliability.md](../engine-and-reliability.md) — the scannable companion (timeouts table, fast-mode RAM budget, run-report columns).
- [../architecture.md](../architecture.md) — `ReportSpec` single-loop design, run folders, registry.
- [../auth-and-signin.md](../auth-and-signin.md) — `navigate_with_auth`, `_recover` mid-run re-auth, device-mode worker cap.
- [../reports.md](../reports.md) — per-report save specifics (Highway Log PDF print override).
- [../lessons.md](../lessons.md) — the managed-Edge-under-concurrency field failure.
