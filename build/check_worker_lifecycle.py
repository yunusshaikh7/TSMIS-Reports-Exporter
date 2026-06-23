"""CT-10: per-worker terminal lifecycle -- producer path + gate release.

The invariant P7a's TaskCoordinator must preserve: every task-owning worker
posts **exactly one** terminal event for its outcome, and that terminal frees
the single-task gate (`_task`/`_current_job`) and lets the matrix queue advance.

Because worker terminal delivery is PATH-DEPENDENT (R1-R14), this check runs each
gate-owning worker's real `run()` synchronously with browser / filesystem /
engine collaborators stubbed, captures its queue emissions, and asserts it emits
exactly one terminal of the expected kind on success / cancel / expected-error /
unexpected-error. It then feeds that terminal through `GuiApi._handle` and asserts
the gate is released. Payload-encoded cancel/error variants and queue-advance are
covered separately.

KNOWN GAP (characterized, NOT asserted-safe): `GuiApi._end_task` clears state
unconditionally, so a duplicate-late terminal arriving after a queued successor
has started CLOBBERS the successor. The exactly-once fix is owned by P7a
(R1-R06 / R1-R14; see 00-coordination.md D21). `test_duplicate_late_active_successor`
LOCKS that current behavior so P7a's fix visibly flips it.

LoginWorker is producer-tested like the others: its `run()` / `_run_login_in_browser`
are driven offline with a fake Playwright (no real browser launch), an immediate
`done` event, and stubbed `new_login_context` / `is_logged_in` / `_save_state` (no
auth-file write); the Edge-device fallback is isolated via `_try_edge_persistent_login`
/ `storage_state_is_portable`. Covered: `login_saved`, `login_device_ok`,
`login_failed`, cancellation, expected error, and unexpected error.

Pure Python (imports the real gui_api/gui_worker; no window, no browser, no
network, no auth-file write). Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_worker_lifecycle.py
"""
import contextlib
import logging
import sys
import threading
import types
from pathlib import Path

# This check deliberately drives worker error paths, which call log.exception().
# Silence logging so those EXPECTED tracebacks don't spam the CI output.
logging.disable(logging.CRITICAL)

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import gui_api  # noqa: E402
import gui_worker as gw  # noqa: E402
import events as ev  # noqa: E402
import playwright.sync_api as pw  # noqa: E402

_failures = []

# Every kind that ENDS a task (frees the gate). export_partial/log/progress/
# batch_progress/matrix_cell/env_access are progress, NOT terminal.
TERMINAL = {"export_done", "consolidate_done", "reset_done", "chromium_done",
            "batch_done", "matrix_done", "matrix_export_done", "env_shot",
            "env_access_done", "error", "cancelled",
            "login_saved", "login_device_ok", "login_failed"}


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


class _Q:
    """A drop-in for queue.Queue that just records (kind, payload) tuples."""
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


@contextlib.contextmanager
def _patched(*triples):
    saved = [(o, a, getattr(o, a)) for o, a, _ in triples]
    for o, a, v in triples:
        setattr(o, a, v)
    try:
        yield
    finally:
        for o, a, v in saved:
            setattr(o, a, v)


@contextlib.contextmanager
def _fake_playwright():
    yield object()


class _FakeBrowser:
    def close(self):
        pass


class _FakePage:
    def evaluate(self, _js):
        return ["PROD", "SSOR"]                       # [env, src]

    def screenshot(self, **_k):
        return b"img-bytes"


def _terminals(items):
    return [k for k, _ in items if k in TERMINAL]


def _api():
    """A GuiApi with browser/auth/scan side effects stubbed."""
    a = gui_api.GuiApi()
    a.cancel_event.clear()
    a._maybe_autoscan = lambda *_a, **_k: None
    a._maybe_active_env_check = lambda *_a, **_k: None
    return a


def _claim(a, name):
    assert a._try_claim_task(name) is True, "fresh gate should be claimable"
    return a


