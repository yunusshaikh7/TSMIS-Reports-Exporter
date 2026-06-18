# GUI: pywebview / WebView2 desktop shell

What this doc covers: the desktop GUI's UI stack, the Python⇄JS bridge and threading/queue model, the WebView2 profile and data-location decisions, the five hard-won pywebview field traps (this doc OWNS them), and how to live-verify `scripts/ui/` changes.

For the engine the GUI drives, see [engine-and-reliability.md](engine-and-reliability.md); for sign-in flows surfaced in the GUI, [auth-and-signin.md](auth-and-signin.md); for the updater swap-mode/MOTW/SHA-256 pipeline (full treatment), [build-and-release.md](build-and-release.md) and [it-and-security.md](it-and-security.md); for golden checks + verification loops, [verification-and-testing.md](verification-and-testing.md); cross-cutting field-failure narratives live in [lessons.md](lessons.md).

> **Code-level walkthrough:** [internals/gui-bridge.md](internals/gui-bridge.md) — the full Python⇄JS message lifecycle (kind→handler→event→renderer), the single-task gate, every worker's `run()`, and the env-scan concurrency.

## UI stack

The packaged product is a **pywebview window using the Edge WebView2 backend**, rendering `scripts/ui/` (`index.html` + `app.css` + `app.js`) — **plain HTML/CSS/JS, no framework and no build step**. Static files ship in the bundle; end-user setup stays global-pip. This replaced the original Tkinter window (v0.8.0): Tk could neither match the approved design (Windows-11 look, dark titlebar, two-column layout) nor stop cutting off on small screens. A web layout is responsive (stacks + scrolls below ~980px wide; theme = System/Light/Dark header toggle persisted in `localStorage`, resolved to an effective `html[data-theme]` before first paint).

WebView2 is a safe dependency here: it ships with Windows 10/11 and evergreen Edge — the same Edge this tool already requires. `tkinter`/`_tkinter` are **excluded** from the bundle.

**`webview.start(gui="edgechromium")` is forced** so a missing runtime fails loudly with a clear message box (`_fatal_box`, "The app window could not be created.") instead of silently degrading to the legacy MSHTML backend. Verified in `gui_api.run()`:

```python
webview.start(gui="edgechromium", debug=debug,
              private_mode=False, storage_path=str(WEBVIEW_PROFILE_DIR))
```

Three Python modules own the GUI; the engines underneath stay console-free:

| Module | Role |
|---|---|
| `scripts/gui_main.py` | Entry point. `_bootstrap()` dev import paths; swap-mode branch; `_unblock_dotnet_assemblies()`; `setup_logging(enable_faulthandler=False)`; `updater.cleanup_leftovers()`; then `gui_api.run()`. |
| `scripts/gui_api.py` | The `GuiApi` js_api bridge + GUI state + the worker-queue pump + `run()` (creates the window, starts the webview loop). |
| `scripts/gui_worker.py` | The worker threads (`ExportWorker`, `LoginWorker`, `CheckWorker`, `ConsolidateWorker`, `BatchWorker`, `EnvCheckWorker`, `EnvScanWorker`, `ChromiumWorker`, `ResetWorker`, `UpdateWorker`). **Unchanged across the Tk→WebView rewrite.** |

Only `cli.py` and `gui_*.py` touch `print`/`input`/`msvcrt`/the window. Core code (`common.py`, `exporter.py`, the consolidator cores) reports via the `Events` sink (`scripts/events.py`) and raises exceptions — never `print`/`input`/`sys.exit`.

## UI-demo: visual source of truth

`C:\Users\Yunus\Projects\tsmis-exporter-ui-demo` is a Lovable-built React/TanStack/Tailwind demo the user "really liked the look of". Its OKLCH design tokens, dark-titlebar layout, and component styling were ported into `scripts/ui/app.css` during the v0.8.0 rewrite (June 2026). It is **feature-stale** (models v0.4.x — no fast mode, dated outputs, device sign-in, or site pickers): treat it as the **visual** source of truth / design inspiration only, NEVER as a feature spec.

## Threading and the queue model

Playwright's sync API is **thread-affine** — only the thread that created a page may touch it. So all browser work runs on worker threads. The message flow:

