"""Shared helpers used by every TSMIS export script.

Keeps one copy of: the report URL, the route list, auth file location,
auth validation, and the Playwright navigation helpers. Report-specific
logic (which report to pick, how to save the result) lives in the
individual export_*.py scripts so bugs in one report do not affect the
others.
"""
import json
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    PlaywrightTimeoutError = Exception  # only hit if Playwright isn't installed yet

try:
    import msvcrt  # Windows: lets us read keystrokes without blocking
    _HAS_KEYBOARD = True
except ImportError:
    _HAS_KEYBOARD = False

URL = "https://rhansonrizing.github.io/tsmis_reports/index.html"

# All export scripts share this auth file. login.py writes it; the
# export scripts read it. Lives in scripts/ so it stays next to the
# code that uses it and is easy to .gitignore.
AUTH = Path(__file__).parent / "tsmis_auth.json"

# Output root. Each report writes into its own subfolder under here
# (e.g. output/ramp_summary/, output/ramp_detail/).
OUTPUT_ROOT = Path(__file__).parent.parent / "output"

# Timeouts (milliseconds). Increase these if reports are timing out.
#
#   REPORT_TIMEOUT_MS      Hard ceiling for a single route to render or
#                          download. Some routes (e.g. Route 5 Ramp Detail)
#                          legitimately take minutes, so this is generous.
#   SKIP_PROMPT_AFTER_MS   How long to wait before telling the user they
#                          can press 'S' to skip a slow route. The hard
#                          timeout still applies; this is just the soft
#                          "second timer" that opens the escape hatch.
#   COUNTY_ENABLE_TIMEOUT_MS  Wait for the County dropdown to enable after
#                          District is set.
REPORT_TIMEOUT_MS = 300_000
SKIP_PROMPT_AFTER_MS = 60_000
COUNTY_ENABLE_TIMEOUT_MS = 60_000

ROUTES = [
    "001","002","003","004","005","005S","006","007","008","008U","009","010","010S",
    "011","012","013","014","014U","015","015S","016","017","018","020","022","023",
    "024","025","026","027","028","029","032","033","034","035","036","037","038",
    "039","040","041","043","044","045","046","047","049","050","051","052","053",
    "054","055","056","057","058","058U","059","060","061","062","063","065","066",
    "067","068","070","071","072","073","074","075","076","077","078","079","080",
    "082","083","084","085","086","087","088","089","090","091","092","094","095",
    "096","097","098","099","101","101U","103","104","105","107","108","109","110",
    "111","112","113","114","115","116","118","119","120","121","123","124","125",
    "126","127","128","129","130","131","132","133","134","135","136","137","138",
    "139","140","142","144","145","146","147","149","150","151","152","153","154",
    "155","156","158","160","161","162","163","164","165","166","167","168","169",
    "170","172","173","174","175","177","178","178S","180","182","183","184","185",
    "186","187","188","189","190","191","192","193","197","198","199","200","201",
    "202","203","204","205","207","210","210U","211","213","215","216","217","218",
    "219","220","221","222","223","227","229","232","233","236","237","238","241",
    "242","243","244","245","246","247","253","254","255","259","260","261","262",
    "263","265","266","267","269","270","271","273","275","280","281","282","283",
    "284","299","330","371","380","395","405","505","580","605","680","710","780",
    "805","880","880S","905","980",
]


def handle_bad_auth(reason):
    """Delete stale auth file and tell the user what to do."""
    print()
    print("=" * 60)
    print("LOGIN PROBLEM")
    print("=" * 60)
    print(f"Reason: {reason}")
    print()
    if AUTH.exists():
        try:
            AUTH.unlink()
            print(f"Deleted stale session file: {AUTH.name}")
        except Exception as e:
            print(f"Could not delete {AUTH.name}: {e}")
            print("Please delete it manually.")
    print()
    print('Next step:  Close this window, then run  "2. login (update login).bat"')
    print("=" * 60)
    input("\nPress Enter to exit...")
    sys.exit(1)


def require_valid_auth():
    """Exit with guidance if the auth file is missing or corrupt."""
    if not AUTH.exists():
        handle_bad_auth("No saved session file found.")
    try:
        with open(AUTH, "r", encoding="utf-8") as f:
            json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        handle_bad_auth(f"Session file is corrupted ({type(e).__name__}).")