def _gate_free(a):
    if a._try_claim_task("probe"):
        a._release_task()
        return True
    return False


# ---------------------------------------------------------------------------
# Producer scenarios: each runs a real worker run() with stubbed collaborators
# and returns its queue emissions.  (worker, gate, expected_terminal, outcome, fn)
# ---------------------------------------------------------------------------

def _export(outcome):
    q = _Q()
    w = gw.ExportWorker(["spec"], q, threading.Event(), threading.Event(), routes=["1"])
    if outcome == "success":
        w._run_specs = lambda _e, _r: None
    elif outcome == "expected-error":
        def rs(_e, _r): raise gw.AuthError("no session")
        w._run_specs = rs
    elif outcome == "unexpected-error":
        def rs(_e, _r): raise ValueError("kaboom")
        w._run_specs = rs
    else:  # partial -> export_partial (progress) THEN error (terminal)
        def rs(_e, results): results.append(("spec", ev.RunResult())); raise ValueError("midway")
        w._run_specs = rs
    w.run()
    return q.items


def _consolidate(outcome):
    q = _Q()
    if outcome == "success":
        fn = lambda **_k: ev.ConsolidateResult(status="ok")
    else:
        def fn(**_k): raise RuntimeError("bad input")
    w = gw.ConsolidateWorker(fn, q, threading.Event(), lambda _p: True)
    w.run()
    return q.items


def _reset(outcome):
    q = _Q()
    cancel = threading.Event()
    if outcome == "success":
        targets = []
    else:                                              # cancel: break before delete
        targets = [("Run folders", Path("X-never-touched"))]
        cancel.set()
    with _patched((gw, "reset_targets", lambda _i: targets),
                  (gw, "measure_targets", lambda t: (len(t), 100))):
        gw.ResetWorker(q, False, cancel).run()
    return q.items


def _chromium(outcome):
    q = _Q()
    action = "delete" if outcome == "unexpected-error" else "download"
    w = gw.ChromiumWorker(q, action, threading.Event())
    if outcome == "success":
        w._download = lambda: True
    elif outcome == "cancel":
        w._download = lambda: False
    else:
        def boom(): raise RuntimeError("locked")
        w._delete = boom
    w.run()
    return q.items


def _envcheck(outcome):
    q = _Q()
    w = gw.EnvCheckWorker(q)
    if outcome == "expected-error":
        def nab(_p, **_k): raise gw.AuthError("no session")
        patches = [(pw, "sync_playwright", _fake_playwright),
                   (gw, "new_authed_browser", nab)]
    else:                                              # success
        patches = [(pw, "sync_playwright", _fake_playwright),
                   (gw, "new_authed_browser", lambda _p, **_k: (_FakeBrowser(), None, _FakePage())),
                   (gw, "navigate_with_auth", lambda _p, **_k: None),
                   (gw, "is_logged_in", lambda _p: True),
                   (gw, "page_url_for_display", lambda _p: "https://tsmis/x")]
    with _patched(*patches):
        w.run()
    return q.items


def _envscan():
    q = _Q()
    w = gw.EnvScanWorker(q, threading.Event())
    w.check_one = lambda _page, src, env, _specs: {
        "key": f"{src}-{env}", "source": src, "environment": env,
        "label": "L", "status": "ok", "detail": "", "url": "", "reports": {}}
    with _patched((gw, "has_valid_auth", lambda: False),     # -> 1 scanner, no parallel pre-check
                  (pw, "sync_playwright", _fake_playwright),
                  (gw, "new_authed_browser", lambda _p, **_k: (_FakeBrowser(), None, _FakePage()))):
        w.run()
    return q.items


