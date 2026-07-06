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
import batch_manifest
import report_library
import updater
from gui_worker import (ActiveEnvCheckWorker, BatchWorker, CheckWorker,
                        ChromiumWorker, ConsolidateWorker, EnvCheckWorker,
                        EnvScanWorker, ExportWorker, LoginWorker, ResetWorker,
                        UpdateWorker, measure_targets, reset_targets)
from exporter_parallel import MAX_WORKERS, default_worker_count
from logging_setup import active_log_file, set_debug_logging

from paths import (BUNDLED_BROWSERS_DIR, DATA_ROOT, DOWNLOADED_BROWSERS_DIR,
                   FAILURES_DIR, LOG_DIR, OUTPUT_ROOT, TSN_LIBRARY_ROOT,
                   WEBVIEW_PROFILE_DIR,
                   is_frozen, list_output_days, list_output_days_for_report)
from version import APP_NAME, __version__
from common import (
    BROWSER_CHANNELS, CHANNEL_LABELS, DATA_SOURCES, DATA_SOURCE_LABELS,
    ENVIRONMENTS, ENVIRONMENT_LABELS, ROUTES, AuthError,
    _auth_file_age_hours, clear_auth, default_site_url, dev_site_url, get_site,
    has_valid_auth, init_preferred_channel_from_settings, parse_routes,
    require_valid_auth, set_preferred_channel, set_site,
)
from paths import EDGE_LOGIN_PROFILE_DIR
from reports import (COMPARE_GROUPS, COMPARE_KEYS, COMPARE_REPORTS, CONSOLIDATE_KEYS,
                     CONSOLIDATE_REPORTS, EXPORT_DISPLAY, EXPORT_REPORTS, PICKER_ORDER,
                     compare_index_for_key, consolidate_index_for_key,
                     enabled_export_reports, export_reports_status,
                     resolve_export_keys)
import artifact_store
import outcome
from gui_endpoint import _api_method      # the shared js_api decorator
import contract
import gui_win32
from task_coordinator import TaskCoordinator
from gui_matrix import GuiMatrixMixin

log = logging.getLogger("tsmis.gui")
# Everything shown in the GUI's log pane is mirrored here, so tsmis.log
# carries the user's view of a run alongside the engine's own diagnostics.
ui_log = logging.getLogger("tsmis.ui")

_CHANNEL_SHORT = {"chromium": "Chromium", "msedge": "Edge", "chrome": "Chrome"}
_SHUTDOWN = object()

class _StampedQueue:
    """Wraps the worker->GUI message queue to tag each TERMINAL message with the claim
    EPOCH it was produced under (P7a exactly-once / P7a-B01). A terminal becomes a
    3-tuple `(kind, payload, epoch)`; every non-terminal message passes through
    unchanged as its `(kind, payload)` 2-tuple. The pump reads the epoch back and the
    dispatch drops a terminal whose epoch is no longer the live claim's, so a straggler
    can't clobber a successor that already took the gate — even a same-kind one, or a
    wildcard `error`/`cancelled`, which a kind-only guard could not distinguish.

    A worker is handed one of these (via `GuiApi._gated_queue`) when it is started under
    a held gate, so all of its messages carry that claim's identity. Workers only ever
    `.put()`; `__getattr__` forwards anything else to the real queue for safety."""

    def __init__(self, q, epoch):
        self._q = q
        self._epoch = epoch

    def put(self, item):
        if item[0] in contract.TERMINAL:
            self._q.put((item[0], item[1], self._epoch))
        else:
            self._q.put(item)

    def __getattr__(self, name):
        return getattr(self._q, name)


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



def _report_list_payload():
    """The report-list metadata the GUI bridge sends the frontend (the Export /
    Consolidate / Compare tab lists). PURE — derived from the report registry, with
    no `self`, no I/O, and no GuiApi construction — so it is BOTH the payload
    `get_initial_state` ships AND a safe, read-only oracle for the catalog parity
    check. (Constructing GuiApi would write the TSN library skeleton via
    `ensure_layout` and start the worker threads — P4-R05.)"""
    _export_fmt = {label: fmt for label, fmt, _spec in EXPORT_REPORTS}
    return {
        # Every export report, with `disabled` marking the app-wide-disabled ones
        # (none today). The UI shows disabled rows GREYED (not hidden). `key` is the
        # stable export-op key the UI passes back (P3 / §C.5); `idx` is the DISPLAY
        # position in this list (not the registry order) — the UI keys off `key`, so
        # idx is metadata only. `group`/`short` (P-D) drive the family-grouped picker.
        # The list is ordered by PICKER_ORDER (flat reports first in the site's order,
        # then the family groups), distinct from the registry order.
        "reports": [{"key": spec.subdir, "idx": pos, "label": label, "fmt": fmt,
                     "disabled": disabled,
                     "group": EXPORT_DISPLAY.get(spec.subdir, (None, None))[0],
                     "short": EXPORT_DISPLAY.get(spec.subdir, (None, None))[1]}
                    for pos, (_i, label, fmt, spec, disabled) in enumerate(sorted(
                        export_reports_status(),
                        key=lambda t: PICKER_ORDER.index(t[3].subdir)))],
        # Each consolidate entry carries its INPUT file format for the tab badge: a
        # module's own INPUT_FMT (the PDF-input consolidators) wins, else the matching
        # export report's format, else Excel.
        "cons_reports": [{"key": CONSOLIDATE_KEYS[i], "label": label,
                          "fmt": (getattr(_mod, "INPUT_FMT", None)
                                  or _export_fmt.get(label, "Excel"))}
                         for i, (label, _mod) in enumerate(CONSOLIDATE_REPORTS)],
        "compare_groups": [{"id": gid, "label": glabel}
                           for gid, glabel in COMPARE_GROUPS],
        "compare_reports": [{"key": COMPARE_KEYS[i], "label": label, "kind": kind,
                             "group": group,
                             "subdir": getattr(_mod, "subdir", None),
                             # The two file-picker labels for "files" comparisons (so
                             # PDF-vs-Excel doesn't mislabel both TSMIS sides).
                             "file_a_label": getattr(_mod, "file_a_label", "TSMIS"),
                             "file_b_label": getattr(_mod, "file_b_label", "TSN")}
                            for i, (label, _mod, kind, group) in enumerate(COMPARE_REPORTS)],
    }


