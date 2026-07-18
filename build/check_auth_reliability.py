"""Offline auth/session/browser reliability contract.

Uses fakes only: no browser process, network, auth file, or live TSMIS page.
Covers saved-session vs device-mode selection, browser resolution/fallback/cache,
dynamic timeout accessors, navigation cancellation/error classification, and
meaningful best-effort fallbacks that must log type + first-line reason.
"""
import contextlib
import builtins
import io
import logging
import os

from _checklib import Checker, patch, scripts_path

scripts_path()

import auth_nav
import browser_channels
import edge_device
import login
import report_nav
import session
import settings
import site_target
import timeouts
from errors import AuthError, BrowserNotFoundError, SiteUnreachableError

c = Checker()


@contextlib.contextmanager
def capture_log(logger, level=logging.INFO):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(level)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)


class _Context:
    def __init__(self, page):
        self.page = page

    def new_page(self):
        return self.page


def test_session_mode_selection():
    print("session orchestration selects saved-state vs device mode explicitly:")
    saved_browser = object()
    saved_page = object()
    saved_context = _Context(saved_page)
    calls = {}

    def launch(playwright, **kwargs):
        calls["launch"] = (playwright, kwargs)
        return saved_browser

    def new_context(browser, storage_state=None):
        calls["context"] = (browser, storage_state)
        return saved_context

    with patch(session, "require_valid_auth", lambda: None), \
         patch(session, "_auth_file_age_hours", lambda: 2.5), \
         patch(session, "launch_browser", launch), \
         patch(session, "_new_app_context", new_context), \
         patch(session, "open_edge_device_context",
               lambda _p: (_ for _ in ()).throw(
                   AssertionError("device mode used with valid saved auth"))):
        actual = session.new_authed_browser("PLAYWRIGHT", parallel=True)
    c.check("valid auth launches a parallel saved-session browser",
            actual == (saved_browser, saved_context, saved_page)
            and calls["launch"][1]["parallel"] is True
            and calls["launch"][1]["headless"] is True)
    c.check("saved storage-state path is passed to the app context",
            calls["context"] == (saved_browser, str(session.AUTH)))
    c.check("LNA launch arguments remain on the saved-session path",
            calls["launch"][1]["args"] is session._LNA_ARGS)

    device_context = object()
    device_page = object()
    device_calls = []

    def invalid_auth():
        raise AuthError("expired\nsecond line")

    with patch(session, "require_valid_auth", invalid_auth), \
         patch(session, "open_edge_device_context",
               lambda p: (device_calls.append(p) or
                          (device_context, device_page))), \
         patch(session, "launch_browser",
               lambda *_a, **_k: (_ for _ in ()).throw(
                   AssertionError("saved-session launch used without auth"))), \
         capture_log(session.log) as stream:
        actual = session.new_authed_browser("PLAYWRIGHT", parallel=True)
    logged = stream.getvalue()
    c.check("invalid/missing auth falls back to the persistent device context",
            actual == (device_context, device_context, device_page)
            and device_calls == ["PLAYWRIGHT"])
    c.check("saved-session fallback logs type + first-line reason",
            "AuthError" in logged and "expired" in logged
            and "second line" not in logged, logged)


class _Chromium:
    def __init__(self):
        self.launches = []

    def launch(self, **kwargs):
        self.launches.append(dict(kwargs))
        if kwargs.get("channel") == "chrome":
            raise RuntimeError("Chrome failed after its probe")
        return "EDGE-BROWSER"


class _Playwright:
    def __init__(self):
        self.chromium = _Chromium()


def _reset_browser_cache():
    browser_channels._resolved_channel = None
    browser_channels._resolved_parallel = None


