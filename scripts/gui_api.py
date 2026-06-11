"""Python side of the TSMIS Exporter GUI (pywebview / Edge WebView2).

The window is a WebView rendering scripts/ui/ (plain HTML/CSS/JS); this module
is everything behind it:

  * GuiApi -- the js_api bridge. Every public method here is callable from
    JS as `window.pywebview.api.<name>(...)`. Methods validate, mutate the
    small GUI state, and start the SAME worker threads the Tk GUI used
    (gui_worker.py is unchanged) -- the engines stay console-free behind the
    Events seam.
  * the worker-queue pump -- translates gui_worker's (kind, payload) messages
    into JSON events pushed to JS via evaluate_js, mirroring the old
    gui_app._handle() state machine.
  * run() -- creates the window and starts the webview loop (called by
    gui_main.main()).

Threading: js_api calls arrive on pywebview bridge threads, workers post to
self._q from their own threads, and a sender thread serializes EVERYTHING
going to JS through one ordered queue -- so log lines, progress and state
snapshots can never interleave out of order. State mutations take self._lock.

The tsmis.ui logging contract from the Tk GUI carries over: every line shown
in the log pane is mirrored to the `tsmis.ui` logger, every user decision and
every swallowed exception is logged with its reason.
"""
import ctypes
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue

import webview

import run_report
from gui_worker import CheckWorker, ConsolidateWorker, ExportWorker, LoginWorker
from exporter_parallel import DEFAULT_WORKERS, MAX_WORKERS

from paths import LOG_DIR, OUTPUT_ROOT, WEBVIEW_PROFILE_DIR, list_output_days
from version import APP_NAME, __version__
from common import (
    BROWSER_CHANNELS, CHANNEL_LABELS, DATA_SOURCES, DATA_SOURCE_LABELS,
    ENVIRONMENTS, ENVIRONMENT_LABELS, ROUTES, AuthError, clear_auth, get_site,
    parse_routes, require_valid_auth, set_preferred_channel, set_site,
)
from reports import EXPORT_REPORTS, CONSOLIDATE_REPORTS

log = logging.getLogger("tsmis.gui")
# Everything shown in the GUI's log pane is mirrored here, so tsmis.log
# carries the user's view of a run alongside the engine's own diagnostics.
ui_log = logging.getLogger("tsmis.ui")

_CHANNEL_SHORT = {"chromium": "Chromium", "msedge": "Edge", "chrome": "Chrome"}
_SHUTDOWN = object()


def _app_icon_path():
    """Path to the bundled app icon (.ico), or None. Frozen: bundled into
    _internal via sys._MEIPASS; in dev it's build/app.ico. Best-effort -- a
    missing icon must never stop the GUI from launching."""
    base = getattr(sys, "_MEIPASS", None)
    candidates = []
    if base:
        candidates.append(Path(base) / "app.ico")
    candidates.append(Path(__file__).resolve().parent.parent / "build" / "app.ico")
    return next((c for c in candidates if c.exists()), None)


def _ui_index_path():
    """Path to the UI entry html. Frozen: bundled as _internal/ui/; dev:
    scripts/ui/."""
    base = getattr(sys, "_MEIPASS", None)
    if base and (Path(base) / "ui" / "index.html").exists():
        return Path(base) / "ui" / "index.html"
    return Path(__file__).resolve().parent / "ui" / "index.html"


def _api_method(fn):
    """Wrap a js_api method: an uncaught exception in a windowed .exe would
    vanish (no stderr) and leave the UI hanging on a dead Promise, so log the
    full traceback and hand JS a structured error instead."""
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            logging.getLogger("tsmis.crash").critical(
                "uncaught exception in GUI api %s", fn.__name__, exc_info=True)
            try:
                self._emit_log(f"ERROR: {type(e).__name__}: {e} (details in the log file)")
            except Exception:
                pass
            return {"error": f"{type(e).__name__}: {e} (details are in the log file)"}
    wrapper.__name__ = fn.__name__
    return wrapper


