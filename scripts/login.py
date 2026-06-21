"""Capture an authenticated TSMIS session and save it to tsmis_auth.json.

The resulting scripts/tsmis_auth.json is shared by every export script
(ramp summary, ramp detail, etc.), so you only need to log in once per
session expiry.

The interactive flow lives in main() (guarded by __main__) so importing this
module has no side effects -- the GUI replaces the input() prompts with its
own headed-login flow without launching a browser on import.
"""
import logging
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from common import (
    AUTH, BROWSER_CHANNELS, CHANNEL_LABELS, LOGIN_BROWSER_ARGS,
    BrowserNotFoundError, get_url, is_logged_in,
    capture_edge_login_state_from_profiles, capture_edge_login_state_over_cdp,
    capture_storage_state_if_logged_in, get_preferred_channel,
    launch_edge_login_context, new_login_context, save_auth_state,
    storage_state_is_portable, try_device_sso_login,
)

log = logging.getLogger("tsmis.login")


def main():
    from logging_setup import setup_logging
    setup_logging()
    print()
    print("#" * 64)
    print("#" + " " * 62 + "#")
    print("#" + "  TSMIS LOGIN — READ THIS FIRST".ljust(62) + "#")
    print("#" + " " * 62 + "#")
    print("#" * 64)
    print()
    print("  A browser window is about to open.")
    print()
    print("  In the browser:")
    print("    1. Click 'Sign In with ArcGIS'")
    print("    2. Click 'Caltrans Azure AD'")
    print("    3. Enter your @dot.ca.gov email + password")
    print("    4. Complete MFA")
    print("    5. Wait until the TSMIS report page is loaded")
    print()
    print("  THEN: come back to THIS BLACK WINDOW (alt-tab) and")
    print("  press Enter to save your session.")
    print()
    print("  This one session is used for ALL report types.")
    print()
    print("#" * 64)
    print()
    input(">>> Press Enter NOW to open the browser... ")

    try:
        _run_login()
    except BrowserNotFoundError as e:
        print()
        print("=" * 64)
        print(f"PROBLEM: {e}")
        print("=" * 64)
        input("Press Enter to exit...")
        sys.exit(1)


def _run_login():
    with sync_playwright() as p:
        # Console/fallback flow. The GUI moved silent Edge one-click sign-in to
        # a quiet BACKGROUND check; the console has no background worker, so with
        # no explicit pick it still tries the silent sign-in first, then opens a
        # headed window in the chosen Chromium-class browser (Chrome by default,
        # Built-in Chromium when picked), and finally the Edge recapture for
        # Edge-only PCs. Edge is never a user-pickable EXPORT browser now.
        pref = get_preferred_channel()          # 'chrome'|'chromium'|None
        log.info("login: starting (export browser: %s)", pref or "auto (Chrome-first)")

        # Silent first (only with no explicit pick): on managed Caltrans PCs the
        # persistent Edge sign-in profile signs itself in via the one-click
        # Windows sign-in -- no window, no typing.
        if pref is None:
            print()
            print("Trying automatic sign-in (Microsoft Edge + this PC's Windows account)...")
            state = try_device_sso_login(p)
            if state:
                if storage_state_is_portable(p, state):
                    _save_state(state)
                    log.info("login: SAVED via silent device sign-in")
                    print()
                    print(f"Session saved to {AUTH.name}  (automatic device sign-in)")
                    print('  You can close this window and run "3. run_export (main script).bat"')
                    input("Press Enter to exit...")
                    return
                # Signed in, but the cookies are device-bound. Do NOT save them
                # (stale Azure stubs make later sign-ins prompt interactively).
                log.info("login: device sign-in works; exports will sign in live "
                         "(capture not portable, not saved)")
                print()
                print("This PC signs in automatically, but that session can't be saved")
                print("for reuse. That's fine: exports sign themselves in the same way,")
                print('so you can run "3. run_export (main script).bat" directly.')
                input("Press Enter to exit...")
                return
            print("Automatic sign-in isn't available here; opening a browser window...")

        # Headed capture in the chosen Chromium-class browser (Chrome first by
        # default; Built-in Chromium when picked or Chrome is absent).
        order = (["chromium", "chrome"] if pref == "chromium"
                 else ["chrome", "chromium"])
        for ch in order:
            if ch == "chromium" and "chromium" not in BROWSER_CHANNELS:
                continue
            try:
                browser = p.chromium.launch(headless=False, channel=ch,
                                            args=LOGIN_BROWSER_ARGS)
            except Exception as e:
                log.info("login: %s launch failed (%s)", ch, type(e).__name__)
                continue
            _login_with_browser(browser, CHANNEL_LABELS[ch])
            return

        # No Chrome/Chromium available (Edge-only PC): persistent-profile Edge
        # recapture, validating portability before saving (a Windows
        # device-broker/PRT capture can't be reused elsewhere -> device mode).
        print()
        print("No Chrome/Chromium browser is available; signing in with Microsoft Edge...")
        edge_state = _try_edge_persistent_login(p)
        if edge_state:
            print("Checking that the captured sign-in can be reused for exports...")
            if storage_state_is_portable(p, edge_state):
                _save_state(edge_state)
                log.info("login: SAVED via Edge recapture")
                print()
                print(f"Session saved to {AUTH.name}  (Microsoft Edge)")
                print('  You can close this window and run "3. run_export (main script).bat"')
                input("Press Enter to exit...")
                return
            log.info("login: Edge capture device-bound (not portable); device mode")
            print()
            print("Microsoft Edge signed you in through the Windows work profile, so that")
            print("session can't be saved -- but exports sign themselves in the same way,")
            print('so you can run "3. run_export (main script).bat" directly.')
            input("Press Enter to exit...")
            return
        log.info("login: Edge capture failed")
        print()
        print("Sign-in could not be completed. Install Google Chrome or Microsoft Edge,")
        print("then run this again.")
        input("Press Enter to exit...")