def test_browser_resolution_and_fallback():
    print("browser resolver orders, classifies, caches, and excludes a failed launch:")
    original = (browser_channels._resolved_channel,
                browser_channels._resolved_parallel,
                browser_channels._preferred_channel,
                browser_channels.BROWSER_CHANNELS)
    forced = os.environ.pop("TSMIS_BROWSER_CHANNEL", None)
    try:
        browser_channels._preferred_channel = None
        browser_channels.BROWSER_CHANNELS = ("chromium", "chrome", "msedge")
        c.check("parallel order keeps Edge last",
                browser_channels._parallel_candidates()
                == ("chromium", "chrome", "msedge"))
        browser_channels._preferred_channel = "chrome"
        c.check("parallel user preference moves Chrome first but leaves Edge last",
                browser_channels._parallel_candidates()
                == ("chrome", "chromium", "msedge"))
        os.environ["TSMIS_BROWSER_CHANNEL"] = "msedge"
        c.check("hard environment override is the only parallel candidate",
                browser_channels._parallel_candidates() == ("msedge",))
        del os.environ["TSMIS_BROWSER_CHANNEL"]

        p = _Playwright()
        probes = []

        def probe(_p, channel):
            probes.append(channel)
            return "ok"

        _reset_browser_cache()
        with patch(browser_channels, "_candidate_channels",
                   lambda: ("chrome", "msedge")), \
             patch(browser_channels, "_probe_channel", probe):
            launched = browser_channels.launch_browser(
                p, headless=True, args=["--one"])
            again = browser_channels._resolve_channel(p)
        c.check("real Chrome launch failure falls through to Edge",
                launched == "EDGE-BROWSER"
                and [item["channel"] for item in p.chromium.launches]
                == ["chrome", "msedge"])
        c.check("failed real launch is excluded during re-resolution",
                probes == ["chrome", "msedge"], f"probes={probes}")
        c.check("the successful fallback is cached without another probe",
                again == "msedge" and probes == ["chrome", "msedge"])

        c.check("missing-browser errors are distinguished from broken installs",
                browser_channels._looks_missing("Executable doesn't exist")
                and not browser_channels._looks_missing("CDP protocol mismatch"))
        _reset_browser_cache()
        with patch(browser_channels, "_candidate_channels", lambda: ("chrome",)), \
             patch(browser_channels, "_probe_channel", lambda _p, _c: "missing"):
            try:
                browser_channels._resolve_channel(p)
                missing_message = ""
            except BrowserNotFoundError as exc:
                missing_message = str(exc)
        _reset_browser_cache()
        with patch(browser_channels, "_candidate_channels", lambda: ("chrome",)), \
             patch(browser_channels, "_probe_channel", lambda _p, _c: "broken"):
            try:
                browser_channels._resolve_channel(p)
                broken_message = ""
            except BrowserNotFoundError as exc:
                broken_message = str(exc)
        c.check("terminal messages distinguish absent vs uncontrollable browser",
                "No compatible" in missing_message
                and "was found but could not be controlled" in broken_message)
    finally:
        (browser_channels._resolved_channel,
         browser_channels._resolved_parallel,
         browser_channels._preferred_channel,
         browser_channels.BROWSER_CHANNELS) = original
        if forced is None:
            os.environ.pop("TSMIS_BROWSER_CHANNEL", None)
        else:
            os.environ["TSMIS_BROWSER_CHANNEL"] = forced


def test_context_fallback_is_logged():
    print("optional local-network permission fallback logs the exact reason:")
    sentinel = object()

    class Browser:
        def __init__(self):
            self.calls = []

        def new_context(self, **kwargs):
            self.calls.append(kwargs)
            if "permissions" in kwargs:
                raise RuntimeError("permission unsupported\nsecond line")
            return sentinel

    browser = Browser()
    with capture_log(browser_channels.log) as stream:
        result = browser_channels._new_app_context(
            browser, storage_state="state.json")
    logged = stream.getvalue()
    c.check("fallback drops only permissions and preserves storage state",
            result is sentinel and browser.calls == [
                {"permissions": ["local-network-access"],
                 "storage_state": "state.json"},
                {"storage_state": "state.json"}])
    c.check("permission fallback logs type + first-line reason",
            "RuntimeError" in logged and "permission unsupported" in logged
            and "second line" not in logged, logged)


class _PersistentChromium:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def launch_persistent_context(self, *args, **kwargs):
        self.calls.append((args, dict(kwargs)))
        if "permissions" in kwargs:
            raise RuntimeError("permission unsupported\nsecond line")
        return self.result


class _PersistentPlaywright:
    def __init__(self, result):
        self.chromium = _PersistentChromium(result)


