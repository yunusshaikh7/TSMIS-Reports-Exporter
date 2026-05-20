"""Bulk-export Highway Sequence Listing Excel files for every California state route.

Output: output/highway_sequence/highway_sequence_route_<ROUTE>.xlsx
"""
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from common import (
    OUTPUT_ROOT,
    REPORT_TIMEOUT_MS,
    ROUTES,
    handle_bad_auth,
    is_logged_in,
    navigate_with_auth,
    new_authed_browser,
    require_valid_auth,
    select_report,
    wait_with_skip_option,
)

REPORT_LABEL = "Highway Sequence Listing"
OUT = OUTPUT_ROOT / "highway_sequence"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    require_valid_auth()

    skipped = []
    user_skipped = []
    failed = []
    saved = 0

    print("=" * 60)
    print(f"TSMIS Highway Sequence Bulk Export — {len(ROUTES)} routes")
    print("=" * 60)
    print()

    with sync_playwright() as p:
        browser, _ctx, page = new_authed_browser(p)
        navigate_with_auth(page)

        if not is_logged_in(page):
            browser.close()
            handle_bad_auth("Saved session is expired or invalid.")

        print("Logged in. Setting up form...")
        select_report(page, REPORT_LABEL)
        print("Ready. Starting export.\n")

        for i, route in enumerate(ROUTES, 1):
            out_path = OUT / f"highway_sequence_route_{route}.xlsx"
            prefix = f"[{i:>3}/{len(ROUTES)}] Route {route}:"

            if out_path.exists():
                print(f"{prefix} already exists, skip")
                continue

            try:
                page.get_by_label("Route", exact=True).select_option(route)
                page.get_by_role("button", name="Generate").click()
                # The Export button only renders when the report has data. If
                # the route is empty, TSMIS shows a "No ... found" message
                # instead — match that loosely so unknown empty-state wording
                # doesn't stall the loop.
                matched = wait_with_skip_option(
                    page,
                    """() => {
                        const t = document.body.innerText;
                        return document.querySelector('button.export-btn') !== null
                            || /No \\w+ found/i.test(t);
                    }""",
                    prefix,
                )
                if not matched:
                    user_skipped.append(route)
                    navigate_with_auth(page)
                    if not is_logged_in(page):
                        browser.close()
                        handle_bad_auth("Session expired during skip recovery.")
                    select_report(page, REPORT_LABEL)
                    continue

                if page.locator("button.export-btn").count() == 0:
                    print(f"{prefix} empty, skip")
                    skipped.append(route)
                    continue

                page.wait_for_timeout(1000)
                with page.expect_download(timeout=REPORT_TIMEOUT_MS) as dl_info:
                    page.locator("button.export-btn", has_text="Export").first.click()
                dl_info.value.save_as(str(out_path))
                saved += 1
                print(f"{prefix} saved")

            except Exception as e:
                print(f"{prefix} FAILED ({type(e).__name__}) — recovering")
                failed.append(route)
                try:
                    navigate_with_auth(page)
                    if not is_logged_in(page):
                        browser.close()
                        handle_bad_auth("Session expired partway through the batch.")
                    select_report(page, REPORT_LABEL)
                except SystemExit:
                    raise
                except Exception as recovery_err:
                    print(f"Recovery failed: {recovery_err}")
                    break

        print()
        print("=" * 60)
        print(f"Saved this run:  {saved}")
        print(f"Empty (skipped): {len(skipped)} {skipped if skipped else ''}")
        print(f"Skipped by user: {len(user_skipped)} {user_skipped if user_skipped else ''}")
        print(f"Failed:          {len(failed)} {failed if failed else ''}")
        print(f"Output folder:   {OUT}")
        print("=" * 60)

        browser.close()


if __name__ == "__main__":
    main()
