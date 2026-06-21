# GUI bridge & worker internals

Code-level walkthrough of the Python⇄JS bridge, the two-queue message pipeline, the single-task gate, and every worker thread. Deepens [../gui.md](../gui.md) (the scannable what/why: UI stack, WebView2 profile, the five pywebview traps). This doc is the "how the message actually flows and how the workers run" companion — read it before changing `gui_api.py`, `gui_worker.py`, or `scripts/ui/app.js`.

Files: `scripts/gui_main.py` (entry/bootstrap), `scripts/gui_api.py` (the `GuiApi` js_api bridge + state + pumps), `scripts/gui_worker.py` (worker threads), `scripts/ui/app.js` (frontend), `scripts/ui/index.html` (static shell). The control seam between core and GUI is the `Events` sink (`scripts/events.py:Events`).

---

## 1. The big picture — three threads of control, two queues

The GUI is a pywebview/Edge-WebView2 window rendering `scripts/ui/`. Playwright's sync API is **thread-affine** (only the thread that created a page may touch it), so all browser work runs on dedicated worker threads, never on the bridge/UI thread. Communication is strictly one-way per direction:

- **Workers → GUI:** worker threads `put((kind, payload))` onto `GuiApi._q` (`gui_api.py:122`, a `queue.Queue`). The protocol is documented at the top of `gui_worker.py:8-55`.
- **GUI → JS:** `_handle`/api methods `put` JSON-ready event dicts onto a *second* queue `GuiApi._out` (`gui_api.py:123`). One sender thread drains `_out`, batches, and `evaluate_js`-dispatches.
- **JS → Python:** `app.js` calls `window.pywebview.api.<method>()` (the public `GuiApi` methods), each returning a Promise.

Three long-lived daemon threads are started in `GuiApi.__init__` (`gui_api.py:174-175`):

| Thread name | Function | Role |
|---|---|---|
| `gui-pump` | `GuiApi._worker_pump` (`gui_api.py:383`) | Drains `_q`, dispatches each `(kind, payload)` through `_handle` |
| `gui-send` | `GuiApi._sender` (`gui_api.py:249`) | Drains `_out`, batches ≤200, dispatches to JS via `evaluate_js` |
| `gui-icon` | `GuiApi._set_window_icon_late` (`gui_api.py:315`) | One-shot: sets the window icon with pure Win32 off the STA thread |

Plus pywebview's own **bridge threads** (one per `api.<method>()` call) and each worker thread it spawns. State mutations on `GuiApi` are guarded by `self._lock`, a `threading.RLock` (`gui_api.py:121`).

### Why two queues, not one

`_q` carries the *worker protocol* `(kind, payload)` tuples (engine vocabulary). `_handle` translates those into *JS event dicts* (`{"t": …}`) and enqueues onto `_out`. The split keeps the worker protocol independent of the wire format, and — critically — funnels **everything destined for JS through a single ordered queue** so log lines, progress, and full state snapshots can never interleave out of order on the wire. A `("log", …)` from a worker and a `_push_state()` from a bridge-call handler both land in `_out` in the order they were enqueued.

---

## 2. The full message lifecycle (one round trip)

```
[worker thread]  self.q.put(("progress", {...}))         # gui_worker, e.g. ExportWorker._on_route
        │
        ▼
[gui-pump]       _worker_pump → _handle("progress", p)    # gui_api.py:383, :392
        │            └─ mutates GuiApi state under _lock (for some kinds)
        │            └─ self._emit({"t": "progress", "p": p})   → _out
        ▼
[gui-send]       _sender drains _out, batch ≤200          # gui_api.py:249
        │            evaluate_js("window.__tsmis && window.__tsmis.dispatch([...])")
        ▼
[WebView2 JS]    window.__tsmis.dispatch(events)          # app.js:1428
        │            for ev: switch(ev.t) → renderer
        │            "progress" → renderProgress(ev.p)     # app.js:1248
        ▼
[user clicks]    api.skip_route() / api.start_export(...)  # app.js → bridge thread
        │
        ▼
[bridge thread]  GuiApi.skip_route() (wrapped by _api_method)  # gui_api.py:1337
                     self.skip_event.set(); returns {"ok": True} → JS Promise
```

`_emit` (`gui_api.py:192`) is just `self._out.put(event)`. `_push_state` (`gui_api.py:228`) emits `{"t": "state", "s": self._state_snapshot()}`.

### The sender's batching and resilience (`_sender`, `gui_api.py:249-274`)

1. `self._ready.wait()` — block until JS calls `api.ui_ready()` (first render done); otherwise `dispatch` wouldn't exist yet.
2. `ev = self._out.get()` (blocking), then drain greedily with `get_nowait()` up to **200** events into one `batch`.
3. `evaluate_js("window.__tsmis && window.__tsmis.dispatch(%s)" % json.dumps(batch, default=str))`.
4. `default=str` on `json.dumps`: a future non-JSON payload (e.g. a stray `Path`) **degrades to a string instead of throwing and dropping the whole batch**.
5. `evaluate_js` failure (window torn down mid-run is the normal cause) is logged at `info` and the loop keeps draining — never crashes the sender.
6. Shutdown: `_SHUTDOWN` sentinel (`gui_api.py:73`) put on `_out` by `_on_closed` returns the thread.

The `window.__tsmis &&` guard in the JS string means a dispatch that arrives before `app.js` defined `window.__tsmis` (only at the end of `boot()`, `app.js:2293`) is silently a no-op rather than a JS error — but in practice `_sender` waits on `_ready` which is only set by `ui_ready()` *after* `boot()` finishes, so `__tsmis` is always present.

---

## 3. The kind → handler → event → renderer table