def _batch(outcome):
    q = _Q()
    manifest = {"steps": [{"src": "ssor", "env": "prod", "status": "pending"}],
                "dest": None, "fast": False, "workers": 1, "auto_consolidate": False}
    w = gw.BatchWorker(manifest, q, threading.Event(), threading.Event(), threading.Event())
    _spec = types.SimpleNamespace(label="Ramp Summary", subdir="ramp_summary")
    w._specs = lambda: [_spec]
    w._step_views = lambda _s, _e: []
    if outcome == "success":
        # the env's one report exports COMPLETE -> env marked done -> batch_done.
        def rs(_self, _e, results):
            results.append((_spec, types.SimpleNamespace(
                saved=5, exists=[], empty=[], user_skipped=[], failed=[],
                completion=gw.outcome.COMPLETE, artifact=gw.outcome.PROMOTED)))
    else:
        def rs(_self, _e, _r): raise gw.AuthError("no session")
    with _patched((gw.ExportWorker, "_run_specs", rs),
                  (gw, "set_site", lambda *_a: None),
                  (gw, "get_site", lambda: ("ssor", "prod")),
                  (gw.batch_manifest, "mark_done", lambda *_a: None),
                  (gw.batch_manifest, "is_complete", lambda _m: True)):
        w.run()
    return q.items


def _batch_invalid():
    """BatchWorker.run over a manifest whose saved KEYS can't all resolve (a
    removed/renamed report). Must abort ALL-OR-NOTHING with EXACTLY ONE terminal
    (`error`) — no `batch_done`, no env marked done — the invalid saved selection
    can't run a narrower batch (P3-B01/B02 / §C.5)."""
    q = _Q()
    manifest = {"version": 2, "reports": ["__removed__", "ramp_summary"],
                "steps": [{"src": "ssor", "env": "prod", "status": "pending"}],
                "dest": None, "fast": False, "workers": 1, "auto_consolidate": False}
    w = gw.BatchWorker(manifest, q, threading.Event(), threading.Event(),
                       threading.Event())
    with _patched((gw, "set_site", lambda *_a: None),
                  (gw, "get_site", lambda: ("ssor", "prod")),
                  (gw.batch_manifest, "mark_done",
                   lambda *_a: (_ for _ in ()).throw(AssertionError("marked done!")))):
        w.run()
    return q.items


def _matrix_export(outcome):
    q = _Q()
    spec = types.SimpleNamespace(label="Ramp Summary")
    w = gw.MatrixBatchExportWorker([(spec, "ssor", "prod")], None, q,
                                   threading.Event(), threading.Event(), threading.Event())
    if outcome == "success":
        def step(*_a, **_k): return None
    else:
        def step(*_a, **_k): raise gw.AuthError("no session")
    with _patched((gw, "_run_matrix_export_step", step),
                  (gw, "set_site", lambda *_a: None),
                  (gw, "get_site", lambda: ("ssor", "prod"))):
        w.run()
    return q.items


def _matrix_compare():
    q = _Q()
    w = gw.MatrixCompareWorker(None, "ssor-prod", [("ramp_summary", "ssor-prod", "env")],
                               q, threading.Event())
    with _patched((gw.matrix, "build_comparison",
                   lambda *_a, **_k: types.SimpleNamespace(status="ok", message=""))):
        w.run()
    return q.items


def _day_matrix_compare():
    q = _Q()
    w = gw.DayMatrixCompareWorker("ssor", [("2026-06-11", "ramp_summary")], None,
                                  q, threading.Event())
    with _patched((gw.day_matrix, "build_day_cell",
                   lambda *_a, **_k: types.SimpleNamespace(status="ok", message=""))):
        w.run()
    return q.items


def _matrix_tsn():
    q = _Q()
    w = gw.MatrixTsnConsolidateWorker(None, "highway_log", q, threading.Event())
    with _patched((gw.matrix, "consolidate_tsn_pdfs", lambda *_a, **_k: "tsn.xlsx")):
        w.run()
    return q.items


