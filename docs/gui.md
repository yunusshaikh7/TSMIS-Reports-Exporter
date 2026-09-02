# GUI: pywebview / WebView2 desktop shell

What this doc covers: the desktop GUI's UI stack, the Python⇄JS bridge and threading/queue model, the WebView2 profile and data-location decisions, the five hard-won pywebview field traps (this doc OWNS them), and how to live-verify `scripts/ui/` changes.

For the engine the GUI drives, see [engine-and-reliability.md](engine-and-reliability.md); for sign-in flows surfaced in the GUI, [auth-and-signin.md](auth-and-signin.md); for the updater swap-mode/MOTW/SHA-256 pipeline (full treatment), [build-and-release.md](build-and-release.md) and [it-and-security.md](it-and-security.md); for golden checks + verification loops, [verification-and-testing.md](verification-and-testing.md); cross-cutting field-failure narratives live in [lessons.md](lessons.md).

> **Code-level walkthrough:** [internals/gui-bridge.md](internals/gui-bridge.md) — the full Python⇄JS message lifecycle (kind→handler→event→renderer), the single-task gate, every worker's `run()`, and the env-scan concurrency.

## UI stack

The packaged product is a **pywebview window using the Edge WebView2 backend**, rendering `scripts/ui/` — **plain HTML/CSS/JS, no framework and no build step**. As of v0.18.0 the front-end is split into `index.html` + `app.css` + `app.js` (orchestration) + `mock.js` (the `#mock` fixtures, a SEPARATE file — never edit fixtures in `app.js`) + `ui-dom.js` / `ui-matrix.js` / `ui-settings.js` (renderer modules) + `contract.js` (the bridge enum mirror of `scripts/contract.py`). Static files ship in the bundle; end-user setup stays global-pip. This replaced the original Tkinter window (v0.8.0): Tk could neither match the approved design (Windows-11 look, dark titlebar, two-column layout) nor stop cutting off on small screens. A web layout is responsive (stacks + scrolls below ~980px wide; theme = System/Light/Dark header toggle persisted in `localStorage`, resolved to an effective `html[data-theme]` before first paint).

WebView2 is a safe dependency here: it ships with Windows 10/11 and evergreen Edge — the same Edge this tool already requires. `tkinter`/`_tkinter` are **excluded** from the bundle.

### Design tokens — colour, radius, motion, and TYPE

`app.css` opens with the token block. Colour and radius have been tokenised for a
long time (62 custom properties; only two hardcoded hex values in the whole
sheet). **Type joined them after an audit found 13 distinct font sizes across 101
declarations, six of them half-pixels** (9.5 / 10.5 / 11.5 / 12.5 / 13.5). The
six-step scale is `--text-2xs` 10 · `--text-xs` 11 · `--text-sm` 12 ·
`--text-base` 13 · `--text-lg` 15 · `--text-xl` 17, and
`build/check_type_scale.py` fails on a raw px font-size or a non-integer token.

Two things worth knowing before touching it:

- **Whole pixels are the point, not tidiness.** A 1366×768 work PC runs at 150%
  DPI, where a `.5px` size lands between device pixels and Windows rounds it
  inconsistently from one element to the next — which is what made the UI read as
  slightly unfinished on exactly the machines this ships to.
- **The half-pixels were never a finer scale.** Each sat in the same role as its
  integer neighbour (12.5px on tabs and chips, right beside 12px on tabs and
  chips), so each pair collapsed onto one token. `base` is 13px because that is
  what `body` has always been.