This is the master map. Every worker-posted `kind` is dispatched by `_handle` (`gui_api.py:462-564`), most translate to a `{"t": …}` JS event, and `app.js dispatch` (`app.js:1482`) routes `ev.t` to a renderer. **Note: an unknown `kind` hits `_handle`'s `else`, which logs `log.warning("unhandled worker event kind …")` (P0) — it is no longer silently dropped, but a real worker message still needs its own branch to act** (see Gotchas).

| Worker `kind` (`gui_worker.py`) | `_handle` branch (`gui_api.py`) | JS event `t` | `app.js dispatch` renderer |
|---|---|---|---|
| `log` (str) | `_emit_log(payload)` :393 | `log` | `appendLog` :122 |
| `progress` (dict) | emit as-is :395 | `progress` | `renderProgress` (only if runMode export/batch) :1248 |
| `worker_status` (w,text) | emit :397 | `wstatus` | `updateWorkerStatus` :475 |
| `preview_shot` (w,b64,note,url) | emit :400 | `preview` | `showPreviewEvent` :389 |
| `env_shot` (dict) | `_on_env_shot` :404 / :1434 | `preview` (w=0, +`env_info`) | `showPreviewEvent` :389 |
| `env_access` (dict) | `_on_env_access` :406 / :1495 | `state` (snapshot) + `log` | `renderState`→`renderEnvAccess` :1024 |
| `env_access_done` (dict) | `_on_env_scan_done` :408 / :1505 | `log` + `run_ended` (via `_end_task`) | `appendLog`, `endRunUi` |
| `reset_done` (dict) | `_on_reset_done` :410 / :1980 | `log`/`modal` + `run_ended` | `appendLog`/`showMessage`, `endRunUi` |
| `chromium_done` (dict) | `_on_chromium_done` :412 / :1898 | `log`/`modal` + `settings` + `run_ended` | `appendLog`, `fillSettings`, `endRunUi` |
| `export_done` (list) | `_finish_export` :414 / :552 | `log`s + `run_ended` + `state` | `appendLog`, `endRunUi`, `renderState` |
| `export_partial` (list) | inline :416-425 | (none — just stores state) | — |
| `consolidate_done` (Result) | `_finish_consolidate` :426 / :643 | `log`/`modal` + `run_ended` | `appendLog`/`showMessage`, `endRunUi` |
| `login_open` | inline :428-434 | `state` + `log` | `renderState`, `appendLog` |
| `login_saved` | inline :435-439 | `log` + `run_ended` (`_end_task`) + autoscan | `appendLog`, `endRunUi` |
| `login_device_ok` | inline :440-450 | `log` + `run_ended` + autoscan | `appendLog`, `endRunUi` |
| `login_failed` | inline :451-460 | `log` + `modal` + `run_ended` | `appendLog`, `showMessage`, `endRunUi` |
| `check` (key,status,text) | inline :461-466 | `state` | `renderState` |
| `checks_done` (dict) | `_on_checks_done` :467 / :683 | `state` + maybe `log` + autoscan | `renderState` |
| `cancelled` | inline :469-472 | `log` + `run_ended` | `appendLog`, `endRunUi` |
| `batch_progress` (dict) | `_on_batch_progress` :473 / :1294 | `state` | `renderState`→`syncBatchHeadline` |
| `batch_done` (dict) | `_on_batch_done` :475 / :1304 | `log` + `run_ended` + `state` | `appendLog`, `endRunUi` |
| `active_env_done` (dict) | `_on_active_env_done` :481 / :844 | `state` (snapshot) | `renderState`→`applyMatrixEnvFlags` (quiet background check — clears `_active_check`, NOT the task gate) |
| `matrix_cell` (dict) | `_on_matrix_cell` :550 / :2501 | `state` (snapshot) | `renderState`→matrix progress (per-cell, non-terminal) |
| `matrix_done` (dict) | `_on_matrix_done` :552 / :2511 | `log` + `matrix_refresh` + `run_ended` | `appendLog`, `renderMatrix`/`renderDayMatrix`, `endRunUi` |
| `matrix_export_done` (dict) | `_on_matrix_export_done` :554 / :2528 | `log` + `run_ended` (+ auto-chain by-day) | `appendLog`, `endRunUi`, matrix refresh |
| `update_status` (dict) | `_on_update_status` :477 / :724 | `state` + maybe `log` | `renderState`→`renderUpdate` |
| `error` (kind,msg) | `_on_error` :479 / :794 | `log` + `modal` + `run_ended` | `appendLog`, `showMessage`, `endRunUi` |

**Discrepancy note vs the topic doc / `gui_worker.py` docstring:** the worker protocol docstring (`gui_worker.py:9-56`) lists most kinds but omits `check`, `checks_done`, `batch_progress`, `batch_done`, `active_env_done`, `matrix_cell`, `matrix_done`, and `matrix_export_done` (a pre-existing known gap, also called out in `gui.md`). All eight are real and handled — see the table.

### JS event types that have NO worker `kind`

These are emitted by `GuiApi` methods directly (not via the pump), via `_emit`:
- `run_started` — `{t:"run_started", mode, label, workers}` emitted at the top of every task starter (`start_export`, `start_consolidate`, `verify_environment`, etc.) → `startRunUi` (`app.js:1366`).
- `settings` — `{t:"settings", s: get_settings()}` emitted by `_on_chromium_done` (`gui_api.py:1920`) → `fillSettings` (`app.js:1434`).
- `state` — `{t:"state", s: snapshot}` from `_push_state` (the workhorse) → `renderState`.
- `modal` — from `_emit_modal` (`gui_api.py:200`) → `showMessage`.

---

## 4. `_state_snapshot` — the exact shape the UI consumes

**The whole UI is driven by full snapshots.** Python owns all app state; `app.js` owns only presentation + form fields and never invents log lines. `_state_snapshot` (`gui_api.py:204-226`) is taken under `_lock` and returns:

