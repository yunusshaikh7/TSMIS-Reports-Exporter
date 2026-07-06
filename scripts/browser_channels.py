"""Browser launch + channel resolution/probing (P8b — engine layer L1).

Extracted verbatim from common.py: which Chromium-class browser to drive
(Built-in Chromium / Chrome / Edge), probing that a channel is actually
controllable, the per-process resolution cache, the user's preferred-channel
pick, and the LNA-pre-granted app/login contexts. Independent of auth and
navigation — it launches a browser, it does not sign in. common.py re-exports the
public names, so `from common import launch_browser` (etc.) is unchanged.

Console-free; the module logger keeps common.py's `"tsmis.auth"` name so log
output is byte-identical.
"""
import logging
import os
import sys
from pathlib import Path

from errors import BrowserNotFoundError

log = logging.getLogger("tsmis.auth")


# The app normally drives a Chromium-based browser ALREADY on the machine
# instead of bundling one (smaller download, nothing for AV/DLP to flag,
# auto-updated by the OS). Microsoft Edge ships with Windows; Chrome is the
# common alternative. Both are Chromium, so page.pdf() and downloads work.
#
# Some installs ALSO carry a private "Built-in Chromium" for Playwright: the
# with-browser release zip ships one inside _internal\ms-playwright (paths.py
# points PLAYWRIGHT_BROWSERS_PATH at it), and the .bat setup downloads one via
# `playwright install chromium`. When present it is listed first and becomes
# the default: it is unmanaged -- org policy can't relaunch it into a work
# profile mid-SSO, the failure that broke managed-Edge sign-in -- and its
# revision is pinned to the Playwright driver. Edge and Chrome stay in the
# picker as fallbacks. channel="chromium" runs the full browser in new-headless
# mode, so the one binary serves both headed sign-in and headless exports.
#
# Forward-compatibility: launching a *system channel* is intentionally
# version-tolerant -- Playwright talks CDP, which is stable, so ordinary Edge
# auto-updates keep working without a rebuild. To be safe anyway we (a) PROBE
# the browser before trusting it -- launch headless and actually drive a page --
# so a too-new Edge that Playwright can't control is detected and we fall
# through to the next channel, and (b) fail with a clear, accurate message that
# tells the user to update the tool (vs. "install a browser") only when a
# browser is present but unusable.
#
# An admin can pin a channel with the TSMIS_BROWSER_CHANNEL environment variable.


def _playwright_browsers_dir():
    """Folder where Playwright keeps its own browsers, or None when no private
    Chromium should be considered. PLAYWRIGHT_BROWSERS_PATH wins (paths.py
    points it at the bundle's ms-playwright when one ships next to the .exe).
    PACKAGED builds otherwise return None: the machine may carry an unrelated
    Playwright cache (e.g. from dev work) whose revision doesn't match this
    app's driver -- the system-browser build must default to Edge, not to that.
    Dev / .bat runs use Playwright's per-OS default cache, which is exactly
    where `1. setup…bat`'s `playwright install chromium` puts it."""
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env and env != "0":
        return Path(env)
    if getattr(sys, "frozen", False):
        return None
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / "ms-playwright"
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "ms-playwright"
    return home / ".cache" / "ms-playwright"


def _chromium_available():
    """True if a Playwright-managed Chromium appears to be installed (bundled
    next to the .exe, or downloaded by `playwright install chromium`). A cheap
    folder check -- the launch-time probe still validates it actually runs."""
    browsers_dir = _playwright_browsers_dir()
    if browsers_dir is None:
        return False
    try:
        return any(browsers_dir.glob("chromium-*"))
    except OSError:
        return False


# Default sequential order: Built-in Chromium (when present), then Google Chrome,
# then Microsoft Edge LAST. Chrome-before-Edge is deliberate (v0.17.0): every work
# PC has Edge but not all have Chrome, so Chrome — when installed — is the preferred
# EXPORT browser, while Edge stays the implicit one-click/device sign-in path and the
# ultimate fallback. `_parallel_candidates()` keeps its own (Edge-avoiding) order.
BROWSER_CHANNELS = ((("chromium",) if _chromium_available() else ())
                    + ("chrome", "msedge"))