def test_edge_persistent_permission_fallbacks_are_logged():
    print("Edge persistent-profile permission fallbacks preserve state and log:")

    class Page:
        def __init__(self):
            self.gotos = []

        def goto(self, url):
            self.gotos.append(url)

    login_ctx = object()
    login_page = Page()
    login_p = _PersistentPlaywright(login_ctx)
    with patch(edge_device, "_ensure_profile_dir", lambda: None), \
         patch(edge_device, "_first_or_new_page", lambda ctx: login_page), \
         patch(edge_device, "get_url", lambda: "https://target.example/report"), \
         capture_log(edge_device.log) as stream:
        actual_ctx, cdp_url = edge_device.launch_edge_login_context(login_p)
    logged = stream.getvalue()
    c.check("headed Edge login retries without only the optional permission",
            actual_ctx is login_ctx and cdp_url is None
            and len(login_p.chromium.calls) == 2
            and "permissions" in login_p.chromium.calls[0][1]
            and "permissions" not in login_p.chromium.calls[1][1]
            and login_page.gotos == ["https://target.example/report"])
    c.check("headed Edge permission fallback logs type + first-line reason",
            "RuntimeError" in logged and "permission unsupported" in logged
            and "second line" not in logged, logged)

    device_ctx = object()
    device_page = object()
    device_p = _PersistentPlaywright(device_ctx)
    with patch(edge_device, "_ensure_profile_dir", lambda: None), \
         patch(edge_device, "_known_edge_profile_names", lambda: ["Default"]), \
         patch(edge_device, "_first_or_new_page", lambda ctx: device_page), \
         patch(edge_device, "navigate_with_auth", lambda page: None), \
         patch(edge_device, "is_logged_in", lambda page: True), \
         capture_log(edge_device.log) as stream:
        actual_ctx, actual_page = edge_device.open_edge_device_context(device_p)
    logged = stream.getvalue()
    c.check("silent device sign-in retries the same profile without permission",
            (actual_ctx, actual_page) == (device_ctx, device_page)
            and len(device_p.chromium.calls) == 2
            and "permissions" in device_p.chromium.calls[0][1]
            and "permissions" not in device_p.chromium.calls[1][1])
    c.check("device-mode permission fallback logs type + first-line reason",
            "RuntimeError" in logged and "permission unsupported" in logged
            and "second line" not in logged, logged)


def test_console_login_fallbacks_are_logged():
    print("console login fallback decisions retain first-line diagnostics:")

    class Chromium:
        def __init__(self):
            self.channels = []

        def launch(self, **kwargs):
            self.channels.append(kwargs["channel"])
            if kwargs["channel"] == "chrome":
                raise RuntimeError("Chrome policy blocked\nsecond line")
            return "CHROMIUM-BROWSER"

    class Playwright:
        def __init__(self):
            self.chromium = Chromium()

    class PlaywrightManager:
        def __init__(self, playwright):
            self.playwright = playwright

        def __enter__(self):
            return self.playwright

        def __exit__(self, *_args):
            return False

    p = Playwright()
    opened = []
    with patch(login, "sync_playwright", lambda: PlaywrightManager(p)), \
         patch(login, "get_preferred_channel", lambda: "chrome"), \
         patch(login, "BROWSER_CHANNELS", ("chrome", "chromium")), \
         patch(login, "_login_with_browser",
               lambda browser, label: opened.append((browser, label))), \
         capture_log(login.log) as stream:
        login._run_login()
    logged = stream.getvalue()
    c.check("headed login falls through from Chrome to bundled Chromium",
            p.chromium.channels == ["chrome", "chromium"]
            and opened == [("CHROMIUM-BROWSER", login.CHANNEL_LABELS["chromium"])])
    c.check("headed-browser launch failure logs type + first-line reason",
            "RuntimeError" in logged and "Chrome policy blocked" in logged
            and "second line" not in logged, logged)

    ctx = object()
    captured_state = {"cookies": [{"name": "session"}]}
    closes = []
    with patch(login, "launch_edge_login_context", lambda _p: (ctx, None)), \
         patch(login, "capture_storage_state_if_logged_in",
               lambda _ctx: (_ for _ in ()).throw(
                   ValueError("live capture unavailable\nsecond line"))), \
         patch(login, "capture_edge_login_state_over_cdp", lambda *_a: None), \
         patch(login, "capture_edge_login_state_from_profiles",
               lambda _p: (captured_state, "Profile 1")), \
         patch(login, "_safe_close_context", lambda value: closes.append(value)), \
         patch(builtins, "input", lambda *_a, **_k: ""), \
         patch(builtins, "print", lambda *_a, **_k: None), \
         capture_log(login.log) as stream:
        recovered = login._try_edge_persistent_login("PLAYWRIGHT")
    logged = stream.getvalue()
    c.check("Edge login falls through live capture and CDP to profile recapture",
            recovered is captured_state and closes == [ctx])
    c.check("live Edge capture failure logs type + first-line reason",
            "ValueError" in logged and "live capture unavailable" in logged
            and "second line" not in logged, logged)


