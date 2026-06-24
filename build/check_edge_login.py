"""Offline checks for the P8c Edge-login behavior changes (no live browser):

  * CDP debug-port gating (edge-login-cdp-port-unauthenticated-loopback): the
    interactive login launch opens NO `--remote-debugging-port` by default (it
    would expose an unauthenticated CDP endpoint on 127.0.0.1 for the whole
    sign-in), and capture_edge_login_state_over_cdp is a clean no-op when no port
    was opened. Opening it is strictly opt-in (enable_cdp=True), on demand.
  * Cancel responsiveness (should_cancel threaded into the login busy-waits):
    capture_edge_login_state_over_cdp / capture_edge_login_state_from_profiles /
    storage_state_is_portable poll should_cancel and bail promptly instead of
    waiting out their full deadlines, so a Stop during login is honored.

Pure Python with fake Playwright objects -- run with the build venv:

    build\\.venv\\Scripts\\python.exe build\\check_edge_login.py
"""
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))

import edge_device  # noqa: E402

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


# --- fake Playwright ---------------------------------------------------------

class _FakePage:
    def is_closed(self):
        return False

    def goto(self, *a, **k):
        return None


class _FakeCtx:
    def __init__(self):
        self.pages = [_FakePage()]
        self.closed = False

    def new_page(self):
        pg = _FakePage()
        self.pages.append(pg)
        return pg

    def close(self):
        self.closed = True

    def storage_state(self):
        return {"cookies": [], "origins": []}


class _FakeChromium:
    def __init__(self):
        self.launch_args = []          # args of each launch_persistent_context call
        self.connect_calls = []        # cdp urls connect_over_cdp was asked for

    def launch_persistent_context(self, user_data_dir, **kwargs):
        self.launch_args.append(list(kwargs.get("args", [])))
        return _FakeCtx()

    def connect_over_cdp(self, url, **kwargs):
        self.connect_calls.append(url)
        raise RuntimeError("connect_over_cdp must not be called without a port")


class _FakeP:
    def __init__(self):
        self.chromium = _FakeChromium()


def _has_debug_port(args):
    return any(str(a).startswith("--remote-debugging-port") for a in args)


def test_cdp_port_gating(tmp):
    print("Edge-login CDP debug-port gating (unauthenticated-loopback fix):")
    edge_device.EDGE_LOGIN_PROFILE_DIR = tmp / "edge_profile"

    # Default: NO debug port, cdp_url is None.
    p = _FakeP()
    ctx, cdp_url = edge_device.launch_edge_login_context(p)
    check("default launch opens NO --remote-debugging-port",
          not _has_debug_port(p.chromium.launch_args[0]))
    check("default launch returns cdp_url=None", cdp_url is None)

    # Opt-in: the port is opened on demand and a cdp_url is returned.
    p2 = _FakeP()
    ctx2, cdp_url2 = edge_device.launch_edge_login_context(p2, enable_cdp=True)
    check("enable_cdp=True opens the debug port",
          _has_debug_port(p2.chromium.launch_args[0]))
    check("enable_cdp=True returns a 127.0.0.1 cdp_url",
          isinstance(cdp_url2, str) and cdp_url2.startswith("http://127.0.0.1:"))


def test_cdp_capture_skips_without_port():
    print("capture_edge_login_state_over_cdp is a no-op without a port:")
    p = _FakeP()
    out = edge_device.capture_edge_login_state_over_cdp(p, None)
    check("returns None when cdp_url is None", out is None)
    check("never attempts a CDP connection", p.chromium.connect_calls == [])


def test_cancel_bails_promptly(tmp):
    print("login busy-waits poll should_cancel and bail (no waiting out the deadline):")
    edge_device.EDGE_LOGIN_PROFILE_DIR = tmp / "edge_profile"
    edge_device.EDGE_LOGIN_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    yes = lambda: True

    # CDP re-attach: a cancel returns None before any connect attempt.
    p1 = _FakeP()
    out = edge_device.capture_edge_login_state_over_cdp(
        p1, "http://127.0.0.1:9", timeout_ms=8_000, should_cancel=yes)
    check("CDP re-attach returns None on cancel", out is None)
    check("CDP re-attach never connected (bailed first)", p1.chromium.connect_calls == [])

    # Profile recapture: a cancel returns (None, None) before any profile launch.
    p2 = _FakeP()
    state, name = edge_device.capture_edge_login_state_from_profiles(
        p2, timeout_ms=20_000, should_cancel=yes)
    check("profile recapture returns (None, None) on cancel",
          state is None and name is None)
    check("profile recapture never launched a profile (bailed first)",
          p2.chromium.launch_args == [])

    # Portability probe: a cancel returns False before launching any browser.
    launched = {"n": 0}
    real_launch = edge_device.launch_browser

    def _boom(*a, **k):
        launched["n"] += 1
        raise AssertionError("launch_browser must not run when cancelled")

    edge_device.launch_browser = _boom
    try:
        portable = edge_device.storage_state_is_portable(
            _FakeP(), {"cookies": [], "origins": []}, should_cancel=yes)
    finally:
        edge_device.launch_browser = real_launch
    check("portability probe returns False on cancel", portable is False)
    check("portability probe never launched a browser (bailed first)",
          launched["n"] == 0)


