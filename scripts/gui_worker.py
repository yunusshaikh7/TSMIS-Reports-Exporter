"""Worker threads for the GUI.

Playwright's sync API is thread-affine, so all browser work happens on a
dedicated worker thread -- never on the Tk main thread. Workers communicate by
putting messages on a queue.Queue (thread-safe); the GUI drains it via
root.after(). Workers never touch Tk widgets.

Message protocol (all are (kind, payload) tuples):
    ("log", str)                       one status line
    ("progress", dict)                 {done,total,route,report,report_i,report_n,saved,empty,skipped,failed,exists}
    ("export_done", [(spec, RunResult), ...])   all selected reports finished
    ("export_partial", [(spec, RunResult), ...]) reports done before an error (then an "error" follows)
    ("consolidate_done", ConsolidateResult)
    ("login_open", None)               headed browser is up; user should finish SSO
    ("login_saved", None)              a VALID session was captured and written
    ("login_failed", None)             window closed/finished without a real login
    ("cancelled", None)                task stopped at user request
    ("error", (kind, message))         kind is "auth" or "general"
"""
import json
import logging
import threading

from common import (
    AUTH, ROUTES, URL, AuthError, BrowserNotFoundError, PreflightError,
    BROWSER_CHANNELS, CHANNEL_LABELS, check_browsers, launch_login_browser,
)
from events import Events
from exporter import run_export
from paths import OUTPUT_ROOT


class ExportWorker(threading.Thread):
    """Runs one OR MORE bulk exports, translating engine Events into GUI messages.

    `specs` may be a single ReportSpec or a list. Multiple report types run one
    after another (each reuses the proven engine), so in fast mode only `workers`
    browsers are ever open at once. Posts ('export_done', [(spec, RunResult), ...])
    when all selected reports finish (the list is partial if cancelled)."""

    def __init__(self, specs, queue, cancel_event, skip_event, workers=1, routes=None):
        super().__init__(daemon=True)
        # Accept a single spec or a list, so callers can't trip on the shape.
        self.specs = list(specs) if isinstance(specs, (list, tuple)) else [specs]
        self.q = queue
        self.cancel = cancel_event
        self.skip = skip_event
        self.workers = workers              # >1 -> experimental parallel "fast mode"
        # None means "all routes"; otherwise the chosen subset. Stored as a
        # concrete list so the engine and the progress total agree.
        self.routes = list(routes) if routes is not None else list(ROUTES)
        self._total = len(self.routes)
        # route -> latest status, so the end-of-run retry pass (which re-reports a
        # route, e.g. failed -> saved) updates counts in place rather than
        # double-counting. Counts are derived from this map on each update. Reset
        # per report type so each report's progress starts clean.
        self._route_status = {}
        self._tally_lock = threading.Lock()  # fast mode: several threads call _on_route
        self._cur_label = ""               # report currently running (shown in progress)
        self._report_i = 0                 # 1-based index of the current report
        self._report_n = len(self.specs)   # how many reports this run will do

    def _on_route(self, route, status):
        with self._tally_lock:              # in fast mode this fires from many threads
            self._route_status[route] = status      # latest status wins (retry re-reports)
            counts = {"saved": 0, "empty": 0, "skipped": 0, "failed": 0, "exists": 0}
            for st in self._route_status.values():
                if st in counts:
                    counts[st] += 1
            msg = {"done": len(self._route_status), **counts}
        msg["total"] = self._total
        msg["route"] = route
        msg["report"] = self._cur_label
        msg["report_i"] = self._report_i
        msg["report_n"] = self._report_n
        self.q.put(("progress", msg))

    def _should_skip(self):
        if self.skip.is_set():
            self.skip.clear()               # one press skips one route
            return True
        return False

    def run(self):
        events = Events(
            on_log=lambda t: self.q.put(("log", t)),
            on_route=self._on_route,
            should_skip=self._should_skip,
            is_cancelled=self.cancel.is_set,
        )
        results = []
        try:
            for i, spec in enumerate(self.specs, 1):
                if self.cancel.is_set():
                    break
                self._report_i = i
                self._cur_label = spec.label
                with self._tally_lock:
                    self._route_status = {}         # fresh counts for this report
                if self._report_n > 1:
                    self.q.put(("log", ""))
                    self.q.put(("log", f"===== Report {i} of {self._report_n}: {spec.label} ====="))
                # Reset the progress bar/counts for this report so the GUI doesn't
                # show the previous report's tally while this one spins up.
                self.q.put(("progress", {
                    "done": 0, "total": self._total, "route": "—",
                    "saved": 0, "empty": 0, "skipped": 0, "failed": 0, "exists": 0,
                    "report": spec.label, "report_i": i, "report_n": self._report_n,
                }))
                if self.workers and self.workers > 1:
                    from exporter_parallel import run_export_parallel  # lazy
                    result = run_export_parallel(spec, events, workers=self.workers,
                                                 routes=self.routes)
                else:
                    result = run_export(spec, events, routes=self.routes)
                results.append((spec, result))
            self.q.put(("export_done", results))
            return
        except AuthError as e:
            err = ("auth", str(e))
        except (PreflightError, BrowserNotFoundError) as e:
            err = ("general", str(e))               # message is already user-safe
        except Exception as e:
            err = ("general", f"{type(e).__name__}: {e}")
        # An error aborted a multi-report run partway. Hand the GUI whatever
        # reports DID finish so "Save run report…" still covers them (each is also
        # auto-saved under output/run_reports/), then surface the error.
        if results:
            self.q.put(("export_partial", results))
        self.q.put(("error", err))