1. **Workers → GUI:** each worker thread posts `(kind, payload)` tuples onto `GuiApi._q` (a `queue.Queue`). The full per-message protocol is documented at the top of `gui_worker.py`, and `gui_api._handle` is the exhaustive dispatcher. The handled kinds are `log`, `progress`, `worker_status`, `preview_shot`, `env_shot`, `env_access`, `env_access_done`, `reset_done`, `chromium_done`, `export_done`, `export_partial`, `consolidate_done`, `login_open`, `login_saved`, `login_device_ok`, `login_failed`, `cancelled`, `batch_progress`, `batch_done`, `update_status`, `check`, `checks_done`, `error` — note the `gui_worker.py` docstring itself omits the last four (`check`/`checks_done` from `CheckWorker`; `batch_progress`/`batch_done` from `BatchWorker`).
2. **The pump:** `GuiApi._worker_pump` (thread `gui-pump`) drains `_q` and dispatches each message through `_handle(kind, payload)` — the state machine that mutates GUI state and enqueues JS events. (This is the WebView reimplementation of the old Tk `gui_app._handle`.)
3. **GUI → JS, single ordered path:** `_handle`/api methods enqueue events onto a SECOND queue `_out`. **One** sender thread (`gui-send`, `GuiApi._sender`) drains `_out`, batches up to **200** events, and delivers them as one JSON array via `evaluate_js("window.__tsmis && window.__tsmis.dispatch(...)")`. Because everything to JS goes through this one ordered queue, log lines, progress, and state snapshots can never interleave out of order. `json.dumps(batch, default=str)` so a future non-JSON payload degrades to a string instead of killing the whole batch.
4. **JS → Python:** `app.js` calls back through `window.pywebview.api.<method>()` (the public `GuiApi` methods), each returning a Promise.

State mutations take `self._lock` (an `RLock`). In fast mode each export worker owns its own Playwright/browser/context. Two `threading.Event`s gate the loop (`cancel_event`, `skip_event`) plus `pause_event` (B1 between-route hold); login uses `login_done`/`login_cancel`.

### Sequence (one event batch)

```
worker thread ── (kind,payload) ──▶ _q ──▶ _worker_pump/_handle ──▶ _out
                                                                       │
                                              _sender (one thread, batch ≤200)
                                                                       │
                                    evaluate_js → window.__tsmis.dispatch([…])
                                                                       │
app.js dispatch() routes each ev.t (state|log|progress|run_started|run_ended|
                                     wstatus|preview|modal|…) to a renderer
                                                                       │
JS user action ── window.pywebview.api.<method>() ──▶ GuiApi (Promise reply)
```

## UI layering: Python owns state, JS owns presentation

**Python owns all app state** (auth, task, checks, days, batch, update, env-access) and pushes **full snapshots** (`_state_snapshot()` → `{t:"state", s:…}`, sent on every `_push_state()`). `app.js` owns ONLY presentation + form fields and **never invents log lines** — everything shown in the log pane originates in Python so the `tsmis.ui` file-log mirror stays complete. The mirror: `_emit_log(text)` logs the line to the `tsmis.ui` logger AND emits it to JS; `_emit_modal` and `ui_event` likewise log every dialog and user UI event. So `tsmis.log` carries the user's view of a run (what was clicked, what was reported) next to the engine's own diagnostics — the "one log upload answers it" contract.

Every `GuiApi` public method is wrapped by `_api_method`: an uncaught exception in a windowed `.exe` would vanish (no stderr) and leave the UI hanging on a dead Promise, so it logs the full traceback to `tsmis.crash` and returns a structured `{"error": …}` to JS instead. Uncaught JS errors come back through `api.log_js_error` → `tsmis.crash`.

## Persistent WebView2 profile

The GUI window uses a persistent **app-owned** user-data folder, `paths.WEBVIEW_PROFILE_DIR` (`data\webview2`), via `webview.start(private_mode=False, storage_path=…)`. pywebview's default private mode writes a **fresh Chromium profile into `%TEMP%` on EVERY launch** (tens of MB, leaked when the process is killed) and cold-starts the browser each time. One stable folder avoids both, and the UI stores nothing sensitive in it. (`updater._clear_webview_caches()` drops the WebView2 HTTP caches every launch so an update's new `app.js` is never served stale; Local Storage/theme are untouched.)

## Data location (option A)

The WebView2 profile (above) lives under the app's data tree. The packaged app writes ALL its data — `output/`, the auth token, logs, config, and that profile — **next to the `.exe`**, with a `%LOCALAPPDATA%\TSMIS Exporter` fallback when the folder is read-only (which also flips the updater into link-only mode). The full data-location model (`DATA_ROOT`/`OUTPUT_ROOT`/derived paths) is owned by [architecture.md](architecture.md); the IT/file-by-file view is in [it-and-security.md](it-and-security.md).