CHANNEL_LABELS = {"chromium": "Built-in Chromium", "msedge": "Microsoft Edge",
                  "chrome": "Google Chrome"}


_resolved_channel = None        # validated channel, cached for the process


_resolved_parallel = None       # validated channel for PARALLEL workers (see below)


_preferred_channel = None       # user's pick (tried first; the other stays a fallback)


def set_preferred_channel(channel):
    """Record the user's preferred EXPORT browser (tried first; the others stay
    fallbacks). Only a CHROMIUM-CLASS channel is accepted -- 'chrome' or
    'chromium'; Edge is the implicit one-click/device sign-in path and is never
    pinned here as the export browser (anything else, including 'msedge' or None,
    resets to the default Chrome-first order). Clears the resolved caches so the
    next launch honors the new preference. A hard TSMIS_BROWSER_CHANNEL env
    override still wins over this."""
    global _preferred_channel, _resolved_channel, _resolved_parallel
    _preferred_channel = channel if channel in ("chromium", "chrome") else None
    _resolved_channel = None
    _resolved_parallel = None
    log.info("browser: preferred channel set to %s", _preferred_channel or "(default order)")


def init_preferred_channel_from_settings():
    """Seed the in-memory preferred EXPORT browser from the persisted Settings
    pick once at GUI start (the hot resolution path stays settings-free). Lazy
    import like get_url(); silently leaves the default order if settings can't be
    read or the pick isn't a valid Chromium-class channel."""
    try:
        import settings
        set_preferred_channel(settings.get_export_browser() or None)
    except Exception as e:
        log.info("browser: could not seed preferred channel from settings (%s)",
                 type(e).__name__)


def get_preferred_channel():
    """The channel the user explicitly pinned -- the TSMIS_BROWSER_CHANNEL env
    override first, then the UI pick recorded by set_preferred_channel -- or
    None when no explicit choice was made. Lets the sign-in flow honor the same
    browser choice the exports use."""
    forced = os.environ.get("TSMIS_BROWSER_CHANNEL", "").strip()
    if forced:
        return forced
    return _preferred_channel


def _candidate_channels():
    forced = os.environ.get("TSMIS_BROWSER_CHANNEL", "").strip()
    if forced:
        return (forced,)
    if _preferred_channel:
        return (_preferred_channel,) + tuple(c for c in BROWSER_CHANNELS if c != _preferred_channel)
    return BROWSER_CHANNELS


def _parallel_candidates():
    """Channel order for PARALLEL saved-session browsers (fast mode's workers,
    the env scan's scanners). Managed Edge is a bad host for several
    concurrent headless instances restoring a storage_state — field failure:
    org-managed Edge timed fast-mode workers out on a Chrome-captured session
    — so parallel work prefers an unmanaged Chromium (Built-in Chromium, then
    Chrome) and takes Edge only as a warned LAST resort. Edge keeps its
    one-click device sign-in role untouched (that flow is sequential by
    design). A UI pick of Edge is deliberately NOT honored here — honoring it
    is what caused the failure; the hard TSMIS_BROWSER_CHANNEL override still
    wins for debugging."""
    forced = os.environ.get("TSMIS_BROWSER_CHANNEL", "").strip()
    if forced:
        return (forced,)
    order = [c for c in BROWSER_CHANNELS if c != "msedge"]
    if _preferred_channel and _preferred_channel != "msedge":
        order = ([_preferred_channel]
                 + [c for c in order if c != _preferred_channel])
    if "msedge" in BROWSER_CHANNELS:
        order.append("msedge")
    return tuple(order)


def _looks_missing(err):
    """True if the launch error means the browser isn't installed (vs. installed
    but unusable). Used only to choose a better error message."""
    m = str(err).lower()
    return any(s in m for s in (
        "executable doesn't exist", "is not installed", "no such file",
        "cannot find", "was not found", "wasn't found", "could not find",
    ))


