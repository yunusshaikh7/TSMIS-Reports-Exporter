"""Microsoft Edge device-SSO login + storage-state capture (P8b — L3; uses L1+L2).

Extracted verbatim from common.py: the persistent-profile Edge launch, the
device-broker (PRT) sign-in, capturing a portable storage_state over CDP / from
the live context / from the on-disk profiles, and the portability probe. Uses
browser_channels (launch + contexts) and auth_nav (navigate + signed-in check).
common.py re-exports the public names.

Console-free; the `"tsmis.auth"` logger name is preserved.
"""
import logging
import socket
import time

from paths import EDGE_LOGIN_PROFILE_DIR
from errors import AuthError
from site_target import get_url
from browser_channels import _LNA_ARGS, _new_app_context, launch_browser
from auth_nav import auth_state, is_logged_in, navigate_with_auth

log = logging.getLogger("tsmis.auth")


def _free_local_port():
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _first_or_new_page(ctx):
    try:
        pages = [pg for pg in ctx.pages if not pg.is_closed()]
    except Exception:
        pages = []
    return pages[0] if pages else ctx.new_page()


def capture_storage_state_if_logged_in(ctx, *, navigate=False, timeout_ms=15_000):
    """Return Playwright storage_state from `ctx` only after a real TSMIS login.

    `navigate=True` is for recapture attempts: reopen an Edge profile, navigate
    to the report URL, and see whether the profile already carries the session.
    """
    try:
        pages = [pg for pg in ctx.pages if not pg.is_closed()]
    except Exception:
        pages = []
    for page in pages:
        try:
            if is_logged_in(page):
                return ctx.storage_state()
        except Exception:
            continue
    # Nothing matched: record what each open page actually showed, so a failed
    # capture in the headed login flow is diagnosable from the log.
    for page in pages:
        try:
            log.info("auth: capture page not signed in: %s", auth_state(page))
        except Exception:
            pass
    if not navigate:
        return None
    try:
        # Full sign-in chain, not a bare goto: the app shows its own
        # "Sign In with ArcGIS" button when the reopened profile has no live
        # app token, and the profile's silent Azure session only helps if the
        # chain is actually clicked through.
        page = _first_or_new_page(ctx)
        navigate_with_auth(page)
        if is_logged_in(page):
            return ctx.storage_state()
    except Exception:
        return None
    return None


def launch_edge_login_context(p):
    """Open headed Edge with an app-owned persistent profile for SSO.

    Managed Edge can abandon Playwright's temporary profile when it switches into
    a work profile. This launches Edge with a durable user data directory so a
    later recapture pass can reopen the same profile tree and extract cookies.
    A CDP port is also enabled; if Edge preserves it across the switch, callers
    can attach to the live relaunched browser before falling back to disk.
    """
    EDGE_LOGIN_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    port = _free_local_port()
    args = _LNA_ARGS + [
        "--profile-directory=Default",
        f"--remote-debugging-port={port}",
    ]
    # Pre-grant local-network-access like every other automated context (the
    # permission dialog otherwise opens as an extra tab in the sign-in window);
    # fall back without the kwarg for browsers that don't know the name.
    try:
        ctx = p.chromium.launch_persistent_context(
            str(EDGE_LOGIN_PROFILE_DIR),
            channel="msedge",
            headless=False,
            args=args,
            permissions=["local-network-access"],
        )
    except Exception:
        ctx = p.chromium.launch_persistent_context(
            str(EDGE_LOGIN_PROFILE_DIR),
            channel="msedge",
            headless=False,
            args=args,
        )
    page = _first_or_new_page(ctx)
    page.goto(get_url())
    return ctx, f"http://127.0.0.1:{port}"


def _known_edge_profile_names():
    names = ["Default"]
    try:
        for child in EDGE_LOGIN_PROFILE_DIR.iterdir():
            if child.is_dir() and (child.name == "Default" or child.name.startswith("Profile ")):
                names.append(child.name)
    except OSError:
        pass
    return list(dict.fromkeys(names))


