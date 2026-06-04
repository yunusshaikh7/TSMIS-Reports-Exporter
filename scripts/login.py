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

from common import AUTH, URL


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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(URL)

        print()
        print("=" * 64)
        print(">>> ALT-TAB BACK HERE after you finish logging in <<<")
        print("=" * 64)
        input(">>> Press Enter once the TSMIS report page is loaded: ")

        ctx.storage_state(path=str(AUTH))
        print()
        print(f"✓ Session saved to {AUTH.name}")
        print('  You can close this window and run "3. run_export (main script).bat"')
        print()
        browser.close()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