# --- LoginWorker producer path (offline: fake Playwright, no auth-file write) ---
class _AlwaysDone:
    """A done-event that is permanently set: `_run_login_in_browser` CLEARS the
    done event then waits on it, so a plain pre-set Event would be cleared and
    hang. clear() is a no-op here -> wait() returns immediately, modelling an
    instant "I've finished logging in" click."""
    def clear(self):
        pass

    def set(self):
        pass

    def is_set(self):
        return True

    def wait(self, _timeout=None):
        return True


class _FakeChromium:
    def __init__(self, launch):
        self._launch = launch

    def launch(self, **kw):
        return self._launch(**kw)


class _FakeP:
    def __init__(self, launch):
        self.chromium = _FakeChromium(launch)


@contextlib.contextmanager
def _login_pw(launch):
    yield _FakeP(launch)


class _FakePageGoto:
    def goto(self, _url):
        pass


class _FakeLoginCtx:
    pages = [object()]                                 # _any_logged_in iterates these

    def new_page(self):
        return _FakePageGoto()

    def cookies(self):
        return []

    def storage_state(self):
        return {"cookies": [], "origins": []}          # truthy -> "captured"

    def close(self):
        pass


def _login(outcome):
    q = _Q()
    cancel = threading.Event()
    w = gw.LoginWorker(q, _AlwaysDone(), cancel)       # always "done" -> no hang
    w._save_state = lambda _s: None                    # never write the auth file
    patches = [(gw, "get_preferred_channel", lambda: None),
               (gw, "get_url", lambda: "https://tsmis/login")]
    if outcome == "device_ok":                         # EDGE fallback: no Chrome/Chromium opens
        def launch(**_kw): raise RuntimeError("no chrome/chromium")
        w._try_edge_persistent_login = lambda _p, _log: {"cookies": []}
        patches += [(pw, "sync_playwright", lambda: _login_pw(launch)),
                    (gw, "storage_state_is_portable", lambda _p, _s: False)]
    else:                                              # MAIN path: a browser launches
        def launch(**_kw): return _FakeBrowser()
        patches.append((pw, "sync_playwright", lambda: _login_pw(launch)))
        if outcome == "saved":
            patches += [(gw, "new_login_context", lambda _b: _FakeLoginCtx()),
                        (gw, "is_logged_in", lambda _pg: True)]
        elif outcome == "failed":
            patches += [(gw, "new_login_context", lambda _b: _FakeLoginCtx()),
                        (gw, "is_logged_in", lambda _pg: False)]
        elif outcome == "cancel":
            cancel.set()                               # cancel also unblocks the done-wait
            patches += [(gw, "new_login_context", lambda _b: _FakeLoginCtx()),
                        (gw, "is_logged_in", lambda _pg: False)]
        elif outcome == "expected-error":
            def nlc(_b): raise gw.BrowserNotFoundError("no usable browser")
            patches.append((gw, "new_login_context", nlc))
        else:                                          # unexpected-error
            def nlc(_b): raise RuntimeError("kaboom")
            patches.append((gw, "new_login_context", nlc))
    with _patched(*patches):
        w.run()
    return q.items