def test_cancel_reaches_nested_navigate(tmp):
    print("should_cancel reaches the NESTED recapture navigate (P8c-R01):")
    edge_device.EDGE_LOGIN_PROFILE_DIR = tmp / "edge_profile2"
    edge_device.EDGE_LOGIN_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    seen = []                          # the should_cancel each nested navigate received
    real_nav = edge_device.navigate_with_auth
    real_logged = edge_device.is_logged_in

    def _rec_nav(page, **kw):          # record the kwarg, exactly like Codex's diagnostic
        seen.append(kw.get("should_cancel", "MISSING"))

    edge_device.navigate_with_auth = _rec_nav
    edge_device.is_logged_in = lambda page: False     # force the navigate=True recapture path

    marker = lambda: False             # NOT cancelled -> the outer loop reaches the nested navigate

    class _P2Page:
        def is_closed(self):
            return False

    class _Ctx2:
        pages = []                     # no pre-existing page -> _first_or_new_page opens one

        def new_page(self):
            return _P2Page()

        def storage_state(self):
            return {"cookies": [], "origins": []}

    class _Browser2:
        contexts = [_Ctx2()]

        def close(self):
            pass

    class _Chromium2:
        def connect_over_cdp(self, url, **k):
            return _Browser2()

        def launch_persistent_context(self, *a, **k):
            return _Ctx2()

    class _P2:
        chromium = _Chromium2()

    try:
        # A context opens, then nested recapture navigation begins -- the callback
        # must arrive there, not only at the outer pre-connect/pre-launch poll.
        edge_device.capture_edge_login_state_over_cdp(
            _P2(), "http://127.0.0.1:9", timeout_ms=500, should_cancel=marker)
        edge_device.capture_edge_login_state_from_profiles(
            _P2(), timeout_ms=500, should_cancel=marker)
    finally:
        edge_device.navigate_with_auth = real_nav
        edge_device.is_logged_in = real_logged

    check("nested recapture navigate ran on both CDP + profile paths", len(seen) >= 2)
    check("every nested navigate received the should_cancel callback (not empty kwargs)",
          bool(seen) and all(cb is marker for cb in seen))


def test_recapture_swallow_logged():
    print("auth-path recapture swallow LOGS the reason (not silent):")
    import io
    import logging

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.DEBUG)
    edge_device.log.addHandler(handler)
    old_level = edge_device.log.level
    edge_device.log.setLevel(logging.DEBUG)
    real_nav = edge_device.navigate_with_auth

    def _boom(page, **k):
        raise RuntimeError("navigate exploded")

    class _P:
        def is_closed(self):
            return False

    class _Ctx:
        pages = []

        def new_page(self):
            return _P()

        def storage_state(self):
            return {"cookies": [], "origins": []}

    edge_device.navigate_with_auth = _boom
    try:
        out = edge_device.capture_storage_state_if_logged_in(_Ctx(), navigate=True)
    finally:
        edge_device.navigate_with_auth = real_nav
        edge_device.log.removeHandler(handler)
        edge_device.log.setLevel(old_level)
    logged = buf.getvalue()
    check("recapture navigate failure returns None", out is None)
    check("recapture navigate failure is LOGGED (not silent)",
          "recapture navigate failed" in logged and "RuntimeError" in logged)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tsmis_edge_"))
    test_cdp_port_gating(tmp)
    test_cdp_capture_skips_without_port()
    test_cancel_bails_promptly(tmp)
    test_cancel_reaches_nested_navigate(tmp)
    test_recapture_swallow_logged()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL EDGE-LOGIN CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