class ConsolidateWorker(threading.Thread):
    """Runs one consolidator. Overwrite is resolved by the GUI before start,
    so the injected confirm callback just returns the pre-decided answer."""

    def __init__(self, consolidate_fn, queue, cancel_event, confirm):
        super().__init__(daemon=True)
        self.consolidate_fn = consolidate_fn
        self.q = queue
        self.cancel = cancel_event
        self.confirm = confirm

    def run(self):
        events = Events(
            on_log=lambda t: self.q.put(("log", t)),
            is_cancelled=self.cancel.is_set,
        )
        try:
            result = self.consolidate_fn(events=events, confirm_overwrite=self.confirm)
            self.q.put(("consolidate_done", result))
        except Exception as e:
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))


class LoginWorker(threading.Thread):
    """Opens a headed browser for SSO+MFA, waits for the user to signal done
    (done_event, set by a GUI button), then saves the storage_state.

    cancel_event also sets done_event to unblock the wait; if cancel is set the
    session is NOT saved.
    """

    def __init__(self, queue, done_event, cancel_event):
        super().__init__(daemon=True)
        self.q = queue
        self.done = done_event
        self.cancel = cancel_event

    def run(self):
        from playwright.sync_api import sync_playwright
        log = logging.getLogger("tsmis.login")
        try:
            with sync_playwright() as p:
                # Sign-in prefers Chrome: managed Edge relaunches itself during the
                # Caltrans SSO and kills the automated window. Exports still use the
                # user's chosen browser (the session is browser-agnostic).
                browser, login_channel = launch_login_browser(p)
                try:
                    ctx = browser.new_context()
                    page = ctx.new_page()
                    page.goto(URL)
                    self.q.put(("login_open", None))
                    self.q.put(("log", f"Sign-in window opened in "
                                       f"{CHANNEL_LABELS.get(login_channel, login_channel)}. "
                                       "(Exports still use the browser selected in the header.)"))
                    log.info("login: window opened in %s; waiting for the user to finish",
                             login_channel)

                    # Simple, proven flow: just WAIT for the user to click "I've
                    # finished logging in" (or Cancel), then save. We deliberately
                    # do NO polling / page inspection while they sign in. Poking the
                    # page during the SSO/MFA redirects (the old close-watcher's
                    # per-tick ctx.cookies()/page checks) made Microsoft Edge
                    # relaunch itself and disconnect, closing the login window the
                    # moment sign-in completed (Edge-only; Chrome was unaffected).
                    # Not touching the page during sign-in is what keeps Edge happy.
                    while not self.done.wait(0.2):
                        pass

                    if self.cancel.is_set():
                        self.q.put(("cancelled", None))
                        log.info("login: cancelled by user")
                    else:
                        # Save whatever session the context now holds. (One capture,
                        # after the user says they're done -- no mid-login probing.)
                        self._save_state(ctx.storage_state())
                        self.q.put(("login_saved", None))
                        log.info("login: session saved")
                finally:
                    self._safe_close(browser)
        except BrowserNotFoundError as e:
            self.q.put(("error", ("general", str(e))))
        except Exception as e:
            logging.getLogger("tsmis.login").exception("login worker crashed")
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))

    @staticmethod
    def _safe_close(browser):
        try:
            browser.close()
        except Exception:
            pass

    @staticmethod
    def _save_state(state):
        AUTH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUTH, "w", encoding="utf-8") as f:
            json.dump(state, f)


# --- startup readiness checks -------------------------------------------------
# (Login isn't checked here -- the header status row + Log in button own it.)

def _check_output():
    try:
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        probe = OUTPUT_ROOT / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return ("ok", "Output folder: writable")
    except Exception:
        return ("bad", "Output folder: NOT writable")


def _check_tools():
    try:
        import pdfplumber  # noqa: F401
        import openpyxl    # noqa: F401
        return ("ok", "Report tools (PDF/Excel): ready")
    except Exception as e:
        return ("bad", f"Report tools: missing ({type(e).__name__})")


class CheckWorker(threading.Thread):
    """Runs the launch-time readiness checks off the Tk thread, posting each
    result as ('check', (key, status, text)) and a final ('checks_done', dict).

    The instant checks (login, output folder, PDF/Excel tools) are posted first;
    the browser probes are slower (each launches a headless browser) so they land
    a couple seconds later. status is one of 'ok' | 'bad'.
    """

    def __init__(self, queue):
        super().__init__(daemon=True)
        self.q = queue

    def run(self):
        for key, fn in (("output", _check_output), ("tools", _check_tools)):
            try:
                status, text = fn()
            except Exception as e:
                status, text = "bad", f"{key}: error ({type(e).__name__})"
            self.q.put(("check", (key, status, text)))

        try:
            results = check_browsers()           # {channel: ok|missing|broken}
        except Exception:
            results = {ch: "broken" for ch in BROWSER_CHANNELS}
        detail = {"ok": "ready", "missing": "not installed",
                  "broken": "found, but this tool can't control it (it may be too new)"}
        for ch in BROWSER_CHANNELS:
            status = results.get(ch, "broken")
            self.q.put(("check", (f"browser_{ch}", "ok" if status == "ok" else "bad",
                                   f"{CHANNEL_LABELS[ch]}: {detail[status]}")))
        self.q.put(("checks_done", results))