_SCENARIOS = [
    # (worker, gate, expected terminal, outcome, run_fn)
    ("ExportWorker", "export", "export_done", "success", lambda: _export("success")),
    ("ExportWorker", "export", "error", "expected-error", lambda: _export("expected-error")),
    ("ExportWorker", "export", "error", "unexpected-error", lambda: _export("unexpected-error")),
    ("ExportWorker", "export", "error", "partial", lambda: _export("partial")),
    ("ConsolidateWorker", "consolidate", "consolidate_done", "success", lambda: _consolidate("success")),
    ("ConsolidateWorker", "consolidate", "error", "unexpected-error", lambda: _consolidate("error")),
    ("ResetWorker", "reset", "reset_done", "success", lambda: _reset("success")),
    ("ResetWorker", "reset", "reset_done", "cancel", lambda: _reset("cancel")),
    ("ChromiumWorker", "chromium", "chromium_done", "success", lambda: _chromium("success")),
    ("ChromiumWorker", "chromium", "chromium_done", "cancel", lambda: _chromium("cancel")),
    ("ChromiumWorker", "chromium", "chromium_done", "unexpected-error", lambda: _chromium("unexpected-error")),
    ("EnvCheckWorker", "envcheck", "env_shot", "success", lambda: _envcheck("success")),
    ("EnvCheckWorker", "envcheck", "env_shot", "expected-error", lambda: _envcheck("expected-error")),
    ("EnvScanWorker", "envscan", "env_access_done", "success", _envscan),
    ("BatchWorker", "batch", "batch_done", "success", lambda: _batch("success")),
    ("BatchWorker", "batch", "error", "expected-error", lambda: _batch("expected-error")),
    ("BatchWorker", "batch", "error", "invalid-manifest", _batch_invalid),
    ("MatrixBatchExportWorker", "matrix", "matrix_export_done", "success", lambda: _matrix_export("success")),
    ("MatrixBatchExportWorker", "matrix", "error", "expected-error", lambda: _matrix_export("expected-error")),
    ("MatrixCompareWorker", "matrix", "matrix_done", "success", _matrix_compare),
    ("DayMatrixCompareWorker", "matrix", "matrix_done", "success", _day_matrix_compare),
    ("MatrixTsnConsolidateWorker", "matrix", "matrix_done", "success", _matrix_tsn),
    ("LoginWorker", "login", "login_saved", "success", lambda: _login("saved")),
    ("LoginWorker", "login", "login_device_ok", "device-mode", lambda: _login("device_ok")),
    ("LoginWorker", "login", "login_failed", "no-login-detected", lambda: _login("failed")),
    ("LoginWorker", "login", "cancelled", "cancel", lambda: _login("cancel")),
    ("LoginWorker", "login", "error", "expected-error", lambda: _login("expected-error")),
    ("LoginWorker", "login", "error", "unexpected-error", lambda: _login("unexpected-error")),
]


def test_producer_paths():
    print("producer path: each worker emits exactly one terminal, which frees the gate:")
    orig_clear = gui_api.clear_auth
    gui_api.clear_auth = lambda *_a, **_k: None         # the auth-error feed must not touch the file
    try:
        for worker, gate, expected, outcome, fn in _SCENARIOS:
            items = fn()
            terminals = _terminals(items)
            one = len(terminals) == 1 and terminals[0] == expected
            check(f"{worker} [{outcome}] emits exactly one terminal = {expected}", one)
            if not one:
                print(f"      got terminals: {terminals}  (all kinds: {[k for k, _ in items]})")
                continue
            kind, payload = next((k, p) for k, p in items if k in TERMINAL)
            a = _claim(_api(), gate)
            a._handle(kind, payload)
            check(f"{worker} [{outcome}] terminal frees the gate via _handle", _gate_free(a))
    finally:
        gui_api.clear_auth = orig_clear


def test_terminal_payload_variants():
    print("payload-encoded cancel/error terminals still free the gate:")
    variants = [
        ("batch", "batch_done", {"cancelled": True, "done": 0, "total": 1}),
        ("batch", "batch_done", {"done": 0, "total": 1}),               # incomplete
        ("reset", "reset_done", {"files": 0, "mb": 0, "cancelled": True}),
        ("reset", "reset_done", {"files": 0, "mb": 0, "errors": ["a.xlsx open in Excel"]}),
        ("chromium", "chromium_done", {"ok": False, "cancelled": True, "action": "download"}),
        ("chromium", "chromium_done", {"ok": False, "error": "locked", "action": "download"}),
        ("matrix", "matrix_done", {"done": 0, "total": 1, "cancelled": True}),
        ("matrix", "matrix_done", {"done": 0, "total": 1, "errors": 1}),
        ("matrix", "matrix_export_done", {"ok": False, "count": 0, "total": 1, "cancelled": True}),
        ("envscan", "env_access_done", {"cancelled": True, "ok": 0, "total": 6}),
        ("envcheck", "env_shot", {"error": "sign-in didn't complete"}),
    ]
    for gate, kind, payload in variants:
        a = _claim(_api(), gate)
        a._handle(kind, payload)
        check(f"{kind} {sorted(payload)} frees the gate", _gate_free(a))


