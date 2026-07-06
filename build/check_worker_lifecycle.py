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

EXACTLY-ONCE (P7a / R1-R06 / R1-R14 / P7a-B01): the `TaskCoordinator` owns the gate and
stamps every claim with a monotonic EPOCH -- the task instance's identity. A gated worker
tags its terminal with the epoch it was started under (`GuiApi._gated_queue` ->
`_StampedQueue`); `GuiApi._handle` drops any terminal whose epoch is no longer the live
claim's (`TaskCoordinator.is_live`), so a straggler can NOT clobber a successor that
already started -- INCLUDING a same-kind matrix successor or a wildcard `error`/`cancelled`,
which the earlier kind-only guard could not tell apart. `test_duplicate_late_active_successor`
and `test_duplicate_late_same_kind_matrix` assert that; `test_stamped_queue_tags_terminals`
and `test_coordinator_epoch_is_live` pin the mechanism; `test_dispatch_covers_contract`
keeps the dispatch table complete against the `contract` SSOT. Workers post exactly one
terminal (see test_producer_paths), so this is the defensive net that makes a duplicate/late
terminal safe rather than a clobber (it flipped the prior known gap).

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
                    # **_k tolerates the P8c should_cancel kwarg now threaded in.
                    (gw, "storage_state_is_portable", lambda _p, _s, **_k: False)]
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


def test_stamped_queue_tags_terminals():
    print("the gated queue tags terminals with the claim epoch, passes others through:")
    q = _Q()
    sq = gui_api._StampedQueue(q, 42)
    sq.put(("log", "hello"))
    sq.put(("progress", {"done": 1}))
    sq.put(("export_done", ["r"]))
    sq.put(("error", ("auth", "x")))
    check("non-terminal 'log' passes through as a 2-tuple", q.items[0] == ("log", "hello"))
    check("non-terminal 'progress' passes through as a 2-tuple",
          q.items[1] == ("progress", {"done": 1}))
    check("terminal 'export_done' is stamped (kind, payload, epoch)",
          q.items[2] == ("export_done", ["r"], 42))
    check("terminal 'error' is stamped (kind, payload, epoch)",
          q.items[3] == ("error", ("auth", "x"), 42))


def test_coordinator_epoch_is_live():
    print("the coordinator bumps the epoch on each claim and is_live tracks it:")
    import task_coordinator
    c = task_coordinator.TaskCoordinator(threading.RLock(), 8)
    check("fresh coordinator: epoch 0", c.current_epoch() == 0)
    check("is_live(0) False while idle (no task owns the gate)", c.is_live(0) is False)
    assert c.try_claim("export")
    e1 = c.current_epoch()
    check("try_claim bumped the epoch", e1 == 1)
    check("is_live(e1) True for the live claim", c.is_live(e1) is True)
    check("is_live(None) True while a task runs (untagged == current; legacy)",
          c.is_live(None) is True)
    check("is_live(stale) False for a prior epoch", c.is_live(e1 - 1) is False)
    c.release()
    check("after release the gate is idle: is_live(e1) False", c.is_live(e1) is False)
    check("is_live(None) False while idle", c.is_live(None) is False)
    c.enqueue(_job("m"))
    c.take_next()
    e2 = c.current_epoch()
    check("take_next bumped the epoch again (monotonic)", e2 == 2)
    check("is_live(e1) False (stale) once a newer claim holds the gate", c.is_live(e1) is False)
    check("is_live(e2) True for the current matrix claim", c.is_live(e2) is True)
    c.release()
    c.claim_direct("login")        # the login/envcheck/envscan/chromium claim path
    check("claim_direct bumped the epoch too (monotonic)", c.current_epoch() == 3)
    check("is_live(e2) False once claim_direct supersedes it", c.is_live(e2) is False)


def _msg_values():
    """Every declared message string on contract.Msg (the bridge vocabulary SSOT)."""
    return {v for k, v in vars(gui_api.contract.Msg).items()
            if not k.startswith("_") and isinstance(v, str)}


