"""Bulk-export TSAR: Ramp Summary PDFs for every California state route.

Output: output/ramp_summary/tsar_ramp_summary_route_<ROUTE>.pdf
"""
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('ERROR: Playwright is not installed. Run "1. setup (one time).bat" first.')
    sys.exit(1)

from common import (
    OUTPUT_ROOT,
    ROUTES,
    handle_bad_auth,
    is_logged_in,
    navigate_with_auth,
    new_authed_browser,
    require_valid_auth,
    select_report,
    wait_with_skip_option,
)

REPORT_LABEL = "TSAR: Ramp Summary"
OUT = OUTPUT_ROOT / "ramp_summary"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    require_valid_auth()

    skipped = []
    user_skipped = []
    failed = []
    saved = 0

    print("=" * 60)
    print(f"TSMIS Ramp Summary Bulk Export — {len(ROUTES)} routes")
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
            out_path = OUT / f"tsar_ramp_summary_route_{route}.pdf"
            prefix = f"[{i:>3}/{len(ROUTES)}] Route {route}:"

            if out_path.exists():
                print(f"{prefix} already exists, skip")
                continue

            try:
                page.get_by_label("Route", exact=True).select_option(route)
                page.get_by_role("button", name="Generate").click()
                matched = wait_with_skip_option(
                    page,
                    f"""() => {{
                        const t = document.body.innerText;
                        return t.includes('Route {route}') || t.includes('No ramps found');
                    }}""",
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

                if "No ramps found" in page.inner_text("body"):
                    print(f"{prefix} empty, skip")
                    skipped.append(route)
                    continue

                page.wait_for_timeout(1000)
                page.pdf(
                    path=str(out_path),
                    format="Letter",
                    print_background=True,
                    margin={"top": "0.4in", "bottom": "0.4in", "left": "0.4in", "right": "0.4in"},
                )
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