class GuiApi(GuiMatrixMixin):
    """State + bridge behind the WebView UI. Public methods = the JS api."""

    def __init__(self):
        self._window = None
        self._lock = threading.RLock()
        self._q = Queue()            # worker -> GUI messages (gui_worker protocol)
        self._out = Queue()          # GUI -> JS events (ordered)
        self._ready = threading.Event()      # JS finished its first render
        self._started = False        # first get_initial_state happened

        # Task state — the single-flight gate (`_task`), the running matrix job, the
        # matrix queue, and the job-id counter — is OWNED by the TaskCoordinator
        # (P7a). `_task` / `_current_job` / `_queue` / `_job_seq` below are thin
        # property proxies to it, so the rest of gui_api reads them unchanged.
        self._coord = TaskCoordinator(self._lock, self._QUEUE_LIMIT)
        # Worker message kind -> handler (P7a: the _handle dispatch table, replacing
        # the old if/elif chain). Built once; _handle drops a terminal whose claim
        # epoch is no longer the live one (exactly-once) before dispatching, and
        # log.warnings an unknown kind (no silent drop).
        self._dispatch = {
            contract.Msg.LOG: self._emit_log,
            contract.Msg.PROGRESS: self._on_progress,
            contract.Msg.WORKER_STATUS: self._on_worker_status,
            contract.Msg.PREVIEW_SHOT: self._on_preview_shot,
            contract.Msg.ENV_SHOT: self._on_env_shot,
            contract.Msg.ENV_ACCESS: self._on_env_access,
            contract.Msg.ENV_ACCESS_DONE: self._on_env_scan_done,
            contract.Msg.ACTIVE_ENV_DONE: self._on_active_env_done,
            contract.Msg.RESET_DONE: self._on_reset_done,
            contract.Msg.CHROMIUM_DONE: self._on_chromium_done,
            contract.Msg.EXPORT_DONE: self._finish_export,
            contract.Msg.EXPORT_PARTIAL: self._on_export_partial,
            contract.Msg.CONSOLIDATE_DONE: self._finish_consolidate,
            contract.Msg.LOGIN_OPEN: self._on_login_open,
            contract.Msg.LOGIN_SAVED: self._on_login_saved,
            contract.Msg.LOGIN_DEVICE_OK: self._on_login_device_ok,
            contract.Msg.LOGIN_FAILED: self._on_login_failed,
            contract.Msg.CHECK: self._on_check,
            contract.Msg.CHECKS_DONE: self._on_checks_done,
            contract.Msg.CANCELLED: self._on_cancelled,
            contract.Msg.BATCH_PROGRESS: self._on_batch_progress,
            contract.Msg.BATCH_DONE: self._on_batch_done,
            contract.Msg.MATRIX_CELL: self._on_matrix_cell,
            contract.Msg.MATRIX_DONE: self._on_matrix_done,
            contract.Msg.MATRIX_EXPORT_DONE: self._on_matrix_export_done,
            contract.Msg.UPDATE_STATUS: self._on_update_status,
            contract.Msg.ERROR: self._on_error,
        }
        # The quiet background active-env check runs OUTSIDE the single-task gate
        # (it must never block the Log in / Export buttons), so it has its own
        # lightweight flag + a supersede token for a newer env switch.
        self._active_check = False
        self._active_check_seq = 0
        self._active_check_supersede = threading.Event()
        self._fast_run = False       # running export is fast mode (Skip is off)
        self._authed = False
        self._device_ok = False      # silent device sign-in proven to work
        self._login_phase = None     # None|starting|open|saving|cancelling
        self._auth_dot = "unknown"
        self._auth_text = "Checking session…"
        # The persisted EXPORT-browser pick ('' → the Chrome-first default);
        # seed common's preferred channel from it so the first sign-in/export
        # honors it. Edge is the implicit one-click path, never an export pick.
        self._channel = settings.get_export_browser() or BROWSER_CHANNELS[0]
        init_preferred_channel_from_settings()
        # Seed the canonical TSN library's on-disk skeleton (per-report folders
        # + hint files) so a fresh install is self-documenting: the user can find
        # where each report's TSN files go without first importing one. Cheap,
        # offline, idempotent; never block startup on it.
        try:
            import tsn_library
            tsn_library.ensure_layout()
        except Exception as e:                                  # noqa: BLE001
            log.info("tsn_library.ensure_layout skipped: %s: %s",
                     type(e).__name__, (str(e).splitlines() or [""])[0])
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
        self._last_summary = None    # JSON-safe completion summary (persistent card)
        self._last_batch_outcome = None   # {completion, artifact} of the last batch (run_ended)
        self._last_run_folder = None # dated run-folder root of the last export
        self._batch = None           # B3: live Export-Everything progress {label,done,total}
        self._batch_resume = None    # B3: a resumable manifest summary, or None
        self._matrix = None          # matrix recompute progress {phase,row,cell,done,total} | None
        # Matrix-scoped job queue (v0.16.0): matrix actions ENQUEUE instead of
        # racing the single-task gate. A second click queues; jobs run one at a
        # time and auto-advance. The global gate (self._task) still serializes
        # everything — the queue just feeds matrix work into it in order.
        # (_queue / _current_job / _job_seq now live on self._coord — see proxies.)
        self._export_worker = None   # live ExportWorker (screenshot requests)
        # Server-side confirmation for the one destructive op (delete all
        # reports): reset_preview issues a single-use token bound to the
        # include_input flag; start_reset requires it back, so the delete can't
        # run without a preview having been shown first. (token, include_input).
        self._reset_token = None
        self.cancel_event = threading.Event()
        self.skip_event = threading.Event()
        self.pause_event = threading.Event()     # B1: between-route hold
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
                "paused": self.pause_event.is_set(),
                "authed": self._authed,
                "device_ok": self._device_ok,
                "export_browser": self._export_browser_view(),
                "auth_dot": self._auth_dot,
                "auth_text": self._auth_text,
                "login_phase": self._login_phase,
                "login_label": "Re-login" if self._authed else "Log in",
                "checks": {k: dict(v) for k, v in self._checks.items()},
                "checks_running": self._checks_running,
                "days": list_output_days(),
                "can_save_report": bool(self._last_results),
                "last_summary": self._last_summary,
                "batch": self._batch,
                "batch_resume": self._batch_resume,
                "matrix": self._matrix,
                "matrix_queue": [self._job_view(j) for j in self._queue],
                "matrix_current": (self._job_view(self._current_job)
                                   if self._current_job else None),
                "matrix_fast": {"on": settings.get_matrix_fast(),
                                "workers": settings.get("fast_workers")},
                "matrix_formulas": settings.get_matrix_formulas(),
                "day_matrix_formulas": settings.get_day_matrix_formulas(),
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

    def _export_browser_view(self):
        """What will actually do the exporting right now, for the title-bar
        indicator (cheap stat only — never launches a browser or opens the Edge
        profile). Normal: a saved login → the chosen Chromium-class browser;
        else device/primed Edge → one-click; else a prompt to sign in. Fast: the
        chosen Chromium-class browser × workers. (The Settings picker between
        Built-in Chromium and Chrome rides in get_settings, not here.) Called
        under self._lock (from _state_snapshot)."""
        pick = settings.get_export_browser()        # '' | 'chrome' | 'chromium'
        chromium_present = "chromium" in BROWSER_CHANNELS
        cls = pick if pick in ("chrome", "chromium") else (
            "chromium" if chromium_present else "chrome")
        cls_label = CHANNEL_LABELS.get(cls, cls)
        if self._authed:
            normal, dot = f"{cls_label} · saved login", "ok"
        elif self._device_ok:
            normal, dot = "Microsoft Edge · one-click", "ok"
        else:
            normal, dot = "sign in to export", "warn"
        try:
            workers = settings.get("fast_workers")
        except Exception:
            workers = default_worker_count()
        return {"normal": normal, "fast": f"{cls_label} ×{workers}",
                "dot": dot, "cls_label": cls_label}

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

    def _find_own_window(self, title):
        """The top-level window owned by THIS process with `title`, or None
        (gui_win32.find_own_window — PID-matched so we never WM_SETICON another
        process's same-titled window)."""
        return gui_win32.find_own_window(title)

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
            hwnd = None
            deadline = time.monotonic() + 20            # window appears ~1-2s in
            while time.monotonic() < deadline and not hwnd:
                hwnd = self._find_own_window(APP_NAME)
                if not hwnd:
                    time.sleep(0.5)
            if not hwnd:
                log.info("window icon not set (this process's %r window not found)",
                         APP_NAME)
                return
            gui_win32.set_window_icon(hwnd, ico)
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

    # ---- task-state proxies to the TaskCoordinator (P7a) ----------------------
    # Plain forwards (no lock here — the coordinator guards every COMPOUND mutation
    # under the shared RLock; these single-attr reads/writes are protected by the
    # caller's own `with self._lock` where they already mutate state). Keeping the
    # `_task` / `_current_job` / `_queue` / `_job_seq` names lets the rest of gui_api
    # stay untouched while the coordinator is the single owner.
    @property
    def _task(self):
        return self._coord.task

    @_task.setter
    def _task(self, value):
        self._coord.task = value

    @property
    def _current_job(self):
        return self._coord.current_job

    @_current_job.setter
    def _current_job(self, value):
        self._coord.current_job = value

    @property
    def _queue(self):
        return self._coord.queue

    @_queue.setter
    def _queue(self, value):
        # the reorder/remove endpoints rebuild the deque wholesale; forward it to the
        # coordinator (these run under self._lock, which the coordinator shares).
        self._coord.queue = value

    @property
    def _job_seq(self):
        return self._coord._job_seq

    @_job_seq.setter
    def _job_seq(self, value):
        self._coord._job_seq = value

    # ---- worker-queue pump (the old gui_app._handle state machine) ------------

    def _worker_pump(self):
        while True:
            msg = self._q.get()
            # Gated workers post a 3-tuple (kind, payload, epoch); everything else is a
            # 2-tuple (kind, payload). An untagged terminal (a non-gated worker can only
            # post non-terminals) carries epoch None — treated as the live claim's.
            kind, payload = msg[0], msg[1]
            epoch = msg[2] if len(msg) > 2 else None
            try:
                self._handle(kind, payload, epoch)
            except Exception:
                logging.getLogger("tsmis.crash").critical(
                    "uncaught exception handling worker message %r", kind, exc_info=True)

    def _handle(self, kind, payload, epoch=None):
        # Exactly-once gate (R1-R06/R1-R14/P7a-B01): a TERMINAL is acted on only if its
        # claim EPOCH is still the live one. A terminal tagged with a prior claim's epoch
        # is a straggler — its task ended and a successor may now hold the gate (even one
        # of the SAME kind, or a wildcard error/cancelled, which a kind-only guard could
        # not tell apart) — so it is dropped instead of clobbering the successor's
        # gate/job. Workers post exactly one terminal (check_worker_lifecycle), so this
        # is the defensive net that turns a duplicate/late terminal into a safe no-op.
        if kind in contract.TERMINAL and not self._coord.is_live(epoch):
            log.info("lifecycle: dropped a late %r terminal (epoch %r; live gate %r/%r)",
                     kind, epoch, self._coord.task, self._coord.current_epoch())
            return
        handler = self._dispatch.get(kind)
        if handler is None:
            # No silent drop: a worker posted an event kind this sink has no handler
            # for — the worker/bridge protocol drifted (a kind added on one side
            # only). Log it so "one log upload answers it" rather than the event
            # vanishing without a trace.
            log.warning("unhandled worker event kind %r (payload dropped)", kind)
            return
        handler(payload)

    # ---- per-kind handlers (the dispatch table targets) -----------------------
    def _on_progress(self, payload):
        self._emit({"t": "progress", "p": payload})

    def _on_worker_status(self, payload):
        worker, text = payload
        self._emit({"t": "wstatus", "w": worker, "text": text})

    def _on_preview_shot(self, payload):
        worker, b64, note, url = payload
        self._emit({"t": "preview", "w": worker, "img": b64, "note": note, "url": url})

    def _on_export_partial(self, payload):
        # A multi-report run errored partway; keep the completed reports so
        # "Save run report…" still covers them. The "error" message that follows
        # resets the run state. aborted=True: the run did NOT finish every selected
        # report, so it can't read as complete even if the reports that DID finish
        # were each complete (P1-B04).
        summary = (self._build_export_summary(payload, self.cancel_event.is_set(),
                                              aborted=True)
                   if payload else None)
        with self._lock:
            self._last_results = payload
            self._last_summary = summary
            self._last_run_folder = (summary or {}).get("run_folder")

    def _on_login_open(self, payload):
        with self._lock:
            self._login_phase = "open"
        self._set_dot("busy", "Waiting — finish sign-in in the browser")
        self._emit_log("Browser opened. Complete sign-in (SSO + MFA), then click "
                       "‘I've finished logging in’.")
        self._push_state()

    def _on_login_saved(self, payload):
        self._emit_log("Session saved.")
        self._refresh_auth()
        self._end_task()
        self._maybe_autoscan("login")

    def _on_login_device_ok(self, payload):
        # Silent device sign-in works, but the session is device-bound so no file
        # was saved (and none is needed): each export signs itself in.
        with self._lock:
            self._device_ok = True
        self._emit_log("This PC signs in automatically (Microsoft Edge + your "
                       "Windows account). Nothing to save — exports will sign "
                       "themselves in.")
        self._refresh_auth()
        self._end_task()
        self._maybe_autoscan("login")

    def _on_login_failed(self, payload):
        self._emit_log("Login wasn't completed — no new session was saved.")
        self._emit_modal(
            "info", "Login not completed",
            "It doesn't look like you finished signing in, so no session was saved.\n\n"
            "Click 'Log in' and complete sign-in until the TSMIS report page loads — "
            "then either click “I've finished logging in” or just close the "
            "browser window, and your session will be saved.")
        self._refresh_auth()
        self._end_task()

    def _on_check(self, payload):
        key, status, text = payload
        with self._lock:
            if key in self._checks:
                self._checks[key] = {"status": status, "text": text}
        self._push_state()

    def _on_cancelled(self, payload):
        self._emit_log("Cancelled.")
        self._set_dot("ok" if self._authed else "bad", "Idle")
        self._end_task()

    def _end_task(self):
        with self._lock:
            ended = self._task            # capture the kind before clearing it
            self._fast_run = False
            self._login_phase = None
            self._export_worker = None
            self._batch = None
            self._matrix = None
            self.pause_event.clear()      # never leak a paused state across runs
            self._coord.release()         # free the gate + drop the running job (RLock: nested-safe)
        self._refresh_auth()
        # R1-B07: run_ended carries the just-finished run's outcome additively
        # (completion + artifact), so a frontend handler has the result immediately.
        # Export -> the per-run card summary; batch -> the aggregate batch outcome
        # (P1-B02). Other tasks carry nothing (absent fields default to 'complete'
        # on the JS side).
        payload = {"t": "run_ended"}
        if ended == "export" and self._last_summary:
            payload["completion"] = self._last_summary.get("completion")
            payload["artifact"] = self._last_summary.get("artifact")
        elif ended == "batch":
            # P1-B02: start/resume CLEAR _last_batch_outcome, and _on_batch_done sets
            # the current run's outcome. So a None here means this batch ended via the
            # ERROR path (an auth/browser failure emits 'error', not 'batch_done', and
            # _on_error reaches here) before any environment outcome was recorded —
            # report it as FAILED, never the previous (successful) run's outcome.
            bo = self._last_batch_outcome or {"completion": outcome.FAILED,
                                              "artifact": outcome.PREVIOUS_PRESERVED}
            payload["completion"] = bo.get("completion")
            payload["artifact"] = bo.get("artifact")
        self._emit(payload)
        self._push_state()
        # Whatever just ended (matrix or not) frees the gate — pull the next
        # queued matrix job in. No-op when the queue is empty or another task
        # grabs the gate first (re-checked under the lock inside).
        self._try_start_next_matrix_job()

    # ---- single-flight task gate + input validation (bridge hardening) --------

    def _try_claim_task(self, name):
        """Atomically claim the single task slot: returns True if claimed, False
        if another task is already running. Use this instead of a separate
        'check' then later 'set' -- those two race, so two quick clicks (or a
        save dialog between them) could both pass the gate and start two
        workers."""
        return self._coord.try_claim(name)

    def _claim_task_error(self, name):
        """Claim the single task slot, or return WHY it can't be claimed
        (None on success). The quiet background env check deliberately does NOT
        hold the task gate (that would lock the whole UI for its ~20-60 s on
        every device-mode app start) — but it DOES hold the single-instance
        Edge sign-in profile, so a user task launched mid-check used to fail
        with a bare browser-launch error (the one-way exclusion, B8). Now the
        user gets a soft busy message and the check is SUPERSEDED so a retry a
        few seconds later wins."""
        with self._lock:
            active = self._active_check
        if active:
            self._active_check_supersede.set()
            log.info("claim %s deferred: background env check running "
                     "(superseding it)", name)
            return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
        if not self._try_claim_task(name):
            return {"error": "A task is already running."}
        return None

    def _release_task(self):
        """Drop a slot claimed by _try_claim_task before a worker actually
        started (e.g. the user cancelled the save dialog), so the next action
        isn't blocked by a phantom task."""
        self._coord.release()

    def _gated_queue(self):
        """The worker->GUI queue a JUST-CLAIMED worker must post to: a thin proxy that
        tags each terminal with the current claim's epoch (P7a-B01). The gate is held by
        the caller, so `current_epoch()` is this claim's identity; a later/duplicate
        terminal tagged with it is then dropped once a successor has taken the gate. Every
        gate-owning worker is started with this (never the raw `self._q`) so no terminal
        is left untagged."""
        return _StampedQueue(self._q, self._coord.current_epoch())

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
        cancelled = self.cancel_event.is_set()
        summary = self._build_export_summary(results, cancelled) if results else None
        with self._lock:
            self._last_results = results
            self._last_summary = summary
            self._last_run_folder = (summary or {}).get("run_folder")
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
        self._flash_taskbar()
        self._end_task()

    def _build_export_summary(self, results, cancelled, aborted=False):
        """JSON-safe per-report outcome of an export, kept in state so the GUI
        can show a persistent completion card (counts, Open folder, Retry
        failed) after the run instead of relaxing straight to idle.

        Carries the producer/store-owned outcome (P1): each report's `completion`
        + `artifact` (set by the store-swap layer; falls back to the count-derived
        completion for a non-store run), and a RUN-level `completion`/`artifact` the
        card and the run_ended event key on. `aborted` = a multi-report run that did
        NOT finish every selected report (an exception after an earlier one), so its
        completion can't be derived solely from the reports that DID finish."""
        reports = []
        totals = {"saved": 0, "exists": 0, "empty": 0, "skipped": 0, "failed": 0}
        run_folder = None
        completions = []
        for spec, result in results:
            counts = {"saved": result.saved, "exists": len(result.exists),
                      "empty": len(result.empty), "skipped": len(result.user_skipped),
                      "failed": len(result.failed)}
            for k, v in counts.items():
                totals[k] += v
            if result.output_dir and run_folder is None:
                run_folder = str(Path(result.output_dir).parent)
            rcompletion = result.completion or outcome.run_completion(result, cancelled=cancelled)
            completions.append(rcompletion)
            reports.append({"label": spec.label, **counts,
                            "completion": rcompletion,
                            "artifact": result.artifact or outcome.NONE,
                            "failed_routes": list(result.failed),
                            "output_dir": result.output_dir,
                            "report_path": result.report_path})
        # Run-level completion = a REDUCER over the per-report completions, NEVER
        # re-derived from summed counts (where one complete report would mask
        # another's no_data — P1-B04). Run-level artifact = the most telling
        # per-report outcome (a preserved last-good wins over a promotion).
        completion = outcome.reduce_completion(completions, cancelled=bool(cancelled),
                                               aborted=bool(aborted))
        arts = [r["artifact"] for r in reports]
        run_artifact = next((a for a in (outcome.PREVIOUS_PRESERVED, outcome.PROMOTED,
                                         outcome.NEW_UNPROMOTED) if a in arts), outcome.NONE)
        return {"reports": reports, "totals": totals,
                "failed_total": totals["failed"], "cancelled": bool(cancelled),
                "aborted": bool(aborted),
                "completion": completion, "artifact": run_artifact,
                "run_folder": run_folder}

    def _flash_taskbar(self):
        """Flash the taskbar button when a run finishes and the window isn't in
        front, so someone who switched away gets nudged back. Pure ctypes/Win32
        from the gui-pump worker thread -- the same safe, off-STA pattern as the
        icon setter (never the WinForms STA thread). Honors notify_on_finish;
        best-effort, never affects the app."""
        try:
            if not settings.get("notify_on_finish"):
                return
            hwnd = self._find_own_window(APP_NAME)
            if not hwnd:
                return
            gui_win32.flash_taskbar(hwnd)
        except Exception as e:
            log.info("taskbar flash skipped (%s: %s)", type(e).__name__, e)

    def _finish_consolidate(self, result):
        if result.status == "ok":
            for line in result.summary_lines:
                self._emit_log(line)
            self._set_dot("ok" if self._authed else "bad", "Done")
            # Comparisons carry a verdict: surface the quick answer in a
            # dialog too — "everything matches" is the expected outcome
            # between environments, so it deserves more than a log line.
            if result.verdict and result.summary_lines:
                head = result.summary_lines[0]
                if result.verdict == "match":
                    self._emit_modal("info", "Everything matches",
                                     head + "\n\n"
                                     "The saved workbook has the full "
                                     "breakdown and self-checks.")
                elif head.lstrip().startswith("⚠") or "COULD NOT COMPARE" in head:
                    # Some inputs were unreadable: the engine keeps status ok +
                    # verdict "diff" but leads summary_lines[0] with the literal
                    # "⚠ COULD NOT COMPARE EVERYTHING". The rows that WERE
                    # compared may all match, so titling this "Differences
                    # found" would misread — call it incomplete instead.
                    self._emit_modal("warning", "Comparison incomplete",
                                     head + "\n\n"
                                     "Some input files could not be read, so the "
                                     "comparison is not complete. The saved "
                                     "workbook lists exactly what was skipped.")
                else:
                    self._emit_modal("warning", "Differences found",
                                     head + "\n\n"
                                     "Open the saved workbook for the "
                                     "cell-by-cell breakdown (Summary → "
                                     "Comparison → Only-in sheets).")
        elif result.status == "cancelled":
            self._emit_log(result.message or "Cancelled.")
        else:
            self._emit_log(f"ERROR: {result.message}")
            self._emit_modal("error", "Consolidation failed", result.message)
        self._flash_taskbar()
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
        # Also kick the quiet single-combo check for the SELECTED env — lights
        # the Edge one-click chip and fills this env's report flags. Credential-
        # gated, so it's a no-op for a brand-new user with nothing set up.
        self._maybe_active_env_check("startup")

    def _maybe_autoscan(self, reason):
        """Start the env-access scan unprompted — once per session, only when
        a login is available (a no-login scan would just log six failures at
        every launch), never preempting other work, and only when the matching
        Settings toggle allows it. The trigger has its own toggle: after app
        start vs after a sign-in (the start one is off by default)."""
        key = ("env_check_after_start" if reason == "startup"
               else "env_check_after_signin")
        try:
            if not settings.get(key):
                return
        except Exception as e:
            log.info("autoscan skipped: settings unreadable (%s: %s)",
                     type(e).__name__, str(e).splitlines()[0] if str(e) else "")
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

    def _maybe_active_env_check(self, reason):
        """Quietly check the CURRENTLY selected env in the background (app start
        + env switch): prove Edge one-click / device sign-in (lights the chip)
        and refresh that env's report availability (the Export-tab + matrix
        flags). Runs only when a credential path likely exists — a saved login
        OR the Edge profile is primed — so brand-new users trigger no pointless
        network hits, and NEVER while another task or check is running (it must
        not touch the single-task gate, and the Edge profile opens one at a time).
        Quiet on every failure."""
        try:
            primed = (EDGE_LOGIN_PROFILE_DIR.is_dir()
                      and any(EDGE_LOGIN_PROFILE_DIR.iterdir()))
        except OSError:
            primed = False
        if not (has_valid_auth() or primed):
            return
        src, env = get_site()
        with self._lock:
            if self._task or self._active_check:
                return
            self._active_check = True
            self._active_check_seq += 1
            seq = self._active_check_seq
            self._active_check_supersede.clear()
        log.info("active env check: %s (%s-%s)", reason, src, env)
        ActiveEnvCheckWorker(self._q, src, env, seq,
                             supersede=self._active_check_supersede).start()

    def _on_active_env_done(self, payload):
        """The quiet active-env check finished. Drop a stale result (a newer env
        switch bumped the seq and owns the flag); otherwise clear the flag, light
        the Edge one-click chip when sign-in worked via device mode, and refresh
        the matrix env flags."""
        via_device = False
        with self._lock:
            if payload.get("seq") != self._active_check_seq:
                return                  # superseded; the newer check owns the flag
            self._active_check = False
            if payload.get("via_device"):
                self._device_ok = True
                via_device = True
        if via_device:
            self._refresh_auth()
        self._push_state()
        self._emit({"t": "matrix_refresh"})   # re-overlay the matrix env flags

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
        revert = payload.get("revert", False)
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
            if revert:
                self._emit_log("Revert: no earlier version was found to go back to.")
            else:
                self._emit_log(f"You're on the latest version (v{__version__}).")
        elif phase == "staged":
            if revert:
                self._emit_log(f"Previous version v{ver} is downloaded and ready — "
                               f"click ‘Restart to revert’ when you're done working "
                               f"(the app closes, reinstalls v{ver}, and reopens).")
            else:
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
        # An error that ENDS A MATRIX JOB (only auth / browser-not-found reach
        # here from the matrix workers — both unrecoverable this session) would
        # hit every queued matrix job the same way. Drop the pending queue so it
        # can't cascade into a modal storm; the user fixes the cause + re-queues.
        with self._lock:
            if kind == "auth":
                self._authed = False
            # Clear the pending queue only when the error ended a MATRIX job —
            # those remaining jobs would hit the same failure. A non-matrix auth
            # failure (e.g. a login) leaves queued matrix jobs alone; the first one
            # to run then self-clears the rest if the problem persists.
            was_matrix = self._current_job is not None
            cleared = len(self._queue) if was_matrix else 0
            if was_matrix:
                self._queue.clear()
        if kind == "auth":
            clear_auth()
        if cleared:
            self._emit_log(f"Cleared {cleared} queued matrix job(s) — fix the "
                           "problem above, then re-queue them.")
        if kind == "auth":
            self._set_dot("bad", "No saved login — click Log in")
            self._emit_modal("warning", "Login needed",
                             f"{message}\n\nClick 'Log in' to sign in again.")
        else:
            self._set_dot("bad", "Error")
            self._emit_modal("error", "Error",
                             f"{message}\n\nMore details are in the log file.")
        # P1-B02 (narrowed): a batch that FAILS mid-run (auth/browser) still finished
        # some environments before the fatal error (BatchWorker marked them done + kept
        # their stores). Preserve that progress so the terminal reads PARTIAL when ≥1 env
        # completed, reserving FAILED for a batch that completed zero. _last_batch_outcome
        # is None here (start/resume cleared it; the fatal path emits 'error', not
        # 'batch_done'); _batch carries the live done-count from the last batch_progress.
        if self._task == "batch" and self._last_batch_outcome is None:
            done = (self._batch or {}).get("done", 0)
            self._last_batch_outcome = {
                "completion": outcome.PARTIAL if done else outcome.FAILED,
                "artifact": outcome.PREVIOUS_PRESERVED}
        self._flash_taskbar()        # a task ended (with an error) — nudge if away
        self._end_task()
        if was_matrix:               # the failed cell stays as-is; refresh both grids
            self._emit({"t": "matrix_refresh"})

    # ======================= JS-callable api methods ==========================

    @_api_method
    def get_initial_state(self):
        if not self._started:
            self._started = True
            self._refresh_auth()
            self._start_checks_locked()
            self._start_update_check()       # quiet unless an update exists
            self._batch_resume = self._pending_batch()   # offer to resume an interrupted batch
        return {
            "app_name": APP_NAME,
            "version": __version__,
            "output_root": str(OUTPUT_ROOT),
            "log_dir": str(LOG_DIR),
            # Bridge enum SSOT (P7a): the canonical task / terminal-kind / env-access
            # vocabulary, so ui/contract.js (P9) is checked against the backend, not
            # re-hardcoded. See scripts/contract.py.
            "contract": contract.initial_state_enums(),
            # The report-list metadata (Export / Consolidate / Compare tab lists) is
            # built by the PURE module-level `_report_list_payload()` so it is also a
            # safe read-only oracle for the catalog parity check (P4-R05).
            **_report_list_payload(),
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
            "batch_resume": self._batch_resume,
            "batch_dest": settings.get_batch_dest(),
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
    def set_export_browser(self, channel):
        """Pick which Chromium-class browser does normal exports / fast mode /
        the login capture. Only 'chrome' or 'chromium' (Edge stays the implicit
        one-click sign-in path + ultimate fallback, not a user-pickable export
        browser). Persisted across sessions."""
        if channel in ("", "auto"):
            channel = ""                     # clear → auto (Chrome-first default)
        elif channel not in ("chromium", "chrome"):
            return {"error": f"not a selectable export browser: {channel}"}
        settings.set_export_browser(channel)
        with self._lock:
            self._channel = channel or BROWSER_CHANNELS[0]
        set_preferred_channel(channel or None)   # None → default; Edge stays a fallback
        self._emit_log("Export browser set to "
                       + (CHANNEL_LABELS[channel] if channel else "automatic (Chrome-first)")
                       + " (Microsoft Edge is still used for one-click sign-in "
                       "and as a fallback).")
        self._push_state()
        return {"ok": True}

    @_api_method
    def set_site(self, source, environment):
        # Safe even while the env scan runs: scanner threads pin their own
        # targets via common.set_thread_site and never touch this selection.
        set_site(source=source, environment=environment)
        src, env = get_site()
        self._emit_log(f"Site set to {DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]} "
                       "(used by the next sign-in or export).")
        # Quietly re-check the newly selected env in the background (proves
        # one-click here + refreshes this env's report flags). Credential-gated.
        self._maybe_active_env_check("site_switch")
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
            revert = self._update.get("revert", False)
        if phase in ("checking", "downloading", "applying"):
            return {"ok": True}              # already busy with update work
        if phase == "staged":
            self._emit_log("A download is already ready — click "
                           + ("‘Restart to revert’" if revert else "‘Restart to update’")
                           + " in the title bar to install it.")
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
        # Constrain to our own GitHub repo: release_url is API-sourced (html_url),
        # and webbrowser.open on an attacker-influenced value could launch an
        # arbitrary handler. safe_release_url falls back to the constant page.
        url = updater.safe_release_url(self._update.get("url"))
        ui_log.info("opening release page: %s", url)
        webbrowser.open(url)
        return {"ok": True}

    @_api_method
    def revert_to_previous(self):
        """Download + stage the PREVIOUS full release and (after the user clicks
        Restart) swap to it — the Settings "revert to previous version" control.
        Reuses the one-click update pipeline (resolve a specific older tag, then
        the same verify/stage/swap), so the riskiest code is unchanged. Only a
        writable packaged install can self-swap; a read-only / dev install must
        download the older zip from the releases page instead. The download is
        allowed mid-run (network + disk only, like a forward update); the restart
        that applies it stays gated on no task (update_apply)."""
        if updater.update_support()[0] != "ok":
            return {"error": "This install can't revert itself — open the releases "
                             "page and extract an earlier version into a writable folder."}
        with self._lock:
            phase = self._update.get("phase")
            if phase in ("checking", "downloading", "applying"):
                return {"error": "An update or revert is already in progress."}
            if phase == "staged":
                # Don't silently discard a download the user already staged.
                return {"error": "A download is already staged — restart to apply it, "
                                 "or reopen the app first, then revert."}
            self._update = {"phase": "downloading", "progress": 0, "revert": True}
        ui_log.info("revert: user chose 'Revert to previous version'")
        self._emit_log("Reverting to the previous version — finding it and downloading…")
        self._push_state()
        UpdateWorker(self._q, "revert", manual=True).start()
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
    def start_export(self, report_keys, routes_text, fast, workers,
                     auto_consolidate=False):
        # Validate inputs BEFORE claiming the task slot (pure, no shared state),
        # then claim atomically -- so two quick clicks can't both pass the gate
        # and launch two export runs (the old check-then-set raced). Selection is
        # by stable export-op KEY now (P3 / §C.5), resolved ALL-OR-NOTHING: any
        # unknown/disabled/duplicate key rejects the whole selection (never a
        # narrower run), never mis-resolved by list position.
        specs, invalid = resolve_export_keys(
            report_keys if isinstance(report_keys, (list, tuple)) else [])
        if invalid:
            return {"error": "One or more selected reports aren't available — "
                             "reopen the tab and pick again."}
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

        err = self._claim_task_error("export")
        if err:
            return err
        with self._lock:
            self._fast_run = n_workers > 1
            self._last_summary = None       # the previous run's card clears now
            self._last_run_folder = None
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()

        names = ", ".join(s.label for s in specs)
        msg = f"Starting export: {names}"
        if len(run_routes) != len(ROUTES):
            msg += f"   ·   {len(run_routes)} routes"
        if n_workers > 1:
            msg += f"   ·   FAST MODE ({n_workers} browsers)"
        if auto_consolidate:
            msg += "   ·   auto-consolidate"
        self._emit_log(msg)
        self._set_dot("busy",
                      f"Exporting {len(specs)} report(s)…" if len(specs) > 1
                      else f"Exporting {specs[0].label}…")
        # `workers` tells the UI how many live browser-status rows to show.
        self._emit({"t": "run_started", "mode": "export", "label": "Working…",
                    "workers": n_workers})
        self._push_state()
        worker = ExportWorker(specs, self._gated_queue(), self.cancel_event, self.skip_event,
                              workers=n_workers, routes=run_routes,
                              pause_event=self.pause_event,
                              auto_consolidate=bool(auto_consolidate))
        with self._lock:
            self._export_worker = worker
        worker.start()
        return {"ok": True}

    @_api_method
    def retry_failed(self):
        """Re-run only the routes that FAILED in the last export. Reuses the
        normal export engine (resume skips routes already saved, so only the
        genuinely-missing ones are re-pulled). Serial (workers=1) so it works
        without a saved login, mirroring the engine's own end-of-run retry."""
        with self._lock:
            results = list(self._last_results or [])
        failing = [(spec, list(result.failed)) for spec, result in results if result.failed]
        if not failing:
            return {"error": "There are no failed routes to retry."}
        specs = [spec for spec, _ in failing]
        # The union of every failing report's failed routes, run against all of
        # them. Almost always one report (single-report runs are the norm); when
        # several reports failed DIFFERENT routes, resume idempotency means each
        # report re-pulls only its own still-missing files and skips the rest —
        # so the retry stays complete without the engine needing per-spec lists.
        routes = sorted({r for _, fr in failing for r in fr})

        err = self._claim_task_error("export")
        if err:
            return err
        with self._lock:
            self._fast_run = False
            self._last_summary = None
            self._last_run_folder = None
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()
        self._emit_log(f"Retrying {len(routes)} failed route(s): {', '.join(routes)}")
        self._set_dot("busy", "Retrying failed routes…")
        self._emit({"t": "run_started", "mode": "export",
                    "label": "Retrying failed routes…", "workers": 1})
        self._push_state()
        worker = ExportWorker(specs, self._gated_queue(), self.cancel_event, self.skip_event,
                              workers=1, routes=routes, pause_event=self.pause_event)
        with self._lock:
            self._export_worker = worker
        worker.start()
        return {"ok": True}

    @_api_method
    def open_run_folder(self):
        """Open the output folder of the run that just finished (the dated
        run-folder root). The path is engine-produced under OUTPUT_ROOT, so no
        extra validation is needed."""
        with self._lock:
            folder = self._last_run_folder
        if not folder:
            return {"error": "No recent run to open."}
        self._open_folder(Path(folder))
        return {"ok": True}

    # ---- batch: Export Everything (B3) ----------------------------------------

    @staticmethod
    def _parse_env_keys(env_keys):
        """Validate JS-supplied 'src-env' keys into ordered, de-duped (src, env)
        combos; unknown keys are dropped."""
        out, seen = [], set()
        for k in (env_keys if isinstance(env_keys, (list, tuple)) else []):
            parts = str(k).split("-")
            if (len(parts) == 2 and parts[0] in DATA_SOURCES
                    and parts[1] in ENVIRONMENTS and (parts[0], parts[1]) not in seen):
                seen.add((parts[0], parts[1]))
                out.append((parts[0], parts[1]))
        return out

    def _pending_batch(self):
        """A resumable batch (a saved manifest with pending environments) as a
        small UI summary, or None."""
        m = batch_manifest.load()
        if m and batch_manifest.pending(m):
            return {"reports": list(m.get("reports", [])),
                    "pending": len(batch_manifest.pending(m)),
                    "total": len(m.get("steps", []))}
        return None

    @_api_method
    def start_batch_export(self, report_keys, env_keys, fast, workers,
                           auto_consolidate=False):
        """B3 Export Everything: export the selected report types across the
        selected environments, sequentially, with a persistent manifest so it can
        resume across restarts. Reports travel by stable export-op KEY (P3 / §C.5):
        the manifest persists keys, so a registry re-order can't resume the wrong
        report (F7). Resolved ALL-OR-NOTHING: any unknown/disabled/duplicate key
        rejects the whole selection (never a narrower batch)."""
        specs, invalid = resolve_export_keys(
            report_keys if isinstance(report_keys, (list, tuple)) else [])
        if invalid:
            return {"error": "One or more selected report types aren't available — "
                             "reopen the tab and pick again."}
        if not specs:
            return {"error": "Tick at least one report type to export."}
        keys = [s.subdir for s in specs]   # canonical export-op keys (validated, enabled)
        combos = self._parse_env_keys(env_keys)
        if not combos:
            return {"error": "Pick at least one environment."}
        n_workers = 1
        if fast:
            try:
                n_workers = max(2, min(int(workers), MAX_WORKERS))
            except (TypeError, ValueError):
                n_workers = max(2, default_worker_count())
        err = self._claim_task_error("batch")
        if err:
            return err
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()
        dest = settings.get_batch_dest()
        manifest = batch_manifest.build(keys, combos, bool(fast), n_workers,
                                        bool(auto_consolidate), dest=dest)
        batch_manifest.save(manifest)
        with self._lock:
            self._fast_run = n_workers > 1
            self._batch_resume = None
            self._last_summary = None     # a batch supersedes the last export card
            self._last_run_folder = None
            self._last_batch_outcome = None   # P1-B02: never reuse a prior run's outcome
        msg = (f"Starting Export Everything: {len(keys)} report type(s) "
               f"across {len(combos)} environment(s)")
        if n_workers > 1:
            msg += f"   ·   FAST MODE ({n_workers} browsers)"
        if auto_consolidate:
            msg += "   ·   auto-consolidate"
        self._emit_log(msg)
        self._emit_log(f"  Destination: {dest}")
        self._set_dot("busy", "Export Everything…")
        self._emit({"t": "run_started", "mode": "batch", "label": "Working…",
                    "workers": n_workers})
        self._push_state()
        BatchWorker(manifest, self._gated_queue(), self.cancel_event, self.skip_event,
                    self.pause_event).start()
        return {"ok": True}

    @_api_method
    def report_library_info(self):
        """The always-current destination + per-report freshness, for the
        Export Everything tab's library view (B3). Pure filesystem stat."""
        dest = settings.get_batch_dest()
        reports = [(label, spec.subdir)
                   for _i, label, _fmt, spec in enabled_export_reports()]
        return {"dest": dest, "reports": report_library.report_ages(dest, reports)}

    @_api_method
    def set_batch_dest(self, path):
        """Set (or, with an empty path, reset) the Export Everything destination."""
        dest = settings.set_batch_dest(path)
        self._emit_log(f"Export Everything destination: {dest}")
        self._push_state()
        return {"dest": dest}

    @_api_method
    def pick_batch_dest(self):
        """Native folder dialog to choose the always-current destination."""
        cur = settings.get_batch_dest()
        start = cur if Path(cur).is_dir() else str(OUTPUT_ROOT)
        picked = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=start)
        if not picked:
            return {"cancelled": True}
        path = picked[0] if isinstance(picked, (list, tuple)) else picked
        dest = settings.set_batch_dest(str(path))
        self._emit_log(f"Export Everything destination: {dest}")
        self._push_state()
        return {"dest": dest}

    @_api_method
    def resume_batch(self):
        """Continue a saved, interrupted batch from its next pending environment."""
        m = batch_manifest.load()
        if not m or not batch_manifest.pending(m):
            return {"error": "There's no saved batch to resume."}
        err = self._claim_task_error("batch")
        if err:
            return err
        self.cancel_event.clear()
        self.skip_event.clear()
        self.pause_event.clear()
        with self._lock:
            self._fast_run = bool(m.get("fast"))
            self._batch_resume = None
            self._last_summary = None
            self._last_run_folder = None
            self._last_batch_outcome = None   # P1-B02: never reuse a prior run's outcome
        pend, total = len(batch_manifest.pending(m)), len(m.get("steps", []))
        self._emit_log(f"Resuming Export Everything — {pend} of {total} "
                       "environment(s) left.")
        self._set_dot("busy", "Export Everything…")
        self._emit({"t": "run_started", "mode": "batch", "label": "Working…",
                    "workers": m.get("workers", 1) if m.get("fast") else 1})
        self._push_state()
        BatchWorker(m, self._gated_queue(), self.cancel_event, self.skip_event,
                    self.pause_event).start()
        return {"ok": True}

    @_api_method
    def discard_batch(self):
        """Forget a saved, interrupted batch (the user doesn't want to resume)."""
        batch_manifest.clear()
        with self._lock:
            self._batch_resume = None
        self._emit_log("Discarded the saved Export Everything batch.")
        self._push_state()
        return {"ok": True}

    def _on_batch_progress(self, payload):
        with self._lock:
            self._batch = {"label": payload.get("label", ""),
                           "done": payload.get("done", 0),
                           "total": payload.get("total", 0),
                           "src": payload.get("src"),
                           "env": payload.get("env"),
                           "steps": payload.get("steps", [])}
        self._push_state()

    def _on_batch_done(self, payload):
        done, total = payload.get("done", 0), payload.get("total", 0)
        if payload.get("complete"):
            batch_manifest.clear()
            self._emit_log(f"Export Everything finished — all {total} "
                           "environment(s) done.")
        elif payload.get("cancelled"):
            self._emit_log(f"Export Everything stopped — {done} of {total} "
                           "environment(s) done. Re-open the app to resume the rest.")
        else:
            self._emit_log(f"Export Everything ended — {done} of {total} "
                           "environment(s) done; some were left pending (see the log).")
        # Aggregate batch outcome for run_ended (P1-B02): complete only when every
        # environment finished; else partial (some kept last-good) / cancelled.
        bcompletion = payload.get("completion") or (
            outcome.COMPLETE if payload.get("complete")
            else outcome.CANCELLED if payload.get("cancelled") else outcome.PARTIAL)
        bartifact = (outcome.PROMOTED if bcompletion == outcome.COMPLETE
                     else outcome.PREVIOUS_PRESERVED)
        resume = self._pending_batch()        # recompute outside the lock
        with self._lock:
            self._batch = None
            self._batch_resume = resume
            self._last_batch_outcome = {"completion": bcompletion, "artifact": bartifact}
        self._flash_taskbar()
        self._end_task()

    @_api_method
    def request_preview(self, worker_no):
        """Ask browser `worker_no` (1-based) for a live screenshot; it answers
        with a 'preview' event at its next safe poll point (≤ ~5 s during a
        report wait; a long download can delay it until the next route)."""
        with self._lock:
            worker = self._export_worker
            running = self._task == "export" or (
                self._task == "matrix" and self._current_job is not None
                and self._current_job.get("kind") == "export")
        if not running or worker is None:
            return {"error": "No export is running."}
        worker.request_screenshot(worker_no)
        ui_log.info("preview requested for browser %s", worker_no)
        return {"ok": True}

    def _matrix_export_running(self):
        """True while a matrix re-EXPORT job is the running task. Pause/Skip + live
        preview apply to it exactly like a normal export — MatrixBatchExportWorker
        forwards pause_event/skip_event to the underlying ExportWorker."""
        with self._lock:
            return (self._task == "matrix" and self._current_job is not None
                    and self._current_job.get("kind") == "export")

    @_api_method
    def skip_route(self):
        # Read+set under the lock: the unlocked pair could race _end_task + the
        # matrix queue advance and stamp the NEXT job with a skip meant for the
        # one that just ended (BUG-10). The queue advance clears the control
        # events under its claim, so a stale set can no longer leak forward.
        with self._lock:
            hit = self._task == "export" or self._matrix_export_running()
            if hit:
                self.skip_event.set()
        if hit:
            self._emit_log("Skip requested — will move on once the current wait ends.")
        return {"ok": True}

    @_api_method
    def cancel_run(self):
        # Tasks that honor cancel_event between steps. (login has its own cancel;
        # envcheck is a single short headless verify that can't stop partway.)
        # Read+set under the lock (BUG-10): unlocked, this could race _end_task
        # and the matrix queue advance, cancelling the NEXT queued job instead of
        # the one the user targeted.
        with self._lock:
            task = self._task
            if task in ("export", "batch", "consolidate", "compare", "chromium",
                        "envscan", "reset", "matrix"):
                self.cancel_event.set()
                self.pause_event.clear()  # unblock a paused run so cancel lands
        if task in ("export", "batch", "consolidate", "compare", "chromium",
                    "envscan", "reset", "matrix"):
            self._emit_log("Cancel requested…")
        elif task == "envcheck":
            self._emit_log("The environment check can't be stopped partway — "
                           "it'll finish in a moment.")
        return {"ok": True}

    @_api_method
    def pause_or_resume(self):
        """Toggle a between-routes hold on the running export (B1). The current
        route(s) finish, then the run holds until Resume. Unlike Skip, pause is
        well-defined in fast mode (every browser parks before its next route), so
        it works there too. Also pauses an Export Everything batch (between
        routes, and between environments) and a matrix re-export. No-op unless one
        is running."""
        # Toggle under the lock (BUG-10): matches _end_task's locked
        # pause_event.clear(), so a toggle can't interleave a run transition.
        with self._lock:
            if (self._task not in ("export", "batch")
                    and not self._matrix_export_running()):
                return {"error": "No export is running."}
            resumed = self.pause_event.is_set()
            if resumed:
                self.pause_event.clear()
            else:
                self.pause_event.set()
        if resumed:
            self._emit_log("Resumed.")
        else:
            self._emit_log("Paused — finishing the current route(s), then holding. "
                           "Click Resume to continue.")
        self._push_state()
        return {"ok": True}

    # ---- login -----------------------------------------------------------------

    @_api_method
    def start_login(self):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("login")   # claim + bump epoch (gate already checked)
            self._login_phase = "starting"
        self.login_done.clear()
        self.login_cancel.clear()
        self._set_dot("busy", "Signing in…")
        self._emit_log("Starting sign-in…")
        self._push_state()
        LoginWorker(self._gated_queue(), self.login_done, self.login_cancel).start()
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
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("envcheck")   # claim + bump epoch (gate already checked)
        src, env = get_site()
        label = f"{DATA_SOURCE_LABELS[src]} / {ENVIRONMENT_LABELS[env]}"
        self._emit_log(f"Verifying environment: opening TSMIS on {label}…")
        self._set_dot("busy", f"Checking {label}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Checking {label}…"})
        self._push_state()
        EnvCheckWorker(self._gated_queue()).start()
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
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("envscan")   # claim + bump epoch (gate already checked)
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
        EnvScanWorker(self._gated_queue(), self.cancel_event).start()
        return {"ok": True}

    def _on_env_access(self, payload):
        """One site's verdict → state snapshot + a log line. The quiet
        background active-env check sets `quiet` to update the flags silently
        (no per-combo log line)."""
        entry = dict(payload)
        quiet = entry.pop("quiet", False)
        entry["checked_at"] = time.strftime("%H:%M")
        with self._lock:
            self._env_access[entry["key"]] = entry
        if not quiet:
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
    def consolidate_info(self, report_key, day):
        row = self._pick_report(CONSOLIDATE_REPORTS, consolidate_index_for_key(report_key))
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
    def open_consolidate_input(self, report_key):
        row = self._pick_report(CONSOLIDATE_REPORTS, consolidate_index_for_key(report_key))
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
    def start_consolidate(self, report_key, day):
        # Validate the report KEY + day BEFORE claiming the slot -- otherwise a bad
        # key would leave self._task set, wedging the task gate "consolidate"
        # forever (every later action blocked until restart).
        row = self._pick_report(CONSOLIDATE_REPORTS, consolidate_index_for_key(report_key))
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        try:
            day = self._safe_day(day)
        except ValueError as e:
            return {"error": str(e)}
        label, mod = row
        err = self._claim_task_error("consolidate")
        if err:
            return err
        self.cancel_event.clear()
        self._emit_log(f"Starting consolidation: {label}" + (f"   ·   {day}" if day else ""))
        self._set_dot("busy", f"Consolidating {label}…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": f"Consolidating {label}…"})
        self._push_state()
        # Overwrite was resolved by the UI before start (consolidate_info +
        # confirm dialog), so the injected callback just says yes.
        ConsolidateWorker(mod.consolidate, self._gated_queue(), self.cancel_event,
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
        # F9: the comparator writes to a temp path; commit_workbook validates + os.replaces
        # it onto the picked name (compare_core untouched). For mode="both" the VALUES
        # workbook is the single transactional artifact (committed first) and the formulas
        # sibling is best-effort, so an interrupted run never leaves a values copy without
        # its twin (or a truncated picked file). The OS save dialog already confirmed the
        # destination, so the inner confirm is a pass-through.
        def committed(events=None, confirm_overwrite=None, day=None):
            return artifact_store.commit_workbook(
                out,
                lambda tmp: run_fn(tmp, events=events,
                                   confirm_overwrite=lambda _p: True, day=day),
                twin=(mode == "both"), expect_sheet="Comparison")
        ConsolidateWorker(committed, self._gated_queue(), self.cancel_event,
                          lambda _p: True).start()
        return {"ok": True}

    def _begin_compare(self, label, mode, save_dir, suggest, build):
        """Shared claim → save-dialog → launch tail for the two compare endpoints
        (P7b unify of start_compare / start_compare_env). Claims the single-task gate
        BEFORE the blocking save dialog so a second click is rejected at once. `suggest`
        is a *lazy* default-name callable evaluated INSIDE the claim (preserving the
        pre-P7b ordering where suggest_name ran after the claim), so a suggest-name /
        dialog / launch-prep error releases the gate and can never wedge it.
        `build(out_path, events, confirm_overwrite, day)` is the comparator call
        (`mod.compare` / `adapter.compare_folders`)."""
        err = self._claim_task_error("compare")
        if err:
            return err
        try:
            out = self._save_dialog_for_compare(save_dir, suggest())
            if out is None:
                self._release_task()
                return {"cancelled": True}
            return self._launch_compare(label, mode, out, build)
        except Exception:
            self._release_task()        # a suggest-name/dialog/launch error must not wedge the gate
            raise

    @_api_method
    def start_compare(self, report_key, tsmis_path, tsn_path,
                      want_formulas=True, want_values=False):
        row = self._pick_report(COMPARE_REPORTS, compare_index_for_key(report_key))
        if row is None:
            return {"error": "That comparison isn't available — please reopen the tab."}
        label, mod, kind, _group = row[:4]
        if kind != "files":
            return {"error": "This comparison type takes folders, not files."}
        if not tsmis_path or not tsn_path:
            return {"error": "Pick both files first (a TSMIS and a TSN workbook)."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live formulas)."}
        return self._begin_compare(
            label, mode, Path(tsmis_path).parent,
            lambda: mod.suggest_name(tsmis_path),
            lambda out_path, events=None, confirm_overwrite=None, day=None:
                mod.compare(tsmis_path, tsn_path, out_path, events=events,
                            confirm_overwrite=confirm_overwrite, mode=mode))

    @_api_method
    def get_compare_folders(self, report_key):
        """Run folders that contain the chosen cross-env report (the compare
        folder dropdowns call this on report-type change so only usable runs are
        offered — A2). 'files'-kind comparisons and adapters without a subdir
        return all folders (their dropdowns aren't shown). Pure filesystem stat;
        no task lock, no browser."""
        row = self._pick_report(COMPARE_REPORTS, compare_index_for_key(report_key))
        if row is None:
            return {"folders": list_output_days()}
        _label, adapter, kind, _group = row[:4]
        subdir = getattr(adapter, "subdir", None)
        if kind != "folders" or not subdir:
            return {"folders": list_output_days()}
        return {"folders": list_output_days_for_report(subdir)}

    @_api_method
    def start_compare_env(self, report_key, dir_a, dir_b,
                          want_formulas=True, want_values=False):
        """Cross-environment comparison: two run folders (names from the
        dropdowns resolve under output/; Browse… hands in absolute paths)."""
        row = self._pick_report(COMPARE_REPORTS, compare_index_for_key(report_key))
        if row is None:
            return {"error": "That comparison isn't available — please reopen the tab."}
        label, adapter, kind, _group = row[:4]
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
        # A2 server-side guard mirroring the filtered dropdowns: a run folder
        # picked from the list must actually hold this report's export (Browse…
        # absolute paths are the user's explicit choice and skip this).
        subdir = getattr(adapter, "subdir", None)
        if subdir:
            for raw, p in ((dir_a, pa), (dir_b, pb)):
                if Path(raw).is_absolute():
                    continue
                sub = p / subdir
                try:
                    present = sub.is_dir() and any(sub.iterdir())
                except OSError:
                    present = False
                if not present:
                    return {"error": f"The folder “{raw}” has no {label} export "
                                     "to compare — pick one that does."}
        mode = self._compare_mode(want_formulas, want_values)
        if mode is None:
            return {"error": "Tick at least one output (values and/or live formulas)."}
        import compare_env
        compare_env.DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
        return self._begin_compare(
            label, mode, compare_env.DEFAULT_OUT_DIR,
            lambda: adapter.suggest_name(pa, pb),
            lambda out_path, events=None, confirm_overwrite=None, day=None:
                adapter.compare_folders(pa, pb, out_path, events=events,
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
        except OSError as e:
            # best-effort sizing — the Settings panel still renders (downloaded may
            # read False / 0 MB); log so a recurring read failure is diagnosable (P7a).
            log.info("settings: couldn't inspect the downloaded Chromium (%s: %s)",
                     type(e).__name__, e)
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
            # Which Chromium-class browser does exports/fast/login-capture. The
            # Settings control only matters when BOTH exist (else it's just info);
            # Edge is the implicit one-click path, never listed here.
            "export_browser": {
                "value": settings.get_export_browser() or "auto",
                "chrome_ok": self._checks.get("browser_chrome", {}).get("status") == "ok",
                "chromium_present": "chromium" in BROWSER_CHANNELS,
                "labels": {c: CHANNEL_LABELS[c] for c in ("chromium", "chrome")},
            },
            "tsn_library": self._tsn_library_status(),
            "tsn_library_root": str(TSN_LIBRARY_ROOT),   # the on-disk TSN home

            "meta": {
                "version": __version__,
                "build": "portable app" if is_frozen() else "development run",
                "variant": ("with built-in browser"
                            if "chromium" in BROWSER_CHANNELS else "system browser"),
                "data_root": str(DATA_ROOT),
                "output_root": str(OUTPUT_ROOT),
                "log_file": str(active_log_file()),
                "failures_dir": str(FAILURES_DIR),
                "auth_state": auth_state,
                "max_workers": MAX_WORKERS,
                # "ok" = writable packaged install (can self-update/revert);
                # "link" = read-only; "off" = dev run. Gates the Revert control.
                "update_support": updater.update_support()[0],
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

    @_api_method
    def apply_site_preset(self, preset):
        """Point ALL six site addresses at a preset in one click: 'dev' (the
        development host tsmis-dev.dot.ca.gov — where Intersection reports are
        available) or 'prod' (clear every override → the built-in production
        addresses). Returns the refreshed site-URL rows for the Settings list."""
        if preset not in ("dev", "prod"):
            return {"error": "Unknown site preset."}
        failed = []
        for src in DATA_SOURCES:
            for env in ENVIRONMENTS:
                url = dev_site_url(src, env) if preset == "dev" else ""
                try:
                    settings.set_site_url(src, env, url)
                except ValueError as e:
                    failed.append(f"{src}-{env}: {e}")
        if failed:
            self._emit_log("Some site addresses couldn't be set: " + "; ".join(failed))
            return {"error": "Some addresses couldn't be set — see the log.",
                    "site_urls": self._site_url_rows()}
        self._emit_log("All site addresses set to the "
                       + ("development site (tsmis-dev.dot.ca.gov) — Intersection "
                          "reports are available there." if preset == "dev"
                          else "built-in production addresses."))
        self._push_state()
        return {"ok": True, "site_urls": self._site_url_rows()}

    # ---- Built-in Chromium download / delete -----------------------------------

    def _start_chromium(self, action, start_log):
        with self._lock:
            if self._task:
                return {"error": "A task is already running."}
            if self._active_check:
                self._active_check_supersede.set()   # the check yields; retry wins
                return {"error": "Checking the sign-in status in the background — try again in a few seconds."}
            self._coord.claim_direct("chromium")   # claim + bump epoch (gate already checked)
        self.cancel_event.clear()
        self._emit_log(start_log)
        self._set_dot("busy", "Working on the Built-in Chromium…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": ("Downloading the Built-in Chromium…"
                              if action == "download" else
                              "Removing the Built-in Chromium…")})
        self._push_state()
        ChromiumWorker(self._gated_queue(), action, self.cancel_event).start()
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
            self._emit_log("Built-in Chromium downloaded. Restart the app, then "
                           "pick it under Settings ▸ Export browser (browsers "
                           "are probed at startup).")
            self._emit_modal("info", "Built-in Chromium downloaded",
                             "The browser is in place. Restart the app, then "
                             "choose it under Settings ▸ Export browser.")
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
        if key == "fast_workers":
            # The matrix corner spinner reads this back from the snapshot
            # (matrix_fast.workers); push so an unrelated state event can't revert it.
            self._push_state()
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
        warns = []
        targets = reset_targets(include_input, warnings=warns)
        files, size = measure_targets(targets)
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._reset_token = (token, include_input)
        # Enumeration warnings ride the LABEL list only (no path -> the dialog
        # renders them as plain lines); the delete path never sees them.
        return {"targets": [label for label, _p in targets]
                           + [f"⚠ {w}" for w in warns],
                # The concrete paths too, so the confirm dialog shows EXACTLY
                # what will be deleted (the labels alone hid the real location of
                # the user-chosen Export Everything store).
                "paths": [str(p) for _label, p in targets],
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
        err = self._claim_task_error("reset")
        if err:
            return err
        ui_log.info("reset: user confirmed delete-all-reports (input=%s)",
                    include_input)
        self.cancel_event.clear()
        self._emit_log("Deleting all reports…")
        self._set_dot("busy", "Deleting reports…")
        self._emit({"t": "run_started", "mode": "consolidate",
                    "label": "Deleting reports…"})
        self._push_state()
        ResetWorker(self._gated_queue(), include_input=include_input,
                    cancel_event=self.cancel_event).start()
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
        elif payload.get("cancelled"):
            self._emit_log(f"Cancelled — deleted {payload['files']} file(s) "
                           f"({payload['mb']} MB) before stopping. Logs, your "
                           "login and settings were kept.")
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
        paths, the OS version, and an ALLOWLISTED subset of diagnostic settings
        (settings.support_bundle_settings(), not all_settings() — so no site_urls /
        batch_dest / future sensitive key leaks) — diagnostics need those. So it's
        safe to send to the TSMIS maintainer, not "safe to post publicly"; the
        user-facing wording below says so plainly."""
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
                       f"  version and selected diagnostic settings (diagnostics need them);\n"
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
                       f"settings:   {settings.support_bundle_settings()}\n"
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
                    except OSError as e:
                        # one locked/unreadable log shouldn't sink the whole bundle —
                        # skip it, but log which so a maintainer knows it's absent (P7a).
                        ui_log.info("support bundle: skipped %s (%s: %s)",
                                    f.name, type(e).__name__, e)
            reports = sorted((OUTPUT_ROOT / "run_reports").glob("*.csv"),
                             key=lambda p: p.stat().st_mtime, reverse=True)[:50]
            for f in reports:
                try:
                    zf.write(f, f"run_reports/{f.name}")
                    added += 1
                except OSError as e:
                    ui_log.info("support bundle: skipped run report %s (%s: %s)",
                                f.name, type(e).__name__, e)
        ui_log.info("support bundle saved: %s (%d files)", out, added)
        self._emit_log(f"Support bundle saved ({added} files): {out}")
        self._emit_log("  It has logs, run reports and selected diagnostic settings "
                       "(and this PC's name in paths) — never your password or saved "
                       "login. Send it to the TSMIS maintainer.")
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

    def _open_file(self, path):
        """Open a FILE with its default app (Excel for .xlsx). Unlike
        _open_folder it never creates anything — the caller has already checked
        the file exists."""
        try:
            os.startfile(str(path))          # Windows; launches the associated app
            ui_log.info("opened file: %s", path)
        except Exception as e:
            log.warning("could not open file %s (%s: %s)", path, type(e).__name__, e)
            self._emit_modal("error", "Could not open file", str(e))

    @_api_method
    def open_output_folder(self):
        self._open_folder(OUTPUT_ROOT)
        return {"ok": True}

    @_api_method
    def open_logs_folder(self):
        self._open_folder(LOG_DIR)
        return {"ok": True}

    @_api_method
    def open_consolidated_folder(self, report_key, day):
        # Same WS5 guards as its siblings: resolve the report KEY and validate
        # the day (no traversal into a folder outside OUTPUT_ROOT -- this method
        # mkdir+opens the resolved path via _open_folder).
        row = self._pick_report(CONSOLIDATE_REPORTS, consolidate_index_for_key(report_key))
        if row is None:
            return {"error": "That report isn't available — please reopen the tab."}
        try:
            day = self._safe_day(day)
        except ValueError as e:
            return {"error": str(e)}
        _label, mod = row
        self._open_folder(mod.out_path_for(day).parent)
        return {"ok": True}


# ============================== window bootstrap ==============================

def _fatal_box(text):
    """Last-resort error surface for a windowed .exe (no console, no window)."""
    try:
        gui_win32.message_box(text, APP_NAME)        # MB_ICONERROR
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
        except Exception as e:
            log.info("devtools toggle unreadable (%s: %s); staying off",
                     type(e).__name__, str(e).splitlines()[0] if str(e) else "")
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