## The FIVE pywebview traps (all hit in the field)

These are the load-bearing constraints. Each one cost a real field failure; do not regress them.

### Trap 1 — never rename the main thread; `[main]` is a logging Filter

pywebview detects "is `start()` already running" via the **main thread's NAME**. `logging_setup` must therefore never rename the main thread — it tags `[main]` via a logging `Filter` (`_MainThreadTag`, which rewrites `record.threadName` from `"MainThread"` to `"main"` in the LOG RECORD only) instead of `threading.main_thread().name = …`. Renaming the actual thread makes pywebview's `create_window` treat it as "the GUI loop is already running" and **block forever** running the GUI loop itself. Verified in `logging_setup.setup_logging`.

### Trap 2 — never do work in window-event handlers; set the icon from a worker

pywebview fires window events (`shown`, etc.) on the **WinForms STA thread while WebView2 is still initializing asynchronously on it**. A handler that blocks (the original icon-setter loaded a .NET assembly) starves the message pump and **INTERMITTENTLY deadlocks the window** — "Not responding" + WER `AppHangB1` before the page loads (~6/8 launches at its worst, machine-state dependent). The fix: only `closed` (which fires after the loop ends) is subscribed (`window.events.closed += self._on_closed`); the icon is set from a **plain worker thread** with pure Win32 (`_set_window_icon_late`: `_find_own_window`/`EnumWindows` matched on our own PID → `LoadImageW` + `SendMessageW`/`WM_SETICON`). The taskbar-flash notification (`_flash_taskbar`, `FlashWindowEx`, v0.13.0) follows the SAME off-STA, never-in-a-window-event-handler approach — though it runs **inline on the `gui-pump` thread** rather than spawning its own (the icon setter uses a dedicated `gui-icon` thread). The load-bearing rule is the same: neither runs in a pywebview window-event handler.

### Trap 3 — `faulthandler` is disabled in the GUI process

`gui_main.main()` calls `setup_logging(enable_faulthandler=False)`. `faulthandler`'s Windows handler sees the CLR's **routine first-chance access violations** (pythonnet, which the WebView2 backend runs on) and dumps all threads mid-exception-dispatch — observed wedging init ("Not responding", WER `AppHangB1`) and spamming `crash.log` with dumps from healthy-looking runs. Console entry points never load the CLR and keep faulthandler's hard-crash dumps. Python-level crashes in the GUI are still caught by `sys.excepthook` + `threading.excepthook` and the `_api_method` wrapper. Verified in `logging_setup.setup_logging`'s docstring and code.

### Trap 4 — Mark-of-the-Web kills the CLR; `_unblock_dotnet_assemblies()`