def navigate_with_auth(page):
    """Open the TSMIS page and click through any leftover SSO redirect."""
    page.goto(URL)
    page.wait_for_timeout(2000)
    try:
        page.get_by_text("Caltrans Azure AD").click(timeout=4000)
        page.wait_for_url(URL, timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(2000)


def is_logged_in(page):
    """Quick check: are we on the report page, or stuck at a login screen?"""
    return "tsmis_reports" in page.url and page.locator("#customReport").count() > 0


def select_report(page, report_label):
    """Pick a report from the #customReport dropdown then fan out
    District/County/Route to -- ALL --.

    report_label is the exact dropdown text, e.g. "TSAR: Ramp Summary".
    """
    page.locator("#customReport").click()
    page.locator("#customReport li.cs-option", has_text=report_label).first.click()
    page.get_by_role("button", name="District / County / Route").click()
    page.get_by_label("District").select_option(label="-- ALL --")
    page.wait_for_function(
        "() => !document.querySelector('#districtCountySelect').disabled",
        timeout=COUNTY_ENABLE_TIMEOUT_MS,
    )
    page.locator("#districtCountySelect").select_option(label="-- ALL --")


def _drain_skip_key():
    """Return True if any pending keystroke is 'S' (case-insensitive).

    Windows-only via msvcrt. On other platforms always returns False —
    the user can still Ctrl+C, just not soft-skip a route.
    """
    if not _HAS_KEYBOARD:
        return False
    pressed_s = False
    while msvcrt.kbhit():
        try:
            ch = msvcrt.getwch()
        except Exception:
            ch = ""
        if ch and ch.lower() == "s":
            pressed_s = True
    return pressed_s


def wait_with_skip_option(page, js_condition, prefix,
                          hard_timeout_ms=None,
                          skip_prompt_after_ms=None):
    """Wait for a JS condition with a hard ceiling and a user-skip escape.

    Polls page.wait_for_function in short chunks so we can:
      - check for a keyboard skip request ('S' on Windows),
      - print a "still working" status once the soft timer fires,
      - and enforce a hard timeout that is independent of the skip prompt.

    Returns True when the condition matched, False if the user pressed 'S'
    to skip. Raises PlaywrightTimeoutError when the hard timeout elapses.
    """
    if hard_timeout_ms is None:
        hard_timeout_ms = REPORT_TIMEOUT_MS
    if skip_prompt_after_ms is None:
        skip_prompt_after_ms = SKIP_PROMPT_AFTER_MS

    start = time.monotonic()
    hard_deadline = start + hard_timeout_ms / 1000
    prompt_at = start + skip_prompt_after_ms / 1000
    poll_chunk_ms = 5000
    prompted = False
    next_status = 0.0

    while True:
        if _drain_skip_key():
            print(f"  {prefix} skipped (user pressed 'S')")
            return False

        now = time.monotonic()
        if now >= hard_deadline:
            raise PlaywrightTimeoutError(
                f"Exceeded hard timeout of {int(hard_timeout_ms / 1000)}s"
            )

        chunk = min(poll_chunk_ms, max(100, int((hard_deadline - now) * 1000)))
        try:
            page.wait_for_function(js_condition, timeout=chunk)
            return True
        except PlaywrightTimeoutError:
            pass  # not done yet — fall through and re-check skip / deadline

        now = time.monotonic()
        if not prompted and now >= prompt_at:
            elapsed = int(now - start)
            remaining = int(hard_deadline - now)
            if _HAS_KEYBOARD:
                print(
                    f"  {prefix} still working ({elapsed}s elapsed; "
                    f"up to {remaining}s left). Press 'S' to skip this route."
                )
            else:
                print(
                    f"  {prefix} still working ({elapsed}s elapsed; "
                    f"up to {remaining}s left)."
                )
            prompted = True
            next_status = now + 30
        elif prompted and now >= next_status:
            print(f"  {prefix} still working ({int(now - start)}s)...")
            next_status = now + 30


def new_authed_browser(p):
    """Launch a headless Chromium with the saved auth restored.

    Returns (browser, context, page). Caller is responsible for browser.close().
    """
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-features=LocalNetworkAccessChecksWarnings",
            "--enable-features=LocalNetworkAccessChecks",
        ],
    )
    try:
        ctx = browser.new_context(
            storage_state=str(AUTH),
            permissions=["local-network-access"],
        )
    except Exception:
        ctx = browser.new_context(storage_state=str(AUTH))
    page = ctx.new_page()
    return browser, ctx, page