```python
{
  "task": None|"export"|"consolidate"|"login"|"compare"|"batch"|"envcheck"|"envscan"|"chromium"|"reset",
  "fast_run":   bool,                 # running export is fast mode (Skip is off)
  "paused":     self.pause_event.is_set(),
  "authed":     bool,                 # valid saved auth file
  "device_ok":  bool,                 # silent Edge device sign-in proven this session
  "auth_dot":   "ok"|"bad"|"busy"|"unknown",
  "auth_text":  str,
  "login_phase": None|"starting"|"open"|"saving"|"cancelling",
  "login_label": "Re-login"|"Log in",
  "checks":     {key: {"status","text"}, ...},  # browser_<ch>, output, tools
  "checks_running": bool,
  "days":       list_output_days(),   # run-folder names, newest first
  "can_save_report": bool(self._last_results),
  "last_summary": JSON-safe completion summary or None,   # _build_export_summary
  "batch":      {label,done,total,src,env,steps} or None, # live Export-Everything
  "batch_resume": {reports,pending,total} or None,        # resumable manifest
  "update":     {phase, version?, progress?, can_apply?, staged?, revert?, ...},
  "env_access": {"<src>-<env>": {key,source,environment,label,status,detail,url,...}},
  "logins":     {"file": {valid, age_h}, "device": {ok, primed}},  # _login_states
}
```

**Consumed by `renderState` (`app.js:686-845`)**, which is one big idempotent re-render: it sets the auth dot/text, the two login-path chips, the readiness chips, locks every config input when `st.task != null` (`const locked = st.task != null`, `app.js:753`), toggles every action button's `disabled` off the task name, and calls the sub-renderers (`renderUpdate`, `renderDays`, `renderEnvAccess`, `updateActivityCards`). Because it's a full snapshot every time, there is **no incremental state on the JS side** — any state push fully re-derives the UI. This is the load-bearing model: a worker never tells JS "increment the saved count"; it mutates Python state and pushes the whole picture.

`get_initial_state` (`gui_api.py:813-858`) returns the **immutable init payload** (`S.init` in JS) — app name/version, the report/consolidate/compare registries, routes, channels, sources/envs, fast defaults, settings, *plus* the first `state` snapshot under key `"state"`. It also runs the once-only startup work (`_refresh_auth`, `_start_checks_locked`, `_start_update_check`, `_pending_batch`) gated on `self._started` (`gui_api.py:815`).

---

## 5. The single-task gate

Only ONE task runs at a time. The gate is `self._task` (a string name or `None`), guarded by `_lock`.

### Claiming atomically

`_try_claim_task(name)` (`gui_api.py:496-506`) is the **atomic check-and-set**:

```python
with self._lock:
    if self._task:
        return False
    self._task = name
    return True
```

This replaced an earlier check-then-set that **raced**: two quick clicks (or a save dialog opening between the two operations) could both pass the gate and start two workers. The rule: **validate pure inputs first, then claim atomically, then start the worker.** See `start_export` (`gui_api.py:1038-1099`): it resolves specs/routes/workers *before* `_try_claim_task("export")`, so a bad index returns an error without ever touching `_task`.

