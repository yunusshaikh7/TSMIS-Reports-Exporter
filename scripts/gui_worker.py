"""Worker threads for the GUI.

Playwright's sync API is thread-affine, so all browser work happens on a
dedicated worker thread -- never on the Tk main thread. Workers communicate by
putting messages on a queue.Queue (thread-safe); the GUI drains it via
root.after(). Workers never touch Tk widgets.

Message protocol (all are (kind, payload) tuples):
    ("log", str)                       one status line
    ("progress", dict)                 {done,total,route,saved,empty,skipped,failed}
    ("export_done", RunResult)
    ("consolidate_done", ConsolidateResult)
    ("login_open", None)               headed browser is up; user should finish SSO
    ("login_saved", None)              session captured and written
    ("cancelled", None)                task stopped at user request
    ("error", (kind, message))         kind is "auth" or "general"
"""
import threading

from common import AUTH, ROUTES, URL, AuthError, PreflightError
from events import Events
from exporter import run_export


class ExportWorker(threading.Thread):
    """Runs one bulk export, translating engine Events into GUI messages."""

    def __init__(self, spec, queue, cancel_event, skip_event, workers=1):
        super().__init__(daemon=True)
        self.spec = spec
        self.q = queue
        self.cancel = cancel_event
        self.skip = skip_event
        self.workers = workers              # >1 -> experimental parallel "fast mode"
        self._tally = {"done": 0, "saved": 0, "empty": 0, "skipped": 0, "failed": 0}
        self._tally_lock = threading.Lock()  # fast mode: several threads call _on_route

    def _on_route(self, route, status):
        with self._tally_lock:              # in fast mode this fires from many threads
            self._tally["done"] += 1
            if status in self._tally:       # saved/empty/skipped/failed ("exists" only advances done)
                self._tally[status] += 1
            msg = dict(self._tally)
        msg["total"] = len(ROUTES)
        msg["route"] = route
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
        try:
            if self.workers and self.workers > 1:
                from exporter_parallel import run_export_parallel  # lazy
                result = run_export_parallel(self.spec, events, workers=self.workers)
            else:
                result = run_export(self.spec, events)
            self.q.put(("export_done", result))
        except AuthError as e:
            self.q.put(("error", ("auth", str(e))))
        except PreflightError as e:
            self.q.put(("error", ("general", str(e))))      # message is already user-safe
        except Exception as e:
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))


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
        from playwright.sync_api import sync_playwright  # after PLAYWRIGHT_BROWSERS_PATH is set
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                try:
                    ctx = browser.new_context()
                    page = ctx.new_page()
                    page.goto(URL)
                    self.q.put(("login_open", None))

                    while not self.done.wait(0.2):
                        pass                # wait until the user clicks "I've finished"

                    if self.cancel.is_set():
                        self.q.put(("cancelled", None))
                    else:
                        ctx.storage_state(path=str(AUTH))
                        self.q.put(("login_saved", None))
                finally:
                    browser.close()
        except Exception as e:
            self.q.put(("error", ("general", f"{type(e).__name__}: {e}")))