def test_dispatch_covers_contract():
    print("the _handle dispatch table + terminal set match the contract SSOT (P7a-A01):")
    a = _api()
    declared = _msg_values()
    handled = set(a._dispatch.keys())
    check("every contract.Msg has a dispatch handler", declared <= handled)
    check("no dispatch handler outside contract.Msg", handled <= declared)
    term = set(gui_api.contract.TERMINAL)
    check("every terminal kind is a declared contract.Msg", term <= declared)
    check("every terminal kind has a dispatch handler", term <= handled)


def test_duplicate_late_active_successor():
    print("duplicate-late terminal with an ACTIVE successor is a no-op (P7a exactly-once):")
    a = _api()
    a._dispatch_matrix_job = lambda job: True
    _claim(a, "export")
    e1 = a._coord.current_epoch()                      # the export claim's identity (its worker stamps this)
    succ = _job("successor")
    a._queue.append(succ)
    a._handle("export_done", [], e1)                   # the export's REAL terminal: frees gate, starts successor
    check("precondition: the successor is the running task",
          a._task == "matrix" and a._current_job is succ)
    e2 = a._coord.current_epoch()
    check("precondition: the successor claimed a fresh epoch", e2 != e1)
    # Stragglers from the FINISHED export (all tagged e1) -- EVERY terminal class, incl.
    # the generic error/cancelled wildcards a kind-only guard accepted against a successor:
    a._handle("export_done", [], e1)
    a._handle("error", ("general", "late straggler"), e1)
    a._handle("cancelled", None, e1)
    check("no straggler clobbers the successor's gate (still 'matrix')", a._task == "matrix")
    check("no straggler clears the successor's running job", a._current_job is succ)


def test_duplicate_late_same_kind_matrix():
    print("a stale SAME-KIND matrix_done can't clobber the next matrix job (P7a-B01):")
    a = _api()
    started = []
    a._dispatch_matrix_job = lambda job: (started.append(job["label"]) or True)
    j1, j2 = _job("m1"), _job("m2")
    a._queue.append(j1)
    a._queue.append(j2)
    a._try_start_next_matrix_job()                     # j1 claims the matrix gate
    e1 = a._coord.current_epoch()
    check("precondition: the first matrix job is running",
          a._task == "matrix" and a._current_job is j1)
    a._handle("matrix_done", {"done": 1, "total": 1}, e1)   # j1's REAL terminal -> j2 auto-starts
    e2 = a._coord.current_epoch()
    check("precondition: the second matrix job is running (fresh epoch)",
          a._current_job is j2 and e2 != e1)
    a._handle("matrix_done", {"done": 1, "total": 1}, e1)   # STALE duplicate from j1
    check("the stale same-kind matrix_done did NOT clobber the second job",
          a._task == "matrix" and a._current_job is j2)
    check("each matrix job was dispatched exactly once", started == ["m1", "m2"])


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


def test_active_check_soft_busy():
    """B8: a user claim during the quiet background env check gets a clear soft
    message (never a browser-launch crash), supersedes the check, and works
    normally once the check is done."""
    print("active-check exclusion (B8):")
    a = _api()
    a._active_check = True
    a._active_check_supersede.clear()
    err = a._claim_task_error("export")
    check("claim during the check -> soft busy message",
          bool(err) and "background" in err["error"])
    check("...the check was superseded", a._active_check_supersede.is_set())
    check("...the task gate was NOT taken", a._coord.task is None)
    a._active_check = False
    err = a._claim_task_error("export")
    check("claim after the check -> gate taken normally", err is None
          and a._coord.task == "export")
    a._coord.release()



def main():
    test_active_check_soft_busy()
    test_producer_paths()
    test_terminal_payload_variants()
    test_queue_advances_on_terminal()
    test_invalid_manifest_batch_advances_successor()
    test_stamped_queue_tags_terminals()
    test_coordinator_epoch_is_live()
    test_dispatch_covers_contract()
    test_duplicate_late_idle()
    test_duplicate_late_active_successor()
    test_duplicate_late_same_kind_matrix()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL WORKER-LIFECYCLE CHECKS PASSED")
    print("(note: the TaskCoordinator's exactly-once guard drops a straggler terminal — P7a)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