`start_login` / `verify_environment` / `check_environments` / `_start_chromium` set `self._task` directly inside a `with self._lock:` block (they have no blocking dialog between the check and the set, so the separate helper isn't needed).

### Releasing without running

`_release_task` (`gui_api.py:508-513`) drops a slot claimed before a worker actually started — used when a **native save dialog is cancelled**. The compare flows (`start_compare`, `start_compare_env`) claim *before* opening the blocking save dialog (so a second click is rejected immediately), then `self._release_task()` + `return {"cancelled": True}` if the user cancels, and a `try/except: self._release_task(); raise` so a `suggest_name`/dialog error can't wedge the gate forever (`gui_api.py:1670-1685`, :1745-1761).

### Ending a task

`_end_task` (`gui_api.py:482-492`) is the single teardown:

```python
with self._lock:
    self._task = None; self._fast_run = False; self._login_phase = None
    self._export_worker = None; self._batch = None
    self.pause_event.clear()      # never leak a paused state across runs
self._refresh_auth()
self._emit({"t": "run_ended"})    # → app.js endRunUi()
self._push_state()
```

Every terminal `_handle` branch (`_finish_export`, `_finish_consolidate`, `cancelled`, `_on_error`, login outcomes, `_on_reset_done`, `_on_chromium_done`, `_on_env_scan_done`, `_on_batch_done`, `_on_env_shot`) ends by calling `_end_task` so the gate always re-opens. `run_ended` triggers `endRunUi` (`app.js:1403`) which stops the elapsed timer, clears the worker strip, and resets the progress card.

**Cancel granularity:** `cancel_run` (`gui_api.py:1344-1356`) sets `cancel_event` + clears `pause_event` (so a paused run unblocks and the cancel lands) for tasks that honor cancel between steps; `envcheck` is a single short headless verify that "can't be stopped partway" so it just logs that.

---

## 6. `_api_method` — bridge-call hardening

Every public `GuiApi` method is wrapped by `@_api_method` (`gui_api.py:97-113`):

```python
def wrapper(self, *args, **kwargs):
    try:
        return fn(self, *args, **kwargs)
    except Exception as e:
        logging.getLogger("tsmis.crash").critical(
            "uncaught exception in GUI api %s", fn.__name__, exc_info=True)
        try: self._emit_log(f"ERROR: {type(e).__name__}: {e} (details in the log file)")
        except Exception: pass
        return {"error": f"{type(e).__name__}: {e} (details are in the log file)"}
```

A windowed `.exe` has no stderr, so an uncaught exception in a bridge call would vanish and leave the JS Promise hanging forever. The wrapper guarantees: (1) the full traceback lands in `tsmis.crash` (→ `tsmis.log`), (2) the user sees one line in the log pane, (3) JS gets a structured `{"error": …}` it can surface. Every JS caller checks `if (res && res.error) showMessage(...)`. The mirror on the JS side: uncaught JS errors come back through `api.log_js_error` (`app.js:2244`, `dispatch` catch at :1449, the global `window.error` handler).

**Gotcha:** `wrapper.__name__ = fn.__name__` (`gui_api.py:112`) is required — pywebview enumerates `js_api` methods by name to inject the stubs, so the wrapper must masquerade as the original.

---

## 7. Pause / cancel / skip — the Event plumbing

Five `threading.Event`s live on `GuiApi` (`gui_api.py:168-172`): `cancel_event`, `skip_event`, `pause_event`, `login_done`, `login_cancel`. They flow into the engine through the `Events` sink (`events.py:Events`), built per worker in `ExportWorker._build_events` (`gui_worker.py:278-290`):

```python
Events(on_log=…, on_route=self._on_route, should_skip=self._should_skip,
       is_cancelled=self.cancel.is_set, on_status=…,
       screenshot_wanted=self._shot_wanted, on_screenshot=self._on_screenshot,
       is_paused=self.pause.is_set)
```

| Control | JS → bridge | Event set | Engine consults | Semantics |
|---|---|---|---|---|
| **Cancel** | `cancel_run` :1344 | `cancel_event.set()` | `is_cancelled` (~5s in waits; between routes) | Stops the current export *immediately mid-wait*; partial `RunResult`; not a failure. |
| **Skip** | `skip_route` :1337 | `skip_event.set()` | `should_skip`→`_should_skip` :272 (one press = one route) | Disabled in fast mode (`st.fast_run`) — the JS button is greyed (`app.js:787`). |
| **Pause** | `pause_or_resume` :1358 (toggle) | `pause_event.set()/clear()` | `is_paused`→`exporter._wait_while_paused` | Holds BETWEEN routes (never inside a thread-affine wait). Works in fast mode (every worker parks). |

**`_should_skip` (`gui_worker.py:272-276`)** is self-clearing: `if self.skip.is_set(): self.skip.clear(); return True`. One button press skips exactly one route. **`pause_event` is NOT self-clearing** — `is_paused` returns its state and the engine spins until it clears; `cancel_run` clears it so a paused run can be cancelled, and `_end_task` clears it so a paused state never leaks across runs.

**Login events** are separate: `login_done` (set by `finish_login`, `gui_api.py:1398`) and `login_cancel` (set by `cancel_login`, :1407). `LoginWorker` waits on `done` in a `while not self.done.wait(0.x)` loop. `cancel_login` sets *both* `login_cancel` and `login_done` so the wait unblocks (`gui_api.py:1407-1408`); the worker then checks `cancel.is_set()` and does NOT save. `_on_closed` (`gui_api.py:349-357`) also sets `cancel_event`, `login_cancel`, `login_done` so a window close at any point lets every worker exit cleanly.

---

## 8. Each worker's `run()` — what it does, what it posts

All workers are `threading.Thread(daemon=True)` subclasses in `gui_worker.py`. They never touch the window; they only `self.q.put(...)`.

### ExportWorker (`gui_worker.py:223-460`)

The workhorse: runs **one or more** `ReportSpec`s sequentially. `specs` is normalized to a list (`gui_worker.py:168`), so callers can pass one or many.

- `run()` (`:435`): builds the Events sink, calls `_run_specs(events, results)`, then posts `("export_done", results)`. On `AuthError` → `("error", ("auth", …))`; on `PreflightError`/`BrowserNotFoundError` → `("error", ("general", …))`; on any other exception → `log.exception` + `("error", ("general", "Type: msg"))`. If any reports finished before the error, it first posts `("export_partial", results)` so "Save run report" still covers them.
- `_run_specs` (`:292-344`): for each spec — reset per-report progress, optionally clear `out_dir` (B3 refresh), pick `run_export` vs `run_export_parallel` (fast mode, `workers>1`), append `(spec, result)`, then B2 auto-consolidate inline (`:342`). This method **does NOT post `export_done`/`error`** — the caller owns the run lifecycle (so `BatchWorker` can reuse it per-environment).
- `_on_route` (`:257-270`): the tally. Under `_tally_lock` (fast mode fires this from many threads), it keeps `route → latest status` so the end-of-run retry pass (which re-reports a route, e.g. failed→saved) **updates in place rather than double-counting**, derives counts, and posts `("progress", {done,total,route,report,report_i,report_n,...counts})`.
- **Live screenshots:** `request_screenshot(worker_no)` (`:195`, called from the bridge thread by `GuiApi.request_preview`) adds to `_shot_requests` under `_shot_lock`; the engine thread polls `_shot_wanted` (`:202`, one request = one shot) and answers via `_on_screenshot` (`:210`) → `("preview_shot", (w, b64, note, url))`. Playwright thread-affinity is why the GUI thread can't snap directly — it sets a flag the owning thread drains at its next safe poll point.
- **B3 env tagging:** when `out_base` is set, `_run_specs` wraps `spec.filename` with `dataclasses.replace(spec, filename=lambda r: env_tagged_filename(spec.filename(r), tag))` (`:329-334`) — front-stamps the `<src-env>` onto every output file in one place (covers sequential + parallel + both retry passes), keeping `subdir`/`label`/consolidator-mapping on the original spec.

### BatchWorker (`gui_worker.py:461-586`)

B3 "Export Everything": runs selected report types × selected environments sequentially, **reusing `ExportWorker._run_specs` once per environment** (so resume/idempotency, fast mode, pause, auto-consolidate all come free).

- Per-env targeting uses the **process-global `common.set_site`** (`:450`), NOT `set_thread_site` — because the batch is a single sequential orchestrator under the single-task gate, so mutating the global is safe; the user's original selection is captured (`original = get_site()`, `:441`) and restored in `finally` (`:495`).
- For each pending step (`status != "done"`): `_wait_while_paused` (B1 hold between envs), break on cancel, `set_site(src,env)`, post `("batch_progress", {src,env,label,done,total,steps})`, build an `ExportWorker` with `out_base = <dest>/<src-env>`, and call `ew._run_specs(ew._build_events(), [])`.
- `AuthError`/`BrowserNotFoundError` → post `("error", …)` and **return keeping the manifest** (every env would hit the same wall — fix the cause and resume). Other exceptions → log, leave the env pending, `continue` (don't mark done). Done envs persist via `batch_manifest.mark_done` (`:488`).
- `_step_views` (`:407-428`) builds the ordered per-env stepper view (each step `done`/`running`/`pending`) **from the manifest** so it's correct across a resume. Posts `("batch_done", {done,total,cancelled,complete})` at the end.

### ConsolidateWorker (`gui_worker.py:587-619`)

Runs one consolidator (or comparison `compare`/`compare_folders` — `_launch_compare` passes the run fn here too). Builds a minimal `Events(on_log, is_cancelled)`, calls `consolidate_fn(events=, confirm_overwrite=self.confirm, day=self.day)`, posts `("consolidate_done", ConsolidateResult)`. The `confirm` callback is **pre-decided** by the UI (overwrite resolved by `consolidate_info` + the JS confirm dialog before start), so it just returns `True`. Crash → `("error", ("general", …))`.

### LoginWorker (`gui_worker.py:1232-1474`)

Opens a headed browser for SSO+MFA and saves a portable storage_state. Full browser-order logic lives in `common.py`; the worker orchestrates: honor the user's pick → silent device sign-in first (`try_device_sso_login`) → Built-in Chromium headed → persistent-profile Edge recapture → Chrome fallback. Posts `login_open` (browser is up), then one of `login_saved` / `login_device_ok` / `login_failed` / `cancelled` / `("error", …)`. The hard-won detail: it captures the instant a real TSMIS login appears and treats "no tabs remain" (not the original tab closing) as the close signal (`_run_login_in_browser`, `:1244-1321`).

### CheckWorker (`gui_worker.py:1579-1645`)

Launch-time readiness probes. Posts the instant checks first — `("check", ("output", status, text))` and `("check", ("tools", …))` — then the slower per-browser probes `("check", ("browser_<ch>", …))`, then `("checks_done", results)`. `_handle("check")` updates `self._checks[key]` and pushes state; `_on_checks_done` (`gui_api.py:683-699`) flips `checks_running` off, warns if the *selected* browser is unusable, and triggers `_maybe_autoscan("startup")`.

### ResetWorker (`gui_worker.py:620-679`)

"Delete all reports". `reset_targets(include_input)` (`:95`) enumerates the `(label, Path)` pairs (run folders, legacy flat dirs, consolidated/comparison output, the Export-Everything store, failure shots, optionally TSN input PDFs — never logs/login/settings/profile). Deletes between targets (cancellable; `shutil.rmtree(onerror=...)`), reports what was **actually freed** (before − remaining, so Excel-locked files aren't counted as deleted), posts `("reset_done", {files, mb, errors, cancelled})`. The bridge side has a **single-use confirm token** (see §10).

### ChromiumWorker (`gui_worker.py:680-796`)

Download/delete the app-owned Built-in Chromium. Download drives the **bundled Playwright Node driver** (`compute_driver_executable()` + `install chromium --no-shell`) with `PLAYWRIGHT_BROWSERS_PATH` aimed at `DOWNLOADED_BROWSERS_DIR` — works frozen (no `python -m playwright`), streams throttled progress (ANSI-stripped) to the log, `CREATE_NO_WINDOW`, cancellable (kills the subprocess). Delete `rmtree`s only that folder. Posts `("chromium_done", {ok, action, cancelled, error})`.

### EnvCheckWorker (`gui_worker.py:797-903`)

The idle "Verify environment". Opens TSMIS headless exactly like an export (`new_authed_browser`), reads the page's own `CONFIG` via `_CONFIG_JS` (the same source `_site_params_ok` trusts), compares to `get_site()`, screenshots (JPEG q70 → base64). **Always posts exactly one `("env_shot", dict)`** — even on failure (with `error` set) — so the task gate can never wedge. `_on_env_shot` (`gui_api.py:1434`) turns it into a `preview` event with an `env_info` payload the modal renders as a verdict banner.

### UpdateWorker (`gui_worker.py:1475-1578`)

Off-thread one-click update/revert. Action `"check"` → `updater.check_for_update()` → `("update_status", {phase:"available"|"none", ..., "_info": UpdateInfo})`. The `_info` key carries the Python-side `UpdateInfo`; `_on_update_status` pops it into `self._update_info` and **strips it before the dict reaches JS** (`gui_api.py:728-733`). Action `"download"`/`"revert"` → `download_and_stage` with an `on_progress` callback posting `phase:"downloading"` at each new percent, then `phase:"staged"`. `revert` first resolves `resolve_previous_release()`. Network/disk only — no Playwright.

### EnvScanWorker (`gui_worker.py:904-1162`)

The big concurrency story — see §9.

---

## 9. EnvScanWorker concurrency in depth

"Check all environments" probes **every** src×env combo headless (does sign-in complete, does the page load the *requested* site, can the form pull data, is every report type offered). It's deliberately **fast** because it auto-runs after startup/sign-in.

### Shared-queue scanners

`run()` (`gui_worker.py:848-938`):

1. `combos = [(s,e) for s in DATA_SOURCES for e in ENVIRONMENTS]` (six).
2. `n = min(MAX_SCANNERS=3, len(combos)) if has_valid_auth() else 1` — **device sign-in mode (no saved auth file) caps to 1 thread**, because the persistent Edge profile can only be open in one browser (the same rule fast mode applies).
3. If `n>1`, `n = self._parallel_scanners(n)` (the channel guard, below).
4. A `queue_mod.Queue` `work` is filled with all combos; `n` scanner threads each `work.get_nowait()` off it until empty or cancel.
5. `results` dict + `fatals` list guarded by a `lock`.
6. Each scanner: `with sync_playwright() as p:` (its OWN Playwright — the sync API is thread-affine), lazily creates one `new_authed_browser(p, parallel=True)` browser on its first combo, and reuses it across combos.

```python
def scanner(worker_no):
    with sync_playwright() as p:
        browser = page = None
        while not self.cancel.is_set():
            try: src, env = work.get_nowait()
            except queue_mod.Empty: break
            set_thread_site(src, env)                 # ← pin THIS thread's target
            if browser is None:
                browser, _ctx, page = new_authed_browser(p, parallel=True)
            out = self._check_one(page, src, env, report_specs)
            with lock: results[out["key"]] = out
            self.q.put(("env_access", out))
        ... finally: set_thread_site(None, None); browser.close()
```

### `set_thread_site` threading-local + how `get_site()` consults it

`common._thread_site = threading.local()` (`common.py:121`). `set_thread_site(src, env)` (`common.py:124-131`) sets `_thread_site.pair = (src, env)` for the *calling thread only* (both-None or partial = clear). `get_site()` (`common.py:134-138`):

```python
def get_site():
    pair = getattr(_thread_site, "pair", None)
    return pair if pair else (_data_source, _environment)   # pin, else global
```

So every site-aware helper that flows through `get_site()` — `get_url`, `expected_host`, `_site_params_ok`, the signed-in host check, custom-URL overrides — **retargets for that thread only**. Three scanner threads can each navigate to a *different* env simultaneously without racing, and **the user's header selection (the process-global `_data_source`/`_environment`) is never touched** (`set_site` from the bridge thread is independent). Engine/login/export threads never call `set_thread_site`, so they always follow the global. The scanner clears the pin in `finally` (`gui_worker.py:892`).

### The parallel-channel rule

`_parallel_scanners(n)` (`gui_worker.py:940-959`): probes `resolve_parallel_channel(p)` once (cached). If the only usable browser is **managed Edge** (`channel == "msedge"`), it returns `1` — three concurrent managed-Edge sessions restoring the same saved session is the exact failure fast mode hit in the field (org-managed Edge misbehaves under concurrency). Only an unmanaged Chromium/Chrome parallel channel allows real parallelism. `new_authed_browser(p, parallel=True)` itself prefers Built-in Chromium → Chrome → Edge-only-as-last-resort.

### Per-combo verdict (`_check_one`, `gui_worker.py:961-1068`)

**Never raises** — the answer (crashes included) rides in the returned dict's `status`/`detail`. Sequence: `navigate_with_auth` (→ `unreachable` on `SiteUnreachableError`), `is_logged_in` (→ `denied`/`no_signin`), read `_CONFIG_JS` (→ `wrong_site` if the page loaded a different env/src), read the report dropdown via `_REPORT_OPTIONS_JS` (`gui_worker.py:776-793` — finds each option by text, flags greyed via any common disable convention), then a real `preflight` on the first *available* report type (→ `no_reports` if the data round-trip fails; the form is static HTML signed-out, so form presence proves nothing). Final mapping via `env_verdict(config_readable, reports_readable)` (`:796-812`, a pure unit-tested function that is **fail-closed**: unreadable CONFIG/dropdown ⇒ `unverified`, never a silent green `ok`). Verdict states: `ok | unverified | reports_off | no_reports | denied | no_signin | wrong_site | unreachable | error`.

Results stream live: each combo posts `("env_access", out)` as it finishes (`_on_env_access` stamps `checked_at`, stores in `self._env_access`, pushes state → live Settings rows + title-bar chip). At the end `("env_access_done", {ok,done,total,cancelled,error})`; if **every** scanner died (`fatal and len(fatals)==n`), the unchecked combos are filled with the fatal so no row stays "checking". `_on_env_scan_done` (`gui_api.py:1505`) **deletes any still-"checking" entries** (a cancelled scan leaves later sites back at "not checked", never a stale spinner).

---

## 10. Bridge-input hardening (path/index/token validation)

Untrusted JS input is validated at the boundary:

- `_pick_report(registry, idx)` (`gui_api.py:515-524`) — bounds-checked registry row or `None` for a bad/non-numeric index. A malformed bridge call can't `IndexError` after `_task` was set and wedge the gate.
- `_safe_day(day)` (`gui_api.py:526-539`) — a consolidate/compare `day` must be `None`/empty or an **existing** run folder; a traversal like `..\..\Windows` raises `ValueError`. So a crafted day can't resolve a path outside the output area.
- `_resolve_under_output(name)` (`gui_api.py:541-550`) — resolves a dropdown run-folder NAME to an absolute path, rejecting anything that escapes `OUTPUT_ROOT.resolve()`. Browse… absolute paths are the user's explicit choice and skip this.
- `_parse_env_keys` (`gui_api.py:1155-1166`) — validates `src-env` keys into ordered, de-duped `(src,env)` combos; unknown keys dropped.
- **Reset confirm token:** `reset_preview` (`gui_api.py:1935-1949`) issues `secrets.token_urlsafe(16)` bound to the `include_input` flag and stores `(token, include_input)`. `start_reset` (`gui_api.py:1951-1978`) consumes it single-use and **refuses** unless `confirm_token` matches AND `include_input` matches — so a direct bridge call can't skip the preview the user approved.
- `open_release_page` constrains the URL via `updater.safe_release_url` (API-sourced `html_url` could otherwise launch an arbitrary handler).

---

## 11. JS boot, bridge readiness, and the mock

### `boot(realApi)` (`app.js:2251-2299`)

`booted` guard (one-shot). Sets `api = realApi`, then retries `get_initial_state` **up to 6 times** with backoff `Math.min(1000*attempt, 3000)`, **re-grabbing `window.pywebview.api` each round** (`app.js:2270-2272`) because on a cold WebView2 the api object appears before its method stubs are injected (pywebview trap 5). On success: `S.init = init`, `buildStatic()`, `fillSettings()`, `bindEvents()`, `S.st = S.init.state`, `renderState()`, then defines `window.__tsmis = {dispatch, test_state}` and calls `api.ui_ready()` (which sets Python's `_ready` so `_sender` starts). On persistent failure → `showFatal`.

### `bridgeReady()` gates on the METHOD, not the object

```js
const bridgeReady = () =>
  !!(window.pywebview && window.pywebview.api
     && typeof window.pywebview.api.get_initial_state === "function");
```

(`app.js:2310-2312`.) Two-layer attach:
- `pywebviewready` event → `if (bridgeReady()) boot(window.pywebview.api)` (`app.js:2314`).
- A 150 ms `setInterval` poll (`app.js:2322`) catches a ready event that fired before the listener attached — keeps running until `booted`.
- Reassuring "Still starting…" `showFatal` at **8 s** (the poll keeps going; a late bridge still boots and clears it), real failure banner at **60 s** (`app.js:2330-2344`).

### `dispatch` routing (`app.js:1428-1455`)

Each event in the batch is isolated in a `try/catch` (one bad payload must not take down the rest; failures go to `api.log_js_error`). `switch(ev.t)`: `state`→`renderState`, `settings`→`fillSettings`, `log`→`appendLog` (sets `sawLog`), `progress`→`renderProgress` *only if runMode is export/batch*, `wstatus`→`updateWorkerStatus`, `preview`→`showPreviewEvent`, `run_started`→`startRunUi`, `run_ended`→`endRunUi`, `modal`→`showMessage`. **The log pane scrolls ONCE per batch** (`if (sawLog) scrollLogToEnd()`, `:1454`) — a batch can carry hundreds of lines, and per-line `scrollTop` would force a reflow each.

### `WANT_MOCK` / `makeMockApi` (`app.js:2305`, :2350-3091)

`const WANT_MOCK = /[?#&]mock\b/.test(location.search + location.hash)` — engaged **only** by a `#mock`/`?mock` flag. `if (WANT_MOCK) boot(makeMockApi())` (`app.js:2317`). **The mock must never auto-start without the flag** — a cold WebView2 can inject the real bridge later than any timeout, and a silent mock fallback would show convincing fake exports inside the real app. So without `#mock` the page only ever waits for the real bridge. `makeMockApi` returns an object with the same method names as `GuiApi`, driving the same `dispatch` with simulated `push(...)` events (its own `st`, fake screenshots via canvas, timer-driven runs).

---

## 12. `gui_main.py` startup ordering (load-bearing)

`main()` (`gui_main.py:67-112`) runs a **strict order** dictated by the pywebview traps (owned by [../gui.md](../gui.md)):

1. **Swap-mode branch FIRST** (`:75`): `if updater.SWAP_FLAG in sys.argv: updater.run_swap_mode(...)` — before logging/paths/CLR, because the staged-exe process runs from `data\update\staged` and normal path resolution would aim at the wrong folder. Never returns.
2. `setup_logging(enable_faulthandler=False)` (`:83`) — faulthandler is disabled in the GUI process (it dumps on the CLR's routine first-chance access violations and deadlocks init; trap 3).
3. `_unblock_dotnet_assemblies()` (`:84`) — strips the NTFS `Zone.Identifier` (Mark-of-the-Web) stream from `_internal/{pythonnet,clr_loader,webview}` **before the CLR loads** (trap 4), else .NET refuses tagged assemblies.
4. `updater.cleanup_leftovers()` (`:90`) — drops `*.old` and stale staging from a prior update.
5. `import gui_api` (`:95`, deferred — a missing pywebview in dev shows a message box, not a stderr crash), then `gui_api.run()`.

`run()` (`gui_api.py:2165-2221`): creates the `GuiApi`, resolves the UI index (`_ui_index_path`, frozen `_internal/ui/` vs dev `scripts/ui/`), sizes the window to fit the screen, `webview.create_window(..., js_api=api, text_select=True)`, `api.attach(window)`, then `webview.start(gui="edgechromium", debug=, private_mode=False, storage_path=WEBVIEW_PROFILE_DIR)`. `gui="edgechromium"` is **forced** so a missing WebView2 runtime fails loudly via `_fatal_box`. `attach` (`gui_api.py:179-190`) subscribes **only** `closed` (never `shown` — trap 2) and spawns `gui-icon` to set the icon off-STA.

---

## 13. Extension recipe — add a method + worker + kind + renderer

End-to-end, to add (say) a new long-running task "frobnicate":

1. **Worker** (`gui_worker.py`): subclass `threading.Thread`, take `(queue, cancel_event, …)`, do the work posting `self.q.put(("frob_progress", …))` and a terminal `self.q.put(("frob_done", {...}))` (and `("error", (kind,msg))` on failure). Document the new kinds in the protocol docstring (`:8-55`).
2. **Bridge method** (`gui_api.py`): `@_api_method def start_frob(self, …): validate pure inputs; if not self._try_claim_task("frob"): return {"error": …}; self.cancel_event.clear(); self._set_dot("busy", …); self._emit({"t":"run_started","mode":"consolidate","label":…}); self._push_state(); FrobWorker(self._q, self.cancel_event).start(); return {"ok": True}`. Import the worker at the top (`gui_worker` import block, `gui_api.py:45-48`). Add `"frob"` to the `cancel_run` whitelist (`gui_api.py:1348`) if it honors cancel.
3. **Pump handler** (`gui_api.py:_handle`): add `elif kind == "frob_progress": self._emit({"t":"progress","p":payload})` and `elif kind == "frob_done": self._on_frob_done(payload)` where `_on_frob_done` ends with `self._end_task()`. (An unhandled kind now falls through to `_handle`'s `else` and is **logged** (P0), not silently dropped — but it still needs its own branch to do anything.)
4. **Snapshot** (if the task needs persistent UI state): add a field to `_state_snapshot` (`gui_api.py:204`) and clear it in `_end_task`.
5. **Renderer** (`app.js`): add the JS caller (e.g. a button `onclick` in `bindEvents`), surface `{"error"}` via `showMessage`, and handle any new `ev.t` in `dispatch` (`:1432`). If you reuse `progress`/`run_started`/`run_ended` you get the progress card for free.
6. **Mock** (`app.js:makeMockApi`): add a matching `start_frob: async () => {...}` that `push(...)`es the same event sequence, so `#mock` previews it.
7. **Golden check:** extend `build/check_gui_bridge.py`.

**Add a `GuiApi` method without a worker** (pure query, e.g. `report_library_info`): just `@_api_method`, validate, return a dict. No task slot, no `run_started`.

**Add a new compare type / consolidator:** the bridge is generic — `start_compare`/`start_compare_env`/`start_consolidate` already read the registries (`reports.py`), so you only touch `reports.py` + the module (see [../reports.md](../reports.md) and the CLAUDE.md "Extending" section). `get_initial_state` re-derives the UI lists from the registries.

---

## 14. Gotchas a maintainer will trip on

- **Thread-affinity is absolute.** The bridge/UI thread must never touch a Playwright page. Screenshots are request-flag-then-drain (`_shot_wanted`); the `gui-pump` and `gui-icon`/`_flash_taskbar` threads use pure Win32 (no CLR) off the WinForms STA thread.
- **`_handle` logs unknown kinds (`gui_api.py:462-564`).** A worker that posts a `kind` not in the if/elif chain falls through to the `else`, which logs `log.warning("unhandled worker event kind …")` (P0) — it no longer vanishes with no trace, but it still does nothing useful. If a new worker message "does nothing", check you added the `_handle` branch.
- **The snapshot is full-state.** Don't push a partial state from JS expecting Python to merge it — Python is the sole owner. To change what the UI shows, mutate `GuiApi` state under `_lock` and `_push_state()`. JS `renderState` re-derives *everything* from the snapshot each time.
- **Claim the task slot AFTER pure validation, BEFORE any blocking dialog.** A bad index/day that `raise`s after `self._task` is set wedges the gate until restart. Compare flows claim before the save dialog and must `_release_task()` on cancel/error (the `try/except: _release_task(); raise` pattern).
- **`pause_event` does not self-clear; `skip_event` does.** Forgetting that pause persists (and that `_end_task`/`cancel_run` must clear it) leaks a paused state into the next run.
- **`progress` events are ignored unless `S.runMode` is "export" or "batch"** (`app.js:1440`). A consolidate/compare run uses an indeterminate bar; posting `("progress", …)` from one of those does nothing on screen.
- **Batch headline vs the bar.** A batch's "which environment" arrives as a `state` push *between* per-route `progress` events; `syncBatchHeadline` (`app.js:1304`) refreshes the headline + stepper **but deliberately NOT the bar** — re-running `renderProgress` with the previous env's 100% would overshoot a whole environment then snap back. Don't move the bar from a state push.
- **`_info`/`UpdateInfo` must be stripped before JS.** `UpdateInfo` is not JSON-serializable as the UI expects; `_on_update_status` pops `_info` (and `manual`) before the dict becomes the JS-visible `self._update`. Adding a non-serializable field to an `update_status` payload will hit the `default=str` fallback (it becomes a useless string).
- **`wrapper.__name__` on `_api_method`.** pywebview enumerates methods by name; a decorator that doesn't preserve `__name__` would break the bridge stub injection.
- **Auto-consolidate runs INLINE on the ExportWorker thread** (`_auto_consolidate`, `gui_worker.py:214`), NOT via a `ConsolidateWorker` — because the single-task gate already holds the `export` slot and a separate worker claiming `consolidate` would deadlock the gate.
- **`_sender` blocks on `_ready` until `ui_ready()`.** If JS never calls `ui_ready()` (a boot failure), nothing is ever dispatched to JS — but `_on_closed` sets `_ready` so the sender can drain its `_SHUTDOWN` and exit on window close.

---

## See also

- [../gui.md](../gui.md) — UI stack, WebView2 profile, the five pywebview traps (owned there), `#mock` verification loop.
- [../engine-and-reliability.md](../engine-and-reliability.md) — the export engine the workers drive, run-lifecycle/ETA/stepper, live status + previews.
- [../auth-and-signin.md](../auth-and-signin.md) — `LoginWorker` browser order, device sign-in, the two title-bar login chips.
- [../build-and-release.md](../build-and-release.md) — the updater swap-mode/MOTW/SHA-256 pipeline `UpdateWorker` feeds.
- [../comparison-engine.md](../comparison-engine.md) / [../reports.md](../reports.md) — what `ConsolidateWorker` and the compare bridge methods call.