Extracting a release zip **without Unblock** tags every file with an NTFS `Zone.Identifier` stream, and .NET Framework **refuses to load tagged assemblies** → instant "Failed to resolve Python.Runtime.Loader.Initialize" (field failure, v0.8.0's first download). Dev runs and CI never go through a downloaded zip, so ONLY releases hit it. `gui_main._unblock_dotnet_assemblies()` strips the `Zone.Identifier` streams from the bundled `.NET` trees (`_internal/pythonnet`, `_internal/clr_loader`, `_internal/webview`) **at startup, before the CLR loads** (called right after `setup_logging`, before `cleanup_leftovers`/`import gui_api`). Only the CLR cares — plain Win32 DLL loads ignore the tag — so only those trees are cleaned. Best-effort: on a read-only install it fails and the fatal box explains the manual Unblock. Repro for testing: `Set-Content <dll> -Stream Zone.Identifier` with `ZoneId=3` on `_internal\pythonnet\**`. Full IT/Defender view in [it-and-security.md](it-and-security.md); the in-app-download path never carries MOTW (zipfile writes raw bytes) — see [build-and-release.md](build-and-release.md).

### Trap 5 — the js_api OBJECT appears before its method stubs

On a cold WebView2, `window.pywebview.api` can **exist while pywebview is still injecting the method functions into it** — calling one throws "`get_initial_state` is not a function" and a one-shot boot died on it permanently (field failure, first launch after the v0.10.2 update — the coldest start there is, Windows still scanning every fresh file). Two-layer defense in `app.js`:

- **`bridgeReady()` gates boot on the METHOD, not the object:** `!!(window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_initial_state === "function")`. The `pywebviewready` event handler boots only `if (bridgeReady())`; a 150 ms `setInterval` poll catches a ready event that fired before the listener attached.
- **`boot()` retries `get_initial_state` ~6 times**, re-grabbing `window.pywebview.api` each round (stubs may have landed), with backoff `Math.min(1000*attempt, 3000)`.

A reassuring "Still starting…" banner appears at **8 s** (the poll keeps running; a late bridge still boots); the real failure banner (`showFatal`, "The app's interface couldn't connect to its engine") only at **60 s**.

## The `#mock` API (opt-in only; must never auto-start)

`app.js` ships a built-in mock API that can drive the whole UI — simulated runs included — without launching the real app. It is engaged ONLY when the URL carries a `mock` flag: `const WANT_MOCK = /[?#&]mock\b/.test(location.search + location.hash)`. That's how the layout is screenshot-tested (open `scripts/ui/index.html#mock` in a browser).

**The mock must never auto-start.** A cold WebView2 can inject the real bridge later than any fixed timeout, and a silent mock fallback would show convincing **fake exports inside the real app**. So without `#mock`, the page only ever waits for the real bridge (the poll above) and shows the fatal banner if it never arrives — it never falls back to the mock. The mock factory is `makeMockApi()`; `boot(makeMockApi())` runs only inside `if (WANT_MOCK)`.

## Verifying UI changes (live, via the preview mock)

How to live-verify `scripts/ui/` changes without launching the packaged app, and the gotchas that waste time (from the preview-verification memory):

- **Mock server:** `.claude/launch.json` defines `ui-mock` — a Python `http.server` on **port 8765** serving `scripts/ui`. `preview_start("ui-mock")`, then navigate to **`/index.html#mock`** (the `#mock` hash engages `WANT_MOCK`). Without it the page waits for the real pywebview bridge and shows a fatal banner.
- **Bare `S`, not `window.S`:** app state is `const S` at module scope, which does NOT attach to `window`. In `preview_eval`, reference **`S.st` / `S.init`** directly — `window.S` is always `undefined` (false-negative "not booted").
- **Screenshot service is flaky:** `preview_screenshot` intermittently hangs (30 s timeout) while `preview_eval`/`inspect`/`snapshot` keep working. Verify via **DOM-state evals** (classes, computed styles, geometry) — they're conclusive. Restarting the server sometimes recovers screenshots; don't fight it.
- **Cache / stale page:** the browser caches `app.js`. If the preview server dies and restarts, the loaded page can stay on an OLD `app.js` (reloads silently fail while the server is down). After editing, confirm fresh code loaded with `typeof <a-newly-added-fn> !== 'undefined'`; if stale, cache-bust: `location.replace('/index.html?v='+Math.floor(performance.now())+'#mock')`. `Date.now()`/`Math.random()` are fine in `preview_eval` (it's the page, not a Workflow script).
- **Async confirms:** clicking `#btnStartExport` shows the "No saved login" confirm asynchronously — click Start, then in a SEPARATE eval click the "Start anyway" button, then check `S.st.task`. A single combined eval finds no modal yet.

Golden checks (no login, fast) live under `build\.venv\Scripts\python.exe build\check_*.py` — `check_gui_bridge.py` exercises `gui_api` (its "dialog blew up" traceback is an intentional test, still `[OK]`). Run them after Python edits. Full list + the COM-recalc compare loop: [verification-and-testing.md](verification-and-testing.md).

## Related GUI behaviors (owned elsewhere)

- **Run lifecycle / completion summary / ETA / progress hierarchy / Export Everything stepper** (v0.13.0): `gui_api._build_export_summary`, `_on_batch_progress`, `app.js renderPreflight`/`updateActivityCards`/`updateEta`/`syncBatchHeadline`/`renderBatchSteps`. See [engine-and-reliability.md](engine-and-reliability.md).
- **Live browser status + Preview screenshots** (`request_screenshot` → `common.maybe_screenshot` → `("preview_shot", …)` modal, URL fragment stripped by `page_url_for_display`): [engine-and-reliability.md](engine-and-reliability.md), [auth-and-signin.md](auth-and-signin.md).
- **Settings tab, env-access scan, Verify env, Delete all reports, Built-in Chromium download:** [engine-and-reliability.md](engine-and-reliability.md), [auth-and-signin.md](auth-and-signin.md), [it-and-security.md](it-and-security.md).
- **One-click update / revert title-bar pill** (`_on_update_status`, `update_start`/`update_apply`/`revert_to_previous`): full pipeline in [build-and-release.md](build-and-release.md).
- **The two sign-in title-bar chips** (`_login_states()` → Saved login + Edge one-click): [auth-and-signin.md](auth-and-signin.md).