class GuiApi:
    """State + bridge behind the WebView UI. Public methods = the JS api."""

    def __init__(self):
        self._window = None
        self._lock = threading.RLock()
        self._q = Queue()            # worker -> GUI messages (gui_worker protocol)
        self._out = Queue()          # GUI -> JS events (ordered)
        self._ready = threading.Event()      # JS finished its first render
        self._started = False        # first get_initial_state happened

        self._task = None            # None | "export" | "consolidate" | "login"
        self._fast_run = False       # running export is fast mode (Skip is off)
        self._authed = False
        self._device_ok = False      # silent device sign-in proven to work
        self._login_phase = None     # None|starting|open|saving|cancelling
        self._auth_dot = "unknown"
        self._auth_text = "Checking session…"
        self._channel = BROWSER_CHANNELS[0]  # the dropdown's current pick
        self._checks_running = False
        self._checks = {}
        for ch in BROWSER_CHANNELS:
            self._checks[f"browser_{ch}"] = {"status": "busy",
                                             "text": f"{CHANNEL_LABELS[ch]}: checking…"}
        self._checks["output"] = {"status": "busy", "text": "Output folder: checking…"}
        self._checks["tools"] = {"status": "busy", "text": "Report tools: checking…"}

        self._last_results = []      # [(spec, RunResult), ...] of the last export
        self.cancel_event = threading.Event()
        self.skip_event = threading.Event()
        self.login_done = threading.Event()
        self.login_cancel = threading.Event()

        threading.Thread(target=self._worker_pump, daemon=True, name="gui-pump").start()
        threading.Thread(target=self._sender, daemon=True, name="gui-send").start()

    # ---- plumbing: Python -> JS ---------------------------------------------

    def attach(self, window):
        self._window = window
        # NOTE: no 'shown' handler on purpose. pywebview fires window events on
        # the WinForms STA thread while WebView2 is still initializing on it;
        # a Python callback there (the original icon-setting handler loaded a
        # .NET assembly) can starve the message pump mid-init and deadlock the
        # window ("Not responding" before the page ever loads). The icon is
        # applied from a plain worker thread instead, and 'closed' only fires
        # at teardown, after the message loop is done.
        window.events.closed += self._on_closed
        threading.Thread(target=self._set_window_icon_late, daemon=True,
                         name="gui-icon").start()

    def _emit(self, event):
        self._out.put(event)

    def _emit_log(self, text):
        if text.strip():                     # skip the pane's blank spacer lines
            ui_log.info("%s", text)
        self._emit({"t": "log", "text": text})

    def _emit_modal(self, kind, title, message):
        ui_log.info("dialog (%s) %s: %s", kind, title, message)
        self._emit({"t": "modal", "kind": kind, "title": title, "message": message})

    def _state_snapshot(self):
        with self._lock:
            return {
                "task": self._task,
                "fast_run": self._fast_run,
                "authed": self._authed,
                "device_ok": self._device_ok,
                "auth_dot": self._auth_dot,
                "auth_text": self._auth_text,
                "login_phase": self._login_phase,
                "login_label": "Re-login" if self._authed else "Log in",
                "checks": {k: dict(v) for k, v in self._checks.items()},
                "checks_running": self._checks_running,
                "days": list_output_days(),
                "can_save_report": bool(self._last_results),
            }

    def _push_state(self):
        self._emit({"t": "state", "s": self._state_snapshot()})

    def _sender(self):
        """Single ordered path to JS: batch whatever is queued and dispatch."""
        self._ready.wait()
        while True:
            ev = self._out.get()
            if ev is _SHUTDOWN:
                return
            batch = [ev]
            try:
                while len(batch) < 200:
                    nxt = self._out.get_nowait()
                    if nxt is _SHUTDOWN:
                        return
                    batch.append(nxt)
            except Empty:
                pass
            try:
                # default=str: a future non-JSON payload (e.g. a Path) must
                # degrade to a string, not silently kill the whole batch.
                self._window.evaluate_js(
                    "window.__tsmis && window.__tsmis.dispatch(%s)"
                    % json.dumps(batch, default=str))
            except Exception as e:
                # Window torn down mid-run is the normal cause; the file log
                # still has everything, so just note it and keep draining.
                log.info("sender: evaluate_js failed (%s: %s)", type(e).__name__, e)

    # ---- window lifecycle ----------------------------------------------------

    def _set_window_icon_late(self):
        """Give the window the app icon (the packaged exe icon does not
        transfer to the runtime window by itself). Pure ctypes/Win32 from a
        worker thread -- no CLR, nothing runs on the GUI thread; SendMessage
        marshals WM_SETICON safely. Best-effort: a missing icon must never
        affect the app."""
        try:
            ico = _app_icon_path()
            if not ico:
                return
            u32 = ctypes.windll.user32
            hwnd = 0
            deadline = time.monotonic() + 20            # window appears ~1-2s in
            while time.monotonic() < deadline and not hwnd:
                hwnd = u32.FindWindowW(None, APP_NAME)
                if not hwnd:
                    time.sleep(0.5)
            if not hwnd:
                log.info("window icon not set (window %r not found)", APP_NAME)
                return
            LR_LOADFROMFILE, IMAGE_ICON, WM_SETICON = 0x10, 1, 0x80
            for which, size in ((0, 16), (1, 32)):      # ICON_SMALL, ICON_BIG
                hicon = u32.LoadImageW(None, str(ico), IMAGE_ICON, size, size,
                                       LR_LOADFROMFILE)
                if hicon:
                    u32.SendMessageW(hwnd, WM_SETICON, which, hicon)
        except Exception as e:
            log.info("window icon not set (%s: %s)", type(e).__name__, e)

    def _on_closed(self):
        # Unblock any worker so it can exit cleanly (same as the Tk _on_close).
        ui_log.info("window closed by user%s",
                    f" (task {self._task!r} still running)" if self._task else "")
        self.cancel_event.set()
        self.login_cancel.set()
        self.login_done.set()
        self._out.put(_SHUTDOWN)
        self._ready.set()                    # never leave the sender parked

    # ---- auth status ----------------------------------------------------------

    def _refresh_auth(self):
        with self._lock:
            try:
                require_valid_auth()
                self._authed = True
                self._auth_dot, self._auth_text = "ok", "Session ready"
            except AuthError:
                self._authed = False
                if self._device_ok:
                    # No saved file, but this PC signs exports in by itself
                    # (device sign-in mode) -- a ready state, not a problem.
                    self._auth_dot = "ok"
                    self._auth_text = "Automatic sign-in ready (no saved login needed)"
                else:
                    self._auth_dot, self._auth_text = "bad", "No saved login — click Log in"

    def _set_dot(self, state, text):
        with self._lock:
            self._auth_dot, self._auth_text = state, text

    # ---- worker-queue pump (the old gui_app._handle state machine) ------------

    def _worker_pump(self):
        while True:
            kind, payload = self._q.get()
            try:
                self._handle(kind, payload)
            except Exception:
                logging.getLogger("tsmis.crash").critical(
                    "uncaught exception handling worker message %r", kind, exc_info=True)

    def _handle(self, kind, payload):
        if kind == "log":
            self._emit_log(payload)
        elif kind == "progress":
            self._emit({"t": "progress", "p": payload})
        elif kind == "export_done":
            self._finish_export(payload)
        elif kind == "export_partial":
            # A multi-report run errored partway; keep the completed reports so
            # "Save run report…" still covers them. The "error" message that
            # follows resets the run state.
            with self._lock:
                self._last_results = payload
        elif kind == "consolidate_done":
            self._finish_consolidate(payload)
        elif kind == "login_open":
            with self._lock:
                self._login_phase = "open"
            self._set_dot("busy", "Waiting — finish sign-in in the browser")
            self._emit_log("Browser opened. Complete sign-in (SSO + MFA), then click "
                           "‘I've finished logging in’.")
            self._push_state()
        elif kind == "login_saved":
            self._emit_log("Session saved.")
            self._refresh_auth()
            self._end_task()
        elif kind == "login_device_ok":
            # Silent device sign-in works, but the session is device-bound so no
            # file was saved (and none is needed): each export signs itself in.
            with self._lock:
                self._device_ok = True
            self._emit_log("This PC signs in automatically (Microsoft Edge + your "
                           "Windows account). Nothing to save — exports will sign "
                           "themselves in.")
            self._refresh_auth()
            self._end_task()
        elif kind == "login_failed":
            self._emit_log("Login wasn't completed — no new session was saved.")
            self._emit_modal(
                "info", "Login not completed",
                "It doesn't look like you finished signing in, so no session was saved.\n\n"
                "Click 'Log in' and complete sign-in until the TSMIS report page loads — "
                "then either click “I've finished logging in” or just close the "
                "browser window, and your session will be saved.")
            self._refresh_auth()
            self._end_task()
        elif kind == "check":
            key, status, text = payload
            with self._lock:
                if key in self._checks:
                    self._checks[key] = {"status": "ok" if status == "ok" else status, "text": text}
            self._push_state()
        elif kind == "checks_done":
            self._on_checks_done(payload)
        elif kind == "cancelled":
            self._emit_log("Cancelled.")
            self._set_dot("ok" if self._authed else "bad", "Idle")
            self._end_task()
        elif kind == "error":
            self._on_error(payload)

    def _end_task(self):
        with self._lock:
            self._task = None
            self._fast_run = False
            self._login_phase = None
        self._refresh_auth()
        self._emit({"t": "run_ended"})
        self._push_state()

    def _finish_export(self, results):
        # results is [(spec, RunResult), ...] -- one entry per report type run
        # (partial if cancelled before the later reports started).
        with self._lock:
            self._last_results = results
        self._emit_log("")
        if not results:
            self._emit_log("No reports completed.")
            self._end_task()
            return
        total_saved = total_failed = 0
        for spec, result in results:
            handled = (result.saved + len(result.exists) + len(result.empty)
                       + len(result.user_skipped) + len(result.failed))
            total_saved += result.saved
            total_failed += len(result.failed)
            prefix = f"{spec.label}: " if len(results) > 1 else "Done. "
            self._emit_log(f"{prefix}{handled} routes handled — saved {result.saved}, "
                           f"already had {len(result.exists)}, empty {len(result.empty)}, "
                           f"skipped {len(result.user_skipped)}, failed {len(result.failed)}.")
            if result.failed:
                self._emit_log(f"  Failed routes: {result.failed}")
            if result.report_path:
                self._emit_log(f"  Run report auto-saved: {result.report_path}")
        if len(results) > 1:
            self._emit_log(f"All reports done — total saved {total_saved}, "
                           f"total failed {total_failed}.")
        with self._lock:
            if not self._authed:
                self._device_ok = True   # the run signed itself in (device sign-in mode)
        self._end_task()

    def _finish_consolidate(self, result):
        if result.status == "ok":
            for line in result.summary_lines:
                self._emit_log(line)
            self._set_dot("ok" if self._authed else "bad", "Done")
        elif result.status == "cancelled":
            self._emit_log(result.message or "Cancelled.")
        else:
            self._emit_log(f"ERROR: {result.message}")
            self._emit_modal("error", "Consolidation failed", result.message)
        self._end_task()

    def _on_checks_done(self, results):
        with self._lock:
            self._checks_running = False
        # If the *selected* browser isn't usable, tell the user what will happen.
        usable = [c for c in BROWSER_CHANNELS if results.get(c) == "ok"]
        sel = self._channel
        if sel and results.get(sel) != "ok":
            if usable:
                self._emit_log(f"Note: {CHANNEL_LABELS[sel]} can't be used right now — "
                               f"exports will use {CHANNEL_LABELS[usable[0]]} instead.")
            else:
                self._emit_log("Warning: no usable web browser was found. Install Microsoft "
                               "Edge (or Google Chrome) before running an export.")
        self._push_state()

    def _on_error(self, payload):
        kind, message = payload
        self._emit_log(f"ERROR: {message}")
        if kind == "auth":
            clear_auth()
            with self._lock:
                self._authed = False
            self._set_dot("bad", "No saved login — click Log in")
            self._emit_modal("warning", "Login needed",
                             f"{message}\n\nClick 'Log in' to sign in again.")
        else:
            self._set_dot("bad", "Error")
            self._emit_modal("error", "Error",
                             f"{message}\n\nMore details are in the log file.")
        self._end_task()

    # ======================= JS-callable api methods ==========================

    @_api_method
    def get_initial_state(self):
        if not self._started:
            self._started = True
            self._refresh_auth()
            self._start_checks_locked()
        return {
            "app_name": APP_NAME,
            "version": __version__,
            "output_root": str(OUTPUT_ROOT),
            "log_dir": str(LOG_DIR),
            "reports": [{"label": label, "fmt": fmt} for label, fmt, _spec in EXPORT_REPORTS],
            "cons_reports": [label for label, _mod in CONSOLIDATE_REPORTS],
            "routes": list(ROUTES),
            "channels": [{"id": c, "label": CHANNEL_LABELS[c],
                          "short": _CHANNEL_SHORT.get(c, CHANNEL_LABELS[c])}
                         for c in BROWSER_CHANNELS],
            "channel": self._channel,
            "sources": [{"id": s, "label": DATA_SOURCE_LABELS[s]} for s in DATA_SOURCES],
            "envs": [{"id": e, "label": ENVIRONMENT_LABELS[e]} for e in ENVIRONMENTS],
            "site": dict(zip(("source", "environment"), get_site())),
            "fast": {"default": DEFAULT_WORKERS, "max": MAX_WORKERS},
            "state": self._state_snapshot(),
        }

    @_api_method
    def ui_ready(self):
        self._ready.set()
        log.info("ui ready (first render done)")
        return True

    @_api_method
    def ui_event(self, name):
        ui_log.info("ui: %s", name)
        return True

    @_api_method
    def log_js_error(self, message):
        logging.getLogger("tsmis.crash").error("uncaught JS error: %s", message)
        return True

    # ---- header controls -----------------------------------------------------

    @_api_method
    def set_browser(self, channel):
        if channel not in BROWSER_CHANNELS:
            return {"error": f"unknown browser channel: {channel}"}
        with self._lock:
            self._channel = channel
        set_preferred_channel(channel)       # tried first; the others stay fallbacks
        self._emit_log(f"Browser set to {CHANNEL_LABELS[channel]} "
                       "(the other is still used as a fallback if needed).")
        return {"ok": True}

    @_api_method
    def set_site(self, source, environment):
        set_site(source=source, environment=environment)
        src, env = get_site()
        self._emit_log(f"Site set to {DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]} "
                       "(used by the next sign-in or export).")
        return {"ok": True}

    def _start_checks_locked(self):
        with self._lock:
            self._checks_running = True
            for key, item in self._checks.items():
                self._checks[key] = {"status": "busy",
                                     "text": item["text"].split(":")[0] + ": checking…"}
        CheckWorker(self._q).start()

    @_api_method
    def start_checks(self):
        if self._task:                       # never probe mid export/login
            return {"error": "busy"}
        self._start_checks_locked()
        self._push_state()
        return {"ok": True}

    # ---- routes ---------------------------------------------------------------

    @_api_method
    def parse_routes_preview(self, raw):
        try:
            chosen = parse_routes(raw)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "count": len(chosen), "routes": chosen}

    # ---- export ----------------------------------------------------------------

    @_api_method
    def start_export(self, report_idxs, routes_text, fast, workers):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
        specs = [EXPORT_REPORTS[i][2] for i in report_idxs
                 if 0 <= i < len(EXPORT_REPORTS)]
        if not specs:
            return {"error": "Tick at least one report to export."}
        raw = (routes_text or "").strip()
        if raw:
            try:
                run_routes = parse_routes(raw)
            except ValueError as e:
                return {"error": f"{e}\n\nExample: 5, 99, 101"}
        else:
            run_routes = list(ROUTES)
        n_workers = 1
        if fast:
            try:
                n_workers = max(2, min(int(workers), MAX_WORKERS))
            except (TypeError, ValueError):
                n_workers = DEFAULT_WORKERS

        with self._lock:
            self._task = "export"
            self._fast_run = n_workers > 1
        self.cancel_event.clear()
        self.skip_event.clear()

        names = ", ".join(s.label for s in specs)
        msg = f"Starting export: {names}"
        if len(run_routes) != len(ROUTES):
            msg += f"   ·   {len(run_routes)} routes"
        if n_workers > 1:
            msg += f"   ·   FAST MODE ({n_workers} browsers)"
        self._emit_log(msg)
        self._set_dot("busy",
                      f"Exporting {len(specs)} report(s)…" if len(specs) > 1
                      else f"Exporting {specs[0].label}…")
        self._emit({"t": "run_started", "mode": "export", "label": "Working…"})
        self._push_state()
        ExportWorker(specs, self._q, self.cancel_event, self.skip_event,
                     workers=n_workers, routes=run_routes).start()
        return {"ok": True}

    @_api_method
    def skip_route(self):
        if self._task == "export":
            self.skip_event.set()
            self._emit_log("Skip requested — will move on once the current wait ends.")
        return {"ok": True}

    @_api_method
    def cancel_run(self):
        if self._task in ("export", "consolidate"):
            self.cancel_event.set()
            self._emit_log("Cancel requested…")
        return {"ok": True}

    # ---- login -----------------------------------------------------------------

    @_api_method
    def start_login(self):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            self._task = "login"
            self._login_phase = "starting"
        self.login_done.clear()
        self.login_cancel.clear()
        self._set_dot("busy", "Signing in…")
        self._emit_log("Starting sign-in…")
        self._push_state()
        LoginWorker(self._q, self.login_done, self.login_cancel).start()
        return {"ok": True}

    @_api_method
    def finish_login(self):
        with self._lock:
            self._login_phase = "saving"
        self.login_done.set()
        self._set_dot("busy", "Saving session…")
        self._push_state()
        return {"ok": True}

    @_api_method
    def cancel_login(self):
        with self._lock:
            self._login_phase = "cancelling"
        self.login_cancel.set()
        self.login_done.set()
        self._push_state()
        return {"ok": True}

    # ---- consolidate -------------------------------------------------------------

    @_api_method
    def consolidate_info(self, report_idx, day):
        _label, mod = CONSOLIDATE_REPORTS[int(report_idx)]
        out = mod.out_path_for(day or None)
        return {"dest_dir": str(out.parent), "out_path": str(out),
                "exists": out.exists()}

    @_api_method
    def decline_overwrite(self):
        self._emit_log("Consolidation cancelled (kept existing file).")
        return {"ok": True}

    @_api_method
    def start_consolidate(self, report_idx, day):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            self._task = "consolidate"
        day = day or None
        label, mod = CONSOLIDATE_REPORTS[int(report_idx)]
        self.cancel_event.clear()
        self._emit_log(f"Starting consolidation: {label}" + (f"   ·   {day}" if day else ""))
        self._set_dot("busy", f"Consolidating {label}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Consolidating {label}…"})
        self._push_state()
        # Overwrite was resolved by the UI before start (consolidate_info +
        # confirm dialog), so the injected callback just says yes.
        ConsolidateWorker(mod.consolidate, self._q, self.cancel_event,
                          lambda _p: True, day=day).start()
        return {"ok": True}

    # ---- run report / folders -----------------------------------------------------

    @_api_method
    def save_run_report(self):
        """Save a copy of the last run's per-route report to a chosen location.
        For a multi-report run this is one combined CSV. Every run is also
        auto-saved per report under output/run_reports/."""
        with self._lock:
            results = list(self._last_results)
        if not results:
            return {"error": "No completed run to save yet."}
        if len(results) == 1:
            spec, _result = results[0]
            default = f"run_report_{spec.subdir}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            default = f"run_report_multi_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        picked = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=default,
            file_types=("CSV file (*.csv)",))
        if not picked:
            return {"cancelled": True}
        path = Path(picked[0] if isinstance(picked, (list, tuple)) else picked)
        if len(results) == 1:
            spec, result = results[0]
            run_report.write_run_report(result, spec.label, path)
        else:
            run_report.write_run_report_multi(
                [(spec.label, result) for spec, result in results], path)
        self._emit_log(f"Run report saved: {path}")
        return {"saved": str(path)}

    def _open_folder(self, folder):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))        # Windows
            ui_log.info("opened folder: %s", folder)
        except Exception as e:
            log.warning("could not open folder %s (%s: %s)", folder, type(e).__name__, e)
            self._emit_modal("error", "Could not open folder", str(e))

    @_api_method
    def open_output_folder(self):
        self._open_folder(OUTPUT_ROOT)
        return {"ok": True}

    @_api_method
    def open_logs_folder(self):
        self._open_folder(LOG_DIR)
        return {"ok": True}

    @_api_method
    def open_consolidated_folder(self, report_idx, day):
        _label, mod = CONSOLIDATE_REPORTS[int(report_idx)]
        self._open_folder(mod.out_path_for(day or None).parent)
        return {"ok": True}


