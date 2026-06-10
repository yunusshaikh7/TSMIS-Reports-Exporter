"""Capture an authenticated TSMIS session and save it to tsmis_auth.json.

The resulting scripts/tsmis_auth.json is shared by every export script
(ramp summary, ramp detail, etc.), so you only need to log in once per
session expiry.

The interactive flow lives in main() (guarded by __main__) so importing this
module has no side effects -- the GUI (Phase 4) will replace the input()
prompts with its own headed-login flow without launching a browser on import.
"""
import json
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from common import (
    AUTH, URL, BrowserNotFoundError, is_logged_in, launch_browser,
    capture_edge_login_state_from_profiles, capture_edge_login_state_over_cdp,
    capture_storage_state_if_logged_in, launch_edge_login_context,
)


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
        edge_state = _try_edge_persistent_login(p)
        if edge_state:
            _save_state(edge_state)
            print()
            print(f"Session saved to {AUTH.name}  (experimental Edge recapture)")
            print('  You can close this window and run "3. run_export (main script).bat"')
            input("Press Enter to exit...")
            return

        print()
        print("Experimental Edge sign-in was not captured.")
        print("Opening Google Chrome fallback -- please sign in again.")
        _run_standard_login(p)
        return

        browser = launch_browser(p, headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(URL)

        print()
        print("=" * 64)
        print(">>> ALT-TAB BACK HERE after you finish logging in <<<")
        print("=" * 64)
        input(">>> Press Enter once the TSMIS report page is loaded: ")

        # Only save if we can confirm a real login (the report page is loaded).
        # If the browser was closed or sign-in wasn't finished, is_logged_in
        # either returns False or raises -- either way, don't save a junk session.
        try:
            logged_in = is_logged_in(page)
        except Exception:
            logged_in = False

        print()
        if logged_in:
            ctx.storage_state(path=str(AUTH))
            print(f"✓ Session saved to {AUTH.name}")
            print('  You can close this window and run "3. run_export (main script).bat"')
        else:
            print("✗ Sign-in wasn't completed — the TSMIS report page isn't loaded")
            print("  (or the browser was closed). No session was saved. Please run this")
            print("  login again and wait for the report page before pressing Enter.")
        print()
        try:
            browser.close()
        except Exception:
            pass
        input("Press Enter to exit...")


def _try_edge_persistent_login(p):
    ctx = None
    cdp_url = None
    try:
        ctx, cdp_url = launch_edge_login_context(p)
    except Exception as e:
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


def _run_standard_login(p):
    try:
        browser = p.chromium.launch(headless=False, channel="chrome")
        label = "Google Chrome"
    except Exception:
        browser = launch_browser(p, headless=False)
        label = "selected browser"

    ctx = browser.new_context()
    page = ctx.new_page()
    page.goto(URL)

    print()
    print("=" * 64)
    print(f">>> Signing in with {label}.")
    print(">>> ALT-TAB BACK HERE after you finish logging in.")
    print("=" * 64)
    input(">>> Press Enter once the TSMIS report page is loaded: ")

    try:
        logged_in = is_logged_in(page)
    except Exception:
        logged_in = False

    print()
    if logged_in:
        ctx.storage_state(path=str(AUTH))
        print(f"Session saved to {AUTH.name}")
        print('  You can close this window and run "3. run_export (main script).bat"')
    else:
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
    AUTH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH, "w", encoding="utf-8") as f:
        json.dump(state, f)


if __name__ == "__main__":
    main()