**Spacing is deliberately NOT tokenised**, and that is a measured decision rather
than an omission: 48 of the 59 padding/margin/gap declarations already sit on a
2px rhythm. The nine that do not (1 · 3 · 5 · 7 · 9 px) are each a density choice
on a hand-tuned element — `.option-row` at 9px vertical is the height of all 98
option rows; `.route-cell` at 5px is the density of the route grid — and the
layout is built around real constraints (a 1366×768 laptop at 150% DPI is ~910
CSS px, which the stylesheet's own comments design for). Rounding them onto a
grid is a visual decision for the owner, not a cleanup to apply blind.

**`webview.start(gui="edgechromium")` is forced** so a missing runtime fails loudly with a clear message box (`_fatal_box`, "The app window could not be created.") instead of silently degrading to the legacy MSHTML backend. Verified in `gui_api.run()`:

```python
webview.start(gui="edgechromium", debug=debug,
              private_mode=False, storage_path=str(WEBVIEW_PROFILE_DIR))
```

The GUI is owned by a small set of Python modules (v0.18.0 split the old monolith out by concern); the engines underneath stay console-free:

| Module | Role |
|---|---|
| `scripts/gui_main.py` | Entry point. `_bootstrap()` dev import paths; swap-mode branch; the `--self-test` / `--collect-evidence` CLI branches; `_unblock_dotnet_assemblies()`; `setup_logging(enable_faulthandler=False)`; `updater.cleanup_leftovers()`; then `gui_api.run()`. |
| `scripts/gui_api.py` | The `GuiApi` js_api bridge + the worker-queue pump + `run()` (creates the window, starts the webview loop). Mixes in `gui_matrix.GuiMatrixMixin`; delegates task/gate state to `task_coordinator`. |
| `scripts/task_coordinator.py` | **The single owner of task/gate state** (P7a). A monotonic claim **epoch** stamps every worker message so a straggler terminal from a superseded task can't clobber an already-started successor (exactly-once terminal delivery). |
| `scripts/contract.py` + `scripts/ui/contract.js` | The Python⇄JS **bridge enum SSOT** — message kinds, completion states, etc. — so the two sides can't drift. |
| `scripts/gui_endpoint.py` / `gui_matrix.py` / `gui_win32.py` | Extracted endpoint groups (P7b/P7c): the endpoint base, the Matrix feature endpoints (the mixin), and the pywebview/win32 window concerns. |
| `scripts/gui_worker.py` | The worker threads — `ExportWorker`, `LoginWorker`, `CheckWorker`, `ConsolidateWorker`, `BatchWorker`, `EnvCheckWorker`, `ActiveEnvCheckWorker`, `EnvScanWorker`, `ChromiumWorker`, `ResetWorker`, `UpdateWorker`, plus the matrix workers `MatrixBatchExportWorker` / `MatrixCompareWorker` / `DayMatrixCompareWorker` / `MatrixTsnConsolidateWorker`. **Not** force-split. |

Only `cli.py` and `gui_*.py` touch `print`/`input`/`msvcrt`/the window. Core code (`common.py`, `exporter.py`, the consolidator cores) reports via the `Events` sink (`scripts/events.py`) and raises exceptions — never `print`/`input`/`sys.exit`.

## UI-demo: visual source of truth

`C:\Users\Yunus\Projects\tsmis-exporter-ui-demo` is a Lovable-built React/TanStack/Tailwind demo the user "really liked the look of". Its OKLCH design tokens, dark-titlebar layout, and component styling were ported into `scripts/ui/app.css` during the v0.8.0 rewrite (June 2026). It is **feature-stale** (models v0.4.x — no fast mode, dated outputs, device sign-in, or site pickers): treat it as the **visual** source of truth / design inspiration only, NEVER as a feature spec.

## Threading and the queue model

Playwright's sync API is **thread-affine** — only the thread that created a page may touch it. So all browser work runs on worker threads. The message flow:

1. **Workers → GUI:** each worker thread posts `(kind, payload)` tuples onto `GuiApi._q` (a `queue.Queue`). The full per-message protocol is documented at the top of `gui_worker.py`, and `gui_api._handle` is the exhaustive dispatcher. The handled kinds are `log`, `progress`, `worker_status`, `preview_shot`, `env_shot`, `env_access`, `env_access_done`, `reset_done`, `chromium_done`, `export_done`, `export_partial`, `consolidate_done`, `login_open`, `login_saved`, `login_device_ok`, `login_failed`, `cancelled`, `batch_progress`, `batch_done`, `update_status`, `check`, `checks_done`, `matrix_cell`, `matrix_done`, `matrix_export_done`, `active_env_done`, `error` (the kind strings + the completion vocab now live ONCE in `scripts/contract.py` / `ui/contract.js`, so Python and JS can't drift; `run_ended` / the export summary additionally carry the `completion` + `artifact` outcome fields).
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

### What a batch costs — the two coalescing rules

A batch is drained from the queue, not metered, so it routinely carries SEVERAL
full state snapshots — there are ~92 `_push_state()` call sites, 54 of them in
`gui_matrix.py` alone. Two rules keep a burst cheap, and both are locked by
`build/check_state_paint_coalescing.js`:

- **`dispatch` assigns every state but paints only the last.** `S.st = ev.s` runs
  for each one in order (so anything an interleaved handler reads is unchanged);
  `paintState()` runs only at the final state index. Each state is a FULL
  snapshot, so the last paint produces the same DOM the whole sequence would
  have. Measured on the matrix tab: a 20-state batch went **194 ms → 21 ms**.
  The `_lastTask` TSN-rebuild watcher deliberately stays OUTSIDE that guard — it
  watches for a task *transition*, so collapsing the states could step over the
  consolidate→idle edge.
- **`paintState` repaints only the matrix on screen.** All four updaters used to
  run on every push regardless of tab. Arriving at any matrix tab runs its own
  full render (`setTab` / `setEverySub`), so an off-screen matrix loses nothing.

The third piece is `applyLockState`: the ~324 `disabled` writes and eight
container sweeps that greyed the UI on every push now run only when `locked`
actually CHANGES, and the 98 option rows grey from a single **`body.busy`** class
in CSS instead of a per-row class write. That is safe only while every locking
control either exists before the first render or sets its own `disabled` when
built — a new dynamic control must do one or the other. Together these took
`renderState` from 22 `querySelectorAll` sweeps / 324 element writes to **5 / 58**.

> **Measure before "optimizing" an animation here.** Three layout-animating CSS
> rules look like obvious jank (`transition: flex-grow` on the two columns,
> `transition: width` on the progress fill, `@keyframes indeterminate` animating
> `left` forever). Profiled on the matrix tab against a forced-layout control
> they cost **0.05–0.13 ms per frame** — 1.9 ms for the whole 240 ms column
> transition, and ~194 ms per MINUTE for the indeterminate bar, i.e. under 0.4%
> of a frame. They are in isolated layout scopes, so the textbook concern does
> not apply. Left alone deliberately; see [lessons.md](lessons.md) #16.

## UI layering: Python owns state, JS owns presentation

**Python owns all app state** (auth, task, checks, days, batch, update, env-access) and pushes **full snapshots** (`_state_snapshot()` → `{t:"state", s:…}`, sent on every `_push_state()`). `app.js` owns ONLY presentation + form fields and **never invents log lines** — everything shown in the log pane originates in Python so the `tsmis.ui` file-log mirror stays complete. The mirror: `_emit_log(text)` logs the line to the `tsmis.ui` logger AND emits it to JS; `_emit_modal` and `ui_event` likewise log every dialog and user UI event. So `tsmis.log` carries the user's view of a run (what was clicked, what was reported) next to the engine's own diagnostics — the "one log upload answers it" contract.

Every `GuiApi` public method is wrapped by `_api_method`: an uncaught exception in a windowed `.exe` would vanish (no stderr) and leave the UI hanging on a dead Promise, so it logs the full traceback to `tsmis.crash` and returns a structured `{"error": …}` to JS instead. Uncaught JS errors come back through `api.log_js_error` → `tsmis.crash`.

## Persistent WebView2 profile

The GUI window uses a persistent **app-owned** user-data folder, `paths.WEBVIEW_PROFILE_DIR` (`data\webview2`), via `webview.start(private_mode=False, storage_path=…)`. pywebview's default private mode writes a **fresh Chromium profile into `%TEMP%` on EVERY launch** (tens of MB, leaked when the process is killed) and cold-starts the browser each time. One stable folder avoids both, and the UI stores nothing sensitive in it. (`updater._clear_webview_caches()` drops the WebView2 HTTP caches on every **frozen** launch — it sits below the `is_frozen()` guard in `cleanup_leftovers`, since a dev launch serves `scripts/ui` live — so an update's new `app.js` is never served stale; Local Storage/theme are untouched.)

## Data location (option A)

The WebView2 profile (above) lives under the app's data tree. The packaged app writes ALL its data — `output/`, the auth token, logs, config, and that profile — **next to the `.exe`**, with a `%LOCALAPPDATA%\TSMIS Exporter` fallback when the folder is read-only (which also flips the updater into link-only mode). The full data-location model (`DATA_ROOT`/`OUTPUT_ROOT`/derived paths) is owned by [architecture.md](architecture.md); the IT/file-by-file view is in [it-and-security.md](it-and-security.md).

## Accessibility posture (measured 2026-08-21)

This is a Caltrans tool, so Section 508 / WCAG 2.1 AA is a question that gets
asked. These are **measurements against the running UI**, not intentions — every
figure below was taken in the `#mock` across the Export, Compare, Everything ▸
matrix and Settings tabs, in both themes.

| Check | Result |
|---|---|
| Text contrast vs WCAG AA (4.5:1 body, 3:1 large) | **0 failures**, light and dark |
| Accessible names on checkboxes + radios | **117 / 117** — every one via a wrapping `<label>` |
| Accessible names on buttons | **360 / 360** |
| Focus indication | 18 `:focus-visible` rules; **0 of 200** sampled focusables lacked a matching focus rule |
| `prefers-reduced-motion` | Global block neutralises `*, *::before, *::after`, plus a specific re-override for the `!important` theme cross-fade |
| Positive `tabindex` (breaks natural order) | **0** |
| Keyboard traps in hidden panes | **0 of 523** focusables in `display:none` subtrees are Tab-reachable |
| Tab semantics | 4 tablists, each with exactly one `aria-selected="true"` |
| Document `lang` / `title` | `en` / "TSMIS Exporter" |
| Horizontal overflow at 910×512 (a 1366×768 work PC at 150% DPI) | **0 px** on all six tabs |
| Pathological content (a 180-char OneDrive path + a 4× repeated error line, injected into six path/label surfaces) | **0 px** page overflow, **0** elements burst their container |

**Not verified, and not claimed:**

- **Real screen-reader behaviour.** Accessible names exist and the roles are
  right, but nobody has driven this with NVDA or JAWS. Names being present is
  necessary, not sufficient — announcement order and live-region behaviour during
  a run are unmeasured.
- **Keyboard traversal by hand.** The absence of positive `tabindex` and of
  reachable focusables in hidden panes rules out the common traps; actually
  tabbing the whole app has not been done.
- **Non-text contrast** (borders, icon glyphs, focus rings against their
  backgrounds) — the audit measured text only, which is the 1.4.3 criterion.
  1.4.11 non-text contrast is untested.

Two traps worth knowing before you re-run any of this:

- **The `#mock` preview does not composite frames when the pane is hidden**, so
  width and computed flex values there are unreliable — it reported `flex-grow: 0`
  and 2px columns at 1280px while the same page measured correctly at 800px. Use
  height / `scrollHeight`, computed colour, and element counts, which are stable;
  do not conclude a layout bug from a width read alone.
- **Crude probes lie in both directions here.** `read_page` renders the option
  checkboxes as `checkbox "on"`, which looks exactly like a missing label and is
  not — they are wrapped in `<label>`. Splitting the stylesheet on the first
  `prefers-reduced-motion` finds the small matrix-only block and misses the global
  one below it. Check the DOM or the source before believing either.

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
- **Cache / stale page:** the browser HTTP-caches `app.js` **and `app.css`** (and the other `ui-*.js` modules). A page-URL `?v=` cache-bust does NOT refresh them, and a preview-server restart alone does not either (the browser reuses the cached files across restarts). **Reliable fresh assets** after editing: in a preview eval run `await fetch('http://localhost:8765/app.js',{cache:'reload'}); await fetch('http://localhost:8765/app.css',{cache:'reload'});` (add any edited `ui-*.js` the same way) then `location.reload()` and re-navigate to `#mock`. Confirm fresh code loaded with `typeof <a-newly-added-fn> !== 'undefined'`. `Date.now()`/`Math.random()` are fine in `preview_eval` (it's the page, not a Workflow script).
- **Async confirms:** clicking `#btnStartExport` shows the "No saved login" confirm asynchronously — click Start, then in a SEPARATE eval click the "Start anyway" button, then check `S.st.task`. A single combined eval finds no modal yet.
- **Mock event ORDER ≠ production (v0.18.4 lesson):** on a job finish the **mock** emits `state` THEN `run_ended`+`matrix_refresh` (mock.js), but the **real bridge** emits `run_ended` (→ async `renderMatrix`/`renderDayMatrix`) THEN `state` THEN `matrix_refresh` (`_end_task` then `_on_matrix_done`). So an ORDER-sensitive bug won't show by driving the mock's own flow — replay the production order directly: `dispatch([{t:'run_ended'},{t:'state',s:{...S.st,matrix_current:null,task:null}},{t:'matrix_refresh'}])`. This is how the **matrix queue-phantom** (a finished/cancelled compare stuck "running" in the queue panel, both matrices) was caught. Root cause: `.mc-group{display:flex}` (app.css) outranks the UA `[hidden]{display:none}`, so `el.hidden=true` did NOT hide the panel — fixed with `.mc-group[hidden]{display:none}` + clearing the row list on every `renderQueuePanel` path. **Watch for the same trap on any element you hide via `el.hidden` that also has a class-level `display` rule.**

Golden checks (no login, fast) live under `build\.venv\Scripts\python.exe build\check_*.py` — `check_gui_bridge.py` exercises `gui_api` (its "dialog blew up" traceback is an intentional test, still `[OK]`). Run them after Python edits. Full list + the COM-recalc compare loop: [verification-and-testing.md](verification-and-testing.md).

## The comparison matrix (Everything ▸ Comparison-matrix sub-tab)

The Everything pane has **two sub-tabs** (`.subtabs` like Compare's): *Refresh & export*
(`#everyExport`, the batch controls) and *Comparison matrix* (`#everyMatrix`). A single
**`app.js applyMatrixWide()`** computes the full-width context from `S.tab`/`S.everySub`/
`S.compareGroup` and toggles `body.matrix-wide` (+ `body.mw-day` for the by-day matrix,
`body.mw-bl` for the vs-Baseline matrix — each picks its own config corner);
`setEverySub`, `setTab`, and `selectCompareGroup` all call it, so every entry point stays
in sync and leaving always clears it. **Full-width layout:** `.main` is a flex row (not
grid) so the two columns' `flex-grow` can animate — `body.matrix-wide` grows the config
column and shrinks the activity column to a slim, still-present log (the
preflight/completion cards step aside; the grid fills width *and* height with the
data rows sharing the leftover height). NB grid-template-columns can't transition
between `minmax(…fr)` track-lists in Chromium, which is why the layout is flex.
**Both matrices share the same full-width CSS** via three classes — `.mx-host` (the
pane), `.mx-pane` (the matrix container), `.mx-gridsection` (the grid's card-section) —
so the rules are written once (`body.matrix-wide .mx-pane …`) and the Everything matrix
and the by-day matrix get identical layout.

The grid (`renderMatrix`) is fed by `gui_api.matrix_info` (a pure-filesystem
snapshot). **7 rows** (every report — Ramp Summary/Detail, Highway Sequence, both
Highway Log formats, Intersection Summary/Detail — all with cross-env AND vs-TSN as of
v0.17.0); each **row header** carries the
report name (evidence-supported rows append a small **camera badge**, v0.24.0 —
`evidenceRowBadge`: only the PDF-edition rows carry one since the 2026-08-05
ruling — four at first, FIVE since v0.37.0 when Highway Detail (PDF) joined on the
pre-release freeze lifting (vs-TSN only; it has no env hooks, so the env lane stays
at four); every other row gets no
badge, the toggle's status lines name them), a per-row **comparison-mode select**
(compact + content-sized in a
`.mx-fluent-select` chevron wrapper; the "(soon)" greying is now defensive — every
mode is coded), a vs-TSN
**file picker** when in a TSN mode — a **status-dot chip** (`.mxtp-file`) that surfaces
the active TSN file (green dot = file ready / amber = dropped PDFs need consolidating /
grey = none) over compact Choose / Consolidate / Clear buttons — and a **per-row
refresh**; each **column header** has a **per-column refresh**. Refreshes are polished
**ghost icon-buttons** (`.mxch-refresh`) and the header **baseline picker** is a
light-surface `select-light` (not the dark title-bar skin). Each cell renders the unified `cmp` state — **discrepancy count,
colour-coded** (`.mx-match`/`.mx-diff-lo`/`.mx-diff-hi`/`.mx-stale`/`.mx-missing`/`.mx-na`)
plus greyed / needs-export / needs-TSN / "consolidate N PDFs" / stale states — with
compact **icon** actions (`↻ export` / `↻ compare` / `↗ open`, gated on support+built; since
v0.23.0 a **camera** on built, FRESH cells — the on-demand evidence run for the existing
comparison, offered ONLY on the tsn/env modes of the PDF-edition rows since the
2026-08-05 ruling — five rows on the tsn mode as of v0.37.0 (Highway Detail (PDF)
joined), four on env; a missing TSN print set reports per cell at run time).
The **config zone** (`#matrixConfig`, a card under the slim activity log, shown via
`body.matrix-wide:not(.mw-day)`) holds the report + **environment-column** show/hide toggles,
the global "set all comparisons to…" (env|tsn), the live-formulas toggle, the **evidence-images
toggle + per-column count** (`#matrixEvidence` / `#matrixEvidenceCount` — ONE shared persisted
pair `evidence_images`/`evidence_examples` mirrored on the by-day corner, synced by
`syncMatrixEvidence` off the state's `evidence` block; greyed only when NO report is ready.
Since v0.24.0 the hint is an always-visible **status block** (`.ev-status-line`); the
2026-08-05 amendment re-truthed it to the print-crop rule: one ✓/○ line PER supported
PDF-edition family (✓ with its TSN print count when the prints are dropped, ○ naming
the drop folder when not), one ✓ line for the four cross-environment PDF-vs-PDF cells
(both environments' own prints), and one "No evidence: …" line naming every other row
(the state's `evidence.unsupported`, one entry per row, derived server-side from
`matrix_rows()` × `visual_evidence.capable`/`env_capable` — evidence exists only for
the PDF-edition families, so an Excel row is listed even when its PDF sibling is
supported) — so the toggle is never a mystery switch —
[comparison-engine.md](comparison-engine.md) §13), the live
queue, and the **fast-mode browser-count spinner** (`#matrixWorkers`, the `.mc-workers` row): it writes the
shared `fast_workers` setting via `set_setting`, so the matrix corner, the Export pane
(`#fastWorkers`) and the Settings tab (`#setFastWorkers`) stay on one value; `syncMatrixFast`
reflects it (and greys the row when fast mode is off). A baseline `<select>` (switch → confirm →
`set_matrix_baseline` + `recompute_matrix("all")`), Refresh-stale (also the **resume**
after a **Cancel**), Open-comparisons-folder, and a Cancel button live in the actions
row. `updateMatrixProgress()` greys all matrix controls live + toggles the Cancel
button; the grid re-renders on `run_ended` / `matrix_refresh`. The mock returns the
full multi-mode snapshot (modes, row_modes, all_envs, hidden_envs, tsn_meta) + every
new bridge method, exercising all states at `/index.html#mock`. Engine + bridge:
[comparison-engine.md](comparison-engine.md) §12. **Headless caveat:** the `#mock`
reports viewport width 0 until `preview_resize`d and won't tick transitions — verify
the wide layout end-state via DOM measurement.

### The matrix job queue + fast mode + row/col buttons (v0.16.0)

Matrix actions no longer claim the single-task gate directly — they **enqueue a
Job** and the queue runs one at a time. The queue lives in `gui_api`: `self._queue`
(deque) + `self._current_job` + `self._job_seq`; `_enqueue_matrix_job` →
`_try_start_next_matrix_job` (claims the gate AND `popleft`s **atomically** under the
lock, then `_dispatch_matrix_job` resolves targets with the lock released — returns
False ⇒ drop the no-work job + try the next). `_end_task` clears `_current_job` and
auto-advances; an error that ends a matrix job (`_on_error`, auth or browser) clears
the pending queue so it can't cascade. **Targets resolve at START, not enqueue**
(`_resolve_compare_cells` / `_resolve_export_steps`), so a job reflects exports done
before it. Snapshot keys: `matrix_queue`, `matrix_current`, `matrix_fast`. New bridge:
`refresh_row_export`/`refresh_column_export`, `set_matrix_fast`,
`matrix_queue_remove|move|clear`, `matrix_stop_all`. Worker: `MatrixBatchExportWorker`
(manifest-free, `workers=N` ⇒ fast). UI: each row/column header has a **two-button
group** (`mxHeaderBtns`: ↻ `i-refresh` re-export + ⟳ `i-compare` rebuild), a Fast
toggle + a live queue panel (`renderQueuePanel` / `mxQueueRow`) in the config zone;
action triggers stay LIVE mid-run (a 2nd click queues) — only selection controls grey.

### The Compare-tab "vs TSN Matrix" (v0.16.0; renamed + generalized v0.16.1)

A second matrix under the **Compare** tab — sub-tab label **"vs TSN Matrix"** (internal
group id stays `tsn_by_day`), appended after the registry `compare_groups`: rows = **every
report type** (HL Excel + PDF, Ramp Summary/Detail, Highway Sequence, Intersection
Summary/Detail — all wired as of v0.17.0), columns = exported **days** you add, each cell = (report, day)
**vs TSN**. ONE source selector (default ssor-prod); no cross-env, no live re-export.
`selectCompareGroup("tsn_by_day")` swaps `#compareClassic` out for `#dayMatrixSection` and
calls `applyMatrixWide()` so it goes **full-width too** (same treatment as the Everything
matrix); `renderDayMatrix` is fed by `gui_api.day_matrix_info`. It **shares** the
TSN-picker component (`mxTsnPicker`, rendered PER ROW — named by its report, like
the Everything matrix), the cell vocab
(`mxCellContent`/`mxActBtn`), and the SAME job queue (the queue panel renders in both
places); day compare Jobs carry `which:"day"` and route to `DayMatrixCompareWorker`.
**Its own config corner** (`#dayMatrixConfig`, shown via `body.matrix-wide.mw-day`) mirrors
`#matrixConfig` and holds the by-day matrix's granular controls — the queue, the **Day
columns** add-day toolbar, a **live-formulas** toggle, and the **Reports** show/hide
toggles (the per-report **TSN dataset** pickers moved to the row headers) — all relocated
out of the grid section so the grid area is as
lean as the Everything matrix's (fits ~5 rows at 1440×720 without scrolling). The by-day
live-formulas toggle is its **own** setting (`day_matrix_formulas`, snapshot key + bridge
`set_day_matrix_formulas`, synced by `syncDayMatrixFormulas`) — independent of the Everything
matrix's `matrix_formulas`; the **evidence-images pair** (`#dayMatrixEvidence` +
`#dayMatrixEvidenceCount`, `syncDayMatrixEvidence`) is by contrast the SAME shared setting as
the Everything matrix's. Engine + store: [comparison-engine.md](comparison-engine.md) §12.
Mock + bridge exercised at `/index.html#mock` (Compare ▸ vs TSN Matrix).

**The add-day picker names what each day holds** (2026-09-02, all three day matrices). A
run folder exists as soon as ANY report was pulled that day, so a bare date in the picker
read like a full export when it might hold one Ramp Summary. Every option now reads
`2026-08-31  ·  HL HSL RD` — the catalog's short codes (`report_catalog.short_code`, one
per export key, asserted unique at import) of the reports actually exported that day for
THIS matrix, in row order, from the snapshot's `available_day_reports` (each matrix module's
`available_day_reports(source)` over the ONE shared walk, `artifact_store.exported_subdirs_by_day`,
which applies the same real-export-file test as `available_days`, so a day is offered exactly
when it carries at least one tag). An export-less today says `today — nothing exported yet`;
the PDF-vs-Excel picker tags a family with both editions `HL` and a one-edition family
`HL:xlsx` / `HL:pdf` (a cell it cannot build). One renderer, `mxDayOptionText`, serves the
three pickers; an older bridge without the map falls back to the bare date.

### The Compare-tab "vs Baseline Matrix" (v0.26.0)

A **third** matrix sub-tab under Compare (group id `baseline_by_day`, appended beside
"vs TSN Matrix"): rows = the same 12 report types, columns = exported **days** you add,
each cell = (report, day) **vs a picked baseline** — an earlier day, or the
Export-Everything store, for the same source. Same-format on both sides by construction;
**compare-only** (no export actions, no TSN pickers, no consolidated badges, no evidence
cameras — `compare_folders` reads the per-route files straight from both folders).
`selectCompareGroup("baseline_by_day")` swaps in `#baselineMatrixSection`, full-width via
`body.matrix-wide.mw-bl`; `renderBaselineMatrix` is fed by `gui_api.baseline_matrix_info`.
The **Source + Baseline selects** live in the section head — the baseline picker lists the
store + every exported day with its report coverage ("2026-06-11 (9/13 reports)"), the
per-report half renders as the cells' "baseline not exported" state, and the baseline's own
day column renders "baseline" cells (highlighted `.mx-baseline-col`, not rebuildable). Its
config corner (`#baselineMatrixConfig`) holds the shared queue panel, the add-day toolbar,
its OWN live-formulas toggle (`baseline_matrix_formulas`, `syncBaselineMatrixFormulas`) and
the report toggles. Jobs carry `which:"baseline"` → `BaselineMatrixCompareWorker` on the
same queue. Engine + store: [comparison-engine.md](comparison-engine.md) §12c.
Mock + bridge exercised at `/index.html#mock` (Compare ▸ vs Baseline Matrix).

### The Compare-tab "PDF vs Excel Matrix" (v0.31.0)

The **fourth** matrix, and the only one whose two sides come from the *same* run
folder: the 5 dual-edition families × exported days, each cell self-checking that
day's PDF export against its Excel export. It was built ON the
`report_catalog.MATRIX` wiring the same day that wiring landed, which is what
proved the wiring — a new matrix cost a table row per report instead of a fifth
if-chain. Lives in `pdf_excel_matrix.py`; the sub-tab renders through the same
`ui-matrix.js` as the other three.

### The ArcGIS tab (v0.29.0; two sub-tabs since v0.39.0)

The one tab that never touches the TSMIS site. Both sub-tabs build from the
manually-stocked `arcgis_layers/` library, and both are ordinary
build-then-compare flows driven from `gui_arcgis_api.py` (`arcgis_status` /
`start_arcgis_build` / `start_arcgis_compare`, and the `*_report_*` mirrors) with
`ui-arcgis.js` as their renderer:

- **Clean Road** — builds our own CA HIGHWAYS table from the layers as-of a chosen
  date and compares it against the TSN extract, both flavors. The as-of box
  matters: `resolve_default_asof()` takes its default from the *staged TSN
  extract*, not from the layer library, so a build off fresh layers still
  reconstructs the extract's date unless you set it.
- **Reports vs layers** — renders a TSMIS *report* from the same layers and diffs
  it against the app's own export of that report (Highway Detail first). Because
  both sides are TSMIS, they should agree; the card leads with the **vintage**
  warning in warning colour, because an as-of that doesn't match the compared
  export's day measures network change instead of correctness.

Statewide runs here are long (~25–30 min for a report build), so both flows are
cancellable and report progress through the same `Events` sink as an export.

**Extending it** (roadmap G1 adds the CA INTERSECTIONS and CA RAMPS builds) is a
new build + comparator behind the existing endpoint shape — read
[planning/cleanroad-highways.md](planning/cleanroad-highways.md) first for the
measured build rules, and don't re-derive them.

### Matrix cell states, and the one that is deliberately not green

`ui-matrix.js` renders a cell from `cmp` state. Beyond the familiar built /
stale / match / failed states, v0.41.0 added **`mx-preview`**: a counts-only
result showing the difference count in grey with *"counts only — build to
certify"*. It is checked BEFORE the built/stale/match branches and can never
render as `mx-match` — a zero-difference preview reads `match*`, never a green
tick. That is enforced structurally rather than by convention (see
[comparison-engine.md](comparison-engine.md) §2c) and asserted by
`build/check_comparison_preview.py`, which reads this file to prove the branch
order and the absence of `mx-match`. **If you reorder the branches in
`ui-matrix.js`, that check fails — which is the point.**

v0.41.2 added one sub-state inside that branch. A counts-only run writes no
file, so a stale cell's existing workbook is untouched; when the preview
re-derives that workbook's own published counts, the cell reads **"counts
confirmed"** — the same `mx-preview` class plus an `mx-confirmed` accent class
(success-coloured left edge + sub-line, muted background and italic number
unchanged). It answers the only question a stale cell raises — *do the saved
numbers still hold?* — without claiming the file itself is current, because
equal totals don't mean equal rows. Same rule as the parent state: accent, never
promotion, and `confirms` never reaches `_staleness`.

The toggle behind all of this is the counts-only checkbox in each matrix's
config zone. It has its OWN bridge endpoint (`set_matrix_preview_only`), like
every other matrix toggle, because `matrix_preview_only` is a stored-only-when-on
flag outside `settings.DEFAULTS` — the generic `set_setting` drops keys it
doesn't know. It shipped wired to `set_setting` in v0.41.0 and so clicked,
reported success, saved nothing, and snapped back on the next state sync
(fixed v0.41.2). `set_setting` now REFUSES an unknown key instead of returning
`ok`, and `check_ui_contract` asserts both that every `set_setting` key in the
UI is a real DEFAULTS key and that this toggle calls its own endpoint.

### One-stop EXPORT on the by-day matrix (v0.17.0)

The by-day matrix is the **export + consolidate + compare-vs-TSN** home for
individually-pulled days (the Everything matrix stays the always-current health view).
**"Export today →"** (footer, accent) — or the today **column-header ↻**, a **row ↻**, or
a **today cell's ↻** — pulls a fresh **dated run folder** `output/<today> <src-env>/` for
the matrix source, then auto-chains the consolidate + compare so the new column **fills
itself**. **Only today is exportable**: `day_matrix_snapshot.today` gates every export
control (past columns show no export action — their pull stays the immutable record handed
to the vendor; you can still rebuild/compare them). Plumbing: `export_day_column/row/cell`
→ a `which:"day"` **export** Job → `MatrixBatchExportWorker(dated=True)` (the
`_run_matrix_export_step(dated=True)` writes the dated folder via `out_base=None`, site set
to the matrix source like `BatchWorker`); on `matrix_export_done` for a day job,
`_on_matrix_export_done` enqueues the matching **compare** Job (skipped on cancel). Fast
mode + worker count reuse the **shared** `matrix_fast`/`fast_workers` knob (the by-day
corner's `#dayMatrixFast`/`#dayMatrixWorkers` stay in sync with the Everything matrix /
Export pane / Settings via `syncDayMatrixFast`); **pause/resume + skip** (`#btnDayPause`/
`#btnDaySkip`, shown while a `which:"day"` export runs) forward to the engine like a normal
export. Foundation note: a future **district-wide** pull (TSN HL/HSL are per-district) would
widen `_resolve_day_export_steps` to per-district steps — the dated/site/queue machinery
already fits. Golden `check_day_matrix` (today-gating, dated worker, export→compare chain);
mock + bridge at `/index.html#mock`.

### Env-check flags on the matrices (v0.17.0)

Both matrices reuse the Export tab's amber convention to surface what the **env-access**
scan flagged. `applyMatrixEnvFlags()` (app.js) overlays `S.st.env_access` (keyed
`"<src>-<env>"` → `reports[<registry label>]` = `ok|greyed|missing`) onto the
already-rendered grid — cheap class/tooltip toggles over cells/headers stamped with
`data-rk`/`data-env`/`data-label`, so it re-runs on any state push without a rebuild.
The **Everything** matrix is report×env, so it flags precisely: the **cell** (amber inset
border + "export may fail" tooltip), its **row header** (amber when flagged in any shown
env), and the **env column header** (`mx-env-warn` amber / `mx-env-bad` red for a
whole-env verdict). The **by-day** matrix is report×day under one `snap.source` env, so it
flags the **row header**. It re-overlays live from `dispatch`'s `state` case (when a matrix
tab is visible) and on `matrix_refresh`, so the quiet background active-env check (auth
§4a) keeps the flags current. The lookup works because the matrix `row_labels` ARE the
EXPORT_REPORTS labels (`reports.matrix_rows()` → `EXPORT_REPORTS[idx][0]`) — exactly the
`env_access.reports` key. Verified at `/index.html#mock` (seeded `env_access`).

### Export-browser indicator + quiet active-env check (v0.17.0)

The title-bar **Browser dropdown is gone**, replaced by a read-only **indicator**
(`#exportBrowserInd`, fed by `state.export_browser` = `{normal, fast, dot, cls_label}` from
`_export_browser_view`) of what will actually export — e.g. "Google Chrome · saved login"
or "Microsoft Edge · one-click". The only real choice — **Built-in Chromium vs installed
Chrome** — moved to **Settings ▸ Export browser** (`renderExportBrowser`: radios when both
exist, else an info line), persisted via `set_export_browser`; Edge is the implicit
one-click path, not pickable. On app start + env switch the GUI quietly proves one-click
and refreshes the active env's report flags via the background **active-env check** — full
detail in [auth-and-signin.md](auth-and-signin.md) §4 / §4a. **Title-bar vs card trap
applies:** the indicator uses `--titlebar-*` tokens (`.tb-ind`), the Settings radios are
card controls.

### Drag-to-reorder matrix rows + columns (v0.17.0 Phase 4b)

Each row/column header carries a small drag grip (`dndAttach` in app.js — one HTML5-DnD
helper shared by both matrices). Dropping reorders: the new key order is persisted via the
bridge (`set_matrix_row_order` / `set_matrix_env_order` / `set_day_matrix_row_order` →
`settings.{matrix_row_order,matrix_env_order,day_matrix_row_order}`) and re-rendered. The
**backend applies the order** — `matrix.apply_order(keys, order)` treats the saved list as a
sort key over the ACTUAL visible rows/columns (named keys first, then the rest in natural
order), so it's a pure display preference: unknown/stale keys are ignored, a report/env/day
added or removed later degrades gracefully, and a hidden row is never resurrected by the order
list. The drop indicator (`--primary` edge via `.dnd-before-/.dnd-after-{x,y}`) shows the
insert point. Verified at `/index.html#mock` (synthetic drag on both matrices, rows + env
columns, persistence across re-render) + golden `check_matrix.test_reorder` /
`check_matrix_bridge` (bridge round-trip).

### Settings ▸ TSN reports panel (v0.17.0)

The canonical TSN library ([comparison-engine.md](comparison-engine.md) / `tsn_library.py`) gets a
status panel in Settings (`#setTsnLibrary`, rendered by `renderTsnLibrary` from
`get_settings().tsn_library`). A header line shows the **on-disk folder** (`tsn_library_root`
= `paths.TSN_LIBRARY_ROOT`; each report keeps its raw + consolidated files in a `<report>`
subfolder) with an **Open folder** button (`open_tsn_library_folder` → `_open_folder`); each
row's name tooltips that report's `raw_dir`. The library is **self-documenting**:
`tsn_library.ensure_layout()` seeds every report's `<report>/raw/` folder with a hint file
naming the expected format, plus a root README — run at GUI start AND before Open folder, so a
fresh install never shows an empty folder (v0.17.1). The matrix **Choose…** picker
(`pick_matrix_tsn_file`) also defaults its dialog into that report's library folder, not the
legacy per-run `_tsn_input/` location. Then one row per registered report: a **dot** (green = consolidated
current · amber = missing/stale-or-raw-not-yet-built · grey = no raw imported), a status line
(`N raw <kind> · consolidated current|STALE|not yet built`), and two actions —
**Import raw…** (`import_tsn_raw`: a native multi-file dialog, PDFs or the statewide workbook
per the report's `raw_kind`, copied into the library via `tsn_library.import_raw`) and
**Rebuild** (`rebuild_tsn_library`: builds the consolidated/normalized workbook via
`tsn_library.build_consolidated(force=True)` on the shared single-task slot, reusing
`ConsolidateWorker`). The bridge methods refresh the panel: Import returns the fresh rows;
Rebuild sets `S._tsnRebuildPending` and the `"state"` handler re-fetches `tsn_library_status()`
once the task slot frees. Mock + bridge exercised at `/index.html#mock` (Settings ▸ TSN reports)
and golden `check_gui_bridge.test_tsn_library_panel`.

## Motion layer + control polish

A light app-wide motion system (end of `app.css`, `prefers-reduced-motion`-aware),
driven by a **motion-token scale** in `:root`: `--motion-instant` (80ms `:active`
press), `--motion-fast` (120ms hover/colour), `--motion` (180ms entrances + list
inserts), `--motion-slow` (240ms panes), `--motion-theme` (500ms theme fade), plus
`--ease-out` / `--ease-pop`. Entrances: tab panes rise+fade (`pane-in`), sub-panes
cross-fade, popovers/modals `pop-in`/`modal-in`, and per-element inserts for
**activity-log lines** (`line-in`), the **env stepper** + **worker rows** (`rise-in`),
**saved-report rows**, and the preflight↔progress↔completion **lifecycle cards**.
Buttons/tabs have a tactile `:active` press; the theme toggle runs a **slower
light↔dark cross-fade** — `app.js withThemeTransition()` adds `html.theme-anim` for the
change window, and the `@media (prefers-reduced-motion)` block **re-overrides that
`!important` transition** so reduced-motion still snaps (and zeroes transform-on-hover
end-states the duration clamp alone can't).

**Control-polish conventions** (the matrix controls set the bar; the rest of the app
matches it — keep it that way): tints are always
`color-mix(in oklab, var(--token) N%, <surface>)`, never hardcoded literals; focus is a
2px `var(--ring)` ring on inset/ghost controls, while the filled `.btn` keeps its
offset **double-ring** so focus stays visible on a primary fill; compact-control
heights come from `--control-h-sm`/`--control-h-md`. **Title-bar vs card trap:**
title-bar controls (`.tb-select`, `.btn-icon`, `.btn-titlebar`, `.status-chip`) MUST
keep `--titlebar-*` tokens + faint white fills; card controls (`select-light`, the
matrix controls, `.btn-*` on cards) use `--card`/`--foreground`/`--input-border` — a
card skin on the dark bar (or the bar skin on a light card) goes invisible.

NOTE: the `#mock` is rendered headless, which does not advance CSS transitions — verify
motion *end-states* + that the rules apply (animation-name / computed values), and watch
the actual motion in the real WebView2 window.

## Related GUI behaviors (owned elsewhere)

- **Run lifecycle / completion summary / ETA / progress hierarchy / Export Everything stepper** (v0.13.0): `gui_api._build_export_summary`, `_on_batch_progress`, `app.js renderPreflight`/`updateActivityCards`/`updateEta`/`syncBatchHeadline`/`renderBatchSteps`. See [engine-and-reliability.md](engine-and-reliability.md).
- **Live browser status + Preview screenshots** (`request_screenshot` → `common.maybe_screenshot` → `("preview_shot", …)` modal, URL fragment stripped by `page_url_for_display`): [engine-and-reliability.md](engine-and-reliability.md), [auth-and-signin.md](auth-and-signin.md).
- **Settings tab, env-access scan, Verify env, Delete all reports, Built-in Chromium download:** [engine-and-reliability.md](engine-and-reliability.md), [auth-and-signin.md](auth-and-signin.md), [it-and-security.md](it-and-security.md).
- **One-click update / revert title-bar pill** (`_on_update_status`, `update_start`/`update_apply`/`revert_to_previous`): full pipeline in [build-and-release.md](build-and-release.md).
- **The two sign-in title-bar chips** (`_login_states()` → Saved login + Edge one-click): [auth-and-signin.md](auth-and-signin.md).