def _try_edge_persistent_login(p):
    ctx = None
    cdp_url = None
    try:
        ctx, cdp_url = launch_edge_login_context(p)
    except Exception as e:
        log.info("login: experimental Edge launch unavailable (%s)", type(e).__name__)
        print()
        print(f"Experimental Edge sign-in could not open ({type(e).__name__}).")
        return None

    print()
    print("=" * 64)
    print(">>> Experimental Edge sign-in is open.")
    print(">>> ALT-TAB BACK HERE after you finish logging in.")
    print("=" * 64)
    input(">>> Press Enter once the TSMIS report page is loaded: ")

    try:
        state = capture_storage_state_if_logged_in(ctx)
        if state:
            _safe_close_context(ctx)
            return state
    except Exception:
        pass

    print("Edge did not expose a live session; trying CDP/profile recapture...")
    state = capture_edge_login_state_over_cdp(p, cdp_url)
    if state:
        _safe_close_context(ctx)
        return state

    _safe_close_context(ctx)
    state, _profile_name = capture_edge_login_state_from_profiles(p)
    return state


def _login_with_browser(browser, label):
    """Drive a normal headed sign-in in `browser`; save only on a real login."""
    # Pre-granted local-network-access context: otherwise Chrome prompts per
    # sign-in and an unanswered prompt blocks the signed-in UI, so the login
    # is never detected (see common.LOGIN_BROWSER_ARGS).
    ctx = new_login_context(browser)
    page = ctx.new_page()
    page.goto(get_url())
    log.info("login: sign-in window opened in %s", label)

    print()
    print("=" * 64)
    print(f">>> Signing in with {label}.")
    print(">>> ALT-TAB BACK HERE after you finish logging in.")
    print("=" * 64)
    input(">>> Press Enter once the TSMIS report page is loaded: ")

    # SSO can land the signed-in report page in a popup/new tab, so check every
    # open page -- not just the original one (which the IdP may have replaced).
    logged_in = False
    for pg in ctx.pages:
        try:
            if is_logged_in(pg):
                logged_in = True
                break
        except Exception:
            continue

    print()
    if logged_in:
        save_auth_state(ctx.storage_state())
        log.info("login: SAVED via %s", label)
        print(f"Session saved to {AUTH.name}")
        print('  You can close this window and run "3. run_export (main script).bat"')
    else:
        log.info("login: %s finished without a detected login; nothing saved", label)
        print("Sign-in was not completed. No session was saved.")
        print("Run this login again and wait for the report page before pressing Enter.")
    print()
    try:
        browser.close()
    except Exception:
        pass
    input("Press Enter to exit...")


def _safe_close_context(ctx):
    try:
        ctx.close()
    except Exception:
        pass


def _save_state(state):
    save_auth_state(state)              # logs path + cookie count


if __name__ == "__main__":
    main()
