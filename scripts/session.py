"""Authenticated-browser session orchestration (P8b — L4; uses L1+L2+L3).

Extracted verbatim from common.py: `new_authed_browser` — the top-level entry
that hands the engine a ready (browser, context, page) signed into the selected
site, using a saved session when present and falling back to Edge device sign-in
otherwise. Orchestrates browser_channels + auth_nav + edge_device. common.py
re-exports it.

Console-free; the `"tsmis.auth"` logger name is preserved.
"""
import logging

from paths import AUTH
from errors import AuthError
from browser_channels import _LNA_ARGS, _new_app_context, launch_browser
from auth_nav import _auth_file_age_hours, require_valid_auth
from edge_device import open_edge_device_context

log = logging.getLogger("tsmis.auth")


def new_authed_browser(p, parallel=False):
    """Launch a headless browser ready to drive TSMIS.

    With a valid saved session, restores it into the user's preferred browser
    (the original flow). `parallel=True` marks a browser that runs alongside
    OTHERS restoring the same session (fast mode's workers, the env scan's
    scanners): the channel order then avoids managed Edge — see
    _parallel_candidates. With NO usable saved session, runs in DEVICE
    SIGN-IN mode instead: it reopens the app-owned persistent Edge sign-in
    profile, where the one-click Windows sign-in lives, and the "Caltrans
    Azure AD" click signs the context in live with no typed credentials.
    Edge-only and profile-bound by design: on managed Caltrans PCs Chrome
    asks for credentials, and even a fresh Edge context without this profile
    doesn't get the one-click sign-in (device mode is single-browser, so
    `parallel` is moot there).

    Returns (browser, context, page). Caller is responsible for browser.close()
    -- in device mode the persistent context doubles as the browser handle, and
    its .close() shuts the persistent browser down.
    """
    state = None
    try:
        require_valid_auth()
        state = str(AUTH)
    except AuthError as e:
        reason = str(e).splitlines()[0] if str(e) else type(e).__name__
        log.info("auth: no usable saved session (%s: %s)",
                 type(e).__name__, reason)
        state = None

    if state is None:
        log.info("auth: DEVICE SIGN-IN mode (persistent Edge profile, no auth file)")
        ctx, page = open_edge_device_context(p)   # raises AuthError if it can't sign in
        return ctx, ctx, page

    age = _auth_file_age_hours()
    log.info("auth: using saved session %s%s%s", AUTH,
             f" (saved {age:.1f} h ago)" if age is not None else "",
             " [parallel worker]" if parallel else "")
    browser = launch_browser(p, headless=True, parallel=parallel, args=_LNA_ARGS)
    ctx = _new_app_context(browser, storage_state=state)
    page = ctx.new_page()
    return browser, ctx, page