def _job(label, kind="compare", scope="cell", which="env"):
    return {"id": label, "kind": kind, "scope": scope, "label": label,
            "row": None, "env": None, "subdir": None, "fast": False,
            "which": which, "force": False, "status": "queued"}


def test_queue_advances_on_terminal():
    print("a terminal with a queued successor advances the queue:")
    a = _api()
    dispatched = []
    a._dispatch_matrix_job = lambda job: (dispatched.append(job["label"]) or True)
    _claim(a, "export")
    a._queue.append(_job("succ-1"))
    a._queue.append(_job("succ-2"))
    n = len(a._queue)
    a._handle("export_done", [])
    check("queue advanced by one", len(a._queue) == n - 1)
    check("successor dispatched", dispatched == ["succ-1"])
    check("gate held by the running successor", a._task == "matrix")
    a._handle("matrix_done", {"done": 1, "total": 1})
    check("second successor dispatched", dispatched == ["succ-1", "succ-2"])
    a._handle("matrix_done", {"done": 1, "total": 1})
    check("gate free once the queue drains", _gate_free(a))
    check("queue empty", not a._queue)


def test_duplicate_late_idle():
    print("duplicate-late terminal while idle is a harmless no-op:")
    a = _claim(_api(), "export")
    a._handle("cancelled", None)
    a._handle("export_done", [])
    check("gate still free after an idle duplicate-late", _gate_free(a))


def test_duplicate_late_active_successor():
    print("duplicate-late terminal with an ACTIVE successor (KNOWN GAP -> P7a):")
    a = _api()
    a._dispatch_matrix_job = lambda job: True
    _claim(a, "export")
    succ = _job("successor")
    a._queue.append(succ)
    a._handle("export_done", [])
    check("precondition: the successor is the running task",
          a._task == "matrix" and a._current_job is succ)
    a._handle("export_done", [])                       # straggler from the finished export
    check("[known gap: P7a] duplicate-late clobbers the successor's gate", a._task is None)
    check("[known gap: P7a] duplicate-late clears the successor's current job",
          a._current_job is None)


def test_invalid_manifest_batch_advances_successor():
    print("P3-B02: an invalid-manifest batch's ONE terminal advances a queued successor:")
    items = _batch_invalid()
    check("invalid-manifest batch emits exactly one terminal = error",
          _terminals(items) == ["error"])
    check("no batch_done accompanies the error (one terminal per outcome)",
          not any(k == "batch_done" for k, _p in items))
    # Feed that single terminal through _handle WITH an already-dispatched successor:
    # one terminal frees the gate and advances the queue — it cannot clobber the
    # successor (there is no stray second terminal).
    a = _api()
    dispatched = []
    a._dispatch_matrix_job = lambda job: (dispatched.append(job["label"]) or True)
    _claim(a, "batch")
    a._queue.append(_job("succ-after-invalid"))
    kind, payload = next((k, p) for k, p in items if k in TERMINAL)
    a._handle(kind, payload)
    check("the single error terminal advanced the queued successor (not clobbered)",
          dispatched == ["succ-after-invalid"] and a._task == "matrix")


def main():
    test_producer_paths()
    test_terminal_payload_variants()
    test_queue_advances_on_terminal()
    test_invalid_manifest_batch_advances_successor()
    test_duplicate_late_idle()
    test_duplicate_late_active_successor()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL WORKER-LIFECYCLE CHECKS PASSED")
    print("(note: test_duplicate_late_active_successor LOCKS a known gap closed by P7a)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
