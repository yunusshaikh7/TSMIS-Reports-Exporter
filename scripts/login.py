"""Capture an authenticated TSMIS session and save it to tsmis_auth.json.

The resulting scripts/tsmis_auth.json is shared by every export script
(ramp summary, ramp detail, etc.), so you only need to log in once per
session expiry.

The interactive flow lives in main() (guarded by __main__) so importing this
module has no side effects -- the GUI (Phase 4) will replace the input()
prompts with its own headed-login flow without launching a browser on import.
"""
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from common import AUTH, URL, BrowserNotFoundError, is_logged_in, open_login_browser


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


# Sign-in attempts, in order: Chrome first, Edge only as a last-resort fallback.
# Managed Microsoft Edge relaunches itself into the work profile during the
# Caltrans SSO and can't be automated (a known, unresolved limitation -- see
# CLAUDE.md). The saved session is browser-agnostic, so exports still use the
# browser the export scripts choose (Edge by default).
_ATTEMPTS = [("chrome", False, "Google Chrome"),
             ("msedge", False, "Microsoft Edge")]


def _run_login():
    with sync_playwright() as p:
        opened_any = False
        for i, (channel, inprivate, label) in enumerate(_ATTEMPTS):
            browser = open_login_browser(p, channel, inprivate=inprivate)
            if browser is None:
                continue
            opened_any = True
            last = (i == len(_ATTEMPTS) - 1)
            logged_in = False
            try:
                ctx = browser.new_context()
                page = ctx.new_page()
                page.goto(URL)
                print()
                print("=" * 64)
                print(f">>> Signing in with {label}.")
                print(">>> ALT-TAB BACK HERE after you finish logging in <<<")
                print("=" * 64)
                input(">>> Press Enter once the TSMIS report page is loaded: ")
                # Only save if we can confirm a real login. If managed Edge
                # relaunched, the context is dead and is_logged_in raises -- treat
                # that as "not signed in here" and try the next browser.
                try:
                    logged_in = is_logged_in(page)
                    if logged_in:
                        ctx.storage_state(path=str(AUTH))
                except Exception:
                    logged_in = False
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

            print()
            if logged_in:
                print(f"✓ Session saved to {AUTH.name}  (signed in with {label})")
                print('  You can close this window and run "3. run_export (main script).bat"')
                input("Press Enter to exit...")
                return
            if not last:
                print(f"  {label} sign-in wasn't detected (managed Edge may have relaunched).")
                print("  Opening the next browser -- please sign in again.")
            else:
                print("✗ Sign-in wasn't completed in any browser. No session was saved.")
                print("  Run this login again and wait for the TSMIS report page before")
                print("  pressing Enter.")
                input("Press Enter to exit...")
                return

        if not opened_any:
            print()
            print("PROBLEM: Couldn't open Google Chrome or Microsoft Edge for sign-in.")
            print("  Please install Google Chrome, then run this login again.")
            input("Press Enter to exit...")


if __name__ == "__main__":
    main()
