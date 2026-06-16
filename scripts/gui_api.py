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
import secrets
import sys
import threading
import time
import webbrowser
from pathlib import Path
from queue import Empty, Queue

import webview

import run_report
import settings
import updater
from gui_worker import (CheckWorker, ChromiumWorker, ConsolidateWorker,
                        EnvCheckWorker, EnvScanWorker, ExportWorker,
                        LoginWorker, ResetWorker, UpdateWorker,
                        measure_targets, reset_targets)
from exporter_parallel import MAX_WORKERS, default_worker_count
from logging_setup import LOG_FILE, set_debug_logging

from paths import (BUNDLED_BROWSERS_DIR, DATA_ROOT, DOWNLOADED_BROWSERS_DIR,
                   FAILURES_DIR, LOG_DIR, OUTPUT_ROOT, WEBVIEW_PROFILE_DIR,
                   is_frozen, list_output_days)
from version import APP_NAME, __version__
from common import (
    BROWSER_CHANNELS, CHANNEL_LABELS, DATA_SOURCES, DATA_SOURCE_LABELS,
    ENVIRONMENTS, ENVIRONMENT_LABELS, ROUTES, AuthError,
    _auth_file_age_hours, clear_auth, default_site_url, get_site,
    has_valid_auth, parse_routes, require_valid_auth, set_preferred_channel,
    set_site,
)
from paths import EDGE_LOGIN_PROFILE_DIR
from reports import COMPARE_REPORTS, CONSOLIDATE_REPORTS, EXPORT_REPORTS

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

        # Per-environment access verdicts from the Settings "Check all
        # environments" scan, keyed "src-env". Session-only on purpose (access
        # is server-side state that changes under us): every launch starts at
        # "not checked". Mirrored into each snapshot for the Settings rows +
        # the title-bar access chip.
        self._env_access = {}

        # One-click update state, mirrored into every snapshot for the title-bar
        # pill. phase: idle|checking|none|available|downloading|staged|applying|
        # failed; can_apply False = read-only install (pill opens the release
        # page instead). The UpdateInfo itself stays Python-side.
        self._update = {"phase": "idle"}
        self._update_info = None

        self._last_results = []      # [(spec, RunResult), ...] of the last export
        self._export_worker = None   # live ExportWorker (screenshot requests)
        # Server-side confirmation for the one destructive op (delete all
        # reports): reset_preview issues a single-use token bound to the
        # include_input flag; start_reset requires it back, so the delete can't
        # run without a preview having been shown first. (token, include_input).
        self._reset_token = None
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
                "update": dict(self._update),
                "env_access": {k: dict(v) for k, v in self._env_access.items()},
                "logins": self._login_states(),
            }

    def _push_state(self):
        self._emit({"t": "state", "s": self._state_snapshot()})

    def _login_states(self):
        """The TWO sign-in paths, separately, for the title-bar indicators:
        the SAVED LOGIN file (captured via Chrome / Built-in Chromium; what
        exports restore and fast mode requires) and the EDGE ONE-CLICK
        (the persistent Edge sign-in profile — `primed` means the profile
        exists from a past headed Edge sign-in, `ok` means a silent sign-in
        actually worked this session). Cheap stat calls only."""
        valid = has_valid_auth()
        age = _auth_file_age_hours() if valid else None
        try:
            primed = EDGE_LOGIN_PROFILE_DIR.is_dir() and any(
                EDGE_LOGIN_PROFILE_DIR.iterdir())
        except OSError:
            primed = False
        return {"file": {"valid": valid,
                         "age_h": round(age, 1) if age is not None else None},
                "device": {"ok": self._device_ok, "primed": primed}}

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
        elif kind == "worker_status":
            worker, text = payload
            self._emit({"t": "wstatus", "w": worker, "text": text})
        elif kind == "preview_shot":
            worker, b64, note, url = payload
            self._emit({"t": "preview", "w": worker, "img": b64, "note": note,
                        "url": url})
        elif kind == "env_shot":
            self._on_env_shot(payload)
        elif kind == "env_access":
            self._on_env_access(payload)
        elif kind == "env_access_done":
            self._on_env_scan_done(payload)
        elif kind == "reset_done":
            self._on_reset_done(payload)
        elif kind == "chromium_done":
            self._on_chromium_done(payload)
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
            self._maybe_autoscan("login")
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
            self._maybe_autoscan("login")
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
        elif kind == "update_status":
            self._on_update_status(payload)
        elif kind == "error":
            self._on_error(payload)

    def _end_task(self):
        with self._lock:
            self._task = None
            self._fast_run = False
            self._login_phase = None
            self._export_worker = None
        self._refresh_auth()
        self._emit({"t": "run_ended"})
        self._push_state()

    # ---- single-flight task gate + input validation (bridge hardening) --------

    def _try_claim_task(self, name):
        """Atomically claim the single task slot: returns True if claimed, False
        if another task is already running. Use this instead of a separate
        'check' then later 'set' -- those two race, so two quick clicks (or a
        save dialog between them) could both pass the gate and start two
        workers."""
        with self._lock:
            if self._task:
                return False
            self._task = name
            return True

    def _release_task(self):
        """Drop a slot claimed by _try_claim_task before a worker actually
        started (e.g. the user cancelled the save dialog), so the next action
        isn't blocked by a phantom task."""
        with self._lock:
            self._task = None

    @staticmethod
    def _pick_report(registry, idx):
        """Bounds-checked registry row for a UI-supplied index, or None for a
        bad (out-of-range / non-numeric) index -- a malformed bridge call can't
        IndexError its way to an unhandled state or leave a task slot stuck."""
        try:
            i = int(idx)
        except (TypeError, ValueError):
            return None
        return registry[i] if 0 <= i < len(registry) else None

    @staticmethod
    def _safe_day(day):
        """Validate a consolidate/compare 'day' (run-folder name) from the
        bridge: None/empty (newest) or an EXISTING run folder. Anything else --
        a traversal like '..\\..\\Windows' or a stale name -- is rejected, so a
        crafted day can never resolve a path outside the output area. Returns
        the validated day (or None); raises ValueError otherwise."""
        day = (day or "").strip()
        if not day:
            return None
        if day in list_output_days():
            return day
        raise ValueError("That export folder isn't available — pick one from "
                         "the list.")

    @staticmethod
    def _resolve_under_output(name):
        """Resolve a run-folder NAME (from a dropdown, not Browse…) to an
        absolute path, rejecting any traversal that escapes OUTPUT_ROOT. Browse…
        hands in absolute paths and is handled separately by the caller."""
        root = OUTPUT_ROOT.resolve()
        p = (OUTPUT_ROOT / name).resolve()
        if p != root and root not in p.parents:
            raise ValueError("That folder is outside the output area.")
        return p

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
            # Comparisons carry a verdict: surface the quick answer in a
            # dialog too — "everything matches" is the expected outcome
            # between environments, so it deserves more than a log line.
            if result.verdict and result.summary_lines:
                if result.verdict == "match":
                    self._emit_modal("info", "Everything matches",
                                     result.summary_lines[0] + "\n\n"
                                     "The saved workbook has the full "
                                     "breakdown and self-checks.")
                else:
                    self._emit_modal("warning", "Differences found",
                                     result.summary_lines[0] + "\n\n"
                                     "Open the saved workbook for the "
                                     "cell-by-cell breakdown (Summary → "
                                     "Comparison → Only-in sheets).")
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
        # Browsers are probed and the saved login (if any) is known: the right
        # moment for the automatic environment check.
        self._maybe_autoscan("startup")

    def _maybe_autoscan(self, reason):
        """Start the env-access scan unprompted — once per session, only when
        a login is available (a no-login scan would just log six failures at
        every launch), never preempting other work, and only when the
        Settings toggle allows it."""
        try:
            if not settings.get("env_check_on_start"):
                return
        except Exception:
            return
        with self._lock:
            if self._task or self._env_access:
                return
            if not (self._authed or self._device_ok):
                return
        log.info("env scan: automatic start (%s)", reason)
        self._emit_log("Checking access to all environments in the background "
                       "(automatic — turn off in Settings)…")
        self.check_environments()

    def _on_update_status(self, payload):
        """UpdateWorker's whole-state posts. `manual` (user clicked) decides
        whether quiet outcomes (up to date / a failed launch check) reach the
        log pane; tsmis.log always has the full story from updater.py."""
        manual = payload.pop("manual", False)
        info = payload.pop("_info", None)
        with self._lock:
            if info is not None:
                self._update_info = info
            self._update = payload
        phase = payload.get("phase")
        ver = payload.get("version")
        if phase == "available":
            if payload.get("can_apply"):
                size = f" ({payload['size_mb']} MB)" if payload.get("size_mb") else ""
                self._emit_log(f"Update available: v{ver}{size} — click "
                               f"‘Update to v{ver}’ in the title bar to install it.")
                # An update being offered WHILE the helper log ends in a
                # failure means the last attempt rolled back — say so instead
                # of looking like nothing ever happened.
                fail = updater.last_swap_failure()
                if fail:
                    log.warning("update: previous swap rolled back: %s", fail)
                    self._emit_log("Heads-up: the previous update attempt could "
                                   "not be applied and the old version was "
                                   "restored. Trying again usually works — "
                                   "close any window showing the app's folder "
                                   "first. (Details: update_helper.log in the "
                                   "logs folder.)")
            else:
                self._emit_log(f"Update available: v{ver}. This app folder isn't "
                               "writable, so the title-bar button opens the download "
                               "page instead — extract the new zip into a folder you "
                               "can write to.")
        elif phase == "none" and manual:
            self._emit_log(f"You're on the latest version (v{__version__}).")
        elif phase == "staged":
            self._emit_log(f"Update v{ver} is downloaded and ready — click "
                           "‘Restart to update’ when you're done working "
                           "(the app closes, updates itself, and reopens).")
        elif phase == "failed" and manual:
            self._emit_log(f"Update problem: {payload.get('note')} "
                           "(details are in the log file)")
        self._push_state()

    def _start_update_check(self, manual=False):
        mode, why = updater.update_support()
        if mode == "off":
            log.info("update check skipped: %s", why)
            if manual:
                self._emit_log("Update check: not available in a development run.")
            return
        if mode == "link":
            log.info("update: link-only mode (%s)", why)
        with self._lock:
            self._update = {"phase": "checking"}
        if manual:
            self._emit_log("Checking for updates…")
        self._push_state()
        UpdateWorker(self._q, "check", manual=manual).start()

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
            self._start_update_check()       # quiet unless an update exists
        return {
            "app_name": APP_NAME,
            "version": __version__,
            "output_root": str(OUTPUT_ROOT),
            "log_dir": str(LOG_DIR),
            "reports": [{"label": label, "fmt": fmt} for label, fmt, _spec in EXPORT_REPORTS],
            "cons_reports": [label for label, _mod in CONSOLIDATE_REPORTS],
            "compare_reports": [{"label": label, "kind": kind}
                                for label, _mod, kind in COMPARE_REPORTS],
            "routes": list(ROUTES),
            "channels": [{"id": c, "label": CHANNEL_LABELS[c],
                          "short": _CHANNEL_SHORT.get(c, CHANNEL_LABELS[c])}
                         for c in BROWSER_CHANNELS],
            "channel": self._channel,
            "sources": [{"id": s, "label": DATA_SOURCE_LABELS[s]} for s in DATA_SOURCES],
            "envs": [{"id": e, "label": ENVIRONMENT_LABELS[e]} for e in ENVIRONMENTS],
            "site": dict(zip(("source", "environment"), get_site())),
            "fast": {"default": default_worker_count(), "max": MAX_WORKERS},
            "settings": self.get_settings(),
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
        # Safe even while the env scan runs: scanner threads pin their own
        # targets via common.set_thread_site and never touch this selection.
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

    # ---- one-click update ------------------------------------------------------

    @_api_method
    def check_updates(self):
        """Manual re-check (clicking the version chip)."""
        with self._lock:
            phase = self._update.get("phase")
        if phase in ("checking", "downloading", "applying"):
            return {"ok": True}              # already busy with update work
        if phase == "staged":
            self._emit_log("An update is already downloaded — click "
                           "‘Restart to update’ in the title bar to install it.")
            return {"ok": True}
        self._start_update_check(manual=True)
        return {"ok": True}

    @_api_method
    def update_start(self):
        """Download + stage the offered update. Allowed during a run (network
        and disk only); the restart itself is gated on no task running."""
        with self._lock:
            if self._update.get("phase") != "available" or not self._update.get("can_apply"):
                return {"error": "No update is ready to install."}
            info = self._update_info
            if info is None:
                return {"error": "No update is ready to install."}
            self._update = {"phase": "downloading", "progress": 0,
                            "version": info.version, "url": info.release_url,
                            "can_apply": True}
        size = f" ({round(info.asset_size / 1e6)} MB)" if info.asset_size else ""
        self._emit_log(f"Downloading update v{info.version}{size}…")
        self._push_state()
        UpdateWorker(self._q, "download", info=info).start()
        return {"ok": True}

    @_api_method
    def update_apply(self):
        """Restart into the staged update: launch the swap helper, then close
        this window (the helper waits for our PID before touching files)."""
        with self._lock:
            if self._task:
                return {"error": "Finish or cancel the running task first."}
            if self._update.get("phase") != "staged":
                return {"error": "No downloaded update is ready."}
            staged = self._update.get("staged")
            self._update = dict(self._update, phase="applying")
        ui_log.info("update: user chose Restart to update")
        try:
            updater.apply_update_and_restart(staged)
        except updater.UpdateError as e:
            with self._lock:
                self._update = {"phase": "failed", "note": str(e)}
            self._emit_log(f"Update problem: {e} (details are in the log file)")
            self._push_state()
            return {"error": str(e)}
        self._emit_log("Restarting to finish the update — the app will close "
                       "and reopen by itself…")
        self._push_state()
        threading.Thread(target=self._close_for_update, daemon=True,
                         name="update-restart").start()
        return {"ok": True}

    def _close_for_update(self):
        time.sleep(1.2)                  # let the sender flush the goodbye line
        try:
            self._window.destroy()       # webview.start() returns; process exits
        except Exception:
            log.warning("window destroy failed; force-exiting so the update "
                        "helper can proceed", exc_info=True)
            os._exit(0)

    @_api_method
    def open_release_page(self):
        url = self._update.get("url") or updater.RELEASES_PAGE
        ui_log.info("opening release page: %s", url)
        webbrowser.open(url)
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
        # Validate inputs BEFORE claiming the task slot (pure, no shared state),
        # then claim atomically -- so two quick clicks can't both pass the gate
        # and launch two export runs (the old check-then-set raced).
        specs = []
        for i in (report_idxs if isinstance(report_idxs, (list, tuple)) else []):
            row = self._pick_report(EXPORT_REPORTS, i)
            if row is not None:
                specs.append(row[2])
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
                n_workers = max(2, default_worker_count())

        if not self._try_claim_task("export"):
            return {"error": "A task is already running."}
        with self._lock:
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
        # `workers` tells the UI how many live browser-status rows to show.
        self._emit({"t": "run_started", "mode": "export", "label": "Working…",
                    "workers": n_workers})
        self._push_state()
        worker = ExportWorker(specs, self._q, self.cancel_event, self.skip_event,
                              workers=n_workers, routes=run_routes)
        with self._lock:
            self._export_worker = worker
        worker.start()
        return {"ok": True}

    @_api_method
    def request_preview(self, worker_no):
        """Ask browser `worker_no` (1-based) for a live screenshot; it answers
        with a 'preview' event at its next safe poll point (≤ ~5 s during a
        report wait; a long download can delay it until the next route)."""
        with self._lock:
            worker = self._export_worker
            running = self._task == "export"
        if not running or worker is None:
            return {"error": "No export is running."}
        worker.request_screenshot(worker_no)
        ui_log.info("preview requested for browser %s", worker_no)
        return {"ok": True}

    @_api_method
    def skip_route(self):
        if self._task == "export":
            self.skip_event.set()
            self._emit_log("Skip requested — will move on once the current wait ends.")
        return {"ok": True}

    @_api_method
    def cancel_run(self):
        if self._task in ("export", "consolidate", "compare", "chromium",
                          "envscan"):
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

    # ---- verify environment (idle screenshot) ---------------------------------

    @_api_method
    def verify_environment(self):
        """Open TSMIS headless exactly like an export would, read which data
        source / environment the page ACTUALLY loaded, and screenshot it —
        proof the automation lands on the selected site without running an
        export. Needs a login (saved or automatic), like an export."""
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            self._task = "envcheck"
        src, env = get_site()
        label = f"{DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]}"
        self._emit_log(f"Verifying environment: opening TSMIS on {label}…")
        self._set_dot("busy", f"Checking {label}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Checking {label}…"})
        self._push_state()
        EnvCheckWorker(self._q).start()
        return {"ok": True}

    def _on_env_shot(self, payload):
        """EnvCheckWorker's single result message → log + preview modal."""
        src, env = get_site()
        want = f"{DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]}"
        if payload.get("error"):
            self._emit_log(f"Environment check failed: {payload['error']}")
            self._emit_modal("warning", "Environment check failed", payload["error"])
        elif payload.get("env"):
            got = (f"{DATA_SOURCE_LABELS.get(payload['src'], payload['src'])} / "
                   f"{ENVIRONMENT_LABELS.get(payload['env'], payload['env'])}")
            if payload.get("matches"):
                self._emit_log(f"Environment check: the page is running {got} "
                               "— matches your selection.")
            else:
                self._emit_log(f"WARNING: the page is running {got}, but "
                               f"{want} is selected. Exports would hit {got}.")
        else:
            self._emit_log("Environment check: signed in, but the page didn't "
                           "report which site it loaded (screenshot attached).")
        if payload.get("img") or payload.get("error") is None:
            self._emit({"t": "preview", "w": 0, "img": payload.get("img"),
                        "note": "Verify environment",
                        "url": payload.get("url"), "env_info": {
                            "ok": payload.get("ok"),
                            "env": payload.get("env"), "src": payload.get("src"),
                            "matches": payload.get("matches"),
                            "wanted": want}})
        self._end_task()

    # ---- environment access scan (Settings + title-bar chip) -------------------

    @_api_method
    def check_environments(self):
        """Probe EVERY data source / environment combination headless, like an
        export would: does sign-in complete, does the page load the right
        site, and can the report form pull data. Verdicts stream into the
        Settings rows and the title-bar access chip as each site finishes.
        Needs a login (saved or automatic), like an export."""
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            self._task = "envscan"
            for src in DATA_SOURCES:
                for env in ENVIRONMENTS:
                    key = f"{src}-{env}"
                    self._env_access[key] = {
                        "key": key, "source": src, "environment": env,
                        "label": f"{DATA_SOURCE_LABELS[src]} / "
                                 f"{ENVIRONMENT_LABELS[env]}",
                        "status": "checking", "detail": "Checking…",
                        "url": "", "checked_at": ""}
        self.cancel_event.clear()
        self._emit_log("Checking sign-in and report access for every "
                       "environment (six sites — this can take a few minutes)…")
        self._set_dot("busy", "Checking environments…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Checking all environments…"})
        self._push_state()
        EnvScanWorker(self._q, self.cancel_event).start()
        return {"ok": True}

    def _on_env_access(self, payload):
        """One site's verdict from the scan → state snapshot + a log line."""
        entry = dict(payload)
        entry["checked_at"] = time.strftime("%H:%M")
        with self._lock:
            self._env_access[entry["key"]] = entry
        mark = "OK" if entry["status"] == "ok" else "PROBLEM"
        self._emit_log(f"  {entry['label']}: {mark} — {entry['detail']}")
        self._push_state()

    def _on_env_scan_done(self, payload):
        with self._lock:
            # A cancelled scan leaves later sites untouched — back to "not
            # checked", never a stale spinner.
            for key in [k for k, v in self._env_access.items()
                        if v.get("status") == "checking"]:
                del self._env_access[key]
        if payload.get("error"):
            self._emit_log(f"Environment check stopped: {payload['error']}")
        elif payload.get("cancelled"):
            self._emit_log("Environment check cancelled.")
        else:
            ok, total = payload.get("ok", 0), payload.get("total", 0)
            if ok == total:
                self._emit_log(f"Environment check done: all {total} sites OK.")
            else:
                self._emit_log(f"Environment check done: {ok} of {total} sites "
                               "OK — details next to each address in Settings.")
        self._end_task()

    # ---- consolidate -------------------------------------------------------------

    @_api_method
    def consolidate_info(self, report_idx, day):
        row = self._pick_report(CONSOLIDATE_REPORTS, report_idx)
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        try:
            day = self._safe_day(day)
        except ValueError as e:
            return {"error": str(e)}
        _label, mod = row
        out = mod.out_path_for(day)
        info = {"dest_dir": str(out.parent), "out_path": str(out),
                "exists": out.exists()}
        # Reports whose input is user-supplied (TSN PDFs) advertise it so the
        # pane can say where the files go and offer to open that folder.
        note = getattr(mod, "INPUT_NOTE", None)
        if note:
            info["input_note"] = note
            info["input_dir"] = str(mod.input_dir_for(day or None))
        return info

    @_api_method
    def open_consolidate_input(self, report_idx):
        row = self._pick_report(CONSOLIDATE_REPORTS, report_idx)
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        _label, mod = row
        in_dir = getattr(mod, "INPUT_DIR", None)
        if in_dir is None:
            return {"error": "This report has no input folder."}
        self._open_folder(in_dir)
        return {"ok": True}

    @_api_method
    def decline_overwrite(self):
        self._emit_log("Consolidation cancelled (kept existing file).")
        return {"ok": True}

    @_api_method
    def start_consolidate(self, report_idx, day):
        # Validate the report index + day BEFORE claiming the slot -- otherwise a
        # bad index would IndexError after self._task was set, wedging the task
        # gate "consolidate" forever (every later action blocked until restart).
        row = self._pick_report(CONSOLIDATE_REPORTS, report_idx)
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        try:
            day = self._safe_day(day)
        except ValueError as e:
            return {"error": str(e)}
        label, mod = row
        if not self._try_claim_task("consolidate"):
            return {"error": "A task is already running."}
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

    # ---- comparisons (TSMIS vs TSN files / env vs env run folders) -----------------

    @_api_method
    def pick_compare_file(self, side):
        """Native open dialog for one comparison input. `side` is "TSMIS" or
        "TSN" (display only). Returns {"path": ...} or {"cancelled": True}."""
        picked = self._window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False,
            file_types=("Excel workbook (*.xlsx)",))
        if not picked:
            return {"cancelled": True}
        path = picked[0] if isinstance(picked, (list, tuple)) else picked
        ui_log.info("compare: %s file picked: %s", side, path)
        return {"path": str(path)}

    @_api_method
    def pick_compare_folder(self, side):
        """Native folder dialog for one cross-environment comparison side
        (for folders outside output/ — the dropdowns list the run folders)."""
        picked = self._window.create_file_dialog(
            webview.FOLDER_DIALOG, directory=str(OUTPUT_ROOT))
        if not picked:
            return {"cancelled": True}
        path = picked[0] if isinstance(picked, (list, tuple)) else picked
        ui_log.info("compare: side %s folder picked: %s", side, path)
        return {"path": str(path)}

    def _save_dialog_for_compare(self, directory, suggested):
        """Shared save dialog — the native dialog also owns the overwrite
        question. Returns a Path or None (cancelled)."""
        picked = self._window.create_file_dialog(
            webview.SAVE_DIALOG, directory=str(directory),
            save_filename=suggested,
            file_types=("Excel workbook (*.xlsx)",))
        if not picked:
            ui_log.info("compare: save dialog cancelled")
            return None
        return Path(picked[0] if isinstance(picked, (list, tuple)) else picked)

    @staticmethod
    def _compare_mode(want_formulas, want_values):
        if not want_formulas and not want_values:
            return None
        return ("both" if want_formulas and want_values
                else "formulas" if want_formulas else "values")

    def _launch_compare(self, label, mode, out, run_fn):
        # The task slot was already claimed by the caller (before the save
        # dialog), so a second click can't slip in while the dialog is open.
        self.cancel_event.clear()
        kinds = {"both": "values + live formulas", "formulas": "live formulas",
                 "values": "values"}[mode]
        self._emit_log(f"Starting comparison: {label} ({kinds})")
        ui_log.info("compare: %s mode=%s out=%s", label, mode, out)
        self._set_dot("busy", "Comparing…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Comparing — {label}…"})
        self._push_state()
        ConsolidateWorker(run_fn, self._q, self.cancel_event,
                          lambda _p: True).start()
        return {"ok": True}

    @_api_method
    def start_compare(self, report_idx, tsmis_path, tsn_path,
                      want_formulas=True, want_values=False):
        row = self._pick_report(COMPARE_REPORTS, report_idx)
        if row is None:
            return {"error": "That comparison isn't available — please reopen the tab."}
        label, mod, kind = row
        if kind != "files":
            return {"error": "This comparison type takes folders, not files."}
        if not tsmis_path or not tsn_path:
            return {"error": "Pick both files first (a TSMIS and a TSN workbook)."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live formulas)."}
        # Claim the slot BEFORE the (blocking) save dialog so a second click is
        # rejected immediately; release it if the user cancels the dialog.
        if not self._try_claim_task("compare"):
            return {"error": "A task is already running."}
        out = self._save_dialog_for_compare(Path(tsmis_path).parent,
                                            mod.suggest_name(tsmis_path))
        if out is None:
            self._release_task()
            return {"cancelled": True}
        return self._launch_compare(
            label, mode, out,
            lambda events=None, confirm_overwrite=None, day=None:
                mod.compare(tsmis_path, tsn_path, out, events=events,
                            confirm_overwrite=confirm_overwrite, mode=mode))

    @_api_method
    def start_compare_env(self, report_idx, dir_a, dir_b,
                          want_formulas=True, want_values=False):
        """Cross-environment comparison: two run folders (names from the
        dropdowns resolve under output/; Browse… hands in absolute paths)."""
        row = self._pick_report(COMPARE_REPORTS, report_idx)
        if row is None:
            return {"error": "That comparison isn't available — please reopen the tab."}
        label, adapter, kind = row
        if kind != "folders":
            return {"error": "This comparison type takes files, not folders."}
        if not dir_a or not dir_b:
            return {"error": "Pick both export folders first."}
        # A dropdown hands in a run-folder NAME (resolved under output/, with
        # traversal rejected); Browse… hands in an absolute path the user
        # explicitly chose, used as-is.
        try:
            pa = Path(dir_a) if Path(dir_a).is_absolute() else self._resolve_under_output(dir_a)
            pb = Path(dir_b) if Path(dir_b).is_absolute() else self._resolve_under_output(dir_b)
        except ValueError as e:
            return {"error": str(e)}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live formulas)."}
        import compare_env
        compare_env.DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
        if not self._try_claim_task("compare"):
            return {"error": "A task is already running."}
        out = self._save_dialog_for_compare(compare_env.DEFAULT_OUT_DIR,
                                            adapter.suggest_name(pa, pb))
        if out is None:
            self._release_task()
            return {"cancelled": True}
        return self._launch_compare(
            label, mode, out,
            lambda events=None, confirm_overwrite=None, day=None:
                adapter.compare_folders(pa, pb, out, events=events,
                                        confirm_overwrite=confirm_overwrite,
                                        mode=mode))

    # ---- settings & maintenance -----------------------------------------------

    def _site_url_rows(self):
        """All six (src, env) combos with their effective / default URLs —
        the Settings tab's editable "site addresses" list."""
        overrides = settings.all_site_urls()
        rows = []
        for src in DATA_SOURCES:
            for env in ENVIRONMENTS:
                key = f"{src}-{env}"
                default = default_site_url(src, env)
                custom = overrides.get(key)
                rows.append({
                    "key": key, "source": src, "environment": env,
                    "label": f"{DATA_SOURCE_LABELS[src]} · {ENVIRONMENT_LABELS[env]}",
                    "default": default,
                    "url": custom or default,
                    "custom": bool(custom),
                })
        return rows

    def _chromium_state(self):
        """What the Settings tab's Built-in Chromium section shows."""
        bundled = bool(BUNDLED_BROWSERS_DIR and BUNDLED_BROWSERS_DIR.is_dir())
        downloaded = False
        size_mb = 0
        try:
            if DOWNLOADED_BROWSERS_DIR.is_dir():
                downloaded = any(DOWNLOADED_BROWSERS_DIR.glob("chromium-*"))
                if downloaded:
                    size_mb = round(sum(
                        f.stat().st_size
                        for f in DOWNLOADED_BROWSERS_DIR.rglob("*") if f.is_file()
                    ) / 1e6)
        except OSError:
            pass
        return {
            "bundled": bundled,
            "downloaded": downloaded,
            "downloaded_mb": size_mb,
            # whether THIS process can already use a Built-in Chromium
            # (channels are probed at startup; changes need a restart)
            "active": "chromium" in BROWSER_CHANNELS,
            "dir": str(DOWNLOADED_BROWSERS_DIR),
        }

    @_api_method
    def get_settings(self):
        """Everything the Settings tab shows: the saved knobs plus read-only
        build/paths facts (so problems are diagnosable from the screen)."""
        auth_state = "saved login" if has_valid_auth() else (
            "automatic sign-in" if self._device_ok else "none")
        return {
            "values": settings.all_settings(),
            "defaults": dict(settings.DEFAULTS),
            "site_urls": self._site_url_rows(),
            "chromium": self._chromium_state(),
            "meta": {
                "version": __version__,
                "build": "portable app" if is_frozen() else "development run",
                "variant": ("with built-in browser"
                            if "chromium" in BROWSER_CHANNELS else "system browser"),
                "data_root": str(DATA_ROOT),
                "output_root": str(OUTPUT_ROOT),
                "log_file": str(LOG_FILE),
                "failures_dir": str(FAILURES_DIR),
                "auth_state": auth_state,
                "max_workers": MAX_WORKERS,
            },
        }

    @_api_method
    def set_site_url(self, source, environment, url):
        """Save (or clear, with an empty value) one environment's TSMIS
        address. Applies to the very next sign-in / export / verify — the
        stopgap for "the site moved before an app update shipped"."""
        url = (url or "").strip()
        if url == default_site_url(source, environment):
            url = ""                      # typing the default back = no override
        try:
            settings.set_site_url(source, environment, url)
        except ValueError as e:
            return {"error": str(e), "site_urls": self._site_url_rows()}
        label = f"{DATA_SOURCE_LABELS.get(source, source)} / " \
                f"{ENVIRONMENT_LABELS.get(environment, environment)}"
        if url:
            self._emit_log(f"Site address for {label} changed to {url} "
                           "(used from the next sign-in or export on).")
        else:
            self._emit_log(f"Site address for {label} reset to the default.")
        return {"ok": True, "site_urls": self._site_url_rows()}

    # ---- Built-in Chromium download / delete -----------------------------------

    def _start_chromium(self, action, start_log):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            self._task = "chromium"
        self.cancel_event.clear()
        self._emit_log(start_log)
        self._set_dot("busy", "Working on the Built-in Chromium…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": ("Downloading the Built-in Chromium…"
                              if action == "download" else
                              "Removing the Built-in Chromium…")})
        self._push_state()
        ChromiumWorker(self._q, action, self.cancel_event).start()
        return {"ok": True}

    @_api_method
    def download_chromium(self):
        """Download the Built-in Chromium into the app's data folder (the
        same browser the with-browser variant ships; ~170 MB). Restart to
        select it — browsers are probed at startup."""
        if self._chromium_state()["downloaded"]:
            return {"error": "A downloaded Built-in Chromium is already here. "
                             "Delete it first to re-download."}
        ui_log.info("chromium: user started download")
        return self._start_chromium(
            "download", "Downloading the Built-in Chromium (~170 MB)…")

    @_api_method
    def delete_chromium(self):
        """Remove the DOWNLOADED Built-in Chromium (the with-browser bundle's
        own copy is part of the app and is never touched)."""
        if not self._chromium_state()["downloaded"]:
            return {"error": "There is no downloaded Built-in Chromium to remove."}
        ui_log.info("chromium: user started delete")
        return self._start_chromium(
            "delete", "Removing the downloaded Built-in Chromium…")

    def _on_chromium_done(self, payload):
        if payload.get("cancelled"):
            self._emit_log("Built-in Chromium download cancelled.")
        elif not payload.get("ok"):
            msg = payload.get("error") or "Something went wrong (see the log)."
            self._emit_log(f"ERROR: {msg}")
            self._emit_modal("error", "Built-in Chromium", msg)
        elif payload.get("action") == "download":
            self._emit_log("Built-in Chromium downloaded. Restart the app to "
                           "see it in the Browser dropdown (browsers are "
                           "probed at startup).")
            self._emit_modal("info", "Built-in Chromium downloaded",
                             "The browser is in place. Restart the app and it "
                             "will appear in the Browser dropdown as "
                             "'Built-in Chromium'.")
        else:
            self._emit_log("Downloaded Built-in Chromium removed."
                           + (" Restart the app to finish switching back to "
                              "Edge/Chrome." if self._chromium_state()["active"]
                              else ""))
        self._set_dot("ok" if self._authed else "bad", "Done")
        # Refresh the Settings tab's section (JS swaps in the new state).
        self._emit({"t": "settings", "s": self.get_settings()})
        self._end_task()

    @_api_method
    def set_setting(self, key, value):
        """Persist one setting and apply any live side effect. Timeouts and
        the worker default are read at run start, so they apply to the next
        run; verbose logging switches immediately; DevTools applies on the
        next launch."""
        new = settings.update({key: value})
        if key == "debug_logging":
            set_debug_logging(new["debug_logging"])
        ui_log.info("settings: %s = %r", key, new.get(key))
        return {"ok": True, "values": new}

    @_api_method
    def reset_preview(self, include_input=False):
        """What "Delete all reports" would remove right now — shown in the
        confirm dialog so the user approves a concrete list, not a vibe. Also
        issues the single-use confirm token start_reset requires (server-side
        gate: the delete can't run unless a preview was shown for the same
        include_input)."""
        include_input = bool(include_input)
        targets = reset_targets(include_input)
        files, size = measure_targets(targets)
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._reset_token = (token, include_input)
        return {"targets": [label for label, _p in targets],
                "files": files, "mb": round(size / 1e6, 1), "token": token}

    @_api_method
    def start_reset(self, include_input=False, confirm_token=None):
        """Delete all generated reports. Server-side confirmation: requires the
        single-use token reset_preview issued for the SAME include_input, so a
        direct bridge call can't skip the preview the user approved. Logs, the
        saved login and the settings always survive."""
        include_input = bool(include_input)
        with self._lock:
            expected = self._reset_token
            self._reset_token = None        # single-use: consume it either way
        if not expected or confirm_token != expected[0] or expected[1] != include_input:
            ui_log.warning("reset: refused — no matching confirmation (a preview "
                           "must be shown first)")
            return {"error": "Please confirm the delete from the dialog "
                             "(open 'Delete all reports' again)."}
        if not self._try_claim_task("reset"):
            return {"error": "A task is already running."}
        ui_log.info("reset: user confirmed delete-all-reports (input=%s)",
                    include_input)
        self._emit_log("Deleting all reports…")
        self._set_dot("busy", "Deleting reports…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Deleting reports…"})
        self._push_state()
        ResetWorker(self._q, include_input=bool(include_input)).start()
        return {"ok": True}

    def _on_reset_done(self, payload):
        if payload.get("errors"):
            self._emit_log(f"Deleted {payload['files']} file(s) "
                           f"({payload['mb']} MB), but some items couldn't be "
                           "removed:")
            for line in payload["errors"]:
                self._emit_log(f"  {line}")
            self._emit_modal("warning", "Some files couldn't be deleted",
                             "Close any report files still open in Excel, "
                             "then run 'Delete all reports' again.")
        else:
            self._emit_log(f"Done — deleted {payload['files']} file(s), "
                           f"freed {payload['mb']} MB. Logs, your login and "
                           "settings were kept.")
        self._set_dot("ok" if self._authed else "bad", "Done")
        self._end_task()

    @_api_method
    def save_support_bundle(self):
        """Zip the diagnostics a maintainer needs (rotating logs, run reports,
        settings, a manifest) to a user-chosen location.

        What it does NOT contain: the saved login / browser profiles / failure
        dumps (FAILURES_DIR) are never added. What it DOES contain, by design:
        the rotating logs and the manifest, which include this PC's name in file
        paths, the OS version, and the current settings — diagnostics need those.
        So it's safe to send to the TSMIS maintainer, not "safe to post
        publicly"; the user-facing wording below says so plainly."""
        import io
        import platform
        import zipfile

        default = f"tsmis_support_{time.strftime('%Y%m%d_%H%M%S')}.zip"
        picked = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=default,
            file_types=("Zip archive (*.zip)",))
        if not picked:
            return {"cancelled": True}
        out = Path(picked[0] if isinstance(picked, (list, tuple)) else picked)

        manifest = io.StringIO()
        src, env = get_site()
        manifest.write(f"TSMIS Exporter support bundle\n"
                       f"NOTE: includes this PC's name in file paths, the OS\n"
                       f"  version and current settings (diagnostics need them);\n"
                       f"  NO saved login, browser profile, or failure dumps.\n"
                       f"  Send it to the TSMIS maintainer, not a public forum.\n"
                       f"created:    {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                       f"version:    {__version__}\n"
                       f"build:      {'frozen' if is_frozen() else 'dev'}\n"
                       f"python:     {platform.python_version()}\n"
                       f"os:         {platform.platform()}\n"
                       f"data_root:  {DATA_ROOT}\n"
                       f"output:     {OUTPUT_ROOT}\n"
                       f"site:       src={src} env={env}\n"
                       f"browsers:   {list(BROWSER_CHANNELS)} (picked: {self._channel})\n"
                       f"login:      {'saved file' if has_valid_auth() else 'none'}"
                       f"{' + device sign-in' if self._device_ok else ''}\n"
                       f"settings:   {settings.all_settings()}\n"
                       f"run folders: {list_output_days() or '(none)'}\n")
        added = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.txt", manifest.getvalue())
            for pattern, arc in (("tsmis.log*", "logs"), ("crash.log", "logs"),
                                 ("update_helper.log", "logs")):
                for f in sorted(LOG_DIR.glob(pattern)):
                    try:
                        zf.write(f, f"{arc}/{f.name}")
                        added += 1
                    except OSError:
                        pass
            reports = sorted((OUTPUT_ROOT / "run_reports").glob("*.csv"),
                             key=lambda p: p.stat().st_mtime, reverse=True)[:50]
            for f in reports:
                try:
                    zf.write(f, f"run_reports/{f.name}")
                    added += 1
                except OSError:
                    pass
        ui_log.info("support bundle saved: %s (%d files)", out, added)
        self._emit_log(f"Support bundle saved ({added} files): {out}")
        self._emit_log("  It has logs, run reports and settings (and this PC's "
                       "name in paths) — never your password or saved login. "
                       "Send it to the TSMIS maintainer.")
        return {"saved": str(out)}

    @_api_method
    def clear_saved_login(self):
        """Settings-tab action: forget the saved session (the file is deleted;
        automatic device sign-in, when available, is unaffected)."""
        removed = clear_auth()
        with self._lock:
            self._authed = False
        self._refresh_auth()
        self._emit_log("Saved login deleted — click 'Log in' to sign in again."
                       if removed else "There was no saved login to delete.")
        self._push_state()
        return {"ok": True, "removed": removed}

    @_api_method
    def open_failures_folder(self):
        self._open_folder(FAILURES_DIR)
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
    if not debug:
        try:
            debug = bool(settings.get("ui_devtools"))   # Settings-tab toggle
        except Exception:
            pass
    log.info("starting webview (window %dx%d, ui=%s, profile=%s%s)",
             width, height, index, WEBVIEW_PROFILE_DIR, ", debug" if debug else "")
    try:
        webview.start(gui="edgechromium", debug=debug,
                      private_mode=False, storage_path=str(WEBVIEW_PROFILE_DIR))
    except Exception as e:
        # Most likely causes: the WebView2 runtime is missing (ships with
        # Windows 10/11 and Edge), or the app folder came from a downloaded
        # zip that wasn't unblocked AND sits somewhere read-only, so the
        # startup self-unblock couldn't strip the Mark-of-the-Web either.
        log.critical("webview failed to start", exc_info=True)
        _fatal_box("The app window could not be created.\n\n"
                   "This tool displays its interface with Microsoft Edge "
                   "WebView2, which is part of Windows 10/11. Installing or "
                   "updating Microsoft Edge restores it.\n\n"
                   "If this folder was extracted from a downloaded zip, the "
                   "zip's 'blocked' flag can also cause this: right-click "
                   "the zip → Properties → tick Unblock → extract again "
                   "(into a folder you can write to, e.g. Desktop).\n\n"
                   f"Details: {type(e).__name__}: {e}\n"
                   f"Log file: {LOG_DIR}")
        raise SystemExit(1)