def capture_edge_login_state_over_cdp(p, cdp_url, *, timeout_ms=8_000):
    """Try to attach to a live relaunched Edge and capture its storage_state."""
    log.info("auth: trying CDP re-attach to Edge at %s (up to %ds)",
             cdp_url, timeout_ms // 1000)
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        browser = None
        try:
            browser = p.chromium.connect_over_cdp(
                cdp_url,
                timeout=1_500,
                is_local=True,
                no_defaults=True,
            )
            for ctx in browser.contexts:
                state = capture_storage_state_if_logged_in(ctx, navigate=True)
                if state:
                    return state
        except Exception:
            pass
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
        time.sleep(0.5)
    return None


def capture_edge_login_state_from_profiles(p, *, timeout_ms=20_000):
    """Reopen the app-owned Edge profile tree and look for a saved TSMIS login.

    Returns `(state, profile_name)` or `(None, None)`.
    """
    deadline = time.monotonic() + (timeout_ms / 1000)
    for profile_name in _known_edge_profile_names():
        log.info("auth: recapture: reopening Edge profile %r headless", profile_name)
        while time.monotonic() < deadline:
            ctx = None
            try:
                ctx = p.chromium.launch_persistent_context(
                    str(EDGE_LOGIN_PROFILE_DIR),
                    channel="msedge",
                    headless=True,
                    args=[f"--profile-directory={profile_name}"],
                )
                state = capture_storage_state_if_logged_in(ctx, navigate=True)
                if state:
                    return state, profile_name
                break
            except Exception as e:
                log.info("auth: recapture: profile %r attempt failed (%s); retrying",
                         profile_name, type(e).__name__)
                time.sleep(1)
            finally:
                if ctx:
                    try:
                        ctx.close()
                    except Exception:
                        pass
    return None, None


def open_edge_device_context(p, *, headless=True):
    """Open the app-owned persistent Edge sign-in profile, logged in and ready.

    The one-click Windows sign-in lives in the durable login profile
    (EDGE_LOGIN_PROFILE_DIR, primed by the headed Edge login) -- a fresh
    cookie-free Edge context does NOT get it. Managed Edge may have moved the
    signed-in state into a work profile directory, so each known profile is
    tried in turn: open it headless, navigate (the "Caltrans Azure AD" click
    happens inside navigate_with_auth), and keep the first context that lands
    logged in. A profile that was never primed -- or a PC without the silent
    sign-in -- never reaches the report page, so this raises AuthError there.

    Returns (ctx, page) with the context left OPEN; the caller owns closing it
    (ctx.close() shuts the whole persistent browser down). NOTE: a persistent
    profile can only be open in ONE browser at a time -- callers must not hold
    two of these concurrently.
    """
    EDGE_LOGIN_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    profiles = _known_edge_profile_names()
    attempts = []
    for profile_name in profiles:
        ctx = None
        log.info("auth: device sign-in: opening Edge profile %r (headless=%s)",
                 profile_name, headless)
        try:
            launch_kwargs = dict(
                channel="msedge",
                headless=headless,
                args=_LNA_ARGS + [f"--profile-directory={profile_name}"],
            )
            # Pre-grant local-network-access like every other automated
            # context; retry without it for browsers that don't know the name.
            try:
                ctx = p.chromium.launch_persistent_context(
                    str(EDGE_LOGIN_PROFILE_DIR),
                    permissions=["local-network-access"],
                    **launch_kwargs,
                )
            except Exception:
                ctx = p.chromium.launch_persistent_context(
                    str(EDGE_LOGIN_PROFILE_DIR), **launch_kwargs,
                )
            page = _first_or_new_page(ctx)
            navigate_with_auth(page)
            if is_logged_in(page):
                log.info("auth: device sign-in succeeded with Edge profile %r",
                         profile_name)
                return ctx, page
            attempts.append(f"{profile_name}: opened but did not sign in")
            log.info("auth: device sign-in: profile %r opened but did not sign in",
                     profile_name)
        except Exception as e:
            # The classic field failure here is "profile already in use" --
            # the profile can only be open in ONE browser at a time.
            reason = str(e).splitlines()[0] if str(e) else type(e).__name__
            attempts.append(f"{profile_name}: {type(e).__name__}: {reason}")
            log.warning("auth: device sign-in: Edge profile %r failed: %s: %s",
                        profile_name, type(e).__name__, reason)
        if ctx is not None:
            try:
                ctx.close()
            except Exception:
                pass
    log.warning("auth: device sign-in failed; attempts: %s", attempts or "none")
    raise AuthError(
        "Automatic sign-in could not complete on this PC "
        f"(tried {len(profiles)} Edge profile(s); details in the log). "
        "Please log in."
    )


def try_device_sso_login(p):
    """Attempt a fully silent TSMIS sign-in and capture its storage_state.

    Uses the app-owned persistent Edge profile (open_edge_device_context),
    where the one-click Windows sign-in lives -- no window, no typing.
    Edge-only by design: Chrome never gets the silent sign-in there. Returns
    the captured storage_state dict, or None when silent sign-in isn't
    available (callers fall back to a headed login window). NOTE: captures
    from this profile are often device-bound -- callers must check
    storage_state_is_portable before saving one."""
    ctx = None
    try:
        ctx, _page = open_edge_device_context(p)
        log.info("auth: silent device sign-in succeeded; capturing state")
        return ctx.storage_state()
    except Exception as e:
        log.info("auth: silent device sign-in not available (%s: %s)",
                 type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        return None
    finally:
        if ctx is not None:
            try:
                ctx.close()
            except Exception:
                pass


def storage_state_is_portable(p, state):
    """True if `state` actually signs into TSMIS when restored into a FRESH
    headless context -- the exact way the export engine will use it.

    Why this exists: managed Edge can satisfy the Azure AD sign-in through the
    Windows device broker (PRT) instead of cookies. A session captured from such
    a work profile LOOKS valid -- the live profile is signed in -- but its cookie
    jar carries only stub Azure tokens (an ESTSAUTH header with no payload), so
    restoring it into any fresh context silently fails to log in. Saving a state
    like that would strand the user with exports that can't sign in, so callers
    must test a capture here before writing the auth file."""
    browser = None
    try:
        log.info("auth: portability check: restoring capture into a fresh "
                 "headless context")
        browser = launch_browser(p, headless=True, args=_LNA_ARGS)
        ctx = _new_app_context(browser, storage_state=state)
        page = ctx.new_page()
        navigate_with_auth(page)
        portable = is_logged_in(page)
        log.info("auth: portability check: %s",
                 "PORTABLE (safe to save)" if portable
                 else "NOT portable (device-bound capture; will not be saved)")
        return portable
    except Exception as e:
        log.warning("auth: portability check errored (%s: %s); treating capture "
                    "as not portable", type(e).__name__,
                    str(e).splitlines()[0] if str(e) else "")
        return False
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