def test_dynamic_timeouts_and_settings_fallback_logs():
    print("timeout/site accessors read Settings at call time and log fallback reasons:")
    values = {"report_timeout_min": 7, "download_start_timeout_s": 11}
    with patch(settings, "get", lambda key: values[key]):
        first = timeouts.report_timeout_ms()
        values["report_timeout_min"] = 9
        second = timeouts.report_timeout_ms()
        download = timeouts.download_start_timeout_ms()
    c.check("timeout accessor observes a changed setting without restart",
            (first, second, download) == (420_000, 540_000, 11_000))

    def settings_boom(_key):
        raise RuntimeError("config locked\nsecond line")

    with patch(settings, "get", settings_boom), capture_log(timeouts.log) as stream:
        fallback = timeouts.report_timeout_ms()
    logged = stream.getvalue()
    c.check("timeout settings failure returns the compiled default",
            fallback == timeouts.REPORT_TIMEOUT_MS)
    c.check("timeout fallback logs type + first-line reason only",
            "RuntimeError" in logged and "config locked" in logged
            and "second line" not in logged, logged)

    def url_boom(_src, _env):
        raise RuntimeError("site settings locked\nsecond line")

    with patch(settings, "get_site_url", url_boom), \
         patch(site_target, "get_site", lambda: ("ssor", "prod")), \
         capture_log(site_target.log) as stream:
        url = site_target.get_url()
    logged = stream.getvalue()
    c.check("site-settings failure falls back to the built-in target",
            url == "https://tsmis.dot.ca.gov/index.html?env=prod&src=ssor")
    c.check("site fallback logs type + first-line reason",
            "RuntimeError" in logged and "site settings locked" in logged
            and "second line" not in logged, logged)


def test_navigation_cancel_and_error_classification():
    print("auth navigation honors cancel and classifies an unreachable site:")

    class Page:
        def __init__(self):
            self.gotos = []
            self.waits = []

        def goto(self, url):
            self.gotos.append(url)

        def wait_for_timeout(self, ms):
            self.waits.append(ms)

        def get_by_role(self, *_a, **_k):
            raise AssertionError("cancelled navigation entered the sign-in UI loop")

    page = Page()
    polls = []

    def cancel():
        polls.append(True)
        return True

    with patch(auth_nav, "get_url", lambda: "https://target.example/report"), \
         patch(auth_nav, "is_logged_in", lambda _page: False), \
         patch(auth_nav, "auth_state",
               lambda _page: {"url": "https://target.example/report",
                              "signals": {}}):
        auth_nav.navigate_with_auth(page, should_cancel=cancel)
    c.check("cancel is polled before any sign-in interaction",
            polls == [True] and page.gotos == ["https://target.example/report"])
    c.check("cancel exits with only the final bounded status wait",
            page.waits == [1000])

    class OfflinePage:
        def goto(self, _url):
            raise OSError("network unavailable\nsecond line")

    with patch(auth_nav, "get_url", lambda: "https://target.example/report"):
        try:
            auth_nav.navigate_with_auth(OfflinePage())
            error = None
        except SiteUnreachableError as exc:
            error = exc
    c.check("goto failure becomes SiteUnreachableError with the first-line cause",
            error is not None and "network unavailable" in str(error)
            and "second line" not in str(error) and isinstance(error.__cause__, OSError))


def test_preview_poll_failure_is_logged():
    print("preview-request polling failure remains nonfatal but is no longer silent:")

    class Events:
        worker_no = 4

        def screenshot_wanted(self, _worker):
            raise RuntimeError("preview flag unavailable\nsecond line")

    class Page:
        def screenshot(self, **_kwargs):
            raise AssertionError("capture ran after request polling failed")

    with capture_log(report_nav.log) as stream:
        report_nav.maybe_screenshot(Page(), Events(), note="test")
    logged = stream.getvalue()
    c.check("poll failure logs worker, type, and first-line reason",
            "browser 4" in logged and "RuntimeError" in logged
            and "preview flag unavailable" in logged
            and "second line" not in logged, logged)


if __name__ == "__main__":
    print("auth/session/browser offline reliability:")
    test_session_mode_selection()
    test_browser_resolution_and_fallback()
    test_context_fallback_is_logged()
    test_edge_persistent_permission_fallbacks_are_logged()
    test_console_login_fallbacks_are_logged()
    test_dynamic_timeouts_and_settings_fallback_logs()
    test_navigation_cancel_and_error_classification()
    test_preview_poll_failure_is_logged()
    raise SystemExit(c.summary())