# ============================== window bootstrap ==============================

def _fatal_box(text):
    """Last-resort error surface for a windowed .exe (no console, no window)."""
    try:
        ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, 0x10)  # MB_ICONERROR
    except Exception:
        pass


def run():
    """Create the window and run the GUI (blocks until the window closes)."""
    api = GuiApi()
    index = _ui_index_path()
    if not index.exists():
        log.critical("UI assets missing: %s", index)
        _fatal_box("The app's interface files are missing, so the window can't "
                   "open. Re-extract the app folder, or reinstall.\n\n"
                   f"(Expected at: {index})")
        raise SystemExit(1)

    # Open at a size that fits the screen (small laptops included); the layout
    # scrolls below ~980px wide, so nothing is ever cut off at the minimum.
    try:
        screen = webview.screens[0]
        width = min(1180, int(screen.width * 0.92))
        height = min(780, int(screen.height * 0.90))
    except Exception:
        width, height = 1080, 720
    window = webview.create_window(
        APP_NAME, str(index), js_api=api,
        width=width, height=height, min_size=(560, 480),
        text_select=True)              # users copy log lines / paths
    api.attach(window)
    # Persistent app-owned WebView2 profile: pywebview's default private mode
    # writes a fresh Chromium profile into %TEMP% on EVERY launch (tens of MB,
    # leaked if the process is killed) and cold-starts the browser each time.
    # One stable folder under the app's data dir avoids both; the UI stores
    # nothing sensitive in it.
    debug = os.environ.get("TSMIS_UI_DEBUG", "").strip().lower() in ("1", "true", "yes")
    log.info("starting webview (window %dx%d, ui=%s, profile=%s%s)",
             width, height, index, WEBVIEW_PROFILE_DIR, ", debug" if debug else "")
    try:
        webview.start(gui="edgechromium", debug=debug,
                      private_mode=False, storage_path=str(WEBVIEW_PROFILE_DIR))
    except Exception as e:
        # Most likely cause on a clean PC: the WebView2 runtime is missing
        # (ships with Windows 10/11 and Microsoft Edge).
        log.critical("webview failed to start", exc_info=True)
        _fatal_box("The app window could not be created.\n\n"
                   "This tool displays its interface with Microsoft Edge "
                   "WebView2, which is part of Windows 10/11. Installing or "
                   "updating Microsoft Edge restores it.\n\n"
                   f"Details: {type(e).__name__}: {e}\n"
                   f"Log file: {LOG_DIR}")
        raise SystemExit(1)