def _probe_channel(p, channel):
    """Launch `channel` headless and confirm Playwright can actually DRIVE it
    (not merely find it): open a page and run a trivial script over CDP. This is
    what catches a future Edge that Playwright is too old to control. Returns
    "ok" | "missing" | "broken"; always closes the probe browser. The reason a
    probe fails is logged here -- it is deliberately not in the user-facing
    message, so the log is the place that says WHY a channel was passed over.
    """
    browser = None
    try:
        browser = p.chromium.launch(headless=True, channel=channel)
    except Exception as e:
        status = "missing" if _looks_missing(e) else "broken"
        log.info("browser: probe %s -> %s (%s: %s)", channel, status,
                 type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        return status
    try:
        page = browser.new_context().new_page()
        page.goto("about:blank", timeout=15_000)
        return "ok" if page.evaluate("1 + 1") == 2 else "broken"
    except Exception as e:
        # Launches but can't be driven -> try the next one.
        log.info("browser: probe %s -> broken driving a page (%s: %s)", channel,
                 type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        return "broken"
    finally:
        try:
            browser.close()
        except Exception:  # silent-ok: probe teardown; the probe verdict above is the report
            pass


def _resolve_channel(p, exclude=(), parallel=False):
    """Pick a browser Playwright can drive -- Built-in Chromium when present,
    then Edge, then Chrome -- validating each by probe. Cached for the process
    (parallel work keeps its own cache + order — see _parallel_candidates).
    `exclude` skips channels already known to fail a real launch (so the
    fallback doesn't re-pick the same broken one). Raises BrowserNotFoundError
    (UI-neutral) with a message that distinguishes "none installed" from
    "installed but too new for this tool"."""
    global _resolved_channel, _resolved_parallel
    cached = _resolved_parallel if parallel else _resolved_channel
    if cached and cached not in exclude:
        return cached
    candidates = _parallel_candidates() if parallel else _candidate_channels()
    statuses = {}
    for channel in candidates:
        if channel in exclude:
            continue
        status = _probe_channel(p, channel)
        statuses[channel] = status
        if status == "ok":
            if parallel:
                _resolved_parallel = channel
                if channel == "msedge":
                    log.warning("browser: parallel workers fall back to "
                                "Microsoft Edge (no Chromium/Chrome usable) — "
                                "managed Edge can be unreliable with several "
                                "concurrent sessions")
            else:
                _resolved_channel = channel
            log.info("browser: resolved %schannel %s (candidates %s, excluded %s)",
                     "parallel " if parallel else "", channel,
                     list(candidates), list(exclude))
            return channel
    log.warning("browser: no usable channel (probes: %s, excluded %s)",
                statuses, list(exclude))
    if any(s == "broken" for s in statuses.values()):
        tried = ", ".join(f"{c} ({s})" for c, s in statuses.items())
        raise BrowserNotFoundError(
            "A web browser (Microsoft Edge / Google Chrome) was found but could "
            "not be controlled -- it may have updated to a version this tool "
            "doesn't support yet. Please update TSMIS Exporter, or contact the "
            f"maintainer to refresh it. (Tried: {tried}.)"
        )
    raise BrowserNotFoundError(
        "No compatible web browser was found. This app uses Microsoft Edge or "
        "Google Chrome to reach TSMIS -- please install Microsoft Edge, then try "
        "again."
    )


def resolve_parallel_channel(p):
    """The channel parallel saved-session browsers would use (probed +
    cached). Lets callers decide whether running several at once is wise:
    "msedge" here means nothing but managed Edge is usable — the env scan
    then drops to ONE browser instead of risking three concurrent Edge
    sessions (the fast-mode field failure). Raises BrowserNotFoundError when
    no browser works at all."""
    return _resolve_channel(p, parallel=True)


def launch_browser(p, *, headless=True, parallel=False, **kwargs):
    """Launch the first browser Playwright can drive (Built-in Chromium when
    present, then the system Edge, then Chrome).

    `parallel=True` is for saved-session browsers that run SEVERAL AT ONCE
    (fast mode's workers, the env scan's scanners): the order then prefers an
    unmanaged Chromium and takes Edge only last — see _parallel_candidates.

    Resolves + validates the channel once per process (a headless probe, so no
    window flashes during headed login), caches it, then launches for real. If a
    previously-good channel unexpectedly fails an actual launch, the cache is
    cleared and the chain is re-resolved so it can still fall back. All terminal
    failures surface as BrowserNotFoundError with a user-safe message.
    """
    global _resolved_channel, _resolved_parallel
    channel = _resolve_channel(p, parallel=parallel)   # may raise BrowserNotFoundError
    try:
        return p.chromium.launch(headless=headless, channel=channel, **kwargs)
    except Exception as first_err:
        # The probe passed but the real launch failed. Re-resolve EXCLUDING this
        # channel so we actually fall through to the OTHER browser instead of
        # re-picking the same broken one (a probe pass doesn't guarantee a real
        # launch succeeds).
        failed = channel
        log.warning("browser: launch of %s failed (%s: %s); re-resolving without it",
                    failed, type(first_err).__name__,
                    str(first_err).splitlines()[0] if str(first_err) else "")
        if parallel:
            _resolved_parallel = None
        else:
            _resolved_channel = None
        try:
            channel = _resolve_channel(p, exclude={failed}, parallel=parallel)
            return p.chromium.launch(headless=headless, channel=channel, **kwargs)
        except BrowserNotFoundError:
            raise
        except Exception:
            log.exception("browser: fallback launch failed too")
            raise BrowserNotFoundError(
                "The web browser could not be started. It may have updated to a "
                "version this tool doesn't support yet -- please update TSMIS "
                "Exporter, or contact the maintainer."
            ) from first_err


def check_browsers():
    """Probe each known browser channel for the readiness panel. Returns
    {channel: "ok" | "missing" | "broken"} (see _probe_channel). Opens its own
    Playwright, so call it from a worker thread -- never the Tk main thread."""
    from playwright.sync_api import sync_playwright
    results = {}
    with sync_playwright() as p:
        for channel in BROWSER_CHANNELS:
            results[channel] = _probe_channel(p, channel)
    log.info("browser: readiness check %s", results)
    return results


# The TSMIS page pulls report data from an intranet host, which Chromium's
# Local Network Access checks would block behind an "allow this site to access
# devices on your local network?" prompt no one can answer headless. Launch
# with the checks in their non-warning form and pre-grant the permission on
# every automated context (_new_app_context).
_LNA_ARGS = [
    "--disable-features=LocalNetworkAccessChecksWarnings",
    "--enable-features=LocalNetworkAccessChecks",
]


def _new_app_context(browser, storage_state=None):
    """New context with the local-network-access permission pre-granted (see
    _LNA_ARGS). The fallback drops only the optional permissions kwarg (older
    browsers may not know the permission name)."""
    kwargs = {}
    if storage_state is not None:
        kwargs["storage_state"] = storage_state
    try:
        return browser.new_context(permissions=["local-network-access"], **kwargs)
    except Exception:
        return browser.new_context(**kwargs)


# Public face of the LNA setup for the HEADED sign-in flows (login.py /
# gui_worker.LoginWorker). The headed windows need the exact same treatment as
# the automated contexts: without it, Chrome gates the TSMIS page's intranet
# data behind an "access devices on your local network?" prompt on EVERY
# sign-in -- and while the prompt sits unanswered the signed-in UI never
# appears, so a completed login is never detected and nothing is saved.
# (The persistent-profile Edge flow has carried this since v0.5.)
LOGIN_BROWSER_ARGS = _LNA_ARGS


def new_login_context(browser):
    """Context for a headed sign-in window, local-network-access pre-granted.
    Pair with a launch that passed LOGIN_BROWSER_ARGS."""
    return _new_app_context(browser)
